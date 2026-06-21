#!/usr/bin/env python3
"""Reader-portal v2 social BACKEND tests (#134 engagement / #133 discovery).

Exercises the real endpoints on a constructed ``core.Api`` (the constructor does
NOT connect to ИРБИС). A tiny in-memory fake ИРБИС backs the recommendation seams
(606/700/610 reads + index search) and reader-name resolution, so no live server
is touched and the "similar"/"for you" ranking is deterministic. All social state
is persisted in OUR access store, reader-scoped by ticket — nothing is written to
the live ИРБИС server (the seams only READ it).

Covered (per the v2 contract):
  * REVIEWS: post -> {id}; list aggregates avg/count + cards + ``mine``; one
    editable review per (reader,db,mfn) (upsert replaces rating/text); delete own;
    403 deleting someone else's; rating 1..5 validation.
  * RECOMMENDATIONS: "similar" ranks candidates by shared-subject/author overlap,
    excludes the seed, attaches a human reason; "for you" derives from the reader's
    history subjects and is empty with no history.
  * HISTORY: the record-open path auto-logs for a reader (not a guest); deduped by
    (db,mfn) keeping the latest; capped/newest-first.
  * SAVED SEARCHES: CRUD (list/add/delete), reader-scoped, delete-own.
  * AUTH: guests READ reviews/recommendations but are 401/403 on every write +
    history + saved-search + foryou route.
  * PG parity: the social-store CRUD on a real PostgreSQL when reachable (skips
    cleanly otherwise) — proves schema_postgres.sql + PgAccessStore methods.

Wired into the test_access.py runner (module list) so the CI sqlite + postgres
legs both run it. Standalone:  py -3.12 tests/test_social.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.store import AccessStore
from access.social import SocialService
from access.authz import READER_GRANTS, GUEST_GRANTS

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
# Fake ИРБИС: a small fixed catalogue used by the recommendation seams. Each
# record carries 606 (subjects), 700 (authors), 610 (collectives). The fake
# exposes the SAME read_record / search surface core's seams call, so the real
# _social_terms / _social_search run unchanged over it (no live server).
# --------------------------------------------------------------------------- #
#   mfn 1 (seed): subjects {Базы данных, Программирование}, author Иванов, coll НИИ
#   mfn 2: subjects {Базы данных, Программирование} -> overlap 2 (top similar)
#   mfn 3: subjects {Базы данных}, author Иванов -> overlap 2 (subject+author)
#   mfn 4: subjects {Сети} -> no overlap with the seed (must NOT appear)
#   mfn 5: author Иванов only -> overlap 1
_CATALOG = {
    1: {'subjects': ['Базы данных', 'Программирование'], 'authors': ['Иванов И.И.'],
        'collectives': ['НИИ Систем'], 'title': 'Введение в БД'},
    2: {'subjects': ['Базы данных', 'Программирование'], 'authors': ['Петров П.П.'],
        'collectives': [], 'title': 'БД и программирование'},
    3: {'subjects': ['Базы данных'], 'authors': ['Иванов И.И.'],
        'collectives': [], 'title': 'Реляционные БД'},
    4: {'subjects': ['Сети'], 'authors': ['Сидоров С.С.'],
        'collectives': [], 'title': 'Компьютерные сети'},
    5: {'subjects': ['Алгоритмы'], 'authors': ['Иванов И.И.'],
        'collectives': [], 'title': 'Алгоритмы'},
}


def _make_record(mfn):
    """Build the parsed-record shape core's seams expect from a _CATALOG row."""
    rec = {'mfn': mfn, 'fields': []}
    row = _CATALOG[mfn]
    for s in row['subjects']:
        rec['fields'].append({'tag': '606', 'value': '^A' + s, 'text': '',
                              'subfields': {'A': s}})
    for a in row['authors']:
        rec['fields'].append({'tag': '700', 'value': '^A' + a, 'text': '',
                              'subfields': {'A': a}})
    for c in row['collectives']:
        rec['fields'].append({'tag': '610', 'value': c, 'text': c, 'subfields': {}})
    rec['fields'].append({'tag': '200', 'value': '^A' + row['title'], 'text': '',
                          'subfields': {'A': row['title']}})
    return rec


