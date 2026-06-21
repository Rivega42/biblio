#!/usr/bin/env python3
"""Global-correction ``.gbl`` executor (gap A3, epic #188).

Implements SPEC_engine_gbl.md, FIRST shippable slice: a self-contained,
pure-stdlib parser + applier + preview for the core ИРБИС batch-correction
operators, with the PFT (ФОРМАТ) evaluation deliberately factored out behind a
``format_eval`` hook so the module works *before* the A1 PFT engine
(``access.pft``) lands and transparently delegates to it once it does.

What this module is
-------------------
ИРБИС ``IC_gbl`` ports a ``.gbl`` job — a parameter header plus a sequence of
operators — and applies it to each record of a selection. Each operator sees the
record in the state the previous operators left it in (GLOBAL_CORRECTION §1.0,
``txt:5920``); ``apply`` mutates a *copy* so the caller's record is never touched.

Record model (the slice's JSON shape, SPEC §0 "Модель записи")
--------------------------------------------------------------
A record is a dict ``tag -> list of field instances``; each instance is a dict of
``subfield letter -> value`` with the whole-field value under the empty key ``''``::

    {
      "200": [{"a": "Заглавие", "f": "Иванов"}],
      "910": [{"b": "1024365"}, {"b": "1024366"}],
      "920": [{"": "PAZK"}],
    }

Convenience: a bare string field value (``{"920": "PAZK"}``) or a single dict
(``{"200": {"a": "..."}}``) are accepted on input and normalised on the way in.

Operators implemented in THIS slice (GLOBAL_CORRECTION §1.3)
-----------------------------------------------------------
  * ``ADD``   — add a new field repetition (whole field) or a subfield.
  * ``REP``   — replace a field / subfield wholesale (empty ФОРМАТ 1 => delete).
  * ``CHA`` / ``CHAC`` — replace a substring (CHAC case-sensitive, CHA not).
  * ``DEL``   — delete a field repetition or a subfield (incl. F-mode '1'/'0').
  * ``DELR`` / ``UNDEL`` — logical record delete / undelete (status flag).
  * ``EMPTY`` — clear the record.
  * ``IF … FI`` — conditional block (ФОРМАТ result ``'1'`` gates the body).
  * ``REPEAT … UNTIL`` — loop the body while UNTIL's ФОРМАТ yields ``'1'``
    (hard iteration cap, SPEC §3.4 R loop-guard).
  * ``PUTLOG`` / ``PUTFLD`` — append a protocol line (PUTFLD ≡ PUTLOG, deprecated).
  * ``//`` — comment (kept in the AST for protocol fidelity).

Occurrence selectors (3rd line, GLOBAL_CORRECTION §1.1): ``*`` ALL · ``N`` n-th ·
``L`` last · ``L-N`` n-th from end · ``F`` by-format (i-th ФОРМАТ 1 line drives the
i-th repetition).

Not in this slice (carried, not lost): ``NEWMFN/NEWREC/CORREC/END`` (other-record
ops), ``UNDOR`` (copy history), ``DEFFLD/GETFLD`` (model fields), ``ALL``. These
operator names still *parse* (so a real job is never silently truncated) and are
attached to the AST as ``UnsupportedOp`` nodes that ``apply`` skips with a recorded
note; only the listed operators execute. ``NEWMFN/NEWREC/CORREC`` consume their
``… END`` body during parsing so the surrounding job stays structurally valid.

The format_eval boundary (SPEC §2)
----------------------------------
ФОРМАТ 1/2 and every ``&uf(...)`` are ordinary PFT formats evaluated on the current
record — this module does NOT interpret PFT. It calls a single hook,
``format_eval(fmt, record, ctx)`` (one string) / ``format_eval_lines`` (a list, for
F-mode and whole-field ADD). Resolution order (``resolve_format_eval``):

  1. an explicit ``ctx['format_eval']`` callable (tests inject literal/field stubs);
  2. ``access.pft.eval`` if that module is importable (A1, once it lands);
  3. the built-in ``stub_format_eval`` — a deliberately minimal evaluator that
     understands quoted literals ``'…'``, ``%n`` parameter substitution, bare
     ``vNNN[^x]`` field references and ``#`` (the empty-string producer) so the
     slice's tests run with no PFT engine at all.

This keeps A3 unblocked on A1 while making the delegation a one-line swap.
"""
import copy


