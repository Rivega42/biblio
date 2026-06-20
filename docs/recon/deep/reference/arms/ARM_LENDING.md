# АРМ «Книговыдача» — разбор INI

Источник: `IRBISB.INI` → `_work\cfg_txt\IRBIS64__irbisb.ini.txt` (CP1251, 336 строк). Секций: **8**: `[Main]`, `[Search]`, `[Display]`, `[Reader]`, `[Request]`, `[WS]`, `[PRIVATE]`, `[FULLTEXT]`.

> ⚠ В `[Main]` — `MailUser`/`MailPassword`; `RFID_UNI_ADDRESS=127.0.0.1` (IP RFID) — значения НЕ переносятся.

## `[Main]`
| Ключ | Смысл |
|---|---|
| `CLIENT_TIME_LIVE=15`, `DBNNAMECAT=dbnam3.mnu`, `HLPFILE=irbisb.hlp` | тайм-аут; меню БД; помощь |
| `MaxCont=5` | макс. контингентов |
| `TagFullText=951`, `TagImage=950`, `TagVid=920`, `SerVid=J` | метки полей |
| `DBNPREFSHIFR=I=`, `DBNTAGEKZ=910`, `DBNTAGSHIFR=903`, `DBNTAGSPROS=999` | префикс/метки шифра, экземпляра, спроса |
| `DBNDELIM*` (STATUS=A,INV=B,BAR=H,STORE=D,WINV1=1,WINV2=2), `DBNFREEEKZ=0`, `DBNWINVEKZ=U` | разборка экземпляра |
| `BriefPft=BRIEF`, `DefaultDB=IBIS`, `OptionAble=1`, `MULTIVISIT=1` | краткий формат; БД; настройки; множественные посещения |
| `PRRFID=0`, `RFIDTYPE=4`, `RFID_ANTIVOR_*`, `RFID_SKYE_*`, `RFID_UNI_*` (`INTERVAL`,`UID`,`ADDRESS`(IP),`PORT=6001`), `ConfirmMultiRFID=1` | RFID-оборудование: тип (4=универсальное серверное), интервалы, адрес/порт |
| `AutoLand=1`, `ReservMode=1` | автовыдача; режим брони |
| `BarComIn/BarComOut`, `BARINMODE=1`, `ReaderBarCode=`, `BARCODERELATION=2` | штрих-кодирование |
| `OTVFACE=1`, `PROTVFACE=0` | интерфейс выдачи/возврата |
| `MailHost/MailPort/MailFrom/MailFromAdress/MailSSL/MailOption` | почта (user/password опущены) |
| `PRMHRKV=0`, `MHRKVMNU=mhrkv.mnu`, `KVMNU=kv.mnu`, `MHRMNU=mhr.mnu` | места хранения/квоты |
| `REQUESTNEWEKZABLE=1`, `LANDFORMAT=brief` | заказ нового экземпляра; формат выдачи |
| `RETROLANDWSS=200r.wss`, `RETROLANDFLC=!200r`, `NEWEKZWSS=910.wss`, `NEWEKZFLC=!910` | ретрофонд/новый экз.: РЛ + ФЛК |
| `RETURNABLE/RETURNTORESERVABLE/LANDABLE/RETROLANDABLE/PROLONGABLE/RETURNDELETEABLE/REQUESTABLE/REQUESTRESERVABLE/REQUESTDELETEABLE/PEREREGABLE=1` | разрешения операций книговыдачи |
| `UpdateLock=1`, `AutoinFile=autoin_light.gbl` | блокировка при обновлении; автоввод (light) |
| `URLForIrbisNavigator`, `ClientIniForIrbisNavigator=Irbis_Navigator.ini` | навигатор |
| `PAYABLE=1`, `PAYDBN=PAY`, `PAYTALONPFT=talon` | платные услуги: БД, формат талона |
| `IRIABLE=1`, `RECUPDIF=1`, `RECOMENDPFT=recomend`, `BLINDABLE=1` | ИРИ; актуализация; рекомендации; режим для слабовидящих |
| `ReservMail=1`, `ReservMailPft=ReservMail`, `ReservMailAsk=1`, `RESERVSTATUSMAIL=1`, `OTKAZMAIL=1` | почтовые уведомления о брони/статусе/отказе |
| `VISITMNU=visit.mnu`, `GUESTVISIT=1` | учёт посещений; гостевое |
| `ANALOGPFT=rel_content`, `STRONGPROLONG=1` | аналоги; жёсткое продление |
| `PftMnu=PFTw.MNU`, `FmtMnu=FMT31.MNU`, `TabMnu=tabw.mnu`, `PftOpt=PFTw_H.OPT`, `WsOpt=WS31.OPT` | меню форматов/опций |
| `OperHint=1`, `OperHintPft=operhintb`, `OPERSTATPFT=operstat` | оперативные подсказки/статистика |
| `RDRENTRY/RQSTENTRY/DBNENTRY=1`, `RDREDIT/DBNEDIT/RQSTEDIT=1` | права ввода/правки RDR/RQST/DBN |
| `MAXHISTORYCOUNT=15`, `MAXCICLE=10`, `PASSWORDMD5=0`, `MAXREPEAT=5000`, `MAXDOCSEARCH=5000` | история; циклы; хеш; лимиты |

