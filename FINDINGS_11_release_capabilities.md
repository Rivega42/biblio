# FINDINGS 11 — Каталог возможностей (по истории выпусков)

Источник: RELEASE_OVERALL.doc (txt:СТРОКА). Документ — сводные примечания к выпускам САБ ИРБИС64+. Охват по версиям: от 2002.2 (RELEASE_OVERALL.doc (txt:9757)) до 2021.1 (RELEASE_OVERALL.doc (txt:2)); хронология от новых версий к старым. Каталог сгруппирован по областям (не пересказ версий). Цитаты указывают на репрезентативную строку появления возможности.

---

## Сервер и протокол

- Запуск сервера в режиме приложения; режим ПРОВЕРКА ПРАВ ДОСТУПА на полные права к папке IRBIS64 — RELEASE_OVERALL.doc (txt:323).
- Отказ от монопольной блокировки при редактировании/актуализации, распараллеливание; фрагментация файла документов MST_NUM_FRAGMENTS — RELEASE_OVERALL.doc (txt:3024).
- Журналирование действий сервера LogActionsToFile — RELEASE_OVERALL.doc (txt:3032); сохранение/восстановление клиентов SAVE_CLIENTS_WHILE_STOP — RELEASE_OVERALL.doc (txt:3035).
- Оптимизация: BlockingTimeoutInMS, ALL_PROCESS_MONITOR, PROCESS_TIME_LIVE_FAST — RELEASE_OVERALL.doc (txt:3039); контроль повторного запуска АРМа Check_ARMLoginIP — RELEASE_OVERALL.doc (txt:3048); до 3 доп. портов IP_PORT1..3 — RELEASE_OVERALL.doc (txt:3055).
- Контроль скорости сети THREAD_TIME_LIVE — RELEASE_OVERALL.doc (txt:4241); REDIRECT-запросы [AllowRedirect], AllowRedirectAll, Count — RELEASE_OVERALL.doc (txt:4245).
- TCP/IP сервер: прерывание процесса и возврат накопленного результата — RELEASE_OVERALL.doc (txt:5263); вложенность серверных ini — RELEASE_OVERALL.doc (txt:6951); автослияние версий записи AutoMerge — RELEASE_OVERALL.doc (txt:6813).
- TCP/IP сервер БД ИРБИС64 с профилями CLIENT_INI.MNU — RELEASE_OVERALL.doc (txt:7639); межбиблиотечный обмен через ИРБИС TCP/IP сервер — RELEASE_OVERALL.doc (txt:2035).
- Работа в *NIX (Debian) для J-ИРБИС 2.0 (импортозамещение) — RELEASE_OVERALL.doc (txt:350); поддержка HTTPS — RELEASE_OVERALL.doc (txt:351).

## АРМ Каталогизатор

