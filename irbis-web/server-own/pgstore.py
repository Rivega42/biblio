#!/usr/bin/env python3
"""PostgreSQL-backed store for the own-server (prod target). Same interface as
store.OwnStore (sqlite), so app.py/migrate.py switch via env OWN_STORE_BACKEND=pg.
Search: tsvector (to_tsquery prefix) for keywords + ILIKE for author/title/doctype.
Records as JSONB, covers as bytea, holdings with cell addressing.

Driver: psycopg 3 (`pip install "psycopg[binary]"`)."""
import os
import json
import re
import threading

try:                                  # psycopg only needed for the pg backend
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except Exception:                     # sqlite mode (e.g. Python 3.14 without psycopg)
    psycopg = None

from store import STORAGE, KIND_RU, CELL_SIZES   # общий конфиг структуры хранения

DDL = """
CREATE TABLE IF NOT EXISTS rec(
  db text NOT NULL, mfn int NOT NULL,
  title text, author text, year text, doctype text,
  availability text, has_cover boolean DEFAULT false, cover bytea,
  brief text, fields jsonb, keywords text,
  search_vector tsvector,
  PRIMARY KEY(db, mfn)
);
CREATE TABLE IF NOT EXISTS dbs(code text PRIMARY KEY, name text, public boolean DEFAULT true);
CREATE TABLE IF NOT EXISTS location(
  id bigserial PRIMARY KEY, parent_id bigint, kind text, code text, name text, size text, address text
);
CREATE INDEX IF NOT EXISTS loc_parent ON location(parent_id);
CREATE TABLE IF NOT EXISTS holding(
  id bigserial PRIMARY KEY, db text NOT NULL, mfn int NOT NULL,
  inv_no text, status text, location_id bigint, rfid text, UNIQUE(db, inv_no)
);
CREATE INDEX IF NOT EXISTS rec_sv ON rec USING gin(search_vector);
CREATE INDEX IF NOT EXISTS holding_rec ON holding(db, mfn);
CREATE INDEX IF NOT EXISTS holding_loc ON holding(location_id);
"""


