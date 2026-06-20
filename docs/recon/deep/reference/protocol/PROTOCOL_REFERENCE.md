# PROTOCOL_REFERENCE — нативный протокол ИРБИС64 (клиентский C-API)

> **Источник:** `docs/reference/irbis64_client_dll_TEXT.txt` (1277 строк, прочитан целиком). Ссылки `(txt:N)`.
> **Ограничение источника:** документ описывает **C-API библиотеки `irbis64_client.dll`** (прототипы Pascal, коды возврата, форматы строк в буферах). **Байтовый/проводной формат TCP-пакетов :6666 в документе НЕ описан** — см. §7 (gap). Ниже — семантика «полезной нагрузки», которую веб-бэкенд формирует и разбирает. Углубляет [FINDINGS_03_protocol](../../FINDINGS_03_protocol.md).

## 1. Общая модель данных

### 1.1 Типы
Два типа во всех сигнатурах `(txt:93)`: `integer` (коды/MFN/размеры/флаги) и `Pchar` (C-строка: байты `char` + `\0`) `(txt:96)`. Одиночный `char` — параметр `arm` в `IC_reg` `(txt:110)` и `delim` в `IC_field` `(txt:504)`.

### 1.2 Кодировки — карта UTF-8 ↔ ANSI
Правило: **все строки UTF-8, КРОМЕ явных ANSI-исключений** `(txt:94)`:
| Где | Напр. | Кодировка | Ссылка |
|---|---|---|---|
| По умолчанию (данные/термины/форматы) | вход/выход | **UTF-8** | (txt:94) |
| `IC_reg` → answer (INI-профиль) | выход | ANSI | (txt:136) |
| `IC_update_ini` ← inifile | вход | ANSI | (txt:244) |
| `IC_getresourse` → answer | выход | ANSI | (txt:274) |
| `IC_getresoursegroup` → answer | выход | ANSI | (txt:309) |
| `IC_putresourse` ← Aresourse | вход | ANSI | (txt:337) |
| `IC_adm_getclientlist`/`getclientslist`/`getprocesslist` → answer | выход | ANSI | (txt:1144,1156,1168) |

Закономерность: **ресурсы (файлы сервера) и INI/списки клиентов — ANSI**; библиографические данные — UTF-8. `IC_getbinaryresourse` отдаёт сырой бинарь без перекодировки `(txt:326)`.

### 1.3 Разделители строк `$0D0A` vs `$3130`
| Разделитель | Байты | Когда |
|---|---|---|
| `$0D0A` | CR LF | реальный разделитель строк верхнего уровня `(txt:96)` |
| `$3130` | символы «1»,«0» | псевдоразделитель: заменяет `$0D0A` внутри вложенного значения, помещённого в одну строку внешнего набора `(txt:308)` |

Конверсия: `IC_reset_delim` (`$0D0A→$3130`, упаковка) / `IC_delim_reset` (`$3130→$0D0A`, распаковка) `(txt:1201-1219)`.
**$3130 в ОТВЕТАХ** (распаковывать): `IC_getresoursegroup` `(txt:308)`, `IC_nexttrmgroup`/`prevtrmgroup` `(txt:736)`, `IC_search`/`searchscan`/`sformatgroup`/posting-format `(txt:812,841,858,920)`, `IC_adm_getalldeletedlists` `(txt:1044-1047)`.
**$3130 во ВХОДЕ** (упаковывать): `IC_updategroup`/`_sinhronize` `(txt:422)`, `IC_print.Ahead` `(txt:932)`, `IC_stat.Astat` `(txt:970)`, `IC_gbl.Agbl` `(txt:996)`.
**Особый `$30`** (символ «0») — разделитель полей внутри ответа `IC_nexttrmgroup`: `<ссылка>$30<термин>$30<результат>` `(txt:732)`. Не путать с `$3130`.

