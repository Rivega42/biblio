#!/usr/bin/env python3
"""Тесты DEBTORS — реестр задолженностей/санкций АРМ Книговыдача.

Покрыто (in-memory + фиксированные ISO-даты + fake-clock для детерминизма):
  * `days_overdue` — просрочка (14 дней), ровно в срок -> 0, до срока -> 0;
  * `register_overdue` — amount = дни * тариф; нулевая просрочка -> 0;
  * `register_lost` — amount = стоимость замены;
  * `reader_debts` — total/count только по unsettled; `settle` убирает из unsettled;
  * `evaluate_block` — по сумме (>threshold -> block), по количеству
    (>=threshold_count -> block), один долг -> warn, ноль долгов -> unblock;
    идемпотентность блокировки (upsert);
  * `is_blocked`; `debtors_report` — by_kind / total_owed / readers_with_debt.

Запуск: py -3.12 tests/test_debtors.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import debtors

PASS = [0]
FAIL = [0]

# Детерминированные «часы» для created_at (момент регистрации долга/блокировки).
CLOCK = '2026-06-15T00:00:00+00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def svc():
    """Свежий сервис на чистом in-memory сторе с фиксированными часами."""
    return debtors.DebtorsService(store=debtors.DebtStore(':memory:'),
                                  now=lambda: CLOCK)


def days_overdue_checks():
    print('-- days_overdue: целые дни просрочки по календарю')
    d = debtors.DebtorsService
    check('14 дней просрочки', d.days_overdue('2026-06-01', '2026-06-15') == 14)
    check('ровно в срок -> 0', d.days_overdue('2026-06-15', '2026-06-15') == 0)
    check('до срока -> 0', d.days_overdue('2026-06-20', '2026-06-15') == 0)
    check('1 день просрочки', d.days_overdue('2026-06-14', '2026-06-15') == 1)
    check('пустой due_date -> 0', d.days_overdue('', '2026-06-15') == 0)


def register_overdue_checks():
    print('-- register_overdue: amount = дни * тариф/день (копеек)')
    s = svc()
    deb = s.register_overdue('R1', 'BK-1', due_date='2026-06-01',
                             as_of='2026-06-15', fine_per_day_kopecks=500)
    check('kind overdue', deb['kind'] == 'overdue')
    check('amount = 14 * 500 = 7000', deb['amount_kopecks'] == 7000)
    check('not settled', deb['settled'] == 0)
    check('created_at от часов', deb['created_at'] == CLOCK)
    z = s.register_overdue('R1', 'BK-2', due_date='2026-06-15',
                           as_of='2026-06-15', fine_per_day_kopecks=500)
    check('нулевая просрочка -> amount 0', z['amount_kopecks'] == 0)


def register_lost_checks():
    print('-- register_lost: amount = стоимость замены')
    s = svc()
    deb = s.register_lost('R2', 'BK-9', replacement_kopecks=120000)
    check('kind lost', deb['kind'] == 'lost')
    check('amount = replacement', deb['amount_kopecks'] == 120000)
    check('due_date None у lost', deb['due_date'] is None)


def reader_debts_settle_checks():
    print('-- reader_debts / settle: total/count только по unsettled')
    s = svc()
    a = s.register_overdue('R3', 'BK-1', '2026-06-01', '2026-06-15', 500)  # 7000
    s.register_lost('R3', 'BK-2', 3000)                                    # 3000
    rd = s.reader_debts('R3')
    check('count 2', rd['count'] == 2)
    check('total 10000', rd['total'] == 10000)
    ok = s.settle(a['id'])
    check('settle вернул True', ok is True)
    rd2 = s.reader_debts('R3')
    check('после settle count 1', rd2['count'] == 1)
    check('после settle total 3000', rd2['total'] == 3000)
    check('повторный settle -> False', s.settle(a['id']) is False)


def evaluate_block_checks():
    print('-- evaluate_block: эскалация warn/block по сумме и количеству')
    # по сумме: один крупный долг при threshold_count=99 -> block из-за total
    s1 = svc()
    s1.register_lost('RB', 'BK-1', 5000)
    st1 = s1.evaluate_block('RB', threshold_kopecks=1000, threshold_count=99)
    check('сумма > порога -> block', st1['level'] == 'block')
    check('состояние total 5000', st1['total'] == 5000)
    # один долг ниже порогов -> warn
    s2 = svc()
    s2.register_lost('RW', 'BK-1', 500)
    st2 = s2.evaluate_block('RW', threshold_kopecks=1000, threshold_count=3)
    check('один долг ниже порогов -> warn', st2['level'] == 'warn')
    check('warn -> не is_blocked', s2.is_blocked('RW') is False)
    # по количеству: 3 мелких долга при высоком пороге суммы -> block
    s3 = svc()
    for i in range(3):
        s3.register_lost('RC', 'BK-%d' % i, 100)
    st3 = s3.evaluate_block('RC', threshold_kopecks=10 ** 9, threshold_count=3)
    check('count >= порога -> block', st3['level'] == 'block')
    check('count 3', st3['count'] == 3)
    # ноль долгов -> снять блокировку
    s4 = svc()
    s4.register_lost('RU', 'BK-1', 9000)
    s4.evaluate_block('RU', threshold_kopecks=1000, threshold_count=3)
    check('сначала заблокирован', s4.is_blocked('RU') is True)
    only = s4.reader_debts('RU')['items'][0]
    s4.settle(only['id'])
    st4 = s4.evaluate_block('RU', threshold_kopecks=1000, threshold_count=3)
    check('ноль долгов -> level None', st4['level'] is None)
    check('ноль долгов -> unblock', s4.is_blocked('RU') is False)


def block_idempotent_checks():
    print('-- evaluate_block идемпотентен (upsert одной записи)')
    s = svc()
    s.register_lost('RI', 'BK-1', 9000)
    s.evaluate_block('RI', threshold_kopecks=1000, threshold_count=3)
    s.evaluate_block('RI', threshold_kopecks=1000, threshold_count=3)
    blocked = s.store.blocked_readers()
    rows = [b for b in blocked if b['reader'] == 'RI']
    check('одна запись блокировки (не дубль)', len(rows) == 1)
    check('is_blocked после повтора', s.is_blocked('RI') is True)
    check('get_block уровень block',
          s.store.get_block('RI')['level'] == 'block')


def is_blocked_checks():
    print('-- is_blocked: True только при level=block')
    s = svc()
    check('неизвестный читатель -> False', s.is_blocked('NOPE') is False)
    s.store.block_reader('RX', 'warn-only', 'warn', CLOCK)
    check('warn -> is_blocked False', s.is_blocked('RX') is False)
    s.store.block_reader('RX', 'now blocked', 'block', CLOCK)
    check('block -> is_blocked True', s.is_blocked('RX') is True)


def debtors_report_checks():
    print('-- debtors_report: агрегат по всем открытым долгам')
    s = svc()
    s.register_overdue('A', 'BK-1', '2026-06-01', '2026-06-15', 500)  # 7000 overdue
    s.register_lost('A', 'BK-2', 3000)                                # 3000 lost
    s.register_lost('B', 'BK-3', 12000)                               # 12000 lost
    rep = s.debtors_report()
    check('readers_with_debt 2', rep['readers_with_debt'] == 2)
    check('total_owed 22000', rep['total_owed'] == 22000)
    check('by_kind overdue 7000', rep['by_kind']['overdue'] == 7000)
    check('by_kind lost 15000', rep['by_kind']['lost'] == 15000)
    # погашение исключает долг из отчёта
    deb = s.reader_debts('B')['items'][0]
    s.settle(deb['id'])
    rep2 = s.debtors_report()
    check('после settle readers_with_debt 1', rep2['readers_with_debt'] == 1)
    check('после settle total_owed 10000', rep2['total_owed'] == 10000)


def main():
    days_overdue_checks()
    register_overdue_checks()
    register_lost_checks()
    reader_debts_settle_checks()
    evaluate_block_checks()
    block_idempotent_checks()
    is_blocked_checks()
    debtors_report_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
