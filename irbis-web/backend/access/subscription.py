#!/usr/bin/env python3
"""SUBSCRIPTION — подписка на периодику в контуре Комплектования (kardex).

Контур Комплектование (подписка/периодика) в ИРБИС64: библиотека оформляет
ПОДПИСКУ на сериальное издание у поставщика, заранее заводит ОЖИДАЕМЫЕ номера
выпусков (план поступлений) и по мере прихода РЕГИСТРИРУЕТ поступление каждого
выпуска. Незакрытые ожидания — это «дыры» в kardex-картотеке (номер ждали, но не
получили), по которым комплектатор шлёт рекламацию поставщику.

Зачем отдельно от ``serials.py``
--------------------------------
``serials`` моделирует БИБЛИОГРАФИЧЕСКУЮ сериальную иерархию: сводная запись
журнала <-> запись номера (рёбра 461/46), то есть уже ОПИСАННЫЕ выпуски в
каталоге. Здесь — КОМПЛЕКТОВАТЕЛЬНЫЙ контур: договор подписки с поставщиком,
ПЛАН ожидаемых номеров и факт их поступления (kardex). Это разные сущности:
подписка живёт до того, как номер вообще пришёл и был расписан в каталоге.

Own-store, как ``pay.py``/``serials.py``: чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей. Соединение
thread-local (домашний стиль); строки — dict.
"""
import sqlite3
import threading
import time


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS subscription (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,            -- заглавие сериального издания
  issn        TEXT,                     -- ISSN
  supplier_id INTEGER,                  -- поставщик (агентство подписки)
  period_from TEXT,                     -- начало периода подписки
  period_to   TEXT,                     -- конец периода подписки
  copies      INTEGER NOT NULL DEFAULT 1, -- число выписываемых экземпляров
  created_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sub_issue (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  subscription_id INTEGER NOT NULL REFERENCES subscription(id) ON DELETE CASCADE,
  number          TEXT,                 -- номер выпуска
  year            TEXT,                 -- год выпуска
  expected        INTEGER NOT NULL DEFAULT 1, -- ожидаемый по плану подписки
  received        INTEGER NOT NULL DEFAULT 0, -- поступление зарегистрировано
  received_at     REAL,                 -- момент регистрации поступления
  UNIQUE(subscription_id, number, year)
);
CREATE INDEX IF NOT EXISTS sub_issue_sub_idx ON sub_issue(subscription_id);
CREATE INDEX IF NOT EXISTS subscription_title_idx ON subscription(title);
"""


class SubscriptionStore:
    """Собственный sqlite-стор подписки на периодику (подписки + kardex-выпуски).

    ``db_path=':memory:'`` (по умолчанию) или файл; create-on-init.
    Соединение thread-local (домашний стиль); строки — dict.
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
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ---- подписка --------------------------------------------------------- #
    def add_subscription(self, title, issn, supplier_id, period_from,
                         period_to, copies, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO subscription(title,issn,supplier_id,period_from,'
            'period_to,copies,created_at) VALUES(?,?,?,?,?,?,?)',
            (title, issn,
             None if supplier_id is None else int(supplier_id),
             period_from, period_to, int(copies), created_at))
        c.commit()
        return self.get_subscription(cur.lastrowid)

    def get_subscription(self, subscription_id):
        r = self._conn().execute(
            'SELECT * FROM subscription WHERE id=?',
            (subscription_id,)).fetchone()
        return dict(r) if r else None

    def subscriptions(self):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM subscription ORDER BY id').fetchall()]

    # ---- выпуск (kardex) -------------------------------------------------- #
    def get_issue(self, subscription_id, number, year):
        r = self._conn().execute(
            'SELECT * FROM sub_issue WHERE subscription_id=? AND number IS ? '
            'AND year IS ?', (subscription_id, number, year)).fetchone()
        return dict(r) if r else None

    def add_issue(self, subscription_id, number, year, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO sub_issue(subscription_id,number,year,expected,'
            'received) VALUES(?,?,?,1,0)',
            (subscription_id, number, year))
        c.commit()
        r = c.execute('SELECT * FROM sub_issue WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def mark_received(self, issue_id, received_at):
        c = self._conn()
        c.execute('UPDATE sub_issue SET received=1, received_at=? WHERE id=?',
                  (received_at, issue_id))
        c.commit()
        r = c.execute('SELECT * FROM sub_issue WHERE id=?',
                      (issue_id,)).fetchone()
        return dict(r) if r else None

    def issues(self, subscription_id):
        """Выпуски подписки хронологически: по году, затем номеру, затем id."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM sub_issue WHERE subscription_id=? '
            'ORDER BY year, number, id', (subscription_id,)).fetchall()]

    def pending_issues(self, subscription_id):
        """Ожидаемые, но НЕ поступившие выпуски (kardex-дыры)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM sub_issue WHERE subscription_id=? AND expected=1 '
            'AND received=0 ORDER BY year, number, id',
            (subscription_id,)).fetchall()]

    def counts(self):
        subs = int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM subscription').fetchone()['n'])
        issues = int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM sub_issue').fetchone()['n'])
        received = int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM sub_issue WHERE received=1').fetchone()['n'])
        pending = int(self._conn().execute(
            'SELECT COUNT(*) AS n FROM sub_issue WHERE expected=1 '
            'AND received=0').fetchone()['n'])
        return subs, issues, received, pending


class SubscriptionService:
    """Операции подписки на периодику над :class:`SubscriptionStore`.

    Оформление подписки на сериальное издание, авто-генерация плана ожидаемых
    номеров и регистрация поступления выпусков (kardex). ``now`` инжектируется
    (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or SubscriptionStore(':memory:')
        self._now = now or time.time

    # -- оформление подписки ----------------------------------------------- #
    def subscribe(self, title, issn=None, supplier_id=None, period_from=None,
                  period_to=None, copies=1):
        """Оформить подписку на сериальное издание. Возвращает строку подписки."""
        return self.store.add_subscription(
            title,
            None if issn is None else str(issn),
            supplier_id,
            None if period_from is None else str(period_from),
            None if period_to is None else str(period_to),
            copies, self._now())

    def list_subscriptions(self):
        """Все подписки (по id)."""
        return self.store.subscriptions()

    def get(self, subscription_id):
        """Подписка + число выпусков/поступлений (или ``None``, если не найдена)."""
        s = self.store.get_subscription(subscription_id)
        if s is None:
            return None
        s = dict(s)
        iss = self.store.issues(subscription_id)
        s['issues_count'] = len(iss)
        s['received_count'] = sum(1 for i in iss if i['received'])
        return s

    def find(self, query):
        """Поиск подписок по подстроке заглавия (кириллица — фильтр в Python).

        SQLite-овский LIKE регистронезависим только для ASCII, поэтому
        подстроку заглавия фильтруем в Python (как ``serials.find``).
        """
        rows = self.store.subscriptions()
        if query:
            needle = query.lower()
            rows = [r for r in rows if needle in (r['title'] or '').lower()]
        return rows

    # -- план ожидаемых номеров (kardex) ----------------------------------- #
    def generate_issues(self, subscription_id, numbers, year):
        """Авто-создать ОЖИДАЕМЫЕ номера (expected=1, received=0) по списку.

        Это и есть «авто-создание номеров» в контуре подписки: заранее заводим
        план поступлений. Идемпотентно по ``(subscription_id, number, year)`` —
        повтор не задваивает, уже заведённый номер остаётся как есть.

        Возвращает список выпусков плана (новые + уже существовавшие) в порядке
        переданных номеров; ``None``, если подписки с таким id нет.
        """
        if self.store.get_subscription(subscription_id) is None:
            return None
        year = None if year is None else str(year)
        out = []
        for number in numbers:
            number = None if number is None else str(number)
            existing = self.store.get_issue(subscription_id, number, year)
            if existing is not None:
                out.append(existing)
                continue
            out.append(self.store.add_issue(
                subscription_id, number, year, self._now()))
        return out

    # -- регистрация поступления (kardex) ---------------------------------- #
    def receive_issue(self, subscription_id, number, year):
        """Отметить ПОСТУПЛЕНИЕ выпуска (received=1, received_at=now).

        Возвращает обновлённую строку выпуска; ``None``, если такого
        ожидаемого номера в плане подписки нет.
        """
        year = None if year is None else str(year)
        number = None if number is None else str(number)
        issue = self.store.get_issue(subscription_id, number, year)
        if issue is None:
            return None
        return self.store.mark_received(issue['id'], self._now())

    def pending(self, subscription_id):
        """Ожидаемые, но НЕ поступившие номера (kardex-дыры под рекламацию)."""
        return self.store.pending_issues(subscription_id)

    def stats(self):
        """Сводка: ``{subscriptions, issues, received, pending}``."""
        subs, issues, received, pending = self.store.counts()
        return {'subscriptions': subs, 'issues': issues,
                'received': received, 'pending': pending}
