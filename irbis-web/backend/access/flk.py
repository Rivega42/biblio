#!/usr/bin/env python3
"""Declarative ФЛК (формально-логический контроль) validation engine.

Gap A2, epic #188. Implements SPEC_engine_flk.md, FIRST shippable slice: simple
predicate kinds only (full PFT-expression predicates are A1, not yet built — rules
needing them are carried disabled with ``blocked_on='A1'`` so none are lost).

What this module is
-------------------
A *declarative* validator: each rule is a plain dict (the schema of SPEC §1.1);
the engine evaluates a record draft (field/subfield dict) against the active
ruleset and returns a list of violations with ИРБИС result semantics 0/1/2
(SPEC §0): ``0`` passed · ``1`` непреодолимая (blocks save) · ``2`` преодолимая
(saveable after acknowledgement). Worst-severity is aggregated across the run.

Record draft shape (the ``record`` of ``POST /api/validate``)
-------------------------------------------------------------
A field/subfield dict — repeatable fields are lists of instances::

    {
      "920": "PAZK",                       # scalar field value, or
      "200": {"a": "Заглавие", "f": "..."},# instance with subfields, or
      "910": [{"b": "1024365"}, {"b": "1024365"}],  # repeating field
      "101": "rus",
      "10":  {"a": "5-7654-0001-X"}
    }

A field value may be a bare string, a ``{subfield: value}`` dict, or a list of
either. ``value(record, '200', 'a')`` returns the first instance's subfield;
``values(...)`` returns all instances. A bare-string field has an implicit
"whole-field" value reachable with ``subfield=None``.

Predicate kinds implemented in THIS slice
-----------------------------------------
  * ``mandatory``   — field (and optional subfield) present & non-empty.
  * ``dictionary``  — value ∈ a seeded A5 vocabulary (calls the access store's
                      ``vocabulary_values`` — does NOT duplicate seeding).
  * ``isbn_checksum`` / ``issn_checksum`` — the real ISO check-digit algorithm.
  * ``regex``       — value matches / must-not-match a pattern.
  * ``duplicate``   — against the catalog inverted index. No catalog store exists
                      yet → evaluated as a clearly-marked STUB (never fires, the
                      violation list records ``stub=True`` only if a store is wired).

Complex predicates (``&unifor`` / full PFT expressions, БО-свёртка dup keys) are
NOT in this slice: any rule needing them is loaded with ``enabled=False`` and
``blocked_on='A1'`` so it is registered, visible, and never silently dropped.

Tenant tuning (SPEC §3)
-----------------------
``load_ruleset(tenant_overrides=...)`` overlays per-tenant deltas onto the canon:
``enabled`` toggle, ``severity`` *softening* (1→2 only; hardening 2→1 is refused
unless ``allow_hardening``), and ``message`` override. The canon (``SYSTEM_RULES``)
is read-only.
"""
import re

# ИРБИС result semantics (SPEC §0): first char of a ФЛК result.
SEV_PASS = 0   # контроль пройден
SEV_HARD = 1   # непреодолимая — сохранение блокируется
SEV_SOFT = 2   # преодолимая — можно сохранить с подтверждением


# --------------------------------------------------------------------------- #
# Record-draft accessors. A field can be: a bare string, a {subfield:val} dict,
# or a list of either (repeating). All return '' / [] when absent.
# --------------------------------------------------------------------------- #
def _instances(record, field):
    """Normalize a field to a list of instances (each str or dict)."""
    raw = record.get(field)
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _inst_value(inst, subfield):
    """Read ``subfield`` from one instance (str or dict). subfield=None => whole
    field value (the bare string, or a dict's '' / 'value' key if present)."""
    if isinstance(inst, dict):
        if subfield is None:
            return inst.get('') or inst.get('value') or ''
        # subfield letters are matched case-insensitively (ИРБИС ^A == ^a here)
        return inst.get(subfield) or inst.get(subfield.lower()) \
            or inst.get(subfield.upper()) or ''
    # bare string instance: only the whole-field value exists
    return inst if subfield is None else ''


