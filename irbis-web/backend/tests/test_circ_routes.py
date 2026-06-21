#!/usr/bin/env python3
"""HTTP-route tests for the CIRCULATION desk + CATALOGING worklist (MVP Phase 1,
#183 cataloger / #185 circulation, epic #223).

The CirculationEngine is unit-tested standalone (``test_circulation.py``) and its
catalog 910^A flip is covered by ``test_integration.py``; THIS suite proves the
staff workstation surface is reachable over HTTP — every assertion goes through
the real ``core.Api.route()`` dispatcher (the same path server.py / app_aiohttp.py
use), with a constructed ``Api`` (the constructor does NOT connect to ИРБИС).

Covered (the task contract, all through route()):
  * CATALOGING #183 — GET /api/worklist/{db} returns the editor field menu
    (curated WORKLIST_IBIS for IBIS/PAZK, generic fallback otherwise);
  * CIRCULATION #185 — a STAFF session can issue → the reader formulary
    (/api/circ/reader, field 40) shows the loan → return clears it; renew updates
    the due date; fines read back;
  * the catalog 910^A flips 0→1 on issue and 1→0 on return (the engine is wired
    WITH the catalog handle by core.Api.__init__);
  * GUEST and READER sessions get 403 on EVERY staff circ/worklist route (these
    are staff workstations — not public);
  * the ENTITLEMENT gate refuses the 'circulation' module when disabled (a valid
    grant on a disabled module is still 403).

Wired into the test_access.py runner (module list) so the CI sqlite + postgres
legs both run it. Standalone-runnable in the house style:
  py -3.12 tests/test_circ_routes.py  -> ok ... + "N passed, M failed" + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS
from access import circulation as _circ
from access.catalog import (CatalogStore, EXEMPLAR_FREE, EXEMPLAR_ISSUED)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Staff grants for the circ desk + cataloging editor wired in core.py: circ.issue
# (lend/renew/read formulary) + circ.return (take back) gate the 'circulation'
# module; record.write gates the cataloging worklist editor. A real account carries
# these via a seeded role (seed.py: librarian / administrator); here we mint them
# onto the session token directly so the suite needs no DB role.
STAFF_GRANTS = [
    {'function': 'circ.issue', 'db': '*', 'level': 'write'},
    {'function': 'circ.return', 'db': '*', 'level': 'write'},
    {'function': 'record.write', 'db': '*', 'level': 'write'},
]

INV = '2001001'   # inventory number (910^b) of the demo copy
T0 = 1_700_000_000.0
DAY = 86400


def _book_with_copy(inv=INV, status=EXEMPLAR_FREE):
    """A valid catalog record carrying one 910 exemplar keyed by inventory ``inv``
    whose 910^A starts at ``status`` (default free)."""
    return {
        '920': 'PAZK',
        '200': [{'a': 'Алгоритмы и структуры данных', 'f': 'Кнут Д.'}],
        '700': [{'a': 'Кнут', 'g': 'Дональд'}],
        '101': 'rus',
        '910': [{'a': status, 'b': inv}],
        '907': [{'a': 'Каталогизатор'}],
    }


def _api(with_copy=True, fixed_now=None):
    """A constructed Api with NO live ИРБИС, a fresh in-memory circulation store,
    and a CatalogStore carrying one demo copy (so the 910^A flip is observable).

    The circulation engine is rebuilt over a ':memory:' store wired to THIS api's
    catalog handle (catalog=api.catalog, the same seam core.Api.__init__ wires) so
    issue/return flip the catalog exemplar exactly as in production. ``fixed_now``
    pins the desk clock for deterministic due dates."""
    os.environ['JWT_SECRET'] = 'circ-routes-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    if with_copy:
        api.catalog.save('IBIS', _book_with_copy(INV, EXEMPLAR_FREE))
    api.circulation = _circ.CirculationEngine(
        store=_circ.CirculationStore(':memory:'),
        notifications=api.notifications,
        catalog=api.catalog, catalog_db=api.cfg.db_default)
    if fixed_now is not None:
        api._CIRC_NOW = lambda: fixed_now
    return api, _core


def _staff(api, login='circ'):
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
# 1. Cataloging worklist (#183) — GET /api/worklist/{db}.
# --------------------------------------------------------------------------- #
def worklist_route_checks():
    print('-- worklist route: GET /api/worklist/{db} (curated + generic)')
    api, _core = _api()
    H = _staff(api)

    st, p = api.route('GET', '/api/worklist/IBIS', {}, None, H)
    check('GET /api/worklist/IBIS -> 200', st == 200)
    check('worklist returns a fields list', isinstance(p['data']['fields'], list)
          and len(p['data']['fields']) > 0)
    fld = p['data']['fields'][0]
    check('field carries code+label+type',
          'code' in fld and 'label' in fld and 'type' in fld)
    check('IBIS worklist has the curated 920 type field',
          any(f['code'] == '920' for f in p['data']['fields']))
    check('a field marks required', any(f.get('required') for f in p['data']['fields']))
    check('a field carries subfields',
          any(isinstance(f.get('subfields'), list) for f in p['data']['fields']))

    # PAZK shares the curated book worklist.
    st, p = api.route('GET', '/api/worklist/PAZK', {}, None, H)
    check('GET /api/worklist/PAZK -> 200 (curated)', st == 200
          and any(f['code'] == '920' for f in p['data']['fields']))

    # An unknown base falls back to the generic worklist (still usable: title etc).
    st, p = api.route('GET', '/api/worklist/SOMEDB', {}, None, H)
    check('GET /api/worklist/SOMEDB -> 200 (generic fallback)', st == 200)
    check('generic worklist still has 200 заглавие',
          any(f['code'] == '200' for f in p['data']['fields']))
    check('generic worklist omits the curated-only 920',
          not any(f['code'] == '920' for f in p['data']['fields']))


# --------------------------------------------------------------------------- #
# 2. Circulation desk (#185) — issue → formulary → return → renew → fines.
# --------------------------------------------------------------------------- #
def circulation_route_checks():
    print('-- circ routes: issue / reader formulary / return / renew / fines')
    api, _core = _api(fixed_now=T0)
    H = _staff(api)
    ticket = '111'

    # Empty formulary before any loan.
    st, p = api.route('GET', '/api/circ/reader', {'ticket': [ticket]}, None, H)
    check('GET /api/circ/reader -> 200', st == 200)
    check('formulary empty before issue', p['data']['loans'] == [])
    check('formulary echoes the ticket', p['data']['reader']['ticket'] == ticket)

    # ISSUE the copy.
    st, p = api.route('POST', '/api/circ/issue', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    check('POST /api/circ/issue -> 200', st == 200)
    check('issue returns a loanId', isinstance(p['data'].get('loanId'), int))
    loan_id = p['data']['loanId']
    due = p['data']['due']
    check('issue reports a due date in the future', due > T0)
    check('issue flips catalog 910^A 0->1 (reported)',
          p['data'].get('exemplarStatus') == EXEMPLAR_ISSUED)
    check('issue flips catalog exemplar in the store',
          api.catalog.exemplar_status('IBIS', INV) == EXEMPLAR_ISSUED)
    check('catalog copy not available after issue',
          api.catalog.is_available('IBIS', INV) is False)

    # FORMULARY now shows the loan (field-40 card).
    st, p = api.route('GET', '/api/circ/reader', {'ticket': [ticket]}, None, H)
    check('formulary shows 1 loan after issue', len(p['data']['loans']) == 1)
    card = p['data']['loans'][0]
    check('loan card carries item (^B инв)', str(card['item']) == INV)
    check('loan card carries issued (^D) + due (^E)',
          card['issued'] == T0 and card['due'] == due)
    check('loan card carries the loanId', card['loanId'] == loan_id)
    check('reader on-hand count = 1', p['data']['reader']['onHand'] == 1)
    # frontend CircLoan/CircReader contract fields (additive, optional in api.ts).
    check('loan card carries overdue flag', card['overdue'] is False)
    check('loan card carries renewable flag', card['renewable'] is True)
    check('reader carries debtor flag', p['data']['reader']['debtor'] is False)
    check('formulary carries a messages list',
          isinstance(p['data']['messages'], list))

    # RENEW updates the due date (later than the first due).
    api._CIRC_NOW = lambda: T0 + 5 * DAY
    st, p = api.route('POST', '/api/circ/renew', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    check('POST /api/circ/renew -> 200', st == 200)
    new_due = p['data']['due']
    check('renew pushes the due date out', new_due > due)
    st, p = api.route('GET', '/api/circ/reader', {'ticket': [ticket]}, None, H)
    check('formulary reflects the renewed due',
          p['data']['loans'][0]['due'] == new_due)
    check('formulary shows 1 renewal', p['data']['loans'][0]['renewals'] == 1)

    # RETURN clears the loan and frees the catalog copy.
    api._CIRC_NOW = lambda: T0 + 6 * DAY
    st, p = api.route('POST', '/api/circ/return', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    check('POST /api/circ/return -> 200', st == 200)
    check('return reports ok', p['data']['ok'] is True)
    check('return flips catalog 910^A 1->0 (reported)',
          p['data'].get('exemplarStatus') == EXEMPLAR_FREE)
    check('return frees the catalog exemplar in the store',
          api.catalog.exemplar_status('IBIS', INV) == EXEMPLAR_FREE)
    check('catalog copy available again after return',
          api.catalog.is_available('IBIS', INV) is True)

    # FORMULARY cleared after return.
    st, p = api.route('GET', '/api/circ/reader', {'ticket': [ticket]}, None, H)
    check('formulary empty after return', p['data']['loans'] == [])
    check('reader on-hand count back to 0', p['data']['reader']['onHand'] == 0)

    # Returning a copy with no on-hand loan -> 404 (not 500).
    st, _ = api.route('POST', '/api/circ/return', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': 'NOPE'}, H)
    check('return of un-loaned item -> 404', st == 404)
    st, _ = api.route('POST', '/api/circ/renew', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': 'NOPE'}, H)
    check('renew of un-loaned item -> 404', st == 404)


def circ_fines_route_checks():
    print('-- circ routes: GET /api/circ/fines (formulary debt)')
    api, _core = _api(fixed_now=T0)
    H = _staff(api)
    ticket = '222'

    # No fines initially.
    st, p = api.route('GET', '/api/circ/fines', {'ticket': [ticket]}, None, H)
    check('GET /api/circ/fines -> 200', st == 200)
    check('no fines initially', p['data']['total'] == 0 and p['data']['items'] == [])
    check('fines report carries currency', 'currency' in p['data'])

    # Issue, then return WAY overdue → an overdue fine is charged and shows up.
    st, p = api.route('POST', '/api/circ/issue', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    check('issue for fines case -> 200', st == 200)
    # В01 max_return_days=20, fine_per_day _DEFAULT=5 → 30 days over grace accrues.
    api._CIRC_NOW = lambda: T0 + 60 * DAY
    st, p = api.route('POST', '/api/circ/return', {},
                      {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    check('overdue return -> 200', st == 200)
    check('overdue return charges a fine', p['data'].get('fineCharged', 0) > 0)

    st, p = api.route('GET', '/api/circ/fines', {'ticket': [ticket]}, None, H)
    check('fines now reports a positive total', p['data']['total'] > 0)
    check('fines lists the charged item',
          len(p['data']['items']) == 1
          and p['data']['items'][0]['kind'] == 'fine_overdue')
    # frontend CircFine contract aliases (id/reason/paid) present alongside canon.
    fine = p['data']['items'][0]
    check('fine carries id + reason + paid (frontend contract)',
          'id' in fine and 'reason' in fine and fine['paid'] is False)


def circ_formular_blocks_checks():
    print('-- circ routes: overdue formulary surfaces debtor block + overdue flag')
    api, _core = _api(fixed_now=T0)
    H = _staff(api)
    ticket = '555'

    api.route('POST', '/api/circ/issue', {},
              {'ticket': ticket, 'db': 'IBIS', 'item': INV}, H)
    # Jump well past the due date so the loan is a hard debtor + overdue.
    api._CIRC_NOW = lambda: T0 + 60 * DAY
    st, p = api.route('GET', '/api/circ/reader', {'ticket': [ticket]}, None, H)
    check('overdue formulary -> 200', st == 200)
    check('overdue loan flagged overdue', p['data']['loans'][0]['overdue'] is True)
    check('hard debtor surfaced debtor=True', p['data']['reader']['debtor'] is True)
    check('debtor block message present', len(p['data']['reader']['blocks']) > 0)


# --------------------------------------------------------------------------- #
# 3. Auth — guest AND reader get 403 on every staff circ/worklist route.
# --------------------------------------------------------------------------- #
STAFF_ROUTES = [
    ('GET', '/api/worklist/IBIS', None),
    ('GET', '/api/circ/reader', None),       # ?ticket= via query
    ('POST', '/api/circ/issue', {'ticket': '111', 'db': 'IBIS', 'item': INV}),
    ('POST', '/api/circ/return', {'ticket': '111', 'db': 'IBIS', 'item': INV}),
    ('POST', '/api/circ/renew', {'ticket': '111', 'db': 'IBIS', 'item': INV}),
    ('GET', '/api/circ/fines', None),        # ?ticket= via query
]


def auth_checks():
    print('-- auth: guest + reader 403 on every staff circ/worklist route')
    api, _core = _api()

    for label, headers in (('guest', _guest_headers(api)),
                           ('reader', _reader_headers(api))):
        for m, path, b in STAFF_ROUTES:
            q = {'ticket': ['111']}           # harmless for GET routes
            st, _payload = api.route(m, path, q, b, headers)
            check('%s denied on %s %s (403)' % (label, m, path), st == 403)

    # No session at all -> 401/403, never 200.
    for m, path, b in STAFF_ROUTES:
        st, _ = api.route(m, path, {'ticket': ['111']}, b, {})
        check('no session on %s %s -> 401/403' % (m, path), st in (401, 403))

    # Sanity: a staff session IS admitted (the guard isn't blanket-denying).
    H = _staff(api)
    st, _ = api.route('GET', '/api/worklist/IBIS', {}, None, H)
    check('staff admitted to /api/worklist/IBIS (200)', st == 200)
    st, _ = api.route('GET', '/api/circ/reader', {'ticket': ['111']}, None, H)
    check('staff admitted to /api/circ/reader (200)', st == 200)


# --------------------------------------------------------------------------- #
# 4. Entitlement gate — a disabled 'circulation' module refuses a valid grant.
# --------------------------------------------------------------------------- #
def entitlement_gate_checks():
    print('-- entitlement: disabled circulation module refuses a valid grant (403)')
    api, _core = _api()
    H = _staff(api)

    # Baseline: with entitlements open, the staff grant issues (200).
    st, _ = api.route('POST', '/api/circ/issue', {},
                      {'ticket': '333', 'db': 'IBIS', 'item': INV}, H)
    check('issue allowed when circulation module licensed', st == 200)

    orig = _core.entitlements.is_module_enabled
    # Disable the circulation module for this tenant (cataloging stays enabled).
    _core.entitlements.is_module_enabled = (
        lambda tenant, module, dsn=None: module != 'circulation')
    try:
        st, p = api.route('GET', '/api/circ/reader', {'ticket': ['333']}, None, H)
        check('circ formulary refused when module disabled (403)', st == 403)
        check('refusal cites module not licensed',
              'module not licensed' in (p.get('error', {}).get('message', '')))
        st, _ = api.route('POST', '/api/circ/return', {},
                          {'ticket': '333', 'db': 'IBIS', 'item': INV}, H)
        check('circ return refused when module disabled (403)', st == 403)
        # Cataloging worklist is a SEPARATE module — still allowed.
        st, _ = api.route('GET', '/api/worklist/IBIS', {}, None, H)
        check('worklist still allowed (cataloging module separate)', st == 200)
    finally:
        _core.entitlements.is_module_enabled = orig

    # Restored: issue works again once the module is licensed.
    st, _ = api.route('POST', '/api/circ/issue', {},
                      {'ticket': '444', 'db': 'IBIS', 'item': INV}, H)
    check('issue allowed again after module re-enabled', st == 200)


def main():
    worklist_route_checks()
    circulation_route_checks()
    circ_fines_route_checks()
    circ_formular_blocks_checks()
    auth_checks()
    entitlement_gate_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
