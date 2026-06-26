# LAS_FUNCTION_MAP — карта функций LibraryAdminServer.exe (панель администратора)

> **Источник:** ПОЛНАЯ C#‑декомпиляция (ilspycmd) — `_scratch_devices/dc_LAS/` (377 файлов). Цитаты — по классам/методам/файлам декомпиляции. Гипотезы — **(инференс)**.
> **Связанные:** [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) · [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) · [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md)
> **Обозначения вызовов:** **WS** = `App.WebService.*` (центральный сервис) · **ABIS** = `App.AbisWorker.*` (ИРБИС/SIP2) · **RDR** = `App.Reader.*` (настольный считыватель, `EasyBook_RFid.dll`) · **RFIDCore** = `SmartRFID.Reader.ReadsReceiver` (служба RFID Core).

## 1. Архитектура приложения

`LibraryAdminServer.exe` — WPF/.NET (ModernWpf). Глобальное состояние — статический `App` (`LibraryAdminServer/App.cs`): `WebService`, `AbisWorker`, `Reader Reader=new Reader(1)`, `CameraFD`, `Config`, `IrbisConfig`, ~50 флагов `Is*Enabled` (из лицензии `VersionWorker.CheckVersion`).

**`Application_Startup` (порядок загрузки):**
1. `IsDeviceLicenseValid()` (P/Invoke `EasyBook_RFid.dll`).
2. `LoadDB` ← `DBSettings.xml`: `ConnectionString` (дефолт `http://127.0.0.1:8000/api.svc`), прокси, `IsUseRFIDCore`, `RFIDCoreConnectionString` (`url;admin;‹pwd›`), EAS/чек/email/SMTP.
3. `LoadSIP2` ← `SIP2settings.xml`: ИРБИС/SIP2 (`DbIP/DbPort`, логин/пароль, `IrbisDB`), `AgeControl`, `NeedCheckDebts`, `OnlyOneRenew`, `UseSIP2`.
4. `LoadCam` ← `FaceDetect.xml` → `CameraFD` (Dahua: `CameraIP`, `RegistratorIP`, `Port=37777`, `ChannelNo`, логин/пароль).
5. **AbisWorker:** `new AbisWorker(IsUseSIP2 ? SIP2 : IRBIS, config)` → `Connect()`.
6. NLog → `Log\AppLog.txt`.

**`MainWindow`:** показывает `LoginPage` (модально). Таймеры: `checkReaderTimer`(1с `RDR.IsConnected`), `checkABISTimer`(10с `ABIS.IsDbOk`), **`sendCharTimer`(0.5с `Inventory()`** — эмуляция ввода RFID/ЕКП в активное окно АРМ ИРБИС), `serviceTimer`(1м `WS.ServicesGet`), `alarmTimer`(1с `WS.GateAlarmGet`→`AlarmWindow`). Навигация `mainMenu_SelectionChanged` подменяет страницу модуля. `WebService` создаётся в `LoginPage.GetLogin()` после входа.

## 2. Карта модулей (`LibraryAdminServer.Modules.*`)

### 2.1 «Библиотекарь» — BookCheckInOut (главный операционный, прямая ИРБИС)
- **BookCheckMenuPage** — меню → страницы; проверка `IsDeviceLicenseValid`.
- **BookCheckOutPage** (выдача): `GetReader` (`WS.ReaderInfoGet`→`ABIS.GetClientName`); `ReaderTimer_Tick` авто‑карта (RDR `GetSnDms` фильтр `UserCard`, ЕКП 14 симв.→`WS.ReaderInfoGet`/диалог/`ABIS`+`WS.ReaderModify`); `Timer_Tick` набор книг (`RDR.GetSnDms`→`ABIS.GetDocInfo`); **`btnCheckOutConfirm_Click`** — выдача: `RDR.UnsetEas(SN)` (если `IsUseEAS`, до 40 попыток) → `ABIS.Checkout(Reader.Rfid, book.RFIDID)` → чек (`ReceiptPrintHelper`) + email; `btnRFIDAuth_Click`→`RFIDSearchDialogPage`; `btnFaceIDAuth_Click`→`FaceDetectPage(recognize)`.
- **BookCheckInPage** (возврат): `Timer_Tick` набор; **`btnCheckIn_Click`** — `RDR.SetEas(SN)` (если EAS) → `ABIS.Checkin(book.RFIDID)`.
- **ReaderFormPage** (формуляр): `ABIS.GetClientChargedDocs(Rfid)`→по RFID `ABIS.GetDocInfo`; **`btnProlong_Click`** — `ABIS.Renew(RFIDID, Rfid, due+ReturnDaysCount, out msg)`.
- **BookInfoPage** — `RDR.GetSnDms`→`ABIS.GetDocInfo`; владелец `ABIS.GetClientName`.
- **BooksPage / BookModifyWindow** — каталог: `WS.BooksGet`, `WS.BookCoverGet`, `ABIS.GetDocInfo`, `WS.BookModify`.
- **RFIDSearchDialogPage** — чтение читательской карты (RDR, нормализация ключа `001B`/hex)→`WS.ReaderInfoGet`.
- **UserRegistrationPage** — **регистрация ЕКП**: лицензия (`TS1Worker.ParseData(TS1)`→`EKPWorker.IsAuthenticated`), `TimerUID_Tick` (Mifare UID), `TimerPersID_Tick` (ЕКП `GetPersID/GetPersData/GetMainDoc/GetPhoto`), проверка `ABIS.GetReaders`, привязка `ABIS.AddEkp`; **`btnUserReg_Click`** — `ABIS.AddReader`→`WS.ReaderModify`→`WS.ReaderPhotoAdd`→печать заявления (`DocxPrinterViaHtml`); ручной `btnUserReg_m_Click`→`ABIS.AddReaderByCard`.

