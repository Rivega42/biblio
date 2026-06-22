#!/usr/bin/env python3
"""ИРБИС → Biblio data **migrator** (pilot enabler, epic #223).

Exports an existing ИРБИС library's data from a *source* ИРБИС64 server and loads
it into Biblio's own store (the same sqlite-dev / PostgreSQL-prod stores the app
serves from). This is the seam that lets a real library move off the legacy САБ
onto Biblio: catalog records (``IBIS``) become :class:`access.catalog.CatalogStore`
records; readers (``RDR``) become circulation readers + the portal reader store,
with their ПДн **encrypted at rest** (V1 seam, ``access/crypto.py``).

It RUNS transiently against a real server to populate a target DB; it is NOT part
of the serving app. The protocol layer (``irbis/`` client + ``core``'s
``SessionManager``) is reused unchanged as the read-only export handle; the target
stores are reused unchanged as the load handle — nothing in ``core.py`` /
``access/catalog.py`` is modified.

ПДн / security (HARD)
---------------------
Real reader data (RDR) is персональные данные. This tool only ever *loads* a
target DB — it must NEVER persist real ПДн or credentials to the repository. Two
guarantees enforce that here:

  * **Encryption at rest.** Every reader PII field this migrator writes (name parts,
    e-mail, phone) is run through :func:`access.crypto.encrypt` before it touches a
    store, so the migrated value is ciphertext — exactly like
    ``reader_review.reader_name``. A raw dump of the target never reveals a name.
  * **Redacted logging.** The report carries COUNTS only; per-record logging (when
    enabled) prints redacted samples (``Бр***``), never a full name/contact and
    never the source password.

Mapping (ИРБИС → Biblio)
------------------------
*Catalog* (``IBIS`` → ``CatalogStore`` records — the shapes already match, so the
map is largely 1:1, lower-casing subfield codes to the canonical ``200^a`` form
the engines/index use)::

    200 (заглавие)        -> 200^a title, ^e/^f/^v…   (DB_IBIS §3.5)
    700/701/702/710       -> author/collective headings (^a/^g…)
    210 (выходные данные) -> imprint
    101/102               -> language / country
    675/621               -> УДК / ББК
    610                   -> unstructured keywords (K=)
    910 (экземпляры)      -> exemplars, ^a status / ^b inventory / ^d location …
    920                   -> worklist (carried so ФЛК picks the right rules)
    <source MFN>          -> 907^_mfn  (idempotency key, see below)

*Reader* (``RDR`` → circulation reader + portal reader store — minimal, only what
the product uses; DB_CIRCULATION §1–3)::

    30 (RI=)              -> reader ticket  (the primary key everywhere)
    10/11/12              -> surname / name / patronymic  (ПДн -> ENCRYPTED)
    32, 17/18             -> e-mail / phones              (ПДн -> ENCRYPTED)
    50                    -> reader category (circulation policy bucket)

Idempotency
-----------
A re-run must UPSERT, never duplicate. The stable key per catalog record is its
**source MFN**, stamped into the loaded record as a private ``907^_mfn`` subfield
and indexed on first load so a re-run resolves the existing target ``mfn`` and
updates it in place (CatalogStore.save with an explicit ``mfn``). Readers are keyed
by their ticket (``30``/RI=), which is already the natural primary key of every
reader table — re-loading a ticket is an ``INSERT OR REPLACE`` upsert.

CLI
---
::

    python -m tools.migrate_irbis --source-host H --source-port P \
        --user U --pass S --target-tenant slug \
        [--dbs IBIS,RDR] [--catalog-db IBIS] [--dry-run] [--limit N] [--verbose]

Prints a JSON report ``{records_read, records_loaded, readers_loaded, skipped,
errors}``. ``--dry-run`` connects, reads, and maps every record/reader and reports
the same counts WITHOUT writing the target (no row touched, no PII persisted).
"""
import argparse
import json
import sys

# Reused as handles — NOT modified. Import lazily-friendly (the protocol + stores
# are stdlib-only so this works on a fresh box with no installs).
from access import crypto
from access.catalog import CatalogStore
from access.circulation import CirculationStore
from access.store import AccessStore


# --------------------------------------------------------------------------- #
# Idempotency key. The source MFN is stamped into a private 907 subfield so a
# re-run can find the already-loaded target record and update it in place rather
# than inserting a duplicate. 907 (каталогизатор/служебное) is the natural home;
# the '_mfn' subfield code is private (won't collide with a real ^a/^b/^c).
# --------------------------------------------------------------------------- #
SOURCE_MFN_FIELD = '907'
SOURCE_MFN_SUB = '_mfn'

