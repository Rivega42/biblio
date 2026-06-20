#!/usr/bin/env python3
"""Access suite tests: password hash/verify, authz best-grant logic, effective grants.
Run: py irbis-web/backend/tests/test_access.py  (writes a temp sqlite db)."""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.store import AccessStore
from access.authz import authorize, best_grant, READER_GRANTS, GUEST_GRANTS
from access.seed import seed

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def main():
    # password
    h = AccessStore.hash_password('s3cret')
    check('password verify ok', AccessStore.verify_password('s3cret', h))
    check('password verify bad', not AccessStore.verify_password('wrong', h))

    # authz logic (pure)
    grants = [
        {'function': 'record.write', 'db': '*', 'level': 'write'},
        {'function': 'record.write', 'db': 'IBIS', 'level': 'admin'},
        {'function': 'search', 'db': '*', 'level': 'read'},
    ]
    check('exact db beats *', best_grant(grants, 'record.write', 'IBIS')['level'] == 'admin')
    check('falls back to *', best_grant(grants, 'record.write', 'RDR')['level'] == 'write')
    check('write allows on RDR', authorize(grants, 'record.write', 'RDR', 'write'))
    check('read<write denied', not authorize(grants, 'search', 'IBIS', 'write'))
    check('no grant denied', not authorize(grants, 'admin.users', 'IBIS', 'admin'))
    check('guest can search', authorize(GUEST_GRANTS, 'search', 'IBIS', 'read'))
    check('guest cannot order', not authorize(GUEST_GRANTS, 'order', 'IBIS', 'write'))
    check('reader can order', authorize(READER_GRANTS, 'order', 'IBIS', 'write'))

    # store + seed + effective grants
    tmp = os.path.join(tempfile.gettempdir(), 'irbisweb_test_access.db')
    if os.path.exists(tmp):
        os.remove(tmp)
    st = AccessStore(tmp)
    seed(st)
    acc = st.authenticate('admin', 'admin')
    check('seed admin authenticates', acc is not None)
    check('seed bad password rejected', st.authenticate('admin', 'nope') is None)
    eg = st.effective_grants(acc['id'])
    check('admin has admin.users', authorize(eg, 'admin.users', 'IBIS', 'admin'))
    lib = st.authenticate('librarian', 'librarian')
    leg = st.effective_grants(lib['id'])
    check('librarian can write IBIS', authorize(leg, 'record.write', 'IBIS', 'write'))
    check('librarian cannot admin users', not authorize(leg, 'admin.users', 'IBIS', 'admin'))
    check('librarian can order', authorize(leg, 'order', 'IBIS', 'write'))

    # audit
    st.audit('admin', 'record.write', 'IBIS', 42, 'ok', {'note': 'тест'})
    check('audit recorded', len(st.recent_audit()) >= 1)

    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
