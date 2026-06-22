# Biblio — containerized deployment (MVP Phase 2)

One-command deployment of the Biblio web stack: a TLS reverse proxy, the Python
backend (API + built SPA), and PostgreSQL. Closes #207 (epic #223).

> Aligns with the production-packaging shape in
> [`SPEC_iac_fleet.md` §1.2 / §6.3](../docs/design/specs/platform/SPEC_iac_fleet.md)
> (single-node Docker stack: app + PostgreSQL behind an internal reverse proxy /
> TLS termination, env-only secrets, no secrets in images). This `deploy/` is the
> single-node compose bundle; the full IaC/fleet topology in that spec is a later
> phase.

## Topology

```
                         ┌──────────────────────────────────────────────┐
   https://localhost ──▶ │ proxy (nginx)  — TLS termination (443→…)      │
                         └───────────────┬──────────────────────────────┘
                                         │ http (compose network)
                         ┌───────────────▼──────────────────────────────┐
                         │ backend (Python · server.py)                 │
                         │   • serves the JSON API (/api/*)             │
                         │   • serves the built SPA (frontend/dist)     │
                         └───────────────┬──────────────────────────────┘
                                         │ postgresql://db:5432
                         ┌───────────────▼──────────────────────────────┐
                         │ db (postgres:16) — Access store + tenancy     │
                         └──────────────────────────────────────────────┘
```

- **How the SPA (`dist/`) is served — backend-serves-dist.** `Dockerfile.backend`
  is multi-stage: a `node` stage runs `vite build`, and the built `dist/` is
  copied into the runtime image at `frontend/dist`. The backend's
  `static_files.py` detects it (`has_dist()`) and the single Python process
  serves both the API and the SPA. One container, one routing source of truth.
  (`Dockerfile.frontend` exists for the *alternative* "proxy serves static dist"
  topology and is **not** part of the default `up` — see the comments in it.)
- **TLS.** The `proxy` (nginx) terminates TLS on **:443** and reverse-proxies
  everything to the backend. Dev uses a **self-signed** cert (browsers will
  warn — expected). HTTP **:80** redirects to HTTPS.
- **Access store on PostgreSQL.** The backend runs with
  `ACCESS_BACKEND=postgres` against the `db` service (ADR-004). Engines still on
  sqlite (notify/catalog/circ/acq/bp) write to a persisted named volume.

## One-command up

```sh
cd deploy
cp .env.example .env          # 1. fill in secrets (see CHANGE IN PROD markers)
sh proxy/gen-cert.sh          # 2. generate a dev self-signed TLS cert
docker compose up --build     # 3. bring up db + backend + proxy
```

Then open **https://localhost** (accept the self-signed-cert warning in dev).

Stop / reset:

```sh
docker compose down           # stop, keep volumes (data persists)
docker compose down -v        # stop + delete volumes (wipe PG + sqlite data)
```

## Environment

All config is env-driven; nothing sensitive is baked into an image.
Copy `.env.example` → `.env` (gitignored) and set at least:

| Var | Purpose | Dev default | Prod |
|---|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL superuser password | `devpassword` | **CHANGE** — long random |
| `APP_SECRET` | Signs sessions/JWT | `dev-insecure-…` | **CHANGE** — `openssl rand -hex 32` |
| `POSTGRES_USER` / `POSTGRES_DB` | PG role / database | `postgres` / `irbis_access` | as needed |
| `HTTP_PORT` / `HTTPS_PORT` | Host ports for the proxy | `80` / `443` | as needed |
| `IRBIS_HOST` / `IRBIS_PORT` | Live ИРБИС64 TCP server (optional) | `host.docker.internal:6666` | your server |
| `IRBIS_USER` / `IRBIS_PASS` | ИРБИС service account | `MASTER` / *(empty)* | **CHANGE** |
| `IRBIS_DB_DEFAULT` / `IRBIS_PUBLIC_DBS` | default + reader-visible DBs | `IBIS` / `IBIS` | as needed |

> The full env model the backend understands lives in `irbis-web/backend/config.py`
> and `access/pgstore.py` (`ACCESS_BACKEND`, `ACCESS_PG_DSN`, the `*_DB` sqlite
> paths). The compose file wires these for you.

## Provisioning the first tenant

The Access store is multi-tenant (control schema + per-tenant schema `t_<slug>`).
After the stack is up, provision a tenant via the provisioning CLI (added by a
sibling task):

```sh
# inside the running backend container:
docker compose exec backend python -m access.provision <slug>
```

> **Next step / dependency:** `python -m access.provision <slug>` is provided by
> the tenant-provisioning task (sibling agent). It runs `ensure_control_schema()`
> + the per-tenant schema/migrations/seed against `ACCESS_PG_DSN`. Until that CLI
> lands, the PG control + tenant schemas can be created with the tenancy helpers
> in `access/pgstore.py`. This deployment infra is ready for it — the backend
> already points at PostgreSQL.

## TLS notes