### 1.4 Буферы и переполнение
Память под `answer` выделяет **вызывающая программа**; размер — отдельный `abufsize` `(txt:95)`. Переполнение → `ERR_BUFSIZE` `(txt:102)`; у `IC_nexttrm` при этом **в буфере ничего** → ретрай с бо́льшим буфером `(txt:705)`. Исключение: `IC_getbinaryresourse` — память `PBuffer` выделяет/освобождает сама DLL `(txt:320)`.

### 1.5 Соглашение вызовов
Явно `stdcall` только у `IC_update`, `IC_adm_getalldeletedlists`, `IC_adm_newdb` `(txt:395,1033,1073)`. `TODO(Проход Б #01: уточнить calling convention всей DLL — dumpbin /EXPORTS.)`

### 1.6 Файл констант
Числовые значения кодов и все именованные константы — в `irbis64_client.pas` `(txt:97)`. `TODO(Проход Б #02: добыть irbis64_client.pas из SDK — числовые значения ВСЕХ кодов; известно лишь CLIENT_NOT_ALLOWED = -3338 из контекста проекта.)`

## 2. Сессия

### 2.1 `IC_reg` — регистрация (первой!) `(txt:106-139)`
```pascal
function IC_reg(aserver_host: Pchar; aserver_port: Pchar; arm: char;
                user_name, password: Pchar; var answer: Pchar; abufsize: integer): integer;
```
| # | Параметр | Тип | Значение |
|---|---|---|---|
| 1 | aserver_host | Pchar | IP сервера, напр. `192.168.5.140` (txt:115) |
| 2 | aserver_port | Pchar | порт **строкой** — `6666` (txt:116) |
| 3 | arm | char | тип АРМа (один символ) (txt:117) |
| 4 | user_name | Pchar | логин (txt:124) |
| 5 | password | Pchar | пароль (txt:125) |
| 6 | answer | var Pchar | выход (txt:126) |
| 7 | abufsize | integer | размер буфера (txt:127) |

**Значения `arm`** `(txt:117-123)`: `IRBIS_READER` (Читатель), `IRBIS_CATALOG`, `IRBIS_COMPLECT`, `IRBIS_BOOKLAND`, `IRBIS_ADMINISTRATOR` (для группы 10, txt:1004), `IRBIS_BOOKPROVD`. `TODO(Проход Б #03: однобуквенные литералы IRBIS_* — из .pas.)`
**Ответ:** INI-профиль пользователя (набор строк `$0D0A`, **ANSI**) `(txt:136)`.
**Коды:** `ZERO` / `CLIENT_NOT_IN_LIST` / `WRONG_PASSWORD` / `CLIENT_LIST_OVERLOAD` / `CLIENT_NOT_ALLOWED` (= **-3338**) `(txt:130-135)`.
До `IC_reg` допустимы только `IC_set_*` `(txt:138-139)`.

### 2.2 Завершение/keepalive
`IC_unreg(user_name)` `(txt:143-154)`; `IC_nooperation` keepalive `(txt:1183-1188)`; `IC_set_client_time_live(Aopt мин, умолч.1)` `(txt:156-168)`. Сервер авто-разрегистрирует по `CLIENT_TIME_LIVE` (из `irbis_server.ini`) `(txt:154,1188)`. Бэкенду: слать keepalive по таймеру или переоткрывать сессию.

### 2.3 Общие параметры `(txt:170-235)`
`IC_set_show_waiting(сек,3)`; `IC_set_webserver(1/0,0)`; `IC_set_webcgi(умолч. /cgi-bin/wwwirbis.exe)`; `IC_set_blocksocket(1/0,0)`; `IC_isbusy`→1/0. Web-шлюз — альтернативный CGI-транспорт `(txt:185-212)`; для веб-бэкенда нерелевантно (он сам шлюз по TCP). 

## 3. Функции по группам — сигнатуры/структуры/коды

Общие коды `(txt:98-102)`: `ERR_USER`, `ERR_BUSY`, `ERR_UNKNOWN`, `ERR_BUFSIZE`.

