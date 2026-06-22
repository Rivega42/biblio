# Pilot readiness — go-live checklist (post-MVP, epic #223)

> Concrete checklist to take the `deploy/` stack from a local MVP demo to a **real
> pilot** at a single library (e.g. СПб ГТБ / first tenant). It is deliberately
> **honest** about what is pilot-ready and what is *not* yet production-grade.
>
> Scope: the single-node Docker stack in [`deploy/`](../../deploy/) —
> `proxy` (nginx, TLS) → `backend` (Python, API + built SPA) → `db`
> (`postgres:16`). The full multi-region IaC/fleet topology
> ([`SPEC_iac_fleet.md`](specs/platform/SPEC_iac_fleet.md)) is a later phase.
>
> Reliability targets and DR policy referenced here are the **single-node /
> on-prem tier** of [`SPEC_sre.md`](specs/platform/SPEC_sre.md) (D4): one node = no
> HA, RPO up to the last nightly dump, RTO in minutes-to-hours — to be stated
> explicitly in the pilot SLA (SPEC_sre §1.3 "Tiering", §3.1 note).

---

## TL;DR — pilot-ready vs not

| Area | Pilot-ready? | Notes |
|---|---|---|
| One-command stack (proxy/backend/db) | ✅ Yes | `docker compose up --build`; healthchecks gate orchestration |
| TLS termination | ✅ Yes (with a real cert) | nginx terminates TLS; dev uses self-signed → **replace for pilot** |
| Env-only secrets | ✅ Yes | nothing sensitive in images or git; `.env` gitignored |
| Multi-tenant Access store on PostgreSQL | ✅ Yes | schema-per-tenant; provision via `python -m access.provision` |
| Backups + tested restore | ✅ Yes (nightly logical) | `deploy/backup/*`; RPO ≈ up to 24h — **acceptable for pilot, state in SLA** |
| Healthchecks / readiness | ⚠️ Partial | container healthchecks present; no `/readyz` split, no external monitoring stack |
| High availability / failover | ❌ No | single node; PG failover, replicas, multi-AZ are D3/IaC (post-pilot) |
| Observability (metrics/traces/alerts) | ❌ No | no Prometheus/OTel collector/dashboards yet (SPEC_sre §2 — post-pilot) |
| Certified СКЗИ / ФСТЭК-attested crypto | ❌ No | TLS + app crypto are standard OpenSSL, **not** certified СКЗИ |
| Live-ИРБИС64 bridge | ⚙️ Optional | works if you point `IRBIS_*` at a running server; stack boots without it |

Legend: ✅ ready · ⚠️ partial / manual · ❌ not in this phase · ⚙️ optional.

---

## Go-live checklist

### 1. Secrets — set real values in `.env`
- [ ] `cp deploy/.env.example deploy/.env` (this file is gitignored — never commit it).
- [ ] Set a strong **`POSTGRES_PASSWORD`** (long random, not `devpassword`).
- [ ] Set a strong **`APP_SECRET`** — `openssl rand -hex 32` (signs sessions/JWT).
- [ ] If using the live-ИРБИС bridge, set **`IRBIS_PASS`** (service-account password).
- [ ] Confirm no `CHANGE IN PROD` placeholder values remain in `deploy/.env`.
- [ ] For a real deployment, source secrets from a manager (Vault/SOPS), not a
      plaintext file left on disk. (Pilot: a locked-down `.env` with `chmod 600`
      on a single trusted host is acceptable; document who has access.)

### 2. TLS — real certificate, not self-signed
- [ ] **Dev/self-signed (default):** `sh deploy/proxy/gen-cert.sh` writes
      `deploy/proxy/certs/{server.crt,server.key}` (gitignored). Browsers warn —
      expected for dev only. (This script is cross-platform: Linux/macOS **and**
      Windows git-bash — see the header note about MSYS path-mangling.)
