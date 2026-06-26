# DEVICE_IRBIS_INTEGRATION — связки надстройки с ИРБИС64 и что реплицировать в Biblio

> **Источник:** статический разбор `EasyBookAbis.dll`/`LibraryAdminServer.exe` (дампы `_recon/_scratch_devices/str_*.txt`), конфиги `SIP2settings.xml`/`config.ini`/`DBSettings.xml`, `manual.txt`. Ссылки `str_<файл>`. Гипотезы помечены **(инференс)**.
> **Связанные:** [DEVICE_INVENTORY.md](DEVICE_INVENTORY.md) · [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
> **⚠ Секреты:** боевые строки подключения к ИРБИС/сервису/камере — в конфигах на стенде; здесь только структура. Значения паролей **не коммитятся** (`секрет → .env`).

## 0. Две точки сопряжения

Надстройка цепляется к экосистеме библиотеки в двух местах:
1. **АБИС ИРБИС64** — для данных читателей и книговыдачи (модуль «Библиотекарь», SafeKeeper‑заказы, регистрация ЕКП). Два режима — **прямой ИРБИС (ManagedClient.4 TCP)** или **SIP2** (флаг `UseSIP2`).
2. **Центральный сервис IDlogic** (`api.svc`) — для парка устройств (станции/ворота/полки/СКУД/камеры). Это НЕ ИРБИС, отдельный продукт IDlogic; разобран в [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §7.

```
LibraryAdminServer.exe ─┬─ EasyBookAbis.dll ─┬─ ManagedClient.4 ──TCP:6666──▶ irbis_server (RDR/RQST/KNIGA)
   (AbisWorker)         │   (AbisConnectType) └─ SIP2 client ──TCP──▶ SIP2-сервер АБИС  (если UseSIP2=True)
                        └─ WebService ───────────REST/JSON──▶ api.svc :8005 (парк устройств)
```

Выбор ветки — единый флаг `UseSIP2` (в `SIP2settings.xml` = `False` → этот стенд работает **напрямую с ИРБИС**). Обе ветки за единым фасадом `AbisWorker` с общими результатами (`CheckoutResult`, `CheckinResult`, `IsCheckOutOk`, `IsRenewOk`, `IsLoginOk`).

---

## 1. Прямое подключение к ИРБИС (ManagedClient.4)

`EasyBookAbis.dll` встраивает клиент **ManagedClient.4** (ManagedIrbis, А.Нежданов; PDB `G:\ManagedClient.4-master\…`, ресурс `EasyBookAbis.Resources.ManagedClient.4.dll`). Строка подключения собирается в рантайме (`str_EasyBookAbis`):
```
host={0};port={1};user={2};password={3};arm=B;    ← АРМ «B» (Книговыдача) — выдача/возврат/заказы
host={0};port={1};user={2};password={3};arm=C;    ← АРМ «C» (Каталогизатор) — чтение/запись записей
```
Разбор/сборка: `ParseConnectionString`, `catalogConnectionString`, `GetFullConnectionStringWithoutPooling`, `DefaultConnectionString`. Альтернатива (есть, но не используется на стенде) — **прямой доступ к файлам БД без сервера**: `IrbisDirectReader32/64` (читает `.MST/.XRF/.IFP`, namespace `ManagedClient.Direct`). Боевой режим — **TCP `TcpClient`** к `irbis_server`.

### Конфиг подключения (`SIP2settings.xml` — несмотря на имя!)
| Поле | Назначение |
|---|---|
| `DbIP` / `DbPort` | хост/порт `irbis_server` (порт `6666`). **⚠ → .env** |
| `IsNeedAuth` | слать ли логин/пароль |
| `DbLogin` / `DbPassword` | учётка ИРБИС. **⚠ → .env** |
| `IrbisDB` = `KNIGA%SERV21%` | имя БД каталога `KNIGA` + профиль/сервер в `%…%` (`SERV21` ↔ логин‑префикс `21_`). **(инференс)** — разбивается по `%` при загрузке, имя БД идёт в `PushDatabase`/`FormatRecordDatabase`. БД читателей — отдельно `RDR`, заказов — `RQST` |
| `ReturnDaysCount=30` | срок выдачи (дней) для расчёта даты возврата |
| `AllowTakeIfDebts` / `AllowReturnIfDebts` | разрешать выдачу/возврат при задолженности |
| `NeedCheckDebts` | проверять ли долги (`GetUserDebts`) |
| `OnlyOneRenew` | ограничить одним продлением |
| `AgeControl` | возрастная цензура (`@cenz`/`GetBookCenz`) |
| `InstitutionID` / `LocationCode` | SIP2 AO/локация (только в SIP2‑режиме) |
| `UseSIP2` | прямой ИРБИС (False) vs SIP2 (True) |

`config.ini [IRBIS]` — резервные `Ip=127.0.0.1/Port=6666/Login/Password` (для агента TagService).

---

## 2. Читатели (БД RDR)

Записи читателей — в БД **RDR**. Методы: `GetRecordFromRdr`, `GetRecordsFromRdr`, `GetUserByRecord`, `AddReader`, `AddReaderByCard`, `IsRecordExists`.

**Поиск по билету** — поле **30**:
```
V30:'{билет}' and V910^H <> ''        (str_EasyBookAbis:18935)
```
**Поля RDR, которые трогает надстройка** (подтверждены свойствами + конвенции ИРБИС, частично **(инференс)**):
| Поле | Содержимое | Доказательство |
|---|---|---|
| **30** | билет / читательский | литерал `V30:'…'` |
| **10/11** | ФИО (фамилия/имя/отчество) | `lastName/firstName/patronymic/GetClientName` |
| **21/23** | дата рождения | `birthDate/BirthYear/GetAgeByDateTime` (для `AgeControl`) |
| **50** | категория | `UserCategory/get_Category` |
| **40** | выданные экземпляры (строки выдачи) | `GetClientChargedDocs/OnHands/Charged` |
| (контакты) | email/телефон | `EMail/phone` |
| (RFID/ЕКП) | привязанная карта | спец‑подполе IDlogic — **тег не литерал, UNKNOWN** |

**Привязка RFID‑карты / ЕКП (Единая Карта Петербуржца):** карта несёт тройку `rfidCode` (UID), `abisCode` (= билет, поле 30), `serialNumber`. Методы `AddReaderByCard`, `AddEkp`, `AddExtraCard`; чтение ЕКП — внешний `EkpMed.dll`/`EKPMedWorker2` при `UseEKP=true`. Защита: `CardInUseError`/`HasAnotherCardError`/`HasTheSameCardError` (одна карта — один читатель). Где именно в RDR хранится код карты — собирается в рантайме, **тег подполя не виден в строках** (реплицировать как выделенное подполе + зеркало в локальной БД IDlogic). Регистрация по ЕКП пишет в ИРБИС паспортные поля («Кем выдан паспорт», «Адрес прописки», `manual.txt:515`).

> **FaceDetect** в `EasyBookAbis` отсутствует — там читатель ищется только по билету или RFID/ЕКП‑карте. Поиск «по лицу» реализован в `LibraryAdminServer.exe` через Dahua NetSDK (см. [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §6), он лишь резолвит читателя в билет.

---

## 3. Книговыдача / возврат / продление

Методы: `Checkout`/`CheckoutResult`, `Checkin`/`CheckinResult`, `RenewWithResult`, `IsCheckined`/`GetCheckinedRecord`, `SetBookState`/`GetDocState`, `GetDocInfo`/`GetDocDuedate`/`GetDocHolders`, `ReadRecord(s)`/`WriteRecord`/`GetMaxMfn`.

**Экземпляр = поле 910.** Подполя: `^A` инв.номер, `^B` штрихкод, **`^H` статус** (фильтр `V910^H <> ''`). Валидаторы `Require910`/`Check10`. Поля книги: `Cipher/Shifr/Inv/Owner`.

**Строка операции/держателя = поле 691** (транзакция выдачи):
```
V691^F:'{0}' and V691^C:'{1}' and V691^V:'{2}' and V691^A:'{3}' and V691^O:'{4}'   (str_EasyBookAbis:18951)
```
`^A`=инв.номер; `^F/^C/^V/^O` — фонд/сигла/операция/владелец (**(инференс)**, точная семантика частично UNKNOWN).

**«Доступна к выдаче»:** `AllAvailable/AllowCheckOut/IsCheckOutOk` = статус 910^H + `GetDocHolders` + политика долгов/возраста. Запись нового статуса: `SetBookState '{0}' TO {1}` (ошибка `State {0} is unavailable for Irbis`). Перечень статусов: `OnShelf`, `OnHands`, `Charged`, `InTransit`, `OnOrder`, `BookedForOrder`, `WaitingOnHoldShelf`, `Discarded`, `InProcess` и др.

**Даты:** срок = `ReturnDaysCount`(=30); расчёт `GetReturnDate/NewReturnDate/AddDays`; маска ИРБИС **`yyyyMMdd`**, показ `dd.MM.yyyy`; `GetDateFromIrbisFormat`; опц. `UseUniversityDateFormat`.

**Долги:** `GetUserDebts/IsUserHaveOverdueBooks/HasOverdueBooks`, меню `dolg.mnu`, гейтинг `NeedCheckDebts/AllowTakeIfDebts/AllowReturnIfDebts`.

**Поток:** `ReadRecord(RDR по V30)` → `ReadRecord(книга по 910/691)` → правка поля 40 (RDR) + 910/691 (книга) → `WriteRecord` обоих. Вспом.: `@brief`, `@cenz`, `rzn.mnu`, `MaskMrg`.

Модуль «Библиотекарь» (`manual.txt:426`) явно «заменяет собой АРМ Книговыдача» и соединяется с АБИС «напрямую или по SIP2».

---

## 4. SIP2 (когда `UseSIP2=True`)

`EasyBookAbis.SIP2` / `RfidStation.SIP2` — **SIP2‑клиент self‑check** к серверу АБИС. В строках видны номера сообщений и коды полей (`str_EasyBookAbis:18890‑18909`):

| Литерал/метод | SIP2 | Назначение |
|---|---|---|
| `9300CN` | **93→94** Login | вход (`CN`=login id) |
| `9901002.00AY` | **99→98** SC/ACS Status | статус (`2.00`, `AY` seq) |
| `63015…` + маски `Y…/…Y…` | **63→64** Patron Information | инфо о читателе (10‑симв. summary) |
| `Checkout`/`Checkin` | **11→12** / **09→10** | выдача/возврат (**(инференс)** номера) |
| `RenewWithResult`/`AllowPatronRenewal` | **29→30** | продление |
| `AllowPatronStatusUpdate` | **23→24** | статус читателя |

**Поля:** `AO`(institution), `AP`(location), `AA`(patron), `AB`(item), `AC`(terminal pwd), `AD`(patron pwd), `AJ`(title), `AY`(seq), `BV`(fee). Сборка: `|AD|AB`, `|AC|AY`, `|AC|BIN|AY`, `AP|AO`. Контрольная сумма/seq: `CheckSumAdd`/`IsCheckSumCorrect`/`IgnoreCheckSum`. Лог `sip_log.txt` (`CONNECT_ERROR/Request/Response/ERROR`), даты `yyyyMMdd`/`HHmmss`.

**UI‑поля SIP2** (LAS): `tbSIP2IPAddress`, `tbSIP2Port`, `tbSIP2Login`, `pbSIP2Pass`, `tbSIP2InstitutionID`(→AO), `tbSIP2LocationID`(→AP), `tbSIP2ReturnDaysCount` → ложатся в `SIP2settings.xml`.

> Поскольку надстройка — SIP2‑**клиент**, чтобы наша Biblio заменила АБИС в SIP2‑развёртывании, нам нужен **SIP2‑сервер** с сообщениями 93/99/63/11/09/23/29 и полями AO/AP/AA/AB/AC/AD/AJ/AY + checksum/seq. На стенде `UseSIP2=False`, поэтому достаточно эмуляции серверного протокола ИРБИС.

---

## 5. Заказы/бронирование (БД RQST)

SafeKeeper‑заказы пишутся в БД **RQST** (заказы/требования ИРБИС):
- `CreateRequest`, `GetRecordFromRqst`, `GetRequestedDocs`, `GetRequestSequenceNumber`/`LastSeqNumber` (выделение порядкового номера RQST).
- Статусы `OnOrder`/`BookedForOrder`/`Holds`/`WaitingOnHoldShelf`, `IsHoldOk`, `GetDocHolders`.
- UI: `btnOrderCheckout_Click` — превращение брони SafeKeeper в реальную выдачу (`OrderStateToCheckoutButtonConverter`).
- Встроенный ManagedClient INI знает роли БД `REQUEST`/`RDRDBN`(READER) — стандартная триада ИРБИС: каталог (KNIGA) / читатели (RDR) / заказы (RQST).

То есть бронирование = запись RQST (через `CreateRequest`, нумерация `GetRequestSequenceNumber`); при выдаче — `Checkout`, статус экземпляра `OnOrder/BookedForOrder` → `OnHands`. Точная раскладка полей RQST (30=№ заказа, 40=билет, 11=шифр, 910‑связь) — **(инференс)** по конвенции, частично UNKNOWN.

---

## 6. Чек‑лист: что Biblio должна воспроизвести для бесшовной замены

### 6.1 Серверный протокол ИРБИС (эмулировать поднабор ManagedClient.4 на `:6666`)
- [ ] **Аутентификация/сессия:** регистрация клиента с `arm=B` и `arm=C`, разрегистрация, keep‑alive.
- [ ] **ReadRecord / ReadRecords** (RDR, KNIGA, RQST по MFN).
- [ ] **Search** (язык запросов ИРБИС): `V30:'<билет>' and V910^H <> ''`; `V691^F:'..' and V691^C:'..' and V691^V:'..' and V691^A:'..' and V691^O:'..'`; `MFN > {n} AND MFN <= {m}`.
- [ ] **WriteRecord** (RDR поле 40; KNIGA поле 910^H статус, поле 691 строки выдачи).
- [ ] **FormatRecord/FormatRecords** (PFT: `@brief`, `@cenz`, `ReaderRightsPft`, `ReturnRightsPft`).
- [ ] **GetMaxMfn**, переключение БД `PushDatabase/PopDatabase/FormatRecordDatabase` (KNIGA↔RDR↔RQST).
- [ ] Чтение INI/меню: `rzn.mnu`, `dolg.mnu`, `RDRPFTMNU`, сигла/места.
- [ ] **Формат записи на проводе:** строки `MFN#status` + поля/подполя с ``; маска дат `yyyyMMdd`.

### 6.2 БД и поля (наш слой данных должен их отдавать/принимать)
- [ ] **RDR:** 30 (билет), 10/11 (ФИО), 21/23 (д.р.), 50 (категория), 40 (выданные), спец‑подполе RFID/ЕКП‑карты (реплицировать), email/телефон.
- [ ] **KNIGA/каталог:** 910 (`^A` инв, `^B` штрихкод, `^H` статус), 691 (строки выдачи `^F^C^V^A^O`), шифр, `@cenz` (возраст).
- [ ] **RQST:** запись заказа, нумерация, статусы OnOrder/BookedForOrder/Hold.

### 6.3 Движок политики книговыдачи (из `SIP2settings.xml`)
- [ ] Срок `ReturnDaysCount`; правила долгов (`NeedCheckDebts`/`AllowTakeIfDebts`/`AllowReturnIfDebts`); `OnlyOneRenew`; `AgeControl`; проверки регистрации/места.

### 6.4 SIP2 (только если развёртывание ставит `UseSIP2=True`)
- [ ] **SIP2‑сервер**: 93/94 login, 99/98 status, 63/64 patron, 23/24 patron status, 11/12 checkout, 09/10 checkin, 29/30 renew; поля AO/AP/AA/AB/AC/AD/AJ/AY + checksum + seq.

### 6.5 Хранилище RFID/ЕКП‑привязок
- [ ] Семантика `AddReaderByCard`/`AddEkp`/`AddExtraCard`: `rfidCode ↔ билет(abisCode) ↔ serialNumber`, «одна карта — один читатель» (`CardInUseError`/`HasAnotherCardError`), интеграция `EkpMed.dll` при ЕКП.

### 6.6 Центральный сервис устройств (`api.svc`) — если заменяем и его
- [ ] REST/JSON эндпоинт с операциями из [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §7.1 (Stations/SafeKeeper/SmartShelf/Gates/ACS/Devices/Readers/Users/KPI/Update), Basic‑auth.

---

## 7. Открытые места интеграции
- Точный тег подполя RDR для RFID/ЕКП‑карты — собирается в рантайме, не литерал → нужно подтвердить на боевой RDR или декомпиляцией.
- Семантика подполей 691 (`^F^C^V^A^O`) и раскладка RQST — **(инференс)** по конвенции.
- Номера SIP2 checkout/checkin/renew (11/09/29) — по именам методов; литералом видны только 93/99/63.
- Разбор `KNIGA%SERV21%` (`%…%`) — **(инференс)**: имя БД + профиль/сервер.
Подробнее — [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
