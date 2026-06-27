#!/usr/bin/env python3
"""Тесты ребра 5.3 — КСУ «Пополнение записи» (авто-распределение партии).

Покрыто:
  * `distribute`: число наименований (17) == len(items), Σ экземпляров (copies);
    агрегаты by_section (44-49), by_type / by_language (45), printed/non_printed
    (145-150 / 18-19); инвариант Σ-по-граням == общим titles/copies; пустой раздел/
    тип/язык собираются в явную корзину "(не указано)";
  * пустой список -> все счётчики нули;
  * `KsuAutoService.compute` — расчёт без записи; `compute_and_store` идемпотентен
    по ksu_no (повтор обновляет снимок, не плодит строк); `get` / `list_ksu`.

Запуск: py -3.12 tests/test_ksu_auto.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.ksu_auto import (
    distribute, KsuAutoStore, KsuAutoService, UNSPECIFIED,
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


def _batch():
    """Партия из 4 наименований (две по разделам/типам/языкам, печ./непеч.)."""
    return [
        {'section': 'A', 'doc_type': 'book', 'language': 'rus',
         'printed': True, 'copies': 3},
        {'section': 'A', 'doc_type': 'book', 'language': 'eng',
         'printed': True, 'copies': 2},
        {'section': 'B', 'doc_type': 'periodical', 'language': 'rus',
         'printed': True, 'copies': 5},
        {'section': 'B', 'doc_type': 'eresource', 'language': 'rus',
         'printed': False, 'copies': 1},
    ]


def distribute_totals_checks():
    print('-- 5.3: distribute считает titles (17) и copies')
    d = distribute(_batch())
    check('titles == число наименований (4)', d['titles'] == 4)
    check('copies == Σ экземпляров (11)', d['copies'] == 11)


def distribute_facets_checks():
    print('-- 5.3: by_section / by_type / by_language агрегаты')
    d = distribute(_batch())
    check('by_section[A] = 2 наим. / 5 экз.',
          d['by_section']['A'] == {'titles': 2, 'copies': 5})
    check('by_section[B] = 2 наим. / 6 экз.',
          d['by_section']['B'] == {'titles': 2, 'copies': 6})
    check('by_type[book] = 2 / 5', d['by_type']['book'] == {'titles': 2, 'copies': 5})
    check('by_type[periodical] = 1 / 5',
          d['by_type']['periodical'] == {'titles': 1, 'copies': 5})
    check('by_language[rus] = 3 / 9',
          d['by_language']['rus'] == {'titles': 3, 'copies': 9})
    check('by_language[eng] = 1 / 2',
          d['by_language']['eng'] == {'titles': 1, 'copies': 2})

    # Инвариант: Σ по любой грани == общим titles/copies.
    for facet in ('by_section', 'by_type', 'by_language'):
        st = sum(c['titles'] for c in d[facet].values())
        sc = sum(c['copies'] for c in d[facet].values())
        check('Σ %s == titles/copies' % facet, st == d['titles'] and sc == d['copies'])


def distribute_printed_checks():
    print('-- 5.3: printed / non_printed (145-150 / 18-19)')
    d = distribute(_batch())
    check('printed = 3 наим. / 10 экз.',
          d['printed'] == {'titles': 3, 'copies': 10})
    check('non_printed = 1 наим. / 1 экз.',
          d['non_printed'] == {'titles': 1, 'copies': 1})
    check('printed+non_printed titles == titles (4)',
          d['printed']['titles'] + d['non_printed']['titles'] == d['titles'])
    check('printed+non_printed copies == copies (11)',
          d['printed']['copies'] + d['non_printed']['copies'] == d['copies'])


def distribute_edge_checks():
    print('-- 5.3: пустой список -> нули; пустой атрибут -> корзина "(не указано)"')
    z = distribute([])
    check('пустой: titles 0', z['titles'] == 0)
    check('пустой: copies 0', z['copies'] == 0)
    check('пустой: by_section пуст', z['by_section'] == {})
    check('пустой: printed нули', z['printed'] == {'titles': 0, 'copies': 0})
    check('None == []', distribute(None)['titles'] == 0)

    # default printed=True; пустой раздел/тип/язык -> UNSPECIFIED.
    d = distribute([{'copies': 4}])
    check('одна строка без атрибутов -> 1 наим. / 4 экз.',
          d['titles'] == 1 and d['copies'] == 4)
    check('пустой раздел -> корзина UNSPECIFIED',
          d['by_section'][UNSPECIFIED] == {'titles': 1, 'copies': 4})
    check('printed по умолчанию True', d['printed'] == {'titles': 1, 'copies': 4})

    # отсутствующий copies трактуется как 0 (наименование без экземпляров).
    d2 = distribute([{'section': 'A'}])
    check('нет copies -> 0 экз. при 1 наим.',
          d2['titles'] == 1 and d2['copies'] == 0)


def service_compute_checks():
    print('-- 5.3: KsuAutoService.compute (без записи)')
    svc = KsuAutoService(KsuAutoStore(':memory:'))
    d = svc.compute(_batch())
    check('compute == distribute (titles 4)', d['titles'] == 4 and d['copies'] == 11)
    check('compute не пишет в стор', svc.list_ksu() == [])


def service_store_checks():
    print('-- 5.3: compute_and_store идемпотентен по ksu_no; get / list')
    clock = [1000.0]
    svc = KsuAutoService(KsuAutoStore(':memory:'), now=lambda: clock[0])
    d = svc.compute_and_store('2026/0001', _batch())
    check('compute_and_store вернул сводку', d['titles'] == 4 and d['copies'] == 11)

    snap = svc.get('2026/0001')
    check('get: снимок сохранён', snap is not None)
    check('get: distribution == сводка', snap['distribution']['copies'] == 11)
    check('get: created_at == now (1000)', snap['created_at'] == 1000.0)
    check('list_ksu = [2026/0001]', svc.list_ksu() == ['2026/0001'])
    check('get неизвестного КСУ -> None', svc.get('NOPE') is None)

    # Идемпотентность: повтор по тому же ksu_no обновляет снимок, не плодит строк.
    clock[0] = 2000.0
    svc.compute_and_store('2026/0001', [{'section': 'X', 'copies': 7}])
    check('list_ksu всё ещё 1 строка', svc.list_ksu() == ['2026/0001'])
    snap2 = svc.get('2026/0001')
    check('снимок обновлён (titles 1 / copies 7)',
          snap2['distribution']['titles'] == 1 and snap2['distribution']['copies'] == 7)
    check('created_at обновлён (2000)', snap2['created_at'] == 2000.0)

    # Второй номер КСУ — отдельный снимок.
    svc.compute_and_store('2026/0002', _batch())
    check('list_ksu = два номера', svc.list_ksu() == ['2026/0001', '2026/0002'])


def persistence_checks():
    print('-- 5.3: персист снимка переживает новое соединение (файл-стор)')
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    try:
        svc = KsuAutoService(KsuAutoStore(path), now=lambda: 5.0)
        svc.compute_and_store('K-1', _batch())
        svc2 = KsuAutoService(KsuAutoStore(path))   # новый стор/соединение
        snap = svc2.get('K-1')
        check('снимок прочитан из файла', snap is not None and
              snap['distribution']['copies'] == 11)
        check('list_ksu из файла = [K-1]', svc2.list_ksu() == ['K-1'])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main():
    distribute_totals_checks()
    distribute_facets_checks()
    distribute_printed_checks()
    distribute_edge_checks()
    service_compute_checks()
    service_store_checks()
    persistence_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
