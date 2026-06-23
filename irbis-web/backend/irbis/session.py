#!/usr/bin/env python3
"""Thread-safe IRBIS session manager.

One long-lived registered session (client_id) is shared across HTTP requests and
serialized with a lock (the protocol increments query_id and the demo server caps
concurrent clients, so a single reused session is the safe P0 choice). Auto-(re)connect
on first use or after a dropped connection.
"""
import threading
import socket
from .client import IrbisClient, IrbisError


class SessionManager:
    def __init__(self, host, port, workstation, user, password, timeout=8.0, encoding='utf-8'):
        self._lock = threading.Lock()
        self._client = IrbisClient(host, port, workstation, timeout, encoding)
        self._creds = (user, password)
        self.connected = False

    def _ensure(self):
        if self.connected:
            return
        r = self._client.connect(*self._creds)
        if r.return_code != 0:
            raise IrbisError(r.return_code, 'register failed (workstation/creds?)')
        self.connected = True

    def _call(self, fn):
        with self._lock:
            try:
                self._ensure()
                return fn(self._client)
            except (ConnectionError, OSError, socket.error):
                # dropped connection -> re-register once and retry
                self.connected = False
                self._ensure()
                return fn(self._client)

    # public, thread-safe operations
    def server_version(self):
        with self._lock:
            self._ensure()
            return self._client.server_version

    def max_mfn(self, db):
        return self._call(lambda c: c.max_mfn(db))

    def search(self, db, expr, first=1, maxn=0):
        return self._call(lambda c: c.search(db, expr, first=first, maxn=maxn))

    def read_record(self, db, mfn):
        return self._call(lambda c: c.read_record(db, mfn))

    def format_record(self, db, mfn, pft='@brief'):
        return self._call(lambda c: c.format_record(db, mfn, pft))

    def read_terms(self, db, start, count=20):
        return self._call(lambda c: c.read_terms(db, start, count))

    def read_file(self, spec):
        return self._call(lambda c: c.read_file(spec))

    def update_record(self, db, record_lines, lock=0, actualize=1):
        return self._call(lambda c: c.update_record(db, record_lines, lock, actualize))

    def close(self):
        with self._lock:
            try:
                self._client.disconnect()
            finally:
                self.connected = False
