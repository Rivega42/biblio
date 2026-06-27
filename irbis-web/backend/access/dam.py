#!/usr/bin/env python3
"""DAM — собственный реестр цифровых ассетов записи каталога (ребро INTEGRATION_MAP 7.1).

Каталожная запись-ресурс ИРБИС64 связывается со своим бинарём (полным текстом /
образом) тремя локальными полями БО блока «образы/полные тексты»:

  * **951** — *внешний объект*: ссылка/путь на файл ПТ вне записи (внешний URL/файл);
  * **953** — *встроенный двоичный*: сам бинарь в записи (``^B`` base64, ввод ``!12``).
    Здесь мы **НЕ раздуваем БД сырыми байтами** — храним лишь идентификатор блоба
    (``ref`` = ключ/путь объекта в DAM-хранилище);
  * **955** — *метаданные ПТ*: ``^A`` имя файла, ``^N`` число страниц, ``^B`` ссылка на
    шаблон прав RIGHT (тот же template id, что читает ``access.rights`` — ребро 7.2).

Зачем отдельно от ``access.fulltext``
-------------------------------------
``fulltext`` — реестр/резолв артефактов ПТ, объединяющий стор И опциональный
каталог-handle (резолв 951/953/955 прямо из записи БО), с двойным бэкендом
sqlite/PostgreSQL. **DAM** — узкий own-store **РЕЕСТР АССЕТОВ** (метаданные связей
запись↔бинарь): чистый stdlib ``sqlite3``, без каталог-handle, без сети, без новых
pip-зависимостей — в точности как ``pay.py``/``devices.py``. Это и есть закрытие
ребра 7.1 на уровне хранилища: «у записи (db, mfn) такие-то ассеты».

Реального объектного хранилища (S3/MinIO) здесь нет — это деплой (ARCHITECTURE §3,
«Файлы/Хранилище»). DAM хранит только МЕТАДАННЫЕ ассета: вид (951/953/955),
``ref`` (URL/путь/идентификатор блоба/имя файла), число страниц (955^N), MIME и
ссылку на шаблон прав (955^B). Сам байтовый поток — за DAM-бэкендом.

Связь с правами (ребро 7.2). 955^B (ссылка на RIGHT-шаблон) кладётся в поле
``rights_template`` — но ``access.rights`` здесь **НЕ импортируется**: мы лишь храним
id шаблона, чтобы вызывающий скомбинировал его с ``RightService.access_level``.
"""
import sqlite3
import threading
import time

# Виды ассетов — совпадают с тегами полей БО блока образов/ПТ.
KIND_EXTERNAL = '951'   # внешний URL/файл (ref = URL/путь)
KIND_EMBEDDED = '953'   # встроенный двоичный (ref = идентификатор блоба в DAM-хранилище)
KIND_META = '955'       # метаданные ПТ (ref = имя файла ^A, pages = ^N, rights_template = ^B)
KINDS = (KIND_EXTERNAL, KIND_EMBEDDED, KIND_META)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS dam_asset (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  db              TEXT NOT NULL,            -- имя БД-источника (IBIS/SK/VKR/…)
  mfn             INTEGER NOT NULL,         -- MFN каталожной записи-ресурса
  kind            TEXT NOT NULL,            -- '951' внешний | '953' блоб | '955' метаданные ПТ
  ref             TEXT NOT NULL,            -- URL/путь | id блоба | имя файла ^A
  pages           INTEGER,                  -- 955^N число страниц (иначе NULL)
  mime            TEXT,                     -- MIME-тип ассета (иначе NULL)
  rights_template TEXT,                     -- 955^B ссылка на RIGHT-шаблон (иначе NULL)
  created_at      REAL NOT NULL,
  UNIQUE(db, mfn, kind, ref)
);
CREATE INDEX IF NOT EXISTS dam_asset_rec_idx ON dam_asset(db, mfn);
"""


class DamStore:
    """Собственный sqlite-стор реестра ассетов DAM. ``:memory:`` или файл; create-on-init.

    Соединение thread-local (домашний стиль); строки — dict. Идемпотентность связи
    запись↔бинарь обеспечивает ``UNIQUE(db, mfn, kind, ref)``.
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

    def add(self, db, mfn, kind, ref, pages, mime, rights_template, created_at):
        """Привязать ассет к записи (db, mfn). Идемпотентно по (db, mfn, kind, ref):
        повторная привязка того же бинаря возвращает уже существующую строку."""
        c = self._conn()
        cur = c.execute(
            'INSERT OR IGNORE INTO dam_asset(db,mfn,kind,ref,pages,mime,'
            'rights_template,created_at) VALUES(?,?,?,?,?,?,?,?)',
            (str(db), int(mfn), kind, str(ref), pages, mime, rights_template,
             created_at))
        c.commit()
        if cur.lastrowid and cur.rowcount:
            return self.get(cur.lastrowid)
        # Уже была такая связь (INSERT OR IGNORE не вставил) — вернуть существующую.
        r = c.execute(
            'SELECT * FROM dam_asset WHERE db=? AND mfn=? AND kind=? AND ref=?',
            (str(db), int(mfn), kind, str(ref))).fetchone()
        return dict(r) if r else None

    def get(self, asset_id):
        r = self._conn().execute(
            'SELECT * FROM dam_asset WHERE id=?', (asset_id,)).fetchone()
        return dict(r) if r else None

    def for_record(self, db, mfn):
        """Все ассеты записи (db, mfn) в порядке добавления."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM dam_asset WHERE db=? AND mfn=? ORDER BY id',
            (str(db), int(mfn))).fetchall()]

    def for_record_kind(self, db, mfn, kind):
        """Ассеты записи (db, mfn) заданного вида (951/953/955)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM dam_asset WHERE db=? AND mfn=? AND kind=? ORDER BY id',
            (str(db), int(mfn), kind)).fetchall()]

    def delete(self, asset_id):
        """Удалить ассет по id. Возвращает True, если строка была удалена."""
        c = self._conn()
        cur = c.execute('DELETE FROM dam_asset WHERE id=?', (asset_id,))
        c.commit()
        return bool(cur.rowcount)

    def counts_by_kind(self):
        """Число ассетов по видам -> ``{kind: n}`` (только непустые виды)."""
        rows = self._conn().execute(
            'SELECT kind, COUNT(*) AS n FROM dam_asset GROUP BY kind').fetchall()
        return {r['kind']: int(r['n']) for r in rows}


