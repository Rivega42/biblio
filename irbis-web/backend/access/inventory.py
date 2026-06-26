#!/usr/bin/env python3
"""Inventory domain — фондовая инвентаризация (stocktake) ручным RFID-ТСД.

Узел #272 / Фаза 2 (BIBLIO_DEVICE_INTEGRATION_DESIGN.md §5.2): Android-ТСД
(ручной UHF-терминал) массово читает EPC-метки на полке и сверяет результат с
каталогом. Это нативный домен Biblio над собственным sqlite-стором — паритет
dev/prod (ADR-004: sqlite dev / Postgres prod, зеркало в
``schema_inventory.sql``). Чистая доменная логика, без сетевого I/O и без новых
pip-зависимостей — в точности как ``devices.py``/``acquisition.py``.

Что это
-------
Оператор открывает СЕССИЮ инвентаризации на конкретном месте хранения
(``location``), терминал сканирует метки (каждый ``item_code`` идемпотентно —
повторное чтение той же метки не плодит строк), затем сессия закрывается. По
её данным строится СВЕРКА с каталогом (BookInvStates из §5.2:
Found/NotFound/NotOnPlace/Unknown) через инъектируемый seam ``catalog``:

  * ``present``  — отсканировано и числится здесь (Found);
  * ``missing``  — числится здесь, но не отсканировано (NotFound, ожид.−скан);
  * ``foreign``  — отсканировано, но числится не здесь (NotOnPlace);
  * ``unknown``  — отсканировано, но каталог такой код не знает (Unknown / New).

Каталог — НЕ часть этого домена: домен ничего не знает про ИРБИС/нативную АБИС,
он зовёт duck-typed seam (см. :class:`InventoryService`). Если seam не задан
(``catalog is None``) — сверка деградирует штатно: возвращаются только сканы,
ожидаемое/отсутствующее пусто.

Гранты/аудит — на слое маршрутов (``server.py`` + ``access/authz.py``); сам
домен — чистая логика над своим стором, как ``devices.py``.
"""
import threading
import time

