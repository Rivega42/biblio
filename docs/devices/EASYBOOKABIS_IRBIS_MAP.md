# EASYBOOKABIS_IRBIS_MAP — построчный разбор EasyBookAbis.dll: точные поля ИРБИС

> **Источник:** ПОЛНАЯ C#‑декомпиляция `EasyBookAbis.dll` (ilspycmd) — `_scratch_devices/dc_EasyBookAbis/`, ключевой класс `EasyBookAbis.Irbis.Irbis` (2393 стр.). Ссылки — `Irbis.cs:строка`. Это точная модель того, что надстройка читает/пишет в ИРБИС; нужно для репликации в Biblio.
> **Связанные:** [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) (обзор) · [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) · [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md)

## 0. Фасад и подключение

`AbisWorker(AbisConnectType, Config)` (`AbisWorker.cs`) — единый фасад: `IRBIS` → `EasyBookAbis.Irbis.Irbis`, `SIP2` → `EasyBookAbis.SIP2.SIP`. Все методы делегируются в `_db`.

Подключение (`Irbis.cs:122-143`): два клиента `ManagedClient64` к одному серверу, разные АРМ:
- **рабочая строка** `host={DbIP};port={DbPort};user={Login};password={…};Db={Dbs[0]};arm=B;` — **АРМ B (Книговыдача)**, основной клиент `client`.
- **каталожная строка** `…;arm=C;` (`catalogConnectionString`) — **АРМ C (Каталогизатор)**, временный клиент только для чтения настройки `writePlace`.
- `client.Timeout = 5000`. БД: `Rdr="RDR"` (`:126`), `Rqst="RQST"` (`:127`), каталог — `config.IrbisConfig.Dbs` (по умолчанию `{"IBIS"}`, `IrbisConfig.cs`).

Настройки, читаемые из INI ИРБИС (`LoadSettings`/`LoadDebtSettings`/`LoadWritePlace`, `:145-205`):
| Свойство | Источник INI | Назначение |
|---|---|---|
| `place` | `[Request] MaskMrg` | место выдачи → подполе `40^V` и `40^R` |
| `sigla` | `[Main] BIBSIGLA` | сигла → `3054^D` при регистрации |
| `clearHistory` | `[Reader] READERHISTORY == 0` | удалять `40^C` при возврате |
| `useReturnDebtMode` | `[Main] ReaderCOMP == 1` | режим проверки долгов через PFT |
| `returnDebtFormat` | `[Reader] ReturnRightsPft` | `@<pft>` → «возврат разрешён?» |
| `takeDebtFormat` | `[Reader] ReaderRightsPft` | `@<pft>` → «выдача разрешена?» |
| `writePlace` | АРМ C: `[PRIVATE] MZ` | место регистрации → `51^C` |
| `knowledgeSectionsDict` | меню `rzn.mnu` | расшифровка раздела знаний (поле 60) |

`Connect`/`IsDbOk`/`NoOp`/`Reconnect` (`:80-115, 1996-2022`) — сессия с авто‑переподключением (до 3 попыток в каждой операции).

## 1. Используемые базы и префиксы поиска

| Префикс/запрос | База | Что ищет | Где |
|---|---|---|---|
| `RI=<id>` | RDR | читатель по идентификатору/RFID (билет) | везде (`GetRecordFromRdr`) |
| `GUID=<id>` | RDR | читатель по GUID | `AddEkp` |
| `MDPASP=<hash>` | RDR | читатель по хэшу ФИО+ДР / год+паспорт | `GetReaders` |
| `H=<docID>` | RDR | держатели экземпляра (у кого на руках) | `GetDocHolders`, `GetDocDuedate` |
| `IN=<docID>` / `I=<docID>` | каталог (Dbs) | экземпляр по инв.номеру/штрихкоду | `GetRecordFromDBs` |
| `V30:'<id>' and V910^H <> ''` | RQST | заказ читателя | `GetRecordFromRqst` |
| `RI=<id>` | RQST | заказанные документы | `GetRequestedDocs` → поле 903 |
| `V691^F/^C/^V/^A/^O` | каталог | рекомендации (по полю 90 читателя) | `GetRecomendedDocs` |
| `MFN > n AND MFN <= m` | каталог | полная выгрузка постранично (100) | `DoWork` |

Хэш `MDPASP` (`GetMMD5`, `:401-430`): UPPER, замена латинских гомоглифов на кириллицу, MD5 → HEX. Варианты: `MD5(год+MD5(паспорт))`, `MD5(Фамилия+Имя+Отчество+ДР)`.

## 2. Модель полей (сводно)

