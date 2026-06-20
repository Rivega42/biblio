# АРМ «Комплектатор» — разбор INI

Источник: `IRBISP.INI` → `_work\cfg_txt\IRBIS64__irbisp.ini.txt` (CP1251, 2907 строк — самый объёмный по логике закупок/КСУ/списания). Секций: **11**: `[MAIN]`, `[ENTRY]`, `[DISPLAY]`, `[FULLTEXT]`, `[POST]`, `[WS]`, `[PRIVATE]`, `[DESKTOP]`, `[CMPL]`, `[SEARCH]`, `[SEARCHCMP]`.

> ⚠ В `[MAIN]` — `LIBNETUSER`/`LIBNETPASSWORD` — значения НЕ переносятся.

## `[MAIN]`
| Группа | Смысл |
|---|---|
| `DBNNAMECAT`, `PftOpt`, `PftMnu=Pftpw.mnu`, `WsOpt`, `FmtMnu`, `TabMnu`, `IMPORT/EXPORT/COPYMNU` | меню/опции форматов |
| `NameCmpl=CMPL` | имя БД комплектования |
| `HLPFILE_K=irbisp.hlp`, `HLPFILE=irbisc.hlp` | помощь |
| `Access*` (~30) | права режимов: `AccessZakaz/Postup/Spisan/Podp/Move/Corr/Glob/Copy/LookLog`, мастера `AccessSpisMaster/ZakMaster/PostMaster`, статистика `AccessSpisStat`, импорт `AccessImpWeb/ImpZ/ImpLib`, `AccessLevel=0` |
| `Paperable=True`, `SetPrivate=0`, `SetPrivateCmpl=1`, `SetPrivateWSS=setprivc` | печать; приватные параметры |
| `WriteLog=1`, `LogFile=logcmpl.txt`, `MaxSizeLog=10000` | журналирование |
| `MODATHR*`, `DBEK1=IBIS`/`DBEK2=BOOK`, `PRRELATION=1` | авторитетные БД; БД ЭК для экземпляров; связи |
| `DefCopyFst=KPMK`, `DefCopyDbn=CMPL` | FST/БД копирования по умолчанию |
| `NameIZC=IZC.mnu`, `IZC_NumbDigits=4` | издательский каталог |
| `ProvFondTask=ProvFondN.gbl`, `MaxInvProvFond=10`, `ProvDelTask=Del910S`, `StatusProvFond=U,0,1,E` | проверка фонда: задание, лимит, статусы |
| `PrefSpis*` (TP=,TJ=,JR=,JM=,EXU=,G=) | префиксы словарей при списании |
| `SpisGbl*`+`*After` (~20 пар) | задания списания по сценариям + постредактура (`KUMUL909*`) |
| `StatusSpisInd=0,E,5,p`, `StatusNoSpis=1,2,3,4,6,8,9,R`, `StatusSpisGroup=U,C` | статусы экземпляров для списания индивид./групп./запрет |
| `CreateZakTask=CreateSZ`, `PrefZakBook30=NZZ=` | создание записи заказа |
| `RUSMARCFST/UNIMARCFST/USMARCFST`+`*GBL`, `ZIMPORT*`, `ImportMerge=0` | импорт MARC/Z |
| `LIBNET*` | ЛИБНЕТ (user/password — только имена) |
| `MAXINVENT=1`, `MAXIZD/MAXKSU/MAXKS2/MAXACTKSU/MAXACTKS2/MAXSZ=1` | ведение макс. значений нумерации (инв., орг., КСУ, акты, заказ) |
| `MaxExcelRows=1000`, `MaxSchPortion=100`, `MaxGlobPortion=20` | лимиты Excel/поиска/глобальной |
| `NJDelMove=1`, `AspDelMove=1` | включать номера журналов/статьи в Удаление-Перенос |
| `ModePostForZakaz=1`, `ModeEnterInCMPL=1`, `ModeZakPodb=1`, `ModeComplectator=0` | режимы: регистрация по заказу, ввод-перенос в CMPL, заказ из PODB |
| `IbisZAKINI=IbisMoveZak.ini`, `CMPLZAKINI=CmplZak.ini` | под-INI видов поиска в Мастере заказов |
| `NameDbnLog=LOGP`, `DbnWork=WORK`, `TagDbnList=1001` | БД протокола; рабочая БД для таблиц; метка имени справочника БД |

