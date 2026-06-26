# Спецификация домена `devices` (1/3)

> Новый нативный домен Biblio для парка устройств — по образцу `acquisition`/`circulation`. Каноничная рамка: [DEVICES_NATIVE_ARCHITECTURE.md](../DEVICES_NATIVE_ARCHITECTURE.md) (#272). Это **единственный по‑настоящему новый домен** (остальное — переиспользование circulation/catalog/holds/own‑store).
> Связанные спеки: [COMPAT_ADAPTER_CONTRACT.md](COMPAT_ADAPTER_CONTRACT.md) (2/3), [SAFEKEEPER_HOLDS_MAPPING.md](SAFEKEEPER_HOLDS_MAPPING.md) (3/3).

## 1. Размещение и конвенции (как у acquisition/circulation)
- **Модуль:** `irbis-web/backend/access/devices.py` — `DeviceStore` (sqlite, create‑on‑init, dev‑паритет ADR‑004) + `DeviceService` (операции; чистая доменная логика над стором, без сетевого I/O). По образцу `access/acquisition.py`, `access/circulation.py`.
- **Схема прод:** `irbis-web/backend/access/schema_devices.sql` (Postgres‑зеркало inline‑sqlite схемы; новый файл, не трогает `schema_postgres.sql`). По образцу `schema_acquisition.sql`.
- **Гранты:** через access‑store `grant_entry(function, db, level)` — функции `devices.read` (мониторинг), `devices.admin` (CRUD устройств/баннеров), `devices.service` (сервисные операции/мастер‑ключи). Проверка — существующий `access/authz.py`/`rights.py`.
- **Аудит:** доменные события (`device_event`) + центральный audit‑log access‑стора. Перечень типов — `ExternalLogTypes` (32 шт., [LAS_FUNCTION_MAP.md](../LAS_FUNCTION_MAP.md) §3) как справочник, моделируем по своим правилам (НЕ копия БД IDlogic).
- **Сидинг:** `seed.py`/`seed_vocab.py` — типы устройств, направления СКУД, типы событий.

## 2. Сущности (schema_devices.sql)

```sql
-- Реестр устройств (MON_Device/MON_Station/SK_SafeKeeper/MON_Gate → единая таблица)
CREATE TABLE device (
  id          BIGSERIAL PRIMARY KEY,
  guid        UUID UNIQUE,                 -- DeviceID (cfg3) / Station/SafeKeeper ID
  kind        TEXT NOT NULL,               -- 'desktop_reader'|'gate'|'station'|'safekeeper'|'smartshelf'|'acs_reader'|'camera'
  type_id     INT, type_name TEXT,
  name        TEXT,
  library     TEXT,                        -- сигла/МХ (связь с own-store)
  ip          TEXT, port INT,              -- SK_SafeKeeper.IPAddress / counter / camera
  is_online   INT NOT NULL DEFAULT 0,
  last_seen   DOUBLE PRECISION,
  cfg         TEXT, cfg2 TEXT,             -- выгрузка конфигурации считывателя
  created     DOUBLE PRECISION NOT NULL,
  updated     DOUBLE PRECISION NOT NULL
);
-- Здоровье/метрики (DeviceDataAdd → почасовая исправность)
CREATE TABLE device_health (
  id          BIGSERIAL PRIMARY KEY,
  device      BIGINT NOT NULL REFERENCES device(id) ON DELETE CASCADE,
  ts          DOUBLE PRECISION NOT NULL,
  hour        INT,
  soft_online INT, ok_count INT, error_count INT,
  state_id    INT                          -- derived: 1 неизв/2 исправно/3 диагностика/4 не настроено
);
-- Журнал событий устройства (MON_StationData/EventTypeID + ExternalLog)
CREATE TABLE device_event (
  id          BIGSERIAL PRIMARY KEY,
  device      BIGINT REFERENCES device(id) ON DELETE CASCADE,
  ts          DOUBLE PRECISION NOT NULL,
  type_id     INT,                          -- EventTypeID (категория) / ExternalLogTypes
  event_name  TEXT, message TEXT,
  user_code   TEXT,                         -- билет/RFID, если применимо
  loan_ref    BIGINT,                       -- связь с circulation (выдача/возврат на устройстве)
  hold_ref    BIGINT                        -- связь с holds (locker-заказ)
);
-- Противокражные срабатывания (MON_GateEASEvent)
CREATE TABLE gate_event (
  id BIGSERIAL PRIMARY KEY, device BIGINT REFERENCES device(id),
  ts DOUBLE PRECISION NOT NULL, uid TEXT, book_code TEXT, book_name TEXT, is_book INT
);
-- Счётчик посетителей (MON_GateCounter / камеры)
CREATE TABLE visitor_count (
  id BIGSERIAL PRIMARY KEY, device BIGINT REFERENCES device(id),
  ts DOUBLE PRECISION NOT NULL, value_in INT, value_out INT
);
-- Умные полки (SS_BookOnShelf) — текущая инвентаризация
CREATE TABLE shelf_item (
  id BIGSERIAL PRIMARY KEY, device BIGINT REFERENCES device(id),
  ts DOUBLE PRECISION NOT NULL, book_code TEXT, book_name TEXT, count_takes INT
);
-- СКУД (ACS_Event) — проход
CREATE TABLE acs_event (
  id BIGSERIAL PRIMARY KEY, device BIGINT REFERENCES device(id),
  ts DOUBLE PRECISION NOT NULL, rfid_code TEXT, client_name TEXT,
  direction INT, zone TEXT
);
-- Камеры FaceID (FD_Device/Camera) — параметры (Dahua)
CREATE TABLE camera (
  id BIGSERIAL PRIMARY KEY, device BIGINT REFERENCES device(id),
  ip TEXT, nvr_ip TEXT, port INT DEFAULT 37777, channel INT, login TEXT, secret_ref TEXT
);
-- Мастер-ключи SafeKeeper (SK_MasterRFID) — RFID-карта сотрудника
CREATE TABLE device_master_rfid (
  id BIGSERIAL PRIMARY KEY, rfid TEXT NOT NULL, fio TEXT,
  device BIGINT REFERENCES device(id),       -- привязка ключ↔камера (SafeKeeperMasterRFIDModify)
  is_deleted INT DEFAULT 0
);
-- Баннеры станций (MON_Banner) — афиша
CREATE TABLE station_banner (
  id BIGSERIAL PRIMARY KEY, name TEXT, image BYTEA, period_from DOUBLE PRECISION,
  period_to DOUBLE PRECISION, interval_sec INT, is_enabled INT DEFAULT 1
);
```
> Ячейки локеров живут НЕ здесь, а в holds (#222) — см. спеку 3/3 (заказ = бронь с pickup=ячейка). `device` лишь хранит safekeeper и его `ip`/тип.

## 3. Операции (`DeviceService`)
- `register(guid, kind, name, library, ip, cfg…)` / `modify` / `list(kind, library)` — реестр (CRUD), грант `devices.admin`.
- `heartbeat(guid, soft_online, ok, error)` — приём `DeviceDataAdd`: пишет `device_health`, derive `state_id`, обновляет `device.is_online/last_seen`.
- `record_event(device, type_id, name, message, user_code, loan_ref?, hold_ref?)` — события.
- `gate_alarm(device, uid, book_code…)` / `visitor(device, in, out)` / `shelf_sync(device, items[])` / `acs_pass(device, rfid, direction, zone)` — приём отчётов устройств.
- `masters(device)` / `master_modify(...)` — мастер‑ключи (грант `devices.service`).
- мониторинг/отчёты: `health_series(device, day)`, `info(kind, period)`, `events(device, period)` — гранты `devices.read`.
- Лицензия устройства: `is_license_valid(guid)` (наша модель лицензий, не схема IDlogic).

## 4. Связи с другими доменами (не дублируем)
- **circulation** — выдача/возврат, инициированные с устройства (станция/настольный), идут в circulation‑движок; `device_event.loan_ref` ссылается на loan.
- **holds (#222)** — locker‑заказы; `device_event.hold_ref`; ячейки/состояния — в holds (спека 3/3).
- **catalog (CatalogStore)** — статус экземпляра/RFID‑тег (910^A/H/B); устройства его читают/меняют через circulation/catalog, не через свою таблицу.
- **own‑store/RDR** — читатель/карты/фото (FaceID‑идентификация пишет фото в own‑store).

## 5. Что НЕ делаем
- Не копируем 106 DTO/151 операцию IDlogic как нашу БД/контракт — это вход для **compat‑шима** (спека 2/3), который транслирует в эти нативные операции.
- Не заводим параллельный «Device Service»‑силос — `devices` живёт рядом с circulation/holds в `access/`.
