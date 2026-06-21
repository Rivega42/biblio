#!/usr/bin/env python3
"""Bibliographic catalog record store + CRUD — the heart of cataloging.

Gap (catalog store), epic #188. FIRST shippable slice: an own sqlite-backed store
for bibliographic records, wired to the two landed engines:

  * ФЛК (A2, ``access/flk.py``) runs on every ``save`` — a severity-1 (непреодолимая)
    violation REJECTS the write (no row touched); severity-2 (преодолимая) warnings
    are returned but the record is saved (unless ``skip_warnings`` says otherwise).
  * PFT (A1, ``access/pft.py``) renders brief / full display of a stored record via
    ``pft.eval`` over a small built-in format (overridable per call / per db).

What this module is
-------------------
A self-contained record store. Records live as JSON blobs (the engines' I1
field/subfield dict) plus a denormalized inverted index (``record_index``) so the
catalog can answer ``PREFIX=term`` queries (``T=`` title, ``A=`` author, ``K=``
keyword, ``IN=`` inventory number) without re-scanning every blob.

Record shape (the engines' I1 draft — same as ``access/flk.py`` / ``access/pft.py``)::

    {
      "200": [{"a": "Основы каталогизации", "f": "Иванова И.И."}],  # repeating field
      "700": [{"a": "Иванова И.И."}],
      "610": [{"": "каталогизация"}, {"": "библиография"}],
      "910": [{"a": "0", "b": "1024365"}],
      "101": "rus",
      "920": "PAZK",
    }

A field may be a bare string, a ``{subfield: value}`` dict, or a list of either.

Store schema (own sqlite tables, created on init)
-------------------------------------------------
``record``        — one row per bibliographic record::
    id INTEGER PK · db TEXT · mfn INTEGER (sequential per db) · data_json TEXT
    · status TEXT ('active' | 'deleted') · created REAL · updated REAL
    UNIQUE(db, mfn)

``record_index``  — the denormalized inverted index used by ``search``::
    record_id INTEGER (→record.id) · prefix TEXT ('T'|'A'|'K'|'IN') · term TEXT
    · term_norm TEXT (casefolded, for matching)

MFN assignment
--------------
``mfn`` is sequential per ``db`` (``MAX(mfn)+1``), mirroring ИРБИС master-file
record numbers. It is assigned once on first save and never reused (a logical
delete keeps the row + mfn, just flips ``status`` to 'deleted').
"""
import json
import sqlite3
import threading
import time

from access import flk
from access import pft


