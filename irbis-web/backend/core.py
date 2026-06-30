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
from access import gbl as _gbl
from access import notifications as _notifications
from access import circulation as _circulation
from access.holds import HoldService
from access.shelves import ShelfService
from access.social import SocialService
from access import acquisition as _acquisition
from access import bookprovision as _bookprovision
from access import phpass               # cutover jirbis→Biblio: phpass-вход (#294)
from access import devices as _devices
from access import locker as _locker
from access import readers as _readers
from access import tag_codec as _tag_codec
from access import reader_agent as _reader_agent
from access import inventory as _inventory
from access import vision as _vision
from access import sip2 as _sip2
from access import compat_devices as _compat_devices
from access import demo_requests as _demo_requests
from access.catalog import CatalogStore, CatalogError
from access import oidc as _oidc
from access.oidc_store import OidcStore
from access.identity_store import IdentityStore
from access import fulltext as _fulltext
from access import rights as _rights
from access import lich as _lich

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


def _unwrap_mfn(value):
    """Снять MFN из служебного ``*mfn``, который мог пройти ``normalize_record``.

    Резолвер глоб.корректировки планирует MFN как ``rec['*mfn'] = <int>``; gbl
    нормализует запись (``_op_correc`` → ``normalize_record``), превращая бэр-инт в
    ``[{'': '2'}]``. Принимаем оба вида (а также None) и возвращаем ``int`` или
    None, не падая на мусоре."""
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get('', '')
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class _DeviceCircAdapter:
    """Адаптер реальной книговыдачи под device-сид ``circulation`` (#272).

    locker/compat зовут ``checkout(ticket, code)``; реальный движок —
    ``checkout(reader_id, item, today, …)`` и отдаёт Decision. Здесь склейка:
    ленивая регистрация читателя по билету (``_circ_reader``) + текущий clock
    (``_circ_today``). Возврат — Decision (locker читает ``.ok``/``.reasons``)."""

    def __init__(self, api):
        self.api = api

    def checkout(self, ticket, code):
        if self.api.circulation is None:
            return False
        reader_id = self.api._circ_reader(ticket)
        return self.api.circulation.checkout(reader_id, code, self.api._circ_today())

    def checkin(self, ticket, code):
        """Возврат (IAbis Checkin) по (билет, экземпляр): резолв займа → return_item.
        None — нет выданного экземпляра у читателя."""
        if self.api.circulation is None:
            return False
        reader_id = self.api._circ_reader(ticket)
        loan = self.api._circ_find_loan(reader_id, code)
        if loan is None:
            return None
        return self.api.circulation.return_item(loan['id'], self.api._circ_today())

    def renew(self, ticket, code):
        """Продление (IAbis Renew/Prolong) по (билет, экземпляр)."""
        if self.api.circulation is None:
            return False
        reader_id = self.api._circ_reader(ticket)
        loan = self.api._circ_find_loan(reader_id, code)
        if loan is None:
            return None
        return self.api.circulation.renew(loan['id'], self.api._circ_today())

    def loans(self, ticket):
        """Выданные экземпляры читателя (IAbis GetClientChargedDocs) — карточки 40."""
        if self.api.circulation is None:
            return []
        reader_id = self.api._circ_reader(ticket)
        today = self.api._circ_today()
        return [self.api._loan_card(ln, today=today)
                for ln in self.api.circulation.store.loans_on_hand(reader_id)]

    def doc_state(self, code):
        """Статус экземпляра 910^A (IAbis GetDocState) по инвентарному номеру."""
        if self.api.catalog is None:
            return None
        return self.api.catalog.exemplar_status(self.api.cfg.db_default, code)

    def debts(self, ticket):
        """Долги/задолженность читателя (IAbis GetUserDebts)."""
        if self.api.circulation is None:
            return {}
        reader_id = self.api._circ_reader(ticket)
        return self.api.circulation.reader_debt(reader_id, self.api._circ_today())

    def doc_info(self, code):
        """Библио-инфо экземпляра (IAbis GetDocInfo): mfn + заглавие по штрихкоду."""
        if self.api.catalog is None:
            return None
        found = self.api.catalog.find_exemplar(self.api.cfg.db_default, code)
        if not found:
            return None
        mfn = found[0]
        title = ''
        try:
            brief = self.api._hold_brief(self.api.cfg.db_default, int(mfn))
            title = (brief or {}).get('title') or ''
        except Exception:
            title = ''
        return {'mfn': mfn, 'title': title}

    def set_doc_state(self, code, state):
        """Выставить 910^A экземпляра (IAbis SetBookState)."""
        if self.api.catalog is None or state is None:
            return False
        try:
            self.api.catalog.set_exemplar_status(self.api.cfg.db_default, code, str(state))
            return True
        except Exception:
            return False

    def doc_cenz(self, code):
        """Возрастная цензура экземпляра (IAbis GetBookCenz): 900^Z без '+', иначе 18.

        Рекон: @cenz PFT экземпляра → число; иначе 900^Z (убрать '+'); иначе 18.
        Возвращает минимальный возраст (int) или None, если книга не найдена."""
        if self.api.catalog is None:
            return None
        db = self.api.cfg.db_default
        found = self.api.catalog.find_exemplar(db, code)
        if not found:
            return None
        rec = self.api.catalog.get(db, found[0]) or {}
        insts = rec.get('900') or []
        if not isinstance(insts, list):
            insts = [insts]
        for inst in insts:
            if isinstance(inst, dict):
                z = inst.get('z') or inst.get('Z')
                if z:
                    try:
                        return int(str(z).lstrip('+').strip())
                    except ValueError:
                        pass
        return 18


