#!/usr/bin/env python3
"""AUTHORITY CONTROL — авторитетный/нормативный контроль точек доступа
(контур Каталогизатор, issue #359).

Реестр авторитетных (нормативных) заголовков, их вариантов/нерекомендуемых форм
и перекрёстных ссылок «см.»/«см. также» с дедупликацией и слиянием дублей — тот
слой нормативного контроля, который ИРБИС держит в авторитетных файлах. Здесь
сделано own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004),
thread-local соединение, dict-строки, без сети и без новых pip-зависимостей —
в точности как ``vocab_editor.py`` / ``config_store.py``. Никаких
live-ИРБИС-записей.

ОТДЕЛЬНЫЙ own-store модуль: не путать с ``access.authority`` (substitution
pipeline / fill-map ``^3`` из эпика #188) — это самостоятельный реестр точек
доступа.

Зачем
-----
Каталогизатор должен контролировать **точки доступа**: имена персон,
наименования организаций, тематические и географические рубрики. Один и тот же
заголовок не должен задваиваться из-за регистра/пробелов, поэтому всё
дедуплицируется по НОРМАЛИЗОВАННОЙ форме (:func:`normalize_heading`). Варианты
(нерекомендуемые формы) и см.-ссылки сводят разнобой написаний к единому
авторитетному заголовку и связывают смежные заголовки между собой.

Модель
------
  * таблица ``heading`` — авторитетный заголовок; уникален по паре ``(kind, norm)``;
  * таблица ``variant`` — варианты/нерекомендуемые формы; дедуп по
    ``(heading_id, norm)``;
  * таблица ``xref`` — перекрёстные ссылки «см.»/«см. также»; дедуп по
    ``(src_id, dst_id, ref_type)``.

``AuthorityStore`` — низкоуровневый стор (CRUD над тремя таблицами).
``AuthorityService`` — глубина: поиск с подтягиванием вариантов и ссылок,
контроль точек доступа (``find_or_create``) и слияние дублей (``merge``).

Запуск тестов: ``py -3.12 tests/test_authority_control.py``.
"""
import re
import sqlite3
import threading
from datetime import datetime, timezone

# Тип заголовка: персона / организация / тема / географическое название.
KINDS = ('person', 'org', 'subject', 'geo')

# Тип перекрёстной ссылки: «см.» (отсылка к авторитетной форме) и «см. также».
REF_TYPES = ('see', 'see_also')

# Схлопывание пробельных последовательностей при нормализации.
_WS_RE = re.compile(r'\s+')


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


def normalize_heading(s):
    """Нормализовать заголовок для дедупа/поиска.

    Обрезаем крайние пробелы, схлопываем внутренние пробельные последовательности
    в один пробел (regex) и приводим к нижнему регистру через ``casefold``.
    Пустой/``None`` -> ``''``.
    """
    if not s:
        return ''
    collapsed = _WS_RE.sub(' ', str(s).strip())
    return collapsed.casefold()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS heading (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  kind       TEXT NOT NULL,            -- person | org | subject | geo
  heading    TEXT NOT NULL,            -- авторитетная форма (как введена)
  norm       TEXT NOT NULL,            -- нормализованная форма (для дедупа/поиска)
  note       TEXT NOT NULL DEFAULT '', -- примечание/область применения
  created_at TEXT,
  UNIQUE (kind, norm)
);
CREATE INDEX IF NOT EXISTS heading_kind_idx ON heading(kind, norm);

CREATE TABLE IF NOT EXISTS variant (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  heading_id INTEGER NOT NULL,         -- ссылка на авторитетный заголовок
  variant    TEXT NOT NULL,            -- вариант/нерекомендуемая форма (как введена)
  norm       TEXT NOT NULL,            -- нормализованная форма варианта
  created_at TEXT,
  UNIQUE (heading_id, norm)
);
CREATE INDEX IF NOT EXISTS variant_heading_idx ON variant(heading_id);

