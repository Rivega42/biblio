#!/usr/bin/env python3
"""PAY — собственный финансовый леджер читателя (ребро INTEGRATION_MAP 3.3).

Аналог ИРБИС-БД **PAY** (проводки начислений/оплат, ключ ``RI=`` = билет
читателя), но own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без
сети и без новых pip-зависимостей — в точности как ``circulation.py``/``devices.py``.

Зачем отдельно от ``circulation.fine``
--------------------------------------
``fine`` — состояние штрафа НА ВЫДАЧЕ (loan-keyed: начислен/оплачен/прощён по
конкретному ``loan``). **PAY** — РЕЕСТР финансовых проводок ЧИТАТЕЛЯ (reader-keyed,
``RI=``): начисления (штраф за просрочку / возмещение утери) и платежи. Книговыдача
постит сюда проводки при начислении/оплате через опциональный ``pay=``-хендл
(``CirculationEngine``). Это и есть «утеря/штраф → PAY» из DB_CIRCULATION §5
(штрафы в БД PAY по ключу ``RI=``).
"""
import sqlite3
import threading
import time

# Виды проводок: начисления (charge) и платёж.
CHARGE_KINDS = ('fine_overdue', 'lost_replacement')
KIND_PAYMENT = 'payment'
ALL_KINDS = CHARGE_KINDS + (KIND_PAYMENT,)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS pay_entry (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  reader     TEXT NOT NULL,            -- RI= билет читателя
  kind       TEXT NOT NULL,            -- fine_overdue | lost_replacement | payment
  amount     REAL NOT NULL DEFAULT 0,
  currency   TEXT NOT NULL DEFAULT 'RUB',
  ref        TEXT,                     -- доменная ссылка (loan id и т.п.)
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS pay_entry_reader_idx ON pay_entry(reader, kind);
"""


class PayStore:
    """Собственный sqlite-стор PAY-проводок. ``:memory:`` или файл; create-on-init.
    Соединение thread-local (домашний стиль); строки — dict."""

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

    def add(self, reader, kind, amount, currency, ref, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO pay_entry(reader,kind,amount,currency,ref,created_at) '
            'VALUES(?,?,?,?,?,?)',
            (reader, kind, float(amount), currency,
             None if ref is None else str(ref), created_at))
        c.commit()
        return self.get(cur.lastrowid)

    def get(self, entry_id):
        r = self._conn().execute(
            'SELECT * FROM pay_entry WHERE id=?', (entry_id,)).fetchone()
        return dict(r) if r else None

    def entries(self, reader):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM pay_entry WHERE reader=? ORDER BY id',
            (reader,)).fetchall()]

    def sums(self, reader):
        """Суммы по видам проводок для читателя -> ``{kind: amount}``."""
        rows = self._conn().execute(
            'SELECT kind, COALESCE(SUM(amount),0) AS s FROM pay_entry '
            'WHERE reader=? GROUP BY kind', (reader,)).fetchall()
        return {r['kind']: float(r['s']) for r in rows}


class PayLedger:
    """Операции над :class:`PayStore` — проводки начислений/платежей + баланс.

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах.
    """

    def __init__(self, store=None, now=None):
        self.store = store or PayStore(':memory:')
        self._now = now or time.time

    def post_charge(self, reader, amount, kind, ref=None, currency='RUB'):
        """Проводка НАЧИСЛЕНИЯ (штраф за просрочку / возмещение утери).

        ``kind`` ∈ :data:`CHARGE_KINDS`. Возвращает строку проводки."""
        if kind not in CHARGE_KINDS:
            raise ValueError('unknown charge kind: %r' % (kind,))
        return self.store.add(reader, kind, amount, currency, ref, self._now())

    def post_payment(self, reader, amount, ref=None, currency='RUB'):
        """Проводка ПЛАТЕЖА читателя."""
        return self.store.add(reader, KIND_PAYMENT, amount, currency, ref,
                              self._now())

    def entries(self, reader):
        """Все проводки читателя (хронологически)."""
        return self.store.entries(reader)

    def balance(self, reader):
        """Текущий долг читателя = Σ начислений − Σ платежей (округл. до копеек)."""
        s = self.store.sums(reader)
        charges = sum(s.get(k, 0.0) for k in CHARGE_KINDS)
        payments = s.get(KIND_PAYMENT, 0.0)
        return round(charges - payments, 2)