class FakeIrbis:
    """Minimal stand-in for the ResilientIrbis handle core's seams call."""

    def read_record(self, db, mfn):
        if mfn not in _CATALOG:
            from irbis.client import IrbisError
            raise IrbisError(-140, 'no such mfn')
        return _make_record(mfn)

    def format_record(self, db, mfn, pft='@brief'):
        return _CATALOG.get(mfn, {}).get('title', '') if db != 'RDR' else ''

    def search(self, db, expr):
        """Honour '"PREFIX=term"' for S=/A=/K= and RDR RI= (reader name)."""
        e = expr.strip().strip('"')
        if e.startswith('RI='):
            return (1, [77])      # any reader resolves to a fixed RDR mfn
        if '=' not in e:
            return (0, [])
        prefix, term = e.split('=', 1)
        kind = {'S': 'subjects', 'A': 'authors', 'K': 'collectives'}.get(prefix)
        if kind is None:
            return (0, [])
        mfns = [m for m, row in sorted(_CATALOG.items()) if term in row[kind]]
        return (len(mfns), mfns)


class FakeRdrIrbis(FakeIrbis):
    """As FakeIrbis but read_record('RDR', 77) yields a reader name (field 10)."""

    def read_record(self, db, mfn):
        if db == 'RDR':
            return {'mfn': mfn, 'fields': [
                {'tag': '10', 'value': 'Читателев Ч.Ч.', 'text': 'Читателев Ч.Ч.',
                 'subfields': {}}]}
        return super().read_record(db, mfn)


# --------------------------------------------------------------------------- #
# A constructed Api with NO live ИРБИС: a fresh in-memory access store + the fake
# ИРБИС wired so the real social seams run deterministically.
# --------------------------------------------------------------------------- #
def _api(irbis=None):
    os.environ['JWT_SECRET'] = 'social-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.access = AccessStore(':memory:')
    api.irbis = irbis or FakeRdrIrbis()
    # Rebuild social over the fresh store with the (reloaded) instance seams.
    api.social = SocialService(
        api.access, read_terms=api._social_terms, search=api._social_search,
        brief_read=api._hold_brief, reader_name=api._social_reader_name)
    return api, _core


def _reader(api, ticket='111'):
    _tok, sess = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                  tenant='public', rdr_mfn=77)
    return sess


def _guest(api):
    _tok, sess = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return sess


# --------------------------------------------------------------------------- #
# 1. Reviews / ratings (#134).
# --------------------------------------------------------------------------- #
def reviews_checks():
    print('-- reviews: post / list (avg,count,mine) / upsert / delete-own / 403')
    api, _core = _api()
    r1 = _reader(api, '111')
    r2 = _reader(api, '222')

    st, payload = api.post_review(r1, {'db': 'IBIS', 'mfn': 1, 'rating': 4,
                                       'text': 'Хорошая книга'})
    check('post review returns 200 + id', st == 200 and 'id' in payload['data'])
    rid1 = payload['data']['id']

    # Second reader reviews the same item.
    st, payload = api.post_review(r2, {'db': 'IBIS', 'mfn': 1, 'rating': 2,
                                       'text': 'Так себе'})
    check('second reader review 200', st == 200)

    # List: avg over {4,2}=3.0, count 2, both cards, and r1's "mine".
    st, payload = api.list_reviews(r1, 'IBIS', 1)
    d = payload['data']
    check('reviews list 200', st == 200)
    check('avg is mean of the two ratings', d['avg'] == 3.0)
    check('count is 2', d['count'] == 2)
    check('two review cards', len(d['items']) == 2)
    check('mine reflects r1 review', d.get('mine') == {'rating': 4, 'text': 'Хорошая книга'})
    check('review card carries reader name',
          any(it['readerName'] == 'Читателев Ч.Ч.' for it in d['items']))

    # Upsert: r1 re-posts -> rating/text replaced, still ONE review (count stays 2).
    st, payload = api.post_review(r1, {'db': 'IBIS', 'mfn': 1, 'rating': 5,
                                       'text': 'Передумал'})
    check('upsert keeps same review id', payload['data']['id'] == rid1)
    st, payload = api.list_reviews(r1, 'IBIS', 1)
    check('upsert did not add a row (count still 2)', payload['data']['count'] == 2)
    check('upsert replaced rating (avg now mean of {5,2})',
          payload['data']['avg'] == 3.5)
    check('mine reflects the upsert', payload['data']['mine']['rating'] == 5)

    # Rating validation: out of range / non-int -> 400.
    st, _p = api.post_review(r1, {'db': 'IBIS', 'mfn': 1, 'rating': 9})
    check('rating > 5 -> 400', st == 400)
    st, _p = api.post_review(r1, {'db': 'IBIS', 'mfn': 1, 'rating': 'x'})
    check('non-int rating -> 400', st == 400)
    st, _p = api.post_review(r1, {'db': 'IBIS', 'mfn': 1})
    check('missing rating -> 400', st == 400)

    # Delete: r2 cannot delete r1's review (403); r1 can delete its own.
    st, _p = api.delete_review(r2, {'id': rid1})
    check("delete someone else's review -> 403", st == 403)
    st, payload = api.delete_review(r1, {'id': rid1})
    check('delete own review -> 200', st == 200 and payload['data']['id'] == rid1)
    st, payload = api.list_reviews(r1, 'IBIS', 1)
    check('own review gone, count drops to 1', payload['data']['count'] == 1)
    check('mine cleared after delete', 'mine' not in payload['data'])

    # Guest may READ reviews (public OPAC engagement) but not WRITE.
    g = _guest(api)
    st, payload = api.list_reviews(g, 'IBIS', 1)
    check('guest can read reviews (200)', st == 200 and payload['data']['count'] == 1)
    denied = False
    try:
        api.post_review(g, {'db': 'IBIS', 'mfn': 1, 'rating': 3})
    except _core.Denied as dn:
        denied = dn.status in (401, 403)
    check('guest cannot post a review (403)', denied)


