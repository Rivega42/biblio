#!/usr/bin/env python3
"""Тесты контура Комплектование — подписка на периодику (kardex).

Покрыто:
  * subscribe — оформление подписки на сериальное издание у поставщика;
  * generate_issues — авто-создание ожидаемых номеров плана (идемпотентно по
    (subscription_id, number, year));
  * receive_issue — регистрация поступления выпуска (+ pending уменьшается);
  * pending — ожидаемые, но не поступившие номера (kardex-дыры);
  * find по подстроке заглавия (кириллица — фильтр в Python);
  * stats {subscriptions, issues, received, pending};
  * receive_issue несуществующего номера -> None.

Запуск: py -3.12 tests/test_subscription.py ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.subscription import SubscriptionService, SubscriptionStore

PASS = [0]
FAIL = [0]
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _svc(clock=None):
    return SubscriptionService(SubscriptionStore(':memory:'), now=clock)


def subscribe_checks():
    print('-- subscribe: оформление подписки')
    svc = _svc(lambda: T0)
    s = svc.subscribe('Библиотечное дело', issn='1234-5678', supplier_id=7,
                      period_from='2024-01', period_to='2024-12', copies=2)
    check('подписка оформлена',
          s['title'] == 'Библиотечное дело' and s['issn'] == '1234-5678'
          and s['supplier_id'] == 7 and s['copies'] == 2)
    check('период подписки сохранён',
          s['period_from'] == '2024-01' and s['period_to'] == '2024-12')
    check('get -> подписка + счётчики',
          svc.get(s['id'])['issues_count'] == 0)
    check('list_subscriptions -> 1', len(svc.list_subscriptions()) == 1)
    check('get несуществующей -> None', svc.get(999) is None)


def generate_idempotent_checks():
    print('-- generate_issues: авто-создание плана (идемпотентно)')
    svc = _svc(lambda: T0)
    s = svc.subscribe('Знание - сила')
    plan = svc.generate_issues(s['id'], ['1', '2', '3'], '2024')
    check('создан план из 3 ожидаемых номеров', len(plan) == 3)
    check('номера ожидаемые, не поступившие',
          all(i['expected'] == 1 and i['received'] == 0 for i in plan))
    # повтор того же диапазона + расширение
    plan2 = svc.generate_issues(s['id'], ['2', '3', '4'], '2024')
    check('повтор вернул те же id для #2,#3',
          plan2[0]['id'] == plan[1]['id'] and plan2[1]['id'] == plan[2]['id'])
    stats = svc.stats()
    check('задвоения нет: всего 4 номера (1..4)', stats['issues'] == 4)
    check('generate в несуществующую подписку -> None',
          svc.generate_issues(999, ['1'], '2024') is None)


def receive_pending_checks():
    print('-- receive_issue + pending (kardex-дыры)')
    svc = _svc(lambda: T0)
    s = svc.subscribe('Научный мир')
    svc.generate_issues(s['id'], ['1', '2', '3'], '2024')
    check('изначально ожидаем 3 номера', len(svc.pending(s['id'])) == 3)

    r = svc.receive_issue(s['id'], '2', '2024')
    check('поступление зарегистрировано',
          r is not None and r['received'] == 1 and r['received_at'] == T0)
    check('pending уменьшился до 2', len(svc.pending(s['id'])) == 2)
    check('kardex-дыры — это #1 и #3',
          sorted(i['number'] for i in svc.pending(s['id'])) == ['1', '3'])

    svc.receive_issue(s['id'], '1', '2024')
    svc.receive_issue(s['id'], '3', '2024')
    check('все поступили -> pending пуст', svc.pending(s['id']) == [])


def find_stats_checks():
    print('-- find по заглавию + stats')
    svc = _svc(lambda: T0)
    s1 = svc.subscribe('Библиотека и общество')
    s2 = svc.subscribe('Вестник науки')
    s3 = svc.subscribe('Большая библиотека')
    svc.generate_issues(s1['id'], ['1', '2'], '2024')
    svc.generate_issues(s2['id'], ['1'], '2024')
    svc.receive_issue(s1['id'], '1', '2024')

    hits = svc.find('библиотек')           # кириллица, нижний регистр
    titles = sorted(h['title'] for h in hits)
    check('find подстрокой (кириллица, регистр) -> 2',
          titles == ['Библиотека и общество', 'Большая библиотека'])
    check('find без совпадений -> []', svc.find('xyz-нет-такого') == [])

    st = svc.stats()
    check('stats subscriptions=3', st['subscriptions'] == 3)
    check('stats issues=3', st['issues'] == 3)
    check('stats received=1', st['received'] == 1)
    check('stats pending=2', st['pending'] == 2)
    # глушим неиспользованную ссылку s3 явной проверкой
    check('третья подписка отдельной записью', s3['id'] != s1['id'])


def edge_checks():
    print('-- граничные случаи')
    svc = _svc(lambda: T0)
    s = svc.subscribe('Огонёк')
    svc.generate_issues(s['id'], ['1'], '2024')
    check('receive несуществующего номера -> None',
          svc.receive_issue(s['id'], '99', '2024') is None)
    check('receive в несуществующую подписку -> None',
          svc.receive_issue(999, '1', '2024') is None)


def main():
    subscribe_checks()
    generate_idempotent_checks()
    receive_pending_checks()
    find_stats_checks()
    edge_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
