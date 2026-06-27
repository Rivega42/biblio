#!/usr/bin/env python3
"""Тесты рёбер 7.6 (поток ВКР) + 8.3 (бэкреф 903 <-> I=) — own-store ВКР.

Покрыто:
  * `submit` -> работа в статусе submitted с заполненными полями;
  * `set_antiplagiat` (215^W) + `originality_ok` относительно порога;
  * `review`: approve при ок -> approved; approve при низкой оригинальности ->
    reject с флагом причины; явный reject -> rejected;
  * `link_catalog` (8.3): бэкреф по шифру 903 (source_db/source_mfn/shifr);
  * `list` по faculty/status; `search` по подстроке заглавия (кириллица);
  * `get` несуществующего -> None.

Запуск: py -3.12 tests/test_vkr.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.vkr import (
    VkrStore, VkrService,
    STATUS_SUBMITTED, STATUS_APPROVED, STATUS_REJECTED,
)

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


def _svc(min_originality=70.0):
    """Сервис с детерминированным now и собственным in-memory стором."""
    return VkrService(VkrStore(':memory:'), now=lambda: T0,
                      min_originality=min_originality)


def submit_checks():
    print('-- 7.6: submit -> submitted')
    svc = _svc()
    v = svc.submit('Анализ данных', 'Иванов И.И.', year=2025,
                   faculty='ФКН', speciality='09.03.04', file_ref='vkr/1.pdf')
    check('submit -> status submitted', v['status'] == STATUS_SUBMITTED)
    check('поля сохранены', v['title'] == 'Анализ данных'
          and v['author'] == 'Иванов И.И.' and v['year'] == '2025'
          and v['faculty'] == 'ФКН' and v['file_ref'] == 'vkr/1.pdf')
    check('антиплагиат ещё не задан', v['antiplag_pct'] is None)
    check('get возвращает ту же запись', svc.get(v['id'])['id'] == v['id'])


def antiplagiat_checks():
    print('-- 7.6: set_antiplagiat (215^W) + originality_ok порог')
    svc = _svc(min_originality=70.0)
    v = svc.submit('Работа', 'Петров П.П.')
    check('без оценки originality_ok -> False', svc.originality_ok(v['id']) is False)
    svc.set_antiplagiat(v['id'], 85.0)
    check('% записан (215^W)', svc.get(v['id'])['antiplag_pct'] == 85.0)
    check('85 >= 70 -> originality_ok True', svc.originality_ok(v['id']) is True)
    svc.set_antiplagiat(v['id'], 65.0)
    check('65 < 70 -> originality_ok False', svc.originality_ok(v['id']) is False)
    svc.set_antiplagiat(v['id'], 70.0)
    check('ровно порог 70 -> originality_ok True', svc.originality_ok(v['id']) is True)
    check('set_antiplagiat несуществующего -> None',
          svc.set_antiplagiat(99999, 90.0) is None)


def review_checks():
    print('-- 7.6: review approve при ок / reject при низкой оригинальности')
    svc = _svc(min_originality=70.0)

    v_ok = svc.submit('Высокая оригинальность', 'А.')
    svc.set_antiplagiat(v_ok['id'], 90.0)
    r_ok = svc.review(v_ok['id'], approve=True)
    check('approve при ок -> ok True', r_ok['ok'] is True and r_ok['reason'] is None)
    check('approve при ок -> status approved',
          r_ok['vkr']['status'] == STATUS_APPROVED)

    v_low = svc.submit('Низкая оригинальность', 'Б.')
    svc.set_antiplagiat(v_low['id'], 40.0)
    r_low = svc.review(v_low['id'], approve=True)
    check('approve при низкой оригинальности -> ok False',
          r_low['ok'] is False and r_low['reason'] == 'low_originality')
    check('отказ по антиплагиату -> status rejected',
          r_low['vkr']['status'] == STATUS_REJECTED)

    v_rej = svc.submit('Явный отказ', 'В.')
    svc.set_antiplagiat(v_rej['id'], 95.0)
    r_rej = svc.review(v_rej['id'], approve=False)
    check('явный reject -> status rejected',
          r_rej['vkr']['status'] == STATUS_REJECTED and r_rej['ok'] is False)

    check('review несуществующего -> None', svc.review(99999) is None)


def link_catalog_checks():
    print('-- 8.3: link_catalog — бэкреф 903 <-> I=')
    svc = _svc()
    v = svc.submit('Привязка к ЭК', 'Г.')
    linked = svc.link_catalog(v['id'], db='IBIS', mfn=4321, shifr='Д-903/15')
    check('source_db записан', linked['source_db'] == 'IBIS')
    check('source_mfn записан (int)', linked['source_mfn'] == 4321)
    check('shifr 903 записан (бэкреф)', linked['shifr'] == 'Д-903/15')
    check('link_catalog несуществующего -> None',
          svc.link_catalog(99999, 'IBIS', 1, 'X') is None)


def list_checks():
    print('-- 7.6: list по faculty / status')
    svc = _svc()
    a = svc.submit('A', 'a', faculty='ФКН')
    svc.submit('B', 'b', faculty='ФКН')
    svc.submit('C', 'c', faculty='Физфак')
    svc.set_antiplagiat(a['id'], 90.0)
    svc.review(a['id'], approve=True)   # a -> approved

    check('list() -> все 3', len(svc.list()) == 3)
    check('list(faculty=ФКН) -> 2', len(svc.list(faculty='ФКН')) == 2)
    check('list(faculty=Физфак) -> 1', len(svc.list(faculty='Физфак')) == 1)
    check('list(status=approved) -> 1',
          len(svc.list(status=STATUS_APPROVED)) == 1)
    check('list(status=submitted) -> 2',
          len(svc.list(status=STATUS_SUBMITTED)) == 2)
    check('list(faculty=ФКН,status=approved) -> 1',
          len(svc.list(faculty='ФКН', status=STATUS_APPROVED)) == 1)


def search_checks():
    print('-- 7.6: search по подстроке заглавия (кириллица)')
    svc = _svc()
    svc.submit('Машинное обучение в библиотеках', 'а')
    svc.submit('Обучение нейросетей', 'б')
    svc.submit('Каталогизация', 'в')
    check('подстрока "обучение" -> 2 (регистронезависимо для кириллицы)',
          len(svc.search('обучение')) == 2)
    check('подстрока "Каталог" -> 1', len(svc.search('Каталог')) == 1)
    check('нет совпадений -> 0', len(svc.search('квантовая')) == 0)
    check('пустой запрос -> все 3', len(svc.search('')) == 3)


def get_missing_checks():
    print('-- get несуществующего -> None')
    svc = _svc()
    check('get(99999) -> None', svc.get(99999) is None)


def main():
    submit_checks()
    antiplagiat_checks()
    review_checks()
    link_catalog_checks()
    list_checks()
    search_checks()
    get_missing_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
