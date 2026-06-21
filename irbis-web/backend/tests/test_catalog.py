#!/usr/bin/env python3
"""Bibliographic catalog store + CRUD tests (catalog gap, epic #188).

Covers the first shippable slice of ``access/catalog.py`` — the record store that
ties the landed engines together (ФЛК A2 on save, PFT A1 for display), layered on
the A5 vocabulary seeding so dictionary ФЛК rules resolve.

Standalone-runnable, mirroring the house style of tests/test_flk.py /
tests/test_pft.py / tests/test_seeding.py::

    py -3.12 tests/test_catalog.py   ->  'ok …' lines + 'N passed, M failed', exit!=0

What is exercised
  1. Schema / store init: tables created on a fresh :memory: store.
  2. save valid record -> get returns it byte-for-byte; mfn assigned sequentially.
  3. save with missing mandatory 200^a (non-аналитика) -> rejected with a
     severity-1 violation (ФЛК A2 wired); nothing written.
  4. save with only a soft (severity-2) violation -> still saved, warning surfaced.
  5. search by T= (title) and A= (author) finds the saved record; K=/IN= index.
  6. logical delete hides the record from search and get; undelete restores it.
  7. brief / full render via PFT (A1) produce non-empty strings; bare-prefix and
     case-insensitive search; index_terms / parse_expr units.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import flk
from access import seed_vocab
from access.catalog import CatalogStore, parse_expr, SEARCH_PREFIXES
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


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #
def _seeded_access_store():
    """An in-memory Access store seeded with A5 system vocabs (jz/vd/...), so the
    ФЛК language/worklist dictionary rules can resolve. Without it those rules
    no-op (the engine never fabricates a violation it can't substantiate)."""
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


def _store():
    return CatalogStore(':memory:', access_store=_seeded_access_store())


# A clean, valid book record (passes the full ФЛК save run):
# 920 worklist + title + valid language + executor.
def _good_book():
    return {
        '920': 'PAZK',
        '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.'}],
        '700': [{'a': 'Петров П.П.'}],
        '610': [{'': 'каталогизация'}, {'': 'библиография'}],
        '101': 'rus',
        '910': [{'a': '0', 'b': '1024365'}],
        '907': [{'a': 'Сидорова С.С.'}],
    }