### Поле 40 (RDR) — строка книговыдачи (одна на экземпляр на руках)
| Подполе | Смысл | Когда пишется |
|---|---|---|
| `F` | статус/дата возврата: `******` пока на руках → `yyyyMMdd` при возврате; фильтр «на руках» = начинается с `*` | Checkout=`******`, Checkin=дата |
| `A` | шифр/полочный индекс (= поле 903 экземпляра) | Checkout |
| `B` | штрихкод (= 910^B) | Checkout |
| `K` | место хранения / читальный зал (= 910^D) | Checkout |
| `V` | место выдачи (`place`=MaskMrg, или `*`) | Checkout |
| `D` | дата выдачи `yyyyMMdd` | Checkout |
| `1` | время выдачи `HHmmss` | Checkout |
| `E` | срок возврата `yyyyMMdd` | Checkout, Renew |
| `G` | имя БД каталога экземпляра | Checkout |
| `H`/`h` | идентификатор экземпляра (инв/штрихкод) | Checkout (ключ) |
| `I` | оператор (логин, `chargePerson`) | Checkout, Checkin |
| `C` | краткое описание книги (`@brief`) | Checkout; удаляется при возврате если `clearHistory` |
| `2` | время возврата `HHmmss` | Checkin |
| `R` | место возврата (`place`) | Checkin |
| `L` | дата продления `yyyyMMdd` | Renew |

### Поле 910 (каталог) — экземпляр
| Подполе | Смысл |
|---|---|
| `A`/`a` | **статус экземпляра** (число `BookState`, см. §4): `0`/`9`=на полке, `1`=выдан, `4`=утерян, `6`=списан, `U`/`C`=группа экземпляров (с `1`=всего, `2`=выдано) |
| `B` | штрихкод/инв.номер экземпляра (ключ поиска) |
| `D` | место хранения / читальный зал |
| `H`/`h` | идентификатор экземпляра |
| `1`,`2` | для групповых (`U`/`C`): всего / выдано |

### Прочие поля экземпляра/книги
`903` — шифр (полочный); `999` — счётчик выдач (инкремент при Checkout); `900^Z` — возрастной ценз; `200^A/^E` — заглавие/подзаголовок; `461^C`+`46^I` — для статей; `700/701/961 ^A/^G/^B` — авторы; `60` + `rzn.mnu` и `606^9/^A/^B` — жанры/тематика; `953^p=2 ^B`, `954^p/^f` — обложка; `920` — рабочий лист (`NJ`=журнал); `933/936` + `V691^F` — связь журнала.

### Поля читателя (RDR)
`10/11/12` — Ф/И/О; `21` — год рождения; `23` — пол; `17` — телефон; `32` — email; `30` — билет/карта; `24` — доп.карта; `28` — код ЕКП; `12000` — GUID; `100` — статус («1»); `101` — гражданство («ЕКП РФ»); `103` — PIN; `51` — регистрация (`^C`=место); `31^A/^B` — дата/оператор создания; `3054` — служебное (`^B`оператор/`^C`время/`^D`сигла/`^E`«Н»); `90^F/^O/^V/^C/^A` — для рекомендаций; `12814/12815` — хэши паспорта/ФИО для поиска; `40` — выдачи. Парсинг — `ManagedClient.Readers.ReaderInfo.Parse` (Fio, Ticket, Birthdate, Category, Email, Age, Rights, Registrations).

## 3. Операции построчно

### Checkout(clientID, bookID) — `Irbis.cs:1457-1619`
1. `GetRecordFromDBs(bookID)` (поиск `IN=`/`I=`); нет → ошибка.
2. `GetDocState` ≠ `Available(0)` и ≠ `AllAvailable(10)` → «не доступен».
3. В 910 берёт поле где `H==bookID`: `chz=910^D`, `b=910^B`; `shif=903`.
4. `GetRecordFromRdr(clientID,"RI")`; нет → «читатель не найден».
5. Если `ageControl`: возраст читателя (по `21`/`Birthdate`) < `GetBookCenz` → отказ.
6. `returnDate = DateConverter.GetReturnDate()` (см. §5).
7. **Запись в RDR:** добавляет поле `40` (`GetChecoutedRecordField`, `:1408-1428`): `F=******`, `A=shif`, `B=b`, `K=chz`, `V=place|*`, `D=yyyyMMdd`, `1=HHmmss`, `E=returnDate`, `G=db`, `H=bookID`, `I=login`, `C=@brief` → `WriteRecord(RDR)`. При ошибке — повторная проверка, что запись всё же легла (`IsRecordExists` по D+1+A+V).
8. **Запись в каталог:** `910^A="1"`, `999 = 999+1` → `WriteRecord(каталог)`.
9. → `CheckoutResult{Result, Name=@brief, DueDate=returnDate}`.

