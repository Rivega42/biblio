# P0 Build Kit — веб-ИРБИС (ядро + Access + Читатель)

> Превращает модель доступа и инженерное ТЗ в **реализуемые контракты** для фазы P0. Не зависит от
> живого сервера: протокол спрятан за интерфейсом `IrbisClient` (на время разработки — мок; в бою —
> адаптер на клиенте BookCabinet). Опирается на `ACCESS_MODEL`, `FUNCTION_PROTOCOL_MAP`,
> `TZ_CLAUDE_CODE` + аддендум. Версия 1.0, 20.06.2026.

---

## 1. Структура репозитория

```
irbis-web/
├─ README.md
├─ .gitignore                # секреты, данные, бинарь, .env, *.ini с кредами
├─ .env.example              # схема конфигурации (без значений)
├─ backend/                  # Python aiohttp
│  ├─ app.py                 # точка входа, маршруты
│  ├─ config.py              # чтение env (никаких секретов в коде)
│  ├─ irbis/
│  │  ├─ client.py           # интерфейс IrbisClient (абстрактный)
│  │  ├─ bookcabinet.py      # адаптер на клиенте BookCabinet (боевой)  TODO(intg)
│  │  ├─ mock.py             # мок для разработки/тестов
│  │  └─ session_pool.py     # пул сессий по типам АРМ
│  ├─ access/
│  │  ├─ models.py           # учётки, гранты, роли, аудит (ORM)
│  │  ├─ resolver.py         # функция→АРМ-контекст + команды
│  │  ├─ authz.py            # проверка гранта (функция×база×уровень)
│  │  └─ audit.py            # журналирование write/admin
│  ├─ api/
│  │  ├─ auth.py             # вход читателя(билет)/сотрудника(логин)
│  │  ├─ search.py           # поиск, словарь/автодополнение
│  │  ├─ record.py           # чтение/формат записи, файлы
│  │  └─ order.py            # заказ, корзина, ЛК
│  └─ tests/
├─ frontend/                 # React/TS/Tailwind
│  ├─ src/{api,components,screens,state}/
│  └─ ...
└─ infra/                    # docker-compose (PostgreSQL), миграции
```

## 2. Конфигурация (`.env.example` — схема, без значений)

```
# IRBIS сервер
IRBIS_HOST=                  # напр. 192.168.8.19
IRBIS_PORT=6666
# Служебные АРМ-креды (по типам АРМ) — ТОЛЬКО env, не в репо
IRBIS_READER_USER=
IRBIS_READER_PASS=
IRBIS_CATALOG_USER=
IRBIS_CATALOG_PASS=
IRBIS_BOOKLAND_USER=
IRBIS_BOOKLAND_PASS=
# ... аналогично COMPLECT/BOOKPROVD/ADMINISTRATOR по мере включения модулей
# Базы
IRBIS_DB_DEFAULT=IBIS
# PostgreSQL
PG_DSN=postgresql://user:pass@host:5432/irbisweb
# Приложение
APP_SECRET=                  # ключ подписи сессий
APP_ENV=dev                  # dev|prod
```

## 3. Схема PostgreSQL (учётки сотрудников, гранты, аудит)

> Читатели НЕ дублируются в PG — они в `RDR` (вход по билету). В PG — только сотрудники и их гранты,
> сессии, аудит.

```sql
-- сотрудники
CREATE TABLE staff_account (
  id BIGSERIAL PRIMARY KEY,
  login TEXT UNIQUE NOT NULL,
  pass_hash TEXT NOT NULL,
  full_name TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- грант = функция × база × уровень
-- function: 'search'|'record.read'|'record.write'|'record.delete'|'order'|'circ.issue'|
--           'circ.return'|'cat.gbl'|'acq.receipt'|'kо.vuz'|'admin.db'|'admin.users'|...
-- db: имя БД или '*' (все) | группа
-- level: 'read'|'write'|'admin'
CREATE TABLE grant_entry (
  id BIGSERIAL PRIMARY KEY,
  account_id BIGINT NOT NULL REFERENCES staff_account(id) ON DELETE CASCADE,
  function TEXT NOT NULL,
  db TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('read','write','admin')),
  UNIQUE(account_id, function, db)
);

-- роль = именованный пресет грантов (опционально)
CREATE TABLE role (id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE role_grant (
  role_id BIGINT REFERENCES role(id) ON DELETE CASCADE,
  function TEXT NOT NULL, db TEXT NOT NULL, level TEXT NOT NULL
);
CREATE TABLE account_role (
  account_id BIGINT REFERENCES staff_account(id) ON DELETE CASCADE,
  role_id BIGINT REFERENCES role(id) ON DELETE CASCADE,
  PRIMARY KEY(account_id, role_id)
);

-- аудит write/admin
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor TEXT NOT NULL,            -- логин/билет
  function TEXT NOT NULL, db TEXT, mfn INTEGER,
  result TEXT NOT NULL,           -- ok|denied|error
  detail JSONB
);
```

