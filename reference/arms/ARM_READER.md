# АРМ «Читатель» — разбор INI

Источник: `Irbisr.ini` → `_work\cfg_txt\IRBIS64__irbisr.ini.txt` (CP1251, 704 строки). Секций: **7**: `[Main]`, `[SEARCH]`, `[Rubricator]`, `[Display]`, `[Reader]`, `[Request]`, `[NAVIGATOR]`.

> ⚠ В `[Main]` есть `MailUser`/`MailPassword` — значения НЕ переносятся.

## `[Main]`
| Ключ | Смысл |
|---|---|
| `CLIENT_TIME_LIVE=15`, `DBNNAMECAT=dbnam3.mnu` | тайм-аут; меню списка БД (читателю видны IBIS+IMAGE) |
| `TagFullText=951`, `TagImage=950`, `TagVid=920`, `SERVID=J` | метки полного текста/имиджа/вида; признак сериального |
| `AnalVid1=ASP`, `AnalVid2=AUNTD` | виды аналитических описаний (статьи) |
| `DBNPREFSHIFR=I=`, `DBNTAGSHIFR=903`, `DBNTAGSOURCE=463`, `DBNTAGEKZ=910` | префикс/метки шифра, источника, экземпляра |
| `DBNDELIM*` (SOURCE=W, STATUS=A, INV=B, BAR=H, STORE=D, WINV1=1, WINV2=2) | разделители подполей экземпляра |
| `DBNFREEEKZ=0`, `DBNWINVEKZ=U` | свободный экземпляр; статус списанного |
| `HelpDBN=HELP`, `PFTMNU=formatw.mnu`, `PFTOPT=PFTW_H.OPT`, `BriefPft=BRIEF`, `DefaultDB=IBIS` | помощь; меню/опции форматов; краткий; БД по умолчанию |
| `ExportMnu=exportw.mnu`, `PRMARCFORMAT=MARC`, `TezSelectLevel=2` | экспорт; MARC; уровень выбора из тезауруса |
| `Exportable/Printable/Retrolandable/Recomendable=1` | разрешения: экспорт, печать, заказ по ретрофонду, рекомендации |
| `SortMnu=sort.mnu`, `SortMaxHits=100` | меню/лимит сортировки |
| `InfoForReaderPft=FREEKZ1`, `RECOMENDPFT=recomend` | формат информации для читателя; рекомендации |
| `MINIMIZEABLE/CLOSEABLE=1` | управление окном |
| `DebilPrefix=K=` | префикс поиска «для чайников» |
| `PRRELATION=1`, `RelationMnu=relationr.mnu` | связанные документы |
| `FloatDebil=0`, `AutoDebil=0`, `UNIVERSALREADER=0`, `KeyService=1` | режимы упрощённого/универсального читателя; сервис ключей |
| `RETROLANDWSS=200R_R.wss`, `RETROLANDFLC=!200R_R`, `RETROLANDPFT=retrolandpft` | заказ по ретрофонду: РЛ, ФЛК, формат |
| `FULLTEXTABLE=1`, `STRONGREQUEST=0`, `REGISTRTIMER=15`, `DisplaySence=100` | доступность ПТ; контроль заказа; таймер регистрации; чувствительность показа |
| `MailHost/MailPort/MailFrom/MailFromAdress/MailSSL/MailOption` | почта (user/password опущены) |
| `mailbodyR=`, `mailsubjectR=` | шаблоны письма восстановления пароля (текст/тема) |
| `SHORTCUT_*` (~40) | горячие клавиши; `SHORTCUT_DISPLAYREQUESTMAINMENUITEM=P` (Заказ) — единственная заданная |

