# FINDINGS 09 — Web-ИРБИС и читательский доступ

> Источник: WEBIRBIS64+.DOC (оригинал), читан как WEBIRBIS64_.DOC.txt.
> Ссылки на факты — WEBIRBIS64+.DOC (txt:СТРОКА). Документ = «Web-ИРБИС64+. Руководство пользователя», Москва 2020 (txt:21-40).

---

## Архитектура Web-шлюза (компоненты, CGI, конфигурация, связь с сервером)

**Установка/предпосылки.** Установщик — wsetup.exe (txt:102). До установки должны стоять Web-сервер и серверная часть ИРБИС64+ (txt:103); требуется ~50 Мб (txt:104).

**Исходные параметры установки** (txt:105-108): путь на irbis_server.ini сервера БД; путь на htdocs; путь на CGI.

**Создаваемые директории** (txt:109-116): irbis64r_plus в htdocs (index.html, мнемоника HTTP_PATH); irbis64r_plus в cgi-bin (CGI_PATH); frames_plus (форм-файлы *.frm; подпапки BBK, DEFAULT, FULLTEXT, GRNTI, MAKE_VREADER, TABLE_FORMS, UDC, URUB); Deposit_plus (*.pft, *.mnu); в htdocs — CSS, FONTS, IMAGES, JS, PHP.

**Проверка/старт.** http://<АДРЕС>/HTTP_PATH/index.html → страница авторизации author.frm (txt:120). После логина/пароля → основной поисковый интерфейс (txt:125-127). «ВОЙТИ КАК ГОСТЬ» требует в БД RDR записи с GUEST в полях 30 и 50 (txt:125). Шлюз должен иметь права писать/создавать/удалять файлы в директории БД сервера ИРБИС64+ (txt:132).

**Модель CGI.** Работа на форм-файлах *.frm (txt:153); основной параметрический файл — irbis_server_ft.ini в CGI_PATH; по каждой команде — последовательность фреймов, формирующая HTML-страницу (txt:153). База по умолчанию — IBIS (txt:154).

**Команды C21COM** (GET/POST) (txt:157-164): F Показ фреймов→ShowFrames; S Поиск→SearchFrames; T Словарь→DictionryFrames; Z Заказ→ZakazFrames; R Запись→RecUpdateFrames; плюс E Экспорт (txt:411-412,451). Значение — список фреймов через запятую.

**Секции INI/БД.** Имя секции — I21DBN=, команда — C21COM=; для одной БД допускается много секций (txt:165). Пример запроса основной страницы: C21COM=F&I21DBN=AUTHOR&P21DBN=IBIS&Z21FLAGID=1&Z21ID=111&Z21FAMILY=111 (txt:167-173).

**Препроцессинг.** Запрос анализируется форматом cgiflc.pft (папка DEPOSIT_plus); при I21DBN=AUTHOR и корректной авторизации значение заменяется на <P21DBN>_FULLTEXT (txt:174-175). cgiflc.pft используется и для отмены обязательной авторизации (txt:492); путь в [WEB] CgiFlc= (txt:516).

**Пример секции [IBIS_FULLTEXT]** (txt:178-188): FRAMES=...frames_plus\FullText\, ShowFrames=header_ft.frm,baner_ft.frm,search_ft.frm,footer_ft.frm, SearchFrames=...,RESULT,footer_ft.frm, MIN_COLOR_COUNT=3, DBNAME=IBIS. Спец-фрейм RESULT — точка вставки результатов; при ненахождении фреймы ищутся в [WEB] FRAMES=...frames_plus\Default\.

**Связь с сервером ИРБИС64 ([MAIN])** (txt:505-512): IRBISPATH (исполняемый модуль сервера), DATAPATH (БД), DepositPATH/DepositPriority, CGITimeOut (макс. время запроса; иначе Server error: timeout ellapsed).

**Доп. команды сборки страниц** (txt:199-235): <!FORMAT=формат|@file> (INSERT_ALL_PARAMETERS — все непустые параметры в hidden-поля); <!FILE=file.frm> (поиск рядом→в БД→[WEB] FRAMES); подстановки TIME, MAXIMUMMFN, RUNTIMEPID(=ReaderIDTag 1002), DATABASE, MFNCOUNT, MFN, DB, TOTALRECS, BEGINRECS, ENDRECS; многострочный формат в <? ... ?>.

