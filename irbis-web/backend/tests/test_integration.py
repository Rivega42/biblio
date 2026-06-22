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
from access.acquisition import AcquisitionEngine, AcquisitionStore
from access.bookprovision import BookProvisionEngine, KIND_MAIN
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


# --------------------------------------------------------------------------- #
# Edge A — Комплектование → Книговыдача (поступление → экземпляр выдаётся).
#
# AcquisitionEngine получает опциональный ``circulation`` handle. После receive()
# (ToCat создаёт 910-экземпляр со статусом «свободен») комплектование
# подтверждает через circulation, что поступивший инв.№ доступен к выдаче, и сам
# экземпляр реально выдаётся.
# --------------------------------------------------------------------------- #
def acq_to_circulation_checks():
    print('-- edge A: поступление (acq) → экземпляр сразу выдаётся (circ)')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat,
                             catalog_db='IBIS')
    acq = AcquisitionEngine(catalog=cat, catalog_db='IBIS', circulation=circ)

    order = acq.create_order('Алгоритмы', author='Кормен Т.', copies=2,
                             price=1000.0)
    inv = ['ACQ-A-1', 'ACQ-A-2']
    res = acq.receive(order['id'], 'KSU-2026-001', 2, inv_numbers=inv)

    # ToCat created the bib record + free 910 exemplars.
    check('receipt created catalog record', res['catalog_mfn'] is not None)
    check('both copies free in catalog after receipt',
          cat.is_available('IBIS', inv[0]) and cat.is_available('IBIS', inv[1]))

    # Invariant: комплектование подтвердило выдаваемость обоих экземпляров через
    # circulation (register_acquired_item → catalog.is_available).
    check('acquisition reports both copies lendable',
          sorted(res['lendable']) == sorted(inv))

    # And the copy really lends through circulation, flipping 910^A 0->1.
    circ.store.add_reader('S1', category='STD')
    d = circ.checkout('S1', inv[0], T0)
    check('received copy checks out', d.decision == ALLOW)
    check('checkout flipped the acquired copy 0->1 in catalog',
          cat.exemplar_status('IBIS', inv[0]) == EXEMPLAR_ISSUED)
    # the second, untouched copy is still free
    check('untouched acquired copy still free',
          cat.is_available('IBIS', inv[1]) is True)


def acq_to_circulation_backcompat_checks():
    print('-- edge A back-compat: acquisition standalone (no circulation)')
    # No circulation handle → receive() works exactly as before; lendable empty.
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    acq = AcquisitionEngine(catalog=cat, catalog_db='IBIS')  # no circulation
    order = acq.create_order('Без выдачи', copies=1, price=10.0)
    res = acq.receive(order['id'], 'KSU-BC-1', 1, inv_numbers=['ACQ-BC-1'])
    check('standalone receipt still succeeds', res['receipt'] is not None)
    check('standalone lendable list is empty', res['lendable'] == [])
    check('standalone КСУ still accumulated',
          acq.ksu_summary('KSU-BC-1')['copies'] == 1)

    # Circulation wired but with NO catalog → register defaults to lendable=True
    # (circulation lends against the shifr, keeps no inventory of its own).
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy())  # no catalog
    acq2 = AcquisitionEngine(circulation=circ)         # no catalog either
    o2 = acq2.create_order('Шифр', copies=1, price=5.0)
    r2 = acq2.receive(o2['id'], 'KSU-BC-2', 1, inv_numbers=['ACQ-BC-2'])
    check('circ-without-catalog accepts copy as lendable',
          r2['lendable'] == ['ACQ-BC-2'])


# --------------------------------------------------------------------------- #
# Edge B — Книгообеспеченность → Книговыдача (Кко учитывает выданные/на руках).
#
# BookProvisionEngine получает опциональный ``circulation`` handle. Выданный
# экземпляр (910^A=1) по-прежнему принадлежит фонду — Кко не должна ронять его
# в 0. С circulation-хендлом такой экземпляр считается обеспеченным, если он на
# руках (on-hand loan).
# --------------------------------------------------------------------------- #
def _bp_one_disc_one_binding(cat, circ, inv):
    """A book-provision engine with one discipline (1 student) bound to one
    catalog holding keyed by ``inv``."""
    bp = BookProvisionEngine(catalog=cat, circulation=circ)
    fac = bp.add_faculty('F1', 'Факультет')
    spec = bp.add_specialty(fac, napr='09.03.01', name='Информатика')
    disc = bp.add_discipline(spec, '3001', name='Алгоритмы', students=1)
    bp.bind_literature(disc, 'Алгоритмы', kind=KIND_MAIN,
                       catalog_db='IBIS', inv_key=inv)
    return bp, disc


