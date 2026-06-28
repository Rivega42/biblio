#!/usr/bin/env python3
"""ИНФОРОСТ — коннектор импорта оцифрованного наследия (трек «Оцифровка», эпик #240).

inforost.org — внешняя CMS оцифрованного наследия (коллекции образов: афиши,
рукописи, фотодокументы и т. п.). Это ИСТОЧНИК импорта оцифровки в Biblio: с его
стороны выгружается экспорт (коллекции -> позиции -> страницы-образы), а наш
коннектор переводит эту форму в каталожные tag-keyed записи Biblio и в
выставка-форму витрины, ведя собственный журнал импортов для идемпотентности.

Реальный публичный API инфороста в этом контуре НЕДОСТУПЕН, поэтому модуль не
ходит в сеть: он МАПИТ документированную форму инфорост-экспорта в форму Biblio.
Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей — в точности как ``config_store.py``/``exhibits.py``. Никаких
записей в живой ИРБИС.

Форма инфорост-экспорта (вход)
------------------------------
Документированная выгрузка::

    {'collections': [
       {'id': 'c1', 'title': 'Афиши 1920-х', 'description': '...',
        'items': [
          {'id': 'i1', 'title': 'Афиша Чайки', 'author': 'Театр', 'year': '1925',
           'pages': [{'no': 1, 'image': 'https://inforost/i1/1.jpg'}, ...]},
          ...]},
       ...]}

Коллекция несёт позиции (``items``); позиция несёт страницы (``pages``), каждая
со ссылкой на образ (``image``).

Маппинг в Biblio
----------------
Каталожная запись Biblio — tag-keyed dict (как везде в проекте: поле -> список
инстансов ``[{code: value}]`` либо скаляр). Маппер позиции:

  * ``200^a``  <- ``title``  (заглавие; присутствует всегда);
  * ``700^a``  <- ``author`` (если задан);
  * ``210^d``  <- ``year``   (если задан);
  * ``900^b``  <- ``'08'``   (вид издания = оцифровка, ФИКСИРОВАНО);
  * ``source`` <- ``'inforost:' + id`` (происхождение; присутствует всегда).

Пустые поля ОПУСКАЮТСЯ (нет ключа), КРОМЕ ``200`` и ``source``. Все мапперы —
ЧИСТЫЕ функции, устойчивые к отсутствию любых полей (defensive, как
``access/oai_pmh.py``).

Own-store
---------
``InforostImportStore`` — журнал импортов (``inforost_import``) для
идемпотентности и аудита: повторный ``source_id`` в рамках тенанта не плодит
дубль (``INSERT OR IGNORE`` по ``UNIQUE(tenant, source_id)``).
``InforostService`` — глубина: сводный план импорта (dry-run) и регистрация
плана в журнале с подсчётом «новое/пропущено».
"""
import json  # noqa: F401  (stdlib JSON — домашний стиль own-store-модулей)
import sqlite3
import threading
from datetime import datetime, timezone

__all__ = [
    'map_item', 'item_assets', 'map_collection', 'parse_export',
    'InforostImportStore', 'InforostService', 'SCHEMA_SQLITE',
]

# Вид издания для оцифровки (900^b) — фиксированная константа коннектора.
KIND_DIGITIZED = '08'

# Префикс источника происхождения записи (поле ``source``).
SOURCE_PREFIX = 'inforost:'


