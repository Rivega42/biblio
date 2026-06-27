#!/usr/bin/env python3
"""Тесты ребра 3.1 — own-store реестр читателя RDR (профиль вместо строки-id).

Покрыто:
  * `ReaderRegistry.register` + `resolve` -> полная запись-профиль (билет, ФИО,
    категория, статус, контакты);
  * идемпотентность `ReaderStore.upsert` (повтор по id обновляет, не дублирует,
    сохраняет created_at);
  * `block` / `unblock` -> смена status active<->blocked;
  * `field30` -> структура подполей 30 RDR (^A билет, ^B категория, ^C ФИО,
    ^S статус);
  * `get`/`resolve` несуществующего читателя -> None (best-effort);
  * изоляция профилей по id (один читатель не влияет на другого).

Запуск: py -3.12 tests/test_reader_registry.py  ; регистрируется в
tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.reader_registry import (
    ReaderRegistry, ReaderStore, STATUS_ACTIVE, STATUS_BLOCKED,
)

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


def _reg(now=None):
    return ReaderRegistry(ReaderStore(':memory:'), now=now)


def register_resolve_checks():
    print('-- register + resolve: профиль, а не строка-id')
    reg = _reg()
    p = reg.register('RDR-1', category='В01', full_name='Иванов Иван',
                     email='i@lib.ru', phone='+7000', faculty='ФИЯ')
    check('register вернул запись', p is not None and p['id'] == 'RDR-1')
    r = reg.resolve('RDR-1')
    check('resolve -> dict-запись', isinstance(r, dict))
    check('resolve: категория', r['category'] == 'В01')
    check('resolve: ФИО', r['full_name'] == 'Иванов Иван')
    check('resolve: контакты', r['email'] == 'i@lib.ru' and r['phone'] == '+7000')
    check('resolve: факультет', r['faculty'] == 'ФИЯ')
    check('status по умолчанию active', r['status'] == STATUS_ACTIVE)
    check('ticket по умолчанию == id', r['ticket'] == 'RDR-1')
    check('get == resolve', reg.get('RDR-1')['id'] == 'RDR-1')
    check('resolve по билету (ticket)', reg.resolve('RDR-1')['id'] == 'RDR-1')


def upsert_idempotent_checks():
    print('-- upsert идемпотентен: повтор обновляет, не дублирует')
    store = ReaderStore(':memory:')
    a = store.upsert('RDR-9', category='В01', full_name='Старое',
                     created_at=T0, updated_at=T0)
    b = store.upsert('RDR-9', full_name='Новое ФИО', updated_at=T0 + 100)
    check('одна запись (не дубль)', len(store.list()) == 1)
    check('ФИО обновилось', b['full_name'] == 'Новое ФИО')
    check('категория сохранилась', b['category'] == 'В01')
    check('created_at сохранён', b['created_at'] == T0)
    check('updated_at сдвинулся', b['updated_at'] == T0 + 100 and a is not None)
    check('find_by_ticket находит', store.find_by_ticket('RDR-9')['id'] == 'RDR-9')


def block_unblock_checks():
    print('-- block / unblock: смена статуса')
    reg = _reg()
    reg.register('RDR-2', category='В02', full_name='Петров')
    p = reg.block('RDR-2')
    check('block -> blocked', p['status'] == STATUS_BLOCKED)
    check('resolve видит blocked', reg.resolve('RDR-2')['status'] == STATUS_BLOCKED)
    p2 = reg.unblock('RDR-2')
    check('unblock -> active', p2['status'] == STATUS_ACTIVE)


def field30_checks():
    print('-- field30: структура подполей 30 RDR')
    reg = _reg()
    reg.register('RDR-3', ticket='BC-3', category='Д01', full_name='Сидоров С.С.')
    f = reg.field30('RDR-3')
    check('field30 -> dict', isinstance(f, dict))
    check('^A билет', f['A'] == 'BC-3')
    check('^B категория', f['B'] == 'Д01')
    check('^C ФИО', f['C'] == 'Сидоров С.С.')
    check('^S статус', f['S'] == STATUS_ACTIVE)
    reg.block('RDR-3')
    check('^S отражает блокировку', reg.field30('RDR-3')['S'] == STATUS_BLOCKED)
    check('field30 несуществующего -> None', reg.field30('NOPE') is None)


def missing_checks():
    print('-- несуществующий читатель -> None (best-effort)')
    reg = _reg()
    check('get отсутствующего -> None', reg.get('GHOST') is None)
    check('resolve отсутствующего -> None', reg.resolve('GHOST') is None)
    check('block отсутствующего не бросает',
          reg.block('GHOST') is None or reg.block('GHOST') == {})


def isolation_checks():
    print('-- изоляция профилей по id')
    reg = _reg()
    reg.register('RDR-A', category='В01', full_name='A')
    reg.register('RDR-B', category='В05', full_name='B')
    reg.block('RDR-A')
    check('A заблокирован', reg.resolve('RDR-A')['status'] == STATUS_BLOCKED)
    check('B не затронут', reg.resolve('RDR-B')['status'] == STATUS_ACTIVE)
    check('B сохранил категорию', reg.resolve('RDR-B')['category'] == 'В05')
    check('list по категории фильтрует',
          [x['id'] for x in reg.list(category='В05')] == ['RDR-B'])
    check('list всех -> 2', len(reg.list()) == 2)


def main():
    register_resolve_checks()
    upsert_idempotent_checks()
    block_unblock_checks()
    field30_checks()
    missing_checks()
    isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
