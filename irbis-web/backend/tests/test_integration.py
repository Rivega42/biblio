#!/usr/bin/env python3
"""Cross-module integration tests — the «связующая ткань» seams (INTEGRATION_MAP).

Wires the two highest-value межмодульные рёбра that the integration map flagged
as designed-but-not-wired, and proves them end-to-end over the existing in-memory
stores (no core.py, no network):

  * Edges 2.1/2.2 — Catalog↔Circulation 910^A flip. ``CirculationEngine`` is given
    a ``catalog`` handle; ``checkout`` flips the linked catalog exemplar's
    ``910^A`` 0→1 (issued), ``return_item`` flips it 1→0 (free), and ``place_hold``
    /availability reads honour the catalog ``910^A``. The item↔record link is
    resolved by inventory number (``910^b``), as the spec describes.

  * Edge 6.1 — Authority↔Catalog ^3 on save. ``CatalogStore`` is given an
    ``authority`` handle; a field instance carrying ``_authority_ref`` (the
    authority record id) is resolved through ``authority.substitute`` on ``save``,
    filling ``^a/^b/^g`` + the ``^3`` link before ФЛК/index.

Both seams are exercised WITH the handle (wired) and the back-compat paths
(no handle) are re-asserted so nothing regresses.

Standalone-runnable in the house style of tests/test_catalog.py /
tests/test_circulation.py::

    py -3.12 tests/test_integration.py  ->  'ok …' lines + 'N passed, M failed'

Also wired into tests/test_access.py (the CI runner) via module_checks so the
existing CI step exercises these seams with no workflow change.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import flk
from access import seed_vocab
from access import authority as A
from access.authority import AuthorityStore
from access.catalog import (CatalogStore, EXEMPLAR_FREE, EXEMPLAR_ISSUED)
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy,
    ALLOW, SECONDS_PER_DAY,
)
from access.store import AccessStore

PASS = [0]
FAIL = [0]

DAY = SECONDS_PER_DAY
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Fixtures.
# --------------------------------------------------------------------------- #
def _seeded_access_store():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


def _book_with_copy(inv='1024365', status=EXEMPLAR_FREE):
    """A valid book carrying one 910 exemplar keyed by inventory ``inv`` whose
    910^A starts at ``status`` (default free)."""
    return {
        '920': 'PAZK',
        '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.'}],
        '700': [{'a': 'Петров П.П.'}],
        '101': 'rus',
        '910': [{'a': status, 'b': inv}],
        '907': [{'a': 'Сидорова С.С.'}],
    }


# --------------------------------------------------------------------------- #
# Edge 2.1/2.2 — Catalog↔Circulation 910^A flip (the original break).
# --------------------------------------------------------------------------- #
def checkout_return_flip_checks():
    print('-- edge 2.1/2.2: checkout/return flip catalog 910^A')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    inv = '1024365'
    cat.save('IBIS', _book_with_copy(inv, EXEMPLAR_FREE))

    # the catalog accessors locate + read the exemplar by inventory number (910^b)
    check('exemplar located by 910^b', cat.find_exemplar('IBIS', inv) is not None)
    check('exemplar starts FREE (910^A=0)',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)
    check('is_available True before loan', cat.is_available('IBIS', inv) is True)

    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(),
                            catalog=cat, catalog_db='IBIS')
    store.add_reader('R1', category='В01')

    # CHECKOUT: 910^A flips 0 -> 1 (issued) on the linked catalog record.
    d = eng.checkout('R1', inv, T0)
    check('checkout allowed', d.decision == ALLOW)
    check('checkout flips catalog 910^A 0->1',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_ISSUED)
    check('catalog item not available after checkout',
          cat.is_available('IBIS', inv) is False)
    check('checkout reports the flipped catalog mfn',
          d.computed.get('catalog_mfn') == 1
          and d.computed.get('exemplar_status') == EXEMPLAR_ISSUED)
    # the loan itself still recorded in circulation's own store
    check('loan recorded on hand', store.count_on_hand('R1') == 1)

    # RETURN: 910^A flips 1 -> 0 (free).
    loan_id = d.computed['loan']['id']
    dr = eng.return_item(loan_id, T0 + 5 * DAY)
    check('return allowed', dr.decision == ALLOW)
    check('return flips catalog 910^A 1->0',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)
    check('catalog item available again after return',
          cat.is_available('IBIS', inv) is True)
    check('return reports the flipped catalog mfn',
          dr.computed.get('catalog_mfn') == 1
          and dr.computed.get('exemplar_status') == EXEMPLAR_FREE)


def availability_read_checks():
    print('-- edge 2.2: hold/availability honours catalog 910^A')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    inv = '777001'
    cat.save('IBIS', _book_with_copy(inv, EXEMPLAR_FREE))
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(),
                            catalog=cat, catalog_db='IBIS')
    store.add_reader('R1', category='В01')

    # FREE copy in the catalog → a hold on it is ready immediately (position 1).
    d = eng.place_hold('R1', inv, T0)
    check('hold on catalog-free item is position 1', d.computed['position'] == 1)
    check('hold on catalog-free item is ready',
          store.get_hold(d.computed['hold']['id'])['status'] == 'ready')
    check('engine.catalog_available True for free copy',
          eng.catalog_available(inv) is True)

    # Now mark the copy ISSUED in the catalog OUT OF BAND (e.g. a parallel desk),
    # with no circulation loan row. place_hold must NOT mark a new hold ready,
    # because the catalog says the copy is not free (edge 2.2).
    cat.set_exemplar_status('IBIS', inv, EXEMPLAR_ISSUED)
    check('engine.catalog_available False for issued copy',
          eng.catalog_available(inv) is False)
    store.add_reader('R2', category='В01')
    d2 = eng.place_hold('R2', inv, T0 + 1 * DAY)
    # R2 is alone in the queue per circulation, but the catalog status blocks ready.
    check('hold NOT ready when catalog marks copy issued',
          store.get_hold(d2.computed['hold']['id'])['status'] == 'queued')


def circulation_backcompat_checks():
    print('-- edge 2.1/2.2 back-compat: circulation standalone (no catalog)')
    # No catalog handle → engine behaves exactly as before; no crash, no flip.
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())
    store.add_reader('R1', category='В01')
    d = eng.checkout('R1', 'SHELF-1', T0)
    check('standalone checkout allowed', d.decision == ALLOW)
    check('standalone checkout reports no catalog_mfn',
          'catalog_mfn' not in d.computed)
    check('standalone catalog_available is None (no opinion)',
          eng.catalog_available('SHELF-1') is None)
    dr = eng.return_item(d.computed['loan']['id'], T0 + 1 * DAY)
    check('standalone return allowed', dr.decision == ALLOW)
    check('standalone return reports no catalog_mfn',
          'catalog_mfn' not in dr.computed)

    # Catalog wired but the item is UNKNOWN to the catalog → graceful no-op flip.
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    eng2 = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat)
    eng2.store.add_reader('R2', category='В01')
    d2 = eng2.checkout('R2', 'NO-SUCH-INV', T0)
    check('checkout of catalog-unknown item still allowed', d2.decision == ALLOW)
    check('catalog-unknown item flip is a no-op (no catalog_mfn)',
          'catalog_mfn' not in d2.computed)


# --------------------------------------------------------------------------- #
# Edge 6.1 — Authority↔Catalog ^3 on save.
# --------------------------------------------------------------------------- #
def _authority_store_with_tolstoy():
    auth = AuthorityStore(':memory:')
    pid = auth.add_record(
        'athra',
        {'a': 'Толстой', 'b': 'Л. Н.', 'g': 'Лев Николаевич',
         'f': '1828-1910', '9': '1'},
        terms=['Толстой, Л. Н.'])
    sid = auth.add_record(
        'athrs',
        {'a': 'Литература', 'b': 'История и критика'},
        terms=['Литература'])
    return auth, pid, sid


def authority_on_save_checks():
    print('-- edge 6.1: catalog.save fills ^3 + subfields from authority')
    auth, pid, sid = _authority_store_with_tolstoy()
    cat = CatalogStore(':memory:', access_store=_seeded_access_store(),
                       authority=auth)

    # A record whose 700 carries only an _authority_ref (the authority id). On
    # save, the seam resolves it: fills ^a/^b/^g/^f/^9 AND the ^3 link.
    rec = {
        '920': 'PAZK',
        '200': [{'a': 'Война и мир'}],
        '700': [{'_authority_ref': pid}],
        '101': 'rus',
        '907': [{'a': 'X'}],
    }
    res = cat.save('IBIS', rec)
    check('save with authority ref succeeds', res['saved'] is True)
    saved = cat.get('IBIS', res['mfn'])
    inst = saved['700'][0]
    check('authority filled 700^a (фамилия)', inst.get('a') == 'Толстой')
    check('authority filled 700^b (инициалы)', inst.get('b') == 'Л. Н.')
    check('authority filled 700^g (расширение)', inst.get('g') == 'Лев Николаевич')
    check('authority filled 700^f (даты)', inst.get('f') == '1828-1910')
    check('^3 link == authority id', inst.get('3') == str(pid))
    check('_authority_ref marker dropped', '_authority_ref' not in inst)

    # subject heading 606 from an athrs record — also gets ^3 + heading subfields.
    rec2 = {
        '920': 'PAZK',
        '200': [{'a': 'Сборник статей'}],
        '606': [{'_authority_ref': sid}],
        '101': 'rus',
        '907': [{'a': 'X'}],
    }
    res2 = cat.save('IBIS', rec2)
    saved2 = cat.get('IBIS', res2['mfn'])
    s606 = saved2['606'][0]
    check('606 filled ^a from athrs', s606.get('a') == 'Литература')
    check('606 carries ^3 == subject authority id', s606.get('3') == str(sid))


def apply_authority_helper_checks():
    print('-- edge 6.1: apply_authority() helper (explicit call)')
    auth, pid, _sid = _authority_store_with_tolstoy()
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())  # no default

    # Helper works with a per-call authority handle even when the store has none.
    rec = {'700': [{}]}
    cat.apply_authority(rec, '700', pid, instance=0, authority=auth)
    check('apply_authority fills ^a', rec['700'][0].get('a') == 'Толстой')
    check('apply_authority sets ^3', rec['700'][0].get('3') == str(pid))

    # Operator-supplied subfields not requested by the fill-map survive; the role
    # ^9 etc. is only set when the authority carries it.
    rec2 = {'701': [{'_authority_ref': pid, '4': '070'}]}  # ^4 role = operator's
    cat.resolve_authority_refs(rec2, authority=auth)
    check('resolve keeps operator ^4 role', rec2['701'][0].get('4') == '070')
    check('resolve fills ^a + ^3 on 701',
          rec2['701'][0].get('a') == 'Толстой'
          and rec2['701'][0].get('3') == str(pid))

    # A broken ^3 reference (unknown authority id) is surfaced loudly, not silent.
    raised = False
    try:
        cat.apply_authority({'700': [{}]}, '700', 999999, authority=auth)
    except A.AuthorityNotFound:
        raised = True
    check('unknown authority id raises AuthorityNotFound', raised)


def authority_backcompat_checks():
    print('-- edge 6.1 back-compat: save without an authority handle')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())  # no authority

    # A record that already carries ^3 (client supplied) saves untouched.
    rec = {
        '920': 'PAZK',
        '200': [{'a': 'Книга'}],
        '700': [{'a': 'Иванов И.', '3': '7'}],
        '101': 'rus',
        '907': [{'a': 'X'}],
    }
    res = cat.save('IBIS', rec)
    check('save without authority handle still works', res['saved'] is True)
    saved = cat.get('IBIS', res['mfn'])
    check('client-supplied ^3 preserved', saved['700'][0].get('3') == '7')
    check('client-supplied ^a preserved', saved['700'][0].get('a') == 'Иванов И.')

    # The plain good-book path (no refs anywhere) is unchanged.
    res2 = cat.save('IBIS', _book_with_copy())
    check('plain save unaffected by edge 6.1', res2['saved'] is True
          and res2['overallSeverity'] == flk.SEV_PASS)


# --------------------------------------------------------------------------- #
# Combined seam — both edges together over one shared catalog.
# --------------------------------------------------------------------------- #
def combined_seam_checks():
    print('-- combined: authority-linked record + circulation flip on its copy')
    auth, pid, _sid = _authority_store_with_tolstoy()
    cat = CatalogStore(':memory:', access_store=_seeded_access_store(),
                       authority=auth)
    inv = '900900'
    rec = {
        '920': 'PAZK',
        '200': [{'a': 'Анна Каренина'}],
        '700': [{'_authority_ref': pid}],
        '101': 'rus',
        '910': [{'a': EXEMPLAR_FREE, 'b': inv}],
        '907': [{'a': 'X'}],
    }
    res = cat.save('IBIS', rec)
    saved = cat.get('IBIS', res['mfn'])
    check('record has ^3 from authority', saved['700'][0].get('3') == str(pid))
    check('record copy starts free', cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)

    eng = CirculationEngine(store=CirculationStore(':memory:'),
                            policy=default_policy(), catalog=cat)
    eng.store.add_reader('R1', category='В01')
    d = eng.checkout('R1', inv, T0)
    check('checkout flips the authority-linked record copy 0->1',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_ISSUED)
    # the ^3 link is untouched by the circulation flip (it only edits 910^A)
    re_saved = cat.get('IBIS', res['mfn'])
    check('^3 survives the 910^A flip', re_saved['700'][0].get('3') == str(pid))
    eng.return_item(d.computed['loan']['id'], T0 + 3 * DAY)
    check('return flips it back 1->0', cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)


def main():
    checkout_return_flip_checks()
    availability_read_checks()
    circulation_backcompat_checks()
    authority_on_save_checks()
    apply_authority_helper_checks()
    authority_backcompat_checks()
    combined_seam_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
