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
from access.pgstore import make_store as make_access_store
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


# Curated cataloging worklist for a book (IBIS/PAZK) — drives DynamicField on the
# frontend. type -> control (text/menu/dict/tree/bool/authority/date); subfields nested.
# In production this comes from the server worklist (.ws/.wss) per FIELD_CATALOG.
WORKLIST_IBIS = [
    {'code': '920', 'label': 'Тип записи', 'type': 'menu', 'required': True,
     'options': ['PAZK', 'SPEC', 'NJ', 'NJP']},
    {'code': '200', 'label': 'Заглавие', 'type': 'text', 'required': True, 'subfields': [
        {'code': 'a', 'label': 'Основное заглавие', 'type': 'text'},
        {'code': 'e', 'label': 'Сведения, относящиеся к заглавию', 'type': 'text'},
        {'code': 'f', 'label': 'Первые сведения об ответственности', 'type': 'text'}]},
    {'code': '700', 'label': 'Первый автор', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Фамилия', 'type': 'text'},
        {'code': 'g', 'label': 'Имя', 'type': 'text'}]},
    {'code': '210', 'label': 'Выходные данные', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Место издания', 'type': 'text'},
        {'code': 'c', 'label': 'Издательство', 'type': 'text'},
        {'code': 'd', 'label': 'Год издания', 'type': 'text'}]},
    {'code': '215', 'label': 'Количественные характеристики', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Объём (с.)', 'type': 'text'}]},
    {'code': '10', 'label': 'ISBN', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'ISBN', 'type': 'text'}]},
    {'code': '101', 'label': 'Язык основного текста', 'type': 'menu',
     'options': ['rus', 'eng', 'fre', 'ger', 'ita', 'spa']},
    {'code': '606', 'label': 'Предметная рубрика', 'type': 'text', 'repeatable': True, 'subfields': [
        {'code': 'a', 'label': 'Рубрика', 'type': 'text'},
        {'code': 'b', 'label': 'Подрубрика', 'type': 'text'}]},
    {'code': '331', 'label': 'Аннотация', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Текст аннотации', 'type': 'text'}]},
]