# --------------------------------------------------------------------------- #
# Record model — normalisation + field/subfield accessors.
# A field is stored as a list of instances; an instance is {subfield: value}
# with the whole-field text under the '' key. Input is liberally normalised.
# --------------------------------------------------------------------------- #
def _norm_instance(inst):
    """Coerce one field instance to a ``{subfield: value}`` dict."""
    if isinstance(inst, dict):
        return dict(inst)
    # a bare string instance is the whole-field value
    return {'': '' if inst is None else str(inst)}


def normalize_record(record):
    """Return a canonical ``tag -> [instance dict]`` copy of ``record``.

    Accepts the liberal input shapes (bare string field, single dict, or list)
    and yields the strict internal form. Never mutates the input."""
    out = {}
    for tag, raw in (record or {}).items():
        tag = str(tag)
        if raw is None:
            out[tag] = []
        elif isinstance(raw, list):
            out[tag] = [_norm_instance(i) for i in raw]
        else:
            out[tag] = [_norm_instance(raw)]
    return out


def _field(record, tag):
    return record.setdefault(str(tag), [])


def field_values(record, tag, subfield=None):
    """All values of ``tag`` (a given subfield, or whole-field when subfield is
    None), one per repetition that actually carries it."""
    out = []
    for inst in record.get(str(tag), []):
        v = _inst_get(inst, subfield)
        if v != '':
            out.append(v)
    return out


def _inst_get(inst, subfield):
    """Read a subfield from one instance (None => whole-field ''). Subfield
    letters match case-insensitively (ИРБИС ^A == ^a)."""
    if subfield is None:
        return inst.get('', '')
    return inst.get(subfield) or inst.get(subfield.lower()) \
        or inst.get(subfield.upper()) or ''


def _inst_set(inst, subfield, value):
    inst['' if subfield is None else subfield] = value


# --------------------------------------------------------------------------- #
# AST node types. Lightweight dict-like objects (no external deps); ``kind`` is
# the dispatch key for ``apply``. Closing markers (FI/UNTIL/END) are NOT nodes —
# they are consumed by the parser into block structure (SPEC §1.3).
# --------------------------------------------------------------------------- #
class Op(dict):
    """An AST operator node. A thin dict subclass so it pretty-prints and is
    trivially serialisable, with attribute access for readability."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __repr__(self):
        return 'Op(%r)' % (dict(self),)


class Program(dict):
    """Top-level AST: ``{'params': [...], 'body': [Op,...], 'warnings': [...]}``."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)


class ParseError(ValueError):
    """Raised on a malformed job (unknown operator, unclosed block, bad %n)."""


# Occurrence selector kinds (3rd line of a field operator).
OCC_ALL, OCC_NTH, OCC_LAST, OCC_LAST_MINUS, OCC_BY_FORMAT = \
    'ALL', 'NTH', 'LAST', 'LAST_MINUS', 'BY_FORMAT'

_FIELD_OPS = ('ADD', 'REP', 'CHA', 'CHAC', 'DEL')
# Other-record / model-field operators: parsed for fidelity, not executed here.
_OTHER_RECORD = ('NEWMFN', 'NEWREC', 'CORREC')
_PLACEHOLDER = 'XXXXXXXXXXXXXXXXXXX'


def _is_placeholder(line):
    """A line that stands for ∅ (SPEC §1.1): empty, or the ``XXXX…`` filler."""
    s = line.strip()
    return s == '' or set(s) == {'X'}


def _norm_fmt(line):
    """Normalise a ФОРМАТ line: the placeholder becomes the empty string ∅."""
    return '' if _is_placeholder(line) else line


def _parse_occ(line):
    """Parse the 3rd-line occurrence selector into an ``Occ`` tuple."""
    s = (line or '').strip()
    if s == '' or s == '*':
        return (OCC_ALL, None)
    up = s.upper()
    if up == 'F':
        return (OCC_BY_FORMAT, None)
    if up == 'L':
        return (OCC_LAST, None)
    if up.startswith('L-'):
        try:
            return (OCC_LAST_MINUS, int(up[2:]))
        except ValueError:
            return (OCC_ALL, None)
    try:
        return (OCC_NTH, int(s))
    except ValueError:
        # unknown selector — be permissive, treat as ALL (parity: server is lax)
        return (OCC_ALL, None)


def _parse_tag(line):
    """Split ``<tag>[^<sub>]`` (2nd line). Returns ``(tag, subfield|None)``."""
    s = (line or '').strip()
    if '^' in s:
        tag, sub = s.split('^', 1)
        return (tag.strip(), (sub.strip() or None))
    return (s, None)


