#!/usr/bin/env python3
"""Inventory domain tests (узел #272 / Фаза 2, BIBLIO_DEVICE_INTEGRATION_DESIGN.md §5.2).

Сценарные тесты нативного домена `inventory` (фондовая инвентаризация ручным
RFID-ТСД) над in-memory стором (детерминизм, без DB-сервера). Дом. стиль
``test_devices.py``::

    py -3.12 tests/test_inventory.py  ->  ok ... + "N passed, M failed" + exit code

Покрыто:
  * жизненный цикл: open → scan (идемпотентно: тот же item дважды = 1 строка) → close;
  * scan/close в закрытую/несуществующую сессию → InventoryError;
  * report: present/missing/foreign/unknown против FakeCatalog (BookInvStates);
  * report без seam (catalog is None) — штатная деградация;
  * list_sessions (по db/status), get (со сканами), scans.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.inventory import (
    InventoryStore, InventoryService, InventoryError,
    STATUS_OPEN, STATUS_CLOSED,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def expect_raises(name, fn, exc=InventoryError):
    try:
        fn()
        check(name, False)
    except exc:
        check(name, True)
    except Exception:
        check(name, False)


class FakeCatalog:
    """Duck-typed seam каталога для сверки.

    expected_items(db, location) -> что числится в этом месте;
    item_known(db, item_code)    -> знает ли каталог такой экземпляр вообще.
    """

    def __init__(self, expected_by_loc, known):
        # expected_by_loc: {(db, location): [item_code, ...]}
        self._expected = expected_by_loc
        self._known = set(known)

    def expected_items(self, db, location):
        return list(self._expected.get((db, location), []))

    def item_known(self, db, item_code):
        return item_code in self._known


def make_service(now_ref, catalog=None):
    return InventoryService(InventoryStore(':memory:'), catalog=catalog,
                            now=lambda: now_ref[0])


def test_lifecycle_and_idempotent_scan():
    now = [1000.0]
    svc = make_service(now)
    sess = svc.open('IBIS', 'SHELF-A1', operator='op1')
    check('open returns row', sess and sess['location'] == 'SHELF-A1')
    check('open status open', sess['status'] == STATUS_OPEN)
    check('open sets started ts', sess['started'] == 1000.0 and sess['finished'] is None)
    check('open sets operator', sess['operator'] == 'op1')
    sid = sess['id']
    # идемпотентность: один и тот же item дважды = 1 строка
    svc.scan(sid, 'BK-1', rfid='EPC-AAA')
    svc.scan(sid, 'BK-1', rfid='EPC-AAA')  # повтор
    svc.scan(sid, 'BK-2', rfid='EPC-BBB')
    rows = svc.scans(sid)
    check('idempotent scan: 2 rows', len(rows) == 2)
    check('scan codes recorded', {r['item_code'] for r in rows} == {'BK-1', 'BK-2'})
    check('scan keeps first rfid', rows[0]['rfid'] == 'EPC-AAA')
    check('scan ts from now seam', rows[0]['ts'] == 1000.0)
    # close
    now[0] = 1234.0
    closed = svc.close(sid)
    check('close sets status closed', closed['status'] == STATUS_CLOSED)
    check('close sets finished ts', closed['finished'] == 1234.0)


def test_scan_close_errors():
    now = [1.0]
    svc = make_service(now)
    sess = svc.open('IBIS', 'SHELF-B', operator='op')
    sid = sess['id']
    svc.close(sid)
    expect_raises('scan on closed raises', lambda: svc.scan(sid, 'BK-9'))
    expect_raises('close on closed raises', lambda: svc.close(sid))
    expect_raises('scan on missing raises', lambda: svc.scan(99999, 'BK-9'))
    expect_raises('close on missing raises', lambda: svc.close(99999))


def test_report_with_catalog():
    now = [10.0]
    # числится на SHELF-A1: BK-1, BK-2, BK-3; известны каталогу: BK-1..BK-4
    cat = FakeCatalog(
        expected_by_loc={('IBIS', 'SHELF-A1'): ['BK-1', 'BK-2', 'BK-3']},
        known=['BK-1', 'BK-2', 'BK-3', 'BK-4'])
    svc = make_service(now, catalog=cat)
    sess = svc.open('IBIS', 'SHELF-A1', operator='op')
    sid = sess['id']
    # сканируем: BK-1 (present), BK-2 (present), BK-4 (foreign: числится не здесь),
    # BK-9 (unknown: каталог не знает; тоже foreign). BK-3 НЕ сканирован → missing.
    svc.scan(sid, 'BK-1')
    svc.scan(sid, 'BK-2')
    svc.scan(sid, 'BK-4')
    svc.scan(sid, 'BK-9')
    rep = svc.report(sid)
    check('report session_id', rep['session_id'] == sid)
    check('report scanned count', len(rep['scanned']) == 4)
    check('report expected_count', rep['expected_count'] == 3)
    check('report present', sorted(rep['present']) == ['BK-1', 'BK-2'])
    check('report missing', rep['missing'] == ['BK-3'])
    check('report foreign', sorted(rep['foreign']) == ['BK-4', 'BK-9'])
    check('report unknown', rep['unknown'] == ['BK-9'])
    # report работает и на открытой, и на закрытой сессии
    svc.close(sid)
    rep2 = svc.report(sid)
    check('report stable after close', rep2['present'] == rep['present'])


def test_report_without_catalog():
    now = [5.0]
    svc = make_service(now)  # catalog=None
    sess = svc.open('IBIS', 'SHELF-C', operator='op')
    sid = sess['id']
    svc.scan(sid, 'BK-1')
    svc.scan(sid, 'BK-2')
    rep = svc.report(sid)
    check('no-catalog scanned passthrough', sorted(rep['scanned']) == ['BK-1', 'BK-2'])
    check('no-catalog expected_count 0', rep['expected_count'] == 0)
    check('no-catalog present empty', rep['present'] == [])
    check('no-catalog missing empty', rep['missing'] == [])
    check('no-catalog foreign empty', rep['foreign'] == [])
    check('no-catalog unknown empty', rep['unknown'] == [])
    expect_raises('report on missing raises', lambda: svc.report(99999))


def test_list_get_scans():
    now = [1.0]
    svc = make_service(now)
    s1 = svc.open('IBIS', 'L1', operator='op')
    s2 = svc.open('IBIS', 'L2', operator='op')
    s3 = svc.open('OTHER', 'L3', operator='op')
    svc.close(s2['id'])
    check('list all', len(svc.list_sessions()) == 3)
    check('list by db', len(svc.list_sessions(db='IBIS')) == 2)
    check('list by status open', len(svc.list_sessions(status=STATUS_OPEN)) == 2)
    check('list by status closed', len(svc.list_sessions(status=STATUS_CLOSED)) == 1)
    check('list by db+status', len(svc.list_sessions(db='OTHER', status=STATUS_OPEN)) == 1)
    svc.scan(s1['id'], 'BK-1')
    got = svc.get(s1['id'])
    check('get includes scans', 'scans' in got and len(got['scans']) == 1)
    check('get missing returns None', svc.get(99999) is None)
    check('scans accessor', len(svc.scans(s1['id'])) == 1)


def main():
    for t in (test_lifecycle_and_idempotent_scan, test_scan_close_errors,
              test_report_with_catalog, test_report_without_catalog,
              test_list_get_scans):
        print('==', t.__name__)
        t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
