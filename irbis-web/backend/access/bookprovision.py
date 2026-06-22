#!/usr/bin/env python3
"""Book-provision engine (книгообеспеченность, ВУЗ) — the «связка» + ККО.

Cluster 4 of INTEGRATION_MAP (``docs/design/INTEGRATION_MAP.md``), the BD VUZ
domain (``docs/recon/deep/reference/databases/DB_VUZ.md``), business rules E1
(``docs/design/specs/rules/SPEC_business_acquisition.md`` §2). FIRST shippable
slice: a *self-contained* engine over its own sqlite store that models the
curriculum linkage («связка») Факультет→Направление→Специальность→Дисциплина,
binds recommended literature (titles) to a discipline, and computes the
book-provision coefficient (Кко = exemplars ÷ contingent) with the exact 4-cell
division-by-zero policy of SPEC E1 §2.2.

What this module is
-------------------
A standalone domain engine: pure stdlib + ``sqlite3`` (dev parity, ADR-004), no
network I/O, no new pip deps, no edits to the landed modules. It is deliberately
self-contained — it carries its own «связка» store — but when a read-only
``catalog`` handle (an :class:`access.catalog.CatalogStore`) is wired it reads
live exemplar counts (910 copies) from the catalog instead of the copy counts
recorded inline on the binding. The catalog is **read only**: this module never
writes to it.

The «связка» model (DB_VUZ §4/§5/§9, fields 83/68/691/90)
--------------------------------------------------------
The ИРБИС linkage is a chain Фак(`^A`)–Направление(`^N`)–Спец(`^C`)–Вид(`^V`)–
Форма(`^O`)–Семестр(`^F`) that binds a *discipline* (field 3 id, on a DISC
record, contingents in field 83) to a *contingent* of students (field 68 on a
VUZ record, students from RDR or the manual 68^Z), and — once literature is
bound — to the catalog (field 691, kind осн/доп from 691^G). We normalise that
into four entities:

  * :class:`Faculty`     — Факультет (the ``^A`` root of every связка).
  * :class:`Specialty`   — Направление+Специальность under a faculty
                           (the ``^N``/``^C`` link), with вид/форма (``^V``/``^O``).
  * :class:`Discipline`  — a учебная дисциплина (field 3 id) read by a specialty
                           for a given семестр (``^F``), carrying its contingent
                           of students (RDR-derived or the 68^Z fallback).
  * literature bindings  — recommended titles bound to a discipline with a *kind*
                           (``KIND_MAIN`` основная / ``KIND_EXTRA`` дополнительная),
                           the field-691 link. Each binding records the catalog
                           coordinates (db + inventory key 910^b) so a wired
                           catalog can be read for live exemplar counts, plus an
                           inline ``copies`` fallback for standalone operation.

The Кко coefficient + edge policy (SPEC E1 §2.1/§2.2, AC3/AC4)
-------------------------------------------------------------
For a discipline (its bound literature ``copies`` and its contingent of
``students``)::

    Кко = exemplars / students          (SPEC E1 §2.1)

with the explicit 4-cell division-by-zero policy of SPEC E1 §2.2 (mirroring the
SPEC business-rule convention — NULL «нет данных» is kept distinct from 0 «не
обеспечено» so archival zero-contingent bindings don't sink the average):

    students == 0 and exemplars  > 0  ->  1.0   (обеспечено; no consumers)
    students == 0 and exemplars == 0  ->  None  (NULL — нет данных; excluded
                                                  from averages)
    students  > 0 and exemplars == 0  ->  0.0   (не обеспечено; under-provision
                                                  candidate)
    students  > 0 and exemplars  > 0  ->  exemplars / students

Reports (per-discipline / per-specialty)
---------------------------------------
The average Кко over a discipline's bindings excludes NULLs (SPEC E1 §2.4),
optionally normalised to 1 (``min(Кко_i, 1)`` — over-provision of one title does
not paper over a deficit of another). A discipline is *under-provisioned* when
its average Кко is below the per-tenant ``kko_norm`` (default 0.5 for основная,
0.25 for дополнительная, SPEC E1 §2.6/§3.4) **and** it has students. The
per-specialty summary rolls those up and lists the under-provisioned disciplines
with their shortfall = ``ceil(students * kko_norm) - exemplars`` (the §2.6
дозаказ добор).
"""
import math
import sqlite3
import threading
import time


