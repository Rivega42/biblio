#!/usr/bin/env python3
"""Configuration from environment / .env (no secrets in code; .env is gitignored)."""
import os


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
        # Access store: sqlite path (dev) or Postgres DSN (prod) — ADR-004
        self.access_db = os.environ.get('ACCESS_DB', os.path.join(here, 'access.db'))
        self.pg_dsn = os.environ.get('PG_DSN', '')      # prod: postgresql://...
        self.app_secret = os.environ.get('APP_SECRET', 'dev-insecure-secret')
        # App
        self.app_host = os.environ.get('APP_HOST', '127.0.0.1')
        self.app_port = int(os.environ.get('APP_PORT', '8080'))
        self.app_env = os.environ.get('APP_ENV', 'dev')