**Статистика обращений ([MAIN])** (txt:616-643): LogDateBase=LOGDB (пусто=выкл.); EveryDayEmtyLogDB=1, период EveryDayEmtyLogDBTime= (1-30), отчёт ..._Report= (otchet.csv), формат ..._Format= (otchet, в Deposit_plus).

---

## Виды поиска для читателя и ЭК

**Основной библ. поиск.** Поля задаёт Dublin_core.frm, вставляемый в search_ft.frm по параметру SHOW_DUBLIN_CORE (txt:193-195).

**Выбор БД.** SELECTDB=1 в [MAIN] выводит выпадающий список БД (по умолч. 0) (txt:237-239,516). Включение БД в web-список — автоматически при создании в АРМ Администратор или режимом «СДЕЛАТЬ БД ЭБ ДОСТУПНОЙ ЧИТАТЕЛЮ WEB» (txt:241-242).

**Полнотекстовый поиск с ранжированием.** В I21DBN=IBIS_FULLTEXT; параметры FT_REQUEST, FT_PREFIX=K=, FT_S21LOG=4, S21FMT=briefHTML_ft (txt:245-247,427). Морфология рус. языка вместо усечения — Morphology=1 в [FullText] (txt:528-530).

**Параметры поиска S21*** (txt:417-450): S21LOG между выражениями (0 ИЛИ/1 И/3 НЕТ) и между словами (0/1/2 фраза/3/4 ранжирование/5 по сканированию словаря); S21P01 (извлечение терминов 0-3, 3=основы), S21P02 (усечение 0/1), S21P03 (префикс), S21P04 (квалификатор-метки), S21P05 (содержание), S21P06/07 (границы сканирования), S21STR (термины); S21ALL (ISIS, кавычка→<.>); сортировка S21SRW+S21SRD(UP/DOWN); S21SCAN/S21SCAN_FULL; раскраска S21COLORTERMS/S21ALLTRM, область без раскраски <!>.

**Словарь (T)** (txt:461-464): T21CNR, T21PRF, T21TRM, T21SELTRM, T21CHK.

**Переменный элемент поиска** — variant_search_field.mnu (в deposit_plus), пары строк; параметры field_type(input/select), parameters, source(*.mnu), autocompleteType(extractLastWord/wholeQuery, источник — словарь с префиксом S21P03) (txt:764-771).

**Доп. поиск/навигация ЭБ** (txt:652-694): профессиональный библ. поиск; УДК ([UDC], БД RSUDC, форматы udc.pft,ref1.pft,ref2.pft); ББК ([BBK], БД RSBBK, bbk.pft,ref1_bbk.pft,ref2_bbk.pft); таблицы книгообеспеченности (3 вида; форматы KoSpecDisc, KoVuzDiscNumEkz, поле 693, GetKkoBook, AccessRdr) (txt:692-752). Включение в [MAIN]: MPROF/MUDK/MBBK/MKO (по умолч. 1), SPECIAL_VISION (слабовидящие, 0) (txt:518-528).

**ЭК.** Прямое упоминание — метка MFN_PAGE(3502) «MFN в ПБД первой релевантной страницы … списке найденных записей ЭК» (txt:569,590); БД каталога в поставке — IBIS (txt:154).

---

## HTML-форматы вывода (отличие веб-PFT от экранных)

Веб-форматы — *.pft, вызываемые из фреймов (<!FORMAT=@имя>) или через S21FMT (имя без расширения) (txt:282,417); генерируют HTML (суффиксы HTML/_ft). Отличие от экранных PFT — встроенные команды шлюза <!FORMAT=...>, <!FILE=...>, <--...--> (txt:199-235).

**Сборка страницы результатов** (txt:244-258): SearchFrames=header_ft,baner_ft,search_ft,after_search_ft,RESULT,footer_ft; сообщение о результатах — after_search_ft.frm (ссылка на листание referings_ft.pft); показ документов — BriefHTML_ft.pft (вложенные форматы: библиоописание + ссылки на страницы); фасеты «Распределение результатов поиска» — footer_ft.frm.

