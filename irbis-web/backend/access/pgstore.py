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
import re
import threading

from .store import AccessStore   # reuse pbkdf2 hash/verify (interchangeable hashes)

# DDL lives next to this module as the shared production schema.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCHEMA_SQL_PATH = os.path.join(_HERE, 'schema_postgres.sql')      # Access DDL (per tenant)
_CONTROL_SQL_PATH = os.path.join(_HERE, 'schema_control.sql')      # control.tenant catalog

# A slug is the tenant key and becomes part of a SQL identifier (t_<slug>). It is
# NEVER interpolated into SQL without passing this gate, so schema names can't be
# used for injection. Lowercase letters/digits/underscore, must start with a letter.
_SLUG_RE = re.compile(r'^[a-z][a-z0-9_]{0,40}$')


def _validate_slug(slug):
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise ValueError(
            'invalid tenant slug %r (need ^[a-z][a-z0-9_]{0,40}$)' % (slug,))
    return slug


def schema_for(slug):
    """Schema name that holds tenant <slug>'s Access data: ``t_<slug>``."""
    return 't_' + _validate_slug(slug)


class PgAccessStore:
    """Same public API as ``access.store.AccessStore`` on PostgreSQL/psycopg3.

    A dedicated database/schema is expected (default DSN points at
    ``irbis_access``) so the Access tables never collide with own-server
    catalog data.

    **Multi-tenant (issue #100):** pass ``tenant_schema='t_<slug>'`` to scope the
    SAME store class to one tenant. Every connection checkout then runs
    ``SET search_path = <schema>, public`` so all unqualified table access reads/
    writes that tenant's schema only — data is fully separated by schema, with no
    leakage when a pooled connection is reused (the path is set on every checkout).
    ``tenant_schema=None`` (the default) keeps the back-compat single-``public``
    behaviour unchanged. Prefer ``make_tenant_store(dsn, slug)`` to construct one.
    """

    def __init__(self, dsn, tenant_schema=None):
        self.dsn = dsn
        self.db_path = dsn          # parity with AccessStore.db_path (a few callers introspect it)
        self.tenant_schema = tenant_schema   # 't_<slug>' for a tenant, or None for public
        self._local = threading.local()
        self.ensure_schema()

    # ---- connection (thread-local, autocommit like the sqlite store's per-op commit) ----
    def _conn(self):
        import psycopg
        from psycopg.rows import dict_row
        conn = getattr(self._local, 'conn', None)
        if conn is None or conn.closed:
            conn = psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True)
            self._apply_search_path(conn)
            self._local.conn = conn
        return conn

    def _apply_search_path(self, conn):
        """Pin this connection to the tenant schema (then ``public``).

        Called on every checkout of a fresh connection, so a connection reused
        across tenants never leaks: the search_path is (re)set deterministically.
        The schema identifier is built only from a validated slug (see
        ``schema_for``), so it is safe to embed without quoting injection risk.
        Run only when this store is tenant-scoped; the public store keeps PG's
        default search_path untouched (back-compat).
        """
        if self.tenant_schema:
            from psycopg import sql
            conn.execute(
                sql.SQL('SET search_path = {}, public').format(
                    sql.Identifier(self.tenant_schema)))

    def ensure_schema(self):
        """Create the Access tables. For a tenant store, create the schema first
        and apply the (unqualified) Access DDL *into* it via ``search_path``."""
        conn = self._conn()   # also applies search_path = t_<slug>, public
        if self.tenant_schema:
            from psycopg import sql
            conn.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(
                sql.Identifier(self.tenant_schema)))
            # search_path is already pinned (PG resolves it lazily at query time),
            # so the unqualified DDL below creates tables inside t_<slug>.
        with open(_SCHEMA_SQL_PATH, encoding='utf-8') as f:
            ddl = f.read()
        conn.execute(ddl)

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

    # ---- vocabularies (seeding engine, gap A5 #188) — same surface as AccessStore ----
    # All writes go through the tenant-pinned search_path, so they land in t_<slug>.
    def upsert_vocabulary(self, name, title, kind, field_hint, seed_version):
        self._conn().execute(
            'INSERT INTO vocabulary(name,title,kind,field_hint,seed_version) '
            'VALUES(%s,%s,%s,%s,%s) ON CONFLICT(name) DO UPDATE SET '
            'title=EXCLUDED.title, kind=EXCLUDED.kind, field_hint=EXCLUDED.field_hint',
            (name, title, kind, field_hint, seed_version))

    def upsert_vocabulary_value(self, vocab, code, label, sort, origin='seed'):
        # ON CONFLICT keeps the stored origin (don't downgrade custom->seed on reseed).
        self._conn().execute(
            'INSERT INTO vocabulary_value(vocab,code,label,sort,origin) VALUES(%s,%s,%s,%s,%s) '
            'ON CONFLICT(vocab,code) DO UPDATE SET label=EXCLUDED.label, sort=EXCLUDED.sort',
            (vocab, code, label, sort, origin))

    def get_vocabulary(self, name):
        r = self._conn().execute('SELECT * FROM vocabulary WHERE name=%s', (name,)).fetchone()
        return dict(r) if r else None

    def list_vocabularies(self):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM vocabulary ORDER BY name').fetchall()]

    def vocabulary_values(self, name, active_only=False):
        sql = ('SELECT code,label,sort,origin,active FROM vocabulary_value '
               'WHERE vocab=%s' + (' AND active=true' if active_only else '') +
               ' ORDER BY sort, code')
        return [dict(r) for r in self._conn().execute(sql, (name,)).fetchall()]

    def upsert_classification_node(self, name, code, label, parent, depth, path, sort=0):
        self._conn().execute(
            'INSERT INTO classification_node(name,code,label,parent,depth,path,sort) '
            'VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(name,code) DO UPDATE SET '
            'label=EXCLUDED.label, parent=EXCLUDED.parent, depth=EXCLUDED.depth, '
            'path=EXCLUDED.path, sort=EXCLUDED.sort',
            (name, code, label, parent, depth, path, sort))

    def classification_nodes(self, name):
        return [dict(r) for r in self._conn().execute(
            'SELECT code,label,parent,depth,path,sort FROM classification_node '
            'WHERE name=%s ORDER BY sort, code', (name,)).fetchall()]

    # ---- reader holds (#222) — reader-scoped by RDR ticket, NOT on live ИРБИС ----
    def hold_find_live(self, ticket, db, mfn):
        r = self._conn().execute(
            "SELECT * FROM reader_hold WHERE ticket=%s AND db=%s AND mfn=%s "
            "AND status IN ('queued','ready') ORDER BY id LIMIT 1",
            (ticket, db, mfn)).fetchone()
        return dict(r) if r else None

    def hold_queue(self, db, mfn):
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM reader_hold WHERE db=%s AND mfn=%s "
            "AND status IN ('queued','ready') ORDER BY queued_at, id",
            (db, mfn)).fetchall()]

    def hold_add(self, ticket, db, mfn, title, status, queued_at, until=None):
        r = self._conn().execute(
            'INSERT INTO reader_hold(ticket,db,mfn,title,status,queued_at,until) '
            'VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id',
            (ticket, db, mfn, title, status, queued_at, until)).fetchone()
        return self.hold_get(r['id'])

    def hold_get(self, hold_id):
        r = self._conn().execute(
            'SELECT * FROM reader_hold WHERE id=%s', (hold_id,)).fetchone()
        return dict(r) if r else None

    def holds_for(self, ticket):
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM reader_hold WHERE ticket=%s AND status IN ('queued','ready') "
            'ORDER BY queued_at, id', (ticket,)).fetchall()]

    def hold_cancel(self, ticket, hold_id):
        row = self._conn().execute(
            "SELECT * FROM reader_hold WHERE id=%s AND ticket=%s "
            "AND status IN ('queued','ready')", (hold_id, ticket)).fetchone()
        if not row:
            return None
        self._conn().execute(
            "UPDATE reader_hold SET status='cancelled' WHERE id=%s", (hold_id,))
        return dict(row)

    # ---- reader shelves / reading lists (#222) — reader-scoped by RDR ticket ----
    def shelf_lists(self, ticket):
        return [dict(r) for r in self._conn().execute(
            'SELECT id,name,system,created_at FROM reader_shelf WHERE ticket=%s '
            'ORDER BY system DESC, created_at, id', (ticket,)).fetchall()]

    def shelf_get(self, ticket, list_id):
        r = self._conn().execute(
            'SELECT * FROM reader_shelf WHERE ticket=%s AND id=%s',
            (ticket, list_id)).fetchone()
        return dict(r) if r else None

    def shelf_create(self, ticket, list_id, name, system=0):
        self._conn().execute(
            'INSERT INTO reader_shelf(id,ticket,name,system) VALUES(%s,%s,%s,%s) '
            'ON CONFLICT(ticket,id) DO NOTHING',
            (list_id, ticket, name, bool(system)))
        return self.shelf_get(ticket, list_id)

    def shelf_next_custom_id(self, ticket):
        n = self._conn().execute(
            'SELECT COUNT(*) AS n FROM reader_shelf WHERE ticket=%s AND system=false',
            (ticket,)).fetchone()['n']
        existing = {r['id'] for r in self.shelf_lists(ticket)}
        i = n + 1
        while ('s%d' % i) in existing:
            i += 1
        return 's%d' % i

    def shelf_items(self, ticket, list_id):
        return [dict(r) for r in self._conn().execute(
            'SELECT db,mfn,title FROM reader_shelf_item WHERE ticket=%s AND list_id=%s '
            'ORDER BY added_at, db, mfn', (ticket, list_id)).fetchall()]

    def shelf_add_item(self, ticket, list_id, db, mfn, title):
        self._conn().execute(
            'INSERT INTO reader_shelf_item(ticket,list_id,db,mfn,title) '
            'VALUES(%s,%s,%s,%s,%s) '
            'ON CONFLICT(ticket,list_id,db,mfn) DO UPDATE SET title=EXCLUDED.title',
            (ticket, list_id, db, mfn, title))

    def shelf_remove_item(self, ticket, list_id, db, mfn):
        self._conn().execute(
            'DELETE FROM reader_shelf_item WHERE ticket=%s AND list_id=%s '
            'AND db=%s AND mfn=%s', (ticket, list_id, db, mfn))


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


