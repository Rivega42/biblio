#!/usr/bin/env python3
"""PFT formatting engine — the A1 keystone (epic #188, SPEC_engine_pft.md).

This is the self-contained *expression core* of the ИРБИС64 PFT formatting
language that the ФЛК (A2, ``access/flk.py``) and глобальная корректировка (A3,
``.gbl``) engines delegate to. It is the in-process module contract formalized in
SPEC_api_contracts §3.1 / mismatch M4:

    pft.eval(fmt, record, ctx)       -> str          # single-line result
    pft.eval_lines(fmt, record, ctx) -> list[str]    # multi-line (repeat groups)

Scope (first shippable slice — SPEC §1.3 Phase 1 + a Phase-2 / Phase-3 subset)
------------------------------------------------------------------------------
A *hybrid interpreter*: the format string is tokenized → parsed to a small AST →
interpreted against a record. Output is a plain string (the IR-document /
HTML/PDF rendering of SPEC §1.1 is a later phase; here the IR collapses to text).

Record shape (the I1 field/subfield draft — same as ``access/flk.py``)::

    {
      "200": [{"a": "Заглавие", "f": "Автор"}],   # repeating field = list of instances
      "910": [{"a": "0", "b": "INV1"}, {"b": "INV2"}],
      "101": "rus",                                # bare-string field
      "10":  {"a": "5-7654-0001-X"}                # single instance (dict)
    }

A field may be a bare string, a ``{subfield: value}`` dict, or a list of either.

Implemented PFT constructs
--------------------------
  * Field refs: ``v200``, ``v200^a``, ``v200^*`` (first subfield), fragment
    ``v200^a*off.len`` / ``v1*3.3`` (SPEC §2).
  * ``mfn`` / ``mfn(d)`` — record number from ``ctx['mfn']`` (SPEC §2).
  * Literals: conditional ``"…"`` (once if the *adjacent* field is present),
    repeatable ``|…|`` (per instance, incl. ``|x|+`` prefix / ``+|x|`` suffix),
    unconditional ``'…'`` (always) (SPEC §5).
  * Dummy output ``d<tag>`` / ``n<tag>`` (literal by field presence/absence, §6).
  * ``IF … THEN … ELSE … FI`` with nesting; conditions ``= <> < <= > >= :``
    (contains) and ``NOT / AND / OR``; predicates ``p(...)`` / ``a(...)`` (§7,§10).
  * Repeat groups ``(… v910 …)`` — one pass per instance of the repeating field
    inside (SPEC §10); ``eval_lines`` surfaces them as separate lines.
  * Concatenation by ``,`` and ``+`` (SPEC §7).
  * ``f(expr[,width[,dec]])`` number→string; ``val(...)`` text→number;
    ``s(...)`` concatenation/implicit-OR (SPEC §8).
  * ``&unifor('…')`` / ``&uf('…')`` — the UNIFOR registry (see ``UNIFOR``).

UNIFOR codes implemented (vs degraded)
--------------------------------------
Implemented (first char of the argument):
  ``C`` ISBN/ISSN checksum control (0 ok / 1 error) — **the code ФЛК A2 reuses**;
  ``3`` date/time (``3`` ГГГГММДД, ``30`` year, ``31`` month, ``32`` day, ``33``
  YY, ``34``/``35`` no-lead-zero, ``39`` time, today's date from ``ctx['now']``);
  ``A``/``P`` Nth field occurrence (``Av910^a#2``); ``9`` strip double-quotes;
  ``Q`` lowercase; ``X`` strip ``<…>``; ``E`` first N words; ``!`` / ``+F``
  post-edit (collapse double separators / drop RTF); ``6`` nested template format
  (``6<name>`` resolved from ``ctx['modules']``, ``%N`` params).
Degraded to empty string (carried, never crash — SPEC §2.1 risk, §15 "Format
error 99" parity): every other code (``D``,``7``,``J``,``l``-index lookups,
``+1``/``+7`` globals beyond ctx, ``T``,``+I``,``$`` …). Unknown ⇒ ``''``.

Graceful degradation
---------------------
The engine NEVER raises on malformed/unsupported input: an unparsable construct
is skipped (emits ``''``), so a partially-understood real ``.pft`` still yields
the parts we understand rather than a 500. ``strict=True`` opts into raising
``PftError`` (used by the format editor / preview path).
"""
from __future__ import annotations

import datetime as _dt
import re

__all__ = [
    'eval', 'eval_lines', 'PftError', 'UNIFOR', 'register_unifor',
    'isbn_issn_ok',
]


# --------------------------------------------------------------------------- #
# Errors. In non-strict mode (the default, what A2/A3 use) we never raise.
# --------------------------------------------------------------------------- #
class PftError(Exception):
    """A PFT format/parse error. Carries an ИРБИС-style numeric ``code``
    (SPEC §15 / PFT_LANGUAGE §15): 8 IF-without-THEN, 19/20 unbalanced parens,
    53 IF-without-FI, 99 unknown command."""

    def __init__(self, message, code=99):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------- #
# Record-draft accessors. A field can be a bare string, a {subfield:val} dict,
# or a list of either (repeating). Mirrors access/flk.py so A2 and A1 agree.
# --------------------------------------------------------------------------- #
def _instances(record, tag):
    raw = record.get(tag) if record else None
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _inst_value(inst, subfield):
    """Read ``subfield`` from one instance. subfield=None => whole field value."""
    if isinstance(inst, dict):
        if subfield is None or subfield == '':
            # whole-field value: the bare '' key, else join subfields in order
            if inst.get(''):
                return inst['']
            if inst.get('value'):
                return inst['value']
            return ''.join(str(v) for v in inst.values())
        return (inst.get(subfield) or inst.get(subfield.lower())
                or inst.get(subfield.upper()) or '')
    # bare string instance: only the whole-field value exists
    return inst if (subfield is None or subfield == '') else ''


def _first_subfield(inst):
    """``v200^*`` — value of the first subfield of the first instance."""
    if isinstance(inst, dict):
        for v in inst.values():
            if v:
                return v
        return ''
    return inst or ''


def field_value(record, tag, subfield=None):
    """First non-empty instance's subfield value (or '')."""
    for inst in _instances(record, tag):
        v = _inst_value(inst, subfield)
        if v:
            return v
    insts = _instances(record, tag)
    return _inst_value(insts[0], subfield) if insts else ''


def field_values(record, tag, subfield=None):
    """All instances' subfield values (skipping empties)."""
    out = []
    for inst in _instances(record, tag):
        v = _inst_value(inst, subfield)
        if v:
            out.append(v)
    return out


def present(record, tag, subfield=None):
    """``p(...)`` — at least one non-empty instance of the field/subfield."""
    return bool(field_value(record, tag, subfield))


def _fragment(value, off, length):
    """``v…*off.len`` — substring (0-based offset, given length)."""
    if value is None:
        return ''
    s = str(value)
    if off is None:
        return s
    if off >= len(s):
        return ''
    return s[off:off + length] if length is not None else s[off:]


# --------------------------------------------------------------------------- #
# Check digits (ISBN-10/13 + ISSN) — UNIFOR 'C', reused by ФЛК A2 (SPEC §2.2).
# Self-contained: A1 owns the algorithm; A2 may delegate via &unifor('C'…).
# --------------------------------------------------------------------------- #
def _clean_ident(raw):
    s = (raw or '').upper().replace('-', '').replace(' ', '')
    return ''.join(c for c in s if c.isdigit() or c == 'X')