- **Dev:** `sh proxy/gen-cert.sh` writes `proxy/certs/{server.crt,server.key}`
  (gitignored). Self-signed → browser warning is expected.
  Regenerate with a custom name: `CERT_CN=biblio.local sh proxy/gen-cert.sh`.
- **Prod:** replace those two files with a certificate from your CA (internal CA
  / certbot / Let's Encrypt — the nginx HTTP server already exposes the ACME
  `http-01` webroot). Then enable HSTS (uncomment the `Strict-Transport-Security`
  header in `proxy/nginx.conf`).

## Backups & restore

`pg_dump`-based backup/restore of the `db` service, writing into a `backups`
named volume (survives container recreate, stays out of git/host):

```sh
sh deploy/backup/pg_backup.sh                 # one timestamped dump → backups volume
KEEP=14 sh deploy/backup/pg_backup.sh         # + prune all but the newest 14
sh deploy/backup/pg_restore.sh                # list available dumps
sh deploy/backup/pg_restore.sh <dump-file>    # restore (prompts; FORCE=1 to skip)
```

Test a restore without touching live data (rehearse into a throwaway DB):

```sh
FORCE=1 RESTORE_DB=irbis_restore_test sh deploy/backup/pg_restore.sh <dump-file>
docker compose exec db psql -U postgres -d irbis_restore_test -c "\dn"   # verify
docker compose exec db dropdb -U postgres irbis_restore_test             # clean up
```

Scheduling (cron / Task Scheduler), 3-2-1 off-box copies, and the monthly
restore-test cadence are documented in `pg_backup.sh` and in
[`docs/design/PILOT_READINESS.md`](../docs/design/PILOT_READINESS.md) → "Backups".
> Single-node pilot = nightly logical dump (RPO up to ~24h, no PITR yet); see
> [`SPEC_sre.md` §3.2](../docs/design/specs/platform/SPEC_sre.md).

## Healthchecks

All three services report health (`docker compose ps` → `healthy`), and
orchestration waits on dependencies (`proxy` waits for `backend` healthy;
`backend` waits for `db` healthy):

- `db` — `pg_isready` (postgres:16).
- `backend` — GET `/api/health` via the image's own `python` (the slim image has
  no curl/wget); unauthenticated, returns 200 even when ИРБИС is down.
- `proxy` — `curl -fsk https://localhost/` (nginx:alpine ships curl; `-k` for the
  self-signed dev cert).

## Going to a real pilot

See [`docs/design/PILOT_READINESS.md`](../docs/design/PILOT_READINESS.md) — a
concrete go-live checklist (real secrets, real TLS cert, first-tenant
provisioning, backup schedule + tested restore, monitoring/log access, data
migration, rollback plan) that is honest about what is pilot-ready vs not (no HA,
no PITR, no certified СКЗИ, optional live-ИРБИС bridge).

## Prod hardening checklist

- [ ] **Secrets:** set strong `POSTGRES_PASSWORD` + `APP_SECRET`; source `.env`
      from a secret manager (Vault/SOPS), not a file on disk. Never commit `.env`.
- [ ] **TLS:** real cert (not self-signed); enable HSTS; TLS 1.2/1.3 only (set).
- [ ] **No exposed internal ports:** keep `db` and `backend` host ports
      commented out (default); only the proxy publishes ports.
- [ ] **DB:** restrict `POSTGRES` network exposure; enable backups/PITR
      (see `SPEC_iac_fleet.md` §1.2 / SPEC_sre); pin the `postgres:16` digest.
- [ ] **Images:** pin base images by digest; scan (Trivy) + sign (cosign) in CI
      per [`SPEC_I6 §B`](../docs/design/specs/SPEC_I6_security_compliance.md).
- [ ] **Tenant isolation:** verify per-tenant schema isolation after provisioning.
- [ ] **Reverse proxy:** tighten CSP and `client_max_body_size`; add rate limits.
- [ ] **152-ФЗ / РДР:** confirm reader PII stays out of logs/telemetry.
- [ ] **Updates:** `docker compose pull && docker compose up -d --build` on a
      maintenance window; keep volumes.

## Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | The stack: `db` + `backend` + `proxy`, volumes, healthchecks (all 3 services) |
| `Dockerfile.backend` | Multi-stage: build SPA → Python runtime serving API + dist |
| `Dockerfile.frontend` | SPA artifact build (alternative proxy-serves-dist topology; not in default `up`) |
| `proxy/nginx.conf` | TLS termination + reverse proxy to backend |
| `proxy/gen-cert.sh` | Generate a dev self-signed cert (cross-platform: Linux/macOS + Windows git-bash) |
| `backup/pg_backup.sh` | `pg_dump` the `db` service to a timestamped file in the `backups` volume |
| `backup/pg_restore.sh` | Restore a dump (live DB or a throwaway DB for restore-tests) |
| `.env.example` | Every env var with safe dev defaults + CHANGE IN PROD markers |
| `.dockerignore` | Keep secrets / state / build output out of image layers |
```
