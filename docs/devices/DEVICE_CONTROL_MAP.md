# DEVICE_CONTROL_MAP — как управляется каждый класс устройств

> **Источник:** статический разбор `C:\IRBIS64\Library Admin Server\` — дампы строк `_recon/_scratch_devices/str_*.txt`, конфиги, `manual.txt` (PDF‑руководство). Ссылки в формате `str_<файл>` / `manual.txt:строка`. Где вывод — гипотеза, помечено **(инференс)**.
> **Связанные:** [DEVICE_INVENTORY.md](DEVICE_INVENTORY.md) · [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## 0. Архитектура управления (где что приводится)

```
                    ┌─────────────────────────────────────────────┐
                    │  Центральный сервис IDlogic  (api.svc)        │
                    │  http://‹WCF_HOST›:8005/api.svc  REST/JSON    │
                    │  агрегирует состояние всего парка устройств   │
                    └───────▲───────────────▲──────────────▲────────┘
        REST/JSON (читает/пишет МЕТАДАННЫЕ) │               │ REST
   ┌────────────────┐                       │               │
   │ LAS (панель    │  ← НЕ управляет       │      ┌────────┴─────────┐
   │ администратора)│    железом напрямую   │      │ Прошивка станций  │
   └────────────────┘                       │      │ (постамат/Safe-   │
                                            │      │ Keeper/полка/СКУД)│
   ┌──────────────────────────────┐         │      │ — привод ячеек,   │
   │ EasyBook TagService (агент)  │─────────┘      │   замков, конвейе-│
   │ на ПК сотрудника / киоске     │                │   ра — ЗДЕСЬ      │
   │  ├─ настольный RFID-считыватель│ ←ЛОКАЛЬНО (COM/USB/TCP/PCSC)      │
   │  ├─ SendChar (эмуляция клавы) │                └──────────────────┘
   │  └─ ИРБИС/SIP2 (книговыдача)  │
   └──────────────────────────────┘
   ┌──────────────────────────────┐
   │ Противокражные ворота         │ ←ЛОКАЛЬНО RFID_ANTIVOR_ActiveX (COM)
   │ Dahua-камеры / FaceDetect     │ ←ЛОКАЛЬНО dhnetsdk (TCP :37777)
   └──────────────────────────────┘
