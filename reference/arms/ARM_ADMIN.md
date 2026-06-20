# АРМ «Администратор» — разбор INI

Источник: `IRBISA.INI` → `_work\cfg_txt\IRBIS64__IRBISA.INI.txt` (CP1251, 120 строк). Секций: **3**: `[Main]`, `[FullText]`, `[CONTEXT]`.

> `User=Демонстрационная версия` — метка лицензии; кредов/IP в файле нет.
> `TODO(recon #ARM-06)`: файл краткий — нет `[SEARCH]/[ENTRY]/[DISPLAY]`. Администратор работает напрямую с физической структурой БД (актуализация/реорганизация/импорт-экспорт), а не через поисковый интерфейс. Серверные параметры (БД, порты) — в `irbis_server.ini` (см. FINDINGS_04).

## `[Main]` — глобальные параметры администрирования
| Группа | Ключи |
|---|---|
| Лицензия/предупреждение | комментарий «Изменение … приведёт к прекращению работы системы!!!», `User=Демонстрационная версия` |
| Актуализация/реорганизация | `AUTO_ACTUALIZE=0` (актуализация в режиме опроса), `MST_NUM_FRAGMENTS=0` (фрагментация MST, до 32), `RecUpdif=0` |
| Словарь/фасеты | `CREATE_CELLS_ON_IF_REORGANIZATION=1` (фасеты из `<dbname>.cells` при реорганизации IF), `MAX_POSTINGS_NUMBER_IN_CELL=0`, `CREATE_OLD_INVERTION_FILES=1` (словарь 13-й версии) |
| Имена БД/меню | `DBNNAMECAT=dbnam1.mnu`, `MASTER=`, `EmptyDBN=BLANK`, `EtalonDBN=IBIS`, `CurDBN=IBIS`, `HLPFILE=irbisa.hlp` |
| Меню операций | `IMPORTMNU=IMPORTW.MNU`, `EXPORTMNU=EXPORTW.MNU`, `COPYMNU=FSTW.MNU` |
| Пути | `DataPath=.\DATAI\`, `workdir=.\workdir`, `UCTABPATH=isisucw`, `ACTABPATH=isisacw` |
| Шрифт интерфейса | `FontName=Arial`, `FontCharSet=204` |
| MARC/XML | `PRMARCFORMAT=MARC`, `XMLTAGFIELD=field`, `XMLTAGSUBFIELD=subfield`, `XMLTAGCONTROL=control`, `XMLATTRIND/TAG/CODE`, `XMLTAGRECORD=record`, `XMLTAGTOPLEVEL=collection` |
| Пункты меню (права/видимость, `…Item=1`, ~55) | работа с БД (`DataBaseItem`,`OpenDBItem`,`NewDBItem`,`EmptyFull(Text)`,`ClearDBItem`,`DeleteDBItem`,`CloseDBItem`,`ImportDBItem`,`ExportDBItem`,`CopyDBItem`), разблокировки (`UnLock*Item`), сервис (`RestatItem`,`ActualItem/ActualIfItem`,`LoadIf*Item`,`ReorgIf/Mf/ExMfItem`,`CopyMfItem`,`RestoreMfItem`, списки `DeletedList/UnactualList/LockedListItem`,`DiagnosMfItem`), сервер (`ServerItem`,`ServerRestartItem`,`ServerCurrentClientListItem`,`ServerClientListItem`,`ServerProcessListItem`), `ExitItem`,`HelpItem` |
| Пакетный ввод | `MULTILOAD=`, `MULTISORT=0`, `AddText_ShablonPFT=shablon.pft` |
| Имидж-каталог | `DBNNAMECAT4=dbname_IC_wn.mnu`, `WEBIRBIS=…\irbis64r_IMGplus17` (путь к Web-шлюзу) |

## `[FullText]` — обслуживание полных текстов
| Ключ | Смысл |
|---|---|
| `FULLTEXTACTUAL=1` | актуализировать ПТ при актуализации словаря |
| `PDFExtractTime=30` | макс. время извлечения страницы (сек) |
| `PDFPageNumber=10` | число страниц |
| `STORE_PAGES/JPG_PAGES/TXT_PAGES/STXT_PAGES_IN_CASH` | кэширование страниц (txt/stxt — да, jpg — нет) |
| `JPG_PAGES_IN_CASH_DPI=200` | DPI кэшируемых JPG |
| `PDF_SPLITMERGE_EXTRACT_PAGE_COUNT=20` | страниц при split/merge |
| `ExtractPDFPageMode=4` | режим извлечения страниц PDF (4=QPDF.exe fast) |
| `ExtractPDFLink=1`, `ExtractPDFTXTMode=0` | извлечение ссылок; режим текста (0=PDF2TEXT.EXE) |
| `CheckPDF_with_Quickdll=1`, `ftcachebuilder=1` | проверка извлекаемости; построитель кэша ПТ |

## `[CONTEXT]`
`DBN=MBA` — текущая (контекстная) БД администрирования.

---
## Сводка по INI всех АРМов
| АРМ | Файл | Секций | ~Параметров | Ключевые секции |
|---|---|---:|---:|---|
| Каталогизатор | irbisc.ini | 10 | ~1375 | `[Main]`, `[SEARCH]` (64 Item, 14 Scnt, 8 Wn), `[NAVIGATOR]`, `[Private]`, `[TEXTS]` |
| Читатель | Irbisr.ini | 7 | ~641 | `[Main]`, `[SEARCH]` (23 Item, 8 Scnt, 5 Int, 9 Wn), `[Reader]`, `[Request]` |
| Книговыдача | IRBISB.INI | 8 | ~309 | `[Main]` (RFID), `[Reader]` (15 Item), `[Request]` (9 Item), `[Search]` (7), `[WS]` |
| Комплектатор | IRBISP.INI | 11 | ~2672 | `[MAIN]`, `[ENTRY]`, `[CMPL]`, `[SEARCH]` (50), `[SEARCHCMP]` (Z31/R28/S4/P12/DBN34/Pdp13), `[POST]` |
| Книгообеспеченность | irbisk.ini | 9 | ~2949 | `[MAIN]`, `[DISPLAY]` (отчёты), `[SEARCH]` (22), `[SEARCHKO]` (27 Item, 3-БД связи), `[WS]` |
| Администратор | IRBISA.INI | 3 | ~100 | `[Main]` (~55 *Item прав), `[FullText]`, `[CONTEXT]` |
| **ИТОГО** | 6 файлов | **48** | **~7046** | |

> Кредами/IP не переносились (правило §6): `MailUser`/`MailPassword` (все клиентские АРМы), `LIBNETUSER`/`LIBNETPASSWORD` (irbisc, irbisp), `RFID_UNI_ADDRESS` IP (irbisb) — только имена ключей.
