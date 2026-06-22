#!/usr/bin/env python3
"""Acquisition (комплектование) engine — order → receipt → КСУ → ToCat → каталог.

Gap E1, epic #188. Closes the biggest unwired ❌ cluster in INTEGRATION_MAP
(cluster 1 «Комплектование → Каталог», the **ToCat** edges 1.1/1.2 + field 66/938
КСУ link), implementing SPEC_business_acquisition.md (the ККО/acquisition formulas
and the КСУ summary-accounting entry).

What this module is
-------------------
A *self-contained* acquisition lifecycle over its own sqlite store — the domain
state the desktop ИРБИС «Мастера» (заказ / поступление / КСУ-распределение) held
in external `.gbl`/`.pft` code, here made explicit and testable. Pure stdlib +
``sqlite3`` (dev parity, ADR-004) — no network I/O, no new pip deps.

The lifecycle (mirrors the АРМ «Комплектатор» tabs, ACQUISITION_FUNCTIONS.md):

  1. **Order (заказ)** — :meth:`AcquisitionEngine.create_order` opens an order line
     (title/author, supplier, copies ordered, unit price, funding source). Status
     walks ``ordered → partially_received → received`` (or ``cancelled``) as copies
     arrive (DB_ACQUISITION поле 62 «суммарный заказ», статус ``StatusZ.mnu``).
  2. **Receipt (поступление)** — :meth:`receive` registers received copies against
     an order and writes a **КСУ** (Книга суммарного учёта) entry: inventory
     numbers, the batch sum, and the act/invoice ref (DB_ACQUISITION КСУ 88: 88^E
     наименований / 88^F экземпляров / 88^G сумма). КСУ rows are the summary book
     of accounting per batch.
  3. **ToCat (передача в каталог)** — the cluster-1 edge. When an optional
     ``catalog`` handle (an :class:`access.catalog.CatalogStore`) is wired,
     :meth:`receive` also creates **or updates** the catalog record via
     ``catalog.save`` and registers the received copies as ``910`` exemplars
     (inventory ``^b``, availability ``^A`` = free, КСУ link ``^U``), plus a КСУ
     back-link on the bib record (field **66/938**, the ``66^u`` КСУ marker the
     SPEC names as the ToCat trigger). New-vs-existing title is resolved by a
     normalized (title, author) key so re-supply of an existing title **adds
     copies to the existing record** instead of duplicating it.
  4. **Standalone** — with NO ``catalog`` handle, order / receipt / КСУ still work
     fully; ToCat is a graceful no-op (back-compat, mirrors the ``catalog=`` seam
     in circulation.py).

ККО (book-provision ratio, SPEC §2)
-----------------------------------
:func:`kko` implements the ККО = ЭКЗЕМПЛЯРЫ / СТУДЕНТЫ formula with the SPEC §2.2
**division-by-zero policy** (the 4-cell table): students==0 ∧ copies>0 → ``1.0``
(provided, no demand); students==0 ∧ copies==0 → ``None`` (no data — excluded
from averages, NOT 0); students>0 → ``copies/students``. :func:`average_kko`
excludes the ``None`` (no-data) cells so archival orphan contingents don't drag
the mean to 0. :func:`reorder_need` is the §2.6 deficit→дозаказ amount.

Record / exemplar contract (ToCat)
----------------------------------
The catalog record this engine writes/extends (the engines' I1 field/subfield
dict, ``{field: [{subfield: value}]}``)::

    {
      "200": [{"a": <title>, "f": <author/responsibility>}],   # заглавие
      "700": [{"a": <author>}],                                 # 1st author
      "920": "PAZK",                                            # worklist (FLK-required)
      "101": "rus",                                             # language
      "66":  [{"u": <ksu_no>}],                                 # ToCat / КСУ back-link
      "910": [                                                  # exemplars (one per copy)
         {"a": "0", "b": <inv_no>, "u": <ksu_no>},              # ^A free · ^b inv# · ^U КСУ
         ...
      ],
    }

``910^A`` uses the catalog's free code (``catalog.EXEMPLAR_FREE`` == ``'0'``) so a
received copy is immediately lendable; circulation flips it 0→1 on checkout.
"""
import math
import sqlite3
import threading
import time

# Optional Catalog seam (INTEGRATION_MAP cluster 1, the ToCat edge). When a
# CatalogStore handle is wired, receipt reflects the batch into the catalog (bib
# record + 910 exemplars). Never a hard dependency — the import is best-effort so
# the module runs standalone (no catalog) exactly like circulation.py's seam.
try:  # pragma: no cover - depends on sibling module / wiring
    from access import catalog as _catalog  # type: ignore
