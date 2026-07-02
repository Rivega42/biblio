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
from access.catalog import CatalogStore, parse_expr, SEARCH_PREFIXES, INDEX_SPEC
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
    # The original four prefixes are still present (back-compat); the set has been
    # expanded with the high-frequency §3.2 prefixes (asserted in extra_prefix_*).
    check('SEARCH_PREFIXES still carries the original four',
          {'T', 'A', 'K', 'IN'} <= set(SEARCH_PREFIXES))

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


# --------------------------------------------------------------------------- #
# 8. Расширенная индексация словарного поиска (§3.2): высокочастотные префиксы
#    помимо исходных T=/A=/K=/IN=. Сохраняем запись со всеми полями и находим её
#    по каждому новому префиксу; исходные четыре префикса не сломаны.
# --------------------------------------------------------------------------- #
def _rich_book():
    """Валидная книга (проходит ФЛК save) со ВСЕМИ полями, питающими расширенный
    набор префиксов §3.2. Поля/подполя сверены по FIELD_DICTIONARY (колонка
    «Словарь»): 225^a→TS=, 710/711^a→M=, 606/605^a→S=, 607^a→GEO=, 675/621→U=,
    900^b→V=, 10/11^a→B=, 903→I=, 210^d→G=, 910^d→MHR=."""
    return {
        '920': 'PAZK',
        '200': [{'a': 'Расширенный поиск в каталоге', 'f': 'Иванова И.И.'}],
        '225': [{'a': 'Библиотечная серия'}],            # TS=
        '700': [{'a': 'Петров П.П.'}],                    # A=
        '710': [{'a': 'Институт информации'}],            # M= (и A= back-compat)
        '711': [{'a': 'Конференция ИРБИС'}],              # M=
        '606': [{'a': 'каталогизация'}],                  # S=
        '605': [{'a': 'библиотечное дело'}],              # S=
        '607': [{'a': 'Россия'}],                         # GEO=
        '675': '004.65',                                  # U= (целое поле, УДК)
        '621': '32.973',                                  # U= (целое поле, ББК)
        '900': [{'b': '05'}],                             # V= (вид документа)
        '10': [{'a': '978-5-7654-0001-7'}],               # B= (ISBN)
        '11': [{'a': '0869-6020'}],                       # B= (ISSN)
        '903': 'Ш1/И-99',                                 # I= (шифр, целое поле)
        '210': [{'a': 'Москва', 'c': 'Наука', 'd': '2024'}],  # G= (год = ^d)
        '101': 'rus',
        '610': [{'': 'информатика'}],                     # K= (исходный префикс)
        '910': [{'a': '0', 'b': '2099001', 'd': 'ЧЗ'}],   # IN=910^b, MHR=910^d
        '907': [{'a': 'Сидорова С.С.'}],
    }


