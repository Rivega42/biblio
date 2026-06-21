#!/usr/bin/env python3
"""PostgreSQL-backed Access store (prod target, ADR-004). Mirrors the sqlite
``AccessStore`` public surface exactly — same methods, same return shapes — so
``core.py`` and the Access test suite run unchanged against either backend
(switch via env ``ACCESS_BACKEND=sqlite|postgres``).

Holds staff accounts, grants, roles and the audit log (readers live in RDR, not
here). DDL is the shared ``schema_postgres.sql``. Password hashing (pbkdf2-sha256)
is reused verbatim from ``AccessStore`` so hashes are interchangeable across
backends.

Driver: psycopg 3 (``pip install "psycopg[binary]"``). psycopg is imported
lazily so this module still imports on a Python without psycopg installed
(e.g. 3.14) when the sqlite backend is selected — only constructing
``PgAccessStore`` requires the driver.
"""
import os
import threading

from .store import AccessStore   # reuse pbkdf2 hash/verify (interchangeable hashes)

# DDL lives next to this module as the shared production schema.
_SCHEMA_SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'schema_postgres.sql')


class PgAccessStore:
    """Same public API as ``access.store.AccessStore`` on PostgreSQL/psycopg3.

    A dedicated database/schema is expected (default DSN points at
    ``irbis_access``) so the Access tables never collide with own-server
    catalog data.
    """

    def __init__(self, dsn):
        self.dsn = dsn
        self.db_path = dsn          # parity with AccessStore.db_path (a few callers introspect it)
        self._local = threading.local()
        self.ensure_schema()

    # ---- connection (thread-local, autocommit like the sqlite store's per-op commit) ----
    def _conn(self):
        import psycopg
        from psycopg.rows import dict_row
        conn = getattr(self._local, 'conn', None)
        if conn is None or conn.closed:
            conn = psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True)
            self._local.conn = conn
        return conn

    def ensure_schema(self):
        with open(_SCHEMA_SQL_PATH, encoding='utf-8') as f:
            ddl = f.read()
        self._conn().execute(ddl)

    # ---- password hashing — reuse the sqlite store's pbkdf2 (hashes interchangeable) ----
    @staticmethod
    def hash_password(pw, iterations=200000):
        return AccessStore.hash_password(pw, iterations)

    @staticmethod
    def verify_password(pw, stored):
        return AccessStore.verify_password(pw, stored)

    # ---- accounts ----
    def create_account(self, login, password, full_name=''):
        self._conn().execute(
            'INSERT INTO staff_account(login,pass_hash,full_name) VALUES(%s,%s,%s)'
            ' ON CONFLICT(login) DO NOTHING',
            (login, self.hash_password(password), full_name))
        return self.get_account(login)

    def get_account(self, login):
        r = self._conn().execute(
            'SELECT * FROM staff_account WHERE login=%s', (login,)).fetchone()
        return dict(r) if r else None

    def authenticate(self, login, password):
        a = self.get_account(login)
        if a and a['is_active'] and self.verify_password(password, a['pass_hash']):
            return a
        return None

    # ---- grants / roles ----
    def add_grant(self, account_id, function, db, level):
        self._conn().execute(
            'INSERT INTO grant_entry(account_id,function,db,level) VALUES(%s,%s,%s,%s)'
            ' ON CONFLICT(account_id,function,db) DO UPDATE SET level=EXCLUDED.level',
            (account_id, function, db, level))

    def add_role(self, name):
        c = self._conn()
        c.execute('INSERT INTO role(name) VALUES(%s) ON CONFLICT(name) DO NOTHING', (name,))
        return c.execute('SELECT id FROM role WHERE name=%s', (name,)).fetchone()['id']

    def add_role_grant(self, role_id, function, db, level):
        self._conn().execute(
            'INSERT INTO role_grant(role_id,function,db,level) VALUES(%s,%s,%s,%s)'
            ' ON CONFLICT(role_id,function,db) DO UPDATE SET level=EXCLUDED.level',
            (role_id, function, db, level))

    def assign_role(self, account_id, role_id):
        self._conn().execute(
            'INSERT INTO account_role(account_id,role_id) VALUES(%s,%s)'
            ' ON CONFLICT(account_id,role_id) DO NOTHING',
            (account_id, role_id))

    def effective_grants(self, account_id):
        """Union of direct grants and grants from all assigned roles."""
        c = self._conn()
        grants = [dict(r) for r in c.execute(
            'SELECT function,db,level FROM grant_entry WHERE account_id=%s',
            (account_id,)).fetchall()]
        grants += [dict(r) for r in c.execute(
            '''SELECT rg.function, rg.db, rg.level FROM role_grant rg
               JOIN account_role ar ON ar.role_id=rg.role_id
               WHERE ar.account_id=%s''', (account_id,)).fetchall()]
        return grants

    # ---- audit ----
    def audit(self, actor, function, db, mfn, result, detail=None):
        from psycopg.types.json import Jsonb
        self._conn().execute(
            'INSERT INTO audit_log(actor,function,db,mfn,result,detail) VALUES(%s,%s,%s,%s,%s,%s)',
            (actor, function, db, mfn, result, Jsonb(detail or {})))

    def recent_audit(self, limit=50):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM audit_log ORDER BY id DESC LIMIT %s', (limit,)).fetchall()]


def make_store(cfg=None):
    """Factory: return the Access store for the configured backend.

    ``ACCESS_BACKEND=sqlite`` (default) -> sqlite ``AccessStore`` at ``cfg.access_db``
    (or ``ACCESS_DB`` env). ``ACCESS_BACKEND=postgres`` -> ``PgAccessStore`` at
    ``ACCESS_PG_DSN`` (default the local ``irbis-pg`` container's ``irbis_access`` db).

    Mirrors ``server-own/store.make_store()``. Sqlite stays the default so nothing
    breaks where psycopg is unavailable.
    """
    backend = os.environ.get('ACCESS_BACKEND', 'sqlite').lower()
    if backend in ('postgres', 'pg'):
        dsn = os.environ.get(
            'ACCESS_PG_DSN', 'postgresql://postgres:pg@127.0.0.1:5433/irbis_access')
        return PgAccessStore(dsn)
    # sqlite (default)
    if cfg is not None and getattr(cfg, 'access_db', None):
        path = cfg.access_db
    else:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.environ.get('ACCESS_DB', os.path.join(here, 'access.db'))
    return AccessStore(path)
