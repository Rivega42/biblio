# ТЗ Фаза 1 — ABIS-порт + Device Service + Reader Agent (ядро Biblio)

> **Цель:** реализовать ядро, дающее полноценную книговыдачу/возврат/продление/регистрацию и работу с настольным RFID‑считывателем — **в обоих режимах** (замена JIRBIS и замена ИРБИС) и с **бесшовным подхватом** существующих устройств.
> **Опора:** [BIBLIO_DEVICE_INTEGRATION_DESIGN.md](BIBLIO_DEVICE_INTEGRATION_DESIGN.md), [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md), [CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md), [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md).
> **Ответы на вопросы заказчика — §6 (бесшовный подхват) и §7 (интерфейсы сотрудников).**

## 1. Состав Фазы 1

| # | Компонент | Что делает |
|---|---|---|
| 1 | **ABIS‑порт** `IAbis` + 2 бэкенда (`IrbisBackend`, `BiblioNativeBackend`) | вся логика читателей/выдачи; режим 1 — клиент ИРБИС, режим 2 — нативная БД |
| 2 | **Device Service** (REST/JSON) | БД парка + читатели/устройства + device‑facing совместимость (`/easybookdll/*`) |
| 3 | **Reader Agent** (Windows) | мост к настольному считывателю; протокол :6001 (совместимый) + WebSocket для портала |
| 4 | **Портал/АРМ (мин.)** | книговыдача/возврат/формуляр/регистрация ЕКП/карты на настольном считывателе |

Вне Фазы 1: станции/постаматы/полки (Фаза 3, нужны прошивки), ТСД/ворота/FaceID (Фаза 2).

## 2. ABIS‑порт — контракт `IAbis` (дословно из рекона)

Интерфейс берётся 1:1 из `EasyBookAbis.IDataBase` (проверенный контракт), реализации подменяются по режиму:
```csharp
interface IAbis {
  bool IsConnected { get; }   bool IsDbOk { get; }
  bool Connect();             bool Disconnect();
  UserInformation GetClientName(string clientID, string pin = null);   // поиск читателя по билету/RFID/ЕКП
  List<string>    GetClientChargedDocs(string clientID);               // коды книг на руках
  List<DocInfo>   GetClientChargedDocsFullInfo(string clientID);       // + детали (формуляр)
  DocInfo         GetDocInfo(string docID);                            // экземпляр: статус/срок/владелец/название
  CheckoutResult  Checkout(string clientID, string bookID);           // выдача
  CheckinResult   Checkin(string docID);                              // возврат
  bool            Renew(string itemID, string clientId, DateTime due, out string msg);  // продление
  CheckoutResult  RenewWithResult(string clientID, string bookID, DateTime due);
  bool            SetBookState(string bookID, BookState state);        // смена статуса экземпляра
  bool            Hold(string clientID, string bookID);               // бронь (в ИРБИС‑ветке = заглушка)
  List<string>    GetRequestedDocs(string clientID);                  // заказы
  List<string>    GetRecomendedDocs(string clientID);
  List<ShortReaderInfo> GetReaders(string ln, string fn, string pat, DateTime bd, string passport);
  bool AddReader(string ln, string fn, string pat, DateTime bd, string passport, string ekp, char gender, string phone, string email);
  bool AddReaderByCard(string ln, string fn, string pat, DateTime bd, string passport, string card, char gender, string phone, string email);
  bool AddEkp(string ticket, string guid, string ekp);                // привязать ЕКП (поле 28)
  AddExtraCardResult AddExtraCard(string userID, string newCard);     // доп.карта (поле 24)
}
```
DTO результатов: `UserInformation`, `DocInfo`, `CheckoutResult{Result,Name,DueDate,Message}`, `CheckinResult{Result,ClientID,Message}`, `ShortReaderInfo`, `UserDebt{AllowTake,AllowReturn,…}`, `AddExtraCardResult`, enum `BookState`. Семантика каждого метода (какие поля читать/писать) — [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) §3.

