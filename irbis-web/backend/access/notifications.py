#!/usr/bin/env python3
"""Reader notification engine — event-driven, multi-channel, idempotent.

Gap A6, epic #188. Implements SPEC_engine_notifications.md, FIRST shippable slice.

What this module is
-------------------
A *self-contained* notification engine that turns circulation/account events
(hold ready, due soon, overdue, fine charged, …) into rendered, deduplicated,
channel-routed messages for a reader. It is deliberately standalone: pure stdlib
+ ``sqlite3`` (dev parity with the rest of the backend, ADR-004), no network I/O.
Channels are abstract — a real e-mail/SMS gateway is plugged in behind the
``Channel`` interface; tests drive it with an in-memory recorder.

The four moving parts
---------------------
  1. ``EventCatalog`` — maps an *event type* (e.g. ``hold_ready``) to its
     ``template`` (subject/body with ``{placeholder}`` slots) and the
     ``default_channels`` fallback order (first-success wins).
  2. ``NotificationQueue`` — a durable sqlite-backed work queue. ``enqueue`` is
     **idempotent** by ``dedup_key`` (UNIQUE) so the same logical event handed in
     twice never double-sends. ``process_once`` claims pending rows, renders the
     template, and attempts the channel chain — marking ``sent`` / ``failed`` and
     bumping the ``attempts`` retry/backoff counter.
  3. Reader **preferences** — a per-reader ``Preferences`` (which channels to use
     for an event, and a global / per-event **opt-out**). Honored at enqueue
     time: opted-out → suppressed (never queued); otherwise the preferred channel
     order overrides the catalog default.
  4. ``Channel`` interface + implementations — ``MemoryChannel`` (records sends,
     for tests), ``EmailChannel`` / ``SmsChannel`` stubs (NO real send; raise or
     record per their ``available`` flag so fallback can be exercised).

Template rendering
------------------
``render`` uses ``access.pft`` when that engine is importable (it formats ИРБИС
PFT field-format expressions); otherwise it falls back to a safe ``str``-based
``{placeholder}`` substitution. The fallback is what runs today since A1/PFT is
not yet built — a missing placeholder is left verbatim rather than raising, so a
template typo degrades gracefully instead of dropping a notification.

Queue / dedup / retry model
---------------------------
``notification(id, tenant, event, recipient, channel, status, dedup_key,
attempts, payload_json, ...)`` with ``UNIQUE(dedup_key)``. ``status`` walks
``pending -> sent`` on success or ``pending -> failed`` once attempts exhaust the
chain; a transient channel error increments ``attempts`` and leaves the row
claimable on the next ``process_once`` (at-least-once, dedup makes the *send*
effectively once per channel). Backoff is advisory: ``next_attempt_at`` is set to
``now + backoff(attempts)`` and respected by the claim query.
"""
import json
import sqlite3
import threading
import time

# --------------------------------------------------------------------------- #
# Template rendering — prefer the real PFT engine (A1) when present, else a
# safe stdlib {placeholder} substitution. Resolved once at import.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - depends on sibling A1 module existing
    from access import pft as _pft  # type: ignore
    _HAVE_PFT = hasattr(_pft, 'format')
except Exception:  # ImportError today; defensive against a half-built module
    _pft = None
    _HAVE_PFT = False


def render(template, payload):
    """Render a template string against ``payload`` (a flat dict).

    Uses ``access.pft.format`` when the PFT engine is importable, else a literal
    ``{key}`` substitution. Unknown placeholders are left verbatim (a template
    typo must not crash the engine or silently drop a notification).
    """
    if template is None:
        return ''
    if _HAVE_PFT:
        try:
            return _pft.format(template, payload)
        except Exception:
            pass  # fall through to the stdlib renderer on any PFT error
    out = template
    for key, val in (payload or {}).items():
        out = out.replace('{%s}' % key, '' if val is None else str(val))
    return out


# --------------------------------------------------------------------------- #
# Channels — abstract interface + a test recorder + non-sending prod stubs.
# --------------------------------------------------------------------------- #
class SendError(Exception):
    """Transient/permanent failure from a channel; engine treats it as a miss."""


class Channel:
    """A delivery surface (email / sms / push / …).

    Subclasses set ``name`` and implement ``send(recipient, subject, body,
    payload)``. ``send`` returns a provider message-id string on success and
    raises :class:`SendError` on failure (so the engine can fall through to the
    next channel in the chain).
    """
    name = 'abstract'

    def send(self, recipient, subject, body, payload):  # pragma: no cover
        raise NotImplementedError


