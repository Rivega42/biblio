#!/usr/bin/env python3
"""CONNECTIONS — редактируемые внешние подключения per-tenant (own-store).

Закрывает разрыв issue #335 (ось развёртывания «надстройка / замена»): тот слой
**доступов к внешним системам**, которые Biblio нужно дёргать — живой ИРБИС,
портал ``jirbis`` (Joomla-БД), «Инфорост». В ИРБИС такие реквизиты рассыпаны по
``.INI``/``.PAR`` строками «ключ=значение», без области видимости и без защиты
секретов. Здесь это сделано **редактируемой записью**, **разделённой по тенантам**
(per-tenant) и с **защитой секретов**. Чистый stdlib + ``sqlite3`` (dev-паритет,
ADR-004), без сети и без новых pip-зависимостей — как ``config_store.py``.

БЕЗОПАСНОСТЬ (главный инвариант)
--------------------------------
Секретные поля (пароли/ключи/токены, см. :data:`SECRET_FIELDS`) **никогда** не
отдаются наружу в открытом виде и **не логируются**. Наружу (в API/витрину) идёт
только **маскированная** конфигурация: непустой секрет -> ``'***'``, пустой
секрет -> ``''`` (а не звёздочки, чтобы UI отличал «не задано» от «задано»).
Реальные значения отдаёт ТОЛЬКО :meth:`ConnectionService.get_raw` — он
предназначен исключительно для внутреннего слоя подключения и не должен
попадать ни в ответы API, ни в логи.

Модель
------
  * таблица ``connection`` — запись уникальна в паре ``(tenant, kind)``;
  * ``kind`` — один из :data:`KINDS` (``irbis``/``jirbis``/``inforost``);
  * ``config`` всегда хранится текстом (JSON, stdlib ``json``);
  * ``enabled`` — флаг включённости подключения (0/1).

``ConnectionStore`` — низкоуровневый стор (upsert + чтение + список + удаление),
оперирует РЕАЛЬНЫМ (немаскированным) config.
``ConnectionService`` — глубина: валидация ``kind``, маскировка секретов на
выдаче, неперезатирание ранее сохранённого секрета при ``'***'``/``''``,
``get_raw`` для внутреннего слоя, подсказки полей для UI.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Поддерживаемые виды внешних подключений.
KINDS = ('irbis', 'jirbis', 'inforost')

# Ключи config, значение которых считается СЕКРЕТОМ (маскируется/не логируется).
SECRET_FIELDS = frozenset({'password', 'pass', 'secret', 'api_key', 'token'})

# Подсказки полей для UI: какой набор ключей у каждого вида и какие из них
# секретные. Несекретные поля помечены ``secret=False`` явно.
FIELD_HINTS = {
    'irbis': [
        {'key': 'host', 'label': 'Хост', 'secret': False},
        {'key': 'port', 'label': 'Порт', 'secret': False},
        {'key': 'db', 'label': 'База данных', 'secret': False},
        {'key': 'user', 'label': 'Пользователь', 'secret': False},
        {'key': 'password', 'label': 'Пароль', 'secret': True},
        {'key': 'encoding', 'label': 'Кодировка', 'secret': False},
    ],
    'jirbis': [
        {'key': 'host', 'label': 'Хост', 'secret': False},
        {'key': 'port', 'label': 'Порт', 'secret': False},
        {'key': 'db', 'label': 'База данных', 'secret': False},
        {'key': 'user', 'label': 'Пользователь', 'secret': False},
        {'key': 'password', 'label': 'Пароль', 'secret': True},
    ],
    'inforost': [
        {'key': 'base_url', 'label': 'Базовый URL', 'secret': False},
        {'key': 'api_key', 'label': 'API-ключ', 'secret': True},
    ],
}

# Значения, при которых секрет в обновлении трактуется как «не менять»:
# маскированная звёздочка (пришла назад из UI) или пустая строка (поле не
# заполнено в форме редактирования).
_KEEP_SECRET_SENTINELS = ('***', '')


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS connection (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant      TEXT NOT NULL DEFAULT 'default',
  kind        TEXT NOT NULL,            -- irbis | jirbis | inforost
  config      TEXT NOT NULL,            -- JSON, всегда хранится текстом
  enabled     INTEGER NOT NULL DEFAULT 1,
  updated_at  TEXT,
  UNIQUE(tenant, kind)
);
CREATE INDEX IF NOT EXISTS connection_tenant_idx ON connection(tenant, kind);
"""


