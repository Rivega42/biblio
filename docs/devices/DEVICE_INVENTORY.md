# DEVICE_INVENTORY — реестр файлов надстройки управления оконечными устройствами

> **Объект:** `C:\IRBIS64\Library Admin Server\` — надстройка **IDlogic Admin Server (LAS)** + локальный агент **EasyBook TagService** для управления внешними устройствами библиотеки (RFID-считыватели, противокражные ворота, станции самообслуживания/постаматы, камеры бронирования SafeKeeper, умные полки, СКУД, камеры/FaceDetect) поверх САБ ИРБИС64.
> **Метод:** только статический анализ (печатные строки ASCII+UTF‑16LE, конфиги, логи, PDF‑руководство). Бинарники **не запускались**. Дампы строк — в `_recon/_scratch_devices/str_*.txt` (в репозиторий не коммитятся). Извлечение PDF — `pdftotext` → `_scratch_devices/manual.txt`.
> **Связанные доки:** [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) · [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
> **⚠ Секреты:** в конфигах найдены боевые креды/строки подключения (см. раздел 7). В этот реестр вынесены только структура и порты; **значения паролей не коммитятся** — `секрет → .env`.

## 1. Что это за поставка (резюме)

**IDlogic Admin Server** (производитель — ООО «АйДи‑Лоджик»/IDlogic, `info@idlogic.ru`, `www.id-logic.ru`, тел. +7 495 780‑86‑86 / +7 812 777‑33‑44) — WPF‑приложение «панель администратора» (`LibraryAdminServer.exe`, .NET, ModernWpf), входит в Единый реестр ПО РФ. Это **тонкий клиент центрального веб‑сервиса IDlogic** (WCF/REST `api.svc`), который агрегирует состояние всего парка устройств. Физическими устройствами LAS сам **не управляет** (кроме настольного RFID‑считывателя на ПК оператора и Dahua‑камер) — приводом ячеек/станций занимается прошивка станций + центральный сервер.

Ключевые компоненты поставки:
| Компонент | Файл | Роль |
|---|---|---|
| Панель администратора | `LibraryAdminServer.exe` (9.3 МБ, .NET/WPF) | GUI‑консоль управления всем парком устройств; клиент `api.svc` |
| ABIS‑интеграция | `EasyBookAbis.dll` (3.6 МБ) | подключение к ИРБИС (ManagedClient.4) и/или SIP2; читатели/книговыдача/заказы |
| RFID‑ядро | `EasyBook_RFid.dll` (809 КБ, Delphi) | абстракция ~15 семейств считывателей; модель данных метки (ISO 28560/Danish) |
| Локальный агент считывателя | `Distrib\TagServiceLAS\IDLogicTagServiceLAS.exe` | «EasyBook TagService» — драйвит настольный считыватель на удалённом ПК |
| Конфигуратор считывателя | `UniDllConfigurator.exe`, `TestUniDll.exe` | выбор/тест типа считывателя, запись `.cfg/.cfg3` |
| Лицензирование | `LicenseChecker.dll`, `EkpMed.dll(_x64)`, `*.ekp` | проверка лицензии устройства; чтение ЕКП/паспорта |
| Руководство | `Admin Server - Руководство.pdf` (16.5 МБ) | официальное руководство пользователя (12 модулей) |

> Версия сборки: `LibraryAdminServer.exe` собран **22.12.2025**; `EasyBookAbis.dll`/PDF — 13.08.2025. Есть встроенный голосовой ассистент на GPT (маршруты `/web/gpt/*`) — самые новые функции.

## 2. Структура каталога (верхний уровень)

```
C:\IRBIS64\Library Admin Server\
├─ LibraryAdminServer.exe            ← панель администратора (главный модуль)
├─ EasyBookAbis.dll                  ← интеграция с ИРБИС/SIP2
├─ EasyBook_RFid.dll                 ← RFID-ядро (native, Delphi)
├─ *.dll  (≈190 шт.)                 ← SDK устройств + .NET runtime (см. §3–§5)
├─ config.ini / options.ini          ← конфиг SendChar/TagService
├─ settings.xml                      ← ReaderPower
├─ DBSettings.xml                    ← строка подключения к центральному api.svc + Update/EKP/RFIDCore
├─ SIP2settings.xml                  ← (несмотря на имя) подключение к ИРБИС + политика книговыдачи
├─ FaceDetect.xml                    ← конфиг Dahua-камеры/NVR для FaceDetect
├─ EasyBook_rfid.cfg / .cfg3 / .ekp  ← бинарный выбор считывателя / web-привязка / лицензия
├─ versions.inf                      ← манифест обновления (файл;MD5)
├─ Admin Server - Руководство.pdf    ← руководство (12 модулей)
├─ Log\AppLog.txt                    ← лог ошибок приложения (NLog)
├─ sdk_log\sdk_log.log               ← лог Dahua NetSDK (камеры/FaceDetect)
├─ Configurations\easybook_rfid.cfg3 ← альт. web-привязка (другой DeviceID)
├─ Templates\RDRToolDoc.docx         ← шаблон отчёта по читателям (RDR)
├─ ru-RU\ en-GB\ eu-ES\              ← локализация ModernWpf (рус/англ/баскский)
├─ ACS-Unified-MSI-Win-4300 (DRIVER WIN)\  ← драйвер PC/SC ACS ACR (см. §6)
├─ CP210x_Windows_Drivers\           ← драйвер Silicon Labs USB↔UART (COM-считыватели)
├─ Driver_microM\                    ← драйвер MicroEM uEMqSCR (ЕКП/контактный)
├─ Distrib\                          ← дистрибутивы драйверов + полный TagServiceLAS
│   ├─ TagServiceLAS\               ← готовый комплект агента считывателя (см. §4)
│   ├─ Driver_ACR1281.zip / Driver_MicroEM.zip / Driver_RRU1861.zip
├─ Download\                         ← per-branch комплекты разворачивания (дубликаты TagServiceLAS)
│   ├─ Kuchumov3in1\ , «н20 на CCPL-1421 …»\ , «охта8 5800 - 6047»\
├─ Update\                           ← каталог под LAS_Update.zip
└─ Temp\
```

## 3. Главные исполняемые/интеграционные модули (.NET)

| Файл | Размер | Дата | Тип | Назначение (гипотеза/подтверждение) |
|---|---|---|---|---|
| `LibraryAdminServer.exe` | 9.31 МБ | 22.12.2025 | .NET WPF | **Панель администратора.** Модули `Modules.{Vending,SafeKeeper,Gates,Dashboard,BookCheckInOut,SmartShelves,FaceDetect,EKP,Users,…}`. Клиент центрального `api.svc` (REST/JSON, Basic‑auth). |
| `EasyBookAbis.dll` | 3.60 МБ | 13.08.2025 | .NET | **Интеграция с АБИС.** Встроенный `ManagedClient.4` (прямой ИРБИС TCP, `arm=B/C`), плюс клиент `SIP2`. Поиск/чтение/запись RDR/RQST/каталог, книговыдача/возврат/продление. MoonSharp(Lua) для конвертации меток. |
| `EasyBook_RFid.dll` | 809 КБ | 27.01.2025 | native (Delphi) | **RFID‑ядро.** Классы `TReader_*` для ~15 семейств считывателей; модель данных `TRFIDDanish` (ISO 28560/Danish). Экспорт C: `DeviceOpen/Close`, `RfidReadDataByCfg`, `RfidDM15Read/Write`, `RfidEASGet/Set`, `ReaderPowerGet/Set`. |
| `Distrib\TagServiceLAS\IDLogicTagServiceLAS.exe` | 354 КБ | 24.07.2023 | .NET | **EasyBook TagService** — локальный агент: драйвит настольный считыватель, режим SendChar, `SocketServer`, флаг `UseSip`. Ставится на ПК сотрудника/киоск. |
| `UniDllConfigurator.exe` | 1.68 МБ | 27.01.2025 | .NET | «UniDll Configurator 3.0» — выбор типа считывателя (3 слота), COM/USB/TCP, режим чтения, EAS/AFI; пишет `.cfg/.cfg3`. |
| `TestUniDll.exe` | 1.10 МБ | 23.12.2020 | .NET | Тестовая утилита для проверки считывателя через то же ядро. |
| `ManagedClient.4.dll` | 462 КБ | 24.01.2022 | .NET | Клиент ИРБИС64 (ManagedIrbis, А.Нежданов). PDB `G:\ManagedClient.4-master\…`. Используется EasyBookAbis. |
| `LicenseChecker.dll` | 473 КБ | 16.04.2024 | .NET | Проверка лицензии: `IsLicenseValid`/`IsDeviceLicenseValid` (файл `*.ekp`). |
| `EkpMed.dll` / `EkpMed_x64.dll` | 1.98/2.79 МБ | 16.04.2024 | native | Чтение ЕКП/паспорта (контактный считыватель) при регистрации читателя. |
| `MoonSharp.Interpreter.dll` | 409 КБ | — | .NET | Интерпретатор Lua — правила конвертации кода метки. |
| `BLToolkit.4.dll` | 1.85 МБ | — | .NET | ORM локальной БД IDlogic (карты ЕКП, привязки RFID↔читатель, статистика). |
| `Newtonsoft.Json.dll` | 702 КБ | — | .NET | JSON для REST‑вызовов `api.svc`. |
| `NLog.dll` | 877 КБ | — | .NET | Логирование (`Log\AppLog.txt`). |
| `MailKit.dll`/`MimeKit.dll`/`BouncyCastle.Cryptography.dll` | — | — | .NET | SMTP‑уведомления читателям. |
| `EPPlus.dll` (+Interfaces/Drawing) | 3.0 МБ | — | .NET | Экспорт отчётов в XLSX. |
| `DocumentFormat.OpenXml.dll`/`OpenXmlPowerTools.dll` | — | — | .NET | Работа с DOCX (шаблоны отчётов). |
| `ModernWpf.dll`/`ModernWpf.Controls.dll`/`De.TorstenMandelkow.MetroChart.dll`/`LiveCharts*.dll` | — | — | .NET | UI/графики панели. |

## 4. SDK устройств — RFID‑считыватели (native)

> Полное сопоставление «класс EasyBook → вендор → DLL → диапазон» — в [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §2.

| Файл | Размер | Вендор / семейство | Диапазон / интерфейс |
|---|---|---|---|
| `FeIsc.dll` `FeCom.dll` `fetcp.dll` `feusb.dll` | 258/578/37/333 КБ | **FEIG OBID ISC** (HF) и **ISC.MRU102** (UHF) | HF 13.56 / UHF; транспорт COM/TCP/USB |
| `Clscrfl.dll` | 355 КБ | FEIG CPR обёртка `CLSCRF_*` | HF 13.56, COM |
| `HFReader.dll` | 374 КБ | RR7036 / RoyalRay HF | HF 13.56 (ISO14443/15693) |
| `rh_control.dll` | 310 КБ | IDlogic RH‑серия (HF) | HF 13.56, COM |
| `RRU1861.dll` | 333 КБ | ChaFon RRU1861 (UHF) | UHF EPC Gen2 / ISO18000‑63/6B |
| `RRU9816.dll` | 364 КБ | ChaFon RRU9816/RRU2861 (UHF) | UHF EPC Gen2 |
| `UHFAPI.dll` `UHFControl.dll` | 336/9 КБ | Chainway/IDlogic R3 (UHF, HID) | UHF EPC Gen2, USB‑HID |
| `IDlogicR3API.dll` | 88 КБ | IDlogic R3 (обёртка над UHFAPI) | UHF |
| `NURAPI.dll` `NurApiDotNet.dll` `IDLogicNURApi.dll`(`.Native`) | 200/101/211/7 КБ | **Nordic ID NUR** (UHF‑модуль) | UHF EPC Gen2/Gen2v2 |
| `rfidlib_reader.dll` `rfidlib_aip_iso15693.dll` `rfidlib_drv_rpan.dll` | 814/625/991 КБ | Andea rfidlib (FEIG‑производный) | HF ISO15693, COM/TCP/USB |
| `Andea.RPan.dll` `Andea.RPan.Native.dll` | 18/8 КБ | **Andea R‑Pan** (.NET обёртка) | HF; типы `LSGATE/MTGATE` (ворота) |
| `ZReader.dll` | 239 КБ | **IronLogic Z‑2 / Matrix** (USB) | HF 13.56, USB‑serial; GPIO `ZR_M3n_SetOutputs/GetInputs` |
| `scardsyn.dll` | 64 КБ | PC/SC синхронизация Mifare | контактный/PC‑SC |
| `hidapi.dll` | 79 КБ | HID‑транспорт (Chainway/NUR) | USB‑HID |
| `RFID_ANTIVOR_ActiveX.dll` | 418 КБ | **Противокражные ворота** (COM/ActiveX обёртка над EasyBook) | COM‑порт; `EAS_Set/Reset/Alarm` |

## 5. SDK устройств — камеры / видео (Dahua, native)

| Файл | Размер | Назначение |
|---|---|---|
| `dhnetsdk.dll` `dhconfigsdk.dll` `dhplay.dll` | 12.0/2.6/4.4 МБ | **Dahua NetSDK** — логин к IP‑камере/NVR, `CLIENT_DetectFace`, `CLIENT_RealLoadPictureEx`, видеопоток |
| `NetSDKCS.dll` | 250 КБ | .NET‑обёртка Dahua NetSDK (грузится в `btnFaceIDAuth_Click`) |
| `avnetsdk.dll` `AjNetSdkDll.dll` `AJCamera.dll` | 2.8 МБ/919/10 КБ | вспом. видео‑SDK |
| `FaceDetectDll.dll` (+`FaceDetect.xml`) | 28 КБ | локальный детектор лиц |
| `fisheye.dll` `ImageAlg.dll` `IvsDrawer.dll` `Infra.dll` `Stream.dll` `StreamSvr.dll` `NetFramework.dll` `json.dll` `libcurl.dll` `libeay32.dll` `ssleay32.dll` | — | зависимости Dahua SDK (видео/изображение/сеть/крипто) |

## 6. Драйверы устройств (INF/SYS/MSI)

| Путь | Содержимое | Для чего |
|---|---|---|
| `CP210x_Windows_Drivers\` | `CP210xVCPInstaller_x64/x86.exe`, `slabvcp.inf/.cat` | **Silicon Labs CP210x USB↔UART** (VID_10C4). Виртуальный COM для последовательных считывателей/ворот. По INF: `InitialBaudRate=115200, 8N1`. |
| `ACS-Unified-MSI-Win-4300 (DRIVER WIN)\` | `Setup.exe`, `x64/x86\ACS_Unified_PCSC_Driver-4.3.0.0.msi`, `ReadMe.txt` | **ACS Unified PC/SC** v4.3 — драйвер ридеров ACS ACR (ACR1281 и др.) для контактных/контактлесс карт (ЕКП). |
| `Driver_microM\Windows 7 x64\` и `Windows x32\{PC_SC,USB}\` | `uEMqSCR.sys/.inf/.cat`, `WdfCoInstaller01009.dll` | **MicroEM uEM USB SmartCard Reader** (VID_c251 PID_130a) — контактный считыватель ЕКП. |
| `Distrib\Driver_ACR1281.zip` | копия драйвера ACS | дистрибутив |
| `Distrib\Driver_MicroEM.zip` | копия драйвера MicroEM | дистрибутив |
| `Distrib\Driver_RRU1861.zip` | драйвер ChaFon RRU1861 (UHF) | дистрибутив |

## 7. Конфиги, логи, артефакты (детально)

| Файл | Содержимое (структура) | Замечания |
|---|---|---|
| `config.ini` | `[SendChar]` AddEnter/Delimiter/EasMode/OnlyUniqueReads/ChangePower; `[Conversion]` PlaySound; **`[IRBIS]` Ip/Port(6666)/Login/Password** | конфиг агента считывателя; разбор — в [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §3 |
| `options.ini` | `[Main]` EASMode/Interval(1000)/IsEnter/IsSingleRead | легаси‑вариант TagService |
| `settings.xml` | `<ReaderPower>7</ReaderPower>` | мощность РЧ настольного считывателя |
| `DBSettings.xml` | `ConnectionString=http://‹WCF_HOST›:8005/api.svc`; `UpdatePath=//SRV-RFID/…/LAS_Update`; `UseEKP=true`; `RFIDCoreConnectionString=http://127.0.0.1:8000;admin;‹SECRET›`; SMTP/proxy; `IsUseEAS/IsUsePrintReceipt/…` | **строка подключения к центральному сервису + RFIDCore. ⚠ секрет → .env** |
| `SIP2settings.xml` | **подключение к ИРБИС** (`DbIP/DbPort(6666)/DbLogin/DbPassword/IrbisDB=KNIGA%SERV21%`) + политика (`ReturnDaysCount=30`, `AllowTakeIfDebts`, `NeedCheckDebts`, `OnlyOneRenew`, `AgeControl`, `UseSIP2=False`) + `InstitutionID/LocationCode` | имя вводит в заблуждение: тут боевая строка ИРБИС. **⚠ секрет → .env** |
| `FaceDetect.xml` | Dahua: `CameraIP`, `RegistratorIP`(NVR), `Port=37777`, `ChannelNo=4`, `CameraID=17`, `Login/Password`, `VisitorsTimeoutLoading=30` | **⚠ пароль камеры → .env** |
| `EasyBook_rfid.cfg` (20 б) | бинарный (lightly‑encoded) выбор считывателя + параметры порта | пишет UniDllConfigurator |
| `easybook_rfid.cfg3` | `[Main]` DeviceID(GUID)/ServiceURL(`…:8005/api.svc`)/ReadTimeout(5000)/UseWebLog(0) | web‑привязка устройства (лицензия/веб‑лог) |
| `Configurations\easybook_rfid.cfg3` | то же, другой `DeviceID` | альтернативный профиль |
| `EasyBook_rfid.ekp` (12 б) | бинарный файл лицензии («EKP») | проверяется LicenseChecker |
| `versions.inf` | `имя_файла;MD5` для PDF/EasyBookAbis/EasyBook_RFid/LibraryAdminServer/UniDllConfigurator | манифест обновления |
| `Log\AppLog.txt` | NLog‑лог ошибок: модули `Vending/SafeKeeper/Gates/Dashboard/BookCheckInOut(FaceIDAuth)`; ошибки доступа к серверу/`NetSDKCS` | подтверждает состав модулей и Dahua‑путь |
| `sdk_log\sdk_log.log` | лог Dahua NetSDK: `CLIENT_LoginEx2 [IP=…:37777]`, `CLIENT_DetectFace`, `CLIENT_RealLoadPictureEx`, `CLIENT_MatrixGetCameras` | подтверждает FaceDetect/счётчик посетителей через камеры |
| `Templates\RDRToolDoc.docx` | шаблон отчёта по БД читателей RDR | — |
| `Distrib\TagServiceLAS\` | полный комплект агента: `IDLogicTagServiceLAS.exe` + ядро + все SDK + `config.ini/settings.xml/*.cfg/*.ekp` | то, что ставят на удалённый ПК/киоск |
| `Download\{Kuchumov3in1, н20 …, охта8 …}\` | per‑branch копии `TagserviceLAS.zip` + драйверы | комплекты разворачивания по филиалам (НЕ ПДн — это названия библиотек/филиалов) |

## 8. Карта «файл → класс устройства»

```
RFID настольный считыватель ── EasyBook_RFid.dll + (FeIsc|HFReader|RRU*|UHFAPI|NURAPI|rfidlib_*|ZReader|rh_control|Clscrfl) + config.ini/*.cfg
ЕКП/контактная карта ─────────  EkpMed.dll + scardsyn.dll + (ACS PC/SC | MicroEM uEMqSCR)
Противокражные ворота ────────  RFID_ANTIVOR_ActiveX.dll → EasyBook_RFid.dll (Andea R-Pan / FEIG EAS), COM
Камеры / FaceDetect / счётчик ─ dhnetsdk.dll + NetSDKCS.dll + FaceDetectDll.dll + FaceDetect.xml (Dahua)
Станции/SafeKeeper/полки/СКУД ─ LibraryAdminServer.exe (только метаданные) → api.svc (центральный сервис) → прошивка станций
ИРБИС/SIP2 ──────────────────  EasyBookAbis.dll (ManagedClient.4 / SIP2) ← SIP2settings.xml/config.ini[IRBIS]
Лицензия/обновление ──────────  LicenseChecker.dll + *.ekp + versions.inf + DBSettings.xml(UpdatePath)
```

## 9. Что важно для замены (указатели)

- Физический привод **ячеек постаматов/SafeKeeper и механики станций** в этих бинарниках **отсутствует** — он в прошивке станций + центральном сервере (см. [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)). Реплицируемо «из коробки»: **настольный RFID‑считыватель**, **противокражные ворота (COM, EAS)**, **интеграция с ИРБИС/SIP2**, **модель данных метки (ISO 28560/Danish)**, **REST‑контракт `api.svc`** (перечень операций — в [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §7).
- Для нашей Biblio критично воспроизвести: (1) серверный протокол ИРБИС (поднабор ManagedClient.4) **или** SIP2‑сервер; (2) поля БД RDR/RQST/каталог (30, 40, 910^A/B/H, 691); (3) REST `api.svc` для парка устройств; (4) кодирование метки. Полный чек‑лист — [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) §6.
