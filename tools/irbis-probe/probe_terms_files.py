#!/usr/bin/env python3
# Prohod B (extension): confirm TERMS ('H') and FILE/RESOURCE ('L') commands. Read-only.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe_terms_files_results.txt'),
               'w', encoding='utf-8')
    def p(*a): print(*a, file=out)

    c = IrbisClient(workstation='A')
    r = c.connect('MASTER', '1')
    p('CONNECT code=%s' % r.return_code)
    db = 'IBIS'

    # --- TERMS: 'H' = read terms forward from dictionary. Args: db, term, count ---
    for term, count in [('K=A', 12), ('A=КОЛИСНИЧЕНКО', 8), ('V=', 10)]:
        rr = c._execute('H', [db, term, str(count)])
        p('\n=== TERMS H db=%s start="%s" count=%s : ret=%s ===' % (db, term, count, rr.return_code))
        for line in rr.data[:14]:
            p('   ' + line)

    # --- FILE/RESOURCE: 'L' = read a text resource. Path spec: <pathtype>.<db>.<file> ---
    for spec in ['2.IBIS.brief.pft', '2.IBIS.dbnam.mnu', '3.IBIS.kv.mnu', '1.IBIS.IBIS.pft']:
        rr = c._execute('L', [spec])
        body = '\n'.join(rr.data) if rr.data else ''
        p('\n=== FILE L "%s" : ret=%s, bytes=%d ===' % (spec, rr.return_code, len(rr.raw)))
        p('   raw[ret-line..]: ' + repr(rr.lines[10:13]))
        p('   data head: ' + (body[:200].replace('\n', ' | ')))

    c.disconnect()
    p('\nDONE')
    out.close()

if __name__ == '__main__':
    main()
