# CENTRAL_SERVICE — центральный сервис IDlogic (api.svc) и его общение с устройствами

> **Вопрос:** как устроен центральный сервис IDlogic и как он общается с устройствами.
> **Источник:** ПОЛНАЯ декомпиляция клиента `LibraryAdminServer.exe` (ilspycmd) — `_scratch_devices/dc_LAS/`, ключевой файл `LibraryAdminServer.WebService/WebService.cs` (1147 стр., весь клиент сервиса) + 106 DataContract'ов (`…/DataContracts/*.cs`) + бэкенды TagService (`dc_TagService/.../DbWork.cs`, `WebDb.cs`). Сам сервер `api.svc` на машине отсутствует (удалённый) — спецификация восстановлена со стороны клиента.
> **Связанные:** [DEVICE_CONNECTION_MAP.md](DEVICE_CONNECTION_MAP.md) · [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md) · [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) · [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md)
> **⚠ Секреты:** найдены захардкоженные креды (см. §7) — `секрет → .env`, в репозиторий не вынесены.

## 1. Что это и как устроено

**Центральный сервис IDlogic** — единый серверный backend (`api.svc`, по факту **HTTP + REST/JSON**, несмотря на `.svc`/WCF‑имя), который держит общую БД всего парка устройств и читателей. Все участники (LAS, станции, ворота, SafeKeeper, полки, СКУД, настольные считыватели через TagService) ходят к нему. Архитектурно это **звезда**: устройства наполняют БД своим состоянием, LAS администрирует и отображает.

Эндпоинты (из конфигов и кода):
- `http://‹WCF_HOST›:8005/api.svc` — продакшн (из `DBSettings.xml`).
- `http://127.0.0.1:8000/api.svc` — дефолт в коде `App.LoadDB` (локальный/RFIDCore).
- Маршруты с префиксами **`/las/`** (операции LAS), **`/web/`** (настройки/KPI/баннеры/камеры/GPT), **`/web/gpt/`** (голосовой ассистент), **`/easybookdll/`** (устройство‑facing: лицензия/health/читатели — от TagService/ядра).

**Два взаимозаменяемых backend'а** (видно из TagService): REST `api.svc` **или** прямой **MS SQL Server** (хранимые процедуры). У сервиса под капотом — SQL Server (таблицы `Owners`, `lib_SNUID`, хранимые `lic_GetVersionByDeviceGUID`, `rdr_ReaderInfoGet`, `rdr_ReaderModify` — см. [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) §6).

## 2. Транспорт и формат вызова (точно, из WebService.cs)

```csharp
// конструктор клиента
_client = new HttpClient(new HttpClientHandler { UseProxy=false, Proxy=null });
_client.MaxResponseContentBufferSize = 2_097_152_000;        // ~2 ГБ (большие выгрузки)
_client.DefaultRequestHeaders.Authorization =
    new AuthenticationHeaderValue("Basic", Base64(login + ":" + password));   // ⚠ Basic поверх http
// каждый вызов:
POST  {baseUrl}/{route}
Content-Type: application/json   (тело = JsonConvert.SerializeObject(анонимный объект параметров))
→ ответ: application/json  →  JsonConvert.DeserializeObject<T>
       | application/vnd.openxmlformats…sheet  → поток (XLSX‑отчёты)
       | application/zip  → файл (обновление LAS_Update.zip)
```
Особенности:
- **Аутентификация — HTTP Basic** (`Base64(login:password)`), по умолчанию по **http://** (не TLS). 401 → «Неверный логин и/или пароль».
- **Даты — Microsoft JSON формат** (`DateFormatHandling.MicrosoftDateFormat` → `"\/Date(1699999999999+0300)\/"`) во всех операциях с датами.
- **Прокси:** при `App.IsUseProxy` запрос идёт через `HttpWebRequest`+`WebProxy` (+`NetworkCredential` при `IsUseCredentials`).
- **Тело параметров** — анонимный JSON‑объект; имена полей = имена C#‑параметров (camelCase). Тело может быть `""` (для `*Get` без аргументов).
- Ответы — `List<DTO>` (списки) или скаляр (`bool`/`int`/`Guid?`). `byte[]`/фото передаются как `int[]` (поэлементно).

Клиент `WebService` создаётся **после входа** в `SafeKeeper.LoginPage.GetLogin()` с логином/паролем оператора LAS (не путать с устройство‑facing кредами `/easybookdll/`).

