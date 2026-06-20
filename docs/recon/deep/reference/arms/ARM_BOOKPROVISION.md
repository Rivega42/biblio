# АРМ «Книгообеспеченность» — разбор INI

Источник: `irbisk.ini` → `_work\cfg_txt\IRBIS64__irbisk.ini.txt` (CP1251, 3153 строки). Секций: **9**: `[MAIN]`, `[ENTRY]`, `[DISPLAY]`, `[USERMODE]`, `[PRIVATE]`, `[WS]`, `[SEARCH]`, `[SEARCHKO]`, `[DESKTOP]`.

> ⚠ В `[MAIN]` есть `MailUser`/`MailPassword` — значения НЕ переносятся.

## `[MAIN]`
Три рабочие БД: VUZ (учебные планы/контингент), RDR (студенты), каталог.
| Группа | Ключи |
|---|---|
| Совместимость | `Forcirbisini=cirbiscK.ini` |
| Форматы/меню КО | `PftMnu=PFTKOw.MNU`, `PftOpt=PFTKOw.OPT`, `WsOpt=ws52ko.opt`, `FmtMnu=FMT52ko.MNU`, `TabMnu=tabkow.mnu`, `GlobMnu=globKO.mnu`, `GlobMnuKO=globk.mnu` |
| Имена БД | `NameVUZ=VUZ`, `NameCMPL=CMPL`, `NameRDR=RDR`, `DATAPATH=.\dataI\` |
| Приватность | `SetPrivate=0`, `SetPrivateKO=1`, `SetPrivateWSS=setprivk` |
| Справочники контингента | `FilialMnu=Fili.mnu`, `NameFOMNU=fo.mnu`, `NameFAKMNU=fak.mnu`, `NameKafMnu=kafch.mnu`, `NameSpecMNU=Spec.mnu`, `NameNaprMNU=Napr.mnu`, `NameDiscMNU=Disc.mnu` |
| Права по базам | `AccessCorrVUZ/RDR/Cat`, `AccessCorrLt/Rt/Link`, `AccessGlob/SetMnu/Batch/Link/Move/Del/Print/Log/Set/Anal/Conv/Import`, `AccessRdr=1`, `AccessRDRTotal=1`, `AccessLevel=0`, `ReaderMode=0` |
| Связывание дисциплин/контингента | `WsAddNewCont=83K.wss`, `PftAddNewCont=VUZ84`, `TaskAddNewCont=vAdd83.gbl`, `TaskMoveKafDisc=LinkDisc.gbl`, `TaskDelSpec/TaskDelDisc/TaskDel83` |
| Расчёт ККО | `MetaQueryKO="!I=$"`, `PftForEkzKMI/PftForEkzCom`, `PftStatDisc=KoStatDisc`, `GetKkoBook=1`, `PftElectroName=KoElectro`, `DbNameForKKO=DbNameForKKO.mnu` |
| Рекомендация литературы | `RecomendRDR=!RdrBook`, `DiscForRDR=RdrDisc`, `AutoInFile=autoink.gbl` |
| Протокол/почта | `NameDbnLog=LOGP`, `EmailAble=1`, `EmailAdressPft=v32`, `MailHost/Port/From/FromAdress/SSL` (user/password опущены), `PassWordMD5=1` |
| Тексты/термины отчётов | `SpecInCylce`, `SpecInDisc`, `Spec-Prof`, `Vid_Obuch=Уровень подготовки` (переключаемые подписи Специальность/Профиль) |
| Импорт XML/Excel | `StartRecordXML=record`, `NameFieldXml=field`, `NameTagXML=tag`, `NameSubFieldXml=subfield`, `NameDelimXML=code`, `DefaultWsImp=Default_Imp.ws`, `NameListFldBrief=ListForConv.mnu` |
| Прочее | `MaxBriefForSort=5000`, `MaxPortionGlob=10`, `MaxStudDisplay=100`, `MaxTabPortion=1000`, `MaxAnalogMove=100`, `AutoClearSpaces=1`, `LimPftFull_boko691=10` |

## `[ENTRY]`
`RECUPDIF=1`, `DBNFLC=dbnflck`, `TabNumbTag=68`/`TabNumbDelim=Z`/`TabForNumb=!VUZNUMB` (нумерация контингента), `FirstFOinTree=Д/О`, `PrefVid=V=`, `PrefShifr=I=`, `ValElectro=ZU` (признак эл.ресурса). Импорт со слиянием: `MergeDbVuzgbl/wss/Sch`, `MergeDbRdrgbl/wss/Sch`. Протокол: `LogWsName=Log`, `LogWssShow=LogShowK`, `TagLog*`.

## `[DISPLAY]` — отчёты и таблицы (ядро КО)
Декодирование: `DeCodeSpec=1`, `DeCodeFak=1`, `MnuItemSpec/Fak`. Форматы частей: `KOPart2Pft=KoPart2`, `KOPart4Pft=KoPart4`, `KKOELECRES1=1`, `TextElecRes=(ЭУ)`. Отчёты-списки: `GRTabList1=KOLISTBOOKVO`, `GRTabList2=KOLISTBAS`, `GRTabList3=KOLISTEKZ`, `GRTabList4=KOPLAN`, `GRTabElectro=KoListElectro`+`GrTabListName1..4`. Суммарные: `GRTabStatSpec/StatDisc/StatFak/StatCyclFo`. Лицензирование: `GRTabPart1/Part11/Part2/Part3/Part4`, итоговые `GRTabItogCycl=KoItogCycleN`, `GRTabItogDisc=LicenDisc`, `GRTabKafDisc`. По VUZ: `GRTabVuz/VuzFull/VuzPolyDb`; по RDR: `GRTabRdr/RdrStat/RdrDolg1..4`. РЛ опросов: `GRWssList1..4`, `GRWssStat/StatFak/StatSN`, `GRWssPart1/Part24/Part4`, `GRWssVuz`, `GRWssRdr`. Справочники интерфейса: `SpravName1..13` (Формы/Виды обучения, Факультеты, Специальности/Профили, Направление, Кафедры чит./вып., Дисциплины, Цикл, Уровень комплекта, ВК, Идентификаторы ВК, Другие БД каталога). Цвета/новизна: `ColorAnalog=$800000`, `ColorNoSem=$80`, `StrgColor1..4`, `GRPart1YearNew=5`, `AfterPoint=2`. Похожие: `PftLikeThis=LikeThisKO`, `WssLike=!BOFullLink`.

## `[USERMODE]`
Закомментирована (шаблон DLL «Оформить заказ по ФП»): `UMNUMB`, `UMDLL0=KO_FP.dll`, `UMFUNCTION0=KO_ADD_FP`, `UMPFT0`, `UMNAME0`, `UMGROUP0`. Активных режимов нет.

## `[PRIVATE]`
`EKP=IBIS`, флаги вывода в ККО (`VidInKKO/FOInKKO/SemInKKO/SpecInKKO/NaprInKKO/FakInKKO=1`), управление расчётом (`PrModeCalcKKO=1`, `PrAskCalcKKO=0`, `AnalogElRes=1`, `LinkCatalogRdr=1`), показ аналогов/ЭУ (`ShowAnalog=1`, `ShowElectro=1`, `ShowNoCurrentSem=1`), геометрия панелей, похожие (`DBNLike=podb`, `LinkFull=1`), `FIO=1`, пары `PRPARNAME/VALUE1..9`.

## `[WS]` — права рабочих листов по базам
Раздельно для VUZ/каталога/RDR: `NewableVuz=1`/`NewableCat=0`/`NewableRdr=0` (контингент правится, каталог и студенты в режиме чтения), `Deleteable*`, `Clearable*`, `Userable=1`, `KBVirtual1/2=1`, `DISPLAYABLE/WSMNUABLE=1`, `MfnRecord=1`, `DBN=IBIS`, геометрия.

## `[SEARCH]` — словарный поиск по каталогу
`ItemNumb=22`. Виды: Заглавие `T=`, Автор `A=`, Год `G=`, Инв.№ `IN=`, МХР `MHR=`, **Факультет `FAK=`, Специальность/Профиль, Направление, Дисциплина, Кафедра читающая, Цикл, Вид/Форма обучения** (специфика КО), Вид `V=`, Характер `HD=`, Целевое `CN=`, Носитель `N=`, УДК/ББК `U=`, Др.классификация `RIN=`, Раздел знаний `RZN=`, Шифр `I=`, Ключевые `K=`. `ScntNumb=11`, `IntNumb=0`, `WnNumb=8`. Хвост: `SeqSearch=1`, `ComplSearch=1`, `MaxComplItem=0`.

## `[SEARCHKO]` — поиск/связывание по книгообеспеченности (ключевая, ~2150 строк)
Главный механизм АРМа: поиск по контингенту/дисциплинам с одновременным переходом по трём БД (VUZ ↔ RDR ↔ Каталог) и расчётом ККО. `ItemNumb=27`. Структура элемента — расширенная, с ветвлением по целевой БД (Vuz/Rdr/Cat) и вторичной области:
| Ключ | Смысл |
|---|---|
| `ItemName<n>`/`ItemPref<n>` | название / префикс словаря (`DISCN=`,`DFAK=`,`VFAK=`,`!`для контингента) |
| `ItemTab<n>` | таблица первичной области (`!VUZ`,`!discN`) |
| `ItemFstVuz/Rdr/Cat<n>` | FST первичного отбора в соотв. БД |
| `ItemGlobVuz/Rdr/Cat<n>` | GBL-задание (`Move83`,`Move691`,`MergeDisc`) |
| `ItemSecSch<n>` | формат запроса для вторичной области |
| `ItemSecName<n>` | заголовок вторичной области |
| `ItemSecShow<n>`/`ItemSecTab<n>` | формат показа / таблица |
| `ItemSec991<n>` | значение метки 991 (ключ связи) |
| `ItemSecFstVuz/Rdr/Cat<n>`, `ItemSecGlobVuz/Rdr/Cat<n>` | FST/GBL вторичной области по каждой БД |
| `ItemSecSchRdr/Cat/Vuz<n>`, `ItemSecNameRdr/Cat<n>`, `ItemSecTabRdr/Cat<n>`, `ItemSec991Rdr/Cat<n>` | ветви перехода Студенты/Книги/Контингент |
| `ItemSecTabCatSum<n>` | таблица суммарных ККО по каталогу (`!boko`,`!bokodisc`) |
| `ItemSecTabSemPft/Val<n>`, `ItemTabNumb<n>`, `ItemDelim<n>`/`ItemDelimVal<n>` | семестровая раскладка и нумерация столбцов |

Виды поиска (выборка из 27): Дисциплина-читается `DISCN=`, Контингент (Фак-Напр-Спец-ВО-ФО-Сем) `!`, Факультет `DFAK=`, Факультет-специальность-контингент `VFAK=`, Кафедра читающая, Специальность/Профиль, Направление, Цикл, Форма/Вид обучения, Рабочая программа (наименование/идентификатор/дата окончания/архив), Семестр, Курс, Кафедра-дисциплины-контингент, Контингент-дисциплины-книги, Факультет-филиал, Дисциплины филиала, Дисциплина→перенос в учебники, Дисциплина→учебники по типу и РП, Обновлённые дисциплины, Идентификатор дисциплин, Вид документа.

## `[DESKTOP]`
Геометрия рабочего стола пользователя.