### Checkin(docID) — `Irbis.cs:1649-1816`
1. `GetRecordFromDBs(docID)`; `GetDocState` должен быть `OnHands(1)`.
2. `GetDocHolders(docID)` (RDR `H=`, фильтр поля 40 `F` начинается с `*` и `H==docID`); держателей ровно 1 (0 или >1 → отказ).
3. Проверки держателя (`GetUserByRecord`): долги (`Debt.AllowReturn`), просрочка (`HasOverdueBooks` при `!allowReturnIfDebts`), перерегистрация (`HasRegistration` при `checkRegistration`).
4. `GetCheckinedRecord` (`:1855-1883`): в поле 40 (по `H==docID`, `F` нач. `*`): **`F=yyyyMMdd`** (дата возврата), добавляет **`2=HHmmss`**, удаляет `C` если `clearHistory`, `I=login`, `R=place` → `WriteRecord(RDR)` (с пост‑проверкой `IsCheckined` по F+2).
5. **Каталог:** `910^A="0"` → `WriteRecord` (до 3 попыток).
6. → `CheckinResult{Result, ClientID=билет(30)}`.

### Renew / RenewWithResult — `Irbis.cs:2045-2106, 2268-2348`
- `GetRecordFromRdr(clientId,"RI")`; в поле 40 где `F` нач. `*` и `H==itemID`: если есть `L` и `onlyOneRenew` → отказ; иначе `L=yyyyMMdd` (доб./замена), `E=newDate` → `WriteRecord(RDR)`.

### SetBookState(bookID, state) — `Irbis.cs:2228-2266`
- `AllAvailable(10)`/`BookedForOrder(11)` запрещены для записи в ИРБИС.
- `910` где `H==bookID`: `A = (int)state` → `WriteRecord(каталог)` (до 3 попыток). (LAS использует для перевода экземпляра в `OnShelf(9)` при комплектовании SafeKeeper, и обратно.)

### AddReader / AddReaderByCard — `Irbis.cs:304-399`
Создаёт запись RDR (`Database=RDR`): `12814`=хэш паспорта, `12815`=конкатенация 6 хэшей (для поиска), `100="1"`, `10/11/12`=ФИО, `17`=телефон, `32`=email, `21`=год, `23`=пол, `51`=`yyyyMMdd`+`^C=writePlace`, `31^A`=дата `^B`=login, `3054="ДА" ^B`=login `^C`=время `^D`=sigla `^E="Н"`. Различие: **AddReader** добавляет `101="ЕКП РФ"` и `28=ekp`; **AddReaderByCard** добавляет `30=card`. → `WriteRecord`.

### AddEkp(ticket, guid, ekp) — `Irbis.cs:263-302`
Находит RDR по `RI=ticket` или `GUID=guid`; если поля `28` нет — добавляет, если есть но пустое — заполняет, если занято — отказ (одна ЕКП). → `WriteRecord`.

### AddExtraCard(userID, newCard) — `Irbis.cs:2350-2387`
Находит RDR по `RI=userID`; если поле `24` занято → `HasAnotherCardError`; если `newCard` уже у кого‑то (`RI=newCard`) → `CardInUseError`/`HasTheSameCardError`; иначе `24=newCard` → `WriteRecord`. Enum результата: `Success/CardInUseError/HasAnotherCardError/HasTheSameCardError/CommonError`.

### GetReaders(ФИО, ДР, паспорт) — `Irbis.cs:207-261`
Поиск RDR по `MDPASP=` (сначала хэш ФИО+ДР, затем год+паспорт) → `ShortReaderInfo{BirthYear, Guid(12000), Ekp(28), FIO, Rfid(билет)}`.

### GetClientName / GetUserByRecord — `Irbis.cs:610-677, 549-608`
RDR по `RI=`. Читает: ФИО/билет/категория/email/возраст/права (`ReaderInfo`), `103`(PIN, опц.), `12000`(GUID), `28`(ЕКП); считает просрочку (поле 40 `^E` < сегодня), регистрацию (поле 51 `^C` год≥текущий и место), долги (`GetUserDebts`). → `UserInformation`.

### GetClientChargedDocs / …FullInfo — `Irbis.cs:432-547`
RDR по `RI=`; поле 40 где есть `A`, `F` нач. `*` (и опц. `V` ∈ `bookOnHandsPlaces`). Short → список `H`. Full → `DocInfo` по подполям 40: `G`(db), `H`(id), `C`(имя), `E`(срок), `A`(шифр), `B`(инв), `K`(место) + дотягивает книгу из каталога (`GetRecordFromDB(H, db=G)`).

