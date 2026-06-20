# Интеграция: проектный комплект ↔ глубокий ресерч (Проход А завершён)

> Связывает присланный комплект `irbis-web` (design/build/recon/reference) с глубокой картографией в [`deep/`](deep/). Главный вывод: **глубокий ресерч закрывает ключевой пробел комплекта** — отсутствовавшую папку `DATAI` (конфиги баз), которую `RECON_FINDINGS_02 §6` и `PROJECT_INDEX §4` помечали как «нужно с сервера» (Проход А). Дата интеграции: 2026-06-20.

## 1. Откуда взялись два исследования
- **Комплект (`docs/{design,build,recon,reference}`)** собран ранее по архиву `IRBIS64_COPY` (программная папка **без `DATAI`**). Сильная сторона — протокол (официальная дока), модель доступа, инженерные ТЗ, экраны. Самооценка полноты: «PFT/WSS/CHM сэмплированы, не до каждого поля» (`CLAUDECODE_PROJECT_BRIEF §4`).
- **Глубокий ресерч (`docs/recon/deep`)** выполнен на **живой инсталляции `C:\IRBIS64` с реальной `DATAI`** (49 папок БД + конфиги). Это и есть **Проход А** + глубже: каждая строка FST, словарь полей/подполей, язык PFT, рабочие листы, INI всех АРМов, модель книговыдачи из конфигов.

## 2. Что комплект добавляет к глубокому ресерчу (закрытые/уточнённые вопросы)
| Было в `deep/OPEN_QUESTIONS` | Уточнение из комплекта | Источник |
|---|---|---|
| `#R02/#0301` — проводной TCP-протокол не задокументирован | **Эталонный клиент `BookCabinet`** (рабочая реализация) + **живой сервер `localhost:6666`** доступен для Прохода Б | `CLAUDECODE_PROJECT_BRIEF §3,§7` |
| `#0302` — числовые коды ошибок неизвестны | **`-3338` = `CLIENT_NOT_ALLOWED`** (гейт по типу АРМа) — числовое значение | `FUNCTION_PROTOCOL_MAP §8`, `ACCESS_MODEL §2` |
| привязка возможностей к протоколу не сведена | **`FUNCTION_PROTOCOL_MAP.md`** — функция → команды `IC_*` + требуемый АРМ-контекст | `docs/design/` |
| модель прав/ролей не формализована | **`ACCESS_MODEL_web-irbis.md`** — (функция × база × уровень), гранты вместо «АРМов» | `docs/design/` |
| — | Контекст пилота: **СПб ГТБ**, целевая архитектура (React+aiohttp+PG), фазы P0–P4 | `CLAUDECODE_PROJECT_BRIEF`, `P0_BUILDKIT` |

## 3. Что глубокий ресерч добавляет к комплекту (закрывает его открытые задачи)
| Открытая задача комплекта | Чем закрыто в `deep/` |
|---|---|
| `PROJECT_INDEX §4.1` / `RECON_FINDINGS_02 §6.7` — **Проход А: конфиги баз `DATAI` (форматы/префиксы/формы)** | **выполнено целиком**: [reference/databases/](deep/reference/databases/) — каждая из 49 БД (PAR, **вся FST**, словарь полей/подполей, PFT-каталог, связи) |
| «PFT/WSS сэмплированы» | [PFT_LANGUAGE.md](deep/reference/format/PFT_LANGUAGE.md) (44 конструкции + 41 UNIFOR-код), [FIELD_DICTIONARY.md](deep/reference/format/FIELD_DICTIONARY.md) (115 полей с подполями), `.wss` в DB_IBIS/DB_ACQUISITION |
| `BRIEF §6.3` — точные правила полей / виды поиска по базам | [ARM_*.md](deep/reference/arms/) — посекционный INI всех 6 АРМов (виды поиска `[SEARCH]`/`[SEARCHKO]`/`[SEARCHCMP]`, ФЛК, права полей) |
| модель книговыдачи (в доке отсутствовала) | [DB_CIRCULATION.md](deep/reference/databases/DB_CIRCULATION.md) — заказ→выдача(`RQSTRDR.PFT`)→возврат→архив, статусы `ste.mnu`/`reservstatus.mnu`, восстановлено из конфигов |
| GUAR Фонд↔Опись (поле 488) — подтверждено комплектом | расширено в [DB_SPECIAL.md](deep/reference/databases/DB_SPECIAL.md): **5-уровневая** иерархия FOND/OPIS/DELO/GUAR/LIST, связь вверх `488^T`=903 родителя, вниз поле 330 |
| полный реестр/профиль баз | [DOCUMENT_REGISTER.md](deep/DOCUMENT_REGISTER.md) (14 270 файлов, todo=0) + [CAPABILITY_MAP.md](deep/CAPABILITY_MAP.md) §8 (профиль 49 БД) |

## 4. Соответствие RECON_FINDINGS (комплект) ↔ deep (этот ресерч)
| Комплект | Глубокий эквивалент (deeper) |
|---|---|
| `RECON_FINDINGS_01` (сервер/реестр баз) | `deep/FINDINGS_04_server_admin` + `deep/FINDINGS_02 §8` (49 БД) |
| `RECON_FINDINGS_02` (каталог протокола) | `deep/FINDINGS_03_protocol` (80 функций с параметрами/кодами) |
| `RECON_FINDINGS_03` (GUAR, веб-модель, клиенты) | `deep/FINDINGS_09_web_reader` + `DB_SPECIAL` (GUAR) + `FINDINGS_05` (Каталогизатор) |
| `RECON_FINDINGS_04` (конфиги: префиксы/FST/PAR) | `deep/FINDINGS_02` + **все** `deep/reference/databases/*` |
| `RECON_FINDINGS_05` (PFT/v920/WSS) | `deep/reference/format/PFT_LANGUAGE` + `FIELD_DICTIONARY` + `DB_IBIS §3,§5` |
| `RECON_FINDINGS_06` (Комплектатор/КО/Админ) | `deep/FINDINGS_06/07` + `DB_ACQUISITION/DB_VUZ` + `ARM_*` |
| `RECON_FINDINGS_07` (релиз-ноуты) | `deep/FINDINGS_11_release_capabilities` |

## 5. Приоритет источников (правило `FILES_MANIFEST §4`)
`reference` (протокол/мануал) > `recon` (доказательная база, **включая `deep/`**) > `design` > `build`. При расхождении факта — фиксировать `TODO(...)`, не догадываться. Глубокий ресерч имеет ту же доказательную силу, что `RECON_FINDINGS`, и приоритетнее `design/build` по фактам о механике баз.

## 6. Что осталось (требует живого сервера / боевых баз СПб ГТБ)
- **Проход Б** на `localhost:6666`: точные форматы пакетов и числовые коды `IC_*` (символьные — есть в `deep/FINDINGS_03`; числовые — снять с сервера/`BookCabinet`).
- **Боевые базы СПб ГТБ** (PLAY/TUAR/EK/ESKIZ/HPO): их `[SEARCH]`/PFT/WSS — механика та же (см. `deep/`), значения — с сервера библиотеки.
- Полный перечень — в [deep/OPEN_QUESTIONS.md](deep/OPEN_QUESTIONS.md) и `TODO(irbis-web #N)`/`TODO(Проход Б)`.
