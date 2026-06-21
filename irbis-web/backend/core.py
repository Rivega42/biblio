#!/usr/bin/env python3
"""Framework-agnostic API core. One Api.route() is shared by the stdlib server
(server.py, runs on any Python) and the aiohttp app (app_aiohttp.py, Python 3.12).

Pipeline: authn (bearer token -> session) -> authorize (grant function x db x level)
-> IRBIS call -> normalize -> audit (write/admin). Server -3338 -> 403.
"""
import os
import random
import socket
import threading
import time
from urllib.parse import unquote_to_bytes

from config import Config
from irbis import SessionManager
from irbis.client import IrbisError
from irbis.parser import field, fields
from access.store import AccessStore
from access.pgstore import make_store as make_access_store, PgAccessStore
from access.authz import authorize, READER_GRANTS, GUEST_GRANTS
from access.seed import seed
from access import jwt as _jwt
from access import entitlements
from access import flk
from access import notifications as _notifications
from access import circulation as _circulation
from access.holds import HoldService
from access.shelves import ShelfService
from access.social import SocialService
from access import acquisition as _acquisition
from access import bookprovision as _bookprovision
from access.catalog import CatalogStore

# Default tenant slug when running single-tenant / sqlite dev (no control plane).
DEFAULT_TENANT = os.environ.get('DEFAULT_TENANT', 'public')

# Map an authz function to the functional MODULE that must be licensed for it
# (issue #101 entitlements). Functions not listed are not module-gated (always
# allowed if the grant passes). Entitlements are a SEPARATE axis from grants:
# even with a valid grant, a request to a disabled module is refused.
FUNCTION_MODULE = {
    'search': 'opac', 'record.read': 'opac', 'terms': 'opac', 'file': 'opac',
    'record.write': 'cataloging', 'record.delete': 'cataloging', 'cat.gbl': 'cataloging',
    'order': 'reader', 'cabinet': 'reader',
    'circ.issue': 'circulation', 'circ.return': 'circulation',
    # АРМ Комплектатор (acquisition): order/receive/КСУ — staff-only, module-gated.
    # acq.receipt already existed for the receipt write; acq.read gates the КСУ /
    # order-status reads on the same 'acquisition' module.
    'acq.receipt': 'acquisition', 'acq.read': 'acquisition',
    # Книгообеспеченность (book-provision, ВУЗ): связка writes + Кко reads, gated on
    # the 'bookprovision' module (issue #101 licensing).
    'bp.write': 'bookprovision', 'bp.read': 'bookprovision',
    'admin.db': 'admin', 'admin.users': 'admin',
}


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


# Generic fallback worklist for a base that has no curated worklist (anything but
# IBIS/PAZK). The minimal set every bibliographic record carries — заглавие /
# автор / выходные данные — so a new editor still renders a usable form. A real
# deployment derives the per-base worklist from the server .ws/.wss (FIELD_CATALOG).
WORKLIST_GENERIC = [
    {'code': '200', 'label': 'Заглавие', 'type': 'text', 'required': True, 'subfields': [
        {'code': 'a', 'label': 'Основное заглавие', 'type': 'text'},
        {'code': 'f', 'label': 'Сведения об ответственности', 'type': 'text'}]},
    {'code': '700', 'label': 'Первый автор', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Фамилия', 'type': 'text'},
        {'code': 'g', 'label': 'Имя', 'type': 'text'}]},
    {'code': '210', 'label': 'Выходные данные', 'type': 'text', 'subfields': [
        {'code': 'a', 'label': 'Место издания', 'type': 'text'},
        {'code': 'c', 'label': 'Издательство', 'type': 'text'},
        {'code': 'd', 'label': 'Год издания', 'type': 'text'}]},
]


# IRBIS return codes that mean "this client_id is no longer a valid session" —
# observed after a server Стоп/Старт, when the demo "max 3 clients" cap drops us,
# or when the registered session otherwise lapses (see WIRE_PROTOCOL §5/§11 and
# DLL_API_EXTRACTED IC_reg/IC_unreg). On any of these the right cure is to throw
# the stale client_id away, re-register, and retry — NOT to surface the error.
#   -3337  client already registered (a re-register collided with a lingering session)
#   -3338  CLIENT_NOT_ALLOWED (no ARM access for this session — also raised when the
#          server forgot us after a restart and rejects the unknown client_id)
# The range guard (-3300..-3349) catches the sibling -33xx session codes the wire
# recon flagged as "to be enumerated", so a server restart self-heals even if the
# exact code isn't in our table yet. Data-level codes (-140 missing MFN, -603
# deleted record, -202..-204 terms) are NOT here — those are real answers, not a
# dead session, and must propagate unchanged.
_STALE_SESSION_CODES = frozenset((-3337, -3338))


def _is_stale_session(code):
    if code in _STALE_SESSION_CODES:
        return True
    return code is not None and -3349 <= code <= -3300


class ResilientIrbis:
    """Self-healing wrapper around :class:`irbis.SessionManager`.

    A long-running backend keeps one registered ИРБИС session (client_id) and
    opens a fresh TCP per command (the protocol's one-connection-per-request
    model). That session goes STALE when the server is restarted (Стоп/Старт) or
    the demo "max 3 clients" cap evicts us: every subsequent command then fails —
    a socket error, or an IRBIS -33xx "not a valid session" return code — and
    historically only a process restart recovered it.

    This wrapper makes recovery automatic. Every call is funnelled through
    ``_resilient``: on a connection error OR a stale-session return code it drops
    the dead client_id (forcing a brand-new client_id so a re-register can't
    collide with a lingering server-side session as -3337), re-registers, and
    retries — up to ``retries`` times with a small linear backoff. A transient,
    a Стоп/Старт, or the client cap thus heals WITHOUT a process restart.

    It also records reachability: ``last_error`` / ``last_ok_ts`` and a cheap
    ``ping()`` back the ``irbis`` block of /api/health. The underlying
    SessionManager is already lock-serialized; an extra lock here guards the
    reset+health bookkeeping so concurrent requests re-register at most once.
    """

    # Methods proxied 1:1 to the SessionManager, each wrapped with retry.
    _PROXIED = ('max_mfn', 'search', 'read_record', 'format_record',
                'read_terms', 'read_file', 'update_record')

    def __init__(self, sm, retries=2, backoff=0.2):
        self._sm = sm
        self._retries = max(0, int(retries))
        self._backoff = max(0.0, float(backoff))
        self._lock = threading.Lock()
        self.last_error = None
        self.last_ok_ts = None
        for name in self._PROXIED:
            setattr(self, name, self._make_proxy(name))

    def _make_proxy(self, name):
        def proxy(*args, **kwargs):
            return self._resilient(name, lambda: getattr(self._sm, name)(*args, **kwargs))
        proxy.__name__ = name
        return proxy

    def _reset_session(self):
        """Discard the stale registration so the next call re-registers.

        Marks the SessionManager unconnected and rotates the underlying client's
        client_id, so the re-register starts a genuinely new server session
        instead of colliding with the lingering old one (-3337)."""
        with self._lock:
            try:
                self._sm.connected = False
                client = getattr(self._sm, '_client', None)
                if client is not None:
                    client.connected = False
                    # Fresh client_id => the server sees a new session, dodging -3337.
                    client.client_id = 100000 + random.randint(0, 899999)
            except Exception:
                pass

    def _resilient(self, label, fn):
        attempts = self._retries + 1
        last_exc = None
        for i in range(attempts):
            try:
                result = fn()
                self.last_error = None
                self.last_ok_ts = time.time()
                return result
            except (ConnectionError, OSError, socket.error) as e:
                last_exc = e
                self.last_error = '%s: %s' % (label, e)
                self._reset_session()
            except IrbisError as e:
                # A dead-session code self-heals; a data-level code (missing MFN,
                # deleted record, real query error) is a genuine answer — re-raise.
                if not _is_stale_session(e.code):
                    raise
                last_exc = e
                self.last_error = '%s: irbis %s' % (label, e.code)
                self._reset_session()
            if i < attempts - 1 and self._backoff:
                time.sleep(self._backoff * (i + 1))   # linear backoff
        # Exhausted retries: surface as an IrbisError so route()'s handler maps it.
        if isinstance(last_exc, IrbisError):
            raise last_exc
        raise IrbisError(-1, 'irbis unreachable after %d attempts: %s' % (attempts, last_exc))

    def server_version(self):
        return self._resilient('server_version', self._sm.server_version)

    def ping(self):
        """Cheap reachability probe for /api/health. Returns True if a trivial
        round-trip (server_version, which forces a register) succeeds; records
        last_error and returns False otherwise — never raises."""
        try:
            self.server_version()
            return True
        except Exception as e:
            self.last_error = 'ping: %s' % e
            return False

    def health(self):
        """Reachability snapshot for /api/health."""
        return {'lastError': self.last_error,
                'lastOkTs': self.last_ok_ts,
                'retries': self._retries}

    def close(self):
        try:
            self._sm.close()
        except Exception:
            pass


