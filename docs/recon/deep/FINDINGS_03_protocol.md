# FINDINGS 03 — Протокол / клиентская библиотека IRBIS64_CLIENT.DLL

> **Источник:** `irbis64_client_dll.doc` → конвертирован в `irbis64_client_dll.doc.txt` (UTF-8). Ссылки в формате `irbis64_client_dll.doc (txt:СТРОКА)`. Документ прочитан целиком (строки 1–1290). Раздел 12 пуст — `(пока нет)` `irbis64_client_dll.doc (txt:1221-1222)`.

## Общая модель

Библиотека `irbis64_client.dll` — полнофункциональный доступ к БД ИРБИС64 через TCP/IP-сервер ИРБИС64 `(txt:91-92)`.

**Типы/кодировки** `(txt:93-97)`: два типа — `integer` и `Pchar`; строки в **UTF-8** (кроме явно оговорённых ANSI-случаев); буфер выделяет вызывающая программа; строка = байты `char` + двоичный ноль; разбиение на строки последовательностью **`$0D0A`**; прототипы/коды/константы — в `irbis64_client.pas`. **Псевдоразделитель `$3130`** заменяет `$0D0A` в групповых/расформатированных ответах; преобразование — `IC_reset_delim`/`IC_delim_reset` `(txt:308, txt:1201-1219)`.

**Жизненный цикл сессии:** `IC_reg` обязательно первой, возвращает INI-профиль (ANSI) `(txt:106-139)`; `IC_unreg` в конце `(txt:141-154)`; `IC_nooperation` периодически — сигнал «жив» `(txt:1183-1188)`; интервал авто-подтверждения `IC_set_client_time_live` (минуты, по умолч. 1) `(txt:156-168)`. Авто-разрегистрация по таймауту **`CLIENT_TIME_LIVE`** в `irbis_server.ini` `(txt:154, txt:1188)`.

**Режимы ожидания/Web-шлюз:** `IC_set_show_waiting` (сек, по умолч. 3) `(txt:170-183)`; `IC_set_webserver` (1/0, по умолч. 0) `(txt:185-200)`; `IC_set_webcgi` (по умолч. `/cgi-bin/wwwirbis.exe`) `(txt:202-212)`; `IC_set_blocksocket` («мёртвое» ожидание, 1/0, по умолч. 0) `(txt:214-226)`; `IC_isbusy` (1 — не завершено, 0 — завершено) `(txt:228-235)`. Web-шлюз — см. `Сервер 64.doc` `(txt:199-200)`.

## Каталог функций (всего 80 функций, префикс `IC_`)

### (2) Общего назначения `(txt:104-235)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 2.1 (txt:106) | `IC_reg` регистрация | host;port(6666);arm;user;password;answer;abufsize | answer=INI-профиль (ANSI) | `ZERO`;`CLIENT_NOT_IN_LIST`;`WRONG_PASSWORD`;`CLIENT_LIST_OVERLOAD`;`CLIENT_NOT_ALLOWED` |
| 2.2 (txt:141) | `IC_unreg` раз-регистрация | user_name | — | `ZERO`/ошибка |
| 2.3 (txt:156) | `IC_set_client_time_live` | Aopt(мин) | — | `ZERO` |
| 2.4 (txt:170) | `IC_set_show_waiting` | Aopt(сек) | — | `ZERO` |
| 2.5 (txt:185) | `IC_set_webserver` | Aopt(1/0) | — | `ZERO` |
| 2.6 (txt:202) | `IC_set_webcgi` | Acgi | — | `ZERO` |
| 2.7 (txt:214) | `IC_set_blocksocket` | Aopt(1/0) | — | `ZERO` |
| 2.8 (txt:228) | `IC_isbusy` | нет | — | 1/0 |

### (3) Ресурсы и INI-профиль `(txt:237-345)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 3.1 (txt:239) | `IC_update_ini` | inifile(ANSI) | — | `ZERO` |
| 3.2 (txt:254) | `IC_getresourse` | Apath;Adbn;Afilename;answer;abufsize | answer=ресурс(ANSI), кэш | `ZERO` |
| 3.3 (txt:279) | `IC_clearresourse` (без сервера) | нет | — | `ZERO` |
| 3.4 (txt:292) | `IC_getresoursegroup` | acontext(`Apath.Adbn.Afilename`);answer;abufsize | acontext=непустые; answer (`$0D0A`→`$3130`,ANSI) | `ZERO` |
| 3.5 (txt:314) | `IC_getbinaryresourse` | Apath;Adbn;Afilename;Abuffer:PBuffer | Abuffer^.data | `ZERO` |
| 3.6 (txt:331) | `IC_putresourse` | Apath;Adbn;Afilename;Aresourse(ANSI) | — | `ZERO` |

