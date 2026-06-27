#!/usr/bin/env python3
"""KKO_REPORTS — аналитика коэффициента книгообеспеченности (Кко) АРМ «Книгообеспеченность».

Отчётный слой НАД цифрами обеспеченности: расчёт коэффициента книгообеспеченности
(Кко) по дисциплинам, дефицит экземпляров (сколько докупить), своды по кафедрам,
худшие позиции и сохранение срезов «на дату». Дополняет ``access/bookprovision.py``
(его НЕ трогаем) — там учёт связки «дисциплина ↔ издание ↔ контингент», здесь —
сводная аналитика поверх итоговых чисел.

Что считаем
-----------
Коэффициент книгообеспеченности (Кко) дисциплины = число доступных экземпляров
изданий списка литературы, делённое на число студентов. Сравнивается с нормативом
(``norm_per_student`` — экз/студента, напр. 0.5). Если Кко ниже норматива — позиция
требует докомплектования; дефицит = сколько экземпляров не хватает до норматива.

Форма входной «дисциплины» (dict)
---------------------------------
::

    {'discipline': str,            # название дисциплины
     'department': str,            # кафедра
     'students': int,              # контингент (число студентов)
     'exemplars': int,            # доступных экз. изданий списка
     'norm_per_student': float}    # норматив экз/студента (порог Кко)

Большинство функций — ЧИСТЫЕ над переданными dict (как ``access/db_utils.py``),
без собственного I/O. Опционально — небольшой sqlite-стор срезов по периодам
(``KkoSnapshotStore``) в домашнем стиле (``SCHEMA_SQLITE`` / thread-local
``_conn()`` / инжектируемый ``now``). НИКАКИХ записей в живой ИРБИС.

Чистый stdlib (math, json, sqlite3, threading, time), без pip и без сети.
"""
import json
import math
import sqlite3
import threading
import time

__all__ = [
    'coefficient', 'deficit', 'status', 'discipline_provision', 'report',
    'by_department', 'worst', 'KkoSnapshotStore',
]


# --------------------------------------------------------------------------- #
# Чистые расчёты по одной дисциплине.
# --------------------------------------------------------------------------- #
def coefficient(students, exemplars):
    """Коэффициент книгообеспеченности Кко = exemplars / students (округл. до 2 знаков).

    При ``students <= 0`` возвращает ``0.0`` (деление не определено — контингента
    нет). Результат всегда ``float``."""
    students = int(students or 0)
    if students <= 0:
        return 0.0
    return round(float(exemplars or 0) / students, 2)


def deficit(students, exemplars, norm_per_student):
    """Дефицит экземпляров = сколько ещё нужно докупить до норматива.

    ``max(0, ceil(students * norm_per_student) - exemplars)``. Никогда не
    отрицательный (профицит дефицитом не считается). Возвращает ``int``."""
    required = math.ceil(int(students or 0) * float(norm_per_student or 0))
    return max(0, required - int(exemplars or 0))


def status(coefficient_value, norm_per_student):
    """Статус обеспеченности по значению Кко относительно норматива.

    ``'critical'`` если Кко == 0 (экземпляров нет совсем); ``'low'`` если
    ``0 < Кко < norm`` (ниже норматива); ``'ok'`` если ``Кко >= norm``. Порог —
    сам ``norm_per_student``."""
    coeff = float(coefficient_value or 0)
    norm = float(norm_per_student or 0)
    if coeff <= 0:
        return 'critical'
    if coeff < norm:
        return 'low'
    return 'ok'


def discipline_provision(disc):
    """Карточка обеспеченности дисциплины: исходные поля + рассчитанные.

    Добавляет к копии входного dict ключи ``coefficient`` (Кко), ``deficit``
    (сколько докупить), ``required`` (= ``ceil(students * norm)`` — сколько надо
    всего) и ``status`` (ok/low/critical). Устойчиво к отсутствию полей (нули по
    умолчанию)."""
    disc = dict(disc or {})
    students = int(disc.get('students') or 0)
    exemplars = int(disc.get('exemplars') or 0)
    norm = float(disc.get('norm_per_student') or 0)
    coeff = coefficient(students, exemplars)
    out = dict(disc)
    out['coefficient'] = coeff
    out['deficit'] = deficit(students, exemplars, norm)
    out['required'] = math.ceil(students * norm)
    out['status'] = status(coeff, norm)
    return out


