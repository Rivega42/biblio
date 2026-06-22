#!/usr/bin/env sh
# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL backup for the Biblio deploy stack (post-MVP pilot hardening, #223).
#
# Dumps the `db` service (the Access store: accounts / grants / audit / tenancy)
# to a TIMESTAMPED file inside the `backups` named volume (mounted at /backups in
# the db container). Uses `docker compose exec` against the already-running stack
# — no host pg_dump needed, credentials never appear on the host command line.
#
#   sh deploy/backup/pg_backup.sh                  # one dump → /backups/<db>-<ts>.dump
#   KEEP=14 sh deploy/backup/pg_backup.sh          # also prune dumps older than 14
#   FORMAT=plain sh deploy/backup/pg_backup.sh     # plain SQL instead of custom
#
# Output (inside the `backups` volume, survives container recreate):
#   /backups/<POSTGRES_DB>-YYYYmmdd-HHMMSS.dump     (custom format, default)
#   /backups/<POSTGRES_DB>-YYYYmmdd-HHMMSS.sql.gz   (FORMAT=plain)
#
# Restore with: deploy/backup/pg_restore.sh <file>   (see that script).
# Schedule with cron / Task Scheduler — see "SCHEDULING" at the bottom and
# docs/design/PILOT_READINESS.md → "Backups".
# ─────────────────────────────────────────────────────────────────────────────
set -eu

# Windows git-bash / MSYS mangles arguments that look like Unix paths (e.g. the
# container path "/backups/…" passed to `docker compose exec pg_dump -f`) into
# "C:/Program Files/Git/backups/…". Every "/…" path in this script is a path
# INSIDE the db container, never a host path, so disabling conversion is safe.
# No-op on Linux/macOS. (Same class of fix as proxy/gen-cert.sh.)
export MSYS_NO_PATHCONV=1

# Run from deploy/ so `docker compose` finds the compose file + .env regardless
# of the caller's CWD.
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEPLOY_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$DEPLOY_DIR"

# docker compose v2 (plugin) vs legacy docker-compose.
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "ERROR: docker compose (v2) or docker-compose not found on PATH." >&2
    exit 1
fi

# Credentials come from .env (gitignored) → fall back to the compose defaults.
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-irbis_access}"
if [ -f .env ]; then
    PG_USER=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_USER:-$PG_USER}") || true
    PG_DB=$(. ./.env >/dev/null 2>&1; echo "${POSTGRES_DB:-$PG_DB}") || true
fi

FORMAT="${FORMAT:-custom}"
TS=$(date +%Y%m%d-%H%M%S)

# Confirm the db service is up before we try to dump.
if ! $DC ps --status running db 2>/dev/null | grep -q db; then
    echo "ERROR: the 'db' service is not running. Start the stack first:" >&2
    echo "       (cd $DEPLOY_DIR && $DC up -d db)" >&2
    exit 1
fi

if [ "$FORMAT" = "plain" ]; then
    OUT="/backups/${PG_DB}-${TS}.sql.gz"
    echo "Backing up '$PG_DB' (plain SQL, gzip) → ${OUT} (in 'backups' volume)"
    # pg_dump | gzip, all inside the container so the dump never crosses to host.
    $DC exec -T db sh -c \
        "pg_dump -U '$PG_USER' -d '$PG_DB' --no-owner --no-privileges | gzip -c > '$OUT'"
else
    OUT="/backups/${PG_DB}-${TS}.dump"
    echo "Backing up '$PG_DB' (custom format) → ${OUT} (in 'backups' volume)"
    # Custom format (-Fc): compressed, supports selective + parallel restore.
    $DC exec -T db \
        pg_dump -U "$PG_USER" -d "$PG_DB" -Fc --no-owner --no-privileges -f "$OUT"
fi

# Report size + list current backups.
echo "Done. Backups currently in the volume:"
$DC exec -T db sh -c "ls -lh /backups/ 2>/dev/null | grep -E '\.(dump|sql\.gz)$' || echo '(none)'"

# Optional retention: keep only the newest $KEEP dumps (by mtime), prune the rest.
if [ -n "${KEEP:-}" ]; then
    echo "Retention: keeping newest $KEEP dump(s), pruning older…"
    $DC exec -T db sh -c \
        "cd /backups && ls -1t *.dump *.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f -- ; echo 'pruned.'"
fi

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULING (cron / Task Scheduler)
#
# Per SPEC_sre §3.2, a single-node pilot starts with a nightly logical dump
# (RPO ≈ up to 24h; tighten with WAL archiving when you move to multi-node).
#
# Linux/macOS cron — nightly 02:30, keep 14 days, log to a file:
#   30 2 * * *  KEEP=14 /path/to/repo/deploy/backup/pg_backup.sh >> /var/log/biblio-backup.log 2>&1
#
# Windows Task Scheduler (git-bash):
#   schtasks /Create /SC DAILY /ST 02:30 /TN "biblio-pg-backup" ^
#     /TR "\"C:\Program Files\Git\bin\sh.exe\" C:\IRBIS64\_recon\deploy\backup\pg_backup.sh"
#
# 3-2-1 (SPEC_sre §3.2): copy the `backups` volume off-box to a second location
# (and ideally one immutable/offline copy). Inspect the volume on the host with:
#   docker compose -f deploy/docker-compose.yml exec db ls -lh /backups
#   docker run --rm -v deploy_backups:/b -v "$PWD":/out alpine cp -r /b /out/backups-copy
#   (volume name is "<project>_backups"; check `docker volume ls`)
# ─────────────────────────────────────────────────────────────────────────────
