# Контракт device-facing compat-адаптера (2/3)

> Тонкий **протокольный шим**: принимает вызовы, которые физические устройства/агенты IDlogic (TagService, станции, постаматы) уже умеют делать, и **транслирует** их в нативные сервисы Biblio. НЕ система‑источник, НЕ копия `api.svc`. Рамка — [DEVICES_NATIVE_ARCHITECTURE.md](../DEVICES_NATIVE_ARCHITECTURE.md) (#272).
> Связанные: [DOMAIN_DEVICES_SPEC.md](DOMAIN_DEVICES_SPEC.md) (1/3), [SAFEKEEPER_HOLDS_MAPPING.md](SAFEKEEPER_HOLDS_MAPPING.md) (3/3). Перечень эндпоинтов — [device_service_openapi.json](../contracts/device_service_openapi.json).
> Достоверность: **[C]** подтверждено клиентским кодом; **[I]** инференс (station‑facing направление — сверяется трейсом/мок‑станцией).

## 1. Размещение и принцип
- **Модуль:** `irbis-web/backend/access/compat_devices.py` (HTTP‑роутер шима) — тонкий слой над `DeviceService`/`CirculationEngine`/`HoldService`/own‑store. Без своей БД.
- Каждый входящий device‑вызов → 1–2 вызова нативных сервисов → ответ в формате, который ждёт устройство.
- **Размещение в Biblio:** узел ген‑линии после auth+режимов; reuse уже валидированных own‑store/circulation.

## 2. Аутентификация (бесшовный подхват)
- Устройства/агенты IDlogic ходят с **унаследованным Basic `ServiceLogin:<legacy>`** (захардкожен в resx TagService — [TAGSERVICE_FUNCTION_MAP.md](../TAGSERVICE_FUNCTION_MAP.md) §6). Шим **whitelist'ит** этот Basic и мапит на сервис‑аккаунт с грантом `devices.service` (+ ограниченный `circulation`/`holds`). **[C]**
- В Biblio предпочтительно TLS + токен; legacy‑Basic принимаем **только** для бесшовного подхвата существующих устройств (флаг конфигурации, по умолчанию off в проде).

## 3. Карта «device endpoint → нативный сервис»

### 3.1 Настольный считыватель / агент (`/easybookdll/*`) — [C]
| Endpoint (вход) | Нативная трансляция | Ответ устройству |
|---|---|---|
| `POST /easybookdll/IsServerAlive` | health ping | `true` |
| `POST /easybookdll/LibraryInfoGet {deviceID}` | `DeviceService.get(guid)` + лицензия | `[{LibraryID, TS, TS1}]` |
| `POST /easybookdll/ReaderInfoGet {id,rfidCode,deviceID}` | own‑store/RDR: найти читателя по RFID/ЕКП (поля 28/30/24) | `[{AbisCode, RFIDCode}]` |
| `POST /easybookdll/ReaderModify {…,abisCode,rfidCode,serialNumber,deviceID}` | own‑store/RDR: привязать карту (28/30/24) | `bool` |
| `POST /easybookdll/DeviceIsLicenseValid {deviceID}` | `DeviceService.is_license_valid(guid)` | `bool` |
| `POST /easybookdll/DeviceDataAdd {deviceID,soft,ok,error}` | `DeviceService.heartbeat(...)` → `device_health` | `bool` |
| `POST /easybookdll/BooksCacheAddUpdate {…}` | лог/кэш (catalog/devices), идемпотентно | `bool` |

### 3.2 Сокет/WebSocket настольного считывателя (Reader Agent) — [C]
Протокол `:6001` (команды 75/77/79/81/97, [TAGSERVICE_FUNCTION_MAP.md](../TAGSERVICE_FUNCTION_MAP.md) §4) и WebSocket портала → читают/пишут метку (кодек ISO 28560‑2), EAS/AFI; результаты идут в circulation (выдача/возврат) и catalog (статус 910^A). Reader Agent — отдельный компонент, использует тот же шим‑слой.

### 3.3 Станции / постаматы / SafeKeeper (station‑facing) — [I]
| Endpoint (вход, гипотеза) | Нативная трансляция | Деталь |
|---|---|---|
| `OrdersGet` / `OrderBodyGet` | `HoldService`: holds станции (locker‑заказы), тело = книги заказа | спека 3/3 |
| `SafeKeeperInfoGet2 {safeKeeperID}` | holds → карта ячеек (занятость), `device.ip` | CellsState вычисляем из holds |
| `OrderModify {opID,stateID,cellNumber,…}` | переход состояния hold (1→2→3→4/6, opID 0 отмена) | спека 3/3 §3 |
| `OrderBookProcessedSet {bookCode,orderID}` | пометить позицию заказа обработанной (hold body) | — |
| `MastersRFIDGet` / `SafeKeeperMasterRFIDModify` | `DeviceService.masters()` / `master_modify()` | грант `devices.service` |
| `StationAliveMonitoringGet` / health | `DeviceService.heartbeat`/`health_series` | derive online |

> Эти строки — наша **гипотеза** того, что станция шлёт. Шим реализует их по реконструированной модели; сверка — мок‑станцией ([mock_station_spec.md](../contracts/mock_station_spec.md)) и позже одним сетевым трейсом/станционным билдом.

### 3.4 Выдача/возврат с устройства → circulation — [C для семантики]
Любой checkout/checkin/renew, инициированный устройством (станция, локер‑выдача, настольный), идёт в **`CirculationEngine`** (`checkout`/`return_item`/`renew`), который применяет правила и пишет loan/910^A. При ошибке записи в АБИС (режим замены JIRBIS) — статус заказа `6` (с‑ошибками), см. спеку 3/3.

## 4. Что отдаём LAS‑админу (опционально)
LAS‑admin маршруты (`*Get`/`*Modify`, `info_*`) можно отдавать тем же шимом для совместимости со штатным LAS‑GUI, транслируя в `DeviceService`/`HoldService`/circulation reads. Но штатный UI Biblio эти данные читает напрямую из доменов, без шима.

## 5. Границы
- Шим **не хранит состояние** — только переводит. Источник истины — нативные домены.
- Legacy‑Basic — только compat‑режим; прод — токены/TLS.
- Station‑facing `[I]` помечать в коде флагом — заменить на факт после трейса/станции в одном месте.
