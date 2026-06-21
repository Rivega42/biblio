#!/usr/bin/env python3
"""Identity / Tenancy / Licensing tests (issue #101, I1).

Covers the three new mechanisms layered on the merged Access store:

  1. JWT sessions — dependency-free HS256 issue->verify round-trip, and that a
     TAMPERED or EXPIRED token is rejected (-> no session -> 401 at the edge).
  2. Tenant context — the JWT carries a `tenant` claim; the session is scoped to
     it; on PostgreSQL the per-tenant store sees only that tenant's data.
  3. Entitlements (licensing) — a request to a DISABLED module is refused even
     with a valid grant (grants = can-do, entitlements = is-licensed). On the
     dev/`public` path entitlements fail open so the guest flow keeps working.

Backends:
  * sqlite / pure  — JWT round-trip, tamper/expiry rejection, public fail-open
    entitlement, and the _guard entitlement-gating path with a monkeypatched
    entitlement check (no DB needed). Always run.
  * postgres only  — tenant-claim data scoping and real `control.tenant_module`
    gating. Runs when ACCESS_BACKEND=postgres (or ACCESS_TEST_PG=1) AND a PG is
    reachable; otherwise SKIPPED cleanly (never red-flags the sqlite dev box).

Invoked by the test_access.py runner (identity_checks) so the CI postgres step
exercises it with NO .github/ change.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import jwt as _jwt
from access import entitlements
from access.authz import authorize, GUEST_GRANTS

PASS = [0]
FAIL = [0]

SECRET = 'unit-test-secret'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# 1. JWT — pure, backend-independent.
# --------------------------------------------------------------------------- #
def jwt_checks():
    print('-- jwt (HS256, dep-free)')
    claims = {'sub': 'admin', 'tenant': 'acme', 'kind': 'staff',
              'grants': [{'function': 'search', 'db': '*', 'level': 'read'}]}
    tok = _jwt.encode(claims, SECRET)
    check('token is a plain string (bearer)', isinstance(tok, str) and tok.count('.') == 2)

    out = _jwt.decode(tok, SECRET)
    check('round-trip preserves sub', out['sub'] == 'admin')
    check('round-trip preserves tenant', out['tenant'] == 'acme')
    check('round-trip preserves kind', out['kind'] == 'staff')
    check('round-trip preserves grants', out['grants'] == claims['grants'])
    check('encode sets iat/exp', 'iat' in out and 'exp' in out and out['exp'] > out['iat'])

    # tampered payload — flip one char in the payload segment -> signature mismatch
    h, p, s = tok.split('.')
    bad_char = 'B' if p[5] != 'B' else 'C'
    tampered = '%s.%s.%s' % (h, p[:5] + bad_char + p[6:], s)
    rejected = False
    try:
        _jwt.decode(tampered, SECRET)
    except _jwt.JwtError:
        rejected = True
    check('tampered payload rejected', rejected)

    # tampered signature
    rejected = False
    try:
        _jwt.decode('%s.%s.%s' % (h, p, s[:-3] + ('xyz' if s[-3:] != 'xyz' else 'abc')), SECRET)
    except _jwt.JwtError:
        rejected = True
    check('tampered signature rejected', rejected)

    # wrong secret
    rejected = False
    try:
        _jwt.decode(tok, 'other-secret')
    except _jwt.JwtError:
        rejected = True
    check('wrong-secret token rejected', rejected)

    # expired token (exp in the past)
    expired = _jwt.encode({'sub': 'x'}, SECRET, ttl_seconds=-10)
    rejected = False
    try:
        _jwt.decode(expired, SECRET)
    except _jwt.JwtError:
        rejected = True
    check('expired token rejected', rejected)

    # not-yet-expired token with injected now still valid; same token expired by clock
    near = _jwt.encode({'sub': 'x'}, SECRET, ttl_seconds=5, now=1000)
    check('valid before exp', _jwt.decode(near, SECRET, now=1004)['sub'] == 'x')
    rejected = False
    try:
        _jwt.decode(near, SECRET, now=1006)
    except _jwt.JwtError:
        rejected = True
    check('expired by injected clock rejected', rejected)

    # alg downgrade ("alg":"none") must not be accepted — pinned to HS256 on decode
    import base64 as _b64
    import json as _json
    none_header = _b64.urlsafe_b64encode(
        _json.dumps({'alg': 'none', 'typ': 'JWT'}).encode()).rstrip(b'=').decode()
    none_payload = _b64.urlsafe_b64encode(
        _json.dumps({'sub': 'attacker'}).encode()).rstrip(b'=').decode()
    rejected = False
    try:
        _jwt.decode('%s.%s.' % (none_header, none_payload), SECRET)
    except _jwt.JwtError:
        rejected = True
    check('alg=none downgrade rejected', rejected)

    # malformed token
    rejected = False
    try:
        _jwt.decode('not-a-jwt', SECRET)
    except _jwt.JwtError:
        rejected = True
    check('malformed token rejected', rejected)


# --------------------------------------------------------------------------- #
# 2. Api session + entitlement gating — uses a constructed Api (no live IRBIS:
#    the constructor does not connect; we only call _new_session/_session/_guard).
# --------------------------------------------------------------------------- #
def api_session_checks():
    print('-- api session + guard')
    os.environ['JWT_SECRET'] = SECRET
    import importlib
    import core as _core
    importlib.reload(_core)            # pick up JWT_SECRET set above
    api = _core.Api()

    # issue a guest session -> verify it round-trips through _session
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    sess = api._session(tok)
    check('guest token verifies to session', sess is not None and sess['kind'] == 'guest')
    check('session carries tenant claim', sess['tenant'] == 'public')
    check('session actor == sub', sess['actor'] == 'guest')

    # tampered token -> no session (the edge maps None -> 401)
    h, p, s = tok.split('.')
    bad = '%s.%s.%s' % (h, p, s[:-2] + ('zz' if s[-2:] != 'zz' else 'aa'))
    check('tampered token -> no session (401)', api._session(bad) is None)

    # expired token -> no session
    expired = _jwt.encode({'sub': 'guest', 'tenant': 'public', 'kind': 'guest',
                           'grants': GUEST_GRANTS}, api.jwt_secret, ttl_seconds=-5)
    check('expired token -> no session (401)', api._session(expired) is None)

    # _guard: a guest can search on the public path (entitlements fail open)
    guard_ok = True
    try:
        api._guard(sess, 'search', 'IBIS', 'read')
    except _core.Denied:
        guard_ok = False
    check('guest search allowed on public (grant + open entitlement)', guard_ok)

    # _guard: grant gate still bites (guest cannot order/write)
    denied = False
    try:
        api._guard(sess, 'order', 'IBIS', 'write')
    except _core.Denied as d:
        denied = d.status == 403
    check('guest order denied by grant gate (403)', denied)

    # ENTITLEMENT gate is separate from grants: monkeypatch is_module_enabled to
    # disable the 'opac' module -> even a VALID search grant is refused.
    staff_grants = [{'function': 'search', 'db': '*', 'level': 'read'}]
    stok, ssess = api._new_session('staff', 'admin', staff_grants, tenant='acme')
    # sanity: with entitlements open, search is allowed
    open_ok = True
    try:
        api._guard(ssess, 'search', 'IBIS', 'read')
    except _core.Denied:
        open_ok = False
    check('valid grant allowed when module licensed', open_ok)

    orig = _core.entitlements.is_module_enabled
    _core.entitlements.is_module_enabled = (
        lambda tenant, module, dsn=None: not (tenant == 'acme' and module == 'opac'))
    try:
        gated = False
        try:
            api._guard(ssess, 'search', 'IBIS', 'read')
        except _core.Denied as d:
            gated = d.status == 403 and 'module' in d.message
        check('disabled module refused despite valid grant (403)', gated)
    finally:
        _core.entitlements.is_module_enabled = orig


# --------------------------------------------------------------------------- #
# 3. Entitlements default / public fail-open — pure (no DB).
# --------------------------------------------------------------------------- #
def entitlement_default_checks():
    print('-- entitlements (public fail-open)')
    check('public is always licensed', entitlements.is_module_enabled('public', 'cataloging'))
    check('empty tenant is always licensed', entitlements.is_module_enabled('', 'cataloging'))
    check('public enabled_modules == defaults',
          entitlements.enabled_modules('public') == list(entitlements.DEFAULT_MODULES))
    check('DEFAULT_MODULES non-empty', len(entitlements.DEFAULT_MODULES) >= 3)


# --------------------------------------------------------------------------- #
# 4. PostgreSQL: tenant-claim data scoping + real tenant_module gating.
# --------------------------------------------------------------------------- #
A_SLUG, B_SLUG = 'idn_a', 'idn_b'


def pg_reachable(dsn):
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
        print('-- identity PG suite SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return False


def pg_checks(dsn):
    print('-- identity: postgres', dsn.rsplit('@', 1)[-1])
    from access import pgstore

    # clean slate
    pgstore.deprovision_tenant(A_SLUG, dsn)
    pgstore.deprovision_tenant(B_SLUG, dsn)

    sa = pgstore.provision_tenant(A_SLUG, 'Identity A', 'публичная', dsn)
    sb = pgstore.provision_tenant(B_SLUG, 'Identity B', 'школьная', dsn)

    # --- tenant-claim data scoping: a distinct account per tenant, invisible across ---
    sa.create_account('alice', 'pw_a', 'Alice')
    sb.create_account('bob', 'pw_b', 'Bob')
    check('tenant A sees its own account', sa.authenticate('alice', 'pw_a') is not None)
    check('tenant A cannot see B account', sa.get_account('bob') is None)
    check('tenant B cannot see A account', sb.get_account('alice') is None)

    # --- entitlements seeded enabled by provisioning ---
    mods_a = entitlements.enabled_modules(A_SLUG, dsn)
    check('provisioning seeds default modules enabled',
          set(entitlements.DEFAULT_MODULES).issubset(set(mods_a)))
    check('is_module_enabled True for seeded module',
          entitlements.is_module_enabled(A_SLUG, 'cataloging', dsn))

    # --- disable one module -> is_module_enabled False, dropped from the list ---
    entitlements.set_module(A_SLUG, 'cataloging', False, dsn)
    check('disabled module -> is_module_enabled False',
          entitlements.is_module_enabled(A_SLUG, 'cataloging', dsn) is False)
    check('disabled module dropped from enabled list',
          'cataloging' not in entitlements.enabled_modules(A_SLUG, dsn))
    # other tenant unaffected (isolation of the licensing axis too)
    check('other tenant module unaffected',
          entitlements.is_module_enabled(B_SLUG, 'cataloging', dsn) is True)

    # --- GATING THROUGH _guard: a valid grant on a DISABLED module is refused ---
    os.environ['JWT_SECRET'] = SECRET
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    # session for tenant A with a real record.write grant (cataloging module)
    grants = [{'function': 'record.write', 'db': 'IBIS', 'level': 'write'}]
    _tok, sess = api._new_session('staff', 'alice', grants, tenant=A_SLUG)

    # cataloging is DISABLED for A -> record.write refused even with the grant
    refused = False
    try:
        api._guard(sess, 'record.write', 'IBIS', 'write')
    except _core.Denied as d:
        refused = d.status in (403, 404) and 'module' in d.message
    check('disabled module refused via _guard despite grant', refused)

    # re-enable -> now the grant passes the entitlement gate
    entitlements.set_module(A_SLUG, 'cataloging', True, dsn)
    passed = True
    try:
        api._guard(sess, 'record.write', 'IBIS', 'write')
    except _core.Denied:
        passed = False
    check('re-enabled module allows the grant through', passed)

    # cleanup
    pgstore.deprovision_tenant(A_SLUG, dsn)
    pgstore.deprovision_tenant(B_SLUG, dsn)


def run_pg():
    dsn = entitlements.default_pg_dsn()
    if not pg_reachable(dsn):
        return
    pg_checks(dsn)


def main():
    jwt_checks()
    api_session_checks()
    entitlement_default_checks()
    run_pg()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
