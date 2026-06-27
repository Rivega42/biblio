#!/usr/bin/env python3
"""КСУ «Пополнение записи» — авто-распределение партии (ребро INTEGRATION_MAP 5.3).

Аналог внешнего ИРБИС-«Мастера» «Пополнение записи КСУ»: на записи КСУ (920=KSU)
он раскладывает поступившую партию по числам наименований (поля **17/18/19**),
направлениям/разделам (**44–49**) и печатным/непечатным (**145–150**). Точный
алгоритм этих авточисел в desktop-ИРБИС лежал во внешнем `.gbl`/`.pft`-коде и в
recon не транскрибирован (TODO #CMPL-05 в ``acquisition.py``) — здесь честная
СОБСТВЕННАЯ модель распределения: считаем сводку по строкам партии явно и
тестируемо, own-store (чистый stdlib + ``sqlite3``, dev-паритет, ADR-004), без
сети и без новых pip-зависимостей — как ``pay.py``/``acquisition.py``/``devices.py``.

Зачем отдельный модуль (НЕ редактируем ``acquisition.py``)
---------------------------------------------------------
``acquisition.py`` несёт КСУ-СУММАТОР партии (88^E/^F/^G наименований/экземпляров/
сумма) на приёме поступления. Здесь — следующий шаг КСУ-учёта: РАСПРЕДЕЛЕНИЕ той же
партии по разделам/типам/языкам/печатности (поля 17/18/19/44–49/145–150). Это
чистая агрегирующая модель над описанием строк партии, поэтому живёт отдельно —
не трогая lifecycle комплектования.

Карта полей (recon DB_ACQUISITION A.3.1/A.4, та же, что ``KSU_DISTRIBUTION_FIELDS``)::

    17        число наименований (поступило)        -> titles
    18/19     членение числа наименований           -> printed/non_printed titles
    44–49     распределение по разделам             -> by_section (titles/copies)
    145–150   печатные / непечатные                 -> printed / non_printed
    (тип/язык) by_type / by_language               -> сводка для 45 «по типу/языку»

Модель строки партии (вход :func:`distribute`)::

    {'section': str,      # раздел/направление (44–49 / 151)
     'doc_type': str,     # тип документа (книга / период. / эл.ресурс …)
     'language': str,     # язык (101)
     'printed': bool,     # печатный (True) / непечатный (False) — 145–150
     'copies': int}       # экземпляров этого наименования в партии

Одна строка == одно НАИМЕНОВАНИЕ (поле 17 = число строк); ``copies`` — экземпляры
этого наименования. Сводка агрегирует наименования и экземпляры по каждой грани.
"""
import json
import sqlite3
import threading
import time

# Поля КСУ-распределения (recon A.3.1/A.4), которые заполняет «Пополнение записи».
# Совпадает с acquisition.KSU_DISTRIBUTION_FIELDS — дублируем здесь как локальную
# карту-документацию грани 5.3 (модуль самодостаточен, без импорта acquisition).
KSU_DISTRIBUTION_FIELDS = {
    '17': 'число наименований (поступило)',           # titles
    '18': 'число наименований печатных',              # printed titles
    '19': 'число наименований непечатных',            # non-printed titles
    '44': 'распределение по разделам',                # by_section
    '45': 'по типу/языку',                            # by_type / by_language
    '46': 'распределение по разделам',
    '47': 'распределение по разделам',
    '48': 'УДК',
    '49': 'ББК',
    '145': 'печатные',                                # printed
    '146': 'непечатные',                              # non_printed
    '147': 'характер',
    '148': 'фонды',
    '149': 'канал',
    '150': 'прочее',
}

# Ключ грани, под который агрегируется строка, если её атрибут пуст. Пустой раздел/
# тип/язык не теряем — собираем в явную корзину, чтобы Σ корзин == titles/copies.
UNSPECIFIED = '(не указано)'


def _bucket_key(value):
    """Нормализовать атрибут грани в ключ-корзину (пустое -> :data:`UNSPECIFIED`)."""
    s = str(value or '').strip()
    return s if s else UNSPECIFIED


