# TAGSERVICE_FUNCTION_MAP — карта функций EasyBook TagService (IDLogicTagServiceLAS.exe)

> **Источник:** ПОЛНАЯ C#‑декомпиляция (ilspycmd) — `_scratch_devices/dc_TagService/` (66 файлов). WPF/.NET 4.5 **x86**, зависимости `ManagedClient.4.dll`, `Newtonsoft.Json`. `App.Version="2.0"`, копирайт «IDLogic 2021». Гипотезы — **(инференс)**.
> **Связанные:** [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md) · [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) · [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md)
> **⚠ Секреты:** захардкоженные креды/ключи (resx, `TS1Worker`) — `секрет → .env`, значения не вынесены.

## 1. Что это и жизненный цикл

TagService — **локальный фоновый трей‑агент** на ПК сотрудника/киоске. Драйвит настольный RFID‑считыватель (`EasyBook_Rfid.dll`) и связывает четыре мира:
- **активное окно Windows** — эмулирует ввод кода метки/ЕКП «с клавиатуры» в АРМ ИРБИС (Каталогизатор, Регистрация читателя);
- **локальный TCP‑сокет `:6001`** — текстовый протокол, которым внешнее ПО командует считывателем (читать UID, ставить/снимать EAS) — см. §4;
- **ИРБИС64** (`ManagedClient64`, АРМ `C`) — см. §5;
- **центральный сервис IDlogic** (REST `/easybookdll/*` **или** прямой SQL) — лицензия/читатели/health — см. §6.
Плюс чтение **ЕКП** через `EkpMed.dll`.

**Цикл:** `App.Main` → `Application_Startup` (single‑instance, `LoadAppsHeaders` ← `apps.txt`, создаёт `Reader`) → `MainWindow` ctor (лицензия `IsDeviceLicenseValid`/`IsLicenseValid`, создаёт `Irbis`) → **`LoadingWindow.Window_Loaded`** (главная инициализация: `Config.GetDeviceSerial`←`easybook_rfid.cfg3 DeviceID`, выбор backend `ServiceURL?WebDb:DbWork`, `GetLibraryInfo`, разрешение ЕКП `TSWorker.DecryptLibWork`+`EKPWorker.IsAuthenticated`) → `MainWindow_Loaded` (поднимает `SocketServer :6001`, таймеры, прячет в трей).

**Таймеры (`MainWindow`):** `tmrSendKeys`(300 мс — главный цикл чтения→эмуляция ввода), `tmrCheckServices`(30 с — health ИРБИС/сервера), `tmrCheckReaderIsConnect`(10 с), `tmrUpdateMenu`(100 мс), `tmrShowStatus`(3 с). Доступ к считывателю сериализован `lock(App.ReaderLocker)`.

## 2. Пофайловая карта (по namespace)

### `TagService` (ядро/UI)
- **App** — точка входа; статика: `ReaderLocker`, `Reader Reader`, `IDatabase DbWork`, `Irbis IrbisWorker`, `Dictionary Ekps`, `IsEkpAllowed`, `AppHeaders`, `Version="2.0"`. Методы: `Main`, `Application_Startup`, `LoadAppsHeaders`(←`apps.txt`), `Application_DispatcherUnhandledException`(→`error.log`), `GetEncoding`.
- **MainWindow** — главная логика. Методы: `TmrSendKeys_Tick` (цикл), `TmrCheckServices_Tick`, `SendStringToActiveControl`, `GetActiveControl`, `SendKey`, `CheckLang`, `UpdateEas`, `GetPersId(sn)`, `AddReaderToDb(ekp,sn)`, `BtnCheckConnect_Click`, `StartStopSendChar`.
- **LoadingWindow** — инициализация backend/лицензии/ЕКП (`Window_Loaded`).
- **WaitEkpWindow** — модальное ожидание приложения ЕКП к считывателю (`PersID`, poll 1 с).
- **Reader** — обёртка над `Readers` (P/Invoke). `IsConnected`, `WriteDm(sn,dm)`, **`GetSnDms()`** (главное чтение всех меток), `SetEas/UnsetEas/GetEas`, `SetPower`, `PlaySound`. Поля `_readerNo=1`, `power`, `isPowerUsed`.
- **Readers** — статический контейнер P/Invoke (§3).
- **IniFile** — обёртка `Get/WritePrivateProfileString`; **сигнатура `Read(key, section, default)`** (нестандартный порядок).
- enum **WorkMode**{Conversion,SendChar}, **SendCharState**{Started,Stopped}.

### `TagService.Rfid`
- **EasWorker** — фоновый поток установки EAS из `AsyncPipe<string>`; событие `EasSetted`.
- **BWIsReaderOpen : BackgroundWorker** — асинхронная проверка `Reader.IsConnected`.

