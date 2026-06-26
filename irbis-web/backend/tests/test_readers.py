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


def main():
    for t in (test_bind_find, test_bind_guards, test_upsert_idempotent_and_kind,
              test_cards_for, test_rdr_lookup_fallback):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
