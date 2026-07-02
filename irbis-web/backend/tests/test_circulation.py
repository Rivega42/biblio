#!/usr/bin/env python3
"""Circulation engine tests (gap E2, epic #188).

Scenario-based tests of the circulation rules + own sqlite store, per
SPEC_business_circulation.md. Everything runs against an in-memory store with an
*injected* ``today`` (epoch seconds) so the rules — fines, lost grace, queue —
are deterministic and need no clock.

Standalone-runnable in the house style of ``test_seeding.py``::

    py -3.12 tests/test_circulation.py   ->  ok ...  +  "N passed, M failed"  + exit code

Covered (mirrors the §11 test matrix + the task scenarios):
  * checkout respects ``max_books`` (limit_exceeded);
  * a hard debtor is blocked from checkout (reader_has_debt) but an authorised
    ``staff_override`` lends over the debt;
  * renew is blocked when a hold exists (holds_block_renewal=block), allowed with
    an authorised override; ``threshold`` / ``allow`` modes;
  * renew cap (max_prolong) enforced — never override-able;
  * fine accrues correctly after grace (numeric example) + cap + fine-free;
  * hold queue gives correct FIFO position;
  * return triggers hold-ready;
  * lost candidate → confirm → replacement charge;
  * tenant policy isolation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import circulation as circ
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy,
    ALLOW, DENY, REQUIRE_OVERRIDE, SECONDS_PER_DAY,
)

PASS = [0]
FAIL = [0]

# A fixed reference "today" so every scenario is deterministic.
DAY = SECONDS_PER_DAY
T0 = 1_700_000_000  # arbitrary epoch anchor


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def fresh(policy=None, category='В01', reader='R1'):
    """A fresh engine over an in-memory store with one seeded reader."""
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=policy or default_policy())
    store.add_reader(reader, category=category)
    return store, eng


# --------------------------------------------------------------------------- #
# 1. Store + policy basics.
# --------------------------------------------------------------------------- #
def store_and_policy_checks():
    print('-- store schema + policy defaults')
    store = CirculationStore(':memory:')
    store.add_reader('R1', category='В01')
    check('reader round-trips', store.get_reader('R1')['category'] == 'В01')

    loan = store.add_loan('R1', 'BK-1', T0 + 20 * DAY, T0)
    check('loan created on-hand', loan['returned'] == 0 and loan['renewals'] == 0)
    check('count_on_hand counts open loans', store.count_on_hand('R1') == 1)

    p = default_policy('tenantA')
    check('policy tenant id', p['tenant_id'] == 'tenantA')
    check('policy max_prolong default 5', p['limits']['В01']['max_prolong'] == 5)
    check('policy holds_block_renewal=block', p['renewal']['holds_block_renewal'] == 'block')
    check('policy lost_after_days=60', p['lost']['lost_after_days'] == 60)
    check('policy hold_shelf_days=3', p['hold']['hold_shelf_days'] == 3)
    check('GUEST max_books low', p['limits']['GUEST']['max_books'] <= 1)

    # fresh policy per call — mutating one must not leak (isolation, AC7)
    p['limits']['В01']['max_books'] = 999
    p2 = default_policy()
    check('policy fresh per call (no leak)', p2['limits']['В01']['max_books'] == 5)


# --------------------------------------------------------------------------- #
# 2. Checkout — limits (§5) and the debtor gate (§2).
# --------------------------------------------------------------------------- #
def checkout_limit_checks():
    print('-- checkout: MaxBooks limit')
    # В01 max_books=5; lend 5, the 6th is denied.
    store, eng = fresh(category='В01')
    for i in range(5):
        d = eng.checkout('R1', 'BK-%d' % i, T0)
        check('checkout %d allowed' % i, d.decision == ALLOW) if i == 0 else None
    check('5 books on hand', store.count_on_hand('R1') == 5)
    d6 = eng.checkout('R1', 'BK-6', T0)
    check('6th checkout requires override (limit)', d6.decision == REQUIRE_OVERRIDE
          and 'limit_exceeded' in d6.reasons)

    # authorised staff override lends the 6th
    d6o = eng.checkout('R1', 'BK-6', T0, staff_override=True, override_grant=True)
    check('staff override lends over limit', d6o.decision == ALLOW)
    check('override unauthorised is denied',
          eng.checkout('R1', 'BK-7', T0, staff_override=True,
                       override_grant=False).decision == DENY)


def checkout_debtor_checks():
    print('-- checkout: debtor gate vs staff override')
    store, eng = fresh(category='В01')
    # Make R1 a HARD debtor: an overdue loan well past the overdue grace.
    overdue_due = T0 - 30 * DAY                # 30 days overdue
    store.add_loan('R1', 'OLD', overdue_due, overdue_due - 20 * DAY)
    today = T0
    check('debt_level hard', circ.debt_level(store, eng.policy, 'R1', today) == 'hard')

    d = eng.checkout('R1', 'NEW', today)
    check('debtor blocked from checkout (require_override)',
          d.decision == REQUIRE_OVERRIDE and 'reader_has_debt' in d.reasons)

    # staff override with grant lends over the debt
    do = eng.checkout('R1', 'NEW', today, staff_override=True, override_grant=True)
    check('staff_override lends to debtor', do.decision == ALLOW)

    # without the grant the override is rejected
    dn = eng.checkout('R1', 'NEW2', today, staff_override=True, override_grant=False)
    check('debtor override without grant denied',
          dn.decision == DENY and 'override_unauthorised' in dn.reasons)

    # a reader inside grace (1 day overdue) is soft, not a hard debtor. STD has
    # max_dolg_books=2 so the (reduced) debtor limit is not the blocker here —
    # this isolates the debt *gate*: a soft debtor is NOT gated by reader_has_debt.
    store2, eng2 = fresh(category='STD', reader='R2')
    store2.add_loan('R2', 'SOFT', T0 - 1 * DAY, T0 - 21 * DAY)  # 1 day overdue = grace
    check('soft debtor not hard', circ.debt_level(store2, eng2.policy, 'R2', T0) != 'hard')
    d_soft = eng2.checkout('R2', 'X', T0)
    check('soft debtor not gated by reader_has_debt',
          d_soft.decision == ALLOW and 'reader_has_debt' not in d_soft.reasons)


# --------------------------------------------------------------------------- #
# 3. Renew — holds-block-renewal (§1) + cap.
# --------------------------------------------------------------------------- #
def renew_hold_checks():
    print('-- renew: holds-block-renewal')
    store, eng = fresh(category='В01')
    loan = eng.checkout('R1', 'BK', T0).computed['loan']

    # no hold → renew allowed, due pushed out, counter bumped
    d = eng.renew(loan['id'], T0 + 5 * DAY)
    check('renew allowed when no hold', d.decision == ALLOW)
    check('renew bumps counter', store.get_loan(loan['id'])['renewals'] == 1)
    check('renew pushes due out',
          store.get_loan(loan['id'])['due'] == (T0 + 5 * DAY) + 20 * DAY)
    check('renew emits renewal_confirmed',
          any(e['event'] == 'renewal_confirmed' for e in d.events))

    # another reader queues a hold on the same item → renew now blocked
    store.add_reader('R2', category='В01')
    eng.place_hold('R2', 'BK', T0 + 6 * DAY)
    d2 = eng.renew(loan['id'], T0 + 7 * DAY)
    check('renew blocked when hold exists (require_override)',
          d2.decision == REQUIRE_OVERRIDE and 'hold_exists' in d2.reasons)

    # authorised override renews past the hold
    d3 = eng.renew(loan['id'], T0 + 7 * DAY, staff_override=True, override_grant=True)
    check('renew override past hold (with grant)', d3.decision == ALLOW)

    # override without grant is rejected
    d4 = eng.renew(loan['id'], T0 + 8 * DAY, staff_override=True, override_grant=False)
    check('renew override past hold without grant denied',
          d4.decision == DENY and 'override_unauthorised' in d4.reasons)


def renew_mode_checks():
    print('-- renew: threshold / allow modes')
    # threshold mode, hold_block_threshold=1 → queue of 1 allowed, 2 blocked
    pol = default_policy()
    pol['renewal']['holds_block_renewal'] = 'threshold'
    pol['renewal']['hold_block_threshold'] = 1
    store, eng = fresh(policy=pol, category='В01')
    loan = eng.checkout('R1', 'BK', T0).computed['loan']
    store.add_reader('R2', category='В01')
    eng.place_hold('R2', 'BK', T0 + 1 * DAY)          # queue len 1 (<= threshold)
    d1 = eng.renew(loan['id'], T0 + 2 * DAY)
    check('threshold: queue<=threshold allows renew', d1.decision == ALLOW)
    store.add_reader('R3', category='В01')
    eng.place_hold('R3', 'BK', T0 + 3 * DAY)          # queue len 2 (> threshold)
    d2 = eng.renew(loan['id'], T0 + 4 * DAY)
    check('threshold: queue>threshold blocks renew',
          d2.decision == REQUIRE_OVERRIDE and 'hold_exists' in d2.reasons)

    # allow mode → hold never blocks
    pol2 = default_policy()
    pol2['renewal']['holds_block_renewal'] = 'allow'
    store2, eng2 = fresh(policy=pol2, category='В01')
    loan2 = eng2.checkout('R1', 'BK', T0).computed['loan']
    store2.add_reader('Rx', category='В01')
    eng2.place_hold('Rx', 'BK', T0 + 1 * DAY)
    check('allow mode: hold never blocks renew',
          eng2.renew(loan2['id'], T0 + 2 * DAY).decision == ALLOW)


def renew_cap_checks():
    print('-- renew: max_prolong cap')
    store, eng = fresh(category='В01')                 # max_prolong=5
    loan = eng.checkout('R1', 'BK', T0).computed['loan']
    today = T0
    for i in range(5):
        today += 1 * DAY
        d = eng.renew(loan['id'], today)
        if i == 0:
            check('renew #1 allowed', d.decision == ALLOW)
    check('5 renewals done', store.get_loan(loan['id'])['renewals'] == 5)
    d6 = eng.renew(loan['id'], today + 1 * DAY)
    check('6th renew denied by cap (hard, not override-able)',
          d6.decision == DENY and 'max_prolong_reached' in d6.reasons)
    # even an authorised override cannot beat the cap
    d6o = eng.renew(loan['id'], today + 1 * DAY, staff_override=True, override_grant=True)
    check('cap is not override-able', d6o.decision == DENY)


# --------------------------------------------------------------------------- #
# 4. Fines — §3.2 formula (numeric), grace, cap, fine-free.
# --------------------------------------------------------------------------- #
def fine_checks():
    print('-- fines: accrual formula')
    # В01 fine_per_day=5.0, overdue_grace_days=1, fine_cap=500.
    store, eng = fresh(category='В01')
    # loan due 10 days ago → 10 days overdue, grace 1 → billable 9 → 9*5 = 45.
    due = T0 - 10 * DAY
    loan = store.add_loan('R1', 'BK', due, due - 20 * DAY)
    res = eng.accrue_fines(T0)
    f = store.get_fine(loan['id'], 'fine_overdue')
    check('fine accrued for overdue loan', f is not None and f['status'] == 'accrued')
    check('fine = (10-1)*5 = 45.0', f['amount'] == 45.0)
    check('accrue result reports days', res and res[0]['days'] == 9)

    # idempotent: re-running with the same today does not double the amount
    eng.accrue_fines(T0)
    check('accrual idempotent (same today, same amount)',
          store.get_fine(loan['id'], 'fine_overdue')['amount'] == 45.0)

    # cap: a long overdue is capped at fine_cap (500)
    store2, eng2 = fresh(category='В01', reader='R2')
    due2 = T0 - 200 * DAY                               # 199 billable * 5 = 995 > cap
    loan2 = store2.add_loan('R2', 'BK2', due2, due2 - 20 * DAY)
    eng2.accrue_fines(T0)
    check('fine capped at fine_cap=500',
          store2.get_fine(loan2['id'], 'fine_overdue')['amount'] == 500.0)

    # within grace → no fine (1 day overdue, grace 1 → billable 0)
    store3, eng3 = fresh(category='В01', reader='R3')
    loan3 = store3.add_loan('R3', 'BK3', T0 - 1 * DAY, T0 - 21 * DAY)
    eng3.accrue_fines(T0)
    check('no fine within grace', store3.get_fine(loan3['id'], 'fine_overdue') is None)

    # fine-free category (Д01 rate 0) → never accrues
    store4, eng4 = fresh(category='Д01', reader='R4')
    loan4 = store4.add_loan('R4', 'BK4', T0 - 30 * DAY, T0 - 44 * DAY)
    eng4.accrue_fines(T0)
    check('fine-free category accrues nothing',
          store4.get_fine(loan4['id'], 'fine_overdue') is None)


def fine_lifecycle_checks():
    print('-- fines: charge on return, waive, pay')
    store, eng = fresh(category='В01')
    due = T0 - 10 * DAY
    loan = store.add_loan('R1', 'BK', due, due - 20 * DAY)
    d = eng.return_item(loan['id'], T0)
    check('return marks loan returned', store.get_loan(loan['id'])['returned'] == 1)
    check('return charges accrued fine (45)', d.computed.get('fine_charged') == 45.0)
    check('return emits fine_charged event',
          any(e['event'] == 'fine_charged' for e in d.events))
    check('fine now charged', store.get_fine(loan['id'], 'fine_overdue')['status'] == 'charged')

    # waive needs the grant
    store2, eng2 = fresh(category='В01', reader='R2')
    due2 = T0 - 10 * DAY
    loan2 = store2.add_loan('R2', 'BK2', due2, due2 - 20 * DAY)
    eng2.accrue_fines(T0)
    check('waive without grant denied',
          eng2.waive_fine(loan2['id'], override_grant=False).decision == DENY)
    check('waive with grant allowed',
          eng2.waive_fine(loan2['id'], override_grant=True).decision == ALLOW)
    check('waived fine status', store2.get_fine(loan2['id'], 'fine_overdue')['status'] == 'waived')

    # pay closes the money; on-hand marker only cleared by return (independence §3.5)
    store3, eng3 = fresh(category='В01', reader='R3')
    due3 = T0 - 10 * DAY
    loan3 = store3.add_loan('R3', 'BK3', due3, due3 - 20 * DAY)
    eng3.accrue_fines(T0)
    eng3.pay_fine(loan3['id'])
    check('pay marks fine paid', store3.get_fine(loan3['id'], 'fine_overdue')['status'] == 'paid')
    check('pay does NOT return the loan (40^F independent)',
          store3.get_loan(loan3['id'])['returned'] == 0)


# --------------------------------------------------------------------------- #
# 5. Hold queue — FIFO position (§6) + return triggers hold-ready.
# --------------------------------------------------------------------------- #
def hold_queue_checks():
    print('-- hold queue: FIFO position')
    store, eng = fresh(category='В01')
    holder = eng.checkout('R1', 'BK', T0).computed['loan']  # R1 holds the item
    store.add_reader('R2', category='В01')
    store.add_reader('R3', category='В01')
    store.add_reader('R4', category='В01')

    eng.place_hold('R2', 'BK', T0 + 1 * DAY)
    eng.place_hold('R3', 'BK', T0 + 2 * DAY)
    eng.place_hold('R4', 'BK', T0 + 3 * DAY)
    check('R2 is position 1 (FIFO)', eng.queue_position('BK', 'R2') == 1)
    check('R3 is position 2 (FIFO)', eng.queue_position('BK', 'R3') == 2)
    check('R4 is position 3 (FIFO)', eng.queue_position('BK', 'R4') == 3)
    check('non-queued reader position 0', eng.queue_position('BK', 'R9') == 0)

    # a free item → first hold is ready immediately at position 1
    store5, eng5 = fresh(category='В01', reader='R5')
    dh = eng5.place_hold('R5', 'FREE', T0)
    check('hold on free item is position 1', dh.computed['position'] == 1)
    check('hold on free item is ready',
          store5.get_hold(dh.computed['hold']['id'])['status'] == 'ready')


def return_triggers_hold_checks():
    print('-- return triggers hold-ready')
    store, eng = fresh(category='В01')
    loan = eng.checkout('R1', 'BK', T0).computed['loan']
    store.add_reader('R2', category='В01')
    store.add_reader('R3', category='В01')
    h2 = eng.place_hold('R2', 'BK', T0 + 1 * DAY).computed['hold']
    eng.place_hold('R3', 'BK', T0 + 2 * DAY)

    d = eng.return_item(loan['id'], T0 + 5 * DAY)
    check('return is allowed', d.decision == ALLOW)
    check('return makes head hold ready (R2)', d.computed.get('hold_ready') == h2['id'])
    check('head hold status ready', store.get_hold(h2['id'])['status'] == 'ready')
    check('return emits hold_ready to R2',
          any(e['event'] == 'hold_ready' and e['recipient'] == 'R2' for e in d.events))
    check('R3 still queued behind', eng.queue_position('BK', 'R3') == 2)


# --------------------------------------------------------------------------- #
# 6. Lost — candidate → confirm → replacement (§4).
# --------------------------------------------------------------------------- #
def lost_checks():
    print('-- lost: candidate -> confirm -> replacement')
    store, eng = fresh(category='В01')                 # lost_after_days=60
    # 90 days overdue → over the lost threshold
    due = T0 - 90 * DAY
    loan = store.add_loan('R1', 'BK', due, due - 20 * DAY, item_price=300.0)

    scan = eng.scan_lost_candidates(T0)
    check('over-overdue flagged lost_candidate', loan['id'] in scan.computed['candidates'])
    check('candidate emits staff_alert',
          any(e['event'] == 'staff_alert' for e in scan.events))
    check('candidate is NOT auto-debt (no replacement fine yet)',
          store.get_fine(loan['id'], 'lost_replacement') is None)

    # confirm needs the grant
    check('lost confirm without grant denied',
          eng.mark_lost(loan['id'], T0, confirm=True, override_grant=False).decision == DENY)

    d = eng.mark_lost(loan['id'], T0, confirm=True, override_grant=True)
    check('lost confirm allowed with grant', d.decision == ALLOW)
    check('loan status lost', store.get_loan(loan['id'])['lost_status'] == 'lost')
    check('replacement = price*1.0 = 300', d.computed['replacement_value'] == 300.0)
    rf = store.get_fine(loan['id'], 'lost_replacement')
    check('replacement charged to PAY', rf is not None and rf['status'] == 'charged')
    check('lost emits lost_confirmed (ws2 signal)',
          any(e['event'] == 'lost_confirmed' for e in d.events))

    # fallback when price empty/0 → default_replacement_value (100)
    store2, eng2 = fresh(category='В01', reader='R2')
    due2 = T0 - 90 * DAY
    loan2 = store2.add_loan('R2', 'BK2', due2, due2 - 20 * DAY, item_price=0)
    d2 = eng2.mark_lost(loan2['id'], T0, confirm=True, override_grant=True)
    check('empty price falls back to default replacement (100)',
          d2.computed['replacement_value'] == 100.0)

    # lost supersedes accrued overdue fine (not billed twice)
    store3, eng3 = fresh(category='В01', reader='R3')
    due3 = T0 - 90 * DAY
    loan3 = store3.add_loan('R3', 'BK3', due3, due3 - 20 * DAY, item_price=200.0)
    eng3.accrue_fines(T0)
    check('overdue fine accrued before lost',
          store3.get_fine(loan3['id'], 'fine_overdue') is not None)
    eng3.mark_lost(loan3['id'], T0, confirm=True, override_grant=True)
    check('lost_supersedes_fine waives overdue fine',
          store3.get_fine(loan3['id'], 'fine_overdue')['status'] == 'waived')


# --------------------------------------------------------------------------- #
# 7. Tenant policy isolation (AC7) + GUEST category.
# --------------------------------------------------------------------------- #
def isolation_checks():
    print('-- tenant isolation + category limits')
    # Two tenants with different policies; one's tweak never affects the other.
    polA = default_policy('A')
    polA['limits']['В01']['max_books'] = 2
    polB = default_policy('B')   # default max_books 5
    storeA, engA = fresh(policy=polA, category='В01', reader='RA')
    storeB, engB = fresh(policy=polB, category='В01', reader='RB')
    engA.checkout('RA', 'b1', T0)
    engA.checkout('RA', 'b2', T0)
    check('tenant A hits its own (lower) limit at 3rd',
          engA.checkout('RA', 'b3', T0).decision == REQUIRE_OVERRIDE)
    # tenant B with default 5 still lends a 3rd freely
    engB.checkout('RB', 'b1', T0)
    engB.checkout('RB', 'b2', T0)
    check('tenant B keeps its own (higher) limit',
          engB.checkout('RB', 'b3', T0).decision == ALLOW)

    # GUEST: max_books 1 — second checkout requires override
    storeG, engG = fresh(category='GUEST', reader='G1')
    check('guest first checkout allowed', engG.checkout('G1', 'g1', T0).decision == ALLOW)
    check('guest second checkout over limit',
          engG.checkout('G1', 'g2', T0).decision == REQUIRE_OVERRIDE)


def op_id_idempotency_checks():
    print('-- op_id идемпотентность (BDP replay, #412)')
    store, eng = fresh()
    d1 = eng.checkout('R1', 'BK-OP', T0, op_id='op-abc')
    check('первая выдача с op_id allowed', d1.decision == ALLOW)
    loan1 = d1.computed['loan']
    check('loan получил op_id', loan1.get('op_id') == 'op-abc')

    # Повтор того же op_id (sync.replay) не создаёт вторую выдачу.
    d2 = eng.checkout('R1', 'BK-OP', T0, op_id='op-abc')
    check('replay того же op_id allowed', d2.decision == ALLOW)
    check('replay помечен replayed', d2.computed.get('replayed') is True)
    check('replay вернул ту же выдачу', d2.computed['loan']['id'] == loan1['id'])
    check('вторая loan не создана', store.count_on_hand('R1') == 1)

    # Разные op_id → разные выдачи.
    d3 = eng.checkout('R1', 'BK-OP2', T0, op_id='op-xyz')
    check('другой op_id -> новая выдача', d3.computed['loan']['id'] != loan1['id'])
    check('на руках 2', store.count_on_hand('R1') == 2)

    # Staff-путь без op_id — несколько выдач без конфликта (NULL'ы различны).
    s2, e2 = fresh()
    a = e2.checkout('R1', 'S1', T0)
    b = e2.checkout('R1', 'S2', T0)
    check('staff без op_id: обе ok', a.decision == ALLOW and b.decision == ALLOW)
    check('op_id staff-выдачи NULL', a.computed['loan'].get('op_id') is None)

    check('get_loan_by_op_id находит', store.get_loan_by_op_id('op-abc')['id'] == loan1['id'])
    check('get_loan_by_op_id(None) -> None', store.get_loan_by_op_id(None) is None)


def saga_checks():
    print('-- BDP-сага reserve->commit/rollback (#415)')
    store, eng = fresh()
    d = eng.reserve('R1', 'BK-S', T0, op_id='op-s1')
    check('reserve allowed + phase', d.decision == ALLOW and d.computed['phase'] == 'reserve')
    check('reserve создал PENDING-loan', d.computed['loan']['pending'] == 1)
    check('reserve засчитан в on_hand', store.count_on_hand('R1') == 1)
    d2 = eng.reserve('R1', 'BK-S', T0, op_id='op-s1')
    check('reserve replay идемпотентен', d2.computed.get('replayed') is True and store.count_on_hand('R1') == 1)
    c = eng.commit('op-s1')
    check('commit allowed', c.decision == ALLOW and c.computed['phase'] == 'commit')
    check('commit снял pending', c.computed['loan']['pending'] == 0)
    check('после commit on_hand=1', store.count_on_hand('R1') == 1)
    check('commit повтор ок', eng.commit('op-s1').decision == ALLOW)
    check('rollback committed → already_committed', 'already_committed' in eng.rollback('op-s1').reasons)

    store2, eng2 = fresh()
    eng2.reserve('R1', 'BK-R', T0, op_id='op-r1')
    check('до rollback on_hand=1', store2.count_on_hand('R1') == 1)
    rb = eng2.rollback('op-r1')
    check('rollback allowed', rb.decision == ALLOW and rb.computed['phase'] == 'rollback')
    check('после rollback on_hand=0 (компенсация)', store2.count_on_hand('R1') == 0)
    check('rollback неизвестного op_id → DENY', eng2.rollback('nope').decision == DENY)
    check('commit неизвестного op_id → DENY', eng2.commit('nope').decision == DENY)

    store3, eng3 = fresh()
    store3.set_blocked('R1', 1)
    dd = eng3.reserve('R1', 'BK-X', T0, op_id='op-x')
    check('reserve заблокированному → DENY', dd.decision == DENY and 'reader_blocked' in dd.reasons)
    check('отказной reserve не создал loan', store3.count_on_hand('R1') == 0)

    store4, eng4 = fresh()
    eng4.reserve('R1', 'BK-T', T0, op_id='op-t')
    check('до expire pending=1', len(store4.pending_loans()) == 1)
    rolled = eng4.expire_pending(now=T0 + 10 * DAY, ttl=1 * DAY)
    check('expire откатил зависший резерв', len(rolled) == 1 and store4.count_on_hand('R1') == 0)


def main():
    store_and_policy_checks()
    op_id_idempotency_checks()
    saga_checks()
    checkout_limit_checks()
    checkout_debtor_checks()
    renew_hold_checks()
    renew_mode_checks()
    renew_cap_checks()
    fine_checks()
    fine_lifecycle_checks()
    hold_queue_checks()
    return_triggers_hold_checks()
    lost_checks()
    isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