## 3. Полный каталог операций (route → параметры → ответ DTO)

> Сгруппировано по классам. `op/opID`: 0=удалить, 1=создать, 2=обновить, 3=смена пароля. Полные имена/порядок — `WebService.cs`.

### Аутентификация/пользователи (`/las/`)
| Операция | Параметры | Ответ |
|---|---|---|
| `LoginInfoGet` | login, password | `AUTH_LoginInfo` |
| `LoginInfoModify` | opID, login, password, newPassword, roleTypeID, ФИО | int |
| `LoginModulesAccessGet` | loginID | `List<AUTH_LoginModulesAccess>` |
| `RoleTypesGet` | — | `List<AUTH_RoleType>` |
| `UsersInfoGet` / `UserModify` / `UserModulesAccessAddModify` | … | `List<AUTH_UserInfo>` / int |

### Настольные считыватели / устройства (`/las/`, `/web/`)
| Операция | Параметры | Ответ |
|---|---|---|
| `DevicesGet` | — | `List<MON_Device>` |
| `DeviceModify` | opID, deviceID, name, typeID, **cfg, cfg2**, libraryID | Guid? |
| `DeviceTypesGet` | — | `List<MON_DeviceType>` |
| `DeviceDataGet` | deviceID, selectedDate | `List<MON_DeviceData>` |
| `DevicesLastHistoryGet` / `DesktopDeviceInfoGet` | libraryID / deviceID | … |
| `DesktopDeviceConfigGet` | deviceID, connectionString | поток ZIP (дистрибутив TagService) |

### Ворота (`/las/`)
| Операция | Параметры | Ответ |
|---|---|---|
| `GatesGet` | — | `List<MON_Gate>` |
| `GateModify` | gateID, name, ip, port, typeID, cfgTypeID, libraryID, **counterName/IP/Port** | bool |
| `GateTypesGet` | — | `List<MON_GateType>` |
| `GateDataGet` | gateID, date | `List<MON_GateData>` |
| `GateAlarmGet` / `GateAlarmsGet` | id / gateID, период | тревоги |
| `GateCountersGet` | gateID, период | `List<MON_GateCounter>` (вход/выход) |
| `GateEASEventsGet` | gateID, период | `List<MON_GateEASEvent>` |

### SafeKeeper / заказы (`/las/`)
| Операция | Параметры | Ответ |
|---|---|---|
| `SafeKeepersGet` / `SafeKeepersForOrderGet` / `VendingsSafekeepersGet` | — | `List<SK_SafeKeeper>` |
| `SafeKeeperInfoGet2` | safeKeeperID | `List<SK_SafeKeeperInfo>` (ячейки) |
| `SafeKeeperModify` | opID, safeKeeperID, name, libraryID | int |
| `OrdersGet` | — | `List<SK_Order>` |
| `OrderModify` | opID, id, number, **cellNumber**, readerRFID, readerFIO, **stateID**, safekeeperID, loginID | int |
| `OrderBodyGet` / `OrderBodyModify` | orderID / (…, bookRFID, isVerified, isProcessed) | … |
| `OrderBookProcessedSet` | bookCode, orderID | bool |
| `MastersRFIDGet` / `MasterRFIDModify` | — / (opID, id, rfidCode, ФИО) | мастер‑ключи |
| `SafeKeeperMasterRFIDModify` / `SafeKeepersMasterRFIDGet` | привязка ключ↔камера | … |
| `SafeKeeperHistoryGet` / `…MasterGet` | период | история |

### Станции/Vending (`/las/`, `/web/`)
| Операция | Параметры | Ответ |
|---|---|---|
| `StationsGet` | — | `List<MON_Station>` |
| `StationModify` | stationID, name, libraryID | bool |
| `StationDataGet` / `StationEventStatsGet` / `StationEventsHistoryGet` | … | события/статистика |
| `StationAliveMonitoringGet` | stationID, date | `List<MON_StationAliveMonitoring>` |
| `StationsWithCoordinatesGet` | libraryID | координаты для схемы зала |
| `VendingsGet` | libraryID | `List<MON_Station>` |
| `BooksOnVendingStationGet` / `VendingOrdersGet` / `VendingsEventsHistoryGet` | … | книги/заказы |
| баннеры: `BannersGet`, `BannerAddModify`, `BannerTaskAddModify`, `StationsByBannerIDGet` | … | афиша |

