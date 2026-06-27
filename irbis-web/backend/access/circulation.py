#!/usr/bin/env python3
"""Circulation engine — loan / hold / return / renew + business rules.

Gap E2, epic #188. Implements SPEC_business_circulation.md, FIRST shippable slice.

What this module is
-------------------
A *self-contained* circulation engine: the domain rules that decide whether a
loan / renewal / hold is **allowed**, and that **compute** fines, replacement
values and queue positions — over a small own sqlite store. It is deliberately
standalone: pure stdlib + ``sqlite3`` (dev parity with the rest of the backend,
ADR-004), no network I/O, no new pip deps.

The spec is emphatic that a *rule* is not an *operation*: a rule is the predicate
``decide(ctx) -> {allow|deny|require_override, reasons[], computed?}`` that gates
the ws3 operation (create RDR.40, set ``40^F``/``40^L``/``40^U`` …). Here the two
are folded together for the slice — the engine both decides and applies to its
own store — but the *decision* is always exposed (``Decision``) so the rule layer
is testable and reusable in isolation, exactly as §0 demands.

The moving parts
----------------
  1. :class:`CirculationStore` — own sqlite store with four tables:
       * ``reader(id, category, blocked)``
       * ``loan(id, reader, item, due, returned, renewals, lost_status)``
       * ``hold(id, reader, item, status, queued_at, ready_at)``
       * ``fine(id, reader, loan, amount, status, kind)``
     create-on-init; ``:memory:`` / temp file in tests.
  2. :func:`default_policy` — the per-tenant ``circ_policy`` dict, defaults
     straight from §5.3 / §7 of the spec (limits by category, ``max_prolong=5``,
     ``fine_per_day`` / ``fine_cap`` / ``overdue_grace_days``, ``lost_after_days``,
     ``hold_shelf_days`` …).
  3. :class:`CirculationEngine` — the operations: ``checkout`` (limits + debtor
     gate, ``staff_override``), ``return_item`` (clear debt marker, trigger next
     hold), ``renew`` (holds-block-renewal + renew cap), ``place_hold`` (FIFO
     position), ``accrue_fines`` (the §3.2 formula), ``mark_lost`` (candidate →
     confirm), ``queue_position``. Every gated op returns a :class:`Decision`.

Rule decisions enforced (per spec section)
------------------------------------------
  * §1 holds-block-renewal — ``holds_block_renewal`` ∈ {block, threshold, allow};
    default ``block``: an active hold/queue on the item denies renewal
    (``hold_exists``) unless ``staff_override`` (right ``circ.renew.override_hold``).
    Renewal cap ``max_prolong`` (default 5).
  * §2 debtor: two separate rules — reader self-service gate (a *hard* debtor is
    denied checkout/renew with ``reader_has_debt``) vs staff override
    (``circ.lend.override_debt``) which lets the librarian lend over the debt.
  * §3 fines — ``min(fine_per_day × billable_days, fine_cap)`` after
    ``overdue_grace_days``; ``fine_per_day == 0`` ⇒ fine-free; accrual is
    idempotent per ``(loan, day)``.
  * §4 lost — overdue beyond ``lost_after_days`` ⇒ ``lost_candidate`` + staff
    alert (no auto-debt); ``mark_lost(confirm=True)`` ⇒ ``lost`` + replacement
    charge ``910^E × multiplier + fee`` (fallback when price empty).
  * §5 limits — ``max_books`` / ``max_dolg_books`` by category; over-limit ⇒
    ``limit_exceeded`` unless ``staff_override``.
  * §6 hold queue — FIFO position; return hands the freed item to the queue head
    (``hold_ready`` + shelf TTL).

Events
------
Operations return *event intents* (``{'event','recipient','payload'}``) for A6
(``hold_ready`` / ``fine_charged`` / ``renewal_confirmed`` / ``fine_paid`` /
``hold_cancelled`` / ``lost_confirmed`` / ``staff_alert`` …). If an
:class:`access.notifications.NotificationQueue` is handed to the engine (the
optional ``notifications=`` handle, mirroring the ``catalog=`` seam) each intent
is also **rendered + enqueued** through A6: the event is mapped to its template,
a reader-friendly render context is built (item→title, epoch→date, price→amount,
currency default), and the notice is queued on the template's default channels
(idempotent by dedup_key — no double-send). A reader-facing event notifies the
reader; ``staff_alert`` is re-addressed to the staff recipient. Dispatch is
best-effort and fully isolated: an unknown event or any A6 error is skipped, the
circulation operation still succeeds. With no handle the engine is standalone —
intents are only returned, never dispatched (back-compat).
"""
import sqlite3
import threading
import time

# Optional A6 integration — emit events through its idempotent enqueue when a
# queue is wired; else we just return event intents. Never a hard dependency.
try:  # pragma: no cover - depends on sibling A6 module / wiring
    from access import notifications as _notifications  # type: ignore
except Exception:  # ImportError when run in isolation
    _notifications = None


SECONDS_PER_DAY = 86400

# Маркер «книга не возвращена / задолженность» в подполе 40^F (FST DOLG=).
# Из конфигов: `RETURNDATE1=F`, признак долга = `40^F:'******'` (DB_CIRCULATION
# §3/§5). Пока книга на руках — в 40^F стоит этот маркер; при возврате он
# замещается датой фактического возврата (40^F = дата).
DEBT_MARKER = '******'


# --------------------------------------------------------------------------- #
# reservstatus (RQST 910^A 0–4) ↔ наш enum hold.status — ребро 2.6.
# --------------------------------------------------------------------------- #
# «Одно подполе — разные кодировки» (recon #CIRC-06, DB_CIRCULATION §6, ws3 §6):
# 910^A в RQST (статус БРОНИ, словарь `reservstatus.mnu`, коды 0–4) — это НЕ то
# же, что 910^A в ЭК (статус ЭКЗЕМПЛЯРА, `ste.mnu`). Наш движок хранит статус
# брони отдельным enum'ом `hold.status` (queued|ready|fulfilled|cancelled|expired) —
# дизайн их верно разводит; здесь — двусторонний словарь кодов <-> enum.
#
# Семантика `reservstatus.mnu` (DB_CIRCULATION §5 «БРОНИРОВАНИЕ»):
#   0 — заказ отправлен с места хранения (МХР) на место выдачи (МВ): экз. в пути,
#       читатель ещё ждёт → у нас бронь стоит в очереди      => 'queued'
#   1 — получен на МВ / готов для выдачи: бронь «на полке»,
#       читатель может забирать                              => 'ready'
#   2 — получен от читателя (бронь сработала, выдан/закрыт)  => 'fulfilled'
#   3 — для возврата на МХР: экз. больше не держится за читателем,
#       уходит в фонд (бронь не реализована)                 => 'expired'
#   4 — отправлен с МВ обратно на МХР (тот же исход — снят с полки) => 'expired'
#
# Прямое отображение код->enum (resolve_hold_status_in):
RESERVSTATUS_TO_HOLD = {
    '0': 'queued',
    '1': 'ready',
    '2': 'fulfilled',
    '3': 'expired',
    '4': 'expired',
}
# Обратное enum->код (hold_status_to_reservstatus). 3 и 4 оба означают «снят с
# полки»; для каноничной обратной проводки expired → '3' (на МХР), как первый из
# пары «возврат в фонд». `cancelled` — чисто наш статус (отмена читателем до
# срабатывания брони): в `reservstatus.mnu` отдельного кода нет, бронь просто
# исчезает из RQST (транзитная БД чистится `rqst_clear.gbl`) — отображаем в None.
HOLD_TO_RESERVSTATUS = {
    'queued': '0',
    'ready': '1',
    'fulfilled': '2',
    'expired': '3',
    'cancelled': None,
}


