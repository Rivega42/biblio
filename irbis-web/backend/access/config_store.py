#!/usr/bin/env python3
"""CONFIG STORE — типизированные параметры АРМ «Администратор» (own-store).

Закрывает разрыв «редактирование параметров»: тот слой настроек, который ИРБИС
держит в ``.INI``/``.PAR``-файлах, здесь сделан **декларативным**, типизированным
и **разделённым по тенантам** (per-tenant). Чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в точности как
``pay.py``/``reader_registry.py``. Никаких live-ИРБИС-записей.

Зачем
-----
В ИРБИС параметры рассыпаны по ``.INI``/``.PAR`` (строки «ключ=значение», без
типа и без области видимости). У АРМ «Администратор» нет места, куда такие
правки можно было бы **сохранить** декларативно. ``config_store`` — own-store
такого слоя: каждая запись имеет ЯВНЫЙ тип (``str``/``int``/``float``/``bool``/
``json``), значение хранится текстом, но на чтении детерминированно
**десериализуется** обратно в Python-тип. Параметры изолированы по ``tenant``
(один и тот же ключ у разных тенантов независим).

Модель
------
  * таблица ``config_param`` — ключ уникален в паре ``(tenant, key)``;
  * ``value`` всегда хранится текстом; ``type`` — заявленный тип значения;
  * сериализация: ``bool`` -> ``'true'``/``'false'``; ``json`` ->
    ``json.dumps(ensure_ascii=False, sort_keys=True)``; остальное -> ``str(value)``;
  * десериализация — обратный round-trip по ``type`` (см. :func:`_deserialize`).

``ConfigStore`` — низкоуровневый стор (CRUD + список + тенанты).
``ConfigService`` — глубина: типобезопасное чтение, bulk-set (all-or-nothing),
export/import для бэкапа/переноса.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Допустимые типы параметра.
TYPE_STR = 'str'
TYPE_INT = 'int'
TYPE_FLOAT = 'float'
TYPE_BOOL = 'bool'
TYPE_JSON = 'json'
ALL_TYPES = (TYPE_STR, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_JSON)

# Литералы, принимаемые при десериализации bool (мягкий guard).
_BOOL_TRUE = ('true', '1')
_BOOL_FALSE = ('false', '0')


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS config_param (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant      TEXT NOT NULL DEFAULT 'default',
  key         TEXT NOT NULL,
  type        TEXT NOT NULL,            -- str | int | float | bool | json
  value       TEXT NOT NULL,            -- всегда хранится текстом
  description TEXT NOT NULL DEFAULT '',
  updated_at  TEXT,
  UNIQUE(tenant, key)
);
CREATE INDEX IF NOT EXISTS config_param_tenant_idx ON config_param(tenant, key);
"""


def _infer_type(value):
    """Вывести тип параметра из Python-значения.

    Порядок важен: ``bool`` проверяется ДО ``int`` (в Python ``bool`` —
    подкласс ``int``), ``dict``/``list`` -> ``json``, остальное -> ``str``.
    """
    if isinstance(value, bool):
        return TYPE_BOOL
    if isinstance(value, int):
        return TYPE_INT
    if isinstance(value, float):
        return TYPE_FLOAT
    if isinstance(value, (dict, list)):
        return TYPE_JSON
    return TYPE_STR


def _coerce_bool(value):
    """Привести значение к bool по мягким правилам (для bool-guard).

    Принимает реальный ``bool``, а также строки ``'true'``/``'false'``/
    ``'1'``/``'0'`` (без учёта регистра/пробелов). Иначе — ``ValueError``.
    """
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in _BOOL_TRUE:
        return True
    if s in _BOOL_FALSE:
        return False
    raise ValueError('значение не приводится к bool: %r' % (value,))