class PgStore:
    def __init__(self, dsn):
        self.dsn = dsn
        self.path = dsn
        self._local = threading.local()
        with self._c() as c:
            c.execute(DDL)

    def _c(self):
        conn = getattr(self._local, 'conn', None)
        if conn is None or conn.closed:
            conn = psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True)
            self._local.conn = conn
        return conn

    # ---- write ----
    def add_db(self, code, name, public=True):
        self._c().execute(
            "INSERT INTO dbs(code,name,public) VALUES(%s,%s,%s) ON CONFLICT(code) DO UPDATE SET name=EXCLUDED.name",
            (code, name, bool(public)))

    def upsert(self, db, mfn, item, brief, fields, cover, keywords):
        text_blob = ' '.join([item.get('title') or '', item.get('author') or '', keywords or ''])
        self._c().execute(
            """INSERT INTO rec(db,mfn,title,author,year,doctype,availability,has_cover,cover,brief,fields,keywords,search_vector)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_tsvector('simple', %s))
               ON CONFLICT(db,mfn) DO UPDATE SET
                 title=EXCLUDED.title, author=EXCLUDED.author, year=EXCLUDED.year, doctype=EXCLUDED.doctype,
                 availability=EXCLUDED.availability, has_cover=EXCLUDED.has_cover, cover=EXCLUDED.cover,
                 brief=EXCLUDED.brief, fields=EXCLUDED.fields, keywords=EXCLUDED.keywords, search_vector=EXCLUDED.search_vector""",
            (db, mfn, item.get('title'), item.get('author'), item.get('year'), item.get('docType'),
             item.get('availability'), bool(cover), cover, brief, Jsonb(fields), keywords, text_blob))

    # ---- read ----
    def databases(self):
        return self._c().execute("SELECT code,name,public FROM dbs ORDER BY code").fetchall()

    def count(self, db):
        return self._c().execute("SELECT count(*) n FROM rec WHERE db=%s", (db,)).fetchone()['n']

    @staticmethod
    def _clean(s):
        return ' '.join(re.sub(r'[^0-9A-Za-zА-Яа-яЁё\-\s]', ' ', s or '').split())

    def _where(self, prefix, q, expr):
        """Return (sql_condition, params) for the search."""
        if expr:
            pairs = re.findall(r'"([A-Za-z]+)=([^"]+)"', expr)
            op = ' OR ' if '+' in expr else ' AND '
            conds, params = [], []
            for p, v in pairs:
                c, pr = self._col_cond(p.upper(), self._clean(v.replace('$', '')))
                if c:
                    conds.append('(' + c + ')')
                    params += pr
            return (op.join(conds), params) if conds else (None, None)
        return self._col_cond((prefix or 'K').upper(), self._clean(q))

    def _col_cond(self, prefix, q):
        if not q:
            return None, None
        col = {'A': 'author', 'T': 'title', 'V': 'doctype'}.get(prefix)
        toks = q.split()
        if col:
            return ' AND '.join('%s ILIKE %%s' % col for _ in toks), ['%' + t + '%' for t in toks]
        tsq = ' & '.join(t + ':*' for t in toks)
        return "search_vector @@ to_tsquery('simple', %s)", [tsq]

    def search(self, db, prefix, q, expr, page, size):
        cond, params = self._where(prefix, q, expr)
        if not cond:
            return 0, []
        c = self._c()
        total = c.execute("SELECT count(*) n FROM rec WHERE db=%s AND (" + cond + ")", [db] + params).fetchone()['n']
        rows = c.execute(
            "SELECT mfn,title,author,year,doctype,availability,has_cover FROM rec WHERE db=%s AND (" + cond + ")"
            " ORDER BY mfn LIMIT %s OFFSET %s", [db] + params + [size, (page - 1) * size]).fetchall()
        items = [{'mfn': r['mfn'], 'title': r['title'], 'author': r['author'], 'year': r['year'],
                  'docType': r['doctype'], 'availability': r['availability'], 'hasCover': r['has_cover']} for r in rows]
        return total, items

    def terms(self, db, start, count):
        m = re.match(r'([A-Za-z]+)=(.*)', start or '')
        prefix = (m.group(1) if m else 'K').upper()
        part = self._clean(m.group(2) if m else (start or ''))
        col = {'A': 'author', 'T': 'title'}.get(prefix, 'title')
        rows = self._c().execute(
            "SELECT DISTINCT %s v FROM rec WHERE db=%%s AND %s ILIKE %%s ORDER BY v LIMIT %%s" % (col, col),
            (db, part + '%', count)).fetchall()
        return [{'count': 1, 'term': prefix + '=' + (r['v'] or '')} for r in rows if r['v']]

    def record(self, db, mfn):
        r = self._c().execute("SELECT brief,has_cover,fields FROM rec WHERE db=%s AND mfn=%s", (db, mfn)).fetchone()
        if not r:
            return None
        return {'db': db, 'mfn': mfn, 'brief': r['brief'], 'hasCover': r['has_cover'],
                'fields': r['fields'] or [], 'holdings': self.holdings(db, mfn)}

    def cover(self, db, mfn):
        r = self._c().execute("SELECT cover FROM rec WHERE db=%s AND mfn=%s", (db, mfn)).fetchone()
        return bytes(r['cover']) if r and r['cover'] else None

    # ---- write (cataloging) ----
    def next_mfn(self, db):
        r = self._c().execute("SELECT max(mfn) m FROM rec WHERE db=%s", (db,)).fetchone()
        return (r['m'] or 0) + 1

    def save(self, db, mfn, posted_fields):
        from store import fields_from_posted, item_from_fields
        fields = fields_from_posted(posted_fields)
        item, keywords, brief = item_from_fields(fields)
        if not mfn:
            mfn = self.next_mfn(db)
        self.upsert(db, mfn, item, brief, fields, None, keywords)
        return mfn

    # ---- размещение: иерархия локаций + экземпляры ----
    def add_location(self, parent_id, kind, code, name=None, size=None, address=None):
        return self._c().execute(
            "INSERT INTO location(parent_id,kind,code,name,size,address) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
            (parent_id, kind, code, name, size, address)).fetchone()['id']

    def seed_storage(self, config=None):
        config = config or STORAGE
        if self._c().execute("SELECT count(*) n FROM location").fetchone()['n'] == 0:
            for b in config['buildings']:
                bid = self.add_location(None, 'building', b['code'], address=b.get('address'))
                for fl in b['floors']:
                    fid = self.add_location(bid, 'floor', fl['code'])
                    for rm in fl['rooms']:
                        rid = self.add_location(fid, 'room', rm['code'])
                        for ri in range(1, rm['racks'] + 1):
                            rkid = self.add_location(rid, 'rack', '%02d' % ri)
                            for si, ncells in enumerate(rm['shelves'], start=1):
                                shid = self.add_location(rkid, 'shelf', '%d' % si)
                                for ci in range(1, ncells + 1):
                                    self.add_location(shid, 'cell', '%02d' % ci, size=CELL_SIZES[(ci - 1) % len(CELL_SIZES)])
            for m in config['machines']:
                mid = self.add_location(None, m['kind'], m['code'])
                for si in range(1, m['slots'] + 1):
                    self.add_location(mid, 'slot', '%02d' % si)
        return self.leaves()

    def leaves(self):
        c = self._c()

        def sub(k):
            return [r['id'] for r in c.execute(
                "SELECT s.id FROM location s JOIN location m ON s.parent_id=m.id WHERE m.kind=%s ORDER BY s.id", (k,)).fetchall()]
        return {'cells': [r['id'] for r in c.execute("SELECT id FROM location WHERE kind='cell' ORDER BY id").fetchall()],
                'postamat': sub('postamat'), 'return': sub('return')}

    def place_holding(self, db, mfn, inv_no, status, location_id, rfid):
        self._c().execute(
            "INSERT INTO holding(db,mfn,inv_no,status,location_id,rfid) VALUES(%s,%s,%s,%s,%s,%s)"
            " ON CONFLICT(db,inv_no) DO UPDATE SET status=EXCLUDED.status, location_id=EXCLUDED.location_id, rfid=EXCLUDED.rfid",
            (db, mfn, inv_no, status, location_id, rfid))

    def add_holding(self, db, mfn, inv_no, status, location_id, rfid):
        self.place_holding(db, mfn, inv_no, status, location_id, rfid)

    def _loc_index(self):
        return {r['id']: r for r in self._c().execute(
            "SELECT id,parent_id,kind,code,name,address FROM location").fetchall()}

    def location_path(self, loc_id, idx=None):
        idx = idx if idx is not None else self._loc_index()
        chain, cur = [], idx.get(loc_id)
        while cur:
            chain.append({'kind': cur['kind'], 'code': cur['code'], 'name': cur['name']})
            cur = idx.get(cur['parent_id'])
        chain.reverse()
        return chain

    def holdings(self, db, mfn):
        idx = self._loc_index()
        out = []
        for r in self._c().execute("SELECT inv_no,status,location_id,rfid FROM holding WHERE db=%s AND mfn=%s ORDER BY inv_no", (db, mfn)).fetchall():
            path = self.location_path(r['location_id'], idx) if r['location_id'] else []
            addr = ' / '.join('%s %s' % (KIND_RU.get(p['kind'], p['kind']), p['code']) for p in path)
            out.append({'inv_no': r['inv_no'], 'status': r['status'], 'rfid': r['rfid'],
                        'location': addr, 'cell': path[-1]['code'] if path else '', 'path': path})
        return out

    def count_holdings(self, db):
        return self._c().execute("SELECT count(*) n FROM holding WHERE db=%s", (db,)).fetchone()['n']

    def storage_tree(self, db=None):
        c = self._c()
        locs = c.execute("SELECT id,parent_id,kind,code,name,address,size FROM location ORDER BY id").fetchall()
        children = {}
        for loc in locs:
            children.setdefault(loc['parent_id'], []).append(loc)
        occ = {}
        for r in c.execute("""SELECT h.location_id lid, h.status, h.inv_no, h.mfn, rec.title
                              FROM holding h LEFT JOIN rec ON rec.db=h.db AND rec.mfn=h.mfn
                              WHERE h.location_id IS NOT NULL""").fetchall():
            occ[r['lid']] = {'status': r['status'], 'inv': r['inv_no'], 'mfn': r['mfn'], 'title': r['title']}

        def build(node):
            n = {'id': node['id'], 'kind': node['kind'], 'code': node['code'],
                 'name': node['name'], 'address': node['address'], 'size': node['size']}
            if node['kind'] in ('cell', 'slot'):
                o = occ.get(node['id'])
                n['occupied'] = bool(o)
                if o:
                    n.update({'status': o['status'], 'inv': o['inv'], 'mfn': o['mfn'], 'title': o['title']})
            else:
                n['children'] = [build(k) for k in children.get(node['id'], [])]
            return n
        return [build(r) for r in children.get(None, [])]


def make_store():
    """Factory used by app.py / migrate.py: sqlite (default) or pg via env."""
    backend = os.environ.get('OWN_STORE_BACKEND', 'sqlite').lower()
    if backend == 'pg':
        dsn = os.environ.get('OWN_PG_DSN', 'postgresql://postgres:pg@127.0.0.1:5433/irbisweb')
        return PgStore(dsn)
    from store import OwnStore
    here = os.path.dirname(os.path.abspath(__file__))
    return OwnStore(os.environ.get('OWN_DB', os.path.join(here, 'own.db')))
