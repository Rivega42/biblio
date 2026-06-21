#!/usr/bin/env python3
"""Vocabulary seeding orchestration (gap A5, epic #188).

Two halves:

  1. ``ensure_seed_catalog(dsn)`` — populate ``control.seed_catalog`` (the master
     copy of the SYSTEM dictionaries) from ``seed_data.py``. PostgreSQL only; runs
     once per control plane, idempotent (upsert on (vocab, code)). Called inside
     provisioning before a tenant is seeded.

  2. ``seed_vocabularies(store, dsn=...)`` — populate ONE tenant's schema:
       * SYSTEM vocabs: read from ``control.seed_catalog`` (PG) and copy values into
         the tenant's ``vocabulary``/``vocabulary_value`` with ``origin='seed'``.
       * INSTITUTION vocabs/trees: create EMPTY metadata rows (no values) so the
         library can fill them (import from source ИРБИS §2.3, or the ws5 editor).
     Works against both backends: the sqlite dev ``AccessStore`` (single-tenant
     ``public``) seeds straight from ``seed_data.py`` (no control plane); the
     ``PgAccessStore`` (tenant-scoped) seeds from the control catalog.

Idempotent throughout (upsert on name / (vocab, code)) so re-provision is safe and
never duplicates or clobbers a value the library marked custom/imported.
"""
from . import seed_data


def ensure_seed_catalog(dsn=None):
    """Fill ``control.seed_catalog`` from ``seed_data.SYSTEM_VOCABS`` (idempotent).

    PostgreSQL only — the control plane holds the master copy. Imported lazily so
    the sqlite dev path (no psycopg) never touches it.
    """
    from .pgstore import default_pg_dsn, _admin_conn, ensure_control_schema
    dsn = dsn or default_pg_dsn()
    ensure_control_schema(dsn)              # creates control.seed_catalog if absent
    conn = _admin_conn(dsn)
    try:
        for (name, code, label, kind, version, title, hint, sort) in \
                seed_data.system_catalog_rows():
            conn.execute(
                'INSERT INTO control.seed_catalog'
                '(vocab,code,label,kind,seed_version,title,field_hint,sort) '
                'VALUES(%s,%s,%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT(vocab,code) DO UPDATE SET '
                'label=EXCLUDED.label, title=EXCLUDED.title, '
                'field_hint=EXCLUDED.field_hint, sort=EXCLUDED.sort, '
                'seed_version=EXCLUDED.seed_version',
                (name, code, label, kind, version, title, hint, sort))
    finally:
        conn.close()


def _seed_institution_empties(store):
    """Create EMPTY metadata rows for institution dictionaries + trees.

    The library fills the values later (import/manual). seed_version stays NULL —
    this is what makes ``kv.mnu`` exist-but-empty rather than missing, so the UI can
    prompt "fill me in" and reseed knows to leave it alone.
    """
    for name, spec in seed_data.INSTITUTION_VOCABS.items():
        store.upsert_vocabulary(name, spec['title'], 'institution',
                                spec.get('field_hint'), None)


def seed_vocabularies(store, dsn=None, from_catalog=None):
    """Seed ``store``'s tenant schema with system vocabs + empty institution vocabs.

    ``from_catalog``:
      * ``True``  — read SYSTEM values from ``control.seed_catalog`` (PG path).
      * ``False`` — read SYSTEM values directly from ``seed_data.py`` (sqlite dev).
      * ``None``  — auto: catalog iff the store is a tenant-scoped ``PgAccessStore``.

    Returns a small report dict (counts) for observability/tests. Idempotent.
    """
    if from_catalog is None:
        from_catalog = bool(getattr(store, 'tenant_schema', None))

    sys_vocabs = 0
    sys_values = 0

    if from_catalog:
        from .pgstore import default_pg_dsn, _admin_conn
        dsn = dsn or default_pg_dsn()
        conn = _admin_conn(dsn)
        try:
            rows = conn.execute(
                'SELECT vocab,code,label,seed_version,title,field_hint,sort '
                'FROM control.seed_catalog ORDER BY vocab, sort, code').fetchall()
        finally:
            conn.close()
        seen = set()
        for r in rows:
            if r['vocab'] not in seen:
                store.upsert_vocabulary(r['vocab'], r['title'], 'system',
                                        r['field_hint'], r['seed_version'])
                seen.add(r['vocab'])
                sys_vocabs += 1
            store.upsert_vocabulary_value(r['vocab'], r['code'], r['label'],
                                          r['sort'], 'seed')
            sys_values += 1
    else:
        # Direct from seed_data (sqlite dev — no control plane).
        for name, spec in seed_data.SYSTEM_VOCABS.items():
            store.upsert_vocabulary(name, spec['title'], 'system',
                                    spec['field_hint'], seed_data.SEED_VERSION)
            sys_vocabs += 1
            for sort, (code, label) in enumerate(spec['values']):
                store.upsert_vocabulary_value(name, code, label, sort, 'seed')
                sys_values += 1

    _seed_institution_empties(store)

    return {
        'system_vocabs': sys_vocabs,
        'system_values': sys_values,
        'institution_vocabs': len(seed_data.INSTITUTION_VOCABS),
        'seed_version': seed_data.SEED_VERSION,
    }


def import_tree(store, name, nodes, origin='imported'):
    """Persist parsed ``.tre`` ``nodes`` (from access.mnu.parse_tre) into the tenant.

    Resolves each node's parent-index into a parent *code* and a dotted materialized
    ``path`` of codes, then upserts. Used by the import pipeline (SPEC §4.2).
    """
    codes = [n['code'] for n in nodes]
    paths = []
    for i, n in enumerate(nodes):
        parent_idx = n.get('parent')
        parent_code = codes[parent_idx] if parent_idx is not None else None
        path = (paths[parent_idx] + '.' + n['code']) if parent_idx is not None else n['code']
        paths.append(path)
        store.upsert_classification_node(name, n['code'], n['label'],
                                         parent_code, n['depth'], path, i)
    return {'tree': name, 'nodes': len(nodes)}
