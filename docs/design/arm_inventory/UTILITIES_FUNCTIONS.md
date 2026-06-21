# Инвентаризация функций — серверные УТИЛИТЫ ИРБИС64 vs наше покрытие

> **Назначение.** Исчерпывающий реестр (строка на каждую дискретную функцию) **standalone-утилит** САБ ИРБИС64+ — отдельных `.exe`-инструментов, лежащих в `C:\IRBIS64` рядом с пятью АРМами, но **не являющихся** ни одним из них (это «последнее белое пятно» карты ИРБИС). Сюда входят компиляторы ресурсов (форматы/таблицы/деревья), пакетные обработчики (глобальная корректировка, мультизагрузка), редактор MARC, полнотекстовая подсистема (PDF→текст), инструменты пресетов конфигурации, серверное ядро и хост-хелперы. Перечислены ВСЕ найденные на живой инсталляции бинарники, ничего не «просемплировано».
>
> **Ground truth (прочитано дословно):**
> - **Живой реестр бинарников** — `recon/deep/inventory.csv` (21 `.exe` + конфиги `GenPFT64.ini`, `ISO2709Editor.INI`, `xpdfrc`; все `.exe` помечены `skipped — not decompiled (rule 6)`, поэтому функция выводится из конфигов + ARM/recon-описаний, а не из дизассемблера).
> - **Сырые конфиги утилит** на диске `C:\IRBIS64`: `GenPFT64.ini` (`[MAIN] PftMnu/WSFDT/ACTABPATH`), `ISO2709Editor.INI` (полное меню: «карман», импорт XLS/MDB/DBF→ISO2709, таблица соответствия столбцов↔меток), `xpdfrc` (конфиг Foolabs Xpdf — это и есть `pdftotext`), `irbis_server.ini` `[FullText]` (цепочка `ExtractPDFPageMode`/`ExtractPDFTXTMode`/`CheckPDF_with_Quickdll`/`ftcachebuilder`).
> - [CAPABILITY_MAP §1](../../recon/deep/CAPABILITY_MAP.md) (перечень утилит: `IrbisGblAdmin`, `IrbisExtractFullText`+`pdftotext`, `ftcachebuilder`, `IrbisMultiLoad`, штрих/QR), §6/§11 (форматы, ISO2709/MARC двусторонняя конверсия, табличные формы), §8 (полнотекст, БД RIGHT/LICH/ZAPR).
> - [PFT_LANGUAGE §1/§14](../../recon/deep/reference/format/PFT_LANGUAGE.md) (`GENPFT64.EXE` — редактор форматов, вызывается из АРМ Администратор, показывает размер формата и **время выполнения в мс**; `<IMG SRC="IRBIS:!!ШТРИХ_КОД!!">`), [PFT_MODULES §3](../../recon/deep/reference/format/PFT_MODULES.md) (табличные формы `.tab/.pft/.tbg/.srw/.hdr`, `IC_print`).
> - [GLOBAL_CORRECTION §1–4](../../recon/deep/reference/format/GLOBAL_CORRECTION.md) (язык `.gbl`, 22 оператора, `IC_gbl(...)`, 124 файла `.gbl`, режим в Каталогизаторе и серверном Администраторе).
> - [FIELD_DICTIONARY](../../recon/deep/reference/format/FIELD_DICTIONARY.md) (FST/инверсия, `.TRE`-деревья), [FINDINGS_04 §архитектура/§FullText/§установка](../../recon/deep/FINDINGS_04_server_admin.md) (ядро `irbis_server.exe` + воркеры `server_64.exe` + сервис `service_64.exe`, `[FullText]`, лог, `service_64.exe /INSTALL`).
> - [PROTOCOL_REFERENCE §3](../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md), [WIRE_PROTOCOL](../../recon/deep/reference/protocol/WIRE_PROTOCOL.md) (команды, которые утилиты гонят по проводу: `IC_gbl`, `IC_print`, `IC_updategroup*`, регистрация/чтение/запись).
>
> **Наше покрытие (сверено):** движки [SPEC_engine_pft](../specs/engines/SPEC_engine_pft.md) (A1), [SPEC_engine_gbl](../specs/engines/SPEC_engine_gbl.md) (A3), [SPEC_engine_flk](../specs/engines/SPEC_engine_flk.md), [SPEC_service_authority](../specs/engines/SPEC_service_authority.md) (A4), [SPEC_seeding](../specs/engines/SPEC_seeding.md) (A5); гос [SPEC_protocols](../specs/gov/SPEC_protocols.md) (B2 Z39.50/MARC/ISO2709), [SPEC_gov_exchange](../specs/gov/SPEC_gov_exchange.md) (НЭБ/СКБР/ЛИБНЕТ), [SPEC_gov_statistics](../specs/gov/SPEC_gov_statistics.md); платформа [SPEC_finance_erm_dam](../specs/platform/SPEC_finance_erm_dam.md) (DAM/полнотекст), [SPEC_lowcode](../specs/platform/SPEC_lowcode.md), [SPEC_iac_fleet](../specs/platform/SPEC_iac_fleet.md), [SPEC_sre](../specs/platform/SPEC_sre.md); [SPEC_ws5_admin](../specs/SPEC_ws5_admin.md), [SPEC_ws1_cataloger](../specs/SPEC_ws1_cataloger.md), [SPEC_I1_foundation](../specs/SPEC_I1_foundation.md), [INTEGRATION_MAP](../INTEGRATION_MAP.md).
>
> **Особенность утилит.** В отличие от АРМов (диалоговые рабочие места), эти инструменты — **компиляторы/конвертеры/пакетники ресурсов и данных ИРБИС** (PFT→исполняемый формат, `.gbl`→массовая правка, XLS→ISO2709, PDF→текст-индекс), плюс **серверное ядро** и хост-хелперы. Многие из них в веб-on-PostgreSQL архитектуре **растворяются в движках/сервисах** (их функция становится частью A1/A3/A4/B2/DAM), а часть — это **легаси-артефакты файловой реализации** (ILF-инверсия, межпроцессный обмен), которые сознательно отбрасываются (⚫).
>
> **Легенда статуса.** ✅ покрыто спекой с AC · 🟡 частично (названо в спеке, нет полной схемы/контракта) · ❌ не покрыто (реальный пробел на построение) · ⚫ DROP (легаси/неприменимо в веб-on-PostgreSQL — обосновано в примечании).

