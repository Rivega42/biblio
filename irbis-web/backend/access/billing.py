#!/usr/bin/env python3
"""Billing skeleton (D5 / issue #209, epic #223 — MVP Phase 2).

A *skeleton*: tariff plans → the set of functional modules they license + a few
usage limits. NO payment gateway, NO invoicing/VAT, NO metering pipeline — those
are later D5 work. What this provides is the part the MVP needs:

  * a small, declarative ``PLANS`` table (``free`` / ``standard`` / ``pro``);
  * ``plan_modules(plan)`` / ``plan_limits(plan)`` — what a plan unlocks;
  * ``set_tenant_plan(store, tenant, plan)`` — record the tenant's plan AND apply
    its module entitlements (turn the plan's modules ON, the rest OFF) via the
    existing per-tenant entitlement gate (``access.entitlements``, issue #101);
  * ``get_tenant_plan`` / ``tenant_usage`` / ``check_limit`` — read the plan, count
    current usage, and a soft-enforcement helper for a record-create style check.

**Where the plan is stored.** The plan name is a control-plane fact, so it lives
next to the tenant in ``control.tenant.plan`` on PostgreSQL (added idempotently by
``_ensure_plan_column`` — a plain ``ALTER TABLE … ADD COLUMN IF NOT EXISTS`` so an
already-provisioned DB upgrades with no migration step). Entitlements themselves
stay in ``control.tenant_module`` exactly as before — billing only *drives* them.

**Dev / single-tenant degradation.** The sqlite dev box and the non-tenant
``public`` path have no control plane. There ``set_tenant_plan`` is a no-op that
still validates the plan name and reports it; ``get_tenant_plan`` returns the
``DEFAULT_PLAN``; entitlements stay fail-open (everything enabled) exactly as
``access.entitlements`` already behaves with no rows. So billing never locks dev
out and is *off by default until a plan is explicitly set on a provisioned PG
tenant* — matching the "best-effort, off by default if no plan set" contract.
"""
import os

from . import entitlements

# All modules a tenant could be licensed for — the catalogue billing draws from.
# Kept in lock-step with ``entitlements.DEFAULT_MODULES`` (the product's functional
# module set); a plan selects a subset of these to enable.
ALL_MODULES = tuple(entitlements.DEFAULT_MODULES)

# Sentinel "no ceiling" for a limit (the ``pro`` plan and any unset limit).
UNLIMITED = None

# --------------------------------------------------------------------------- #
# Plan catalogue. Each plan declares the modules it licenses and a few usage
# limits. ``limits`` keys are resources ``check_limit`` understands:
#   max_records   — bibliographic records the tenant may hold (catalog size)
#   max_readers   — registered readers
#   max_storage_mb— attached-file / cover storage budget, MB
# A limit of ``UNLIMITED`` (None) means no ceiling. A resource absent from a
# plan's limits is treated as unlimited too.
# --------------------------------------------------------------------------- #
PLANS = {
    'free': {
        'title': 'Free',
        # A try-it tier: read/search + reader portal only; no staff write desks.
        'modules': ('opac', 'reader'),
        'limits': {'max_records': 1000, 'max_readers': 200, 'max_storage_mb': 100},
    },
    'standard': {
        'title': 'Standard',
        # A working small/medium library: catalog + circulation + reader portal +
        # admin + analytics. No acquisition / book-provision (those are pro).
        'modules': ('opac', 'cataloging', 'circulation', 'reader', 'admin', 'analytics'),
        'limits': {'max_records': 100000, 'max_readers': 20000, 'max_storage_mb': 10240},
    },
    'pro': {
        'title': 'Pro',
        # Everything: all functional modules, no ceilings.
        'modules': ALL_MODULES,
        'limits': {'max_records': UNLIMITED, 'max_readers': UNLIMITED,
                   'max_storage_mb': UNLIMITED},
    },
}

# The plan a freshly provisioned tenant gets, and the dev/``public`` answer.
DEFAULT_PLAN = os.environ.get('DEFAULT_PLAN', 'standard')

# Resources ``check_limit`` knows how to enforce.
LIMIT_RESOURCES = ('max_records', 'max_readers', 'max_storage_mb')


