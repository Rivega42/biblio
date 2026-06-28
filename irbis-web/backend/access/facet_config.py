#!/usr/bin/env python3
"""FACET CONFIG — авто-фасеты из любого поля каталога (own-store).

Продвигает эпик #240 («Быстрые победы»). Вместо ХАРДКОДА набора фасетов
(вид/язык/автор) — декларативный КОНФИГ «поле→фасет» (per-tenant) и подсчёт
частот значений по списку каталожных записей. Чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в точности как
``config_store.py``/``oai_pmh.py``. Никаких live-ИРБИС-записей.

Зачем
-----
Фасетный поиск (боковая панель «уточнить») в ИРБИС опирается на фиксированный
список аспектов. ``facet_config`` снимает это ограничение: библиотека сама
описывает, какие поля каталога становятся фасетами (тег + подполе + русская
подпись), а сервис считает по ним частоты значений на любом наборе записей.
Конфиг изолирован по ``tenant``; без кастома действует встроенный набор
:data:`DEFAULT_FACETS`.

Форма записи (как везде в проекте)
----------------------------------
Tag-keyed dict: поля — теги (строки), подполя — ключи внутри инстанса::

    {'900': [{'b': '05'}],
     '700': [{'a': 'Иванов И.'}, {'a': 'Петров П.'}],
     '210': [{'d': '2021'}],
     '101': 'rus',
     '606': [{'a': 'История'}]}

Поле может быть списком инстансов-dict ``[{code: value}]`` ИЛИ голым скаляром
(как ``'101': 'rus'``). Хелперы :func:`_instances`/:func:`_sub` зеркалят подход
``access/oai_pmh.py`` к этой форме и устойчивы к отсутствию полей/None.

Модель
------
  * facet-def — dict ``{'tag', 'subfield', 'label'}``; пустой ``subfield`` (``''``)
    означает «брать поле как ГОЛЫЙ скаляр» (как 101);
  * ``key`` фасета — ``tag + '^' + subfield`` при непустом подполе, иначе ``tag``
    (например ``'900^b'`` или ``'101'``);
  * таблица ``facet_config`` — кастом-набор, уникальный в тройке
    ``(tenant, tag, subfield)``; кастом ПЕРЕОПРЕДЕЛЯЕТ встроенный набор целиком.

``FacetConfigStore`` — низкоуровневый sqlite-стор (upsert/list/get/remove).
``FacetService`` — глубина: разрешение активного набора (:meth:`configured`) и
подсчёт фасетов (:meth:`compute`); тонко делегирует стору CRUD.
"""
import sqlite3
import threading
from datetime import datetime, timezone

# Встроенный набор фасетов (используется, если у тенанта нет кастом-конфига).
# Пустой 'subfield' ('') = брать поле как голый скаляр (как 101).
DEFAULT_FACETS = [
    {'tag': '900', 'subfield': 'b', 'label': 'Вид документа'},
    {'tag': '101', 'subfield': '',  'label': 'Язык'},
    {'tag': '700', 'subfield': 'a', 'label': 'Автор'},
    {'tag': '210', 'subfield': 'd', 'label': 'Год издания'},
    {'tag': '606', 'subfield': 'a', 'label': 'Тематика'},
]


def _utcnow():
    """Текущее время в ISO8601 (UTC, без микросекунд). Инжектируется как ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def facet_key(tag, subfield):
    """Ключ фасета: ``tag^subfield`` при непустом подполе, иначе ``tag``.

    Примеры: ``('900', 'b')`` -> ``'900^b'``; ``('101', '')`` -> ``'101'``."""
    tag = str(tag)
    subfield = subfield or ''
    return tag + ('^' + subfield if subfield else '')


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS facet_config (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant     TEXT NOT NULL DEFAULT 'public',
  tag        TEXT NOT NULL,
  subfield   TEXT NOT NULL DEFAULT '',
  label      TEXT NOT NULL DEFAULT '',
  enabled    INTEGER NOT NULL DEFAULT 1,
  sort       INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT,
  UNIQUE(tenant, tag, subfield)
);
CREATE INDEX IF NOT EXISTS facet_config_tenant_idx ON facet_config(tenant, sort, id);
"""