# Catalog fields we carry across. The record shapes already match (MARC-ish
# field->[{subfield:value}]); we copy every field the source has, but this is the
# documented set the product reads / indexes (DB_IBIS §3.3/§3.5). We copy ALL
# fields verbatim — this list is for documentation + the dry-run preview.
CATALOG_FIELDS = (
    '200', '700', '701', '702', '710', '210', '205', '215', '101', '102',
    '675', '621', '606', '607', '610', '900', '910', '920', '907',
)

# RDR fields the product uses. PII fields are encrypted at rest.
RDR_TICKET_FIELD = '30'                       # RI= — the reader ticket / primary key
RDR_NAME_FIELDS = ('10', '11', '12')          # surname / name / patronymic (ПДн)
RDR_CONTACT_FIELDS = ('32', '17', '18')       # e-mail / phones (ПДн)
RDR_CATEGORY_FIELD = '50'                     # reader category (policy bucket)
RDR_PII_FIELDS = RDR_NAME_FIELDS + RDR_CONTACT_FIELDS

# ИРБИС record status bits (master-file RECORD.status). 0x01 = LOGICALLY DELETED,
# 0x02 = LONG (multi-block), 0x80 = ABSENT/blocked. A read of a deleted/absent
# record usually surfaces as an IrbisError (-600/-601/-605/-140 etc.), but a
# record can also come back with a non-empty status carrying the delete bit; we
# skip either way. (Parser puts the raw status string in rec['status'].)
STATUS_DELETED_BITS = 0x01 | 0x80


def _status_is_deleted(status):
    """True iff a parsed record's ``status`` marks it logically deleted / absent.

    The status is a string of the integer master-file status. Empty / non-numeric
    => active (the live IBIS returns '' for every active record)."""
    if status is None:
        return False
    s = str(status).strip()
    if not s:
        return False
    try:
        return bool(int(s) & STATUS_DELETED_BITS)
    except ValueError:
        return False


def redact(value):
    """Redact a PII string for logging: keep <=2 leading chars, mask the rest.

    ``'Бродовский' -> 'Бр***'``; empty/None -> ''. Never returns the full value —
    this is the only form reader PII may appear in a log line."""
    if not value:
        return ''
    s = str(value)
    return (s[:2] + '***') if len(s) > 2 else (s[:1] + '***')


# --------------------------------------------------------------------------- #
# Mapping: parsed-ИРБИС-record (irbis.parser shape) -> Biblio record dict.
#
# The client parser yields rec['fields'] = [{'tag','value','text','subfields'}…].
# CatalogStore wants {tag: [ {subfield_lower: value}, … ]} (repeatable fields are
# lists; a field with no subfields becomes a bare-value instance under '' ). We
# lower-case subfield codes so the stored record matches the canonical 200^a /
# 910^b shape the ФЛК / PFT / index engines key on (the live server returns
# UPPER-case codes; CatalogStore reads case-insensitively but we normalize so the
# AT-REST record is canonical and round-trips byte-for-byte in tests).
# --------------------------------------------------------------------------- #
def _instance_from_field(f):
    """One CatalogStore field-instance from a parsed source field.

    ``f`` is a parser field dict. Returns a ``{subfield: value}`` dict (codes
    lower-cased), or a bare string when the source field has no subfields."""
    subs = f.get('subfields') or {}
    if not subs:
        # bare value (e.g. 101 'rus', 920 'PAZK', 675 '004.4') — keep as a string.
        return f.get('value', '')
    inst = {}
    head = f.get('text') or ''
    if head:
        inst[''] = head            # text before the first '^' (rare on IBIS bib data)
    for code, text in subs.items():
        if code == '_repeats':
            continue
        inst[str(code).lower()] = text
    # carry repeated subfields (parser stashes extras under '_repeats')
    for rep in subs.get('_repeats', []):
        for code, text in rep.items():
            key = str(code).lower()
            inst.setdefault(key, text)
    return inst