---

## 1. Компиляторы/редакторы ресурсов БД (форматы, таблицы, деревья)

> Эти утилиты компилируют/редактируют **параметрические ресурсы** ИРБИС, которые в нашей архитектуре становятся артефактами движков A1 (PFT/печать) и A4/A5 (классификаторы/seeding). У них есть и встроенные редакторы в АРМ Администратор (`Tool*Item`), но как **standalone-`.exe`** они вынесены для пакетной/массовой работы.

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 1 | **`GenPFT64.exe`** — компилятор/редактор форматов PFT | Редактирует и **компилирует/прогоняет** формат `.pft`; показывает размер формата и **время выполнения в мс** ([PFT_LANGUAGE §1](../../recon/deep/reference/format/PFT_LANGUAGE.md)). Конфиг `GenPFT64.ini`: `PftMnu=PFTw.MNU`, `WSFDT`, `ACTABPATH=.\isisacw` (таблицы actab). Сердце показа/печати всех АРМов. | engine **A1** [SPEC_engine_pft §1–6](../specs/engines/SPEC_engine_pft.md) (AC1–AC16: интерпретатор PFT-AST → IR → HTML/PDF/RTF/DOCX; DoD-гейт прямо требует **«время рендера в мс — паритет `genpft64`»**) | ✅ | Прямой и полный аналог. Мы **не переиспользуем** `genpft64.exe`/`irbis64.dll` — реимплементируем как сервис `format`. |
| 2 | **`tabgen.exe`** — генератор табличных форм | Собирает **табличные/печатные формы** из набора `.tab` (RTF-рамка) + `.pft` (тело строки) + `.tbg` (декларативное опредление) + `.srw` (ключ сортировки) + `.hdr` ([PFT_MODULES §3](../../recon/deep/reference/format/PFT_MODULES.md)); протокол `IC_print(...)`. Инвентарные/статистические/КСУ-списки → RTF. | engine **A1** [SPEC_engine_pft §3.3, §5, AC14](../specs/engines/SPEC_engine_pft.md) (табличный движок: `.tbg`→HTML/PDF/XLSX, `.tab`-fallback, агрегаты считаются в PostgreSQL, сущность `table_form`) | ✅ | Покрыт внутри A1 как «табличный движок»; развязан от print-бэкенда через IR. |
| 3 | **`GENTREE.EXE`** — генератор справочников-деревьев `.TRE` | Строит/пересобирает иерархические **`.TRE`-деревья** (шаблон-форматы `PFT.TRE`, классификаторы-навигаторы) из плоских источников ([PFT_LANGUAGE §9.2](../../recon/deep/reference/format/PFT_LANGUAGE.md), [FIELD_DICTIONARY](../../recon/deep/reference/format/FIELD_DICTIONARY.md)). | engine **A4/A5** [SPEC_service_authority §6](../specs/engines/SPEC_service_authority.md) (`classification_node` + closure-table, ленивое раскрытие, авто-подстановка индекса 964/675/621; AC-C1…C5) + [SPEC_seeding §1–2](../specs/engines/SPEC_seeding.md) (системные деревья ГРНТИ/УДК/ББК как seed) | ✅ | Генерация дерева ≈ построение `classification_node` из seed/импорта; closure-table для эффективной реклассификации. |

