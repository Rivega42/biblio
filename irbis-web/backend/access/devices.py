#!/usr/bin/env python3
"""Devices domain — реестр парка устройств + health/события (нативный домен Biblio).

Узел #272 (DEVICES_NATIVE_ARCHITECTURE.md): всё, что в стеке IDlogic делал
центральный `api.svc`/LAS, реализуем как НОРМАЛЬНЫЕ домены Biblio. `devices` —
единственный по-настоящему НОВЫЙ домен (остальное — переиспользование
circulation/catalog/holds/own-store). Это НЕ копия БД IDlogic и НЕ второй
«Device Service»-силос — реконструированный контракт IDlogic лишь источник
требований; модель наша.

Что это
-------
Самодостаточный домен над собственным sqlite-стором (dev-паритет, ADR-004:
sqlite dev / Postgres prod — зеркало в ``schema_devices.sql``). Чистая доменная
логика, без сетевого I/O, без новых pip-зависимостей — в точности как
``acquisition.py``/``circulation.py``.

Сущности (см. DOMAIN_DEVICES_SPEC.md)
-------------------------------------
  * ``device``            — реестр (настольный считыватель / ворота / станция /
                            SafeKeeper / умная полка / СКУД-считыватель / камера);
  * ``device_health``     — почасовая исправность (вход ``DeviceDataAdd``);
  * ``device_event``      — журнал событий (EventTypeID / ExternalLogTypes), со
                            связями ``loan_ref`` (circulation) / ``hold_ref`` (holds);
  * ``gate_event``        — противокражные срабатывания (MON_GateEASEvent);
  * ``visitor_count``     — счётчик посетителей (MON_GateCounter / камеры);
  * ``shelf_item``        — текущая инвентаризация умной полки (SS_BookOnShelf);
  * ``acs_event``         — проход СКУД (ACS_Event);
  * ``device_master_rfid``— мастер-ключи SafeKeeper (SK_MasterRFID);
  * ``station_banner``    — афиша станций (MON_Banner).

Ячейки локеров здесь НЕ живут — это holds (#222) + ``locker_order``
(SAFEKEEPER_HOLDS_MAPPING.md). ``device`` хранит лишь камеру и её ip/тип.

Гранты/аудит
------------
Домен — чистая логика над своим стором (как acquisition.py): авторизацию
(`devices.read`/`devices.admin`/`devices.service`) и центральный audit-log
проставляет слой маршрутов (`server.py` + `access/authz.py`); сам домен пишет
доменные события в ``device_event``.
"""
import threading
import time

# --------------------------------------------------------------------------- #
# Константы — виды устройств, статусы здоровья, направления СКУД.
# --------------------------------------------------------------------------- #
KIND_DESKTOP = 'desktop_reader'
KIND_GATE = 'gate'
KIND_STATION = 'station'
KIND_SAFEKEEPER = 'safekeeper'
KIND_SMARTSHELF = 'smartshelf'
KIND_ACS = 'acs_reader'
KIND_CAMERA = 'camera'
KINDS = (KIND_DESKTOP, KIND_GATE, KIND_STATION, KIND_SAFEKEEPER,
         KIND_SMARTSHELF, KIND_ACS, KIND_CAMERA)

# Здоровье устройства (DeviceMonitoringPage: 1 Неизвестно / 2 Исправно /
# 3 Требует диагностики / 4 Не настроено). Точную формулу IDlogic строки не
# выдали — политика наша (документирована в derive_state), словарь — их.
STATE_UNKNOWN = 1
STATE_OK = 2
STATE_DIAG = 3
STATE_UNCONFIGURED = 4
STATE_NAMES = {STATE_UNKNOWN: 'Неизвестно', STATE_OK: 'Исправно',
               STATE_DIAG: 'Требует диагностики', STATE_UNCONFIGURED: 'Не настроено'}

# Направление прохода СКУД (acs_Directiontype).
DIR_IN = 1
DIR_OUT = 2