def _serialize(value, type_):
    """Сериализовать Python-значение в текст согласно заявленному типу.

    Здесь же — ВАЛИДАЦИЯ: если значение не соответствует типу, бросается
    ``ValueError`` (напр. ``type='int'`` со значением ``'abc'``).
    """
    if type_ == TYPE_BOOL:
        return 'true' if _coerce_bool(value) else 'false'
    if type_ == TYPE_INT:
        # bool — подкласс int; принимаем как 0/1 осознанно.
        if isinstance(value, bool):
            return str(int(value))
        try:
            return str(int(value))
        except (TypeError, ValueError):
            raise ValueError('значение не int: %r' % (value,))
    if type_ == TYPE_FLOAT:
        try:
            return repr(float(value))
        except (TypeError, ValueError):
            raise ValueError('значение не float: %r' % (value,))
    if type_ == TYPE_JSON:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            raise ValueError('значение не сериализуется в json: %r' % (value,))
    if type_ == TYPE_STR:
        return str(value)
    raise ValueError('неизвестный тип параметра: %r' % (type_,))


def _deserialize(text, type_):
    """Десериализовать текст обратно в Python-значение по типу (round-trip).

    Guard'ы: ``bool`` принимает ``'true'``/``'false'``/``'1'``/``'0'``;
    ``json`` разбирается через ``json.loads``.
    """
    if type_ == TYPE_BOOL:
        return _coerce_bool(text)
    if type_ == TYPE_INT:
        return int(text)
    if type_ == TYPE_FLOAT:
        return float(text)
    if type_ == TYPE_JSON:
        return json.loads(text)
    # TYPE_STR и фоллбэк.
    return text


