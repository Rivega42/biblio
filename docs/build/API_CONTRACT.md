# API-контракт `irbis-web` — шов между фронтом и бэкендом

> **Источник истины — [`openapi.yaml`](openapi.yaml)** (OpenAPI 3.1, issue #116). Машиночитаемый контракт `openapi.yaml` **авторитетен** для путей, параметров, форм запросов/ответов и схем данных. Этот файл — **человекочитаемый гид**: при расхождении выигрывает `openapi.yaml`. Линт: `npx --yes @redocly/cli@latest lint docs/build/openapi.yaml` (должно быть 0 ошибок). Схемы зеркалят TS-интерфейсы в `frontend/src/api.ts`.
>
> **Расхождения «код против прозы» (зафиксировано при сверке с `backend/core.py` `Api.route()`):**
> - `GET /api/storage?db` — есть в типизированном клиенте (`api.ts`) и в `server-own/app.py`, но **НЕ** реализован в `core.py` (адаптер ИРБИС вернёт `404 not_found`). В `openapi.yaml` задокументирован как часть контракта с пометкой.
> - `GET /api/render/{db}/{mfn}?fmt` и `GET /api/resource/{db}/{file}` существуют в `core.py`, но отсутствуют в `api.ts` и в `openapi.yaml` (не часть публичного контракта фронта). `render` упомянут в таблице ниже для полноты.
> - `RecordData.holdings[]` / тип `Holding` — в контракте (`api.ts`), но `core.py` `record()` их не заполняет (отдаёт только `fields`); их отдаёт `server-own`. В схеме поле опционально.
> - `GET /api/terms` — клиент шлёт только `start`/`count`; `db` берётся из дефолта сервера (в таблице ниже значится `db&start&count`).

> **Это точка соединения двух задач.** Фронтенд (Vite/React/TS) общается с бэкендом ТОЛЬКО через этот REST-контракт. За контрактом может стоять **любой** бэкенд:
> - **`backend/`** — адаптер к существующему ИРБИС64 (Проход Б). Демо «как J-ИРБИС» — уже работает.
> - **`server-own/`** — **наш собственный сервер** (PostgreSQL/наша модель). Реализует тот же контракт → фронт работает без изменений.
>
> Так мы переходим на свой сервер по частям (strangler): эндпоинт за эндпоинтом, база за базой, с возможностью dual-run и сверки. См. [OWN_SERVER_ARCHITECTURE.md](../design/OWN_SERVER_ARCHITECTURE.md).

## Конверт
Успех: `{ "ok": true, "data": <...> }` · Ошибка: `{ "ok": false, "error": { "code", "message" } }` (без внутренних деталей). Бинарные ответы (обложка/файл) — сырые байты с `Content-Type`. Аутентификация: `Authorization: Bearer <token>`; `<img>`/ссылки — `?t=<token>`.

## Эндпоинты (P0)
| Метод / путь | Назначение | Грант |
|---|---|---|
| `POST /api/auth/guest` | гостевая сессия → `{token, kind}` | публично |
| `POST /api/auth/reader` `{ticket}` | вход читателя → `{token, kind, name, mfn}` | публично |
| `POST /api/auth/staff` `{login,password}` | вход сотрудника → `{token, login, name, grants[]}` | публично |
| `GET /api/health` | `{server, version, db, maxmfn}` | — |
| `GET /api/databases` | `{items: DbItem[], default}` | сессия |
| `GET /api/search?db&prefix&q&page&pageSize` (или `&expr=`) | `SearchResult` | `search` |
| `GET /api/terms?db&start&count` | `{terms: Term[]}` | `terms` |
| `GET /api/record/{db}/{mfn}` | `RecordData` | `record.read` |
| `GET /api/render/{db}/{mfn}?fmt` | `{rendered}` | `record.read` |
| `GET /api/cover/{db}/{mfn}` | байты изображения | `record.read` |
| `POST /api/order` `{db,mfn}` | заказ | `order` |
| `GET /api/me/cabinet` | `CabinetData` (формуляр) | `cabinet` |
| `GET /api/worklist/{db}` | профиль РЛ (DynamicField) | сессия |
| `POST /api/record/{db}/{mfn}` `{fields}` | сохранить запись (mfn=0 — создать) | `record.write` |

## Формы данных (TS)
```ts
DbItem      = { code, name, public }
ResultItem  = { mfn, title, author?, year?, docType?, availability?: 'available'|'issued'|'unknown', hasCover? }
SearchResult= { db, expr, total, page, pageSize, items: ResultItem[] }
Term        = { count, term }
FieldVal    = { tag, value, text?, subfields: Record<string,string> }   // подполя по '^'
RecordData  = { db, mfn, version?, brief?, hasCover?, fields: FieldVal[] }
CabinetData = { mfn, name, loans: {value, subfields}[], loanCount }
Grant       = { function, db, level }
```
> Контракт **стабилен** — обе реализации обязаны его соблюдать. Расширения своего сервера (ячеистое хранение, версии, аналитика) добавляются НОВЫМИ эндпоинтами, не ломая существующие.

## Маршрутизация при переходе (strangler)
Перед фронтом — обратный прокси/шлюз; per-endpoint (или per-db) маршрут на `backend/` (ИРБИС) или `server-own/`. Пока база не мигрирована — её обслуживает адаптер; после миграции и сверки — наш сервер. Источник истины контракта — этот файл.