def isbn_issn_ok(raw):
    """True iff ``raw`` is a structurally valid ISBN-10, ISBN-13 or ISSN
    (correct check digit). Empty / wrong length → False."""
    s = _clean_ident(raw)
    if len(s) == 10:
        total = 0
        for i, c in enumerate(s):
            if c == 'X':
                if i != 9:
                    return False
                d = 10
            elif c.isdigit():
                d = ord(c) - 48
            else:
                return False
            total += (10 - i) * d
        return total % 11 == 0
    if len(s) == 13:
        if not s.isdigit():
            return False
        total = sum((1 if i % 2 == 0 else 3) * (ord(c) - 48)
                    for i, c in enumerate(s))
        return total % 10 == 0
    if len(s) == 8:                      # ISSN
        total = 0
        for i, c in enumerate(s):
            if c == 'X':
                if i != 7:
                    return False
                d = 10
            elif c.isdigit():
                d = ord(c) - 48
            else:
                return False
            total += (8 - i) * d
        return total % 11 == 0
    return False


# --------------------------------------------------------------------------- #
# UNIFOR registry. Each handler: fn(arg:str, value:str, ctx, record) -> str.
# ``arg`` is the code-stripped remainder; ``value`` is the already-evaluated
# inline value (the part after the code literal, if the call embeds a vNNN).
# --------------------------------------------------------------------------- #
UNIFOR = {}


def register_unifor(code, fn):
    """Register/override a UNIFOR handler keyed by its leading code char(s)."""
    UNIFOR[code] = fn


_MONTHS_NOM = ['', 'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
               'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
# Genitive (родительный падеж) — '36MM' vs '37MM' (PFT_LANGUAGE §9.1 code 3).
_MONTHS_GEN = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
               'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
_MONTHS_ENG = ['', 'January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']


def _now(ctx):
    """The 'today' used by date codes — overridable via ctx['now'] for tests."""
    if ctx and ctx.get('now') is not None:
        return ctx['now']
    return _dt.datetime.now()


def _parse_yyyymmdd(s):
    """Parse a ``ГГГГММДД`` (YYYYMMDD) string into a ``date``; ``None`` on
    failure. Tolerates surrounding whitespace and separators (extracts the
    first 8 digits)."""
    digits = ''.join(c for c in str(s or '') if c.isdigit())
    if len(digits) < 8:
        return None
    try:
        return _dt.date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def _uf_date(arg, value, ctx, record):
    """UNIFOR ``3`` — date/time (PFT_LANGUAGE §9.1 / decompiled case ``0x33``).

    Today's date is ``ctx['now']`` (else ``datetime.now()``). Sub-codes
    (the ``3`` is already stripped by the dispatcher):

      * (empty) ГГГГММДД · ``0`` year · ``1`` month(zero-pad) · ``2`` day(pad)
        · ``3`` ГГ (YY) · ``4`` month no-lead-zero · ``5`` day no-lead-zero
        · ``9`` HHMMSS — current-clock fields.
      * ``6MM`` month name nominative · ``7MM`` genitive · ``8MM`` English
        (``MM`` = the 2-digit month, e.g. ``&unifor('36',&unifor('31'))``).
      * ``A`` day-of-year of the supplied/inline ``ГГГГММДД`` (decompiled 3A).
      * ``B<date>,<±days>`` shift a date by N days → ГГГГММДД (decompiled 3B).
      * ``C<date1>,<date2>`` whole-day difference ``date1 - date2`` (3C; ``0``
        if either side unparsable, matching the C default).
    """
    now = _now(ctx)
    sub = arg  # arg already had the leading '3' stripped by the dispatcher
    if sub == '' or sub is None:
        return now.strftime('%Y%m%d')
    if sub == '0':
        return now.strftime('%Y')
    if sub == '1':
        return now.strftime('%m')
    if sub == '2':
        return now.strftime('%d')
    if sub == '3':
        return now.strftime('%y')
    if sub == '4':
        return str(now.month)
    if sub == '5':
        return str(now.day)
    if sub == '9':
        return now.strftime('%H%M%S')
    # month-name codes 6MM/7MM/8MM — the MM is taken from the trailing two
    # digits (or, if absent, from the inline value, else today's month).
    if sub[0] in ('6', '7', '8'):
        table = {'6': _MONTHS_NOM, '7': _MONTHS_GEN, '8': _MONTHS_ENG}[sub[0]]
        mm = sub[1:3] if len(sub) >= 3 and sub[1:3].isdigit() else ''
        if not mm:
            mm = (value or '')[:2]
        try:
            month = int(mm) if mm else now.month
            return table[month]
        except (ValueError, IndexError):
            return ''
    # The date payload for A/B/C may be inline in the spec (e.g.
    # &unifor('3C20260621,20260601')) or in the evaluated value
    # (&unifor('3C'v210^d)); prefer the in-spec tail, fall back to the value.
    payload = (sub[1:] + value) if len(sub) > 1 else (value or '')
    payload = payload.strip()
    today = now.date() if hasattr(now, 'date') else now
    # 3A — day of the year of the supplied YYYYMMDD (else today).
    if sub[0] == 'A':
        d = _parse_yyyymmdd(payload) or today
        return str(d.timetuple().tm_yday)
    # 3B<date>,<±days> — shift a date by N days → ГГГГММДД.
    if sub[0] == 'B':
        base_s, _, off_s = payload.partition(',')
        base = _parse_yyyymmdd(base_s) or today
        try:
            days = int(off_s) if off_s.strip() else 0
        except ValueError:
            days = 0
        return (base + _dt.timedelta(days=days)).strftime('%Y%m%d')
    # 3C<date1>,<date2> — whole-day difference date1-date2 (0 if unparsable).
    if sub[0] == 'C':
        a_s, _, b_s = payload.partition(',')
        da, db = _parse_yyyymmdd(a_s), _parse_yyyymmdd(b_s)
        if da is None or db is None:
            return '0'
        return str((da - db).days)
    return now.strftime('%Y%m%d')


def _uf_checksum(arg, value, ctx, record):
    """UNIFOR ``C`` — ISSN/ISBN control: '0' valid, '1' error (SPEC §9.1).
    The value to check is the inline ``value`` (e.g. ``&unifor('C'v10^a)``)."""
    target = value if value else arg
    return '0' if isbn_issn_ok(target) else '1'


def _uf_occurrence(arg, value, ctx, record):
    """UNIFOR ``A``/``P`` — specified field occurrence: ``Av<tag>^<sub>#<occ>``
    (SPEC §9.1, e.g. ``&unifor('Av920#1')``). 1-based occurrence."""
    m = re.match(r'v(\d+)(?:\^(.))?(?:\*(\d+)(?:\.(\d+))?)?(?:#(\d+))?$', arg, re.I)
    if not m:
        return ''
    tag, sub, off, length, occ = m.groups()
    insts = _instances(record, tag)
    idx = (int(occ) - 1) if occ else 0
    if idx < 0 or idx >= len(insts):
        return ''
    v = _first_subfield(insts[idx]) if sub == '*' else _inst_value(insts[idx], sub)
    if off is not None:
        v = _fragment(v, int(off), int(length) if length is not None else None)
    return v or ''


def _uf_strip_quotes(arg, value, ctx, record):
    """UNIFOR ``9`` — remove double-quote characters (SPEC §9.1)."""
    return (value or arg or '').replace('"', '')


def _uf_lower(arg, value, ctx, record):
    """UNIFOR ``Q`` — lowercase the string (SPEC §9.1)."""
    return (value or arg or '').lower()


def _uf_strip_angle(arg, value, ctx, record):
    """UNIFOR ``X`` — remove ``<…>`` fragments (SPEC §9.1)."""
    return re.sub(r'<[^>]*>', '', value or arg or '')


def _uf_first_words(arg, value, ctx, record):
    """UNIFOR ``E`` — first N words: ``EN<string>`` (PFT_LANGUAGE §9.1).

    Whitespace runs collapse to single spaces (CDS/ISIS word semantics)."""
    m = re.match(r'(\d+)(.*)$', arg, re.S)
    if not m:
        return value or ''
    n = int(m.group(1))
    src = value if value else m.group(2)
    return ' '.join((src or '').split()[:n])


def _uf_cut_after_words(arg, value, ctx, record):
    """UNIFOR ``F`` — keep the line up to and including the Nth word, dropping
    the remainder: ``FN<string>`` (PFT_LANGUAGE §9.1).

    Distinct from ``E``: ``F`` preserves the *original* inter-word spacing of
    the kept prefix (it truncates the string after the Nth word boundary),
    whereas ``E`` re-joins on single spaces."""
    m = re.match(r'(\d+)(.*)$', arg, re.S)
    if not m:
        return value or ''
    n = int(m.group(1))
    src = value if value else m.group(2)
    src = src or ''
    if n <= 0:
        return ''
    # walk the string, counting word starts; cut at the end of the Nth word.
    words_seen = 0
    in_word = False
    cut = len(src)
    for i, ch in enumerate(src):
        if ch.isspace():
            if in_word and words_seen == n:
                cut = i
                break
            in_word = False
        else:
            if not in_word:
                words_seen += 1
            in_word = True
    return src[:cut]


def _uf_substr_marker(arg, value, ctx, record):
    """UNIFOR ``G`` — substring relative to a marker char: ``GNA<string>``
    (PFT_LANGUAGE §9.1 / decompiled case ``0x33``-sibling).

    ``N`` = 0 → take the part *up to* (excluding) the marker; ``N`` = 1 → the
    part *from* (including) the marker. ``A`` is the marker character, with two
    wildcards: ``#`` = the first digit, ``$`` = the first (latin/cyrillic)
    letter. Marker not found → the whole string (mode 0) / empty (mode 1)."""
    m = re.match(r'([01])(.)(.*)$', arg, re.S)
    if not m:
        return value or arg or ''
    mode, marker, tail = m.group(1), m.group(2), m.group(3)
    src = value if value else tail
    src = src or ''
    if marker == '#':
        pos = next((i for i, c in enumerate(src) if c.isdigit()), -1)
    elif marker == '$':
        pos = next((i for i, c in enumerate(src) if c.isalpha()), -1)
    else:
        pos = src.find(marker)
    if pos < 0:
        return src if mode == '0' else ''
    return src[:pos] if mode == '0' else src[pos:]


# Cyrillic→Latin transliteration tables (UNIFOR ``T``). Table 0 is a practical
# GOST-7.79-ish System B mapping; table 1 a simplified ASCII variant. Both are
# applied longest-key-first so digraphs (``щ``→``shh``) win over single letters.
_TRANSLIT_0 = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'cz', 'ч': 'ch', 'ш': 'sh', 'щ': 'shh',
    'ъ': '"', 'ы': 'y', 'ь': "'", 'э': 'e', 'ю': 'yu', 'я': 'ya',
}
_TRANSLIT_1 = dict(_TRANSLIT_0, **{
    'й': 'i', 'х': 'kh', 'ц': 'ts', 'ъ': '', 'ь': '', 'э': 'eh',
})


