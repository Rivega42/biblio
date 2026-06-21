#!/usr/bin/env python3
"""152-ФЗ / ФСТЭК compliance BACKEND tests — audit findings V1 / V5 / V9
(GitHub #199, epic #223; AUDIT_REPORT_IRBIS64_compliance.md; SPEC_compliance_152fz;
SPEC_pki_keys ADR-006). Exercises the three critical gaps closed in this slice:

  * V1 — field-level encryption of stored ПДн at rest. The reader display name in
    ``reader_review`` is ciphertext at rest (a raw dump never reveals it) and is
    decrypted only in the handler. The AES-GCM (AEAD) leg is SKIPPED-WITH-NOTE when
    the ``cryptography`` lib is absent (CI has no it) — the always-available dev
    fallback / pgcrypto leg still proves ciphertext-at-rest, so CI never fails for
    want of a cipher backend.
  * V5 — ПДн-access journal. A staff formulary read (GET /api/circ/reader) writes a
    ``pdn.read`` audit entry {actor, subject=ticket, action}; GET /api/admin/pdn-
    access returns it newest-first (super-admin only — 403 for regular staff /
    reader / guest). A reader reading their OWN data is NOT journaled.
  * V9 — consent + right-to-erasure. GET/POST /api/reader/consent records consent
    (append-only history); POST /api/reader/erase {confirm:true} deletes the authed
    reader's OWN reviews/holds/shelves/history/saved-searches/consent from OUR store
    (never the live ИРБИС RDR), returns per-table counts, audits, and a reader can
    only erase their own ticket's data (cross-ticket isolation).

Construction mirrors test_social / test_circ_routes: a constructed ``core.Api``
(no live ИРБИС) with an in-memory access store + a fake ИРБИС that resolves a
reader name, and an in-memory circulation engine so the formulary read runs. PG
parity (pgcrypto encryption + consent + erasure on a real PostgreSQL) runs on the
postgres backend and skips cleanly otherwise.

Wired into the test_access.py runner (module list). Standalone:
    py tests/test_compliance.py
    (set ACCESS_BACKEND=postgres) py -3.12 tests/test_compliance.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.store import AccessStore
from access import crypto
from access import circulation as _circ
from access.authz import READER_GRANTS, GUEST_GRANTS

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Staff/admin grants minted onto the session token (no DB role needed). The
# super-admin grant is admin.db/*/admin (carried by the seeded 'administrator'
# role); circ.issue lets staff read the formulary.
SUPER_ADMIN_GRANTS = [
    {'function': 'circ.issue', 'db': '*', 'level': 'write'},
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
]
PLAIN_STAFF_GRANTS = [
    {'function': 'circ.issue', 'db': '*', 'level': 'write'},
]

READER_NAME = 'Читателев Чеслав Читателевич'


class FakeRdrIrbis:
    """Minimal ИРБИС stand-in: RI= search resolves to a fixed RDR mfn whose field
    10 carries the reader name, so core._social_reader_name returns a real ПДн."""

    def read_record(self, db, mfn):
        if db == 'RDR':
            return {'mfn': mfn, 'fields': [
                {'tag': '10', 'value': READER_NAME, 'text': READER_NAME,
                 'subfields': {}}]}
        from irbis.client import IrbisError
        raise IrbisError(-140, 'no such mfn')

    def search(self, db, expr):
        e = expr.strip().strip('"')
        if e.startswith('RI='):
            return (1, [77])
        return (0, [])


def _api():
    """Constructed Api: in-memory access store + fake ИРБИС + in-memory circ."""
    os.environ['JWT_SECRET'] = 'compliance-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.access = AccessStore(':memory:')
    api.irbis = FakeRdrIrbis()
    # Rebuild the reader-scoped services over the fresh store (the constructor
    # built them over the original store before we swapped api.access).
    from access.social import SocialService
    from access.holds import HoldService
    from access.shelves import ShelfService
    api.social = SocialService(
        api.access, read_terms=api._social_terms, search=api._social_search,
        brief_read=api._hold_brief, reader_name=api._social_reader_name)
    api.holds = HoldService(api.access, catalog=None, brief_read=api._hold_brief)
    api.shelves = ShelfService(api.access, brief_read=api._hold_brief)
    # In-memory circulation so GET /api/circ/reader (the formulary read) runs.
    api.circulation = _circ.CirculationEngine(
        store=_circ.CirculationStore(':memory:'),
        notifications=api.notifications, catalog=None,
        catalog_db=api.cfg.db_default)
    return api, _core


def _headers(api, kind, actor, grants, **extra):
    tok, _ = api._new_session(kind, actor, grants, tenant='public', **extra)
    return {'authorization': 'Bearer ' + tok}


def _staff_h(api, grants=PLAIN_STAFF_GRANTS, login='circ'):
    return _headers(api, 'staff', login, grants)


def _admin_h(api, login='admin'):
    return _headers(api, 'staff', login, SUPER_ADMIN_GRANTS)


def _reader_h(api, ticket='111'):
    return _headers(api, 'reader', 'RI=%s' % ticket, READER_GRANTS, rdr_mfn=77)


def _guest_h(api):
    return _headers(api, 'guest', 'guest', GUEST_GRANTS)


# --------------------------------------------------------------------------- #
# V1 — field-level ПДн encryption at rest (crypto round-trip + ciphertext at rest).
# --------------------------------------------------------------------------- #
def crypto_checks():
    print('-- V1: crypto round-trip + ciphertext at rest (backend=%s, aead=%s)'
          % (crypto.backend(), crypto.aead_available()))

    # The always-available leg (dev fallback OR pgcrypto-key path): round-trip +
    # ciphertext (plaintext not a substring) + transparency for non-tokens.
    name = READER_NAME
    tok = crypto.encrypt(name)
    check('encrypt yields a pdn token', crypto.is_token(tok))
    check('round-trip decrypt == plaintext', crypto.decrypt(tok) == name)
    check('ciphertext at rest (name not in token)', name not in tok)
    check('empty/None pass through encrypt', crypto.encrypt('') == '' and crypto.encrypt(None) is None)
    check('legacy plaintext passes through decrypt', crypto.decrypt('Иванов И.') == 'Иванов И.')
    check('encrypt is idempotent (no double-wrap)', crypto.encrypt(tok) == tok)

    # Key ROTATION: a token written under one key id still reads after the active
    # id changes; new writes use the new id.
    old_id, old_k = os.environ.get('PDN_KEY_ID'), os.environ.get('PDN_KEY')
    try:
        os.environ['PDN_KEY_ID'] = 'a'
        os.environ['PDN_KEY_a'] = 'secret-a'
        ta = crypto.encrypt('РотацияA')
        os.environ['PDN_KEY_ID'] = 'b'
        os.environ['PDN_KEY_b'] = 'secret-b'
        tb = crypto.encrypt('РотацияB')
        check('rotated: old-id ciphertext still decrypts', crypto.decrypt(ta) == 'РотацияA')
        check('rotated: new-id ciphertext decrypts', crypto.decrypt(tb) == 'РотацияB')
        check('tokens carry distinct key ids', ta.split(':')[3] == 'a' and tb.split(':')[3] == 'b')
    finally:
        for k in ('PDN_KEY_a', 'PDN_KEY_b'):
            os.environ.pop(k, None)
        if old_id is None:
            os.environ.pop('PDN_KEY_ID', None)
        else:
            os.environ['PDN_KEY_ID'] = old_id
        if old_k is not None:
            os.environ['PDN_KEY'] = old_k

    # The AES-GCM (AEAD) leg — SKIP-WITH-NOTE when `cryptography` is absent.
    if crypto.aead_available():
        check('AEAD backend is AES-GCM', crypto.backend() == 'gcm')
        t = crypto.encrypt(name)
        check('AES-GCM token tagged gcm', t.split(':')[2] == 'gcm')
        check('AES-GCM round-trip', crypto.decrypt(t) == name)
    else:
        print('  note  AES-GCM leg SKIPPED (cryptography not installed) — '
              'dev-fallback cipher proves ciphertext-at-rest; prod uses '
              'pgcrypto (PG) or AES-GCM (with cryptography)')


def store_crypto_checks():
    print('-- V1: reader_review.reader_name stored as ciphertext, decrypted on read')
    st = AccessStore(':memory:')
    row = st.review_upsert('111', 'IBIS', 1, 5, 'отлично', READER_NAME, 1000.0)
    check('review_upsert returns decrypted name', row['reader_name'] == READER_NAME)

    raw = st.review_name_ciphertext('111', 'IBIS', 1)
    raw_s = raw.decode('utf-8', 'replace') if isinstance(raw, (bytes, bytearray)) else raw
    check('stored value is NOT plaintext', READER_NAME not in (raw_s or ''))
    check('stored value is a pdn ciphertext token', crypto.is_token(raw_s))

    # Reads decrypt transparently.
    mine = st.review_mine('111', 'IBIS', 1)
    check('review_mine decrypts name', mine['reader_name'] == READER_NAME)
    cards = st.reviews_for('IBIS', 1)
    check('reviews_for decrypts name', cards and cards[0]['reader_name'] == READER_NAME)

    # An empty name stays NULL/empty (no ciphering an empty PII slot).
    st.review_upsert('222', 'IBIS', 1, 4, '', '', 1001.0)
    check('empty name stored as-is (not ciphered)',
          not crypto.is_token(st.review_name_ciphertext('222', 'IBIS', 1) or ''))


# --------------------------------------------------------------------------- #
# V5 — ПДн-access journal (staff read journals; reader-own does not; route guard).
# --------------------------------------------------------------------------- #
def pdn_journal_checks():
    print('-- V5: staff formulary read journals pdn.read; /api/admin/pdn-access')
    api, _core = _api()

    # A staff member reads a reader's formulary → a pdn.read entry is written with
    # actor + subject ticket.
    st, p = api.route('GET', '/api/circ/reader', {'ticket': ['111']}, None, _staff_h(api))
    check('staff formulary read 200', st == 200)
    check('formulary shows the (decrypted) reader name',
          p['data']['reader']['name'] == READER_NAME)

    entries = api.access.pdn_access_log(50)
    check('a pdn.read journal entry was written', len(entries) == 1)
    if entries:
        e = entries[0]
        import json as _json
        detail = e['detail'] if isinstance(e['detail'], dict) else _json.loads(e['detail'])
        check('journal records actor', e['actor'] == 'circ')
        check('journal records subject ticket', detail.get('subject') == '111')
        check('journal records read action', detail.get('action') == 'read')

    # GET /api/admin/pdn-access — super-admin sees it newest-first.
    st, p = api.route('GET', '/api/admin/pdn-access', {}, None, _admin_h(api))
    check('admin pdn-access 200 (super-admin)', st == 200)
    check('admin pdn-access returns the entry',
          len(p['data']['items']) == 1 and p['data']['items'][0]['function'] == 'pdn.read')

    # Regular staff / reader / guest are 403 (the journal is itself ПДн-by-ref).
    st, _ = api.route('GET', '/api/admin/pdn-access', {}, None, _staff_h(api))
    check('regular staff pdn-access 403', st == 403)
    st, _ = api.route('GET', '/api/admin/pdn-access', {}, None, _reader_h(api))
    check('reader pdn-access 403', st == 403)
    st, _ = api.route('GET', '/api/admin/pdn-access', {}, None, _guest_h(api))
    check('guest pdn-access 403', st in (401, 403))


def pdn_self_access_checks():
    print('-- V5: a reader reading their OWN data is NOT journaled')
    api, _core = _api()
    H = _reader_h(api, '111')

    # A reader posts + lists their own review (reads own ПДн) — no pdn.read entry.
    api.route('POST', '/api/review', {}, {'db': 'IBIS', 'mfn': 1, 'rating': 5,
                                          'text': 'моя книга'}, H)
    api.route('GET', '/api/reviews', {'db': ['IBIS'], 'mfn': ['1']}, None, H)
    api.route('GET', '/api/history', {}, None, H)
    check('reader self-access wrote NO pdn.read entry', len(api.access.pdn_access_log(50)) == 0)

    # Direct helper check: actor == subject ⇒ skipped; actor != subject ⇒ journaled.
    rsess = api._session(H['authorization'][7:])
    api._audit_pdn_read(rsess, '111', ['name'], 'self')      # own ticket → skip
    check('helper skips reader-own access', len(api.access.pdn_access_log(50)) == 0)
    api._audit_pdn_read(rsess, '999', ['name'], 'other')     # different ticket → journal
    check('helper journals reader access to ANOTHER subject',
          len(api.access.pdn_access_log(50)) == 1)


# --------------------------------------------------------------------------- #
# V9 — consent + right-to-erasure.
# --------------------------------------------------------------------------- #
def consent_checks():
    print('-- V9: consent get/set (append-only history)')
    api, _core = _api()
    H = _reader_h(api, '111')

    # Unset → given:false.
    st, p = api.route('GET', '/api/reader/consent', {}, None, H)
    check('consent get (unset) 200 given:false', st == 200 and p['data']['given'] is False)

    # Grant.
    st, p = api.route('POST', '/api/reader/consent', {}, {'given': True}, H)
    check('consent set granted 200', st == 200 and p['data']['given'] is True)
    st, p = api.route('GET', '/api/reader/consent', {}, None, H)
    check('consent now reads granted', p['data']['given'] is True)
    check('consent carries version + ts', 'version' in p['data'] and p['data'].get('ts'))

    # Withdraw → latest row wins; prior granted row is kept (append-only).
    api.route('POST', '/api/reader/consent', {}, {'given': False}, H)
    st, p = api.route('GET', '/api/reader/consent', {}, None, H)
    check('consent withdraw reflected', p['data']['given'] is False)
    rows = api.access._conn().execute(
        'SELECT COUNT(*) AS n FROM reader_consent WHERE ticket=?', ('111',)).fetchone()['n']
    check('consent is append-only (2 history rows)', rows == 2)

    # Missing 'given' → 400; a guest/staff (non-reader) → 403.
    st, _ = api.route('POST', '/api/reader/consent', {}, {}, H)
    check('consent set without given -> 400', st == 400)
    st, _ = api.route('GET', '/api/reader/consent', {}, None, _staff_h(api))
    check('non-reader consent -> 403', st == 403)


def erasure_checks():
    print('-- V9: erase removes exactly the reader OWN rows + audits + cross-ticket')
    api, _core = _api()
    H1 = _reader_h(api, '111')
    H2 = _reader_h(api, '222')

    # Seed data for BOTH readers across every table.
    for H, t in ((H1, '111'), (H2, '222')):
        api.route('POST', '/api/review', {}, {'db': 'IBIS', 'mfn': 1, 'rating': 5,
                                              'text': 'r'}, H)
        api.route('POST', '/api/hold', {}, {'db': 'IBIS', 'mfn': 7}, H)
        api.route('POST', '/api/shelves', {}, {'name': 'Мой список'}, H)
        api.route('GET', '/api/history', {}, None, H)       # no-op (history auto-logged elsewhere)
        api.social.log_open(t, 'IBIS', 9)
        api.route('POST', '/api/savedsearch', {}, {'name': 'q', 'db': 'IBIS',
                                                   'prefix': 'K', 'query': 'базы'}, H)
        api.route('POST', '/api/reader/consent', {}, {'given': True}, H)

    def counts(ticket):
        c = api.access._conn()
        return {
            'reviews': c.execute('SELECT COUNT(*) n FROM reader_review WHERE ticket=?', (ticket,)).fetchone()['n'],
            'holds': c.execute('SELECT COUNT(*) n FROM reader_hold WHERE ticket=?', (ticket,)).fetchone()['n'],
            'shelves': c.execute('SELECT COUNT(*) n FROM reader_shelf WHERE ticket=?', (ticket,)).fetchone()['n'],
            'history': c.execute('SELECT COUNT(*) n FROM reader_history WHERE ticket=?', (ticket,)).fetchone()['n'],
            'saved': c.execute('SELECT COUNT(*) n FROM saved_search WHERE ticket=?', (ticket,)).fetchone()['n'],
            'consent': c.execute('SELECT COUNT(*) n FROM reader_consent WHERE ticket=?', (ticket,)).fetchone()['n'],
        }

    before1, before2 = counts('111'), counts('222')
    check('reader 111 has data in every table', all(v > 0 for v in before1.values()))

    # Erase requires confirm:true.
    st, _ = api.route('POST', '/api/reader/erase', {}, {}, H1)
    check('erase without confirm -> 400', st == 400)

    # Reader 111 erases their own data.
    st, p = api.route('POST', '/api/reader/erase', {}, {'confirm': True}, H1)
    check('erase 200', st == 200)
    erased = p['data']['erased']
    check('erase returns per-table counts',
          erased.get('reviews') == 1 and erased.get('holds') == 1
          and erased.get('savedSearches') == 1 and erased.get('consent') == 1)

    after1, after2 = counts('111'), counts('222')
    check('reader 111 rows all gone', all(v == 0 for v in after1.values()))
    check('reader 222 rows UNTOUCHED (cross-ticket isolation)', after2 == before2)

    # Erasure is audited.
    erasure_audit = [a for a in api.access.recent_audit(50) if a['function'] == 'erasure']
    check('erasure is audited', len(erasure_audit) >= 1)

    # A reader can only erase THEIR OWN ticket — the ticket is derived from the
    # session, never the body, so there is no cross-ticket erase. A staff/guest is
    # refused (reader session required).
    st, _ = api.route('POST', '/api/reader/erase', {}, {'confirm': True}, _staff_h(api))
    check('staff erase -> 403 (reader session required)', st == 403)


# --------------------------------------------------------------------------- #
# Postgres parity — pgcrypto encryption + consent + erasure on real PG.
# --------------------------------------------------------------------------- #
def pg_parity_checks():
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return
    try:
        from access.pgstore import PgAccessStore, default_pg_dsn
        st = PgAccessStore(os.environ.get('ACCESS_PG_DSN', default_pg_dsn()))
        st._conn().execute('TRUNCATE reader_review, reader_hold, reader_shelf, '
                           'reader_shelf_item, reader_history, saved_search, '
                           'reader_consent RESTART IDENTITY')
    except Exception as e:
        print('-- compliance pg parity SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return
    print('-- compliance: postgres parity (pgcrypto=%s)' % getattr(st, '_pgcrypto', None))

    # V1 — reader_name encrypted at rest, decrypted on read (pgcrypto or token).
    row = st.review_upsert('pg-1', 'IBIS', 1, 5, 'ok', READER_NAME, 1000.0)
    check('[pg] review_upsert returns decrypted name', row['reader_name'] == READER_NAME)
    raw = st.review_name_ciphertext('pg-1', 'IBIS', 1)
    raw_s = raw.decode('utf-8', 'replace') if isinstance(raw, (bytes, bytearray)) else str(raw)
    check('[pg] stored reader_name is NOT plaintext', READER_NAME not in (raw_s or ''))
    check('[pg] reviews_for decrypts name',
          st.reviews_for('IBIS', 1)[0]['reader_name'] == READER_NAME)
    check('[pg] review_mine decrypts name',
          st.review_mine('pg-1', 'IBIS', 1)['reader_name'] == READER_NAME)

    # V9 — consent append-only + erasure scope.
    st.consent_record('pg-1', True, 1, 1000.0)
    st.consent_record('pg-1', False, 1, 1001.0)
    cur = st.consent_current('pg-1')
    check('[pg] consent effective = latest (withdrawn)', cur and cur['given'] is False)

    st.hold_add('pg-1', 'IBIS', 7, 'T', 'queued', 1000.0)
    st.saved_search_add('pg-1', 'q', 'IBIS', 'K', 'базы', 1000.0)
    st.hold_add('pg-2', 'IBIS', 7, 'T', 'queued', 1000.0)     # another reader, untouched
    erased = st.erase_reader('pg-1')
    check('[pg] erase removes reviews+holds+saved+consent',
          erased['reviews'] == 1 and erased['holds'] == 1
          and erased['savedSearches'] == 1 and erased['consent'] == 2)
    check('[pg] other reader hold untouched', len(st.holds_for('pg-2')) == 1)

    # V5 — pdn.read journal read on PG.
    st.audit('staff1', 'pdn.read', None, None, 'ok', {'subject': 'pg-1', 'action': 'read'})
    j = st.pdn_access_log(50)
    check('[pg] pdn_access_log returns pdn.read entry',
          len(j) == 1 and j[0]['function'] == 'pdn.read')


def main():
    crypto_checks()
    store_crypto_checks()
    pdn_journal_checks()
    pdn_self_access_checks()
    consent_checks()
    erasure_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