# --------------------------------------------------------------------------- #
# Parser — table-driven by operator "arity" in lines (SPEC §1.2).
# --------------------------------------------------------------------------- #
def parse(gbl_text):
    """Parse a ``.gbl`` job (str or CP1251 bytes) into a :class:`Program` AST.

    Line-significant grammar (GLOBAL_CORRECTION §2):
      * line 1 = parameter count (0..9);
      * then 2 lines per parameter (value-or-.MNU/.WSS, then caption);
      * then operator groups, each a name line plus its fixed extra lines.

    Field operators (ADD/REP/CHA/CHAC/DEL) take 5 lines; flow operators their own
    count; ``IF…FI`` / ``REPEAT…UNTIL`` / ``NEWMFN…END`` parse into nested blocks.
    Raises :class:`ParseError` on an unknown operator, an unclosed block, or a
    ``%n`` reference beyond the declared parameter count."""
    if isinstance(gbl_text, (bytes, bytearray)):
        gbl_text = bytes(gbl_text).decode('cp1251')
    # Keep blank lines (significant), drop the trailing newline split artefact.
    lines = gbl_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    # ---- parameter header (line 1 = count, then 2 lines per param) ----------
    pos = 0
    if not lines or lines[0].strip() == '':
        raise ParseError('empty job: missing parameter-count line')
    try:
        nparams = int(lines[0].strip())
    except ValueError:
        raise ParseError('line 1: parameter count must be an integer, got %r'
                         % lines[0])
    pos = 1
    params = []
    for i in range(nparams):
        if pos + 1 >= len(lines):
            raise ParseError('parameter %d: truncated header' % (i + 1))
        value, caption = lines[pos], lines[pos + 1]
        source = 'prompt'
        if value.strip() == '':
            source = 'prompt'
        elif value.strip().lower().endswith('.mnu'):
            source = 'mnu'
        elif value.strip().lower().endswith('.wss'):
            source = 'wss'
        else:
            source = 'literal'
        params.append(Op(idx=i + 1, source=source,
                         value=value.strip(), caption=caption.strip()))
        pos += 2

    warnings = []
    body, pos = _parse_ops(lines, pos, nparams, warnings, stop=None)
    prog = Program(params=params, body=body, warnings=warnings)
    return prog


# Single-line flow / record operators -> their AST kind.
_RECORD_OPS = {'DELR': 'DELR', 'UNDEL': 'UNDEL', 'EMPTY': 'EMPTY', 'ALL': 'ALL'}


