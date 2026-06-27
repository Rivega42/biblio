#!/usr/bin/env python3
"""Suppliers — собственный справочник поставщиков + реестр счетов-актов.

Контур **Комплектование**, недомоделированный участок: поставщики (организация-
посредник, IZD) и счета/акты сейчас покрыты лишь частично (поставщик «жил» строкой
``supplier`` на заказе ``acq_order`` и ссылкой акта ``act_ref`` на КСУ, без
самостоятельной сущности). Этот модуль выносит их в own-store справочник —
организация-поставщик как первоклассная запись и счёт-акт как отдельная строка со
статусом (draft|received|paid|cancelled), связью с поставщиком и мягкими ссылками
на заказ/КСУ (``order_ref`` / ``ksu_no``) контура ``acquisition.py``.

Зачем отдельный модуль (а не правка ``acquisition.py``)
------------------------------------------------------
``acquisition.py`` моделирует жизненный цикл заказ → поступление → КСУ → каталог;
поставщик там — атрибут заказа, а счёт — лишь текстовая ссылка ``act_ref`` на запись
КСУ (88^B/^J «акт/счёт»). Реестр контрагентов и финансовых документов — отдельная
ответственность (нормализованный справочник + статусы счёта), поэтому он живёт в
своём сторе и связывается с заказами/КСУ по ссылке, не редактируя контур поступлений.

Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), thread-local соединение, строки
как dict — в точности как ``pay.py`` / ``acquisition.py``. Без сети и без новых
pip-зависимостей. Фильтр по подстроке имени (``find``) делается в Python, а не через
SQLite ``LIKE``: ``LIKE`` в sqlite3 без ICU регистронезависим только для ASCII, для
кириллицы он бы не нашёл совпадение в другом регистре — поэтому матчинг casefold-ом
на стороне Python.
"""
import sqlite3
import threading
import time

