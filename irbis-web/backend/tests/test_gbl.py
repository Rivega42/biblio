#!/usr/bin/env python3
"""Global-correction ``.gbl`` executor tests (gap A3, epic #188).

Covers the first shippable slice of the A3 batch-correction engine
(``access.gbl``), which is self-contained pure stdlib and runs with NO PFT (A1)
engine present — ФОРМАТ evaluation is injected as a literal/field stub so the
operator semantics can be exercised in isolation:

  1. Parser (pure): the parameter header + the 5-line field operators
     (ADD/REP/CHA/CHAC/DEL) + the IF…FI / REPEAT…UNTIL blocks parse into the AST
     with the right arity; XXXX… / blank lines normalise to ∅; malformed jobs
     (unknown operator, unclosed block, %n over the declared count) raise.
  2. Apply (pure): ADD a field, REP replace a field & a subfield, REP-empty
     deletes, DEL a field, CHA/CHAC substring replace, IF gates an op, a small
     multi-operator job — each over a copy (the input record is never mutated).
  3. format_eval boundary: an explicit ctx hook is used; the stub evaluator
     resolves when no hook and no access.pft is importable.
  4. Preview (pure): a dry-run yields a correct field-level diff WITHOUT mutating
     the input records (SPEC AC5).

Standalone-runnable in the house style of tests/test_seeding.py:
``py -3.12 tests/test_gbl.py`` -> ``ok …`` lines + ``N passed, M failed`` + exit
code. No DB, no network, no PFT engine required.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import gbl

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
# Literal/field format_eval stub for the tests — so they never depend on a full
# PFT engine. Understands: '' / '#' -> ∅; quoted literal 'x' -> x (with %n);
# bare vNNN[^s] -> first repetition value; '1'/'0' flags pass through. This is
# the same contract access.gbl.stub_format_eval offers, made explicit in ctx.
# --------------------------------------------------------------------------- #
def lit_eval(fmt, record, ctx):
    return gbl.stub_format_eval(fmt, record, ctx)


def by_format_eval(mapping):
    """Build a format_eval that returns a fixed multi-line string for a marker
    format (so F-mode tests are deterministic without PFT)."""
    def _e(fmt, record, ctx):
        if fmt in mapping:
            return mapping[fmt]
        return gbl.stub_format_eval(fmt, record, ctx)
    return _e


def rec(d):
    return gbl.normalize_record(d)


# --------------------------------------------------------------------------- #
# 1. Parser.
# --------------------------------------------------------------------------- #
def parser_checks():
    print('-- parser (.gbl -> AST)')

    # Header: 0 params, one ADD operator (5 lines).
    job = "0\nADD\n910\n\n'X'\n\n"
    prog = gbl.parse(job)
    check('parse no-params header', prog['params'] == [])
    check('parse one ADD op', len(prog['body']) == 1 and prog['body'][0]['kind'] == 'ADD')
    op = prog['body'][0]
    check('parse ADD tag/occ/fmt1', op['tag'] == '910'
          and op['occ'][0] == gbl.OCC_ALL and op['fmt1'] == "'X'")

    # Parameter header: 1 param with a caption, then a field op.
    job_p = ("1\n\nВведите дату\nDEL\n40\n*\nXXXXXXXXXXXXXXXXXXX\n"
             "XXXXXXXXXXXXXXXXXXX\n")
    prog_p = gbl.parse(job_p)
    check('parse 1 param', len(prog_p['params']) == 1
          and prog_p['params'][0]['caption'] == 'Введите дату')
    check('parse prompt param source', prog_p['params'][0]['source'] == 'prompt')
    delop = prog_p['body'][0]
    check('parse DEL op', delop['kind'] == 'DEL' and delop['tag'] == '40')
    check('parse XXXX placeholder -> empty fmt', delop['fmt1'] == '' and delop['fmt2'] == '')

    # Tag with subfield: 200^a.
    job_s = "0\nREP\n200^a\n1\n'T'\n\n"
    op_s = gbl.parse(job_s)['body'][0]
    check('parse subfield tag', op_s['tag'] == '200' and op_s['subfield'] == 'a')
    check('parse NTH occ', op_s['occ'] == (gbl.OCC_NTH, 1))

    # F-mode occurrence.
    job_f = "0\nDEL\n910\nF\n(flag/)\n\n"
    op_f = gbl.parse(job_f)['body'][0]
    check('parse F-mode occ', op_f['occ'][0] == gbl.OCC_BY_FORMAT)

    # IF…FI block parses into a nested body, FI is consumed (not a node).
    job_if = "0\nIF\nif p(v200) then '1' fi\nADD\n910\n\n'Y'\n\nFI\n"
    prog_if = gbl.parse(job_if)
    ifop = prog_if['body'][0]
    check('parse IF block', ifop['kind'] == 'IF' and len(ifop['body']) == 1)
    check('parse IF body is ADD', ifop['body'][0]['kind'] == 'ADD')
    check('parse FI not a node', all(o['kind'] != 'FI' for o in prog_if['body']))

    # REPEAT…UNTIL.
    job_rep = "0\nREPEAT\nDEL\n910\n1\n\n\nUNTIL\nif p(v910) then '1' fi\n"
    rop = gbl.parse(job_rep)['body'][0]
    check('parse REPEAT block', rop['kind'] == 'REPEAT' and len(rop['body']) == 1)
    check('parse UNTIL captured', "p(v910)" in rop['until'])

    # PUTLOG and comment.
    job_misc = "0\n//a comment\nPUTLOG\n'hi'\n"
    prog_misc = gbl.parse(job_misc)
    kinds = [o['kind'] for o in prog_misc['body']]
    check('parse comment node', 'COMMENT' in kinds)
    check('parse PUTLOG node', 'PUTLOG' in kinds)

    # CP1251 bytes decode on input.
    raw = "0\nADD\n900\n\n'тест'\n\n".encode('cp1251')
    op_b = gbl.parse(raw)['body'][0]
    check('parse decodes cp1251 bytes', op_b['fmt1'] == "'тест'")

    # --- error cases ---
    check('unknown operator raises', _raises(gbl.ParseError, gbl.parse, "0\nFOO\n"))
    check('unclosed IF raises',
          _raises(gbl.ParseError, gbl.parse, "0\nIF\nif x then '1' fi\nADD\n9\n\n'a'\n\n"))
    check('stray FI raises', _raises(gbl.ParseError, gbl.parse, "0\nFI\n"))
    check('%n over declared count raises',
          _raises(gbl.ParseError, gbl.parse, "0\nADD\n910\n\n'%1'\n\n"))
    check('non-int param count raises', _raises(gbl.ParseError, gbl.parse, "x\n"))

    # NEWMFN…END parses (carried, body validated) but is flagged unsupported.
    job_nm = "0\nNEWMFN\n'*'\nADD\n920\n\n'SZ'\n\nEND\n"
    nm = gbl.parse(job_nm)['body'][0]
    check('parse NEWMFN block', nm['kind'] == 'NEWMFN' and nm.get('supported') is False)
    check('parse NEWMFN body validated', len(nm['body']) == 1)


def _raises(exc, fn, *a):
    try:
        fn(*a)
        return False
    except exc:
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# 2. Apply — operator semantics over a copy.
# --------------------------------------------------------------------------- #
def apply_checks():
    print('-- apply (operators)')
    ctx = {'format_eval': lit_eval}

    # ADD a whole field.
    prog = gbl.parse("0\nADD\n910\n\n'1024365'\n\n")
    r = gbl.apply(prog, {'200': [{'a': 'Книга'}]}, ctx)
    check('ADD creates field', gbl.field_values(r, '910') == ['1024365'])
    check('ADD keeps other fields', gbl.field_values(r, '200', 'a') == ['Книга'])

    # ADD a subfield to an existing repetition.
    prog = gbl.parse("0\nADD\n200^f\n1\n'Иванов'\n\n")
    r = gbl.apply(prog, {'200': [{'a': 'Заглавие'}]}, ctx)
    check('ADD subfield', gbl.field_values(r, '200', 'f') == ['Иванов']
          and gbl.field_values(r, '200', 'a') == ['Заглавие'])

    # REP replaces a whole field.
    prog = gbl.parse("0\nREP\n920\n*\n'PVK'\n\n")
    r = gbl.apply(prog, {'920': [{'': 'PAZK'}]}, ctx)
    check('REP whole field', gbl.field_values(r, '920') == ['PVK'])

    # REP replaces a subfield (1st repetition).
    prog = gbl.parse("0\nREP\n200^a\n1\n'Новое'\n\n")
    r = gbl.apply(prog, {'200': [{'a': 'Старое', 'f': 'Автор'}]}, ctx)
    check('REP subfield', gbl.field_values(r, '200', 'a') == ['Новое'])
    check('REP subfield keeps sibling', gbl.field_values(r, '200', 'f') == ['Автор'])

    # REP with empty ФОРМАТ 1 deletes the field (GC §1.3).
    prog = gbl.parse("0\nREP\n910\n*\n\n\n")
    r = gbl.apply(prog, {'910': [{'': 'x'}]}, ctx)
    check('REP empty deletes field', gbl.field_values(r, '910') == [])

    # DEL removes a whole field repetition.
    prog = gbl.parse("0\nDEL\n910\n*\n\n\n")
    r = gbl.apply(prog, {'910': [{'': 'a'}, {'': 'b'}]}, ctx)
    check('DEL all repetitions', gbl.field_values(r, '910') == [])

    # DEL the N-th repetition only.
    prog = gbl.parse("0\nDEL\n910\n1\n\n\n")
    r = gbl.apply(prog, {'910': [{'': 'a'}, {'': 'b'}]}, ctx)
    check('DEL nth repetition', gbl.field_values(r, '910') == ['b'])

    # DEL a subfield (leaves the repetition).
    prog = gbl.parse("0\nDEL\n200^f\n*\n\n\n")
    r = gbl.apply(prog, {'200': [{'a': 'T', 'f': 'A'}]}, ctx)
    check('DEL subfield only', gbl.field_values(r, '200', 'a') == ['T']
          and gbl.field_values(r, '200', 'f') == [])

    # CHA replaces a substring, case-insensitively.
    prog = gbl.parse("0\nCHA\n926^b\n*\n'.'\n'. '\n")
    r = gbl.apply(prog, {'926': [{'b': 'И.И.'}]}, ctx)
    check('CHA substring (all)', gbl.field_values(r, '926', 'b') == ['И. И. '])

    # CHA is case-insensitive; CHAC is case-sensitive.
    prog_cha = gbl.parse("0\nCHA\n900\n*\n'abc'\n'X'\n")
    r1 = gbl.apply(prog_cha, {'900': [{'': 'ABCabc'}]}, ctx)
    check('CHA ignores case', gbl.field_values(r1, '900') == ['XX'])
    prog_chac = gbl.parse("0\nCHAC\n900\n*\n'abc'\n'X'\n")
    r2 = gbl.apply(prog_chac, {'900': [{'': 'ABCabc'}]}, ctx)
    check('CHAC respects case', gbl.field_values(r2, '900') == ['ABCX'])

    # F-mode DEL: '1' lines delete the matching repetition (GC del40.gbl pattern).
    ev = by_format_eval({'(flag/)': '0\n1\n0'})
    prog = gbl.parse("0\nDEL\n910\nF\n(flag/)\n\n")
    r = gbl.apply(prog, {'910': [{'': 'a'}, {'': 'b'}, {'': 'c'}]},
                  {'format_eval': ev})
    check('DEL F-mode deletes flagged', gbl.field_values(r, '910') == ['a', 'c'])

    # DELR sets the logical-delete flag (record marked, not dropped).
    prog = gbl.parse("0\nDELR\n")
    local = {'format_eval': lit_eval}
    r = gbl.apply(prog, {'200': [{'a': 'x'}]}, local)
    check('DELR sets deleted flag', local['_state']['deleted'] is True)

    # input record is NOT mutated.
    src = {'910': [{'': 'a'}]}
    prog = gbl.parse("0\nDEL\n910\n*\n\n\n")
    gbl.apply(prog, src, ctx)
    check('apply does not mutate input', src == {'910': [{'': 'a'}]})


# --------------------------------------------------------------------------- #
# 2b. IF gating + multi-operator job.
# --------------------------------------------------------------------------- #
def control_flow_checks():
    print('-- control flow (IF / multi-op)')

    # IF true -> body runs.  cond evaluator returns '1' iff 200^a present.
    def cond_eval(fmt, record, ctx):
        if fmt.startswith('if p(v200)'):
            return '1' if gbl.field_values(record, '200', 'a') else '0'
        return gbl.stub_format_eval(fmt, record, ctx)

    job = "0\nIF\nif p(v200) then '1' fi\nADD\n910\n\n'YES'\n\nFI\n"
    prog = gbl.parse(job)
    r_on = gbl.apply(prog, {'200': [{'a': 'T'}]}, {'format_eval': cond_eval})
    check('IF true runs body', gbl.field_values(r_on, '910') == ['YES'])
    r_off = gbl.apply(prog, {'300': [{'a': 'x'}]}, {'format_eval': cond_eval})
    check('IF false skips body', gbl.field_values(r_off, '910') == [])

    # Multi-operator job: ADD a 910, REP the 920, DEL a 900 — sequential, each
    # sees the previous result.
    multi = ("0\n"
             "ADD\n910\n\n'INV-1'\n\n"
             "REP\n920\n*\n'PVK'\n\n"
             "DEL\n900\n*\n\n\n")
    prog = gbl.parse(multi)
    start = {'920': [{'': 'PAZK'}], '900': [{'b': 'a'}], '200': [{'a': 'Кн'}]}
    r = gbl.apply(prog, start, {'format_eval': lit_eval})
    ok = (gbl.field_values(r, '910') == ['INV-1']
          and gbl.field_values(r, '920') == ['PVK']
          and gbl.field_values(r, '900') == []
          and gbl.field_values(r, '200', 'a') == ['Кн'])
    check('multi-operator job applies in order', ok)


# --------------------------------------------------------------------------- #
# 3. format_eval delegation boundary.
# --------------------------------------------------------------------------- #
def format_eval_checks():
    print('-- format_eval boundary')

    # Explicit ctx hook wins.
    sentinel = object()
    picked = gbl.resolve_format_eval({'format_eval': sentinel})
    check('ctx hook takes precedence', picked is sentinel)

    # With no hook and no access.pft, the built-in stub is selected.
    # (access.pft does not exist in this slice -> falls through to the stub.)
    picked2 = gbl.resolve_format_eval({})
    has_pft = _pft_importable()
    if has_pft:
        check('A1 pft.eval delegated when present', picked2 is not gbl.stub_format_eval)
    else:
        check('stub selected without A1', picked2 is gbl.stub_format_eval)

    # The stub itself: literal, field ref, param, empty.
    check('stub literal', gbl.stub_format_eval("'hi'", rec({}), {}) == 'hi')
    check('stub empty/#', gbl.stub_format_eval('#', rec({}), {}) == ''
          and gbl.stub_format_eval('', rec({}), {}) == '')
    check('stub field ref',
          gbl.stub_format_eval('v200^a', rec({'200': [{'a': 'Z'}]}), {}) == 'Z')
    check('stub param subst',
          gbl.stub_format_eval("'%1'", rec({}), {'params': {'1': '20240101'}}) == '20240101')


def _pft_importable():
    try:
        from access import pft            # noqa: F401
        return getattr(pft, 'eval', None) is not None
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# 4. Preview — dry-run diff with no mutation.
# --------------------------------------------------------------------------- #
def preview_checks():
    print('-- preview (dry-run diff)')
    ctx = {'format_eval': lit_eval}

    # ADD + REP across two records; verify the diff and that inputs are intact.
    prog = gbl.parse("0\nADD\n910\n\n'NEW'\n\nREP\n920\n*\n'PVK'\n\n")
    records = [
        {'920': [{'': 'PAZK'}]},
        {'920': [{'': 'PVK'}], '910': [{'': 'NEW'}]},   # ADD still adds a 2nd 910
    ]
    snapshot = [dict(records[0]), dict(records[1])]
    report = gbl.preview(prog, records, ctx)

    check('preview returns one entry per record', len(report) == 2)
    r0 = report[0]
    check('preview rec0 changed', r0['status'] == 'changed')
    # rec0: 910 added (PAZK->PVK on 920, +910 NEW)
    add_910 = [c for c in r0['changes'] if c['tag'] == '910' and c['op'] == 'add']
    mod_920 = [c for c in r0['changes'] if c['tag'] == '920' and c['op'] == 'modify']
    check('preview diff: 910 added', len(add_910) == 1 and add_910[0]['after'] == 'NEW')
    check('preview diff: 920 modified PAZK->PVK',
          len(mod_920) == 1 and mod_920[0]['before'] == 'PAZK'
          and mod_920[0]['after'] == 'PVK')

    # No mutation of the inputs (SPEC AC5).
    check('preview does not mutate inputs',
          records[0] == snapshot[0] and records[1] == snapshot[1])

    # A record with no applicable change reports 'unchanged'.
    prog_noop = gbl.parse("0\nREP\n920\n*\n'PVK'\n\n")
    rep2 = gbl.preview(prog_noop, [{'920': [{'': 'PVK'}]}], ctx)
    check('preview unchanged when no diff', rep2[0]['status'] == 'unchanged'
          and rep2[0]['changes'] == [])

    # before/after snapshots are carried for UI rendering.
    check('preview carries before/after',
          report[0]['before']['920'][0][''] == 'PAZK'
          and report[0]['after']['920'][0][''] == 'PVK')


def main():
    parser_checks()
    apply_checks()
    control_flow_checks()
    format_eval_checks()
    preview_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
