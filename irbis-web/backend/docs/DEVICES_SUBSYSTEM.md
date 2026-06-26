# Подсистема устройств (devices) — как устроена и как работает

> Живой документ по РЕАЛИЗАЦИИ подсистемы внешних устройств библиотеки в Biblio
> (RFID-считыватели, противокражные ворота, постаматы/SafeKeeper, умные полки,
> СКУД, камеры). Обновляется при каждом изменении кода.
> Архитектурное решение и рекон-первоисточник — `docs/devices/` (PR #265),
> план — issue #272. Код: слайсы 1–3 + шим — PR #277 (в `main`); HTTP-врезка +
> ABIS-порт сидов — ветка `feat/devices-abis-port`.

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

### `readers.py` — реестр карт читателей (ABIS-порт RFID↔билет)
- `ReaderStore` + `ReaderService`. Таблица `reader_card` (rfid_code PK → abis_code/serial/kind).
- `find_by_card(rfid)` → `{abis_code, rfid_code}` (own-реестр; опц. фолбэк в живой
  RDR через сид `rdr_lookup(code)->билет`); `bind_card(abis_code, rfid_code, serial, kind)`
  — идемпотентный upsert (ReaderModify с устройства). Kind↔поле RDR: main→30/extra→24/ekp→28.
- Источник истины карт в ИРБИС — RDR 30/24/28; здесь СВОЙ реестр привязок (живой
  ИРБИС не пишем, #222). Запись обратно в прод-RDR — отдельная интеграция позже.

### `tag_codec.py` — кодек метки RFID (ISO 28560-2)
- Чистый stdlib-кодек данных тега (из рекона, `docs/devices/TAG_DATA_MODEL.md`):
  `encode_element`/`decode_element` (precursor-байт: bit7 offset, биты6-4 compaction,
  биты3-0 relative-OID), `encode_block`/`decode_block` (round-trip набора элементов),
  `security_state(afi)` (AFI/EAS). Компакции 1 int / 2 hex / 3-5 5/6/7-bit / 6 octet /
  7 int-string. `OID_PRIMARY_ITEM_ID=1` (штрихкод). `TagCodecError` на битый блок.

### `reader_agent.py` — настольный считыватель (оркестрация через сиды)
- `ReaderAgentService(transport=None, codec=None)` — тонкая обвязка железа за
  ИНЪЕКТИРУЕМЫМИ сидами (без импортов, без сокетов, без БД): `transport`
  (`read_uid`/`read_block`/`write_block`/`set_eas`), `codec` (= `tag_codec`).
- `read_tag()`→`{uid,itemId,data}`; `program_tag(item_id)`→кодирует и пишет блок;
  `set_security(on)` (EAS); `issue_prepare`/`return_prepare` — **выдача→EAS off,
  возврат→EAS on** (метка снимается с охраны, когда книга уходит на руки; ворота
  ловят EAS-on вне зоны). На сервере transport=None (железо — на клиенте станции);
  кодек подключён общий `tag_codec`.

### `compat_devices.py` — device-facing compat-адаптер (тонкий шим)
- `CompatDevicesService.handle(endpoint, payload)` — переводит вызов устройства в
  нативный сервис. Своей БД нет; сиды: `devices` (обязат.), `readers` (own-store/RDR),
  `locker`, `circulation`, `holds`.
- `/easybookdll/*`: `IsServerAlive`, `LibraryInfoGet`, `ReaderInfoGet`/`ReaderModify`
  (через `readers`-сид, поля 28/30/24), `DeviceIsLicenseValid`,
  `DeviceDataAdd`→`devices.heartbeat`, `BooksCacheAddUpdate`.
- **IAbis (роль A), реальная книговыдача** через `circulation`-сид (`_DeviceCircAdapter`):
  `Checkout`/`Checkin`/`Renew` (билет — явный `abisCode` ИЛИ резолв RFID-карты через
  `readers`), `GetClientChargedDocs` (выданные экземпляры = карточки поля 40),
  `GetDocState` (910^A экземпляра). Результат Decision сводится к `{Success, Reasons, Due}`.
- **Кодек тега** через `codec`-сид: `TagDecode` (hex-блок → `{ItemId, Data}`),
  `TagEncode` (`itemId` → hex-блок). Битый блок → `ItemId: null`.
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
### HTTP-врезка в `core.Api` (готово)
Шим подключён к боевому диспетчеру `core.Api`:
- **Маршрут:** `POST /api/devices/<endpoint>` → `Api._device_compat` → `CompatDevicesService.handle`.
- **Аутентификация:** унаследованный Basic `ServiceLogin` (env `EASYBOOK_LEGACY_PASS`,
  compat-режим); без него подсистема закрыта (401). Это и есть бесшовный подхват
  существующих устройств IDlogic; в проде — TLS+токены поверх.
- **Подключение движков** (`Api.__init__`, best-effort, env-DB-пути): `self.devices`
  (DEVICES_DB), `self.readers` (READERS_DB), `self.locker` (LOCKER_DB),
  `self.compat_devices`.
- **Реальная книговыдача:** `_DeviceCircAdapter(api)` — склейка device-сидов с боевым
  `CirculationEngine`: `checkout`/`checkin`(`return_item` по `_circ_find_loan`)/`renew`/
  `loans`(`loans_on_hand`→`_loan_card`)/`doc_state`(`catalog.exemplar_status`). Ленивая
  регистрация читателя `_circ_reader` + clock `_circ_today`; locker/IAbis читают
  `Decision.ok/.reasons`. Тот же engine и каталог 910^A, что АРМ выдачи — никакой
  второй книговыдачи.

## 4. Тесты

```
py -3.12 tests/test_devices.py         # 36 — домен devices
py -3.12 tests/test_locker.py          # 33 — locker-заказы/ячейки
py -3.12 tests/test_readers.py         # 15 — реестр карт RFID↔билет
py -3.12 tests/test_tag_codec.py       # 24 — кодек тега ISO 28560-2
py -3.12 tests/test_reader_agent.py    # 26 — настольный считыватель (сиды)
py -3.12 tests/test_tag_integration.py #  8 — reader_agent ↔ tag_codec (реальные модули)
py -3.12 tests/test_compat_devices.py  # 61 — шим (станц. + IAbis + tag-кодек)
py -3.12 tests/test_device_routes.py   # 19 — HTTP /api/devices/* (e2e Checkout→Checkin, Tag round-trip)
```
Всего 222, in-memory, без DB-сервера. Стиль `test_acquisition.py`/`test_circ_routes.py`
(standalone + счётчик). Route-тесты гоняют через `Api.route` с Basic `ServiceLogin`;
e2e `test_iabis_checkout_e2e` крутит реальный circulation + каталожный 910^A по HTTP.

## 5. Статус и что дальше
- Готово: домен `devices`, `locker` (SafeKeeper→holds), compat-шим
  (`/easybookdll/*` + station-facing), **HTTP-врезка в `core.Api`** (POST
  `/api/devices/*`, Basic-аутентификация), **ABIS-порт** — `readers` (карты) +
  **IAbis-книговыдача** (Checkout/Checkin/Renew/GetClientChargedDocs/GetDocState)
  через `_DeviceCircAdapter` на боевом circulation + каталоге 910^A; **кодек тега**
  ISO 28560-2 (`tag_codec`) + **настольный считыватель** (`reader_agent`) + tag-эндпоинты.
- Дальше: остаток IAbis (SetBookState/GetUserDebts/GetBookCenz), запись карт
  обратно в прод-RDR (30/24/28), реальный транспорт считывателя (сокет к железу
  на клиенте станции), Фаза 2 (ворота/ТСД/камеры).
- Заблокировано (не код): физический привод ячеек реальных станций — нужен
  station-facing трейс/станционный билд (не перепрошивка), `docs/devices/OPEN_QUESTIONS.md` §1.

## 6. Безопасность
- Унаследованный device-facing Basic `ServiceLogin` принимается только в compat-режиме (пароль — из конфигурации, в коде нет). В проде — TLS + токены.
- Захардкоженные креды/ключи IDlogic НЕ воспроизводятся. Секретов в коде/доке нет.