def _parse_ops(lines, pos, nparams, warnings, stop):
    """Parse operators until EOF or one of the ``stop`` closing markers.

    ``stop`` is a set of upper-case marker names (e.g. ``{'FI'}``) or None for
    top level. Returns ``(body, pos_after_marker_or_eof)``."""
    body = []
    n = len(lines)
    while pos < n:
        name_line = lines[pos]
        name = name_line.strip()
        up = name.upper()

        # Skip wholly blank lines between operators (filler / formatting).
        if name == '':
            pos += 1
            continue

        if stop is not None and up in stop:
            return body, pos + 1            # consume the closing marker

        # ---- comment // (up to 4 following text lines, but real files use 1) -
        if name.startswith('//') or name.startswith('/*'):
            body.append(Op(kind='COMMENT', text=name))
            pos += 1
            continue

        # ---- field operators: 5 lines total -------------------------------- #
        if up in _FIELD_OPS:
            op, pos = _parse_field_op(up, lines, pos, nparams)
            body.append(op)
            continue

        # ---- IF … FI ------------------------------------------------------- #
        if up == 'IF':
            cond = _need(lines, pos + 1, 'IF: missing condition format')
            _check_params(cond, nparams)
            inner, pos = _parse_ops(lines, pos + 2, nparams, warnings, stop={'FI'})
            body.append(Op(kind='IF', cond=_norm_fmt(cond), body=inner))
            continue

        # ---- REPEAT … UNTIL ------------------------------------------------ #
        if up == 'REPEAT':
            inner, pos, until = _parse_repeat(lines, pos + 1, nparams, warnings)
            _check_params(until, nparams)
            body.append(Op(kind='REPEAT', body=inner, until=_norm_fmt(until)))
            continue

        # ---- PUTLOG / PUTFLD (deprecated alias) ---------------------------- #
        if up in ('PUTLOG', 'PUTFLD'):
            fmt = _need(lines, pos + 1, '%s: missing format line' % up)
            _check_params(fmt, nparams)
            if up == 'PUTFLD':
                warnings.append('PUTFLD is deprecated; use PUTLOG (line %d)'
                                % (pos + 1))
            body.append(Op(kind='PUTLOG', fmt=_norm_fmt(fmt), deprecated=(up == 'PUTFLD')))
            pos += 2
            continue

        # ---- single-line record ops --------------------------------------- #
        if up in _RECORD_OPS:
            kind = _RECORD_OPS[up]
            op = Op(kind=kind)
            if kind == 'ALL':
                op['supported'] = False
                warnings.append('ALL parsed but not executed in this slice (line %d)'
                                % (pos + 1))
            body.append(op)
            pos += 1
            continue

        # ---- other-record blocks: NEWMFN / NEWREC / CORREC … END ----------- #
        if up in _OTHER_RECORD:
            op, pos = _parse_other_record(up, lines, pos, nparams, warnings)
            body.append(op)
            continue

        # ---- model-field ops (experimental): DEFFLD (5 lines) / GETFLD (2) - #
        if up == 'DEFFLD':
            tag = _need(lines, pos + 1, 'DEFFLD: missing tag')
            warnings.append('DEFFLD experimental, not executed (line %d)' % (pos + 1))
            body.append(Op(kind='DEFFLD', tag=tag.strip(), supported=False))
            pos += 5
            continue
        if up == 'GETFLD':
            tag = _need(lines, pos + 1, 'GETFLD: missing tag')
            warnings.append('GETFLD experimental, not executed (line %d)' % (pos + 1))
            body.append(Op(kind='GETFLD', tag=tag.strip(), supported=False))
            pos += 2
            continue

        # ---- stray closing markers at the wrong level / unknown operator --- #
        if up in ('FI', 'UNTIL', 'END'):
            raise ParseError('line %d: unexpected %s (no open block)'
                             % (pos + 1, up))
        raise ParseError('line %d: unknown operator %r' % (pos + 1, name))

    # EOF reached.
    if stop is not None:
        raise ParseError('unclosed block: expected %s before end of job'
                         % '/'.join(sorted(stop)))
    return body, pos


def _parse_field_op(up, lines, pos, nparams):
    """Parse a 5-line field operator (name already at ``pos``)."""
    if pos + 4 >= len(lines):
        raise ParseError('line %d: %s truncated (needs 5 lines)' % (pos + 1, up))
    tag_line = lines[pos + 1]
    occ_line = lines[pos + 2]
    fmt1 = lines[pos + 3]
    fmt2 = lines[pos + 4]
    tag, sub = _parse_tag(tag_line)
    if not tag:
        raise ParseError('line %d: %s missing field tag' % (pos + 2, up))
    _check_params(fmt1, nparams)
    _check_params(fmt2, nparams)
    op = Op(kind=up, tag=tag, subfield=sub, occ=_parse_occ(occ_line),
            fmt1=_norm_fmt(fmt1), fmt2=_norm_fmt(fmt2))
    return op, pos + 5


def _parse_repeat(lines, pos, nparams, warnings):
    """Body of a REPEAT, returning ``(body, pos_after_until, until_fmt)``."""
    body, pos = _parse_ops(lines, pos, nparams, warnings, stop={'UNTIL'})
    # the UNTIL marker is consumed by _parse_ops; its format is the next line
    if pos >= len(lines):
        raise ParseError('REPEAT…UNTIL: missing UNTIL condition format')
    until = lines[pos]
    return body, pos + 1, until


def _parse_other_record(up, lines, pos, nparams, warnings):
    """Parse NEWMFN/NEWREC (2 header lines) or CORREC (4-5) plus their … END body.

    The body is parsed (so it stays structurally validated) but the whole node is
    flagged ``supported=False`` — execution of other-record operators is a later
    A3 slice. Returns ``(op, pos_after_END)``."""
    if up in ('NEWMFN', 'NEWREC'):
        fmt = _need(lines, pos + 1, '%s: missing format line' % up)
        _check_params(fmt, nparams)
        header = {'kind': up, 'fmt': _norm_fmt(fmt), 'supported': False}
        body_start = pos + 2
    else:  # CORREC: db / key→1001 / terms (4 lines; optional 5th = count)
        for off in range(1, 4):
            _need(lines, pos + off, 'CORREC: truncated header')
        header = {
            'kind': 'CORREC', 'supported': False,
            'dbFmt': _norm_fmt(lines[pos + 1]),
            'keyFmt': _norm_fmt(lines[pos + 2]),
            'termsFmt': _norm_fmt(lines[pos + 3]),
        }
        body_start = pos + 4
    inner, pos = _parse_ops(lines, body_start, nparams, warnings, stop={'END'})
    warnings.append('%s parsed but not executed in this slice' % up)
    op = Op(**header)
    op['body'] = inner
    return op, pos