# --------------------------------------------------------------------------- #
# Локальные аксессоры по форме записи проекта.
#
# Зеркалят access/oai_pmh.py (tag-keyed ``{tag: [inst]}``): голый скаляр
# оборачивается в одноэлементный список; из инстанса-dict берём подполе.
# --------------------------------------------------------------------------- #
def _instances(record, tag):
    """Список инстансов поля ``tag`` (устойчиво к отсутствию/скаляру/None).

    Голый скаляр (например ``'101': 'rus'``) оборачивается в одноэлементный
    список — чтобы единообразно итерироваться; dict-инстанс остаётся как есть."""
    if not isinstance(record, dict):
        return []
    val = record.get(tag)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _inst_sub(inst, code):
    """Значение подполя ``code`` из ОДНОГО инстанса поля или ``''``.

    Если инстанс — голый скаляр (поле без подполей) и запрашивается подполе —
    он его не несёт, поэтому возвращается ``''``. Зеркалит подход
    ``access/oai_pmh.py`` к tag-keyed форме."""
    if isinstance(inst, dict):
        if code in inst and inst[code] not in (None, ''):
            return str(inst[code])
        return ''
    # инстанс — скаляр: при пустом code считаем сам скаляр значением
    if not code:
        if inst in (None, ''):
            return ''
        return str(inst)
    return ''


def _facet_values(record, tag, subfield):
    """Значения фасета из записи для одной facet-def (тег + подполе).

    Для непустого ``subfield`` — первое значение этого подполя в КАЖДОМ
    инстансе поля (повторяющиеся поля 700 -> несколько значений). Для пустого
    ``subfield`` — поле как голый скаляр (первый инстанс). Пустые значения
    отбрасываются. Возвращает список строк (без дедупликации внутри записи —
    это решает вызывающий по семантике частоты)."""
    out = []
    if subfield:
        for inst in _instances(record, tag):
            v = _inst_sub(inst, subfield)
            if v:
                out.append(v)
    else:
        # голый скаляр: 101 / любое поле без подполей
        for inst in _instances(record, tag):
            v = _inst_sub(inst, '')
            if v:
                out.append(v)
                break  # скаляр — одно значение на запись
    return out