- Полнотекстовый поиск на основе ИРБИС-Навигатора — RELEASE_OVERALL.doc (txt:7).
- Протоколирование действий клиента в БД LOGC; LOGC= в [MAIN]; форма LOGC0, чистка DelDate — RELEASE_OVERALL.doc (txt:8).
- Печать на E-mail (2/e-mail/subject); формат optim_h_iri.pft, параметр PATHTOCGIIRBIS — RELEASE_OVERALL.doc (txt:39).
- Удаление постоянных запросов DELETEIRIMNU= — RELEASE_OVERALL.doc (txt:45); постоянные запросы в разделе ПОИСК — RELEASE_OVERALL.doc (txt:3338).
- Шифрование пароля читателя MD5 в поле 130; PASSWORDMD5=; autoin.gbl, PassWord130.gbl — RELEASE_OVERALL.doc (txt:54).
- Стат.формы: контроль гориз./верт. — RELEASE_OVERALL.doc (txt:76); СТАТИСТИКА с опросными листами STTWSSMNU= — RELEASE_OVERALL.doc (txt:87); HTML без Excel STFHTML= — RELEASE_OVERALL.doc (txt:777); диаграммы PIE/BAR — RELEASE_OVERALL.doc (txt:1660); двухмерные стат.формы — RELEASE_OVERALL.doc (txt:7530).
- Отключение сообщений при корректировке найденных NOVINKA= — RELEASE_OVERALL.doc (txt:365).
- Оперативный режим ВЫПОЛНИТЬ ПАКЕТНОЕ ЗАДАНИЕ по формату; вложенные задания @<формат> — RELEASE_OVERALL.doc (txt:2107); REFRESHDB — RELEASE_OVERALL.doc (txt:2111); автозапуск BATCHFILE — RELEASE_OVERALL.doc (txt:1220); справочник BATCHMNU/BATCHABLE — RELEASE_OVERALL.doc (txt:3228); переменные параметры %N — RELEASE_OVERALL.doc (txt:3211).
- Последовательный поиск: только удалённые, НЕ СОДЕРЖИТ — RELEASE_OVERALL.doc (txt:771); ВСЕ повторения — RELEASE_OVERALL.doc (txt:8394).
- Предотбор документов в WSS через свойство ПРЕФИКС ДЛЯ ПОИСКА — RELEASE_OVERALL.doc (txt:776).
- Групповая отметка коротких описаний по Shift — RELEASE_OVERALL.doc (txt:787).
- Переключатель ОПЕРАТИВНЫХ РЕЖИМОВ (СЕРВИС) — RELEASE_OVERALL.doc (txt:789); расположение кнопок HINTTOOLBAR= — RELEASE_OVERALL.doc (txt:801).
- Подробная история корректировок в поле 907 (^X) FULL907=1; формат full907.pft — RELEASE_OVERALL.doc (txt:791).
- Динамический РЛ подполей (метод ввода 18, .PFT) — RELEASE_OVERALL.doc (txt:797); динамический РЛ полей AUTOWSPFT/PRAUTOWS — RELEASE_OVERALL.doc (txt:816); метод ввода 17 на лету — RELEASE_OVERALL.doc (txt:1618).
- ЧИСТКА ПРОБЕЛОВ AUTOCLEARSPACES, исключения NotClearSpacesMnu= — RELEASE_OVERALL.doc (txt:806).
- Метод ввода 16 — файловые ресурсы сервера PUTFILEABLE — RELEASE_OVERALL.doc (txt:1637) / RELEASE_OVERALL.doc (txt:3341).
- Иерархические справочники TRE; ItemIdentN, ItemIdentUpN — RELEASE_OVERALL.doc (txt:1207).
- Произвольные оперативные режимы: команды 4, 5, 10–109 — RELEASE_OVERALL.doc (txt:3304); MAXBINRESOURCE — RELEASE_OVERALL.doc (txt:3336).
- Глобальные счётчики: БД COUNT, форматный выход uf ++C — RELEASE_OVERALL.doc (txt:2551).
- Технология КАРМАНОВ — RELEASE_OVERALL.doc (txt:5500); СРАВНИТЬ буфер/текущую — RELEASE_OVERALL.doc (txt:6815); БУФЕРНАЯ ЗАПИСЬ (COPY/VIEW/PASTE) — RELEASE_OVERALL.doc (txt:9040).
- Заимствование/импорт со СЛИЯНИЕМ ImportMerge=1, в одно касание ImportOneTouch=1 — RELEASE_OVERALL.doc (txt:5539); сохранение контекста CREATEINITCONTEXT — RELEASE_OVERALL.doc (txt:5545).
- Орфоконтроль (словарь MS Word) + CUSTOMDICT — RELEASE_OVERALL.doc (txt:8391).
- Глоб. корректировка: операторы UNDEL, ALL, EMPTY, CHAC; протокол в файл — RELEASE_OVERALL.doc (txt:9048).
- Редактор форматов GenPft64.exe: монитор глоб. переменных — RELEASE_OVERALL.doc (txt:621), шаблоны Alt-N — RELEASE_OVERALL.doc (txt:649), синтаксический контроль — RELEASE_OVERALL.doc (txt:664).

## АРМ Книговыдача / МБА

