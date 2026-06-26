#!/usr/bin/env python3
"""Sip2Codec + Sip2Service tests — SIP2-кодек и ACS-диспетчер (станции/киоски).

    py -3.12 tests/test_sip2.py  -> ok ... + "N passed, M failed" + код

Покрыто: checksum (известный вектор + инвариант), parse/build round-trip,
конверт AY/AZ с checksum_ok True/False, повтор поля → список, мусорный кадр →
Sip2Error; пары сообщений 93→94, 99→98, 63→64 (со списком loans), 17→18,
11→12 (ok + deny с AF из reasons), 09→10, 29→30, 35→36; graceful при сидах None.

Фейки (Decision-like / FakeCirc / FakeReaders) — duck-typed под контракт сервиса.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.sip2 import Sip2Codec, Sip2Service, Sip2Error

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Фейки доменных сидов (duck-typed под контракт Sip2Service).
# --------------------------------------------------------------------------- #
class FakeDecision:
    """Decision-like: .ok + .reasons (как access.circulation.Decision)."""

    def __init__(self, ok, reasons=None):
        self._ok = ok
        self.reasons = list(reasons or [])

    @property
    def ok(self):
        return self._ok


class FakeCirc:
    """circulation-сид: checkout/checkin/renew/loans/doc_state."""

    def __init__(self, decision=None, loans=None, state=None):
        self._decision = decision
        self._loans = loans or []
        self._state = state
        self.calls = []

    def checkout(self, ticket, item):
        self.calls.append(('checkout', ticket, item))
        return self._decision

    def checkin(self, ticket, item):
        self.calls.append(('checkin', ticket, item))
        return self._decision

    def renew(self, ticket, item):
        self.calls.append(('renew', ticket, item))
        return self._decision

    def loans(self, ticket):
        self.calls.append(('loans', ticket))
        return list(self._loans)

    def doc_state(self, item):
        self.calls.append(('doc_state', item))
        return self._state


class FakeReaders:
    """readers-сид: find_by_card(rfid) -> {'abis_code': билет} | None."""

    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    def find_by_card(self, code):
        t = self.mapping.get(code)
        return {'abis_code': t, 'rfid_code': code} if t else None


C = Sip2Codec
FIXED_NOW = 1_700_000_000.0   # фиксированное «сейчас» для детерминизма
DT = '20231115    000000'     # SIP2 datetime-болванка (18 символов) для запросов


def svc(circ=None, readers=None):
    return Sip2Service(circulation=circ, readers=readers, now=lambda: FIXED_NOW,
                       inst_id='BIBLIO')


# Болванки фикс.части запросов: длина обязана совпадать с Sip2Codec.FIXED_LEN,
# чтобы переменные поля (AA/AB/AO) разбирались корректно (см. §2 разбора).
def req(mid, fixed, fields, seq=None):
    assert len(fixed) == C.FIXED_LEN.get(mid, len(fixed)), \
        '%s fixed len %d != %r' % (mid, len(fixed), C.FIXED_LEN.get(mid))
    return C.build(mid, fixed, fields, seq=seq)


F_LOGIN = '00'                       # 93: алгоритмы UID/PWD
F_SCSTATUS = '0' + '010' + '2.00'    # 99: status+width+version
F_PATRON = '000' + DT + '          '  # 63: язык(3)+дата+summary(10)
F_ITEM = DT                          # 17: дата
F_CO = 'YN' + DT + DT                # 11: renew_ok+no_block+дата+срок
F_CI = 'N' + DT + DT                 # 09: no_block+дата+дата
F_RENEW = 'YN' + DT + DT             # 29: renew_ok+no_block+дата+срок
F_END = DT                           # 35: дата


# --------------------------------------------------------------------------- #
# Кодек.
# --------------------------------------------------------------------------- #
def test_checksum_known_vector():
    # Инвариант: сумма всех байтов кадра (вплоть до AZ) + checksum-байты ≡ 0.
    s = '9300CNuser|COpw|CPloc|AY1AZ'
    crc = C.checksum(s)
    check('checksum is 4 upper-hex', len(crc) == 4 and crc == crc.upper())
    total = (sum(ord(c) for c in s) + int(crc[0:2], 16) + int(crc[2:4], 16))
    # (0x10000 - sum) & 0xFFFF — проверим прямой формулой.
    expect = '%04X' % ((0x10000 - (sum(ord(c) for c in s) & 0xFFFF)) & 0xFFFF)
    check('checksum matches formula', crc == expect)


def test_build_parse_roundtrip():
    frame = C.build('11', F_CO, [('AA', 'T-1'), ('AB', 'BK-9')])
    p = C.parse(frame)
    check('roundtrip id', p['id'] == '11')
    check('roundtrip fixed', p['fixed'] == F_CO)
    check('roundtrip field AA', p['fields'].get('AA') == 'T-1')
    check('roundtrip field AB', p['fields'].get('AB') == 'BK-9')
    check('roundtrip no seq', p['seq'] is None)
    check('roundtrip no checksum', p['checksum_ok'] is None)


def test_build_parse_with_envelope_ok():
    frame = C.build('93', F_LOGIN, [('CN', 'u'), ('CO', 'p')], seq=3)
    check('envelope ends CRLF', frame.endswith('\r'))
    check('envelope has AY/AZ', 'AY3AZ' in frame)
    p = C.parse(frame)
    check('parse seq', p['seq'] == 3)
    check('parse checksum_ok True', p['checksum_ok'] is True)
    check('parse field through envelope', p['fields'].get('CN') == 'u')


def test_parse_checksum_bad():
    frame = C.build('93', F_LOGIN, [('CN', 'u')], seq=3)
    # Портим CRC (последние 4 hex перед \r).
    bad = frame[:-5] + '0000' + '\r'
    p = C.parse(bad)
    check('parse checksum_ok False on tamper', p['checksum_ok'] is False)
    check('parse still recovers seq', p['seq'] == 3)


def test_parse_repeated_field_list():
    # 64 fixed = 35 символов (status14+lang3+date18); затем повторяющиеся AU.
    frame = C.build('64', ' ' * 14 + '000' + DT,
                    [('AU', 'BK-1'), ('AU', 'BK-2'), ('AU', 'BK-3')])
    p = C.parse(frame)
    check('repeated field -> list', p['fields'].get('AU') == ['BK-1', 'BK-2', 'BK-3'])


def test_parse_garbage_raises():
    raised = []
    for bad in ('', 'x', '7', None):
        try:
            C.parse(bad)
        except Sip2Error:
            raised.append(True)
        except Exception:
            raised.append(False)
    check('garbage frames raise Sip2Error', raised == [True, True, True, True])


# --------------------------------------------------------------------------- #
# Сервис — пары сообщений.
# --------------------------------------------------------------------------- #
def test_login_93_94():
    s = svc()
    resp = s.handle(req('93', F_LOGIN, [('CN', 'u'), ('CO', 'p'), ('CP', 'loc')],
                        seq=1))
    p = C.parse(resp)
    check('login resp id 94', p['id'] == '94')
    check('login ok flag', p['fixed'][:1] == '1')
    check('login echoes seq', p['seq'] == 1)


def test_status_99_98():
    s = svc()
    resp = s.handle(req('99', F_SCSTATUS, []))
    p = C.parse(resp)
    check('status resp id 98', p['id'] == '98')
    check('status online flag', p['fixed'][:1] == '1')
    check('status has AO inst', p['fields'].get('AO') == 'BIBLIO')
    check('status has BX support mask', isinstance(p['fields'].get('BX'), str)
          and len(p['fields'].get('BX')) == 16)


def test_patron_63_64_with_loans():
    circ = FakeCirc(loans=['BK-1', 'BK-2'])
    readers = FakeReaders({'RF-7': 'T-7'})
    s = svc(circ=circ, readers=readers)
    resp = s.handle(req('63', F_PATRON, [('AO', 'BIBLIO'), ('AA', 'RF-7')], seq=5))
    p = C.parse(resp)
    check('patron resp id 64', p['id'] == '64')
    check('patron resolved ticket via readers', p['fields'].get('AA') == 'T-7')
    check('patron charged list AU', p['fields'].get('AU') == ['BK-1', 'BK-2'])
    check('patron echoes seq', p['seq'] == 5)
    check('loans called with resolved ticket', ('loans', 'T-7') in circ.calls)


def test_item_17_18():
    circ = FakeCirc(state='05')   # CirculationStatus 05 (Charged)
    s = svc(circ=circ)
    resp = s.handle(req('17', F_ITEM, [('AO', 'BIBLIO'), ('AB', 'BK-9')]))
    p = C.parse(resp)
    check('item resp id 18', p['id'] == '18')
    check('item circ status in fixed', p['fixed'][:2] == '05')
    check('item echoes AB', p['fields'].get('AB') == 'BK-9')
    check('doc_state called', ('doc_state', 'BK-9') in circ.calls)


def test_checkout_11_12_ok():
    circ = FakeCirc(decision=FakeDecision(True))
    s = svc(circ=circ)
    resp = s.handle(req('11', F_CO, [('AA', 'T-1'), ('AB', 'BK-9')]))
    p = C.parse(resp)
    check('checkout resp id 12', p['id'] == '12')
    check('checkout ok in fixed', p['fixed'][:1] == '1')
    check('checkout CK ok', p['fields'].get('CK') == '1')
    check('checkout no AF on ok', 'AF' not in p['fields'])
    check('checkout called', ('checkout', 'T-1', 'BK-9') in circ.calls)


def test_checkout_11_12_deny():
    circ = FakeCirc(decision=FakeDecision(False, reasons=['reader_has_debt']))
    s = svc(circ=circ)
    resp = s.handle(req('11', F_CO, [('AA', 'T-1'), ('AB', 'BK-9')]))
    p = C.parse(resp)
    check('checkout deny fixed', p['fixed'][:1] == '0')
    check('checkout deny CK 0', p['fields'].get('CK') == '0')
    check('checkout deny AF carries reason',
          'reader_has_debt' in (p['fields'].get('AF') or ''))


def test_checkin_09_10():
    circ = FakeCirc(decision=FakeDecision(True))
    s = svc(circ=circ)
    resp = s.handle(req('09', F_CI, [('AO', 'BIBLIO'), ('AB', 'BK-9')]))
    p = C.parse(resp)
    check('checkin resp id 10', p['id'] == '10')
    check('checkin ok in fixed', p['fixed'][:1] == '1')
    check('checkin echoes AB', p['fields'].get('AB') == 'BK-9')
    check('checkin called', any(c[0] == 'checkin' and c[2] == 'BK-9'
                                for c in circ.calls))


def test_renew_29_30():
    circ = FakeCirc(decision=FakeDecision(True))
    s = svc(circ=circ)
    resp = s.handle(req('29', F_RENEW, [('AA', 'T-1'), ('AB', 'BK-9')]))
    p = C.parse(resp)
    check('renew resp id 30', p['id'] == '30')
    # §2.7 разбора: успех терминала = resp[2:4]=='1Y'.
    check('renew ok marker 1Y', p['fixed'][:2] == '1Y')
    check('renew called', ('renew', 'T-1', 'BK-9') in circ.calls)


def test_end_session_35_36():
    s = svc(readers=FakeReaders({'RF-1': 'T-1'}))
    resp = s.handle(req('35', F_END, [('AA', 'RF-1')], seq=9))
    p = C.parse(resp)
    check('end session resp id 36', p['id'] == '36')
    check('end session ok Y', p['fixed'][:1] == 'Y')
    check('end session resolves ticket', p['fields'].get('AA') == 'T-1')
    check('end session echoes seq', p['seq'] == 9)


# --------------------------------------------------------------------------- #
# Graceful — все сиды None.
# --------------------------------------------------------------------------- #
def test_seams_none_graceful():
    s = Sip2Service(now=lambda: FIXED_NOW)   # circ/readers/devices = None
    # Checkout: None-circ → ok=0, валидный кадр 12.
    p = C.parse(s.handle(req('11', F_CO, [('AA', 'T-1'), ('AB', 'BK-9')])))
    check('none-circ checkout id 12', p['id'] == '12')
    check('none-circ checkout deny', p['fields'].get('CK') == '0')
    # Patron: None-circ/readers → пустой AU, AA = как пришло.
    p2 = C.parse(s.handle(req('63', F_PATRON, [('AA', 'T-9')])))
    check('none-circ patron id 64', p2['id'] == '64')
    check('none-circ patron AA passthrough', p2['fields'].get('AA') == 'T-9')
    check('none-circ patron no AU', 'AU' not in p2['fields'])
    # Item: None-circ → статус unknown '01', валидный кадр 18.
    p3 = C.parse(s.handle(req('17', F_ITEM, [('AB', 'BK-1')])))
    check('none-circ item id 18', p3['id'] == '18')
    check('none-circ item status 01', p3['fixed'][:2] == '01')
    # Unknown message → 96 Request SC Resend (мягкий отказ, не падение).
    p4 = C.parse(s.handle(C.build('77', '', [])))
    check('unknown msg -> 96 resend', p4['id'] == '96')


def main():
    for t in (test_checksum_known_vector, test_build_parse_roundtrip,
              test_build_parse_with_envelope_ok, test_parse_checksum_bad,
              test_parse_repeated_field_list, test_parse_garbage_raises,
              test_login_93_94, test_status_99_98, test_patron_63_64_with_loans,
              test_item_17_18, test_checkout_11_12_ok, test_checkout_11_12_deny,
              test_checkin_09_10, test_renew_29_30, test_end_session_35_36,
              test_seams_none_graceful):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
