#!/usr/bin/env python3
"""Licensing / entitlements (issue #101, I1): which MODULES a tenant is licensed for.

Entitlements answer "is this tenant LICENSED for module X?" — a separate axis from
grants. Grants are *can-do* (this account may write IBIS); entitlements are
*is-licensed* (this tenant has the cataloging module turned on at all). A request
is refused if EITHER fails: a valid grant on a disabled module is still refused
(403/404). Billing (initiative I7) will later consume this table; it is kept
independent of billing here.

Storage: ``control.tenant_module(tenant_id, module, enabled, PRIMARY KEY(tenant_id,
module))`` in the PostgreSQL ``control`` schema (the cross-tenant catalog, next to
``control.tenant``). DDL is idempotent (``schema_control.sql``).

Dev / single-tenant fallback: the sqlite dev box and the non-tenant ``public``
path have no ``control`` schema. There, entitlement checks default to *enabled*
(``is_module_enabled`` returns True) so the guest flow and sqlite dev keep working
with zero config — licensing only bites once a tenant is provisioned on PG and a
module is explicitly disabled.
"""
import os

# Functional modules of the product (surfaces composed by grants). The seed turns
# these ON by default for a freshly provisioned tenant; an operator disables one to
# revoke its license. Keep this list aligned with the product's functional modules.
DEFAULT_MODULES = (
    'opac',          # читательский портал / поиск-каталог
    'cataloging',    # каталогизация (запись/редактирование)
    'circulation',   # книговыдача
    'acquisition',   # комплектование (АРМ Комплектатор)
    'bookprovision', # книгообеспеченность (ВУЗ — связка + Кко)
    'reader',        # читательский кабинет / заказы
    'admin',         # администрирование тенанта
    'analytics',     # отчёты/статистика
)


def default_pg_dsn():
    """DSN used by entitlement helpers — same env knob the Access store reads."""
    return os.environ.get(
        'ACCESS_PG_DSN', 'postgresql://postgres:pg@127.0.0.1:5433/irbis_access')


def _admin_conn(dsn):
    """Short-lived autocommit connection for control-plane reads/writes.

    Lazy psycopg import so this module imports on a Python without psycopg
    (the sqlite dev path never calls anything that needs it).
    """
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def _tenant_id(conn, tenant):
    """Resolve a tenant slug to its control.tenant id, or None if unknown."""
    r = conn.execute('SELECT id FROM control.tenant WHERE slug=%s', (tenant,)).fetchone()
    return r['id'] if r else None


def seed_modules(tenant, dsn=None, modules=DEFAULT_MODULES, enabled=True):
    """Idempotently insert the default module set for ``tenant`` as enabled.

    Run as part of provisioning. Existing rows are left untouched (so an operator
    who disabled a module is not re-enabled by a re-provision). Returns the list
    of modules seeded. No-op-safe to call repeatedly.
    """
    dsn = dsn or default_pg_dsn()
    conn = _admin_conn(dsn)
    try:
        tid = _tenant_id(conn, tenant)
        if tid is None:
            raise ValueError('unknown tenant %r (provision it first)' % tenant)
        for m in modules:
            conn.execute(
                'INSERT INTO control.tenant_module(tenant_id, module, enabled) '
                'VALUES(%s,%s,%s) ON CONFLICT(tenant_id, module) DO NOTHING',
                (tid, m, bool(enabled)))
        return list(modules)
    finally:
        conn.close()


def set_module(tenant, module, enabled, dsn=None):
    """Enable/disable one module for ``tenant`` (upsert). Returns the new state."""
    dsn = dsn or default_pg_dsn()
    conn = _admin_conn(dsn)
    try:
        tid = _tenant_id(conn, tenant)
        if tid is None:
            raise ValueError('unknown tenant %r' % tenant)
        conn.execute(
            'INSERT INTO control.tenant_module(tenant_id, module, enabled) '
            'VALUES(%s,%s,%s) ON CONFLICT(tenant_id, module) '
            'DO UPDATE SET enabled=EXCLUDED.enabled',
            (tid, module, bool(enabled)))
        return bool(enabled)
    finally:
        conn.close()