### 3.1 Группа 3 — Ресурсы/INI `(txt:237-345)`
- `IC_update_ini(inifile)` — пополнить серверный INI-профиль; вход ANSI `(txt:241-252)`.
- `IC_getresourse(Apath:int; Adbn,Afilename; var answer; abufsize)` — текст ресурса, ANSI, кэш `(txt:256-277)`. `Apath` `(txt:259-264)`: `SYSPATH`(\irbis64\), `DATAPATH`(\irbis64\datai\), `DBNPATH2/3/10` (каталог БД). `TODO(Проход Б #05: числовые Apath + разница DBNPATH2/3/10.)`
- `IC_clearresourse` — очистка кэша, без сервера `(txt:281-290)`.
- `IC_getresoursegroup(var acontext; var answer; abufsize)` — `acontext`: строки `Apath.Adbn.Afilename` (напр. `DBNPATH10.IBIS.BRIEF.PFT`); ответ ANSI, `$0D0A→$3130` `(txt:294-309)`.
- `IC_getbinaryresourse(Apath; Adbn,Afilename; var Abuffer:PBuffer)` — бинарь в `Abuffer^.data`, память DLL `(txt:316-326)`. `TODO(Проход Б #06: структура PBuffer.)`
- `IC_putresourse(Apath; Adbn,Afilename,Aresourse)` — запись текста (ANSI) на сервер `(txt:333-345)`.

### 3.2 Группа 4 — Мастер-файл `(txt:347-485)`
- `IC_read(Adbn; Amfn,Alock; var answer; abufsize)` — Alock 1/0; Ret `ZERO`/`REC_DELETE`/`REC_PHYS_DELETE`/`READ_WRONG_MFN`; answer = клиентское представление (§4) `(txt:351-374)`.
- `IC_readformat(...Aformat...; answer; answer1)` — `Aformat` = формат или `@имя`; answer1 = расформат, 1-я строка = код результата `(txt:381-391)`.
- `IC_update(Adbn; Alock,Aifupdate; var answer; abufsize) stdcall` — answer = исходная запись (клиент. представление), вернётся обновлённая; Ret `>0` = maxMFN, иначе ошибка (в т.ч. `VERSION_ERROR` → answer = реальная запись) `(txt:395-414)`.
- `IC_updategroup(...)` — записи: каждая = одна строка (`$0D0A→$3130`); буфер не обновляется (только статус+MFN) `(txt:418-429)`.
- `IC_runlock(Adbn;Amfn)` разблокировать (не для версионного режима) `(txt:433-445)`; `IC_ifupdate(Adbn;Amfn)` актуализировать `(txt:449-461)`; `IC_maxmfn(Adbn)`→`maxmfn+1` `(txt:465-471)`.
- `IC_updategroup_sinhronize(Alock,Aifupdate; Adbnames; var answer; abufsize)` — записи из разных БД (Adbnames по строке); применяется **только если успех для ВСЕХ** (транзакция) `(txt:475-485)`.

### 3.3 Группа 5 — Работа с записью (локально, без сервера) `(txt:487-684)`
`IC_fieldn`(порядк.№ поля/<0) · `IC_field`(значение поля/подполя; delim `$00`=всё поле) · `IC_fldadd`(nf=0→в конец) · `IC_fldrep`(пусто→удалить) · `IC_nfields` · `IC_nocc` · `IC_fldtag` · `IC_fldempty` · `IC_changemfn` · `IC_recdel`/`IC_recundel` · `IC_recunlock` · `IC_getmfn` · `IC_recdummy` · `IC_isActualized`/`IC_isLocked`/`IC_isDeleted`(1/0). Коды `ZERO`/`ERR_BUFSIZE`/`ERR_USER` `(txt:492-684)`.