# --------------------------------------------------------------------------- #
# Сводный отчёт по списку дисциплин.
# --------------------------------------------------------------------------- #
def report(disciplines):
    """Полный отчёт по списку дисциплин: карточки + агрегированная сводка.

    Возвращает dict::

        {'items': [discipline_provision(disc) для каждой дисциплины],
         'summary': {
             'disciplines': N,                 # число дисциплин
             'avg_coefficient': float,         # средний Кко (округл. до 2 знаков)
             'total_deficit': int,             # суммарный дефицит экземпляров
             'by_status': {'ok': n, 'low': n, 'critical': n},
             'students_total': int}}           # суммарный контингент

    Пустой список -> нулевая сводка (``avg_coefficient`` 0.0)."""
    disciplines = disciplines or []
    items = [discipline_provision(d) for d in disciplines]

    by_status = {'ok': 0, 'low': 0, 'critical': 0}
    total_deficit = 0
    students_total = 0
    coeff_sum = 0.0
    for it in items:
        by_status[it['status']] = by_status.get(it['status'], 0) + 1
        total_deficit += int(it['deficit'])
        students_total += int(it.get('students') or 0)
        coeff_sum += float(it['coefficient'])

    n = len(items)
    avg_coefficient = round(coeff_sum / n, 2) if n else 0.0
    return {
        'items': items,
        'summary': {
            'disciplines': n,
            'avg_coefficient': avg_coefficient,
            'total_deficit': total_deficit,
            'by_status': by_status,
            'students_total': students_total,
        },
    }


def by_department(disciplines):
    """Свод по кафедрам -> ``{department: {disciplines, avg_coefficient, total_deficit}}``.

    Группирует дисциплины по полю ``department`` и для каждой кафедры считает число
    дисциплин, средний Кко (округл. до 2 знаков) и суммарный дефицит. Дисциплины без
    кафедры попадают в группу ``''``. Пустой список -> ``{}``."""
    buckets = {}
    for d in (disciplines or []):
        prov = discipline_provision(d)
        dept = str(prov.get('department') or '')
        b = buckets.setdefault(dept, {'disciplines': 0, '_coeff_sum': 0.0,
                                      'total_deficit': 0})
        b['disciplines'] += 1
        b['_coeff_sum'] += float(prov['coefficient'])
        b['total_deficit'] += int(prov['deficit'])

    out = {}
    for dept, b in buckets.items():
        n = b['disciplines']
        out[dept] = {
            'disciplines': n,
            'avg_coefficient': round(b['_coeff_sum'] / n, 2) if n else 0.0,
            'total_deficit': b['total_deficit'],
        }
    return out


def worst(disciplines, n=5):
    """``n`` дисциплин с НАИМЕНЬШИМ Кко (худшие позиции, по возрастанию).

    Возвращает список карточек ``discipline_provision`` отсортированных по
    возрастанию ``coefficient``; тай-брейк — по названию дисциплины (стабильно,
    детерминированно). ``n`` ограничивает длину (по умолчанию 5)."""
    items = [discipline_provision(d) for d in (disciplines or [])]
    items.sort(key=lambda it: (it['coefficient'], str(it.get('discipline') or '')))
    if n is None:
        return items
    return items[:max(0, int(n))]


# --------------------------------------------------------------------------- #
# Опциональный sqlite-стор срезов по периодам («Кко на дату»).
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS kko_snapshot (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  period      TEXT NOT NULL UNIQUE,     -- метка периода среза (напр. '2026-Q2')
  report_json TEXT NOT NULL,            -- сериализованный report() (ensure_ascii=False)
  created_at  TEXT NOT NULL
);
"""


class KkoSnapshotStore:
    """Собственный sqlite-стор срезов Кко по периодам. ``:memory:`` или файл.

    Соединение thread-local (домашний стиль); ``row_factory = Row``; ``now``
    инжектируется (по умолчанию ISO-метка от ``time.time``) для детерминизма в
    тестах. Срез на период уникален (``period`` UNIQUE) — повторный ``save``
    замещает предыдущий."""

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._now = now or (lambda: str(time.time()))
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

    def save(self, period, report_dict):
        """Сохранить срез отчёта на период (UPSERT по ``period``) -> строка среза.

        ``report_dict`` сериализуется в JSON c ``ensure_ascii=False`` (кириллица
        читаемая). Повторный вызов с тем же ``period`` замещает срез и обновляет
        ``created_at``."""
        c = self._conn()
        payload = json.dumps(report_dict, ensure_ascii=False)
        created = self._now()
        c.execute(
            'INSERT INTO kko_snapshot(period, report_json, created_at) '
            'VALUES(?,?,?) '
            'ON CONFLICT(period) DO UPDATE SET '
            'report_json=excluded.report_json, created_at=excluded.created_at',
            (period, payload, created))
        c.commit()
        r = c.execute('SELECT * FROM kko_snapshot WHERE period=?',
                      (period,)).fetchone()
        return dict(r) if r else None

    def get(self, period):
        """Распарсенный отчёт среза за период или ``None``, если среза нет."""
        r = self._conn().execute(
            'SELECT report_json FROM kko_snapshot WHERE period=?',
            (period,)).fetchone()
        if r is None:
            return None
        return json.loads(r['report_json'])

    def periods(self):
        """Список периодов с сохранёнными срезами (по возрастанию метки)."""
        rows = self._conn().execute(
            'SELECT period FROM kko_snapshot ORDER BY period').fetchall()
        return [r['period'] for r in rows]