def _translit(src, table):
    out = []
    for ch in src:
        low = ch.lower()
        rep = table.get(low)
        if rep is None:
            out.append(ch)
        elif ch == low:
            out.append(rep)
        else:                                # preserve title/upper-casing
            out.append(rep.upper() if len(rep) == 1 else rep.capitalize())
    return ''.join(out)


def _uf_translit(arg, value, ctx, record):
    """UNIFOR ``T`` — transliterate Cyrillic to Latin: ``TN<string>`` where
    ``N`` selects the table (``0`` default, ``1`` simplified) (PFT_LANGUAGE
    §9.1). Non-Cyrillic characters pass through unchanged."""
    m = re.match(r'(\d?)(.*)$', arg, re.S)
    tableno = m.group(1)
    src = value if value else (m.group(2) or '')
    table = _TRANSLIT_1 if tableno == '1' else _TRANSLIT_0
    return _translit(src, table)


# Insertion-point markers ``%…%`` that the term-ending code ``L`` removes.
_ENDMARK_RE = re.compile(r'%([^%]*)%')


def _uf_term_ending(arg, value, ctx, record):
    """UNIFOR ``L`` — term ending: ``L<term>`` (PFT_LANGUAGE §9.1 / decompiled
    case ``0x4c``). The dictionary/morphology lookup needs the inverted file,
    which this slice does not carry, so we degrade to the documented *marker
    pass*: the real code strips the ``%…%`` insertion-point markers from the
    computed ending and concatenates the segments. With no index we apply that
    same marker-stripping to the supplied term so a template using ``L`` still
    renders clean text rather than echoing the ``%`` markers."""
    src = value if value else (arg or '')
    return _ENDMARK_RE.sub(r'\1', src or '')


def _uf_full_record(arg, value, ctx, record):
    """UNIFOR ``0`` — the whole document (format ALL): every field flattened to
    ``<tag>#<value>`` lines (PFT_LANGUAGE §9.1 / decompiled case ``0x30``).

    A plain readable dump of the record; repeating instances are each emitted
    on their own line. Useful for debug/diagnostic templates."""
    if not record:
        return ''
    lines = []
    for tag in record:
        for inst in _instances(record, tag):
            lines.append('%s#%s' % (tag, _inst_value(inst, None)))
    return '\n'.join(lines)


def _uf_record_status(arg, value, ctx, record):
    """UNIFOR ``+6`` — record status: ``1`` if the record is NOT logically
    deleted, ``0`` if it is (PFT_LANGUAGE §9.1 / decompiled case ``0x2b``→
    ``0x36`` via ``IrbisIsDeleted``). The flag is read from ``ctx['deleted']``
    (the A1↔store contract); absent ⇒ treated as live (``1``)."""
    deleted = bool((ctx or {}).get('deleted'))
    return '0' if deleted else '1'


def _uf_urlcode(arg, value, ctx, record):
    """UNIFOR ``+3E`` / ``+3D`` — URL-encode / -decode a string (PFT_LANGUAGE
    §9.1). The leading ``E``/``D`` selects the direction; payload is the inline
    value (or the spec tail)."""
    direction = arg[:1].upper()
    src = value if value else arg[1:]
    src = src or ''
    import urllib.parse as _url
    if direction == 'D':
        return _url.unquote(src)
    # default to encode (E); quote keeps unreserved chars, encodes the rest.
    return _url.quote(src, safe='')


