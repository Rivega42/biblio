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
catalog can answer ``PREFIX=term`` queries without re-scanning every blob.

Indexed prefixes (the ИРБИС inverted-file словарь, CATALOGER_FUNCTIONS §3.2).
The first slice carried only ``T=``/``A=``/``K=``/``IN=`` (4 of the 63 видов
словарного поиска); this store now also inverts the highest-frequency catalog
prefixes confirmed against ``docs/recon/deep/reference/format/FIELD_DICTIONARY``:

  * ``T=``   заглавие              <- 200^a
  * ``TS=``  заглавие серии        <- 225^a
  * ``A=``   автор (физ. лицо)     <- 700^a / 701^a / 702^a
  * ``M=``   коллектив/мероприятие <- 710^a / 711^a
  * ``K=``   ключевые слова        <- 610 (ПОСЛОВНО: каждое слово 610 — термин)
  * ``S=``   предметная рубрика    <- 606^a / 605^a
  * ``GEO=`` географ. рубрика      <- 607^a
  * ``U=``   индекс УДК/ББК        <- 675 / 621 (целое поле)
  * ``V=``   вид документа         <- 900^b
  * ``G=``   год издания           <- 210^d
  * ``B=``   ISBN / ISSN           <- 10^a / 11^a
  * ``I=``   шифр документа        <- 903 (целое поле)
  * ``IN=``  инв. № / штрих-код    <- 910^b
  * ``MHR=`` место хранения        <- 910^d
  * ``AR=``  № авторитетной записи <- 700/701/710/606/607 ^3 (поиск каталога ПО
             авторитету — обратное ребро INTEGRATION_MAP 6.4 / 11.1)

Связи иерархии записей (INTEGRATION_MAP кластер 9, поиск-по-связи ``Scnt``).
В ИРБИС связь между записями каталога хранится НЕ как ссылка-по-MFN, а как
повтор ключа издания-хозяина в поле-связи зависимой записи (статьи, номера
журнала, тома). Хозяин (журнал/сборник/сводная запись многотомника) несёт свой
собственный ключ-идентичность (заглавие 200^a, ISSN 11^a, шифр 903); зависимая
запись несёт ТОТ ЖЕ ключ в поле-связи (463/461/481/963). Чтобы развести поиск по
связи (ребра 9.1/9.2/9.3), оба полюса инвертируются под двумя «зеркальными»
служебными префиксами, по которым ``linked_records`` сматчивает хозяина с детьми:

  * ``HOST=`` ключ-идентичность ИЗДАНИЯ-ХОЗЯИНА (по нему дочерние записи его
             находят) <- 200^a (заглавие), 11^a (ISSN), 903 (шифр документа)
  * ``LINK=`` ключ-ОТСЫЛКА зависимой записи на хозяина (по нему хозяин находит
             свои аналитики/номера/тома):
               9.1 статья↔журнал/сборник: 463^c (загл. хозяина), 463^j (ISSN)
               9.2 номер↔журнал:          461^c (загл. общей части), 461^j (ISSN)
               9.3 том↔сводная (многотом): 481^c (загл. приплетённого/тома)
             (963 — свод. сведения аналитики: 963^c загл., 963^j ISSN — то же
             семейство ``LINK=``, back-up к 463 для записей со сводным описанием).

Обход связи: :meth:`CatalogStore.linked_records` (db, mfn, kind). ``kind='children'``
от записи-хозяина возвращает все зависимые записи (их ``LINK=`` совпал с её
``HOST=``); ``kind='host'`` от зависимой записи возвращает её хозяина (её ``LINK=``
совпал с чьим-то ``HOST=``). Симметрия 9.1/9.2/9.3 даёт обе стороны ребра.

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
from access import authority as _authority  # substitute() — the ^3 fill-map (edge 6.1)


