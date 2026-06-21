#!/usr/bin/env python3
"""Reader-portal #222 BACKEND tests — holds + queue, notification inbox, shelves.

Exercises the real endpoints on a constructed ``core.Api`` (the constructor does
NOT connect to ИРБИС), with the title-resolution seam stubbed so no live server is
touched. All state is persisted in OUR access store / notification queue, reader-
scoped by ticket — nothing is written to the live ИРБИС server.

Covered (per the #222 contract):
  * HOLDS: place -> ``ready`` when a copy is free, ``queued``+position when taken; a
    second reader gets position 2; idempotent re-hold; list; cancel.
  * INBOX: a circulation-dispatched notice (real ``CirculationEngine._emit`` ->
    persistent queue) appears in the addressed reader's inbox; unread count drops
    after marking read (one + all); reader-scoped (one reader can't see another's).
  * SHELVES: the two system lists seed lazily on first GET; add / remove / dedup;
    create a custom list.
  * AUTH: a guest session is refused (401/403) on every reader-portal route.

Wired into the test_access.py runner (module list) so the CI sqlite + postgres
legs both run it. Standalone-runnable in the house style:
  py -3.12 tests/test_portal222.py  -> ok ... + "N passed, M failed" + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.store import AccessStore
from access import notifications as nt
from access import circulation as circ
from access.holds import HoldService
from access.shelves import ShelfService, SYSTEM_IDS
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
# A constructed Api with NO live ИРБИС: stub the brief-read seam, and rebuild the
# reader-portal services over a fresh in-memory access store + queue so each test
# group is isolated and fast.
# --------------------------------------------------------------------------- #
def _api(brief=None):
    os.environ['JWT_SECRET'] = 'portal222-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    # Fresh, isolated, in-memory persistence (no live server, no temp files).
    api.access = AccessStore(':memory:')
    api.notifications = nt.NotificationQueue(':memory:')
    api.circulation = circ.CirculationEngine(
        store=circ.CirculationStore(':memory:'), notifications=api.notifications)
    seam = brief or (lambda db, mfn: {'title': 'Заглавие %d' % mfn})
    api.holds = HoldService(api.access, catalog=None, brief_read=seam)
    api.shelves = ShelfService(api.access, brief_read=seam)
    return api, _core


def _reader(api, ticket='111'):
    _tok, sess = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                  tenant='public', rdr_mfn=1)
    return sess


def _guest(api):
    _tok, sess = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return sess


# --------------------------------------------------------------------------- #
# 1. Holds — ready / queued / position / idempotency / list / cancel.
# --------------------------------------------------------------------------- #
def holds_checks():
    print('-- holds: place (ready/queued), position, cancel')
    api, _core = _api()
    r1 = _reader(api, '111')

    # First hold on a free item (no catalog opinion -> first-in-line surfaced ready).
    st, payload = api.place_hold(r1, {'db': 'IBIS', 'mfn': 42})
    check('place hold returns 200', st == 200)
    d = payload['data']
    check('first hold is ready', d['status'] == 'ready')
    check('first hold position 1', d['position'] == 1)
    hold1 = d['holdId']

    # Idempotent re-hold: same reader, same item -> existing hold returned.
    st, payload = api.place_hold(r1, {'db': 'IBIS', 'mfn': 42})
    check('re-hold idempotent (same holdId)', payload['data']['holdId'] == hold1)
    check('re-hold keeps position 1', payload['data']['position'] == 1)

    # Second reader on the SAME item -> queued at position 2.
    r2 = _reader(api, '222')
    st, payload = api.place_hold(r2, {'db': 'IBIS', 'mfn': 42})
    check('second reader queued', payload['data']['status'] == 'queued')
    check('second reader position 2', payload['data']['position'] == 2)

    # GET /api/holds for r1: one live hold, title resolved, position present.
    st, payload = api.list_holds(r1)
    items = payload['data']['items']
    check('list_holds returns the reader hold', len(items) == 1)
    check('hold card carries resolved title', items[0]['title'] == 'Заглавие 42')
    check('hold card carries db/mfn', items[0]['db'] == 'IBIS' and items[0]['mfn'] == 42)
    check('hold card position 1', items[0]['position'] == 1)

    # r2 only sees its own hold (reader-scoped).
    st, payload = api.list_holds(r2)
    check('holds reader-scoped (r2 sees only its own)',
          len(payload['data']['items']) == 1 and
          payload['data']['items'][0]['holdId'] != hold1)

    # Cancel r1's hold -> cancelled; then r2 (still queued) is now alone.
    st, payload = api.cancel_hold(r1, {'holdId': hold1})
    check('cancel returns 200', st == 200)
    check('cancel reports cancelled', payload['data']['status'] == 'cancelled')
    st, payload = api.list_holds(r1)
    check('cancelled hold drops from r1 list', payload['data']['items'] == [])

    # Cancelling someone else's / a missing hold -> 404 (not the reader's live hold).
    st, payload = api.cancel_hold(r1, {'holdId': 999999})
    check('cancel of missing hold -> 404', st == 404)

    # A fresh reader now first in line on a previously-taken item is queued behind
    # the still-live r2 hold (FIFO honoured across cancels).
    st, payload = api.place_hold(_reader(api, '333'), {'db': 'IBIS', 'mfn': 42})
    check('new holder queues behind the surviving r2 hold (position 2)',
          payload['data']['status'] == 'queued' and payload['data']['position'] == 2)


def holds_availability_checks():
    print('-- holds: catalog availability drives ready vs queued')

    class _Cat:
        """Minimal catalog seam: item is issued (not free)."""
        def find_exemplar(self, db, item):
            return (1, 0, {'b': item})

        def is_available(self, db, item):
            return False    # taken -> first holder must be QUEUED, not ready

    api, _core = _api()
    api.holds = HoldService(api.access, catalog=_Cat(),
                            brief_read=lambda db, mfn: {'title': 'T%d' % mfn})
    r1 = _reader(api, '111')
    st, payload = api.place_hold(r1, {'db': 'IBIS', 'mfn': 7})
    check('catalog says taken -> first hold queued (not ready)',
          payload['data']['status'] == 'queued')
    check('queued first hold still position 1', payload['data']['position'] == 1)


# --------------------------------------------------------------------------- #
# 2. Notification inbox — reads circulation-dispatched notices, read/unread.
# --------------------------------------------------------------------------- #
def inbox_checks():
    print('-- inbox: circulation-dispatched notice + unread/read')
    api, _core = _api()
    ticket = '111'
    r1 = _reader(api, ticket)

    # Drive a REAL circulation event addressed to the reader ticket: a return that
    # frees a queued item enqueues hold_ready to the queue-head reader (= ticket).
    cstore = api.circulation.store
    cstore.add_reader('owner', category='В01')
    cstore.add_reader(ticket, category='В01')      # the reader, keyed by ticket
    DAY = circ.SECONDS_PER_DAY
    T0 = 1_700_000_000
    loan = api.circulation.checkout('owner', 'BK-1', T0).computed['loan']
    api.circulation.place_hold(ticket, 'BK-1', T0 + DAY)   # reader queues
    api.circulation.return_item(loan['id'], T0 + 2 * DAY)  # -> hold_ready to ticket

    # The dispatched notice is now in the persistent queue, addressed to ticket.
    st, payload = api.notifications_inbox(r1, False)
    check('inbox returns 200', st == 200)
    items = payload['data']['items']
    check('inbox lists the circulation-dispatched notice', len(items) == 1)
    check('notice is hold_ready', items[0]['event'] == 'hold_ready')
    check('notice rendered (non-empty subject)', bool(items[0]['subject']))
    check('notice starts unread', items[0]['read'] is False)
    check('inbox unread count is 1', payload['data']['unread'] == 1)
    notif_id = items[0]['id']

    # unread filter shows it; reader-scoped (a different ticket sees nothing).
    st, payload = api.notifications_inbox(r1, True)
    check('unread filter shows the unread notice', len(payload['data']['items']) == 1)
    other = _reader(api, '999')
    st, payload = api.notifications_inbox(other, False)
    check('inbox reader-scoped (other reader sees nothing)',
          payload['data']['items'] == [] and payload['data']['unread'] == 0)

    # Mark one read -> unread drops to 0; the card now reads as read.
    st, payload = api.notifications_read(r1, {'id': notif_id})
    check('mark one read returns 200', st == 200)
    check('unread drops to 0 after read', payload['data']['unread'] == 0)
    st, payload = api.notifications_inbox(r1, False)
    check('notice now reads as read', payload['data']['items'][0]['read'] is True)
    check('unread filter empty after read', api.notifications_inbox(r1, True)[1]['data']['items'] == [])

    # mark-all is a no-op now but still returns 0 (and is the path for {all:true}).
    st, payload = api.notifications_read(r1, {'all': True})
    check('mark all read returns unread 0', payload['data']['unread'] == 0)


# --------------------------------------------------------------------------- #
# 3. Shelves — lazy system seed, add/remove/dedup, create.
# --------------------------------------------------------------------------- #
def shelves_checks():
    print('-- shelves: seed / add / remove / dedup / create')
    api, _core = _api()
    r1 = _reader(api, '111')

    # First GET lazily seeds the two system lists.
    st, payload = api.shelves_list(r1)
    check('shelves returns 200', st == 200)
    lists = payload['data']['lists']
    ids = {l['id'] for l in lists}
    check('system lists seeded lazily (want+fav)', SYSTEM_IDS <= ids)
    by_id = {l['id']: l for l in lists}
    check('want is «Хочу прочитать» and system', by_id['want']['name'] == 'Хочу прочитать'
          and by_id['want']['system'] is True)
    check('fav is «Избранное» and system', by_id['fav']['name'] == 'Избранное'
          and by_id['fav']['system'] is True)
    check('system lists start empty', by_id['want']['items'] == [])

    # Add an item to 'want'; dedup on a repeated add.
    st, payload = api.shelf_add_item(r1, {'listId': 'want', 'db': 'IBIS', 'mfn': 10})
    check('add item returns 200', st == 200 and payload['data']['listId'] == 'want')
    api.shelf_add_item(r1, {'listId': 'want', 'db': 'IBIS', 'mfn': 10})  # dup
    api.shelf_add_item(r1, {'listId': 'want', 'db': 'IBIS', 'mfn': 11})
    st, payload = api.shelves_list(r1)
    want = {l['id']: l for l in payload['data']['lists']}['want']
    check('add deduped (10 appears once)', len(want['items']) == 2)
    check('item title resolved via brief seam',
          any(it['mfn'] == 10 and it['title'] == 'Заглавие 10' for it in want['items']))

    # Remove one item.
    st, payload = api.shelf_remove_item(r1, {'listId': 'want', 'db': 'IBIS', 'mfn': 10})
    check('remove returns 200', st == 200)
    st, payload = api.shelves_list(r1)
    want = {l['id']: l for l in payload['data']['lists']}['want']
    check('item removed', [it['mfn'] for it in want['items']] == [11])

    # Adding to a non-existent list -> 404.
    st, payload = api.shelf_add_item(r1, {'listId': 'nope', 'db': 'IBIS', 'mfn': 1})
    check('add to unknown list -> 404', st == 404)

    # Create a custom list, then add to it.
    st, payload = api.shelf_create(r1, {'name': 'Лето 2026'})
    new_id = payload['data']['id']
    check('create custom list returns id+name', payload['data']['name'] == 'Лето 2026'
          and new_id not in SYSTEM_IDS)
    api.shelf_add_item(r1, {'listId': new_id, 'db': 'IBIS', 'mfn': 5})
    st, payload = api.shelves_list(r1)
    custom = {l['id']: l for l in payload['data']['lists']}[new_id]
    check('custom list is not a system list', custom['system'] is False)
    check('custom list holds the added item',
          [it['mfn'] for it in custom['items']] == [5])

    # Reader-scoped: a different reader gets its OWN fresh system lists, no items.
    r2 = _reader(api, '222')
    st, payload = api.shelves_list(r2)
    r2lists = {l['id']: l for l in payload['data']['lists']}
    check('shelves reader-scoped (r2 has fresh empty system lists)',
          r2lists['want']['items'] == [] and new_id not in r2lists)


# --------------------------------------------------------------------------- #
# 4. Auth — guest is refused (401/403) on every reader-portal route.
# --------------------------------------------------------------------------- #
def auth_checks():
    print('-- auth: guest 401/403 on all reader-portal routes')
    api, _core = _api()
    guest = _guest(api)

    routes = [
        ('POST', '/api/hold', {'db': 'IBIS', 'mfn': 1}),
        ('GET', '/api/holds', None),
        ('POST', '/api/hold/cancel', {'holdId': 1}),
        ('GET', '/api/notifications', None),
        ('POST', '/api/notifications/read', {'all': True}),
        ('GET', '/api/shelves', None),
        ('POST', '/api/shelves', {'name': 'x'}),
        ('POST', '/api/shelves/item', {'listId': 'want', 'db': 'IBIS', 'mfn': 1}),
        ('POST', '/api/shelves/item/remove', {'listId': 'want', 'db': 'IBIS', 'mfn': 1}),
    ]
    # Direct handler calls raise Denied(403) for a guest (reader session required).
    handlers = [
        lambda: api.place_hold(guest, {'db': 'IBIS', 'mfn': 1}),
        lambda: api.list_holds(guest),
        lambda: api.cancel_hold(guest, {'holdId': 1}),
        lambda: api.notifications_inbox(guest, False),
        lambda: api.notifications_read(guest, {'all': True}),
        lambda: api.shelves_list(guest),
        lambda: api.shelf_create(guest, {'name': 'x'}),
        lambda: api.shelf_add_item(guest, {'listId': 'want', 'db': 'IBIS', 'mfn': 1}),
        lambda: api.shelf_remove_item(guest, {'listId': 'want', 'db': 'IBIS', 'mfn': 1}),
    ]
    for (m, p, _b), fn in zip(routes, handlers):
        denied = False
        try:
            fn()
        except _core.Denied as d:
            denied = d.status in (401, 403)
        check('guest denied on %s %s (403)' % (m, p), denied)

    # And through the real dispatcher: a guest token -> 401/403 status, never 200.
    headers = {}   # no bearer at all -> no session
    for m, p, b in routes:
        st, _payload = api.route(m, p, {}, b, headers)
        check('route %s %s with no session -> 401/403' % (m, p), st in (401, 403))

    # A reader, by contrast, is admitted (sanity: the guard isn't blanket-denying).
    r1 = _reader(api, '111')
    st, _payload = api.shelves_list(r1)
    check('reader admitted to /api/shelves (200)', st == 200)


# --------------------------------------------------------------------------- #
# 5. Postgres parity — the reader_hold / reader_shelf store CRUD on real PG.
# Exercises the %s-style SQL + ON CONFLICT against PostgreSQL when reachable;
# skips cleanly (not a failure) on the sqlite dev box / when PG/psycopg is absent.
# This is what proves the schema_postgres.sql DDL + PgAccessStore methods work on
# the CI postgres leg, alongside the sqlite coverage above.
# --------------------------------------------------------------------------- #
def pg_parity_checks():
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return
    try:
        from access.pgstore import PgAccessStore, default_pg_dsn
        st = PgAccessStore(os.environ.get('ACCESS_PG_DSN', default_pg_dsn()))
        st._conn().execute('TRUNCATE reader_hold, reader_shelf, reader_shelf_item '
                           'RESTART IDENTITY')
    except Exception as e:
        print('-- portal222 pg parity SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return
    print('-- portal222: postgres parity (reader_hold / reader_shelf CRUD)')

    # Holds CRUD on PG via the HoldService (no catalog → first-in-line ready).
    holds = HoldService(st, catalog=None, brief_read=lambda db, mfn: {'title': 'PG%d' % mfn})
    r1 = holds.place('pg-1', 'IBIS', 5)
    check('[pg] first hold ready position 1', r1['status'] == 'ready' and r1['position'] == 1)
    check('[pg] re-hold idempotent', holds.place('pg-1', 'IBIS', 5)['holdId'] == r1['holdId'])
    r2 = holds.place('pg-2', 'IBIS', 5)
    check('[pg] second reader queued position 2',
          r2['status'] == 'queued' and r2['position'] == 2)
    check('[pg] list_for is reader-scoped', len(holds.list_for('pg-1')) == 1)
    check('[pg] cancel works', holds.cancel('pg-1', r1['holdId'])['status'] == 'cancelled')
    check('[pg] cancelled hold gone from list', holds.list_for('pg-1') == [])

    # Shelves CRUD on PG: lazy system seed + add/dedup/remove/create.
    shelves = ShelfService(st, brief_read=lambda db, mfn: {'title': 'PG%d' % mfn})
    lists = shelves.lists('pg-1')
    check('[pg] system lists seeded', SYSTEM_IDS <= {l['id'] for l in lists})
    shelves.add_item('pg-1', 'want', 'IBIS', 10)
    shelves.add_item('pg-1', 'want', 'IBIS', 10)   # dup
    want = {l['id']: l for l in shelves.lists('pg-1')}['want']
    check('[pg] add deduped', len(want['items']) == 1)
    cust = shelves.create('pg-1', 'PG-список')
    check('[pg] custom list created', cust['id'] not in SYSTEM_IDS)
    check('[pg] add to unknown list -> None', shelves.add_item('pg-1', 'nope', 'IBIS', 1) is None)
    shelves.remove_item('pg-1', 'want', 'IBIS', 10)
    want = {l['id']: l for l in shelves.lists('pg-1')}['want']
    check('[pg] item removed', want['items'] == [])


def main():
    holds_checks()
    holds_availability_checks()
    inbox_checks()
    shelves_checks()
    auth_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