### Умные полки (`/las/`)
`BooksOnShelfGet(stationID)`→`List<SS_BookOnShelf>` · `SmartShelfReturnsGet`→`List<SS_Return>` · `SmartShelfStatGet`→`List<SS_Stat>`.

### СКУД (`/las/`)
`ACSGet`→`List<ACS_ACS>` · `ACSEventsGet(level,levelID,период)`→`List<ACS_Event>` · `ACSAdvancedEventsGet` · `ACSReaderModify` · `ACSReaderAntennaAddModify`/`ACSReaderAntennasGet` · `ACSReaderTypesGet` · `ACSZoneModify` · `EntranceModify`.

### Хранение фонда (`/las/`, `/web/`)
`BookCasesGet`, `BookCasesAndShelvesGet`, `BookCaseAddModify`, `BookCaseSectionsGet/AddModify`, `BookShelfAddModify`, `BookCellAddModify`, `BookCellsOnShelfGet`, `BooksOnCellGet`, `BookKeepingBooksGet`, `BookKeepingBookInfoGet`, `BookKeepingBookRemove`, `BookKeepingBookSearch`, `BookKeepingBookToCellBind`, `BookKeepingHistoryAdd/Get/StatGet`, `BookKeepingBackgroundGet/Modify/OpacityModify`, `BookKeepingEnvironmentGet/Modify`, `BookKeepingStationCoordinatesSet`.

### Читатели / FaceDetect / KPI / прочее
- Читатели: `ReadersGet`, `ReaderInfoGet(id, rfidCode)`→`List<RDR_ReaderInfo>`, `ReaderModify(opID, readerID, name, abisCode, rfidCode, serialNumber, email)`, `ReaderPhotoAdd/Delete`.
- FaceDetect: `FaceDetectDevicesAndCamerasGet`, `FaceDetectStationsGet`, `FaceDetectCameraModify`, `FaceDetectCameraToStationAttach`, `FaceDetectDeviceModify`.
- KPI/посетители: `KPIServicesGet/TypesGet/Modify/Apply`, `KPIEmployeesGet`, `KPIReportServicesGet`, `KPIDailyEmployeeReportGet`, `VisitorsGet(intCameraIDList, период, lastVisitorID)`→`List<KPI_Visitor>`, `KPICamerasGet`.
- Библиотеки/книги: `LibrariesGet`, `LibraryModify`, `BooksGet`, `BookCoverGet`, `BookModify`, `BookToLibBooksAdd`, `BookFromLibBooksGet`, `TSLibraryUpdate`, `KeyUpdate`.
- Дашборд: `info_{Equipment,EAS,Stations,DesktopDevices,SafeKeepers,SmartShelves,ACS}Get` + `…AdvancedGet`.
- Лог/обновление/настройки: `ExternalLogAdd/Get`, `upd_IsUpdateAvailable`, `upd_Update`(zip), `upd_UpdateInfoGet`, `SettingsGet/Modify`, `ManualGet` (руководство; в текущем клиенте десериализуется как `MemoryStream` из строки — фактически не работает как поток, баг исходника), `ColorsGet`, `ServicesGet`.
- GPT: `/web/gpt/GetAnalytics`, `GetDashboardMetrics`, `GetTopQueries`, `GetLanguages`, `GetVoiceTypes`, `GetVoiceAssistantSettings`, `GetVoiceResponseTemplates`, `GetTemplateStations`, `Update…`.

### Устройство‑facing (`/easybookdll/`, от TagService/ядра)
| Операция | Тело | Назначение |
|---|---|---|
| `IsServerAlive` | — | health |
| `LibraryInfoGet` | `{deviceID}` | `{LibraryID, TS, TS1}` (лицензия/привязка) |
| `ReaderInfoGet` | `{id:0, rfidCode, deviceID}` | найти читателя по RFID/ЕКП |
| `ReaderModify` | `{opID, readerID, name, abisCode, rfidCode, email, serialNumber, deviceID}` | привязать карту к читателю |
| `DeviceIsLicenseValid` | `{deviceID}` | валидна ли лицензия устройства |
| `DeviceDataAdd` | `{deviceID, softOnlineCount, deviceOkCount, deviceErrorCount}` | **health‑метрики считывателя** |
| `BooksCacheAddUpdate` | … | кэш прочитанных кодов книг |

