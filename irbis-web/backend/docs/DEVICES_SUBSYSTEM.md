# Подсистема устройств (devices) — как устроена и как работает

> Живой документ по РЕАЛИЗАЦИИ подсистемы внешних устройств библиотеки в Biblio
> (RFID-считыватели, противокражные ворота, постаматы/SafeKeeper, умные полки,
> СКУД, камеры). Обновляется при каждом изменении кода.
> Архитектурное решение и рекон-первоисточник — `docs/devices/` (PR #265),
> план — issue #272, код — ветка `feat/devices-domain` / PR #277.

## 1. Принцип (узел #272)

Устройства реализованы как **нативные домены Biblio**, НЕ как второй сервис-клон
`api.svc`/LAS поверх ИРБИС. Реконструированный контракт IDlogic (151 операция,
`/easybookdll/*`, заказы SafeKeeper, мониторинг, RFID/EAS) — это **спецификация
того, что ждут физические устройства**, а реализует её тонкий device-facing
**compat-адаптер**, который переводит вызовы устройств в нативные сервисы.

Карта «возможность IDlogic → домен Biblio»:
| IDlogic | Нативный домен |
|---|---|
| Checkout/Checkin/Renew | существующий `circulation` |
| Статус экземпляра / RFID-тег | `catalog` (910^A/H/B) |
| Поля читателя 30/24/28/103 | own-store / RDR |
| SafeKeeper-заказы / ячейки | **`locker`** поверх holds (#222) |
| Реестр устройств + health + события + ворота/EAS + счётчик + полки + СКУД + камеры + мастер-ключи | **`devices`** (новый домен) |

## 2. Модули (`irbis-web/backend/access/`)

Все — в домашнем идиоме (standalone, sqlite dev / Postgres prod ADR-004, чистая
доменная логика, инъектируемые сиды; см. `acquisition.py`/`circulation.py`).

### `devices.py` — домен парка устройств
- `DeviceStore` (sqlite) + `DeviceService` (операции). Схема прод — `schema_devices.sql`.
- Таблицы: `device` (реестр), `device_health` (метрики), `device_event` (журнал),
  `gate_event`, `visitor_count`, `shelf_item`, `acs_event`, `device_master_rfid`,
  `station_banner`.
- Ключевые операции `DeviceService`:
  - `register(guid, kind, …)` — идемпотентно по `guid`; `modify` / `remove` / `list` / `get`.
  - `heartbeat(guid, soft_online, ok, error)` — вход `DeviceDataAdd`: пишет
    `device_health`, считает `derive_state` (DeviceStateID 1 неизв/2 ок/3 диагн/4 не
    настроено), ставит `is_online`/`last_seen`.
  - `record_event` / `gate_alarm` / `visitor` / `shelf_sync` / `acs_pass` — приём отчётов.
  - `masters` / `master_modify` / `is_master_valid` — мастер-ключи SafeKeeper (скоуп по камере).
  - `info` (online + state_name), `is_license_valid` (наша модель лицензий).
- Авторизация (`devices.read/admin/service`) и центральный аудит — на слое
  маршрутов (как у `acquisition`); домен — чистая логика.

### `locker.py` — locker-заказы (постамат/SafeKeeper) поверх holds (#222)
- `LockerStore` + `LockerService`. Заказ = бронь читателя с pickup-местом = ячейка.
- Таблицы: `locker_order` (companion к брони), `locker_order_item`.
- Состояния: `CREATED(1)→PREPARED(2)→STAFFED(3, ячейка занята)→ISSUED(4)`;
  `CANCELLED(5)`, `ISSUED_ERROR(6)`.
- Жизненный цикл `LockerService`:
  - `create(ticket, safekeeper_id)` → 1; `add_book(order, code, rfid)` → 2;
  - `staff(order, cell_no)` → 3, занимает свободную ячейку (занятую → `LockerError`);
  - `issue(order)` → выдача через сид `circulation.checkout(ticket, code)`; все ок → 4
    (ячейка освобождается), любая ошибка → 6 + `abis_error`; без сида — standalone (4, без loan);
  - `cancel(order)` → 5, ячейка освобождается.
  - Ячейки: `busy_cells` / `cells_state` (битмаска: бит `cell_no-1`) / `free_cells` / `allocate_cell`.
  - `service_open(sk, cell, master_rfid)` — сервисное открытие мастер-ключом (валидация через сид `devices`) + событие.
- Сиды (опц., как `catalog=` в acquisition): `circulation` (выдача), `devices`
  (мастер-ключ + события), `holds` (зеркало брони #222).

### `compat_devices.py` — device-facing compat-адаптер (тонкий шим)
- `CompatDevicesService.handle(endpoint, payload)` — переводит вызов устройства в
  нативный сервис. Своей БД нет; сиды: `devices` (обязат.), `readers` (own-store/RDR),
  `locker`, `circulation`, `holds`.
- `/easybookdll/*`: `IsServerAlive`, `LibraryInfoGet`, `ReaderInfoGet`/`ReaderModify`
  (через `readers`-сид, поля 28/30/24), `DeviceIsLicenseValid`,
  `DeviceDataAdd`→`devices.heartbeat`, `BooksCacheAddUpdate`.
- station-facing: `MastersRFIDGet`/`SafeKeeperMasterRFIDModify` → `devices`;
  `OrdersGet`/`SafeKeeperInfoGet2`(CellsState наружу)/`OrderBookProcessedSet`/
  `OrderModify`(opID/stateID→create/staff/issue/cancel) → `locker`.
- `authorize(auth_header)` — whitelist унаследованного Basic `ServiceLogin` ТОЛЬКО
  при заданном `legacy_pass` (compat-режим; пароль из конфига, не в коде). Это путь
  бесшовного подхвата существующих устройств IDlogic; в проде — TLS+токены.

## 3. Поток (как работает «по проводу»)

```
Устройство/агент IDlogic ──HTTP(Basic legacy)──▶ compat_devices (шим)
   ├─ DeviceDataAdd        ──▶ devices.heartbeat        (health/online)
   ├─ ReaderInfoGet/Modify ──▶ readers (own-store/RDR)  (карты 28/30/24)
   ├─ OrdersGet/OrderModify──▶ locker (заказы/ячейки)   (1→2→3→4/6)
   │     └─ issue           ──▶ circulation.checkout    (loan + 910^A)
   └─ Masters*              ──▶ devices (мастер-ключи)
```
HTTP-врезка шима в `core.Api.route` (как у других доменов) — отдельный тонкий
слой (TODO след. шага); сейчас транслятор покрыт юнит-тестами напрямую.

## 4. Тесты

```
py -3.12 tests/test_devices.py         # 36 — домен devices
py -3.12 tests/test_locker.py          # 33 — locker-заказы/ячейки
py -3.12 tests/test_compat_devices.py  # 43 — шим (включая station-facing)
```
Всего 112, in-memory, без DB-сервера. Стиль `test_acquisition.py` (standalone + счётчик).

## 5. Статус и что дальше
- Готово: домен `devices`, `locker` (SafeKeeper→holds), compat-шим (`/easybookdll/*` + station-facing).
- Дальше: HTTP-врезка шима в `core.Api.route`; ABIS-порт `IAbis` (книговыдача/
  регистрация — `circulation`/own-store backend); Reader Agent (настольный считыватель).
- Заблокировано (не код): физический привод ячеек реальных станций — нужен
  station-facing трейс/станционный билд (не перепрошивка), `docs/devices/OPEN_QUESTIONS.md` §1.

## 6. Безопасность
- Унаследованный device-facing Basic `ServiceLogin` принимается только в compat-режиме (пароль — из конфигурации, в коде нет). В проде — TLS + токены.
- Захардкоженные креды/ключи IDlogic НЕ воспроизводятся. Секретов в коде/доке нет.