CREATE TABLE IF NOT EXISTS xref (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  src_id     INTEGER NOT NULL,         -- заголовок-источник ссылки
  dst_id     INTEGER NOT NULL,         -- заголовок-назначение ссылки
  ref_type   TEXT NOT NULL,            -- see | see_also
  created_at TEXT,
  UNIQUE (src_id, dst_id, ref_type)
);
CREATE INDEX IF NOT EXISTS xref_src_idx ON xref(src_id);
"""


class AuthorityStore:
    """Собственный sqlite-стор авторитетных заголовков, вариантов и см.-ссылок.

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах.
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

    # ======================================================================
    # ЗАГОЛОВОК (heading) — авторитетная точка доступа
    # ======================================================================
    def add(self, kind, heading, note=''):
        """Добавить авторитетный заголовок.

        ``ValueError`` если ``kind`` не из :data:`KINDS` или ``heading`` пуст
        (после ``strip``). Дедуп: если заголовок с такой парой ``(kind, norm)``
        уже есть — возвращается СУЩЕСТВУЮЩИЙ (а не создаётся дубль).
        """
        if kind not in KINDS:
            raise ValueError('недопустимый kind: %r' % (kind,))
        heading = (heading or '').strip()
        if not heading:
            raise ValueError('пустой heading')
        norm = normalize_heading(heading)
        c = self._conn()
        existing = c.execute(
            'SELECT * FROM heading WHERE kind=? AND norm=?',
            (kind, norm)).fetchone()
        if existing is not None:
            return dict(existing)
        cur = c.execute(
            'INSERT INTO heading(kind,heading,norm,note,created_at) '
            'VALUES(?,?,?,?,?)',
            (kind, heading, norm, note, self._now()))
        c.commit()
        return self.get(cur.lastrowid)

    def get(self, id):
        """Заголовок-dict по ``id`` или ``None``."""
        r = self._conn().execute(
            'SELECT * FROM heading WHERE id=?', (id,)).fetchone()
        return dict(r) if r else None

    def list(self, kind=None, q=None, limit=200):
        """Список заголовков с фильтром по ``kind`` и подстроке ``q``.

        ``q`` ищется как подстрока по нормализованной форме ``norm`` (сама ``q``
        тоже нормализуется через :func:`normalize_heading`). Сортировка по
        ``heading``.
        """
        sql = 'SELECT * FROM heading'
        clauses = []
        params = []
        if kind is not None:
            clauses.append('kind=?')
            params.append(kind)
        if q:
            clauses.append('norm LIKE ?')
            params.append('%' + normalize_heading(q) + '%')
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY heading LIMIT ?'
        params.append(limit)
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def update_note(self, id, note):
        """Обновить примечание заголовка. -> обновлённый dict или ``None``."""
        if self.get(id) is None:
            return None
        c = self._conn()
        c.execute('UPDATE heading SET note=? WHERE id=?', (note, id))
        c.commit()
        return self.get(id)

    def remove(self, id):
        """Удалить заголовок каскадно (его варианты и ссылки, где он src/dst).

        -> ``True``, если заголовок был удалён, иначе ``False``.
        """
        if self.get(id) is None:
            return False
        c = self._conn()
        c.execute('DELETE FROM variant WHERE heading_id=?', (id,))
        c.execute('DELETE FROM xref WHERE src_id=? OR dst_id=?', (id, id))
        c.execute('DELETE FROM heading WHERE id=?', (id,))
        c.commit()
        return True

    # ======================================================================
    # ВАРИАНТ (variant) — нерекомендуемая форма заголовка
    # ======================================================================
    def add_variant(self, heading_id, variant):
        """Добавить вариант к заголовку.

        ``None``, если ``heading_id`` не существует. Дедуп по
        ``(heading_id, norm)``: повторный вариант возвращает существующий.
        """
        if self.get(heading_id) is None:
            return None
        norm = normalize_heading(variant)
        c = self._conn()
        existing = c.execute(
            'SELECT * FROM variant WHERE heading_id=? AND norm=?',
            (heading_id, norm)).fetchone()
        if existing is not None:
            return dict(existing)
        cur = c.execute(
            'INSERT INTO variant(heading_id,variant,norm,created_at) '
            'VALUES(?,?,?,?)',
            (heading_id, variant, norm, self._now()))
        c.commit()
        r = c.execute('SELECT * FROM variant WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def variants(self, heading_id):
        """Варианты заголовка (упорядочены по ``variant``)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM variant WHERE heading_id=? ORDER BY variant',
            (heading_id,)).fetchall()]

    def remove_variant(self, id):
        """Удалить вариант. -> ``True``, если что-то удалено."""
        c = self._conn()
        cur = c.execute('DELETE FROM variant WHERE id=?', (id,))
        c.commit()
        return cur.rowcount > 0

    # ======================================================================
    # ССЫЛКА (xref) — перекрёстная ссылка «см.»/«см. также»
    # ======================================================================
    def add_xref(self, src_id, dst_id, ref_type='see_also'):
        """Добавить перекрёстную ссылку ``src -> dst``.

        ``ValueError`` если ``ref_type`` не из :data:`REF_TYPES`, если
        ``src_id == dst_id`` (сообщение ``'self-reference'``) или если какой-либо
        из id не существует. Дедуп по ``(src_id, dst_id, ref_type)``.
        """
        if ref_type not in REF_TYPES:
            raise ValueError('недопустимый ref_type: %r' % (ref_type,))
        if src_id == dst_id:
            raise ValueError('self-reference')
        if self.get(src_id) is None or self.get(dst_id) is None:
            raise ValueError('нет такого заголовка')
        c = self._conn()
        existing = c.execute(
            'SELECT * FROM xref WHERE src_id=? AND dst_id=? AND ref_type=?',
            (src_id, dst_id, ref_type)).fetchone()
        if existing is not None:
            return dict(existing)
        cur = c.execute(
            'INSERT INTO xref(src_id,dst_id,ref_type,created_at) '
            'VALUES(?,?,?,?)',
            (src_id, dst_id, ref_type, self._now()))
        c.commit()
        r = c.execute('SELECT * FROM xref WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def xrefs(self, heading_id):
        """Исходящие ссылки заголовка (где ``heading_id == src_id``)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM xref WHERE src_id=? ORDER BY id',
            (heading_id,)).fetchall()]

    def remove_xref(self, id):
        """Удалить ссылку. -> ``True``, если что-то удалено."""
        c = self._conn()
        cur = c.execute('DELETE FROM xref WHERE id=?', (id,))
        c.commit()
        return cur.rowcount > 0


