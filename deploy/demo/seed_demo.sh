#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# Наполнение ПУБЛИЧНОГО ДЕМО-СТЕНДА Biblio показательными данными (issue #226).
#
# Переиспользует ШТАТНЫЕ механизмы бэкенда (НИЧЕГО не дублирует):
#   1) python -m access.provision <slug> — заводит демо-арендатора:
#        схема-на-арендатора + системные словари + админ-аккаунт + план/модули
#        (см. irbis-web/backend/access/provision.py). Идемпотентно.
#   2) deploy/demo/seed_demo_catalog.py — кладёт ~10 показательных записей в
#        own-store каталога через CatalogStore.save() (без живого ИРБИС, без ПДн).
#   3) deploy/demo/seed_demo_engines.py — оживляет НОВЫЕ блоки продукта на own-store
#        (связи иерархии /api/linked, полные тексты /api/fulltext, книгообеспеченность
#        /api/bp/provision) через штатные движки. Зависит от шага 2 (привязки КО
#        ссылаются на инв.№ демо-каталога). Идемпотентно.
#   4) демо-читатели БЕЗ реальных ПДн — создаются как обычные учётные записи
#        через python -m access.seed-подобный вызов (вымышленные имена).
#
# Запускать ПОСЛЕ подъёма демо-стека:
#   cd deploy
#   docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build
#   sh demo/seed_demo.sh
#
# Параметры читаются из deploy/.env (скопированного из .env.demo.example):
#   DEMO_TENANT_SLUG, DEMO_TENANT_NAME, DEMO_ADMIN_LOGIN, DEMO_ADMIN_PASSWORD,
#   DEMO_PLAN. Безопасные дефолты заданы ниже на случай отсутствия .env.
# ─────────────────────────────────────────────────────────────────────────────
set -eu

# git-bash / MSYS не должен превращать аргументы вида "/app/…" в windows-пути:
# все "/…"-пути здесь — это пути ВНУТРИ контейнера. No-op на Linux/macOS.
export MSYS_NO_PATHCONV=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEPLOY_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$DEPLOY_DIR"

# docker compose v2 (плагин) vs legacy docker-compose.
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "ОШИБКА: docker compose (v2) или docker-compose не найдены в PATH." >&2
    exit 1
fi

# Базовый + demo-overlay компоновки (тот же набор файлов, что и при up).
COMPOSE="-f docker-compose.yml -f docker-compose.demo.yml"

# Параметры демо из .env (gitignored) → дефолты.
DEMO_TENANT_SLUG="demo"; DEMO_TENANT_NAME="Демо-библиотека Biblio"
DEMO_ADMIN_LOGIN="demo"; DEMO_ADMIN_PASSWORD="demo"; DEMO_PLAN="standard"
if [ -f .env ]; then
    # shellcheck disable=SC1091
    DEMO_TENANT_SLUG=$(. ./.env >/dev/null 2>&1; echo "${DEMO_TENANT_SLUG:-demo}") || true
    DEMO_TENANT_NAME=$(. ./.env >/dev/null 2>&1; echo "${DEMO_TENANT_NAME:-Демо-библиотека Biblio}") || true
    DEMO_ADMIN_LOGIN=$(. ./.env >/dev/null 2>&1; echo "${DEMO_ADMIN_LOGIN:-demo}") || true
    DEMO_ADMIN_PASSWORD=$(. ./.env >/dev/null 2>&1; echo "${DEMO_ADMIN_PASSWORD:-demo}") || true
    DEMO_PLAN=$(. ./.env >/dev/null 2>&1; echo "${DEMO_PLAN:-standard}") || true
fi

# Бэкенд должен быть запущен (сид идёт через exec в backend-контейнер).
if ! $DC $COMPOSE ps --status running backend 2>/dev/null | grep -q backend; then
    echo "ОШИБКА: сервис 'backend' не запущен. Сначала поднимите демо-стек:" >&2
    echo "       (cd $DEPLOY_DIR && $DC $COMPOSE up -d --build)" >&2
    exit 1
fi

echo "════════════════════════════════════════════════════════════════════════"
echo " Наполнение демо-стенда Biblio (арендатор: $DEMO_TENANT_SLUG, план: $DEMO_PLAN)"
echo "════════════════════════════════════════════════════════════════════════"