def extra_prefix_index_checks():
    print('-- расширенная индексация (§3.2): index_terms / SEARCH_PREFIXES')
    st = _store()
    terms = st.index_terms(_rich_book())
    by_prefix = {}
    for p, t in terms:
        by_prefix.setdefault(p, set()).add(t)

    # каждый новый префикс присутствует в инверсии записи.
    for pre in ('TS', 'M', 'S', 'GEO', 'U', 'V', 'B', 'I', 'G', 'MHR'):
        check('index_terms covers %s=' % pre, pre in by_prefix)
    # исходные четыре по-прежнему индексируются.
    for pre in ('T', 'A', 'K', 'IN'):
        check('index_terms still covers %s= (back-compat)' % pre, pre in by_prefix)

    # точные значения по сверенным полям.
    check('TS= <- 225^a', 'Библиотечная серия' in by_prefix.get('TS', set()))
    check('M= <- 710^a + 711^a',
          {'Институт информации', 'Конференция ИРБИС'} <= by_prefix.get('M', set()))
    check('S= <- 606^a + 605^a',
          {'каталогизация', 'библиотечное дело'} <= by_prefix.get('S', set()))
    check('GEO= <- 607^a', 'Россия' in by_prefix.get('GEO', set()))
    check('U= <- 675 + 621 (whole field)',
          {'004.65', '32.973'} <= by_prefix.get('U', set()))
    check('V= <- 900^b', '05' in by_prefix.get('V', set()))
    check('B= <- 10^a + 11^a',
          {'978-5-7654-0001-7', '0869-6020'} <= by_prefix.get('B', set()))
    check('I= <- 903 (whole field)', 'Ш1/И-99' in by_prefix.get('I', set()))
    check('G= <- 210^d (year)', '2024' in by_prefix.get('G', set()))
    check('MHR= <- 910^d', 'ЧЗ' in by_prefix.get('MHR', set()))
    # 710^a остаётся и под A= (формат записи/привязки не сломаны).
    check('A= still carries 710^a (back-compat)',
          'Институт информации' in by_prefix.get('A', set()))

    # все объявленные SEARCH_PREFIXES реально присутствуют в INDEX_SPEC.
    spec_prefixes = {p for p, _f, _s in INDEX_SPEC}
    check('every SEARCH_PREFIX is indexable',
          set(SEARCH_PREFIXES) <= spec_prefixes)
    check('SEARCH_PREFIXES adds the §3.2 high-freq set',
          {'TS', 'M', 'S', 'GEO', 'U', 'V', 'B', 'I', 'G', 'MHR'} <= set(SEARCH_PREFIXES))


def extra_prefix_search_checks():
    print('-- расширенный словарный поиск (§3.2): найти по каждому новому префиксу')
    st = _store()
    res = st.save('IBIS', _rich_book())
    check('rich record saved (saved True)', res['saved'] is True)
    mfn = res['mfn']

    cases = [
        ('TS=Библиотечная серия', 'TS= серия (225^a)'),
        ('M=Институт информации', 'M= коллектив (710^a)'),
        ('M=Конференция ИРБИС', 'M= мероприятие (711^a)'),
        ('S=каталогизация', 'S= предметная рубрика (606^a)'),
        ('S=библиотечное дело', 'S= рубрика (605^a)'),
        ('GEO=Россия', 'GEO= географ. рубрика (607^a)'),
        ('U=004.65', 'U= УДК (675)'),
        ('U=32.973', 'U= ББК (621)'),
        ('V=05', 'V= вид документа (900^b)'),
        ('B=978-5-7654-0001-7', 'B= ISBN (10^a)'),
        ('B=0869-6020', 'B= ISSN (11^a)'),
        ('I=Ш1/И-99', 'I= шифр документа (903)'),
        ('G=2024', 'G= год издания (210^d)'),
        ('MHR=ЧЗ', 'MHR= место хранения (910^d)'),
    ]
    for expr, label in cases:
        hits = st.search('IBIS', expr)
        check('%s finds the record' % label,
              hits['total'] == 1 and hits['items'][0]['mfn'] == mfn)

    # parse_expr корректно разбирает многосимвольные/новые префиксы.
    check('parse_expr GEO=', parse_expr('GEO=Россия') == ('GEO', 'Россия'))
    check('parse_expr MHR= (multichar)', parse_expr('MHR=ЧЗ') == ('MHR', 'ЧЗ'))
    check('parse_expr lowercase mhr=', parse_expr('mhr=чз') == ('MHR', 'чз'))

    # регистронезависимость для нового префикса.
    ci = st.search('IBIS', 'M=институт информации')
    check('extended prefix search is case-insensitive', ci['total'] == 1)

    # промах по новому префиксу -> пусто (а не ошибка).
    miss = st.search('IBIS', 'U=999.999')
    check('extended-prefix miss -> total 0', miss['total'] == 0 and miss['items'] == [])

    # исходные четыре префикса по-прежнему находят ту же запись.
    for expr, label in (('T=Расширенный поиск в каталоге', 'T='),
                        ('A=Петров П.П.', 'A='),
                        ('K=информатика', 'K='),
                        ('IN=2099001', 'IN=')):
        hits = st.search('IBIS', expr)
        check('original prefix %s still works' % label, hits['total'] == 1)

    # удаление прячет запись из расширенного поиска; undelete возвращает.
    st.delete('IBIS', mfn)
    check('extended prefix hidden after delete',
          st.search('IBIS', 'U=004.65')['total'] == 0)
    st.undelete('IBIS', mfn)
    check('extended prefix findable after undelete',
          st.search('IBIS', 'U=004.65')['total'] == 1)


