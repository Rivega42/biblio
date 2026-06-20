#!/usr/bin/env python3
"""Smoke test: backend IRBIS layer against the live server (no HTTP). Read-only.
Proves end-to-end: SessionManager -> IrbisClient -> live :6666 -> real IBIS data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config
from irbis import SessionManager

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smoke_results.txt'),
               'w', encoding='utf-8')
    def p(*a): print(*a, file=out)

    cfg = Config()
    sm = SessionManager(cfg.irbis_host, cfg.irbis_port, cfg.workstation,
                        cfg.irbis_user, cfg.irbis_pass, cfg.timeout)
    db = cfg.db_default
    p('HEALTH: server %s:%d, version=%s, maxmfn(%s)=%s'
      % (cfg.irbis_host, cfg.irbis_port, sm.server_version(), db, sm.max_mfn(db)))

    count, mfns = sm.search(db, '"V=05"')
    p('SEARCH V=05: total=%s, first=%s' % (count, mfns[:8]))

    mfn = mfns[0] if mfns else 1
    rec = sm.read_record(db, mfn)
    p('\nREAD MFN %s: version=%s, guid=%s, fields=%d'
      % (rec['mfn'], rec['version'], rec['guid'], len(rec['fields'])))
    for f in rec['fields'][:12]:
        sub = (' subfields=' + str(f['subfields'])) if f['subfields'] else ''
        p('  %-5s | %s%s' % (f['tag'], f['value'][:70], sub))

    p('\nRENDER @brief: %s' % sm.format_record(db, mfn, '@brief'))

    p('\nTERMS (H) start "A=КОЛИСНИЧЕНКО" x6:')
    for cnt, term in sm.read_terms(db, 'A=КОЛИСНИЧЕНКО', 6):
        p('   %4d  %s' % (cnt, term))

    p('\nFILE (L) 3.IBIS.kv.mnu (menu vocabulary, first 6 lines):')
    txt = sm.read_file('3.%s.kv.mnu' % db)
    for line in txt.splitlines()[:6]:
        p('   ' + line)

    sm.close()
    p('\nOK')
    out.close()

if __name__ == '__main__':
    main()