`Apath` `(txt:259-264)`: `SYSPATH`(`\irbis64\`), `DATAPATH`(`\irbis64\datai\`), `DBNPATH2/3/10`(БД). `Adbn` не нужен для SYSPATH/DATAPATH `(txt:265)`.

### (4) Мастер-файл БД `(txt:347-485)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 4.1 (txt:349) | `IC_read` | Adbn;Amfn;Alock(1/0);answer;abufsize | answer=клиентское представление | `ZERO`;`REC_DELETE`;`REC_PHYS_DELETE`;`READ_WRONG_MFN` |
| 4.2 (txt:379) | `IC_readformat` | +Aformat;answer1;abufsize1 | answer=запись; answer1=расформат | как 4.1 |
| 4.3 (txt:393) | `IC_update` (stdcall) | Adbn;Alock;Aifupdate;answer;abufsize | answer=обновл. запись | >0 = maxMFN; иначе ошибка, в т.ч. `VERSION_ERROR` |
| 4.4 (txt:416) | `IC_updategroup` | Adbn;Alock;Aifupdate;answer(1 строка/запись,`$0D0A`→`$3130`);abufsize | буфер НЕ обновляется (только статус+MFN) | >0=maxMFN/ошибка |
| 4.5 (txt:431) | `IC_runlock` разблокировать | Adbn;Amfn | — | `ZERO` (не применяется при режиме на основе версии) |
| 4.6 (txt:447) | `IC_ifupdate` актуализировать | Adbn;Amfn | — | `ZERO` |
| 4.7 (txt:463) | `IC_maxmfn` | Adbn | — | `maxmfn+1` |
| 4.8 (txt:473) | `IC_updategroup_sinhronize` связанная | Alock;Aifupdate;Adbnames;answer;abufsize | буфер не изменяется | `ZERO`/ошибка (только если успех для ВСЕХ) |

### (5) Работа с записью (локально, без сервера) `(txt:487-684)`
| № | Функция | Вход | Возврат |
|---|---|---|---|
| 5.1 (txt:490) | `IC_fieldn` | Arecord;Amet;Aocc | порядк.№ или <0 |
| 5.2 (txt:502) | `IC_field` | Arecord;nf;delim(`$00`=всё поле);answer;abufsize | `ZERO`/`ERR_BUFSIZE`/`ERR_USER` |
| 5.3 (txt:517) | `IC_fldadd` | Arecord;Amet;nf(0=последним);pole;abufsize | `ZERO`/`ERR_BUFSIZE` |
| 5.4 (txt:532) | `IC_fldrep` (пусто=удалить) | Arecord;nf;pole;abufsize | `ZERO`/`ERR_BUFSIZE`/`ERR_USER` |
| 5.5 (txt:546) | `IC_nfields` | Arecord | кол-во полей |
| 5.6 (txt:556) | `IC_nocc` | Arecord;Amet | кол-во повторений |
| 5.7 (txt:567) | `IC_fldtag` | Arecord;nf | метка/`ERR_USER` |
| 5.8 (txt:578) | `IC_fldempty` | Arecord | `ZERO` |
| 5.9 (txt:589) | `IC_changemfn` | Arecord;newmfn | `ZERO` |
| 5.10 (txt:601) | `IC_recdel` уст. логич.удал. | Arecord | `ZERO` |
| 5.11 (txt:612) | `IC_recundel` снять логич.удал. | Arecord | `ZERO` |
| 5.12 (txt:623) | `IC_recunlock` снять блокировку | Arecord | `ZERO` |
| 5.13 (txt:634) | `IC_getmfn` | Arecord | mfn |
| 5.14 (txt:644) | `IC_recdummy` пустая запись | Arecord;abufsize | `ZERO`/`ERR_BUFSIZE` |
| 5.15 (txt:656) | `IC_isActualized` | Arecord | 1/0 |
| 5.16 (txt:666) | `IC_isLocked` | Arecord | 1/0 |
| 5.17 (txt:676) | `IC_isDeleted` | Arecord | 1/0 |

### (6) Словарь `(txt:686-814)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 6.1 (txt:688) | `IC_nexttrm` | Adbn;Aterm;Anumb(0=все≤MAX_POSTINGS_IN_PACKET);answer;abufsize | `nnn#<термин>` | `ZERO`;`TERM_NOT_EXISTS`;`TERM_LAST_IN_LIST`;`TERM_FIRST_IN_LIST`;`ERR_BUFSIZE` |
| 6.2 (txt:713) | `IC_nexttrmgroup` | +Aformat(5 способов) | `nnn#<ссылка>$30<термин>$30<результат>` | как 6.1 |
| 6.3 (txt:743) | `IC_prevtrm` обратный | как 6.1 | как 6.1 | как 6.1 |
| 6.4 (txt:749) | `IC_prevtrmgroup` обратный+формат | как 6.2 | как 6.2 | как 6.2 |
| 6.5 (txt:755) | `IC_posting` ссылки термина | Adbn;Aterm;Anumb;Afirst(0=только число) | `mfn#tag#occ#pos#` | `ZERO`/число ссылок/ошибка |
| 6.6 (txt:775) | `IC_postinggroup` первые ссылки списка | Adbn;Aterms;answer;abufsize | `nnn#<ссылка>` | `ZERO`/ошибка |
| 6.7 (txt:794) | `IC_postingformat` ссылки+формат | Adbn;Aterm;Anumb;Afirst;Aformat;answer1;abufsize1;answer;abufsize | answer1=`mfn#<результат>`; answer=`mfn#tag#occ#pos#` | `ZERO`/ошибка |

`Aformat` (5 способов) `(txt:719-725)`: формат / `@имя` / `@`(оптимизир.) / `*`(по ссылке) / пусто; `***`→метка из 1-й ссылки.

### (7) Поиск `(txt:816-858)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 7.1 (txt:818) | `IC_search` прямой | Adbn;Asexp;Anumb(0=все≤MAX);Afirst(0=только число);Aformat;answer;abufsize | `mfn#<результат>` | кол-во найденных/ошибка |
| 7.2 (txt:843) | `IC_searchscan` последовательный | +Amin,Amax(0→1/0→maxmfn);Aseq(формат→0/1) | `mfn#<результат>` | кол-во найденных/ошибка |

### (8) Форматирование `(txt:860-920)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 8.1 (txt:864) | `IC_sformat` по MFN | Adbn;Amfn;Aformat;answer;abufsize | результат | код форматирования/ошибка |
| 8.2 (txt:882) | `IC_record_sformat` клиентское представл. | Adbn;Aformat(без `@`);Arecord;answer;abufsize | результат | код/ошибка |
| 8.3 (txt:894) | `IC_sformatgroup` группа | Adbn;Amfnlist(диапазон/список);Aformat;answer;abufsize | `mfn#<результат>` | код/ошибка |

### (9) Пакетная обработка (длительные) `(txt:922-1000)`
| № | Функция | Вход | Выход | Возврат |
|---|---|---|---|---|
| 9.1 (txt:925) | `IC_print` табличная форма | Adbn;Atab(`@`);Ahead(≤3 строк);Amod;Asexp;Amin,Amax;Aseq;Amfnlist;answer;abufsize | RTF | `ZERO`/ошибка |
| 9.2 (txt:964) | `IC_stat` статистика | +Astat(`FMT,N1,N2,N3`) | RTF | `ZERO`/ошибка |
| 9.3 (txt:985) | `IC_gbl` глоб. корректировка | Adbn;Aifupdate;Agbl(`@`/строки);Asexp;Amin,Amax;Aseq;Amfnlist;answer;abufsize | протокол | `ZERO`/ошибка |

`Amfnlist` `(txt:936-952)`: диапазон `0/min/max`; список `N/mfn…`; отрицат. `-N/mfn…` («кроме»). Результат = пересечение трёх списков `(txt:953-956)`. `Astat`: `FMT(поле^подполе)`, `N1`(длина), `N2`(макс.значений), `N3`(0/1/2 сортировка) `(txt:970-979)`.

### (10) Администратор (требует `IRBIS_ADMINISTRATOR`) `(txt:1003-1178)`
| № | Функция | Вход | Возврат |
|---|---|---|---|
| 10.1 (txt:1006) | `IC_adm_restartserver` | нет | `ZERO`/ошибка |
| 10.2 (txt:1015) | `IC_adm_getdeletedlist` | Adbn;answer;abufsize | `N#mfn` (1 физ./0 лог.) |
| 10.3 (txt:1031) | `IC_adm_getalldeletedlists` (stdcall) | Adbn;answer;abufsize | 7 строк (см. ниже) |
| 10.4 (txt:1051) | `IC_adm_dbempty` | Adbn | `ZERO`/ошибка |
| 10.5 (txt:1061) | `IC_adm_dbdelete` | Adbn | `ZERO`/ошибка |
| 10.6 (txt:1071) | `IC_adm_newdb` (stdcall) | Adbn;Adef;AReader(1/0) | `ZERO`/ошибка |
| 10.7 (txt:1083) | `IC_adm_dbunlock` монопольную | Adbn | `ZERO`/ошибка |
| 10.8 (txt:1093) | `IC_adm_dbunlockmfn` | Adbn;Amfnlist | `ZERO`/ошибка |
| 10.9 (txt:1104) | `IC_adm_dbstartcreatedictionry` | Adbn | `ZERO`/ошибка |
| 10.10 (txt:1114) | `IC_adm_dbstartreorgdictionry` | Adbn | `ZERO`/ошибка |
| 10.11 (txt:1124) | `IC_adm_dbstartreorgmaster` | Adbn | `ZERO`/ошибка |
| 10.12 (txt:1134) | `IC_adm_getclientlist` текущие | answer;abufsize | список (ANSI) |
| 10.13 (txt:1146) | `IC_adm_getclientslist` для доступа | answer;abufsize | список (ANSI) |
| 10.14 (txt:1158) | `IC_adm_getprocesslist` | answer;abufsize | список (ANSI) |
| 10.15 (txt:1170) | `IC_adm_setclientslist` | AClientMnu | `ZERO`/ошибка |

7 строк `IC_adm_getalldeletedlists` `(txt:1042-1049)`: (1) общее число удал./заблок./неактуал.; (2) MFN лог.удал.; (3) MFN физ.удал.; (4) MFN неактуал.; (5) MFN заблок.; (6) maxMFN+1; (7) монопольная блокировка (`0`/`ERR_DBEWLOCK`). Списки `$0D0A`→`$3130`.

### (11) Вспомогательные `(txt:1180-1219)`
| № | Функция | Вход | Возврат |
|---|---|---|---|
| 11.1 (txt:1183) | `IC_nooperation` («жив») | нет | int |
| 11.2 (txt:1190) | `IC_getposting` элемент ссылки | APost;AType(0 mfn/1 tag/2 occ/3 pos) | элемент |
| 11.3 (txt:1201) | `IC_reset_delim` `$0D0A`→`$3130` | Aline | Pchar |
| 11.4 (txt:1211) | `IC_delim_reset` `$3130`→`$0D0A` | Aline | Pchar |

### (12) Полнотекстовые БД `(txt:1221-1222)` — `(пока нет)`.

## Модель записи и статусов
MFN — номер записи в мастер-файле `(txt:355)`; `IC_maxmfn`→`maxmfn+1` `(txt:463-471)`.
Клиентское представление (`IC_read`) `(txt:368-374)`:
```
0#<код возврата>
MFN#<статус записи>
0#<номер версии записи>
TAG#<значение поля>   ← TAG = числовая метка
```
Подполя — односимвольный разделитель (`IC_field`) `(txt:502-515)`. Ссылка `mfn#tag#occ#pos#` `(txt:769-770)`, разбор `IC_getposting` `(txt:1190-1199)`.
Признаки записи: логич.удалённость (`IC_recdel`/`IC_recundel`/`IC_isDeleted`) `(txt:601-621,676-684)`; заблокированность (`IC_recunlock`/`IC_isLocked`, серверно `IC_runlock`) `(txt:623-632,666-674)`; актуализированность (`Aifupdate`/`IC_ifupdate`/`IC_isActualized`) `(txt:447-461,656-664)`. Версионирование: `VERSION_ERROR` при несовпадении версий, answer=реальная запись `(txt:409-410)`. Удаление: лог.(`REC_DELETE`)/физ.(`REC_PHYS_DELETE`) `(txt:365-366)`; в списках N=1 физ./0 лог. `(txt:1029)`.

## Поиск через протокол
Два вида `(txt:1224-1228)`: прямой (инвертированный файл) и последовательный (перебор; БОЛЬШЕ/МЕНЬШЕ, НАЛИЧИЕ/ОТСУТСТВИЕ).
**Прямой** `(txt:1230-1265)`. Операнд: `"<префикс><термин>$"/(tag1,…tagN)` `(txt:1235)`. `$`=правое усечение `(txt:1240)`; `"`=ограничитель при пробел/скобки/#/операторы `(txt:1241)`; `/(...)`=квалификация по меткам `(txt:1242)`. Операторы: `+`(ИЛИ), `*`(И), `^`(НЕ, двуместный), `(G)`(в одном поле), `(F)`(в одном повторении), `.`(в одном повторении подряд) `(txt:1243-1249)`. Приоритет: `.`→`(F)`→`(G)`→`* ^`→`+`, слева направо; скобки объединяются только `+ * ^` `(txt:1250-1257)`. Примеры `(txt:1259-1265)`.
**Последовательный** `(txt:1267-1276)`: формат `if <выражение> then '1' else '0' fi`; запись подходит, если результат содержит `'1'`. В АРМах Читатель/Каталогизатор (свободный поиск) — без `if…fi` `(txt:1275)`; регулярный последовательный → задаётся в `<dbname>.fst` `(txt:1276)`.

## Коды доступа к АРМам и коды ошибок
**АРМ (`arm` в `IC_reg`)** `(txt:117-123)`: `IRBIS_READER`(Читатель), `IRBIS_CATALOG`(Каталогизатор), `IRBIS_COMPLECT`(Комплектатор), `IRBIS_BOOKLAND`(Книговыдача), `IRBIS_ADMINISTRATOR`(Администратор — для группы 10), `IRBIS_BOOKPROVD`(Книгообеспеченность).
**Коды ошибок (символьные имена; числовые — в `irbis64_client.pas`):** `ZERO` (txt:131); `ERR_USER` (txt:99); `ERR_BUSY` (txt:100); `ERR_UNKNOWN` (txt:101); `ERR_BUFSIZE` (txt:102); `CLIENT_NOT_IN_LIST` (txt:132); `WRONG_PASSWORD` (txt:133); `CLIENT_LIST_OVERLOAD` (txt:134); `CLIENT_NOT_ALLOWED` (txt:135); `REC_DELETE` (txt:365); `REC_PHYS_DELETE` (txt:366); `READ_WRONG_MFN` (txt:367); `VERSION_ERROR` (txt:410); `TERM_NOT_EXISTS` (txt:702); `TERM_LAST_IN_LIST` (txt:703); `TERM_FIRST_IN_LIST` (txt:704); `ERR_DBEWLOCK` (txt:1049). Константы: `MAX_POSTINGS_IN_PACKET` (txt:695,762,825); `CLIENT_TIME_LIVE` (txt:1188). В документе реальных ПДн/паролей нет.

## Открытые вопросы (TODO recon)
- `TODO(recon #0301: проводной формат нативного TCP-протокола (порт 6666) — документ описывает только C-API dll, не пакеты сокета; нужен анализ трафика/дизассемблирование dll.)`
- `TODO(recon #0302: числовые значения всех кодов возврата — в irbis64_client.pas (txt:97); найти .pas из SDK.)`
- `TODO(recon #0303: структура PBuffer для IC_getbinaryresourse (txt:316-320) — в .pas.)`
- `TODO(recon #0304: числовые значения Apath и разница DBNPATH2/3/10, отсутствие DBNPATH1/4..9 (txt:259-264).)`
- `TODO(recon #0305: раздел 12 полнотекстовые БД «(пока нет)» (txt:1221-1222) — проверить новую версию.)`
- `TODO(recon #0306: формат задания глоб. корректировки Agbl (txt:996) — Общее описание системы.)`
- `TODO(recon #0307: структура @tab и RTF-вывода IC_print/IC_stat (txt:962,983).)`
- `TODO(recon #0308: квалификация /(tag) и «вторая часть ссылки» — Приложение 5 Общего описания (txt:1242).)`
- `TODO(recon #0309: числовые коды результата расформатирования (txt:391,879).)`
- `TODO(recon #0310: соглашение вызовов — stdcall явно только у IC_update/IC_adm_getalldeletedlists/IC_adm_newdb (txt:395,1033,1073); по умолчанию для всей dll?)`

---
**Сводка:** 80 функций в 11 рабочих группах (раздел 12 пуст). Разбивка: (2) общие — 8; (3) ресурсы/INI — 6; (4) мастер-файл — 8; (5) запись — 17; (6) словарь — 7; (7) поиск — 2; (8) форматирование — 3; (9) пакетная — 3; (10) администратор — 15; (11) вспомогательные — 4. 6 кодов доступа к АРМам, 18 символьных кодов ошибок. Главный пробел: проводной TCP-протокол (порт 6666) в документе не описан — только C-API. TODO recon: 10 (#0301–#0310).
