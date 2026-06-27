#!/usr/bin/env python3
"""AUDIT TRAIL — богатый структурированный журнал аудита для АРМ «Администратор».

Глубже минимального ``st.audit()`` из ``access/store.py`` (его НЕ трогаем): это
самостоятельный, запрашиваемый журнал с before/after-снимками, диффами на уровне
полей и фильтрацией. Own-store: чистый stdlib + ``sqlite3`` (dev-паритет,
ADR-004), без сети и без новых pip-зависимостей — в точности как
``pay.py``/``reader_registry.py``. В живую ИРБИС НИЧЕГО не пишет.

Зачем отдельно от ``store.audit``
---------------------------------
``store.audit`` — плоская строка-факт (кто/что/когда). Здесь же — полноценная
**запись изменения**: статус (ok/denied/error), снимки состояния объекта ДО и
ПОСЛЕ (``before``/``after`` как произвольные dict → JSON), мультиарендность
(``tenant``) и индексы под выборки администратора (по актору, действию, объекту,
времени). На этом строятся диффы полей, сводки и история действий актора.

Слой
----
  * :class:`AuditStore`   — sqlite-стор (запись/выборка/счётчик), строки — dict;
  * :class:`AuditService` — глубина поверх стора: диффы, сводки, история актора.

``now`` инжектируется (по умолчанию :func:`_utcnow`, ISO8601 UTC) — для
детерминизма в тестах.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Допустимые статусы записи аудита.
STATUS_OK = 'ok'
STATUS_DENIED = 'denied'
STATUS_ERROR = 'error'
STATUSES = (STATUS_OK, STATUS_DENIED, STATUS_ERROR)


def _utcnow():
    """Текущее время в ISO8601 (UTC) — дефолтный инжектируемый ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS audit_entry (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL,                 -- ISO8601 момент события
  actor       TEXT NOT NULL,                 -- кто (логин/АРМ-оператор)
  action      TEXT NOT NULL,                 -- что сделал (create/update/delete/…)
  object_type TEXT NOT NULL,                 -- тип объекта (reader/record/…)
  object_id   TEXT,                          -- id объекта
  db          TEXT NOT NULL DEFAULT '*',     -- БД ИРБИС (или '*')
  status      TEXT NOT NULL DEFAULT 'ok',    -- ok | denied | error
  before_json TEXT,                          -- снимок ДО (JSON) | NULL
  after_json  TEXT,                          -- снимок ПОСЛЕ (JSON) | NULL
  tenant      TEXT NOT NULL DEFAULT 'default',
  note        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS audit_entry_actor_idx  ON audit_entry(actor);
CREATE INDEX IF NOT EXISTS audit_entry_action_idx ON audit_entry(action);
CREATE INDEX IF NOT EXISTS audit_entry_obj_idx    ON audit_entry(object_type, object_id);
CREATE INDEX IF NOT EXISTS audit_entry_ts_idx     ON audit_entry(ts);
"""


def _dumps(obj):
    """Сериализовать произвольный dict в стабильный JSON (или ``None``)."""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _loads(text):
    """Разобрать JSON обратно в dict (или ``None``)."""
    if text is None:
        return None
    return json.loads(text)


def _row_to_dict(r):
    """Строку sqlite -> dict записи с распарсенными ``before``/``after``."""
    d = dict(r)
    d['before'] = _loads(d.pop('before_json', None))
    d['after'] = _loads(d.pop('after_json', None))
    return d


class AuditStore:
    """Собственный sqlite-стор записей аудита. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict
    (с распарсенными ``before``/``after``)."""

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
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

    def record(self, actor, action, object_type, object_id, db='*',
               status=STATUS_OK, before=None, after=None, tenant='default',
               note='', ts=None):
        """Записать факт аудита. ``before``/``after`` — произвольные dict,
        сохраняются как стабильный JSON. Возвращает вставленную строку-dict с
        ``before``/``after``, распарсенными обратно в dict."""
        when = self._now_value(ts)
        c = self._conn()
        cur = c.execute(
            'INSERT INTO audit_entry(ts,actor,action,object_type,object_id,db,'
            'status,before_json,after_json,tenant,note) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (when, actor, action, object_type,
             None if object_id is None else str(object_id), db, status,
             _dumps(before), _dumps(after), tenant, note))
        c.commit()
        return self.get(cur.lastrowid)

    def _now_value(self, ts):
        """ts передаётся явно из сервиса/вызова (инъекция времени)."""
        return _utcnow() if ts is None else ts

    def get(self, entry_id):
        r = self._conn().execute(
            'SELECT * FROM audit_entry WHERE id=?', (entry_id,)).fetchone()
        return _row_to_dict(r) if r else None

    def _where(self, actor=None, action=None, object_type=None, object_id=None,
               status=None, since=None, until=None, tenant=None):
        """Собрать WHERE-условие и параметры из непустых фильтров (AND)."""
        clauses = []
        params = []
        if actor is not None:
            clauses.append('actor=?')
            params.append(actor)
        if action is not None:
            clauses.append('action=?')
            params.append(action)
        if object_type is not None:
            clauses.append('object_type=?')
            params.append(object_type)
        if object_id is not None:
            clauses.append('object_id=?')
            params.append(str(object_id))
        if status is not None:
            clauses.append('status=?')
            params.append(status)
        if since is not None:
            clauses.append('ts>=?')
            params.append(since)
        if until is not None:
            clauses.append('ts<=?')
            params.append(until)
        if tenant is not None:
            clauses.append('tenant=?')
            params.append(tenant)
        sql = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        return sql, params

    def entries(self, actor=None, action=None, object_type=None,
                object_id=None, status=None, since=None, until=None,
                tenant=None, limit=200):
        """Список записей (с распарсенными ``before``/``after``), новые сверху.
        Каждый непустой фильтр сужает выборку по AND; ``since``/``until`` —
        сравнение строк ``ts`` (ISO)."""
        where, params = self._where(
            actor=actor, action=action, object_type=object_type,
            object_id=object_id, status=status, since=since, until=until,
            tenant=tenant)
        sql = 'SELECT * FROM audit_entry' + where + ' ORDER BY ts DESC, id DESC'
        if limit is not None:
            sql += ' LIMIT ?'
            params = params + [limit]
        rows = self._conn().execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count(self, actor=None, action=None, object_type=None, object_id=None,
              status=None, since=None, until=None, tenant=None):
        """Число записей под те же фильтры, что и :meth:`entries` (без limit)."""
        where, params = self._where(
            actor=actor, action=action, object_type=object_type,
            object_id=object_id, status=status, since=since, until=until,
            tenant=tenant)
        sql = 'SELECT COUNT(*) AS n FROM audit_entry' + where
        return int(self._conn().execute(sql, params).fetchone()['n'])


class AuditService:
    """Глубина поверх :class:`AuditStore` — диффы полей, сводки, история актора.

    ``now`` инжектируется (по умолчанию :func:`_utcnow`) для детерминизма в
    тестах; все записи проходят через него, если ``ts`` не задан явно."""

    def __init__(self, store=None, now=None):
        self.store = store or AuditStore(':memory:')
        self._now = now or _utcnow

    def record(self, actor, action, object_type, object_id, db='*',
               status=STATUS_OK, before=None, after=None, tenant='default',
               note=''):
        """Записать факт аудита (время — из инжектированного ``now``)."""
        return self.store.record(
            actor, action, object_type, object_id, db=db, status=status,
            before=before, after=after, tenant=tenant, note=note,
            ts=self._now())

    def entries(self, **kw):
        """Прокси к :meth:`AuditStore.entries`."""
        return self.store.entries(**kw)

    def get(self, entry_id):
        """Прокси к :meth:`AuditStore.get` — запись по id или ``None``."""
        return self.store.get(entry_id)

    def count(self, **kw):
        """Прокси к :meth:`AuditStore.count`."""
        return self.store.count(**kw)

    def diff(self, entry_id):
        """Поэлементный дифф ``before`` → ``after`` записи.

        Возвращает ``{'changed': {поле: {'from': x, 'to': y}}, 'added':
        {поле: val}, 'removed': {поле: val}}``. Если одна из сторон ``None`` —
        она трактуется как ``{}`` (создание → всё в ``added``, удаление → всё в
        ``removed``). Для отсутствующей записи — пустой дифф."""
        entry = self.store.get(entry_id)
        if entry is None:
            return {'changed': {}, 'added': {}, 'removed': {}}
        before = entry.get('before') or {}
        after = entry.get('after') or {}
        changed = {}
        added = {}
        removed = {}
        for key in after:
            if key not in before:
                added[key] = after[key]
            elif before[key] != after[key]:
                changed[key] = {'from': before[key], 'to': after[key]}
        for key in before:
            if key not in after:
                removed[key] = before[key]
        return {'changed': changed, 'added': added, 'removed': removed}

    def summary(self, tenant=None, since=None):
        """Сводка по журналу -> ``{'total': N, 'by_action': {...},
        'by_actor': {...}, 'by_status': {...}}`` (с учётом фильтров
        ``tenant``/``since``)."""
        rows = self.store.entries(tenant=tenant, since=since, limit=None)
        by_action = {}
        by_actor = {}
        by_status = {}
        for r in rows:
            by_action[r['action']] = by_action.get(r['action'], 0) + 1
            by_actor[r['actor']] = by_actor.get(r['actor'], 0) + 1
            by_status[r['status']] = by_status.get(r['status'], 0) + 1
        return {
            'total': len(rows),
            'by_action': by_action,
            'by_actor': by_actor,
            'by_status': by_status,
        }

    def actor_history(self, actor, limit=50):
        """Записи одного актора (новые сверху)."""
        return self.store.entries(actor=actor, limit=limit)
