#!/usr/bin/env python3
"""ROLES — собственная модель ролевого доступа для АРМ «Администратор».

Постоянный (редактируемый) слой ролей, который стоит РЯДОМ с захардкоженными
грантами из ``access/authz.py`` (тот модуль НЕ редактируется). ``authz.py`` даёт
неизменяемые наборы грантов для гостя/читателя и чистые функции разрешения
(``best_grant``/``authorize``); здесь — богатая, хранимая в БД иерархия ролей с
наследованием, которую администратор может править через UI.

Дизайн (домашний стиль, в точности как ``pay.py``/``reader_registry.py``):
чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей. Соединение thread-local, строки -> dict, инжектируемые часы
``now`` для детерминизма в тестах. Никаких записей в живой ИРБИС.

Модель грантов
--------------
Грант = (function x db x level), где ``level`` ∈ {read, write, admin}. Семантика
ровно как в ``authz.py``: точный ``db`` бьёт ``'*'``; уровни упорядочены
``read < write < admin``; для разрешения берётся «лучший» грант. ``RoleService``
повторяет эту семантику, но поверх грантов, выведенных из ролей аккаунта
(включая унаследованные по цепочке ``parent_id``).
"""
import sqlite3
import threading
import datetime

# Упорядочивание уровней (зеркало authz.LEVEL_RANK: read < write < admin).
LEVEL_RANK = {'read': 1, 'write': 2, 'admin': 3}
LEVELS = ('read', 'write', 'admin')


def _utcnow():
    """ISO8601-метка времени UTC (инжектируемые часы по умолчанию)."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS role (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE,     -- машинное имя роли
  description TEXT NOT NULL DEFAULT '',
  parent_id   INTEGER,                  -- родитель для наследования (NULL = корень)
  created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_grant (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  role_id   INTEGER NOT NULL,
  function  TEXT NOT NULL,              -- имя функции (как в authz)
  db        TEXT NOT NULL DEFAULT '*',  -- конкретная БД или '*' (любая)
  level     TEXT NOT NULL DEFAULT 'read',  -- read | write | admin
  UNIQUE(role_id, function, db)
);
CREATE INDEX IF NOT EXISTS role_grant_role_idx ON role_grant(role_id);
CREATE TABLE IF NOT EXISTS account_role (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  account     TEXT NOT NULL,            -- логин/учётка
  role_id     INTEGER NOT NULL,
  assigned_at TEXT NOT NULL,
  UNIQUE(account, role_id)
);
CREATE INDEX IF NOT EXISTS account_role_account_idx ON account_role(account);
"""


