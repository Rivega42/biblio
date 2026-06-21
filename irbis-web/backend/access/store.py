#!/usr/bin/env python3
"""Access store — sqlite3 for dev (runs with no DB server); schema mirrors the
PostgreSQL DDL in schema_postgres.sql (ADR-004: sqlite dev / Postgres prod).

Holds staff accounts, grants, roles and the audit log. Readers are NOT stored
here (they authenticate against RDR); only staff + their grants live in this store.
"""
import os
import sqlite3
import hashlib
import hmac
import json
import threading
import time

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS staff_account (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  login TEXT UNIQUE NOT NULL,
  pass_hash TEXT NOT NULL,
  full_name TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS grant_entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES staff_account(id) ON DELETE CASCADE,
  function TEXT NOT NULL,
  db TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('read','write','admin')),
  UNIQUE(account_id, function, db)
);
CREATE TABLE IF NOT EXISTS role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS role_grant (
  role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  function TEXT NOT NULL, db TEXT NOT NULL, level TEXT NOT NULL,
  UNIQUE(role_id, function, db)
);
CREATE TABLE IF NOT EXISTS account_role (
  account_id INTEGER NOT NULL REFERENCES staff_account(id) ON DELETE CASCADE,
  role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  PRIMARY KEY(account_id, role_id)
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  actor TEXT NOT NULL,
  function TEXT NOT NULL, db TEXT, mfn INTEGER,
  result TEXT NOT NULL, detail TEXT
);
-- Per-tenant vocabularies + classification trees (seeding engine, gap A5 #188).
-- Mirrors schema_postgres.sql. On sqlite dev there is one (single-tenant 'public')
-- store, so these tables hold that tenant's seeded dictionaries.
CREATE TABLE IF NOT EXISTS vocabulary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('system','institution')),
  field_hint TEXT,
  seed_version INTEGER,
  is_overridden INTEGER NOT NULL DEFAULT 0,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS vocabulary_value (
  vocab TEXT NOT NULL REFERENCES vocabulary(name) ON DELETE CASCADE,
  code TEXT NOT NULL,
  label TEXT NOT NULL,
  sort INTEGER NOT NULL DEFAULT 0,
  origin TEXT NOT NULL DEFAULT 'seed' CHECK (origin IN ('seed','imported','custom')),
  active INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (vocab, code)
);
CREATE INDEX IF NOT EXISTS vocabulary_value_vocab_idx ON vocabulary_value(vocab, sort);
CREATE TABLE IF NOT EXISTS classification_node (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  code TEXT NOT NULL,
  label TEXT NOT NULL,
  parent TEXT,
  depth INTEGER NOT NULL DEFAULT 0,
  path TEXT,
  sort INTEGER NOT NULL DEFAULT 0,
  origin TEXT NOT NULL DEFAULT 'seed',
  UNIQUE (name, code)
);
CREATE INDEX IF NOT EXISTS classification_node_tree_idx ON classification_node(name, parent);
"""


class AccessStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ---- password hashing (pbkdf2-sha256, stdlib) ----
    @staticmethod
    def hash_password(pw, iterations=200000):
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, iterations)
        return 'pbkdf2$%d$%s$%s' % (iterations, salt.hex(), dk.hex())

    @staticmethod
    def verify_password(pw, stored):
        try:
            _algo, it, salt_hex, hash_hex = stored.split('$')
            dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'),
                                     bytes.fromhex(salt_hex), int(it))
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False

    # ---- accounts ----
    def create_account(self, login, password, full_name=''):
        c = self._conn()
        c.execute('INSERT OR IGNORE INTO staff_account(login,pass_hash,full_name) VALUES(?,?,?)',
                  (login, self.hash_password(password), full_name))
        c.commit()
        return self.get_account(login)

    def get_account(self, login):
        r = self._conn().execute('SELECT * FROM staff_account WHERE login=?', (login,)).fetchone()
        return dict(r) if r else None

    def authenticate(self, login, password):
        a = self.get_account(login)
        if a and a['is_active'] and self.verify_password(password, a['pass_hash']):
            return a
        return None

    # ---- grants / roles ----
    def add_grant(self, account_id, function, db, level):
        c = self._conn()
        c.execute('INSERT OR REPLACE INTO grant_entry(account_id,function,db,level) VALUES(?,?,?,?)',
                  (account_id, function, db, level))
        c.commit()

    def add_role(self, name):
        c = self._conn()
        c.execute('INSERT OR IGNORE INTO role(name) VALUES(?)', (name,))
        c.commit()
        return c.execute('SELECT id FROM role WHERE name=?', (name,)).fetchone()['id']

    def add_role_grant(self, role_id, function, db, level):
        c = self._conn()
        c.execute('INSERT OR REPLACE INTO role_grant(role_id,function,db,level) VALUES(?,?,?,?)',
                  (role_id, function, db, level))
        c.commit()

    def assign_role(self, account_id, role_id):
        c = self._conn()
        c.execute('INSERT OR IGNORE INTO account_role(account_id,role_id) VALUES(?,?)',
                  (account_id, role_id))
        c.commit()

    def effective_grants(self, account_id):
        """Union of direct grants and grants from all assigned roles."""
        c = self._conn()
        grants = [dict(r) for r in c.execute(
            'SELECT function,db,level FROM grant_entry WHERE account_id=?', (account_id,)).fetchall()]
        grants += [dict(r) for r in c.execute(
            '''SELECT rg.function, rg.db, rg.level FROM role_grant rg
               JOIN account_role ar ON ar.role_id=rg.role_id
               WHERE ar.account_id=?''', (account_id,)).fetchall()]
        return grants

    # ---- audit ----
    def audit(self, actor, function, db, mfn, result, detail=None):
        c = self._conn()
        c.execute('INSERT INTO audit_log(ts,actor,function,db,mfn,result,detail) VALUES(?,?,?,?,?,?,?)',
                  (time.time(), actor, function, db, mfn, result,
                   json.dumps(detail or {}, ensure_ascii=False)))
        c.commit()

    def recent_audit(self, limit=50):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM audit_log ORDER BY id DESC LIMIT ?', (limit,)).fetchall()]

    # ---- vocabularies (seeding engine, gap A5 #188) ----
    def upsert_vocabulary(self, name, title, kind, field_hint, seed_version):
        """Insert/update a dictionary's metadata row (idempotent on name)."""
        c = self._conn()
        c.execute(
            'INSERT INTO vocabulary(name,title,kind,field_hint,seed_version) '
            'VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET '
            'title=excluded.title, kind=excluded.kind, field_hint=excluded.field_hint',
            (name, title, kind, field_hint, seed_version))
        c.commit()

    def upsert_vocabulary_value(self, vocab, code, label, sort, origin='seed'):
        """Insert/update one (code,label) of a dictionary (idempotent on vocab,code).

        Never downgrades origin: a value the library marked 'custom'/'imported' keeps
        that origin on a re-seed so reseed merge logic (SPEC §3.3) can protect it.
        """
        c = self._conn()
        c.execute(
            'INSERT INTO vocabulary_value(vocab,code,label,sort,origin) VALUES(?,?,?,?,?) '
            'ON CONFLICT(vocab,code) DO UPDATE SET label=excluded.label, sort=excluded.sort',
            (vocab, code, label, sort, origin))
        c.commit()

    def get_vocabulary(self, name):
        r = self._conn().execute('SELECT * FROM vocabulary WHERE name=?', (name,)).fetchone()
        return dict(r) if r else None

    def list_vocabularies(self):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM vocabulary ORDER BY name').fetchall()]

    def vocabulary_values(self, name, active_only=False):
        sql = ('SELECT code,label,sort,origin,active FROM vocabulary_value '
               'WHERE vocab=?' + (' AND active=1' if active_only else '') +
               ' ORDER BY sort, code')
        return [dict(r) for r in self._conn().execute(sql, (name,)).fetchall()]

    def upsert_classification_node(self, name, code, label, parent, depth, path, sort=0):
        c = self._conn()
        c.execute(
            'INSERT INTO classification_node(name,code,label,parent,depth,path,sort) '
            'VALUES(?,?,?,?,?,?,?) ON CONFLICT(name,code) DO UPDATE SET '
            'label=excluded.label, parent=excluded.parent, depth=excluded.depth, '
            'path=excluded.path, sort=excluded.sort',
            (name, code, label, parent, depth, path, sort))
        c.commit()

    def classification_nodes(self, name):
        return [dict(r) for r in self._conn().execute(
            'SELECT code,label,parent,depth,path,sort FROM classification_node '
            'WHERE name=? ORDER BY sort, code', (name,)).fetchall()]