## `[SEARCH]`
`ItemNumb=23`. Структура как в каталогизаторе + доп. ключи: `ItemPft<n>` (формат элемента), `ItemExactly<n>` (точное соответствие), `ItemHint<n>` (заполнены подсказками).
Виды поиска (0..22): Ключевые слова `K=`(Logic=4), Автор `A=`(Adv=ATHRA), Рубрикатор `R=`(тип 2), Вид/Тип `V=`(vd.mnu), Характер `HD=`(hd.mnu), Заглавие `T=`, Коллектив `M=`(ATHRC), Предметные `S=`(ATHRS), Страна `C=`(str.mnu), Язык `J=`(jz.mnu), Год `G=`, Журнал за год `JR=`, УДК/ББК `U=`, Др.классификация `RIN=`, Издающая орг. `O=`, ISBN/ISSN `B=`, Дата ввода `DP=`, Дата поступления `DR=`, ВУЗ `VUZ=`, Автограф `F=`, Персоналия `P=`, Носитель `N=`(nos.mnu), Сигла `X=`(sigl.mnu).
Квалификаторы: `CvalifNumb=4`. Поиск по связи: `ScntNumb=8`. **Авторитетные (ключевое отличие Читателя): `IntNumb=5`** — `IntName/IntPref/IntType/IntAddata`:
| n | Назначение | Pref | Type | Addata |
|---|---|---|---|---|
| 0 | Тезаурус | K= | 1 | — |
| 1 | АФ Коллективные авторы | M= | 0 | athrc,M=,0,@athrcgrr |
| 2 | АФ Предметные заголовки | S= | 0 | athrs,S=,3,@athrsgrr |
| 3 | АФ Индивидуальные авторы | A= | 0 | athra,A=,1,@athragrr |
| 4 | АПУ к УДК | U= | 0 | athru,M=,4,@athrugrr |

Навигаторы: `WnNumb=9` (8 как у каталогизатора + Wn8 = Универсальный тематич. навигатор URUB). Хвост: `SeqSearch=1`, `DebilSearch=1`, `ComplSearch=1`, `DEFLEXKW=1`, `MORPHOLOGY=1`.

## `[Rubricator]`
Как в каталогизаторе + `RubTagPost=0` (метка ссылок постингов).

## `[Display]`
`MaxMarked=100`.

## `[Reader]` — параметры читательской БД (RDR)
`RdrDBN=RDR`, `RdrPrefReader=RI=`, `MaxRegistration=2`, **`MaxBooks=5`**, **`MaxDolgBooks=1`**, `ReaderAccess=1`, `RDRTAGREQUEST=40`, `RDRDELIM*` (SHIFR=A, INV=B, BRIEF=C, TIME1=D, RETURNDATE0=E, RETURNDATE1=F, DBNAME=G, BAR=H), `RDRPREFDOLGNIK=RB=`/`RDRPREFSHIFR=C=`/`RDRPREFBRIEF=N=`/`RDRPREFBAR=H=`, `RDRBRIEFFORMAT=RDR0`, `PRINTREQUEST=1`/`PRINTRQSTFORMAT=order`/`PRINTREQUESTCHECK=0`.
> Лимиты web-читателя (5/1) отличаются от АРМ Книговыдача (20/20) — см. ARM_LENDING.

## `[Request]` — параметры заказов (RQST)
`RqstDBN=RQST`, `RQSTTAGREADER=30`, `RQSTTAGRDRBRIEF=31`, `RQSTTAGBRIEF=201`, `RQSTTAGSHIFR=903`, `RQSTTAGTIME0=40`, `RQSTTAGTIME1=41`, `RQSTTAGRETURNDATE=42`, `RQSTTAGDBN=1`, `RQSTTAGDOP=100`, `RQSTTAGEKZ=910`, `RQSTTAGFREEEKZ=950`, `RQSTTAGNOTE=101`, `RQSTDELIM*` (INV=B, BAR=H, STORE=D, EKZNUMB=Z), `RQSTRDRPFT=RQSTRDR`, `RQSTPFT=RQST_HTML`.

## `[NAVIGATOR]`
`InitURL=IRBIS:3,0,,Irbis_Navigator_Help0.html` (стартовая — справка). Далее `PARNAME_*`, `MODTAG_*`, `TRMPORTION=100`, `SEARCHPORTION=20`, `NUMBFREEPAR=20`, `MAXHISTORYTITLELENGTH=80`, `FULLTEXTMorphology=0` — аналогично каталогизатору.
