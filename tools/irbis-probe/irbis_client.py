#!/usr/bin/env python3
"""Minimal IRBIS64 client adapter (Prohod B), derived empirically from the live
:6666 wire protocol (see docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md).

Model: ONE TCP connection per request; session via client_id.
Request frame:  "<bodyLen>\n" + lines("\n"):
    command, workstation, command, client_id, query_id, password, username, "","",""  [+args]
Response frame: lines("\r\n"): command, client_id, query_id, size, [version@register],
    reserved..., return_code(index 10), data(index 11+)
Encodings: bibliographic data = UTF-8; INI/resources = CP1251(ANSI).
"""
import socket, random

class Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.lines = raw.decode('utf-8', 'replace').split('\r\n')
        try:
            self.return_code = int(self.lines[10]) if len(self.lines) > 10 and self.lines[10].lstrip('-').isdigit() else None
        except Exception:
            self.return_code = None
        self.data = self.lines[11:] if len(self.lines) > 11 else []

class IrbisClient:
    def __init__(self, host='127.0.0.1', port=6666, workstation='A'):
        self.host, self.port, self.workstation = host, port, workstation
        self.user = self.password = ''
        self.client_id = 100000 + random.randint(0, 899999)
        self.query_id = 0
        self.connected = False
        self.ini = ''

    def _execute(self, command, args=None, recv_timeout=8.0):
        self.query_id += 1
        lines = [command, self.workstation, command, str(self.client_id),
                 str(self.query_id), self.password, self.user, '', '', '']
        if args:
            lines += [a if isinstance(a, str) else str(a) for a in args]
        body = ('\n'.join(lines) + '\n').encode('utf-8')
        packet = (str(len(body)) + '\n').encode('ascii') + body
        s = socket.create_connection((self.host, self.port), timeout=recv_timeout)
        s.settimeout(recv_timeout)
        s.sendall(packet)
        data = b''
        try:
            while True:
                ch = s.recv(65536)
                if not ch:
                    break
                data += ch
        except socket.timeout:
            pass
        finally:
            try: s.close()
            except Exception: pass
        return Response(data)

    # ---- session ----
    def connect(self, user, password):
        self.user, self.password = user, password
        r = self._execute('A', [user, password])
        if r.return_code == 0:
            self.connected = True
            # INI profile is ANSI(CP1251); it starts at data[1:] (after the '30' line)
            self.ini = b'\r\n'.join(p.encode('latin1', 'ignore') for p in r.data).decode('cp1251', 'replace')
        return r

    def disconnect(self):
        if self.connected:
            r = self._execute('B', [self.user])
            self.connected = False
            return r

    def nop(self):
        return self._execute('N')

    # ---- read ----
    def max_mfn(self, db):
        return self._execute('O', [db]).return_code

    def search(self, db, expr, fmt='', first=1, maxn=0):
        r = self._execute('K', [db, expr, '0', str(first), str(maxn), fmt])
        mfns = []
        # data[0] = count, then lines "mfn#<result>"
        for line in r.data[1:]:
            if '#' in line:
                left = line.split('#', 1)[0]
                if left.isdigit():
                    mfns.append(int(left))
        count = None
        if r.data and r.data[0].isdigit():
            count = int(r.data[0])
        return count, mfns, r

    def read_record(self, db, mfn):
        r = self._execute('C', [db, str(mfn), '0'])
        fields = []
        for line in r.data:
            if '#' in line:
                tag, val = line.split('#', 1)
                fields.append((tag, val))
        return fields, r

    def format_record(self, db, mfn, fmt):
        # FORMAT command 'G': db, format, count=1, mfn
        r = self._execute('G', [db, fmt, '1', str(mfn)])
        return r