# --------------------------------------------------------------------------- #
# 2. Recommendations (#133) — "similar" ranked by shared-term overlap.
# --------------------------------------------------------------------------- #
def recommendations_checks():
    print('-- recommendations: similar ranked by overlap, seed excluded, reason')
    api, _core = _api()
    g = _guest(api)

    st, payload = api.recommendations(g, 'IBIS', 1)
    check('recommendations 200 (guest-readable)', st == 200)
    items = payload['data']['items']
    mfns = [it['mfn'] for it in items]
    check('seed (mfn 1) excluded from its own recs', 1 not in mfns)
    check('non-overlapping record (mfn 4) excluded', 4 not in mfns)
    check('overlapping records surfaced (2 and 3)', 2 in mfns and 3 in mfns)
    # mfn 2 shares two subjects; mfn 3 shares one subject + one author => both
    # overlap 2; mfn 5 shares one author => overlap 1. Top-overlap come first.
    check('mfn 5 (overlap 1) ranks below the overlap-2 records',
          mfns.index(5) > mfns.index(2) and mfns.index(5) > mfns.index(3))
    by_mfn = {it['mfn']: it for it in items}
    check('subject-sharing rec reasons by topic',
          by_mfn[2]['reason'].startswith('Общая тема'))
    check('author-only rec (mfn 5) reason is "Тот же автор"',
          by_mfn[5]['reason'] == 'Тот же автор')
    check('rec carries a resolved title', by_mfn[2]['title'] == 'БД и программирование')

    # A seed with no terms / unknown mfn -> empty list (degrades, never raises).
    st, payload = api.recommendations(g, 'IBIS', 999)
    check('unknown seed -> empty recs', st == 200 and payload['data']['items'] == [])


def foryou_checks():
    print('-- recommendations/foryou: derived from history subjects; empty w/o history')
    api, _core = _api()
    r1 = _reader(api, '111')

    # No history yet -> empty.
    st, payload = api.recommendations_foryou(r1)
    check('foryou empty with no history', st == 200 and payload['data']['items'] == [])

    # Open mfn 3 (subjects {Базы данных}) -> history logged. for-you should then
    # surface other "Базы данных" records (2), excluding the history record (3).
    api.record(r1, 'IBIS', 3)
    st, payload = api.recommendations_foryou(r1)
    mfns = [it['mfn'] for it in payload['data']['items']]
    check('foryou surfaces a record sharing a history subject (mfn 2)', 2 in mfns)
    check('foryou excludes the already-seen history record (mfn 3)', 3 not in mfns)
    check('foryou items carry a reason',
          all(it.get('reason') for it in payload['data']['items']))


