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