def value(record, field, subfield=None):
    """First instance's subfield value (or '')."""
    for inst in _instances(record, field):
        v = _inst_value(inst, subfield)
        if v:
            return v
    # fall back to first instance even if empty-string, for presence checks
    insts = _instances(record, field)
    return _inst_value(insts[0], subfield) if insts else ''


def values(record, field, subfield=None):
    """All instances' subfield values (skipping empties)."""
    out = []
    for inst in _instances(record, field):
        v = _inst_value(inst, subfield)
        if v:
            out.append(v)
    return out


def present(record, field, subfield=None):
    """SPEC ``p(...)``: field/subfield present and non-empty."""
    return bool(value(record, field, subfield))


# --------------------------------------------------------------------------- #
# Check digits (real algorithms — SPEC AC4). isbn implements both ISBN-10 (mod 11,
# 'X'=10) and ISBN-13 (EAN mod 10). issn is mod 11 with 'X'=10.
# --------------------------------------------------------------------------- #
def _digits_only(s, allow_x=True):
    s = (s or '').upper().replace('-', '').replace(' ', '')
    if allow_x:
        return ''.join(c for c in s if c.isdigit() or c == 'X')
    return ''.join(c for c in s if c.isdigit())


def isbn_checksum_ok(raw):
    """True iff ``raw`` is a structurally valid ISBN-10 or ISBN-13 (correct check
    digit). Empty / wrong-length → False (a non-empty ISBN must be valid)."""
    s = _digits_only(raw)
    if len(s) == 10:
        total = 0
        for i, c in enumerate(s):
            d = 10 if c == 'X' else (ord(c) - 48)
            if c == 'X' and i != 9:
                return False           # 'X' only allowed as the check digit
            if not (c.isdigit() or (c == 'X' and i == 9)):
                return False
            total += (10 - i) * d
        return total % 11 == 0
    if len(s) == 13:
        if not s.isdigit():
            return False
        total = sum((1 if i % 2 == 0 else 3) * (ord(c) - 48) for i, c in enumerate(s))
        return total % 10 == 0
    return False


def issn_checksum_ok(raw):
    """True iff ``raw`` is a structurally valid ISSN (8 chars, mod-11, 'X'=10)."""
    s = _digits_only(raw)
    if len(s) != 8:
        return False
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


# --------------------------------------------------------------------------- #
# 920 branching (SPEC §2.2). Masks: exact value ('J') or prefix ('NJ*' ≡ v920:'NJ').
# --------------------------------------------------------------------------- #
def _mask_matches(record_type, mask):
    if mask.endswith('*'):
        return record_type.startswith(mask[:-1])
    return record_type == mask


def branch_applies(branch, record_type):
    """Does a rule's ``branch`` admit this ``record_type`` (= v920)?

    No branch => always applies. ``negate=False``: applies when v920 matches any
    mask. ``negate=True``: applies when v920 matches NONE of the masks."""
    if not branch:
        return True
    masks = branch.get('match', [])
    hit = any(_mask_matches(record_type, m) for m in masks)
    return (not hit) if branch.get('negate') else hit


# --------------------------------------------------------------------------- #
# Dictionary lookup over the A5-seeded vocab store (does NOT re-implement seeding).
# A store exposes ``vocabulary_values(name)`` -> [{'code':..., 'active':...}, ...].
# --------------------------------------------------------------------------- #
def _dict_has(store, vocab, code):
    """True iff ``code`` is an active value of ``vocab`` in this tenant's store.

    Case-insensitive on the code (ИРБИС dictionary codes are matched loosely). If
    the store can't answer (no vocab tables / missing dict), returns None so the
    caller can treat it as 'unknown' rather than a false violation."""
    if store is None or not code:
        return None
    try:
        rows = store.vocabulary_values(vocab, active_only=True)
    except Exception:
        return None
    if not rows:
        return None
    code_l = code.strip().lower()
    return any((r['code'] or '').strip().lower() == code_l for r in rows)


