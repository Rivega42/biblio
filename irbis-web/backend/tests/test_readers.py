#!/usr/bin/env python3
"""ReaderService tests — реестр карт RFID↔билет (ABIS-порт, #272).

    py -3.12 tests/test_readers.py  -> ok ... + "N passed, M failed" + код

Покрыто: bind→find (own-реестр); неизвестная карта → None; пустые аргументы →
False; идемпотентный upsert + смена kind; фолбэк в живой RDR через сид
``rdr_lookup``; cards_for(билет).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.readers import ReaderStore, ReaderService, KIND_MAIN, KIND_EKP

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


def svc(rdr_lookup=None):
    return ReaderService(ReaderStore(':memory:'), rdr_lookup=rdr_lookup)


def test_bind_find():
    s = svc()
    check('bind ok', s.bind_card('T-1', 'RF-1') is True)
    r = s.find_by_card('RF-1')
    check('find returns mapping', r == {'abis_code': 'T-1', 'rfid_code': 'RF-1'})
    check('unknown card -> None', s.find_by_card('NOPE') is None)
    check('empty rfid -> None', s.find_by_card('') is None)


def test_bind_guards():
    s = svc()
    check('no abis -> False', s.bind_card(None, 'RF') is False)
    check('no rfid -> False', s.bind_card('T-1', None) is False)


def test_upsert_idempotent_and_kind():
    s = svc()
    s.bind_card('T-1', 'RF-1', kind=KIND_MAIN)
    s.bind_card('T-2', 'RF-1', serial='SN', kind=KIND_EKP)  # та же карта, новый билет/kind
    r = s.store.find_by_rfid('RF-1')
    check('upsert overwrites abis', r['abis_code'] == 'T-2')
    check('upsert sets kind', r['kind'] == KIND_EKP)
    check('upsert sets serial', r['serial'] == 'SN')
    check('single row for card', len(s.cards_for('T-2')) == 1)


def test_cards_for():
    s = svc()
    s.bind_card('T-5', 'RF-A', kind=KIND_MAIN)
    s.bind_card('T-5', 'RF-B', kind=KIND_EKP)
    cards = s.cards_for('T-5')
    check('two cards for reader', len(cards) == 2)
    check('cards belong to reader', all(c['abis_code'] == 'T-5' for c in cards))


def test_rdr_lookup_fallback():
    calls = []
    def lookup(code):
        calls.append(code)
        return 'T-9' if code == 'LIVE' else None
    s = svc(rdr_lookup=lookup)
    check('fallback resolves to ticket',
          s.find_by_card('LIVE') == {'abis_code': 'T-9', 'rfid_code': 'LIVE'})
    check('fallback miss -> None', s.find_by_card('NOPE') is None)
    # own-реестр имеет приоритет над фолбэком
    s.bind_card('T-1', 'LOCAL')
    s.find_by_card('LOCAL')
    check('own-store hit does not call rdr_lookup', 'LOCAL' not in calls)


def test_rdr_sync_plan():
    s = svc()
    s.bind_card('T-1', 'RF-MAIN', kind=KIND_MAIN)
    s.bind_card('T-1', 'RF-EKP', kind=KIND_EKP)
    plan = s.rdr_sync_plan('T-1')
    fields = {p['field']: p['value'] for p in plan}
    check('plan field 30 = main card', fields.get('30') == 'RF-MAIN')
    check('plan field 28 = ekp card', fields.get('28') == 'RF-EKP')
    check('plan op set', all(p['op'] == 'set' for p in plan))
    check('empty reader -> empty plan', s.rdr_sync_plan('NOBODY') == [])


def test_resolve_patron():
    s = svc()
    s.bind_card('T-100', 'AABBCCDD11', kind=KIND_MAIN)
    r = s.resolve_patron('main', 'aabbccdd11')  # регистронезависимо
    check('resolve ok (CI по UID)', r['status'] == 'ok' and r['patron'] == 'T-100')
    check('resolve вернул kind карты', r['kind'] == KIND_MAIN)
    check('unknown UID -> guest', s.resolve_patron('main', 'ZZZZ')['status'] == 'unknown')
    check('пустой UID -> unknown', s.resolve_patron('main', '')['status'] == 'unknown')
    # UID НЕ усекается: длинный EPC (36) резолвится целиком
    long_epc = 'E20034120139' + 'F' * 24  # 36 симв.
    s.bind_card('T-200', long_epc, kind=KIND_EKP)
    rl = s.resolve_patron('ekp', long_epc.lower())
    check('длинный EPC резолвится без усечения', rl['status'] == 'ok' and rl['patron'] == 'T-200')
    # две карты с общим 24-символьным префиксом — РАЗНЫЕ читатели (нет коллизии)
    s.bind_card('T-201', 'E20034120139FFFFFFFFFFFF' + '0001', kind=KIND_EKP)
    s.bind_card('T-202', 'E20034120139FFFFFFFFFFFF' + '0002', kind=KIND_EKP)
    check('карта ...0001 -> T-201', s.resolve_patron('ekp', 'E20034120139FFFFFFFFFFFF0001')['patron'] == 'T-201')
    check('карта ...0002 -> T-202', s.resolve_patron('ekp', 'E20034120139FFFFFFFFFFFF0002')['patron'] == 'T-202')
    # ambiguous: живой RDR вернул >1 читателя на один UID
    s2 = svc(rdr_lookup=lambda u: ['T-A', 'T-B'])
    amb = s2.resolve_patron('main', 'DUP')
    check('коллизия RDR -> ambiguous', amb['status'] == 'ambiguous' and amb['candidates'] == ['T-A', 'T-B'])
    # rdr_lookup единичный -> ok
    s3 = svc(rdr_lookup=lambda u: 'T-LIVE')
    check('rdr единичный -> ok', s3.resolve_patron('main', 'LIVE')['patron'] == 'T-LIVE')


def test_tenant_scope():
    print('== test_tenant_scope (#7)')
    s = svc()
    s.bind_card('T-A', 'CARD-X', tenant='libA')
    check('tenant=libA резолвит свою карту',
          s.resolve_patron('main', 'CARD-X', tenant='libA')['patron'] == 'T-A')
    check('tenant=libB НЕ видит чужую карту (ПДн-изоляция)',
          s.resolve_patron('main', 'CARD-X', tenant='libB')['status'] == 'unknown')
    check('tenant=None (глобально) видит', s.resolve_patron('main', 'CARD-X')['patron'] == 'T-A')
    check('CI сохраняется в скоупе', s.resolve_patron('main', 'card-x', tenant='libA')['patron'] == 'T-A')


def main():
    for t in (test_bind_find, test_bind_guards, test_upsert_idempotent_and_kind,
              test_cards_for, test_rdr_lookup_fallback, test_rdr_sync_plan,
              test_resolve_patron, test_tenant_scope):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
