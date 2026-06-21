#!/usr/bin/env python3
"""Tenant provisioning (issue #187/#207, epic #223 — MVP Phase 2).

"A new library registers → gets a tenant → catalogues → lends." This is the
*one command* that stands a tenant up end-to-end, on top of the schema-per-tenant
machinery already in ``access.pgstore`` (issue #100):

  1. **schema** — ``CREATE SCHEMA t_<slug>`` + the Access DDL into it (done by
     ``PgAccessStore(tenant_schema=…)`` construction; recorded in
     ``control.tenant``);
  2. **vocabularies** — ``seed_vocabularies()`` populates the system dictionaries
     and creates the institution ones empty (gap A5, #188);
  3. **admin account** — the tenant's first staff account, carrying the seeded
     ``administrator`` role (so the library can immediately log in and run every
     desk);
  4. **plan + entitlements** — ``billing.set_tenant_plan`` records the plan and
     turns exactly that plan's modules ON (issue #101 / #209).

Everything is **idempotent**: re-provisioning the same slug re-converges (no dup
schema, no dup account, plan re-applied) and never destroys tenant data.

**sqlite / single-tenant dev degradation.** There is no control plane on the
sqlite dev box, and only the one ``DEFAULT_TENANT`` ('public') store. Provisioning
there still does the useful, real work it can — seed the roles + vocabularies into
that single store and create the admin account against it — and reports the plan
without a control plane to persist it on. So the same call works in dev (you get a
seeded store + a working admin login) and in prod (you additionally get a real
isolated PG schema + persisted plan/entitlements).

CLI::

    python -m access.provision <slug> [--name NAME] [--admin LOGIN]
                                       [--password PW] [--plan PLAN] [--kind KIND]
    python -m access.provision --list
    python -m access.provision --deprovision <slug>
"""
import os
import sys

from . import billing

# Default library kind for ``control.tenant.kind`` (NOT NULL). 'публичная' = a
# public library; an operator can pass --kind for school/vuz/departmental.
DEFAULT_KIND = 'публичная'
# Dev-default admin password, env-overridable (no secret in code; access.db is
# gitignored, PG tenant pw should be set explicitly in prod).
DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'changeme')
# The role the tenant's first account gets — the seeded role that holds every
# staff grant (see access/seed.py ROLE_GRANTS['administrator']).
ADMIN_ROLE = 'administrator'