def _utcnow():
    """Текущее время UTC в ISO8601 (инжектируемые часы по умолчанию)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# Локальные аксессоры по форме инфорост-экспорта (устойчивы к None/не-dict).
# --------------------------------------------------------------------------- #
def _get(obj, key, default=''):
    """Значение ключа ``key`` из dict ``obj`` или ``default`` (None -> default).

    Устойчиво к ``obj`` не-dict (вернёт ``default``) и к значению ``None``
    (тоже ``default``) — defensive-доступ в духе ``access/oai_pmh.py``."""
    if not isinstance(obj, dict):
        return default
    val = obj.get(key, default)
    return default if val is None else val


def _str(value):
    """Привести значение к строке (``''`` для пустого/None)."""
    if value is None:
        return ''
    return str(value)


# --------------------------------------------------------------------------- #
# ЧИСТЫЕ мапперы: инфорост-экспорт -> форма Biblio.
# --------------------------------------------------------------------------- #
def item_assets(item):
    """Список URL образов страниц позиции (из ``pages[].image``).

    Возвращает список строк-URL в порядке страниц. Устойчиво к отсутствию
    ``pages``/``None``/не-списку и к страницам без ``image`` (такие пропускаются).
    Используется как набор образов (assets) позиции для витрины и для подсчёта
    объёма импорта."""
    pages = _get(item, 'pages', None)
    if not isinstance(pages, list):
        return []
    out = []
    for page in pages:
        image = _get(page, 'image', '')
        if image:
            out.append(_str(image))
    return out


def map_item(item):
    """Смаппить позицию инфорост-экспорта в tag-keyed запись Biblio -> dict.

    Возвращает каталожную запись::

        {'200': [{'a': title}],
         '700': [{'a': author}],   # если author задан
         '210': [{'d': year}],     # если year задан
         '900': [{'b': '08'}],     # вид = оцифровка, ФИКСИРОВАНО
         'source': 'inforost:<id>'}

    Пустые поля ОПУСКАЮТСЯ, КРОМЕ ``200`` и ``source`` (они присутствуют всегда —
    минимум адресуемой записи). Устойчиво к отсутствию любых полей."""
    title = _str(_get(item, 'title', ''))
    author = _str(_get(item, 'author', ''))
    year = _str(_get(item, 'year', ''))
    item_id = _str(_get(item, 'id', ''))

    rec = {'200': [{'a': title}]}
    if author:
        rec['700'] = [{'a': author}]
    if year:
        rec['210'] = [{'d': year}]
    rec['900'] = [{'b': KIND_DIGITIZED}]
    rec['source'] = SOURCE_PREFIX + item_id
    return rec


def _slug(value):
    """Человекочитаемый ключ витрины из ``id`` коллекции (lower, непустой).

    Приводит к нижнему регистру и срезает пробелы; если результат пуст —
    отдаёт фоллбэк ``'collection'`` (slug в выставка-форме обязателен и непуст)."""
    s = _str(value).strip().lower()
    return s or 'collection'


def map_collection(coll):
    """Смаппить коллекцию инфорост-экспорта в выставка-форму витрины -> dict.

    Возвращает::

        {'slug': <slug из id>,
         'title': <title>,
         'description': <description>,
         'items': [{'source_id': <item id>,
                    'caption': <item title>,
                    'assets': [<url образов>]}, ...]}

    ``slug`` строится из ``id`` коллекции (lower, непустой); каждая позиция несёт
    ``source_id`` (исходный id), ``caption`` (заглавие позиции) и ``assets``
    (URL образов через :func:`item_assets`). Устойчиво к отсутствию
    ``items``/``None``."""
    items_in = _get(coll, 'items', None)
    if not isinstance(items_in, list):
        items_in = []
    items = []
    for item in items_in:
        items.append({
            'source_id': _str(_get(item, 'id', '')),
            'caption': _str(_get(item, 'title', '')),
            'assets': item_assets(item),
        })
    return {
        'slug': _slug(_get(coll, 'id', '')),
        'title': _str(_get(coll, 'title', '')),
        'description': _str(_get(coll, 'description', '')),
        'items': items,
    }


def parse_export(data):
    """Сводный ПЛАН импорта инфорост-экспорта (dry-run, без записи) -> dict.

    Проходит по коллекциям и их позициям и собирает::

        {'collections': [map_collection(c), ...],   # выставка-формы
         'records': [map_item(i), ...],             # каталожные записи (все items)
         'collections_total': <число коллекций>,
         'items_total': <суммарное число позиций>,
         'assets_total': <суммарное число образов страниц>}

    Это безопасный предпросмотр: ничего не пишется и не уходит в живой ИРБИС.
    Устойчиво к отсутствию ``collections``/``items``/``None`` (defensive, как
    ``access/oai_pmh.py``)."""
    collections_in = _get(data, 'collections', None)
    if not isinstance(collections_in, list):
        collections_in = []

    collections = []
    records = []
    assets_total = 0
    items_total = 0
    for coll in collections_in:
        collections.append(map_collection(coll))
        items_in = _get(coll, 'items', None)
        if not isinstance(items_in, list):
            items_in = []
        for item in items_in:
            records.append(map_item(item))
            assets_total += len(item_assets(item))
            items_total += 1
    return {
        'collections': collections,
        'records': records,
        'collections_total': len(collections),
        'items_total': items_total,
        'assets_total': assets_total,
    }


# --------------------------------------------------------------------------- #
# OWN-STORE: журнал импортов (идемпотентность/аудит).
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS inforost_import (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant     TEXT NOT NULL DEFAULT 'default',
  source_id  TEXT NOT NULL,            -- id коллекции/позиции в инфоросте
  kind       TEXT NOT NULL,            -- 'collection' | 'item'
  title      TEXT NOT NULL DEFAULT '',
  created_at TEXT,
  UNIQUE(tenant, source_id)
);
CREATE INDEX IF NOT EXISTS inforost_import_tenant_idx
  ON inforost_import(tenant, source_id);
"""


