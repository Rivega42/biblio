# SPEC · Внешние библиотечные протоколы (Z39.50 / SRU·SRW / OAI-PMH / SIP2 / NCIP·ILS-DI)

> Закрытие гос-рыночного пробела **B2** ([DESIGN_COVERAGE §B](../../DESIGN_COVERAGE.md), эпик **#188**) — детальные контракты межсистемных протоколов, по которым нас **ищут извне** (Z39.50/SRU-сервер, OAI-PMH-провайдер) и по которым **мы заимствуем/обмениваемся** (Z39.50/SRU-клиент к СКБР/WorldCat, NCIP/ILS-DI в консорциуме). В ИРБИС эти протоколы существуют точечно и однонаправленно: Z39.50 — **только клиентский** импорт через `yaz.dll` с серверной частью **выключенной** (`Z39_50_SERVER=0`), без SRU/OAI/SIP2/NCIP как сервисов. Гос-рынок РФ (вузы, областные/научные библиотеки, НЭБ-агрегация, ЭБС, консорциумы, RFID-самообслуживание) требует, чтобы наша платформа была **полноценным узлом отраслевой экосистемы** — и сервером, и клиентом, и провайдером, и мостом к самообслуживанию.
>
> **Грунтовано на recon (читать как ground truth):**
> [CAPABILITY_MAP §11](../../../recon/deep/CAPABILITY_MAP.md) (Z39.50 клиентский импорт `yaz.dll`; серверный `Z39_50_SERVER=0` выкл.; OAI/ЛИБНЕТ импорт; форматы обмена ISO 2709 / RUSMARC·UNIMARC·USMARC·MARC21) ·
> [ARM_CATALOGER `[Main]`](../../../recon/deep/reference/arms/ARM_CATALOGER.md) (параметры Z-импорта `ZIMPORTSEARCHPAGE`/`ZIMPORTFORMAT`; ЛИБНЕТ `LIBNETIP`/`LIBNETSEARCHPAGE`/`LIBNETFORMAT`/`LIBNETFST`/`LIBNETGBL`; импортные FST/GBL `RUSMARCFST`/`UNIMARCFST`/`USMARCFST`+`*GBL`) ·
> [PROTOCOL_REFERENCE §5](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md) (грамматика поиска: префиксы `A=`/`K=`/`T=`/`V=`/`I=`…, правое усечение `$`, квалификация `/(метки)`, операторы `+ * ^ (G) (F) .`) ·
> [DB_IBIS](../../../recon/deep/reference/databases/DB_IBIS.md) (109 префиксов IBIS, инвертирование `.FST`) · [DB_MBA §11](../../../recon/deep/reference/databases/DB_MBA.md) (сиглы фондодержателей `sigl.mnu`, межбибл. цикл — субстрат NCIP) ·
> [FIELD_DICTIONARY](../../../recon/deep/reference/format/FIELD_DICTIONARY.md) (метки полей → use-атрибуты BIB-1).
>
> **Опорные спеки:** родитель — **I2** ([SPEC_I2 §C #123](../SPEC_I2_catalog_search.md): «Z39.50/SRU клиент И сервер… OAI-PMH-провайдер… SIP2… +NCIP/ILS-DI»). Поисковый бэкенд — **наш PostgreSQL FTS** ([SPEC_I2 §A #122](../SPEC_I2_catalog_search.md): `to_tsvector('russian')`+`pg_trgm`, бустинг, фасеты; **не** нативный ИРБИС-словарь). Заимствование в РЛ каталогизатора — [SPEC_ws1 §4–5](../SPEC_ws1_cataloger.md) (поиск во внешнем источнике → импорт в РЛ → ФЛК → правка → сохранение; импорт/экспорт MARC). Рендер записей в обменные форматы (MARCXML/ISO 2709/Dublin Core/каталожная карточка) — **переиспользуется из A1** [SPEC_engine_pft.md](../engines/SPEC_engine_pft.md) (форматы `rmarcw`/`umarcw`/`usmrcw`, Dublin Core уже в `PFTW.MNU`), **не дублируется**. Импорт MARC→запись и ФЛК импорта — A2 [SPEC_engine_flk.md](../engines/SPEC_engine_flk.md) (`!998` контроль импорта). Авторитеты для маппинга персоналий — A4 [SPEC_service_authority.md](../engines/SPEC_service_authority.md). Контракт REST/конверт/двойной гейт `грант×энтайтлмент` — A7 [SPEC_api_contracts.md](../engines/SPEC_api_contracts.md), I1 [#101/#116](../SPEC_I1_foundation.md). SIP2 — мост к движку книговыдачи [SPEC_ws3_circulation.md](../SPEC_ws3_circulation.md) / I3 и к edge-офлайн [SPEC_I4_edge_offline.md](../SPEC_I4_edge_offline.md). NCIP/ILS-DI — слой консорциумов **CN #181** ([SPEC_I4 §D](../SPEC_I4_edge_offline.md): три зоны, union-каталог, resource sharing). Журнал доступа/ПДн (SIP2 несёт ПДн читателя) — I6 (B4 152-ФЗ/ФСТЭК). Гос-выгрузки НЭБ/СМЭВ/СКБР (B3) — **смежная спека**, здесь только транспорт/общая часть (OAI-провайдер как канал для агрегаторов).
>
> Платформа: **PostgreSQL + Python-бэкенд**. Каждый протокол — **отдельный адаптер** (микросервис/модуль) поверх ядра I1; см. §6.

**DoD-гейт (как в I1/I2/A1/A6):** код + автотест + **контракт-тест против эталонного внешнего клиента** (реальные YAZ/zoomsh, Apache Solr SRU, OAI-PMH-валидатор, SIP2-эмулятор) + **тест изоляции тенанта** (per-tenant БД/наборы/auth; запрос к тенанту A не отдаёт записи тенанта B) + наблюдаемость (trace/`tenant_id`, метрики по протоколу: запросы/латентность/ошибки/размер ответа) + a11y (н/п — машинные протоколы; для explain/diagnostics — корректные коды) + **152-ФЗ-гейт** (SIP2/NCIP несут ПДн → минимизация, журнал доступа, шифрование транспорта) + обновление доков. Размеры S/M/L.

---

## 0. Принципы и границы

- **Протокол — адаптер, не ядро.** Каждый протокол реализует трансляцию «внешний запрос ↔ наш канонический поиск/запись», но **не содержит бизнес-логики**. Поиск всегда уходит в **наш PostgreSQL-FTS** ([SPEC_I2 #122](../SPEC_I2_catalog_search.md)) через единый внутренний `SearchService`; выдача записи — через `RecordService` (ядро I1) + рендер **A1** в нужную схему. Адаптер знает свой проводной формат (ASN.1/BER для Z39.50, XML/SRU, текст SIP2, XML NCIP) и маппинг своей системы атрибутов на наш канон — больше ничего.
- **Канонический внутренний поиск — один.** Все протоколы (Z39.50 Type-1 RPN, SRU CQL, OAI `set`+`from/until`) транслируются в **общий внутренний поисковый AST** (§7.1), который исполняет I2-бэкенд. Это значит: BIB-1 use-атрибут `4` (title), CQL `dc.title`, наш префикс `T=` ([PROTOCOL_REFERENCE §5](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)) и индекс FTS `title` — **четыре имени одной точки доступа**. Маппинг ведётся в одной per-tenant таблице соответствий (§7.2), а не в каждом адаптере.
- **Сервер И клиент — раздельные роли.** «Нас ищут» (Z39.50/SRU-**сервер**, OAI-**провайдер**, SIP2-**сервер**, NCIP-**responder**) и «мы ищем/обмениваемся» (Z39.50/SRU-**клиент**, NCIP-**initiator**) — это разные направления, разные адаптеры, но **общий слой маппинга и общий канон**. ИРБИС имел только клиента Z39.50; мы добавляем серверные роли (паритет с Alma/Koha/OCLC-узлами).
- **Tenant-scoping — инвариант.** Внешний узел адресует **конкретную базу конкретного тенанта** (§6.4): Z39.50 database-name → `(tenant, db)`; SRU path → `(tenant, db)`; OAI endpoint → per-tenant; SIP2/NCIP — institution-id → тенант. Запрос без валидной привязки к тенанту не выполняется. Negative-тест изоляции — DoD-гейт.
- **Форматы — из A1, не переписываем.** Z39.50 Present / SRU recordSchema / OAI metadataPrefix отдают запись в MARCXML / ISO 2709 / RUSMARC / UNIMARC / MARC21 / Dublin Core / MODS — всё это **рендерит A1** ([SPEC_engine_pft.md](../engines/SPEC_engine_pft.md), форматы `rmarcw`/`umarcw`/`usmrcw` + Dublin Core из `PFTW.MNU`, [CAPABILITY_MAP §6](../../../recon/deep/CAPABILITY_MAP.md)). Адаптер запрашивает у A1 `format(record, schema)` и заворачивает результат в свой конверт. Обратный путь (импорт MARC→запись) — A2/ws1.
- **Версии — явные.** Каждый протокол многоверсионный (Z39.50 v3; SRU 1.1/1.2/2.0 + SRW; OAI-PMH 2.0; SIP2 2.00; NCIP v1/v2, ILS-DI). Версия согласуется в init/explain; адаптер декларирует поддерживаемые версии в `explain`/`Identify`/`SC Status`. Нельзя «молча» сменить семантику.
- **Безопасность транспорта.** Серверные протоколы, несущие ПДн (SIP2 — статус читателя; NCIP — LookupUser) — **только по TLS** (SIP2 over TLS / stunnel-паритет; NCIP over HTTPS), с per-tenant auth и журналом доступа (152-ФЗ, I6 B4). Z39.50/SRU/OAI по библиографическим данным — TLS рекомендуется, auth настраиваемо (анонимный read допустим для публичного OAI).
- **Границы.** Эта спека — **транспорт и контракт протоколов**. Она **не** определяет: схему MARC-полей (A1/ws1), бизнес-цикл книговыдачи (ws3/I3), модель консорциума/union-каталога (CN #181, [SPEC_I4 §D](../SPEC_I4_edge_offline.md)), форматы гос-выгрузок НЭБ/СМЭВ (B3 — смежная спека; здесь только OAI как канал доставки). Маппинг конкретных полей RUSMARC↔наш канон ведётся в A1/ws1, здесь — как он подключается к протоколу.

---

## 1. Z39.50 (ANSI/NISO Z39.50-2003, ISO 23950; BIB-1)

> Самый «тяжёлый» протокол: бинарный ASN.1/BER поверх TCP, сессионный (init→search→present→…). Две роли. Эталон клиента — YAZ/`zoomsh` (наследие `yaz.dll` ИРБИС), эталон сервера — наш target проверяется тем же YAZ-клиентом и WorldCat/СКБР-сканером.

### 1.1 Z39.50-сервер (нас ищут извне)

**Зачем:** областные/научные библиотеки, агрегаторы, СКБР и зарубежные узлы должны находить наши записи стандартным клиентом. ИРБИС это **не отдавал** (`Z39_50_SERVER=0`). Это паритетный must-have для гос-узла.

**Поддерживаемые сервисы (Z39.50 v3 services):**

| Сервис | Назначение | Реализация |
|---|---|---|
| **Init** | согласование версии/опций/preferredMessageSize/maximumRecordSize; auth (open / idPass / anonymous) | привязка сессии к `(tenant, db, grants)`; объявляем options: search, present, scan, namedResultSets |
| **Search** | приём **Type-1 RPN** запроса (BIB-1 attribute set) над database-name → выполнение | RPN → внутренний AST (§7.1); database-name → `(tenant, db)`; результат → named result set + count |
| **Present** | выдача записей из result set (range `start`/`count`), preferredRecordSyntax | A1 рендерит каждую запись в MARC-синтаксис (USMARC/UNIMARC/RUSMARC/MARCXML/GRS-1/SUTRS/XML) |
| **Scan** | просмотр словаря термов от точки (browse index) — паритет нашего словарного просмотра | scan по индексу FTS/префиксу ([PROTOCOL_REFERENCE §3.4 `IC_nexttrm`](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md) — семантика «термин#число ссылок») |
| **Close** | корректное завершение сессии | освобождение result sets, отвязка сессии |

**Маппинг BIB-1 use-атрибутов → наши индексы** (per-tenant таблица §7.2; ядро — общеотраслевой профиль):

| BIB-1 use | Семантика | Наш FTS-индекс / префикс ([PROTOCOL_REFERENCE §5](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)) | Поле(я) recon |
|---|---|---|---|
| `1` Personal name | автор-персона | `author` / `A=` | 700/701/702 |
| `4` Title | заглавие | `title` / `T=` | 200^a |
| `7` ISBN | ISBN | `isbn` / `B=` | 10^a |
| `8` ISSN | ISSN | `issn` | 11^a/225^x |
| `21` Subject | предмет/рубрика | `subject` / `S=` | 606/607/610 |
| `1003` Author (any) | любой автор | `author_any` / `A=` | 70x/71x |
| `1016` Any | свободный | `all` (FTS-весь документ) | весь BO |
| `12` Local number | MFN/локальный № | `mfn` / `I=`(шифр 903) | MFN, 903 |
| `1007` Standard id | ид.№ | `stdid` | 19 |
| `31` Date of publication | год издания | `year` / `V=` | 210^d |
| `30` Date | дата | `date` | 210^d/210^h |

- **Relation/position/structure/truncation/completeness атрибуты** BIB-1 транслируются: `relation=3`(equal)→exact; `truncation=1`(right)→наш `$` (правое усечение, [PROTOCOL_REFERENCE §5.1](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)); `structure=2`(word)→FTS-слово; `structure=1`(phrase)→фразовый поиск; `relation=4`(≥)/`2`(≤) для year → диапазон.
- **Булевы операторы** RPN (`and`/`or`/`and-not`) → наш AST `AND`/`OR`/`NOT` (паритет операторам ИРБИС `* + ^`, [PROTOCOL_REFERENCE §5.2](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)). Прокс-операторы (proximity) → FTS `<->`/расстояние (паритет `(F)`/`.`), деградация в `AND`+warning при неподдержке.
- **Неизвестный use-атрибут** → diagnostic Bib-1 `114` (unsupported use attribute), не падение сессии.

**Per-tenant БД и auth:**
- Каждый тенант экспонирует одну или несколько баз (database-name = `<slug>` или `<slug>/<db>`), видимость баз = настройка тенанта (паритет `DBNAM*.MNU`, [CAPABILITY_MAP §8](../../../recon/deep/CAPABILITY_MAP.md)).
- Init-auth: `open` (анонимный, если тенант разрешил публичный Z-сервер), `idPass` (логин/пароль per-tenant Z-аккаунт, не равен staff-учётке), отображается на грант `z3950.serve:<db>:read` + энтайтлмент `protocols`.
- Rate-limit и `maximumRecordSize`/`preferredMessageSize` — per-tenant (защита от выкачки всего каталога; §6.5).

**AC (сервер):** AC-Z1 внешний YAZ-клиент (`yaz-client`) делает init→find→show над нашей базой тенанта и получает корректные MARC-записи; AC-Z2 scan возвращает упорядоченный список термов с числом постингов; AC-Z3 BIB-1 use `4`/`1`/`21`/`7` ищут по правильным индексам; правое усечение работает; AC-Z4 запрос к базе тенанта B под сессией тенанта A невозможен (изоляция); AC-Z5 неизвестный атрибут → корректный diagnostic, сессия жива.

### 1.2 Z39.50-клиент (заимствование из СКБР/WorldCat/внешних узлов)

**Зачем:** копикаталогизация ([SPEC_ws1 §4](../SPEC_ws1_cataloger.md)) — паритет ИРБИС-импорта через `yaz.dll` (параметры `ZIMPORTSEARCHPAGE`/`ZIMPORTFORMAT`, [ARM_CATALOGER `[Main]`](../../../recon/deep/reference/arms/ARM_CATALOGER.md)), но как сервис, не как АРМ-кнопка.

**Поток (search→present→импорт):**
```
каталогизатор (ws1) ─ "найти по ISBN/заглавию/автору в источнике X"
        ▼
 [z3950-client adapter] ── init(target) ── find(RPN из нашего AST) ── present(N) ──▶ MARC-записи
        ▼
 предпросмотр результатов (наш канон-вид через A1) → выбор записи
        ▼
 импорт: MARC(target) ── маппинг (RUSMARCFST/UNIMARCFST/USMARCFST + *GBL, recon) ──▶ запись в РЛ (920)
        ▼
 ФЛК импорта (A2 !998) → правка → сохранение (ws1)
```

- **Источники (targets) per-tenant** (паритет `LIBNETIP`/`ZIMPORTSEARCHPAGE`): СКБР, ЛИБНЕТ (RUSMARC), WorldCat/OCLC (MARC21), РГБ/РНБ Z-таргеты, LoC. Конфиг таргета — host/port/database/auth/preferredRecordSyntax/charset (MARC-8 vs UTF-8 vs cp1251 — конверсия на входе).
- **Запрос** строится из нашего AST → RPN с BIB-1 атрибутами target (обратный маппинг §7.2).
- **Импорт-маппинг** — переиспользуем recon-FST/GBL импорта (`RUSMARCFST`/`UNIMARCFST`/`USMARCFST`+`*GBL`, [ARM_CATALOGER](../../../recon/deep/reference/arms/ARM_CATALOGER.md)) как профиль трансформации MARC→наш канон; исполняется конвертером MARC (A1/ws1 §5), не дублируется здесь.
- **Дедуп при импорте**: перед вставкой — ФЛК `!998` (контроль импорта) + дублет-проверка по каталогу тенанта (ISBN/шифр/свёртка БО, [SPEC_ws1 §2.1](../SPEC_ws1_cataloger.md)); дубль → предупреждение со ссылкой на запись.

**AC (клиент):** AC-Z6 поиск по ISBN в СКБР/WorldCat возвращает записи, предпросмотр в канон-виде; AC-Z7 выбранная запись импортируется в текущий РЛ (920) с маппингом RUSMARC/MARC21→канон; AC-Z8 импортированная запись проходит ФЛК и предупреждает о дубле (998); AC-Z9 charset target (MARC-8/cp1251) корректно конвертируется в UTF-8.

---

## 2. SRU / SRW (1.1 / 1.2 / 2.0; CQL)

> «Z39.50 по HTTP/XML»: те же операции, но REST/SOAP-конверт и человекочитаемый язык запросов **CQL** вместо бинарного RPN. Эталон — стандартный SRU-клиент (LoC SRU test, zoomsh sru). SRU — стейтлесс-сервер (нас ищут), наш предпочтительный «современный» канал.

### 2.1 Операции

| Операция | SRU (GET/POST) | SRW (SOAP) | Назначение |
|---|---|---|---|
| **searchRetrieve** | `?operation=searchRetrieve&query=<CQL>&startRecord&maximumRecords&recordSchema&recordPacking` | SOAP `searchRetrieveRequest` | поиск + выдача записей одним вызовом |
| **explain** | `?operation=explain` (или base URL) | SOAP `explainRequest` | self-description: индексы, схемы, версии, лимиты (ZeeRex) |
| **scan** | `?operation=scan&scanClause=<index>&maximumTerms` | SOAP `scanRequest` | просмотр термов индекса с частотой |

- **Версии**: 1.1/1.2 (`version` параметр), **2.0** (новые имена параметров `query`/`maximumRecords`, `queryType`, `recordXMLEscaping`). Сервер принимает версию из запроса, дефолт — 1.2; объявляет поддержку в explain.
- **recordPacking/recordXMLEscaping**: `xml` (инлайн) / `string` (экранированный). **recordSchema**: `marcxml` (slim MARC21/UNIMARC XML), `mods`, `dc` (oai_dc), `rusmarcxml` — все рендерит **A1**.
- **diagnostics**: SRU diagnostic set (info:srw/diagnostic/1/*) — невалидный CQL → diag 10 (query syntax error); неизвестный индекс → diag 16 (unsupported index); неподдерживаемая схема → diag 66.

### 2.2 CQL → наш поисковый AST

CQL — реляционный язык: `index relation term` + булевы + модификаторы. Транслируется в наш общий AST (§7.1) тем же слоем маппинга, что и BIB-1:

| CQL | Семантика | Наш AST / индекс |
|---|---|---|
| `dc.title = "история"` | заглавие содержит | `MATCH(title, "история")` / `T=` |
| `dc.creator all "толстой лев"` | автор содержит все | `AND(author~толстой, author~лев)` / `A=` |
| `bath.isbn = "978..."` | точный ISBN | `EQ(isbn, ...)` / `B=` |
| `dc.date > 2000` | год издания > | `GT(year, 2000)` / `V=`-диапазон |
| `cql.serverChoice = "вода"` | любой индекс | `MATCH(all, "вода")` (FTS весь BO) |
| `title = "очист*"` | усечение `*` | правое усечение → наш `$` ([PROTOCOL_REFERENCE §5.1](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)) |
| `A and B` / `A or B` / `A not B` | булевы | `AND`/`OR`/`NOT` (паритет `* + ^`) |
| `A prox/distance<3 B` | близость | FTS proximity (паритет `(F)`/`.`) |

- **Context set** маппинг: `dc.*` (Dublin Core), `bath.*` (Bath profile — isbn/issn/lccn), `cql.*` (serverChoice/anywhere/allRecords), `rec.*` (rec.id→MFN). Per-tenant индекс-сет публикуется в `explain` (ZeeRex `<indexInfo>`).
- **Модификаторы отношения** (`=/==/<>/>/</>=/<=/all/any/adj`) → точное/диапазон/фразовое/all-of/any-of.
- **Неизвестный индекс/контекст-сет** → SRU diag 16/15, не падение.

### 2.3 recordSchema (MARCXML / DC / прочее)

`searchRetrieve` отдаёт каждую найденную запись в запрошенной схеме — **рендер A1**: `marcxml`→`umarcw`/`rmarcw` обёрнутый в MARC-slim XML; `dc`→Dublin-Core (есть в `PFTW.MNU`); `mods`→MODS-профиль; дефолт — `marcxml`. Конверт `<records><record><recordData>…`.

**AC (SRU/SRW):** AC-S1 `explain` возвращает валидный ZeeRex с индексами/схемами/версиями тенанта; AC-S2 `searchRetrieve` с CQL `dc.title=...` возвращает записи в `marcxml`; AC-S3 CQL-усечение/булевы/диапазон по году транслируются корректно; AC-S4 невалидный CQL → diag 10; AC-S5 `scan` отдаёт термы+частоту; AC-S6 SRW (SOAP) даёт тот же результат, что SRU (GET); AC-S7 изоляция тенанта по path.

---

## 3. OAI-PMH 2.0 (провайдер; incremental harvest)

> Протокол **массовой выгрузки/харвестинга метаданных** — основной канал для агрегаторов (НЭБ, региональные порталы, поисковые системы научных публикаций). Мы — **провайдер** (data provider): агрегатор периодически забирает (harvest) наши записи, дельтами. Эталон — стандартный OAI-валидатор (re3data/OpenAIRE validator, `oai-pmh-validator`).

### 3.1 Шесть verbs

| Verb | Назначение | Параметры |
|---|---|---|
| **Identify** | self-description репозитория | — → repositoryName, baseURL, protocolVersion `2.0`, adminEmail, earliestDatestamp, deletedRecord (`persistent`/`transient`/`no`), granularity, compression |
| **ListMetadataFormats** | доступные схемы | `identifier?` → `oai_dc` (обязательно) + `marc21`/`rusmarcxml`/`mods` |
| **ListSets** | иерархия наборов | `resumptionToken?` → per-tenant sets (§3.2) |
| **ListIdentifiers** | заголовки (id+datestamp+setSpec) | `metadataPrefix`, `from?`, `until?`, `set?`, `resumptionToken?` |
| **ListRecords** | записи целиком | `metadataPrefix`, `from?`, `until?`, `set?`, `resumptionToken?` |
| **GetRecord** | одна запись | `identifier`, `metadataPrefix` |

- **OAI-identifier**: `oai:<tenant-domain>:<db>/<mfn>` (устойчивый, паритет постоянной ссылки [SPEC_I2 §B](../SPEC_I2_catalog_search.md)).
- **datestamp**: UTC, granularity `YYYY-MM-DDThh:mm:ssZ` (или date-level) — из времени модификации записи (ядро I1 ведёт `updated_at`; в ИРБИС — версия/дозапись в конец MST, [CAPABILITY_MAP §4](../../../recon/deep/CAPABILITY_MAP.md)).

### 3.2 Наборы (sets) per-tenant

- **Set = логическая выборка** записей тенанта: по базе (`db:ibis`), по виду документа (920 → `type:book`/`type:journal`), по фонду/коллекции, по классификатору (ГРНТИ-узел), по «электронные/с полным текстом» (поле 951). Иерархические setSpec (`a:b:c`).
- Конфигурируются тенантом (какие срезы каталога публиковать наружу — приватность фонда). Дефолт — пусто (ничего не отдаём, пока тенант не включил публикацию).
- **selective harvesting**: `set` + `from`/`until` комбинируются (агрегатор берёт «книги, изменённые с даты X»).

### 3.3 resumptionToken (потоковая пагинация)

Большие выборки отдаются порциями: ответ несёт `<resumptionToken>` с зашитым курсором (наш стейтлес-токен: HMAC-подписанный `{tenant, set, prefix, from, until, cursor, expirationDate}` — без серверного стейта, идемпотентно докачиваемо). Агрегатор повторяет verb с токеном до пустого токена. `cursor`/`completeListSize` — опционально. Истёкший токен → error `badResumptionToken`.

### 3.4 Схемы и incremental

- **oai_dc** (обязательно, простой Dublin Core) — рендер A1; **marc21**/**rusmarcxml** (slim MARC XML) — A1; **mods** — опционально.
- **Incremental harvest**: `from`/`until` фильтруют по datestamp → отдаются только изменённые/новые. **Удаления**: `deletedRecord=persistent` — логически удалённая запись (ИРБИС-статус «логически удалена», [CAPABILITY_MAP §4](../../../recon/deep/CAPABILITY_MAP.md)) отдаётся с `<header status="deleted">`, чтобы агрегатор синхронизировал удаление.

### 3.5 Ошибки OAI

`badArgument`, `badVerb`, `cannotDisseminateFormat`, `idDoesNotExist`, `noRecordsMatch` (пустая выборка — валидный ответ, не HTTP-ошибка), `noSetHierarchy`, `badResumptionToken` — в OAI-XML конверте (HTTP 200 с error-элементом).

**AC (OAI):** AC-O1 `Identify` валиден (OAI-валидатор зелёный); AC-O2 `ListRecords&metadataPrefix=oai_dc` отдаёт записи порциями с рабочим resumptionToken; AC-O3 `from`/`until` отдают только изменённые; AC-O4 удалённая запись приходит со `status="deleted"`; AC-O5 `set` per-tenant фильтрует; AC-O6 `marc21`-схема валидна; AC-O7 тенант, не включивший публикацию, отдаёт пустую иерархию/`noRecordsMatch`; AC-O8 истёкший resumptionToken → `badResumptionToken`.

---

## 4. SIP2 (3M Standard Interchange Protocol 2.00; сервер самообслуживания)

> Текстовый протокол станций самообслуживания (self-check киоски, RFID-ворота, кассы оплаты). Мы — **сервер SIP2**, к которому подключается оборудование. Это **мост к нашему движку книговыдачи** (ws3/I3), а не отдельная логика. Эталон — SIP2-эмулятор (`sip2-server` test-harness, Koha/FOLIO SIP-tester).

### 4.1 Сообщения (message pairs)

SIP2 — пары «request код / response код», поля с двухсимвольными идентификаторами + разделитель `|`:

| Запрос | Код | Ответ | Код | Назначение → наш движок |
|---|---|---|---|---|
| Login | `93` | Login Response | `94` | аутентификация станции → per-tenant SIP-аккаунт + institution-id→тенант |
| SC Status | `99` | ACS Status | `98` | health/возможности; объявляем поддерживаемые сообщения, online-status |
| Patron Status Request | `23` | Patron Status Response | `24` | статус читателя (блокировки/штрафы/лимиты) → ws3/RDR |
| Patron Information | `63` | Patron Information Response | `64` | детальный статус: на руках/брони/штрафы/сумма → ws3 |
| Checkout | `11` | Checkout Response | `12` | **выдача** → движок книговыдачи (ws3 §4, RDR.40) |
| Checkin | `09` | Checkin Response | `10` | **возврат** → ws3 (возврат, сортировка) |
| Fee Paid | `37` | Fee Paid Response | `38` | оплата штрафа → PAY (ws3 §5) |
| Block Patron | `01` | (Patron Status) | `24` | блокировка читателя (потеря карты) |
| End Patron Session | `35` | End Session Response | `36` | завершение сессии у киоска |
| Hold | `15` | Hold Response | `16` | бронь/снятие брони (опц.) → ws3 бронь |
| Renew | `29` / Renew All `65` | `30` / `66` | продление → ws3 §4 (`40^L`, лимиты) |

- **Поля статуса** (`patron status` битовая строка): charge/renewal/recall privileges denied, too many items charged/overdue, excessive fines, card blocked — вычисляются из RDR: задолженность `40^F='******'` ([DB_CIRCULATION §3](../../../recon/deep/reference/databases/DB_CIRCULATION.md)), лимиты, блокировки.
- **Checksum** (`AY`/`AZ`) и **sequence number** — опциональная проверка целостности (error detection), включаемо per-станция.

### 4.2 Мост к движку книговыдачи (ws3) и edge

- SIP2-адаптер **не реализует** выдачу/возврат — он вызывает **ws3/I3** ([SPEC_ws3_circulation.md](../SPEC_ws3_circulation.md)): `Checkout(11)` → `circulation.checkout(reader, item)`; `Checkin(09)` → `circulation.checkin(item)`; результат (ok/блокировка/штраф) → SIP2-response.
- **Связь с edge (офлайн)**: киоск работает в библиотеке-edge-узле ([SPEC_I4 §C](../SPEC_I4_edge_offline.md)) — SIP2-сервер живёт **на edge**, выдача проходит локально (edge-master по книговыдаче), синхронизируется в облако при сети. SC Status `online=N` сигналит станции деградацию при потере облака; критичные операции (checkout/checkin) офлайн-устойчивы, оплата (`Fee Paid`) может буферизоваться.
- **self-checkout мобильного** ([SPEC_I2 §B #179](../SPEC_I2_catalog_search.md)) — отдельный REST-путь, но **тот же** `circulation.checkout` под капотом; SIP2 — для физического оборудования.

### 4.3 ПДн и безопасность

SIP2 несёт ПДн читателя (имя `AE`, статус) → **только TLS** (SIP2-over-TLS / stunnel-паритет), per-tenant SIP-аккаунт станции, журнал доступа (152-ФЗ, I6 B4). Минимизация: Patron Status отдаёт флаги/суммы, не полный профиль; имя — по флагу станции.

**AC (SIP2):** AC-I1 Login(93)→94 аутентифицирует станцию, institution→тенант; AC-I2 Patron Status(23)→24 отражает блокировку должника (`40^F='******'`); AC-I3 Checkout(11)→12 проводит выдачу через ws3, экземпляр уходит «на руки»; AC-I4 Checkin(09)→10 возвращает; AC-I5 Fee Paid(37)→38 гасит штраф в PAY; AC-I6 на edge-узле выдача проходит офлайн и синкается; AC-I7 транспорт TLS, ПДн минимизированы, доступ журналируется.

---

## 5. NCIP / ILS-DI (consortia message set)

> Протоколы межбиблиотечного взаимодействия в консорциуме/ЦБС: запрос статуса пользователя, заказ экземпляра, выдача между узлами (resource sharing). Мы — и **responder** (нас спрашивают), и **initiator** (мы спрашиваем). Прямой субстрат — слой консорциумов **CN #181** ([SPEC_I4 §D](../SPEC_I4_edge_offline.md)) и межбибл. абонемент ([DB_MBA](../../../recon/deep/reference/databases/DB_MBA.md), сиглы `sigl.mnu`). Эталон — NCIP-toolkit responder-тест, VuFind/FOLIO NCIP.

### 5.1 NCIP (NISO Z39.83) — message set

| Сообщение | Назначение → наша модель |
|---|---|
| **LookupUser** | статус читателя в нашей системе для узла-партнёра → RDR (блокировки/лимиты/право на МБА), как SIP2 Patron, но XML/межсистемно |
| **LookupItem** | статус/доступность экземпляра → ws3/910 (на руках/свободен/локация) |
| **RequestItem** | заказ экземпляра из другого узла (consortial borrowing) → создаёт заказ MBA/RQST ([DB_MBA §12 цикл](../../../recon/deep/reference/databases/DB_MBA.md)) |
| **CheckOutItem** | выдача экземпляра запрашивающему узлу/читателю → ws3 checkout с пометкой «межбибл.» |
| **CheckInItem** | возврат → ws3 checkin |
| **AcceptItem** | приём прибывшего экземпляра на узле-получателе → MBA приход |
| **CancelRequestItem** | отмена заказа → MBA отмена |
| **RenewItem** | продление межбибл. выдачи → ws3 renew |

- **Agency/institution** в NCIP → наш тенант/филиал (сигла фондодержателя, [DB_MBA §11 `sigl.mnu`](../../../recon/deep/reference/databases/DB_MBA.md): РГБ/РНБ/ВИНИТИ/…). Маршрутизация заказа фондодержателю — паритет recon-механики `902^D`→`942^A=M4` ([DB_MBA §11](../../../recon/deep/reference/databases/DB_MBA.md)).
- **ILS-DI** (DLF Discovery Interface) — упрощённый REST-родственник (GetAvailability, GetРatronInfo, RequestHold, RenewLoan): отдаётся как тонкий REST поверх той же модели, для discovery-слоёв (VuFind/Blacklight).

### 5.2 Роли и связь с CN #181

- **Responder** (нас спрашивают): партнёрский узел делает LookupUser/RequestItem → мы отвечаем из RDR/910/MBA.
- **Initiator** (мы спрашиваем): наш узел заказывает экземпляр у партнёра → RequestItem к нему → AcceptItem при доставке.
- **Resource sharing** между нашими же узлами (филиалы ЦБС, постаматы) — внутри **CN #181** ([SPEC_I4 §D](../SPEC_I4_edge_offline.md): holds/floating между узлами): NCIP — стандартный транспорт этого шеринга наружу (с не-нашими ИБС), внутренний шеринг между нашими узлами идёт через sync-движок I4 напрямую (быстрее), NCIP — для гетерогенного консорциума.
- **Auth/agency-trust**: per-pair доверие узлов (institution-id + ключ), журнал, изоляция тенанта (узел A не лукапит читателей тенанта B).

**AC (NCIP/ILS-DI):** AC-N1 LookupUser от партнёра возвращает статус читателя (блокировки/право МБА) без утечки лишних ПДн; AC-N2 RequestItem создаёт межбибл. заказ (MBA/RQST) с маршрутом на сиглу; AC-N3 CheckOutItem/CheckInItem проводят межузловую выдачу/возврат через ws3; AC-N4 как initiator — заказ у партнёра и AcceptItem при приёме; AC-N5 ILS-DI GetAvailability отдаёт доступность экземпляра discovery-клиенту; AC-N6 изоляция тенанта/agency-trust.

---

## 6. Архитектура: протокол-адаптеры поверх ядра

### 6.1 Топология

```
                 ВНЕШНИЙ МИР (нас ищут / мы ищем / агрегаторы / киоски / партнёры)
   Z-клиент   SRU-клиент   OAI-агрегатор   SIP2-киоск/RFID   NCIP-узел консорциума
      │            │             │               │                   │
 ┌────▼────┐  ┌────▼────┐   ┌────▼────┐    ┌─────▼─────┐      ┌──────▼──────┐
 │ z3950   │  │  sru    │   │  oai    │    │   sip2    │      │   ncip      │   ← адаптеры
 │ srv+cli │  │ srv     │   │ provider│    │  server   │      │ resp+init   │     (отдельные
 │ (ASN.1) │  │ (CQL)   │   │ (XML)   │    │  (TCP txt)│      │ (XML/HTTP)  │     сервисы/модули)
 └────┬────┘  └────┬────┘   └────┬────┘    └─────┬─────┘      └──────┬──────┘
      │ AST/маппинг │ AST/маппинг │ set/from/until │ msg→circ        │ msg→user/item/req
      └─────────────┴──────┬──────┴────────────────┴─────────────────┘
                           ▼
        ┌──────────────────────────────────────────────────────────┐
        │  ОБЩИЙ СЛОЙ:  SearchService (I2 PostgreSQL-FTS, AST §7.1)  │
        │               RecordService (ядро I1, JSONB запись)        │
        │               A1 рендер (MARCXML/ISO2709/DC/MODS)          │
        │               CirculationService (ws3/I3)                  │
        │               маппинг точек доступа (§7.2, per-tenant)     │
        │               tenant-resolver · auth · rate-limit · аудит  │
        └──────────────────────────────────────────────────────────┘
                           ▼
                 PostgreSQL (per-tenant t_<slug>) · A2 ФЛК · A4 авторитеты
```

### 6.2 Почему отдельные адаптеры

- **Изоляция проводных форматов**: ASN.1/BER (Z39.50), XML/HTTP (SRU/OAI/NCIP), текст-TCP (SIP2) — разные стеки, разные библиотеки (YAZ/python-yaz для Z; стандартный HTTP для SRU/OAI; кастомный TCP для SIP2). Падение/уязвимость одного парсера не валит остальные.
- **Независимое масштабирование/версии**: OAI-харвест (тяжёлая выкачка) масштабируется отдельно от SIP2 (низкая латентность киоска). Версии протоколов меняются независимо.
- **Опциональность per-tenant**: тенант включает только нужные протоколы (энтайтлмент `protocols`, под-флаги `z3950_server`/`oai_provider`/`sip2`/`ncip`); выключенный адаптер не слушает порт для тенанта.

### 6.3 Индексация (как протоколы видят данные)

- **Поиск** (Z/SRU/OAI-set-фильтр) идёт в **наш PostgreSQL-FTS** ([SPEC_I2 #122](../SPEC_I2_catalog_search.md)) — тот же индекс, что у читательского поиска; протоколы **не** имеют своего индекса. Это значит: реиндексация/морфология/синонимы автоматически доступны внешним клиентам.
- **OAI datestamp/incremental** — по `updated_at` записи (ядро I1); индекс по дате модификации для быстрых `from/until`-выборок.
- **Scan** (Z/SRU) — по словарным термам FTS-индекса/префикса (паритет `IC_nexttrm`, [PROTOCOL_REFERENCE §3.4](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)).

### 6.4 Tenant-scoping

| Протокол | Как определяется тенант |
|---|---|
| Z39.50 | database-name (`<slug>` / `<slug>/<db>`) + Init-auth account |
| SRU/SRW | URL path (`/sru/<slug>/<db>`) + опц. auth |
| OAI-PMH | per-tenant baseURL (`/oai/<slug>`) |
| SIP2 | Login institution-id (`AO` поле) → тенант + per-station account |
| NCIP/ILS-DI | `ToAgencyId`/`FromAgencyId` + agency-trust ключ |

Tenant-resolver — общий middleware; внутренний поиск/запись всегда под `search_path=t_<slug>` (RLS-инвариант, [SPEC_api_contracts §0](../engines/SPEC_api_contracts.md)). Cross-tenant — negative-тест в CI (DoD-гейт). Внешний идентификатор записи (OAI-id, Z local-number) **не раскрывает** записи другого тенанта.

### 6.5 Rate-limit / auth / антивыкачка

- **Auth**: per-protocol per-tenant аккаунты (Z-account, SIP-account, NCIP agency-key), отделённые от staff-учёток; гранты `z3950.serve`/`oai.provide`/`sip2.serve`/`ncip.respond` × энтайтлмент `protocols`.
- **Rate-limit**: per-account лимиты (запросов/мин, записей/present, maximumRecords); OAI — лимит размера порции + обязательный resumptionToken на больших выборках (антивыкачка всего каталога одним запросом). Z39.50 — `maximumRecordSize`/result-set лимит.
- **Публичность**: тенант явно выбирает, какие протоколы анонимны (публичный OAI/Z для открытого каталога) vs только-auth (SIP2/NCIP — всегда auth+TLS, несут ПДн).
- **Аудит**: каждый внешний запрос → trace с `tenant_id`/protocol/account; метрики; для ПДн-несущих (SIP2/NCIP) — журнал доступа 152-ФЗ.

### 6.6 Версии

| Протокол | Версии | Согласование |
|---|---|---|
| Z39.50 | v3 (v2 деградация) | Init options/version |
| SRU/SRW | 1.1 / 1.2 / 2.0 | `version` параметр; explain объявляет |
| OAI-PMH | 2.0 | Identify `protocolVersion` |
| SIP2 | 2.00 (1.0 fallback) | SC Status |
| NCIP | v1 / v2; ILS-DI 1.1 | message namespace/version |

---

## 7. Канонический поиск, маппинг, API/конфиг

### 7.1 Внутренний поисковый AST (общий для всех протоколов)

Промежуточное представление, в которое транслируются RPN (Z39.50), CQL (SRU), `set+from/until` (OAI):

```jsonc
SearchAST =
  | { op: "MATCH", index: string, term: string, mode: "word"|"phrase"|"exact"|"trunc-right" }
  | { op: "RANGE", index: string, from?: scalar, to?: scalar }     // год/дата
  | { op: "AND"|"OR"|"NOT", left: SearchAST, right: SearchAST }
  | { op: "PROX", left, right, distance: int, ordered: bool }      // близость → FTS
  | { op: "ALL" }                                                  // OAI ListRecords без query
```
- `index` — **канонический** (`title`/`author`/`subject`/`isbn`/`issn`/`year`/`all`/`mfn`/`stdid`/…), не протокольный.
- Исполняется `SearchService` (I2) → SQL поверх `to_tsvector('russian')`+`pg_trgm`+бустинг ([SPEC_I2 #122](../SPEC_I2_catalog_search.md)). Усечение `trunc-right` → префиксный FTS / `term:*` (паритет `$`, [PROTOCOL_REFERENCE §5.1](../../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)).
- Один AST — один движок: исправление релевантности/морфологии в I2 автоматически улучшает все протоколы.

### 7.2 Таблица маппинга точек доступа (per-tenant ресурс `access_points`)

Единая таблица соответствий «протокольный атрибут ↔ канонический индекс ↔ recon-префикс/поле», вместо маппинга в каждом адаптере:

| canon | BIB-1 use | CQL index | OAI (н/п) | recon префикс | recon поле |
|---|---|---|---|---|---|
| `title` | 4 | dc.title | — | `T=` | 200^a |
| `author` | 1, 1003 | dc.creator | — | `A=` | 70x |
| `subject` | 21 | dc.subject | — | `S=` | 60x |
| `isbn` | 7 | bath.isbn | — | `B=` | 10^a |
| `issn` | 8 | bath.issn | — | — | 11^a/225^x |
| `year` | 31 | dc.date | — | `V=` | 210^d |
| `all` | 1016 | cql.serverChoice | — | — | весь BO |
| `mfn` | 12 | rec.id | id-суффикс | `I=`(903) | MFN/903 |

- Сидируется общеотраслевым профилем (A5 [SPEC_seeding.md](../engines/SPEC_seeding.md)); тенант дополняет (свои локальные точки доступа). Базовые префиксы — из инвертирования `.FST` ([DB_IBIS](../../../recon/deep/reference/databases/DB_IBIS.md), 109 префиксов IBIS).
- Используется **обоими направлениями**: сервер (внешний атрибут→canon) и клиент (наш AST→RPN/CQL target-а, обратный маппинг по профилю целевого источника).

### 7.3 API / конфиг (управление протоколами — ws5/Администратор)

REST — tenant-scoped, конверт `{ok,data}`, двойной гейт `грант×энтайтлмент protocols`, в общий `openapi.yaml` (A7 [SPEC_api_contracts.md](../engines/SPEC_api_contracts.md)), тег `protocols`:

| Метод | Путь | Назначение | Грант |
|---|---|---|---|
| GET | `/api/protocols/config` | статус и настройки протоколов тенанта (вкл/порты/auth/sets) | `protocols.config:*:read` |
| PUT | `/api/protocols/config` | вкл/выкл протокол, лимиты, публичность (+ `Idempotency-Key`) | `protocols.config:*:admin` |
| GET | `/api/protocols/access-points` | таблица маппинга точек доступа тенанта (§7.2) | `protocols.config:*:read` |
| PUT | `/api/protocols/access-points` | правка маппинга (+ `Idempotency-Key`) | `protocols.config:*:admin` |
| GET | `/api/protocols/oai/sets` | наборы OAI тенанта (§3.2) | `protocols.config:*:read` |
| PUT | `/api/protocols/oai/sets` | определить/изменить наборы | `protocols.config:*:admin` |
| GET | `/api/protocols/targets` | внешние Z39.50/SRU источники заимствования (СКБР/WorldCat) | `cataloging.import:*:read` |
| PUT | `/api/protocols/targets` | конфиг target (host/port/db/auth/syntax/charset; секрет→KMS) | `cataloging.import:*:admin` |
| POST | `/api/protocols/borrow/search` | заимствование: поиск во внешнем источнике (§1.2) → канон-предпросмотр | `record.write:<db>:write` |
| POST | `/api/protocols/borrow/import` | импорт выбранной внешней записи в РЛ (+ ФЛК A2) | `record.write:<db>:write` |
| GET | `/api/protocols/explain` / `…/identify` | проксированный self-description SRU/OAI (для отладки) | `protocols.config:*:read` |

- **Стандартные протокольные порты/эндпоинты** (Z39.50 TCP :210-класс per-tenant-mux, SRU `/sru/<slug>/<db>`, OAI `/oai/<slug>`, SIP2 TCP+TLS, NCIP `/ncip/<slug>`) обслуживаются адаптерами, **не** этим REST — REST только управляет конфигом. Транспортные секреты (Z/SIP/NCIP аккаунты, target-креды) — в KMS (D2 PKI, I6), в ответах не раскрываются (паритет recon: `LIBNETUSER`/`LIBNETPASSWORD`/`MailPassword` — имена без значений, [ARM_CATALOGER](../../../recon/deep/reference/arms/ARM_CATALOGER.md)).
- **Per-tenant конфиг-модель** (схема `t_<slug>`): `protocol_config` (протокол, enabled, public, limits, auth_ref), `access_point_map` (§7.2), `oai_set` (setSpec, query/фильтр), `z_target`/`sru_target` (источники заимствования), `protocol_account` (внешний аккаунт станции/узла, secret_ref→KMS).

---

## 8. Критический путь

1. **Общий слой**: внутренний `SearchAST` (§7.1) + per-tenant `access_points` маппинг (§7.2) + tenant-resolver/auth/rate-limit + подключение к I2-FTS и A1-рендеру. Без него ни один адаптер не работает корректно. →
2. **SRU/SRW-сервер** (самый дешёвый «нас ищут»: HTTP+CQL+XML, без ASN.1) — explain/searchRetrieve/scan, recordSchema через A1. Первый внешний канал. →
3. **OAI-PMH-провайдер** — 6 verbs, sets per-tenant, resumptionToken, incremental, deleted; канал для НЭБ/агрегаторов (связь B3). →
4. **Z39.50-сервер** (ASN.1/BER, YAZ-стек) — init/search/present/scan, BIB-1-маппинг; паритет с тем, что ИРБИС **не отдавал**. →
5. **Z39.50/SRU-клиент** (заимствование) — targets СКБР/WorldCat/ЛИБНЕТ, search→present→импорт в РЛ через recon-FST/GBL + ФЛК A2 (закрывает ws1 §4). →
6. **SIP2-сервер** — мост к ws3 (checkout/checkin/patron/fee), TLS+ПДн-журнал, edge-офлайн (I4). →
7. **NCIP/ILS-DI** — responder+initiator поверх RDR/910/MBA, agency-trust; слой CN #181 (I4 §D).

**Выходной критерий B2:** наша платформа — **полноценный узел отраслевой экосистемы**: внешние клиенты находят нас по Z39.50 (BIB-1) и SRU (CQL) и забирают записи в MARCXML/RUSMARC/DC; агрегаторы (НЭБ) инкрементально харвестят нас по OAI-PMH 2.0 с наборами per-tenant и resumptionToken; каталогизатор заимствует из СКБР/WorldCat по Z39.50/SRU-клиенту с импортом в РЛ и ФЛК; станции самообслуживания/RFID работают по SIP2 (мост к ws3, офлайн на edge); консорциум обменивается по NCIP/ILS-DI (LookupUser/RequestItem/CheckOut) поверх RDR/MBA — всё через **один канонический поиск (PostgreSQL-FTS I2)** и **один рендер (A1)**, с tenant-scoping/auth/rate-limit/версионированием, заменяя точечный однонаправленный Z39.50-импорт ИРБИС (`yaz.dll`, `Z39_50_SERVER=0`) полным двунаправленным протокольным слоем.

---

## 9. Тест-матрица (реальные клиенты как эталон)

| Сценарий | Эталонный клиент | Проверяет | Этап КП |
|---|---|---|---|
| Z-сервер: init→find→show | `yaz-client`/`zoomsh` | сессия, RPN→AST, present MARC, BIB-1 use `4`/`1`/`21`/`7` | 4 |
| Z-сервер: scan словаря | `yaz-client scan` | термы+постинги (паритет `IC_nexttrm`) | 4 |
| Z-сервер: усечение/булевы | `yaz-client` | `$`-усечение, `and/or/and-not`→`* + ^` | 4 |
| Z-клиент: заимствование по ISBN | наш клиент → СКБР/тест-Z-target | search→present→импорт→ФЛК `!998`→дубль | 5 |
| Z-клиент: charset target | MARC-8/cp1251 target | конверсия в UTF-8 без потерь | 5 |
| SRU: explain (ZeeRex) | LoC SRU validator | индексы/схемы/версии тенанта | 2 |
| SRU: searchRetrieve CQL | SRU test-client | `dc.title`/`bath.isbn`/диапазон года→AST, marcxml | 2 |
| SRU: невалидный CQL | SRU client | diag 10 (syntax) / 16 (index) | 2 |
| SRW (SOAP) паритет SRU | SRW client | тот же результат | 2 |
| OAI: Identify/ListRecords | OAI-PMH validator | конверт, oai_dc, resumptionToken | 3 |
| OAI: incremental from/until | OAI harvester | только изменённые; `status="deleted"` | 3 |
| OAI: set per-tenant | OAI harvester | фильтрация набора; невключённый тенант → `noRecordsMatch` | 3 |
| OAI: истёкший токен | OAI harvester | `badResumptionToken` | 3 |
| SIP2: login+patron+checkout | SIP2-эмулятор (Koha/FOLIO tester) | 93/94, 23/24 (должник), 11/12 через ws3 | 6 |
| SIP2: checkin+fee paid | SIP2-эмулятор | 09/10, 37/38→PAY | 6 |
| SIP2: edge-офлайн | эмулятор на edge-узле | выдача офлайн + синк | 6 |
| NCIP: LookupUser/RequestItem | NCIP-toolkit responder-тест | статус читателя без лишних ПДн; заказ MBA на сиглу | 7 |
| NCIP: CheckOut/CheckIn межузел | NCIP tester | межбибл. выдача через ws3 | 7 |
| ILS-DI: GetAvailability | VuFind/discovery | доступность экземпляра | 7 |
| **Изоляция тенанта** (все протоколы) | каждый эталонный клиент | запрос к тенанту A не отдаёт записи/читателей B | сквозной |
| Rate-limit/антивыкачка | нагрузочный | OAI без токена не выкачивает всё; Z result-set лимит | 1,3 |

---

## 10. Риски

| Риск | Митигация |
|---|---|
| **Z39.50 ASN.1/BER — сложный бинарный стек** (своя реализация рискованна) | Использовать зрелый YAZ (наследие `yaz.dll` ИРБИС) через биндинг/обёртку как для клиента, так и для target; не писать BER с нуля; контракт-тест против `yaz-client` |
| **BIB-1↔наш-индекс маппинг неполон/неоднозначен** (разные источники трактуют use-атрибуты по-разному) | Per-tenant `access_points` (§7.2) с общеотраслевым дефолтом; неизвестный атрибут→diagnostic, не падение; калибровка на реальных СКБР/РГБ-таргетах |
| **Точный маппинг RUSMARC/UNIMARC↔наш канон не извлечён построчно из recon** (FST/GBL импорта названы, тело не разобрано) | Переиспользовать recon-FST/GBL (`RUSMARCFST`/`*GBL`) как профиль трансформации через A1/ws1; уточнить на боевом конфиге (`TODO recon #PROTO-01`); круговой тест import→export без потерь (ws1 §5 AC1) |
| **SIP2/NCIP несут ПДн читателя** (152-ФЗ) | TLS обязателен; минимизация (флаги/суммы, не полный профиль); per-account auth; журнал доступа (I6 B4); согласование локализации ПДн |
| **OAI-выкачка всего каталога** (нагрузка/приватность фонда) | resumptionToken обязателен на больших выборках; per-tenant sets (тенант сам решает, что публиковать); rate-limit; дефолт — ничего не отдаём |
| **Заимствование: дубли/мусорные внешние записи** | ФЛК `!998` + дублет-проверка по каталогу тенанта (ws1 §2.1) перед вставкой; предпросмотр в канон-виде до импорта |
| **NCIP мало распространён в РФ** (вместо него — ИРБИС-нативный МБА/корпоративные схемы) | NCIP/ILS-DI — для гетерогенного консорциума; внутренний шеринг между нашими узлами — через sync-движок I4 (быстрее); NCIP опционален per-tenant; приоритет ниже Z/SRU/OAI |
| **Charset-зоопарк** (MARC-8, cp1251, UTF-8 у разных таргетов/клиентов) | Явная конверсия на границе адаптера; декларация кодировки в init/explain; тест на cp1251/MARC-8 источниках |
| **Версионная фрагментация** (SRU 1.1/1.2/2.0, NCIP v1/v2) | Версия согласуется в init/explain/Identify; адаптер мультиверсионный; деградация с warning, не отказ |

---

## 11. Открытые вопросы (recon TODO + решения)

- `TODO(recon #PROTO-01)` — построчно разобрать импортные FST/GBL (`RUSMARCFST`/`UNIMARCFST`/`USMARCFST`+`*GBL`, [ARM_CATALOGER](../../../recon/deep/reference/arms/ARM_CATALOGER.md)): точный маппинг RUSMARC/UNIMARC/MARC21↔наш канон полей — нужен для Z/SRU-клиента (импорт) и Z/SRU/OAI-сервера (экспорт). Сейчас — переиспользуем тело FST через A1, маппинг калибруется круговым import→export тестом.
- `TODO(recon #PROTO-02)` — реальные параметры Z-таргетов СКБР/ЛИБНЕТ/РГБ (`LIBNETIP`/`ZIMPORTSEARCHPAGE` — URL/порт/database/preferredRecordSyntax/auth) на боевом конфиге тенанта.
- **Полнота BIB-1-профиля**: какой набор use-атрибутов обязателен для СКБР/НЭБ-совместимости (отраслевой профиль РФ vs минимум Bath) — согласовать с пилотом.
- **Выбор SIP2-оборудования** под пилот (СПб ГТБ/вуз): модели self-check/RFID-ворот, их диалект SIP2 (расширения 3M vs нестандартные поля).
- **NCIP vs нативный шеринг I4**: где граница — какие операции консорциума идут по NCIP (внешние ИБС), какие через sync-движок (наши узлы); приоритет NCIP в роадмапе CN #181.
- **OAI deletedRecord-политика**: `persistent` (храним tombstone-историю) vs `transient` — зависит от модели удаления ядра I1 (логическое удаление → отдаём `status="deleted"`; физическое — теряем datestamp).
- **Анонимный vs auth Z39.50/OAI-сервер**: дефолт публичности (открытый каталог вуза vs закрытый) — политика тенанта; согласовать с I6.

---

## Сводка

**Адаптерная архитектура.** Пять протоколов = пять отдельных адаптеров (микросервисов/модулей) поверх общего ядра: **z3950** (сервер+клиент, ASN.1/BER через YAZ), **sru** (сервер, CQL/XML), **oai** (провайдер, XML), **sip2** (сервер, текст-TCP+TLS), **ncip** (responder+initiator, XML/HTTP). Все адаптеры транслируют свой проводной формат и систему атрибутов в **единый канонический слой**: внутренний `SearchAST` (§7.1) → **наш PostgreSQL-FTS** ([SPEC_I2 #122](../SPEC_I2_catalog_search.md)); выдача записей → **рендер A1** (MARCXML/ISO 2709/RUSMARC/UNIMARC/MARC21/Dublin Core/MODS, [SPEC_engine_pft.md](../engines/SPEC_engine_pft.md)); книговыдача (SIP2/NCIP) → **ws3/I3** ([SPEC_ws3_circulation.md](../SPEC_ws3_circulation.md)); заимствование (Z/SRU-клиент) → импорт в РЛ + ФЛК A2 ([SPEC_ws1 §4–5](../SPEC_ws1_cataloger.md)). Маппинг точек доступа (BIB-1 use ↔ CQL index ↔ recon-префикс `T=`/`A=`/`S=` ↔ canon) — в одной per-tenant таблице `access_points` (§7.2), общей для серверной и клиентской ролей. Tenant-scoping (database-name/path/institution-id→тенант), auth (per-protocol-аккаунты × энтайтлмент `protocols`), rate-limit/антивыкачка (resumptionToken, result-set лимиты), версионирование (Z v3 / SRU 1.1-2.0 / OAI 2.0 / SIP2 2.00 / NCIP v1-v2) — общий слой. Заменяет точечный однонаправленный Z39.50-импорт ИРБИС (`yaz.dll`, серверная часть `Z39_50_SERVER=0` выключена) **полным двунаправленным протокольным слоем гос-узла**.

**Файл:** `C:\IRBIS64\_recon\docs\design\specs\gov\SPEC_protocols.md`

**Топ-3 открытых вопроса:**
1. **PROTO-01 — маппинг MARC↔канон не разобран построчно** (импортные FST/GBL названы в recon, тело не извлечено): нужен для корректного импорта (Z/SRU-клиент) и экспорта (Z/SRU/OAI-сервер); пока переиспользуем тело FST через A1, калибруем круговым import→export тестом — критический путь к AC-Z7/AC-S2/AC-O6.
2. **Полнота BIB-1/CQL-профиля для СКБР/НЭБ-совместимости** — обязательный отраслевой набор use-атрибутов/индексов РФ vs минимум Bath; определяет, найдут ли нас гос-агрегаторы «как положено».
3. **Граница NCIP vs нативный шеринг I4 (CN #181)** — какие операции консорциума идут по стандартному NCIP (гетерогенные ИБС) и какие через быстрый sync-движок I4 между нашими узлами; влияет на приоритет и объём NCIP-адаптера.