def _uf_postedit_seps(arg, value, ctx, record):
    """UNIFOR ``!`` — post-edit: collapse double subfield separators / spaces
    (SPEC §9.1 — a whole-output pass; here a no-op marker returning '')."""
    return ''


def _uf_postedit_rtf(arg, value, ctx, record):
    """UNIFOR ``+F`` — post-edit: strip RTF constructs (SPEC §9.1). No-op here."""
    return ''


def _uf_module(arg, value, ctx, record):
    """UNIFOR ``6`` — nested/template format ``6<name>`` or ``6<tmpl>#<p1>,...``
    (SPEC §9.1/§9.2). Resolves the module body from ``ctx['modules']`` (a
    ``{name: pft_body}`` map), substitutes ``%N`` params, and recursively
    evaluates. Unknown module → '' (carried, not a crash)."""
    name = arg
    params = []
    if '#' in arg:
        name, raw = arg.split('#', 1)
        params = raw.split(',')
    modules = (ctx or {}).get('modules') or {}
    body = modules.get(name)
    if body is None:
        return ''
    # %1..%9 parameter substitution (SPEC §9.2 template formats).
    for i, p in enumerate(params, start=1):
        body = body.replace('%%%d' % i, p)
    return eval(body, record, ctx)       # noqa: recursion is intentional


# Default registry (longest code key first so '+F' beats 'F', etc.).
register_unifor('3', _uf_date)
register_unifor('C', _uf_checksum)
register_unifor('A', _uf_occurrence)
register_unifor('P', _uf_occurrence)
register_unifor('9', _uf_strip_quotes)
register_unifor('Q', _uf_lower)
register_unifor('X', _uf_strip_angle)
register_unifor('E', _uf_first_words)
register_unifor('F', _uf_cut_after_words)
register_unifor('G', _uf_substr_marker)
register_unifor('T', _uf_translit)
register_unifor('L', _uf_term_ending)
register_unifor('0', _uf_full_record)
register_unifor('!', _uf_postedit_seps)
register_unifor('+F', _uf_postedit_rtf)
register_unifor('+6', _uf_record_status)
register_unifor('+3', _uf_urlcode)
register_unifor('6', _uf_module)


def _dispatch_unifor(spec, value, ctx, record):
    """Route a parsed UNIFOR call to its handler. ``spec`` is the leading-literal
    argument (code + remainder); ``value`` is the evaluated inline value, if any.
    Unknown code → '' (SPEC §15: diagnosable, never a silent crash)."""
    if spec is None:
        spec = ''
    # multi-char codes first
    for code in ('+F', '+I', '+1', '+7', '+3', '+9', '+5', '+4', '+6', '+0'):
        if spec.startswith(code):
            fn = UNIFOR.get(code)
            return fn(spec[len(code):], value, ctx, record) if fn else ''
    if not spec:
        return ''
    code = spec[0]
    fn = UNIFOR.get(code)
    if fn is None:
        return ''                         # degrade gracefully (Format error 99)
    return fn(spec[1:], value, ctx, record)


# --------------------------------------------------------------------------- #
# Tokenizer. PFT is whitespace-insensitive between commands; literals carry their
# own delimiters. We emit a flat token stream, then a recursive-descent parser
# builds the AST. Comments ``/* … EOL`` are stripped first.
# --------------------------------------------------------------------------- #
_COMMENT = re.compile(r'/\*[^\n]*')

# token kinds
T_FIELD, T_DUMMY, T_LIT, T_NUM, T_IDENT, T_PUNCT, T_UNIFOR = (
    'FIELD', 'DUMMY', 'LIT', 'NUM', 'IDENT', 'PUNCT', 'UNIFOR')

_KEYWORDS = {'if', 'then', 'else', 'fi', 'and', 'or', 'not', 'val', 'f', 's',
             'p', 'a', 'ref', 'mfn', 'rsum', 'rmin', 'rmax', 'ravr', 'l'}


class _Tok:
    __slots__ = ('kind', 'value', 'extra')

    def __init__(self, kind, value, extra=None):
        self.kind = kind
        self.value = value
        self.extra = extra

    def __repr__(self):
        return '<%s %r>' % (self.kind, self.value)


def _tokenize(src):
    src = _COMMENT.sub('', src)
    toks = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in ' \t\r\n':
            i += 1
            continue
        # literals
        if c == '"':
            j = src.find('"', i + 1)
            if j < 0:
                j = n
            toks.append(_Tok(T_LIT, src[i + 1:j], 'cond'))
            i = j + 1
            continue
        if c == "'":
            j = src.find("'", i + 1)
            if j < 0:
                j = n
            toks.append(_Tok(T_LIT, src[i + 1:j], 'uncond'))
            i = j + 1
            continue
        if c == '|':
            j = src.find('|', i + 1)
            if j < 0:
                j = n
            toks.append(_Tok(T_LIT, src[i + 1:j], 'rep'))
            i = j + 1
            continue
        # UNIFOR call: &name(arg) or &uf('...') — keep the raw call, parse later
        if c == '&':
            j, depth = i + 1, 0
            # read the name up to '('
            while j < n and src[j] != '(':
                j += 1
            # now scan balanced parens
            k = j
            while k < n:
                if src[k] == '(':
                    depth += 1
                elif src[k] == ')':
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
                k += 1
            toks.append(_Tok(T_UNIFOR, src[i:k]))
            i = k
            continue
        # field reference  v<tag>[^sub|*][*off.len]
        if c in 'vV':
            m = re.match(r'[vV](\d+)(\^[\*a-zA-Z0-9])?(\*\d+(?:\.\d+)?)?',
                         src[i:])
            if m and m.group(1):
                toks.append(_Tok(T_FIELD, m.group(0)))
                i += m.end()
                continue
        # dummy output d<tag> / n<tag>
        if c in 'dDnN':
            m = re.match(r'[dDnN](\d+)(\^[a-zA-Z0-9])?', src[i:])
            if m:
                toks.append(_Tok(T_DUMMY, m.group(0)))
                i += m.end()
                continue
        # number
        if c.isdigit():
            m = re.match(r'\d+(?:\.\d+)?', src[i:])
            toks.append(_Tok(T_NUM, m.group(0)))
            i += m.end()
            continue
        # identifier / keyword
        if c.isalpha():
            m = re.match(r'[A-Za-z]+', src[i:])
            word = m.group(0)
            toks.append(_Tok(T_IDENT, word))
            i += m.end()
            continue
        # comparison operators (two-char first)
        two = src[i:i + 2]
        if two in ('<>', '<=', '>='):
            toks.append(_Tok(T_PUNCT, two))
            i += 2
            continue
        if c in '(),+=<>:/#%':
            toks.append(_Tok(T_PUNCT, c))
            i += 1
            continue
        # mode commands Mmc, placement Xn/Cn, '*' etc — skipped (no-op in text IR)
        i += 1
    return toks


# --------------------------------------------------------------------------- #
# AST nodes. Each ``render(record, ctx, state)`` returns a string. ``state`` is
# the per-render mutable workspace (current repeat-instance index, output flags).
# --------------------------------------------------------------------------- #
class _Node:
    def render(self, record, ctx, state):
        return ''