class InforostImportStore:
    """Собственный sqlite-журнал импортов инфороста (идемпотентность + аудит).

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах. Каждый импортированный
    объект (коллекция/позиция) фиксируется один раз: пара ``(tenant, source_id)``
    уникальна, повторная запись игнорируется."""

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

    def _row(self, tenant, source_id):
        """Сырая строка журнала (sqlite3.Row) по ключу или ``None``."""
        return self._conn().execute(
            'SELECT * FROM inforost_import WHERE tenant=? AND source_id=?',
            (tenant, source_id)).fetchone()

    def record(self, tenant, source_id, kind, title=''):
        """Зафиксировать импорт объекта в журнале (идемпотентно) -> dict.

        ``INSERT OR IGNORE`` по ``UNIQUE(tenant, source_id)``: повторный
        ``source_id`` в рамках тенанта НЕ создаёт дубль (остаётся первая запись
        с её ``created_at``). Возвращает строку-dict журнала (текущую — новую или
        ранее существовавшую)."""
        now = self._now()
        c = self._conn()
        c.execute(
            'INSERT OR IGNORE INTO inforost_import'
            '(tenant,source_id,kind,title,created_at) VALUES(?,?,?,?,?)',
            (tenant, source_id, kind, title, now))
        c.commit()
        return dict(self._row(tenant, source_id))

    def seen(self, tenant, source_id):
        """Был ли объект уже импортирован в этого тенанта (``bool``)."""
        return self._row(tenant, source_id) is not None

    def for_tenant(self, tenant):
        """Список строк-dict журнала тенанта (по порядку фиксации, id ASC)."""
        rows = self._conn().execute(
            'SELECT * FROM inforost_import WHERE tenant=? ORDER BY id',
            (tenant,)).fetchall()
        return [dict(r) for r in rows]


class InforostService:
    """Глубина над :class:`InforostImportStore`: dry-run план + журналируемый импорт.

    Делегирует журнал стору; добавляет сводный план (тонкая обёртка над
    :func:`parse_export`) и регистрацию плана в журнале с подсчётом
    «новое/пропущено» — для идемпотентного повторного прогона."""

    def __init__(self, store=None, now=None):
        self.store = store or InforostImportStore(':memory:', now=now)

    def plan(self, data):
        """Сводный план импорта (dry-run) — тонкая обёртка над :func:`parse_export`.

        Ничего не пишет в журнал: только показывает, что будет импортировано."""
        return parse_export(data)

    def is_imported(self, tenant, source_id):
        """Был ли объект (по ``source_id``) уже импортирован в тенанта (``bool``)."""
        return self.store.seen(tenant, source_id)

    def import_log(self, tenant, data):
        """Зарегистрировать ВСЕ коллекции и позиции экспорта в журнале -> dict.

        Каждая коллекция фиксируется как ``kind='collection'`` (по её ``slug``),
        каждая позиция — как ``kind='item'`` (по её ``source_id``). Запись
        идемпотентна: впервые увиденные объекты считаются «новыми» (``new``), уже
        бывшие — «пропущенными» (``skipped``). Возвращает::

            {'new': <впервые увиденных>,
             'skipped': <уже бывших>,
             'plan': parse_export(data)}

        Повторный прогон того же экспорта даёт ``new=0`` и весь объём в
        ``skipped`` (идемпотентность)."""
        plan = parse_export(data)
        new = 0
        skipped = 0
        for coll in plan['collections']:
            slug = coll['slug']
            already = self.store.seen(tenant, slug)
            self.store.record(tenant, slug, 'collection', coll['title'])
            if already:
                skipped += 1
            else:
                new += 1
            for item in coll['items']:
                source_id = item['source_id']
                already = self.store.seen(tenant, source_id)
                self.store.record(tenant, source_id, 'item', item['caption'])
                if already:
                    skipped += 1
                else:
                    new += 1
        return {'new': new, 'skipped': skipped, 'plan': plan}
