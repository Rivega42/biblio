#!/usr/bin/env python3
"""Acquisition engine tests (gap E1, epic #188).

Scenario-based tests of the acquisition lifecycle (order → receipt → КСУ → ToCat)
+ the ККО formulas, per SPEC_business_acquisition.md and INTEGRATION_MAP cluster 1
(the ToCat edge). Everything runs against in-memory stores so the lifecycle is
deterministic and needs no DB server.

Standalone-runnable in the house style of ``test_circulation.py``::

    py -3.12 tests/test_acquisition.py   ->  ok ...  +  "N passed, M failed"  + exit code

Covered:
  * order lifecycle: create → partial receipt → full receipt → status walk;
    cancel rules (can't cancel after a receipt);
  * receipt → КСУ summary entry (88^E titles / 88^F copies / 88^G sum + act ref),
    inventory numbers (explicit + auto MIN+1), accumulation across receipts;
  * the ККО ratio incl. the §2.2 division-by-zero policy (all 4 cells),
    average_kko (None excluded), normalize-to-1, reorder_need (§2.6);
  * the ToCat edge: receipt creates a catalog record + a 910 exemplar with
    ^A=free; re-supply of an existing title adds a copy to the existing record
    (NOT a new record); standalone (no catalog) still works (ToCat no-op).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import acquisition as acq
from access.acquisition import (
    AcquisitionStore, AcquisitionEngine, AcquisitionError,
    kko, average_kko, reorder_need, title_key,
    ORDER_ORDERED, ORDER_PARTIAL, ORDER_RECEIVED, ORDER_CANCELLED,
    EXEMPLAR_FREE,
)

# The catalog handle is optional; import it for the ToCat tests. If it can't be
# imported (run in true isolation), the catalog tests degrade to a skip.
try:
    from access import catalog as _catalog
except Exception:  # pragma: no cover
    _catalog = None

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def fresh(catalog=None):
    """A fresh engine over an in-memory store (optionally with a catalog handle)."""
    return AcquisitionEngine(store=AcquisitionStore(':memory:'), catalog=catalog)


def fresh_catalog():
    """A fresh in-memory CatalogStore, or None if catalog isn't importable."""
    if _catalog is None:
        return None
    return _catalog.CatalogStore(':memory:')


# --------------------------------------------------------------------------- #
# 1. Order lifecycle (заказ).
# --------------------------------------------------------------------------- #
def order_lifecycle_checks():
    print('-- order lifecycle')
    eng = fresh()
    o = eng.create_order('Базы данных', author='Дейт К.', supplier='Лань',
                         copies=5, price=500.0, funding_source='бюджет')
    check('order created in ordered status', o['status'] == ORDER_ORDERED)
    check('order copies_ordered=5', o['copies_ordered'] == 5)
    check('order copies_received=0', o['copies_received'] == 0)

    # partial receipt → partially_received
    r1 = eng.receive(o['id'], '2026/1', copies=2, inv_numbers=['100', '101'])
    check('partial receipt -> partially_received',
          r1['order']['status'] == ORDER_PARTIAL)
    check('order tracks 2 received', r1['order']['copies_received'] == 2)

    # remaining receipt → received
    r2 = eng.receive(o['id'], '2026/1', copies=3, inv_numbers=['102', '103', '104'])
    check('full receipt -> received', r2['order']['status'] == ORDER_RECEIVED)
    check('order tracks 5 received', r2['order']['copies_received'] == 5)

    # over-receipt is rejected
    try:
        eng.receive(o['id'], '2026/1', copies=1, inv_numbers=['105'])
        check('over-receipt rejected', False)
    except AcquisitionError:
        check('over-receipt rejected', True)

    # unknown order
    try:
        eng.receive(9999, '2026/1', copies=1)
        check('receive on unknown order rejected', False)
    except AcquisitionError:
        check('receive on unknown order rejected', True)

    # validation on create
    try:
        eng.create_order('', copies=1)
        check('empty title rejected', False)
    except AcquisitionError:
        check('empty title rejected', True)
    try:
        eng.create_order('X', copies=0)
        check('zero copies rejected', False)
    except AcquisitionError:
        check('zero copies rejected', True)


