#!/usr/bin/env python3
"""ИРБИС → Biblio migrator tests (pilot enabler, epic #223 — tools/migrate_irbis.py).

Exercises the migrator end-to-end against a **FakeIrbis** source (synthetic
records + readers, NO live server) loading into in-memory Biblio stores:

  1. catalog: synthetic IBIS records map + load with correct fields/exemplars
     (200/700/210/910 preserved; subfield codes canonicalized to 200^a/910^b);
     the loaded records are findable by T=/A=/IN= and the 910 exemplar survives.
  2. deleted / empty / unreadable source records are SKIPPED (counted), nothing
     loaded for them.
  3. idempotent re-run: migrating the same source twice does NOT duplicate — the
     source-MFN idempotency key resolves the existing target record and upserts.
  4. readers: RDR records map to circulation readers (ticket + category) and the
     reader display name is stored as CIPHERTEXT at rest (V1 crypto seam) — a raw
     read of the at-rest column never reveals the plaintext name. Idempotent by
     ticket; PII never appears in plaintext in the store.
  5. dry-run: reads + maps + reports the would-load counts but writes NOTHING
     (catalog empty, no reader rows, no PII persisted).
  6. report shape + redaction units.

Standalone-runnable, mirroring the house style of tests/test_catalog.py::

    py -3.12 tests/test_migrate.py   ->  'ok …' lines + 'N passed, M failed', exit!=0

NO live-server dependency. (A `--dry-run` smoke against a real 127.0.0.1:6666 is a
valid manual validation but is deliberately NOT in this committed suite.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import crypto
from access.circulation import CirculationStore
from access.store import AccessStore
from access.catalog import CatalogStore

from tools.migrate_irbis import (
    Migrator, Targets, map_catalog_record, map_reader_record, redact,
    _status_is_deleted, _reader_display_name, SOURCE_MFN_FIELD, SOURCE_MFN_SUB,
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


# --------------------------------------------------------------------------- #
# FakeIrbis — a synthetic source satisfying the migrator's read interface
# (max_mfn / read_record). Records are in the irbis.parser shape:
#   {'mfn','status','fields':[{'tag','value','text','subfields'}…]}
# Subfield codes are UPPER-case, mirroring the live server (the mapper lower-cases
# them). A record may be: a dict (returned), 'DELETED' (status carries the delete
# bit), 'EMPTY' (no fields), or 'ERROR' (read raises, as a locked/-605 MFN does).
# --------------------------------------------------------------------------- #
class FakeIrbisError(Exception):
    pass


class FakeIrbis:
    def __init__(self, dbs):
        # dbs: {db_name: [record-or-sentinel, …]} 1-indexed by position+1
        self._dbs = dbs

    def max_mfn(self, db):
        return len(self._dbs.get(db, []))

    def read_record(self, db, mfn):
        recs = self._dbs.get(db, [])
        if mfn < 1 or mfn > len(recs):
            raise FakeIrbisError('out of range')
        item = recs[mfn - 1]
        if item == 'ERROR':
            raise FakeIrbisError('-605 locked/deleted')
        if item == 'EMPTY':
            return {'mfn': mfn, 'status': '', 'fields': []}
        if item == 'DELETED':
            return {'mfn': mfn, 'status': '1', 'fields': [_fld('200', subs={'A': 'Удалённая'})]}
        return item

    def close(self):
        pass


def _fld(tag, value=None, text='', subs=None):
    """Build a parser-shape field dict (UPPER-case subfield codes, like live)."""
    subs = subs or {}
    if value is None:
        value = ('^' + '^'.join('%s%s' % (k, v) for k, v in subs.items())) if subs else text
    return {'tag': tag, 'value': value, 'text': text, 'subfields': dict(subs)}


def _bib(mfn, title, author=None, inv=None, status=''):
    """A synthetic IBIS bibliographic record (parser shape)."""
    fields = [
        _fld('920', text='PAZK'),
        _fld('200', subs={'A': title, 'F': 'отв. ' + (author or 'N.N.')}),
        _fld('101', text='rus'),
        _fld('907', subs={'A': 'Каталогизатор'}),
    ]
    if author:
        fields.append(_fld('700', subs={'A': author}))
    if inv:
        fields.append(_fld('910', subs={'A': '0', 'B': inv, 'D': 'ХР'}))
    fields.append(_fld('610', text='тест'))
    fields.append(_fld('210', subs={'A': 'СПб', 'D': '2013', 'C': 'Изд-во'}))
    return {'mfn': mfn, 'status': status, 'fields': fields}


def _reader(mfn, ticket, surname, name='', patronymic='', email='', category='В01',
            status=''):
    fields = [_fld('30', text=ticket), _fld('920', text='RDR'),
              _fld('50', text=category)]
    if surname:
        fields.append(_fld('10', text=surname))
    if name:
        fields.append(_fld('11', text=name))
    if patronymic:
        fields.append(_fld('12', text=patronymic))
    if email:
        fields.append(_fld('32', text=email))
    return {'mfn': mfn, 'status': status, 'fields': fields}


def _fresh_targets():
    access = AccessStore(':memory:')
    catalog = CatalogStore(':memory:', access_store=access)
    circ = CirculationStore(':memory:')
    return Targets(catalog, circ, access, catalog_db='IBIS', tenant='public')


# --------------------------------------------------------------------------- #
# 1. Catalog migration: map + load, fields/exemplars preserved, findable.
# --------------------------------------------------------------------------- #
def catalog_load_checks():
    print('-- catalog migration (map + load)')
    src = FakeIrbis({'IBIS': [
        _bib(1, 'Основы каталогизации', 'Петров П.П.', '1024365'),
        _bib(2, 'Второе издание', 'Сидоров С.С.', '2048001'),
    ]})
    t = _fresh_targets()
    rep = Migrator(src, t).migrate_catalog(src_db='IBIS')
    check('records_read == 2', rep['records_read'] == 2)
    check('records_loaded == 2', rep['records_loaded'] == 2)
    check('no errors', rep['errors'] == 0)
    check('catalog holds 2 active records', t.catalog.count('IBIS') == 2)

    # The first record round-trips into the canonical 200^a/910^b shape.
    rec = None
    for mfn in t.catalog.list_mfns('IBIS'):
        r = t.catalog.get('IBIS', mfn)
        if r and r.get('200') and r['200'][0].get('a') == 'Основы каталогизации':
            rec = r
            break
    check('record found in target', rec is not None)
    check('200^a title preserved (canonical lower-case)',
          rec['200'][0]['a'] == 'Основы каталогизации')
    check('200^f responsibility preserved', rec['200'][0].get('f', '').startswith('отв.'))
    check('700^a author preserved', rec['700'][0]['a'] == 'Петров П.П.')
    check('210 imprint preserved (210^d)', rec['210'][0]['d'] == '2013')
    # 910 exemplar: status ^a + inventory ^b survive, lower-cased.
    check('910 exemplar present', '910' in rec and isinstance(rec['910'], list))
    check('910^b inventory preserved', rec['910'][0]['b'] == '1024365')
    check('910^a status preserved', rec['910'][0]['a'] == '0')
    check('910^d location preserved', rec['910'][0]['d'] == 'ХР')
    # idempotency stamp present.
    stamp = [i for i in rec[SOURCE_MFN_FIELD] if isinstance(i, dict) and SOURCE_MFN_SUB in i]
    check('source-MFN idempotency stamp written', stamp and stamp[0][SOURCE_MFN_SUB] == '1')

    # findable by the indexed prefixes.
    check('findable by T= (title)', t.catalog.search('IBIS', 'T=Основы каталогизации')['total'] == 1)
    check('findable by A= (author 700^a)', t.catalog.search('IBIS', 'A=Петров П.П.')['total'] == 1)
    check('findable by IN= (910^b)', t.catalog.search('IBIS', 'IN=1024365')['total'] == 1)


# --------------------------------------------------------------------------- #
# 2. Deleted / empty / unreadable records are skipped.
# --------------------------------------------------------------------------- #
def skip_checks():
    print('-- skip deleted / empty / unreadable')
    src = FakeIrbis({'IBIS': [
        _bib(1, 'Хорошая книга', 'Автор А.', '1000'),
        'DELETED',     # status carries the delete bit
        'EMPTY',       # no fields
        'ERROR',       # read raises (locked / -605)
        _bib(5, 'Вторая хорошая', 'Автор Б.', '2000'),
    ]})
    t = _fresh_targets()
    rep = Migrator(src, t).migrate_catalog(src_db='IBIS')
    # read: the 2 good + the deleted + the empty are read (4); the ERROR one raises.
    check('records_read counts readable records (4)', rep['records_read'] == 4)
    check('only the 2 valid records loaded', rep['records_loaded'] == 2)
    check('skipped counts deleted+empty+error (3)', rep['skipped'] == 3)
    check('catalog holds exactly the 2 valid records', t.catalog.count('IBIS') == 2)
    check('deleted record not loaded', t.catalog.search('IBIS', 'T=Удалённая')['total'] == 0)
    check('valid records loaded', t.catalog.search('IBIS', 'T=Хорошая книга')['total'] == 1
          and t.catalog.search('IBIS', 'T=Вторая хорошая')['total'] == 1)


# --------------------------------------------------------------------------- #
# 3. Idempotent re-run: no duplicates.
# --------------------------------------------------------------------------- #
def idempotency_checks():
    print('-- idempotent re-run (no dupes)')
    src = FakeIrbis({'IBIS': [
        _bib(1, 'Книга про идемпотентность', 'Автор И.', '5555'),
        _bib(2, 'Ещё одна', 'Автор Е.', '6666'),
    ]})
    t = _fresh_targets()
    rep1 = Migrator(src, t).migrate_catalog(src_db='IBIS')
    check('first run loads 2', rep1['records_loaded'] == 2 and t.catalog.count('IBIS') == 2)
    mfns_after_1 = set(t.catalog.list_mfns('IBIS'))

    # re-run the SAME source: must upsert, not duplicate.
    rep2 = Migrator(src, t).migrate_catalog(src_db='IBIS')
    check('re-run reads 2 again', rep2['records_read'] == 2)
    check('re-run loads (upserts) 2', rep2['records_loaded'] == 2)
    check('catalog STILL holds 2 (no dupes)', t.catalog.count('IBIS') == 2)
    check('re-run did not mint new mfns', set(t.catalog.list_mfns('IBIS')) == mfns_after_1)
    check('search still finds exactly one of each',
          t.catalog.search('IBIS', 'IN=5555')['total'] == 1
          and t.catalog.search('IBIS', 'IN=6666')['total'] == 1)


# --------------------------------------------------------------------------- #
# 4. Reader migration: ticket + category, PII ENCRYPTED at rest, idempotent.
# --------------------------------------------------------------------------- #
def reader_load_checks():
    print('-- reader migration (PII encrypted at rest)')
    src = FakeIrbis({'RDR': [
        _reader(1, '111', 'Бродовский', 'Александр', 'Иосифович',
                'alio@example.ru', category='В01'),
        _reader(2, '222', 'Иванова', 'Мария', email='maria@example.ru',
                category='С02'),
        _reader(3, '', 'Безбилетный'),     # no ticket -> skipped
    ]})
    t = _fresh_targets()
    rep = Migrator(src, t).migrate_readers(src_db='RDR')
    check('readers_read == 3', rep['records_read'] == 3)
    check('readers_loaded == 2 (ticketless skipped)', rep['readers_loaded'] == 2)
    check('ticketless reader skipped (1)', rep['skipped'] == 1)

    # circulation reader rows: ticket + category, NO PII.
    rd = t.circulation.get_reader('111')
    check('circulation reader 111 created', rd is not None)
    check('reader category mapped (50 -> В01)', rd['category'] == 'В01')
    check('circulation reader row carries no name column', 'reader_name' not in rd)

    # PII at rest is CIPHERTEXT (V1 seam): raw column is a pdn token, plaintext absent.
    raw = t.access.review_name_ciphertext('111', '_MIGRATION', 0)
    check('reader name persisted', raw is not None)
    check('reader name is ciphertext token at rest', crypto.is_token(raw))
    check('plaintext surname NOT present in at-rest value', 'Бродовский' not in raw)
    check('decrypt round-trips the full name',
          crypto.decrypt(raw) == 'Бродовский Александр Иосифович')
    # second reader too
    raw2 = t.access.review_name_ciphertext('222', '_MIGRATION', 0)
    check('second reader name ciphertext at rest', crypto.is_token(raw2)
          and 'Иванова' not in raw2)

    # idempotent by ticket: re-run does not duplicate / corrupt.
    rep2 = Migrator(src, t).migrate_readers(src_db='RDR')
    check('reader re-run loads 2 again (upsert)', rep2['readers_loaded'] == 2)
    again = t.circulation.get_reader('111')
    check('reader 111 still single, category intact', again is not None and again['category'] == 'В01')
    check('reader name still decrypts after re-run',
          crypto.decrypt(t.access.review_name_ciphertext('111', '_MIGRATION', 0))
          == 'Бродовский Александр Иосифович')


# --------------------------------------------------------------------------- #
# 5. Dry-run writes NOTHING.
# --------------------------------------------------------------------------- #
def dry_run_checks():
    print('-- dry-run reads + reports but writes nothing')
    src = FakeIrbis({
        'IBIS': [_bib(1, 'Сухой прогон', 'Автор С.', '7777'),
                 _bib(2, 'Второй', 'Автор В.', '8888')],
        'RDR': [_reader(1, '333', 'Секретов', 'Сергей', email='s@example.ru')],
    })
    t = _fresh_targets()
    rep = Migrator(src, t, dry_run=True).run(dbs=('IBIS', 'RDR'), catalog_db='IBIS')
    check('dry-run reports records_read (3)', rep['records_read'] == 3)
    check('dry-run reports would-load records (2)', rep['records_loaded'] == 2)
    check('dry-run reports would-load readers (1)', rep['readers_loaded'] == 1)
    # NOTHING written.
    check('dry-run wrote NO catalog rows', t.catalog.count('IBIS') == 0)
    check('dry-run wrote NO reader row', t.circulation.get_reader('333') is None)
    check('dry-run persisted NO reader PII',
          t.access.review_name_ciphertext('333', '_MIGRATION', 0) is None)


# --------------------------------------------------------------------------- #
# 6. Full run + report shape + unit checks.
# --------------------------------------------------------------------------- #
def report_and_unit_checks():
    print('-- full run report shape + units')
    src = FakeIrbis({
        'IBIS': [_bib(1, 'Книга', 'Автор', '9001'), 'ERROR',
                 _bib(3, 'Книга 2', 'Автор 2', '9002')],
        'RDR': [_reader(1, '444', 'Петрова', 'Анна')],
    })
    t = _fresh_targets()
    rep = Migrator(src, t).run(dbs=('IBIS', 'RDR'), catalog_db='IBIS')
    check('report has all five keys',
          set(rep) >= {'records_read', 'records_loaded', 'readers_loaded',
                       'skipped', 'errors'})
    check('full run loaded 2 records', rep['records_loaded'] == 2)
    check('full run loaded 1 reader', rep['readers_loaded'] == 1)
    check('full run skipped the ERROR record', rep['skipped'] == 1)
    check('full run no errors', rep['errors'] == 0)

    # limit caps the read count.
    t2 = _fresh_targets()
    rep_lim = Migrator(src, t2).migrate_catalog(src_db='IBIS', limit=1)
    check('limit caps records read to 1', rep_lim['records_read'] == 1)

    # units: status-delete detection.
    check('empty status => active', not _status_is_deleted(''))
    check('None status => active', not _status_is_deleted(None))
    check('status with delete bit (1) => deleted', _status_is_deleted('1'))
    check('status with absent bit (128) => deleted', _status_is_deleted('128'))
    check('non-delete status (2 long) => active', not _status_is_deleted('2'))
    check('non-numeric status => active', not _status_is_deleted('xx'))

    # units: redaction never leaks a full PII value.
    check('redact masks the tail', redact('Бродовский') == 'Бр***')
    check('redact handles short value', redact('А') == 'А***')
    check('redact empty -> empty', redact('') == '' and redact(None) == '')

    # units: mapping of a reader with no PII still yields a ticket.
    mapped = map_reader_record(_reader(1, '555', '', ''))
    check('reader map keeps ticket with no PII', mapped['ticket'] == '555')
    check('reader display name empty when no name parts',
          _reader_display_name(mapped['pii']) == '')

    # units: a catalog record with no source mfn maps without an idempotency stamp.
    rec, mfn = map_catalog_record({'mfn': None, 'status': '',
                                   'fields': [_fld('200', subs={'A': 'X'})]})
    check('map without mfn -> no stamp, mfn None',
          mfn is None and SOURCE_MFN_FIELD not in rec)


def main():
    catalog_load_checks()
    skip_checks()
    idempotency_checks()
    reader_load_checks()
    dry_run_checks()
    report_and_unit_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
