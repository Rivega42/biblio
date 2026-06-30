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

from . import crypto

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
-- Reader-portal state (#222) — holds + queue and reading-list shelves, persisted
-- in OUR store (NOT on the live ИРБИС server), reader-scoped by RDR ticket. Mirrors
-- schema_postgres.sql. A "reader" here is the ticket string (RI=) — readers are NOT
-- in staff_account, so these tables key on the ticket, not an account id.
CREATE TABLE IF NOT EXISTS reader_hold (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket TEXT NOT NULL,             -- RDR ticket (RI=) that owns the hold
  db TEXT NOT NULL,
  mfn INTEGER NOT NULL,
  title TEXT,                       -- resolved at place time (brief read), for the inbox card
  status TEXT NOT NULL DEFAULT 'queued'   -- queued | ready | cancelled
       CHECK (status IN ('queued','ready','cancelled')),
  queued_at REAL NOT NULL,
  until REAL,                       -- pickup-shelf TTL once ready
  UNIQUE(ticket, db, mfn, status)   -- at most one live hold per reader per item (status-scoped)
);
CREATE INDEX IF NOT EXISTS reader_hold_queue_idx ON reader_hold(db, mfn, status, queued_at);
CREATE INDEX IF NOT EXISTS reader_hold_ticket_idx ON reader_hold(ticket, status);
CREATE TABLE IF NOT EXISTS reader_shelf (
  id TEXT NOT NULL,                 -- 'want' | 'fav' (system) | custom 's<n>'
  ticket TEXT NOT NULL,
  name TEXT NOT NULL,
  system INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  PRIMARY KEY (ticket, id)
);
CREATE TABLE IF NOT EXISTS reader_shelf_item (
  ticket TEXT NOT NULL,
  list_id TEXT NOT NULL,
  db TEXT NOT NULL,
  mfn INTEGER NOT NULL,
  title TEXT,
  added_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  PRIMARY KEY (ticket, list_id, db, mfn)
);
CREATE INDEX IF NOT EXISTS reader_shelf_item_list_idx ON reader_shelf_item(ticket, list_id);
-- Reader-portal v2 social layer (#134 engagement / #133 discovery), reader-scoped
-- by RDR ticket, persisted in OUR store (NOT on the live ИРБИС server). Mirrors
-- schema_postgres.sql.
-- reader_review: one editable review per (ticket, db, mfn) — upsert on that key.
CREATE TABLE IF NOT EXISTS reader_review (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket TEXT NOT NULL,
  db TEXT NOT NULL,
  mfn INTEGER NOT NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  text TEXT,
  reader_name TEXT,
  ts REAL NOT NULL,
  UNIQUE(ticket, db, mfn)
);
CREATE INDEX IF NOT EXISTS reader_review_item_idx ON reader_review(db, mfn);
-- reader_history: every record-open, auto-logged. Dedup by (db,mfn) is done at
-- read time (latest ts wins); we append rows so the latest open updates ts.
CREATE TABLE IF NOT EXISTS reader_history (
  ticket TEXT NOT NULL,
  db TEXT NOT NULL,
  mfn INTEGER NOT NULL,
  title TEXT,
  ts REAL NOT NULL,
  PRIMARY KEY (ticket, db, mfn)
);
CREATE INDEX IF NOT EXISTS reader_history_ticket_idx ON reader_history(ticket, ts);
-- saved_search: a reader's stored query (name/db/prefix/query).
CREATE TABLE IF NOT EXISTS saved_search (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket TEXT NOT NULL,
  name TEXT NOT NULL,
  db TEXT,
  prefix TEXT,
  query TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS saved_search_ticket_idx ON saved_search(ticket, id);
-- Consent (152-ФЗ ст.6/9, audit finding V9 / R9) — append-only: a new state is a
-- NEW row, never an UPDATE, so withdraw + re-consent is HISTORY not overwrite
-- (SPEC_compliance_152fz §2.5). The effective consent for a reader is the latest
-- row by ts. Reader-scoped by RDR ticket (readers are not in staff_account).
CREATE TABLE IF NOT EXISTS reader_consent (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket TEXT NOT NULL,
  given INTEGER NOT NULL,            -- 1 granted | 0 withdrawn
  version INTEGER NOT NULL DEFAULT 1, -- privacy-policy version the consent is for
  ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reader_consent_ticket_idx ON reader_consent(ticket, ts DESC);
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

    # ---- admin: account/role administration (АРМ Администратор, #187) ----
    def get_account_by_id(self, account_id):
        r = self._conn().execute(
            'SELECT * FROM staff_account WHERE id=?', (account_id,)).fetchone()
        return dict(r) if r else None

    def list_accounts(self):
        """All staff accounts (id/login/full_name/is_active), login-ordered."""
        return [dict(r) for r in self._conn().execute(
            'SELECT id,login,full_name,is_active FROM staff_account '
            'ORDER BY login').fetchall()]

    def account_roles(self, account_id):
        """Role names assigned to an account (sorted)."""
        return [r['name'] for r in self._conn().execute(
            'SELECT ro.name FROM role ro JOIN account_role ar ON ar.role_id=ro.id '
            'WHERE ar.account_id=? ORDER BY ro.name', (account_id,)).fetchall()]

    def set_account_roles(self, account_id, role_names):
        """Replace an account's role set with ``role_names`` (creates missing roles).

        Idempotent and atomic: clears the account's account_role rows then assigns
        the requested roles, minting a role row for any unknown name (mirrors how
        ``add_role`` is used by the seed). Returns the resolved role-name list."""
        c = self._conn()
        c.execute('DELETE FROM account_role WHERE account_id=?', (account_id,))
        for name in role_names:
            rid = self.add_role(name)
            c.execute('INSERT OR IGNORE INTO account_role(account_id,role_id) VALUES(?,?)',
                      (account_id, rid))
        c.commit()
        return self.account_roles(account_id)

    def set_account_active(self, account_id, active):
        """Enable/disable an account; returns the new is_active (0/1)."""
        c = self._conn()
        c.execute('UPDATE staff_account SET is_active=? WHERE id=?',
                  (1 if active else 0, account_id))
        c.commit()
        a = self.get_account_by_id(account_id)
        return a['is_active'] if a else None

    def list_roles(self):
        """All roles with their grants: [{name, grants:[{function,db,level}]}]."""
        c = self._conn()
        out = []
        for ro in c.execute('SELECT id,name FROM role ORDER BY name').fetchall():
            grants = [dict(r) for r in c.execute(
                'SELECT function,db,level FROM role_grant WHERE role_id=? '
                'ORDER BY function, db', (ro['id'],)).fetchall()]
            out.append({'name': ro['name'], 'grants': grants})
        return out

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

    # ---- reader holds (#222) — reader-scoped by RDR ticket, NOT on live ИРБИС ----
    def hold_find_live(self, ticket, db, mfn):
        """The reader's current non-cancelled hold on (db,mfn), or None (idempotency)."""
        r = self._conn().execute(
            "SELECT * FROM reader_hold WHERE ticket=? AND db=? AND mfn=? "
            "AND status IN ('queued','ready') ORDER BY id LIMIT 1",
            (ticket, db, mfn)).fetchone()
        return dict(r) if r else None

    def hold_queue(self, db, mfn):
        """FIFO queue (queued+ready) for (db,mfn), oldest first — drives position."""
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM reader_hold WHERE db=? AND mfn=? "
            "AND status IN ('queued','ready') ORDER BY queued_at, id",
            (db, mfn)).fetchall()]

    def hold_add(self, ticket, db, mfn, title, status, queued_at, until=None):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO reader_hold(ticket,db,mfn,title,status,queued_at,until) '
            'VALUES(?,?,?,?,?,?,?)', (ticket, db, mfn, title, status, queued_at, until))
        c.commit()
        return self.hold_get(cur.lastrowid)

    def hold_get(self, hold_id):
        r = self._conn().execute(
            'SELECT * FROM reader_hold WHERE id=?', (hold_id,)).fetchone()
        return dict(r) if r else None

    def holds_for(self, ticket):
        """All live (queued/ready) holds owned by a reader, oldest first."""
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM reader_hold WHERE ticket=? AND status IN ('queued','ready') "
            'ORDER BY queued_at, id', (ticket,)).fetchall()]

    def hold_cancel(self, ticket, hold_id):
        """Cancel a reader's own hold; returns the row if it was theirs and live."""
        c = self._conn()
        row = c.execute(
            "SELECT * FROM reader_hold WHERE id=? AND ticket=? "
            "AND status IN ('queued','ready')", (hold_id, ticket)).fetchone()
        if not row:
            return None
        c.execute("UPDATE reader_hold SET status='cancelled' WHERE id=?", (hold_id,))
        c.commit()
        return dict(row)

    # ---- reader shelves / reading lists (#222) — reader-scoped by RDR ticket ----
    def shelf_lists(self, ticket):
        return [dict(r) for r in self._conn().execute(
            'SELECT id,name,system,created_at FROM reader_shelf WHERE ticket=? '
            'ORDER BY system DESC, created_at, id', (ticket,)).fetchall()]

    def shelf_get(self, ticket, list_id):
        r = self._conn().execute(
            'SELECT * FROM reader_shelf WHERE ticket=? AND id=?',
            (ticket, list_id)).fetchone()
        return dict(r) if r else None

    def shelf_create(self, ticket, list_id, name, system=0):
        c = self._conn()
        c.execute('INSERT OR IGNORE INTO reader_shelf(id,ticket,name,system) '
                  'VALUES(?,?,?,?)', (list_id, ticket, name, 1 if system else 0))
        c.commit()
        return self.shelf_get(ticket, list_id)

    def shelf_next_custom_id(self, ticket):
        """Next free custom-list id 's<n>' for this reader (avoids system ids)."""
        n = self._conn().execute(
            "SELECT COUNT(*) AS n FROM reader_shelf WHERE ticket=? AND system=0",
            (ticket,)).fetchone()['n']
        existing = {r['id'] for r in self.shelf_lists(ticket)}
        i = n + 1
        while ('s%d' % i) in existing:
            i += 1
        return 's%d' % i

    def shelf_items(self, ticket, list_id):
        return [dict(r) for r in self._conn().execute(
            'SELECT db,mfn,title FROM reader_shelf_item WHERE ticket=? AND list_id=? '
            'ORDER BY added_at, db, mfn', (ticket, list_id)).fetchall()]

    def shelf_add_item(self, ticket, list_id, db, mfn, title):
        """Add (db,mfn) to a list, deduped per list (PK upserts title)."""
        c = self._conn()
        c.execute(
            'INSERT INTO reader_shelf_item(ticket,list_id,db,mfn,title) VALUES(?,?,?,?,?) '
            'ON CONFLICT(ticket,list_id,db,mfn) DO UPDATE SET title=excluded.title',
            (ticket, list_id, db, mfn, title))
        c.commit()

    def shelf_remove_item(self, ticket, list_id, db, mfn):
        c = self._conn()
        c.execute('DELETE FROM reader_shelf_item WHERE ticket=? AND list_id=? '
                  'AND db=? AND mfn=?', (ticket, list_id, db, mfn))
        c.commit()

    # ---- reader-portal v2 social (#134/#133) — reviews / history / saved searches ----
    @staticmethod
    def _decrypt_review(row):
        """Return the review dict with ``reader_name`` decrypted (V1).

        The column is stored as ciphertext at rest (crypto.encrypt); decryption is
        transparent — a legacy plaintext row passes through unchanged."""
        if row is None:
            return None
        d = dict(row)
        if 'reader_name' in d:
            d['reader_name'] = crypto.decrypt(d['reader_name'])
        return d

    def review_upsert(self, ticket, db, mfn, rating, text, reader_name, ts):
        """Insert/replace the reader's review of (db,mfn) (one per reader+item).

        ``reader_name`` is the reader's resolved display name (ПДн); it is
        ENCRYPTED at rest (V1) so a raw DB dump never reveals it. The returned row
        is decrypted for the caller (transparent)."""
        c = self._conn()
        enc_name = crypto.encrypt(reader_name)
        c.execute(
            'INSERT INTO reader_review(ticket,db,mfn,rating,text,reader_name,ts) '
            'VALUES(?,?,?,?,?,?,?) ON CONFLICT(ticket,db,mfn) DO UPDATE SET '
            'rating=excluded.rating, text=excluded.text, '
            'reader_name=excluded.reader_name, ts=excluded.ts',
            (ticket, db, mfn, rating, text, enc_name, ts))
        c.commit()
        r = c.execute('SELECT * FROM reader_review WHERE ticket=? AND db=? AND mfn=?',
                      (ticket, db, mfn)).fetchone()
        return self._decrypt_review(r)

    def reviews_for(self, db, mfn):
        """All reviews of (db,mfn), newest first — feeds avg/count + cards.

        ``reader_name`` is decrypted in the handler (stored ciphertext, V1)."""
        return [self._decrypt_review(r) for r in self._conn().execute(
            'SELECT * FROM reader_review WHERE db=? AND mfn=? ORDER BY ts DESC, id DESC',
            (db, mfn)).fetchall()]

    def review_mine(self, ticket, db, mfn):
        """The reader's own review of (db,mfn), or None (reader_name decrypted)."""
        r = self._conn().execute(
            'SELECT * FROM reader_review WHERE ticket=? AND db=? AND mfn=?',
            (ticket, db, mfn)).fetchone()
        return self._decrypt_review(r) if r else None

    def review_name_ciphertext(self, ticket, db, mfn):
        """The RAW stored ``reader_name`` value (no decrypt) — for tests/forensics
        that need to assert the at-rest value is ciphertext, not plaintext."""
        r = self._conn().execute(
            'SELECT reader_name FROM reader_review WHERE ticket=? AND db=? AND mfn=?',
            (ticket, db, mfn)).fetchone()
        return r['reader_name'] if r else None

    def review_delete(self, ticket, review_id):
        """Delete the reader's OWN review by id; returns the row, or None when the
        id isn't theirs (so the route can 403 on someone else's review)."""
        c = self._conn()
        row = c.execute('SELECT * FROM reader_review WHERE id=? AND ticket=?',
                        (review_id, ticket)).fetchone()
        if not row:
            return None
        c.execute('DELETE FROM reader_review WHERE id=?', (review_id,))
        c.commit()
        return dict(row)

    def history_log(self, ticket, db, mfn, title, ts):
        """Record a record-open, deduped by (ticket,db,mfn) — the latest open
        updates ts (and refreshes the resolved title when we have one)."""
        c = self._conn()
        c.execute(
            'INSERT INTO reader_history(ticket,db,mfn,title,ts) VALUES(?,?,?,?,?) '
            'ON CONFLICT(ticket,db,mfn) DO UPDATE SET ts=excluded.ts, '
            'title=COALESCE(NULLIF(excluded.title,\'\'), reader_history.title)',
            (ticket, db, mfn, title, ts))
        c.commit()

    def history_for(self, ticket, limit=50):
        """The reader's history, newest first (already deduped by PK), capped."""
        return [dict(r) for r in self._conn().execute(
            'SELECT db,mfn,title,ts FROM reader_history WHERE ticket=? '
            'ORDER BY ts DESC, db, mfn LIMIT ?', (ticket, limit)).fetchall()]

    def popular(self, db=None, limit=12):
        """«Популярное» — самые открываемые записи по ``reader_history`` (агрегат по
        всем читателям). Каждая строка истории уникальна по (ticket,db,mfn), так что
        COUNT = число РАЗНЫХ читателей, открывавших запись. Опц. фильтр по базе.
        Возвращает ``[{db, mfn, count, title}]`` по убыванию популярности."""
        sql = 'SELECT db, mfn, COUNT(*) AS n, MAX(title) AS title FROM reader_history'
        params = []
        if db:
            sql += ' WHERE db=?'
            params.append(db)
        sql += ' GROUP BY db, mfn ORDER BY n DESC LIMIT ?'
        params.append(int(limit))
        return [{'db': r['db'], 'mfn': r['mfn'], 'count': int(r['n']),
                 'title': r['title'] or ('MFN %d' % r['mfn'])}
                for r in self._conn().execute(sql, params).fetchall()]

    def saved_search_list(self, ticket):
        return [dict(r) for r in self._conn().execute(
            'SELECT id,name,db,prefix,query FROM saved_search WHERE ticket=? '
            'ORDER BY id', (ticket,)).fetchall()]

    def saved_search_add(self, ticket, name, db, prefix, query, ts):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO saved_search(ticket,name,db,prefix,query,created_at) '
            'VALUES(?,?,?,?,?,?)', (ticket, name, db, prefix, query, ts))
        c.commit()
        r = c.execute('SELECT * FROM saved_search WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def saved_search_delete(self, ticket, search_id):
        """Delete the reader's own saved search; returns the row, or None."""
        c = self._conn()
        row = c.execute('SELECT * FROM saved_search WHERE id=? AND ticket=?',
                        (search_id, ticket)).fetchone()
        if not row:
            return None
        c.execute('DELETE FROM saved_search WHERE id=?', (search_id,))
        c.commit()
        return dict(row)

    # ---- consent (V9 / R9) — append-only; latest row by ts is effective ----
    def consent_record(self, ticket, given, version, ts):
        """Append a consent state (granted/withdrawn) for the reader. Never an
        UPDATE — the prior state is kept as history (SPEC_compliance_152fz §2.5).
        Returns the effective consent after the write."""
        c = self._conn()
        c.execute('INSERT INTO reader_consent(ticket,given,version,ts) VALUES(?,?,?,?)',
                  (ticket, 1 if given else 0, int(version), ts))
        c.commit()
        return self.consent_current(ticket)

    def consent_current(self, ticket):
        """The reader's effective consent (latest row by ts), or None if never set.

        Returns ``{'given': bool, 'ts': float, 'version': int}``."""
        r = self._conn().execute(
            'SELECT given,version,ts FROM reader_consent WHERE ticket=? '
            'ORDER BY ts DESC, id DESC LIMIT 1', (ticket,)).fetchone()
        if not r:
            return None
        return {'given': bool(r['given']), 'ts': r['ts'], 'version': r['version']}

    # ---- right to erasure (V9 / R9) — delete OUR stored reader data only ----
    # Deletes the reader's own rows across every table OUR store holds for a
    # ticket. Does NOT touch the live ИРБИС RDR (that is the system of record);
    # only the portal-side state we persisted. Reader-scoped: a ticket can only
    # erase its own rows (the route guards the ticket == session).
    def erase_reader(self, ticket):
        """Delete all of ``ticket``'s portal data; return a per-table count dict."""
        c = self._conn()
        counts = {}
        for key, sql in (
                ('reviews', 'DELETE FROM reader_review WHERE ticket=?'),
                ('holds', 'DELETE FROM reader_hold WHERE ticket=?'),
                ('shelves', 'DELETE FROM reader_shelf WHERE ticket=?'),
                ('shelfItems', 'DELETE FROM reader_shelf_item WHERE ticket=?'),
                ('history', 'DELETE FROM reader_history WHERE ticket=?'),
                ('savedSearches', 'DELETE FROM saved_search WHERE ticket=?'),
                ('consent', 'DELETE FROM reader_consent WHERE ticket=?')):
            cur = c.execute(sql, (ticket,))
            counts[key] = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0
        c.commit()
        return counts

    # ---- PDn-access journal read (V5 / R5) — entries are written via audit() ----
    def pdn_access_log(self, limit=50):
        """The most-recent ``pdn.read`` audit entries, newest first, capped.

        The journal reuses the append-only ``audit_log`` with function='pdn.read'
        (MVP: a dedicated pdn_access_log table is specified for a later slice,
        SPEC_compliance_152fz §3.5). Each entry carries actor, subject ticket (in
        detail), ts, action."""
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM audit_log WHERE function='pdn.read' "
            'ORDER BY id DESC LIMIT ?', (limit,)).fetchall()]