def order_cancel_checks():
    print('-- order cancel rules')
    eng = fresh()
    o = eng.create_order('Сети', copies=3, price=100.0)
    c = eng.cancel_order(o['id'])
    check('fresh order cancels', c['status'] == ORDER_CANCELLED)
    # receiving against a cancelled order is rejected
    try:
        eng.receive(o['id'], '2026/2', copies=1, inv_numbers=['200'])
        check('receive on cancelled order rejected', False)
    except AcquisitionError:
        check('receive on cancelled order rejected', True)

    # an order with a receipt cannot be cancelled
    o2 = eng.create_order('ОС', copies=3, price=100.0)
    eng.receive(o2['id'], '2026/3', copies=1, inv_numbers=['300'])
    try:
        eng.cancel_order(o2['id'])
        check('cannot cancel after receipt', False)
    except AcquisitionError:
        check('cannot cancel after receipt', True)


# --------------------------------------------------------------------------- #
# 2. Receipt → КСУ (summary book of accounting).
# --------------------------------------------------------------------------- #
def ksu_checks():
    print('-- receipt -> КСУ entry')
    eng = fresh()
    o = eng.create_order('Алгоритмы', author='Кормен', copies=10, price=300.0)
    r = eng.receive(o['id'], '2026/15', copies=4, inv_numbers=['1', '2', '3', '4'],
                    act_ref='акт-77')
    ksu = r['ksu']
    check('КСУ titles (88^E) = 1', ksu['titles'] == 1)
    check('КСУ copies (88^F) = 4', ksu['copies'] == 4)
    check('КСУ sum (88^G) = 4*300 = 1200', ksu['total_sum'] == 1200.0)
    check('КСУ act ref recorded', ksu['act_ref'] == 'акт-77')
    check('receipt sum = 1200', r['sum'] == 1200.0)
    check('inventory numbers recorded', r['inventory'] == ['1', '2', '3', '4'])

    # a second order receiving into the SAME КСУ accumulates titles/copies/sum
    o2 = eng.create_order('Графы', copies=5, price=200.0)
    r2 = eng.receive(o2['id'], '2026/15', copies=5,
                     inv_numbers=['5', '6', '7', '8', '9'])
    ksu2 = r2['ksu']
    check('КСУ accumulates titles 1+1=2', ksu2['titles'] == 2)
    check('КСУ accumulates copies 4+5=9', ksu2['copies'] == 9)
    check('КСУ accumulates sum 1200+1000=2200', ksu2['total_sum'] == 2200.0)

    # auto inventory (MIN+1) when not supplied
    eng2 = fresh()
    o3 = eng2.create_order('Авто-инв', copies=2, price=50.0)
    r3 = eng2.receive(o3['id'], '2026/20', copies=2)
    check('auto inventory generates 2 numbers', len(r3['inventory']) == 2)
    check('auto inventory unique', len(set(r3['inventory'])) == 2)

    # explicit duplicate inventory rejected
    eng3 = fresh()
    o4 = eng3.create_order('Дубль-инв', copies=2, price=50.0)
    eng3.receive(o4['id'], '2026/21', copies=1, inv_numbers=['DUP'])
    o5 = eng3.create_order('Дубль-инв-2', copies=1, price=50.0)
    try:
        eng3.receive(o5['id'], '2026/21', copies=1, inv_numbers=['DUP'])
        check('duplicate inventory rejected', False)
    except AcquisitionError:
        check('duplicate inventory rejected', True)

    # inventory count must match copies
    eng4 = fresh()
    o6 = eng4.create_order('Несовпад', copies=3, price=50.0)
    try:
        eng4.receive(o6['id'], '2026/22', copies=3, inv_numbers=['a', 'b'])
        check('inventory count mismatch rejected', False)
    except AcquisitionError:
        check('inventory count mismatch rejected', True)


