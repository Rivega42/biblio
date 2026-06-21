#!/usr/bin/env python3
"""HTTP-route tests for the АРМ Администратор (#187, epic #223).

The administration workstation over the EXISTING access store (staff accounts,
roles/grants, audit log, DB list). THIS suite proves that surface is reachable
over HTTP — every assertion goes through the real ``core.Api.route()`` dispatcher
(the same path server.py / app_aiohttp.py use), with a constructed ``Api`` (the
constructor does NOT connect to ИРБИС).

Covered (the task contract, all through route()):
  * ADMIN lists accounts (GET /api/admin/users) — the seeded admin/librarian show
    up with their roles + effective grants;
  * ADMIN creates a user (POST /api/admin/users) with roles -> it then appears in
    the list with those roles, AND the created user can AUTHENTICATE (the password
    was hashed the same way seed.py hashes — pbkdf2, never plaintext);
  * ADMIN replaces a user's roles (POST /api/admin/users/roles) and toggles active
    (POST /api/admin/users/active) — disabling blocks authentication;
  * ADMIN reads roles (GET /api/admin/roles) with their grants;
  * ADMIN reads the audit log (GET /api/admin/audit) — an action issued first shows
    up, newest-first, capped by ?limit=;
  * ADMIN reads the full DB list (GET /api/admin/databases) — every base (staff
    view), not just the public OPAC ones;
  * a NON-ADMIN STAFF session gets 403 on every admin route (has no admin.* grant);
  * GUEST/READER get 403, and no session gets 401/403 — never 200.

Wired into the test_access.py runner (module list) so the CI sqlite + postgres
legs both run it. Standalone-runnable in the house style:
  py tests/test_admin_routes.py  -> ok ... + "N passed, M failed" + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


# An administrator session carries admin.users + admin.db at the admin level (the
# seeded 'administrator' role; seed.py). We mint them onto the token directly so the
# suite needs no DB role wiring — same technique as test_circ_routes.STAFF_GRANTS.
ADMIN_GRANTS = [
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    # plus the everyday read grants an admin role also carries (not needed by the
    # admin routes, but realistic — proves the guard keys on admin.* specifically).
    {'function': 'search', 'db': '*', 'level': 'read'},
]

# A non-admin staff session (e.g. a cataloger): real staff, but NO admin.* grant.
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]

# A fake database menu (code\nname pairs, '*****' terminator) so /api/admin/databases
# works without a live ИРБИС: we stub api.irbis.read_file to return it. IBIS is on the
# public allow-list; RDR/PAY are service bases (non-public) — the admin view must show
# ALL of them (unlike a reader, who would only see IBIS).
_DB_MENU = 'IBIS\nЭлектронный каталог\nRDR\nЧитатели\nPAY\nОплата\n*****\n'


def _api():
    """A constructed Api with NO live ИРБИС and a fresh in-memory access store.

    The access store is rebuilt over ':memory:' so each run is isolated (and the
    seed runs into it via core.Api.__init__). ``irbis.read_file`` is stubbed to a
    fake DB menu (no live server) and ``max_mfn`` to 0 so /api/admin/databases is
    deterministic without a server."""
    os.environ['JWT_SECRET'] = 'admin-routes-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis.read_file = lambda spec: _DB_MENU
    api.irbis.max_mfn = lambda db: 0
    return api, _core


def _admin(api, login='admin-acct'):
    tok, _ = api._new_session('staff', login, ADMIN_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _nonadmin_staff(api, login='cat-acct'):
    tok, _ = api._new_session('staff', login, NONADMIN_STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest_headers(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader_headers(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


# --------------------------------------------------------------------------- #
# 1. Users: list, create (with roles), authenticate the created user.
# --------------------------------------------------------------------------- #
def users_route_checks():
    print('-- admin routes: list / create users (+ created user authenticates)')
    api, _core = _api()
    H = _admin(api)

    # The seed put admin + librarian into the store — they appear in the list.
    st, p = api.route('GET', '/api/admin/users', {}, None, H)
    check('GET /api/admin/users -> 200', st == 200)
    users = p['data']['users']
    check('users is a list', isinstance(users, list) and len(users) >= 2)
    logins = {u['login'] for u in users}
    check('seeded admin listed', 'admin' in logins)
    check('seeded librarian listed', 'librarian' in logins)
    admin_row = next(u for u in users if u['login'] == 'admin')
    check('user item carries id/login/fullName/active',
          isinstance(admin_row['id'], int) and 'login' in admin_row
          and 'fullName' in admin_row and admin_row['active'] is True)
    check('seeded admin shows the administrator role',
          'administrator' in admin_row['roles'])
    check('seeded admin grants include admin.users',
          any(g['function'] == 'admin.users' for g in admin_row['grants']))

    # CREATE a new user with a role + an explicit password.
    st, p = api.route('POST', '/api/admin/users', {},
                      {'login': 'newcat', 'fullName': 'Новый каталогизатор',
                       'password': 'pw-newcat', 'roles': ['cataloger']}, H)
    check('POST /api/admin/users -> 200', st == 200)
    new_id = p['data']['id']
    check('create returns an id', isinstance(new_id, int))
    check('create echoes assigned roles', p['data']['roles'] == ['cataloger'])

    # It now appears in the list WITH the assigned role.
    st, p = api.route('GET', '/api/admin/users', {}, None, H)
    row = next((u for u in p['data']['users'] if u['login'] == 'newcat'), None)
    check('created user now appears in the list', row is not None)
    check('created user carries the cataloger role', row and row['roles'] == ['cataloger'])
    check('created user is active by default', row and row['active'] is True)
    check('created user full name persisted',
          row and row['fullName'] == 'Новый каталогизатор')

    # The created user can AUTHENTICATE — the password was hashed (pbkdf2), not
    # stored plaintext, exactly as seed.py creates accounts.
    st, p = api.route('POST', '/api/auth/staff', {},
                      {'login': 'newcat', 'password': 'pw-newcat'}, {})
    check('created user authenticates (200)', st == 200)
    check('auth returns a staff token', st == 200 and p['data']['kind'] == 'staff')
    # The stored hash is NOT the plaintext password (defence-in-depth assertion).
    acc = api.access.get_account('newcat')
    check('password is hashed, never plaintext',
          acc['pass_hash'] != 'pw-newcat' and acc['pass_hash'].startswith('pbkdf2$'))

    # Wrong password still fails for the created user.
    st, _ = api.route('POST', '/api/auth/staff', {},
                      {'login': 'newcat', 'password': 'WRONG'}, {})
    check('created user wrong password -> 401', st == 401)

    # Duplicate login -> 409 (not a silent overwrite).
    st, _ = api.route('POST', '/api/admin/users', {},
                      {'login': 'newcat', 'password': 'x'}, H)
    check('duplicate login -> 409', st == 409)

    # Missing login -> 400.
    st, _ = api.route('POST', '/api/admin/users', {}, {'password': 'x'}, H)
    check('create without login -> 400', st == 400)


# --------------------------------------------------------------------------- #
# 2. Role replace + active toggle.
# --------------------------------------------------------------------------- #
def roles_and_active_checks():
    print('-- admin routes: replace roles / toggle active')
    api, _core = _api()
    H = _admin(api)

    # Make a user with one role.
    st, p = api.route('POST', '/api/admin/users', {},
                      {'login': 'multi', 'password': 'pw', 'roles': ['cataloger']}, H)
    uid = p['data']['id']
    check('seed user created', st == 200)

    # REPLACE roles -> administrator only.
    st, p = api.route('POST', '/api/admin/users/roles', {},
                      {'userId': uid, 'roles': ['administrator']}, H)
    check('POST /api/admin/users/roles -> 200', st == 200)
    check('roles replaced (administrator only)', p['data']['roles'] == ['administrator'])
    st, p = api.route('GET', '/api/admin/users', {}, None, H)
    row = next(u for u in p['data']['users'] if u['login'] == 'multi')
    check('list reflects replaced role', row['roles'] == ['administrator'])
    check('replaced role brings its grants (admin.db)',
          any(g['function'] == 'admin.db' for g in row['grants']))
    check('old cataloger role no longer present', 'cataloger' not in row['roles'])

    # REPLACE with empty -> no roles.
    st, p = api.route('POST', '/api/admin/users/roles', {},
                      {'userId': uid, 'roles': []}, H)
    check('replace with [] clears roles', st == 200 and p['data']['roles'] == [])

    # roles on an unknown user -> 404.
    st, _ = api.route('POST', '/api/admin/users/roles', {},
                      {'userId': 999999, 'roles': []}, H)
    check('roles on unknown user -> 404', st == 404)
    # roles without userId -> 400.
    st, _ = api.route('POST', '/api/admin/users/roles', {}, {'roles': []}, H)
    check('roles without userId -> 400', st == 400)

    # ACTIVE toggle: disable blocks authentication, re-enable restores it.
    api.route('POST', '/api/admin/users/roles', {},
              {'userId': uid, 'roles': ['cataloger']}, H)   # give it a role again
    st, _ = api.route('POST', '/api/auth/staff', {},
                      {'login': 'multi', 'password': 'pw'}, {})
    check('active user authenticates before disable', st == 200)

    st, p = api.route('POST', '/api/admin/users/active', {},
                      {'userId': uid, 'active': False}, H)
    check('POST /api/admin/users/active(false) -> 200', st == 200 and p['data']['active'] is False)
    st, _ = api.route('POST', '/api/auth/staff', {},
                      {'login': 'multi', 'password': 'pw'}, {})
    check('disabled user cannot authenticate (401)', st == 401)
    st, p = api.route('GET', '/api/admin/users', {}, None, H)
    row = next(u for u in p['data']['users'] if u['login'] == 'multi')
    check('list shows the user inactive', row['active'] is False)

    st, p = api.route('POST', '/api/admin/users/active', {},
                      {'userId': uid, 'active': True}, H)
    check('re-enable -> 200', st == 200 and p['data']['active'] is True)
    st, _ = api.route('POST', '/api/auth/staff', {},
                      {'login': 'multi', 'password': 'pw'}, {})
    check('re-enabled user authenticates again', st == 200)

    # active on unknown user -> 404; without userId -> 400.
    st, _ = api.route('POST', '/api/admin/users/active', {},
                      {'userId': 999999, 'active': True}, H)
    check('active on unknown user -> 404', st == 404)
    st, _ = api.route('POST', '/api/admin/users/active', {}, {'active': True}, H)
    check('active without userId -> 400', st == 400)


# --------------------------------------------------------------------------- #
# 3. Roles list.
# --------------------------------------------------------------------------- #
def roles_list_checks():
    print('-- admin routes: GET /api/admin/roles')
    api, _core = _api()
    H = _admin(api)
    st, p = api.route('GET', '/api/admin/roles', {}, None, H)
    check('GET /api/admin/roles -> 200', st == 200)
    roles = p['data']['roles']
    names = {r['name'] for r in roles}
    check('seeded roles present',
          {'administrator', 'cataloger', 'reader-service'} <= names)
    admin_role = next(r for r in roles if r['name'] == 'administrator')
    check('role carries a grants list', isinstance(admin_role['grants'], list))
    check('administrator role holds admin.users grant',
          any(g['function'] == 'admin.users' and g['level'] == 'admin'
              for g in admin_role['grants']))


# --------------------------------------------------------------------------- #
# 4. Audit log — issue an action first, then see it logged (newest-first, capped).
# --------------------------------------------------------------------------- #
def audit_route_checks():
    print('-- admin routes: GET /api/admin/audit (recent, newest-first, capped)')
    api, _core = _api()
    H = _admin(api)

    # Issue an auditable admin action FIRST (a create writes an audit row).
    api.route('POST', '/api/admin/users', {},
              {'login': 'audited', 'password': 'pw', 'roles': ['cataloger']}, H)

    st, p = api.route('GET', '/api/admin/audit', {}, None, H)
    check('GET /api/admin/audit -> 200', st == 200)
    items = p['data']['items']
    check('audit returns items', isinstance(items, list) and len(items) >= 1)
    row = items[0]
    check('audit row carries the contract fields',
          all(k in row for k in ('ts', 'actor', 'function', 'db', 'mfn', 'result', 'detail')))
    check('the create action is logged',
          any(i['function'] == 'admin.users'
              and (i.get('detail') or {}).get('op') == 'create' for i in items))

    # newest-first: issue two distinguishable actions, the lat+ comes first.
    api.route('POST', '/api/admin/users', {},
              {'login': 'aud-first', 'password': 'pw'}, H)
    api.route('POST', '/api/admin/users', {},
              {'login': 'aud-second', 'password': 'pw'}, H)
    st, p = api.route('GET', '/api/admin/audit', {}, None, H)
    creates = [i for i in p['data']['items']
               if (i.get('detail') or {}).get('op') == 'create']
    check('audit newest-first (last create on top)',
          creates and creates[0]['detail'].get('login') == 'aud-second')

    # limit cap.
    st, p = api.route('GET', '/api/admin/audit', {'limit': ['1']}, None, H)
    check('audit ?limit=1 returns exactly 1', len(p['data']['items']) == 1)


# --------------------------------------------------------------------------- #
# 5. Databases — full staff/admin view (every base, not just public).
# --------------------------------------------------------------------------- #
def databases_route_checks():
    print('-- admin routes: GET /api/admin/databases (full staff view)')
    api, _core = _api()
    H = _admin(api)
    st, p = api.route('GET', '/api/admin/databases', {}, None, H)
    check('GET /api/admin/databases -> 200', st == 200)
    items = p['data']['items']
    codes = {i['code'] for i in items}
    check('admin DB list returns items', isinstance(items, list) and len(items) >= 3)
    check('public OPAC base IBIS present', 'IBIS' in codes)
    check('service base RDR present (admin sees ALL bases)', 'RDR' in codes)
    check('service base PAY present (admin sees ALL bases)', 'PAY' in codes)
    item = next(i for i in items if i['code'] == 'IBIS')
    check('DB item carries code/name/public',
          'code' in item and 'name' in item and 'public' in item)
    check('IBIS flagged public, RDR not',
          item['public'] is True
          and next(i for i in items if i['code'] == 'RDR')['public'] is False)


# --------------------------------------------------------------------------- #
# 6. Auth — non-admin staff + guest + reader 403 on every admin route; no session.
# --------------------------------------------------------------------------- #
ADMIN_ROUTES = [
    ('GET', '/api/admin/users', None),
    ('POST', '/api/admin/users', {'login': 'x', 'password': 'p'}),
    ('POST', '/api/admin/users/roles', {'userId': 1, 'roles': []}),
    ('POST', '/api/admin/users/active', {'userId': 1, 'active': True}),
    ('GET', '/api/admin/roles', None),
    ('GET', '/api/admin/audit', None),
    ('GET', '/api/admin/databases', None),
]


def auth_checks():
    print('-- auth: non-admin staff + guest + reader 403 on every admin route')
    api, _core = _api()

    # Non-admin STAFF: a real staff session that lacks admin.* -> 403 everywhere.
    HS = _nonadmin_staff(api)
    for m, path, b in ADMIN_ROUTES:
        st, _ = api.route(m, path, {}, b, HS)
        check('non-admin staff denied on %s %s (403)' % (m, path), st == 403)

    # GUEST + READER -> 403 (staff session required) everywhere.
    for label, headers in (('guest', _guest_headers(api)),
                           ('reader', _reader_headers(api))):
        for m, path, b in ADMIN_ROUTES:
            st, _ = api.route(m, path, {}, b, headers)
            check('%s denied on %s %s (403)' % (label, m, path), st == 403)

    # No session at all -> 401/403, never 200.
    for m, path, b in ADMIN_ROUTES:
        st, _ = api.route(m, path, {}, b, {})
        check('no session on %s %s -> 401/403' % (m, path), st in (401, 403))

    # Sanity: an admin session IS admitted (the guard isn't blanket-denying).
    H = _admin(api)
    st, _ = api.route('GET', '/api/admin/users', {}, None, H)
    check('admin admitted to /api/admin/users (200)', st == 200)


def main():
    users_route_checks()
    roles_and_active_checks()
    roles_list_checks()
    audit_route_checks()
    databases_route_checks()
    auth_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
