# J-IRBIS MySQL — что нашли и подготовили (ответ на ACCESS_REQUEST)

> Ответ на [`JIRBIS_MYSQL_ACCESS_REQUEST.md`](JIRBIS_MYSQL_ACCESS_REQUEST.md). Метаданные сняты **read-only** с боевого `.55` (SPGTB-SRV-02), **2026-06-27**. **ПДн здесь НЕТ** — дамп с данными хранится off-git (§5).

## 1. Стек и расположение
- **J-IRBIS 2.5.28 «Ember»** (на базе Joomla 2.5) — бандл `C:\jirbis2_server\` на `.55`.
- Apache + **бандл-MySQL на порту `3307`** (localhost, наружу не торчит — потому скан `3306` её не видел).
- Joomla-сайт: `C:\jirbis2_server\htdocs\jirbis2\`.

## 2. База данных
| Параметр | Значение |
|---|---|
| Имя БД | **`jirbis2`** (НЕ `jirbis` — поправка к запросу) |
| Префикс таблиц | `jos_` |
| Доступ | `root@localhost`, порт **`3307`** |
| Кодировка | **`utf8_general_ci`** (charset#33 в заголовке `.frm` — подтверждено; **НЕ cp1251**) |
| Движок | **MyISAM** (178 табл.) + 1 **InnoDB** (`jos_ai_chat_feedback`) |
| Объём | **179 таблиц, 113 МБ** |

## 3. Ключевые таблицы (для миграции)
| Таблица | Размер | Что | ПДн |
|---|---|---|---|
| `jos_users` | 0.04 МБ (~240) | учётки + phpass-хэши → upgrade-on-login (#294) | **да** |
| `jos_user_profiles` / `jos_user_usergroup_map` (×2) | ~0 | профили / группы-роли | да |
| `jos_ai_chat_feedback` (InnoDB) | схема, **~0 строк** | история AI-ассистента (#293) | да |
| `jos_reservations` | мелкая | брони CMS-стороны | да |
| `jos_content_rating` | мелкая | соц-слой (рейтинги) | нет |
| `jos_content` / `jos_menu` (×2) / `jos_modules` (×2) | мелкие | CMS-контент / навигация / баннеры | нет |

**Балласт (НЕ переносить):** `jos_jstats_*` (15 таблиц, ~60 МБ — статистика посещений), `jos_session` (×2, ~13 МБ — сессии).

## 4. Заметки по схеме
- Отдельных `*irbis*`-таблиц не нашёл — `com_irbis` использует стандартные `jos_*`; соц-слой = `jos_content_rating` и пр.
- Кодировка **utf8** на уровне таблиц → импорт с `--default-character-set=utf8` (риск «кракозябр» снят).
- `jos_ai_chat_feedback` — InnoDB: для restore нужен `ibdata1`, но строк 0 → важна только схема (есть в `.frm`).

## 5. Дамп (ПДн — off-git, 152-ФЗ)
- Снята **raw-копия** каталога `data\jirbis2` (113 МБ; MyISAM переносимы пофайлово) → **off-git, root-only**, на pve `/root/jirbis2-offgit/`. **В репозиторий НЕ кладётся.**
- Для чистого логического дампа: загрузить raw-копию в MySQL 5.x → `mysqldump --single-transaction --default-character-set=utf8 jirbis2 > jirbis2.sql`.
- Боевой `root`-пароль — в `configuration.php` на `.55`; в репо/чат не выносится.

## 6. Остаётся
- [ ] Передать дамп Biblio-команде по защищённому каналу (или introspect raw-копии).
- [ ] `SHOW CREATE TABLE` после загрузки — подтвердить charset на уровне колонок.
- [ ] `llm_router`-конфиг/секреты (где живут — БД vs файл).

## Связано
[`JIRBIS_MYSQL_ACCESS_REQUEST.md`](JIRBIS_MYSQL_ACCESS_REQUEST.md) · [`JIRBIS_CUTOVER_PLAN.md`](JIRBIS_CUTOVER_PLAN.md)