# Через сколько секунд без heartbeat устройство считается оффлайн.
ONLINE_TTL_SEC = 120


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS device (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  guid        TEXT UNIQUE,
  kind        TEXT NOT NULL,
  type_id     INTEGER, type_name TEXT,
  name        TEXT,
  library     TEXT,
  ip          TEXT, port INTEGER,
  is_online   INTEGER NOT NULL DEFAULT 0,
  last_seen   REAL,
  cfg         TEXT, cfg2 TEXT,
  is_deleted  INTEGER NOT NULL DEFAULT 0,
  created     REAL NOT NULL,
  updated     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS device_health (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  device      INTEGER NOT NULL REFERENCES device(id) ON DELETE CASCADE,
  ts          REAL NOT NULL,
  hour        INTEGER,
  soft_online INTEGER, ok_count INTEGER, error_count INTEGER,
  state_id    INTEGER
);
CREATE INDEX IF NOT EXISTS device_health_dev_idx ON device_health(device, ts);
CREATE TABLE IF NOT EXISTS device_event (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  device      INTEGER REFERENCES device(id) ON DELETE CASCADE,
  ts          REAL NOT NULL,
  type_id     INTEGER,
  event_name  TEXT, message TEXT,
  user_code   TEXT,
  loan_ref    INTEGER,
  hold_ref    INTEGER
);
CREATE INDEX IF NOT EXISTS device_event_dev_idx ON device_event(device, ts);
CREATE TABLE IF NOT EXISTS gate_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device INTEGER REFERENCES device(id) ON DELETE CASCADE,
  ts REAL NOT NULL, uid TEXT, book_code TEXT, book_name TEXT, is_book INTEGER
);
CREATE TABLE IF NOT EXISTS visitor_count (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device INTEGER REFERENCES device(id) ON DELETE CASCADE,
  ts REAL NOT NULL, value_in INTEGER, value_out INTEGER
);
CREATE TABLE IF NOT EXISTS shelf_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device INTEGER REFERENCES device(id) ON DELETE CASCADE,
  ts REAL NOT NULL, book_code TEXT, book_name TEXT, count_takes INTEGER
);
CREATE TABLE IF NOT EXISTS acs_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device INTEGER REFERENCES device(id) ON DELETE CASCADE,
  ts REAL NOT NULL, rfid_code TEXT, client_name TEXT, direction INTEGER, zone TEXT
);
CREATE TABLE IF NOT EXISTS device_master_rfid (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rfid TEXT NOT NULL, fio TEXT,
  device INTEGER REFERENCES device(id) ON DELETE CASCADE,
  is_deleted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS station_banner (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, image BLOB, period_from REAL, period_to REAL,
  interval_sec INTEGER, is_enabled INTEGER NOT NULL DEFAULT 1
);
"""


class DeviceError(Exception):
    """Доменная ошибка devices (неизвестный вид, нет устройства и т.п.)."""


class DeviceStore:
    """Собственный sqlite-стор домена devices (реестр/health/события/…).

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

    # ---- device CRUD ------------------------------------------------------ #
    def add_device(self, guid, kind, name, library, ip, port, type_id,
                   type_name, cfg, cfg2):
        now = time.time()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO device(guid,kind,name,library,ip,port,type_id,'
            'type_name,cfg,cfg2,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (guid, kind, name, library, ip, port, type_id, type_name, cfg, cfg2,
             now, now))
        c.commit()
        return self.get_device(cur.lastrowid)

    def get_device(self, device_id):
        r = self._conn().execute('SELECT * FROM device WHERE id=?',
                                 (device_id,)).fetchone()
        return dict(r) if r else None

    def get_by_guid(self, guid):
        r = self._conn().execute('SELECT * FROM device WHERE guid=?',
                                 (guid,)).fetchone()
        return dict(r) if r else None

    def update_device(self, device_id, **fields):
        if not fields:
            return self.get_device(device_id)
        fields['updated'] = time.time()
        cols = ', '.join('%s=?' % k for k in fields)
        c = self._conn()
        c.execute('UPDATE device SET %s WHERE id=?' % cols,
                  (*fields.values(), device_id))
        c.commit()
        return self.get_device(device_id)

    def list_devices(self, kind=None, library=None, include_deleted=False):
        q = 'SELECT * FROM device WHERE 1=1'
        args = []
        if not include_deleted:
            q += ' AND is_deleted=0'
        if kind is not None:
            q += ' AND kind=?'; args.append(kind)
        if library is not None:
            q += ' AND library=?'; args.append(library)
        q += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    # ---- health ----------------------------------------------------------- #
    def add_health(self, device, soft_online, ok_count, error_count, state_id,
                   ts=None, hour=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        c.execute('INSERT INTO device_health(device,ts,hour,soft_online,'
                  'ok_count,error_count,state_id) VALUES(?,?,?,?,?,?,?)',
                  (device, ts, hour, soft_online, ok_count, error_count, state_id))
        c.commit()

    def health_series(self, device, since=None):
        q = 'SELECT * FROM device_health WHERE device=?'
        args = [device]
        if since is not None:
            q += ' AND ts>=?'; args.append(since)
        q += ' ORDER BY ts'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    # ---- events ----------------------------------------------------------- #
    def add_event(self, device, type_id, event_name, message, user_code,
                  loan_ref, hold_ref, ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        cur = c.execute(
            'INSERT INTO device_event(device,ts,type_id,event_name,message,'
            'user_code,loan_ref,hold_ref) VALUES(?,?,?,?,?,?,?,?)',
            (device, ts, type_id, event_name, message, user_code, loan_ref,
             hold_ref))
        c.commit()
        return cur.lastrowid

    def list_events(self, device=None, since=None):
        q = 'SELECT * FROM device_event WHERE 1=1'
        args = []
        if device is not None:
            q += ' AND device=?'; args.append(device)
        if since is not None:
            q += ' AND ts>=?'; args.append(since)
        q += ' ORDER BY ts, id'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    # ---- gate / visitor / shelf / acs ------------------------------------- #
    def add_gate_event(self, device, uid, book_code, book_name, is_book, ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        c.execute('INSERT INTO gate_event(device,ts,uid,book_code,book_name,'
                  'is_book) VALUES(?,?,?,?,?,?)',
                  (device, ts, uid, book_code, book_name, is_book))
        c.commit()

    def add_visitor(self, device, value_in, value_out, ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        c.execute('INSERT INTO visitor_count(device,ts,value_in,value_out) '
                  'VALUES(?,?,?,?)', (device, ts, value_in, value_out))
        c.commit()

    def replace_shelf(self, device, items, ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        c.execute('DELETE FROM shelf_item WHERE device=?', (device,))
        for it in items:
            c.execute('INSERT INTO shelf_item(device,ts,book_code,book_name,'
                      'count_takes) VALUES(?,?,?,?,?)',
                      (device, ts, it.get('book_code'), it.get('book_name'),
                       it.get('count_takes', 0)))
        c.commit()

    def list_shelf(self, device):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM shelf_item WHERE device=? ORDER BY id',
            (device,)).fetchall()]

    def add_acs_event(self, device, rfid_code, client_name, direction, zone,
                      ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        c.execute('INSERT INTO acs_event(device,ts,rfid_code,client_name,'
                  'direction,zone) VALUES(?,?,?,?,?,?)',
                  (device, ts, rfid_code, client_name, direction, zone))
        c.commit()

    # ---- master-rfid ------------------------------------------------------ #
    def add_master(self, rfid, fio, device):
        c = self._conn()
        cur = c.execute('INSERT INTO device_master_rfid(rfid,fio,device) '
                        'VALUES(?,?,?)', (rfid, fio, device))
        c.commit()
        return cur.lastrowid

    def list_masters(self, device=None):
        if device is None:
            rows = self._conn().execute(
                'SELECT * FROM device_master_rfid WHERE is_deleted=0 '
                'ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM device_master_rfid WHERE is_deleted=0 AND '
                'device=? ORDER BY id', (device,)).fetchall()
        return [dict(r) for r in rows]


class DeviceService:
    """Операции домена устройств над :class:`DeviceStore`.

    Авторизация/аудит — на слое маршрутов; здесь — чистая доменная логика.
    """

    def __init__(self, store=None, now=None):
        self.store = store or DeviceStore()
        self._now = now or time.time

    # -- derive ------------------------------------------------------------- #
    @staticmethod
    def derive_state(soft_online, ok_count, error_count):
        """Свести метрики ``DeviceDataAdd`` к DeviceStateID (1..4).

        Политика наша (точную IDlogic строки не выдали; словарь — их):
          * soft_online==0  → 4 «Не настроено» (агент не на связи);
          * есть ошибки и нет ОК → 3 «Требует диагностики»;
          * есть ОК           → 2 «Исправно»;
          * иначе             → 1 «Неизвестно».
        """
        if not soft_online:
            return STATE_UNCONFIGURED
        if (error_count or 0) > 0 and not (ok_count or 0):
            return STATE_DIAG
        if (ok_count or 0) > 0:
            return STATE_OK
        return STATE_UNKNOWN

    # -- registry ----------------------------------------------------------- #
    def register(self, guid, kind, name=None, library=None, ip=None, port=None,
                 type_id=None, type_name=None, cfg=None, cfg2=None):
        if kind not in KINDS:
            raise DeviceError('unknown device kind: %r' % (kind,))
        existing = self.store.get_by_guid(guid) if guid else None
        if existing:
            return self.store.update_device(
                existing['id'], kind=kind, name=name, library=library, ip=ip,
                port=port, type_id=type_id, type_name=type_name, cfg=cfg,
                cfg2=cfg2, is_deleted=0)
        return self.store.add_device(guid, kind, name, library, ip, port,
                                     type_id, type_name, cfg, cfg2)

    def modify(self, device_id, **fields):
        if self.store.get_device(device_id) is None:
            raise DeviceError('no device id=%r' % (device_id,))
        return self.store.update_device(device_id, **fields)

    def remove(self, device_id):
        return self.store.update_device(device_id, is_deleted=1)

    def list(self, kind=None, library=None):
        return self.store.list_devices(kind=kind, library=library)

    def get(self, guid):
        return self.store.get_by_guid(guid)

    # -- heartbeat / health (вход DeviceDataAdd) ---------------------------- #
    def heartbeat(self, guid, soft_online=1, ok_count=0, error_count=0):
        dev = self.store.get_by_guid(guid)
        if dev is None:
            raise DeviceError('unknown device guid=%r' % (guid,))
        now = self._now()
        state_id = self.derive_state(soft_online, ok_count, error_count)
        hour = int((now // 3600) % 24)
        self.store.add_health(dev['id'], soft_online, ok_count, error_count,
                              state_id, ts=now, hour=hour)
        self.store.update_device(dev['id'], is_online=1, last_seen=now)
        return state_id

    def is_online(self, device):
        last = device.get('last_seen') if isinstance(device, dict) else None
        return bool(last and (self._now() - last) <= ONLINE_TTL_SEC)

    def health_series(self, device_id, day_start=None):
        return self.store.health_series(device_id, since=day_start)

    # -- events / sensors --------------------------------------------------- #
    def record_event(self, device_id, type_id=None, event_name=None,
                     message=None, user_code=None, loan_ref=None, hold_ref=None):
        return self.store.add_event(device_id, type_id, event_name, message,
                                    user_code, loan_ref, hold_ref)

    def gate_alarm(self, device_id, uid=None, book_code=None, book_name=None,
                   is_book=1):
        self.store.add_gate_event(device_id, uid, book_code, book_name, is_book)
        self.store.add_event(device_id, None, 'gate_eas', book_code, uid, None,
                             None)

    def visitor(self, device_id, value_in=0, value_out=0):
        self.store.add_visitor(device_id, value_in, value_out)

    def shelf_sync(self, device_id, items):
        self.store.replace_shelf(device_id, items)

    def acs_pass(self, device_id, rfid_code, client_name=None, direction=DIR_IN,
                 zone=None):
        self.store.add_acs_event(device_id, rfid_code, client_name, direction,
                                 zone)

    def events(self, device_id=None, since=None):
        return self.store.list_events(device=device_id, since=since)

    # -- master-rfid (SafeKeeper) ------------------------------------------- #
    def masters(self, device_id=None):
        return self.store.list_masters(device=device_id)

    def master_modify(self, rfid, fio=None, device_id=None):
        return self.store.add_master(rfid, fio, device_id)

    def is_master_valid(self, rfid, device_id):
        for m in self.store.list_masters(device=device_id):
            if m['rfid'] == rfid:
                return True
        return False

    # -- monitoring info ---------------------------------------------------- #
    def info(self, kind=None, library=None):
        out = []
        for d in self.store.list_devices(kind=kind, library=library):
            d = dict(d)
            d['online'] = self.is_online(d)
            d['state_name'] = STATE_NAMES.get(
                (self.store.health_series(d['id']) or [{}])[-1].get('state_id'),
                STATE_NAMES[STATE_UNKNOWN])
            out.append(d)
        return out

    # -- license ------------------------------------------------------------ #
    def is_license_valid(self, guid):
        """Наша модель лицензий (НЕ схема IDlogic). Слайс: устройство
        зарегистрировано и не удалено ⇒ валидно. Реальную политику заведём
        отдельно."""
        dev = self.store.get_by_guid(guid)
        return bool(dev and not dev.get('is_deleted'))