- [ ] **Pilot:** replace those two files with a certificate from your CA
      (internal CA / certbot / Let's Encrypt). The nginx `:80` server already
      exposes the ACME `http-01` webroot (`/.well-known/acme-challenge/`).
- [ ] Once a **real** cert is in place, enable **HSTS** — uncomment the
      `Strict-Transport-Security` header in `deploy/proxy/nginx.conf`. Do **not**
      enable HSTS with a self-signed cert.
- [ ] Confirm `ssl_protocols TLSv1.2 TLSv1.3` only (already set in `nginx.conf`).
- [ ] ⚠️ **Honest limit:** this is standard OpenSSL TLS, **not** a certified
      СКЗИ / ГОСТ-TLS. If the pilot site requires attested crypto, that is a
      separate gov-segment task ([`SPEC_sre.md` §3.6](specs/platform/SPEC_sre.md),
      I6/§E) and is **out of scope for this pilot**.

### 3. First tenant — provision via CLI
The Access store is multi-tenant (control schema + per-tenant schema `t_<slug>`).
After the stack is up:
- [ ] Provision the pilot library:
      ```sh
      docker compose -f deploy/docker-compose.yml exec backend \
        python -m access.provision <slug> --name "Имя библиотеки" \
        --admin admin --password '<strong-admin-password>' --plan standard
      ```
- [ ] List tenants to confirm: `… exec backend python -m access.provision --list`.
- [ ] Change the admin password from any default; `ADMIN_DEFAULT_PASSWORD`/
      `changeme` must **not** survive into the pilot.
- [ ] (Teardown a mistaken tenant: `… python -m access.provision --deprovision <slug>`.)

### 4. Data migration — via the migrator
- [ ] Bibliographic / catalog data: import from the existing ИРБИС64 fund using
      the project's migration path (bulk IBIS import — a **throughput/freshness**
      job, not a latency-SLO path; [`SPEC_sre.md` §1.5](specs/platform/SPEC_sre.md)).
- [ ] Run a **dry-run on a staging tenant first**; verify record counts and a
      sample of records before importing into the pilot tenant.
- [ ] Take a backup (step 5) **immediately before** the migration so you can roll
      back the data load if it goes wrong.

### 5. Backups — schedule + tested restore
- [ ] Backups land in the `backups` named volume via
      [`deploy/backup/pg_backup.sh`](../../deploy/backup/pg_backup.sh)
      (`pg_dump`, timestamped, custom format).
- [ ] **Schedule a nightly dump** (single-node pilot baseline,
      [`SPEC_sre.md` §3.2](specs/platform/SPEC_sre.md)):
      - Linux/macOS cron (02:30, keep 14 days):
        ```
        30 2 * * *  KEEP=14 /path/to/repo/deploy/backup/pg_backup.sh >> /var/log/biblio-backup.log 2>&1
        ```
      - Windows Task Scheduler (git-bash):
        ```
        schtasks /Create /SC DAILY /ST 02:30 /TN "biblio-pg-backup" \
          /TR "\"C:\Program Files\Git\bin\sh.exe\" C:\IRBIS64\_recon\deploy\backup\pg_backup.sh"
        ```
- [ ] **3-2-1 (SPEC_sre §3.2):** copy the `backups` volume off-box to a second
      location (and ideally one offline/immutable copy). Inspect/export:
      ```sh
      docker compose -f deploy/docker-compose.yml exec db ls -lh /backups
      docker run --rm -v deploy_backups:/b -v "$PWD":/out alpine cp -r /b /out/backups-copy
      ```