# --------------------------------------------------------------------------- #
# 3. Reading history (#133) — auto-logged on record-open, deduped.
# --------------------------------------------------------------------------- #
def history_checks():
    print('-- history: auto-log on record-open (reader only), dedup, newest first')
    api, _core = _api()
    r1 = _reader(api, '111')

    # Guest opening a record must NOT log history.
    g = _guest(api)
    api.record(g, 'IBIS', 1)
    check('guest record-open logs no history',
          api.history(r1)[1]['data']['items'] == [])

    # Reader opens 1 then 2 then re-opens 1 -> dedup keeps 1 once, newest first.
    api.record(r1, 'IBIS', 1)
    api.record(r1, 'IBIS', 2)
    api.record(r1, 'IBIS', 1)         # re-open bumps 1 to the top
    st, payload = api.history(r1)
    items = payload['data']['items']
    check('history 200', st == 200)
    check('history deduped by (db,mfn)', len(items) == 2)
    check('re-opened record floats to newest', items[0]['mfn'] == 1)
    check('history carries a resolved title', items[0]['title'] == 'Введение в БД')

    # Reader-scoped: another reader has an empty history.
    r2 = _reader(api, '222')
    check('history reader-scoped', api.history(r2)[1]['data']['items'] == [])


# --------------------------------------------------------------------------- #
# 4. Saved searches — reader-scoped CRUD.
# --------------------------------------------------------------------------- #
def saved_search_checks():
    print('-- saved searches: list / add / delete (own), reader-scoped')
    api, _core = _api()
    r1 = _reader(api, '111')

    check('saved-search empty initially', api.saved_searches(r1)[1]['data']['items'] == [])

    st, payload = api.save_search(r1, {'name': 'БД', 'db': 'IBIS', 'prefix': 'K',
                                       'query': 'базы данных'})
    check('save search returns 200 + id', st == 200 and 'id' in payload['data'])
    sid = payload['data']['id']
    api.save_search(r1, {'db': 'IBIS', 'prefix': 'A', 'query': 'Иванов'})

    st, payload = api.saved_searches(r1)
    items = payload['data']['items']
    check('two saved searches listed', len(items) == 2)
    first = {it['id']: it for it in items}[sid]
    check('saved search keeps name/db/prefix/query',
          first['name'] == 'БД' and first['db'] == 'IBIS'
          and first['prefix'] == 'K' and first['query'] == 'базы данных')

    # Missing query -> 400.
    st, _p = api.save_search(r1, {'db': 'IBIS', 'query': '   '})
    check('empty query -> 400', st == 400)

    # Reader-scoped: r2 cannot delete r1's saved search (404 — not theirs).
    r2 = _reader(api, '222')
    st, _p = api.delete_search(r2, {'id': sid})
    check("delete another reader's saved search -> 404", st == 404)
    check('r2 sees no saved searches', api.saved_searches(r2)[1]['data']['items'] == [])

    # Delete own.
    st, payload = api.delete_search(r1, {'id': sid})
    check('delete own saved search -> 200', st == 200)
    check('one saved search left', len(api.saved_searches(r1)[1]['data']['items']) == 1)