def _need(lines, idx, msg):
    if idx >= len(lines):
        raise ParseError(msg)
    return lines[idx]


def _check_params(fmt, nparams):
    """Reject a ``%n`` reference beyond the declared parameter count (SPEC §1.4).

    Only bare ``%1..%9`` digit references count; ``%`` followed by a non-digit
    (e.g. format directives) is ignored."""
    i = 0
    s = fmt or ''
    while i < len(s) - 1:
        if s[i] == '%' and s[i + 1].isdigit():
            n = int(s[i + 1])
            if n == 0 or n > nparams:
                raise ParseError('format references %%%d but only %d parameter(s) '
                                 'declared' % (n, nparams))
            i += 2
            continue
        i += 1


# --------------------------------------------------------------------------- #
# Format evaluation hook — delegate to A1 (access.pft.eval) when importable,
# else a deliberately small literal/field stub so this slice runs standalone.
# --------------------------------------------------------------------------- #
def stub_format_eval(fmt, record, ctx):
    """Minimal ФОРМАТ evaluator (used only when no PFT engine is wired).

    Understands just enough to drive the slice's tests and simple literal jobs:
      * the empty-string producer ``#`` and ∅ -> ``''``;
      * a single quoted literal ``'…'`` -> its contents (``%n`` substituted);
      * a bare field reference ``vNNN`` / ``vNNN^x`` -> the first repetition's
        value;
      * a parameter reference ``%n`` on its own -> the parameter value.
    Anything richer (``if…then…``, ``&uf(...)``) is beyond the stub: it returns the
    raw string so a misconfigured job degrades visibly rather than crashing."""
    s = (fmt or '').strip()
    if s == '' or s == '#':
        return ''
    s = _subst_params(s, ctx)
    # quoted literal '...'
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    # bare field reference vNNN[^x]
    if s.lower().startswith('v') and len(s) > 1 and s[1].isdigit():
        ref = s[1:]
        if '^' in ref:
            tag, sub = ref.split('^', 1)
            sub = sub[:1] or None
        else:
            tag, sub = ref, None
        if tag.isdigit():
            vals = field_values(record, tag, sub)
            return vals[0] if vals else ''
    return s


def _subst_params(s, ctx):
    """Replace ``%1..%9`` with the job parameter values from ``ctx['params']``."""
    params = (ctx or {}).get('params') or {}
    out = []
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 1 < len(s) and s[i + 1].isdigit():
            out.append(str(params.get(s[i + 1], params.get(int(s[i + 1]), ''))))
            i += 2
            continue
        out.append(s[i])
        i += 1
    return ''.join(out)


def _import_pft_eval():
    """Return ``access.pft.eval`` if the A1 module is importable, else None."""
    try:
        from access import pft            # noqa: F401  (A1, may not exist yet)
    except Exception:
        return None
    return getattr(pft, 'eval', None)


def resolve_format_eval(ctx):
    """Pick the active format evaluator (SPEC §2 delegation boundary).

    Precedence: an explicit ``ctx['format_eval']`` (tests inject this) > the A1
    ``access.pft.eval`` if importable > the built-in :func:`stub_format_eval`."""
    if ctx and ctx.get('format_eval'):
        return ctx['format_eval']
    pft_eval = _import_pft_eval()
    if pft_eval is not None:
        return pft_eval
    return stub_format_eval


def _eval(fmt, record, ctx):
    return resolve_format_eval(ctx)(fmt, record, ctx)


def _eval_lines(fmt, record, ctx):
    """Multi-line evaluation (F-mode / whole-field ADD). Uses
    ``ctx['format_eval_lines']`` / ``access.pft.evalLines`` when present, else
    splits the single-string result on newlines."""
    if ctx and ctx.get('format_eval_lines'):
        return list(ctx['format_eval_lines'](fmt, record, ctx))
    try:
        from access import pft
        if hasattr(pft, 'evalLines'):
            return list(pft.evalLines(fmt, record, ctx))
    except Exception:
        pass
    res = _eval(fmt, record, ctx)
    return res.split('\n') if res != '' else ['']