# --------------------------------------------------------------------------- #
# Schema. Own tables — does NOT touch the AccessStore schema. Created on init.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  db TEXT NOT NULL,
  mfn INTEGER NOT NULL,
  data_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deleted')),
  created REAL NOT NULL,
  updated REAL NOT NULL,
  UNIQUE(db, mfn)
);
CREATE INDEX IF NOT EXISTS record_db_status_idx ON record(db, status);
CREATE TABLE IF NOT EXISTS record_index (
  record_id INTEGER NOT NULL REFERENCES record(id) ON DELETE CASCADE,
  prefix TEXT NOT NULL,
  term TEXT NOT NULL,
  term_norm TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS record_index_lookup_idx ON record_index(prefix, term_norm);
CREATE INDEX IF NOT EXISTS record_index_record_idx ON record_index(record_id);
"""


# --------------------------------------------------------------------------- #
# Indexing specification. Each entry: (prefix, field, subfield) — which record
# field/subfield feeds which search prefix. subfield=None => whole-field value.
# Mirrors the ИРБИС inverted-file prefixes:
#   T=  title      <- 200^a
#   A=  author     <- 700^a (and 701^a / 710^a personal/corporate added)
#   K=  keyword    <- 610  (whole field; ИРБИС unstructured keywords)
#   IN= inventory# <- 910^b
# --------------------------------------------------------------------------- #
INDEX_SPEC = [
    ('T', '200', 'a'),
    ('A', '700', 'a'),
    ('A', '701', 'a'),
    ('A', '710', 'a'),
    ('K', '610', None),
    ('IN', '910', 'b'),
]

# The prefixes a caller may search by (used to validate / document expressions).
SEARCH_PREFIXES = ('T', 'A', 'K', 'IN')

# Default brief / full display formats (PFT). Overridable per save db or per call.
# Brief: "Author. Title / responsibility . — Lang" with graceful omission of
# absent parts. NOTE: a trailing space separates each implicitly-concatenated
# fragment so adjacent commands (``fi`` + ``v200``) don't fuse into one token.
DEFAULT_BRIEF_PFT = (
    "if p(v700^a) then v700^a, '. ' fi "
    "v200^a "
    "if p(v200^f) then ' / ', v200^f fi "
    "if p(v101) then ' . — ', v101 fi"
)
# Full: brief plus inventory numbers, on separate lines.
DEFAULT_FULL_PFT = (
    "if p(v700^a) then 'Автор: ', v700^a fi "
    "'\nЗаглавие: ', v200^a "
    "if p(v200^f) then ' / ', v200^f fi "
    "if p(v101) then '\nЯзык: ', v101 fi "
    "if p(v920) then '\nРабочий лист: ', v920 fi "
    "if p(v910^b) then '\nИнв. №: ', v910^b+| ; | fi"
)


# --------------------------------------------------------------------------- #
# Record-draft accessors. Repeatable fields are lists of instances (str|dict).
# Local copies (mirror flk/pft) so this module is self-contained — the value
# we index must agree with what the engines see.
# --------------------------------------------------------------------------- #
def _instances(record, field):
    raw = record.get(field) if record else None
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _inst_value(inst, subfield):
    """Read ``subfield`` from one instance. subfield=None => whole-field value."""
    if isinstance(inst, dict):
        if subfield is None or subfield == '':
            if inst.get(''):
                return inst['']
            if inst.get('value'):
                return inst['value']
            return ''.join(str(v) for v in inst.values())
        return (inst.get(subfield) or inst.get(subfield.lower())
                or inst.get(subfield.upper()) or '')
    return inst if (subfield is None or subfield == '') else ''


def _field_values(record, field, subfield=None):
    """All non-empty instance values of ``field`` (optionally a subfield)."""
    out = []
    for inst in _instances(record, field):
        v = _inst_value(inst, subfield)
        if v:
            out.append(str(v))
    return out


def _norm(term):
    """Normalize a term for matching (casefold + trim). ИРБИS inverted terms are
    matched case-insensitively; we keep the original ``term`` for display."""
    return (term or '').strip().casefold()


# --------------------------------------------------------------------------- #
# Search-expression parsing. ``PREFIX=term`` (e.g. ``T=каталог``, ``A=Иванова``).
# A bare term with no recognized prefix is treated as a title (``T=``) search.
# --------------------------------------------------------------------------- #
def parse_expr(expr):
    """Parse ``PREFIX=term`` -> (prefix, term). Unknown/absent prefix => ('T', expr).

    The prefix match is case-insensitive and tolerant of a trailing '='
    (``T=``/``t=``). A bare string with no '=' searches titles."""
    if not expr:
        return ('T', '')
    s = expr.strip()
    if '=' in s:
        pre, term = s.split('=', 1)
        pre = pre.strip().upper()
        if pre in SEARCH_PREFIXES:
            return (pre, term.strip())
    return ('T', s)


class CatalogError(Exception):
    """A catalog operation error (record not found, etc.)."""


class CatalogStore:
    """Own sqlite-backed bibliographic record store + CRUD.

    Parameters
    ----------
    db_path : str
        sqlite path. Use ``':memory:'`` or a temp file in tests.
    access_store : object | None
        Optional A5 vocabulary store passed to ФЛК so dictionary rules (language
        / worklist codes) can validate against the seeded vocabularies. When None,
        those rules no-op (the engine returns no violation it can't substantiate).
    brief_pft / full_pft : str | None
        Override the default brief / full display formats (PFT bodies).
    """

    def __init__(self, db_path=':memory:', access_store=None,
                 brief_pft=None, full_pft=None):
        self.db_path = db_path
        self.access_store = access_store
        self.brief_pft = brief_pft or DEFAULT_BRIEF_PFT
        self.full_pft = full_pft or DEFAULT_FULL_PFT
        self._local = threading.local()
        self.ensure_schema()

    # ---- connection / schema ---- #
    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ------------------------------------------------------------------- #
    # Validation (ФЛК A2 on save). Returns the engine result dict
    # {overallSeverity, canSave, violations:[...]}.
    # ------------------------------------------------------------------- #
    def validate(self, record, *, phase='save', current_mfn=None,
                 tenant_overrides=None):
        """Run ФЛК over ``record`` for ``phase`` (default the full ``save`` run).

        The A5 vocabulary store is threaded through so dictionary rules resolve
        against the seeded vocabularies; the inverted index is wired as the ФЛК
        ``dup_index`` so the (carried) duplicate-inventory rule can fire."""
        return flk.validate(
            record, phase=phase, store=self.access_store,
            current_mfn=current_mfn, dup_index=self._dup_index,
            tenant_overrides=tenant_overrides)

    def _dup_index(self, index, value, current_mfn):
        """ФЛК duplicate-predicate hook: does another ACTIVE record carry this
        inverted term? ``index`` is the ИРБИS index code (e.g. 'IN='); we map it
        to our internal prefix and look it up. Returns a list of other mfns."""
        prefix = (index or '').rstrip('=').upper()
        if prefix not in SEARCH_PREFIXES:
            return []
        # current_mfn is the db-scoped mfn being saved; without a db we can't
        # scope, so dedup across all dbs on the term (conservative — a warning).
        rows = self._conn().execute(
            '''SELECT r.mfn, r.db FROM record_index ri
               JOIN record r ON r.id = ri.record_id
               WHERE ri.prefix=? AND ri.term_norm=? AND r.status='active' ''',
            (prefix, _norm(value))).fetchall()
        return [r['mfn'] for r in rows if r['mfn'] != current_mfn]

    # ------------------------------------------------------------------- #
    # Indexing (extract inverted terms from a record).
    # ------------------------------------------------------------------- #
    def index_terms(self, record):
        """Extract ``[(prefix, term), ...]`` from a record per ``INDEX_SPEC``.

        Public so a caller (or a reindex job) can preview what a record will be
        findable by. Duplicate (prefix, normalized-term) pairs are collapsed."""
        seen = set()
        out = []
        for prefix, field, subfield in INDEX_SPEC:
            for term in _field_values(record, field, subfield):
                key = (prefix, _norm(term))
                if key in seen or not _norm(term):
                    continue
                seen.add(key)
                out.append((prefix, term))
        return out

    def _reindex(self, conn, record_id, record):
        conn.execute('DELETE FROM record_index WHERE record_id=?', (record_id,))
        rows = [(record_id, prefix, term, _norm(term))
                for prefix, term in self.index_terms(record)]
        if rows:
            conn.executemany(
                'INSERT INTO record_index(record_id,prefix,term,term_norm) '
                'VALUES(?,?,?,?)', rows)

    # ------------------------------------------------------------------- #
    # CRUD.
    # ------------------------------------------------------------------- #
    def _next_mfn(self, conn, db):
        r = conn.execute('SELECT COALESCE(MAX(mfn),0)+1 AS n FROM record WHERE db=?',
                         (db,)).fetchone()
        return r['n']

    def _row(self, db, mfn, include_deleted=False):
        sql = 'SELECT * FROM record WHERE db=? AND mfn=?'
        if not include_deleted:
            sql += " AND status='active'"
        r = self._conn().execute(sql, (db, mfn)).fetchone()
        return r

    def save(self, db, record, *, mfn=None, skip_warnings=False,
             tenant_overrides=None):
        """Validate then upsert a record.

        Pipeline:
          1. run ФЛК (A2) — if ANY severity-1 (непреодолимая) violation, REJECT:
             return ``{id:None, mfn:None, saved:False, violations:[...]}`` and
             touch no row.
          2. otherwise upsert (insert with a fresh sequential mfn, or update the
             existing row when ``mfn`` is given) and (re)build the inverted index.

        ``skip_warnings`` is accepted for the warning-acknowledgement workflow:
        severity-2 violations never block a save in either case here (they're
        преодолимые), but the flag is surfaced in the result for the caller/UI.

        Returns ``{id, mfn, saved, violations, overallSeverity, canSave}``.
        """
        conn = self._conn()
        target_mfn = mfn
        existing = self._row(db, mfn, include_deleted=True) if mfn is not None else None

        res = self.validate(record, current_mfn=target_mfn,
                            tenant_overrides=tenant_overrides)
        violations = res['violations']
        if not res['canSave']:                         # severity-1 present -> reject
            return {
                'id': None, 'mfn': None, 'saved': False,
                'violations': violations,
                'overallSeverity': res['overallSeverity'],
                'canSave': False,
            }

        now = time.time()
        data_json = json.dumps(record, ensure_ascii=False)
        if existing is not None:
            conn.execute(
                'UPDATE record SET data_json=?, status=?, updated=? WHERE id=?',
                (data_json, 'active', now, existing['id']))
            record_id = existing['id']
            assigned_mfn = existing['mfn']
        else:
            assigned_mfn = mfn if mfn is not None else self._next_mfn(conn, db)
            cur = conn.execute(
                'INSERT INTO record(db,mfn,data_json,status,created,updated) '
                'VALUES(?,?,?,?,?,?)',
                (db, assigned_mfn, data_json, 'active', now, now))
            record_id = cur.lastrowid
        self._reindex(conn, record_id, record)
        conn.commit()
        return {
            'id': record_id, 'mfn': assigned_mfn, 'saved': True,
            'violations': violations,
            'overallSeverity': res['overallSeverity'],
            'canSave': True,
            'skippedWarnings': bool(skip_warnings and violations),
        }

    def get(self, db, mfn, include_deleted=False):
        """Return the stored record dict (the I1 draft), or None if absent."""
        r = self._row(db, mfn, include_deleted=include_deleted)
        if r is None:
            return None
        return json.loads(r['data_json'])

    def get_meta(self, db, mfn, include_deleted=True):
        """Return the row metadata (id/mfn/status/created/updated), no data."""
        r = self._row(db, mfn, include_deleted=include_deleted)
        if r is None:
            return None
        return {'id': r['id'], 'db': r['db'], 'mfn': r['mfn'],
                'status': r['status'], 'created': r['created'],
                'updated': r['updated']}

    def delete(self, db, mfn):
        """Logical delete: flip status to 'deleted' and drop the inverted index
        (so it vanishes from search) while keeping the row + mfn. Returns True if
        a record was deleted, False if it wasn't active/found."""
        conn = self._conn()
        r = self._row(db, mfn, include_deleted=False)
        if r is None:
            return False
        conn.execute("UPDATE record SET status='deleted', updated=? WHERE id=?",
                     (time.time(), r['id']))
        conn.execute('DELETE FROM record_index WHERE record_id=?', (r['id'],))
        conn.commit()
        return True

    def undelete(self, db, mfn):
        """Restore a logically-deleted record and rebuild its index."""
        conn = self._conn()
        r = self._row(db, mfn, include_deleted=True)
        if r is None or r['status'] != 'deleted':
            return False
        record = json.loads(r['data_json'])
        conn.execute("UPDATE record SET status='active', updated=? WHERE id=?",
                     (time.time(), r['id']))
        self._reindex(conn, r['id'], record)
        conn.commit()
        return True

    # ------------------------------------------------------------------- #
    # Search.
    # ------------------------------------------------------------------- #
    def search(self, db, expr, limit=20, offset=0):
        """Search ``db`` by a ``PREFIX=term`` expression.

        Looks the normalized term up in ``record_index`` (only ACTIVE records are
        indexed), returns ``{total, items:[{mfn, brief, ...}]}`` with a brief
        display rendered via PFT (A1). ``limit``/``offset`` page the items; ``total``
        is the full match count.
        """
        prefix, term = parse_expr(expr)
        term_norm = _norm(term)
        conn = self._conn()
        # total distinct matching records
        total = conn.execute(
            '''SELECT COUNT(DISTINCT r.id) AS n FROM record_index ri
               JOIN record r ON r.id = ri.record_id
               WHERE r.db=? AND r.status='active'
                 AND ri.prefix=? AND ri.term_norm=?''',
            (db, prefix, term_norm)).fetchone()['n']
        rows = conn.execute(
            '''SELECT DISTINCT r.id, r.mfn, r.data_json FROM record_index ri
               JOIN record r ON r.id = ri.record_id
               WHERE r.db=? AND r.status='active'
                 AND ri.prefix=? AND ri.term_norm=?
               ORDER BY r.mfn LIMIT ? OFFSET ?''',
            (db, prefix, term_norm, limit, offset)).fetchall()
        items = []
        for r in rows:
            record = json.loads(r['data_json'])
            items.append({
                'mfn': r['mfn'],
                'brief': self._render(self.brief_pft, record, r['mfn']),
            })
        return {'total': total, 'items': items, 'prefix': prefix, 'term': term}

    # ------------------------------------------------------------------- #
    # Display (PFT A1 render).
    # ------------------------------------------------------------------- #
    def _render(self, fmt, record, mfn):
        out = pft.eval(fmt, record, {'mfn': mfn})
        # Defensive projection: if a format yields nothing (e.g. a record with no
        # 200^a that slipped past as a soft warning), fall back to a plain
        # title/author projection so brief is never empty for a real record.
        if out:
            return out
        title = (_field_values(record, '200', 'a') or [''])[0]
        author = (_field_values(record, '700', 'a') or [''])[0]
        parts = [p for p in (author, title) if p]
        return '. '.join(parts)

    def brief(self, db, mfn):
        """Render the brief display of a stored record via PFT (A1), or '' if absent."""
        record = self.get(db, mfn)
        if record is None:
            return ''
        return self._render(self.brief_pft, record, mfn)

    def full(self, db, mfn):
        """Render the full display of a stored record via PFT (A1), or '' if absent."""
        record = self.get(db, mfn)
        if record is None:
            return ''
        out = pft.eval(self.full_pft, record, {'mfn': mfn})
        return out if out else self._render(self.brief_pft, record, mfn)

    # ------------------------------------------------------------------- #
    # Listing / counts (small conveniences for callers / tests).
    # ------------------------------------------------------------------- #
    def count(self, db, include_deleted=False):
        sql = 'SELECT COUNT(*) AS n FROM record WHERE db=?'
        if not include_deleted:
            sql += " AND status='active'"
        return self._conn().execute(sql, (db,)).fetchone()['n']

    def list_mfns(self, db, include_deleted=False, limit=100, offset=0):
        sql = 'SELECT mfn FROM record WHERE db=?'
        if not include_deleted:
            sql += " AND status='active'"
        sql += ' ORDER BY mfn LIMIT ? OFFSET ?'
        return [r['mfn'] for r in self._conn().execute(
            sql, (db, limit, offset)).fetchall()]
