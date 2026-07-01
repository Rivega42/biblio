#!/usr/bin/env python3
"""SEARCH_INDEX — морфологический полнотекстовый индекс с ранжированием (issue #368).

Own-store полнотекстовый поиск Biblio: собственный обратный индекс (постинги
term→tf по документам) поверх дуального бэкенда (sqlite dev / PostgreSQL prod),
ранжирование BM25. Назначение — искать каталожные записи/полные тексты по
СЛОВОФОРМАМ: пользователь вводит «книга», индекс находит документ, где написано
«книги»/«книгу»/«книгой» — за счёт русской морфологии (стеммер) на этапе
индексации И запроса основы совпадают.

Почему own-store, а не FTS5/tsvector
-------------------------------------
BM25 здесь считается в Python НАД постингами (а не средствами FTS5 sqlite или
``ts_rank``/``tsvector`` PostgreSQL). Это сознательный выбор: одна и та же
формула ранжирования и один и тот же стеммер работают ОДИНАКОВО на обоих
бэкендах — поведение поиска не зависит от движка БД. БД хранит только два
плоских отношения (документ + постинги), всё остальное — чистый Python.

Бэкенд-портируемость (ADR-004, зеркало ``access/fulltext.py``)
--------------------------------------------------------------
``SearchIndexStore`` работает на ДВУХ бэкендах с одинаковой поверхностью (как
``fulltext.py``/``rights.py``/``lich.py``): sqlite по умолчанию (свой файл или
``:memory:``), postgres по DSN; DDL зеркалит схему (``SCHEMA_SQLITE`` /
``_SCHEMA_PG``), psycopg импортируется лениво, соединение — ``threading.local``,
плейсхолдер ``_ph`` ('?' для sqlite / '%s' для postgres).

Морфология
----------
``russian_stem`` — реализация русского стеммера Snowball
(snowballstem.org/algorithms/russian/stemmer.html), чистый Python,
детерминированная, без зависимостей. Латиница/цифры не стеммятся (возвращаются
как есть, в нижнем регистре). См. подробный разбор шагов у самой функции.

Только stdlib: re, math, sqlite3, threading, time, json.
"""
import json
import math
import re
import threading
import time

__all__ = [
    'russian_stem', 'tokenize', 'normalize_query', 'STOPWORDS',
    'SearchIndexStore', 'SearchIndex',
]


# --------------------------------------------------------------------------- #
# Морфология — русский стеммер Snowball (чистый Python, детерминированный).
# --------------------------------------------------------------------------- #
# Гласные русского языка (нижний регистр) — опорные для разметки регионов.
_VOWELS = set('аеиоуыэюя')

# Окончания шагов стеммера. Внутри каждой группы порядок проверки — от ДЛИННОГО
# к короткому: удаляется первое подошедшее (так алгоритм Snowball гарантирует
# максимальное окончание, а не его префикс).
#
# Шаг 1, группа PERFECTIVE GERUND. Делится на две подгруппы: первая снимается
# только если ей предшествует «а» или «я» (group 1 в спецификации Snowball),
# вторая — без такого условия.
_PERFECTIVE_GERUND_1 = ('вшись', 'вши', 'в')
_PERFECTIVE_GERUND_2 = ('ившись', 'ывшись', 'ивши', 'ывши', 'ив', 'ыв')

# REFLEXIVE.
_REFLEXIVE = ('ся', 'сь')

# ADJECTIVE — окончания прилагательных (шаг 1, ветка ADJECTIVAL).
_ADJECTIVE = (
    'ими', 'ыми',
    'его', 'ого', 'ему', 'ому',
    'ее', 'ие', 'ые', 'ое',
    'ей', 'ий', 'ый', 'ой',
    'ем', 'им', 'ым', 'ом',
    'их', 'ых',
    'ую', 'юю',
    'ая', 'яя',
    'ою', 'ею',
)

# PARTICIPLE — причастные «связки», снимаются ПЕРЕД прилагательным (ADJECTIVAL).
# Подгруппа 1 снимается только после «а»/«я», подгруппа 2 — безусловно.
_PARTICIPLE_1 = ('ем', 'нн', 'вш', 'ющ', 'щ')
_PARTICIPLE_2 = ('ивш', 'ывш', 'ующ')