### 2.2 SafeKeeper — заказы/ячейки/мастер‑ключ
- **LoginPage.GetLogin** — создаёт WS; `LoginInfoGet`, `LoginModulesAccessGet`, `IsUpdateAvailable`, `LibrariesGet`, `LASColorsGet`, `ServicesGet`, `RoleTypesGet`, `VersionWorker.CheckVersion`.
- **SafeKeeperMenuPage** — `LoadSafeKeepers` (`WS.SafeKeepersGet`, раскладка `CellsState`→занятость), `LoadOrders` (`WS.OrdersGet`).
- **OrderEditPage** — ядро заказа: `GetReader` (ABIS+WS); `SafeKeeperInfoGet` (свободные ячейки `StationTypeID 3/4`); приём книг `Timer_Tick` (`RDR.GetSnDms`→`ABIS.GetDocInfo`→`RDR.UnsetEas`×10→`ABIS.SetBookState(OnShelf)`→`WS.OrderBodyModify`); выдача `btnCheckOut*_Click` (`ABIS.Checkout`+`WS.OrderBookProcessedSet`); статусы `WS.OrderModify` (2=подтв,4=выдан,0=отмена).
- **OrdersPage/HistoryPage** — `WS.OrdersGet/HistoryGet/HistoryMasterGet`.
- **SafeKeeperPage/DialogPage** — `WS.SafeKeepersGet/SafeKeeperInfoGet/SafeKeeperModify`.
- **AdminsPage/AdminDialogPage** — мастер‑ключи: `WS.MastersRFIDGet/MasterRFIDModify/SafeKeeperMasterRFIDModify/SafeKeepersMasterRFIDGet` + чтение мастер‑карты RDR/ЕКП.

### 2.3 Vending / Stations / SmartShelves
- **Vending** (прямая ИРБИС) — `OrderPage` ≈ OrderEditPage (выдача через вендинг: `ABIS.GetClientName/GetDocInfo/SetBookState/Checkout`, `RDR.GetSnDms/UnsetEas`; `WS.VendingsGet/VendingOrdersGet/OrderModify/OrderBodyModify/BooksOnVendingStationGet`); `VendingAdmins*` — мастер‑ключи.
- **Stations** (только WS) — `WS.StationsGet`(TypeID≠3,≠8), `StationEventStatsGet`, `StationsEventsHistoryGet`, `StationModify`; баннеры `BannersGet/BannerAddModify/BannerTaskAddModify`.
- **SmartShelves** (только WS) — `WS.StationsGet`(TypeID 3/8), `BooksOnShelfGet`, `SmartShelfStatsGet`, `SmartShelfReturnsGet`, `StationModify`.

### 2.4 Gates — противокражные ворота (только WS)
**GatesPage**: `WS.GatesGet`; `WS.GateAlarmsGet`+`GateCountersGet` (графики Вход/Выход/Тревога); `WS.GateEASEventsGet` (срабатывания). **GateEditPage**: `WS.GateTypesGet`, `WS.GateModify`(+счётчик), `WS.ExternalLogAdd`. **AlarmWindow** — `MON_GateAlarm`. Сервис‑пароль захардкожен (секрет).

### 2.5 ACS — СКУД (только WS)
Иерархия `acs_Entrance→acs_Reader→acs_Zone→acs_Antenna`. **ACSPage**: `WS.ACSGet/ACSReaderAntennasGet/ACSEventsGet/ACSAdvancedEventsGet/EntranceModify`. **ACSEditPage**: `WS.EntranceModify/ACSReaderModify/ACSZoneModify/ACSReaderAntennaAddModify/ACSReaderTypesGet` (тип 2 → 4 антенны).