# --------------------------------------------------------------------------- #
# Predicate dispatch. Each returns True when the rule is VIOLATED (SPEC §1.1:
# condition true == violation). ``ctx`` carries the store/current_mfn/etc.
# --------------------------------------------------------------------------- #
def _eval_when(rule, record):
    """Applicability predicate (SPEC ``when``). Currently supports ``present``
    on the rule's own field/subfield (the only ``when`` shape this slice needs).
    Returns True if the rule should be evaluated."""
    w = rule.get('when')
    if not w:
        return True
    if w == 'present':
        return present(record, rule['field'], rule.get('subfield'))
    if w == 'absent':
        return not present(record, rule['field'], rule.get('subfield'))
    # Anything richer is an A1 expression — be permissive (evaluate the rule).
    return True


def evaluate_rule(rule, record, ctx):
    """Evaluate one (already enabled, already branch-admitted) rule.

    Returns a Violation dict if the rule fires, else None. Never raises: an
    internal predicate error degrades to an ``engineError`` soft violation
    (SPEC AC11) so one bad rule can't sink the whole run."""
    try:
        if not _eval_when(rule, record):
            return None
        kind = rule['predicate']
        fired = _PREDICATES[kind](rule, record, ctx)
        # 'duplicate' may return the STUB sentinel — never a real violation yet.
        if fired is _STUB:
            return None
        if not fired:
            return None
        return _make_violation(rule, record)
    except KeyError:
        # unknown predicate kind == not buildable in this slice -> soft engineError
        return _engine_error(rule, 'unknown predicate: %s' % rule.get('predicate'))
    except Exception as e:                       # noqa: BLE001 (isolate per SPEC AC11)
        return _engine_error(rule, 'rule not evaluated: %s' % e)


_STUB = object()   # sentinel: predicate intentionally not wired (no backing store)


def _pred_mandatory(rule, record, ctx):
    return not present(record, rule['field'], rule.get('subfield'))


def _pred_dictionary(rule, record, ctx):
    v = value(record, rule['field'], rule.get('subfield'))
    if not v:
        return False                  # absence is a separate 'mandatory' rule
    has = _dict_has(ctx.get('store'), rule['vocab'], v)
    if has is None:
        return False                  # store can't answer -> don't fabricate
    return not has                    # violation iff code NOT in the dictionary


def _pred_isbn_checksum(rule, record, ctx):
    v = value(record, rule['field'], rule.get('subfield'))
    return bool(v) and not isbn_checksum_ok(v)


def _pred_issn_checksum(rule, record, ctx):
    v = value(record, rule['field'], rule.get('subfield'))
    return bool(v) and not issn_checksum_ok(v)


def _pred_regex(rule, record, ctx):
    v = value(record, rule['field'], rule.get('subfield'))
    if not v:
        return False
    m = re.search(rule['pattern'], v)
    # negate=True (default): VIOLATION when the pattern does NOT match (required shape)
    # negate=False: VIOLATION when the pattern DOES match (forbidden shape)
    return (m is None) if rule.get('regex_negate', True) else (m is not None)


def _pred_duplicate(rule, record, ctx):
    """Duplicate check against the tenant's inverted index (SPEC §1 #4/#5).

    No catalog index store exists in this slice. If a ``dup_index`` callable is
    wired in ctx it is used; otherwise the predicate is a clearly-marked STUB
    that never fires (recon dependency carried, not lost)."""
    dup_index = ctx.get('dup_index')
    if dup_index is None:
        return _STUB
    v = value(record, rule['field'], rule.get('subfield'))
    if not v:
        return False
    other = dup_index(rule['index'], v, ctx.get('current_mfn'))
    return bool(other)


_PREDICATES = {
    'mandatory': _pred_mandatory,
    'dictionary': _pred_dictionary,
    'isbn_checksum': _pred_isbn_checksum,
    'issn_checksum': _pred_issn_checksum,
    'regex': _pred_regex,
    'duplicate': _pred_duplicate,
}


def _make_violation(rule, record):
    return {
        'ruleId': rule['id'],
        'severity': rule['severity'],
        'message': _format_message(rule, record),
        'path': rule.get('path', rule.get('field', '')),
        'field': rule.get('field'),
        'subfield': rule.get('subfield'),
    }