class BillingError(Exception):
    """Raised on an unknown plan or an over-limit when enforcing hard."""


# --------------------------------------------------------------------------- #
# Pure plan lookups (no DB) — usable from anywhere, including sqlite dev.
# --------------------------------------------------------------------------- #
def is_plan(plan):
    return plan in PLANS


def _require_plan(plan):
    if plan not in PLANS:
        raise BillingError('unknown plan %r (known: %s)'
                           % (plan, ', '.join(sorted(PLANS))))
    return plan


def plan_modules(plan):
    """The functional modules a plan licenses (sorted), or raise BillingError."""
    return sorted(PLANS[_require_plan(plan)]['modules'])


def plan_limits(plan):
    """The usage limits for a plan as ``{resource: int|None}`` for every known
    resource (missing → UNLIMITED), or raise BillingError."""
    _require_plan(plan)
    declared = PLANS[plan]['limits']
    return {r: declared.get(r, UNLIMITED) for r in LIMIT_RESOURCES}


def plan_limit(plan, resource):
    """One limit value (int) or ``UNLIMITED`` (None). Raises on an unknown plan."""
    return plan_limits(plan).get(resource, UNLIMITED)


def plans_catalog():
    """The full catalogue for an admin UI: [{plan,title,modules,limits}]."""
    return [{'plan': name, 'title': PLANS[name]['title'],
             'modules': sorted(PLANS[name]['modules']), 'limits': plan_limits(name)}
            for name in sorted(PLANS)]


# --------------------------------------------------------------------------- #
# Plan storage on the control plane (PostgreSQL). The sqlite dev / public path
# has no control plane → these degrade to DEFAULT_PLAN / no-op.
# --------------------------------------------------------------------------- #
def _on_control_plane(store):
    """True iff billing should target a real PostgreSQL control plane.

    Real PG iff a ``PgAccessStore`` is in play OR the env selects the postgres
    backend. The sqlite dev ``AccessStore`` (single-tenant) → dev no-op path, even
    for a non-'public' slug (sqlite has no per-tenant schemas / control plane).
    """
    try:
        from .pgstore import PgAccessStore
        if isinstance(store, PgAccessStore):
            return True
    except Exception:
        pass
    return os.environ.get('ACCESS_BACKEND', 'sqlite').lower() in ('postgres', 'pg')


def _ensure_plan_column(dsn):
    """Add ``control.tenant.plan`` if missing (idempotent, no migration step).

    The control schema/table are created by ``ensure_control_schema``; we only add
    the billing column here so billing owns its own storage extension without
    editing the shared control DDL. Safe to call repeatedly. The DEFAULT is inlined
    (a validated PLANS key, not user input) because PG can't infer a parameter's
    type inside DDL.
    """
    from .pgstore import _admin_conn, ensure_control_schema
    ensure_control_schema(dsn)
    default = DEFAULT_PLAN if DEFAULT_PLAN in PLANS else 'standard'
    conn = _admin_conn(dsn)
    try:
        conn.execute(
            "ALTER TABLE control.tenant ADD COLUMN IF NOT EXISTS plan TEXT "
            "NOT NULL DEFAULT '%s'" % default)
    finally:
        conn.close()


def get_tenant_plan(tenant, dsn=None):
    """The tenant's stored plan, or ``DEFAULT_PLAN`` for dev/public/unreachable.

    Fail-soft like ``entitlements``: the ``public`` path, a control plane that is
    down, or a tenant with no row all answer ``DEFAULT_PLAN`` so dev keeps working.
    """
    if entitlements._is_public(tenant) or not _on_control_plane(None):
        # public, or sqlite dev (env backend not postgres) → default plan, no probe.
        return DEFAULT_PLAN
    dsn = dsn or entitlements.default_pg_dsn()
    try:
        _ensure_plan_column(dsn)
        from .pgstore import _admin_conn
        conn = _admin_conn(dsn)
    except Exception:
        return DEFAULT_PLAN
    try:
        r = conn.execute('SELECT plan FROM control.tenant WHERE slug=%s',
                         (tenant,)).fetchone()
        if not r or not r.get('plan'):
            return DEFAULT_PLAN
        plan = r['plan']
        return plan if plan in PLANS else DEFAULT_PLAN
    except Exception:
        return DEFAULT_PLAN
    finally:
        conn.close()