# --------------------------------------------------------------------------- #
# Exemplar (910) status codes — the ``910^A`` availability flag (ste.mnu).
# The Catalog↔Circulation seam (INTEGRATION_MAP edges 2.1/2.2): circulation flips
# this flag on the catalog item when a copy is issued / returned. We model only
# the two states the seam needs (free / issued); other ste.mnu codes (U=в обработке,
# C=на бронеполке, 6=списан …) are carried as opaque strings and treated as "not
# free" by the availability read.
# --------------------------------------------------------------------------- #
EXEMPLAR_FREE = '0'      # свободен — available to lend
EXEMPLAR_ISSUED = '1'    # выдан — on loan
# Any other 910^A code (U/C/6/…) is "occupied" for availability purposes.


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
# Mirrors the ИРБИС inverted-file словарь (CATALOGER_FUNCTIONS §3.2); each
# field/subfield mapping is confirmed against FIELD_DICTIONARY (the «Словарь»
# column there names the prefix per field). The original four prefixes
# (T=/A=/K=/IN=) keep their exact field bindings — back-compat preserved.
#   T=   заглавие              <- 200^a
#   TS=  заглавие серии        <- 225^a
#   A=   автор (физ. лицо)     <- 700^a / 701^a / 702^a (710 kept for back-compat)
#   M=   коллектив/мероприятие <- 710^a / 711^a
#   K=   ключевые слова        <- 610  (ПОСЛОВНО: значение 610 токенизируется на
#        слова, каждое слово — отдельный термин K=, как у ИРБИС; #270)
#   S=   предметная рубрика    <- 606^a / 605^a
#   GEO= географ. рубрика      <- 607^a
#   U=   индекс УДК/ББК        <- 675 / 621 (whole field)
#   V=   вид документа         <- 900^b
#   G=   год издания           <- 210^d
#   B=   ISBN / ISSN           <- 10^a / 11^a
#   I=   шифр документа        <- 903 (whole field)
#   IN=  инв. № / штрих-код    <- 910^b
#   MHR= место хранения экз.   <- 910^d
#   AR=  № авторитетной записи <- 700/701/710/606/607 ^3 (поиск каталога ПО
#        авторитету: обратное ребро 6.4/11.1 — найти все БО, ссылающиеся на данную
#        авторитетную запись по её номеру `^3`; ср. навигаторы WnLink / `H=`).
# --------------------------------------------------------------------------- #
INDEX_SPEC = [
    # --- original four (unchanged bindings) ---
    ('T', '200', 'a'),
    ('A', '700', 'a'),
    ('A', '701', 'a'),
    ('A', '702', 'a'),
    ('A', '710', 'a'),       # back-compat: 710 stayed under A= in the first slice
    ('K', '610', None),      # пословно (KEYWORD_PREFIXES): каждое слово 610 — термин K=
    ('IN', '910', 'b'),
    # --- заглавие серии ---
    ('TS', '225', 'a'),
    # --- коллектив / мероприятие (corporate author heading) ---
    ('M', '710', 'a'),
    ('M', '711', 'a'),
    # --- тематика ---
    ('S', '606', 'a'),
    ('S', '605', 'a'),
    ('GEO', '607', 'a'),
    ('U', '675', None),
    ('U', '621', None),
    # --- коды ---
    ('V', '900', 'b'),
    ('B', '10', 'a'),
    ('B', '11', 'a'),
    ('I', '903', None),
    # --- выходные данные ---
    ('G', '210', 'd'),
    # --- экземпляр ---
    ('MHR', '910', 'd'),
    # --- авторитетная ссылка ^3 (поиск каталога ПО авторитету, ребро 6.4) ---
    # Каждое поле-заголовок, несущее ^3 = номер авторитетной записи, индексируется
    # под AR=, чтобы найти все БО, ссылающиеся на эту авторитетную запись.
    ('AR', '700', '3'),
    ('AR', '701', '3'),
    ('AR', '702', '3'),
    ('AR', '710', '3'),
    ('AR', '711', '3'),
    ('AR', '600', '3'),
    ('AR', '601', '3'),
    ('AR', '606', '3'),
    ('AR', '607', '3'),
    # --- связи иерархии записей (INTEGRATION_MAP кластер 9, поиск-по-связи) ---
    # HOST= — ключ-идентичность издания-хозяина (журнал/сборник/сводная запись);
    # по нему дочерние записи (статьи/номера/тома) его находят.
    ('HOST', '200', 'a'),    # собственное заглавие хозяина
    ('HOST', '11', 'a'),     # ISSN хозяина (сериальное издание)
    ('HOST', '903', None),   # шифр документа хозяина (целое поле)
    # LINK= — ключ-отсылка зависимой записи на её хозяина; по нему хозяин
    # находит свои аналитики/номера/тома (зеркало HOST=).
    ('LINK', '463', 'c'),    # 9.1 статья → журнал/сборник: заглавие хозяина
    ('LINK', '463', 'j'),    # 9.1 статья → журнал/сборник: ISSN хозяина
    ('LINK', '461', 'c'),    # 9.2 номер → журнал: заглавие общей части
    ('LINK', '461', 'j'),    # 9.2 номер → журнал: ISSN общей части
    ('LINK', '481', 'c'),    # 9.3 том → сводная (приплетённое/многотомник)
    ('LINK', '963', 'c'),    # свод. сведения аналитики (back-up к 463): заглавие
    ('LINK', '963', 'j'),    # свод. сведения аналитики: ISSN
]

# The prefixes a caller may search by (used to validate / document expressions).
# Order: the four original prefixes first, then the expanded set (§3.2 high-freq).
SEARCH_PREFIXES = ('T', 'A', 'K', 'IN',
                   'TS', 'M', 'S', 'GEO', 'U', 'V', 'B', 'I', 'G', 'MHR', 'AR')

