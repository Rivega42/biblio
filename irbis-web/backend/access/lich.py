#!/usr/bin/env python3
"""LICH — личные данные читателя при работе с полными текстами (кластер 7, рёбра 7.4/7.5).

Серверная БД ИРБИС64 ``LICH`` фиксирует персональную активность читателя по
полным текстам (ПТ): закладки, скачанные страницы, личную оценку (рейтинг),
обращения. Связь — читатель (``RDR``, по ``RI=``) ↔ полный текст (``TXT=``). Здесь
воспроизведены три рабочих среза для читательского кабинета ЭБ:

  * **закладки**           — поле 3 (повторяющееся: номера страниц);
  * **рейтинг**            — поле 7 (личная оценка ПТ, число 0..5);
  * **счётчик скачанных**  — поле 4 (кол-во скачанных страниц).

И производная величина для учёта квоты (ребро 7.5):
  * **остаток бюджета скачивания** ``download_budget = RIGHT.^F − LICH.v4`` —
    лимит страниц из шаблона прав минус уже скачанные страницы читателем.

Источники (только факты из конфигов):
  * ``docs/recon/deep/reference/databases/DB_SERVICE.md`` §2 (поля 1/2/3/4/5/6/7/40,
    префиксы ``RI=``/``TXT=``/``ZKL=``/``COL=``/``FULL=``, ``LICH\\lich_web.pft``);
  * ``docs/design/INTEGRATION_MAP.md`` кластер 7 (рёбра 7.4/7.5);
  * ``docs/recon/deep/FINDINGS_09_web_reader.md`` (закладки ПТ в ЛК, RDR_ZAKLADKI → LICH).

> ВНИМАНИЕ (как и в DB_SERVICE §2): ``LICH`` содержит персональные данные. Этот
> модуль владеет ТОЛЬКО структурой (читатель+текст → закладки/рейтинг/скачано); он
> ничего не пишет в живой ИРБИС-сервер — это собственный стор кабинета ПТ (тот же
> посыл изоляции, что у holds/social/notifications).

Ключ записи — пара (``reader``, ``text``): ``reader`` = идентификатор читателя
(RDR ``RI=`` / тикет), ``text`` = идентификатор полного текста (``TXT=``; в боевом
ИРБИС это связка БД ЭБ + шифр, здесь — непрозрачная строка). На пару — ровно одна
запись LICH (как в серверной БД: одна запись на читателя+текст), где аккумулируются
закладки/счётчик/оценка.

Бэкенд-портируемость (ADR-004): ``LichStore`` работает на sqlite (дефолт) и
PostgreSQL (по DSN) с одинаковой поверхностью; DDL зеркалит схему, psycopg —
лениво. ``LichService`` — доменная логика над стором + опциональный ``rights``-seam
для расчёта остатка квоты (ребро 7.5).
"""
import json
import threading
import time

# Границы личной оценки (рейтинга) ПТ. DB_SERVICE §2: пороги индексации v7 — 0..5
# (префиксы OI0..OI5 / OR0..OR5). Оценка вне диапазона → ValueError (роут → 400).
RATING_MIN = 0
RATING_MAX = 5


