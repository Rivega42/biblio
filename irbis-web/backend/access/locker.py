#!/usr/bin/env python3
"""Locker orders (постамат / SafeKeeper) — физический слой брони #222.

Узел #272 (SAFEKEEPER_HOLDS_MAPPING.md, 3/3). Locker-заказ = бронь читателя с
pickup-местом = ячейка камеры. Жизненный цикл/ячейки живут здесь (companion-стор
``locker_order`` + ``locker_order_item``), а выдача/устройства/каталожная бронь —
переиспользуются через ИНЪЕКТИРУЕМЫЕ сиды (идиом ``catalog=`` в acquisition.py):
  * ``circulation`` — опц.: ``checkout(ticket, item) -> Decision|bool`` (выдача при
    получении); нет сида ⇒ выдача без loan (standalone), как no-catalog ToCat;
  * ``devices``     — опц.: ``is_master_valid(rfid, device_id)`` /
    ``record_event(device_id, ...)`` (мастер-ключ + события сервисных открытий);
  * ``holds``       — опц.: зеркало в reader_hold (#222), чтобы заказ был виден в
    списке броней читателя (не обязательно для лога ячеек).

НЕ копия БД IDlogic; контракт IDlogic — лишь источник требований.

Состояния (IDlogic OrderStateId ↔ наши)
  1 CREATED   — создан, тело пустое
  2 PREPARED  — тело наполнено книгами
  3 STAFFED   — укомплектован, книги в ячейке (ячейка занята)
  4 ISSUED    — выдан читателю (ячейка освобождена)
  5 CANCELLED — отменён (opID 0)
  6 ISSUED_ERROR — выдан, но запись в АБИС не прошла (повтор из портала)
"""
import threading
import time

CREATED = 1
PREPARED = 2
STAFFED = 3
ISSUED = 4
CANCELLED = 5
ISSUED_ERROR = 6