except Exception:  # ImportError when run in isolation
    _catalog = None


# --------------------------------------------------------------------------- #
# Constants — order/КСУ status vocabularies + the catalog free-exemplar code.
# --------------------------------------------------------------------------- #
# Order status walk (DB_ACQUISITION поле 62 ^W, StatusZ.mnu — reconstructed to the
# lifecycle the SPEC's demand-driven loop needs).
ORDER_ORDERED = 'ordered'
ORDER_PARTIAL = 'partially_received'
ORDER_RECEIVED = 'received'
ORDER_CANCELLED = 'cancelled'
ORDER_STATUSES = (ORDER_ORDERED, ORDER_PARTIAL, ORDER_RECEIVED, ORDER_CANCELLED)

# The catalog availability flag a freshly-received copy carries (910^A free). Fall
# back to '0' (the documented ste.mnu «свободен» code) when the catalog module is
# not importable, so ToCat still produces the right flag in a degraded import.
EXEMPLAR_FREE = getattr(_catalog, 'EXEMPLAR_FREE', '0')

# Default base (БД) whose ЭК this engine reflects ToCat into (the live electronic
# catalogue is IBIS — same default as circulation.CirculationEngine.catalog_db).
CATALOG_DB = 'IBIS'

# Default worklist code stamped on a ToCat-created bib record (920). PAZK
# («книга») is the catalog's default book worklist; field 920 is FLK-mandatory
# (severity-1) so a ToCat record without it would be rejected by catalog.save.
DEFAULT_WORKLIST = 'PAZK'


# --------------------------------------------------------------------------- #
# ККО formulas (SPEC §2). Pure functions — no store, fully unit-testable.
# --------------------------------------------------------------------------- #
def kko(copies, students):
    """ККО = copies / students with the SPEC §2.2 division-by-zero policy.

    The 4-cell table (§2.2):

      ===============  ===========  =======================================
      copies/students  result       meaning
      ===============  ===========  =======================================
      students==0,>0   ``1.0``      provided (no consumers) — no дозаказ
      students==0,==0  ``None``     no data — excluded from averages (NOT 0)
      students>0,==0   ``0.0``      not provided — дозаказ candidate
      students>0,>0    copies/stud  norm
      ===============  ===========  =======================================

    ``None`` (no-data) is deliberately distinct from ``0.0`` (not-provided) so the
    average ККО isn't dragged down by archival orphan contingents (SPEC R2/AC4).
    """
    copies = float(copies or 0)
    students = float(students or 0)
    if students == 0:
        return 1.0 if copies > 0 else None   # provided vs no-data (NOT 0)
    return copies / students


def average_kko(kko_values, normalize=False):
    """Average ККО over per-title values, EXCLUDING ``None`` (no-data) cells (§2.4).

    ``None`` items are dropped from both the sum and the count N. With
    ``normalize=True`` each term is capped at 1 (``min(kko_i, 1)``) so one
    over-provided book can't compensate another's deficit (SPEC §2.4). Returns
    ``None`` when every value is no-data (N==0) — there is nothing to average.
    """
    present = [v for v in kko_values if v is not None]
    if not present:
        return None
    if normalize:
        present = [min(v, 1.0) for v in present]
    return sum(present) / len(present)


def reorder_need(students, copies, kko_norm=0.5):
    """Deficit дозаказ amount (SPEC §2.6 / §3.3): ``ceil(students*kko_norm) - copies``.

    The number of copies to buy to reach the provision norm. Clamped at 0 (never
    negative — an over-provided title needs no reorder). A title with no students
    (students<=0) is never a reorder candidate (returns 0): the §2.2 policy treats
    it as provided / no-data, not as a deficit.
    """
    if students <= 0:
        return 0
    need = math.ceil(students * kko_norm) - int(copies)
    return max(0, need)


# --------------------------------------------------------------------------- #
# Store — own sqlite (order / receipt / ksu / inventory). create-on-init.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS acq_order (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT,
  supplier TEXT,                       -- организация-посредник (IZD)
  copies_ordered INTEGER NOT NULL DEFAULT 0,
  copies_received INTEGER NOT NULL DEFAULT 0,
  price REAL,                          -- unit price (62^p plan)
  funding_source TEXT,                 -- источник финанс. (88^L Istfin.mnu)
  status TEXT NOT NULL DEFAULT 'ordered'
       CHECK (status IN ('ordered','partially_received','received','cancelled')),
  created REAL NOT NULL,
  updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS acq_order_status_idx ON acq_order(status);