# --------------------------------------------------------------------------- #
# Policy — the per-tenant ``circ_policy`` (defaults from SPEC §5.3 / §7).
# --------------------------------------------------------------------------- #
# Limit matrix keyed by reader category (50.mnu: В01–В05 adults, Д01–Д03 kids,
# STD student, GUEST guest). Values are the spec's starting defaults; a tenant
# tunes them via the low-code configurator (D1). ``_DEFAULT`` is the fallback
# profile used before 50.mnu is seeded (A5) / for an unknown category.
_LIMIT_MATRIX = {
    'В01': {'max_books': 5,  'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
    'В02': {'max_books': 5,  'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
    'В03': {'max_books': 5,  'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
    'В04': {'max_books': 5,  'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
    'В05': {'max_books': 5,  'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
    'Д01': {'max_books': 7,  'max_dolg_books': 1, 'max_return_days': 14, 'max_prolong': 3},
    'Д02': {'max_books': 7,  'max_dolg_books': 1, 'max_return_days': 14, 'max_prolong': 3},
    'Д03': {'max_books': 7,  'max_dolg_books': 1, 'max_return_days': 14, 'max_prolong': 3},
    'STD': {'max_books': 15, 'max_dolg_books': 2, 'max_return_days': 30, 'max_prolong': 5},
    'GUEST': {'max_books': 1, 'max_dolg_books': 0, 'max_return_days': 1,  'max_prolong': 0},
    '_DEFAULT': {'max_books': 5, 'max_dolg_books': 1, 'max_return_days': 20, 'max_prolong': 5},
}


def default_policy(tenant_id='public'):
    """Return a fresh per-tenant ``circ_policy`` dict (defaults from §5.3 / §7).

    A fresh deep-ish copy each call so a caller mutating one tenant's policy
    never leaks into another (isolation, AC7). Values are the spec's documented
    starting defaults — every one is meant to be tuned per-tenant.
    """
    return {
        'tenant_id': tenant_id,
        # §5 limits — by category × item kind (here: by category).
        'limits': {cat: dict(lim) for cat, lim in _LIMIT_MATRIX.items()},
        # §1 renewal.
        'renewal': {
            'holds_block_renewal': 'block',   # block | threshold | allow
            'hold_block_threshold': 0,        # threshold mode: queue len that still allows
            'strong_prolong': True,
        },
        # §2 debtor.
        'debt': {
            'overdue_grace_days': 1,          # soft window: not yet a hard debtor
            'reader_block_on_hard': True,     # hard debtor self-service gate
            'override_grant': 'circ.lend.override_debt',
        },
        # §3 fines — min(fine_per_day × billable_days, fine_cap).
        'fine': {
            'fine_per_day': {'_DEFAULT': 5.0, 'Д01': 0.0, 'Д02': 0.0, 'Д03': 0.0,
                             'rare_fund': 20.0},
            'fine_cap': 500.0,                # ceiling per loan (≤ item price, §3.2)
            'overdue_grace_days': 1,          # billing grace before accrual starts
            'currency': 'RUB',
            'pay_dbn': 'PAY',
            'waive_grant': 'circ.fine.waive',
        },
        # §4 lost.
        'lost': {
            'lost_after_days': 60,            # overdue beyond this ⇒ lost_candidate
            'multiplier': 1.0,                # replacement = price × mult + fee
            'handling_fee': 0.0,
            'default_replacement_value': 100.0,  # fallback when 910^E empty/0
            'lost_supersedes_fine': True,
            'confirm_grant': 'circ.lost.confirm',
        },
        # §6 hold queue.
        'hold': {
            'priority': 'fifo',
            'hold_shelf_days': 3,             # = pickup_ttl in a locker (§6.4)
            'return_to_reservable': True,
        },
        # §8 reminders (ребро 3.5: срок 40^E → due_soon / overdue уведомления).
        'reminder': {
            'due_soon_days': 3,               # окно «скоро срок»: дней до due
        },
    }


def category_limits(policy, category):
    """The limit row for ``category`` (falls back to ``_DEFAULT``)."""
    limits = policy['limits']
    return limits.get(category) or limits['_DEFAULT']


def fine_per_day(policy, category, item_kind=None):
    """Per-day fine rate for ``category`` (and optional ``item_kind`` override)."""
    table = policy['fine']['fine_per_day']
    if item_kind and item_kind in table:
        return float(table[item_kind])
    if category in table:
        return float(table[category])
    return float(table.get('_DEFAULT', 0.0))


# --------------------------------------------------------------------------- #
# Decision — the rule predicate result (allow | deny | require_override).
# --------------------------------------------------------------------------- #
ALLOW = 'allow'
DENY = 'deny'
REQUIRE_OVERRIDE = 'require_override'


class Decision:
    """Result of a rule: ``decision`` + machine ``reasons`` + ``computed`` data.

    ``ok`` is True only for :data:`ALLOW`. ``reasons`` is a list of short stable
    codes (``limit_exceeded`` / ``reader_has_debt`` / ``hold_exists`` /
    ``max_prolong_reached`` …) for the UI / notification layer. ``events`` carries
    any A6 event intents the operation produced.
    """

    def __init__(self, decision, reasons=None, computed=None, events=None):
        self.decision = decision
        self.reasons = list(reasons or [])
        self.computed = dict(computed or {})
        self.events = list(events or [])

    @property
    def ok(self):
        return self.decision == ALLOW

    def __repr__(self):
        return 'Decision(%s, reasons=%r, computed=%r)' % (
            self.decision, self.reasons, self.computed)


# --------------------------------------------------------------------------- #
# Store — own sqlite (reader / loan / hold / fine). create-on-init.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS reader (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL DEFAULT '_DEFAULT',
  blocked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS loan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reader TEXT NOT NULL REFERENCES reader(id),
  item TEXT NOT NULL,             -- shifr / 903
  item_kind TEXT,                 -- читальный зал / редкий фонд / NULL
  item_price REAL,                -- 910^E (replacement basis)
  due REAL NOT NULL,              -- planned return epoch (40^E)
  checked_out_at REAL NOT NULL,
  returned INTEGER NOT NULL DEFAULT 0,   -- 40^F: 0='******' on-hand, 1=returned
  returned_at REAL,
  renewals INTEGER NOT NULL DEFAULT 0,   -- prolong_count (MAXPROLONGCOUNT)
  lost_status TEXT NOT NULL DEFAULT 'none'  -- none | lost_candidate | lost
       CHECK (lost_status IN ('none','lost_candidate','lost'))
);
CREATE INDEX IF NOT EXISTS loan_reader_idx ON loan(reader, returned);
CREATE INDEX IF NOT EXISTS loan_item_idx ON loan(item, returned);
CREATE TABLE IF NOT EXISTS hold (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reader TEXT NOT NULL REFERENCES reader(id),
  item TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued'   -- queued | ready | fulfilled | cancelled | expired
       CHECK (status IN ('queued','ready','fulfilled','cancelled','expired')),
  queued_at REAL NOT NULL,
  ready_at REAL
);
CREATE INDEX IF NOT EXISTS hold_item_idx ON hold(item, status, queued_at);
CREATE TABLE IF NOT EXISTS fine (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reader TEXT NOT NULL REFERENCES reader(id),
  loan INTEGER REFERENCES loan(id),
  amount REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'accrued'  -- accrued | charged | paid | waived
       CHECK (status IN ('accrued','charged','paid','waived')),
  kind TEXT NOT NULL DEFAULT 'fine_overdue'  -- fine_overdue | lost_replacement
       CHECK (kind IN ('fine_overdue','lost_replacement')),
  accrued_through REAL,           -- last day already accrued (idempotency)
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  UNIQUE(loan, kind)              -- one fine row per loan per kind (§3.4 idempotent)
);
CREATE INDEX IF NOT EXISTS fine_reader_idx ON fine(reader, status);
CREATE TABLE IF NOT EXISTS rdr_arh (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  loan INTEGER,                   -- исходная выдача (loan.id), для трассировки
  reader TEXT NOT NULL,           -- 30 (RI=) читатель
  item TEXT NOT NULL,             -- 40^B инв.№ / 910^b
  due REAL,                       -- 40^E план. возврат
  checked_out_at REAL,            -- 40^D дата выдачи
  returned_at REAL NOT NULL,      -- 40^F дата факт. возврата
  lost_status TEXT,               -- состояние на момент архивации
  archived_at REAL NOT NULL       -- момент переноса в архив (152-ФЗ ретенция)
);
CREATE INDEX IF NOT EXISTS rdr_arh_reader_idx ON rdr_arh(reader);
CREATE INDEX IF NOT EXISTS rdr_arh_item_idx ON rdr_arh(item);
"""


class CirculationStore:
    """Own sqlite store for circulation state (reader / loan / hold / fine).

    ``db_path=':memory:'`` (default) or a temp file for tests; create-on-init.
    Connection is thread-local (house style); ``sqlite3.Row`` rows are returned
    as plain dicts from the accessors.
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

    # ---- readers ---------------------------------------------------------- #
    def add_reader(self, reader_id, category='_DEFAULT', blocked=0):
        c = self._conn()
        c.execute('INSERT OR REPLACE INTO reader(id,category,blocked) VALUES(?,?,?)',
                  (reader_id, category, 1 if blocked else 0))
        c.commit()
        return self.get_reader(reader_id)

    def get_reader(self, reader_id):
        r = self._conn().execute(
            'SELECT * FROM reader WHERE id=?', (reader_id,)).fetchone()
        return dict(r) if r else None

    def set_blocked(self, reader_id, blocked):
        c = self._conn()
        c.execute('UPDATE reader SET blocked=? WHERE id=?',
                  (1 if blocked else 0, reader_id))
        c.commit()

    # ---- loans ------------------------------------------------------------ #
    def add_loan(self, reader_id, item, due, checked_out_at,
                 item_kind=None, item_price=None):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO loan(reader,item,item_kind,item_price,due,'
            'checked_out_at) VALUES(?,?,?,?,?,?)',
            (reader_id, item, item_kind, item_price, due, checked_out_at))
        c.commit()
        return self.get_loan(cur.lastrowid)

    def get_loan(self, loan_id):
        r = self._conn().execute(
            'SELECT * FROM loan WHERE id=?', (loan_id,)).fetchone()
        return dict(r) if r else None

    def loans_on_hand(self, reader_id):
        """RDR.40 rows still on hand (``40^F='******'``) for a reader."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan WHERE reader=? AND returned=0 AND lost_status!=? '
            'ORDER BY id', (reader_id, 'lost')).fetchall()]

    def reader_loans(self, reader_id):
        """Все выдачи читателя (на руках + возвращённые) — для полного формуляра."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan WHERE reader=? ORDER BY id',
            (reader_id,)).fetchall()]

    def count_on_hand(self, reader_id):
        """``count_on_hand`` = number of RDR.40 with ``40^F='******'`` (§5.4)."""
        return self._conn().execute(
            'SELECT COUNT(*) AS n FROM loan WHERE reader=? AND returned=0 '
            'AND lost_status!=?', (reader_id, 'lost')).fetchone()['n']

    def item_on_hand_count(self, item):
        """Number of on-hand (not returned, not lost) loans of ``item`` (910^b).

        The read book-provision uses to decide whether an issued copy still
        belongs to the фонд (INTEGRATION_MAP ребро 4.4/4.7): a copy on a reader's
        hands is provisioned, just in use. A confirmed-lost copy has left the фонд
        (``lost_status='lost'``) and is excluded."""
        return self._conn().execute(
            'SELECT COUNT(*) AS n FROM loan WHERE item=? AND returned=0 '
            'AND lost_status!=?', (item, 'lost')).fetchone()['n']

    def open_overdue_loans(self, today_epoch, grace_days=0):
        """On-hand loans past ``due + grace`` (basis for accrual / lost scan)."""
        cutoff = today_epoch - grace_days * SECONDS_PER_DAY
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan WHERE returned=0 AND lost_status!=? AND due<? '
            'ORDER BY id', ('lost', cutoff)).fetchall()]

    def due_soon_loans(self, today_epoch, window_end_epoch):
        """On-hand loans whose планируемый возврат (40^E ``due``) попадает в окно
        ``[today, window_end]`` и ещё НЕ просрочен — основа ``due_soon`` напоминаний
        (ребро 3.5). Просроченные (``due < today``) сюда не попадают: их отдаёт
        :meth:`open_overdue_loans` (комплементарные множества, без пересечения)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan WHERE returned=0 AND lost_status!=? AND due>=? '
            'AND due<=? ORDER BY id',
            ('lost', today_epoch, window_end_epoch)).fetchall()]

    def mark_returned(self, loan_id, returned_at):
        c = self._conn()
        c.execute('UPDATE loan SET returned=1, returned_at=? WHERE id=?',
                  (returned_at, loan_id))
        c.commit()

    def bump_renewal(self, loan_id, new_due):
        c = self._conn()
        c.execute('UPDATE loan SET renewals=renewals+1, due=? WHERE id=?',
                  (new_due, loan_id))
        c.commit()

    def set_lost_status(self, loan_id, status):
        c = self._conn()
        c.execute('UPDATE loan SET lost_status=? WHERE id=?', (status, loan_id))
        c.commit()

    # ---- archive (RDR_ARH) ------------------------------------------------ #
    def archive_loan(self, loan, returned_at, archived_at):
        """Перенести завершённую (возвращённую) выдачу в архив ``rdr_arh``.

        Ребро INTEGRATION_MAP 2.5: при возврате запись о выдаче дублируется в
        отдельную сущность-архив RDR_ARH (152-ФЗ ретенция). Это **opt-in**
        добавление: сама строка ``loan`` остаётся помеченной ``returned=1`` —
        архив её не заменяет, а накапливает историю. Возвращает строку архива.
        """
        c = self._conn()
        cur = c.execute(
            'INSERT INTO rdr_arh(loan,reader,item,due,checked_out_at,'
            'returned_at,lost_status,archived_at) VALUES(?,?,?,?,?,?,?,?)',
            (loan['id'], loan['reader'], loan['item'], loan['due'],
             loan['checked_out_at'], returned_at, loan['lost_status'],
             archived_at))
        c.commit()
        return self.get_archived(cur.lastrowid)

    def get_archived(self, arh_id):
        r = self._conn().execute(
            'SELECT * FROM rdr_arh WHERE id=?', (arh_id,)).fetchone()
        return dict(r) if r else None

    def archived_loans(self, reader_id):
        """Архивные (возвращённые) выдачи читателя — поле 40 в RDR_ARH."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM rdr_arh WHERE reader=? ORDER BY id',
            (reader_id,)).fetchall()]

    def count_archived(self, reader_id=None):
        """Число архивных записей (всего или по читателю)."""
        if reader_id is None:
            return self._conn().execute(
                'SELECT COUNT(*) AS n FROM rdr_arh').fetchone()['n']
        return self._conn().execute(
            'SELECT COUNT(*) AS n FROM rdr_arh WHERE reader=?',
            (reader_id,)).fetchone()['n']

    # ---- holds ------------------------------------------------------------ #
    def add_hold(self, reader_id, item, queued_at):
        c = self._conn()
        cur = c.execute(
            'INSERT INTO hold(reader,item,queued_at) VALUES(?,?,?)',
            (reader_id, item, queued_at))
        c.commit()
        return self.get_hold(cur.lastrowid)

    def get_hold(self, hold_id):
        r = self._conn().execute(
            'SELECT * FROM hold WHERE id=?', (hold_id,)).fetchone()
        return dict(r) if r else None

    def active_holds(self, item):
        """Queue for an item: queued/ready, FIFO by ``queued_at`` then id."""
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM hold WHERE item=? AND status IN ('queued','ready') "
            'ORDER BY queued_at, id', (item,)).fetchall()]

    def set_hold_status(self, hold_id, status, ready_at=None):
        c = self._conn()
        if ready_at is not None:
            c.execute('UPDATE hold SET status=?, ready_at=? WHERE id=?',
                      (status, ready_at, hold_id))
        else:
            c.execute('UPDATE hold SET status=? WHERE id=?', (status, hold_id))
        c.commit()

    # ---- fines ------------------------------------------------------------ #
    def upsert_fine(self, reader_id, loan_id, amount, kind='fine_overdue',
                    status='accrued', accrued_through=None):
        """Idempotent per ``(loan, kind)`` — one fine row per loan per kind."""
        c = self._conn()
        c.execute(
            'INSERT INTO fine(reader,loan,amount,kind,status,accrued_through,'
            'updated_at) VALUES(?,?,?,?,?,?,?) '
            'ON CONFLICT(loan,kind) DO UPDATE SET amount=excluded.amount, '
            'status=excluded.status, accrued_through=excluded.accrued_through, '
            'updated_at=excluded.updated_at',
            (reader_id, loan_id, amount, kind, status, accrued_through, time.time()))
        c.commit()
        return self.get_fine(loan_id, kind)

    def get_fine(self, loan_id, kind='fine_overdue'):
        r = self._conn().execute(
            'SELECT * FROM fine WHERE loan=? AND kind=?',
            (loan_id, kind)).fetchone()
        return dict(r) if r else None

    def set_fine_status(self, fine_id, status):
        c = self._conn()
        c.execute('UPDATE fine SET status=?, updated_at=? WHERE id=?',
                  (status, time.time(), fine_id))
        c.commit()

    def outstanding_fines(self, reader_id):
        """Unpaid / un-waived fines for a reader (accrued or charged)."""
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM fine WHERE reader=? AND status IN ('accrued','charged') "
            'ORDER BY id', (reader_id,)).fetchall()]

    def total_outstanding(self, reader_id):
        row = self._conn().execute(
            "SELECT COALESCE(SUM(amount),0) AS s FROM fine WHERE reader=? "
            "AND status IN ('accrued','charged')", (reader_id,)).fetchone()
        return float(row['s'])