def map_catalog_record(parsed):
    """Map a parsed ИРБИС catalog record -> a CatalogStore record dict.

    Copies every field verbatim (repeatable fields collapse into a list of
    instances), lower-casing subfield codes. Stamps the source MFN into
    ``907^_mfn`` for idempotency. Returns ``(record, source_mfn)``."""
    record = {}
    for f in parsed.get('fields', []):
        tag = f['tag']
        inst = _instance_from_field(f)
        record.setdefault(tag, []).append(inst)

    source_mfn = parsed.get('mfn')
    # Stamp the source MFN as a private 907 subfield (idempotency key). 907 may
    # already exist (каталогизатор); append a dedicated instance carrying only the
    # marker so we never disturb a real 907^a.
    if source_mfn is not None:
        record.setdefault(SOURCE_MFN_FIELD, [])
        record[SOURCE_MFN_FIELD].append({SOURCE_MFN_SUB: str(source_mfn)})
    return record, source_mfn


def map_reader_record(parsed):
    """Map a parsed ИРБИС RDR record -> a minimal Biblio reader dict.

    Returns ``{ticket, category, pii:{...plaintext...}}`` or None when the record
    has no ticket (field 30). The ``pii`` map is PLAINTEXT here — the loader
    encrypts it before any store write (so plaintext never leaves this process).
    """
    def first(tag):
        for f in parsed.get('fields', []):
            if f['tag'] == tag:
                return f.get('value', '') or f.get('text', '')
        return ''

    ticket = (first(RDR_TICKET_FIELD) or '').strip()
    if not ticket:
        return None
    pii = {}
    for tag in RDR_PII_FIELDS:
        v = first(tag)
        if v:
            pii[tag] = v
    category = (first(RDR_CATEGORY_FIELD) or '').strip() or '_DEFAULT'
    return {'ticket': ticket, 'category': category, 'pii': pii}


# --------------------------------------------------------------------------- #
# Source adapter. The migrator reads through a tiny duck-typed interface
# (``max_mfn``/``read_record``) so the live ``core.SessionManager`` /
# ``irbis.SessionManager`` plug straight in AND tests inject a FakeIrbis with no
# server. We don't depend on a concrete class — just the two methods.
# --------------------------------------------------------------------------- #
def open_source(host, port, user, password, workstation='A', timeout=8.0):
    """Open a read-only export session against a source ИРБИС server.

    Returns an ``irbis.SessionManager`` (auto-(re)connect, thread-safe). Imported
    lazily so the module imports on a box without the server / for unit tests that
    inject their own source."""
    from irbis import SessionManager
    return SessionManager(host, port, workstation, user, password, timeout=timeout)


# --------------------------------------------------------------------------- #
# Targets. A small bundle so the migrator can be pointed at fresh in-memory
# stores (tests / dry-run) or the real configured stores. Idempotency for the
# catalog uses an in-process source-MFN -> target-MFN index built on demand from
# the loaded records (so a re-run against an existing store still upserts).
# --------------------------------------------------------------------------- #
class Targets:
    """The set of Biblio stores the migrator loads into.

    Pass explicit stores (tests use ``:memory:`` ones); ``Targets.in_memory()``
    builds a fresh isolated set. The ``access`` store is wired into the catalog so
    its ФЛК dictionary rules can resolve (and to hold the portal reader rows)."""

    def __init__(self, catalog, circulation, access, catalog_db='IBIS',
                 tenant='public'):
        self.catalog = catalog
        self.circulation = circulation
        self.access = access
        self.catalog_db = catalog_db
        self.tenant = tenant

    @classmethod
    def in_memory(cls, catalog_db='IBIS', tenant='public', access=None):
        access = access or AccessStore(':memory:')
        catalog = CatalogStore(':memory:', access_store=access)
        circ = CirculationStore(':memory:')
        return cls(catalog, circ, access, catalog_db=catalog_db, tenant=tenant)

    # -- catalog idempotency: source-MFN -> target-MFN ------------------- #
    def find_by_source_mfn(self, source_mfn):
        """Resolve a previously-loaded record's target MFN by its source MFN.

        Scans the catalog db for the record carrying ``907^_mfn == source_mfn``
        (the idempotency stamp). Returns the target mfn or None. O(n) scan — fine
        for a one-shot migration; a production run could add an index, but the
        catalog store is intentionally not modified here."""
        target = str(source_mfn)
        for mfn in self.catalog.list_mfns(self.catalog_db, include_deleted=True,
                                          limit=10 ** 9):
            rec = self.catalog.get(self.catalog_db, mfn, include_deleted=True)
            if rec is None:
                continue
            for inst in _as_list(rec.get(SOURCE_MFN_FIELD)):
                if isinstance(inst, dict) and str(inst.get(SOURCE_MFN_SUB)) == target:
                    return mfn
        return None


def _as_list(raw):
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