# VERB — глагольные окончания (шаг 1, ветка VERB).
# Подгруппа 1 (после «а»/«я») и подгруппа 2 (безусловно).
_VERB_1 = (
    'ете', 'йте', 'ешь', 'нно',
    'ла', 'на', 'ли', 'ем', 'ло', 'но', 'ет', 'ют', 'ны', 'ть',
    'й', 'л', 'н',
)
_VERB_2 = (
    'ейте', 'уйте', 'енно',
    'ила', 'ыла', 'ена', 'ите', 'или', 'ыли', 'ило', 'ыло', 'ено',
    'уют', 'ует',
    'ей', 'уй', 'ил', 'ыл', 'им', 'ым', 'ен', 'ят', 'ит', 'ыт', 'ены', 'ить',
    'ыть', 'ишь', 'ую', 'ю',
)

# NOUN — именные окончания (шаг 1, ветка NOUN).
_NOUN = (
    'иями', 'ями', 'ами',
    'иям', 'ием', 'иях',
    'ям', 'ам', 'ом', 'ем', 'ах', 'ях',
    'еи', 'ии', 'ей', 'ой', 'ий', 'ев', 'ов', 'ие', 'ье', 'ия', 'ья',
    'ию', 'ью',
    'а', 'е', 'и', 'й', 'о', 'у', 'ы', 'ь', 'ю', 'я',
)

# DERIVATIONAL (шаг 3) — снимается в R2.
_DERIVATIONAL = ('ост', 'ость')

# SUPERLATIVE (шаг 4).
_SUPERLATIVE = ('ейше', 'ейш')


def _rv_region(word):
    """Индекс начала региона RV: позиция ПОСЛЕ первой гласной слова.

    RV — «всё, что после первой гласной». Если гласных нет — RV пуст (len(word))."""
    for i, ch in enumerate(word):
        if ch in _VOWELS:
            return i + 1
    return len(word)


def _r1_r2(word):
    """Индексы начала регионов R1 и R2 (как в общей схеме Snowball).

    R1 — область после первой пары «гласная + негласная». R2 — то же внутри R1
    (после следующей такой пары в R1). Возвращает (r1, r2) — индексы начала."""
    n = len(word)

    def _after_pair(start):
        i = start
        # ищем гласную, за которой идёт негласная
        while i < n and word[i] in _VOWELS:
            # нужно начинать с гласной — но пара ищется по всей строке
            break
        # классический проход: найти первую гласную, затем первую негласную после неё
        j = start
        while j < n and word[j] not in _VOWELS:
            j += 1
        while j < n and word[j] in _VOWELS:
            j += 1
        # j указывает на первую негласную после блока гласных
        if j < n:
            return j + 1
        return n

    r1 = _after_pair(0)
    r2 = _after_pair(r1)
    return r1, r2


def _try_strip(word, rv_start, endings):
    """Снять первое подошедшее окончание из ``endings`` в пределах RV.

    Окончание снимается ТОЛЬКО если целиком лежит в RV (его начало ≥ rv_start) и
    слово на него заканчивается. ``endings`` упорядочены от длинного к короткому —
    берём первое совпадение. Возвращает (новое_слово, True) либо (word, False)."""
    for end in _sorted_by_len(endings):
        if not end:
            continue
        if word.endswith(end) and len(word) - len(end) >= rv_start:
            return word[:len(word) - len(end)], True
    return word, False


def _try_strip_after_ay(word, rv_start, endings):
    """Снять окончание из ``endings`` в RV, но ТОЛЬКО если перед ним стоит «а»/«я».

    Подгруппы 1 у PERFECTIVE GERUND / VERB снимаются по правилу Snowball «group 1»:
    окончание допустимо лишь когда непосредственно перед ним идёт буква «а» или «я»
    (и сама эта «а»/«я» — часть основы, не удаляется)."""
    for end in _sorted_by_len(endings):
        if not end:
            continue
        if not word.endswith(end):
            continue
        cut = len(word) - len(end)
        if cut < rv_start:
            continue
        if cut >= 1 and word[cut - 1] in ('а', 'я'):
            return word[:cut], True
    return word, False


