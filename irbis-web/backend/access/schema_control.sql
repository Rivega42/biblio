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
