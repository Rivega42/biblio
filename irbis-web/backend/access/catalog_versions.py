#!/usr/bin/env python3
"""CATALOG VERSIONS — история версий записи каталога + откат + дифф + дедуп-merge.

Контур **Каталогизатор**: версионирование библиографических записей (own-store
история каждой правки записи по ключу ``(db, mfn)``, откат к версии, field-level
дифф между версиями) и слияние записей-дублей (merge). Own-store: чистый stdlib +
``sqlite3`` (dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в
точности как ``pay.py``/``union.py``.

Что это
-------
  * **версии** — каждый ``snapshot`` записи фиксирует новую версию под
    ``(db, mfn)`` (номер = MAX+1); полный payload записи хранится как JSON, так
    что любую версию можно получить целиком и восстановить;
  * **откат (revert)** — чисто читающая операция: отдаёт ``record`` запрошенной
    версии; само применение (запись обратно в каталог + новый snapshot) — на
    слое каталога/маршрутов, домен версий ничего не мутирует в каталоге;
  * **дифф** — field-level сравнение двух версий по тегам:
    ``{'added', 'removed', 'changed'}``;
  * **merge** — чистая функция слияния двух записей-дублей: по каждому тегу
    выигрывает непустое значение, повторяющиеся поля объединяются без дублей.

Запись ``record`` — это НАША tag-keyed запись (как в ``catalog.py``/``union.py``):
dict полей, где поле — скаляр, ``{подполе: значение}`` или список такого.

Гранты/аудит — на слое маршрутов (``server.py`` + ``access/authz.py``); сам домен —
чистая логика над своим стором.
"""
import json
import sqlite3
import threading
import time


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS catalog_version (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  db         TEXT NOT NULL,            -- БД каталога (IBIS и т.п.)
  mfn        INTEGER NOT NULL,         -- MFN записи в этой БД
  version    INTEGER NOT NULL,         -- номер версии (1..N) в рамках (db,mfn)
  data_json  TEXT NOT NULL,            -- полный payload записи (tag-keyed dict)
  actor      TEXT,                     -- кто зафиксировал версию (логин/билет)
  created_at REAL NOT NULL,
  UNIQUE(db, mfn, version)
);
CREATE INDEX IF NOT EXISTS catalog_version_rec_idx ON catalog_version(db, mfn);
"""


class VersionStore:
    """Собственный sqlite-стор истории версий записи каталога.

    ``db_path=':memory:'`` (по умолчанию) или файл; create-on-init.
    Соединение thread-local (домашний стиль); строки — dict; payload — JSON
    (``ensure_ascii=False``, чтобы кириллица хранилась читаемо).
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

    def max_version(self, db, mfn):
        """Текущий максимальный номер версии для ``(db, mfn)`` (0, если нет)."""
        r = self._conn().execute(
            'SELECT COALESCE(MAX(version),0) AS v FROM catalog_version '
            'WHERE db=? AND mfn=?', (db, int(mfn))).fetchone()
        return int(r['v'])

    def add(self, db, mfn, version, record, actor, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO catalog_version(db,mfn,version,data_json,actor,'
            'created_at) VALUES(?,?,?,?,?,?)',
            (db, int(mfn), int(version),
             json.dumps(record, ensure_ascii=False),
             actor, created_at))
        c.commit()
        return self.get(cur.lastrowid)

    def get(self, row_id):
        r = self._conn().execute(
            'SELECT * FROM catalog_version WHERE id=?', (row_id,)).fetchone()
        return self._row(r)

    def get_version(self, db, mfn, version):
        r = self._conn().execute(
            'SELECT * FROM catalog_version WHERE db=? AND mfn=? AND version=?',
            (db, int(mfn), int(version))).fetchone()
        return self._row(r)

    def versions(self, db, mfn):
        """Все версии ``(db, mfn)`` по возрастанию номера (с payload)."""
        rows = self._conn().execute(
            'SELECT * FROM catalog_version WHERE db=? AND mfn=? '
            'ORDER BY version', (db, int(mfn))).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r):
        """sqlite-строку -> dict с распакованным ``record`` из ``data_json``."""
        if r is None:
            return None
        d = dict(r)
        d['record'] = json.loads(d['data_json'])
        return d


# --------------------------------------------------------------------------- #
# Дифф/merge — на уровне тегов записи (tag-keyed dict). Чистые функции.
# --------------------------------------------------------------------------- #
def _as_list(value):
    """Любую форму поля привести к списку инстансов (скаляр/dict/список)."""
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