```

**Главный вывод:** локально и «по проводу» из этого ПО управляются три класса — **настольный RFID‑считыватель**, **противокражные ворота**, **камеры/FaceDetect**. Постаматы/станции/SafeKeeper/умные полки/СКУД для LAS — это записи в центральном сервисе; реальный привод ячеек/замков — в прошивке станций (см. [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1).

---

## 1. RFID настольный считыватель — общая модель (EasyBook)

Ядро `EasyBook_RFid.dll` (Delphi) прячет ~15 семейств считывателей за единым C‑экспортом (`str_EasyBook_RFid`):

| Экспорт | Назначение |
|---|---|
| `DeviceOpen` / `DeviceClose` | открыть/закрыть считыватель по конфигу |
| `IsReaderOnline` / `IsDeviceLicenseValid` | статус/лицензия |
| `RfidReadDataByCfg` (+`Ptr`,`CachePtr`) | **главный вход**: «прочитать книгу настроенным считывателем» |
| `RfidDM15Init/Read/RawRead/Write/Erase` | ISO15693 Danish Data Model: инициализация/чтение‑декод/сырое чтение блока/запись/стирание |
| `RfidEASGet` / `RfidEASSet` | прочитать/выставить EAS‑бит (противокражная подпись) |
| `RfidEASAFIPasswordSet` / `RfidLockSet` / `ConfigEASDataGet` | пароль EAS/AFI, блокировка, конфиг EAS |
| `ReaderPowerGet/Set`, `ReaderSound` | мощность РЧ, звук |

Базовый класс — `TRFIDReaderAbstract`, конкретные — `TReader_*`. Модель данных метки — `TRFIDDanish`/`IDLogic_Danish` (см. §4).

---

## 2. Поддерживаемые считыватели → вендор → DLL → протокол

Таблица типов из `UniDllConfigurator` (`str_UniDllConfigurator`, `Readers.Items.Strings`) + классы ядра (`str_EasyBook_RFid`):

| Тип (UniDll enum) | Класс EasyBook | Вендор / семейство | SDK DLL | Диапазон / воздух | Транспорт |
|---|---|---|---|---|---|
| 0 `NONE` | — | — | — | — | — |
| 1 `CARDMAN` | `TReaderACS`/`reader_CardMan` | HID **OMNIKEY CardMan 5x21‑CL** | `WINSCARD` (PC/SC) | HF 13.56 + контакт | PC/SC |
| 2 `FEIG_MR100` | `TReader_FEIGMR100` | **FEIG OBID ISC** (MR101/102) | `FeIsc`+`FeCom`/`feusb`/`fetcp` | HF 13.56 (ISO15693/14443) | COM/USB/TCP |
| 3 `FEIG_CPR30` | `TReader_FEIGCPR30` | **FEIG OBID CPR** | `FeIsc`/`Clscrfl` | HF 13.56 | COM |
| 4 `RRHF` | `TReader_RRHF`/`TRadel_RH3` | **RoyalRay/RR HF**, **Radel RH3** | `HFReader`/`rh_control`/`Clscrfl` | HF 13.56 (14443A/B+15693+ICODE) | COM |
| 5 `MICROEM` | `TReader_MICROEM` | **МикроЭМ (JSC MicroEM)** контактный | PC/SC `WINSCARD`+`scardsyn` | контакт (+Mifare) | USB PC/SC (VID_c251 PID_130a) |
| 6 `RADEL` | `TRadel_RH3` | **Radel** HF | `rh_control` | HF 13.56 | COM (RS485 BSA 0‑255) |
| 7 `Andea` | `TReader_ANDEA`/`reader_AndeaRPanHF_new` | **Andea R‑Pan** | `Andea.RPan`→`rfidlib_*` | HF ISO15693 (NXP ICODE SLI/SLIX) | COM 19200 8E1 / USB / TCP:4800 |
| 8 `RR UHF` | `TReader_RoyalrayUHF` | **ChaFon RRU1861** | `RRU1861` | **UHF EPC Gen2/ISO18000‑63+6B** | COM/USB/TCP |
| 9 `Bookos UHF` | `TReader_BookosUHF` | «Bookos» UHF | (UHF G2) | **UHF EPC Gen2** | COM/USB |
| 10 `RR 9816 UHF` | `TReader_Royalray9816UHF` | **ChaFon RRU9816/2861** | `RRU9816` | **UHF EPC Gen2** | COM/USB/TCP |
| 11 `FEIG U102 UHF` | `TReader_FEIGMRU102` | **FEIG ISC.MRU102** | `FeIsc` | **UHF 860‑960** | COM/USB/TCP |
| (новый UI) | `TReader_ChainwayR3` | **Chainway/IDlogic R3** ручной | `IDlogicR3API`→`UHFAPI`+`hidapi` | **UHF EPC Gen2** | USB‑HID |
| (новый UI) | (IDlogic NUR) | **Nordic ID NUR** модуль | `IDLogicNURApi`→`NurApiDotNet`→`NURAPI` | **UHF EPC Gen2/Gen2v2** | USB/TCP |
| (ядро) | `TReader_Z2` | **IronLogic Z‑2/Matrix** | `ZReader` | HF 13.56 (Mifare/EM/ICODE) | USB‑serial; GPIO `ZR_M3n_SetOutputs/GetInputs` |
| (ядро) | `TReader_3M` | **3M** библиотечный pad | native serial `\\.\COM` | HF 13.56 ISO15693 | COM |
| (ядро) | `TReader_ACS` | **ACS ACR1281** | `WINSCARD` (PC/SC) | HF 13.56 (PICC)+контакт | PC/SC |

**Режим чтения** (`rgMainPrimMode`, `str_UniDllConfigurator`): `ISO15 SN` (только UID) · `ISO15 DM` (Danish‑модель) · `ISO14 SN` (Mifare UID) · `ISO14 DM` · `ISO14 CUS` (кастом).

**Команды нижнего уровня (native, по вендорам)** — что слать в железо для своей реализации:
- **FEIG (`str_FeIsc`):** `FEISC_0x1C_EASRequest` (скан EAS), `…0x6A_RFOnOff`, `…0x6F_AntennaTuning`, `…0x71/0x72_SetOutput` (релейные выходы), `…0x74_ReadInput`, `…0x76_CheckAntennas`. ISO15693: `CLSCRF_ReadMultipleBlocks_15693`, `…WriteSingleBlock_15693`, `…SetEAS/ResetEAS/EASAlarm_15693`, `…WriteAFI_15693`.
- **ChaFon UHF (`str_RRU1861`/`str_RRU9816`):** `Inventory_G2`, `ReadData_G2`/`WriteData_G2`, `WriteEPC_G2`, `Lock_G2`, `SetEASAlarm_G2`/`EASAlarm_G2`/`CheckEASAlarm_G2`, `SetPowerDbm`.
- **Nordic ID NUR (`str_NURAPI`):** `NurApiReadTagByEPC`/`WriteTagByEPC`, `NurApiWriteEPC`, `SetLockByEPC`, Gen2v2.
- **Andea/rfidlib (`str_Andea.RPan`/`str_rfidlib_reader`):** `ISO15693_ReadSingleBlock/WriteSingleBlock/LockBlock`, `WriteAfi/ReadAfi`, `NXPICODESLIX_EableEAS/DisableEAS/EASCheck/LockEAS`, `RDR_SetOutput`/`cfg_do`/`RDR_CreateRS485Node`.
- **RH/Radel (`str_rh_control`):** `RH_Reader_ISO15693_WriteBlock`, `…AlarmEAS`, `RH_Device_ChangeBaudRate`, `RH_Device_Request`.

---

## 3. Конфигурация считывателя (config.ini / cfg3 / settings.xml)

`config.ini` (агент TagService, копия в `Distrib\TagServiceLAS\`):
```ini
[SendChar]
AddEnter=1          ; добавить Enter/CR после отправки кода метки эмуляцией клавиатуры
Delimiter=,         ; разделитель между несколькими кодами в одном чтении
EasMode=None        ; EAS при чтении: None | Set/Reset/Check (None = не трогать бит)
OnlyUniqueReads=1   ; подавлять дубли подряд (антидребезг)
ChangePower=1       ; разрешить сервису менять мощность РЧ (вместе с settings.xml)
[Conversion]
PlaySound=0         ; писк при успешном чтении (0=выкл)
[IRBIS]
Ip=127.0.0.1        ; куда подавать код метки (хост ИРБИС-сервера)
Port=6666           ; TCP-порт ИРБИС (6666 = дефолт)
Login= / Password=  ; учётка ИРБИС (пусто = аноним)
```
`options.ini` (легаси): `[Main] EASMode=0/Interval=1000/IsEnter=0/IsSingleRead=0`.

`easybook_rfid.cfg3` — привязка устройства к веб‑сервису (лицензия/веб‑лог):
```ini
[Main]
DeviceID=‹GUID›                       ; ид устройства для лицензирования (DeviceIsLicenseValid)
ServiceURL=http://‹WCF_HOST›:8005/api.svc
ReadTimeout=5000                       ; таймаут чтения метки, мс
UseWebLog=0                            ; слать события чтения в веб-лог
```
`settings.xml`: `<ReaderPower>7</ReaderPower>` — уровень мощности РЧ (→ `ReaderPowerSet`; шкала зависит от устройства, **(инференс)** ~середина).

`EasyBook_rfid.cfg` (20 б, бинарный) — выбор считывателя + параметры порта (COM#/bus/TCP), пишется UniDllConfigurator. `EasyBook_rfid.ekp` (12 б) — файл лицензии, проверяет `LicenseChecker`.

**Транспорт по умолчанию:** последовательные считыватели подключаются через **CP210x USB↔UART** (по INF `115200, 8N1`). Andea: `BaudRate=19200;Frame=8E1;BusAddr=255` (COM) либо `RemotePort=4800` (TCP). MicroEM/ACS/OMNIKEY — PC/SC.

**Режим SendChar** — «эмуляция клавиатуры»: после декодирования метки в строку сервис **печатает её в активное окно** (как с клавиатуры), опц. Enter (`AddEnter`), разделитель и антидребезг. Позволяет вводить RFID/штрихкод в любое окно (АРМ Каталогизатор, OPAC) без интеграции (`manual.txt:717` — «работает аналогично EasyBook TagService… для ИРБИС АРМ Каталогизатор»).

---

## 4. Модель данных RFID‑метки (как закодирована книга)

**HF‑метка книги = ISO 15693 + «датская модель данных» (ISO 28560‑2 / Danish Data Model).** Класс `TRFIDDanish`/`IDLogic_Danish` (`str_EasyBook_RFid`). Сериализатор имеет формат `%s=%d;%d;%d;%s;%s;%s,` — код + три целых (счётчики part/of‑parts/блок) + строковые поля (библиотека‑владелец/инфо комплекта/штрихкод). Ошибки декода: «Input data is missing or corrupt».

**Блочные примитивы (ISO15693):** `RfidDM15Init/Read/RawRead/Write/Erase`; native `ISO15693_ReadSingleBlock/WriteSingleBlock/ReadMultipleBlock/WriteMultipleBlocks/LockBlock`. Идентификация: `Inventory`/`GetUID` → `ISO15693_GetSystemInfo` (UID 8 байт hex).

**AFI (Application Family Identifier)** — настраиваемые байты `AFI ON`/`AFI OFF`: поля `edAFION`/`edAFIOFF` (UniDll), свойства `Value_AFI_ON`/`Value_AFI_OFF`/`IsAFI` (LAS), запись `ISO15693_WriteAFI`/`LockAFI`. Противокражка может работать **через смену AFI** (циркулирующее vs защищённое значение) — классические библиотечные `0x07`/`0xC2` вводятся пользователем в `edAFION/edAFIOFF` (**(инференс)** — в бинарниках это конфигурируемые строки, дефолт `00000000`).

**EAS (Electronic Article Surveillance, противокражный бит)** — основной механизм «антивор»:
- EasyBook: `RfidEASGet`/`RfidEASSet`, `ConfigEASDataGet`, лог `RfidEASGet res=%d;Value=%d`.
- Native NXP ICODE SLI/SLIX: `NXPICODESLIX_EableEAS/DisableEAS/EASCheck` (+LockEAS); FEIG: `CLSCRF_SetEAS/ResetEAS/EASAlarm_15693`, `FEISC_0x1C_EASRequest`; UHF: `SetEASAlarm_G2`.
- LAS: `AntitheftBits`, `IsUseEAS`, `SetEAS`/`UnsetEAS`, `FromEASStructToString`/`FromEASStringToStruct`, пароль `EASorAFIPassword`. EAS можно **запаролить** (`RfidEASAFIPasswordSet`).
- DSFID: `ISO15693_WriteDSFID/LockDSFID`.

**UHF‑метка книги = EPC Gen2:** код книги в банке **EPC** (`WriteEPC_G2`/`NurApiWriteEPC`), USER/EPC‑банки `ReadData_G2/WriteData_G2/Lock_G2`. UHF‑«EAS» эмулируется флагом privacy/alarm.

**Связь с ИРБИС:** инвентарный/штрихкод книги (`InventoryNumber`) кодируется в Danish‑payload (HF) либо в EPC (UHF); декодированный код уходит в ИРБИС (порт 6666) и/или печатается SendChar. Контактные карты (ACS/MicroEM/CardMan) несут ID читателя (`MifareUID`/`UID`) для привязки ЕКП.

---

## 5. Противокражные RFID‑ворота (антивор)

`RFID_ANTIVOR_ActiveX.dll` — **in‑process COM/ActiveX** (Delphi). Сам в железо не ходит — делегирует в `EasyBook_RFid.dll`.

**COM‑интерфейс `IRFID_ANTIVOR`** (ProgID `RFID_ANTIVOR_ActiveX`, лог `IrbisAntivor.log`):
| Метод | Параметры | Назначение |
|---|---|---|
| `ReaderOpen` | **`ComPort`** | открыть считыватель ворот (только COM!) |
| `ReaderClose` | — | закрыть |
| `IsReaderOpen` | →`KValue` | статус |
| `ReaderDataGet` | `DataDelimiter`,`OperationResultID`→`ReaderString` | получить считанные метки (скан‑цикл) |
| `EAS_Set` | `Serial`,`ErrorText` | взвести EAS (защитить) |
| `EAS_Reset` | — | снять EAS |
| `EAS_Alarm` | →`IsAlarm` | вернуть флаг тревоги |

Импорт из `easybook_rfid.dll`: `ReaderPowerGet/Set`, `RfidEASSet/Get`, `RfidReadDataByCfg`, `IsReaderOnline`. То есть `EAS_Set/Reset`→`RfidEASSet`, тревога→`RfidEASGet`/`RfidReadDataByCfg`.

**Протокол ворот:** Andea **R‑Pan** по RS485 (`19200, 8E1, BusAddr 255`) или TCP **:4800** или USB; воздух — **ISO 15693 / NXP I‑CODE EAS**. «Antivor» — это бренд IDlogic («противокражные ворота»), не отдельный протокол.

**Тревога:** программно‑опрашиваемый флаг — ворота непрерывно инвентаризируют метки и читают EAS‑бит; `EAS_Alarm` отдаёт `IsAlarm` наверх. Релейный выход «сирена/строб» можно поднять командами `FEISC_0x72_SetOutput`/`RDR_SetOutput`/`cfg_do`/`ZR_M3n_SetOutputs` (зависит от модели; конкретная привязка номера выхода — деталь монтажа).

**В LAS** ворота — это статистика и справочник: типы (иконки) `Andea`/`Cinema`/`Monogate`/`SenseGate`/`Other`; сущности `MON_Gate`, `MON_GateAlarm`, `MON_GateEASEvent`, `MON_GateCounter` (счётчик `CounterIP`/`CounterPort`/направление). События тревоги: дата/время + название книги + RFID‑код (`manual.txt:110`).

**Счётчик посетителей (вход/выход):** в `RFID_ANTIVOR_ActiveX.dll` **отсутствует** — он в прошивке ворот/отдельном датчике (`MON_GateCounter` лишь читает агрегаты с сервера). → [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §3.

---

## 6. Камеры / FaceDetect / счётчик посетителей по видео

**SDK:** Dahua NetSDK (`dhnetsdk.dll`) + .NET‑обёртка `NetSDKCS.dll` + `FaceDetectDll.dll`. Лог `sdk_log\sdk_log.log` показывает реальный путь:
`CLIENT_LoginEx2 [IP=…, port=37777]` → `CLIENT_DetectFace` → `CLIENT_MatrixGetCameras` → `CLIENT_RealLoadPictureEx`/`CLIENT_RealPlayEx`.

**Конфиг `FaceDetect.xml`:** `CameraIP`, `RegistratorIP` (NVR), `Port=37777`, `ChannelNo`, `CameraID`, `Login/Password`, `Brightness/Sharpness/Contrast=128`, `VisitorsTimeoutLoading=30`. **⚠ пароль камеры — секрет → .env.**

**FaceID‑авторизация** (модуль «Библиотекарь», `BookCheckOutPage.btnFaceIDAuth_Click`): динамически грузит `NetSDKCS` (Dahua), распознаёт лицо камерой/NVR, колбэк `Fd_OnFaceRecognized`; находит читателя как альтернативу карте (`manual.txt:430`). Привязка лица: снимок (`btnSnapshot_Click`) → `ReaderPhotoAdd`.

**Счётчик посетителей по видео:** операции `VisitorsGet`/`KPICamerasGet` (агрегация серверная по списку камер и диапазону дат).

---

## 7. Станции самообслуживания / SafeKeeper Pro / умные полки / СКУД — через центральный сервис

> Для LAS это **записи в центральном сервисе** `api.svc` (REST/JSON, Basic‑auth). Привод железа (ячейки, замки, конвейер) — в прошивке станций; в этих бинарниках команд открытия ячеек/реле **нет** (проверено грепом: ни `OpenCell/OpenDoor/Unlock/Relay/Modbus/SerialPort`). → [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1.

### 7.1 Контракт центрального сервиса (то, что наша система должна предоставлять/заменить)
Транспорт: HTTP **REST + JSON** (Newtonsoft), заголовки `application/json`, `Authorization: Basic`, выгрузки `application/zip`/XLSX. Префиксы маршрутов: `/las/`, `/web/`, `/web/gpt/`. Полный перечень операций (из `str_LibraryAdminServer`):

| Класс | Операции (Get=чтение, Modify/AddModify=upsert, Set=поле) |
|---|---|
| **Станции/Vending** | `StationsGet`, `StationModify`, `StationDataGet`, `StationEventStatsGet`, `StationEventsHistoryGet`, `StationAliveMonitoringGet`, `StationsWithCoordinatesGet`, `/web/VendingsGet`, `VendingOrdersGet`, `VendingsEventsHistoryGet`, `VendingsSafekeepersGet`, `BooksOnVendingStationGet`, `info_StationsGet/AdvancedGet` |
| **SafeKeeper** | `SafeKeepersGet`, `SafeKeeperInfoGet2`, `SafeKeeperModify`, `SafeKeepersForOrderGet`, `OrdersGet`, `OrderModify`, `OrderBodyGet`, `OrderBodyModify`, `OrderBookProcessedSet`, `SafeKeeperHistoryGet`, `SafeKeeperHistoryMasterGet`, `MastersRFIDGet`, `MasterRFIDModify`, `SafeKeepersMasterRFIDGet`, `SafeKeeperMasterRFIDModify`, `info_SafeKeepersGet/AdvancedGet` |
| **Умные полки** | `BooksOnShelfGet`, `BookCellsOnShelfGet`, `SmartShelfReturnsGet`, `SmartShelfStatGet`, `info_SmartShelvesGet/AdvancedGet` |
| **Ворота** | `GatesGet`, `GateModify`, `GateTypesGet`, `GateDataGet`, `GateAlarmGet`, `GateAlarmsGet`, `GateCountersGet`, `GateEASEventsGet`, `info_EASGet/AdvancedGet` |
| **СКУД/ACS** | `ACSGet`, `ACSEventsGet`, `ACSAdvancedEventsGet`, `ACSReaderModify`, `ACSReaderAntennaAddModify`, `ACSReaderAntennasGet`, `ACSReaderTypesGet`, `ACSZoneModify`, `EntranceModify`, `info_ACSGet/AdvancedGet` |
| **Хранение фонда** | `BookCasesGet`, `BookCasesAndShelvesGet`, `BookCaseAddModify`, `BookCaseSectionsGet/AddModify`, `BookShelfAddModify`, `BookCellAddModify`, `BooksOnCellGet`, `BookKeepingBooksGet`, `BookKeepingBookInfoGet/Remove/Search`, `BookKeepingBookToCellBind`, `BookKeepingHistoryAdd/Get/StatGet`, `BookKeeping*Background*` |
| **Афиша/баннеры** | `BannersGet`, `BannerAddModify`, `BannerTaskAddModify`, `StationsByBannerIDGet` |
| **FaceDetect/камеры** | `FaceDetectDevicesAndCamerasGet`, `FaceDetectStationsGet`, `FaceDetectCameraModify`, `FaceDetectCameraToStationAttach`, `FaceDetectDeviceModify`, `KPICamerasGet`, `VisitorsGet` |
| **Устройства/общее** | `DevicesGet`, `DeviceModify`, `DeviceDataGet`, `DeviceTypesGet`, `DevicesLastHistoryGet`, `DesktopDeviceInfoGet`, `DesktopDeviceConfigGet`, `info_DesktopDevicesGet/AdvancedGet`, `info_EquipmentGet` |
| **Книги/библиотеки** | `BooksGet`, `BookCoverGet`, `BookModify`, `BookToLibBooksAdd`, `BookFromLibBooksGet`, `LibrariesGet`, `LibraryModify`, `TSLibraryUpdate` |
| **Читатели** | `ReadersGet`, `ReaderInfoGet`, `ReaderModify`, `ReaderPhotoAdd/Delete` |
| **Пользователи/доступ** | `LoginInfoGet/Modify`, `LoginModulesAccessGet`, `UsersInfoGet`, `UserModify`, `UserModulesAccessAddModify`, `RoleTypesGet` |
| **KPI/отчёты/лог/обновление** | `KPIServicesGet`, `KPIServiceModify/Apply`, `KPIEmployeeDailyReportGet`, `ExternalLogAdd/Get`, `KeyUpdate`, `SettingsGet/Modify`, `ManualGet`, `ColorsGet`, `upd_IsUpdateAvailable`, `upd_Update`, `upd_UpdateInfoGet` |
| **Голосовой ассистент (GPT)** | `/web/gpt/GetAnalytics`, `GetDashboardMetrics`, `GetTopQueries`, `GetVoiceAssistantSettings`, `GetVoiceResponseTemplates`, `Update…` |

### 7.2 Станции самообслуживания (киоски книговыдачи / постаматы)
Сущность `Station`: `StationID`, `StationName`, `StationTypeID/Name`, `Coordinates` (для схемы зала), `IsOnline`/`DateLastOnline`, **`IsPrinterOk`** (чековый принтер), **`IsConveyorOk`** (механизм выдачи/конвейер). Записи LAS: только `StationModify` (переименование/перенос) + назначение баннеров. **Команд «выдать книгу/открыть лоток» нет** — книговыдача идёт на киоске, LAS читает события. Афиша: `BannerAddModify` (JPEG/PNG 16:9 1920×1080, интервал сек, период показа).

### 7.3 SafeKeeper Pro (камеры бронирования / ячейки)
Сущности: `SafeKeeper` (`SafeKeeperId`, `HardwareID`, `SerialNumber`, счётчики ячеек `CellsCount/Vacant/Busy`); ячейка (`CellNo`, `CellNumberShifted`, `IsBusy`, `CellContent`, `UserFIO/UserCode`, `DateBusy`, `StorageTimeHint`); заказ `SK_Order` + тело `SK_OrderBody`. **Мастер‑ключ** — RFID‑карта сотрудника (`SK_MasterRFID`), привязана к конкретным камерам.

**Состояния заказа (6, `manual.txt:174,178`):**
```
Создан ──▶ Подготовлен ──▶ Укомплектован ──▶ Выдан
(Created)  (Prepared)      (Completed)        (Issued)
   │            │                                 └─▶ Выдан с ошибками (ABIS-запись не прошла, повтор из LAS)
   └────────────┴──────────────────────────────────▶ Отменён (Cancelled)