def bp_counts_issued_copies_checks():
    print('-- edge B: Кко учитывает выданный (на руках) экземпляр')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    inv = 'BP-1'
    cat.save('IBIS', _book_with_copy(inv, EXEMPLAR_FREE))
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat,
                             catalog_db='IBIS')
    bp, disc = _bp_one_disc_one_binding(cat, circ, inv)

    # Free copy, 1 student → Кко = 1/1 = 1.0 (обеспечено).
    rep = bp.discipline_provision(disc)
    check('free copy: exemplars=1', rep['bindings'][0]['exemplars'] == 1)
    check('free copy: Кко = 1.0', rep['average_kko'] == 1.0)

    # Now issue the copy through circulation (910^A 0->1) to a student.
    circ.store.add_reader('S1', category='STD')
    d = circ.checkout('S1', inv, T0)
    check('copy checked out', d.decision == ALLOW)
    check('catalog now marks the copy issued',
          cat.is_available('IBIS', inv) is False)

    # Invariant (ребро 4.4/4.7): the copy is on a reader's hands but STILL фонд —
    # Кко must keep counting it as 1 provisioned copy, not drop to 0.
    rep2 = bp.discipline_provision(disc)
    check('issued-but-on-hand copy still counts as provisioned',
          rep2['bindings'][0]['exemplars'] == 1)
    check('Кко unchanged at 1.0 while copy on loan',
          rep2['average_kko'] == 1.0)
    check('discipline NOT under-provisioned while copy on loan',
          rep2['under_provisioned'] is False)

    # After return, the copy is free again — still 1 (sanity).
    circ.return_item(d.computed['loan']['id'], T0 + DAY)
    rep3 = bp.discipline_provision(disc)
    check('returned copy still provisioned', rep3['bindings'][0]['exemplars'] == 1)


def bp_lost_copy_not_counted_checks():
    print('-- edge B: подтверждённая утрата покидает фонд (Кко падает)')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    inv = 'BP-2'
    cat.save('IBIS', _book_with_copy(inv, EXEMPLAR_FREE))
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat,
                             catalog_db='IBIS')
    bp, disc = _bp_one_disc_one_binding(cat, circ, inv)

    circ.store.add_reader('S1', category='STD')
    d = circ.checkout('S1', inv, T0)
    # Confirm the loss: lost_status='lost' ⇒ the copy has LEFT the фонд, so
    # item_on_hand is now False and Кко drops to 0 (не обеспечено).
    circ.mark_lost(d.computed['loan']['id'], T0 + 100 * DAY, confirm=True,
                   override_grant=True)
    check('lost copy no longer on-hand in circulation',
          circ.item_on_hand(inv) is False)
    rep = bp.discipline_provision(disc)
    check('lost copy not counted as provisioned',
          rep['bindings'][0]['exemplars'] == 0)
    check('Кко drops to 0 after confirmed loss', rep['average_kko'] == 0.0)
    check('discipline under-provisioned after loss',
          rep['under_provisioned'] is True)


def bp_backcompat_checks():
    print('-- edge B back-compat: book-provision without circulation handle')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    inv = 'BP-BC'
    cat.save('IBIS', _book_with_copy(inv, EXEMPLAR_FREE))
    # No circulation handle: an issued copy reads as NOT provisioned (the original
    # free/not-free behaviour) — proving the new branch is opt-in.
    bp = BookProvisionEngine(catalog=cat)  # no circulation
    fac = bp.add_faculty('F1')
    spec = bp.add_specialty(fac, napr='09.03.01')
    disc = bp.add_discipline(spec, '3001', students=1)
    bp.bind_literature(disc, 'Алгоритмы', catalog_db='IBIS', inv_key=inv)
    check('free copy provisioned (no circ handle)',
          bp.discipline_provision(disc)['bindings'][0]['exemplars'] == 1)
    cat.set_exemplar_status('IBIS', inv, EXEMPLAR_ISSUED)
    check('issued copy NOT counted without circulation handle',
          bp.discipline_provision(disc)['bindings'][0]['exemplars'] == 0)


