#!/usr/bin/env python3
"""Reader-portal v2 social layer (#134 engagement / #133 discovery) — BACKEND.

Reader-scoped reviews + ratings, reading history, saved searches, and
content-based recommendations — all persisted in OUR access store
(``reader_review`` / ``reader_history`` / ``saved_search`` tables), reader-scoped
by the RDR ticket (RI=). NOTHING here is written to the live ИРБИС server: the
catalog is only ever READ through injected seams to compute "similar" / "for you"
candidates (the same posture as ``holds.py`` / ``shelves.py``, #222).

This module is pure domain logic over the store + three small injected seams,
mirroring the holds/shelves pattern:

  * ``read_terms(db, mfn) -> {'subjects': [...], 'authors': [...],
    'collectives': [...]}`` — the seed record's 606 / 700 / 610 values, used to
    find similar records and (for "for you") to weight the reader's history. A
    ``None`` seam ⇒ no terms ⇒ empty recommendations (degrades, never raises).
  * ``search(db, prefix, term) -> [mfn, ...]`` — run a catalog/OPAC index search
    for a single term under a prefix ('S' subject, 'A' author, 'K' collective),
    returning candidate mfns. ``None`` ⇒ no candidates.
  * ``brief_read(db, mfn) -> {'title': str, 'author': str, ...}`` — resolve a
    candidate / history item's display title + author (reuses the OPAC brief read).

Reviews
-------
One editable review per (reader, db, mfn) — a second POST upserts (rating + text
replace the prior). ``reviews(db, mfn)`` aggregates ``avg`` + ``count`` over all
readers and, for a signed-in reader, returns ``mine``. Deleting is own-review
only (the route enforces 403 for someone else's id).

Recommendations ("similar")
---------------------------
Read the seed record's subjects/authors/collectives; for each term run the
matching index search; collect candidate mfns and count how many distinct seed
terms each candidate shares (overlap). Rank by that overlap descending (ties by
mfn for determinism), drop the seed itself and any already-held duplicate, cap at
``RECO_CAP``. Each item carries a human ``reason`` — "Общая тема: …" for a shared
subject (the highest-overlap explanation), "Тот же автор" for a shared author,
"Та же организация" for a shared collective.

"For you"
---------
Union the subjects of the reader's recent history records (most-recent first,
capped), then run the SAME shared-term ranking against that union — excluding the
records already in the reader's history. Empty history ⇒ empty list.
"""

# Cap on how many recommendation items we return (both "similar" and "for you").
RECO_CAP = 10
# How many recent history records feed the "for you" subject union.
FORYOU_HISTORY_DEPTH = 20
# Cap on history items returned to the portal.
HISTORY_CAP = 50
# How many candidate mfns to pull per term search (keeps the fan-out bounded).
PER_TERM_CAP = 30

_RATING_MIN = 1
_RATING_MAX = 5


def _clamp_rating(rating):
    """Coerce ``rating`` to an int in 1..5, or raise ValueError. The route turns
    a ValueError into a 400 so a bad rating never reaches the store."""
    try:
        r = int(rating)
    except (TypeError, ValueError):
        raise ValueError('rating must be an integer 1..5')
    if r < _RATING_MIN or r > _RATING_MAX:
        raise ValueError('rating out of range 1..5')
    return r