# --------------------------------------------------------------------------- #
# 3. ККО ratio + division-by-zero policy (SPEC §2.2, all 4 cells).
# --------------------------------------------------------------------------- #
def kko_checks():
    print('-- ККО ratio + div-by-zero policy')
    # cell 1: students>0, copies>0 -> copies/students
    check('ККО 40/100 = 0.4', kko(40, 100) == 0.4)
    check('ККО 10/100 = 0.1', kko(10, 100) == 0.1)
    # cell 2: students>0, copies=0 -> 0 (deficit, дозаказ candidate)
    check('ККО 0/100 = 0.0 (not provided)', kko(0, 100) == 0.0)
    # cell 3: students=0, copies>0 -> 1.0 (provided, no consumers)
    check('ККО copies>0,students=0 -> 1.0', kko(50, 0) == 1.0)
    # cell 4: students=0, copies=0 -> None (no data, NOT 0)
    check('ККО 0/0 -> None (no data)', kko(0, 0) is None)
    check('None is distinct from 0.0', kko(0, 0) is not kko(0, 100))

    # average: SPEC §6 П2 — (0.40 + 0.10) / 2 = 0.25
    avg = average_kko([kko(40, 100), kko(10, 100)])
    check('average ККО of П2 = 0.25', avg == 0.25)

    # None cells excluded from the average (archival orphan doesn't drag it down)
    avg2 = average_kko([kko(40, 100), kko(0, 0), kko(10, 100)])
    check('None excluded from average -> still 0.25', avg2 == 0.25)

    # all-None -> None (nothing to average)
    check('all-None average -> None', average_kko([None, None]) is None)

    # normalize to 1: a 2.0 over-provision capped to 1.0
    # values [2.0, 0.0] -> raw avg 1.0; normalized -> (1.0 + 0.0)/2 = 0.5
    check('normalize caps terms at 1',
          average_kko([2.0, 0.0], normalize=True) == 0.5)
    check('un-normalized avg of same = 1.0',
          average_kko([2.0, 0.0]) == 1.0)

    # reorder need (§2.6): П2 weak title — ceil(100*0.5) - 10 = 40
    check('reorder_need weak title = 40', reorder_need(100, 10, 0.5) == 40)
    # over-provided -> 0 (never negative)
    check('reorder_need over-provided = 0', reorder_need(100, 80, 0.5) == 0)
    # no students -> never a reorder candidate
    check('reorder_need with 0 students = 0', reorder_need(0, 0, 0.5) == 0)
    # ceil rounding: ceil(3*0.5)=ceil(1.5)=2, minus 0 copies = 2
    check('reorder_need ceil rounding = 2', reorder_need(3, 0, 0.5) == 2)


