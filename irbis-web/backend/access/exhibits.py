#!/usr/bin/env python3
"""EXHIBITS — виртуальные выставки (трек «Оцифровка»).

Кураторские подборки записей каталога и оцифрованных образов (assets): к каждой
выставке прикрепляются позиции (запись ``db``/``mfn`` + опциональная ссылка на
образ ``asset_ref`` + подпись), у позиций задаётся порядок (``sort``), а сама
выставка может быть опубликована (публичная витрина) либо скрыта (черновик).

Own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без
новых pip-зависимостей — в точности как ``pay.py``/``reader_registry.py``. Никаких
записей в живой ИРБИС: выставка — это надстройка-витрина над каталогом, она лишь
ССЫЛАЕТСЯ на записи (``db``/``mfn``) и образы DAM/IIIF, ничего в них не меняя.

Зачем отдельным стором
----------------------
Каталожная запись и её оцифрованные образы — это первичные данные. Выставка —
кураторский АРТЕФАКТ поверх них: один и тот же образ может попасть в несколько
выставок с разной подписью и в разном порядке. Поэтому подборка хранится отдельно
(``exhibit`` + ``exhibit_item``), а не «зашивается» в каталог.

Структура
---------
  * ``exhibit``      — выставка: ``slug`` (уникальный человекочитаемый ключ для
    URL витрины), ``title``, ``description``, флаг ``published``, метки времени;
  * ``exhibit_item`` — позиция выставки: ссылка на запись (``db``/``mfn``),
    опциональная ссылка на образ (``asset_ref``), подпись (``caption``) и порядок
    показа (``sort``).
"""
import sqlite3
import threading
from datetime import datetime, timezone


def _utcnow():
    """Текущее время UTC в ISO8601 (инжектируемые часы по умолчанию)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS exhibit (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  slug        TEXT NOT NULL UNIQUE,      -- человекочитаемый ключ витрины (URL)
  title       TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  published   INTEGER NOT NULL DEFAULT 0,  -- 0 черновик | 1 опубликовано
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exhibit_item (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  exhibit_id  INTEGER NOT NULL,         -- FK -> exhibit.id
  db          TEXT NOT NULL,            -- база каталога (напр. IBIS)
  mfn         INTEGER NOT NULL,         -- MFN записи в базе
  asset_ref   TEXT NOT NULL DEFAULT '', -- ссылка на оцифрованный образ (DAM/IIIF)
  caption     TEXT NOT NULL DEFAULT '', -- кураторская подпись
  sort        INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS exhibit_item_exhibit_idx ON exhibit_item(exhibit_id);
"""


class ExhibitStore:
    """Собственный sqlite-стор выставок и их позиций. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict."""

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

    # -- exhibit ----------------------------------------------------------

    def create_exhibit(self, slug, title, description=''):
        """Создать выставку (черновик). Дубликат ``slug`` -> sqlite IntegrityError."""
        ts = self._now()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO exhibit(slug,title,description,published,'
            'created_at,updated_at) VALUES(?,?,?,0,?,?)',
            (slug, title, description or '', ts, ts))
        c.commit()
        return self.get_by_id(cur.lastrowid)

    def get_exhibit(self, slug):
        """Выставка по ``slug`` или ``None``."""
        r = self._conn().execute(
            'SELECT * FROM exhibit WHERE slug=?', (slug,)).fetchone()
        return dict(r) if r else None

    def get_by_id(self, exhibit_id):
        """Выставка по ``id`` или ``None``."""
        r = self._conn().execute(
            'SELECT * FROM exhibit WHERE id=?', (exhibit_id,)).fetchone()
        return dict(r) if r else None

    def list_exhibits(self, published_only=False):
        """Список выставок (все или только опубликованные), по ``id``."""
        if published_only:
            rows = self._conn().execute(
                'SELECT * FROM exhibit WHERE published=1 ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM exhibit ORDER BY id').fetchall()
        return [dict(r) for r in rows]

    def set_published(self, slug, published):
        """Переключить флаг публикации выставки. Возвращает строку или ``None``."""
        ts = self._now()
        c = self._conn()
        c.execute('UPDATE exhibit SET published=?,updated_at=? WHERE slug=?',
                  (1 if published else 0, ts, slug))
        c.commit()
        return self.get_exhibit(slug)

    # -- exhibit_item -----------------------------------------------------

    def add_item(self, exhibit_id, db, mfn, asset_ref='', caption='', sort=0):
        """Добавить позицию в выставку. Возвращает строку позиции."""
        ts = self._now()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO exhibit_item(exhibit_id,db,mfn,asset_ref,caption,'
            'sort,created_at) VALUES(?,?,?,?,?,?,?)',
            (exhibit_id, db, int(mfn), asset_ref or '', caption or '',
             int(sort), ts))
        c.commit()
        return self._item(cur.lastrowid)

    def _item(self, item_id):
        r = self._conn().execute(
            'SELECT * FROM exhibit_item WHERE id=?', (item_id,)).fetchone()
        return dict(r) if r else None

    def items(self, exhibit_id):
        """Позиции выставки по возрастанию ``sort`` (затем ``id``)."""
        rows = self._conn().execute(
            'SELECT * FROM exhibit_item WHERE exhibit_id=? '
            'ORDER BY sort, id', (exhibit_id,)).fetchall()
        return [dict(r) for r in rows]

    def remove_item(self, item_id):
        """Удалить позицию по ``id``. ``True`` если что-то удалено."""
        c = self._conn()
        cur = c.execute('DELETE FROM exhibit_item WHERE id=?', (item_id,))
        c.commit()
        return cur.rowcount > 0

    def set_item_sort(self, item_id, sort):
        """Переустановить ``sort`` у позиции."""
        c = self._conn()
        c.execute('UPDATE exhibit_item SET sort=? WHERE id=?',
                  (int(sort), item_id))
        c.commit()

    def max_sort(self, exhibit_id):
        """Максимальный ``sort`` среди позиций выставки (или ``0``, если пусто)."""
        r = self._conn().execute(
            'SELECT COALESCE(MAX(sort),0) AS m FROM exhibit_item '
            'WHERE exhibit_id=?', (exhibit_id,)).fetchone()
        return int(r['m']) if r else 0


