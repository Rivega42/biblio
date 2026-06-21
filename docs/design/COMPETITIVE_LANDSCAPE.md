# Конкурентная карта (внешний ресерч)

> Профили конкурентов и аналогов по 5 сегментам (с источниками) + сводные выводы и пробелы. Матрица «мы vs конкуренты» — [`COMPETITIVE_MATRIX.md`](COMPETITIVE_MATRIX.md). Наш продукт — [ARCHITECTURE](ARCHITECTURE.md), [PRODUCT_PRACTICES](PRODUCT_PRACTICES.md), [ROADMAP](ROADMAP.md). Данные — веб-ресерч (point-in-time; цифры инсталляций ориентировочны).

## 1. РФ/СНГ АБИС — прямые конкуренты
- **ИРБИС64/128** (ЭБНИТ/ГПНТБ) — отраслевой стандарт, тысячи инсталляций; **legacy desktop-АРМы** + Web-ИРБИС/J-ИРБИС; проприетарная ISIS-СУБД (не PostgreSQL); «облако» = VPS-хостинг, не SaaS; есть RUSMARC/MARC21, Z39.50, RFID, СК-ЕСИА. Реестр отеч.ПО — да. **Это система, которую замещаем.**
- **МАРК Cloud / МАРК-SQL** (НПО Информсистема) — **самый масштабный облачный конкурент**: единая АБИС всех ЦБС Москвы (~440 библиотек), Н.Новгород, школы Чувашии; **облачный SaaS** в ДЦ провайдера, браузер; PostgreSQL/др.; Astra Linux. Реестр — да. **Главная угроза по «облачности» + гос-референс.**
- **Руслан-Нео** (Открытые библиотечные системы, СПб) — **ближе всех архитектурно**: SOA, веб, облако, multi-tenant, кросс-платформа; SIP2, RUSMARC, Solr; БД Oracle/MySQL/PostgreSQL. Z39.50/OAI/AI/мобайл — не заявлены. Реестр — да.
- **МегаПро** (Дата Экспресс) — **near-peer**: веб все модули, on-prem + SaaS «Библиохостинг», **уже заявлены МегаПро.AI + МегаПро.API (API-first) + .Auth (авторитеты)**; 10 модулей (ЭБ, каталогизация, комплектование, подписка, книговыдача, книгообеспеченность, ВКР, хранение). Реестр, Astra. **Самый «современный» из РФ по фичам.**
- **OPAC-Global** (ДИТ-М/Дата Экспресс) — полностью веб, централизованный сервер, опыт мультибиблиотечных сводов (напр. Тверь); UI устаревший; не self-serve SaaS.
- **1С:Библиотека** — на платформе 1С; школы/вузы; сила — экосистема 1С и франчайзи; библиотечная глубина слабее; не библиотечный SaaS.
- **Absotheque/Веб-Либэр** (ЛИБЭР) — веб, каталогизация/авторитеты/RFID; **вытеснена МАРК Cloud из Москвы (с 2018)**.
- **Нижний/школьный сегмент:** Либра-онлайн (BiblioSoft, **freemium-облако**), Библио#21 (ГИВЦ Минкультуры), АБИС НЕВА (BalticSoft) — широкий охват, малая глубина, ценовое давление.
- **Иностранные в РФ:** Alma/Aleph (РГБ) — после 2022 уход вендора/санкции → **окно импортозамещения** (но и для МАРК Cloud/Руслан-Нео).

## 2. Международные коммерческие LSP/ILS — эталоны
- **Ex Libris Alma + Primo** (Clarivate) — лидер, **чистый multi-tenant SaaS**; единый workflow печать+электроника+цифра; **трёхзонная модель консорциумов (Community/Network/Institution)**; REST API + **webhooks + Cloud Apps**; **BIBFRAME**/LOD; Primo **CDI** (5 млрд+) + **Research Assistant (генеративный RAG-поиск со ссылками)**; WCAG 2.2 AA + VPAT. Минус — lock-in Alma↔Primo.
- **OCLC WMS + WorldCat Discovery** — глобальный SaaS поверх **WorldCat (610 млн+ записей)**: библиотеки **разделяют записи** (кооперативная каталогизация, сетевой эффект); **WorldCat Entities/FAST/Dewey как LOD** (150 млн+ сущностей, устойчивые URI); ILL/Tipasa.
- **SirsiDynix** (Symphony/Horizon + **BLUEcloud** SaaS-слой) — «модернизация без миграции» поверх legacy; MobileCirc, discovery Enterprise + Portfolio(DAM), BookMyne. Критика — медленная доставка.
- **Innovative** (Clarivate): **Polaris** (Leap — браузерный staff, REST/Swagger), **Sierra** (PostgreSQL + **SierraDNA — прямой read-only SQL к БД для отчётности**), **Vega** (multi-tenant SaaS, **MARC→BIBFRAME entity-based discovery**, кураторские **Showcases**; экосистема Vega LX: Program/события, Promote/маркетинг, WebBuilder/CMS-сайт, **Vega Mobile** — цифровой билет + self-checkout + push).
- **Aleph** — legacy ILS, клиентов мигрируют в Alma (урок миграции).
- **TIND** (на open-source **Invenio**, спин-офф CERN) — hosted SaaS; ILS + DA(DAM, плотно IIIF) + IR + RDM; Python/Flask + OpenSearch + PostgreSQL; клиенты Caltech/ООН.

