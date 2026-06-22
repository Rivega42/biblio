# Biblio — контейнерное развёртывание (MVP, Фаза 2)

Развёртывание веб-стека Biblio одной командой: TLS reverse-proxy, Python-бэкенд
(API + собранный SPA) и PostgreSQL. Закрывает #207 (эпик #223).

> Соответствует форме промышленной упаковки из
> [`SPEC_iac_fleet.md` §1.2 / §6.3](../docs/design/specs/platform/SPEC_iac_fleet.md)
> (одноузловой Docker-стек: приложение + PostgreSQL за внутренним reverse-proxy /
> терминацией TLS, секреты только в env, секретов в образах нет). Этот `deploy/` —
> одноузловой compose-набор; полная IaC/флот-топология из той спеки — более поздняя
> фаза.

## Топология

```
                         ┌──────────────────────────────────────────────┐
   https://localhost ──▶ │ proxy (nginx)  — терминация TLS (443→…)       │
                         └───────────────┬──────────────────────────────┘
                                         │ http (compose-сеть)
                         ┌───────────────▼──────────────────────────────┐
                         │ backend (Python · server.py)                 │
                         │   • отдаёт JSON API (/api/*)                  │
                         │   • отдаёт собранный SPA (frontend/dist)     │
                         └───────────────┬──────────────────────────────┘
                                         │ postgresql://db:5432
                         ┌───────────────▼──────────────────────────────┐
                         │ db (postgres:16) — Access-стор + мультиаренда │
                         └──────────────────────────────────────────────┘
```

- **Как отдаётся SPA (`dist/`) — backend-serves-dist.** `Dockerfile.backend`
  многостадийный: стадия `node` запускает `vite build`, и собранный `dist/`
  копируется в рантайм-образ в `frontend/dist`. Бэкенд (`static_files.py`)
  обнаруживает его (`has_dist()`), и один Python-процесс отдаёт и API, и SPA.
  Один контейнер — один источник истины по маршрутизации. (`Dockerfile.frontend`
  существует для *альтернативной* топологии «proxy отдаёт статику dist» и **не**
  входит в дефолтный `up` — см. комментарии в нём.)
- **TLS.** `proxy` (nginx) терминирует TLS на **:443** и reverse-проксирует всё на
  бэкенд. В dev используется **самоподписанный** сертификат (браузеры предупреждают
  — это ожидаемо). HTTP **:80** редиректит на HTTPS.
- **Access-стор на PostgreSQL.** Бэкенд работает с `ACCESS_BACKEND=postgres` против
  сервиса `db` (ADR-004). Движки (notify/catalog/circ/acq/bp) на sqlite пишут в
  персистентный именованный том.

## Подъём одной командой

```sh
cd deploy
cp .env.example .env          # 1. заполнить секреты (см. метки CHANGE IN PROD)
sh proxy/gen-cert.sh          # 2. сгенерировать dev самоподписанный TLS-сертификат
docker compose up --build     # 3. поднять db + backend + proxy
```

Затем открыть **https://localhost** (в dev принять предупреждение о самоподписанном сертификате).

Остановка / сброс:

```sh
docker compose down           # остановить, тома сохранить (данные остаются)
docker compose down -v        # остановить + удалить тома (стереть данные PG + sqlite)
```

## Окружение

Вся конфигурация через env; ничего чувствительного не зашито в образ.
Скопировать `.env.example` → `.env` (в gitignore) и задать как минимум:

| Переменная | Назначение | Dev-дефолт | Прод |
|---|---|---|---|
| `POSTGRES_PASSWORD` | пароль суперпользователя PostgreSQL | `devpassword` | **СМЕНИТЬ** — длинный случайный |
| `APP_SECRET` | подпись сессий/JWT | `dev-insecure-…` | **СМЕНИТЬ** — `openssl rand -hex 32` |
| `POSTGRES_USER` / `POSTGRES_DB` | роль / база PG | `postgres` / `irbis_access` | по необходимости |
| `HTTP_PORT` / `HTTPS_PORT` | порты хоста для proxy | `80` / `443` | по необходимости |
| `IRBIS_HOST` / `IRBIS_PORT` | живой TCP-сервер ИРБИС64 (опц.) | `host.docker.internal:6666` | ваш сервер |
| `IRBIS_USER` / `IRBIS_PASS` | сервис-аккаунт ИРБИС | `MASTER` / *(пусто)* | **СМЕНИТЬ** |
| `IRBIS_DB_DEFAULT` / `IRBIS_PUBLIC_DBS` | дефолтная + видимые читателю БД | `IBIS` / `IBIS` | по необходимости |

> Полную модель env, которую понимает бэкенд, см. в `irbis-web/backend/config.py`
> и `access/pgstore.py` (`ACCESS_BACKEND`, `ACCESS_PG_DSN`, sqlite-пути `*_DB`).
> Compose-файл прокидывает их за вас.

## Провижининг первого арендатора

Access-стор мультиарендный (control-схема + схема-на-арендатора `t_<slug>`).
После подъёма стека — провижининг через CLI:

```sh
# внутри запущенного backend-контейнера:
docker compose exec backend python -m access.provision <slug> \
  --name "Имя библиотеки" --admin admin --password '<надёжный-пароль>' --plan standard
```

> CLI `python -m access.provision <slug>` выполняет `ensure_control_schema()` +
> схему/миграции/сидинг арендатора против `ACCESS_PG_DSN`. Инфраструктура к этому
> готова — бэкенд уже указывает на PostgreSQL.

## Заметки по TLS

