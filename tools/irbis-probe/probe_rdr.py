#!/usr/bin/env python3
# Check the reader DB (RDR): is there data, what is the ticket field/prefix. Read-only.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient
from collections import OrderedDict

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe_rdr_results.txt'), 'w', encoding='utf-8')
    def p(*a): print(*a, file=out)
    c = IrbisClient(workstation='A')
    c.connect('MASTER', '1')
    mm = c.max_mfn('RDR')
    p('RDR max_mfn(+1) =', mm)
    # try search by reader-identifier prefix RI= (truncated)
    for expr in ['"RI=$"', '"RG=$"']:
        try:
            res = c.search('RDR', expr, maxn=5)
            cnt, mfns = res[0], res[1]
        except Exception as e:
            cnt, mfns = 'ERR ' + str(e), []
        p('search RDR %s -> count=%s mfns=%s' % (expr, cnt, mfns[:5]))
    # real ticket values from the RI= dictionary
    rt = c._execute('H', ['RDR', 'RI=', '8'])
    p('\nRI= dictionary terms (count#term):')
    for line in rt.data[:8]:
        p('   ' + line)
    # raw fields of RDR MFN 1 (find ticket field 30, name 10/11, loans 40)
    rr = c._execute('C', ['RDR', '1', '0'])
    p('\nRDR MFN1 raw (data lines):')
    for line in rr.data[:28]:
        p('   ' + line)
    c.disconnect()
    out.close()

if __name__ == '__main__':
    main()