## `[ENTRY]` — ввод и КСУ
`PrefKsuCmplSpis=KS2=`, `MaxAddFields=10`, `DefFieldNumb=10`, `DbnFLC=DBNFLC`, `RECUPDIF=1`. Задания подписки: `NewPdpGbl`, `NewPdpgbl1/2`, `GroupPdpGbl`. Таблицы пополнения КСУ: `KsuFst1=rksu.fst`(+`Dop=rksuVUZ.fst`), `KsuFst2=rks2.fst`(выбытие+VUZ), `KsuFst3=itp.fst`(подписка), `KsuFst4=rsz.fst`(заказ); `FmtKsTotal=rKsuITG`. Префиксы КСУ: `PrefKsuP=NKSUK=`, `PrefKsuS=NKS2=`, `PrefKsuD=ITPK=`, `PrefKsuZ=SZK=`, `PrefKsuCat=NKSU=`, `PrefKsuCmpl=KSU=`; `PrefInv=IN=`, `PrefShifr=I=`; удаление `PrefForDel=V=DEL`. Метки: `TagMove=66`, `TagCopy=910`, `Tagdj=901`, `TagShifr=903`; разделители `DelimKsu=U`,`DelimInv=B`,`DelimBar=H`,`DelimStatus=A`,`DelimMhr=D`. РЛ создания: `WsZkNew/WsIzdNew/WsKsuNew/WsKs2New/WsKs3New/WsKs4New/WsOjkNew/WsAzpNew`, статистики `WsStaKsu1..4`, перенос `WsForMove=ToCat`. Заказ: `WssZakaz62=62zak`, `WsPolzv=POLZV`, `ValNoDone=ОБРНЗ`. Протокол в БД: `LogWsName=Log`, `LogWssShow=LogShowP`, `TagLog*` (Nmsg=60, Date=907, Text=300, Oper=200, ApplIdent=102).

## `[DISPLAY]`
Меню табличных форм по режимам: `TabMnuForZ`(заказ), `TabMnuForP`(подписка), `TabMnuForR=tabprwN.mnu`(поступление), `TabMnuForSIBIS/SCMPL`(списание ЭК/CMPL), `TabMnuForCat`. `FileSelTab=seltab64.par`, `FstToCat=Transn.fst`/`FstToCatJ`, лимиты показа (`MaxBriefPortion=3`, `MaxShowPortion=10`, `MaxInvProvDisplay=100`, `MaxInvSpisDisplay=1000`, `MaxZakInTree=100`, `MaxBookInTree=100`, `MaxInTab=1000`), `ListSort=1`.

## `[FULLTEXT]`
`PAGE0_BOOST=0`.

## `[POST]` — поступление/подписка по издательским каталогам
`NamePodpJ=POST`, `NamePodpB=PODB`, `PrefIP=IP=`, задания переноса `MoveKPgbl`, `MoveZakKpGbl`, `MoveNewKpGbl`, импорт/экспорт `ImpKpBook/ImpKpSerial/ExpKpBook`, РЛ `WsDefKp/WsDefKpSerial/WsZakPost=PostBr/WsZakPodb=PodbBr`, метки организации (`TagCodeOrg=30`, `DelimCodeOrg=K`, `DelimTextOrg=A`), форматы цены `CenaPftP/CenaPftZ`.

## `[WS]`
Размеры формы (`WsFormHeight=608`, `WsFormWidth=759`, `DISPLAYPANELHEIGHT=190`) и права: `Userable/Userable1/Deleteable/Clearable/KBVirtual1/2/DISPLAYABLE/WSMNUABLE=1`.

## `[PRIVATE]`
Значения оператора/состояния мастеров: `ETR=ДК`, `FIO=1`, `KSU=2018/4`, `EKP=IBIS`(БД каталога для словарей), `ELRES=IBIS`(эл.ресурсы), `DBNLIKE=IBIS`/`LinkFull=1`(похожие), геометрия форм мастеров, флаги `SpisAutoin/SpisFlc/SpisUpdif`, `MaxNumbNJ=100`, пары `PRPARNAME/PRPARVALUE1..9`.

## `[DESKTOP]`
`WsFormHeightMy=500`, `WsFormWidthMy=700`.

