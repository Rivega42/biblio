#!/usr/bin/env python3
"""DISCIPLINE NORMS — модель данных «дисциплина ↔ издание ↔ норматив ↔ контингент».

АРМ Книгообеспеченность (ВУЗ), слой нормативов по РПД (рабочим программам
дисциплин). Хранит учебные дисциплины с их контингентом студентов и нормативы
привязки изданий (сколько экземпляров издания требуется на одного студента),
а затем вычисляет ТРЕБУЕМОЕ число экземпляров и ДЕФИЦИТ относительно наличия.

Зачем отдельно от ``bookprovision``
-----------------------------------
``bookprovision`` — это полный движок «связки» Факультет→Направление→Спец→
Дисциплина с расчётом коэффициента Кко = экземпляры/студенты и 4-клеточной
политикой деления на ноль (SPEC E1). Он отвечает на вопрос «сколько экземпляров
ФАКТИЧЕСКИ на одного студента». Этот модуль НЕ трогает ``bookprovision`` и решает
СМЕЖНУЮ задачу — НОРМАТИВНУЮ сторону по РПД: сколько экземпляров издания ДОЛЖНО
быть (``norm_per_student``) на контингент, и каков дефицит относительно наличия.
Цифры (``required``/``deficit``/``coverage``) подаются дальше в ``kko_reports``.

Архитектура (домашний стиль, ADR-004)
-------------------------------------
Чистый stdlib + ``sqlite3``: без сети и без новых pip-зависимостей — в точности
как ``pay.py`` / ``reader_registry.py``. Соединение thread-local (``self._local``
+ :meth:`_conn`, ``row_factory=Row``); наружу — простые dict-записи. ``now``
инжектируется (по умолчанию :func:`_utcnow`, ISO8601 UTC) для детерминизма в
тестах. Никаких записей в живой ИРБИС — только собственный own-store.

Модель данных
-------------
  * ``discipline``   — учебная дисциплина: ``code`` (уникальный шифр по РПД),
    ``name``, ``department`` (кафедра), ``contingent`` (число студентов).
  * ``edition_norm`` — норматив привязки издания к дисциплине: ``edition_ref``
    (ссылка на издание — инвентарный/BBK/идентификатор каталога), ``kind``
    (``main`` основная / ``extra`` дополнительная), ``norm_per_student`` (норма
    экземпляров на одного студента). Уникален по (дисциплина, издание).

Расчёт
------
Для каждого издания дисциплины::

    required = ceil(contingent * norm_per_student)   (math.ceil, округление вверх)
    deficit  = max(0, required - available)          (available — из available_map)
    coverage = Σ min(available, required) / Σ required по дисциплине

При отсутствии нормативов (``Σ required == 0``) покрытие считается полным
(``coverage == 1.0`` — требовать нечего, значит всё обеспечено).
"""
import math
import sqlite3
import threading
from datetime import datetime, timezone

