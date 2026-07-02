#!/usr/bin/env python3
"""BDP HTTP-роуты /api/bdp/* (#418, DS1) — device-token контур для демостенда.

Прогоняет флоу через РОУТ-слой ``Api._bdp``: регистрация staff'ом → device-token →
card/item/reserve/commit/return/cells/health. Доказывает, что робо-шкаф / мок-агент /
киоск говорят с VPS по нативному BDP (не legacy Basic ServiceLogin). Standalone.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['JWT_SECRET'] = 'bdp-routes-test'
os.environ['ACCESS_DB'] = ':memory:'
os.environ['DEVICES_DB'] = ':memory:'
os.environ['LOCKER_DB'] = ':memory:'
import importlib
import core as _core
importlib.reload(_core)
from access import seed_vocab
from access.catalog import CatalogStore
from access import devices as _devices
from access import circulation as _circ
from access.readers import ReaderStore, ReaderService, KIND_MAIN

PASS = [0]
FAIL = [0]
STAFF = {'kind': 'staff', 'actor': 'tester', 'tenant': 'public'}


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _api():
    api = _core.Api()
    api.irbis = None
    seed_vocab.seed_vocabularies(api.access, from_catalog=False)
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    # Свежие in-memory домен-сторы — детерминизм + актуальная схема (изоляция от
    # файловых сторов из Api.__init__, которые копят состояние между прогонами).
    api.devices = _devices.DeviceService(_devices.DeviceStore(':memory:'))
    api.circulation = _circ.CirculationEngine(
        store=_circ.CirculationStore(':memory:'), policy=_circ.default_policy())
    api.readers = ReaderService(ReaderStore(':memory:'))
    api.catalog.save('IBIS', {
        '920': 'PAZK', '200': [{'a': 'Демо-книга'}], '700': [{'a': 'Автор'}],
        '610': [{'': 'демо'}], '101': 'rus', '907': [{'a': 'Оп'}],
        '910': [{'a': '0', 'b': 'INV-1', 'h': 'EPC-1'}]})
    api.readers.bind_card('T-9', 'CARD-9', kind=KIND_MAIN)
    return api


def run():
    print('-- BDP /api/bdp/* роуты (#418)')
    api = _api()

    st, _ = api._bdp('POST', '/api/bdp/reserve',
                     {'patron': 'T-9', 'item': 'INV-1'}, {}, None)
    check('без device-token → 401', st == 401)

    st, pl = api._bdp('POST', '/api/bdp/register',
                      {'guid': 'cab-1', 'name': 'Демо-шкаф'}, {}, STAFF)
    check('register (staff) → 200 + токен', st == 200 and bool(pl['data']['token']))
    tok = pl['data']['token']
    H = {'authorization': 'Bearer ' + tok}
    check('device — self_service_cabinet', pl['data']['device']['kind'] == _devices.KIND_SELF_SERVICE_CABINET)

    try:
        api._bdp('POST', '/api/bdp/register', {'guid': 'x'}, {}, None)
        check('register без staff → отказ', False)
    except _core.Denied:
        check('register без staff → Denied', True)

    st, pl = api._bdp('POST', '/api/bdp/card',
                      {'reader_role': 'main', 'uid': 'card-9'}, H, None)
    check('card → resolve_patron T-9', st == 200 and pl['data']['patron'] == 'T-9')

    st, pl = api._bdp('POST', '/api/bdp/item', {'epc': 'EPC-1'}, H, None)
    check('item(EPC-1) → INV-1', st == 200 and pl['data']['item'] == 'INV-1')

    st, pl = api._bdp('POST', '/api/bdp/reserve',
                      {'patron': 'T-9', 'item': 'INV-1', 'op_id': 'op-1'}, H, None)
    check('reserve → 200 PENDING', st == 200 and pl['data']['loan']['pending'] == 1)

    st, pl = api._bdp('POST', '/api/bdp/commit', {'op_id': 'op-1'}, H, None)
    check('commit → 200 активна', st == 200 and pl['data']['loan']['pending'] == 0)
    lid = pl['data']['loan']['id']

    api._bdp('POST', '/api/bdp/cell',
             {'row': 'FRONT', 'x': 1, 'y': 9, 'state': 'free'}, H, None)
    st, pl = api._bdp('GET', '/api/bdp/cells', {}, H, None)
    check('cells → зеркало ячеек (1)', st == 200 and len(pl['data']['cells']) == 1)

    st, pl = api._bdp('POST', '/api/bdp/return', {'loan_id': lid}, H, None)
    check('return → 200', st == 200)

    st, pl = api._bdp('POST', '/api/bdp/reserve',
                      {'patron': 'T-9', 'item': 'INV-1', 'op_id': 'op-1'}, H, None)
    check('replay reserve(op-1) идемпотентно', st == 200 and pl['data'].get('replayed') is True)

    st, _ = api._bdp('POST', '/api/bdp/commit', {'op_id': 'op-1'},
                     {'authorization': 'Bearer nope'}, None)
    check('чужой токен → 401', st == 401)

    st, pl = api._bdp('POST', '/api/bdp/health', {'note': 'ok'}, H, None)
    check('health → 200', st == 200 and pl['data']['ok'] is True)

    st, _ = api._bdp('POST', '/api/bdp/frobnicate', {}, H, None)
    check('unknown op → 404', st == 404)


def run_h1():
    print('-- BDP H1: card-binding + item-availability + ownership')
    api = _api()
    _, pa = api._bdp('POST', '/api/bdp/register', {'guid': 'cabA', 'name': 'A'}, {}, STAFF)
    HA = {'authorization': 'Bearer ' + pa['data']['token']}
    devA = pa['data']['device']['id']

    # reserve БЕЗ приложенной карты → 409 (не бронировать на произвольный билет)
    st, _ = api._bdp('POST', '/api/bdp/reserve', {'item': 'INV-1', 'op_id': 'A1'}, HA, None)
    check('reserve без карты → 409 no_card_session', st == 409)

    # card → серверная сессия; reserve берёт patron из неё
    api._bdp('POST', '/api/bdp/card', {'reader_role': 'main', 'uid': 'card-9'}, HA, None)
    st, pl = api._bdp('POST', '/api/bdp/reserve', {'item': 'INV-1', 'op_id': 'A1'}, HA, None)
    check('reserve после карты → 200 PENDING', st == 200 and pl['data']['loan']['pending'] == 1)

    # двойной reserve того же экземпляра (другой op) → item_unavailable
    st, pl = api._bdp('POST', '/api/bdp/reserve', {'item': 'INV-1', 'op_id': 'A2'}, HA, None)
    check('двойной reserve экземпляра → item_unavailable',
          st == 403 and 'item_unavailable' in str(pl))

    # другое устройство НЕ может commit/rollback чужую сагу
    _, pb = api._bdp('POST', '/api/bdp/register', {'guid': 'cabB', 'name': 'B'}, {}, STAFF)
    HB = {'authorization': 'Bearer ' + pb['data']['token']}
    st, _ = api._bdp('POST', '/api/bdp/commit', {'op_id': 'A1'}, HB, None)
    check('чужое устройство commit → 403 forbidden', st == 403)
    st, _ = api._bdp('POST', '/api/bdp/rollback', {'op_id': 'A1'}, HB, None)
    check('чужое устройство rollback → 403 forbidden', st == 403)

    # владелец commit — ок
    st, _ = api._bdp('POST', '/api/bdp/commit', {'op_id': 'A1'}, HA, None)
    check('владелец commit → 200', st == 200)


def main():
    run()
    run_h1()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