class _Seq(_Node):
    """A concatenation of nodes (',' / '+' / juxtaposition)."""

    def __init__(self, parts):
        self.parts = parts

    def render(self, record, ctx, state):
        return ''.join(p.render(record, ctx, state) for p in self.parts)


class _Literal(_Node):
    def __init__(self, text, kind):
        self.text = text
        self.kind = kind            # 'cond' | 'rep' | 'uncond'

    def render(self, record, ctx, state):
        if self.kind == 'uncond':
            return self.text
        # cond/rep literals are gated by adjacent-field presence; the parser
        # attaches them to the field, so a standalone one falls back to: emit if
        # the current group instance exists (rep) or once (cond) — approximated
        # by the state's "last field emitted" flag.
        if state.get('emit_literal', True):
            return self.text
        return ''


class _Field(_Node):
    def __init__(self, tag, subfield, first_sub, off, length,
                 prefix=None, suffix=None):
        self.tag = tag
        self.subfield = subfield
        self.first_sub = first_sub
        self.off = off
        self.length = length
        self.prefix = prefix          # list[_Literal] before the field
        self.suffix = suffix          # list[_Literal] after the field

    def _one(self, inst, record, ctx, state):
        if self.first_sub:
            v = _first_subfield(inst)
        else:
            v = _inst_value(inst, self.subfield)
        if self.off is not None:
            v = _fragment(v, self.off, self.length)
        return v or ''

    def render(self, record, ctx, state):
        insts = _instances(record, self.tag)
        # inside a repeat group, only the current instance is visible
        gi = state.get('group_index')
        if gi is not None and state.get('group_tag') == self.tag:
            insts = [insts[gi]] if 0 <= gi < len(insts) else []
        # only non-empty occurrences are emitted; literals key off emitted order
        emitted = [self._one(x, record, ctx, state) for x in insts]
        emitted = [v for v in emitted if v]
        present_any = bool(emitted)
        last = len(emitted) - 1
        out = []
        cond_done = False                    # conditional literals emit once
        for k, v in enumerate(emitted):
            piece = ''
            for lit in (self.prefix or []):
                if lit.kind == 'rep_plus':       # |x|+ : not before the first
                    if k > 0:
                        piece += lit.text
                elif lit.kind == 'cond':         # "x" prefix: once, with the field
                    if not cond_done:
                        piece += lit.text
                else:                            # 'x' uncond / |x| rep
                    piece += lit.text
            piece += v
            for lit in (self.suffix or []):
                if lit.kind == 'plus_rep':       # +|x| : not after the last
                    if k < last:
                        piece += lit.text
                elif lit.kind == 'cond':         # "x" suffix: once
                    if not cond_done:
                        piece += lit.text
                else:                            # 'x' / |x| rep
                    piece += lit.text
            cond_done = True
            out.append(piece)
        # a conditional prefix literal must still print once even if the field has
        # exactly one (already handled); absent field => prefix/suffix suppressed.
        state['last_present'] = present_any
        return ''.join(out)


class _Dummy(_Node):
    """``d<tag>`` / ``n<tag>`` — emit attached conditional literals by presence."""

    def __init__(self, negate, tag, subfield, literals):
        self.negate = negate
        self.tag = tag
        self.subfield = subfield
        self.literals = literals     # the preceding conditional literals

    def render(self, record, ctx, state):
        has = present(record, self.tag, self.subfield)
        fire = (not has) if self.negate else has
        if not fire:
            return ''
        return ''.join(l.text for l in self.literals)


class _Mfn(_Node):
    def __init__(self, width):
        self.width = width

    def render(self, record, ctx, state):
        mfn = (ctx or {}).get('mfn', 0) or 0
        s = str(int(mfn))
        if self.width:
            s = s.rjust(self.width, '0')
        return s


class _Unifor(_Node):
    def __init__(self, spec_node, value_node):
        self.spec_node = spec_node       # _Node producing the code+arg literal
        self.value_node = value_node     # _Node producing the inline value (opt)

    def render(self, record, ctx, state):
        spec = self.spec_node.render(record, ctx, state) if self.spec_node else ''
        value = self.value_node.render(record, ctx, state) if self.value_node else ''
        try:
            return _dispatch_unifor(spec, value, ctx, record)
        except Exception:                # noqa: BLE001 — degrade, never crash
            return ''


class _Func(_Node):
    """val / f / s / rsum / rmin / rmax / ravr — numeric / string functions."""

    def __init__(self, name, args):
        self.name = name
        self.args = args                 # list[_Node]

    def render(self, record, ctx, state):
        name = self.name
        if name == 'val':
            # val() takes the FIRST numeric value of its formatted argument. For a
            # bare repeating field we read the first instance (so val(v999)==first
            # occurrence), else the whole formatted string (SPEC §8.1).
            arg = _unwrap_field(self.args[0]) if self.args else None
            if isinstance(arg, _Field):
                txt = field_value(record, arg.tag, arg.subfield)
            else:
                txt = self.args[0].render(record, ctx, state) if self.args else ''
            return _fmt_num(_to_num(txt))
        if name == 's':
            return ''.join(a.render(record, ctx, state) for a in self.args)
        if name == 'f':
            val = _to_num(self.args[0].render(record, ctx, state)) if self.args else 0
            width = int(_to_num(self.args[1].render(record, ctx, state))) \
                if len(self.args) > 1 else 0
            dec = int(_to_num(self.args[2].render(record, ctx, state))) \
                if len(self.args) > 2 else 0
            s = ('%.*f' % (dec, val)) if dec else str(int(val))
            return s.rjust(width) if width else s
        if name in ('rsum', 'rmin', 'rmax', 'ravr'):
            nums = []
            for a in self.args:
                # a repeat-aware numeric scan over all instances it references
                for piece in _iter_numeric(a, record, ctx, state):
                    nums.append(piece)
            if not nums:
                return '0'
            if name == 'rsum':
                return _fmt_num(sum(nums))
            if name == 'rmin':
                return _fmt_num(min(nums))
            if name == 'rmax':
                return _fmt_num(max(nums))
            return _fmt_num(sum(nums) / len(nums))
        return ''


def _unwrap_field(node):
    """If ``node`` is a _Field (possibly wrapped in a single-element _Seq), return
    that _Field; else return the node unchanged."""
    if isinstance(node, _Field):
        return node
    if isinstance(node, _Seq) and len(node.parts) == 1:
        return _unwrap_field(node.parts[0])
    return node


def _iter_numeric(node, record, ctx, state):
    """Yield numeric values of a node across all repeat instances of any single
    field it references (rsum/rmin/... support). Falls back to one scalar."""
    inner = _unwrap_field(node)
    if isinstance(inner, _Field):
        for inst in _instances(record, inner.tag):
            v = inner._one(inst, record, ctx, state)
            if v:
                yield _to_num(v)
        return
    txt = node.render(record, ctx, state)
    if txt:
        yield _to_num(txt)


class _Pred(_Node):
    """p(...) / a(...) used only inside IF conditions — returns '1' or ''."""

    def __init__(self, negate, field_node):
        self.negate = negate
        self.field_node = field_node

    def truth(self, record, ctx, state):
        if isinstance(self.field_node, _Field):
            has = present(record, self.field_node.tag, self.field_node.subfield)
        else:
            has = bool(self.field_node.render(record, ctx, state))
        return (not has) if self.negate else has

    def render(self, record, ctx, state):
        return '1' if self.truth(record, ctx, state) else ''