def enabled_modules(tenant, dsn=None):
    """List the enabled module names for ``tenant`` (sorted).

    Returns the explicit DEFAULT_MODULES list for the dev/``public`` path or when
    the control plane is unreachable / has no rows — i.e. "all enabled" by default,
    matching ``is_module_enabled``'s fail-open dev behaviour.
    """
    if _is_public(tenant):
        return list(DEFAULT_MODULES)
    dsn = dsn or default_pg_dsn()
    try:
        conn = _admin_conn(dsn)
    except Exception:
        return list(DEFAULT_MODULES)
    try:
        tid = _tenant_id(conn, tenant)
        if tid is None:
            return list(DEFAULT_MODULES)
        rows = conn.execute(
            'SELECT module FROM control.tenant_module '
            'WHERE tenant_id=%s AND enabled=true ORDER BY module', (tid,)).fetchall()
        if not rows:
            return list(DEFAULT_MODULES)
        return [r['module'] for r in rows]
    except Exception:
        return list(DEFAULT_MODULES)
    finally:
        conn.close()


def is_module_enabled(tenant, module, dsn=None):
    """True iff ``module`` is licensed for ``tenant``.

    Fail-open for dev/single-tenant: the ``public`` (non-tenant) path, an
    unreachable control plane, or a tenant with no tenant_module rows all return
    True so sqlite dev and the guest flow keep working. Once a tenant exists on PG
    with explicit rows, the stored ``enabled`` flag is authoritative — a disabled
    module returns False even when the caller holds a valid grant.
    """
    if _is_public(tenant):
        return True
    dsn = dsn or default_pg_dsn()
    try:
        conn = _admin_conn(dsn)
    except Exception:
        return True                      # control plane down -> don't lock dev out
    try:
        tid = _tenant_id(conn, tenant)
        if tid is None:
            return True                  # tenant not provisioned in control -> dev/public
        r = conn.execute(
            'SELECT enabled FROM control.tenant_module WHERE tenant_id=%s AND module=%s',
            (tid, module)).fetchone()
        if r is None:
            return True                  # no explicit row -> not gated (default-enabled)
        return bool(r['enabled'])
    except Exception:
        return True
    finally:
        conn.close()


def _is_public(tenant):
    """The non-tenant/single-tenant dev path: no control plane, never gated."""
    return not tenant or tenant == 'public'


# --- Режимы продукта (узел 3): «режим» = ПРЕСЕТ включённых модулей ----------
# «Режим» тенанта — это НЕ параллельная сущность, а именованный пресет поверх
# существующего tenant_module-механизма. portal-only — first-class режим.
#   full      — вся АБИС (все модули): Biblio как полная система.
#   webportal — только читательский портал (OPAC + кабинет + статистика), БЕЗ
#               staff-АРМов (каталогизация/выдача/комплектование/ККО/админ).
#   demo      — тот же портальный набор, но витринный; «витринное» поведение
#               (read-mostly, сэмпл-данные) включается отдельно APP_ENV/overlay
#               (см. docker-compose.demo.yml) — режим лишь сужает модули.
MODE_PRESETS = {
    'full':      tuple(DEFAULT_MODULES),
    'webportal': ('opac', 'reader', 'analytics'),
    'demo':      ('opac', 'reader'),
}
MODES = tuple(MODE_PRESETS)


def set_mode(tenant, mode, dsn=None):
    """Применить режим к тенанту: включить модули его пресета, выключить прочие.

    Режим — пресет над tenant_module: enable модули из ``MODE_PRESETS[mode]``,
    disable все остальные из ``DEFAULT_MODULES``. Возвращает отсортированный
    список включённых модулей. Неизвестный режим → ``ValueError``. На public/dev
    (без control-plane) запись модулей — no-op в ``set_module`` (fail-open).
    """
    if mode not in MODE_PRESETS:
        raise ValueError('unknown mode %r (expected one of %s)'
                         % (mode, ', '.join(MODES)))
    preset = set(MODE_PRESETS[mode])
    for m in DEFAULT_MODULES:
        set_module(tenant, m, m in preset, dsn=dsn)
    return sorted(preset)


def derive_mode(modules):
    """Определить режим по набору включённых модулей (для отображения в админке).

    Точное совпадение с пресетом → его имя; иначе ``'custom'`` (оператор собрал
    нестандартный набор вручную через per-module тумблеры). Чистая функция —
    не ходит в БД (зовущий передаёт ``enabled_modules(tenant)``).
    """
    s = set(modules or ())
    for name, preset in MODE_PRESETS.items():
        if s == set(preset):
            return name
    return 'custom'
