#!/usr/bin/env python3
"""Тесты LOAN POLICY — декларативные политики выдачи АРМ «Книговыдация» (own-store).

Покрыто:
  * стор: upsert (новая/обновление), get_policy, list_policies, delete_policy;
  * resolve — вся цепочка фолбэка по убыванию специфичности с меткой `matched`:
    exact > category > type > global > default (зеркало authz.best_grant);
  * check_loan — выдача vs limit_reached на границе
    (current_count == max_items запрещает, max_items-1 разрешает);
  * can_renew — граница renewals_used < renewals;
  * fine_for — 0 без просрочки, days*rate при просрочке, отрицательные дни -> 0;
  * DEFAULT_POLICY — когда стор пуст.

Запуск: py -3.12 tests/test_loan_policy.py ; в агрегаторе test_access.py.
ASCII `->` в принтах (cp1251-консоль падает на юникод-стрелках).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import loan_policy

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Детерминированные часы для updated_at.
class _Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-01-01T00:00:%02dZ' % self.t


def _svc():
    """In-memory сервис с фейковыми часами."""
    return loan_policy.LoanPolicyService(
        store=loan_policy.LoanPolicyStore(':memory:', now=_Clock()))


def store_checks():
    print('-- store: upsert / get / list / delete')
    s = loan_policy.LoanPolicyStore(':memory:', now=_Clock())
    p = s.upsert_policy('В01', 'book', 30, 10, renewals=2,
                        deposit_kopecks=0, fine_per_day_kopecks=300)
    check('upsert вернул dict', isinstance(p, dict))
    check('loan_days сохранён', p['loan_days'] == 30)
    check('max_items сохранён', p['max_items'] == 10)
    check('renewals сохранён', p['renewals'] == 2)
    check('fine_per_day сохранён', p['fine_per_day_kopecks'] == 300)
    check('updated_at проставлен', bool(p['updated_at']))
    check('get_policy точная пара', s.get_policy('В01', 'book')['loan_days'] == 30)
    check('get_policy промах -> None', s.get_policy('В99', 'book') is None)
    # Обновление той же пары — не дубль, новые значения.
    p2 = s.upsert_policy('В01', 'book', 45, 12)
    check('upsert update loan_days', p2['loan_days'] == 45)
    check('upsert update max_items', p2['max_items'] == 12)
    check('upsert update не плодит дубль', len(s.list_policies()) == 1)
    s.upsert_policy('В02', 'journal', 7, 3)
    check('list_policies 2 правила', len(s.list_policies()) == 2)
    pid = s.get_policy('В02', 'journal')['id']
    check('delete_policy True', s.delete_policy(pid) is True)
    check('delete снизил счёт', len(s.list_policies()) == 1)
    check('delete несуществующего -> False', s.delete_policy(999999) is False)


def resolve_checks():
    print('-- resolve: цепочка фолбэка exact > category > type > global > default')
    svc = _svc()
    # Заселяем все четыре уровня разными loan_days, чтобы видеть, какой сработал.
    svc.set_policy('В01', 'book', 40, 9)            # exact
    svc.set_policy('В01', '*', 35, 8)               # category
    svc.set_policy('*', 'book', 25, 7)              # type
    svc.set_policy('*', '*', 20, 6)                 # global

    r = svc.resolve('В01', 'book')
    check('exact matched', r['matched'] == 'exact')
    check('exact loan_days', r['loan_days'] == 40)

    # Убираем exact -> должен сработать category (cat,'*').
    svc.store.delete_policy(svc.store.get_policy('В01', 'book')['id'])
    r = svc.resolve('В01', 'book')
    check('category matched', r['matched'] == 'category')
    check('category loan_days', r['loan_days'] == 35)

    # Убираем category -> должен сработать type ('*',type).
    svc.store.delete_policy(svc.store.get_policy('В01', '*')['id'])
    r = svc.resolve('В01', 'book')
    check('type matched', r['matched'] == 'type')
    check('type loan_days', r['loan_days'] == 25)

    # Убираем type -> должен сработать global ('*','*').
    svc.store.delete_policy(svc.store.get_policy('*', 'book')['id'])
    r = svc.resolve('В01', 'book')
    check('global matched', r['matched'] == 'global')
    check('global loan_days', r['loan_days'] == 20)

    # Убираем global -> остаётся встроенный DEFAULT_POLICY.
    svc.store.delete_policy(svc.store.get_policy('*', '*')['id'])
    r = svc.resolve('В01', 'book')
    check('default matched', r['matched'] == 'default')
    check('default loan_days', r['loan_days'] == loan_policy.DEFAULT_POLICY['loan_days'])
    check('default из пустого стора', svc.resolve('X', 'y')['matched'] == 'default')


def check_loan_checks():
    print('-- check_loan: выдача vs limit_reached на границе')
    svc = _svc()
    svc.set_policy('В01', 'book', 14, 5)            # max_items=5
    # На границе: current_count == max_items запрещает.
    r = svc.check_loan('В01', 'book', 5)
    check('на лимите -> запрет', r['allowed'] is False)
    check('reason limit_reached', r['reason'] == 'limit_reached')
    # max_items-1 разрешает.
    r = svc.check_loan('В01', 'book', 4)
    check('ниже лимита -> разрешено', r['allowed'] is True)
    check('reason ok', r['reason'] == 'ok')
    check('check_loan отдаёт loan_days', r['loan_days'] == 14)
    check('check_loan отдаёт max_items', r['max_items'] == 5)
    # Сверх лимита тоже запрет.
    check('сверх лимита -> запрет', svc.check_loan('В01', 'book', 6)['allowed'] is False)
    # Пустой стор -> дефолтный лимит 5.
    svc2 = _svc()
    check('пустой стор -> дефолт max_items 5',
          svc2.check_loan('В01', 'book', 5)['allowed'] is False)
    check('пустой стор -> ниже дефолта разрешено',
          svc2.check_loan('В01', 'book', 4)['allowed'] is True)


def can_renew_checks():
    print('-- can_renew: граница renewals_used < renewals')
    svc = _svc()
    svc.set_policy('В01', 'book', 14, 5, renewals=2)
    check('0 использовано -> можно', svc.can_renew('В01', 'book', 0) is True)
    check('1 использовано -> можно', svc.can_renew('В01', 'book', 1) is True)
    check('2 использовано (на границе) -> нельзя',
          svc.can_renew('В01', 'book', 2) is False)
    check('3 использовано -> нельзя', svc.can_renew('В01', 'book', 3) is False)


def fine_for_checks():
    print('-- fine_for: 0 без просрочки, days*rate при просрочке, отриц. -> 0')
    svc = _svc()
    svc.set_policy('В01', 'book', 14, 5, fine_per_day=700)
    check('0 дней -> 0', svc.fine_for('В01', 'book', 0) == 0)
    check('3 дня -> 3*700', svc.fine_for('В01', 'book', 3) == 2100)
    check('отрицательные дни -> 0', svc.fine_for('В01', 'book', -5) == 0)
    # Пустой стор -> дефолтная ставка 500 коп/день.
    svc2 = _svc()
    rate = loan_policy.DEFAULT_POLICY['fine_per_day_kopecks']
    check('пустой стор -> дефолтная ставка', svc2.fine_for('X', 'y', 2) == 2 * rate)


def main():
    store_checks()
    resolve_checks()
    check_loan_checks()
    can_renew_checks()
    fine_for_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
