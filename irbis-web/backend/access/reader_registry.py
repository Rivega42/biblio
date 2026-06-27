#!/usr/bin/env python3
"""READER REGISTRY — собственный реестр читателей RDR (ребро INTEGRATION_MAP 3.1).

Аналог ИРБИС-БД **RDR** (база читателей, ключ ``RI=`` = номер билета), но
own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без
новых pip-зависимостей — в точности как ``pay.py``/``devices.py``.

Зачем
-----
В ``circulation.py`` читатель — это лишь строка ``reader(id, category, blocked)``
(минимум для расчёта лимитов и штрафов §5). Этого мало: читатель должен быть
полноценной **ЗАПИСЬЮ-ПРОФИЛЕМ** RDR (ФИО, категория, контакты, факультет,
статус), а не «строкой-id». ``reader_registry`` — это own-store такого профиля.

Маппинг на поля RDR
-------------------
  * ``id``        — поле ``RI=`` (номер билета, первичный ключ);
  * ``ticket``    — дубль билета (поле 30 ^A / штрих-код), обычно == ``id``;
  * ``category``  — поле 50 (категория читателя, напр. В01–В05 / Д01–Д03);
  * ``full_name`` — поля 10 (фамилия) / 11 (имя-отчество), здесь — собранное ФИО;
  * ``status``    — ``active`` / ``blocked`` (см. поле 30 ^S и блокировку);
  * ``email`` / ``phone`` / ``faculty`` — контактные/учебные реквизиты профиля.

Как circulation подключит реестр (duck-typed ``resolve``)
---------------------------------------------------------
``circulation.py`` НЕ редактируется этим ребром. Подключение — опциональным
хендлом ``reader_registry=`` у ``CirculationEngine`` (как ``pay=``/``catalog=``):

    from access.reader_registry import ReaderRegistry, ReaderStore
    reg = ReaderRegistry(ReaderStore(':memory:'))
    reg.register('RDR-1', category='В01', full_name='Иванов Иван')
    eng = CirculationEngine(store=..., policy=..., reader_registry=reg)

Контракт duck-typing — единственный метод, который вызывает circulation:

    profile = reader_registry.resolve(reader_id)   # полная запись-dict | None

То есть там, где раньше у движка был ``reader_id`` (строка), он сможет получить
полноценный профиль через ``resolve(...)``: вернётся dict-запись (билет, ФИО,
категория, статус, контакты) либо ``None``, если читатель не заведён в реестре.
Реестр best-effort: его методы не бросают наружу — недоступность реестра не
должна ронять книговыдачу (как ``pay``-хендл в ребре 3.3).
"""
import sqlite3
import threading
import time

