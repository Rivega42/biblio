#!/usr/bin/env python3
"""Multi-field default search expression (#245).

The portal used to default to the K= (keyword) index, which is unreliable on the
СПб ГТБ server (dictionary shows postings but search returns 0). The default is now
a multi-field OR across title + author + keywords, uppercased to match the
dictionary form, so a cyrillic query returns hits regardless of the K= index state.

Standalone:  py tests/test_search_expr.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import build_expr

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def search_expr_checks():
    print('-- build_expr multi-field default (#245)')
    che = ''.join(chr(x) for x in [0x447, 0x435, 0x445, 0x43e, 0x432])  # 'чехов' lowercase
    CHE = che.upper()
    allx = build_expr({'q': [che], 'prefix': ['ALL']})
    check('ALL -> uppercased OR across T/A/K',
          allx == '"T=%s$" + "A=%s$" + "K=%s$"' % (CHE, CHE, CHE))
    check('no prefix defaults to multi-field', build_expr({'q': [che]}) == allx)
    check('sentinel * also multi-field', build_expr({'q': [che], 'prefix': ['*']}) == allx)
    check('single prefix T still single', build_expr({'q': [che], 'prefix': ['T']}).startswith('"T=%s' % che))
    check('explicit expr passthrough', build_expr({'expr': ['"A=X"']}) == '"A=X"')
    check('empty q -> None', build_expr({'q': ['']}) is None)


if __name__ == '__main__':
    search_expr_checks()
    print('\nSEARCH-EXPR: %d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)
