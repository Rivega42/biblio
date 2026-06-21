#!/usr/bin/env python3
"""Reader shelves / reading lists (#222) — reader-portal BACKEND.

Per-reader reading lists, persisted in OUR access store (``reader_shelf`` +
``reader_shelf_item``), reader-scoped by RDR ticket — NOT on the live ИРБИС
server.

Two **system** lists are seeded lazily on first access (so a reader who never
opens their shelves leaves no rows): ``want`` «Хочу прочитать» and ``fav``
«Избранное». A reader may create additional **custom** lists; items
(``db``, ``mfn``) are deduped per list, and the display title is resolved once at
add time via the injected brief-read seam (mirroring ``holds.py``).

This is pure domain logic over the store + one injected seam (``brief_read`` for
the title); no I/O of its own.
"""

# System reading lists every reader gets, seeded lazily on first GET.
SYSTEM_LISTS = (
    ('want', 'Хочу прочитать'),
    ('fav', 'Избранное'),
)
SYSTEM_IDS = frozenset(i for i, _ in SYSTEM_LISTS)


class ShelfService:
    """Create / list reading lists and add/remove items, over an access store.

    Parameters
    ----------
    store
        Access store (``AccessStore`` sqlite or ``PgAccessStore``) providing the
        reader_shelf CRUD. Reader-scoped by ticket.
    brief_read : callable | None
        ``brief_read(db, mfn) -> {'title': str, ...}`` to resolve a stored item's
        display title at add time. ``None`` ⇒ title blank.
    """

    def __init__(self, store, brief_read=None):
        self.store = store
        self.brief_read = brief_read

    def _title(self, db, mfn):
        if self.brief_read is None:
            return ''
        try:
            it = self.brief_read(db, mfn) or {}
            t = (it.get('title') or '').strip()
            return '' if t == ('MFN %d' % mfn) else t
        except Exception:
            return ''

    def _ensure_system(self, ticket):
        """Seed the two system lists for a reader if not present (idempotent)."""
        have = {r['id'] for r in self.store.shelf_lists(ticket)}
        for list_id, name in SYSTEM_LISTS:
            if list_id not in have:
                self.store.shelf_create(ticket, list_id, name, system=1)

    # ---- operations ------------------------------------------------------- #
    def lists(self, ticket):
        """All of a reader's lists (system seeded lazily), each with its items."""
        self._ensure_system(ticket)
        out = []
        for lst in self.store.shelf_lists(ticket):
            items = [{'db': it['db'], 'mfn': it['mfn'],
                      'title': it.get('title') or ('MFN %d' % it['mfn'])}
                     for it in self.store.shelf_items(ticket, lst['id'])]
            out.append({'id': lst['id'], 'name': lst['name'],
                        'system': bool(lst['system']), 'items': items})
        return out

    def create(self, ticket, name):
        """Create a custom list with an auto-assigned id. Returns ``{'id','name'}``."""
        self._ensure_system(ticket)
        name = (name or '').strip() or 'Список'
        list_id = self.store.shelf_next_custom_id(ticket)
        self.store.shelf_create(ticket, list_id, name, system=0)
        return {'id': list_id, 'name': name}

    def add_item(self, ticket, list_id, db, mfn):
        """Add (db,mfn) to ``list_id`` (deduped). Returns ``{'listId'}`` or None
        when the list doesn't exist for this reader."""
        self._ensure_system(ticket)
        if self.store.shelf_get(ticket, list_id) is None:
            return None
        title = self._title(db, mfn)
        self.store.shelf_add_item(ticket, list_id, db, mfn, title)
        return {'listId': list_id}

    def remove_item(self, ticket, list_id, db, mfn):
        """Remove (db,mfn) from ``list_id``. Returns ``{'listId'}`` or None when the
        list doesn't exist for this reader."""
        self._ensure_system(ticket)
        if self.store.shelf_get(ticket, list_id) is None:
            return None
        self.store.shelf_remove_item(ticket, list_id, db, mfn)
        return {'listId': list_id}
