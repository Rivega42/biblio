#!/usr/bin/env python3
"""Generic OpenID Connect / OAuth2 client (узел 3 — плагины авторизации).

Stdlib-only (urllib): стандартный authorization-code flow + userinfo. Превращает
внешнего провайдера (Яндекс / Сбер ID / ЕСИА / любой OIDC) в набор claim'ов о
пользователе. МАППИНГ claim→учётка/билет и выпуск сессии — НЕ здесь, а в роут-
хендлере (MVP-2b): этот модуль знает только протокол, не модель Biblio.

ОТКЛЮЧЁН по умолчанию: боевой провайдер задаётся `OIDC_PROVIDER` + кредами в
окружении (в код не попадают). Провайдер-специфика (URL'ы, имя claim, scope) — в
``PROVIDERS``; нестандартные нюансы помечены (`nonstandard`).

HTTP-примитивы (`_post_form`/`_get_json`) вынесены модульным уровнем НАМЕРЕННО —
юнит-тест подменяет их фейками и проверяет поток без сети.
"""
import json
import secrets
import urllib.parse
import urllib.request

# Пресеты провайдеров — только СТАНДАРТНЫЙ OIDC-поток (authorize/token/userinfo).
PROVIDERS = {
    'yandex': {
        'authorize': 'https://oauth.yandex.ru/authorize',
        'token': 'https://oauth.yandex.ru/token',
        'userinfo': 'https://login.yandex.ru/info?format=json',
        'scope': 'login:email login:info',
        'claim': 'default_email',
        'label': 'Яндекс ID',
    },
    'sber': {  # Сбер ID
        'authorize': 'https://online.sberbank.ru/CSAFront/oidc/authorize.do',
        'token': 'https://api.sberbank.ru/ru/prod/tokens/v2/oidc',
        'userinfo': 'https://api.sberbank.ru/ru/prod/sberbankid/v2.1/userInfo',
        'scope': 'openid email',
        'claim': 'email',
        'label': 'Сбер ID',
    },
    'esia': {  # Госуслуги / ЕСИА
        'authorize': 'https://esia.gosuslugi.ru/aas/oauth2/ac',
        'token': 'https://esia.gosuslugi.ru/aas/oauth2/te',
        'userinfo': 'https://esia.gosuslugi.ru/rs/prns',
        'scope': 'openid fullname snils email',
        'claim': 'snils',
        'label': 'Госуслуги (ЕСИА)',
        # ВНИМАНИЕ: ЕСИА НЕстандартна — параметры authorize/token подписываются
        # RSA (client_secret = PKCS7-подпись scope+timestamp+clientId+state), плюс
        # свой формат timestamp. Боевое подключение доберём в MVP-2b с реальными
        # кредами/сертификатом библиотеки. Пресет даёт URL'ы и имя claim.
        'nonstandard': 'RSA-signed request params; wire in MVP-2b with real creds',
    },
    'generic': {  # любой стандартный OIDC — URL'ы задаются из конфига
        'authorize': '', 'token': '', 'userinfo': '',
        'scope': 'openid email', 'claim': 'email', 'label': 'OIDC',
    },
}


def provider_config(name, overrides=None):
    """Конфиг провайдера = пресет + непустые overrides (URL'ы/claim из окружения)."""
    base = dict(PROVIDERS.get((name or '').lower()) or {})
    if overrides:
        base.update({k: v for k, v in overrides.items() if v})
    return base


def new_state():
    """CSRF-state для authorize→callback (хранить в сессии/куке и сверять)."""
    return secrets.token_urlsafe(24)


def build_authorize_url(pcfg, client_id, redirect_uri, state):
    """URL, на который редиректим пользователя (шаг 1 code-flow)."""
    auth = pcfg.get('authorize') or ''
    if not auth:
        raise ValueError('provider has no authorize endpoint')
    q = urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': pcfg.get('scope', 'openid email'),
        'state': state,
    })
    return auth + ('&' if '?' in auth else '?') + q


def _post_form(url, data, timeout=10):
    """POST application/x-www-form-urlencoded → JSON (подменяется в тестах)."""
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded',
                 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get_json(url, headers, timeout=10):
    """GET → JSON (подменяется в тестах)."""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def exchange_code(pcfg, client_id, client_secret, code, redirect_uri, timeout=10):
    """Шаг 2: обменять authorization code на токены (server-to-server, TLS)."""
    return _post_form(pcfg['token'], {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
    }, timeout=timeout)


def fetch_userinfo(pcfg, access_token, timeout=10):
    """Шаг 3: забрать claim'ы пользователя по access_token (без проверки подписи
    id_token — claim'ы берём с userinfo-эндпойнта по TLS-бэкчэнелу)."""
    return _get_json(pcfg['userinfo'],
                     {'Authorization': 'Bearer ' + access_token,
                      'Accept': 'application/json'}, timeout=timeout)


def claim_value(pcfg, userinfo):
    """Значение ключевого claim'а провайдера (email/snils/...) — ключ маппинга."""
    return str((userinfo or {}).get(pcfg.get('claim', 'email')) or '').strip()
