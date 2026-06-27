#!/usr/bin/env python3
"""SERIALS — сериальная иерархия: периодика и многотомники (рёбра 9.2/9.3).

Связь «сводный сериал <-> выпуск» в ИРБИС хранится связующими полями:

  * **9.2 периодика** — журнал <-> номер: 461 (общая часть издания) на записи
    номера ссылается на сводную запись журнала; 46x (доп. серийные сведения,
    здесь как 46) уточняют год/номер выпуска;
  * **9.3 многотомник** — том <-> сводная запись: 481 (специфика тома) на записи
    тома ссылается на сводную запись многотомника; 963 несёт обозначение тома.

Own-store, как ``pay.py``/``union.py``: чистый stdlib + ``sqlite3`` (dev-паритет,
ADR-004), без сети и без новых pip-зависимостей. Связь моделируется
структурно — родитель ``serial`` (журнал/многотомник) и дети ``serial_issue``
(номера/тома), — а не дублированием тегов 461/481 в каждой записи: это и есть
рёбра 461/46 (журнал) и 481/963 (многотомник) в нашей реляционной форме.
"""
import sqlite3
import threading
import time

# Виды сводного сериала.
KIND_JOURNAL = 'journal'        # 9.2 — периодика (461/46)
KIND_MULTIVOLUME = 'multivolume'  # 9.3 — многотомник (481/963)
ALL_KINDS = (KIND_JOURNAL, KIND_MULTIVOLUME)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS serial (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,            -- journal | multivolume
  title      TEXT NOT NULL,            -- 200^a заглавие сводной записи
  issn       TEXT,                     -- 11^a ISSN (для журналов)
  shifr      TEXT,                     -- 903 шифр сводной записи
  source_mfn INTEGER,                  -- MFN сводной записи в БД-источнике
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS serial_issue (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  serial     INTEGER NOT NULL REFERENCES serial(id) ON DELETE CASCADE,
  number     TEXT,                     -- номер выпуска (461/46) / обозначение тома
  year       TEXT,                     -- год выпуска
  volume     TEXT,                     -- 963 — номер тома многотомника
  source_mfn INTEGER,                  -- MFN записи номера/тома в БД-источнике
  created_at REAL NOT NULL,
  UNIQUE(serial, number, year, volume)
);
CREATE INDEX IF NOT EXISTS serial_issue_serial_idx ON serial_issue(serial);
CREATE INDEX IF NOT EXISTS serial_title_idx ON serial(title);
"""


class SerialsStore:
    """Собственный sqlite-стор сериальной иерархии (сводные сериалы + выпуски).

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

    # ---- сводный сериал --------------------------------------------------- #
    def add_serial(self, kind, title, issn, shifr, source_mfn, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO serial(kind,title,issn,shifr,source_mfn,created_at) '
            'VALUES(?,?,?,?,?,?)',
            (kind, title, issn, shifr,
             None if source_mfn is None else int(source_mfn), created_at))
        c.commit()
        return self.get_serial(cur.lastrowid)

    def get_serial(self, serial_id):
        r = self._conn().execute(
            'SELECT * FROM serial WHERE id=?', (serial_id,)).fetchone()
        return dict(r) if r else None

    def serials(self):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM serial ORDER BY id').fetchall()]

    # ---- выпуск (номер / том) -------------------------------------------- #
    def get_issue(self, serial_id, number, year, volume):
        r = self._conn().execute(
            'SELECT * FROM serial_issue WHERE serial=? AND number IS ? '
            'AND year IS ? AND volume IS ?',
            (serial_id, number, year, volume)).fetchone()
        return dict(r) if r else None

    def add_issue(self, serial_id, number, year, volume, source_mfn,
                  created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO serial_issue(serial,number,year,volume,source_mfn,'
            'created_at) VALUES(?,?,?,?,?,?)',
            (serial_id, number, year, volume,
             None if source_mfn is None else int(source_mfn), created_at))
        c.commit()
        r = c.execute('SELECT * FROM serial_issue WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def issues(self, serial_id):
        """Выпуски сериала хронологически: по году, затем тому/номеру, затем id."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM serial_issue WHERE serial=? '
            'ORDER BY year, volume, number, id', (serial_id,)).fetchall()]

    def issue_count(self, serial_id):
        return int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM serial_issue WHERE serial=?',
            (serial_id,)).fetchone()['n'])

    def counts(self):
        rows = self._conn().execute(
            'SELECT kind, COUNT(*) AS n FROM serial GROUP BY kind').fetchall()
        by_kind = {r['kind']: int(r['n']) for r in rows}
        issues = int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM serial_issue').fetchone()['n'])
        return by_kind, issues


class SerialsService:
    """Операции сериальной иерархии над :class:`SerialsStore`.

    Регистрация сводного сериала (журнал/многотомник) и присоединение к нему
    выпусков (номеров/томов) — рёбра 461/46 (9.2) и 481/963 (9.3). ``now``
    инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or SerialsStore(':memory:')
        self._now = now or time.time

    # -- регистрация сводного сериала -------------------------------------- #
    def register(self, kind, title, issn=None, shifr=None, source_mfn=None):
        """Завести сводную запись журнала/многотомника.

        ``kind`` ∈ :data:`ALL_KINDS`. Возвращает строку сериала.
        """
        if kind not in ALL_KINDS:
            raise ValueError('unknown serial kind: %r' % (kind,))
        return self.store.add_serial(
            kind, title,
            None if issn is None else str(issn),
            None if shifr is None else str(shifr),
            source_mfn, self._now())

    # -- присоединение выпуска (9.2 461/46 ; 9.3 481/963) ------------------ #
    def add_issue(self, serial_id, number=None, year=None, volume=None,
                  source_mfn=None):
        """Добавить номер/том в иерархию сериала.

        Для журнала это номер (461 на сводную + 46 серийные сведения),
        для многотомника — том (481 на сводную + 963 обозначение тома).
        Идемпотентно по ``(serial, number, year, volume)``: повтор не задваивает,
        возвращает уже существующий выпуск.

        Возвращает ``None``, если сериала с таким id нет.
        """
        if self.store.get_serial(serial_id) is None:
            return None
        number = None if number is None else str(number)
        year = None if year is None else str(year)
        volume = None if volume is None else str(volume)
        existing = self.store.get_issue(serial_id, number, year, volume)
        if existing is not None:
            return existing
        return self.store.add_issue(serial_id, number, year, volume,
                                    source_mfn, self._now())

    # -- чтение ------------------------------------------------------------- #
    def issues(self, serial_id):
        """Номера/тома сериала (хронологически)."""
        return self.store.issues(serial_id)

    def get(self, serial_id):
        """Сериал + число выпусков (или ``None``, если не найден)."""
        s = self.store.get_serial(serial_id)
        if s is None:
            return None
        s = dict(s)
        s['issues_count'] = self.store.issue_count(serial_id)
        return s

    def find(self, query):
        """Поиск сериалов по подстроке заглавия (кириллица — фильтр в Python).

        SQLite-овский LIKE регистронезависим только для ASCII, поэтому
        подстроку заглавия фильтруем в Python (как ``union.search_records``).
        """
        rows = self.store.serials()
        if query:
            needle = query.lower()
            rows = [r for r in rows if needle in (r['title'] or '').lower()]
        for r in rows:
            r['issues_count'] = self.store.issue_count(r['id'])
        return rows

    def stats(self):
        """Сводка: ``{serials, issues, journals, multivolumes}``."""
        by_kind, issues = self.store.counts()
        journals = by_kind.get(KIND_JOURNAL, 0)
        multivolumes = by_kind.get(KIND_MULTIVOLUME, 0)
        return {'serials': journals + multivolumes, 'issues': issues,
                'journals': journals, 'multivolumes': multivolumes}
