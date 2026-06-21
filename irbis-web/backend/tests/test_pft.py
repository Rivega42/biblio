#!/usr/bin/env python3
"""PFT formatting-engine tests (gap A1, epic #188).

Covers the first shippable slice of the PFT interpreter (``access/pft.py``) — the
keystone the ФЛК (A2) and .gbl (A3) engines delegate to (SPEC_engine_pft.md,
SPEC_api_contracts §3.1 / mismatch M4). Standalone-runnable, mirroring the house
style of tests/test_flk.py / tests/test_seeding.py::

    py -3.12 tests/test_pft.py   ->  'ok …' lines + 'N passed, M failed', exit!=0 on fail

What is exercised
  1. Field substitution: v200^a, whole-field v101, v200^* first subfield, fragment.
  2. Repeating fields: all instances of v910^b, repeatable |…| literals, prefix/suffix.
  3. IF / THEN / ELSE / FI: 920-branching with '=' and ':' (contains), nesting.
  4. Concatenation: ',' and '+', conditional/unconditional literals.
  5. UNIFOR implemented: 'C' (ISBN/ISSN checksum — the code ФЛК reuses), '3' (date
     today, via ctx['now']), 'Av…#n' (Nth occurrence), 'Q'/'9' string ops.
  5b. UNIFOR deepened batch: date '36'/'37'/'38' (month name nom/gen/eng),
     '3A' day-of-year, '3B' date±days, '3C' date difference; 'E'/'F' first/keep-N
     words, 'G' substring up-to/from a marker (#/$ wildcards), 'T' translit
     cyrillic→latin, 'L' term-ending marker strip, '0' full-record dump, '+6'
     record status, '+3E'/'+3D' URL encode/decode.
  6. Graceful skip of an unsupported construct (ref()/l() index lookups, unknown
     UNIFOR) — degrades to '' without crashing the surrounding render.
  7. Dummy output d/n, val()/f()/rsum(), p()/a() predicates, eval_lines groups.
  8. A golden-ish slice from PFT_LANGUAGE (920-branch idiom from brief.pft).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
from access import pft
from access.pft import eval as pft_eval   # the importable contract name

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# A representative book record (field -> list/dict/str of subfields).
def _book():
    return {
        '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.', 'e': 'учебник'}],
        '910': [{'a': '0', 'b': 'INV1'}, {'a': '0', 'b': 'INV2'},
                {'a': '0', 'b': 'INV3'}],
        '101': 'rus',
        '920': 'PAZK',
        '10': {'a': '5-7654-0001-9'},          # valid ISBN-10
        '999': [{'': '3'}, {'': '4'}, {'': '5'}],
    }


# --------------------------------------------------------------------------- #
# 1. Field substitution.
# --------------------------------------------------------------------------- #
def field_checks():
    print('-- field substitution')
    rec = _book()
    check('v200^a -> title', pft_eval('v200^a', rec) == 'Основы каталогизации')
    check('v101 whole-field -> rus', pft_eval('v101', rec) == 'rus')
    check('v200^f -> author', pft_eval('v200^f', rec) == 'Иванова И.И.')
    check('v200^* -> first subfield', pft_eval('v200^*', rec) == 'Основы каталогизации')
    check('absent subfield -> empty', pft_eval('v200^z', rec) == '')
    check('absent field -> empty', pft_eval('v700^a', rec) == '')
    # fragment v…*off.len (0-based)
    check('fragment v101*0.2 -> "ru"', pft_eval('v101*0.2', rec) == 'ru')
    # mfn from ctx
    check('mfn(6) zero-padded', pft_eval('mfn(6)', rec, {'mfn': 42}) == '000042')
    check('bare mfn', pft_eval('mfn', rec, {'mfn': 7}) == '7')


# --------------------------------------------------------------------------- #
# 2. Repeating fields.
# --------------------------------------------------------------------------- #
def repeat_checks():
    print('-- repeating fields')
    rec = _book()
    # A bare field command outputs ALL occurrences concatenated (PFT semantics).
    check('v910^b emits all occurrences', pft_eval('v910^b', rec) == 'INV1INV2INV3')
    # |x|+ repeatable prefix = separator before each instance except the first.
    check('|sep|+ separator between repeats',
          pft_eval('| ; |+v910^b', rec) == 'INV1 ; INV2 ; INV3')
    # +|x| repeatable suffix = after each instance except the last.
    check('+|sep| separator after repeats',
          pft_eval('v910^b+| ; |', rec) == 'INV1 ; INV2 ; INV3')
    # repeat group emits each instance
    grp = pft_eval('(v910^b)', rec)
    check('repeat group over v910 -> all 3', grp == 'INV1INV2INV3')
    # eval_lines splits the group into one line per instance
    lines = pft.eval_lines('(v910^b)', rec)
    check('eval_lines yields 3 lines', lines == ['INV1', 'INV2', 'INV3'])


# --------------------------------------------------------------------------- #
# 3. IF / THEN / ELSE / FI + 920 branching.
# --------------------------------------------------------------------------- #
def if_checks():
    print('-- if/then/else/fi')
    rec = _book()                              # 920 = PAZK
    check("if v920='J' else branch",
          pft_eval("if v920='J' then 'журнал' else 'книга' fi", rec) == 'книга')
    jrec = dict(rec, **{'920': 'J'})
    check("if v920='J' then branch",
          pft_eval("if v920='J' then 'журнал' else 'книга' fi", jrec) == 'журнал')
    # ':' contains operator (case-insensitive)
    njrec = dict(rec, **{'920': 'NJ31'})
    check("if v920:'NJ' contains",
          pft_eval("if v920:'NJ' then 'периодика' else 'моно' fi", njrec) == 'периодика')
    check("contains is false for PAZK",
          pft_eval("if v920:'NJ' then 'периодика' else 'моно' fi", rec) == 'моно')
    # nested IF with its own FI
    nested = "if v920:'NJ' then if v101='rus' then 'РУС' else 'X' fi else 'NO' fi"
    check('nested if (NJ + rus)', pft_eval(nested, njrec) == 'РУС')
    # missing ELSE: no output when condition false
    check('if without else, false -> empty',
          pft_eval("if v920='J' then 'журнал' fi", rec) == '')
    # predicate p()/a() in condition
    check('p(v200^a) true branch',
          pft_eval("if p(v200^a) then 'есть' else 'нет' fi", rec) == 'есть')
    check('a(v700) (absent) true branch',
          pft_eval("if a(v700) then 'нет автора' else 'есть' fi", rec) == 'нет автора')
    # NOT / AND / OR
    check('AND both true',
          pft_eval("if p(v200^a) and v101='rus' then 'ok' fi", rec) == 'ok')
    check('OR one true',
          pft_eval("if v920='J' or p(v200^a) then 'ok' fi", rec) == 'ok')
    check('NOT inverts',
          pft_eval("if not v920='J' then 'не журнал' fi", rec) == 'не журнал')


# --------------------------------------------------------------------------- #
# 4. Concatenation + literals.
# --------------------------------------------------------------------------- #
def concat_checks():
    print('-- concatenation / literals')
    rec = _book()
    check('comma concatenation',
          pft_eval("v200^a, ' / ', v200^f", rec) ==
          'Основы каталогизации / Иванова И.И.')
    check('plus concatenation',
          pft_eval("v101 + '-' + v920", rec) == 'rus-PAZK')
    # unconditional literal always emits; conditional only with adjacent field
    check('unconditional literal always',
          pft_eval("'X', v700^a", rec) == 'X')
    # conditional literal "…" before present field emits with it
    check('conditional prefix literal on present field',
          pft_eval('"Заглавие: "v200^a', rec) == 'Заглавие: Основы каталогизации')
    check('conditional prefix literal on absent field suppressed',
          pft_eval('"Автор: "v700^a', rec) == '')


# --------------------------------------------------------------------------- #
# 5. UNIFOR codes implemented.
# --------------------------------------------------------------------------- #
def unifor_checks():
    print('-- unifor (implemented)')
    rec = _book()
    # 'C' — ISBN/ISSN checksum control: '0' ok, '1' error. The code ФЛК reuses.
    check("&unifor('C' valid ISBN-10) -> 0",
          pft_eval("&unifor('C'v10^a)", rec) == '0')
    bad = dict(rec, **{'10': {'a': '5-7654-0001-0'}})   # flipped check digit
    check("&unifor('C' bad ISBN) -> 1",
          pft_eval("&unifor('C'v10^a)", bad) == '1')
    issn = dict(rec, **{'11': {'a': '0378-5955'}})       # textbook-valid ISSN
    check("&unifor('C' valid ISSN) -> 0",
          pft_eval("&unifor('C'v11^a)", issn) == '0')
    # direct API check of the shared algorithm
    check('isbn_issn_ok valid ISBN-13', pft.isbn_issn_ok('978-0-306-40615-7'))
    check('isbn_issn_ok rejects bad', not pft.isbn_issn_ok('978-0-306-40615-0'))

    # '3' — date today (via ctx['now'] for determinism).
    fixed = datetime.datetime(2026, 6, 21, 9, 30, 0)
    check("&unifor('3') -> YYYYMMDD",
          pft_eval("&unifor('3')", rec, {'now': fixed}) == '20260621')
    check("&unifor('30') -> year",
          pft_eval("&unifor('30')", rec, {'now': fixed}) == '2026')
    check("&unifor('32') -> day",
          pft_eval("&unifor('32')", rec, {'now': fixed}) == '21')

    # 'A' — Nth field occurrence: &unifor('Av910^b#2') -> 2nd instance.
    check("&unifor('Av910^b#2') -> 2nd inv",
          pft_eval("&unifor('Av910^b#2')", rec) == 'INV2')
    check("&unifor('Av920#1') -> first 920 (brief.pft idiom)",
          pft_eval("&unifor('Av920#1')", rec) == 'PAZK')

    # 'Q' lowercase, '9' strip quotes.
    check("&unifor('Q' value) lowercases",
          pft_eval("&unifor('Q'v920)", rec) == 'pazk')
    quoted = dict(rec, **{'300': '"кавычки"'})
    check("&unifor('9' value) strips quotes",
          pft_eval("&unifor('9'v300)", quoted) == 'кавычки')

    # '&uf' short form is equivalent to &unifor.
    check("&uf('C' …) short form works",
          pft_eval("&uf('C'v10^a)", rec) == '0')


# --------------------------------------------------------------------------- #
# 5b. UNIFOR — newly-deepened batch (date 36/37/38/3A/3B/3C, E/F/G, T, L, 0,
#     +6, +3E/+3D). Grounded in PFT_LANGUAGE.md §9.1 + IRBIS64_UNIFOR_decompiled.c.
# --------------------------------------------------------------------------- #
def unifor_date_checks():
    print('-- unifor date extensions (36/37/38/3A/3B/3C)')
    rec = _book()
    fixed = datetime.datetime(2026, 6, 21, 9, 30, 0)   # June 21st 2026, day 172
    # 36MM/37MM/38MM — month name nominative / genitive / English.
    check("&unifor('3606') -> июнь (nominative)",
          pft_eval("&unifor('3606')", rec, {'now': fixed}) == 'июнь')
    check("&unifor('3706') -> июня (genitive)",
          pft_eval("&unifor('3706')", rec, {'now': fixed}) == 'июня')
    check("&unifor('3806') -> June (English)",
          pft_eval("&unifor('3806')", rec, {'now': fixed}) == 'June')
    # month name fed from another date code: &unifor('36',&unifor('31')).
    check("&unifor('36'&unifor('31')) composes month name from today",
          pft_eval("&unifor('36'&unifor('31'))", rec, {'now': fixed}) == 'июнь')
    # 3A — day-of-year of an inline YYYYMMDD; Jan 1 = 1, the fixed date = 172.
    check("&unifor('3A20260101') -> 1 (Jan 1 day-of-year)",
          pft_eval("&unifor('3A20260101')", rec) == '1')
    check("&unifor('3A20260621') -> 172",
          pft_eval("&unifor('3A20260621')", rec) == '172')
    # 3B — shift a date by ±N days, formatted back to YYYYMMDD.
    check("&unifor('3B20260101,10') -> 20260111",
          pft_eval("&unifor('3B20260101,10')", rec) == '20260111')
    check("&unifor('3B20260301,-1') -> 20260228",
          pft_eval("&unifor('3B20260301,-1')", rec) == '20260228')
    # 3C — whole-day difference date1-date2; non-date arg -> '0'.
    check("&unifor('3C20260621,20260601') -> 20",
          pft_eval("&unifor('3C20260621,20260601')", rec) == '20')
    check("&unifor('3C') bad args -> 0",
          pft_eval("&unifor('3Cxxx,yyy')", rec) == '0')


def unifor_string_checks():
    print('-- unifor string ops (E/F/G/T/L/9/X)')
    rec = {'200': [{'a': 'Hello World Foo Bar'}],
           '300': 'Москва', '301': 'a  b   c d'}
    # E — first N words (whitespace-collapsed).
    check("&unifor('E2'v200^a) -> 'Hello World'",
          pft_eval("&unifor('E2'v200^a)", rec) == 'Hello World')
    # F — keep up to Nth word, preserving original spacing (distinct from E).
    check("&unifor('F2'v301) preserves spacing 'a  b'",
          pft_eval("&unifor('F2'v301)", rec) == 'a  b')
    check("&unifor('E2'v301) collapses spacing 'a b'",
          pft_eval("&unifor('E2'v301)", rec) == 'a b')
    check("&unifor('F10' more words than present -> whole string)",
          pft_eval("&unifor('F10'v301)", rec) == 'a  b   c d')
    check("&unifor('F0') -> empty",
          pft_eval("&unifor('F0'v301)", rec) == '')
    # G — substring up to / from a marker char (# = digit, $ = letter).
    check("&unifor('G0 'v200^a) up-to-space -> 'Hello'",
          pft_eval("&unifor('G0 'v200^a)", rec) == 'Hello')
    check("&unifor('G1W'v200^a) from 'W' -> 'World Foo Bar'",
          pft_eval("&unifor('G1W'v200^a)", rec) == 'World Foo Bar')
    digrec = {'200': [{'a': 'abc123def'}]}
    check("&unifor('G0#') up-to-first-digit -> 'abc'",
          pft_eval("&unifor('G0#'v200^a)", digrec) == 'abc')
    check("&unifor('G1#') from-first-digit -> '123def'",
          pft_eval("&unifor('G1#'v200^a)", digrec) == '123def')
    check("&unifor('G0Z') marker absent (mode 0) -> whole string",
          pft_eval("&unifor('G0Z'v200^a)", rec) == 'Hello World Foo Bar')
    check("&unifor('G1Z') marker absent (mode 1) -> empty",
          pft_eval("&unifor('G1Z'v200^a)", rec) == '')
    # T — transliterate cyrillic -> latin (table 0 / table 1).
    check("&unifor('T0'v300) -> Moskva",
          pft_eval("&unifor('T0'v300)", rec) == 'Moskva')
    tr = {'300': 'Щука'}
    check("&unifor('T0') digraph щ -> 'shh', title-cased",
          pft_eval("&unifor('T0'v300)", tr) == 'Shhuka')
    check("&unifor('T1') simplified table х -> 'kh'",
          pft_eval("&unifor('T1'v300)", {'300': 'Хор'}) == 'Khor')
    # L — term ending: strips %…% insertion-point markers (index-free fallback).
    check("&uf('L') strips %…% markers",
          pft_eval("&uf('Labc%def%ghi')", rec) == 'abcdefghi')


def unifor_misc_checks():
    print('-- unifor misc (0 / +6 / +3E / +3D)')
    rec = {'200': [{'a': 'T'}], '101': 'rus', '300': 'Москва'}
    # 0 — full-record dump: every field as 'tag#value' lines.
    dump = pft_eval("&unifor('0')", rec)
    check("&unifor('0') dumps all tags",
          '200#T' in dump and '101#rus' in dump and '300#Москва' in dump)
    check("&unifor('0') on empty record -> ''",
          pft_eval("&unifor('0')", {}) == '')
    # +6 — record status: 1 live, 0 logically deleted (from ctx['deleted']).
    check("&unifor('+6') live record -> 1",
          pft_eval("&unifor('+6')", rec, {}) == '1')
    check("&unifor('+6') deleted record -> 0",
          pft_eval("&unifor('+6')", rec, {'deleted': True}) == '0')
    # +3E / +3D — URL encode / decode (round-trip).
    enc = pft_eval("&unifor('+3E'v300)", rec)
    check("&unifor('+3E') URL-encodes 'Москва'",
          enc == '%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0')
    check("&unifor('+3D') decodes a literal back to 'Москва'",
          pft_eval("&unifor('+3D%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0')", rec)
          == 'Москва')
    check("+3E then +3D round-trips a cyrillic string",
          pft_eval("&unifor('+3D'&unifor('+3E'v300))", rec) == 'Москва')


# --------------------------------------------------------------------------- #
# 6. Graceful degradation of unsupported constructs.
# --------------------------------------------------------------------------- #
def degrade_checks():
    print('-- graceful degradation')
    rec = _book()
    # ref(l(...)) needs the inverted index — not in this slice; must NOT crash,
    # and the surrounding text must still render.
    out = pft_eval("v200^a, ref(l('I='v933), v200^a), ' КОНЕЦ'", rec)
    check('ref()/l() degrade to empty, rest renders',
          out == 'Основы каталогизации КОНЕЦ')
    # unknown UNIFOR code -> '' (Format error 99 parity), no crash.
    check("unknown unifor code -> empty",
          pft_eval("'A'&unifor('ZZZ')'B'", rec) == 'AB')
    # malformed IF (no FI) degrades rather than raising, in non-strict mode.
    safe = pft_eval("if v920='J' then 'x'", rec)
    check('malformed IF (no FI) degrades, no crash', isinstance(safe, str))
    # mode commands mhl/mpl and placement / # are skipped (no-op) not echoed.
    check('mode command mhl is a no-op',
          pft_eval("mhl, v101", rec) == 'rus')
    check('placement / is a no-op text-wise',
          pft_eval("v101 / v920", rec) == 'rusPAZK')
    # strict mode DOES raise on a real error (editor/preview path).
    raised = False
    try:
        pft_eval("if v920='J' then 'x'", rec, strict=True)
    except pft.PftError as e:
        raised = (e.code == 53)
    check('strict mode raises PftError(53) on IF-without-FI', raised)


# --------------------------------------------------------------------------- #
# 7. Dummy output, numeric functions, predicates.
# --------------------------------------------------------------------------- #
def func_checks():
    print('-- dummy / numeric functions')
    rec = _book()
    # dummy d<tag>: emit literal only if field present.
    check('d200 present -> literal emitted',
          pft_eval('"[есть заглавие]"d200', rec) == '[есть заглавие]')
    check('n700 absent -> literal emitted',
          pft_eval('"(Отсут.)"n700', rec) == '(Отсут.)')
    check('d700 absent -> nothing',
          pft_eval('"[есть]"d700', rec) == '')
    # val() : first number in text, else 0.
    check('val of v999 first instance -> 3',
          pft_eval("val(v999)", rec) == '3')
    # rsum over repeating numeric field 999 -> 3+4+5 = 12.
    check('rsum over v999 -> 12', pft_eval("rsum(v999)", rec) == '12')
    check('rmax over v999 -> 5', pft_eval("rmax(v999)", rec) == '5')
    # f(number, width, dec) formatting.
    check('f(val(v999),4) right-justified width 4',
          pft_eval("f(val(v999),4)", rec).strip() == '3')


# --------------------------------------------------------------------------- #
# 8. Golden-ish slice from PFT_LANGUAGE / brief.pft (920-branch idiom).
# --------------------------------------------------------------------------- #
def golden_checks():
    print('-- golden slice (brief.pft 920 idiom)')
    # brief.pft line 1: IF v920='SZPRF' then '...' else <body> — for a normal
    # record the else-body runs; we check the SZPRF short-circuit and the
    # &unifor('Av920#1'):'SPEC' worklist test (brief.pft line 24).
    fmt = ("if v920='SZPRF' then 'Служебная запись' else "
           "v200^a fi")
    rec = _book()
    check('brief.pft SZPRF else-branch -> title',
          pft_eval(fmt, rec) == 'Основы каталогизации')
    szp = dict(rec, **{'920': 'SZPRF'})
    check('brief.pft SZPRF then-branch',
          pft_eval(fmt, szp) == 'Служебная запись')
    # brief.pft worklist test: &unifor('Av920#1'):'SPEC'
    spec = dict(rec, **{'920': 'SPEC'})
    wl = "if &unifor('Av920#1'):'SPEC' then 'спецвид' else 'обычный' fi"
    check("brief.pft &unifor('Av920#1'):'SPEC' true on SPEC",
          pft_eval(wl, spec) == 'спецвид')
    check("brief.pft worklist test false on PAZK",
          pft_eval(wl, rec) == 'обычный')
    # A compact bibliographic line: title + " / " + author + "." (MD-ish).
    line = "v200^a,' / 'v200^f,'.'"
    check('compact bib line',
          pft_eval(line, rec) == 'Основы каталогизации / Иванова И.И..')


def main():
    field_checks()
    repeat_checks()
    if_checks()
    concat_checks()
    unifor_checks()
    unifor_date_checks()
    unifor_string_checks()
    unifor_misc_checks()
    degrade_checks()
    func_checks()
    golden_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
