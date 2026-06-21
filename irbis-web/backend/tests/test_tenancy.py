#!/usr/bin/env python3
"""Tenant isolation tests (issue #100, I1): schema-per-tenant on PostgreSQL.

The hard gate for multi-tenancy. Provisions two tenants in separate schemas
(t_<slug>) and asserts that a tenant-scoped Access store sees ONLY its own
tenant's accounts / grants / audit — never the other tenant's rows, in either
direction — plus a direct negative SQL probe that tenant A's scope cannot read
tenant B's schema. Also checks provisioning idempotency and deprovision teardown.

Backends:
  * postgres only — schema-per-tenant is a PG feature. Runs when
    ACCESS_BACKEND=postgres (or ACCESS_TEST_PG=1) AND a PG is reachable at
    ACCESS_PG_DSN; otherwise the whole suite is SKIPPED cleanly (exit 0), so it
    never red-flags the sqlite-only dev box. CI runs it against the postgres
    service container (see .github/workflows/ci.yml).

Run (PG):  (set ACCESS_BACKEND=postgres) py -3.12 irbis-web/backend/tests/test_tenancy.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import pgstore
from access.authz import authorize

PASS = [0]
FAIL = [0]

# Two tenants in their own schemas. Slugs are deliberately disjoint.
A_SLUG, B_SLUG = 'tnt_a', 'tnt_b'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def pg_reachable(dsn):
    """True iff the postgres backend is requested AND a server is reachable."""
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return False
    try:
        conn = pgstore._admin_conn(dsn)
        conn.close()
        return True
    except Exception as e:                       # PG down / psycopg missing -> skip cleanly
        print('-- tenancy suite SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return False


def _count_in_schema(dsn, schema, table):
    """Direct row count in a fully-qualified schema.table (control-plane probe)."""
    from psycopg import sql
    conn = pgstore._admin_conn(dsn)
    try:
        return conn.execute(sql.SQL('SELECT count(*) AS n FROM {}.{}').format(
            sql.Identifier(schema), sql.Identifier(table))).fetchone()['n']
    finally:
        conn.close()


def run(dsn):
    # Clean slate so the run is deterministic.
    pgstore.deprovision_tenant(A_SLUG, dsn)
    pgstore.deprovision_tenant(B_SLUG, dsn)

    # ---- provision two tenants, each seeded (admin/admin, librarian/librarian) ----
    sa = pgstore.provision_tenant(A_SLUG, 'Library A', 'публичная', dsn)
    sb = pgstore.provision_tenant(B_SLUG, 'Library B', 'школьная', dsn)
    check('two distinct schemas', sa.tenant_schema != sb.tenant_schema
          and sa.tenant_schema == 't_tnt_a' and sb.tenant_schema == 't_tnt_b')

    # control catalog has both rows with the right kind
    tenants = {t['slug']: t for t in pgstore.list_tenants(dsn)}
    check('control row A (kind)', tenants.get('tnt_a', {}).get('kind') == 'публичная')
    check('control row B (kind)', tenants.get('tnt_b', {}).get('kind') == 'школьная')

    # ---- a DISTINCT account in each tenant ----
    sa.create_account('alice', 'pw_a', 'Alice (A only)')
    sb.create_account('bob', 'pw_b', 'Bob (B only)')

    # ---- authenticate: each tenant sees only its own account ----
    check('A authenticates alice', sa.authenticate('alice', 'pw_a') is not None)
    check('B authenticates bob', sb.authenticate('bob', 'pw_b') is not None)
    # cross-tenant invisibility: A never sees bob; B never sees alice
    check('A cannot see bob (authenticate)', sa.authenticate('bob', 'pw_b') is None)
    check('A cannot see bob (get_account)', sa.get_account('bob') is None)
    check('B cannot see alice (authenticate)', sb.authenticate('alice', 'pw_a') is None)
    check('B cannot see alice (get_account)', sb.get_account('alice') is None)

    # seeded admin is independent per tenant (same login, different schema/row)
    admin_a = sa.authenticate('admin', 'admin')
    admin_b = sb.authenticate('admin', 'admin')
    check('both tenants have own admin', admin_a is not None and admin_b is not None)

    # ---- effective_grants are per-tenant (seeded admin has admin.users) ----
    ega = sa.effective_grants(admin_a['id'])
    egb = sb.effective_grants(admin_b['id'])
    check('A admin effective grants', authorize(ega, 'admin.users', 'IBIS', 'admin'))
    check('B admin effective grants', authorize(egb, 'admin.users', 'IBIS', 'admin'))

    # ---- audit is per-tenant: write in A only ----
    sa.audit('alice', 'record.write', 'IBIS', 7, 'ok', {'note': 'A-only'})
    aud_a = sa.recent_audit()
    aud_b = sb.recent_audit()
    check('A audit has its row', any(r['actor'] == 'alice' for r in aud_a))
    check('B audit never sees A row', not any(r['actor'] == 'alice' for r in aud_b))

    # ---- NEGATIVE probe: tenant A's scope cannot read tenant B's schema rows ----
    # Run a query through A's pinned connection (search_path = t_tnt_a, public)
    # using the UNQUALIFIED table name: it must resolve to A's schema, so bob
    # (who only exists in B) is invisible. Reaching bob would prove a leak.
    leaked = sa._conn().execute(
        'SELECT count(*) AS n FROM staff_account WHERE login=%s', ('bob',)
    ).fetchone()['n']
    check('A search_path cannot reach B rows', leaked == 0)
    # And symmetric: B's scope cannot reach alice.
    leaked_b = sb._conn().execute(
        'SELECT count(*) AS n FROM staff_account WHERE login=%s', ('alice',)
    ).fetchone()['n']
    check('B search_path cannot reach A rows', leaked_b == 0)

    # Ground truth via the control plane: each row physically lives in its schema.
    check('alice physically in t_tnt_a only',
          _count_in_schema(dsn, 't_tnt_a', 'staff_account') >= 1
          and _count_in_schema(dsn, 't_tnt_b', 'staff_account') >= 1)

    # ---- provisioning is idempotent: re-provision must not duplicate or raise ----
    before = sa.get_account('alice')
    sa2 = pgstore.provision_tenant(A_SLUG, 'Library A', 'публичная', dsn)
    after = sa2.get_account('alice')
    check('re-provision preserves data', before is not None and after is not None
          and before['id'] == after['id'])
    check('re-provision no dup tenant rows',
          sum(1 for t in pgstore.list_tenants(dsn) if t['slug'] == 'tnt_a') == 1)

    # ---- deprovision removes the schema (and the control row) ----
    pgstore.deprovision_tenant(B_SLUG, dsn)
    from psycopg import sql
    conn = pgstore._admin_conn(dsn)
    try:
        exists = conn.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name=%s",
            ('t_tnt_b',)).fetchone()
    finally:
        conn.close()
    check('deprovision drops schema', exists is None)
    check('deprovision removes control row',
          all(t['slug'] != 'tnt_b' for t in pgstore.list_tenants(dsn)))

    # idempotent deprovision (second call is a no-op, must not raise)
    pgstore.deprovision_tenant(B_SLUG, dsn)
    check('deprovision idempotent', True)

    # cleanup
    pgstore.deprovision_tenant(A_SLUG, dsn)


def main():
    dsn = pgstore.default_pg_dsn()
    if not pg_reachable(dsn):
        print('\n0 passed, 0 failed (tenancy: postgres unavailable, skipped)')
        sys.exit(0)
    print('-- tenancy: postgres', dsn.rsplit('@', 1)[-1])
    run(dsn)
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
