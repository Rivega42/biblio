# Подсистема внешних устройств Biblio — сводный хендофф

> Единый документ передачи по подсистеме внешних устройств (замена IDlogic-стека
> ИРБИС64+: RFID-считыватели, постаматы/SafeKeeper, станции самообслуживания,
> противокражные ворота, умные полки, СКУД, камеры/FaceID, ТСД).
> Реконструкция-первоисточник — `docs/devices/` (PR #265). Реализация — `main`
> (PR #277/#280/#283/#285/#287/#288/#289), issue плана #272. Дев-детали по модулям —
> [DEVICES_SUBSYSTEM.md](DEVICES_SUBSYSTEM.md).
>
> Статус: **функционально завершено в коде — 453 теста зелёных.** Остаток —
> железо/деплой/декомпиляция (см. §7 «Разблокировка»).

## 1. Принцип (узел #272)

Устройства — **нативные домены Biblio**, а НЕ второй сервис-клон IDlogic поверх
ИРБИС. Реконструированный контракт IDlogic — это спецификация того, что ждут
устройства; реализует её тонкий device-facing **compat-адаптер**, переводящий
вызовы устройств в нативные сервисы (circulation/catalog/holds/own-store).

| Возможность IDlogic | Нативный домен Biblio |
|---|---|
| Checkout/Checkin/Renew, долги, инфо/статус/ценз | существующий `circulation` + `catalog` (910^A/H/B) |
| Поля читателя / карты 30/24/28 | own-store `readers` |
| SafeKeeper-заказы / ячейки | `locker` поверх holds (#222) |
| Реестр устройств, health, события, ворота/EAS, счётчик, полки, СКУД, мастер-ключи | `devices` |
| ТСД-инвентаризация | `inventory` |
| Камеры/FaceID | `vision` (токены, не биометрия) |
| Метка RFID | `tag_codec` (ISO 28560-2) |
| Настольный считыватель | `reader_agent` |
| Сторонние киоски | `sip2` (Standard Interchange Protocol v2) |

## 2. Карта модулей (`irbis-web/backend/access/`)

| Модуль | Класс/роль | Тестов |
|---|---|---|
| `devices.py` | `DeviceService` — реестр/heartbeat→health/события/сенсоры/мастер-ключи/лицензии | 36 |
| `locker.py` | `LockerService` — постаматы/SafeKeeper: заказы 1→6, ячейки (битмаска), мастер-открытие | 33 |
| `readers.py` | `ReaderService` — карты RFID↔билет (28/30/24) + `rdr_sync_plan` (DRY-RUN) | 19 |
| `tag_codec.py` | кодек метки ISO 28560-2 (precursor/компакции/AFI-EAS) | 24 |
| `reader_agent.py` | `ReaderAgentService` — настольный считыватель (read/program/EAS) через сиды | 26 |
| `inventory.py` | `InventoryService` — ТСД-инвентаризация, сверка с каталогом (910^D) | 37 |
| `vision.py` | `VisionService` — камеры/FaceID, реестр токен↔билет, `forget` | 49 |
| `sip2.py` | `Sip2Codec` + `Sip2Service` — протокол SIP2 (8 пар сообщений) | 60 |
| `mock_station.py` | `MockStation` — симулятор станции (e2e) | 35 |
| `compat_devices.py` | `CompatDevicesService` — device-facing шим (транслятор) | 88 |
| *core.py* | `_DeviceCircAdapter` (книговыдача), `_InventoryCatalogAdapter` (сверка), HTTP-врезка | — |
| *интеграция* | `tag_integration` 8, `station_integration` 15, `device_routes` 23 | 46 |

Postgres-зеркала: `schema_devices.sql`, `schema_inventory.sql`, `schema_vision.sql`
(ADR-004: sqlite dev / Postgres prod).

## 3. HTTP — `POST /api/devices/<endpoint>`

Единая точка: `core.Api._device_compat` → `CompatDevicesService.handle`.
Аутентификация — унаследованный Basic `ServiceLogin` (env `EASYBOOK_LEGACY_PASS`),
без неё `401`. 37 эндпоинтов:

**`/easybookdll/*` (19):** `IsServerAlive`, `LibraryInfoGet`, `ReaderInfoGet`,
`ReaderModify`, `DeviceIsLicenseValid`, `DeviceDataAdd`, `BooksCacheAddUpdate`,
`Checkout`, `Checkin`, `Renew`, `GetClientChargedDocs`, `GetDocState`,
`GetUserDebts`, `GetDocInfo`, `SetBookState`, `GetBookCenz`, `TagDecode`,
`TagEncode`, `Sip2`.

**station-facing (18):** `MastersRFIDGet`, `SafeKeeperMasterRFIDModify`, `OrdersGet`,
`SafeKeeperInfoGet2`, `OrderBookProcessedSet`, `OrderModify`, `GateEventAdd`,
`VisitorCountAdd`, `SmartShelfSync`, `BooksOnShelfGet`, `AcsPassAdd`,
`InventoryOpen`, `InventoryScan`, `InventoryClose`, `InventoryReport`,
`FaceEnroll`, `FaceIdentify`, `FaceEventAdd`.

Книговыдача на станции (тот же engine, что АРМ выдачи): `Checkout/Checkin/Renew`
→ `_DeviceCircAdapter` → `CirculationEngine` + flip каталожного 910^A.

## 4. Протоколы

- **IDlogic compat** — `/api/devices/*`, JSON DTO, Basic `ServiceLogin`.
- **SIP2** — пары 93/94, 99/98, 63/64, 17/18, 11/12, 09/10, 29/30, 35/36; кадр
  пробрасывается через `Sip2` endpoint (`{line}`→`{Response}`). Реальный TCP-листенер
  SIP2 — деплойная обвязка (см. §7).
- **Метка ISO 28560-2** — `TagDecode`/`TagEncode`; полная побайтовая раскладка
  (precursor, компакции, EAS/AFI) подтверждена декомпиляцией.

## 5. Запуск и тесты

```
cd irbis-web/backend
py -3.12 tests/test_devices.py            # 36
py -3.12 tests/test_locker.py             # 33
py -3.12 tests/test_readers.py            # 19
py -3.12 tests/test_tag_codec.py          # 24
py -3.12 tests/test_reader_agent.py       # 26
py -3.12 tests/test_tag_integration.py    #  8
py -3.12 tests/test_inventory.py          # 37
py -3.12 tests/test_vision.py             # 49
py -3.12 tests/test_sip2.py               # 60
py -3.12 tests/test_mock_station.py       # 35
py -3.12 tests/test_compat_devices.py     # 88
py -3.12 tests/test_device_routes.py      # 23
py -3.12 tests/test_station_integration.py # 15
# ИТОГО 453, in-memory, без БД-сервера
```
CI (`backend-tests sqlite+postgres`, `contract-lint`, `frontend-build`) — зелёный на всех 7 PR.

## 6. Деплой и безопасность

- **Env (БД доменов):** `DEVICES_DB`, `READERS_DB`, `LOCKER_DB`, `INVENTORY_DB`,
  `VISION_DB` (sqlite-пути; в проде — Postgres через `ACCESS_BACKEND`). Книговыдача/
  каталог — `CIRC_DB`/`CATALOG_DB` (общие с АРМ).
- **Env (аутентификация устройств):** `EASYBOOK_LEGACY_PASS` — пароль `ServiceLogin`,
  который уже прописан в существующих устройствах IDlogic. Без него device-эндпоинты
  закрыты (401). Это путь бесшовного подхвата; в проде — TLS поверх + ротация.
- **#222 — живой ИРБИС не пишем:** все домены — own-store; `rdr_sync_plan` отдаёт
  ПЛАН правок RDR (30/24/28), но сам сервер не трогает.
- **Приватность:** `vision` хранит только непрозрачные токены лиц (не изображения/
  шаблоны), `forget(ticket)` — право на забвение. Найденные в реконе креды/ключи
  IDlogic не воспроизводятся; секретов в коде/доке нет (см. `SECRETS_INVENTORY.local.md`,
  gitignored).
- **SECRETS → .env:** захардкоженный legacy Basic и AES-ключ ЕКП IDlogic — НЕ копировать
  в код; конфигурировать через окружение.

## 7. Что осталось и ЧТО НУЖНО ДЛЯ РАЗБЛОКИРОВКИ

### 7.1 🔴 Фаза 3 — привод реальных станций/постаматов (ЗАБЛОКИРОВАНО)
Физическое открытие конкретной ячейки постамата, механика станции выдачи и
аппаратный счётчик посетителей живут в **прошивке станции**, которой НЕТ в
переданном пакете (есть только LAS + TagService + central-service контракт).
Соответствует открытым вопросам рекона `OPEN_QUESTIONS.md §1–3`.

**Для разблокировки нужно ОДНО из (по убыванию пользы):**
1. **Сетевой трейс** (PCAP/Fiddler/Wireshark) реальной станции ↔ central-service во
   время: открытия ячейки (выдача), комплектации (загрузка), сервисного открытия
   мастер-ключом, heartbeat. Это раскрывает station-facing направление (команды
   станции и формат отчётов сенсоров).
2. **Станционный билд** (EXE/прошивка ПО, крутящегося на ПК постамата/киоска — не
   LAS/TagService) для статического анализа: имена операций, формат команд привода.
3. **Доступ к железу** — реальная станция/постамат или вендорский тест-стенд:
   наблюдать и драйвить вживую.
4. **Вендор-спека контроллера ячеек** — протокол платы-актуатора (часто serial/
   Modbus/relay-board командный набор) + распиновка.

Что уже готово к подключению, когда появится протокол: реестр станций/ячеек
(`devices`/`locker`), состояние ячеек (битмаска), заказы 1→6, мастер-ключи,
события — каркас домена под привод есть; нужен только station-facing драйвер.

### 7.2 Остаток вне кода (не заблокировано технически — нужно решение/доступ)
- **Запись карт в прод-RDR.** `rdr_sync_plan(ticket)` отдаёт готовый план правок
  полей 30/24/28. Нужно: явное разрешение писать в живой ИРБИС (сейчас запрещено
  #222) + окно/креды синхронизации. Тогда добавляю исполнитель плана.
- **Реальный TCP-транспорт SIP2 / настольного считывателя.** Логика готова
  (`sip2`, `reader_agent`); нужен деплой-таргет: где слушать (host:port), на чём
  крутить листенер у киоска/стойки, и параметры COM/порта считывателя.
- **Booking-by-face flow (SafeKeeper).** Идентификация лицом (`vision.identify`)
  готова; связка «камера → заказ в ячейке по лицу» частично инференс — нужен трейс
  или спека этого сценария central-service.

### 7.3 Мелочь
- ISO 28560-2: digit-субмаппинг 5/6-бит компакции реализован по документированному
  `+0x40` (заглавные/символы); точная цифровая подкарта — подтвердить дампом реальной
  метки. На штрихкод (OID 1) не влияет (octet/hex/7-бит покрывают).
