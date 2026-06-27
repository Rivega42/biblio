#!/usr/bin/env python3
"""VOCAB EDITOR — редактор словарей ``.mnu`` и классификационных деревьев ``.tre``
(контур Каталогизатор).

Own-store CRUD над:

  * **значениями словаря** (``.mnu`` — пары код/наименование, напр. виды документа,
    языки, страны): добавление/переименование/деактивация/удаление, упорядочивание
    через ``sort``, мягкое выключение через ``active`` (значение не теряется в
    историзированных записях, но скрыто из выпадающих списков);
  * **узлами классификационного дерева** (``.tre`` — ГРНТИ/УДК/ББК): добавление узла
    с вычислением ``depth`` и материализованного точечного ``path`` из кодов,
    перенос ветви (``move_node`` с пересчётом ``depth``/``path`` потомков), выборка
    поддерева по префиксу ``path``.

Зеркалит модель ``access.store`` (таблицы ``vocabulary_value`` /
``classification_node``), но это ОТДЕЛЬНЫЙ own-store модуль — чистый stdlib +
``sqlite3``, thread-local соединение, dict-строки, без сети и pip-зависимостей,
ровно как ``pay.py`` / ``circulation.py`` (dev-паритет, ADR-004).

Запуск тестов: ``py -3.12 tests/test_vocab_editor.py``.
"""
import sqlite3
import threading
import time

# Источник значения/узла (как в store.vocabulary_value.origin): значение,
# созданное редактором вручную, помечается 'custom' — чтобы реседирование (SPEC
# §3.3) его не затирало.
ORIGIN_SEED = 'seed'
ORIGIN_IMPORTED = 'imported'
ORIGIN_CUSTOM = 'custom'


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS vocab_value (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  vocab  TEXT NOT NULL,             -- имя словаря (.mnu)
  code   TEXT NOT NULL,             -- код значения
  label  TEXT NOT NULL,             -- наименование значения
  sort   INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  origin TEXT NOT NULL DEFAULT 'custom',
  UNIQUE (vocab, code)
);
CREATE INDEX IF NOT EXISTS vocab_value_vocab_idx ON vocab_value(vocab, sort);

