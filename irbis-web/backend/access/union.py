#!/usr/bin/env python3
"""UNION — Сводный каталог SK (рёбра INTEGRATION_MAP 8.1–8.3).

Записи библиотек-участниц сводятся в общий каталог по сигле держателя
(902^s) с дедупликацией экземпляров и федеративным поиском. Аналог
ИРБИС-БД **SK** (Сводный Каталог), но own-store: чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в точности
как ``pay.py``/``devices.py``.

Что это
-------
  * **8.1 свод по сигле** — каждая запись библиотеки-участницы приходит со
    своей сиглой держателя (902^s) и порождает *holding* (держание) под
    одной сводной записью;
  * **8.2 дедупликация** — несколько библиотек с одним и тем же изданием
    сходятся в ОДНУ сводную запись по ключу дедупликации ``dedup_key``
    (приоритет ISBN > шифр(903) > нормализованный ``title|year``); каждая
    добавляет лишь своё holding (своя сигла);
  * **8.3 федеративный поиск** — поиск по заглавию/году отдаёт сводные
    записи со списком сигл всех держателей.

Запись ``rec`` — это НАША tag-keyed запись (как в ``catalog.py``): dict
полей, где поле — скаляр, ``{подполе: значение}`` или список такого.
Парсинг устойчив к любой из трёх форм (см. ``_field_value``).

Гранты/аудит — на слое маршрутов (``server.py`` + ``access/authz.py``);
сам домен — чистая логика над своим стором.
"""
import re
import sqlite3
import threading
import time

