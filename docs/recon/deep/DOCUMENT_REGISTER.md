# DOCUMENT_REGISTER — реестр всех файлов и статусы обработки

> Реестр охватывает **обе рабочие папки**: `INSTALL` = `C:\IRBIS64\` (действующая инсталляция сервера + БД), `DOCS` = `C:\IRBIS64_COPY 17-09-2025\` (комплект документации и справки). Полный машинный леджер — [`inventory.csv`](inventory.csv) (по одной строке на файл: Source, RelPath, DB, Ext, SizeBytes, Category, Status, Coverage). Этот MD — человекочитаемая сводка с прослеживаемостью.

## Легенда статусов
- **done** — содержимое отражено в карте (FINDINGS/CAPABILITY_MAP). Для массовых однотипных конфигов (правило §6 ТЗ) — зафиксирована **механика + образцы**, статус `done` означает «механика разобрана, семейство покрыто», см. колонку Coverage в CSV.
- **skipped** — не анализируется по обоснованной причине: данные БД, изображения, исполняемые файлы (не декомпилируем), образцы полных текстов, архивы дистрибутива, либо справка в нечитаемом формате с указанием, чем покрыта.
- **todo** — не обработано. **Текущее значение todo = 0.**

## Сводка полноты

| | Всего | done | skipped | todo |
|---|---|---|---|---|
| **Все файлы** | **14 270** | **11 323** | **2 947** | **0** |

| Категория | Всего | done | skipped | Причина skipped |
|---|---|---|---|---|
| config (par/fst/ini/pft/mnu/wss/opt/…) | 11 292 | 11 292 | 0 | — |
| image (jpg/gif/png/bmp/ico/wav) | 2 256 | 0 | 2 256 | изображения/образы (данные) |
| data (mst/xrf/ifp/l01/n01/cnt/lex/dic…) | 568 | 0 | 568 | файлы данных/индексы БД (бинарь) |
| doc (doc/docx/rtf/ppt/pdf/chm/hlp) | 77 | 28 | 49 | см. §1 ниже |
| binary (exe/dll) | 52 | 0 | 52 | исполняемые — не декомпилируем (§6) |
| other (rar/ilf/srt/ps1/xpdfrc) | 20 | 3 | 17 | архивы/скомпилированные FST-WS/рабочие скрипты |
| junk (old/bak/new) | 5 | 0 | 5 | резерв/временные |

По источникам: INSTALL — 14 198 файлов, DOCS — 72 файла.

## 1. Документация (Pass 1) — все 77 doc-файлов

### 1.1 Проанализированные документы (28) → конвертированы (Word/PowerPoint COM, CP1251→UTF-8) и отражены в FINDINGS

| Файл | Источник | Покрывающий FINDINGS |
|---|---|---|
| `irbis64_client_dll.doc` | DOCS | [FINDINGS_03](FINDINGS_03_protocol.md) — протокол/клиентская DLL (80 функций) |
| `Сервер 64.doc`, `s_irbis.doc`, `Администрирование сервера ИРБИС64.ppt`, `Инструкция по установке ИРБИС64.doc`, `Первые шаги … администратора ИРБИС64.doc`, `Инструкция по переходу на новую версию.doc` | INSTALL/DOCS | [FINDINGS_04](FINDINGS_04_server_admin.md) — сервер и администрирование |
| `irbiscat.doc` | DOCS | [FINDINGS_05](FINDINGS_05_arm_cataloger.md) — АРМ Каталогизатор |
| `IrbisCom.doc`, `Комплектатор в Каталогизаторе.docx` | DOCS | [FINDINGS_06](FINDINGS_06_arm_acquisition.md) — АРМ Комплектатор |
| `irbisKO64.doc` | DOCS | [FINDINGS_07](FINDINGS_07_arm_bookprovision.md) — АРМ Книгообеспеченность |
| `WBKNJ.doc`, `IrbisMBA.doc` | DOCS | [FINDINGS_08](FINDINGS_08_arm_lending_mba.md) — Книговыдача/МБА |
| `WEBIRBIS64+.DOC` | DOCS | [FINDINGS_09](FINDINGS_09_web_reader.md) — Web-ИРБИС / Читатель |
| `irbis64_2022.doc` | DOCS | [FINDINGS_10](FINDINGS_10_overview_system.md) — общее описание системы |
| `RELEASE_OVERALL.doc` | DOCS | [FINDINGS_11](FINDINGS_11_release_capabilities.md) — каталог возможностей по выпускам |
| `Irbis64_struct.rtf`, `Формат Rich Text.doc` | INSTALL | [FINDINGS_12](FINDINGS_12_record_structure.md) — структура записи и файлов БД |
| `IRBISPRL.DOC` | DOCS | [FINDINGS_13](FINDINGS_13_irbisprl.md) — перечень элементов данных ЭК/комплектования |
| `Описание БД … GUAR.doc`, `Описание БД … EVENT.docx`, `Построение … фасетов … .doc`, `Инструкция по созданию стат.форм.doc`, `Дополнительные материалы ИРБИС64+.doc` | DOCS | [FINDINGS_14](FINDINGS_14_db_descriptions_misc.md) — спец-БД и тематические материалы |
| `Datai\CMPL\KSUN1SH.RTF`, `KSUN2SH.RTF`, `KSUN3SH.RTF` | INSTALL | RTF-шаблоны печатных форм КСУ — отражены в [FINDINGS_06](FINDINGS_06_arm_acquisition.md) |

### 1.2 Справка CHM/HLP (14) — skipped: извлечение недоступно
`hh.exe -decompile` в данной среде неработоспособен (возвращает 0 файлов); 7-Zip/chm-библиотеки отсутствуют. Содержание справки **дублируется эквивалентными `.doc`**, которые проанализированы.

| CHM/HLP | Чем покрыто |
|---|---|
| `irbis64.chm` (72 МБ — мастер-справка) | `irbis64_2022.doc` → FINDINGS_10 |
| `irbisc.chm`, `irbiscat2008.chm`, `IRBISC.HLP` | `irbiscat.doc` → FINDINGS_05 |
| `irbisp.chm`, `irbiscom_2008.chm`, `IRBISP.HLP` | `IrbisCom.doc` → FINDINGS_06 |
| `irbisk.chm`, `IRBISK.HLP` | `irbisKO64.doc` → FINDINGS_07 |
| `irbisb.chm`, `IRBISB.HLP` | `WBKNJ.doc`/`IrbisMBA.doc` → FINDINGS_08 |
| `irbisa.chm` (×2), `IRBISA.HLP` | `Сервер 64.doc` → FINDINGS_04 |
| `irbisNavigator.chm` | Навигатор — FINDINGS_09 (раздел NAVIGATOR) |
| `TCP_IP.chm` | `irbis64_client_dll.doc` → FINDINGS_03 |

> `TODO(recon #R01: при наличии рабочего извлечения CHM (другая ОС/7-Zip) сверить полную справку irbis64.chm с .doc — возможны разделы, отсутствующие в .doc.)`

### 1.3 Прочие doc/pdf (skipped как данные/вспомогательное)
- **Образцы полных текстов** (данные): 21 PDF в `Datai\IBIS\Texts\`, `Datai\GUAR\*.pdf`, `Datai\VKR\*.pdf`; 4 PDF и 4 DOCX в `Datai\MBA\Texts\` (договоры/абоненты МБА).
- **Вспомогательная док-ция БД** (частично покрыта FINDINGS_14, TODO #1401): `Datai\GUAR\guar_PFT.doc`, `Datai\GUAR\Описание…GUAR.doc` (дубль), `Datai\HELP\IZMGR1.DOC`/`IZMGR2.DOC`, `Datai\IBIS\DOCLAD99.DOC`, `Datai\IMAGE\DOCLAD99.DOC`, `Datai\PODB\KP_INST.DOC`.

## 2. Конфиги (Pass 2) — 11 292 файла, status=done (механика+образцы)

Разобрана механика каждого типа (см. [FINDINGS_02](FINDINGS_02_config_and_db_profiles.md)); для повторяющихся семейств зафиксированы образцы (правило §6 ТЗ).

| Тип | Кол-во | Назначение | Где разобрано |
|---|---|---|---|
| `.pft` | 3 903 | форматы показа/вывода | FINDINGS_02 §5, FINDINGS_05/09 |
| `.mnu` | 2 154 | меню/справочники | FINDINGS_02 §7 |
| `.wss` | 1 608 | рабочие листы подполей | FINDINGS_02 §6 |
| `.gbl` | 546 | задания глобальной корректировки | FINDINGS_05, FINDINGS_03 §9 |
| `.srw` | 475 | форматы/выгрузки | FINDINGS_02 §1 |
| `.ws` | 459 | рабочие листы ввода | FINDINGS_02 §6 |
| `.tbu`/`.tbg` | 685 | таблицы переформатирования | FINDINGS_02 §1 |
| `.hdr` | 402 | заголовки таблиц | FINDINGS_05 |
| `.fst` | 336 | инвертирование → префиксы | FINDINGS_02 §3 |
| `.opt` | 111 | выбор ресурса по полю 920 | FINDINGS_02 §5–6 |
| `.tab` | 97 | таблицы соответствия (ISO/MARC) | FINDINGS_05 |
| `.ini` | 75 | профили АРМов/БД | FINDINGS_02 §4, FINDINGS_04 |
| `.stf`/`.stw` | 123 | сценарии статистических форм | FINDINGS_14 |
| `.tre` | 69 | иерархические справочники | FINDINGS_02 §7 |
| `.xlt` | 62 | переключатели/транслитерация | FINDINGS_05 |
| `.par` | 56 | пути файлов БД | FINDINGS_02 §2 |
| прочие (`txt,smf,clf,html,sch,fmt,ows,xls,wsl,rul,ww,bas,htm,json,msg,voh,any`) | ~130 | разное (тексты, формы, схемы) | FINDINGS_02/05/09 |

Профиль каждой из **49 БД** (поисковые префиксы, число конфигов) — [FINDINGS_02 §8](FINDINGS_02_config_and_db_profiles.md). Полный реестр БД — `Datai\DBNAM1.MNU` (44 БД для каталогизатора) + служебные.

## 3. Данные / изображения / бинарь / прочее (skipped)
- **data (568):** мастер-файлы `.mst`, ссылки `.xrf`, словари/инверсия `.l01/.n01/.ifp`, счётчики `.cnt`, фасеты `.cell*`, словари орфографии `.lex/.dic` — содержимое не анализируется (правило §6), структура файлов БД описана теоретически в [FINDINGS_12](FINDINGS_12_record_structure.md).
- **image (2 256):** `.jpg/.gif/.png/.bmp/.ico/.wav` — образы каталога, иконки, звуки.
- **binary (52):** `.exe/.dll` (сервер, АРМы, утилиты, YAZ/Z39.50, RFID, PDF-утилиты) — **не декомпилируются**; назначение выводится из имён и документации (FINDINGS_04).
- **other-skipped (17):** `.ilf` (скомпилированные FST/WS — бинарь), `.rar` (архивы дистрибутива `Datai.rar`, `IRBIS64.rar`, `IRBIS64_COPY….rar` — не распаковываются в репозиторий), рабочие скрипты разведки.

## 4. Отчёт о полноте
- Обработаны обе папки: **14 270 файлов**, из них **done = 11 323**, **skipped = 2 947 (с причинами)**, **todo = 0**.
- Каждый документ комплекта отражён в картах либо помечен `skipped` с причиной (§1).
- Машинно-находимые незакрытые вопросы собраны как `TODO(recon #NNNN)` в [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
- Главное ограничение среды: недоступно извлечение CHM/HLP (см. §1.2, TODO #R01) — компенсировано анализом эквивалентных `.doc`.
