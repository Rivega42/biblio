#!/usr/bin/env python3
"""Тесты ребра 3.3 — утеря/штраф -> касса PAY + цена замены из каталога 910^E.

Покрыто:
  * `PayLedger`: проводки начисления/платежа, баланс = Σ начислений − Σ платежей,
    неизвестный charge-kind -> ValueError, изоляция читателей;
  * circulation: `mark_lost(confirm)` берёт цену замены из каталога 910^E (когда
    `item_price` пуст) и постит возмещение в PAY; приоритет `item_price` над
    каталогом; fallback на дефолт политики;
  * штраф за просрочку фиксируется в PAY на возврате, оплата -> проводка платежа;
  * back-compat: без `pay`-хендла поведение прежнее; сбой PAY не роняет операцию.

Запуск: py -3.12 tests/test_pay.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.pay import PayLedger, PayStore
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


class _Cat:
    """Минимальный каталог-заглушка: find_exemplar -> (mfn, idx, {'e': price})."""

    def __init__(self, price=None):
        self._price = price

    def find_exemplar(self, db, item):
        if self._price is None:
            return None
        return (1, 0, {'e': self._price})


def ledger_checks():
    print('-- PayLedger: проводки + баланс')
    led = PayLedger(PayStore(':memory:'))
    e = led.post_charge('R1', 100.0, 'lost_replacement', ref='L1')
    check('charge записан', e['kind'] == 'lost_replacement' and e['amount'] == 100.0
          and e['reader'] == 'R1')
    led.post_charge('R1', 50.0, 'fine_overdue', ref='L2')
    check('баланс = сумма начислений (150)', led.balance('R1') == 150.0)
    led.post_payment('R1', 60.0, ref='L2')
    check('баланс после платежа (90)', led.balance('R1') == 90.0)
    check('entries хронологичны (3)', len(led.entries('R1')) == 3)
    bad = False
    try:
        led.post_charge('R1', 10, 'nonsense')
    except ValueError:
        bad = True
    check('неизвестный charge-kind -> ValueError', bad)
    check('другой читатель изолирован (0)', led.balance('R2') == 0)


def lost_price_910e_checks():
    print('-- 3.3: цена замены из каталога 910^E + проводка возмещения в PAY')
    store = CirculationStore(':memory:')
    led = PayLedger(PayStore(':memory:'))
    eng = CirculationEngine(store=store, policy=default_policy(),
                            catalog=_Cat('500'), pay=led)
    store.add_reader('R1', category='В01')
    loan = store.add_loan('R1', 'BK-1', T0 + 10 * DAY, T0, item_price=None)
    d = eng.mark_lost(loan['id'], T0 + 100 * DAY, confirm=True, override_grant=True)
    check('mark_lost ALLOW', d.decision == ALLOW)
    check('цена замены = 910^E (500)', d.computed['replacement_value'] == 500.0)
    check('PAY: баланс = возмещение 500', led.balance('R1') == 500.0)
    ents = led.entries('R1')
    check('PAY: одна проводка lost_replacement',
          len(ents) == 1 and ents[0]['kind'] == 'lost_replacement')
    check('PAY: ref = loan id', ents[0]['ref'] == str(loan['id']))


def lost_price_priority_checks():
    print('-- 3.3: приоритет item_price над 910^E; fallback на дефолт политики')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(), catalog=_Cat('500'))
    store.add_reader('R1', category='В01')
    l1 = store.add_loan('R1', 'BK-A', T0 + 10 * DAY, T0, item_price=700.0)
    d1 = eng.mark_lost(l1['id'], T0 + 100 * DAY, confirm=True, override_grant=True)
    check('item_price на выдаче приоритетнее 910^E (700)',
          d1.computed['replacement_value'] == 700.0)

    eng2 = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy())   # нет каталога
    eng2.store.add_reader('R1', category='В01')
    l2 = eng2.store.add_loan('R1', 'BK-B', T0 + 10 * DAY, T0, item_price=None)
    d2 = eng2.mark_lost(l2['id'], T0 + 100 * DAY, confirm=True, override_grant=True)
    check('нет цены/каталога -> дефолт политики (100)',
          d2.computed['replacement_value']
          == default_policy()['lost']['default_replacement_value'])


def fine_pay_flow_checks():
    print('-- 3.3: штраф на возврате -> PAY charge, оплата -> PAY payment')
    store = CirculationStore(':memory:')
    led = PayLedger(PayStore(':memory:'))
    eng = CirculationEngine(store=store, policy=default_policy(), pay=led)
    store.add_reader('R1', category='В01')             # fine_per_day _DEFAULT=5
    due = T0 - 10 * DAY
    loan = store.add_loan('R1', 'BK-F', due, due - 20 * DAY)
    d = eng.return_item(loan['id'], T0)
    amt = d.computed.get('fine_charged')
    check('возврат начислил штраф (>0)', bool(amt) and amt > 0)
    check('PAY: штраф проведён', led.balance('R1') == amt)
    eng.pay_fine(loan['id'])
    check('PAY: после оплаты баланс 0', led.balance('R1') == 0.0)
    kinds = [e['kind'] for e in led.entries('R1')]
    check('PAY: проводки [fine_overdue, payment]', kinds == ['fine_overdue', 'payment'])


def backcompat_checks():
    print('-- 3.3: без pay-хендла прежнее поведение; сбой PAY не роняет')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())   # pay=None
    store.add_reader('R1', category='В01')
    loan = store.add_loan('R1', 'BK-X', T0 + 10 * DAY, T0, item_price=300.0)
    d = eng.mark_lost(loan['id'], T0 + 100 * DAY, confirm=True, override_grant=True)
    check('mark_lost ALLOW без pay', d.decision == ALLOW)
    check('возмещение посчитано (300)', d.computed['replacement_value'] == 300.0)

    class _Boom:
        def post_charge(self, *a, **k):
            raise RuntimeError('pay down')

        def post_payment(self, *a, **k):
            raise RuntimeError('pay down')

    eng2 = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), pay=_Boom())
    eng2.store.add_reader('R1', category='В01')
    l = eng2.store.add_loan('R1', 'BK-Y', T0 + 10 * DAY, T0, item_price=300.0)
    d2 = eng2.mark_lost(l['id'], T0 + 100 * DAY, confirm=True, override_grant=True)
    check('сбой PAY не роняет mark_lost', d2.decision == ALLOW)


def main():
    ledger_checks()
    lost_price_910e_checks()
    lost_price_priority_checks()
    fine_pay_flow_checks()
    backcompat_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
