#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL restore for the Biblio deploy stack (post-MVP pilot hardening, #223).
#
# Restores a dump produced by deploy/backup/pg_backup.sh back into the `db`
# service. Reads the dump from inside the `backups` named volume (mounted at
# /backups in the db container).
#
#   sh deploy/backup/pg_restore.sh                          # list available dumps
#   sh deploy/backup/pg_restore.sh irbis_access-20260622-021500.dump
#   sh deploy/backup/pg_restore.sh /backups/foo.sql.gz      # plain-SQL gz dump
#
# ⚠ DESTRUCTIVE: restoring overwrites objects in the target database. The custom-
#   format path runs pg_restore with --clean --if-exists (drops then recreates).
#   You are prompted to confirm unless FORCE=1 is set.
#
# RESTORE-TEST (rehearsal — SPEC_sre §3.4 "бэкап рабочий только после restore"):
#   A backup is only trustworthy once a restore has been *exercised*. To test a
#   restore WITHOUT touching the live DB, restore into a throwaway database:
#       RESTORE_DB=irbis_restore_test sh deploy/backup/pg_restore.sh <file>
#   then sanity-check it and drop it:
#       docker compose -f deploy/docker-compose.yml exec db \
#         psql -U postgres -d irbis_restore_test -c "\dn"   # schemas present?
#       docker compose -f deploy/docker-compose.yml exec db \
#         dropdb -U postgres irbis_restore_test
#   Do this monthly (see docs/design/PILOT_READINESS.md → "Backups").
# ─────────────────────────────────────────────────────────────────────────────
set -eu

# Windows git-bash / MSYS mangles "/backups/…" container-path arguments into
# "C:/Program Files/Git/backups/…". Every "/…" path here is a path INSIDE the
# db container, never a host path, so disabling conversion is safe. No-op on
# Linux/macOS. (Same class of fix as proxy/gen-cert.sh.)
export MSYS_NO_PATHCONV=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEPLOY_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$DEPLOY_DIR"

if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "ERROR: docker compose (v2) or docker-compose not found on PATH." >&2
    exit 1
fi

PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-irbis_access}"
if [ -f .env ]; then
    PG_USER=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_USER:-$PG_USER}") || true
    PG_DB=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_DB:-$PG_DB}") || true
fi
# Target DB: default the live DB; override with RESTORE_DB for a test restore.
TARGET_DB="${RESTORE_DB:-$PG_DB}"

if ! $DC ps --status running db 2>/dev/null | grep -q db; then
    echo "ERROR: the 'db' service is not running. Start it first:" >&2
    echo "       (cd $DEPLOY_DIR && $DC up -d db)" >&2
    exit 1
fi

FILE="${1:-}"
if [ -z "$FILE" ]; then
    echo "Available dumps in the 'backups' volume:"
    $DC exec -T db sh -c "ls -lh /backups/ 2>/dev/null | grep -E '\.(dump|sql\.gz)$' || echo '(none)'"
    echo ""
    echo "Usage: sh deploy/backup/pg_restore.sh <dump-file>"
    echo "       (file is relative to /backups unless given as an absolute path)"
    exit 0
fi

# Resolve to a /backups path unless an absolute container path was given.
case "$FILE" in
    /*) SRC="$FILE" ;;
    *)  SRC="/backups/$FILE" ;;
esac

if ! $DC exec -T db sh -c "[ -f '$SRC' ]"; then
    echo "ERROR: dump not found inside the db container at: $SRC" >&2
    echo "       Run 'sh deploy/backup/pg_restore.sh' with no args to list dumps." >&2
    exit 1
fi

# Confirmation gate (skip with FORCE=1, e.g. in automated rehearsals).
if [ "${FORCE:-0}" != "1" ]; then
    printf 'Restore %s INTO database "%s" (this overwrites existing objects). Continue? [y/N] ' "$SRC" "$TARGET_DB"
    read -r ans
    case "$ans" in y|Y|yes|YES) ;; *) echo "Aborted."; exit 1 ;; esac
fi

# Ensure the target DB exists (createdb is a no-op-ish if it already exists).
$DC exec -T db sh -c "createdb -U '$PG_USER' '$TARGET_DB' 2>/dev/null || true"

echo "Restoring $SRC → database '$TARGET_DB'…"
case "$SRC" in
    *.sql.gz)
        # Plain SQL gzip dump → pipe through psql.
        $DC exec -T db sh -c "gunzip -c '$SRC' | psql -U '$PG_USER' -d '$TARGET_DB' -v ON_ERROR_STOP=1"
        ;;
    *.sql)
        $DC exec -T db sh -c "psql -U '$PG_USER' -d '$TARGET_DB' -v ON_ERROR_STOP=1 -f '$SRC'"
        ;;
    *)
        # Custom format (-Fc) → pg_restore with clean+if-exists for idempotency.
        $DC exec -T db \
            pg_restore -U "$PG_USER" -d "$TARGET_DB" --clean --if-exists --no-owner --no-privileges "$SRC"
        ;;
esac

echo "Restore complete. Quick check (schemas in '$TARGET_DB'):"
$DC exec -T db psql -U "$PG_USER" -d "$TARGET_DB" -c "\dn" || true