### `TagService.Models`
- **Tag** : Sn, Eas(bool?), Dm, Name, IsUseDm; `ToString()`=Dm.Id|Sn.
- **Dm** (данные DM‑15): TypeUsage, Country, Isil, ComplectNo=1, ComplectCount=1, Id.
- **Status**(Message,IsSuccess), enum **TypeUsage**{New,Book,Loading,Deleted,UserCard}.

### `TagService.Utils`
- **Irbis** — клиент ИРБИС (§5).
- **Config** — `easybook_rfid.cfg3`/`proxy.ini` (§8).
- **Settings** (синглтон) — `config.ini` (§8).
- **SendCharUtils** — режим по заголовку активного окна (§7).
- **DbWork : IDatabase** — прямой SQL backend (§6).
- **WebDb : IDatabase** (namespace `…DB`) — REST backend (§6).
- **MultiDataToDBSender / DataFromDBReceiver** — фоновые потоки записи/keep‑alive SQL.
- **EasSetWorker** — поток set/unset EAS из `AsyncPipe<KeyValuePair<string,bool>>` (с ретраем).
- **TSWorker / TS1Worker / TntCryptoUtils / Encryptor** — крипто/лицензия (§8).
- структуры `ConnectOptions`(Ip/Port/Login/Password), `UserInfo`(AbisCode,RFIDCode), `UserDebt`, `DbConnect`, enum `EasMode`{None,On,Off}.

### `TagService.Utils.SocketServer`
- **SocketServer** — TCP :6001 (§4); **Client** (буфер 102400, LastResponse, EasMode); enum **IrbisRequest** (коды команд).

### `EKPMedCSharp`
- **EKPWorker** — P/Invoke `EkpMed.dll` (§7); структуры `TPersData`, `TMainDocument`, enum `persDataFlags`.

### `AsyncData`
- **AsyncPipe<T>** (Push/Pop/PopAll), **AsyncProcessablePipe<T>**, **AsyncProcessor<T>** — потокобезопасные очереди/пул обработчиков.

### Global
- **CRC16** (CCITT 0x1021 + ZMODEM 0xA001) — только для лицензии. **TSWorker** — лицензия (§8). **Resources** — `WebLogin="ServiceLogin"`, `WebPassword="‹REDACTED›"` (захардкожено в resx). Конвертеры WPF — без бизнес‑логики.

## 3. P/Invoke в EasyBook_Rfid.dll (драйвер считывателя)

`TagService/Readers.cs` (возврат `int`, **1 = успех**):
```csharp
int IsReaderOnline(ref int stateOk, int readerNo=1);
int RfidReadDataByCfgPtr(ref int tagsCount, StringBuilder data, int readerNo=1, int fullDm=0, int eas=0, int readTypeId=-1);  // главное чтение
int RfidEASGetPtr(StringBuilder uid, ref byte value, int readerNo=1);
int RfidEASSetPtr(StringBuilder uid, byte value, int readerNo=1);
int RfidDM15WritePtr(StringBuilder uid, StringBuilder dm, int readerNo=1);
int RfidDM15InitPtr(StringBuilder uid, byte aTypeUsage, int readerNo=1);
int ReaderSound(int timeOut, int other, int count, int readerNo=1);
int ReaderPowerSet(byte value, int readerNo=1);
int ReaderPowerGet(ref byte value, int readerNo=1);
int IsDeviceLicenseValid();        // MainWindow
```
+ `LicenseChecker.dll!IsLicenseValid()`; user32/kernel32 для эмуляции клавиатуры (§7).
`RfidReadDataByCfgPtr` пишет в `data` CSV‑строку меток, разбор по `,` и `=`/`;`; «маяк» `AABCDEFF`(len 24) фильтруется. DM‑строка: `"{TypeUsage};{ComplectCount};{ComplectNo};{Id};{Country};{Isil}"`.

## 4. Сокет‑сервер :6001 — протокол управления считывателем (КЛЮЧ для Biblio)

`TagService.Utils.SocketServer/SocketServer.cs`. TCP `IPAddress.Any:6001`, `Listen(5)`, async accept/receive/send. Кодировка **UTF‑8**; вход очищается от `\0` (буфер 102400); **ответ + терминатор `"\r"`**. Лог `server_log.txt` при `Settings.SaveServerLog=1`. CRC в сокет‑протоколе **не** используется.

Первые **2 символа** = код команды (enum `IrbisRequest`):