### 2.1 `IrbisBackend` (режим 1)
Реализация поверх клиента `irbis_server` — точно по §3.1 дизайна и полевой модели IRBIS‑map (поиск `RI/GUID/MDPASP/H/IN`, запись RDR 40 / каталог 910^A/999, PFT `@brief/@cenz`, INI `MaskMrg/BIBSIGLA/…`).

### 2.2 `BiblioNativeBackend` (режим 2)
Та же семантика поверх нативной БД (§3). Правила (срок возврата, долги, возраст, перерегистрация, статусы) — как в реконе.

## 3. Нативная БД (режим 2) — схема (минимум Фазы 1)

> Поля — эквиваленты ИРБИС (в скобках — исходный тег), чтобы семантика устройств совпадала.

- **reader** — `id, ticket(30), last_name(10), first_name(11), patronymic(12), birth_date(21/23), gender(23), category(50), email(32), phone(17), status(100), citizenship(101), pin(103), guid(12000), ekp_code(28), reg_date(51), reg_place(51^C), created_by(31^B), search_hash_passport(12814), search_hash_fio(12815)`.
- **reader_card** — `reader_id, code, kind{main(30)|extra(24)|ekp(28)}, serial` (правило: одна карта — один читатель; ошибки `CardInUse/HasAnother/HasSame`).
- **catalog_record** — `id, title, authors, shelf_mark(903), age_cenz(900^Z), genres, cover_url` (или ссылка на каталожный модуль).
- **item** (экземпляр) — `id, catalog_record_id, inv_number, barcode(910^B), status(910^A → enum BookState), location(910^D), shelf_mark(903), issue_count(999)`.
- **loan** (выдача = поле 40) — `id, reader_id, item_id, issued_at(D+1), due_at(E), returned_at(F→дата), return_time(2), renew_count, last_renew_at(L), operator(I), place_out(V), place_in(R), book_name_snapshot(C)`. Открытая выдача = `returned_at IS NULL` (эквивалент `F` начинается с `*`).
- **order** (заказ/бронь, RQST‑эквивалент) — `id, reader_id, number, state, cell_number, safekeeper_id, created_at`.
- **order_item** — `order_id, item_id|barcode, verified, processed`.
- **audit_log** — `id, ts, login, action(ExternalLogTypes), entity, entity_id, comment` (см. §7).

Индексы под поиск: `ticket`, `card.code`, `item.barcode`, `search_hash_*`.

## 4. Device Service — эндпоинты Фазы 1

Контракт и DTO — из [CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md). Транспорт: HTTPS, токен/ключ‑на‑устройство (улучшение против Basic у IDlogic). Фаза 1 реализует:

**Читатели:** `ReadersGet`, `ReaderInfoGet(id, rfidCode)`, `ReaderModify(opID, readerID, name, abisCode, rfidCode, serialNumber, email)`, `ReaderPhotoAdd/Delete`.
**Устройства (настольные):** `DevicesGet`, `DeviceModify`, `DeviceTypesGet`, `DeviceDataGet`, `DesktopDeviceInfoGet`, `DesktopDeviceConfigGet`.
**Доступ/пользователи:** `LoginInfoGet`, `LoginModulesAccessGet`, `UsersInfoGet`, `UserModify`, `RoleTypesGet`, `LoginInfoModify`.
**Библиотеки/справочники:** `LibrariesGet`, `LibraryModify`, `LASColorsGet`, `ServicesGet`, `SettingsGet/Modify`, `ManualGet`.
**Лог/обновление:** `ExternalLogAdd/Get`, `upd_IsUpdateAvailable/Update/UpdateInfoGet`.

**Device‑facing совместимость** (ключ к §6): `/easybookdll/IsServerAlive`, `/LibraryInfoGet{deviceID}`, `/ReaderInfoGet{id,rfidCode,deviceID}`, `/ReaderModify{…,deviceID}`, `/DeviceIsLicenseValid{deviceID}`, `/DeviceDataAdd{deviceID,softOnlineCount,deviceOkCount,deviceErrorCount}`, `/BooksCacheAddUpdate`.