# Статусы профиля читателя (поле 30 ^S / блокировка).
STATUS_ACTIVE = 'active'
STATUS_BLOCKED = 'blocked'
STATUSES = (STATUS_ACTIVE, STATUS_BLOCKED)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS reader_profile (
  id         TEXT PRIMARY KEY,         -- RI= номер билета
  ticket     TEXT,                     -- 30^A / штрих-код (обычно == id)
  category   TEXT,                     -- 50 категория читателя
  full_name  TEXT,                     -- 10 фамилия + 11 имя-отчество (ФИО)
  status     TEXT NOT NULL DEFAULT 'active',  -- active | blocked
  email      TEXT,
  phone      TEXT,
  faculty    TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reader_profile_ticket_idx ON reader_profile(ticket);
CREATE INDEX IF NOT EXISTS reader_profile_cat_idx ON reader_profile(category);
"""


class ReaderStore:
    """Собственный sqlite-стор профилей читателей RDR. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict."""

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

    def upsert(self, reader_id, ticket=None, category=None, full_name=None,
               status=STATUS_ACTIVE, email=None, phone=None, faculty=None,
               created_at=None, updated_at=None):
        """Идемпотентно завести/обновить профиль по ``id`` (``RI=``).

        Повторный ``upsert`` того же id обновляет поля и ``updated_at``, но
        сохраняет исходный ``created_at`` (одна запись, не дубль)."""
        now = time.time() if updated_at is None else updated_at
        existing = self.get(reader_id)
        c = self._conn()
        if existing is None:
            created = now if created_at is None else created_at
            c.execute(
                'INSERT INTO reader_profile(id,ticket,category,full_name,status,'
                'email,phone,faculty,created_at,updated_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?)',
                (reader_id, ticket if ticket is not None else reader_id,
                 category, full_name, status, email, phone, faculty, created,
                 now))
        else:
            c.execute(
                'UPDATE reader_profile SET ticket=?,category=?,full_name=?,'
                'status=?,email=?,phone=?,faculty=?,updated_at=? WHERE id=?',
                (ticket if ticket is not None else existing['ticket'],
                 category if category is not None else existing['category'],
                 full_name if full_name is not None else existing['full_name'],
                 status if status is not None else existing['status'],
                 email if email is not None else existing['email'],
                 phone if phone is not None else existing['phone'],
                 faculty if faculty is not None else existing['faculty'],
                 now, reader_id))
        c.commit()
        return self.get(reader_id)

    def get(self, reader_id):
        r = self._conn().execute(
            'SELECT * FROM reader_profile WHERE id=?', (reader_id,)).fetchone()
        return dict(r) if r else None

    def find_by_ticket(self, ticket):
        r = self._conn().execute(
            'SELECT * FROM reader_profile WHERE ticket=? ORDER BY id LIMIT 1',
            (ticket,)).fetchone()
        return dict(r) if r else None

    def set_status(self, reader_id, status, updated_at=None):
        now = time.time() if updated_at is None else updated_at
        c = self._conn()
        c.execute('UPDATE reader_profile SET status=?,updated_at=? WHERE id=?',
                  (status, now, reader_id))
        c.commit()
        return self.get(reader_id)

    def list(self, category=None):
        if category is None:
            rows = self._conn().execute(
                'SELECT * FROM reader_profile ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM reader_profile WHERE category=? ORDER BY id',
                (category,)).fetchall()
        return [dict(r) for r in rows]


class ReaderRegistry:
    """Операции над :class:`ReaderStore` — реестр читателей RDR.

    Реализует duck-typed контракт ``resolve(reader_id)`` для опционального
    хендла ``reader_registry=`` в ``CirculationEngine`` (см. докстринг модуля).
    Best-effort: методы не бросают наружу (недоступность реестра не должна
    ронять книговыдачу). ``now`` инжектируется для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or ReaderStore(':memory:')
        self._now = now or time.time

    def register(self, reader_id, ticket=None, category=None, full_name=None,
                 status=STATUS_ACTIVE, email=None, phone=None, faculty=None):
        """Завести/обновить профиль читателя (идемпотентно по ``id``)."""
        try:
            return self.store.upsert(
                reader_id, ticket=ticket, category=category,
                full_name=full_name, status=status, email=email, phone=phone,
                faculty=faculty, updated_at=self._now())
        except Exception:
            return None

    def get(self, reader_id):
        """Профиль по id (``RI=``) или ``None``."""
        try:
            return self.store.get(reader_id)
        except Exception:
            return None

    def resolve(self, reader_id):
        """Полная запись-профиль читателя по id или ``None`` (контракт для
        circulation: ``reader_registry.resolve(reader_id)``)."""
        try:
            prof = self.store.get(reader_id)
            if prof is None:
                prof = self.store.find_by_ticket(reader_id)
            return prof
        except Exception:
            return None

    def block(self, reader_id):
        """Заблокировать читателя (status -> ``blocked``)."""
        try:
            return self.store.set_status(reader_id, STATUS_BLOCKED,
                                         updated_at=self._now())
        except Exception:
            return None

    def unblock(self, reader_id):
        """Снять блокировку (status -> ``active``)."""
        try:
            return self.store.set_status(reader_id, STATUS_ACTIVE,
                                         updated_at=self._now())
        except Exception:
            return None

    def list(self, category=None):
        """Все профили (или по категории)."""
        try:
            return self.store.list(category=category)
        except Exception:
            return []

    def field30(self, reader_id):
        """Структура поля 30 RDR для читателя -> dict подполей или ``None``.

        Подполя (best-effort, без падений):
          * ``A`` — номер билета (``ticket`` / ``id``);
          * ``B`` — категория (поле 50);
          * ``C`` — ФИО (поля 10/11);
          * ``S`` — статус (``active`` / ``blocked``).
        """
        prof = self.resolve(reader_id)
        if prof is None:
            return None
        return {
            'A': prof.get('ticket') or prof.get('id'),
            'B': prof.get('category'),
            'C': prof.get('full_name'),
            'S': prof.get('status'),
        }
