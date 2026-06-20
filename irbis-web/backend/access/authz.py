#!/usr/bin/env python3
"""Authorization: grant = (function x db x level). Pure functions, no I/O.

Decision (P0_BUILDKIT §4): a grant matches when function equals and db is exact or '*';
an exact-db grant outranks a '*' grant; the effective level must be >= the level needed.
Server's -3338 (CLIENT_NOT_ALLOWED) is mapped to HTTP 403 at the API edge.
"""
LEVEL_RANK = {'read': 1, 'write': 2, 'admin': 3}

# Implicit grant sets for non-staff sessions (not stored in DB).
GUEST_GRANTS = [
    {'function': 'search', 'db': '*', 'level': 'read'},
    {'function': 'record.read', 'db': '*', 'level': 'read'},
    {'function': 'terms', 'db': '*', 'level': 'read'},
    {'function': 'file', 'db': '*', 'level': 'read'},
]
READER_GRANTS = GUEST_GRANTS + [
    {'function': 'order', 'db': '*', 'level': 'write'},
    {'function': 'cabinet', 'db': '*', 'level': 'read'},
]


def best_grant(grants, function, db):
    cands = [g for g in grants if g['function'] == function and g['db'] in (db, '*')]
    if not cands:
        return None
    exact = [g for g in cands if g['db'] == db]
    pool = exact or cands                      # exact db beats '*'
    return max(pool, key=lambda g: LEVEL_RANK.get(g['level'], 0))


def authorize(grants, function, db, level_needed):
    g = best_grant(grants, function, db)
    if not g:
        return False
    return LEVEL_RANK.get(g['level'], 0) >= LEVEL_RANK.get(level_needed, 99)
