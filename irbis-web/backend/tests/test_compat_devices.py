#!/usr/bin/env python3
"""Device-facing compat-адаптер tests (узел #272, COMPAT_ADAPTER_CONTRACT.md 2/3).

Проверяет транслятор IDlogic-вызовов в нативные сервисы Biblio над in-memory
``DeviceService`` + фейковым ``readers``-сидом (детерминизм, без сети/DB-сервера).
Дом. стиль ``test_devices.py``::

    py -3.12 tests/test_compat_devices.py  -> ok ... + "N passed, M failed" + код

Покрыто:
  * auth: whitelist унаследованного Basic только при заданном legacy_pass; отказ
    при неверном/отсутствующем;
  * /easybookdll/*: IsServerAlive, LibraryInfoGet, DeviceDataAdd→heartbeat,
    DeviceIsLicenseValid, ReaderInfoGet/ReaderModify (с сидом и без — graceful),
    BooksCacheAddUpdate;
  * station-facing: MastersRFIDGet / SafeKeeperMasterRFIDModify → домен devices;
  * неизвестный эндпоинт → CompatError; endpoint с/без префикса.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.devices import DeviceService, DeviceStore, KIND_DESKTOP, KIND_SAFEKEEPER, STATE_OK
from access.compat_devices import (
    CompatDevicesService, CompatError, parse_basic, LEGACY_LOGIN,
    CARD_KIND_EKP, CARD_KIND_MAIN,
)
import base64

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


class FakeReaders:
    """Минимальный own-store/RDR сид для теста (карты 28/30/24)."""
    def __init__(self):
        self.cards = {'RFID-1': {'abis_code': 'T-100', 'rfid_code': 'RFID-1'}}
        self.bound = []

    def find_by_card(self, code):
        return self.cards.get(code)

    def bind_card(self, abis_code, rfid_code, serial, kind):
        self.bound.append((abis_code, rfid_code, serial, kind))
        return True


def make(devices_now=None, readers=None, legacy_pass=None):
    svc = DeviceService(DeviceStore(':memory:'), now=devices_now)
    return svc, CompatDevicesService(svc, readers=readers, legacy_pass=legacy_pass)


def basic(login, pwd):
    return 'Basic ' + base64.b64encode(('%s:%s' % (login, pwd)).encode()).decode()


def test_auth():
    _, c = make(legacy_pass='secret')
    check('auth ok legacy basic', c.authorize(basic(LEGACY_LOGIN, 'secret')) is True)
    check('auth wrong pass', c.authorize(basic(LEGACY_LOGIN, 'nope')) is False)
    check('auth wrong login', c.authorize(basic('other', 'secret')) is False)
    check('auth no header', c.authorize(None) is False)
    check('auth garbage', c.authorize('Bearer xyz') is False)
    _, c2 = make()  # legacy_pass not configured → compat off
    check('auth off when no legacy_pass', c2.authorize(basic(LEGACY_LOGIN, 'secret')) is False)
    # parse_basic
    check('parse_basic ok', parse_basic(basic('a', 'b')) == ('a', 'b'))
    check('parse_basic none', parse_basic('Basic !!!') is None)


def test_easybook_health_license():
    now = [1000.0]
    svc, c = make(devices_now=lambda: now[0])
    svc.register('g-1', KIND_DESKTOP, name='RDR', library='SIG-A')
    check('IsServerAlive', c.handle('easybookdll/IsServerAlive') is True)
    check('with leading slash', c.handle('/easybookdll/IsServerAlive') is True)
    li = c.handle('easybookdll/LibraryInfoGet', {'deviceID': 'g-1'})
    check('LibraryInfoGet maps library', li and li[0]['LibraryID'] == 'SIG-A')
    check('LibraryInfoGet unknown -> []', c.handle('easybookdll/LibraryInfoGet', {'deviceID': 'no'}) == [])
    # DeviceDataAdd -> heartbeat
    ok = c.handle('easybookdll/DeviceDataAdd',
                  {'deviceID': 'g-1', 'softOnlineCount': 1, 'deviceOkCount': 5, 'deviceErrorCount': 0})
    check('DeviceDataAdd true', ok is True)
    dev = svc.get('g-1')
    check('DeviceDataAdd set online', dev['is_online'] == 1)
    check('DeviceDataAdd wrote health (state ok)', svc.health_series(dev['id'])[-1]['state_id'] == STATE_OK)
    check('DeviceDataAdd unknown device -> false',
          c.handle('easybookdll/DeviceDataAdd', {'deviceID': 'no'}) is False)
    check('license valid', c.handle('easybookdll/DeviceIsLicenseValid', {'deviceID': 'g-1'}) is True)
    check('license unknown false', c.handle('easybookdll/DeviceIsLicenseValid', {'deviceID': 'no'}) is False)
    check('BooksCacheAddUpdate noop true', c.handle('easybookdll/BooksCacheAddUpdate', {}) is True)


def test_reader_seam():
    fr = FakeReaders()
    svc, c = make(readers=fr)
    info = c.handle('easybookdll/ReaderInfoGet', {'rfidCode': 'RFID-1'})
    check('ReaderInfoGet maps card', info and info[0]['AbisCode'] == 'T-100')
    check('ReaderInfoGet unknown card -> []', c.handle('easybookdll/ReaderInfoGet', {'rfidCode': 'X'}) == [])
    # ReaderModify with serial -> ekp kind
    ok = c.handle('easybookdll/ReaderModify',
                  {'abisCode': 'T-100', 'rfidCode': 'EKP-9', 'serialNumber': 'SN1'})
    check('ReaderModify true', ok is True)
    check('ReaderModify bound ekp', fr.bound and fr.bound[-1][3] == CARD_KIND_EKP)
    # ReaderModify without serial -> main kind
    c.handle('easybookdll/ReaderModify', {'abisCode': 'T-100', 'rfidCode': 'C-1'})
    check('ReaderModify main kind', fr.bound[-1][3] == CARD_KIND_MAIN)
    # graceful degrade без сида
    _, c2 = make()
    check('ReaderInfoGet no seam -> []', c2.handle('easybookdll/ReaderInfoGet', {'rfidCode': 'RFID-1'}) == [])
    check('ReaderModify no seam -> False', c2.handle('easybookdll/ReaderModify', {'abisCode': 'x'}) is False)


def test_station_masters():
    svc, c = make()
    sk = svc.register('sk-1', KIND_SAFEKEEPER, name='SK-1')
    ok = c.handle('/las/SafeKeeperMasterRFIDModify', {'safekeeperID': 'sk-1', 'rfidCode': 'MK-1', 'fio': 'Петров'})
    check('master modify true', ok is True)
    masters = c.handle('/las/MastersRFIDGet', {'safeKeeperID': 'sk-1'})
    check('masters get one', len(masters) == 1 and masters[0]['RFID'] == 'MK-1')
    check('master modify unknown sk false',
          c.handle('/las/SafeKeeperMasterRFIDModify', {'safekeeperID': 'no', 'rfidCode': 'X'}) is False)


def test_station_orders():
    from access.locker import LockerService, LockerStore, STAFFED, ISSUED, CANCELLED
    svc = DeviceService(DeviceStore(':memory:'))
    sk = svc.register('sk-ord', KIND_SAFEKEEPER, name='SK-ORD')
    lk = LockerService(LockerStore(':memory:'))
    c = CompatDevicesService(svc, locker=lk)
    # create order (opID=1) -> id
    oid = c.handle('/las/OrderModify', {'opID': 1, 'safeKeeperID': 'sk-ord',
                                        'readerRFID': 'T-1', 'readerFIO': 'Иванов'})
    check('OrderModify create returns id', isinstance(oid, int) and oid > 0)
    lk.add_book(oid, 'BK-1')
    # staff (stateID=3, cellNumber)
    c.handle('/las/OrderModify', {'opID': 2, 'id': oid, 'stateID': 3, 'cellNumber': 2})
    check('staffed via compat', lk.store.get_order(oid)['state'] == STAFFED)
    # OrdersGet maps
    orders = c.handle('/las/OrdersGet', {'safeKeeperID': 'sk-ord'})
    check('OrdersGet one', len(orders) == 1 and orders[0]['StateId'] == STAFFED)
    check('OrdersGet cell', orders[0]['CellNumber'] == 2 and orders[0]['ReaderRFID'] == 'T-1')
    # SafeKeeperInfoGet2 cells
    info = c.handle('/las/SafeKeeperInfoGet2', {'safeKeeperID': 'sk-ord'})
    check('cells_state bit for cell2', info and info[0]['CellsState'] == 0b10)
    check('busy cells', info[0]['BusyCells'] == [2])
    # OrderBookProcessedSet
    check('book processed set', c.handle('/las/OrderBookProcessedSet', {'orderID': oid, 'bookCode': 'BK-1'}) is True)
    check('item processed', lk.store.list_items(oid)[0]['processed'] == 1)
    # issue (stateID=4)
    c.handle('/las/OrderModify', {'opID': 2, 'id': oid, 'stateID': 4})
    check('issued via compat', lk.store.get_order(oid)['state'] == ISSUED)
    check('cell freed after issue', lk.busy_cells(sk['id']) == set())
    # cancel another
    oid2 = c.handle('/las/OrderModify', {'opID': 1, 'safeKeeperID': 'sk-ord', 'readerRFID': 'T-2'})
    c.handle('/las/OrderModify', {'opID': 0, 'id': oid2})
    check('cancelled via compat', lk.store.get_order(oid2)['state'] == CANCELLED)
    # no locker seam -> graceful
    _, c2 = make()
    check('OrdersGet no locker -> []', c2.handle('/las/OrdersGet', {'safeKeeperID': 'x'}) == [])
    check('OrderModify no locker -> 0', c2.handle('/las/OrderModify', {'opID': 1}) == 0)


def test_unknown():
    _, c = make()
    try:
        c.handle('easybookdll/Frobnicate', {})
        check('unknown raises', False)
    except CompatError:
        check('unknown raises', True)


class _Dec:
    """Имитация circulation.Decision (.ok/.reasons/.computed)."""
    def __init__(self, ok, reasons=None, computed=None):
        self.ok = ok
        self.reasons = reasons or []
        self.computed = computed or {}


class FakeAbis:
    """circulation-сид IAbis: checkout/checkin/renew/loans/doc_state."""
    def __init__(self, deny=(), no_loan=()):
        self.deny = set(deny)
        self.no_loan = set(no_loan)
        self.calls = []
    def checkout(self, ticket, code):
        self.calls.append(('checkout', ticket, code))
        if code in self.deny:
            return _Dec(False, reasons=['reader_has_debt'])
        return _Dec(True, computed={'due': 1700000000})
    def checkin(self, ticket, code):
        self.calls.append(('checkin', ticket, code))
        return None if code in self.no_loan else _Dec(True)
    def renew(self, ticket, code):
        self.calls.append(('renew', ticket, code))
        return None if code in self.no_loan else _Dec(True, computed={'due': 1700086400})
    def loans(self, ticket):
        return [{'loanId': 1, 'item': 'INV-1', 'title': 'Кнут', 'due': 1700086400}]
    def doc_state(self, code):
        return '1' if code == 'INV-1' else None


def test_iabis_circulation():
    abis = FakeAbis(deny=['BAD'], no_loan=['FREE'])
    c = CompatDevicesService(DeviceService(DeviceStore(':memory:')),
                             readers=FakeReaders(), circulation=abis)
    # checkout success / deny
    r = c.handle('easybookdll/Checkout', {'abisCode': 'T-1', 'bookCode': 'INV-1'})
    check('Checkout success', r['Success'] is True and r['Due'] == 1700000000)
    r = c.handle('easybookdll/Checkout', {'abisCode': 'T-1', 'bookCode': 'BAD'})
    check('Checkout deny + reasons', r['Success'] is False and 'reader_has_debt' in r['Reasons'])
    # резолв билета по RFID-карте через readers (RFID-1 → T-100)
    c.handle('easybookdll/Checkout', {'readerRFID': 'RFID-1', 'bookCode': 'INV-9'})
    check('Checkout resolves ticket via card', ('checkout', 'T-100', 'INV-9') in abis.calls)
    # bad request (нет билета/кода)
    check('Checkout bad_request', c.handle('easybookdll/Checkout', {'bookCode': 'X'})['Success'] is False)
    # checkin: успех и «нет выданного экземпляра»
    check('Checkin success', c.handle('easybookdll/Checkin', {'abisCode': 'T-1', 'bookCode': 'INV-1'})['Success'] is True)
    rn = c.handle('easybookdll/Checkin', {'abisCode': 'T-1', 'bookCode': 'FREE'})
    check('Checkin no loan -> not_found', rn['Success'] is False and 'not_found' in rn['Reasons'])
    # renew
    check('Renew success', c.handle('easybookdll/Renew', {'abisCode': 'T-1', 'bookCode': 'INV-1'})['Success'] is True)
    # loans + doc state
    loans = c.handle('easybookdll/GetClientChargedDocs', {'abisCode': 'T-1'})
    check('GetClientChargedDocs lists loan', len(loans) == 1 and loans[0]['item'] == 'INV-1')
    ds = c.handle('easybookdll/GetDocState', {'bookCode': 'INV-1'})
    check('GetDocState returns 910^A', ds == [{'BookCode': 'INV-1', 'State': '1'}])
    check('GetDocState unknown -> []', c.handle('easybookdll/GetDocState', {'bookCode': 'NOPE'}) == [])
    # graceful без circulation-сида
    c0 = CompatDevicesService(DeviceService(DeviceStore(':memory:')))
    check('Checkout no seam -> Success False', c0.handle('easybookdll/Checkout', {'abisCode': 'T', 'bookCode': 'I'})['Success'] is False)
    check('GetClientChargedDocs no seam -> []', c0.handle('easybookdll/GetClientChargedDocs', {'abisCode': 'T'}) == [])


def main():
    for t in (test_auth, test_easybook_health_license, test_reader_seam,
              test_station_orders, test_iabis_circulation,
              test_station_masters, test_unknown):
        print('==', t.__name__)
        t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
