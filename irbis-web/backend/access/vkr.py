#!/usr/bin/env python3
"""VKR — собственный стор выпускных квалификационных работ (рёбра 7.6 + 8.3).

Поток ВКР: студент сдаёт работу (submitted), проверка на антиплагиат фиксирует
% оригинальности (215^W), рецензент утверждает/отклоняет (review), а утверждённая
ВКР привязывается к записи Электронного каталога по шифру 903 (бэкреф IMAGE/ВКР
903 <-> ``I=``, ребро 8.3). Own-store: чистый stdlib + ``sqlite3`` (dev-паритет,
ADR-004), без сети и без новых pip-зависимостей — в точности как ``pay.py`` /
``union.py``.

Что это
-------
  * **7.6 поток ВКР** — жизненный цикл работы: submit -> set_antiplagiat ->
    review (approve/reject). Approve запрещён, если оригинальность ниже порога
    ``min_originality`` — тогда review возвращает отказ с флагом причины;
  * **8.3 бэкреф 903 <-> I=** — ``link_catalog`` привязывает ВКР к записи ЭК по
    шифру документа (903): пишет ``source_db`` / ``source_mfn`` / ``shifr``, что
    и образует обратную ссылку из полнотекстового объекта (IMAGE/ВКР) на запись
    каталога.

Гранты/аудит — на слое маршрутов (``server.py`` + ``access/authz.py``); сам
домен — чистая логика над своим стором.
"""
import sqlite3
import threading
import time

# Статусы потока ВКР.
STATUS_SUBMITTED = 'submitted'
STATUS_REVIEW = 'review'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'
ALL_STATUSES = (STATUS_SUBMITTED, STATUS_REVIEW, STATUS_APPROVED, STATUS_REJECTED)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS vkr (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,            -- заглавие работы
  author        TEXT NOT NULL,            -- автор (студент)
  year          TEXT,                     -- год защиты
  faculty       TEXT,                     -- факультет
  speciality    TEXT,                     -- специальность
  shifr         TEXT,                     -- 903 — шифр записи ЭК (бэкреф 8.3)
  source_db     TEXT,                     -- БД-источник записи ЭК
  source_mfn    INTEGER,                  -- MFN записи в ЭК
  antiplag_pct  REAL,                     -- 215^W — % оригинальности
  status        TEXT NOT NULL,            -- submitted|review|approved|rejected
  file_ref      TEXT,                     -- ссылка на полный текст (IMAGE/ВКР)
  created_at    REAL NOT NULL,
  updated_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS vkr_faculty_idx ON vkr(faculty);
CREATE INDEX IF NOT EXISTS vkr_status_idx ON vkr(status);
CREATE INDEX IF NOT EXISTS vkr_shifr_idx ON vkr(shifr);
"""


class VkrStore:
    """Собственный sqlite-стор выпускных квалификационных работ.

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
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    def add(self, title, author, year, faculty, speciality, file_ref, status,
            created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO vkr(title,author,year,faculty,speciality,file_ref,'
            'status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (title, author,
             None if year is None else str(year),
             faculty, speciality, file_ref, status, created_at, created_at))
        c.commit()
        return self.get(cur.lastrowid)

    def get(self, vkr_id):
        r = self._conn().execute(
            'SELECT * FROM vkr WHERE id=?', (vkr_id,)).fetchone()
        return dict(r) if r else None

    def update(self, vkr_id, updated_at, **fields):
        """Частичное обновление произвольных колонок + ``updated_at``."""
        if not fields:
            return self.get(vkr_id)
        cols = ', '.join('%s=?' % k for k in fields)
        args = list(fields.values()) + [updated_at, vkr_id]
        c = self._conn()
        c.execute('UPDATE vkr SET %s, updated_at=? WHERE id=?' % cols, args)
        c.commit()
        return self.get(vkr_id)

    def delete(self, vkr_id):
        c = self._conn()
        cur = c.execute('DELETE FROM vkr WHERE id=?', (vkr_id,))
        c.commit()
        return cur.rowcount > 0

    def list(self, faculty=None, status=None):
        q = 'SELECT * FROM vkr WHERE 1=1'
        args = []
        if faculty is not None:
            q += ' AND faculty=?'
            args.append(faculty)
        if status is not None:
            q += ' AND status=?'
            args.append(status)
        q += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]


