#!/usr/bin/env python3
"""ККО aggregate + Move691/архив-692 tests (книгообеспеченность, ВУЗ — cluster 4).

Covers the cluster-4 seams landed on top of the standalone book-provision engine
(``access/bookprovision.py``), per ``docs/design/INTEGRATION_MAP.md`` cluster 4
(рёбра 4.1/4.4/4.5) and ``docs/recon/deep/reference/databases/DB_VUZ.md`` §6.2/§6.3
(формула ККО, поле 691) / §6.4 (архив 692):

  * **ребро 4.4 (полный агрегат ККО).** ``Кко = экземпляры/студенты``; the full
    cross-БД свод IBIS(экз)xRDR(студенты) — students from RDR by связка
    (``ACCESSRDR=1``) через опц. ``rdr`` handle, else поле ``68^Z``
    (``ACCESSRDR=0``); exemplars include on-hand-loaned copies (фонд, не полка);
    Sumэкз/Sumстуд + границы (деление на 0, NULL «нет данных»).
  * **ребро 4.1 (Move691).** связка контингента (68/83 ``^A^L^N^C^V^O^F``) ->
    каталог поле **691** (``691^I=<3^0>`` + ``^G`` тип лит.), через catalog handle;
    идемпотентность; разрешение mfn по ``910^b``.
  * **ребро 4.5 (архив 692).** снятая привязка 691 -> архивное поле **692**.
  * **back-compat.** без ``rdr`` handle -> 68^Z; без ``catalog`` handle ->
    Move691/archive691 поднимают ошибку, а ККО — standalone copies.

Runs against in-memory stores; Move691/архив-692 use the REAL
``access.catalog.CatalogStore`` (the genuine handle, round-tripped through
ФЛК/save) so the seam is exercised end-to-end. The catalog store carries its own
sqlite<->PG parity (tested in test_catalog/test_circulation); here we additionally
assert the bookprovision sqlite<->PG schema parity файл carries the new ``^L`` column.

Standalone-runnable in the house style::

    py -3.12 tests/test_ko.py   ->  ok ...  +  "N passed, M failed"  + exit
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.bookprovision import (
    BookProvisionEngine, BookProvisionError,
    KIND_MAIN, KIND_EXTRA,
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


def fresh(catalog=None, rdr=None, circulation=None, kko_norm=None):
    return BookProvisionEngine(':memory:', catalog=catalog, rdr=rdr,
                               circulation=circulation, kko_norm=kko_norm)


def linkage(eng, students=100, source='68z', fili=''):
    """Build a one-discipline связка (Фак-Напр-Спец-ВО-ФО-Сем) and return its ids."""
    fac = eng.add_faculty('ФВТ', name='Факультет вычислительной техники')
    sp = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                           vid='бакалавр', form='очная', fili=fili,
                           name='Информатика и ВТ')
    disc = eng.add_discipline(sp, disc_id='D-БД', name='Базы данных',
                              semester='3', students=students,
                              students_source=source)
    return fac, sp, disc


# --------------------------------------------------------------------------- #
# Fakes (FakeIrbis-style synthetic handles — read-only, duck-typed).
# --------------------------------------------------------------------------- #
class _FakeRdr:
    """Read-only RDR handle: counts students by связка (ACCESSRDR=1 path).

    ``by`` maps a связка tuple (A,L,N,C,V,O,F) -> student count. A связка absent
    from the map returns None (no opinion) so the engine falls back to 68^Z."""
    def __init__(self, by):
        self._by = by

    def count_students(self, linkage):
        key = (linkage.get('A', ''), linkage.get('L', ''), linkage.get('N', ''),
               linkage.get('C', ''), linkage.get('V', ''), linkage.get('O', ''),
               linkage.get('F', ''))
        return self._by.get(key)


class _FakeCirc:
    """Read-only circulation handle: which inventory keys are on an on-hand loan."""
    def __init__(self, on_hand):
        self._on_hand = set(on_hand)

    def item_on_hand(self, inv_key):
        return inv_key in self._on_hand


def _real_catalog():
    """A real CatalogStore (the genuine handle) or None if unimportable."""
    try:
        from access.catalog import CatalogStore
        return CatalogStore(':memory:')
    except Exception:
        return None


def _save_book(cat, db, title, exemplars):
    """Save a catalog record with copies = [(inv_key, status), ...]. Returns mfn.

    920 (worklist) is ФЛК-mandatory; 101 keeps the brief format happy."""
    from access.catalog import EXEMPLAR_FREE
    res = cat.save(db, {
        '200': [{'a': title}],
        '101': 'rus',
        '920': 'PAZK',
        '910': [{'a': status, 'b': key} for key, status in exemplars]
        or [{'a': EXEMPLAR_FREE, 'b': 'X'}],
    })
    assert res['saved'], 'fixture book must save (ФЛК): %r' % res
    return res['mfn']


# --------------------------------------------------------------------------- #
# 1. ребро 4.4 — full ККО aggregate: students from RDR by связка vs 68^Z.
# --------------------------------------------------------------------------- #
def students_source_checks():
    print('-- ККО: студенты из RDR по связке (ACCESSRDR=1) vs 68^Z (ACCESSRDR=0)')

    # 68^Z fallback (no rdr handle) — the recorded contingent is used.
    eng = fresh()
    _, _, disc = linkage(eng, students=100)
    eng.bind_literature(disc, 'Книга', kind=KIND_MAIN, copies=40)
    rep = eng.discipline_provision(disc)
    check('68^Z: students=100 from inline count', rep['students'] == 100)
    check('68^Z: source reported 68z', rep['students_source'] == '68z')
    check('68^Z: Кко 40/100 = 0.40', abs(rep['average_kko'] - 0.40) < 1e-9)

    # RDR by связка overrides the inline 68^Z when the handle has an opinion.
    rdr = _FakeRdr({('ФВТ', '', '09.03.01', 'АСОИУ', 'бакалавр', 'очная', '3'): 80})
    eng2 = fresh(rdr=rdr)
    _, _, disc2 = linkage(eng2, students=100)   # 68^Z says 100…
    eng2.bind_literature(disc2, 'Книга', kind=KIND_MAIN, copies=40)
    rep2 = eng2.discipline_provision(disc2)
    check('RDR: students=80 from RDR (overrides 68^Z 100)', rep2['students'] == 80)
    check('RDR: source reported rdr', rep2['students_source'] == 'rdr')
    check('RDR: Кко 40/80 = 0.50', abs(rep2['average_kko'] - 0.50) < 1e-9)

    # RDR with no opinion for this связка -> falls back to 68^Z.
    rdr_empty = _FakeRdr({('OTHER', '', '', '', '', '', ''): 5})
    eng3 = fresh(rdr=rdr_empty)
    _, _, disc3 = linkage(eng3, students=100)
    eng3.bind_literature(disc3, 'Книга', kind=KIND_MAIN, copies=40)
    rep3 = eng3.discipline_provision(disc3)
    check('RDR no-opinion -> 68^Z fallback (100, 68z)',
          rep3['students'] == 100 and rep3['students_source'] == '68z')

    # RDR handle that errors -> degrades to 68^Z (never crashes).
    class _Boom:
        def count_students(self, linkage):
            raise RuntimeError('rdr down')
    eng4 = fresh(rdr=_Boom())
    _, _, disc4 = linkage(eng4, students=100)
    eng4.bind_literature(disc4, 'Книга', kind=KIND_MAIN, copies=40)
    rep4 = eng4.discipline_provision(disc4)
    check('RDR error -> 68^Z fallback (no crash)',
          rep4['students'] == 100 and rep4['students_source'] == '68z')


def aggregate_checks():
    print('-- ККО: полный кросс-БД агрегат Sumэкз/Sumстуд + average + границы')
    # Two disciplines under one specialty/faculty, each one binding (so the
    # per-discipline average_kko == that binding's Кко — clean to assert). The
    # фонд-weighted aggregate_kko (Sumэкз/Sumстуд) is DISTINCT from the
    # discipline-mean average_kko, which is the whole point of reporting both.
    eng = fresh()
    fac = eng.add_faculty('ФВТ')
    sp = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                           vid='бакалавр', form='очная')
    # D1: 60 копий / 100 студ -> Кко 0.60 (обеспечена).
    d1 = eng.add_discipline(sp, disc_id='D1', name='Сильная', semester='1',
                            students=100)
    eng.bind_literature(d1, 'Много книг', kind=KIND_MAIN, copies=60)
    # D2: 20 копий / 200 студ -> Кко 0.10 (не обеспечена).
    d2 = eng.add_discipline(sp, disc_id='D2', name='Слабая', semester='1',
                            students=200)
    eng.bind_literature(d2, 'Мало книг', kind=KIND_MAIN, copies=20)

    agg = eng.provision_aggregate(specialty_id=sp)
    check('aggregate scope = specialty', agg['scope'] == 'specialty')
    check('aggregate total_exemplars = 60+20 = 80', agg['total_exemplars'] == 80)
    check('aggregate total_students = 100+200 = 300', agg['total_students'] == 300)
    # Sumэкз/Sumстуд = 80/300 (фонд-weighted aggregate).
    check('aggregate_kko = Sumэкз/Sumстуд = 80/300',
          abs(agg['aggregate_kko'] - 80 / 300) < 1e-9)
    # average over disciplines = mean(0.60, 0.10) = 0.35 (distinct from weighted).
    check('average_kko = mean(0.60, 0.10) = 0.35',
          abs(agg['average_kko'] - 0.35) < 1e-9)
    check('aggregate_kko distinct from average_kko (weighted vs mean)',
          abs(agg['aggregate_kko'] - agg['average_kko']) > 1e-3)
    # D2 (0.10 < 0.5) under-provisioned; D1 (0.60) is not.
    under_ids = {u['disc_id'] for u in agg['under_provisioned']}
    check('only D2 under-provisioned', under_ids == {'D2'})
    # D2 shortfall ceil(200*0.5) - 20 = 80; D1 none -> total 80.
    check('aggregate total_shortfall = 80', agg['total_shortfall'] == 80)
    check('students_sources counts 2x 68z', agg['students_sources']['68z'] == 2)

    # faculty scope sees both disciplines too.
    agg_f = eng.provision_aggregate(faculty_id=fac)
    check('faculty scope covers both disciplines',
          agg_f['total_disciplines'] == 2 and agg_f['total_exemplars'] == 80)
    # tenant scope (no filter) also covers them.
    agg_t = eng.provision_aggregate()
    check('tenant scope = both disciplines', agg_t['total_disciplines'] == 2)

    # RDR-sourced aggregate: students come from RDR by связка (ACCESSRDR=1).
    rdr = _FakeRdr({
        ('ФВТ', '', '09.03.01', 'АСОИУ', 'бакалавр', 'очная', '1'): 50,
    })
    eng_r = fresh(rdr=rdr)
    facr = eng_r.add_faculty('ФВТ')
    spr = eng_r.add_specialty(facr, napr='09.03.01', spec='АСОИУ',
                              vid='бакалавр', form='очная')
    dr = eng_r.add_discipline(spr, disc_id='D1', semester='1', students=999)
    eng_r.bind_literature(dr, 'кн', kind=KIND_MAIN, copies=25)  # 25/50 = 0.5
    agg_r = eng_r.provision_aggregate(specialty_id=spr)
    check('RDR aggregate uses RDR students (50, not 68^Z 999)',
          agg_r['total_students'] == 50)
    check('RDR aggregate_kko = 25/50 = 0.5',
          abs(agg_r['aggregate_kko'] - 0.5) < 1e-9)
    check('RDR aggregate students_sources counts rdr',
          agg_r['students_sources']['rdr'] == 1)


def aggregate_boundary_checks():
    print('-- ККО агрегат: границы (нет студентов -> NULL, деление на 0)')
    eng = fresh()
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S')
    # Only an archival zero-contingent discipline -> Sumстуд=0 -> aggregate NULL.
    arch = eng.add_discipline(sp, disc_id='ARCH', semester='9', students=0)
    eng.bind_literature(arch, 'Старьё', kind=KIND_MAIN, copies=30)
    agg = eng.provision_aggregate(specialty_id=sp)
    check('Sumстуд=0 -> aggregate_kko None (NULL «нет данных», no div-by-0)',
          agg['aggregate_kko'] is None)
    check('zero-contingent not under-provisioned in aggregate',
          agg['under_provisioned'] == [])
    check('total_students=0', agg['total_students'] == 0)

    # empty scope (no disciplines) -> aggregate None, zero totals.
    sp2 = eng.add_specialty(fac, napr='N2', spec='S2')
    agg2 = eng.provision_aggregate(specialty_id=sp2)
    check('empty scope -> aggregate_kko None', agg2['aggregate_kko'] is None)
    check('empty scope -> 0 disciplines', agg2['total_disciplines'] == 0)

    # unknown scope rejected.
    try:
        eng.provision_aggregate(specialty_id=99999)
        check('unknown specialty scope rejected', False)
    except BookProvisionError:
        check('unknown specialty scope rejected', True)
    try:
        eng.provision_aggregate(faculty_id=99999)
        check('unknown faculty scope rejected', False)
    except BookProvisionError:
        check('unknown faculty scope rejected', True)


def aggregate_onhand_checks():
    print('-- ККО агрегат: выданный на руки экз остаётся в фонде (ребро 4.4/4.7)')
    cat = _real_catalog()
    if cat is None:
        check('real catalog importable', False)
        return
    from access.catalog import EXEMPLAR_ISSUED
    db = 'IBIS'
    # One issued copy; circulation says it is on an on-hand loan -> still фонд.
    _save_book(cat, db, 'Выданная', [('INV-OUT', EXEMPLAR_ISSUED)])
    circ = _FakeCirc(on_hand={'INV-OUT'})
    eng = fresh(catalog=cat, circulation=circ)
    _, _, disc = linkage(eng, students=1)
    eng.bind_literature(disc, 'Выданная', kind=KIND_MAIN,
                        catalog_db=db, inv_key='INV-OUT')
    rep = eng.discipline_provision(disc)
    check('issued-but-on-hand counts as 1 provisioned exemplar',
          rep['bindings'][0]['exemplars'] == 1)
    agg = eng.provision_aggregate()
    check('aggregate counts on-hand copy in Sumэкз',
          agg['total_exemplars'] == 1)

    # Without the circulation handle the same issued copy reads 0 (back-compat).
    eng_nc = fresh(catalog=cat)
    _, _, d2 = linkage(eng_nc, students=1)
    eng_nc.bind_literature(d2, 'Выданная', kind=KIND_MAIN,
                           catalog_db=db, inv_key='INV-OUT')
    rep_nc = eng_nc.discipline_provision(d2)
    check('no circulation handle -> issued copy reads 0 (back-compat)',
          rep_nc['bindings'][0]['exemplars'] == 0)


# --------------------------------------------------------------------------- #
# 2. ребро 4.1 — Move691: связка -> каталог поле 691.
# --------------------------------------------------------------------------- #
def move691_checks():
    print('-- Move691: связка контингента -> каталог поле 691 (^I + ^A^L^N^C^V^O^F)')
    cat = _real_catalog()
    if cat is None:
        check('real catalog importable', False)
        return
    db = 'IBIS'
    mfn = _save_book(cat, db, 'Учебник по БД', [('INV-1', '0')])

    eng = fresh(catalog=cat)
    fac = eng.add_faculty('ФВТ')
    sp = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                           vid='бакалавр', form='очная', fili='СПб')
    disc = eng.add_discipline(sp, disc_id='D-БД', name='Базы данных',
                              semester='3', students=100)
    eng.bind_literature(disc, 'Учебник по БД', kind=KIND_MAIN,
                        catalog_db=db, inv_key='INV-1')

    res = eng.move691(disc)
    check('move691 touched 1 record', len(res) == 1 and res[0]['mfn'] == mfn)
    check('move691 reports created (not replaced)', res[0]['created'] is True)

    rec = cat.get(db, mfn)
    insts = rec.get('691')
    insts = insts if isinstance(insts, list) else [insts]
    check('caталог record now carries a 691', len(insts) == 1)
    f691 = insts[0]
    # ^I = id дисциплины (3^0).
    check('691^I = disc_id (3^0)', f691.get('I') == 'D-БД')
    # связка ^A^L^N^C^V^O^F all present and correct.
    check('691^A = факультет', f691.get('A') == 'ФВТ')
    check('691^L = филиал', f691.get('L') == 'СПб')
    check('691^N = направление', f691.get('N') == '09.03.01')
    check('691^C = специальность', f691.get('C') == 'АСОИУ')
    check('691^V = вид', f691.get('V') == 'бакалавр')
    check('691^O = форма', f691.get('O') == 'очная')
    check('691^F = семестр', f691.get('F') == '3')
    # ^G = тип лит. основная (691G.MNU: Осн).
    check('691^G = Осн (основная)', f691.get('G') == 'Осн')

    # idempotent: a second move691 updates in place, does NOT duplicate the 691.
    res2 = eng.move691(disc)
    check('second move691 reports replaced (idempotent)',
          res2[0]['created'] is False)
    rec2 = cat.get(db, mfn)
    insts2 = rec2.get('691')
    insts2 = insts2 if isinstance(insts2, list) else [insts2]
    check('still exactly one 691 (no duplicate)', len(insts2) == 1)

    # the 910 holding survives the round-trip (we only touched 691).
    holds = rec2.get('910')
    holds = holds if isinstance(holds, list) else [holds]
    check('910 holding preserved through move691', holds[0].get('b') == 'INV-1')


def move691_explicit_mfn_checks():
    print('-- Move691: explicit mfn target (no inv_key resolution)')
    cat = _real_catalog()
    if cat is None:
        check('real catalog importable', False)
        return
    db = 'IBIS'
    mfn = _save_book(cat, db, 'Книга без экз.привязки', [('Z-1', '0')])
    eng = fresh(catalog=cat)
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S', vid='бак', form='оч')
    disc = eng.add_discipline(sp, disc_id='DX', semester='2', students=10)
    # No bound holdings — drive Move691 by explicit mfn.
    res = eng.move691(disc, catalog_db=db, mfn=mfn)
    check('explicit-mfn move691 touched the record', res[0]['mfn'] == mfn)
    rec = cat.get(db, mfn)
    insts = rec.get('691')
    insts = insts if isinstance(insts, list) else [insts]
    check('691^I written for explicit mfn', insts[0].get('I') == 'DX')
    check('691 omits empty ^L (single-campus)', 'L' not in insts[0])
    check('691^G defaults to Осн (no bound kind)', insts[0].get('G') == 'Осн')


def move691_backcompat_checks():
    print('-- Move691/archive691: без catalog handle -> ошибка (нечего трогать)')
    eng = fresh(catalog=None)
    _, _, disc = linkage(eng, students=10)
    try:
        eng.move691(disc)
        check('move691 without catalog handle raises', False)
    except BookProvisionError:
        check('move691 without catalog handle raises', True)
    try:
        eng.archive691(disc, 'IBIS', 1)
        check('archive691 without catalog handle raises', False)
    except BookProvisionError:
        check('archive691 without catalog handle raises', True)

    # no resolvable target (no inv_key, no mfn) -> raises.
    cat = _real_catalog()
    if cat is not None:
        eng2 = fresh(catalog=cat)
        fac = eng2.add_faculty('Ф')
        sp = eng2.add_specialty(fac, napr='N', spec='S')
        d = eng2.add_discipline(sp, disc_id='D', semester='1', students=5)
        eng2.bind_literature(d, 'Без ключа', kind=KIND_MAIN, copies=3)  # no inv_key
        try:
            eng2.move691(d)
            check('move691 with no resolvable target raises', False)
        except BookProvisionError:
            check('move691 with no resolvable target raises', True)


# --------------------------------------------------------------------------- #
# 3. ребро 4.5 — архив 692: снятая привязка 691 -> поле 692.
# --------------------------------------------------------------------------- #
def archive692_checks():
    print('-- архив 692: снятая привязка 691 -> архивное поле 692')
    cat = _real_catalog()
    if cat is None:
        check('real catalog importable', False)
        return
    db = 'IBIS'
    mfn = _save_book(cat, db, 'Учебник', [('INV-1', '0')])
    eng = fresh(catalog=cat)
    fac = eng.add_faculty('ФВТ')
    sp = eng.add_specialty(fac, napr='09.03.01', spec='АСОИУ',
                           vid='бакалавр', form='очная')
    disc = eng.add_discipline(sp, disc_id='D-БД', semester='3', students=100)
    eng.bind_literature(disc, 'Учебник', kind=KIND_MAIN,
                        catalog_db=db, inv_key='INV-1')
    eng.move691(disc)
    # sanity: 691 present, no 692 yet.
    rec = cat.get(db, mfn)
    check('precondition: 691 present', '691' in rec)
    check('precondition: no 692 yet', not rec.get('692'))

    moved = eng.archive691(disc, db, mfn)
    check('archive691 returns True (one binding moved)', moved is True)
    rec2 = cat.get(db, mfn)
    rem = rec2.get('691')
    rem = rem if isinstance(rem, list) else ([rem] if rem else [])
    check('691 binding removed (none left for this disc)',
          all(x.get('I') != 'D-БД' for x in rem))
    arch = rec2.get('692')
    arch = arch if isinstance(arch, list) else ([arch] if arch else [])
    check('692 archive now carries the binding', len(arch) == 1)
    check('archived 692 keeps ^I + связка',
          arch[0].get('I') == 'D-БД' and arch[0].get('A') == 'ФВТ'
          and arch[0].get('N') == '09.03.01')

    # archiving again is a no-op (nothing matches now).
    moved2 = eng.archive691(disc, db, mfn)
    check('second archive691 is a no-op (False)', moved2 is False)
    rec3 = cat.get(db, mfn)
    arch3 = rec3.get('692')
    arch3 = arch3 if isinstance(arch3, list) else ([arch3] if arch3 else [])
    check('no duplicate archive entry', len(arch3) == 1)

    # unknown record / discipline rejected.
    try:
        eng.archive691(disc, db, 999999)
        check('archive691 unknown mfn raises', False)
    except BookProvisionError:
        check('archive691 unknown mfn raises', True)
    try:
        eng.archive691(999999, db, mfn)
        check('archive691 unknown discipline raises', False)
    except BookProvisionError:
        check('archive691 unknown discipline raises', True)


def move_archive_roundtrip_checks():
    print('-- Move691->archive691: preserve unrelated 691 of другой дисциплины')
    cat = _real_catalog()
    if cat is None:
        check('real catalog importable', False)
        return
    db = 'IBIS'
    mfn = _save_book(cat, db, 'Многодисциплинарный учебник', [('INV-9', '0')])
    eng = fresh(catalog=cat)
    fac = eng.add_faculty('Ф')
    sp = eng.add_specialty(fac, napr='N', spec='S', vid='б', form='о')
    dA = eng.add_discipline(sp, disc_id='DA', semester='1', students=10)
    dB = eng.add_discipline(sp, disc_id='DB', semester='2', students=20)
    eng.bind_literature(dA, 'кн', kind=KIND_MAIN, catalog_db=db, inv_key='INV-9')
    eng.bind_literature(dB, 'кн', kind=KIND_EXTRA, catalog_db=db, inv_key='INV-9')
    eng.move691(dA, catalog_db=db, mfn=mfn)
    eng.move691(dB, catalog_db=db, mfn=mfn)
    rec = cat.get(db, mfn)
    insts = rec.get('691')
    insts = insts if isinstance(insts, list) else [insts]
    check('two 691 bindings (DA + DB)', len(insts) == 2)
    check('DB bound as доп (^G=Доп)',
          any(x.get('I') == 'DB' and x.get('G') == 'Доп' for x in insts))

    # archive only DA -> DB survives in 691, DA lands in 692.
    eng.archive691(dA, db, mfn)
    rec2 = cat.get(db, mfn)
    rem = rec2.get('691')
    rem = rem if isinstance(rem, list) else [rem]
    check('DB still in 691 after archiving DA',
          [x.get('I') for x in rem] == ['DB'])
    arch = rec2.get('692')
    arch = arch if isinstance(arch, list) else [arch]
    check('DA in 692 archive', arch[0].get('I') == 'DA')


# --------------------------------------------------------------------------- #
# 4. PG-parity of the bp schema (the ^L column carried into the PG DDL file).
# --------------------------------------------------------------------------- #
def pg_parity_checks():
    print('-- PG-паритет: схема bp_specialty несёт ^L (fili) в обоих DDL')
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql = open(os.path.join(here, 'access', 'schema_bookprovision.sql'),
               encoding='utf-8').read()
    check('PG DDL bp_specialty has fili column',
          re.search(r'\bfili\b\s+TEXT', sql) is not None)
    check('PG DDL UNIQUE includes fili',
          re.search(r'UNIQUE \([^)]*\bfili\b[^)]*\)', sql) is not None)
    # the sqlite schema (engine source) also carries fili (sqlite<->PG parity).
    from access import bookprovision as bp
    check('sqlite schema has fili column', 'fili TEXT' in bp.SCHEMA_SQLITE)


def main():
    students_source_checks()
    aggregate_checks()
    aggregate_boundary_checks()
    aggregate_onhand_checks()
    move691_checks()
    move691_explicit_mfn_checks()
    move691_backcompat_checks()
    archive692_checks()
    move_archive_roundtrip_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