def _engine_error(rule, detail):
    return {
        'ruleId': rule['id'],
        'severity': SEV_SOFT,            # never block on an engine failure
        'message': 'Правило %s не вычислено (%s)' % (rule['id'], detail),
        'path': rule.get('path', rule.get('field', '')),
        'field': rule.get('field'),
        'subfield': rule.get('subfield'),
        'engineError': True,
    }


_TEMPLATE = re.compile(r'\{\{\s*([0-9]+)(?:\^([a-zA-Z]))?\s*\}\}')


def _format_message(rule, record):
    """Substitute ``{{NNN^x}}`` / ``{{NNN}}`` tokens from the record (thin local
    version of SPEC's A1.format; full templating is A1)."""
    msg = rule.get('message', '')

    def repl(m):
        return value(record, m.group(1), m.group(2)) or ''
    return _TEMPLATE.sub(repl, msg)


# --------------------------------------------------------------------------- #
# Canon ruleset — 8 real rules transcribed from FLC_VALIDATION.md (SPEC §1.3).
# --------------------------------------------------------------------------- #
SYSTEM_RULES = [
    # (1) ISBN checksum — !10.PFT, FLC §2.1. Bad check digit is преодолимо (2).
    {
        'id': 'fld.10.isbn.checksum', 'source': '!10.PFT',
        'scope': 'field', 'field': '10', 'subfield': 'a',
        'predicate': 'isbn_checksum', 'when': 'present',
        'severity': SEV_SOFT,
        'message': 'Ошибка в ISBN: {{10^a}}', 'path': '010/a',
        'phase': 'fieldExit', 'enabled': True,
    },
    # (2) mandatory title 200^a — dbnflc.pft#6, FLC §1. Непреодолимо (1) for the
    #     non-аналитика branch (920 not starting NJ); the analytics softening is a
    #     paired rule (see #2b) so severity stays declarative (SPEC §1.3 note).
    {
        'id': 'rec.200a.mandatory', 'source': 'dbnflc.pft#6',
        'scope': 'record', 'field': '200', 'subfield': 'a',
        'branch': {'field': '920', 'match': ['NJ*', 'A*'], 'negate': True},
        'predicate': 'mandatory',
        'severity': SEV_HARD,
        'message': 'Ошибка : Отсутствует заглавие', 'path': '200/a',
        'phase': 'save', 'enabled': True,
    },
    # (2b) mandatory title 200^a for analytics (920 = A*) — softened to 2.
    {
        'id': 'rec.200a.mandatory.analyt', 'source': 'dbnflc.pft#6',
        'scope': 'record', 'field': '200', 'subfield': 'a',
        'branch': {'field': '920', 'match': ['A*'], 'negate': False},
        'predicate': 'mandatory',
        'severity': SEV_SOFT,
        'message': 'Отсутствует заглавие (аналитика)', 'path': '200/a',
        'phase': 'save', 'enabled': True,
    },
    # (3) language dictionary 101 — !101.PFT, jz.mnu, FLC §2.2. Bad code = 1.
    {
        'id': 'fld.101.lang.dict', 'source': '!101.PFT',
        'scope': 'field', 'field': '101', 'subfield': None,
        'predicate': 'dictionary', 'vocab': 'jz.mnu', 'when': 'present',
        'severity': SEV_HARD,
        'message': 'неверен код языка: {{101}}', 'path': '101',
        'phase': 'fieldExit', 'enabled': True,
    },
    # (4) doc-type dictionary 900^b — !900.PFT, vd.mnu, FLC §2.2. Преодолимо (2).
    {
        'id': 'fld.900.doctype.dict', 'source': '!900.PFT',
        'scope': 'subfield', 'field': '900', 'subfield': 'b',
        'predicate': 'dictionary', 'vocab': 'vd.mnu', 'when': 'present',
        'severity': SEV_SOFT,
        'message': 'Неверен вид док-та: {{900^b}}', 'path': '900/b',
        'phase': 'fieldExit', 'enabled': True,
    },
    # (5) worklist dictionary 920 — !920.PFT, 920.mnu, FLC §2.2. Selector node;
    #     dictionary 920.mnu is institution-seeded (may be empty) -> _dict_has
    #     returns None and the rule no-ops until the tenant fills it. Непреодолимо.
    {
        'id': 'fld.920.worklist.dict', 'source': '!920.PFT',
        'scope': 'field', 'field': '920', 'subfield': None,
        'predicate': 'dictionary', 'vocab': '920.mnu', 'when': 'present',
        'severity': SEV_HARD,
        'message': 'Неверен код рабочего листа: {{920}}', 'path': '920',
        'phase': 'save', 'enabled': True,
    },
    # (6) mandatory worklist 920 — !920.PFT, FLC §2.2. 920 absent = непреодолимо.
    {
        'id': 'rec.920.mandatory', 'source': '!920.PFT',
        'scope': 'field', 'field': '920', 'subfield': None,
        'predicate': 'mandatory',
        'severity': SEV_HARD,
        'message': 'Отсутствует Код рабочего листа', 'path': '920',
        'phase': 'save', 'enabled': True,
    },
    # (7) duplicate inv# 910^b — dbnflc.pft#7, IN= index, FLC §1. STUB: no catalog
    #     index store yet -> the predicate is wired but never fires without a
    #     ``dup_index`` in ctx (carried, not lost). Преодолимо (2).
    {
        'id': 'rec.910b.dup.inv', 'source': 'dbnflc.pft#7',
        'scope': 'subfield', 'field': '910', 'subfield': 'b',
        'branch': {'field': '920', 'match': ['J', 'ASP', 'AUNTD'], 'negate': True},
        'predicate': 'duplicate', 'index': 'IN=', 'when': 'present',
        'severity': SEV_SOFT,
        'message': 'Дублетный инв.номер: {{910^b}}', 'path': '910/b',
        'phase': 'save', 'enabled': True,
        'stub': True, 'blocked_on': 'catalog-index',
    },
    # (8) ФИО исполнителя 907^a — dbnflc.pft#1, FLC §1. The real rule matches a
    #     907 instance whose date == today (&unifor('3')) — that date predicate is
    #     an A1 expression, so the date-matched variant is carried disabled
    #     (blocked_on=A1). The shipped slice enforces the weaker, fully-decidable
    #     form: a non-журнал record must carry at least one 907^a. Преодолимо (2).
    {
        'id': 'rec.907.fio', 'source': 'dbnflc.pft#1',
        'scope': 'record', 'field': '907', 'subfield': 'a',
        'branch': {'field': '920', 'match': ['J'], 'negate': True},
        'predicate': 'mandatory',
        'severity': SEV_SOFT,
        'message': 'Ошибка : не определено ФИО исполнителя', 'path': '907/a',
        'phase': 'save', 'enabled': True,
    },
    # (8b) ФИО исполнителя with TODAY's date — needs &unifor('3') (A1). Carried
    #      disabled so the full rule is registered and not lost.
    {
        'id': 'rec.907.fio.today', 'source': 'dbnflc.pft#1',
        'scope': 'record', 'field': '907', 'subfield': 'a',
        'branch': {'field': '920', 'match': ['J'], 'negate': True},
        'predicate': 'unifor_date_today',
        'severity': SEV_SOFT,
        'message': 'Ошибка : не определено ФИО исполнителя (на текущую дату)',
        'path': '907/a', 'phase': 'save',
        'enabled': False, 'blocked_on': 'A1',
    },
]