# Служебные префиксы связи иерархии записей (INTEGRATION_MAP кластер 9). Они НЕ
# входят в SEARCH_PREFIXES (обычный словарный поиск `PREFIX=term` их не разбирает —
# это back-compat для §3.2-сьюты), а используются ВНУТРИ обхода связи
# (``linked_records``): HOST= — ключ-идентичность хозяина, LINK= — ключ-отсылка
# зависимой записи. Зеркальная пара сматчивается по нормализованному значению.
LINK_PREFIXES = ('HOST', 'LINK')

# Пословные (keyword) префиксы — индексируются НЕ целым полем, а каждым словом
# отдельной строкой словаря (как у ИРБИС: значение поля 610 «театральное
# искусство; театр» даёт термины «театральное», «искусство», «театр»). Точный
# поиск ``K=театр`` находит запись, где «театр» — одно из ключевых слов, а
# усечение ``K=театр$`` (prefix-match по term_norm) и составные выражения
# продолжают работать без изменений (#270). Прочие префиксы (T=/A=/S=/U=/I=…)
# остаются ЦЕЛО-ПОЛЕВЫМИ — поведение не меняется.
KEYWORD_PREFIXES = ('K',)

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


def brief_item_from_record(mfn, record):
    """Структурная карточка результата (mfn/title/author/year/docType/availability/
    hasCover) из НАШЕЙ tag-keyed записи — зеркало Api._brief_from_record, но через
    _field_values (регистр подполя нечувствителен). Чтобы own-индекс отдавал поиск
    под тем же контрактом /api/search, в обход сломанного ИРБИС-K= (#229/#262)."""
    def first(field, sub=None):
        vals = _field_values(record, field, sub)
        return vals[0] if vals else ''
    title = first('200', 'a')
    author = first('700', 'a')
    if author:
        g = first('700', 'g')
        if g:
            author = author + ', ' + g
    else:
        author = first('200', 'f')
    year = first('210', 'd')
    doctype = first('900', 't') or first('900', 'b')
    avail = 'unknown'
    holds = _field_values(record, '910', 'a')
    if holds:
        avail = 'available' if holds[0] in ('0', '') else 'issued'
    return {'mfn': mfn, 'title': title or ('MFN %d' % mfn), 'author': author,
            'year': year, 'docType': doctype, 'availability': avail,
            'hasCover': bool(_instances(record, '953'))}


def _norm(term):
    """Normalize a term for matching (casefold + trim). ИРБИS inverted terms are
    matched case-insensitively; we keep the original ``term`` for display."""
    return (term or '').strip().casefold()


def _keyword_words(value):
    """Разбить значение keyword-поля (610) на отдельные слова для пословного K=.

    ИРБИС индексирует ключевые слова ПОСЛОВНО: значение «театральное искусство;
    театр» порождает термины «театральное», «искусство», «театр» — каждый под
    ``K=``. Разделители — любая не-словарная пунктуация/пробелы (``;``, ``,``,
    ``.``, тире и т.п.); слово — максимальная последовательность буквенно-цифровых
    символов (с учётом Unicode-кириллицы) плюс внутренние дефис/апостроф (чтобы
    «научно-популярный» / «d'art» не дробились). Каждое слово отдаётся в исходном
    регистре (нормализация под ``term_norm`` — отдельно, как у целых терминов);
    дубликаты в пределах одного значения отсеиваются вызывающим (``index_terms``)
    по ключу (prefix, _norm). Возвращает список слов в порядке появления."""
    if not value:
        return []
    words, buf = [], []
    for ch in str(value):
        if ch.isalnum() or (ch in "-'" and buf):
            buf.append(ch)
        else:
            if buf:
                words.append(''.join(buf).strip("-'"))
                buf = []
    if buf:
        words.append(''.join(buf).strip("-'"))
    return [w for w in words if w]


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