# --------------------------------------------------------------------------- #
# Occurrence resolution — turn an ``Occ`` selector into a list of indices into a
# field's repetition list (GLOBAL_CORRECTION §1.1).
# --------------------------------------------------------------------------- #
def _resolve_occ(occ, count):
    kind, arg = occ
    if count == 0:
        return []
    if kind == OCC_ALL:
        return list(range(count))
    if kind == OCC_NTH:
        idx = arg - 1                       # 1-based in the job
        return [idx] if 0 <= idx < count else []
    if kind == OCC_LAST:
        return [count - 1]
    if kind == OCC_LAST_MINUS:
        idx = count - 1 - arg
        return [idx] if 0 <= idx < count else []
    # BY_FORMAT handled at the call site (needs the format lines)
    return []


# --------------------------------------------------------------------------- #
# Operator execution. ``apply`` runs the program body over a *copy* of the
# record; ``_apply_op`` dispatches by kind. ``state`` carries the protocol log,
# the deleted/empty flags and a record of skipped (unsupported) operators.
# --------------------------------------------------------------------------- #
def apply(ast, record, ctx=None):
    """Execute ``ast`` over a copy of ``record`` and return the new record.

    Operators run sequentially; each sees the record as the previous ones left
    it (SPEC §0 parity). ФОРМАТ lines are evaluated through the format_eval hook
    (delegated to A1 when available). The input record is never mutated.

    ``ctx`` may carry ``format_eval`` / ``params`` / ``max_iterations``. After the
    run, ``ctx['_state']`` (if ctx is a dict) holds ``{putlog, deleted, emptied,
    skipped}`` for the caller; the return value is the corrected record."""
    orig_ctx = ctx
    work_ctx = dict(ctx) if ctx else {}
    rec = normalize_record(record)
    state = {'putlog': [], 'deleted': False, 'emptied': False, 'skipped': []}
    body = ast['body'] if isinstance(ast, dict) else ast
    _run_body(body, rec, work_ctx, state)
    # Surface the run state on BOTH the working copy and the caller's ctx dict
    # (so a caller that passed a dict can read ctx['_state'] after the call).
    work_ctx['_state'] = state
    if isinstance(orig_ctx, dict):
        orig_ctx['_state'] = state
    return rec


def _run_body(body, rec, ctx, state):
    for op in body:
        _apply_op(op, rec, ctx, state)


def _apply_op(op, rec, ctx, state):
    kind = op['kind']
    fn = _OP_DISPATCH.get(kind)
    if fn is None or op.get('supported') is False:
        if kind not in ('COMMENT',):
            state['skipped'].append(kind)
        return
    fn(op, rec, ctx, state)


# ---- field operators ------------------------------------------------------- #
def _op_add(op, rec, ctx, state):
    """ADD: add a new repetition (whole field) or a subfield (GC §1.3 ADD)."""
    tag, sub = op['tag'], op['subfield']
    field = _field(rec, tag)
    if sub is None:
        # whole-field ADD: each ФОРМАТ 1 line => a new repetition.
        for line in _eval_lines(op['fmt1'], rec, ctx):
            if line == '' and op['fmt1'] == '':
                continue
            field.append({'': line})
        return
    # subfield ADD: 1st ФОРМАТ 1 line -> subfield in the targeted repetition(s).
    val = _eval(op['fmt1'], rec, ctx)
    occ = op['occ']
    if occ[0] == OCC_BY_FORMAT:
        lines = _eval_lines(op['fmt1'], rec, ctx)
        for i, line in enumerate(lines):
            if i < len(field) and line != '':
                _inst_set(field[i], sub, line)
        return
    idxs = _resolve_occ(occ, len(field))
    if not idxs:
        field.append({})
        idxs = [len(field) - 1]
    for i in idxs:
        _inst_set(field[i], sub, val)


def _op_rep(op, rec, ctx, state):
    """REP: replace a field/subfield wholesale; empty ФОРМАТ 1 deletes it."""
    tag, sub = op['tag'], op['subfield']
    field = _field(rec, tag)
    occ = op['occ']
    if occ[0] == OCC_BY_FORMAT:
        lines = _eval_lines(op['fmt1'], rec, ctx)
        for i in range(len(field)):
            if i < len(lines):
                _rep_one(field, i, sub, lines[i])
        return
    val = _eval(op['fmt1'], rec, ctx)
    for i in _resolve_occ(occ, len(field)):
        _rep_one(field, i, sub, val)
    _compact(field)


