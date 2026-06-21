#!/usr/bin/env python3
"""Backend hardening tests (issue: harden ИРБИС connection + public-only OPAC).

Two independent concerns, both fully sqlite-green and requiring NO live ИРБИС:

  A. SELF-HEAL — ``core.ResilientIrbis`` wraps the SessionManager so a STALE
     registered session (after a server Стоп/Старт, or the demo "max 3 clients"
     cap evicting us) RE-REGISTERS and retries instead of failing every request
     until a manual process restart. We assert: a first-call connection error
     re-registers and succeeds on retry; a stale-session IRBIS return code
     (-3337/-3338/-33xx) self-heals the same way; a DATA-level code (-140 missing
     MFN) propagates unchanged (it's a real answer, not a dead session); retries
     are bounded (exhaustion raises); health()/ping() reflect reachability.

  B. PUBLIC-ONLY OPAC — a guest/reader session may only touch the configured
     PUBLIC bibliographic bases (Config.public_dbs, default {IBIS}); a non-public
     db (RDR readers, LICH/PAY/RIGHT ПДн, RQST/CMPL service, LOG*) is refused 403
     on search/record/render/terms/showcase/rubricator/facets/cover/
     example-queries, and is hidden from /api/databases. STAFF keep access per
     their grants (the public confinement does not apply to them).

House style mirrors tests/test_discovery.py — a constructed ``Api`` (whose
constructor does NOT connect to ИРБИС) with stubs injected over ``api.irbis``.
Invoked by the tests/test_access.py runner via the generic ``module_checks``
loop, so the existing CI step that runs test_access.py also runs this suite with
no .github/ workflow change.

Standalone too::

    py -3.12 tests/test_resilience.py   ->  'ok …' lines + 'N passed, M failed'
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

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
# Stubs.
# --------------------------------------------------------------------------- #
class _FakeClient:
    """The bits of irbis.client.IrbisClient that ResilientIrbis._reset_session
    touches (so we can observe the client_id rotation on re-register)."""

    def __init__(self):
        self.connected = True
        self.client_id = 123456


class FlakySession:
    """Stand-in for irbis.SessionManager.

    ``fail_plan`` maps a method name -> a list of exceptions to raise on the first
    N calls (one per entry), after which the call succeeds and returns
    ``results[name]``. ``register_count`` counts how often the wrapper forced a
    re-register (via _reset_session marking us disconnected, the way a real
    re-register is observed)."""

    def __init__(self, fail_plan=None, results=None):
        self._fail_plan = {k: list(v) for k, v in (fail_plan or {}).items()}
        self._results = results or {}
        self._calls = {}
        self.connected = True
        self._client = _FakeClient()
        self.reset_count = 0
        self.closed = False

    def _dispatch(self, name):
        self._calls[name] = self._calls.get(name, 0) + 1
        plan = self._fail_plan.get(name)
        if plan:
            raise plan.pop(0)
        return self._results.get(name, ('OK', name))

    # SessionManager surface that ResilientIrbis proxies / touches
    def max_mfn(self, db):
        return self._dispatch('max_mfn')

    def search(self, db, expr, first=1, maxn=0):
        return self._dispatch('search')

    def read_record(self, db, mfn):
        return self._dispatch('read_record')

    def format_record(self, db, mfn, pft='@brief'):
        return self._dispatch('format_record')

    def read_terms(self, db, start, count=20):
        return self._dispatch('read_terms')

    def read_file(self, spec):
        return self._dispatch('read_file')

    def update_record(self, db, lines, lock=0, actualize=1):
        return self._dispatch('update_record')

    def server_version(self):
        return self._dispatch('server_version')

    def close(self):
        self.closed = True

    def calls(self, name):
        return self._calls.get(name, 0)


def _irbis_error(code):
    from irbis.client import IrbisError
    return IrbisError(code, 'stub %s' % code)


def _resilient(fail_plan=None, results=None, retries=2, backoff=0.0):
    """Build a ResilientIrbis over a FlakySession (backoff 0 keeps tests fast)."""
    import core as _core
    importlib.reload(_core)
    sm = FlakySession(fail_plan=fail_plan, results=results)
    wrapper = _core.ResilientIrbis(sm, retries=retries, backoff=backoff)
    return wrapper, sm, _core


# --------------------------------------------------------------------------- #
# A. ResilientIrbis self-heal.
# --------------------------------------------------------------------------- #
def reconnect_on_socket_error_checks():
    print('-- ResilientIrbis: socket error -> re-register + retry')
    # First search() raises a ConnectionError (dropped TCP / server restart),
    # the retry succeeds.
    w, sm, _ = _resilient(fail_plan={'search': [ConnectionError('reset by peer')]},
                          results={'search': (7, [1, 2, 3])})
    cid_before = sm._client.client_id
    out = w.search('IBIS', '"K=x"')
    check('search retried after socket error -> success', out == (7, [1, 2, 3]))
    check('search was attempted twice (fail + retry)', sm.calls('search') == 2)
    check('re-register rotated client_id (new server session)',
          sm._client.client_id != cid_before)
    check('reset marked session disconnected before retry',
          sm.connected is False)
    check('last_error cleared after the successful retry', w.last_error is None)
    check('last_ok_ts recorded after success', w.last_ok_ts is not None)


def reconnect_on_stale_session_code_checks():
    print('-- ResilientIrbis: stale-session IRBIS code -> re-register + retry')
    # A -3338 (CLIENT_NOT_ALLOWED, also seen when the server forgot our client_id
    # after a restart) self-heals: drop the session, re-register, retry.
    for code in (-3337, -3338, -3310):
        w, sm, _ = _resilient(fail_plan={'read_record': [_irbis_error(code)]},
                              results={'read_record': {'mfn': 5}})
        out = w.read_record('IBIS', 5)
        check('stale code %d self-heals on retry' % code, out == {'mfn': 5})
        check('stale code %d retried once' % code, sm.calls('read_record') == 2)


def data_level_code_propagates_checks():
    print('-- ResilientIrbis: data-level IRBIS code propagates (NOT a dead session)')
    from irbis.client import IrbisError
    # -140 (no such MFN) and -603 (deleted) are real answers — must NOT be retried
    # or swallowed; they propagate unchanged for the endpoint to handle.
    for code in (-140, -603):
        w, sm, _ = _resilient(fail_plan={'read_record': [_irbis_error(code),
                                                          _irbis_error(code)]})
        raised = None
        try:
            w.read_record('IBIS', 999)
        except IrbisError as e:
            raised = e.code
        check('data code %d propagates unchanged' % code, raised == code)
        check('data code %d NOT retried (single attempt)' % code,
              sm.calls('read_record') == 1)


def retries_are_bounded_checks():
    print('-- ResilientIrbis: bounded retries (exhaustion raises)')
    from irbis.client import IrbisError
    # Every attempt fails with a connection error -> after retries exhausted, raise.
    w, sm, _ = _resilient(
        fail_plan={'max_mfn': [ConnectionError('down')] * 9}, retries=2)
    raised = False
    try:
        w.max_mfn('IBIS')
    except IrbisError:
        raised = True
    check('exhausted reconnect raises IrbisError', raised)
    check('attempted exactly retries+1 (3) times', sm.calls('max_mfn') == 3)
    check('last_error retained after exhaustion', bool(w.last_error))

    # Stale IRBIS code that never clears also exhausts and re-raises that error.
    w2, sm2, _ = _resilient(
        fail_plan={'search': [_irbis_error(-3338)] * 9}, retries=1)
    raised2 = None
    try:
        w2.search('IBIS', '"K=x"')
    except IrbisError as e:
        raised2 = e.code
    check('persistent stale code exhausts and re-raises it', raised2 == -3338)
    check('persistent stale code attempted retries+1 (2) times',
          sm2.calls('search') == 2)


def health_and_ping_checks():
    print('-- ResilientIrbis: health()/ping() reflect reachability')
    from irbis.client import IrbisError
    w, sm, _ = _resilient(results={'server_version': '2022.1'})
    check('ping() True when server reachable', w.ping() is True)
    h = w.health()
    check('health() exposes lastError/lastOkTs/retries',
          set(('lastError', 'lastOkTs', 'retries')) <= set(h))
    check('health() lastError None when healthy', h['lastError'] is None)

    # server unreachable on every attempt -> ping False, never raises
    w2, sm2, _ = _resilient(fail_plan={'server_version': [ConnectionError('x')] * 9},
                            retries=1)
    check('ping() False when server unreachable (no raise)', w2.ping() is False)
    check('health() records lastError when down', bool(w2.health()['lastError']))

    # close() proxies to the underlying SessionManager
    w.close()
    check('close() proxied to SessionManager', sm.closed is True)


def is_stale_session_helper_checks():
    print('-- _is_stale_session classifier')
    import core as _core
    importlib.reload(_core)
    f = _core._is_stale_session
    check('-3337 is stale', f(-3337))
    check('-3338 is stale', f(-3338))
    check('-3300/-3349 range is stale', f(-3300) and f(-3349) and f(-3325))
    check('-140 (missing MFN) is NOT stale', not f(-140))
    check('-603 (deleted) is NOT stale', not f(-603))
    check('-202 (terms) is NOT stale', not f(-202))
    check('None is NOT stale', not f(None))
    check('0 is NOT stale', not f(0))


# --------------------------------------------------------------------------- #
# B. Public-only OPAC enforcement (constructed Api + discovery-style FakeIrbis).
# --------------------------------------------------------------------------- #
def _fld(tag, value, subfields=None):
    return {'tag': tag, 'value': value, 'text': value, 'subfields': subfields or {}}


class OpacFake:
    """Minimal ИРБИС stub for the Api OPAC endpoints (records/terms/menu/maxmfn).
    The public-DB guard must reject a non-public db BEFORE any of these run, so a
    403 path never reaches the stub — but a public db must flow through to it."""

    def __init__(self, dbmenu=''):
        self._dbmenu = dbmenu
        self.touched = []          # dbs that actually reached IRBIS (public path)

    def max_mfn(self, db):
        self.touched.append(db)
        return 6

    def read_record(self, db, mfn):
        self.touched.append(db)
        return {'mfn': mfn, 'status': '0', 'version': '1', 'guid': None,
                'fields': [_fld('200', 'T %d' % mfn, {'A': 'T %d' % mfn})]}

    def search(self, db, expr, first=1, maxn=0):
        self.touched.append(db)
        return 1, [1]

    def read_terms(self, db, start, count=20):
        self.touched.append(db)
        return [(3, '%s%s' % (start, 'X'))]

    def read_file(self, spec):
        return self._dbmenu

    def format_record(self, db, mfn, pft='@brief'):
        return ''


def _api(fake):
    os.environ['JWT_SECRET'] = 'resilience-test-secret'
    os.environ.pop('IRBIS_PUBLIC_DBS', None)        # exercise the default {IBIS}
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = fake
    return api, _core


def _guest(api):
    from access.authz import GUEST_GRANTS
    return api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')


def _reader(api):
    from access.authz import READER_GRANTS
    return api._new_session('reader', 'RI=001', READER_GRANTS,
                            tenant='public', rdr_mfn=1)


def _staff(api):
    grants = [
        {'function': 'search', 'db': '*', 'level': 'read'},
        {'function': 'record.read', 'db': '*', 'level': 'read'},
        {'function': 'terms', 'db': '*', 'level': 'read'},
        {'function': 'file', 'db': '*', 'level': 'read'},
    ]
    return api._new_session('staff', 'cataloger', grants, tenant='public')


# Non-public bases a reader must never query (service + ПДн).
_FORBIDDEN = ('RDR', 'LICH', 'PAY', 'RIGHT', 'RQST', 'CMPL', 'LOGB', 'RDR_ARH', 'ZAPR')


def public_db_guard_search_checks():
    print('-- public-DB: guest/reader 403 on non-public db (search)')
    api, _core = _api(OpacFake())
    _t, guest = _guest(api)
    _tr, reader = _reader(api)

    # public base flows through
    status, payload = api.search(guest, 'IBIS', '"K=x"', 1, 20)
    check('guest search on IBIS (public) -> 200', status == 200)
    check('IBIS reached the IRBIS stub', 'IBIS' in api.irbis.touched)

    for db in _FORBIDDEN:
        denied_g = denied_r = None
        try:
            api.search(guest, db, '"K=x"', 1, 20)
        except _core.Denied as d:
            denied_g = d.status
        try:
            api.search(reader, db, '"K=x"', 1, 20)
        except _core.Denied as d:
            denied_r = d.status
        check('guest search %s -> 403' % db, denied_g == 403)
        check('reader search %s -> 403' % db, denied_r == 403)
    # crucially the forbidden db never reached IRBIS (guard runs before the call)
    check('no forbidden db ever reached the IRBIS stub',
          not any(db in api.irbis.touched for db in _FORBIDDEN))


def public_db_guard_all_endpoints_checks():
    print('-- public-DB: guest 403 across every OPAC read endpoint on RDR/LICH')
    api, _core = _api(OpacFake())
    _t, guest = _guest(api)

    def denied(call):
        try:
            call()
        except _core.Denied as d:
            return d.status
        return None

    for db in ('RDR', 'LICH'):
        check('record %s -> 403' % db, denied(lambda: api.record(guest, db, 1)) == 403)
        check('render %s -> 403' % db,
              denied(lambda: api.render(guest, db, 1, '@brief')) == 403)
        check('terms %s -> 403' % db, denied(lambda: api.terms(guest, db, '', 10)) == 403)
        check('showcase %s -> 403' % db,
              denied(lambda: api.showcase(guest, db, 'new', 12)) == 403)
        check('rubricator %s -> 403' % db,
              denied(lambda: api.rubricator(guest, db, 'G=', '', 30)) == 403)
        check('facets %s -> 403' % db,
              denied(lambda: api.facets(guest, db, '"K=x"')) == 403)
        check('cover %s -> 403' % db, denied(lambda: api.cover(guest, db, 1)) == 403)
        check('example_queries %s -> 403' % db,
              denied(lambda: api.example_queries(guest, db)) == 403)


def public_db_guard_staff_allowed_checks():
    print('-- public-DB: staff keep access to service bases (per grants)')
    api, _core = _api(OpacFake())
    _t, staff = _staff(api)
    # staff are NOT public-confined; a '*' read grant lets them search RDR.
    status, payload = api.search(staff, 'RDR', '"RI=1"', 1, 20)
    check('staff search RDR -> 200 (grant governs, not public policy)', status == 200)
    status, payload = api.terms(staff, 'LICH', '', 10)
    check('staff terms LICH -> 200', status == 200)
    check('staff reached RDR + LICH on the stub',
          'RDR' in api.irbis.touched and 'LICH' in api.irbis.touched)


def databases_visibility_checks():
    print('-- /api/databases: readers see only public bases; staff see all')
    menu = ('IBIS\nЭлектронный каталог\n'
            'RDR\nЧитатели\n'
            'LICH\nПДн\n'
            'RQST\nЗаказы\n')
    api, _core = _api(OpacFake(dbmenu=menu))
    _t, guest = _guest(api)
    _tr, reader = _reader(api)
    _ts, staff = _staff(api)

    status, payload = api.databases(guest, with_counts=False)
    codes = {i['code'] for i in payload['data']['items']}
    check('guest /api/databases returns 200', status == 200)
    check('guest sees IBIS (public)', codes == {'IBIS'})
    check('guest does NOT see RDR/LICH/RQST',
          not ({'RDR', 'LICH', 'RQST'} & codes))
    check('every db a guest sees is flagged public',
          all(i['public'] for i in payload['data']['items']))

    status, payload = api.databases(reader, with_counts=False)
    rcodes = {i['code'] for i in payload['data']['items']}
    check('reader sees only public bases too', rcodes == {'IBIS'})

    status, payload = api.databases(staff, with_counts=False)
    scodes = {i['code'] for i in payload['data']['items']}
    check('staff sees ALL bases', scodes == {'IBIS', 'RDR', 'LICH', 'RQST'})
    by = {i['code']: i for i in payload['data']['items']}
    check('staff: IBIS flagged public', by['IBIS']['public'] is True)
    check('staff: RDR flagged non-public', by['RDR']['public'] is False)
    check('staff: LICH flagged non-public', by['LICH']['public'] is False)


def public_db_config_override_checks():
    print('-- public-DB: IRBIS_PUBLIC_DBS env extends the allow-list')
    menu = 'IBIS\nКаталог\nPERIO\nПериодика\nRDR\nЧитатели\n'
    os.environ['IRBIS_PUBLIC_DBS'] = 'IBIS, PERIO'    # add PERIO as public
    try:
        import core as _core
        importlib.reload(_core)
        api = _core.Api()
        api.irbis = OpacFake(dbmenu=menu)
        _t, guest = _guest(api)
        # PERIO now counts as public -> guest may search it and sees it listed
        status, payload = api.search(guest, 'PERIO', '"K=x"', 1, 20)
        check('configured-public PERIO -> guest search 200', status == 200)
        status, payload = api.databases(guest, with_counts=False)
        codes = {i['code'] for i in payload['data']['items']}
        check('guest sees configured-public IBIS+PERIO, not RDR',
              codes == {'IBIS', 'PERIO'})
        # RDR is still non-public -> still 403
        denied = None
        try:
            api.search(guest, 'RDR', '"K=x"', 1, 20)
        except _core.Denied as d:
            denied = d.status
        check('RDR still non-public under override -> 403', denied == 403)
    finally:
        os.environ.pop('IRBIS_PUBLIC_DBS', None)


def route_public_db_checks():
    print('-- route(): guest hitting non-public db via the real dispatch -> 403')
    menu = 'IBIS\nКаталог\nRDR\nЧитатели\n'
    api, _core = _api(OpacFake(dbmenu=menu))
    tok, _s = _guest(api)
    h = {'authorization': 'Bearer ' + tok}

    status, payload = api.route('GET', '/api/search',
                                {'db': ['RDR'], 'q': ['x']}, None, h)
    check('route GET /api/search?db=RDR (guest) -> 403',
          status == 403 and payload['ok'] is False)

    status, payload = api.route('GET', '/api/record/RDR/1', {}, None, h)
    check('route GET /api/record/RDR/1 (guest) -> 403', status == 403)

    # public db still works end-to-end through route()
    status, payload = api.route('GET', '/api/search',
                                {'db': ['IBIS'], 'q': ['x']}, None, h)
    check('route GET /api/search?db=IBIS (guest) -> 200', status == 200)

    # /api/databases through route() hides RDR for the guest
    status, payload = api.route('GET', '/api/databases', {'counts': ['0']}, None, h)
    codes = {i['code'] for i in payload['data']['items']}
    check('route /api/databases (guest) hides RDR', codes == {'IBIS'})


def health_endpoint_checks():
    print('-- /api/health reflects ИРБИС reachability (never 500)')
    # reachable
    api, _core = _api(OpacFake())
    api.irbis = _core.ResilientIrbis(FlakySession(results={
        'server_version': '2022.1', 'max_mfn': 6}), retries=1, backoff=0.0)
    payload = api.health()
    check('health ok envelope', payload.get('ok') is True)
    check('health reports irbis.reachable True', payload['data']['irbis']['reachable'] is True)
    check('health carries version', payload['data'].get('version') == '2022.1')

    # unreachable -> reachable False, still ok:True (HTTP 200), no raise
    api2, _core2 = _api(OpacFake())
    api2.irbis = _core2.ResilientIrbis(
        FlakySession(fail_plan={'server_version': [ConnectionError('x')] * 9,
                                'max_mfn': [ConnectionError('x')] * 9}),
        retries=1, backoff=0.0)
    payload = api2.health()
    check('health on dead ИРБИС still ok envelope', payload.get('ok') is True)
    check('health reports irbis.reachable False', payload['data']['irbis']['reachable'] is False)
    check('health surfaces lastError when down', bool(payload['data']['irbis']['lastError']))


def main():
    # A. self-heal
    reconnect_on_socket_error_checks()
    reconnect_on_stale_session_code_checks()
    data_level_code_propagates_checks()
    retries_are_bounded_checks()
    health_and_ping_checks()
    is_stale_session_helper_checks()
    # B. public-only OPAC
    public_db_guard_search_checks()
    public_db_guard_all_endpoints_checks()
    public_db_guard_staff_allowed_checks()
    databases_visibility_checks()
    public_db_config_override_checks()
    route_public_db_checks()
    health_endpoint_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
