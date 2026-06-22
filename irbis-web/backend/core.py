#!/usr/bin/env python3
"""Framework-agnostic API core. One Api.route() is shared by the stdlib server
(server.py, runs on any Python) and the aiohttp app (app_aiohttp.py, Python 3.12).

Pipeline: authn (bearer token -> session) -> authorize (grant function x db x level)
-> IRBIS call -> normalize -> audit (write/admin). Server -3338 -> 403.
"""
import hashlib
import hmac
import json
import os
import random
import socket
import statistics
import threading
import time
from datetime import datetime, timezone
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
from access import billing as _billing
from access import provision as _provision
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

# Build/version marker surfaced by /api/metrics (pilot observability). Set
# $BUILD_VERSION in the container to the image tag / git sha; a stable dev default
# otherwise. Not a secret — safe to expose unauthenticated.
BUILD_VERSION = os.environ.get('BUILD_VERSION', 'dev')

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


# Поля RDR, где может храниться пароль читателя для входа на портал:
#   130 — «Пароль» (ИРБИС64+, основной рабочий лист читателя);
#   100 — «Пароль для интернета» (классический RDR\DEFAULT.WS).
# Аудит отметил оба варианта хранения значения: открытый текст ЛИБО несолёный
# MD5-хэш (32 hex-символа). Проверяем оба, чтобы пройти любой существующий набор
# данных без миграции. См. docs/recon/.../databases/DB_CIRCULATION.md (поле 100).
READER_PASSWORD_TAGS = ('130', '100')


def _reader_password_value(rec):
    """Вернуть сохранённый пароль читателя из записи RDR (первое непустое
    значение полей 130/100) или '' если пароль не задан. Берётся «голое»
    значение поля; если пароль положили в подполе, поддерживаем и это."""
    for tag in READER_PASSWORD_TAGS:
        f = field(rec, tag)
        if not f:
            continue
        val = (f.get('value') or '').strip()
        if not val:
            # пароль мог быть записан в подполе (редкий РЛ) — возьмём первое
            for sub in (f.get('subfields') or {}).values():
                if sub and str(sub).strip():
                    val = str(sub).strip()
                    break
        if val:
            return val
    return ''


def verify_reader_password(supplied, stored):
    """Проверить введённый пароль ``supplied`` против сохранённого ``stored``.

    Поддерживает оба формата хранения, отмеченные аудитом:
      * открытый текст — посимвольное сравнение в постоянном времени;
      * несолёный MD5 (32 hex) — сравнение MD5(supplied) со ``stored``
        без учёта регистра hex.
    Сравнения выполняются через ``hmac.compare_digest`` (защита от тайминг-атак).
    Пустой ``supplied`` или ``stored`` -> False (пустой пароль не валиден)."""
    if not supplied or not stored:
        return False
    # 1) открытый текст
    if hmac.compare_digest(supplied, stored):
        return True
    # 2) несолёный MD5: сохранён 32-символьный hex -> сверяем MD5 от введённого
    s = stored.strip()
    if len(s) == 32 and all(c in '0123456789abcdefABCDEF' for c in s):
        digest = hashlib.md5(supplied.encode('utf-8')).hexdigest()
        if hmac.compare_digest(digest, s.lower()):
            return True
    return False


