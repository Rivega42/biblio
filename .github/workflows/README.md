# CI/CD — GitHub Actions

Automated verification gates for `irbis-web`. Defined in [`ci.yml`](ci.yml);
tracks issue **#118** (initiative **I1**). Runs on every **push** and **pull
request** to `main`. A run must be green for the change to be considered verified.

## What the pipeline gates

| Job | Runner | What it checks | Pass criterion |
|---|---|---|---|
| **backend-tests** | ubuntu, Python 3.12 | Access suite (`irbis-web/backend/tests/test_access.py`) run **twice** — once on the **sqlite** backend (default) and once on **PostgreSQL** (`postgres:16` service container, db `irbis_access`, `ACCESS_BACKEND=postgres`). This is the durable PG↔sqlite parity gate (issue #92) since the local Windows box can't always run PostgreSQL. | Suite exits 0 on **both** backends (it exits non-zero on any failed check). |
| **contract-lint** | ubuntu, Node 20 | `npx @redocly/cli lint docs/build/openapi.yaml` — the OpenAPI contract is well-formed. | 0 lint errors. |
| **frontend-build** | ubuntu, Node 20 | `npm ci` + `npm run build` (Vite) for `irbis-web/frontend`. Fonts are self-hosted under `public/design/fonts/`, so the build needs no network. A non-blocking `tsc --noEmit` type-check also runs. | Production build succeeds. (Type-check is `continue-on-error` — it reports known type-only warnings but does not fail the gate.) |

## How the PostgreSQL parity gate works

`backend-tests` starts a `postgres:16` **service container** with a health check
and `POSTGRES_DB=irbis_access`. The second test run sets:

```
ACCESS_BACKEND=postgres
ACCESS_PG_DSN=postgresql://postgres:postgres@127.0.0.1:5432/irbis_access
```

`PgAccessStore.ensure_schema()` creates the Access tables on connect (DDL from
`access/schema_postgres.sql`), so no separate migration step is needed. When
`ACCESS_BACKEND` is unset the same suite runs against an in-memory sqlite store.

## Dependencies

CI installs backend test deps from
[`irbis-web/backend/requirements-dev.txt`](../../irbis-web/backend/requirements-dev.txt)
(`psycopg[binary]`, `pytest`). The sqlite path needs none of these — psycopg is
imported lazily, so the suite runs on the Python standard library alone.

## Pinned versions

`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`.

## Running the gates locally

```sh
# Access suite (sqlite — no DB needed)
python irbis-web/backend/tests/test_access.py

# OpenAPI lint
npx --yes @redocly/cli@latest lint docs/build/openapi.yaml

# Frontend build
npm --prefix irbis-web/frontend ci
npm --prefix irbis-web/frontend run build
```

The PostgreSQL run requires a reachable PG at `ACCESS_PG_DSN`; on developer
machines without one it is the CI's job. Locally the suite skips the postgres
backend cleanly when PG/psycopg is unavailable.