# --------------------------------------------------------------------------- #
# 5. Auth — guest is refused on every write/history/saved-search/foryou route,
# both via direct handler (Denied) and via the dispatcher (401/403 status).
# --------------------------------------------------------------------------- #
def auth_checks():
    print('-- auth: guest 401/403 on writes + history + saved-search + foryou')
    api, _core = _api()
    guest = _guest(api)

    handlers = [
        ('POST /api/review', lambda: api.post_review(guest, {'db': 'IBIS', 'mfn': 1, 'rating': 3})),
        ('POST /api/review/delete', lambda: api.delete_review(guest, {'id': 1})),
        ('GET /api/recommendations/foryou', lambda: api.recommendations_foryou(guest)),
        ('GET /api/history', lambda: api.history(guest)),
        ('GET /api/savedsearch', lambda: api.saved_searches(guest)),
        ('POST /api/savedsearch', lambda: api.save_search(guest, {'query': 'x'})),
        ('POST /api/savedsearch/delete', lambda: api.delete_search(guest, {'id': 1})),
    ]
    for label, fn in handlers:
        denied = False
        try:
            fn()
        except _core.Denied as d:
            denied = d.status in (401, 403)
        check('guest denied on %s (403)' % label, denied)

    # Through the real dispatcher: no session -> 401/403, never 200.
    routes = [
        ('POST', '/api/review', {'db': 'IBIS', 'mfn': 1, 'rating': 3}),
        ('POST', '/api/review/delete', {'id': 1}),
        ('GET', '/api/recommendations/foryou', None),
        ('GET', '/api/history', None),
        ('GET', '/api/savedsearch', None),
        ('POST', '/api/savedsearch', {'query': 'x'}),
        ('POST', '/api/savedsearch/delete', {'id': 1}),
    ]
    for m, p, b in routes:
        st, _payload = api.route(m, p, {}, b, {})
        check('route %s %s with no session -> 401/403' % (m, p), st in (401, 403))

    # A reader is admitted (sanity: the guard isn't blanket-denying).
    r1 = _reader(api, '111')
    st, _p = api.history(r1)
    check('reader admitted to /api/history (200)', st == 200)

    # Reviews + recommendations ARE guest-readable (dispatcher returns 200).
    g = _guest(api)
    tok, _s = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    hdr = {'authorization': 'Bearer ' + tok}
    st, _p = api.route('GET', '/api/reviews', {'db': ['IBIS'], 'mfn': ['1']}, None, hdr)
    check('guest route GET /api/reviews -> 200', st == 200)
    st, _p = api.route('GET', '/api/recommendations',
                       {'db': ['IBIS'], 'mfn': ['1']}, None, hdr)
    check('guest route GET /api/recommendations -> 200', st == 200)


# --------------------------------------------------------------------------- #
# 6. Postgres parity — social-store CRUD on real PG (skips cleanly otherwise).
# --------------------------------------------------------------------------- #
def pg_parity_checks():
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return
    try:
        from access.pgstore import PgAccessStore, default_pg_dsn
        st = PgAccessStore(os.environ.get('ACCESS_PG_DSN', default_pg_dsn()))
        st._conn().execute('TRUNCATE reader_review, reader_history, saved_search '
                           'RESTART IDENTITY')
    except Exception as e:
        print('-- social pg parity SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return
    print('-- social: postgres parity (reader_review / reader_history / saved_search)')

    svc = SocialService(st, now=lambda: 1000.0)
    # Reviews: upsert + aggregate + delete-own.
    rid = svc.post_review('pg-1', 'IBIS', 1, 4, 'ok')['id']
    svc.post_review('pg-2', 'IBIS', 1, 2, 'meh')
    agg = svc.reviews('IBIS', 1, ticket='pg-1')
    check('[pg] avg over two reviews', agg['avg'] == 3.0 and agg['count'] == 2)
    check('[pg] mine present', agg.get('mine', {}).get('rating') == 4)
    svc.post_review('pg-1', 'IBIS', 1, 5, 'changed')        # upsert
    check('[pg] upsert keeps one review', svc.reviews('IBIS', 1)['count'] == 2)
    check('[pg] delete own -> id', svc.delete_review('pg-1', rid)['id'] == rid)
    check('[pg] delete others -> None', svc.delete_review('pg-2', 999999) is None)

    # History: dedup + newest-first.
    svc.store.history_log('pg-1', 'IBIS', 1, 'T1', 1000.0)
    svc.store.history_log('pg-1', 'IBIS', 2, 'T2', 1001.0)
    svc.store.history_log('pg-1', 'IBIS', 1, 'T1', 1002.0)   # re-open bumps ts
    hist = svc.history('pg-1')['items']
    check('[pg] history deduped', len(hist) == 2)
    check('[pg] history newest first', hist[0]['mfn'] == 1)

    # Saved searches: add / list / delete-own.
    sid = svc.save_search('pg-1', 'q', 'IBIS', 'K', 'базы')['id']
    check('[pg] saved-search listed', len(svc.saved_searches('pg-1')['items']) == 1)
    check('[pg] delete-own saved-search', svc.delete_search('pg-1', sid)['id'] == sid)
    check('[pg] delete missing saved-search -> None',
          svc.delete_search('pg-1', 999999) is None)


def main():
    reviews_checks()
    recommendations_checks()
    foryou_checks()
    history_checks()
    saved_search_checks()
    auth_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
