#!/usr/bin/env python3
"""Тесты COLLECTION_SUBS — time-boxed подписки читателя на коллекции/записи.

Покрыто (in-memory + фиксированные ISO-даты + инжектируемые «часы» для
детерминизма ``active(at=None)``):
  * `subscribe` — создаёт подписку (поля reader/kind/ref/даты/created_at);
  * `active` — окно дат: внутри окна -> в списке; до date_from -> нет; после
    date_to -> нет; открытые границы None -> всегда активна; граничные равные
    даты включительно (date_from == at, at == date_to);
  * `active(at=None)` — берёт дату из инжектируемого now (детерминизм);
  * валидация: невалидный kind -> ValueError; пустой reader/ref -> ValueError;
    кривой формат даты -> ValueError;
  * `cancel` — чужую не удаляет (False), свою удаляет (True);
  * `list` / `for_reader`.

Запуск: py -3.12 tests/test_collection_subs.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import collection_subs

PASS = [0]
FAIL = [0]

# Детерминированные «часы»: фиксированный ISO-момент. active(at=None) берёт
# первые 10 символов -> '2026-06-28'.
CLOCK = '2026-06-28T00:00:00+00:00'
TODAY = '2026-06-28'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def svc():
    """Свежий сервис на чистом in-memory сторе с фиксированными часами."""
    store = collection_subs.CollectionSubStore(':memory:', now=lambda: CLOCK)
    return collection_subs.CollectionSubscriptionService(
        store=store, now=lambda: CLOCK)


def subscribe_checks():
    print('-- subscribe: создаёт подписку с полями и часами')
    s = svc()
    sub = s.subscribe('R1', 'collection', 'COL-7',
                      date_from='2026-06-01', date_to='2026-12-31')
    check('reader сохранён', sub['reader'] == 'R1')
    check('target_kind collection', sub['target_kind'] == 'collection')
    check('target_ref COL-7', sub['target_ref'] == 'COL-7')
    check('date_from сохранён', sub['date_from'] == '2026-06-01')
    check('date_to сохранён', sub['date_to'] == '2026-12-31')
    check('created_at от часов', sub['created_at'] == CLOCK)
    check('есть id', sub['id'] is not None)


def kinds_checks():
    print('-- subscribe: все допустимые виды цели')
    s = svc()
    check('exhibit ок',
          s.subscribe('R1', 'exhibit', 'EXH-1')['target_kind'] == 'exhibit')
    check('record ок',
          s.subscribe('R1', 'record', 'REC-9')['target_kind'] == 'record')
    check('VALID_KINDS',
          collection_subs.VALID_KINDS == ('collection', 'exhibit', 'record'))


def active_window_checks():
    print('-- active: окно дат [from..to]')
    s = svc()
    # окно вокруг TODAY (2026-06-28)
    s.subscribe('R1', 'collection', 'IN', '2026-06-01', '2026-12-31')
    inside = s.active('R1', at=TODAY)
    check('внутри окна -> активна', len(inside) == 1)
    check('внутри окна -> та самая', inside[0]['target_ref'] == 'IN')
    # дата ДО date_from -> не активна
    before = s.active('R1', at='2026-05-31')
    check('до date_from -> не активна', len(before) == 0)
    # дата ПОСЛЕ date_to -> не активна
    after = s.active('R1', at='2027-01-01')
    check('после date_to -> не активна', len(after) == 0)


def active_boundaries_checks():
    print('-- active: граничные равные даты включительно')
    s = svc()
    s.subscribe('R1', 'record', 'B', '2026-06-10', '2026-06-20')
    check('date_from == at -> активна (вкл.)',
          len(s.active('R1', at='2026-06-10')) == 1)
    check('at == date_to -> активна (вкл.)',
          len(s.active('R1', at='2026-06-20')) == 1)
    check('за день до from -> нет',
          len(s.active('R1', at='2026-06-09')) == 0)
    check('за день после to -> нет',
          len(s.active('R1', at='2026-06-21')) == 0)


def active_open_bounds_checks():
    print('-- active: открытые границы None')
    s = svc()
    # обе границы None -> всегда активна
    s.subscribe('RO', 'collection', 'OPEN-BOTH', None, None)
    check('None/None -> активна сейчас',
          len(s.active('RO', at=TODAY)) == 1)
    check('None/None -> активна в далёком прошлом',
          len(s.active('RO', at='1999-01-01')) == 1)
    check('None/None -> активна в далёком будущем',
          len(s.active('RO', at='2099-01-01')) == 1)
    # открытое начало
    s2 = svc()
    s2.subscribe('RF', 'collection', 'OPEN-FROM', None, '2026-06-30')
    check('None..to внутри -> активна',
          len(s2.active('RF', at='2020-01-01')) == 1)
    check('None..to после to -> нет',
          len(s2.active('RF', at='2026-07-01')) == 0)
    # открытый конец
    s3 = svc()
    s3.subscribe('RT', 'collection', 'OPEN-TO', '2026-06-01', None)
    check('from..None после from -> активна',
          len(s3.active('RT', at='2099-01-01')) == 1)
    check('from..None до from -> нет',
          len(s3.active('RT', at='2026-05-01')) == 0)


def active_default_now_checks():
    print('-- active(at=None): дата из инжектируемого now')
    s = svc()
    s.subscribe('R1', 'collection', 'NOW-IN', '2026-06-01', '2026-12-31')
    s.subscribe('R1', 'collection', 'NOW-OUT', '2020-01-01', '2020-12-31')
    act = s.active('R1')  # at=None -> TODAY из CLOCK
    refs = [a['target_ref'] for a in act]
    check('at=None активна только текущая', refs == ['NOW-IN'])


def validation_checks():
    print('-- subscribe: валидация ввода -> ValueError')
    s = svc()

    def raises(fn):
        try:
            fn()
            return False
        except ValueError:
            return True

    check('невалидный kind -> ValueError',
          raises(lambda: s.subscribe('R1', 'bogus', 'X')))
    check('пустой reader -> ValueError',
          raises(lambda: s.subscribe('', 'collection', 'X')))
    check('None reader -> ValueError',
          raises(lambda: s.subscribe(None, 'collection', 'X')))
    check('пустой ref -> ValueError',
          raises(lambda: s.subscribe('R1', 'collection', '')))
    check('кривой формат date_from -> ValueError',
          raises(lambda: s.subscribe('R1', 'collection', 'X',
                                     date_from='2026/06/01')))
    check('кривой формат date_to (короткая) -> ValueError',
          raises(lambda: s.subscribe('R1', 'collection', 'X',
                                     date_to='2026-6-1')))


def cancel_checks():
    print('-- cancel: только своя подписка')
    s = svc()
    mine = s.subscribe('R1', 'collection', 'MINE', None, None)
    other = s.subscribe('R2', 'collection', 'OTHER', None, None)
    # чужой пытается отменить -> False, строка на месте
    check('чужую отменить -> False', s.cancel('R2', mine['id']) is False)
    check('чужая не удалена', s.store.get(mine['id']) is not None)
    # свою отменить -> True, строки нет
    check('свою отменить -> True', s.cancel('R1', mine['id']) is True)
    check('своя удалена', s.store.get(mine['id']) is None)
    check('повторная отмена -> False', s.cancel('R1', mine['id']) is False)
    # подписка другого читателя не пострадала
    check('подписка R2 цела', s.store.get(other['id']) is not None)


def list_for_reader_checks():
    print('-- list / for_reader: подписки читателя')
    s = svc()
    s.subscribe('R1', 'collection', 'A', None, None)
    s.subscribe('R1', 'record', 'B', None, None)
    s.subscribe('R2', 'collection', 'C', None, None)
    lst = s.list('R1')
    check('list R1 -> 2 подписки', len(lst) == 2)
    refs = sorted(x['target_ref'] for x in lst)
    check('list R1 -> A,B', refs == ['A', 'B'])
    check('store.for_reader R2 -> 1', len(s.store.for_reader('R2')) == 1)
    check('list неизвестного -> []', s.list('NOPE') == [])


def store_get_remove_checks():
    print('-- store: get / remove / remove_for')
    s = svc()
    sub = s.subscribe('R1', 'collection', 'X', None, None)
    check('store.get возвращает dict', isinstance(s.store.get(sub['id']), dict)
          and s.store.get(sub['id'])['target_ref'] == 'X')
    check('store.get несуществующего -> None', s.store.get(999999) is None)
    check('remove_for чужого -> False',
          s.store.remove_for('OTHER', sub['id']) is False)
    check('remove существующей -> True', s.store.remove(sub['id']) is True)
    check('remove повторно -> False', s.store.remove(sub['id']) is False)


def main():
    subscribe_checks()
    kinds_checks()
    active_window_checks()
    active_boundaries_checks()
    active_open_bounds_checks()
    active_default_now_checks()
    validation_checks()
    cancel_checks()
    list_for_reader_checks()
    store_get_remove_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