- Рассылка ИРИ HTML в тело/вложением MAILOPTION= — RELEASE_OVERALL.doc (txt:99); авто-ИРИ AUTOIRI=1 — RELEASE_OVERALL.doc (txt:1285); формат темы/тела IriMailPft — RELEASE_OVERALL.doc (txt:2369).
- Формирование ЗАКАЗА для текущего читателя CreateRqst= — RELEASE_OVERALL.doc (txt:101).
- Книговыдача-Лайт BL_READER_FULL — RELEASE_OVERALL.doc (txt:372); Книговыдача-Самообслуживание RS_READER_PROLONG/RS_READER_FULL — RELEASE_OVERALL.doc (txt:386).
- Чекбоксы рассылки при бронировании/отказе (RESERVMAIL, RESERVSTATUSMAIL, OTKAZMAIL) — RELEASE_OVERALL.doc (txt:396).
- Контроль по ВОЗРАСТНОМУ ОГРАНИЧЕНИЮ: год рождения (поле 21 RDR), подполе 900^Z (NN+) — RELEASE_OVERALL.doc (txt:405).
- МНОГОЭКЗЕМПЛЯРНАЯ КНИГОВЫДАЧА MULTIEKZ=1 — RELEASE_OVERALL.doc (txt:409).
- Таблицы: печать/сохранение в HTML и CSV — RELEASE_OVERALL.doc (txt:428).
- Звуковой сигнал новых заказов rington3.wav; RQSTNEWBEEP — RELEASE_OVERALL.doc (txt:439).
- ПЕРЕАДРЕСАЦИЯ заказа на издание-аналог ANALOGPFT — RELEASE_OVERALL.doc (txt:440).
- ГРУППОВОЕ ОБСЛУЖИВАНИЕ ОДНИМ ЭКЗЕМПЛЯРОМ — RELEASE_OVERALL.doc (txt:828); ЗАФИКСИРОВАТЬ ГРУППОВОЕ ПОСЕЩЕНИЕ — RELEASE_OVERALL.doc (txt:2645).
- Скоростная идентификация по радиометке/штрихкоду — RELEASE_OVERALL.doc (txt:835); скоростная книговыдача RFID AUTOLAND — RELEASE_OVERALL.doc (txt:7596).
- Сортировка отбора по словарям RDR SORTMNU= — RELEASE_OVERALL.doc (txt:840).
- ПРАВО ПОЛЬЗОВАНИЯ на основе формата ReaderRightsPft/RDRTAGRIGHTS; ИН/ШК через модельное поле 1001 — RELEASE_OVERALL.doc (txt:854) / RELEASE_OVERALL.doc (txt:9508).
- ПЕРЕРЕГИСТРАЦИЯ/ГРУППОВАЯ ПЕРЕРЕГИСТРАЦИЯ PEREREGABLE= — RELEASE_OVERALL.doc (txt:856).
- Право обслуживания: поля 29, 56, 57; RIGHTSWSS, RIGHTSABLE — RELEASE_OVERALL.doc (txt:2642); MAXBOOKS, MAXDOLGBOOKS — RELEASE_OVERALL.doc (txt:7851).
- ОПЕРАТИВНАЯ СТАТИСТИКА OPERSTAT.PFT — RELEASE_OVERALL.doc (txt:1280); статистика посещений по сеансам обслуживания uf ++B — RELEASE_OVERALL.doc (txt:2670); по местам выдачи — RELEASE_OVERALL.doc (txt:7856).
- Бронеполка: статус забронирован (9), RESERVMODE, RETURNTORESERVABLE, REQUESTRESERVABLE, ReservStatusMnu1..3 — RELEASE_OVERALL.doc (txt:7289) / RELEASE_OVERALL.doc (txt:5563).
- Выдача вслепую — RELEASE_OVERALL.doc (txt:5607); автоввод ШК/RFID AUTOIN_RFID_BARCODE=1 — RELEASE_OVERALL.doc (txt:5623); подтверждение группового чтения меток ConfirmMultiRFID=1 — RELEASE_OVERALL.doc (txt:5616).
- ОФОРМЛЕНИЕ ОТКАЗОВ (поле 44) — RELEASE_OVERALL.doc (txt:5557); пометка заказов как распечатанных — RELEASE_OVERALL.doc (txt:5561).
- Подсистема ИРИ (профили в поле 140 RDR) — RELEASE_OVERALL.doc (txt:5434); УЧЁТ УСЛУГ PAYDELETE/PAYLIST/PAYREORG — RELEASE_OVERALL.doc (txt:1313).
- Максимум продлений MAXPROLONGCOUNT (счётчик 40^4) — RELEASE_OVERALL.doc (txt:1725); спец-продление SPECPROLONG — RELEASE_OVERALL.doc (txt:2649).
- Распределённая БД читателей корпорации REDIRECT, MULTIRDRMNU — RELEASE_OVERALL.doc (txt:3903).
- ВЫДАЧА БЕЗ ЭК — RELEASE_OVERALL.doc (txt:9506).

## АРМ Комплектатор

