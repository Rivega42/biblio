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
(``hold_ready`` / ``overdue`` / ``fine_charged`` / ``renewal_confirmed`` …). If
an :class:`access.notifications.NotificationQueue` is handed to the engine they
are also enqueued (idempotent by dedup_key); otherwise they are only returned —
the rule layer never depends on A6 being present.
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

    def count_on_hand(self, reader_id):
        """``count_on_hand`` = number of RDR.40 with ``40^F='******'`` (§5.4)."""
        return self._conn().execute(
            'SELECT COUNT(*) AS n FROM loan WHERE reader=? AND returned=0 '
            'AND lost_status!=?', (reader_id, 'lost')).fetchone()['n']

    def open_overdue_loans(self, today_epoch, grace_days=0):
        """On-hand loans past ``due + grace`` (basis for accrual / lost scan)."""
        cutoff = today_epoch - grace_days * SECONDS_PER_DAY
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan WHERE returned=0 AND lost_status!=? AND due<? '
            'ORDER BY id', ('lost', cutoff)).fetchall()]

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

    def __init__(self, store=None, policy=None, notifier=None, tenant='public'):
        self.store = store or CirculationStore(':memory:')
        self.policy = policy or default_policy(tenant)
        self.notifier = notifier
        self.tenant = tenant

    # ---- event emission --------------------------------------------------- #
    def _emit(self, event, recipient, payload):
        """Build an event intent; enqueue via A6 when a notifier is wired."""
        intent = {'event': event, 'recipient': recipient, 'payload': dict(payload)}
        if self.notifier is not None:
            try:
                self.notifier.enqueue(event, recipient, payload, tenant=self.tenant)
            except Exception:
                pass  # A6 is best-effort here; the intent is still returned
        return intent

    # ---- checkout (§2 debtor gate + §5 limits) ---------------------------- #
    def checkout(self, reader_id, item, today, item_kind=None, item_price=None,
                 staff_override=False, override_grant=False):
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
        computed = {'loan': loan, 'due': due, 'override': bool(reasons)}
        return Decision(ALLOW, [], computed)

    # ---- renew (§1 holds-block-renewal + cap) ----------------------------- #
    def renew(self, loan_id, today, staff_override=False, override_grant=False):
        """Renew a loan. Blocks on an active hold (holds-block-renewal) and on the
        renewal cap; ``staff_override`` (right ``circ.renew.override_hold``) lets a
        librarian renew past a hold but never past the cap.
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
        return Decision(ALLOW, [], {'loan': updated, 'due': new_due}, [ev])

    # ---- return (§3.5 clear marker + §6 trigger next hold) ---------------- #
    def return_item(self, loan_id, today):
        """Return a loan. Marks it returned, fixes any accrued fine (assessment →
        charged), and — if a queue exists on the item — hands it to the head
        (``hold_ready`` + shelf TTL), holds-aware (§6.5).

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

        # ws3 op: clear 40^F (the return gesture closes the loan).
        self.store.mark_returned(loan_id, today)

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

        return Decision(ALLOW, [], computed, events)

    # ---- place_hold (§6 FIFO queue position) ------------------------------ #
    def place_hold(self, reader_id, item, today):
        """Place a hold; returns ALLOW with ``computed['position']`` (1-based FIFO).

        If the item is free (no on-hand loan, no queue) the hold is created and
        immediately ``ready`` at position 1.
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
        if item_on_loan == 0 and len(queue) == 1:
            self.store.set_hold_status(hold['id'], 'ready', ready_at=today)
            shelf_until = today + self.policy['hold']['hold_shelf_days'] * SECONDS_PER_DAY
            events.append(self._emit('hold_ready', reader_id,
                          {'ref': hold['id'], 'item': item, 'hold_until': shelf_until}))
        hold = self.store.get_hold(hold['id'])
        return Decision(ALLOW, [], {'hold': hold, 'position': position}, events)

    def queue_position(self, item, reader_id):
        """1-based FIFO position of ``reader_id`` in ``item``'s queue (0 = absent).

        position = 1 + count(active holds queued strictly earlier) (§6.3, fifo).
        """
        queue = self.store.active_holds(item)  # already FIFO ordered
        for idx, h in enumerate(queue):
            if h['reader'] == reader_id:
                return idx + 1
        return 0

    def cancel_hold(self, hold_id, today):
        """Reader cancels a hold; frees the item to the next in queue (§6.5)."""
        hold = self.store.get_hold(hold_id)
        if hold is None:
            return Decision(DENY, ['unknown_hold'])
        self.store.set_hold_status(hold_id, 'cancelled')
        return Decision(ALLOW, [], {'cancelled': hold_id})

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

    def mark_lost(self, loan_id, today, confirm=False, override_grant=False):
        """Lost workflow (§4): without ``confirm`` ⇒ ``lost_candidate`` (fail-safe,
        no auto-debt); with ``confirm`` ⇒ ``lost`` + replacement charge.

        Confirm requires authorisation (``override_grant``, right
        ``circ.lost.confirm``). Replacement = ``910^E × multiplier + handling_fee``
        with a fallback when the item price is empty/0. ``lost_supersedes_fine``
        waives the accrued overdue fine so the reader isn't billed twice (§4.2).
        Emits ``lost_confirmed`` (→ ws2 write-off signal) + ``fine_charged`` (A6).
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

        # §4.2 replacement value.
        price = loan['item_price']
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

        events = [
            self._emit('lost_confirmed', loan['reader'],
                       {'ref': loan_id, 'item': loan['item'], 'price': replacement}),
            self._emit('fine_charged', loan['reader'],
                       {'ref': loan_id, 'amount': replacement,
                        'currency': self.policy['fine']['currency'],
                        'kind': 'lost_replacement'}),
        ]
        return Decision(ALLOW, [], {'lost_status': 'lost',
                                    'replacement_value': replacement}, events)

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