class RoleStore:
    """Собственный sqlite-стор ролевой модели. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.

    ``now`` инжектируется (по умолчанию :func:`_utcnow`) — чтобы тесты могли
    передать фиксированные часы для детерминизма.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._local = threading.local()
        self._now = now or _utcnow
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

    # --- роли -----------------------------------------------------------

    def _resolve_role_id(self, role):
        """Внутреннее: id роли по dict / id (int) / имени (str) или ``None``."""
        if isinstance(role, dict):
            return role.get('id')
        r = self.get_role(role)
        return r['id'] if r else None

    def create_role(self, name, description='', parent=None):
        """Создать роль. ``parent`` — dict/id/имя родителя или ``None`` (корень).

        Возвращает созданную запись-dict."""
        parent_id = None
        if parent is not None:
            parent_id = self._resolve_role_id(parent)
            if parent_id is None:
                raise ValueError('parent role not found: %r' % (parent,))
        c = self._conn()
        cur = c.execute(
            'INSERT INTO role(name,description,parent_id,created_at) '
            'VALUES(?,?,?,?)',
            (name, description, parent_id, self._now()))
        c.commit()
        return self._role_by_id(cur.lastrowid)

    def _role_by_id(self, role_id):
        r = self._conn().execute(
            'SELECT * FROM role WHERE id=?', (role_id,)).fetchone()
        return dict(r) if r else None

    def get_role(self, id_or_name):
        """Роль по id (int/число) или по имени (str) -> dict | None."""
        if id_or_name is None:
            return None
        if isinstance(id_or_name, dict):
            id_or_name = id_or_name.get('id')
        c = self._conn()
        # int -> поиск по id; строка-число тоже трактуем как id.
        if isinstance(id_or_name, int) and not isinstance(id_or_name, bool):
            r = c.execute('SELECT * FROM role WHERE id=?',
                          (id_or_name,)).fetchone()
            return dict(r) if r else None
        r = c.execute('SELECT * FROM role WHERE name=?',
                      (id_or_name,)).fetchone()
        return dict(r) if r else None

    def list_roles(self):
        """Все роли (по id)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM role ORDER BY id').fetchall()]

    # --- гранты ---------------------------------------------------------

    def add_grant(self, role, function, db='*', level='read'):
        """Добавить/обновить грант роли. Идемпотентно по (role, function, db):
        повторный вызов обновляет уровень. Возвращает строку гранта."""
        role_id = self._resolve_role_id(role)
        if role_id is None:
            raise ValueError('role not found: %r' % (role,))
        if level not in LEVEL_RANK:
            raise ValueError('unknown level: %r' % (level,))
        c = self._conn()
        c.execute(
            'INSERT INTO role_grant(role_id,function,db,level) VALUES(?,?,?,?) '
            'ON CONFLICT(role_id,function,db) DO UPDATE SET level=excluded.level',
            (role_id, function, db, level))
        c.commit()
        r = c.execute(
            'SELECT * FROM role_grant WHERE role_id=? AND function=? AND db=?',
            (role_id, function, db)).fetchone()
        return dict(r) if r else None

    def remove_grant(self, role, function, db):
        """Удалить грант роли по (function, db)."""
        role_id = self._resolve_role_id(role)
        if role_id is None:
            raise ValueError('role not found: %r' % (role,))
        c = self._conn()
        c.execute(
            'DELETE FROM role_grant WHERE role_id=? AND function=? AND db=?',
            (role_id, function, db))
        c.commit()

    def role_grants(self, role):
        """Гранты, заданные НЕПОСРЕДСТВЕННО на роли (без наследования)."""
        role_id = self._resolve_role_id(role)
        if role_id is None:
            raise ValueError('role not found: %r' % (role,))
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM role_grant WHERE role_id=? ORDER BY id',
            (role_id,)).fetchall()]

    # --- назначение ролей аккаунтам -------------------------------------

    def assign(self, account, role):
        """Назначить роль аккаунту. Идемпотентно: повторное назначение не
        бросает (UNIQUE + ON CONFLICT DO NOTHING)."""
        role_id = self._resolve_role_id(role)
        if role_id is None:
            raise ValueError('role not found: %r' % (role,))
        c = self._conn()
        c.execute(
            'INSERT INTO account_role(account,role_id,assigned_at) '
            'VALUES(?,?,?) ON CONFLICT(account,role_id) DO NOTHING',
            (account, role_id, self._now()))
        c.commit()

    def unassign(self, account, role):
        """Снять роль с аккаунта."""
        role_id = self._resolve_role_id(role)
        if role_id is None:
            raise ValueError('role not found: %r' % (role,))
        c = self._conn()
        c.execute('DELETE FROM account_role WHERE account=? AND role_id=?',
                  (account, role_id))
        c.commit()

    def account_roles(self, account):
        """Список ролей-dict, НЕПОСРЕДСТВЕННО назначенных аккаунту."""
        rows = self._conn().execute(
            'SELECT r.* FROM role r JOIN account_role a ON a.role_id=r.id '
            'WHERE a.account=? ORDER BY r.id', (account,)).fetchall()
        return [dict(r) for r in rows]


