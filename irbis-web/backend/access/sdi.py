#!/usr/bin/env python3
"""SDI / ИРИ — избирательное распространение информации (ребро INTEGRATION_MAP 10.1).

Аналог ИРБИС-механизма ИРИ (избирательное распространение информации) /
SDI (selective dissemination of information): профили интересов читателя
(RDR поле 140 — постоянные тематические запросы) переигрываются против
каталога, и читателю выдаются ТОЛЬКО НОВЫЕ попадания относительно прошлого
прогона.

Own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без
новых pip-зависимостей — в точности как ``pay.py``/``devices.py``.

Как это работает
----------------
``sdi_profile`` хранит постоянный запрос (``db`` + ``query``) читателя;
``sdi_hit`` — журнал уже показанных читателю mfn (UNIQUE по профилю). На
``run_profile`` сервис вызывает ``catalog.search(db, query)`` (duck-typed
хендл, НЕ импорт ``catalog``), отбирает mfn, которых ещё нет в ``sdi_hit``
профиля, записывает их как «увиденные» и обновляет ``last_run_at``. Поэтому
повторный прогон без новых записей в каталоге возвращает пустой ``new`` —
механизм идемпотентен.

Каталог-хендл (контракт)
------------------------
Любой объект с методом ``search(db, query, limit=...) -> {'items': [{'mfn': int,
...}], ...}``. Без хендла (``catalog=None``) сервис деградирует мягко: прогон
профиля возвращает ``{'new': [], ...}`` (как при недоступном каталоге).

Гранты/аудит
------------
Домен — чистая логика над своим стором (как ``pay.py``): авторизацию и
центральный audit-log проставляет слой маршрутов (``server.py`` +
``access/authz.py``); сам домен сетевого I/O не делает.
"""
import sqlite3
import threading
import time


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS sdi_profile (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  reader      TEXT NOT NULL,            -- RI= билет читателя
  name        TEXT,                     -- человекочитаемое имя профиля
  db          TEXT NOT NULL,            -- база каталога (IBIS и т.п.)
  query       TEXT NOT NULL,            -- постоянный запрос (RDR поле 140)
  created_at  REAL NOT NULL,
  last_run_at REAL                      -- момент последнего прогона (NULL — не запускался)
);
CREATE INDEX IF NOT EXISTS sdi_profile_reader_idx ON sdi_profile(reader);
CREATE TABLE IF NOT EXISTS sdi_hit (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  profile       INTEGER NOT NULL REFERENCES sdi_profile(id) ON DELETE CASCADE,
  mfn           INTEGER NOT NULL,
  first_seen_at REAL NOT NULL,
  UNIQUE(profile, mfn)
);
CREATE INDEX IF NOT EXISTS sdi_hit_profile_idx ON sdi_hit(profile, mfn);
"""


class SdiStore:
    """Собственный sqlite-стор ИРИ/SDI (профили интересов + журнал попаданий).

    ``db_path=':memory:'`` (по умолчанию) или временный файл в тестах;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.
    """

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ---- profile CRUD ----------------------------------------------------- #
    def add_profile(self, reader, name, db, query, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO sdi_profile(reader,name,db,query,created_at) '
            'VALUES(?,?,?,?,?)', (reader, name, db, query, created_at))
        c.commit()
        return self.get_profile(cur.lastrowid)

    def get_profile(self, profile_id):
        r = self._conn().execute(
            'SELECT * FROM sdi_profile WHERE id=?', (profile_id,)).fetchone()
        return dict(r) if r else None

    def list_profiles(self, reader=None):
        if reader is None:
            rows = self._conn().execute(
                'SELECT * FROM sdi_profile ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM sdi_profile WHERE reader=? ORDER BY id',
                (reader,)).fetchall()
        return [dict(r) for r in rows]

    def remove_profile(self, profile_id):
        c = self._conn()
        cur = c.execute('DELETE FROM sdi_profile WHERE id=?', (profile_id,))
        c.commit()
        return cur.rowcount > 0

    def touch_run(self, profile_id, last_run_at):
        c = self._conn()
        c.execute('UPDATE sdi_profile SET last_run_at=? WHERE id=?',
                  (last_run_at, profile_id))
        c.commit()

    # ---- hits ------------------------------------------------------------- #
    def seen_mfns(self, profile_id):
        """Множество уже показанных читателю mfn по профилю."""
        rows = self._conn().execute(
            'SELECT mfn FROM sdi_hit WHERE profile=?', (profile_id,)).fetchall()
        return {r['mfn'] for r in rows}

    def add_hits(self, profile_id, mfns, first_seen_at):
        """Записать НОВЫЕ mfn как увиденные. UNIQUE(profile,mfn) -> дубли
        тихо игнорируются (идемпотентность). Возвращает число вставленных."""
        c = self._conn()
        n = 0
        for mfn in mfns:
            cur = c.execute(
                'INSERT OR IGNORE INTO sdi_hit(profile,mfn,first_seen_at) '
                'VALUES(?,?,?)', (profile_id, int(mfn), first_seen_at))
            n += cur.rowcount
        c.commit()
        return n

    def hits(self, profile_id):
        """Все попадания профиля (хронологически — порядок первого показа)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM sdi_hit WHERE profile=? ORDER BY id',
            (profile_id,)).fetchall()]