# --------------------------------------------------------------------------- #
# Literature kind — field 691^G (691G.MNU: Осн=основная / Доп=дополнительная).
# Drives the default provision norm (основная стандартно строже).
# --------------------------------------------------------------------------- #
KIND_MAIN = 'main'    # основная литература (691^G = Осн)
KIND_EXTRA = 'extra'  # дополнительная литература (691^G = Доп)

# Per-kind provision norm (SPEC E1 §2.6/§3.4 defaults; per-tenant tunable).
DEFAULT_KKO_NORM = {KIND_MAIN: 0.5, KIND_EXTRA: 0.25}


# --------------------------------------------------------------------------- #
# Schema. Own tables — does NOT touch the catalog / AccessStore schema.
# Created on init. (PG DDL parity: access/schema_bookprovision.sql.)
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS bp_faculty (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL,
  name TEXT NOT NULL DEFAULT '',
  UNIQUE(code)
);
CREATE TABLE IF NOT EXISTS bp_specialty (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  faculty_id INTEGER NOT NULL REFERENCES bp_faculty(id) ON DELETE CASCADE,
  napr TEXT NOT NULL DEFAULT '',        -- 68/83 ^N направление
  spec TEXT NOT NULL DEFAULT '',        -- 68/83 ^C специальность/профиль
  vid  TEXT NOT NULL DEFAULT '',        -- 68/83 ^V вид обучения (уровень)
  form TEXT NOT NULL DEFAULT '',        -- 68/83 ^O форма обучения
  name TEXT NOT NULL DEFAULT '',
  UNIQUE(faculty_id, napr, spec, vid, form)
);
CREATE TABLE IF NOT EXISTS bp_discipline (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  specialty_id INTEGER NOT NULL REFERENCES bp_specialty(id) ON DELETE CASCADE,
  disc_id TEXT NOT NULL,                -- field 3^0 идентификатор дисциплины
  name TEXT NOT NULL DEFAULT '',        -- field 3^a наименование
  semester TEXT NOT NULL DEFAULT '',    -- 83/68 ^F семестр(ы)
  students INTEGER NOT NULL DEFAULT 0,  -- contingent (RDR count or 68^Z)
  students_source TEXT NOT NULL DEFAULT '68z',  -- 'rdr' | '68z' (audit, AC5)
  UNIQUE(specialty_id, disc_id, semester)
);
CREATE INDEX IF NOT EXISTS bp_discipline_spec_idx
  ON bp_discipline(specialty_id);
