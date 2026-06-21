#!/usr/bin/env python3
"""HTTP-route tests for the ACQUISITION + BOOK-PROVISION engines (epic #188, #101).

The engines (``access/acquisition.py`` / ``access/bookprovision.py``) are unit-
tested standalone (``test_acquisition.py`` / ``test_bookprovision.py``); THIS suite
proves they are reachable over the HTTP surface — every assertion goes through the
real ``core.Api.route()`` dispatcher (the same path server.py / app_aiohttp.py use),
with a constructed ``Api`` (the constructor does NOT connect to ИРБИС).

Covered (the task contract):
  * a STAFF session can place an order / receive copies (→ КСУ + ToCat) / read КСУ
    and order-status THROUGH route();
  * a STAFF session can build a связка (faculty→specialty→discipline) + bind
    literature and compute the per-discipline / per-specialty Кко THROUGH route();
  * GUEST and READER sessions get 403 on EVERY acq/bp route (these are АРМ
    Комплектатор / Книгообеспеченность functions — staff-only, not public);
  * the ENTITLEMENT gate refuses the module when disabled (a valid grant on a
    disabled 'acquisition' / 'bookprovision' module is still 403).

Wired into the test_access.py runner (module list) so the CI sqlite + postgres
legs both run it. Standalone-runnable in the house style:
  py -3.12 tests/test_acq_bp_routes.py  -> ok ... + "N passed, M failed" + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS
from access import acquisition as _acq
from access import bookprovision as _bp

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Staff grants for the АРМ Комплектатор / Книгообеспеченность functions wired in
# core.py (acq.receipt/acq.read writes+reads acquisition; bp.write/bp.read book-
# provision). A real account would carry these via a seeded role; here we mint them
# onto the session token directly so the suite needs no DB role.
STAFF_GRANTS = [
    {'function': 'acq.receipt', 'db': '*', 'level': 'write'},
    {'function': 'acq.read', 'db': '*', 'level': 'read'},
    {'function': 'bp.write', 'db': '*', 'level': 'write'},
    {'function': 'bp.read', 'db': '*', 'level': 'read'},
]


def _api():
    """A constructed Api with NO live ИРБИС and fresh in-memory engine stores.

    The acquisition / book-provision engines are rebuilt over ':memory:' stores so
    each test group starts empty and isolated; the shared CatalogStore is the ToCat
    seam (acquisition writes it, book-provision could read it)."""
    os.environ['JWT_SECRET'] = 'acq-bp-routes-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    from access.catalog import CatalogStore
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    api.acquisition = _acq.AcquisitionEngine(
        store=_acq.AcquisitionStore(':memory:'), catalog=api.catalog,
        catalog_db=api.cfg.db_default)
    api.bookprovision = _bp.BookProvisionEngine(':memory:', catalog=api.catalog)
    return api, _core


def _staff(api, login='compl'):
    tok, _sess = api._new_session('staff', login, STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest_headers(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader_headers(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


# --------------------------------------------------------------------------- #
# 1. Acquisition through route(): order → receive (КСУ + ToCat) → reads.
# --------------------------------------------------------------------------- #
def acquisition_route_checks():
    print('-- acq routes: order / receive / КСУ / order-status (staff via route())')
    api, _core = _api()
    H = _staff(api)

    # POST /api/acq/order — open an order line.
    st, p = api.route('POST', '/api/acq/order', {},
                      {'title': 'Алгоритмы', 'author': 'Кнут', 'copies': 3,
                       'price': 100.0}, H)
    check('POST /api/acq/order -> 200', st == 200)
    check('order created in ordered status', p['data']['status'] == 'ordered')
    oid = p['data']['id']

    # POST /api/acq/receive — 2 of 3 copies → КСУ entry + ToCat catalog record.
    st, p = api.route('POST', '/api/acq/receive', {},
                      {'orderId': oid, 'ksuNo': '2026/1', 'copies': 2,
                       'unitPrice': 100.0, 'actRef': 'акт-7'}, H)
    check('POST /api/acq/receive -> 200', st == 200)
    check('receive writes КСУ (88^F copies=2)', p['data']['ksu']['copies'] == 2)
    check('receive sum = price*copies (88^G=200)', p['data']['sum'] == 200.0)
    check('receive assigns 2 inventory numbers', len(p['data']['inventory']) == 2)
    check('ToCat created a catalog record (mfn present)',
          p['data']['catalog_mfn'] is not None and
          p['data']['catalog_action'] == 'created')
    check('order now partially_received',
          p['data']['order']['status'] == 'partially_received')

    # GET /api/acq/order?id= — order-status read.
    st, p = api.route('GET', '/api/acq/order', {'id': [str(oid)]}, None, H)
    check('GET /api/acq/order?id= -> 200', st == 200)
    check('order-status reports partially_received',
          p['data']['status'] == 'partially_received')

    # GET /api/acq/ksu?no= — the КСУ summary row.
    st, p = api.route('GET', '/api/acq/ksu', {'no': ['2026/1']}, None, H)
    check('GET /api/acq/ksu?no= -> 200', st == 200)
    check('КСУ summary: 1 title / 2 copies / sum 200',
          p['data']['titles'] == 1 and p['data']['copies'] == 2 and
          p['data']['total_sum'] == 200.0)

    # Cancel is refused after a receipt (copies already in the fund) -> 400.
    st, p = api.route('POST', '/api/acq/order/cancel', {}, {'id': oid}, H)
    check('cancel after receipt -> 400 (can\'t cancel received)', st == 400)

    # A second, untouched order CAN be cancelled.
    st, p = api.route('POST', '/api/acq/order', {},
                      {'title': 'Лишний', 'copies': 1}, H)
    oid2 = p['data']['id']
    st, p = api.route('POST', '/api/acq/order/cancel', {}, {'id': oid2}, H)
    check('cancel of untouched order -> cancelled',
          st == 200 and p['data']['status'] == 'cancelled')

    # Unknown order / КСУ reads -> 404 (not 500).
    st, _ = api.route('GET', '/api/acq/order', {'id': ['999999']}, None, H)
    check('unknown order -> 404', st == 404)
    st, _ = api.route('GET', '/api/acq/ksu', {'no': ['nope']}, None, H)
    check('unknown КСУ -> 404', st == 404)


# --------------------------------------------------------------------------- #
# 2. Book-provision through route(): связка → bind → Кко reports.
# --------------------------------------------------------------------------- #
def bookprovision_route_checks():
    print('-- bp routes: связка (faculty/specialty/discipline) / bind / Кко')
    api, _core = _api()
    H = _staff(api)

    st, p = api.route('POST', '/api/bp/faculty', {},
                      {'code': 'ФВТ', 'name': 'Факультет ВТ'}, H)
    check('POST /api/bp/faculty -> 200', st == 200)
    fid = p['data']['id']

    st, p = api.route('POST', '/api/bp/specialty', {},
                      {'facultyId': fid, 'napr': '09.03.01', 'spec': 'ИВТ'}, H)
    check('POST /api/bp/specialty -> 200', st == 200)
    sid = p['data']['id']

    st, p = api.route('POST', '/api/bp/discipline', {},
                      {'specialtyId': sid, 'discId': 'D-1',
                       'name': 'Программирование', 'students': 100}, H)
    check('POST /api/bp/discipline -> 200', st == 200)
    did = p['data']['id']

    # Bind основная literature with 40 copies → Кко = 40/100 = 0.4 (under 0.5 norm).
    st, p = api.route('POST', '/api/bp/bind', {},
                      {'disciplineId': did, 'title': 'Учебник', 'kind': 'main',
                       'copies': 40}, H)
    check('POST /api/bp/bind -> 200', st == 200)

    # GET /api/bp/discipline?id= — per-discipline Кко report.
    st, p = api.route('GET', '/api/bp/discipline', {'id': [str(did)]}, None, H)
    check('GET /api/bp/discipline?id= -> 200', st == 200)
    check('discipline Кко = 0.4', abs(p['data']['average_kko'] - 0.4) < 1e-9)
    check('discipline under-provisioned (Кко<0.5)',
          p['data']['under_provisioned'] is True)
    check('shortfall = ceil(100*0.5)-40 = 10', p['data']['shortfall'] == 10)

    # Contingent refresh: drop students to 50 → Кко = 40/50 = 0.8 (now provided).
    st, p = api.route('POST', '/api/bp/contingent', {},
                      {'disciplineId': did, 'students': 50, 'source': 'rdr'}, H)
    check('POST /api/bp/contingent -> 200', st == 200)
    st, p = api.route('GET', '/api/bp/discipline', {'id': [str(did)]}, None, H)
    check('after recount Кко = 0.8', abs(p['data']['average_kko'] - 0.8) < 1e-9)
    check('no longer under-provisioned', p['data']['under_provisioned'] is False)

    # normalize=1 caps each Кко term at 1 (over-provision can't paper over deficit).
    st, p = api.route('GET', '/api/bp/discipline',
                      {'id': [str(did)], 'normalize': ['1']}, None, H)
    check('normalize=1 honoured (Кко still 0.8 here)',
          abs(p['data']['average_kko'] - 0.8) < 1e-9)

    # GET /api/bp/specialty?id= — per-specialty rollup.
    st, p = api.route('GET', '/api/bp/specialty', {'id': [str(sid)]}, None, H)
    check('GET /api/bp/specialty?id= -> 200', st == 200)
    check('specialty rollup lists the discipline',
          len(p['data']['disciplines']) == 1)
    check('specialty average Кко = 0.8',
          abs(p['data']['average_kko'] - 0.8) < 1e-9)

    # Unknown discipline / specialty -> 404.
    st, _ = api.route('GET', '/api/bp/discipline', {'id': ['999999']}, None, H)
    check('unknown discipline -> 404', st == 404)
    st, _ = api.route('GET', '/api/bp/specialty', {'id': ['999999']}, None, H)
    check('unknown specialty -> 404', st == 404)


# --------------------------------------------------------------------------- #
# 3. Auth — guest AND reader get 403 on every acq/bp route (staff-only АРМ).
# --------------------------------------------------------------------------- #
ACQ_BP_ROUTES = [
    ('POST', '/api/acq/order', {'title': 'x', 'copies': 1}),
    ('POST', '/api/acq/order/cancel', {'id': 1}),
    ('POST', '/api/acq/receive', {'orderId': 1, 'ksuNo': 'k', 'copies': 1}),
    ('GET', '/api/acq/order', None),       # ?id= via query (default 0)
    ('GET', '/api/acq/ksu', None),
    ('POST', '/api/bp/faculty', {'code': 'F'}),
    ('POST', '/api/bp/specialty', {'facultyId': 1}),
    ('POST', '/api/bp/discipline', {'specialtyId': 1, 'discId': 'D'}),
    ('POST', '/api/bp/contingent', {'disciplineId': 1, 'students': 1}),
    ('POST', '/api/bp/bind', {'disciplineId': 1, 'title': 't'}),
    ('GET', '/api/bp/discipline', None),
    ('GET', '/api/bp/specialty', None),
]


def auth_checks():
    print('-- auth: guest + reader 403 on every acq/bp route')
    api, _core = _api()

    for label, headers in (('guest', _guest_headers(api)),
                           ('reader', _reader_headers(api))):
        for m, path, b in ACQ_BP_ROUTES:
            q = {'id': ['1'], 'no': ['k']}    # harmless for GET routes
            st, _payload = api.route(m, path, q, b, headers)
            check('%s denied on %s %s (403)' % (label, m, path), st == 403)

    # No session at all -> 401/403, never 200.
    for m, path, b in ACQ_BP_ROUTES:
        st, _ = api.route(m, path, {'id': ['1'], 'no': ['k']}, b, {})
        check('no session on %s %s -> 401/403' % (m, path), st in (401, 403))

    # Sanity: a staff session IS admitted (the guard isn't blanket-denying).
    H = _staff(api)
    st, _ = api.route('POST', '/api/acq/order', {},
                      {'title': 'OK', 'copies': 1}, H)
    check('staff admitted to /api/acq/order (200)', st == 200)


# --------------------------------------------------------------------------- #
# 4. Entitlement gate — a disabled module refuses even a valid grant.
# --------------------------------------------------------------------------- #
def entitlement_gate_checks():
    print('-- entitlement: disabled module refuses a valid grant (403)')
    api, _core = _api()
    H = _staff(api)

    # Baseline: with entitlements open, the staff grant places an order (200).
    st, _ = api.route('POST', '/api/acq/order', {},
                      {'title': 'Baseline', 'copies': 1}, H)
    check('acq order allowed when acquisition module licensed', st == 200)

    orig = _core.entitlements.is_module_enabled
    # Disable BOTH acquisition and bookprovision for this tenant.
    _core.entitlements.is_module_enabled = (
        lambda tenant, module, dsn=None:
        module not in ('acquisition', 'bookprovision'))
    try:
        st, p = api.route('POST', '/api/acq/order', {},
                          {'title': 'Gated', 'copies': 1}, H)
        check('acq order refused when acquisition module disabled (403)', st == 403)
        check('refusal cites module not licensed',
              'module not licensed' in (p.get('error', {}).get('message', '')))

        st, p = api.route('GET', '/api/acq/ksu', {'no': ['x']}, None, H)
        check('acq КСУ read refused when module disabled (403)', st == 403)

        st, p = api.route('POST', '/api/bp/faculty', {}, {'code': 'F'}, H)
        check('bp faculty refused when bookprovision disabled (403)', st == 403)

        st, p = api.route('GET', '/api/bp/specialty', {'id': ['1']}, None, H)
        check('bp specialty read refused when module disabled (403)', st == 403)
    finally:
        _core.entitlements.is_module_enabled = orig

    # Restored: the order works again once the module is licensed.
    st, _ = api.route('POST', '/api/acq/order', {},
                      {'title': 'Restored', 'copies': 1}, H)
    check('acq order allowed again after module re-enabled', st == 200)


def main():
    acquisition_route_checks()
    bookprovision_route_checks()
    auth_checks()
    entitlement_gate_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
