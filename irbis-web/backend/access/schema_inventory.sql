-- Inventory domain — PostgreSQL DDL mirror of inventory.py's inline sqlite schema
-- (ADR-004: sqlite dev / Postgres prod). Узел #272 / Фаза 2
-- (BIBLIO_DEVICE_INTEGRATION_DESIGN.md §5.2).
--
-- Фондовая инвентаризация (stocktake) ручным RFID-ТСД (Android UHF-терминал):
-- сессия инвентаризации на месте хранения + идемпотентные сканы меток; сверка
-- с каталогом строится в сервисе (seam), не в БД. НОВЫЙ файл — не трогает
-- schema_postgres.sql / schema_devices.sql.

-- Сессия инвентаризации (открыта оператором на месте хранения, потом закрыта).
CREATE TABLE IF NOT EXISTS stocktake (
  id        BIGSERIAL PRIMARY KEY,
  db        TEXT,                                  -- база/каталог (контекст сверки)
  location  TEXT,                                  -- место хранения (полка/стеллаж/МХ)
  status    TEXT NOT NULL DEFAULT 'open'           -- open | closed
              CHECK (status IN ('open','closed')),
  operator  TEXT,                                  -- кто проводит
  started   DOUBLE PRECISION,
  finished  DOUBLE PRECISION,
  note      TEXT
);
CREATE INDEX IF NOT EXISTS stocktake_db_idx ON stocktake(db, location);

-- Скан метки в рамках сессии — идемпотентно по (session_id,item_code):
-- повторное чтение той же метки не плодит строк (UNIQUE + INSERT OR IGNORE / ON CONFLICT).
CREATE TABLE IF NOT EXISTS stocktake_scan (
  id         BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES stocktake(id) ON DELETE CASCADE,
  item_code  TEXT NOT NULL,                        -- инв.номер/штрихкод (декод EPC)
  rfid       TEXT,                                 -- сырой EPC/UID метки
  ts         DOUBLE PRECISION,
  UNIQUE(session_id, item_code)
);
CREATE INDEX IF NOT EXISTS stocktake_scan_sess_idx ON stocktake_scan(session_id);