class _InventoryCatalogAdapter:
    """Сид сверки ТСД-инвентаризации с каталогом: ожидаемые экземпляры места
    (910^D==location) + известность кода. Реальный «место→экземпляры» индекс."""

    def __init__(self, api):
        self.api = api

    def expected_items(self, db, location):
        if self.api.catalog is None:
            return []
        return self.api.catalog.exemplars_at(db, location)

    def item_known(self, db, item_code):
        if self.api.catalog is None:
            return False
        return self.api.catalog.find_exemplar(db, item_code) is not None


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
    # 3) phpass ($P$/$H$) перенесённых из jos_users (#294, cutover jirbis→Biblio):
    # реальный дамп jirbis2 (2026-06-28) подтвердил — ВСЕ 240 учёток несут phpass,
    # поэтому бесшовный вход переносится именно этой веткой. Чистая проверка в
    # постоянном времени (verify_legacy_password → phpass.verify, для не-phpass
    # вернёт False, поэтому ветки plaintext/MD5 выше не дублируются).
    if phpass.verify_legacy_password(supplied, s):
        return True
    # Upgrade-on-login (пере-хэш в наш нативный pbkdf2 + persist) делается НЕ здесь
    # (это чистая проверка), а в слое входа при verify==True И phpass.needs_rehash:
    # запись нативного хэша в поле пароля. Реальный persist в живой ИРБИС — отдельный
    # супервизируемый шаг (posture #222: боевой ИРБИС сейчас НЕ пишем).
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
                           self.cfg.irbis_pass, self.cfg.timeout,
                           encoding=self.cfg.irbis_encoding),
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
        # Own-store реестр читателя RDR (ребро 3.1) — профиль вместо строки-id;
        # передаётся в circulation хендлом reader_registry= (резолв читателя как
        # полной записи). Best-effort. Строится ДО circulation.
        try:
            from access import reader_registry as _reader_registry
            rr_db = os.environ.get('READER_REGISTRY_DB',
                                   os.path.join(here, 'reader_registry.db'))
            self.reader_registry = _reader_registry.ReaderRegistry(
                _reader_registry.ReaderStore(rr_db))
        except Exception:
            self.reader_registry = None
        # Own-store слои Книговыдачи, разведённые в роуты ниже И подключаемые в
        # circulation как хендлы (ребро 11.4): политики выдачи (внешние
        # редактируемые лимиты) + реестр должников (санкции/блок). Строятся ДО
        # circulation, чтобы передать их в движок. Best-effort.
        try:
            from access import loan_policy as _loan_policy
            self.loan_policy = _loan_policy.LoanPolicyService(
                _loan_policy.LoanPolicyStore(os.environ.get(
                    'LOAN_POLICY_DB', os.path.join(here, 'loan_policy.db'))))
        except Exception:
            self.loan_policy = None
        try:
            from access import debtors as _debtors
            self.debtors = _debtors.DebtorsService(
                _debtors.DebtStore(os.environ.get(
                    'DEBTORS_DB', os.path.join(here, 'debtors.db'))))
        except Exception:
            self.debtors = None
        # Circulation engine wired to that queue (notifications=) so its _emit
        # dispatches reader-addressable notices, AND to the catalog handle (catalog=)
        # so checkout/return flip the linked exemplar's 910^A (0↔1, edges 2.1/2.2)
        # in the shared ЭК, AND to loan_policy=/debtors= (ребро 11.4: внешние
        # лимиты + блок должников на выдаче). Own sqlite store (env CIRC_DB),
        # standalone from the live ИРБИС server (#222: never write the live server).
        try:
            circ_db = os.environ.get('CIRC_DB', os.path.join(here, 'circ.db'))
            self.circulation = _circulation.CirculationEngine(
                store=_circulation.CirculationStore(circ_db),
                notifications=self.notifications,
                catalog=self.catalog, catalog_db=self.cfg.db_default,
                reader_registry=self.reader_registry,
                loan_policy=self.loan_policy, debtors=self.debtors)
        except Exception:
            self.circulation = None
        # Hold + shelf services over OUR access store, reader-scoped by ticket. The
        # brief-read seam resolves a display title via the existing OPAC read; no
        # catalog handle is wired in this slice (availability falls back to the
        # FIFO queue — first-in-line is surfaced ready).
        self.holds = HoldService(self.access, catalog=None,
                                 brief_read=self._hold_brief)
        self.shelves = ShelfService(self.access, brief_read=self._hold_brief)
        # Own-store домен-слайсы, разведённые в роуты ниже: ИРИ/SDI (ребро 10.1),
        # Сводный каталог SK (8.1/8.2), воркер-диспетч уведомлений (11.3).
        # Best-effort: сбой сборки не должен ломать API.
        try:
            from access import sdi as _sdi
            self.sdi = _sdi.SdiService(
                _sdi.SdiStore(os.environ.get('SDI_DB', os.path.join(here, 'sdi.db'))),
                catalog=self.catalog)
        except Exception:
            self.sdi = None
        try:
            from access import union as _union
            self.union = _union.UnionCatalog(
                _union.UnionStore(os.environ.get('UNION_DB',
                                                 os.path.join(here, 'union.db'))))
        except Exception:
            self.union = None
        try:
            from access import notify_dispatch as _notify_dispatch
            self.dispatch_worker = (
                _notify_dispatch.DispatchWorker(self.notifications)
                if self.notifications is not None else None)
        except Exception:
            self.dispatch_worker = None
        # Батч-2 фич-модули, разведённые в роуты ниже: ВКР (7.6/8.3), КСУ-авто
        # (5.3), периодика (9.x), DAM/файлы (7.1). Best-effort.
        try:
            from access import vkr as _vkr
            self.vkr = _vkr.VkrService(
                _vkr.VkrStore(os.environ.get('VKR_DB', os.path.join(here, 'vkr.db'))))
        except Exception:
            self.vkr = None
        try:
            from access import ksu_auto as _ksu_auto
            self.ksu_auto = _ksu_auto.KsuAutoService(
                _ksu_auto.KsuAutoStore(os.environ.get('KSU_AUTO_DB',
                                                      os.path.join(here, 'ksu_auto.db'))))
        except Exception:
            self.ksu_auto = None
        try:
            from access import serials as _serials
            self.serials = _serials.SerialsService(
                _serials.SerialsStore(os.environ.get('SERIALS_DB',
                                                     os.path.join(here, 'serials.db'))))
        except Exception:
            self.serials = None
        try:
            from access import dam as _dam
            self.dam = _dam.DamRegistry(
                _dam.DamStore(os.environ.get('DAM_DB', os.path.join(here, 'dam.db'))))
        except Exception:
            self.dam = None
        # Трек «Оцифровка» (PR #325), разведён в роуты ниже: OCR-слой (own-store —
        # полнотекст распознанных образов постранично) + виртуальные выставки
        # (own-store — кураторские подборки-витрина над каталогом, public-read).
        # IIIF-манифесты (Presentation v3) и OAI-PMH провайдер — чисто-функциональны
        # (импортируются в хендлерах, как marc/db_utils). Никаких записей в живой
        # ИРБИС: выставка ССЫЛАЕТСЯ на записи/образы, OCR — свой текстовый слой,
        # IIIF/OAI — маппинг каталога в JSON/DC. Best-effort: сбой сборки -> None.
        try:
            from access import ocr as _ocr
            self.ocr = _ocr.OcrService(
                _ocr.OcrStore(os.environ.get('OCR_DB', os.path.join(here, 'ocr.db'))))
        except Exception:
            self.ocr = None
        try:
            from access import exhibits as _exhibits
            self.exhibits = _exhibits.ExhibitService(
                _exhibits.ExhibitStore(os.environ.get(
                    'EXHIBITS_DB', os.path.join(here, 'exhibits.db'))))
        except Exception:
            self.exhibits = None
        # Батч own-store модулей (эпик #240), разведённый в роуты ниже: шаблоны
        # метаданных по виду издания (Каталогизатор) · очередь фоновых задач с
        # приоритетами (фундамент pipeline оцифровки) · time-boxed подписки
        # читателя на коллекции/выставки/записи. Все — own-store/stdlib+sqlite,
        # живой ИРБИС не пишется (#222). Best-effort: сбой сборки -> None.
        try:
            from access import metadata_templates as _md_templates
            self.metadata_templates = _md_templates.TemplateService(
                _md_templates.TemplateStore(os.environ.get(
                    'METADATA_TEMPLATES_DB', os.path.join(here, 'metadata_templates.db'))))
        except Exception:
            self.metadata_templates = None
        try:
            from access import job_queue as _job_queue
            self.job_queue = _job_queue.JobQueue(
                _job_queue.JobStore(os.environ.get(
                    'JOB_QUEUE_DB', os.path.join(here, 'job_queue.db'))))
        except Exception:
            self.job_queue = None
        try:
            from access import collection_subs as _collection_subs
            self.collection_subs = _collection_subs.CollectionSubscriptionService(
                _collection_subs.CollectionSubStore(os.environ.get(
                    'COLLECTION_SUBS_DB', os.path.join(here, 'collection_subs.db'))))
        except Exception:
            self.collection_subs = None
        # Батч #240 (вторая волна): авто-фасеты «поле→фасет» (конфиг + подсчёт по
        # записям) + реестр IP-диапазонов организаций (провайдер IP-авто-входа,
        # резолв IP→организация). Оба own-store/stdlib, живой ИРБИС не пишется.
        try:
            from access import facet_config as _facet_config
            self.facets_cfg = _facet_config.FacetService(
                _facet_config.FacetConfigStore(os.environ.get(
                    'FACET_CONFIG_DB', os.path.join(here, 'facet_config.db'))))
        except Exception:
            self.facets_cfg = None
        try:
            from access import ip_auth as _ip_auth
            self.ip_auth = _ip_auth.IpAuthService(
                _ip_auth.IpRangeStore(os.environ.get(
                    'IP_AUTH_DB', os.path.join(here, 'ip_auth.db'))))
        except Exception:
            self.ip_auth = None
        # Матрица доступов (issue #331): own-store РЕДАКТИРУЕМЫХ тарифов (data-driven,
        # правятся в админ-таблице) + каталог разделов/функций (SSOT в access_matrix).
        # Дефолтные тарифы (free/standard/pro) сидируются идемпотентно из текущих
        # PLANS; дальше — админ-правки. Best-effort: сбой -> None (резолвер fail-open).
        try:
            from access import tariff_store as _tariff_store
            from access import access_matrix as _access_matrix
            self.tariffs = _tariff_store.TariffStore(os.environ.get(
                'TARIFFS_DB', os.path.join(here, 'tariffs.db')))
            _access_matrix.seed_defaults(self.tariffs)
        except Exception:
            self.tariffs = None
        # Онбординг-конфиг (issue #335): режим развёртывания (надстройка/замена ×
        # облако/on-prem) · редактируемая конфигурация библиотеки (наименование/
        # логотип/реквизиты — заменяет захардкоженный фронт tenantContent) ·
        # внешние подключения (ИРБИС/jirbis/инфорост, секреты маскируются наружу,
        # off-git). Best-effort: сбой -> None (резолверы деградируют).
        try:
            from access import deployment as _deployment
            self.deployment = _deployment.DeploymentService(
                _deployment.DeploymentStore(os.environ.get(
                    'DEPLOYMENT_DB', os.path.join(here, 'deployment.db'))))
        except Exception:
            self.deployment = None
        try:
            from access import library_config as _library_config
            self.library_config = _library_config.LibraryConfigService(
                _library_config.LibraryConfigStore(os.environ.get(
                    'LIBRARY_CONFIG_DB', os.path.join(here, 'library_config.db'))))
        except Exception:
            self.library_config = None
        try:
            from access import connections as _connections
            self.connections = _connections.ConnectionService(
                _connections.ConnectionStore(os.environ.get(
                    'CONNECTIONS_DB', os.path.join(here, 'connections.db'))))
        except Exception:
            self.connections = None
        try:
            from access import inforost as _inforost
            self.inforost = _inforost.InforostService(
                _inforost.InforostImportStore(os.environ.get(
                    'INFOROST_DB', os.path.join(here, 'inforost.db'))))
        except Exception:
            self.inforost = None
        try:
            from access import webhooks as _webhooks
            self.webhooks = _webhooks.WebhookService(
                _webhooks.WebhookStore(os.environ.get(
                    'WEBHOOKS_DB', os.path.join(here, 'webhooks.db'))))
        except Exception:
            self.webhooks = None
        # Бэклог own-store модулей (#316/#317/#318), разведённый в роуты ниже:
        # поставщики/счета + подписка-периодика (Комплектование), версии записи +
        # редактор словарей .mnu/.tre (Каталогизатор), роли RBAC + аудит-трейл +
        # конфиг-параметры (Администратор). MARC/MARCXML/дедуп/печать/db_utils —
        # чисто-функциональные, импортируются в хендлерах. Best-effort: сбой
        # сборки -> сервис None (роут вернёт пустой ответ, не 500).
        try:
            from access import suppliers as _suppliers
            self.suppliers = _suppliers.SupplierService(
                _suppliers.SupplierStore(os.environ.get(
                    'SUPPLIERS_DB', os.path.join(here, 'suppliers.db'))))
        except Exception:
            self.suppliers = None
        try:
            from access import subscription as _subscription
            self.subscription = _subscription.SubscriptionService(
                _subscription.SubscriptionStore(os.environ.get(
                    'SUBSCRIPTION_DB', os.path.join(here, 'subscription.db'))))
        except Exception:
            self.subscription = None
        try:
            from access import catalog_versions as _catalog_versions
            self.catalog_versions = _catalog_versions.VersionService(
                _catalog_versions.VersionStore(os.environ.get(
                    'VERSIONS_DB', os.path.join(here, 'versions.db'))))
        except Exception:
            self.catalog_versions = None
        try:
            from access import vocab_editor as _vocab_editor
            self.vocab_editor = _vocab_editor.VocabEditor(
                _vocab_editor.VocabStore(os.environ.get(
                    'VOCAB_EDITOR_DB', os.path.join(here, 'vocab_editor.db'))))
        except Exception:
            self.vocab_editor = None
        try:
            from access import authority_control as _authc
            self.authority_control = _authc.AuthorityService(
                _authc.AuthorityStore(os.environ.get(
                    'AUTHORITY_CTL_DB', os.path.join(here, 'authority_control.db'))))
        except Exception:
            self.authority_control = None
        try:
            from access import search_index as _search_index
            self.search_index = _search_index.SearchIndex(
                _search_index.SearchIndexStore(os.environ.get(
                    'SEARCH_INDEX_DB', os.path.join(here, 'search_index.db'))))
        except Exception:
            self.search_index = None
        try:
            from access import roles as _roles
            self.roles = _roles.RoleService(
                _roles.RoleStore(os.environ.get(
                    'ROLES_DB', os.path.join(here, 'roles.db'))))
        except Exception:
            self.roles = None
        try:
            from access import audit_trail as _audit_trail
            self.audit_trail = _audit_trail.AuditService(
                _audit_trail.AuditStore(os.environ.get(
                    'AUDIT_TRAIL_DB', os.path.join(here, 'audit_trail.db'))))
        except Exception:
            self.audit_trail = None
        try:
            from access import config_store as _config_store
            self.config = _config_store.ConfigService(
                _config_store.ConfigStore(os.environ.get(
                    'CONFIG_DB', os.path.join(here, 'config.db'))))
        except Exception:
            self.config = None
        # Книгообеспеченность (PR #320), разведена в роуты ниже: модель РПД
        # «дисциплина↔издание↔норматив↔контингент» + снапшот-стор ККО-аналитики
        # (сами расчёты Кко — чисто-функциональны, импорт в хендлерах). Best-effort.
        try:
            from access import discipline_norms as _discipline_norms
            self.discipline_norms = _discipline_norms.DisciplineNormService(
                _discipline_norms.DisciplineStore(os.environ.get(
                    'DISCIPLINE_NORMS_DB', os.path.join(here, 'discipline_norms.db'))))
        except Exception:
            self.discipline_norms = None
        try:
            from access import kko_reports as _kko_reports
            self.kko_snapshots = _kko_reports.KkoSnapshotStore(os.environ.get(
                'KKO_DB', os.path.join(here, 'kko.db')))
        except Exception:
            self.kko_snapshots = None
        # Привязки внешней OIDC-личности к билету (узел 3 MVP-2b): отдельный
        # sqlite-стор + резолв конфига провайдера. OFF, если провайдер не задан
        # (cfg.oidc_provider пуст) — _oidc_enabled() это проверяет. Best-effort.
        try:
            self.oidc_store = OidcStore(self.cfg.oidc_db)
        except Exception:
            self.oidc_store = None
        # узел 3 MVP-3: связь сотрудник↔читательский билет (единая идентичность).
        self.identity_store = IdentityStore(self.cfg.identity_db)
        self._oidc_pcfg = _oidc.provider_config(self.cfg.oidc_provider, {
            'authorize': self.cfg.oidc_authorize_url, 'token': self.cfg.oidc_token_url,
            'userinfo': self.cfg.oidc_userinfo_url, 'claim': self.cfg.oidc_claim,
        }) if self.cfg.oidc_provider else {}
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

        # ---- Внешние устройства (#272): реестр devices + locker-заказы + шим ----
        # Нативные домены поверх готовых own-store/circulation/holds. compat-шим
        # принимает device-facing вызовы IDlogic (POST /api/devices/<endpoint>) и
        # переводит их в эти сервисы. Реальная выдача из ячейки/со стойки — через
        # _DeviceCircAdapter (тот же engine, что АРМ выдачи). Карты RFID↔билет — в
        # своём реестре (readers), живой ИРБИС не пишем (#222). Best-effort.
        try:
            dev_db = os.environ.get('DEVICES_DB', os.path.join(here, 'devices.db'))
            self.devices = _devices.DeviceService(_devices.DeviceStore(dev_db))
        except Exception:
            self.devices = None
        try:
            rdr_db = os.environ.get('READERS_DB', os.path.join(here, 'readers.db'))
            self.readers = _readers.ReaderService(_readers.ReaderStore(rdr_db))
        except Exception:
            self.readers = None
        _circ_adapter = _DeviceCircAdapter(self) if self.circulation is not None else None
        try:
            locker_db = os.environ.get('LOCKER_DB', os.path.join(here, 'locker.db'))
            self.locker = _locker.LockerService(
                _locker.LockerStore(locker_db),
                circulation=_circ_adapter, devices=self.devices)
        except Exception:
            self.locker = None
        # Настольный считыватель (станция/стойка): hardware-транспорт живёт на
        # клиенте устройства, на сервере transport=None — модуль доступен для
        # станционных клиентов и серверных tag-хелперов, кодек — общий tag_codec.
        try:
            self.reader_agent = _reader_agent.ReaderAgentService(codec=_tag_codec)
        except Exception:
            self.reader_agent = None
        # Фаза 2: ТСД-инвентаризация фонда + камеры/FaceID. Свои own-store домены
        # (env INVENTORY_DB / VISION_DB). vision хранит только токены лиц, не
        # биометрию. Реконсиляция инвентаризации с каталогом — отдельный адаптер
        # (нужен индекс «место→экземпляры»), пока catalog-сид не подключён. Best-effort.
        try:
            inv_db = os.environ.get('INVENTORY_DB', os.path.join(here, 'inventory.db'))
            self.inventory = _inventory.InventoryService(
                _inventory.InventoryStore(inv_db),
                catalog=_InventoryCatalogAdapter(self))
        except Exception:
            self.inventory = None
        try:
            vis_db = os.environ.get('VISION_DB', os.path.join(here, 'vision.db'))
            self.vision = _vision.VisionService(_vision.VisionStore(vis_db))
        except Exception:
            self.vision = None
        # SIP2-ACS для сторонних киосков самообслуживания: на той же боевой
        # книговыдаче (circ-адаптер) и реестре карт (readers). Транспорт SIP2 —
        # TCP на деплое; здесь сервис обрабатывает кадр-строку (HTTP-пробрасывает шим).
        try:
            self.sip2 = _sip2.Sip2Service(circulation=_circ_adapter,
                                          readers=self.readers, devices=self.devices)
        except Exception:
            self.sip2 = None
        try:
            self.compat_devices = _compat_devices.CompatDevicesService(
                devices=self.devices, readers=self.readers, holds=self.holds,
                circulation=_circ_adapter, locker=self.locker, codec=_tag_codec,
                inventory=self.inventory, vision=self.vision, sip2=self.sip2,
                legacy_pass=os.environ.get('EASYBOOK_LEGACY_PASS'))
        except Exception:
            self.compat_devices = None

        # ---- Полный текст + права + личный кабинет ПТ (кластер 7) ----
        # Три связанных движка обслуживают эндпойнт /api/fulltext (ребра 7.1/7.2/
        # 7.3/7.5):
        #   * fulltext  (FulltextRegistry) — реестр артефактов ПТ записи (951/953/
        #     955). Резолвит их из СВОЕГО стора (env FULLTEXT_DB) И из каталожной
        #     записи через тот же catalog-handle (ребро 7.1). Каждый 955-артефакт
        #     несёт rights_template (955^B) — вход для гейтинга прав.
        #   * rights    (RightService)  — по категории читателя и шаблону прав
        #     (резолв 955^B через catalog-handle → стор RightStore, env RIGHT_DB)
        #     считает уровень доступа deny/view/download и постраничный лимит ^F
        #     (рёбра 7.2/7.3). Пустой шаблон ⇒ полный доступ (download).
        #   * lich      (LichService)   — личный кабинет ПТ читателя (env LICH_DB):
        #     счётчик скачанных страниц (поле 4) и остаток квоты download_budget =
        #     RIGHT.^F − LICH.v4 (ребро 7.5), привязан к rights-seam.
        # Все три — СВОИ сторы, отдельные от живого ИРБИС (та же посадка, что у
        # circulation/holds/bookprovision, #222). Каталог-handle общий (тот же
        # CatalogStore, что резолвит 955/955^B). Best-effort: сбой сборки не валит
        # API (эндпойнт тогда деградирует — пустые артефакты / без квоты).
        try:
            ft_db = os.environ.get('FULLTEXT_DB', os.path.join(here, 'fulltext.db'))
            self.fulltext = _fulltext.FulltextRegistry(
                store=_fulltext.FulltextStore(ft_db), catalog=self.catalog)
        except Exception:
            self.fulltext = None
        try:
            right_db = os.environ.get('RIGHT_DB', os.path.join(here, 'right.db'))
            self.rights = _rights.RightService(
                store=_rights.RightStore(right_db), catalog=self.catalog)
        except Exception:
            self.rights = None
        try:
            lich_db = os.environ.get('LICH_DB', os.path.join(here, 'lich.db'))
            self.lich = _lich.LichService(
                _lich.LichStore(lich_db), rights=self.rights)
        except Exception:
            self.lich = None

        # ---- Заявки на демодоступ (публичная страница продукта, #226) ----
        # Свой стор заявок (env DEMO_DB; по умолчанию файл рядом с access.db,
        # ':memory:' в тестах) — отдельный от Access-стора и от живого ИРБИС. Форма
        # на /product POST'ит сюда (с обязательным согласием 152-ФЗ); листинг —
        # только super-admin. Best-effort: сбой сборки стора не валит API (форма
        # тогда вернёт 503, остальной API работает).
        try:
            demo_db = os.environ.get('DEMO_DB', os.path.join(here, 'demo_requests.db'))
            self.demo_requests = _demo_requests.DemoRequestStore(demo_db)
        except Exception:
            self.demo_requests = None

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
                        'login': acc['login'], 'name': acc['full_name'], 'grants': grants,
                        # узел 3 MVP-3: привязанный читательский билет (если этот
                        # сотрудник — ещё и читатель) → UI покажет «смотреть как читатель».
                        'readerTicket': self.identity_store.reader_for_staff(acc['login'])})

    # --- Единая идентичность читатель↔сотрудник (узел 3 MVP-3) --------------
    def staff_link_reader(self, session, body):
        """POST /api/staff/link-reader {ticket, password} — сотрудник привязывает
        свой ЧИТАТЕЛЬСКИЙ билет, доказав владение (билет+пароль штатным reader-
        входом — логику RDR не дублируем). Один человек = и сотрудник, и читатель."""
        if not session or session.get('kind') != 'staff':
            return 401, err('auth_required', 'staff session required')
        ticket = (body.get('ticket') or '').strip()
        password = body.get('password') or ''
        if not ticket:
            return 400, err('bad_request', 'ticket required')
        st, _r = self.auth_reader({'ticket': ticket, 'password': password,
                                   'tenant': session.get('tenant', DEFAULT_TENANT)})
        if st != 200:
            return 401, err('auth_failed', 'invalid reader ticket or password')
        login = session.get('sub') or session.get('actor') or ''
        self.identity_store.link(login, ticket)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            login, 'identity.link', None, None, 'ok', {'ticket': ticket})
        return 200, ok({'linked': True, 'staffLogin': login, 'ticket': ticket})

    def staff_unlink_reader(self, session):
        """POST /api/staff/unlink-reader — снять привязку билета у сотрудника."""
        if not session or session.get('kind') != 'staff':
            return 401, err('auth_required', 'staff session required')
        login = session.get('sub') or session.get('actor') or ''
        n = self.identity_store.unlink(login)
        return 200, ok({'unlinked': bool(n)})

    def view_as_reader(self, session):
        """POST /api/staff/view-as-reader — сотрудник с привязанным билетом получает
        ЧИТАТЕЛЬСКУЮ сессию своего билета (QA «смотреть как читатель»). Нет привязки
        → 404. Билет уже доказан паролем на этапе привязки, поэтому здесь без пароля."""
        if not session or session.get('kind') != 'staff':
            return 401, err('auth_required', 'staff session required')
        login = session.get('sub') or session.get('actor') or ''
        ticket = self.identity_store.reader_for_staff(login)
        if not ticket:
            return 404, err('not_found', 'no reader ticket linked')
        mfn = self._oidc_lookup_mfn(ticket)
        token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                     tenant=session.get('tenant', DEFAULT_TENANT), rdr_mfn=mfn)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            login, 'identity.view_as_reader', None, mfn or None, 'ok', {'ticket': ticket})
        return 200, ok({'token': token, 'kind': 'reader', 'ticket': ticket, 'mfn': mfn})

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
        # Демо/QA-читатель (env-gated, по умолчанию ВЫКЛ). Когда заданы оба
        # TEST_READER_TICKET/TEST_READER_PASS — вход в портал по этому
        # билет+паролю БЕЗ записи RDR: ИРБИС не трогаем, auth реальных читателей
        # (ниже) не ослабляем. Только для пилотов/демо.
        demo_ticket = self.cfg.test_reader_ticket
        demo_pass = self.cfg.test_reader_pass
        if demo_ticket and demo_pass and ticket == demo_ticket:
            if password != demo_pass:
                store.audit('RI=%s' % ticket, 'auth.reader', None, None, 'denied')
                return 401, err('auth_failed', 'invalid credentials')
            token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                         tenant=tenant, rdr_mfn=0)
            store.audit('RI=%s' % ticket, 'auth.reader', None, None, 'ok_demo')
            return 200, ok({'token': token, 'kind': 'reader',
                            'name': 'Демо-читатель', 'mfn': 0, 'demo': True})
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

    # --- Плагины авторизации: вход через внешний OIDC (узел 3, MVP-2b) --------
    # Явная привязка: внешняя личность (provider, subject) ↔ читательский билет.
    # Привязку создаёт сам читатель (вошёл билет+пароль → подтвердил), поэтому
    # OIDC-вход НИКОГДА не обходит пароль для непривязанной личности — первый раз
    # отдаёт handoff, по которому привязка возможна только из читательской сессии.
    def _oidc_enabled(self):
        return bool(self.cfg.oidc_provider and self._oidc_pcfg.get('authorize')
                    and self.cfg.oidc_client_id and self.oidc_store is not None)

    def _oidc_lookup_mfn(self, ticket):
        """RDR-mfn по билету для контекста сессии. 0, если ИРБИС off / нет записи."""
        try:
            _c, mfns = self.irbis.search('RDR', '"RI=%s"' % ticket)
            return mfns[0] if mfns else 0
        except Exception:
            return 0

    def auth_oidc_providers(self):
        """GET /api/auth/oidc/providers — настроенный провайдер для кнопки входа
        (пусто, если OIDC выключен). Публичный."""
        if not self._oidc_enabled():
            return 200, ok({'providers': []})
        return 200, ok({'providers': [{
            'provider': self.cfg.oidc_provider,
            'label': self._oidc_pcfg.get('label', self.cfg.oidc_provider)}]})

    def auth_oidc_start(self, session, query):
        """GET /api/auth/oidc/start?intent=login|bind — authorize-URL + подписанный
        state. intent=bind ТРЕБУЕТ читательскую сессию (билет вшивается в state,
        подписанный нами → callback ему доверяет)."""
        if not self._oidc_enabled():
            return 404, err('unavailable', 'oidc disabled')
        intent = (query.get('intent', ['login'])[0] or 'login')
        if intent not in ('login', 'bind'):
            return 400, err('bad_request', 'bad intent')
        st = {'oidc': 'state', 'intent': intent, 'nonce': _oidc.new_state()}
        if intent == 'bind':
            if not session or session.get('kind') != 'reader':
                return 401, err('auth_required', 'reader session required to bind')
            st['ticket'] = (session.get('sub') or '')[3:]   # 'RI=<ticket>' → ticket
        state = _jwt.encode(st, self.jwt_secret, ttl_seconds=600)
        url = _oidc.build_authorize_url(self._oidc_pcfg, self.cfg.oidc_client_id,
                                        self.cfg.oidc_redirect_uri, state)
        return 200, ok({'url': url, 'state': state, 'provider': self.cfg.oidc_provider})

    def auth_oidc_callback(self, body):
        """POST /api/auth/oidc/callback {code, state} — завершить OIDC-поток (SPA
        зовёт после редиректа провайдера). Проверяет подпись+exp state, обменивает
        код, тянет userinfo, берёт claim (subject). intent=login: привязано →
        читательская сессия; не привязано → handoff для шага привязки. intent=bind:
        создаёт привязку (provider, subject)↔ticket из подписанного state."""
        if not self._oidc_enabled():
            return 404, err('unavailable', 'oidc disabled')
        code = (body.get('code') or '').strip()
        state = (body.get('state') or '').strip()
        if not code or not state:
            return 400, err('bad_request', 'code and state required')
        try:
            st = _jwt.decode(state, self.jwt_secret)
        except _jwt.JwtError:
            return 400, err('bad_state', 'invalid or expired state')
        if st.get('oidc') != 'state':
            return 400, err('bad_state', 'bad state')
        try:
            tok = _oidc.exchange_code(self._oidc_pcfg, self.cfg.oidc_client_id,
                                      self.cfg.oidc_client_secret, code,
                                      self.cfg.oidc_redirect_uri)
            userinfo = _oidc.fetch_userinfo(self._oidc_pcfg, tok.get('access_token') or '')
        except Exception:
            return 502, err('oidc_provider', 'provider exchange failed')
        subject = _oidc.claim_value(self._oidc_pcfg, userinfo)
        if not subject:
            return 502, err('oidc_provider', 'no subject claim in userinfo')
        provider = self.cfg.oidc_provider
        store = self._store_for(DEFAULT_TENANT)
        if st.get('intent') == 'bind':
            ticket = st.get('ticket') or ''
            if not ticket:
                return 400, err('bad_state', 'no ticket in bind state')
            self.oidc_store.link(provider, subject, ticket)
            store.audit('RI=%s' % ticket, 'auth.oidc.bind', None, None, 'ok',
                        {'provider': provider})
            return 200, ok({'bound': True, 'linked': True, 'provider': provider})
        # intent == login
        ticket = self.oidc_store.ticket_for(provider, subject)
        if not ticket:
            handoff = _jwt.encode({'oidc': 'handoff', 'provider': provider,
                                   'subject': subject}, self.jwt_secret, ttl_seconds=600)
            store.audit('oidc:%s' % provider, 'auth.oidc.login', None, None, 'unbound')
            return 200, ok({'bound': False, 'handoff': handoff, 'provider': provider})
        mfn = self._oidc_lookup_mfn(ticket)
        token, _ = self._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                                     tenant=DEFAULT_TENANT, rdr_mfn=mfn)
        store.audit('RI=%s' % ticket, 'auth.oidc.login', None, mfn or None, 'ok',
                    {'provider': provider})
        return 200, ok({'bound': True, 'token': token, 'kind': 'reader',
                        'ticket': ticket, 'mfn': mfn, 'via': provider})

    def auth_oidc_bind(self, session, body):
        """POST /api/auth/oidc/bind {handoff} — привязать ранее НЕпривязанную
        OIDC-личность (из handoff'а unbound-входа) к билету ТЕКУЩЕГО читателя.
        Требует читательскую сессию (он вошёл билет+пароль) → доказана и внешняя
        личность (handoff подписан нами после реального OIDC-callback), и владение
        билетом (парольная сессия). Без обоих — привязки нет."""
        if not session or session.get('kind') != 'reader':
            return 401, err('auth_required', 'reader session required')
        handoff = (body.get('handoff') or '').strip()
        if not handoff:
            return 400, err('bad_request', 'handoff required')
        try:
            h = _jwt.decode(handoff, self.jwt_secret)
        except _jwt.JwtError:
            return 400, err('bad_handoff', 'invalid or expired handoff')
        if h.get('oidc') != 'handoff':
            return 400, err('bad_handoff', 'bad handoff')
        ticket = (session.get('sub') or '')[3:]
        provider, subject = h.get('provider'), h.get('subject')
        if not (provider and subject and ticket):
            return 400, err('bad_request', 'incomplete bind')
        self.oidc_store.link(provider, subject, ticket)
        self._store_for(DEFAULT_TENANT).audit(
            'RI=%s' % ticket, 'auth.oidc.bind', None, None, 'ok',
            {'provider': provider, 'via': 'handoff'})
        return 200, ok({'linked': True, 'provider': provider})

    def _brief_item(self, db, mfn):
        """Structured result item (title/author/year/docType/availability) for cards."""
        # ДЕМО/own-store (#374): для баз OWN_SEARCH_DBS бриф строим из own-store (без
        # ИРБИС) — чтобы заглавия в бронях/формуляре/полках резолвились в демо, а не
        # были «MFN N». Прод (пустой флаг) — прежний путь через ИРБИС.
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            own = self._own_record(db, mfn)
            if own is not None:
                return self._brief_from_record(mfn, own)
            return {'mfn': mfn, 'title': 'MFN %d' % mfn, 'availability': 'unknown'}
        try:
            rec = self.irbis.read_record(db, mfn)
        except IrbisError:
            return {'mfn': mfn, 'title': 'MFN %d' % mfn, 'availability': 'unknown'}
        return self._brief_from_record(mfn, rec)

    def _brief_from_record(self, mfn, rec):
        """Тот же структурный бриф, но из УЖЕ загруженной записи — чтобы own-index
        путь поиска (#229, в обход сломанного ИРБИС-K=) строил идентичную форму
        карточки без чтения записи из ИРБИС по каждому MFN."""
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
        # #229/#262: базы из OWN_SEARCH_DBS — поиск (одиночный И составной: +/*/^,
        # скобки) обслуживаем из НАШЕГО индекса (CatalogStore), в обход ИРБИС (напр.
        # сломанный K=). Флаг по умолчанию пуст → ветка не срабатывает, прод не меняется.
        if (self.catalog is not None and db.upper() in self.cfg.own_search_dbs
                and '=' in (expr or '')):
            start = (page - 1) * page_size
            res = self.catalog.search_items(db, expr, page_size, start)
            return 200, ok({'db': db, 'expr': expr, 'total': res['total'], 'page': page,
                            'pageSize': page_size, 'items': res['items'], 'source': 'own'})
        # NB (#233 revert): IRBIS 'K' returns the FULL MFN list regardless of maxn
        # (verified on the СПб ГТБ server — maxn is ignored), so windowing must be
        # CLIENT-SIDE. MFN transfer is cheap; the expensive cost is reading records
        # (_brief_item), so we slice to just this page's MFNs and read only those.
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

    @staticmethod
    def _own_to_fields(record):
        """Own-store запись (tag-keyed) -> список fields как у ``irbis.parse_record``.

        Каждое поле -> ``{tag, value:'^a..^b..', text, subfields}``. '' / None-ключ
        подполя = «голова» поля (без подполей). Служебные ('*mfn' и т.п.) и
        нецифровые теги пропускаются. Используется демо-фолбэком ``_own_record``."""
        from irbis.parser import parse_subfields
        out = []
        for tag, insts in (record or {}).items():
            st = str(tag)
            if not st.isdigit():
                continue
            for inst in (insts if isinstance(insts, list) else [insts]):
                if isinstance(inst, dict):
                    head, parts = '', []
                    for k, v in inst.items():
                        sv = '' if v is None else str(v)
                        if k in ('', None):
                            head = sv
                        else:
                            parts.append('^%s%s' % (k, sv))
                    value = head + ''.join(parts)
                else:
                    value = '' if inst is None else str(inst)
                h, subs = parse_subfields(value)
                out.append({'tag': st, 'value': value, 'text': h, 'subfields': subs})
        return out

    def _own_record(self, db, mfn):
        """Запись из own-store CatalogStore в форме ``record()`` (демо/own-store, #374).

        None, если каталога нет или запись отсутствует. Бриф — через ``catalog.brief``
        (PFT поверх own-store), мягко -> '' при ошибке."""
        if self.catalog is None:
            return None
        try:
            record = self.catalog.get(db, int(mfn))
        except Exception:
            record = None
        if record is None:
            return None
        try:
            brief = self.catalog.brief(db, int(mfn)) or ''
        except Exception:
            brief = ''
        return {'mfn': int(mfn), 'status': '0', 'version': 0, 'guid': None,
                'fields': self._own_to_fields(record), 'brief': brief}

    def record(self, session, db, mfn):
        self._guard(session, 'record.read', db, 'read')
        self._public_db_guard(session, db)
        # ДЕМО/own-store (#229/#374): базы из OWN_SEARCH_DBS обслуживаются из НАШЕГО
        # каталога в обход ИРБИС (search() уже так делает) — распространяем на деталь
        # записи, чтобы экраны работали без живого ИРБИС. Прод (пустой флаг) — как был.
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            rec = self._own_record(db, mfn)
            if rec is None:
                return 404, err('not_found', 'record %s/%s not found' % (db, mfn))
            rec['db'] = db
            rec['hasCover'] = any(f['tag'] == '953' for f in rec['fields'])
            self._log_history(session, db, mfn)
            return 200, ok(rec)
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
        # ДЕМО/own-store (#374): для own_search_dbs рендерим бриф из own-store.
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            try:
                rendered = self.catalog.brief(db, int(mfn)) or ''
            except Exception:
                rendered = ''
            return 200, ok({'db': db, 'mfn': mfn, 'fmt': fmt, 'rendered': rendered})
        return 200, ok({'db': db, 'mfn': mfn, 'fmt': fmt,
                        'rendered': self.irbis.format_record(db, mfn, fmt)})

    def _read_terms(self, db, anchor, count):
        """Словарь терминов (count, term) — own-store для баз OWN_SEARCH_DBS (#374),
        иначе живой ИРБИС. ``anchor`` = ``'PREFIX=term'`` (или ``'PREFIX='``). Чинит
        указатель словаря и подсказки «вы имели в виду» в демо без ИРБИС."""
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            prefix, _eq, term = (anchor or '').partition('=')
            return self.catalog.dictionary(db, prefix, term, count)
        return self.irbis.read_terms(db, anchor, count)

    def terms(self, session, db, start, count):
        self._guard(session, 'terms', db, 'read')
        self._public_db_guard(session, db)
        rows = self._read_terms(db, start, count)
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
                got = self._read_terms(db, anchor, self._SUGGEST_SCAN)
            except (IrbisError, Exception):
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
            rows = self._read_terms(db, seek, limit)
        except (IrbisError, Exception):
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
                rows = self._read_terms(db, prefix + '=', max(limit * 3, 24))
            except (IrbisError, Exception):
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
        # ДЕМО/own-store (#374): счётчик из own-store для баз OWN_SEARCH_DBS.
        if code.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            try:
                return int(self.catalog.count(code))
            except Exception:
                return None
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
        try:
            txt = self.irbis.read_file(self.cfg.db_menu)
            lines = [x.strip() for x in txt.splitlines() if x.strip() and x.strip() != '*****']
        except Exception:
            lines = []   # ИРБИС недоступен/None (демо) -> фолбэк меню ниже
        if not lines:
            # ДЕМО/own-store (#374): меню баз из публичного allow-list, когда ИРБИС
            # недоступен — чтобы селектор баз (мульти-БД) работал без живого сервера.
            _names = {'IBIS': 'Электронный каталог', 'PERIO': 'Периодические издания',
                      'NTD': 'Нормативно-техническая документация'}
            for code in sorted(self.cfg.public_dbs):
                lines += [code, _names.get(code, code)]
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
        if mfn == 0:
            self._webhooks_emit(session.get('tenant', DEFAULT_TENANT), 'record.created',
                                {'db': db, 'mfn': assigned})
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

    # ------------------------------------------------------------------- #
    # Глобальная корректировка (.gbl) по выборке записей каталога — ребро
    # 11.2 INTEGRATION_MAP. Замыкает шов «интерпретатор gbl (access/gbl.py) ↔
    # собственный стор каталога (access/catalog.py)»: эндпоинт прогоняет
    # распарсенное задание .gbl по явной выборке MFN, читая/сохраняя записи
    # через CatalogStore (НЕ через живой ИРБИС — та же посадка, что у
    # circulation/holds/acquisition, #222).
    # ------------------------------------------------------------------- #
    def _gbl_resolver(self, db):
        """Построить ``resolver(db, term) -> record | None`` поверх CatalogStore.

        CORREC резолвит чужую запись ПО ТЕРМИНУ (значение из ФОРМАТ-словаря,
        напр. инв.№/штрих-код или ``PREFIX=term``). Стратегия резолва:
          1. голый integer ⇒ это MFN — прямое чтение ``catalog.get``;
          2. иначе пробуем как инв.№/штрих-код экземпляра (``find_exemplar`` →
             MFN-владелец) — типовой кейс кросс-БД заданий (InsteadLost ищет по
             ``IN=``);
          3. иначе как поисковое выражение (``search_records``) — берём первую
             запись совпадения.

        Резолвленный MFN планируется в служебное поле ``*mfn`` записи, чтобы
        ``emit`` обновил ИМЕННО эту запись (а не вставил дубль с новым MFN).
        ``*``-теги сохраняются ``normalize_record`` и игнорируются ``diff_records``
        (как и статус-маркеры), так что в БО они не попадают. Возвращает запись
        (``tag -> [...]``) или None (промах — gbl запишет его в ``correc_misses``,
        не падая)."""
        def _tag(rec, target_db, mfn):
            rec = dict(rec)
            rec['*db'] = target_db
            rec['*mfn'] = mfn
            return rec

        def resolver(target_db, term):
            if self.catalog is None:
                return None
            t = str(term).strip()
            if not t:
                return None
            # 1) голый MFN
            if t.isdigit():
                rec = self.catalog.get(target_db, int(t))
                if rec is not None:
                    return _tag(rec, target_db, int(t))
            # 2) инв.№/штрих-код экземпляра → запись-владелец
            try:
                found = self.catalog.find_exemplar(target_db, t)
                if found is not None:
                    rec = self.catalog.get(target_db, found[0])
                    if rec is not None:
                        return _tag(rec, target_db, found[0])
            except Exception:
                pass
            # 3) поисковое выражение (PREFIX=term) → первая запись
            try:
                res = self.catalog.search_records(target_db, t, limit=1)
                items = res.get('items') or []
                if items:
                    return _tag(items[0]['record'], target_db, items[0]['mfn'])
            except Exception:
                pass
            return None
        return resolver

    def _gbl_emit(self, db, results, audit_actor, tenant):
        """Построить ``emit(db, record) -> mfn`` поверх CatalogStore.

        Персистит созданную (NEWMFN/NEWREC) или кросс-правленую (CORREC) ЧУЖУЮ
        запись через ``catalog.save`` (та же запись персиста, что у обычного
        ``save_record``: ФЛК + переиндексация). Если запись несёт служебный
        ``*mfn`` (CORREC резолвил существующую запись — см. ``_gbl_resolver``),
        это UPDATE по тому MFN; иначе INSERT с новым MFN (NEWMFN/NEWREC). Служебные
        ``*``-теги вычищаются перед персистом, чтобы не попасть в БО. MFN
        присваивается/подтверждается стором; ``save`` возвращает его в ``mfn``.
        Накапливает аудит-сводку в ``results`` и пишет строку аудита (как соседние
        write-эндпоинты). Если ``save`` отклонил запись (severity-1 ФЛК) —
        поднимаем ``CatalogError``, чтобы вызывающий пометил конкретную запись
        ошибкой, а не молча потерял правку."""
        def emit(target_db, record):
            if self.catalog is None:
                raise CatalogError('catalog store not configured')
            # CORREC: UPDATE по резолвленному MFN. ``*mfn`` мог пройти через
            # ``normalize_record`` (стать ``[{'': '2'}]``) — снимаем оба варианта.
            existing_mfn = _unwrap_mfn(record.pop('*mfn', None))
            # вычистить все служебные '*'-теги (db/mfn/статус) из БО.
            for k in [t for t in record if isinstance(t, str) and t.startswith('*')]:
                record.pop(k, None)
            save_kwargs = {'mfn': existing_mfn} if existing_mfn is not None else {}
            saved = self.catalog.save(target_db, record, **save_kwargs)
            if not saved.get('saved'):
                raise CatalogError(
                    'ФЛК отклонил запись (severity-1) при emit в %s' % target_db)
            mfn = saved['mfn']
            results.append({'db': target_db, 'mfn': mfn})
            try:
                self._store_for(tenant).audit(
                    audit_actor, 'cat.gbl', target_db, mfn, 'ok',
                    {'op': 'emit'})
            except Exception:
                pass
            return mfn
        return emit

    def cataloging_gbl(self, session, body):
        """POST /api/cataloging/gbl — исполнить глобальную корректировку .gbl по
        явной выборке записей каталога (ребро 11.2 INTEGRATION_MAP).

        Тело запроса::

            { "db": "IBIS",                  # БД каталога (по умолчанию db_default)
              "mfns": [12, 34, ...],         # явная выборка MFN
              "gbl": "<текст .gbl>",         # задание (str CP1251/utf8 ИЛИ {params,body})
              "params": {"1": "20240101"},   # опц. значения параметров %1..%9
              "mode": "preview" | "apply" }  # сухой прогон ИЛИ персист (по умолчанию preview)

        Гард: только сотрудник с правом каталогизации (``cat.gbl``/write) —
        гость/читатель → 403 (``_require_staff`` + ``_guard`` + ``_public_db_guard``).
        Энтайтлмент-гейт (FUNCTION_MODULE → 'cataloging') действует тоже.

        Семантика:
          * парсинг через ``access.gbl.parse`` (ParseError → 400);
          * ``format_eval`` НЕ задаётся явно — ``gbl`` сам делегирует его в реальный
            PFT-движок ``access.pft.eval`` (он импортируем); параметры ``%1..%9``
            прокидываются через ``ctx['params']``;
          * ``resolver``/``emit`` завязаны на CatalogStore (см. ``_gbl_resolver`` /
            ``_gbl_emit``): resolver — чтение чужой записи по терму, emit — персист
            созданной/правленой записи с возвратом MFN;
          * ``mode=preview`` — возврат предпросмотра (before/after + дельта полей +
            что СОЗДАЛОСЬ бы (NEWMFN) и кросс-правилось бы (CORREC)); НИЧЕГО не
            персистится (хост-emit подавлен внутри ``preview``);
          * ``mode=apply`` — каждая запись выборки правится и персистится обратно
            (DELR ⇒ логическое удаление, EMPTY ⇒ опустошение), чужие созданные/
            правленые записи эмитятся, пишется аудит. Ошибка отдельной записи
            оборачивается (per-record ``status='error'``) — пачка не падает целиком.

        Возврат ``{db, mode, processed, changed, deleted, emptied, errors,
        createdCount, correcCount, records:[...]}``; в режиме preview ``records``
        несёт дельту/before/after, в режиме apply — итоговый статус по каждой MFN."""
        self._require_staff(session)
        db = (body.get('db') or self.cfg.db_default)
        self._guard(session, 'cat.gbl', db, 'write')
        self._public_db_guard(session, db)
        if self.catalog is None:
            return 503, err('unavailable', 'catalog store not configured')
        mfns = body.get('mfns') or []
        if not isinstance(mfns, list):
            return 400, err('bad_request', 'mfns must be a list')
        mode = (body.get('mode') or 'preview').strip().lower()
        if mode not in ('preview', 'apply'):
            return 400, err('bad_request', "mode must be 'preview' or 'apply'")
        # Распарсить задание (текст .gbl ИЛИ уже-распарсенный Program-словарь).
        raw = body.get('gbl')
        if isinstance(raw, dict) and 'body' in raw:
            ast = raw
        else:
            if not raw:
                return 400, err('bad_request', 'gbl text required')
            try:
                ast = _gbl.parse(raw)
            except _gbl.ParseError as e:
                return 400, err('bad_request', 'gbl parse error: %s' % e)
        params = body.get('params') or {}
        tenant = session.get('tenant', DEFAULT_TENANT)
        actor = session['actor']

        # Прочитать выборку записей (отсутствующие MFN помечаем, не падаем).
        loaded = []          # (mfn, record | None)
        for m in mfns:
            try:
                mi = int(m)
            except (TypeError, ValueError):
                loaded.append((m, None))
                continue
            loaded.append((mi, self.catalog.get(db, mi)))

        if mode == 'preview':
            return self._gbl_preview(db, ast, params, loaded)
        return self._gbl_apply(db, ast, params, loaded, tenant, actor)

    def _gbl_preview(self, db, ast, params, loaded):
        """Сухой прогон .gbl по выборке: дельта по каждой записи + что создалось/
        кросс-правилось бы. Ничего не персистит (``gbl.preview`` чист)."""
        records, present = [], []
        for mfn, rec in loaded:
            if rec is None:
                records.append({'mfn': mfn, 'status': 'missing', 'changes': []})
                continue
            present.append((mfn, rec))
        # gbl.preview принимает список записей; пройдём их одним вызовом, но нам
        # нужны MFN рядом с каждой дельтой — прогоняем по одной, чтобы не терять
        # привязку (выборки малы; per-record изоляция — это и есть AC9).
        for mfn, rec in present:
            ctx = {'db': db, 'params': params,
                   'resolver': self._gbl_resolver(db)}
            rep = _gbl.preview(ast, [rec], ctx)[0]
            rep['mfn'] = mfn
            records.append(rep)
        changed = sum(1 for r in records if r.get('status') == 'changed')
        deleted = sum(1 for r in records if r.get('status') == 'deleted')
        emptied = sum(1 for r in records if r.get('status') == 'emptied')
        errors = sum(1 for r in records if r.get('status') == 'error')
        created = sum(len(r.get('created') or []) for r in records)
        correc = sum(len(r.get('correc') or []) for r in records)
        return 200, ok({
            'db': db, 'mode': 'preview', 'processed': len(loaded),
            'changed': changed, 'deleted': deleted, 'emptied': emptied,
            'errors': errors, 'createdCount': created, 'correcCount': correc,
            'records': records,
        })

    def _gbl_apply(self, db, ast, params, loaded, tenant, actor):
        """Исполнить .gbl по выборке и ПЕРСИСТИТЬ результат через CatalogStore.

        По каждой записи: ``gbl.apply`` (с resolver/emit поверх стора), затем
        персист обратно (``save``/``delete``), аудит. Ошибка отдельной записи
        изолируется в per-record статус — пачка не падает целиком."""
        emitted = []                              # сводка emit (NEWMFN/CORREC)
        emit = self._gbl_emit(db, emitted, actor, tenant)
        resolver = self._gbl_resolver(db)
        records = []
        changed = deleted = emptied = errors = 0
        for mfn, rec in loaded:
            if rec is None:
                records.append({'mfn': mfn, 'status': 'missing'})
                continue
            ctx = {'db': db, 'params': params, 'resolver': resolver, 'emit': emit}
            try:
                before = _gbl.normalize_record(rec)
                after = _gbl.apply(ast, rec, ctx)
                state = ctx.get('_state', {})
                if state.get('emptied'):
                    # EMPTY очистил запись — логически удаляем её из стора.
                    self.catalog.delete(db, mfn)
                    status = 'emptied'
                    emptied += 1
                elif state.get('deleted'):
                    # DELR — логическое удаление записи.
                    self.catalog.delete(db, mfn)
                    status = 'deleted'
                    deleted += 1
                else:
                    diff = _gbl.diff_records(before, after)
                    if diff:
                        saved = self.catalog.save(db, after, mfn=mfn)
                        if not saved.get('saved'):
                            raise CatalogError('ФЛК отклонил запись (severity-1)')
                        status = 'changed'
                        changed += 1
                    else:
                        status = 'unchanged'
                try:
                    self._store_for(tenant).audit(
                        actor, 'cat.gbl', db, mfn, 'ok',
                        {'mode': 'apply', 'status': status,
                         'putlog': state.get('putlog', [])})
                except Exception:
                    pass
                records.append({'mfn': mfn, 'status': status,
                                'putlog': state.get('putlog', [])})
            except Exception as e:                # изоляция одной записи (AC9)
                errors += 1
                records.append({'mfn': mfn, 'status': 'error', 'error': str(e)})
        return 200, ok({
            'db': db, 'mode': 'apply', 'processed': len(loaded),
            'changed': changed, 'deleted': deleted, 'emptied': emptied,
            'errors': errors, 'createdCount': len(emitted), 'emitted': emitted,
            'records': records,
        })

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
        server hiccup so recommendations never raise. ДЕМО/own-store (#374): для баз
        OWN_SEARCH_DBS термины берём из own-store (рекомендации работают без ИРБИС)."""
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            rec = self._own_record(db, mfn)
            if rec is None:
                return {'subjects': [], 'authors': [], 'collectives': []}
        else:
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
        # ДЕМО/own-store (#374): кандидатов по термину ищем в own-store CatalogStore
        # для баз OWN_SEARCH_DBS — рекомендации «Похожие» работают без ИРБИС.
        if db.upper() in self.cfg.own_search_dbs and self.catalog is not None:
            try:
                res = self.catalog.search(db, '%s=%s' % (prefix, term), limit=50, offset=0)
                return [it['mfn'] for it in res.get('items', [])]
            except Exception:
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
        self._webhooks_emit(session.get('tenant', DEFAULT_TENANT), 'hold.placed',
                            {'mfn': mfn, 'db': db, 'ticket': ticket})
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

    def place_holds_batch(self, session, body):
        """POST /api/holds/batch — оформить корзину читателя как заказы (ребро 10.2).

        Принимает корзину портала ``{items:[{db?, mfn}, …]}`` и персистит каждую
        позицию как бронь (own-store аналог RQST: «один движок, два клиента»)
        через ``HoldService.place_many``. Идемпотентно поэлементно; публичность
        каждой БД проверяется так же, как в одиночном ``place_hold``."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'order', self.cfg.db_default, 'write')
        items = []
        for it in (body.get('items') or []):
            db = (it.get('db') if isinstance(it, dict) else None) or self.cfg.db_default
            self._public_db_guard(session, db)
            items.append({'db': db,
                          'mfn': it.get('mfn') if isinstance(it, dict) else None})
        res = self.holds.place_many(ticket, items, default_db=self.cfg.db_default)
        return 200, ok(res)

    # ---- ИРИ/SDI (ребро 10.1) — reader-scoped ----------------------------- #
    def sdi_add(self, session, body):
        """POST /api/sdi/profile — завести постоянный запрос (RDR.140) читателя."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.sdi is None:
            return 200, ok({'profile': None})
        query = (body.get('query') or '').strip()
        if not query:
            return 400, err('bad_request', 'query required')
        db = (body.get('db') or self.cfg.db_default)
        self._public_db_guard(session, db)
        prof = self.sdi.add_profile(ticket, (body.get('name') or '').strip(),
                                    db, query)
        return 200, ok({'profile': prof})

    def sdi_list(self, session):
        """GET /api/sdi/profiles — постоянные запросы читателя."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.sdi is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.sdi.list_profiles(ticket)})

    def sdi_remove(self, session, body):
        """POST /api/sdi/profile/remove — удалить свой профиль."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.sdi is None:
            return 200, ok({'removed': False})
        try:
            pid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        if pid not in {p['id'] for p in self.sdi.list_profiles(ticket)}:
            return 404, err('not_found', 'profile not found')
        return 200, ok({'removed': self.sdi.remove_profile(pid)})

    def sdi_run(self, session, body):
        """POST /api/sdi/run — переиграть профиль(и) и вернуть НОВЫЕ попадания."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.sdi is None:
            return 200, ok({'profiles': 0, 'new_total': 0, 'results': []})
        pid = body.get('id')
        if pid is not None:
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                return 400, err('bad_request', 'id')
            if pid not in {p['id'] for p in self.sdi.list_profiles(ticket)}:
                return 404, err('not_found', 'profile not found')
            return 200, ok(self.sdi.run_profile(pid))
        return 200, ok(self.sdi.run_all(ticket))

    def sdi_new(self, session):
        """GET /api/sdi/new — накопленные новые попадания читателя."""
        ticket = self._reader_ticket(session)
        self._guard(session, 'cabinet', '*', 'read')
        if self.sdi is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.sdi.new_for_reader(ticket)})

    # ---- Сводный каталог SK (рёбра 8.1/8.2) ------------------------------- #
    def union_search(self, session, query, year):
        """GET /api/union/search — федеративный поиск по сводному каталогу."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.union is None:
            return 200, ok({'items': [], 'total': 0})
        items = self.union.search(query=query or None, year=year or None)
        return 200, ok({'items': items, 'total': len(items)})

    def union_ingest(self, session, body):
        """POST /api/union/ingest — свести запись участницы (сигла 902^s). Staff."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.union is None:
            return 200, ok({'union_id': None})
        sigla = (body.get('sigla') or '').strip()
        if not sigla:
            return 400, err('bad_request', 'sigla required')
        res = self.union.ingest(body.get('record') or {}, sigla,
                                source_db=body.get('db'),
                                source_mfn=body.get('mfn'))
        return 200, ok(res)

    # ---- Диспетч внешней доставки уведомлений (ребро 11.3) — admin -------- #
    def notifications_dispatch(self, session, body):
        """POST /api/admin/notifications/dispatch — прогнать очередь уведомлений
        в каналы (InApp всегда; внешние email/SMS — только по конфигу тенанта, по
        умолчанию OFF). Admin-grant."""
        self._guard(session, 'admin', '*', 'admin')
        if self.dispatch_worker is None:
            return 200, ok({'processed': 0, 'sent': 0, 'failed': 0, 'retried': 0})
        return 200, ok(self.dispatch_worker.run_once())

    # ---- ВКР (рёбра 7.6/8.3) ---------------------------------------------- #
    def vkr_submit(self, session, body):
        """POST /api/vkr — студент подаёт ВКР (любая авториз. читат. сессия)."""
        self._reader_ticket(session)
        if self.vkr is None:
            return 200, ok({'vkr': None})
        title = (body.get('title') or '').strip()
        if not title:
            return 400, err('bad_request', 'title required')
        rec = self.vkr.submit(title, (body.get('author') or '').strip(),
                              year=body.get('year'), faculty=body.get('faculty'),
                              speciality=body.get('speciality'),
                              file_ref=body.get('fileRef'))
        return 200, ok({'vkr': rec})

    def vkr_list(self, session, query):
        """GET /api/vkr — список ВКР (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.vkr is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.vkr.list(
            faculty=(query.get('faculty', [None])[0]),
            status=(query.get('status', [None])[0]))})

    def vkr_review(self, session, body):
        """POST /api/vkr/review — утвердить/отклонить ВКР (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.vkr is None:
            return 200, ok({'vkr': None})
        try:
            vid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        res = self.vkr.review(vid, approve=bool(body.get('approve', True)))
        if res is None:
            return 404, err('not_found', 'vkr not found')
        return 200, ok(res)

    # ---- КСУ авто-распределение (ребро 5.3) ------------------------------- #
    def ksu_distribute(self, session, body):
        """POST /api/ksu/distribute — авто-распределение партии (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.ksu_auto is None:
            return 200, ok({'titles': 0, 'copies': 0})
        items = body.get('items') or []
        ksu_no = body.get('ksuNo')
        if ksu_no:
            return 200, ok(self.ksu_auto.compute_and_store(ksu_no, items))
        return 200, ok(self.ksu_auto.compute(items))

    # ---- Периодика (рёбра 9.2/9.3) ---------------------------------------- #
    def serials_register(self, session, body):
        """POST /api/serials — завести журнал/многотомник (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.serials is None:
            return 200, ok({'serial': None})
        title = (body.get('title') or '').strip()
        if not title:
            return 400, err('bad_request', 'title required')
        try:
            rec = self.serials.register((body.get('kind') or '').strip(), title,
                                        issn=body.get('issn'),
                                        shifr=body.get('shifr'),
                                        source_mfn=body.get('mfn'))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'serial': rec})

    def serials_add_issue(self, session, body):
        """POST /api/serials/issue — добавить номер/том (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.serials is None:
            return 200, ok({'issue': None})
        try:
            sid = int(body.get('serialId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'serialId required')
        rec = self.serials.add_issue(sid, number=body.get('number'),
                                     year=body.get('year'),
                                     volume=body.get('volume'),
                                     source_mfn=body.get('mfn'))
        if rec is None:
            return 404, err('not_found', 'serial not found')
        return 200, ok({'issue': rec})

    def serials_search(self, session, query):
        """GET /api/serials/search — поиск сериалов (public-read)."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.serials is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.serials.find(
            (query.get('q', [''])[0] or '').strip())})

    # ---- DAM / файлы (ребро 7.1) ------------------------------------------ #
    def dam_attach(self, session, body):
        """POST /api/dam/attach — привязать бинарь 951/953/955 к записи (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.dam is None:
            return 200, ok({'asset': None})
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        db = (body.get('db') or self.cfg.db_default)
        kind = (body.get('kind') or '').strip()
        ref = (body.get('ref') or '').strip()
        if not kind or not ref:
            return 400, err('bad_request', 'kind/ref required')
        rec = self.dam.attach(db, mfn, kind, ref, pages=body.get('pages'),
                              mime=body.get('mime'),
                              rights_template=body.get('rightsTemplate'))
        return 200, ok({'asset': rec})

    def dam_assets(self, session, query):
        """GET /api/dam?db=&mfn= — бинари записи (public-read, закрытие 7.1)."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.dam is None:
            return 200, ok({'items': []})
        db = (query.get('db', [self.cfg.db_default])[0])
        try:
            mfn = int(query.get('mfn', ['0'])[0])
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        return 200, ok({'items': self.dam.assets_for(db, mfn)})

    # ===================================================================== #
    # Трек «Оцифровка» (PR #325): виртуальные выставки · IIIF-манифесты ·    #
    # OCR-полнотекст · OAI-PMH провайдер. Гварды: витрина выставок и поиск   #
    # OCR — public-read (search); правка выставок и индексация OCR —          #
    # cataloging write; OAI-PMH — публичный (анонимный харвестер). Все —      #
    # own-store/чисто-функциональны, живой ИРБИС не пишется (#222).           #
    # ===================================================================== #

    # ---- Виртуальные выставки (own-store ExhibitService) ------------------ #
    def exhibits_list(self, session, query):
        """GET /api/exhibits — опубликованные выставки (public-read витрина).

        Отдаёт ТОЛЬКО опубликованные подборки (черновики на витрину не попадают)."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.exhibits is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.exhibits.public_exhibits()})

    def exhibit_view(self, session, slug):
        """GET /api/exhibits/{slug} — публичный вид выставки + позиции (public-read).

        На витрине видны только ОПУБЛИКОВАННЫЕ выставки: черновик/неизвестный
        slug -> 404 (чтобы черновик нельзя было подсмотреть по прямой ссылке)."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.exhibits is None:
            return 404, err('not_found', 'exhibit not found')
        view = self.exhibits.view(slug)
        if view is None or not view['exhibit'].get('published'):
            return 404, err('not_found', 'exhibit not found')
        return 200, ok(view)

    def exhibit_create(self, session, body):
        """POST /api/exhibits — создать выставку-черновик (cataloging write).

        ``slug``/``title`` обязательны; дубликат ``slug`` -> 400. Флаг
        ``published`` публикует сразу (иначе создаётся черновик). Раздел
        «Оцифровка» гейтится тарифом (#331 Фаза 3): нет в тарифе -> 402/грейс."""
        self._guard(session, 'cataloging', '*', 'write')
        if self._matrix_section_verdict(session, 'digitization') == 'deny':
            raise Denied(402, 'payment_required',
                         'раздел «Оцифровка» не входит в тариф')
        if self.exhibits is None:
            return 200, ok({'exhibit': None})
        slug = (body.get('slug') or '').strip()
        title = (body.get('title') or '').strip()
        if not slug or not title:
            return 400, err('bad_request', 'slug/title required')
        try:
            ex = self.exhibits.create(slug, title,
                                      (body.get('description') or '').strip())
        except ValueError as e:
            return 400, err('bad_request', str(e))
        if body.get('published'):
            ex = self.exhibits.publish(slug)
        return 200, ok({'exhibit': ex})

    def exhibit_add_item(self, session, body):
        """POST /api/exhibits/item — добавить запись/образ в выставку (cataloging write).

        ``slug`` + ``mfn`` обязательны; ``db`` (по умолч. публичная), ``caption``,
        ``assetRef`` — опциональны. Неизвестный ``slug`` -> 400."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.exhibits is None:
            return 200, ok({'item': None})
        slug = (body.get('slug') or '').strip()
        if not slug:
            return 400, err('bad_request', 'slug required')
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        db = (body.get('db') or self.cfg.db_default)
        try:
            item = self.exhibits.add_record(
                slug, db, mfn, caption=(body.get('caption') or ''),
                asset_ref=(body.get('assetRef') or ''))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'item': item})

    def exhibit_publish(self, session, body):
        """POST /api/exhibits/publish — опубликовать/снять выставку (cataloging write).

        ``slug`` обязателен; ``published`` (по умолч. True) задаёт направление.
        Неизвестный ``slug`` -> 404."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.exhibits is None:
            return 200, ok({'exhibit': None})
        slug = (body.get('slug') or '').strip()
        if not slug:
            return 400, err('bad_request', 'slug required')
        if self.exhibits.get(slug) is None:
            return 404, err('not_found', 'exhibit not found')
        published = body.get('published', True)
        ex = (self.exhibits.publish(slug) if published
              else self.exhibits.unpublish(slug))
        return 200, ok({'exhibit': ex})

    # ---- IIIF Presentation v3 манифест (чисто-функциональный iiif.py) ----- #
    def iiif_manifest(self, session, query):
        """GET /api/iiif/manifest?db=&mfn= — IIIF Presentation v3 манифест (public-read).

        Собирает манифест из DAM-ассетов записи: каждый ассет с числом страниц
        (955^N) раскрывается в канвы (URL образа = ``<ref>/<page_no>``, размеры
        ``w``/``h`` из query или дефолт). Метка манифеста — краткое заглавие записи
        (best-effort OPAC-brief, деградирует до ``MFN N``). Нет страничных ассетов
        -> валидный манифест без канв. Гость/читатель ограничен публичной базой."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        db = (query.get('db', [self.cfg.db_default])[0])
        try:
            mfn = int(query.get('mfn', ['0'])[0])
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        if mfn <= 0:
            return 400, err('bad_request', 'mfn required')
        self._public_db_guard(session, db)
        from access import iiif as _iiif
        base = os.environ.get(
            'IIIF_BASE_URL', 'http://%s:%d/iiif' % (self.cfg.app_host, self.cfg.app_port))
        manifest_id = '%s/%s/%d/manifest' % (base.rstrip('/'), db, mfn)
        label = (self._hold_brief(db, mfn) or {}).get('title') or ('MFN %d' % mfn)
        try:
            w = int(query.get('w', ['1000'])[0])
            h = int(query.get('h', ['1414'])[0])
        except (TypeError, ValueError):
            w, h = 1000, 1414
        pages = []
        if self.dam is not None:
            for a in self.dam.assets_for(db, mfn):
                n = a.get('pages')
                if not n:
                    continue
                ref = (a.get('ref') or '').rstrip('/')
                for i in range(1, int(n) + 1):
                    pages.append({'page_no': i, 'image': '%s/%d' % (ref, i),
                                  'width': w, 'height': h})
        man = _iiif.manifest_from_pages(
            manifest_id, label, manifest_id + '/canvas/', pages)
        return 200, ok({'manifest': man, 'pages': len(pages)})

    # ---- OCR-полнотекст образов (own-store OcrService) -------------------- #
    def ocr_index(self, session, body):
        """POST /api/ocr/index — проиндексировать OCR-текст документа (cataloging write).

        ``assetRef`` обязателен; ``pages`` — список ``{page_no, text}`` (upsert по
        странице). Возвращает число обработанных страниц и итог по документу."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.ocr is None:
            return 200, ok({'indexed': 0})
        asset_ref = (body.get('assetRef') or '').strip()
        if not asset_ref:
            return 400, err('bad_request', 'assetRef required')
        pages = body.get('pages') or []
        n = self.ocr.index_document(asset_ref, pages,
                                    lang=(body.get('lang') or 'rus'))
        return 200, ok({'indexed': n, 'pageCount': self.ocr.page_count(asset_ref)})

    def ocr_search(self, session, query):
        """GET /api/ocr/search?q=[&assetRef=] — поиск по OCR-слою (public-read).

        Без ``assetRef`` — по всем документам (``{asset_ref,page_no,snippet}``); с
        ним — внутри одного (``{page_no,snippet}``). Пустой ``q`` -> []."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.ocr is None:
            return 200, ok({'hits': []})
        q = (query.get('q', [''])[0] or '').strip()
        asset_ref = (query.get('assetRef', [''])[0] or '').strip()
        hits = (self.ocr.search_in_document(asset_ref, q) if asset_ref
                else self.ocr.search_all(q))
        return 200, ok({'hits': hits})

    # ---- OCR-pipeline: очередь распознавания (job_queue + ocr, #240/#335) --- #
    def ocr_recognize(self, session, body):
        """POST /api/ocr/recognize — поставить документ в очередь OCR (cataloging write).

        Кладёт фоновую задачу (job_queue, kind ``ocr``): ``assetRef`` + ``pages``
        (страницы-сырьё). Реальное распознавание — воркером (``/api/ocr/process``)
        вне HTTP. Возвращает поставленную задачу. Очередь недоступна -> job null."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.job_queue is None:
            return 200, ok({'job': None})
        asset_ref = (body.get('assetRef') or '').strip()
        if not asset_ref:
            return 400, err('bad_request', 'assetRef required')
        try:
            priority = int(body.get('priority', 0))
        except (TypeError, ValueError):
            priority = 0
        job = self.job_queue.enqueue('ocr', payload={'assetRef': asset_ref,
                                                      'pages': body.get('pages') or []},
                                     priority=priority)
        return 200, ok({'job': job})

    def ocr_process(self, session, body):
        """POST /api/ocr/process — обработать следующую OCR-задачу очереди (super-admin).

        Воркер pipeline оцифровки: захватывает pending-задачу job_queue, индексирует
        её страницы в OCR-слой (поиск по тексту), завершает задачу с итогом. Не-ocr
        задачу возвращает в очередь (fail с пометкой). Пустая очередь -> job null."""
        self._require_super_admin(session)
        if self.job_queue is None or self.ocr is None:
            return 200, ok({'job': None})
        job = self.job_queue.claim()
        if job is None:
            return 200, ok({'job': None})
        if job.get('kind') != 'ocr':
            # чужой вид задачи — помечаем ошибкой, не индексируем
            return 200, ok({'job': self.job_queue.fail(job['id'], 'not an ocr job'),
                            'indexed': 0})
        payload = job.get('payload') or {}
        asset_ref = payload.get('assetRef') or ''
        pages = payload.get('pages') or []
        indexed = self.ocr.index_document(asset_ref, pages) if asset_ref else 0
        # Мост в морфо-FTS (#368): склеить текст страниц и проиндексировать с
        # морфологией+ранжированием. Best-effort — провал индекса не валит задачу.
        if asset_ref and self.search_index is not None:
            try:
                text = '\n'.join((p.get('text') or '') for p in pages)
                self.search_index.index('ocr:' + asset_ref, text,
                                        db='OCR', title=asset_ref)
            except Exception:
                pass
        done = self.job_queue.complete(job['id'], result={'indexed': indexed})
        return 200, ok({'job': done, 'indexed': indexed})

    # ---- OAI-PMH 2.0 провайдер метаданных (чисто-функциональный oai_pmh.py) - #
    def _oai_records(self, limit=200):
        """Записи публичной базы (own-store CatalogStore) для OAI-провайдера.

        tag-keyed dict + инжектированный ``mfn`` (его читает ``oai_identifier``).
        Источник — СВОЙ каталог (без обращения к живому ИРБИС). Пусто, если каталог
        недоступен."""
        out = []
        if self.catalog is None:
            return out
        db = self.cfg.db_default
        try:
            for mfn in self.catalog.list_mfns(db, limit=limit):
                rec = self.catalog.get(db, mfn)
                if rec is None:
                    continue
                rec = dict(rec)
                rec.setdefault('mfn', mfn)
                out.append(rec)
        except Exception:
            pass
        return out

    def oai(self, session, query):
        """GET /api/oai?verb= — OAI-PMH 2.0 провайдер метаданных каталога (public).

        Анонимный (харвестеры безсессионны), отдаёт только публичную базу в
        Dublin Core (``oai_dc``). Диспетч обязательных глаголов: Identify,
        ListMetadataFormats, GetRecord, ListRecords, ListIdentifiers. Записи — из
        собственного каталога (никогда не из живого ИРБИС). Неизвестный verb -> 400
        (badVerb), неподдерживаемый формат -> 400 (cannotDisseminateFormat)."""
        from access import oai_pmh as _oai
        verb = (query.get('verb', [''])[0] or '').strip()
        base_url = os.environ.get(
            'OAI_BASE_URL',
            'http://%s:%d/api/oai' % (self.cfg.app_host, self.cfg.app_port))
        if verb == 'Identify':
            return 200, ok({'verb': verb, 'Identify': _oai.identify(
                os.environ.get('OAI_REPO_NAME', 'Biblio OAI-PMH'), base_url,
                os.environ.get('OAI_ADMIN_EMAIL', 'admin@localhost'),
                _oai.DEFAULT_DATESTAMP)})
        if verb == 'ListMetadataFormats':
            return 200, ok({'verb': verb,
                            'ListMetadataFormats': _oai.list_metadata_formats()})
        prefix = (query.get('metadataPrefix', ['oai_dc'])[0] or 'oai_dc')
        if prefix != 'oai_dc':
            return 400, err('cannotDisseminateFormat', 'unsupported metadataPrefix')
        records = self._oai_records()
        if verb == 'GetRecord':
            ident = (query.get('identifier', [''])[0] or '').strip()
            if not ident:
                return 400, err('badArgument', 'identifier required')
            rec = _oai.get_record(records, ident)
            if rec is None:
                return 404, err('idDoesNotExist', 'no such record')
            return 200, ok({'verb': verb, 'GetRecord': rec})
        if verb == 'ListRecords':
            set_spec = (query.get('set', [None])[0])
            return 200, ok({'verb': verb, 'ListRecords':
                            _oai.list_records(records, set_spec=set_spec)})
        if verb == 'ListIdentifiers':
            return 200, ok({'verb': verb,
                            'ListIdentifiers': _oai.list_identifiers(records)})
        return 400, err('badVerb', 'unknown or missing verb')

    # ===================================================================== #
    # Батч own-store модулей (эпик #240): шаблоны метаданных по виду издания  #
    # (Каталогизатор) · очередь фоновых задач (pipeline оцифровки, admin) ·   #
    # time-boxed подписки читателя на коллекции (контур читателя).            #
    # ===================================================================== #

    # ---- Шаблоны метаданных по виду издания (TemplateService) ------------- #
    def templates_types(self, session, query):
        """GET /api/cataloging/templates — виды издания + шаблоны (cataloging read)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.metadata_templates is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.metadata_templates.types()})

    def template_skeleton(self, session, query):
        """GET /api/cataloging/template?type= — каркас полей под вид (cataloging read).

        Неизвестный тип -> 404."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.metadata_templates is None:
            return 404, err('not_found', 'templates unavailable')
        type_ = (query.get('type', [''])[0] or '').strip()
        if not type_:
            return 400, err('bad_request', 'type required')
        sk = self.metadata_templates.skeleton(type_)
        if sk is None:
            return 404, err('not_found', 'unknown template type')
        return 200, ok(sk)

    def template_save(self, session, body):
        """POST /api/cataloging/template — сохранить кастомный шаблон (cataloging write).

        ``type`` + ``fields`` (непустой список field-def с непустым ``tag``)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.metadata_templates is None:
            return 200, ok({'template': None})
        type_ = (body.get('type') or '').strip()
        if not type_:
            return 400, err('bad_request', 'type required')
        try:
            tpl = self.metadata_templates.save(
                type_, body.get('fields'), label=body.get('label'))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'template': tpl})

    # ---- Очередь фоновых задач (JobQueue) — pipeline оцифровки, admin ------ #
    def job_enqueue(self, session, body):
        """POST /api/jobs — поставить фоновую задачу (admin).

        ``kind`` обязателен; ``payload`` (dict), ``priority`` (int, больше=раньше)."""
        self._require_super_admin(session)
        if self.job_queue is None:
            return 200, ok({'job': None})
        kind = (body.get('kind') or '').strip()
        if not kind:
            return 400, err('bad_request', 'kind required')
        try:
            priority = int(body.get('priority', 0))
        except (TypeError, ValueError):
            priority = 0
        job = self.job_queue.enqueue(kind, payload=body.get('payload'),
                                     priority=priority)
        return 200, ok({'job': job})

    def jobs_list(self, session, query):
        """GET /api/jobs?status= — список задач + сводка очереди (super-admin)."""
        self._require_super_admin(session)
        if self.job_queue is None:
            return 200, ok({'items': [], 'stats': {'total': 0, 'by_status': {}}})
        status = (query.get('status', [None])[0])
        try:
            limit = min(500, max(1, int(query.get('limit', ['100'])[0])))
        except (TypeError, ValueError):
            limit = 100
        return 200, ok({'items': self.job_queue.list(status=status, limit=limit),
                        'stats': self.job_queue.stats()})

    def job_claim(self, session, body):
        """POST /api/jobs/claim — захватить следующую задачу воркером (admin).

        Пустая очередь -> ``job: null``."""
        self._require_super_admin(session)
        if self.job_queue is None:
            return 200, ok({'job': None})
        return 200, ok({'job': self.job_queue.claim()})

    def job_complete(self, session, body):
        """POST /api/jobs/complete — завершить задачу успехом (admin).

        ``id`` обязателен; ``result`` (dict) опц. Неизвестный id -> 404."""
        self._require_super_admin(session)
        if self.job_queue is None:
            return 200, ok({'job': None})
        try:
            jid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        job = self.job_queue.complete(jid, result=body.get('result'))
        if job is None:
            return 404, err('not_found', 'job not found')
        return 200, ok({'job': job})

    def job_fail(self, session, body):
        """POST /api/jobs/fail — завершить задачу ошибкой (super-admin).

        ``id`` обязателен; ``error`` (строка) опц. Неизвестный id -> 404."""
        self._require_super_admin(session)
        if self.job_queue is None:
            return 200, ok({'job': None})
        try:
            jid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        job = self.job_queue.fail(jid, error=(body.get('error') or ''))
        if job is None:
            return 404, err('not_found', 'job not found')
        return 200, ok({'job': job})

    # ---- Time-boxed подписки читателя на коллекции (CollectionSubscription) - #
    def collection_subscribe(self, session, body):
        """POST /api/me/collections — подписать читателя на коллекцию/выставку/запись.

        Reader-scoped. ``kind`` (collection|exhibit|record) + ``ref`` обязательны;
        ``from``/``to`` — окно дат ``YYYY-MM-DD`` (опц., открытая граница = None)."""
        ticket = self._reader_ticket(session)
        if self.collection_subs is None:
            return 200, ok({'subscription': None})
        try:
            sub = self.collection_subs.subscribe(
                ticket, (body.get('kind') or '').strip(),
                (body.get('ref') or '').strip(),
                date_from=(body.get('from') or None),
                date_to=(body.get('to') or None))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'subscription': sub})

    def collection_subs_list(self, session, query):
        """GET /api/me/collections?active=1 — подписки читателя (reader-scoped).

        ``active=1`` -> только активные на сегодня; иначе все."""
        ticket = self._reader_ticket(session)
        if self.collection_subs is None:
            return 200, ok({'items': []})
        active = query.get('active', ['0'])[0] in ('1', 'true', 'yes')
        items = (self.collection_subs.active(ticket) if active
                 else self.collection_subs.list(ticket))
        return 200, ok({'items': items})

    def collection_unsubscribe(self, session, body):
        """POST /api/me/collections/cancel — отменить СВОЮ подписку (reader-scoped)."""
        ticket = self._reader_ticket(session)
        if self.collection_subs is None:
            return 200, ok({'cancelled': False})
        try:
            sid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        return 200, ok({'cancelled': self.collection_subs.cancel(ticket, sid)})

    # ---- Авто-фасеты «поле→фасет» (FacetService) -------------------------- #
    def facet_config_list(self, session, query):
        """GET /api/facet-config — активный набор фасетов тенанта (cataloging read)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.facets_cfg is None:
            return 200, ok({'items': []})
        tenant = session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'items': self.facets_cfg.configured(tenant)})

    def facet_config_set(self, session, body):
        """POST /api/facet-config — завести/обновить facet-def (cataloging write).

        ``tag`` обязателен; ``subfield`` (опц., '' = поле-скаляр), ``label``,
        ``enabled``, ``sort``."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.facets_cfg is None:
            return 200, ok({'facet': None})
        tag = (body.get('tag') or '').strip()
        if not tag:
            return 400, err('bad_request', 'tag required')
        tenant = session.get('tenant', DEFAULT_TENANT)
        label = (body.get('label') or tag).strip()
        try:
            sort = int(body.get('sort', 0))
        except (TypeError, ValueError):
            sort = 0
        facet = self.facets_cfg.upsert(
            tenant, tag, (body.get('subfield') or ''), label,
            enabled=bool(body.get('enabled', True)), sort=sort)
        return 200, ok({'facet': facet})

    def facet_config_remove(self, session, body):
        """POST /api/facet-config/remove — удалить facet-def по id (cataloging write)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.facets_cfg is None:
            return 200, ok({'removed': False})
        try:
            fid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        return 200, ok({'removed': self.facets_cfg.remove(fid)})

    def facets_compute(self, session, body):
        """POST /api/facets/compute — подсчёт авто-фасетов по набору записей (cataloging read).

        Утилита превью: ``records`` — список tag-keyed записей; возвращает
        ``{key: [{value,count}...]}`` по активному набору фасетов тенанта."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.facets_cfg is None:
            return 200, ok({'facets': {}})
        tenant = session.get('tenant', DEFAULT_TENANT)
        records = body.get('records') or []
        return 200, ok({'facets': self.facets_cfg.compute(records, tenant=tenant)})

    # ---- Реестр IP-диапазонов организаций (IpAuthService) — admin --------- #
    def ip_ranges_list(self, session, query):
        """GET /api/admin/ip-ranges — список IP-диапазонов организаций (admin)."""
        self._guard(session, 'admin', '*', 'admin')
        if self.ip_auth is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.ip_auth.list()})

    def ip_range_add(self, session, body):
        """POST /api/admin/ip-ranges — добавить IP-диапазон организации (admin).

        ``cidr`` + ``org`` обязательны; ``role``/``label`` опц. Кривой CIDR/
        пустой org -> 400."""
        self._guard(session, 'admin', '*', 'admin')
        if self.ip_auth is None:
            return 200, ok({'range': None})
        try:
            rng = self.ip_auth.add_range(
                (body.get('cidr') or '').strip(), (body.get('org') or '').strip(),
                role=(body.get('role') or ''), label=(body.get('label') or ''))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'range': rng})

    def ip_range_remove(self, session, body):
        """POST /api/admin/ip-ranges/remove — удалить диапазон по id (admin)."""
        self._guard(session, 'admin', '*', 'admin')
        if self.ip_auth is None:
            return 200, ok({'removed': False})
        try:
            rid = int(body.get('id'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'id required')
        return 200, ok({'removed': self.ip_auth.remove(rid)})

    def ip_resolve(self, session, query):
        """GET /api/admin/ip-ranges/resolve?ip= — резолв IP→организация (admin).

        Диагностика провайдера IP-авто-входа: к какой организации отнесён IP
        (самый специфичный включённый диапазон) или ``null``."""
        self._guard(session, 'admin', '*', 'admin')
        if self.ip_auth is None:
            return 200, ok({'match': None})
        ip = (query.get('ip', [''])[0] or '').strip()
        if not ip:
            return 400, err('bad_request', 'ip required')
        return 200, ok({'match': self.ip_auth.resolve(ip)})

    # ---- Browse-указатели A–Z (чисто-функциональный browse_index) --------- #
    def _catalog_records(self, db, limit=500):
        """Записи базы из собственного CatalogStore (без живого ИРБИС).

        Источник для указателей/агрегаций own-store. Пусто, если каталог
        недоступен."""
        out = []
        if self.catalog is None:
            return out
        try:
            for mfn in self.catalog.list_mfns(db, limit=limit):
                rec = self.catalog.get(db, mfn)
                if rec is not None:
                    out.append(rec)
        except Exception:
            pass
        return out

    @staticmethod
    def _record_search_text(rec):
        """Поисковый текст каталожной записи для FTS (#368): заглавие/авторы/темы/аннотация.

        Собирает значения подполей ключевых БО-полей в одну строку: 200 (заглавие
        ^a/^b/^e/^f), 700/701/710 (авторы ^a/^b/^g), 606/610 (темы/коллектив),
        330/331 (аннотация/реферат). Поля повторяющиеся (list инстансов), подполя —
        dict или строка. Возвращает (title, text): title = первое 200^a; text = всё
        склеено пробелом (включая title)."""
        def vals(tag, keys):
            out = []
            raw = rec.get(tag)
            if raw is None:
                return out
            for inst in (raw if isinstance(raw, list) else [raw]):
                if isinstance(inst, dict):
                    for k, v in inst.items():
                        if (not keys or str(k).strip().lower() in keys) and v:
                            out.append(str(v))
                elif inst:
                    out.append(str(inst))
            return out
        title_parts = vals('200', {'a', 'b', 'e', 'f'})
        title = title_parts[0] if title_parts else ''
        parts = []
        parts += title_parts
        for tag, keys in (('700', {'a', 'b', 'g'}), ('701', {'a', 'b', 'g'}),
                          ('710', {'a', 'b'}), ('606', set()), ('610', set()),
                          ('330', set()), ('331', set())):
            parts += vals(tag, keys)
        return title, ' '.join(p for p in parts if p)

    def browse_terms(self, session, query):
        """GET /api/browse?db=&tag=&subfield= — указатель A–Z по полю (public-read).

        Перебор терминов (по умолчанию авторы 700^a) по первой букве со
        счётчиками: ``{letters:[...], buckets:{буква:[{term,count}]}}``. Источник —
        собственный каталог (own-store, без живого ИРБИС). Гость/читатель
        ограничен публичной базой."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        db = (query.get('db', [self.cfg.db_default])[0])
        self._public_db_guard(session, db)
        from access import browse_index as _bi
        tag = (query.get('tag', ['700'])[0] or '700').strip()
        subfield = (query.get('subfield', ['a'])[0] or '')
        records = self._catalog_records(db)
        return 200, ok(_bi.browse(records, tag, subfield))

    # ---- Матрица доступов / тарифы (admin, issue #331) -------------------- #
    def access_matrix_get(self, session, query):
        """GET /api/admin/access-matrix?tenant= — эффективная матрица тенанта (admin).

        По умолчанию — тенант текущей сессии. Резолвит из редактируемого стора
        тарифов: какие разделы/функции включены, лимиты (+à-la-carte), enforcement."""
        self._require_super_admin(session)
        from access import access_matrix as _am
        if self.tariffs is None:
            return 200, ok({'matrix': None})
        tenant = (query.get('tenant', [None])[0]) or session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'tenant': tenant, 'matrix': _am.resolve(self.tariffs, tenant),
                        'usage': self._tenant_usage(tenant)})

    def tariffs_table(self, session, query):
        """GET /api/admin/tariffs — данные редактируемой админ-таблицы (admin).

        Строки каталога (разделы/функции/ресурсы — SSOT) × колонки тарифов ×
        ячейки (included/value/enforcement)."""
        self._require_super_admin(session)
        from access import access_matrix as _am
        if self.tariffs is None:
            return 200, ok({'rows': _am.catalog_rows(), 'tariffs': [], 'cells': {}})
        return 200, ok(_am.editable_table(self.tariffs))

    def tariff_create(self, session, body):
        """POST /api/admin/tariffs — добавить тариф-колонку (admin)."""
        self._require_super_admin(session)
        if self.tariffs is None:
            return 200, ok({'tariff': None})
        name = (body.get('name') or '').strip()
        if not name:
            return 400, err('bad_request', 'name required')
        try:
            t = self.tariffs.create_tariff(name, title=(body.get('title') or name),
                                           sort=int(body.get('sort', 0)))
        except Exception:
            return 400, err('bad_request', 'tariff exists or invalid')
        return 200, ok({'tariff': t})

    def tariff_cell_set(self, session, body):
        """POST /api/admin/tariffs/cell — задать ячейку матрицы (admin).

        ``tariff`` + ``itemKey`` обязательны; ``included`` (bool), ``value`` (int),
        ``enforcement`` ('block'|'grace') — частичный апдейт (непереданные не
        затираются)."""
        self._require_super_admin(session)
        if self.tariffs is None:
            return 200, ok({'cell': None})
        tariff = (body.get('tariff') or '').strip()
        item_key = (body.get('itemKey') or '').strip()
        if not tariff or not item_key:
            return 400, err('bad_request', 'tariff/itemKey required')
        included = body.get('included')
        value = body.get('value')
        value = int(value) if isinstance(value, (int, float)) else None
        enforcement = body.get('enforcement')
        if enforcement is not None and enforcement not in ('block', 'grace'):
            return 400, err('bad_request', 'enforcement must be block|grace')
        try:
            cell = self.tariffs.set_entry(
                tariff, item_key,
                included=(bool(included) if included is not None else None),
                value=value, enforcement=enforcement)
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'cell': cell})

    def tariff_assign(self, session, body):
        """POST /api/admin/tariffs/assign — назначить тариф тенанту (admin)."""
        self._require_super_admin(session)
        if self.tariffs is None:
            return 200, ok({'assigned': None})
        tenant = (body.get('tenant') or '').strip()
        tariff = (body.get('tariff') or '').strip()
        if not tenant or not tariff:
            return 400, err('bad_request', 'tenant/tariff required')
        try:
            res = self.tariffs.assign_tenant(tenant, tariff)
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'assigned': res})

    def tariff_addon(self, session, body):
        """POST /api/admin/tariffs/addon — докупить à-la-carte пакет тенанту (admin).

        ``tenant`` + ``resource`` + ``packs`` + ``packSize``."""
        self._require_super_admin(session)
        if self.tariffs is None:
            return 200, ok({'addon': None})
        tenant = (body.get('tenant') or '').strip()
        resource = (body.get('resource') or '').strip()
        if not tenant or not resource:
            return 400, err('bad_request', 'tenant/resource required')
        try:
            packs = int(body.get('packs', 1))
            pack_size = int(body.get('packSize', 0))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'packs/packSize must be int')
        return 200, ok({'addon': self.tariffs.add_addon(tenant, resource, packs, pack_size)})

    def tariff_delete(self, session, body):
        """POST /api/admin/tariffs/delete — удалить тариф-колонку (admin)."""
        self._require_super_admin(session)
        if self.tariffs is None:
            return 200, ok({'removed': False})
        name = (body.get('name') or '').strip()
        if not name:
            return 400, err('bad_request', 'name required')
        return 200, ok({'removed': self.tariffs.delete_tariff(name)})

    # ---- Онбординг: режим развёртывания (super-admin, #335) --------------- #
    def deployment_catalog(self, session, query):
        """GET /api/admin/deployment/catalog — режимы×топологии для визарда (super-admin)."""
        self._require_super_admin(session)
        from access import deployment as _dep
        if self.deployment is not None:
            return 200, ok(self.deployment.catalog())
        return 200, ok({'modes': _dep.REPLACEMENT_MODES, 'topologies': _dep.TOPOLOGIES})

    def deployment_get(self, session, query):
        """GET /api/admin/deployment?tenant= — режим развёртывания тенанта (super-admin)."""
        self._require_super_admin(session)
        if self.deployment is None:
            return 200, ok({'deployment': None})
        tenant = (query.get('tenant', [None])[0]) or session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'deployment': self.deployment.resolve(tenant)})

    def deployment_set(self, session, body):
        """POST /api/admin/deployment — задать режим/топологию тенанта (super-admin)."""
        self._require_super_admin(session)
        if self.deployment is None:
            return 200, ok({'deployment': None})
        tenant = (body.get('tenant') or '').strip() or session.get('tenant', DEFAULT_TENANT)
        try:
            res = self.deployment.set(tenant, (body.get('mode') or '').strip(),
                                      (body.get('topology') or '').strip())
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'deployment': res, 'resolved': self.deployment.resolve(tenant)})

    def onboard_apply(self, session, body):
        """POST /api/admin/onboard — шаг «завершения» онбординга арендатора (super-admin).

        Оркестрирует одним вызовом: режим развёртывания (deployment) + базовый
        брендинг (library_config name/full_name). Возвращает резолв режима (с
        нужными подключениями) + конфиг — чтобы визард повёл к следующему шагу
        (настройка подключений ИРБИС/jirbis/инфорост по required_connections)."""
        self._require_super_admin(session)
        tenant = (body.get('tenant') or '').strip() or session.get('tenant', DEFAULT_TENANT)
        out = {'tenant': tenant}
        if self.deployment is not None and (body.get('mode') or '').strip():
            try:
                self.deployment.set(tenant, (body.get('mode') or '').strip(),
                                    (body.get('topology') or '').strip() or 'cloud')
            except ValueError as e:
                return 400, err('bad_request', str(e))
            out['deployment'] = self.deployment.resolve(tenant)
        if self.library_config is not None and (body.get('name') or body.get('fullName')):
            patch = {}
            if body.get('name'):
                patch['name'] = body.get('name')
            if body.get('fullName'):
                patch['full_name'] = body.get('fullName')
            out['config'] = self.library_config.update(tenant, patch)
        return 200, ok(out)

    # ---- Конфигурация библиотеки (брендинг/реквизиты, #335) --------------- #
    def library_config_public(self, session, query):
        """GET /api/library-config — публичная конфигурация библиотеки (public-read).

        Брендинг/реквизиты/контакты для читательского портала (заменяет
        захардкоженный tenantContent). Ничего секретного."""
        self._guard(session, 'search', self.cfg.db_default, 'read')
        if self.library_config is None:
            return 200, ok({'config': None})
        tenant = session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'config': self.library_config.public(tenant)})

    def library_config_get(self, session, query):
        """GET /api/admin/library-config — полная конфигурация (tenant-admin)."""
        self._require_admin(session, 'admin.users')
        if self.library_config is None:
            return 200, ok({'config': None})
        tenant = session.get('tenant', DEFAULT_TENANT)
        return 200, ok({'config': self.library_config.get(tenant)})

    def library_config_set(self, session, body):
        """POST /api/admin/library-config — частичный апдейт конфигурации (tenant-admin)."""
        self._require_admin(session, 'admin.users')
        if self.library_config is None:
            return 200, ok({'config': None})
        tenant = session.get('tenant', DEFAULT_TENANT)
        try:
            cfg = self.library_config.update(tenant, body or {})
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'config': cfg})

    # ---- Внешние подключения (ИРБИС/jirbis/инфорост, super-admin, #335) --- #
    def connections_list(self, session, query):
        """GET /api/admin/connections?tenant= — подключения тенанта (МАСКИРОВАННЫЕ, super-admin).

        Секреты наружу как ``***``; реальные значения — только внутреннему слою."""
        self._require_super_admin(session)
        from access import connections as _conn
        tenant = (query.get('tenant', [None])[0]) or session.get('tenant', DEFAULT_TENANT)
        hints = {k: _conn.FIELD_HINTS.get(k, []) for k in _conn.KINDS}
        items = self.connections.list(tenant) if self.connections else []
        return 200, ok({'items': items, 'kinds': list(_conn.KINDS), 'hints': hints})

    def connection_set(self, session, body):
        """POST /api/admin/connections — задать подключение (super-admin).

        ``kind`` (irbis|jirbis|inforost) + ``config``. Секрет, переданный как ``***``/
        пустой — не затирает ранее сохранённый. Возвращает МАСКИРОВАННЫЙ вид."""
        self._require_super_admin(session)
        if self.connections is None:
            return 200, ok({'connection': None})
        tenant = (body.get('tenant') or '').strip() or session.get('tenant', DEFAULT_TENANT)
        kind = (body.get('kind') or '').strip()
        config = body.get('config')
        try:
            res = self.connections.set(tenant, kind, config,
                                       enabled=bool(body.get('enabled', True)))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'connection': res})

    def connection_remove(self, session, body):
        """POST /api/admin/connections/remove — удалить подключение (super-admin)."""
        self._require_super_admin(session)
        if self.connections is None:
            return 200, ok({'removed': False})
        tenant = (body.get('tenant') or '').strip() or session.get('tenant', DEFAULT_TENANT)
        kind = (body.get('kind') or '').strip()
        return 200, ok({'removed': self.connections.remove(tenant, kind)})

    # ---- Импорт из Инфорост (источник оцифровки, super-admin, #240/#335) -- #
    def inforost_plan(self, session, body):
        """POST /api/admin/inforost/plan — сухой план импорта из инфорост-экспорта (super-admin).

        Тело ``export`` — выгрузка инфорост (коллекции/позиции/страницы); ответ —
        сводный план (выставки/записи/число образов), НИЧЕГО не пишет."""
        self._require_super_admin(session)
        if self.inforost is None:
            return 200, ok({'plan': None})
        return 200, ok({'plan': self.inforost.plan(body.get('export') or {})})

    def inforost_import(self, session, body):
        """POST /api/admin/inforost/import — зафиксировать импорт в журнал (super-admin).

        Регистрирует коллекции/позиции инфорост-экспорта в own-store журнал
        (идемпотентно по source_id). Возвращает ``{new, skipped, plan}``."""
        self._require_super_admin(session)
        if self.inforost is None:
            return 200, ok({'new': 0, 'skipped': 0})
        tenant = (body.get('tenant') or '').strip() or session.get('tenant', DEFAULT_TENANT)
        return 200, ok(self.inforost.import_log(tenant, body.get('export') or {}))

    def inforost_import_exhibits(self, session, body):
        """POST /api/admin/inforost/import-exhibits — создать выставки из инфорост-плана (super-admin).

        Каждая инфорост-коллекция -> выставка own-store (slug/title/описание) + её
        позиции (подпись + ссылка на оцифрованный образ). Идемпотентно: выставка с
        существующим slug пропускается. mfn позиций = 0 (плейсхолдер — каталожная
        запись создаётся отдельным проходом; здесь привязка к образу). Возвращает
        число созданных/пропущенных выставок."""
        self._require_super_admin(session)
        if self.inforost is None or self.exhibits is None:
            return 200, ok({'created': 0, 'skipped': 0})
        plan = self.inforost.plan(body.get('export') or {})
        created, skipped, items = 0, 0, 0
        for coll in plan.get('collections', []):
            slug = (coll.get('slug') or '').strip()
            if not slug or self.exhibits.get(slug) is not None:
                skipped += 1
                continue
            try:
                self.exhibits.create(slug, coll.get('title') or slug,
                                     coll.get('description') or '')
            except ValueError:
                skipped += 1
                continue
            for it in (coll.get('items') or []):
                assets = it.get('assets') or []
                self.exhibits.add_record(
                    slug, self.cfg.db_default, 0,
                    caption=(it.get('caption') or ''),
                    asset_ref=(assets[0] if assets else ''))
                items += 1
            if body.get('publish'):
                self.exhibits.publish(slug)   # сразу на витрину
            created += 1
        return 200, ok({'created': created, 'skipped': skipped, 'items': items})

    def inforost_import_records(self, session, body):
        """POST /api/admin/inforost/import-records — создать каталожные записи из плана (super-admin).

        Записи инфорост-плана сохраняются в собственный CatalogStore (own-store, не
        живой ИРБИС #222). Добавляем код рабочего листа 920 (по умолчанию PAZK),
        если его нет. Невалидная запись (ФЛК sev-1) -> skipped. Возвращает число
        созданных/пропущенных + их MFN."""
        self._require_super_admin(session)
        if self.inforost is None or self.catalog is None:
            return 200, ok({'created': 0, 'skipped': 0, 'mfns': []})
        plan = self.inforost.plan(body.get('export') or {})
        db = self.cfg.db_default
        created, skipped, mfns = 0, 0, []
        for rec in plan.get('records', []):
            rec = dict(rec)
            rec.setdefault('920', 'PAZK')
            try:
                res = self.catalog.save(db, rec)
            except Exception:
                skipped += 1
                continue
            if res and res.get('saved') and res.get('mfn'):
                created += 1
                mfns.append(res['mfn'])
            else:
                skipped += 1
        return 200, ok({'created': created, 'skipped': skipped, 'mfns': mfns})

    # ---- Исходящие вебхуки (#356, эпик #240) ----------------------------- #
    # Реестр подписок per-tenant на события + подписанный payload (HMAC) +
    # журнал доставки. Секреты наружу маскируются. Реальная сетевая отправка —
    # на слое applier; здесь — реестр + prepare/preview + журнал. Super-admin.
    def _webhooks_emit(self, tenant, event, data):
        """Эмиссия исходящего вебхука на доменном событии (#356).

        Подготовить цели по АКТИВНЫМ подпискам тенанта и зажурналировать доставку
        (статус ``prepared``). Реальная сетевая отправка — на слое коннектора;
        здесь фиксируем намерение в журнал, чтобы оператор видел трафик. Полностью
        best-effort: если стор не собран или подписок нет — тихо ноль, событие
        никогда не должно ломать основную операцию (выдачу/бронь/сохранение)."""
        wh = getattr(self, 'webhooks', None)
        if wh is None:
            return 0
        try:
            targets = wh.prepare(tenant, event, data or {})
            for t in targets:
                wh.store.log_delivery(t['subscription_id'], event, 'prepared')
            return len(targets)
        except Exception:
            return 0

    def webhooks_list(self, session, query):
        """GET /api/admin/webhooks?tenant= — подписки тенанта (secret маскирован, super-admin)."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 200, ok({'items': [], 'events': []})
        from access import webhooks as _wh
        tenant = (query.get('tenant') or [session.get("tenant", DEFAULT_TENANT)])[0]
        return 200, ok({'items': self.webhooks.list(tenant), 'events': list(_wh.EVENTS)})

    def webhooks_subscribe(self, session, body):
        """POST /api/admin/webhooks — подписка на событие (super-admin).

        ``tenant`` + ``event`` (из EVENTS) + ``url`` + опц. ``secret``. Невалидное
        событие/пустой url -> 400. В ответе secret маскирован."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 503, err('unavailable', 'webhooks store off')
        tenant = body.get("tenant") or session.get("tenant", DEFAULT_TENANT)
        try:
            sub = self.webhooks.subscribe(tenant, body.get('event') or '',
                                          body.get('url') or '', body.get('secret') or '')
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok(sub)

    def webhooks_set_active(self, session, body):
        """POST /api/admin/webhooks/active — вкл/выкл подписку (super-admin)."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 503, err('unavailable', 'webhooks store off')
        sub = self.webhooks.set_active(int(body.get('id') or 0), bool(body.get('active')))
        if sub is None:
            return 404, err('not_found', 'subscription not found')
        return 200, ok(sub)

    def webhooks_remove(self, session, body):
        """POST /api/admin/webhooks/remove — удалить подписку (super-admin)."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 503, err('unavailable', 'webhooks store off')
        return 200, ok({'removed': self.webhooks.unsubscribe(int(body.get('id') or 0))})

    def webhooks_preview(self, session, body):
        """POST /api/admin/webhooks/preview — что будет отправлено по событию (super-admin).

        ``tenant`` + ``event`` + опц. ``data``. Возвращает список целей с payload и
        подписью (по активным подпискам) — без реальной отправки."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 200, ok({'targets': []})
        tenant = body.get("tenant") or session.get("tenant", DEFAULT_TENANT)
        targets = self.webhooks.prepare(tenant, body.get('event') or '', body.get('data') or {})
        return 200, ok({'targets': targets})

    def webhooks_deliveries(self, session, query):
        """GET /api/admin/webhooks/deliveries?subscriptionId= — журнал доставки (super-admin)."""
        self._require_super_admin(session)
        if self.webhooks is None:
            return 200, ok({'items': []})
        sid = query.get('subscriptionId')
        sid = int(sid[0]) if sid and sid[0] else None
        return 200, ok({'items': self.webhooks.store.deliveries(sid)})

    # ---- Авторитетный/нормативный контроль (#359, Каталогизатор) --------- #
    # Own-store заголовков (персона/орг/тема/гео) + варианты + см.-ссылки +
    # дедуп/слияние. Контроль точек доступа. Гейт cataloging (штат).
    def authority_search(self, session, query):
        """GET /api/authority?kind=&q= — поиск заголовков (с вариантами и см.-также)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.authority_control is None:
            return 200, ok({'items': []})
        kind = (query.get('kind') or [None])[0]
        q = (query.get('q') or [None])[0]
        return 200, ok({'items': self.authority_control.search(kind, q)})

    def authority_create(self, session, body):
        """POST /api/authority — создать/найти заголовок (дедуп по виду+норме)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        try:
            h = self.authority_control.create(body.get('kind') or '',
                                              body.get('heading') or '', body.get('note') or '')
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'heading': h})

    def authority_variant(self, session, body):
        """POST /api/authority/variant — добавить вариант формы к заголовку."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        v = self.authority_control.add_variant(int(body.get('headingId') or 0), body.get('variant') or '')
        if v is None:
            return 404, err('not_found', 'heading not found')
        return 200, ok({'variant': v})

    def authority_link(self, session, body):
        """POST /api/authority/link — связать заголовки см./см.-также."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        try:
            x = self.authority_control.link(int(body.get('srcId') or 0), int(body.get('dstId') or 0),
                                            body.get('refType') or 'see_also')
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'xref': x})

    def authority_find_or_create(self, session, body):
        """POST /api/authority/find-or-create — контроль точки доступа (вернуть/создать)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        try:
            h = self.authority_control.find_or_create(body.get('kind') or '', body.get('heading') or '')
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'heading': h})

    def authority_merge(self, session, body):
        """POST /api/authority/merge — слить дубль заголовков (drop -> keep)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        try:
            res = self.authority_control.merge(int(body.get('keepId') or 0), int(body.get('dropId') or 0))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        return 200, ok(res)

    def authority_remove(self, session, body):
        """POST /api/authority/remove — удалить заголовок (каскадно вар./ссылки)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.authority_control is None:
            return 503, err('unavailable', 'authority store off')
        return 200, ok({'removed': self.authority_control.store.remove(int(body.get('id') or 0))})

    def my_modules(self, session):
        """GET /api/me/modules — активный набор функциональных модулей тенанта (#335).

        Резолвит режим развёртывания тенанта в набор модулей: ``overlay_jirbis``
        прячет тяжёлый бэк-офис (каталогизация/комплектование живут в живом ИРБИС),
        ``replace_*``/``full`` включают больше. Доступен любому сотруднику — фронт
        прячет неактуальные десктопы. Режим не назначен/стор не собран ->
        ``configured:false`` (фронт показывает всё, ничего не ограничивая)."""
        self._require_staff(session)
        if self.deployment is None:
            return 200, ok({'configured': False, 'mode': None, 'modules': []})
        r = self.deployment.resolve(session.get('tenant', DEFAULT_TENANT))
        return 200, ok({'configured': bool(r.get('configured')),
                        'mode': r.get('mode'),
                        'modules': r.get('default_modules', [])})

    # ---- Морфо-полнотекст: own-store FTS + BM25 (#368) ------------------- #
    # Морфологический поиск (русский стеммер) с ранжированием BM25 поверх
    # собственного индекса. Источник — OCR-текст (мост в ocr_process) + ручная
    # индексация. Поиск/похожие — public-read; индексация/реиндекс — штат/админ.
    def fulltext_search(self, session, query):
        """GET /api/fulltext/search?q=&limit= — морфо-полнотекст с BM25 (public-read)."""
        if self.search_index is None:
            return 200, ok({'hits': [], 'query': ''})
        q = (query.get('q') or [''])[0]
        try:
            limit = min(50, max(1, int((query.get('limit') or ['20'])[0])))
        except (TypeError, ValueError):
            limit = 20
        return 200, ok({'query': q, 'hits': self.search_index.search(q, limit=limit)})

    def fulltext_more_like(self, session, query):
        """GET /api/fulltext/more-like?ref= — похожие по терминам документа (public-read)."""
        if self.search_index is None:
            return 200, ok({'hits': []})
        ref = (query.get('ref') or [''])[0]
        if not ref:
            return 400, err('bad_request', 'ref required')
        return 200, ok({'ref': ref, 'hits': self.search_index.more_like(ref)})

    def fulltext_index(self, session, body):
        """POST /api/fulltext/index — проиндексировать документ (штат, cataloging)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.search_index is None:
            return 503, err('unavailable', 'search index off')
        ref = (body.get('ref') or '').strip()
        if not ref:
            return 400, err('bad_request', 'ref required')
        res = self.search_index.index(ref, body.get('text') or '',
                                      db=body.get('db') or '',
                                      mfn=int(body.get('mfn') or 0),
                                      title=body.get('title') or '')
        return 200, ok({'indexed': res})

    def fulltext_reindex_ocr(self, session, body):
        """POST /api/fulltext/reindex-ocr — переиндексировать весь OCR-слой в FTS (super-admin).

        Бэкфилл: склеивает текст страниц каждого OCR-документа и индексирует с
        морфологией. Возвращает число переиндексированных документов."""
        self._require_super_admin(session)
        if self.search_index is None or self.ocr is None:
            return 200, ok({'reindexed': 0})
        store = getattr(self.ocr, 'store', None)
        if store is None:
            return 200, ok({'reindexed': 0})
        by_ref = {}
        for p in store.all_pages():
            by_ref.setdefault(p['asset_ref'], []).append(p.get('text') or '')
        n = 0
        for ref, texts in by_ref.items():
            try:
                self.search_index.index('ocr:' + ref, '\n'.join(texts), db='OCR', title=ref)
                n += 1
            except Exception:
                pass
        return 200, ok({'reindexed': n})

    def fulltext_reindex_catalog(self, session, query):
        """POST /api/fulltext/reindex-catalog?db= — переиндексировать каталог в FTS (super-admin).

        Бэкфилл own-store каталога: для каждой записи извлекает заглавие/авторов/темы/
        аннотацию и индексирует с морфологией (ref=cat:<db>:<mfn>). Делает морфо-поиск
        полезным по основному корпусу, а не только по OCR. Возвращает число записей."""
        self._require_super_admin(session)
        if self.search_index is None or self.catalog is None:
            return 200, ok({'reindexed': 0})
        db = (query.get('db') or [self.cfg.db_default])[0]
        n = 0
        try:
            mfns = list(self.catalog.list_mfns(db, limit=5000))
        except Exception:
            mfns = []
        for mfn in mfns:
            rec = self.catalog.get(db, mfn)
            if rec is None:
                continue
            title, text = self._record_search_text(rec)
            try:
                self.search_index.index('cat:%s:%s' % (db, mfn), text, db=db,
                                        mfn=int(mfn), title=title)
                n += 1
            except Exception:
                pass
        return 200, ok({'reindexed': n})

    def analytics_overview(self, session):
        """GET /api/analytics/overview — сводка ключевых метрик библиотеки (штат).

        Пульс библиотеки одним вызовом: фонд/читатели/штат/оцифровка/выставки/
        авторитет/архив выдач. Каждая метрика — best-effort по own-store (свой
        try/except -> 0/None), чтобы дашборд никогда не падал из-за одного стора."""
        self._require_staff(session)
        tenant = session.get('tenant', DEFAULT_TENANT)
        m = dict(self._tenant_usage(tenant))   # records/readers/staff_seats/ocr_pages
        def _safe(fn, default=0):
            try:
                return fn()
            except Exception:
                return default
        m['exhibits'] = _safe(lambda: len(self.exhibits.list(published_only=False)) if self.exhibits else 0)
        m['exhibits_public'] = _safe(lambda: len(self.exhibits.public_exhibits()) if self.exhibits else 0)
        m['authority'] = _safe(lambda: len(self.authority_control.store.list(limit=100000)) if self.authority_control else 0)
        m['loans_archived'] = _safe(lambda: int(self.circulation.count_archived()) if self.circulation else 0)
        # Полнотекст-индекс (#368) + очередь фоновых задач (#356/jobs).
        m['fts_indexed'] = _safe(lambda: int(self.search_index.store.count())
                                 if (self.search_index and getattr(self.search_index, 'store', None)) else 0)
        _js = _safe(lambda: self.job_queue.stats() if self.job_queue else {}, {})
        m['jobs_total'] = int((_js or {}).get('total', 0))
        _bs = (_js or {}).get('by_status') or {}
        m['jobs_pending'] = int(_bs.get('pending', 0))
        m['jobs_done'] = int(_bs.get('done', 0))
        return 200, ok({'tenant': tenant, 'metrics': m})

    # ===================================================================== #
    # Разводка own-store бэклога (#316/#317/#318) в роуты.                   #
    # Комплектование: поставщики/счета + подписка-периодика. Каталогизатор:  #
    # MARC ISO2709/MARCXML обмен, дедуп, печать ГОСТ, версии, редактор       #
    # словарей .mnu/.tre. Администратор: редактируемые роли (RBAC), аудит-   #
    # трейл, конфиг-параметры. Утилиты: стат/экспорт/дубли/ФЛК-lite над       #
    # выборкой. Всё own-store, без записи в живой ИРБИС (#222); если сервис   #
    # не собрался — пустой ответ, не 500.                                    #
    # ===================================================================== #

    # ---- Комплектование: поставщики/счета (PR #316) ---------------------- #
    def suppliers_add(self, session, body):
        """POST /api/acq/supplier — завести поставщика (staff)."""
        self._guard(session, 'acq.receipt', '*', 'write')
        if self.suppliers is None:
            return 200, ok({'supplier': None})
        name = (body.get('name') or '').strip()
        if not name:
            return 400, err('bad_request', 'name required')
        try:
            rec = self.suppliers.add_supplier(
                name, inn=body.get('inn'), contact=body.get('contact'),
                email=body.get('email'), phone=body.get('phone'),
                address=body.get('address'))
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'supplier': rec})

    def suppliers_list(self, session, query):
        """GET /api/acq/suppliers — поставщики + сводка (staff)."""
        self._guard(session, 'acq.read', '*', 'read')
        if self.suppliers is None:
            return 200, ok({'items': [], 'stats': {}})
        active = query.get('active', ['0'])[0] in ('1', 'true', 'yes')
        return 200, ok({'items': self.suppliers.list(active_only=active),
                        'stats': self.suppliers.stats()})

    def supplier_invoice(self, session, body):
        """POST /api/acq/supplier/invoice — счёт-акт поставщика (staff)."""
        self._guard(session, 'acq.receipt', '*', 'write')
        if self.suppliers is None:
            return 200, ok({'invoice': None})
        try:
            sid = int(body.get('supplierId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'supplierId required')
        number = (body.get('number') or '').strip()
        if not number:
            return 400, err('bad_request', 'number required')
        try:
            rec = self.suppliers.add_invoice(
                sid, number, body.get('amount'), date=body.get('date'),
                ksu_no=body.get('ksuNo'), order_ref=body.get('orderRef'))
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'invoice': rec})

    # ---- Комплектование: подписка/периодика (PR #316) -------------------- #
    def subscription_add(self, session, body):
        """POST /api/acq/subscription — оформить подписку (staff)."""
        self._guard(session, 'acq.receipt', '*', 'write')
        if self.subscription is None:
            return 200, ok({'subscription': None})
        title = (body.get('title') or '').strip()
        if not title:
            return 400, err('bad_request', 'title required')
        rec = self.subscription.subscribe(
            title, issn=body.get('issn'), supplier_id=body.get('supplierId'),
            period_from=body.get('periodFrom'), period_to=body.get('periodTo'),
            copies=int(body.get('copies') or 1))
        return 200, ok({'subscription': rec})

    def subscriptions_list(self, session, query):
        """GET /api/acq/subscriptions — подписки + сводка (staff)."""
        self._guard(session, 'acq.read', '*', 'read')
        if self.subscription is None:
            return 200, ok({'items': [], 'stats': {}})
        return 200, ok({'items': self.subscription.list_subscriptions(),
                        'stats': self.subscription.stats()})

    def subscription_receive(self, session, body):
        """POST /api/acq/subscription/receive — отметить поступление номера (staff)."""
        self._guard(session, 'acq.receipt', '*', 'write')
        if self.subscription is None:
            return 200, ok({'issue': None})
        try:
            sid = int(body.get('subscriptionId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'subscriptionId required')
        rec = self.subscription.receive_issue(
            sid, body.get('number'), body.get('year'))
        if rec is None:
            return 404, err('not_found', 'issue not found')
        return 200, ok({'issue': rec})

    # ---- Каталогизатор: MARC ISO2709 / MARCXML обмен (PR #316/#317) ------- #
    def marc_export(self, session, body):
        """POST /api/cataloging/marc/export — записи -> ISO 2709 (base64, staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        import base64
        from access import marc as _marc
        records = body.get('records') or []
        try:
            blob = _marc.export_batch(records)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'iso2709_b64': base64.b64encode(blob).decode('ascii'),
                        'count': len(records)})

    def marc_import(self, session, body):
        """POST /api/cataloging/marc/import — ISO 2709 (base64) -> записи (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        import base64
        from access import marc as _marc
        b64 = body.get('iso2709_b64') or ''
        try:
            data = base64.b64decode(b64) if b64 else b''
            records = _marc.import_batch(data)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'records': records, 'count': len(records)})

    def marcxml_export(self, session, body):
        """POST /api/cataloging/marcxml/export — записи -> MARCXML (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import marcxml as _mx
        records = body.get('records') or []
        try:
            xml = _mx.to_marcxml_collection(records)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'marcxml': xml, 'count': len(records)})

    def marcxml_import(self, session, body):
        """POST /api/cataloging/marcxml/import — MARCXML -> записи (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        from access import marcxml as _mx
        xml = body.get('marcxml') or ''
        try:
            records = _mx.from_marcxml_collection(xml)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'records': records, 'count': len(records)})

    # ---- Каталогизатор: copy-cataloging через SRU/Z39.50 (#240) ---------- #
    def copy_search_url(self, session, body):
        """POST /api/cataloging/copy/url — собрать SRU-URL для копикаталогизации (cataloging read).

        ``base`` (URL SRU-сервиса) + ``field`` (title|author|isbn|any) + ``term``.
        Сетевой вызов делает вызывающий слой (граница транспорта); возвращаем URL +
        CQL-запрос."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import sru as _sru
        base = (body.get('base') or '').strip()
        term = (body.get('term') or '').strip()
        if not base or not term:
            return 400, err('bad_request', 'base/term required')
        query = _sru.search_query((body.get('field') or 'any'), term)
        try:
            mx = min(50, max(1, int(body.get('max', 10))))
        except (TypeError, ValueError):
            mx = 10
        return 200, ok({'url': _sru.sru_url(base, query, max_records=mx), 'query': query})

    def copy_parse(self, session, body):
        """POST /api/cataloging/copy/parse — разобрать SRU-ответ -> записи + кандидаты (cataloging read).

        ``xml`` — SRU searchRetrieveResponse (с MARCXML). Опц. ``isbn``/``title`` —
        отфильтровать кандидатов-дублей для импорта."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import sru as _sru
        parsed = _sru.parse_response(body.get('xml') or '')
        out = {'total': parsed['total'], 'records': parsed['records'],
               'count': len(parsed['records'])}
        if body.get('isbn') or body.get('title'):
            out['candidates'] = _sru.candidates(
                parsed['records'], isbn=body.get('isbn'), title=body.get('title'))
        return 200, ok(out)

    def copy_import(self, session, body):
        """POST /api/cataloging/copy/import — импортировать записи SRU-ответа в каталог (cataloging write).

        Разбирает ``xml`` (SRU/MARCXML) и сохраняет записи в собственный CatalogStore
        (920=PAZK по умолч., ФЛК; невалидные -> skipped). Не пишет живой ИРБИС (#222)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.catalog is None:
            return 200, ok({'created': 0, 'skipped': 0, 'mfns': []})
        from access import sru as _sru
        parsed = _sru.parse_response(body.get('xml') or '')
        db = self.cfg.db_default
        created, skipped, mfns = 0, 0, []
        for rec in parsed['records']:
            rec = dict(rec)
            rec.setdefault('920', 'PAZK')
            try:
                res = self.catalog.save(db, rec)
            except Exception:
                skipped += 1
                continue
            if res and res.get('saved') and res.get('mfn'):
                created += 1
                mfns.append(res['mfn'])
            else:
                skipped += 1
        return 200, ok({'created': created, 'skipped': skipped, 'mfns': mfns})

    # ---- Каталогизатор: дедуп / copy-cataloging (PR #317) ---------------- #
    def dedup_scan(self, session, body):
        """POST /api/cataloging/dedup — кластеры дублей + сводка (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import dedup as _dd
        records = body.get('records') or []
        return 200, ok({'clusters': _dd.find_duplicates(records),
                        'stats': _dd.dedup_stats(records)})

    def dedup_check(self, session, body):
        """POST /api/cataloging/dedup/check — дубль ли запись в наборе (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import dedup as _dd
        idx = _dd.is_duplicate(body.get('record') or {},
                               body.get('existing') or [])
        return 200, ok({'duplicate': idx is not None, 'index': idx})

    # ---- Каталогизатор: печать ГОСТ (PR #317) ---------------------------- #
    def catalog_print_route(self, session, body):
        """POST /api/cataloging/print — карточки/списки/индексы ГОСТ (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import catalog_print as _cp
        records = body.get('records') or []
        form = (body.get('form') or 'card').strip()
        kw = {}
        if form == 'index':
            if body.get('by'):
                kw['by'] = body.get('by')
            if body.get('code'):
                kw['code'] = body.get('code')
        try:
            text = _cp.to_text(records, form=form, **kw)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'text': text, 'form': form, 'count': len(records)})

    # ---- Каталогизатор: версии записи (PR #316) -------------------------- #
    def versions_history(self, session, query):
        """GET /api/cataloging/versions?db=&mfn= — история версий (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.catalog_versions is None:
            return 200, ok({'items': []})
        db = (query.get('db', [self.cfg.db_default])[0])
        try:
            mfn = int(query.get('mfn', ['0'])[0])
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        return 200, ok({'items': self.catalog_versions.history(db, mfn)})

    def versions_snapshot(self, session, body):
        """POST /api/cataloging/versions/snapshot — зафиксировать версию (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.catalog_versions is None:
            return 200, ok({'version': None})
        db = (body.get('db') or self.cfg.db_default)
        try:
            mfn = int(body.get('mfn'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn required')
        actor = (session or {}).get('actor')
        ver = self.catalog_versions.snapshot(db, mfn, body.get('record') or {},
                                             actor=actor)
        return 200, ok({'version': ver})

    def versions_revert(self, session, body):
        """POST /api/cataloging/versions/revert — record указанной версии (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.catalog_versions is None:
            return 200, ok({'record': None})
        db = (body.get('db') or self.cfg.db_default)
        try:
            mfn = int(body.get('mfn'))
            ver = int(body.get('version'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'mfn/version required')
        rec = self.catalog_versions.revert(db, mfn, ver)
        if rec is None:
            return 404, err('not_found', 'version not found')
        return 200, ok({'record': rec})

    # ---- Каталогизатор: редактор словарей .mnu / деревьев .tre (PR #317) -- #
    def vocab_values(self, session, query):
        """GET /api/cataloging/vocab?vocab= — значения словаря (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.vocab_editor is None:
            return 200, ok({'items': []})
        vocab = (query.get('vocab', [''])[0] or '').strip()
        if not vocab:
            return 400, err('bad_request', 'vocab required')
        active = query.get('activeOnly', ['0'])[0] in ('1', 'true', 'yes')
        return 200, ok({'items': self.vocab_editor.values(vocab, active_only=active)})

    def vocab_add_value(self, session, body):
        """POST /api/cataloging/vocab/value — добавить/переименовать значение (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.vocab_editor is None:
            return 200, ok({'value': None})
        vocab = (body.get('vocab') or '').strip()
        code = (body.get('code') or '').strip()
        if not vocab or not code:
            return 400, err('bad_request', 'vocab/code required')
        rec = self.vocab_editor.add_value(vocab, code, (body.get('label') or ''),
                                          sort=body.get('sort'))
        return 200, ok({'value': rec})

    def tree_children(self, session, query):
        """GET /api/cataloging/tree?tree=&parent= — узлы дерева (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        if self.vocab_editor is None:
            return 200, ok({'items': []})
        tree = (query.get('tree', [''])[0] or '').strip()
        if not tree:
            return 400, err('bad_request', 'tree required')
        parent = (query.get('parent', [None])[0])
        return 200, ok({'items': self.vocab_editor.children(tree, parent_code=parent)})

    def tree_add_node(self, session, body):
        """POST /api/cataloging/tree/node — добавить узел дерева (staff)."""
        self._guard(session, 'cataloging', '*', 'write')
        if self.vocab_editor is None:
            return 200, ok({'node': None})
        tree = (body.get('tree') or '').strip()
        code = (body.get('code') or '').strip()
        if not tree or not code:
            return 400, err('bad_request', 'tree/code required')
        try:
            rec = self.vocab_editor.add_node(tree, code, (body.get('label') or ''),
                                             parent_code=body.get('parentCode'),
                                             sort=body.get('sort'))
        except KeyError as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'node': rec})

    # ---- Администратор: редактируемые роли RBAC (PR #318) ---------------- #
    def rbac_roles(self, session, query):
        """GET /api/admin/rbac/roles — список ролей (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.roles is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.roles.list_roles()})

    def rbac_create_role(self, session, body):
        """POST /api/admin/rbac/role — создать роль (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.roles is None:
            return 200, ok({'role': None})
        name = (body.get('name') or '').strip()
        if not name:
            return 400, err('bad_request', 'name required')
        try:
            rec = self.roles.create_role(name, description=(body.get('description') or ''),
                                         parent=body.get('parent'))
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'role': rec})

    def rbac_add_grant(self, session, body):
        """POST /api/admin/rbac/grant — добавить грант роли (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.roles is None:
            return 200, ok({'grant': None})
        role = body.get('role')
        function = (body.get('function') or '').strip()
        if role is None or not function:
            return 400, err('bad_request', 'role/function required')
        try:
            rec = self.roles.add_grant(role, function, db=(body.get('db') or '*'),
                                       level=(body.get('level') or 'read'))
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'grant': rec})

    def rbac_assign(self, session, body):
        """POST /api/admin/rbac/assign — назначить роль учётке (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.roles is None:
            return 200, ok({'assigned': False})
        account = (body.get('account') or '').strip()
        role = body.get('role')
        if not account or role is None:
            return 400, err('bad_request', 'account/role required')
        try:
            self.roles.assign(account, role)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'assigned': True})

    def rbac_effective(self, session, query):
        """GET /api/admin/rbac/effective?account= — эффективные гранты (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.roles is None:
            return 200, ok({'grants': []})
        account = (query.get('account', [''])[0] or '').strip()
        if not account:
            return 400, err('bad_request', 'account required')
        return 200, ok({'grants': self.roles.effective_grants(account)})

    # ---- Администратор: аудит-трейл (PR #318) ---------------------------- #
    def audit_trail_query(self, session, query):
        """GET /api/admin/audit-trail — запросный аудит-журнал + сводка (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.audit_trail is None:
            return 200, ok({'items': [], 'summary': {}})
        kw = {}
        for k in ('actor', 'action', 'status'):
            v = (query.get(k, [None])[0])
            if v:
                kw[k] = v
        try:
            limit = min(500, max(1, int(query.get('limit', ['100'])[0])))
        except (TypeError, ValueError):
            limit = 100
        return 200, ok({'items': self.audit_trail.entries(limit=limit, **kw),
                        'summary': self.audit_trail.summary()})

    def audit_trail_export(self, session, query):
        """GET /api/admin/audit-trail/export.csv — выгрузка аудита в CSV (admin).

        Те же фильтры, что audit-trail (actor/action/status), CSV с BOM (Excel-
        дружественная кириллица). Гейт admin.users."""
        self._guard(session, 'admin.users', '*', 'admin')
        import csv
        import io
        cols = ['ts', 'actor', 'action', 'object_type', 'object_id', 'db', 'status', 'tenant']
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        if self.audit_trail is not None:
            kw = {}
            for k in ('actor', 'action', 'status'):
                v = (query.get(k, [None])[0])
                if v:
                    kw[k] = v
            try:
                limit = min(5000, max(1, int(query.get('limit', ['1000'])[0])))
            except (TypeError, ValueError):
                limit = 1000
            for e in self.audit_trail.entries(limit=limit, **kw):
                w.writerow(['' if e.get(c) is None else e.get(c) for c in cols])
        data = ('﻿' + buf.getvalue()).encode('utf-8')
        return 200, Raw(data, 'text/csv; charset=utf-8')

    # ---- Администратор: конфиг-параметры (PR #318) ----------------------- #
    def config_list(self, session, query):
        """GET /api/admin/config — параметры тенанта (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.config is None:
            return 200, ok({'items': []})
        tenant = (query.get('tenant', ['default'])[0])
        prefix = (query.get('prefix', [None])[0])
        return 200, ok({'items': self.config.store.list(tenant=tenant, prefix=prefix)})

    def config_set(self, session, body):
        """POST /api/admin/config — задать параметр (admin)."""
        self._guard(session, 'admin.users', '*', 'admin')
        if self.config is None:
            return 200, ok({'param': None})
        key = (body.get('key') or '').strip()
        if not key:
            return 400, err('bad_request', 'key required')
        try:
            rec = self.config.store.set(
                key, body.get('value'), type=body.get('type'),
                tenant=(body.get('tenant') or 'default'),
                description=body.get('description'))
        except (ValueError, TypeError) as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'param': rec})

    # ---- Утилиты: стат/экспорт/дубли/ФЛК-lite над выборкой (PR #318) ------ #
    def utils_stats(self, session, body):
        """POST /api/utils/stats — статистика по набору записей (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import db_utils as _du
        records = body.get('records') or []
        return 200, ok({'stats': _du.stats(records),
                        'fund': _du.fund_summary(records)})

    def utils_export(self, session, body):
        """POST /api/utils/export — экспорт выборки в json/csv (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import db_utils as _du
        records = body.get('records') or []
        fmt = (body.get('format') or 'json').strip()
        if fmt == 'csv':
            fields = body.get('fields') or []
            return 200, ok({'format': 'csv', 'data': _du.export_csv(records, fields)})
        return 200, ok({'format': 'json', 'data': _du.export_json(records)})

    def utils_duplicates(self, session, body):
        """POST /api/utils/duplicates — потенциальные дубли по тег-спеке (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import db_utils as _du
        records = body.get('records') or []
        spec = (body.get('tag') or '').strip()
        if not spec:
            return 400, err('bad_request', 'tag required')
        return 200, ok({'duplicates': _du.duplicate_keys(records, spec)})

    def utils_validate(self, session, body):
        """POST /api/utils/validate — предимпортный ФЛК-lite по обязат. тегам (staff)."""
        self._guard(session, 'cataloging', '*', 'read')
        from access import db_utils as _du
        records = body.get('records') or []
        required = body.get('required') or []
        bad = _du.validate_batch(records, required)
        return 200, ok({'invalid': bad, 'ok': len(bad) == 0})

    # ---- Книговыдача: политики выдачи (PR #320, ребро 11.4) --------------- #
    def loan_policies_list(self, session, query):
        """GET /api/circ/policies — список политик выдачи (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if self.loan_policy is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.loan_policy.store.list_policies()})

    def loan_policy_set(self, session, body):
        """POST /api/circ/policy — задать политику (категория×вид издания) (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        if self.loan_policy is None:
            return 200, ok({'policy': None})
        cat = (body.get('readerCategory') or '*').strip() or '*'
        dt = (body.get('docType') or '*').strip() or '*'
        try:
            rec = self.loan_policy.set_policy(
                cat, dt, int(body.get('loanDays')), int(body.get('maxItems')),
                renewals=int(body.get('renewals') or 1),
                deposit=int(body.get('deposit') or 0),
                fine_per_day=int(body.get('finePerDay') or 0))
        except (TypeError, ValueError) as e:
            return 400, err('bad_request', 'loanDays/maxItems int required: %s' % e)
        return 200, ok({'policy': rec})

    def loan_policy_resolve(self, session, query):
        """GET /api/circ/policy/resolve?category=&docType= — применимая политика (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if self.loan_policy is None:
            return 200, ok({'policy': None})
        cat = (query.get('category', ['*'])[0] or '*')
        dt = (query.get('docType', ['*'])[0] or '*')
        return 200, ok({'policy': self.loan_policy.resolve(cat, dt)})

    # ---- Книговыдача: должники/санкции (PR #320) -------------------------- #
    def debts_list(self, session, query):
        """GET /api/circ/debts?reader= — долги читателя или сводный отчёт (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if self.debtors is None:
            return 200, ok({'report': {}, 'reader': None})
        reader = (query.get('reader', [''])[0] or '').strip()
        if reader:
            return 200, ok({'reader': reader,
                            'debts': self.debtors.reader_debts(reader),
                            'blocked': self.debtors.is_blocked(reader)})
        return 200, ok({'report': self.debtors.debtors_report()})

    def debt_register(self, session, body):
        """POST /api/circ/debt — зарегистрировать долг (просрочка/утеря) (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        if self.debtors is None:
            return 200, ok({'debt': None})
        reader = (body.get('reader') or '').strip()
        item = (body.get('item') or '').strip()
        if not reader or not item:
            return 400, err('bad_request', 'reader/item required')
        kind = (body.get('kind') or 'overdue').strip()
        db = (body.get('db') or '*')
        try:
            if kind == 'lost':
                rec = self.debtors.register_lost(
                    reader, item, int(body.get('amount') or 0), db=db)
            else:
                rec = self.debtors.register_overdue(
                    reader, item, body.get('dueDate'), body.get('asOf'),
                    int(body.get('finePerDay') or 0), db=db)
        except Exception as e:
            return 400, err('bad_request', str(e))
        return 200, ok({'debt': rec})

    def debt_settle(self, session, body):
        """POST /api/circ/debt/settle — погасить долг (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        if self.debtors is None:
            return 200, ok({'settled': False})
        try:
            did = int(body.get('debtId'))
        except (TypeError, ValueError):
            return 400, err('bad_request', 'debtId required')
        return 200, ok({'settled': bool(self.debtors.settle(did))})

    def blocks_list(self, session, query):
        """GET /api/circ/blocks — заблокированные читатели (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'read')
        if self.debtors is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.debtors.store.blocked_readers()})

    def block_evaluate(self, session, body):
        """POST /api/circ/block/evaluate — пересчитать блокировку читателя (staff)."""
        self._guard(session, 'circ.issue', self.cfg.db_default, 'write')
        if self.debtors is None:
            return 200, ok({'state': None})
        reader = (body.get('reader') or '').strip()
        if not reader:
            return 400, err('bad_request', 'reader required')
        state = self.debtors.evaluate_block(
            reader, threshold_kopecks=int(body.get('thresholdKopecks') or 0),
            threshold_count=int(body.get('thresholdCount') or 3))
        return 200, ok({'state': state})

    # ---- Книгообеспеченность: нормы РПД (PR #320) ------------------------- #
    def discipline_add(self, session, body):
        """POST /api/bp/rpd/discipline — завести дисциплину РПД с контингентом (staff)."""
        self._guard(session, 'bp.write', '*', 'write')
        if self.discipline_norms is None:
            return 200, ok({'discipline': None})
        code = (body.get('code') or '').strip()
        name = (body.get('name') or '').strip()
        if not code or not name:
            return 400, err('bad_request', 'code/name required')
        rec = self.discipline_norms.add_discipline(
            code, name, department=(body.get('department') or ''),
            contingent=int(body.get('contingent') or 0))
        return 200, ok({'discipline': rec})

    def disciplines_list(self, session, query):
        """GET /api/bp/rpd/disciplines — список дисциплин РПД (staff)."""
        self._guard(session, 'bp.read', '*', 'read')
        if self.discipline_norms is None:
            return 200, ok({'items': []})
        return 200, ok({'items': self.discipline_norms.store.list_disciplines()})

    def discipline_norm_set(self, session, body):
        """POST /api/bp/rpd/norm — привязать норматив издания к дисциплине (staff)."""
        self._guard(session, 'bp.write', '*', 'write')
        if self.discipline_norms is None:
            return 200, ok({'norm': None})
        code = (body.get('disciplineCode') or '').strip()
        ref = (body.get('editionRef') or '').strip()
        if not code or not ref:
            return 400, err('bad_request', 'disciplineCode/editionRef required')
        try:
            rec = self.discipline_norms.set_norm(
                code, ref, float(body.get('normPerStudent')),
                kind=(body.get('kind') or 'main'))
        except ValueError as e:
            return 400, err('bad_request', str(e))
        except TypeError:
            return 400, err('bad_request', 'normPerStudent required')
        return 200, ok({'norm': rec})

    def discipline_required(self, session, query):
        """GET /api/bp/rpd/required?code= — требуемые экземпляры по нормам РПД (staff)."""
        self._guard(session, 'bp.read', '*', 'read')
        if self.discipline_norms is None:
            return 200, ok({'items': [], 'total': 0})
        code = (query.get('code', [''])[0] or '').strip()
        if not code:
            return 400, err('bad_request', 'code required')
        return 200, ok({'items': self.discipline_norms.required_copies(code),
                        'total': self.discipline_norms.total_required(code)})

    # ---- Книгообеспеченность: ККО-аналитика (PR #320) -------------------- #
    def kko_report(self, session, body):
        """POST /api/bp/kko/report — отчёт книгообеспеченности по дисциплинам (staff)."""
        self._guard(session, 'bp.read', '*', 'read')
        from access import kko_reports as _kko
        disciplines = body.get('disciplines') or []
        rep = _kko.report(disciplines)
        rep['by_department'] = _kko.by_department(disciplines)
        rep['worst'] = _kko.worst(disciplines, int(body.get('worst') or 5))
        return 200, ok(rep)

    def kko_snapshot_save(self, session, body):
        """POST /api/bp/kko/snapshot — сохранить срез отчёта на период (staff)."""
        self._guard(session, 'bp.write', '*', 'write')
        if self.kko_snapshots is None:
            return 200, ok({'snapshot': None})
        from access import kko_reports as _kko
        period = (body.get('period') or '').strip()
        if not period:
            return 400, err('bad_request', 'period required')
        rec = self.kko_snapshots.save(period, _kko.report(body.get('disciplines') or []))
        return 200, ok({'snapshot': rec})

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

    # ---- Готовые движки связности: linked / fulltext / bp-provision -------- #
    # Три эндпойнта поверх УЖЕ landed движков (их сами не правим):
    #   * /api/linked    — обход связи иерархии записей (catalog.linked_records);
    #   * /api/fulltext  — артефакты ПТ + уровень доступа (fulltext × rights × lich);
    #   * /api/bp/provision — быстрый отчёт ККО (bookprovision.*_provision).
    # Первые два — ПУБЛИЧНЫЕ (как /api/record): тот же search/record.read-грант +
    # public-db guard, чтобы гость/читатель не дотянулся до служебной/ПДн БД.
    # /api/bp/provision — STAFF-grant (КО-функция, не публичный).

    def linked(self, session, db, mfn, kind):
        """GET /api/linked/{db}/{mfn}?kind=children|host — обход связи иерархии
        издания (статья↔журнал/сборник, номер↔журнал, том↔сводная).

        Публичный (как /api/record): ``record.read``-грант + public-db guard, так
        что гость/читатель не обойдёт связь по непубличной/ПДн БД. Делегирует в
        ``catalog.linked_records(db, mfn, kind)`` и проецирует результат на контракт
        фронта ``{db, mfn, kind, total, items:[{mfn, brief}]}`` (служебное поле
        ``keys`` движка наружу не отдаём). Мягкая деградация: нет каталог-движка /
        нет записи / нет ключей связи → ``{total:0, items:[]}`` (никогда не 500)."""
        self._guard(session, 'record.read', db, 'read')
        self._public_db_guard(session, db)
        kind = (kind or 'children').strip().lower()
        if kind not in ('children', 'host', 'parent'):
            kind = 'children'
        result = {'total': 0, 'items': [], 'kind': kind}
        if self.catalog is not None:
            try:
                result = self.catalog.linked_records(db, mfn, kind)
            except Exception:
                result = {'total': 0, 'items': [], 'kind': kind}
        items = [{'mfn': it.get('mfn'), 'brief': it.get('brief', '')}
                 for it in (result.get('items') or [])]
        return 200, ok({'db': db, 'mfn': mfn, 'kind': result.get('kind', kind),
                        'total': result.get('total', 0), 'items': items})

    def _reader_category(self, session):
        """Категория читателя (RDR поле 50, код по 50.mnu) для текущей сессии, или
        None. Берётся ТОЛЬКО для читательской сессии — по её ``rdr_mfn`` читаем
        живую запись RDR и достаём поле 50. Гость/staff → None (категории нет; для
        прав это значит «правило категории не совпало»). Никогда не бросает: сбой
        чтения RDR деградирует к None (rights трактует как deny по шаблону / full
        при пустом шаблоне)."""
        if not session or session.get('kind') != 'reader':
            return None
        mfn = session.get('rdr_mfn')
        if not mfn:
            return None
        try:
            rec = self.irbis.read_record('RDR', mfn)
        except (IrbisError, OSError, socket.error):
            return None
        f = field(rec, '50')
        if not f:
            return None
        val = (f.get('value') or '').strip()
        if not val:
            # категория могла лечь в подполе (редкий РЛ) — первое непустое
            for sub in (f.get('subfields') or {}).values():
                if sub and str(sub).strip():
                    val = str(sub).strip()
                    break
        return val or None

    def fulltext_record(self, session, db, mfn):
        """GET /api/fulltext/{db}/{mfn} — артефакты полного текста записи + уровень
        доступа категории текущего пользователя.

        Публичный (как /api/record): ``record.read``-грант + public-db guard.

        ``artifacts`` — из ``fulltext.artifacts_for(db, mfn)`` (стор + каталог),
        спроецированы на контракт фронта ``{kind, ref, pages, rightsTemplate}``.

        ``access`` собирается из связки rights×lich (ребра 7.2/7.3/7.5):
          * ``level``  = ``rights.access_level(категория, db, mfn)`` —
            deny/view/download по 955^B-шаблону (пустой шаблон ⇒ download);
          * ``pageLimit`` = ``rights.page_limit(категория, db, mfn)`` (None ⇒ опущен);
          * ``downloadBudget`` = ``lich.download_budget(билет, "db/mfn", категория,
            db, mfn)`` — остаток квоты скачивания ТОЛЬКО для читательской сессии
            (квота персональна, привязана к билету). Гость — уровень по rights без
            квоты (downloadBudget опущен). ПДн: чужой LICH-счётчик не светим —
            бюджет считается строго по билету текущего читателя.

        Мягкая деградация: нет движков / нет данных → пустые ``artifacts`` и
        безопасный ``access`` (level из rights, иначе download), никогда не 500."""
        self._guard(session, 'record.read', db, 'read')
        self._public_db_guard(session, db)
        # 1) Артефакты ПТ (ребро 7.1) — проекция на контракт фронта.
        artifacts = []
        if self.fulltext is not None:
            try:
                for art in self.fulltext.artifacts_for(db, mfn):
                    artifacts.append({
                        'kind': art.get('kind'),
                        'ref': art.get('ref'),
                        'pages': art.get('pages'),
                        'rightsTemplate': art.get('rights_template'),
                    })
            except Exception:
                artifacts = []
        # 2) Уровень доступа (рёбра 7.2/7.3) — по категории читателя и 955^B-шаблону.
        category = self._reader_category(session)
        level = 'download'          # пустой шаблон ⇒ полный доступ (безопасный дефолт)
        page_limit = None
        if self.rights is not None:
            try:
                level = self.rights.access_level(category, db=db, mfn=mfn)
            except Exception:
                level = 'download'
            try:
                page_limit = self.rights.page_limit(category, db=db, mfn=mfn)
            except Exception:
                page_limit = None
        access = {'level': level}
        if page_limit is not None:
            access['pageLimit'] = page_limit
        # 3) Остаток квоты скачивания (ребро 7.5) — ТОЛЬКО для читателя (по билету).
        if session and session.get('kind') == 'reader' and self.lich is not None:
            ticket = (session.get('actor') or '')[3:]   # 'RI=<ticket>' → '<ticket>'
            if ticket:
                try:
                    budget = self.lich.download_budget(
                        ticket, '%s/%s' % (db, mfn),
                        reader_category=category, db=db, mfn=mfn)
                except Exception:
                    budget = None
                if budget is not None:
                    access['downloadBudget'] = budget
        return 200, ok({'db': db, 'mfn': mfn, 'artifacts': artifacts,
                        'access': access})

    @staticmethod
    def _bp_provision_report(raw, *, scope, subject):
        """Спроецировать сырой отчёт движка (discipline/specialty/aggregate
        provision) на лёгкий контракт фронта ``BpProvisionReport``.

        Возвращает СУПЕРСЕТ: исходные поля движка (для деска) + лёгкие синонимы,
        которые читает информер фронта: ``scope`` (discipline|specialty|faculty),
        ``subject`` (запрошенный id), ``coefficient`` (= average_kko), ``norm``
        (kko_norm, если есть), ``status`` (ok|deficit), ``copies`` (total_exemplars,
        если есть), ``shortfall``, ``bindings``. ``status`` — ``deficit`` при
        under-provisioned (bool для дисциплины; непустой список для специальности/
        агрегата), иначе ``ok``."""
        out = dict(raw or {})
        out['scope'] = scope
        out['subject'] = subject
        avg = raw.get('average_kko')
        out['coefficient'] = avg
        if raw.get('kko_norm') is not None:
            out['norm'] = raw.get('kko_norm')
        if 'total_exemplars' in raw:
            out['copies'] = raw.get('total_exemplars')
        under = raw.get('under_provisioned')
        is_deficit = bool(under) if isinstance(under, bool) else bool(under)
        out['status'] = 'deficit' if is_deficit else 'ok'
        return out

    def bp_provision(self, session, discipline=None, specialty=None,
                     faculty=None, normalize=False):
        """GET /api/bp/provision?discipline=|specialty=|faculty= — быстрый отчёт
        ККО для деска Книгообеспеченности. STAFF-grant (КО-функция, не публичный).

        Ровно один параметр scope:
          * ``discipline=<id>`` → ``bookprovision.discipline_provision``;
          * ``specialty=<id>``  → ``bookprovision.specialty_provision``;
          * ``faculty=<id>``    → ``bookprovision.provision_aggregate(faculty_id=)``.
        Результат проецируется на ``BpProvisionReport`` (см. ``_bp_provision_report``).
        Неизвестный id → 404 (не 500). Нет ни одного параметра → 400."""
        self._require_staff(session)
        self._guard(session, 'bp.read', self.cfg.db_default, 'read')
        if self.bookprovision is None:
            return 503, err('unavailable', 'book-provision engine unavailable')
        try:
            if discipline:
                raw = self.bookprovision.discipline_provision(
                    int(discipline), normalize=normalize)
                return 200, ok(self._bp_provision_report(
                    raw, scope='discipline', subject=str(discipline)))
            if specialty:
                raw = self.bookprovision.specialty_provision(
                    int(specialty), normalize=normalize)
                return 200, ok(self._bp_provision_report(
                    raw, scope='specialty', subject=str(specialty)))
            if faculty:
                raw = self.bookprovision.provision_aggregate(
                    faculty_id=int(faculty), normalize=normalize)
                return 200, ok(self._bp_provision_report(
                    raw, scope='faculty', subject=str(faculty)))
        except (ValueError, _bookprovision.BookProvisionError) as e:
            # Нечисловой scope (напр. оператор ввёл НАЗВАНИЕ дисциплины в быстром
            # отчёте ProvisionLookup) → int() бросает ValueError ДО движка. Ловим
            # вместе с BookProvisionError → мягкая деградация 404 (не 500), как и
            # обещает docstring «Неизвестный id → 404».
            return 404, err('not_found', str(e))
        return 400, err('bad_request', 'discipline, specialty or faculty required')

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
        self._webhooks_emit(session.get('tenant', DEFAULT_TENANT), 'loan.issued',
                            {'loanId': loan['id'], 'ticket': ticket, 'item': item,
                             'due': d.computed['due']})
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

    # ---- Enforcement матрицы доступов (#331 Фаза 2) ----------------------- #
    def _matrix_enforce_cap(self, session, resource, current):
        """Применить лимит тарифа к ресурсу при текущем потреблении ``current``.

        Резолвит матрицу тенанта; превышение (``current >= limit``) при режиме
        ``block`` -> ``Denied(402)``; при ``grace`` или в пределах -> возвращает
        ``(verdict, info)`` для мягкого предупреждения. Fail-open: нет стора
        тарифов -> ``('allow', {})`` (dev/непровиженные работают)."""
        if self.tariffs is None:
            return 'allow', {}
        from access import access_matrix as _am
        tenant = session.get('tenant', DEFAULT_TENANT)
        verdict, info = _am.cap_verdict(_am.resolve(self.tariffs, tenant),
                                        resource, current)
        if verdict == 'deny':
            raise Denied(402, 'payment_required',
                         'лимит тарифа исчерпан: %s (%s/%s)'
                         % (resource, current, info.get('limit')))
        return verdict, info

    def _matrix_section_verdict(self, session, section):
        """Вердикт раздела матрицы для тенанта: ``allow|grace|deny``.

        Fail-open: нет стора тарифов -> ``allow``. Вызывающий роут сам решает —
        ``deny`` обычно -> 402 (раздел не входит в тариф)."""
        if self.tariffs is None:
            return 'allow'
        from access import access_matrix as _am
        return _am.section_verdict(
            _am.resolve(self.tariffs, session.get('tenant', DEFAULT_TENANT)), section)

    def _tenant_usage(self, tenant):
        """Текущее потребление ресурсов тенанта (usage vs cap, #331).

        Best-effort подсчёт по own-store: каждый счётчик в своём try/except (любая
        ошибка -> 0), чтобы виджет лимитов никогда не падал. ``storage_mb`` пока не
        отслеживается -> 0. Ключи совпадают с ``access_matrix.RESOURCES``."""
        u = {'staff_seats': 0, 'readers': 0, 'records': 0, 'ocr_pages': 0, 'storage_mb': 0}
        try:
            u['staff_seats'] = len(self._store_for(tenant).list_accounts())
        except Exception:
            pass
        try:
            if self.reader_registry is not None:
                u['readers'] = len(self.reader_registry.list())
        except Exception:
            pass
        try:
            if self.catalog is not None:
                u['records'] = int(self.catalog.count(self.cfg.db_default))
        except Exception:
            pass
        try:
            store = getattr(self.ocr, 'store', None)
            if store is not None:
                u['ocr_pages'] = len(store.all_pages())
        except Exception:
            pass
        return u

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
        # Лимит тарифа на число сотруднических аккаунтов (#331 Фаза 2): при
        # block-режиме сверх лимита -> 402; иначе создаём (grace мягко пропускает).
        self._matrix_enforce_cap(session, 'staff_seats', len(store.list_accounts()))
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
        mods = entitlements.enabled_modules(tenant)
        return 200, ok({
            'tenant': tenant, 'plan': plan,
            'limits': _billing.plan_limits(plan),
            'usage': usage,
            'modules': mods,
            # Режим (узел 3) = производное от набора модулей (demo/webportal/full
            # или 'custom', если оператор включил нестандартный набор вручную).
            'mode': entitlements.derive_mode(mods),
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

    def admin_set_mode(self, session, body):
        """POST /api/admin/billing/mode {tenant,mode} — переключить РЕЖИМ тенанта.

        Режим (demo/webportal/full) — именованный пресет набора модулей поверх
        entitlements (``entitlements.MODE_PRESETS``): применяет пресет через
        ``set_mode`` (enable модули режима, disable прочие). Это «крупный» брат
        ``admin_set_module`` (тот тумблит один модуль). Best-effort на public/dev
        (fail-open — нечего персистить). Audited."""
        self._require_super_admin(session)
        tenant = (body.get('tenant') or '').strip()
        if not tenant:
            return 400, err('bad_request', 'tenant required')
        mode = (body.get('mode') or '').strip()
        if mode not in entitlements.MODE_PRESETS:
            return 400, err('bad_request', 'unknown mode: %s (ожидается %s)'
                            % (mode, ', '.join(entitlements.MODES)))
        applied = True
        if entitlements._is_public(tenant):
            applied = False                  # dev/public: fail-open, нечего персистить
        else:
            try:
                entitlements.set_mode(tenant, mode)
            except Exception as e:
                return 400, err('bad_request', str(e))
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'mode', 'tenant': tenant, 'mode': mode})
        return 200, ok({'tenant': tenant, 'mode': mode, 'applied': applied,
                        'modules': entitlements.enabled_modules(tenant)})

    # ---- Публичная страница продукта: заявка на демодоступ (#226) ----
    # POST /api/demo-request — ПУБЛИЧНЫЙ (без логина): форма на /product собирает
    # ФИО/e-mail/телефон/учреждение/должность + ОБЯЗАТЕЛЬНОЕ согласие 152-ФЗ. Без
    # согласия → 400 и заявка НЕ сохраняется. GET /api/admin/demo-requests — листинг
    # заявок (ПДн), только super-admin (admin.db@admin).
    def demo_request(self, body):
        """POST /api/demo-request {fullName,email,phone,institution,position,consent}.

        Публичный (без сессии). Согласие на обработку ПДн (152-ФЗ) ОБЯЗАТЕЛЬНО:
        ``consent`` ложно → 400 (заявка не сохраняется). ФИО + e-mail валидируются.
        Хранится ровно набор полей формы + согласие + время (минимизация). Аудит
        пишется БЕЗ ПДн заявителя (только факт + id) — ПДн не попадают в журнал."""
        if self.demo_requests is None:
            return 503, err('unavailable', 'demo request store unavailable')
        body = body or {}
        consent = bool(body.get('consent'))
        try:
            rec = self.demo_requests.add(
                full_name=body.get('fullName') or body.get('full_name') or '',
                email=body.get('email') or '',
                phone=body.get('phone') or '',
                institution=body.get('institution') or '',
                position=body.get('position') or '',
                consent=consent)
        except _demo_requests.ConsentRequired as e:
            return 400, err('consent_required', str(e))
        except _demo_requests.ValidationError as e:
            return 400, err('bad_request', str(e))
        # Аудит факта заявки — БЕЗ ПДн (минимизация): только id и отметка согласия.
        try:
            self._store_for(DEFAULT_TENANT).audit(
                'public', 'demo.request', None, rec['id'], 'ok',
                {'op': 'demo-request', 'consent': True})
        except Exception:
            pass
        return 200, ok({'id': rec['id'], 'accepted': True})

    def admin_demo_requests(self, session, limit):
        """GET /api/admin/demo-requests?limit= — заявки на демодоступ (super-admin).

        Содержат ПДн заявителей, поэтому только super-admin (admin.db@admin), как
        соседние кросс-тенантные admin-поверхности. Новейшие первыми."""
        self._require_super_admin(session)
        if self.demo_requests is None:
            return 200, ok({'items': []})
        items = self.demo_requests.list(limit)
        self._store_for(session.get('tenant', DEFAULT_TENANT)).audit(
            session['actor'], 'admin.db', None, None, 'ok',
            {'op': 'demo-requests', 'count': len(items)})
        return 200, ok({'items': items})

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

    def _device_compat(self, path, body, headers):
        """device-facing compat-шим IDlogic: POST /api/devices/<endpoint> (#272).

        Аутентификация — унаследованный Basic ``ServiceLogin`` (compat-режим, env
        EASYBOOK_LEGACY_PASS); без него подсистема закрыта (401), как и положено
        для бесшовного подхвата существующих устройств. Тело — JSON DTO IDlogic,
        ответ — нативный результат через ``CompatDevicesService.handle``."""
        if self.compat_devices is None:
            return 503, err('unavailable', 'devices subsystem not configured')
        if not self.compat_devices.authorize(headers.get('authorization')):
            return 401, err('unauthorized', 'device authorization required')
        endpoint = path[len('/api/devices/'):].strip('/')
        try:
            return 200, ok(self.compat_devices.handle(endpoint, body))
        except _compat_devices.CompatError as e:
            return 400, err('unsupported', str(e))

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
            if method == 'GET' and path == '/api/auth/oidc/providers':
                return self.auth_oidc_providers()
            if method == 'GET' and path == '/api/auth/oidc/start':
                return self.auth_oidc_start(session, query)
            if method == 'POST' and path == '/api/auth/oidc/callback':
                return self.auth_oidc_callback(body or {})
            if method == 'POST' and path == '/api/auth/oidc/bind':
                return self.auth_oidc_bind(session, body or {})
            if method == 'POST' and path == '/api/staff/link-reader':
                return self.staff_link_reader(session, body or {})
            if method == 'POST' and path == '/api/staff/unlink-reader':
                return self.staff_unlink_reader(session)
            if method == 'POST' and path == '/api/staff/view-as-reader':
                return self.view_as_reader(session)
            if method == 'GET' and path == '/api/health':
                return 200, self.health()
            if method == 'GET' and path == '/api/metrics':
                return self.metrics(session)
            # ---- Публичная заявка на демодоступ (#226) — БЕЗ логина ----
            if method == 'POST' and path == '/api/demo-request':
                return self.demo_request(body or {})
            # ---- Внешние устройства IDlogic (compat-шим, #272) — Basic ServiceLogin ----
            if method == 'POST' and path.startswith('/api/devices/'):
                return self._device_compat(path, body or {}, headers)
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
            # ---- Глобальная корректировка .gbl по выборке каталога (ребро 11.2) ----
            if method == 'POST' and path == '/api/cataloging/gbl':
                return self.cataloging_gbl(session, body or {})
            if method == 'POST' and path == '/api/order':
                return self.order(session, body or {})
            # ---- reader-portal: holds, notifications inbox, shelves (#222) ----
            if method == 'POST' and path == '/api/hold':
                return self.place_hold(session, body or {})
            if method == 'GET' and path == '/api/holds':
                return self.list_holds(session)
            if method == 'POST' and path == '/api/holds/batch':
                return self.place_holds_batch(session, body or {})
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
            # ---- ИРИ/SDI (ребро 10.1) ----
            if method == 'POST' and path == '/api/sdi/profile':
                return self.sdi_add(session, body or {})
            if method == 'GET' and path == '/api/sdi/profiles':
                return self.sdi_list(session)
            if method == 'POST' and path == '/api/sdi/profile/remove':
                return self.sdi_remove(session, body or {})
            if method == 'POST' and path == '/api/sdi/run':
                return self.sdi_run(session, body or {})
            if method == 'GET' and path == '/api/sdi/new':
                return self.sdi_new(session)
            # ---- Сводный каталог SK (рёбра 8.1/8.2) ----
            if method == 'GET' and path == '/api/union/search':
                return self.union_search(
                    session, (query.get('q', [''])[0] or '').strip(),
                    (query.get('year', [''])[0] or '').strip())
            if method == 'POST' and path == '/api/union/ingest':
                return self.union_ingest(session, body or {})
            # ---- Диспетч уведомлений (ребро 11.3) ----
            if method == 'POST' and path == '/api/admin/notifications/dispatch':
                return self.notifications_dispatch(session, body or {})
            # ---- ВКР (рёбра 7.6/8.3) ----
            if method == 'POST' and path == '/api/vkr':
                return self.vkr_submit(session, body or {})
            if method == 'GET' and path == '/api/vkr':
                return self.vkr_list(session, query)
            if method == 'POST' and path == '/api/vkr/review':
                return self.vkr_review(session, body or {})
            # ---- КСУ авто-распределение (ребро 5.3) ----
            if method == 'POST' and path == '/api/ksu/distribute':
                return self.ksu_distribute(session, body or {})
            # ---- Периодика (рёбра 9.2/9.3) ----
            if method == 'POST' and path == '/api/serials':
                return self.serials_register(session, body or {})
            if method == 'POST' and path == '/api/serials/issue':
                return self.serials_add_issue(session, body or {})
            if method == 'GET' and path == '/api/serials/search':
                return self.serials_search(session, query)
            # ---- DAM / файлы (ребро 7.1) ----
            if method == 'POST' and path == '/api/dam/attach':
                return self.dam_attach(session, body or {})
            if method == 'GET' and path == '/api/dam':
                return self.dam_assets(session, query)
            # ---- Оцифровка: выставки / IIIF / OCR / OAI-PMH (PR #325) ----
            # Точные пути POST/GET — выше generic-роута выставки по slug (тот
            # GET-only, len(parts)==3), чтобы /api/exhibits/item|publish не
            # перехватывались как slug. Новые namespace'ы (/api/exhibits, /api/iiif,
            # /api/ocr, /api/oai) не коллизируют с существующим диспетчем.
            if method == 'POST' and path == '/api/exhibits':
                return self.exhibit_create(session, body or {})
            if method == 'POST' and path == '/api/exhibits/item':
                return self.exhibit_add_item(session, body or {})
            if method == 'POST' and path == '/api/exhibits/publish':
                return self.exhibit_publish(session, body or {})
            if method == 'GET' and path == '/api/exhibits':
                return self.exhibits_list(session, query)
            if (method == 'GET' and len(parts) == 3
                    and parts[0] == 'api' and parts[1] == 'exhibits'):
                return self.exhibit_view(session, parts[2])
            if method == 'GET' and path == '/api/iiif/manifest':
                return self.iiif_manifest(session, query)
            if method == 'POST' and path == '/api/ocr/index':
                return self.ocr_index(session, body or {})
            if method == 'GET' and path == '/api/ocr/search':
                return self.ocr_search(session, query)
            if method == 'POST' and path == '/api/ocr/recognize':
                return self.ocr_recognize(session, body or {})
            if method == 'POST' and path == '/api/ocr/process':
                return self.ocr_process(session, body or {})
            if method == 'GET' and path == '/api/oai':
                return self.oai(session, query)
            # ---- Батч #240: шаблоны метаданных · очередь задач · подписки ----
            if method == 'GET' and path == '/api/cataloging/templates':
                return self.templates_types(session, query)
            if method == 'GET' and path == '/api/cataloging/template':
                return self.template_skeleton(session, query)
            if method == 'POST' and path == '/api/cataloging/template':
                return self.template_save(session, body or {})
            if method == 'POST' and path == '/api/jobs':
                return self.job_enqueue(session, body or {})
            if method == 'GET' and path == '/api/jobs':
                return self.jobs_list(session, query)
            if method == 'POST' and path == '/api/jobs/claim':
                return self.job_claim(session, body or {})
            if method == 'POST' and path == '/api/jobs/complete':
                return self.job_complete(session, body or {})
            if method == 'POST' and path == '/api/jobs/fail':
                return self.job_fail(session, body or {})
            if method == 'POST' and path == '/api/me/collections':
                return self.collection_subscribe(session, body or {})
            if method == 'GET' and path == '/api/me/collections':
                return self.collection_subs_list(session, query)
            if method == 'POST' and path == '/api/me/collections/cancel':
                return self.collection_unsubscribe(session, body or {})
            # ---- Батч #240 (2-я волна): авто-фасеты + реестр IP-диапазонов ----
            if method == 'GET' and path == '/api/facet-config':
                return self.facet_config_list(session, query)
            if method == 'POST' and path == '/api/facet-config':
                return self.facet_config_set(session, body or {})
            if method == 'POST' and path == '/api/facet-config/remove':
                return self.facet_config_remove(session, body or {})
            if method == 'POST' and path == '/api/facets/compute':
                return self.facets_compute(session, body or {})
            if method == 'GET' and path == '/api/admin/ip-ranges/resolve':
                return self.ip_resolve(session, query)
            if method == 'GET' and path == '/api/admin/ip-ranges':
                return self.ip_ranges_list(session, query)
            if method == 'POST' and path == '/api/admin/ip-ranges':
                return self.ip_range_add(session, body or {})
            if method == 'POST' and path == '/api/admin/ip-ranges/remove':
                return self.ip_range_remove(session, body or {})
            # ---- Browse-указатели A–Z (#240) ----
            if method == 'GET' and path == '/api/browse':
                return self.browse_terms(session, query)
            # ---- Матрица доступов / тарифы (admin, #331) ----
            if method == 'GET' and path == '/api/admin/access-matrix':
                return self.access_matrix_get(session, query)
            if method == 'GET' and path == '/api/admin/tariffs':
                return self.tariffs_table(session, query)
            if method == 'POST' and path == '/api/admin/tariffs':
                return self.tariff_create(session, body or {})
            if method == 'POST' and path == '/api/admin/tariffs/cell':
                return self.tariff_cell_set(session, body or {})
            if method == 'POST' and path == '/api/admin/tariffs/assign':
                return self.tariff_assign(session, body or {})
            if method == 'POST' and path == '/api/admin/tariffs/addon':
                return self.tariff_addon(session, body or {})
            if method == 'POST' and path == '/api/admin/tariffs/delete':
                return self.tariff_delete(session, body or {})
            # ---- Онбординг: режим развёртывания / конфиг библиотеки / подключения (#335) ----
            if method == 'GET' and path == '/api/admin/deployment/catalog':
                return self.deployment_catalog(session, query)
            if method == 'GET' and path == '/api/admin/deployment':
                return self.deployment_get(session, query)
            if method == 'POST' and path == '/api/admin/deployment':
                return self.deployment_set(session, body or {})
            if method == 'POST' and path == '/api/admin/onboard':
                return self.onboard_apply(session, body or {})
            if method == 'GET' and path == '/api/library-config':
                return self.library_config_public(session, query)
            if method == 'GET' and path == '/api/admin/library-config':
                return self.library_config_get(session, query)
            if method == 'POST' and path == '/api/admin/library-config':
                return self.library_config_set(session, body or {})
            if method == 'GET' and path == '/api/admin/connections':
                return self.connections_list(session, query)
            if method == 'POST' and path == '/api/admin/connections':
                return self.connection_set(session, body or {})
            if method == 'POST' and path == '/api/admin/connections/remove':
                return self.connection_remove(session, body or {})
            if method == 'POST' and path == '/api/admin/inforost/plan':
                return self.inforost_plan(session, body or {})
            if method == 'POST' and path == '/api/admin/inforost/import':
                return self.inforost_import(session, body or {})
            if method == 'POST' and path == '/api/admin/inforost/import-exhibits':
                return self.inforost_import_exhibits(session, body or {})
            if method == 'POST' and path == '/api/admin/inforost/import-records':
                return self.inforost_import_records(session, body or {})
            # ---- Исходящие вебхуки (#356) ----
            if method == 'GET' and path == '/api/admin/webhooks':
                return self.webhooks_list(session, query)
            if method == 'POST' and path == '/api/admin/webhooks':
                return self.webhooks_subscribe(session, body or {})
            if method == 'POST' and path == '/api/admin/webhooks/active':
                return self.webhooks_set_active(session, body or {})
            if method == 'POST' and path == '/api/admin/webhooks/remove':
                return self.webhooks_remove(session, body or {})
            if method == 'POST' and path == '/api/admin/webhooks/preview':
                return self.webhooks_preview(session, body or {})
            if method == 'GET' and path == '/api/admin/webhooks/deliveries':
                return self.webhooks_deliveries(session, query)
            # ---- Авторитетный/нормативный контроль (#359) ----
            if method == 'GET' and path == '/api/authority':
                return self.authority_search(session, query)
            if method == 'POST' and path == '/api/authority':
                return self.authority_create(session, body or {})
            if method == 'POST' and path == '/api/authority/variant':
                return self.authority_variant(session, body or {})
            if method == 'POST' and path == '/api/authority/link':
                return self.authority_link(session, body or {})
            if method == 'POST' and path == '/api/authority/find-or-create':
                return self.authority_find_or_create(session, body or {})
            if method == 'POST' and path == '/api/authority/merge':
                return self.authority_merge(session, body or {})
            if method == 'POST' and path == '/api/authority/remove':
                return self.authority_remove(session, body or {})
            # ---- Активные модули тенанта по режиму развёртывания (#335) ----
            if method == 'GET' and path == '/api/me/modules':
                return self.my_modules(session)
            # ---- Морфо-полнотекст: FTS + BM25 (#368) ----
            if method == 'GET' and path == '/api/fulltext/search':
                return self.fulltext_search(session, query)
            if method == 'GET' and path == '/api/fulltext/more-like':
                return self.fulltext_more_like(session, query)
            if method == 'POST' and path == '/api/fulltext/index':
                return self.fulltext_index(session, body or {})
            if method == 'POST' and path == '/api/fulltext/reindex-ocr':
                return self.fulltext_reindex_ocr(session, body or {})
            if method == 'POST' and path == '/api/fulltext/reindex-catalog':
                return self.fulltext_reindex_catalog(session, query)
            # ---- Аналитический обзор библиотеки (штат) ----
            if method == 'GET' and path == '/api/analytics/overview':
                return self.analytics_overview(session)
            # ---- Комплектование: поставщики/счета + подписка (PR #316) ----
            if method == 'POST' and path == '/api/acq/supplier':
                return self.suppliers_add(session, body or {})
            if method == 'GET' and path == '/api/acq/suppliers':
                return self.suppliers_list(session, query)
            if method == 'POST' and path == '/api/acq/supplier/invoice':
                return self.supplier_invoice(session, body or {})
            if method == 'POST' and path == '/api/acq/subscription':
                return self.subscription_add(session, body or {})
            if method == 'GET' and path == '/api/acq/subscriptions':
                return self.subscriptions_list(session, query)
            if method == 'POST' and path == '/api/acq/subscription/receive':
                return self.subscription_receive(session, body or {})
            # ---- Каталогизатор: MARC/MARCXML обмен (PR #316/#317) ----
            if method == 'POST' and path == '/api/cataloging/marc/export':
                return self.marc_export(session, body or {})
            if method == 'POST' and path == '/api/cataloging/marc/import':
                return self.marc_import(session, body or {})
            if method == 'POST' and path == '/api/cataloging/marcxml/export':
                return self.marcxml_export(session, body or {})
            if method == 'POST' and path == '/api/cataloging/marcxml/import':
                return self.marcxml_import(session, body or {})
            # ---- Каталогизатор: copy-cataloging SRU/Z39.50 (#240) ----
            if method == 'POST' and path == '/api/cataloging/copy/url':
                return self.copy_search_url(session, body or {})
            if method == 'POST' and path == '/api/cataloging/copy/parse':
                return self.copy_parse(session, body or {})
            if method == 'POST' and path == '/api/cataloging/copy/import':
                return self.copy_import(session, body or {})
            # ---- Каталогизатор: дедуп / печать ГОСТ (PR #317) ----
            if method == 'POST' and path == '/api/cataloging/dedup':
                return self.dedup_scan(session, body or {})
            if method == 'POST' and path == '/api/cataloging/dedup/check':
                return self.dedup_check(session, body or {})
            if method == 'POST' and path == '/api/cataloging/print':
                return self.catalog_print_route(session, body or {})
            # ---- Каталогизатор: версии записи (PR #316) ----
            if method == 'GET' and path == '/api/cataloging/versions':
                return self.versions_history(session, query)
            if method == 'POST' and path == '/api/cataloging/versions/snapshot':
                return self.versions_snapshot(session, body or {})
            if method == 'POST' and path == '/api/cataloging/versions/revert':
                return self.versions_revert(session, body or {})
            # ---- Каталогизатор: редактор словарей .mnu/.tre (PR #317) ----
            if method == 'GET' and path == '/api/cataloging/vocab':
                return self.vocab_values(session, query)
            if method == 'POST' and path == '/api/cataloging/vocab/value':
                return self.vocab_add_value(session, body or {})
            if method == 'GET' and path == '/api/cataloging/tree':
                return self.tree_children(session, query)
            if method == 'POST' and path == '/api/cataloging/tree/node':
                return self.tree_add_node(session, body or {})
            # ---- Администратор: роли RBAC (PR #318) ----
            if method == 'GET' and path == '/api/admin/rbac/roles':
                return self.rbac_roles(session, query)
            if method == 'POST' and path == '/api/admin/rbac/role':
                return self.rbac_create_role(session, body or {})
            if method == 'POST' and path == '/api/admin/rbac/grant':
                return self.rbac_add_grant(session, body or {})
            if method == 'POST' and path == '/api/admin/rbac/assign':
                return self.rbac_assign(session, body or {})
            if method == 'GET' and path == '/api/admin/rbac/effective':
                return self.rbac_effective(session, query)
            # ---- Администратор: аудит-трейл + конфиг (PR #318) ----
            if method == 'GET' and path == '/api/admin/audit-trail':
                return self.audit_trail_query(session, query)
            if method == 'GET' and path == '/api/admin/audit-trail/export.csv':
                return self.audit_trail_export(session, query)
            if method == 'GET' and path == '/api/admin/config':
                return self.config_list(session, query)
            if method == 'POST' and path == '/api/admin/config':
                return self.config_set(session, body or {})
            # ---- Утилиты: стат/экспорт/дубли/ФЛК-lite (PR #318) ----
            if method == 'POST' and path == '/api/utils/stats':
                return self.utils_stats(session, body or {})
            if method == 'POST' and path == '/api/utils/export':
                return self.utils_export(session, body or {})
            if method == 'POST' and path == '/api/utils/duplicates':
                return self.utils_duplicates(session, body or {})
            if method == 'POST' and path == '/api/utils/validate':
                return self.utils_validate(session, body or {})
            # ---- Книговыдача: политики выдачи (PR #320, ребро 11.4) ----
            if method == 'GET' and path == '/api/circ/policies':
                return self.loan_policies_list(session, query)
            if method == 'POST' and path == '/api/circ/policy':
                return self.loan_policy_set(session, body or {})
            if method == 'GET' and path == '/api/circ/policy/resolve':
                return self.loan_policy_resolve(session, query)
            # ---- Книговыдача: должники/санкции (PR #320) ----
            if method == 'GET' and path == '/api/circ/debts':
                return self.debts_list(session, query)
            if method == 'POST' and path == '/api/circ/debt':
                return self.debt_register(session, body or {})
            if method == 'POST' and path == '/api/circ/debt/settle':
                return self.debt_settle(session, body or {})
            if method == 'GET' and path == '/api/circ/blocks':
                return self.blocks_list(session, query)
            if method == 'POST' and path == '/api/circ/block/evaluate':
                return self.block_evaluate(session, body or {})
            # ---- Книгообеспеченность: нормы РПД + ККО-аналитика (PR #320) ----
            # NB: /api/bp/rpd/* — отдельный namespace от существующих
            # bookprovision-роутов /api/bp/discipline (факультет/специальность/
            # контингент/привязка), чтобы не шадоить их в диспетче.
            if method == 'POST' and path == '/api/bp/rpd/discipline':
                return self.discipline_add(session, body or {})
            if method == 'GET' and path == '/api/bp/rpd/disciplines':
                return self.disciplines_list(session, query)
            if method == 'POST' and path == '/api/bp/rpd/norm':
                return self.discipline_norm_set(session, body or {})
            if method == 'GET' and path == '/api/bp/rpd/required':
                return self.discipline_required(session, query)
            if method == 'POST' and path == '/api/bp/kko/report':
                return self.kko_report(session, body or {})
            if method == 'POST' and path == '/api/bp/kko/snapshot':
                return self.kko_snapshot_save(session, body or {})
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
            # Быстрый отчёт ККО для деска (discipline|specialty|faculty). Staff-only.
            if method == 'GET' and path == '/api/bp/provision':
                norm = query.get('normalize', ['0'])[0] in ('1', 'true', 'yes')
                return self.bp_provision(
                    session,
                    discipline=(query.get('discipline', [''])[0] or '').strip(),
                    specialty=(query.get('specialty', [''])[0] or '').strip(),
                    faculty=(query.get('faculty', [''])[0] or '').strip(),
                    normalize=norm)
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
            if method == 'POST' and path == '/api/admin/billing/mode':
                return self.admin_set_mode(session, body or {})
            # ---- Заявки на демодоступ (публичная страница продукта, super-admin, #226) ----
            if method == 'GET' and path == '/api/admin/demo-requests':
                limit = min(1000, max(1, int(query.get('limit', ['100'])[0])))
                return self.admin_demo_requests(session, limit)
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
            # ---- Готовые движки связности: linked / fulltext (публичные) ----
            # /api/linked/{db}/{mfn}?kind=children|host — обход связи иерархии.
            if method == 'GET' and len(parts) == 4 and parts[0] == 'api' and parts[1] == 'linked':
                return self.linked(session, parts[2], int(parts[3]),
                                   query.get('kind', ['children'])[0])
            # /api/fulltext/{db}/{mfn} — артефакты ПТ + уровень доступа.
            if method == 'GET' and len(parts) == 4 and parts[0] == 'api' and parts[1] == 'fulltext':
                return self.fulltext_record(session, parts[2], int(parts[3]))
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
    prefix = (query.get('prefix', ['ALL'])[0] or 'ALL').strip().upper()
    # Multi-field default (#245): OR across title + author + keywords so a cyrillic
    # query returns hits even where the K= keyword index is unreliable on the server.
    # Each leg is truncated ($) for recall. IRBIS query OR operator is ' + '.
    if prefix in ('ALL', '*', ''):
        qu = q.upper()   # match the UPPERCASE dictionary form (recall for lowercase input)
        return ' + '.join('"%s=%s$"' % (p, qu) for p in ('T', 'A', 'K'))
    if prefix in _TRUNCATED_PREFIXES and not q.endswith('$'):
        q += '$'
    return '"%s=%s"' % (prefix, q)
