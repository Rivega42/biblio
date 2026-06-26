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