class RoleService:
    """Бизнес-логика поверх :class:`RoleStore` — наследование ролей,
    эффективные гранты и проверка разрешений.

    Семантика разрешений зеркалит ``access/authz.py`` (точный ``db`` бьёт
    ``'*'``; ``read < write < admin``), но работает поверх грантов, выведенных
    из всех ролей аккаунта с учётом наследования по ``parent_id``.
    """

    def __init__(self, store=None, now=None):
        self.store = store or RoleStore(':memory:', now=now)

    # --- наследование ---------------------------------------------------

    def resolve_role_chain(self, role):
        """Цепочка ролей-dict от ``role`` вверх по родителям (для UI «роль
        наследует от…»). Защита от циклов через visited-множество id.

        Первой идёт сама роль, затем её родитель и т.д. до корня."""
        chain = []
        visited = set()
        cur = self.store.get_role(role)
        if cur is None:
            raise ValueError('role not found: %r' % (role,))
        while cur is not None and cur['id'] not in visited:
            visited.add(cur['id'])
            chain.append(cur)
            parent_id = cur.get('parent_id')
            if parent_id is None:
                break
            cur = self.store.get_role(parent_id)
        return chain

    def _role_chain_ids(self, role_id):
        """Внутреннее: множество id роли + всех её предков (защита от циклов)."""
        ids = []
        visited = set()
        cur_id = role_id
        while cur_id is not None and cur_id not in visited:
            visited.add(cur_id)
            ids.append(cur_id)
            r = self.store.get_role(cur_id)
            if r is None:
                break
            cur_id = r.get('parent_id')
        return ids

    # --- эффективные гранты ---------------------------------------------

    def effective_grants(self, account):
        """ОБЪЕДИНЕНИЕ грантов всех ролей аккаунта, ВКЛЮЧАЯ унаследованные
        (обход вверх по ``parent_id`` с защитой от циклов).

        При совпадении (function, db) на разных уровнях побеждает БОЛЕЕ
        ПРАВОМОЧНЫЙ уровень (admin > write > read). Возвращает список dict-ов
        вида ``{'function','db','level'}`` (без id роли — это сведённый набор)."""
        # Собираем id всех ролей с учётом наследования.
        role_ids = []
        seen_roles = set()
        for r in self.store.account_roles(account):
            for rid in self._role_chain_ids(r['id']):
                if rid not in seen_roles:
                    seen_roles.add(rid)
                    role_ids.append(rid)
        # Сводим гранты: ключ (function, db) -> самый правомочный level.
        best = {}
        for rid in role_ids:
            role = self.store._role_by_id(rid)
            if role is None:
                continue
            for g in self.store.role_grants(role):
                key = (g['function'], g['db'])
                cur = best.get(key)
                if cur is None or LEVEL_RANK.get(g['level'], 0) > LEVEL_RANK.get(cur, 0):
                    best[key] = g['level']
        return [{'function': fn, 'db': db, 'level': lvl}
                for (fn, db), lvl in best.items()]

    # --- проверка разрешений (зеркало authz.best_grant/authorize) -------

    def _best_grant(self, grants, function, db):
        """Лучший грант для (function, db): точный db бьёт ``'*'``, среди
        кандидатов — максимальный уровень. Зеркало ``authz.best_grant``."""
        cands = [g for g in grants
                 if g['function'] == function and g['db'] in (db, '*')]
        if not cands:
            return None
        exact = [g for g in cands if g['db'] == db]
        pool = exact or cands                      # точный db бьёт '*'
        return max(pool, key=lambda g: LEVEL_RANK.get(g['level'], 0))

    def has_permission(self, account, function, db, level):
        """Есть ли у аккаунта право (function, db) с уровнем >= ``level``.

        Разрешает по сведённым эффективным грантам (с наследованием),
        применяя best-grant-логику ``authz``: точный db бьёт ``'*'``, уровень
        упорядочен read < write < admin."""
        grants = self.effective_grants(account)
        g = self._best_grant(grants, function, db)
        if not g:
            return False
        return LEVEL_RANK.get(g['level'], 0) >= LEVEL_RANK.get(level, 99)

    # --- тонкие проксирующие обёртки над стором (удобство API) ----------

    def create_role(self, name, description='', parent=None):
        return self.store.create_role(name, description=description,
                                      parent=parent)

    def get_role(self, id_or_name):
        return self.store.get_role(id_or_name)

    def list_roles(self):
        return self.store.list_roles()

    def add_grant(self, role, function, db='*', level='read'):
        return self.store.add_grant(role, function, db=db, level=level)

    def remove_grant(self, role, function, db):
        return self.store.remove_grant(role, function, db)

    def role_grants(self, role):
        return self.store.role_grants(role)

    def assign(self, account, role):
        return self.store.assign(account, role)

    def unassign(self, account, role):
        return self.store.unassign(account, role)

    def account_roles(self, account):
        return self.store.account_roles(account)