class AuthorityService:
    """Глубина над :class:`AuthorityStore`: поиск с подтягиванием вариантов и
    ссылок, контроль точек доступа (``find_or_create``) и слияние дублей
    (``merge``). Делегирует CRUD стору; добавляет гарантии для вызывающих.
    """

    def __init__(self, store=None, now=None):
        self.store = store or AuthorityStore(':memory:', now=now)

    def create(self, kind, heading, note=''):
        """Создать заголовок (делегирует ``add``, дедуп по ``(kind, norm)``)."""
        return self.store.add(kind, heading, note=note)

    def search(self, kind=None, q=None):
        """Поиск заголовков с подтянутыми вариантами и см.-ссылками.

        Для каждого найденного заголовка возвращается его dict, дополненный:
          * ``'variants'`` — список dict-вариантов;
          * ``'see_also'`` — список ``{'id','heading','ref_type'}`` по исходящим
            ссылкам (название ``heading`` подтягивается у заголовка-назначения).
        """
        out = []
        for h in self.store.list(kind=kind, q=q):
            row = dict(h)
            row['variants'] = self.store.variants(h['id'])
            see_also = []
            for x in self.store.xrefs(h['id']):
                dst = self.store.get(x['dst_id'])
                see_also.append({
                    'id': x['dst_id'],
                    'heading': dst['heading'] if dst else None,
                    'ref_type': x['ref_type'],
                })
            row['see_also'] = see_also
            out.append(row)
        return out

    def add_variant(self, heading_id, variant):
        """Добавить вариант к заголовку (делегирует стор). -> dict или ``None``."""
        return self.store.add_variant(heading_id, variant)

    def link(self, src_id, dst_id, ref_type='see_also'):
        """Связать заголовки см.-ссылкой (делегирует ``add_xref``)."""
        return self.store.add_xref(src_id, dst_id, ref_type=ref_type)

    def find_or_create(self, kind, heading):
        """Контроль точки доступа: вернуть существующий заголовок по
        ``(kind, norm)`` либо создать новый.

        В ответ добавляется ключ ``'created'``: ``True``, если заголовок создан
        в этом вызове, ``False`` — если найден существующий.
        """
        if kind not in KINDS:
            raise ValueError('недопустимый kind: %r' % (kind,))
        norm = normalize_heading(heading)
        existing = self.store._conn().execute(
            'SELECT * FROM heading WHERE kind=? AND norm=?',
            (kind, norm)).fetchone()
        if existing is not None:
            row = dict(existing)
            row['created'] = False
            return row
        row = dict(self.store.add(kind, heading))
        row['created'] = True
        return row

    def merge(self, keep_id, drop_id):
        """Слить дубли: перенести содержимое ``drop`` в ``keep`` и удалить ``drop``.

        Шаги:
          * варианты ``drop`` переносятся в ``keep`` (как ``add_variant``, дедуп);
          * сам заголовок ``drop`` добавляется ВАРИАНТОМ к ``keep``;
          * исходящие/входящие ссылки ``drop`` перецепляются на ``keep``
            (ставшие self-ссылками пропускаются), с дедупом;
          * ``drop`` удаляется каскадно.

        ``ValueError`` если ``keep_id == drop_id`` или какой-либо из id не
        существует. -> ``{'kept': keep_dict, 'moved_variants': N, 'merged': True}``.
        """
        if keep_id == drop_id:
            raise ValueError('keep == drop')
        keep = self.store.get(keep_id)
        drop = self.store.get(drop_id)
        if keep is None or drop is None:
            raise ValueError('нет такого заголовка')

        moved = 0
        # Переносим варианты drop -> keep (дедуп через add_variant).
        for v in self.store.variants(drop_id):
            self.store.add_variant(keep_id, v['variant'])
            moved += 1
        # Сам заголовок drop становится вариантом keep.
        self.store.add_variant(keep_id, drop['heading'])

        # Перецепляем ссылки drop -> keep, пропуская ставшие self-ссылками.
        rows = self.store._conn().execute(
            'SELECT * FROM xref WHERE src_id=? OR dst_id=?',
            (drop_id, drop_id)).fetchall()
        for x in rows:
            new_src = keep_id if x['src_id'] == drop_id else x['src_id']
            new_dst = keep_id if x['dst_id'] == drop_id else x['dst_id']
            if new_src != new_dst:
                try:
                    self.store.add_xref(new_src, new_dst, ref_type=x['ref_type'])
                except ValueError:
                    pass
        # Старые ссылки drop удалятся вместе с заголовком при remove (каскад).
        self.store.remove(drop_id)

        return {
            'kept': self.store.get(keep_id),
            'moved_variants': moved,
            'merged': True,
        }
