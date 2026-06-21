#!/usr/bin/env python3
"""Notification engine tests (gap A6, epic #188).

Covers the self-contained notification engine (access/notifications.py):

  1. EventCatalog: SPEC event set present with template + default channel chain;
     register/override; unknown event rejected at enqueue.
  2. Rendering: stdlib {placeholder} fallback (PFT engine A1 absent today) fills
     known slots and leaves unknown ones verbatim (no crash, no dropped notice).
  3. Queue happy path: enqueue -> process delivers via the preferred channel and
     marks the row 'sent' with the delivering channel recorded.
  4. Dedup: a second enqueue of the same logical event is a no-op (single send);
     explicit dedup_key honoured.
  5. Opt-out: an opted-out reader yields a 'suppressed' row, never sent; '*'
     opts out of everything.
  6. Preferences: per-event channel order overrides the catalog default.
  7. Fallback chain: first channel fails -> next channel delivers (first-success).
  8. Retry: a transiently-failing chain bumps attempts and re-queues; once the
     transient clears the next process_once delivers; exhausted chain -> 'failed'.

Standalone-runnable in the house style of tests/test_seeding.py:
  py -3.12 tests/test_notifications.py  ->  'ok ...' lines + 'N passed, M failed'
  and exit code 1 on any failure (so CI fails loud).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import notifications as nt

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _q(catalog=None):
    """A fresh in-memory queue (each test isolated)."""
    return nt.NotificationQueue(':memory:', catalog=catalog)


# --------------------------------------------------------------------------- #
# 1. Event catalog.
# --------------------------------------------------------------------------- #
# Every event CirculationEngine._emit raises (grep circulation.py for `_emit(`).
# A name here with no catalog entry is an intent that falls through silently —
# rendered/sent never. Keep this list in lock-step with circulation.py.
CIRCULATION_EVENTS = (
    'hold_ready', 'due_soon', 'overdue', 'fine_charged',
    'renewal_confirmed', 'fine_paid', 'lost_confirmed', 'staff_alert',
)


def catalog_checks():
    print('-- event catalog')
    cat = nt.EventCatalog()
    for ev in ('hold_ready', 'due_soon', 'overdue', 'fine_charged'):
        check('catalog has %s' % ev, cat.has(ev))
    check('hold_ready template has subject+body',
          set(cat.template('hold_ready')) >= {'subject', 'body'})
    check('hold_ready default channels are a non-empty list',
          isinstance(cat.default_channels('hold_ready'), list)
          and cat.default_channels('hold_ready'))
    check('overdue prioritises sms first',
          cat.default_channels('overdue')[0] == 'sms')

    # No circulation event may fall through for lack of a template: each must
    # have a non-empty subject+body and at least one default channel.
    for ev in CIRCULATION_EVENTS:
        check('catalog covers circulation event %s' % ev, cat.has(ev))
        if not cat.has(ev):
            continue
        tmpl = cat.template(ev)
        check('%s has non-empty subject+body' % ev,
              bool(tmpl.get('subject')) and bool(tmpl.get('body')))
        check('%s has a non-empty channel chain' % ev,
              isinstance(cat.default_channels(ev), list)
              and bool(cat.default_channels(ev)))

    # staff_alert is staff-facing: an e-mail default, and addressed to the
    # librarian (not a reader-style greeting / SMS).
    check('staff_alert defaults to email', cat.default_channels('staff_alert') == ['email'])
    check('staff_alert subject reads as a staff notice',
          'Служебное' in cat.template('staff_alert')['subject'])

    # register/override does not leak into the class-level DEFAULTS
    cat.register('renewal_ok', {'subject': 'OK', 'body': 'Renewed {title}'},
                 ['email'])
    check('register adds a custom event', cat.has('renewal_ok'))
    check('register does not mutate DEFAULTS',
          'renewal_ok' not in nt.EventCatalog.DEFAULTS)

    # unknown event rejected at enqueue
    q = _q()
    raised = False
    try:
        q.enqueue('not_a_real_event', 'r1', {})
    except KeyError:
        raised = True
    check('enqueue rejects unknown event', raised)


# --------------------------------------------------------------------------- #
# 2. Rendering — stdlib fallback (PFT/A1 not built yet).
# --------------------------------------------------------------------------- #
def render_checks():
    print('-- template rendering (stdlib fallback)')
    out = nt.render('«{title}» до {due_date}', {'title': 'Война и мир',
                                                'due_date': '2026-07-01'})
    check('render fills known placeholders',
          out == '«Война и мир» до 2026-07-01')
    check('render leaves unknown placeholder verbatim (no crash)',
          nt.render('hi {missing}', {'title': 'x'}) == 'hi {missing}')
    check('render of None -> empty string', nt.render(None, {}) == '')
    check('render None value -> empty', nt.render('x={v}', {'v': None}) == 'x=')


# --------------------------------------------------------------------------- #
# 3. Happy path: enqueue -> process delivers via preferred channel.
# --------------------------------------------------------------------------- #
def deliver_checks():
    print('-- enqueue -> process delivers')
    q = _q()
    email = nt.MemoryChannel('email')
    sms = nt.MemoryChannel('sms')

    res = q.enqueue('hold_ready', 'reader-42',
                    {'reader_name': 'Иван', 'title': 'Идиот',
                     'hold_until': '2026-06-30', 'pickup': 'Абонемент',
                     'ref': 'hold-100'})
    check('enqueue returns pending row', res['status'] == 'pending'
          and res['deduped'] is False)
    check('one pending in queue', q.pending_count() == 1)

    summary = q.process_once({'email': email, 'sms': sms})
    check('process reports one sent', summary['sent'] == 1)
    check('delivered via email (first preferred)', len(email.sent) == 1)
    check('sms not used (email succeeded)', len(sms.sent) == 0)

    row = q.get(res['id'])
    check('row marked sent', row['status'] == 'sent')
    check('delivering channel recorded', row['channel'] == 'email')
    check('attempts == 1', row['attempts'] == 1)
    check('rendered body reached channel',
          'Идиот' in email.sent[0]['body'])
    check('rendered subject reached channel',
          'Идиот' in email.sent[0]['subject'])

    # idempotent processing: nothing pending -> second pass is a no-op
    again = q.process_once({'email': email, 'sms': sms})
    check('second process_once sends nothing', again['sent'] == 0)
    check('no double-send on reprocess', len(email.sent) == 1)


# --------------------------------------------------------------------------- #
# 4. Dedup prevents double-send.
# --------------------------------------------------------------------------- #
def dedup_checks():
    print('-- dedup (idempotent enqueue)')
    q = _q()
    email = nt.MemoryChannel('email')
    payload = {'title': 'Обломов', 'ref': 'hold-7'}

    a = q.enqueue('hold_ready', 'reader-1', payload)
    b = q.enqueue('hold_ready', 'reader-1', payload)   # same logical event
    check('second enqueue is deduped', b['deduped'] is True)
    check('same row id returned', a['id'] == b['id'])
    check('only one row queued', len(q.all()) == 1)

    q.process_once({'email': email})
    check('dedup -> single send', len(email.sent) == 1)

    # re-enqueue after delivery still deduped (no resurrection of a sent notice)
    c = q.enqueue('hold_ready', 'reader-1', payload)
    check('post-send enqueue still deduped', c['deduped'] is True)
    q.process_once({'email': email})
    check('no extra send after re-enqueue', len(email.sent) == 1)

    # explicit dedup_key wins over the derived one
    q2 = _q()
    q2.enqueue('fine_charged', 'reader-2', {'dedup_key': 'fine-xyz', 'amount': 50})
    d = q2.enqueue('fine_charged', 'reader-2',
                   {'dedup_key': 'fine-xyz', 'amount': 999})  # different payload
    check('explicit dedup_key dedupes regardless of payload', d['deduped'] is True)


# --------------------------------------------------------------------------- #
# 5. Opt-out suppresses.
# --------------------------------------------------------------------------- #
def optout_checks():
    print('-- opt-out suppression')
    q = _q()
    email = nt.MemoryChannel('email')

    prefs = nt.Preferences(opted_out={'due_soon'})
    res = q.enqueue('due_soon', 'reader-9', {'title': 'X', 'ref': 'loan-1'},
                    prefs=prefs)
    check('opted-out enqueue -> suppressed', res['status'] == 'suppressed')
    check('no pending row created', q.pending_count() == 0)

    q.process_once({'email': email})
    check('suppressed notice never sent', len(email.sent) == 0)
    check('row persisted as suppressed (audit trail)',
          len(q.by_status('suppressed')) == 1)

    # a NON-opted event for the same reader still goes through
    res2 = q.enqueue('overdue', 'reader-9', {'title': 'X', 'days_overdue': 3,
                                             'ref': 'loan-1'}, prefs=prefs)
    check('non-opted event still queued', res2['status'] == 'pending')

    # global '*' opt-out blocks everything
    q2 = _q()
    allp = nt.Preferences(opted_out={'*'})
    r = q2.enqueue('hold_ready', 'r', {'title': 'T', 'ref': 'h1'}, prefs=allp)
    check('global opt-out suppresses any event', r['status'] == 'suppressed')


# --------------------------------------------------------------------------- #
# 6. Preferences override the catalog channel order.
# --------------------------------------------------------------------------- #
def preference_checks():
    print('-- preferences (channel order override)')
    q = _q()
    email = nt.MemoryChannel('email')
    sms = nt.MemoryChannel('sms')

    # hold_ready defaults to [email, sms]; reader prefers sms-first.
    prefs = nt.Preferences(channels={'hold_ready': ['sms', 'email']})
    q.enqueue('hold_ready', 'reader-5', {'title': 'Y', 'ref': 'h9'}, prefs=prefs)
    q.process_once({'email': email, 'sms': sms})
    check('preferred sms used first', len(sms.sent) == 1)
    check('email skipped when sms preferred', len(email.sent) == 0)


# --------------------------------------------------------------------------- #
# 7. Fallback chain — first channel fails, next delivers.
# --------------------------------------------------------------------------- #
def fallback_checks():
    print('-- fallback chain (first-success)')
    q = _q()
    email = nt.MemoryChannel('email', fail=True)   # always fails
    sms = nt.MemoryChannel('sms')                  # succeeds

    res = q.enqueue('hold_ready', 'reader-3', {'title': 'Z', 'ref': 'h3'})
    summary = q.process_once({'email': email, 'sms': sms})
    check('fallback delivered exactly one', summary['sent'] == 1)
    check('email attempted', email.attempts == 1)
    check('email recorded no successful send', len(email.sent) == 0)
    check('sms delivered as fallback', len(sms.sent) == 1)

    row = q.get(res['id'])
    check('row sent via fallback channel', row['status'] == 'sent'
          and row['channel'] == 'sms')

    # EmailChannel stub with available=False also triggers fallback
    q2 = _q()
    em = nt.EmailChannel(available=False)
    sm = nt.SmsChannel(available=True)
    q2.enqueue('hold_ready', 'reader-4', {'title': 'Q', 'ref': 'h4'})
    q2.process_once({'email': em, 'sms': sm})
    check('unavailable email stub falls back to sms', len(sm.outbox) == 1)
    check('email stub outbox empty', len(em.outbox) == 0)


# --------------------------------------------------------------------------- #
# 8. Retry increments attempts; exhausted chain -> failed.
# --------------------------------------------------------------------------- #
def retry_checks():
    print('-- retry / attempts counter')
    # Channel fails once then succeeds; no fallback wired, so the row must
    # re-queue (attempts++) and deliver on the next process_once.
    q = _q()
    flaky = nt.MemoryChannel('email', fail_times=1)
    res = q.enqueue('hold_ready', 'reader-6', {'title': 'R', 'ref': 'h6'})

    s1 = q.process_once({'email': flaky})
    check('first pass retried (no send)', s1['sent'] == 0 and s1['retried'] == 1)
    row = q.get(res['id'])
    check('attempts incremented to 1', row['attempts'] == 1)
    check('row back to pending', row['status'] == 'pending')
    check('last_error recorded', bool(row['last_error']))

    # backoff sets next_attempt_at into the future; process at that time.
    s2 = q.process_once({'email': flaky}, now=row['next_attempt_at'])
    check('second pass delivers after transient clears', s2['sent'] == 1)
    row2 = q.get(res['id'])
    check('attempts now 2', row2['attempts'] == 2)
    check('row finally sent', row2['status'] == 'sent')

    # Always-failing chain with no fallback walks attempts to MAX -> failed.
    q2 = _q()
    dead = nt.MemoryChannel('email', fail=True)
    r2 = q2.enqueue('hold_ready', 'reader-7', {'title': 'D', 'ref': 'h7'})
    t = 0.0
    for _ in range(nt.MAX_ATTEMPTS):
        row = q2.get(r2['id'])
        if row['status'] != 'pending':
            break
        q2.process_once({'email': dead}, now=max(t, row['next_attempt_at']))
        t = row['next_attempt_at'] + 1
    final = q2.get(r2['id'])
    check('exhausted chain marked failed', final['status'] == 'failed')
    check('attempts reached the cap', final['attempts'] == nt.MAX_ATTEMPTS)

    # backoff helper is monotonic-ish and capped
    check('backoff(0) == 0', nt.backoff_seconds(0) == 0)
    check('backoff caps at last bucket',
          nt.backoff_seconds(999) == nt.backoff_seconds(nt.MAX_ATTEMPTS))


def main():
    catalog_checks()
    render_checks()
    deliver_checks()
    dedup_checks()
    optout_checks()
    preference_checks()
    fallback_checks()
    retry_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