# --------------------------------------------------------------------------- #
# Ruleset loading + per-tenant override overlay (SPEC §3).
# --------------------------------------------------------------------------- #
def _clone(rule):
    r = dict(rule)
    if 'branch' in r and r['branch'] is not None:
        r['branch'] = dict(r['branch'])
    return r


def load_ruleset(tenant_overrides=None, allow_hardening=False):
    """Return the effective ruleset = canon ⊕ per-tenant deltas (SPEC §3.1).

    ``tenant_overrides`` maps ``ruleId -> {enabled?, severity?, message?}``. A
    delta may DISABLE a rule, SOFTEN it (1→2), or override its message. Hardening
    (2→1) is refused unless ``allow_hardening`` (SPEC §3.1 policy R4) — the canon
    severity is kept instead. ``None`` fields inherit the canon.

    Returns a list of effective rule dicts (canon order preserved)."""
    overrides = tenant_overrides or {}
    out = []
    for canon in SYSTEM_RULES:
        eff = _clone(canon)
        ov = overrides.get(canon['id'])
        if ov:
            if ov.get('enabled') is not None:
                eff['enabled'] = bool(ov['enabled'])
            if ov.get('severity') is not None:
                new_sev = int(ov['severity'])
                # softening (canon 1 -> 2) always allowed; hardening gated.
                if new_sev >= eff['severity'] or allow_hardening:
                    eff['severity'] = new_sev
            if ov.get('message') is not None:
                eff['message'] = ov['message']
        out.append(eff)
    return out


