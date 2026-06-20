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
