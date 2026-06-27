#!/usr/bin/env python3
"""Тесты per-student enrollment книгообеспеченности — рёбра 4.2/4.3/10.3.

Закрывает шов «студент ↔ дисциплина» (RDR поле 90 контингент / 69 изучаемые
дисциплины), которого не было (была только агрегатная модель контингента-счётчика):
  * 4.2 — `enroll`/`unenroll` (per-student связь студент↔дисциплина);
  * 10.3 — `student_disciplines` (студент видит свои дисциплины в ЛК);
  * 4.2/4.3 — `sync_contingent_from_enrollments` (контингент дисциплины ← фактические
    записи студентов, source='rdr', вместо ручного 68^Z).

Запуск: py -3.12 tests/test_bp_enrollment.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.bookprovision import BookProvisionEngine, BookProvisionError

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _eng_with_disc():
    eng = BookProvisionEngine(':memory:')
    fac = eng.add_faculty('ФКН', 'Факультет КН')
    spec = eng.add_specialty(fac, napr='09.03.04', spec='ПИ')
    d1 = eng.add_discipline(spec, 'D-1', name='Театроведение')
    d2 = eng.add_discipline(spec, 'D-2', name='История театра')
    return eng, d1, d2


def enroll_checks():
    print('-- 4.2: enroll / unenroll (студент ↔ дисциплина, идемпотентно)')
    eng, d1, d2 = _eng_with_disc()
    eid = eng.enroll('111', d1)
    check('enroll вернул id', isinstance(eid, int))
    check('enroll идемпотентен', eng.enroll('111', d1) == eid)
    check('на D-1 записан 1', eng.enrolled_count(d1) == 1)
    check('unenroll True', eng.unenroll('111', d1) is True)
    check('после unenroll D-1 = 0', eng.enrolled_count(d1) == 0)
    check('unenroll повторно -> False', eng.unenroll('111', d1) is False)

    bad = False
    try:
        eng.enroll('111', 99999)
    except BookProvisionError:
        bad = True
    check('enroll на несуществующую дисциплину -> error', bad)
    bad2 = False
    try:
        eng.enroll('', d1)
    except BookProvisionError:
        bad2 = True
    check('enroll без студента -> error', bad2)


def student_disciplines_checks():
    print('-- 10.3: студент видит свои дисциплины (ЛК)')
    eng, d1, d2 = _eng_with_disc()
    eng.enroll('111', d1)
    eng.enroll('111', d2)
    eng.enroll('222', d1)
    d111 = eng.student_disciplines('111')
    check('студент 111 -> 2 дисциплины', len(d111) == 2)
    check('дисциплины несут disc_id', {d['disc_id'] for d in d111} == {'D-1', 'D-2'})
    check('дисциплины несут имя', any(d['name'] == 'Театроведение' for d in d111))
    check('студент 222 -> 1', len(eng.student_disciplines('222')) == 1)
    check('изоляция: неизвестный студент -> []', eng.student_disciplines('999') == [])


def sync_contingent_checks():
    print('-- 4.2/4.3: контингент дисциплины ← фактические записи (source=rdr)')
    eng, d1, d2 = _eng_with_disc()
    eng.enroll('111', d1)
    eng.enroll('222', d1)
    eng.enroll('333', d1)
    n = eng.sync_contingent_from_enrollments(d1)
    check('sync вернул 3', n == 3)
    row = eng._conn().execute(
        'SELECT students, students_source FROM bp_discipline WHERE id=?',
        (d1,)).fetchone()
    check('bp_discipline.students = 3 (из записей)', row['students'] == 3)
    check("students_source = 'rdr'", row['students_source'] == 'rdr')
    # на D-2 нет записей -> контингент 0
    check('sync пустой -> 0', eng.sync_contingent_from_enrollments(d2) == 0)


def main():
    enroll_checks()
    student_disciplines_checks()
    sync_contingent_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
