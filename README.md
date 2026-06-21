# irbis-web — веб-версия САБ ИРБИС64+ (проект и доказательная база)

[![CI](https://github.com/Rivega42/biblio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Rivega42/biblio/actions/workflows/ci.yml)

Репозиторий проекта **веб-замены ИРБИС64+** (пилот — каталог СПб театральной библиотеки) и **полной картографии** продукта, на которую он опирается. Разработчика/исходников сервера нет → демо-поставка ИРБИС64+ = действующая спецификация, восстановленная из файлов.

## С чего начать
1. [docs/CLAUDECODE_PROJECT_BRIEF.md](docs/CLAUDECODE_PROJECT_BRIEF.md) — главный бриф (зачем/что/как). **Читать первым.**
2. [docs/PROJECT_INDEX.md](docs/PROJECT_INDEX.md) — порядок чтения комплекта.
3. [docs/FILES_MANIFEST.md](docs/FILES_MANIFEST.md) — раскладка и статусы файлов.

## Структура `docs/`
| Папка | Что | Статус |
|---|---|---|
| [`docs/design/`](docs/design/) | **Что строим**: [мастер-карта возможностей](docs/design/IRBIS_CAPABILITY_MAP_v2.md), [модель доступа](docs/design/ACCESS_MODEL_web-irbis.md) (функция×база×уровень), [функция→протокол](docs/design/FUNCTION_PROTOCOL_MAP.md), экраны [читателя](docs/design/SCREENMAP_web-reader.md)/[сотрудника](docs/design/SCREENMAP_web-staff.md) | И/П |
| [`docs/build/`](docs/build/) | **Как строим**: [инженерное ТЗ](docs/build/TZ_CLAUDE_CODE_irbis-web.md) + [аддендум доступа](docs/build/TZ_CLAUDE_CODE_ADDENDUM_access-suite.md) + [контракты P0](docs/build/P0_BUILDKIT_web-irbis.md) | И |
| [`docs/recon/`](docs/recon/) | **Откуда выводы**: находки [01](docs/recon/RECON_FINDINGS_01.md)–[07](docs/recon/RECON_FINDINGS_07.md), [методика](docs/recon/TZ_IRBIS_RECON.md), [промт-перепроверка](docs/recon/PROMPT_CLAUDECODE_RECON.md) | Д/М |
| [`docs/recon/deep/`](docs/recon/deep/) | **Глубокая картография** (этот ресерч): [CAPABILITY_MAP](docs/recon/deep/CAPABILITY_MAP.md), 14 FINDINGS, [reference/](docs/recon/deep/reference/) (per-DB FST/поля/PFT, INI всех АРМов), [реестр файлов](docs/recon/deep/DOCUMENT_REGISTER.md), [открытые вопросы](docs/recon/deep/OPEN_QUESTIONS.md) | Д |
| [`docs/reference/`](docs/reference/) | **Первоисточники** (только чтение): [API протокола](docs/reference/irbis64_client_dll_TEXT.txt), [мануал J-ИРБИС](docs/reference/ReadMe_jirbis2_text.txt) | С |

Интеграция двух исследований (комплект ↔ глубокий ресерч): [docs/recon/INTEGRATION_deep-recon.md](docs/recon/INTEGRATION_deep-recon.md).
Журнал: [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Принципы
- **Организация по учёткам/грантам**, не по «АРМам» (АРМ — только контекст протокола; гейт `-3338`).
- **Отображение — серверным PFT** (не переписываем язык форматирования в коде).
- **Безопасность некомпромиссна**: секреты только в env ([`.env.example`](.env.example)), бинарь/данные/`*.ini` с кредами — не в репозиторий, секрет-сканер в CI. Незакрытое — `TODO(...)`, факты — с источником.

## Код (предстоит, фаза P0)
`backend/` (Python/aiohttp: irbis/access/api) · `frontend/` (React-TS) · `infra/` — по [P0_BUILDKIT](docs/build/P0_BUILDKIT_web-irbis.md). Сейчас репозиторий — документация и доказательная база; сборка каркаса P0 — следующий этап.