## `[CMPL]` — сценарии КСУ и списания в БД CMPL
РЛ опросов: `CMPLStatKsuWss=CC_StatKsuWss`, `CMPLSpisWss=CC_SpisWss`, `CMPLProvFondWss=CC_ProvFondWss`. Префиксы отбора: `PrefKsuCat=NKSU=`, `PrefKsuS=NKS2=`, `PrefKsuMOVE=NAP=`, `PrefKsuCmplSpisSelf=PKS2=`, `PrefKsuCmpl=KSU=`, `PrefSpisTitCat/PrefSpisTitJ/PrefSpisInvCat/PrefInv/PrefShifr/PrefSpisYearNJ`. Шаги КСУ поступления: `StatKsuStepNewBef/Bas/Aft`, пополнение `StatKsuStepUpdBef/Bas/Aft`. Шаги КСУ выбытия: `StatKs2StepBef/Step2/StepAft`, пополнение `StatKs2StepClearBef/UpdBas/UpdAft`. Списание: `SpisGblLostInv=SpisGblUT`, `SpisGblFile(+_Before)`, `SpisGblBAll/Binv/JAll/JNum/JYear`. Проверка фонда: `ProvFileUtf8=1`, `ProvFondStep1=Del910S`, `ProvFondStep2=provfondN`. Справочники: `TabMnu=CC_Tabw.MNU`, `TabTre=CC_Tabw.tre`; пакетный модуль `IrbisbatIni=irbisbat.ini`, `IrbisBatEXE=irbisBat_Plus.exe`.

## `[SEARCH]` — словарный поиск по каталогу
`ItemNumb=50`. Структура как в каталогизаторе. Виды: Ключевые `K=`, Автор `A=`(ATHRA), Рубрикатор `R=`, Заглавие/журналы/серии, Вид `V=`, Характер `HD=`, Целевое `CN=`, Носитель `N=`, ВУЗ `VUZ=`, Коллектив `M=`(ATHRC), Орг. `O=`, Предметные `S=`(ATHRS), Геогр. `GEO=`, экземплярные: Инв.№ `IN=`(`@dmodin`), `INK/EXU/INS/INSK`, Проверка фонда `INP=`, МХР `MHR=`, Коллекция `Coll=`, КСУ `NKSU/NKS2`, акт `NA=`. `CvalifNumb=4`; `ScntNumb=11`; `IntNumb=0`, `WnNumb=0`. Хвост: `SeqSearch=1`, `ComplSearch=1`, `MaxComplItem=15`.

## `[SEARCHCMP]` — комплексный поиск по БД комплектования (ключевая особенность)
Древовидный поиск по сущностям комплектования с переходом по связи и подстановкой во вторую область. Несколько НЕЗАВИСИМЫХ наборов элементов, различаемых суффиксом ключа:
| Набор | Ключ-счётчик | Сущность |
|---|---|---|
| Z | `ItemNumbZ=31` | Заказы (невыполненные/выполненные/организации/книги/дезидераты) |
| R | `ItemNumbR=28` | Поступление (КСУ, акты, источники, МХР, коллекции, РСУ, ИТОГОВАЯ КСУ) |
| S | `ItemNumbS=4` | Выбытие (КСУ выбытия, акты передачи, дата, период) |
| P | `ItemNumbP=12` | Подписка (издания, периоды, адресаты, каталоги) |
| DBN | `ItemNumbDbn=34` | Навигация по разделам |
| Pdp | `ItemNumbPdp=13` | Подписка из издательского каталога (PODB) |

Структура элемента (пример Z): `ItemNameZ<n>`(название/раздел `-`), `ItemPrefZ<n>`(префикс), `ItemIdentZ/IdentUpZ`(раздел), `ItemMenuZ`, `ItemSecondFmtZ<n>`(PFT запроса для 2-й области — переход по связи через `&uf/&unifor`), `ItemSecondNameZ<n>`(заголовок 2-й области), `ItemSecondShowZ<n>`(формат показа), `Item991Z<n>`(значение метки 991 — ключ связи), `ItemSecondExpTabZ<n>`(таблица экспорта `!TabZak/!TabKsu/!TabKO`). Аналогично — суффиксы R/S/P/DBN/Pdp. Это «поиск по связи» уровня АРМ Комплектатор (связки Заказ↔Книги, КСУ↔Документы, Организация↔Заказы, Дисциплина↔Книги для КО).
