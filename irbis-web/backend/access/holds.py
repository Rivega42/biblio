#!/usr/bin/env python3
"""Reader holds + queue (#222) — reader-portal BACKEND.

A reader places a *hold* on a catalogue item (db, mfn). The hold and the FIFO
queue live in OUR access store (``reader_hold`` table), reader-scoped by the RDR
ticket — they are **NOT** written to the live ИРБИС server. This is the logical
reservation layer the portal owns; the eventual боевая интеграция with RQST/910
on the server is a separate concern (cf. ``core.order``'s TODO).

Queue model
-----------
Position is the reader's 1-based rank in the FIFO hold queue for that exact
(db, mfn), ordered by ``queued_at`` then id (oldest first). The first reader in
line is handed the copy when one is free:

  * If a free copy exists — the catalogue says ``is_available`` (via the wired
    catalog handle / exemplar API) AND no one is already ahead — the new hold is
    created ``ready`` at position 1.
  * Otherwise the hold is ``queued`` at its FIFO position (2, 3, …).

Without a catalog handle there is no availability signal, so a first-in-line hold
is still surfaced as ``ready`` (position 1) — the portal can show it as ready to
pick up — while later holders queue behind it. Re-holding the same item is
idempotent: the reader's existing live hold (and its current position) is
returned unchanged.

Title is resolved once at place time via the injected ``brief_read`` callable
(the existing OPAC brief read) so the holds list and the notification card can
show a human title without a second server round-trip.

This module is pure domain logic over the store + two small injected seams
(``catalog`` for availability, ``brief_read`` for the title); it performs no I/O
of its own and never raises out of the optional seams.
"""

READY = 'ready'
QUEUED = 'queued'
CANCELLED = 'cancelled'

# Default pickup-shelf TTL (days) for a hold that becomes ready. Kept local so the
# module stays standalone; the circulation policy owns the authoritative value.
HOLD_SHELF_DAYS = 3
_SECONDS_PER_DAY = 86400