class FacetConfigStore:
    """Собственный sqlite-стор кастом-набора фасетов (per-tenant).

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain ``dict``. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах. Уникальность —
    в тройке ``(tenant, tag, subfield)``; ``upsert`` идемпотентен по ней.
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

    @staticmethod
    def _to_dict(row):
        """Преобразовать строку таблицы (``sqlite3.Row``) в plain ``dict``."""
        return dict(row)

    def _row_by_key(self, tenant, tag, subfield):
        """Сырая строка по тройке ключа или ``None``."""
        return self._conn().execute(
            'SELECT * FROM facet_config WHERE tenant=? AND tag=? AND subfield=?',
            (tenant, str(tag), subfield or '')).fetchone()

    def upsert(self, tenant, tag, subfield, label, enabled=True, sort=0):
        """Завести/обновить facet-def (upsert по ``(tenant, tag, subfield)``).

        Идемпотентно: повторный вызов с той же тройкой обновляет
        ``label``/``enabled``/``sort``/``updated_at``, а не плодит дубль.
        Возвращает сохранённую строку-``dict``."""
        tag = str(tag)
        subfield = subfield or ''
        enabled_int = 1 if enabled else 0
        now = self._now()
        c = self._conn()
        existing = self._row_by_key(tenant, tag, subfield)
        if existing is None:
            c.execute(
                'INSERT INTO facet_config(tenant,tag,subfield,label,enabled,'
                'sort,updated_at) VALUES(?,?,?,?,?,?,?)',
                (tenant, tag, subfield, label, enabled_int, int(sort), now))
        else:
            c.execute(
                'UPDATE facet_config SET label=?,enabled=?,sort=?,updated_at=? '
                'WHERE tenant=? AND tag=? AND subfield=?',
                (label, enabled_int, int(sort), now, tenant, tag, subfield))
        c.commit()
        return self._to_dict(self._row_by_key(tenant, tag, subfield))

    def list(self, tenant='public', enabled_only=False):
        """Список facet-def тенанта (по ``sort``, затем ``id``) -> список ``dict``.

        ``enabled_only=True`` — оставить только включённые записи."""
        if enabled_only:
            rows = self._conn().execute(
                'SELECT * FROM facet_config WHERE tenant=? AND enabled=1 '
                'ORDER BY sort, id', (tenant,)).fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM facet_config WHERE tenant=? ORDER BY sort, id',
                (tenant,)).fetchall()
        return [self._to_dict(r) for r in rows]

    def get(self, id):
        """Строка-``dict`` facet-def по ``id`` или ``None``."""
        row = self._conn().execute(
            'SELECT * FROM facet_config WHERE id=?', (id,)).fetchone()
        return self._to_dict(row) if row else None

    def remove(self, id):
        """Удалить facet-def по ``id``. ``True`` — если строка была удалена."""
        c = self._conn()
        cur = c.execute('DELETE FROM facet_config WHERE id=?', (id,))
        c.commit()
        return cur.rowcount > 0


class FacetService:
    """Глубина над :class:`FacetConfigStore`: разрешение активного набора
    фасетов и подсчёт частот значений по списку записей. Делегирует CRUD стору.
    """

    def __init__(self, store=None, now=None):
        self.store = store or FacetConfigStore(':memory:', now=now)

    def configured(self, tenant='public'):
        """Активный набор фасетов тенанта -> список facet-def с ``key``.

        Каждый элемент — ``{'tag', 'subfield', 'label', 'key'}``, где
        ``key = tag^subfield`` (или ``tag`` при пустом подполе). Логика
        переопределения: если у тенанта есть кастомные ВКЛЮЧЁННЫЕ записи —
        возвращаются они (кастом замещает встроенный набор ЦЕЛИКОМ); иначе —
        :data:`DEFAULT_FACETS`."""
        custom = self.store.list(tenant=tenant, enabled_only=True)
        if custom:
            return [{
                'tag': row['tag'],
                'subfield': row['subfield'],
                'label': row['label'],
                'key': facet_key(row['tag'], row['subfield']),
            } for row in custom]
        return [{
            'tag': d['tag'],
            'subfield': d['subfield'],
            'label': d['label'],
            'key': facet_key(d['tag'], d['subfield']),
        } for d in DEFAULT_FACETS]

    def compute(self, records, tenant='public', defs=None):
        """Подсчитать частоты значений каждого фасета по списку записей.

        ``defs`` — явный набор facet-def (с ``key`` или без — он довычисляется);
        по умолчанию берётся :meth:`configured` тенанта. По каждой tag-keyed
        записи извлекаются значения фасета (для непустого подполя — по одному на
        КАЖДЫЙ инстанс поля; для пустого подполя — поле как скаляр), пустые
        отбрасываются. Внутри фасета значения сортируются по УБЫВАНИЮ ``count``,
        затем по значению (лексикографически).

        Возвращает ``dict`` ``{key: [{'value', 'count'}, ...]}`` — по одному
        ключу на каждый фасет из набора (даже если значений нет — пустой список).
        Устойчиво к отсутствию полей/None в записях (defensive)."""
        use_defs = defs if defs is not None else self.configured(tenant)
        # Инициализируем счётчики по всем фасетам (порядок ключей — как в наборе).
        counters = {}
        order = []
        for d in use_defs:
            key = d.get('key') or facet_key(d.get('tag'), d.get('subfield'))
            if key not in counters:
                counters[key] = {}
                order.append((key, d))
        for rec in (records or []):
            for key, d in order:
                tag = d.get('tag')
                subfield = d.get('subfield', '')
                for value in _facet_values(rec, tag, subfield):
                    counters[key][value] = counters[key].get(value, 0) + 1
        out = {}
        for key, _d in order:
            buckets = counters[key]
            # сортировка: по убыванию count, затем по значению (возрастанию)
            items = sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0]))
            out[key] = [{'value': v, 'count': c} for v, c in items]
        return out

    # --- тонкие делегаты к стору ------------------------------------------- #
    def upsert(self, tenant, tag, subfield, label, enabled=True, sort=0):
        """Делегат :meth:`FacetConfigStore.upsert` — завести/обновить facet-def."""
        return self.store.upsert(tenant, tag, subfield, label,
                                 enabled=enabled, sort=sort)

    def list(self, tenant='public', enabled_only=False):
        """Делегат :meth:`FacetConfigStore.list` — кастом-набор тенанта."""
        return self.store.list(tenant=tenant, enabled_only=enabled_only)

    def remove(self, id):
        """Делегат :meth:`FacetConfigStore.remove` — удалить facet-def по ``id``."""
        return self.store.remove(id)
