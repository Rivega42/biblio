#!/usr/bin/env python3
"""FULLTEXT — реестр артефактов полных текстов / образов (кластер 7, ребро 7.1).

Каталожная запись-ресурс ИРБИС64 связывается с физическими полными текстами / образами
тремя локальными полями БО (блок «образы/полные тексты»):

  * **951** — *внешний объект*: ссылка/путь на файл ПТ вне записи
    (`^A` имя файла, `^I` URL, `^T` текст ссылки). Хранится как **ссылка**, бинарь не
    втягивается в БД (по `951.wss`/FIELD_DICTIONARY).
  * **953** — *встроенный двоичный ресурс*: в боевом ИРБИС `^B` несёт сам бинарь
    (base64, ввод `!12`). Здесь мы **НЕ раздуваем БД сырыми байтами** — храним
    blob-референс (путь+хэш) и метаданные (`^A` тип ресурса по `953.mnu`, `^T` имя,
    `^P` режим показа по `xp.mnu`). Сам байтовый поток — за DAM-бэкендом (см. «Отложено»).
  * **955** — *метаданные ПТ*: `^A` имя файла, `^N` число страниц, `^B` ссылка на
    шаблон прав RIGHT (тот же template id, что читает ``access.rights``). 955^B мы
    **только резолвим и отдаём наружу** (чтобы вызывающий скомбинировал с
    ``rights.access_level``) — сам гейтинг здесь НЕ реализуется.

Граница ответственности (важно). Этот модуль — про **хранение/резолв** артефактов ПТ:
он ХРАНИТ ссылки/blob-референсы/метаданные и РЕЗОЛВИТ их по каталожной записи. Гейтинг
доступа (deny/view/download по категории читателя, лимит страниц ^F) живёт в
``access.rights`` (рёбра 7.2–7.5) и здесь НЕ дублируется. ``artifacts_for`` лишь
возвращает ссылку на шаблон прав (955^B / ``rights_template``) рядом с каждым ПТ-артефактом,
чтобы вызывающий код мог сам спросить ``RightService.access_level``.

Источники (только факты из конфигов):
  * ``docs/recon/deep/reference/format/FIELD_DICTIONARY.md`` (951 `^A`/`^I`/`^T`);
  * ``docs/recon/deep/reference/databases/DB_CATALOG_VARIANTS.md`` §IMAGE
    (953 `^A`/`^T`/`^P`/`^B`; `Uni_H.pft`: 953^B → слот 12 «бинарник в записи», 951 →
    слот 10 «директория внешних файлов»; «образ карточки» собирает 951/953/955);
  * ``docs/recon/deep/reference/databases/DB_SERVICE.md`` §1/§2 (955^B → RIGHT;
    LICH `FULL=` при скачано ≥ v955^N — т.е. `^N` = число страниц);
  * ``docs/design/ARCHITECTURE.md`` §3 (Файлы/Хранилище: обложки, ПТ/PDF в S3/MinIO,
    view-only-прокси; Сканирование/DAM → 951/953/955);
  * ``docs/design/INTEGRATION_MAP.md`` кластер 7 (ребро 7.1 + связь 7.2–7.5);
  * ``docs/recon/deep/FINDINGS_09_web_reader.md`` (951 Show_ed; 953 «двоичный ресурс»;
    955^A IMAGE_FILE; постраничный просмотр PDF).

Связь с каталогом — через ОПЦИОНАЛЬНЫЙ catalog-handle (как ``rights.RightService``):
``catalog.get(db, mfn) -> record``. По нему резолвятся 951/953/955 каталожной записи и
дополняют реестр-стор (артефакты, заведённые напрямую через ``attach``). Без handle —
back-compat: каталог не читается, резолв опирается только на стор.

Бэкенд-портируемость (ADR-004: sqlite dev / PostgreSQL prod) — ``FulltextStore``
работает на ДВУХ бэкендах с одинаковой поверхностью (как ``rights.py``/``lich.py``/
``demo_requests.py``): sqlite по умолчанию (свой файл/``:memory:``), postgres по DSN;
DDL зеркалит схему, psycopg импортируется лениво.
"""
import hashlib
import json
import threading
import time