def _is_empty(value):
    """Поле «пустое»? (None, пустая строка/коллекция, или dict без значений)."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    if isinstance(value, dict):
        return all(_is_empty(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return len(value) == 0 or all(_is_empty(v) for v in value)
    return False


def _norm_for_compare(value):
    """Канонизировать значение поля для сравнения/дедупа (порядок подполей не важен,
    форма скаляр/dict не путается)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def diff_records(rec_a, rec_b):
    """Field-level дифф двух tag-keyed записей.

    ``rec_a`` — «было», ``rec_b`` — «стало». Возвращает
    ``{'added': [tag], 'removed': [tag], 'changed': [tag]}`` (теги отсортированы):
      * ``added``   — тег есть в ``rec_b`` и нет (или пуст) в ``rec_a``;
      * ``removed`` — тег есть в ``rec_a`` и нет (или пуст) в ``rec_b``;
      * ``changed`` — тег непуст в обеих, но значения различаются.
    """
    a = rec_a or {}
    b = rec_b or {}
    tags = set(a) | set(b)
    added, removed, changed = [], [], []
    for tag in tags:
        ina = tag in a and not _is_empty(a[tag])
        inb = tag in b and not _is_empty(b[tag])
        if inb and not ina:
            added.append(tag)
        elif ina and not inb:
            removed.append(tag)
        elif ina and inb and _norm_for_compare(a[tag]) != _norm_for_compare(b[tag]):
            changed.append(tag)
    return {'added': sorted(added), 'removed': sorted(removed),
            'changed': sorted(changed)}


def merge(record_a, record_b):
    """Слить две записи-дубля в одну (дедупликация). Чистая функция.

    Правила по каждому тегу:
      * тег только в одной записи -> берётся как есть;
      * тег в обеих:
          - если один из них пуст -> побеждает непустой;
          - иначе значения объединяются в список ИНСТАНСОВ без дублей
            (повторяющиеся поля схлопываются: один и тот же инстанс не плодится).
            Если после объединения остался ровно один инстанс — он отдаётся
            скаляром/dict (не оборачивается в список без нужды).
    Порядок: сначала инстансы ``record_a``, затем новые из ``record_b``.
    """
    a = record_a or {}
    b = record_b or {}
    out = {}
    for tag in list(a) + [t for t in b if t not in a]:
        va = a.get(tag)
        vb = b.get(tag)
        if tag not in b or _is_empty(vb):
            out[tag] = va
            continue
        if tag not in a or _is_empty(va):
            out[tag] = vb
            continue
        # оба непустые -> объединяем инстансы без дублей
        merged = []
        seen = set()
        for inst in _as_list(va) + _as_list(vb):
            if _is_empty(inst):
                continue
            key = _norm_for_compare(inst)
            if key in seen:
                continue
            seen.add(key)
            merged.append(inst)
        out[tag] = merged[0] if len(merged) == 1 else merged
    return out


class VersionService:
    """Операции версионирования записи каталога над :class:`VersionStore`.

    Snapshot/история/получение версии/откат/дифф. ``now`` инжектируется
    (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or VersionStore(':memory:')
        self._now = now or time.time

    def snapshot(self, db, mfn, record, actor=None):
        """Зафиксировать новую версию записи под ``(db, mfn)``.

        Номер версии = текущий MAX+1 (первая версия = 1). Возвращает номер
        зафиксированной версии.
        """
        version = self.store.max_version(db, mfn) + 1
        self.store.add(db, mfn, version, record, actor, self._now())
        return version

    def history(self, db, mfn):
        """История версий ``(db, mfn)``: метаданные по возрастанию версии.

        Каждый элемент — ``{version, actor, created_at}`` (без тяжёлого payload;
        сам record берётся через :meth:`get_version`).
        """
        return [{'version': r['version'], 'actor': r['actor'],
                 'created_at': r['created_at']}
                for r in self.store.versions(db, mfn)]

    def get_version(self, db, mfn, version):
        """Запись (``record``) указанной версии ``(db, mfn)`` или ``None``."""
        row = self.store.get_version(db, mfn, version)
        return row['record'] if row else None

    def revert(self, db, mfn, version):
        """Вернуть ``record`` версии для восстановления (чисто читающее).

        Само применение (запись обратно в каталог + новый snapshot) — на слое
        каталога; домен версий ничего не мутирует. Возвращает ``record`` или
        ``None``, если версии нет.
        """
        return self.get_version(db, mfn, version)

    def diff(self, db, mfn, v1, v2):
        """Field-level дифф между версиями ``v1`` («было») и ``v2`` («стало»).

        Возвращает ``{'added', 'removed', 'changed'}`` (списки тегов). Если
        какой-то версии нет — её запись считается пустой записью.
        """
        ra = self.get_version(db, mfn, v1) or {}
        rb = self.get_version(db, mfn, v2) or {}
        return diff_records(ra, rb)