## `[Search]`
`ItemNumb=7`, `MinLKeyWord=4`. Упрощённая структура: Шифр `I=`, Штрих-код/Инв.№ `IN=`(Exactly=1), Автор `A=`, Заглавие `T=`, Заглавие-журналы `TJ=`(Exactly=2), Краткое описание ИМИДЖ `AA=`, Слова распознанного текста `KT=`.

## `[Display]`
`MaxMarked=100`, `MaxBriefPortion=5`.

## `[Reader]` — основная для книговыдачи
Общие ключи (RdrDBN, RDRTAG*, RDRDELIM*, RDRPREF* — как у Читателя) + специфика выдачи:
| Ключ | Смысл |
|---|---|
| `RdrPftMnu=DOLGW.MNU` | меню форматов читателя (должники) |
| `ReaderHistory=0`, `MaxHistory=75` | история выдач; глубина |
| `MaxReturnDays=20`, `ReturnDaysMnu=return.mnu` | срок возврата; меню сроков |
| `RDRBRIEFFORMAT=RDR0W_HTML`, `RDRTODAYFORMAT=rdrw_html_dolg2a` | HTML-форматы читателя |
| `F8RETURN=!f8ret` | формат F8 для возврата |
| **`MaxBooks=20`, `MaxDolgBooks=20`** | лимиты книг/должников (АРМ ≠ web 5/1) |
| `STRONGRETURN=0`, `STRONGDISPLAY=0`, `READERACCESS=1` | жёсткие режимы; доступ |
| `ReaderDopInfoPft`, `BorrowDopInfoPft`, `MULTIBOOKS=0`, `MAXPROLONGCOUNT=5`, `SORTMNU=sort.mnu` | доп.информация; множественная выдача; макс. продлений |
| **`ItemNumb=15`** — словарь видов поиска по RDR | Читатели `RI=`, Держатели `RB=`, шифр выданной `C=`, название `N=`, штрих-код `H=`, выдач `DV=`, возвратов `DW=`, посещаемость `VS=`, утерянные `HU=`, отриц.баланс `S-=`, в библиотеке `VIS=`, пользователи ИРИ `IRI=`, профили ИРИ `RIP=`, категория `KAT=`, посещаемость за год `PRG=` |

## `[Request]` — заказы (+ для книговыдачи)
Метки/разделители RQST* — как у Читателя + `UnservedSortKey=3`, `RQSTTALONPFT=cntrlW_html`, `RQSTPFTMNU=pftw.mnu`, `RQSTFULL=0`, `Mask*` (Mrg/Dbn/Reader/Shifr/Inv/Bar/Store=`*`), `Autoask=60`, `OTKAZMNU=otkaz.mnu`, `ReservStatusMnu1..3`, `RqstDopInfoPft`. **`ItemNumb=9`** — словарь поиска по заказам: невыполненные `RI=`, бронь `RB=`, все `RZ=`, шифр `IZ=`, дата `DZ=`, распечатанные `P0=`, статус брони `VBS=`, выполненные `RS=`, отказы `RO=`.

## `[WS]`
`Deleteable=1`, `Clearable=1`, `KBVirtual1/2=1`, `DISPLAYABLE=1`, `WSMNUABLE=1`.

## `[PRIVATE]`
`FIO=1` (только идентификатор оператора).

## `[FULLTEXT]`
`JPG_PAGES_IN_CASH_DPI=200`.