# --------------------------------------------------------------------------- #
# 4. ToCat edge (cluster 1: Комплектование → Каталог).
# --------------------------------------------------------------------------- #
def tocat_checks():
    print('-- ToCat edge (receipt -> catalog record + 910 exemplar)')
    cat = fresh_catalog()
    if cat is None:
        check('catalog module importable (skip ToCat)', False)
        return
    eng = fresh(catalog=cat)

    # receipt creates a catalog record + a 910 exemplar with ^A=free
    o = eng.create_order('Машинное обучение', author='Бишоп', copies=3,
                         price=400.0)
    r = eng.receive(o['id'], '2026/30', copies=1, inv_numbers=['INV-AAA'])
    check('ToCat created a catalog record', r['catalog_action'] == 'created')
    check('ToCat returned a catalog mfn', r['catalog_mfn'] is not None)
    check('receipt stores catalog_mfn',
          r['receipt']['catalog_mfn'] == r['catalog_mfn'])

    mfn = r['catalog_mfn']
    record = cat.get('IBIS', mfn)
    check('catalog record has title 200^a',
          _val(record, '200', 'a') == 'Машинное обучение')
    check('catalog record has author 700^a', _val(record, '700', 'a') == 'Бишоп')
    check('catalog record carries field-66 КСУ link',
          _val(record, '66', 'u') == '2026/30')

    # the 910 exemplar: ^b inventory, ^A free, ^U КСУ
    ex = cat.find_exemplar('IBIS', 'INV-AAA')
    check('910 exemplar findable by inv#', ex is not None)
    check('exemplar ^A is free (lendable now)',
          cat.exemplar_status('IBIS', 'INV-AAA') == EXEMPLAR_FREE)
    check('exemplar is_available true', cat.is_available('IBIS', 'INV-AAA') is True)
    inst = ex[2] if ex else {}
    check('exemplar carries КСУ back-link ^U',
          str(inst.get('u') or '') == '2026/30')

    # re-supply of the SAME title adds a copy to the EXISTING record (not a dup)
    count_before = cat.count('IBIS')
    o2 = eng.create_order('Машинное обучение', author='Бишоп', copies=2,
                          price=400.0)
    r2 = eng.receive(o2['id'], '2026/31', copies=1, inv_numbers=['INV-BBB'])
    check('re-supply UPDATES existing record', r2['catalog_action'] == 'updated')
    check('re-supply lands on SAME mfn', r2['catalog_mfn'] == mfn)
    check('catalog record count unchanged (no duplicate)',
          cat.count('IBIS') == count_before)

    record2 = cat.get('IBIS', mfn)
    ex_list = record2['910'] if isinstance(record2['910'], list) else [record2['910']]
    check('existing record now has 2 exemplars', len(ex_list) == 2)
    check('new copy findable by its inv#',
          cat.find_exemplar('IBIS', 'INV-BBB') is not None)
    check('new copy is free', cat.is_available('IBIS', 'INV-BBB') is True)
    check('both КСУ links present on record',
          {i.get('u') for i in _instances(record2, '66')} == {'2026/30', '2026/31'})

    # a DIFFERENT title creates a NEW record
    o3 = eng.create_order('Глубокое обучение', author='Гудфеллоу', copies=1,
                          price=600.0)
    r3 = eng.receive(o3['id'], '2026/32', copies=1, inv_numbers=['INV-CCC'])
    check('different title -> new record', r3['catalog_action'] == 'created')
    check('different title -> different mfn', r3['catalog_mfn'] != mfn)


def tocat_standalone_checks():
    print('-- ToCat graceful no-op when no catalog wired')
    eng = fresh(catalog=None)   # standalone
    o = eng.create_order('Без каталога', copies=2, price=100.0)
    r = eng.receive(o['id'], '2026/40', copies=2, inv_numbers=['S1', 'S2'])
    # order / receipt / КСУ all work; ToCat is a no-op
    check('standalone receipt succeeds', r['receipt'] is not None)
    check('standalone КСУ written', r['ksu']['copies'] == 2)
    check('standalone catalog_mfn is None', r['catalog_mfn'] is None)
    check('standalone catalog_action is None', r['catalog_action'] is None)
    check('standalone order advanced to received',
          r['order']['status'] == ORDER_RECEIVED)


def title_key_checks():
    print('-- title key (new-vs-existing resolver)')
    check('title key casefolds + trims',
          title_key('  Базы Данных ', 'Дейт') == title_key('базы данных', 'дейт'))
    check('different author -> different key',
          title_key('X', 'A') != title_key('X', 'B'))
    check('missing author normalized to empty',
          title_key('X') == ('x', ''))


# --------------------------------------------------------------------------- #
# Small local accessors for the test assertions.
# --------------------------------------------------------------------------- #
def _instances(record, field):
    raw = record.get(field)
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _val(record, field, subfield):
    for inst in _instances(record, field):
        if isinstance(inst, dict) and inst.get(subfield):
            return inst[subfield]
    return ''


def main():
    order_lifecycle_checks()
    order_cancel_checks()
    ksu_checks()
    kko_checks()
    title_key_checks()
    tocat_checks()
    tocat_standalone_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
