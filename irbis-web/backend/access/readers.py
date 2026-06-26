#!/usr/bin/env python3
"""Reader card registry (RFID↔билет) — ABIS-порт для device-flows (#272).

Устройствам нужно по RFID-карте получить «абонентский код» (билет, RDR^30) и
наоборот привязать карту к билету (ReaderModify с устройства). Источник истины
карт в ИРБИС — RDR-поля 30 (осн. билет) / 24 (доп. карта) / 28 (ЕКП). В Biblio
держим СВОЙ реестр привязок (own-store, posture #222 — живой ИРБИС не пишем):
устройство «учит» нас привязке через ReaderModify, дальше ReaderInfoGet резолвит
карту локально. Для уже существующих читателей опц. сид ``rdr_lookup(code)->билет``
даёт фолбэк в живой RDR (RI=/поиск по карте).

Сиды compat-шима (``readers=`` в compat_devices.py):
  * ``find_by_card(rfid_code) -> {'abis_code','rfid_code'} | None``
  * ``bind_card(abis_code, rfid_code, serial=, kind=) -> bool``

Kind ↔ поле RDR: main→30, extra→24, ekp→28 (см. CARD_KIND_* в compat_devices).
"""
import threading
import time

KIND_MAIN = 'main'    # RDR^30
KIND_EXTRA = 'extra'  # RDR^24
KIND_EKP = 'ekp'      # RDR^28

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS reader_card (
  rfid_code  TEXT PRIMARY KEY,
  abis_code  TEXT NOT NULL,
  serial     TEXT,
  kind       TEXT NOT NULL DEFAULT 'main',
  created    REAL NOT NULL,
  updated    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reader_card_abis_idx ON reader_card(abis_code);
"""


class ReaderError(Exception):
    """Доменная ошибка реестра карт читателей."""


class ReaderStore:
    """Собственный sqlite-стор привязок RFID→билет (не живой ИРБИС, #222)."""

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

    def find_by_rfid(self, rfid_code):
        r = self._conn().execute('SELECT * FROM reader_card WHERE rfid_code=?',
                                 (rfid_code,)).fetchone()
        return dict(r) if r else None

    def upsert(self, abis_code, rfid_code, serial=None, kind=KIND_MAIN):
        now = time.time()
        c = self._conn()
        c.execute(
            'INSERT INTO reader_card(rfid_code,abis_code,serial,kind,created,updated)'
            ' VALUES(?,?,?,?,?,?) ON CONFLICT(rfid_code) DO UPDATE SET '
            'abis_code=excluded.abis_code, serial=excluded.serial, '
            'kind=excluded.kind, updated=excluded.updated',
            (rfid_code, abis_code, serial, kind, now, now))
        c.commit()
        return self.find_by_rfid(rfid_code)

    def list_for(self, abis_code):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM reader_card WHERE abis_code=? ORDER BY kind, rfid_code',
            (abis_code,)).fetchall()]


class ReaderService:
    """ABIS-порт реестра карт читателей; опц. фолбэк в живой RDR через сид."""

    def __init__(self, store=None, rdr_lookup=None):
        self.store = store or ReaderStore()
        self.rdr_lookup = rdr_lookup  # опц.: callable(rfid_code) -> билет|None (живой RDR)

    def find_by_card(self, rfid_code):
        """Резолв RFID-карты → билет. Сначала own-реестр, затем (опц.) живой RDR."""
        if not rfid_code:
            return None
        r = self.store.find_by_rfid(rfid_code)
        if r:
            return {'abis_code': r['abis_code'], 'rfid_code': r['rfid_code']}
        if self.rdr_lookup is not None:
            try:
                ticket = self.rdr_lookup(rfid_code)
            except Exception:
                ticket = None
            if ticket:
                return {'abis_code': ticket, 'rfid_code': rfid_code}
        return None

    def bind_card(self, abis_code, rfid_code, serial=None, kind=KIND_MAIN):
        """Привязать RFID-карту к билету (ReaderModify с устройства). Идемпотентно."""
        if not abis_code or not rfid_code:
            return False
        self.store.upsert(abis_code, rfid_code, serial=serial, kind=kind or KIND_MAIN)
        return True

    def cards_for(self, abis_code):
        return self.store.list_for(abis_code)