# Виды литературы по нормативу (как в bookprovision: 691^G Осн/Доп).
KIND_MAIN = 'main'    # основная литература
KIND_EXTRA = 'extra'  # дополнительная литература


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS discipline (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  code       TEXT NOT NULL UNIQUE,        -- шифр дисциплины по РПД
  name       TEXT NOT NULL DEFAULT '',
  department TEXT NOT NULL DEFAULT '',    -- кафедра
  contingent INTEGER NOT NULL DEFAULT 0,  -- число студентов
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS edition_norm (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  discipline_id    INTEGER NOT NULL,
  edition_ref      TEXT NOT NULL,         -- ссылка на издание (инв./BBK/идентификатор)
  kind             TEXT NOT NULL DEFAULT 'main',  -- main | extra
  norm_per_student REAL NOT NULL DEFAULT 0,        -- экземпляров на студента
  UNIQUE(discipline_id, edition_ref)
);
CREATE INDEX IF NOT EXISTS edition_norm_disc_idx ON edition_norm(discipline_id);
"""


class DisciplineStore:
    """Собственный sqlite-стор дисциплин и нормативов изданий. ``:memory:`` или
    файл; create-on-init. Соединение thread-local (домашний стиль); строки — dict.

    ``now`` инжектируется (по умолчанию :func:`_utcnow`, ISO8601) для детерминизма
    в тестах — пишется в ``discipline.updated_at`` при upsert/изменении контингента.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._now = now or _utcnow
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

    # ---- дисциплины ---- #
    def upsert_discipline(self, code, name='', department='', contingent=0):
        """Идемпотентно завести/обновить дисциплину по ``code``.

        Повторный upsert того же шифра обновляет наименование, кафедру и
        контингент (и ``updated_at``), не создавая дубль. Возвращает строку-dict."""
        now = self._now()
        existing = self.get_discipline(code)
        c = self._conn()
        if existing is None:
            c.execute(
                'INSERT INTO discipline(code,name,department,contingent,updated_at) '
                'VALUES(?,?,?,?,?)',
                (str(code), name, department, max(0, int(contingent or 0)), now))
        else:
            c.execute(
                'UPDATE discipline SET name=?,department=?,contingent=?,updated_at=? '
                'WHERE code=?',
                (name, department, max(0, int(contingent or 0)), now, str(code)))
        c.commit()
        return self.get_discipline(code)

    def get_discipline(self, code):
        """Дисциплина по шифру (``code``) -> dict | None."""
        r = self._conn().execute(
            'SELECT * FROM discipline WHERE code=?', (str(code),)).fetchone()
        return dict(r) if r else None

    def list_disciplines(self):
        """Все дисциплины (в порядке id) -> list[dict]."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM discipline ORDER BY id').fetchall()]

    def set_contingent(self, code, contingent):
        """Обновить контингент дисциплины. -> dict | None (None, если нет такой)."""
        if self.get_discipline(code) is None:
            return None
        c = self._conn()
        c.execute(
            'UPDATE discipline SET contingent=?,updated_at=? WHERE code=?',
            (max(0, int(contingent or 0)), self._now(), str(code)))
        c.commit()
        return self.get_discipline(code)

    # ---- нормативы изданий ---- #
    def add_norm(self, discipline_id, edition_ref, kind=KIND_MAIN,
                 norm_per_student=0.0):
        """Идемпотентно завести/обновить норматив издания (upsert на
        (discipline_id, edition_ref)). Повтор обновляет ``kind`` и норму.
        Возвращает строку-dict норматива."""
        c = self._conn()
        existing = self._conn().execute(
            'SELECT id FROM edition_norm WHERE discipline_id=? AND edition_ref=?',
            (discipline_id, str(edition_ref))).fetchone()
        if existing is None:
            c.execute(
                'INSERT INTO edition_norm'
                '(discipline_id,edition_ref,kind,norm_per_student) VALUES(?,?,?,?)',
                (discipline_id, str(edition_ref), kind,
                 float(norm_per_student or 0.0)))
        else:
            c.execute(
                'UPDATE edition_norm SET kind=?,norm_per_student=? WHERE id=?',
                (kind, float(norm_per_student or 0.0), existing['id']))
        c.commit()
        r = self._conn().execute(
            'SELECT * FROM edition_norm WHERE discipline_id=? AND edition_ref=?',
            (discipline_id, str(edition_ref))).fetchone()
        return dict(r) if r else None

    def norms(self, discipline_id):
        """Нормативы изданий дисциплины (в порядке id) -> list[dict]."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM edition_norm WHERE discipline_id=? ORDER BY id',
            (discipline_id,)).fetchall()]

    def remove_norm(self, discipline_id, edition_ref):
        """Снять норматив издания с дисциплины. -> True, если запись была."""
        c = self._conn()
        cur = c.execute(
            'DELETE FROM edition_norm WHERE discipline_id=? AND edition_ref=?',
            (discipline_id, str(edition_ref)))
        c.commit()
        return cur.rowcount > 0