- [ ] **TEST the restore — a backup is only trustworthy once restored**
      ([`SPEC_sre.md` §3.4](specs/platform/SPEC_sre.md): "бэкап рабочий только
      после restore"). Rehearse into a throwaway DB without touching live data:
      ```sh
      FORCE=1 RESTORE_DB=irbis_restore_test \
        sh deploy/backup/pg_restore.sh <dump-file>
      docker compose -f deploy/docker-compose.yml exec db \
        psql -U postgres -d irbis_restore_test -c "\dn"   # schemas present?
      docker compose -f deploy/docker-compose.yml exec db \
        dropdb -U postgres irbis_restore_test             # clean up
      ```
- [ ] Do this restore-test **before go-live** and then **monthly** (record the
      run; SPEC_sre §3.4 per-tenant/monthly cadence).
- [ ] ⚠️ **Honest limit:** this is a **nightly logical dump only**. There is **no
      continuous WAL archiving / PITR** in the single-node pilot, so worst-case
      data loss (RPO) is up to ~24h (whatever changed since the last nightly
      dump). State this RPO in the pilot SLA. PITR + replicas come with the
      multi-node IaC phase (D3 / SPEC_sre §3.1–§3.2).

### 6. Monitoring & log access
- [ ] Container health is visible: `docker compose -f deploy/docker-compose.yml ps`
      shows `db`, `backend`, `proxy` as **healthy** (healthchecks added — §below).
- [ ] Logs: `docker compose -f deploy/docker-compose.yml logs -f <service>`.
      Decide who has shell access to the host and how logs are retained.
- [ ] Set Docker log rotation on the host (e.g. `max-size`/`max-file` in the
      daemon config or a `logging:` block) so logs don't fill the disk over a pilot.
- [ ] ⚠️ **Honest limit:** there is **no metrics/traces/alerting stack** in this
      phase — no Prometheus/OTel collector, no SLO dashboards, no burn-rate
      alerts (all defined in [`SPEC_sre.md` §2](specs/platform/SPEC_sre.md) for a
      later phase). Pilot monitoring is **manual** (`ps`/`logs` + the synthetic
      check below). Assign a person to eyeball it daily during the pilot.
- [ ] Minimal external check: a cron/uptime probe hitting `https://<host>/api/health`
      (returns 200 with an `ok` envelope; never 500, even when ИРБИС is down).

### 7. Rollback plan
- [ ] **App/config rollback:** the app is rebuilt from this repo. To roll back a
      bad deploy, check out the previous good commit and
      `docker compose up -d --build`. Pin the deployed git SHA somewhere visible.
- [ ] **Data rollback:** restore the most recent good dump into the live DB
      (step 5; the custom-format restore runs `pg_restore --clean --if-exists`).
      Always take a fresh backup *before* a risky change so you have a recovery point.
- [ ] **Image/base rollback:** `db` is `postgres:16`, `proxy` is `nginx:1.27-alpine`.
      Avoid surprise upgrades on the maintenance window: prefer
      `docker compose pull && docker compose up -d` only in an announced window;
      keep volumes (do **not** use `down -v`).
- [ ] **Stack down/up without data loss:** `docker compose down` keeps volumes
      (`pgdata`, `backups`, `backend-data`); `docker compose down -v` **wipes**
      them — never run `-v` against a pilot.
- [ ] Keep this checklist + the DR steps **off the box too** (a copy outside the
      restored system) — SPEC_sre §3.3 ("runbook вне восстанавливаемой системы").

### 8. Network & exposure
- [ ] Only the `proxy` publishes host ports (`80`/`443`). Keep the `db` and
      `backend` host-port mappings **commented out** (the default) — they talk
      over the compose network only.
- [ ] Put the host behind the site firewall; expose only 80/443 externally
      (80 only for the ACME challenge + redirect to 443).
- [ ] Confirm reader PII stays out of operational logs (152-ФЗ; SPEC_sre §2.5).

---

## Healthchecks (added in this hardening pass)

`docker compose ps` reports each service's health, and orchestration waits on
dependencies (`proxy` starts only once `backend` is healthy; `backend` only once
`db` is healthy):

| Service | Probe | Why this form |
|---|---|---|
| `db` | `pg_isready -U … -d …` | already present (`postgres:16`) |
| `backend` | `python -c "urllib.request.urlopen('http://127.0.0.1:8080/api/health')"` | the `python:3.12-slim` image has **no curl/wget** — probe with the app's own interpreter (stdlib, no image bloat); `/api/health` is unauthenticated and returns 200 even when ИРБИС is down |
| `proxy` | `curl -fsk https://localhost/` | `nginx:alpine` ships curl; `-k` because the dev cert is self-signed — we assert TLS terminates + the proxy answers, not cert validity |

Verify after `up`:
```sh
docker compose -f deploy/docker-compose.yml ps        # all three → "healthy"
```

---

## Known limits for the pilot (be explicit with the customer)

1. **Single node = no HA.** One host; if it dies, the service is down until it is
   restored from backup (RTO minutes-to-hours). No automatic PG failover, no
   replicas, no multi-AZ. (Comes with the D3 IaC phase.)
2. **RPO ≈ up to 24h.** Nightly logical dump only; no continuous WAL/PITR yet.
   Worst case you lose changes since the last nightly backup. State in SLA.
3. **No certified СКЗИ / ФСТЭК-attested crypto.** TLS and app crypto use standard
   OpenSSL. A gov-segment / attested-contour deployment is a separate effort
   (SPEC_sre §3.6, I6/§E) and is **not** part of this pilot.
4. **No metrics/traces/alerting stack.** Monitoring is manual (`ps`/`logs` +
   `/api/health`). SLO dashboards + burn-rate alerts (SPEC_sre §2) are post-pilot.
5. **Live-ИРБИС64 bridge is optional.** OPAC features that need the native ИРБИС
   server require `IRBIS_*` pointing at a running server (on Docker Desktop, use
   `host.docker.internal`). Without it, the stack still boots; ИРБИС-dependent
   features are unavailable.
6. **Self-signed cert by default.** A real cert must be installed before go-live
   (step 2); otherwise every browser warns and HSTS cannot be enabled.

---

## References
- [`deploy/README.md`](../../deploy/README.md) — stack topology, env model, prod hardening checklist.
- [`SPEC_sre.md`](specs/platform/SPEC_sre.md) (D4) — SLO/SLI, RPO/RTO, backup policy, restore-rehearsal cadence, graceful degradation, runbooks.
- [`SPEC_iac_fleet.md`](specs/platform/SPEC_iac_fleet.md) (D3) — multi-node / multi-region IaC: replication, geo-backups, failover (the post-pilot phase).