def _tokenize_search_expr(expr):
    """Токенизировать ИРБИС-K-выражение в список токенов:
    ``('op', '(')|')'|'+'|'*'|'^'`` и ``('term', '<PREFIX=term[$]>')``. Внутри
    кавычек — литерал; снаружи операторы/скобки разделяют термины (#262)."""
    toks = []
    s = expr or ''
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in '()+*^':
            toks.append(('op', c))
            i += 1
            continue
        if c == '"':
            j = s.find('"', i + 1)
            if j == -1:
                j = n
            toks.append(('term', s[i + 1:j]))
            i = j + 1
            continue
        # bare-термин: значение может содержать пробелы (напр. ``A=Чехов А.П.``),
        # поэтому читаем до ОПЕРАТОРА/скобки/кавычки (не до пробела) и обрезаем края.
        j = i
        while j < n and s[j] not in '()+*^"':
            j += 1
        term = s[i:j].strip()
        if term:
            toks.append(('term', term))
        i = j
    return toks


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
    authority : object | None
        Optional :class:`access.authority.AuthorityStore` handle. When wired,
        ``save`` resolves pending authority references (a field instance carrying
        an ``_authority_ref`` subfield) through ``authority.substitute`` — filling
        ``^a/^b/^g`` + the ``^3`` link before ФЛК / index (INTEGRATION_MAP edge
        6.1). When None, save is unchanged: the client must supply ``^3`` itself.

        The same handle drives two further seams (both opt-in / back-compatible):
          * autoin (edge 6.2): ``save(..., autoin=True)`` auto-creates/links an
            authority record for a heading saved WITHOUT ``^3`` and threads the
            ``^3`` back in (``authority.autoin``);
          * ФЛК ``^3`` (edge 6.3): ``validate`` passes the handle to ``flk`` so a
            broken ``^3`` (id absent from the authority base) raises a severity-2
            violation.
        When ``authority`` is None all three seams no-op (full back-compat).
    """

    def __init__(self, db_path=':memory:', access_store=None,
                 brief_pft=None, full_pft=None, authority=None):
        self.db_path = db_path
        self.access_store = access_store
        self.authority = authority
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
                 tenant_overrides=None, authority=None):
        """Run ФЛК over ``record`` for ``phase`` (default the full ``save`` run).

        The A5 vocabulary store is threaded through so dictionary rules resolve
        against the seeded vocabularies; the inverted index is wired as the ФЛК
        ``dup_index`` so the (carried) duplicate-inventory rule can fire. The
        authority handle (per-call arg or the store default) is wired as the ФЛК
        ``authority`` resolver so the ``^3``-integrity rule (edge 6.3) can verify
        each heading's ``^3`` against the authority base."""
        auth = authority if authority is not None else self.authority
        return flk.validate(
            record, phase=phase, store=self.access_store,
            current_mfn=current_mfn, dup_index=self._dup_index,
            tenant_overrides=tenant_overrides, authority=auth)

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
        findable by. Duplicate (prefix, normalized-term) pairs are collapsed.

        Пословный K= (#270): keyword-префиксы (``KEYWORD_PREFIXES``, напр. ``K=``
        над полем 610) индексируются НЕ целым значением поля, а каждым словом
        отдельным термином (``_keyword_words``) — как у ИРБИС. Точное ``K=театр``
        тогда находит запись, где «театр» — одно из ключевых слов; усечение
        ``K=театр$`` и составные выражения работают как раньше. Прочие префиксы
        кладутся целым полем (без изменений)."""
        seen = set()
        out = []
        for prefix, field, subfield in INDEX_SPEC:
            for value in _field_values(record, field, subfield):
                # keyword-поле → пословно; остальные — целым значением (как было).
                terms = (_keyword_words(value) if prefix in KEYWORD_PREFIXES
                         else [value])
                for term in terms:
                    norm = _norm(term)
                    key = (prefix, norm)
                    if key in seen or not norm:
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
             tenant_overrides=None, authority=None, autoin=False):
        """Validate then upsert a record.

        Pipeline:
          0a. (edge 6.1) if an ``authority`` handle is available (per-call arg or
             the store default), resolve any pending authority reference into the
             record IN PLACE — filling ``^a/^b/^g`` + the ``^3`` link — BEFORE
             validation/index, so the saved record + index already carry ``^3``.
          0b. (edge 6.2, opt-in via ``autoin=True``) for every heading field
             (700/710/606/…) that carries a non-empty heading but NO ``^3``,
             auto-create/link an authority record (``authority.autoin``) and write
             the resulting ``^3`` back into the field — replenish the authority
             base from cataloguing. Off by default (it mutates the authority store).
          1. run ФЛК (A2) — if ANY severity-1 (непреодолимая) violation, REJECT:
             return ``{id:None, mfn:None, saved:False, violations:[...]}`` and
             touch no row. The authority handle is threaded so the ``^3``-integrity
             rule (edge 6.3) flags a broken link.
          2. otherwise upsert (insert with a fresh sequential mfn, or update the
             existing row when ``mfn`` is given) and (re)build the inverted index
             (now including ``AR=`` over ``^3`` — edge 6.4).

        ``skip_warnings`` is accepted for the warning-acknowledgement workflow:
        severity-2 violations never block a save in either case here (they're
        преодолимые), but the flag is surfaced in the result for the caller/UI.

        Returns ``{id, mfn, saved, violations, overallSeverity, canSave}`` plus,
        when autoin ran, ``autoin`` = the list of ``(field, instance, id, created)``
        applied.
        """
        conn = self._conn()
        target_mfn = mfn

        # Edge 6.1: pull authority subfields + ^3 before validation/index.
        auth = authority if authority is not None else self.authority
        autoin_applied = []
        if auth is not None:
            self.resolve_authority_refs(record, authority=auth)
            # Edge 6.2: autoin — replenish ATHR* from headings saved without ^3.
            if autoin:
                autoin_applied = self.autoin_authority(record, authority=auth)

        existing = self._row(db, mfn, include_deleted=True) if mfn is not None else None

        res = self.validate(record, current_mfn=target_mfn,
                            tenant_overrides=tenant_overrides, authority=auth)
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
            'autoin': autoin_applied,
        }

    # ------------------------------------------------------------------- #
    # Authority↔Catalog seam (INTEGRATION_MAP edge 6.1).
    #
    # A field instance asks for authority substitution by carrying an
    # ``_authority_ref`` subfield = the authority record id (e.g.
    # ``{'700': [{'_authority_ref': 42}]}``). ``apply_authority`` resolves that
    # id through the authority store and fills ``^a/^b/^g/…`` + the ``^3`` link
    # via ``authority.substitute`` (the same fill-map the UI uses), then drops the
    # ref marker. ``resolve_authority_refs`` sweeps every fill-mappable field on a
    # record (called from ``save`` when an authority handle is wired).
    # ------------------------------------------------------------------- #
    def apply_authority(self, record, field, authority_id, *, instance=0,
                        authority=None):
        """Fill one field instance's subfields from an authority record + ``^3``.

        Resolves ``authority_id`` in the base bound to ``field`` (via the authority
        module's FILL_MAP), runs ``authority.substitute(field, rec)`` to build the
        ``{^a/^b/^g, '3': id}`` patch, and merges it into ``record[field][instance]``
        in place (mutating + returning the record). The ``^3`` link is always set
        for linkable fields (DB_AUTHORITY §5.2). Returns the merged patch too via
        the instance; raises the authority module's errors on a missing record /
        unknown field tag so the caller sees a broken ^3 reference loudly.
        """
        auth = authority if authority is not None else self.authority
        if auth is None:
            raise CatalogError(
                'apply_authority called without an authority handle wired')
        tag = str(field)
        spec = _authority.FILL_MAP.get(tag)
        if spec is None:
            raise _authority.UnknownCatalogField(
                'no fill-map for catalog field %r' % tag)
        rec = auth.get(spec['db'], authority_id)
        if rec is None:
            raise _authority.AuthorityNotFound(
                'authority %r not found in %s for field %s'
                % (authority_id, spec['db'], tag))
        patch = _authority.substitute(tag, rec)

        insts = record.get(field)
        if insts is None:
            insts = [{}]
            record[field] = insts
        elif not isinstance(insts, list):
            insts = [insts]
            record[field] = insts
        if instance >= len(insts):
            insts.extend({} for _ in range(instance - len(insts) + 1))
        cur = insts[instance]
        if not isinstance(cur, dict):
            cur = {'': cur} if cur else {}
            insts[instance] = cur
        cur.pop('_authority_ref', None)
        cur.update(patch)
        return record

    def resolve_authority_refs(self, record, *, authority=None):
        """Sweep ``record`` for pending ``_authority_ref`` markers and apply each.

        For every fill-mappable field (700/701/710/606/607/…) whose instance
        carries ``_authority_ref``, resolve+fill it in place. Instances without the
        marker are left untouched (so an operator-supplied ``^3`` survives). Returns
        the list of ``(field, instance, authority_id)`` triples applied."""
        applied = []
        for field in list(record.keys()):
            if str(field) not in _authority.FILL_MAP:
                continue
            insts = record[field]
            if not isinstance(insts, list):
                insts = [insts]
            for i, inst in enumerate(insts):
                if isinstance(inst, dict) and inst.get('_authority_ref') is not None:
                    aid = inst['_authority_ref']
                    self.apply_authority(record, field, aid, instance=i,
                                         authority=authority)
                    applied.append((str(field), i, aid))
        return applied

    # ------------------------------------------------------------------- #
    # autoin — replenish ATHR* from cataloguing (INTEGRATION_MAP edge 6.2).
    #
    # The reverse of edge 6.1: instead of pulling subfields from a chosen
    # authority, we PUSH a heading typed straight into the catalog (700/710/606/…)
    # into the authority base. For every heading instance that carries a real
    # heading (^a/…) but NO ``^3`` link, ``authority.autoin`` either links it to an
    # existing authority record (same fold-key) or materialises a fresh
    # ``needs_review`` one; we write the returned id back as ``^3`` so the saved
    # record + index already carry the link. Port of ``autoin.gbl`` (SPEC §3.4).
    # ------------------------------------------------------------------- #
    def autoin_authority(self, record, *, authority=None):
        """Sweep ``record`` for headings WITHOUT ``^3`` and autoin each in place.

        For every fill-mappable field whose instance has a non-empty heading
        (some fill-map subfield present) but no ``^3``, call ``authority.autoin``
        and set the returned id as ``^3``. Index-only fields without a ``^3`` link
        (675/621 — ``link=False``) are skipped (they carry no ``^3``). Instances
        that already carry ``^3`` (operator- or 6.1-supplied) are left untouched.
        Returns the list of ``(field, instance, authority_id, created)`` applied."""
        auth = authority if authority is not None else self.authority
        if auth is None:
            raise CatalogError(
                'autoin_authority called without an authority handle wired')
        applied = []
        for field in list(record.keys()):
            tag = str(field)
            spec = _authority.FILL_MAP.get(tag)
            if spec is None or not spec.get('link', True):
                continue                      # no ^3 link on this field => skip
            insts = record[field]
            if not isinstance(insts, list):
                insts = [insts]
            for i, inst in enumerate(insts):
                if not isinstance(inst, dict):
                    continue
                if inst.get('3') or inst.get('_authority_ref') is not None:
                    continue                  # already linked / pending ref
                # does this instance carry an actual heading to push?
                has_heading = any(inst.get(ck) or inst.get(ck.upper())
                                  for ck, _ak in spec['pairs'])
                if not has_heading:
                    continue
                aid, created = auth.autoin(tag, inst)
                inst['3'] = str(aid)
                applied.append((tag, i, aid, created))
        return applied

    # ------------------------------------------------------------------- #
    # Exemplar status (910^A) — the Catalog↔Circulation seam (edges 2.1/2.2).
    #
    # A bibliographic record holds its copies as repeating ``910`` fields; each
    # carries a shelfmark/inventory key (``910^b``) and an availability flag
    # (``910^A``: 0 free / 1 issued / …). Circulation flips ``910^A`` here when a
    # copy is checked out / returned, and reads it to know what is free. The item
    # is resolved by inventory number (``910^b``), the same key circulation stores
    # as its ``loan.item`` (903/910^b per the spec).
    # ------------------------------------------------------------------- #
    @staticmethod
    def _exemplar_key(inst):
        """Inventory/shelfmark key of a 910 instance (``910^b``), or '' if none."""
        if isinstance(inst, dict):
            return str(inst.get('b') or inst.get('B') or '')
        return ''

    def find_exemplar(self, db, item):
        """Locate the ``910`` instance keyed by inventory number ``item``.

        Scans active records' ``910`` fields for one whose ``910^b`` == ``item``.
        Returns ``(mfn, index, instance_dict)`` or ``None`` — the address
        circulation uses to flip ``910^A`` for that specific copy."""
        target = str(item)
        for r in self._conn().execute(
                "SELECT mfn, data_json FROM record WHERE db=? AND status='active' "
                'ORDER BY mfn', (db,)).fetchall():
            record = json.loads(r['data_json'])
            insts = record.get('910')
            if insts is None:
                continue
            if not isinstance(insts, list):
                insts = [insts]
            for i, inst in enumerate(insts):
                if self._exemplar_key(inst) == target:
                    return (r['mfn'], i, inst)
        return None

    def exemplar_status(self, db, item):
        """Read ``910^A`` for the copy keyed by inventory ``item`` (None if absent)."""
        found = self.find_exemplar(db, item)
        if found is None:
            return None
        inst = found[2]
        if isinstance(inst, dict):
            return str(inst.get('a') or inst.get('A') or '')
        return ''

    def is_available(self, db, item):
        """True iff the copy keyed by ``item`` exists and its ``910^A`` is FREE.

        The availability read circulation uses for free-exemplar matching / hold
        placement (edge 2.2). Any non-free / unknown status ⇒ not available."""
        st = self.exemplar_status(db, item)
        return st == EXEMPLAR_FREE

    def set_exemplar_status(self, db, item, status):
        """Flip ``910^A`` of the copy keyed by inventory ``item`` to ``status``.

        The write-back that closes edges 2.1/2.2: circulation calls this on
        checkout (``status=EXEMPLAR_ISSUED``) and return (``status=EXEMPLAR_FREE``).
        Re-indexes the touched record so search stays consistent. Returns the
        ``mfn`` whose copy was flipped, or None if no such copy exists (circulation
        then degrades gracefully — it still records its own loan)."""
        found = self.find_exemplar(db, item)
        if found is None:
            return None
        mfn, idx, _inst = found
        conn = self._conn()
        r = self._row(db, mfn, include_deleted=False)
        if r is None:
            return None
        record = json.loads(r['data_json'])
        insts = record.get('910')
        if not isinstance(insts, list):
            insts = [insts]
            record['910'] = insts
        inst = insts[idx]
        if not isinstance(inst, dict):
            inst = {'b': str(item)}
            insts[idx] = inst
        inst['a'] = str(status)
        conn.execute('UPDATE record SET data_json=?, updated=? WHERE id=?',
                     (json.dumps(record, ensure_ascii=False), time.time(), r['id']))
        self._reindex(conn, r['id'], record)
        conn.commit()
        return mfn

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

    def search_records(self, db, expr, limit=20, offset=0):
        """Поиск по выражению — ОДИНОЧНОМУ ``PREFIX=term`` ИЛИ СОСТАВНОМУ ИРБИС-K
        (``+`` ИЛИ · ``*`` И · ``^`` НЕ · скобки · кавычки · ``$`` усечение). Возврат
        ``{total, items:[{mfn, record}], expr}`` в порядке mfn (#229/#262 — own-index
        поиск за флагом OWN_SEARCH_DBS, в обход сломанного ИРБИС-K=; покрывает и
        дефолтный мультиполевой запрос портала ``("T=q$" + "A=q$" + "K=q$")``)."""
        conn = self._conn()
        ids = self._eval_search_expr(conn, db, expr)
        total = len(ids)
        if not ids:
            return {'total': 0, 'items': [], 'expr': expr}
        # Упорядочим по mfn и возьмём страницу. id-множество тащим чанками, чтобы
        # не упереться в лимит числа параметров SQLite на больших выборках.
        ordered = sorted(self._mfns_for_ids(conn, ids), key=lambda r: r['mfn'])
        page = ordered[offset:offset + limit]
        if not page:
            return {'total': total, 'items': [], 'expr': expr}
        page_ids = [r['id'] for r in page]
        ph = ','.join('?' * len(page_ids))
        recs = {r['id']: r for r in conn.execute(
            'SELECT id, mfn, data_json FROM record WHERE id IN (%s)' % ph,
            page_ids).fetchall()}
        items = [{'mfn': recs[i]['mfn'], 'record': json.loads(recs[i]['data_json'])}
                 for i in page_ids if i in recs]
        return {'total': total, 'items': items, 'expr': expr}

    def _mfns_for_ids(self, conn, ids):
        """``[(id, mfn)]`` для множества record.id — чанками по 900 (лимит SQLite)."""
        out = []
        ids = list(ids)
        for k in range(0, len(ids), 900):
            chunk = ids[k:k + 900]
            ph = ','.join('?' * len(chunk))
            out.extend(conn.execute(
                'SELECT id, mfn FROM record WHERE id IN (%s)' % ph, chunk).fetchall())
        return out

    def _term_record_ids(self, conn, db, single_expr):
        """Множество record.id для ОДНОГО ``PREFIX=term`` (+ усечение ``$``)."""
        prefix, term = parse_expr(single_expr)
        trunc = term.endswith('$')
        base = _norm(term[:-1] if trunc else term)
        if trunc:
            esc = base.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            cond = "ri.prefix=? AND ri.term_norm LIKE ? ESCAPE '\\'"
            targs = (prefix, esc + '%')
        else:
            cond = 'ri.prefix=? AND ri.term_norm=?'
            targs = (prefix, base)
        rows = conn.execute(
            'SELECT DISTINCT r.id FROM record_index ri JOIN record r ON r.id = ri.record_id '
            "WHERE r.db=? AND r.status='active' AND " + cond, (db,) + targs).fetchall()
        return {r['id'] for r in rows}

    def _eval_search_expr(self, conn, db, expr):
        """Вычислить выражение → множество record.id. Рекурсивный спуск с
        приоритетом: OR (``+``) ниже AND/НЕ (``*``/``^``); скобки переопределяют;
        листы — термины ``PREFIX=term``. Множества: ``+`` union, ``*`` intersect,
        ``^`` difference (#262)."""
        toks = _tokenize_search_expr(expr)
        pos = [0]

        def peek():
            return toks[pos[0]] if pos[0] < len(toks) else None

        def parse_or():
            left = parse_and()
            while peek() == ('op', '+'):
                pos[0] += 1
                left = left | parse_and()
            return left

        def parse_and():
            left = parse_factor()
            while peek() in (('op', '*'), ('op', '^')):
                op = toks[pos[0]][1]
                pos[0] += 1
                right = parse_factor()
                left = (left & right) if op == '*' else (left - right)
            return left

        def parse_factor():
            t = peek()
            if t == ('op', '('):
                pos[0] += 1
                inner = parse_or()
                if peek() == ('op', ')'):
                    pos[0] += 1
                return inner
            if t is not None and t[0] == 'term':
                pos[0] += 1
                return self._term_record_ids(conn, db, t[1])
            if t is not None:        # неожиданный токен — пропустить, не зациклиться
                pos[0] += 1
            return set()

        return parse_or()

    def search_items(self, db, expr, limit=20, offset=0):
        """Как ``search_records``, но возвращает СТРУКТУРНЫЕ карточки той же формы,
        что ИРБИС-путь /api/search (через ``brief_item_from_record``). Это вход для
        маршрута own-индекса за флагом OWN_SEARCH_DBS (#262)."""
        res = self.search_records(db, expr, limit, offset)
        res['items'] = [brief_item_from_record(it['mfn'], it['record']) for it in res['items']]
        return res

    # ------------------------------------------------------------------- #
    # Поиск-по-связи иерархии записей (INTEGRATION_MAP кластер 9, рёбра
    # 9.1/9.2/9.3). Связь хранится как повтор ключа издания-хозяина в поле-связи
    # зависимой записи (463/461/481/963), а не как ссылка-по-MFN. Обе стороны
    # инвертированы зеркальной парой HOST=/LINK= (см. INDEX_SPEC); обход
    # сматчивает их по нормализованному значению ключа.
    # ------------------------------------------------------------------- #
    def _link_keys(self, conn, record_id, prefix):
        """Нормализованные значения служебного префикса связи (HOST|LINK) у записи."""
        rows = conn.execute(
            'SELECT DISTINCT term_norm FROM record_index '
            'WHERE record_id=? AND prefix=?', (record_id, prefix)).fetchall()
        return [r['term_norm'] for r in rows if r['term_norm']]

    def linked_records(self, db, mfn, kind='children', *, limit=100, offset=0):
        """Обойти связь иерархии записей от записи ``mfn`` в активной БД ``db``.

        Связь иерархии (статья↔журнал/сборник 9.1, номер↔журнал 9.2,
        том↔сводная 9.3) хранится как ОБЩИЙ КЛЮЧ: издание-хозяин несёт свой
        ключ-идентичность под ``HOST=`` (200^a заглавие / 11^a ISSN / 903 шифр),
        зависимая запись несёт ТОТ ЖЕ ключ как отсылку под ``LINK=`` (463/461/481/963).

        ``kind``:
          * ``'children'`` (по умолчанию) — от записи-ХОЗЯИНА: вернуть все
            зависимые записи, чей ``LINK=`` совпал с её ``HOST=`` (аналитики
            журнала, номера журнала, тома многотомника). Реализует прямое ребро
            «хозяин → дети» (``Scnt``-подобный обход).
          * ``'host'`` / ``'parent'`` — от ЗАВИСИМОЙ записи: вернуть её
            издание(-я)-хозяина, чей ``HOST=`` совпал с её ``LINK=``. Обратное
            ребро «ребёнок → хозяин».

        Совпадение — по нормализованному (casefold+trim) значению ключа, та же
        нормализация, что у словарного поиска. Запись не считается своим
        собственным родственником (self-MFN исключается). Возвращает
        ``{total, items:[{mfn, brief}], kind, keys}`` — ``keys`` = ключи связи,
        по которым шёл матч (для отладки/прозрачности). Если запись отсутствует
        или у неё нет ключей нужной стороны — ``total=0, items=[]``.
        """
        conn = self._conn()
        src = self._row(db, mfn, include_deleted=False)
        if src is None:
            return {'total': 0, 'items': [], 'kind': kind, 'keys': []}
        if kind in ('host', 'parent'):
            my_prefix, other_prefix = 'LINK', 'HOST'   # ребёнок → хозяин
        else:                                          # 'children' (default)
            my_prefix, other_prefix = 'HOST', 'LINK'   # хозяин → дети
        keys = self._link_keys(conn, src['id'], my_prefix)
        if not keys:
            return {'total': 0, 'items': [], 'kind': kind, 'keys': []}
        placeholders = ','.join('?' for _ in keys)
        base = (
            'FROM record_index ri JOIN record r ON r.id = ri.record_id '
            "WHERE r.db=? AND r.status='active' AND r.id<>? "
            'AND ri.prefix=? AND ri.term_norm IN (%s)' % placeholders)
        params = [db, src['id'], other_prefix] + keys
        total = conn.execute(
            'SELECT COUNT(DISTINCT r.id) AS n ' + base, params).fetchone()['n']
        rows = conn.execute(
            'SELECT DISTINCT r.id, r.mfn, r.data_json ' + base +
            ' ORDER BY r.mfn LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
        items = [{'mfn': r['mfn'],
                  'brief': self._render(self.brief_pft, json.loads(r['data_json']),
                                        r['mfn'])}
                 for r in rows]
        return {'total': total, 'items': items, 'kind': kind, 'keys': keys}

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
