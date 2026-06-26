#!/usr/bin/env python3
"""Locker orders tests (узел #272, SAFEKEEPER_HOLDS_MAPPING.md 3/3).

Сценарные тесты физического слоя locker-заказа (#222 + ячейки) над in-memory
стором + фейковыми сидами circulation/devices. Дом. стиль ``test_devices.py``::

    py -3.12 tests/test_locker.py  -> ok ... + "N passed, M failed" + код

Покрыто:
  * жизненный цикл: create(1)→add_book(2)→staff(3, ячейка занята)→issue(4, ячейка
    свободна) + выдача через circulation-сид (processed); cancel освобождает;
  * ошибка АБИС при выдаче → ISSUED_ERROR(6) + abis_error;
  * ячейки: busy_cells / cells_state (битмаска) / free_cells / allocate;
    занять занятую → LockerError;
  * standalone без circulation-сида → issue без loan (state 4);
  * мастер-ключ: service_open валиден/невалиден (через devices-сид) + событие;
  * переходы из неверных состояний → LockerError.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.locker import (
    LockerStore, LockerService, LockerError,
    CREATED, PREPARED, STAFFED, ISSUED, CANCELLED, ISSUED_ERROR,
)
from access.devices import DeviceService, DeviceStore, KIND_SAFEKEEPER

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def expect_raises(name, fn):
    try:
        fn(); check(name, False)
    except LockerError:
        check(name, True)
    except Exception:
        check(name, False)


class FakeCirc:
    """circulation-сид: checkout(ticket, code) -> bool; denies set отказывают."""
    def __init__(self, deny=()):
        self.deny = set(deny)
        self.calls = []
    def checkout(self, ticket, code):
        self.calls.append((ticket, code))
        return code not in self.deny


def svc(circ=None, devices=None):
    return LockerService(LockerStore(':memory:'), circulation=circ, devices=devices)


def test_lifecycle_happy():
    circ = FakeCirc()
    s = svc(circ=circ)
    o = s.create('T-1', safekeeper_id=10, reader_fio='Иванов')
    check('create state CREATED', o['state'] == CREATED)
    o = s.add_book(o['id'], 'BK-1', 'RF-1')
    check('add_book -> PREPARED', o['state'] == PREPARED)
    s.add_book(o['id'], 'BK-2')
    check('two items', len(s.store.list_items(o['id'])) == 2)
    o = s.staff(o['id'], cell_no=3, staffed_by='lib1')
    check('staff -> STAFFED', o['state'] == STAFFED and o['cell_no'] == 3)
    check('cell 3 busy', 3 in s.busy_cells(10))
    o2 = s.issue(o['id'])
    check('issue -> ISSUED', o2['state'] == ISSUED and o2['abis_error'] is None)
    check('circ called per book', len(circ.calls) == 2)
    check('items processed', all(i['processed'] == 1 for i in s.store.list_items(o['id'])))
    check('cell freed after issue', 3 not in s.busy_cells(10))


def test_issue_abis_error():
    circ = FakeCirc(deny=['BK-BAD'])
    s = svc(circ=circ)
    o = s.create('T-2', 10)
    s.add_book(o['id'], 'BK-OK')
    s.add_book(o['id'], 'BK-BAD')
    o = s.staff(o['id'], cell_no=1)
    o = s.issue(o['id'])
    check('issue error -> ISSUED_ERROR', o['state'] == ISSUED_ERROR)
    check('abis_error set', bool(o['abis_error']))
    check('cell freed on error', 1 not in s.busy_cells(10))


def test_cells():
    s = svc()
    for t, cell in (('A', 1), ('B', 2), ('C', 4)):
        o = s.create('R-' + t, 10)
        s.add_book(o['id'], 'b')
        s.staff(o['id'], cell_no=cell)
    check('busy cells {1,2,4}', s.busy_cells(10) == {1, 2, 4})
    # битмаска: биты 0,1,3 -> 1+2+8 = 11
    check('cells_state bitmask', s.cells_state(10) == 0b1011)
    check('free cells of 5', s.free_cells(10, 5) == [3, 5])
    check('allocate first free', s.allocate_cell(10, 5) == 3)
    # занять занятую
    o = s.create('R-X', 10)
    s.add_book(o['id'], 'b')
    expect_raises('staff busy cell raises', lambda: s.staff(o['id'], cell_no=1))
    # нет свободных
    s2 = svc()
    o = s2.create('R-Y', 20); s2.add_book(o['id'], 'b'); s2.staff(o['id'], 1)
    expect_raises('allocate no free raises', lambda: s2.allocate_cell(20, 1))


def test_cancel_and_bad_transitions():
    s = svc()
    o = s.create('T-3', 10)
    s.add_book(o['id'], 'b')
    s.staff(o['id'], cell_no=2)
    check('cell 2 busy before cancel', 2 in s.busy_cells(10))
    c = s.cancel(o['id'])
    check('cancel -> CANCELLED', c['state'] == CANCELLED)
    check('cell freed after cancel', 2 not in s.busy_cells(10))
    expect_raises('issue from cancelled raises', lambda: s.issue(o['id']))
    # staff requires PREPARED
    o2 = s.create('T-4', 10)
    expect_raises('staff before prepared raises', lambda: s.staff(o2['id'], 5))
    # add_book to issued
    o3 = s.create('T-5', 10); s.add_book(o3['id'], 'b'); s.staff(o3['id'], 6); s.issue(o3['id'])
    expect_raises('add_book to issued raises', lambda: s.add_book(o3['id'], 'x'))


def test_standalone_no_circ():
    s = svc()  # circulation seam None
    o = s.create('T-6', 10)
    s.add_book(o['id'], 'b')
    s.staff(o['id'], 1)
    o = s.issue(o['id'])
    check('standalone issue -> ISSUED (no loan)', o['state'] == ISSUED and o['abis_error'] is None)


def test_master_service_open():
    dev = DeviceService(DeviceStore(':memory:'))
    sk = dev.register('sk-guid', KIND_SAFEKEEPER, name='SK')
    dev.master_modify('MK-1', fio='Петров', device_id=sk['id'])
    s = svc(devices=dev)
    check('service_open valid master', s.service_open(sk['id'], 2, 'MK-1') is True)
    check('service_open logged event', any(e['event_name'] == 'service_open' for e in dev.events(sk['id'])))
    expect_raises('service_open invalid master raises',
                  lambda: s.service_open(sk['id'], 2, 'MK-NOPE'))


def test_views():
    dev = DeviceService(DeviceStore(':memory:'))
    s = svc(devices=dev)
    o = s.create('T-7', 10, reader_fio='Сидоров')
    s.add_book(o['id'], 'b1'); s.add_book(o['id'], 'b2')
    s.staff(o['id'], cell_no=4, staffed_by='lib2')
    g = s.get(o['id'])
    check('get has items', len(g['items']) == 2)
    check('cell_shifted computed', g['cell_shifted'] == 4)
    check('list_for_reader', len(s.list_for_reader('T-7')) == 1)
    check('list_for_safekeeper', len(s.list_for_safekeeper(10)) == 1)
    # событие staff проброшено в devices (по safekeeper id = 10, не зарегистрирован — guard)
    check('event guard ok (no crash)', True)


def main():
    for t in (test_lifecycle_happy, test_issue_abis_error, test_cells,
              test_cancel_and_bad_transitions, test_standalone_no_circ,
              test_master_service_open, test_views):
        print('==', t.__name__)
        t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
