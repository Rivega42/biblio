-- Production schema (PostgreSQL) for the access suite. Dev uses the sqlite mirror
-- in store.py (ADR-004). Readers live in RDR (not here); only staff + grants + audit.

CREATE TABLE IF NOT EXISTS staff_account (
  id          BIGSERIAL PRIMARY KEY,
  login       TEXT UNIQUE NOT NULL,
  pass_hash   TEXT NOT NULL,
  full_name   TEXT,
  is_active   BOOLEAN NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- grant = function x base x level
-- function: 'search'|'record.read'|'record.write'|'record.delete'|'terms'|'file'|
--           'order'|'cabinet'|'circ.issue'|'circ.return'|'cat.gbl'|'acq.receipt'|
--           'admin.db'|'admin.users'|...
-- db: database name or '*' (all)
-- level: 'read'|'write'|'admin'
CREATE TABLE IF NOT EXISTS grant_entry (
  id          BIGSERIAL PRIMARY KEY,
  account_id  BIGINT NOT NULL REFERENCES staff_account(id) ON DELETE CASCADE,
  function    TEXT NOT NULL,
  db          TEXT NOT NULL,
  level       TEXT NOT NULL CHECK (level IN ('read','write','admin')),
  UNIQUE(account_id, function, db)
);

CREATE TABLE IF NOT EXISTS role (
  id   BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS role_grant (
  role_id  BIGINT NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  function TEXT NOT NULL, db TEXT NOT NULL, level TEXT NOT NULL,
  UNIQUE(role_id, function, db)
);
CREATE TABLE IF NOT EXISTS account_role (
  account_id BIGINT NOT NULL REFERENCES staff_account(id) ON DELETE CASCADE,
  role_id    BIGINT NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  PRIMARY KEY(account_id, role_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
  id        BIGSERIAL PRIMARY KEY,
  ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor     TEXT NOT NULL,            -- staff login or reader ticket
  function  TEXT NOT NULL, db TEXT, mfn INTEGER,
  result    TEXT NOT NULL,            -- ok | denied | error
  detail    JSONB
);
CREATE INDEX IF NOT EXISTS audit_log_ts_idx ON audit_log(ts DESC);

-- Effective rights of an account = union(grant_entry, role_grant via account_role).

-- ---------------------------------------------------------------------------
-- Per-tenant vocabularies + classification trees (seeding engine, gap A5 #188).
-- Live in the tenant schema t_<slug> alongside Access, so isolation is the same
-- schema-per-tenant mechanism (no tenant_id column needed). Populated at
-- provisioning by seed_vocabularies() from control.seed_catalog. Idempotent DDL.
-- ---------------------------------------------------------------------------

-- One row per dictionary (MNU). kind: 'system' (vendor-standard, seeded with
-- values) | 'institution' (library-specific, seeded EMPTY). seed_version stamps
-- which system seed epoch populated it (NULL for empty institution vocabs).
CREATE TABLE IF NOT EXISTS vocabulary (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT UNIQUE NOT NULL,        -- 'vd.mnu','ste.mnu','kv.mnu'…
  title         TEXT NOT NULL,               -- human-readable
  kind          TEXT NOT NULL CHECK (kind IN ('system','institution')),
  field_hint    TEXT,                        -- bound field/subfield: '900^c','910^A'
  seed_version  INTEGER,                     -- system seed epoch, NULL for empty institution
  is_overridden BOOLEAN NOT NULL DEFAULT false,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- code -> label pairs of one dictionary, ordered. origin tracks seed vs custom
-- so a future reseed never clobbers a library's edits; is_active is soft-delete.
CREATE TABLE IF NOT EXISTS vocabulary_value (
  id            BIGSERIAL PRIMARY KEY,
  vocab         TEXT NOT NULL REFERENCES vocabulary(name) ON DELETE CASCADE,
  code          TEXT NOT NULL,               -- case-sensitive ИРБИС code
  label         TEXT NOT NULL,
  sort          INTEGER NOT NULL DEFAULT 0,
  origin        TEXT NOT NULL DEFAULT 'seed' CHECK (origin IN ('seed','imported','custom')),
  active        BOOLEAN NOT NULL DEFAULT true,
  UNIQUE (vocab, code)
);
CREATE INDEX IF NOT EXISTS vocabulary_value_vocab_idx ON vocabulary_value(vocab, sort);

-- Classification tree nodes (TRE). parent is a self-reference by (name, code);
-- path is a dotted materialized path of codes for subtree queries.
CREATE TABLE IF NOT EXISTS classification_node (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,               -- tree name: 'spec.tre','cikod.tre'
  code          TEXT NOT NULL,
  label         TEXT NOT NULL,
  parent        TEXT,                        -- parent node code within the same tree
  depth         INTEGER NOT NULL DEFAULT 0,
  path          TEXT,                        -- materialized 'a.b.c' path of codes
  sort          INTEGER NOT NULL DEFAULT 0,
  origin        TEXT NOT NULL DEFAULT 'seed',
  UNIQUE (name, code)
);
CREATE INDEX IF NOT EXISTS classification_node_tree_idx ON classification_node(name, parent);

-- ---------------------------------------------------------------------------
-- Reader-portal state (#222): holds + queue and reading-list shelves.
-- Persisted in OUR store (NOT written to the live ИРБИС server), reader-scoped by
-- RDR ticket (RI=). Readers are NOT in staff_account, so these tables key on the
-- ticket string, not an account id. Mirrors the sqlite DDL in store.py.
-- ---------------------------------------------------------------------------

-- One placed hold. status: queued (in line) | ready (free copy on the pickup
-- shelf) | cancelled. position is computed live from the FIFO queue, not stored.
CREATE TABLE IF NOT EXISTS reader_hold (
  id         BIGSERIAL PRIMARY KEY,
  ticket     TEXT NOT NULL,                -- RDR ticket (RI=) that owns the hold
  db         TEXT NOT NULL,
  mfn        INTEGER NOT NULL,
  title      TEXT,                         -- resolved at place time (brief read)
  status     TEXT NOT NULL DEFAULT 'queued'
             CHECK (status IN ('queued','ready','cancelled')),
  queued_at  DOUBLE PRECISION NOT NULL,
  until      DOUBLE PRECISION,             -- pickup-shelf TTL once ready
  UNIQUE(ticket, db, mfn, status)          -- at most one live hold per reader per item
);
CREATE INDEX IF NOT EXISTS reader_hold_queue_idx ON reader_hold(db, mfn, status, queued_at);
CREATE INDEX IF NOT EXISTS reader_hold_ticket_idx ON reader_hold(ticket, status);

-- Reading lists. Two system lists ('want','fav') seeded lazily per reader; the
-- reader may add custom lists ('s<n>'). Dedup of items is per (ticket,list,db,mfn).
CREATE TABLE IF NOT EXISTS reader_shelf (
  id         TEXT NOT NULL,                -- 'want' | 'fav' (system) | custom 's<n>'
  ticket     TEXT NOT NULL,
  name       TEXT NOT NULL,
  system     BOOLEAN NOT NULL DEFAULT false,
  created_at DOUBLE PRECISION NOT NULL DEFAULT extract(epoch from now()),
  PRIMARY KEY (ticket, id)
);
CREATE TABLE IF NOT EXISTS reader_shelf_item (
  ticket    TEXT NOT NULL,
  list_id   TEXT NOT NULL,
  db        TEXT NOT NULL,
  mfn       INTEGER NOT NULL,
  title     TEXT,
  added_at  DOUBLE PRECISION NOT NULL DEFAULT extract(epoch from now()),
  PRIMARY KEY (ticket, list_id, db, mfn)
);
CREATE INDEX IF NOT EXISTS reader_shelf_item_list_idx ON reader_shelf_item(ticket, list_id);