def _sorted_by_len(endings):
    """Уникальные окончания, отсортированные по убыванию длины (длинные сначала)."""
    seen = []
    for e in endings:
        if e not in seen:
            seen.append(e)
    return sorted(seen, key=len, reverse=True)


def russian_stem(word):
    """Русский стеммер Snowball (snowballstem.org/algorithms/russian/stemmer.html).

    Сводит словоформу к основе детерминированным набором правил. Латиница и
    цифры НЕ стеммятся — возвращаются как есть в нижнем регистре (поиск по ним
    точный). Пустая строка → ''.

    Регионы (общая схема Snowball):
      * **RV** — всё, что после первой гласной слова;
      * **R1** — после первой пары «гласная + негласная»;
      * **R2** — то же внутри R1.

    Шаги (упрощённо, всё — в пределах RV, если не сказано иначе):
      1. PERFECTIVE GERUND (в/вши/вшись после а/я; ив/ивши/ившись/ыв/ывши/ывшись).
         Если снят — переход к шагу 2. Иначе: снять REFLEXIVE (ся/сь); затем
         попытаться ADJECTIVAL (PARTICIPLE перед ADJECTIVE, либо просто ADJECTIVE);
         если ничего не снято — попытаться VERB; если и это нет — снять NOUN.
      2. Если RV кончается на «и» — удалить.
      3. В R2 снять DERIVATIONAL (ост/ость).
      4. Один из: удвоенную «нн» → «н»; SUPERLATIVE (ейш/ейше); если RV кончается
         на «ь» — удалить.

    Возвращает строку-основу (нижний регистр).
    """
    if word is None:
        return ''
    w = str(word).strip().lower()
    if not w:
        return ''
    # Кириллицу стеммим; всё прочее (латиница/цифры/смешанное) — возвращаем как есть.
    if not all(ch in _VOWELS or ('а' <= ch <= 'я') or ch == 'ё' for ch in w):
        return w
    # «ё» → «е» (нормализация, как принято в Snowball Russian).
    w = w.replace('ё', 'е')

    rv = _rv_region(w)
    _, r2 = _r1_r2(w)

    # ---- Шаг 1 ---------------------------------------------------------- #
    # PERFECTIVE GERUND: сначала подгруппа после а/я, затем безусловная подгруппа.
    new, done = _try_strip_after_ay(w, rv, _PERFECTIVE_GERUND_1)
    if not done:
        new, done = _try_strip(w, rv, _PERFECTIVE_GERUND_2)
    if done:
        w = new
    else:
        # REFLEXIVE
        w, _ = _try_strip(w, rv, _REFLEXIVE)
        # ADJECTIVAL = ADJECTIVE [+ PARTICIPLE]
        w2, adj = _try_strip(w, rv, _ADJECTIVE)
        if adj:
            w = w2
            # после снятия прилагательного пробуем снять причастную связку
            p, pdone = _try_strip_after_ay(w, rv, _PARTICIPLE_1)
            if not pdone:
                p, pdone = _try_strip(w, rv, _PARTICIPLE_2)
            if pdone:
                w = p
        else:
            # VERB
            v, vdone = _try_strip_after_ay(w, rv, _VERB_1)
            if not vdone:
                v, vdone = _try_strip(w, rv, _VERB_2)
            if vdone:
                w = v
            else:
                # NOUN
                w, _ = _try_strip(w, rv, _NOUN)

    # пересчёт регионов после шага 1
    rv = _rv_region(w)
    _, r2 = _r1_r2(w)

    # ---- Шаг 2: «и» в конце RV ----------------------------------------- #
    if w.endswith('и') and len(w) - 1 >= rv:
        w = w[:-1]

    # ---- Шаг 3: DERIVATIONAL в R2 -------------------------------------- #
    for end in _sorted_by_len(_DERIVATIONAL):
        if w.endswith(end) and len(w) - len(end) >= r2:
            w = w[:len(w) - len(end)]
            break

    # ---- Шаг 4 --------------------------------------------------------- #
    rv = _rv_region(w)
    if w.endswith('нн') and len(w) - 1 >= rv:
        # удвоенную «нн» → «н»
        w = w[:-1]
    else:
        sup, sdone = _try_strip(w, rv, _SUPERLATIVE)
        if sdone:
            w = sup
            rv = _rv_region(w)
            if w.endswith('нн') and len(w) - 1 >= rv:
                w = w[:-1]
        elif w.endswith('ь') and len(w) - 1 >= rv:
            w = w[:-1]

    return w