### 3.4 Группа 6 — Словарь `(txt:686-814)`
- `IC_nexttrm(Adbn,Aterm; Anumb; answer; abufsize)` — Anumb 0=все ≤`MAX_POSTINGS_IN_PACKET`; Ret `ZERO`/`TERM_NOT_EXISTS`/`TERM_LAST_IN_LIST`/`TERM_FIRST_IN_LIST`/`ERR_BUFSIZE`; out строки `nnn#<термин>` (nnn=число ссылок) `(txt:690-711)`.
- `IC_nexttrmgroup(...Aformat...)` — out `nnn#<ссылка>$30<термин>$30<результат>`, ссылка=`mfn#tag#occ#pos#` `(txt:715-738)`.
- `IC_prevtrm`/`IC_prevtrmgroup` — обратный порядок `(txt:745-753)`.
- `IC_posting(Adbn,Aterm; Anumb,Afirst; answer; abufsize)` — Afirst=0→только число ссылок; out строки `mfn#tag#occ#pos#` `(txt:757-770)`.
- `IC_postinggroup(Adbn,Aterms; answer; abufsize)` — по строке на термин: `nnn#<первая ссылка>` `(txt:777-792)`.
- `IC_postingformat(...)` — 2 буфера: answer1 `mfn#<результат>`, answer `mfn#tag#occ#pos#` `(txt:796-814)`.

**`Aformat` — 5 способов** `(txt:719-725)`: (1) строка формата; (2) `@имя`; (3) `@` (оптимизированный по виду записи); (4) `*` (по ссылке: для `1.200.2.3` → 2-е повторение 200); (5) пусто (без форматирования). Спецсочетание `***` → метка из 1-й ссылки (`v***`→`v200`). В `IC_search`/`IC_sformat` доступны 1–3+пусто (без `*`); в `IC_record_sformat` способ `@` не работает `(txt:827-831,871-874,887)`.

### 3.5 Группа 7 — Поиск `(txt:816-858)`
- `IC_search(Adbn,Asexp; Anumb,Afirst; Aformat; answer; abufsize)`: Asexp = прямое выражение (§5); **Anumb** = размер страницы (0=все ≤MAX); **Afirst** = смещение 1-based (0→вернуть только КОЛИЧЕСТВО найденных); Ret `≥0` = число найденных; out строки `mfn#<результат>` (`$0D0A→$3130`) `(txt:820-841)`.
- `IC_searchscan(...Amin,Amax; Aseq...)`: последовательный поиск; Amin=0→1, Amax=0→maxMFN; Aseq = формат→`0`/`1`; если задан и Asexp — последовательный по результату прямого `(txt:845-858)`.

### 3.6 Группа 8 — Форматирование `(txt:860-920)`
`IC_sformat(Adbn;Amfn;Aformat...)`(способы 1–3) · `IC_record_sformat(Adbn;Aformat;Arecord...)`(без `@`) · `IC_sformatgroup(Adbn;Amfnlist;Aformat...)` — Amfnlist диапазон(`0/min/max`) или список(`N/mfn…`); out `mfn#<результат>` `(txt:866-920)`.

### 3.7 Группа 9 — Пакетная `(txt:922-1000)`
- `IC_print(Adbn,Atab,Ahead,Amod,Asexp; Amin,Amax; Aseq,Amfnlist; answer; abufsize)` — Atab=`@имя` табличной формы, Ahead ≤3 строк; out **RTF**; результат = пересечение трёх списков (прямой ∩ последовательный ∩ Amfnlist) `(txt:927-962)`.
- `IC_stat(Adbn,Astat,Asexp; Amin,Amax; Aseq,Amfnlist...)` — Astat задания `FMT,N1,N2,N3` (FMT=`поле^подполе`, N1 длина, N2 макс. значений, N3 сортировка 0/1/2); out RTF `(txt:966-983)`.
- `IC_gbl(Adbn,Aifupdate,Agbl,Asexp; Amin,Amax; Aseq,Amfnlist...)` — Agbl = `@имя` или строки задания; out протокол `(txt:987-1000)`. `TODO(Проход Б #07: грамматика задания Agbl.)`
**Amfnlist 3 формата** `(txt:936-952)`: диапазон `0/min/max`; список `N/mfn…`; отрицательный `-N/mfn…` (все КРОМЕ).

