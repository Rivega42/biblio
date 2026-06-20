# API-контракт `irbis-web` — шов между фронтом и бэкендом

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