class ConnectionStore:
    """Собственный sqlite-стор внешних подключений (РЕАЛЬНЫЙ config).

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict, ``config`` распарсен из JSON. ``now``
    инжектируется (по умолчанию :func:`_utcnow`, ISO8601) для детерминизма в
    тестах. Этот слой хранит секреты КАК ЕСТЬ — маскировка живёт уровнем выше,
    в :class:`ConnectionService`.
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

    def _row(self, tenant, kind):
        """Сырая строка таблицы (sqlite3.Row) по ключу или ``None``."""
        return self._conn().execute(
            'SELECT * FROM connection WHERE tenant=? AND kind=?',
            (tenant, kind)).fetchone()

    @staticmethod
    def _to_dict(row):
        """Преобразовать строку таблицы в dict с РАСПАРСЕННЫМ config и bool."""
        d = dict(row)
        d['config'] = json.loads(d['config'])
        d['enabled'] = bool(d['enabled'])
        return d

    def set(self, tenant, kind, config_json, enabled=True):
        """Завести/обновить (upsert по ``(tenant, kind)``) подключение.

        ``config_json`` — строка JSON (сериализуется уровнем выше). Возвращает
        сохранённую строку-dict с распарсенным ``config``.
        """
        now = self._now()
        c = self._conn()
        existing = self._row(tenant, kind)
        if existing is None:
            c.execute(
                'INSERT INTO connection(tenant,kind,config,enabled,updated_at) '
                'VALUES(?,?,?,?,?)',
                (tenant, kind, config_json, 1 if enabled else 0, now))
        else:
            c.execute(
                'UPDATE connection SET config=?,enabled=?,updated_at=? '
                'WHERE tenant=? AND kind=?',
                (config_json, 1 if enabled else 0, now, tenant, kind))
        c.commit()
        return self._to_dict(self._row(tenant, kind))

    def get(self, tenant, kind):
        """Строка-dict подключения (config распарсен) или ``None``."""
        row = self._row(tenant, kind)
        return self._to_dict(row) if row else None

    def for_tenant(self, tenant):
        """Список строк-dict подключений тенанта (по ``kind``)."""
        rows = self._conn().execute(
            'SELECT * FROM connection WHERE tenant=? ORDER BY kind',
            (tenant,)).fetchall()
        return [self._to_dict(r) for r in rows]

    def remove(self, tenant, kind):
        """Удалить подключение. ``True`` — если строка удалена, иначе ``False``."""
        c = self._conn()
        cur = c.execute(
            'DELETE FROM connection WHERE tenant=? AND kind=?', (tenant, kind))
        c.commit()
        return cur.rowcount > 0


class ConnectionService:
    """Глубина над :class:`ConnectionStore`: валидация, маскировка секретов,
    неперезатирание секретов при ``'***'``/``''``, ``get_raw`` для внутреннего
    слоя, подсказки полей. Наружу выдаёт ТОЛЬКО маскированную конфигурацию.
    """

    def __init__(self, store=None, now=None):
        self.store = store or ConnectionStore(':memory:', now=now)

    @staticmethod
    def mask_config(config):
        """Вернуть КОПИЮ config с замаскированными секретными полями.

        Секретный ключ (из :data:`SECRET_FIELDS`) с НЕпустым значением ->
        ``'***'``; пустой секрет (``''``/``None``/falsy) -> ``''`` (чтобы UI
        отличал «задано» от «не задано»). Несекретные поля не трогаются.
        """
        masked = {}
        for key, value in config.items():
            if key in SECRET_FIELDS:
                masked[key] = '***' if value else ''
            else:
                masked[key] = value
        return masked

    def _public(self, row):
        """Публичное (маскированное) представление строки подключения."""
        return {
            'kind': row['kind'],
            'enabled': row['enabled'],
            'config': self.mask_config(row['config']),
        }

    def set(self, tenant, kind, config, enabled=True):
        """Завести/обновить подключение; вернуть МАСКИРОВАННОЕ представление.

        Валидация: ``kind`` обязан быть в :data:`KINDS`, ``config`` — ``dict``
        (иначе ``ValueError``). НЕПЕРЕЗАТИРАНИЕ СЕКРЕТА при обновлении: если
        секретное поле пришло как ``''`` ИЛИ ``'***'`` — берётся ранее
        сохранённое значение (а не затирается пустотой/звёздочками); при
        непустом новом значении — обновляется. Реальный (немаскированный)
        ``config`` хранится в собственном сторе (off-git); наружу возвращается
        маскированная версия.
        """
        if kind not in KINDS:
            raise ValueError('неизвестный вид подключения: %r' % (kind,))
        if not isinstance(config, dict):
            raise ValueError('config должен быть dict: %r' % (config,))

        merged = dict(config)
        existing = self.store.get(tenant, kind)
        if existing is not None:
            prev = existing['config']
            for key in SECRET_FIELDS:
                if key in merged and merged[key] in _KEEP_SECRET_SENTINELS:
                    # Пришёл «sentinel» (''/'***') — не затираем прежний секрет.
                    if key in prev:
                        merged[key] = prev[key]
                    else:
                        # Прежнего значения не было — нечего хранить, убираем.
                        merged.pop(key, None)

        config_json = json.dumps(merged, ensure_ascii=False, sort_keys=True)
        row = self.store.set(tenant, kind, config_json, enabled=enabled)
        return self._public(row)

    def get(self, tenant, kind):
        """Маскированное представление подключения (+kind,enabled) или ``None``."""
        row = self.store.get(tenant, kind)
        return self._public(row) if row else None

    def get_raw(self, tenant, kind):
        """НЕмаскированное представление — РЕАЛЬНЫЕ секреты.

        ВНИМАНИЕ: только для внутреннего слоя подключения (драйвер ИРБИС/jirbis/
        инфорост). НЕ отдавать в API и НЕ логировать. Возвращает dict
        ``{kind, enabled, config}`` с настоящими значениями секретов или
        ``None``, если подключения нет.
        """
        row = self.store.get(tenant, kind)
        if row is None:
            return None
        return {
            'kind': row['kind'],
            'enabled': row['enabled'],
            'config': row['config'],
        }

    def list(self, tenant):
        """Список МАСКИРОВАННЫХ представлений подключений тенанта (по ``kind``)."""
        return [self._public(row) for row in self.store.for_tenant(tenant)]

    def remove(self, tenant, kind):
        """Удалить подключение. ``True`` — если удалено, иначе ``False``."""
        return self.store.remove(tenant, kind)

    @staticmethod
    def field_hints(kind):
        """Подсказки полей формы для вида подключения (или ``[]`` для неизвестного)."""
        return FIELD_HINTS.get(kind, [])
