#!/usr/bin/env python3
"""End-to-end HTTP test against a running server (default :8080). Read-only + guarded write.
Run the server first, then: py irbis-web/backend/tests/e2e.py"""
import json
import os
import urllib.request

BASE = os.environ.get('BASE', 'http://127.0.0.1:8080')
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'e2e_results.txt'),
           'w', encoding='utf-8')


def call(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    if data:
        req.add_header('Content-Type', 'application/json')
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, r.read(), r.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get('Content-Type', '')


def j(method, path, token=None, body=None):
    st, raw, _ = call(method, path, token, body)
    try:
        return st, json.loads(raw.decode('utf-8'))
    except Exception:
        return st, {'_raw': raw[:80].decode('latin1')}


def p(*a):
    print(*a, file=OUT)


def main():
    # guest auth
    st, r = j('POST', '/api/auth/guest')
    gtok = r['data']['token']
    p('guest auth: %s kind=%s' % (st, r['data']['kind']))

    st, r = j('GET', '/api/health', gtok)
    p('health: %s version=%s maxmfn=%s' % (st, r['data']['version'], r['data']['maxmfn']))

    st, r = j('GET', '/api/search?prefix=K&q=Android&pageSize=3', gtok)
    p('search K=Android: %s total=%s items=%s' % (st, r['data']['total'], len(r['data']['items'])))

    st, r = j('GET', '/api/terms?start=K%3DAND&count=5', gtok)
    p('terms K=AND: %s -> %s' % (st, [t['term'] for t in r['data']['terms'][:4]]))

    st, r = j('GET', '/api/record/IBIS/1', gtok)
    p('record IBIS/1: %s fields=%s hasCover=%s' % (st, len(r['data']['fields']), r['data']['hasCover']))

    # cover image
    st, raw, ctype = call('GET', '/api/cover/IBIS/1', gtok)
    p('cover IBIS/1: %s ctype=%s bytes=%s magic=%s'
      % (st, ctype, len(raw), raw[:3].hex() if raw else ''))

    # authz: order without token -> 401; guest -> 403
    st, r = j('POST', '/api/order', None, {'db': 'IBIS', 'mfn': 1})
    p('order no-token: %s (expect 401)' % st)
    st, r = j('POST', '/api/order', gtok, {'db': 'IBIS', 'mfn': 1})
    p('order as guest: %s (expect 403)' % st)

    # staff auth (librarian: reader-service+cataloger) -> order allowed, admin.users denied
    st, r = j('POST', '/api/auth/staff', None, {'login': 'librarian', 'password': 'librarian'})
    ltok = r.get('data', {}).get('token')
    p('staff auth librarian: %s grants=%d' % (st, len(r.get('data', {}).get('grants', []))))
    st, r = j('POST', '/api/order', ltok, {'db': 'IBIS', 'mfn': 1})
    p('order as librarian: %s status=%s (expect 200)' % (st, r.get('data', {}).get('status')))

    # admin auth -> full rights
    st, r = j('POST', '/api/auth/staff', None, {'login': 'admin', 'password': 'admin'})
    atok = r.get('data', {}).get('token')
    p('staff auth admin: %s grants=%d' % (st, len(r.get('data', {}).get('grants', []))))
    st, r = j('POST', '/api/order', atok, {'db': 'IBIS', 'mfn': 1})
    p('order as admin: %s status=%s (expect 200)' % (st, r.get('data', {}).get('status')))

    # bad staff creds
    st, r = j('POST', '/api/auth/staff', None, {'login': 'admin', 'password': 'nope'})
    p('staff bad creds: %s (expect 401)' % st)

    p('\nDONE')
    OUT.close()


if __name__ == '__main__':
    main()
