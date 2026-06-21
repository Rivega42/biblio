#!/usr/bin/env python3
"""Authority-files service tests (gap A4, epic #188).

Covers the first shippable slice of the authority service (access/authority.py):

  1. AuthorityStore (in-memory sqlite, no server): seed a few person/subject/
     corporate records -> search finds by term (prefix + substring), get returns
     the full record, base isolation (athra id not fetchable as athrs), empty
     store / no hit returns [] not error (SPEC AC-L1).
  2. Substitution fill-map (SPEC §3.2): person -> 700 fills ^a/^b/^g/^f/^9 + ^3;
     corporate -> 710 fills ^a/^b/^c/^s + ^3; subject -> 606 collects heading +
     subrubrics + ^3; ^3 always == authority id and never copied from the
     authority's own subfields; index field 675 carries NO ^3; absent subfields
     omitted (operator role ^9/^4 not clobbered).
  3. Error paths: missing authority (None) and unknown catalog field both raise;
     kind/field mismatch (person record into a corporate field) raises.

Standalone-runnable (``py -3.12 tests/test_authority.py``) in the house style of
tests/test_seeding.py: ``ok …`` lines + ``N passed, M failed`` + exit code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import authority as A
from access.authority import (AuthorityStore, substitute,
                              AuthorityNotFound, UnknownCatalogField)

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
# Shared fixture: a tiny seeded store with persons / corporate / subject.
# --------------------------------------------------------------------------- #
def seed_store():
    st = AuthorityStore(':memory:')
    ids = {}
    # ATHRA — individual author: Толстой, Л. Н. (Лев Николаевич), 1828-1910.
    ids['tolstoy'] = st.add_record(
        'athra',
        {'a': 'Толстой', 'b': 'Л. Н.', 'g': 'Лев Николаевич',
         'f': '1828-1910', '9': '1'},
        terms=['Толстой, Л. Н.', 'Толстой Лев Николаевич'],
        worklist='ATHRA')
    # ATHRA — a second person, to prove search discriminates.
    ids['chekhov'] = st.add_record(
        'athra',
        {'a': 'Чехов', 'b': 'А. П.', 'g': 'Антон Павлович', 'f': '1860-1904'},
        terms=['Чехов, А. П.', 'Чехов Антон Павлович'])
    # ATHRC — corporate body (with subdivision + city + country).
    ids['rgb'] = st.add_record(
        'athrc',
        {'a': 'Российская государственная библиотека', 'b': 'НИО редких книг',
         'c': 'Москва', 's': 'RU', '9': '0'},
        terms=['Российская государственная библиотека'])
    # ATHRS — subject heading with thematic + geographic subrubric.
    ids['lit'] = st.add_record(
        'athrs',
        {'a': 'Литература', 'b': 'История и критика', 'g': 'Россия',
         'h': '19 в.'},
        terms=['Литература -- История и критика'])
    # ATHRU — UDC index entry (no ^3 link on substitution).
    ids['udc'] = st.add_record(
        'athru',
        {'a': '821.161.1', 'c': 'Русская литература'},
        terms=['821.161.1', 'Русская литература'])
    return st, ids


# --------------------------------------------------------------------------- #
# 1. Store: search + get + isolation.
# --------------------------------------------------------------------------- #
def store_checks():
    print('-- AuthorityStore (search / get / isolation)')
    st, ids = seed_store()

    # db<->kind mapping is the six ИРБИС bases.
    check('db->kind maps six bases', set(A.DB_TO_KIND) ==
          {'athra', 'athrc', 'athrs', 'athrg', 'athru', 'athrb'})

    # prefix search finds Толстой by an explicit term.
    hits = st.search('athra', 'Толс')
    check('prefix search finds by term', len(hits) == 1 and
          hits[0]['id'] == ids['tolstoy'])
    check('hit carries kind', hits and hits[0]['kind'] == 'personal')
    check('hit carries matched term', hits and 'Толстой' in (hits[0]['matched'] or ''))
    check('hit carries fill_hint (AC-L4)',
          hits and hits[0]['fill_hint'].get('a') == 'Толстой')

    # prefix is right-truncation only: 'олстой' (substring) does NOT match in prefix mode.
    check('prefix mode does not match mid-string',
          st.search('athra', 'олстой') == [])
    # ...but substring mode does.
    sub = st.search('athra', 'олстой', mode='substring')
    check('substring mode matches mid-string',
          len(sub) == 1 and sub[0]['id'] == ids['tolstoy'])

    # search discriminates between the two persons.
    chk = st.search('athra', 'Чех')
    check('search discriminates persons',
          len(chk) == 1 and chk[0]['id'] == ids['chekhov'])

    # case-insensitive (term_norm lower-casing).
    check('search is case-insensitive',
          len(st.search('athra', 'толс')) == 1)

    # empty query / empty store -> [] (AC-L1, not an error).
    check('empty query returns []', st.search('athra', '') == [])
    check('no-hit returns []', st.search('athra', 'Достоев') == [])
    empty = AuthorityStore(':memory:')
    check('empty store returns [] not error', empty.search('athra', 'x') == [])

    # base isolation: an athrc query never returns the athra record, and vice versa.
    check('corporate base finds its own record',
          len(st.search('athrc', 'Российская')) == 1)
    check('corporate query does not leak person',
          st.search('athrc', 'Толс') == [])

    # get returns the full record within the right base.
    rec = st.get('athra', ids['tolstoy'])
    check('get returns full record', rec is not None and
          rec['heading_210']['a'] == 'Толстой' and
          rec['heading_210']['f'] == '1828-1910')
    check('get echoes record id', rec['id'] == ids['tolstoy'])
    check('get carries worklist extra', rec.get('worklist') == 'ATHRA')

    # get is base-scoped: the person id is NOT fetchable as a subject record.
    check('get is base-scoped (no cross-base fetch)',
          st.get('athrs', ids['tolstoy']) is None)
    check('get missing id returns None', st.get('athra', 99999) is None)


# --------------------------------------------------------------------------- #
# 2. Substitution fill-map (SPEC §3.2).
# --------------------------------------------------------------------------- #
def substitute_checks():
    print('-- substitute (fill-map 700/710/606/675 + ^3)')
    st, ids = seed_store()

    # --- person -> 700: ^a/^b/^g/^f/^9 + ^3 (AC-S1). ---
    person = st.get('athra', ids['tolstoy'])
    patch700 = substitute('700', person)
    check('700 fills ^a (фамилия)', patch700['a'] == 'Толстой')
    check('700 fills ^b (инициалы)', patch700['b'] == 'Л. Н.')
    check('700 fills ^g (расширение)', patch700['g'] == 'Лев Николаевич')
    check('700 fills ^f (даты)', patch700['f'] == '1828-1910')
    check('700 fills ^9 (признак)', patch700['9'] == '1')
    check('700 writes ^3 = authority id', patch700['3'] == str(ids['tolstoy']))
    check('700 ^3 is the id, not an authority subfield',
          '3' not in person['heading_210'] and patch700['3'] == str(person['id']))

    # 701 uses the same person fill-map.
    check('701 fills like 700', substitute('701', person)['a'] == 'Толстой')

    # --- absent subfield omitted: Чехов has no ^9 -> patch has no '9'. ---
    chekhov = st.get('athra', ids['chekhov'])
    pc = substitute('700', chekhov)
    check('absent ^9 omitted (operator role not clobbered)', '9' not in pc)
    check('present ^f still filled', pc['f'] == '1860-1904')
    check('absent subfield still links ^3', pc['3'] == str(ids['chekhov']))

    # --- corporate -> 710: ^a/^b/^c/^s + ^3 (AC-S2). ---
    rgb = st.get('athrc', ids['rgb'])
    patch710 = substitute('710', rgb)
    check('710 fills ^a (наименование)',
          patch710['a'] == 'Российская государственная библиотека')
    check('710 fills ^b (подразделение)', patch710['b'] == 'НИО редких книг')
    check('710 fills ^c (город)', patch710['c'] == 'Москва')
    check('710 fills ^s (страна)', patch710['s'] == 'RU')
    check('710 writes ^3', patch710['3'] == str(ids['rgb']))

    # --- subject -> 606: heading + subrubrics + ^3 (AC-S3). ---
    lit = st.get('athrs', ids['lit'])
    patch606 = substitute('606', lit)
    check('606 fills ^a (заголовок)', patch606['a'] == 'Литература')
    check('606 fills ^b (темат. подзагол.)', patch606['b'] == 'История и критика')
    check('606 fills ^g (геогр. подзагол.)', patch606['g'] == 'Россия')
    check('606 fills ^h (хронол. подзагол.)', patch606['h'] == '19 в.')
    check('606 writes ^3', patch606['3'] == str(ids['lit']))

    # --- index field 675 (UDC): fills ^a/^c but NO ^3 link (SPEC §3.2). ---
    udc = st.get('athru', ids['udc'])
    patch675 = substitute('675', udc)
    check('675 fills ^a (индекс)', patch675['a'] == '821.161.1')
    check('675 fills ^c (поясн. слова)', patch675['c'] == 'Русская литература')
    check('675 carries NO ^3 link', '3' not in patch675)

    # patch is a plain dict the client can apply directly (AC-L4).
    check('patch is a plain dict', isinstance(patch700, dict))


# --------------------------------------------------------------------------- #
# 3. Error / edge paths.
# --------------------------------------------------------------------------- #
def error_checks():
    print('-- error paths (missing authority / unknown field / kind mismatch)')
    st, ids = seed_store()

    # missing authority (None) -> AuthorityNotFound.
    raised = False
    try:
        substitute('700', None)
    except AuthorityNotFound:
        raised = True
    check('missing authority raises AuthorityNotFound', raised)

    # unknown catalog field -> UnknownCatalogField.
    raised = False
    try:
        substitute('999', st.get('athra', ids['tolstoy']))
    except UnknownCatalogField:
        raised = True
    check('unknown catalog field raises UnknownCatalogField', raised)

    # kind/field mismatch: a person record into a corporate field (710) raises.
    raised = False
    try:
        substitute('710', st.get('athra', ids['tolstoy']))
    except AuthorityNotFound:
        raised = True
    check('person-into-corporate-field raises', raised)

    # add_record rejects an unknown db.
    raised = False
    try:
        st.add_record('athrx', {'a': 'x'})
    except ValueError:
        raised = True
    check('add_record rejects unknown db', raised)

    # integer tag also works (str-coerced).
    p = substitute(700, st.get('athra', ids['tolstoy']))
    check('integer catalog tag accepted', p['a'] == 'Толстой')


def main():
    store_checks()
    substitute_checks()
    error_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
