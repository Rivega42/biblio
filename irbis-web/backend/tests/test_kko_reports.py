#!/usr/bin/env python3
"""Тесты KKO_REPORTS — аналитика коэффициента книгообеспеченности (Кко).

Покрыто (на синтетике из 4 дисциплин: одна ok, одна low, одна critical с
exemplars=0, плюс две на одной кафедре):
  * coefficient — норма, students=0 -> 0.0;
  * deficit — = ceil(students*norm) - exemplars, не отрицательный при профиците;
  * status — ok / low / critical;
  * discipline_provision — рассчитанные поля (coefficient/deficit/required/status);
  * report — сводка (avg_coefficient/total_deficit/by_status/students_total);
  * by_department — rollup по кафедрам;
  * worst — упорядочивание по возрастанию Кко;
  * KkoSnapshotStore — save/get round-trip (кириллица сохранена) + periods.

Запуск: py -3.12 tests/test_kko_reports.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import kko_reports as kr

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Фикстура: 4 дисциплины, кириллица в названиях/кафедрах, норматив 0.5.
#   «Высшая математика»: 100 студ., 60 экз. -> Кко 0.6 >= 0.5 -> ok, дефицит 0.
#   «Физика»:            100 студ., 30 экз. -> Кко 0.3  < 0.5 -> low, дефицит 20.
#   «Философия»:          50 студ.,  0 экз. -> Кко 0.0       -> critical, дефицит 25.
#   «Программирование»:   40 студ., 10 экз. -> Кко 0.25 < 0.5 -> low, дефицит 10.
def fixture():
    return [
        {'discipline': 'Высшая математика', 'department': 'Кафедра математики',
         'students': 100, 'exemplars': 60, 'norm_per_student': 0.5},
        {'discipline': 'Физика', 'department': 'Кафедра физики',
         'students': 100, 'exemplars': 30, 'norm_per_student': 0.5},
        {'discipline': 'Философия', 'department': 'Кафедра философии',
         'students': 50, 'exemplars': 0, 'norm_per_student': 0.5},
        {'discipline': 'Программирование', 'department': 'Кафедра математики',
         'students': 40, 'exemplars': 10, 'norm_per_student': 0.5},
    ]


def coefficient_checks():
    print('-- coefficient: Кко = exemplars / students')
    check('60/100 -> 0.6', kr.coefficient(100, 60) == 0.6)
    check('30/100 -> 0.3', kr.coefficient(100, 30) == 0.3)
    check('округление до 2 знаков (10/3)', kr.coefficient(3, 10) == 3.33)
    check('students=0 -> 0.0', kr.coefficient(0, 50) == 0.0)
    check('students отрицательно -> 0.0', kr.coefficient(-5, 50) == 0.0)
    check('exemplars=0 -> 0.0', kr.coefficient(50, 0) == 0.0)


def deficit_checks():
    print('-- deficit: ceil(students*norm) - exemplars, не отрицательный')
    check('100*0.5-30 -> 20', kr.deficit(100, 30, 0.5) == 20)
    check('50*0.5-0 -> 25', kr.deficit(50, 0, 0.5) == 25)
    check('профицит -> 0 (не минус)', kr.deficit(100, 60, 0.5) == 0)
    check('ceil дробного норматива (33*0.5=16.5 -> 17)',
          kr.deficit(33, 0, 0.5) == 17)


def status_checks():
    print('-- status: ok / low / critical относительно норматива')
    check('Кко >= norm -> ok', kr.status(0.6, 0.5) == 'ok')
    check('Кко == norm -> ok (граница)', kr.status(0.5, 0.5) == 'ok')
    check('0 < Кко < norm -> low', kr.status(0.3, 0.5) == 'low')
    check('Кко == 0 -> critical', kr.status(0.0, 0.5) == 'critical')


def discipline_provision_checks():
    print('-- discipline_provision: исходные поля + рассчитанные')
    p = kr.discipline_provision(fixture()[1])  # Физика
    check('исходное название сохранено', p['discipline'] == 'Физика')
    check('coefficient 0.3', p['coefficient'] == 0.3)
    check('deficit 20', p['deficit'] == 20)
    check('required = ceil(100*0.5) = 50', p['required'] == 50)
    check('status low', p['status'] == 'low')
    crit = kr.discipline_provision(fixture()[2])  # Философия
    check('critical при exemplars=0', crit['status'] == 'critical')
    check('required у critical = 25', crit['required'] == 25)


def report_checks():
    print('-- report: items + summary (avg/total_deficit/by_status/students_total)')
    rep = kr.report(fixture())
    s = rep['summary']
    check('4 карточки в items', len(rep['items']) == 4)
    check('disciplines 4', s['disciplines'] == 4)
    # avg = (0.6 + 0.3 + 0.0 + 0.25) / 4 = 0.2875 -> 0.29
    check('avg_coefficient 0.29', s['avg_coefficient'] == 0.29)
    # дефициты: 0 + 20 + 25 + 10 = 55
    check('total_deficit 55', s['total_deficit'] == 55)
    check('by_status ok=1', s['by_status']['ok'] == 1)
    check('by_status low=2', s['by_status']['low'] == 2)
    check('by_status critical=1', s['by_status']['critical'] == 1)
    check('students_total 290', s['students_total'] == 290)
    empty = kr.report([])
    check('пустой отчёт: avg 0.0, disciplines 0',
          empty['summary']['avg_coefficient'] == 0.0
          and empty['summary']['disciplines'] == 0)


def by_department_checks():
    print('-- by_department: rollup по кафедрам')
    dept = kr.by_department(fixture())
    check('3 кафедры', len(dept) == 3)
    math_d = dept['Кафедра математики']
    check('математика: 2 дисциплины', math_d['disciplines'] == 2)
    # avg = (0.6 + 0.25) / 2 = 0.425 -> 0.42 (банковское round)
    check('математика: avg_coefficient округлён', math_d['avg_coefficient'] == 0.42)
    check('математика: total_deficit 10 (0 + 10)', math_d['total_deficit'] == 10)
    check('философия: total_deficit 25',
          dept['Кафедра философии']['total_deficit'] == 25)


def worst_checks():
    print('-- worst: упорядочивание по возрастанию Кко')
    w = kr.worst(fixture())
    check('первой идёт худшая (Философия, Кко 0.0)',
          w[0]['discipline'] == 'Философия')
    check('коэффициенты по возрастанию',
          [x['coefficient'] for x in w] == [0.0, 0.25, 0.3, 0.6])
    check('worst(n=2) -> 2 позиции', len(kr.worst(fixture(), n=2)) == 2)
    check('две худшие — Философия и Программирование',
          [x['discipline'] for x in kr.worst(fixture(), n=2)]
          == ['Философия', 'Программирование'])


def snapshot_store_checks():
    print('-- KkoSnapshotStore: save/get round-trip + periods (in-memory)')
    store = kr.KkoSnapshotStore(':memory:', now=lambda: '2026-06-27T00:00:00')
    rep = kr.report(fixture())
    saved = store.save('2026-Q2', rep)
    check('save вернул строку с period', saved['period'] == '2026-Q2')
    check('save проставил created_at', saved['created_at'] == '2026-06-27T00:00:00')
    got = store.get('2026-Q2')
    check('get вернул отчёт', got is not None)
    check('round-trip: total_deficit совпал',
          got['summary']['total_deficit'] == rep['summary']['total_deficit'])
    check('round-trip: кириллица сохранена',
          got['items'][0]['discipline'] == 'Высшая математика')
    check('get несуществующего периода -> None', store.get('1999') is None)
    store.save('2026-Q1', rep)
    check('periods отсортированы по возрастанию',
          store.periods() == ['2026-Q1', '2026-Q2'])
    # UPSERT: повторный save того же периода замещает, не дублирует.
    store.save('2026-Q2', kr.report([]))
    check('UPSERT не плодит периоды', store.periods() == ['2026-Q1', '2026-Q2'])
    check('UPSERT заместил содержимое',
          store.get('2026-Q2')['summary']['disciplines'] == 0)


def main():
    coefficient_checks()
    deficit_checks()
    status_checks()
    discipline_provision_checks()
    report_checks()
    by_department_checks()
    worst_checks()
    snapshot_store_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
