#!/usr/bin/env python3
"""Единая идентичность: связь учётки сотрудника с читательским билетом (узел 3
MVP-3). Один человек может быть И сотрудником, И читателем — тогда из staff-сессии
он может «посмотреть как читатель» (QA) и видит свой билет в профиле.

Отдельный sqlite-стор (как oidc_store/notify/circ). Связь создаётся ЯВНО:
сотрудник в кабинете вводит свой билет+пароль (доказывает владение билетом) →
линк (staff_login → ticket). ПДн тут не хранятся — только логин и номер билета.
"""
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS staff_reader_link (
  staff_login TEXT PRIMARY KEY,
  ticket TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS srl_ticket_idx ON staff_reader_link(ticket);
"""


class IdentityStore:
    def __init__(self, path=':memory:'):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def link(self, staff_login, ticket, now=None):
        """Связать учётку сотрудника с билетом. Идемпотентно (одна связь на логин,
        перепривязка заменяет билет)."""
        now = float(now if now is not None else time.time())
        with self._lock:
            self._conn.execute(
                "INSERT INTO staff_reader_link(staff_login, ticket, created_at) "
                "VALUES(?,?,?) ON CONFLICT(staff_login) "
                "DO UPDATE SET ticket=excluded.ticket, created_at=excluded.created_at",
                (staff_login, ticket, now))
            self._conn.commit()
        return {'staffLogin': staff_login, 'ticket': ticket}

    def reader_for_staff(self, staff_login):
        """Билет, привязанный к сотруднику, или None."""
        with self._lock:
            r = self._conn.execute(
                "SELECT ticket FROM staff_reader_link WHERE staff_login=?",
                (staff_login,)).fetchone()
        return r['ticket'] if r else None

    def staff_for_reader(self, ticket):
        """Логин сотрудника, привязанного к билету, или None (если этот читатель —
        тоже сотрудник)."""
        with self._lock:
            r = self._conn.execute(
                "SELECT staff_login FROM staff_reader_link WHERE ticket=?",
                (ticket,)).fetchone()
        return r['staff_login'] if r else None

    def unlink(self, staff_login):
        """Снять привязку. Возвращает число удалённых строк."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM staff_reader_link WHERE staff_login=?", (staff_login,))
            self._conn.commit()
            return cur.rowcount
