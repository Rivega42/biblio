#!/usr/bin/env python3
"""Authority-files service — first shippable slice (gap A4, epic #188).

Self-contained sqlite store + lookup + substitution pipeline for the six
ИРБИС authority bases (ATHRA/C/S/G/U/B), unified onto one polymorphic
``authority_record`` table with JSON subfields — the model decided in
``docs/design/specs/engines/SPEC_service_authority.md`` §1 and grounded on
``docs/recon/deep/reference/databases/DB_AUTHORITY.md``.

What this module ships (SPEC §9 critical path, steps 1-3 — the search +
substitution core; plus the autoin hook of step 4, edge 6.2; merge/trees remain
later slices):

  * ``AuthorityStore`` — own sqlite tables ``authority_record`` (id, kind, db,
    data_json) + ``authority_term`` (authority_id, term) created on init.
    The term table is the projection that ports the FST dictionary (SPEC §1.3):
    every searchable string of a record is denormalised into one ``term`` row.
  * ``search(db, q)`` — prefix/substring lookup over ``authority_term`` (SPEC §2.1,
    AC-L1); empty store → empty list, never an error.
  * ``get(db, id)`` — full record (SPEC §2.2, AC-L3).
  * ``substitute(catalog_field_tag, authority_record)`` — the fill-map step of the
    substitution pipeline (SPEC §3.1 step [4]/[5], §3.2 table): returns the subfield
    patch ``{'a':…,'b':…,'g':…,'3':authority_id}`` to write into the catalog field,
    always carrying the ``^3`` link = the authority record id (DB_AUTHORITY §5.2).
  * ``AuthorityStore.autoin(catalog_field_tag, subfields)`` — the autoin hook
    (SPEC §3.4, port of ``autoin.gbl``) for the REVERSE edge «catalog → ATHR*»
    (INTEGRATION_MAP 6.2): a catalog heading (700/710/606/…) saved WITHOUT ``^3``
    is folded to an alcode, linked to an existing authority record by that alcode
    or, failing that, materialised as a fresh ``needs_review`` record. Returns
    ``(authority_id, created)`` — the id to thread into ``^3``.

Design notes (paritet with ground truth):
  * ``db`` ∈ {athra, athrc, athrs, athrg, athru, athrb} ↔ ``kind`` ∈
    {personal, corporate, subject, geographic, udc_index, bbk_index}
    (SPEC §1.1 table). ``search``/``get`` are scoped by ``db`` so a term in one
    base never leaks into another (paritet RLS isolation, AC-L5 at the db axis).
  * Catalog subfield keys are lowercase ('a','b','g','f','s','c','h','9','3') —
    the SPEC §3.2 fill-map convention (FIELD_DICTIONARY writes them ^A/^B/… in
    upper, but the JSON patch the client applies in the DynamicField is keyed by
    the lowercased letter). ``^3`` is *always* the authority id, never copied
    from the authority's own subfields (DB_AUTHORITY §5.2: catalog ^3 = number of
    the authority record).

The store accepts ``:memory:`` or a temp path so tests run with no DB server,
matching the AccessStore pattern in ``access/store.py``.
"""
import json
import sqlite3
import threading


# --------------------------------------------------------------------------- #
# db (ИРБИС authority base) <-> kind (polymorphic discriminator).  SPEC §1.1.
# --------------------------------------------------------------------------- #
DB_TO_KIND = {
    'athra': 'personal',
    'athrc': 'corporate',
    'athrs': 'subject',
    'athrg': 'geographic',
    'athru': 'udc_index',
    'athrb': 'bbk_index',
}
KIND_TO_DB = {v: k for k, v in DB_TO_KIND.items()}


