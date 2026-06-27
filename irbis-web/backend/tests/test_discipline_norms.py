#!/usr/bin/env python3
"""Тесты модели данных «дисциплина <-> издание <-> норматив <-> контингент».

Покрыто (in-memory стор + фиктивные часы, кириллица в названиях/кафедрах):
  * add_discipline + get_discipline (заведение и чтение);
  * set_contingent (обновляет контингент существующей дисциплины);
  * set_norm (upsert: повтор обновляет норму/вид; на неизвестную -> ValueError);
  * norms (список нормативов дисциплины);
  * required_copies = ceil(contingent*norm) для каждого издания;
  * total_required (сумма по изданиям);
  * need с available_map (deficit = max(0, required-available), ноль при покрытии);
  * coverage (частичное покрытие -> дробь; полное -> 1.0; нет норм -> 1.0);
  * remove_norm.

Запуск: py -3.12 tests/test_discipline_norms.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import discipline_norms as dn

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _service():
    """Сервис на in-memory сторе с фиксированными часами (детерминизм)."""
    clock = ['2026-06-27T00:00:00+00:00']
    store = dn.DisciplineStore(':memory:', now=lambda: clock[0])
    return dn.DisciplineNormService(store=store), clock


def discipline_checks():
    print('-- add_discipline / get_discipline / set_contingent')
    svc, clock = _service()
    d = svc.add_discipline('Б1.О.01', 'Философия', department='Кафедра философии',
                           contingent=120)
    check('add_discipline вернул шифр', d['code'] == 'Б1.О.01')
    check('наименование (кириллица)', d['name'] == 'Философия')
    check('кафедра (кириллица)', d['department'] == 'Кафедра философии')
    check('контингент 120', d['contingent'] == 120)
    check('updated_at проставлен', d['updated_at'] == '2026-06-27T00:00:00+00:00')
    got = svc.store.get_discipline('Б1.О.01')
    check('get_discipline читает запись', got is not None and got['name'] == 'Философия')
    check('get_discipline неизвестной -> None',
          svc.store.get_discipline('НЕТ') is None)
    # upsert тем же шифром не плодит дубль
    svc.add_discipline('Б1.О.01', 'Философия науки', contingent=130)
    check('upsert обновил наименование',
          svc.store.get_discipline('Б1.О.01')['name'] == 'Философия науки')
    check('одна запись в list_disciplines', len(svc.store.list_disciplines()) == 1)
    upd = svc.set_contingent('Б1.О.01', 150)
    check('set_contingent обновил контингент', upd['contingent'] == 150)
    check('set_contingent неизвестной -> None',
          svc.set_contingent('НЕТ', 10) is None)


def norm_checks():
    print('-- set_norm: upsert + резолв по code + ValueError + norms')
    svc, _ = _service()
    disc = svc.add_discipline('Б1.О.02', 'История', contingent=100)
    n = svc.set_norm('Б1.О.02', 'BK-1', 0.5, kind='main')
    check('set_norm вернул издание', n['edition_ref'] == 'BK-1')
    check('set_norm kind main', n['kind'] == 'main')
    check('set_norm norma 0.5', n['norm_per_student'] == 0.5)
    svc.set_norm('Б1.О.02', 'BK-2', 0.25, kind='extra')
    check('два норматива у дисциплины',
          len(svc.store.norms(disc['id'])) == 2)
    # upsert: повтор того же издания обновляет норму, не плодит дубль
    n2 = svc.set_norm('Б1.О.02', 'BK-1', 1.0, kind='main')
    check('set_norm upsert обновил норму', n2['norm_per_student'] == 1.0)
    check('upsert не плодит дубль (всё ещё 2)',
          len(svc.store.norms(disc['id'])) == 2)
    # неизвестная дисциплина -> ValueError
    raised = False
    try:
        svc.set_norm('НЕТ', 'BK-9', 0.5)
    except ValueError:
        raised = True
    check('set_norm на неизвестную -> ValueError', raised)


def required_checks():
    print('-- required_copies = ceil(contingent*norm) + total_required')
    svc, _ = _service()
    svc.add_discipline('Б1.О.03', 'Математика', contingent=100)
    svc.set_norm('Б1.О.03', 'BK-1', 0.5, kind='main')   # ceil(100*0.5) = 50
    svc.set_norm('Б1.О.03', 'BK-2', 0.33, kind='extra')  # ceil(100*0.33)=ceil(33)=33
    req = svc.required_copies('Б1.О.03')
    by_ref = {r['edition_ref']: r for r in req}
    check('required BK-1 = 50', by_ref['BK-1']['required'] == 50)
    check('required BK-2 = ceil(33.0) = 33', by_ref['BK-2']['required'] == 33)
    # округление ВВЕРХ: контингент 7, норма 0.3 -> ceil(2.1) = 3
    svc.add_discipline('Б1.О.04', 'Физика', contingent=7)
    svc.set_norm('Б1.О.04', 'BK-3', 0.3)
    check('required ceil(7*0.3=2.1) = 3',
          svc.required_copies('Б1.О.04')[0]['required'] == 3)
    check('total_required = 50+33 = 83', svc.total_required('Б1.О.03') == 83)
    check('required_copies неизвестной -> []',
          svc.required_copies('НЕТ') == [])


def need_coverage_checks():
    print('-- need (deficit) + coverage (дробь / 1.0 / нет норм)')
    svc, _ = _service()
    svc.add_discipline('Б1.О.05', 'Химия', contingent=100)
    svc.set_norm('Б1.О.05', 'BK-1', 0.5)   # required 50
    svc.set_norm('Б1.О.05', 'BK-2', 0.2)   # required 20
    need = svc.need('Б1.О.05', {'BK-1': 30, 'BK-2': 25})
    by_ref = {r['edition_ref']: r for r in need}
    check('need available проброшен', by_ref['BK-1']['available'] == 30)
    check('need deficit = max(0,50-30) = 20', by_ref['BK-1']['deficit'] == 20)
    check('need deficit ноль при покрытии (25>=20)',
          by_ref['BK-2']['deficit'] == 0)
    check('need неизвестной -> []', svc.need('НЕТ', {}) == [])
    # coverage частичное: covered = min(30,50)+min(25,20)=30+20=50; required=70 -> 0.71
    cov = svc.coverage('Б1.О.05', {'BK-1': 30, 'BK-2': 25})
    check('coverage частичное -> 0.71', cov == round(50 / 70, 2))
    # полное покрытие -> 1.0
    check('coverage полное -> 1.0',
          svc.coverage('Б1.О.05', {'BK-1': 50, 'BK-2': 20}) == 1.0)
    # нет норм -> 1.0 (требовать нечего)
    svc.add_discipline('Б1.О.06', 'Биология', contingent=80)
    check('coverage без норм -> 1.0', svc.coverage('Б1.О.06', {}) == 1.0)


def remove_checks():
    print('-- remove_norm')
    svc, _ = _service()
    disc = svc.add_discipline('Б1.О.07', 'Экология', contingent=40)
    svc.set_norm('Б1.О.07', 'BK-1', 0.5)
    check('remove_norm True для существующего',
          svc.store.remove_norm(disc['id'], 'BK-1') is True)
    check('норматив удалён', svc.store.norms(disc['id']) == [])
    check('remove_norm False для отсутствующего',
          svc.store.remove_norm(disc['id'], 'BK-1') is False)


def main():
    discipline_checks()
    norm_checks()
    required_checks()
    need_coverage_checks()
    remove_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