## 4. Как сервис общается с устройствами (модель)

**Ключевой принцип:** LAS **не** командует станциями/воротами/ячейками. Их состояние в БД сервиса наполняют **сами устройства** (их прошивка/контроллер), а LAS читает (`*Get`) и администрирует справочники (`*Modify`).

```
            POST своё состояние/события                  GET состояние/события
устройство ───────────────────────────▶  api.svc (БД)  ◀─────────────────────────── LAS
(станция/ворота/SafeKeeper/полка/СКУД)    SQL Server     (панель администратора)
настольный считыватель (TagService) ──▶  /easybookdll/* (health, читатели, лицензия)
```

Что именно «течёт» от устройства к сервису (видно по схемам DTO — это «вход» для устройства, «выход» для LAS):
- **Настольный считыватель → `/easybookdll/DeviceDataAdd`** `{deviceID, softOnlineCount, deviceOkCount, deviceErrorCount}` — почасовая исправность; LAS читает это как `MON_DeviceData{SoftOnlineCount, DeviceOKCount, DeviceErrorCount, DeviceState}` (графики мониторинга). **Подтверждено** (нативное ядро + WebService).
- **Станция → сервис:** `MON_Station` несёт здоровье узлов, которые рапортует киоск: `IsReaderOk, IsCardReaderOk, IsPrinterOk, IsABISOk, IsControllerOk, IsConveyorOk, IsOnline, LastUpdate`; плюс события `MON_StationData{EventTypeID, Message, UserCode}` и `StationAliveMonitoring{HourValue, AlivePercents}`. **Протокол станция→сервис в этих бинарниках отсутствует** (в прошивке станции) — `[инференс]` по схемам.
- **Ворота → сервис:** `MON_GateEASEvent{UID, BookName, BookCode, IsBook, DateValue}` (срабатывания антикражи) и `MON_GateCounter{Date, ValueIn, ValueOut}` (счётчик вход/выход), liveness `MON_Gate{IsOnline, CounterIP, CounterPort, IsCounterOnline}`. `[инференс]`.
- **SafeKeeper → сервис:** `SK_SafeKeeper{CellsCount, **CellsState:long?** (битовая маска занятости до 64 ячеек), BusyCellsCount, VacantCellsCount, IPAddress, IsOnline}` и пер‑ячейка `SK_SafeKeeperInfo{CellNo, IsBusy, UserFIO, UserCode, CellContent, DateBusy, StorageTime}`. `[инференс]`.
- **Умная полка → сервис:** `SS_BookOnShelf{BookCode, BookName, CountTakes}`, возвраты `SS_Return`. `[инференс]`.
- **СКУД → сервис:** `ACS_Event{EventDate, RFIDCode, ClientName, ReaderID, DirectionTypeID}`. `[инференс]`.

> «`[инференс]`» означает: сами DTO и операции чтения подтверждены кодом LAS; обратный канал «устройство → сервис» в наличных бинарниках не реализован (он в прошивке станций) — но **формат данных, которые устройство обязано отдавать, известен точно** из этих DTO. Это и есть то, что наша система должна реализовать на серверной стороне.

## 5. Схемы данных устройств (JSON DTO, точные поля)

