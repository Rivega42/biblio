#!/usr/bin/env python3
"""Заявки на демодоступ (issue #226) — тест.

Публичная страница продукта Biblio (`/product`) несёт форму-заявку на демодоступ.
Эта сьюта покрывает:

  * STORE (sqlite, всегда): сохранение валидной заявки; обязательность согласия
    152-ФЗ (без согласия — НЕ сохраняем, поднимаем ConsentRequired); валидацию
    (ФИО/e-mail); минимизацию (хранится ровно набор полей формы); листинг
    новейшими первыми.
  * ROUTES (через реальный core.Api.route(), sqlite, без живого ИРБИС):
    POST /api/demo-request публичен (без логина), требует согласия (400 без него),
    валидирует; GET /api/admin/demo-requests — только super-admin (403 прочим),
    отдаёт сохранённые заявки.
  * PG-ПАРИТЕТ (когда postgres доступен; иначе чисто пропускается): тот же
    add/consent/validate/list на PgAccessStore-DSN — доказывает портируемость DDL.

Вписана в раннер tests/test_access.py (его module-list) через ``module_checks`` —
раннер вызывает каждую ``*_checks()`` и складывает PASS/FAIL.

Standalone:  py tests/test_demo_requests.py
PG:          (set ACCESS_BACKEND=postgres) py -3.12 tests/test_demo_requests.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import demo_requests
from access.demo_requests import DemoRequestStore, ConsentRequired, ValidationError
from access.authz import GUEST_GRANTS, READER_GRANTS

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# A valid applicant (synthetic ПДн — example.org per RFC 2606).
VALID = dict(full_name='Иванова Мария Петровна', email='m.ivanova@example.org',
             phone='+7 900 000-00-00', institution='ЦГБ им. Пушкина',
             position='Заведующая отделом')


# --------------------------------------------------------------------------- #
# 1. STORE — sqlite (always). Save / consent / validation / minimization / list.
# --------------------------------------------------------------------------- #
def store_checks():
    print('-- demo-requests: store (sqlite)')
    st = DemoRequestStore(':memory:')
    check('empty store count == 0', st.count() == 0)

    # Save a valid request WITH consent.
    rec = st.add(consent=True, **VALID)
    check('add returns an id', isinstance(rec['id'], int) and rec['id'] >= 1)
    check('add echoes consent True', rec['consent'] is True)
    check('store count == 1 after add', st.count() == 1)

    # Minimization: exactly the five form fields + consent + created_at are stored.
    got = st.get(rec['id'])
    check('get round-trips fullName', got['fullName'] == VALID['full_name'])
    check('get round-trips email', got['email'] == VALID['email'])
    check('get round-trips phone', got['phone'] == VALID['phone'])
    check('get round-trips institution', got['institution'] == VALID['institution'])
    check('get round-trips position', got['position'] == VALID['position'])
    check('stored request carries consent', got['consent'] is True)
    check('stored request carries createdAt', isinstance(got['createdAt'], float))
    check('view has no extra PII keys',
          set(got) == {'id', 'fullName', 'email', 'phone', 'institution',
                       'position', 'consent', 'createdAt'})

    # 152-ФЗ: consent is MANDATORY — without it, ConsentRequired and NOTHING saved.
    before = st.count()
    raised = False
    try:
        st.add(consent=False, **VALID)
    except ConsentRequired:
        raised = True
    check('add without consent raises ConsentRequired', raised)
    check('rejected request was NOT persisted', st.count() == before)
    # Falsy consent variants are all rejected.
    for bad in (False, 0, '', None):
        r = False
        try:
            st.add(full_name='Тест', email='t@example.org', consent=bad)
        except ConsentRequired:
            r = True
        check('consent=%r rejected' % (bad,), r)
    check('no falsy-consent request persisted', st.count() == before)

    # Validation: ФИО required, e-mail required + must look like an e-mail.
    def _expect_validation(**kw):
        try:
            st.add(consent=True, **kw)
            return False
        except ValidationError:
            return True
    check('missing fullName rejected',
          _expect_validation(full_name='', email='a@example.org'))
    check('missing email rejected',
          _expect_validation(full_name='Имя', email=''))
    check('malformed email rejected',
          _expect_validation(full_name='Имя', email='not-an-email'))
    check('still only the one valid request', st.count() == 1)

    # Optional fields default to '' (phone/institution/position not required).
    rec2 = st.add(full_name='Сидоров С.С.', email='s@example.org', consent=True)
    g2 = st.get(rec2['id'])
    check('optional fields default to empty', g2['phone'] == '' and g2['position'] == '')

    # Listing: newest first.
    items = st.list()
    check('list returns all requests', len(items) == 2)
    check('list newest-first', items[0]['id'] == rec2['id'])


# --------------------------------------------------------------------------- #
# 2. ROUTES — over the real dispatcher (sqlite, no live ИРБИС).
# --------------------------------------------------------------------------- #
SUPER_ADMIN_GRANTS = [
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]


def _api():
    os.environ['JWT_SECRET'] = 'demo-request-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    os.environ['DEMO_DB'] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    return _core.Api(), _core


def _super(api, login='super'):
    tok, _ = api._new_session('staff', login, SUPER_ADMIN_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _nonadmin(api, login='cat'):
    tok, _ = api._new_session('staff', login, NONADMIN_STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


def route_checks():
    print('-- demo-requests: routes (POST /api/demo-request, GET /api/admin/demo-requests)')
    api, _core = _api()

    # POST is PUBLIC — no Authorization header at all.
    st, p = api.route('POST', '/api/demo-request', {}, {
        'fullName': 'Петров Пётр', 'email': 'p.petrov@example.org',
        'phone': '+7 911 111-11-11', 'institution': 'Библиотека №1',
        'position': 'Директор', 'consent': True}, {})
    check('public POST /api/demo-request -> 200 (no login)', st == 200)
    check('accepted=True with an id', p['data'].get('accepted') is True and p['data'].get('id'))

    # 152-ФЗ: missing consent -> 400, request NOT stored.
    st, p = api.route('POST', '/api/demo-request', {}, {
        'fullName': 'Без Согласия', 'email': 'no@example.org', 'consent': False}, {})
    check('POST without consent -> 400', st == 400)
    check('400 carries consent_required code', p.get('error', {}).get('code') == 'consent_required')

    # consent omitted entirely -> 400 too.
    st, _ = api.route('POST', '/api/demo-request', {}, {
        'fullName': 'Нет Поля', 'email': 'x@example.org'}, {})
    check('POST with consent omitted -> 400', st == 400)

    # Validation: bad e-mail -> 400.
    st, _ = api.route('POST', '/api/demo-request', {}, {
        'fullName': 'Имя', 'email': 'bogus', 'consent': True}, {})
    check('POST malformed email -> 400', st == 400)
    # Missing fullName -> 400.
    st, _ = api.route('POST', '/api/demo-request', {}, {
        'email': 'a@example.org', 'consent': True}, {})
    check('POST missing fullName -> 400', st == 400)

    # Listing: super-admin sees the one accepted request; non-admin / reader / anon 403.
    H = _super(api)
    st, p = api.route('GET', '/api/admin/demo-requests', {}, None, H)
    check('GET /api/admin/demo-requests (super) -> 200', st == 200)
    items = p['data']['items']
    check('listing has exactly the 1 accepted request', len(items) == 1)
    check('listing carries the applicant fields',
          items[0]['email'] == 'p.petrov@example.org'
          and items[0]['fullName'] == 'Петров Пётр'
          and items[0]['consent'] is True)

    st, _ = api.route('GET', '/api/admin/demo-requests', {}, None, _nonadmin(api))
    check('GET demo-requests (non-admin staff) -> 403', st == 403)
    st, _ = api.route('GET', '/api/admin/demo-requests', {}, None, _reader(api))
    check('GET demo-requests (reader) -> 403', st == 403)
    st, _ = api.route('GET', '/api/admin/demo-requests', {}, None, {})
    check('GET demo-requests (anonymous) -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# 3. PG-ПАРИТЕТ — when postgres reachable; else skip cleanly.
# --------------------------------------------------------------------------- #
def _pg_reachable_dsn():
    """Return a PG DSN if the postgres backend is requested AND reachable, else None."""
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return None
    try:
        from access import pgstore
        dsn = pgstore.default_pg_dsn()
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS demo_request')      # deterministic slate
        conn.close()
        return dsn
    except Exception as e:
        print('-- demo-requests: postgres SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return None


def pg_parity_checks():
    dsn = _pg_reachable_dsn()
    if dsn is None:
        return
    print('-- demo-requests: store (postgres parity)')
    st = DemoRequestStore(dsn, backend='postgres')
    check('[pg] empty count == 0', st.count() == 0)
    rec = st.add(consent=True, **VALID)
    check('[pg] add returns an id', isinstance(rec['id'], int) and rec['id'] >= 1)
    check('[pg] count == 1', st.count() == 1)
    got = st.get(rec['id'])
    check('[pg] round-trips email', got['email'] == VALID['email'])
    check('[pg] stored consent True', got['consent'] is True)
    # consent mandatory on PG too.
    before = st.count()
    raised = False
    try:
        st.add(consent=False, **VALID)
    except ConsentRequired:
        raised = True
    check('[pg] consent mandatory', raised and st.count() == before)
    # validation on PG too.
    bad = False
    try:
        st.add(full_name='', email='a@example.org', consent=True)
    except ValidationError:
        bad = True
    check('[pg] validation enforced', bad)
    # listing newest-first.
    rec2 = st.add(full_name='Второй', email='v@example.org', consent=True)
    items = st.list()
    check('[pg] list newest-first', items and items[0]['id'] == rec2['id'])
    # cleanup
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS demo_request')
        conn.close()
    except Exception:
        pass


def main():
    store_checks()
    route_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
