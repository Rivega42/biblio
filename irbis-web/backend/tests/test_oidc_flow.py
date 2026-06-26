#!/usr/bin/env python3
"""OIDC login/bind flow (узел 3 MVP-2b): binding-стор + роуты start/callback/bind.

БЕЗ СЕТИ: HTTP провайдера мокается подменой access.oidc._post_form/_get_json.
Проверяет ключевое свойство безопасности: НЕпривязанная внешняя личность НЕ даёт
доступа (отдаёт handoff), привязка возможна ТОЛЬКО из читательской сессии.
Standalone:  python tests/test_oidc_flow.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import oidc as _oidc  # noqa: E402
from access.oidc_store import OidcStore  # noqa: E402
from access.authz import READER_GRANTS  # noqa: E402

_fails = []


def check(name, cond):
    print(('  ok  ' if cond else 'FAIL ') + name)
    if not cond:
        _fails.append(name)


def store_checks():
    print('-- oidc_store: привязки')
    s = OidcStore(':memory:')
    check('ticket_for empty -> None', s.ticket_for('yandex', 'sub1') is None)
    s.link('yandex', 'sub1', 'T100')
    check('ticket_for after link', s.ticket_for('yandex', 'sub1') == 'T100')
    s.link('yandex', 'sub1', 'T200')
    check('re-bind redirects ticket', s.ticket_for('yandex', 'sub1') == 'T200')
    check('list_for_ticket shows binding',
          any(x['subject'] == 'sub1' for x in s.list_for_ticket('T200')))
    check('unlink removes',
          s.unlink('yandex', 'T200') == 1 and s.ticket_for('yandex', 'sub1') is None)


def _api_oidc():
    os.environ['JWT_SECRET'] = 'oidc-flow-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    os.environ['OIDC_DB'] = ':memory:'
    os.environ['OIDC_PROVIDER'] = 'yandex'
    os.environ['OIDC_CLIENT_ID'] = 'CID'
    os.environ['OIDC_CLIENT_SECRET'] = 'SECRET'
    os.environ['OIDC_REDIRECT_URI'] = 'https://lib.example/oidc/callback'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis.read_file = lambda spec: ''
    api.irbis.max_mfn = lambda db: 0
    api.irbis.search = lambda db, expr: (0, [])
    return api


def flow_checks():
    print('-- oidc routes: providers / start / callback / bind')
    api = _api_oidc()
    _oidc._post_form = lambda u, d, timeout=10: {'access_token': 'AT-1'}
    _oidc._get_json = lambda u, h, timeout=10: {'default_email': 'reader@ya.ru'}

    st, p = api.route('GET', '/api/auth/oidc/providers', {}, None, {})
    check('providers lists yandex',
          st == 200 and p['data']['providers'][0]['provider'] == 'yandex')

    st, p = api.route('GET', '/api/auth/oidc/start', {'intent': ['login']}, None, {})
    check('start -> url+state',
          st == 200 and p['data']['url'].startswith('https://oauth.yandex.ru/authorize?'))
    state = p['data']['state']

    # 1) вход ДО привязки -> unbound + handoff (НЕ пускает!)
    st, p = api.route('POST', '/api/auth/oidc/callback', {}, {'code': 'C1', 'state': state}, {})
    check('callback unbound (no access)',
          st == 200 and p['data']['bound'] is False and 'handoff' in p['data'] and 'token' not in p['data'])
    handoff = p['data']['handoff']

    # 2) привязка без читательской сессии -> 401
    st, _ = api.route('POST', '/api/auth/oidc/bind', {}, {'handoff': handoff}, {})
    check('bind without reader -> 401', st == 401)

    # 3) читатель вошёл (билет+пароль) -> привязал handoff
    rtok, _ = api._new_session('reader', 'RI=T777', READER_GRANTS, tenant='public', rdr_mfn=1)
    RH = {'authorization': 'Bearer ' + rtok}
    st, p = api.route('POST', '/api/auth/oidc/bind', {}, {'handoff': handoff}, RH)
    check('bind links identity', st == 200 and p['data']['linked'] is True)

    # 4) повторный вход -> bound -> читательская сессия
    st, p = api.route('GET', '/api/auth/oidc/start', {'intent': ['login']}, None, {})
    state2 = p['data']['state']
    st, p = api.route('POST', '/api/auth/oidc/callback', {}, {'code': 'C2', 'state': state2}, {})
    check('callback bound -> reader token',
          st == 200 and p['data']['bound'] is True and 'token' in p['data'] and p['data'].get('kind') == 'reader')

    # 5) поддельный state -> 400
    st, _ = api.route('POST', '/api/auth/oidc/callback', {}, {'code': 'C', 'state': 'garbage'}, {})
    check('forged state -> 400', st == 400)

    # 6) start intent=bind без читательской сессии -> 401
    st, _ = api.route('GET', '/api/auth/oidc/start', {'intent': ['bind']}, None, {})
    check('start bind without reader -> 401', st == 401)


def run():
    store_checks()
    flow_checks()
    print('PASS' if not _fails else ('FAILED: %d' % len(_fails)))
    return 0 if not _fails else 1


if __name__ == '__main__':
    sys.exit(run())