# --------------------------------------------------------------------------- #
# Edge C — Книговыдача → Комплектование (списание/утрата → КСУ выбытия).
#
# CirculationEngine получает опциональный ``acquisition`` handle. Подтверждённая
# утрата (mark_lost confirm=True) пишет проводку в КСУ выбытия комплектования
# (910^V № акта, 910^X кол-во), с кросс-ссылкой на КСУ поступления, если инв.№
# известен комплектованию.
# --------------------------------------------------------------------------- #
def circ_lost_to_acq_disposal_checks():
    print('-- edge C: подтверждённая утрата (circ) → КСУ выбытия (acq)')
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    acq = AcquisitionEngine(catalog=cat, catalog_db='IBIS')
    # Receive a copy first so acquisition KNOWS the inv.№ (cross-link to its КСУ
    # поступления).
    order = acq.create_order('Утрата', copies=1, price=500.0)
    inv = 'DISP-1'
    acq.receive(order['id'], 'KSU-RECV-9', 1, inv_numbers=[inv])

    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat,
                             catalog_db='IBIS', acquisition=acq)
    circ.store.add_reader('R1', category='В01')
    d = circ.checkout('R1', inv, T0)
    res = circ.mark_lost(d.computed['loan']['id'], T0 + 100 * DAY, confirm=True,
                         override_grant=True, ksu_disp_no='KSU-DISP-2026-1')

    # Invariant: a disposal row exists in acquisition's КСУ выбытия for the copy.
    check('mark_lost reports a disposal', res.computed.get('disposal') is not None)
    disp = res.computed['disposal']
    check('disposal keyed by the lost inv.№', disp['inv_no'] == inv)
    check('disposal booked under the акт списания',
          disp['ksu_disp_no'] == 'KSU-DISP-2026-1')
    check('disposal reason is lost', disp['reason'] == 'lost')
    # cross-link to the original КСУ поступления (inv.№ known to acquisition).
    check('disposal cross-links the КСУ поступления',
          disp['ksu_recv_no'] == 'KSU-RECV-9')
    check('disposal ref carries the loan id',
          disp['ref'] == str(d.computed['loan']['id']))

    # acquisition's выбытие rollup sees one copy written off.
    summ = acq.disposal_summary('KSU-DISP-2026-1')
    check('acq disposal summary counts 1 copy', summ['copies'] == 1)

    # Idempotent: re-confirming the same loss doesn't double the disposal row.
    circ.mark_lost(d.computed['loan']['id'], T0 + 100 * DAY, confirm=True,
                   override_grant=True, ksu_disp_no='KSU-DISP-2026-1')
    check('disposal stays idempotent on re-confirm',
          acq.disposal_summary('KSU-DISP-2026-1')['copies'] == 1)


def circ_lost_default_act_checks():
    print('-- edge C: default акт списания when none supplied')
    acq = AcquisitionEngine()  # standalone acquisition store
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), acquisition=acq)
    circ.store.add_reader('R1', category='В01')
    inv = 'DISP-DEF'
    d = circ.checkout('R1', inv, T0)
    res = circ.mark_lost(d.computed['loan']['id'], T0 + 100 * DAY, confirm=True,
                         override_grant=True)  # no ksu_disp_no
    disp = res.computed['disposal']
    check('default акт списания is LOST-<date>',
          disp['ksu_disp_no'].startswith('LOST-'))
    # inv.№ unknown to acquisition (no receipt) → no cross-link, still booked.
    check('disposal of unknown inv has no recv cross-link',
          disp['ksu_recv_no'] is None)
    check('disposal still records the copy', disp['inv_no'] == inv)


def circ_lost_backcompat_checks():
    print('-- edge C back-compat: circulation lost without acquisition handle')
    # No acquisition handle → mark_lost works exactly as before; no disposal key.
    circ = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy())  # no acquisition
    circ.store.add_reader('R1', category='В01')
    d = circ.checkout('R1', 'NOACQ-1', T0)
    res = circ.mark_lost(d.computed['loan']['id'], T0 + 100 * DAY, confirm=True,
                         override_grant=True)
    check('standalone mark_lost still ALLOW', res.decision == ALLOW)
    check('standalone mark_lost still charges replacement',
          res.computed.get('replacement_value') is not None)
    check('standalone mark_lost reports no disposal',
          'disposal' not in res.computed)
    # An unconfirmed candidate never writes a disposal even with a handle wired.
    acq = AcquisitionEngine()
    circ2 = CirculationEngine(store=CirculationStore(':memory:'),
                              policy=default_policy(), acquisition=acq)
    circ2.store.add_reader('R2', category='В01')
    d2 = circ2.checkout('R2', 'CAND-1', T0)
    res2 = circ2.mark_lost(d2.computed['loan']['id'], T0 + 100 * DAY,
                           confirm=False)  # candidate only
    check('lost_candidate writes no disposal', 'disposal' not in res2.computed)
    check('acq disposal ledger empty for unconfirmed candidate',
          acq.store.disposal_for_inv('CAND-1') == [])


def main():
    checkout_return_flip_checks()
    availability_read_checks()
    circulation_backcompat_checks()
    authority_on_save_checks()
    apply_authority_helper_checks()
    authority_backcompat_checks()
    combined_seam_checks()
    # Edge A — Комплектование → Книговыдача.
    acq_to_circulation_checks()
    acq_to_circulation_backcompat_checks()
    # Edge B — Книгообеспеченность → Книговыдача.
    bp_counts_issued_copies_checks()
    bp_lost_copy_not_counted_checks()
    bp_backcompat_checks()
    # Edge C — Книговыдача → Комплектование (КСУ выбытия).
    circ_lost_to_acq_disposal_checks()
    circ_lost_default_act_checks()
    circ_lost_backcompat_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
