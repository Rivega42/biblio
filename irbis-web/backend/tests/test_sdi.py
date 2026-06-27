#!/usr/bin/env python3
"""Тесты ребра 10.1 — ИРИ/SDI: избирательное распространение информации.

Покрыто:
  * `SdiStore`/`SdiService`: add/list/remove профиля, изоляция по reader;
  * `run_profile`: НОВЫЕ mfn относительно прошлого прогона; пустой результат,
    когда нового нет; идемпотентность (повторный run без новых -> new:[]);
  * прирост каталога ([1,2] -> [1,2,3]) даёт ровно new:[3] на 2-м прогоне;
  * `run_all`: сводка по всем профилям; без catalog-хендла -> пусто;
  * `new_for_reader`: накопленные попадания читателя.

Фейковый catalog-хендл с управляемым search(): мутируем выдачу между прогонами.

Запуск: py -3.12 tests/test_sdi.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.sdi import SdiService, SdiStore

PASS = [0]
FAIL = [0]
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


class _Cat:
    """Каталог-заглушка с управляемой выдачей. ``mfns`` мутируем в тесте,
    эмулируя появление новых записей в каталоге между прогонами.

    Контракт: ``search(db, query, limit=...) -> {'items':[{'mfn':int}], ...}``.
    """

    def __init__(self, mfns):
        self.mfns = list(mfns)
        self.calls = []

    def search(self, db, query, limit=200):
        self.calls.append((db, query, limit))
        return {'items': [{'mfn': m, 'db': db} for m in self.mfns],
                'count': len(self.mfns)}


def profile_crud_checks():
    print('-- SDI: add/list/remove профиля + изоляция по reader')
    svc = SdiService(SdiStore(':memory:'), now=lambda: T0)
    p = svc.add_profile('R1', 'История', 'IBIS', 'T=история')
    check('add_profile вернул строку', p['reader'] == 'R1'
          and p['name'] == 'История' and p['db'] == 'IBIS'
          and p['query'] == 'T=история')
    check('новый профиль не запускался (last_run_at NULL)',
          p['last_run_at'] is None)
    svc.add_profile('R1', 'Физика', 'IBIS', 'T=физика')
    svc.add_profile('R2', 'Чужой', 'IBIS', 'T=чужой')
    check('list_profiles по reader (R1 -> 2)', len(svc.list_profiles('R1')) == 2)
    check('изоляция по reader (R2 -> 1)', len(svc.list_profiles('R2')) == 1)
    ok = svc.remove_profile(p['id'])
    check('remove_profile -> True', ok)
    check('после remove у R1 один профиль', len(svc.list_profiles('R1')) == 1)
    check('remove несуществующего -> False', svc.remove_profile(99999) is False)


def run_new_checks():
    print('-- SDI: run_profile -> НОВЫЕ mfn; прирост каталога даёт new:[3]')
    cat = _Cat([1, 2])
    svc = SdiService(SdiStore(':memory:'), catalog=cat, now=lambda: T0)
    p = svc.add_profile('R1', 'История', 'IBIS', 'T=история')
    r1 = svc.run_profile(p['id'])
    check('1-й прогон: new = [1,2]', sorted(r1['new']) == [1, 2])
    check('1-й прогон: total_seen = 2', r1['total_seen'] == 2)
    check('search вызван с db/query профиля',
          cat.calls[-1][0] == 'IBIS' and cat.calls[-1][1] == 'T=история')
    check('last_run_at проставлен',
          svc.store.get_profile(p['id'])['last_run_at'] == T0)

    # каталог пополнился записью 3
    cat.mfns = [1, 2, 3]
    r2 = svc.run_profile(p['id'])
    check('2-й прогон: только НОВОЕ -> new = [3]', r2['new'] == [3])
    check('2-й прогон: total_seen = 3', r2['total_seen'] == 3)


def empty_and_idempotent_checks():
    print('-- SDI: пустой результат + идемпотентность')
    cat = _Cat([10, 11])
    svc = SdiService(SdiStore(':memory:'), catalog=cat, now=lambda: T0)
    p = svc.add_profile('R1', 'Проф', 'IBIS', 'T=q')
    svc.run_profile(p['id'])                      # увидели 10,11
    r2 = svc.run_profile(p['id'])                 # каталог не менялся
    check('повторный run без новых -> new = []', r2['new'] == [])
    check('total_seen стабилен (2)', r2['total_seen'] == 2)
    r3 = svc.run_profile(p['id'])                 # ещё раз — всё так же
    check('идемпотентность: 3-й run -> new = []', r3['new'] == [])
    check('hits профиля не задублировались (2)',
          len(svc.store.hits(p['id'])) == 2)


def run_all_checks():
    print('-- SDI: run_all (все профили / один читатель)')
    cat = _Cat([1, 2, 3])
    svc = SdiService(SdiStore(':memory:'), catalog=cat, now=lambda: T0)
    svc.add_profile('R1', 'A', 'IBIS', 'T=a')
    svc.add_profile('R1', 'B', 'IBIS', 'T=b')
    svc.add_profile('R2', 'C', 'IBIS', 'T=c')
    summ = svc.run_all('R1')
    check('run_all(R1): 2 профиля', summ['profiles'] == 2)
    check('run_all(R1): new_total = 6 (3+3)', summ['new_total'] == 6)
    check('run_all(R1) не трогает R2',
          all(p['last_run_at'] is None for p in svc.list_profiles('R2')))
    all_summ = svc.run_all()                       # все читатели
    check('run_all() покрывает все профили (3)', all_summ['profiles'] == 3)
    # повторно — нового нет
    again = svc.run_all('R1')
    check('run_all повторно -> new_total = 0', again['new_total'] == 0)


def no_catalog_checks():
    print('-- SDI: без catalog-хендла -> пусто (мягкая деградация)')
    svc = SdiService(SdiStore(':memory:'), catalog=None, now=lambda: T0)
    p = svc.add_profile('R1', 'X', 'IBIS', 'T=x')
    r = svc.run_profile(p['id'])
    check('без catalog: new = []', r['new'] == [])
    check('без catalog: total_seen = 0', r['total_seen'] == 0)
    check('без catalog: попаданий не записано', svc.store.hits(p['id']) == [])
    check('run_profile несуществующего профиля -> пусто',
          svc.run_profile(99999)['new'] == [])


def new_for_reader_checks():
    print('-- SDI: new_for_reader (накопленные попадания читателя)')
    cat = _Cat([1, 2])
    svc = SdiService(SdiStore(':memory:'), catalog=cat, now=lambda: T0)
    p1 = svc.add_profile('R1', 'A', 'IBIS', 'T=a')
    svc.add_profile('R2', 'Z', 'IBIS', 'T=z')
    svc.run_profile(p1['id'])
    acc = svc.new_for_reader('R1')
    check('new_for_reader(R1): 2 попадания', len(acc) == 2)
    check('new_for_reader несёт mfn профиля',
          sorted(h['mfn'] for h in acc) == [1, 2])
    check('new_for_reader изолирован по reader (R2 -> пусто)',
          svc.new_for_reader('R2') == [])


def main():
    profile_crud_checks()
    run_new_checks()
    empty_and_idempotent_checks()
    run_all_checks()
    no_catalog_checks()
    new_for_reader_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
