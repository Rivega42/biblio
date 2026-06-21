#!/usr/bin/env python3
"""Per-tenant vocabulary seeding tests (gap A5, epic #188).

Covers the seeding engine layered on the merged tenancy (#100) + Identity (#101):

  1. Parsers (pure, always run): ``parse_mnu`` round-trips incl. CP1251 bytes and
     the ``*****`` terminator (recon #VOC-03 empty final pair filtered);
     ``parse_tre`` recovers depth + parent from leading dots.
  2. sqlite dev seed (pure, always run): seeding the single-tenant ``public`` store
     populates SYSTEM vocabs with values and creates INSTITUTION vocabs EMPTY;
     re-seed is idempotent.
  3. PostgreSQL (skipped cleanly when PG unavailable): provision a tenant ->
     system vocabs present & populated, institution vocabs present & empty;
     per-tenant isolation (tenant A's vocab edit invisible to B); re-provision
     idempotent.

Invoked by the test_access.py runner (seeding_checks) so the CI postgres step
exercises the PG path with NO .github/ change. The sqlite suite stays green
locally with no DB.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import mnu as _mnu
from access import seed_data
from access import seed_vocab
from access.store import AccessStore

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
# 1. Parsers — pure, backend-independent.
# --------------------------------------------------------------------------- #
def parser_checks():
    print('-- parsers (.mnu / .tre)')

    # Basic round-trip from a str menu with the ***** terminator.
    text = 'KN\nКниги в целом\n05\nОднотомное издание\n*****\n'
    pairs = _mnu.parse_mnu(text)
    check('parse_mnu pairs count', pairs == [('KN', 'Книги в целом'),
                                             ('05', 'Однотомное издание')])

    # CP1251 BYTES decode -> UTF-8 (the on-disk ИРБИS encoding).
    raw = ('rus\nРусский\neng\nАнглийский\n*****\n').encode('cp1251')
    pairs_cp = _mnu.parse_mnu(raw)
    check('parse_mnu decodes cp1251 bytes',
          pairs_cp == [('rus', 'Русский'), ('eng', 'Английский')])

    # Empty final pair before ***** is dropped (recon #VOC-03).
    artefact = 'a\nAlpha\nb\nBeta\n\n\n*****\n'
    check('parse_mnu drops empty final pair',
          _mnu.parse_mnu(artefact) == [('a', 'Alpha'), ('b', 'Beta')])

    # Stops at ***** — nothing after the terminator leaks in.
    after = 'a\nAlpha\n*****\nGARBAGE\nMORE\n'
    check('parse_mnu stops at terminator', _mnu.parse_mnu(after) == [('a', 'Alpha')])

    # Real seed data round-trips through a serialize->parse cycle (ste.mnu, 14).
    ste = seed_data.SYSTEM_VOCABS['ste.mnu']['values']
    serialized = ''.join('%s\n%s\n' % (c, l) for c, l in ste) + '*****\n'
    check('parse_mnu round-trips ste.mnu (14)',
          _mnu.parse_mnu(serialized.encode('cp1251')) == ste)

    # .tre: leading dots -> depth; parent reconstructed by the level stack.
    tre = 'Root\n.Child A\n..Leaf A1\n.Child B\n'
    nodes = _mnu.parse_tre(tre)
    check('parse_tre node count', len(nodes) == 4)
    check('parse_tre depths', [n['depth'] for n in nodes] == [0, 1, 2, 1])
    check('parse_tre root has no parent', nodes[0]['parent'] is None)
    check('parse_tre child parent is root', nodes[1]['parent'] == 0)
    check('parse_tre leaf parent is child A', nodes[2]['parent'] == 1)
    check('parse_tre second child reparents to root', nodes[3]['parent'] == 0)

    # live extraction is a documented stub, must raise (not silently no-op)
    raised = False
    try:
        _mnu.import_mnu_from_source('kv.mnu')
    except NotImplementedError:
        raised = True
    check('source-ИРБИS extraction is a documented stub', raised)


# --------------------------------------------------------------------------- #
# 2. sqlite dev seed — pure (in-memory db, no server).
# --------------------------------------------------------------------------- #
def sqlite_seed_checks():
    print('-- sqlite seed (single-tenant public)')
    st = AccessStore(':memory:')
    report = seed_vocab.seed_vocabularies(st, from_catalog=False)

    check('report counts system vocabs', report['system_vocabs'] == len(seed_data.SYSTEM_VOCABS))
    check('report counts institution vocabs',
          report['institution_vocabs'] == len(seed_data.INSTITUTION_VOCABS))

    # SYSTEM vocab present & populated
    vd = st.get_vocabulary('vd.mnu')
    check('system vocab vd.mnu present', vd is not None and vd['kind'] == 'system')
    check('system vocab vd.mnu has seed_version', vd['seed_version'] == seed_data.SEED_VERSION)
    vd_vals = st.vocabulary_values('vd.mnu')
    check('vd.mnu populated', len(vd_vals) == len(seed_data.SYSTEM_VOCABS['vd.mnu']['values']))
    check('vd.mnu has KN code', any(v['code'] == 'KN' for v in vd_vals))

    # ste.mnu full 14 (circulation-critical)
    ste_vals = st.vocabulary_values('ste.mnu')
    check('ste.mnu full (14)', len(ste_vals) == 14)
    check('ste.mnu code 1 = выдан читателю',
          any(v['code'] == '1' and 'читател' in v['label'] for v in ste_vals))

    # values are sorted by seed order
    check('vd.mnu sorted by seed order', [v['code'] for v in vd_vals][:2] == ['KN', '05'])

    # INSTITUTION vocab present but EMPTY
    kv = st.get_vocabulary('kv.mnu')
    check('institution vocab kv.mnu present', kv is not None and kv['kind'] == 'institution')
    check('institution vocab kv.mnu empty seed_version', kv['seed_version'] is None)
    check('institution vocab kv.mnu has NO values', st.vocabulary_values('kv.mnu') == [])
    check('institution vocab mhr.mnu present',
          st.get_vocabulary('mhr.mnu') is not None)

    # idempotent re-seed: no duplicates, no raise, counts unchanged
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    check('re-seed idempotent (vd.mnu value count stable)',
          len(st.vocabulary_values('vd.mnu')) == len(seed_data.SYSTEM_VOCABS['vd.mnu']['values']))

    # a library CUSTOM value survives re-seed (origin not downgraded)
    st.upsert_vocabulary_value('kv.mnu', 'AB', 'Абонемент', 0, 'custom')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    kv_vals = st.vocabulary_values('kv.mnu')
    check('custom institution value survives re-seed',
          len(kv_vals) == 1 and kv_vals[0]['origin'] == 'custom')

    # tree import (parse_tre -> import_tree -> classification_nodes)
    nodes = _mnu.parse_tre('Root\n.Child\n..Leaf\n')
    seed_vocab.import_tree(st, 'spec.tre', nodes)
    stored = st.classification_nodes('spec.tre')
    check('tree import stores nodes', len(stored) == 3)
    leaf = [n for n in stored if n['code'] == 'Leaf'][0]
    check('tree import materializes path', leaf['path'] == 'Root.Child.Leaf')
    check('tree import sets parent code', leaf['parent'] == 'Child')


# --------------------------------------------------------------------------- #
# 3. PostgreSQL — provision -> seeded; isolation; idempotent re-provision.
# --------------------------------------------------------------------------- #
A_SLUG, B_SLUG = 'seed_a', 'seed_b'


def pg_reachable(dsn):
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return False
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.close()
        return True
    except Exception as e:
        print('-- seeding PG suite SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return False


def pg_checks(dsn):
    print('-- seeding: postgres', dsn.rsplit('@', 1)[-1])
    from access import pgstore

    # clean slate
    pgstore.deprovision_tenant(A_SLUG, dsn)
    pgstore.deprovision_tenant(B_SLUG, dsn)

    # provision_tenant runs seed_vocabularies internally
    sa = pgstore.provision_tenant(A_SLUG, 'Seed A', 'публичная', dsn)
    sb = pgstore.provision_tenant(B_SLUG, 'Seed B', 'школьная', dsn)

    # --- system vocabs present & populated in the tenant schema ---
    vd = sa.get_vocabulary('vd.mnu')
    check('PG: system vd.mnu seeded', vd is not None and vd['kind'] == 'system')
    check('PG: vd.mnu has seed_version', vd['seed_version'] == seed_data.SEED_VERSION)
    check('PG: vd.mnu populated from catalog',
          len(sa.vocabulary_values('vd.mnu')) == len(seed_data.SYSTEM_VOCABS['vd.mnu']['values']))
    check('PG: ste.mnu full (14)', len(sa.vocabulary_values('ste.mnu')) == 14)
    check('PG: reservstatus.mnu full (5)', len(sa.vocabulary_values('reservstatus.mnu')) == 5)

    # --- institution vocabs present & EMPTY ---
    kv = sa.get_vocabulary('kv.mnu')
    check('PG: institution kv.mnu present', kv is not None and kv['kind'] == 'institution')
    check('PG: institution kv.mnu empty', sa.vocabulary_values('kv.mnu') == []
          and kv['seed_version'] is None)

    # --- per-tenant ISOLATION: edit A's vocab, B never sees it ---
    sa.upsert_vocabulary_value('kv.mnu', 'AB', 'Абонемент (A only)', 0, 'custom')
    a_kv = sa.vocabulary_values('kv.mnu')
    b_kv = sb.vocabulary_values('kv.mnu')
    check('PG: A sees its own kv edit', any(v['code'] == 'AB' for v in a_kv))
    check('PG: B does NOT see A kv edit (isolation)', b_kv == [])
    # And a system-vocab edit in A is invisible to B too
    sa.upsert_vocabulary_value('vd.mnu', 'KN', 'KN-renamed-in-A', 0, 'custom')
    b_kn = [v for v in sb.vocabulary_values('vd.mnu') if v['code'] == 'KN']
    check('PG: B keeps original KN label (isolation)',
          b_kn and b_kn[0]['label'] == 'Книги в целом')

    # --- re-provision is idempotent: counts stable, custom edit preserved ---
    before = len(sa.vocabulary_values('vd.mnu'))
    sa2 = pgstore.provision_tenant(A_SLUG, 'Seed A', 'публичная', dsn)
    after = len(sa2.vocabulary_values('vd.mnu'))
    check('PG: re-provision stable vd.mnu count', before == after)
    a_kv2 = sa2.vocabulary_values('kv.mnu')
    check('PG: re-provision preserves custom kv value',
          len(a_kv2) == 1 and a_kv2[0]['origin'] == 'custom')

    # cleanup
    pgstore.deprovision_tenant(A_SLUG, dsn)
    pgstore.deprovision_tenant(B_SLUG, dsn)


def run_pg():
    from access import pgstore
    dsn = pgstore.default_pg_dsn()
    if not pg_reachable(dsn):
        return
    pg_checks(dsn)


def main():
    parser_checks()
    sqlite_seed_checks()
    run_pg()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
