#!/usr/bin/env python3
"""Synchronous IRBIS64 client — production-shaped, derived empirically in Prohod B.

Wire protocol (see docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md):
  * ONE TCP connection per request; session persists via client_id.
  * Request frame: "<bodyLen>\\n" + lines("\\n"):
        command, workstation, command, client_id, query_id, password, username, "","",""  [+args]
  * Response frame: lines("\\r\\n"); return_code at index 10; data from index 11.
  * Encodings: bibliographic data = UTF-8; INI/resources = CP1251.
This module is transport-agnostic: an aiohttp/async port only swaps `_execute`.
"""
import socket
import random
from .parser import parse_record

DELIM = '\x1f\x1e'   # IRBIS record field delimiter on the wire


class IrbisError(Exception):
    def __init__(self, code, message=''):
        super().__init__('IRBIS error %s: %s' % (code, message))
        self.code = code
        self.message = message


class Response:
    """Parsed server response frame."""
    def __init__(self, raw: bytes, encoding: str = 'utf-8'):
        self.raw = raw
        self.lines = raw.decode(encoding, 'replace').split('\r\n')
        self.return_code = None
        if len(self.lines) > 10 and self.lines[10].lstrip('-').isdigit():
            self.return_code = int(self.lines[10])
        self.data = self.lines[11:] if len(self.lines) > 11 else []

    def ok(self):
        return self.return_code is not None and self.return_code >= 0


class IrbisClient:
    def __init__(self, host='127.0.0.1', port=6666, workstation='A', timeout=8.0, encoding='utf-8'):
        self.host, self.port = host, port
        self.workstation = workstation
        self.timeout = timeout
        self.encoding = encoding   # bibliographic data encoding (UTF-8 default; CP1251 for classic ИРБИС, #228)
        self.user = self.password = ''
        self.client_id = 100000 + random.randint(0, 899999)
        self.query_id = 0
        self.connected = False
        self.server_version = ''

    # ---- transport ----
    def _execute(self, command, args=None):
        self.query_id += 1
        lines = [command, self.workstation, command, str(self.client_id),
                 str(self.query_id), self.password, self.user, '', '', '']
        if args:
            lines += [a if isinstance(a, str) else str(a) for a in args]
        body = ('\n'.join(lines) + '\n').encode(self.encoding)
        packet = (str(len(body)) + '\n').encode('ascii') + body
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        s.sendall(packet)
        data = b''
        try:
            while True:
                ch = s.recv(65536)
                if not ch:
                    break          # server closed -> response complete
                data += ch
        except socket.timeout:
            pass
        finally:
            try:
                s.close()
            except Exception:
                pass
        return Response(data, self.encoding)

    # ---- session ----
    def connect(self, user, password):
        self.user, self.password = user, password
        r = self._execute('A', [user, password])
        if r.return_code == 0:
            self.connected = True
            if len(r.lines) > 4:
                self.server_version = r.lines[4]
        return r

    def disconnect(self):
        if self.connected:
            try:
                self._execute('B', [self.user])
            finally:
                self.connected = False

    def nop(self):
        return self._execute('N')

    # ---- read ----
    def max_mfn(self, db):
        r = self._execute('O', [db])
        return r.return_code

    def search(self, db, expr, fmt='', first=1, maxn=0):
        """Return (count, [mfn,...]). expr must be a valid IRBIS query, e.g. '"K=...".'"""
        r = self._execute('K', [db, expr, '0', str(first), str(maxn), fmt])
        if r.return_code is not None and r.return_code < 0:
            raise IrbisError(r.return_code, 'search failed')
        count = int(r.data[0]) if r.data and r.data[0].lstrip('-').isdigit() else 0
        mfns = []
        for line in r.data[1:]:
            head = line.split('#', 1)[0]
            if head.isdigit():
                mfns.append(int(head))
        return count, mfns

    def read_record(self, db, mfn):
        """Return a parsed record dict (mfn/status/version/guid/fields[])."""
        r = self._execute('C', [db, str(mfn), '0'])
        if r.return_code is not None and r.return_code < 0:
            raise IrbisError(r.return_code, 'read failed')
        return parse_record(r.data)

    def format_record(self, db, mfn, pft='@brief'):
        """Server-side PFT rendering of one record. Returns text."""
        r = self._execute('G', [db, pft, '1', str(mfn)])
        if r.return_code is not None and r.return_code < 0:
            raise IrbisError(r.return_code, 'format failed')
        return '\n'.join(x for x in r.data if x).strip()

    # codes that still carry a valid term list (exact term may not exist)
    _TERM_OK = (0, -202, -203, -204)

    def read_terms(self, db, start, count=20):
        """Dictionary terms from `start` (command 'H'). Returns [(posting_count, term), ...]."""
        r = self._execute('H', [db, start, str(count)])
        if r.return_code is not None and r.return_code not in self._TERM_OK:
            raise IrbisError(r.return_code, 'read_terms failed')
        terms = []
        for line in r.data:
            if '#' in line:
                cnt, term = line.split('#', 1)
                terms.append((int(cnt) if cnt.isdigit() else 0, term))
        return terms

    def read_file(self, spec):
        """Read a text resource (command 'L'). spec = '<pathcode>.<db>.<file>'
        (e.g. '2.IBIS.brief.pft', '3.IBIS.kv.mnu'). Returns decoded text (CP1251), '' if absent.
        Server separates internal lines with \\x1F\\x1E; content follows the 10-line preamble."""
        r = self._execute('L', [spec])
        # round-trip via latin1 to recover exact bytes, then decode CP1251
        segs = r.raw.decode('latin1').split('\r\n')
        content = '\r\n'.join(segs[10:]).encode('latin1')
        return content.decode('cp1251', 'replace').replace('\x1f\x1e', '\n').strip()

    # ---- write (guarded; use only with write grants) ----
    def update_record(self, db, record_lines, lock=0, actualize=1):
        """record_lines: list of 'tag#value' (mfn#status and 0#version prepended by caller)."""
        rec = DELIM.join(record_lines)
        r = self._execute('D', [db, str(lock), str(actualize), rec])
        if r.return_code is not None and r.return_code < 0:
            raise IrbisError(r.return_code, 'update failed')
        return r