def _is_pg(handle):
    """True, если ``handle`` — PG DSN-строка (а не путь к sqlite-файлу)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


def _clamp_rating(rating):
    """Привести рейтинг к int в [RATING_MIN..RATING_MAX] или поднять ValueError."""
    try:
        r = int(rating)
    except (TypeError, ValueError):
        raise ValueError('рейтинг должен быть целым числом %d..%d' % (RATING_MIN, RATING_MAX))
    if r < RATING_MIN or r > RATING_MAX:
        raise ValueError('рейтинг вне диапазона %d..%d' % (RATING_MIN, RATING_MAX))
    return r


def _page_no(page):
    """Привести номер страницы-закладки к положительному int или поднять ValueError."""
    try:
        n = int(page)
    except (TypeError, ValueError):
        raise ValueError('номер страницы должен быть целым числом')
    if n < 1:
        raise ValueError('номер страницы должен быть ≥ 1')
    return n


# --------------------------------------------------------------------------- #
# Хранилище личных данных LICH (sqlite dev / PostgreSQL prod), своя схема.
# Одна строка на (reader, text); закладки — JSON-массив номеров страниц (поле 3).
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS lich_entry (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  reader          TEXT NOT NULL,             -- поле 1: идентификатор читателя (RI=)
  text            TEXT NOT NULL,             -- поле 2: идентификатор полного текста (TXT=)
  bookmarks_json  TEXT NOT NULL DEFAULT '[]',-- поле 3: закладки (номера страниц)
  downloaded      INTEGER NOT NULL DEFAULT 0,-- поле 4: кол-во скачанных страниц
  rating          INTEGER,                   -- поле 7: личная оценка (NULL = не оценено)
  updated_at      REAL NOT NULL,
  UNIQUE(reader, text)
);
CREATE INDEX IF NOT EXISTS lich_reader_idx ON lich_entry(reader);
CREATE INDEX IF NOT EXISTS lich_text_idx   ON lich_entry(text);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS lich_entry (
  id              BIGSERIAL PRIMARY KEY,
  reader          TEXT NOT NULL,
  text            TEXT NOT NULL,
  bookmarks_json  TEXT NOT NULL DEFAULT '[]',
  downloaded      INTEGER NOT NULL DEFAULT 0,
  rating          INTEGER,
  updated_at      DOUBLE PRECISION NOT NULL,
  UNIQUE(reader, text)
);
CREATE INDEX IF NOT EXISTS lich_reader_idx ON lich_entry(reader);
CREATE INDEX IF NOT EXISTS lich_text_idx   ON lich_entry(text);
"""


class LichStore:
    """Стор личных данных ПТ (sqlite по умолчанию / PostgreSQL по DSN).

    Одна запись на (reader, text). Поверхность низкого уровня:
    ``get`` / ``ensure`` / ``set_bookmarks`` / ``set_downloaded`` / ``set_rating`` /
    ``for_reader`` / ``count``. Бизнес-операции (добавить/снять закладку, инкремент
    скачанного) живут в ``LichService``.

    Parameters
    ----------
    db_path : str
        ``':memory:'`` (дефолт) / путь к sqlite-файлу, ЛИБО PG DSN (``postgresql://…``).
    backend : str | None
        ``'sqlite'`` | ``'postgres'``; если не задан — по виду ``db_path``.
    """

    def __init__(self, db_path=':memory:', backend=None):
        self.db_path = db_path
        if backend is None:
            backend = 'postgres' if _is_pg(db_path) else 'sqlite'
        self.backend = backend
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is not None and not getattr(c, 'closed', False):
            return c
        if self.backend == 'postgres':
            import psycopg
            from psycopg.rows import dict_row
            c = psycopg.connect(self.db_path, row_factory=dict_row, autocommit=True)
        else:
            import sqlite3
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
        self._local.conn = c
        return c

    @property
    def _ph(self):
        return '%s' if self.backend == 'postgres' else '?'

    def ensure_schema(self):
        c = self._conn()
        if self.backend == 'postgres':
            c.execute(_SCHEMA_PG)
        else:
            c.executescript(SCHEMA_SQLITE)
            c.commit()

    @staticmethod
    def _view(r):
        return {
            'id': r['id'],
            'reader': r['reader'],
            'text': r['text'],
            'bookmarks': json.loads(r['bookmarks_json'] or '[]'),
            'downloaded': int(r['downloaded'] or 0),
            'rating': (None if r['rating'] is None else int(r['rating'])),
            'updatedAt': float(r['updated_at']),
        }

    def get(self, reader, text):
        """Запись LICH для (reader, text) — нормализованный dict, либо None."""
        ph = self._ph
        r = self._conn().execute(
            'SELECT * FROM lich_entry WHERE reader=%s AND text=%s' % (ph, ph),
            (str(reader), str(text))).fetchone()
        return self._view(dict(r)) if r else None

    def ensure(self, reader, text, now=None):
        """Вернуть запись (reader, text), создав пустую при отсутствии."""
        existing = self.get(reader, text)
        if existing is not None:
            return existing
        ts = float(now if now is not None else time.time())
        c = self._conn()
        ph = self._ph
        sql = ('INSERT INTO lich_entry(reader,text,bookmarks_json,downloaded,rating,updated_at) '
               'VALUES(%s,%s,%s,%s,%s,%s)' % (ph, ph, ph, ph, ph, ph))
        if self.backend == 'postgres':
            c.execute(sql + ' ON CONFLICT(reader,text) DO NOTHING',
                      (str(reader), str(text), '[]', 0, None, ts))
        else:
            c.execute(
                'INSERT OR IGNORE INTO lich_entry'
                '(reader,text,bookmarks_json,downloaded,rating,updated_at) '
                'VALUES(?,?,?,?,?,?)',
                (str(reader), str(text), '[]', 0, None, ts))
            c.commit()
        return self.get(reader, text)

    def _update(self, reader, text, sets, params, now):
        """Применить SET-фрагмент к строке (reader,text), обновив updated_at."""
        ts = float(now if now is not None else time.time())
        ph = self._ph
        c = self._conn()
        c.execute(
            'UPDATE lich_entry SET %s, updated_at=%s WHERE reader=%s AND text=%s'
            % (sets, ph, ph, ph),
            tuple(params) + (ts, str(reader), str(text)))
        if self.backend != 'postgres':
            c.commit()
        return self.get(reader, text)

    def set_bookmarks(self, reader, text, pages, now=None):
        """Заменить множество закладок (поле 3) на нормализованный список страниц."""
        self.ensure(reader, text, now=now)
        pj = json.dumps(list(pages), ensure_ascii=False)
        return self._update(reader, text, 'bookmarks_json=%s' % self._ph, [pj], now)

    def set_downloaded(self, reader, text, n, now=None):
        """Установить счётчик скачанных страниц (поле 4) в ``n`` (≥0)."""
        self.ensure(reader, text, now=now)
        return self._update(reader, text, 'downloaded=%s' % self._ph, [max(0, int(n))], now)

    def set_rating(self, reader, text, rating, now=None):
        """Установить личную оценку (поле 7); ``None`` — снять оценку."""
        self.ensure(reader, text, now=now)
        val = None if rating is None else int(rating)
        return self._update(reader, text, 'rating=%s' % self._ph, [val], now)

    def for_reader(self, reader, limit=500):
        """Все записи ПТ читателя (новейшие по обновлению первыми)."""
        limit = max(1, min(5000, int(limit)))
        ph = self._ph
        rows = self._conn().execute(
            'SELECT * FROM lich_entry WHERE reader=%s '
            'ORDER BY updated_at DESC, id DESC LIMIT %s' % (ph, ph),
            (str(reader), limit)).fetchall()
        return [self._view(dict(r)) for r in rows]

    def count(self):
        r = self._conn().execute('SELECT COUNT(*) AS n FROM lich_entry').fetchone()
        return int(dict(r)['n'])


