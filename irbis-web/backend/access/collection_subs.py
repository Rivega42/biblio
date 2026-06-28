#!/usr/bin/env python3
"""COLLECTION_SUBS — собственный реестр TIME-BOXED ПОДПИСОК читателя на
коллекции / выставки / отдельные записи каталога (контур читателя; эпик #240).

Назначение
----------
Читатель оформляет подписку на ЦЕЛЬ (коллекцию, выставку или запись каталога)
на интервал дат ``[date_from .. date_to]``. Пока интервал АКТИВЕН на текущую
дату — подписка surface-ится (показывается в личном кабинете / витрине). Любая
из границ интервала может быть открытой (``None``): открытое начало означает
«активна с самого начала», открытый конец — «активна бессрочно».

Реализация own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без
сети и без новых pip-зависимостей — в точности как ``debtors.py`` /
``pay.py`` / ``reader_registry.py``. В живой ИРБИС НЕ пишем.

Чем отличается от ``subscription.py``
-------------------------------------
``subscription.py`` — это подписка на ПЕРИОДИКУ (комплектование/выписка
журналов и газет). **COLLECTION_SUBS** — совсем другой слой: личная подписка
ЧИТАТЕЛЯ на коллекцию/выставку/запись с ограничением по датам. Общего кода и
таблиц нет.

Даты
----
Даты — строки ISO8601 ``YYYY-MM-DD`` (или ``None`` = открытая граница).
Сравнение дат лексикографическое: для формата ``YYYY-MM-DD`` оно совпадает с
календарным порядком, поэтому ``datetime`` для проверки активности не нужен.
"""
import sqlite3
import threading
from datetime import datetime, timezone

# Допустимые виды цели подписки.
KIND_COLLECTION = 'collection'  # коллекция (тематическое собрание записей)
KIND_EXHIBIT = 'exhibit'        # виртуальная/физическая выставка
KIND_RECORD = 'record'          # отдельная запись каталога
VALID_KINDS = (KIND_COLLECTION, KIND_EXHIBIT, KIND_RECORD)


def _utcnow():
    """Текущий момент в ISO8601 (UTC, без долей секунды) — дефолтный ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS collection_sub (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  reader      TEXT NOT NULL,            -- RI= билет читателя-подписчика
  target_kind TEXT NOT NULL,            -- collection | exhibit | record
  target_ref  TEXT NOT NULL,            -- идентификатор цели (id коллекции/записи)
  date_from   TEXT,                     -- ISO YYYY-MM-DD или NULL (открытое начало)
  date_to     TEXT,                     -- ISO YYYY-MM-DD или NULL (открытый конец)
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS collection_sub_reader_idx ON collection_sub(reader);
"""


class CollectionSubStore:
    """Собственный sqlite-стор подписок читателя на коллекции/записи.

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки возвращаются как ``dict``.
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

    # -- запись ---------------------------------------------------------------

    def add(self, reader, target_kind, target_ref, date_from, date_to):
        """Завести подписку; возвращает строку-dict.

        ``date_from`` / ``date_to`` принимают ``None`` (открытая граница)."""
        c = self._conn()
        cur = c.execute(
            'INSERT INTO collection_sub(reader,target_kind,target_ref,'
            'date_from,date_to,created_at) VALUES(?,?,?,?,?,?)',
            (reader, target_kind, target_ref, date_from, date_to, self._now()))
        c.commit()
        return self.get(cur.lastrowid)

    # -- чтение ---------------------------------------------------------------

    def get(self, sub_id):
        r = self._conn().execute(
            'SELECT * FROM collection_sub WHERE id=?', (sub_id,)).fetchone()
        return dict(r) if r else None

    def for_reader(self, reader):
        """Все подписки читателя в хронологическом порядке (created_at / id)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM collection_sub WHERE reader=? '
            'ORDER BY created_at, id', (reader,)).fetchall()]

    # -- удаление -------------------------------------------------------------

    def remove(self, sub_id):
        """Удалить подписку по id; ``True`` если строка была и удалена."""
        c = self._conn()
        cur = c.execute('DELETE FROM collection_sub WHERE id=?', (sub_id,))
        c.commit()
        return cur.rowcount > 0

    def remove_for(self, reader, sub_id):
        """Удалить подписку, ТОЛЬКО если она принадлежит ``reader``.

        ``True`` если строка была удалена; чужую/несуществующую не трогает."""
        c = self._conn()
        cur = c.execute(
            'DELETE FROM collection_sub WHERE id=? AND reader=?',
            (sub_id, reader))
        c.commit()
        return cur.rowcount > 0


