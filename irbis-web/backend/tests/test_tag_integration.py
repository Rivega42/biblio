#!/usr/bin/env python3
"""Интеграция reader_agent ↔ tag_codec (узел #272, Reader Agent).

Проверяет, что настольный считыватель (ReaderAgentService) корректно работает с
реальным кодеком ISO 28560-2 (tag_codec): чтение тега декодирует itemId,
программирование тега кодирует блок, который декодируется обратно. Транспорт —
крошечный in-memory фейк (без железа).

    py -3.12 tests/test_tag_integration.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import tag_codec as tc
from access.reader_agent import ReaderAgentService, ReaderAgentError

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1; print('  ok  ', name)
    else:
        FAIL[0] += 1; print('  FAIL', name)


class MemTag:
    """Фейк-транспорт: хранит один блок тега в памяти + флаг EAS."""
    def __init__(self, uid='E0040100DEADBEEF', block=None):
        self.uid = uid
        self.block = block
        self.eas = None
    def read_uid(self):
        return self.uid
    def read_block(self):
        return self.block
    def write_block(self, data):
        self.block = data
        return True
    def set_eas(self, on):
        self.eas = bool(on)
        return True


def test_read_real_tag():
    block = tc.encode_block({tc.OID_PRIMARY_ITEM_ID: '2001001'})
    ra = ReaderAgentService(transport=MemTag(block=block), codec=tc)
    r = ra.read_tag()
    check('uid surfaced', bool(r['uid']))
    check('itemId decoded from real tag', str(r['itemId']) == '2001001')


def test_program_then_read():
    tag = MemTag(block=None)
    ra = ReaderAgentService(transport=tag, codec=tc)
    out = ra.program_tag('3005777')
    check('program_tag ok', out['ok'] is True and out['written'] > 0)
    # перечитать запрограммированный блок реальным кодеком
    check('written block decodes back', tc.decode_block(tag.block).get(tc.OID_PRIMARY_ITEM_ID) == '3005777')
    r = ra.read_tag()
    check('read after program', str(r['itemId']) == '3005777')


def test_eas_direction():
    tag = MemTag(block=b'')
    ra = ReaderAgentService(transport=tag, codec=tc)
    ra.issue_prepare('1')   # выдача → EAS off
    check('issue -> EAS off', tag.eas is False)
    ra.return_prepare('1')  # возврат → EAS on
    check('return -> EAS on', tag.eas is True)


def test_empty_item_raises():
    ra = ReaderAgentService(transport=MemTag(), codec=tc)
    try:
        ra.program_tag('')
        check('empty itemId raises', False)
    except ReaderAgentError:
        check('empty itemId raises', True)


def main():
    for t in (test_read_real_tag, test_program_then_read, test_eas_direction,
              test_empty_item_raises):
        print('==', t.__name__); t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