class ExhibitService:
    """Операции над :class:`ExhibitStore` — кураторский сервис выставок.

    ``now`` инжектируется через стор (``_utcnow`` по умолчанию, ISO8601) для
    детерминизма в тестах. Никаких записей в живой ИРБИС: сервис лишь хранит
    кураторские подборки-ссылки на каталожные записи и образы.
    """

    def __init__(self, store=None, now=None):
        self.store = store or ExhibitStore(':memory:', now=now)

    def ensure_schema(self):
        """Гарантировать наличие схемы (делегирует стору)."""
        self.store.ensure_schema()

    def create(self, slug, title, description=''):
        """Создать выставку (черновик). Дубликат ``slug`` -> ``ValueError``."""
        if self.store.get_exhibit(slug) is not None:
            raise ValueError('exhibit slug already exists: %r' % (slug,))
        try:
            return self.store.create_exhibit(slug, title, description)
        except sqlite3.IntegrityError:
            raise ValueError('exhibit slug already exists: %r' % (slug,))

    def get(self, slug):
        """Выставка по ``slug`` или ``None``."""
        return self.store.get_exhibit(slug)

    def add_record(self, slug, db, mfn, caption='', asset_ref=''):
        """Добавить запись/образ в выставку (``sort`` = max+1).

        Неизвестный ``slug`` -> ``ValueError``. Возвращает строку позиции."""
        ex = self.store.get_exhibit(slug)
        if ex is None:
            raise ValueError('unknown exhibit slug: %r' % (slug,))
        nxt = self.store.max_sort(ex['id']) + 1
        return self.store.add_item(ex['id'], db, mfn, asset_ref=asset_ref,
                                   caption=caption, sort=nxt)

    def reorder(self, slug, item_ids):
        """Переустановить ``sort`` позиций по порядку ``item_ids`` (с 1).

        Неизвестный ``slug`` -> ``ValueError``. Возвращает позиции в новом
        порядке. Позиции, не попавшие в ``item_ids``, остаются как есть."""
        ex = self.store.get_exhibit(slug)
        if ex is None:
            raise ValueError('unknown exhibit slug: %r' % (slug,))
        for pos, item_id in enumerate(item_ids, start=1):
            self.store.set_item_sort(item_id, pos)
        return self.store.items(ex['id'])

    def publish(self, slug):
        """Опубликовать выставку (показать на витрине)."""
        return self.store.set_published(slug, True)

    def unpublish(self, slug):
        """Снять выставку с публикации (вернуть в черновики)."""
        return self.store.set_published(slug, False)

    def public_exhibits(self):
        """Только опубликованные выставки (для публичной витрины)."""
        return self.store.list_exhibits(published_only=True)

    def list(self, published_only=False):
        """Список выставок (все или только опубликованные)."""
        return self.store.list_exhibits(published_only=published_only)

    def view(self, slug):
        """Развёрнутый вид выставки -> ``{'exhibit':..., 'items':[...]}``.

        Позиции — по возрастанию ``sort``. Неизвестный ``slug`` -> ``None``."""
        ex = self.store.get_exhibit(slug)
        if ex is None:
            return None
        return {'exhibit': ex, 'items': self.store.items(ex['id'])}

    def remove(self, slug, item_id):
        """Удалить позицию ``item_id`` из выставки ``slug``.

        ``True`` если позиция принадлежала выставке и была удалена."""
        ex = self.store.get_exhibit(slug)
        if ex is None:
            return False
        row = self.store._item(item_id)
        if row is None or row['exhibit_id'] != ex['id']:
            return False
        return self.store.remove_item(item_id)