**Форматы/меню (Прил.2)** (txt:488-492): dbn_web_ft.mnu/web_mnu_select_ft.pft (список БД); subject_wn.mnu (тематика); referings_ft.pft / referings_img2.pft (листание PDF); BriefHTML_ft.pft / book_bo_h.pft (показ/библиография); img.pft (страница PDF→JPG); variant_search_field.mnu; Zakaz.pft; Cgiflc.pft; fst_rec.fst, dbnflc_rec.pft (ВКР).

**Раскраска ([WEB])** (txt:499-505): EXTPREF=<b><font color=red>, EXTPOST=</font></b>, MIN_COLOR_COUNT; кнопки↔команды: Выполнить=F, Заказать=Z, Экспорт=E, Поиск=S, Словарь=T, Далее=T, Вернуться=F.

**Экспорт E** (txt:451-460): EXP21FMT(ISO/TXT), EXP21CODE(UTF-8/WIN/DOS), EXP21FST(UMARCEW/RMARCE/SMARCEW — внутр.ИРБИС/UNIMARC/RUSMARC/USMARC).

---

## Полные тексты и права доступа через web

**Видимость ссылок** — Show_ed в [MAIN] (внешние объекты, поле 951): 0 всем / 1 только авторизованным / 2 не показывать (txt:512-515).

**Просмотр.** [IBIS_READER] (txt:370-374): ShowFrames=header_reader,reader,footer_reader, SearchFrames=book_viewer.frm, БД IBIS. Всплывающее окно — по ссылке «Постраничный просмотр полного текста» / клику по первой релевантной странице (txt:376).

**Кэш/пути ([FullText])** (txt:528-532): TextCacheRootPath, TextPath, TextPathAlias, Morphology=1.

**Скачивание** (txt:482-484): «Получить двоичный ресурс» (BINARY_RESOURCE_MFN/_OCC; метка 953, ^a тип/^b картинка); «Скачать файл» (IMAGE_FILE_NAME, IMAGE_FILE_MFN(955^A), IMAGE_FILE_DOWNLOAD 0 открыть/1 скачать, IMAGE_FILE_PAGE стр. PDF). Безопасность: [WEB] Safe_File_Download/Safe_File_Paths для C21COM=2 (txt:505).

**Эл. книговыдача.** Все обращения к полному тексту в интервал EBookAccessInterval (по умолч. 24 ч, [MAIN]) = ОДНА эл. книговыдача (txt:264,512).

**Метки PDF ([PARAMETRS])** (txt:564-590): DOWNLOAD_FILE=1102, PDF_PAGE=1104, NUM_PAGES=3500, NUM_MFNS=3501, MFN_PAGE=3502, FT_WORDS_TAG=3336.

---

## Личный кабинет / заказ / запись читателя через web

**Личный кабинет** — фрейм author_3.frm (txt:259). Содержит (txt:262-269): издания на руках; история книговыдач (бумажные + электронные, обратнохронологически, лимит MAXHISTORYCOUNT=10); закладки полных текстов; корзина заказов; личные постоянные запросы; «ЗАГРУЗИТЬ ТЕКСТ В ЭБ» (в поставке — ВКР, БД VKR).

**Секции личного кабинета** (irbis_server_ft.ini):
- Литература на руках [RDR] → show_rcard.frm/show_rcard.pft, БД RDR (txt:271-282);
- История [RDR_HISTORY] → show_history.frm/show_history.pft, БД RDR (txt:283-295);
- Закладки [RDR_ZAKLADKI] → show_zakladki.frm/show_zakladki.pft, БД LICH, есть RecUpdateFrames (txt:297-310);
- Корзина [RQST]: SearchFrames=header_rqst,RESULT,footer_rqst, БД RQST; ссылка в author_3.frm через C21COM=S, поиск S21ALL=I=$, формат RQST_WEB (txt:312-326);
- Мои запросы [ZAPR]: ShowFrames=show_search_queries.frm, RecUpdateFrames=RESULT,rec_update_result_json.frm, БД ZAPR (txt:328-338);
- Загрузить текст в ЭБ [IBIS_REC]: ShowFrames=header_rec,reg,footer_rdr, RecUpdateFrames=header_rec,RESULT,footer_r,footer_rdr, БД VKR (txt:341-362).