# --------------------------------------------------------------------------- #
# The engine — evaluate a record against a ruleset for one phase.
# --------------------------------------------------------------------------- #
def validate(record, ruleset=None, phase='save', field=None,
             store=None, current_mfn=None, dup_index=None,
             tenant_overrides=None):
    """Validate ``record`` for ``phase`` and aggregate worst-severity (SPEC §2).

    Pipeline (SPEC §2.1–2.4):
      1. resolve the ruleset (canon ⊕ tenant overrides) if not supplied;
      2. filter by ``enabled`` and ``phase`` (and ``field`` for fieldExit);
      3. 920 first (selector), then by field, then by rule id (determinism);
      4. apply ``branch`` (920 record-type gating) and ``when``;
      5. evaluate the predicate -> Violation (engineError-isolated);
      6. aggregate: overallSeverity = worst, canSave = (overall != 1), sorted list.

    Returns ``{overallSeverity, canSave, violations:[...]}``."""
    if ruleset is None:
        ruleset = load_ruleset(tenant_overrides)
    record_type = value(record, '920') or ''
    ctx = {'store': store, 'current_mfn': current_mfn, 'dup_index': dup_index}

    # SPEC §2.1: the `save` phase is a FULL run — it also includes the field-level
    # `!NNN` (fieldExit) rules, not only record-scope `save` rules. `fieldExit` on
    # its own runs just that field's rules (live per-field feedback).
    if phase == 'save':
        active = [r for r in ruleset if r.get('enabled', True)
                  and r.get('phase') in ('save', 'fieldExit')]
    else:
        active = [r for r in ruleset if r.get('enabled', True) and r.get('phase') == phase]
    if phase == 'fieldExit' and field is not None:
        active = [r for r in active if r.get('field') == field]

    # Order: 920 selector first, then ascending field label, then rule id (SPEC §2.1).
    def _order_key(r):
        is_920 = 0 if r.get('field') == '920' else 1
        try:
            fld = int(r.get('field') or 0)
        except ValueError:
            fld = 0
        return (is_920, fld, r['id'])
    active.sort(key=_order_key)

    violations = []
    for rule in active:
        if not branch_applies(rule.get('branch'), record_type):
            continue
        v = evaluate_rule(rule, record, ctx)
        if v is not None:
            violations.append(v)

    overall = _worst_severity(violations)
    # Sort for the UI: severity 1 first, then 2; within, by path (SPEC §2.4).
    violations.sort(key=lambda v: (0 if v['severity'] == SEV_HARD else 1,
                                   v.get('path') or ''))
    return {
        'overallSeverity': overall,
        'canSave': overall != SEV_HARD,
        'violations': violations,
    }


def _worst_severity(violations):
    """worst() over the list: 1 if any hard, else 2 if any soft, else 0."""
    if any(v['severity'] == SEV_HARD for v in violations):
        return SEV_HARD
    if any(v['severity'] == SEV_SOFT for v in violations):
        return SEV_SOFT
    return SEV_PASS
