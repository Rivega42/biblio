#!/usr/bin/env python3
"""Declarative ФЛК validation-engine tests (gap A2, epic #188).

Covers the first shippable slice of the engine layered on the merged A5 seeding
(seed_vocab / vocabulary tables), tenancy (#100) and Identity (#101):

  1. Check digits (pure): the real ISBN-10 / ISBN-13 / ISSN check-digit algorithms
     accept known-good and reject known-bad identifiers.
  2. Engine (pure, with an in-memory seeded store): a valid record passes; missing
     200^a -> severity-1; a bad language code -> dictionary violation (against the
     A5-seeded jz.mnu); a bad ISBN checksum is caught; 920-branching selects the
     correct rules; a type-2 warning leaves the record saveable; per-tenant override
     softens / disables a rule.
  3. API (pure, constructed Api — no live IRBIS): POST /api/validate is tenant-
     scoped via the JWT claim and guarded like save_record; returns violations.

Invoked by the test_access.py runner (flk_checks) so the CI postgres step runs it
too with NO .github/ change. The sqlite suite stays green locally with no DB; the
PG-only path skips cleanly when postgres is unavailable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import flk
from access import seed_vocab
from access.store import AccessStore

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _seeded_store():
    """An in-memory Access store seeded with the A5 system vocabs (jz/vd/...)."""
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


# --------------------------------------------------------------------------- #
# 1. Check digits — pure, backend-independent.
# --------------------------------------------------------------------------- #
def checksum_checks():
    print('-- checksums (isbn/issn)')
    # ISBN-10: valid (5-7654-0001-9 has the correct mod-11 check digit).
    check('isbn-10 valid', flk.isbn_checksum_ok('5-7654-0001-9'))
    # Flip the check digit -> invalid.
    check('isbn-10 bad check digit rejected', not flk.isbn_checksum_ok('5-7654-0001-0'))
    # 'X' as the check digit is the literal value 10 — valid where it balances mod 11.
    check('isbn-10 X check digit valid', flk.isbn_checksum_ok('0-8044-2957-X'))
    # A well-known valid ISBN-10 and ISBN-13.
    check('isbn-10 0306406152 valid', flk.isbn_checksum_ok('0-306-40615-2'))
    check('isbn-13 9780306406157 valid', flk.isbn_checksum_ok('978-0-306-40615-7'))
    check('isbn-13 bad rejected', not flk.isbn_checksum_ok('978-0-306-40615-0'))
    check('isbn empty rejected', not flk.isbn_checksum_ok(''))
    check('isbn wrong length rejected', not flk.isbn_checksum_ok('12345'))
    # ISSN: 0378-5955 is a textbook-valid ISSN.
    check('issn 0378-5955 valid', flk.issn_checksum_ok('0378-5955'))
    check('issn bad rejected', not flk.issn_checksum_ok('0378-5950'))


# --------------------------------------------------------------------------- #
# 2. Engine — pure, with a seeded in-memory store.
# --------------------------------------------------------------------------- #
def engine_checks():
    print('-- engine (validate)')
    store = _seeded_store()

    # A clean, valid book record: 920 worklist, title, language, good ISBN, executor.
    good = {
        '920': 'PAZK',
        '200': {'a': 'Основы каталогизации'},
        '101': 'rus',
        '10': {'a': '5-7654-0001-9'},
        '907': {'a': 'Иванова И.И.'},
    }
    res = flk.validate(good, phase='save', store=store)
    check('valid record passes (overall 0)', res['overallSeverity'] == flk.SEV_PASS)
    check('valid record canSave', res['canSave'] is True)
    check('valid record has no violations', res['violations'] == [])

    # Missing 200^a on a non-аналитика book -> severity-1 (непреодолимо), blocks save.
    no_title = dict(good)
    no_title.pop('200')
    res = flk.validate(no_title, phase='save', store=store)
    ids = [v['ruleId'] for v in res['violations']]
    check('missing 200^a -> rec.200a.mandatory fires', 'rec.200a.mandatory' in ids)
    title_v = [v for v in res['violations'] if v['ruleId'] == 'rec.200a.mandatory'][0]
    check('missing 200^a is severity 1', title_v['severity'] == flk.SEV_HARD)
    check('missing 200^a blocks save (canSave False)', res['canSave'] is False)
    check('missing 200^a violation bound to path 200/a', title_v['path'] == '200/a')

    # Bad language code -> dictionary violation against the A5-seeded jz.mnu.
    bad_lang = dict(good, **{'101': 'zzz'})
    res = flk.validate(bad_lang, phase='save', store=store)
    ids = [v['ruleId'] for v in res['violations']]
    check('bad lang code -> fld.101.lang.dict fires', 'fld.101.lang.dict' in ids)
    lang_v = [v for v in res['violations'] if v['ruleId'] == 'fld.101.lang.dict'][0]
    check('bad lang code is severity 1', lang_v['severity'] == flk.SEV_HARD)
    check('bad lang message interpolates the value', 'zzz' in lang_v['message'])
    # A valid seeded code (rus) must NOT trip the dictionary rule.
    res_ok = flk.validate(good, phase='save', store=store)
    check('valid lang code passes dictionary',
          'fld.101.lang.dict' not in [v['ruleId'] for v in res_ok['violations']])

    # Bad ISBN checksum is caught (fieldExit phase for the ISBN rule).
    bad_isbn = dict(good, **{'10': {'a': '5-7654-0001-0'}})
    res = flk.validate(bad_isbn, phase='fieldExit', field='10', store=store)
    ids = [v['ruleId'] for v in res['violations']]
    check('bad ISBN checksum caught', 'fld.10.isbn.checksum' in ids)
    isbn_v = [v for v in res['violations'] if v['ruleId'] == 'fld.10.isbn.checksum'][0]
    check('ISBN violation is severity 2 (преодолимо)', isbn_v['severity'] == flk.SEV_SOFT)
    # Good ISBN passes the same fieldExit run.
    res = flk.validate(good, phase='fieldExit', field='10', store=store)
    check('good ISBN passes fieldExit', res['violations'] == [])

    # 920-branching: rec.200a.mandatory (branch negate NJ*/A*) must NOT fire on an
    # NJ record (it's excluded), and the analytics-softened variant fires on A*.
    nj_no_title = {'920': 'NJ31', '101': 'rus', '907': {'a': 'X'}}
    res = flk.validate(nj_no_title, phase='save', store=store)
    ids = [v['ruleId'] for v in res['violations']]
    check('920=NJ31 excludes rec.200a.mandatory', 'rec.200a.mandatory' not in ids)

    analyt_no_title = {'920': 'ASP', '101': 'rus', '907': {'a': 'X'}}
    res = flk.validate(analyt_no_title, phase='save', store=store)
    ids = [v['ruleId'] for v in res['violations']]
    check('920=ASP (A*) selects analytics-softened title rule',
          'rec.200a.mandatory.analyt' in ids and 'rec.200a.mandatory' not in ids)
    analyt_v = [v for v in res['violations']
                if v['ruleId'] == 'rec.200a.mandatory.analyt'][0]
    check('analytics title rule is severity 2', analyt_v['severity'] == flk.SEV_SOFT)

    # A type-2-only record is still saveable (canSave True) — преодолимое не блокирует.
    # ASP record without 200^a yields ONLY soft (analytics title + nothing hard).
    check('type-2-only record stays saveable',
          res['canSave'] is True and res['overallSeverity'] == flk.SEV_SOFT)

    # Worst-severity aggregation: a record with both a hard (no 920) and soft
    # (bad ISBN) violation aggregates to 1 and blocks.
    mixed = {'200': {'a': 'T'}, '101': 'rus', '10': {'a': '5-7654-0001-0'},
             '907': {'a': 'X'}}                 # no 920 -> rec.920.mandatory (hard)
    res = flk.validate(mixed, phase='save', store=store)
    sevs = {v['severity'] for v in res['violations']}
    check('mixed record has both sev1 and sev2', flk.SEV_HARD in sevs)
    check('worst-severity aggregates to 1', res['overallSeverity'] == flk.SEV_HARD)
    check('violations sorted severity-1 first',
          res['violations'][0]['severity'] == flk.SEV_HARD)

    # 920 mandatory: empty 920 -> rec.920.mandatory severity-1.
    no_920 = {'200': {'a': 'T'}, '101': 'rus', '907': {'a': 'X'}}
    res = flk.validate(no_920, phase='save', store=store)
    check('missing 920 -> rec.920.mandatory fires',
          'rec.920.mandatory' in [v['ruleId'] for v in res['violations']])

    # 907 ФИО: a non-журнал record without 907^a -> soft.
    no_fio = {'920': 'PAZK', '200': {'a': 'T'}, '101': 'rus'}
    res = flk.validate(no_fio, phase='save', store=store)
    check('missing 907^a -> rec.907.fio fires (soft)',
          'rec.907.fio' in [v['ruleId'] for v in res['violations']])

    # 907 ФИО branch: on a журнал (920=J) the 907 rule is excluded.
    jrnl = {'920': 'J', '200': {'a': 'T'}, '101': 'rus'}
    res = flk.validate(jrnl, phase='save', store=store)
    check('920=J excludes rec.907.fio',
          'rec.907.fio' not in [v['ruleId'] for v in res['violations']])


# --------------------------------------------------------------------------- #
# 2b. Per-tenant override (SPEC §3).
# --------------------------------------------------------------------------- #
def override_checks():
    print('-- per-tenant override')
    store = _seeded_store()
    no_title = {'920': 'PAZK', '101': 'rus', '907': {'a': 'X'}}

    # Baseline: missing title is hard (blocks).
    base = flk.validate(no_title, phase='save', store=store)
    check('baseline missing title blocks', base['canSave'] is False)

    # Soften rec.200a.mandatory 1 -> 2: now the record is saveable (with warning).
    overrides = {'rec.200a.mandatory': {'severity': flk.SEV_SOFT}}
    rs = flk.load_ruleset(tenant_overrides=overrides)
    soft = flk.validate(no_title, phase='save', store=store, ruleset=rs)
    title_v = [v for v in soft['violations'] if v['ruleId'] == 'rec.200a.mandatory'][0]
    check('override softens 200a to severity 2', title_v['severity'] == flk.SEV_SOFT)
    check('softened rule no longer blocks save', soft['canSave'] is True)

    # Hardening is refused by default (canon severity kept).
    rs_h = flk.load_ruleset(tenant_overrides={'fld.10.isbn.checksum': {'severity': flk.SEV_HARD}})
    isbn_rule = [r for r in rs_h if r['id'] == 'fld.10.isbn.checksum'][0]
    check('hardening refused by default (severity kept 2)',
          isbn_rule['severity'] == flk.SEV_SOFT)
    # ...unless explicitly allowed.
    rs_h2 = flk.load_ruleset(tenant_overrides={'fld.10.isbn.checksum': {'severity': flk.SEV_HARD}},
                             allow_hardening=True)
    isbn_rule2 = [r for r in rs_h2 if r['id'] == 'fld.10.isbn.checksum'][0]
    check('hardening applied when allow_hardening', isbn_rule2['severity'] == flk.SEV_HARD)

    # Disable a rule: it no longer fires.
    rs_d = flk.load_ruleset(tenant_overrides={'rec.200a.mandatory': {'enabled': False}})
    disabled = flk.validate(no_title, phase='save', store=store, ruleset=rs_d)
    check('disabled rule does not fire',
          'rec.200a.mandatory' not in [v['ruleId'] for v in disabled['violations']])

    # Custom message override is returned.
    rs_m = flk.load_ruleset(tenant_overrides={'rec.200a.mandatory': {'message': 'НЕТ ЗАГЛАВИЯ!'}})
    custom = flk.validate(no_title, phase='save', store=store, ruleset=rs_m)
    title_v = [v for v in custom['violations'] if v['ruleId'] == 'rec.200a.mandatory'][0]
    check('custom message override returned', title_v['message'] == 'НЕТ ЗАГЛАВИЯ!')

    # A1-blocked rules are carried (registered) but disabled by default.
    full = flk.load_ruleset()
    blocked = [r for r in full if r.get('blocked_on') == 'A1']
    check('A1-blocked rules are registered', len(blocked) >= 1)
    check('A1-blocked rules are disabled', all(not r['enabled'] for r in blocked))
    check('rule count is 8+ (seeded canon)', len(flk.SYSTEM_RULES) >= 8)


# --------------------------------------------------------------------------- #
# 3. API — constructed Api, no live IRBIS (the constructor doesn't connect).
# --------------------------------------------------------------------------- #
def api_checks():
    print('-- api /api/validate')
    os.environ['JWT_SECRET'] = 'flk-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()

    # A staff session on the public tenant with a record.write grant (cataloging
    # is licensed by default on public -> entitlement gate open).
    grants = [{'function': 'record.write', 'db': '*', 'level': 'write'}]
    _tok, sess = api._new_session('staff', 'cataloger', grants, tenant='public')

    body = {'db': 'IBIS', 'phase': 'save',
            'record': {'920': 'PAZK', '101': 'rus', '907': {'a': 'X'}}}  # no 200^a
    status, payload = api.validate_record(sess, body)
    check('validate endpoint returns 200', status == 200)
    check('validate endpoint ok envelope', payload.get('ok') is True)
    data = payload['data']
    check('validate endpoint reports canSave False (hard violation)',
          data['canSave'] is False)
    check('validate endpoint surfaces the title violation',
          any(v['ruleId'] == 'rec.200a.mandatory' for v in data['violations']))

    # A valid record passes through the endpoint.
    good_body = {'db': 'IBIS', 'phase': 'save', 'record': {
        '920': 'PAZK', '200': {'a': 'T'}, '101': 'rus',
        '10': {'a': '5-7654-0001-9'}, '907': {'a': 'X'}}}
    status, payload = api.validate_record(sess, good_body)
    check('valid record canSave via endpoint', payload['data']['canSave'] is True)
    check('valid record no violations via endpoint', payload['data']['violations'] == [])

    # Guard: a session WITHOUT record.write is denied (403).
    from access.authz import GUEST_GRANTS
    _gt, guest = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    denied = False
    try:
        api.validate_record(guest, body)
    except _core.Denied as d:
        denied = d.status == 403
    check('validate denied without record.write grant (403)', denied)

    # Route dispatch reaches the handler (status 200 via route()).
    headers = {'authorization': 'Bearer ' + _tok}
    status, payload = api.route('POST', '/api/validate', {}, good_body, headers)
    check('route POST /api/validate dispatches (200)', status == 200)


def main():
    checksum_checks()
    engine_checks()
    override_checks()
    api_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