# Ячейка занята, когда заказ в ней укомплектован (STAFFED). Выдача/отмена/ошибка
# освобождают ячейку.
OCCUPYING_STATES = (STAFFED,)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS locker_order (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  reader_ticket TEXT NOT NULL,
  reader_fio   TEXT,
  safekeeper   INTEGER NOT NULL,
  cell_no      INTEGER,
  cell_shift   INTEGER NOT NULL DEFAULT 0,
  state        INTEGER NOT NULL DEFAULT 1,
  staffed_by   TEXT,
  master_rfid  TEXT,
  abis_error   TEXT,
  created      REAL NOT NULL,
  updated      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS locker_order_sk_idx ON locker_order(safekeeper, state);
CREATE INDEX IF NOT EXISTS locker_order_rdr_idx ON locker_order(reader_ticket);
CREATE TABLE IF NOT EXISTS locker_order_item (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id  INTEGER NOT NULL REFERENCES locker_order(id) ON DELETE CASCADE,
  book_code TEXT, book_rfid TEXT,
  verified  INTEGER NOT NULL DEFAULT 0,
  processed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS locker_order_item_oid_idx ON locker_order_item(order_id);
"""


class LockerError(Exception):
    """Доменная ошибка locker (нет заказа, ячейка занята, нет свободных и т.п.)."""


class LockerStore:
    """Собственный sqlite-стор locker-заказов (companion к брони #222)."""

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

    def add_order(self, reader_ticket, reader_fio, safekeeper):
        now = time.time()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO locker_order(reader_ticket,reader_fio,safekeeper,state,'
            'created,updated) VALUES(?,?,?,?,?,?)',
            (reader_ticket, reader_fio, safekeeper, CREATED, now, now))
        c.commit()
        return self.get_order(cur.lastrowid)

    def get_order(self, order_id):
        r = self._conn().execute('SELECT * FROM locker_order WHERE id=?',
                                 (order_id,)).fetchone()
        return dict(r) if r else None

    def update_order(self, order_id, **fields):
        if not fields:
            return self.get_order(order_id)
        fields['updated'] = time.time()
        cols = ', '.join('%s=?' % k for k in fields)
        c = self._conn()
        c.execute('UPDATE locker_order SET %s WHERE id=?' % cols,
                  (*fields.values(), order_id))
        c.commit()
        return self.get_order(order_id)

    def list_orders(self, safekeeper=None, reader_ticket=None, state=None):
        q = 'SELECT * FROM locker_order WHERE 1=1'
        args = []
        if safekeeper is not None:
            q += ' AND safekeeper=?'; args.append(safekeeper)
        if reader_ticket is not None:
            q += ' AND reader_ticket=?'; args.append(reader_ticket)
        if state is not None:
            q += ' AND state=?'; args.append(state)
        q += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    def add_item(self, order_id, book_code, book_rfid):
        c = self._conn()
        cur = c.execute('INSERT INTO locker_order_item(order_id,book_code,'
                        'book_rfid) VALUES(?,?,?)', (order_id, book_code, book_rfid))
        c.commit()
        return cur.lastrowid

    def list_items(self, order_id):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM locker_order_item WHERE order_id=? ORDER BY id',
            (order_id,)).fetchall()]

    def set_item_processed(self, order_id, book_code):
        c = self._conn()
        c.execute('UPDATE locker_order_item SET processed=1 WHERE order_id=? AND '
                  'book_code=?', (order_id, book_code))
        c.commit()


class LockerService:
    """Жизненный цикл locker-заказа + ячейки; выдача/устройства — через сиды."""

    def __init__(self, store=None, circulation=None, devices=None, holds=None,
                 now=None):
        self.store = store or LockerStore()
        self.circulation = circulation
        self.devices = devices
        self.holds = holds
        self._now = now or time.time

    # -- lifecycle ---------------------------------------------------------- #
    def create(self, reader_ticket, safekeeper_id, reader_fio=None):
        return self.store.add_order(reader_ticket, reader_fio, safekeeper_id)

    def add_book(self, order_id, book_code, book_rfid=None):
        o = self._require(order_id)
        if o['state'] not in (CREATED, PREPARED):
            raise LockerError('order %d not fillable (state=%d)' % (order_id, o['state']))
        self.store.add_item(order_id, book_code, book_rfid)
        if o['state'] == CREATED:
            o = self.store.update_order(order_id, state=PREPARED)
        return o

    def staff(self, order_id, cell_no, staffed_by=None, master_rfid=None):
        """Укомплектовать (PREPARED→STAFFED): занять свободную ячейку."""
        o = self._require(order_id)
        if o['state'] != PREPARED:
            raise LockerError('order %d not preparable (state=%d)' % (order_id, o['state']))
        if cell_no in self.busy_cells(o['safekeeper']):
            raise LockerError('cell %s busy on safekeeper %s' % (cell_no, o['safekeeper']))
        o = self.store.update_order(order_id, state=STAFFED, cell_no=cell_no,
                                    staffed_by=staffed_by, master_rfid=master_rfid)
        self._event(o, 'order_staffed', 'cell=%s' % cell_no)
        return o

    def issue(self, order_id):
        """Выдать (STAFFED→ISSUED): списать книги через circulation; ошибка→ISSUED_ERROR."""
        o = self._require(order_id)
        if o['state'] != STAFFED:
            raise LockerError('order %d not issuable (state=%d)' % (order_id, o['state']))
        err = None
        if self.circulation is not None:
            for it in self.store.list_items(order_id):
                code = it['book_code']
                try:
                    res = self.circulation.checkout(o['reader_ticket'], code)
                    ok = getattr(res, 'allow', None)
                    ok = bool(res) if ok is None else ok
                except Exception as e:  # pragma: no cover - seam guard
                    ok = False
                    err = str(e)
                if ok:
                    self.store.set_item_processed(order_id, code)
                else:
                    err = err or ('checkout denied: %s' % code)
        new_state = ISSUED if err is None else ISSUED_ERROR
        o = self.store.update_order(order_id, state=new_state, abis_error=err)
        self._event(o, 'order_issued' if err is None else 'order_issued_error', err)
        return o

    def cancel(self, order_id):
        o = self._require(order_id)
        if o['state'] in (ISSUED, CANCELLED):
            raise LockerError('order %d not cancellable (state=%d)' % (order_id, o['state']))
        o = self.store.update_order(order_id, state=CANCELLED)
        self._event(o, 'order_cancelled', None)
        return o

    # -- cells -------------------------------------------------------------- #
    def busy_cells(self, safekeeper_id):
        cells = set()
        for o in self.store.list_orders(safekeeper=safekeeper_id):
            if o['state'] in OCCUPYING_STATES and o['cell_no'] is not None:
                cells.add(o['cell_no'])
        return cells

    def cells_state(self, safekeeper_id):
        """Битовая маска занятости (бит ``cell_no-1`` = занято) — формат наружу
        для legacy-клиентов (compat-шим). 1-based ячейки → 0-based биты."""
        mask = 0
        for cell in self.busy_cells(safekeeper_id):
            if cell and cell > 0:
                mask |= (1 << (cell - 1))
        return mask

    def free_cells(self, safekeeper_id, capacity):
        busy = self.busy_cells(safekeeper_id)
        return [c for c in range(1, capacity + 1) if c not in busy]

    def allocate_cell(self, safekeeper_id, capacity):
        free = self.free_cells(safekeeper_id, capacity)
        if not free:
            raise LockerError('no free cells on safekeeper %s' % safekeeper_id)
        return free[0]

    # -- service (master key) ----------------------------------------------- #
    def service_open(self, safekeeper_id, cell_no, master_rfid):
        """Сервисное открытие ячейки мастер-ключом (валидация через devices-сид)."""
        if self.devices is not None and not self.devices.is_master_valid(
                master_rfid, safekeeper_id):
            raise LockerError('invalid master key for safekeeper %s' % safekeeper_id)
        if self.devices is not None:
            self.devices.record_event(safekeeper_id, event_name='service_open',
                                      message='cell=%s' % cell_no,
                                      user_code=master_rfid)
        return True

    # -- views -------------------------------------------------------------- #
    def get(self, order_id):
        o = self.store.get_order(order_id)
        if o is None:
            return None
        o = dict(o)
        o['items'] = self.store.list_items(order_id)
        o['cell_shifted'] = (o['cell_no'] - o['cell_shift']) if o['cell_no'] is not None else None
        return o

    def list_for_reader(self, reader_ticket):
        return self.store.list_orders(reader_ticket=reader_ticket)

    def list_for_safekeeper(self, safekeeper_id):
        return self.store.list_orders(safekeeper=safekeeper_id)

    # -- internals ---------------------------------------------------------- #
    def _require(self, order_id):
        o = self.store.get_order(order_id)
        if o is None:
            raise LockerError('no locker order id=%r' % (order_id,))
        return o

    def _event(self, order, name, message):
        if self.devices is None:
            return
        try:
            self.devices.record_event(order['safekeeper'], event_name=name,
                                      message=message,
                                      user_code=order['reader_ticket'],
                                      hold_ref=order['id'])
        except Exception:  # pragma: no cover - seam guard
            pass
