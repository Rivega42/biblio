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

# живой каталог (дизайн-система на реальных данных IBIS):
#   http://127.0.0.1:8080/app    (или /ui/app/)

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
| `GET /api/worklist/{db}` | рабочий лист (профиль полей для DynamicField) | сессия |
| `POST /api/record/{db}/{mfn}` | сохранить запись (mfn=0 — создать) | `record.write` |

## Фронтенд (дизайн-система + живой каталог)
`frontend/` — дизайн-система **ИРБИС-Веб** (Claude Design): токены, темы (Рабочая/Театр/a11y),
React-компоненты (`SearchBar`, `ResultCard`, `StatusBadge`, `PftBlock`, `Pagination`, `DynamicField`…),
кликабельный прототип на моках (`ui_kits/`). Подробности — `frontend/readme.md`.

`frontend/app/` — **живой каталог**: те же дизайн-компоненты, но на **реальных данных IBIS** через наш API.
- **Читатель:** гостевой вход → поиск (автодополнение из словаря) → результаты (карточки + статусы) →
  читательская карточка записи (обложка из 953, поля с подписями, рубрики-чипы, экземпляры) → вход → заказ.
- **Сотрудник** (переключатель в шапке): вход (`admin/admin`, `librarian/librarian`) → **рабочий стол по грантам**
  (показаны только разрешённые домены, не «по АРМам») → **Каталогизация**: рабочий лист на компоненте `DynamicField`
  (тип поля → контрол, подполя, ФЛК), загрузка записи из IBIS, **сохранение в живой сервер** (песочница `WORK`,
  чтобы не трогать каталог) с записью в аудит.

Точки подключения из прототипа (`runQuery/recordFor/login/confirmOrder`) реализованы в `app/api.js`.
Открыть: `http://127.0.0.1:8080/app`. Проверено headless-браузером: поиск/карточка/обложка читателя;
вход сотрудника, грант-фильтр рабочего стола, создание записи в WORK (MFN присвоен, read-back совпал).

> Нюанс: `<img>` не шлёт заголовок `Authorization`, поэтому обложка берётся как `/api/cover/...?t=<token>`.
> В dev React/Babel грузятся с CDN — в боевом контуре заменяются на self-hosted (разд. 11 ТЗ).

## Структура
```
irbis-web/
├─ .env.example
├─ backend/
│  ├─ core.py            # ⭐ framework-agnostic API: authn→authz→IRBIS→audit
│  ├─ server.py          # транспорт stdlib + демо-страница (/) + статика /ui/
│  ├─ app_aiohttp.py     # транспорт aiohttp (то же ядро, через executor)
│  ├─ static_files.py    # отдача frontend/ под /ui/
│  ├─ reader_page.py     # простая демо-страница читателя
│  ├─ config.py          # .env (секреты не в коде)
│  ├─ irbis/             # слой протокола (Проход Б): client/parser/session
│  ├─ access/            # гранты/роли/аудит: store(sqlite)+schema_postgres+authz+seed
│  └─ tests/             # test_access (unit), e2e (HTTP)
└─ frontend/             # дизайн-система ИРБИС-Веб (Claude Design) + живой каталог
   ├─ tokens/ components/ ui_kits/ guidelines/   # токены, React-компоненты, прототип
   ├─ _ds_bundle.js styles.css                   # сборка компонентов + корневой CSS
   └─ app/               # ⭐ ЖИВОЙ каталог: index.html + api.js + live.jsx
                         #    дизайн-компоненты на реальных данных IBIS (через /api)
```

## Развёртывание (Docker)
Производственный запуск поверх существующего ИРБИС64 — одним образом (сборка фронта + рантайм бэкенда):
```
cp irbis-web/.env.example irbis-web/.env      # вписать IRBIS_HOST/USER/PASS, APP_SECRET
cd irbis-web
docker compose up -d --build                  # → http://<host>:8080
```
- Фронт собирается внутри образа (Vite, self-hosted — без CDN), бэкенд (aiohttp) отдаёт его и проксирует к ИРБИС.
- `IRBIS_HOST` — адрес боевого сервера (`host.docker.internal` если на том же хосте; иначе IP/DNS сервера ИРБИС).
- Учётки/гранты/аудит (sqlite) — в томе `irbis-web-data` (переживают перезапуск). Postgres — когда переедет Access.
- Конфиг полностью из env; список баз тянется с сервера (`IRBIS_DB_MENU`). Секретов в образе нет.

Без Docker (dev): `py irbis-web/backend/app_aiohttp.py` (или `server.py`) + отдельно `npm --prefix irbis-web/frontend run dev` (Vite-прокси на :8080), либо `npm run build` и бэкенд отдаёт `dist`.

## Безопасность
- Секреты только в `backend/.env` (**gitignored**); dev-БД доступа `access.db` — **gitignored**.
- Ошибки без внутренних деталей; денай прав и `-3338` → `403`; аудит write/admin.
- Запись (`record.write`/`order`) — только под соответствующим грантом.

## Дальше (issues #33/#34)
- asyncpg-реализация `AccessStore` + Postgres (prod), миграции.
- Боевой `order` → запись RQST + резерв экземпляра/ячейки; файлы/полный текст PDF через прокси.
- Frontend React+TS+Tailwind по [`TZ_ClaudeDesign_UI.md`](../docs/design/TZ_ClaudeDesign_UI.md) поверх этого API.
