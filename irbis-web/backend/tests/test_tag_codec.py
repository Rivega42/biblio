#!/usr/bin/env python3
"""tag_codec tests — кодек RFID-метки ISO 28560-2 (Reader Agent).

    py -3.12 tests/test_tag_codec.py  -> ok ... + "N passed, M failed" + код

Покрыто: round-trip OID 1 (штрихкод как integer / octet / hex); многоэлементный
блок; набивка-терминатор; битый precursor → TagCodecError; 5/6/7-бит текст;
константы AFI/EAS и хелпер security_state.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.tag_codec import (
    encode_element, decode_element, encode_block, decode_block,
    security_state, TagCodecError,
    COMPACTION_INTEGER, COMPACTION_HEX, COMPACTION_OCTET,
    COMPACTION_5BIT, COMPACTION_6BIT, COMPACTION_7BIT,
    OID_PRIMARY_ITEM_ID, OID_OWNER_LIBRARY,
    AFI_SECURE, AFI_FREE, AFI_NONE, EAS_ON, EAS_OFF,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


def test_element_integer():
    enc = encode_element(OID_PRIMARY_ITEM_ID, 30001234, COMPACTION_INTEGER)
    oid, val, nxt = decode_element(enc)
    check('integer oid round-trips', oid == OID_PRIMARY_ITEM_ID)
    check('integer value round-trips', val == 30001234)
    check('integer next_offset = len', nxt == len(enc))


def test_element_octet_barcode():
    bc = '30500123456789'
    enc = encode_element(OID_PRIMARY_ITEM_ID, bc, COMPACTION_OCTET)
    oid, val, nxt = decode_element(enc)
    check('octet barcode round-trips as str', val == bc and oid == 1)


def test_element_hex():
    enc = encode_element(OID_PRIMARY_ITEM_ID, 'DEADBEEF', COMPACTION_HEX)
    oid, val, nxt = decode_element(enc)
    check('hex round-trips uppercase', val == 'DEADBEEF')


def test_block_multi():
    elems = {
        OID_PRIMARY_ITEM_ID: ('30500123456789', COMPACTION_OCTET),
        OID_OWNER_LIBRARY: ('RU-MOSGB', COMPACTION_OCTET),
    }
    blob = encode_block(elems)
    out = decode_block(blob)
    check('block primary id round-trips', out[OID_PRIMARY_ITEM_ID] == '30500123456789')
    check('block owner round-trips', out[OID_OWNER_LIBRARY] == 'RU-MOSGB')
    check('block element count', len(out) == 2)


def test_block_default_compaction():
    # int → integer, str → octet (эвристика по умолчанию)
    blob = encode_block({OID_PRIMARY_ITEM_ID: 12345, 2: 'AB'})
    out = decode_block(blob)
    check('default int -> integer', out[OID_PRIMARY_ITEM_ID] == 12345)
    check('default str -> octet', out[2] == 'AB')


def test_block_padding_terminator():
    blob = encode_block({OID_PRIMARY_ITEM_ID: ('XYZ', COMPACTION_OCTET)})
    out = decode_block(blob + b'\x00\x00\x00\x00')  # хвостовая набивка нулями
    check('padding stops decode', out == {OID_PRIMARY_ITEM_ID: 'XYZ'})


def test_nbit_text():
    # 5/6-бит компакция со смещением +0x40 кодирует подмножество '@'..'_'
    # (заглавные буквы); это то, что подтверждено декомпиляцией (§3 доки).
    enc5 = encode_element(2, 'ABCXYZ', COMPACTION_5BIT)
    _, v5, _ = decode_element(enc5)
    check('5-bit text round-trips', v5.startswith('ABCXYZ'))
    enc6 = encode_element(2, 'HELLO', COMPACTION_6BIT)
    _, v6, _ = decode_element(enc6)
    check('6-bit text round-trips', v6.startswith('HELLO'))
    # 7-бит — полный ISO 646 IRV (без смещения), включая цифры/дефис/строчные
    enc7 = encode_element(2, 'Lib-42', COMPACTION_7BIT)
    _, v7, _ = decode_element(enc7)
    check('7-bit text round-trips', v7.startswith('Lib-42'))


def test_malformed():
    try:
        decode_element(b'\x01\x05AB')  # длина 5, payload 2 байта → corrupt
        check('truncated payload raises', False)
    except TagCodecError:
        check('truncated payload raises', True)
    try:
        decode_element(b'\x00\x00')  # compaction=0 → corrupt precursor
        check('zero-compaction precursor raises', False)
    except TagCodecError:
        check('zero-compaction precursor raises', True)
    try:
        decode_element(b'')  # пустой ввод
        check('empty input raises', False)
    except TagCodecError:
        check('empty input raises', True)


def test_afi_eas():
    check('AFI_SECURE != AFI_FREE', AFI_SECURE != AFI_FREE)
    check('AFI_NONE is zero', AFI_NONE == 0x00)
    check('EAS_ON/OFF distinct', EAS_ON != EAS_OFF)
    sec = security_state(AFI_SECURE)
    check('secure state has eas on', sec['secure'] and sec['eas'] == EAS_ON
          and sec['label'] == 'secured')
    free = security_state(AFI_FREE)
    check('free state has eas off', (not free['secure']) and free['eas'] == EAS_OFF
          and free['label'] == 'free')


def test_extended_header():
    # расширенный заголовок (бит7=1): offset present, байт1=offset, байт2=длина
    payload = b'\x99'  # integer payload single octet
    blob = bytes([0x80 | (COMPACTION_INTEGER << 4) | 1, 0x02, 0x01]) + payload
    oid, val, nxt = decode_element(blob)
    check('extended header decodes oid', oid == 1)
    check('extended header decodes value', val == 0x99 and nxt == len(blob))


def main():
    for t in (test_element_integer, test_element_octet_barcode, test_element_hex,
              test_block_multi, test_block_default_compaction,
              test_block_padding_terminator, test_nbit_text, test_malformed,
              test_afi_eas, test_extended_header):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
