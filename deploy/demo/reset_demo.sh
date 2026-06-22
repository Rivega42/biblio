#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# Периодический СБРОС публичного демо-стенда Biblio к эталону (issue #226).
#
# Зачем: демо-стенд read-mostly и публичный — любой посетитель может что-то
# изменить. Чтобы стенд всегда выглядел опрятно для экспертов реестра, его
# СОДЕРЖИМОЕ периодически возвращается к «эталонному» снимку (golden snapshot).
#
# Механизм (без потери схемы/паролей разработчиков):
#   • golden-снимок — это обычный pg_dump демо-БД, снятый СРАЗУ ПОСЛЕ seed_demo.sh
#     (см. --snapshot), плюс пометка own-store sqlite как эталона;
#   • при сбросе: restore golden-дампа в PostgreSQL (Access-стор) и пере-сидинг
#     own-store каталога/читателей штатными скриптами. Демо-правки посетителей
#     исчезают, эталон восстанавливается.
#
# Режимы:
#   sh demo/reset_demo.sh --snapshot   # один раз: снять эталонный снимок ПОСЛЕ сида
#   sh demo/reset_demo.sh              # сброс к последнему эталонному снимку
#   sh demo/reset_demo.sh --reseed     # сброс «с нуля»: пере-провижининг + сид
#
# Планирование (cron / Task Scheduler) — см. блок SCHEDULING внизу. Типично:
# ночной сброс раз в сутки. RPO здесь не важен (демо не хранит ценных данных).
# ─────────────────────────────────────────────────────────────────────────────
set -eu
export MSYS_NO_PATHCONV=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEPLOY_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$DEPLOY_DIR"

if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "ОШИБКА: docker compose (v2) или docker-compose не найдены в PATH." >&2
    exit 1
fi

COMPOSE="-f docker-compose.yml -f docker-compose.demo.yml"

PG_USER="postgres"; PG_DB="irbis_access"
if [ -f .env ]; then
    # shellcheck disable=SC1091
    PG_USER=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_USER:-postgres}") || true
    PG_DB=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_DB:-irbis_access}") || true
fi

# Эталонный дамп держим в томе backups под фиксированным именем (перезаписывается
# только при --snapshot). Так restore не зависит от таймстампов.
GOLDEN="/backups/demo-golden.dump"

require_running() {
    if ! $DC $COMPOSE ps --status running backend 2>/dev/null | grep -q backend; then
        echo "ОШИБКА: демо-стек не запущен. Поднимите его:" >&2
        echo "       (cd $DEPLOY_DIR && $DC $COMPOSE up -d --build)" >&2
        exit 1
    fi
}

MODE="${1:-reset}"

case "$MODE" in
    --snapshot)
        require_running
        echo "Снимаю ЭТАЛОННЫЙ снимок демо-БД '$PG_DB' → $GOLDEN (в томе backups)…"
        echo "  (выполните это ОДИН РАЗ сразу после успешного demo/seed_demo.sh)"
        $DC $COMPOSE exec -T db \
            pg_dump -U "$PG_USER" -d "$PG_DB" -Fc --no-owner --no-privileges -f "$GOLDEN"
        echo "Готово. Эталон зафиксирован: $GOLDEN"
        echo "Теперь периодический 'sh demo/reset_demo.sh' будет возвращать стенд к нему."
        ;;

    --reseed)
        require_running
        echo "Полный пере-сид демо-стенда (провижининг + каталог + читатели)…"
        sh "$SCRIPT_DIR/seed_demo.sh"
        echo "Пере-сид завершён. Не забудьте обновить эталон: sh demo/reset_demo.sh --snapshot"
        ;;

    reset|"")
        require_running
        # Есть ли эталонный снимок?
        if $DC $COMPOSE exec -T db sh -c "[ -f '$GOLDEN' ]"; then
            echo "Сброс демо к эталонному снимку $GOLDEN…"
            # Восстановление Access-стора из golden-дампа (FORCE — без интерактива).
            FORCE=1 sh "$SCRIPT_DIR/../backup/pg_restore.sh" "demo-golden.dump"
            # Own-store (каталог) сбрасываем пере-сидом: записи идемпотентны по
            # заглавию, но чужие демо-правки в каталоге переживут restore PG.
            # Чтобы каталог тоже вернулся к эталону — очищаем CATALOG_DB и сидим.
            echo "Сброс own-store каталога к эталону…"
            $DC $COMPOSE exec -T backend sh -c \
                'rm -f "${CATALOG_DB:-/data/catalog.db}" 2>/dev/null || true'
            $DC $COMPOSE exec -T backend python - < "$SCRIPT_DIR/seed_demo_catalog.py"
            echo "Сброс завершён: Access-стор — из golden-дампа, каталог — пере-сидинг."
        else
            echo "Эталонный снимок $GOLDEN не найден — выполняю полный пере-сид."
            echo "  (после него снимите эталон: sh demo/reset_demo.sh --snapshot)"
            sh "$SCRIPT_DIR/seed_demo.sh"
        fi
        ;;

    *)
        echo "Неизвестный режим: $MODE" >&2
        echo "Использование: sh demo/reset_demo.sh [--snapshot | --reseed]" >&2
        exit 2
        ;;
esac

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULING (cron / Task Scheduler) — периодический сброс публичного демо.
#
# Linux/macOS cron — ежедневный сброс в 04:00, лог в файл:
#   0 4 * * *  /path/to/repo/deploy/demo/reset_demo.sh >> /var/log/biblio-demo-reset.log 2>&1
#
# Windows Task Scheduler (git-bash):
#   schtasks /Create /SC DAILY /ST 04:00 /TN "biblio-demo-reset" ^
#     /TR "\"C:\Program Files\Git\bin\sh.exe\" C:\IRBIS64\_recon\deploy\demo\reset_demo.sh"
#
# Порядок первичной настройки на сервере в РФ:
#   1) up -d (demo overlay)  2) sh demo/seed_demo.sh  3) sh demo/reset_demo.sh --snapshot
#   4) поставить cron/Task Scheduler на ежедневный 'sh demo/reset_demo.sh'.
# Подробности — docs/deploy/DEMO_STAND.md → «Сброс и ретенция».
# ─────────────────────────────────────────────────────────────────────────────
