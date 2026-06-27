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

Cross-DB seams now wired (cluster 4, all through OPTIONAL read/handle wiring —
the engine stays fully standalone and back-compatible when nothing is wired):

  * **ребро 4.4 (полный агрегат ККО, DB_VUZ §6.2).** ``Кко = экземпляры/студенты``.
    Exemplars come from IBIS (910/693 via the catalog handle, фонд = свободные +
    выданные-на-руки, see ``_binding_exemplars``); the *contingent of students*
    comes from RDR by связка (``&uf('JRDR,LN=<связка>')`` при ``ACCESSRDR=1``)
    через опциональный ``rdr`` handle, **or** falls back to поле ``68^Z`` (the
    inline ``students``, ``ACCESSRDR=0``). :meth:`provision_aggregate` rolls the
    full cross-БД свод IBIS(экз)×RDR(студенты) over a faculty/specialty/всю связку.
  * **ребро 4.1 (Move691, DB_VUZ §6.3).** :meth:`move691` переносит связку
    контингента (68/83 ``^A^L^N^C^V^O^F``) в каталог как поле **691** (привязка
    экз↔дисциплина) с ``691^I=<3^0>`` + ``^G`` тип лит. — через catalog handle
    (``catalog.save``); каталог НЕ редактируется напрямую.
  * **ребро 4.5 (архив 692, DB_VUZ §6.4).** :meth:`archive691` снимает привязку
    691 и переносит её в архивное поле **692** (``Arhiv692.gbl``) — тоже через
    catalog handle.

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
# Catalog field tags for the Move691 / архив-692 seam (DB_VUZ §6.3/§6.4).
#   691 — привязка экземпляра каталога к дисциплине+контингенту (связка).
#   692 — архив книгообеспеченности (снятые/исторические привязки 691).
# 691^G (тип лит.) follows 691G.MNU: основная=Осн / дополнительная=Доп.
# --------------------------------------------------------------------------- #
FIELD_LINK = '691'         # привязка экз↔дисциплина (Move691.gbl)
FIELD_ARCHIVE = '692'      # архив КО (Arhiv692.gbl / GlobArhiv)
KIND_691G = {KIND_MAIN: 'Осн', KIND_EXTRA: 'Доп'}  # 691^G value per 691G.MNU


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
  fili TEXT NOT NULL DEFAULT '',        -- 68/83 ^L филиал (для связки 691)
  name TEXT NOT NULL DEFAULT '',
  UNIQUE(faculty_id, napr, spec, vid, form, fili)
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
CREATE TABLE IF NOT EXISTS bp_enrollment (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student TEXT NOT NULL,                 -- RDR билет (RI=), поле 90 контингент
  discipline_id INTEGER NOT NULL REFERENCES bp_discipline(id) ON DELETE CASCADE,
  created REAL NOT NULL,                 -- запись на дисциплину (поле 69)
  UNIQUE(student, discipline_id)
);
CREATE INDEX IF NOT EXISTS bp_enrollment_student_idx ON bp_enrollment(student);
CREATE INDEX IF NOT EXISTS bp_enrollment_disc_idx ON bp_enrollment(discipline_id);
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
    rdr : object | None
        Optional read-only RDR (читатели) handle — the *students* side of the
        full ККО aggregate (INTEGRATION_MAP ребро 4.4, DB_VUZ §6.2). When wired
        (the ``ACCESSRDR=1`` regime) the contingent of a discipline is counted
        live from RDR by связка — ``&uf('JRDR,LN=<связка>')`` — instead of the
        inline ``68^Z`` count. Duck-typed: the engine asks
        ``rdr.count_students(linkage)`` where ``linkage`` is the связка dict
        ``{A,L,N,C,V,O,F}`` (or a ``count_by_linkage``/``students`` alias). A
        ``None`` return (or any error / no handle) degrades to the recorded
        ``68^Z`` count — the ``ACCESSRDR=0`` fallback — so the engine never
        crashes on an out-of-sync RDR (back-compat).
    kko_norm : dict | None
        Per-kind provision norm (основная/дополнительная). Defaults to
        :data:`DEFAULT_KKO_NORM` (0.5 / 0.25, SPEC E1 §2.6/§3.4). A fresh copy is
        taken so a caller mutating one engine's norms never leaks into another.
    """

    def __init__(self, db_path=':memory:', catalog=None, kko_norm=None,
                 circulation=None, rdr=None):
        self.db_path = db_path
        self.catalog = catalog
        self.circulation = circulation
        self.rdr = rdr
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
                      name='', fili=''):
        """Bind a Направление/Специальность (the связка ``^N``/``^C`` + вид/форма
        ``^V``/``^O`` + филиал ``^L``) under a faculty. Idempotent on
        (faculty, napr, spec, vid, form, fili). ``fili`` (the ``^L`` филиал) is
        optional — empty for single-campus вузы; it completes the связка
        ``^A^L^N^C^V^O^F`` that Move691 carries into каталог. Returns the
        specialty id."""
        if not self._faculty_exists(faculty_id):
            raise BookProvisionError('unknown faculty_id %r' % (faculty_id,))
        conn = self._conn()
        row = conn.execute(
            '''SELECT id FROM bp_specialty
               WHERE faculty_id=? AND napr=? AND spec=? AND vid=? AND form=?
                 AND fili=?''',
            (faculty_id, napr, spec, vid, form, fili)).fetchone()
        if row is not None:
            if name:
                conn.execute('UPDATE bp_specialty SET name=? WHERE id=?',
                             (name, row['id']))
                conn.commit()
            return row['id']
        cur = conn.execute(
            '''INSERT INTO bp_specialty(faculty_id,napr,spec,vid,form,fili,name)
               VALUES(?,?,?,?,?,?,?)''',
            (faculty_id, napr, spec, vid, form, fili, name))
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
    # Студент ↔ дисциплина (per-student enrollment, RDR 90/69) — рёбра 4.2/4.3/10.3.
    # ------------------------------------------------------------------- #
    def enroll(self, student, discipline_id):
        """Записать студента (RDR билет, поле 90 контингент) на дисциплину (69).

        Ребро 4.2: per-student связь студент↔дисциплина (а не только агрегатный
        счётчик контингента). Идемпотентно по (student, discipline_id). Возвращает
        id записи."""
        if not self._discipline_exists(discipline_id):
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        if not student:
            raise BookProvisionError('student (RDR ticket) is required')
        conn = self._conn()
        row = conn.execute(
            'SELECT id FROM bp_enrollment WHERE student=? AND discipline_id=?',
            (str(student), discipline_id)).fetchone()
        if row is not None:
            return row['id']
        cur = conn.execute(
            'INSERT INTO bp_enrollment(student,discipline_id,created) VALUES(?,?,?)',
            (str(student), discipline_id, time.time()))
        conn.commit()
        return cur.lastrowid

    def unenroll(self, student, discipline_id):
        """Снять студента с дисциплины. Возвращает True, если запись была."""
        conn = self._conn()
        cur = conn.execute(
            'DELETE FROM bp_enrollment WHERE student=? AND discipline_id=?',
            (str(student), discipline_id))
        conn.commit()
        return cur.rowcount > 0

    def student_disciplines(self, student):
        """Дисциплины студента (ребро 10.3: студент видит свои дисциплины в ЛК).

        Список строк ``bp_discipline``, на которые записан студент (поле 69
        «изучаемые дисциплины» по билету 90)."""
        rows = self._conn().execute(
            '''SELECT d.* FROM bp_discipline d
               JOIN bp_enrollment e ON e.discipline_id = d.id
               WHERE e.student=? ORDER BY d.id''', (str(student),)).fetchall()
        return [dict(r) for r in rows]

    def enrolled_count(self, discipline_id):
        """Число студентов, записанных на дисциплину (per-student контингент)."""
        return self._conn().execute(
            'SELECT COUNT(*) AS n FROM bp_enrollment WHERE discipline_id=?',
            (discipline_id,)).fetchone()['n']

    def sync_contingent_from_enrollments(self, discipline_id):
        """Пересчитать контингент дисциплины ИЗ фактических записей (рёбра 4.2/4.3):
        ``bp_discipline.students = COUNT(bp_enrollment)``, ``source='rdr'``.

        Закрывает шов «VUZ контингент ← реальные студенты 90/69» вместо ручного
        68^Z-счётчика. Возвращает новый контингент."""
        n = self.enrolled_count(discipline_id)
        self.set_contingent(discipline_id, n, source='rdr')
        return n

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
    # Студенты (контингент) — the RDR side of the full ККО aggregate.
    #   RDR by связка (ACCESSRDR=1, &uf('JRDR,LN=<связка>')) when an rdr handle is
    #   wired, else the inline 68^Z count (ACCESSRDR=0). DB_VUZ §6.2.
    # ------------------------------------------------------------------- #
    def _linkage_for(self, discipline_row):
        """The связка dict ``{A,L,N,C,V,O,F}`` of a discipline (DB_VUZ §4.1/§6.3).

        Joins дисциплина→специальность→факультет into the contingent linkage
        ``^A`` факультет / ``^L`` филиал / ``^N`` направление / ``^C`` спец /
        ``^V`` вид / ``^O`` форма / ``^F`` семестр — the key Move691 carries into
        каталог and the key RDR is counted by (``JRDR,LN=<связка>``)."""
        sp = self._conn().execute(
            'SELECT * FROM bp_specialty WHERE id=?',
            (discipline_row['specialty_id'],)).fetchone()
        fac = self._conn().execute(
            'SELECT * FROM bp_faculty WHERE id=?',
            (sp['faculty_id'],)).fetchone() if sp is not None else None
        return {
            'A': (fac['code'] if fac is not None else ''),
            'L': (sp['fili'] if sp is not None else ''),
            'N': (sp['napr'] if sp is not None else ''),
            'C': (sp['spec'] if sp is not None else ''),
            'V': (sp['vid'] if sp is not None else ''),
            'O': (sp['form'] if sp is not None else ''),
            'F': str(discipline_row['semester'] or ''),
        }

    def _students_from_rdr(self, linkage):
        """Count students from the RDR handle by связка (None if no opinion).

        Read-only probe of the optional ``rdr`` handle (the ``ACCESSRDR=1`` path,
        ``&uf('JRDR,LN=<связка>')``). Duck-typed: tries ``count_students`` /
        ``count_by_linkage`` / ``students`` in turn. Returns the count, or ``None``
        when no handle is wired / it has no opinion / it errors — so the caller
        degrades cleanly to the 68^Z fallback (``ACCESSRDR=0``)."""
        if self.rdr is None:
            return None
        for name in ('count_students', 'count_by_linkage', 'students'):
            probe = getattr(self.rdr, name, None)
            if probe is None:
                continue
            try:
                n = probe(dict(linkage))
            except Exception:
                return None
            if n is None:
                return None
            return max(0, int(n))
        return None

    def _students_for(self, discipline_row):
        """Resolve a discipline's contingent → ``(students, source)`` (DB_VUZ §6.2).

        RDR by связка when an ``rdr`` handle is wired and has an opinion
        (``source='rdr'``, ``ACCESSRDR=1``); otherwise the inline ``68^Z`` count
        recorded on the discipline (``source='68z'``, ``ACCESSRDR=0``). This is the
        students side of the full cross-БД ККО aggregate IBIS(экз)×RDR(студенты)."""
        n = self._students_from_rdr(self._linkage_for(discipline_row))
        if n is not None:
            return n, 'rdr'
        return max(0, int(discipline_row['students'] or 0)), '68z'

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
        # Контингент: RDR by связка (ACCESSRDR=1) when an rdr handle is wired,
        # else the recorded 68^Z count (ACCESSRDR=0). The live source overrides
        # the stored students_source so the report is honest about ACCESSRDR.
        students, students_source = self._students_for(d)
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
            'students': students, 'students_source': students_source,
            'total_exemplars': total_exemplars,
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
    # Полный кросс-БД агрегат ККО IBIS(экз)×RDR(студенты) — ребро 4.4.
    # ------------------------------------------------------------------- #
    def provision_aggregate(self, faculty_id=None, specialty_id=None,
                            normalize=False):
        """Full cross-БД ККО aggregate IBIS(экз)×RDR(студенты) over the связка.

        The sweep that closes ребро 4.4 «полный агрегат»: it rolls EVERY discipline
        in scope, pulling exemplars from the catalog (IBIS 910/693 фонд, on-hand
        included) and students from RDR by связка (``ACCESSRDR=1``) or the ``68^Z``
        fallback (``ACCESSRDR=0``) — DB_VUZ §6.2. Scope is the whole tenant by
        default, one ``faculty_id``, or one ``specialty_id``.

        Two aggregate coefficients are reported (both real, neither replaces the
        other):

          * ``aggregate_kko`` — фонд-weighted ``Σэкз / Σстуд`` over disciplines
            with students > 0 (the «сколько экземпляров на одного студента» свод;
            zero-contingent disciplines carry no students and are excluded from the
            ratio, mirroring the NULL policy);
          * ``average_kko`` — the mean of the disciplines' (non-NULL) average Кко
            (SPEC E1 §2.4), so an over-stocked discipline cannot mask a deficit.

        Returns a dict::

            {scope, faculty_id, specialty_id,
             disciplines, total_disciplines,
             total_exemplars, total_students, students_sources,
             aggregate_kko, average_kko,
             under_provisioned:[...], total_shortfall}
        """
        disc_ids = self._scope_discipline_ids(faculty_id, specialty_id)
        total_exemplars = 0
        total_students = 0
        disc_avgs = []
        under = []
        total_shortfall = 0
        students_sources = {'rdr': 0, '68z': 0}
        for did in disc_ids:
            rep = self.discipline_provision(did, normalize=normalize)
            total_exemplars += rep['total_exemplars']
            total_students += rep['students']
            students_sources[rep['students_source']] = \
                students_sources.get(rep['students_source'], 0) + 1
            disc_avgs.append(rep['average_kko'])
            if rep['under_provisioned']:
                under.append({
                    'discipline_id': rep['discipline_id'],
                    'disc_id': rep['disc_id'], 'name': rep['name'],
                    'students': rep['students'],
                    'students_source': rep['students_source'],
                    'average_kko': rep['average_kko'],
                    'shortfall': rep['shortfall'],
                })
            total_shortfall += rep['shortfall']
        # Σэкз/Σстуд: undefined (None) when no students anywhere — NULL «нет данных»
        # rather than a misleading 0 (consistent with the per-binding policy).
        aggregate = (total_exemplars / total_students) if total_students > 0 \
            else None
        scope = ('specialty' if specialty_id is not None
                 else 'faculty' if faculty_id is not None else 'tenant')
        return {
            'scope': scope, 'faculty_id': faculty_id,
            'specialty_id': specialty_id,
            'disciplines': disc_ids, 'total_disciplines': len(disc_ids),
            'total_exemplars': total_exemplars,
            'total_students': total_students,
            'students_sources': students_sources,
            'aggregate_kko': aggregate,
            'average_kko': average_kko(disc_avgs, normalize=normalize),
            'under_provisioned': under, 'total_shortfall': total_shortfall,
        }

    def _scope_discipline_ids(self, faculty_id, specialty_id):
        """Discipline ids in scope for the aggregate (tenant / faculty / specialty)."""
        conn = self._conn()
        if specialty_id is not None:
            if not self._specialty_exists(specialty_id):
                raise BookProvisionError('unknown specialty_id %r' % (specialty_id,))
            rows = conn.execute(
                'SELECT id FROM bp_discipline WHERE specialty_id=? ORDER BY id',
                (specialty_id,)).fetchall()
        elif faculty_id is not None:
            if not self._faculty_exists(faculty_id):
                raise BookProvisionError('unknown faculty_id %r' % (faculty_id,))
            rows = conn.execute(
                '''SELECT d.id FROM bp_discipline d
                   JOIN bp_specialty s ON s.id=d.specialty_id
                   WHERE s.faculty_id=? ORDER BY d.id''',
                (faculty_id,)).fetchall()
        else:
            rows = conn.execute(
                'SELECT id FROM bp_discipline ORDER BY id').fetchall()
        return [r['id'] for r in rows]

    # ------------------------------------------------------------------- #
    # Move691 (ребро 4.1) / архив 692 (ребро 4.5) — связка ↔ каталог, через
    # the optional catalog handle (catalog.get/save). The catalog is touched
    # ONLY through the handle; this engine never writes catalog rows directly.
    # ------------------------------------------------------------------- #
    def _require_catalog(self):
        if self.catalog is None:
            raise BookProvisionError(
                'move691/archive691 require a catalog handle (none wired)')
        return self.catalog

    def _resolve_mfn(self, db, binding_row, mfn):
        """The catalog mfn a binding's 691 lives on: explicit ``mfn`` or resolved
        from the holding's inventory key (``910^b`` → ``find_exemplar``)."""
        if mfn is not None:
            return mfn
        key = binding_row['inv_key'] if binding_row is not None else None
        if not key:
            return None
        finder = getattr(self.catalog, 'find_exemplar', None)
        if finder is None:
            return None
        try:
            found = finder(db, key)
        except Exception:
            return None
        return found[0] if found else None

    def _link_691(self, discipline_row, kind):
        """Build the 691 field instance from the связка (DB_VUZ §6.3).

        ``^I``=id дисциплины (3^0), ``^A^L^N^C^V^O^F``=связка контингента (omitting
        empty subfields), ``^G``=тип лит. (Осн/Доп per 691G.MNU). This is the row
        Move691.gbl writes into каталог to bind экземпляр↔дисциплина."""
        lk = self._linkage_for(discipline_row)
        inst = {'I': str(discipline_row['disc_id'])}
        for sub in ('A', 'L', 'N', 'C', 'V', 'O', 'F'):
            if lk.get(sub):
                inst[sub] = lk[sub]
        g = KIND_691G.get(kind)
        if g:
            inst['G'] = g
        return inst

    @staticmethod
    def _instances(record, tag):
        """Field ``tag`` of a record as a list of instance dicts (never None)."""
        insts = record.get(tag)
        if insts is None:
            return []
        if not isinstance(insts, list):
            insts = [insts]
        return insts

    @staticmethod
    def _same_link(inst, disc_id):
        """Does a 691/692 instance bind discipline ``disc_id`` (match on ``^I``)?"""
        if not isinstance(inst, dict):
            return False
        return str(inst.get('I') or inst.get('i') or '') == str(disc_id)

    def move691(self, discipline_id, catalog_db=None, mfn=None, kind=None):
        """Move691 (ребро 4.1): связка контингента → каталог поле **691**.

        Carries the discipline's связка (68/83 ``^A^L^N^C^V^O^F``) into каталог as
        a field-691 binding (``691^I=<3^0>`` + ``^G`` тип лит.) — the привязка
        экз↔дисциплина (DB_VUZ §6.3, ``Move691.gbl``). One 691 is written per bound
        holding the discipline carries (resolved by ``910^b`` inventory key), or to
        an explicit ``mfn`` when given. **Idempotent on ``(mfn, disc_id)``**: an
        existing 691 for the same дисциплина on that record is refreshed in place,
        never duplicated.

        The catalog is reached ONLY through the wired handle (``catalog.get`` to
        read the record, ``catalog.save`` to write it back). Raises
        :class:`BookProvisionError` when no catalog handle is wired. Returns a list
        of ``{mfn, disc_id, kind, created}`` — one per record touched."""
        cat = self._require_catalog()
        d = self._discipline_row(discipline_id)
        if d is None:
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        # Targets: each bound holding's catalog record (db + resolved mfn), or a
        # single explicit (catalog_db, mfn). Deduplicate on (db, mfn).
        targets = {}
        binds = self._conn().execute(
            'SELECT * FROM bp_binding WHERE discipline_id=? ORDER BY id',
            (discipline_id,)).fetchall()
        if mfn is not None:
            db = catalog_db or (binds[0]['catalog_db'] if binds else None)
            if db is None:
                raise BookProvisionError('move691: catalog_db required with mfn')
            # Explicit-mfn kind: the strictest bound kind (основная dominates), or
            # KIND_MAIN when nothing is bound yet.
            bk = {b['kind'] for b in binds}
            targets[(db, mfn)] = KIND_MAIN if KIND_MAIN in bk or not bk \
                else KIND_EXTRA
        else:
            for b in binds:
                db = catalog_db or b['catalog_db']
                rmfn = self._resolve_mfn(db, b, None)
                if db is None or rmfn is None:
                    continue
                targets[(db, rmfn)] = b['kind']
        if not targets:
            raise BookProvisionError(
                'move691: no catalog target resolved (need bound holdings with '
                'inv_key, or an explicit mfn)')
        results = []
        for (db, tmfn), bind_kind in targets.items():
            use_kind = kind if kind is not None else bind_kind
            record = cat.get(db, tmfn)
            if record is None:
                raise BookProvisionError(
                    'move691: catalog record %s/%r not found' % (db, tmfn))
            insts = self._instances(record, FIELD_LINK)
            link = self._link_691(d, use_kind)
            replaced = False
            for i, inst in enumerate(insts):
                if self._same_link(inst, d['disc_id']):
                    insts[i] = link
                    replaced = True
                    break
            if not replaced:
                insts.append(link)
            record[FIELD_LINK] = insts
            cat.save(db, record, mfn=tmfn)
            results.append({'mfn': tmfn, 'disc_id': d['disc_id'],
                            'kind': use_kind, 'created': not replaced})
        return results

    def archive691(self, discipline_id, db, mfn):
        """Архив 692 (ребро 4.5): снять привязку 691 → перенести в поле **692**.

        Removes the field-691 instance binding ``discipline_id`` from каталог record
        ``mfn`` and appends it to the archival field **692** (``Arhiv692.gbl`` /
        ``GlobArhiv``, DB_VUZ §6.4) — the history of снятых привязок. Reached ONLY
        through the wired catalog handle (``catalog.get``/``catalog.save``). Returns
        ``True`` when a 691 was archived, ``False`` when none matched (no-op).
        Raises :class:`BookProvisionError` when no catalog handle is wired."""
        cat = self._require_catalog()
        d = self._discipline_row(discipline_id)
        if d is None:
            raise BookProvisionError('unknown discipline_id %r' % (discipline_id,))
        record = cat.get(db, mfn)
        if record is None:
            raise BookProvisionError(
                'archive691: catalog record %s/%r not found' % (db, mfn))
        insts = self._instances(record, FIELD_LINK)
        keep = []
        moved = []
        for inst in insts:
            if self._same_link(inst, d['disc_id']):
                moved.append(inst)
            else:
                keep.append(inst)
        if not moved:
            return False
        record[FIELD_LINK] = keep
        archive = self._instances(record, FIELD_ARCHIVE)
        archive.extend(moved)
        record[FIELD_ARCHIVE] = archive
        cat.save(db, record, mfn=mfn)
        return True

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