# --------------------------------------------------------------------------- #
# Multi-tenancy: control schema + provisioning (issue #100, I1).
# --------------------------------------------------------------------------- #
def default_pg_dsn():
    """DSN used by tenancy helpers — the same env knob the Access store reads."""
    return os.environ.get(
        'ACCESS_PG_DSN', 'postgresql://postgres:pg@127.0.0.1:5433/irbis_access')


def _admin_conn(dsn):
    """A short-lived autocommit connection for cross-tenant (control-plane) DDL.

    Kept separate from any store's thread-local connection so its search_path
    stays at PG's default — provisioning addresses schemas explicitly.
    """
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def ensure_control_schema(dsn=None):
    """Create the ``control`` schema + ``control.tenant`` table (idempotent)."""
    dsn = dsn or default_pg_dsn()
    with open(_CONTROL_SQL_PATH, encoding='utf-8') as f:
        ddl = f.read()
    conn = _admin_conn(dsn)
    try:
        conn.execute(ddl)
    finally:
        conn.close()


def make_tenant_store(slug, dsn=None):
    """A ``PgAccessStore`` scoped to tenant ``<slug>`` (schema ``t_<slug>``)."""
    return PgAccessStore(dsn or default_pg_dsn(), tenant_schema=schema_for(slug))