# --- Виды артефактов ПТ (контракт наружу) ---------------------------------- #
# Совпадают с тегами полей БО: 951 внешняя ссылка / 953 встроенный двоичный /
# 955 метаданные ПТ. ``attach``/``artifacts_for`` оперируют этими константами.
KIND_LINK = '951'    # внешний объект: ссылка/путь к файлу ПТ
KIND_BLOB = '953'    # встроенный двоичный: blob-референс (путь+хэш), не сырые байты
KIND_META = '955'    # метаданные ПТ: файл, число страниц, ссылка на шаблон прав
KINDS = (KIND_LINK, KIND_BLOB, KIND_META)

# Подполя полей-источников → канонические ключи артефакта. Зеркало 951/953/955 .wss.
# Регистронезависимо (как ``rights._extract_955b``: b/B).
_SUB_951 = {'a': 'file', 'i': 'url', 't': 'text'}                 # имя файла / URL / текст ссылки
_SUB_953 = {'a': 'res_type', 't': 'name', 'p': 'view_mode', 'b': 'blob'}  # тип/имя/режим/бинарь
_SUB_955 = {'a': 'file', 'n': 'pages', 'b': 'rights_template'}    # файл / число страниц / шаблон прав


def _is_pg(handle):
    """True, если ``handle`` — PG DSN-строка (а не путь к sqlite-файлу)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


def _s(v):
    """Привести значение подполя к обрезанной строке (None → '')."""
    return '' if v is None else str(v).strip()


def _to_pages(v):
    """Привести `^N` (число страниц) к неотрицательному int или None.

    Пусто/нечисло → None (страниц не известно). Отрицательное → None (мусор)."""
    s = _s(v)
    if not s:
        return None
    try:
        n = int(s)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _subfields(inst, alias_map):
    """Достать канонические подполя из одного инстанса поля (str | dict).

    Инстанс-строка (поле без подполей) кладётся в ключ из ``alias_map['']`` если он
    задан, иначе игнорируется. Подполя читаются регистронезависимо (как 955^B в rights)."""
    out = {}
    if inst is None:
        return out
    if isinstance(inst, dict):
        for key, val in inst.items():
            canon = alias_map.get(str(key).strip().lower())
            if canon is not None:
                out[canon] = _s(val)
    else:
        # Целое поле строкой подполей не несёт; для 951/953/955 без подполей пропускаем.
        bare = alias_map.get('')
        if bare is not None:
            out[bare] = _s(inst)
    return out


def _instances(record, tag):
    """Список инстансов поля ``tag`` записи (поле повторяющееся). [] если нет."""
    if not record:
        return []
    raw = record.get(tag)
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def blob_ref(data=None, *, path=None, sha256=None, size=None, content_type=None):
    """Сформировать blob-референс для встроенного двоичного ресурса (953).

    Назначение — НЕ хранить сырые байты в БД (раздувание): держим ссылку на объект в
    DAM/объектном хранилище (S3/MinIO, ARCHITECTURE §3) + контрольную сумму для fixity.

    Parameters
    ----------
    data : bytes | None
        Сырые байты — используются ТОЛЬКО для вычисления sha256/size на лету
        (например, в тесте). В стор сами байты не пишутся.
    path : str | None
        Путь/ключ объекта в DAM-хранилище (``s3://bucket/key`` / относительный путь).
    sha256 : str | None
        Готовый хэш (если уже посчитан выше по конвейеру). Имеет приоритет над ``data``.
    size : int | None
        Размер в байтах (если известен).
    content_type : str | None
        MIME-тип объекта.

    Returns
    -------
    dict
        ``{'path','sha256','size','contentType'}`` (пустые ключи опускаются).
    """
    ref = {}
    p = _s(path)
    if p:
        ref['path'] = p
    h = _s(sha256)
    if not h and data is not None:
        h = hashlib.sha256(data).hexdigest()
    if h:
        ref['sha256'] = h
    if size is None and data is not None:
        size = len(data)
    if size is not None:
        ref['size'] = int(size)
    ct = _s(content_type)
    if ct:
        ref['contentType'] = ct
    return ref


# --------------------------------------------------------------------------- #
# Хранилище артефактов ПТ (sqlite dev / PostgreSQL prod), своя схема.
# Один артефакт = одна строка (db, mfn, kind, [seq]). data_json несёт подполя
# вида артефакта (951: file/url/text · 953: res_type/name/view_mode/blob ·
# 955: file/pages/rights_template). Сырые двоичные байты в БД НЕ пишутся (953 — blob-реф).
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS fulltext_artifact (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  db          TEXT NOT NULL,             -- имя БД-источника (IBIS/SK/VKR/…)
  mfn         INTEGER NOT NULL,          -- MFN каталожной записи-ресурса
  kind        TEXT NOT NULL,             -- '951' ссылка | '953' blob-реф | '955' метаданные ПТ
  data_json   TEXT NOT NULL DEFAULT '{}',-- подполя артефакта (по виду)
  created_at  REAL NOT NULL,
  updated_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS fulltext_rec_idx ON fulltext_artifact(db, mfn);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS fulltext_artifact (
  id          BIGSERIAL PRIMARY KEY,
  db          TEXT NOT NULL,
  mfn         BIGINT NOT NULL,
  kind        TEXT NOT NULL,
  data_json   TEXT NOT NULL DEFAULT '{}',
  created_at  DOUBLE PRECISION NOT NULL,
  updated_at  DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS fulltext_rec_idx ON fulltext_artifact(db, mfn);
"""


class FulltextStore:
    """Стор артефактов ПТ (sqlite по умолчанию / PostgreSQL по DSN).

    Артефакты, заведённые ПРЯМО (``attach``) — поверх тех, что резолвятся из каталога.
    Поверхность: ``attach`` / ``for_record`` / ``delete_record`` / ``count``.

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
            'db': r['db'],
            'mfn': int(r['mfn']),
            'kind': r['kind'],
            'data': json.loads(r['data_json'] or '{}'),
            'createdAt': float(r['created_at']),
            'updatedAt': float(r['updated_at']),
        }

    def attach(self, db, mfn, kind, data, now=None):
        """Добавить артефакт ПТ к записи (db, mfn). Возвращает нормализованный артефакт.

        ``kind`` ∈ {951,953,955}; ``data`` — dict подполей вида (уже нормализованных).
        Поля 951/953/955 повторяющиеся, поэтому артефакты НЕ перезаписывают друг друга:
        каждый ``attach`` — отдельная строка (одна запись может нести несколько ПТ)."""
        kind = str(kind).strip()
        if kind not in KINDS:
            raise ValueError('kind должен быть одним из %s' % (KINDS,))
        ts = float(now if now is not None else time.time())
        dj = json.dumps(dict(data or {}), ensure_ascii=False)
        c = self._conn()
        ph = self._ph
        if self.backend == 'postgres':
            row = c.execute(
                'INSERT INTO fulltext_artifact(db,mfn,kind,data_json,created_at,updated_at) '
                'VALUES(%s,%s,%s,%s,%s,%s) RETURNING *',
                (str(db), int(mfn), kind, dj, ts, ts)).fetchone()
            return self._view(dict(row))
        cur = c.execute(
            'INSERT INTO fulltext_artifact(db,mfn,kind,data_json,created_at,updated_at) '
            'VALUES(?,?,?,?,?,?)',
            (str(db), int(mfn), kind, dj, ts, ts))
        c.commit()
        r = c.execute('SELECT * FROM fulltext_artifact WHERE id=?', (cur.lastrowid,)).fetchone()
        return self._view(dict(r))

    def for_record(self, db, mfn):
        """Все артефакты записи (db, mfn) из стора (в порядке добавления). [] если нет."""
        ph = self._ph
        rows = self._conn().execute(
            'SELECT * FROM fulltext_artifact WHERE db=%s AND mfn=%s ORDER BY id'
            % (ph, ph), (str(db), int(mfn))).fetchall()
        return [self._view(dict(r)) for r in rows]

    def delete_record(self, db, mfn):
        """Удалить все артефакты записи (db, mfn). Возвращает число удалённых строк."""
        ph = self._ph
        c = self._conn()
        cur = c.execute('DELETE FROM fulltext_artifact WHERE db=%s AND mfn=%s'
                        % (ph, ph), (str(db), int(mfn)))
        if self.backend != 'postgres':
            c.commit()
            return cur.rowcount
        return getattr(cur, 'rowcount', 0)

    def count(self):
        r = self._conn().execute('SELECT COUNT(*) AS n FROM fulltext_artifact').fetchone()
        return int(dict(r)['n'])


class FulltextRegistry:
    """Реестр артефактов ПТ на запись каталога (ребро 7.1): хранение + резолв.

    Объединяет ДВА источника артефактов ПТ записи:
      1. **стор** (``FulltextStore``) — артефакты, заведённые напрямую ``attach`` (наш
         реестр, независимый от живого ИРБИС);
      2. **каталог** (опц. handle ``catalog.get(db, mfn) -> record``) — поля 951/953/955
         каталожной записи (как их видит сама запись БО).

    ``artifacts_for`` сводит оба в единый список с нормализованной формой. Гейтинг здесь
    НЕ реализуется (см. ``access.rights``): для каждого ПТ-артефакта в выдаче лежит
    ``rights_template`` (955^B), чтобы вызывающий скомбинировал с ``rights.access_level``.

    Parameters
    ----------
    store : FulltextStore | None
        Стор артефактов. ``None`` ⇒ реестр работает только поверх каталога (резолв из
        записи), без собственного слоя ``attach``.
    catalog : object | None
        Каталог-handle с ``get(db, mfn) -> record`` (``access.catalog.CatalogStore``).
        По нему резолвятся 951/953/955 записи. ``None`` ⇒ back-compat: каталог не
        читается (резолв опирается только на стор; без стора — пусто).
    now : callable
        Часы (``time.time`` по умолчанию) — для штампов ``attach``.
    """

    def __init__(self, store=None, catalog=None, now=None):
        self.store = store
        self.catalog = catalog
        if now is None:
            now = time.time
        self._now = now

    # ---- запись артефакта (через стор) ----------------------------------- #
    def attach(self, db, mfn, kind, **fields):
        """Завести артефакт ПТ на запись (db, mfn). Требует стор.

        Унифицированный конструктор по виду:

          * ``kind='951'`` (ссылка): ``file=`` имя файла, ``url=`` URL, ``text=`` текст
            ссылки. Бинарь НЕ принимается — это внешняя ссылка.
          * ``kind='953'`` (встроенный двоичный): ``res_type=`` тип (953.mnu),
            ``name=`` имя, ``view_mode=`` режим показа (xp.mnu), ``blob=`` blob-референс
            (dict из ``blob_ref`` ИЛИ ``data=bytes`` — тогда blob-реф считается на лету;
            сырые байты в стор НЕ пишутся). ``path=``/``sha256=``/``size=``/
            ``content_type=`` — шорткаты для ``blob_ref``.
          * ``kind='955'`` (метаданные ПТ): ``file=`` имя файла, ``pages=`` число
            страниц (^N), ``rights_template=`` ссылка на шаблон прав (955^B).

        Возвращает нормализованный артефакт (как элемент ``artifacts_for``)."""
        if self.store is None:
            raise RuntimeError('attach требует FulltextStore (store=None)')
        kind = str(kind).strip()
        data = self._build_data(kind, fields)
        raw = self.store.attach(db, mfn, kind, data, now=self._now())
        return self._normalize(raw['kind'], raw['data'], source='store',
                               artifact_id=raw['id'])

    @staticmethod
    def _build_data(kind, fields):
        """Собрать нормализованный data-dict артефакта из kwargs ``attach`` по виду."""
        f = dict(fields or {})
        if kind == KIND_LINK:
            data = {}
            for key in ('file', 'url', 'text'):
                if key in f and _s(f[key]):
                    data[key] = _s(f[key])
            return data
        if kind == KIND_BLOB:
            data = {}
            for key in ('res_type', 'name', 'view_mode'):
                if key in f and _s(f[key]):
                    data[key] = _s(f[key])
            blob = f.get('blob')
            if isinstance(blob, dict):
                data['blob'] = dict(blob)
            elif any(k in f for k in ('data', 'path', 'sha256', 'size', 'content_type')):
                ref = blob_ref(data=f.get('data'), path=f.get('path'),
                               sha256=f.get('sha256'), size=f.get('size'),
                               content_type=f.get('content_type'))
                if ref:
                    data['blob'] = ref
            return data
        if kind == KIND_META:
            data = {}
            if 'file' in f and _s(f['file']):
                data['file'] = _s(f['file'])
            if 'pages' in f:
                p = _to_pages(f['pages'])
                if p is not None:
                    data['pages'] = p
            if 'rights_template' in f and _s(f['rights_template']):
                data['rights_template'] = _s(f['rights_template'])
            return data
        raise ValueError('kind должен быть одним из %s' % (KINDS,))

    # ---- резолв из каталожной записи (951/953/955) ----------------------- #
    def _record(self, db, mfn):
        """Прочитать каталожную запись через handle. None при отсутствии/ошибке.

        Никогда не бросает наружу seam-ошибку (деградирует к None — как rights.py)."""
        if self.catalog is None:
            return None
        try:
            return self.catalog.get(db, mfn)
        except Exception:
            return None

    @classmethod
    def _from_record(cls, record):
        """Список нормализованных артефактов из полей 951/953/955 записи (по порядку видов)."""
        out = []
        for tag, alias in ((KIND_LINK, _SUB_951), (KIND_BLOB, _SUB_953), (KIND_META, _SUB_955)):
            for inst in _instances(record, tag):
                sub = _subfields(inst, alias)
                out.append(cls._normalize(tag, sub, source='catalog'))
        return out

    @classmethod
    def _normalize(cls, kind, data, *, source, artifact_id=None):
        """Привести артефакт к стабильной публичной форме (общей для стора и каталога).

        Общие ключи: ``kind`` · ``source`` (catalog|store) · ``ref`` (ссылка/путь/None) ·
        ``pages`` (число страниц | None) · ``rights_template`` (955^B | None) · ``data``
        (сырые подполя вида). ``ref`` единообразно «где взять артефакт»:
          * 951 → URL или имя файла;
          * 953 → путь blob-референса (объект в DAM), либо None если только метаданные;
          * 955 → имя файла ПТ (^A).
        ``rights_template`` заполняется ТОЛЬКО для 955 (^B) — это вход для ``rights``."""
        data = dict(data or {})
        pages = None
        rights_template = None
        ref = None
        if kind == KIND_LINK:
            ref = data.get('url') or data.get('file') or None
        elif kind == KIND_BLOB:
            blob = data.get('blob')
            if isinstance(blob, dict):
                ref = blob.get('path') or None
            # 953 из каталога несёт base64 в ^B — наружу сам бинарь НЕ отдаём (раздувание).
            # Оставляем признак наличия встроенного ресурса во флаге ``embedded``.
        elif kind == KIND_META:
            ref = data.get('file') or None
            pages = data.get('pages')
            if pages is None:
                pages = _to_pages(data.get('pages'))
            rights_template = data.get('rights_template') or None
        art = {
            'kind': kind,
            'source': source,
            'ref': (ref if (ref is None or _s(ref)) else None),
            'pages': pages,
            'rights_template': rights_template,
            'data': data,
        }
        if kind == KIND_BLOB:
            art['embedded'] = bool(data.get('blob') is not None
                                   or data.get('res_type') or data.get('name'))
        if artifact_id is not None:
            art['id'] = artifact_id
        return art

    # ---- основной контракт (ребро 7.1) ----------------------------------- #
    def artifacts_for(self, db, mfn):
        """Все артефакты ПТ записи (db, mfn): стор + каталог, единым списком.

        Каждый артефакт: ``kind`` (951/953/955), ``source`` (store|catalog), ``ref``
        (ссылка/путь/имя файла, либо None), ``pages`` (число страниц для 955, иначе None),
        ``rights_template`` (955^B — ссылка на шаблон прав, иначе None), ``data`` (сырые
        подполя). Порядок: сначала артефакты из стора (что завели через ``attach``), затем
        из каталожной записи (как их видит сама запись БО). Без handle и без стора — []."""
        out = []
        if self.store is not None:
            for raw in self.store.for_record(db, mfn):
                out.append(self._normalize(raw['kind'], raw['data'], source='store',
                                           artifact_id=raw['id']))
        record = self._record(db, mfn)
        if record is not None:
            out.extend(self._from_record(record))
        return out

    def page_count(self, db, mfn):
        """Число страниц ПТ записи (955^N), либо None если не задано.

        Берёт максимум ``pages`` среди артефактов 955 (несколько ПТ на запись — берём
        наибольший known-объём; ровно как LICH `FULL=` сверяет скачано против v955^N).
        None ⇒ ни один 955-артефакт не несёт числа страниц."""
        pages = None
        for art in self.artifacts_for(db, mfn):
            if art['kind'] == KIND_META and art.get('pages') is not None:
                p = art['pages']
                pages = p if pages is None else max(pages, p)
        return pages

    def rights_template_for(self, db, mfn):
        """Ссылка на шаблон прав ПТ записи (955^B), либо None.

        Удобный аксессор для связки с ``access.rights`` (ребро 7.2): первый непустой
        ``rights_template`` среди 955-артефактов. Сам гейтинг НЕ делает — только отдаёт
        id шаблона, который ``RightService.access_level`` превратит в deny/view/download."""
        for art in self.artifacts_for(db, mfn):
            if art['kind'] == KIND_META and art.get('rights_template'):
                return art['rights_template']
        return None
