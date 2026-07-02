#!/usr/bin/env python3
"""Devices domain tests (узел #272, DEVICES_NATIVE_ARCHITECTURE.md).

Сценарные тесты нативного домена `devices` над in-memory стором (детерминизм, без
DB-сервера). Дом. стиль ``test_acquisition.py``::

    py -3.12 tests/test_devices.py   ->  ok ... + "N passed, M failed" + exit code

Покрыто:
  * реестр: register (новый/идемпотентный по guid) → modify → list/get → remove;
  * heartbeat: запись health + derive_state (все 4 ветки) + online/last_seen;
  * события: record_event, gate_alarm (gate_event + device_event), visitor,
    shelf_sync (replace), acs_pass;
  * мастер-ключи: master_modify / masters / is_master_valid (скоуп по камере);
  * info: online-флаг + state_name из последнего health;
  * license-слайс.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.devices import (
    DeviceStore, DeviceService, DeviceError,
    KIND_DESKTOP, KIND_SAFEKEEPER, KIND_GATE, KIND_SELF_SERVICE_CABINET,
    STATE_UNKNOWN, STATE_OK, STATE_DIAG, STATE_UNCONFIGURED, STATE_NAMES,
    DIR_OUT, ONLINE_TTL_SEC,
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


def expect_raises(name, fn, exc=DeviceError):
    try:
        fn()
        check(name, False)
    except exc:
        check(name, True)
    except Exception:
        check(name, False)


def make_service(now_ref):
    return DeviceService(DeviceStore(':memory:'), now=lambda: now_ref[0])


def test_registry():
    now = [1000.0]
    svc = make_service(now)
    d = svc.register('g-1', KIND_DESKTOP, name='RDR-1', library='SIGLA1', ip='10.0.0.5')
    check('register returns row', d and d['guid'] == 'g-1' and d['kind'] == KIND_DESKTOP)
    check('register not deleted', d['is_deleted'] == 0)
    # идемпотентность по guid — апдейт, не дубль
    d2 = svc.register('g-1', KIND_DESKTOP, name='RDR-1-renamed', library='SIGLA1')
    check('register idempotent by guid', d2['id'] == d['id'] and d2['name'] == 'RDR-1-renamed')
    check('list one device', len(svc.list(kind=KIND_DESKTOP)) == 1)
    # modify
    svc.modify(d['id'], name='RDR-1b')
    check('modify name', svc.store.get_device(d['id'])['name'] == 'RDR-1b')
    expect_raises('modify unknown raises', lambda: svc.modify(999, name='x'))
    # unknown kind
    expect_raises('register unknown kind raises', lambda: svc.register('g-x', 'frobnicator'))
    # remove → не в списке
    svc.remove(d['id'])
    check('remove hides from list', len(svc.list(kind=KIND_DESKTOP)) == 0)
    check('get_by_guid still finds (deleted)', svc.get('g-1')['is_deleted'] == 1)


def test_derive_state():
    ds = DeviceService.derive_state
    check('derive: offline->unconfigured', ds(0, 5, 0) == STATE_UNCONFIGURED)
    check('derive: errors only->diag', ds(1, 0, 3) == STATE_DIAG)
    check('derive: ok->ok', ds(1, 7, 1) == STATE_OK)
    check('derive: nothing->unknown', ds(1, 0, 0) == STATE_UNKNOWN)


def test_heartbeat():
    now = [5000.0]
    svc = make_service(now)
    svc.register('g-2', KIND_DESKTOP, name='RDR-2')
    st = svc.heartbeat('g-2', soft_online=1, ok_count=10, error_count=0)
    check('heartbeat returns state ok', st == STATE_OK)
    dev = svc.get('g-2')
    check('heartbeat sets online', dev['is_online'] == 1 and dev['last_seen'] == 5000.0)
    check('health series has 1', len(svc.health_series(dev['id'])) == 1)
    # online TTL
    check('is_online within ttl', svc.is_online(dev) is True)
    now[0] = 5000.0 + ONLINE_TTL_SEC + 1
    check('is_online expired', svc.is_online(dev) is False)
    expect_raises('heartbeat unknown guid raises', lambda: svc.heartbeat('nope'))


def test_events_and_sensors():
    now = [10.0]
    svc = make_service(now)
    g = svc.register('g-gate', KIND_GATE, name='Gate-1')
    svc.gate_alarm(g['id'], uid='E004FF', book_code='BK-100', book_name='Книга', is_book=1)
    evs = svc.events(device_id=g['id'])
    check('gate_alarm logs device_event', len(evs) == 1 and evs[0]['event_name'] == 'gate_eas')
    check('gate_event stored', len(svc.store._conn().execute('SELECT * FROM gate_event').fetchall()) == 1)
    svc.visitor(g['id'], value_in=3, value_out=1)
    vc = svc.store._conn().execute('SELECT * FROM visitor_count').fetchone()
    check('visitor stored in/out', vc['value_in'] == 3 and vc['value_out'] == 1)
    # shelf replace semantics
    sh = svc.register('g-shelf', KIND_SAFEKEEPER, name='Shelf')  # any device
    svc.shelf_sync(sh['id'], [{'book_code': 'A'}, {'book_code': 'B'}])
    check('shelf has 2', len(svc.store.list_shelf(sh['id'])) == 2)
    svc.shelf_sync(sh['id'], [{'book_code': 'C'}])
    items = svc.store.list_shelf(sh['id'])
    check('shelf replaced to 1', len(items) == 1 and items[0]['book_code'] == 'C')
    svc.acs_pass(g['id'], rfid_code='R-1', client_name='Иванов', direction=DIR_OUT, zone='Z1')
    check('acs event stored', len(svc.store._conn().execute('SELECT * FROM acs_event').fetchall()) == 1)


def test_masters():
    now = [1.0]
    svc = make_service(now)
    sk1 = svc.register('sk-1', KIND_SAFEKEEPER, name='SK-1')
    sk2 = svc.register('sk-2', KIND_SAFEKEEPER, name='SK-2')
    svc.master_modify('MK-AAA', fio='Петров', device_id=sk1['id'])
    check('masters scoped to sk1', len(svc.masters(device_id=sk1['id'])) == 1)
    check('masters sk2 empty', len(svc.masters(device_id=sk2['id'])) == 0)
    check('master valid on sk1', svc.is_master_valid('MK-AAA', sk1['id']) is True)
    check('master invalid on sk2', svc.is_master_valid('MK-AAA', sk2['id']) is False)
    check('wrong master invalid', svc.is_master_valid('MK-ZZZ', sk1['id']) is False)


def test_info_and_license():
    now = [100.0]
    svc = make_service(now)
    d = svc.register('g-info', KIND_DESKTOP, name='RDR-info', library='SIG')
    svc.heartbeat('g-info', soft_online=1, ok_count=0, error_count=2)  # -> diag
    info = svc.info(kind=KIND_DESKTOP)
    check('info one row', len(info) == 1)
    check('info state_name diag', info[0]['state_name'] == STATE_NAMES[STATE_DIAG])
    check('info online true', info[0]['online'] is True)
    check('license valid for live device', svc.is_license_valid('g-info') is True)
    svc.remove(d['id'])
    check('license invalid after remove', svc.is_license_valid('g-info') is False)
    check('license invalid unknown', svc.is_license_valid('nope') is False)


def test_tenant_and_cabinet_cells():
    print('-- tenant-изоляция + cabinet_cell (#414)')
    svc = make_service([1000.0])
    a = svc.register('cab-A', KIND_SELF_SERVICE_CABINET, name='Шкаф A', tenant='libA')
    b = svc.register('cab-B', KIND_SELF_SERVICE_CABINET, name='Шкаф B', tenant='libB')
    check('self_service_cabinet — валидный kind', a['kind'] == KIND_SELF_SERVICE_CABINET)
    check('device.tenant сохранён', a.get('tenant') == 'libA' and b.get('tenant') == 'libB')
    check('list(tenant=libA) — только свой', [d['guid'] for d in svc.list(tenant='libA')] == ['cab-A'])
    check('list(tenant=libB) — только свой', [d['guid'] for d in svc.list(tenant='libB')] == ['cab-B'])
    check('list() без tenant — оба', len(svc.list()) == 2)

    svc.cell_upsert('libA', a['id'], 'FRONT', 1, 9, state='occupied', item='INV-1', epc='EPC1')
    svc.cell_upsert('libA', a['id'], 'FRONT', 1, 10, state='free')
    svc.cell_upsert('libA', a['id'], 'BACK', 2, 3, state='awaiting_extraction', item='INV-2')
    check('cell_map — 3 ячейки', len(svc.cell_map('libA', a['id'])) == 3)
    free = svc.free_cells('libA', a['id'])
    check('free_cells — 1 свободная (y=10)', len(free) == 1 and free[0]['y'] == 10)

    # upsert идемпотентен по (device,row,x,y)
    svc.cell_upsert('libA', a['id'], 'FRONT', 1, 9, state='free')
    check('upsert не задвоил ячейку', len(svc.cell_map('libA', a['id'])) == 3)
    check('состояние ячейки обновлено',
          svc.store.cabinet_cell_get(a['id'], 'FRONT', 1, 9)['state'] == 'free')

    # изоляция ячеек между арендаторами
    svc.cell_upsert('libB', b['id'], 'FRONT', 1, 1, state='occupied', item='X')
    check('cell_map(libA) не видит ячейки libB', len(svc.cell_map('libA', a['id'])) == 3)
    check('cell_map(libB) — только свои', len(svc.cell_map('libB', b['id'])) == 1)


def test_device_tokens():
    print('-- device-token (BDP auth, #413)')
    nr = [1000.0]
    svc = make_service(nr)
    d = svc.register('cab-T', KIND_SELF_SERVICE_CABINET, name='Шкаф T', tenant='libT')
    t = svc.issue_token(d['id'])
    check('issue вернул сырой токен', isinstance(t.get('token'), str) and len(t['token']) > 20)
    check('токен наследует tenant устройства', t['tenant'] == 'libT')
    ctx = svc.authenticate_token('Bearer ' + t['token'])
    check('authenticate → device/tenant/kind',
          bool(ctx) and ctx['device_id'] == d['id'] and ctx['tenant'] == 'libT'
          and ctx['kind'] == KIND_SELF_SERVICE_CABINET)
    check('authenticate без Bearer-префикса тоже ок', svc.authenticate_token(t['token']) is not None)
    check('неверный токен → None', svc.authenticate_token('Bearer nope') is None)
    check('пустой → None', svc.authenticate_token('') is None)
    check('в сторе хэш, не сырой токен', svc.store.get_token_by_hash(t['token']) is None)

    # ротация: старый отзывается, новый работает
    t2 = svc.rotate_token(d['id'])
    check('после ротации старый невалиден', svc.authenticate_token(t['token']) is None)
    check('новый токен валиден', svc.authenticate_token(t2['token']) is not None)

    # отзыв
    svc.revoke_token(t2['id'])
    check('отозванный невалиден', svc.authenticate_token(t2['token']) is None)

    # срок годности
    t3 = svc.issue_token(d['id'], ttl=100)
    check('токен со сроком валиден до истечения', svc.authenticate_token(t3['token']) is not None)
    nr[0] = 1000.0 + 200
    check('просроченный невалиден', svc.authenticate_token(t3['token']) is None)

    # tenant-изоляция list
    d2 = svc.register('cab-U', KIND_SELF_SERVICE_CABINET, tenant='libU')
    svc.issue_token(d2['id'])
    check('list_tokens(tenant=libT) не видит libU',
          all(x['tenant'] == 'libT' for x in svc.list_tokens(tenant='libT')))
    # удалённое устройство → токен невалиден
    t4 = svc.issue_token(d2['id'])
    svc.remove(d2['id'])
    check('токен удалённого устройства невалиден', svc.authenticate_token(t4['token']) is None)


def main():
    for t in (test_registry, test_derive_state, test_heartbeat,
              test_events_and_sensors, test_masters, test_info_and_license,
              test_tenant_and_cabinet_cells, test_device_tokens):
        print('==', t.__name__)
        t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
