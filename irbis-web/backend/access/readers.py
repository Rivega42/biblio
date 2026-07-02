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

    def find_by_rfid_ci(self, rfid_code):
        """Регистронезависимый поиск карты (#417): UID хранят по-разному
        (uppercase hex у RFID), резолв не должен зависеть от регистра."""
        r = self._conn().execute(
            'SELECT * FROM reader_card WHERE UPPER(rfid_code)=UPPER(?)',
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

    def resolve_patron(self, reader_role, uid):
        """Канонический резолв карты → один читатель (#417).

        ``reader_role`` — вид карты (``main``/``ekp``/``extra`` или BDP-роль),
        ``uid`` — сырой идентификатор (NFC-UID / UHF-EPC). UID нормализуется
        (uppercase, strip, БЕЗ усечения — усечение до 24 символов рождало коллизии
        личностей, см. bookcabinet C10). Возвращает
        ``{'status': 'ok'|'unknown'|'ambiguous', 'patron': billet|None, ...}``:
          * ``ok``        — ровно один читатель (карта в реестре или живой RDR);
          * ``unknown``   — карта не найдена → сценарий «гость» (публичный поиск,
                            циркуляция недоступна);
          * ``ambiguous`` — коллизия (живой RDR вернул >1 читателя) → в аудит,
                            обслуживать нельзя без разбора.
        """
        norm = (uid or '').strip().upper()
        if not norm:
            return {'status': 'unknown', 'patron': None, 'uid': ''}
        card = self.store.find_by_rfid_ci(norm)
        if card is not None:
            return {'status': 'ok', 'patron': card['abis_code'],
                    'kind': card['kind'], 'uid': norm}
        if self.rdr_lookup is not None:
            try:
                res = self.rdr_lookup(norm)
            except Exception:  # pragma: no cover - seam guard
                res = None
            if res:
                if isinstance(res, (list, tuple, set)):
                    distinct = sorted({str(x) for x in res if x})
                    if len(distinct) > 1:
                        return {'status': 'ambiguous', 'patron': None,
                                'candidates': distinct, 'uid': norm}
                    if len(distinct) == 1:
                        return {'status': 'ok', 'patron': distinct[0],
                                'kind': reader_role, 'uid': norm}
                else:
                    return {'status': 'ok', 'patron': str(res),
                            'kind': reader_role, 'uid': norm}
        return {'status': 'unknown', 'patron': None, 'uid': norm}

    # kind карты → поле RDR (источник истины карт в ИРБИС)
    KIND_FIELD = {KIND_MAIN: '30', KIND_EXTRA: '24', KIND_EKP: '28'}

    def rdr_sync_plan(self, abis_code):
        """DRY-RUN: какие правки RDR-полей (30/24/28) НУЖНО внести в живой ИРБИС,
        чтобы привязки own-реестра отразились в RDR читателя. Сам ИРБИС НЕ пишем
        (#222) — это план для явной админ-синхронизации/экспорта.

        Возврат: список ``{'field','value','kind','op':'set'}`` по картам читателя."""
        plan = []
        for c in self.store.list_for(abis_code):
            field = self.KIND_FIELD.get(c['kind'], '30')
            plan.append({'field': field, 'value': c['rfid_code'],
                         'kind': c['kind'], 'op': 'set'})
        return plan