```
**Открытие ячейки:** физически — мастер‑ключом **на самой камере** (`manual.txt:225` «сервисные открытия ячеек», `:231` «нужен мастер‑ключ»); укомплектование — «с помощью камеры бронирования» (`:174`). LAS лишь пишет `OrderModify`/`OrderBookProcessedSet`/`SafeKeeperModify` через сервис. Привод соленоида ячейки — в контроллере камеры. → [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1.

### 7.4 Умные полки (SmartShelf)
Сущность `SS_BookOnShelf`; операции `BooksOnShelfGet` (что сейчас на полке), `SmartShelfReturnsGet`, `SmartShelfStatGet`. Полка/киоск сама пушит RFID‑инвентаризацию на сервер; LAS читает. Вкладки: Состояние/Возвраты/Статистика (`manual.txt:304‑336`).

### 7.5 СКУД (контроль доступа / турникеты)
Сущности: `ACS_Entrance` (проход), `ACS_ReaderType`/`ReaderAntenna` (стационарный считыватель + антенна), `ZoneID/ZoneName` + направление (`acs_Directiontype`), `ACS_Event`. Идентификатор посетителя — RFID‑карта/пропуск, считанная на антеннах; проход = (считыватель/антенна, зона, направление, время). `manual.txt:384‑424`.

### 7.6 Хранение фонда (адресное хранение)
Иерархия `BookCase`(стеллаж)→`Section`(секция)→`Shelf`(полка)→`Cell`(ячейка); привязка `BookKeepingBookToCellBind`; инвентаризация/перемещение/привязка с мобильным RFID; отчёты (XLSX); конструктор схемы зала. `manual.txt:528‑682`.

---

## 8. Сводка: что реплицируемо «по проводу» прямо сейчас

| Класс | Управление в этом ПО | Реплицируемо нами |
|---|---|---|
| Настольный RFID‑считыватель | **да** — EasyBook ядро, COM/USB/TCP/PCSC, команды по вендору | **да**, полностью (см. §2,§4) |
| Противокражные ворота | **да** — COM, EAS_Set/Reset/Alarm (Andea R‑Pan/FEIG) | **да** (см. §5) |
| Камеры/FaceDetect | **да** — Dahua NetSDK TCP:37777 | **да** (если Dahua) |
| Модель данных метки | **да** — ISO 28560/Danish (HF), EPC (UHF) | **да** (см. §4) |
| Станции/SafeKeeper/полки/СКУД | **нет** — только метаданные через `api.svc` | **частично**: реплицировать REST‑контракт (§7.1); привод ячеек — нужен доступ к станции (→ OPEN_QUESTIONS) |
