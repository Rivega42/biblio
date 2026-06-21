# SPEC · Финансы (Парус) + ERM + конвейер оцифровки (DAM) + CDL

> Закрывает пробел **D6** ([DESIGN_COVERAGE §D6](../../DESIGN_COVERAGE.md) — «Финансы (Парус) + ERM (#182) + конвейер оцифровки (DG #159/#180) + CDL — оркестрация. ❌/🟡 → I7/I5»). Эпик [#188](https://github.com/Rivega42/biblio/issues/188), родители **I5** (АРМ-паритет: финансы комплектования, ERM как движок ws2) и **I7** (коммерциализация: оцифровка как платный модуль, метеринг хранилища/трафика). Доводит четыре «отложенных-но-нужных» блока от «названо» до реализуемости (контракт/модель/AC), фиксируя границы с уже спроектированными слоями.
>
> **Грунтовка (читать как ground truth):**
> [SPEC_ws2 §9 / §4](../SPEC_ws2_acquisition.md) (финансы комплектования: цены/суммы 62/88^G/N/P, источник финанс. `Istfin.mnu`, каналы `KP.mnu`, валюта `val.mnu`, **счёт ИРБИС-Парус 88^J/^I**, КСУ-распределение партии) ·
> [CAPABILITY_MAP §11 / §8](../../../recon/deep/CAPABILITY_MAP.md) (полные тексты: 11-я строка `<DB>.PAR`, поля **951/950/955**, извлечение/кэш PDF `irbis_server.ini [FullText]`, `pdftotext`/QuickPDF; БД **RIGHT/LICH/ZAPR**; протоколы/периферия) ·
> [PRODUCT_PRACTICES §«Цифровая библиотека»/«Управление ресурсами»](../../PRODUCT_PRACTICES.md) (**ERM/COUNTER/knowledge base**, IIIF-просмотр, OAIS/fixity, **CDL**, **конвейер оцифровки capture→DAM→OCR→тег→каталог→IIIF**, «заменить отдельный сканирующий продукт»; пилот СПб театральная — книги + эскизы) ·
> [SPEC_reader_jirbis §4](../SPEC_reader_jirbis.md) ([#97](../SPEC_I2_catalog_search.md) view-only прокси: 951 `^A`путь/`^I`URL, 951(`^D`/`^L`/`^9`)+RIGHT(IP/категория/период), **приоритет 951>955**, лимит страниц, всё через бэкенд-прокси; DG/IIIF Content Search #180/#162) ·
> [SPEC_rag §1.4/§6.2](../diff/SPEC_rag.md) (OCR/полнотекст-связь: `paragraph`-чанки из оцифрованного PDF, IIIF Content Search, авто-каталогизация из PDF; **этот SPEC поставляет ALTO/hOCR-координаты и текст, RAG их потребляет**) ·
> [SPEC_I2 §B #97](../SPEC_I2_catalog_search.md) (карточка: просмотрщик обложек/**IIIF**/PDF, AC2 подсветка по координатам Content Search) ·
> [SPEC_engine_flk §4.1](../engines/SPEC_engine_flk.md) (черновик метаданных оцифровки проходит ФЛК phase=import) · [SPEC_engine_notifications](../engines/SPEC_engine_notifications.md) (A6 — уведомления о возврате CDL/истечении лицензии).
>
> **Принципы границ.** Этот SPEC **оркеструет**, а не дублирует: финансовые суммы/КСУ-проводки живут в ws2; права на файл и view-only-прокси — в #97; OCR-потребление (поиск/RAG) — в SPEC_rag; биллинг-движок/метрики тарификации — в **D5** ([DESIGN_COVERAGE §D5](../../DESIGN_COVERAGE.md), I7); уведомления — в A6; авторитеты/ФЛК черновика — A4/A2. Здесь — **финансовая интеграция (Парус), ERM-модель, конвейер DAM с оркестрацией/очередью, CDL-движок** и их контракты.

---

## 0. Назначение и границы

**Назначение.** Четыре связанных, ранее «скелетных» блока платформы:

1. **Финансы/Парус** — двусторонняя сверка комплектования с внешней бухгалтерией (Парус и аналоги): связь счёт/бюджет (`88^J/^I`), распределение бюджета по фондам/источникам финансирования, сверка проведённых сумм. **Read-only в Phase 1** (импорт справочников счетов + сверка), write (формирование платёжных заявок) — Phase 2.
2. **ERM ([#182](https://github.com/Rivega42/biblio/issues/182))** — управление электронными ресурсами: лицензии/доступы/сроки, **COUNTER/SUSHI-учёт использования** (связь B1 гос-статистика), интеграция э-подписок/ЭБС, knowledge base доступов. ERM — это «движок ws2» для э-ресурсов (паритет подписке периодики POST, но для электронного).
3. **Конвейер оцифровки (DAM, DG [#159](https://github.com/Rivega42/biblio/issues/159)/[#180](https://github.com/Rivega42/biblio/issues/180))** — capture (сканер TWAIN/edge) → объектное хранилище → **fixity (SHA256)** → OCR/HTR → **ALTO/hOCR-координаты** → индексация (поиск/подсветка) → метаданные (**950/951/955**) → **IIIF**-манифесты/просмотрщик. С оркестрацией, очередью, ресурс-лимитами. **Цель — заменить отдельный сканирующий продукт.**
4. **Controlled Digital Lending (CDL)** — временная выдача э-копий оцифрованных изданий: **owned-to-loaned ratio**, DRM/таймер, права на базе #97 (951/RIGHT) и циркуляционной модели I3.

**Границы (что НЕ здесь):**
- Цикл комплектования (заявка→заказ→поступление→КСУ→выбытие), суммы/проводки 62/88 → **ws2** ([SPEC_ws2](../SPEC_ws2_acquisition.md)). Финансы здесь — **интеграционный слой** поверх ws2-данных, не их замена.
- Биллинг **тенанта** (тарифы/счета/НДС за SaaS), метрики метеринга как продукт → **D5** (I7). Здесь — метрики оцифровки/ERM-стоимости **отдаются** в D5.
- Лексический/полнотекстовый/семантический поиск, RAG, авто-каталогизация → **#122/SPEC_rag**. Конвейер DAM **поставляет** текст+координаты+`paragraph`-чанки; индексирует и ищет — поиск.
- Права на файл, view-only-прокси, постраничный рендер PDF → **#97** ([SPEC_reader §4](../SPEC_reader_jirbis.md)). CDL **переиспользует** этот прокси, добавляя слой временного entitlement.
- Циркуляционная механика (статусы экземпляра, очередь брони, продление) → **I3** ([SPEC_I3](../SPEC_I3_circulation_storage.md)). CDL — это «цифровой экземпляр» поверх той же модели loan.
- Уведомления (истечение лицензии ERM, возврат CDL, готовность оцифровки) → **A6** ([SPEC_engine_notifications](../engines/SPEC_engine_notifications.md)).

---

## 1. Финансы / интеграция с Парус

### 1.1 Что есть в recon и что строим

ИРБИС связывает поступление со счётом бухгалтерии через **поле 88** КСУ ([SPEC_ws2 §4](../SPEC_ws2_acquisition.md)): `^J`/`^I` — счёт (интеграция ИРБИС-Парус), `^G` сумма, `^N` НДС, `^L` источник финансирования (`Istfin.mnu`), `^M` оплачено (`Nd.mnu`), `^H` платно/бесплатно (`netda.mnu`). Это **точки сопряжения**, но сам обмен с Парусом в конфигах не формализован (open-question). Мы строим **интеграционный адаптер** поверх ws2-данных, не трогая доменную модель комплектования.

### 1.2 Фазы интеграции (граница read-only Phase 1)

| Фаза | Направление | Что | Риск |
|---|---|---|---|
| **Phase 1 (read-only)** | Парус → платформа | импорт справочника **счетов/бюджетных строк/КБК** + проведённых сумм; **сверка** (reconciliation): КСУ-сумма (88^G) ↔ проведённая сумма по счёту (88^J); отчёт расхождений | низкий — не пишем в бухгалтерию |
| **Phase 2 (write)** | платформа → Парус | формирование **платёжной заявки/обязательства** из заказа (62), отдача в Парус; статус оплаты возвращается | высокий — финансовая запись во внешней системе; gated за грантом + аудитом |

**Решение: Phase 1 — обязательна и достаточна для паритета** (ИРБИС хранит `^J/^I` как ссылку, реальную проводку делает бухгалтер в Парусе). Phase 2 — опциональный платный модуль (I7), включается per-tenant. Граница зафиксирована, чтобы пилот не блокировался на write-интеграции с чужой ERP.

### 1.3 Адаптерная модель (провайдер абстрагирован)

Парус — не единственная бухгалтерия (1С, «Смета», региональные казначейские системы). Абстракция `AccountingProvider`:

```
AccountingProvider (интерфейс)
  importChart() -> ChartOfAccounts        // счета/бюджетные строки/КБК/источники
  importPostings(period) -> Posting[]      // проведённые суммы за период
  // Phase 2:
  submitObligation(order) -> ObligationRef // платёжное обязательство из заказа
  pollPayment(ref) -> PaymentStatus
  provider_id  string   // "parus" | "1c" | "smeta" | "csv-manual"
```

> **Граница.** Транспорт Парус-специфичен (файловый обмен/XML/REST — open-question Q-FIN-1, уточняется на боевом контуре тенанта). Домен знает только интерфейс; `csv-manual` — деградационный провайдер (ручная загрузка выписки), чтобы интеграция не блокировала тенанта без API Паруса.

### 1.4 Распределение бюджета по фондам

Поверх ws2: бюджет тенанта делится на **строки** (источник финансирования `Istfin.mnu` × фонд/МХ `mhr.mnu` × канал `KP.mnu` × период). Каждая КСУ-проводка поступления (88) **списывает** из соответствующей строки; ERM-лицензия (раздел 2) и оцифровка (если платная) тоже списывают. `BudgetLine` — агрегат, не дублирует суммы 88, а **проецирует** их.

```
budget_line
  id           uuid PK
  tenant_id    uuid NOT NULL            -- RLS (ядро I1)
  fiscal_year  int  NOT NULL
  source_fin   text NOT NULL            -- Istfin.mnu (бюджет/внебюджет/грант/дар)
  fund         text NULL                -- МХ/фонд (mhr.mnu)
  account_ref  text NULL                -- счёт/КБК из Паруса (88^J)
  planned      numeric(14,2) NOT NULL   -- план
  committed    numeric(14,2) NOT NULL   -- заказано (Σ 62^D по строке)
  spent        numeric(14,2) NOT NULL   -- проведено (Σ 88^G сверено с Парусом)
  currency     text NOT NULL DEFAULT 'RUB'  -- val.mnu
  UNIQUE (tenant_id, fiscal_year, source_fin, fund, account_ref)
```

### 1.5 Сверка (reconciliation)

`spent` (наша Σ 88^G по строке) сверяется с `importPostings()` Паруса по `account_ref`/периоду; расхождение > порога → запись в **отчёт сверки** (что у нас, что в Парусе, дельта, статус: совпало/расхождение/не найдено). Отчёт — для бухгалтера; ничего автоматически не правится (Phase 1 read-only).

### 1.6 AC — финансы

- **AC-F1.** Импорт справочника счетов/КБК из Паруса (или CSV-провайдером) наполняет `budget_line.account_ref`; КСУ-проводка 88 связывается со строкой бюджета по `88^J`/источнику.
- **AC-F2.** Распределение бюджета: `committed`/`spent` агрегируются из ws2 (62/88) по строке; перерасход (`committed > planned`) сигнализируется, не блокирует (политика тенанта).
- **AC-F3.** Сверка Phase 1 read-only: отчёт расхождений «наша Σ88^G ↔ проведено в Парусе» формируется; платформа **не пишет** в бухгалтерию.
- **AC-F4.** Адаптер абстрагирован: смена провайдера (Парус→1С→CSV) не трогает доменную модель `budget_line`/ws2; `csv-manual` работает без API.
- **AC-F5.** Phase 2 (если включён): платёжная заявка из заказа отдаётся в Парус под грантом + аудитом; без гранта — недоступна.

---

## 2. ERM — управление электронными ресурсами (#182)

### 2.1 Назначение

ERM — «движок ws2 для электронного»: то, чем подписка периодики (POST→OJK) является для печатного, ERM является для э-ресурсов (ЭБС, э-журналы, базы данных, отдельные э-книги). Управляет **жизненным циклом доступа**: лицензия → активация → мониторинг использования (COUNTER) → продление/прекращение. Эталоны — Alma ERM, FOLIO eHoldings, EBSCO ([PRODUCT_PRACTICES §«Управление ресурсами»](../../PRODUCT_PRACTICES.md)).

### 2.2 Модель данных

```
e_resource                              -- ресурс (ЭБС/пакет/э-журнал/БД)
  id           uuid PK
  tenant_id    uuid NOT NULL            -- RLS
  title        text NOT NULL
  provider     text NOT NULL            -- ЭБС «Лань»/«Юрайт»/eLibrary/...
  kind         enum                     -- package | journal | database | ebook
  platform_url text NULL
  identifiers  jsonb                    -- ISSN/ISBN/DOI-префикс/проприетарный id

license                                 -- лицензия на ресурс
  id           uuid PK
  tenant_id    uuid NOT NULL
  e_resource   uuid NOT NULL REFERENCES e_resource
  license_type enum                     -- subscription | perpetual | trial | OA | consortial
  start_date   date NOT NULL
  end_date     date NULL                -- null для perpetual
  cost         numeric(14,2) NULL       -- связь budget_line (раздел 1.4)
  budget_line  uuid NULL REFERENCES budget_line
  terms        jsonb                    -- одновр. доступы, ILL-разрешён?, post-cancellation, walk-in
  status       enum                     -- active | expiring | expired | cancelled | trial
  INDEX (tenant_id, status, end_date)   -- алерты истечения (A6)

access_point                            -- как читатель попадает в ресурс
  id           uuid PK
  tenant_id    uuid NOT NULL
  license      uuid NOT NULL REFERENCES license
  method       enum                     -- ip_range | ezproxy | oidc(ЕСИА) | referrer | login_pass
  config       jsonb                    -- IP-маски/SP-метаданные/прокси-конфиг
  coverage     jsonb                    -- что покрыто (диапазон лет/томов; knowledge base, 2.4)
```

### 2.3 COUNTER/SUSHI-учёт (связь B1)

**COUNTER** — стандарт отчётов использования э-ресурсов (TR/PR/IR-отчёты, метрики `Total_Item_Requests`, `Unique_Title_Requests` и т.п.); **SUSHI** — протокол их автозабора (REST-API провайдера). ERM:
- **Тянет** SUSHI-отчёты с платформ провайдеров по расписанию (`fetchCounterReport(provider, period)`), нормализует в единую модель `usage_stat`.
- **Считает cost-per-use** (стоимость лицензии / число использований) — ключевая метрика принятия решения о продлении.
- **Отдаёт** агрегаты в гос-статистику **B1** ([DESIGN_COVERAGE §B1](../../DESIGN_COVERAGE.md): «COUNTER/SUSHI») и в дашборды комплектатора (ws2 demand-driven: что не используется → не продлевать; что используется на пределе одновр. доступов → доукупить).

```
usage_stat
  id           uuid PK
  tenant_id    uuid NOT NULL            -- RLS
  e_resource   uuid NOT NULL REFERENCES e_resource
  period       date NOT NULL            -- месяц отчёта
  report_type  text NOT NULL            -- TR_J1 | PR_P1 | IR_A1 | ...
  metric       text NOT NULL            -- Total_Item_Requests | Unique_Title_Requests | ...
  value        bigint NOT NULL
  source       enum                     -- sushi | manual_upload
  UNIQUE (tenant_id, e_resource, period, report_type, metric)
```

> **Граница приватности.** COUNTER — **агрегированная** статистика использования (без идентификации читателя); это не история чтения (152-ФЗ B4). SUSHI-токены провайдеров — секреты тенанта (хранилище секретов I6, не в `config` открыто).

### 2.4 Knowledge base доступов

KB — карта «какие тайтлы/диапазоны покрыты какой лицензией» (паритет FOLIO eHoldings / Alma CZ): связывает запись каталога/портала с активным `access_point`, чтобы OPAC показал «доступно онлайн через ЭБС X» и **link-resolver** (OpenURL, [PRODUCT_PRACTICES §«Обнаружение»](../../PRODUCT_PRACTICES.md)) довёл до полного текста. Для Phase 1 — ручное/CSV-наполнение coverage; глобальная KB провайдеров (как GOKb) — перспектива.

### 2.5 Жизненный цикл и алерты

`license.status` переходит `trial→active→expiring→expired/cancelled`; за N дней до `end_date` — алерт комплектатору через **A6** ([SPEC_engine_notifications](../engines/SPEC_engine_notifications.md)). Перерасход одновр. доступов (`terms`) или истечение → сигнал. Решение о продлении опирается на cost-per-use (2.3).

### 2.6 AC — ERM

- **AC-E1.** Лицензия заводится с типом/сроками/условиями и точкой доступа (IP/EZproxy/ЕСИА); статус ведётся по жизненному циклу.
- **AC-E2.** SUSHI-забор COUNTER-отчёта нормализуется в `usage_stat`; cost-per-use считается; агрегат отдаётся в B1 и дашборд ws2.
- **AC-E3.** Истечение лицензии (за N дней) шлёт алерт через A6; expired-ресурс помечается недоступным в OPAC.
- **AC-E4.** Knowledge base связывает запись/портал с активной точкой доступа; OPAC показывает «доступно онлайн», link-resolver ведёт к полному тексту.
- **AC-E5.** Стоимость лицензии списывается из `budget_line` (раздел 1.4); SUSHI-токены — в секрет-хранилище, не в открытом конфиге.

---

## 3. Конвейер оцифровки (DAM) — DG #159/#180

### 3.1 Архитектура конвейера

```
[capture]    сканер TWAIN/edge-узел | загрузка файлов | импорт папки
   │          (книжный/планетарный/планшетный; пилот СПб — книги + эскизы)
   ▼
[ingest]     приём в DAM: создать digital_object (master) → object storage (S3-совместимое)
   │          fixity: SHA256 при приёме (3.3); вирус-скан; дедуп по хэшу
   ▼
[derive]     деривативы: тайлы (pyramidal TIFF/JPEG для IIIF), превью, thumbnail, PDF
   ▼
[ocr/htr]    OCR (печать) / HTR (рукопись) → текст + ALTO/hOCR (координаты слов) (3.4)
   ▼
[index]      текст+координаты → поиск (#122/SPEC_rag): paragraph-чанки, Content Search
   ▼
[metadata]   связать с записью каталога: поля 950(имидж)/951(путь/URL)/955(полнотекст)
   │          + авто-каталог черновик (SPEC_rag §6) ← опционально
   ▼
[publish]    IIIF-манифест (3.5) → просмотрщик (#97/#162) с подсветкой по координатам
```

Каждый шаг — **идемпотентная задача** в очереди (3.2); объект проходит конвейер как стейт-машина (`status`: ingested→derived→ocr_done→indexed→published, с `failed`/`retry` на каждом).

### 3.2 Оркестрация, очередь, ресурс-лимиты

- **Очередь задач** (паритет событийной шине I7 #107 / outbox): каждый шаг — сообщение; воркеры тянут по типу (OCR-воркер, derive-воркер). Падение задачи → retry с backoff; превышение retry → `failed` + алерт (A6).
- **Ресурс-лимиты per-tenant:** OCR/derive — тяжёлые (CPU/GPU, время); лимит параллельных задач и объёма/период per-tenant (анти-DoS, cost-cap; метрики метеринга → **D5**). Превышение → задача ждёт в очереди, не падает.
- **Приоритет:** ingest/fixity — синхронно-быстро; OCR/derive — фоном; CDL-запрошенный объект может получить приоритет.
- **Edge-capture:** сканер на edge-узле библиотеки (TWAIN, паритет [SPEC_I4](../SPEC_I4_edge_offline.md)); мастер заливается в облако при сети (offline-first), деривативы/OCR — в облаке.

### 3.3 Цифровая сохранность (fixity, OAIS)

- **SHA256 при приёме** записывается в `digital_object.checksum`; периодическая **проверка fixity** (фоновое задание) перечитывает объект и сверяет хэш → битрот/повреждение детектируется, алерт.
- **Мастер неизменяем** (write-once); деривативы пересоздаваемы из мастера. Версионирование метаданных, не мастера.
- Паритет OAIS ([PRODUCT_PRACTICES §«Цифровая сохранность»](../../PRODUCT_PRACTICES.md)): SIP(приём)→AIP(хранение)→DIP(выдача). Миграция форматов — перспектива.

### 3.4 OCR/HTR → ALTO/hOCR-координаты (связь поиск/RAG)

- OCR (печать) и **HTR** (рукопись, для архивных пилотов) → **полный текст** + **ALTO XML / hOCR** (координаты каждого слова на странице).
- **Это поставщик для [SPEC_rag §1.4](../diff/SPEC_rag.md):** текст → `paragraph`-чанки (полнотекстовый/семантический поиск); координаты → **подсветка термина на странице** (IIIF Content Search, [#97 AC2](../SPEC_I2_catalog_search.md)/#180/#162). Конвейер DAM **производит** артефакты; индексирует/ищет — поиск. Контракт: `{record_id, page, text, words:[{w, x,y,w,h}]}`.
- Per-page confidence OCR; низкое → флаг «нужна вычитка» (HITL); вычитка правит текст-слой, не мастер.

### 3.5 IIIF (манифесты + просмотрщик)

- **IIIF Presentation API**: на каждый оцифрованный объект — `manifest.json` (canvases=страницы, метаданные, ссылки на тайлы). **IIIF Image API**: deep-zoom тайлы из object storage.
- **IIIF Content Search API**: поиск внутри документа по OCR-координатам (3.4) → подсветка на странице. Это веб-проекция `ji_highlight` ИРБИС ([SPEC_reader §4](../SPEC_reader_jirbis.md)) на стандарт.
- Просмотрщик — компонент #97/#162 (Mirador/UV-подобный или свой на DS); открывается из карточки записи.
- **Замена сканирующего продукта:** интегрированный capture→IIIF закрывает функцию отдельного ПО оцифровки (цель PRODUCT_PRACTICES).

### 3.6 Метаданные (950/951/955) — связь с каталогом

Опубликованный объект связывается с библиозаписью через recon-поля ([CAPABILITY_MAP §11](../../../recon/deep/CAPABILITY_MAP.md)): **951** (`^A` относит. путь к файлу в хранилище / `^I` URL, взаимоисключающи), **950** (имидж), **955** (полнотекст-привязка). Папка/хранилище = 11-й параметр PAR в ИРБИС; у нас — object storage + `digital_object`. Авто-каталогизация черновика метаданных — через [SPEC_rag §6](../diff/SPEC_rag.md), проходит ФЛК (A2).

```
digital_object
  id           uuid PK
  tenant_id    uuid NOT NULL            -- RLS
  record_id    bigint NULL              -- связь с каталогом (951/950/955); null до привязки
  kind         enum                     -- book_scan | image | sketch(эскиз) | manuscript | av
  master_uri   text NOT NULL            -- мастер в object storage (write-once)
  checksum     text NOT NULL            -- SHA256 (fixity, 3.3)
  status       enum NOT NULL            -- ingested|derived|ocr_done|indexed|published|failed
  iiif_manifest text NULL               -- URI манифеста (3.5)
  ocr_status   enum                     -- none|done|needs_review
  page_count   int NULL
  field_links  jsonb                    -- {f951:[...], f950:[...], f955:[...]}
  created_at   timestamptz NOT NULL
  INDEX (tenant_id, status), INDEX (tenant_id, record_id)

digital_page                            -- страница (для IIIF canvas + OCR)
  id           uuid PK
  object_id    uuid NOT NULL REFERENCES digital_object
  page_no      int NOT NULL
  image_uri    text NOT NULL            -- тайл/дериватив
  ocr_text     text NULL
  ocr_alto_uri text NULL                -- ALTO/hOCR (координаты, 3.4)
  ocr_conf     float NULL
  UNIQUE (object_id, page_no)
```

### 3.7 AC — DAM

- **AC-D1.** Capture (TWAIN/edge/загрузка) создаёт `digital_object` (master в object storage) с **SHA256** при приёме; периодическая fixity-проверка детектирует повреждение.
- **AC-D2.** Конвейер — очередь идемпотентных задач с retry/backoff и **ресурс-лимитами per-tenant**; падение шага не теряет объект (стейт-машина, `failed`→retry); метрики метеринга отдаются в D5.
- **AC-D3.** OCR/HTR даёт текст + **ALTO/hOCR-координаты**; текст→`paragraph`-чанки поиска (#122/SPEC_rag), координаты→Content Search; низкий confidence → флаг вычитки.
- **AC-D4.** Объект связывается с записью через **950/951/955**; авто-каталог черновик (если включён) проходит ФЛК A2 (phase=import), не пишет в чистовик без ревью.
- **AC-D5.** Публикация даёт **IIIF-манифест** + просмотрщик (#97/#162) с deep-zoom и подсветкой найденного по координатам.
- **AC-D6.** Мастер неизменяем (write-once); деривативы пересоздаваемы; вычитка OCR правит текст-слой, не мастер.

---

## 4. Controlled Digital Lending (CDL)

### 4.1 Назначение и принцип

CDL — временная выдача **э-копии** оцифрованного издания по модели «один физический экземпляр = одна одновременная цифровая выдача» ([PRODUCT_PRACTICES §«Цифровая сохранность»](../../PRODUCT_PRACTICES.md): controlled digital lending). Принцип **owned-to-loaned ratio**: число одновременных CDL-выдач ≤ числу принадлежащих библиотеке физических экземпляров (910), которые при этом **изъяты из физического оборота** на время цифровой выдачи. Это «цифровой экземпляр» поверх циркуляционной модели **I3**.

### 4.2 Модель (поверх loan I3 + права #97)

```
cdl_title                               -- что доступно по CDL
  id            uuid PK
  tenant_id     uuid NOT NULL           -- RLS
  record_id     bigint NOT NULL         -- библиозапись
  object_id     uuid NOT NULL REFERENCES digital_object  -- оцифрованная копия
  owned_count   int  NOT NULL           -- сколько физ.экз. (910) выделено под CDL
  loan_period   interval NOT NULL       -- срок выдачи (напр. 14 дней / 1 час «короткая»)
  max_concurrent int NOT NULL           -- = owned_count (инвариант owned-to-loaned)
  CHECK (max_concurrent <= owned_count)

cdl_loan                                -- активная цифровая выдача
  id            uuid PK
  tenant_id     uuid NOT NULL
  cdl_title     uuid NOT NULL REFERENCES cdl_title
  reader_id     uuid NOT NULL
  issued_at     timestamptz NOT NULL
  expires_at    timestamptz NOT NULL    -- issued_at + loan_period (DRM-таймер)
  returned_at   timestamptz NULL        -- ранний возврат
  status        enum                    -- active | expired | returned
  INDEX (tenant_id, cdl_title, status)  -- подсчёт активных < max_concurrent
```

### 4.3 Инвариант owned-to-loaned (ядро CDL)

При запросе выдачи: `count(active cdl_loan для title) < cdl_title.max_concurrent` ⇒ выдать; иначе → **очередь брони** (паритет I3, [SPEC_I3](../SPEC_I3_circulation_storage.md): «вы N-й»). Выданный CDL-экземпляр **резервирует** физический 910 (статус «изъят под CDL»), чтобы тот же экземпляр не выдали физически — соблюдение принципа «одна копия в обороте за раз». Возврат (ранний или по таймеру) освобождает слот → следующий из очереди.

### 4.4 DRM / таймер / view-only

- **Таймер:** `expires_at`; по истечении — доступ отзывается (фоновое задание + проверка на каждом запросе страницы). Ранний возврат читателем освобождает слот.
- **Доступ — через view-only прокси #97:** CDL **не отдаёт файл**, а рендерит постранично через бэкенд-прокси ([SPEC_reader §4](../SPEC_reader_jirbis.md): «бинарь не утекает»), с лимитом печати/копирования по `951^9`-флагам. CDL добавляет к правам #97 **временной entitlement** (действует только в окне loan).
- **Права:** проверка на каждой странице = #97-модель (951 `^D`/`^L`/`^9` + RIGHT IP/категория/период, **приоритет 951>955**) **И** активный `cdl_loan`. Нет активной выдачи → нет доступа, даже если файл существует.
- **Lightweight watermark** (читательский id/таймштамп на странице) — опция тенанта (анти-утечка).

### 4.5 Связь с RIGHT/LICH и циркуляцией

- **RIGHT** (955: IP/категория/специальность/периоды) — базовый гейт «кому вообще доступен ресурс» ([CAPABILITY_MAP §8/§11](../../../recon/deep/CAPABILITY_MAP.md)); CDL-loan — поверх: «доступен И сейчас выдан этому читателю».
- **LICH** (личные данные/закладки) — CDL-выдача в личном кабинете читателя (#97 ЛК), opt-in история (152-ФЗ B4).
- Возврат/истечение CDL → событие циркуляции (I3) + уведомление A6 («ваша цифровая выдача истекает завтра»).

### 4.6 AC — CDL

- **AC-C1.** Выдача CDL разрешена только если `active loans < max_concurrent` (= owned_count); иначе — очередь брони (паритет I3); выданный CDL резервирует физ.экз. 910.
- **AC-C2.** DRM-таймер: по `expires_at` доступ отзывается автоматически; ранний возврат освобождает слот для очереди.
- **AC-C3.** Доступ к копии — только через view-only прокси #97 (постранично, бинарь не утекает), с лимитом печати/копирования по `951^9`; нет активного `cdl_loan` → нет доступа.
- **AC-C4.** Права = #97 (951/RIGHT, приоритет 951>955) **И** активная выдача; RIGHT-гейт (IP/категория/период) соблюдён.
- **AC-C5.** Истечение/возврат CDL шлёт уведомление через A6; выдача видна в ЛК читателя (LICH/#97), история — opt-in (B4).

---

## 5. API / модель (контракт)

Базовые пути; аутентификация/тенант/RLS/гранты — платформенный middleware I1; все эндпоинты — в общем OpenAPI ([SPEC_I1 §контракты](../SPEC_I1_foundation.md), A7). Чувствительные операции (Phase 2 финансы, reindex DAM, политика CDL) — высокий грант (ws5/Администратор).

```
# Финансы
GET  /api/finance/budget-lines               -- строки бюджета (committed/spent из ws2)
POST /api/finance/accounting/import          -- импорт счетов/проводок (provider) [Phase 1]
GET  /api/finance/reconciliation?period=     -- отчёт сверки (наша Σ88 ↔ Парус)
POST /api/finance/obligation                 -- платёжная заявка из заказа [Phase 2, грант]

# ERM
GET/POST /api/erm/resources                  -- э-ресурсы
GET/POST /api/erm/licenses                    -- лицензии (тип/сроки/условия/budget_line)
GET      /api/erm/usage?resource=&period=     -- COUNTER usage_stat (cost-per-use)
POST     /api/erm/sushi/fetch                 -- забор SUSHI-отчёта (грант; токены в секретах)
GET      /api/erm/kb/resolve?id=              -- knowledge base / link-resolver (OpenURL)

# DAM / оцифровка
POST /api/dam/objects                        -- ingest (capture/upload) → digital_object + SHA256
GET  /api/dam/objects/{id}                    -- статус конвейера (стейт-машина)
POST /api/dam/objects/{id}/ocr                -- (пере)запустить OCR/HTR
GET  /api/dam/objects/{id}/manifest           -- IIIF Presentation manifest
GET  /api/dam/objects/{id}/search?q=          -- IIIF Content Search (по ALTO-координатам)
GET  /api/dam/fixity?id=                       -- статус проверки целостности

# CDL
GET  /api/cdl/titles                          -- доступные по CDL (owned/available)
POST /api/cdl/loans                           -- запросить выдачу (инвариант 4.3) → loan | queue
POST /api/cdl/loans/{id}/return               -- ранний возврат (освобождает слот)
GET  /api/cdl/page/{loan}/{n}                 -- постраничный рендер ЧЕРЕЗ прокси #97 (DRM-гейт)
```

### Сервисы (абстракции)

| Сервис | Назначение |
|---|---|
| `AccountingProvider` | абстракция бухгалтерии (Парус/1С/CSV), import/reconcile/[obligation] — раздел 1.3 |
| `ErmService` | лицензии/доступы/жизненный цикл + алерты (A6) — раздел 2 |
| `CounterSushiHarvester` | забор/нормализация COUNTER, cost-per-use, отдача в B1 — раздел 2.3 |
| `DigitizationOrchestrator` | стейт-машина конвейера, очередь, ресурс-лимиты, retry — раздел 3.2 |
| `FixityService` | SHA256 при приёме + периодическая проверка — раздел 3.3 |
| `OcrHtrService` | OCR/HTR → текст + ALTO/hOCR (поставщик для SPEC_rag) — раздел 3.4 |
| `IiifService` | манифесты + Image/Content Search API — раздел 3.5 |
| `CdlService` | owned-to-loaned инвариант, таймер, view-only через прокси #97 — раздел 4 |

> **Модель — конфиг, не код.** `AccountingProvider`/`OcrHtrService`/embedding (через SPEC_rag) инжектируются per-deployment; домен не зависит от конкретного Паруса/OCR-движка (паритет абстракций SPEC_rag/SPEC_compliance_152fz).

---

## 6. Критический путь

1. **DAM-ядро** (раздел 3): `digital_object` + ingest/fixity (SHA256) + object storage + стейт-машина/очередь → capture работает, объекты целостны. *Предусловие CDL и связи 950/951/955.*
2. **OCR/HTR → ALTO/hOCR** (3.4) → текст+координаты отдаются поиску (#122/SPEC_rag) и Content Search → полнотекст оцифрованного ищется и подсвечивается.
3. **IIIF** (3.5): манифест + просмотрщик (#97/#162) → deep-zoom + подсветка; «замена сканирующего продукта» достигнута.
4. **ERM** (раздел 2): лицензии/доступы + SUSHI/COUNTER → cost-per-use + алерты (A6) + B1; параллельно DAM.
5. **Финансы Phase 1** (раздел 1): адаптер `AccountingProvider` + `budget_line` + сверка read-only поверх ws2.
6. **CDL** (раздел 4): owned-to-loaned + таймер + view-only через прокси #97 + очередь (I3). *Зависит от 1–3 (нужна оцифрованная копия) и #97 (прокси/права).*
7. **Финансы Phase 2** (write в Парус) + платный модуль оцифровки/ERM (I7) — по мере фаз.

**Зависимости:** I1 (RLS/тенант/гранты/OpenAPI/object storage); **ws2** (суммы 62/88, КСУ — финансы поверх них); **#97** ([SPEC_reader §4](../SPEC_reader_jirbis.md): view-only прокси, 951/RIGHT, приоритет 951>955 — фундамент CDL/доступа); **SPEC_rag** (потребитель OCR-текста/координат; авто-каталог черновика); **#122** (индексация полнотекста); **A2** ФЛК (черновик метаданных); **A4** авторитеты; **A6** уведомления (истечение лицензии/возврат CDL/готовность оцифровки); **I3** циркуляция (loan-модель для CDL); **I4** edge (TWAIN-capture офлайн); **B1** гос-статистика (COUNTER); **D5** биллинг (метеринг хранилища/OCR/трафика); **B4** 152-ФЗ (opt-in история CDL).

**Выходной критерий D6:** комплектатор сверяет суммы с Парусом (read-only Phase 1) и распределяет бюджет по фондам поверх ws2; ERM ведёт лицензии/доступы с COUNTER/SUSHI-учётом (cost-per-use, алерты, отдача в B1); конвейер оцифровки превращает скан в **целостный (SHA256) объект → OCR/ALTO → индекс → IIIF-просмотр с подсветкой**, заменяя отдельный сканирующий продукт; CDL выдаёт э-копии по owned-to-loaned-инварианту с DRM-таймером через view-only прокси #97 — четыре «отложенных» блока доведены от «названо» до контракта/модели/AC.

---

## 7. Тест-матрица

> **Главные оси: сверка-финансов · COUNTER-учёт · fixity/OCR-координаты · owned-to-loaned/DRM.**

| # | Сценарий | Ось | Тип | Ожидание |
|---|---|---|---|---|
| T-F1 | Импорт счетов Паруса + связь 88^J→budget_line | finance | integration | строка бюджета наполнена, КСУ связана (AC-F1) |
| T-F2 | Сверка Σ88^G ↔ проведено в Парусе | finance | integration | отчёт расхождений, **ничего не пишем в бухгалтерию** (AC-F3) |
| T-F3 | Смена провайдера Парус→CSV | finance | unit | домен не тронут, csv-manual работает (AC-F4) |
| T-F4 | Phase 2 obligation без гранта | finance | security | отказ (AC-F5) |
| T-E1 | SUSHI-забор COUNTER TR_J1 → usage_stat + cost-per-use | erm | integration | нормализовано, cost/use посчитан (AC-E2) |
| T-E2 | Лицензия за N дней до end_date | erm | integration | алерт через A6, статус expiring (AC-E3) |
| T-E3 | Expired-ресурс в OPAC | erm | integration | помечен недоступным; KB не ведёт (AC-E3/E4) |
| T-E4 | SUSHI-токен в открытом config | erm | security | запрещено, токен в секретах (AC-E5) |
| T-D1 | Ingest скана → SHA256 | dam | integration | checksum записан; повреждённый детектируется fixity (AC-D1) |
| T-D2 | Падение OCR-задачи | dam | integration | retry/backoff, объект не потерян, →failed→retry (AC-D2) |
| T-D3 | Ресурс-лимит per-tenant превышен | dam/cost | integration | задача ждёт в очереди, не падает; метеринг→D5 (AC-D2) |
| T-D4 | OCR → ALTO-координаты → Content Search | dam | integration | подсветка слова на странице по координатам (AC-D3/D5) |
| T-D5 | Связь объекта 950/951/955 + авто-каталог | dam | integration | привязка к записи; черновик через ФЛК import (AC-D4) |
| T-D6 | Правка мастера | dam | security | запрещена (write-once); вычитка правит текст-слой (AC-D6) |
| T-D7 | IIIF-манифест + deep-zoom | dam | integration | просмотрщик открывает, тайлы из storage (AC-D5) |
| T-C1 | CDL-выдача при active == owned_count | cdl | integration | очередь, не выдача; инвариант держится (AC-C1) |
| T-C2 | Истечение DRM-таймера | cdl | integration | доступ отозван автоматически (AC-C2) |
| T-C3 | Запрос страницы без активного loan | cdl | security | доступа нет, даже если файл есть (AC-C3) |
| T-C4 | Скачать бинарь напрямую (минуя прокси) | cdl | security | невозможно, только постраничный рендер (AC-C3) |
| T-C5 | RIGHT-гейт (чужой IP/категория) + 951>955 | cdl | security | отказ по правам, приоритет 951 (AC-C4) |
| T-C6 | Ранний возврат CDL | cdl | integration | слот освобождён, следующий из очереди (AC-C1/C2) |

---

## 8. Риски и открытые вопросы

| # | Риск | Митигация |
|---|---|---|
| R1 | Транспорт/формат обмена с Парусом не формализован в recon | абстракция `AccountingProvider` + `csv-manual` деградация (Phase 1 read-only не зависит от API Паруса); транспорт уточняется на боевом контуре (Q-FIN-1) |
| R2 | Write в чужую ERP (Phase 2) — финансовый риск/ответственность | Phase 2 опционален, gated за грантом+аудитом; Phase 1 (сверка) самодостаточна для паритета |
| R3 | SUSHI-API провайдеров нестабильны/разнятся (версии COUNTER 5 vs 5.1) | нормализация в единую `usage_stat`; `manual_upload` fallback; токены в секрет-хранилище |
| R4 | OCR-качество на рукописях/старом шрифте низкое → мусор в поиске | per-page confidence + HITL-вычитка (правит текст-слой, не мастер); HTR для рукописей; флаг needs_review |
| R5 | Стоимость OCR/derive/хранилища на масштабе (cost-DoS) | ресурс-лимиты per-tenant + очередь (не падение); метеринг→D5; деривативы пересоздаваемы, мастер write-once |
| R6 | CDL — правовая серость в РФ (нет прямого аналога US CDL) | строгий owned-to-loaned инвариант (изъятие физ.910) + view-only прокси (бинарь не утекает) + watermark; **правовая допустимость per-tenant/per-издание — политика, не код** (Q-CDL-1) |
| R7 | Утечка оцифрованного контента (обход прокси/таймера) | всё через бэкенд-прокси #97 (бинарь не отдаётся); DRM-таймер на каждом запросе страницы; RIGHT-гейт; watermark |
| R8 | Рассинхрон fixity (битрот в object storage) | периодическая проверка SHA256 + алерт; мастер write-once; деривативы восстановимы |

**Открытые вопросы:**
- **Q-FIN-1.** Реальный транспорт/формат обмена ИРБИС-Парус (файловый/XML/REST) и семантика `88^J/^I` на боевом контуре тенанта — определяет реализацию `AccountingProvider` для Паруса (для пилота достаточно `csv-manual`). Связь с recon TODO ws2 (#CMPL-06 экономика цен).
- **Q-CDL-1.** Правовая модель CDL в РФ: какие издания допустимы к контролируемой цифровой выдаче (срок охраны / договор с правообладателем / собственная оцифровка), и как owned-to-loaned ratio соотносится с лицензионным правом — это **юридическая политика тенанта/издания**, конфигурируется, не зашивается; нужен чек-лист допустимости (связь B4/I6).
- **Q-DAM-1.** Выбор OCR/HTR-движка и IIIF-просмотрщика для гос-контура (self-hosted, без внешнего egress — паритет [SPEC_rag Q2](../diff/SPEC_rag.md)): Tesseract/EasyOCR/коммерческий vs качество на рус./нац. языках и рукописях; Mirador/UV vs свой на DS. Влияет на 3.4/3.5 и cost (D5).

---

> Файл: `docs/design/specs/platform/SPEC_finance_erm_dam.md`. Закрывает D6 (#188), родители I5/I7. Грунтовка: SPEC_ws2 §9/§4 (финансы/Парус 88^J/^I, КСУ), CAPABILITY_MAP §11/§8 (951/950/955, RIGHT/LICH, FullText/PDF), PRODUCT_PRACTICES (ERM/COUNTER, IIIF, OAIS/fixity, CDL, конвейер оцифровки), SPEC_reader §4 / #97 (view-only прокси, 951>955), SPEC_rag §1.4/§6 (OCR→чанки/Content Search; потребитель ALTO-координат). Связи: I1 (RLS/гранты/storage), ws2 (суммы/КСУ), #97 (прокси/права — фундамент CDL), #122/SPEC_rag (индексация/RAG), A2/A4 (ФЛК/авторитеты черновика), A6 (уведомления), I3 (loan для CDL), I4 (edge-capture), B1 (COUNTER в гос-статистику), D5 (метеринг), B4 (opt-in история). Абстракции `AccountingProvider`/`OcrHtrService` провайдер-агностичны.
