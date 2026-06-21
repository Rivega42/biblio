#!/usr/bin/env python3
"""Book-provision engine tests (книгообеспеченность, ВУЗ — cluster 4, epic #188).

Scenario-based tests of the «связка» model + Кко computation + provision reports,
per docs/recon/deep/reference/databases/DB_VUZ.md §4/§5/§9 and
docs/design/specs/rules/SPEC_business_acquisition.md §2 (E1). Everything runs
against an in-memory store; the catalog read-through is exercised with a tiny
fake catalog handle and (separately) the real ``access.catalog.CatalogStore``.

Standalone-runnable in the house style of ``test_circulation.py``::

    py -3.12 tests/test_bookprovision.py   ->  ok ...  +  "N passed, M failed"  + exit

Covered (mirrors SPEC E1 AC3/AC4/AC6/AC7 + the task scenarios):
  * building the связка Факультет→Направление→Специальность→Дисциплина (idempotent);
  * binding literature to a discipline with a kind (основная/дополнительная);
  * the Кко computation incl. the 4-cell division-by-zero policy — the
    zero-contingent edges (students=0 ∧ exemplars>0 ⇒ 1; students=0 ∧
    exemplars=0 ⇒ NULL) and the zero-exemplar edge (students>0 ∧ exemplars=0 ⇒ 0);
  * average Кко excluding NULLs + normalize-to-1;
  * exemplar count read live from a wired catalog (910^A availability) and the
    standalone fallback to recorded copies;
  * per-discipline + per-specialty under-provision reports with shortfall.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import bookprovision as bp
from access.bookprovision import (
    BookProvisionEngine, BookProvisionError,
    KIND_MAIN, KIND_EXTRA, DEFAULT_KKO_NORM,
    kko, average_kko, shortfall,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def fresh(catalog=None, kko_norm=None):
    return BookProvisionEngine(':memory:', catalog=catalog, kko_norm=kko_norm)


def linkage(eng, students=100, source='68z'):
    """Build a one-discipline связка and return its ids."""
    fac = eng.add_faculty('ФВТ', name='Факультет вычислительной техники')
    sp = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                           vid='бакалавр', form='очная',
                           name='Информатика и ВТ')
    disc = eng.add_discipline(sp, disc_id='D-БД', name='Базы данных',
                              semester='3', students=students,
                              students_source=source)
    return fac, sp, disc


# --------------------------------------------------------------------------- #
# 1. Pure Кко math — the 4-cell division-by-zero policy (SPEC E1 §2.2, AC4).
# --------------------------------------------------------------------------- #
def kko_math_checks():
    print('-- Кко math: 4-cell div-by-zero policy')
    check('students>0, exemplars>0 -> exemplars/students',
          kko(40, 100) == 0.40)
    check('students>0, exemplars=0 -> 0 (не обеспечено)',
          kko(0, 100) == 0.0)
    check('students=0, exemplars>0 -> 1.0 (обеспечено)',
          kko(50, 0) == 1.0)
    check('students=0, exemplars=0 -> None (NULL, нет данных)',
          kko(0, 0) is None)
    # NULL is distinct from 0.0 — the crux of SPEC E1 §2.2 / AC4.
    check('NULL is not 0.0', kko(0, 0) is None and kko(0, 1) == 0.0)
    # defensive clamping of negatives
    check('negative inputs clamp to 0', kko(-5, 100) == 0.0)


def average_and_shortfall_checks():
    print('-- average Кко (NULL-excluding) + shortfall')
    # П2 (SPEC E1 §6): ККО₁=0.40, ККО₂=0.10 -> average 0.25
    check('average excludes nothing here -> 0.25',
          abs(average_kko([0.40, 0.10]) - 0.25) < 1e-9)
    # NULL excluded from the average
    check('NULL excluded from average',
          abs(average_kko([0.40, None, 0.10]) - 0.25) < 1e-9)
    check('all-NULL -> None', average_kko([None, None]) is None)
    # normalize: min(Кко_i, 1) caps over-provision
    check('normalize caps each term at 1',
          abs(average_kko([2.0, 0.0], normalize=True) - 0.5) < 1e-9)
    check('without normalize over-provision counts full',
          abs(average_kko([2.0, 0.0]) - 1.0) < 1e-9)
    # shortfall = ceil(students*norm) - exemplars, floored at 0 (SPEC E1 §2.6)
    check('shortfall ceil(100*0.5)-10 = 40', shortfall(10, 100, 0.5) == 40)
    check('shortfall at-norm = 0', shortfall(50, 100, 0.5) == 0)
    check('shortfall zero-contingent = 0', shortfall(0, 0, 0.5) == 0)


# --------------------------------------------------------------------------- #
# 2. Building the связка (Факультет→Направление→Специальность→Дисциплина).
# --------------------------------------------------------------------------- #
def linkage_build_checks():
    print('-- build связка + idempotency + validation')
    eng = fresh()
    fac, sp, disc = linkage(eng, students=100)
    check('faculty/specialty/discipline created', fac and sp and disc)

    d = eng.get_discipline(disc)
    check('discipline carries id (3^0)', d['disc_id'] == 'D-БД')
    check('discipline carries semester (^F)', d['semester'] == '3')
    check('discipline carries contingent', d['students'] == 100)

    # idempotent re-add returns the same ids (the связка is a set, not a bag)
    check('faculty add idempotent', eng.add_faculty('ФВТ') == fac)
    sp2 = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                            vid='бакалавр', form='очная')
    check('specialty add idempotent', sp2 == sp)
    disc2 = eng.add_discipline(sp, disc_id='D-БД', semester='3', students=120)
    check('discipline add idempotent (updates contingent)',
          disc2 == disc and eng.get_discipline(disc)['students'] == 120)

    # a different семестр is a different discipline-contingent row
    disc_s4 = eng.add_discipline(sp, disc_id='D-БД', semester='4', students=80)
    check('different semester -> different row', disc_s4 != disc)
    check('two disciplines under specialty',
          len(eng.list_disciplines(sp)) == 2)

    # validation: unknown parents / missing keys are rejected
    try:
        eng.add_specialty(99999)
        check('unknown faculty rejected', False)
    except BookProvisionError:
        check('unknown faculty rejected', True)
    try:
        eng.add_discipline(sp, disc_id='')
        check('empty disc_id rejected', False)
    except BookProvisionError:
        check('empty disc_id rejected', True)


# --------------------------------------------------------------------------- #
# 3. Binding literature to a discipline (field 691, kind 691^G).
# --------------------------------------------------------------------------- #
def binding_checks():
    print('-- bind literature (основная/дополнительная)')
    eng = fresh()
    _, _, disc = linkage(eng, students=100)
    b1 = eng.bind_literature(disc, 'Дейт. Введение в БД', kind=KIND_MAIN,
                             copies=40)
    b2 = eng.bind_literature(disc, 'Гарсиа-Молина. СУБД', kind=KIND_EXTRA,
                             copies=10)
    check('two bindings created', b1 and b2 and b1 != b2)
    binds = eng.list_bindings(disc)
    check('binding records kind осн/доп',
          {x['kind'] for x in binds} == {KIND_MAIN, KIND_EXTRA})
    check('binding records copies (standalone)',
          {x['copies'] for x in binds} == {40, 10})

    # validation: unknown discipline / bad kind
    try:
        eng.bind_literature(99999, 'X', copies=1)
        check('bind to unknown discipline rejected', False)
    except BookProvisionError:
        check('bind to unknown discipline rejected', True)
    try:
        eng.bind_literature(disc, 'X', kind='bogus', copies=1)
        check('bad kind rejected', False)
    except BookProvisionError:
        check('bad kind rejected', True)


# --------------------------------------------------------------------------- #
# 4. Per-discipline Кко report (standalone) — incl. the edge cells.
# --------------------------------------------------------------------------- #
def discipline_report_checks():
    print('-- per-discipline provision report (standalone copies)')
    eng = fresh()
    _, _, disc = linkage(eng, students=100)
    eng.bind_literature(disc, 'Книга 1', kind=KIND_MAIN, copies=40)   # Кко 0.40
    eng.bind_literature(disc, 'Книга 2', kind=KIND_EXTRA, copies=10)  # Кко 0.10
    rep = eng.discipline_provision(disc)
    kkos = sorted(b['kko'] for b in rep['bindings'])
    check('per-binding Кко = [0.10, 0.40]', kkos == [0.10, 0.40])
    check('average Кко = 0.25', abs(rep['average_kko'] - 0.25) < 1e-9)
    # norm is the strictest kind bound (основная 0.5 dominates доп 0.25)
    check('discipline norm = 0.5 (основная dominates)', rep['kko_norm'] == 0.5)
    check('under-provisioned (0.25 < 0.5)', rep['under_provisioned'] is True)
    # shortfall over the whole bound фонд: ceil(100*0.5) - (40+10) = 0
    check('shortfall over full фонд = 0 (total exemplars at norm)',
          rep['shortfall'] == 0)

    # well-provisioned discipline: 60 copies / 100 students = 0.60 >= 0.5
    eng2 = fresh()
    _, _, disc2 = linkage(eng2, students=100)
    eng2.bind_literature(disc2, 'Хорошая книга', kind=KIND_MAIN, copies=60)
    rep2 = eng2.discipline_provision(disc2)
    check('well-provisioned not flagged', rep2['under_provisioned'] is False)
    check('well-provisioned shortfall 0', rep2['shortfall'] == 0)


def edge_cell_report_checks():
    print('-- Кко edge cells through the report (zero-contingent / zero-exemplar)')
    # zero-contingent, exemplars present -> Кко 1.0 (обеспечено), NOT under-prov.
    eng = fresh()
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S')
    arch = eng.add_discipline(sp, disc_id='ARCH', name='Архивная',
                              semester='9', students=0)
    eng.bind_literature(arch, 'Старый учебник', kind=KIND_MAIN, copies=50)
    rep = eng.discipline_provision(arch)
    check('zero-contingent + exemplars -> Кко 1.0',
          rep['bindings'][0]['kko'] == 1.0)
    check('zero-contingent not under-provisioned (no consumers)',
          rep['under_provisioned'] is False)
    check('zero-contingent shortfall 0', rep['shortfall'] == 0)

    # orphan: zero-contingent AND zero-exemplar -> NULL, excluded from average
    orphan = eng.add_discipline(sp, disc_id='ORPH', name='Сирота',
                                semester='10', students=0)
    eng.bind_literature(orphan, 'Нет экземпляров', kind=KIND_MAIN, copies=0)
    rep_o = eng.discipline_provision(orphan)
    check('orphan binding Кко is NULL', rep_o['bindings'][0]['kko'] is None)
    check('orphan average_kko is None (all NULL excluded)',
          rep_o['average_kko'] is None)
    check('orphan not under-provisioned (no data, no consumers)',
          rep_o['under_provisioned'] is False)

    # zero-exemplar but with students -> Кко 0.0, flagged, shortfall = ceil(50*.5)
    eng3 = fresh()
    _, _, disc = linkage(eng3, students=50)
    eng3.bind_literature(disc, 'Без экземпляров', kind=KIND_MAIN, copies=0)
    rep3 = eng3.discipline_provision(disc)
    check('students>0 zero-exemplar -> Кко 0.0', rep3['bindings'][0]['kko'] == 0.0)
    check('students>0 zero-exemplar under-provisioned', rep3['under_provisioned'])
    check('shortfall ceil(50*0.5)-0 = 25', rep3['shortfall'] == 25)


# --------------------------------------------------------------------------- #
# 5. Catalog read-through — exemplars from 910 when a handle is wired.
# --------------------------------------------------------------------------- #
class _FakeCatalog:
    """Minimal read handle exposing the one method the engine reads."""
    def __init__(self, available):
        self._available = available  # {(db, key): bool}

    def is_available(self, db, key):
        return self._available.get((db, key), False)


def catalog_read_checks():
    print('-- exemplar count from a wired catalog (910^A)')
    cat = _FakeCatalog({('IBIS', 'INV-1'): True, ('IBIS', 'INV-2'): False})
    eng = fresh(catalog=cat)
    _, _, disc = linkage(eng, students=1)
    # bound to a FREE holding -> counts as 1 available exemplar (Кко 1.0)
    eng.bind_literature(disc, 'Свободный', kind=KIND_MAIN,
                        catalog_db='IBIS', inv_key='INV-1', copies=0)
    # bound to an ISSUED holding -> counts as 0 available (Кко 0.0)
    eng.bind_literature(disc, 'Выданный', kind=KIND_MAIN,
                        catalog_db='IBIS', inv_key='INV-2', copies=99)
    rep = eng.discipline_provision(disc)
    by_title = {b['title']: b for b in rep['bindings']}
    check('free holding -> 1 exemplar from catalog',
          by_title['Свободный']['exemplars'] == 1)
    check('issued holding -> 0 exemplars (ignores inline copies)',
          by_title['Выданный']['exemplars'] == 0)

    # standalone (no catalog) uses the recorded copies even with an inv_key
    eng_s = fresh(catalog=None)
    _, _, d_s = linkage(eng_s, students=1)
    eng_s.bind_literature(d_s, 'Оффлайн', kind=KIND_MAIN,
                          catalog_db='IBIS', inv_key='INV-1', copies=7)
    rep_s = eng_s.discipline_provision(d_s)
    check('standalone falls back to recorded copies',
          rep_s['bindings'][0]['exemplars'] == 7)


def real_catalog_read_checks():
    print('-- exemplar count from the real CatalogStore (910^A)')
    try:
        from access.catalog import CatalogStore, EXEMPLAR_FREE, EXEMPLAR_ISSUED
    except Exception as e:  # pragma: no cover - catalog should import
        check('real catalog importable (skipped: %s)' % e, False)
        return
    cat = CatalogStore(':memory:')
    # a record with two copies: INV-A free, INV-B issued. 920 (worklist code) is
    # ФЛК-mandatory; 101 (language) keeps the brief format happy.
    res = cat.save('IBIS', {
        '200': [{'a': 'Учебник по БД'}],
        '101': 'rus',
        '920': 'PAZK',
        '910': [{'a': EXEMPLAR_FREE, 'b': 'INV-A'},
                {'a': EXEMPLAR_ISSUED, 'b': 'INV-B'}],
    })
    check('real catalog record saved (ФЛК passed)', res['saved'] is True)
    eng = fresh(catalog=cat)
    _, _, disc = linkage(eng, students=1)
    eng.bind_literature(disc, 'Свободный экз.', kind=KIND_MAIN,
                        catalog_db='IBIS', inv_key='INV-A', copies=0)
    eng.bind_literature(disc, 'Выданный экз.', kind=KIND_MAIN,
                        catalog_db='IBIS', inv_key='INV-B', copies=0)
    rep = eng.discipline_provision(disc)
    by_title = {b['title']: b for b in rep['bindings']}
    check('real catalog: free 910^A -> 1 exemplar',
          by_title['Свободный экз.']['exemplars'] == 1)
    check('real catalog: issued 910^A -> 0 exemplars',
          by_title['Выданный экз.']['exemplars'] == 0)


# --------------------------------------------------------------------------- #
# 6. Per-specialty rollup + under-provision listing.
# --------------------------------------------------------------------------- #
def specialty_report_checks():
    print('-- per-specialty provision summary (under-provision list)')
    eng = fresh()
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S')
    # D1 under-provisioned: 10 copies / 100 students = 0.10 < 0.5
    d1 = eng.add_discipline(sp, disc_id='D1', name='Слабая', semester='1',
                            students=100)
    eng.bind_literature(d1, 'Мало книг', kind=KIND_MAIN, copies=10)
    # D2 well-provisioned: 80 copies / 100 students = 0.80 >= 0.5
    d2 = eng.add_discipline(sp, disc_id='D2', name='Сильная', semester='1',
                            students=100)
    eng.bind_literature(d2, 'Много книг', kind=KIND_MAIN, copies=80)
    # D3 archival (students=0, copies>0) -> Кко 1.0, NOT under-provisioned
    d3 = eng.add_discipline(sp, disc_id='D3', name='Архив', semester='9',
                            students=0)
    eng.bind_literature(d3, 'Старьё', kind=KIND_MAIN, copies=30)

    rep = eng.specialty_provision(sp)
    check('rollup covers all 3 disciplines', len(rep['disciplines']) == 3)
    under_ids = {u['disc_id'] for u in rep['under_provisioned']}
    check('only D1 under-provisioned', under_ids == {'D1'})
    d1_under = next(u for u in rep['under_provisioned'] if u['disc_id'] == 'D1')
    check('D1 shortfall ceil(100*0.5)-10 = 40', d1_under['shortfall'] == 40)
    check('specialty total_shortfall = 40', rep['total_shortfall'] == 40)
    # specialty average excludes nothing NULL here: mean(0.10, 0.80, 1.0)
    check('specialty average_kko = mean of discipline averages',
          abs(rep['average_kko'] - (0.10 + 0.80 + 1.0) / 3) < 1e-9)

    # unknown specialty rejected
    try:
        eng.specialty_provision(99999)
        check('unknown specialty rejected', False)
    except BookProvisionError:
        check('unknown specialty rejected', True)


def norm_per_kind_checks():
    print('-- per-kind norm + tenant isolation of norms')
    # дополнительная-only discipline uses the laxer norm 0.25
    eng = fresh()
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S')
    d = eng.add_discipline(sp, disc_id='D', students=100)
    eng.bind_literature(d, 'Доп. книга', kind=KIND_EXTRA, copies=30)  # 0.30
    rep = eng.discipline_provision(d)
    check('доп-only norm = 0.25', rep['kko_norm'] == 0.25)
    check('0.30 >= 0.25 -> not under-provisioned',
          rep['under_provisioned'] is False)

    # per-tenant norm override + isolation (a mutation never leaks)
    eng_strict = fresh(kko_norm={'main': 1.0, 'extra': 1.0})
    _, _, ds = linkage(eng_strict, students=10)
    eng_strict.bind_literature(ds, 'Книга', kind=KIND_MAIN, copies=5)  # 0.5
    rep_s = eng_strict.discipline_provision(ds)
    check('strict tenant norm 1.0 flags 0.5', rep_s['under_provisioned'] is True)
    check('default norm table not mutated', DEFAULT_KKO_NORM[KIND_MAIN] == 0.5)


def main():
    kko_math_checks()
    average_and_shortfall_checks()
    linkage_build_checks()
    binding_checks()
    discipline_report_checks()
    edge_cell_report_checks()
    catalog_read_checks()
    real_catalog_read_checks()
    specialty_report_checks()
    norm_per_kind_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