> Все circulation‑эффекты этих эндпоинтов (например регистрация читателя по ЕКП с устройства) Device Service проводит через `IAbis` — то есть пишет в ИРБИС (режим 1) или в нативную БД (режим 2).

## 5. Reader Agent — протокол

Драйвер настольного считывателя (как нативное ядро): `IsReaderOnline / RfidReadDataByCfg / RfidEASGet/Set / RfidDM15Read/Write / ReaderPowerGet/Set / ReaderSound` (можно временно линковать `EasyBook_RFid.dll`). Конфиг — `config.ini`/`cfg3` совместимо ([TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) §8).
Два канала наружу:
1. **Сокет :6001, протокол‑совместимый** (команды `75/77/79/81/97`, поля `UI{nn}/SI{nn}`, разделитель `|`, терминатор `\r`) — [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) §4. Нужен для бесшовной замены: ПО, которое уже говорит на :6001, продолжит работать.
2. **WebSocket JSON** (`localhost`) — для веб‑портала Biblio (браузер не открывает COM): `{cmd:"read"} → {tags:[{sn,dm,eas}]}`, `{cmd:"eas",set:true,uid}`, `{cmd:"status"}`.
3. **SendChar** (опц.) — ввод кода в активное окно (legacy‑совместимость с АРМ ИРБИС).
Метка: ISO 15693/Danish (HF) + EPC (UHF), EAS/AFI.

## 6. Бесшовный подхват устройств — ДА, с нюансами

«Бесшовно» = устройство начинает работать с Biblio **без переустановки/перепрошивки**, переключением конфигурации на наш адрес. Возможность зависит от того, **настраивается ли URL сервера** у устройства, и от того, что мы предъявляем **тот же контракт**.

