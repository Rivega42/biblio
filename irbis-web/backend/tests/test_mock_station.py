#!/usr/bin/env python3
"""MockStation tests — эмулятор станции самообслуживания IDlogic (#272).

    py -3.12 tests/test_mock_station.py  -> ok ... + "N passed, M failed" + код

Покрыто: ping (жив/мёртв); identify hit/miss; read_tag (ok/битый);
self_checkout смешанный успех+отказ; self_checkin; loans; gate_pass;
полный run_self_service (happy path → правильный summary + длина transcript);
graceful, когда identify вернул ``[]``; MockStationError при ``call=None`` и
не-callable. Seam — ``FakeApi.call(endpoint, payload)`` с канон-ответами на
имена эндпоинтов (форма реальных ответов compat-шима).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.mock_station import MockStation, MockStationError

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


class FakeApi:
    """Фейк device-facing seam: канон-ответы по имени эндпоинта + журнал вызовов.

    Формы ответов зеркалят реальный compat-шим:
      ReaderInfoGet        -> [{'AbisCode','RFIDCode'}] | []
      TagDecode            -> {'ItemId': 'INV-..'} | {'ItemId': None}
      Checkout/Checkin     -> {'Success': True} | {'Success': False,'Reasons':[..]}
      GetClientChargedDocs -> [{..}]
      IsServerAlive        -> True/False
      GateEventAdd         -> True/False
    """

    def __init__(self, alive=True, readers=None, tags=None, deny=None,
                 loans=None, gate_ok=True):
        self.alive = alive
        self.readers = readers or {}        # rfid -> AbisCode
        self.tags = tags or {}              # hex_block -> ItemId
        self.deny = set(deny or [])         # bookCode, которым отказать в Checkout
        self._loans = loans if loans is not None else []
        self.gate_ok = gate_ok
        self.calls = []                     # список (endpoint, payload)

    def call(self, endpoint, payload):
        self.calls.append((endpoint, payload))
        if endpoint == 'IsServerAlive':
            return self.alive
        if endpoint == 'ReaderInfoGet':
            abis = self.readers.get(payload.get('rfidCode'))
            if not abis:
                return []
            return [{'AbisCode': abis, 'RFIDCode': payload.get('rfidCode')}]
        if endpoint == 'TagDecode':
            return {'ItemId': self.tags.get(payload.get('block'))}
        if endpoint in ('Checkout', 'Checkin'):
            code = payload.get('bookCode')
            if code in self.deny:
                return {'Success': False, 'Reasons': ['policy_block']}
            return {'Success': True}
        if endpoint == 'GetClientChargedDocs':
            return list(self._loans)
        if endpoint == 'GateEventAdd':
            return self.gate_ok
        raise AssertionError('unexpected endpoint: %r' % (endpoint,))


# Удобный конструктор: вернуть (MockStation, FakeApi) с общим seam.
def make(**kw):
    api = FakeApi(**kw)
    return MockStation(api.call), api


def test_ping():
    st, _ = make(alive=True)
    check('ping alive -> True', st.ping() is True)
    st2, _ = make(alive=False)
    check('ping dead -> False', st2.ping() is False)
    check('ping recorded in transcript', st.transcript[0][0] == 'IsServerAlive')


def test_identify():
    st, _ = make(readers={'RF-1': 'T-1'})
    check('identify hit -> ticket', st.identify_by_card('RF-1') == 'T-1')
    check('identify miss -> None', st.identify_by_card('RF-X') is None)
    check('identify empty rfid -> None', st.identify_by_card('') is None)


def test_read_tag():
    st, _ = make(tags={'AA': 'INV-1'})
    check('read_tag ok -> itemId', st.read_tag('AA') == 'INV-1')
    check('read_tag bad block -> None', st.read_tag('FF') is None)


def test_self_checkout_mixed():
    st, _ = make(deny={'INV-2'})
    out = st.self_checkout('T-1', ['INV-1', 'INV-2', 'INV-3'])
    check('checkout issued the allowed', out['issued'] == ['INV-1', 'INV-3'])
    check('checkout denied the blocked', [d['item'] for d in out['denied']] == ['INV-2'])
    check('denial carries reasons', out['denied'][0]['reasons'] == ['policy_block'])
    check('checkout empty list -> empty result',
          st.self_checkout('T-1', []) == {'issued': [], 'denied': []})


def test_self_checkin():
    st, _ = make(deny={'INV-9'})
    out = st.self_checkin('T-1', ['INV-1', 'INV-9'])
    check('checkin returned the allowed', out['returned'] == ['INV-1'])
    check('checkin denied the blocked', [d['item'] for d in out['denied']] == ['INV-9'])


def test_loans():
    st, _ = make(loans=[{'BookCode': 'INV-1'}, {'BookCode': 'INV-2'}])
    check('loans returns docs', len(st.loans('T-1')) == 2)
    st2, _ = make(loans=[])
    check('loans empty -> []', st2.loans('T-1') == [])


def test_gate_pass():
    st, api = make(gate_ok=True)
    check('gate_pass ok -> True', st.gate_pass('INV-1') is True)
    check('gate_pass sent isBook', api.calls[-1][1]['isBook'] == 1)
    st2, _ = make(gate_ok=False)
    check('gate_pass fail -> False', st2.gate_pass('INV-1') is False)


def test_run_self_service_happy():
    st, _ = make(readers={'RF-1': 'T-1'},
                 tags={'AA': 'INV-1', 'BB': 'INV-2'},
                 loans=[{'BookCode': 'INV-1'}, {'BookCode': 'INV-2'}])
    summary = st.run_self_service('RF-1', ['AA', 'BB'])
    check('run identifies ticket', summary['ticket'] == 'T-1')
    check('run reads both items', summary['items'] == ['INV-1', 'INV-2'])
    check('run issues both', summary['issued'] == ['INV-1', 'INV-2'])
    check('run no denials', summary['denied'] == [])
    check('run reports loan count', summary['loan_count'] == 2)
    check('run alive flag', summary['alive'] is True)
    # transcript: ping, identify, 2x TagDecode, 2x Checkout, loans = 7 calls
    check('run transcript length', len(st.transcript) == 7)


def test_run_self_service_no_reader():
    st, _ = make(readers={}, tags={'AA': 'INV-1'})
    summary = st.run_self_service('RF-NONE', ['AA'])
    check('no reader -> ticket None', summary['ticket'] is None)
    check('no reader -> no issue', summary['issued'] == [])
    check('no reader -> no Checkout call',
          all(e != 'Checkout' for e, _, _ in st.transcript))


def test_run_self_service_with_denial():
    st, _ = make(readers={'RF-1': 'T-1'}, tags={'AA': 'INV-1', 'BB': 'INV-2'},
                 deny={'INV-2'}, loans=[{'BookCode': 'INV-1'}])
    summary = st.run_self_service('RF-1', ['AA', 'BB'])
    check('mixed run issues one', summary['issued'] == ['INV-1'])
    check('mixed run denies one', [d['item'] for d in summary['denied']] == ['INV-2'])
    check('mixed run loan count', summary['loan_count'] == 1)


def test_constructor_guards():
    try:
        MockStation(None)
        check('call=None raises', False)
    except MockStationError:
        check('call=None raises', True)
    try:
        MockStation('not-callable')
        check('non-callable raises', False)
    except MockStationError:
        check('non-callable raises', True)
    api = FakeApi()
    st = MockStation(api.call, device_id='kiosk-7')
    check('device_id stored', st.device_id == 'kiosk-7')


def main():
    for t in (test_ping, test_identify, test_read_tag, test_self_checkout_mixed,
              test_self_checkin, test_loans, test_gate_pass,
              test_run_self_service_happy, test_run_self_service_no_reader,
              test_run_self_service_with_denial, test_constructor_guards):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