class DamRegistry:
    """Операции реестра ассетов над :class:`DamStore` — связь запись↔бинарь (ребро 7.1).

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    Гейтинг доступа здесь НЕ реализуется: для 955-ассета храним ``rights_template``
    (955^B), чтобы вызывающий скомбинировал с ``access.rights`` (ребро 7.2).
    """

    def __init__(self, store=None, now=None):
        self.store = store or DamStore(':memory:')
        self._now = now or time.time

    def attach(self, db, mfn, kind, ref, pages=None, mime=None,
               rights_template=None):
        """Привязать бинарь к записи (db, mfn). Идемпотентно по (db, mfn, kind, ref).

        ``kind`` ∈ {951,953,955}; ``ref`` — внешний URL/файл (951), идентификатор блоба
        (953) или имя файла ^A (955). ``pages`` — 955^N; ``rights_template`` — 955^B.
        Возвращает строку ассета (новую или уже существовавшую)."""
        if kind not in KINDS:
            raise ValueError('kind должен быть одним из %s' % (KINDS,))
        if ref is None or not str(ref).strip():
            raise ValueError('ref обязателен (где взять бинарь)')
        p = None if pages is None else int(pages)
        return self.store.add(db, mfn, kind, str(ref).strip(), p, mime,
                              rights_template, self._now())

    def assets_for(self, db, mfn):
        """Все бинари записи (db, mfn) — закрытие 7.1: запись↔бинарь.

        Порядок — добавления. Пусто, если у записи нет ассетов."""
        return self.store.for_record(db, mfn)

    def by_kind(self, db, mfn, kind):
        """Ассеты записи (db, mfn) заданного вида (951/953/955)."""
        if kind not in KINDS:
            raise ValueError('kind должен быть одним из %s' % (KINDS,))
        return self.store.for_record_kind(db, mfn, kind)

    def get(self, asset_id):
        """Ассет по id, либо None."""
        return self.store.get(asset_id)

    def remove(self, asset_id):
        """Отвязать (удалить) ассет по id. True, если был удалён."""
        return self.store.delete(asset_id)

    def stats(self):
        """Сводка реестра -> ``{'assets': N, 'by_kind': {951:, 953:, 955:}}``.

        ``by_kind`` всегда несёт все три вида (0 для отсутствующих)."""
        bk = self.store.counts_by_kind()
        by_kind = {k: int(bk.get(k, 0)) for k in KINDS}
        return {'assets': sum(by_kind.values()), 'by_kind': by_kind}
