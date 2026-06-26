#!/usr/bin/env python3
"""ReaderAgentService tests — оркестратор настольного RFID-считывателя (#272).

    py -3.12 tests/test_reader_agent.py  -> ok ... + "N passed, M failed" + код

Покрыто: read_tag happy/без-UID/без-считывателя; program_tag ok/write-fail/
пустой item_id→ReaderAgentError; set_security on/off; issue/return_prepare —
правильное направление EAS (выдача OFF, возврат ON). Сиды — FakeTransport
(пишет вызовы, отдаёт канонические UID/блоки, ломается по требованию) и
FakeCodec (decode/encode тривиальны через repr-байты словаря).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.reader_agent import ReaderAgentService, ReaderAgentError, PRIMARY_ITEM_OID

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


class FakeTransport:
    """Фейк аппаратного канала: пишет вызовы, отдаёт канон, ломается по требованию."""

    def __init__(self, uid='UID-1', block=None, write_ok=True, eas_ok=True):
        self._uid = uid
        self._block = block
        self.write_ok = write_ok
        self.eas_ok = eas_ok
        self.calls = []          # список ('метод', аргумент)
        self.written = None      # последний записанный блок
        self.eas_state = None    # последнее значение set_eas

    def read_uid(self):
        self.calls.append(('read_uid', None))
        return self._uid

    def read_block(self):
        self.calls.append(('read_block', None))
        return self._block

    def write_block(self, data):
        self.calls.append(('write_block', data))
        self.written = data
        return self.write_ok

    def set_eas(self, on):
        self.calls.append(('set_eas', on))
        self.eas_state = on
        return self.eas_ok


class FakeCodec:
    """Тривиальный кодек: dict<->repr-байты (encode/decode обратимы)."""

    def encode_block(self, mapping):
        return repr(dict(mapping)).encode('utf-8')

    def decode_block(self, data):
        try:
            return eval(data.decode('utf-8'), {'__builtins__': {}}, {})
        except Exception:
            return {}


def encoded(mapping):
    return FakeCodec().encode_block(mapping)


def test_read_tag_happy():
    block = encoded({PRIMARY_ITEM_OID: 'BK-100', 5: 'RU-LIB'})
    t = FakeTransport(uid='UID-9', block=block)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    r = s.read_tag()
    check('read_tag returns uid', r['uid'] == 'UID-9')
    check('read_tag decodes itemId (OID 1)', r['itemId'] == 'BK-100')
    check('read_tag returns decoded data', r['data'].get(5) == 'RU-LIB')
    check('read_tag read uid+block', [c[0] for c in t.calls] == ['read_uid', 'read_block'])


def test_read_tag_no_uid():
    t = FakeTransport(uid=None)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    r = s.read_tag()
    check('no-uid -> uid None', r['uid'] is None)
    check('no-uid -> itemId None', r['itemId'] is None)
    check('no-uid does not read block', ('read_block', None) not in t.calls)


def test_read_tag_no_transport():
    s = ReaderAgentService(transport=None, codec=FakeCodec())
    r = s.read_tag()
    check('no-reader -> uid None', r['uid'] is None)
    check('no-reader -> reason no-reader', r.get('reason') == 'no-reader')


def test_program_tag_ok():
    t = FakeTransport(write_ok=True)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    r = s.program_tag('BK-7', extra={5: 'RU-LIB'})
    check('program_tag ok', r['ok'] is True)
    check('program_tag written length', r['written'] == len(t.written))
    # OID 1 = item_id попал в payload
    decoded = FakeCodec().decode_block(t.written)
    check('program_tag encodes OID1=item_id', decoded.get(PRIMARY_ITEM_OID) == 'BK-7')
    check('program_tag merges extra', decoded.get(5) == 'RU-LIB')


def test_program_tag_write_fail():
    t = FakeTransport(write_ok=False)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    r = s.program_tag('BK-8')
    check('write-fail -> ok False', r['ok'] is False)
    check('write-fail -> written 0', r['written'] == 0)


def test_program_tag_empty_raises():
    s = ReaderAgentService(transport=FakeTransport(), codec=FakeCodec())
    raised = False
    try:
        s.program_tag('')
    except ReaderAgentError:
        raised = True
    check('empty item_id raises ReaderAgentError', raised)
    raised_none = False
    try:
        s.program_tag(None)
    except ReaderAgentError:
        raised_none = True
    check('None item_id raises ReaderAgentError', raised_none)


def test_program_tag_no_transport():
    s = ReaderAgentService(transport=None, codec=FakeCodec())
    r = s.program_tag('BK-1')
    check('program no-reader -> ok False', r['ok'] is False and r['written'] == 0)


def test_set_security_on_off():
    t = FakeTransport(eas_ok=True)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    on = s.set_security(True)
    check('set_security on -> ok+eas True', on == {'ok': True, 'eas': True})
    check('set_security on -> transport set_eas(True)', t.eas_state is True)
    off = s.set_security(False)
    check('set_security off -> ok+eas False', off == {'ok': True, 'eas': False})
    check('set_security off -> transport set_eas(False)', t.eas_state is False)


def test_set_security_fail_and_no_transport():
    t = FakeTransport(eas_ok=False)
    s = ReaderAgentService(transport=t, codec=FakeCodec())
    r = s.set_security(True)
    check('set_eas fail -> ok False (eas requested True)', r == {'ok': False, 'eas': True})
    s2 = ReaderAgentService(transport=None)
    r2 = s2.set_security(True)
    check('set_security no-reader -> ok False', r2['ok'] is False and r2.get('reason') == 'no-reader')


def test_issue_return_prepare_direction():
    # выдача → EAS OFF (книга может покинуть зону)
    t1 = FakeTransport()
    s1 = ReaderAgentService(transport=t1, codec=FakeCodec())
    r1 = s1.issue_prepare('BK-1')
    check('issue_prepare sets EAS OFF', r1['eas'] is False and t1.eas_state is False)
    # возврат → EAS ON (книга снова под защитой)
    t2 = FakeTransport()
    s2 = ReaderAgentService(transport=t2, codec=FakeCodec())
    r2 = s2.return_prepare('BK-1')
    check('return_prepare sets EAS ON', r2['eas'] is True and t2.eas_state is True)


def main():
    for t in (test_read_tag_happy, test_read_tag_no_uid, test_read_tag_no_transport,
              test_program_tag_ok, test_program_tag_write_fail,
              test_program_tag_empty_raises, test_program_tag_no_transport,
              test_set_security_on_off, test_set_security_fail_and_no_transport,
              test_issue_return_prepare_direction):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