CREATE TABLE IF NOT EXISTS bp_binding (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discipline_id INTEGER NOT NULL REFERENCES bp_discipline(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT '',       -- bound literature (book) label
  kind TEXT NOT NULL DEFAULT 'main' CHECK (kind IN ('main','extra')),  -- 691^G
  catalog_db TEXT,                      -- catalog db for the live read (910)
  inv_key TEXT,                         -- 910^b inventory key of the copy/holding
  copies INTEGER NOT NULL DEFAULT 0,    -- standalone exemplar count (no catalog)
  created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS bp_binding_disc_idx ON bp_binding(discipline_id);
"""


class BookProvisionError(Exception):
    """A book-provision operation error (unknown discipline / specialty / …)."""


# --------------------------------------------------------------------------- #
# Pure Кко math — kept module-level so it is testable in complete isolation
# (no store, no catalog), exactly the SPEC E1 §2.2 4-cell policy.
# --------------------------------------------------------------------------- #
def kko(exemplars, students):
    """Book-provision coefficient Кко = exemplars / students (SPEC E1 §2.1/§2.2).

    The 4-cell division-by-zero policy (SPEC E1 §2.2, AC4):

      * students == 0, exemplars  > 0  -> ``1.0``  (обеспечено — no consumers)
      * students == 0, exemplars == 0  -> ``None`` (NULL — нет данных)
      * students  > 0, exemplars == 0  -> ``0.0``  (не обеспечено)
      * students  > 0, exemplars  > 0  -> exemplars / students

    ``None`` (NULL) is deliberately distinct from ``0.0`` so archival
    zero-contingent bindings are excluded from averages rather than dragging
    them down. Negative inputs are clamped to 0 (defensive)."""
    e = max(0, int(exemplars or 0))
    s = max(0, int(students or 0))
    if s == 0:
        return 1.0 if e > 0 else None
    return e / s


def average_kko(values, normalize=False):
    """Average of per-binding Кко values, excluding NULL (SPEC E1 §2.4).

    NULL (``None``) values — «нет данных» — are dropped from both the sum and the
    count. With ``normalize`` each term is capped at 1 (``min(Кко_i, 1)``) so
    over-provision of one title cannot mask a deficit in another (SPEC E1 §2.4,
    AC6). Returns ``None`` when every value is NULL (nothing to average)."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    if normalize:
        present = [min(v, 1.0) for v in present]
    return sum(present) / len(present)


def shortfall(exemplars, students, kko_norm):
    """Дозаказ добор до норматива = ceil(students * kko_norm) - exemplars,
    floored at 0 (SPEC E1 §2.6). The number of copies to acquire to reach the
    provision norm; ``0`` when already at/above norm or there are no students."""
    s = max(0, int(students or 0))
    e = max(0, int(exemplars or 0))
    if s == 0:
        return 0
    need = math.ceil(s * float(kko_norm)) - e
    return need if need > 0 else 0


class BookProvisionEngine:
    """Self-contained book-provision («связка» + Кко) engine over its own store.

    Parameters
    ----------
    db_path : str
        sqlite path. Use ``':memory:'`` or a temp file in tests.
    catalog : object | None
        Optional read-only :class:`access.catalog.CatalogStore` handle. When
        wired, exemplar counts are read live from the catalog (910 copies of the
        bound holding, by inventory key 910^b) instead of the binding's inline
        ``copies``. The handle is used READ-ONLY — this engine never writes to
        the catalog. When ``None`` the engine is fully standalone (uses the
        recorded ``copies``).
    circulation : object | None
        Optional read-only :class:`access.circulation.CirculationEngine` handle —
        the Книгообеспеченность↔Книговыдача seam (INTEGRATION_MAP ребро 4.4/4.7).
        Кко counts the фонд, not just what is on the shelf: a copy currently **on
        loan** (on a student's hands) still belongs to the фонд and must count as
        provisioned. The catalog read alone undercounts it — an issued copy reads
        ``910^A=1`` (not free) → 0. With this handle wired, a bound holding the
        catalog marks issued is re-checked against circulation: if it is on an
        on-hand loan it is counted as 1 provisioned copy (not 0). The handle is
        READ-ONLY (asks ``circulation.item_on_hand``); without it the catalog read
        stands unchanged (back-compat).
    kko_norm : dict | None
        Per-kind provision norm (основная/дополнительная). Defaults to
        :data:`DEFAULT_KKO_NORM` (0.5 / 0.25, SPEC E1 §2.6/§3.4). A fresh copy is
        taken so a caller mutating one engine's norms never leaks into another.
    """

    def __init__(self, db_path=':memory:', catalog=None, kko_norm=None,
                 circulation=None):
        self.db_path = db_path
        self.catalog = catalog
        self.circulation = circulation
        self.kko_norm = dict(kko_norm) if kko_norm else dict(DEFAULT_KKO_NORM)
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
    # «Связка» construction — Факультет→Направление→Специальность→Дисциплина.
    # ------------------------------------------------------------------- #
    def add_faculty(self, code, name=''):
        """Create (or fetch) a Факультет by ``code`` (the связка ``^A`` root).
        Idempotent: re-adding the same code returns the existing id."""
        if not code:
            raise BookProvisionError('faculty code is required')
        conn = self._conn()
        row = conn.execute('SELECT id FROM bp_faculty WHERE code=?',
                           (str(code),)).fetchone()
        if row is not None:
            if name:
                conn.execute('UPDATE bp_faculty SET name=? WHERE id=?',
                             (name, row['id']))
                conn.commit()
            return row['id']
        cur = conn.execute('INSERT INTO bp_faculty(code,name) VALUES(?,?)',
                           (str(code), name))
        conn.commit()
        return cur.lastrowid

    def add_specialty(self, faculty_id, napr='', spec='', vid='', form='',
                      name=''):
        """Bind a Направление/Специальность (the связка ``^N``/``^C`` + вид/форма
        ``^V``/``^O``) under a faculty. Idempotent on
        (faculty, napr, spec, vid, form). Returns the specialty id."""
        if not self._faculty_exists(faculty_id):
            raise BookProvisionError('unknown faculty_id %r' % (faculty_id,))
        conn = self._conn()
        row = conn.execute(
            '''SELECT id FROM bp_specialty
               WHERE faculty_id=? AND napr=? AND spec=? AND vid=? AND form=?''',
            (faculty_id, napr, spec, vid, form)).fetchone()
        if row is not None:
            if name:
                conn.execute('UPDATE bp_specialty SET name=? WHERE id=?',
                             (name, row['id']))
                conn.commit()
            return row['id']
        cur = conn.execute(
            '''INSERT INTO bp_specialty(faculty_id,napr,spec,vid,form,name)
               VALUES(?,?,?,?,?,?)''',
            (faculty_id, napr, spec, vid, form, name))
        conn.commit()
        return cur.lastrowid

    def add_discipline(self, specialty_id, disc_id, name='', semester='',
                       students=0, students_source='68z'):
        """Attach a учебная дисциплина (field 3^0 ``disc_id``) read by a specialty
        for a семестр (``^F``), with its contingent of ``students``.

        ``students_source`` records where the count came from — ``'rdr'`` (live
        from RDR by связка, AccessRdr=1) or ``'68z'`` (the manual 68^Z fallback)
        — for audit (SPEC E1 §2.3, AC5). Idempotent on
        (specialty, disc_id, semester): re-adding updates name/contingent.
        Returns the discipline id."""
        if not self._specialty_exists(specialty_id):
            raise BookProvisionError('unknown specialty_id %r' % (specialty_id,))
        if not disc_id:
            raise BookProvisionError('discipline id (3^0) is required')
        if students_source not in ('rdr', '68z'):
            raise BookProvisionError('students_source must be rdr|68z')
        conn = self._conn()
        students = max(0, int(students or 0))
        row = conn.execute(
            '''SELECT id FROM bp_discipline
               WHERE specialty_id=? AND disc_id=? AND semester=?''',
            (specialty_id, str(disc_id), str(semester))).fetchone()
        if row is not None:
            conn.execute(
                '''UPDATE bp_discipline SET name=?, students=?, students_source=?
                   WHERE id=?''',
                (name, students, students_source, row['id']))
            conn.commit()
            return row['id']
        cur = conn.execute(
            '''INSERT INTO bp_discipline
               (specialty_id,disc_id,name,semester,students,students_source)
               VALUES(?,?,?,?,?,?)''',
            (specialty_id, str(disc_id), name, str(semester), students,
             students_source))
        conn.commit()
        return cur.lastrowid

    def set_contingent(self, discipline_id, students, source='68z'):
        """Update a discipline's contingent (students + source) in place.

        Models the RDR/68^Z student-count refresh (SPEC E1 §2.3): a recount from
        RDR (``source='rdr'``) or the manual 68^Z fallback (``source='68z'``)."""
        if not self._discipline_exists(discipline_id):
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        if source not in ('rdr', '68z'):
            raise BookProvisionError('source must be rdr|68z')
        conn = self._conn()
        conn.execute(
            'UPDATE bp_discipline SET students=?, students_source=? WHERE id=?',
            (max(0, int(students or 0)), source, discipline_id))
        conn.commit()

    # ------------------------------------------------------------------- #
    # Bind recommended literature to a discipline (field 691, kind 691^G).
    # ------------------------------------------------------------------- #
    def bind_literature(self, discipline_id, title, kind=KIND_MAIN,
                        copies=0, catalog_db=None, inv_key=None):
        """Bind a recommended title to a discipline (the field-691 link).

        ``kind`` is :data:`KIND_MAIN` (основная) or :data:`KIND_EXTRA`
        (дополнительная) — field 691^G. Exemplars are read either live from a
        wired catalog (pass ``catalog_db`` + ``inv_key`` = the 910^b inventory
        key of the holding) or, standalone, from the recorded ``copies``. Returns
        the binding id."""
        if not self._discipline_exists(discipline_id):
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        if kind not in (KIND_MAIN, KIND_EXTRA):
            raise BookProvisionError('kind must be %r or %r'
                                     % (KIND_MAIN, KIND_EXTRA))
        conn = self._conn()
        cur = conn.execute(
            '''INSERT INTO bp_binding
               (discipline_id,title,kind,catalog_db,inv_key,copies,created)
               VALUES(?,?,?,?,?,?,?)''',
            (discipline_id, title, kind, catalog_db, inv_key,
             max(0, int(copies or 0)), time.time()))
        conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------------- #
    # Exemplar count — from the catalog (910) when wired, else recorded copies.
    # ------------------------------------------------------------------- #
    def _binding_exemplars(self, binding_row):
        """Provisioned exemplars of one binding's literature (фонд count, not shelf).

        With a catalog handle and an ``inv_key``, read the live 910 holding by
        inventory number (``910^b``) from the catalog (READ ONLY). A copy counts
        as **provisioned** if it belongs to the фонд — that is *broader* than
        "free on the shelf":

          * free in the catalog (``910^A=0``)            -> provisioned (1);
          * issued (``910^A=1``) **but on an on-hand loan** in circulation
            -> still фонд, still provisioned (1) — when a ``circulation`` handle
            is wired (INTEGRATION_MAP ребро 4.4/4.7: Кко учитывает выданные);
          * otherwise (issued with no circulation opinion, списан, lost, …) -> 0.

        Without the circulation handle the read is the plain free/not-free check
        (back-compat). Without a catalog handle (or key) fall back to the binding's
        recorded ``copies``. Both reads are best-effort: any error degrades to the
        recorded ``copies`` so the engine never crashes on an out-of-sync catalog."""
        db = binding_row['catalog_db']
        key = binding_row['inv_key']
        if self.catalog is not None and db and key:
            try:
                # Free on the shelf → provisioned. One holding == 1 copy.
                if self.catalog.is_available(db, key):
                    return 1
                # Issued copy: still фонд if circulation has it on an on-hand loan.
                # Кко must not drop a checked-out book to 0 — it IS provided, just
                # currently in use (INTEGRATION_MAP ребро 4.4/4.7).
                if self._on_hand_in_circulation(key):
                    return 1
                return 0
            except Exception:
                pass
        return max(0, int(binding_row['copies'] or 0))

    def _on_hand_in_circulation(self, inv_key):
        """Is the copy keyed by ``inv_key`` (910^b) on an on-hand loan in circulation?

        Read-only probe of the optional circulation handle (the
        Книгообеспеченность↔Книговыдача seam). Returns False when no handle is
        wired or circulation has no opinion / errors — so the catalog read stays
        authoritative in standalone mode."""
        if self.circulation is None:
            return False
        probe = getattr(self.circulation, 'item_on_hand', None)
        if probe is None:
            return False
        try:
            return bool(probe(inv_key))
        except Exception:
            return False

    # ------------------------------------------------------------------- #
    # Reports — per-discipline / per-specialty provision summary.
    # ------------------------------------------------------------------- #
    def _kko_norm_for(self, kind):
        return self.kko_norm.get(kind, DEFAULT_KKO_NORM.get(kind, 0.5))

    def discipline_provision(self, discipline_id, normalize=False):
        """Per-discipline provision summary (coefficient, shortfall, bindings).

        For each bound title computes Кко (SPEC E1 §2.1/§2.2) over its exemplars
        and the discipline's contingent, then the average Кко excluding NULLs
        (SPEC E1 §2.4, ``normalize`` caps each term at 1). A discipline is
        ``under_provisioned`` when its average Кко is below the per-kind norm
        **and** it has students; ``shortfall`` = ceil(students*norm) - exemplars
        over the whole bound фонд (SPEC E1 §2.6).

        Returns a dict::

            {discipline_id, disc_id, name, semester, students, students_source,
             bindings:[{binding_id, title, kind, exemplars, kko}],
             average_kko, kko_norm, under_provisioned, shortfall}
        """
        d = self._discipline_row(discipline_id)
        if d is None:
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        students = int(d['students'] or 0)
        rows = self._conn().execute(
            'SELECT * FROM bp_binding WHERE discipline_id=? ORDER BY id',
            (discipline_id,)).fetchall()
        bindings = []
        kko_values = []
        total_exemplars = 0
        # The discipline's norm is the strictest over the kinds it actually
        # binds (основная 0.5 dominates дополнительная 0.25); основная default
        # when nothing is bound yet.
        kinds = {r['kind'] for r in rows} or {KIND_MAIN}
        norm = max(self._kko_norm_for(k) for k in kinds)
        for r in rows:
            ex = self._binding_exemplars(r)
            total_exemplars += ex
            coeff = kko(ex, students)
            kko_values.append(coeff)
            bindings.append({
                'binding_id': r['id'], 'title': r['title'], 'kind': r['kind'],
                'exemplars': ex, 'kko': coeff,
            })
        avg = average_kko(kko_values, normalize=normalize)
        # Under-provisioned: has consumers, average is defined and below norm.
        under = (students > 0 and avg is not None and avg < norm)
        return {
            'discipline_id': discipline_id, 'disc_id': d['disc_id'],
            'name': d['name'], 'semester': d['semester'],
            'students': students, 'students_source': d['students_source'],
            'bindings': bindings, 'average_kko': avg, 'kko_norm': norm,
            'under_provisioned': under,
            'shortfall': shortfall(total_exemplars, students, norm),
        }

    def specialty_provision(self, specialty_id, normalize=False):
        """Per-specialty rollup: every discipline's provision + the list of
        under-provisioned disciplines with their shortfall.

        Returns a dict::

            {specialty_id, disciplines:[<discipline_provision>...],
             average_kko, under_provisioned:[{discipline_id, disc_id, name,
                                              average_kko, shortfall}...],
             total_shortfall}

        ``average_kko`` is the mean of the disciplines' (non-NULL) average Кко
        (SPEC E1 §2.4: NULL disciplines excluded)."""
        if not self._specialty_exists(specialty_id):
            raise BookProvisionError('unknown specialty_id %r' % (specialty_id,))
        rows = self._conn().execute(
            'SELECT id FROM bp_discipline WHERE specialty_id=? ORDER BY id',
            (specialty_id,)).fetchall()
        disciplines = []
        under = []
        total_shortfall = 0
        disc_avgs = []
        for r in rows:
            rep = self.discipline_provision(r['id'], normalize=normalize)
            disciplines.append(rep)
            disc_avgs.append(rep['average_kko'])
            if rep['under_provisioned']:
                under.append({
                    'discipline_id': rep['discipline_id'],
                    'disc_id': rep['disc_id'], 'name': rep['name'],
                    'average_kko': rep['average_kko'],
                    'shortfall': rep['shortfall'],
                })
            total_shortfall += rep['shortfall']
        return {
            'specialty_id': specialty_id, 'disciplines': disciplines,
            'average_kko': average_kko(disc_avgs, normalize=normalize),
            'under_provisioned': under, 'total_shortfall': total_shortfall,
        }

    # ------------------------------------------------------------------- #
    # Small read helpers / existence checks.
    # ------------------------------------------------------------------- #
    def _faculty_exists(self, faculty_id):
        return self._conn().execute(
            'SELECT 1 FROM bp_faculty WHERE id=?', (faculty_id,)).fetchone() \
            is not None

    def _specialty_exists(self, specialty_id):
        return self._conn().execute(
            'SELECT 1 FROM bp_specialty WHERE id=?', (specialty_id,)).fetchone() \
            is not None

    def _discipline_exists(self, discipline_id):
        return self._conn().execute(
            'SELECT 1 FROM bp_discipline WHERE id=?', (discipline_id,)) \
            .fetchone() is not None

    def _discipline_row(self, discipline_id):
        return self._conn().execute(
            'SELECT * FROM bp_discipline WHERE id=?', (discipline_id,)).fetchone()

    def get_discipline(self, discipline_id):
        """Return the discipline row as a dict (or None)."""
        r = self._discipline_row(discipline_id)
        return dict(r) if r is not None else None

    def list_disciplines(self, specialty_id):
        """Discipline ids attached to a specialty (creation order)."""
        return [r['id'] for r in self._conn().execute(
            'SELECT id FROM bp_discipline WHERE specialty_id=? ORDER BY id',
            (specialty_id,)).fetchall()]

    def list_bindings(self, discipline_id):
        """Binding rows (as dicts) bound to a discipline (creation order)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM bp_binding WHERE discipline_id=? ORDER BY id',
            (discipline_id,)).fetchall()]
