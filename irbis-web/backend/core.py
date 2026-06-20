#!/usr/bin/env python3
"""Framework-agnostic API core. One Api.route() is shared by the stdlib server
(server.py, runs on any Python) and the aiohttp app (app_aiohttp.py, Python 3.12).

Pipeline: authn (bearer token -> session) -> authorize (grant function x db x level)
-> IRBIS call -> normalize -> audit (write/admin). Server -3338 -> 403.
"""
import secrets
import threading
from urllib.parse import unquote_to_bytes

from config import Config
from irbis import SessionManager
from irbis.client import IrbisError
from irbis.parser import field, fields
from access.store import AccessStore
from access.authz import authorize, READER_GRANTS, GUEST_GRANTS
from access.seed import seed


def ok(data):
    return {'ok': True, 'data': data}


def err(code, message):
    return {'ok': False, 'error': {'code': code, 'message': message}}


class Raw:
    """Binary response (e.g. cover image)."""
    def __init__(self, data, content_type):
        self.data, self.content_type = data, content_type


class Api:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        self.irbis = SessionManager(self.cfg.irbis_host, self.cfg.irbis_port,
                                    self.cfg.workstation, self.cfg.irbis_user,
                                    self.cfg.irbis_pass, self.cfg.timeout)
        self.access = AccessStore(self.cfg.access_db)
        seed(self.access)                      # idempotent dev seed
        self._sessions = {}
        self._lock = threading.Lock()

    # ---- session helpers ----
    def _new_session(self, kind, actor, grants, **extra):
        token = secrets.token_urlsafe(24)
        sess = {'kind': kind, 'actor': actor, 'grants': grants}
        sess.update(extra)
        with self._lock:
            self._sessions[token] = sess
        return token, sess

    def _session(self, token):
        with self._lock:
            return self._sessions.get(token)

    @staticmethod
    def _bearer(headers):
        h = headers.get('authorization') or headers.get('Authorization') or ''
        return h[7:].strip() if h.lower().startswith('bearer ') else None

    def _guard(self, session, function, db, level):
        """Authorize or raise Denied. Audits denials for write/admin."""
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        if not authorize(session['grants'], function, db, level):
            if level in ('write', 'admin'):
                self.access.audit(session['actor'], function, db, None, 'denied')
            raise Denied(403, 'forbidden', 'grant required: %s/%s/%s' % (function, db, level))

    # ---- endpoints ----
    def health(self):
        return ok({'server': '%s:%d' % (self.cfg.irbis_host, self.cfg.irbis_port),
                   'version': self.irbis.server_version(),
                   'db': self.cfg.db_default,
                   'maxmfn': self.irbis.max_mfn(self.cfg.db_default)})

    def auth_guest(self):
        token, _ = self._new_session('guest', 'guest', GUEST_GRANTS)
        return 200, ok({'token': token, 'kind': 'guest'})

    def auth_staff(self, body):
        acc = self.access.authenticate(body.get('login', ''), body.get('password', ''))
        if not acc:
            return 401, err('auth_failed', 'invalid credentials')
        grants = self.access.effective_grants(acc['id'])
        token, _ = self._new_session('staff', acc['login'], grants, account_id=acc['id'])
        self.access.audit(acc['login'], 'auth.staff', None, None, 'ok')
        return 200, ok({'token': token, 'kind': 'staff',
                        'login': acc['login'], 'name': acc['full_name'], 'grants': grants})

    def auth_reader(self, body):
        ticket = (body.get('ticket', '') or '').strip()
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        try:
            _count, mfns = self.irbis.search('RDR', '"RI=%s"' % ticket)
        except IrbisError:
            mfns = []
        if not mfns:
            return 401, err('auth_failed', 'reader not found')
        rec = self.irbis.read_record('RDR', mfns[0])
        name_f = field(rec, '10') or field(rec, '11')
        name = (name_f or {}).get('value', '') if name_f else ''
        token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS, rdr_mfn=mfns[0])
        return 200, ok({'token': token, 'kind': 'reader', 'name': name, 'mfn': mfns[0]})

    def search(self, session, db, expr, page, page_size):
        self._guard(session, 'search', db, 'read')
        count, mfns = self.irbis.search(db, expr)
        start = (page - 1) * page_size
        items = []
        for mfn in mfns[start:start + page_size]:
            try:
                brief = self.irbis.format_record(db, mfn, '@brief')
            except IrbisError:
                brief = ''
            items.append({'mfn': mfn, 'brief': brief})
        return 200, ok({'db': db, 'expr': expr, 'total': count,
                        'page': page, 'pageSize': page_size, 'items': items})

    def record(self, session, db, mfn):
        self._guard(session, 'record.read', db, 'read')
        rec = self.irbis.read_record(db, mfn)
        try:
            rec['brief'] = self.irbis.format_record(db, mfn, '@brief')
        except IrbisError:
            rec['brief'] = ''
        rec['db'] = db
        rec['hasCover'] = any(f['tag'] == '953' for f in rec['fields'])
        return 200, ok(rec)

    def render(self, session, db, mfn, fmt):
        self._guard(session, 'record.read', db, 'read')
        return 200, ok({'db': db, 'mfn': mfn, 'fmt': fmt,
                        'rendered': self.irbis.format_record(db, mfn, fmt)})

    def terms(self, session, db, start, count):
        self._guard(session, 'terms', db, 'read')
        rows = self.irbis.read_terms(db, start, count)
        return 200, ok({'db': db, 'start': start,
                        'terms': [{'count': c, 'term': t} for c, t in rows]})

    def cover(self, session, db, mfn):
        """Embedded cover from field 953 (^B is URL-encoded image bytes)."""
        self._guard(session, 'record.read', db, 'read')
        rec = self.irbis.read_record(db, mfn)
        f = field(rec, '953')
        if not f or 'B' not in f['subfields']:
            return 404, err('not_found', 'no embedded cover')
        data = unquote_to_bytes(f['subfields']['B'])
        kind = (f['subfields'].get('A') or 'JPG').upper()
        ctype = {'JPG': 'image/jpeg', 'JPEG': 'image/jpeg', 'PNG': 'image/png',
                 'GIF': 'image/gif'}.get(kind, 'application/octet-stream')
        return 200, Raw(data, ctype)

    def resource(self, session, db, spec_file):
        """Read a server text resource (menus/PFT) via FILE 'L'. pathcode 3 = db menus."""
        self._guard(session, 'file', db, 'read')
        text = self.irbis.read_file('3.%s.%s' % (db, spec_file))
        return 200, ok({'db': db, 'file': spec_file, 'text': text})

    def order(self, session, body):
        db = body.get('db', self.cfg.db_default)
        mfn = body.get('mfn')
        self._guard(session, 'order', db, 'write')
        # TODO(order): materialize a real RQST request record + reserve a copy/cell on the
        # live server (needs RQST worklist + reader id). For P0: validate + audit + queue marker.
        self.access.audit(session['actor'], 'order', db, mfn, 'ok', {'queued': True})
        return 200, ok({'db': db, 'mfn': mfn, 'status': 'queued',
                        'note': 'P0: заказ принят (запись RQST — TODO боевой интеграции)'})

    def cabinet(self, session):
        if not session or session['kind'] != 'reader':
            raise Denied(403, 'forbidden', 'reader session required')
        self._guard(session, 'cabinet', '*', 'read')
        rec = self.irbis.read_record('RDR', session['rdr_mfn'])
        loans = [{'value': f['value'], 'subfields': f['subfields']}
                 for f in fields(rec, '40')]
        name_f = field(rec, '10') or field(rec, '11')
        return 200, ok({'mfn': session['rdr_mfn'],
                        'name': (name_f or {}).get('value', ''),
                        'loans': loans, 'loanCount': len(loans)})

    # ---- dispatcher ----
    def route(self, method, path, query, body, headers):
        """Return (status, payload) where payload is dict | Raw | None."""
        path = path.rstrip('/') or '/'
        if method == 'OPTIONS':
            return 204, None
        session = self._session(self._bearer(headers))
        try:
            if method == 'POST' and path == '/api/auth/guest':
                return self.auth_guest()
            if method == 'POST' and path == '/api/auth/staff':
                return self.auth_staff(body or {})
            if method == 'POST' and path == '/api/auth/reader':
                return self.auth_reader(body or {})
            if method == 'GET' and path == '/api/health':
                return 200, self.health()
            parts = path.strip('/').split('/')
            if method == 'GET' and path == '/api/search':
                db = query.get('db', [self.cfg.db_default])[0]
                expr = build_expr(query)
                if not expr:
                    return 400, err('bad_request', 'q or expr required')
                page = max(1, int(query.get('page', ['1'])[0]))
                ps = min(50, max(1, int(query.get('pageSize', ['20'])[0])))
                return self.search(session, db, expr, page, ps)
            if method == 'GET' and path == '/api/terms':
                db = query.get('db', [self.cfg.db_default])[0]
                start = query.get('start', [''])[0]
                cnt = min(50, max(1, int(query.get('count', ['15'])[0])))
                return self.terms(session, db, start, cnt)
            if method == 'POST' and path == '/api/order':
                return self.order(session, body or {})
            if method == 'GET' and path == '/api/me/cabinet':
                return self.cabinet(session)
            if len(parts) == 4 and parts[0] == 'api' and parts[1] in ('record', 'render', 'cover'):
                db, mfn = parts[2], int(parts[3])
                if parts[1] == 'record':
                    return self.record(session, db, mfn)
                if parts[1] == 'cover':
                    return self.cover(session, db, mfn)
                return self.render(session, db, mfn, query.get('fmt', ['@brief'])[0])
            if len(parts) == 4 and parts[0] == 'api' and parts[1] == 'resource':
                return self.resource(session, parts[2], parts[3])
            return 404, err('not_found', 'unknown route')
        except Denied as d:
            return d.status, err(d.code, d.message)
        except IrbisError as e:
            return (403 if e.code == -3338 else 502), err('irbis', 'backend error')
        except ValueError:
            return 400, err('bad_request', 'invalid parameter')
        except Exception:
            return 500, err('internal', 'internal error')

    def close(self):
        self.irbis.close()


class Denied(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def build_expr(query):
    if query.get('expr'):
        return query['expr'][0]
    q = (query.get('q', [''])[0] or '').strip().replace('"', '')
    if not q:
        return None
    prefix = (query.get('prefix', ['K'])[0] or 'K').strip().upper()
    if prefix in ('A', 'T') and not q.endswith('$'):
        q += '$'
    return '"%s=%s"' % (prefix, q)