```
MON_Device         : ID(Guid), Name, IsOnline, TypeID, TypeName, CFG, CFG2, LibraryID
MON_DeviceData     : DeviceID(Guid), DateValue, HourValue, SoftOnlineCount, DeviceOKCount,
                     DeviceErrorCount, DeviceOKCount_Percent, DeviceStateID, DeviceState
MON_Station        : ID(Guid), Name, IsOnline, SN, TypeID, IsReaderOk, IsCardReaderOk,
                     IsPrinterOk, IsABISOk, IsControllerOk, IsConveyorOk, StationAliveMonitoring[]
MON_StationData    : StationID(Guid), DateEvent, EventTypeID, EventName, Message, UserCode, Count, PairID
MON_Gate           : ID(Guid), Name, IP, Port, TypeID, IsOnline, CounterName, CounterIP, CounterPort, IsCounterOnline
MON_GateEASEvent   : ID, GateID(Guid), DateValue, UID, BookName, BookCode, IsBook
MON_GateCounter    : Date, ValueIn, ValueOut
SK_SafeKeeper      : ID(Guid), Name, CellsCount, SerialNumber, CellsState(long-битмаска),
                     IPAddress, IsOnline, SafeKeeperTypeID, CellShift, BusyCellsCount, VacantCellsCount
SK_SafeKeeperInfo  : StationID(Guid), StationTypeID, CellNo, UserFIO, UserCode, CellContent,
                     DateBusy, IsBusy, CellShift, StorageTime, StorageTimeHint, CellContentDescription
SK_Order           : Id, Number, CellNumber, ReaderRFID, StateId, ReaderFIO, SafeKeeperId(Guid), CellNumberShifted
SK_OrderBody       : Id, BookRFID, BookInfo, IsVerified, IsProcessed, OrderId, Authors
SS_BookOnShelf     : ID, BookID, BookName, BookCode, CountTakes, BookRate
VD_BookOnVending   : VendingStationID(Guid), CellNumber, BookName, BookCode, MasterID, UserCode, DateIn
ACS_Event          : ID, EventDate, RFIDCode, ClientName, ReaderID, DirectionTypeID
RDR_ReaderInfo     : ID, Name, BirthDate, AbisCode(билет), RFIDCode, SerialNumber, Email, Photo, IsHavePhoto
```
> Полный список 106 DTO — `_scratch_devices/dto_fields.txt`. Состояния заказа `SK_Order.StateId`: 1=Создан,2=Подготовлен,3=Укомплектован,4=Выдан,5=Отменён (см. [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §7.3 и enum `OrderStates`). Типы станций `TypeID`: 3/8=умные полки, 3/4=ячейки SafeKeeper (фильтры в коде), прочее=станции.

## 6. Что реализовать в Biblio, чтобы заменить центральный сервис

1. **HTTP‑сервис** с маршрутами `/las/*`, `/web/*`, `/web/gpt/*`, `/easybookdll/*`, POST+JSON, **Basic‑auth**, Microsoft‑формат дат, ответы `List<DTO>`/скаляр, выгрузки XLSX/ZIP. (Наша версия — лучше HTTPS + токены.)
2. **БД устройств** со схемами §5 (или эквивалент): устройства, их данные/health, ворота+события EAS+счётчики, SafeKeeper+ячейки+заказы, станции+события, полки, СКУД+события, читатели (RFID/ЕКП/фото), баннеры, KPI/посетители, лицензии, лог.
3. **Приём данных от устройств:** реализовать обратный канал «устройство → сервис» (станции/ворота/SafeKeeper/полки/СКУД пишут своё состояние; настольный считыватель — `/easybookdll/DeviceDataAdd` health). Формат — по DTO §5.
4. **Устройство‑facing API `/easybookdll/`** (`IsServerAlive`, `LibraryInfoGet`, `ReaderInfoGet`, `ReaderModify`, `DeviceIsLicenseValid`, `DeviceDataAdd`, `BooksCacheAddUpdate`) — чтобы существующие TagService/станции могли работать с нашим сервером без переустановки.
5. **SQL‑backend (опц.):** воспроизвести хранимые `lic_GetVersionByDeviceGUID`, `rdr_ReaderInfoGet`, `rdr_ReaderModify`, таблицы `Owners`/`lib_SNUID` — для прямого SQL‑режима TagService.

## 7. Безопасность (находки)

| Находка | Где | Риск |
|---|---|---|
| **Basic‑auth поверх http://** | `WebService` ctor | креды в Base64 по открытому каналу → `секрет → .env` + TLS |
| **Захардкоженные креды устройство‑facing** `ServiceLogin` / `‹REDACTED›` | TagService `Resources` (resx) | общий пароль на всех устройствах |
| **Захардкоженные сервис‑пароли** (`‹...›`) | LAS `SecurityWindow`, `GatesSecurityWindow` | сервис‑доступ, не выносить в Biblio |
| **AES‑ключ ЕКП/лицензии в коде**, нулевой IV | TagService `TS1Worker`/`TntCryptoUtils` | слабая крипто‑схема |
| Боевые IP/пароли ИРБИС, камеры, RFIDCore | `SIP2settings.xml`, `FaceDetect.xml`, `DBSettings.xml` | `секрет → .env`, не коммитить |

Все значения секретов наблюдались в конфигах/коде на стенде и **в репозиторий не вынесены**.