| Код | Команда | Вход | Ответ |
|---|---|---|---|
| `75` | ChangeEasMode | `75`+режим(`0/1/2`) | пусто |
| `77` | **ReadUids** | `77` | `78`+кол‑во(`"00"`)+по метке `UI{nn}{sn≤16}SI{nn}{sn|dm.Id}|` |
| `79` | ReadFullTags | `79` | `"8000"` (заглушка) |
| `81` | **WriteEas** | `81`+(`1`=set/иначе unset)+опц. `UI{nn}{uid16}…` | `82`+симв+okCount(`"00"`)+`UI{nn}{uid}…` |
| `97` | RepeatResponse | `97` | последний `LastResponse` |

Детали `77`: вызывает `Reader.GetSnDms()`; UHF (>16 симв.) → UID = последние 16 симв., запоминается `uhfTags[uid]=sn`; ЕКП (Dm==null, Sn.Length==14, при `IsEkpAllowed`) → код через кэш `Ekps`/`DbWork.FindReader`/UI‑окно, блок `7801UI…SI…|` + async `AddReaderToDb`. Детали `81`: до 2 попыток `SetEas/UnsetEas` на UID (через `uhfTags`), затем `Reader.SetPower()`.

## 5. ИРБИС (Irbis.cs)

Клиент **`ManagedClient64`** (`ManagedClient.4.dll`):
```csharp
connectionstring = $"host={Ip};port={Port};user={Login};password={Password};arm=C;";  // АРМ C (Каталогизатор)
client.Timeout = 5000;  // параметры из config.ini [IRBIS], дефолт 127.0.0.1:6666
```
БД по умолчанию **`RDR`** (`Rdr="RDR"`). Операции: `Connect/Disconnect`, `NoOp` (keep‑alive), `IsConnected/IsDbOk`, **`GetClientInfo(clientID)`** (`PushDatabase("RDR")`→`GetRecordFromRdr(clientID,"RI")`→`ReaderInfo.Parse`), `GetRecordFromRdr(id, queryType)` (`SearchRead("{queryType}={id}")`, 3 ретрая+реконнект), **`GetDocDuedate(docID)`** (поле **40**: `^A`,`^F` (нач. `*`), `^H`==docID → `^E` дата), `WriteRecord` (3 попытки), `PushDatabase/PopDatabase`. Префиксы поиска: **`RI=`** (читатель по идентификатору/RFID), **`H=`** (документ). Результат `GetClientInfo` → регистрация ЕКП в центр. БД (`AddReaderToDb`).

## 6. Центральный сервис — два backend'а (IDatabase)

Интерфейс `IDatabase{GetLibraryInfo, GetTs, CheckConnect, FindReader, AddReader, IsDbOpened}`. Выбор в `LoadingWindow`: есть `ServiceURL`→`WebDb`(REST), иначе `DbWork`(SQL).

### DbWork — прямой MS SQL (`SQLConnString` из cfg3)
| Метод | SQL |
|---|---|
| GetLibraryInfo(guid) | хран. `[lic_GetVersionByDeviceGUID] @guid` → `{Guid,TS}` |
| GetTs() | `SELECT TOP 1 TS1 FROM Owners` |
| CheckConnect() | `SELECT TOP 1 ID FROM Owners` |
| FindReader(code) | хран. `rdr_ReaderInfoGet @id=0, @rfidCode=code` → `{AbisCode,RFIDCode}` |
| AddReader(user,ekp,serial) | хран. `rdr_ReaderModify @opID=1,@readerID=0,@name,@birthDate,@abisCode,@rfidCode=ekp,@serialNumber, OUT @newID` |
+ keep‑alive `DataFromDBReceiver`: `Select 1 from lib_SNUID`.

### WebDb — REST (`ServiceURL` из cfg3)
`HttpWebRequest` POST, `application/json; charset=UTF-8`. **Auth: Basic `Base64(login:password)`**, где `login=ServiceLogin`, `password=‹REDACTED›` (захардкожено в resx). Эндпоинты `_url+"/easybookdll/…"`:
| Метод | Эндпоинт | Тело | Ответ |
|---|---|---|---|
| CheckConnect | `/easybookdll/IsServerAlive` | — | bool |
| GetLibraryInfo | `/easybookdll/LibraryInfoGet` | `{deviceID}` | `{LibraryID,TS,TS1}` |
| FindReader | `/easybookdll/ReaderInfoGet` | `{id:0,rfidCode,deviceID}` | `List<UserInfo>` |
| AddReader | `/easybookdll/ReaderModify` | `{opID:1,readerID:0,name,abisCode,rfidCode,email,serialNumber,deviceID}` | bool |

Плюс нативное ядро (`EasyBook_RFid.dll`) шлёт на тот же `ServiceURL`: `/easybookdll/DeviceIsLicenseValid`, `/DeviceDataAdd` (health `{deviceID, softOnlineCount, deviceOkCount, deviceErrorCount}`), `/BooksCacheAddUpdate`.

## 7. SendChar (эмуляция клавиатуры) + ЕКП