CREATE TABLE IF NOT EXISTS acq_ksu (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ksu_no TEXT NOT NULL UNIQUE,         -- 88^A год+№ (the KSU= key)
  titles INTEGER NOT NULL DEFAULT 0,   -- 88^E наименований
  copies INTEGER NOT NULL DEFAULT 0,   -- 88^F экземпляров
  total_sum REAL NOT NULL DEFAULT 0,   -- 88^G сумма
  act_ref TEXT,                        -- акт/счёт (88^B / 88^J invoice)
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS acq_receipt (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL REFERENCES acq_order(id),
  ksu_id INTEGER NOT NULL REFERENCES acq_ksu(id),
  copies INTEGER NOT NULL,
  unit_price REAL,
  sum REAL NOT NULL DEFAULT 0,
  catalog_mfn INTEGER,                 -- the ToCat bib record (NULL if standalone)
  created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS acq_receipt_order_idx ON acq_receipt(order_id);
CREATE TABLE IF NOT EXISTS acq_inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  receipt_id INTEGER NOT NULL REFERENCES acq_receipt(id),
  ksu_no TEXT NOT NULL,                -- 910^U back-link to КСУ
  inv_no TEXT NOT NULL,               -- 910^b inventory number
  UNIQUE(inv_no)
);
CREATE INDEX IF NOT EXISTS acq_inventory_receipt_idx ON acq_inventory(receipt_id);
-- КСУ выбытия (книга суммарного учёта — часть «исключение»). Списание ставит
-- №КСУ выбытия (910^V), кол-во (910^X) и статус «списан» 910^A=6 на экземпляр
-- (INTEGRATION_MAP ребро 5.2 / кластер 1.5). Каждая строка — один выбывший экз.
-- с причиной (reason: lost/worn/…) и обратной ссылкой на КСУ поступления, если
-- инв.№ известен в acq_inventory (cross-link «партия поступления ↔ выбытие»).
CREATE TABLE IF NOT EXISTS acq_disposal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  inv_no TEXT NOT NULL,                -- 910^b выбывшего экземпляра
  ksu_disp_no TEXT NOT NULL,           -- 910^V № КСУ выбытия (акт списания)
  reason TEXT NOT NULL DEFAULT 'lost', -- причина (lost/worn/transfer/…)
  ksu_recv_no TEXT,                    -- КСУ поступления (если инв.№ известен)
  amount REAL NOT NULL DEFAULT 1,      -- 910^X кол-во (1 экз. на строку)
  ref TEXT,                            -- внешняя ссылка (loan_id / акт)
  created REAL NOT NULL,
  UNIQUE(inv_no, ksu_disp_no)          -- идемпотентность: один экз. на акт один раз
);
CREATE INDEX IF NOT EXISTS acq_disposal_ksu_idx ON acq_disposal(ksu_disp_no);
"""


class AcquisitionStore:
    """Own sqlite store for acquisition state (order / receipt / КСУ / inventory).

    ``db_path=':memory:'`` (default) or a temp file for tests; create-on-init.
    Connection is thread-local (house style); rows are returned as plain dicts.
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

    # ---- orders ----------------------------------------------------------- #
    def add_order(self, title, author, supplier, copies_ordered, price,
                  funding_source):
        now = time.time()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO acq_order(title,author,supplier,copies_ordered,'
            'price,funding_source,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?)',
            (title, author, supplier, copies_ordered, price, funding_source,
             ORDER_ORDERED, now, now))
        c.commit()
        return self.get_order(cur.lastrowid)

    def get_order(self, order_id):
        r = self._conn().execute(
            'SELECT * FROM acq_order WHERE id=?', (order_id,)).fetchone()
        return dict(r) if r else None

    def update_order(self, order_id, copies_received, status):
        c = self._conn()
        c.execute('UPDATE acq_order SET copies_received=?, status=?, updated=? '
                  'WHERE id=?', (copies_received, status, time.time(), order_id))
        c.commit()
        return self.get_order(order_id)

    def list_orders(self, status=None):
        if status is None:
            rows = self._conn().execute(
                'SELECT * FROM acq_order ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM acq_order WHERE status=? ORDER BY id',
                (status,)).fetchall()
        return [dict(r) for r in rows]

    # ---- КСУ -------------------------------------------------------------- #
    def get_ksu(self, ksu_no):
        r = self._conn().execute(
            'SELECT * FROM acq_ksu WHERE ksu_no=?', (ksu_no,)).fetchone()
        return dict(r) if r else None

    def upsert_ksu(self, ksu_no, add_titles, add_copies, add_sum, act_ref=None):
        """Insert a КСУ row, or accumulate a further receipt into an existing one.

        КСУ is the *summary* book of accounting: a batch number (88^A) aggregates
        наименований (88^E) / экземпляров (88^F) / сумма (88^G). Re-receiving
        against the same КСУ number accumulates the totals (idempotent on the
        number, additive on the totals)."""
        c = self._conn()
        existing = self.get_ksu(ksu_no)
        if existing is None:
            c.execute(
                'INSERT INTO acq_ksu(ksu_no,titles,copies,total_sum,act_ref,'
                'created) VALUES(?,?,?,?,?,?)',
                (ksu_no, add_titles, add_copies, add_sum, act_ref, time.time()))
        else:
            c.execute(
                'UPDATE acq_ksu SET titles=titles+?, copies=copies+?, '
                'total_sum=total_sum+?, act_ref=COALESCE(?,act_ref) WHERE ksu_no=?',
                (add_titles, add_copies, add_sum, act_ref, ksu_no))
        c.commit()
        return self.get_ksu(ksu_no)

    # ---- receipts + inventory --------------------------------------------- #
    def add_receipt(self, order_id, ksu_id, copies, unit_price, sum_,
                    catalog_mfn=None):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO acq_receipt(order_id,ksu_id,copies,unit_price,sum,'
            'catalog_mfn,created) VALUES(?,?,?,?,?,?,?)',
            (order_id, ksu_id, copies, unit_price, sum_, catalog_mfn, time.time()))
        c.commit()
        return self.get_receipt(cur.lastrowid)

    def get_receipt(self, receipt_id):
        r = self._conn().execute(
            'SELECT * FROM acq_receipt WHERE id=?', (receipt_id,)).fetchone()
        return dict(r) if r else None

    def set_receipt_catalog_mfn(self, receipt_id, catalog_mfn):
        c = self._conn()
        c.execute('UPDATE acq_receipt SET catalog_mfn=? WHERE id=?',
                  (catalog_mfn, receipt_id))
        c.commit()

    def add_inventory(self, receipt_id, ksu_no, inv_no):
        c = self._conn()
        c.execute('INSERT INTO acq_inventory(receipt_id,ksu_no,inv_no) '
                  'VALUES(?,?,?)', (receipt_id, ksu_no, inv_no))
        c.commit()

    def inventory_for_ksu(self, ksu_no):
        return [r['inv_no'] for r in self._conn().execute(
            'SELECT inv_no FROM acq_inventory WHERE ksu_no=? ORDER BY id',
            (ksu_no,)).fetchall()]

    def inventory_exists(self, inv_no):
        return self._conn().execute(
            'SELECT 1 FROM acq_inventory WHERE inv_no=?',
            (inv_no,)).fetchone() is not None

    def receipt_ksu_for_inv(self, inv_no):
        """КСУ поступления (910^U) of the inventory number, or None if unknown.

        The cross-link a disposal uses to tie an выбытие back to the партия
        поступления (acq_inventory.ksu_no)."""
        r = self._conn().execute(
            'SELECT ksu_no FROM acq_inventory WHERE inv_no=?',
            (inv_no,)).fetchone()
        return r['ksu_no'] if r else None

    # ---- disposals (КСУ выбытия / списание) ------------------------------- #
    def add_disposal(self, inv_no, ksu_disp_no, reason='lost',
                     ksu_recv_no=None, amount=1, ref=None):
        """Record one выбывший экземпляр in the КСУ выбытия (idempotent per
        ``(inv_no, ksu_disp_no)``). Returns the disposal row dict, or the existing
        one if this exact (экз., акт) pair was already written."""
        c = self._conn()
        existing = c.execute(
            'SELECT * FROM acq_disposal WHERE inv_no=? AND ksu_disp_no=?',
            (inv_no, ksu_disp_no)).fetchone()
        if existing is not None:
            return dict(existing)
        cur = c.execute(
            'INSERT INTO acq_disposal(inv_no,ksu_disp_no,reason,ksu_recv_no,'
            'amount,ref,created) VALUES(?,?,?,?,?,?,?)',
            (inv_no, ksu_disp_no, reason, ksu_recv_no, amount, ref, time.time()))
        c.commit()
        r = c.execute('SELECT * FROM acq_disposal WHERE id=?',
                      (cur.lastrowid,)).fetchone()
        return dict(r)

    def disposal_for_inv(self, inv_no):
        """All КСУ-выбытия rows for an inventory number (creation order)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM acq_disposal WHERE inv_no=? ORDER BY id',
            (inv_no,)).fetchall()]

    def disposal_summary(self, ksu_disp_no):
        """Aggregate of one акт списания: copies + total amount (88^F/^X rollup)."""
        r = self._conn().execute(
            'SELECT COUNT(*) AS copies, COALESCE(SUM(amount),0) AS amount '
            'FROM acq_disposal WHERE ksu_disp_no=?', (ksu_disp_no,)).fetchone()
        return {'ksu_disp_no': ksu_disp_no, 'copies': r['copies'],
                'amount': float(r['amount'])}


# --------------------------------------------------------------------------- #
# Title key — the new-vs-existing resolver (ToCat dedup).
# --------------------------------------------------------------------------- #
def title_key(title, author=None):
    """Normalized (title, author) key for new-vs-existing-title resolution.

    Re-supply of an existing title must ADD copies to that record, not create a
    duplicate. We match on a casefolded/trimmed (title, author) pair — the same
    pragmatic key the desktop dedup (`!KDEX/!KDK.pft`) uses on заглавие+автор."""
    t = (title or '').strip().casefold()
    a = (author or '').strip().casefold()
    return (t, a)


class AcquisitionError(Exception):
    """An acquisition operation error (unknown order, over-receipt, …)."""


# --------------------------------------------------------------------------- #
# Engine — the order → receipt → КСУ → ToCat lifecycle.
# --------------------------------------------------------------------------- #
class AcquisitionEngine:
    """Acquisition operations over an :class:`AcquisitionStore`.

    ``catalog`` (optional) is an :class:`access.catalog.CatalogStore` handle — the
    cluster-1 ToCat seam. When wired, :meth:`receive` reflects each batch into the
    catalog (creates/updates the bib record + 910 exemplars + the field-66 КСУ
    link). With no handle the engine is fully standalone: order / receipt / КСУ
    work, ToCat is a graceful no-op (back-compat, mirrors circulation's seam).

    ``catalog_db`` is the base (БД) whose ЭК ToCat writes into (default ``IBIS``).
    ``inv_prefix`` seeds auto-generated inventory numbers when a receipt doesn't
    supply explicit ones (910^b = MIN+1 auto-number, ACQUISITION_FUNCTIONS P-13).

    ``circulation`` (optional) is an :class:`access.circulation.CirculationEngine`
    handle — the cluster-1 «поступление → выдаётся» seam (INTEGRATION_MAP, ребро
    Комплектование↔Книговыдача). When wired, :meth:`receive` confirms each freshly
    received inventory number is **lendable now** through circulation
    (``circulation.register_acquired_item``): a copy that lands in the фонд is
    immediately available for checkout, closing the gap between поступление and
    книговыдача. The handle is used best-effort and only for the post-receipt
    confirmation — with no handle the engine is fully standalone (back-compat,
    mirrors the ``catalog=`` seam).
    """

    def __init__(self, store=None, catalog=None, catalog_db=CATALOG_DB,
                 worklist=DEFAULT_WORKLIST, inv_prefix='INV-', circulation=None):
        self.store = store or AcquisitionStore(':memory:')
        self.catalog = catalog
        self.catalog_db = catalog_db
        self.worklist = worklist
        self.inv_prefix = inv_prefix
        # Optional Circulation seam (INTEGRATION_MAP ребро Комплектование↔Книговыдача).
        # When wired, a received copy is confirmed lendable through circulation so
        # поступление → книговыдача is closed. Never a hard dependency.
        self.circulation = circulation

    # ---- order (заказ) ---------------------------------------------------- #
    def create_order(self, title, author=None, supplier=None, copies=1,
                     price=None, funding_source=None):
        """Open an order line (заказ). Returns the new order dict (status ``ordered``).

        ``copies`` is the number ordered; ``price`` the planned unit price (62^p);
        ``funding_source`` the funding code (88^L Istfin.mnu)."""
        if not title or not str(title).strip():
            raise AcquisitionError('order requires a title')
        if int(copies) <= 0:
            raise AcquisitionError('order requires copies >= 1')
        return self.store.add_order(
            str(title).strip(), author, supplier, int(copies), price,
            funding_source)

    def cancel_order(self, order_id):
        """Cancel an order. Refuses if anything was already received (a partially-
        or fully-received order can't be cancelled — those copies are in the fund).
        Returns the updated order dict."""
        order = self.store.get_order(order_id)
        if order is None:
            raise AcquisitionError('unknown order %r' % order_id)
        if order['status'] == ORDER_CANCELLED:
            return order
        if order['copies_received'] > 0:
            raise AcquisitionError(
                'cannot cancel order %r: %d copies already received'
                % (order_id, order['copies_received']))
        return self.store.update_order(order_id, order['copies_received'],
                                       ORDER_CANCELLED)

    def _next_status(self, order, copies_received):
        """Derive the order status from copies received vs ordered."""
        if copies_received <= 0:
            return ORDER_ORDERED
        if copies_received >= order['copies_ordered']:
            return ORDER_RECEIVED
        return ORDER_PARTIAL

    # ---- receipt (поступление) + КСУ + ToCat ------------------------------ #
    def receive(self, order_id, ksu_no, copies, unit_price=None,
                inv_numbers=None, act_ref=None):
        """Register ``copies`` received against ``order_id`` into КСУ ``ksu_no``.

        Steps (the full поступление → КСУ → ToCat lifecycle):

          1. validate (known order, not cancelled, no over-receipt past ordered);
          2. assign inventory numbers (explicit ``inv_numbers`` or auto MIN+1);
          3. write/accumulate the КСУ summary entry (88^E/^F/^G + act ref);
          4. record the receipt + inventory rows;
          5. advance the order status (ordered→partially_received→received);
          6. **ToCat** (when a ``catalog`` handle is wired): create or update the
             bib record and register the copies as 910 exemplars (^A free, ^b inv#,
             ^U КСУ) + the field-66 КСУ link. Re-supply of an existing title adds
             copies to the existing record (resolved by :func:`title_key`).

        Returns a result dict::

            {
              'receipt': <receipt row>,
              'ksu': <КСУ row>,
              'order': <updated order row>,
              'inventory': [inv_no, ...],
              'sum': <batch sum>,
              'catalog_mfn': <bib mfn or None>,      # None when standalone
              'catalog_action': 'created'|'updated'|None,
              'lendable': [inv_no, ...],             # copies circ confirms lendable
            }
        """
        order = self.store.get_order(order_id)
        if order is None:
            raise AcquisitionError('unknown order %r' % order_id)
        if order['status'] == ORDER_CANCELLED:
            raise AcquisitionError('order %r is cancelled' % order_id)
        copies = int(copies)
        if copies <= 0:
            raise AcquisitionError('receipt requires copies >= 1')
        already = order['copies_received']
        if already + copies > order['copies_ordered']:
            raise AcquisitionError(
                'over-receipt on order %r: %d received + %d > %d ordered'
                % (order_id, already, copies, order['copies_ordered']))

        # 2. inventory numbers — explicit, or auto MIN+1 (910^b auto-number).
        inv_numbers = self._resolve_inventory(inv_numbers, copies)

        # 3. КСУ summary entry. This batch adds 1 title (this order is one
        # наименование) and `copies` экземпляров; the sum is unit_price × copies.
        price = unit_price if unit_price is not None else order['price']
        batch_sum = round(float(price or 0) * copies, 2)
        ksu = self.store.upsert_ksu(ksu_no, add_titles=1, add_copies=copies,
                                    add_sum=batch_sum, act_ref=act_ref)

        # 4. receipt + inventory rows.
        receipt = self.store.add_receipt(order_id, ksu['id'], copies, price,
                                         batch_sum)
        for inv in inv_numbers:
            self.store.add_inventory(receipt['id'], ksu_no, inv)

        # 5. advance order status.
        new_received = already + copies
        order = self.store.update_order(order_id, new_received,
                                        self._next_status(order, new_received))

        # 6. ToCat — reflect into the catalog (best-effort, optional handle).
        catalog_mfn, catalog_action = self._to_cat(order, ksu_no, inv_numbers)
        if catalog_mfn is not None:
            self.store.set_receipt_catalog_mfn(receipt['id'], catalog_mfn)
            receipt = self.store.get_receipt(receipt['id'])

        # 7. Поступление → книговыдача: confirm each received copy is lendable now
        # through circulation (cluster-1 seam). Best-effort, optional handle.
        lendable = self._confirm_lendable(inv_numbers)

        return {
            'receipt': receipt,
            'ksu': ksu,
            'order': order,
            'inventory': inv_numbers,
            'sum': batch_sum,
            'catalog_mfn': catalog_mfn,
            'catalog_action': catalog_action,
            'lendable': lendable,
        }

    def _confirm_lendable(self, inv_numbers):
        """Confirm each received inventory number is lendable through circulation.

        The Комплектование↔Книговыдача seam: a copy that just landed in the фонд
        must be checkout-ready immediately. When a ``circulation`` handle is wired,
        ask it to register/confirm each ``inv_no`` (``register_acquired_item``);
        the engine collects the inv-numbers circulation accepted as lendable.
        Best-effort: with no handle (standalone) — or any circulation error — the
        receipt still stands; we just report an empty (or partial) lendable list."""
        if self.circulation is None:
            return []
        confirmed = []
        reg = getattr(self.circulation, 'register_acquired_item', None)
        if reg is None:
            return []
        for inv in inv_numbers:
            try:
                if reg(inv, catalog_db=self.catalog_db):
                    confirmed.append(inv)
            except Exception:
                # one bad copy must not break the receipt or the rest of the batch
                continue
        return confirmed

    def _resolve_inventory(self, inv_numbers, copies):
        """Return ``copies`` inventory numbers — explicit ones, or auto MIN+1.

        Explicit numbers must be unique (not already in the inventory ledger) and
        count exactly ``copies``. When omitted, generate sequential numbers from
        the current ledger max + 1 (910^b auto-number, ACQUISITION_FUNCTIONS P-13).
        """
        if inv_numbers is not None:
            inv_numbers = [str(x) for x in inv_numbers]
            if len(inv_numbers) != copies:
                raise AcquisitionError(
                    'inventory count %d != copies %d'
                    % (len(inv_numbers), copies))
            seen = set()
            for inv in inv_numbers:
                if inv in seen or self.store.inventory_exists(inv):
                    raise AcquisitionError('duplicate inventory number %r' % inv)
                seen.add(inv)
            return inv_numbers
        # auto MIN+1: continue from the ledger's numeric max under our prefix.
        return self._auto_inventory(copies)

    def _auto_inventory(self, copies):
        """Generate ``copies`` sequential inventory numbers (prefix + zero-padded)."""
        existing = self.store._conn().execute(  # noqa: SLF001 (own store)
            'SELECT inv_no FROM acq_inventory').fetchall()
        max_n = 0
        for r in existing:
            s = r['inv_no']
            if s.startswith(self.inv_prefix):
                tail = s[len(self.inv_prefix):]
                if tail.isdigit():
                    max_n = max(max_n, int(tail))
        return ['%s%06d' % (self.inv_prefix, max_n + i + 1)
                for i in range(copies)]

    # ---- ToCat (cluster 1: Комплектование → Каталог) ---------------------- #
    def _to_cat(self, order, ksu_no, inv_numbers):
        """Reflect a received batch into the catalog (the cluster-1 ToCat edge).

        Resolves new-vs-existing title by :func:`title_key`: an existing catalog
        record for the same (title, author) gets the new copies APPENDED as 910
        exemplars (re-supply → add copies, not duplicate); otherwise a fresh bib
        record is created. Each copy becomes a ``910`` field with ``^b`` inventory,
        ``^A`` = free (lendable now), and ``^U`` = КСУ number. The field-66 КСУ
        link (``66^u``) marks the record as catalogued from this КСУ batch.

        Returns ``(catalog_mfn, action)`` where action ∈ {'created','updated'} —
        or ``(None, None)`` when no catalog is wired / the write degrades (the
        receipt + КСУ still stand; ToCat is best-effort, mirrors circulation).
        """
        if self.catalog is None:
            return (None, None)
        try:
            existing_mfn = self._find_catalog_record(order['title'],
                                                     order['author'])
            new_910 = [{'a': EXEMPLAR_FREE, 'b': inv, 'u': ksu_no}
                       for inv in inv_numbers]
            if existing_mfn is not None:
                # Re-supply: append the new exemplars to the existing record.
                record = self.catalog.get(self.catalog_db, existing_mfn)
                if record is None:                      # vanished — fall to create
                    existing_mfn = None
                else:
                    record.setdefault('910', [])
                    if not isinstance(record['910'], list):
                        record['910'] = [record['910']]
                    record['910'].extend(new_910)
                    self._merge_ksu_link(record, ksu_no)
                    res = self.catalog.save(self.catalog_db, record,
                                            mfn=existing_mfn)
                    return (res['mfn'], 'updated') if res['saved'] else (None, None)
            # New title — build a fresh bib record.
            record = self._new_bib_record(order, ksu_no, new_910)
            res = self.catalog.save(self.catalog_db, record)
            return (res['mfn'], 'created') if res['saved'] else (None, None)
        except Exception:
            # ToCat is best-effort: a catalog/FLK failure must NOT break the
            # receipt. The КСУ + inventory are already committed.
            return (None, None)

    def _find_catalog_record(self, title, author):
        """Find an existing catalog mfn for (title, author), or None.

        Searches the catalog by title (``T=``), then disambiguates by matching the
        normalized (title, author) key so re-supply lands on the same record."""
        want = title_key(title, author)
        res = self.catalog.search(self.catalog_db, 'T=%s' % (title or ''),
                                  limit=50)
        for item in res.get('items', []):
            rec = self.catalog.get(self.catalog_db, item['mfn'])
            if rec is None:
                continue
            rt = (_first_value(rec, '200', 'a') or '')
            ra = (_first_value(rec, '700', 'a') or '')
            if title_key(rt, ra) == want:
                return item['mfn']
        return None

    def _new_bib_record(self, order, ksu_no, new_910):
        """Build a fresh I1 bib record for a newly-catalogued title (ToCat create).

        Carries заглавие (200^a/^f), author (700^a), the FLK-required worklist
        (920), language (101 rus default), the field-66 КСУ link, and the 910
        exemplars."""
        record = {
            '200': [{'a': order['title'],
                     'f': order['author'] or ''}],
            '920': self.worklist,
            '101': 'rus',
            '66': [{'u': ksu_no}],
            '910': list(new_910),
        }
        if order['author']:
            record['700'] = [{'a': order['author']}]
        return record

    @staticmethod
    def _merge_ksu_link(record, ksu_no):
        """Ensure the record carries a field-66 КСУ link for ``ksu_no`` (idempotent)."""
        insts = record.get('66')
        if insts is None:
            record['66'] = [{'u': ksu_no}]
            return
        if not isinstance(insts, list):
            insts = [insts]
            record['66'] = insts
        for inst in insts:
            if isinstance(inst, dict) and str(inst.get('u') or '') == str(ksu_no):
                return                                  # already linked
        insts.append({'u': ksu_no})

    # ---- read helpers (reporting / tests) --------------------------------- #
    def order_status(self, order_id):
        order = self.store.get_order(order_id)
        return order['status'] if order else None

    def ksu_summary(self, ksu_no):
        """The КСУ summary row (88^E titles / 88^F copies / 88^G sum + act)."""
        return self.store.get_ksu(ksu_no)

    # ---- disposal / списание (cluster 5.2: Книговыдача → КСУ выбытия) ------ #
    def record_disposal(self, inv_no, ksu_disp_no, reason='lost', ref=None,
                        amount=1):
        """Record a выбытие (списание) of one inventory number into the КСУ выбытия.

        The Книговыдача→Комплектование (КСУ) seam (INTEGRATION_MAP ребро 5.2):
        circulation, on a confirmed loss / write-off, calls this so the lost copy
        is reflected in the acquisition выбытие ledger (910^V № КСУ выбытия, 910^X
        кол-во, status «списан»). The original поступление КСУ (910^U) is
        cross-linked automatically when the inventory number is known to
        acquisition's inventory ledger (re-supply traceability партия↔выбытие).

        Idempotent per ``(inv_no, ksu_disp_no)``: re-recording the same copy on the
        same акт returns the existing row (no double count). Returns the disposal
        row dict."""
        if not inv_no or not str(inv_no).strip():
            raise AcquisitionError('disposal requires an inventory number')
        if not ksu_disp_no or not str(ksu_disp_no).strip():
            raise AcquisitionError('disposal requires a КСУ выбытия number')
        ksu_recv = self.store.receipt_ksu_for_inv(str(inv_no))
        return self.store.add_disposal(
            str(inv_no), str(ksu_disp_no), reason=reason, ksu_recv_no=ksu_recv,
            amount=amount, ref=ref)

    def disposal_summary(self, ksu_disp_no):
        """Rollup of one акт списания (copies + total amount). See store method."""
        return self.store.disposal_summary(ksu_disp_no)


# --------------------------------------------------------------------------- #
# Record-draft accessors (local copies so the module is self-contained — same
# semantics as catalog.py's _field_values, but we only need the first value).
# --------------------------------------------------------------------------- #
def _first_value(record, field, subfield):
    """First non-empty value of ``field``'s ``subfield`` in a record, or ''."""
    raw = record.get(field) if record else None
    if raw is None:
        return ''
    insts = raw if isinstance(raw, list) else [raw]
    for inst in insts:
        if isinstance(inst, dict):
            v = inst.get(subfield) or inst.get(subfield.upper()) or ''
        else:
            v = inst if subfield in ('', None) else ''
        if v:
            return str(v)
    return ''