class _Compare(_Node):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def truth(self, record, ctx, state):
        lv = self.left.render(record, ctx, state)
        rv = self.right.render(record, ctx, state)
        op = self.op
        if op == '=':
            return lv == rv
        if op == '<>':
            return lv != rv
        if op == ':':
            return rv.lower() in lv.lower()
        # numeric/lexicographic for < <= > >=
        ln, rn = _to_num(lv), _to_num(rv)
        if op == '<':
            return ln < rn
        if op == '<=':
            return ln <= rn
        if op == '>':
            return ln > rn
        if op == '>=':
            return ln >= rn
        return False

    def render(self, record, ctx, state):
        return '1' if self.truth(record, ctx, state) else ''


class _BoolOp(_Node):
    def __init__(self, op, parts):
        self.op = op                    # 'and' | 'or'
        self.parts = parts

    def truth(self, record, ctx, state):
        vals = [_truth(p, record, ctx, state) for p in self.parts]
        return all(vals) if self.op == 'and' else any(vals)

    def render(self, record, ctx, state):
        return '1' if self.truth(record, ctx, state) else ''


class _NotOp(_Node):
    def __init__(self, part):
        self.part = part

    def truth(self, record, ctx, state):
        return not _truth(self.part, record, ctx, state)

    def render(self, record, ctx, state):
        return '1' if self.truth(record, ctx, state) else ''


def _truth(node, record, ctx, state):
    """Evaluate any node as a boolean (IF condition context)."""
    if hasattr(node, 'truth'):
        return node.truth(record, ctx, state)
    return bool(node.render(record, ctx, state))


class _If(_Node):
    def __init__(self, cond, then_node, else_node):
        self.cond = cond
        self.then_node = then_node
        self.else_node = else_node

    def render(self, record, ctx, state):
        if _truth(self.cond, record, ctx, state):
            return self.then_node.render(record, ctx, state) if self.then_node else ''
        return self.else_node.render(record, ctx, state) if self.else_node else ''


class _Group(_Node):
    """Repeat group ``(…)`` — evaluate the body once per instance of the (single)
    repeating field referenced inside (SPEC §10). Emits joined; eval_lines splits
    on the group boundary so multi-line group output is preserved."""

    def __init__(self, body, tags):
        self.body = body
        self.tags = tags                # field tags referenced in the group

    def _max_instances(self, record):
        return max((len(_instances(record, t)) for t in self.tags), default=1)

    def render(self, record, ctx, state):
        n = self._max_instances(record)
        if n <= 1:
            saved = state.get('group_index'), state.get('group_tag')
            state['group_index'] = None
            out = self.body.render(record, ctx, state)
            state['group_index'], state['group_tag'] = saved
            return out
        lead = self.tags[0] if self.tags else None
        out = []
        saved_i, saved_t = state.get('group_index'), state.get('group_tag')
        for k in range(n):
            state['group_index'] = k
            state['group_tag'] = lead
            out.append(self.body.render(record, ctx, state))
        state['group_index'], state['group_tag'] = saved_i, saved_t
        return ''.join(out)

    def render_lines(self, record, ctx, state):
        n = self._max_instances(record)
        lead = self.tags[0] if self.tags else None
        lines = []
        saved_i, saved_t = state.get('group_index'), state.get('group_tag')
        for k in range(max(n, 1)):
            state['group_index'] = k if n > 1 else None
            state['group_tag'] = lead
            lines.append(self.body.render(record, ctx, state))
        state['group_index'], state['group_tag'] = saved_i, saved_t
        return lines


# --------------------------------------------------------------------------- #
# numeric helpers
# --------------------------------------------------------------------------- #
_NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')


def _to_num(text):
    """``val()`` semantics — first number in the text, else 0."""
    if isinstance(text, (int, float)):
        return text
    m = _NUM_RE.search(str(text or ''))
    if not m:
        return 0
    s = m.group(0)
    return float(s) if '.' in s else int(s)


def _fmt_num(n):
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    return str(n)