- **Dev:** `sh proxy/gen-cert.sh` пишет `proxy/certs/{server.crt,server.key}`
  (в gitignore). Самоподписанный → предупреждение браузера ожидаемо.
  Сгенерировать с другим именем: `CERT_CN=biblio.local sh proxy/gen-cert.sh`.
- **Прод:** заменить эти два файла сертификатом от вашего CA (внутренний CA /
  certbot / Let's Encrypt — HTTP-сервер nginx уже отдаёт ACME `http-01` webroot).
  Затем включить HSTS (раскомментировать заголовок `Strict-Transport-Security`
  в `proxy/nginx.conf`).

## Бэкапы и восстановление

Бэкап/restore сервиса `db` на базе `pg_dump`, с записью в именованный том `backups`
(переживает пересоздание контейнера, не попадает в git/на хост):

```sh
sh deploy/backup/pg_backup.sh                 # один дамп с таймстампом → том backups
KEEP=14 sh deploy/backup/pg_backup.sh         # + оставить только 14 новейших
sh deploy/backup/pg_restore.sh                # список доступных дампов
sh deploy/backup/pg_restore.sh <файл-дампа>   # восстановить (с подтверждением; FORCE=1 пропустить)
```

Проверить restore без касания живых данных (репетиция в throwaway-БД):

```sh
FORCE=1 RESTORE_DB=irbis_restore_test sh deploy/backup/pg_restore.sh <файл-дампа>
docker compose exec db psql -U postgres -d irbis_restore_test -c "\dn"   # проверка
docker compose exec db dropdb -U postgres irbis_restore_test             # убрать
```

Планирование (cron / Task Scheduler), 3-2-1 копии вне хоста и ежемесячная
периодичность restore-теста описаны в `pg_backup.sh` и в
[`docs/design/PILOT_READINESS.md`](../docs/design/PILOT_READINESS.md) → «Бэкапы».
> Одноузловой пилот = ночной логический дамп (RPO до ~24ч, PITR пока нет); см.
> [`SPEC_sre.md` §3.2](../docs/design/specs/platform/SPEC_sre.md).

## Healthcheck'и

Все три сервиса сообщают здоровье (`docker compose ps` → `healthy`), оркестрация
ждёт зависимости (`proxy` ждёт `backend` healthy; `backend` ждёт `db` healthy):

- `db` — `pg_isready` (postgres:16).
- `backend` — GET `/api/health` через собственный `python` образа (в slim-образе нет
  curl/wget); без авторизации, возвращает 200 даже при недоступном ИРБИС.
- `proxy` — `curl -fsk https://localhost/` (nginx:alpine несёт curl; `-k` для
  самоподписанного dev-сертификата).

## Переход к реальному пилоту

См. [`docs/design/PILOT_READINESS.md`](../docs/design/PILOT_READINESS.md) — конкретный
go-live чек-лист (реальные секреты, реальный TLS-сертификат, провижининг первого
арендатора, расписание бэкапов + проверенный restore, доступ к мониторингу/логам,
миграция данных, план отката), честный в том, что готово к пилоту, а что нет (нет HA,
нет PITR, нет сертифицированных СКЗИ, мост к живому ИРБИС опционален).

## Чек-лист прод-хардненинга

- [ ] **Секреты:** задать сильные `POSTGRES_PASSWORD` + `APP_SECRET`; брать `.env`
      из менеджера секретов (Vault/SOPS), не из файла на диске. Не коммитить `.env`.
- [ ] **TLS:** реальный сертификат (не самоподписанный); включить HSTS; только TLS 1.2/1.3 (задано).
- [ ] **Нет открытых внутренних портов:** держать порты хоста `db` и `backend`
      закомментированными (по умолчанию); порты публикует только proxy.
- [ ] **БД:** ограничить сетевую доступность `POSTGRES`; включить бэкапы/PITR
      (см. `SPEC_iac_fleet.md` §1.2 / SPEC_sre); запинить дайджест `postgres:16`.
- [ ] **Образы:** пинить базовые образы по дайджесту; сканировать (Trivy) + подписывать
      (cosign) в CI по [`SPEC_I6 §B`](../docs/design/specs/SPEC_I6_security_compliance.md).
- [ ] **Изоляция арендаторов:** проверить изоляцию схем-на-арендатора после провижининга.
- [ ] **Reverse-proxy:** ужесточить CSP и `client_max_body_size`; добавить rate-limit.
- [ ] **152-ФЗ / РДР:** убедиться, что ПДн читателей не попадают в логи/телеметрию.
- [ ] **Обновления:** `docker compose pull && docker compose up -d --build` в окно
      обслуживания; тома сохранять.

## Файлы

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | Стек: `db` + `backend` + `proxy`, тома, healthcheck'и (все 3 сервиса) |
| `Dockerfile.backend` | Многостадийный: сборка SPA → Python-рантайм, отдающий API + dist |
| `Dockerfile.frontend` | Сборка артефакта SPA (альтернативная топология proxy-serves-dist; не в дефолтном `up`) |
| `proxy/nginx.conf` | Терминация TLS + reverse-proxy на бэкенд |
| `proxy/gen-cert.sh` | Генерация dev самоподписанного сертификата (кросс-платформенно: Linux/macOS + Windows git-bash) |
| `backup/pg_backup.sh` | `pg_dump` сервиса `db` в файл с таймстампом в томе `backups` |
| `backup/pg_restore.sh` | Восстановление дампа (живая БД или throwaway-БД для restore-тестов) |
| `.env.example` | Все env-переменные с безопасными dev-дефолтами + метки CHANGE IN PROD |
| `.dockerignore` | Держать секреты / состояние / артефакты сборки вне слоёв образа |
```