def list_tenants(dsn=None):
    """All provisioned tenants from the control catalog (ordered by slug)."""
    dsn = dsn or default_pg_dsn()
    ensure_control_schema(dsn)
    conn = _admin_conn(dsn)
    try:
        return [dict(r) for r in conn.execute(
            'SELECT id, slug, name, kind, created_at FROM control.tenant '
            'ORDER BY slug').fetchall()]
    finally:
        conn.close()


def provision_tenant(slug, name, kind, dsn=None, do_seed=True):
    """Create (or re-create idempotently) tenant ``<slug>`` and return its store.

    Steps (all idempotent — safe to re-run):
      1. ensure ``control`` schema + record the tenant row (upsert on slug);
      2. ``CREATE SCHEMA IF NOT EXISTS t_<slug>`` and apply the Access DDL into it
         (done by ``PgAccessStore(tenant_schema=...)`` on construction);
      3. run the idempotent seed (admin/admin, librarian/librarian) *inside* that
         tenant schema.

    Returns the tenant-scoped ``PgAccessStore``.
    """
    _validate_slug(slug)
    dsn = dsn or default_pg_dsn()
    ensure_control_schema(dsn)
    conn = _admin_conn(dsn)
    try:
        conn.execute(
            'INSERT INTO control.tenant(slug, name, kind) VALUES(%s,%s,%s) '
            'ON CONFLICT(slug) DO UPDATE SET name=EXCLUDED.name, kind=EXCLUDED.kind',
            (slug, name, kind))
    finally:
        conn.close()
    # Constructing the store creates t_<slug> and the Access tables within it
    # (including the vocabulary/classification tables from schema_postgres.sql).
    store = make_tenant_store(slug, dsn)
    if do_seed:
        from .seed import seed
        seed(store)
        # Licensing (#101): turn the default module set ON for the new tenant.
        # Idempotent; leaves any operator-disabled module untouched on re-provision.
        from . import entitlements
        entitlements.seed_modules(slug, dsn)
        # Seeding engine (A5, #188): system vocabs populated, institution vocabs
        # created empty — runs AFTER schema migrate, idempotent (re-provision safe).
        from . import seed_vocab
        seed_vocab.ensure_seed_catalog(dsn)     # master catalog (control plane)
        seed_vocab.seed_vocabularies(store, dsn)  # copy into t_<slug>
    return store


def deprovision_tenant(slug, dsn=None):
    """Drop tenant ``<slug>``: ``DROP SCHEMA t_<slug> CASCADE`` + remove its
    control row. Idempotent (no error if the tenant was never provisioned)."""
    _validate_slug(slug)
    dsn = dsn or default_pg_dsn()
    from psycopg import sql
    conn = _admin_conn(dsn)
    try:
        conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
            sql.Identifier(schema_for(slug))))
        # control.tenant may not exist yet on a clean DB; referencing a missing
        # table errors at plan time, so check existence before deleting the row.
        has_ctl = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='control' AND table_name='tenant'").fetchone()
        if has_ctl:
            conn.execute('DELETE FROM control.tenant WHERE slug=%s', (slug,))
    finally:
        conn.close()
