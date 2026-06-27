#!/usr/bin/env python3
"""OCR — слой распознанного текста оцифрованных документов (трек «Оцифровка»).

После сканирования образа документа OCR-движок (вне Biblio) выдаёт распознанный
текст ПОСТРАНИЧНО. Этот модуль — own-store такого текста: хранит текст каждой
страницы по ссылке на образ (``asset_ref``) и даёт полнотекстовый поиск ВНУТРИ
одного документа и по всем сразу (со сниппетами вокруг найденного).

Зачем отдельно
--------------
DAM/образы хранят сам бинарь (скан/PDF) и метаданные. Здесь — ТОЛЬКО текстовый
слой OCR: то, что можно искать. Один документ = много строк ``ocr_page`` (по
одной на страницу), ключ — пара ``(asset_ref, page_no)``.

Паттерн (как ``pay.py`` / ``reader_registry.py``)
-------------------------------------------------
Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей. Соединение thread-local; строки — обычные dict; ``now``
инжектируется (по умолчанию :func:`_utcnow`, ISO8601) для детерминизма в тестах.
Никаких записей в живой ИРБИС.
"""
import datetime
import sqlite3
import threading

# Язык распознавания по умолчанию (поле ``lang`` строки страницы).
DEFAULT_LANG = 'rus'


def _utcnow():
    """Текущий момент в ISO8601 (UTC, секунды). Инжектируемый источник времени."""
    return datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS ocr_page (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_ref  TEXT NOT NULL,             -- ссылка на образ документа (DAM/PDF)
  page_no    INTEGER NOT NULL,          -- номер страницы (1..N)
  text       TEXT,                      -- распознанный текст страницы
  lang       TEXT DEFAULT 'rus',        -- язык распознавания
  created_at TEXT,                      -- ISO8601 (UTC)
  UNIQUE(asset_ref, page_no)
);
CREATE INDEX IF NOT EXISTS ocr_page_asset_idx ON ocr_page(asset_ref);
"""


class OcrStore:
    """Собственный sqlite-стор OCR-страниц. ``:memory:`` или файл; create-on-init.
    Соединение thread-local (домашний стиль); строки — dict."""

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

    def add_page(self, asset_ref, page_no, text, lang=DEFAULT_LANG,
                 created_at=None):
        """Завести/обновить страницу (upsert по ``(asset_ref, page_no)``).

        Повторный вызов той же пары обновляет ``text``/``lang``/``created_at``,
        но не плодит дубль (UNIQUE-ключ). Возвращает строку-dict."""
        when = _utcnow() if created_at is None else created_at
        c = self._conn()
        c.execute(
            'INSERT INTO ocr_page(asset_ref,page_no,text,lang,created_at) '
            'VALUES(?,?,?,?,?) '
            'ON CONFLICT(asset_ref,page_no) DO UPDATE SET '
            'text=excluded.text, lang=excluded.lang, '
            'created_at=excluded.created_at',
            (asset_ref, int(page_no), text, lang, when))
        c.commit()
        return self.get_page(asset_ref, page_no)

    def get_page(self, asset_ref, page_no):
        r = self._conn().execute(
            'SELECT * FROM ocr_page WHERE asset_ref=? AND page_no=?',
            (asset_ref, int(page_no))).fetchone()
        return dict(r) if r else None

    def pages(self, asset_ref):
        """Все страницы документа по возрастанию ``page_no``."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM ocr_page WHERE asset_ref=? ORDER BY page_no',
            (asset_ref,)).fetchall()]

    def delete_document(self, asset_ref):
        """Удалить все страницы документа. Возвращает число удалённых строк."""
        c = self._conn()
        cur = c.execute('DELETE FROM ocr_page WHERE asset_ref=?', (asset_ref,))
        c.commit()
        return cur.rowcount

    def all_pages(self):
        """Все страницы всех документов (asset_ref, затем page_no)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM ocr_page ORDER BY asset_ref, page_no').fetchall()]


class OcrService:
    """Операции над :class:`OcrStore` — индексация и полнотекстовый поиск.

    Поиск регистронезависимый и корректно работает с кириллицей (``str.lower``
    в Python — Unicode-aware). ``now`` инжектируется для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or OcrStore(':memory:')
        self._now = now or _utcnow

    def index_document(self, asset_ref, pages, lang=DEFAULT_LANG):
        """Проиндексировать документ постранично.

        ``pages`` — список ``{'page_no', 'text'}``; каждая страница
        добавляется/обновляется (upsert). Возвращает число обработанных
        страниц."""
        n = 0
        for p in pages:
            self.store.add_page(asset_ref, p['page_no'], p.get('text', ''),
                                lang=lang, created_at=self._now())
            n += 1
        return n

    def _snippet(self, text, query, width=40):
        """Фрагмент ``text`` вокруг ПЕРВОГО вхождения ``query``.

        Регистронезависимо; по краям ставится ``'...'``, если фрагмент не
        упирается в начало/конец строки. Нет вхождения (или пустой ввод) -> ''."""
        if not text or not query:
            return ''
        pos = text.lower().find(query.lower())
        if pos == -1:
            return ''
        start = max(0, pos - width)
        end = min(len(text), pos + len(query) + width)
        frag = text[start:end]
        if start > 0:
            frag = '...' + frag
        if end < len(text):
            frag = frag + '...'
        return frag

    def search_in_document(self, asset_ref, query):
        """Поиск ``query`` по страницам ОДНОГО документа.

        Возвращает список ``{'page_no', 'snippet'}`` для страниц, где запрос
        встречается (регистронезависимо). Пустой ``query`` -> ``[]``."""
        if not query:
            return []
        ql = query.lower()
        out = []
        for p in self.store.pages(asset_ref):
            text = p.get('text') or ''
            if ql in text.lower():
                out.append({'page_no': p['page_no'],
                            'snippet': self._snippet(text, query)})
        return out

    def search_all(self, query):
        """Поиск ``query`` по всем страницам всех документов.

        Возвращает список ``{'asset_ref', 'page_no', 'snippet'}``. Пустой
        ``query`` -> ``[]``."""
        if not query:
            return []
        ql = query.lower()
        out = []
        for p in self.store.all_pages():
            text = p.get('text') or ''
            if ql in text.lower():
                out.append({'asset_ref': p['asset_ref'],
                            'page_no': p['page_no'],
                            'snippet': self._snippet(text, query)})
        return out

    def page_count(self, asset_ref):
        """Число проиндексированных страниц документа."""
        return len(self.store.pages(asset_ref))

    def word_count(self, asset_ref):
        """Суммарное число слов по страницам документа (``str.split``)."""
        total = 0
        for p in self.store.pages(asset_ref):
            total += len((p.get('text') or '').split())
        return total