class MemoryChannel(Channel):
    """In-memory recorder for tests. Captures every send; can be forced to fail.

    ``fail`` -> always raises (exercise the fallback chain).
    ``fail_times`` -> raises for the first N attempts then succeeds (exercise the
    retry/attempts counter).
    """

    def __init__(self, name='memory', fail=False, fail_times=0):
        self.name = name
        self.fail = fail
        self.fail_times = fail_times
        self.sent = []          # list of dicts actually delivered
        self.attempts = 0       # total send() invocations (incl. failures)

    def send(self, recipient, subject, body, payload):
        self.attempts += 1
        if self.fail:
            raise SendError('%s: forced failure' % self.name)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise SendError('%s: transient failure' % self.name)
        rec = {'recipient': recipient, 'subject': subject,
               'body': body, 'payload': payload}
        self.sent.append(rec)
        return '%s-%d' % (self.name, len(self.sent))


class EmailChannel(Channel):
    """SMTP stub — NO real network send in this slice.

    ``available=False`` makes it raise (simulating an unconfigured gateway), which
    is how the fallback chain is exercised in prod-shaped wiring. When available it
    records to ``outbox`` exactly like a real adapter would hand off to a relay.
    """
    name = 'email'

    def __init__(self, available=True):
        self.available = available
        self.outbox = []

    def send(self, recipient, subject, body, payload):
        if not self.available:
            raise SendError('email: gateway not configured')
        self.outbox.append({'to': recipient, 'subject': subject, 'body': body})
        return 'email-stub-%d' % len(self.outbox)


class SmsChannel(Channel):
    """SMS gateway stub — NO real send. Mirrors :class:`EmailChannel`."""
    name = 'sms'

    def __init__(self, available=True):
        self.available = available
        self.outbox = []

    def send(self, recipient, subject, body, payload):
        if not self.available:
            raise SendError('sms: gateway not configured')
        self.outbox.append({'to': recipient, 'text': body})
        return 'sms-stub-%d' % len(self.outbox)


