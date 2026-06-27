#!/usr/bin/env python3
"""Тесты справочника поставщиков + счетов-актов (контур Комплектование).

Покрыто:
  * supplier: add/get/list (включая active_only)/find/deactivate; кириллица в
    имени (фильтр в Python, т.к. SQLite LIKE регистронезависим лишь для ASCII);
  * invoice: add_invoice (+ ошибка на несуществующего поставщика),
    set_invoice_status (+ ошибка на неизвестный статус/счёт), фильтры invoices
    (по поставщику / по статусу / комбинированный);
  * total_by_supplier (раскладка по статусам + total/payable);
  * stats (счётчики поставщиков/счетов + Σ сумм).

Запуск: py -3.12 tests/test_suppliers.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.suppliers import (
    SupplierStore, SupplierService, SupplierError, INVOICE_STATUSES,
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


def _svc():
    """Сервис на in-memory сторе с детерминированным временем."""
    return SupplierService(SupplierStore(':memory:'), now=lambda: T0)


def supplier_crud_checks():
    print('-- supplier: add/get/list/find/deactivate')
    svc = _svc()
    s = svc.add_supplier('ООО Лань', inn='7801234567', contact='Иванов И.И.',
                         email='sales@lan.ru', phone='+7-812-000', address='СПб')
    check('add_supplier вернул строку с id', bool(s) and s['id'] >= 1)
    check('поля сохранены', s['name'] == 'ООО Лань' and s['inn'] == '7801234567'
          and s['contact'] == 'Иванов И.И.')
    check('новый поставщик активен', s['is_active'] == 1)
    check('get по id', svc.get(s['id'])['name'] == 'ООО Лань')
    check('get несуществующего -> None', svc.get(999) is None)

    bad = False
    try:
        svc.add_supplier('')
    except SupplierError:
        bad = True
    check('пустое имя -> SupplierError', bad)

    s2 = svc.add_supplier('Книжный Дом', inn='5009999999')
    check('list -> 2 поставщика', len(svc.list()) == 2)

    # deactivate + active_only
    svc.deactivate(s2['id'])
    check('deactivate -> is_active=0', svc.get(s2['id'])['is_active'] == 0)
    check('list(active_only) -> только активный',
          [x['id'] for x in svc.list(active_only=True)] == [s['id']])
    check('list() по-прежнему оба', len(svc.list()) == 2)

    bad = False
    try:
        svc.deactivate(999)
    except SupplierError:
        bad = True
    check('deactivate несуществующего -> SupplierError', bad)


def supplier_find_checks():
    print('-- supplier: find (подстрока, кириллица, регистронезависимо)')
    svc = _svc()
    svc.add_supplier('ООО Лань', inn='7801234567', contact='Иванов И.И.')
    svc.add_supplier('Книжный Дом', inn='5009999999', email='info@kdom.ru')
    svc.add_supplier('Эксмо', inn='7700000001')

    check('find по подстроке имени', [s['name'] for s in svc.find('Лань')]
          == ['ООО Лань'])
    check('find кириллица в другом регистре (лань)',
          [s['name'] for s in svc.find('лань')] == ['ООО Лань'])
    check('find по ИНН', [s['name'] for s in svc.find('5009999999')]
          == ['Книжный Дом'])
    check('find по контакту', [s['name'] for s in svc.find('Иванов')]
          == ['ООО Лань'])
    check('find по email', [s['name'] for s in svc.find('kdom')]
          == ['Книжный Дом'])
    check('find без совпадений -> []', svc.find('неттакого') == [])
    check('find пустой запрос -> все', len(svc.find('')) == 3)


def invoice_checks():
    print('-- invoice: add (+ ошибка на неизвестного поставщика), статусы, фильтры')
    svc = _svc()
    s = svc.add_supplier('ООО Лань')
    s2 = svc.add_supplier('Эксмо')

    inv = svc.add_invoice(s['id'], number='СЧ-1', amount=1500.0, date='2026-01-10',
                          ksu_no='2026/1', order_ref=42)
    check('add_invoice вернул строку', bool(inv) and inv['supplier_id'] == s['id'])
    check('сумма/валюта по умолчанию', inv['amount'] == 1500.0
          and inv['currency'] == 'RUB')
    check('статус по умолчанию draft', inv['status'] == 'draft')
    check('мягкие ссылки на КСУ/заказ (текст)',
          inv['ksu_no'] == '2026/1' and inv['order_ref'] == '42')

    bad = False
    try:
        svc.add_invoice(999, number='X', amount=10)
    except SupplierError:
        bad = True
    check('счёт на несуществующего поставщика -> SupplierError', bad)

    bad = False
    try:
        svc.add_invoice(s['id'], number='X', amount=10, status='nonsense')
    except SupplierError:
        bad = True
    check('неизвестный статус при создании -> SupplierError', bad)

    # set_invoice_status
    upd = svc.set_invoice_status(inv['id'], 'received')
    check('set_invoice_status -> received', upd['status'] == 'received')

    bad = False
    try:
        svc.set_invoice_status(inv['id'], 'nonsense')
    except SupplierError:
        bad = True
    check('set_invoice_status неизвестный статус -> SupplierError', bad)

    bad = False
    try:
        svc.set_invoice_status(999, 'paid')
    except SupplierError:
        bad = True
    check('set_invoice_status неизвестный счёт -> SupplierError', bad)

    # ещё счета для фильтров
    inv2 = svc.add_invoice(s['id'], number='СЧ-2', amount=500.0)
    svc.set_invoice_status(inv2['id'], 'paid')
    svc.add_invoice(s2['id'], number='Э-1', amount=2000.0)   # draft, другой поставщик

    check('invoices() -> все 3', len(svc.invoices()) == 3)
    check('invoices(supplier_id) -> 2 у Лань',
          len(svc.invoices(supplier_id=s['id'])) == 2)
    check('invoices(status=draft) -> 1',
          [i['number'] for i in svc.invoices(status='draft')] == ['Э-1'])
    check('invoices(supplier+status) -> received СЧ-1',
          [i['number'] for i in svc.invoices(supplier_id=s['id'],
                                             status='received')] == ['СЧ-1'])


def total_and_stats_checks():
    print('-- total_by_supplier + stats')
    svc = _svc()
    s = svc.add_supplier('ООО Лань')
    s2 = svc.add_supplier('Эксмо')
    svc.deactivate(s2['id'])

    i_recv = svc.add_invoice(s['id'], number='R', amount=1500.0)
    svc.set_invoice_status(i_recv['id'], 'received')
    i_paid = svc.add_invoice(s['id'], number='P', amount=500.0)
    svc.set_invoice_status(i_paid['id'], 'paid')
    svc.add_invoice(s['id'], number='D', amount=300.0)             # draft
    svc.add_invoice(s2['id'], number='X', amount=999.0)           # другой поставщик

    tot = svc.total_by_supplier(s['id'])
    check('total_by_supplier: total = 2300', tot['total'] == 2300.0)
    check('total_by_supplier: received = 1500', tot['received'] == 1500.0)
    check('total_by_supplier: paid = 500', tot['paid'] == 500.0)
    check('total_by_supplier: draft = 300', tot['draft'] == 300.0)
    check('total_by_supplier: cancelled = 0', tot['cancelled'] == 0.0)
    check('total_by_supplier: payable = received (1500)', tot['payable'] == 1500.0)
    check('total_by_supplier чужого счёта не учитывает',
          svc.total_by_supplier(s2['id'])['total'] == 999.0)

    st = svc.stats()
    check('stats: 2 поставщика', st['suppliers'] == 2)
    check('stats: 1 активный', st['active_suppliers'] == 1)
    check('stats: 4 счёта', st['invoices'] == 4)
    check('stats: Σ всех сумм = 3299', st['total_amount'] == 3299.0)
    check('stats: разбивка по статусам присутствует',
          st['invoices_by_status'].get('received') == 1
          and st['invoices_by_status'].get('paid') == 1)
    check('INVOICE_STATUSES — 4 статуса',
          set(INVOICE_STATUSES) == {'draft', 'received', 'paid', 'cancelled'})


def main():
    supplier_crud_checks()
    supplier_find_checks()
    invoice_checks()
    total_and_stats_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
