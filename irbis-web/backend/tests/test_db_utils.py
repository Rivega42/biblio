#!/usr/bin/env python3
"""Тесты DB_UTILS — инструментарий АРМ «Утилиты» (статистика/выгрузки/обслуживание).

Покрыто (на синтетике — 4 записи с кириллицей, общим ISBN и разными годами/типами):
  * `stats` — count / by_type (920) / by_year (210^d) / by_language (101^a) /
    with_exemplars (910) / avg_fields;
  * `fund_summary` — total_exemplars и разрезы by_status (910^a) / by_location (910^d);
  * `export_json` — round-trip через json.loads + сохранение кириллицы;
  * `export_csv` — заголовок, значения подполей и пустая ячейка для отсутствующего тега;
  * `field_histogram` / `field_histogram_sorted` — счётчик тегов и порядок;
  * `duplicate_keys` — общий ISBN найден, уникальные исключены;
  * `validate_batch` — флаг отсутствующих обязательных тегов, полные записи пропущены.

Запуск: py -3.12 tests/test_db_utils.py ; в агрегаторе test_access.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import db_utils as du

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Синтетический фонд: 4 записи.
#   rec1, rec2 — общий ISBN '978-5-1' (дубль); rec3 — свой ISBN; rec4 — без ISBN.
#   типы 920: PAZK x2, ASP, SPEC; годы 2021 x2, 2019; языки rus x3, eng.
#   экземпляры 910: rec1 — 2 (status '0' loc 'ЧЗ' + status 'u' loc 'АБ'),
#   rec2 — 1 (status '0' loc 'ЧЗ'); rec3/rec4 — без экземпляров.
# --------------------------------------------------------------------------- #
def fixture():
    rec1 = {'mfn': 1, 'fields': [
        {'tag': '920', 'value': 'PAZK'},
        {'tag': '101', 'subfields': [{'code': 'a', 'value': 'rus'}]},
        {'tag': '200', 'subfields': [{'code': 'a', 'value': 'Война и мир'}]},
        {'tag': '210', 'subfields': [{'code': 'd', 'value': '2021'}]},
        {'tag': '700', 'subfields': [{'code': 'a', 'value': 'Толстой'}]},
        {'tag': '10', 'subfields': [{'code': 'a', 'value': '978-5-1'}]},
        {'tag': '910', 'subfields': [{'code': 'a', 'value': '0'},
                                     {'code': 'd', 'value': 'ЧЗ'}]},
        {'tag': '910', 'subfields': [{'code': 'a', 'value': 'u'},
                                     {'code': 'd', 'value': 'АБ'}]},
    ]}
    rec2 = {'mfn': 2, 'fields': [
        {'tag': '920', 'value': 'PAZK'},
        {'tag': '101', 'subfields': [{'code': 'a', 'value': 'rus'}]},
        {'tag': '200', 'subfields': [{'code': 'a', 'value': 'Анна Каренина'}]},
        {'tag': '210', 'subfields': [{'code': 'd', 'value': 'c2021'}]},
        {'tag': '700', 'subfields': [{'code': 'a', 'value': 'Толстой'}]},
        {'tag': '10', 'subfields': [{'code': 'a', 'value': '978-5-1'}]},
        {'tag': '910', 'subfields': [{'code': 'a', 'value': '0'},
                                     {'code': 'd', 'value': 'ЧЗ'}]},
    ]}
    rec3 = {'mfn': 3, 'fields': [
        {'tag': '920', 'value': 'ASP'},
        {'tag': '101', 'subfields': [{'code': 'a', 'value': 'rus'}]},
        {'tag': '200', 'subfields': [{'code': 'a', 'value': 'Журнал'}]},
        {'tag': '210', 'subfields': [{'code': 'd', 'value': '[2019]'}]},
        {'tag': '10', 'subfields': [{'code': 'a', 'value': '978-5-9'}]},
    ]}
    # rec4 — без 920? нет: даём редкий тип SPEC, eng, без 210^d, без ISBN, без 910.
    rec4 = {'mfn': 4, 'fields': [
        {'tag': '920', 'value': 'SPEC'},
        {'tag': '101', 'subfields': [{'code': 'a', 'value': 'eng'}]},
        {'tag': '200', 'subfields': [{'code': 'a', 'value': 'Notes'}]},
    ]}
    return [rec1, rec2, rec3, rec4]


def stats_checks():
    print('-- stats: count / by_type / by_year / by_language / exemplars / avg')
    s = du.stats(fixture())
    check('count 4', s['count'] == 4)
    check('by_type PAZK 2', s['by_type'].get('PAZK') == 2)
    check('by_type ASP 1', s['by_type'].get('ASP') == 1)
    check('by_type SPEC 1', s['by_type'].get('SPEC') == 1)
    check('by_year 2021 -> 2 (вкл. c2021)', s['by_year'].get('2021') == 2)
    check('by_year 2019 -> 1 (из [2019])', s['by_year'].get('2019') == 1)
    check('by_language rus 3', s['by_language'].get('rus') == 3)
    check('by_language eng 1', s['by_language'].get('eng') == 1)
    check('with_exemplars 2 (rec1, rec2)', s['with_exemplars'] == 2)
    # поля: rec1=8, rec2=7, rec3=5, rec4=3 -> 23/4 = 5.75
    check('avg_fields 5.75', abs(s['avg_fields'] - 5.75) < 1e-9)
    se = du.stats([])
    check('пустой список -> count 0', se['count'] == 0)
    check('пустой список -> avg_fields 0.0', se['avg_fields'] == 0.0)
    check('пустой список -> by_type {}', se['by_type'] == {})


def fund_checks():
    print('-- fund_summary: экземпляры 910 (status ^a / location ^d)')
    f = du.fund_summary(fixture())
    check('total_exemplars 3', f['total_exemplars'] == 3)
    check('by_status 0 -> 2', f['by_status'].get('0') == 2)
    check('by_status u -> 1', f['by_status'].get('u') == 1)
    check('by_location ЧЗ -> 2', f['by_location'].get('ЧЗ') == 2)
    check('by_location АБ -> 1', f['by_location'].get('АБ') == 1)
    fe = du.fund_summary([])
    check('пусто -> total 0', fe['total_exemplars'] == 0)


def export_checks():
    print('-- export_json / export_csv')
    recs = fixture()
    js = du.export_json(recs)
    check('export_json round-trip', json.loads(js) == recs)
    check('export_json сохраняет кириллицу (не \\uXXXX)', 'Война и мир' in js)
    check('export_json без ASCII-эскейпа', '\\u' not in js)

    csv_text = du.export_csv(recs, ['920', '200^a', '210^d'])
    lines = csv_text.strip().split('\n')
    check('csv заголовок = спецификации', lines[0] == '920,200^a,210^d')
    check('csv строк = 1 заголовок + 4 записи', len(lines) == 5)
    check('csv первая запись 920/200^a',
          lines[1] == 'PAZK,Война и мир,2021')
    # rec4 не имеет 210^d -> пустая ячейка в конце строки
    check('csv пустая ячейка для отсутствующего 210^d у rec4',
          lines[4] == 'SPEC,Notes,')
    # отсутствующее подполе/тег целиком -> пустая ячейка
    csv2 = du.export_csv(recs[3:4], ['999', '700^a'])
    check('csv отсутствующий тег/подполе -> пустые ячейки',
          csv2.strip().split('\n')[1] == ',')


def histogram_checks():
    print('-- field_histogram / field_histogram_sorted')
    h = du.field_histogram(fixture())
    check('hist 920 = 4', h.get('920') == 4)
    check('hist 910 = 3 (повторы учтены)', h.get('910') == 3)
    check('hist 10 (ISBN) = 3', h.get('10') == 3)
    check('hist 700 = 2', h.get('700') == 2)
    check('hist пустой список -> {}', du.field_histogram([]) == {})
    sorted_h = du.field_histogram_sorted(fixture())
    # теги 101/200/920 встречаются по 4 раза; при равном счётчике -> по тегу asc.
    check('sorted[0] = (101, 4): макс. счётчик, тег asc при равенстве',
          sorted_h[0] == ('101', 4))
    check('первые три равны 4 и отсортированы по тегу',
          [t for t, c in sorted_h[:3]] == ['101', '200', '920'])
    # счётчики не возрастают по списку
    counts = [c for _t, c in sorted_h]
    check('sorted по убыванию счётчика', counts == sorted(counts, reverse=True))


def duplicate_checks():
    print('-- duplicate_keys: дубли по ISBN (10^a)')
    d = du.duplicate_keys(fixture(), '10^a')
    check('общий ISBN 978-5-1 найден', '978-5-1' in d)
    check('дубль ISBN -> mfn [1, 2]', d.get('978-5-1') == [1, 2])
    check('уникальный ISBN 978-5-9 исключён', '978-5-9' not in d)
    check('запись без ISBN не создаёт ключ', None not in d)
    check('пустой список -> {}', du.duplicate_keys([], '10^a') == {})


def validate_checks():
    print('-- validate_batch: обязательные теги (ФЛК-lite)')
    recs = fixture()
    # требуем 920 (есть у всех) и 700 (нет у rec3, rec4)
    bad = du.validate_batch(recs, ['920', '700'])
    by_mfn = {b['mfn']: b['missing'] for b in bad}
    check('rec3 без 700 помечен', by_mfn.get(3) == ['700'])
    check('rec4 без 700 помечен', by_mfn.get(4) == ['700'])
    check('rec1 (полная) НЕ в списке', 1 not in by_mfn)
    check('rec2 (полная) НЕ в списке', 2 not in by_mfn)
    check('только 2 записи помечены', len(bad) == 2)
    # требуем только 920 -> все полны
    check('все имеют 920 -> пусто', du.validate_batch(recs, ['920']) == [])
    # несколько отсутствующих тегов в порядке required
    bad2 = du.validate_batch([recs[3]], ['700', '210', '920'])
    check('missing в порядке required', bad2[0]['missing'] == ['700', '210'])


def main():
    stats_checks()
    fund_checks()
    export_checks()
    histogram_checks()
    duplicate_checks()
    validate_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