class Api:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        self.irbis = ResilientIrbis(
            SessionManager(self.cfg.irbis_host, self.cfg.irbis_port,
                           self.cfg.workstation, self.cfg.irbis_user,
                           self.cfg.irbis_pass, self.cfg.timeout),
            retries=self.cfg.irbis_retries, backoff=self.cfg.irbis_backoff)
        self.access = make_access_store(self.cfg)   # sqlite (default) or Postgres via ACCESS_BACKEND
        seed(self.access)                      # idempotent dev seed
        # Seeding engine (A5, #188): seed the single-tenant 'public' store's vocabs
        # in dev so /api/vocab has data without a control plane. Idempotent; best-effort
        # (a store without the vocab tables — older schema — must not break startup).
        try:
            from access import seed_vocab
            seed_vocab.seed_vocabularies(self.access, from_catalog=False)
        except Exception:
            pass
        # JWT signing secret from env (non-secret dev default ok). The token is a
        # plain signed bearer string — the frontend (api.ts) needs no change.
        self.jwt_secret = os.environ.get('JWT_SECRET', 'dev-insecure-jwt-secret')
        self.jwt_ttl = int(os.environ.get('JWT_TTL_SECONDS', '43200'))   # 12h

        # ---- reader-portal: holds, notification inbox, shelves (#222) ----
        # A PERSISTENT, reader-addressable notification queue (env NOTIFY_DB path,
        # default a file next to access.db; ':memory:' in tests). Circulation
        # enqueues reader notices here; the inbox endpoint reads them back keyed by
        # the reader ticket (recipient). This is what lets a reader SEE the notices
        # circulation dispatches. Best-effort: a build failure must not break the
        # API (the inbox then simply reports empty).
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            notify_db = os.environ.get('NOTIFY_DB', os.path.join(here, 'notify.db'))
            self.notifications = _notifications.NotificationQueue(notify_db)
        except Exception:
            self.notifications = None
        # Shared CatalogStore (own sqlite, env CATALOG_DB; ':memory:' in tests) —
        # the ЭК / exemplar seam reused across engines: circulation flips 910^A on
        # issue/return through it (edges 2.1/2.2), acquisition WRITES into it
        # (receipt → bib + 910 + КСУ), book-provision READS exemplar counts. Built
        # BEFORE circulation so the circ engine can be constructed WITH the catalog
        # handle (so the staff desk's issue/return drive the catalog 910^A). It is a
        # separate store from the live ИРБИС server (same posture as circ/holds,
        # #222). Best-effort: a build failure must not break the API.
        try:
            cat_db = os.environ.get('CATALOG_DB', os.path.join(here, 'catalog.db'))
            self.catalog = CatalogStore(cat_db, access_store=self.access)
        except Exception:
            self.catalog = None
        # Circulation engine wired to that queue (notifications=) so its _emit
        # dispatches reader-addressable notices, AND to the catalog handle (catalog=)
        # so checkout/return flip the linked exemplar's 910^A (0↔1, edges 2.1/2.2)
        # in the shared ЭК. Own sqlite store (env CIRC_DB), standalone from the live
        # ИРБИС server (#222: never write the live server).
        try:
            circ_db = os.environ.get('CIRC_DB', os.path.join(here, 'circ.db'))
            self.circulation = _circulation.CirculationEngine(
                store=_circulation.CirculationStore(circ_db),
                notifications=self.notifications,
                catalog=self.catalog, catalog_db=self.cfg.db_default)
        except Exception:
            self.circulation = None
        # Hold + shelf services over OUR access store, reader-scoped by ticket. The
        # brief-read seam resolves a display title via the existing OPAC read; no
        # catalog handle is wired in this slice (availability falls back to the
        # FIFO queue — first-in-line is surfaced ready).
        self.holds = HoldService(self.access, catalog=None,
                                 brief_read=self._hold_brief)
        self.shelves = ShelfService(self.access, brief_read=self._hold_brief)
        # Reader-portal v2 social layer (#134 reviews/ratings + #133 recommendations,
        # reading history, saved searches). Reader-scoped by ticket in OUR access
        # store; the recommendation seams READ the live OPAC (606/700/610 + index
        # search) but never WRITE the live ИРБИС server (same posture as holds/#222).
        self.social = SocialService(
            self.access,
            read_terms=self._social_terms, search=self._social_search,
            brief_read=self._hold_brief, reader_name=self._social_reader_name)

        # ---- АРМ Комплектатор + Книгообеспеченность (acquisition + book-provision) ----
        # Both engines share the SAME CatalogStore built above (the ToCat / exemplar
        # seam): acquisition WRITES into it (receipt → bib record + 910 exemplars +
        # field-66 КСУ link), book-provision READS exemplar counts from it (910^A
        # availability). It is a separate store from the live ИРБИС server — these АРМ
        # functions never touch the live server (same posture as circulation/holds,
        # #222). Best-effort: a build failure must not break the API.
        # Acquisition engine (order → receipt → КСУ → ToCat). Own sqlite store (env
        # ACQ_DB), the catalog handle wired so receipt reflects ToCat into the ЭК.
        try:
            acq_db = os.environ.get('ACQ_DB', os.path.join(here, 'acq.db'))
            self.acquisition = _acquisition.AcquisitionEngine(
                store=_acquisition.AcquisitionStore(acq_db),
                catalog=self.catalog, catalog_db=self.cfg.db_default)
        except Exception:
            self.acquisition = None
        # Book-provision engine (связка + Кко). Own sqlite store (env BP_DB); the
        # SAME catalog handle wired READ-ONLY so live 910 exemplar counts back Кко.
        try:
            bp_db = os.environ.get('BP_DB', os.path.join(here, 'bp.db'))
            self.bookprovision = _bookprovision.BookProvisionEngine(
                bp_db, catalog=self.catalog)
        except Exception:
            self.bookprovision = None

    # ---- session helpers (signed JWT; no server-side session table) ----
    def _new_session(self, kind, actor, grants, **extra):
        """Issue a signed JWT bearer token carrying {sub, tenant, kind, grants, ...}.

        The session dict is reconstructed from the verified claims in _session(),
        so the token is fully self-contained — nothing is held server-side.
        """
        claims = {'sub': actor, 'tenant': extra.pop('tenant', DEFAULT_TENANT),
                  'kind': kind, 'grants': grants}
        claims.update(extra)
        token = _jwt.encode(claims, self.jwt_secret, ttl_seconds=self.jwt_ttl)
        return token, self._claims_to_session(claims)

    @staticmethod
    def _claims_to_session(claims):
        """Shape verified JWT claims into the session dict the endpoints expect."""
        sess = dict(claims)
        sess['actor'] = claims.get('sub')
        sess.setdefault('tenant', DEFAULT_TENANT)
        sess.setdefault('grants', [])
        return sess

    def _session(self, token):
        """Verify the JWT (signature + exp) and return the session, or None.

        A tampered or expired token verifies as invalid -> None -> the route
        treats it as no session (401). Never raises to the caller.
        """
        if not token:
            return None
        try:
            claims = _jwt.decode(token, self.jwt_secret)
        except _jwt.JwtError:
            return None
        return self._claims_to_session(claims)

    @staticmethod
    def _bearer(headers):
        h = headers.get('authorization') or headers.get('Authorization') or ''
        return h[7:].strip() if h.lower().startswith('bearer ') else None

    def _store_for(self, tenant):
        """Access store scoped to ``tenant`` for this request.

        - Single-tenant / sqlite dev (tenant 'public' or none): the default
          ``self.access`` store, back-compat unchanged.
        - Multi-tenant on PostgreSQL: a ``PgAccessStore`` pinned to ``t_<slug>``
          via the existing search_path mechanism, so accounts/grants/audit read
          and write that tenant's schema only. Falls back to the default store if
          the tenant store can't be built (keeps dev resilient).
        """
        if not tenant or tenant == DEFAULT_TENANT:
            return self.access
        if not isinstance(self.access, PgAccessStore):
            return self.access          # sqlite dev has no per-tenant schemas
        try:
            from access.pgstore import make_tenant_store
            return make_tenant_store(tenant)
        except Exception:
            return self.access

    def _guard(self, session, function, db, level):
        """Authorize or raise Denied. Audits denials for write/admin.

        Two independent gates (issue #101):
          1. entitlement — is the session's tenant LICENSED for this function's
             module? A disabled module is refused even with a valid grant.
          2. grant — does the session's grant allow function x db x level?
        """
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        tenant = session.get('tenant', DEFAULT_TENANT)
        module = FUNCTION_MODULE.get(function)
        if module and not entitlements.is_module_enabled(tenant, module):
            if level in ('write', 'admin'):
                self._store_for(tenant).audit(session['actor'], function, db, None, 'denied')
            raise Denied(403, 'forbidden', 'module not licensed: %s' % module)
        if not authorize(session['grants'], function, db, level):
            if level in ('write', 'admin'):
                self._store_for(tenant).audit(session['actor'], function, db, None, 'denied')
            raise Denied(403, 'forbidden', 'grant required: %s/%s/%s' % (function, db, level))

    # ---- public-DB policy (reader OPAC must never reach service/ПДн bases) ----
    # Non-staff sessions (guest, reader) may only touch databases on the configured
    # PUBLIC allow-list (Config.public_dbs, default {IBIS}). Everything else — RDR,
    # RQST, CMPL/PODB/POST/VUZ, PAY, RIGHT, LICH, LOG*, RDR_ARH, COUNT, WORK, ZAPR,
    # MBA*, the ATHR*/TEZ/URUB authority files — is non-public and is refused (403)
    # for a reader and hidden from their /api/databases. A reader must never be able
    # to query RDR/LICH. Staff are governed by their grants instead (per-ARM access),
    # so they keep reaching service bases they're entitled to.
    _PUBLIC_KINDS = ('guest', 'reader')

    def _is_public_session(self, session):
        """True for guest/reader sessions, which are confined to public DBs."""
        return bool(session) and session.get('kind') in self._PUBLIC_KINDS

    def _is_public_db(self, db):
        return (db or '').strip().upper() in self.cfg.public_dbs

    def _public_db_guard(self, session, db):
        """Reject a non-public ``db`` for a guest/reader session (403).

        Runs BEFORE the per-record IRBIS read so a reader can never even probe a
        service/ПДн base. Staff bypass this gate — their grants decide. Called by
        every public OPAC read endpoint (search/record/render/terms/showcase/
        rubricator/facets/cover/example-queries)."""
        if self._is_public_session(session) and not self._is_public_db(db):
            raise Denied(403, 'forbidden', 'database not public: %s' % (db or ''))

    # ---- endpoints ----
    def health(self):
        """Liveness + ИРБИС reachability. Never raises: if the ИРБИС server is
        down/restarting it reports ``irbis.reachable=False`` with the last error
        and HTTP 200, so a monitor sees a structured 'degraded' rather than a 500.
        After a server Стоп/Старт the ResilientIrbis wrapper re-registers on the
        next call, so health flips back to reachable without a process restart."""
        info = {'server': '%s:%d' % (self.cfg.irbis_host, self.cfg.irbis_port),
                'db': self.cfg.db_default}
        try:
            info['version'] = self.irbis.server_version()
            info['maxmfn'] = self.irbis.max_mfn(self.cfg.db_default)
            reachable = True
        except (IrbisError, OSError, socket.error):
            reachable = False
        h = self.irbis.health() if hasattr(self.irbis, 'health') else {}
        info['irbis'] = {'reachable': reachable,
                         'lastError': h.get('lastError'),
                         'lastOkTs': h.get('lastOkTs')}
        return ok(info)

    @staticmethod
    def _tenant_of(body):
        """Tenant slug requested at login; defaults to single-tenant 'public'."""
        return (body.get('tenant') or DEFAULT_TENANT).strip() or DEFAULT_TENANT

    def auth_guest(self, body=None):
        tenant = self._tenant_of(body or {})
        token, _ = self._new_session('guest', 'guest', GUEST_GRANTS, tenant=tenant)
        return 200, ok({'token': token, 'kind': 'guest'})

    def auth_staff(self, body):
        tenant = self._tenant_of(body)
        store = self._store_for(tenant)
        acc = store.authenticate(body.get('login', ''), body.get('password', ''))
        if not acc:
            return 401, err('auth_failed', 'invalid credentials')
        grants = store.effective_grants(acc['id'])
        token, _ = self._new_session('staff', acc['login'], grants,
                                     tenant=tenant, account_id=acc['id'])
        store.audit(acc['login'], 'auth.staff', None, None, 'ok')
        return 200, ok({'token': token, 'kind': 'staff', 'tenant': tenant,
                        'login': acc['login'], 'name': acc['full_name'], 'grants': grants})

    def auth_reader(self, body):
        ticket = (body.get('ticket', '') or '').strip()
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        tenant = self._tenant_of(body)
        try:
            _count, mfns = self.irbis.search('RDR', '"RI=%s"' % ticket)
        except IrbisError:
            mfns = []
        if not mfns:
            return 401, err('auth_failed', 'reader not found')
        rec = self.irbis.read_record('RDR', mfns[0])
        name_f = field(rec, '10') or field(rec, '11')
        name = (name_f or {}).get('value', '') if name_f else ''
        token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                     tenant=tenant, rdr_mfn=mfns[0])
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
        self._public_db_guard(session, db)
        count, mfns = self.irbis.search(db, expr)
        start = (page - 1) * page_size
        items = [self._brief_item(db, mfn) for mfn in mfns[start:start + page_size]]
        return 200, ok({'db': db, 'expr': expr, 'total': count,
                        'page': page, 'pageSize': page_size, 'items': items})

    def record(self, session, db, mfn):
        self._guard(session, 'record.read', db, 'read')
        self._public_db_guard(session, db)
        rec = self.irbis.read_record(db, mfn)
        try:
            rec['brief'] = self.irbis.format_record(db, mfn, '@brief')
        except IrbisError:
            rec['brief'] = ''
        rec['db'] = db
        rec['hasCover'] = any(f['tag'] == '953' for f in rec['fields'])
        # Reading-history hook (#133): auto-log a record-open for a reader session.
        # Best-effort — never breaks the read.
        self._log_history(session, db, mfn)
        return 200, ok(rec)

    def render(self, session, db, mfn, fmt):
        self._guard(session, 'record.read', db, 'read')
        self._public_db_guard(session, db)
        return 200, ok({'db': db, 'mfn': mfn, 'fmt': fmt,
                        'rendered': self.irbis.format_record(db, mfn, fmt)})

    def terms(self, session, db, start, count):
        self._guard(session, 'terms', db, 'read')
        self._public_db_guard(session, db)
        rows = self.irbis.read_terms(db, start, count)
        return 200, ok({'db': db, 'start': start,
                        'terms': [{'count': c, 'term': t} for c, t in rows]})

    def showcase(self, session, db, kind, limit):
        """Discovery façade — "new arrivals / featured" brief cards for the portal.

        Guarded by the same ``search``/read grant as /api/search (guests may see
        the showcase — it is public OPAC content). ``kind`` ∈ new|popular; both
        resolve to the most recent records for now (popular falls back to new
        until a circulation-ranking signal exists). "Recent" = the highest MFNs
        (MFN is assigned monotonically on input), read top-down from maxmfn so no
        date index is required. Returns brief items (reusing ``_brief_item``) and
        degrades to an empty list — never raises — when the DB is empty or the
        server is briefly unreachable, so the homepage still renders."""
        self._guard(session, 'search', db, 'read')
        self._public_db_guard(session, db)
        kind = (kind or 'new').lower()
        if kind not in ('new', 'popular'):
            kind = 'new'
        try:
            top = self.irbis.max_mfn(db)
        except IrbisError:
            top = 0
        # max_mfn returns the next free MFN; the last real record is top-1.
        # Over-scan downward and keep only cards with a REAL title: records
        # whose 200^a is empty (or that failed to read) come back from
        # _brief_item as the bare "MFN N" stub — those read as broken on the
        # homepage, so we skip them and pull the next record instead. A scan
        # cap stops a long run of empty/deleted records from looping forever.
        items = []
        scan_cap = max(limit * 6, limit + 40)
        for mfn in range(top - 1, 0, -1):
            if len(items) >= limit or (top - 1 - mfn) >= scan_cap:
                break
            it = self._brief_item(db, mfn)
            title = (it.get('title') or '').strip()
            if not title or title == ('MFN %d' % mfn):
                continue  # no real title → not a showcase-worthy new arrival
            items.append(it)
        return 200, ok({'db': db, 'kind': kind, 'limit': limit, 'items': items})

    def rubricator(self, session, db, prefix, start, limit):
        """Browse a classification / navigator dictionary (terms + posting counts)
        so the portal can render GRNTI / UDC / keyword navigators.

        Reuses the same ``read_terms`` dictionary mechanism as /api/terms, but is
        scoped to a navigator ``prefix`` (e.g. 'G=' GRNTI, 'U=' UDC, 'K='
        keywords): it scans from ``prefix``+``start`` and keeps only terms that
        still carry that prefix, stripping the prefix so the UI gets clean values
        with counts and a ready-to-run search ``expr`` per entry. Guarded by
        ``terms``/read (public — guests browse navigators). Empty list, never a
        raise, when the prefix has no terms or the server is briefly absent."""
        self._guard(session, 'terms', db, 'read')
        self._public_db_guard(session, db)
        prefix = (prefix or '').strip()
        seek = prefix + (start or '')
        try:
            rows = self.irbis.read_terms(db, seek, limit)
        except IrbisError:
            rows = []
        entries = []
        for cnt, term in rows:
            if prefix and not term.startswith(prefix):
                continue                      # walked past this navigator's block
            value = term[len(prefix):] if prefix else term
            entries.append({'term': term, 'value': value, 'count': cnt,
                            'expr': '"%s"' % term})
        return 200, ok({'db': db, 'prefix': prefix, 'start': start,
                        'limit': limit, 'terms': entries})

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
        self._public_db_guard(session, db)
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
        self._public_db_guard(session, db)
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

    # Service / authority / ПДн DBs that must never surface to a reader. Kept for
    # reference + back-compat, but the authoritative reader-visibility decision is
    # now the PUBLIC allow-list in Config.public_dbs (deny-by-default): a base is
    # public iff it is on that list, so additions like PAY/RIGHT/LICH/RDR_ARH/ZAPR/
    # WORK/MBA*/VUZ are non-public without having to be enumerated here.
    _SERVICE_DBS = {'RDR', 'RQST', 'CMPL', 'PODB', 'POST', 'VISIT', 'VUZ', 'PAY',
                    'RIGHT', 'LICH', 'RDR_ARH', 'ZAPR', 'COUNT', 'WORK', 'LOG',
                    'LOGB', 'LOGC', 'LOGP', 'LOGDB', 'MBA', 'MBA_ARH'}

    # Seeded example search chips per DB for the portal — static config for now
    # (a future iteration can derive these from the most-used dictionary terms).
    # Each chip is a ready-to-run query: {label, prefix, q} so the frontend can
    # build the same expression /api/search would. Falls back to _EX_DEFAULT.
    _EX_DEFAULT = [
        {'label': 'Программирование', 'prefix': 'K', 'q': 'программирование'},
        {'label': 'История', 'prefix': 'K', 'q': 'история'},
        {'label': 'Пушкин', 'prefix': 'A', 'q': 'Пушкин'},
    ]
    _EXAMPLE_QUERIES = {
        'IBIS': [
            {'label': 'Информатика', 'prefix': 'K', 'q': 'информатика'},
            {'label': 'Математика', 'prefix': 'K', 'q': 'математика'},
            {'label': 'Толстой Л.Н.', 'prefix': 'A', 'q': 'Толстой'},
            {'label': 'Новинки 2024', 'prefix': 'K', 'q': '2024'},
        ],
    }

    def _db_count(self, code):
        """Cheap record count for a DB selector: maxmfn-1 (the last assigned MFN).

        ``O`` (max_mfn) is a single round-trip and reads no records, so this is
        safe to call per database. Returns an int >= 0, or None when the count
        can't be obtained (server/permission hiccup) so the field can be omitted
        gracefully rather than failing the whole list."""
        try:
            top = self.irbis.max_mfn(code)
        except IrbisError:
            return None
        if top is None or top < 0:
            return None
        return max(0, top - 1)

    def databases(self, session, with_counts=True):
        """List databases. A guest/reader session sees ONLY public (OPAC) bases —
        the service/ПДн bases (RDR, LICH, PAY, LOG*, …) are filtered out entirely
        so a reader's DB picker can never even name them. Staff (and any non-public
        kind) see every base in the menu, governed by their grants downstream."""
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        public_only = self._is_public_session(session)
        txt = self.irbis.read_file(self.cfg.db_menu)
        lines = [x.strip() for x in txt.splitlines() if x.strip() and x.strip() != '*****']
        items = []
        for i in range(0, len(lines) - 1, 2):
            code = lines[i]
            name = lines[i + 1]
            if not code:
                continue
            public = self._is_public_db(code)
            if public_only and not public:
                continue                       # hide service/ПДн bases from readers
            item = {'code': code, 'name': name, 'public': public}
            if with_counts:
                cnt = self._db_count(code)
                if cnt is not None:
                    item['count'] = cnt        # additive field; back-compat preserved
            items.append(item)
        return 200, ok({'items': items, 'default': self.cfg.db_default})

    def example_queries(self, session, db):
        """Seeded example search chips for a DB (discovery façade).

        Static per-DB config for now (``_EXAMPLE_QUERIES`` / ``_EX_DEFAULT``).
        Guarded by ``search``/read like /api/search (public — guests see the
        chips on the homepage). Each chip carries {label, prefix, q} plus a
        precomputed ``expr`` so the frontend can run it verbatim through
        /api/search. Never touches IRBIS, so it cannot fail on a server hiccup."""
        self._guard(session, 'search', db, 'read')
        self._public_db_guard(session, db)
        chips = self._EXAMPLE_QUERIES.get(db) or self._EXAMPLE_QUERIES.get(
            (db or '').upper()) or self._EX_DEFAULT
        out = []
        for c in chips:
            prefix = (c.get('prefix') or 'K').upper()
            q = (c.get('q') or '').replace('"', '')
            if prefix in ('A', 'T') and not q.endswith('$'):
                q += '$'
            out.append({'label': c.get('label') or q, 'prefix': prefix,
                        'q': c.get('q'), 'expr': '"%s=%s"' % (prefix, q)})
        return 200, ok({'db': db, 'examples': out})

    def worklist(self, session, db):
        """GET /api/worklist/{db} — the cataloging editor worklist (#183).

        The field menu that drives the DynamicField editor on the cataloger
        workstation: ``{fields:[{code,label,type,required,repeatable,options?,
        subfields?}]}``. Serves the curated book worklist (:data:`WORKLIST_IBIS`)
        for IBIS / PAZK and a small generic fallback (:data:`WORKLIST_GENERIC`)
        for any other base, so a new editor always has a usable form.

        Staff-only surface, guarded by the cataloging ``record.write``/write grant
        (you load the editor for a base you may write); a guest/reader carries no
        such grant and is refused 403. The entitlement gate (FUNCTION_MODULE →
        'cataloging') applies too, so a tenant without the cataloging module is
        refused even with a grant."""
        self._require_staff(session)
        self._guard(session, 'record.write', db, 'write')
        code = (db or '').strip().upper()
        fields = WORKLIST_IBIS if code in ('IBIS', 'PAZK') else WORKLIST_GENERIC
        return 200, ok({'db': db, 'fields': fields})

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
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'record.write', db, assigned, 'ok', {'created': mfn == 0})
        return 200, ok({'db': db, 'mfn': assigned, 'created': mfn == 0, 'returnCode': r.return_code})

    def validate_record(self, session, body):
        """Run the declarative ФЛК engine over a record draft (gap A2, #188).

        Tenant-scoped via the JWT tenant claim (``_store_for`` -> the tenant's
        seeded vocabularies back dictionary checks); guarded by the same
        ``record.write``/cataloging grant + entitlement as ``save_record`` (you
        validate what you may write). Returns the violation list + worst-severity
        without touching IRBIS — a pure record->violations function (SPEC §5.1)."""
        db = (body.get('db') or self.cfg.db_default)
        self._guard(session, 'record.write', db, 'write')
        record = body.get('record') or {}
        phase = body.get('phase') or 'save'
        field_arg = body.get('field')
        current_mfn = body.get('currentMfn')
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        result = flk.validate(record, phase=phase, field=field_arg,
                              store=store, current_mfn=current_mfn)
        return 200, ok({'db': db, 'phase': phase,
                        'overallSeverity': result['overallSeverity'],
                        'canSave': result['canSave'],
                        'violations': result['violations']})

    def order(self, session, body):
        db = body.get('db', self.cfg.db_default)
        mfn = body.get('mfn')
        self._guard(session, 'order', db, 'write')
        # TODO(order): materialize a real RQST request record + reserve a copy/cell on the
        # live server (needs RQST worklist + reader id). For P0: validate + audit + queue marker.
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'order', db, mfn, 'ok', {'queued': True})
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

    # ---- reader-portal: holds, notifications inbox, shelves (#222) -------- #
    # All reader-scoped by the RDR ticket. Guests (no reader session) get 401/403.
    # Persisted in OUR access store / notification queue, NOT on the live ИРБИС
    # server (mirrors core.order's "don't touch the live server" posture).
    def _reader_ticket(self, session):
        """The bare RDR ticket for a reader session, or raise Denied.

        Reader sessions carry ``actor='RI=<ticket>'`` (see ``auth_reader``); the
        ticket itself is the reader-scope key for holds/shelves/inbox. A non-reader
        (guest/staff) session is refused — these are reader surfaces."""
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        if session.get('kind') != 'reader':
            raise Denied(403, 'forbidden', 'reader session required')
        actor = session.get('actor') or ''
        return actor[3:] if actor.startswith('RI=') else actor

    def _hold_brief(self, db, mfn):
        """Title-resolution seam for holds/shelves: reuse the OPAC brief read.

        Returns ``{'title': ...}``; degrades to a stub on any server hiccup so a
        hold/shelf add never fails for want of a title."""
        try:
            return self._brief_item(db, mfn)
        except Exception:
            return {'title': 'MFN %d' % mfn}

    # ---- social (#134/#133) seams over the live OPAC (READ-ONLY) ---------- #
    def _social_terms(self, db, mfn):
        """Seed-record terms for recommendations: 606 subjects, 700 authors, 610
        collectives. Reads the live record (never writes); degrades to empty on any
        server hiccup so recommendations never raise."""
        try:
            rec = self.irbis.read_record(db, mfn)
        except (IrbisError, OSError, socket.error):
            return {'subjects': [], 'authors': [], 'collectives': []}
        subjects = []
        for f in fields(rec, '606'):
            head = sf(f, 'A') or sf(f, 'a') or (f.get('text') or '').strip()
            if head:
                subjects.append(head)
        authors = []
        for f in fields(rec, '700'):
            a = sf(f, 'A') or sf(f, 'a')
            if a:
                authors.append(a)
        collectives = []
        for f in fields(rec, '610'):
            v = (f.get('text') or '').strip() or sf(f, 'A') or sf(f, 'a')
            if v:
                collectives.append(v)
        return {'subjects': subjects, 'authors': authors, 'collectives': collectives}

    def _social_search(self, db, prefix, term):
        """Index search for one term under ``prefix`` (S/A/K) -> candidate mfns.

        Wraps the live OPAC search with a bounded result set; returns [] on any
        error so a single bad term never breaks a recommendation run."""
        term = (term or '').strip()
        if not term:
            return []
        try:
            _count, mfns = self.irbis.search(db, '"%s=%s"' % (prefix, term))
        except (IrbisError, OSError, socket.error):
            return []
        return mfns

    def _social_reader_name(self, ticket):
        """Resolve a reader's display name (RDR 10/11) for review labels; '' on miss."""
        try:
            _count, mfns = self.irbis.search('RDR', '"RI=%s"' % ticket)
            if not mfns:
                return ''
            rec = self.irbis.read_record('RDR', mfns[0])
            name_f = field(rec, '10') or field(rec, '11')
            return (name_f or {}).get('value', '') if name_f else ''
        except (IrbisError, OSError, socket.error):
            return ''

    def place_hold(self, session, body):
        """POST /api/hold — place (or return the existing) hold for the reader."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'order', self.cfg.db_default, 'write')
        db = (body.get('db') or self.cfg.db_default)
        self._public_db_guard(session, db)
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        res = self.holds.place(ticket, db, mfn)
        return 200, ok(res)

    def list_holds(self, session):
        """GET /api/holds — the reader's live holds with queue positions."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'order', self.cfg.db_default, 'write')
        return 200, ok({'items': self.holds.list_for(ticket)})

    def cancel_hold(self, session, body):
        """POST /api/hold/cancel — cancel the reader's own hold."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'order', self.cfg.db_default, 'write')
        try:
            hold_id = int(body.get('holdId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'holdId required')
        res = self.holds.cancel(ticket, hold_id)
        if res is None:
            return 404, err('not_found', 'hold not found')
        return 200, ok(res)

    def notifications_inbox(self, session, unread_only):
        """GET /api/notifications — the reader's dispatched notices + unread count."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.notifications is None:
            return 200, ok({'items': [], 'unread': 0})
        items = self.notifications.inbox(ticket, unread_only=unread_only)
        unread = self.notifications.unread_count(ticket)
        return 200, ok({'items': items, 'unread': unread})

    def notifications_read(self, session, body):
        """POST /api/notifications/read — mark one ({id}) or all ({all:true}) read."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.notifications is None:
            return 200, ok({'unread': 0})
        mark_all = bool(body.get('all'))
        notif_id = None
        if not mark_all:
            try:
                notif_id = int(body.get('id'))
            except (TypeError, ValueError):
                return 400, err('bad_request', 'id or all:true required')
        unread = self.notifications.mark_read(ticket, notif_id=notif_id,
                                              mark_all=mark_all)
        return 200, ok({'unread': unread})

    def shelves_list(self, session):
        """GET /api/shelves — the reader's reading lists (system seeded lazily)."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        return 200, ok({'lists': self.shelves.lists(ticket)})

    def shelf_create(self, session, body):
        """POST /api/shelves — create a custom reading list."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        res = self.shelves.create(ticket, body.get('name'))
        return 200, ok(res)

    def shelf_add_item(self, session, body):
        """POST /api/shelves/item — add (db,mfn) to a list (deduped)."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        list_id = (body.get('listId') or '').strip()
        db = (body.get('db') or self.cfg.db_default)
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        res = self.shelves.add_item(ticket, list_id, db, mfn)
        if res is None:
            return 404, err('not_found', 'list not found')
        return 200, ok(res)

    def shelf_remove_item(self, session, body):
        """POST /api/shelves/item/remove — remove (db,mfn) from a list."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        list_id = (body.get('listId') or '').strip()
        db = (body.get('db') or self.cfg.db_default)
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        res = self.shelves.remove_item(ticket, list_id, db, mfn)
        if res is None:
            return 404, err('not_found', 'list not found')
        return 200, ok(res)

    # ---- reader-portal v2 social: reviews/ratings (#134), recommendations + ----
    # history + saved searches (#133). Reviews + recommendations are READABLE by a
    # guest (public OPAC engagement); all WRITES + history + saved-search require a
    # reader session (401/403 for a guest). Reader-scoped by ticket in OUR store.
    def post_review(self, session, body):
        """POST /api/review — upsert the reader's review of (db, mfn)."""
        ticket = self._reader_ticket(session)
        db = (body.get('db') or self.cfg.db_default)
        self._public_db_guard(session, db)
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        try:
            res = self.social.post_review(ticket, db, mfn, body.get('rating'),
                                          body.get('text'))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok(res)

    def list_reviews(self, session, db, mfn):
        """GET /api/reviews — avg/count + cards (+ mine for a reader). Guest-readable."""
        self._guard(session, 'search', db, 'read')
        self._public_db_guard(session, db)
        ticket = None
        if session and session.get('kind') == 'reader':
            ticket = self._reader_ticket(session)
        return 200, ok(self.social.reviews(db, mfn, ticket=ticket))

    def delete_review(self, session, body):
        """POST /api/review/delete — delete the reader's OWN review (403 otherwise)."""
        ticket = self._reader_ticket(session)
        try:
            review_id = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        res = self.social.delete_review(ticket, review_id)
        if res is None:
            return 403, err('forbidden', 'not your review')
        return 200, ok(res)

    def recommendations(self, session, db, mfn):
        """GET /api/recommendations — "similar" records to the seed. Guest-readable."""
        self._guard(session, 'search', db, 'read')
        self._public_db_guard(session, db)
        return 200, ok(self.social.similar(db, mfn))

    def recommendations_foryou(self, session):
        """GET /api/recommendations/foryou — from the reader's history (reader-only)."""
        ticket = self._reader_ticket(session)
        return 200, ok(self.social.for_you(ticket))

    def history(self, session):
        """GET /api/history — the reader's reading history (deduped, capped)."""
        ticket = self._reader_ticket(session)
        return 200, ok(self.social.history(ticket))

    def saved_searches(self, session):
        """GET /api/savedsearch — the reader's saved searches."""
        ticket = self._reader_ticket(session)
        return 200, ok(self.social.saved_searches(ticket))

    def save_search(self, session, body):
        """POST /api/savedsearch — persist a saved search."""
        ticket = self._reader_ticket(session)
        try:
            res = self.social.save_search(ticket, body.get('name'), body.get('db'),
                                          body.get('prefix'), body.get('query'))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok(res)

    def delete_search(self, session, body):
        """POST /api/savedsearch/delete — delete the reader's own saved search."""
        ticket = self._reader_ticket(session)
        try:
            search_id = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        res = self.social.delete_search(ticket, search_id)
        if res is None:
            return 404, err('not_found', 'saved search not found')
        return 200, ok(res)

    def _log_history(self, session, db, mfn):
        """Best-effort reading-history hook for the record-open path. Logs only for
        a reader session and never raises — a logging hiccup must not break the read."""
        try:
            if session and session.get('kind') == 'reader':
                ticket = self._reader_ticket(session)
                self.social.log_open(ticket, db, mfn)
        except Exception:
            pass

    # ---- АРМ Комплектатор (acquisition) + Книгообеспеченность (book-provision) ----
    # Staff surfaces (NOT public): guest/reader sessions are refused. Each handler
    # is guarded by an acquisition / book-provision function whose module must be
    # licensed (FUNCTION_MODULE → entitlements). State lives in OUR own engine
    # stores, never the live ИРБИС server (mirrors circulation/holds posture).
    def _require_staff(self, session):
        """Reject a guest/reader session on a staff-only АРМ surface (403).

        These are АРМ Комплектатор / Книгообеспеченность functions — only a staff
        session may reach them. A reader/guest carries the public OPAC grant set
        which lacks acq.*/bp.*, so the per-function ``_guard`` would 403 anyway;
        this is an explicit, uniform early refusal so the surface is unambiguous."""
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        if session.get('kind') != 'staff':
            raise Denied(403, 'forbidden', 'staff session required')

    def acq_order(self, session, body):
        """POST /api/acq/order — open an order line (заказ). Staff + acq.receipt."""
        self._require_staff(session)
        self._guard(session, 'acq.receipt', self.cfg.db_default, 'write')
        try:
            order = self.acquisition.create_order(
                title=body.get('title'), author=body.get('author'),
                supplier=body.get('supplier'), copies=int(body.get('copies', 1)),
                price=body.get('price'), funding_source=body.get('fundingSource'))
        except _acquisition.AcquisitionError as e:
            return 400, err('bad_request', str(e))
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'acq.receipt', self.cfg.db_default, order['id'], 'ok',
            {'op': 'order'})
        return 200, ok(order)

    def acq_cancel(self, session, body):
        """POST /api/acq/order/cancel — cancel an order (refused if anything received)."""
        self._require_staff(session)
        self._guard(session, 'acq.receipt', self.cfg.db_default, 'write')
        try:
            order_id = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        try:
            order = self.acquisition.cancel_order(order_id)
        except _acquisition.AcquisitionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok(order)

    def acq_receive(self, session, body):
        """POST /api/acq/receive — register received copies → КСУ → ToCat. acq.receipt."""
        self._require_staff(session)
        self._guard(session, 'acq.receipt', self.cfg.db_default, 'write')
        try:
            order_id = int(body.get('orderId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'orderId required')
        ksu_no = (body.get('ksuNo') or '').strip()
        if not ksu_no:
            return 400, err('bad_request', 'ksuNo required')
        try:
            copies = int(body.get('copies'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'copies required')
        try:
            res = self.acquisition.receive(
                order_id, ksu_no, copies, unit_price=body.get('unitPrice'),
                inv_numbers=body.get('invNumbers'), act_ref=body.get('actRef'))
        except _acquisition.AcquisitionError as e:
            return 400, err('bad_request', str(e))
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'acq.receipt', self.cfg.db_default,
            res.get('catalog_mfn'), 'ok',
            {'op': 'receive', 'ksu': ksu_no, 'copies': copies})
        return 200, ok(res)

    def acq_order_status(self, session, order_id):
        """GET /api/acq/order?id= — the order row + its status. acq.read."""
        self._require_staff(session)
        self._guard(session, 'acq.read', self.cfg.db_default, 'read')
        order = self.acquisition.store.get_order(order_id)
        if order is None:
            return 404, err('not_found', 'unknown order %r' % order_id)
        return 200, ok(order)

    def acq_ksu(self, session, ksu_no):
        """GET /api/acq/ksu?no= — the КСУ summary row (88^E/^F/^G). acq.read."""
        self._require_staff(session)
        self._guard(session, 'acq.read', self.cfg.db_default, 'read')
        ksu = self.acquisition.ksu_summary(ksu_no)
        if ksu is None:
            return 404, err('not_found', 'unknown КСУ %r' % ksu_no)
        return 200, ok(ksu)

    def bp_faculty(self, session, body):
        """POST /api/bp/faculty — create/fetch a Факультет (связка ^A root). bp.write."""
        self._require_staff(session)
        self._guard(session, 'bp.write', self.cfg.db_default, 'write')
        try:
            fid = self.bookprovision.add_faculty(body.get('code'),
                                                 name=body.get('name', ''))
        except _bookprovision.BookProvisionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'id': fid})

    def bp_specialty(self, session, body):
        """POST /api/bp/specialty — bind a Направление/Специальность. bp.write."""
        self._require_staff(session)
        self._guard(session, 'bp.write', self.cfg.db_default, 'write')
        try:
            sid = self.bookprovision.add_specialty(
                int(body.get('facultyId')), napr=body.get('napr', ''),
                spec=body.get('spec', ''), vid=body.get('vid', ''),
                form=body.get('form', ''), name=body.get('name', ''))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'facultyId required')
        except _bookprovision.BookProvisionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'id': sid})

    def bp_discipline(self, session, body):
        """POST /api/bp/discipline — attach a дисциплина + contingent. bp.write."""
        self._require_staff(session)
        self._guard(session, 'bp.write', self.cfg.db_default, 'write')
        try:
            did = self.bookprovision.add_discipline(
                int(body.get('specialtyId')), body.get('discId'),
                name=body.get('name', ''), semester=body.get('semester', ''),
                students=int(body.get('students', 0)),
                students_source=body.get('studentsSource', '68z'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'specialtyId required')
        except _bookprovision.BookProvisionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'id': did})

    def bp_contingent(self, session, body):
        """POST /api/bp/contingent — refresh a discipline's student count. bp.write."""
        self._require_staff(session)
        self._guard(session, 'bp.write', self.cfg.db_default, 'write')
        try:
            did = int(body.get('disciplineId'))
            students = int(body.get('students'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'disciplineId and students required')
        try:
            self.bookprovision.set_contingent(
                did, students, source=body.get('source', '68z'))
        except _bookprovision.BookProvisionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'disciplineId': did, 'students': students})

    def bp_bind(self, session, body):
        """POST /api/bp/bind — bind recommended literature to a discipline. bp.write."""
        self._require_staff(session)
        self._guard(session, 'bp.write', self.cfg.db_default, 'write')
        try:
            did = int(body.get('disciplineId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'disciplineId required')
        try:
            bid = self.bookprovision.bind_literature(
                did, body.get('title', ''),
                kind=body.get('kind', _bookprovision.KIND_MAIN),
                copies=int(body.get('copies', 0)),
                catalog_db=body.get('catalogDb'), inv_key=body.get('invKey'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'invalid copies')
        except _bookprovision.BookProvisionError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'id': bid})

    def bp_discipline_provision(self, session, discipline_id, normalize):
        """GET /api/bp/discipline?id=&normalize= — per-discipline Кко report. bp.read."""
        self._require_staff(session)
        self._guard(session, 'bp.read', self.cfg.db_default, 'read')
        try:
            return 200, ok(self.bookprovision.discipline_provision(
                discipline_id, normalize=normalize))
        except _bookprovision.BookProvisionError as e:
            return 404, err('not_found', str(e))

    def bp_specialty_provision(self, session, specialty_id, normalize):
        """GET /api/bp/specialty?id= — per-specialty rollup report. bp.read."""
        self._require_staff(session)
        self._guard(session, 'bp.read', self.cfg.db_default, 'read')
        try:
            return 200, ok(self.bookprovision.specialty_provision(
                specialty_id, normalize=normalize))
        except _bookprovision.BookProvisionError as e:
            return 404, err('not_found', str(e))

    # ---- Циркуляция / выдача (circulation desk) — staff-only (#185) -------- #
    # The circulation workstation over the existing CirculationEngine. State lives
    # in the engine's OWN sqlite store (loan/hold/fine, field-40 formulary model);
    # issue/return ALSO flip the linked catalog exemplar's 910^A (edges 2.1/2.2)
    # because the engine is constructed WITH the catalog handle. Never writes the
    # live ИРБИС server (same posture as holds/acquisition, #222). Staff-only: a
    # reader/guest carries the public OPAC grant set (no circ.*) and is refused.
    _CIRC_NOW = staticmethod(time.time)

    def _circ_today(self):
        """The circulation 'today' epoch (injectable clock; defaults to now)."""
        return float(self._CIRC_NOW())

    def _circ_reader(self, ticket):
        """Ensure the engine has a reader row for ``ticket`` and return its id.

        The engine's store is standalone from RDR (#222), so a reader is
        lazily registered on first desk contact. ``add_reader`` is idempotent
        (INSERT OR REPLACE) — re-issuing to the same ticket never duplicates."""
        store = self.circulation.store
        if store.get_reader(ticket) is None:
            store.add_reader(ticket)
        return ticket

    def _circ_find_loan(self, ticket, item):
        """The reader's on-hand loan (40^F='******') of ``item``, or None.

        issue/return/renew address a loan by (ticket, item) — the desk operator
        scans a reader card + a barcode, not an internal loan id. Picks the most
        recent on-hand row for that item so a re-loan after return resolves."""
        item = str(item)
        match = [ln for ln in self.circulation.store.loans_on_hand(ticket)
                 if str(ln['item']) == item]
        return match[-1] if match else None

    def _loan_card(self, ln, today=None):
        """Shape an engine loan row as a formulary card (field-40 model).

        Maps the loan to the РДР field-40 subfields the desk shows: ^A шифр/^B инв
        (here the single ``item`` stands for both until a separate shifr is wired),
        ^D выдан (checked_out), ^E план.возврат (due). Adds a resolved title via the
        OPAC brief-read seam (best-effort) so the card is human-readable, plus the
        ``overdue`` / ``renewable`` flags the circulation desk shows per loan."""
        item = ln['item']
        title = ''
        try:
            brief = self._hold_brief(self.cfg.db_default, int(item))
            title = (brief or {}).get('title') or ''
        except (TypeError, ValueError):
            title = ''
        if title == ('MFN %s' % item):
            title = ''
        if today is None:
            today = self._circ_today()
        return {
            'loanId': ln['id'], 'db': self.cfg.db_default, 'item': item,
            'title': title, 'issued': ln['checked_out_at'], 'due': ln['due'],
            'renewals': ln['renewals'], 'lostStatus': ln['lost_status'],
            'returned': bool(ln['returned']),
            'overdue': bool(ln['due'] < today),
            'renewable': ln['lost_status'] == 'none',
        }

    def circ_reader(self, session, ticket):
        """GET /api/circ/reader?ticket= — the reader formulary (field 40).

        Returns ``{reader:{ticket,name,...}, loans:[...]}`` — the on-hand loans
        for the desk operator. Guarded by ``circ.issue``/read (a desk read)."""
        self._require_staff(session)
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        reader_id = self._circ_reader(ticket)
        today = self._circ_today()
        loans = [self._loan_card(ln, today=today)
                 for ln in self.circulation.store.loans_on_hand(reader_id)]
        debt = self.circulation.reader_debt(reader_id, today)
        # Block/service messages for the desk (должник / просрочка). The engine's
        # debt model is the source of truth; surfaced both as machine flags and as
        # human ``blocks``/``messages`` the circulation desk renders.
        blocks = []
        if debt['debt_level'] == 'hard':
            blocks.append('должник: блокировка самообслуживания')
        if any(ln['overdue'] for ln in loans):
            blocks.append('есть просроченные выдачи')
        return 200, ok({
            'reader': {'ticket': ticket, 'name': self._social_reader_name(ticket),
                       # canonical engine view
                       'debtLevel': debt['debt_level'],
                       'onHand': debt['on_hand'],
                       'outstanding': debt['outstanding'],
                       # circulation-desk view (frontend CircReader)
                       'debtor': debt['debt_level'] == 'hard',
                       'finesTotal': debt['outstanding'],
                       'blocks': blocks},
            'loans': loans,
            'messages': blocks,
        })

    def circ_issue(self, session, body):
        """POST /api/circ/issue {ticket, db, item} — lend a copy to the reader.

        Maps to ``CirculationEngine.checkout`` (limits + debtor gate live there);
        on ALLOW flips the catalog 910^A 0→1. ``circ.issue``/write. A denied/
        override-required decision is surfaced 409 with its machine reasons so the
        desk can prompt for a staff override (a future endpoint)."""
        self._require_staff(session)
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        ticket = (body.get('ticket') or '').strip()
        item = (str(body.get('item') or '')).strip()
        if not ticket or not item:
            return 400, err('bad_request', 'ticket and item required')
        reader_id = self._circ_reader(ticket)
        d = self.circulation.checkout(reader_id, item, self._circ_today())
        if not d.ok:
            status = 409 if d.decision == _circulation.REQUIRE_OVERRIDE else 403
            return status, err('circ_denied', ','.join(d.reasons) or d.decision)
        loan = d.computed['loan']
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'circ.issue', self.cfg.db_default, loan['id'], 'ok',
            {'ticket': ticket, 'item': item})
        out = {'loanId': loan['id'], 'ticket': ticket, 'item': item,
               'due': d.computed['due']}
        if 'catalog_mfn' in d.computed:
            out['catalogMfn'] = d.computed['catalog_mfn']
            out['exemplarStatus'] = d.computed['exemplar_status']
        return 200, ok(out)

    def circ_return(self, session, body):
        """POST /api/circ/return {ticket, db, item} — take a copy back.

        Resolves the (ticket,item) on-hand loan and maps to
        ``CirculationEngine.return_item`` (fixes any fine, triggers the next hold,
        flips catalog 910^A 1→0). ``circ.return``/write."""
        self._require_staff(session)
        self._guard(session, 'circ.return', self.cfg.db_default, 'write')
        ticket = (body.get('ticket') or '').strip()
        item = (str(body.get('item') or '')).strip()
        if not ticket or not item:
            return 400, err('bad_request', 'ticket and item required')
        reader_id = self._circ_reader(ticket)
        loan = self._circ_find_loan(reader_id, item)
        if loan is None:
            return 404, err('not_found', 'no on-hand loan of %s' % item)
        d = self.circulation.return_item(loan['id'], self._circ_today())
        if not d.ok:
            return 409, err('circ_denied', ','.join(d.reasons) or d.decision)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'circ.return', self.cfg.db_default, loan['id'], 'ok',
            {'ticket': ticket, 'item': item})
        out = {'ok': True, 'loanId': loan['id'], 'ticket': ticket, 'item': item}
        if 'fine_charged' in d.computed:
            out['fineCharged'] = d.computed['fine_charged']
        if 'hold_ready' in d.computed:
            out['holdReady'] = d.computed['hold_ready']
        if 'catalog_mfn' in d.computed:
            out['catalogMfn'] = d.computed['catalog_mfn']
            out['exemplarStatus'] = d.computed['exemplar_status']
        return 200, ok(out)

    def circ_renew(self, session, body):
        """POST /api/circ/renew {ticket, db, item} — prolong a loan.

        Resolves the (ticket,item) on-hand loan and maps to
        ``CirculationEngine.renew`` (holds-block-renewal + renew cap + debtor gate
        live there). ``circ.issue``/write. A block (hold/cap/debt) is surfaced
        409 with reasons so the desk can prompt for an override."""
        self._require_staff(session)
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        ticket = (body.get('ticket') or '').strip()
        item = (str(body.get('item') or '')).strip()
        if not ticket or not item:
            return 400, err('bad_request', 'ticket and item required')
        reader_id = self._circ_reader(ticket)
        loan = self._circ_find_loan(reader_id, item)
        if loan is None:
            return 404, err('not_found', 'no on-hand loan of %s' % item)
        d = self.circulation.renew(loan['id'], self._circ_today())
        if not d.ok:
            status = 409 if d.decision == _circulation.REQUIRE_OVERRIDE else 403
            return status, err('circ_denied', ','.join(d.reasons) or d.decision)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'circ.issue', self.cfg.db_default, loan['id'], 'ok',
            {'op': 'renew', 'ticket': ticket, 'item': item})
        return 200, ok({'loanId': loan['id'], 'ticket': ticket, 'item': item,
                        'due': d.computed['due']})

    def circ_fines(self, session, ticket):
        """GET /api/circ/fines?ticket= — the reader's outstanding fines.

        ``{total, items:[...]}`` over the engine's fine store. ``circ.issue``/read."""
        self._require_staff(session)
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        reader_id = self._circ_reader(ticket)
        store = self.circulation.store
        items = [{'id': f['id'], 'fineId': f['id'], 'loanId': f['loan'],
                  'amount': f['amount'], 'kind': f['kind'], 'status': f['status'],
                  'reason': f['kind'], 'paid': f['status'] == 'paid'}
                 for f in store.outstanding_fines(reader_id)]
        return 200, ok({'ticket': ticket,
                        'total': store.total_outstanding(reader_id),
                        'currency': self.circulation.policy['fine']['currency'],
                        'items': items})

    def vocab_list(self, session):
        """List the session tenant's dictionaries (name/title/kind/seed_version).

        Tenant-scoped via the JWT tenant claim (``_store_for``); guarded by the same
        ``file``/read grant as ``resource`` (any АРМ staff may read dictionaries —
        they back ФЛК and dropdowns). Returns [] if the store predates the vocab
        tables (older schema), never raises."""
        self._guard(session, 'file', '*', 'read')
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        try:
            vocabs = store.list_vocabularies()
        except Exception:
            vocabs = []
        items = [{'name': v['name'], 'title': v['title'], 'kind': v['kind'],
                  'seedVersion': v.get('seed_version')} for v in vocabs]
        return 200, ok({'items': items})

    def vocab(self, session, name):
        """Values of one dictionary (code/label/sort/active) for dropdowns + ФЛК.

        Tenant-scoped; guarded by ``file``/read. 404 if the dictionary doesn't exist
        for this tenant. An institution dictionary seeded empty returns values=[]."""
        self._guard(session, 'file', name, 'read')
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        meta = store.get_vocabulary(name)
        if not meta:
            return 404, err('not_found', 'unknown vocabulary: %s' % name)
        values = store.vocabulary_values(name)
        return 200, ok({'name': name, 'title': meta['title'], 'kind': meta['kind'],
                        'seedVersion': meta.get('seed_version'),
                        'values': [{'code': v['code'], 'label': v['label'],
                                    'sort': v['sort'], 'active': bool(v['active']),
                                    'origin': v['origin']} for v in values]})

    def classification(self, session, name):
        """Nodes of one classification tree (code/label/parent/depth/path).

        Tenant-scoped; guarded by ``file``/read. Empty list (200) for a tree with no
        nodes yet (institution tree seeded empty)."""
        self._guard(session, 'file', name, 'read')
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        try:
            nodes = store.classification_nodes(name)
        except Exception:
            nodes = []
        return 200, ok({'name': name, 'nodes': [
            {'code': n['code'], 'label': n['label'], 'parent': n['parent'],
             'depth': n['depth'], 'path': n['path']} for n in nodes]})

    def modules(self, session):
        """Licensing read: the functional modules enabled for the session's tenant
        (issue #101 entitlements). Any authenticated session may read its own
        tenant's enabled-module list."""
        if not session:
            raise Denied(401, 'unauthorized', 'no session')
        tenant = session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'tenant': tenant, 'modules': entitlements.enabled_modules(tenant)})

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
                return self.auth_guest(body or {})
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
            if method == 'GET' and path == '/api/showcase':
                db = query.get('db', [self.cfg.db_default])[0]
                kind = query.get('kind', ['new'])[0]
                limit = min(50, max(1, int(query.get('limit', ['12'])[0])))
                return self.showcase(session, db, kind, limit)
            if method == 'GET' and path == '/api/rubricator':
                db = query.get('db', [self.cfg.db_default])[0]
                prefix = query.get('prefix', [''])[0]
                start = query.get('start', [''])[0]
                limit = min(100, max(1, int(query.get('limit', ['30'])[0])))
                return self.rubricator(session, db, prefix, start, limit)
            if method == 'GET' and path == '/api/example-queries':
                db = query.get('db', [self.cfg.db_default])[0]
                return self.example_queries(session, db)
            if method == 'POST' and path == '/api/validate':
                return self.validate_record(session, body or {})
            if method == 'POST' and path == '/api/order':
                return self.order(session, body or {})
            # ---- reader-portal: holds, notifications inbox, shelves (#222) ----
            if method == 'POST' and path == '/api/hold':
                return self.place_hold(session, body or {})
            if method == 'GET' and path == '/api/holds':
                return self.list_holds(session)
            if method == 'POST' and path == '/api/hold/cancel':
                return self.cancel_hold(session, body or {})
            if method == 'GET' and path == '/api/notifications':
                unread_only = query.get('unread', ['0'])[0] in ('1', 'true', 'yes')
                return self.notifications_inbox(session, unread_only)
            if method == 'POST' and path == '/api/notifications/read':
                return self.notifications_read(session, body or {})
            if method == 'GET' and path == '/api/shelves':
                return self.shelves_list(session)
            if method == 'POST' and path == '/api/shelves':
                return self.shelf_create(session, body or {})
            if method == 'POST' and path == '/api/shelves/item':
                return self.shelf_add_item(session, body or {})
            if method == 'POST' and path == '/api/shelves/item/remove':
                return self.shelf_remove_item(session, body or {})
            # ---- reader-portal v2 social: reviews/ratings (#134) ----
            if method == 'POST' and path == '/api/review/delete':
                return self.delete_review(session, body or {})
            if method == 'POST' and path == '/api/review':
                return self.post_review(session, body or {})
            if method == 'GET' and path == '/api/reviews':
                db = query.get('db', [self.cfg.db_default])[0]
                try:
                    mfn = int(query.get('mfn', ['0'])[0])
                except ValueError:
                    return 400, err('bad_request', 'mfn required')
                return self.list_reviews(session, db, mfn)
            # ---- reader-portal v2: recommendations (#133) ----
            if method == 'GET' and path == '/api/recommendations/foryou':
                return self.recommendations_foryou(session)
            if method == 'GET' and path == '/api/recommendations':
                db = query.get('db', [self.cfg.db_default])[0]
                try:
                    mfn = int(query.get('mfn', ['0'])[0])
                except ValueError:
                    return 400, err('bad_request', 'mfn required')
                return self.recommendations(session, db, mfn)
            # ---- reader-portal v2: reading history (#133) ----
            if method == 'GET' and path == '/api/history':
                return self.history(session)
            # ---- reader-portal v2: saved searches (#133) ----
            if method == 'POST' and path == '/api/savedsearch/delete':
                return self.delete_search(session, body or {})
            if method == 'GET' and path == '/api/savedsearch':
                return self.saved_searches(session)
            if method == 'POST' and path == '/api/savedsearch':
                return self.save_search(session, body or {})
            # ---- АРМ Комплектатор (acquisition) — staff-only, module-gated ----
            if method == 'POST' and path == '/api/acq/order':
                return self.acq_order(session, body or {})
            if method == 'POST' and path == '/api/acq/order/cancel':
                return self.acq_cancel(session, body or {})
            if method == 'POST' and path == '/api/acq/receive':
                return self.acq_receive(session, body or {})
            if method == 'GET' and path == '/api/acq/order':
                return self.acq_order_status(session, int(query.get('id', ['0'])[0]))
            if method == 'GET' and path == '/api/acq/ksu':
                return self.acq_ksu(session, (query.get('no', [''])[0] or '').strip())
            # ---- Книгообеспеченность (book-provision) — staff-only, module-gated ----
            if method == 'POST' and path == '/api/bp/faculty':
                return self.bp_faculty(session, body or {})
            if method == 'POST' and path == '/api/bp/specialty':
                return self.bp_specialty(session, body or {})
            if method == 'POST' and path == '/api/bp/discipline':
                return self.bp_discipline(session, body or {})
            if method == 'POST' and path == '/api/bp/contingent':
                return self.bp_contingent(session, body or {})
            if method == 'POST' and path == '/api/bp/bind':
                return self.bp_bind(session, body or {})
            if method == 'GET' and path == '/api/bp/discipline':
                norm = query.get('normalize', ['0'])[0] in ('1', 'true', 'yes')
                return self.bp_discipline_provision(
                    session, int(query.get('id', ['0'])[0]), norm)
            if method == 'GET' and path == '/api/bp/specialty':
                norm = query.get('normalize', ['0'])[0] in ('1', 'true', 'yes')
                return self.bp_specialty_provision(
                    session, int(query.get('id', ['0'])[0]), norm)
            # ---- Циркуляция / выдача (circulation desk) — staff-only (#185) ----
            if method == 'GET' and path == '/api/circ/reader':
                return self.circ_reader(session, (query.get('ticket', [''])[0] or '').strip())
            if method == 'POST' and path == '/api/circ/issue':
                return self.circ_issue(session, body or {})
            if method == 'POST' and path == '/api/circ/return':
                return self.circ_return(session, body or {})
            if method == 'POST' and path == '/api/circ/renew':
                return self.circ_renew(session, body or {})
            if method == 'GET' and path == '/api/circ/fines':
                return self.circ_fines(session, (query.get('ticket', [''])[0] or '').strip())
            if method == 'GET' and path == '/api/me/cabinet':
                return self.cabinet(session)
            if method == 'GET' and path == '/api/me/modules':
                return self.modules(session)
            if method == 'GET' and path == '/api/vocab':
                return self.vocab_list(session)
            if method == 'GET' and len(parts) == 3 and parts[0] == 'api' and parts[1] == 'vocab':
                return self.vocab(session, parts[2])
            if method == 'GET' and len(parts) == 3 and parts[0] == 'api' and parts[1] == 'classification':
                return self.classification(session, parts[2])
            if method == 'GET' and path == '/api/databases':
                with_counts = query.get('counts', ['1'])[0] not in ('0', 'false', 'no')
                return self.databases(session, with_counts=with_counts)
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