def set_tenant_plan(store, tenant, plan, dsn=None):
    """Assign ``plan`` to ``tenant`` and apply its module entitlements.

    Steps:
      1. validate the plan name (raise BillingError on unknown);
      2. record the plan on ``control.tenant.plan`` (PG only);
      3. drive ``control.tenant_module`` so exactly the plan's modules are enabled
         and every other known module is disabled — the plan becomes the single
         source of truth for what the tenant can reach.

    Dev / ``public`` (no control plane): a no-op that still validates + returns the
    plan (entitlements stay fail-open). ``store`` is accepted for symmetry with the
    other provisioning helpers and future per-tenant bookkeeping; the entitlement
    writes go through the control plane by slug.
    """
    _require_plan(plan)
    if entitlements._is_public(tenant) or not _on_control_plane(store):
        # dev / single-tenant: validate + report, but nothing to persist or gate.
        return {'tenant': tenant, 'plan': plan, 'modules': plan_modules(plan),
                'applied': False}
    dsn = dsn or entitlements.default_pg_dsn()
    _ensure_plan_column(dsn)
    from .pgstore import _admin_conn
    conn = _admin_conn(dsn)
    try:
        conn.execute('UPDATE control.tenant SET plan=%s WHERE slug=%s', (plan, tenant))
    finally:
        conn.close()
    # Apply entitlements: enable the plan's modules, disable the rest. set_module
    # upserts, so this converges regardless of prior state (re-plan safe).
    wanted = set(plan_modules(plan))
    for module in ALL_MODULES:
        entitlements.set_module(tenant, module, module in wanted, dsn)
    return {'tenant': tenant, 'plan': plan, 'modules': sorted(wanted), 'applied': True}


# --------------------------------------------------------------------------- #
# Usage + soft enforcement.
# --------------------------------------------------------------------------- #
def tenant_usage(store, tenant=None):
    """Best-effort current usage counters for a tenant ``store``.

    Counts what the Access store can see locally — registered staff accounts and
    the dictionary footprint — plus, when wired, catalog record / reader counts.
    A resource we can't count is simply omitted (callers treat absence as 0). Never
    raises: a store predating a table just yields a smaller dict.
    """
    usage = {}
    # Records: prefer a catalog handle on the store if present (max_records source).
    counter = getattr(store, 'record_count', None)
    if callable(counter):
        try:
            usage['max_records'] = int(counter())
        except Exception:
            pass
    # Readers: staff store doesn't hold readers, but a wired counter may.
    rcounter = getattr(store, 'reader_count', None)
    if callable(rcounter):
        try:
            usage['max_readers'] = int(rcounter())
        except Exception:
            pass
    return usage


def check_limit(store, tenant, resource, current, plan=None, hard=False, dsn=None):
    """Soft-enforce a usage limit. Returns True iff ``current`` is within budget.

    ``current`` is the count *if this operation proceeds* (so a record-create passes
    ``record_count + 1``). Resolves the tenant's plan (unless ``plan`` is given),
    looks up that resource's ceiling, and compares.

    Best-effort + off by default:
      * an UNLIMITED ceiling (pro plan, or a resource a plan doesn't cap) → True;
      * the dev/``public`` path uses ``DEFAULT_PLAN`` like everything else;
      * an unknown ``resource`` → True (we don't enforce what we don't model).

    ``hard=True`` raises ``BillingError`` instead of returning False when over —
    for a call site that wants to abort rather than branch.
    """
    if resource not in LIMIT_RESOURCES:
        return True
    plan = plan or get_tenant_plan(tenant, dsn)
    ceiling = plan_limit(plan, resource)
    if ceiling is UNLIMITED:
        return True
    ok = int(current) <= int(ceiling)
    if not ok and hard:
        raise BillingError(
            'plan %r limit exceeded for %s: %s > %s'
            % (plan, resource, current, ceiling))
    return ok
