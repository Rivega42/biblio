-- Acquisition (комплектование) — PostgreSQL DDL mirror of acquisition.py's
-- inline sqlite schema (ADR-004: sqlite dev / Postgres prod). Gap E1, epic #188.
--
-- This is the prod-parity schema for the acquisition lifecycle store (order →
-- receipt → КСУ → inventory). The dev store (access/acquisition.py
-- AcquisitionStore) creates the equivalent tables in sqlite on init; this file is
-- the Postgres counterpart, kept in sync with that module. NEW file — does not
-- touch schema_postgres.sql (owned by a concurrent sibling).
--
-- The ToCat seam (bib record + 910 exemplars) is NOT modelled here: ToCat writes
-- into the CATALOG store (access/catalog.py), not into acquisition's own tables.
-- Acquisition only persists order / receipt / КСУ / inventory state and carries a
-- pointer (acq_receipt.catalog_mfn) to the bib record ToCat created/updated.

-- Order line (заказ) — DB_ACQUISITION поле 62 «суммарный заказ», статус StatusZ.mnu.
CREATE TABLE IF NOT EXISTS acq_order (
  id              BIGSERIAL PRIMARY KEY,
  title           TEXT NOT NULL,
  author          TEXT,
  supplier        TEXT,                          -- организация-посредник (IZD)
  copies_ordered  INTEGER NOT NULL DEFAULT 0,
  copies_received INTEGER NOT NULL DEFAULT 0,
  price           DOUBLE PRECISION,              -- unit price (62^p plan)
  funding_source  TEXT,                          -- источник финанс. (88^L Istfin.mnu)
  status          TEXT NOT NULL DEFAULT 'ordered'
                    CHECK (status IN ('ordered','partially_received','received','cancelled')),
  created         DOUBLE PRECISION NOT NULL,
  updated         DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS acq_order_status_idx ON acq_order(status);

-- КСУ (Книга суммарного учёта) — the summary book of accounting per batch.
-- 88^A год+№ (the KSU= key) · 88^E наименований · 88^F экземпляров · 88^G сумма.
CREATE TABLE IF NOT EXISTS acq_ksu (
  id         BIGSERIAL PRIMARY KEY,
  ksu_no     TEXT NOT NULL UNIQUE,               -- 88^A (год+№)
  titles     INTEGER NOT NULL DEFAULT 0,         -- 88^E наименований
  copies     INTEGER NOT NULL DEFAULT 0,         -- 88^F экземпляров
  total_sum  DOUBLE PRECISION NOT NULL DEFAULT 0,-- 88^G сумма
  act_ref    TEXT,                               -- акт/счёт (88^B / 88^J invoice)
  created    DOUBLE PRECISION NOT NULL
);

-- Receipt (поступление) — one registration of received copies against an order.
CREATE TABLE IF NOT EXISTS acq_receipt (
  id          BIGSERIAL PRIMARY KEY,
  order_id    BIGINT NOT NULL REFERENCES acq_order(id),
  ksu_id      BIGINT NOT NULL REFERENCES acq_ksu(id),
  copies      INTEGER NOT NULL,
  unit_price  DOUBLE PRECISION,
  sum         DOUBLE PRECISION NOT NULL DEFAULT 0,
  catalog_mfn BIGINT,                            -- the ToCat bib record (NULL if standalone)
  created     DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS acq_receipt_order_idx ON acq_receipt(order_id);

-- Inventory ledger — one row per received copy (910^b inv# ↔ 910^U КСУ link).
CREATE TABLE IF NOT EXISTS acq_inventory (
  id         BIGSERIAL PRIMARY KEY,
  receipt_id BIGINT NOT NULL REFERENCES acq_receipt(id),
  ksu_no     TEXT NOT NULL,                      -- 910^U back-link to КСУ
  inv_no     TEXT NOT NULL UNIQUE,               -- 910^b inventory number
  CONSTRAINT acq_inventory_inv_uniq UNIQUE (inv_no)
);
CREATE INDEX IF NOT EXISTS acq_inventory_receipt_idx ON acq_inventory(receipt_id);