def distribute(items):
    """Свести строки партии ``items`` в сводку КСУ-распределения (ребро 5.3).

    ``items`` — список строк-наименований
    ``[{'section','doc_type','language','printed','copies'}, ...]``. Каждая строка
    == одно НАИМЕНОВАНИЕ (поле 17), ``copies`` — экземпляров этого наименования.

    Возвращает сводку::

        {'titles': N,                 # число наименований (поле 17) == len(items)
         'copies': total_copies,      # Σ экземпляров
         'by_section':  {section:  {'titles':, 'copies':}},   # 44–49
         'by_type':     {doc_type: {'titles':, 'copies':}},   # 45
         'by_language': {language: {'titles':, 'copies':}},   # 45
         'printed':     {'titles':, 'copies':},               # 145 / 18
         'non_printed': {'titles':, 'copies':}}               # 146 / 19

    Инварианты (проверяемы): ``titles == len(items)``; ``copies`` == Σ copies;
    Σ titles/copies по любой из граней (section/type/language) и по printed+non_printed
    равны общим titles/copies. Пустой список -> все счётчики нули.
    """
    summary = {
        'titles': 0,
        'copies': 0,
        'by_section': {},
        'by_type': {},
        'by_language': {},
        'printed': {'titles': 0, 'copies': 0},
        'non_printed': {'titles': 0, 'copies': 0},
    }
    for item in items or ():
        copies = int(item.get('copies') or 0)
        summary['titles'] += 1
        summary['copies'] += copies
        _accumulate(summary['by_section'], _bucket_key(item.get('section')), copies)
        _accumulate(summary['by_type'], _bucket_key(item.get('doc_type')), copies)
        _accumulate(summary['by_language'], _bucket_key(item.get('language')),
                    copies)
        bucket = 'printed' if item.get('printed', True) else 'non_printed'
        summary[bucket]['titles'] += 1
        summary[bucket]['copies'] += copies
    return summary


def _accumulate(facet, key, copies):
    """Прибавить одно наименование (+``copies`` экз.) в корзину ``key`` грани ``facet``."""
    cell = facet.get(key)
    if cell is None:
        cell = {'titles': 0, 'copies': 0}
        facet[key] = cell
    cell['titles'] += 1
    cell['copies'] += copies


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS ksu_distribution (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ksu_no       TEXT NOT NULL UNIQUE,     -- № КСУ (88^A / KSU=), ключ снимка
  payload_json TEXT NOT NULL,            -- сводка distribute(), JSON
  created_at   REAL NOT NULL
);
"""


class KsuAutoStore:
    """Собственный sqlite-стор снимков КСУ-распределения по номеру КСУ.

    ``:memory:`` (по умолчанию) или файл; create-on-init. Соединение thread-local
    (домашний стиль); строки — dict. Снимок persist-ится по ``ksu_no`` (UNIQUE) —
    повтор обновляет (идемпотентность по номеру КСУ).
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

    def upsert(self, ksu_no, summary, created_at):
        """Сохранить/обновить снимок распределения по ``ksu_no`` (идемпотентно).

        Первый вызов вставляет строку; повтор по тому же ``ksu_no`` ПЕРЕЗАПИСЫВАЕТ
        payload и ``created_at`` (снимок отражает последний расчёт). Возвращает
        сохранённый снимок-строку (dict)."""
        payload = json.dumps(summary, ensure_ascii=False)
        c = self._conn()
        existing = self.get(ksu_no)
        if existing is None:
            c.execute(
                'INSERT INTO ksu_distribution(ksu_no,payload_json,created_at) '
                'VALUES(?,?,?)', (ksu_no, payload, created_at))
        else:
            c.execute(
                'UPDATE ksu_distribution SET payload_json=?, created_at=? '
                'WHERE ksu_no=?', (payload, created_at, ksu_no))
        c.commit()
        return self.get(ksu_no)

    def get(self, ksu_no):
        """Снимок распределения по ``ksu_no`` -> dict ``{ksu_no, distribution,
        created_at}`` или ``None``."""
        r = self._conn().execute(
            'SELECT * FROM ksu_distribution WHERE ksu_no=?', (ksu_no,)).fetchone()
        if r is None:
            return None
        return {'ksu_no': r['ksu_no'],
                'distribution': json.loads(r['payload_json']),
                'created_at': r['created_at']}

    def list_ksu(self):
        """Номера КСУ всех сохранённых снимков (в порядке создания)."""
        return [r['ksu_no'] for r in self._conn().execute(
            'SELECT ksu_no FROM ksu_distribution ORDER BY id').fetchall()]


class KsuAutoService:
    """Сервис КСУ-распределения над :class:`KsuAutoStore` (ребро 5.3).

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    ``compute`` — чистый расчёт без записи; ``compute_and_store`` — расчёт + persist
    снимка по ``ksu_no`` (идемпотентно).
    """

    def __init__(self, store=None, now=None):
        self.store = store or KsuAutoStore(':memory:')
        self._now = now or time.time

    def compute(self, items):
        """Посчитать сводку распределения партии (БЕЗ записи) -> :func:`distribute`."""
        return distribute(items)

    def compute_and_store(self, ksu_no, items):
        """Посчитать распределение партии и сохранить снимок по ``ksu_no``.

        Идемпотентно по ``ksu_no``: повторный вызов с тем же номером ОБНОВЛЯЕТ
        снимок (не плодит строк). Возвращает сводку (как :meth:`compute`)."""
        summary = distribute(items)
        self.store.upsert(ksu_no, summary, self._now())
        return summary

    def get(self, ksu_no):
        """Сохранённый снимок распределения по ``ksu_no`` или ``None``."""
        return self.store.get(ksu_no)

    def list_ksu(self):
        """Номера КСУ всех сохранённых снимков."""
        return self.store.list_ksu()
