# Cutover jirbis → Biblio (узел 4) — план

Готовится ДО доступа к MySQL, чтобы по приходу дампа выполнить быстро. Связано:
[[prod-reality-spb-gtb]], мастер миграции ИРБИС (#225), социальный слой own-store.

## 1. AS-IS — где что живёт

| Данные | Источник | Переносить? |
|---|---|---|
| Учётка читателя (билет), интернет-пароль | **ИРБИС RDR** (поле 30 `RI=`, пароль 130 plaintext / 100 MD5) | ❌ бесшовно |
| ПДн читателя (ФИО/адрес/тел) | **ИРБИС RDR** (10–12/13/17–18/32) | ❌ читаем из ИРБИС, шифруем у себя |
| Выдачи / формуляр | **ИРБИС RDR** (поле 40, живой) | ❌ через TCP |
| Заказы / брони / очередь | **ИРБИС RQST** | ❌ (наш holds #222 параллелен) |
| **Рейтинги / отзывы / Top-N** | **Joomla MySQL** (`*_irbis_*`) | ✅ → `reader_review` |
| **Сохранённые поиски / алерты** | **Joomla MySQL** (или RDR — уточнить) | ✅ → `saved_search` |
| **История чтения** | Joomla (если есть) | ✅ опц. → `reader_history` |
| Новости / CMS-контент | **Joomla MySQL** (`#__content`) | ✅ опц. → tenant-content (#248) |
| Joomla-веб-админы / SSO | **Joomla MySQL** (`#__users`) | ◑ опц. → `staff_account` / `reader_identity` |

**Главное:** ~всё «важное» читателя (учётка/пароль/выдачи/заказы) уже в ИРБИС → **бесшовно, миграции не требует.** Из Joomla тянем только соц-слой + CMS, которых в ИРБИС НЕТ.

## 2. Маппинг (Joomla → Biblio) — уточняется дампом

| Joomla-таблица (типовая `*_irbis_*`) | → Biblio-стор | Поля цели |
|---|---|---|
| `*_irbis_rating`/`_vote`/`_comment` | `reader_review` | ticket, db, mfn, rating, text, ts |
| `*_irbis_savedquery`/`_alert` | `saved_search` | ticket, name, db, prefix, query, ts |
| `#__content`/`#__categories` | tenant-content (опц.) | slug, title, body, ts |
| `#__users` (только админы) | `staff_account`/`reader_identity` | по ролям |

Целевые таблицы соц-слоя уже есть: `access/store.py` (`reader_review`/`reader_history`/`saved_search`), сервис `access/social.py`.

## 3. План импорта
**`tools/migrate_joomla.py`** (написать по приходу дампа): парс mysqldump → ETL → загрузка в own-store целевого тенанта.
- **Идемпотентность:** UPSERT по ключам (`UNIQUE(ticket,db,mfn)` / `saved_search`) → re-run не дублирует.
- **152-ФЗ:** дамп НЕ коммитить (`.gitignore` `*.sql`/`jirbis_*`); `reader_name` шифровать `crypto.encrypt`; аудит операций.
- **Критичный маппинг:** `jos_users.id ↔ RDR.ticket` (без него рейтинги/поиски не привязать к читателю).
- **Прогон:** dry-run на staging → сверка объёмов → cutover в боевой тенант.

## 4. Уже бесшовно (без миграции)
- Вход читателя — билет+пароль из RDR поля 130 (работает, ~258 читателей).
- Формуляр/выдачи (RDR 40) и заказы (RQST) — живьём через TCP-сервер ИРБИС.
- Полки/брони/история/отзывы — наши own-store (separate от ИРБИС).

## 5. Открытые вопросы (снимаются дампом + доступом к MySQL)
1. Точные имена таблиц соц-слоя (`SHOW TABLES LIKE '%irbis%'`).
2. **Поле связи `jos_users.id ↔ RDR.ticket`** (критично).
3. Объёмы (COUNT рейтингов/комментов/поисков).
4. Где живут сохранённые запросы (Joomla или RDR).
5. Формат поля 130 (plaintext/MD5) — подтвердить образцом.
6. Нужен ли перенос CMS-контента (решает библиотека).

## 6. Якоря кода
- Мастер ИРБИС→Biblio: `tools/migrate_irbis.py` (`Migrator`, `migrate_catalog`/`migrate_readers`, `crypto.encrypt` ПДн).
- Эндпойнты: `core.py` `admin_migrate_inspect`/`admin_migrate_run`; фронт `api.ts` `migrateInspect`/`migrateRun`.
- Соц-слой: `access/social.py` (reviews/history/saved_searches/recommendations), `access/store.py` (CRUD соц-таблиц), `access/holds.py`.

**Готово к запуску по приходу доступа к MySQL.** Инструменты на месте; нужен дамп + уточнение схемы Joomla и маппинга user↔ticket.

---

## 7. Обновление по факту доступа (2026-06-27)

Доступ к боевой БД получен (портативный `C:\jirbis2_server\`, Windows; БД `jirbis2`, MariaDB 10.1.38, префикс `jos_`, root/локально). Схема ключевых таблиц снята, объёмы измерены, код компонента `com_irbis` отреверсен. Дамп с данными — ПДн (152-ФЗ), **off-git**; отчёты recon держим локально.

### 7.1. Резолв открытых вопросов из §5
1. **Имена таблиц соц-слоя** — сняты (`mysqlshow`, ~180 таблиц `jos_`). Соц-слой как «WEB-2.0 community» (форум Kunena, галереи Phoca, события, комментарии, опросы, FAQ) **МЁРТВ** на боевом → НЕ мигрируем.
2. **Связь `jos_users.id ↔ RDR.ticket`** — снимается с реальной строкой `jos_users` при дизайне #294; читателей это не блокирует (вход бесшовный через RDR 130).
3. **Объёмы** — `svk_cs`=**30531** (единственный крупный живой датасет), `users`=**240**, `reservations`=**34**, `rec_rate`=4, `rdr_cache`=2, `bases`=20, `mhr`=11, `content`=7; `rec`=0, `req`/`req_rec`/`portions`=0, `ai_chat_feedback`=0.
4. **Сохранённые поиски** — это `jos_req`+`jos_req_rec`+`jos_portions` (Joomla), но **пусто** → greenfield (мигрировать нечего, фича строится с нуля, ребро 10.1 ИРИ).
5. **Формат поля 130** — подтверждён образцом: **9-симв plaintext** (258/258), поля 24/100 ОТСУТСТВУЮТ. Наш `auth_reader` уже совпадает → читатели бесшовны без миграции.
6. **CMS-контент** — `jos_content`=7 статей → опц. в tenant-content (#248).

### 7.2. Коррекция AS-IS — реальный вес cutover
- **Бесшовно (без миграции):** вход читателя (RDR 130), формуляр/выдачи (RDR 40), заказы (RQST), полки/брони/отзывы (own-store).
- **Реальные данные на перенос:** сводный каталог `svk_cs` (30531) · учётки `jos_users` phpass `$P$D` len34 (240, перенос хэшей off-git + phpass-verifier + upgrade-on-login) · бронь визита `jos_reservations` (34) · мелкий конфиг (`bases` 20 / `mhr` 11 / `content` 7) · обложки `com_irbis\images` ≈ **7.6 ГБ** (~270k файлов).
- **Greenfield (данных нет):** кэш каталога `jos_rec`, сохранённые запросы/SDI, AI-чат-фидбэк.
- **Папка jirbis 18 ГБ:** ~9 ГБ логи/tmp (хлам) + 7.6 ГБ обложки + ~350 МБ БД + код. Скрытого корпуса оцифровки НЕТ.

### 7.3. AI-ассистент jirbis — реверс (вход в #293)
Ассистент **реальный и инструментальный (MCP)**, не «болталка». Карта кода (`com_irbis`):

| Файл | Роль |
|---|---|
| `includes/ji_ai.php` (27.5 КБ) | ядро чата (секрет-маркеры API-ключа в стр. 1/13) |
| `includes/answer.php` (30 КБ) | диспетчер; **`case 'mcp':`** (стр.556) = мост к инструментам |
| `units/ji_ai_static.php` + `css/jirbis_ai.css` | UI-виджет |
| `mcp/grnti.php` (8.3 КБ) | **единственный MCP-инструмент** — рубрикатор ГРНТИ; HTTP-MCP `localhost:8088/.../mcp/grnti.php`, заголовок `Mcp-Session-Id`, JSON-RPC `initialize/tools` |
| `llm_router` (в `htdocs\jirbis2`) | LLM-прокси (теневой llm_router) |

Т.е. `com_irbis\mcp` = ровно **один файл** `grnti.php`, не папка-фреймворк. Архитектура: PHP-модуль (ji_ai) → llm_router (LLM) + MCP-инструменты (grnti — минимальный образец). Схема фидбэка `jos_ai_chat_feedback` определена в `update_scripts/update_tables_and_cfg.php:616-618` (`tool_calls_json` MEDIUMTEXT, `deepthink` TINYINT). Это рабочий паттерн «инструментальный поиск-агент» под #293 (направление: неформальный тон, проактивно сам ищет и предлагает).

### 7.4. Заведённые задачи
Эпик **#298**; **#294** учётки phpass (бесшовный вход + upgrade-on-login); **#295** сводный каталог `svk_cs`; **#296** бронь посещения; **#297** мелкий конфиг + обложки; **#293** AI поиск-агент (инструментальный).

### 7.5. Следующий шаг
Дамп исходников `ji_ai.php` / `answer.php` / `mcp/grnti.php` / `ji_ai_static.php` (с маскировкой секретов) + дерево `llm_router` → разбор архитектуры и дизайн агента Biblio в #293. По кредам можно стартовать #294 независимо (не зависит от папок jirbis).