# --------------------------------------------------------------------------- #
# Нечёткое сопоставление терминов («Вы имели в виду …») — компактно на stdlib.
# --------------------------------------------------------------------------- #
def levenshtein(a, b):
    """Расстояние Левенштейна между двумя строками (итеративно, O(len(a)*len(b)),
    память O(min)). Чистый stdlib, без зависимостей."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1,        # удаление
                           cur[j - 1] + 1,     # вставка
                           prev[j - 1] + cost))  # замена
        prev = cur
    return prev[-1]


def _trigrams(s):
    """Множество триграмм строки с краевыми маркерами (для коротких слов и
    устойчивости к перестановкам). 'кот' -> {'  к','  ко','кот','от ','т  '}."""
    s = '  ' + s + '  '
    return {s[i:i + 3] for i in range(len(s) - 2)}


def trigram_similarity(a, b):
    """Сходство по Жаккару на множествах триграмм в [0..1]."""
    if a == b:
        return 1.0
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def term_similarity(query, candidate):
    """Комбинированная близость query↔candidate в [0..1]: смесь нормированного
    Левенштейна и триграммного сходства. Регистронезависима. Используется для
    ранжирования подсказок «Вы имели в виду»."""
    q = (query or '').strip().lower()
    c = (candidate or '').strip().lower()
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    dist = levenshtein(q, c)
    lev_sim = 1.0 - dist / max(len(q), len(c))
    tri_sim = trigram_similarity(q, c)
    # Левенштейн ловит опечатки в один символ, триграммы — общую похожесть.
    return 0.6 * lev_sim + 0.4 * tri_sim


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


# --------------------------------------------------------------------------- #
# Замер скорости ИРБИС↔Biblio (panel «liquid glass», super-admin).
#
# Методика — ЧЕСТНАЯ и like-for-like, на stdlib ``time.perf_counter``:
#   * каждую сторону прогоняем N раз, отбрасываем ОДИН максимальный выброс
#     (самый медленный прогон — JIT/кэш/сетевой всплеск), берём МЕДИАНУ остатка;
#   * любой сбой стороны -> ``None`` для неё + пометка в ``notes`` (НЕ 500, НЕ
#     выдуманное число);
#   * на ИРБИС НИЧЕГО не пишем (он общий, продакшн): где сравниваемой операции нет
#     read-only аналога (выдача), берём round-trip ЧТЕНИЯ записи как ЯВНО помеченную
#     прокси-оценку стоимости одной протокольной операции.
# --------------------------------------------------------------------------- #
BENCH_SAMPLES = 5          # N прогонов на сторону (медиана из N-1 после отброса max)
BENCH_MIGRATE_N = 50       # сколько записей читать для оценки скорости миграции


def _bench_median_ms(fn, samples=BENCH_SAMPLES):
    """Прогнать ``fn`` ``samples`` раз, вернуть МЕДИАНУ длительности в мс, отбросив
    один максимальный выброс. Возвращает ``(median_ms, error)``: при первом же
    исключении -> ``(None, '<repr>')`` (сторона помечается недоступной, не падает).

    Выброс отбрасывается только когда прогонов >= 3 (иначе медиана из 1-2 значений
    нерепрезентативна и сам отброс исказил бы её). Время меряется per-прогон через
    ``time.perf_counter`` (монотонные часы) — складывать ничего не нужно."""
    durations = []
    for _ in range(max(1, int(samples))):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as e:                         # noqa: BLE001 - сторона недоступна
            return None, '%s: %s' % (type(e).__name__, e)
        durations.append((time.perf_counter() - t0) * 1000.0)
    if len(durations) >= 3:
        durations.remove(max(durations))               # отбрасываем один max-выброс
    return statistics.median(durations), None


class Api:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        # ---- operational metrics (pilot observability, /api/metrics) ----
        # Process start (for uptime) + cheap in-process request/error counters.
        # A plain lock-guarded counter — no metering pipeline, no per-route cardinality.
        self._started_at = time.time()
        self._metrics_lock = threading.Lock()
        self._req_count = 0
        self._err_count = 0
        self.irbis = ResilientIrbis(
            SessionManager(self.cfg.irbis_host, self.cfg.irbis_port,
                           self.cfg.workstation, self.cfg.irbis_user,
                           self.cfg.irbis_pass, self.cfg.timeout),
            retries=self.cfg.irbis_retries, backoff=self.cfg.irbis_backoff)
        self.access = make_access_store(self.cfg)   # sqlite (default) or Postgres via ACCESS_BACKEND
        seed(self.access)                      # idempotent dev seed
        # Per-tenant Access stores, lazily built + cached by _store_for (PG only).
        # Caching pins each tenant's search_path-scoped connection once and reuses
        # it, instead of rebuilding a connection (and re-SETting search_path) every
        # request — and routes the auth read to the SAME schema provisioning wrote
        # to (t_<slug>), fixing the post-provision "no session" propagation bug.
        self._tenant_stores = {}
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

        # ---- benchmark cache (ИРБИС↔Biblio panel, super-admin) ----
        # Последний результат замера, кэш В ПАМЯТИ процесса (GET /api/admin/benchmark
        # отдаёт его; пусто -> 404). Lock-guarded — замер может прийти конкурентно.
        self._bench_lock = threading.Lock()
        self._bench_cache = None

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

        - Single-tenant / sqlite dev: the default ``self.access`` store,
          back-compat unchanged.
        - Multi-tenant on PostgreSQL: a ``PgAccessStore`` pinned to ``t_<slug>``
          via the existing search_path mechanism, so accounts/grants/audit read
          and write that tenant's schema only.

        **Post-provision propagation (the container-smoke bug).** Provisioning
        ALWAYS writes a tenant's accounts into its own schema ``t_<slug>`` — and
        that includes the DEFAULT tenant, whose admin lands in ``t_public``, not
        PG's bare ``public`` schema. The auth read must therefore use the SAME
        schema provisioning wrote to. Previously the default tenant short-circuited
        to ``self.access`` (search_path = public), so a freshly-provisioned
        ``public`` admin authenticated 401 ("no session") because the read looked
        in the wrong schema. Now, on PG, the default tenant is routed to its
        provisioned ``t_public`` schema whenever that schema exists, so a
        provisioned admin is authable on the very next request.

        Resolved tenant-scoped stores are cached per slug (``self._tenant_stores``)
        so the search_path-pinned connection is established once and reused, rather
        than rebuilding a connection (and re-running ``SET search_path``) on every
        request. The un-provisioned default-tenant fallback is deliberately NOT
        cached, so a tenant provisioned mid-process is picked up on the next call
        (cache miss → re-resolve to the now-existing ``t_<slug>``) instead of
        serving a stale public-schema store.
        """
        if not isinstance(self.access, PgAccessStore):
            return self.access          # sqlite dev has no per-tenant schemas
        slug = tenant or DEFAULT_TENANT
        cached = self._tenant_stores.get(slug)
        if cached is not None:
            return cached
        from access import pgstore
        try:
            if slug == DEFAULT_TENANT and not pgstore.schema_exists(slug):
                # Un-provisioned PG dev: no t_public yet → the bare public store
                # (where startup seed() wrote). Do NOT cache: once 'public' is
                # provisioned its schema appears and the next call re-resolves to
                # the tenant-scoped store.
                return self.access
            store = pgstore.make_tenant_store(slug)
        except Exception:
            return self.access          # PG hiccup → stay resilient, don't cache
        self._tenant_stores[slug] = store
        return store

    def _audit_pdn_read(self, session, subject_ticket, fields_accessed, resource):
        """Journal a READ of reader ПДн on behalf of staff — audit finding V5 / R5
        (152-ФЗ ст.19 ч.2 п.5; ФСТЭК-21 РСБ). Writes a ``pdn.read`` entry to the
        append-only audit log: {ts (audit adds it), actor, subject=ticket, action,
        fields, resource}.

        Only third-party access is journaled: a reader reading THEIR OWN data is
        not a ПДн-access event (the actor IS the subject), so it is skipped. Never
        raises — a journaling hiccup must not break the staff read."""
        try:
            if not session:
                return
            actor = session.get('actor') or ''
            # A reader reading own data: actor 'RI=<ticket>' == the subject ticket.
            if session.get('kind') == 'reader' and actor[3:] == subject_ticket:
                return
            tenant = session.get('tenant', DEFAULT_TENANT)
            self._store_for(tenant).audit(
                actor, 'pdn.read', None, None, 'ok',
                {'subject': subject_ticket, 'action': 'read',
                 'fields': fields_accessed, 'resource': resource})
        except Exception:
            pass

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

    def metrics(self, session=None):
        """GET /api/metrics — lightweight operational metrics for monitoring
        (pilot observability). Plain JSON, **unauthenticated-safe**: it carries no
        PII and no secrets, only operational counters a monitor needs.

        Always (no auth required):
          * ``version``    — build/version marker ($BUILD_VERSION, e.g. image tag);
          * ``uptimeSec``  — process uptime in seconds;
          * ``requests``   — {total, errors} in-process counters since start
                             (errors = responses with status >= 400);
          * ``irbis``      — the same reachability block as /api/health (server,
                             default db, reachable flag, maxmfn when reachable,
                             lastError/lastOkTs) — operational, not PII;
          * ``tenants.count`` — number of provisioned tenants (0 on sqlite dev /
                             no control plane). A bare count, not a tenant list.

        Admin-guarded detail (only when the caller presents a valid super-admin
        session — ``admin.db`` at admin): ``tenants.detail`` adds the per-tenant
        record/reader counts where cheaply available. These counts could hint at a
        library's scale, so they are NOT exposed unauthenticated; a monitor scrape
        with no token simply omits the block. Slug/name are operational identifiers
        (not PII) and only surface to a super-admin here. Never raises — a counting
        or control-plane hiccup degrades to a smaller dict, still HTTP 200."""
        now = time.time()
        with self._metrics_lock:
            req_total, req_errors = self._req_count, self._err_count
        out = {
            'version': BUILD_VERSION,
            'uptimeSec': round(now - self._started_at, 3),
            'requests': {'total': req_total, 'errors': req_errors},
        }
        # ИРБИС reachability (reuse the health probe; never raises).
        irbis = {'server': '%s:%d' % (self.cfg.irbis_host, self.cfg.irbis_port),
                 'db': self.cfg.db_default}
        try:
            irbis['maxmfn'] = self.irbis.max_mfn(self.cfg.db_default)
            irbis['reachable'] = True
        except (IrbisError, OSError, socket.error):
            irbis['reachable'] = False
        h = self.irbis.health() if hasattr(self.irbis, 'health') else {}
        irbis['lastError'] = h.get('lastError')
        irbis['lastOkTs'] = h.get('lastOkTs')
        out['irbis'] = irbis
        # Per-tenant block: a bare count unauthenticated; per-tenant record/reader
        # detail only for a super-admin (could hint at a library's scale).
        tenants = {'count': 0}
        try:
            rows = _provision.list_tenants()      # [] on sqlite dev / no control plane
            tenants['count'] = len(rows)
            is_admin = bool(session) and session.get('kind') == 'staff' \
                and authorize(session.get('grants', []), 'admin.db', '*', 'admin')
            if is_admin and rows:
                detail = []
                for r in rows:
                    slug = r.get('slug')
                    item = {'slug': slug, 'name': r.get('name')}
                    try:
                        usage = _billing.tenant_usage(self._store_for(slug), slug)
                        if 'max_records' in usage:
                            item['records'] = usage['max_records']
                        if 'max_readers' in usage:
                            item['readers'] = usage['max_readers']
                    except Exception:
                        pass
                    detail.append(item)
                tenants['detail'] = detail
        except Exception:
            pass
        out['tenants'] = tenants
        return 200, ok(out)

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
        """Аутентификация читателя: билет + пароль (как в jirbis).

        Тело: ``{ticket, password}``. По билету (``RI=<ticket>``) находим запись
        RDR, затем СВЕРЯЕМ пароль с полем пароля записи (130/100; открытый текст
        или несолёный MD5 — см. ``verify_reader_password``). Неверный пароль -> 401.

        Поведение, когда у читателя пароль в RDR НЕ задан, управляется флагом
        ``REQUIRE_READER_PASSWORD`` (по умолчанию true): при true — вход запрещён
        (401), при false — разрешён вход по одному билету (legacy). И тот, и другой
        исход логируется. Пароль НИКОГДА не логируется и не возвращается."""
        ticket = (body.get('ticket', '') or '').strip()
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        password = body.get('password', '') or ''
        tenant = self._tenant_of(body)
        store = self._store_for(tenant)
        try:
            _count, mfns = self.irbis.search('RDR', '"RI=%s"' % ticket)
        except IrbisError:
            mfns = []
        if not mfns:
            # Один и тот же ответ для «нет читателя» и «неверный пароль» —
            # не раскрываем существование билета.
            return 401, err('auth_failed', 'invalid credentials')
        rec = self.irbis.read_record('RDR', mfns[0])
        stored = _reader_password_value(rec)
        require = self.cfg.require_reader_password
        if stored:
            # У читателя задан пароль — проверяем ВСЕГДА, независимо от флага.
            if not verify_reader_password(password, stored):
                store.audit('RI=%s' % ticket, 'auth.reader', 'RDR', mfns[0], 'denied')
                return 401, err('auth_failed', 'invalid credentials')
            outcome = 'ok'
        else:
            # Пароль у читателя не задан.
            if require:
                store.audit('RI=%s' % ticket, 'auth.reader', 'RDR', mfns[0], 'denied')
                return 401, err('auth_failed', 'password not set')
            # Legacy-режим: пускаем по билету, но фиксируем это в аудите.
            outcome = 'ok_no_password'
        name_f = field(rec, '10') or field(rec, '11')
        name = (name_f or {}).get('value', '') if name_f else ''
        token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                     tenant=tenant, rdr_mfn=mfns[0])
        store.audit('RI=%s' % ticket, 'auth.reader', 'RDR', mfns[0], outcome)
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

    @staticmethod
    def _expr_term(expr):
        """Разобрать ПРОСТОЙ одночленный поисковый expr вида ``"A=Толстой$"`` в
        пару ``(prefix, value)`` для подсказок. Усечение ``$`` и кавычки
        отбрасываются. Сложные булевы выражения (``*``, ``+``, ``^``, скобки) ->
        ``(None, None)`` — для них подсказки не строим."""
        if not expr:
            return None, None
        e = expr.strip()
        if e and e[0] == '"' and e[-1] == '"':
            e = e[1:-1]
        if any(ch in e for ch in ('*', '+', '^', '(', ')', '"')):
            return None, None      # булева/сложная конструкция — пропускаем
        e = e.rstrip('$').strip()
        if '=' in e:
            pre, val = e.split('=', 1)
            return (pre + '='), val.strip()
        return '', e

    def _did_you_mean(self, db, expr):
        """Подсказки «Вы имели в виду» для запроса, давшего 0 результатов.
        Best-effort: при сложном выражении/ошибке -> []. Имена терминов (без
        служебных полей score), готовые к показу."""
        prefix, value = self._expr_term(expr)
        if value is None or not value:
            return []
        return [s['value'] for s in self._suggest_terms(db, prefix, value, limit=5)]

    def search(self, session, db, expr, page, page_size):
        self._guard(session, 'search', db, 'read')
        self._public_db_guard(session, db)
        count, mfns = self.irbis.search(db, expr)
        start = (page - 1) * page_size
        items = [self._brief_item(db, mfn) for mfn in mfns[start:start + page_size]]
        out = {'db': db, 'expr': expr, 'total': count,
               'page': page, 'pageSize': page_size, 'items': items}
        # На пустую выдачу — добавим «Вы имели в виду …» (тем же механизмом, что
        # /api/suggest). Никогда не ломает поиск: ошибка подбора -> поле опускается.
        if count == 0:
            try:
                dym = self._did_you_mean(db, expr)
            except Exception:
                dym = []
            if dym:
                out['didYouMean'] = dym
        return 200, ok(out)

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

    # Сколько терминов словаря просматривать при подборе подсказок, и сколько
    # отдавать. Окно держим скромным (один-два запроса 'H'), чтобы не нагружать
    # сервер; топ ограничиваем 5–8 (контракт эндпойнта).
    _SUGGEST_SCAN = 200
    _SUGGEST_LIMIT = 8
    _SUGGEST_MIN_SIM = 0.34          # порог отсева заведомо непохожих терминов

    def _suggest_terms(self, db, prefix, q, limit=None):
        """Подобрать похожие термины словаря для (возможно ошибочного) ``q``.

        Возвращает список ``[{term, value, count, expr, score}]``, ранжированный
        по близости (см. ``term_similarity``), не длиннее ``limit``. ``prefix`` —
        вид словаря (``A=``/``T=``/``K=`` …, опционален); сопоставление идёт по
        ЗНАЧЕНИЮ (часть после префикса). Никогда не бросает: при недоступности
        сервера или пустом блоке возвращает []. Чистая логика — переиспользуется
        и эндпойнтом /api/suggest, и веткой didYouMean в /api/search."""
        limit = limit or self._SUGGEST_LIMIT
        prefix = (prefix or '').strip()
        # Вид словаря приходит от клиента как код индекса ("K"/"A"/"T"), но ключи
        # словаря ИРБИС хранятся С разделителем ("K=ТЕАТР"). Без "=" якорь
        # (prefix+первый символ) промахивается мимо блока словаря и suggest пуст —
        # добиваем "=", если клиент его не прислал. "K=" остаётся как есть.
        if prefix and not prefix.endswith('='):
            prefix = prefix + '='
        qv = (q or '').strip()
        if not qv:
            return []
        # Окно словаря вокруг запроса. Якорь — первый символ значения; словарь
        # ИРБИС обычно в верхнем регистре, но регистр запроса заранее не известен,
        # поэтому сканируем от ОБОИХ вариантов первого символа (как введён и в
        # верхнем регистре) и сливаем, дедуплицируя по терму. Так окрестность
        # точного термина покрывается независимо от регистра словаря.
        first = qv[:1]
        anchors = [prefix + first]
        if first.upper() != first:
            anchors.append(prefix + first.upper())
        rows = []
        seen_terms = set()
        for anchor in anchors:
            try:
                got = self.irbis.read_terms(db, anchor, self._SUGGEST_SCAN)
            except IrbisError:
                got = []
            for cnt, term in got:
                if term not in seen_terms:
                    seen_terms.add(term)
                    rows.append((cnt, term))
        scored = []
        ql = qv.lower()
        for cnt, term in rows:
            if prefix and not term.startswith(prefix):
                continue                      # вышли за пределы этого словаря
            value = term[len(prefix):] if prefix else term
            if not value:
                continue
            if value.lower() == ql:
                continue                      # точное совпадение — это не «подсказка»
            score = term_similarity(qv, value)
            if score < self._SUGGEST_MIN_SIM:
                continue
            scored.append((score, cnt, term, value))
        # Сортировка: сначала по близости, затем по числу постингов (популярнее —
        # выше), затем алфавитно для детерминизма.
        scored.sort(key=lambda r: (-r[0], -r[1], r[3].lower()))
        out = []
        for score, cnt, term, value in scored[:limit]:
            out.append({'term': term, 'value': value, 'count': cnt,
                        'expr': '"%s"' % term, 'score': round(score, 4)})
        return out

    def suggest(self, session, db, prefix, q, limit=None):
        """GET /api/suggest — «Вы имели в виду …»: похожие термины словаря на
        опечатку. Публичный (как /api/terms): гость/читатель вправе звать, но
        только для публичных баз. Возвращает ``{db, prefix, q, suggestions:[…]}``.
        Деградирует до пустого списка, никогда не 500."""
        self._guard(session, 'terms', db, 'read')
        self._public_db_guard(session, db)
        suggestions = self._suggest_terms(db, prefix, q, limit)
        return 200, ok({'db': db, 'prefix': (prefix or '').strip(),
                        'q': (q or '').strip(), 'suggestions': suggestions})

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
        # Billing soft enforcement (#209): on a CREATE, refuse if the tenant's plan
        # caps max_records and we'd exceed it. Best-effort + off by default — a
        # plan-less tenant (dev/public, or pro/unlimited) always passes; any count
        # error fails open (never blocks a write because billing couldn't count).
        if mfn == 0:
            tenant = session.get('tenant', DEFAULT_TENANT)
            try:
                current = int(self.irbis.max_mfn(db)) + 1
                if not _billing.check_limit(self.access, tenant, 'max_records', current):
                    raise Denied(402, 'plan_limit',
                                 'plan record limit reached for %s' % db)
            except Denied:
                raise
            except Exception:
                pass                # counting failed → fail open (don't block writes)
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

    # ---- privacy: consent + right-to-erasure (V9 / R9, 152-ФЗ ст.6/9/14/21) ---- #
    # Reader-session surfaces over OUR store. Consent is append-only history;
    # erasure deletes ONLY our portal-side data for the authed reader's own ticket
    # (never the live ИРБИС RDR — that is the system of record). A reader can only
    # act on THEIR OWN ticket (the session's RI= ticket), enforced by deriving the
    # ticket from the session, not from the request body.
    # Current privacy-policy version a consent is recorded against (env-overridable).
    _CONSENT_VERSION = int(os.environ.get('PDN_POLICY_VERSION', '1'))

    def get_consent(self, session):
        """GET /api/reader/consent → {given, ts, version} (false/none when unset)."""
        ticket = self._reader_ticket(session)
        cur = self._store_for(session.get('tenant', DEFAULT_TENANT)).consent_current(ticket)
        if cur is None:
            return 200, ok({'given': False, 'ts': None, 'version': self._CONSENT_VERSION})
        return 200, ok(cur)

    def set_consent(self, session, body):
        """POST /api/reader/consent {given} → record the reader's consent state.

        Append-only: each call is a NEW row (granted/withdrawn history), so a
        withdraw + re-consent is preserved. Audited."""
        ticket = self._reader_ticket(session)
        if 'given' not in (body or {}):
            return 400, err('bad_request', 'given required')
        given = bool(body.get('given'))
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        cur = store.consent_record(ticket, given, self._CONSENT_VERSION, time.time())
        store.audit(session['actor'], 'consent', None, None, 'ok',
                    {'subject': ticket, 'given': given, 'version': self._CONSENT_VERSION})
        return 200, ok(cur)

    def erase_me(self, session, body):
        """POST /api/reader/erase {confirm:true} → delete the reader's OWN stored
        data (reviews/holds/shelves/history/saved-searches/consent) from OUR store.

        Right to erasure (152-ФЗ ст.14/21). Scope: only OUR portal-side data for
        the authed reader's own ticket — the live ИРБИС RDR record is NOT touched.
        Guarded: the ticket comes from the session, so a reader can only erase their
        own data (no cross-ticket erase). Audited with the per-table counts."""
        ticket = self._reader_ticket(session)
        if not (body or {}).get('confirm'):
            return 400, err('bad_request', 'confirm:true required')
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        erased = store.erase_reader(ticket)
        store.audit(session['actor'], 'erasure', None, None, 'ok',
                    {'subject': ticket, 'erased': erased})
        return 200, ok({'erased': erased})

    def admin_pdn_access(self, session, limit):
        """GET /api/admin/pdn-access?limit= → the ПДн-access journal, newest first.

        The V5 journal of ``pdn.read`` events (who read whose reader ПДн). Super-
        admin only (``admin.db`` at admin) — the journal is itself ПДн-by-reference
        and must not be broadly readable (SPEC_compliance_152fz §3.3)."""
        self._require_super_admin(session)
        store = self._store_for(session.get('tenant', DEFAULT_TENANT))
        items = [self._audit_view(r) for r in store.pdn_access_log(limit)]
        return 200, ok({'items': items})

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
        # V5: a staff member is about to READ this reader's ПДн (formulary = name +
        # loans + debt). Journal the third-party access to ПДн before resolving it.
        self._audit_pdn_read(session, ticket, ['name', 'history'], 'circ.reader')
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

    # ---- АРМ Администратор — staff-only, admin.users/admin.db guards (#187) ---- #
    # The administration workstation over the EXISTING access store: staff accounts,
    # their roles/grants, the audit log, and the full database list. Every surface is
    # staff-only (a reader/guest is refused) AND gated by an 'admin'-module function
    # (admin.users for account/role administration, admin.db for the DB list) at the
    # 'admin' level — only an account carrying the seeded 'administrator' role (which
    # holds admin.users/admin.db at admin) passes. A non-admin staff session lacks
    # those grants, so the per-function _guard 403s it. State lives in OUR access
    # store (self._store_for(tenant)) — the same store auth/audit already use.
    def _require_admin(self, session, function):
        """Staff gate + ``function`` (admin.users|admin.db) at admin level, or raise.

        ``_require_staff`` rejects a reader/guest up front (403); ``_guard`` then
        enforces the admin grant + the 'admin' module entitlement, auditing the
        denial (level 'admin' is a write/admin op). Returns the tenant-scoped store
        the handler operates on, so account/role/audit reads hit the same schema
        the session authenticated against."""
        self._require_staff(session)
        self._guard(session, function, '*', 'admin')
        return self._store_for(session.get('tenant', DEFAULT_TENANT))

    @staticmethod
    def _account_view(store, acc):
        """Shape one staff account row as the admin list item (roles + grants)."""
        return {'id': acc['id'], 'login': acc['login'],
                'fullName': acc.get('full_name') or '',
                'active': bool(acc['is_active']),
                'roles': store.account_roles(acc['id']),
                'grants': [{'function': g['function'], 'db': g['db'], 'level': g['level']}
                           for g in store.effective_grants(acc['id'])]}

    def admin_users(self, session):
        """GET /api/admin/users — every staff account with its roles + effective grants."""
        store = self._require_admin(session, 'admin.users')
        users = [self._account_view(store, a) for a in store.list_accounts()]
        return 200, ok({'users': users})

    def admin_create_user(self, session, body):
        """POST /api/admin/users — create a staff account (hashed pw) + assign roles.

        Hashes the password exactly as seed.py does (``store.create_account`` ->
        ``hash_password`` pbkdf2-sha256; plaintext is never stored). The dev-default
        password is env-overridable (ADMIN_DEFAULT_PASSWORD) so a created account is
        usable in dev without a secret in the request. Roles are assigned the same
        way the seed does (``set_account_roles`` -> add_role/assign). Audited."""
        store = self._require_admin(session, 'admin.users')
        login = (body.get('login') or '').strip()
        if not login:
            return 400, err('bad_request', 'login required')
        if store.get_account(login):
            return 409, err('conflict', 'login exists: %s' % login)
        password = body.get('password') or os.environ.get('ADMIN_DEFAULT_PASSWORD', 'changeme')
        full_name = (body.get('fullName') or '').strip()
        acc = store.create_account(login, password, full_name)
        roles = body.get('roles') or []
        if roles:
            store.set_account_roles(acc['id'], [str(r) for r in roles])
        store.audit(session['actor'], 'admin.users', None, acc['id'], 'ok',
                    {'op': 'create', 'login': login, 'roles': list(roles)})
        return 200, ok({'id': acc['id'], 'login': login,
                        'roles': store.account_roles(acc['id'])})

    def admin_set_roles(self, session, body):
        """POST /api/admin/users/roles {userId, roles:[]} — replace an account's roles."""
        store = self._require_admin(session, 'admin.users')
        try:
            user_id = int(body.get('userId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'userId required')
        if store.get_account_by_id(user_id) is None:
            return 404, err('not_found', 'unknown user %r' % user_id)
        roles = [str(r) for r in (body.get('roles') or [])]
        applied = store.set_account_roles(user_id, roles)
        store.audit(session['actor'], 'admin.users', None, user_id, 'ok',
                    {'op': 'roles', 'roles': applied})
        return 200, ok({'ok': True, 'userId': user_id, 'roles': applied})

    def admin_set_active(self, session, body):
        """POST /api/admin/users/active {userId, active:bool} — enable/disable an account."""
        store = self._require_admin(session, 'admin.users')
        try:
            user_id = int(body.get('userId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'userId required')
        if store.get_account_by_id(user_id) is None:
            return 404, err('not_found', 'unknown user %r' % user_id)
        active = bool(body.get('active'))
        store.set_account_active(user_id, active)
        store.audit(session['actor'], 'admin.users', None, user_id, 'ok',
                    {'op': 'active', 'active': active})
        return 200, ok({'ok': True, 'userId': user_id, 'active': active})

    def admin_roles(self, session):
        """GET /api/admin/roles — every role with its grants."""
        store = self._require_admin(session, 'admin.users')
        return 200, ok({'roles': store.list_roles()})

    def admin_audit(self, session, limit):
        """GET /api/admin/audit?limit= — the most-recent audit entries, capped.

        ``recent_audit`` returns newest-first (ORDER BY id DESC); detail is
        normalized to a parsed object (sqlite stores it as a JSON string, PG as
        JSONB) and ts to a float epoch so the payload is backend-uniform."""
        store = self._require_admin(session, 'admin.db')
        items = [self._audit_view(r) for r in store.recent_audit(limit)]
        return 200, ok({'items': items})

    @staticmethod
    def _audit_view(r):
        """Backend-uniform audit row: parse detail, coerce ts to a float epoch."""
        detail = r.get('detail')
        if isinstance(detail, str):
            try:
                detail = json.loads(detail) if detail else {}
            except ValueError:
                detail = {'raw': detail}
        ts = r.get('ts')
        if hasattr(ts, 'timestamp'):              # PG TIMESTAMPTZ -> datetime
            ts = ts.timestamp()
        return {'ts': ts, 'actor': r.get('actor'), 'function': r.get('function'),
                'db': r.get('db'), 'mfn': r.get('mfn'), 'result': r.get('result'),
                'detail': detail or {}}

    def admin_databases(self, session):
        """GET /api/admin/databases — the FULL database list (staff admin view).

        Reuses ``databases()`` (which already returns every base for a staff/non-public
        session — the public-only filter applies to guest/reader only), gated here by
        admin.db so only an administrator reaches the admin DB surface. Returns the
        same item shape {code,name,public,count?} under ``items``."""
        store = self._require_admin(session, 'admin.db')   # noqa: F841 (gate only)
        _st, payload = self.databases(session, with_counts=True)
        return 200, ok({'items': payload['data']['items'],
                        'default': payload['data'].get('default')})

    # ---- Platform admin: tenant provisioning + billing (MVP Phase 2, #207/#209) ----
    # These are CROSS-tenant control-plane surfaces (provision a NEW tenant, set a
    # tenant's plan/modules). They are super-admin only: gated by ``admin.db`` at
    # the admin level — the highest seeded admin grant (only the 'administrator'
    # role carries it). A reader/guest is rejected by ``_require_staff`` up front; a
    # non-admin staff session lacks ``admin.db`` so ``_guard`` 403s it. On the
    # sqlite dev box there is no control plane, so provisioning/billing degrade
    # sensibly (single 'public' store; plan reported but not persisted) — the routes
    # still work end-to-end so the suite runs on sqlite, and bite for real on PG.
    def _require_super_admin(self, session):
        """Platform-admin gate (staff + ``admin.db`` at admin), or raise Denied."""
        self._require_staff(session)
        self._guard(session, 'admin.db', '*', 'admin')

    def admin_tenants(self, session):
        """GET /api/admin/tenants — every provisioned tenant {slug,name,kind,plan}.

        Reads the control catalog (``provision.list_tenants`` → joins the billing
        plan). On sqlite dev there is no control plane, so this returns the single
        DEFAULT_TENANT with its default plan so the surface is non-empty in dev."""
        self._require_super_admin(session)
        tenants = _provision.list_tenants()
        if not tenants:
            # sqlite dev / no control plane: surface the single tenant we serve.
            tenants = [{'slug': DEFAULT_TENANT, 'name': DEFAULT_TENANT,
                        'kind': None, 'plan': _billing.get_tenant_plan(DEFAULT_TENANT)}]
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok', {'op': 'tenants'})
        return 200, ok({'tenants': tenants})

    def admin_create_tenant(self, session, body):
        """POST /api/admin/tenant {slug,name,adminLogin,plan?} — provision a tenant.

        Drives ``provision.provision_tenant``: schema (PG) / seeded store (sqlite) →
        vocabularies → admin account (administrator role) → plan + entitlements.
        Idempotent. The admin password defaults to $ADMIN_DEFAULT_PASSWORD (no
        secret in the request); a caller may pass ``adminPassword``. Audited."""
        self._require_super_admin(session)
        slug = (body.get('slug') or '').strip()
        if not slug:
            return 400, err('bad_request', 'slug required')
        name = (body.get('name') or slug).strip()
        admin_login = (body.get('adminLogin') or 'admin').strip()
        plan = (body.get('plan') or _billing.DEFAULT_PLAN).strip()
        if not _billing.is_plan(plan):
            return 400, err('bad_request', 'unknown plan: %s' % plan)
        admin_password = body.get('adminPassword')
        kind = (body.get('kind') or _provision.DEFAULT_KIND).strip()
        try:
            report = _provision.provision_tenant(
                self.access, slug, name, admin_login,
                admin_password=admin_password, plan=plan, kind=kind)
        except _billing.BillingError as e:
            return 400, err('bad_request', str(e))
        except ValueError as e:                       # invalid slug, etc.
            return 400, err('bad_request', str(e))
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'provision', 'slug': slug, 'plan': report['plan']})
        return 200, ok({'slug': slug, 'name': name, 'plan': report['plan'],
                        'modules': report['modules'],
                        'admin': report['admin'], 'postgres': report['postgres']})

    def admin_billing(self, session, tenant):
        """GET /api/admin/billing?tenant= — a tenant's plan, limits, usage, modules.

        Resolves the plan (``billing.get_tenant_plan``), its declared limits, a
        best-effort usage snapshot, and the enabled module list. Defaults to the
        session's own tenant when ``?tenant=`` is omitted."""
        self._require_super_admin(session)
        tenant = (tenant or session.get('tenant') or DEFAULT_TENANT).strip() or DEFAULT_TENANT
        plan = _billing.get_tenant_plan(tenant)
        store = self._store_for(tenant)
        usage = _billing.tenant_usage(store, tenant)
        return 200, ok({
            'tenant': tenant, 'plan': plan,
            'limits': _billing.plan_limits(plan),
            'usage': usage,
            'modules': entitlements.enabled_modules(tenant),
            'plans': _billing.plans_catalog(),
        })

    def admin_set_plan(self, session, body):
        """POST /api/admin/billing/plan {tenant,plan} — assign a plan + apply modules.

        ``billing.set_tenant_plan`` records the plan and drives entitlements so
        exactly the plan's modules are enabled. Audited."""
        self._require_super_admin(session)
        tenant = (body.get('tenant') or '').strip()
        if not tenant:
            return 400, err('bad_request', 'tenant required')
        plan = (body.get('plan') or '').strip()
        if not _billing.is_plan(plan):
            return 400, err('bad_request', 'unknown plan: %s' % plan)
        info = _billing.set_tenant_plan(self._store_for(tenant), tenant, plan)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'plan', 'tenant': tenant, 'plan': plan})
        return 200, ok({'tenant': tenant, 'plan': info['plan'],
                        'modules': info['modules'],
                        'limits': _billing.plan_limits(plan),
                        'applied': info['applied']})

    def admin_set_module(self, session, body):
        """POST /api/admin/billing/module {tenant,module,enabled} — toggle one entitlement.

        A targeted override on top of the plan (e.g. trial-enable acquisition).
        Best-effort on the sqlite dev path (no control plane → reported, not
        persisted). Audited."""
        self._require_super_admin(session)
        tenant = (body.get('tenant') or '').strip()
        if not tenant:
            return 400, err('bad_request', 'tenant required')
        module = (body.get('module') or '').strip()
        if not module:
            return 400, err('bad_request', 'module required')
        enabled = bool(body.get('enabled'))
        applied = True
        if entitlements._is_public(tenant):
            applied = False                  # dev/public: fail-open, nothing to persist
        else:
            try:
                entitlements.set_module(tenant, module, enabled)
            except Exception as e:
                return 400, err('bad_request', str(e))
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'module', 'tenant': tenant, 'module': module, 'enabled': enabled})
        return 200, ok({'tenant': tenant, 'module': module,
                        'enabled': enabled, 'applied': applied,
                        'modules': entitlements.enabled_modules(tenant)})

    # ---- Миграция из ИРБИС: интроспекция источника + запуск (epic #223, #225) ----
    # Кросс-тенантные операции онбординга: super-admin подключается к ВНЕШНЕМУ
    # серверу-источнику ИРБИС (или к локальным файлам БД) и (1) снимает план —
    # список БД + инвентарь полей с пометкой нештатных допполей, либо (2) запускает
    # перенос каталога/читателей в целевой tenant. Драйвер — tools.migrate_irbis
    # (тот же код, что и CLI), импортируется ЛЕНИВО (он не часть рантайма сервера).
    #
    # ПДн / секреты (ЖЁСТКО): креды источника ТРАНЗИENTНЫ — живут только в стеке
    # обработчика, НЕ персистятся в открытом виде и НЕ попадают в ответ / аудит /
    # лог. В аудит и в эхо-ответ идёт лишь redacted-описание источника (host:port,
    # user — без пароля; для локального режима — только path). Реальные ПДн читателя
    # при переносе шифруются на месте (V1-seam, как и в CLI-миграторе).
    @staticmethod
    def _migrate_redact_source(mode, source):
        """Безопасное для лога/ответа описание источника — БЕЗ пароля.

        Сетевой источник -> ``{host, port, user}`` (пароль выброшен); локальный ->
        ``{path}``. Никогда не возвращает поле пароля ни под каким ключом."""
        source = source or {}
        if mode == 'local':
            return {'path': source.get('path')}
        return {'host': source.get('host'), 'port': source.get('port'),
                'user': source.get('user')}

    def _migrate_open_source(self, mode, source):
        """Открыть источник миграции по режиму. Возвращает (handle, error|None).

        ``network`` -> tools.migrate_irbis.open_source (сессия ИРБИС, креды только
        в стеке); ``local`` -> LocalSource поверх tools.irbis_mst (если адаптер не
        готов — мягкая ошибка «адаптер не готов»). Любой иной режим -> ошибка."""
        from tools import migrate_irbis as _mig
        source = source or {}
        if mode == 'network':
            host = (source.get('host') or '').strip()
            if not host:
                return None, err('bad_request', 'source.host обязателен для network')
            port = int(source.get('port') or 6666)
            user = source.get('user') or ''
            password = source.get('pass') or source.get('password') or ''
            workstation = (source.get('workstation') or 'A').strip() or 'A'
            handle = _mig.open_source(host, port, user, password,
                                      workstation=workstation)
            return handle, None
        if mode == 'local':
            path = (source.get('path') or '').strip()
            if not path:
                return None, err('bad_request', 'source.path обязателен для local')
            try:
                handle = _mig.LocalSource(path)
            except _mig.LocalAdapterUnavailable as e:
                return None, err('not_ready', str(e))
            return handle, None
        return None, err('bad_request', 'mode должен быть network|local')

    def admin_migrate_inspect(self, session, body):
        """POST /api/admin/migrate/inspect — интроспекция источника ИРБИС (ДВУХФАЗНАЯ, #225).

        Тело ``{mode:'network'|'local', source:{host,port,user,pass}|{path}, dbs?}``.
        Две фазы (выбор по ``dbs``), чтобы большой источник (десятки БД) не упирался
        в HTTP-таймаут:

          * **без ``dbs`` — быстрый список:** перечисляет БД и на каждую отдаёт лишь
            дешёвые метаданные ``{code, name, kind, recordCount, readerCount?}`` БЕЗ
            инвентаря полей (число записей берётся из управляющей записи, без
            сканирования). Проходит быстро даже на ~50 БД.
          * **с ``dbs:[коды]`` — инвентарь полей:** разбирает ТОЛЬКО эти БД, добавляя
            на каждую ``fields:[{tag,label?,subfields,freq,custom}]`` (тяжёлое
            сэмплирование записей, выборка ограничена сверху).

        Super-admin only (403 прочим). Креды транзиентны: в ответ/аудит уходит
        только redacted-описание (без пароля)."""
        self._require_super_admin(session)
        from tools import migrate_irbis as _mig
        mode = (body.get('mode') or 'network').strip()
        source = body.get('source') or {}
        dbs = body.get('dbs') or None
        handle, error = self._migrate_open_source(mode, source)
        if error is not None:
            status = 503 if error['error']['code'] == 'not_ready' else 400
            return status, error
        try:
            plan = _mig.introspect(handle, dbs=dbs)
        except Exception:                              # noqa: BLE001 - источник недоступен
            return 502, err('source_error', 'не удалось прочитать источник')
        finally:
            close = getattr(handle, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:                       # noqa: BLE001
                    pass
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'migrate.inspect', 'mode': mode,
             'source': self._migrate_redact_source(mode, source),
             'databases': [d['code'] for d in plan['databases']]})
        return 200, ok(plan)

    def admin_migrate_run(self, session, body):
        """POST /api/admin/migrate/run — выполнить миграцию (синхронно).

        Тело ``{mode, source, tenant, dbs:[], dryRun:bool}``. Читает каталог/
        читателей из источника и грузит их в целевой tenant (ПДн шифруются на
        месте). ``dryRun`` читает+мапит+считает, НИЧЕГО не записывая. Возвращает
        ``{report:{records_read,records_loaded,readers_loaded,skipped,errors}}``.
        Super-admin only. Креды транзиентны (redacted в аудите/ответе)."""
        self._require_super_admin(session)
        from tools import migrate_irbis as _mig
        mode = (body.get('mode') or 'network').strip()
        source = body.get('source') or {}
        dbs = body.get('dbs') or ['IBIS', 'RDR']
        dbs = [str(d).strip() for d in dbs if str(d).strip()]
        dry_run = bool(body.get('dryRun'))
        target_tenant = (body.get('tenant') or session.get('tenant')
                         or DEFAULT_TENANT).strip() or DEFAULT_TENANT
        catalog_db = (body.get('catalogDb') or 'IBIS').strip() or 'IBIS'
        handle, error = self._migrate_open_source(mode, source)
        if error is not None:
            status = 503 if error['error']['code'] == 'not_ready' else 400
            return status, error
        # Целевые хранилища — РЕАЛЬНЫЕ стора приложения (как у CLI-мигратора, но
        # внутри сервера): каталог приложения (self.catalog, канонизирует через ФЛК),
        # циркуляционный стор (читательские строки ticket+категория) и access-store
        # целевого тенанта (зашифрованные ПДн, аудит). Если каталог/циркуляция не
        # поднялись (best-effort при старте) — миграция недоступна, а не падает.
        store = self._store_for(target_tenant)
        circ_store = getattr(self.circulation, 'store', None)
        if self.catalog is None or circ_store is None:
            return 503, err('not_ready', 'целевые хранилища недоступны')
        targets = _mig.Targets(self.catalog, circ_store, store,
                               catalog_db=catalog_db, tenant=target_tenant)
        try:
            report = _mig.Migrator(handle, targets, dry_run=dry_run).run(
                dbs=tuple(dbs), catalog_db=catalog_db)
        except Exception:                              # noqa: BLE001 - источник/загрузка упали
            return 502, err('migrate_error', 'миграция прервана')
        finally:
            close = getattr(handle, 'close', None)
            if callable(close):
                try:
                    close()
                except Exception:                       # noqa: BLE001
                    pass
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'migrate.run', 'mode': mode, 'tenant': target_tenant,
             'dbs': dbs, 'dryRun': dry_run,
             'source': self._migrate_redact_source(mode, source),
             'report': report})
        return 200, ok({'report': report, 'tenant': target_tenant, 'dryRun': dry_run})

    # --------------------------------------------------------------------- #
    # Замер скорости ИРБИС↔Biblio (panel «liquid glass», super-admin).
    #
    # Контракт ответа (фронт BenchmarkPanel.tsx уже его потребляет — форму не менять):
    #   { query:{irbis_ms,biblio_ms}, circulation:{irbis_ms|null,biblio_ms},
    #     migration:{records_per_sec,total|null}, ts:<iso>, notes:{...} }
    # Каждая сторона — медиана из N прогонов с отбросом max-выброса (_bench_median_ms);
    # любой сбой стороны -> null + пометка в ``notes`` (не 500). Все три стадии —
    # ЧЕСТНЫЕ замеры реальных операций; единственная прокси (явно помечена) —
    # ``circulation.irbis_ms`` (на ИРБИС писать нельзя, он общий/продакшн).
    # --------------------------------------------------------------------- #
    # Частый поисковый термин для query-стадии. ``K=`` (ключевые слова / целое поле
    # 610) — самый населённый словарь; ``A=Иванов$`` как запасной частый автор. Берём
    # ОДИН И ТОТ ЖЕ expr для обеих сторон (like-for-like), $ — правое усечение.
    _BENCH_QUERY_EXPR = '"K=библиотека"'

    def _bench_query(self, db, notes):
        """query-стадия: один и тот же expr по живому ИРБИС и по own-store Biblio.

        Обе стороны РЕАЛЬНЫ: ``irbis_ms`` — round-trip ``self.irbis.search`` по живому
        серверу; ``biblio_ms`` — ``self.catalog.search`` по нашему мигрированному
        sqlite/PG-стору (тот же inverted-index словарный поиск). Любая упавшая
        сторона -> ``None`` + пометка. Возвращает ``{'irbis_ms','biblio_ms'}``."""
        expr = self._BENCH_QUERY_EXPR
        notes['query'] = {'expr': expr, 'db': db, 'method': 'real',
                          'samples': BENCH_SAMPLES,
                          'note': 'одинаковый запрос обеим сторонам (like-for-like); '
                                  'медиана с отбросом max-выброса'}
        irbis_ms, ierr = _bench_median_ms(lambda: self.irbis.search(db, expr))
        if ierr:
            notes['query']['irbis_error'] = ierr
        biblio_ms = None
        if self.catalog is None:
            notes['query']['biblio_error'] = 'own-store недоступен'
        else:
            biblio_ms, berr = _bench_median_ms(
                lambda: self.catalog.search(db, expr, limit=20))
            if berr:
                notes['query']['biblio_error'] = berr
        return {'irbis_ms': irbis_ms, 'biblio_ms': biblio_ms}

    def _bench_circulation(self, db, notes):
        """circulation-стадия: own-store выдача+возврат vs прокси-чтение ИРБИС.

        ``biblio_ms`` — РЕАЛЬНАЯ операция выдача→возврат в ИЗОЛИРОВАННОМ временном
        сторе (``CirculationStore(':memory:')`` + temp читатель/экземпляр), чтобы не
        загрязнять боевой own-store; после замера временный стор просто отбрасывается.

        ``irbis_ms`` — ПРОКСИ: round-trip чтения записи (read_record + format) как
        оценка стоимости ОДНОЙ протокольной операции. Записывать выдачу на ИРБИС
        НЕЛЬЗЯ (общий продакшн-сервер), поэтому прямого аналога нет — это явно
        помечено в ``notes`` (``irbis_method='proxy'``)."""
        notes['circulation'] = {
            'biblio_method': 'real', 'irbis_method': 'proxy', 'samples': BENCH_SAMPLES,
            'note': 'Biblio — реальная выдача+возврат во ВРЕМЕННОМ изолированном сторе; '
                    'ИРБИС — ПРОКСИ (round-trip чтения записи), т.к. запись на общий '
                    'продакшн-сервер ИРБИС запрещена'}

        # --- Biblio: реальная issue→return в изолированном in-memory сторе ---
        biblio_ms = None
        try:
            today = int(time.time())

            def _one_cycle():
                store = _circulation.CirculationStore(':memory:')
                engine = _circulation.CirculationEngine(store=store)   # без catalog — standalone
                store.add_reader('BENCH_READER', category='_DEFAULT')
                dec = engine.checkout('BENCH_READER', 'BENCH_ITEM', today)
                if not dec.ok:
                    raise RuntimeError('checkout denied: %s' % dec.reasons)
                engine.return_item(dec.computed['loan']['id'], today)
            biblio_ms, berr = _bench_median_ms(_one_cycle)
            if berr:
                notes['circulation']['biblio_error'] = berr
        except Exception as e:                         # noqa: BLE001 - стадия не валит ответ
            notes['circulation']['biblio_error'] = '%s: %s' % (type(e).__name__, e)

        # --- ИРБИС: прокси одной протокольной операции (чтение записи) ---
        irbis_ms = None
        try:
            top = self.irbis.max_mfn(db)
            mfn = 1 if not top or top < 1 else min(top, max(1, top // 2))

            def _proxy():
                self.irbis.read_record(db, mfn)
                self.irbis.format_record(db, mfn, '@brief')
            irbis_ms, ierr = _bench_median_ms(_proxy)
            if ierr:
                notes['circulation']['irbis_error'] = ierr
        except Exception as e:                         # noqa: BLE001
            notes['circulation']['irbis_error'] = '%s: %s' % (type(e).__name__, e)
        return {'irbis_ms': irbis_ms, 'biblio_ms': biblio_ms}

    def _bench_migration(self, db, notes):
        """migration-стадия: РЕАЛЬНОЕ чтение N записей из ИРБИС -> records_per_sec.

        Read-only: читаем ``BENCH_MIGRATE_N`` записей подряд через ту же протокольную
        операцию, что использует мигратор (``read_record``; на этой же сессии работает
        ``tools.migrate_irbis``), считаем суммарное время и скорость. ``total`` —
        ``max_mfn`` основной БД (полный объём для оценки «N мин на весь объём» на
        фронте). Сбой -> ``records_per_sec=None`` + пометка."""
        notes['migration'] = {'db': db, 'method': 'real', 'sample': BENCH_MIGRATE_N,
                              'note': 'реальное read-only чтение записей тем же '
                                      'протокольным путём, что и мигратор'}
        rps = None
        total = None
        try:
            top = self.irbis.max_mfn(db)
            total = int(top) if top and top > 0 else None
        except Exception as e:                         # noqa: BLE001
            notes['migration']['total_error'] = '%s: %s' % (type(e).__name__, e)
        try:
            top = total or 0
            n = min(BENCH_MIGRATE_N, top) if top else BENCH_MIGRATE_N
            read = 0
            t0 = time.perf_counter()
            for mfn in range(1, n + 1):
                try:
                    self.irbis.read_record(db, mfn)
                    read += 1
                except IrbisError:
                    continue                            # удалённая/пустая запись — пропуск
            elapsed = time.perf_counter() - t0
            if read > 0 and elapsed > 0:
                rps = read / elapsed
                notes['migration']['records_read'] = read
            else:
                notes['migration']['migration_error'] = 'нет прочитанных записей'
        except Exception as e:                         # noqa: BLE001
            notes['migration']['migration_error'] = '%s: %s' % (type(e).__name__, e)
        return {'records_per_sec': rps, 'total': total}

    def benchmark_run(self, session):
        """POST /api/admin/benchmark/run — выполнить замер и закэшировать результат.

        Super-admin only (как соседние /api/admin/*). Прогоняет три стадии (query /
        circulation / migration), собирает контракт-ответ, кладёт его в кэш в памяти
        процесса и возвращает. Стороны деградируют независимо: упавшая возвращает
        ``null`` + пометку в ``notes`` — НИКОГДА не 500 и не выдуманное число."""
        self._require_super_admin(session)
        db = self.cfg.db_default
        notes = {}
        result = {
            'query': self._bench_query(db, notes),
            'circulation': self._bench_circulation(db, notes),
            'migration': self._bench_migration(db, notes),
            'ts': datetime.now(timezone.utc).isoformat(),
            'notes': notes,
        }
        with self._bench_lock:
            self._bench_cache = result
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok', {'op': 'benchmark.run'})
        return 200, ok(result)

    def benchmark_get(self, session):
        """GET /api/admin/benchmark — последний кэш замера (или 404, если не запускали).

        Super-admin only. Кэш живёт в памяти процесса (теряется при рестарте) — тогда
        404, и фронт остаётся в демо-режиме."""
        self._require_super_admin(session)
        with self._bench_lock:
            cached = self._bench_cache
        if cached is None:
            return 404, err('not_found', 'замер ещё не запускался')
        return 200, ok(cached)

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
        """Return (status, payload). Thin counting wrapper over ``_dispatch_route``
        (pilot observability): bumps the request counter, and the error counter when
        the resolved status is >= 400. OPTIONS preflight (204) is not counted as a
        request. Counting never affects the response."""
        status, payload = self._dispatch_route(method, path, query, body, headers)
        if not (method == 'OPTIONS' and status == 204):
            with self._metrics_lock:
                self._req_count += 1
                if status >= 400:
                    self._err_count += 1
        return status, payload

    def _dispatch_route(self, method, path, query, body, headers):
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
            if method == 'GET' and path == '/api/metrics':
                return self.metrics(session)
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
            if method == 'GET' and path == '/api/suggest':
                db = query.get('db', [self.cfg.db_default])[0]
                prefix = query.get('prefix', [''])[0]
                q = query.get('q', [''])[0]
                return self.suggest(session, db, prefix, q)
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
            # ---- privacy: consent + right-to-erasure (V9, 152-ФЗ) ----
            if method == 'GET' and path == '/api/reader/consent':
                return self.get_consent(session)
            if method == 'POST' and path == '/api/reader/consent':
                return self.set_consent(session, body or {})
            if method == 'POST' and path == '/api/reader/erase':
                return self.erase_me(session, body or {})
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
            # ---- АРМ Администратор — staff-only, admin.users/admin.db (#187) ----
            if method == 'GET' and path == '/api/admin/users':
                return self.admin_users(session)
            if method == 'POST' and path == '/api/admin/users/roles':
                return self.admin_set_roles(session, body or {})
            if method == 'POST' and path == '/api/admin/users/active':
                return self.admin_set_active(session, body or {})
            if method == 'POST' and path == '/api/admin/users':
                return self.admin_create_user(session, body or {})
            if method == 'GET' and path == '/api/admin/roles':
                return self.admin_roles(session)
            if method == 'GET' and path == '/api/admin/audit':
                limit = min(500, max(1, int(query.get('limit', ['50'])[0])))
                return self.admin_audit(session, limit)
            if method == 'GET' and path == '/api/admin/databases':
                return self.admin_databases(session)
            # ---- privacy: ПДн-access journal (V5, super-admin only) ----
            if method == 'GET' and path == '/api/admin/pdn-access':
                limit = min(500, max(1, int(query.get('limit', ['50'])[0])))
                return self.admin_pdn_access(session, limit)
            # ---- Platform admin: tenant provisioning + billing (#207/#209) ----
            if method == 'GET' and path == '/api/admin/tenants':
                return self.admin_tenants(session)
            if method == 'POST' and path == '/api/admin/tenant':
                return self.admin_create_tenant(session, body or {})
            if method == 'GET' and path == '/api/admin/billing':
                return self.admin_billing(session, query.get('tenant', [''])[0])
            if method == 'POST' and path == '/api/admin/billing/plan':
                return self.admin_set_plan(session, body or {})
            if method == 'POST' and path == '/api/admin/billing/module':
                return self.admin_set_module(session, body or {})
            # ---- Миграция из ИРБИС: интроспекция + запуск (super-admin, #225) ----
            if method == 'POST' and path == '/api/admin/migrate/inspect':
                return self.admin_migrate_inspect(session, body or {})
            if method == 'POST' and path == '/api/admin/migrate/run':
                return self.admin_migrate_run(session, body or {})
            # ---- Замер скорости ИРБИС↔Biblio (super-admin, panel «liquid glass») ----
            if method == 'POST' and path == '/api/admin/benchmark/run':
                return self.benchmark_run(session)
            if method == 'GET' and path == '/api/admin/benchmark':
                return self.benchmark_get(session)
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


# Textual «heading» prefixes that take ИРБИС right-truncation (`$`) so a search
# matches the whole inverted term from its leading words (e.g. ``A=Толстой$``,
# ``T=Война$``). These are the словарь видов where the user types a leading
# fragment of a name/title and expects the dictionary entry to match from the
# left (CATALOGER_FUNCTIONS §3.1.8 усечение). Code prefixes (IN=/B=/I=/V=/G=/U=)
# and exact codes are matched verbatim — never auto-truncated. Mirrors the
# catalog inverted-index prefixes (access/catalog.py SEARCH_PREFIXES) for the
# textual subset:
#   A=  автор · T=  заглавие · TS= заглавие серии · M=  коллектив · S= рубрика
_TRUNCATED_PREFIXES = ('A', 'T', 'TS', 'M', 'S')


def build_expr(query):
    if query.get('expr'):
        return query['expr'][0]
    q = (query.get('q', [''])[0] or '').strip().replace('"', '')
    if not q:
        return None
    prefix = (query.get('prefix', ['K'])[0] or 'K').strip().upper()
    if prefix in _TRUNCATED_PREFIXES and not q.endswith('$'):
        q += '$'
    return '"%s=%s"' % (prefix, q)