# --------------------------------------------------------------------------- #
# Debt model — §2.1: none | soft | hard.
# --------------------------------------------------------------------------- #
def debt_level(store, policy, reader_id, today_epoch):
    """Classify a reader's debt (§2.1): ``none`` / ``soft`` / ``hard``.

    ``hard`` if any of: an overdue on-hand loan past the overdue grace; a
    confirmed-lost loan with an unpaid replacement; an unpaid fine over the money
    grace. ``soft`` = something owed but inside grace. ``none`` = clean.
    """
    grace_days = policy['debt']['overdue_grace_days']
    cutoff_hard = today_epoch - grace_days * SECONDS_PER_DAY

    has_soft = False
    # overdue on-hand loans
    for ln in store.loans_on_hand(reader_id):
        if ln['due'] < today_epoch:
            if ln['due'] < cutoff_hard:
                return 'hard'
            has_soft = True
    # unpaid fines / lost replacement
    fines = store.outstanding_fines(reader_id)
    for f in fines:
        if f['kind'] == 'lost_replacement' and f['amount'] > 0:
            return 'hard'
    total = sum(f['amount'] for f in fines)
    if total > 0:
        # money grace: a token amount stays soft; here grace is the per-day rate
        # floor — any non-trivial balance is hard. Default money grace = 0 ⇒ hard.
        return 'hard'
    return 'soft' if has_soft else 'none'