### 3.8 Группа 10 — Администратор (`IRBIS_ADMINISTRATOR`) `(txt:1003-1178)`
`IC_adm_restartserver` · `IC_adm_getdeletedlist`(строки `N#mfn`, N 1=физ/0=лог) · `IC_adm_getalldeletedlists` (stdcall; 7 строк, §3.8.1) · `IC_adm_dbempty`/`dbdelete`/`newdb`(stdcall; Adef название, AReader 1/0) · `IC_adm_dbunlock`/`dbunlockmfn` · `IC_adm_dbstartcreatedictionry`/`dbstartreorgdictionry`/`dbstartreorgmaster` · `IC_adm_getclientlist`/`getclientslist`/`getprocesslist`(ANSI) · `IC_adm_setclientslist(AClientMnu)` `(txt:1003-1178)`. (Имена в оригинале с опечаткой `dictionry` — использовать как есть.)
**§3.8.1 `IC_adm_getalldeletedlists` — 7 строк** `(txt:1042-1049)`: (1) число удал.+заблок.+неактуал.; (2) MFN лог.удал.; (3) MFN физ.удал.; (4) MFN неактуал.; (5) MFN заблок.; (6) maxMFN+1; (7) монопольная блокировка `0`/`ERR_DBEWLOCK`.

### 3.9 Группа 11 — Вспомогательные `(txt:1180-1219)`
`IC_nooperation`(keepalive) · `IC_getposting(APost; AType)` AType 0=mfn/1=tag/2=occ/3=pos · `IC_reset_delim`(`$0D0A→$3130`) · `IC_delim_reset`(`$3130→$0D0A`).
### 3.10 Группа 12 — Полнотекстовые БД `(txt:1221-1222)` — `(пока нет)`.

## 4. Клиентское представление записи `(txt:368-374)`
```
0#<код возврата>
MFN#<статус записи>
0#<номер версии записи>
TAG#<значение поля>
...
```
TAG = числовая метка поля; разделитель «метка#значение» = `#`. **Подполя** извлекаются `IC_field` с односимвольным delim (`$00`=всё поле) — фиксированный литерал-разделитель подполей в тексте не назван `(txt:509)`. `TODO(Проход Б #09: символ-разделитель подполей (обычно '^').)` **Ссылка** = `mfn#tag#occ#pos#` `(txt:769,1196)`. Для группового обновления — вся запись в одну строку (`$0D0A→$3130`) `(txt:422)`.
**Статусы записи:** логич.удаление (`IC_recdel`/`recundel`/`isDeleted`); заблокированность (`IC_recunlock`/`isLocked`/серверно `IC_runlock`); актуализированность (`IC_ifupdate`/`Aifupdate`/`isActualized`). Версионирование: строка 3 = номер версии; конфликт → `VERSION_ERROR` `(txt:410)`.

## 5. Грамматика поискового выражения `(txt:1224-1276)`

### 5.1 Прямой поиск — операнд `(txt:1233-1242)`
```
"<префикс><термин>$"/(tag1,tag2,…tagN)
```
- `<префикс>` — вид словаря (напр. `A=`,`K=`,`V=`); `<термин>` — термин;
- `$` — **правое усечение** (без него — точное);
- `"…"` — ограничитель (обязателен при пробеле/скобках/`#`/символах операторов);
- `/(tags)` — **квалификация по меткам полей**.
`TODO(Проход Б #10: полный список префиксов — из *.fst/меню.)`

