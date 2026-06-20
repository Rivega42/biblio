#!/usr/bin/env python3
"""Our own catalog server (PoC) — implements the SAME API contract as backend/, but
serves bibliographic data from OUR store (sqlite/FTS, migrated from IRBIS), and serves
the same built frontend. Proves the seam: the web client runs unchanged on our server.

  py irbis-web/server-own/migrate.py            # fill own.db from IRBIS
  py irbis-web/server-own/app.py                # http://127.0.0.1:8081
"""
import os
import json
import posixpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from store import OwnStore

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.normpath(os.path.join(HERE, '..', 'frontend', 'dist'))
STORE = OwnStore(os.environ.get('OWN_DB', os.path.join(HERE, 'own.db')))
DEFAULT_DB = os.environ.get('OWN_DEFAULT_DB', 'IBIS')
PORT = int(os.environ.get('OWN_PORT', '8081'))

_CT = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
       '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
       '.svg': 'image/svg+xml', '.map': 'application/json'}


def ok(data):
    return {'ok': True, 'data': data}


def build_expr(q):
    if q.get('expr'):
        return None, None, q['expr'][0]
    return (q.get('prefix', ['K'])[0], (q.get('q', [''])[0] or ''), None)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, payload, ctype='application/json; charset=utf-8'):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = (payload or '').encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b'', 'text/plain')

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == '/api/auth/guest':
            return self._send(200, ok({'token': 'own-guest', 'kind': 'guest'}))
        if u.path == '/api/order':
            return self._send(200, ok({'status': 'queued', 'note': 'own-server PoC'}))
        return self._send(404, {'ok': False, 'error': {'code': 'not_found', 'message': '-'}})

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        q = parse_qs(u.query)
        try:
            if p == '/' or p == '':
                return self._serve_dist('/index.html')
            if p.startswith('/assets/'):
                return self._serve_dist(p)
            if p == '/api/health':
                return self._send(200, ok({'server': 'own-server (sqlite)', 'version': 'own-0.1',
                                           'db': DEFAULT_DB, 'maxmfn': STORE.count(DEFAULT_DB)}))
            if p == '/api/databases':
                items = [{'code': d['code'], 'name': d['name'], 'public': bool(d['public'])} for d in STORE.databases()]
                return self._send(200, ok({'items': items, 'default': DEFAULT_DB}))
            if p == '/api/search':
                db = q.get('db', [DEFAULT_DB])[0]
                prefix, term, expr = build_expr(q)
                page = max(1, int(q.get('page', ['1'])[0]))
                size = min(50, max(1, int(q.get('pageSize', ['20'])[0])))
                total, items = STORE.search(db, prefix, term, expr, page, size)
                return self._send(200, ok({'db': db, 'expr': expr or (prefix + '=' + (term or '')),
                                           'total': total, 'page': page, 'pageSize': size, 'items': items}))
            if p == '/api/terms':
                db = q.get('db', [DEFAULT_DB])[0]
                start = q.get('start', [''])[0]
                cnt = min(50, max(1, int(q.get('count', ['8'])[0])))
                return self._send(200, ok({'db': db, 'start': start, 'terms': STORE.terms(db, start, cnt)}))
            parts = p.strip('/').split('/')
            if len(parts) == 4 and parts[0] == 'api' and parts[1] in ('record', 'cover'):
                db, mfn = parts[2], int(parts[3])
                if parts[1] == 'record':
                    rec = STORE.record(db, mfn)
                    return self._send(200, ok(rec)) if rec else self._send(404, {'ok': False, 'error': {'code': 'not_found', 'message': '-'}})
                data = STORE.cover(db, mfn)
                return self._send(200, data, 'image/jpeg') if data else self._send(404, b'', 'text/plain')
            if p == '/api/me/cabinet':
                return self._send(200, ok({'mfn': 0, 'name': 'Гость', 'loans': [], 'loanCount': 0}))
            return self._send(404, {'ok': False, 'error': {'code': 'not_found', 'message': '-'}})
        except Exception:
            return self._send(500, {'ok': False, 'error': {'code': 'internal', 'message': '-'}})

    def _serve_dist(self, rel):
        rel = posixpath.normpath('/' + rel.lstrip('/')).lstrip('/')
        full = os.path.join(DIST, *rel.split('/'))
        if not os.path.isfile(full):
            return self._send(404, b'build not found - run npm run build in frontend/', 'text/plain')
        ext = os.path.splitext(full)[1].lower()
        with open(full, 'rb') as f:
            self._send(200, f.read(), _CT.get(ext, 'application/octet-stream'))


def main():
    print('OWN catalog server on http://127.0.0.1:%d (store: %s, db %s, %d records)'
          % (PORT, STORE.path, DEFAULT_DB, STORE.count(DEFAULT_DB)))
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()


if __name__ == '__main__':
    main()
