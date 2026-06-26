#!/usr/bin/env python3
"""E2E симулятором станции (узел #272): MockStation гоняет полный сценарий
самообслуживания через РЕАЛЬНЫЙ compat-шим + боевую circulation + tag_codec.

Карта читателя + RFID-метка → бесконтактная книговыдача на станции:
  ping → identify_by_card(RFID→билет) → read_tag(декод метки→инв.№) →
  self_checkout(боевой Checkout) → loans. Плюс SIP2-кадр через тот же шим.

    py -3.12 tests/test_station_integration.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.mock_station import MockStation

PASS = [0]
FAIL = [0]
_MEM = ('DEVICES_DB', 'READERS_DB', 'LOCKER_DB', 'CIRC_DB', 'CATALOG_DB', 'ACQ_DB',
        'BP_DB', 'NOTIFY_DB', 'FULLTEXT_DB', 'INVENTORY_DB', 'VISION_DB')


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


def _api():
    os.environ['JWT_SECRET'] = 'test'
    os.environ['EASYBOOK_LEGACY_PASS'] = 'x'
    for k in _MEM:
        os.environ[k] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    return _core.Api()


def _book(inv, status):
    return {'920': 'PAZK', '200': [{'a': 'Алгоритмы', 'f': 'Кнут'}], '101': 'rus',
            '910': [{'a': status, 'b': inv}], '907': [{'a': 'Кат'}]}


def _book_at(inv, location):
    """Экземпляр на конкретном месте хранения (910^D=location)."""
    from access.catalog import EXEMPLAR_FREE
    r = _book(inv, EXEMPLAR_FREE)
    r['910'] = [{'a': EXEMPLAR_FREE, 'b': inv, 'd': location}]
    return r


def test_inventory_reconcile():
    api = _api()
    db = api.cfg.db_default
    api.catalog.save(db, _book_at('INV-A', 'A1'))
    api.catalog.save(db, _book_at('INV-B', 'A1'))
    api.catalog.save(db, _book_at('INV-C', 'A2'))
    inv = api.inventory
    s = inv.open(db, 'A1', operator='lib')
    inv.scan(s['id'], 'INV-A')    # present (ожидается на A1, отсканирован)
    inv.scan(s['id'], 'INV-C')    # foreign (числится на A2)
    inv.scan(s['id'], 'INV-UNK')  # unknown (нет в каталоге)
    rep = inv.report(s['id'])
    check('reconcile present', rep['present'] == ['INV-A'])
    check('reconcile missing (INV-B не отсканирован)', rep['missing'] == ['INV-B'])
    check('reconcile foreign (INV-C с A2)', 'INV-C' in rep['foreign'])
    check('reconcile unknown (INV-UNK)', 'INV-UNK' in rep['unknown'])


def test_book_cenz_route():
    from access.catalog import EXEMPLAR_FREE
    api = _api()
    db = api.cfg.db_default
    rec = _book('INV-Z', EXEMPLAR_FREE); rec['900'] = [{'z': '+16'}]
    api.catalog.save(db, rec)
    api.catalog.save(db, _book('INV-NOZ', EXEMPLAR_FREE))  # без 900 → дефолт 18
    r = api.compat_devices.handle('GetBookCenz', {'bookCode': 'INV-Z'})
    check('GetBookCenz 900^Z=16', r.get('MinAge') == 16)
    r2 = api.compat_devices.handle('GetBookCenz', {'bookCode': 'INV-NOZ'})
    check('GetBookCenz default 18', r2.get('MinAge') == 18)


def test_self_service_e2e():
    from access.catalog import EXEMPLAR_FREE
    api = _api()
    db = api.cfg.db_default
    api.catalog.save(db, _book('INV-1', EXEMPLAR_FREE))
    handle = api.compat_devices.handle
    # привязать карту RF-1 → билет T-1; закодировать метку INV-1
    handle('ReaderModify', {'abisCode': 'T-1', 'rfidCode': 'RF-1'})
    block = handle('TagEncode', {'itemId': 'INV-1'})['Block']

    st = MockStation(call=lambda ep, pl: handle(ep, pl))
    summary = st.run_self_service('RF-1', [block])
    check('станция онлайн', summary['alive'] is True)
    check('читатель опознан по карте', summary['ticket'] == 'T-1')
    check('метка раскодирована в инв.№', summary['items'] == ['INV-1'])
    check('книга выдана', summary['issued'] == ['INV-1'] and not summary['denied'])
    check('заём виден на станции', summary['loan_count'] == 1)
    check('транскрипт записан', len(st.transcript) >= 4)
    # возврат на станции освобождает экземпляр (checkin через тот же шим)
    s2 = MockStation(call=lambda ep, pl: handle(ep, pl))
    back = s2.self_checkin('T-1', ['INV-1'])
    check('возврат принят', back['returned'] == ['INV-1'] and not back['denied'])
    check('после возврата займов нет', len(s2.loans('T-1')) == 0)


def test_sip2_through_api():
    api = _api()
    # SIP2 95→... ; простой 93 Login кадр → 94 ответ через тот же шим
    r = api.compat_devices.handle('Sip2', {'line': '9300CNstaff|COpwd|'})
    check('SIP2 кадр обработан', isinstance(r['Response'], str) and r['Response'].startswith('94'))


def main():
    for t in (test_self_service_e2e, test_sip2_through_api,
              test_inventory_reconcile, test_book_cenz_route):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