def exemplar_by_tag_checks():
    print('-- find_exemplar_by_tag (RFID-метка -> экземпляр, G1 #411)')
    st = _store()
    # Копия с RFID-меткой на самом экземпляре (910^h) + инв.№ (910^b).
    rec = dict(_good_book())
    rec['910'] = [{'a': '0', 'b': 'INV-A1', 'h': 'E2003411DEADBEEF00000001'}]
    r = st.save('IBIS', rec)
    check('rec with 910^h saved', r['saved'] is True)
    mfn = r['mfn']

    hit = st.find_exemplar_by_tag('IBIS', 'E2003411DEADBEEF00000001')
    check('find_exemplar_by_tag matches 910^h', hit is not None and hit[0] == mfn)
    check('resolved instance carries inventory 910^b',
          hit is not None and hit[2].get('b') == 'INV-A1')
    check('unknown tag -> None', st.find_exemplar_by_tag('IBIS', 'NOPE') is None)
    check('empty tag -> None', st.find_exemplar_by_tag('IBIS', '') is None)

    # Фолбэк по 941^h (RFID-дубль уровня записи; у 910 метки нет) → первая копия.
    rec2 = dict(_good_book())
    rec2['200'] = [{'a': 'Издание с меткой в 941'}]
    rec2['910'] = [{'a': '0', 'b': 'INV-B7'}]
    rec2['941'] = [{'h': 'E2003411CAFEBABE00000002'}]
    r2 = st.save('IBIS', rec2)
    check('rec with 941^h saved', r2['saved'] is True)
    hit2 = st.find_exemplar_by_tag('IBIS', 'E2003411CAFEBABE00000002')
    check('941^h fallback resolves to first 910 copy',
          hit2 is not None and hit2[2].get('b') == 'INV-B7')

    # Индексация/поиск по RF= (метка → запись через словарь).
    check('RF in SEARCH_PREFIXES', 'RF' in SEARCH_PREFIXES)
    check('RF binds 910^h in INDEX_SPEC', ('RF', '910', 'h') in INDEX_SPEC)
    check('RF binds 941^h in INDEX_SPEC', ('RF', '941', 'h') in INDEX_SPEC)
    check('RF= search finds the tagged record',
          st.search('IBIS', 'RF=E2003411DEADBEEF00000001')['total'] == 1)

    # H5 (#16): та же метка на копии ДРУГОЙ записи → неоднозначно → None (не гадаем).
    dup = dict(_good_book())
    dup['200'] = [{'a': 'Двойник по метке'}]
    dup['910'] = [{'a': '0', 'b': 'INV-DUP', 'h': 'E2003411DEADBEEF00000001'}]
    st.save('IBIS', dup)
    check('EPC на копиях разных записей → None (неоднозначно)',
          st.find_exemplar_by_tag('IBIS', 'E2003411DEADBEEF00000001') is None)


def main():
    schema_checks()
    save_get_checks()
    flk_reject_checks()
    flk_warning_checks()
    search_checks()
    delete_checks()
    render_checks()
    unit_checks()
    extra_prefix_index_checks()
    extra_prefix_search_checks()
    exemplar_by_tag_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
