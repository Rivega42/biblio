# irbis-web — P0 (ядро + доступ + читательский поиск)

Боевой каркас веб-замены ИРБИС. **Backend читает/пишет реальные данные живого сервера ИРБИС64** через адаптер, снятый в Проходе Б ([`WIRE_PROTOCOL.md`](../docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md)). Контракты — [`P0_BUILDKIT`](../docs/build/P0_BUILDKIT_web-irbis.md); хранилище доступа — [`ADR-004`](../docs/build/ADR-004_access-store-sqlite-postgres.md).

## Статус (проверено на живом `:6666`, БД IBIS)
- ✅ Протокол: соединение/сессия, поиск, чтение полей+подполей (`^`), рендер серверным PFT, словарь (автодополнение), ресурсы, встроенные обложки.
- ✅ **Access-набор:** гранты `функция×база×уровень` + роли + аудит; `authz` (точная база > `*`); вход guest/staff/reader; `-3338`/денай → `403`.
- ✅ Два транспорта на **общем ядре** `core.py`: stdlib (`server.py`) и **aiohttp** (`app_aiohttp.py`) — одинаковый e2e.
- ✅ Демо-страница читателя (`/`): поиск → автодополнение → карточка → обложка.

## Запуск
```
cp irbis-web/.env.example irbis-web/backend/.env     # вписать IRBIS_USER/PASS

# вариант A — stdlib, без установки (любой Python 3)
py  irbis-web/backend/server.py                       # http://127.0.0.1:8080

# вариант B — aiohttp (Python 3.12)
py -3.12 -m pip install aiohttp asyncpg
py -3.12 irbis-web/backend/app_aiohttp.py

# тесты
py irbis-web/backend/tests/test_access.py             # authz/audit (unit)
py irbis-web/backend/smoke.py                          # слой IRBIS на живом сервере
py irbis-web/backend/tests/e2e.py                      # HTTP e2e (сервер должен быть запущен)
```
Демо-аккаунты (dev-сид): `admin/admin` (все права), `librarian/librarian` (читательские + каталогизация).

## API (конверт `{ok, data}` | `{ok:false, error:{code,message}}`; токен — `Authorization: Bearer`)
| Метод/путь | Назначение | Грант |
|---|---|---|
| `GET /api/health` | сервер/версия/maxmfn | — |
| `POST /api/auth/guest` | гостевая сессия | публично |
| `POST /api/auth/staff` | вход сотрудника (login+pass) | публично |
| `POST /api/auth/reader` | вход читателя (билет, через RDR) | публично |
| `GET /api/search?db&prefix&q&page` (или `&expr=`) | поиск: total + краткие БО | `search` |
| `GET /api/terms?db&start&count` | словарь/автодополнение (`count#term`) | `terms` |
| `GET /api/record/{db}/{mfn}` | запись: поля/подполя + `brief` | `record.read` |
| `GET /api/render/{db}/{mfn}?fmt` | серверный рендер PFT | `record.read` |
| `GET /api/cover/{db}/{mfn}` | встроенная обложка (поле 953^B) | `record.read` |
| `GET /api/resource/{db}/{file}` | меню/словарь БД (FILE `L`) | `file` |
| `POST /api/order` | заказ (guard+audit; RQST — TODO) | `order` |
| `GET /api/me/cabinet` | формуляр читателя (RDR, поле 40) | `cabinet` |

## Структура
```
irbis-web/
├─ .env.example
└─ backend/
   ├─ core.py            # ⭐ framework-agnostic API: authn→authz→IRBIS→audit
   ├─ server.py          # транспорт stdlib + демо-страница (/)
   ├─ app_aiohttp.py     # транспорт aiohttp (то же ядро, через executor)
   ├─ reader_page.py     # демо-страница читателя
   ├─ config.py          # .env (секреты не в коде)
   ├─ irbis/             # слой протокола (Проход Б): client/parser/session
   ├─ access/            # гранты/роли/аудит: store(sqlite)+schema_postgres+authz+seed
   └─ tests/             # test_access (unit), e2e (HTTP)
```

## Безопасность
- Секреты только в `backend/.env` (**gitignored**); dev-БД доступа `access.db` — **gitignored**.
- Ошибки без внутренних деталей; денай прав и `-3338` → `403`; аудит write/admin.
- Запись (`record.write`/`order`) — только под соответствующим грантом.

## Дальше (issues #33/#34)
- asyncpg-реализация `AccessStore` + Postgres (prod), миграции.
- Боевой `order` → запись RQST + резерв экземпляра/ячейки; файлы/полный текст PDF через прокси.
- Frontend React+TS+Tailwind по [`TZ_ClaudeDesign_UI.md`](../docs/design/TZ_ClaudeDesign_UI.md) поверх этого API.
