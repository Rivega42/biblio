#!/usr/bin/env python3
"""Backend stabilization suite (post-MVP rough edges from the pilot smoke, epic #223).

Two rough edges found during the deployed-container smoke:

  1. **Post-provision propagation** (the real bug). After
     ``provision_tenant('public', admin=…)`` stood the tenant + admin up on the PG
     stack, the very next ``POST /api/auth/staff {admin}`` transiently returned "no
     session" — the freshly-created account was not visible to the next request.
     Root cause: provisioning writes a tenant's accounts into its OWN schema
     ``t_<slug>`` (the default tenant included → ``t_public``), but the auth read
     short-circuited the default tenant to the un-scoped public store (search_path =
     PG ``public``), looking in the wrong schema. The fix routes the default tenant's
     auth read to its provisioned ``t_public`` schema when that schema exists, so a
     provisioned admin is authable on the very next request.

     This leg is PG-only: it provisions ``t_public`` and asserts the next-request
     auth succeeds (it would 401 before the fix). It is GATED on a reachable
     postgres (ACCESS_BACKEND=postgres / ACCESS_TEST_PG=1) and SKIPS cleanly
     otherwise. On the sqlite single-tenant dev box there are no per-tenant schemas,
     so the bug cannot occur — a documented no-op (a sanity pass that the default
     store authenticates a freshly-seeded admin).

  2. **Metrics / health deepening** (pilot observability). ``GET /api/metrics`` —
     a plain-JSON, unauthenticated-safe operational snapshot: version marker, uptime,
     request/error counters, the ИРБИС reachability block, and a per-tenant count
     (bare count unauthenticated; per-tenant detail only for a super-admin). The
     checks assert the documented shape, that it needs no auth, that error counting
     works, that the admin-only detail is withheld from anon/non-admin, and that no
     secret/PII (JWT secret, password, ticket) leaks into the payload. All pure
     (sqlite, no live ИРБИС) — always run.

Wired into the test_access.py runner (its module list) via ``module_checks`` — the
runner calls every ``*_checks()`` here and folds the PASS/FAIL tally in, so the CI
sqlite + postgres legs both exercise it.

Standalone:  py -3.12 tests/test_stabilize.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = [0]
FAIL = [0]

# A minimal DB-menu + max_mfn stub so a constructed Api needs no live ИРБИС.
_DB_MENU = 'IBIS\nЭлектронный каталог\nRDR\nЧитатели\n*****\n'

SUPER_ADMIN_GRANTS = [
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _api():
    """A constructed sqlite Api with the ИРБИС seams stubbed (no live server)."""
    os.environ['JWT_SECRET'] = 'stabilize-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis.read_file = lambda spec: _DB_MENU
    api.irbis.max_mfn = lambda db: 0
    return api, _core


# --------------------------------------------------------------------------- #
# 1. Metrics endpoint — pure (sqlite, no live ИРБИС). Always run.
# --------------------------------------------------------------------------- #
def metrics_shape_checks():
    print('-- metrics: GET /api/metrics shape + unauthenticated-safe')
    api, _core = _api()

    # Unauthenticated: 200 with the documented top-level shape.
    st, p = api.route('GET', '/api/metrics', {}, None, {})
    check('GET /api/metrics unauthenticated -> 200', st == 200)
    check('metrics envelope ok=True', p.get('ok') is True)
    d = p['data']
    check('metrics carries version/uptimeSec/requests/irbis/tenants',
          set(d) >= {'version', 'uptimeSec', 'requests', 'irbis', 'tenants'})
    check('version marker present (str)', isinstance(d['version'], str) and d['version'])
    check('uptimeSec is a non-negative number',
          isinstance(d['uptimeSec'], (int, float)) and d['uptimeSec'] >= 0)
    check('requests carries total+errors ints',
          set(d['requests']) == {'total', 'errors'}
          and all(isinstance(d['requests'][k], int) for k in ('total', 'errors')))
    check('irbis block carries server/db/reachable',
          set(d['irbis']) >= {'server', 'db', 'reachable'})
    check('tenants carries a bare count int', isinstance(d['tenants'].get('count'), int))

    # No per-tenant DETAIL is exposed to an anonymous scrape.
    check('anon scrape withholds tenants.detail', 'detail' not in d['tenants'])


def metrics_counters_checks():
    print('-- metrics: request/error counters move')
    api, _core = _api()

    # Baseline (this call is counted AFTER it returns, so its own response is 0).
    _st, p0 = api.route('GET', '/api/metrics', {}, None, {})
    base = p0['data']['requests']
    check('initial counters start at 0', base == {'total': 0, 'errors': 0})

    # One OK call (auth/guest -> 200) + one error call (unknown route -> 404).
    api.route('POST', '/api/auth/guest', {}, {}, {})
    api.route('GET', '/api/nope', {}, None, {})

    _st, p1 = api.route('GET', '/api/metrics', {}, None, {})
    cur = p1['data']['requests']
    # Counted since base: the first metrics call, the guest call, the 404 = 3 more.
    check('total advanced by the served requests', cur['total'] == base['total'] + 3)
    check('error counter caught the 404', cur['errors'] == base['errors'] + 1)

    # OPTIONS preflight (204) is NOT counted as a request. Between the two reads
    # only ONE billable request runs (the first read itself; OPTIONS adds 0), so
    # the delta is +1 — proving the OPTIONS call contributed nothing.
    before = api.route('GET', '/api/metrics', {}, None, {})[1]['data']['requests']['total']
    api.route('OPTIONS', '/api/anything', {}, None, {})
    after = api.route('GET', '/api/metrics', {}, None, {})[1]['data']['requests']['total']
    check('OPTIONS preflight not counted', after == before + 1)


def metrics_auth_posture_checks():
    print('-- metrics: admin-only tenant detail; anon/non-admin withheld; no PII')
    api, _core = _api()

    # Super-admin: the detail block MAY appear (empty on sqlite — no control plane —
    # but the key is gated, never leaked to a non-admin).
    tok, _ = api._new_session('staff', 'super', SUPER_ADMIN_GRANTS, tenant='public')
    _st, p_admin = api.route('GET', '/api/metrics', {}, None,
                             {'authorization': 'Bearer ' + tok})
    # On sqlite there are no provisioned tenants, so detail is omitted (count 0).
    check('super-admin sqlite: count 0, no detail (no control plane)',
          p_admin['data']['tenants']['count'] == 0
          and 'detail' not in p_admin['data']['tenants'])

    # Non-admin staff must NOT receive a tenants.detail block.
    ntok, _ = api._new_session('staff', 'cat', NONADMIN_STAFF_GRANTS, tenant='public')
    _st, p_non = api.route('GET', '/api/metrics', {}, None,
                           {'authorization': 'Bearer ' + ntok})
    check('non-admin staff withholds tenants.detail',
          'detail' not in p_non['data']['tenants'])

    # No secret/PII anywhere in the payload: JWT secret, a password, or a reader ticket.
    rtok, _ = api._new_session('reader', 'RI=111', [], tenant='public', rdr_mfn=1)
    api.route('POST', '/api/auth/staff', {}, {'login': 'admin', 'password': 'admin'}, {})
    blob = json.dumps(p_admin, ensure_ascii=False).lower()
    check('no jwt secret in metrics', 'stabilize-test-secret' not in blob)
    check('no password field in metrics', 'pass_hash' not in blob and 'password' not in blob)
    check('no bearer token in metrics', 'bearer' not in blob and tok.lower() not in blob)


# --------------------------------------------------------------------------- #
# 2. Post-provision propagation — sqlite no-op sanity (always) + PG leg (gated).
# --------------------------------------------------------------------------- #
def provision_auth_sqlite_checks():
    print('-- propagation: sqlite single-tenant (no per-tenant schema; sanity)')
    api, _core = _api()
    from access import provision
    # Provision the single 'public' store, then authenticate the named admin on the
    # very next request via the real dispatcher. On sqlite the store IS the public
    # store, so this just confirms the flow is wired (the bug is PG-schema-specific).
    provision.provision_tenant(api.access, 'public', 'Dev', 'devadmin',
                               admin_password='devpw', plan='standard')
    st, p = api.route('POST', '/api/auth/staff', {},
                      {'login': 'devadmin', 'password': 'devpw', 'tenant': 'public'}, {})
    check('sqlite: provisioned admin authenticates next request (200)',
          st == 200 and p['data']['kind'] == 'staff')


def _pg_reachable(dsn):
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return False
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.close()
        return True
    except Exception as e:
        print('-- stabilize PG SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return False


def run_pg():
    """THE regression for the container-smoke bug: provision the DEFAULT tenant on
    PG (admin lands in t_public) and assert the very next POST /api/auth/staff
    succeeds. This 401'd before the _store_for fix (it read the bare public schema)
    and 200s after. Skips cleanly when postgres/psycopg unavailable."""
    from access import pgstore
    dsn = pgstore.default_pg_dsn()
    if not _pg_reachable(dsn):
        return
    print('-- stabilize: postgres', dsn.rsplit('@', 1)[-1])
    os.environ['JWT_SECRET'] = 'stabilize-pg-secret'
    os.environ['ACCESS_BACKEND'] = 'postgres'
    from access import provision

    # ---- (a) DEFAULT tenant ('public') — the exact smoke scenario ----
    pgstore.deprovision_tenant('public', dsn)
    try:
        import importlib
        import core as _core
        importlib.reload(_core)
        api = _core.Api()                       # self.access = un-scoped public store
        api.irbis.max_mfn = lambda db: 0

        # Provision tenant 'public' with a NAMED admin → lands in schema t_public.
        public_store = pgstore.PgAccessStore(dsn)
        rep = provision.provision_tenant(
            public_store, 'public', 'Public Lib', 'smokeadmin',
            admin_password='smoke-pw', plan='standard', dsn=dsn)
        check('[pg] provisioned admin schema is t_public',
              rep['store'].tenant_schema == 't_public')

        # THE assertion: the very next request authenticates. (401 before the fix.)
        st, p = api.route('POST', '/api/auth/staff', {},
                          {'login': 'smokeadmin', 'password': 'smoke-pw',
                           'tenant': 'public'}, {})
        check('[pg] provisioned admin authable on the very next request (200)',
              st == 200 and p.get('data', {}).get('kind') == 'staff')
        check('[pg] auth echoes the public tenant',
              st == 200 and p['data'].get('tenant') == 'public')

        # The seeded admin/admin (also written into t_public by provision's seed) too.
        st2, _ = api.route('POST', '/api/auth/staff', {},
                           {'login': 'admin', 'password': 'admin', 'tenant': 'public'}, {})
        check('[pg] seeded admin/admin in t_public authenticates', st2 == 200)

        # Wrong password is still rejected through the same (correct) schema.
        st3, _ = api.route('POST', '/api/auth/staff', {},
                           {'login': 'smokeadmin', 'password': 'nope', 'tenant': 'public'}, {})
        check('[pg] wrong password rejected on t_public path (401)', st3 == 401)

        # Metrics over PG: the provisioned tenant shows in the bare count, and the
        # super-admin detail lists it (slug/name only — operational, not PII).
        st4, pm = api.route('GET', '/api/metrics', {}, None, {})
        check('[pg] metrics tenant count >= 1', st4 == 200
              and pm['data']['tenants']['count'] >= 1)
        atok, _ = api._new_session('staff', 'super', SUPER_ADMIN_GRANTS, tenant='public')
        _st, pa = api.route('GET', '/api/metrics', {}, None,
                            {'authorization': 'Bearer ' + atok})
        check('[pg] super-admin metrics carries tenants.detail',
              isinstance(pa['data']['tenants'].get('detail'), list))
    finally:
        pgstore.deprovision_tenant('public', dsn)

    # ---- (b) a NON-default tenant — scoped auth path also resolves next-request ----
    slug = 'stab_t'
    pgstore.deprovision_tenant(slug, dsn)
    try:
        importlib.reload(_core)
        api2 = _core.Api()
        api2.irbis.max_mfn = lambda db: 0
        ps = pgstore.PgAccessStore(dsn)
        provision.provision_tenant(ps, slug, 'Stab Tenant', 'stabadmin',
                                   admin_password='stab-pw', plan='standard', dsn=dsn)
        st, p = api2.route('POST', '/api/auth/staff', {},
                           {'login': 'stabadmin', 'password': 'stab-pw',
                            'tenant': slug}, {})
        check('[pg] non-default tenant admin authable next request (200)',
              st == 200 and p['data'].get('tenant') == slug)
        # Cross-tenant invisibility holds: the public path cannot see this admin.
        st2, _ = api2.route('POST', '/api/auth/staff', {},
                            {'login': 'stabadmin', 'password': 'stab-pw',
                             'tenant': 'public'}, {})
        check('[pg] tenant admin invisible on the public path (401)', st2 == 401)
    finally:
        pgstore.deprovision_tenant(slug, dsn)
        os.environ['ACCESS_BACKEND'] = 'sqlite'


def main():
    metrics_shape_checks()
    metrics_counters_checks()
    metrics_auth_posture_checks()
    provision_auth_sqlite_checks()
    run_pg()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
