#!/usr/bin/env python3
"""Circulation→Notifications integration-edge tests (epic #188).

Wires the seam where :class:`access.circulation.CirculationEngine._emit` routes a
circulation event into the A6 notification engine
(:class:`access.notifications.NotificationQueue`): render + enqueue the notice on
the template's default channels, reader vs staff routing, and the back-compat /
failure-isolation guarantees the rule layer depends on.

Covered:
  * a checkout→return that charges a fine enqueues a correctly-rendered,
    correctly-channelled ``fine_charged`` notice through the engine;
  * a return that frees a queued item enqueues ``hold_ready`` to the *reader* at
    the queue head (reader routing);
  * a renewal enqueues ``renewal_confirmed``; a fine payment enqueues
    ``fine_paid``; an overdue-driven accrual+return path renders the amount;
  * a lost-candidate scan enqueues ``staff_alert`` to the *staff* recipient, NOT
    the reader (staff routing), on the staff (email-only) channel;
  * render context: the rendered body/subject carry the mapped slots (title from
    the item shifr, amount+currency on a money notice) — no literal ``{title}``;
  * back-compat: with NO notifications handle the engine dispatches nothing and
    the loan/return/hold still record (mirrors the catalog seam);
  * failure isolation: an unknown event and a dispatch failure (a throwing queue)
    never raise out of the circulation operation — the op still succeeds;
  * no double-send: a repeated logical event enqueues exactly one notice (dedup);
  * every event ``_emit`` raises has a template in the A6 catalog.

Standalone-runnable in the house style of test_circulation.py / test_notifications.py:
  py -3.12 tests/test_circ_notify.py  ->  ok ... + "N passed, M failed" + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import circulation as circ
from access import notifications as nt
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy, ALLOW, SECONDS_PER_DAY,
)

PASS = [0]
FAIL = [0]

DAY = SECONDS_PER_DAY
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _wired(policy=None, category='В01', reader='R1', tenant='public'):
    """A circulation engine with a fresh A6 queue + recording channels wired.

    Returns ``(store, eng, queue, channels)`` where ``channels`` is the
    ``{name: MemoryChannel}`` map handed to ``queue.process_once``.
    """
    store = CirculationStore(':memory:')
    queue = nt.NotificationQueue(':memory:')
    eng = CirculationEngine(store=store, policy=policy or default_policy(),
                            notifications=queue, tenant=tenant)
    store.add_reader(reader, category=category)
    channels = {'email': nt.MemoryChannel('email'), 'sms': nt.MemoryChannel('sms')}
    return store, eng, queue, channels


def _drain(queue, channels):
    """Process the queue to completion; return the list of delivered records."""
    queue.process_once(channels)
    delivered = []
    for ch in channels.values():
        delivered.extend(ch.sent)
    return delivered


# --------------------------------------------------------------------------- #
# 1. Coverage — every emitted event has an A6 template.
# --------------------------------------------------------------------------- #
def coverage_checks():
    print('-- coverage: every _emit event has a template')
    cat = nt.EventCatalog()
    # Events CirculationEngine._emit raises (kept in lock-step with circulation.py).
    emitted = ('renewal_confirmed', 'fine_charged', 'hold_ready', 'fine_paid',
               'staff_alert', 'lost_confirmed', 'hold_cancelled')
    for ev in emitted:
        check('catalog covers emitted event %s' % ev, cat.has(ev))


# --------------------------------------------------------------------------- #
# 2. Checkout → return charging a fine enqueues fine_charged (reader routing).
# --------------------------------------------------------------------------- #
def fine_charged_dispatch_checks():
    print('-- fine_charged: render + enqueue on return')
    store, eng, queue, channels = _wired(category='В01')
    due = T0 - 10 * DAY                                # 9 billable days * 5 = 45
    loan = store.add_loan('R1', 'BK-901', due, due - 20 * DAY)

    d = eng.return_item(loan['id'], T0)
    check('return still succeeds', d.decision == ALLOW)
    check('fine charged in store', d.computed.get('fine_charged') == 45.0)

    rows = queue.all()
    fc = [r for r in rows if r['event'] == 'fine_charged']
    check('exactly one fine_charged enqueued', len(fc) == 1)
    check('fine_charged addressed to the reader', fc and fc[0]['recipient'] == 'R1')
    check('fine_charged pending before processing',
          fc and fc[0]['status'] == 'pending')

    delivered = _drain(queue, channels)
    fc_sent = [m for m in delivered if 'штраф' in m['subject'].lower()
               or 'Штраф' in m['subject']]
    check('fine_charged delivered through the engine', len(fc_sent) == 1)
    # render context: amount + currency interpolated (no literal placeholder).
    body = fc_sent[0]['body'] if fc_sent else ''
    check('rendered amount present', '45' in body)
    check('rendered currency present (default RUB)', 'RUB' in body)
    check('no unrendered {amount} placeholder', '{amount}' not in body)
    # fine_charged default channel chain is [email, sms] → delivered via email.
    check('fine_charged delivered via email (first default channel)',
          len(channels['email'].sent) >= 1)


# --------------------------------------------------------------------------- #
# 3. Return frees a queued item → hold_ready to the queue-head reader.
# --------------------------------------------------------------------------- #
def hold_ready_dispatch_checks():
    print('-- hold_ready: enqueue to the queue-head reader')
    store, eng, queue, channels = _wired(category='В01')
    loan = eng.checkout('R1', 'BK-7', T0).computed['loan']
    store.add_reader('R2', category='В01')
    store.add_reader('R3', category='В01')
    eng.place_hold('R2', 'BK-7', T0 + 1 * DAY)
    eng.place_hold('R3', 'BK-7', T0 + 2 * DAY)

    d = eng.return_item(loan['id'], T0 + 5 * DAY)
    check('return allowed', d.decision == ALLOW)

    hr = [r for r in queue.all() if r['event'] == 'hold_ready']
    check('exactly one hold_ready enqueued', len(hr) == 1)
    check('hold_ready addressed to head reader R2 (not R3)',
          hr and hr[0]['recipient'] == 'R2')

    delivered = _drain(queue, channels)
    hr_sent = [m for m in delivered if m['recipient'] == 'R2'
               and 'Бронь готова' in m['subject']]
    check('hold_ready delivered to R2', len(hr_sent) == 1)
    check('rendered title carries the item shifr',
          hr_sent and 'BK-7' in hr_sent[0]['subject'])


# --------------------------------------------------------------------------- #
# 4. Renewal + payment dispatch.
# --------------------------------------------------------------------------- #
def renewal_and_payment_dispatch_checks():
    print('-- renewal_confirmed + fine_paid dispatch')
    store, eng, queue, channels = _wired(category='В01')
    loan = eng.checkout('R1', 'BK-RN', T0).computed['loan']
    eng.renew(loan['id'], T0 + 5 * DAY)
    rc = [r for r in queue.all() if r['event'] == 'renewal_confirmed']
    check('renewal_confirmed enqueued to reader', len(rc) == 1 and rc[0]['recipient'] == 'R1')

    # accrue a fine then pay it → fine_paid dispatched.
    store2, eng2, queue2, channels2 = _wired(category='В01', reader='RP')
    due = T0 - 10 * DAY
    ln = store2.add_loan('RP', 'BK-PAY', due, due - 20 * DAY)
    eng2.accrue_fines(T0)
    eng2.pay_fine(ln['id'])
    fp = [r for r in queue2.all() if r['event'] == 'fine_paid']
    check('fine_paid enqueued to reader', len(fp) == 1 and fp[0]['recipient'] == 'RP')
    delivered = _drain(queue2, channels2)
    check('fine_paid delivered', any('Оплата принята' in m['subject'] for m in delivered))


# --------------------------------------------------------------------------- #
# 5. Staff routing — lost-candidate scan goes to STAFF, not the reader.
# --------------------------------------------------------------------------- #
def staff_routing_checks():
    print('-- staff routing: staff_alert -> staff recipient, email-only')
    store, eng, queue, channels = _wired(category='В01')   # default staff_recipient='staff'
    due = T0 - 90 * DAY                                      # over lost_after_days=60
    loan = store.add_loan('R1', 'BK-LOST', due, due - 20 * DAY)

    d = eng.scan_lost_candidates(T0)
    check('scan still succeeds', d.decision == ALLOW)
    check('candidate flagged', loan['id'] in d.computed['candidates'])

    sa = [r for r in queue.all() if r['event'] == 'staff_alert']
    check('exactly one staff_alert enqueued', len(sa) == 1)
    check('staff_alert addressed to STAFF, not the reader',
          sa and sa[0]['recipient'] == 'staff' and sa[0]['recipient'] != 'R1')
    # staff_alert default channel chain is [email] only.
    import json as _json
    chain = _json.loads(sa[0]['channels_json']) if sa else []
    check('staff_alert routed to the email-only staff channel', chain == ['email'])

    delivered = _drain(queue, channels)
    check('staff_alert delivered via email only', len(channels['email'].sent) == 1
          and len(channels['sms'].sent) == 0)
    check('staff_alert reads as a staff notice (Служебное)',
          any('Служебное' in m['subject'] for m in delivered))
    # the reader id is still carried into the staff notice context.
    check('staff notice references the reader formulary',
          any('R1' in m['body'] for m in delivered))

    # a custom staff_recipient is honoured.
    store2 = CirculationStore(':memory:')
    queue2 = nt.NotificationQueue(':memory:')
    eng2 = CirculationEngine(store=store2, policy=default_policy(),
                             notifications=queue2, staff_recipient='circ-desk@lib')
    store2.add_reader('RR', category='В01')
    store2.add_loan('RR', 'BK-L2', T0 - 90 * DAY, T0 - 110 * DAY)
    eng2.scan_lost_candidates(T0)
    sa2 = [r for r in queue2.all() if r['event'] == 'staff_alert']
    check('custom staff_recipient honoured',
          sa2 and sa2[0]['recipient'] == 'circ-desk@lib')


# --------------------------------------------------------------------------- #
# 6. Back-compat — no notifications handle ⇒ no dispatch, op still records.
# --------------------------------------------------------------------------- #
def backcompat_checks():
    print('-- back-compat: standalone engine (no notifications handle)')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())  # no handle
    store.add_reader('R1', category='В01')
    loan = eng.checkout('R1', 'BK-BC', T0).computed['loan']

    # an event-producing op still returns its intents and records state.
    d = eng.renew(loan['id'], T0 + 5 * DAY)
    check('standalone renew still succeeds', d.decision == ALLOW)
    check('standalone renew still records (renewals bumped)',
          store.get_loan(loan['id'])['renewals'] == 1)
    check('standalone renew still returns the event intent',
          any(e['event'] == 'renewal_confirmed' for e in d.events))

    # return that charges a fine still works with no dispatcher.
    store2 = CirculationStore(':memory:')
    eng2 = CirculationEngine(store=store2, policy=default_policy())
    store2.add_reader('R2', category='В01')
    due = T0 - 10 * DAY
    ln = store2.add_loan('R2', 'BK-BC2', due, due - 20 * DAY)
    dr = eng2.return_item(ln['id'], T0)
    check('standalone return still records the return',
          store2.get_loan(ln['id'])['returned'] == 1)
    check('standalone return still charges the fine',
          dr.computed.get('fine_charged') == 45.0)

    # notifier= back-compat alias still wires dispatch (same role as notifications=).
    store3 = CirculationStore(':memory:')
    queue3 = nt.NotificationQueue(':memory:')
    eng3 = CirculationEngine(store=store3, policy=default_policy(), notifier=queue3)
    store3.add_reader('R3', category='В01')
    l3 = eng3.checkout('R3', 'BK-AL', T0).computed['loan']
    eng3.renew(l3['id'], T0 + 5 * DAY)
    check('notifier= alias still dispatches',
          any(r['event'] == 'renewal_confirmed' for r in queue3.all()))


# --------------------------------------------------------------------------- #
# 7. Failure isolation — unknown event + throwing dispatcher don't raise.
# --------------------------------------------------------------------------- #
class _ThrowingQueue:
    """A notifications handle whose enqueue always blows up (and has no catalog)."""
    catalog = None

    def enqueue(self, *a, **k):
        raise RuntimeError('queue is down')


def failure_isolation_checks():
    print('-- failure isolation: bad dispatch never breaks circulation')
    # (a) a dispatch failure (throwing queue) must not break the operation.
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(),
                            notifications=_ThrowingQueue())
    store.add_reader('R1', category='В01')
    loan = eng.checkout('R1', 'BK-F', T0).computed['loan']
    raised = False
    try:
        d = eng.renew(loan['id'], T0 + 5 * DAY)
    except Exception:
        raised = True
    check('throwing dispatcher does not raise out of renew', not raised)
    check('loan still renewed despite dispatch failure',
          store.get_loan(loan['id'])['renewals'] == 1)

    # a return that frees a hold + charges a fine — multiple emits, all isolated.
    store.add_reader('R2', category='В01')
    due = T0 - 10 * DAY
    ln = store.add_loan('R1', 'BK-F2', due, due - 20 * DAY)
    eng.place_hold('R2', 'BK-F2', T0)
    raised2 = False
    try:
        dr = eng.return_item(ln['id'], T0)
    except Exception:
        raised2 = True
    check('throwing dispatcher does not raise out of return', not raised2)
    check('return still recorded despite dispatch failure',
          store.get_loan(ln['id'])['returned'] == 1)

    # (b) an event with no matching template is skipped, not raised.
    store2, eng2, queue2, _ = _wired(category='В01', reader='RX')
    raised3 = False
    try:
        eng2._emit('not_a_real_event', 'RX', {'item': 'BK', 'ref': 'x1'})
    except Exception:
        raised3 = True
    check('unknown event does not raise out of _emit', not raised3)
    check('unknown event enqueues nothing',
          not [r for r in queue2.all() if r['event'] == 'not_a_real_event'])


# --------------------------------------------------------------------------- #
# 8. No double-send — a repeated logical event enqueues once (dedup).
# --------------------------------------------------------------------------- #
def no_double_send_checks():
    print('-- no double-send: dedup keeps one notice per logical event')
    store, eng, queue, channels = _wired(category='В01')
    due = T0 - 10 * DAY
    ln = store.add_loan('R1', 'BK-DS', due, due - 20 * DAY)
    # Same loan id ⇒ same ref ⇒ same dedup key: emit fine_charged twice by hand.
    eng._emit('fine_charged', 'R1', {'ref': ln['id'], 'amount': 45.0,
                                     'currency': 'RUB', 'item': 'BK-DS'})
    eng._emit('fine_charged', 'R1', {'ref': ln['id'], 'amount': 45.0,
                                     'currency': 'RUB', 'item': 'BK-DS'})
    fc = [r for r in queue.all() if r['event'] == 'fine_charged']
    check('repeated logical event enqueued exactly once', len(fc) == 1)
    delivered = _drain(queue, channels)
    check('repeated logical event delivered exactly once',
          len([m for m in delivered if '45' in m['body']]) == 1)


def main():
    coverage_checks()
    fine_charged_dispatch_checks()
    hold_ready_dispatch_checks()
    renewal_and_payment_dispatch_checks()
    staff_routing_checks()
    backcompat_checks()
    failure_isolation_checks()
    no_double_send_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
