#!/usr/bin/env python3
"""Configurable bibliographic encoding (#228).

The IRBIS client historically hard-coded UTF-8 for both the response decode and
the request encode. A classic ИРБИС install keeps its inverted index + records in
CP1251, so UTF-8 decoding garbled the dictionary/records and UTF-8-encoded query
terms never matched the CP1251 index (cyrillic search -> 0). Encoding is now
configurable (env IRBIS_ENCODING; Config -> SessionManager -> IrbisClient ->
Response/_execute). read_file (resources) stays CP1251 regardless (uses raw bytes).

Standalone:  py tests/test_encoding.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irbis.client import Response, IrbisClient

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def encoding_checks():
    print('-- irbis encoding (#228): configurable bibliographic encoding')
    cyr = 'ЧЕХОВ'
    # Minimal frame: 11 leading fields (return_code slot etc.) then the term as data.
    frame = ('\r\n'.join([''] * 11) + cyr).encode('cp1251')
    check('Response(cp1251) decodes cyrillic correctly', Response(frame, 'cp1251').lines[-1] == cyr)
    check('Response(utf-8) garbles cp1251 bytes (the bug)', Response(frame, 'utf-8').lines[-1] != cyr)
    check('Response default encoding stays utf-8', Response(b'x').lines[0] == 'x')
    check('IrbisClient stores encoding=cp1251', IrbisClient(encoding='cp1251').encoding == 'cp1251')
    check('IrbisClient default encoding is utf-8', IrbisClient().encoding == 'utf-8')
    # Config reads IRBIS_ENCODING from env, default utf-8.
    import importlib
    import config as _c
    os.environ['IRBIS_ENCODING'] = 'cp1251'
    importlib.reload(_c)
    check('Config reads IRBIS_ENCODING=cp1251', _c.Config().irbis_encoding == 'cp1251')
    del os.environ['IRBIS_ENCODING']
    importlib.reload(_c)
    check('Config default encoding is utf-8', _c.Config().irbis_encoding == 'utf-8')


if __name__ == '__main__':
    encoding_checks()
    print('\nENCODING: %d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)