| Устройство | Бесшовно? | Как |
|---|---|---|
| **Настольный считыватель (EasyBook TagService)** | ✅ да | сменить в `easybook_rfid.cfg3` `ServiceURL` и в `config.ini [IRBIS]` адрес → на Biblio. Наш Device Service отдаёт `/easybookdll/*`, ABIS‑порт принимает выдачу. Либо ставим свой Reader Agent (тот же :6001). |
| **Противокражные ворота** | ✅ да | COM‑устройство, сервера не знает; наш Gate Agent читает их так же (Andea R‑Pan/FEIG). |
| **Камеры Dahua / FaceID** | ✅ да | камеры/NVR не зависят от ПО; наш Vision подключается к тем же IP:37777. |
| **Станции самообслуживания** | ⚠️ если URL конфигурируем | если прошивка станции позволяет указать адрес сервера и говорит на задокументированном `api.svc`‑контракте — переключаем на Biblio (мы его предъявляем 1:1). Если URL зашит — нужен доступ к прошивке. |
| **SafeKeeper / постаматы** | ⚠️/🔴 | аналогично: метаданные — да; **физическое открытие ячейки** — в прошивке (нужен её протокол, [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1). |
| **Умные полки** | ⚠️ | то же — нужен доступ к контроллеру/его конфигу. |

**Что даёт бесшовность:** мы полностью задокументировали device‑facing контракт (`/easybookdll/*`, маршруты `api.svc`, DTO) — поэтому Biblio может предъявить **байт‑в‑байт тот же API**. Тогда «подхват» = смена адреса в конфиге устройства. **Где не бесшовно** — там, где адрес зашит в прошивку станции/локера; это единственный реальный барьер, и он только на станционном железе (не на настольных/воротах/камерах/ТСД).

**Вывод:** настольные считыватели, ворота, камеры, ТСД — **бесшовно** (конфиг). Станции/постаматы/полки — бесшовно **при условии** конфигурируемого URL прошивки; иначе нужен доступ к прошивке (Фаза 3).

## 7. Интерфейсы сотрудников (загрузка книг, аудиты, …) — ДА, покрыты

Все служебные модули этих приложений разобраны в [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md) §2 и воспроизводятся в Biblio (портал/АРМ + Device Service + ABIS‑порт):

| Интерфейс сотрудника | Откуда | Чем покрывается в Biblio |
|---|---|---|
| **Книговыдача/возврат/продление/формуляр** | LAS «Библиотекарь» | Фаза 1: ABIS‑порт (`Checkout/Checkin/Renew/GetClientChargedDocsFullInfo`) + Reader Agent |
| **Регистрация читателя (ЧБ/ЕКП), привязка карт/фото** | LAS «Библиотекарь», ЕКП | Фаза 1: `AddReader/AddReaderByCard/AddEkp/AddExtraCard` + `ReaderPhotoAdd` |
| **Загрузка/добавление книг, правка** | LAS «Все книги», `BookToLibBooksAdd/BookModify` | Device Service (`BooksGet/BookModify/BookToLibBooksAdd`) + дотяжка из каталога ИРБИС (`GetDocInfo`); массовый импорт каталога — каталожный слой/ИРБИС |
| **Хранение фонда: привязка к полкам, инвентаризация, перемещение** | LAS «Хранение фонда» | Фаза 2 (ТСД) + Device Service (`BookKeeping*`); логика и статусы `BookInvStates` |
| **Аудит действий** | LAS `ExternalLog` (enum `ExternalLogTypes`: BookCheckOut/In, OrderAdded, ReaderRFIDAdded, UserEdited, … 31 тип) | таблица `audit_log` (§3) + `ExternalLogAdd/Get`; каждая операция логируется |
| **Отчёты по инвентаризации (найдено/не найдено/перемещено), экспорт XLSX** | LAS «Хранение фонда»→История/Отчёты | Фаза 2/3: `BookKeepingHistoryGet/StatGet` + экспорт |
| **Мониторинг устройств, дашборд, KPI/посетители** | LAS «Мониторинг/Отчёты/KPI» | Фаза 2/3: `info_*`, `*DataGet`, `VisitorsGet` |
| **Пользователи/роли/права на модули** | LAS «Пользователи» | Фаза 1: `UsersInfoGet/UserModify/LoginModulesAccessGet` |
| **Лицензии устройств, конфиг считывателей** | LAS «Лицензии», UniDllConfigurator | Фаза 1/2: `DevicesGet/DeviceModify`, выгрузка cfg |

**Аудиты** — особо: модель аудита уже извлечена полностью — это перечисление `ExternalLogTypes` (31 тип событий: книговыдача/возврат, заказы, привязка карт, действия пользователей и т.д.) + таблица `audit_log`. То есть аудит‑трейл воспроизводится 1:1.

**Итог по вопросу:** да — служебные интерфейсы из этих приложений (книговыдача, регистрация, загрузка/правка книг, хранение фонда/инвентаризация, аудиты, отчёты, пользователи, лицензии) **покрыты картами рекона**; Фаза 1 закрывает книговыдачу/регистрацию/пользователей, Фазы 2–3 — мобильную инвентаризацию, отчёты и станционное железо.

## 8. Критерии приёмки Фазы 1
- Книговыдача/возврат/продление и формуляр работают через настольный считыватель **в обоих режимах** (`IrbisBackend` к реальному ИРБИС; `BiblioNativeBackend` к своей БД) — с идентичным поведением.
- Регистрация читателя (ЧБ и ЕКП) и привязка карт/фото — через ABIS‑порт.
- Существующий **EasyBook TagService подхватывается** сменой `ServiceURL`/`[IRBIS]` (проверка device‑facing совместимости).
- Аудит‑лог фиксирует операции (типы `ExternalLogTypes`).
- Миграция: вычитка `RDR/RQST/каталог` из ИРБИС в нативную БД, расхождений нет (сверка по выборке).

## 9. Зависимости и блокеры
- Станционное железо (постаматы/станции/полки) — Фаза 3, нужен протокол прошивки ([OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1–3).
- Целевой Android‑ТСД и его UHF‑SDK — для Фазы 2.
- Побайтовая раскладка ISO 28560/Danish — для совместимости с уже промаркированным фондом ([OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §8; закрывается декомпиляцией Delphi‑ядра).