- Заявка-Заказ-Поступление: статус заявки, словари по идентификатору/дате, подполя поля 62 в ЭК и CMPL — RELEASE_OVERALL.doc (txt:118).
- Таблицы интерфейса: 0-й столбец-номер, фильтрация/сортировка колонок — RELEASE_OVERALL.doc (txt:134).
- Статус Сетевой локальный ресурс (E) в STW.mnu, STE.mnu — RELEASE_OVERALL.doc (txt:149).
- Списание по файлу ИН/ШК: MaxInvSpisDisplay, постредактура SpisGbl*After — RELEASE_OVERALL.doc (txt:155); предпросмотр SpisFileShowInTab — RELEASE_OVERALL.doc (txt:2706); отметка по файлу-списку — RELEASE_OVERALL.doc (txt:175).
- Списание журналов по году-месту хранения, по комплектам/номерам — RELEASE_OVERALL.doc (txt:177); единое место хранения — RELEASE_OVERALL.doc (txt:1000).
- КСУ: поля 44, 744, 147–151; имена БД пополнения в поле 21 — RELEASE_OVERALL.doc (txt:443) / RELEASE_OVERALL.doc (txt:864); итоговая КСУ сбором по БД каталога (SchTotal, формат RksuITG) — RELEASE_OVERALL.doc (txt:883).
- Протокол в БД NameDbnLog= (РЛ LOG) — RELEASE_OVERALL.doc (txt:468); задания списания в UTF-8 — RELEASE_OVERALL.doc (txt:486).
- Сетевые удалённые ресурсы (РСУ): РЛ кода RSU, поле 951 (НРСУ, даты, RD4.mnu), реестр 881^A/E/F/P/W — RELEASE_OVERALL.doc (txt:895); продление ProLongNet, архив поля 942 — RELEASE_OVERALL.doc (txt:923).
- Выходные формы: ListInvKsu, TksuFull, TJ_PostNUM, TJ_PostMHR, TJ_nopost, KS2RZN, TksuMHR — RELEASE_OVERALL.doc (txt:144) / RELEASE_OVERALL.doc (txt:494) / RELEASE_OVERALL.doc (txt:957).
- Многотомники: формат PftVolYest, таблицы переноса KPM.fst/KPMK.fst/MNOG.fst — RELEASE_OVERALL.doc (txt:1786).
- Проверка дублетности по свёртке PftDublInCat/svertkaCMPL — RELEASE_OVERALL.doc (txt:1810) / RELEASE_OVERALL.doc (txt:2771).
- Модели макс. инвентарного номера ModeInvent, ModeInvent1..5; разрядность до 2^63-1 — RELEASE_OVERALL.doc (txt:1768) / RELEASE_OVERALL.doc (txt:2777).
- Заимствование из ЛИБНЕТ/WEB/Z39.50 AccessImpWeb/AccessImpZ/AccessImpLib — RELEASE_OVERALL.doc (txt:1436).
- Проверка фонда StatusProvFond; быстрая проверка по ИН/ШК — RELEASE_OVERALL.doc (txt:1438); результат в новый файл с _ — RELEASE_OVERALL.doc (txt:2785).
- Прайс-листы из Excel в издательские БД NameListFldPodb=IZDAT.mnu — RELEASE_OVERALL.doc (txt:2752); БД издательского каталога PODB, подписки POST — RELEASE_OVERALL.doc (txt:9903).
- Суммарный заказ (СЗ): РЛ SZ, поле 62, поле 907 (этапы 907s.mnu) — RELEASE_OVERALL.doc (txt:9321); технология аукционов/тендеров (ФЗ №94) — RELEASE_OVERALL.doc (txt:6698).
- Несколько актов ИУ в одной партии КСУ (поле 88, Cena.gbl) — RELEASE_OVERALL.doc (txt:9886).
- Интеграция ИРБИС-ПАРУС (экспорт КСУ в бухгалтерию) — RELEASE_OVERALL.doc (txt:7143).

## АРМ Книгообеспеченность

- Отчёт ККО для текущего семестра с порогом ККО — RELEASE_OVERALL.doc (txt:191); Только электронные учебники? — RELEASE_OVERALL.doc (txt:3432); пропорционально студентам — RELEASE_OVERALL.doc (txt:4050).
- РЛ заявки 694ko.wss: идентификатор/дата заявки — RELEASE_OVERALL.doc (txt:195); перенос контингента Move691.gbl — RELEASE_OVERALL.doc (txt:196).
- Отчёт Дисциплины с электронными ресурсами: поля 951/955, права через БД RIGHT и 3C.mnu/3A.mnu — RELEASE_OVERALL.doc (txt:202).
- Вид поиска Держатели литературы в RDR, таблица Dolg.wss (экспорт txt/xls/csv) — RELEASE_OVERALL.doc (txt:212).
- Замена кодов специальностей: RepCNA, RepRDR, RepWithMnu, kns.mnu — RELEASE_OVERALL.doc (txt:216).
- Привязка/открепление учебников к рабочим программам: MoveWPCat, Move691, AddWPCat, vDEL691, признак 691^5 — RELEASE_OVERALL.doc (txt:522) / RELEASE_OVERALL.doc (txt:2921).
- Статистика книговыдачи GRTabRdrStat=KoStat по курсам/категориям (KTG.mnu) — RELEASE_OVERALL.doc (txt:561).
- Протоколы заданий в БД NameDbnLog=LOGP — RELEASE_OVERALL.doc (txt:567); рассылка по E-mail EmailAble, EmailAdressPft — RELEASE_OVERALL.doc (txt:587).
- Импорт-Обновление БД VUZ: дописывание/полное обновление контингентов, архив 832/943 — RELEASE_OVERALL.doc (txt:1014); импорт студентов из XML/XLS/CSV — RELEASE_OVERALL.doc (txt:2880).
- Подключение доп. БД каталога к таблицам ADDDBN, AddDbnListName — RELEASE_OVERALL.doc (txt:4095) / RELEASE_OVERALL.doc (txt:4139).
- Расчёт обеспеченности GetKkoBook (экземпляры или ККО из поля 693) — RELEASE_OVERALL.doc (txt:3422); КМИ — RELEASE_OVERALL.doc (txt:6640).
- Аналоги взаимозаменяемых учебников (поле 699) — RELEASE_OVERALL.doc (txt:6926); для электронного аналога ККО=1 AnalogElRes=1 — RELEASE_OVERALL.doc (txt:2789).
- Интегрированный вариант КО (УНД, НУП) — БД VUZ, инициализация IRBISCKO.INI — RELEASE_OVERALL.doc (txt:9842).

## АРМ Администратор