class HoldService:
    """Place / cancel / list reader holds over an access store.

    Parameters
    ----------
    store
        The access store (``AccessStore`` sqlite or ``PgAccessStore``) — provides
        the reader_hold CRUD. Reader-scoped by ticket.
    catalog : object | None
        Optional catalogue handle exposing ``is_available(db, item)`` /
        ``find_exemplar(db, item)`` (``access.catalog.CatalogStore``). When wired,
        availability decides ready-vs-queued for the first holder. ``None`` ⇒ no
        availability opinion (first holder surfaced ready).
    brief_read : callable | None
        ``brief_read(db, mfn) -> {'title': str, ...}`` to resolve the display
        title at place time. ``None`` ⇒ title left blank (a "MFN n" stub).
    now : callable
        Clock injection (``time.time`` by default) so tests are deterministic.
    """

    def __init__(self, store, catalog=None, brief_read=None, now=None,
                 shelf_days=HOLD_SHELF_DAYS):
        self.store = store
        self.catalog = catalog
        self.brief_read = brief_read
        self.shelf_days = shelf_days
        if now is None:
            import time
            now = time.time
        self._now = now

    # ---- availability seam (catalog 910^A) -------------------------------- #
    def _catalog_free(self, db, mfn):
        """Catalogue availability for (db,mfn): True/False, or None (no opinion).

        ``mfn`` is the catalogue address; the catalog keys exemplars by inventory
        (``910^b``) so we ask by mfn-as-item. Any catalog error / absent copy ⇒
        None (caller falls back to its own queue state). Never raises."""
        if self.catalog is None:
            return None
        try:
            item = str(mfn)
            if hasattr(self.catalog, 'find_exemplar'):
                if self.catalog.find_exemplar(db, item) is None:
                    return None
            return bool(self.catalog.is_available(db, item))
        except Exception:
            return None

    def _title(self, db, mfn):
        if self.brief_read is None:
            return ''
        try:
            it = self.brief_read(db, mfn) or {}
            t = (it.get('title') or '').strip()
            return '' if t == ('MFN %d' % mfn) else t
        except Exception:
            return ''

    def _position(self, ticket, db, mfn):
        """1-based FIFO rank of the reader's live hold in (db,mfn)'s queue (0=absent)."""
        for idx, h in enumerate(self.store.hold_queue(db, mfn)):
            if h['ticket'] == ticket:
                return idx + 1
        return 0

    # ---- operations ------------------------------------------------------- #
    def place(self, ticket, db, mfn):
        """Place (or return the existing) hold for ``ticket`` on (db, mfn).

        Idempotent: an existing live hold is returned with its current position.
        Returns ``{'holdId', 'status', 'position'}``.
        """
        existing = self.store.hold_find_live(ticket, db, mfn)
        if existing:
            return {'holdId': existing['id'], 'status': existing['status'],
                    'position': self._position(ticket, db, mfn)}

        now = self._now()
        # Is anyone already queued/ready ahead of us? (FIFO — they hold priority.)
        queue_before = self.store.hold_queue(db, mfn)
        free = self._catalog_free(db, mfn)
        # Ready iff no one is ahead AND the catalogue does not say "issued".
        # free is None ⇒ no catalog opinion ⇒ first-in-line is surfaced ready.
        ready = (len(queue_before) == 0) and (free is not False)

        status = READY if ready else QUEUED
        until = (now + self.shelf_days * _SECONDS_PER_DAY) if ready else None
        title = self._title(db, mfn)
        hold = self.store.hold_add(ticket, db, mfn, title, status, now, until)
        return {'holdId': hold['id'], 'status': hold['status'],
                'position': self._position(ticket, db, mfn)}

    def place_many(self, ticket, items, default_db=None):
        """Оформить корзину читателя как заказы-брони (ребро INTEGRATION_MAP 10.2).

        Принимает список позиций корзины ``[{db?, mfn}, …]`` и ставит бронь на
        каждую через :meth:`place` — так корзина читательского портала
        **персистится как заказы** (own-store аналог RQST: «один движок, два
        клиента»). Идемпотентно поэлементно (повторная позиция возвращает
        существующую бронь, не задваивает). У позиции без ``db`` берётся
        ``default_db``. Кривая позиция (нет/нечисловой ``mfn``, нет ``db`` и нет
        дефолта) помечается ``error`` и НЕ роняет батч — остальные оформляются.

        Возвращает сводку::

            {'items': [{db, mfn, status|error, holdId?, position?}, …],
             'placed': N,        # успешно оформлено позиций (вкл. идемпотентные)
             'failed': N,        # позиций с ошибкой
             'ready': N, 'queued': N}   # из числа оформленных
        """
        results = []
        placed = failed = ready = queued = 0
        for it in (items or []):
            raw_db = (it.get('db') if isinstance(it, dict) else None) or default_db
            raw_mfn = it.get('mfn') if isinstance(it, dict) else None
            try:
                mfn = int(raw_mfn)
            except (TypeError, ValueError):
                failed += 1
                results.append({'db': raw_db, 'mfn': raw_mfn, 'error': 'bad_mfn'})
                continue
            if not raw_db:
                failed += 1
                results.append({'db': None, 'mfn': mfn, 'error': 'no_db'})
                continue
            res = self.place(ticket, raw_db, mfn)
            placed += 1
            if res.get('status') == READY:
                ready += 1
            elif res.get('status') == QUEUED:
                queued += 1
            results.append({'db': raw_db, 'mfn': mfn, 'status': res['status'],
                            'holdId': res['holdId'], 'position': res['position']})
        return {'items': results, 'placed': placed, 'failed': failed,
                'ready': ready, 'queued': queued}

    def list_for(self, ticket):
        """All of a reader's live holds as portal cards (with live positions)."""
        out = []
        for h in self.store.holds_for(ticket):
            out.append({
                'holdId': h['id'], 'db': h['db'], 'mfn': h['mfn'],
                'title': h.get('title') or ('MFN %d' % h['mfn']),
                'status': h['status'],
                'position': self._position(ticket, h['db'], h['mfn']),
                'until': h.get('until'),
            })
        return out

    def cancel(self, ticket, hold_id):
        """Cancel the reader's own hold. Returns ``{'holdId','status'}`` or None
        when the hold isn't the reader's / isn't live."""
        row = self.store.hold_cancel(ticket, hold_id)
        if row is None:
            return None
        return {'holdId': hold_id, 'status': CANCELLED}
