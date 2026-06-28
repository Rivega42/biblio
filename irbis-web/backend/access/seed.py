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
        # Функция-модуль 'cataloging' — на неё гвардятся own-store роуты каталога
        # (MARC/MARCXML обмен, дедуп, печать, версии, словари, ВКР, DAM, периодика,
        # шаблоны метаданных, авто-фасеты, выставки-правка, OCR-индекс). Без неё
        # реальный каталогизатор получал 403 на этих роутах (грант существовал
        # только в тестах). Write покрывает и read-гварды (write >= read).
        ('cataloging', '*', 'write'),
    ],
    'administrator': [
        ('search', '*', 'read'), ('record.read', '*', 'read'), ('record.write', '*', 'write'),
        ('record.delete', '*', 'admin'), ('terms', '*', 'read'), ('file', '*', 'read'),
        ('order', '*', 'write'), ('cabinet', '*', 'read'),
        ('circ.issue', '*', 'write'), ('circ.return', '*', 'write'),
        ('admin.db', '*', 'admin'), ('admin.users', '*', 'admin'),
        ('acq.receipt', '*', 'write'), ('acq.read', '*', 'read'),
        ('bp.write', '*', 'write'), ('bp.read', '*', 'read'),
        ('cat.gbl', '*', 'write'),
        # См. коммент в роли 'cataloger': own-store роуты каталога гвардятся на
        # функцию 'cataloging'; администратору она тоже нужна (иначе 403).
        ('cataloging', '*', 'write'),
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