class SocialService:
    """Reviews/ratings, history, saved searches + recommendations over a store.

    Parameters
    ----------
    store
        Access store (``AccessStore`` sqlite or ``PgAccessStore``) providing the
        reader_review / reader_history / saved_search CRUD. Reader-scoped by ticket.
    read_terms : callable | None
        ``read_terms(db, mfn) -> {'subjects','authors','collectives'}`` for the
        seed record (606/700/610). ``None`` ⇒ no recommendation terms.
    search : callable | None
        ``search(db, prefix, term) -> [mfn,...]`` index search. ``None`` ⇒ no
        candidates (recommendations come back empty).
    brief_read : callable | None
        ``brief_read(db, mfn) -> {'title','author',...}`` display resolution.
        ``None`` ⇒ blank title/author.
    reader_name : callable | None
        ``reader_name(ticket) -> str`` to label a review with the reader's name.
        ``None`` ⇒ '' (the route can still show "anonymous").
    now : callable
        Clock injection (``time.time`` by default) for deterministic tests.
    """

    # Which index prefix each seed-term kind searches under (IRBIS inverted files:
    # S= subject heading <-606, A= author <-700, K= keyword/collective <-610).
    _PREFIX = {'subjects': 'S', 'authors': 'A', 'collectives': 'K'}

    def __init__(self, store, read_terms=None, search=None, brief_read=None,
                 reader_name=None, now=None):
        self.store = store
        self.read_terms = read_terms
        self.search = search
        self.brief_read = brief_read
        self.reader_name = reader_name
        if now is None:
            import time
            now = time.time
        self._now = now

    # ---- display seams (never raise out) --------------------------------- #
    def _brief(self, db, mfn):
        if self.brief_read is None:
            return {'title': '', 'author': ''}
        try:
            it = self.brief_read(db, mfn) or {}
        except Exception:
            return {'title': '', 'author': ''}
        title = (it.get('title') or '').strip()
        if title == ('MFN %d' % mfn):
            title = ''
        return {'title': title, 'author': (it.get('author') or '').strip()}

    def _name(self, ticket):
        if self.reader_name is None:
            return ''
        try:
            return (self.reader_name(ticket) or '').strip()
        except Exception:
            return ''

    # ===================================================================== #
    # REVIEWS / RATINGS (#134) — one editable review per (reader, db, mfn).
    # ===================================================================== #
    def post_review(self, ticket, db, mfn, rating, text=''):
        """Upsert the reader's review of (db, mfn). Returns ``{'id'}``.

        Rating is validated to 1..5 (ValueError → the route returns 400). A second
        post by the same reader on the same item replaces the prior rating/text."""
        rating = _clamp_rating(rating)
        text = (text or '').strip()
        name = self._name(ticket)
        row = self.store.review_upsert(ticket, db, mfn, rating, text, name,
                                       self._now())
        return {'id': row['id']}

    def reviews(self, db, mfn, ticket=None):
        """Aggregate reviews of (db, mfn): ``{avg, count, items, mine?}``.

        ``avg`` is the mean rating rounded to 1 dp (0 when none); ``count`` the
        number of reviews; ``items`` every review as a card (newest first). When a
        ``ticket`` is given and that reader has a review, ``mine`` carries it."""
        rows = self.store.reviews_for(db, mfn)
        count = len(rows)
        avg = round(sum(r['rating'] for r in rows) / count, 1) if count else 0
        items = [{
            'id': r['id'],
            'readerName': r.get('reader_name') or 'Читатель',
            'rating': r['rating'],
            'text': r.get('text') or '',
            'ts': r['ts'],
        } for r in rows]
        out = {'avg': avg, 'count': count, 'items': items}
        if ticket:
            mine = self.store.review_mine(ticket, db, mfn)
            if mine:
                out['mine'] = {'rating': mine['rating'], 'text': mine.get('text') or ''}
        return out

    def delete_review(self, ticket, review_id):
        """Delete the reader's OWN review. Returns ``{'id'}`` or None when the id
        isn't this reader's (the route turns None into 403)."""
        row = self.store.review_delete(ticket, review_id)
        if row is None:
            return None
        return {'id': review_id}

    # ===================================================================== #
    # READING HISTORY (auto-logged) — dedup by (db, mfn), latest kept.
    # ===================================================================== #
    def log_open(self, ticket, db, mfn):
        """Record that the reader opened (db, mfn). Best-effort: any store error is
        swallowed so the record read never breaks (called from the render path)."""
        if not ticket:
            return
        try:
            title = self._brief(db, mfn)['title']
            self.store.history_log(ticket, db, mfn, title, self._now())
        except Exception:
            pass

    def history(self, ticket):
        """The reader's reading history, deduped by (db, mfn) keeping the latest
        open, newest first, capped at ``HISTORY_CAP``."""
        rows = self.store.history_for(ticket, limit=HISTORY_CAP)
        return {'items': [{'db': r['db'], 'mfn': r['mfn'],
                           'title': r.get('title') or ('MFN %d' % r['mfn']),
                           'ts': r['ts']} for r in rows]}

    # ===================================================================== #
    # SAVED SEARCHES — reader-scoped CRUD.
    # ===================================================================== #
    def saved_searches(self, ticket):
        rows = self.store.saved_search_list(ticket)
        return {'items': [{'id': r['id'], 'name': r['name'], 'db': r['db'],
                           'prefix': r.get('prefix') or '', 'query': r['query']}
                          for r in rows]}

    def save_search(self, ticket, name, db, prefix, query):
        """Persist a saved search. Returns ``{'id'}``. ``query`` is required."""
        query = (query or '').strip()
        if not query:
            raise ValueError('query required')
        name = (name or '').strip() or query
        row = self.store.saved_search_add(ticket, name, db or '', prefix or '',
                                          query, self._now())
        return {'id': row['id']}

    def delete_search(self, ticket, search_id):
        """Delete the reader's own saved search. Returns ``{'id'}`` or None."""
        row = self.store.saved_search_delete(ticket, search_id)
        if row is None:
            return None
        return {'id': search_id}

    # ===================================================================== #
    # RECOMMENDATIONS (#133) — content-based, ranked by shared-term overlap.
    # ===================================================================== #
    def _candidates_for_terms(self, db, terms_by_kind):
        """Run the per-term index search and tally, per candidate mfn, which seed
        terms it shares.

        ``terms_by_kind`` is ``{'subjects':[...], 'authors':[...],
        'collectives':[...]}``. Returns ``{mfn: {'overlap': n,
        'subjects': set(), 'authors': set(), 'collectives': set()}}`` where overlap
        is the count of DISTINCT seed terms (across all kinds) the candidate shares.
        """
        if self.search is None:
            return {}
        hits = {}
        for kind, prefix in self._PREFIX.items():
            for term in terms_by_kind.get(kind) or []:
                term = (term or '').strip()
                if not term:
                    continue
                try:
                    mfns = self.search(db, prefix, term) or []
                except Exception:
                    mfns = []
                for mfn in mfns[:PER_TERM_CAP]:
                    h = hits.setdefault(mfn, {'overlap': 0, 'subjects': set(),
                                              'authors': set(), 'collectives': set()})
                    if term not in h[kind]:
                        h[kind].add(term)
                        h['overlap'] += 1
        return hits

    @staticmethod
    def _reason(info):
        """Human explanation for a recommended item, by the strongest shared kind:
        a shared subject first (most meaningful), then author, then collective."""
        if info['subjects']:
            return 'Общая тема: %s' % sorted(info['subjects'])[0]
        if info['authors']:
            return 'Тот же автор'
        if info['collectives']:
            return 'Та же организация'
        return 'Похожая запись'

    def _rank(self, db, hits, exclude):
        """Rank candidate ``hits`` by overlap desc (ties by mfn), drop ``exclude``
        mfns, cap at ``RECO_CAP``, and attach title/author/reason to each."""
        ranked = sorted(
            ((mfn, info) for mfn, info in hits.items() if mfn not in exclude),
            key=lambda kv: (-kv[1]['overlap'], kv[0]))
        out = []
        for mfn, info in ranked[:RECO_CAP]:
            brief = self._brief(db, mfn)
            out.append({'mfn': mfn, 'title': brief['title'],
                        'author': brief['author'], 'reason': self._reason(info)})
        return out

    def similar(self, db, mfn):
        """"Similar" recommendations for the seed record (db, mfn).

        Reads the seed's 606/700/610, finds records sharing those terms, ranks by
        overlap, excludes the seed, caps at ``RECO_CAP``. Empty list when the seed
        has no terms or no neighbours."""
        if self.read_terms is None:
            return {'items': []}
        try:
            terms = self.read_terms(db, mfn) or {}
        except Exception:
            terms = {}
        hits = self._candidates_for_terms(db, terms)
        return {'items': self._rank(db, hits, exclude={mfn})}

    def for_you(self, ticket):
        """"For you" recommendations derived from the reader's reading history.

        Unions the subjects of the reader's recent history records, ranks records
        sharing those subjects by overlap, excludes anything already in the
        reader's history. Empty list when the reader has no history (or the history
        records carry no subjects)."""
        if self.read_terms is None:
            return {'items': []}
        rows = self.store.history_for(ticket, limit=FORYOU_HISTORY_DEPTH)
        if not rows:
            return {'items': []}
        # Union the recent records' subjects; remember a representative db (the
        # newest history db) to run the candidate search against, and exclude every
        # record the reader has already seen.
        subjects = []
        seen = set()
        seed_db = rows[0]['db']
        history_keys = set()
        for r in rows:
            history_keys.add((r['db'], r['mfn']))
            try:
                terms = self.read_terms(r['db'], r['mfn']) or {}
            except Exception:
                terms = {}
            for s in terms.get('subjects') or []:
                s = (s or '').strip()
                if s and s not in seen:
                    seen.add(s)
                    subjects.append(s)
        if not subjects:
            return {'items': []}
        hits = self._candidates_for_terms(seed_db, {'subjects': subjects})
        exclude = {mfn for (d, mfn) in history_keys if d == seed_db}
        return {'items': self._rank(seed_db, hits, exclude=exclude)}
