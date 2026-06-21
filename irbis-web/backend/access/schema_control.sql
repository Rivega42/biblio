-- Control schema (PostgreSQL) for multi-tenancy (issue #100, initiative I1).
--
-- The `control` schema is the cross-tenant catalog: one row per tenant. Each
-- tenant's Access data (staff_account / grant_entry / role / audit_log, the DDL
-- in schema_postgres.sql) lives in its OWN schema `t_<slug>`, fully isolated.
-- A connection picks a tenant by `SET search_path = t_<slug>, public` (see
-- TenantAccessStore in pgstore.py). See ARCHITECTURE §4 (схема-на-тенанта).
--
-- All DDL here is idempotent so provisioning/ensure can run repeatedly.

CREATE SCHEMA IF NOT EXISTS control;

-- kind: публичная | школьная | вузовская | ведомственная (library type;
-- drives the module preset / defaults later — see SPEC_I1 #103). Stored as TEXT
-- (not an enum) so adding a kind needs no migration.
CREATE TABLE IF NOT EXISTS control.tenant (
  id          BIGSERIAL PRIMARY KEY,
  slug        TEXT UNIQUE NOT NULL,      -- url/schema-safe key; schema is t_<slug>
  name        TEXT NOT NULL,             -- human-readable library name
  kind        TEXT NOT NULL,             -- публичная|школьная|вузовская|ведомственная
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Licensing / entitlements (issue #101): which functional MODULES a tenant is
-- licensed for. SEPARATE axis from grants — grants are "can-do" (per account),
-- entitlements are "is-licensed" (per tenant). A request to a disabled module is
-- refused (403/404) even with a valid grant. Billing (I7) consumes this table;
-- it is kept independent of billing here. Default-enabled rows are seeded at
-- provisioning (see access/entitlements.py); an operator flips `enabled` to
-- revoke a module. `module` is TEXT (not an enum) so adding a module needs no
-- migration.
CREATE TABLE IF NOT EXISTS control.tenant_module (
  tenant_id  BIGINT NOT NULL REFERENCES control.tenant(id) ON DELETE CASCADE,
  module     TEXT NOT NULL,             -- opac|cataloging|circulation|acquisition|reader|admin|analytics|...
  enabled    BOOLEAN NOT NULL DEFAULT true,
  PRIMARY KEY(tenant_id, module)
);

-- Seeding engine master catalog (gap A5, issue #188). The single source of truth
-- for "what values to seed into every tenant": the vendor-standard (system) ИРБИС
-- control dictionaries. One row per (vocab, code). seed_vocabularies() copies these
-- into a tenant's schema at provisioning. Institution dictionaries are NOT here —
-- they are created EMPTY in the tenant schema (filled by the library). Versioned by
-- `seed_version` so a future reseed can three-way-merge (SPEC §3.3). Idempotent DDL.
CREATE TABLE IF NOT EXISTS control.seed_catalog (
  vocab         TEXT NOT NULL,             -- 'vd.mnu','ste.mnu'…
  code          TEXT NOT NULL,             -- case-sensitive ИРБИС code
  label         TEXT NOT NULL,
  kind          TEXT NOT NULL,             -- always 'system' here (institution = empty seed)
  seed_version  INTEGER NOT NULL,
  title         TEXT NOT NULL,             -- vocab title (denormalized, same for all rows of a vocab)
  field_hint    TEXT,
  sort          INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (vocab, code)
);