# --------------------------------------------------------------------------- #
# Fill-map (SPEC §3.2).  catalog_field_tag -> spec describing which authority
# heading_210 subfields flow into which catalog subfields, plus the binding db.
#
# Catalog-side keys are lowercase letters (and '3' for the ^3 link).  Each tuple
# is (catalog_key, authority_key): copy authority.heading_210[authority_key] into
# the patch under catalog_key when present.  '3' is appended automatically by
# substitute() and is intentionally NOT in these lists (it is the record id, not
# an authority subfield — DB_AUTHORITY §5.2).
# --------------------------------------------------------------------------- #
FILL_MAP = {
    # 700/701 — 1st / other individual author.  ATHRA, prefix A=, amovf.
    #   ^a Фамилия, ^b Инициалы, ^g Расширение, ^f Даты, ^9 Признак.
    '700': {'db': 'athra', 'kind': 'personal',
            'pairs': [('a', 'a'), ('b', 'b'), ('g', 'g'), ('f', 'f'), ('9', '9')]},
    '701': {'db': 'athra', 'kind': 'personal',
            'pairs': [('a', 'a'), ('b', 'b'), ('g', 'g'), ('f', 'f'), ('9', '9')]},
    # 702 — secondary responsibility.  Role ^4 left to the operator (not filled).
    '702': {'db': 'athra', 'kind': 'personal',
            'pairs': [('a', 'a'), ('b', 'b'), ('g', 'g')]},
    # 600 — persona (about whom).  Adds aspect ^9 + dates ^f.
    '600': {'db': 'athra', 'kind': 'personal',
            'pairs': [('a', 'a'), ('b', 'b'), ('g', 'g'), ('f', 'f'), ('9', '9')]},
    # 710/711 — corporate body.  ATHRC, prefix M=, cmov.
    #   ^a Наимен., ^b Подразделение, ^c Город, ^s Страна, ^9 Тип.
    '710': {'db': 'athrc', 'kind': 'corporate',
            'pairs': [('a', 'a'), ('b', 'b'), ('c', 'c'), ('s', 's'), ('9', '9')]},
    '711': {'db': 'athrc', 'kind': 'corporate',
            'pairs': [('a', 'a'), ('b', 'b'), ('c', 'c'), ('s', 's'), ('9', '9')]},
    # 601 — corporate (about whom).
    '601': {'db': 'athrc', 'kind': 'corporate',
            'pairs': [('a', 'a'), ('b', 'b'), ('c', 'c')]},
    # 606 — subject heading.  ATHRS, prefix S=, pmov.
    #   ^a Заголовок, ^b/^c/^d Подзагол., ^g/^e/^o Геогр., ^h Хронол.
    '606': {'db': 'athrs', 'kind': 'subject',
            'pairs': [('a', 'a'), ('b', 'b'), ('c', 'c'), ('d', 'd'),
                      ('g', 'g'), ('e', 'e'), ('o', 'o'), ('h', 'h')]},
    # 607 — geographic heading.  ATHRG (via ATHRS-geo), prefix G=, gmov.
    '607': {'db': 'athrg', 'kind': 'geographic',
            'pairs': [('a', 'a'), ('b', 'b'), ('c', 'c'), ('d', 'd'),
                      ('g', 'g'), ('e', 'e'), ('o', 'o'), ('h', 'h')]},
    # 675 — UDC index.  ATHRU, prefix U=.  No ^3 link (tree/classmark, §6).
    '675': {'db': 'athru', 'kind': 'udc_index', 'link': False,
            'pairs': [('a', 'a'), ('c', 'c')]},
    # 621 — BBK index.  ATHRB, prefix U=.  No ^3 link.
    '621': {'db': 'athrb', 'kind': 'bbk_index', 'link': False,
            'pairs': [('a', 'a')]},
}


class AuthorityNotFound(Exception):
    """Raised by substitute() when handed a None / unknown authority record."""