class VkrService:
    """Операции потока ВКР над :class:`VkrStore` (рёбра 7.6 + 8.3).

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    ``min_originality`` — порог оригинальности (% по 215^W) для approve.
    """

    def __init__(self, store=None, now=None, min_originality=70.0):
        self.store = store or VkrStore(':memory:')
        self._now = now or time.time
        self.min_originality = float(min_originality)

    # -- 7.6 поток: сдача -------------------------------------------------- #
    def submit(self, title, author, year=None, faculty=None, speciality=None,
               file_ref=None):
        """Сдать ВКР — создать работу в статусе ``submitted``."""
        return self.store.add(title, author, year, faculty, speciality,
                              file_ref, STATUS_SUBMITTED, self._now())

    # -- 7.6 поток: антиплагиат (215^W) ------------------------------------ #
    def set_antiplagiat(self, vkr_id, pct):
        """Записать % оригинальности (215^W). Возвращает обновлённую ВКР/None."""
        if self.store.get(vkr_id) is None:
            return None
        return self.store.update(vkr_id, self._now(), antiplag_pct=float(pct))

    def originality_ok(self, vkr_id):
        """Проходит ли ВКР порог оригинальности (pct >= ``min_originality``)."""
        rec = self.store.get(vkr_id)
        if rec is None or rec['antiplag_pct'] is None:
            return False
        return float(rec['antiplag_pct']) >= self.min_originality

    # -- 7.6 поток: рецензирование ----------------------------------------- #
    def review(self, vkr_id, approve=True):
        """Утвердить/отклонить ВКР -> ``approved`` / ``rejected``.

        Approve запрещён, если оригинальность ниже порога: тогда работа
        переводится в ``rejected`` и в результате выставляется флаг причины.

        Возвращает ``{'vkr', 'ok', 'reason'}`` (или ``None``, если ВКР нет):
        ``ok`` — итог решения, ``reason`` — ``'low_originality'`` при отказе
        из-за антиплагиата, иначе ``None``.
        """
        if self.store.get(vkr_id) is None:
            return None
        if approve and not self.originality_ok(vkr_id):
            rec = self.store.update(vkr_id, self._now(), status=STATUS_REJECTED)
            return {'vkr': rec, 'ok': False, 'reason': 'low_originality'}
        status = STATUS_APPROVED if approve else STATUS_REJECTED
        rec = self.store.update(vkr_id, self._now(), status=status)
        return {'vkr': rec, 'ok': approve, 'reason': None}

    # -- 8.3 бэкреф 903 <-> I= --------------------------------------------- #
    def link_catalog(self, vkr_id, db, mfn, shifr):
        """Привязать ВКР к записи ЭК по шифру 903 (бэкреф IMAGE/ВКР -> I=).

        Пишет ``source_db`` / ``source_mfn`` / ``shifr`` — обратную ссылку из
        полнотекстового объекта на запись каталога. Возвращает ВКР/None.
        """
        if self.store.get(vkr_id) is None:
            return None
        return self.store.update(
            vkr_id, self._now(),
            source_db=db,
            source_mfn=None if mfn is None else int(mfn),
            shifr=shifr)

    # -- чтение ------------------------------------------------------------ #
    def get(self, vkr_id):
        return self.store.get(vkr_id)

    def list(self, faculty=None, status=None):
        return self.store.list(faculty=faculty, status=status)

    def search(self, query):
        """Поиск по подстроке заглавия.

        NB: SQLite-овский LIKE регистронезависим только для ASCII — для
        кириллицы фильтруем подстроку заглавия в Python.
        """
        rows = self.store.list()
        if not query:
            return rows
        needle = query.lower()
        return [r for r in rows if needle in (r['title'] or '').lower()]