# Поля записи, из которых строится ключ дедупликации (приоритет сверху вниз).
FIELD_ISBN = '10'        # 10^a — ISBN
SUB_ISBN = 'a'
FIELD_SHIFR = '903'      # 903 — шифр документа (907^Z-ключ держателя)
FIELD_TITLE = '200'      # 200^a — заглавие
SUB_TITLE = 'a'
FIELD_PUBL = '210'       # 210^d — год издания
SUB_YEAR = 'd'


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS union_record (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  dedup_key  TEXT NOT NULL UNIQUE,      -- ключ свода: isbn:.. | shifr:.. | ty:..
  title      TEXT,
  year       TEXT,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS union_holding (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  union_record INTEGER NOT NULL REFERENCES union_record(id) ON DELETE CASCADE,
  sigla        TEXT NOT NULL,           -- 902^s — сигла держателя
  source_db    TEXT,                    -- БД-источник библиотеки-участницы
  source_mfn   INTEGER,                 -- MFN записи в БД-источнике
  shifr        TEXT,                    -- 903 — шифр держателя
  created_at   REAL NOT NULL,
  UNIQUE(union_record, sigla, source_mfn)
);
CREATE INDEX IF NOT EXISTS union_holding_rec_idx ON union_holding(union_record);
CREATE INDEX IF NOT EXISTS union_holding_sigla_idx ON union_holding(sigla);
CREATE INDEX IF NOT EXISTS union_record_title_idx ON union_record(title);
"""


# --------------------------------------------------------------------------- #
# Парсинг tag-keyed записи (скаляр / dict / список) — зеркало catalog._inst*.
# --------------------------------------------------------------------------- #
def _field_value(rec, field, subfield=None):
    """Первое непустое значение ``field`` (опц. подполя) из записи ``rec``.

    Поле может быть скаляром, ``{подполе: значение}`` или списком такого;
    регистр подполя нечувствителен.
    """
    raw = rec.get(field) if rec else None
    if raw is None:
        return ''
    insts = raw if isinstance(raw, list) else [raw]
    for inst in insts:
        if isinstance(inst, dict):
            if subfield is None or subfield == '':
                v = (inst.get('') or inst.get('value')
                     or ''.join(str(x) for x in inst.values()))
            else:
                v = (inst.get(subfield) or inst.get(subfield.lower())
                     or inst.get(subfield.upper()) or '')
        else:
            v = inst if (subfield is None or subfield == '') else ''
        if v:
            return str(v)
    return ''


def _norm_isbn(raw):
    """Нормализовать ISBN: оставить цифры и финальный X (контр. символ)."""
    if not raw:
        return ''
    return re.sub(r'[^0-9X]', '', str(raw).upper())


def _norm_text(raw):
    """Нормализовать текст для ключа: нижний регистр, схлопнуть пробелы."""
    return re.sub(r'\s+', ' ', str(raw or '').strip().lower())


class UnionStore:
    """Собственный sqlite-стор Сводного каталога SK (сводные записи + holdings).

    ``db_path=':memory:'`` (по умолчанию) или файл; create-on-init.
    Соединение thread-local (домашний стиль); строки — dict.
    """

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ---- сводная запись --------------------------------------------------- #
    def get_record_by_key(self, dedup_key):
        r = self._conn().execute(
            'SELECT * FROM union_record WHERE dedup_key=?',
            (dedup_key,)).fetchone()
        return dict(r) if r else None

    def get_record(self, union_id):
        r = self._conn().execute(
            'SELECT * FROM union_record WHERE id=?', (union_id,)).fetchone()
        return dict(r) if r else None

    def add_record(self, dedup_key, title, year, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO union_record(dedup_key,title,year,created_at) '
            'VALUES(?,?,?,?)', (dedup_key, title, year, created_at))
        c.commit()
        return self.get_record(cur.lastrowid)

    # ---- holding ---------------------------------------------------------- #
    def get_holding(self, union_id, sigla, source_mfn):
        r = self._conn().execute(
            'SELECT * FROM union_holding WHERE union_record=? AND sigla=? '
            'AND source_mfn IS ?', (union_id, sigla, source_mfn)).fetchone()
        return dict(r) if r else None

    def add_holding(self, union_id, sigla, source_db, source_mfn, shifr,
                    created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO union_holding(union_record,sigla,source_db,'
            'source_mfn,shifr,created_at) VALUES(?,?,?,?,?,?)',
            (union_id, sigla, source_db, source_mfn, shifr, created_at))
        c.commit()
        r = c.execute('SELECT * FROM union_holding WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def holdings(self, union_id):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM union_holding WHERE union_record=? ORDER BY id',
            (union_id,)).fetchall()]

    def siglas(self, union_id):
        rows = self._conn().execute(
            'SELECT DISTINCT sigla FROM union_holding WHERE union_record=? '
            'ORDER BY sigla', (union_id,)).fetchall()
        return [r['sigla'] for r in rows]

    def search_records(self, title_like=None, year=None):
        # NB: SQLite-овский lower()/LIKE регистронезависим только для ASCII —
        # для кириллицы фильтруем подстроку заглавия в Python.
        q = 'SELECT * FROM union_record WHERE 1=1'
        args = []
        if year:
            q += ' AND year=?'
            args.append(str(year))
        q += ' ORDER BY id'
        rows = [dict(r) for r in self._conn().execute(q, args).fetchall()]
        if title_like:
            needle = title_like.lower()
            rows = [r for r in rows if needle in (r['title'] or '').lower()]
        return rows

    def counts(self):
        rec = self._conn().execute(
            'SELECT COUNT(*) AS n FROM union_record').fetchone()['n']
        hold = self._conn().execute(
            'SELECT COUNT(*) AS n FROM union_holding').fetchone()['n']
        return int(rec), int(hold)


class UnionCatalog:
    """Операции Сводного каталога SK над :class:`UnionStore`.

    Свод по сигле (902^s) с дедупликацией (приоритет ISBN > шифр(903) >
    нормализованный ``title|year``) и федеративным поиском. ``now``
    инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or UnionStore(':memory:')
        self._now = now or time.time

    # -- ключ дедупликации -------------------------------------------------- #
    def dedup_key(self, rec):
        """Ключ свода из записи: ISBN (10^a) > шифр (903) > ``title|year``.

        ISBN нормализуется (цифры/X); шифр — как есть (trim); fallback —
        нормализованные заглавие+год. Возвращает строку с типовым префиксом.
        """
        isbn = _norm_isbn(_field_value(rec, FIELD_ISBN, SUB_ISBN))
        if isbn:
            return 'isbn:' + isbn
        shifr = _field_value(rec, FIELD_SHIFR).strip()
        if shifr:
            return 'shifr:' + shifr
        title = _norm_text(_field_value(rec, FIELD_TITLE, SUB_TITLE))
        year = _norm_text(_field_value(rec, FIELD_PUBL, SUB_YEAR))
        return 'ty:' + title + '|' + year

    # -- свод записи (8.1 + 8.2) ------------------------------------------- #
    def ingest(self, rec, sigla, source_db=None, source_mfn=None):
        """Свести запись библиотеки-участницы в сводный каталог.

        Найти/создать сводную запись по :meth:`dedup_key`, добавить holding
        с сиглой держателя (902^s). Идемпотентно: повтор ``(sigla,
        source_mfn)`` под той же сводной не задваивает holding.

        Возвращает ``{'union_id', 'dedup_key', 'merged': bool}`` — ``merged``
        True, если присоединились к УЖЕ существовавшей сводной записи.
        """
        key = self.dedup_key(rec)
        title = _field_value(rec, FIELD_TITLE, SUB_TITLE)
        year = _field_value(rec, FIELD_PUBL, SUB_YEAR)
        shifr = _field_value(rec, FIELD_SHIFR).strip() or None

        existing = self.store.get_record_by_key(key)
        merged = existing is not None
        if existing is None:
            existing = self.store.add_record(key, title, year, self._now())
        union_id = existing['id']

        dup = self.store.get_holding(union_id, sigla, source_mfn)
        if dup is None:
            self.store.add_holding(union_id, sigla, source_db, source_mfn,
                                   shifr, self._now())
        return {'union_id': union_id, 'dedup_key': key, 'merged': merged}

    # -- федеративный поиск (8.3) ------------------------------------------ #
    def search(self, query=None, year=None):
        """Поиск по подстроке заглавия / году -> сводные записи со списком сигл.

        ``query`` — substring заглавия; ``year`` — точный год. Каждый результат
        дополнен ``siglas`` (держатели) и ``holdings_count``.
        """
        recs = self.store.search_records(title_like=query, year=year)
        out = []
        for r in recs:
            r = dict(r)
            r['siglas'] = self.store.siglas(r['id'])
            r['holdings_count'] = len(self.store.holdings(r['id']))
            out.append(r)
        return out

    def holdings(self, union_id):
        """Все holdings (держания) сводной записи."""
        return self.store.holdings(union_id)

    def record(self, union_id):
        """Сводная запись + её сиглы/holdings (или None)."""
        r = self.store.get_record(union_id)
        if r is None:
            return None
        r = dict(r)
        r['siglas'] = self.store.siglas(union_id)
        r['holdings'] = self.store.holdings(union_id)
        return r

    def stats(self):
        """Сводка каталога: ``{records, holdings, dedup_rate}``.

        ``dedup_rate`` — доля держаний, «сэкономленных» дедупликацией:
        ``1 - records/holdings`` (0 если держаний нет). 0 => свода не было,
        к 1 => высокая дублируемость изданий между библиотеками.
        """
        records, holdings = self.store.counts()
        dedup_rate = round(1.0 - records / holdings, 4) if holdings else 0.0
        return {'records': records, 'holdings': holdings,
                'dedup_rate': dedup_rate}
