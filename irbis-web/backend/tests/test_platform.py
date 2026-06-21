#!/usr/bin/env python3
"""Platform suite: tenant PROVISIONING + BILLING skeleton (issue #207/#209, epic
#223 — MVP Phase 2).

Three layers, mirroring the rest of the Access suite's structure:

  * PURE (always run, no DB): the billing plan catalogue — plan_modules / plan_limits,
    and check_limit allowing under / blocking over a ceiling. Plus the provisioning
    flow on the sqlite dev path (single 'public' store): provision a tenant → its
    roles/vocabs/admin account exist and the admin AUTHENTICATES; re-provision is
    idempotent.
  * ROUTES (always run, over the real ``core.Api.route()`` dispatcher, sqlite, no
    live ИРБИС): GET /api/admin/tenants, POST /api/admin/tenant, GET /api/admin/billing,
    POST /api/admin/billing/plan, POST /api/admin/billing/module — admitted for a
    super-admin (admin.db@admin) and 403 for non-admin staff / reader / guest; a
    module toggle reflects in the enabled-module list.
  * PG (run when postgres is reachable; skipped cleanly otherwise): provision a real
    isolated ``t_<slug>`` schema → its vocabularies + named admin exist in THAT schema,
    the admin authenticates against it, and the plan drives ``control.tenant_module``
    so exactly the plan's modules are enabled (and a non-plan module is disabled).
    Idempotent re-provision. Deprovision drops the schema.

Wired into the test_access.py runner (its module list) via ``module_checks`` — the
runner calls every ``*_checks()`` defined here and folds the PASS/FAIL tally in, so
the CI sqlite + postgres legs both exercise it.

Standalone:  py -3.12 tests/test_platform.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import billing
from access import provision
from access import entitlements
from access.store import AccessStore
from access.authz import GUEST_GRANTS, READER_GRANTS

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# 1. Billing plan catalogue + limit enforcement — pure, no DB.
# --------------------------------------------------------------------------- #
def billing_plan_checks():
    print('-- billing: plan catalogue (modules + limits)')
    # Every advertised plan is a known plan with sorted modules + full limit set.
    for name in ('free', 'standard', 'pro'):
        check('plan %r is known' % name, billing.is_plan(name))
        mods = billing.plan_modules(name)
        check('plan %r modules sorted+nonempty' % name,
              mods == sorted(mods) and len(mods) >= 1)
        lims = billing.plan_limits(name)
        check('plan %r limits cover every resource' % name,
              set(lims) == set(billing.LIMIT_RESOURCES))
        # Each module a plan licenses is a real product module.
        check('plan %r modules subset of ALL_MODULES' % name,
              all(m in billing.ALL_MODULES for m in mods))

    # free is a strict subset of standard is a strict subset of pro (monotone tiers).
    free, std, pro = (set(billing.plan_modules(p)) for p in ('free', 'standard', 'pro'))
    check('free strict-subset standard', free < std)
    check('standard strict-subset pro', std < pro)
    check('pro = ALL_MODULES', pro == set(billing.ALL_MODULES))

    # cataloging is paid (not in free), acquisition is pro-only.
    check('free has no cataloging', 'cataloging' not in free)
    check('acquisition is pro-only',
          'acquisition' in pro and 'acquisition' not in std)

    # pro is unlimited; free/standard have integer ceilings.
    check('pro max_records unlimited',
          billing.plan_limit('pro', 'max_records') is billing.UNLIMITED)
    check('free max_records is a finite int',
          isinstance(billing.plan_limit('free', 'max_records'), int))
    check('standard max_records > free max_records',
          billing.plan_limit('standard', 'max_records')
          > billing.plan_limit('free', 'max_records'))

    # Unknown plan raises (not silently coerced).
    try:
        billing.plan_modules('enterprise-unicorn')
        check('unknown plan raises BillingError', False)
    except billing.BillingError:
        check('unknown plan raises BillingError', True)

    # plans_catalog shape.
    cat = billing.plans_catalog()
    check('plans_catalog lists all 3', {c['plan'] for c in cat} == {'free', 'standard', 'pro'})
    check('catalog item carries plan/title/modules/limits',
          all(set(c) >= {'plan', 'title', 'modules', 'limits'} for c in cat))


def check_limit_checks():
    print('-- billing: check_limit (under allows / over blocks)')
    st = AccessStore(':memory:')
    # free.max_records = 1000. 'public' resolves to DEFAULT_PLAN, so pin the plan
    # explicitly to test the comparison deterministically.
    cap = billing.plan_limit('free', 'max_records')
    check('under limit allowed', billing.check_limit(st, 'acme', 'max_records', cap - 1, plan='free'))
    check('exactly at limit allowed', billing.check_limit(st, 'acme', 'max_records', cap, plan='free'))
    check('over limit blocked', not billing.check_limit(st, 'acme', 'max_records', cap + 1, plan='free'))

    # pro is unlimited → any count passes.
    check('pro unlimited passes a huge count',
          billing.check_limit(st, 'acme', 'max_records', 10_000_000, plan='pro'))

    # An unmodelled resource is not enforced (returns True).
    check('unknown resource not enforced',
          billing.check_limit(st, 'acme', 'max_widgets', 10**9, plan='free'))

    # hard=True raises instead of returning False when over.
    try:
        billing.check_limit(st, 'acme', 'max_records', cap + 1, plan='free', hard=True)
        check('hard over-limit raises', False)
    except billing.BillingError:
        check('hard over-limit raises', True)
    # hard=True under limit does NOT raise.
    try:
        ok = billing.check_limit(st, 'acme', 'max_records', cap, plan='free', hard=True)
        check('hard under-limit returns True', ok is True)
    except billing.BillingError:
        check('hard under-limit returns True', False)


# --------------------------------------------------------------------------- #
# 2. Provisioning on the sqlite dev path (single 'public' store).
# --------------------------------------------------------------------------- #
def provision_sqlite_checks():
    print('-- provisioning: sqlite dev path (single store)')
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    st = AccessStore(':memory:')
    report = provision.provision_tenant(
        st, 'devlib', 'Dev Library', 'libadmin',
        admin_password='pw-libadmin', plan='standard')

    check('report carries slug/name/plan', report['slug'] == 'devlib'
          and report['name'] == 'Dev Library' and report['plan'] == 'standard')
    check('sqlite path: postgres flag False', report['postgres'] is False)

    # 1. roles seeded (administrator role exists with its grants).
    roles = {r['name'] for r in st.list_roles()}
    check('administrator role seeded', 'administrator' in roles)
    check('cataloger role seeded', 'cataloger' in roles)

    # 2. vocabularies seeded (system dictionaries present + values).
    vocabs = {v['name'] for v in st.list_vocabularies()}
    check('system vocab jz.mnu seeded', 'jz.mnu' in vocabs)
    check('institution vocab kv.mnu created (empty)', 'kv.mnu' in vocabs)
    check('jz.mnu has values', len(st.vocabulary_values('jz.mnu')) > 0)
    check('institution kv.mnu seeded empty', len(st.vocabulary_values('kv.mnu')) == 0)

    # 3. admin account exists, carries administrator role, AUTHENTICATES.
    acc = st.get_account('libadmin')
    check('admin account created', acc is not None)
    check('admin has administrator role', 'administrator' in st.account_roles(acc['id']))
    check('admin authenticates with its password',
          st.authenticate('libadmin', 'pw-libadmin') is not None)
    check('admin wrong password rejected', st.authenticate('libadmin', 'nope') is None)
    check('admin password is hashed (pbkdf2), not plaintext',
          acc['pass_hash'] != 'pw-libadmin' and acc['pass_hash'].startswith('pbkdf2$'))

    # 4. plan reported; modules = standard's modules.
    check('plan modules = standard modules',
          report['modules'] == billing.plan_modules('standard'))

    # Idempotent re-provision: no raise, still one admin, still authenticates.
    report2 = provision.provision_tenant(
        st, 'devlib', 'Dev Library', 'libadmin',
        admin_password='pw-libadmin', plan='standard')
    check('re-provision idempotent (admin still authenticates)',
          st.authenticate('libadmin', 'pw-libadmin') is not None)
    check('re-provision same admin id', report2['admin']['id'] == report['admin']['id'])

    # Bad plan name → BillingError before any work.
    try:
        provision.provision_tenant(st, 'devlib', 'X', 'a', plan='nope')
        check('provision with bad plan raises', False)
    except billing.BillingError:
        check('provision with bad plan raises', True)

    # list_tenants on the dev path returns [] cleanly (no control plane).
    check('list_tenants [] on sqlite dev', provision.list_tenants() == [])


def set_tenant_plan_dev_checks():
    print('-- billing: set_tenant_plan on dev/public (validates, no-op persist)')
    st = AccessStore(':memory:')
    info = billing.set_tenant_plan(st, 'public', 'pro')
    check('public set_tenant_plan validated', info['plan'] == 'pro')
    check('public set_tenant_plan not applied (no control plane)', info['applied'] is False)
    check('public set_tenant_plan reports pro modules',
          info['modules'] == billing.plan_modules('pro'))
    # public plan reads back DEFAULT_PLAN (fail-open).
    check('public get_tenant_plan == DEFAULT_PLAN',
          billing.get_tenant_plan('public') == billing.DEFAULT_PLAN)
    # unknown plan raises.
    try:
        billing.set_tenant_plan(st, 'public', 'nope')
        check('set_tenant_plan unknown raises', False)
    except billing.BillingError:
        check('set_tenant_plan unknown raises', True)


# --------------------------------------------------------------------------- #
# 3. Routes over the real dispatcher (sqlite, no live ИРБИС).
# --------------------------------------------------------------------------- #
_DB_MENU = 'IBIS\nЭлектронный каталог\nRDR\nЧитатели\n*****\n'

# admin.db@admin is the super-admin grant the platform routes require.
SUPER_ADMIN_GRANTS = [
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]
# Real staff, but NO admin.* grant.
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]


def _api():
    os.environ['JWT_SECRET'] = 'platform-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis.read_file = lambda spec: _DB_MENU
    api.irbis.max_mfn = lambda db: 0
    return api, _core


def _super(api, login='super'):
    tok, _ = api._new_session('staff', login, SUPER_ADMIN_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _nonadmin(api, login='cat'):
    tok, _ = api._new_session('staff', login, NONADMIN_STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


def tenants_route_checks():
    print('-- routes: GET /api/admin/tenants, POST /api/admin/tenant')
    api, _core = _api()
    H = _super(api)

    st, p = api.route('GET', '/api/admin/tenants', {}, None, H)
    check('GET /api/admin/tenants -> 200', st == 200)
    tenants = p['data']['tenants']
    check('tenants is a non-empty list', isinstance(tenants, list) and len(tenants) >= 1)
    check('tenant item carries slug/name/plan',
          all(set(t) >= {'slug', 'name', 'plan'} for t in tenants))

    # Provision a tenant over HTTP (sqlite degrades to the single store, but the
    # route runs the full flow + returns the report shape).
    st, p = api.route('POST', '/api/admin/tenant', {},
                      {'slug': 'newlib', 'name': 'New Library',
                       'adminLogin': 'newadmin', 'plan': 'standard'}, H)
    check('POST /api/admin/tenant -> 200', st == 200)
    check('provision echoes slug', p['data']['slug'] == 'newlib')
    check('provision echoes plan + modules',
          p['data']['plan'] == 'standard'
          and p['data']['modules'] == billing.plan_modules('standard'))
    check('provision returns admin info', p['data']['admin']['login'] == 'newadmin')
    # The created admin (on the dev single store) can authenticate.
    st2, p2 = api.route('POST', '/api/auth/staff', {},
                        {'login': 'newadmin',
                         'password': os.environ.get('ADMIN_DEFAULT_PASSWORD', 'changeme')}, {})
    check('provisioned admin authenticates', st2 == 200 and p2['data']['kind'] == 'staff')

    # bad plan -> 400; missing slug -> 400.
    st, _ = api.route('POST', '/api/admin/tenant', {},
                      {'slug': 'x', 'plan': 'nope'}, H)
    check('provision bad plan -> 400', st == 400)
    st, _ = api.route('POST', '/api/admin/tenant', {}, {'name': 'no slug'}, H)
    check('provision missing slug -> 400', st == 400)
    # invalid slug (uppercase) -> 400 (validated by _validate_slug downstream).
    st, _ = api.route('POST', '/api/admin/tenant', {}, {'slug': 'Bad-Slug'}, H)
    check('provision invalid slug -> 400', st == 400)


def billing_route_checks():
    print('-- routes: GET /api/admin/billing, POST .../plan, POST .../module')
    api, _core = _api()
    H = _super(api)

    # Billing snapshot for the default tenant.
    st, p = api.route('GET', '/api/admin/billing', {'tenant': ['public']}, None, H)
    check('GET /api/admin/billing -> 200', st == 200)
    d = p['data']
    check('billing carries plan/limits/usage/modules',
          all(k in d for k in ('plan', 'limits', 'usage', 'modules')))
    check('billing limits cover every resource',
          set(d['limits']) == set(billing.LIMIT_RESOURCES))
    check('billing plan is a known plan', billing.is_plan(d['plan']))

    # Set a plan (dev: validated, modules echoed).
    st, p = api.route('POST', '/api/admin/billing/plan', {},
                      {'tenant': 'public', 'plan': 'pro'}, H)
    check('POST /api/admin/billing/plan -> 200', st == 200)
    check('plan route echoes pro modules',
          p['data']['plan'] == 'pro' and p['data']['modules'] == billing.plan_modules('pro'))
    check('plan route returns limits', set(p['data']['limits']) == set(billing.LIMIT_RESOURCES))
    # bad plan -> 400, missing tenant -> 400.
    st, _ = api.route('POST', '/api/admin/billing/plan', {}, {'tenant': 'public', 'plan': 'nope'}, H)
    check('plan route bad plan -> 400', st == 400)
    st, _ = api.route('POST', '/api/admin/billing/plan', {}, {'plan': 'pro'}, H)
    check('plan route missing tenant -> 400', st == 400)

    # Toggle one module. On the public/dev path it is fail-open (applied False) but
    # the route runs and the enabled-module list is returned.
    st, p = api.route('POST', '/api/admin/billing/module', {},
                      {'tenant': 'public', 'module': 'acquisition', 'enabled': False}, H)
    check('POST /api/admin/billing/module -> 200', st == 200)
    check('module route echoes the toggle',
          p['data']['module'] == 'acquisition' and p['data']['enabled'] is False)
    check('module route returns the enabled-module list', isinstance(p['data']['modules'], list))
    # missing module -> 400.
    st, _ = api.route('POST', '/api/admin/billing/module', {}, {'tenant': 'public'}, H)
    check('module route missing module -> 400', st == 400)


class _FakeUpdateResult:
    def __init__(self, mfn):
        self.data = ['%d#0' % mfn]
        self.return_code = mfn


def enforcement_route_checks():
    print('-- enforcement: save_record max_records soft check (fail-open in dev)')
    api, _core = _api()
    # A cataloger session that may write IBIS.
    tok, _ = api._new_session('staff', 'cat', [
        {'function': 'record.write', 'db': '*', 'level': 'write'},
        {'function': 'search', 'db': '*', 'level': 'read'}], tenant='public')
    H = {'authorization': 'Bearer ' + tok}

    # Stub the live server so a CREATE returns mfn=43; max_mfn high to exercise the
    # count path. On the dev 'public' tenant the plan is DEFAULT (standard, 100k cap)
    # so a create well under it is ALLOWED — proving the wiring fails open / doesn't
    # break normal writes.
    api.irbis.max_mfn = lambda db: 42
    api.irbis.update_record = lambda db, lines, lock=0, actualize=1: _FakeUpdateResult(43)
    st, p = api.route('POST', '/api/record/IBIS/0', {},
                      {'fields': [{'tag': '200', 'value': '^aТест'}]}, H)
    check('create under plan limit allowed (200)', st == 200)
    check('create returns the assigned mfn', st == 200 and p['data']['mfn'] == 43)
    check('create flagged created', st == 200 and p['data']['created'] is True)

    # If the count blows past a (hypothetical) tiny cap, check_limit blocks → 402.
    # We force it by pinning the plan via a direct check: the route uses the tenant's
    # plan, which on dev is standard; so we assert the helper itself blocks the same
    # input under 'free' (the route would 402 identically once a free plan is set).
    over = billing.plan_limit('free', 'max_records') + 1
    check('over free cap would block (helper)',
          not billing.check_limit(api.access, 'somelib', 'max_records', over, plan='free'))


PLATFORM_ROUTES = [
    ('GET', '/api/admin/tenants', None),
    ('POST', '/api/admin/tenant', {'slug': 'z', 'name': 'Z'}),
    ('GET', '/api/admin/billing', None),
    ('POST', '/api/admin/billing/plan', {'tenant': 'public', 'plan': 'pro'}),
    ('POST', '/api/admin/billing/module', {'tenant': 'public', 'module': 'opac', 'enabled': True}),
]


def platform_auth_checks():
    print('-- routes auth: super-admin only; 403 for non-admin/reader/guest/none')
    api, _core = _api()

    # Non-admin staff -> 403 on every platform route.
    HS = _nonadmin(api)
    for m, path, b in PLATFORM_ROUTES:
        st, _ = api.route(m, path, {}, b, HS)
        check('non-admin staff denied %s %s (403)' % (m, path), st == 403)

    # Guest + reader -> 403 (staff session required) everywhere.
    for label, headers in (('guest', _guest(api)), ('reader', _reader(api))):
        for m, path, b in PLATFORM_ROUTES:
            st, _ = api.route(m, path, {}, b, headers)
            check('%s denied %s %s (403)' % (label, m, path), st == 403)

    # No session -> 401/403, never 200.
    for m, path, b in PLATFORM_ROUTES:
        st, _ = api.route(m, path, {}, b, {})
        check('no session %s %s -> 401/403' % (m, path), st in (401, 403))

    # Sanity: a super-admin IS admitted.
    H = _super(api)
    st, _ = api.route('GET', '/api/admin/tenants', {}, None, H)
    check('super-admin admitted to /api/admin/tenants (200)', st == 200)


# --------------------------------------------------------------------------- #
# 4. PG leg — real schema-per-tenant provisioning + entitlement-driven billing.
# --------------------------------------------------------------------------- #
def _pg_reachable(dsn):
    try:
        import psycopg
    except Exception:
        return False
    try:
        conn = psycopg.connect(dsn, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def run_pg():
    """Provision a real tenant on PG: isolated schema + vocabs + admin + plan-driven
    entitlements. Skips cleanly when postgres/psycopg unavailable."""
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return
    from access import pgstore
    dsn = pgstore.default_pg_dsn()
    if not _pg_reachable(dsn):
        print('-- platform PG SKIPPED (postgres unreachable at %s)' % dsn.rsplit('@', 1)[-1])
        return
    print('-- platform: postgres', dsn.rsplit('@', 1)[-1])
    os.environ['ACCESS_BACKEND'] = 'postgres'
    slug = 'plat_test'
    # Clean slate.
    provision.deprovision_tenant(slug, dsn=dsn)
    try:
        public = pgstore.PgAccessStore(dsn)
        report = provision.provision_tenant(
            public, slug, 'Platform Test Lib', 'padmin',
            admin_password='pw-padmin', plan='standard', dsn=dsn)
        check('[pg] provision postgres flag True', report['postgres'] is True)

        # Isolated tenant schema: vocabs + admin live in t_<slug>.
        tstore = pgstore.make_tenant_store(slug, dsn)
        vocabs = {v['name'] for v in tstore.list_vocabularies()}
        check('[pg] system vocab seeded in tenant schema', 'jz.mnu' in vocabs)
        check('[pg] institution vocab created empty', 'kv.mnu' in vocabs
              and len(tstore.vocabulary_values('kv.mnu')) == 0)
        acc = tstore.get_account('padmin')
        check('[pg] named admin in tenant schema', acc is not None)
        check('[pg] admin has administrator role',
              'administrator' in tstore.account_roles(acc['id']))
        check('[pg] admin authenticates', tstore.authenticate('padmin', 'pw-padmin') is not None)

        # Plan drove control.tenant_module: standard's modules enabled, others off.
        enabled = set(entitlements.enabled_modules(slug, dsn))
        check('[pg] plan recorded == standard', billing.get_tenant_plan(slug, dsn) == 'standard')
        check('[pg] standard modules enabled', set(billing.plan_modules('standard')) <= enabled)
        check('[pg] non-plan module (acquisition) disabled',
              not entitlements.is_module_enabled(slug, 'acquisition', dsn))
        check('[pg] plan module (cataloging) enabled',
              entitlements.is_module_enabled(slug, 'cataloging', dsn))

        # Re-plan to pro: acquisition becomes enabled (entitlements converge).
        billing.set_tenant_plan(tstore, slug, 'pro', dsn=dsn)
        check('[pg] re-plan pro enables acquisition',
              entitlements.is_module_enabled(slug, 'acquisition', dsn))
        check('[pg] re-plan pro recorded', billing.get_tenant_plan(slug, dsn) == 'pro')

        # Single-module override on top of the plan.
        entitlements.set_module(slug, 'acquisition', False, dsn)
        check('[pg] module override disables one entitlement',
              not entitlements.is_module_enabled(slug, 'acquisition', dsn))

        # Idempotent re-provision: same admin, no raise.
        r2 = provision.provision_tenant(
            public, slug, 'Platform Test Lib', 'padmin',
            admin_password='pw-padmin', plan='standard', dsn=dsn)
        check('[pg] re-provision idempotent (admin authenticates)',
              tstore.authenticate('padmin', 'pw-padmin') is not None)
        check('[pg] re-provision same admin id', r2['admin']['id'] == report['admin']['id'])

        # list_tenants shows it with its plan.
        rows = {t['slug']: t for t in provision.list_tenants(dsn=dsn)}
        check('[pg] provisioned tenant listed', slug in rows)
        check('[pg] listed tenant carries a plan', rows.get(slug, {}).get('plan') in billing.PLANS)
    finally:
        provision.deprovision_tenant(slug, dsn=dsn)
        os.environ['ACCESS_BACKEND'] = 'sqlite'
    # Deprovision dropped the schema.
    check('[pg] deprovision removed the tenant',
          slug not in {t['slug'] for t in provision.list_tenants(dsn=dsn)})


def main():
    billing_plan_checks()
    check_limit_checks()
    provision_sqlite_checks()
    set_tenant_plan_dev_checks()
    tenants_route_checks()
    billing_route_checks()
    enforcement_route_checks()
    platform_auth_checks()
    run_pg()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