- Клиент: доп. информация о полнотекстовой части БД — RELEASE_OVERALL.doc (txt:229); печать на E-mail — RELEASE_OVERALL.doc (txt:233).
- Авторизация по учётной записи Windows USERNAME=! — RELEASE_OVERALL.doc (txt:1529).
- Серверный: ЭКСПОРТ БД ДЛЯ ПЕРЕНОСА В НОВУЮ ВЕРСИЮ (TXT без ТВП, сохранение GUID) — RELEASE_OVERALL.doc (txt:236).
- Актуализация-СОЗДАТЬ СЛОВАРЬ ЗАНОВО ТОЛЬКО ЭК; команда LOADIFCOMPLETE_EK — RELEASE_OVERALL.doc (txt:614).
- НОВАЯ БД ПО ОБРАЗЦУ (NEWDB) — RELEASE_OVERALL.doc (txt:2952); сортировка списка БД SORTDBLIST — RELEASE_OVERALL.doc (txt:2968).
- РЕОРГАНИЗАЦИЯ ФАЙЛА ДОКУМЕНТОВ с физическим исключением удалённых (сдвиг MFN) — RELEASE_OVERALL.doc (txt:3527).
- Многопроцессорное создание словаря MULTILOAD, MULTISORT; LOCKDB — RELEASE_OVERALL.doc (txt:4162) / RELEASE_OVERALL.doc (txt:4754); ISO по последним копиям MST — RELEASE_OVERALL.doc (txt:4776).
- Команды заданий: SEARCH, PRINT, STAT, STATF, GLOBAL, DIAGNOSMF, DIAGNOSIF, UNLOCKRECORDALL, SILENCE, EXIT — RELEASE_OVERALL.doc (txt:4166) / RELEASE_OVERALL.doc (txt:5783).
- Log-viewer Log-файла сервера — RELEASE_OVERALL.doc (txt:2938); БД HELPINI (все параметры INI) — RELEASE_OVERALL.doc (txt:4777); Редактор ISO/MST-файлов — RELEASE_OVERALL.doc (txt:7902); преобразование Excel/Access/DBF в ISO — RELEASE_OVERALL.doc (txt:7608).

## Читатель / Web-ИРБИС

- Шлюз Web-ИРБИС64+: восстановление пароля через E-mail (webmail.exe, LOGIN_READER/PASSWORD_READER) — RELEASE_OVERALL.doc (txt:290); смена пароля в Личном кабинете — RELEASE_OVERALL.doc (txt:287); авторизация после входа гостем — RELEASE_OVERALL.doc (txt:317); QR-ссылка на документ — RELEASE_OVERALL.doc (txt:320).
- Профилирование интерфейса по форматам доступа (виртуальные поля 1002 логин, 1100 IP): access_*.pft, динамический список БД access_dbn, dbn_web_ft.mnu — RELEASE_OVERALL.doc (txt:671).
- Постоянные запросы по новым поступлениям (АвтоИРИ) — RELEASE_OVERALL.doc (txt:668); двухстраничный просмотр initializationPagePortionCount, листание колесом wheelPageChangerSetting — RELEASE_OVERALL.doc (txt:696); список должников — RELEASE_OVERALL.doc (txt:698); КАРТА САЙТА — RELEASE_OVERALL.doc (txt:699); аутентификация через LDAP LDAP_LOGIN — RELEASE_OVERALL.doc (txt:700).
- J-ИРБИС 2.0: галереи персоналий (БД ATHRA) с наукометрией РИНЦ — RELEASE_OVERALL.doc (txt:326); ввод книгообеспеченности преподавателем через сайт — RELEASE_OVERALL.doc (txt:338); печать табличных форм через сайт — RELEASE_OVERALL.doc (txt:344); скоростная дедубликация сводных каталогов по хэшу свёртки — RELEASE_OVERALL.doc (txt:347); замена Flash на HTML5 — RELEASE_OVERALL.doc (txt:354); авторизация MD5 — RELEASE_OVERALL.doc (txt:356); автогенерация 951^4/951^3/951^H — RELEASE_OVERALL.doc (txt:357).
- Онлайн-регистрация и предоставление пароля по категориям — RELEASE_OVERALL.doc (txt:703); бронирование услуг библиотеки — RELEASE_OVERALL.doc (txt:718); сквозная (бесшовная) авторизация по токену — RELEASE_OVERALL.doc (txt:739); редактирование библиографических справок — RELEASE_OVERALL.doc (txt:749); перевод на Apache 2.4.38/PHP 5.6.40/MariaDB 10.1.38 — RELEASE_OVERALL.doc (txt:761); ГОСТ Р 7.0.100-2018 — RELEASE_OVERALL.doc (txt:763); авторизация по полям 30/130 — RELEASE_OVERALL.doc (txt:765).
- Импорт со слиянием ЭБС Консультант студента, Профилиб; бесшовная авторизация Профилиб/Medlib — RELEASE_OVERALL.doc (txt:352).
- Библиослайдер новых поступлений — RELEASE_OVERALL.doc (txt:2429); тезаурус MESH (медицинские библиотеки) — RELEASE_OVERALL.doc (txt:2445); имидж-каталог (ретроконверсия) — RELEASE_OVERALL.doc (txt:2449).
- Сенсорный интерфейс (мобильные/планшеты/киоски) — RELEASE_OVERALL.doc (txt:3062); Top-10 оценённых книг — RELEASE_OVERALL.doc (txt:3068); регистрация ВКР студентом — RELEASE_OVERALL.doc (txt:3070); поиск в БД музейных экспонатов MUSP — RELEASE_OVERALL.doc (txt:3076); on-line проигрыватель mp3/flv/avi — RELEASE_OVERALL.doc (txt:3549); провайдер данных JSON-RPC 2.0 — RELEASE_OVERALL.doc (txt:3551).
- Расширение поиска по авторитетным файлам (ATHRA/ATHRC, поля 410/510/710) — RELEASE_OVERALL.doc (txt:2440); ПОИСК ДЛЯ ЧАЙНИКОВ AutoDebil/FloatDebil/DBSCH — RELEASE_OVERALL.doc (txt:5760); универсальный тематический навигатор (БД URUB) — RELEASE_OVERALL.doc (txt:5771).
- Дополнительные ограничения поиска (год издания, дата ввода) — RELEASE_OVERALL.doc (txt:9760).