# ── Шаг 1: провижининг демо-арендатора (словари + админ + план) ───────────────
echo "[1/4] Провижининг демо-арендатора (схема + словари + админ + план)…"
$DC $COMPOSE exec -T backend \
    python -m access.provision "$DEMO_TENANT_SLUG" \
        --name "$DEMO_TENANT_NAME" \
        --admin "$DEMO_ADMIN_LOGIN" \
        --password "$DEMO_ADMIN_PASSWORD" \
        --plan "$DEMO_PLAN"

# ── Шаг 2: демо-каталог в own-store (без ИРБИС, без ПДн) ──────────────────────
echo "[2/4] Загрузка демо-каталога в own-store…"
# Скрипт лежит в репозитории, в контейнер не копировался → подаём через stdin.
$DC $COMPOSE exec -T backend python - < "$SCRIPT_DIR/seed_demo_catalog.py"

# ── Шаг 3: own-store движки связности (linked / fulltext / book-provision) ─────
# Оживляет НОВЫЕ блоки продукта на own-store: журнал+статьи и многотомник+тома
# (/api/linked), записи с полем 955 + RIGHT-шаблон (/api/fulltext), связку ВУЗ с
# привязками литературы (/api/bp/provision). Идёт ПОСЛЕ каталога — привязки КО
# ссылаются на инв.№ демо-каталога (910^b). Тоже через stdin.
echo "[3/4] Оживление новых блоков на own-store (linked / fulltext / КО)…"
$DC $COMPOSE exec -T backend python - < "$SCRIPT_DIR/seed_demo_engines.py"

# ── Шаг 4: демо-читатели БЕЗ реальных ПДн ─────────────────────────────────────
# Вымышленные читатели для демонстрации абонемента/ЛК. Имена/email — синтетические
# (домен example.org зарезервирован RFC 2606), никаких реальных ПДн. Создаём через
# штатный create_account + роль reader-service (как в access/seed.py), не дублируя
# логику хеширования паролей.
echo "[4/4] Создание демо-читателей (синтетические данные, без реальных ПДн)…"
$DC $COMPOSE exec -T backend python - <<'PY'
import os, sys
sys.path.insert(0, "/app/backend")
from access.store import AccessStore
from access import seed as access_seed

store = AccessStore(os.environ.get("ACCESS_DB", "/data/access.db"))
# Роли (idempotent): берём те же определения, что и dev-seed.
role_ids = {}
for name, grants in access_seed.ROLE_GRANTS.items():
    rid = store.add_role(name)
    role_ids[name] = rid
    for fn, db, lvl in grants:
        store.add_role_grant(rid, fn, db, lvl)

# Демо-читатели: только синтетические данные (RFC 2606 example.org).
DEMO_READERS = [
    ("reader1", "reader1", "Демо Читатель Первый",  "reader1@example.org"),
    ("reader2", "reader2", "Демо Читатель Второй",  "reader2@example.org"),
    ("reader3", "reader3", "Демо Читатель Третий",  "reader3@example.org"),
]
created = 0
for login, pw, full, _email in DEMO_READERS:
    acc = store.create_account(login, pw, full)
    rid = role_ids.get("reader-service")
    if rid is not None:
        try:
            store.assign_role(acc["id"], rid)
        except Exception:
            pass
    created += 1
    print("  + демо-читатель: %s (%s)" % (login, full))
print("Демо-читателей обработано: %d (синтетические, без реальных ПДн)." % created)
PY

echo "════════════════════════════════════════════════════════════════════════"
echo " Готово. Демо-стенд наполнен."
echo "   Админ-доступ : $DEMO_ADMIN_LOGIN / $DEMO_ADMIN_PASSWORD"
echo "   Читатели     : reader1..reader3 (пароль = логин)"
echo "   Откройте https://<домен-демо>/  (примите dev-сертификат, если самоподписан)"
echo ""
echo " Напоминание: демо read-mostly, периодически сбрасывается к эталону —"
echo "   см. deploy/demo/reset_demo.sh и docs/deploy/DEMO_STAND.md."
echo "════════════════════════════════════════════════════════════════════════"
