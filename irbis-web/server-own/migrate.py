#!/usr/bin/env python3
"""Migrate records from a live IRBIS database into our own store (PoC).
Uses the Prohod-B adapter (../backend/irbis) to read, transforms field/subfield ->
our model, and upserts into sqlite (server-own/own.db).

  py irbis-web/server-own/migrate.py --host 127.0.0.1 --user MASTER --password 1 --db IBIS
"""
import sys
import os
import argparse
from urllib.parse import unquote_to_bytes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', 'backend')))
sys.path.insert(0, HERE)
from irbis.client import IrbisClient            # noqa: E402
from irbis.parser import field, fields as fields_of  # noqa: E402
from store import OwnStore, cell_address          # noqa: E402


def sf(f, c):
    if not f:
        return ''
    d = f['subfields']
    return d.get(c) or d.get(c.upper()) or d.get(c.lower()) or ''


def transform(rec):
    title = sf(field(rec, '200'), 'A')
    au = field(rec, '700')
    author = (sf(au, 'A') + (', ' + sf(au, 'G') if sf(au, 'G') else '')).strip(', ') if au else ''
    author = author or sf(field(rec, '200'), 'F')
    year = sf(field(rec, '210'), 'D') or sf(field(rec, '210'), 'd')
    doctype = sf(field(rec, '900'), 'T') or sf(field(rec, '900'), 'B')
    avail = 'unknown'
    hold = fields_of(rec, '910')
    if hold:
        st = sf(hold[0], 'A')
        avail = 'available' if st in ('0', '') else 'issued'
    cover = None
    f953 = field(rec, '953')
    if f953:
        raw = f953['subfields'].get('B') or f953['subfields'].get('b')
        if raw:
            try:
                cover = unquote_to_bytes(raw)
            except Exception:
                cover = None
    keywords = ' '.join([title, author] + [sf(f, 'A') for f in fields_of(rec, '606')])
    item = {'title': title or ('MFN %d' % rec['mfn']), 'author': author, 'year': year,
            'docType': doctype, 'availability': avail}
    return item, keywords, cover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=6666)
    ap.add_argument('--user', default='MASTER')
    ap.add_argument('--password', default='1')
    ap.add_argument('--db', default='IBIS')
    ap.add_argument('--name', default='Электронный каталог')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--store', default=os.path.join(HERE, 'own.db'))
    a = ap.parse_args()

    c = IrbisClient(a.host, a.port, 'A')
    r = c.connect(a.user, a.password)
    if r.return_code != 0:
        print('connect failed: %s' % r.return_code); return
    st = OwnStore(a.store)
    st.add_db(a.db, a.name, 1)
    count, mfns = c.search(a.db, '"I=$"')
    if a.limit:
        mfns = mfns[:a.limit]
    print('migrating %d records from %s ...' % (len(mfns), a.db))
    done = 0
    for i, mfn in enumerate(mfns):
        try:
            rec = c.read_record(a.db, mfn)
            try:
                brief = c.format_record(a.db, mfn, '@brief')
            except Exception:
                brief = ''
            item, kw, cover = transform(rec)
            if not brief:
                brief = '%s%s%s' % (item['author'] + '. ' if item['author'] else '', item['title'],
                                    '. ' + item['year'] if item['year'] else '')
            st.upsert(a.db, mfn, item, brief, rec['fields'], cover, kw)
            # ячеистое хранение (наша модель): один адресуемый экземпляр на запись
            st.add_holding(a.db, mfn, '%s-%06d' % (a.db, mfn), item['availability'],
                           cell_address(i), 'RFID%08X' % (mfn * 2654435761 & 0xFFFFFFFF))
            done += 1
            if done % 50 == 0:
                print('  %d/%d' % (done, len(mfns)))
        except Exception as e:
            print('  skip MFN %s: %s' % (mfn, e))
    c.disconnect()
    print('done: %d records into %s (db %s, total %d)' % (done, a.store, a.db, st.count(a.db)))


if __name__ == '__main__':
    main()
