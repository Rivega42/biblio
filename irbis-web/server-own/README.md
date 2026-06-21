# server-own — собственный каталог-сервер (PoC)

Реализует **тот же [API-контракт](../../docs/build/API_CONTRACT.md)**, что и `backend/` (адаптер к ИРБИС), но отдаёт данные из **своего** хранилища (sqlite + FTS5), наполняемого миграцией из ИРБИС. **Тот же веб-клиент (`frontend/dist`) работает без изменений** — это и есть объединение «демо как J-ИРБИС» и «свой сервер». Архитектура и план — [OWN_SERVER_ARCHITECTURE.md](../../docs/design/OWN_SERVER_ARCHITECTURE.md).

## Запуск
```
# 1) наполнить наш стор записями из живого ИРБИС (через адаптер Прохода Б)
py irbis-web/server-own/migrate.py --host 127.0.0.1 --user MASTER --password 1 --db IBIS
# 2) собрать фронт (если ещё не собран) и поднять наш сервер
npm --prefix irbis-web/frontend run build
py irbis-web/server-own/app.py            # http://127.0.0.1:8081  — тот же клиент на НАШИХ данных
```
Демо «два сервера, один клиент»: `backend/` (:8080, поверх ИРБИС) и `server-own/` (:8081, наш) отдают один и тот же фронт.

## PostgreSQL (прод-стор) — переключение переменной окружения
Тот же сервер на PostgreSQL вместо sqlite (`store.py`→`pgstore.py`), без изменения API и фронта:
```
# 1) поднять Postgres
docker compose -f irbis-web/server-own/docker-compose.pg.yml up -d
py -3.12 -m pip install "psycopg[binary]"
# 2) миграция в PG (env выбирает бэкенд)
$env:OWN_STORE_BACKEND='pg'; $env:OWN_PG_DSN='postgresql://postgres:pg@127.0.0.1:5433/irbisweb'
py -3.12 irbis-web/server-own/migrate.py --db IBIS
# 3) запуск own-server на PG
$env:OWN_PORT='8082'; py -3.12 irbis-web/server-own/app.py     # http://127.0.0.1:8082
```
Модель PG: записи **JSONB** + `search_vector` (**tsvector**, поиск `to_tsquery` префиксом), обложки **bytea**, экземпляры/ячейки в `holding`. **Проверено:** 390 записей IBIS → PG; `K=Android`=7, расширенный=2, карточка 59 полей, 390 ячеек — тот же фронт на PG.

## Файлы
| Файл | Роль |
|---|---|
| `store.py` | sqlite + FTS5 (dev): модель записи, поиск, чтение, обложки, экземпляры/ячейки |
| `pgstore.py` | **PostgreSQL** (прод): тот же интерфейс (JSONB + tsvector + bytea); `make_store()` выбирает бэкенд по env |
| `migrate.py` | ИРБИС → стор через адаптер (`../backend/irbis`): поля/подполя→наша модель, обложки из 953, ячейки |
| `app.py` | stdlib HTTP: контракт (`auth/health/databases/search/terms/record/cover/cells` + запись) + отдаёт `frontend/dist` |

## Статус / дальше
PoC: чтение (поиск/карточка/обложка) одной базы из мигрированных данных. **Проверено:** 390 записей IBIS → `K=Android`=7, расширенный (Колисниченко∧Android)=2, тот же UI на `own-0.1`.
Prod-вектор: **PostgreSQL** (JSONB + tsvector + pg_trgm) вместо sqlite; нормализованные экземпляры с **ячейками** (#39); запись/каталогизация; инкрементальная синхронизация и сверка; cutover база-за-базой (strangler).
