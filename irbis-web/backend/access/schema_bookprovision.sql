-- Book-provision (книгообеспеченность, ВУЗ) — PostgreSQL DDL.
--
-- Cluster 4 of docs/design/INTEGRATION_MAP.md, BD VUZ (DB_VUZ.md), business
-- rules E1 (SPEC_business_acquisition.md §2). PG parity of the own sqlite store
-- in access/bookprovision.py — the curriculum «связка»
-- Факультет→Направление→Специальность→Дисциплина + recommended-literature
-- bindings (field 691, kind 691^G осн/доп) used for the Кко computation.
--
-- Multi-tenant: every table is tenant-scoped (tenant_id) for schema/row
-- isolation, mirroring the rest of the backend. This file is NEW and standalone
-- (it does NOT modify schema_postgres.sql). Apply within the tenant schema.

CREATE TABLE IF NOT EXISTS bp_faculty (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id   TEXT NOT NULL,
  code        TEXT NOT NULL,                     -- связка ^A (факультет root)
  name        TEXT NOT NULL DEFAULT '',
  UNIQUE (tenant_id, code)
);

CREATE TABLE IF NOT EXISTS bp_specialty (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id   TEXT NOT NULL,
  faculty_id  BIGINT NOT NULL REFERENCES bp_faculty(id) ON DELETE CASCADE,
  napr        TEXT NOT NULL DEFAULT '',   -- 68/83 ^N направление
  spec        TEXT NOT NULL DEFAULT '',   -- 68/83 ^C специальность/профиль
  vid         TEXT NOT NULL DEFAULT '',   -- 68/83 ^V вид обучения (уровень)
  form        TEXT NOT NULL DEFAULT '',   -- 68/83 ^O форма обучения
  fili        TEXT NOT NULL DEFAULT '',   -- 68/83 ^L филиал (для связки 691)
  name        TEXT NOT NULL DEFAULT '',
  UNIQUE (tenant_id, faculty_id, napr, spec, vid, form, fili)
);

CREATE TABLE IF NOT EXISTS bp_discipline (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id       TEXT NOT NULL,
  specialty_id    BIGINT NOT NULL REFERENCES bp_specialty(id) ON DELETE CASCADE,
  disc_id         TEXT NOT NULL,                 -- field 3^0 идентификатор
  name            TEXT NOT NULL DEFAULT '',       -- field 3^a наименование
  semester        TEXT NOT NULL DEFAULT '',       -- 83/68 ^F семестр(ы)
  students        INTEGER NOT NULL DEFAULT 0,     -- contingent (RDR or 68^Z)
  students_source TEXT NOT NULL DEFAULT '68z'
                  CHECK (students_source IN ('rdr','68z')),  -- audit (SPEC E1 §2.3)
  UNIQUE (tenant_id, specialty_id, disc_id, semester)
);
CREATE INDEX IF NOT EXISTS bp_discipline_spec_idx
  ON bp_discipline (tenant_id, specialty_id);

CREATE TABLE IF NOT EXISTS bp_binding (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id     TEXT NOT NULL,
  discipline_id BIGINT NOT NULL REFERENCES bp_discipline(id) ON DELETE CASCADE,
  title         TEXT NOT NULL DEFAULT '',         -- bound literature label
  kind          TEXT NOT NULL DEFAULT 'main'
                CHECK (kind IN ('main','extra')),  -- field 691^G осн/доп
  catalog_db    TEXT,                              -- catalog db for live 910 read
  inv_key       TEXT,                              -- 910^b inventory key
  copies        INTEGER NOT NULL DEFAULT 0,        -- standalone exemplar count
  created       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bp_binding_disc_idx
  ON bp_binding (tenant_id, discipline_id);