class DisciplineNormService:
    """Сервис над :class:`DisciplineStore` — нормативная сторона книгообеспеченности.

    Резолвит дисциплины по шифру (``code``), считает требуемое число экземпляров
    (``required = ceil(contingent * norm)``), дефицит (``max(0, required -
    available)``) и покрытие (``coverage``) относительно карты наличия
    ``available_map`` ({edition_ref: int}). Числа подаются в ``kko_reports``.
    """

    def __init__(self, store=None, now=None):
        self.store = store or DisciplineStore(':memory:', now=now)

    # ---- ведение дисциплин и нормативов ---- #
    def add_discipline(self, code, name, department='', contingent=0):
        """Завести/обновить дисциплину (идемпотентно по ``code``) -> dict."""
        return self.store.upsert_discipline(
            code, name=name, department=department, contingent=contingent)

    def set_contingent(self, discipline_code, contingent):
        """Обновить контингент дисциплины по шифру -> dict | None."""
        return self.store.set_contingent(discipline_code, contingent)

    def set_norm(self, discipline_code, edition_ref, norm_per_student,
                 kind=KIND_MAIN):
        """Задать норматив привязки издания к дисциплине (по её шифру).

        Резолвит дисциплину по ``code``; неизвестная дисциплина -> ``ValueError``.
        Upsert по (дисциплина, издание): повтор обновляет норму/вид. -> dict."""
        disc = self.store.get_discipline(discipline_code)
        if disc is None:
            raise ValueError('unknown discipline code: %r' % (discipline_code,))
        return self.store.add_norm(
            disc['id'], edition_ref, kind=kind,
            norm_per_student=norm_per_student)

    # ---- расчёт требуемого / дефицита / покрытия ---- #
    def required_copies(self, discipline_code):
        """Требуемое число экземпляров по каждому изданию дисциплины.

        Для каждого норматива: ``required = ceil(contingent * norm_per_student)``
        (округление вверх, :func:`math.ceil`). Неизвестная дисциплина -> ``[]``.
        Возвращает list per edition:
        ``[{'edition_ref','kind','norm_per_student','required'}]``."""
        disc = self.store.get_discipline(discipline_code)
        if disc is None:
            return []
        contingent = max(0, int(disc['contingent'] or 0))
        out = []
        for n in self.store.norms(disc['id']):
            norm = float(n['norm_per_student'] or 0.0)
            out.append({
                'edition_ref': n['edition_ref'],
                'kind': n['kind'],
                'norm_per_student': norm,
                'required': math.ceil(contingent * norm),
            })
        return out

    def total_required(self, discipline_code):
        """Суммарное требуемое число экземпляров по всем изданиям дисциплины -> int."""
        return sum(item['required']
                   for item in self.required_copies(discipline_code))

    def need(self, discipline_code, available_map):
        """Потребность по каждому изданию с учётом наличия (``available_map``).

        К каждой строке :meth:`required_copies` добавляет ``available``
        (``available_map.get(edition_ref, 0)``) и ``deficit``
        (``max(0, required - available)``). ``available_map`` — dict
        {edition_ref: int}. Неизвестная дисциплина -> ``[]``."""
        available_map = available_map or {}
        out = []
        for item in self.required_copies(discipline_code):
            available = max(0, int(available_map.get(item['edition_ref'], 0) or 0))
            row = dict(item)
            row['available'] = available
            row['deficit'] = max(0, item['required'] - available)
            out.append(row)
        return out

    def coverage(self, discipline_code, available_map):
        """Доля покрытия дисциплины наличием -> float (2 знака после запятой).

        ``coverage = Σ min(available, required) / Σ required`` по всем изданиям
        дисциплины. При ``Σ required == 0`` (нормативов нет / нулевые нормы)
        возвращает ``1.0`` — требовать нечего, значит покрыто полностью."""
        available_map = available_map or {}
        total_required = 0
        total_covered = 0
        for item in self.required_copies(discipline_code):
            required = item['required']
            available = max(0, int(available_map.get(item['edition_ref'], 0) or 0))
            total_required += required
            total_covered += min(available, required)
        if total_required == 0:
            return 1.0
        return round(total_covered / total_required, 2)
