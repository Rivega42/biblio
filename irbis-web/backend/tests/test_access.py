#!/usr/bin/env python3
"""Access suite tests: password hash/verify, authz best-grant logic, effective
grants, seed, audit — run against BOTH store backends for parity (issue #92).

Backends:
  * sqlite  — always run (temp db); the dev default.
  * postgres — run when ACCESS_BACKEND=postgres (or ACCESS_TEST_PG=1) AND a PG is
    reachable at ACCESS_PG_DSN; skipped cleanly (not failed) when PG is down or
    psycopg is missing. Requires `py -3.12` (psycopg 3.x).

Run sqlite-only:  py irbis-web/backend/tests/test_access.py
Run both:         (set ACCESS_BACKEND=postgres) py -3.12 irbis-web/backend/tests/test_access.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.store import AccessStore
from access.pgstore import PgAccessStore
from access.authz import authorize, best_grant, READER_GRANTS, GUEST_GRANTS
from access.seed import seed

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def pure_checks():
    """Backend-independent checks (password hashing + pure authz). Run once."""
    # password
    h = AccessStore.hash_password('s3cret')
    check('password verify ok', AccessStore.verify_password('s3cret', h))
    check('password verify bad', not AccessStore.verify_password('wrong', h))
    # hashes are interchangeable across backends (same pbkdf2 impl)
    check('pg verifies sqlite hash', PgAccessStore.verify_password('s3cret', h))

    # authz logic (pure)
    grants = [
        {'function': 'record.write', 'db': '*', 'level': 'write'},
        {'function': 'record.write', 'db': 'IBIS', 'level': 'admin'},
        {'function': 'search', 'db': '*', 'level': 'read'},
    ]
    check('exact db beats *', best_grant(grants, 'record.write', 'IBIS')['level'] == 'admin')
    check('falls back to *', best_grant(grants, 'record.write', 'RDR')['level'] == 'write')
    check('write allows on RDR', authorize(grants, 'record.write', 'RDR', 'write'))
    check('read<write denied', not authorize(grants, 'search', 'IBIS', 'write'))
    check('no grant denied', not authorize(grants, 'admin.users', 'IBIS', 'admin'))
    check('guest can search', authorize(GUEST_GRANTS, 'search', 'IBIS', 'read'))
    check('guest cannot order', not authorize(GUEST_GRANTS, 'order', 'IBIS', 'write'))
    check('reader can order', authorize(READER_GRANTS, 'order', 'IBIS', 'write'))


def store_checks(label, st):
    """Store-backed checks (seed + effective grants + audit). Run per backend."""
    print('-- backend:', label)
    seed(st)
    acc = st.authenticate('admin', 'admin')
    check('[%s] seed admin authenticates' % label, acc is not None)
    check('[%s] seed bad password rejected' % label, st.authenticate('admin', 'nope') is None)
    eg = st.effective_grants(acc['id'])
    check('[%s] admin has admin.users' % label, authorize(eg, 'admin.users', 'IBIS', 'admin'))
    lib = st.authenticate('librarian', 'librarian')
    leg = st.effective_grants(lib['id'])
    check('[%s] librarian can write IBIS' % label, authorize(leg, 'record.write', 'IBIS', 'write'))
    check('[%s] librarian cannot admin users' % label, not authorize(leg, 'admin.users', 'IBIS', 'admin'))
    check('[%s] librarian can order' % label, authorize(leg, 'order', 'IBIS', 'write'))

    # seed is idempotent — second run must not duplicate/raise
    seed(st)
    check('[%s] seed idempotent' % label, st.authenticate('admin', 'admin') is not None)

    # audit
    st.audit('admin', 'record.write', 'IBIS', 42, 'ok', {'note': 'тест'})
    check('[%s] audit recorded' % label, len(st.recent_audit()) >= 1)


def sqlite_store():
    # In-memory: a fresh, isolated db per run with no temp file to clean up
    # (and no dependency on free disk space). Single-threaded test => one conn.
    return AccessStore(':memory:')


def pg_store_or_none():
    """Return a clean PgAccessStore, or None if PG/psycopg unavailable.

    Only attempted when the postgres backend is requested. Truncates the Access
    tables first so the run is deterministic (mirrors the fresh sqlite temp db).
    """
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return None
    dsn = os.environ.get('ACCESS_PG_DSN', 'postgresql://postgres:pg@127.0.0.1:5433/irbis_access')
    try:
        st = PgAccessStore(dsn)
        st._conn().execute(
            'TRUNCATE staff_account, grant_entry, role, role_grant, account_role, audit_log '
            'RESTART IDENTITY CASCADE')
        return st
    except Exception as e:                       # PG down / psycopg missing -> skip cleanly
        print('-- backend: postgres SKIPPED (%s: %s)' % (type(e).__name__, str(e).splitlines()[0]))
        return None


def tenancy_checks():
    """Run the tenant-isolation suite (issue #100) and fold its tally in.

    Only does anything on the postgres backend with a reachable server; on the
    sqlite dev box it skips cleanly (returns 0/0). Imported lazily so a Python
    without psycopg still runs the sqlite path. Lives in its own module
    (test_tenancy.py) but is invoked here so the existing CI step that runs
    test_access.py also exercises tenancy without a workflow change.
    """
    try:
        import test_tenancy
    except Exception as e:
        print('-- tenancy suite NOT RUN (import failed: %s)' % e)
        return
    dsn = test_tenancy.pgstore.default_pg_dsn()
    if not test_tenancy.pg_reachable(dsn):
        return
    print('-- tenancy: postgres', dsn.rsplit('@', 1)[-1])
    test_tenancy.run(dsn)
    PASS[0] += test_tenancy.PASS[0]
    FAIL[0] += test_tenancy.FAIL[0]


def identity_checks():
    """Run the Identity/Tenancy/Licensing suite (issue #101) and fold its tally in.

    The JWT + entitlement-default + _guard gating checks always run (no DB); the
    PG-only data-scoping + real tenant_module gating run when postgres is
    reachable and skip cleanly otherwise. Lives in its own module
    (test_identity.py) but is invoked here so the existing CI step that runs
    test_access.py also exercises identity/licensing without a workflow change.
    """
    try:
        import test_identity
    except Exception as e:
        print('-- identity suite NOT RUN (import failed: %s)' % e)
        FAIL[0] += 1                # importable suite is mandatory; surface the failure
        return
    test_identity.jwt_checks()
    test_identity.api_session_checks()
    test_identity.entitlement_default_checks()
    test_identity.run_pg()
    PASS[0] += test_identity.PASS[0]
    FAIL[0] += test_identity.FAIL[0]


def seeding_checks():
    """Run the vocabulary-seeding suite (issue #188, A5) and fold its tally in.

    The parser + sqlite-seed checks always run (no DB); the PG path (provision ->
    seeded vocabs, isolation, idempotency) runs when postgres is reachable and skips
    cleanly otherwise. Lives in its own module (test_seeding.py) but is invoked here
    so the existing CI step that runs test_access.py also exercises seeding with no
    workflow change.
    """
    try:
        import test_seeding
    except Exception as e:
        print('-- seeding suite NOT RUN (import failed: %s)' % e)
        FAIL[0] += 1                # importable suite is mandatory; surface the failure
        return
    test_seeding.parser_checks()
    test_seeding.sqlite_seed_checks()
    test_seeding.run_pg()
    PASS[0] += test_seeding.PASS[0]
    FAIL[0] += test_seeding.FAIL[0]


def flk_checks():
    """Run the declarative ФЛК validation-engine suite (issue #188, A2) and fold
    its tally in.

    All checks are pure (check digits, the engine against an in-memory seeded
    store, the constructed-Api endpoint) — they always run, no DB needed. Lives in
    its own module (test_flk.py) but is invoked here so the existing CI step that
    runs test_access.py also exercises the ФЛК engine with no workflow change.
    """
    try:
        import test_flk
    except Exception as e:
        print('-- flk suite NOT RUN (import failed: %s)' % e)
        FAIL[0] += 1                # importable suite is mandatory; surface the failure
        return
    test_flk.checksum_checks()
    test_flk.engine_checks()
    test_flk.override_checks()
    test_flk.api_checks()
    PASS[0] += test_flk.PASS[0]
    FAIL[0] += test_flk.FAIL[0]


def module_checks(modname):
    """Run a self-contained engine test module (issue #188 A1/A3/A4/A6): import it,
    run every *_checks() it defines, fold its PASS/FAIL tally in. Each lives in its
    own module but is invoked here so the CI test_access.py step also exercises it."""
    try:
        mod = __import__(modname)
    except Exception as e:
        print('-- %s NOT RUN (import failed: %s)' % (modname, e)); FAIL[0] += 1; return
    for fn in sorted(dir(mod)):
        if fn.endswith('_checks') and callable(getattr(mod, fn)):
            getattr(mod, fn)()
    PASS[0] += mod.PASS[0]
    FAIL[0] += mod.FAIL[0]


def main():
    pure_checks()
    store_checks('sqlite', sqlite_store())
    pg = pg_store_or_none()
    if pg is not None:
        store_checks('postgres', pg)
    tenancy_checks()
    identity_checks()
    seeding_checks()
    flk_checks()
    for _m in ('test_pft', 'test_authority', 'test_notifications', 'test_gbl',
               'test_catalog', 'test_circulation', 'test_discovery'):
        module_checks(_m)

    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