# --------------------------------------------------------------------------- #
# Parser — recursive descent over the token stream.
# --------------------------------------------------------------------------- #
class _Parser:
    def __init__(self, toks, strict=False):
        self.toks = toks
        self.pos = 0
        self.strict = strict

    def _peek(self, k=0):
        j = self.pos + k
        return self.toks[j] if j < len(self.toks) else None

    def _next(self):
        t = self._peek()
        self.pos += 1
        return t

    def _at_keyword(self, word):
        t = self._peek()
        return t is not None and t.kind == T_IDENT and t.value.lower() == word

    # ---- top: a sequence of terms separated by ',' / '+' / juxtaposition ---- #
    def parse_sequence(self, stoppers=()):
        parts = []
        tags = []
        while True:
            t = self._peek()
            if t is None:
                break
            if t.kind == T_IDENT and t.value.lower() in stoppers:
                break
            if t.kind == T_PUNCT and t.value in (',', '+'):
                self._next()
                continue
            if t.kind == T_PUNCT and t.value == ')':
                break
            node = self.parse_term(tags)
            if node is not None:
                parts.append(node)
            else:
                # unrecognized token: skip (graceful degradation)
                if self.strict:
                    raise PftError('unexpected token %r' % (t.value,), 99)
                self._next()
        seq = _Seq(parts)
        seq.tags = tags
        return seq

    def parse_term(self, tags):
        t = self._peek()
        if t is None:
            return None
        # IF … FI
        if t.kind == T_IDENT and t.value.lower() == 'if':
            return self.parse_if(tags)
        # repeat group
        if t.kind == T_PUNCT and t.value == '(':
            return self.parse_group(tags)
        # field, with optional prefix/suffix literals
        if t.kind == T_FIELD:
            return self.parse_field(tags, prefix=None)
        # leading conditional/repeat literal — may be a field prefix or dummy lit
        if t.kind == T_LIT:
            return self.parse_literal_led(tags)
        if t.kind == T_DUMMY:
            return self.parse_dummy(tags, leading=[])
        if t.kind == T_UNIFOR:
            self._next()
            return self.parse_unifor(t.value)
        if t.kind == T_IDENT:
            return self.parse_ident(tags)
        if t.kind == T_NUM:
            self._next()
            return _Literal(t.value, 'uncond')
        if t.kind == T_PUNCT and t.value in ('/', '#', '%', '=', '<', '>', ':'):
            self._next()                  # placement / stray operator -> no-op
            return _Seq([])               # empty node (already advanced)
        return None

    def parse_literal_led(self, tags):
        """A literal that may prefix a field/dummy, or stand alone."""
        lits = []
        while self._peek() and self._peek().kind == T_LIT:
            lit = self._next()
            # |x|+ prefix marker
            kind = lit.extra
            nxt = self._peek()
            if (kind == 'rep' and nxt and nxt.kind == T_PUNCT
                    and nxt.value == '+'):
                self._next()
                lits.append(_Literal(lit.value, 'rep_plus'))
            else:
                lits.append(_Literal(lit.value, kind))
        nxt = self._peek()
        if nxt and nxt.kind == T_FIELD:
            return self.parse_field(tags, prefix=lits)
        if nxt and nxt.kind == T_DUMMY:
            return self.parse_dummy(tags, leading=lits)
        # standalone literals (no adjacent field): emit each once. A conditional
        # "…" with nothing to be conditional on degenerates to always-emit
        # (SPEC §5 — it is the field that gates it; absent, it just prints).
        return _Seq([_Literal(l.text, 'uncond') for l in lits])

    def parse_field(self, tags, prefix):
        t = self._next()
        m = re.match(r'[vV](\d+)(?:\^(\*|[a-zA-Z0-9]))?(?:\*(\d+)(?:\.(\d+))?)?$',
                     t.value)
        if m is None:                     # defensive: never crash on a weird ref
            return _Seq([])
        tag = m.group(1)
        sub = m.group(2)
        first_sub = (sub == '*')
        subfield = None if (sub is None or sub == '*') else sub
        off = int(m.group(3)) if m.group(3) is not None else None
        length = int(m.group(4)) if m.group(4) is not None else None
        if tag not in tags:
            tags.append(tag)
        # gather trailing prefix/suffix literals. PFT separator idioms (SPEC §5):
        #   |x|+  repeatable PREFIX before each instance except the FIRST
        #   +|x|  repeatable SUFFIX after each instance except the LAST
        #   |x|   plain repeatable, "x" conditional — emitted per instance.
        # The first three are inter-instance separators; we fold them into the
        # field node so a bare repeating field renders cleanly. Stop at ','.
        sep_prefix = list(prefix or [])
        suffix = []
        while True:
            nxt = self._peek()
            if nxt and nxt.kind == T_PUNCT and nxt.value == '+':
                # +|x| suffix (not after last instance)
                after = self._peek(1)
                if after and after.kind == T_LIT and after.extra == 'rep':
                    self._next()
                    self._next()
                    suffix.append(_Literal(after.value, 'plus_rep'))
                    continue
                break
            if nxt and nxt.kind == T_LIT:
                after = self._peek(1)
                if (nxt.extra == 'rep' and after and after.kind == T_PUNCT
                        and after.value == '+'):
                    # |x|+ prefix-except-first separator -> applies to this field
                    self._next()
                    self._next()
                    sep_prefix.append(_Literal(nxt.value, 'rep_plus'))
                    continue
                if nxt.extra in ('cond', 'rep'):
                    self._next()
                    suffix.append(_Literal(nxt.value, nxt.extra))
                    continue
            break
        return _Field(tag, subfield, first_sub, off, length,
                      prefix=sep_prefix, suffix=suffix)

    def parse_dummy(self, tags, leading):
        t = self._next()
        m = re.match(r'([dDnN])(\d+)(?:\^([a-zA-Z0-9]))?$', t.value)
        negate = m.group(1).lower() == 'n'
        tag = m.group(2)
        subfield = m.group(3)
        # dummy literals are the leading conditional literals; if none captured,
        # also pull any immediately-following ones (PFT allows either side here).
        lits = list(leading)
        return _Dummy(negate, tag, subfield, lits)

    def parse_unifor(self, raw):
        """Parse the raw ``&name(...)`` text into a _Unifor node. The argument is
        a mini-format whose FIRST literal carries the code + its static argument
        (e.g. ``'C'``, ``'Av920#1'``, ``'30'``); anything after is the inline
        VALUE format (e.g. ``v10^a`` in ``&unifor('C'v10^a)``).

        We peel the leading literal off the *raw* inner string directly so the
        field-prefix folding (``parse_literal_led``) can't merge ``'C'`` into the
        following ``v10^a`` (that merge is correct for normal output, wrong here).
        """
        inner = raw[raw.find('(') + 1:raw.rfind(')')]
        inner = inner.strip()
        spec_text = ''
        rest = inner
        if inner[:1] in ("'", '"', '|'):
            close = inner.find(inner[0], 1)
            if close >= 0:
                spec_text = inner[1:close]
                rest = inner[close + 1:]
        spec_node = _Literal(spec_text, 'uncond') if spec_text or rest != inner \
            else None
        # the remaining text is the inline value mini-format (may be empty)
        rest = rest.strip().lstrip(',').strip()
        value_node = None
        if rest:
            value_node = _Parser(_tokenize(rest), self.strict).parse_sequence()
        # if no quoted spec was found, fall back to evaluating the whole inner as
        # the spec (covers &unifor(v910) style dynamic specs).
        if spec_node is None:
            value_seq = _Parser(_tokenize(inner), self.strict).parse_sequence()
            return _Unifor(value_seq, None)
        return _Unifor(spec_node, value_node)

    def parse_ident(self, tags):
        t = self._next()
        word = t.value.lower()
        if word == 'mfn':
            width = None
            if self._peek() and self._peek().kind == T_PUNCT \
                    and self._peek().value == '(':
                self._next()
                inner = self._collect_until_close()
                width = int(_to_num(_render_inline(inner))) or None
            return _Mfn(width)
        if word in ('p', 'a'):
            # predicate: p(field) / a(field)
            if self._peek() and self._peek().value == '(':
                self._next()
                arg_toks = self._collect_until_close()
                arg = _Parser(arg_toks, self.strict).parse_sequence()
                fld = arg.parts[0] if arg.parts else _Seq([])
                return _Pred(word == 'a', fld)
            return None
        if word in ('val', 's', 'f', 'rsum', 'rmin', 'rmax', 'ravr'):
            args = self._parse_call_args(tags)
            return _Func(word, args)
        if word in ('ref', 'l'):
            # ref()/l() need the inverted index / other DB — degrade to '' but
            # consume the argument list so parsing continues (SPEC §2.1 carried).
            if self._peek() and self._peek().value == '(':
                self._next()
                self._collect_until_close()
            return _Seq([])
        if word == 'not':
            sub = self.parse_term(tags)
            return _NotOp(sub if sub is not None else _Seq([]))
        # mode commands (mhl/mpl/mpu/mdl…) and placement — no-op text nodes
        if re.match(r'^m[phd][ul]?$', word):
            return _Seq([])
        if re.match(r'^[xc]\d+$', word):
            return _Seq([])
        # unknown identifier -> emit as literal text (best-effort)
        return _Seq([])

    def _parse_call_args(self, tags):
        args = []
        if not (self._peek() and self._peek().kind == T_PUNCT
                and self._peek().value == '('):
            return args
        self._next()                      # consume '('
        depth = 1
        cur = []
        while self.pos < len(self.toks) and depth > 0:
            t = self._next()
            if t.kind == T_PUNCT and t.value == '(':
                depth += 1
                cur.append(t)
            elif t.kind == T_PUNCT and t.value == ')':
                depth -= 1
                if depth == 0:
                    break
                cur.append(t)
            elif t.kind == T_PUNCT and t.value == ',' and depth == 1:
                args.append(_Parser(cur, self.strict).parse_sequence())
                cur = []
            else:
                cur.append(t)
        if cur:
            args.append(_Parser(cur, self.strict).parse_sequence())
        for a in args:
            for tg in getattr(a, 'tags', []):
                if tg not in tags:
                    tags.append(tg)
        return args

    def _collect_until_close(self):
        depth = 1
        out = []
        while self.pos < len(self.toks) and depth > 0:
            t = self._next()
            if t.kind == T_PUNCT and t.value == '(':
                depth += 1
            elif t.kind == T_PUNCT and t.value == ')':
                depth -= 1
                if depth == 0:
                    break
            out.append(t)
        return out

    def parse_group(self, tags):
        self._next()                      # consume '('
        inner = self._collect_until_close()
        sub = _Parser(inner, self.strict)
        body = sub.parse_sequence()
        gtags = list(getattr(body, 'tags', []))
        for tg in gtags:
            if tg not in tags:
                tags.append(tg)
        return _Group(body, gtags)

    # ---- IF condition / branches ---- #
    def parse_if(self, tags):
        self._next()                      # consume 'if'
        cond = self.parse_condition(tags)
        if not self._at_keyword('then'):
            if self.strict:
                raise PftError('IF without THEN', 8)
            return _Seq([])               # degrade
        self._next()                      # consume 'then'
        then_node = self.parse_sequence(stoppers=('else', 'fi'))
        for tg in getattr(then_node, 'tags', []):
            if tg not in tags:
                tags.append(tg)
        else_node = None
        if self._at_keyword('else'):
            self._next()
            else_node = self.parse_sequence(stoppers=('fi',))
            for tg in getattr(else_node, 'tags', []):
                if tg not in tags:
                    tags.append(tg)
        if self._at_keyword('fi'):
            self._next()
        elif self.strict:
            raise PftError('IF without FI', 53)
        return _If(cond, then_node, else_node)

    def parse_condition(self, tags):
        return self._parse_or(tags)

    def _parse_or(self, tags):
        parts = [self._parse_and(tags)]
        while self._at_keyword('or'):
            self._next()
            parts.append(self._parse_and(tags))
        return parts[0] if len(parts) == 1 else _BoolOp('or', parts)

    def _parse_and(self, tags):
        parts = [self._parse_not(tags)]
        while self._at_keyword('and'):
            self._next()
            parts.append(self._parse_not(tags))
        return parts[0] if len(parts) == 1 else _BoolOp('and', parts)

    def _parse_not(self, tags):
        if self._at_keyword('not'):
            self._next()
            # NOT (expr) or NOT predicate
            if self._peek() and self._peek().kind == T_PUNCT \
                    and self._peek().value == '(':
                self._next()
                inner = self._collect_until_close()
                sub = _Parser(inner, self.strict).parse_condition(tags)
                return _NotOp(sub)
            return _NotOp(self._parse_compare(tags))
        return self._parse_compare(tags)

    def _parse_compare(self, tags):
        # parenthesized condition
        if self._peek() and self._peek().kind == T_PUNCT \
                and self._peek().value == '(':
            self._next()
            inner = self._collect_until_close()
            return _Parser(inner, self.strict).parse_condition(tags)
        left = self.parse_operand(tags)
        t = self._peek()
        if t and t.kind == T_PUNCT and t.value in ('=', '<>', '<', '<=',
                                                   '>', '>=', ':'):
            op = self._next().value
            right = self.parse_operand(tags)
            return _Compare(left, op, right)
        # bare operand as a truth value (e.g. p(...) or a field)
        return left

    def parse_operand(self, tags):
        """A single value operand inside a condition (field, literal, unifor,
        p()/a(), function, number)."""
        t = self._peek()
        if t is None:
            return _Seq([])
        if t.kind == T_FIELD:
            return self.parse_field(tags, prefix=None)
        if t.kind == T_LIT:
            self._next()
            return _Literal(t.value, 'uncond')
        if t.kind == T_NUM:
            self._next()
            return _Literal(t.value, 'uncond')
        if t.kind == T_UNIFOR:
            self._next()
            return self.parse_unifor(t.value)
        if t.kind == T_IDENT:
            return self.parse_ident(tags)
        if t.kind == T_PUNCT and t.value == '(':
            self._next()
            inner = self._collect_until_close()
            return _Parser(inner, self.strict).parse_sequence()
        self._next()
        return _Seq([])