class SdiService:
    """Операции ИРИ/SDI над :class:`SdiStore` — профили + переигрывание запросов.

    ``catalog`` — duck-typed хендл с ``search(db, query, limit=...)`` (НЕ импорт
    ``catalog``); без него прогон деградирует к пустому результату. ``now``
    инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, catalog=None, now=None):
        self.store = store or SdiStore(':memory:')
        self.catalog = catalog
        self._now = now or time.time

    # -- profiles ----------------------------------------------------------- #
    def add_profile(self, reader, name, db, query):
        """Завести постоянный запрос (RDR поле 140) для читателя."""
        return self.store.add_profile(reader, name, db, query, self._now())

    def list_profiles(self, reader):
        return self.store.list_profiles(reader)

    def remove_profile(self, profile_id):
        return self.store.remove_profile(profile_id)

    # -- run ---------------------------------------------------------------- #
    def run_profile(self, profile_id, limit=200):
        """Переиграть запрос профиля против каталога; вернуть НОВЫЕ mfn.

        Отбирает mfn из ``catalog.search`` , которых ещё нет в ``sdi_hit``
        профиля, записывает их как увиденные и обновляет ``last_run_at``.
        Возвращает ``{'profile': id, 'new': [mfn...], 'total_seen': N}``.
        Без каталога/без профиля -> ``{'new': [], 'total_seen': <как было>}``.
        """
        prof = self.store.get_profile(profile_id)
        if prof is None:
            return {'profile': profile_id, 'new': [], 'total_seen': 0}
        if self.catalog is None:
            return {'profile': profile_id, 'new': [],
                    'total_seen': len(self.store.seen_mfns(profile_id))}
        res = self.catalog.search(prof['db'], prof['query'], limit=limit) or {}
        items = res.get('items') or []
        seen = self.store.seen_mfns(profile_id)
        new = []
        for it in items:
            mfn = it.get('mfn') if isinstance(it, dict) else it
            if mfn is None:
                continue
            mfn = int(mfn)
            if mfn not in seen and mfn not in new:
                new.append(mfn)
        now = self._now()
        self.store.add_hits(profile_id, new, now)
        self.store.touch_run(profile_id, now)
        return {'profile': profile_id, 'new': new,
                'total_seen': len(seen) + len(new)}

    def run_all(self, reader=None, limit=200):
        """Прогнать все профили (или одного читателя). Сводка по профилям."""
        profiles = self.store.list_profiles(reader)
        results = [self.run_profile(p['id'], limit=limit) for p in profiles]
        total_new = sum(len(r['new']) for r in results)
        return {'profiles': len(results), 'new_total': total_new,
                'results': results}

    # -- read accumulated --------------------------------------------------- #
    def new_for_reader(self, reader):
        """Накопленные попадания всех профилей читателя -> список строк
        ``{'profile', 'name', 'mfn', 'first_seen_at'}`` (хронологически)."""
        out = []
        for p in self.store.list_profiles(reader):
            for h in self.store.hits(p['id']):
                out.append({'profile': p['id'], 'name': p['name'],
                            'mfn': h['mfn'], 'first_seen_at': h['first_seen_at']})
        return out