### 2.6 BookKeeping — хранение фонда (WS + RFID + ABIS)
**BookKeepingPage** (вкладки Хранение/Поиск/Все книги/Конструктор/История): иерархия `BookCaseSectionsGet→BookCasesAndShelvesGet→BookCellsOnShelfGet→BooksOnCellGet`; RFID‑инвентаризация `ReadTimer_Tick` (`RDR.GetSnDms`/`RFIDCore.GetTags`→`WS.BookKeepingBookInfoGet`, статусы `BookInvStates`; неизвестная книга→`ABIS.GetDocInfo`→`WS.BookToLibBooksAdd`); применение `WS.BookKeepingBookToCellBind`+`HistoryAdd`; конструктор схемы (`WS.BookKeepingEnvironment*`, `StationsWithCoordinatesGet`, `BookCaseAddModify` Coordinates, `BackgroundGet/Modify`); экспорт XLSX.

### 2.7 Monitoring / Dashboard (только WS)
- **MonitoringMenuPage** → 6 страниц (Device/Gates/SafeKeepers/SmartShelves/Stations/Vendings). Паттерн: список + дата + `StationAliveMonitoringGet` + `*DataGet`, фильтр по `EventTypeID`.
- **DashboardPage** — параллельно `WS.Info{Equipment,EAS,Stations,DesktopDevices,SafeKeepers,SmartShelves,ACS}Get`; кнопки → Advanced‑страницы.

### 2.8 Readers / FaceDetect
- **ReaderAddPage/EditPage** — `WS.ReaderInfoGet/ReaderModify/ReaderPhotoAdd/Delete`; авто‑карта RDR/ЕКП; `ABIS.GetClientName`; FaceID `btnFaceID*`.
- **ReadersPage** — `WS.ReadersGet`, поиск (вкл. `ABIS.GetClientName`), пагинация.
- **FaceDetectSettingsPage** — CRUD камер: `WS.FaceDetect{DevicesAndCamerasGet,StationsGet,DeviceModify,CameraModify,CameraToStationAttach}`.

### 2.9 Users / Libraries / Lic / Inventory / Stuff(KPI) / VoiceAssistant
- **Users** — `WS.UsersInfoGet/LoginModulesAccessGet/UserModulesAccessAddModify/LoginInfoModify`; 14 флагов прав на модули.
- **Libraries** — `WS.LibrariesGet/LibraryModify`.
- **Lic** — активация: `LicenseWorker.Decrypt`→`WS.KeyUpdate`/`TSLibraryUpdate`; **LicensePage** — рабочие места `WS.DevicesGet/DeviceModify`, выгрузка cfg/cfg2/cfg3 + ZIP (`EasyBookConfigWorker`); **ReadersConfigPage** — конфигуратор считывателей (ISO15693/14443, EAS/AFI, порты).
- **Inventory** — RFID Core: `ReadsReceiver(RFIDCoreConnectionString, EventID)` `IsConnected/GetTags/StartReadInventory/StopReadInventory`; экспорт/импорт EPC.
- **Stuff/KPI** — `WS.KPI*`; **VisitorPage** — RFID‑авторизация + формуляр + выдача/возврат (`ABIS.Checkout/Checkin/Renew`, `RDR.SetEas/UnsetEas`) + услуги `WS.KPIServiceApply`.
- **VoiceAssistant** — `WS.GPT_*` (язык/голос/настройки/шаблоны/аналитика).

### 2.10 Прочее
- **SettingsPage** — пишет только локальные XML (DBSettings/SIP2settings/FaceDetect) → рестарт.
- **UpdateWindow** — `WS.Update`(zip)/`UpdateInfoGet` → распаковка → рестарт.
- **SecurityWindow / GatesSecurityWindow** — сервис‑пароли захардкожены (секрет, не реплицировать).

## 3. Перечисления (`LibraryAdminServer.Enums`)

