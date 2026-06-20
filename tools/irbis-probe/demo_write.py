#!/usr/bin/env python3
# Demo: SAFE write proof into scratch DB 'WORK' (create -> read back -> logically delete).
# Uses the empirically-confirmed update format. Does NOT touch the public catalog.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient

DELIM = '\x1f\x1e'   # IRBIS record field delimiter on the wire

def encode_record(mfn, status, version, fields):
    lines = ['%d#%d' % (mfn, status), '0#%d' % version] + ['%s#%s' % (t, v) for t, v in fields]
    return DELIM.join(lines)

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_write_results.txt'), 'w', encoding='utf-8')
    def p(*a): print(*a, file=out)

    c = IrbisClient(workstation='A')
    r = c.connect('MASTER', '1')
    p('CONNECT: code=%s' % r.return_code)
    db = 'WORK'
    p('MAXMFN %s before = %s' % (db, c.max_mfn(db)))

    # 1) CREATE new record (mfn=0 -> server assigns)
    rec = encode_record(0, 0, 0, [('920', 'SPEC'),
                                  ('200', '^APROHOD_B_TEST_DELETE_ME'),
                                  ('907', '^Cprobe^A20260620')])
    up = c._execute('D', [db, '0', '1', rec])   # UPDATE: db, lock, actualize, record
    p('\nCREATE update: return_code=%s' % up.return_code)
    p('--- raw update response (first 400) ---')
    p(up.raw.decode('utf-8', 'replace')[:400])

    # assigned MFN is echoed in the update response: data[0] = "<mfn>#<status>"
    new_mfn = None
    if up.data and '#' in up.data[0] and up.data[0].split('#')[0].isdigit():
        new_mfn = int(up.data[0].split('#')[0])
    p('assigned new MFN (from update response) = %s' % new_mfn)
    if not new_mfn:
        new_mfn = 1

    # 2) READ BACK to confirm the write
    fields, rr = c.read_record(db, new_mfn)
    p('\nREAD-BACK MFN %s: code=%s' % (new_mfn, rr.return_code))
    for t, v in fields:
        p('  %-5s | %s' % (t, v[:80]))

    # 3) LOGICALLY DELETE the test record (status bit 1 = logically deleted)
    del_rec = encode_record(int(new_mfn), 1, 1, [('920', 'SPEC'),
                                                 ('200', '^APROHOD_B_TEST_DELETE_ME'),
                                                 ('907', '^Cprobe')])
    dr = c._execute('D', [db, '0', '1', del_rec])
    p('\nLOGICAL DELETE update: return_code=%s' % dr.return_code)
    fields2, rr2 = c.read_record(db, new_mfn)
    p('READ after delete: code=%s (REC_DELETE/negative => deleted)' % rr2.return_code)

    p('\nMAXMFN %s after = %s' % (db, c.max_mfn(db)))
    p('DISCONNECT: code=%s' % (c.disconnect().return_code))
    out.close()

if __name__ == '__main__':
    main()
