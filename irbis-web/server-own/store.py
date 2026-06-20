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
"""


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
                'fields': json.loads(r['fields'] or '[]')}

    def cover(self, db, mfn):
        r = self._conn().execute("SELECT cover FROM rec WHERE db=? AND mfn=?", (db, mfn)).fetchone()
        return r['cover'] if r and r['cover'] else None