# Статусы счёта-акта (жизненный цикл финансового документа поставщика).
INVOICE_DRAFT = 'draft'
INVOICE_RECEIVED = 'received'
INVOICE_PAID = 'paid'
INVOICE_CANCELLED = 'cancelled'
INVOICE_STATUSES = (INVOICE_DRAFT, INVOICE_RECEIVED, INVOICE_PAID, INVOICE_CANCELLED)


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS supplier (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,            -- наименование организации-поставщика (IZD)
  inn        TEXT,                     -- ИНН
  contact    TEXT,                     -- контактное лицо
  email      TEXT,
  phone      TEXT,
  address    TEXT,
  is_active  INTEGER NOT NULL DEFAULT 1,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS supplier_active_idx ON supplier(is_active);
CREATE TABLE IF NOT EXISTS invoice (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_id INTEGER NOT NULL REFERENCES supplier(id),
  number      TEXT,                    -- № счёта/акта (88^B / 88^J у КСУ)
  date        TEXT,                    -- дата документа (как строка, формат вызывающего)
  amount      REAL NOT NULL DEFAULT 0,
  currency    TEXT NOT NULL DEFAULT 'RUB',
  status      TEXT NOT NULL DEFAULT 'draft'
       CHECK (status IN ('draft','received','paid','cancelled')),
  ksu_no      TEXT,                    -- мягкая ссылка на КСУ поступления (88^A)
  order_ref   TEXT,                    -- мягкая ссылка на заказ acq_order.id
  created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS invoice_supplier_idx ON invoice(supplier_id, status);
"""


class SupplierStore:
    """Собственный sqlite-стор справочника поставщиков и счетов-актов.

    ``db_path=':memory:'`` (по умолчанию) или файл для тестов; create-on-init.
    Соединение thread-local (домашний стиль); строки возвращаются как dict.
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

    # ---- suppliers -------------------------------------------------------- #
    def add_supplier(self, name, inn, contact, email, phone, address,
                     created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO supplier(name,inn,contact,email,phone,address,'
            'is_active,created_at) VALUES(?,?,?,?,?,?,1,?)',
            (name, inn, contact, email, phone, address, created_at))
        c.commit()
        return self.get_supplier(cur.lastrowid)

    def get_supplier(self, supplier_id):
        r = self._conn().execute(
            'SELECT * FROM supplier WHERE id=?', (supplier_id,)).fetchone()
        return dict(r) if r else None

    def list_suppliers(self, active_only=False):
        if active_only:
            rows = self._conn().execute(
                'SELECT * FROM supplier WHERE is_active=1 ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM supplier ORDER BY id').fetchall()
        return [dict(r) for r in rows]

    def set_supplier_active(self, supplier_id, is_active):
        c = self._conn()
        c.execute('UPDATE supplier SET is_active=? WHERE id=?',
                  (1 if is_active else 0, supplier_id))
        c.commit()
        return self.get_supplier(supplier_id)

    # ---- invoices --------------------------------------------------------- #
    def add_invoice(self, supplier_id, number, date, amount, currency, status,
                    ksu_no, order_ref, created_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO invoice(supplier_id,number,date,amount,currency,status,'
            'ksu_no,order_ref,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (supplier_id, number, date, float(amount), currency, status,
             ksu_no, order_ref, created_at))
        c.commit()
        return self.get_invoice(cur.lastrowid)

    def get_invoice(self, invoice_id):
        r = self._conn().execute(
            'SELECT * FROM invoice WHERE id=?', (invoice_id,)).fetchone()
        return dict(r) if r else None

    def set_invoice_status(self, invoice_id, status):
        c = self._conn()
        c.execute('UPDATE invoice SET status=? WHERE id=?', (status, invoice_id))
        c.commit()
        return self.get_invoice(invoice_id)

    def list_invoices(self, supplier_id=None, status=None):
        sql = 'SELECT * FROM invoice'
        clauses, params = [], []
        if supplier_id is not None:
            clauses.append('supplier_id=?')
            params.append(supplier_id)
        if status is not None:
            clauses.append('status=?')
            params.append(status)
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def sums_by_status(self, supplier_id):
        """Суммы счетов поставщика по статусам -> ``{status: amount}``."""
        rows = self._conn().execute(
            'SELECT status, COALESCE(SUM(amount),0) AS s FROM invoice '
            'WHERE supplier_id=? GROUP BY status', (supplier_id,)).fetchall()
        return {r['status']: float(r['s']) for r in rows}

    def counts(self):
        """Грубые счётчики для :meth:`SupplierService.stats`."""
        c = self._conn()
        suppliers = c.execute('SELECT COUNT(*) AS n FROM supplier').fetchone()['n']
        active = c.execute(
            'SELECT COUNT(*) AS n FROM supplier WHERE is_active=1').fetchone()['n']
        invoices = c.execute('SELECT COUNT(*) AS n FROM invoice').fetchone()['n']
        by_status = {
            r['status']: r['n'] for r in c.execute(
                'SELECT status, COUNT(*) AS n FROM invoice '
                'GROUP BY status').fetchall()}
        total = c.execute(
            'SELECT COALESCE(SUM(amount),0) AS s FROM invoice').fetchone()['s']
        return {
            'suppliers': suppliers,
            'active_suppliers': active,
            'invoices': invoices,
            'invoices_by_status': by_status,
            'total_amount': float(total),
        }


class SupplierError(Exception):
    """Ошибка операции справочника поставщиков (неизвестный поставщик и т.п.)."""


def _matches(supplier, query):
    """Подстрочный матчинг запроса по полям поставщика (casefold, Python-side).

    SQLite ``LIKE`` без ICU регистронезависим только для ASCII, поэтому для
    кириллицы фильтруем здесь: ``query`` ищется как подстрока (без учёта регистра)
    в name/inn/contact/email поставщика."""
    q = (query or '').strip().casefold()
    if not q:
        return True
    for key in ('name', 'inn', 'contact', 'email'):
        val = supplier.get(key)
        if val and q in str(val).casefold():
            return True
    return False


class SupplierService:
    """Операции над :class:`SupplierStore` — справочник поставщиков + счета-акты.

    ``now`` инжектируется (``time.time`` по умолчанию) для детерминизма в тестах —
    как ``PayLedger`` / семя времени в ``acquisition``.
    """

    def __init__(self, store=None, now=None):
        self.store = store or SupplierStore(':memory:')
        self._now = now or time.time

    # ---- suppliers -------------------------------------------------------- #
    def add_supplier(self, name, inn=None, contact=None, email=None, phone=None,
                     address=None):
        """Завести поставщика (организацию-посредника). Возвращает строку-dict."""
        if not name or not str(name).strip():
            raise SupplierError('supplier requires a name')
        return self.store.add_supplier(
            str(name).strip(), inn, contact, email, phone, address, self._now())

    def get(self, supplier_id):
        """Поставщик по id, или ``None``."""
        return self.store.get_supplier(supplier_id)

    def list(self, active_only=False):
        """Все поставщики (или только активные при ``active_only=True``)."""
        return self.store.list_suppliers(active_only=active_only)

    def find(self, query):
        """Поиск поставщиков по подстроке (name/inn/contact/email, casefold).

        Фильтр в Python (SQLite ``LIKE`` — ASCII-only для регистра), кириллица
        ищется без учёта регистра."""
        return [s for s in self.store.list_suppliers() if _matches(s, query)]

    def deactivate(self, supplier_id):
        """Деактивировать поставщика (``is_active=0``). Возвращает обновлённую строку."""
        if self.store.get_supplier(supplier_id) is None:
            raise SupplierError('unknown supplier %r' % (supplier_id,))
        return self.store.set_supplier_active(supplier_id, False)

    def activate(self, supplier_id):
        """Снова сделать поставщика активным (``is_active=1``)."""
        if self.store.get_supplier(supplier_id) is None:
            raise SupplierError('unknown supplier %r' % (supplier_id,))
        return self.store.set_supplier_active(supplier_id, True)

    # ---- invoices --------------------------------------------------------- #
    def add_invoice(self, supplier_id, number, amount, date=None, ksu_no=None,
                    order_ref=None, currency='RUB', status=INVOICE_DRAFT):
        """Завести счёт-акт поставщика. Поставщик должен существовать.

        ``ksu_no`` / ``order_ref`` — мягкие ссылки на КСУ/заказ контура
        ``acquisition`` (хранятся как текст, без FK на чужой стор). Возвращает
        строку-dict нового счёта (статус по умолчанию ``draft``)."""
        if self.store.get_supplier(supplier_id) is None:
            raise SupplierError('unknown supplier %r' % (supplier_id,))
        if status not in INVOICE_STATUSES:
            raise SupplierError('unknown invoice status %r' % (status,))
        order_ref = None if order_ref is None else str(order_ref)
        ksu_no = None if ksu_no is None else str(ksu_no)
        return self.store.add_invoice(
            supplier_id, number, date, amount, currency, status, ksu_no,
            order_ref, self._now())

    def set_invoice_status(self, invoice_id, status):
        """Сменить статус счёта (draft|received|paid|cancelled)."""
        if status not in INVOICE_STATUSES:
            raise SupplierError('unknown invoice status %r' % (status,))
        if self.store.get_invoice(invoice_id) is None:
            raise SupplierError('unknown invoice %r' % (invoice_id,))
        return self.store.set_invoice_status(invoice_id, status)

    def invoices(self, supplier_id=None, status=None):
        """Счета с фильтром по поставщику и/или статусу (хронологически)."""
        return self.store.list_invoices(supplier_id=supplier_id, status=status)

    def total_by_supplier(self, supplier_id):
        """Σ сумм счетов поставщика по статусам -> ``{status: amount}``.

        Включает агрегаты ``total`` (по всем статусам) и ``payable`` (received —
        принят, но не оплачен) поверх раскладки по статусам, чтобы было видно и
        итог, и «к оплате»."""
        by_status = self.store.sums_by_status(supplier_id)
        total = round(sum(by_status.values()), 2)
        payable = round(by_status.get(INVOICE_RECEIVED, 0.0), 2)
        out = {s: round(by_status.get(s, 0.0), 2) for s in INVOICE_STATUSES}
        out['total'] = total
        out['payable'] = payable
        return out

    def stats(self):
        """Сводка справочника: число поставщиков/активных, счетов по статусам, Σ."""
        return self.store.counts()