def _rep_one(field, i, sub, val):
    if sub is None:
        if val == '':
            field[i] = None                 # marked for compaction (delete)
        else:
            field[i] = {'': val}
    else:
        if val == '':
            field[i].pop(sub, None)
            field[i].pop(sub.lower(), None)
            field[i].pop(sub.upper(), None)
        else:
            _inst_set(field[i], sub, val)


def _compact(field):
    field[:] = [f for f in field if f is not None]


def _op_cha(op, rec, ctx, state):
    """CHA/CHAC: replace substring A (ФОРМАТ 1) with B (ФОРМАТ 2) in the field /
    subfield. CHAC is case-sensitive; CHA matches case-insensitively."""
    tag, sub = op['tag'], op['subfield']
    field = _field(rec, tag)
    case_sensitive = (op['kind'] == 'CHAC')
    occ = op['occ']
    a_default = _eval(op['fmt1'], rec, ctx)
    b_default = _eval(op['fmt2'], rec, ctx)
    if occ[0] == OCC_BY_FORMAT:
        a_lines = _eval_lines(op['fmt1'], rec, ctx)
        b_lines = _eval_lines(op['fmt2'], rec, ctx)
        for i in range(len(field)):
            a = a_lines[i] if i < len(a_lines) else ''
            b = b_lines[i] if i < len(b_lines) else ''
            _cha_one(field[i], sub, a, b, case_sensitive)
        return
    for i in _resolve_occ(occ, len(field)):
        _cha_one(field[i], sub, a_default, b_default, case_sensitive)


def _cha_one(inst, sub, a, b, case_sensitive):
    """Replace all occurrences of ``a`` with ``b`` in one instance's value.

    A empty => append B to the value; B empty => delete A (GC §1.3 CHA)."""
    if sub is None:
        keys = ['']
    else:
        seen = []
        for k in (sub, sub.lower(), sub.upper()):
            if k in inst and k not in seen:
                seen.append(k)
        keys = seen or [sub]
    for k in keys:
        cur = inst.get(k, '')
        if a == '':
            inst[k] = cur + b               # A empty -> append B
        elif case_sensitive:
            inst[k] = cur.replace(a, b)
        else:
            inst[k] = _ci_replace(cur, a, b)


def _ci_replace(text, a, b):
    """Case-insensitive replace-all of ``a`` with ``b`` (CHA semantics)."""
    if not a:
        return text
    out = []
    low_a = a.lower()
    i = 0
    lt = text.lower()
    while i < len(text):
        if lt.startswith(low_a, i):
            out.append(b)
            i += len(a)
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _op_del(op, rec, ctx, state):
    """DEL: delete a field repetition or a subfield (GC §1.3 DEL).

    F-mode: ФОРМАТ 1 yields one line per repetition; ``'1'`` deletes it."""
    tag, sub = op['tag'], op['subfield']
    field = _field(rec, tag)
    occ = op['occ']
    if occ[0] == OCC_BY_FORMAT:
        lines = _eval_lines(op['fmt1'], rec, ctx)
        keep = []
        for i, inst in enumerate(field):
            flag = lines[i].strip() if i < len(lines) else '0'
            if flag == '1':
                continue                    # delete this repetition
            keep.append(inst)
        field[:] = keep
        return
    idxs = set(_resolve_occ(occ, len(field)))
    if sub is None:
        field[:] = [inst for i, inst in enumerate(field) if i not in idxs]
    else:
        for i in idxs:
            field[i].pop(sub, None)
            field[i].pop(sub.lower(), None)
            field[i].pop(sub.upper(), None)


# ---- record / flow operators ---------------------------------------------- #
def _op_delr(op, rec, ctx, state):
    state['deleted'] = True
    rec['*status'] = [{'': 'deleted'}]


def _op_undel(op, rec, ctx, state):
    state['deleted'] = False
    rec['*status'] = [{'': 'active'}]


def _op_empty(op, rec, ctx, state):
    state['emptied'] = True
    rec.clear()


def _op_if(op, rec, ctx, state):
    if _eval(op['cond'], rec, ctx).strip() == '1':
        _run_body(op['body'], rec, ctx, state)


def _op_repeat(op, rec, ctx, state):
    limit = (ctx or {}).get('max_iterations', 100000)
    iters = 0
    while True:
        _run_body(op['body'], rec, ctx, state)
        iters += 1
        if _eval(op['until'], rec, ctx).strip() != '1':
            break
        if iters >= limit:
            raise RuntimeError('REPEAT exceeded %d iterations (loop guard)' % limit)