def _is_pg_dsn(handle):
    """True if ``handle`` looks like a PostgreSQL DSN string (vs a store object)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


def _on_postgres(store):
    """Decide whether this provisioning targets a real PG control plane.

    Real PG iff a ``PgAccessStore`` (or a DSN string) is in play, or the env
    selects the postgres backend. The sqlite dev ``AccessStore`` → single-tenant.
    """
    if _is_pg_dsn(store):
        return True
    try:
        from .pgstore import PgAccessStore
        if isinstance(store, PgAccessStore):
            return True
    except Exception:
        pass
    return os.environ.get('ACCESS_BACKEND', 'sqlite').lower() in ('postgres', 'pg')


def _seed_admin_account(store, login, password, full_name=''):
    """Create (idempotent) ``login`` and give it the ``administrator`` role.

    Reuses the same primitives the dev seed uses (``create_account`` hashes the
    password pbkdf2-sha256; ``add_role``/``assign_role`` wire the role). Safe to
    re-run: ``create_account`` is INSERT-OR-IGNORE, role assignment is idempotent.
    Returns the account row.
    """
    acc = store.create_account(login, password, full_name or login)
    rid = store.add_role(ADMIN_ROLE)
    store.assign_role(acc['id'], rid)
    return acc


def provision_tenant(store, slug, name, admin_login,
                     admin_password=None, plan='standard', kind=DEFAULT_KIND,
                     dsn=None):
    """Stand up tenant ``<slug>`` end-to-end. Idempotent. Returns a report dict.

    ``store`` is the control-plane handle: on sqlite dev pass the single
    ``AccessStore`` (the 'public' store); on PG pass the public ``PgAccessStore``,
    a DSN string, or ``None`` (the env DSN is used). The tenant-scoped store the
    rest of the steps operate on is built here.

    Steps: schema → vocabularies → admin account (administrator role) → plan +
    entitlements. On the sqlite dev path the single store IS the tenant store.
    """
    admin_password = admin_password or DEFAULT_ADMIN_PASSWORD
    billing._require_plan(plan)               # fail fast on a bad plan name
    # Validate the slug on BOTH paths (PG validates downstream too, but the sqlite
    # dev path must reject a bad slug just as firmly so the contract is uniform).
    from .pgstore import _validate_slug
    _validate_slug(slug)

    if _on_postgres(store):
        # ---- real multi-tenant PG: isolated schema + control row + seeds ----
        from . import pgstore, seed, seed_vocab, entitlements
        if dsn is None:
            dsn = store if _is_pg_dsn(store) else getattr(store, 'dsn', None)
        dsn = dsn or pgstore.default_pg_dsn()
        # 1+2: schema + control row + DDL; seed roles/accounts + default modules +
        # vocabularies (pgstore.provision_tenant does roles/seed/entitlements/vocab).
        tstore = pgstore.provision_tenant(slug, name, kind, dsn=dsn, do_seed=True)
        # 3: the tenant's named admin account (beyond the demo admin the seed makes).
        admin = _seed_admin_account(tstore, admin_login, admin_password, name)
        # 4: plan → record it + drive entitlements to exactly the plan's modules.
        plan_info = billing.set_tenant_plan(tstore, slug, plan, dsn=dsn)
        on_pg = True
    else:
        # ---- sqlite / single-tenant dev: seed the single store, no control plane ----
        from . import seed, seed_vocab
        tstore = store
        seed.seed(tstore)                                 # roles + demo accounts (idempotent)
        try:
            seed_vocab.seed_vocabularies(tstore, from_catalog=False)
        except Exception:
            pass
        admin = _seed_admin_account(tstore, admin_login, admin_password, name)
        plan_info = billing.set_tenant_plan(tstore, slug, plan)   # no-op persist; validates
        on_pg = False

    return {
        'slug': slug, 'name': name, 'kind': kind,
        'admin': {'id': admin['id'], 'login': admin_login,
                  'roles': tstore.account_roles(admin['id'])},
        'plan': plan_info['plan'],
        'modules': plan_info['modules'],
        'postgres': on_pg,
        'store': tstore,
    }


def deprovision_tenant(slug, dsn=None):
    """Drop tenant ``<slug>`` (PG: ``DROP SCHEMA t_<slug> CASCADE`` + control row).

    Delegates to ``pgstore.deprovision_tenant`` (idempotent). A no-op-safe call on
    a clean DB. On sqlite dev there is nothing per-tenant to drop, so this is a
    documented no-op there (the single store is shared).
    """
    from . import pgstore
    try:
        pgstore.deprovision_tenant(slug, dsn=dsn)
        return {'slug': slug, 'deprovisioned': True}
    except Exception as e:
        # psycopg missing / PG down → nothing to do on the dev box.
        return {'slug': slug, 'deprovisioned': False, 'reason': str(e).splitlines()[0]}


def list_tenants(dsn=None):
    """All provisioned tenants from the control catalog, with their plan.

    Reuses ``pgstore.list_tenants`` and joins the billing plan
    (``billing.get_tenant_plan``). Returns [] cleanly when there is no control
    plane (sqlite dev / PG down).
    """
    from . import pgstore
    try:
        rows = pgstore.list_tenants(dsn=dsn)
    except Exception:
        return []
    out = []
    for r in rows:
        item = {'slug': r['slug'], 'name': r['name'], 'kind': r.get('kind')}
        try:
            item['plan'] = billing.get_tenant_plan(r['slug'], dsn=dsn)
        except Exception:
            item['plan'] = billing.DEFAULT_PLAN
        out.append(item)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_store(dsn=None):
    """The control-plane store for the CLI: PG public store, or sqlite AccessStore."""
    backend = os.environ.get('ACCESS_BACKEND', 'sqlite').lower()
    if backend in ('postgres', 'pg') or _is_pg_dsn(dsn):
        from .pgstore import PgAccessStore, default_pg_dsn
        return PgAccessStore(dsn or default_pg_dsn())
    from .store import AccessStore
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.environ.get('ACCESS_DB', os.path.join(here, 'access.db'))
    return AccessStore(path)


def _print(report):
    print('provisioned tenant %r (%s)' % (report['slug'], report['name']))
    print('  postgres : %s' % report['postgres'])
    print('  kind     : %s' % report['kind'])
    print('  admin    : %s (roles: %s)'
          % (report['admin']['login'], ', '.join(report['admin']['roles'])))
    print('  plan     : %s' % report['plan'])
    print('  modules  : %s' % ', '.join(report['modules']))


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(
        prog='python -m access.provision',
        description='Provision / deprovision / list IRBIS-web tenants.')
    p.add_argument('slug', nargs='?', help='tenant slug (^[a-z][a-z0-9_]{0,40}$)')
    p.add_argument('--name', help='human-readable library name (default: slug)')
    p.add_argument('--admin', default='admin', help='admin account login (default: admin)')
    p.add_argument('--password', help='admin password (default: $ADMIN_DEFAULT_PASSWORD or changeme)')
    p.add_argument('--plan', default='standard',
                   choices=sorted(billing.PLANS), help='billing plan (default: standard)')
    p.add_argument('--kind', default=DEFAULT_KIND, help='library kind (default: %s)' % DEFAULT_KIND)
    p.add_argument('--dsn', help='PostgreSQL DSN (default: $ACCESS_PG_DSN)')
    p.add_argument('--list', action='store_true', help='list provisioned tenants and exit')
    p.add_argument('--deprovision', metavar='SLUG', help='drop a tenant and exit')
    args = p.parse_args(argv)

    if args.list:
        rows = list_tenants(dsn=args.dsn)
        if not rows:
            print('(no tenants — sqlite dev or empty control plane)')
        for r in rows:
            print('%-20s %-8s %-12s %s' % (r['slug'], r.get('plan'), r.get('kind'), r['name']))
        return 0

    if args.deprovision:
        rep = deprovision_tenant(args.deprovision, dsn=args.dsn)
        print('deprovisioned %r: %s' % (rep['slug'], rep['deprovisioned'])
              + ('' if rep['deprovisioned'] else ' (%s)' % rep.get('reason')))
        return 0

    if not args.slug:
        p.error('a tenant slug is required (or use --list / --deprovision)')

    store = _build_store(args.dsn)
    report = provision_tenant(
        store, args.slug, args.name or args.slug, args.admin,
        admin_password=args.password, plan=args.plan, kind=args.kind, dsn=args.dsn)
    _print(report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