### GetDocInfo / GetDocState — `Irbis.cs:1233-1396`
`GetRecordFromDBs(docID)`; `903`=шифр; 910 по `H==docID` (или `B==docID`): `D`(чз), `B`(инв); `@brief`=title; авторы/жанры/обложка/ценз; `GetDocState` по 910^A (см. §4); если на руках — `GetDocHolders` → владелец `30` и срок (`GetDocDuedate`). → `DocInfo`.

### GetDocHolders — `Irbis.cs:1818-1853`
RDR по `H=docID`; держатели = записи где поле 40 `F` нач. `*` и `H==docID`.

### GetUserDebts — `Irbis.cs:2157-2181`
Через PFT: `returnDebtFormat`(=@ReturnRightsPft) → `AllowReturn = (результат=="1")`; `takeDebtFormat`(=@ReaderRightsPft) → `AllowTake`. Иначе — по просрочке (`IsUserHaveOverdueBooks`: поле 40 `^E` < сегодня).

### GetBookCenz — `Irbis.cs:2202-2226`
`@cenz` PFT экземпляра → число; иначе `900^Z` (убрать `+`); иначе 18.

### GetRequestedDocs / GetRecomendedDocs — `Irbis.cs:1897-1960`
- Requested: RQST по `RI=clientID` → поле `903` каждого заказа.
- Recomended: поле `90` читателя (`^F/^O/^V/^C/^A`) → запрос каталога `V691^F/^C/^V/^A/^O` → поле `903`.

### Hold(docID, clientID) — `Irbis.cs:2389-2391`
**Заглушка — всегда `false`** (бронирование через ИРБИС в этом классе не реализовано; заказы SafeKeeper идут через центральный сервис, см. [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md)).

## 4. Перечисление статусов `BookState` → значение `910^A`

| BookState | Значение (=910^A) | Описание |
|---|---|---|
| Unknown | -1 | неизвестно |
| Available | **0** | доступен для выдачи |
| OnHands | **1** | выдан читателю |
| Lost | **4** | утерян |
| Discarded | **6** | списан |
| Processing | **8** | в обработке |
| OnShelf | **9** | на бронеполке |
| AllAvailable | 10 | экземпляр из группы (не пишется) |
| BookedForOrder | 11 | забронирован (не пишется) |
| InTransit | 12 | перемещается |
| EasError | 1000 | ошибка противокражной подписи (внутр.) |

> `GetDocState` дополнительно трактует `910^A` буквенные: `U`/`C` = группа экземпляров (подполя `1`=всего, `2`=выдано → OnHands если выдано≥всего, иначе AllAvailable); `K` = на руках/неизвестно.

## 5. Расчёт срока возврата (`DateConverter.GetReturnDate`, SIP2/DateConverter.cs)
- Если заданы `Sip2Config.DateReturn1/2` (фиксированные даты семестров) — академический календарь (осень→весна и т.п.).
- Иначе если `UseUniversityDateFormat` — конец февраля след. года / 10 июля.
- Иначе — **`DateTime.Now.AddDays(ReturnDaysCount)`** (обычный режим; код-дефолт `ReturnDaysCount=14` в `Config.cs:23`, на стенде переопределён в **30** через `SIP2settings.xml`).

## 6. Что Biblio должна поддержать на стороне ИРБИС‑совместимости

Чтобы наша система заменила ИРБИС для этой надстройки **без её переустановки**, наш серверный протокол (ManagedClient‑совместимый, `:6666`) должен:
- **Поиск:** `RI=`, `GUID=`, `MDPASP=`, `H=` (по RDR); `IN=`/`I=` (каталог); прямые `V30:'…' and V910^H<>''`, `V691^F:'…' …`; `MFN > n AND MFN <= m`.
- **Чтение/запись записей** RDR и каталога c подполями из §2 (особенно поле `40` и `910`).
- **Форматирование** PFT: `@brief`, `@cenz`, `ReturnRightsPft`/`ReaderRightsPft`.
- **INI/меню:** `[Request]MaskMrg`, `[Main]BIBSIGLA/ReaderCOMP`, `[Reader]ReturnRightsPft/ReaderRightsPft/READERHISTORY`, `[PRIVATE]MZ` (АРМ C), `rzn.mnu`.
- **Семантику операций** §3 (Checkout: 40 + 910^A=1 + 999++; Checkin: 40^F/^2/^R + 910^A=0; Renew: 40^L/^E; регистрация: полный набор полей RDR; ЕКП: поле 28; доп.карта: поле 24).
- Маска дат **`yyyyMMdd`**; время `HHmmss`.

> Альтернатива (если развёртывание ставит `UseSIP2=True`): реализовать SIP2‑сервер — см. [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) §4. Класс `EasyBookAbis.SIP2.SIP` — клиент SIP2 с теми же результатами (`CheckoutResult`/`CheckinResult`).
