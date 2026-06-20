#!/usr/bin/env python3
# Demo: connect + search + read fields + render (server PFT). Read-only.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from irbis_client import IrbisClient

def main():
    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_read_results.txt'), 'w', encoding='utf-8')
    def p(*a): print(*a, file=out)

    c = IrbisClient(workstation='A')
    r = c.connect('MASTER', '1')
    p('CONNECT: return_code=%s, client_id=%s' % (r.return_code, c.client_id))
    if r.return_code != 0:
        p('connect failed; raw:', repr(r.raw[:200])); out.close(); return

    db = 'IBIS'
    p('MAXMFN %s = %s' % (db, c.max_mfn(db)))

    count, mfns, sr = c.search(db, '"V=05"', maxn=5)
    p('SEARCH V=05: count=%s, first mfns=%s' % (count, mfns[:5]))
    if not mfns:
        count, mfns, sr = c.search(db, '"I=$"', maxn=5)
        p('SEARCH I=$: count=%s, first mfns=%s' % (count, mfns[:5]))
    target = mfns[0] if mfns else 1

    p('\n=== READ record MFN %d ===' % target)
    fields, rr = c.read_record(db, target)
    p('read return_code=%s, field-lines=%d' % (rr.return_code, len(fields)))
    p('--- raw read response (first 500) ---')
    p(rr.raw.decode('utf-8', 'replace')[:500])
    p('--- parsed fields (tag # value) ---')
    for tag, val in fields[:40]:
        p('  %-6s | %s' % (tag, val[:90]))

    p('\n=== RENDER MFN %d via server PFT (@brief) ===' % target)
    fr = c.format_record(db, target, '@brief')
    p('format return_code=%s' % fr.return_code)
    p('--- raw format response (first 400) ---')
    p(fr.raw.decode('utf-8', 'replace')[:400])
    p('--- rendered (data lines) ---')
    for line in fr.data[:10]:
        p('  ' + line)

    # try another format
    fr2 = c.format_record(db, target, '@')
    p('\nRENDER @ (optimized): code=%s, data[0]=%s' % (fr2.return_code, (fr2.data[0] if fr2.data else '')[:120]))

    d = c.disconnect()
    p('\nDISCONNECT: return_code=%s' % (d.return_code if d else None))
    out.close()

if __name__ == '__main__':
    main()