---

## 2. Пакетные обработчики данных (корректировка, загрузка, MARC-обмен)

> «Тяжёлые» инструменты массовых операций над записями: глобальная правка по скрипту, мультизагрузка, редактор/конвертер MARC ISO2709.

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 4 | **`IrbisGblAdmin.exe`** — серверный раннер глобальной корректировки | Прогоняет задания **`.gbl`** (22 оператора: `ADD/REP/CHA/CHAC/DEL/DELR/CORREC/NEWMFN/IF…FI/REPEAT…UNTIL`) над выборкой/всей БД; серверная функция `IC_gbl(Adbn,Aifupdate,Agbl,Asexp;Amin,Amax;...)`; режим «без предварительной отметки» (`GLOBTOTALMAIN`); 124 файла `.gbl` в комплекте ([GLOBAL_CORRECTION §1–4](../../recon/deep/reference/format/GLOBAL_CORRECTION.md)). | engine **A3** [SPEC_engine_gbl §1–5, AC1–AC10](../specs/engines/SPEC_engine_gbl.md) (парсер+AST всех 22 операторов; выбор записей; **preview-diff vs apply**; журнал для undo/rollback §4.5; кросс-БД изоляция) | ✅ | Прямой и полный аналог A3. У нас сверх ИРБИС — **обязательный preview-diff и журналируемый rollback**. |
| 5 | **`IrbisMultiLoad.exe`** — массовая загрузка записей | Пакетная загрузка/паковка записей из файлов (ISO2709/MARC/текст ИРБИС), сценарии импорта Z39.50/ЛИБНЕТ/MARC-файлы ([CAPABILITY_MAP §1/§9](../../recon/deep/CAPABILITY_MAP.md)); по проводу — `IC_updategroup`/`IC_updategroup_sinhronize` ([PROTOCOL_REFERENCE §3.2](../../recon/deep/reference/protocol/PROTOCOL_REFERENCE.md)). | [SPEC_gov_exchange §1–4](../specs/gov/SPEC_gov_exchange.md) (импорт НЭБ/СКБР/ЛИБНЕТ: MARC→маппинг FST/GBL→ФЛК `!998`); [SPEC_ws5_admin §6](../specs/SPEC_ws5_admin.md) (пакетный импорт/экспорт с отчётом); [SPEC_seeding §6](../specs/engines/SPEC_seeding.md) (bulk seed) | 🟡 | Конвейер импорта спроектирован, но **детальный field-by-field маппинг и сам пакетный «загрузчик с отчётом об ошибках построчно»** не материализован (recon TODO #GOV-01). Усиление в ws5 §6 / gov_exchange. |
| 6 | **`ISO2709Editor.exe`** — редактор/конвертер MARC ISO2709 | Полноценный **standalone-редактор ISO2709**: модель «карман» (отбор записей в карман, навигация, удаление поля, поиск), сохранение кармана в ISO-файл; **импорт XLS/MDB/DBF→ISO2709 по таблице соответствия «столбец↔метка»** (`ISO2709Editor.INI`: пункты `преобразоватьXLS-карманISO2709`, `установитьСвязь`, ODBC). Инструмент онбординга/миграции данных. | [SPEC_protocols §1–2](../specs/gov/SPEC_protocols.md) (Z39.50/SRU: Present рендерит ISO2709/USMARC/UNIMARC/MARCXML; импорт-маппинг FST/GBL); [SPEC_ws1_cataloger §5](../specs/SPEC_ws1_cataloger.md) (MARC↔запись, ФЛК `!998` на импорт) | 🟡 | **Транспорт** ISO2709/MARC покрыт (B2), но **табличный конвертер «Excel/DBF→MARC по карте столбцов» и ручной hex-уровневый редактор ISO-записи** как отдельная функция не специфицированы. Кандидат на маленький импорт-мастер в ws1 low-code (см. ❌-уточнение ниже). |

---

## 3. Полнотекстовая подсистема ПБД (PDF→текст, кэш, проверка)

> Четыре кооперирующихся инструмента, управляемые секцией `[FullText]` в `irbis_server.ini`. Извлекают текст из PDF/документов для индексации ПБД (полнотекстовая БД, поля 951/955), строят и проверяют кэш. В нашей архитектуре — единый модуль DAM/полнотекст.

> Подтверждённая цепочка из живого `irbis_server.ini [FullText]`: `ExtractPDFPageMode=4` (`1 pdfsplitmerge / 2 QuickPDF / 3 checkpdf.exe+pdfsplitmerge / 4 QPDF.exe fast / 5 QPDF.exe`), `ExtractPDFTXTMode=0` (`0 PDF2TEXT.EXE / 1 QUICKPDF.DLL`), `CheckPDF_with_Quickdll=1`, `ftcachebuilder=1`, `FULLTEXTACTUAL=1`, `PDFExtractTime=30`, `PDFPageNumber=10`.

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 7 | **`IrbisExtractFullText.exe`** — извлечение полного текста | Главный экстрактор ПТ: вытаскивает текст из PDF/документов для индекса ПБД (поля 951/955), управляется `[FullText]` ([CAPABILITY_MAP §1/§8](../../recon/deep/CAPABILITY_MAP.md), [FINDINGS_04 §FullText](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_finance_erm_dam](../specs/platform/SPEC_finance_erm_dam.md) (DAM/полнотекст, эпик #161); [SPEC_ws5_admin §5 AC1–AC3](../specs/SPEC_ws5_admin.md) (переиндексация ПТ, очередь, контроль целостности) | 🟡 | DAM/полнотекст назван, но **сам пайплайн извлечения (OCR/ALTO, текст-слой) технически не детализирован** (recon TODO #DAM-spec). Реальный пробел в глубине. |
| 8 | **`ftcachebuilder.exe`** — построитель кэша полного текста | Предсобирает/индексирует кэш ПБД для быстрого поиска (`ftcachebuilder=1` в `[FullText]`) ([FINDINGS_04 §FullText](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_ws5_admin §5](../specs/SPEC_ws5_admin.md) (очередь/переиндексация ПТ); [SPEC_finance_erm_dam](../specs/platform/SPEC_finance_erm_dam.md) (деривативы/кэш) | 🟡 | Кэш-построение ≈ наш индексатор ПТ (tsvector/деривативы); как отдельный управляемый шаг с метрикой не специфицирован. |
| 9 | **`pdftotext.exe`** — конвертер PDF→текст (Foolabs Xpdf) | Внешний инструмент **Xpdf** (подтверждено `xpdfrc` — `http://www.foolabs.com/xpdf/`): PDF-страница→текст для индекса; режим `ExtractPDFTXTMode=0` (`PDF2TEXT.EXE`) ([FINDINGS_04 §FullText](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_finance_erm_dam](../specs/platform/SPEC_finance_erm_dam.md) (извлечение текст-слоя в пайплайне DAM) | ⚫ | **DROP как конкретный бинарник.** Функция (PDF→текст) нужна и живёт в DAM-пайплайне, но **сам Xpdf-`.exe` заменяется библиотекой** (pdfminer/pypdf/Tika/OCR-движок) — мы не тащим легаси-внешний `.exe`. Функция = 🟡 в DAM (см. #7), артефакт = ⚫. |
| 10 | **`CheckPDF.exe`** — проверка/валидация PDF | Проверяет PDF на возможность извлечения страниц (`CheckPDF_with_Quickdll=1`; `ExtractPDFPageMode=3` = `checkpdf.exe+pdfsplitmerge`) ([FINDINGS_04 §FullText](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_finance_erm_dam](../specs/platform/SPEC_finance_erm_dam.md) (fixity/валидация ассета); [SPEC_ws5_admin §5 AC3](../specs/SPEC_ws5_admin.md) (контроль целостности) | ⚫ | **DROP как бинарник.** Проверка валидности/извлекаемости PDF — это **валидация-шаг внутри DAM-приёма** (fixity + «можно ли извлечь текст»), а не отдельный инструмент. Функция мигрирует в DAM, легаси-`.exe` отбрасывается. |

---

## 4. Инструменты пресетов конфигурации (INI/WS)

> Утилиты предустановки/правки параметрических ini-профилей и рабочих листов `.WS/.WSS`. Прямая параллель — наш **low-code конфигуратор тенанта** (D1 / PMF).

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 11 | **`PsetiniDB.exe`** + **`PsetiniDB_Client`/`Psetini_Client`** — пресеты INI | Предустановка/правка `.INI`-профилей (серверные/АРМ-профили, параметры БД) — пакетная настройка параметрии без ручного редактирования ([FINDINGS_04 §профили/права](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_lowcode §2](../specs/platform/SPEC_lowcode.md) (PMF — управление параметрией тенанта: поля/РЛ/ФЛК/форматы); [SPEC_ws5_admin §4 AC1–AC4](../specs/SPEC_ws5_admin.md) (low-code конфигуратор «без правки кода») | 🟡 | Концепт low-code конфига есть, но **PMF/раздел D1 помечен `[TBD]`**; конкретный «парсер ini/мердж пресетов» не детализирован. |
| 12 | **`Psetws.exe`** + **`Psetws_Client`** — пресеты рабочих листов | Предустановка/правка рабочих листов `.WS/.WSS` (структуры РЛ ввода, подполя) — пакетная заготовка форм ввода ([FINDINGS_04 §коды АРМов](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_lowcode §2](../specs/platform/SPEC_lowcode.md) (РЛ→DynamicField); [SPEC_ws5_admin §4 AC1](../specs/SPEC_ws5_admin.md) (редактор РЛ/подполей/ФЛК по 920); [SPEC_engine_flk](../specs/engines/SPEC_engine_flk.md) (ФЛК) | 🟡 | Редактор РЛ как low-code назван (ws5 §4), но **мердж/версионирование WS-пресетов и пакетная раскладка** в D1 ещё `[TBD]`. |

---

## 5. Утилита QR/штрих-кодов

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 13 | **`QRCodeGenerator.exe`** — генератор QR/штрих-кодов | Генерирует QR/штрих-код-изображения; в показе/печати — конструкция `<IMG SRC="IRBIS:!!ШТРИХ_КОД!!">` ([PFT_LANGUAGE §14](../../recon/deep/reference/format/PFT_LANGUAGE.md); recon TODO `#FMT-01` — QR отдельной конструкцией в Приложении 4 не описан). Применение: штрихкоды экземпляров (910^h, 19^B ISBN), читательские билеты, ссылки портала. | [SPEC_engine_pft §3.1/§3.3](../specs/engines/SPEC_engine_pft.md) (рендер штрих/QR в печатных бланках/этикетках); reader-портал (QR на билет/выдачу/ссылку записи) | 🟡 | Печать штрих/QR в бланках покрыта в A1, но **QR-кейсы читательского портала (билет, код брони из постамата, deep-link на запись)** явно не специфицированы. Связать A1 ↔ нотификации (`hold_pickup_code`) ↔ reader-портал. |

---

## 6. Серверное ядро и сервисная обвязка

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 14 | **`irbis_server.exe`** — ядро сервера | TCP-сервер (порт 6666), диспетчер: реестр сессий/клиентов, запуск воркеров, нативный wire-протокол (`A`/`B`/`C`/`D`…) ([FINDINGS_04 §архитектура](../../recon/deep/FINDINGS_04_server_admin.md), [WIRE_PROTOCOL](../../recon/deep/reference/protocol/WIRE_PROTOCOL.md)). | [SPEC_iac_fleet §1](../specs/platform/SPEC_iac_fleet.md) (K8s cloud-core: app+PostgreSQL HA+PgBouncer+MinIO, Terraform); [SPEC_I1_foundation #99](../specs/SPEC_I1_foundation.md) (прод-упаковка, healthz/readyz); [SPEC_sre §0–1](../specs/platform/SPEC_sre.md) | ✅ «замена» | Роль ядра берёт на себя веб-бэкенд + оркестратор. Нативный TCP-протокол ИРБИС нам не нужен (HTTP/JSON), но **функция «принимать клиентов, диспетчеризовать, держать сессии»** покрыта инфраструктурно. |
| 15 | **`server_64.exe`** — процесс обработки (воркер) | Stateless-обработчик запросов, запускается ядром (не для ручного старта), число растёт до предела ([FINDINGS_04 §ядро+процессы](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_iac_fleet §1](../specs/platform/SPEC_iac_fleet.md) (воркеры/поды, автоскейл); [SPEC_sre §4.3](../specs/platform/SPEC_sre.md) (bulkhead/лимиты) | ✅ «замена» | Воркер-процесс ИРБИС ≈ под/воркер приложения; масштабирование декларативно (HPA), а не «ядро плодит `server_64.exe`». |
| 16 | **`service_64.exe`** — Windows-сервис-обёртка | Запуск ядра как службы Windows (`service_64.exe /INSTALL` / `/UNINSTALL`, `Irbis64_Service`) ([FINDINGS_04 §установка](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_iac_fleet §1](../specs/platform/SPEC_iac_fleet.md) (жизненный цикл сервиса через оркестратор/systemd-unit на edge); [SPEC_I1_foundation #99](../specs/SPEC_I1_foundation.md) | ⚫ | **DROP как механизм.** Windows-служба заменяется контейнером + оркестратором (cloud) / systemd-unit (edge, Astra Linux). Функция «автозапуск как служба» сохраняется концептуально, конкретная Windows-обёртка отбрасывается. |
| 17 | **`ServerLogViewer.exe`** — просмотрщик серверного лога | Просмотр транзакционного лога сервера (формат `дата/время/IP/IDКлиента/Длина/Код/АРМ/№`, `MaxLogFileSize`) ([FINDINGS_04 §протокол](../../recon/deep/FINDINGS_04_server_admin.md)). | [SPEC_sre §2.5–2.6](../specs/platform/SPEC_sre.md) (структурные JSON-логи `trace_id`+`tenant_id`, Loki-класс хранилище, дашборды/алерты); [SPEC_ws5_admin §7](../specs/SPEC_ws5_admin.md) (логи/мониторинг) | 🟡 | Конвейер логов (сбор→хранилище→дашборд) спроектирован, но **отдельный admin-UI «просмотрщик/поиск по логу сервера»** в ws5 не материализован (только дашборды). |

---

## 7. Хост-хелперы и легаси-артефакты

| # | Утилита (`.exe`) | Что делает / функция ИРБИС | Наше покрытие (spec §/AC) | Статус | Примечание |
|---|---|---|---|---|---|
| 18 | **`ILFExplorer.exe`** — обозреватель инвертированного файла | Просмотр инвертированного файла/словаря (термин→постинги, структуры IFP/L01/N01) — диагностика поискового индекса ([FIELD_DICTIONARY](../../recon/deep/reference/format/FIELD_DICTIONARY.md)). | — (нет прямой спеки; ближайшее — scan-обзор словаря через [SPEC_protocols §1](../specs/gov/SPEC_protocols.md) Z39.50 Scan / browse-поиск) | ⚫ | **DROP.** ILF/IFP/L01/N01 — **физический формат инверсии ИРБИС**, которым у нас управляет PostgreSQL (GIN/tsvector). «Обозреватель инвертированного файла» неприменим: индекс — деталь СУБД, не редактируемый/обозреваемый артефакт. Браузинг терминов (если нужен библиотекарю) — через scan/autocomplete поиска, не через ILF-explorer. |
| 19 | **`GetUserName.exe`** — хелпер имени пользователя | OS-хелпер: получить имя текущего пользователя ОС (контекст оператора/станции при handshake) ([FINDINGS_04 §[MAIN]](../../recon/deep/FINDINGS_04_server_admin.md), `RECOGNIZE_CLIENT_ADDRESS`). | — (Identity даёт actor/tenant из JWT) | ⚫ | **DROP.** Имя пользователя/станции в вебе берётся из аутентификации (JWT-субъект, [SPEC_I1_foundation #101](../specs/SPEC_I1_foundation.md)), а не из OS-хелпера на хосте. Легаси десктоп-привязки. |
| 20 | **`local_ip.exe`** — хелпер локального IP | OS-хелпер: определить локальный IP хоста (для конфигурации/привязки/`RECOGNIZE_CLIENT_ADDRESS`) ([FINDINGS_04 §[MAIN]](../../recon/deep/FINDINGS_04_server_admin.md)). | — (адрес клиента из заголовков/zero-trust) | ⚫ | **DROP.** IP-резолвинг — деталь сетевого стека/прокси; в вебе адрес клиента известен из запроса (X-Forwarded-For/mTLS, [SPEC_I6 zero-trust] через [SPEC_sre §4.4](../specs/platform/SPEC_sre.md) rate-limit). Хост-`.exe` не нужен. |

---

## Итоговый подсчёт (tally)

**Всего утилит/функций в реестре: 20** (по уникальным `.exe`; парные клиенты `Psetini_Client`/`Psetws_Client` учтены в #11/#12).

| Статус | Кол-во | Утилиты |
|---|---:|---|
| ✅ покрыто (с AC) | **6** | #1 GenPFT64 · #2 tabgen · #3 GENTREE · #4 IrbisGblAdmin · #14 irbis_server · #15 server_64 |
| 🟡 частично/тонко | **8** | #5 IrbisMultiLoad · #6 ISO2709Editor · #7 IrbisExtractFullText · #8 ftcachebuilder · #11 PsetiniDB · #12 Psetws · #13 QRCodeGenerator · #17 ServerLogViewer |
| ❌ не покрыто (реальный пробел) | **0** | — *(все «пробелы» — это 🟡-углубления уже существующих движков, см. ниже)* |
| ⚫ DROP (легаси/неприменимо) | **6** | #9 pdftotext · #10 CheckPDF · #16 service_64 · #18 ILFExplorer · #19 GetUserName · #20 local_ip |

> **Сверка чисел.** ✅ 6 + 🟡 8 + ❌ 0 + ⚫ 6 = **20**. Итог: **✅ 6 · 🟡 8 · ❌ 0 · ⚫ 6**.

| Статус | Кол-во | Доля |
|---|---:|---:|
| ✅ покрыто | 6 | 30% |
| 🟡 частично | 8 | 40% |
| ❌ не покрыто | 0 | 0% |
| ⚫ DROP | 6 | 30% |

---

### Полный список ❌ (реальные пробелы на построение)

**❌ — пусто.** Ни одна утилита не «провисает» без какого-либо движка/спеки. **НО** четыре 🟡 — это **реальные углубления глубины, без которых функция утилиты не воспроизводится полностью**, и их следует трактовать как приоритетные задачи (де-факто пробелы внутри существующих движков):

| Кандидат | Утилита | Что именно надо достроить | Куда |
|---|---|---|---|
| **G1** | #7/#8/#9/#10 Полнотекст ПБД | **Технический пайплайн извлечения ПТ** (PDF→текст-слой/OCR/ALTO, очередь, кэш-деривативы, метрика свежести ПТ) — сейчас `[TBD: #DAM-spec]`. Это самый существенный недостроенный участок. | SPEC_finance_erm_dam + ws5 §5 |
| **G2** | #6 ISO2709Editor | **Импорт-мастер «таблица (XLS/DBF/CSV)→MARC по карте столбцов↔меток»** + базовый ручной правщик ISO-записи. У ИРБИС это отдельный data-onboarding инструмент; у нас транспорт MARC есть, а табличный конвертер — нет. | ws1 low-code / gov_exchange |
| **G3** | #11/#12 PsetiniDB/Psetws | **Раздел D1 (PMF) `[TBD]`**: парсер/мердж/версионирование пресетов ini и рабочих листов WS — материализовать low-code конфигуратор. | SPEC_lowcode §2 |
| **G4** | #5 IrbisMultiLoad | **Пакетный загрузчик с построчным отчётом об ошибках** + field-by-field маппинг (#GOV-01). | SPEC_gov_exchange / ws5 §6 |
| **G5** | #17 ServerLogViewer | Отдельный **admin-UI поиска по серверному логу** (сейчас только дашборды). | ws5 §7 |

### Полный список ⚫ DROP (сознательные отказы) — с обоснованием

| # | Утилита | Обоснование DROP в веб-on-PostgreSQL |
|---|---|---|
| 9 | `pdftotext.exe` (Foolabs Xpdf) | Внешний легаси-`.exe`; функция PDF→текст сохраняется, но через **библиотеку** (pdfminer/pypdf/Tika/OCR), а не отдельный бинарник. Артефакт отбрасывается, функция = G1. |
| 10 | `CheckPDF.exe` | Проверка извлекаемости/валидности PDF — это **валидация-шаг внутри приёма DAM** (fixity), а не самостоятельный инструмент. |
| 16 | `service_64.exe` (Windows-служба) | Жизненный цикл сервиса = контейнер+оркестратор (cloud) / systemd-unit (edge). Windows-service-обёртка неприменима. |
| 18 | `ILFExplorer.exe` | Инвертированный файл (IFP/L01/N01) — **физический формат индекса ИРБИС**, у нас им управляет PostgreSQL (GIN/tsvector). Обозреватель ILF неприменим; браузинг терминов — через scan/autocomplete. |
| 19 | `GetUserName.exe` | Имя пользователя/станции берётся из аутентификации (JWT), а не из OS-хелпера. Легаси десктоп-привязки. |
| 20 | `local_ip.exe` | Адрес клиента известен из HTTP-запроса (XFF/mTLS); OS-хелпер локального IP не нужен. |

---

### Новая функциональность vs уже-известные пробелы движков

> Ключевой вывод: **ни одна утилита не вводит принципиально новой бизнес-функции** сверх уже отображённых АРМов/движков. Все они — либо «движковые» инструменты (растворяются в A1/A3/A4/B2/DAM), либо инфраструктура (ядро→IaC/SRE), либо легаси-артефакты файловой реализации (⚫).

| Категория | Утилиты | Куда маппится |
|---|---|---|
| **Маппится на уже-известные движки-пробелы** (углубление, не новизна) | #1 GenPFT64→**A1** · #2 tabgen→**A1** · #3 GENTREE→**A4/A5** · #4 IrbisGblAdmin→**A3** · #5 MultiLoad→**B2-обмен** · #6 ISO2709Editor→**B2/ws1** · #7/#8/#9/#10 полнотекст→**DAM** · #11/#12 Pset*→**low-code D1** · #13 QR→**A1/reader** · #17 ServerLogViewer→**SRE/ws5** | Существующие движки/спеки; нужны лишь углубления G1–G5. |
| **Инфраструктура → IaC/SRE** (не новая бизнес-функция) | #14 irbis_server · #15 server_64 · #16 service_64 | SPEC_iac_fleet / SPEC_sre / I1 #99. |
| **Легаси-артефакт файловой реализации → DROP** | #9 pdftotext · #10 CheckPDF · #16 service_64 · #18 ILFExplorer · #19 GetUserName · #20 local_ip | Неприменимо; сознательный отказ. |
| **Генуинно новая функция (которой нет в АРМах/движках)** | — **нет** | Утилиты не расширяют функциональный периметр продукта. |

> **Единственный по-настоящему недо-проработанный участок, вскрытый утилитами** — **полнотекстовая подсистема ПБД (G1)**: четыре кооперирующихся инструмента (`IrbisExtractFullText`/`ftcachebuilder`/`pdftotext`/`CheckPDF`) показывают, что у ИРБИС это **полноценный конвейер извлечения/кэша/валидации**, а у нас он пока `[TBD]` в DAM. Это главный приоритет на достройку. Вторичные — G2 (табличный MARC-импорт из Excel/DBF) и G3 (low-code пресеты D1).

---

## Приложение. Соответствие утилит `inventory.csv` (живая инсталляция)

| `.exe` (inventory.csv) | Размер | Категория CSV | Строка реестра | Статус |
|---|---:|---|---|---|
| `GenPFT64.exe` (+`GenPFT64.ini`) | 1 709 056 | INSTALL | #1 | ✅ |
| `tabgen.exe` | 748 544 | INSTALL | #2 | ✅ |
| `GENTREE.EXE` | 395 264 | INSTALL | #3 | ✅ |
| `IrbisGblAdmin.exe` | 957 952 | INSTALL | #4 | ✅ |
| `IrbisMultiLoad.exe` | 696 832 | INSTALL | #5 | 🟡 |
| `ISO2709Editor.exe` (+`ISO2709Editor.INI`) | 1 552 896 | INSTALL | #6 | 🟡 |
| `IrbisExtractFullText.exe` | 607 744 | INSTALL | #7 | 🟡 |
| `ftcachebuilder.exe` | 635 392 | INSTALL | #8 | 🟡 |
| `pdftotext.exe` (+`xpdfrc`) | 860 160 | INSTALL | #9 | ⚫ |
| `CheckPDF.exe` | 356 864 | INSTALL | #10 | ⚫ |
| `PsetiniDB.exe` / `Psetini_Client.exe` | 1 147 904 / 1 104 384 | INSTALL / DOCS | #11 | 🟡 |
| `Psetws.exe` / `Psetws_Client.exe` | 717 824 / 882 176 | INSTALL / DOCS | #12 | 🟡 |
| `QRCodeGenerator.exe` | 1 347 072 | INSTALL | #13 | 🟡 |
| `irbis_server.exe` (+`irbis_server.ini`) | 776 192 | INSTALL | #14 | ✅ |
| `server_64.exe` | 932 352 | INSTALL | #15 | ✅ |
| `service_64.exe` | 451 584 | INSTALL | #16 | ⚫ |
| `ServerLogViewer.exe` | 693 248 | INSTALL | #17 | 🟡 |
| `ILFExplorer.exe` | 851 968 | INSTALL | #18 | ⚫ |
| `GetUserName.exe` | — | INSTALL | #19 | ⚫ |
| `local_ip.exe` | — | INSTALL | #20 | ⚫ |

> Все 21 `.exe` живой инсталляции (включая парные `*_Client`) отнесены к строкам реестра. Бинарники в `inventory.csv` помечены `skipped — not decompiled (rule 6)`, поэтому функции выведены из **сырых конфигов** (`GenPFT64.ini`, `ISO2709Editor.INI`, `irbis_server.ini [FullText]`, `xpdfrc`) + ARM/recon-описаний — это достоверная база, без дизассемблера.
