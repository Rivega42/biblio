#!/usr/bin/env python3
"""Единая идентичность читатель↔сотрудник (узел 3 MVP-3): стор связи +
роуты link-reader / view-as-reader / unlink. БЕЗ СЕТИ (демо-читатель для
проверки билета без ИРБИС). Standalone: python tests/test_identity_link.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.identity_store import IdentityStore  # noqa: E402

_fails = []


def check(name, cond):
    print(('  ok  ' if cond else 'FAIL ') + name)
    if not cond:
        _fails.append(name)


def store_checks():
    print('-- identity_store: staff<->reader link')
    s = IdentityStore(':memory:')
    check('reader_for_staff empty', s.reader_for_staff('lib') is None)
    s.link('lib', 'T55')
    check('reader_for_staff after link', s.reader_for_staff('lib') == 'T55')
    check('staff_for_reader reverse', s.staff_for_reader('T55') == 'lib')
    s.link('lib', 'T99')
    check('re-link replaces ticket', s.reader_for_staff('lib') == 'T99')
    check('unlink removes', s.unlink('lib') == 1 and s.reader_for_staff('lib') is None)


def _api():
    os.environ['JWT_SECRET'] = 'identity-link-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    os.environ['IDENTITY_DB'] = ':memory:'
    # демо-читатель: проверка билета+пароля без ИРБИС (auth_reader demo-путь).
    os.environ['TEST_READER_TICKET'] = 'T777'
    os.environ['TEST_READER_PASS'] = 'rpass'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis.read_file = lambda spec: ''
    api.irbis.max_mfn = lambda db: 0
    api.irbis.search = lambda db, expr: (0, [])
    return api


def flow_checks():
    print('-- identity routes: link-reader / view-as-reader / unlink')
    api = _api()
    stok, _ = api._new_session('staff', 'lib1',
                               [{'function': 'record.read', 'db': '*', 'level': 'read'}],
                               tenant='public', account_id=1)
    SH = {'authorization': 'Bearer ' + stok}

    # 1. привязать свой билет (верный демо-билет+пароль)
    st, p = api.route('POST', '/api/staff/link-reader', {},
                      {'ticket': 'T777', 'password': 'rpass'}, SH)
    check('link-reader ok',
          st == 200 and p['data']['linked'] is True and p['data']['ticket'] == 'T777')
    check('store has link', api.identity_store.reader_for_staff('lib1') == 'T777')

    # 2. неверный пароль билета → 401 (владение не доказано)
    st, _ = api.route('POST', '/api/staff/link-reader', {},
                      {'ticket': 'T777', 'password': 'WRONG'}, SH)
    check('link wrong pass -> 401', st == 401)

    # 3. посмотреть как читатель → читательская сессия своего билета
    st, p = api.route('POST', '/api/staff/view-as-reader', {}, {}, SH)
    check('view-as-reader -> reader token',
          st == 200 and p['data']['kind'] == 'reader' and p['data']['ticket'] == 'T777' and 'token' in p['data'])

    # 4. отвязать → view-as-reader больше нельзя (404)
    st, _ = api.route('POST', '/api/staff/unlink-reader', {}, {}, SH)
    check('unlink ok', st == 200)
    st, _ = api.route('POST', '/api/staff/view-as-reader', {}, {}, SH)
    check('view-as-reader after unlink -> 404', st == 404)

    # 5. без staff-сессии → 401
    st, _ = api.route('POST', '/api/staff/view-as-reader', {}, {}, {})
    check('view-as-reader no staff -> 401', st == 401)
    st, _ = api.route('POST', '/api/staff/link-reader', {}, {'ticket': 'T1'}, {})
    check('link no staff -> 401', st == 401)


def run():
    store_checks()
    flow_checks()
    print('PASS' if not _fails else ('FAILED: %d' % len(_fails)))
    return 0 if not _fails else 1


if __name__ == '__main__':
    sys.exit(run())
