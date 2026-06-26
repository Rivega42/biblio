#!/usr/bin/env python3
"""Configuration from environment / .env (no secrets in code; .env is gitignored)."""
import os


def _envbool(value, default=False):
    """Parse a textual env flag into a bool. Unset/empty -> ``default``.
    Truthy: 1/true/yes/on; falsy: 0/false/no/off (case-insensitive)."""
    if value is None:
        return default
    v = str(value).strip().lower()
    if v == '':
        return default
    return v in ('1', 'true', 'yes', 'on')


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())


class Config:
    def __init__(self):
        here = os.path.dirname(os.path.abspath(__file__))
        load_env(os.path.join(here, '.env'))
        # IRBIS server
        self.irbis_host = os.environ.get('IRBIS_HOST', '127.0.0.1')
        self.irbis_port = int(os.environ.get('IRBIS_PORT', '6666'))
        # P0 uses one service account; per-ARM accounts come with the access suite
        self.irbis_user = (os.environ.get('IRBIS_READER_USER')
                           or os.environ.get('IRBIS_USER', 'MASTER'))
        self.irbis_pass = (os.environ.get('IRBIS_READER_PASS')
                           or os.environ.get('IRBIS_PASS', ''))
        self.workstation = os.environ.get('IRBIS_WORKSTATION', 'A')
        self.db_default = os.environ.get('IRBIS_DB_DEFAULT', 'IBIS')
        # resource spec of the database-list menu (pathcode.db.file); from connect INI
        self.db_menu = os.environ.get('IRBIS_DB_MENU', '1.&.dbnam1.mnu')
        self.timeout = float(os.environ.get('IRBIS_TIMEOUT', '8'))
        # Кодировка библиоданных сервера (записи / словарь / поиск). UTF-8 по
        # умолчанию; классический ИРБИС с CP1251-индексом → IRBIS_ENCODING=cp1251
        # (#228). read_file (ресурсы/INI) всегда CP1251 независимо от этого.
        self.irbis_encoding = os.environ.get('IRBIS_ENCODING', 'utf-8')
        # ИРБИС resilience (self-heal a stale session after a server Стоп/Старт or
        # the demo "max 3 clients" cap, without a process restart). On a connection
        # or registration failure the client re-registers and retries this many
        # times with a small backoff before the error surfaces. See core.ResilientIrbis.
        self.irbis_retries = int(os.environ.get('IRBIS_RETRIES', '2'))
        self.irbis_backoff = float(os.environ.get('IRBIS_BACKOFF', '0.2'))   # seconds, grows linearly
        # Reader-visible PUBLIC bibliographic databases (OPAC). DENY-BY-DEFAULT:
        # everything NOT in this set is treated as service / authority / ПДн (RDR,
        # RQST, CMPL/PODB/POST/VUZ, PAY, RIGHT, LICH, LOG*, RDR_ARH, COUNT, WORK,
        # ZAPR, MBA*, ATHR*/TEZ/URUB authority files, …) and is hidden from
        # /api/databases and refused (403) on search/record/etc. for guest & reader
        # sessions. Staff still reach any DB their grants allow.
        #
        # Default = IBIS only — the single public electronic catalog shipped in this
        # C:\IRBIS64 installation (confirmed against Datai/DBNAM1.MNU). A site that
        # exposes more public bibliographic bases lists them here, comma/space
        # separated, case-insensitive, e.g. IRBIS_PUBLIC_DBS="IBIS,PERIO,NTD".
        _pub = os.environ.get('IRBIS_PUBLIC_DBS', 'IBIS')
        self.public_dbs = frozenset(
            d.strip().upper() for d in _pub.replace(';', ',').replace(' ', ',').split(',') if d.strip())
        # #229: базы, поиск по которым обслуживается из НАШЕГО индекса (CatalogStore
        # FTS) в обход ИРБИС — например, чтобы обойти сломанный индекс K=. Дефолт
        # ПУСТО → весь поиск идёт через ИРБИС, поведение не меняется. Требует
        # предварительной индексации базы в CatalogStore (ops-миграция). Только
        # одиночные префиксные запросы; составные (+/*/^) пока всегда через ИРБИС.
        _own = os.environ.get('OWN_SEARCH_DBS', '')
        self.own_search_dbs = frozenset(
            d.strip().upper() for d in _own.replace(';', ',').replace(' ', ',').split(',') if d.strip())
        # Access store: sqlite path (dev) or Postgres DSN (prod) — ADR-004
        self.access_db = os.environ.get('ACCESS_DB', os.path.join(here, 'access.db'))
        self.pg_dsn = os.environ.get('PG_DSN', '')      # prod: postgresql://...
        self.app_secret = os.environ.get('APP_SECRET', 'dev-insecure-secret')
        # Reader authentication: require a password (билет + пароль), as in jirbis.
        # Default TRUE — security-critical. When a reader record carries NO password
        # field, behaviour is governed by this same flag: TRUE => login refused (401,
        # logged), FALSE => legacy ticket-only login is allowed (and logged). A reader
        # that HAS a password is always checked, regardless of the flag.
        self.require_reader_password = _envbool(
            os.environ.get('REQUIRE_READER_PASSWORD'), default=True)
        # Demo/QA reader (OFF by default). When BOTH are set, a reader may sign in to
        # the portal with this ticket+password WITHOUT an RDR record — never touches
        # IRBIS and never relaxes real-reader auth above. For pilots/demos only;
        # leave unset in a hardened deployment.
        self.test_reader_ticket = os.environ.get('TEST_READER_TICKET', '').strip()
        self.test_reader_pass = os.environ.get('TEST_READER_PASS', '')
        # App
        self.app_host = os.environ.get('APP_HOST', '127.0.0.1')
        self.app_port = int(os.environ.get('APP_PORT', '8080'))
        self.app_env = os.environ.get('APP_ENV', 'dev')
        # --- Плагины авторизации (узел 3): внешний OIDC-провайдер ------------
        # Яндекс / Сбер ID / ЕСИА / generic. ОТКЛЮЧЕНО по умолчанию
        # (oidc_provider=''). Боевые client_id/secret — только из окружения, в
        # код/репозиторий не попадают. URL'ы — из пресета access/oidc.PROVIDERS;
        # для generic-провайдера переопределяются OIDC_*_URL ниже.
        self.oidc_provider = os.environ.get('OIDC_PROVIDER', '').strip().lower()
        self.oidc_client_id = os.environ.get('OIDC_CLIENT_ID', '')
        self.oidc_client_secret = os.environ.get('OIDC_CLIENT_SECRET', '')
        self.oidc_redirect_uri = os.environ.get('OIDC_REDIRECT_URI', '')
        self.oidc_authorize_url = os.environ.get('OIDC_AUTHORIZE_URL', '')
        self.oidc_token_url = os.environ.get('OIDC_TOKEN_URL', '')
        self.oidc_userinfo_url = os.environ.get('OIDC_USERINFO_URL', '')
        self.oidc_claim = os.environ.get('OIDC_CLAIM', '').strip()