# --------------------------------------------------------------------------- #
# Токенайзер + стоп-слова.
# --------------------------------------------------------------------------- #
# Небольшой русский стоп-лист (служебные слова, не несущие смысла для поиска).
STOPWORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
    'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
    'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще',
    'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'ли', 'если',
    'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж',
    'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они',
    'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем',
    'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе',
    'под', 'будет', 'ж', 'кто', 'этот', 'того', 'потому', 'этого', 'какой',
    'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы',
    'нее', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'об',
    'хоть', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего',
    'них', 'какая', 'много', 'разве', 'эту', 'моя', 'свою', 'этой', 'перед',
    'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более',
    'всегда', 'конечно', 'всю', 'между',
}

# Буквенно-цифровой токен: кириллица (с ё) + латиница + цифры.
_TOKEN_RE = re.compile(r'[а-яёa-z0-9]+', re.UNICODE)


def tokenize(text):
    """Разбить текст на список основ (для индексации тела документа).

    Шаги: нижний регистр → выделить буквенно-цифровые токены (кириллица/латиница/
    цифры) → выкинуть стоп-слова → стеммить каждый (``russian_stem``) → отбросить
    пустые. Возвращает список основ (с повторами — частота важна для tf/BM25)."""
    if not text:
        return []
    out = []
    for raw in _TOKEN_RE.findall(str(text).lower()):
        if raw in STOPWORDS:
            continue
        stem = russian_stem(raw)
        if stem and stem not in STOPWORDS:
            out.append(stem)
    return out


def normalize_query(q):
    """Нормализовать поисковый запрос в список основ (та же обработка, что tokenize).

    Запрос проходит ту же морфологию, что и индексируемый текст — поэтому
    словоформа запроса совпадёт с основой в индексе (ищем «книга» — находим
    «книги»). Возвращает список основ (с повторами)."""
    return tokenize(q)