# --------------------------------------------------------------------------- #
# Engine — operations (each gated op returns a Decision).
# --------------------------------------------------------------------------- #
class CirculationEngine:
    """Circulation operations over a :class:`CirculationStore` + ``circ_policy``.

    ``notifier`` (optional) is an :class:`access.notifications.NotificationQueue`;
    when present, event intents are also enqueued (idempotent). ``tenant`` scopes
    enqueued events. All time arguments are epoch seconds — tests inject ``today``
    deterministically.
    """

    def __init__(self, store=None, policy=None, notifier=None, tenant='public',
                 catalog=None, catalog_db='IBIS', notifications=None,
                 staff_recipient='staff', acquisition=None,
                 archive_on_return=False, devices=None, pay=None,
                 reader_registry=None):
        self.store = store or CirculationStore(':memory:')
        self.policy = policy or default_policy(tenant)
        # Optional A6 (notifications) seam — INTEGRATION_MAP edge Circulation→A6.
        # ``notifications`` is the documented handle (an
        # :class:`access.notifications.NotificationQueue`); ``notifier`` is a
        # back-compat alias for the same role. Whichever is supplied wins
        # (``notifications`` takes precedence if both are given). With no handle
        # the engine stays fully standalone — events are only *returned* as
        # intents, never dispatched (back-compat, mirrors the ``catalog=`` seam).
        self.notifier = notifications if notifications is not None else notifier
        # Staff-facing events (``staff_alert``) are addressed to a librarian, not
        # the reader; this is the recipient handle they enqueue to.
        self.staff_recipient = staff_recipient
        self.tenant = tenant
        # Optional Catalog↔Circulation seam (INTEGRATION_MAP edges 2.1/2.2). When a
        # ``catalog`` (access.catalog.CatalogStore) handle is wired, checkout flips
        # the matching exemplar's ``910^A`` 0→1 (issued) and return flips it 1→0
        # (free); availability reads come from the catalog. ``catalog_db`` is the
        # base whose exemplars this engine reflects into (default IBIS / ЭК). With
        # no handle the engine stays fully standalone (back-compat).
        self.catalog = catalog
        self.catalog_db = catalog_db
        # Optional Acquisition (КСУ) seam (INTEGRATION_MAP ребро 5.2:
        # Книговыдача→Комплектование). When an ``acquisition``
        # (access.acquisition.AcquisitionEngine) handle is wired, a confirmed loss
        # (``mark_lost(confirm=True)``) is reflected into the acquisition КСУ
        # выбытия: the lost copy is written off as выбытие (910^V/^X, статус
        # «списан»). Best-effort, optional — with no handle circulation stays fully
        # standalone (back-compat, mirrors the ``catalog=`` seam).
        self.acquisition = acquisition
        # Архив выдач RDR_ARH (ребро 2.5). **Opt-in**: когда True, ``return_item``
        # дополнительно к ``returned=1`` переносит завершённую выдачу в архив
        # ``rdr_arh`` (152-ФЗ ретенция — отдельная сущность истории выдач). По
        # умолчанию (False) поведение прежнее: только флаг ``returned=1`` в той
        # же таблице, без архива (back-compat).
        self.archive_on_return = archive_on_return
        # Optional Devices seam (INTEGRATION_MAP рёбра 12.6/12.7:
        # ``device_event.loan_ref → loan`` / ``hold_ref → hold``). When a
        # ``devices`` (:class:`access.devices.DeviceService`) handle is wired AND an
        # operation carries a ``device_id`` (станция самообслуживания инициировала
        # выдачу/возврат/бронь), the op also writes a ``device_event`` linking the
        # device journal to the new loan/hold. Best-effort, optional — with no
        # handle / no device_id circulation stays fully standalone (back-compat,
        # mirrors the ``catalog=`` seam).
        self.devices = devices
        # Optional PAY seam (INTEGRATION_MAP ребро 3.3: утеря/штраф → касса PAY).
        # ``pay`` (:class:`access.pay.PayLedger`) — финансовый леджер читателя
        # (``RI=``). When wired, circulation posts a charge on a confirmed loss
        # (возмещение 910^E) и на начисленный при возврате штраф, и a payment on
        # ``pay_fine``. Best-effort, optional — with no handle circulation stays
        # standalone (back-compat).
        self.pay = pay
        # Optional Reader-registry seam (INTEGRATION_MAP ребро 3.1): own-store
        # профиль читателя RDR. When wired, circulation резолвит читателя как
        # полную ЗАПИСЬ (ФИО/категория/статус/контакты) через duck-typed
        # ``reader_registry.resolve(reader_id)``, а не держит строку-id. Best-effort/
        # опционально — без хендла поведение прежнее (back-compat).
        self.reader_registry = reader_registry

    # ---- acquisition-driven seams (поступление → выдача · выдача → КСУ) ---- #
    def register_acquired_item(self, item, catalog_db=None):
        """Confirm a freshly-acquired copy (``item`` = 910^b) is lendable now.

        The Комплектование↔Книговыдача seam (called by
        :meth:`access.acquisition.AcquisitionEngine.receive` through its
        ``circulation`` handle). A received copy that has been reflected into the
        catalog as a free 910 exemplar is checkout-ready: this returns True iff the
        copy is free per the catalog (``910^A=0``). When no catalog is wired the
        copy is accepted as lendable by default (circulation keeps no inventory of
        its own — the loan only references the item shifr). Read-only: it asserts
        lendability, it does not create a loan."""
        db = catalog_db or self.catalog_db
        if self.catalog is None:
            return True  # no catalog opinion — circulation lends against the shifr
        try:
            found = self.catalog.find_exemplar(db, item)
            if found is None:
                return False  # not in the catalog ⇒ not yet a known lendable copy
            return self.catalog.is_available(db, item)
        except Exception:
            return False

    def item_on_hand(self, item):
        """True iff ``item`` (910^b) is on an on-hand loan (not returned, not lost).

        The read-only probe book-provision uses to count a checked-out copy as
        still-provisioned фонд (INTEGRATION_MAP ребро 4.4/4.7)."""
        return self.store.item_on_hand_count(item) > 0

    # ---- event emission --------------------------------------------------- #
    # Events that are addressed to library staff (not the reader): they describe
    # an action a librarian must take (write-off candidate), so they enqueue to
    # ``staff_recipient`` and the catalog routes them to the staff channel.
    _STAFF_EVENTS = frozenset({'staff_alert'})

    def _notice_context(self, event, recipient, payload):
        """Map a circulation event payload to its A6 *template* render context.

        The notification templates (access.notifications.EventCatalog) interpolate
        reader-friendly slots — ``title`` / ``reader_name`` / ``due_date`` /
        ``amount`` / ``currency`` / ``hold_until`` … — but the circulation engine
        speaks in domain terms (``item`` shifr, ``due`` epoch, ``price`` …). This
        bridges the two so a template never renders with a literal ``{title}`` for
        want of the key. Unknown slots degrade gracefully (the renderer leaves a
        missing placeholder verbatim), but the common ones are always supplied.

        The reader/staff identity drives ``reader_name``; ``ref`` is carried
        through verbatim so A6's dedup key stays the circulation domain id (one
        enqueue per logical event, no double-send).
        """
        ctx = dict(payload or {})
        # reader/staff display name — the store holds no human name, so the
        # reader id is the best available label (a real directory would map it).
        ctx.setdefault('reader_name', payload.get('reader_name') or recipient)
        # item shifr stands in for the human title until a catalog title is wired.
        item = payload.get('item')
        if item is not None:
            ctx.setdefault('title', payload.get('title', item))
        # epoch fields → human dates the templates print.
        for src, dst in (('due', 'due_date'), ('hold_until', 'hold_until')):
            val = payload.get(src)
            if val is not None and dst not in ctx:
                ctx[dst] = self._fmt_date(val)
        # lost replacement carries ``price`` as the charge basis → ``amount``.
        if 'amount' not in ctx and payload.get('price') is not None:
            ctx['amount'] = payload['price']
        # currency default so {currency} never renders verbatim on money notices.
        if 'amount' in ctx:
            ctx.setdefault('currency', self.policy['fine']['currency'])
        return ctx

    @staticmethod
    def _fmt_date(value):
        """Format an epoch (or pass through a string) as YYYY-MM-DD for a notice."""
        try:
            return time.strftime('%Y-%m-%d', time.localtime(float(value)))
        except (TypeError, ValueError):
            return value

    def _emit(self, event, recipient, payload):
        """Build an event intent; render + enqueue it through A6 when wired.

        Returns the event *intent* (``{'event','recipient','payload'}``) regardless
        of dispatch — the rule layer never depends on A6 being present. When a
        notifications handle IS wired the notice is also routed to A6:

          * the event is mapped to its template (A6 ``EventCatalog``) and a
            reader-friendly render context is built (:meth:`_notice_context`);
          * a reader-facing event notifies the reader; ``staff_alert`` is
            re-addressed to ``staff_recipient`` (the catalog routes it to the
            staff channel);
          * ``enqueue`` resolves the template's default channels and queues a
            single notice (idempotent by dedup_key — no double-send).

        Robustness: an event with no matching template, or any dispatch failure,
        is logged-and-skipped — it never propagates out of the circulation
        operation (the loan/return/hold still succeeds).
        """
        intent = {'event': event, 'recipient': recipient, 'payload': dict(payload)}
        notifier = self.notifier
        if notifier is None:
            return intent  # standalone — only the intent, no dispatch (back-compat)
        try:
            # No template for this event → skip gracefully rather than letting the
            # intent fall through silently or raising out of the circulation op.
            catalog = getattr(notifier, 'catalog', None)
            if catalog is not None and not catalog.has(event):
                return intent
            to = self.staff_recipient if event in self._STAFF_EVENTS else recipient
            ctx = self._notice_context(event, recipient, payload)
            notifier.enqueue(event, to, ctx, tenant=self.tenant)
        except Exception:
            # A6 is best-effort: a bad template / queue error must NOT break the
            # circulation operation. The intent is still returned for the caller.
            pass
        return intent

    # ---- device journal seam (рёбра 12.6/12.7) ---------------------------- #
    def _record_device_event(self, device_id, event_name, user_code=None,
                             loan_ref=None, hold_ref=None, message=None):
        """Связать доменное событие книговыдачи с журналом устройства (devices).

        Рёбра INTEGRATION_MAP 12.6 (``device_event.loan_ref → loan``) и 12.7
        (``device_event.hold_ref → hold``): когда операция инициирована станцией/
        устройством самообслуживания (передан ``device_id``) И подключён
        ``devices``-хэндл (:class:`access.devices.DeviceService`), после успешной
        операции пишем строку ``device_event`` со ссылкой на выдачу/бронь. Это и
        есть закрытие шва «устройство ↔ книговыдача»: журнал устройства теперь
        ссылается на конкретный ``loan``/``hold`` (а не висит сиротой), а
        circulation остаётся источником истины по выдаче.

        Best-effort и полностью изолирован (как ``catalog=`` / ``notifications=``):
        без ``devices``-хэндла или без ``device_id`` — no-op (back-compat); любая
        ошибка домена устройств НЕ роняет операцию книговыдачи. Возвращает id
        строки ``device_event`` либо ``None``.
        """
        if self.devices is None or device_id is None:
            return None
        record = getattr(self.devices, 'record_event', None)
        if record is None:
            return None
        try:
            return record(device_id, event_name=event_name, message=message,
                          user_code=user_code, loan_ref=loan_ref, hold_ref=hold_ref)
        except Exception:
            return None  # device journal is best-effort; the circ op still stands

    # ---- PAY ledger seam (ребро 3.3) -------------------------------------- #
    def _post_pay_charge(self, reader, amount, kind, ref=None):
        """Проводка НАЧИСЛЕНИЯ (штраф/возмещение) в PAY-леджер (ребро 3.3).

        Best-effort и изолирован (как ``catalog=``/``notifications=``/``devices=``):
        без ``pay``-хендла или при нулевой сумме — no-op (back-compat); ошибка
        леджера НЕ роняет операцию книговыдачи. Возвращает строку проводки/None."""
        if self.pay is None or not amount or amount <= 0:
            return None
        post = getattr(self.pay, 'post_charge', None)
        if post is None:
            return None
        try:
            return post(reader, amount, kind, ref=ref,
                        currency=self.policy['fine']['currency'])
        except Exception:
            return None  # PAY is best-effort; the circ op still stands

    def _post_pay_payment(self, reader, amount, ref=None):
        """Проводка ПЛАТЕЖА в PAY-леджер (ребро 3.3). Best-effort/опционально."""
        if self.pay is None or not amount or amount <= 0:
            return None
        post = getattr(self.pay, 'post_payment', None)
        if post is None:
            return None
        try:
            return post(reader, amount, ref=ref,
                        currency=self.policy['fine']['currency'])
        except Exception:
            return None

    def _catalog_price(self, item):
        """Цена замены экземпляра из каталога **910^E** (ребро 3.3).

        Резолвит экземпляр ``item`` (910^b) в каталоге и читает подполе ``^E``
        (цена). ``None``, если каталог не подключён / экземпляр не найден / цена
        пуста-нечисловая. Чисто читающая, best-effort (никогда не бросает)."""
        if self.catalog is None:
            return None
        try:
            found = self.catalog.find_exemplar(self.catalog_db, item)
            if found is None:
                return None
            inst = found[2]
            if isinstance(inst, dict):
                raw = inst.get('e') or inst.get('E')
                if raw:
                    return float(str(raw).replace(',', '.'))
        except Exception:
            return None
        return None

    # ---- catalog 910^A write-back (edges 2.1/2.2) ------------------------- #
    def _flip_catalog_status(self, item, status):
        """Reflect a loan-state change into the catalog exemplar's ``910^A``.

        Resolves ``item`` (903/inventory) to the matching ``910`` copy and flips
        its ``910^A`` to ``status`` (``'1'`` issued on checkout, ``'0'`` free on
        return). A no-op (returns None) when no catalog is wired or the copy isn't
        found in the catalog — the engine never depends on the catalog being
        present (back-compat) and degrades gracefully if the copy is unknown.
        Returns the catalog mfn flipped, or None."""
        if self.catalog is None:
            return None
        try:
            return self.catalog.set_exemplar_status(self.catalog_db, item, status)
        except Exception:
            return None  # catalog write is best-effort; the loan still stands

    def catalog_available(self, item):
        """Is ``item`` free per the catalog's ``910^A``? (edge 2.2).

        Returns True/False from the catalog when wired and the copy is known;
        returns None when no catalog is wired or the copy is unknown (caller treats
        None as "no catalog opinion" and falls back to its own loan/queue state)."""
        if self.catalog is None:
            return None
        try:
            if self.catalog.find_exemplar(self.catalog_db, item) is None:
                return None
            return self.catalog.is_available(self.catalog_db, item)
        except Exception:
            return None

    # ---- RDR.40 materialization (ребро 2.4) ------------------------------- #
    def _resolve_exemplar40(self, item):
        """Достать из каталога подполя поля 40, привязанные к экземпляру ``item``.

        Ребро 2.4: при выдаче формат ``RQSTRDR.pft`` строит RDR.40 из заказа и
        записи ЭК. У нас ``loan.item`` = инвентарный номер (910^b); каталог по
        нему резолвит запись и отдаёт остальные подполя:

          * ``^A`` = 903 шифр документа (= ``I=`` в ЭК),
          * ``^H`` = 910^H штрих-код,
          * ``^K`` = 910^D место хранения,
          * ``^C`` = brief (краткое описание).

        Возвращает dict с найденными подполями (отсутствующие — пустые). Когда
        каталог не подключён или экземпляр в нём не найден — отдаёт пустой
        результат: поле 40 материализуется из loan-модели и без каталога
        (back-compat), просто без обогащения из ЭК. Чисто читающая операция.
        """
        out = {'A': '', 'H': '', 'K': '', 'C': ''}
        if self.catalog is None:
            return out
        try:
            found = self.catalog.find_exemplar(self.catalog_db, item)
            if found is None:
                return out
            mfn, _idx, inst = found
            # подполя 910 экземпляра (^H штрих-код, ^D место хранения)
            if isinstance(inst, dict):
                out['H'] = str(inst.get('h') or inst.get('H') or '')
                out['K'] = str(inst.get('d') or inst.get('D') or '')
            # 903 шифр документа + brief — из полной записи каталога
            record = self.catalog.get(self.catalog_db, mfn)
            if record is not None:
                out['A'] = self._first_903(record)
            try:
                out['C'] = self.catalog.brief(self.catalog_db, mfn) or ''
            except Exception:
                out['C'] = ''
        except Exception:
            return {'A': '', 'H': '', 'K': '', 'C': ''}
        return out

    @staticmethod
    def _first_903(record):
        """Значение поля 903 (шифр документа) из записи каталога, или ''.

        903 — целое поле (не подполя). Поддерживает обе формы хранения: строку
        и dict-инстанс (``''``/``value``/конкатенация подполей)."""
        raw = record.get('903') if record else None
        if raw is None:
            return ''
        if isinstance(raw, list):
            raw = raw[0] if raw else ''
        if isinstance(raw, dict):
            return str(raw.get('') or raw.get('value')
                       or ''.join(str(v) for v in raw.values()))
        return str(raw)

    # ---- order ↔ catalog record resolve (ребро 2.3) ----------------------- #
    def resolve_order_record(self, item_or_shifr, catalog_db=None):
        """Резолвить запись каталога для заказа/выдачи — ребро 2.3 (903 ↔ ``I=``).

        Заказ RQST привязан к записи ЭК по **шифру** ``903`` = ``I=`` в каталоге
        (``DBNPREFSHIFR=I=``, DB_CIRCULATION §8 «RQST → IBIS»), а не только по
        инвентарному номеру ``910^b``. Этот метод замыкает оба пути резолва в один
        контракт и возвращает ``mfn`` записи каталога (или ``None``):

          1. **по шифру 903** — поиск каталога по инвертированному префиксу
             ``I=`` (``catalog.search(db, 'I=<шифр>')``); берётся первый
             найденный mfn. Это «правильный» путь заказа: ``loan.item`` /
             переданный аргумент трактуется как шифр документа.
          2. **по инв.№ 910^b** (fallback, НЕ ломаем существующий резолв) —
             если по шифру не нашлось, пробуем ``catalog.find_exemplar(db, item)``
             (как в ``_resolve_exemplar40`` / ``_flip_catalog_status``): аргумент
             трактуется как 910^b, возвращается mfn его записи.

        ``catalog_db`` — имя БД ЭК (по умолчанию ``self.catalog_db``). Когда каталог
        не подключён — ``None`` (движок остаётся автономным, back-compat: заказ
        живёт по строке-шифру без записи каталога). Любая ошибка каталога
        деградирует в ``None`` — резолв не должен ронять операцию выдачи.
        Чисто читающая операция (поиск/чтение, без записи).
        """
        if self.catalog is None:
            return None
        db = catalog_db or self.catalog_db
        key = '' if item_or_shifr is None else str(item_or_shifr).strip()
        if not key:
            return None
        # 1) по шифру 903 через инвертированный индекс I= (основной путь заказа).
        try:
            res = self.catalog.search(db, 'I=' + key, limit=1)
            items = (res or {}).get('items') or []
            if items:
                return items[0].get('mfn')
        except Exception:
            pass  # поиск-резолв best-effort — падаем на резолв по инв.№
        # 2) fallback по инв.№ 910^b (существующий путь — не ломаем его).
        try:
            found = self.catalog.find_exemplar(db, key)
            if found is not None:
                return found[0]
        except Exception:
            pass
        return None

    # ---- reservstatus (RQST 910^A 0–4) ↔ hold.status (ребро 2.6) ----------- #
    @staticmethod
    def resolve_hold_status_in(reservstatus):
        """Код брони RQST ``910^A`` (``reservstatus.mnu`` 0–4) → наш ``hold.status``.

        Ребро 2.6 / recon #CIRC-06: входной код брони из RQST переводится в наш
        enum статусов брони (см. :data:`RESERVSTATUS_TO_HOLD`). Принимает строку
        или число (``0``/``'0'``). Неизвестный/пустой код → ``None`` (нечего
        отображать). Не путать со статусом ЭКЗЕМПЛЯРА ``ste.mnu`` — это разные
        кодировки одного подполя в разных БД."""
        if reservstatus is None:
            return None
        return RESERVSTATUS_TO_HOLD.get(str(reservstatus).strip())

    @staticmethod
    def hold_status_to_reservstatus(status):
        """Наш ``hold.status`` → код брони RQST ``910^A`` (``reservstatus.mnu``).

        Обратное отображение ребра 2.6 (см. :data:`HOLD_TO_RESERVSTATUS`).
        ``expired`` отображается в каноничный ``'3'`` (возврат на МХР); ``cancelled``
        — в ``None`` (в `reservstatus.mnu` отдельного кода нет: отменённая бронь
        просто исчезает из транзитной RQST). Неизвестный enum → ``None``."""
        if status is None:
            return None
        return HOLD_TO_RESERVSTATUS.get(str(status).strip())

    def loan_field40(self, loan):
        """Материализовать одну выдачу (``loan``) в структуру **поля 40 RDR**.

        Ребро 2.4 — ДОП. представление поверх текущей loan-модели (не меняет
        колонки/сценарии). Маппинг подполей (DB_CIRCULATION §3 «развёртка поля
        40», §5 модель циркуляции, §8 связи):

          | ^x | смысл                       | источник                       |
          |----|-----------------------------|--------------------------------|
          | ^A | шифр документа              | 903 (резолв ЭК по инв.№)       |
          | ^B | инвентарный номер           | 910^B = ``loan.item``          |
          | ^H | штрих-код                   | 910^H (резолв ЭК)              |
          | ^K | место хранения экземпляра   | 910^D (резолв ЭК)              |
          | ^D | дата выдачи                 | 41 = ``loan.checked_out_at``   |
          | ^E | дата планового возврата     | 42 = ``loan.due``              |
          | ^F | дата факт. возврата / долг  | ``******`` на руках, иначе дата|
          | ^G | имя БД каталога             | ``catalog_db``                 |
          | ^C | краткое описание (brief)    | резолв ЭК                      |
          | ^U | признак утерянной книги     | ``'1'`` при ``lost``           |

        ``^F``: пока на руках/в долгу — маркер ``******`` (FST ``DOLG=``); после
        возврата — дата фактического возврата (``loan.returned_at``). Даты —
        epoch-секунды (как и весь движок); форматирование в ГГГГММДД оставлено
        слою представления.
        """
        ex = self._resolve_exemplar40(loan['item'])
        f40 = {
            'A': ex['A'],                       # 903 шифр
            'B': str(loan['item']),             # 910^B инв.№
            'H': ex['H'],                       # 910^H штрих-код
            'K': ex['K'],                       # 910^D место хранения
            'D': loan['checked_out_at'],        # 41 дата выдачи
            'E': loan['due'],                   # 42 срок
            'G': self.catalog_db,               # имя БД ЭК
            'C': ex['C'],                       # brief
        }
        # ^F — дата факт. возврата либо маркер долга/«на руках».
        if loan['returned']:
            f40['F'] = loan.get('returned_at')
        else:
            f40['F'] = DEBT_MARKER
        # ^U — утерянная книга (HU=).
        if loan.get('lost_status') == 'lost':
            f40['U'] = '1'
        return f40

    def reader_field40(self, reader_id, include_returned=False):
        """Поле 40 читателя как список инстансов (повторяющееся поле, RDR §3).

        По умолчанию — только выдачи «на руках» (``40^F='******'``), как в
        формуляре RDR. ``include_returned=True`` добавляет возвращённые (для
        полного формуляра). Каждый элемент — dict подполей (см.
        :meth:`loan_field40`)."""
        rows = (self.store.loans_on_hand(reader_id) if not include_returned
                else self.store.reader_loans(reader_id))
        return [self.loan_field40(ln) for ln in rows]

    # ---- checkout (§2 debtor gate + §5 limits) ---------------------------- #
    def checkout(self, reader_id, item, today, item_kind=None, item_price=None,
                 staff_override=False, override_grant=False, device_id=None):
        """Lend ``item`` to ``reader_id``. Enforces limits + the debtor gate.

        ``staff_override`` lets a librarian lend over a deny — but only when the
        override is actually authorised (``override_grant=True``, the
        ``circ.lend.override_debt`` / ``circ.lend.override_limit`` right). An
        unauthorised override is ignored (the deny stands).

        Returns a :class:`Decision`; on ALLOW ``computed['loan']`` is the new loan.
        """
        reader = self.store.get_reader(reader_id)
        if reader is None:
            return Decision(DENY, ['unknown_reader'])

        category = reader['category']
        limits = category_limits(self.policy, category)
        reasons = []

        # §2 debtor self-service gate (rule A): a hard debtor is denied.
        level = debt_level(self.store, self.policy, reader_id, today)
        if level == 'hard' and self.policy['debt']['reader_block_on_hard']:
            reasons.append('reader_has_debt')

        # §5 limits: max_books, or max_dolg_books when in debt.
        on_hand = self.store.count_on_hand(reader_id)
        cap = limits['max_dolg_books'] if level != 'none' else limits['max_books']
        if on_hand >= cap:
            reasons.append('limit_exceeded')

        if reader['blocked']:
            reasons.append('reader_blocked')

        if reasons:
            # Only the debt/limit reasons are override-able by authorised staff.
            overridable = set(reasons) <= {'reader_has_debt', 'limit_exceeded'}
            authorised = staff_override and override_grant
            if overridable and authorised:
                pass  # rule B — staff override (would be journalled by 152-ФЗ layer)
            elif overridable and staff_override and not override_grant:
                return Decision(DENY, reasons + ['override_unauthorised'])
            elif overridable:
                return Decision(REQUIRE_OVERRIDE, reasons)
            else:
                return Decision(DENY, reasons)

        due = today + limits['max_return_days'] * SECONDS_PER_DAY
        loan = self.store.add_loan(reader_id, item, due, today,
                                   item_kind=item_kind, item_price=item_price)
        # Edge 2.1: reflect the issue into the catalog exemplar (910^A 0→1).
        cat_mfn = self._flip_catalog_status(item, '1')  # EXEMPLAR_ISSUED
        computed = {'loan': loan, 'due': due, 'override': bool(reasons)}
        if cat_mfn is not None:
            computed['catalog_mfn'] = cat_mfn
            computed['exemplar_status'] = '1'
        # Ребро 12.6: связать журнал устройства с новой выдачей (loan_ref).
        dev_ev = self._record_device_event(device_id, 'loan_checkout',
                                           user_code=reader_id, loan_ref=loan['id'])
        if dev_ev is not None:
            computed['device_event'] = dev_ev
        return Decision(ALLOW, [], computed)

    # ---- renew (§1 holds-block-renewal + cap) ----------------------------- #
    def renew(self, loan_id, today, staff_override=False, override_grant=False,
              device_id=None):
        """Renew a loan. Blocks on an active hold (holds-block-renewal) and on the
        renewal cap; ``staff_override`` (right ``circ.renew.override_hold``) lets a
        librarian renew past a hold but never past the cap. When a ``devices`` handle
        + ``device_id`` are wired, also journals a ``device_event`` (ребро 12.6).
        """
        loan = self.store.get_loan(loan_id)
        if loan is None:
            return Decision(DENY, ['unknown_loan'])
        if loan['returned']:
            return Decision(DENY, ['loan_closed'])

        reader = self.store.get_reader(loan['reader'])
        category = reader['category'] if reader else '_DEFAULT'
        limits = category_limits(self.policy, category)
        reasons = []

        # §1 renew cap — never override-able.
        max_prolong = limits['max_prolong']
        if loan['renewals'] >= max_prolong:
            reasons.append('max_prolong_reached')

        # §1.2 renewable flag (reading room / rare fund) — never override-able here.
        if limits['max_return_days'] <= 0:
            reasons.append('not_renewable')

        # §1.3 holds-block-renewal.
        queue = self.store.active_holds(loan['item'])
        queue_len = len(queue)
        mode = self.policy['renewal']['holds_block_renewal']
        hold_blocks = False
        if queue_len > 0:
            if mode == 'block':
                hold_blocks = True
            elif mode == 'threshold':
                if queue_len > self.policy['renewal']['hold_block_threshold']:
                    hold_blocks = True
            # 'allow' → never blocks
        if hold_blocks:
            reasons.append('hold_exists')

        # §1.2 debtor blocks renewal too (self-service gate).
        level = debt_level(self.store, self.policy, loan['reader'], today)
        if level == 'hard' and self.policy['debt']['reader_block_on_hard']:
            reasons.append('reader_has_debt')

        hard_reasons = {'max_prolong_reached', 'not_renewable'}
        if reasons:
            blocking_hard = hard_reasons & set(reasons)
            if blocking_hard:
                return Decision(DENY, reasons)
            # remaining reasons (hold_exists / reader_has_debt) are override-able
            authorised = staff_override and override_grant
            if authorised:
                pass  # rule override (journalled by 152-ФЗ layer)
            elif staff_override and not override_grant:
                return Decision(DENY, reasons + ['override_unauthorised'])
            else:
                return Decision(REQUIRE_OVERRIDE, reasons)

        new_due = today + limits['max_return_days'] * SECONDS_PER_DAY
        self.store.bump_renewal(loan_id, new_due)
        updated = self.store.get_loan(loan_id)
        ev = self._emit('renewal_confirmed', loan['reader'],
                        {'ref': loan_id, 'item': loan['item'], 'due': new_due})
        dev_ev = self._record_device_event(device_id, 'loan_renew',
                                           user_code=loan['reader'], loan_ref=loan_id)
        computed = {'loan': updated, 'due': new_due}
        if dev_ev is not None:
            computed['device_event'] = dev_ev
        return Decision(ALLOW, [], computed, [ev])

    # ---- return (§3.5 clear marker + §6 trigger next hold) ---------------- #
    def return_item(self, loan_id, today, device_id=None):
        """Return a loan. Marks it returned, fixes any accrued fine (assessment →
        charged), and — if a queue exists on the item — hands it to the head
        (``hold_ready`` + shelf TTL), holds-aware (§6.5). When a ``devices`` handle
        + ``device_id`` are wired (станция возврата), also journals a
        ``device_event`` linked to the loan (ребро 12.6).

        Returns a :class:`Decision` (always ALLOW for an open loan) whose
        ``computed`` reports ``fine_charged`` and ``hold_ready`` and whose
        ``events`` carries the A6 intents.
        """
        loan = self.store.get_loan(loan_id)
        if loan is None:
            return Decision(DENY, ['unknown_loan'])
        if loan['returned']:
            return Decision(DENY, ['already_returned'])

        events = []
        computed = {}

        # §3.3 assessment — fix any accrued overdue fine into a charge at return.
        self.accrue_fines(today, reader_id=loan['reader'])
        fine = self.store.get_fine(loan_id, 'fine_overdue')
        if fine and fine['status'] == 'accrued' and fine['amount'] > 0:
            self.store.set_fine_status(fine['id'], 'charged')
            computed['fine_charged'] = fine['amount']
            events.append(self._emit('fine_charged', loan['reader'],
                          {'ref': loan_id, 'amount': fine['amount'],
                           'currency': self.policy['fine']['currency']}))
            # Ребро 3.3: проводка штрафа в кассу PAY при фиксации на возврате.
            self._post_pay_charge(loan['reader'], fine['amount'], 'fine_overdue', loan_id)

        # ws3 op: clear 40^F (the return gesture closes the loan).
        self.store.mark_returned(loan_id, today)

        # Ребро 2.5: opt-in перенос завершённой выдачи в архив RDR_ARH (152-ФЗ
        # ретенция) — В ДОПОЛНЕНИЕ к ``returned=1`` (флаг off ⇒ как раньше, без
        # архива). Архивируется пост-возвратное состояние выдачи (40^F = дата).
        if self.archive_on_return:
            closed = self.store.get_loan(loan_id)
            arh = self.store.archive_loan(closed, returned_at=today,
                                          archived_at=today)
            if arh is not None:
                computed['archived'] = arh['id']

        # Edge 2.2: reflect the return into the catalog exemplar (910^A 1→0 free).
        # The physical copy is back on the desk; circulation's hold queue (below)
        # is the logical reservation layer, kept separate from the catalog flag.
        cat_mfn = self._flip_catalog_status(loan['item'], '0')  # EXEMPLAR_FREE
        if cat_mfn is not None:
            computed['catalog_mfn'] = cat_mfn
            computed['exemplar_status'] = '0'

        # §6.5 holds-aware: freed item goes to the queue head, not the free shelf.
        if self.policy['hold']['return_to_reservable']:
            queue = self.store.active_holds(loan['item'])
            head = next((h for h in queue if h['status'] == 'queued'), None)
            if head is not None:
                self.store.set_hold_status(head['id'], 'ready', ready_at=today)
                shelf_until = today + self.policy['hold']['hold_shelf_days'] * SECONDS_PER_DAY
                computed['hold_ready'] = head['id']
                events.append(self._emit('hold_ready', head['reader'],
                              {'ref': head['id'], 'item': loan['item'],
                               'hold_until': shelf_until}))

        # Ребро 12.6: связать журнал устройства с возвратом (loan_ref).
        dev_ev = self._record_device_event(device_id, 'loan_return',
                                           user_code=loan['reader'], loan_ref=loan_id)
        if dev_ev is not None:
            computed['device_event'] = dev_ev

        return Decision(ALLOW, [], computed, events)

    # ---- place_hold (§6 FIFO queue position) ------------------------------ #
    def place_hold(self, reader_id, item, today, device_id=None):
        """Place a hold; returns ALLOW with ``computed['position']`` (1-based FIFO).

        If the item is free (no on-hand loan, no queue) the hold is created and
        immediately ``ready`` at position 1. When a ``devices`` handle + ``device_id``
        are wired (станция/умная полка), also journals a ``device_event`` linked to
        the hold (ребро 12.7).
        """
        reader = self.store.get_reader(reader_id)
        if reader is None:
            return Decision(DENY, ['unknown_reader'])

        # A reader already in this item's queue keeps their place (no double-hold).
        existing = [h for h in self.store.active_holds(item)
                    if h['reader'] == reader_id]
        if existing:
            pos = self.queue_position(item, reader_id)
            return Decision(ALLOW, ['already_queued'],
                            {'hold': existing[0], 'position': pos})

        hold = self.store.add_hold(reader_id, item, today)
        # If nobody holds the item and the queue (besides us) is empty → ready now.
        item_on_loan = self.store._conn().execute(  # noqa: SLF001 (own store)
            'SELECT COUNT(*) AS n FROM loan WHERE item=? AND returned=0',
            (item,)).fetchone()['n']
        queue = self.store.active_holds(item)
        position = self.queue_position(item, reader_id)
        events = []
        # Edge 2.2: when a catalog is wired, also honour its 910^A availability —
        # a copy circulation thinks is free but the catalog marks issued (status
        # set out-of-band) must NOT be handed out as ready. None ⇒ no catalog
        # opinion, fall back to circulation's own loan/queue state.
        cat_avail = self.catalog_available(item)
        catalog_free = (cat_avail is not False)
        if item_on_loan == 0 and len(queue) == 1 and catalog_free:
            self.store.set_hold_status(hold['id'], 'ready', ready_at=today)
            shelf_until = today + self.policy['hold']['hold_shelf_days'] * SECONDS_PER_DAY
            events.append(self._emit('hold_ready', reader_id,
                          {'ref': hold['id'], 'item': item, 'hold_until': shelf_until}))
        hold = self.store.get_hold(hold['id'])
        # Ребро 12.7: связать журнал устройства с новой бронью (hold_ref).
        dev_ev = self._record_device_event(device_id, 'hold_placed',
                                           user_code=reader_id, hold_ref=hold['id'])
        computed = {'hold': hold, 'position': position}
        if dev_ev is not None:
            computed['device_event'] = dev_ev
        return Decision(ALLOW, [], computed, events)

    def queue_position(self, item, reader_id):
        """1-based FIFO position of ``reader_id`` in ``item``'s queue (0 = absent).

        position = 1 + count(active holds queued strictly earlier) (§6.3, fifo).
        """
        queue = self.store.active_holds(item)  # already FIFO ordered
        for idx, h in enumerate(queue):
            if h['reader'] == reader_id:
                return idx + 1
        return 0

    def cancel_hold(self, hold_id, today, reason='отменена читателем',
                    device_id=None):
        """Reader cancels a hold; frees the item to the next in queue (§6.5).

        Emits ``hold_cancelled`` (A6) to the reader whose hold was dropped. When a
        ``devices`` handle + ``device_id`` are wired (станция самообслуживания),
        also journals a ``device_event`` linked to the hold (ребро 12.7).
        """
        hold = self.store.get_hold(hold_id)
        if hold is None:
            return Decision(DENY, ['unknown_hold'])
        self.store.set_hold_status(hold_id, 'cancelled')
        ev = self._emit('hold_cancelled', hold['reader'],
                        {'ref': hold_id, 'item': hold['item'], 'reason': reason})
        dev_ev = self._record_device_event(device_id, 'hold_cancelled',
                                           user_code=hold['reader'], hold_ref=hold_id)
        computed = {'cancelled': hold_id}
        if dev_ev is not None:
            computed['device_event'] = dev_ev
        return Decision(ALLOW, [], computed, [ev])

    # ---- scan_due (ребро 3.5: срок 40^E → due_soon / overdue) ------------- #
    def scan_due(self, today, due_soon_days=None, reader_id=None):
        """Просканировать сроки возврата и разослать напоминания (ребро 3.5).

        Шов «RDR.40 (40^E срок) → A6 уведомления»: по выдачам «на руках» движок
        эмитит через :meth:`_emit` (и, если подключён A6, ставит в очередь) два
        события:

          * ``overdue``  — выдача просрочена (``due < today``); payload несёт
            ``days_overdue`` (целые дни просрочки, ≥1);
          * ``due_soon`` — срок близок (``today ≤ due ≤ today + окно``); payload
            несёт ``days_left`` (целые дни до срока, ≥0).

        ``due_soon_days`` — ширина окна «скоро» в днях (по умолчанию из политики
        ``reminder.due_soon_days``); ``reader_id`` ограничивает скан одним
        читателем (точечное напоминание из ЛК/формуляра).

        Идемпотентность напоминаний — через A6 dedup-ключ с **дневным бакетом**
        ``<event>|<loan>|<YYYY-MM-DD>``: в пределах одних суток повторный скан НЕ
        задваивает уведомление (тот же ключ → dedup), но на следующий день
        читатель получит напоминание снова (новый ключ) — ровно semantics
        «ежедневное напоминание о сроке». Без A6-хэндла движок остаётся
        автономным: события только возвращаются интентами (back-compat).

        Возвращает :class:`Decision` (всегда ALLOW): ``computed`` =
        ``{'due_soon': [loan_id, …], 'overdue': [loan_id, …]}``, ``events`` —
        список интентов.
        """
        window = (self.policy.get('reminder', {}).get('due_soon_days', 3)
                  if due_soon_days is None else due_soon_days)
        window_end = today + max(0, int(window)) * SECONDS_PER_DAY
        events = []
        due_soon_ids = []
        overdue_ids = []

        # overdue — просроченные на руках (due < today).
        for ln in self.store.open_overdue_loans(today, grace_days=0):
            if reader_id is not None and ln['reader'] != reader_id:
                continue
            days_overdue = max(1, int((today - ln['due']) // SECONDS_PER_DAY))
            overdue_ids.append(ln['id'])
            events.append(self._emit('overdue', ln['reader'], {
                'ref': ln['id'], 'item': ln['item'], 'due': ln['due'],
                'days_overdue': days_overdue,
                'dedup_key': 'overdue|%s|%s' % (ln['id'], self._fmt_date(today)),
            }))

        # due_soon — срок в окне [today, today+window], ещё не просрочен.
        for ln in self.store.due_soon_loans(today, window_end):
            if reader_id is not None and ln['reader'] != reader_id:
                continue
            days_left = max(0, int((ln['due'] - today) // SECONDS_PER_DAY))
            due_soon_ids.append(ln['id'])
            events.append(self._emit('due_soon', ln['reader'], {
                'ref': ln['id'], 'item': ln['item'], 'due': ln['due'],
                'days_left': days_left,
                'dedup_key': 'due_soon|%s|%s' % (ln['id'], self._fmt_date(today)),
            }))

        return Decision(ALLOW, [],
                        {'due_soon': due_soon_ids, 'overdue': overdue_ids}, events)

    # ---- accrue_fines (§3.2 formula) -------------------------------------- #
    def accrue_fines(self, today, reader_id=None):
        """Daily accrual: ``min(fine_per_day × billable_days, fine_cap)`` (§3.2).

        Scans open overdue loans (optionally a single reader), computes the
        accrued fine after ``overdue_grace_days``, and upserts the fine row. A
        zero rate ⇒ fine-free (no row). Idempotent per ``(loan, day)`` because the
        amount is recomputed from ``today`` and stored on the single per-loan row
        (re-running with the same ``today`` yields the same amount, no doubling).

        Returns a list of ``{'loan','reader','amount','days'}`` dicts for the
        loans that accrued a positive fine.
        """
        grace = self.policy['fine']['overdue_grace_days']
        cap = self.policy['fine']['fine_cap']
        results = []
        for ln in self.store.open_overdue_loans(today, grace_days=0):
            if reader_id is not None and ln['reader'] != reader_id:
                continue
            reader = self.store.get_reader(ln['reader'])
            category = reader['category'] if reader else '_DEFAULT'
            rate = fine_per_day(self.policy, category, ln['item_kind'])
            if rate <= 0:
                continue  # fine-free
            days_overdue = int((today - ln['due']) // SECONDS_PER_DAY)
            billable_days = max(0, days_overdue - grace)
            if billable_days <= 0:
                continue
            amount = min(rate * billable_days, cap)
            if amount <= 0:
                continue
            self.store.upsert_fine(ln['reader'], ln['id'], amount,
                                   kind='fine_overdue', status='accrued',
                                   accrued_through=today)
            results.append({'loan': ln['id'], 'reader': ln['reader'],
                            'amount': amount, 'days': billable_days})
        return results

    def waive_fine(self, loan_id, override_grant=False):
        """Waive (zero) an accrued/charged overdue fine — right ``circ.fine.waive``.

        Returns ALLOW only when authorised (``override_grant=True``).
        """
        if not override_grant:
            return Decision(DENY, ['waive_unauthorised'])
        fine = self.store.get_fine(loan_id, 'fine_overdue')
        if fine is None:
            return Decision(DENY, ['no_fine'])
        self.store.set_fine_status(fine['id'], 'waived')
        return Decision(ALLOW, [], {'waived': loan_id})

    def pay_fine(self, loan_id, kind='fine_overdue'):
        """Apply an incoming ``payment_received`` (§3.5): mark the fine paid.

        Clearing ``40^F`` (the on-hand marker) is *separate* — it happens only on
        physical return, not on payment (§3.5). Returns the recomputed debt-clear.
        """
        fine = self.store.get_fine(loan_id, kind)
        if fine is None:
            return Decision(DENY, ['no_fine'])
        self.store.set_fine_status(fine['id'], 'paid')
        # Ребро 3.3: проводка платежа в кассу PAY.
        self._post_pay_payment(fine['reader'], fine['amount'], loan_id)
        ev = self._emit('fine_paid', fine['reader'],
                        {'ref': loan_id, 'amount': fine['amount']})
        return Decision(ALLOW, [], {'paid': loan_id}, [ev])

    # ---- mark_lost (§4 candidate → confirm) ------------------------------- #
    def scan_lost_candidates(self, today):
        """Mark over-overdue loans as ``lost_candidate`` + a ``staff_alert`` (§4.1).

        Over ``lost_after_days`` past due ⇒ candidate (NOT an auto-debt). Returns
        the candidate loan ids + their staff-alert event intents.
        """
        lost_after = self.policy['lost']['lost_after_days']
        cutoff = today - lost_after * SECONDS_PER_DAY
        flagged = []
        events = []
        for ln in self.store.open_overdue_loans(today, grace_days=0):
            if ln['lost_status'] != 'none':
                continue
            if ln['due'] < cutoff:
                self.store.set_lost_status(ln['id'], 'lost_candidate')
                flagged.append(ln['id'])
                events.append(self._emit('staff_alert', ln['reader'],
                              {'ref': ln['id'], 'item': ln['item'],
                               'kind': 'lost_candidate'}))
        return Decision(ALLOW, [], {'candidates': flagged}, events)

    def mark_lost(self, loan_id, today, confirm=False, override_grant=False,
                  ksu_disp_no=None):
        """Lost workflow (§4): without ``confirm`` ⇒ ``lost_candidate`` (fail-safe,
        no auto-debt); with ``confirm`` ⇒ ``lost`` + replacement charge.

        Confirm requires authorisation (``override_grant``, right
        ``circ.lost.confirm``). Replacement = ``910^E × multiplier + handling_fee``
        with a fallback when the item price is empty/0. ``lost_supersedes_fine``
        waives the accrued overdue fine so the reader isn't billed twice (§4.2).
        Emits ``lost_confirmed`` (→ ws2 write-off signal) + ``fine_charged`` (A6).

        Книговыдача→Комплектование (INTEGRATION_MAP ребро 5.2): when an
        ``acquisition`` handle is wired, a confirmed loss is also reflected into the
        acquisition КСУ выбытия — the lost copy is written off as выбытие
        (``record_disposal``). ``ksu_disp_no`` is the акт списания number to book it
        under (defaults to a per-day ``LOST-<YYYY-MM-DD>`` акт). The write-off is
        best-effort: an acquisition error never blocks the loss confirmation.
        """
        loan = self.store.get_loan(loan_id)
        if loan is None:
            return Decision(DENY, ['unknown_loan'])
        if loan['returned']:
            return Decision(DENY, ['loan_closed'])

        if not confirm:
            self.store.set_lost_status(loan_id, 'lost_candidate')
            ev = self._emit('staff_alert', loan['reader'],
                            {'ref': loan_id, 'item': loan['item'],
                             'kind': 'lost_candidate'})
            return Decision(ALLOW, ['lost_candidate'],
                            {'lost_status': 'lost_candidate'}, [ev])

        # confirm → must be authorised (circ.lost.confirm)
        if not override_grant:
            return Decision(DENY, ['lost_confirm_unauthorised'])

        # §4.2 replacement value. Ребро 3.3: если на выдаче ``item_price`` пуст —
        # берём цену замены из каталога **910^E** (а не только из аргумента);
        # затем — дефолт политики как последний fallback.
        price = loan['item_price']
        if not price or price <= 0:
            price = self._catalog_price(loan['item'])
        if not price or price <= 0:
            price = self.policy['lost']['default_replacement_value']
        replacement = (price * self.policy['lost']['multiplier']
                       + self.policy['lost']['handling_fee'])

        self.store.set_lost_status(loan_id, 'lost')

        # §4.2 lost supersedes fine — waive accrued overdue fine.
        if self.policy['lost']['lost_supersedes_fine']:
            of = self.store.get_fine(loan_id, 'fine_overdue')
            if of and of['status'] in ('accrued', 'charged'):
                self.store.set_fine_status(of['id'], 'waived')

        self.store.upsert_fine(loan['reader'], loan_id, replacement,
                               kind='lost_replacement', status='charged')

        # Ребро 3.3: проводка возмещения в кассу PAY (reader-keyed, ``RI=``).
        self._post_pay_charge(loan['reader'], replacement, 'lost_replacement', loan_id)

        # Книговыдача→Комплектование (ребро 5.2): write the lost copy off into the
        # acquisition КСУ выбытия (910^V/^X, статус «списан»). Best-effort.
        disposal = self._record_disposal(loan, today, ksu_disp_no)

        events = [
            self._emit('lost_confirmed', loan['reader'],
                       {'ref': loan_id, 'item': loan['item'], 'price': replacement}),
            self._emit('fine_charged', loan['reader'],
                       {'ref': loan_id, 'amount': replacement,
                        'currency': self.policy['fine']['currency'],
                        'kind': 'lost_replacement'}),
        ]
        computed = {'lost_status': 'lost', 'replacement_value': replacement}
        if disposal is not None:
            computed['disposal'] = disposal
        return Decision(ALLOW, [], computed, events)

    def _record_disposal(self, loan, today, ksu_disp_no=None):
        """Reflect a confirmed loss into the acquisition КСУ выбытия (ребро 5.2).

        When an ``acquisition`` handle is wired, write the lost copy off as выбытие
        under the акт списания ``ksu_disp_no`` (default ``LOST-<YYYY-MM-DD>``),
        keyed by the loan's item (910^b), reason ``lost``, ref = loan id. Returns
        the disposal row dict, or None when no handle is wired / the write-off
        degrades (the loss confirmation still stands — best-effort, mirrors ToCat).
        """
        if self.acquisition is None:
            return None
        record = getattr(self.acquisition, 'record_disposal', None)
        if record is None:
            return None
        act = ksu_disp_no or ('LOST-' + self._fmt_date(today))
        try:
            return record(loan['item'], act, reason='lost', ref=str(loan['id']))
        except Exception:
            return None  # acquisition write is best-effort; the loss still stands

    # ---- reader as a RECORD (ребро 3.1) ----------------------------------- #
    def reader_record(self, reader_id):
        """Полная запись-профиль читателя (ребро 3.1), а не строка-id.

        Если подключён ``reader_registry`` — вернуть его профиль (билет/ФИО/
        категория/статус/контакты) через duck-typed ``resolve``. Иначе (или если
        в реестре такого читателя нет) — деградирует к базовой строке
        ``reader(id,category,blocked)`` собственного стора. Best-effort: никогда
        не бросает (недоступность реестра не роняет книговыдачу)."""
        if self.reader_registry is not None:
            resolve = getattr(self.reader_registry, 'resolve', None)
            if resolve is not None:
                try:
                    prof = resolve(reader_id)
                    if prof is not None:
                        return prof
                except Exception:
                    pass
        return self.store.get_reader(reader_id)

    # ---- debt summary (GET /api/circ/reader/{id}/debt) -------------------- #
    def reader_debt(self, reader_id, today):
        """Debt summary for the reader formulary / ЛК (§8.1)."""
        return {
            'reader': reader_id,
            'debt_level': debt_level(self.store, self.policy, reader_id, today),
            'on_hand': self.store.count_on_hand(reader_id),
            'outstanding': self.store.total_outstanding(reader_id),
            'fines': self.store.outstanding_fines(reader_id),
        }
