#!/usr/bin/env python3
"""Хранилище привязок внешней OIDC-личности к читательскому билету (узел 3 MVP-2b).

Отдельный sqlite-стор (как notify/catalog/circ): связь ``(provider, subject)`` ↔
``ticket``. Читатели не живут в access-сторе (они в ИРБИС RDR), а сама ПРИВЯЗКА —
наша доменная сущность. Привязка создаётся ЯВНО (читатель входит билет+пароль и
подтверждает «привязать Госуслуги/Яндекс»); вход через провайдера ищет билет по
``(provider, subject)``. Никаких ПДн тут не хранится — только внешний идентификатор
(email/СНИЛС-хэш-подобный subject) и номер билета.
"""
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS oidc_identity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  subject TEXT NOT NULL,
  ticket TEXT NOT NULL,
  created_at REAL NOT NULL,
  UNIQUE(provider, subject)
);
CREATE INDEX IF NOT EXISTS oidc_ticket_idx ON oidc_identity(ticket);
"""


class OidcStore:
    def __init__(self, path=':memory:'):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def link(self, provider, subject, ticket, now=None):
        """Привязать (provider, subject) к билету. Идемпотентно: повторная привязка
        той же внешней личности ПЕРЕНАПРАВЛЯЕТ на новый билет (re-bind)."""
        now = float(now if now is not None else time.time())
        with self._lock:
            self._conn.execute(
                "INSERT INTO oidc_identity(provider, subject, ticket, created_at) "
                "VALUES(?,?,?,?) ON CONFLICT(provider, subject) "
                "DO UPDATE SET ticket=excluded.ticket, created_at=excluded.created_at",
                (provider, subject, ticket, now))
            self._conn.commit()
        return {'provider': provider, 'subject': subject, 'ticket': ticket}

    def ticket_for(self, provider, subject):
        """Билет по внешней личности, или None (тогда вход → шаг привязки)."""
        with self._lock:
            r = self._conn.execute(
                "SELECT ticket FROM oidc_identity WHERE provider=? AND subject=?",
                (provider, subject)).fetchone()
        return r['ticket'] if r else None

    def list_for_ticket(self, ticket):
        """Привязанные к билету внешние личности (для кабинета: что привязано)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT provider, subject, created_at FROM oidc_identity "
                "WHERE ticket=? ORDER BY provider", (ticket,)).fetchall()
        return [{'provider': x['provider'], 'subject': x['subject'],
                 'createdAt': x['created_at']} for x in rows]

    def unlink(self, provider, ticket):
        """Отвязать провайдера от билета. Возвращает число удалённых строк."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM oidc_identity WHERE provider=? AND ticket=?",
                (provider, ticket))
            self._conn.commit()
            return cur.rowcount
