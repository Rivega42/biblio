#!/usr/bin/env python3
"""Discovery / façade backend endpoint tests (reader-portal homepage surfaces).

Covers the four discovery endpoints added to ``core.Api`` that power a richer
reader portal:

  1. GET /api/showcase   — "new arrivals / featured" brief cards (kind new|popular).
  2. GET /api/rubricator — browse a classification/navigator dictionary (terms+counts).
  3. GET /api/databases  — enriched with a per-DB ``count`` (additive, back-compat).
  4. GET /api/example-queries — seeded example search chips per DB.

House style mirrors tests/test_flk.py::api_checks — a constructed ``Api`` (whose
constructor does NOT connect to IRBIS) with a small in-memory ``FakeIrbis`` stub
injected over ``api.irbis``. So the suite is fully sqlite-green and requires NO
live ИРБИС server; the IRBIS-dependent branches are exercised against the stub,
and the "server briefly absent" path is exercised by a stub that raises
IrbisError — proving each endpoint degrades to an empty list rather than 500.

Invoked by the tests/test_access.py runner via the generic ``module_checks`` loop
(it imports the module and calls every ``*_checks()`` it defines, folding the
PASS/FAIL tally in), so the existing CI step that runs test_access.py also runs
this suite with no .github/ workflow change.

Standalone too::

    py -3.12 tests/test_discovery.py   ->  'ok …' lines + 'N passed, M failed'
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
# A tiny in-memory IRBIS stub: just the SessionManager surface the discovery
# endpoints touch. Records are shaped like irbis.parser.parse_record output
# (dict with a 'fields' list) so _brief_item works unchanged.
# --------------------------------------------------------------------------- #
def _fld(tag, value, subfields=None):
    return {'tag': tag, 'value': value, 'text': value, 'subfields': subfields or {}}


def _record(mfn, title, author=None, year=None, cover=False):
    fields = [_fld('200', title, {'A': title})]
    if author:
        fields.append(_fld('700', author, {'A': author}))
    if year:
        fields.append(_fld('210', year, {'D': year}))
    if cover:
        fields.append(_fld('953', 'cover', {'A': 'JPG', 'B': 'xx'}))
    return {'mfn': mfn, 'status': '0', 'version': '1', 'guid': None, 'fields': fields}


class FakeIrbis:
    """In-memory stand-in for SessionManager. ``raise_on`` names methods that
    should raise IrbisError (to exercise the graceful-degradation branches)."""

    def __init__(self, maxmfn=None, terms=None, dbmenu='', raise_on=()):
        # max_mfn returns the NEXT free MFN (one past the last real record),
        # mirroring the real 'O' command — so 5 records => maxmfn 6.
        self._maxmfn = maxmfn if maxmfn is not None else {}
        self._terms = terms or {}            # db -> [(count, term), ...] (sorted)
        self._dbmenu = dbmenu
        self.raise_on = set(raise_on)

    def _maybe_raise(self, name):
        if name in self.raise_on:
            from irbis.client import IrbisError
            raise IrbisError(-1, 'stub raise %s' % name)

    def max_mfn(self, db):
        self._maybe_raise('max_mfn')
        return self._maxmfn.get(db, 1)

    def read_record(self, db, mfn):
        self._maybe_raise('read_record')
        return _record(mfn, 'Заглавие %d' % mfn, author='Автор %d' % mfn,
                       year='20%02d' % (mfn % 100), cover=(mfn % 2 == 0))

    def read_terms(self, db, start, count=20):
        self._maybe_raise('read_terms')
        rows = self._terms.get(db, [])
        # mimic 'H': return up to ``count`` terms at-or-after ``start``.
        out = [(c, t) for (c, t) in rows if t >= start]
        return out[:count]

    def read_file(self, spec):
        self._maybe_raise('read_file')
        return self._dbmenu

    def format_record(self, db, mfn, pft='@brief'):
        return ''


def _api(fake):
    """Construct an Api (no IRBIS connection happens in __init__) and swap its
    session manager for the stub. JWT secret pinned for determinism."""
    os.environ['JWT_SECRET'] = 'discovery-test-secret'
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = fake
    return api, _core


def _guest(api):
    from access.authz import GUEST_GRANTS
    _tok, sess = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return _tok, sess


def _staff(api, grants=None):
    grants = grants if grants is not None else [
        {'function': 'search', 'db': '*', 'level': 'read'},
        {'function': 'terms', 'db': '*', 'level': 'read'},
        {'function': 'file', 'db': '*', 'level': 'read'},
    ]
    _tok, sess = api._new_session('staff', 'cataloger', grants, tenant='public')
    return _tok, sess


# --------------------------------------------------------------------------- #
# 1. /api/showcase — new arrivals.
# --------------------------------------------------------------------------- #
def showcase_checks():
    print('-- /api/showcase')
    # 6 -> 5 real records (mfn 1..5); newest first.
    api, _core = _api(FakeIrbis(maxmfn={'IBIS': 6}))
    _tok, guest = _guest(api)

    status, payload = api.showcase(guest, 'IBIS', 'new', 12)
    check('showcase returns 200', status == 200)
    check('showcase ok envelope', payload.get('ok') is True)
    data = payload['data']
    check('showcase kind echoed', data['kind'] == 'new')
    check('showcase returns 5 items (maxmfn 6 -> mfn 1..5)', len(data['items']) == 5)
    check('showcase newest first (mfn 5 leads)', data['items'][0]['mfn'] == 5)
    check('showcase last item is mfn 1', data['items'][-1]['mfn'] == 1)
    it = data['items'][0]
    check('showcase item has title', bool(it['title']))
    check('showcase item has author', 'author' in it)
    check('showcase item carries cover flag', 'hasCover' in it)

    # limit caps the result
    status, payload = api.showcase(guest, 'IBIS', 'new', 3)
    check('showcase honors limit=3', len(payload['data']['items']) == 3)
    check('showcase limit echoed', payload['data']['limit'] == 3)

    # kind=popular falls back to new (same most-recent set for now)
    status, payload = api.showcase(guest, 'IBIS', 'popular', 12)
    check('showcase kind=popular accepted', payload['data']['kind'] == 'popular')
    check('showcase popular falls back to recent set',
          [i['mfn'] for i in payload['data']['items']] == [5, 4, 3, 2, 1])

    # unknown kind normalises to new
    status, payload = api.showcase(guest, 'IBIS', 'zzz', 12)
    check('showcase unknown kind -> new', payload['data']['kind'] == 'new')

    # empty DB (maxmfn 1 -> no real records) -> graceful empty list
    api2, _ = _api(FakeIrbis(maxmfn={'IBIS': 1}))
    _t2, g2 = _guest(api2)
    status, payload = api2.showcase(g2, 'IBIS', 'new', 12)
    check('showcase on empty DB -> 200 + []', status == 200 and payload['data']['items'] == [])

    # server briefly absent (max_mfn raises) -> empty list, NOT a 500
    api3, _ = _api(FakeIrbis(raise_on=('max_mfn',)))
    _t3, g3 = _guest(api3)
    status, payload = api3.showcase(g3, 'IBIS', 'new', 12)
    check('showcase degrades on IrbisError -> 200 + []',
          status == 200 and payload['data']['items'] == [])


# --------------------------------------------------------------------------- #
# 2. /api/rubricator — navigator dictionary browse.
# --------------------------------------------------------------------------- #
def rubricator_checks():
    print('-- /api/rubricator')
    terms = {'IBIS': [
        (12, 'G=20 Физика'),
        (8, 'G=27 Математика'),
        (3, 'G=50 Информатика'),
        (1, 'H=другое'),                     # different prefix -> must be excluded
    ]}
    api, _core = _api(FakeIrbis(terms=terms))
    _tok, guest = _guest(api)

    status, payload = api.rubricator(guest, 'IBIS', 'G=', '', 30)
    check('rubricator returns 200', status == 200)
    data = payload['data']
    check('rubricator prefix echoed', data['prefix'] == 'G=')
    check('rubricator keeps only G= terms (3)', len(data['terms']) == 3)
    check('rubricator stops at first non-prefix term (H= excluded)',
          all(t['term'].startswith('G=') for t in data['terms']))
    first = data['terms'][0]
    check('rubricator strips the prefix into value',
          first['value'] == '20 Физика' and first['term'] == 'G=20 Физика')
    check('rubricator carries posting count', first['count'] == 12)
    check('rubricator builds a runnable expr', first['expr'] == '"G=20 Физика"')

    # limit is honoured
    status, payload = api.rubricator(guest, 'IBIS', 'G=', '', 2)
    check('rubricator honors limit=2', len(payload['data']['terms']) == 2)

    # a prefix with no terms -> graceful empty list
    status, payload = api.rubricator(guest, 'IBIS', 'ZZ=', '', 30)
    check('rubricator empty prefix block -> []', payload['data']['terms'] == [])

    # server briefly absent (read_terms raises) -> empty list, NOT a 500
    api2, _ = _api(FakeIrbis(raise_on=('read_terms',)))
    _t2, g2 = _guest(api2)
    status, payload = api2.rubricator(g2, 'IBIS', 'G=', '', 30)
    check('rubricator degrades on IrbisError -> 200 + []',
          status == 200 and payload['data']['terms'] == [])


# --------------------------------------------------------------------------- #
# 3. /api/databases — enriched with per-DB count (additive, back-compat).
# --------------------------------------------------------------------------- #
def databases_count_checks():
    print('-- /api/databases (count enrichment)')
    menu = 'IBIS\nКнига\nRDR\nЧитатели\n'
    api, _core = _api(FakeIrbis(maxmfn={'IBIS': 101, 'RDR': 51}, dbmenu=menu))
    _tok, staff = _staff(api)

    status, payload = api.databases(staff)
    check('databases returns 200', status == 200)
    items = payload['data']['items']
    check('databases lists both DBs', {i['code'] for i in items} == {'IBIS', 'RDR'})
    by = {i['code']: i for i in items}
    # back-compat fields preserved
    check('databases keeps code/name/public', all(
        k in by['IBIS'] for k in ('code', 'name', 'public')))
    check('databases IBIS is public', by['IBIS']['public'] is True)
    check('databases RDR is service (not public)', by['RDR']['public'] is False)
    # additive count = maxmfn - 1
    check('databases IBIS count = maxmfn-1 (100)', by['IBIS']['count'] == 100)
    check('databases RDR count = maxmfn-1 (50)', by['RDR']['count'] == 50)

    # counts=0 opt-out omits the field entirely (back-compat shape)
    status, payload = api.databases(staff, with_counts=False)
    by2 = {i['code']: i for i in payload['data']['items']}
    check('databases counts opt-out omits count field', 'count' not in by2['IBIS'])

    # count unavailable (max_mfn raises) -> field omitted gracefully, list still returned
    api2, _ = _api(FakeIrbis(maxmfn={}, dbmenu=menu, raise_on=('max_mfn',)))
    _t2, s2 = _staff(api2)
    status, payload = api2.databases(s2)
    check('databases still returns list when count fails', status == 200
          and len(payload['data']['items']) == 2)
    check('databases omits count when max_mfn fails',
          all('count' not in i for i in payload['data']['items']))

    # no session -> Denied(401)
    denied = False
    try:
        api.databases(None)
    except _core.Denied as d:
        denied = d.status == 401
    check('databases requires a session (401)', denied)


# --------------------------------------------------------------------------- #
# 4. /api/example-queries — seeded chips per DB (no IRBIS).
# --------------------------------------------------------------------------- #
def example_queries_checks():
    print('-- /api/example-queries')
    api, _core = _api(FakeIrbis())          # never touches IRBIS
    _tok, guest = _guest(api)

    status, payload = api.example_queries(guest, 'IBIS')
    check('example-queries returns 200', status == 200)
    ex = payload['data']['examples']
    check('example-queries returns chips', len(ex) >= 1)
    chip = ex[0]
    check('chip has label/prefix/expr', all(k in chip for k in ('label', 'prefix', 'expr')))
    check('chip expr is a quoted IRBIS query', chip['expr'].startswith('"') and '=' in chip['expr'])
    # author chips get the right-truncation '$' (matches build_expr semantics)
    a_chips = [c for c in ex if c['prefix'] == 'A']
    check('author chip expr is right-truncated',
          (not a_chips) or a_chips[0]['expr'].endswith('$"'))

    # unknown DB -> default chip set (graceful), still 200
    status, payload = api.example_queries(guest, 'NOPE')
    check('example-queries falls back to default chips for unknown DB',
          status == 200 and len(payload['data']['examples']) >= 1)


# --------------------------------------------------------------------------- #
# 5. Routing + access control through Api.route() (the real dispatch path).
# --------------------------------------------------------------------------- #
def routing_checks():
    print('-- route() dispatch + access control')
    menu = 'IBIS\nКнига\n'
    fake = FakeIrbis(maxmfn={'IBIS': 6}, dbmenu=menu, terms={'IBIS': [
        (5, 'G=20 Физика'), (2, 'G=27 Математика')]})
    api, _core = _api(fake)
    tok, _sess = _guest(api)
    h = {'authorization': 'Bearer ' + tok}

    status, payload = api.route('GET', '/api/showcase', {'db': ['IBIS'], 'limit': ['4']}, None, h)
    check('route GET /api/showcase -> 200', status == 200)
    check('route showcase respects limit param', len(payload['data']['items']) == 4)

    status, payload = api.route('GET', '/api/rubricator',
                                {'db': ['IBIS'], 'prefix': ['G=']}, None, h)
    check('route GET /api/rubricator -> 200', status == 200)
    check('route rubricator returns prefix terms', len(payload['data']['terms']) == 2)

    status, payload = api.route('GET', '/api/example-queries', {'db': ['IBIS']}, None, h)
    check('route GET /api/example-queries -> 200', status == 200)

    status, payload = api.route('GET', '/api/databases', {'db': ['IBIS']}, None, h)
    check('route GET /api/databases -> 200', status == 200)
    check('route databases carries count', payload['data']['items'][0].get('count') == 5)

    # ?counts=0 opt-out via the query string
    status, payload = api.route('GET', '/api/databases', {'counts': ['0']}, None, h)
    check('route databases ?counts=0 omits count',
          'count' not in payload['data']['items'][0])

    # No token at all -> showcase still guard-checks; guest grants are required.
    # A request with NO Authorization header has no session -> search guard 401.
    status, payload = api.route('GET', '/api/showcase', {'db': ['IBIS']}, None, {})
    check('route showcase without session -> 401',
          status == 401 and payload['ok'] is False)

    # A staff session WITHOUT the search grant is denied showcase (403).
    notok, _ns = _staff(api, grants=[{'function': 'file', 'db': '*', 'level': 'read'}])
    hh = {'authorization': 'Bearer ' + notok}
    status, payload = api.route('GET', '/api/showcase', {'db': ['IBIS']}, None, hh)
    check('route showcase without search grant -> 403', status == 403)


def main():
    showcase_checks()
    rubricator_checks()
    databases_count_checks()
    example_queries_checks()
    routing_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