# --------------------------------------------------------------------------- #
# 1. Store init / schema.
# --------------------------------------------------------------------------- #
def schema_checks():
    print('-- schema / init')
    st = _store()
    names = {r[0] for r in st._conn().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check('record table created', 'record' in names)
    check('record_index table created', 'record_index' in names)
    check('fresh store empty', st.count('IBIS') == 0)


# --------------------------------------------------------------------------- #
# 2. save valid -> get round-trips; sequential mfn.
# --------------------------------------------------------------------------- #
def save_get_checks():
    print('-- save (valid) / get')
    st = _store()
    rec = _good_book()
    res = st.save('IBIS', rec)
    check('valid record saved (saved True)', res['saved'] is True)
    check('valid record canSave', res['canSave'] is True)
    check('valid record assigned mfn 1', res['mfn'] == 1)
    check('valid record has a row id', isinstance(res['id'], int) and res['id'] > 0)
    check('valid record overallSeverity is PASS', res['overallSeverity'] == flk.SEV_PASS)

    got = st.get('IBIS', 1)
    check('get returns the stored record', got == rec)
    check('get returns title intact', got['200'][0]['a'] == 'Основы каталогизации')

    # second save -> mfn 2 (sequential per db); a different db restarts at 1.
    res2 = st.save('IBIS', dict(rec, **{'200': [{'a': 'Второе издание'}]}))
    check('second save in IBIS -> mfn 2', res2['mfn'] == 2)
    res_other = st.save('SECOND', _good_book())
    check('save in another db restarts mfn at 1', res_other['mfn'] == 1)
    check('IBIS now holds 2 records', st.count('IBIS') == 2)

    # absent mfn -> None
    check('get of absent mfn -> None', st.get('IBIS', 999) is None)


# --------------------------------------------------------------------------- #
# 3. save with missing mandatory 200^a -> rejected (severity-1, ФЛК wired).
# --------------------------------------------------------------------------- #
def flk_reject_checks():
    print('-- save rejected by ФЛК (severity-1)')
    st = _store()
    # A non-аналитика record (920=PAZK) without 200^a -> rec.200a.mandatory (HARD).
    no_title = {'920': 'PAZK', '101': 'rus', '907': [{'a': 'X'}]}
    res = st.save('IBIS', no_title)
    check('missing 200^a rejected (saved False)', res['saved'] is False)
    check('missing 200^a rejected (canSave False)', res['canSave'] is False)
    check('missing 200^a -> no mfn assigned', res['mfn'] is None)
    check('missing 200^a -> no row id', res['id'] is None)
    ids = [v['ruleId'] for v in res['violations']]
    check('missing 200^a fires rec.200a.mandatory', 'rec.200a.mandatory' in ids)
    title_v = [v for v in res['violations'] if v['ruleId'] == 'rec.200a.mandatory'][0]
    check('the blocking violation is severity 1', title_v['severity'] == flk.SEV_HARD)
    check('overallSeverity is HARD', res['overallSeverity'] == flk.SEV_HARD)

    # nothing was written: store still empty, mfn counter not advanced.
    check('rejected save writes no row', st.count('IBIS') == 0)
    nxt = st.save('IBIS', _good_book())
    check('rejected save did not consume an mfn (next is 1)', nxt['mfn'] == 1)


# --------------------------------------------------------------------------- #
# 4. save with only a soft (severity-2) violation -> still saved (преодолимо).
# --------------------------------------------------------------------------- #
def flk_warning_checks():
    print('-- save with soft warning (severity-2, saveable)')
    st = _store()
    # 920=PAZK book with a BAD ISBN check digit -> fld.10.isbn.checksum (SOFT) and
    # no 907 -> rec.907.fio (SOFT). No hard violation -> still saved.
    warn_rec = {
        '920': 'PAZK',
        '200': [{'a': 'Книга с предупреждением'}],
        '101': 'rus',
        '10': [{'a': '5-7654-0001-0'}],          # flipped ISBN check digit
    }
    res = st.save('IBIS', warn_rec)
    check('record with only soft violations is saved', res['saved'] is True)
    check('soft-only save canSave True', res['canSave'] is True)
    sevs = {v['severity'] for v in res['violations']}
    check('soft warning surfaced (severity 2 present)', flk.SEV_SOFT in sevs)
    check('no hard violation present', flk.SEV_HARD not in sevs)
    check('warning record is retrievable', st.get('IBIS', res['mfn']) is not None)

    # skip_warnings flag is surfaced on the result.
    res2 = st.save('IBIS', dict(warn_rec, **{'200': [{'a': 'Ещё одна'}]}),
                   skip_warnings=True)
    check('skip_warnings surfaced when warnings present',
          res2.get('skippedWarnings') is True and res2['saved'] is True)


# --------------------------------------------------------------------------- #
# 5. search by T= / A= / K= / IN=.
# --------------------------------------------------------------------------- #
def search_checks():
    print('-- search (T= / A= / K= / IN=)')
    st = _store()
    res = st.save('IBIS', _good_book())
    mfn = res['mfn']

    # T= title
    hits = st.search('IBIS', 'T=Основы каталогизации')
    check('T= finds by title (total 1)', hits['total'] == 1)
    check('T= hit is the right mfn', hits['items'][0]['mfn'] == mfn)
    check('T= hit brief is non-empty', bool(hits['items'][0]['brief']))

    # A= author (700^a)
    hits_a = st.search('IBIS', 'A=Петров П.П.')
    check('A= finds by author (700^a)', hits_a['total'] == 1
          and hits_a['items'][0]['mfn'] == mfn)

    # K= keyword (610)
    hits_k = st.search('IBIS', 'K=каталогизация')
    check('K= finds by keyword (610)', hits_k['total'] == 1)
    hits_k2 = st.search('IBIS', 'K=библиография')
    check('K= finds the second keyword', hits_k2['total'] == 1)

    # IN= inventory number (910^b)
    hits_in = st.search('IBIS', 'IN=1024365')
    check('IN= finds by inventory number (910^b)', hits_in['total'] == 1)

    # case-insensitive match
    hits_ci = st.search('IBIS', 'A=петров п.п.')
    check('search is case-insensitive', hits_ci['total'] == 1)

    # a bare term (no prefix) searches titles
    bare = st.search('IBIS', 'Основы каталогизации')
    check('bare expression searches titles', bare['total'] == 1)

    # a miss returns empty
    miss = st.search('IBIS', 'T=Не существует')
    check('search miss -> total 0, no items', miss['total'] == 0 and miss['items'] == [])

    # search is db-scoped: same title in another db not found under IBIS only.
    st.save('OTHERDB', _good_book())
    scoped = st.search('IBIS', 'T=Основы каталогизации')
    check('search is db-scoped (still total 1 in IBIS)', scoped['total'] == 1)

    # multiple records sharing a title: total counts both.
    st.save('IBIS', _good_book())
    dup = st.search('IBIS', 'T=Основы каталогизации')
    check('shared-title search counts both records', dup['total'] == 2
          and len(dup['items']) == 2)


# --------------------------------------------------------------------------- #
# 6. logical delete hides from search + get; undelete restores.
# --------------------------------------------------------------------------- #
def delete_checks():
    print('-- logical delete / undelete')
    st = _store()
    mfn = st.save('IBIS', _good_book())['mfn']
    check('pre-delete search finds it', st.search('IBIS', 'T=Основы каталогизации')['total'] == 1)

    ok = st.delete('IBIS', mfn)
    check('delete returns True', ok is True)
    check('deleted record hidden from get', st.get('IBIS', mfn) is None)
    check('deleted record hidden from search',
          st.search('IBIS', 'T=Основы каталогизации')['total'] == 0)
    check('deleted record not in active count', st.count('IBIS') == 0)

    # the row + mfn survive (logical, not physical) and are visible with include_deleted.
    meta = st.get_meta('IBIS', mfn, include_deleted=True)
    check('deleted row survives (status deleted)', meta is not None and meta['status'] == 'deleted')
    check('get with include_deleted returns the record',
          st.get('IBIS', mfn, include_deleted=True) is not None)

    # delete of an already-deleted / absent record -> False
    check('re-delete returns False', st.delete('IBIS', mfn) is False)
    check('delete of absent mfn returns False', st.delete('IBIS', 999) is False)

    # undelete restores + reindexes
    check('undelete returns True', st.undelete('IBIS', mfn) is True)
    check('undeleted record visible in get', st.get('IBIS', mfn) is not None)
    check('undeleted record findable again',
          st.search('IBIS', 'T=Основы каталогизации')['total'] == 1)

    # the mfn is NOT reused after delete: a new save gets the next number.
    st.delete('IBIS', mfn)
    new = st.save('IBIS', _good_book())
    check('mfn not reused after delete (next is 2)', new['mfn'] == mfn + 1)


# --------------------------------------------------------------------------- #
# 7. brief / full PFT (A1) render + units (parse_expr, index_terms).
# --------------------------------------------------------------------------- #
def render_checks():
    print('-- brief / full render (PFT A1)')
    st = _store()
    mfn = st.save('IBIS', _good_book())['mfn']

    brief = st.brief('IBIS', mfn)
    check('brief render is a non-empty string', isinstance(brief, str) and brief != '')
    check('brief contains the title', 'Основы каталогизации' in brief)
    check('brief contains the author (700^a)', 'Петров П.П.' in brief)

    full = st.full('IBIS', mfn)
    check('full render is a non-empty string', isinstance(full, str) and full != '')
    check('full contains the title', 'Основы каталогизации' in full)
    check('full contains the inventory number', '1024365' in full)
    check('full is multi-line', '\n' in full)

    # brief of an absent record is '' (not a crash).
    check('brief of absent record -> empty string', st.brief('IBIS', 999) == '')

    # brief never empty for a record (projection fallback if PFT yields nothing).
    minimal_mfn = st.save('IBIS', {'920': 'PAZK', '200': [{'a': 'Только заглавие'}],
                                   '101': 'rus', '907': [{'a': 'X'}]})['mfn']
    mbrief = st.brief('IBIS', minimal_mfn)
    check('minimal record brief non-empty', bool(mbrief) and 'Только заглавие' in mbrief)


def unit_checks():
    print('-- units (parse_expr / index_terms)')
    st = _store()
    # parse_expr
    check('parse_expr T=term', parse_expr('T=каталог') == ('T', 'каталог'))
    check('parse_expr lowercase prefix', parse_expr('a=Иванов') == ('A', 'Иванов'))
    check('parse_expr bare term -> title', parse_expr('каталог') == ('T', 'каталог'))
    check('parse_expr unknown prefix -> title',
          parse_expr('ZZ=x')[0] == 'T')
    check('parse_expr trims whitespace', parse_expr('  IN = 12  ') == ('IN', '12'))
    check('SEARCH_PREFIXES are the documented four',
          set(SEARCH_PREFIXES) == {'T', 'A', 'K', 'IN'})

    # index_terms extracts the right prefixes from a record.
    terms = dict(((p, t) for p, t in st.index_terms(_good_book())))
    prefixes = {p for p, _ in st.index_terms(_good_book())}
    check('index_terms covers T/A/K/IN', {'T', 'A', 'K', 'IN'} <= prefixes)
    check('index_terms title term', terms.get('T') == 'Основы каталогизации')
    check('index_terms inv term', terms.get('IN') == '1024365')

    # multiple authors (700 + 701) all indexed under A=.
    multi = _good_book()
    multi['701'] = [{'a': 'Соавтор А.А.'}]
    a_terms = {t for p, t in st.index_terms(multi) if p == 'A'}
    check('index_terms indexes 700 and 701 authors',
          'Петров П.П.' in a_terms and 'Соавтор А.А.' in a_terms)


def main():
    schema_checks()
    save_get_checks()
    flk_reject_checks()
    flk_warning_checks()
    search_checks()
    delete_checks()
    render_checks()
    unit_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
