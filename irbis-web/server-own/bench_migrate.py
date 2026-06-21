#!/usr/bin/env python3
"""Migration benchmark harness (ASCII only; Cyrillic lives in the .md report).

Measures wall-clock and throughput of migrating IBIS -> our own store via the
IRBIS adapter, with an instrumented breakdown of time spent:
  * READ from IRBIS  (network + protocol, connection-per-request):
        - search (K)       one-shot, amortized
        - read_record (C)  per record
        - format_record(G) per record
  * WRITE to store   (transform + upsert + FTS index/commit)

Usage:
  py bench_migrate.py [--limit N] [--store PATH] [--no-format]
  OWN_STORE_BACKEND=pg OWN_PG_DSN=... py -3.12 bench_migrate.py ...

Prints a machine-readable summary; writes nothing but the store .db (gitignored).
"""
import sys
import os
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', 'backend')))
sys.path.insert(0, HERE)
from irbis.client import IrbisClient            # noqa: E402
from pgstore import make_store                  # noqa: E402
import migrate as M                             # noqa: E402 (reuse transform/placement logic)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=6666)
    ap.add_argument('--user', default='MASTER')
    ap.add_argument('--password', default='1')
    ap.add_argument('--db', default='IBIS')
    ap.add_argument('--name', default='Electronic catalog')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--store', default=os.path.join(HERE, 'bench.db'))
    ap.add_argument('--no-format', action='store_true',
                    help='skip the per-record format_record (G) call')
    a = ap.parse_args()

    backend = os.environ.get('OWN_STORE_BACKEND', 'sqlite').lower()

    c = IrbisClient(a.host, a.port, 'A')
    t_conn0 = time.perf_counter()
    r = c.connect(a.user, a.password)
    t_conn = time.perf_counter() - t_conn0
    if r.return_code != 0:
        print('connect failed rc=%s' % r.return_code)
        return

    os.environ.setdefault('OWN_DB', a.store)
    t_store0 = time.perf_counter()
    st = make_store()
    st.add_db(a.db, a.name, 1)
    slots = st.seed_storage()
    t_store_init = time.perf_counter() - t_store0
    cells, post, ret = slots['cells'], slots['postamat'], slots['return']

    # ---- READ: search (one round trip) ----
    t_s0 = time.perf_counter()
    count, mfns = c.search(a.db, '"I=$"')
    t_search = time.perf_counter() - t_s0
    if a.limit:
        mfns = mfns[:a.limit]
    n = len(mfns)
    print('backend=%s db=%s search_count=%d migrating=%d' % (backend, a.db, count, n))

    t_read_rec = 0.0     # C command
    t_format = 0.0       # G command
    t_write = 0.0        # transform + upsert + place_holding (store side)
    done = 0
    errors = 0

    t_all0 = time.perf_counter()
    for i, mfn in enumerate(mfns):
        try:
            tr0 = time.perf_counter()
            rec = c.read_record(a.db, mfn)
            t_read_rec += time.perf_counter() - tr0

            brief = ''
            if not a.no_format:
                tf0 = time.perf_counter()
                try:
                    brief = c.format_record(a.db, mfn, '@brief')
                except Exception:
                    brief = ''
                t_format += time.perf_counter() - tf0

            tw0 = time.perf_counter()
            item, kw, cover = M.transform(rec)
            if not brief:
                brief = '%s%s%s' % (item['author'] + '. ' if item['author'] else '', item['title'],
                                    '. ' + item['year'] if item['year'] else '')
            st.upsert(a.db, mfn, item, brief, rec['fields'], cover, kw)
            inv = '%s-%06d' % (a.db, mfn)
            rfid = 'RFID%08X' % (mfn * 2654435761 & 0xFFFFFFFF)
            if post and i % 17 == 5:
                st.place_holding(a.db, mfn, inv, 'hold', post[i % len(post)], rfid)
            elif ret and i % 23 == 7:
                st.place_holding(a.db, mfn, inv, 'returned', ret[i % len(ret)], rfid)
            elif i % 11 == 3:
                st.place_holding(a.db, mfn, inv, 'issued', None, rfid)
            elif cells:
                st.place_holding(a.db, mfn, inv, 'available', cells[i % len(cells)], rfid)
            t_write += time.perf_counter() - tw0
            done += 1
        except Exception as e:
            errors += 1
            sys.stderr.write('skip MFN %s: %s\n' % (mfn, e))
    t_all = time.perf_counter() - t_all0
    c.disconnect()

    t_read_total = t_search + t_read_rec + t_format
    rps = done / t_all if t_all else 0.0
    print('--- RESULTS ---')
    print('records_done=%d errors=%d' % (done, errors))
    print('connect_s=%.4f store_init_s=%.4f' % (t_conn, t_store_init))
    print('loop_wall_s=%.4f records_per_sec=%.2f' % (t_all, rps))
    print('read_total_s=%.4f  (search=%.4f read_record_C=%.4f format_G=%.4f)'
          % (t_read_total, t_search, t_read_rec, t_format))
    print('write_total_s=%.4f' % t_write)
    if done:
        print('per_record_ms: read_record_C=%.3f format_G=%.3f write=%.3f total_loop=%.3f'
              % (1000 * t_read_rec / done, 1000 * t_format / done,
                 1000 * t_write / done, 1000 * t_all / done))
    pct_read = 100 * t_read_total / t_all if t_all else 0
    pct_write = 100 * t_write / t_all if t_all else 0
    print('split: read=%.1f%% write=%.1f%% (of loop wall)' % (pct_read, pct_write))
    print('store_count=%d' % st.count(a.db))


if __name__ == '__main__':
    main()