**Загрузка ВКР** (txt:353-362): reg.frm (обяз. поля *), передача PDF input type=file name=PDFTEXT accept=application/pdf; ФЛК dbnflc_rec.pft (WRITE_TEXT_FLC), переформат fst_rec.fst (WRITE_TEXT_FST); результат в footer_r.frm (@Virtual_rec_result): v1101=0 → Yes_Virtual.frm, иначе Not_Virtual.frm. Видимость — SHOW_TEXT_REC=1 [FullText] (txt:531-532).

**Лимиты ([MAIN])** (txt:528): MAXHISTORYCOUNT=10, MAXBOOKMARKCOUNT=20, MAXQUERYCOUNT=20.

**Заказ.** Ссылка «Заказать» при наличии экземпляров (txt:380); подтверждение — order_form.frm из order.frm, библиоописание — zakaz.pft (txt:387). [IBIS_Zakaz]: ShowFrames=header_zakaz,RESULT,order,footer_rqst, ZakazFrames/SearchFrames, БД IBIS (txt:389-396). Показ «ЗАКАЗАТЬ» — Show_order (1/0, авторизованным) (txt:515-516).

**Команда заказа Z** (txt:464-465): Z21CMT, Z21ID, Z21FAMILY, Z21FLAGID(1 идентиф.+фамилия / 0 только идентиф.), Z21MFN, Z21YEAR/TOM/NUM(периодика), Z21MRG(место выдачи); удаление из корзины RQST21MFN (при S21SCAN_FULL=1).

**Авторизация/метки** (txt:593-605): [REQUEST] RQSTTAGFAMILYREADER=130 (пароль в RDR), RQSTTAGREADER=30 (идентиф. в RQST); [READER] RDRPREFREADER=RI=, RDRTAGREADER=30 (логин в RDR). Сессия — [WEB] TimeLiveKey (мин.) (txt:505). Команда R — только авторизованным (txt:470).

**Самозапись «ЗАПИСАТЬСЯ В БИБЛИОТЕКУ»** — [MAIN] RDR_REC=1 (txt:516); подпапка фреймов MAKE_VREADER (txt:114).

**Команда записи R** (txt:466-484): R21MFN(0 новая/>0 добавить), R21IFP(актуализация), R21UPD(0 переписать/1 вхождения/2 удалить/3/4), R21NUMi(метка), R21SUBi_j(подполе), R21VOLi_j(значение), R21OCCi. Повторений поля <=5000 (txt:469).

---

## АРМ «Читатель» (десктоп) — что известно

Отдельного описания десктопного АРМ «Читатель» в файле НЕТ — речь о web-интерфейсе читателя. Косвенно: БД читателей RDR (поля 30 идентификатор, 50 категория, 130 пароль/фамилия) (txt:125,593-605); упоминаются АРМ Администратор (создание БД, «СДЕЛАТЬ БД ЭБ ДОСТУПНОЙ ЧИТАТЕЛЮ WEB», копирование секций IBIS) (txt:241-242,606-614) и АРМ КО (поле 693) (txt:715). TODO(recon #0901): десктопный АРМ «Читатель» здесь не описан.

---

## Открытые вопросы (TODO recon)

- TODO(recon #0901): Десктопный АРМ «Читатель» в файле не описан; нужен отдельный документ.
- TODO(recon #0902): Секции [IBIS_PAGE_ACCESS], [IBIS_AUTHOR], [IBIS_DOWNLOAD] перечислены как копируемые (txt:606-614), но содержимое не раскрыто.
- TODO(recon #0903): Фреймы author.frm (txt:120) и not_author_3.frm (txt:206) упомянуты, структура не описана.
- TODO(recon #0904): Подпапки GRNTI/TABLE_FORMS/URUB (txt:114) — назначение отдельно не описано.
- TODO(recon #0905): Параметр SHOW_DUBLIN_CORE (txt:195) — секция и значения не уточнены (упомянут IMAIN).
- TODO(recon #0906): Числовые C21COM (2 скачать, «3 двоичный ресурс») смешаны с буквенными (txt:482,505); полная карта не сведена.
- TODO(recon #0907): Структура полей БД LICH, ZAPR, VKR не описана (txt:308,338).
- TODO(recon #0908): [PARAMETRS]: полный список PARNAME/PARTAG (PARCOUNT=64) приведён частично (txt:590-593).
- TODO(recon #0909): Рис.1-17 — скриншоты, в txt отсутствуют; визуальные детали интерфейса не извлекаемы.