# --------------------------------------------------------------------------- #
# Event catalog — event type -> {template, default_channels}.
# --------------------------------------------------------------------------- #
class EventCatalog:
    """Maps reader-account events to their template + default channel chain.

    Seeded with the SPEC event set: the reader-facing hold/loan/fine notices
    (hold_ready / due_soon / overdue / fine_charged / hold_cancelled /
    account_blocked / renewal_confirmed / fine_paid / lost_confirmed) plus the
    staff-facing ``staff_alert`` (write-off candidate). The set must cover every
    event ``CirculationEngine._emit`` raises, or that intent falls through
    silently (no template → never rendered/sent). ``register`` lets a tenant
    add/override an entry. Each entry is ``{'template': {'subject','body'},
    'default_channels': [<name>, ...]}`` — channel *names*, resolved to live
    :class:`Channel` objects at send time.
    """

    DEFAULTS = {
        'hold_ready': {
            'template': {
                'subject': 'Бронь готова: {title}',
                'body': ('Здравствуйте, {reader_name}. Заказанный документ '
                         '«{title}» ожидает вас до {hold_until} в {pickup}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'due_soon': {
            'template': {
                'subject': 'Скоро срок возврата: {title}',
                'body': ('Напоминаем: «{title}» нужно вернуть до {due_date}. '
                         'Осталось дней: {days_left}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'overdue': {
            'template': {
                'subject': 'Просрочен возврат: {title}',
                'body': ('Документ «{title}» просрочен на {days_overdue} дн. '
                         'Пожалуйста, верните его как можно скорее.'),
            },
            'default_channels': ['sms', 'email'],
        },
        'fine_charged': {
            'template': {
                'subject': 'Начислен штраф: {amount} {currency}',
                'body': ('На ваш счёт начислен штраф {amount} {currency} '
                         'за «{title}». Текущая задолженность: {balance}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'hold_cancelled': {
            'template': {
                'subject': 'Бронь отменена: {title}',
                'body': 'Ваша бронь на «{title}» отменена. Причина: {reason}.',
            },
            'default_channels': ['email'],
        },
        'account_blocked': {
            'template': {
                'subject': 'Доступ к обслуживанию приостановлен',
                'body': ('Здравствуйте, {reader_name}. Ваш формуляр '
                         'заблокирован. Причина: {reason}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'renewal_confirmed': {
            'template': {
                'subject': 'Срок продлён: {title}',
                'body': ('Здравствуйте, {reader_name}. Срок пользования '
                         'документом «{title}» продлён до {due_date}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'fine_paid': {
            'template': {
                'subject': 'Оплата принята: {amount} {currency}',
                'body': ('Здравствуйте, {reader_name}. Оплата штрафа '
                         '{amount} {currency} принята, спасибо. '
                         'Текущая задолженность: {balance}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        'lost_confirmed': {
            'template': {
                'subject': 'Документ признан утерянным: {title}',
                'body': ('Здравствуйте, {reader_name}. Документ «{title}» '
                         'признан утерянным. К возмещению начислена стоимость '
                         'замены: {amount} {currency}.'),
            },
            'default_channels': ['email', 'sms'],
        },
        # Addressed to library staff, not the reader: a freed-shelf / write-off
        # candidate needs a librarian to action it. E-mail only (no reader SMS).
        'staff_alert': {
            'template': {
                'subject': 'Служебное: кандидат на списание — {title}',
                'body': ('Служебное уведомление. Документ «{title}» (формуляр '
                         'читателя {reader_name}) числится в просрочке сверх '
                         'допустимого срока и помечен как кандидат на списание. '
                         'Требуется проверка формуляра.'),
            },
            'default_channels': ['email'],
        },
    }

    def __init__(self, entries=None):
        # deep-ish copy so a register() never mutates the class-level DEFAULTS
        src = entries if entries is not None else self.DEFAULTS
        self._entries = {ev: dict(spec) for ev, spec in src.items()}

    def register(self, event, template, default_channels):
        self._entries[event] = {'template': dict(template),
                                 'default_channels': list(default_channels)}

    def has(self, event):
        return event in self._entries

    def template(self, event):
        return self._entries[event]['template']

    def default_channels(self, event):
        return list(self._entries[event]['default_channels'])

    def events(self):
        return sorted(self._entries)


# --------------------------------------------------------------------------- #
# Reader preferences — channel order per event + opt-out.
# --------------------------------------------------------------------------- #
class Preferences:
    """Per-reader channel preferences and opt-outs.

    * ``channels`` — optional ``{event: [channel_name, ...]}`` overriding the
      catalog default for that event (and the global default below).
    * ``default_channels`` — optional reader-wide channel order applied to events
      with no per-event entry.
    * ``opted_out`` — a set of events the reader refuses; ``'*'`` opts out of
      everything. ``is_opted_out(event)`` honours both.

    ``resolve(event, catalog)`` returns the effective channel-name chain:
    per-event pref → reader default → catalog default.
    """

    def __init__(self, channels=None, default_channels=None, opted_out=None):
        self.channels = dict(channels or {})
        self.default_channels = list(default_channels) if default_channels else None
        self.opted_out = set(opted_out or ())

    def is_opted_out(self, event):
        return '*' in self.opted_out or event in self.opted_out

    def resolve(self, event, catalog):
        if event in self.channels:
            return list(self.channels[event])
        if self.default_channels:
            return list(self.default_channels)
        return catalog.default_channels(event)


# Convenience: a reader who takes everything on the catalog defaults.
DEFAULT_PREFERENCES = Preferences()


# --------------------------------------------------------------------------- #
# Queue — durable sqlite store with idempotent enqueue + claim/process.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS notification (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant TEXT NOT NULL DEFAULT 'public',
  event TEXT NOT NULL,
  recipient TEXT NOT NULL,
  channel TEXT,                 -- channel that finally delivered (NULL until sent)
  status TEXT NOT NULL DEFAULT 'pending'
         CHECK (status IN ('pending','sent','failed','suppressed')),
  dedup_key TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}',
  channels_json TEXT NOT NULL DEFAULT '[]',  -- resolved channel-name chain
  last_error TEXT,
  next_attempt_at REAL NOT NULL DEFAULT 0,
  read_at REAL,                 -- reader inbox: NULL=unread, epoch=when marked read (#222)
  created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now')),
  UNIQUE (dedup_key)
);
CREATE INDEX IF NOT EXISTS notification_claim_idx
  ON notification(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS notification_inbox_idx
  ON notification(recipient, read_at);
"""

# attempts -> seconds of advisory backoff before the row is reclaimable.
_BACKOFF = [0, 60, 300, 900, 3600]
MAX_ATTEMPTS = 5


def backoff_seconds(attempts):
    """Advisory backoff for the Nth attempt (capped at the last bucket)."""
    if attempts < 0:
        attempts = 0
    return _BACKOFF[min(attempts, len(_BACKOFF) - 1)]


def make_dedup_key(tenant, event, recipient, payload):
    """Deterministic idempotency key.

    A caller may pass an explicit ``dedup_key`` in the payload (e.g. a circulation
    transaction id) — that wins. Otherwise we derive a stable key from the logical
    identity of the event so the same hold/loan can't notify twice. ``ref`` (a
    domain id such as the hold/loan mfn) is the canonical disambiguator.
    """
    if payload and payload.get('dedup_key'):
        return str(payload['dedup_key'])
    ref = '' if not payload else str(payload.get('ref', ''))
    return '|'.join([tenant, event, str(recipient), ref])


class NotificationQueue:
    """sqlite-backed notification work queue (idempotent enqueue, claim/send).

    ``enqueue`` applies preferences/opt-out and inserts a single ``pending`` row
    keyed by ``dedup_key`` (a duplicate enqueue is a no-op, returning the existing
    row's id). ``process_once`` claims due ``pending`` rows and runs each through
    its resolved channel chain.
    """

    def __init__(self, db_path=':memory:', catalog=None, tenant='public'):
        self.db_path = db_path
        self.catalog = catalog or EventCatalog()
        self.tenant = tenant
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
        # Lazy migration: a persistent queue created before the inbox feature (#222)
        # lacks read_at — add it so the inbox can mark notices read. Idempotent.
        cols = {r[1] for r in c.execute('PRAGMA table_info(notification)').fetchall()}
        if 'read_at' not in cols:
            c.execute('ALTER TABLE notification ADD COLUMN read_at REAL')
        c.execute('CREATE INDEX IF NOT EXISTS notification_inbox_idx '
                  'ON notification(recipient, read_at)')
        c.commit()

    # ---- enqueue (idempotent) -------------------------------------------- #
    def enqueue(self, event, recipient, payload=None, prefs=None, tenant=None):
        """Queue one notification. Idempotent by ``dedup_key``; opt-out aware.

        Returns ``{'id', 'status', 'dedup_key', 'deduped'}``:
          * opted-out  -> a ``suppressed`` row (recorded, never sent),
          * duplicate  -> the existing row, ``deduped=True``, no new insert,
          * otherwise  -> a fresh ``pending`` row.
        """
        if not self.catalog.has(event):
            raise KeyError('unknown event type: %r' % event)
        payload = payload or {}
        prefs = prefs or DEFAULT_PREFERENCES
        tenant = tenant or self.tenant
        dedup_key = make_dedup_key(tenant, event, recipient, payload)
        c = self._conn()

        existing = c.execute(
            'SELECT id, status FROM notification WHERE dedup_key=?',
            (dedup_key,)).fetchone()
        if existing is not None:
            return {'id': existing['id'], 'status': existing['status'],
                    'dedup_key': dedup_key, 'deduped': True}

        if prefs.is_opted_out(event):
            status, channels = 'suppressed', []
        else:
            status = 'pending'
            channels = prefs.resolve(event, self.catalog)

        cur = c.execute(
            'INSERT INTO notification(tenant,event,recipient,status,dedup_key,'
            'payload_json,channels_json) VALUES(?,?,?,?,?,?,?)',
            (tenant, event, recipient, status, dedup_key,
             json.dumps(payload, ensure_ascii=False),
             json.dumps(channels, ensure_ascii=False)))
        c.commit()
        return {'id': cur.lastrowid, 'status': status,
                'dedup_key': dedup_key, 'deduped': False}

    # ---- claim + send ----------------------------------------------------- #
    def _claim_due(self, now, limit):
        c = self._conn()
        return c.execute(
            "SELECT * FROM notification WHERE status='pending' "
            'AND next_attempt_at<=? ORDER BY id LIMIT ?',
            (now, limit)).fetchall()

    def process_once(self, channels, now=None, limit=100):
        """Process up to ``limit`` due pending rows once. Returns a summary dict.

        ``channels`` is ``{name: Channel}``. For each claimed row we render the
        template and walk its resolved channel chain, stopping at the first
        success (records the delivering channel + marks ``sent``). If the whole
        chain misses we bump ``attempts``: under :data:`MAX_ATTEMPTS` the row goes
        back to ``pending`` with an advisory backoff; at the cap it is marked
        ``failed``.
        """
        now = time.time() if now is None else now
        c = self._conn()
        summary = {'processed': 0, 'sent': 0, 'failed': 0, 'retried': 0}

        for row in self._claim_due(now, limit):
            summary['processed'] += 1
            payload = json.loads(row['payload_json'])
            chain = json.loads(row['channels_json'])
            tmpl = self.catalog.template(row['event'])
            subject = render(tmpl.get('subject'), payload)
            body = render(tmpl.get('body'), payload)

            delivered_via = None
            last_error = None
            for cname in chain:
                ch = channels.get(cname)
                if ch is None:
                    last_error = 'no channel %r wired' % cname
                    continue
                try:
                    ch.send(row['recipient'], subject, body, payload)
                    delivered_via = cname
                    break
                except SendError as e:
                    last_error = str(e)
                except Exception as e:  # defensive: any channel bug is a miss
                    last_error = '%s: %s' % (type(e).__name__, e)

            attempts = row['attempts'] + 1
            if delivered_via is not None:
                c.execute(
                    "UPDATE notification SET status='sent', channel=?, "
                    "attempts=?, last_error=NULL, updated_at=? WHERE id=?",
                    (delivered_via, attempts, now, row['id']))
                summary['sent'] += 1
            elif attempts >= MAX_ATTEMPTS:
                c.execute(
                    "UPDATE notification SET status='failed', attempts=?, "
                    'last_error=?, updated_at=? WHERE id=?',
                    (attempts, last_error, now, row['id']))
                summary['failed'] += 1
            else:
                nxt = now + backoff_seconds(attempts)
                c.execute(
                    "UPDATE notification SET status='pending', attempts=?, "
                    'last_error=?, next_attempt_at=?, updated_at=? WHERE id=?',
                    (attempts, last_error, nxt, now, row['id']))
                summary['retried'] += 1
        c.commit()
        return summary

    # ---- introspection ---------------------------------------------------- #
    def get(self, notif_id):
        r = self._conn().execute(
            'SELECT * FROM notification WHERE id=?', (notif_id,)).fetchone()
        return dict(r) if r else None

    def by_status(self, status):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM notification WHERE status=? ORDER BY id',
            (status,)).fetchall()]

    def all(self):
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM notification ORDER BY id').fetchall()]

    def pending_count(self):
        return self._conn().execute(
            "SELECT COUNT(*) AS n FROM notification WHERE status='pending'"
        ).fetchone()['n']

    # ---- reader inbox (#222) — reader-addressable view of dispatched notices ----
    # A reader sees the notices circulation enqueued FOR THEM (recipient == ticket),
    # rendered to a {subject, body} card via the event catalog. Suppressed notices
    # (opted-out, never meant for delivery) are excluded from the inbox view.
    def _inbox_card(self, row, tenant):
        """Render one stored notification row into an inbox card (id/ts/event/...)."""
        payload = json.loads(row['payload_json'])
        subject, body = '', ''
        if self.catalog.has(row['event']):
            tmpl = self.catalog.template(row['event'])
            subject = render(tmpl.get('subject'), payload)
            body = render(tmpl.get('body'), payload)
        return {'id': row['id'], 'ts': row['created_at'], 'event': row['event'],
                'subject': subject, 'body': body, 'read': row['read_at'] is not None}

    def inbox(self, recipient, unread_only=False, tenant=None):
        """Dispatched notices addressed to ``recipient`` (newest first), as cards."""
        tenant = tenant or self.tenant
        sql = ("SELECT * FROM notification WHERE recipient=? AND tenant=? "
               "AND status!='suppressed'")
        params = [recipient, tenant]
        if unread_only:
            sql += ' AND read_at IS NULL'
        sql += ' ORDER BY id DESC'
        rows = self._conn().execute(sql, params).fetchall()
        return [self._inbox_card(r, tenant) for r in rows]

    def unread_count(self, recipient, tenant=None):
        tenant = tenant or self.tenant
        return self._conn().execute(
            "SELECT COUNT(*) AS n FROM notification WHERE recipient=? AND tenant=? "
            "AND status!='suppressed' AND read_at IS NULL",
            (recipient, tenant)).fetchone()['n']

    def mark_read(self, recipient, notif_id=None, mark_all=False, tenant=None):
        """Mark one notice (``notif_id``, must belong to ``recipient``) or all of a
        reader's notices read. Returns the reader's remaining unread count."""
        tenant = tenant or self.tenant
        c = self._conn()
        now = time.time()
        if mark_all:
            c.execute(
                'UPDATE notification SET read_at=? WHERE recipient=? AND tenant=? '
                'AND read_at IS NULL', (now, recipient, tenant))
        elif notif_id is not None:
            c.execute(
                'UPDATE notification SET read_at=? WHERE id=? AND recipient=? '
                'AND tenant=? AND read_at IS NULL',
                (now, notif_id, recipient, tenant))
        c.commit()
        return self.unread_count(recipient, tenant)
