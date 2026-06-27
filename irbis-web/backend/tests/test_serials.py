#!/usr/bin/env python3
"""Тесты рёбер 9.2/9.3 — сериальная иерархия: периодика и многотомники.

Покрыто:
  * 9.2 журнал <-> номер (461/46): register журнала + add_issue нескольких
    номеров образуют иерархию под одной сводной записью;
  * 9.3 многотомник <-> том (481/963): register многотомника + add_issue томов;
  * идемпотентность add_issue по (serial, number, year, volume) — повтор не
    задваивает выпуск;
  * issues хронологичны (по году/тому/номеру);
  * find по подстроке заглавия (кириллица — фильтр в Python);
  * stats {serials, issues, journals, multivolumes};
  * get несуществующего сериала -> None; add_issue в несуществующий -> None;
    неизвестный kind -> ValueError.

Запуск: py -3.12 tests/test_serials.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.serials import SerialsService, SerialsStore

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


def journal_checks():
    print('-- 9.2: журнал <-> номер (461/46)')
    svc = SerialsService(SerialsStore(':memory:'))
    j = svc.register('journal', 'Библиотечное дело', issn='1234-5678',
                     shifr='БД', source_mfn=10)
    check('журнал заведён', j['kind'] == 'journal'
          and j['title'] == 'Библиотечное дело' and j['issn'] == '1234-5678')
    svc.add_issue(j['id'], number='3', year='2023', source_mfn=101)
    svc.add_issue(j['id'], number='1', year='2023', source_mfn=102)
    svc.add_issue(j['id'], number='2', year='2024', source_mfn=103)
    iss = svc.issues(j['id'])
    check('три номера под сводной записью', len(iss) == 3)
    check('все номера ссылаются на журнал (461)',
          all(i['serial'] == j['id'] for i in iss))
    check('номера хронологичны (2023#1, 2023#3, 2024#2)',
          [(i['year'], i['number']) for i in iss]
          == [('2023', '1'), ('2023', '3'), ('2024', '2')])


def multivolume_checks():
    print('-- 9.3: многотомник <-> том (481/963)')
    svc = SerialsService(SerialsStore(':memory:'))
    m = svc.register('multivolume', 'Война и мир', shifr='ВМ')
    check('многотомник заведён',
          m['kind'] == 'multivolume' and m['issn'] is None)
    svc.add_issue(m['id'], volume='1', year='1869')
    svc.add_issue(m['id'], volume='2', year='1869')
    svc.add_issue(m['id'], volume='3', year='1869')
    vols = svc.issues(m['id'])
    check('три тома под сводной записью', len(vols) == 3)
    check('тома несут обозначение 963', [v['volume'] for v in vols]
          == ['1', '2', '3'])
    g = svc.get(m['id'])
    check('get -> сериал + число выпусков (3)', g['issues_count'] == 3)


def idempotent_checks():
    print('-- идемпотентный add_issue (повтор не задваивает)')
    svc = SerialsService(SerialsStore(':memory:'))
    j = svc.register('journal', 'Знание - сила')
    a = svc.add_issue(j['id'], number='5', year='2020')
    b = svc.add_issue(j['id'], number='5', year='2020')
    check('повтор (number,year) вернул тот же выпуск', a['id'] == b['id'])
    check('задвоения нет (1 выпуск)', len(svc.issues(j['id'])) == 1)
    svc.add_issue(j['id'], number='6', year='2020')
    check('иной номер добавлен (2 выпуска)', len(svc.issues(j['id'])) == 2)


def find_stats_checks():
    print('-- find по заглавию + stats')
    svc = SerialsService(SerialsStore(':memory:'))
    j1 = svc.register('journal', 'Библиотека и общество')
    j2 = svc.register('journal', 'Научный мир')
    m1 = svc.register('multivolume', 'Большая библиотека')
    svc.add_issue(j1['id'], number='1', year='2021')
    svc.add_issue(j1['id'], number='2', year='2021')
    svc.add_issue(m1['id'], volume='1')

    hits = svc.find('библиотек')          # кириллица, нижний регистр
    titles = sorted(h['title'] for h in hits)
    check('find подстрокой (кириллица, регистр) -> 2',
          titles == ['Библиотека и общество', 'Большая библиотека'])
    check('find несёт число выпусков',
          any(h['title'] == 'Библиотека и общество' and h['issues_count'] == 2
              for h in hits))
    check('find без совпадений -> []', svc.find('xyz-нет-такого') == [])

    st = svc.stats()
    check('stats serials=3', st['serials'] == 3)
    check('stats journals=2, multivolumes=1',
          st['journals'] == 2 and st['multivolumes'] == 1)
    check('stats issues=3', st['issues'] == 3)
    # глушим неиспользованную ссылку j2 явной проверкой
    check('второй журнал отдельной записью', j2['id'] != j1['id'])


def edge_checks():
    print('-- граничные случаи')
    svc = SerialsService(SerialsStore(':memory:'))
    check('get несуществующего -> None', svc.get(999) is None)
    check('add_issue в несуществующий -> None',
          svc.add_issue(999, number='1') is None)
    bad = False
    try:
        svc.register('nonsense', 'X')
    except ValueError:
        bad = True
    check('неизвестный kind -> ValueError', bad)


def main():
    journal_checks()
    multivolume_checks()
    idempotent_checks()
    find_stats_checks()
    edge_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
