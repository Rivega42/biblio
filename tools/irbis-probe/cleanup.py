#!/usr/bin/env python3
# One-off: logically delete leftover PROHOD_B test records in scratch DB WORK.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient

DELIM = '\x1f\x1e'

def main():
    c = IrbisClient(workstation='A')
    c.connect('MASTER', '1')
    db = 'WORK'
    for mfn in range(1, c.max_mfn(db)):
        fields, rr = c.read_record(db, mfn)
        if rr.return_code != 0:
            continue
        is_test = any('PROHOD_B_TEST' in v for _, v in fields)
        if is_test:
            rec = DELIM.join(['%d#1' % mfn, '0#1', '920#SPEC', '907#^Cprobe'])
            r = c._execute('D', [db, '0', '1', rec])
            print('deleted test MFN %d -> code %s' % (mfn, r.return_code))
    c.disconnect()
    print('cleanup done')

if __name__ == '__main__':
    main()