def _op_putlog(op, rec, ctx, state):
    state['putlog'].append(_eval(op['fmt'], rec, ctx))


_OP_DISPATCH = {
    'ADD': _op_add, 'REP': _op_rep, 'CHA': _op_cha, 'CHAC': _op_cha,
    'DEL': _op_del, 'DELR': _op_delr, 'UNDEL': _op_undel, 'EMPTY': _op_empty,
    'IF': _op_if, 'REPEAT': _op_repeat, 'PUTLOG': _op_putlog,
    'COMMENT': lambda *a: None,
}


# --------------------------------------------------------------------------- #
# Preview — dry-run producing a per-record field-level before/after diff with NO
# mutation of the inputs (SPEC §4.1). Counters/persistence side effects are out
# of scope for this slice; the diff is computed purely from the record copies.
# --------------------------------------------------------------------------- #
def preview(ast, records, ctx=None):
    """Dry-run ``ast`` over each record in ``records`` and return a diff report.

    Returns a list of per-record dicts::

        { 'index': i, 'status': 'changed'|'unchanged'|'deleted'|'emptied'|'error',
          'changes': [ {tag, subfield, op, before, after}, ... ],
          'putlog': [...], 'before': {...}, 'after': {...}, 'error': str? }

    Neither the input records nor any external state are mutated — ``apply`` works
    on a deep copy, so ``preview`` is a pure projection (SPEC AC5)."""
    out = []
    for i, record in enumerate(records):
        before = normalize_record(record)
        local_ctx = dict(ctx) if ctx else {}
        try:
            after = apply(ast, before, local_ctx)
        except Exception as e:               # isolate one bad record (SPEC AC9)
            out.append({'index': i, 'status': 'error', 'error': str(e),
                        'changes': [], 'putlog': [], 'before': before, 'after': before})
            continue
        state = local_ctx.get('_state', {})
        changes = diff_records(before, after)
        if state.get('emptied'):
            status = 'emptied'
        elif state.get('deleted'):
            status = 'deleted'
        elif changes:
            status = 'changed'
        else:
            status = 'unchanged'
        out.append({
            'index': i, 'status': status, 'changes': changes,
            'putlog': state.get('putlog', []),
            'before': copy.deepcopy(before), 'after': copy.deepcopy(after),
        })
    return out


def diff_records(before, after):
    """Field/subfield-level before→after diff between two normalised records.

    Emits one change per added / removed / modified (tag, subfield) value,
    comparing repetition-by-repetition so the UI can render «было → стало»."""
    changes = []
    tags = list(dict.fromkeys(list(before.keys()) + list(after.keys())))
    for tag in tags:
        if tag.startswith('*'):              # internal status markers, not BO data
            continue
        b_insts = before.get(tag, [])
        a_insts = after.get(tag, [])
        subs = _all_subfields(b_insts) | _all_subfields(a_insts)
        for sub in sorted(subs, key=lambda s: (s is not None, s or '')):
            b_vals = _vals(b_insts, sub)
            a_vals = _vals(a_insts, sub)
            if b_vals == a_vals:
                continue
            _emit_value_changes(changes, tag, sub, b_vals, a_vals)
    return changes


def _all_subfields(insts):
    subs = set()
    for inst in insts:
        for k in inst.keys():
            subs.add(None if k == '' else k)
    return subs


def _vals(insts, sub):
    key = '' if sub is None else sub
    out = []
    for inst in insts:
        if sub is None:
            if '' in inst:
                out.append(inst.get('', ''))
        elif key in inst:
            out.append(inst.get(key, ''))
    return out


def _emit_value_changes(changes, tag, sub, b_vals, a_vals):
    """Pair up old/new repetition values and emit add/remove/modify changes."""
    n = max(len(b_vals), len(a_vals))
    for i in range(n):
        b = b_vals[i] if i < len(b_vals) else None
        a = a_vals[i] if i < len(a_vals) else None
        if b == a:
            continue
        if b is None:
            op = 'add'
        elif a is None:
            op = 'remove'
        else:
            op = 'modify'
        changes.append({'tag': tag, 'subfield': sub, 'op': op,
                        'before': b, 'after': a})


__all__ = [
    'parse', 'apply', 'preview', 'diff_records', 'normalize_record',
    'field_values', 'resolve_format_eval', 'stub_format_eval',
    'Program', 'Op', 'ParseError',
]
