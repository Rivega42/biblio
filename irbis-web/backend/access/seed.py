#!/usr/bin/env python3
"""Idempotent dev seed: demo roles + staff accounts. Dev passwords only
(access.db is gitignored). In prod, provision accounts via admin tooling.
"""

ROLE_GRANTS = {
    'reader-service': [
        ('search', '*', 'read'), ('record.read', '*', 'read'), ('terms', '*', 'read'),
        ('file', '*', 'read'), ('order', '*', 'write'), ('cabinet', '*', 'read'),
        ('circ.issue', '*', 'write'), ('circ.return', '*', 'write'),
    ],
    'cataloger': [
        ('search', '*', 'read'), ('record.read', '*', 'read'), ('terms', '*', 'read'),
        ('file', '*', 'read'), ('record.write', 'IBIS', 'write'), ('cat.gbl', 'IBIS', 'write'),
    ],
    'administrator': [
        ('search', '*', 'read'), ('record.read', '*', 'read'), ('record.write', '*', 'write'),
        ('record.delete', '*', 'admin'), ('terms', '*', 'read'), ('file', '*', 'read'),
        ('order', '*', 'write'), ('cabinet', '*', 'read'),
        ('circ.issue', '*', 'write'), ('circ.return', '*', 'write'),
        ('admin.db', '*', 'admin'), ('admin.users', '*', 'admin'),
    ],
}

# login -> (password, full_name, [roles])
ACCOUNTS = {
    'admin':     ('admin', 'Администратор (демо)', ['administrator']),
    'librarian': ('librarian', 'Библиотекарь (демо)', ['reader-service', 'cataloger']),
}


def seed(store):
    role_ids = {}
    for name, grants in ROLE_GRANTS.items():
        rid = store.add_role(name)
        role_ids[name] = rid
        for fn, db, lvl in grants:
            store.add_role_grant(rid, fn, db, lvl)
    for login, (pw, full, roles) in ACCOUNTS.items():
        acc = store.create_account(login, pw, full)
        for rn in roles:
            store.assign_role(acc['id'], role_ids[rn])
    return {'roles': list(role_ids), 'accounts': list(ACCOUNTS)}


if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config
    from access.store import AccessStore
    cfg = Config()
    st = AccessStore(cfg.access_db)
    print('seeded:', seed(st))