CREATE TABLE IF NOT EXISTS class_node (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tree        TEXT NOT NULL,        -- имя дерева (.tre): ГРНТИ/УДК/ББК
  code        TEXT NOT NULL,        -- код узла
  label       TEXT NOT NULL,        -- рубрика
  parent_code TEXT,                 -- код родителя (NULL у корня)
  depth       INTEGER NOT NULL DEFAULT 0,
  path        TEXT NOT NULL,        -- материализованный точечный путь из кодов
  sort        INTEGER NOT NULL DEFAULT 0,
  UNIQUE (tree, code)
);
CREATE INDEX IF NOT EXISTS class_node_tree_idx ON class_node(tree, parent_code);
CREATE INDEX IF NOT EXISTS class_node_path_idx ON class_node(tree, path);
"""


class VocabStore:
    """Собственный sqlite-стор значений словаря и узлов дерева.

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки возвращаются как dict.
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

    # ---- словарь (.mnu) ----------------------------------------------------
    def value_get(self, vocab, code):
        r = self._conn().execute(
            'SELECT * FROM vocab_value WHERE vocab=? AND code=?',
            (vocab, code)).fetchone()
        return dict(r) if r else None

    def value_upsert(self, vocab, code, label, sort, active, origin):
        """Idempotent insert/update значения по ключу (vocab, code)."""
        c = self._conn()
        c.execute(
            'INSERT INTO vocab_value(vocab,code,label,sort,active,origin) '
            'VALUES(?,?,?,?,?,?) ON CONFLICT(vocab,code) DO UPDATE SET '
            'label=excluded.label, sort=excluded.sort, active=excluded.active',
            (vocab, code, label, sort, 1 if active else 0, origin))
        c.commit()
        return self.value_get(vocab, code)

    def value_set_label(self, vocab, code, label):
        c = self._conn()
        c.execute('UPDATE vocab_value SET label=? WHERE vocab=? AND code=?',
                  (label, vocab, code))
        c.commit()
        return self.value_get(vocab, code)

    def value_set_active(self, vocab, code, active):
        c = self._conn()
        c.execute('UPDATE vocab_value SET active=? WHERE vocab=? AND code=?',
                  (1 if active else 0, vocab, code))
        c.commit()
        return self.value_get(vocab, code)

    def values(self, vocab, active_only=False):
        sql = ('SELECT * FROM vocab_value WHERE vocab=?'
               + (' AND active=1' if active_only else '')
               + ' ORDER BY sort, code')
        return [dict(r) for r in self._conn().execute(sql, (vocab,)).fetchall()]

    def value_delete(self, vocab, code):
        c = self._conn()
        cur = c.execute('DELETE FROM vocab_value WHERE vocab=? AND code=?',
                        (vocab, code))
        c.commit()
        return cur.rowcount

    # ---- дерево (.tre) -----------------------------------------------------
    def node_get(self, tree, code):
        r = self._conn().execute(
            'SELECT * FROM class_node WHERE tree=? AND code=?',
            (tree, code)).fetchone()
        return dict(r) if r else None

    def node_upsert(self, tree, code, label, parent_code, depth, path, sort):
        c = self._conn()
        c.execute(
            'INSERT INTO class_node(tree,code,label,parent_code,depth,path,sort) '
            'VALUES(?,?,?,?,?,?,?) ON CONFLICT(tree,code) DO UPDATE SET '
            'label=excluded.label, parent_code=excluded.parent_code, '
            'depth=excluded.depth, path=excluded.path, sort=excluded.sort',
            (tree, code, label, parent_code, depth, path, sort))
        c.commit()
        return self.node_get(tree, code)

    def node_set(self, tree, code, parent_code, depth, path):
        """Точечный апдейт parent/depth/path (для move_node, без трогания label/sort)."""
        c = self._conn()
        c.execute('UPDATE class_node SET parent_code=?, depth=?, path=? '
                  'WHERE tree=? AND code=?',
                  (parent_code, depth, path, tree, code))
        c.commit()
        return self.node_get(tree, code)

    def children(self, tree, parent_code):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM class_node WHERE tree=? AND '
            + ('parent_code IS NULL' if parent_code is None else 'parent_code=?')
            + ' ORDER BY sort, code',
            (tree,) if parent_code is None else (tree, parent_code)).fetchall()]

    def subtree(self, tree, path):
        """Узел с данным path + все его потомки (по префиксу ``path + '.'``)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM class_node WHERE tree=? AND (path=? OR path LIKE ?) '
            'ORDER BY path',
            (tree, path, path + '.%')).fetchall()]

    def node_delete_subtree(self, tree, path):
        c = self._conn()
        cur = c.execute(
            'DELETE FROM class_node WHERE tree=? AND (path=? OR path LIKE ?)',
            (tree, path, path + '.%'))
        c.commit()
        return cur.rowcount

    def max_sort(self, tree, parent_code):
        r = self._conn().execute(
            'SELECT COALESCE(MAX(sort),-1) AS m FROM class_node WHERE tree=? AND '
            + ('parent_code IS NULL' if parent_code is None else 'parent_code=?'),
            (tree,) if parent_code is None else (tree, parent_code)).fetchone()
        return int(r['m'])


class VocabEditor:
    """Операции редактирования над :class:`VocabStore`.

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах —
    зарезервировано на случай меток времени; модель CRUD сама по себе детерминирована.
    """

    def __init__(self, store=None, now=None):
        self.store = store or VocabStore(':memory:')
        self._now = now or time.time

    # ======================================================================
    # СЛОВАРЬ (.mnu) — значения код/наименование
    # ======================================================================
    def add_value(self, vocab, code, label, sort=None, origin=ORIGIN_CUSTOM):
        """Добавить значение словаря. ``sort=None`` -> в конец (max+1).

        Идемпотентно по (vocab, code): повторный вызов обновит label/sort.
        """
        if sort is None:
            sort = self._next_value_sort(vocab)
        return self.store.value_upsert(vocab, code, label, sort, True, origin)

    def _next_value_sort(self, vocab):
        vals = self.store.values(vocab)
        return (max(v['sort'] for v in vals) + 1) if vals else 0

    def rename(self, vocab, code, label):
        """Переименовать значение (поменять только наименование)."""
        if self.store.value_get(vocab, code) is None:
            raise KeyError('no such value: %s/%s' % (vocab, code))
        return self.store.value_set_label(vocab, code, label)

    def deactivate(self, vocab, code):
        """Мягко выключить значение (active=0) — скрыть из списков, не удаляя."""
        if self.store.value_get(vocab, code) is None:
            raise KeyError('no such value: %s/%s' % (vocab, code))
        return self.store.value_set_active(vocab, code, False)

    def activate(self, vocab, code):
        """Снова включить ранее деактивированное значение."""
        if self.store.value_get(vocab, code) is None:
            raise KeyError('no such value: %s/%s' % (vocab, code))
        return self.store.value_set_active(vocab, code, True)

    def values(self, vocab, active_only=False):
        """Значения словаря, упорядоченные по (sort, code)."""
        return self.store.values(vocab, active_only=active_only)

    def remove(self, vocab, code):
        """Жёстко удалить значение из словаря. -> True, если что-то удалено."""
        return self.store.value_delete(vocab, code) > 0

    # ======================================================================
    # ДЕРЕВО (.tre) — узлы классификации (ГРНТИ/УДК/ББК)
    # ======================================================================
    def add_node(self, tree, code, label, parent_code=None, sort=None):
        """Добавить узел дерева. Вычисляет ``depth`` и материализованный точечный
        ``path`` из кодов (``parent.path + '.' + code``; корень -> ``code``).

        Идемпотентно по (tree, code): повторный вызов обновит label, но НЕ
        переносит узел (для переноса -> :meth:`move_node`).
        """
        if parent_code is None:
            depth = 0
            path = code
        else:
            parent = self.store.node_get(tree, parent_code)
            if parent is None:
                raise KeyError('no such parent: %s/%s' % (tree, parent_code))
            depth = parent['depth'] + 1
            path = parent['path'] + '.' + code

        existing = self.store.node_get(tree, code)
        if existing is not None:
            # Идемпотентно: обновляем только подпись, оставляя место в дереве.
            return self.store.node_upsert(
                tree, code, label, existing['parent_code'],
                existing['depth'], existing['path'], existing['sort'])

        if sort is None:
            sort = self.store.max_sort(tree, parent_code) + 1
        return self.store.node_upsert(tree, code, label, parent_code,
                                      depth, path, sort)

    def children(self, tree, parent_code=None):
        """Прямые потомки узла (``parent_code=None`` -> корни дерева)."""
        return self.store.children(tree, parent_code)

    def subtree(self, tree, code):
        """Узел + все его потомки (по префиксу материализованного ``path``)."""
        node = self.store.node_get(tree, code)
        if node is None:
            raise KeyError('no such node: %s/%s' % (tree, code))
        return self.store.subtree(tree, node['path'])

    def move_node(self, tree, code, new_parent_code):
        """Перенести узел под нового родителя (``None`` -> в корень) и пересчитать
        ``depth``/``path`` у самого узла И всех его потомков.

        Потомки находятся по СТАРОМУ префиксу path до переноса; затем у каждого
        старый префикс заменяется на новый.
        """
        node = self.store.node_get(tree, code)
        if node is None:
            raise KeyError('no such node: %s/%s' % (tree, code))

        if new_parent_code is None:
            new_depth = 0
            new_path = code
        else:
            if new_parent_code == code:
                raise ValueError('cannot move node under itself')
            parent = self.store.node_get(tree, new_parent_code)
            if parent is None:
                raise KeyError('no such parent: %s/%s' % (tree, new_parent_code))
            # Запрет переноса в собственное поддерево (создал бы цикл).
            if parent['path'] == node['path'] or \
                    parent['path'].startswith(node['path'] + '.'):
                raise ValueError('cannot move node into its own subtree')
            new_depth = parent['depth'] + 1
            new_path = parent['path'] + '.' + code

        old_path = node['path']
        old_depth = node['depth']
        # Сначала потомки (по старому префиксу), потом сам узел.
        descendants = [n for n in self.store.subtree(tree, old_path)
                       if n['code'] != code]
        for d in descendants:
            d_path = new_path + d['path'][len(old_path):]
            d_depth = d['depth'] - old_depth + new_depth
            self.store.node_set(tree, d['code'], d['parent_code'],
                                d_depth, d_path)
        return self.store.node_set(tree, code, new_parent_code,
                                   new_depth, new_path)

    def remove_node(self, tree, code):
        """Удалить узел вместе со всем его поддеревом. -> число удалённых узлов."""
        node = self.store.node_get(tree, code)
        if node is None:
            return 0
        return self.store.node_delete_subtree(tree, node['path'])