class Api:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        self.irbis = SessionManager(self.cfg.irbis_host, self.cfg.irbis_port,
                                    self.cfg.workstation, self.cfg.irbis_user,
                                    self.cfg.irbis_pass, self.cfg.timeout)
        self.access = make_access_store(self.cfg)   # sqlite (default) or Postgres via ACCESS_BACKEND
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

    def _brief_item(self, db, mfn):
        """Structured result item (title/author/year/docType/availability) for cards."""
        try:
            rec = self.irbis.read_record(db, mfn)
        except IrbisError:
            return {'mfn': mfn, 'title': 'MFN %d' % mfn, 'availability': 'unknown'}
        title = sf(field(rec, '200'), 'A') or sf(field(rec, '200'), 'a')
        au = field(rec, '700')
        author = ''
        if au:
            author = (sf(au, 'A') + (', ' + sf(au, 'G') if sf(au, 'G') else '')).strip(', ')
        author = author or sf(field(rec, '200'), 'F')
        year = sf(field(rec, '210'), 'D') or sf(field(rec, '210'), 'd')
        doctype = sf(field(rec, '900'), 'T') or sf(field(rec, '900'), 'B')
        avail = 'unknown'
        hold = fields(rec, '910')
        if hold:
            st = sf(hold[0], 'A')
            avail = 'available' if st in ('0', '') else 'issued'
        return {'mfn': mfn, 'title': title or ('MFN %d' % mfn), 'author': author,
                'year': year, 'docType': doctype, 'availability': avail,
                'hasCover': any(f['tag'] == '953' for f in rec['fields'])}

    def search(self, session, db, expr, page, page_size):
        self._guard(session, 'search', db, 'read')
        count, mfns = self.irbis.search(db, expr)
        start = (page - 1) * page_size
        items = [self._brief_item(db, mfn) for mfn in mfns[start:start + page_size]]
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

    # Facet specs: (field, prefix, label, value->label map). Prefixes confirmed to exist
    # on IBIS via /api/terms (V= вид документа; J= язык ISO codes; A= автор). Values are
    # derived live from the dictionary; labels are looked up per facet, codes shown as-is.
    _FACETS = (
        ('docType', 'V', 'Вид документа', {
            '01': 'Книга (часть)', '02': 'Сборник', '03': 'Многотомник',
            '04': 'Однотомник', '05': 'Книга', '06': 'Стандарт', '08': 'Препринт',
            '09': 'Спецвид', '11': 'Журнал (часть)', '12': 'Журнал',
            'KN': 'Книга', 'DOK': 'Документ', 'FT': 'Полный текст',
            'EXT': 'Внешний ресурс', 'ZL': 'Электронный ресурс',
            'AS': 'Авторское свид.', 'DEL': 'Удалено'}),
        ('lang', 'J', 'Язык', {
            'RUS': 'Русский', 'ENG': 'Английский', 'UKR': 'Украинский',
            'KAZ': 'Казахский', 'GER': 'Немецкий', 'FRE': 'Французский',
            'SPA': 'Испанский', 'ITA': 'Итальянский', 'LAT': 'Латинский'}),
        ('author', 'A', 'Автор', None),
    )

    def _facet_count(self, db, base_expr, prefix, value):
        """Cheap COUNT for (base) intersected (AND, IRBIS '*') with one facet term.
        maxn=0 -> server returns total without reading records. Returns int or None."""
        v = value.replace('"', '')
        expr = '(%s) * "%s=%s"' % (base_expr, prefix, v)
        try:
            count, _ = self.irbis.search(db, expr, maxn=0)
        except IrbisError:
            return None
        return count

    def facets(self, session, db, base_expr, limit=8):
        """Compute facet value counts for a base query via sub-search COUNTs.
        For each facet prefix, derive candidate values from the dictionary
        (read_terms with start='<prefix>='), then count each value intersected
        with the base query. Skips values that don't co-occur (count 0) and any
        facet whose prefix yields no usable terms. Never raises on a sub-failure."""
        self._guard(session, 'search', db, 'read')
        out = []
        for fieldname, prefix, label, labelmap in self._FACETS:
            try:
                rows = self.irbis.read_terms(db, prefix + '=', max(limit * 3, 24))
            except IrbisError:
                continue
            values = []
            for _c, term in rows:
                if not term.startswith(prefix + '='):
                    continue
                val = term[len(prefix) + 1:].strip()
                if val and val not in values:
                    values.append(val)
            scored = []
            for val in values:
                if len(scored) >= limit * 2:
                    break
                cnt = self._facet_count(db, base_expr, prefix, val)
                if cnt:
                    vlabel = (labelmap or {}).get(val.upper()) or (labelmap or {}).get(val) or val
                    scored.append({'value': val, 'label': vlabel, 'count': cnt})
            scored.sort(key=lambda x: x['count'], reverse=True)
            scored = scored[:limit]
            if scored:
                out.append({'field': fieldname, 'prefix': prefix,
                            'label': label, 'values': scored})
        return 200, ok({'db': db, 'expr': base_expr, 'facets': out})

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

    # service/authority DBs not meant for public reader search
    _SERVICE_DBS = {'RDR', 'RQST', 'CMPL', 'PODB', 'POST', 'VISIT', 'LOG', 'COUNT'}

    def databases(self, session):
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        txt = self.irbis.read_file(self.cfg.db_menu)
        lines = [x.strip() for x in txt.splitlines() if x.strip() and x.strip() != '*****']
        items = []
        for i in range(0, len(lines) - 1, 2):
            code = lines[i]
            name = lines[i + 1]
            if not code:
                continue
            public = code not in self._SERVICE_DBS and not code.upper().startswith('ATHR')
            items.append({'code': code, 'name': name, 'public': public})
        return 200, ok({'items': items, 'default': self.cfg.db_default})

    def worklist(self, session, db):
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        return 200, ok({'db': db, 'fields': WORKLIST_IBIS})

    def save_record(self, session, db, mfn, body):
        """Create (mfn=0) or overwrite a record. Guarded by record.write + audited.
        body: {fields:[{tag, value}]} where value already carries ^subfields."""
        self._guard(session, 'record.write', db, 'write')
        version = 0
        if mfn > 0:
            try:
                version = int((self.irbis.read_record(db, mfn).get('version') or 0))
            except (IrbisError, ValueError):
                version = 0
        lines = ['%d#0' % mfn, '0#%d' % version]
        for f in (body.get('fields') or []):
            tag = str(f.get('tag', '')).strip()
            val = (f.get('value') or '').replace('\n', ' ').strip()
            if tag and val:
                lines.append('%s#%s' % (tag, val))
        r = self.irbis.update_record(db, lines)
        assigned = mfn
        if r.data and '#' in r.data[0] and r.data[0].split('#')[0].isdigit():
            assigned = int(r.data[0].split('#')[0])
        self.access.audit(session['actor'], 'record.write', db, assigned, 'ok', {'created': mfn == 0})
        return 200, ok({'db': db, 'mfn': assigned, 'created': mfn == 0, 'returnCode': r.return_code})

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
        # bearer header for API calls; <img>/<a> can't set headers, so also accept ?t=token
        token = self._bearer(headers) or (query.get('t', [None])[0] if query else None)
        session = self._session(token)
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
            if method == 'GET' and path == '/api/facets':
                db = query.get('db', [self.cfg.db_default])[0]
                expr = build_expr(query)
                if not expr:
                    return 400, err('bad_request', 'q or expr required')
                return self.facets(session, db, expr)
            if method == 'POST' and path == '/api/order':
                return self.order(session, body or {})
            if method == 'GET' and path == '/api/me/cabinet':
                return self.cabinet(session)
            if method == 'GET' and path == '/api/databases':
                return self.databases(session)
            if method == 'GET' and len(parts) == 3 and parts[0] == 'api' and parts[1] == 'worklist':
                return self.worklist(session, parts[2])
            if method == 'POST' and len(parts) == 4 and parts[0] == 'api' and parts[1] == 'record':
                return self.save_record(session, parts[2], int(parts[3]), body or {})
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


def sf(f, code):
    """Case-insensitive subfield lookup; '' if absent."""
    if not f:
        return ''
    d = f['subfields']
    return d.get(code) or d.get(code.lower()) or d.get(code.upper()) or ''


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