# --------------------------------------------------------------------------- #
# Хранилище индекса (sqlite dev / PostgreSQL prod) — зеркало FulltextStore.
# Два отношения: doc (метаданные документа + длина в токенах) и posting
# (term→tf по документам). BM25 считается в Python над постингами, без FTS5.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS doc (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ref         TEXT NOT NULL UNIQUE,        -- внешний идентификатор документа (db:mfn / URL / ...)
  db          TEXT NOT NULL DEFAULT '',    -- имя БД-источника
  mfn         INTEGER NOT NULL DEFAULT 0,  -- MFN записи (0 если неприменимо)
  title       TEXT NOT NULL DEFAULT '',    -- заголовок (для выдачи)
  length      INTEGER NOT NULL DEFAULT 0,  -- число токенов тела (для нормировки BM25)
  body        TEXT NOT NULL DEFAULT '',    -- усечённый исходный текст (для сниппетов, #D3)
  created_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS posting (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id      INTEGER NOT NULL,            -- ссылка на doc.id
  term        TEXT NOT NULL,               -- основа (после стемминга)
  tf          INTEGER NOT NULL             -- частота основы в документе
);
CREATE INDEX IF NOT EXISTS posting_term_idx ON posting(term);
CREATE INDEX IF NOT EXISTS posting_doc_idx  ON posting(doc_id);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS doc (
  id          BIGSERIAL PRIMARY KEY,
  ref         TEXT NOT NULL UNIQUE,
  db          TEXT NOT NULL DEFAULT '',
  mfn         BIGINT NOT NULL DEFAULT 0,
  title       TEXT NOT NULL DEFAULT '',
  length      INTEGER NOT NULL DEFAULT 0,
  body        TEXT NOT NULL DEFAULT '',
  created_at  DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS posting (
  id          BIGSERIAL PRIMARY KEY,
  doc_id      BIGINT NOT NULL,
  term        TEXT NOT NULL,
  tf          INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS posting_term_idx ON posting(term);
CREATE INDEX IF NOT EXISTS posting_doc_idx  ON posting(doc_id);
"""


def _is_pg(handle):
    """True, если ``handle`` — PG DSN-строка (а не путь к sqlite-файлу)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


class SearchIndexStore:
    """Стор обратного индекса (sqlite по умолчанию / PostgreSQL по DSN).

    Хранит документы (``doc``) и постинги (``posting`` — term→tf на документ).
    Поверхность: ``upsert_doc`` / ``delete`` / ``get_doc`` / ``postings_for_terms`` /
    ``doc_freq`` / ``totals`` / ``doc_view`` / ``count``. Сам BM25 НЕ считает —
    это делает ``SearchIndex`` в Python над постингами (одинаково на обоих бэкендах).

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
    def _doc_view(r):
        """Привести строку ``doc`` к публичной форме."""
        return {
            'id': r['id'],
            'ref': r['ref'],
            'db': r['db'],
            'mfn': int(r['mfn']),
            'title': r['title'],
            'length': int(r['length']),
            'body': r.get('body', '') if isinstance(r, dict) else '',
        }

    def upsert_doc(self, ref, db, mfn, title, terms, body=''):
        """Пересоздать документ ``ref`` с агрегированными постингами.

        Сначала удаляет старый документ с тем же ``ref`` (и его постинги), затем
        вставляет новый ``doc`` (``length`` = число токенов ``terms``) и
        агрегированные постинги term→tf (сколько раз основа встретилась в теле).
        Возвращает публичную форму документа (``_doc_view``)."""
        terms = list(terms or [])
        length = len(terms)
        # агрегируем term → tf
        tf = {}
        for t in terms:
            tf[t] = tf.get(t, 0) + 1
        ts = time.time()
        c = self._conn()
        ph = self._ph
        ref = str(ref)
        # снять старый документ с этим ref (и его постинги)
        self._delete_rows(ref)
        body = str(body or '')[:2000]
        if self.backend == 'postgres':
            row = c.execute(
                'INSERT INTO doc(ref,db,mfn,title,length,body,created_at) '
                'VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *',
                (ref, str(db or ''), int(mfn or 0), str(title or ''), length, body, ts)).fetchone()
            doc_id = row['id']
            for term, n in tf.items():
                c.execute('INSERT INTO posting(doc_id,term,tf) VALUES(%s,%s,%s)',
                          (doc_id, term, n))
            return self._doc_view(dict(row))
        cur = c.execute(
            'INSERT INTO doc(ref,db,mfn,title,length,body,created_at) VALUES(?,?,?,?,?,?,?)',
            (ref, str(db or ''), int(mfn or 0), str(title or ''), length, body, ts))
        doc_id = cur.lastrowid
        for term, n in tf.items():
            c.execute('INSERT INTO posting(doc_id,term,tf) VALUES(?,?,?)',
                      (doc_id, term, n))
        c.commit()
        r = c.execute('SELECT * FROM doc WHERE id=?', (doc_id,)).fetchone()
        return self._doc_view(dict(r))

    def _delete_rows(self, ref):
        """Снять документ ``ref`` и его постинги (внутренний помощник). True если был."""
        c = self._conn()
        ph = self._ph
        row = c.execute('SELECT id FROM doc WHERE ref=%s' % ph, (ref,)).fetchone()
        if row is None:
            return False
        doc_id = dict(row)['id']
        c.execute('DELETE FROM posting WHERE doc_id=%s' % ph, (doc_id,))
        c.execute('DELETE FROM doc WHERE id=%s' % ph, (doc_id,))
        if self.backend != 'postgres':
            c.commit()
        return True

    def delete(self, ref):
        """Удалить документ ``ref`` и его постинги. True если документ существовал."""
        return self._delete_rows(str(ref))

    def get_doc(self, ref):
        """Документ по ``ref`` (публичная форма) или None, если нет."""
        ph = self._ph
        r = self._conn().execute('SELECT * FROM doc WHERE ref=%s' % ph, (str(ref),)).fetchone()
        return self._doc_view(dict(r)) if r is not None else None

    def doc_view(self, doc_id):
        """Документ по внутреннему id (``{ref,db,mfn,title,length}``) или None."""
        ph = self._ph
        r = self._conn().execute('SELECT * FROM doc WHERE id=%s' % ph, (doc_id,)).fetchone()
        return self._doc_view(dict(r)) if r is not None else None

    def postings_for_terms(self, terms):
        """Постинги по списку основ одним IN-запросом: ``[{term,doc_id,tf}, …]``.

        Пустой список основ → []. Дубли основ схлопываются (DISTINCT по входу)."""
        uniq = []
        for t in terms or []:
            if t and t not in uniq:
                uniq.append(t)
        if not uniq:
            return []
        ph = self._ph
        placeholders = ','.join([ph] * len(uniq))
        rows = self._conn().execute(
            'SELECT term, doc_id, tf FROM posting WHERE term IN (%s)' % placeholders,
            tuple(uniq)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            out.append({'term': d['term'], 'doc_id': d['doc_id'], 'tf': int(d['tf'])})
        return out

    def doc_freq(self, terms):
        """Document frequency: ``{term: df}`` — число РАЗНЫХ документов с основой.

        Пустой список → {}. Используется для idf в BM25."""
        uniq = []
        for t in terms or []:
            if t and t not in uniq:
                uniq.append(t)
        if not uniq:
            return {}
        ph = self._ph
        placeholders = ','.join([ph] * len(uniq))
        rows = self._conn().execute(
            'SELECT term, COUNT(DISTINCT doc_id) AS df FROM posting '
            'WHERE term IN (%s) GROUP BY term' % placeholders,
            tuple(uniq)).fetchall()
        out = {t: 0 for t in uniq}
        for r in rows:
            d = dict(r)
            out[d['term']] = int(d['df'])
        return out

    def totals(self):
        """Сводка коллекции: ``{'N': число документов, 'avgdl': средняя длина}``.

        ``avgdl`` — средняя ``length`` по документам (0.0 если коллекция пуста).
        Нужна для нормировки длины в BM25."""
        c = self._conn()
        r = c.execute('SELECT COUNT(*) AS n, COALESCE(SUM(length),0) AS s FROM doc').fetchone()
        d = dict(r)
        n = int(d['n'])
        total_len = int(d['s'])
        avgdl = (total_len / n) if n else 0.0
        return {'N': n, 'avgdl': avgdl}

    def count(self):
        """Число документов в индексе."""
        r = self._conn().execute('SELECT COUNT(*) AS n FROM doc').fetchone()
        return int(dict(r)['n'])


# --------------------------------------------------------------------------- #
# Сервис поиска — индексация, удаление, BM25-поиск, more_like.
# --------------------------------------------------------------------------- #
# Параметры BM25 (классические значения Okapi).
_BM25_K1 = 1.5
_BM25_B = 0.75


class SearchIndex:
    """Полнотекстовый поиск с морфологией и ранжированием BM25 (own-store).

    Индексация — на стороне вызывающего (``index`` per документ); ``reindex_all``
    не предусмотрен. BM25 считается в Python над постингами из ``SearchIndexStore``
    (одинаково на sqlite и PostgreSQL).

    Parameters
    ----------
    store : SearchIndexStore | None
        Стор индекса. ``None`` ⇒ создаётся sqlite ``:memory:`` (дефолт).
    now : callable
        Часы (``time.time`` по умолчанию) — задел для будущих штампов.
    """

    def __init__(self, store=None, now=None):
        self.store = store if store is not None else SearchIndexStore(':memory:')
        self._now = now if now is not None else time.time

    def index(self, ref, text, db='', mfn=0, title=''):
        """Проиндексировать документ ``ref`` по тексту (+ заголовок).

        Токенизирует ``text`` И ``title`` (заголовок тоже ищется), пересоздаёт
        документ в сторе. Возвращает ``{'ref', 'terms': N уникальных основ,
        'length': всего токенов}``."""
        terms = tokenize(text)
        if title:
            terms = terms + tokenize(title)
        self.store.upsert_doc(ref, db, mfn, title, terms, body=text or '')
        return {'ref': str(ref), 'terms': len(set(terms)), 'length': len(terms)}

    @staticmethod
    def _snippet(body, stems, width=45):
        """Фрагмент ``body`` вокруг первого вхождения любой основы запроса (#D3).

        Основа — префикс словоформы, поэтому ищется как подстрока в теле
        (регистронезависимо). По краям — многоточие. Нет тела/совпадения → ''."""
        text = body or ''
        low = text.lower()
        pos = -1
        for st in stems:
            if not st:
                continue
            p = low.find(st)
            if p >= 0 and (pos < 0 or p < pos):
                pos = p
        if pos < 0:
            return ''
        start = max(0, pos - width)
        end = min(len(text), pos + width)
        frag = text[start:end].strip()
        if start > 0:
            frag = '…' + frag
        if end < len(text):
            frag = frag + '…'
        return frag

    def remove(self, ref):
        """Удалить документ из индекса. True если он там был."""
        return self.store.delete(ref)

    def search(self, query, limit=20):
        """Найти документы по запросу, ранжируя по BM25. Список хитов или [].

        Запрос нормализуется (та же морфология, что при индексации) — поэтому
        ищется по СЛОВОФОРМЕ. Пустой/безтокенный запрос → []. Для каждого
        документа с хотя бы одним совпавшим термином считается BM25 (k1=1.5,
        b=0.75):

            score = Σ_term idf(term) · tf·(k1+1) / (tf + k1·(1 − b + b·dl/avgdl))
            idf(term) = ln(1 + (N − df + 0.5) / (df + 0.5))

        Сортировка: score DESC, ref ASC (стабильно). Каждый хит::

            {'ref', 'db', 'mfn', 'title', 'score' (round 4),
             'matched': [термины запроса, реально найденные в документе]}

        Документ без совпадений в выдачу НЕ включается.
        """
        qterms = normalize_query(query)
        if not qterms:
            return []
        # уникальные основы запроса (для idf/постингов), но matched учитываем по факту
        uniq_terms = []
        for t in qterms:
            if t not in uniq_terms:
                uniq_terms.append(t)

        postings = self.store.postings_for_terms(uniq_terms)
        if not postings:
            return []
        df = self.store.doc_freq(uniq_terms)
        tot = self.store.totals()
        N = tot['N']
        avgdl = tot['avgdl'] or 1.0

        # idf по терминам (по Okapi BM25, неотрицательно сглажен ln(1+…))
        idf = {}
        for term in uniq_terms:
            d = df.get(term, 0)
            idf[term] = math.log(1.0 + (N - d + 0.5) / (d + 0.5))

        # сгруппировать постинги по документам
        by_doc = {}  # doc_id -> {term: tf}
        for p in postings:
            by_doc.setdefault(p['doc_id'], {})[p['term']] = p['tf']

        hits = []
        for doc_id, term_tf in by_doc.items():
            dv = self.store.doc_view(doc_id)
            if dv is None:
                continue
            dl = dv['length'] or 0
            score = 0.0
            matched = []
            for term, tf in term_tf.items():
                denom = tf + _BM25_K1 * (1.0 - _BM25_B + _BM25_B * (dl / avgdl))
                score += idf.get(term, 0.0) * (tf * (_BM25_K1 + 1.0)) / denom
                matched.append(term)
            if not matched:
                continue
            # matched — в порядке появления терминов в запросе (стабильно)
            matched_ordered = [t for t in uniq_terms if t in matched]
            hits.append({
                'ref': dv['ref'],
                'db': dv['db'],
                'mfn': dv['mfn'],
                'title': dv['title'],
                'score': round(score, 4),
                'matched': matched_ordered,
                'snippet': self._snippet(dv.get('body', ''), matched_ordered),
            })

        hits.sort(key=lambda h: (-h['score'], h['ref']))
        return hits[:limit]

    def more_like(self, ref, limit=10):
        """Документы, похожие на ``ref`` (по его топ-терминам). Список хитов или [].

        Берёт топ-основы документа ``ref`` (по tf), делает по ним ``search`` и
        исключает сам ``ref`` из выдачи. Если документа нет или у него нет
        постингов → []."""
        doc = self.store.get_doc(ref)
        if doc is None:
            return []
        # достать постинги документа: все его термины с tf
        c = self.store._conn()
        ph = self.store._ph
        rows = c.execute(
            'SELECT term, tf FROM posting WHERE doc_id=(SELECT id FROM doc WHERE ref=%s)'
            % ph, (str(ref),)).fetchall()
        terms = sorted((dict(r) for r in rows), key=lambda r: (-int(r['tf']), r['term']))
        top = [r['term'] for r in terms[:10]]
        if not top:
            return []
        results = self.search(' '.join(top), limit=limit + 1)
        return [h for h in results if h['ref'] != str(ref)][:limit]