def _render_inline(toks):
    """Render a small token list to text (used for mfn(width) etc.)."""
    node = _Parser(toks).parse_sequence()
    return node.render({}, {}, {})


# --------------------------------------------------------------------------- #
# Public API — the contract A2/A3 consume (SPEC_api_contracts §3.1).
# --------------------------------------------------------------------------- #
def _compile(fmt, strict=False):
    toks = _tokenize(fmt or '')
    return _Parser(toks, strict).parse_sequence()


def eval(fmt, record, ctx=None, strict=False):
    """Format ``record`` with the PFT ``fmt`` string → a single string.

    This is the keystone contract (SPEC_api_contracts §3.1 / M4):
    ``pft.eval(fmt, record, ctx) -> str``.

    Parameters
    ----------
    fmt : str
        Inline PFT source (a format body or a reference resolved by the caller).
    record : dict
        Field/subfield draft (see module docstring). ``None`` → empty record.
    ctx : dict | None
        Per-render workspace carrying, per the A1↔A3 contract:
          * ``mfn``      — current record number (for ``mfn``/``mfn(d)``);
          * ``now``      — datetime override for UNIFOR ``3`` (testability);
          * ``modules``  — ``{name: pft_body}`` for ``&uf('6<name>')`` (A1/A3);
          * ``vars``     — ``&uf('+7…')`` registers (A3 read/write; A2 read-only);
          * ``counters`` — persistent ``&uf('++C…')`` counters (A3);
          * ``crossDb``  — other-DB resolver (``&uf('D…')`` — degraded if absent);
          * ``tenant``   — tenant_id / search_path (isolation invariant).
        Unknown keys are ignored. ``ctx`` is never mutated by ``eval`` itself.
    strict : bool
        When True, raise :class:`PftError` on parse/format errors (editor/preview
        path). Default False → degrade gracefully (skip unparsable constructs).

    Returns
    -------
    str
        The formatted text (the IR collapsed to a string in this slice).
    """
    ctx = ctx or {}
    try:
        ast = _compile(fmt, strict)
    except PftError:
        if strict:
            raise
        return ''
    state = {}
    try:
        return ast.render(record or {}, ctx, state)
    except PftError:
        if strict:
            raise
        return ''
    except Exception:                    # noqa: BLE001 — never crash a render
        if strict:
            raise
        return ''


def eval_lines(fmt, record, ctx=None, strict=False):
    """Format ``record`` → a list of strings, one per repeat-group instance.

    The multi-line companion to :func:`eval` (SPEC_api_contracts §3.1:
    ``pft.evalLines(pftRef, record, ctx) -> string[]``). Used by the .gbl engine
    (A3) for ``F``/``ADD`` modes that produce one output line per field instance.

    If the format contains a single top-level repeat group ``(…)``, each
    instance becomes its own line. Otherwise the whole render is one line. Empty
    lines are preserved (the caller decides whether to drop them).
    """
    ctx = ctx or {}
    try:
        ast = _compile(fmt, strict)
    except PftError:
        if strict:
            raise
        return []
    state = {}
    rec = record or {}
    # find a single top-level group to expand line-wise
    group = None
    if isinstance(ast, _Seq):
        groups = [p for p in ast.parts if isinstance(p, _Group)]
        if len(groups) == 1 and len(ast.parts) == 1:
            group = groups[0]
    try:
        if group is not None:
            return group.render_lines(rec, ctx, state)
        text = ast.render(rec, ctx, state)
        return text.split('\n') if '\n' in text else [text]
    except Exception:                    # noqa: BLE001
        if strict:
            raise
        return []
