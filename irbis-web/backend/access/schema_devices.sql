-- Devices domain — PostgreSQL DDL mirror of devices.py's inline sqlite schema
-- (ADR-004: sqlite dev / Postgres prod). Узел #272 (DEVICES_NATIVE_ARCHITECTURE.md).
--
-- Нативный домен парка устройств Biblio (реестр/health/события/ворота/счётчик/
-- полки/СКУД/мастер-ключи/баннеры). НОВЫЙ файл — не трогает schema_postgres.sql.
-- НЕ копия БД IDlogic: реконструированный контракт IDlogic — лишь источник
-- требований. Ячейки локеров живут НЕ здесь, а в holds (#222) + locker_order
-- (SAFEKEEPER_HOLDS_MAPPING.md); device хранит лишь камеру и её ip/тип.

-- Реестр устройств (MON_Device/MON_Station/SK_SafeKeeper/MON_Gate → единая таблица).
CREATE TABLE IF NOT EXISTS device (
  id          BIGSERIAL PRIMARY KEY,
  guid        UUID UNIQUE,                       -- DeviceID (cfg3) / Station/SafeKeeper ID
  kind        TEXT NOT NULL                      -- вид устройства
                CHECK (kind IN ('desktop_reader','gate','station','safekeeper',
                                'smartshelf','acs_reader','camera',
                                'self_service_cabinet')),
  type_id     INTEGER, type_name TEXT,
  name        TEXT,
  library     TEXT,                              -- сигла/МХ (связь с own-store)
  tenant      TEXT NOT NULL DEFAULT 'public',    -- мультиарендная изоляция (#414)
  ip          TEXT, port INTEGER,                -- IPAddress / counter / camera
  is_online   INTEGER NOT NULL DEFAULT 0,
  last_seen   DOUBLE PRECISION,
  cfg         TEXT, cfg2 TEXT,                   -- выгрузка конфигурации считывателя
  is_deleted  INTEGER NOT NULL DEFAULT 0,
  created     DOUBLE PRECISION NOT NULL,
  updated     DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS device_kind_idx ON device(kind) WHERE is_deleted=0;

-- Здоровье/метрики (вход DeviceDataAdd → почасовая исправность).
CREATE TABLE IF NOT EXISTS device_health (
  id          BIGSERIAL PRIMARY KEY,
  device      BIGINT NOT NULL REFERENCES device(id) ON DELETE CASCADE,
  ts          DOUBLE PRECISION NOT NULL,
  hour        INTEGER,
  soft_online INTEGER, ok_count INTEGER, error_count INTEGER,
  state_id    INTEGER                            -- derive: 1 неизв/2 ок/3 диагн/4 не настр
);
CREATE INDEX IF NOT EXISTS device_health_dev_idx ON device_health(device, ts);

-- Журнал событий устройства (MON_StationData/EventTypeID + ExternalLogTypes).
CREATE TABLE IF NOT EXISTS device_event (
  id          BIGSERIAL PRIMARY KEY,
  device      BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts          DOUBLE PRECISION NOT NULL,
  type_id     INTEGER,
  event_name  TEXT, message TEXT,
  user_code   TEXT,                              -- билет/RFID, если применимо
  loan_ref    BIGINT,                            -- связь с circulation
  hold_ref    BIGINT                             -- связь с holds (locker-заказ)
);
CREATE INDEX IF NOT EXISTS device_event_dev_idx ON device_event(device, ts);

-- Противокражные срабатывания (MON_GateEASEvent).
CREATE TABLE IF NOT EXISTS gate_event (
  id BIGSERIAL PRIMARY KEY,
  device BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts DOUBLE PRECISION NOT NULL, uid TEXT, book_code TEXT, book_name TEXT,
  is_book INTEGER
);

-- Счётчик посетителей (MON_GateCounter / камеры).
CREATE TABLE IF NOT EXISTS visitor_count (
  id BIGSERIAL PRIMARY KEY,
  device BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts DOUBLE PRECISION NOT NULL, value_in INTEGER, value_out INTEGER
);

-- Умные полки (SS_BookOnShelf) — текущая инвентаризация.
CREATE TABLE IF NOT EXISTS shelf_item (
  id BIGSERIAL PRIMARY KEY,
  device BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts DOUBLE PRECISION NOT NULL, book_code TEXT, book_name TEXT, count_takes INTEGER
);

-- СКУД (ACS_Event) — проход.
CREATE TABLE IF NOT EXISTS acs_event (
  id BIGSERIAL PRIMARY KEY,
  device BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts DOUBLE PRECISION NOT NULL, rfid_code TEXT, client_name TEXT,
  direction INTEGER, zone TEXT
);

-- Мастер-ключи SafeKeeper (SK_MasterRFID) — RFID-карта сотрудника.
CREATE TABLE IF NOT EXISTS device_master_rfid (
  id BIGSERIAL PRIMARY KEY,
  rfid TEXT NOT NULL, fio TEXT,
  device BIGINT REFERENCES device(id) ON DELETE CASCADE,
  is_deleted INTEGER NOT NULL DEFAULT 0
);

-- Баннеры станций (MON_Banner) — афиша.
CREATE TABLE IF NOT EXISTS station_banner (
  id BIGSERIAL PRIMARY KEY,
  name TEXT, image BYTEA, period_from DOUBLE PRECISION, period_to DOUBLE PRECISION,
  interval_sec INTEGER, is_enabled INTEGER NOT NULL DEFAULT 1
);

-- Ячейки робо-шкафа (self_service_cabinet) — зеркало физики (#414). Ячейка =
-- полка ФОНДА (не pickup-локер): книга живёт в ячейке; источник правды —
-- журнал агента на RPi, Biblio держит зеркало и сверяет inventory.run.
CREATE TABLE IF NOT EXISTS cabinet_cell (
  id       BIGSERIAL PRIMARY KEY,
  tenant   TEXT NOT NULL DEFAULT 'public',
  device   BIGINT NOT NULL REFERENCES device(id) ON DELETE CASCADE,
  row      TEXT NOT NULL,
  x        INTEGER NOT NULL,
  y        INTEGER NOT NULL,
  state    TEXT NOT NULL DEFAULT 'free'
       CHECK (state IN ('free','occupied','awaiting_extraction','blocked')),
  item     TEXT,
  epc      TEXT,
  updated  DOUBLE PRECISION NOT NULL,
  UNIQUE(device, row, x, y)
);
CREATE INDEX IF NOT EXISTS cabinet_cell_idx ON cabinet_cell(tenant, device, state);

-- Токены устройств (BDP-аутентификация, #413): хранится только sha256-хэш.
CREATE TABLE IF NOT EXISTS device_token (
  id         BIGSERIAL PRIMARY KEY,
  device     BIGINT NOT NULL REFERENCES device(id) ON DELETE CASCADE,
  tenant     TEXT NOT NULL DEFAULT 'public',
  token_hash TEXT NOT NULL UNIQUE,
  label      TEXT,
  created    DOUBLE PRECISION NOT NULL,
  expires    DOUBLE PRECISION,
  revoked    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS device_token_idx ON device_token(device, revoked);