class UnknownCatalogField(Exception):
    """Raised by substitute() when the catalog field tag has no fill-map entry."""


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS authority_record (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  kind      TEXT NOT NULL,
  db        TEXT NOT NULL,
  data_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS authority_record_db_idx ON authority_record(db);
CREATE TABLE IF NOT EXISTS authority_term (
  authority_id INTEGER NOT NULL REFERENCES authority_record(id) ON DELETE CASCADE,
  term         TEXT NOT NULL,
  term_norm    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS authority_term_norm_idx ON authority_term(term_norm);
CREATE INDEX IF NOT EXISTS authority_term_rec_idx ON authority_term(authority_id);
"""


def _norm(s):
    """Normalisation for the search projection (SPEC §1.3 term_norm): lower-case,
    collapsed whitespace.  Diacritic folding is out of scope for this slice."""
    return ' '.join(str(s).lower().split())


# --------------------------------------------------------------------------- #
# Алкод свёртки заголовка (SPEC §3.4 / §4.1 слой 1 — детерминированный
# дублетный ключ).  Минимальный порт `normalizer.fold(subfields) → alcode`:
# конкатенация значимых подполей заголовка в нормализованную строку.  Это ключ,
# по которому autoin (§3.4) находит уже существующую авторитетную запись либо
# заводит новую — точное совпадение алкода == точный дубль.
#
# `pairs` берётся из FILL_MAP[catalog_tag] (каталог-подполе ⇆ авторитет-подполе),
# поэтому свёртка считается по тем же подполям, что и подстановка — заголовок,
# собранный из БО, сворачивается так же, как заголовок из авторитета.
# --------------------------------------------------------------------------- #
def fold_heading(heading, auth_keys):
    """Свернуть подполя заголовка (по ключам авторитета ``auth_keys``) в алкод.

    ``heading`` — словарь подполей (значения авторитет-подполей: 'a','b','g',…);
    ``auth_keys`` — упорядоченный список авторитет-подполей, участвующих в свёртке.
    Возвращает нормализованную строку-ключ ('' если ни одно значимое подполе не
    заполнено).  Порядок ключей фиксирован, поэтому ключ детерминирован."""
    parts = []
    for k in auth_keys:
        v = heading.get(k)
        if v:
            parts.append(_norm(v))
    return ' | '.join(p for p in parts if p)


def _auth_fold_keys_for_kind(kind):
    """Авторитет-подполя свёртки для данного ``kind``: берём ``pairs`` первого
    каталог-поля FILL_MAP с этим kind (например personal → 700 → a/b/g/f/9).
    Так свёртка записи-авторитета и свёртка заголовка из БО считаются по одному
    набору подполей.  Неизвестный kind → пустой список (алкод == '')."""
    for spec in FILL_MAP.values():
        if spec.get('kind') == kind:
            return [auth_key for _ck, auth_key in spec['pairs']]
    return []


class AuthorityStore:
    """Self-contained sqlite store for authority records + the term projection.

    Pass ``:memory:`` or a temp path; schema is created on init (paritet
    AccessStore).  One connection per thread (sqlite objects aren't shareable
    across threads).
    """

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

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

    # ---- write ----------------------------------------------------------- #
    def add_record(self, db, heading_210, terms=None, **extra):
        """Insert one authority record and project its search terms.

        ``db`` is one of DB_TO_KIND keys (kind is derived).  ``heading_210`` is the
        dict of accepted-heading subfields ({'a':…,'b':…,…}).  ``terms`` is an
        optional explicit list of searchable strings (ports the FST projection,
        SPEC §1.3); when omitted, the heading values are projected as terms so a
        record is always findable by its own subfield text.  ``extra`` is merged
        into the stored record (e.g. worklist, see_410, classmarks).

        Returns the new record id, which is the ``^3`` link target.
        """
        db = db.lower()
        if db not in DB_TO_KIND:
            raise ValueError('unknown authority db %r (expected one of %s)'
                             % (db, ', '.join(sorted(DB_TO_KIND))))
        kind = DB_TO_KIND[db]
        record = dict(extra)
        record['kind'] = kind
        record['db'] = db
        record['heading_210'] = dict(heading_210)
        c = self._conn()
        cur = c.execute(
            'INSERT INTO authority_record(kind, db, data_json) VALUES(?,?,?)',
            (kind, db, json.dumps(record, ensure_ascii=False)))
        rec_id = cur.lastrowid
        # write the id back into the stored JSON so get() echoes its own id
        record['id'] = rec_id
        c.execute('UPDATE authority_record SET data_json=? WHERE id=?',
                  (json.dumps(record, ensure_ascii=False), rec_id))
        # ---- term projection (FST port, SPEC §1.3) ----
        if terms is None:
            terms = [v for v in heading_210.values() if v]
        seen = set()
        for t in terms:
            if not t:
                continue
            tn = _norm(t)
            if tn in seen:
                continue
            seen.add(tn)
            c.execute('INSERT INTO authority_term(authority_id, term, term_norm) '
                      'VALUES(?,?,?)', (rec_id, str(t), tn))
        c.commit()
        return rec_id

    # ---- read ------------------------------------------------------------ #
    def get(self, db, rec_id):
        """Full authority record (dict) for ``rec_id`` within ``db``, or None.

        Scoped by ``db`` so a personal-author id can't be fetched as a subject
        (paritet base isolation).  SPEC §2.2 / AC-L3.
        """
        r = self._conn().execute(
            'SELECT data_json FROM authority_record WHERE id=? AND db=?',
            (rec_id, db.lower())).fetchone()
        return json.loads(r['data_json']) if r else None

    def search(self, db, q, mode='prefix', limit=20):
        """Lookup over the term projection within ``db``.  SPEC §2.1, AC-L1.

        ``mode='prefix'`` matches term_norm by right-truncation (paritet
        словарного поиска ``A=ТОЛС…``); ``mode='substring'`` matches anywhere.
        Empty store / no hit → ``[]`` (never an error — AC-L1).  Each hit is the
        full record dict with an added ``'matched'`` term for UI display, and a
        ready ``'fill_hint'`` echo of the heading (SPEC §2.1 ``fill`` block,
        AC-L4 — client doesn't reconstruct subfields).
        """
        qn = _norm(q)
        if not qn:
            return []
        if mode == 'substring':
            pattern = '%' + qn.replace('%', r'\%').replace('_', r'\_') + '%'
        else:  # prefix (default)
            pattern = qn.replace('%', r'\%').replace('_', r'\_') + '%'
        rows = self._conn().execute(
            "SELECT DISTINCT t.authority_id AS aid, r.data_json AS data_json "
            "FROM authority_term t JOIN authority_record r ON r.id = t.authority_id "
            "WHERE r.db=? AND t.term_norm LIKE ? ESCAPE '\\' "
            "ORDER BY t.authority_id LIMIT ?",
            (db.lower(), pattern, limit)).fetchall()
        hits = []
        for row in rows:
            rec = json.loads(row['data_json'])
            # find which concrete term matched (for the "see_from"/display hint)
            mt = self._conn().execute(
                "SELECT term FROM authority_term WHERE authority_id=? "
                "AND term_norm LIKE ? ESCAPE '\\' ORDER BY length(term) LIMIT 1",
                (row['aid'], pattern)).fetchone()
            rec['matched'] = mt['term'] if mt else None
            rec['fill_hint'] = dict(rec.get('heading_210', {}))
            hits.append(rec)
        return hits

    # ---- autoin (SPEC §3.4, порт autoin.gbl — обратное ребро 6.2) --------- #
    def find_by_alcode(self, db, alcode):
        """Найти id принятой авторитетной записи по алкоду свёртки в ``db``.

        Сканирует записи базы и сравнивает их собственный алкод (свёртка
        heading_210 по подполям FILL_MAP) с ``alcode``.  Возвращает id первого
        совпадения или None.  Это слой-1 дедупликации (SPEC §4.1): точное
        совпадение алкода == уже существующая запись."""
        if not alcode:
            return None
        db = db.lower()
        kind = DB_TO_KIND.get(db)
        # авторитет-подполя свёртки берём по первому каталог-полю этого kind.
        auth_keys = _auth_fold_keys_for_kind(kind)
        rows = self._conn().execute(
            'SELECT id, data_json FROM authority_record WHERE db=?',
            (db,)).fetchall()
        for r in rows:
            rec = json.loads(r['data_json'])
            if fold_heading(rec.get('heading_210', {}), auth_keys) == alcode:
                return r['id']
        return None

    def autoin(self, catalog_field_tag, subfields, *, status='needs_review',
               worklist=None):
        """Авто-создать/привязать авторитетную запись по заголовку из БО.

        Порт `autoin.gbl` для **обратного** ребра «каталог → пополнение ATHR*»
        (INTEGRATION_MAP 6.2, SPEC §3.4): когда в БО сохраняется поле-заголовок
        (700/710/606/…) БЕЗ ``^3``, мы по его подполям

          1) считаем алкод свёртки (``fold_heading`` по подполям FILL_MAP);
          2) ищем существующую принятую запись с тем же алкодом →
             привязываемся к ней (без новой записи, паритет AC-S5/T9);
          3) иначе заводим новую запись (``status='needs_review'``, паритет
             autoin — «требует ревизии каталогизатором») и берём её id.

        Возвращает ``(authority_id, created)``: ``authority_id`` — номер для
        протяжки в ``^3``; ``created`` — True если создана новая запись, False
        если привязка к существующей.  Поднимает ``UnknownCatalogField`` для
        каталог-поля без fill-map и ``ValueError`` если из подполей нечего
        свернуть (пустой заголовок — нечего пополнять)."""
        tag = str(catalog_field_tag)
        spec = FILL_MAP.get(tag)
        if spec is None:
            raise UnknownCatalogField(
                'no fill-map for catalog field %r (known: %s)'
                % (tag, ', '.join(sorted(FILL_MAP))))
        db = spec['db']
        # каталог-подполе -> авторитет-подполе по fill-map: собираем heading_210
        # авторитета из подполей каталог-поля.
        heading = {}
        for catalog_key, auth_key in spec['pairs']:
            v = subfields.get(catalog_key) if isinstance(subfields, dict) else None
            if not v and isinstance(subfields, dict):
                v = subfields.get(catalog_key.upper())
            if v:
                heading[auth_key] = v
        auth_keys = [auth_key for _ck, auth_key in spec['pairs']]
        alcode = fold_heading(heading, auth_keys)
        if not alcode:
            raise ValueError(
                'autoin: пустой заголовок для поля %s — нечего пополнять' % tag)

        hit = self.find_by_alcode(db, alcode)
        if hit is not None:
            return (hit, False)

        new_id = self.add_record(
            db, heading,
            worklist=worklist or spec['kind'].upper(),
            status=status, source={'origin': 'autoin', 'catalog_field': tag})
        return (new_id, True)


# --------------------------------------------------------------------------- #
# Substitution pipeline — fill-map step (SPEC §3.1 [4]/[5], §3.2).
# --------------------------------------------------------------------------- #
def substitute(catalog_field_tag, authority_record):
    """Build the subfield patch to write into a catalog field from a chosen
    authority record (SPEC §3.1 steps map+link, §3.2 fill-map; AC-L4/AC-S1..S3).

    Returns a dict ``{catalog_subfield: value, …, '3': authority_id}`` —
    e.g. for a person in 700:
        {'a': 'Толстой', 'b': 'Л. Н.', 'g': 'Лев Николаевич', '3': '42'}

    The ``^3`` link is *always* added (= the authority record id) for fields that
    carry it, and is NEVER taken from the authority's own subfields
    (DB_AUTHORITY §5.2).  Index fields 675/621 have ``link=False`` → no ^3.

    Only fill-map subfields present (and truthy) in the authority's heading are
    written; absent subfields are simply omitted so the operator/ФЛК can fill
    role ^9 / ^4 etc. without the pipeline overwriting them (SPEC §3.2 note).

    Raises:
      AuthorityNotFound   — authority_record is None (missing authority, AC graceful).
      UnknownCatalogField — catalog_field_tag has no fill-map entry.
    """
    tag = str(catalog_field_tag)
    spec = FILL_MAP.get(tag)
    if spec is None:
        raise UnknownCatalogField(
            'no fill-map for catalog field %r (known: %s)'
            % (tag, ', '.join(sorted(FILL_MAP))))
    if authority_record is None:
        raise AuthorityNotFound(
            'no authority record supplied for catalog field %s' % tag)

    # Cross-check the authority kind against the field binding (SPEC §3.3 MODATHR).
    rec_kind = authority_record.get('kind')
    if rec_kind is not None and rec_kind != spec['kind']:
        raise AuthorityNotFound(
            'authority kind %r does not match catalog field %s (expects %r)'
            % (rec_kind, tag, spec['kind']))

    heading = authority_record.get('heading_210', {})
    patch = {}
    for catalog_key, auth_key in spec['pairs']:
        val = heading.get(auth_key)
        if val:  # omit absent/empty subfields — don't clobber operator input
            patch[catalog_key] = val

    if spec.get('link', True):
        rec_id = authority_record.get('id')
        if rec_id is None:
            raise AuthorityNotFound(
                'authority record for field %s has no id to link via ^3' % tag)
        patch['3'] = str(rec_id)
    return patch
