# SPEC · Консолидация API-контрактов новых движков/сервисов (A7)

> Сквозной пробел **A7** из [DESIGN_COVERAGE §A](../../DESIGN_COVERAGE.md) (эпик [#188](https://github.com/Rivega42/biblio/issues/188)). Закрывает дыру: «OpenAPI-контракты новых движков — формализма нет». Контракт-первый подход (I1 [#116](https://github.com/Rivega42/biblio/issues/116), [`openapi.yaml`](../../../build/openapi.yaml) — источник истины REST-шва). Это **сводная спека**: она консолидирует эндпоинты, введённые сёстринскими спеками движков, в один связный контракт, сверяет межмодульные интерфейсы и предлагает готовый OpenAPI-фрагмент к переносу в живой `openapi.yaml`.

**Грунтовка (читать вместе с этой спекой):**
[SPEC_engine_pft.md](SPEC_engine_pft.md) §4 (A1 PFT/печать) ·
[SPEC_engine_flk.md](SPEC_engine_flk.md) §5 (A2 ФЛК) ·
[SPEC_engine_gbl.md](SPEC_engine_gbl.md) §5 (A3 глоб.корректировка) ·
[SPEC_service_authority.md](SPEC_service_authority.md) §2–3 (A4 авторитеты) ·
[SPEC_seeding.md](SPEC_seeding.md) §5 (A5 сидинг/словари) ·
[SPEC_I1_foundation.md](../SPEC_I1_foundation.md) §#101 (Identity/Tenancy/Licensing), §#116 (contract-first), §#118 (CI/Pact) ·
[CONVENTIONS.md](../../CONVENTIONS.md) · [API_CONTRACT.md](../../build/API_CONTRACT.md) (человекочитаемый гид к `openapi.yaml`).

> **Уведомления (A6).** Спека движка уведомлений ([DESIGN_COVERAGE §A6](../../DESIGN_COVERAGE.md)) ещё не написана (это отдельная дыра ❌ → I3/I2). Эндпоинты `/api/notify*` и `/api/me/notification-prefs` здесь **проектируются проактивно** как часть консолидации (раздел 1.6), чтобы A6-спека наследовала готовый контракт, а не вводила его заново. Помечены `status: proposed (A6 pending)`.

> **Граница ответственности этой спеки.** Здесь — **только контракт** (методы, пути, схемы, auth, ошибки) и предложенный OpenAPI-фрагмент в fenced-блоке (раздел 4). Живой [`openapi.yaml`](../../../build/openapi.yaml) **не редактируется этой задачей** (его линтит CI — `npx --yes @redocly/cli@latest lint docs/build/openapi.yaml`, должно быть 0 ошибок; кривая правка ломает сборку). Перенос фрагмента в `openapi.yaml` — отдельный шаг оркестратора (раздел 3.6).

---

## 0. Принципы консолидации

- **Один контракт, один конверт.** Все новые эндпоинты живут в том же `openapi.yaml`, наследуют конверт `{ok,data}` / `{ok,error:{code,message}}` ([API_CONTRACT.md §Конверт](../../build/API_CONTRACT.md)), `bearerAuth`, модель ошибок и пагинацию существующего контракта. Никаких параллельных «контрактов на движок».
- **Тенант — из JWT, не из пути.** `tenant_id` берётся из claim JWT ([SPEC_I1 #101](../SPEC_I1_foundation.md): `sub, tenant_id, grants|roles, kind`), **не** из path/query. Путь `{db}` — это код базы внутри тенанта, не идентификатор арендатора. Изоляция — инвариант (RLS + `search_path` на `t_<slug>`), негатив-тест в CI обязателен.
- **Грант × энтайтлмент — двойной гейт.** Доступ = `(грант функция×база×уровень)` **И** `is_enabled(tenant, module)` ([SPEC_I1 #101](../SPEC_I1_foundation.md) AC2: выключенный модуль → 404/403 даже при наличии гранта). В контракте это два различимых отказа: нет гранта → `403 forbidden`; модуль не подключён → `404 not_found` (или `403 module_disabled` — см. открытый вопрос Q1).
- **Расширение, не слом.** Новые движки добавляются **новыми путями/тегами/схемами**; существующие 17 эндпоинтов и их схемы не меняются ([API_CONTRACT.md](../../build/API_CONTRACT.md): «расширения добавляются НОВЫМИ эндпоинтами»).
- **Идемпотентность записи.** Все мутирующие/пакетные операции принимают `Idempotency-Key` (header) и/или серверный `jobId`; повтор с тем же ключом не дублирует эффект (раздел 3.5).
- **Контракт-тест.** Каждый эндпоинт покрывается Pact/контракт-тестом ([SPEC_I1 #118](../SPEC_I1_foundation.md)); фрагмент раздела 4 должен пройти `redocly lint` без ошибок до переноса.

---

## 1. Консолидированная таблица эндпоинтов

> Сводка всех путей, введённых сёстринскими спеками A1–A5 (+ проактивный A6). Грант записан в нотации `функция:база:уровень` (как `Grant` в `openapi.yaml`). «Энт.» — требуемый энтайтлмент-модуль ([#101](../SPEC_I1_foundation.md)). Тело/ответ — краткая форма; полные схемы — раздел 2 и OpenAPI-фрагмент (раздел 4).

### 1.1 A1 — PFT / форматирование и печать (`tag: format`) — [SPEC_engine_pft.md §4](SPEC_engine_pft.md)

| Метод | Путь | Назначение | Запрос (тело/параметры) | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| POST | `/api/record/{db}/{mfn}/format` | Форматировать одну запись | `{pft?\|profile?, mode:html\|pdf\|rtf\|docx\|plain, params?}` | `text/html` \| `application/pdf` \| `application/rtf` (+ `X-Format-Render-Ms`) | `record.read:{db}:read` | `cataloging`/`opac` | 401, 403, 404, 422 (`format_error`), 400 |
| POST | `/api/format/preview` | Превью inline-PFT (редактор форматов, D1) | `{db, pft, record?\|mfn?, mode}` | `{rendered, errors[]}` (+ `*** Format error N`) | `format.edit:{db}:write` | `cataloging` | 401, 403, 422 |
| POST | `/api/print/cards` | Пакетная печать карточек | `{db, mfn_list?\|query?, card_set, mode:pdf}` | `application/pdf` (или `202 {jobId}` при больших объёмах) | `print:{db}:read` | `cataloging` | 401, 403, 400 |
| POST | `/api/print/table` | Табличная форма (`IC_print`) | `{db, table, head[≤3]?, mfn_list?\|query?, sort?, mode:pdf\|xlsx\|html}` | бинарь \| `202 {jobId}` | `print:{db}:read` | `cataloging` | 401, 403, 400 |
| POST | `/api/print/stat` | Статформа (`IC_stat`) | `{db, stat_form, params?, range?, mode:pdf\|xlsx}` | бинарь \| `202 {jobId}` | `print:{db}:read` | `cataloging` | 401, 403, 400 |
| POST | `/api/print/labels` | Наклейки/ШК/QR | `{db, mfn_list, barcode_field, layout, mode:pdf}` | `application/pdf` | `print:{db}:read` | `cataloging` | 401, 403, 400 |
| GET | `/api/formats` | Доступные форматы показа/печати тенанта | `?db&kind?&record_type_920?` | `{items: FormatMenuItem[]}` | `record.read:{db}:read` | — | 401, 403 |
| GET | `/api/print/forms` | Доступные таблич./печатные формы | `?db&kind?` | `{items: PrintFormItem[]}` | `print:{db}:read` | `cataloging` | 401, 403 |

> **Примечание по пути.** Спека A1 пишет `POST /api/record/{id}/format`; здесь нормализовано к `POST /api/record/{db}/{mfn}/format` — паритет существующему `/api/record/{db}/{mfn}` (path-параметры `db`+`mfn`), `{id}` без базы неоднозначен в мультибазовой модели. **Мисматч M1** (раздел 5).

### 1.2 A2 — ФЛК / валидация (`tag: validation`) — [SPEC_engine_flk.md §5](SPEC_engine_flk.md)

| Метод | Путь | Назначение | Запрос | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| POST | `/api/validate` | Валидация черновика (save/fieldExit/import/delete) | `ValidateRequest {db, phase, field?, record, currentMfn?, rulesetVersion?, acknowledgedWarnings?}` | `ValidateResult {overallSeverity, canSave, rulesetVersion, violations[]}` | `record.write:{db}:write` | `cataloging` | 401, 403, 422 |
| GET | `/api/flk/rules` | Действующий ruleset тенанта (редактор ws5) | `?db` | `{db, rulesetVersion, rules[]}` | `flk.config:{db}:read` | `cataloging` | 401, 403 |
| PUT | `/api/flk/rules` | Сохранить дельты тенанта (новая версия, аудит) | `{db, overrides[]}` (+ `Idempotency-Key`) | `{db, rulesetVersion}` | `flk.config:{db}:admin` | `cataloging` | 401, 403, 409 |
| POST | `/api/flk/preview` | Прогон правила/набора на тестовой записи | `{db, rule?\|ruleset?, record}` | `ValidateResult` | `flk.config:{db}:read` | `cataloging` | 401, 403, 422 |

> `/api/validate` при `phase=save` и `canSave==false` отдаёт `200 {canSave:false, violations}` (не HTTP-ошибку — это валидный бизнес-результат); вызывающий сервис сохранения трактует его как «отказ записи». Severity 2 без `acknowledgedWarnings` → тоже `canSave:false` с пометкой `overcomable:true` у нарушений (раздел 2.2). См. **мисматч M3**.

### 1.3 A3 — Глобальная корректировка `.gbl` (`tag: batch-correct`) — [SPEC_engine_gbl.md §5](SPEC_engine_gbl.md)

| Метод | Путь | Назначение | Запрос | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| POST | `/api/batch-correct` | Запуск задания (превью или применение) | `BatchCorrectRequest {db, gbl, selection, preview, flc}` (+ `Idempotency-Key`) | `200 DiffReport` (preview) \| `202 {jobId, status, totalsEstimate}` | `cat.gbl:{db}:admin` | `cataloging` | 401, 403, 400 (строка/арность) |
| POST | `/api/batch-correct/validate` | Компиляция задания без выборки | `{db, gbl}` | `{ast, errors[], warnings[]}` | `cat.gbl:{db}:admin` | `cataloging` | 401, 403, 400 |
| GET | `/api/batch-correct/jobs` | История заданий тенанта | `?db&actor&dateFrom&dateTo&page&pageSize` | `{items: JobSummary[], total, page, pageSize}` | `cat.gbl:{db}:admin` | `cataloging` | 401, 403 |
| GET | `/api/batch-correct/jobs/{jobId}` | Статус/прогресс задания | — | `JobStatus {status, totals, progress, startedAt, finishedAt, putlog[], error?}` | `cat.gbl:{db}:admin` | `cataloging` | 401, 403, 404 |
| GET | `/api/batch-correct/jobs/{jobId}/diff` | Diff завершённого превью/применения | — | `DiffReport` | `cat.gbl:{db}:admin` | `cataloging` | 401, 403, 404 |
| POST | `/api/batch-correct/jobs/{jobId}/rollback` | Откат задания | (+ `Idempotency-Key`) | `202 {rollbackJobId}` \| `409` (нечего/уже откачено) | `cat.gbl:{db}:admin` | `cataloging` | 401, 403, 404, 409 |

> Кросс-БД операторы (`NEWMFN→другая БД`, `&uf('D<db>…')`) проверяют грант к **целевой** базе того же тенанта ([SPEC_engine_gbl §5.4](SPEC_engine_gbl.md)); выход за тенант запрещён жёстко (тест изоляции). Флаг `GLOBTOTALMAIN` (правка по `query`/всему диапазону без отметки) — отдельный грант/настройка тенанта.

### 1.4 A4 — Сервис авторитетных файлов (`tag: authority`) — [SPEC_service_authority.md §2–3](SPEC_service_authority.md)

| Метод | Путь | Назначение | Запрос | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| GET | `/api/authority/{db}/search` | Поиск кандидатов (подстановка в РЛ) | `?q&prefix&mode=prefix\|keyword\|exact\|advanced&worklist?&limit&cursor` | `{items: AuthorityCandidate[], next_cursor?}` | `authority.read:{db}:read` | `cataloging` | 401, 403, 400 |
| GET | `/api/authority/{db}/{id}` | Полная авторитетная запись | — | `AuthorityRecord` (210/410/510/710/notes/classmarks/ext_ids) | `authority.read:{db}:read` | `cataloging` | 401, 403, 404 |
| GET | `/api/authority/{db}/{id}.jsonld` | JSON-LD (LOD) | — | `application/ld+json` | `authority.read:{db}:read` | `cataloging`/`opac` | 401, 403, 404 |
| GET | `/api/authority/{db}/{id}/related` | Граф «см.также»/параллельные | — | `{items: RelatedLink[]}` | `authority.read:{db}:read` | `cataloging`/`opac` | 401, 403, 404 |
| POST | `/api/authority/{db}/{id}/merge` | Слияние записей + перепривязка `^3` | `{target_id, keep:"target"\|"source", field_resolution}` (+ `Idempotency-Key`) | `202 {jobId}` (фоновая перепривязка через A3) | `authority.write:{db}:admin` | `cataloging` | 401, 403, 404, 409 |
| GET | `/api/classification/{scheme}/tree` | Ленивое раскрытие узла | `?node&depth` | `{nodes: ClassNode[]}` | `record.read:{db}:read` | — | 401, 403 |
| GET | `/api/classification/{scheme}/search` | Поиск рубрики по тексту/коду | `?q&limit&cursor` | `{items: ClassNode[], next_cursor?}` | `record.read:{db}:read` | — | 401, 403, 400 |
| GET | `/api/classification/{scheme}/{code}/path` | Путь от корня (хлебные крошки) | — | `{path: ClassNode[]}` | `record.read:{db}:read` | — | 401, 403, 404 |

> `{db}` ∈ `{athra, athrc, athrs, athrg, athru, athrb}`; `{scheme}` ∈ `{grnti, udc, bbk}`. Ответ `search` несёт готовый блок `fill` (карта «авторитет→подполя каталога») и `^3 = shifr_903` — клиент не реконструирует подполя ([SPEC_service_authority §2.4 AC-L4](SPEC_service_authority.md)). См. **раздел 2.4** (контракт `^3`).

### 1.5 A5 — Сидинг / словари / классификация (`tag: vocab`) — [SPEC_seeding.md §5](SPEC_seeding.md)

| Метод | Путь | Назначение | Запрос | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| GET | `/api/vocab` | Список справочников тенанта | — | `{items: VocabSummary[]}` (name/title/kind/seed_version/count) | `vocab.read:*:read` (любой staff) | — | 401, 403 |
| GET | `/api/vocab/{name}` | Значения словаря (выпадающие списки, ФЛК) | `?activeOnly` | `{name, values: VocabValue[]}` (code/label/sort/active) | `vocab.read:*:read` | — | 401, 403, 404 |
| PUT | `/api/vocab/{name}` | Заменить/обновить значения (CRUD) | `{values: VocabValue[]}` (+ `Idempotency-Key`) | `{name, count, seed_version}` | `vocab.config:*:admin` | — | 401, 403, 409 |
| POST | `/api/vocab/{name}/import` | Импорт `.mnu`/CSV/JSON | `multipart` или `{format, body}` | `{imported, skipped, report[]}` | `vocab.config:*:admin` | — | 401, 403, 400 |
| GET | `/api/vocab/{name}/export` | Экспорт | `?fmt=mnu\|csv\|json` | бинарь/текст | `vocab.read:*:read` | — | 401, 403 |
| GET | `/api/vocab/{name}/validate` | Проверка кода по словарю (мост A2) | `?code` | `{valid, label?}` | `vocab.read:*:read` | — | 401, 403, 404 |
| GET | `/api/classification/{tree}` | Дерево (lazy по `parent`/поддереву) | `?parent&depth` | `{nodes: ClassNode[]}` | `vocab.read:*:read` | — | 401, 403, 404 |
| PUT | `/api/classification/{tree}` | Правка узлов дерева | `{nodes: ClassNode[]}` (+ `Idempotency-Key`) | `{tree, count}` | `vocab.config:*:admin` | — | 401, 403, 409 |
| POST | `/api/onboarding/seed` | Bootstrap: посев сидов+деревьев (idempotent) | `{preset, reseed?}` (+ `Idempotency-Key`) | `{seeded, trees, conflicts[]}` | `tenant.admin:*:admin` | — | 401, 403, 409 |

> **Коллизия пути `/api/classification/*`.** A4 (авторитеты) использует `/api/classification/{scheme}/tree|search|{code}/path` для **навигации** (read-only, грнти/удк/ббк), A5 (сидинг) — `/api/classification/{tree}` (`GET`/`PUT`) для **редактирования** деревьев тенанта. Это разные операции на одном префиксе → **мисматч M2** (раздел 5): нужно развести (предложение — A5 редактор под `/api/vocab/classification/{tree}`, A4 навигация остаётся `/api/classification/{scheme}/…`).

### 1.6 A6 — Уведомления (`tag: notifications`) — **proposed (A6 pending)**, [DESIGN_COVERAGE §A6](../../DESIGN_COVERAGE.md)

| Метод | Путь | Назначение | Запрос | Ответ | Грант | Энт. | Ошибки |
|---|---|---|---|---|---|---|---|
| POST | `/api/notify` | Поставить уведомление в очередь (мультиканал) | `NotifyRequest {channel:[sms\|email\|push], to?\|readerMfn?, template, params, dedupKey?}` (+ `Idempotency-Key`) | `202 {notificationId, status:queued}` | `notify.send:*:write` (system/staff) | `notifications` | 401, 403, 400, 422 |
| GET | `/api/notify/{id}` | Статус доставки (ретраи/каналы) | — | `{id, status, attempts[], channelResults[]}` | `notify.send:*:read` | `notifications` | 401, 403, 404 |
| GET | `/api/me/notification-prefs` | Предпочтения текущего пользователя | — | `NotificationPrefs {channels, mutedTypes, quietHours?}` | `cabinet:*:read` (reader/staff) | `notifications` | 401, 403 |
| PUT | `/api/me/notification-prefs` | Сохранить предпочтения | `NotificationPrefs` (+ `Idempotency-Key`) | `NotificationPrefs` | `cabinet:*:write` | `notifications` | 401, 403, 400 |

> Эти 4 пути — **проект контракта**, чтобы будущая A6-спека наследовала форму, а не вводила её заново. Поведение (ретраи, дедуп, расписание тихих часов) определяет A6-спека; здесь фиксируется только REST-шов.

**Итого консолидировано: 33 эндпоинта** (A1: 8, A2: 4, A3: 6, A4: 8, A5: 9 — минус 2 пересекающихся с A4 по префиксу `classification`, разводятся в M2 → нетто 7 уникальных A5 + 2 спорных; A6 proposed: 4). Уникальных путей по методам — см. раздел 5 (точный счёт после разведения M2).

---

## 2. Схемы данных (новые `components/schemas`)

> Зеркалят формы из сёстринских спек; именование — PascalCase, как существующие схемы `openapi.yaml`. Все вложены в общий конверт `EnvelopeOk`/`EnvelopeError` (не дублируем `{ok,data}` в каждой схеме — он на уровне response).

### 2.1 A1 — форматирование/печать

```jsonc
FormatRequest {
  pft?: string,            // inline-PFT (XOR с profile)
  profile?: string,        // имя формата (напр. "Kn_H"); если нет ни pft, ни profile — авто по OPT (920)
  mode: "html"|"pdf"|"rtf"|"docx"|"plain",
  params?: object          // параметры формата (head-строки, реквизиты и т.п.)
}
FormatMenuItem  { name, title, kind, record_type_920?, modes: string[], description? }   // GET /api/formats
PrintFormItem   { name, title, kind: "tbg"|"tab"|"stat", modes: string[] }                // GET /api/print/forms
FormatError     { code: number, message: string, line?: number }                          // "*** Format error N"
```
Ответ `format`/`print*` — бинарный (`text/html`|`application/pdf`|`application/rtf`|`xlsx`) ИЛИ `202 {jobId}` (большие объёмы). Заголовок `X-Format-Render-Ms` — паритет `genpft64` (мс), на всех успешных рендерах.

### 2.2 A2 — валидация

```jsonc
ValidateRequest {
  db: string,
  phase: "save"|"fieldExit"|"import"|"delete",
  field?: string,                 // только phase=fieldExit
  record: object,                 // JSONB поля/подполя (модель записи I1)
  currentMfn?: number|null,       // исключить себя из дублет-проверок; null — новая запись
  rulesetVersion?: number|null,   // null = текущая версия тенанта
  acknowledgedWarnings?: string[] // ruleId преодолимых (severity 2), подтверждённых оператором
}
ValidateResult {
  overallSeverity: 0|1|2,
  canSave: boolean,               // false при overallSeverity==1 ИЛИ непогашенных severity 2
  rulesetVersion: number,         // воспроизводимость прогона
  violations: Violation[]
}
Violation {
  ruleId: string, severity: 0|1|2, message: string,
  path: string,                   // "010/a" — привязка к полю/подполю/инстансу
  field?: string, subfield?: string,
  overcomable?: boolean,          // true для severity 2 — UI предлагает acknowledge
  dupRef?: number                 // MFN конфликтной записи (дублет)
}
```

### 2.3 A3 — глобальная корректировка

```jsonc
BatchCorrectRequest {
  db: string,
  gbl: { source: "@<name>"|"inline", body?: string|string[], params?: object },
  selection: { query?: string, mfnRange?: {from,to}, mfnList?: number[], sequential?: boolean },
  preview: boolean,
  flc: "off"|"warn"|"block"       // прогон ФЛК (A2) при применении
}
DiffReport  { totals: {records,fieldsChanged}, items: RecordDiff[] }    // пополевой before→after
RecordDiff  { mfn: number, ops: {tag, occ, before?, after?}[] }
JobStatus   { status: "queued"|"running"|"done"|"failed"|"rolledback",
              totals: {processed,total,errors}, progress: number,
              startedAt, finishedAt?, putlog: string[], error?: ApiError }
JobSummary  { jobId, db, actor, startedAt, status, totals }
```

### 2.4 A4 — авторитеты + контракт `^3` (потребляют A2/A1)

```jsonc
AuthorityCandidate {
  id: string, uri: string, shifr_903: string,
  kind: "personal"|"corporate"|"subject"|"geographic"|...,
  worklist: string, is_variant: boolean,
  label: string,
  see_from?: string[],            // 410 формы, ведущие сюда
  fill: object                    // карта «авторитет→подполя каталога»: {"a":..,"b":..,"g":..,"f":..,"9":..}
}
AuthorityRecord { id, kind, shifr_903, heading_210, see_from_410[], see_also[], notes, classmarks, ext_ids, source }
RelatedLink     { kind: "510"|"710"|"parallel", target_id, label, shifr_3 }
ClassNode       { code, label, scheme, parent?, hasChildren: boolean, path?: string[] }
```
**Контракт `^3` (подстановка, потребитель A2/A1):** ответ `search` несёт `shifr_903` + `fill`; клиент пишет в каталог-поле подполя из `fill` и `^3 = shifr_903` ([SPEC_service_authority §3.1 шаг 5](SPEC_service_authority.md)). ФЛК-движок (A2) на сохранении валидирует **присутствие и резолвимость** `^3` (правила `!700`/`!964`), вызывая authority-сервис как источник истины связи — не дублирует её (раздел 3.2б).

### 2.5 A5 — словари/классификация

```jsonc
VocabSummary { name, title, kind, seed_version, count, origin: "system"|"custom" }
VocabValue   { code, label, sort?: number, active: boolean, origin?: "system"|"custom" }
VocabValidateResult { valid: boolean, label?: string }     // GET /api/vocab/{name}/validate?code=X
SeedResult   { seeded: number, trees: number, conflicts: {name, reason}[] }
```

### 2.6 A6 — уведомления (proposed)

```jsonc
NotifyRequest    { channel: ("sms"|"email"|"push")[], to?: string, readerMfn?: number,
                   template: string, params: object, dedupKey?: string }
NotifyStatus     { id, status: "queued"|"sent"|"failed"|"partial", attempts: object[], channelResults: object[] }
NotificationPrefs { channels: {sms,email,push: boolean}, mutedTypes: string[], quietHours?: {from,to,tz} }
```

---

## 3. Сверка межмодульных контрактов (раздел 2 ТЗ)

> Сёстринские агенты пометили три межмодульных интерфейса как требующие сверки. Ниже — формализация каждого + найденные мисматчи (сводка — раздел 5). **Важно:** интерфейсы A1↔A2↔A3 (2a, 2b) — **внутренние (in-process)**, а не REST: A2/A3 вызывают A1 как библиотеку в том же процессе/транзакции. REST-фрагменту они не нужны, но контракт обязателен (контракт-тест на уровне модулей, не Pact-HTTP).

### 3.1 (2a) A1 PFT `pft.eval(ctx)` — expression-core, потребляют A2 и A3

Спека A3 ([SPEC_engine_gbl §2](SPEC_engine_gbl.md)) **уже формализовала** интерфейс вызова A1 как расширение `evaluate(format, record, ctx)`:

```
pft.eval(pftRef, record, ctx) -> string            // одностр. результат
pft.evalLines(pftRef, record, ctx) -> string[]     // многостр. (групповой (...)/) — режим F, ADD по полю
```

**Форма инъекции `ctx`** (то, чего нет в обычном показе; сводим к канону для обоих потребителей):

| Поле `ctx` | Назначение | Источник recon | Кто пишет/читает |
|---|---|---|---|
| `ctx.vars` | переменные/регистры `&uf('+7…')` — строковые/числовые ячейки прогона (`+7W`/`+7R`/`+7U`/`+7S`) | `ExecVars` ([SPEC_engine_gbl §3.2](SPEC_engine_gbl.md)) | A3 пишет/читает; A2 — read-only (обычно не нужен) |
| `ctx.counters` | глобальные счётчики `&uf('++C<idx>#<val>')` (БД COUNT) — **персистентные, per-tenant** | ([SPEC_engine_gbl §3.3](SPEC_engine_gbl.md)) | A3 инкрементит (в превью — **не** инкрементит); A2 — нет |
| `ctx.history` | история копий записи (`&unifor('Z')` размножение, `&uf('4…')` пред.копия для `UNDOR`) | журнал ([SPEC_engine_gbl §4.5](SPEC_engine_gbl.md)) | A3 (откат/размножение); A2 — нет |
| `ctx.crossDb` | доступ к другим БД тенанта на лету (`&uf('J<db>…')`, `&uf('D<db>…')`, `&uf('7,?…?,fmt')`) — резолв по PostgreSQL-индексу | ([SPEC_engine_gbl §2,§6](SPEC_engine_gbl.md)) | A1 резолвит под тенантом; A2 использует для дублет-лукапа (`dupKey`) |
| `ctx.tenant` | `tenant_id` + `search_path` (инвариант изоляции) | [SPEC_I1 #100/#101](../SPEC_I1_foundation.md) | все |

**Мисматч M4 (сверка A1↔A3):** интерфейс `pft.eval(…ctx…)` и инъекция `ctx.vars/counters/history` **объявлены в спеке A3 как требование к A1** ([SPEC_engine_gbl §2](SPEC_engine_gbl.md): «Требование к A1… Если A1 этого не умеет — это блокер A3»), но **спека A1 не выставляет `eval(ctx)` как публичный контракт** — её §4 описывает только REST-эндпоинты, а интерпретатор — как внутренний «явный per-render контекст» ([SPEC_engine_pft §9, риск о побочных эффектах](SPEC_engine_pft.md)) без сигнатуры `ctx`. **Резолюция:** зафиксировать `pft.eval/evalLines(pftRef, record, ctx)` + поля `ctx` (таблица выше) как **внутренний модульный контракт A1** (добавить в A1 §4 ссылку на этот раздел); A2 потребляет подмножество (`ctx.crossDb`, `ctx.tenant`), A3 — полное. Контракт-тест: общий тест-вектор A1↔A2↔A3 на `ctx`.

### 3.2 (2b) A5 `validate(vocab, code) -> {valid,label}` — потребляет A2

Спека A5 ([SPEC_seeding §5](SPEC_seeding.md)) выставляет:
- REST: `GET /api/vocab/{name}/validate?code=X` → `{valid, label}`;
- мост (in-process): `validate(vocab=name, code=value) -> {valid, label}` («пустой/неактивный код → ошибка ФЛК по полю»).

Спека A2 ([SPEC_engine_flk §1.2](SPEC_engine_flk.md)) потребляет это **через DSL-функции A1**:
- `dictHas(file, key) -> bool`, `dictLookup(file, key) -> string` (через A1, [SPEC_engine_flk §1.2](SPEC_engine_flk.md)).

**Мисматч M5 (сверка A2↔A5, имена и ключ):**
1. **Имена не совпадают:** A5 предлагает `validate(vocab, code) -> {valid,label}`; A2 зовёт `dictHas/dictLookup(file, key)`. Это **два имени одной операции**.
2. **Ключ словаря разный:** A2 передаёт `file` как имя `.mnu`-файла (`'jz.mnu'`, `'920.mnu'` — [SPEC_engine_flk §1.3](SPEC_engine_flk.md)); A5 адресует словарь по `{name}` (вероятно `jz`, `920` — без `.mnu`). Нужна нормализация ключа.

**Резолюция:** A5 — владелец данных словарей; A1 `dictHas/dictLookup` реализуются как **тонкая обёртка над A5** `validate(name, code)`:
- `dictHas(file,key)` ≡ `A5.validate(normalize(file), key).valid`;
- `dictLookup(file,key)` ≡ `A5.validate(normalize(file), key).label` (пусто = нет в словаре);
- `normalize(file)` срезает суффикс `.mnu` и регистр → `{name}` A5.
Так A2 продолжает писать правила в терминах `.mnu` (паритет recon), а реальный лукап идёт в A5 (единый источник). Зафиксировать как мост A1↔A5 в A1 §UNIFOR (`&unifor('K<файл>.mnu|<знач>')` → A5). Контракт-тест: правило ФЛК `101 jz.mnu` бьёт по посеянному словарю тенанта.

### 3.2б (2c) Authority `^3` — потребляют A2 и A4-каталог

- **A4 поставляет**: `search` → `{shifr_903, fill, see_from, is_variant}`; pipeline подстановки пишет `^3 = shifr_903` + подполя из `fill` ([SPEC_service_authority §3.1–3.2](SPEC_service_authority.md)).
- **A2 потребляет**: правила `!700`/`!964` валидируют присутствие/резолвимость `^3` на сохранении ([SPEC_service_authority §1: «ФЛК-движок их вызывает; authority-сервис поставляет данные и валидирует связь `^3`»](SPEC_service_authority.md)).
- **A1 потребляет (показ)**: OPAC/карточка может резолвить актуальную форму по `^3` (опц., политика тенанта — [SPEC_service_authority §4.5](SPEC_service_authority.md)).

**Согласовано, без мисматча по форме**, но **открытый вопрос Q3** (из A4): показывать ли в OPAC всегда актуальную форму резолвом по `^3` на лету, или денормализованный кэш подполей с фоновой актуализацией по `W=`. Контракт `^3` стабилен (`^3 == authority.shifr_903`); расходится только **политика показа** — не ломает REST-контракт. Для контракта фиксируем: ответ `AuthorityRecord` несёт канон-форму, ответ `search` несёт `fill` (кэш-кандидат) — потребитель решает по политике.

---

## 4. Предложенный OpenAPI 3.1 фрагмент (к переносу в `openapi.yaml`)

> **Не редактирует живой файл.** Ниже — самодостаточный фрагмент: новые `tags`, `paths`, `components/schemas` для **4 представительных эндпоинтов** (по одному «характерному» на A2/A3/A4/A5 — валидация, запуск пакетной правки + статус job, поиск авторитета, словарь+мост ФЛК). Переиспользует существующие `EnvelopeOk`/`EnvelopeError`/`ApiError`/`Unauthorized`/`Forbidden`/`Db`/`Page`/`PageSize`. Должен пройти `redocly lint` после слияния. Перенос — раздел 3.6 ниже.

```yaml
# --- ДОБАВИТЬ в tags: ---
tags:
  - name: validation
    description: Формально-логический контроль записи (ФЛК, движок A2). Требует грантов.
  - name: batch-correct
    description: Глобальная корректировка .gbl (движок A3). Требует грант cat.gbl admin.
  - name: authority
    description: Авторитетные файлы — поиск, запись, подстановка ^3 (сервис A4).
  - name: vocab
    description: Справочники/классификаторы тенанта и сидинг (A5). Мост ФЛК.

# --- ДОБАВИТЬ в paths: ---
paths:
  /api/validate:
    post:
      tags: [validation]
      operationId: validateRecord
      summary: Валидация черновика записи (ФЛК).
      description: |
        Требует грант `record.write/<db>/write` и включённый модуль `cataloging`.
        Возвращает `200` даже при `canSave:false` — это валидный бизнес-результат,
        а не HTTP-ошибка. `severity 1` блокирует сохранение; `severity 2` — преодолимо
        через `acknowledgedWarnings`.
      parameters:
        - name: Idempotency-Key
          in: header
          required: false
          schema: { type: string }
          description: Ключ идемпотентности (повтор не дублирует аудит-эффект).
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/ValidateRequest" }
      responses:
        "200":
          description: Результат валидации (включая canSave:false).
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data: { $ref: "#/components/schemas/ValidateResult" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }
        "422":
          description: Запись непригодна к разбору (`unprocessable`).
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EnvelopeError" }

  /api/batch-correct:
    post:
      tags: [batch-correct]
      operationId: batchCorrect
      summary: Запуск глобальной корректировки (превью или применение).
      description: |
        Требует грант `cat.gbl/<db>/admin` и включённый модуль `cataloging`.
        `preview:true` → синхронный `DiffReport` (200, БД не меняется);
        `preview:false` → постановка job в очередь (202).
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema: { type: string }
          description: Обязателен для применения — защищает от двойного запуска.
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/BatchCorrectRequest" }
      responses:
        "200":
          description: Превью (пополевой diff, БД не изменена).
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data: { $ref: "#/components/schemas/DiffReport" }
        "202":
          description: Задание поставлено в очередь.
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data:
                        type: object
                        required: [jobId, status]
                        properties:
                          jobId: { type: string }
                          status: { type: string, enum: [queued, running] }
                          totalsEstimate: { type: integer }
        "400":
          description: Ошибка парсинга задания (`bad_request`, номер строки в message).
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EnvelopeError" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }

  /api/batch-correct/jobs/{jobId}:
    parameters:
      - name: jobId
        in: path
        required: true
        schema: { type: string }
        description: Идентификатор задания.
    get:
      tags: [batch-correct]
      operationId: getBatchJob
      summary: Статус и прогресс задания глобальной корректировки.
      description: Требует грант `cat.gbl/<db>/admin`. Прогресс `processed/total`.
      responses:
        "200":
          description: Статус задания.
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data: { $ref: "#/components/schemas/JobStatus" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }
        "404":
          description: Задание не найдено (`not_found`).
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EnvelopeError" }

  /api/authority/{db}/search:
    parameters:
      - name: db
        in: path
        required: true
        schema:
          type: string
          enum: [athra, athrc, athrs, athrg, athru, athrb]
        description: Код авторитетной БД (маппинг на kind).
    get:
      tags: [authority]
      operationId: authoritySearch
      summary: Поиск кандидатов в авторитетном файле (подстановка ^3).
      description: |
        Требует грант `authority.read/<db>/read`. Курсорная пагинация.
        Ответ несёт `fill` (подполя каталога) и `shifr_903` (→ `^3`) — клиент
        не реконструирует подполя.
      parameters:
        - name: q
          in: query
          required: true
          schema: { type: string }
          description: Поисковый термин.
        - name: prefix
          in: query
          required: false
          schema: { type: string }
          description: Словарный префикс (A/M/S/G/U); по умолчанию — главный для БД.
        - name: mode
          in: query
          required: false
          schema:
            type: string
            enum: [prefix, keyword, exact, advanced]
            default: prefix
        - name: worklist
          in: query
          required: false
          schema: { type: string }
        - name: limit
          in: query
          required: false
          schema: { type: integer, minimum: 1, maximum: 100, default: 20 }
        - name: cursor
          in: query
          required: false
          schema: { type: string }
          description: Курсор следующей страницы (из next_cursor).
      responses:
        "200":
          description: Отранжированные кандидаты + курсор.
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data:
                        type: object
                        required: [items]
                        properties:
                          items:
                            type: array
                            items: { $ref: "#/components/schemas/AuthorityCandidate" }
                          next_cursor: { type: string }
        "400":
          description: Пустой `q` (`bad_request`).
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EnvelopeError" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }

  /api/vocab/{name}/validate:
    parameters:
      - name: name
        in: path
        required: true
        schema: { type: string }
        description: Имя справочника тенанта (напр. jz, 920).
    get:
      tags: [vocab]
      operationId: vocabValidate
      summary: Проверка кода по словарю (мост для движка ФЛК A2).
      description: |
        Требует грант `vocab.read/*/read`. Используется движком ФЛК (A2) на
        сохранении: пустой/неактивный код → нарушение по полю. A1-функции
        `dictHas`/`dictLookup` — тонкая обёртка над этим эндпоинтом.
      parameters:
        - name: code
          in: query
          required: true
          schema: { type: string }
          description: Проверяемый код.
      responses:
        "200":
          description: Результат проверки кода.
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/EnvelopeOk"
                  - type: object
                    properties:
                      data: { $ref: "#/components/schemas/VocabValidateResult" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }
        "404":
          description: Справочник не найден (`not_found`).
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EnvelopeError" }

# --- ДОБАВИТЬ в components/schemas: ---
components:
  schemas:
    ValidateRequest:
      type: object
      required: [db, phase, record]
      properties:
        db: { type: string }
        phase: { type: string, enum: [save, fieldExit, import, delete] }
        field: { type: string, description: Только для phase=fieldExit. }
        record: { type: object, additionalProperties: true, description: JSONB поля/подполя (модель записи I1). }
        currentMfn:
          type: integer
          nullable: true
          description: Исключить себя из дублет-проверок; null — новая запись.
        rulesetVersion:
          type: integer
          nullable: true
          description: null = текущая версия тенанта.
        acknowledgedWarnings:
          type: array
          items: { type: string }
          description: ruleId преодолимых (severity 2), подтверждённых оператором.

    Violation:
      type: object
      required: [ruleId, severity, message, path]
      properties:
        ruleId: { type: string }
        severity: { type: integer, enum: [0, 1, 2] }
        message: { type: string }
        path: { type: string, description: "Привязка к полю/подполю, напр. 010/a." }
        field: { type: string }
        subfield: { type: string }
        overcomable: { type: boolean, description: true для severity 2 — UI предлагает acknowledge. }
        dupRef: { type: integer, description: MFN конфликтной записи (дублет). }

    ValidateResult:
      type: object
      required: [overallSeverity, canSave, rulesetVersion, violations]
      properties:
        overallSeverity: { type: integer, enum: [0, 1, 2] }
        canSave: { type: boolean }
        rulesetVersion: { type: integer }
        violations:
          type: array
          items: { $ref: "#/components/schemas/Violation" }

    BatchCorrectRequest:
      type: object
      required: [db, gbl, selection, preview]
      properties:
        db: { type: string }
        gbl:
          type: object
          required: [source]
          properties:
            source: { type: string, description: "@<имя> (задание тенанта) или inline." }
            body:
              oneOf:
                - { type: string }
                - { type: array, items: { type: string } }
            params: { type: object, additionalProperties: true }
        selection:
          type: object
          properties:
            query: { type: string }
            mfnRange:
              type: object
              properties:
                from: { type: integer }
                to: { type: integer }
            mfnList:
              type: array
              items: { type: integer }
            sequential: { type: boolean }
        preview: { type: boolean }
        flc:
          type: string
          enum: [off, warn, block]
          default: warn

    RecordDiff:
      type: object
      required: [mfn, ops]
      properties:
        mfn: { type: integer }
        ops:
          type: array
          items:
            type: object
            properties:
              tag: { type: string }
              occ: { type: integer }
              before: { type: string }
              after: { type: string }

    DiffReport:
      type: object
      required: [totals, items]
      properties:
        totals:
          type: object
          properties:
            records: { type: integer }
            fieldsChanged: { type: integer }
        items:
          type: array
          items: { $ref: "#/components/schemas/RecordDiff" }

    JobStatus:
      type: object
      required: [status, totals, progress]
      properties:
        status: { type: string, enum: [queued, running, done, failed, rolledback] }
        totals:
          type: object
          properties:
            processed: { type: integer }
            total: { type: integer }
            errors: { type: integer }
        progress: { type: number, description: "0..1." }
        startedAt: { type: string, format: date-time }
        finishedAt: { type: string, format: date-time }
        putlog:
          type: array
          items: { type: string }
        error: { $ref: "#/components/schemas/ApiError" }

    AuthorityCandidate:
      type: object
      required: [id, shifr_903, kind, is_variant, label, fill]
      properties:
        id: { type: string }
        uri: { type: string }
        shifr_903: { type: string, description: "Номер авторитетной записи → каталог-поле ^3." }
        kind: { type: string, enum: [personal, corporate, subject, geographic, uniform, title] }
        worklist: { type: string }
        is_variant: { type: boolean, description: "true = найдено по 410; подставлять принятую форму." }
        label: { type: string }
        see_from:
          type: array
          items: { type: string }
          description: 410-формы, ведущие сюда.
        fill:
          type: object
          additionalProperties: { type: string }
          description: "Карта авторитет→подполя каталога ({a,b,g,f,9,...})."

    VocabValidateResult:
      type: object
      required: [valid]
      properties:
        valid: { type: boolean }
        label: { type: string, description: "Расшифровка кода; пусто = нет в словаре." }
```

---

## 5. Сводка мисматчей (к разрешению оркестратором/в спеках)

| # | Между | Суть | Предложенная резолюция |
|---|---|---|---|
| **M1** | A1 ↔ контракт | A1 пишет `POST /api/record/{id}/format` без базы; контракт мультибазовый (`{db}/{mfn}`) | Нормализовать к `/api/record/{db}/{mfn}/format` (паритет существующему record-эндпоинту). Применено в разделе 1.1. |
| **M2** | A4 ↔ A5 | Коллизия префикса `/api/classification/*`: A4 — навигация по схемам (grnti/udc/bbk, read-only), A5 — редактирование деревьев тенанта (GET/PUT) | Развести: A5-редактор → `/api/vocab/classification/{tree}`; A4-навигация остаётся `/api/classification/{scheme}/…`. |
| **M3** | A2 ↔ сервис сохранения | `/api/validate` при `canSave:false` — это `200` (бизнес-результат) или HTTP-4xx? A2 §5 говорит «409-подобный отказ» | Контракт: `/api/validate` всегда `200` с `canSave`; **сервис сохранения записи** (`POST /api/record`) возвращает `409` при `canSave:false`. Разделить ответственность. |
| **M4** | A1 ↔ A3 (и A2) | A3 объявил `pft.eval(…, ctx)` с `ctx.vars/counters/history` как требование к A1; A1 §4 не выставляет `eval(ctx)` как контракт | Зафиксировать `pft.eval/evalLines(pftRef, record, ctx)` + поля `ctx` (раздел 3.1) как внутренний модульный контракт A1; общий тест-вектор A1↔A2↔A3. **Блокер A3, если не закрыт.** |
| **M5** | A2 ↔ A5 | Имена (`dictHas/dictLookup` vs `validate`) и ключ словаря (`'jz.mnu'` vs `{name}=jz`) расходятся | A1 `dictHas/dictLookup` — тонкая обёртка над A5 `validate(name,code)`; `normalize(file)` срезает `.mnu`/регистр. A5 — владелец данных. |

---

## 6. Версионирование, конвенции, сворачивание в `openapi.yaml`

### 6.1 Как это складывается в существующий контракт
- **Конверт/ошибки** — без изменений: новые эндпоинты наследуют `EnvelopeOk`/`EnvelopeError`/`ApiError`; коды ошибок из существующего перечня (`unauthorized, forbidden, bad_request, not_found, irbis, internal`) + новые `unprocessable` (422, ФЛК-разбор), `format_error` (422, PFT), `module_disabled` (если выбран вариант 403 для энтайтлмента — Q1).
- **Теги** — 5 новых (`format`, `validation`, `batch-correct`, `authority`, `vocab`) + `notifications` (proposed). Существующие (`auth/catalog/reader/cataloging/system`) не трогаем.
- **Переиспользование схем** — `Grant`, `Db`, `Page`, `PageSize`, `PathDb`, `PathMfn`, `Unauthorized`, `Forbidden`, `ApiErrorResponse` переиспользуются как есть; новые схемы — раздел 2/4.
- **Пагинация — два стиля.** Существующие списки — offset (`page`/`pageSize`); A4-поиск/A3-история, где набор большой/изменчивый — **курсорная** (`limit`/`cursor`, `next_cursor`). Зафиксировать в API_CONTRACT.md как «курсор для поисковых/потоковых, offset для конечных списков».

### 6.2 Тенант-скоупинг (JWT)
- `tenant_id` — claim JWT ([#101](../SPEC_I1_foundation.md)), извлекается middleware, **не** параметр пути/тела. `{db}` в пути — база внутри тенанта. Все запросы выполняются под `search_path=t_<slug>` (RLS-инвариант); cross-tenant — негатив-тест в CI (DoD-гейт).
- Двойной гейт `грант × энтайтлмент`: `403 forbidden` (нет гранта) vs `404 not_found`/`403 module_disabled` (модуль не подключён) — **Q1**.

### 6.3 Идемпотентность
- Заголовок `Idempotency-Key` (UUID клиента) на всех `POST`/`PUT`, меняющих состояние (`/api/validate` — опц., аудит; `/api/batch-correct` — **обязателен** при `preview:false`; `merge`, `rollback`, `seed`, `vocab PUT`, `notify`). Сервер хранит ключ→результат (TTL), повтор возвращает исходный ответ без повторного эффекта.
- Долгие операции — `jobId`-семантика (A3, merge, seed больших деревьев): `202 {jobId}` + поллинг `GET …/{jobId}`. Откат — отдельный `rollbackJobId`.

### 6.4 Перенос фрагмента в `openapi.yaml` (шаг оркестратора)
1. Слить блоки `tags`/`paths`/`components.schemas` из раздела 4 в [`openapi.yaml`](../../../build/openapi.yaml) (аккуратно, в соответствующие секции — не дублировать существующие `tags`/схемы).
2. Прогнать `npx --yes @redocly/cli@latest lint docs/build/openapi.yaml` → 0 ошибок (CI-гейт).
3. Обновить [API_CONTRACT.md](../../build/API_CONTRACT.md) (человекочитаемая таблица) — добавить строки новых эндпоинтов.
4. Завести Pact/контракт-тесты ([#118](../SPEC_I1_foundation.md)) на новые операции.

---

## 7. Критерии приёмки (AC)

- **AC1 (lint).** OpenAPI-фрагмент раздела 4, слитый в `openapi.yaml`, проходит `redocly lint` с 0 ошибок (CI-гейт #118).
- **AC2 (конверт).** Каждый новый эндпоинт оборачивает ответ в `EnvelopeOk`/`EnvelopeError`; ни один не вводит параллельный формат.
- **AC3 (двойной гейт).** Контракт-тест: при наличии гранта, но выключенном модуле — `404`/`403` (а не `200`); без гранта — `403`; без сессии — `401` ([#101 AC2](../SPEC_I1_foundation.md)).
- **AC4 (тенант-изоляция).** Негатив-тест: запрос тенанта A к данным/job/словарю/авторитету тенанта B — `404`/`403`, утечки нет (RLS), на всех новых путях.
- **AC5 (Pact/контракт-тест, #118).** Каждая операция таблицы раздела 1 покрыта контракт-тестом (потребитель↔провайдер); схемы request/response совпадают с разделом 2/4.
- **AC6 (идемпотентность).** Повтор `POST /api/batch-correct` (применение) / `rollback` / `seed` / `vocab PUT` с тем же `Idempotency-Key` не дублирует эффект; возвращает исходный результат.
- **AC7 (мост A2↔A5, M5).** Контракт-тест: правило ФЛК со словарным лукапом (`101 jz.mnu`) бьёт по посеянному словарю тенанта через `GET /api/vocab/{name}/validate`; имена/ключ нормализованы.
- **AC8 (контракт `ctx`, M4).** Модульный тест-вектор: `pft.eval(pftRef, record, ctx)` с инъекцией `ctx.vars/counters/history/crossDb` даёт идентичный результат при вызове из A2 и A3 (детерминизм, превью не инкрементит `counters`).
- **AC9 (контракт `^3`).** `search` отдаёт `shifr_903`+`fill`; запись каталог-поля содержит `^3==shifr_903`; правило ФЛК `!700`/`!964` валидирует резолвимость `^3` (раздел 3.2б).
- **AC10 (`validate` — бизнес-результат).** `/api/validate` при `canSave:false` отвечает `200` (не 4xx); `409` возникает только из сервиса сохранения записи (M3).

---

## 8. Открытые вопросы

- **Q1 (энтайтлмент-отказ).** Выключенный модуль при наличии гранта — какой HTTP-код: `404 not_found` (маскируем существование, как в [#101 AC2](../SPEC_I1_foundation.md)) или явный `403 module_disabled` (понятнее клиенту, но раскрывает наличие)? Влияет на все теги. **Рекомендация:** `404` для read-путей (маскировка), `403 module_disabled` для write — но требуется решение по безопасности (I6).
- **Q2 (бинарь vs job для печати).** A1 `print/*` при больших объёмах — порог перехода с синхронного бинаря на `202 {jobId}` конфигурируем per-tenant? И где скачивается готовый PDF job — отдельный `GET /api/print/jobs/{jobId}/result`? Не введён в сёстринской A1; нужно дозафиксировать (влияет на UX печати комплектов карточек/КСУ).
- **Q3 (показ `^3`: связь vs кэш).** OPAC всегда резолвит актуальную форму по `^3` на лету или доверяет денормализованному `fill`-кэшу с фоновой актуализацией по `W=`-метке ([SPEC_service_authority §4.5, Q3](SPEC_service_authority.md))? Контракт `^3` стабилен, но политика показа влияет на стоимость рендера и на форму ответа `AuthorityRecord` (нужно ли поле `resolvedForm`).

---

## Сводка

**Консолидировано 33 эндпоинта** в один контракт под 5 новыми тегами (A1 форматирование/печать — 8, A2 ФЛК — 4, A3 глоб.корректировка — 6, A4 авторитеты — 8, A5 сидинг/словари — 7 после разведения коллизии) + **4 проактивных** под `notifications` (A6 — спека ещё не написана, форма заложена заранее). Все наследуют конверт `{ok,data}`/`{ok,error}`, `bearerAuth`, модель ошибок и двойной гейт `грант × энтайтлмент` ([#101](../SPEC_I1_foundation.md)); тенант — из JWT-claim, не из пути; запись/пакет — `Idempotency-Key`.

**Сверены три межмодульных контракта** (раздел 3): **(2a)** A1 `pft.eval/evalLines(pftRef, record, ctx)` с инъекцией `ctx.vars/counters/history/crossDb/tenant` — формализован из A3-спеки (потребляют A2/A3); **(2b)** мост `validate(vocab,code)→{valid,label}` A5, обёрнутый в A1-функции `dictHas/dictLookup` (потребляет A2); **(2c)** контракт `^3 == authority.shifr_903` + `fill` (поставляет A4, валидирует A2, резолвит A1 на показе) — согласован.

**Пять мисматчей к разрешению:** **M1** путь `format` без базы → `{db}/{mfn}`; **M2** коллизия `/api/classification/*` A4↔A5 → развести редактор под `/api/vocab/classification/`; **M3** `/api/validate` `canSave:false` — это `200` (бизнес), `409` отдаёт сервис сохранения; **M4** A1 не выставил `eval(ctx)` как контракт (блокер A3); **M5** имена/ключ словаря A2↔A5.

**Файл:** `C:\IRBIS64\_recon\docs\design\specs\engines\SPEC_api_contracts.md`

**Топ-3 открытых вопроса:** **Q1** — HTTP-код отказа по энтайтлменту (`404` маскировка vs `403 module_disabled`); **Q2** — порог «бинарь→job» и эндпоинт скачивания результата печати A1; **Q3** — показ `^3` в OPAC: резолв актуальной формы на лету vs денормализованный кэш с фоновой актуализацией по `W=`.