class CollectionSubscriptionService:
    """Прикладной слой подписок над :class:`CollectionSubStore`.

    Валидирует ввод, считает активность подписки по окну дат, выдаёт списки и
    отменяет подписки. ``now`` инжектируется (:func:`_utcnow` по умолчанию) для
    детерминизма в тестах; ``store`` тоже инжектируется (``:memory:`` по
    умолчанию).
    """

    def __init__(self, store=None, now=None):
        self._now = now or _utcnow
        self.store = store or CollectionSubStore(':memory:', now=self._now)

    # -- валидация ------------------------------------------------------------

    @staticmethod
    def _check_date(value):
        """Проверить формат границы: ``None`` или строка ``YYYY-MM-DD`` (len 10).

        Базовая проверка формата (длина + позиции дефисов); при нарушении —
        ``ValueError``."""
        if value is None:
            return None
        if not isinstance(value, str) or len(value) != 10 \
                or value[4] != '-' or value[7] != '-':
            raise ValueError('некорректный формат даты (ожидается YYYY-MM-DD): '
                             '%r' % (value,))
        return value

    # -- подписка -------------------------------------------------------------

    def subscribe(self, reader, kind, ref, date_from=None, date_to=None):
        """Оформить подписку читателя на цель ``kind``/``ref`` на окно дат.

        Валидация: ``reader`` непуст, ``kind in VALID_KINDS``, ``ref`` непуст;
        ``date_from`` / ``date_to`` — ``None`` или ``YYYY-MM-DD``. Иначе
        ``ValueError``. Возвращает строку-dict созданной подписки."""
        if not reader:
            raise ValueError('пустой reader (билет читателя)')
        if kind not in VALID_KINDS:
            raise ValueError('недопустимый вид цели: %r (ожидается %s)'
                             % (kind, ', '.join(VALID_KINDS)))
        if not ref:
            raise ValueError('пустой ref (идентификатор цели)')
        date_from = self._check_date(date_from)
        date_to = self._check_date(date_to)
        return self.store.add(reader, kind, ref, date_from, date_to)

    # -- запросы --------------------------------------------------------------

    def list(self, reader):
        """Все подписки читателя (хронологически)."""
        return self.store.for_reader(reader)

    def active(self, reader, at=None):
        """Подписки читателя, АКТИВНЫЕ на дату ``at`` (строка ``YYYY-MM-DD``).

        Если ``at`` не задан — берётся текущая дата из инжектируемого ``now``
        (первые 10 символов ISO-момента). Подписка активна, если
        ``(date_from is None или date_from <= at)`` И
        ``(date_to is None или at <= date_to)``. Сравнение лексикографическое
        (корректно для ``YYYY-MM-DD``). Границы включительны."""
        if at is None:
            at = self._now()[:10]
        result = []
        for sub in self.store.for_reader(reader):
            df = sub['date_from']
            dt = sub['date_to']
            if (df is None or df <= at) and (dt is None or at <= dt):
                result.append(sub)
        return result

    # -- отмена ---------------------------------------------------------------

    def cancel(self, reader, sub_id):
        """Отменить СВОЮ подписку по id -> ``bool`` (удалена ли).

        Чужую подписку не трогает (вернёт ``False``)."""
        return self.store.remove_for(reader, sub_id)