Итоговые права учётки = объединение `grant_entry` + грантов всех её ролей.

## 4. Алгоритм проверки доступа (`authz.py`, псевдокод)

```
def authorize(account, function, db, level_needed):
    grants = union(account.grant_entries, account.roles.grants)   # эффективные гранты
    match = best_grant(grants, function, db)                       # точная база приоритетнее '*'
    if not match: return DENY
    if level_rank(match.level) < level_rank(level_needed): return DENY
    return ALLOW

# поток запроса
authn → authorize → resolver.context(function) → pool.session(arm_type)
       → check db visibility (dbnam) → IC_* call → normalize → audit(if write/admin)
```
`-3338` от сервера → трактуем как 403 (грант/контекст не совпал), детали — в лог, не клиенту.

## 5. Граница протокола: интерфейс `IrbisClient`

Методы, которые вызывает Access (а реализуют мок и адаптер BookCabinet). Привязка к `IC_*` —
по `FUNCTION_PROTOCOL_MAP.md`.

```python
class IrbisClient(Protocol):
    async def connect(self, arm_type: str) -> Session: ...        # IC_reg
    async def search(self, db, expr, fmt, first, count): ...      # IC_search
    async def read_record(self, db, mfn, lock=False): ...         # IC_read
    async def format_record(self, db, mfn, pft): ...              # IC_readformat/IC_sformat
    async def read_terms(self, db, term, count, reverse=False):...# IC_nexttrm/prevtrm
    async def posting(self, db, term): ...                        # IC_posting
    async def get_file(self, db, path, binary=True): ...          # IC_getbinaryresourse/getresourse
    async def update_record(self, db, record, lock, actualize):...# IC_update
    async def global_correction(self, db, gbl, expr): ...         # IC_gbl
    async def print_form(self, db, table, expr): ...              # IC_print
    async def stat(self, db, spec, expr): ...                     # IC_stat
    # admin: newdb/dbempty/dbdelete/reorg/getclientlist/...       # IC_adm_*
```
- `mock.py` — отдаёт фикстуры (для разработки UI и тестов Access без сервера).
- `bookcabinet.py` — `TODO(intg): подключить клиент BookCabinet; сверить форматы пакетов/коды на живом :6666 (Проход Б).`

## 6. Пул сессий (`session_pool.py`)
- На каждый АРМ-тип — пул служебных сессий (креды из env). Переиспользование; keepalive
  `IC_nooperation`; переоткрытие при разрыве; учёт лимита клиентов сервера (демо = 3 → в P0 беречь).

## 7. Контракт REST API (P0)

| Метод/путь | Назначение | Доступ |
| --- | --- | --- |
| `POST /api/auth/reader` | вход читателя (фамилия+билет) → сессия | публично |
| `POST /api/auth/staff` | вход сотрудника (логин+пароль) → сессия | публично |
| `POST /api/auth/guest` | гостевой вход (GUEST) | публично |
| `GET /api/search?db&prefix&q&page&logic` | поиск; ответ: total + краткие описания (серверный PFT) | search:db:read |
| `GET /api/terms?db&prefix&from` | словарь/автодополнение | search:db:read |
| `GET /api/record/{db}/{mfn}?fmt` | запись (формат через серверный PFT) | record.read:db:read |
| `GET /api/file/{db}?path` | файл/полный текст (с проверкой RIGHT) | record.read:db:read |
| `POST /api/order` | оформить заказ (RQST) | order:db:write |
| `GET /api/me/cabinet` | формуляр/история/корзина | (своя запись RDR) |

Конверт ответа: `{ ok, data | error: {code, message} }`. Никаких внутренних деталей в `error`.

## 8. Критерии готовности P0
- Вход читателя по билету и сотрудника по логину; гость.
- Поиск по префиксам видимой базы, автодополнение по словарю, постраничный вывод.
- Просмотр записи серверным PFT (краткое/полное), просмотр файла с учётом прав.
- Оформление заказа; ЛК/формуляр.
- Access: гранты функция×база×уровень работают; аудит write; `-3338`→403.
- Секреты только в env; gitleaks/trufflehog в pre-commit и CI; INI с кредами не в репо.

## 9. Требует живого сервера (TODO до боевого запуска)
- `TODO(Проход Б):` сверить форматы пакетов/коды результата `IC_*`, поведение поиска/словаря, права `RIGHT`, протокол очереди заказов.
- `TODO(СПб ГТБ):` префиксы `[SEARCH]`, форматы PFT и рабочие листы боевых баз (PLAY/TUAR/EK/ESKIZ/HPO).
- `TODO(BookCabinet):` интеграция боевого клиента протокола вместо мока.
- `TODO(штатка):` финальные уровни/пресеты-роли.
