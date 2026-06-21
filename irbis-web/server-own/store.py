#!/usr/bin/env python3
"""Own-server store — sqlite + FTS5. Holds bibliographic records migrated from IRBIS
(via the adapter) in our own model, and answers the same API contract (search/record/...).
Dev = sqlite (ADR-004 pattern); prod target = PostgreSQL (JSONB + tsvector + pg_trgm)."""
import sqlite3
import json
import re
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS rec(
  db TEXT NOT NULL, mfn INTEGER NOT NULL,
  title TEXT, author TEXT, year TEXT, doctype TEXT,
  availability TEXT, has_cover INTEGER DEFAULT 0, cover BLOB,
  brief TEXT, fields TEXT,
  PRIMARY KEY(db, mfn)
);
CREATE TABLE IF NOT EXISTS dbs(code TEXT PRIMARY KEY, name TEXT, public INTEGER DEFAULT 1);
CREATE VIRTUAL TABLE IF NOT EXISTS rec_fts USING fts5(
  db UNINDEXED, mfn UNINDEXED, title, author, keywords, doctype, tokenize='unicode61'
);
-- Иерархия размещения: здание→этаж→помещение→стеллаж→полка→ячейка (+постамат/станция→слоты).
-- Число ячеек на полке РАЗНОЕ (зависит от размера книг). В ИРБИС такого нет.
CREATE TABLE IF NOT EXISTS location(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id INTEGER, kind TEXT, code TEXT, name TEXT, size TEXT, address TEXT,
  gx REAL, gy REAL, gw REAL, gh REAL          -- геометрия для плана помещения (top-down)
);
CREATE INDEX IF NOT EXISTS loc_parent ON location(parent_id);
-- Экземпляр живёт в листовой локации (ячейка/слот) либо нигде (на руках).
CREATE TABLE IF NOT EXISTS holding(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  db TEXT NOT NULL, mfn INTEGER NOT NULL,
  inv_no TEXT, status TEXT, location_id INTEGER, rfid TEXT,
  UNIQUE(db, inv_no)
);
CREATE INDEX IF NOT EXISTS holding_rec ON holding(db, mfn);
CREATE INDEX IF NOT EXISTS holding_loc ON holding(location_id);
"""

# Демо-конфиг структуры хранения. shelves = список «число ячеек на каждой полке стеллажа»
# (разное — под размер книг). machines — системы выдачи/приёма (постамат, станция).
STORAGE = {
    'buildings': [
        {'code': 'Главное здание', 'address': 'СПб, пл. Островского, 6', 'floors': [
            {'code': '1', 'rooms': [
                {'code': 'Зал А', 'racks': 3, 'shelves': [12, 12, 8, 6]},
                {'code': 'Зал Б', 'racks': 2, 'shelves': [10, 10, 6]},
            ]},
            {'code': '2', 'rooms': [
                {'code': 'Основное хранилище', 'racks': 5, 'shelves': [14, 14, 12, 10, 8]},
            ]},
        ]},
        {'code': 'Филиал на Фонтанке', 'address': 'наб. Фонтанки, 41', 'floors': [
            {'code': '1', 'rooms': [{'code': 'Абонемент', 'racks': 2, 'shelves': [8, 8, 6]}]},
        ]},
    ],
    'machines': [
        {'kind': 'postamat', 'code': 'Постамат выдачи', 'slots': 18},
        {'kind': 'return', 'code': 'Станция книгоприёма', 'slots': 6},
    ],
}
KIND_RU = {'building': 'Здание', 'floor': 'Этаж', 'room': 'Помещение', 'rack': 'Стеллаж',
           'shelf': 'Полка', 'cell': 'Ячейка', 'postamat': 'Постамат', 'return': 'Книгоприём', 'slot': 'Слот'}
CELL_SIZES = ['L', 'L', 'M', 'M', 'S']
# Геометрия плана помещения (условные единицы): стеллаж — длинный прямоугольник, ряды с проходами.
RACK_W, RACK_H, COL_GAP, AISLE, MARGIN, PER_ROW = 70, 26, 18, 34, 26, 4


def room_geometry(nracks):
    """Вернуть (room_w, room_h, [(gx,gy,gw,gh) на стеллаж])."""
    racks = []
    for i in range(nracks):
        col, row = i % PER_ROW, i // PER_ROW
        racks.append((MARGIN + col * (RACK_W + COL_GAP), MARGIN + row * (RACK_H + AISLE), RACK_W, RACK_H))
    cols = min(PER_ROW, nracks) or 1
    rows = (nracks + PER_ROW - 1) // PER_ROW or 1
    return (MARGIN * 2 + cols * (RACK_W + COL_GAP) - COL_GAP,
            MARGIN * 2 + rows * (RACK_H + AISLE) - AISLE + 16, racks)


class OwnStore:
    def __init__(self, path):
        self.path = path
        self._local = threading.local()
        self._conn().executescript(SCHEMA)

    def _conn(self):
        c = getattr(self._local, 'c', None)
        if c is None:
            c = sqlite3.connect(self.path)
            c.row_factory = sqlite3.Row
            self._local.c = c
        return c

    # ---- write (migration) ----
    def add_db(self, code, name, public=1):
        c = self._conn()
        c.execute("INSERT OR REPLACE INTO dbs(code,name,public) VALUES(?,?,?)", (code, name, public))
        c.commit()

    def upsert(self, db, mfn, item, brief, fields, cover, keywords):
        c = self._conn()
        c.execute("""INSERT OR REPLACE INTO rec(db,mfn,title,author,year,doctype,availability,has_cover,cover,brief,fields)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (db, mfn, item.get('title'), item.get('author'), item.get('year'), item.get('docType'),
                   item.get('availability'), 1 if cover else 0, cover, brief, json.dumps(fields, ensure_ascii=False)))
        c.execute("DELETE FROM rec_fts WHERE db=? AND mfn=?", (db, mfn))
        c.execute("INSERT INTO rec_fts(db,mfn,title,author,keywords,doctype) VALUES(?,?,?,?,?,?)",
                  (db, mfn, item.get('title') or '', item.get('author') or '', keywords or '', item.get('docType') or ''))
        c.commit()

    # ---- read (API) ----
    def databases(self):
        return [dict(r) for r in self._conn().execute("SELECT code,name,public FROM dbs ORDER BY code")]

    def count(self, db):
        r = self._conn().execute("SELECT count(*) n FROM rec WHERE db=?", (db,)).fetchone()
        return r['n'] if r else 0

    @staticmethod
    def _clean(s):
        return ' '.join(re.sub(r'[^0-9A-Za-zА-Яа-яЁё\-\s]', ' ', s or '').split())

    def _match(self, prefix, q):
        q = self._clean(q)
        if not q:
            return None
        col = {'A': 'author', 'T': 'title', 'V': 'doctype'}.get((prefix or 'K').upper())
        terms = [t + '*' for t in q.split()]
        if col:
            return ' '.join('%s : %s' % (col, t) for t in terms)
        return ' '.join(terms)

    def _match_expr(self, expr):
        pairs = re.findall(r'"([A-Za-z]+)=([^"]+)"', expr)
        op = ' OR ' if '+' in expr else ' AND '
        parts = []
        for p, v in pairs:
            col = {'A': 'author', 'T': 'title', 'V': 'doctype'}.get(p.upper())
            terms = [t + '*' for t in self._clean(v.replace('$', '')).split()]
            if not terms:
                continue
            sub = ' '.join(('%s : %s' % (col, t)) if col else t for t in terms)
            parts.append('(' + sub + ')')
        if not parts:
            return None
        return '(' + op.join(parts) + ')' if len(parts) > 1 else parts[0]

    def search(self, db, prefix, q, expr, page, size):
        c = self._conn()
        m = self._match_expr(expr) if expr else self._match(prefix, q)
        if not m:
            return 0, []
        try:
            total = c.execute("SELECT count(*) n FROM rec_fts WHERE db=? AND rec_fts MATCH ?", (db, m)).fetchone()['n']
            rows = c.execute("""SELECT r.mfn,r.title,r.author,r.year,r.doctype,r.availability,r.has_cover
                                FROM rec r WHERE r.db=? AND r.mfn IN
                                  (SELECT mfn FROM rec_fts WHERE db=? AND rec_fts MATCH ?)
                                ORDER BY r.mfn LIMIT ? OFFSET ?""",
                             (db, db, m, size, (page - 1) * size)).fetchall()
        except sqlite3.OperationalError:
            return 0, []
        items = [{'mfn': r['mfn'], 'title': r['title'], 'author': r['author'], 'year': r['year'],
                  'docType': r['doctype'], 'availability': r['availability'], 'hasCover': bool(r['has_cover'])}
                 for r in rows]
        return total, items

    def terms(self, db, start, count):
        c = self._conn()
        m = re.match(r'([A-Za-z]+)=(.*)', start or '')
        prefix = (m.group(1) if m else 'K').upper()
        part = self._clean(m.group(2) if m else (start or ''))
        col = {'A': 'author', 'T': 'title'}.get(prefix, 'title')
        rows = c.execute("SELECT DISTINCT %s v FROM rec WHERE db=? AND upper(%s) LIKE ? ORDER BY v LIMIT ?"
                         % (col, col), (db, part.upper() + '%', count)).fetchall()
        return [{'count': 1, 'term': prefix + '=' + (r['v'] or '')} for r in rows if r['v']]

    def record(self, db, mfn):
        r = self._conn().execute("SELECT brief,has_cover,fields FROM rec WHERE db=? AND mfn=?", (db, mfn)).fetchone()
        if not r:
            return None
        return {'db': db, 'mfn': mfn, 'brief': r['brief'], 'hasCover': bool(r['has_cover']),
                'fields': json.loads(r['fields'] or '[]'), 'holdings': self.holdings(db, mfn)}

    def cover(self, db, mfn):
        r = self._conn().execute("SELECT cover FROM rec WHERE db=? AND mfn=?", (db, mfn)).fetchone()
        return r['cover'] if r and r['cover'] else None

    # ---- размещение: иерархия локаций + экземпляры ----
    def add_location(self, parent_id, kind, code, name=None, size=None, address=None,
                     gx=None, gy=None, gw=None, gh=None):
        c = self._conn()
        cur = c.execute("INSERT INTO location(parent_id,kind,code,name,size,address,gx,gy,gw,gh)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (parent_id, kind, code, name, size, address, gx, gy, gw, gh))
        c.commit()
        return cur.lastrowid

    def seed_storage(self, config=None):
        """Построить дерево локаций (однократно). Вернуть листья для размещения экземпляров."""
        config = config or STORAGE
        if self._conn().execute("SELECT count(*) n FROM location").fetchone()['n'] == 0:
            for b in config['buildings']:
                bid = self.add_location(None, 'building', b['code'], address=b.get('address'))
                for fl in b['floors']:
                    fid = self.add_location(bid, 'floor', fl['code'])
                    for rm in fl['rooms']:
                        rw, rh, rack_geom = room_geometry(rm['racks'])
                        rid = self.add_location(fid, 'room', rm['code'], gx=0, gy=0, gw=rw, gh=rh)
                        for ri in range(1, rm['racks'] + 1):
                            gx, gy, gw, gh = rack_geom[ri - 1]
                            rkid = self.add_location(rid, 'rack', '%02d' % ri, gx=gx, gy=gy, gw=gw, gh=gh)
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
        c = self._conn()
        sub = lambda k: [r['id'] for r in c.execute(
            "SELECT s.id FROM location s JOIN location m ON s.parent_id=m.id WHERE m.kind=? ORDER BY s.id", (k,))]
        return {'cells': [r['id'] for r in c.execute("SELECT id FROM location WHERE kind='cell' ORDER BY id")],
                'postamat': sub('postamat'), 'return': sub('return')}

    def place_holding(self, db, mfn, inv_no, status, location_id, rfid):
        c = self._conn()
        c.execute("INSERT OR REPLACE INTO holding(db,mfn,inv_no,status,location_id,rfid) VALUES(?,?,?,?,?,?)",
                  (db, mfn, inv_no, status, location_id, rfid))
        c.commit()

    # back-compat alias (older callers)
    def add_holding(self, db, mfn, inv_no, status, location_id, rfid):
        self.place_holding(db, mfn, inv_no, status, location_id, rfid)

    def _loc_index(self):
        return {r['id']: dict(r) for r in self._conn().execute(
            "SELECT id,parent_id,kind,code,name,address FROM location")}

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
        for r in self._conn().execute(
                "SELECT inv_no,status,location_id,rfid FROM holding WHERE db=? AND mfn=? ORDER BY inv_no", (db, mfn)):
            path = self.location_path(r['location_id'], idx) if r['location_id'] else []
            addr = ' / '.join('%s %s' % (KIND_RU.get(p['kind'], p['kind']), p['code']) for p in path)
            out.append({'inv_no': r['inv_no'], 'status': r['status'], 'rfid': r['rfid'],
                        'location': addr, 'cell': path[-1]['code'] if path else '', 'path': path})
        return out

    def count_holdings(self, db):
        r = self._conn().execute("SELECT count(*) n FROM holding WHERE db=?", (db,)).fetchone()
        return r['n'] if r else 0

    def storage_tree(self, db=None):
        """Полное дерево размещения с геометрией и занятостью (для карты/плана помещения)."""
        c = self._conn()
        locs = [dict(r) for r in c.execute(
            "SELECT id,parent_id,kind,code,name,address,size,gx,gy,gw,gh FROM location ORDER BY id")]
        children = {}
        for loc in locs:
            children.setdefault(loc['parent_id'], []).append(loc)
        occ = {}
        for r in c.execute("""SELECT h.location_id lid, h.status, h.inv_no, h.mfn, rec.title
                              FROM holding h LEFT JOIN rec ON rec.db=h.db AND rec.mfn=h.mfn
                              WHERE h.location_id IS NOT NULL"""):
            occ[r['lid']] = {'status': r['status'], 'inv': r['inv_no'], 'mfn': r['mfn'], 'title': r['title']}

        def build(node):
            n = {'id': node['id'], 'kind': node['kind'], 'code': node['code'], 'name': node['name'],
                 'address': node['address'], 'size': node['size'],
                 'gx': node['gx'], 'gy': node['gy'], 'gw': node['gw'], 'gh': node['gh']}
            if node['kind'] in ('cell', 'slot'):
                o = occ.get(node['id'])
                n['occupied'] = bool(o)
                if o:
                    n.update({'status': o['status'], 'inv': o['inv'], 'mfn': o['mfn'], 'title': o['title']})
            else:
                n['children'] = [build(k) for k in children.get(node['id'], [])]
                tot = on = 0
                for k in n['children']:
                    if k['kind'] in ('cell', 'slot'):
                        tot += 1
                        on += 1 if k.get('occupied') else 0
                    else:
                        tot += k.get('cellsTotal', 0)
                        on += k.get('cellsOccupied', 0)
                n['cellsTotal'], n['cellsOccupied'] = tot, on
            return n
        return [build(r) for r in children.get(None, [])]

    # ---- write (cataloging on OUR server) ----
    def next_mfn(self, db):
        r = self._conn().execute("SELECT max(mfn) m FROM rec WHERE db=?", (db,)).fetchone()
        return (r['m'] or 0) + 1

    def save(self, db, mfn, posted_fields):
        fields = fields_from_posted(posted_fields)
        item, keywords, brief = item_from_fields(fields)
        if not mfn:
            mfn = self.next_mfn(db)
        self.upsert(db, mfn, item, brief, fields, None, keywords)
        return mfn


def _parse_subfields(value):
    if '^' not in value:
        return value, {}
    parts = value.split('^')
    subs = {}
    for p in parts[1:]:
        if p:
            subs[p[0]] = p[1:]
    return parts[0], subs


def fields_from_posted(posted):
    """[{tag, value}] (value carries ^subfields) -> [FieldVal]."""
    out = []
    for f in posted or []:
        tag = str(f.get('tag', '')).strip()
        val = (f.get('value') or '').strip()
        if not tag or not val:
            continue
        head, subs = _parse_subfields(val)
        out.append({'tag': tag, 'value': val, 'text': head, 'subfields': subs})
    return out


def item_from_fields(fields):
    def F(tag):
        return next((f for f in fields if f['tag'] == tag), None)

    def Fall(tag):
        return [f for f in fields if f['tag'] == tag]

    def sf(f, c):
        if not f:
            return ''
        d = f['subfields']
        return d.get(c) or d.get(c.upper()) or d.get(c.lower()) or ''

    title = sf(F('200'), 'A')
    au = F('700')
    author = (sf(au, 'A') + (', ' + sf(au, 'G') if sf(au, 'G') else '')).strip(', ') if au else ''
    author = author or sf(F('200'), 'F')
    year = sf(F('210'), 'D')
    doctype = sf(F('900'), 'T') or sf(F('900'), 'B')
    avail = 'unknown'
    hold = Fall('910')
    if hold:
        st = sf(hold[0], 'A')
        avail = 'available' if st in ('0', '') else 'issued'
    keywords = ' '.join([title, author] + [sf(f, 'A') for f in Fall('606')])
    item = {'title': title or 'без заглавия', 'author': author, 'year': year,
            'docType': doctype, 'availability': avail}
    brief = '%s%s%s' % (author + '. ' if author else '', title, '. ' + year if year else '')
    return item, keywords, brief
