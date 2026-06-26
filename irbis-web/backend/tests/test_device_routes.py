#!/usr/bin/env python3
"""Device HTTP routes (POST /api/devices/*) — HTTP-врезка compat-шима (#272).

Гоняем через ``Api.route`` (идиом tests/test_circ_routes.py), без живого ИРБИС и
без файловых БД (все *_DB → ':memory:'). Проверяем: Basic-аутентификацию
ServiceLogin (env EASYBOOK_LEGACY_PASS), плумбинг к devices/readers/locker и
ошибки.

    py -3.12 tests/test_device_routes.py
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEGACY_PASS = 'SEKRET-test'
_MEM_DBS = ('DEVICES_DB', 'READERS_DB', 'LOCKER_DB', 'CIRC_DB', 'CATALOG_DB',
            'ACQ_DB', 'BP_DB', 'NOTIFY_DB', 'FULLTEXT_DB', 'RIGHTS_DB', 'LICH_DB',
            'SOCIAL_DB', 'SHELVES_DB', 'OIDC_DB')

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


def _api():
    os.environ['JWT_SECRET'] = 'test-secret'
    os.environ['EASYBOOK_LEGACY_PASS'] = LEGACY_PASS
    for k in _MEM_DBS:
        os.environ[k] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    return _core.Api(), _core


def _basic(login='ServiceLogin', pwd=LEGACY_PASS):
    raw = base64.b64encode(('%s:%s' % (login, pwd)).encode()).decode()
    return {'authorization': 'Basic ' + raw}


def _post(api, endpoint, body, headers):
    return api.route('POST', '/api/devices/' + endpoint, {}, body, headers)


def test_auth_gate():
    api, _ = _api()
    st, p = _post(api, 'IsServerAlive', {}, {})
    check('no auth -> 401', st == 401 and p['ok'] is False)
    st, p = _post(api, 'IsServerAlive', {}, _basic(pwd='wrong'))
    check('wrong pass -> 401', st == 401)
    st, p = _post(api, 'IsServerAlive', {}, _basic())
    check('valid Basic -> 200 alive', st == 200 and p['data'] is True)


def test_heartbeat_and_unknown():
    api, _ = _api()
    from access.devices import KIND_GATE
    dev = api.devices.register('gate-guid', KIND_GATE, name='Ворота 1')
    st, p = _post(api, 'DeviceDataAdd',
                  {'deviceID': 'gate-guid', 'softOnlineCount': 1, 'deviceOkCount': 3,
                   'deviceErrorCount': 0}, _basic())
    check('heartbeat -> 200 True', st == 200 and p['data'] is True)
    check('device marked online', api.devices.is_online(api.devices.get('gate-guid')) is True)
    st, p = _post(api, 'Frobnicate', {}, _basic())
    check('unknown endpoint -> 400', st == 400 and p['error']['code'] == 'unsupported')


def test_reader_bind_then_info():
    api, _ = _api()
    st, p = _post(api, 'ReaderModify', {'abisCode': 'T-77', 'rfidCode': 'RF-77'}, _basic())
    check('ReaderModify -> 200 True', st == 200 and p['data'] is True)
    st, p = _post(api, 'ReaderInfoGet', {'rfidCode': 'RF-77'}, _basic())
    check('ReaderInfoGet maps card->ticket',
          st == 200 and p['data'] == [{'AbisCode': 'T-77', 'RFIDCode': 'RF-77'}])
    st, p = _post(api, 'ReaderInfoGet', {'rfidCode': 'UNKNOWN'}, _basic())
    check('unknown card -> []', st == 200 and p['data'] == [])


def test_locker_order_via_http():
    api, _ = _api()
    from access.devices import KIND_SAFEKEEPER
    api.devices.register('sk-guid', KIND_SAFEKEEPER, name='SK-1')
    st, oid = _post(api, 'OrderModify',
                    {'opID': 1, 'safeKeeperID': 'sk-guid', 'readerRFID': 'T-1'}, _basic())
    order_id = oid['data']
    check('OrderModify create -> id', st == 200 and isinstance(order_id, int) and order_id > 0)
    api.locker.add_book(order_id, 'BK-1')
    _post(api, 'OrderModify', {'opID': 2, 'id': order_id, 'stateID': 3, 'cellNumber': 1}, _basic())
    st, p = _post(api, 'OrdersGet', {'safeKeeperID': 'sk-guid'}, _basic())
    check('OrdersGet returns staffed order',
          st == 200 and len(p['data']) == 1 and p['data'][0]['CellNumber'] == 1)


def _book_with_copy(inv, status):
    return {'920': 'PAZK', '200': [{'a': 'Алгоритмы и структуры данных', 'f': 'Кнут Д.'}],
            '700': [{'a': 'Кнут', 'g': 'Дональд'}], '101': 'rus',
            '910': [{'a': status, 'b': inv}], '907': [{'a': 'Каталогизатор'}]}


def test_iabis_checkout_e2e():
    """Реальная книговыдача через HTTP: Checkout→loans→GetDocState→Checkin
    бьёт в боевой CirculationEngine + каталожный 910^A (тот же, что АРМ выдачи)."""
    from access.catalog import EXEMPLAR_FREE
    api, _ = _api()
    db = api.cfg.db_default
    api.catalog.save(db, _book_with_copy('INV-1', EXEMPLAR_FREE))
    H = _basic()
    st, p = _post(api, 'Checkout', {'abisCode': 'R-1', 'bookCode': 'INV-1'}, H)
    check('Checkout e2e -> Success', st == 200 and p['data']['Success'] is True)
    st, p = _post(api, 'GetClientChargedDocs', {'abisCode': 'R-1'}, H)
    check('loan visible after checkout',
          st == 200 and len(p['data']) == 1 and str(p['data'][0]['item']) == 'INV-1')
    st, p = _post(api, 'GetDocState', {'bookCode': 'INV-1'}, H)
    check('910^A flipped to issued',
          st == 200 and p['data'] and p['data'][0]['State'] != EXEMPLAR_FREE)
    st, p = _post(api, 'Checkin', {'abisCode': 'R-1', 'bookCode': 'INV-1'}, H)
    check('Checkin e2e -> Success', st == 200 and p['data']['Success'] is True)
    st, p = _post(api, 'GetClientChargedDocs', {'abisCode': 'R-1'}, H)
    check('no loans after checkin', st == 200 and len(p['data']) == 0)
    st, p = _post(api, 'GetDocState', {'bookCode': 'INV-1'}, H)
    check('910^A back to free', st == 200 and p['data'][0]['State'] == EXEMPLAR_FREE)


def test_tag_roundtrip_route():
    """Кодек тега через HTTP: TagEncode → TagDecode восстанавливает itemId."""
    api, _ = _api()
    H = _basic()
    st, p = _post(api, 'TagEncode', {'itemId': '2001001'}, H)
    check('TagEncode -> 200 hex', st == 200 and p['data']['Block'])
    st, p = _post(api, 'TagDecode', {'block': p['data']['Block']}, H)
    check('TagDecode -> itemId', st == 200 and p['data']['ItemId'] == '2001001')


def main():
    for t in (test_auth_gate, test_heartbeat_and_unknown, test_reader_bind_then_info,
              test_locker_order_via_http, test_iabis_checkout_e2e,
              test_tag_roundtrip_route):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