class ConfigStore:
    """Собственный sqlite-стор типизированных параметров АРМ «Администратор».

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._now = now or _utcnow
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    def _row(self, tenant, key):
        """Сырая строка таблицы (sqlite3.Row) по ключу или ``None``."""
        return self._conn().execute(
            'SELECT * FROM config_param WHERE tenant=? AND key=?',
            (tenant, key)).fetchone()

    @staticmethod
    def _to_dict(row):
        """Преобразовать строку таблицы в dict с ДЕСЕРИАЛИЗОВАННЫМ значением."""
        d = dict(row)
        d['value'] = _deserialize(d['value'], d['type'])
        return d

    def set(self, key, value, type=None, tenant='default', description=None):
        """Завести/обновить (upsert по ``(tenant, key)``) типизированный параметр.

        Если ``type`` не задан — он ВЫВОДИТСЯ из Python-значения
        (:func:`_infer_type`). Значение ВАЛИДИРУЕТСЯ под тип (``ValueError`` при
        несоответствии) и сериализуется в текст. Возвращает сохранённую строку
        с ``value``, десериализованным обратно в Python-тип.
        """
        type_ = type if type is not None else _infer_type(value)
        if type_ not in ALL_TYPES:
            raise ValueError('неизвестный тип параметра: %r' % (type_,))
        text = _serialize(value, type_)  # здесь же валидация под тип
        now = self._now()
        c = self._conn()
        existing = self._row(tenant, key)
        if existing is None:
            desc = description if description is not None else ''
            c.execute(
                'INSERT INTO config_param(tenant,key,type,value,description,'
                'updated_at) VALUES(?,?,?,?,?,?)',
                (tenant, key, type_, text, desc, now))
        else:
            # description сохраняется, если в этом вызове не передан.
            desc = description if description is not None else existing['description']
            c.execute(
                'UPDATE config_param SET type=?,value=?,description=?,'
                'updated_at=? WHERE tenant=? AND key=?',
                (type_, text, desc, now, tenant, key))
        c.commit()
        return self._to_dict(self._row(tenant, key))

    def get(self, key, default=None, tenant='default'):
        """Десериализованное значение параметра (Python-тип) или ``default``."""
        row = self._row(tenant, key)
        if row is None:
            return default
        return _deserialize(row['value'], row['type'])

    def get_raw(self, key, tenant='default'):
        """Полная строка-dict параметра (value + type + description) или ``None``."""
        row = self._row(tenant, key)
        return self._to_dict(row) if row else None

    def list(self, tenant='default', prefix=None):
        """Список строк-dict параметров тенанта (по ключу), с фильтром по префиксу.

        ``prefix`` — оставить только ключи, начинающиеся на него.
        """
        if prefix is None:
            rows = self._conn().execute(
                'SELECT * FROM config_param WHERE tenant=? ORDER BY key',
                (tenant,)).fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM config_param WHERE tenant=? AND key LIKE ? '
                "ESCAPE '\\' ORDER BY key",
                (tenant, _like_prefix(prefix))).fetchall()
        return [self._to_dict(r) for r in rows]

    def delete(self, key, tenant='default'):
        """Удалить параметр. ``True`` — если строка была удалена, иначе ``False``."""
        c = self._conn()
        cur = c.execute(
            'DELETE FROM config_param WHERE tenant=? AND key=?', (tenant, key))
        c.commit()
        return cur.rowcount > 0

    def tenants(self):
        """Отсортированный список различных имён тенантов."""
        rows = self._conn().execute(
            'SELECT DISTINCT tenant FROM config_param ORDER BY tenant').fetchall()
        return [r['tenant'] for r in rows]


def _like_prefix(prefix):
    """Экранировать префикс для ``LIKE`` (``%``/``_``/``\\``) и добавить ``%``."""
    esc = (str(prefix).replace('\\', '\\\\')
           .replace('%', '\\%').replace('_', '\\_'))
    return esc + '%'


class ConfigService:
    """Глубина над :class:`ConfigStore`: типобезопасное чтение, bulk-set,
    export/import. Делегирует CRUD стору; добавляет гарантии для вызывающих.
    """

    def __init__(self, store=None, now=None):
        self.store = store or ConfigStore(':memory:', now=now)

    def typed_get(self, key, expected_type, default=None, tenant='default'):
        """Значение параметра с ГАРАНТИЕЙ типа.

        Если параметр есть, но его ``type`` != ``expected_type`` — ``TypeError``
        (guard для вызывающих, которым нужна определённость). Если параметра нет —
        ``default``.
        """
        row = self.store.get_raw(key, tenant=tenant)
        if row is None:
            return default
        if row['type'] != expected_type:
            raise TypeError(
                'тип параметра %r: ожидался %r, в сторе %r'
                % (key, expected_type, row['type']))
        return row['value']

    def set_many(self, mapping, tenant='default'):
        """Bulk-set: для каждого значения тип ВЫВОДИТСЯ; запись all-or-nothing.

        Сначала ВСЕ значения валидируются (сериализуются под выведенный тип);
        если хоть одно не проходит — бросается ``ValueError`` и НЕ пишется
        ничего. Возвращает список сохранённых строк-dict.
        """
        # Фаза валидации: ничего не пишем, пока не проверили всё.
        prepared = []
        for key, value in mapping.items():
            type_ = _infer_type(value)
            _serialize(value, type_)  # бросит ValueError при несоответствии
            prepared.append((key, value, type_))
        # Фаза записи: всё провалидировано.
        out = []
        for key, value, type_ in prepared:
            out.append(self.store.set(key, value, type=type_, tenant=tenant))
        return out

    def export(self, tenant='default'):
        """Снимок тенанта -> dict ``{key: десериализованное_значение}`` (бэкап)."""
        return {row['key']: row['value']
                for row in self.store.list(tenant=tenant)}

    def import_(self, data, tenant='default', overwrite=True):
        """Импортировать ``{key: value}`` в тенант. Возвращает число записанных.

        ``overwrite=False`` — существующие ключи пропускаются (не перезаписываются).
        Тип каждого значения выводится автоматически.
        """
        count = 0
        for key, value in data.items():
            if not overwrite and self.store.get_raw(key, tenant=tenant) is not None:
                continue
            self.store.set(key, value, tenant=tenant)
            count += 1
        return count
