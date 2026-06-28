#!/usr/bin/env python3
"""IP_AUTH — РЕЕСТР IP-диапазонов организаций и автоматический ВХОД ПО IP.

Провайдер авторизации «по IP-диапазону сети организации» — продвигает эпик
#240 (плагины авторизации рядом с ЕСИА/Сбер/Яндекс), но own-store: чистый
stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей — в точности как ``debtors.py``/``pay.py``/``circulation.py``.
Разбор IP/CIDR — ТОЛЬКО stdlib-модулем :mod:`ipaddress` (без сторонних либ).

Назначение
----------
Организация (вуз, библиотека, НИИ) задаёт CIDR-диапазоны своей сети
(например ``10.0.0.0/8``, ``2001:db8::/32``). Когда читатель приходит с IP из
такого диапазона, он автоматически опознаётся как принадлежащий организации —
БЕЗ ввода логина/пароля. Это типичная схема «доступ по IP сети вуза» в ЭБС и
подписных ресурсах.

Границы ответственности
-----------------------
Этот слой — самостоятельный РЕЕСТР диапазонов + РЕЗОЛВ ``ip -> организация``:
он только хранит диапазоны и отвечает, какой организации принадлежит IP.
Реальную выдачу читательской сессии по результату резолва подключит РОДИТЕЛЬ
отдельно (как ``pay=``/``reader_registry=`` у движков), опросив здесь
``IpAuthService.resolve(ip)``. Этот слой не трогает общие файлы.

Семантика резолва
-----------------
  * матчится только ВКЛЮЧЁННЫЙ (``enabled``) диапазон, которому принадлежит IP;
  * при пересечении нескольких диапазонов выбирается НАИБОЛЕЕ СПЕЦИФИЧНЫЙ —
    с наибольшей длиной префикса (``prefixlen``), т.е. самая узкая сеть;
  * семейства адресов изолированы: IPv4-адрес никогда не матчит IPv6-сеть и
    наоборот (``ipaddress`` сам бросает ``TypeError`` — оборачиваем как не-матч);
  * некорректный IP-литерал не валит резолв — возвращается ``None``.

CIDR при добавлении нормализуется через ``ipaddress.ip_network(cidr,
strict=False)`` и хранится в каноническом текстовом виде (``str(net)``), так
что хост-биты «схлопываются» к адресу сети (``10.1.2.5/24`` -> ``10.1.2.0/24``).
"""
import ipaddress
import sqlite3
import threading
from datetime import datetime, timezone


def _utcnow():
    """Текущий момент в ISO8601 (UTC, без микросекунд) — дефолтный ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS ip_range (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  cidr       TEXT NOT NULL,            -- нормализованная сеть (str(ip_network))
  org        TEXT NOT NULL,            -- организация-владелец диапазона
  role       TEXT NOT NULL DEFAULT '', -- роль/категория, выдаваемая по IP
  label      TEXT NOT NULL DEFAULT '', -- человекочитаемая метка диапазона
  enabled    INTEGER NOT NULL DEFAULT 1,-- 1 включён / 0 выключен
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ip_range_enabled_idx ON ip_range(enabled);
"""


class IpRangeStore:
    """Собственный sqlite-стор IP-диапазонов организаций. ``:memory:`` или
    файл; create-on-init. Соединение thread-local (домашний стиль); строки — dict."""

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

    def add(self, cidr, org, role='', label='', enabled=True):
        """Завести запись диапазона; возвращает строку-dict.

        ``cidr`` ожидается уже нормализованным (нормализацию/валидацию делает
        :meth:`IpAuthService.add_range`); стор хранит как есть."""
        c = self._conn()
        cur = c.execute(
            'INSERT INTO ip_range(cidr,org,role,label,enabled,created_at) '
            'VALUES(?,?,?,?,?,?)',
            (cidr, org, role, label, 1 if enabled else 0, self._now()))
        c.commit()
        return self.get(cur.lastrowid)

    def get(self, range_id):
        r = self._conn().execute(
            'SELECT * FROM ip_range WHERE id=?', (range_id,)).fetchone()
        return dict(r) if r else None

    def list(self, enabled_only=False):
        """Список диапазонов (все / только включённые), по ``id``."""
        sql = 'SELECT * FROM ip_range'
        if enabled_only:
            sql += ' WHERE enabled=1'
        sql += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(sql).fetchall()]

    def remove(self, range_id):
        """Удалить диапазон; ``True`` если запись была и удалена."""
        c = self._conn()
        cur = c.execute('DELETE FROM ip_range WHERE id=?', (range_id,))
        c.commit()
        return cur.rowcount > 0

    def set_enabled(self, range_id, enabled):
        """Включить/выключить диапазон; вернуть обновлённую строку-dict|None."""
        c = self._conn()
        c.execute('UPDATE ip_range SET enabled=? WHERE id=?',
                  (1 if enabled else 0, range_id))
        c.commit()
        return self.get(range_id)


class IpAuthService:
    """Прикладной слой авто-входа по IP над :class:`IpRangeStore` —
    валидация/нормализация CIDR, резолв ``ip -> организация`` с выбором самого
    специфичного диапазона.

    ``store`` и ``now`` инжектируются (``:memory:`` и :func:`_utcnow` по
    умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or IpRangeStore(':memory:', now=now)
        self._now = now or _utcnow

    def add_range(self, cidr, org, role='', label=''):
        """Зарегистрировать CIDR-диапазон организации; вернуть строку-dict.

        Валидация:
          * ``cidr`` разбирается ``ipaddress.ip_network(cidr, strict=False)`` —
            некорректный CIDR/хост-биты вне ``strict`` -> ``ValueError``;
          * пустой ``org`` -> ``ValueError``.

        Хранится нормализованный текст сети ``str(ip_network(...))`` (хост-биты
        схлопнуты к адресу сети)."""
        if not org:
            raise ValueError('пустой org недопустим')
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except (ValueError, TypeError) as exc:
            raise ValueError('некорректный CIDR: %r (%s)' % (cidr, exc))
        return self.store.add(str(net), org, role=role, label=label,
                              enabled=True)

    def resolve(self, ip):
        """Найти ВКЛЮЧЁННЫЙ диапазон, которому принадлежит ``ip`` -> dict|None.

        При пересечении нескольких диапазонов возвращается самый СПЕЦИФИЧНЫЙ
        (с наибольшей ``prefixlen``). Некорректный IP-литерал -> ``None``.
        Разные семейства (IPv4 vs IPv6) никогда не матчатся."""
        try:
            addr = ipaddress.ip_address(ip)
        except (ValueError, TypeError):
            return None
        best = None
        best_prefix = -1
        for row in self.store.list(enabled_only=True):
            try:
                net = ipaddress.ip_network(row['cidr'], strict=False)
            except (ValueError, TypeError):
                continue
            try:
                inside = addr in net
            except TypeError:
                # ip и сеть разных семейств — считаем не-матч.
                continue
            if inside and net.prefixlen > best_prefix:
                best = row
                best_prefix = net.prefixlen
        return best

    def list(self, enabled_only=False):
        """Список диапазонов (делегирует стору)."""
        return self.store.list(enabled_only=enabled_only)

    def remove(self, range_id):
        """Удалить диапазон по id -> ``bool`` (делегирует стору)."""
        return self.store.remove(range_id)

    def set_enabled(self, range_id, enabled):
        """Включить/выключить диапазон -> dict|None (делегирует стору)."""
        return self.store.set_enabled(range_id, enabled)