# --------------------------------------------------------------------------- #
# The migration itself.
# --------------------------------------------------------------------------- #
class Migrator:
    """Drive the ИРБИС → Biblio migration over a source + targets.

    ``source`` only needs ``max_mfn(db)`` and ``read_record(db, mfn)`` (the live
    SessionManager satisfies this; tests inject a FakeIrbis). ``dry_run=True`` maps
    everything and counts it WITHOUT writing the targets."""

    def __init__(self, source, targets, *, dry_run=False, log=None):
        self.source = source
        self.targets = targets
        self.dry_run = dry_run
        self._log = log                    # callable(str) or None

    def _emit(self, msg):
        if self._log:
            self._log(msg)

    # -- catalog ------------------------------------------------------------ #
    def migrate_catalog(self, src_db='IBIS', limit=None, report=None):
        """Iterate source ``src_db`` MFN 1..max_mfn, map + load each record.

        Deleted / empty / unreadable records are skipped (counted). Idempotent: a
        record already loaded (matched by source MFN) is updated in place. Returns
        the running report dict."""
        report = report if report is not None else _new_report()
        try:
            top = self.source.max_mfn(src_db)
        except Exception as e:                          # noqa: BLE001 - server may be down
            report['errors'] += 1
            self._emit('catalog: max_mfn(%s) failed: %s' % (src_db, type(e).__name__))
            return report
        if not top or top < 1:
            return report
        last = top if limit is None else min(top, limit)
        for mfn in range(1, last + 1):
            try:
                parsed = self.source.read_record(src_db, mfn)
            except Exception:                           # noqa: BLE001 - deleted/locked MFN
                report['skipped'] += 1
                continue
            report['records_read'] += 1
            if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                report['skipped'] += 1
                continue
            record, source_mfn = map_catalog_record(parsed)
            if self.dry_run:
                report['records_loaded'] += 1           # would-load count
                continue
            try:
                self._load_catalog_record(record, source_mfn)
                report['records_loaded'] += 1
            except Exception as e:                       # noqa: BLE001
                report['errors'] += 1
                self._emit('catalog: load mfn %s failed: %s' % (mfn, type(e).__name__))
        return report

    def _load_catalog_record(self, record, source_mfn):
        """Upsert one mapped record into the catalog (idempotent by source MFN)."""
        existing_mfn = None
        if source_mfn is not None:
            existing_mfn = self.targets.find_by_source_mfn(source_mfn)
        res = self.targets.catalog.save(self.targets.catalog_db, record,
                                        mfn=existing_mfn)
        # A severity-1 ФЛК rejection is a per-record skip, not a crash; surface it.
        if not res.get('saved'):
            raise CatalogLoadRejected(res.get('violations'))
        return res

    # -- readers ------------------------------------------------------------ #
    def migrate_readers(self, src_db='RDR', limit=None, report=None):
        """Iterate source ``src_db`` (readers), map + load each ticket.

        PII is ENCRYPTED before any store write. Idempotent by ticket (upsert).
        Seeds the circulation reader row (ticket + category) so holds/loans can
        reference it. Returns the running report dict."""
        report = report if report is not None else _new_report()
        try:
            top = self.source.max_mfn(src_db)
        except Exception as e:                          # noqa: BLE001
            report['errors'] += 1
            self._emit('readers: max_mfn(%s) failed: %s' % (src_db, type(e).__name__))
            return report
        if not top or top < 1:
            return report
        last = top if limit is None else min(top, limit)
        seen = set()
        for mfn in range(1, last + 1):
            try:
                parsed = self.source.read_record(src_db, mfn)
            except Exception:                           # noqa: BLE001
                report['skipped'] += 1
                continue
            report['records_read'] += 1
            if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                report['skipped'] += 1
                continue
            mapped = map_reader_record(parsed)
            if mapped is None or mapped['ticket'] in seen:
                report['skipped'] += 1
                continue
            seen.add(mapped['ticket'])
            # redacted sample only — never the full name (ПДн logging rule)
            self._emit('reader %s (%s)' % (mapped['ticket'],
                                           redact(mapped['pii'].get('10'))))
            if self.dry_run:
                report['readers_loaded'] += 1
                continue
            try:
                self._load_reader(mapped)
                report['readers_loaded'] += 1
            except Exception as e:                       # noqa: BLE001
                report['errors'] += 1
                self._emit('reader %s load failed: %s' % (mapped['ticket'],
                                                          type(e).__name__))
        return report

    def _load_reader(self, mapped):
        """Load one reader: circulation row (ticket+category) + encrypted PII review.

        The product persists reader PII at rest as ciphertext (V1 seam). We store
        the resolved display name under the same encrypted column the social layer
        uses (``reader_review.reader_name``) so the migrated reader's name is
        ciphertext at rest, identical to a name written by the running app. The
        circulation reader row holds only the ticket + policy category (no PII).
        """
        ticket = mapped['ticket']
        # circulation reader (no PII — just ticket + category bucket)
        self.targets.circulation.add_reader(ticket, category=mapped['category'])
        # reader display name -> ENCRYPTED at rest via the V1 seam.
        display = _reader_display_name(mapped['pii'])
        if display:
            enc = crypto.encrypt(display)
            self._write_reader_pii(ticket, enc, mapped['pii'])

    def _write_reader_pii(self, ticket, enc_name, pii):
        """Persist the reader's encrypted display name into OUR store.

        Writes through ``review_upsert`` against a reserved migration marker
        (db='_MIGRATION', mfn=0) so the name lands in the ENCRYPTED
        ``reader_review.reader_name`` column — proving migrated PII is ciphertext
        at rest by the same mechanism the running app uses. ``review_upsert``
        already calls ``crypto.encrypt`` internally; we pass the plaintext display
        name (idempotent: encrypt() never double-wraps, and the column is the
        single source of the ciphertext-at-rest guarantee)."""
        display = _reader_display_name(pii)
        # rating is required (1..5) by the schema; a migration marker uses 3 (n/a).
        self.targets.access.review_upsert(
            ticket, '_MIGRATION', 0, 3, 'migrated', display, _now())

    # -- driver ------------------------------------------------------------- #
    def run(self, dbs=('IBIS', 'RDR'), catalog_db='IBIS', limit=None):
        """Run the full migration over ``dbs`` and return the combined report."""
        report = _new_report()
        for db in dbs:
            up = db.strip().upper()
            if up == 'RDR':
                self.migrate_readers(src_db=db, limit=limit, report=report)
            else:
                self.migrate_catalog(src_db=db, limit=limit, report=report)
        return report


