#!/usr/bin/env python3
# Probe how the server exposes the list of databases (dbnam menu / pathcodes). Read-only.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe_dblist_results.txt'), 'w', encoding='utf-8')
    def p(*a): print(*a, file=out)
    def read_file(c, spec):
        r = c._execute('L', [spec])
        segs = r.raw.decode('latin1').split('\r\n')
        content = '\r\n'.join(segs[10:]).encode('latin1')
        return content.decode('cp1251', 'replace').replace('\x1f\x1e', '\n').strip()

    c = IrbisClient(workstation='A')
    c.connect('MASTER', '1')
    # dbnam menu candidates: file names from the connect INI (dbnam1.mnu catalog,
    # dbname_IC_wn.mnu web) across pathcodes (0 system, 1 data, 2 db dir).
    files = ['dbnam.mnu', 'dbnam1.mnu', 'dbnam2.mnu', 'dbname_IC_wn.mnu', 'dbnam_ic_wn.mnu']
    dbs = ['&', 'IBIS', 'RUS']
    specs = ['%d.%s.%s' % (pc, db, f) for f in files for pc in (0, 1, 2) for db in dbs]
    for spec in specs:
        try:
            txt = read_file(c, spec)
        except Exception as e:
            txt = 'ERR ' + str(e)
        if not txt:
            continue
        p('=== %s : %d chars ===' % (spec, len(txt)))
        if txt:
            for line in txt.splitlines()[:20]:
                p('   ' + line)
    c.disconnect()
    out.close()

if __name__ == '__main__':
    main()