## 3. Open-source ILS/LSP + discovery
- **FOLIO** (EBSCO/Index Data) — **эталон app-платформы**: микросервисы, multi-tenant, **API-first (OpenAPI до кода)**, Kafka-шина, PostgreSQL; новый стек **Eureka = Keycloak + Kong + sidecars**; apps как контракт (Inventory/Circulation/Acquisitions/**ERM**/Courses/Authority), per-tenant включение через **Entitlement Manager**. **Прямо валидирует нашу архитектуру.**
- **Koha** — зрелый монолит (Perl/MariaDB); богатые протоколы (Z39.50/SRU/SIP2/ILS-DI/NCIP/OAI); **KPZ-плагины** (zip ставится через UI, добавляет REST-маршруты) — модель для нашего маркетплейса.
- **Evergreen** — **изначально консорциальный**: иерархия org-units, union-каталог, межбибл. resource sharing (NC Cardinal — 216 библиотек). **Источник идеи консорциального слоя.**
- **VuFind / Blacklight** — discovery: кастомизация **без форка ядра** (custom module + theme inheritance / Rails engine-as-gem) — паттерн tenant-override. Blacklight → экосистема Samvera (репозитории).

## 4. Цифровая библиотека / DAM / репозитории / оцифровка
- **DSpace** — репозиторий №1 (публикации), REST/OAI/RDF, OAIS-fixity; слабее по масс-оцифровке изображений/IIIF/OCR-конвейеру.
- **Islandora** (Drupal+Fedora6/OCFL+IIIF), **Samvera/Hyrax + Hyku** (multi-tenant DAM, Valkyrie→PostgreSQL/Fedora, IIIF/Mirador) — **Hyku = эталон multi-tenant DAM**.
- **Omeka S** — лёгкий, LOD в ядре; не preservation.
- **CONTENTdm** (OCLC SaaS) — OCR через ABBYY, IIIF; требует desktop Project Client (нет облачного capture), часто не хранит мастера.
- **Veridian** — газеты: **METS/ALTO, координаты слов, article segmentation**, поиск с подсветкой.
- **Goobi** (intranda) — **эталон workflow масс-оцифровки** (шаблоны процессов, ~210 плагинов, QA, OCR ABBYY/Tesseract, экспорт METS/MARC/…).
- **Preservica** — **активная сохранность** (OAIS v3, format-watch, авто-нормализация).
- **IIIF-стек:** Mirador/Universal Viewer, Cantaloupe; **Content Search API** (подсветка по координатам). **OCR/HTR:** Tesseract (ALTO/hOCR), ABBYY, **Transkribus (HTR рукописей)**. Стандарты качества **FADGI**, хранилище **OCFL-на-S3**.