# --------------------------------------------------------------------------- #
# Константы — статусы сессии инвентаризации.
# --------------------------------------------------------------------------- #
STATUS_OPEN = 'open'
STATUS_CLOSED = 'closed'
STATUSES = (STATUS_OPEN, STATUS_CLOSED)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS stocktake (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  db        TEXT,
  location  TEXT,
  status    TEXT NOT NULL DEFAULT 'open',
  operator  TEXT,
  started   REAL,
  finished  REAL,
  note      TEXT
);
CREATE INDEX IF NOT EXISTS stocktake_db_idx ON stocktake(db, location);
CREATE TABLE IF NOT EXISTS stocktake_scan (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES stocktake(id) ON DELETE CASCADE,
  item_code  TEXT NOT NULL,
  rfid       TEXT,
  ts         REAL,
  UNIQUE(session_id, item_code)
);
CREATE INDEX IF NOT EXISTS stocktake_scan_sess_idx ON stocktake_scan(session_id);
"""


class InventoryError(Exception):
    """Доменная ошибка inventory (нет сессии, скан в закрытую сессию и т.п.)."""


class InventoryStore:
    """Собственный sqlite-стор домена инвентаризации (сессии + сканы).

    ``db_path=':memory:'`` (по умолчанию) или временный файл в тестах;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.
    """

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        import sqlite3
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

    # ---- session CRUD ----------------------------------------------------- #
    def add_session(self, db, location, operator, started):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO stocktake(db,location,status,operator,started) '
            'VALUES(?,?,?,?,?)',
            (db, location, STATUS_OPEN, operator, started))
        c.commit()
        return self.get_session(cur.lastrowid)

    def get_session(self, session_id):
        r = self._conn().execute('SELECT * FROM stocktake WHERE id=?',
                                 (session_id,)).fetchone()
        return dict(r) if r else None

    def update_session(self, session_id, **fields):
        if not fields:
            return self.get_session(session_id)
        cols = ', '.join('%s=?' % k for k in fields)
        c = self._conn()
        c.execute('UPDATE stocktake SET %s WHERE id=?' % cols,
                  (*fields.values(), session_id))
        c.commit()
        return self.get_session(session_id)

    def list_sessions(self, db=None, status=None):
        q = 'SELECT * FROM stocktake WHERE 1=1'
        args = []
        if db is not None:
            q += ' AND db=?'; args.append(db)
        if status is not None:
            q += ' AND status=?'; args.append(status)
        q += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    # ---- scans ------------------------------------------------------------ #
    def add_scan(self, session_id, item_code, rfid, ts):
        """Идемпотентная вставка скана: повтор того же item в сессии — no-op."""
        c = self._conn()
        c.execute(
            'INSERT OR IGNORE INTO stocktake_scan(session_id,item_code,rfid,ts) '
            'VALUES(?,?,?,?)', (session_id, item_code, rfid, ts))
        c.commit()

    def list_scans(self, session_id):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM stocktake_scan WHERE session_id=? ORDER BY id',
            (session_id,)).fetchall()]


class InventoryService:
    """Операции домена инвентаризации над :class:`InventoryStore`.

    ``catalog`` — ОПЦИОНАЛЬНЫЙ инъектируемый seam (duck-typed) для сверки. От
    него требуются два метода (см. ниже); если ``catalog is None`` — сверка
    деградирует штатно (возвращает только сканы). Авторизация/аудит — на слое
    маршрутов; здесь — чистая доменная логика.

    Интерфейс seam ``catalog`` (контракт duck-typing)::

        expected_items(db, location) -> iterable[item_code]
            # инв.коды экземпляров, числящихся в этом месте (db+location)
        item_known(db, item_code) -> bool
            # знает ли каталог такой экземпляр вообще

    ``db`` берётся из самой сессии (поле ``db``), ``location`` — из сессии.
    """

    def __init__(self, store=None, catalog=None, now=None):
        self.store = store or InventoryStore()
        self.catalog = catalog
        self._now = now or time.time

    # -- session lifecycle -------------------------------------------------- #
    def open(self, db, location, operator=None):
        return self.store.add_session(db, location, operator, self._now())

    def _require_open(self, session_id):
        sess = self.store.get_session(session_id)
        if sess is None:
            raise InventoryError('no stocktake session id=%r' % (session_id,))
        if sess['status'] != STATUS_OPEN:
            raise InventoryError(
                'stocktake session id=%r is %s (not open)'
                % (session_id, sess['status']))
        return sess

    def scan(self, session_id, item_code, rfid=None):
        """Идемпотентно зафиксировать чтение метки. Закрытая/отсутствующая
        сессия → :class:`InventoryError`."""
        self._require_open(session_id)
        self.store.add_scan(session_id, item_code, rfid, self._now())
        return self.store.get_session(session_id)

    def close(self, session_id):
        self._require_open(session_id)
        return self.store.update_session(
            session_id, status=STATUS_CLOSED, finished=self._now())

    # -- reads -------------------------------------------------------------- #
    def get(self, session_id):
        sess = self.store.get_session(session_id)
        if sess is None:
            return None
        sess = dict(sess)
        sess['scans'] = self.store.list_scans(session_id)
        return sess

    def scans(self, session_id):
        return self.store.list_scans(session_id)

    def list_sessions(self, db=None, status=None):
        return self.store.list_sessions(db=db, status=status)

    # -- reconciliation against catalog seam -------------------------------- #
    def report(self, session_id):
        """Свести сканы сессии с каталогом (seam ``catalog``).

        Возвращает::

            {
              'session_id':    int,
              'scanned':       [item_code, ...],      # отсканированные коды
              'expected_count':int,                   # числится в этом месте
              'present':       [...],  # scanned ∩ expected  (Found)
              'missing':       [...],  # expected − scanned  (NotFound)
              'foreign':       [...],  # scanned − expected  (NotOnPlace)
              'unknown':       [...],  # scanned & not item_known (Unknown/New)
            }

        Без seam (``catalog is None``): expected пусто ⇒ present/missing/foreign
        пусты, unknown пусто (нечем проверить), scanned — как есть.
        """
        sess = self.store.get_session(session_id)
        if sess is None:
            raise InventoryError('no stocktake session id=%r' % (session_id,))

        scanned = [s['item_code'] for s in self.store.list_scans(session_id)]
        scanned_set = set(scanned)

        if self.catalog is None:
            return {
                'session_id': session_id,
                'scanned': scanned,
                'expected_count': 0,
                'present': [],
                'missing': [],
                'foreign': [],
                'unknown': [],
            }

        db = sess['db']
        location = sess['location']
        expected = list(self.catalog.expected_items(db, location))
        expected_set = set(expected)

        present = [c for c in scanned if c in expected_set]
        missing = [c for c in expected if c not in scanned_set]
        foreign = [c for c in scanned if c not in expected_set]
        unknown = [c for c in scanned if not self.catalog.item_known(db, c)]

        return {
            'session_id': session_id,
            'scanned': scanned,
            'expected_count': len(expected_set),
            'present': present,
            'missing': missing,
            'foreign': foreign,
            'unknown': unknown,
        }
