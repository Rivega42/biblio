#!/usr/bin/env python3
"""Тесты батч-оформления корзины читателя как заказов-броней (ребро 10.2).

`HoldService.place_many`: корзина портала ``[{db,mfn},…]`` персистит каждую
позицию как бронь (own-store аналог RQST — «один движок, два клиента»).
Покрыто: пустая корзина; 3 позиции → 3 брони; идемпотентность поэлементно
(повтор не задваивает); кривые позиции (битый mfn / нет db) помечаются `error`
и НЕ роняют батч; подстановка `default_db`.

Запуск (домашний стиль): py -3.12 tests/test_holds_batch.py
Регистрируется в агрегаторе tests/test_access.py (module_checks).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.store import AccessStore
from access.holds import HoldService

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _svc():
    return HoldService(AccessStore(':memory:'))


def empty_checks():
    print('-- place_many: пустая корзина')
    svc = _svc()
    r = svc.place_many('T1', [])
    check('пусто: placed 0', r['placed'] == 0)
    check('пусто: failed 0', r['failed'] == 0)
    check('пусто: items []', r['items'] == [])
    check('пусто: None-корзина не падает', svc.place_many('T1', None)['placed'] == 0)


def basic_checks():
    print('-- place_many: корзина из 3 позиций персистится как брони')
    svc = _svc()
    r = svc.place_many('T1', [{'db': 'IBIS', 'mfn': 10},
                              {'db': 'IBIS', 'mfn': 11},
                              {'db': 'IBIS', 'mfn': 12}])
    check('3 оформлено', r['placed'] == 3)
    check('0 ошибок', r['failed'] == 0)
    check('каждая позиция с holdId', all('holdId' in it for it in r['items']))
    check('list_for видит 3 брони', len(svc.list_for('T1')) == 3)
    check('первый holder каждой позиции → ready (без каталога)', r['ready'] == 3)


def idempotent_checks():
    print('-- place_many: идемпотентно поэлементно (повтор не задваивает)')
    svc = _svc()
    a = svc.place_many('T1', [{'db': 'IBIS', 'mfn': 10}])
    b = svc.place_many('T1', [{'db': 'IBIS', 'mfn': 10}, {'db': 'IBIS', 'mfn': 20}])
    check('повтор позиции 10 → тот же holdId',
          a['items'][0]['holdId'] == b['items'][0]['holdId'])
    check('итого 2 уникальные брони', len(svc.list_for('T1')) == 2)


def resilience_checks():
    print('-- place_many: кривые позиции → error, батч не падает')
    svc = _svc()
    r = svc.place_many('T1', [{'db': 'IBIS', 'mfn': 10},
                              {'db': 'IBIS', 'mfn': 'x'},   # bad_mfn
                              {'mfn': 12}])                 # no_db (default не задан)
    check('1 оформлено', r['placed'] == 1)
    check('2 ошибки', r['failed'] == 2)
    errs = {it.get('error') for it in r['items'] if 'error' in it}
    check('ошибки: bad_mfn + no_db', errs == {'bad_mfn', 'no_db'})
    check('валидная позиция всё равно прошла', len(svc.list_for('T1')) == 1)


def default_db_checks():
    print('-- place_many: default_db подставляется в позицию без db')
    svc = _svc()
    r = svc.place_many('T1', [{'mfn': 10}], default_db='IBIS')
    check('позиция без db взяла default_db',
          r['placed'] == 1 and r['items'][0]['db'] == 'IBIS')


def main():
    empty_checks()
    basic_checks()
    idempotent_checks()
    resilience_checks()
    default_db_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