## Полные тексты

- ИРБИС64 ПБД: Web-ИРБИС ПБД, АРМ Полнотекстовый администратор, АРМ Полнотекстовый читатель — RELEASE_OVERALL.doc (txt:2426).
- Постраничный просмотр PDF (HTML, без Flash) с защитой от копирования/выгрузки — RELEASE_OVERALL.doc (txt:2461) / RELEASE_OVERALL.doc (txt:3548); закладки и оглавление PDF — RELEASE_OVERALL.doc (txt:1168); подсветка терминов запроса в PDF — RELEASE_OVERALL.doc (txt:1177); ограничение доступа к части документа (БД RIGHT) — RELEASE_OVERALL.doc (txt:1181).
- История обращения к полным текстам TEXTHISTORY, формат ehistory.pft — RELEASE_OVERALL.doc (txt:812).
- Ранжированный полнотекстовый поиск (модуль Web-ИРБИС64 Полнотекстовые БД) — RELEASE_OVERALL.doc (txt:3552); морфология FULLTEXTMorphology / [FullText] Morphology — RELEASE_OVERALL.doc (txt:4256).
- Кэширование страниц PDF: TextCacheRootPath, TextPath, TextPathAlias — RELEASE_OVERALL.doc (txt:4862); защищённые PDF isNeedDecryptPDF, PDFPassword — RELEASE_OVERALL.doc (txt:4850); MAX_TIME_CONVERTING, isNeedSplitInsteadExtract — RELEASE_OVERALL.doc (txt:4857); авто-подбор утилит PDFTextExtractUtilityOrder, PDFSplitUtilityOrder — RELEASE_OVERALL.doc (txt:5280).
- Двоичные ресурсы внутри документов (поле 953: BMP/GIF/JPG, только ИРБИС64) — RELEASE_OVERALL.doc (txt:7204); вывод в HTML [[N]] — RELEASE_OVERALL.doc (txt:7212); внешние графические объекты в поле 951 — RELEASE_OVERALL.doc (txt:7374).

## Форматы и PFT

