#!/usr/bin/env python3
"""Тесты контура Каталогизатор — версии записи + откат + дифф + дедуп-merge.

Покрыто:
  * `snapshot`: инкремент версии (1,2,3...) в рамках (db,mfn); вернёт номер;
  * `history`: метаданные версий по (db,mfn) в порядке возрастания + actor;
  * `get_version` / `revert`: полный record нужной версии, None для отсутствующей;
  * `diff`: field-level added / removed / changed по тегам;
  * `merge`: непустое побеждает пустое; повторяющиеся поля объединяются без
    дублей (один и тот же инстанс не плодится); список инстансов сводится;
  * изоляция: версии разных (db,mfn) не пересекаются.

Запуск: py -3.12 tests/test_catalog_versions.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.catalog_versions import (VersionService, VersionStore, merge,
                                      diff_records)

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


def _svc():
    return VersionService(VersionStore(':memory:'), now=lambda: T0)


def snapshot_checks():
    print('-- snapshot: инкремент версии в рамках (db,mfn)')
    svc = _svc()
    rec1 = {'200': {'a': 'Война и мир'}, '210': {'d': '2019'}}
    rec2 = {'200': {'a': 'Война и мир'}, '210': {'d': '2020'}}
    v1 = svc.snapshot('IBIS', 100, rec1, actor='cataloger1')
    v2 = svc.snapshot('IBIS', 100, rec2, actor='cataloger2')
    check('первая версия = 1', v1 == 1)
    check('вторая версия = 2', v2 == 2)
    v3 = svc.snapshot('IBIS', 100, rec1)
    check('третья версия = 3 (MAX+1)', v3 == 3)
    check('actor=None допустим', svc.get_version('IBIS', 100, 3) == rec1)


def history_checks():
    print('-- history: метаданные версий по (db,mfn)')
    svc = _svc()
    svc.snapshot('IBIS', 7, {'200': {'a': 'A'}}, actor='u1')
    svc.snapshot('IBIS', 7, {'200': {'a': 'B'}}, actor='u2')
    hist = svc.history('IBIS', 7)
    check('две версии в истории', len(hist) == 2)
    check('порядок по возрастанию версии',
          [h['version'] for h in hist] == [1, 2])
    check('actor сохранён', [h['actor'] for h in hist] == ['u1', 'u2'])
    check('created_at инжектирован', all(h['created_at'] == T0 for h in hist))
    check('история пустой записи -> []', svc.history('IBIS', 999) == [])


def get_revert_checks():
    print('-- get_version / revert: полный record версии')
    svc = _svc()
    rec1 = {'200': {'a': 'Старое заглавие'}, '700': {'a': 'Толстой'}}
    rec2 = {'200': {'a': 'Новое заглавие'}, '700': {'a': 'Толстой'}}
    svc.snapshot('IBIS', 42, rec1)
    svc.snapshot('IBIS', 42, rec2)
    check('get_version(1) -> исходная запись', svc.get_version('IBIS', 42, 1) == rec1)
    check('get_version(2) -> вторая запись', svc.get_version('IBIS', 42, 2) == rec2)
    check('get_version несуществующей -> None',
          svc.get_version('IBIS', 42, 99) is None)
    # revert — чисто читающее: отдаёт record старой версии для восстановления
    restored = svc.revert('IBIS', 42, 1)
    check('revert отдаёт record старой версии', restored == rec1)
    check('revert ничего не мутирует (история = 2 версии)',
          len(svc.history('IBIS', 42)) == 2)
    check('revert несуществующей -> None', svc.revert('IBIS', 42, 7) is None)


def diff_checks():
    print('-- diff: added / removed / changed по тегам')
    svc = _svc()
    rec1 = {'200': {'a': 'T'}, '210': {'d': '2019'}, '675': '821'}
    rec2 = {'200': {'a': 'T-изменённое'}, '210': {'d': '2019'}, '700': {'a': 'Автор'}}
    svc.snapshot('IBIS', 5, rec1)
    svc.snapshot('IBIS', 5, rec2)
    d = svc.diff('IBIS', 5, 1, 2)
    check('added: 700 (появился)', d['added'] == ['700'])
    check('removed: 675 (исчез)', d['removed'] == ['675'])
    check('changed: 200 (значение изменилось)', d['changed'] == ['200'])
    check('210 не в диффе (не менялось)',
          '210' not in d['added'] + d['removed'] + d['changed'])
    # одинаковые записи -> пустой дифф
    svc.snapshot('IBIS', 6, rec1)
    svc.snapshot('IBIS', 6, dict(rec1))
    dz = svc.diff('IBIS', 6, 1, 2)
    check('идентичные версии -> пустой дифф',
          dz == {'added': [], 'removed': [], 'changed': []})
    # пустое поле трактуется как отсутствие
    de = diff_records({'200': {'a': 'X'}, '300': ''}, {'200': {'a': 'X'}})
    check('пустое поле не считается удалённым', de['removed'] == [])


def merge_checks():
    print('-- merge: непустое побеждает; повторы объединяются без дублей')
    # непустое побеждает пустое
    m1 = merge({'200': {'a': 'Заглавие'}, '210': ''},
               {'200': {'a': 'Заглавие'}, '210': {'d': '2020'}})
    check('непустое значение побеждает пустое', m1['210'] == {'d': '2020'})
    check('одинаковое поле не задвоилось', m1['200'] == {'a': 'Заглавие'})
    # тег только в одной записи -> берётся как есть
    m2 = merge({'700': {'a': 'Толстой'}}, {'701': {'a': 'Иванов'}})
    check('теги из обеих записей присутствуют',
          m2['700'] == {'a': 'Толстой'} and m2['701'] == {'a': 'Иванов'})
    # повторяющиеся поля объединяются без дублей
    m3 = merge({'700': [{'a': 'Толстой'}, {'a': 'Иванов'}]},
               {'700': [{'a': 'Иванов'}, {'a': 'Петров'}]})
    check('повторы объединены, дубль не плодится',
          m3['700'] == [{'a': 'Толстой'}, {'a': 'Иванов'}, {'a': 'Петров'}])
    # полностью совпадающие списки -> один экземпляр без задвоения
    m4 = merge({'700': {'a': 'Толстой'}}, {'700': {'a': 'Толстой'}})
    check('идентичные одиночные -> один инстанс (не список)',
          m4['700'] == {'a': 'Толстой'})
    # пустая запись слева -> результат = правая
    m5 = merge({}, {'200': {'a': 'X'}})
    check('merge с пустой записью отдаёт непустую', m5 == {'200': {'a': 'X'}})
    # порядок: инстансы A, затем новые из B
    m6 = merge({'606': ['история', 'война']}, {'606': ['война', 'мир']})
    check('порядок инстансов A-затем-новые-B',
          m6['606'] == ['история', 'война', 'мир'])


def isolation_checks():
    print('-- изоляция: версии разных (db,mfn) не пересекаются')
    svc = _svc()
    svc.snapshot('IBIS', 1, {'200': {'a': 'A'}})
    svc.snapshot('IBIS', 1, {'200': {'a': 'A2'}})
    svc.snapshot('RDR', 1, {'200': {'a': 'B'}})       # другая БД, тот же mfn
    svc.snapshot('IBIS', 2, {'200': {'a': 'C'}})      # та же БД, другой mfn
    check('(IBIS,1): 2 версии', len(svc.history('IBIS', 1)) == 2)
    check('(RDR,1): 1 версия, нумерация с 1',
          [h['version'] for h in svc.history('RDR', 1)] == [1])
    check('(IBIS,2): 1 версия, нумерация с 1',
          [h['version'] for h in svc.history('IBIS', 2)] == [1])
    check('версии не перепутаны между БД',
          svc.get_version('IBIS', 1, 1) == {'200': {'a': 'A'}}
          and svc.get_version('RDR', 1, 1) == {'200': {'a': 'B'}})


def main():
    snapshot_checks()
    history_checks()
    get_revert_checks()
    diff_checks()
    merge_checks()
    isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