**SendChar** — «вводит» прочитанный код в активное окно АРМ ИРБИС.
- **Когда** — `SendCharUtils.GetWorkMode()`: заголовок активного окна (UPPER/trim) ∈ `{КАТАЛОГИЗАТОР, 910, СВЕДЕНИЯОБЭКЗЕМПЛЯРАХ, БЛОКНОТ, NOTEPAD}` → CATALOG; `{РЕГИСТРАЦИЯЧИТАТЕЛЯ}` → READER; либо ∈ `App.AppHeaders`(`apps.txt`); иначе NONE (ввод не делается).
- **Как** — `TmrSendKeys_Tick`(300 мс): `Reader.GetSnDms()` → ЕКП(14 симв.)→код через `Ekps`/`DbWork.FindReader`/`GetPersId`→`AddReaderToDb`; обычная→`tag.ToString()`+`UpdateEas`; дедуп `OnlyUniqueReads`; склейка `Delimiter`; опц. `+\r\n`(`AddEnter`); `SendStringToActiveControl`.
- `SendKey`: `PostMessage(handle, WM_CHAR=258,…)` для символов, `WM_KEYDOWN=256` для `\n/\r`, `Sleep(10)`; `lParam` через `OemKeyScan`; раскладка `00000409`(US) через `LoadKeyboardLayout`+`WM_INPUTLANGCHANGEREQUEST`.

**ЕКП** (`EKPMedCSharp/EKPWorker.cs`, `EkpMed.dll`, cdecl): `getVersion`, `GetReaderList`, `Authorization(password)`, `GetID/GetPersID`, `GetPersData(flags)`, `GetMainDocument`, `GetPhoto`. Высокоуровневые: `IsAuthenticated(key)`→`Authorization()==0x9000(36864)`, `GetPersData(31)`. Гейт: `App.IsEkpAllowed` (крипто TS) **и** `IsAuthenticated`. Прочитанный `PersID` кэшируется в `Ekps[sn]` и регистрируется (`AddReaderToDb`→`IrbisWorker.GetClientInfo`→`DbWork.AddReader`).

## 8. Конфиги и шифрование

- **`easybook_rfid.cfg3`** `[Main]`: `DeviceID`(GUID лицензии), `SQLConnString`(MS SQL), `ServiceURL`(REST; если задан → WebDb). `proxy.ini`: `ProxyIP/Login/Password/Port`.
- **`config.ini`** (через `Settings`, **`Read(key,section,default)`**): `[SendChar]` AddEnter=1, Delimiter=`,`(значение `NewLine`→`\r\n`), EasMode=None, OnlyUniqueReads=1, ChangePower=0, MaxPower=30, SaveServerLog=0; `[Conversion]` PlaySound=0; `[IRBIS]` IP=127.0.0.1, Port=6666, Login, Password.
- **`apps.txt`** — заголовки окон, где разрешён ввод. `server_log.txt`/`error.log` — логи.
- **Крипто:** `TntCryptoUtils` AES‑128 (ключ = SHA‑256(pwd)[:16], **IV=нули**); `TS1Worker` — обёртка с **захардкоженным ключом** (`секрет`), `Generate/ParseData` (Base64+AES); `TSWorker.DecryptLibWork(guid,crc)` — лицензия по CRC16 GUID библиотеки (бросает «Unknown client!»/«Fake Data!»), бит флага = `IsEkpAllowed`; `CRC16` (CCITT+ZMODEM).

## 9. Дорожная карта повторения в Biblio
1. **Локальный TCP‑агент :6001** с протоколом §4 (`75/77/79/81/97`, поля `UI{nn}`/`SI{nn}`, разделитель `|`, терминатор `\r`, padRight 16, счётчики `"00"`).
2. **Драйвер считывателя** — обёртка над нативной DLL §3 (или наш аналог `IsReaderOnline/RfidReadDataByCfg/RfidEAS Get/Set/RfidDM15Write/ReaderPower*/ReaderSound`).
3. **ИРБИС** — `ManagedClient64`, АРМ `C`, БД `RDR`, поиск `RI=`/`H=`, поле `40` (срок) — §5.
4. **Центр. БД** — REST `/easybookdll/{IsServerAlive,LibraryInfoGet,ReaderInfoGet,ReaderModify,DeviceDataAdd}` **или** SQL (хран. `lic_GetVersionByDeviceGUID`/`rdr_ReaderInfoGet`/`rdr_ReaderModify`, табл. `Owners`/`lib_SNUID`) — §6.
5. **ЕКП** — `EkpMed.dll` (`Authorization→0x9000`, `GetPersID/GetPersData`) с лицензионным гейтом — §7.
6. **Эмуляция ввода** — `PostMessage WM_CHAR/WM_KEYDOWN` в фокусный контрол, режим по заголовку окна — §7.