- QR-коды в HTML (uf #size,level,qrtext); в АРМах IRBIS TYPE=4 — RELEASE_OVERALL.doc (txt:243).
- Графика в HTML-страницу ИРБИС-ссылкой (атрибут ALT=!...) — RELEASE_OVERALL.doc (txt:258).
- Хеш MD5 строки (uf dollar) — RELEASE_OVERALL.doc (txt:262); отправка письма (uf @A e-mail), mailsubjectA/mailbodyA — RELEASE_OVERALL.doc (txt:264).
- Глобальные счётчики (uf ++C) — RELEASE_OVERALL.doc (txt:2992); формат с переменными параметрами (uf 6 формат) — RELEASE_OVERALL.doc (txt:2995); интерактивные форматы с префиксом # (поле 991) — RELEASE_OVERALL.doc (txt:2623).
- uf +9R / uf +9X римские/арабские числа — RELEASE_OVERALL.doc (txt:5210); unifor 4N предыдущая копия — RELEASE_OVERALL.doc (txt:5212); uf +9V версия 32/64 — RELEASE_OVERALL.doc (txt:5228); uf +9J / uf +9K двоичный файл/удаление — RELEASE_OVERALL.doc (txt:5797); uf 3B / uf 3C арифметика дат — RELEASE_OVERALL.doc (txt:5575); uf +98ab замена символа — RELEASE_OVERALL.doc (txt:5585); uf +9L проверка файла/URL — RELEASE_OVERALL.doc (txt:4221).
- HTML-форматы вывода (суффикс _H) как альтернатива RTF — RELEASE_OVERALL.doc (txt:7198); преобразование табличных форм RTF в HTML — RELEASE_OVERALL.doc (txt:822).
- Гиперссылки (unifor +I): 3 вида (внешние объекты 0, один-к-одному 1, один-ко-многим 2) — RELEASE_OVERALL.doc (txt:8752); постредактура (unifor +F, unifor !) — RELEASE_OVERALL.doc (txt:8833).
- Цветовые форматы BRIEFCOLORPFT, RQSTCOLORPFT — RELEASE_OVERALL.doc (txt:1605); вложенные форматы (KN.pft/MN.pft/ASP.pft) — RELEASE_OVERALL.doc (txt:8202); конструкция ТВП (0 0 *) для импорта/экспорта без переформатирования — RELEASE_OVERALL.doc (txt:4539).

## Поиск

- Логические операторы ИЛИ, И, НЕТ, И-в-поле, И-фраза (ItemLogicN) — RELEASE_OVERALL.doc (txt:8737); в Web — И В ПОВТОРЕНИИ, И РЯДОМ, оператор F — RELEASE_OVERALL.doc (txt:1586) / RELEASE_OVERALL.doc (txt:3116).
- Морфология по ключевым словам MORPHOLOGY ([SEARCH]/[NAVIGATOR]), БД MORPH (~140 тыс. статей) — RELEASE_OVERALL.doc (txt:4156) / RELEASE_OVERALL.doc (txt:4284).
- Автодополнение/подсказчик терминов — RELEASE_OVERALL.doc (txt:5764); стоп-слова — RELEASE_OVERALL.doc (txt:3117); свободный поиск с ранжированием — RELEASE_OVERALL.doc (txt:2069); фасетный поиск (только ИРБИС 64+) — RELEASE_OVERALL.doc (txt:2044); распределённый поиск — RELEASE_OVERALL.doc (txt:5814).
- Автоматическое расширение запроса ItemAdvNN= (авторитетные файлы/тезаурус) — RELEASE_OVERALL.doc (txt:8410); свободный последовательный поиск (|МММ выражение) — RELEASE_OVERALL.doc (txt:4982).

## Базы данных и поля

- Новые/специализированные БД: LOGC (txt:23), LOGP (txt:567), RDR_ARH (txt:67), COUNT (txt:2551), RIGHT (txt:1181), EVENT (txt:1271), MORPH (txt:4284), URUB (txt:5771), MUSP (txt:3076), GUAR/GUSK/GURF (txt:4357), ARCH (txt:6432), ATHRA/ATHRC/ATHRG (txt:6458), сводные SK/SK_EKZ/SK_NEW/SK_USER (txt:2405); VUZ, CMPL, RQST, POST, PODB, WORK.
- Ключевые поля ЭК (IBIS): 62 (заказ/планирование), 80 (взамен утерянных), 130 (пароль MD5), 509 (картографический заголовок), 691 (учебное назначение, ^5 РП), 692/693 (ККО), 694 (заявка), 699 (аналоги), 740 (законодательные/религиозные материалы, префиксы ZA=/URD=/VZA=), 900^t (тип документа), 900^Z (возрастное ограничение), 907 (история корректировок ^X), 910 (учёт экземпляров ^D/^B/^U/^9/^!/^=КМИ/статус 9), 920 (вид документа), 951/953/955 (электронные ресурсы/обложки/права), 982 (НТД/патенты), 230/337/135 (электронные ресурсы по ГОСТ 7.82-2001) — RELEASE_OVERALL.doc (txt:124) / RELEASE_OVERALL.doc (txt:2081) / RELEASE_OVERALL.doc (txt:9786).
- БД RDR: поля 21 (дата рождения), 24/30 (авторизация), 29/56/57 (право/места обслуживания), 40 (^4 продления, ^9 примечание выдачи), 50 (категория, повторяемое), 51/52 (место регистрации), 69 (дисциплины), 130 (пароль), 140 (профили ИРИ) — RELEASE_OVERALL.doc (txt:9875).
- БД CMPL: поля 62 (суммарный заказ), 88 (КСУ ^9/^A), 145–151/155 (распределение партии), 692; РСУ-поле 881 (^A/E/F/P/W) — RELEASE_OVERALL.doc (txt:904).
- БД VUZ: поля 83 (дисциплины/семестры с кодом языка), 3^0 (УНД), рабочие программы (WPD), типы записей DISC/FAK — RELEASE_OVERALL.doc (txt:7350).

## RFID / штрихкоды / периферия

- Серверное RFID-устройство (TCP/IP): PRRFID=1, RFIDTYPE=4, RFID_UNI_ADDRESS/PORT/INTERVAL/UID — RELEASE_OVERALL.doc (txt:2694).
- Скоростная книговыдача и идентификация по радиометке/штрихкоду — RELEASE_OVERALL.doc (txt:835) / RELEASE_OVERALL.doc (txt:7596); RFID с противокражной подписью (АНТИВОР, АЭРО СОЛЮШНЗ) — RELEASE_OVERALL.doc (txt:7301); поставщик НП МЦТТ — RELEASE_OVERALL.doc (txt:5556).
- Автоввод/групповое чтение меток AUTOIN_RFID_BARCODE=1, ConfirmMultiRFID=1 — RELEASE_OVERALL.doc (txt:5616); различение ШК читательских билетов ReaderBarCode — RELEASE_OVERALL.doc (txt:7867).
- Печать штрих-кодов: ПЕЧАТЬ КК, BARCODEHEIGHT; в HTML IRBIS штрих-код — RELEASE_OVERALL.doc (txt:8214) / RELEASE_OVERALL.doc (txt:9502); размножение ШК для статуса R (910^H) — RELEASE_OVERALL.doc (txt:7068).
- Списание/проверка фонда по файлу ИН/ШК, контроль дублетности/уникальности (Dbnflc.pft, Provfgr.gbl) — RELEASE_OVERALL.doc (txt:1839) / RELEASE_OVERALL.doc (txt:7959); подполе 910^! не на месте — RELEASE_OVERALL.doc (txt:7976).

## Интеграции и обмен (Z39.50, OAI, MARC, ГОСТ)

- Z39.50: импорт из ресурсов (РГБ, РНБ, ГПНТБ, ВГБИЛ, БЕН, Библиотека конгресса и др.), порты 9999/9909/7090/210, ТВП RUSMARCFST/UNIMARCFST/USMARCFST, ZIMPORTSEARCHPAGE/ZIMPORTFORMAT — RELEASE_OVERALL.doc (txt:7244) / RELEASE_OVERALL.doc (txt:7262); сервер Z64 v3.0 с SRU/SRW/SOAP — RELEASE_OVERALL.doc (txt:4932); функция Insert (запись БО, дополнение поля 951) — RELEASE_OVERALL.doc (txt:4936).
- XML: экспорт/импорт RUSMARCXML/Slim, Dublin Core, MARCXML, MODS; XMLTAGFIELD/XMLTAGSUBFIELD/XMLTAGCONTROL/XMLTAGPREFIX — RELEASE_OVERALL.doc (txt:1642) / RELEASE_OVERALL.doc (txt:4933) / RELEASE_OVERALL.doc (txt:7278).
- MARC: импорт/экспорт RUSMARC/UNIMARC/USMARC (Rmarce.fst, Rmarci.fst, umarciw.fst, vmarci.fst); экспорт периодики в РСВКП Rmarce_RSKP.fst — RELEASE_OVERALL.doc (txt:7388); импорт без переформатирования (поля 9461/9463/9215) — RELEASE_OVERALL.doc (txt:9834).
- ЛИБНЕТ: LIBNETIP/LIBNETUSER/LIBNETPASSWORD — RELEASE_OVERALL.doc (txt:7834); импорт из Web-ИРБИС — RELEASE_OVERALL.doc (txt:7523).
- ЭБС: интеграция метаданных (Лань, IPRBooks, Znanium, Юрайт, book.ru, ibooks, Университетская библиотека и др.), форматы TXT/ISO 2709/CSV, импорт со слиянием, сквозная авторизация — RELEASE_OVERALL.doc (txt:1185) / RELEASE_OVERALL.doc (txt:1565).
- Сводный каталог (СК): импорт со слиянием, Приоритетная сигла SiglP.mnu, SvkAddIND/SvkAddEX — RELEASE_OVERALL.doc (txt:7700).
- Бухгалтерия: ИРБИС-ПАРУС (текстовый экспорт КСУ, PARYS.B.fst) — RELEASE_OVERALL.doc (txt:7143).
- ГОСТ: Р 7.0.100-2018 (полный формат Web) — RELEASE_OVERALL.doc (txt:763), 7.82-2001 (электронные ресурсы) — RELEASE_OVERALL.doc (txt:9786), 7.75-97 (коды языков jz.mnu) — RELEASE_OVERALL.doc (txt:8073); импорт/экспорт ISO 2709, UTF-8 — RELEASE_OVERALL.doc (txt:8174).
- API: клиентский JSON-RPC 2.0 для корпоративной работы — RELEASE_OVERALL.doc (txt:2066); пользовательские функции через DLL (C21COM=11) — RELEASE_OVERALL.doc (txt:6553).

## Открытые вопросы (TODO recon)

- TODO(recon #1101: OAI-PMH в явном виде не упомянут — присутствуют Z39.50, SRU/SRW, SOAP, MARC, XML; OAI отдельной строкой не подтверждён).
- TODO(recon #1102: ряд пунктов J-ИРБИС/Web имеет двойную нумерацию в исходнике, напр. п.6 дважды в версии 2021.1 — RELEASE_OVERALL.doc (txt:351) / RELEASE_OVERALL.doc (txt:352)).
- TODO(recon #1103: имена секций INI для части параметров приведены из контекста; для отдельных параметров секция в тексте не указана явно).
- TODO(recon #1104: цитаты по диапазону 1020-9919 опираются на построчные ссылки субагентов; номера строк в плотном тексте могут смещаться на +/-1-2 — критичные сверять по оригиналу).
- TODO(recon #1105: содержимое скриншотов/рисунков в txt отсутствует — функционал восстановлен по подписям и текстовым описаниям).
