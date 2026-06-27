#!/usr/bin/env python3
"""Тесты ROLES — собственная модель ролевого доступа АРМ «Администратор».

Покрыто (на in-memory сторе с фиксированными часами):
  * CRUD ролей (create/get по id и имени/list);
  * гранты — add (идемпотентно с обновлением уровня) / remove / role_grants;
  * назначение ролей аккаунту — assign/unassign, идемпотентность повторного assign;
  * наследование — child видит гранты parent; resolve_role_chain;
  * сведение эффективных грантов — побеждает более правомочный уровень;
  * has_permission — allow/deny, точный db бьёт '*', упорядочивание уровней;
  * защита от циклов в parent-цепочке (без зацикливания);
  * ValueError на несуществующей роли.

Запуск: py -3.12 tests/test_roles.py ; в агрегаторе test_access.py.
ВНИМАНИЕ: в print-строках только ASCII '->' (cp1251-консоль падает на unicode-стрелках).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import roles

PASS = [0]
FAIL = [0]

# Фиксированные часы для детерминизма.
CLOCK = '2026-06-27T00:00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _store():
    """Свежий in-memory стор с фиксированными часами."""
    return roles.RoleStore(':memory:', now=lambda: CLOCK)


def _service():
    """Свежий сервис поверх in-memory стора с фиксированными часами."""
    return roles.RoleService(store=_store())


def crud_checks():
    print('-- crud: create / get (id и имя) / list')
    s = _store()
    r = s.create_role('librarian', description='Библиотекарь')
    check('create -> dict с id', isinstance(r, dict) and r['id'] >= 1)
    check('имя сохранено', r['name'] == 'librarian')
    check('описание сохранено', r['description'] == 'Библиотекарь')
    check('parent_id NULL у корня', r['parent_id'] is None)
    check('created_at = фикс. часы', r['created_at'] == CLOCK)
    check('get по имени', s.get_role('librarian')['id'] == r['id'])
    check('get по id', s.get_role(r['id'])['name'] == 'librarian')
    check('get несуществующей -> None', s.get_role('nope') is None)
    check('get(None) -> None', s.get_role(None) is None)
    s.create_role('admin')
    check('list -> 2 роли', len(s.list_roles()) == 2)


def grant_checks():
    print('-- grant: add (идемпотентность+обновление) / remove / role_grants')
    s = _store()
    s.create_role('librarian')
    g = s.add_grant('librarian', 'search', db='*', level='read')
    check('add -> dict', isinstance(g, dict) and g['function'] == 'search')
    check('уровень read', g['level'] == 'read')
    check('db по умолчанию *', g['db'] == '*')
    check('1 грант на роли', len(s.role_grants('librarian')) == 1)
    # Повтор того же (function, db) обновляет уровень, не плодит дубль.
    s.add_grant('librarian', 'search', db='*', level='write')
    gs = s.role_grants('librarian')
    check('add идемпотентен (1 грант)', len(gs) == 1)
    check('уровень обновлён -> write', gs[0]['level'] == 'write')
    s.add_grant('librarian', 'record.write', db='IBIS', level='write')
    check('второй грант добавлен', len(s.role_grants('librarian')) == 2)
    s.remove_grant('librarian', 'search', '*')
    check('remove убрал грант', len(s.role_grants('librarian')) == 1)
    check('неизвестный level -> ValueError', _raises(
        lambda: s.add_grant('librarian', 'x', level='superuser')))


def assign_checks():
    print('-- assign / unassign / account_roles (идемпотентность)')
    s = _store()
    s.create_role('librarian')
    s.create_role('admin')
    s.assign('user1', 'librarian')
    check('1 роль у аккаунта', len(s.account_roles('user1')) == 1)
    # Идемпотентность: повторный assign не бросает и не плодит дубль.
    s.assign('user1', 'librarian')
    check('повторный assign идемпотентен', len(s.account_roles('user1')) == 1)
    s.assign('user1', 'admin')
    check('2 роли у аккаунта', len(s.account_roles('user1')) == 2)
    s.unassign('user1', 'librarian')
    names = [r['name'] for r in s.account_roles('user1')]
    check('unassign снял роль', names == ['admin'])
    check('другой аккаунт без ролей', s.account_roles('user2') == [])


def inheritance_checks():
    print('-- inheritance: child видит гранты parent + resolve_role_chain')
    svc = _service()
    base = svc.create_role('base')
    svc.add_grant('base', 'search', db='*', level='read')
    child = svc.create_role('child', parent='base')
    svc.add_grant('child', 'order', db='*', level='write')
    check('child.parent_id = base.id', child['parent_id'] == base['id'])
    svc.assign('u', 'child')
    eff = svc.effective_grants('u')
    funcs = sorted(g['function'] for g in eff)
    check('эффективные = свои + унаследованные', funcs == ['order', 'search'])
    # resolve_role_chain: от child вверх до base.
    chain = [r['name'] for r in svc.resolve_role_chain('child')]
    check('цепочка child -> base', chain == ['child', 'base'])
    check('цепочка корня = сама роль', [r['name'] for r in
          svc.resolve_role_chain('base')] == ['base'])
    check('resolve_role_chain несущ. -> ValueError', _raises(
        lambda: svc.resolve_role_chain('ghost')))
    # Три уровня наследования.
    svc.create_role('grand', parent='child')
    gchain = [r['name'] for r in svc.resolve_role_chain('grand')]
    check('цепочка 3 уровня', gchain == ['grand', 'child', 'base'])


def permissive_checks():
    print('-- permissive: при совпадении (function,db) побеждает старший level')
    svc = _service()
    svc.create_role('low')
    svc.create_role('high')
    svc.add_grant('low', 'record.write', db='IBIS', level='read')
    svc.add_grant('high', 'record.write', db='IBIS', level='admin')
    svc.assign('u', 'low')
    svc.assign('u', 'high')
    eff = svc.effective_grants('u')
    same = [g for g in eff if g['function'] == 'record.write' and g['db'] == 'IBIS']
    check('один сведённый грант на (function,db)', len(same) == 1)
    check('победил более правомочный admin', same[0]['level'] == 'admin')
    # То же при наследовании: parent read, child admin.
    svc2 = _service()
    svc2.create_role('p')
    svc2.add_grant('p', 'f', db='*', level='read')
    svc2.create_role('c', parent='p')
    svc2.add_grant('c', 'f', db='*', level='admin')
    svc2.assign('u2', 'c')
    eff2 = svc2.effective_grants('u2')
    check('наследование: admin бьёт read', [g for g in eff2
          if g['function'] == 'f'][0]['level'] == 'admin')


def permission_checks():
    print('-- has_permission: allow/deny + упорядочивание + точный db бьёт *')
    svc = _service()
    svc.create_role('staff')
    svc.add_grant('staff', 'search', db='*', level='read')
    svc.add_grant('staff', 'record.write', db='IBIS', level='write')
    svc.assign('u', 'staff')
    check('search read -> allow', svc.has_permission('u', 'search', 'ANY', 'read'))
    check('search write -> deny (только read)',
          not svc.has_permission('u', 'search', 'ANY', 'write'))
    check('record.write на IBIS write -> allow',
          svc.has_permission('u', 'record.write', 'IBIS', 'write'))
    check('record.write read <= write -> allow',
          svc.has_permission('u', 'record.write', 'IBIS', 'read'))
    check('record.write admin -> deny',
          not svc.has_permission('u', 'record.write', 'IBIS', 'admin'))
    check('неизвестная функция -> deny',
          not svc.has_permission('u', 'unknown.fn', 'IBIS', 'read'))
    check('аккаунт без ролей -> deny',
          not svc.has_permission('nobody', 'search', 'ANY', 'read'))
    # Точный db бьёт '*': общий read на '*', точный admin на IBIS.
    svc.add_grant('staff', 'catalog', db='*', level='read')
    svc.add_grant('staff', 'catalog', db='IBIS', level='admin')
    check('точный db (IBIS admin) бьёт * (read) -> admin allow',
          svc.has_permission('u', 'catalog', 'IBIS', 'admin'))
    check('на другой БД действует * (read), admin -> deny',
          not svc.has_permission('u', 'catalog', 'OTHER', 'admin'))
    check('на другой БД * read -> allow',
          svc.has_permission('u', 'catalog', 'OTHER', 'read'))


def edgecase_checks():
    print('-- edgecases: цикл в parent-цепочке, ValueError на missing role')
    svc = _service()
    # ValueError: операции над несуществующей ролью.
    check('add_grant missing -> ValueError', _raises(
        lambda: svc.add_grant('ghost', 'f')))
    check('assign missing -> ValueError', _raises(
        lambda: svc.assign('u', 'ghost')))
    check('remove_grant missing -> ValueError', _raises(
        lambda: svc.remove_grant('ghost', 'f', '*')))
    check('role_grants missing -> ValueError', _raises(
        lambda: svc.role_grants('ghost')))
    check('create с несущ. parent -> ValueError', _raises(
        lambda: svc.create_role('orphan', parent='ghost')))
    # Цикл: a -> b -> a (создаём вручную через SQL, обходим без зацикливания).
    a = svc.create_role('a')
    b = svc.create_role('b', parent='a')
    # Замыкаем цикл: a.parent_id = b.id (прямой UPDATE мимо create_role).
    conn = svc.store._conn()
    conn.execute('UPDATE role SET parent_id=? WHERE id=?', (b['id'], a['id']))
    conn.commit()
    chain = [r['name'] for r in svc.resolve_role_chain('a')]
    check('resolve_role_chain не зацикливается на цикле',
          set(chain) == {'a', 'b'} and len(chain) == 2)
    # effective_grants на цикле тоже не виснет.
    svc.add_grant('a', 'fa', db='*', level='read')
    svc.add_grant('b', 'fb', db='*', level='read')
    svc.assign('cyc', 'a')
    eff = sorted(g['function'] for g in svc.effective_grants('cyc'))
    check('effective_grants на цикле без зависания', eff == ['fa', 'fb'])


def _raises(fn, exc=ValueError):
    """True, если ``fn()`` бросает ``exc``."""
    try:
        fn()
        return False
    except exc:
        return True


def main():
    crud_checks()
    grant_checks()
    assign_checks()
    inheritance_checks()
    permissive_checks()
    permission_checks()
    edgecase_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
