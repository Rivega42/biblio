#!/usr/bin/env python3
"""Юнит-тест generic OIDC-клиента (access/oidc.py, узел 3 — плагины авторизации).

БЕЗ СЕТИ: HTTP-примитивы (_post_form/_get_json) подменяются фейками, проверяется
протокольный поток (authorize URL → exchange code → userinfo → claim) и пресеты
провайдеров. Standalone-скрипт в стиле CI-гейта (python tests/test_oidc.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import oidc  # noqa: E402

_fails = []


def check(name, cond):
    print(('  ok ' if cond else 'FAIL ') + name)
    if not cond:
        _fails.append(name)


def run():
    print('-- oidc: пресеты провайдеров')
    y = oidc.provider_config('yandex')
    check('yandex preset has endpoints',
          y['authorize'] and y['token'] and y['userinfo'])
    check('yandex claim is default_email', y['claim'] == 'default_email')
    check('esia flagged nonstandard (RSA)', 'nonstandard' in oidc.provider_config('esia'))
    check('unknown provider -> empty dict', oidc.provider_config('nope') == {})
    g = oidc.provider_config('generic', {
        'authorize': 'https://idp/auth', 'token': 'https://idp/tok',
        'userinfo': 'https://idp/ui', 'claim': 'email'})
    check('generic overrides applied', g['authorize'] == 'https://idp/auth' and g['claim'] == 'email')
    check('generic override ignores empties',
          oidc.provider_config('generic', {'authorize': ''})['authorize'] == '')

    print('-- oidc: authorize URL (шаг 1)')
    state = oidc.new_state()
    check('state is non-trivial', isinstance(state, str) and len(state) >= 16)
    url = oidc.build_authorize_url(y, 'CID', 'https://x/cb', state)
    check('authorize url base', url.startswith('https://oauth.yandex.ru/authorize?'))
    check('authorize url has response_type=code', 'response_type=code' in url)
    check('authorize url has client_id', 'client_id=CID' in url)
    check('authorize url has encoded redirect', 'redirect_uri=https%3A%2F%2Fx%2Fcb' in url)
    check('authorize url has state', 'state=' + state in url)
    try:
        oidc.build_authorize_url(oidc.provider_config('generic'), 'C', 'r', 's')
        check('empty authorize endpoint raises', False)
    except ValueError:
        check('empty authorize endpoint raises', True)

    print('-- oidc: code exchange + userinfo (шаги 2-3, мок HTTP)')
    captured = {}

    def fake_post(u, data, timeout=10):
        captured['token_url'] = u
        captured['data'] = data
        return {'access_token': 'AT-123', 'token_type': 'bearer', 'expires_in': 3600}

    def fake_get(u, headers, timeout=10):
        captured['userinfo_url'] = u
        captured['auth_header'] = headers.get('Authorization')
        return {'default_email': 'user@yandex.ru', 'login': 'user', 'id': '42'}

    oidc._post_form = fake_post
    oidc._get_json = fake_get

    tok = oidc.exchange_code(y, 'CID', 'SECRET', 'CODE-xyz', 'https://x/cb')
    check('exchange hits token endpoint', captured['token_url'] == y['token'])
    check('exchange sends grant_type=authorization_code',
          captured['data']['grant_type'] == 'authorization_code')
    check('exchange sends the code', captured['data']['code'] == 'CODE-xyz')
    check('exchange returns access_token', tok['access_token'] == 'AT-123')

    ui = oidc.fetch_userinfo(y, tok['access_token'])
    check('userinfo hits userinfo endpoint', captured['userinfo_url'] == y['userinfo'])
    check('userinfo sends bearer token', captured['auth_header'] == 'Bearer AT-123')
    check('userinfo returns claims', ui['login'] == 'user')

    check('claim_value picks provider claim (default_email)',
          oidc.claim_value(y, ui) == 'user@yandex.ru')
    check('claim_value empty on missing claim', oidc.claim_value({'claim': 'nope'}, ui) == '')

    print('PASS' if not _fails else ('FAILED: %d' % len(_fails)))
    return 0 if not _fails else 1


if __name__ == '__main__':
    sys.exit(run())