## 5. Вовлечение, discovery-UX, e-lending, инновации 2024–2025
- **BiblioCommons (BiblioCore)** — community discovery: FRBR, фасеты, **shared social graph отзывов/списков между всеми библиотеками-клиентами**; **Browse & Discover** (2024) — кастом-домашняя в духе стриминга; AI-summaries; сильная accessibility.
- **OverDrive/Libby** — лидер e-lending (739 млн выдач 2024); брендинг, Tags, умные holds; **Inspire Me (2025) — LLM-рекомендации через структурированные «инспирации», «сначала доступное», объяснение «почему», privacy-by-design (no free-text), ответ обязан ссылаться на каталог (anti-hallucination)**.
- **Goodreads / StoryGraph** — соц-чтение; StoryGraph выигрывает **ML-рекомендациями по mood/theme/pace + content warnings + reading stats + buddy reads**.
- **Смарт-локеры** (Bibliotheca remoteLocker+, Lyngsoe, D-Tech, Tech Logic) — **24/7 выдача брони, авто-checkout, outdoor IP54** — прямой аналог наших постаматов.
- **RFID self-service** (Bibliotheca selfCheck) + **рекомендации NoveList прямо на киоске** (cross-sell в момент выдачи); people-counting.
- **NoveList** — эталон **appeal-факторов** (tone/pace/style/characterization); **Beanstack** — геймификация (badges/streaks/**community progress-bar**, +46% минут).
- **Тренды 2024–25:** 67% библиотек внедряют AI; **RAG-чат-боты справки**; **AI-каталогизация (Alma AI Metadata Assistant, LoC PCC)**; **NISO 2025** — генеративный AI меняет discovery; accessibility-AI + DAISY; ALA-гайды по AI-политикам/приватности.

## Сводные выводы
**Где выигрываем (уникально или почти):** edge/офлайн-синхронизация · ячейки+постаматы 24/7 · per-tenant маркетплейс модулей · accessibility-first (WCAG 2.2/ГОСТ) · OpenAPI-контракт + IIIF/DAM-ядро · AI-глубина. Из РФ — никто не закрывает этот набор.
**Паритет (must-have, иначе не перейдут):** RUSMARC/MARC21, Z39.50/OAI/SIP2 (+**NCIP/ILS-DI/SRU**), ЕСИА, реестр+Astra, **интеграция СКБР/ЛИБНЕТ/НЭБ + корпоративная сводная каталогизация**, миграция из ИРБИС/МАРК (импорт ISIS/MARC).
**Главные угрозы:** МАРК Cloud (масштаб/гос-референс), Руслан-Нео (архитектура), МегаПро (AI+API). Отрыв строим на edge/постаматах/маркетплейсе/AI-глубине/accessibility, не только на «облачности».

## Пробелы → бэклог (что добрали из ресерча)
| Пробел (источник) | Куда |
|---|---|
| Консорциумы: трёхзонная модель + union-каталог + межтенантный шеринг holds (Evergreen/Alma/РФ-ЦБС) | эпик **CN** → I4 |
| СКБР/ЛИБНЕТ/НЭБ + кооперативная общая каталогизация | CN (cn4) |
| NCIP / ILS-DI / SRU протоколы | CN (cn5) |
| ERM/лицензии/COUNTER + периодика + курсовые резервы (FOLIO/Alma) | эпик **ER** → I5 |
| RAG-ассистент с цитированием + anti-hallucination + inspiration-промпты + «сначала доступное» (Primo/Libby) | PMF (#148) |
| Appeal/mood/pace/content-warnings таксономия как фасеты (StoryGraph/NoveList) | PMA (#143) |
| Entity-based BIBFRAME discovery + entity-URI + авторитеты как LOD (Vega/OCLC) | PME (#147) |
| Кросс-тенантный федеративный соц-граф (BiblioCore) | PMB (#144) |
| Кураторские Showcases + browse-домашняя | PMA (#143) |
| Платформа вовлечения: события + маркетинг + CMS-сайт/SEO (Vega LX) | PMB (#144) |
| Аналитика: прямой SQL к реплике (SierraDNA) + кросс-тенант бенчмарк | PMF (#148) |
| Маркетплейс: webhooks + встроенные мини-приложения + module-descriptors/подпись (Alma/FOLIO/Koha) | PMF (#148) |
| Мобильное приложение: цифровой билет + self-checkout + push (Vega/Libby) | PMB (#144) |
| DAM: web-capture (WebTWAIN/edge), OCFL-на-S3, активная сохранность, IIIF Content Search, Transkribus HTR, Goobi-workflow | DG (#161) |
| WCAG 2.2 AA + VPAT/ACR (European Accessibility Act) | I6 |

## Источники (выборка)
ИРБИС/реестр: elnit.org, irbis128.ru, reestr.digital.gov.ru · МАРК: informsystema.ru · Руслан-Нео: obs.ruslan.ru · МегаПро: data-express.ru · OPAC-Global: opac-global.ru, ditm.ru · 1С: solutions.1c.ru · ЛИБЭР: libermedia.ru · СКБР/ЛИБНЕТ/НЭБ: nilc.ru, skbr21.ru, rusneb.ru · Alma/Primo: exlibrisgroup.com, developers.exlibrisgroup.com, clarivate.com · OCLC: oclc.org, fast.oclc.org · SirsiDynix: sirsidynix.com · Innovative: iii.com · TIND: tind.io · FOLIO: folio.org, dev.folio.org · Koha: koha-community.org · Evergreen: equinoxoli.org · VuFind/Blacklight: vufind.org, samvera · DSpace/Islandora/Samvera/Omeka/CONTENTdm/Veridian/Goobi/Preservica: lyrasis, islandora.github.io, samvera, omeka.org, oclc.org, veridiansoftware.com, intranda.com, preservica.com · IIIF/OCR: iiif.io, tesseractocr.org, transkribus.org, digitizationguidelines.gov (FADGI) · Вовлечение: bibliocommons.com, overdrive.com, libbyapp.com, storygraph, bibliotheca.com, lyngsoesystems.com, beanstack.com, libraryjournal.com, librarytechnology.org (Breeding).