### 5.2 Операторы и приоритет `(txt:1243-1256)`
| Оператор | Смысл | Приоритет |
|---|---|---|
| `.` (в окружении пробелов) | в одном повторении подряд | 1 (высший) |
| `(F)` | в одном повторении поля | 2 |
| `(G)` | в одном поле | 3 |
| `*` И · `^` НЕ (двуместный) | — | 4 |
| `+` ИЛИ | — | 5 (низший) |
Один уровень — слева направо. **Скобочные группы объединяются ТОЛЬКО `+ * ^`** (контекстные `(G)/(F)/.` между скобками недопустимы) `(txt:1257)`.
Примеры `(txt:1259-1265)`: `("A=Иванов$"+"A=Петров$")*("V=03"+"V=05")`; `"K=очист$"/(200,922)*"K=вод$"/(200,922)`.

### 5.3 Последовательный поиск `(txt:1267-1276)`
Выражение = формат ИРБИС; запись подходит, если результат содержит `'1'`. Форма: `if <логическое выражение> then '1' else '0' fi`. В свободном поиске Читателя/Каталогизатора — только `<логическое выражение>` (без обёртки). Регулярный последовательный → переносить в `<dbname>.fst`.

## 6. Модель ошибок
18 символьных кодов `(txt:99-1049)`: `ZERO`, `ERR_USER/BUSY/UNKNOWN/BUFSIZE`, `CLIENT_NOT_IN_LIST/WRONG_PASSWORD/CLIENT_LIST_OVERLOAD/CLIENT_NOT_ALLOWED`(=-3338), `REC_DELETE/REC_PHYS_DELETE/READ_WRONG_MFN`, `VERSION_ERROR`, `TERM_NOT_EXISTS/LAST_IN_LIST/FIRST_IN_LIST`, `ERR_DBEWLOCK`. Константы: `MAX_POSTINGS_IN_PACKET`, `CLIENT_TIME_LIVE`.
**Знаковое соглашение (важно для бэкенда):** нельзя слепо «<0=ошибка» — у ряда функций **положительный возврат = ДАННЫЕ, не код**: `IC_update`/`updategroup`→`>0`=maxMFN; `IC_maxmfn`→maxmfn+1; `IC_search`/`searchscan`→`≥0`=число найденных (0 — валидно); `IC_posting`(Afirst=0)→число ссылок; `IC_fieldn`→номер или `<0`; `IC_is*`→1/0. Нужна таблица «функция→семантика возврата». `TODO(Проход Б #11: числовые значения кодов + знаковое соглашение — из .pas.)`

## 7. Проводной формат TCP-пакета (GAP)
Документ — только C-API DLL; **байтовый формат пакетов :6666 отсутствует.** `TODO(Проход Б #12: снять реальный проводной формат с живого сервера/клиента BookCabinet)`:
- кадр запроса: общий заголовок (длина/число строк), кодировка `arm`/`user`/`password`/`client_id`/`command_code`/`query_id`;
- код команды для каждой `IC_*` (имя ↔ код на проводе);
- разделители на проводе (`$0A`/`$0D0A`; где `$3130`);
- кадр ответа: где код возврата сервера, как отделяется заголовок от тела;
- кодировка на проводе (UTF-8 данные / ANSI ресурсы — проверить);
- handshake `IC_reg` (что сервер шлёт помимо INI; присвоение client_id);
- client_id/query_id (инкремент, для keepalive и параллельных запросов).
Метод: BookCabinet против тестового :6666 + Wireshark/прокси, сопоставить кадры с `IC_*`; либо дизассемблировать функции сериализации перед `send()`.

## 8. Счётчики
80 функций (11 групп; гр.12 пуста): гр.2=8, 3=6, 4=8, 5=17, 6=7, 7=2, 8=3, 9=3, 10=15, 11=4. 18 символьных кодов ошибок; 6 кодов АРМ; 5 кодов Apath; 6 операторов поиска + 5 уровней приоритета; 5 способов Aformat; 3 формата Amfnlist; 3 разделителя (`$0D0A`/`$3130`/`$30`). Числовых значений в тексте: 0 (все в `.pas`; `-3338` из контекста). **TODO(Проход Б): 12** (#01–#12) — большинство закрываются файлом `irbis64_client.pas` из SDK + снятием трафика BookCabinet.
