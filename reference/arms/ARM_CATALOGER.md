# АРМ «Каталогизатор» — разбор INI

Источник: `irbisc.ini` → `_work\cfg_txt\IRBIS64__irbisc.ini.txt` (CP1251, 1475 строк). Секций: **10**: `[Main]`, `[Entry]`, `[Display]`, `[Rubricator]`, `[Private]`, `[NAVIGATOR]`, `[USERMODE]`, `[TEXTS]`, `[FULLTEXT]`, `[SEARCH]`.

> ⚠ В `[Main]` есть почтовые креды (`MailUser`,`MailPassword`) и креды ЛИБНЕТ (`LIBNETUSER`,`LIBNETPASSWORD`) — значения НЕ переносятся, только имена ключей.

## `[Main]` — глобальная настройка
| Ключ | Смысл |
|---|---|
| `CLIENT_TIME_LIVE=15` | тайм-аут клиента (мин) |
| `DBNNAMECAT=dbnam2.tre` | дерево списка БД (древовидный вариант) |
| `PftMnu=PFTw.tre` / `PftOpt=PFTw_H.OPT` | меню форматов показа + опции PFT |
| `FmtMnu=FMT31.tre` / `WsOpt=WS31.OPT` / `TabMnu=tabw.tre` | меню форматов вывода / опций РЛ / табличных форм |
| `IMPORTMNU/EXPORTMNU/COPYMNU` | меню импорта/экспорта/копирования (FST) |
| `STTMNU=stt.mnu` / `STFMNU=stf.tre` | меню стат.таблиц / стат.форм |
| `PRMARCFORMAT=MARC` | внутренний MARC-формат |
| `KKK*` (~25 ключей) | печать каталожной карточки: `KKKpriz=!KKK`, размеры/поля/ориентация/шрифт (`KKKFONTNAME=Arial`, `KKKDEFAULTWIDTH=120`…) |
| `TagFullText=951`, `TagImage=950`, `TagVid=920` | метки: полный текст / имидж / вид документа |
| `SerVid=J`, `DBNTAGSHIFR=903` | признак сериального; метка шифра |
| `HelpDBN=HELP`, `BriefPft=BRIEF`, `DefaultDB=IBIS` | БД помощи; краткий формат; БД по умолчанию |
| `SetPrivate=1`/`SetPrivateWSS=setpriv` | режим «приватных» параметров + РЛ |
| `WSFDT=DEFAULT`, `AccessLevel=0` | РЛ ввода по умолчанию; уровень доступа (0=полный) |
| `DELETEABLE/COPYABLE/IMPORTABLE/CLEARABLE/GLOBALABLE/PREVCOPYABLE=1` | разрешения операций над записями |
| `MODATHRA/C/S/B/U/G` | привязка к авторитетным БД |
| `DBEK1=IBIS` (DBEK2/3 пусты) | список БД ЭК для экземпляров |
| `PRRELATION=1`/`RelationMnu=relation.mnu` | связанные документы + меню |
| `LIBNET*` | импорт из ЛИБНЕТ: `LIBNETIP`(URL), `LIBNETSEARCHPAGE`, `LIBNETFORMAT`, `LIBNETFST`, `LIBNETGBL` (user/password опущены) |
| `RUSMARCFST/UNIMARCFST/USMARCFST`+`*GBL` | FST/GBL импорта в RUSMARC/UNIMARC/USMARC |
| `ZIMPORTSEARCHPAGE`, `ZIMPORTFORMAT` | импорт из Z39.50-ресурсов |
| `HLPFILE=irbisc.hlp`, `Workdir=c:\irbiswrk\` | файл помощи; рабочий каталог |
| `DictionPortion=3`, `DictionSence=300`, `DisplaySence=100` | порция/чувствительность словаря и показа |
| `CustomDict=CUSTOM.DIC`, `SpellColor=clGreen` | орфословарь + цвет подсветки |
| `AutoinFile=autoin.gbl` | ГБ-задание автоввода |
| `UNICODEMNU=unicode.mnu` | виртуальная Unicode-клавиатура |
| `LimPftFull_910/922/330/390/691/boko691` | лимиты повторений полей при форматировании full |
| `SEARCHONLY=0`, `BATCHABLE=1`/`BATCHMNU=batch.mnu`, `Mnuable=1`/`Mnumnu=mnu.mnu` | режим «только поиск»; пакетные задания; корректировка MNU |
| `MailHost/MailPort/MailFrom/MailFromAdress/MailSSL/MailOption` | почта (`MailUser`,`MailPassword` — только имена) |
| `PATHTOCGIIRBIS`, `PASSWORDMD5=0` | URL CGI полнотекста/имидж; MD5-хеш паролей |
| `MAXREPEAT=5000`, `MAXDOCSEARCH=5000` | макс. повторений форматирования / результат поиска в пакете |
| `RSUDCINPUT=1`, `RSBBKINPUT=1` | ввод УДК/ББК из справочных БД |
| `SHORTCUT_*` (~90) | горячие клавиши пунктов меню (База/Ввод/Поиск/Просмотр/Сервис/Помощь) + фокус (`FOCUSTODICTION/ENTRY/BRIEF/DOCUMENT`) |

## `[Entry]` — ввод
`MaxAddFields=10` (макс. добавляемых полей), `DefFieldNumb=10`, `DbnFLC=DBNFLC` (ФЛК по умолчанию), `RECUPDIF=1` (актуализировать при сохранении).

## `[Display]`
`MaxMarked=100`, `MaxBriefPortion=3`.

## `[Rubricator]` — рубрикатор ГРНТИ
`PrefRubGroup=G=`/`RubPref=R=` (префиксы группы/рубрики), `MaxRubGroup=100`/`MaxRubLevel=3`/`RubLevelLength=3` (иерархия), `RubTagCode=3`/`RubTagText=2`/`RubTagLook=20` (метки кода/текста/просмотра), `RubLevelWidth=14`/`RubPattern=.00`.

## `[Private]` — приватные параметры/инвентаризация
Значения по умолчанию текущего пользователя (КСУ, фонд, проверка фонда): `FIO=MASTER`, `EKP=IBIS`, `PROVFOND=1`, `PRFDDAT`, `PRFDMHR=ХР` (место хранения для проверки), множество `KK*/FP*` (книги/фонды по статусам), пары `PRPARNAME1..12`/`PRPARVALUE1..12`.

## `[NAVIGATOR]` — встроенный браузер ИРБИС-Навигатор
`InitURL=irbis:1,,IMAGE,SEARCH_IC_WN,@1?FREEPAR5=0` (стартовый URL — имидж-каталог), `IrbisCorporationAdress/Signatura`, доступность функций (`FileOpen/FileSaveAs/FilePrint/Favorites*/ServisToolBars/URLCoolBar/RBUTTONDOWN=1`), `HelpURL`. `PARNAME_*` (~60) — имена HTTP-параметров CGI-протокола ИРБИС (поиск `S21*`, термины `T21*`, ввод `R21*`, экспорт/импорт `EXP21*/IMP21*`). `MODTAG_*` (1000…1100) — метки модификации. `TRMPORTION=100`, `SEARCHPORTION=20`, `NUMBFREEPAR=20`, `FULLTEXTMAXRESULT=100`, `FULLTEXTMorphology=1`, `RS_READER_PROLONG/FULL=1` (Книговыдача-самообслуживание), `BL_READER_FULL=1` (Книговыдача-лайт).

## `[USERMODE]` — пользовательские режимы (DLL)
Пустая. Структура: `UMNUMB`, `UMDLL<n>`, `UMFUNCTION<n>`, `UMPFT<n>`, `UMNAME<n>`, `UMGROUP<n>`.

## `[TEXTS]` — полные тексты (метки/константы)
`FULL_TEXT_Name=952`, `FULL_TEXT_IMAGE_TAG=953`, `FULL_TEXT_Words_Number=20`, `FULL_TEXT_Index=21`, `FULL_TEXT_BRIEF=22`, `FULL_TEXT_NUMWORDS_IN_BRIEF=30`, `FULL_TEXT_MAX_WORD_LEN=4`.

## `[FULLTEXT]`
`FULLTEXTACTUAL=1`, `CheckPDF_with_Quickdll=1`, `JPG_PAGES_IN_CASH_DPI=200`.

## `[SEARCH]` — словарный поиск
`ItemNumb=64` (индекс 0..63; разделитель раздела имеет `ItemPref=-` и `ItemIdent<N>`). Структура элемента:
| Ключ | Смысл |
|---|---|
| `ItemName<n>` | название вида поиска |
| `ItemPref<n>` | префикс словаря (`A=`,`T=`,`K=`,`S=`,`U=`…); `-`=заголовок раздела |
| `ItemIdent<n>`/`ItemIdentUp<n>` | идентификатор раздела / принадлежность пункта |
| `ItemDictionType<n>` | тип: 0 обычный, 1 по меню, 2 рубрикатор |
| `ItemLogic<n>` | логика по умолчанию |
| `ItemMenu<n>` | файл MNU справочника |
| `ItemF8For<n>` | формат для F8 (`!F8avt`,`!F8TIT`,`!F8COL`…) |
| `ItemModByDic<n>` | формат коррекции по словарю (`!DMODT`,`!DMODK`…) |
| `ItemTranc<n>` | усечение (0=запрещено) |
| `ItemAdv<n>` | расширенный поиск через авторитетную БД: `ATHRA,A=,@sadv` |

Разделы (по `ItemIdent`): 1 Ответственность/Авторы, 2 Заглавие, 3 Тематика, 4 Экземпляры, 5 Коды, 6 Выходные данные, 7 Прочие. Квалификаторы: `CvalifNumb=4` (`CvalifName/CvalifValue` — список меток `/(…)`). Поиск по связи: `ScntNumb=14` (`ScntName/ScntFormat(!scnt1..!scnt13)/ScntPref/ScntSuffix($)/ScntLogic`): Автор, Заглавие, Коллектив, Рубрикатор, Предметные, УДК/ББК, Журнал↔Номера, Номер↔Статьи, Документ↔Приложение, Рецензия, Подшивка, Параллельные, Изменение заглавия, Другие. Авторитетные: `IntNumb=0` (не задействованы). Навигаторы: `WnNumb=8` (`WnName/WnLink` irbis:-ссылки): RSUDC, RSBBK, athrc, athra, athrs, tez, MeSH, ГРНТИ. Хвост: `SeqSearch=1`, `ComplSearch=1`, `DEFLEXKW=1`, `MaxComplItem=15`, `MinLKeyWord=1`, `MinLKWLight=4`, `MORPHOLOGY=1`.