class LichService:
    """Личный кабинет ПТ: закладки/рейтинг/скачивания + остаток квоты (рёбра 7.4/7.5).

    Доменная логика над ``LichStore`` + опциональный ``rights``-seam для лимита ^F.

    Parameters
    ----------
    store : LichStore
        Стор личных данных ПТ (reader+text → закладки/рейтинг/скачано).
    rights : object | None
        Объект с ``page_limit(reader_category, ...) -> int|None`` (обычно
        ``access.rights.RightService``). Нужен только для ``download_budget`` (7.5).
        ``None`` ⇒ без сведений о лимите (бюджет не ограничен).
    now : callable
        Часы (``time.time`` по умолчанию) — детерминизм тестов.
    """

    def __init__(self, store, rights=None, now=None):
        self.store = store
        self.rights = rights
        if now is None:
            now = time.time
        self._now = now

    # ---- закладки (поле 3, ребро 7.4) ------------------------------------ #
    def bookmarks(self, reader, text):
        """Отсортированный список страниц-закладок читателя по тексту (пусто — [])."""
        entry = self.store.get(reader, text)
        return list(entry['bookmarks']) if entry else []

    def add_bookmark(self, reader, text, page):
        """Добавить закладку на страницу (идемпотентно). Возвращает новый список.

        Номер страницы валидируется (``ValueError`` → 400). Дубликат не плодится;
        список держится отсортированным по возрастанию."""
        n = _page_no(page)
        current = set(self.bookmarks(reader, text))
        current.add(n)
        ordered = sorted(current)
        self.store.set_bookmarks(reader, text, ordered, now=self._now())
        return ordered

    def remove_bookmark(self, reader, text, page):
        """Снять закладку со страницы (no-op, если её не было). Возвращает новый список."""
        n = _page_no(page)
        ordered = sorted(p for p in self.bookmarks(reader, text) if p != n)
        self.store.set_bookmarks(reader, text, ordered, now=self._now())
        return ordered

    # ---- рейтинг (поле 7, ребро 7.4) ------------------------------------- #
    def rate(self, reader, text, rating):
        """Поставить личную оценку ПТ (0..5). ``ValueError`` (→400) при выходе за диапазон."""
        r = _clamp_rating(rating)
        self.store.set_rating(reader, text, r, now=self._now())
        return r

    def rating(self, reader, text):
        """Личная оценка читателя по тексту, либо None (не оценено)."""
        entry = self.store.get(reader, text)
        return entry['rating'] if entry else None

    # ---- счётчик скачанных страниц (поле 4, ребро 7.4/7.5) --------------- #
    def downloaded(self, reader, text):
        """Сколько страниц текста читатель уже скачал (поле 4; 0, если записи нет)."""
        entry = self.store.get(reader, text)
        return entry['downloaded'] if entry else 0

    def record_download(self, reader, text, pages=1):
        """Учесть факт скачивания ``pages`` страниц (инкремент поля 4).

        ``pages`` приводится к целому ≥0. Возвращает новое значение счётчика.
        Учёт квоты (отказ при превышении лимита) — забота вызывающего через
        ``download_budget`` ДО фиксации; здесь — только аккумулятор."""
        try:
            delta = int(pages)
        except (TypeError, ValueError):
            raise ValueError('число страниц должно быть целым')
        if delta < 0:
            raise ValueError('число страниц не может быть отрицательным')
        new_total = self.downloaded(reader, text) + delta
        self.store.set_downloaded(reader, text, new_total, now=self._now())
        return new_total

    # ---- остаток квоты скачивания (ребро 7.5) ---------------------------- #
    def download_budget(self, reader, text, *, page_limit=None, reader_category=None,
                        db=None, mfn=None, template_id=None, template=None):
        """Остаток лимита скачивания страниц = ``RIGHT.^F − LICH.v4`` (ребро 7.5).

        Лимит ^F берётся в порядке приоритета:
          1. явный ``page_limit`` (число) — если передан;
          2. иначе — через ``rights``-seam: ``page_limit(reader_category, …)`` с
             разрешением шаблона по записи/id/готовому dict.
        Уже скачано — ``LICH.v4`` (поле 4) читателя по тексту.

        Возвращает:
          * ``None`` — лимит не задан (без ограничения: пустой шаблон / нет ^F /
            нет seam) — скачивание не лимитировано квотой;
          * целое ≥0 — остаток (никогда не отрицательный: ``max(0, ^F − v4)``).
        """
        limit = page_limit
        if limit is None and self.rights is not None:
            try:
                limit = self.rights.page_limit(
                    reader_category, db=db, mfn=mfn,
                    template_id=template_id, template=template)
            except TypeError:
                # seam с упрощённой сигнатурой page_limit(reader_category)
                try:
                    limit = self.rights.page_limit(reader_category)
                except Exception:
                    limit = None
            except Exception:
                limit = None
        if limit is None:
            return None
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return None
        used = self.downloaded(reader, text)
        return max(0, limit - used)

    def can_download(self, reader, text, pages=1, **kw):
        """Можно ли скачать ещё ``pages`` страниц, не превысив квоту (ребро 7.5).

        ``True``, если бюджет не ограничен (``download_budget`` → None) или
        остатка хватает на ``pages``. ``False`` — иначе. Принимает те же
        keyword-аргументы лимита, что и ``download_budget``."""
        budget = self.download_budget(reader, text, **kw)
        if budget is None:
            return True
        try:
            need = int(pages)
        except (TypeError, ValueError):
            return False
        return budget >= max(0, need)

    # ---- сводка для кабинета ---------------------------------------------- #
    def entry(self, reader, text):
        """Полный личный срез по (reader, text): закладки/скачано/рейтинг."""
        e = self.store.get(reader, text)
        if e is None:
            return {'reader': str(reader), 'text': str(text),
                    'bookmarks': [], 'downloaded': 0, 'rating': None}
        return {'reader': e['reader'], 'text': e['text'],
                'bookmarks': list(e['bookmarks']), 'downloaded': e['downloaded'],
                'rating': e['rating']}

    def for_reader(self, reader):
        """Все тексты читателя в кабинете ЭБ (новейшие первыми)."""
        return [{'text': e['text'], 'bookmarks': list(e['bookmarks']),
                 'downloaded': e['downloaded'], 'rating': e['rating']}
                for e in self.store.for_reader(reader)]