| Enum | Значения |
|---|---|
| **BookStates** | CheckInOutOk=1, CheckInOutError=2, MiddleState=3 |
| **AntitheftBits** | EAS=0, AFI=1 |
| **ReaderTypes** | DesktopReader=0, StationaryReader=1 |
| **ISOStatndarts** | ISO15693SN=0, ISO15693DM=1, ISO14443=2 |
| **BookInvStates** | New=1, Found=2, NotFound=3, NotOnPlace=4 («Перемещена»), Unknown=5 |
| **BookKeepingTypes** | Unknown=0, BookCase=1, Station=2, Environment=3 |
| **BookOps** | Read=1, Search=2 |
| **OrderStates** (DBClasses) | Created=1, Prepared=2, Staffed=3 (укомплектован), Issued=4, Cancelled=5 |
| **ExternalLogTypes** | 1..32 (32 члена): EASSystemAdded=1, OrderAdded/Edited/Canceled, MasterRFIDAdded, BannerAdded, DesktopDeviceAdded, EntranceAdded, **BookCheckOut, BookCheckIn**, ReaderFormRequest, BookInfoRequest, **ReaderFDSearch**, ReaderPhotoAdded, ReaderRFIDAdded, BookCaseAdded, …, ProgramSettingsChanged=31, **UserPasswordChanged=32** |

## 4. Локальные сущности (`DBClasses` / `DBClasses.Prop`)

- **BookInfo** — экземпляр в операциях: Title, Authors, Inv/InventoryNumber, Cipher, Location, Owner, DocType, Duedate, State(ИРБИС), BookStates(enum), SN, **RFIDID**, NeedUnsetEas, Reader, CheckIn/OutResult.
- **acs_Entrance/Reader/Zone/Antenna** — иерархия СКУД (IP/Port/направление).
- **PROP_*** (серверные настройки `PROP_Settings`): `PROP_AIS` (ИРБИС: ServerAddress/Port/Login/Password, DaysToReturnCount, BooksDB, IsAgeControl, IsOnlyOneProlong, IsAllowTakeIfDebts/ReturnIfDebts, IsUseSIP2), `PROP_Common`, `PROP_Email` (SMTP), `PROP_Proxy`, `PROP_FaceDetect`.
- **CameraFD** — параметры Dahua (см. §5).

## 5. FaceID / камеры (Dahua)

Логика — через сторонние DLL `AJCamera` (класс `Camera`), `FaceDetectDll` (класс `Device` = NVR/регистратор), `FaceID.Events`. NetSDKCS вызывается внутри них. Параметры — `App.CameraFD` (из `FaceDetect.xml`).
- Подключение (`Modules.Readers/FaceDetectPage`): `Device fd=new Device(RegistratorIP, Port=37777, Login=admin, Password)` + `Camera=new Camera(CameraIP, Brightness, Contrast, Sharpness)`; `Camera.Init/Connect`; `fd.Connect`; `fd.StartVideoStream(ChannelNo, handle,…)`.
- Распознавание: `fd.StartRecognize(ChannelNo,…)`; событие `Fd_OnFaceRecognized(e)` → `int.TryParse(e.UserID)` → `WS.ReaderInfoGet(id)` → `RecognizedReader`. Используется в `btnFaceIDAuth_Click` (BookCheckOut/ReaderForm/Readers).
- Снимок: `FaceDetectControlsPage.btnSnapshot_Click` (GDI `BitBlt` окна видео) → `WS.ReaderPhotoAdd(readerId, bytes)`.

## 6. Сводка: ИРБИС напрямую vs центральный сервис

- **Прямая ИРБИС (ABIS) + RFID (RDR/RFIDCore)** — операционные модули: **BookCheckInOut**, **SafeKeeper.OrderEditPage**, **Vending.OrderPage**, **BookKeeping** (только `GetDocInfo`), **Stuff.VisitorPage**, **Readers** (`GetClientName`). Методы ABIS: `Checkout/Checkin/Renew/GetClientName/GetDocInfo/GetClientChargedDocs/GetReaders/AddReader/AddReaderByCard/AddEkp/SetBookState`.
- **Только центральный сервис (WS)** — Gates, ACS, Monitoring, Dashboard, Stations, SmartShelves, Users, Libraries, Lic, VoiceAssistant, FaceDetect‑настройки, Banners, KPI. Эти модули администрируют данные, которые в БД устройств наполняют сами устройства.
- **Гибрид (FaceID):** распознавание — локальный Dahua SDK; идентификация/фото — через WS.

> Полный контракт центрального сервиса (route→params→DTO) — [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md). Интеграция с ИРБИС (поля RDR/910/691) — [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md).

## 7. Замечания для Biblio (попутные находки)
- Захардкоженные сервис‑пароли и AES‑ключи (секрет → защищённое хранилище, не копировать схему).
- `WebService` — Basic‑auth поверх http (нужен TLS+токены).
- Возможные дефекты исходника: `ACSEditPage.btnACSConfirm_Click` использует неактуальный `EntranceId=-1` при создании; вызов `ACSReaderAntennaAddModify` без `await`; Telegram без URL‑кодирования; нулевой IV в `TntCryptoUtils2`. (Не воспроизводить.)