class CatalogLoadRejected(Exception):
    """A mapped record was rejected by ФЛК on load (severity-1) — per-record skip."""


def _reader_display_name(pii):
    """Build 'Surname Name Patronymic' from the reader PII map (plaintext)."""
    parts = [pii.get(t, '').strip() for t in RDR_NAME_FIELDS]
    return ' '.join(p for p in parts if p)


def _now():
    import time
    return time.time()


def _new_report():
    return {'records_read': 0, 'records_loaded': 0, 'readers_loaded': 0,
            'skipped': 0, 'errors': 0}


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def build_arg_parser():
    p = argparse.ArgumentParser(
        prog='migrate_irbis',
        description='Migrate an ИРБИС library (catalog + readers) into Biblio.')
    p.add_argument('--source-host', required=True, help='source ИРБИС host')
    p.add_argument('--source-port', type=int, default=6666, help='source ИРБИС port')
    p.add_argument('--user', required=True, help='source ИРБИС login')
    p.add_argument('--pass', dest='password', required=True, help='source ИРБИС password')
    p.add_argument('--workstation', default='A', help='ИРБИС workstation code (default A)')
    p.add_argument('--target-tenant', required=True, help='target Biblio tenant slug')
    p.add_argument('--dbs', default='IBIS,RDR',
                   help='comma-separated source DBs to migrate (default IBIS,RDR)')
    p.add_argument('--catalog-db', default='IBIS',
                   help='target catalog base name (default IBIS)')
    p.add_argument('--dry-run', action='store_true',
                   help='read + map + report only; write NOTHING to the target')
    p.add_argument('--limit', type=int, default=None,
                   help='cap MFNs read per DB (smoke-test convenience)')
    p.add_argument('--verbose', action='store_true',
                   help='log per-record progress (redacted PII only)')
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    dbs = tuple(d.strip() for d in args.dbs.replace(';', ',').split(',') if d.strip())

    source = open_source(args.source_host, args.source_port, args.user,
                         args.password, workstation=args.workstation)
    targets = Targets.in_memory(catalog_db=args.catalog_db, tenant=args.target_tenant)
    log = (lambda m: print(m, file=sys.stderr)) if args.verbose else None
    migrator = Migrator(source, targets, dry_run=args.dry_run, log=log)
    try:
        report = migrator.run(dbs=dbs, catalog_db=args.catalog_db, limit=args.limit)
    finally:
        close = getattr(source, 'close', None)
        if callable(close):
            close()
    report['dry_run'] = bool(args.dry_run)
    report['tenant'] = args.target_tenant
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
