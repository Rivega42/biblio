#!/usr/bin/env python3
"""Тесты DEDUP — детект дублей записей каталога (контур Каталогизатор).

Покрыто:
  * `dedup_key`: приоритет ISBN(10^a) > шифр(903) > нормализованный title|year;
    устойчивый парсинг (скаляр/dict/список), нормализация ISBN/кириллицы/регистра;
  * `find_duplicates`: кластер из 2+ по одинаковому ISBN; разные книги -> нет кластеров;
  * `is_duplicate`: дубль -> индекс существующей; новая запись -> None;
  * `cluster_map`: все кластеры (включая одиночные), idx = позиция в наборе;
  * `dedup_stats`: total / unique_keys / duplicate_clusters / duplicate_records;
  * пустой набор -> пусто / нули.

Запуск: py -3.12 tests/test_dedup.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.dedup import (
    dedup_key, find_duplicates, is_duplicate, cluster_map, dedup_stats,
    _field_value, _norm_isbn,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _rec(isbn=None, shifr=None, title=None, year=None):
    """Собрать НАШУ tag-keyed запись из удобных полей."""
    rec = {}
    if isbn is not None:
        rec['10'] = {'a': isbn}
    if shifr is not None:
        rec['903'] = shifr
    if title is not None:
        rec['200'] = {'a': title}
    if year is not None:
        rec['210'] = {'d': year}
    return rec


def dedup_key_checks():
    print('-- dedup_key: приоритет ISBN > шифр > title|year + парсинг')
    check('ключ по ISBN (10^a)',
          dedup_key(_rec(isbn='978-5-7038-1234-5', shifr='X1',
                         title='T', year='2020')) == 'isbn:9785703812345')
    check('ISBN нормализуется (дефисы/пробелы/X)',
          dedup_key(_rec(isbn='5-94157-x')) == 'isbn:594157X')
    check('нет ISBN -> ключ по шифру (903)',
          dedup_key(_rec(shifr='Ш-77', title='T', year='2020')) == 'shifr:Ш-77')
    check('нет ISBN/шифра -> ключ по title|year (кириллица/регистр)',
          dedup_key(_rec(title='Война  И  МИР', year='2020'))
          == 'ty:война и мир|2020')
    # устойчивый парсинг разных форм поля
    check('поле-скаляр читается', _field_value({'903': 'S1'}, '903') == 'S1')
    check('поле-список читается',
          _field_value({'10': [{'a': 'A1'}, {'a': 'A2'}]}, '10', 'a') == 'A1')
    check('подполе регистронезависимо',
          _field_value({'200': {'A': 'Hi'}}, '200', 'a') == 'Hi')
    check('_norm_isbn чистит до цифр/X',
          _norm_isbn('978 5 7038-1234x') == '978570381234X')


def find_duplicates_checks():
    print('-- find_duplicates: кластер из 2+ по одинаковому ISBN')
    recs = [
        _rec(isbn='978-5-00000-001-1', title='Алгоритмы', year='2019'),  # 0
        _rec(isbn='000-0', title='Компиляторы', year='2018'),            # 1
        _rec(isbn='978-5-00000-001-1', title='Алгоритмы', year='2019'),  # 1 дубль 0
    ]
    dups = find_duplicates(recs)
    check('найден ровно один кластер дублей', len(dups) == 1)
    check('кластер по ISBN-ключу',
          dups[0]['key'] == 'isbn:9785000000011')
    check('в кластере участники 0 и 2', dups[0]['members'] == [0, 2])

    print('-- find_duplicates: разные книги -> нет кластеров')
    distinct = [_rec(isbn='111-1'), _rec(isbn='222-2'), _rec(isbn='333-3')]
    check('три разных ISBN -> кластеров дублей нет',
          find_duplicates(distinct) == [])

    print('-- find_duplicates: дубль по шифру и по title|year')
    by_shifr = [_rec(shifr='Ш-1'), _rec(shifr='Ш-1'), _rec(shifr='Ш-2')]
    check('дубль по шифру (903) -> кластер [0,1]',
          find_duplicates(by_shifr) == [{'key': 'shifr:Ш-1',
                                         'members': [0, 1]}])
    by_ty = [_rec(title='ОС', year='2017'), _rec(title='ос', year='2017')]
    check('дубль по нормализ. title|year (регистр)',
          find_duplicates(by_ty) == [{'key': 'ty:ос|2017', 'members': [0, 1]}])


def is_duplicate_checks():
    print('-- is_duplicate: copy-cataloging (дубль -> индекс / новая -> None)')
    existing = [
        _rec(isbn='978-5-99999-000-0', title='Базы данных', year='2018'),  # 0
        _rec(isbn='000-0', title='Компиляторы', year='2018'),              # 1
    ]
    dup = _rec(isbn='978 5 99999 000 0', title='Базы данных (изд. 2)')
    check('дубль существующей -> её индекс',
          is_duplicate(dup, existing) == 0)
    fresh = _rec(isbn='978-5-12345-000-0', title='Сети', year='2021')
    check('новая запись -> None', is_duplicate(fresh, existing) is None)
    check('дубль второй записи -> индекс 1',
          is_duplicate(_rec(isbn='000-0'), existing) == 1)
    check('пустой каталог -> None (всё новое)',
          is_duplicate(fresh, []) is None)


def cluster_map_checks():
    print('-- cluster_map: все кластеры включая одиночные, idx = позиция')
    recs = [
        _rec(isbn='978-5-00000-001-1'),   # 0
        _rec(isbn='978-5-00000-001-1'),   # 1 дубль 0
        _rec(isbn='222-2'),               # 2 одиночка
    ]
    cm = cluster_map(recs)
    check('два различных ключа', len(cm) == 2)
    check('кластер дублей содержит 0 и 1',
          cm['isbn:9785000000011'] == [0, 1])
    check('одиночный ключ присутствует', cm['isbn:2222'] == [2])


def dedup_stats_checks():
    print('-- dedup_stats: total / unique_keys / duplicate_clusters / dup_records')
    recs = [
        _rec(isbn='978-5-77777-000-0', title='ОС', year='2017'),  # 0
        _rec(isbn='978-5-77777-000-0', title='ОС', year='2017'),  # 1 дубль 0
        _rec(isbn='978-5-77777-000-0', title='ОС', year='2017'),  # 2 дубль 0
        _rec(isbn='222-2', title='Компиляторы', year='2018'),     # 3 одиночка
    ]
    st = dedup_stats(recs)
    check('total = 4', st['total'] == 4)
    check('unique_keys = 2', st['unique_keys'] == 2)
    check('duplicate_clusters = 1', st['duplicate_clusters'] == 1)
    check('duplicate_records = total - unique = 2',
          st['duplicate_records'] == 2)


def empty_checks():
    print('-- пустой набор: всё пусто / нули')
    check('find_duplicates([]) -> []', find_duplicates([]) == [])
    check('cluster_map([]) -> {}', cluster_map([]) == {})
    st = dedup_stats([])
    check('dedup_stats([]) -> все нули',
          st == {'total': 0, 'unique_keys': 0,
                 'duplicate_clusters': 0, 'duplicate_records': 0})


def main():
    dedup_key_checks()
    find_duplicates_checks()
    is_duplicate_checks()
    cluster_map_checks()
    dedup_stats_checks()
    empty_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
