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
        self.timeout = float(os.environ.get('IRBIS_TIMEOUT', '8'))
        # App
        self.app_host = os.environ.get('APP_HOST', '127.0.0.1')
        self.app_port = int(os.environ.get('APP_PORT', '8080'))
        self.app_env = os.environ.get('APP_ENV', 'dev')
