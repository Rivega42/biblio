#!/usr/bin/env python3
"""Тесты tariff_store — редактируемые тарифы матрицы доступов (own-store, #331).

Покрыто (на :memory: + фейковые часы):
  * create/get/list тарифов (порядок по sort, затем name);
  * дубликат name -> sqlite3.IntegrityError;
  * update_tariff (partial), delete_tariff каскадит ячейки;
  * set_entry создаёт ячейку с дефолтами (included True, value None, 'block');
  * set_entry PARTIAL: None-параметры не затирают сохранённые поля;
  * included False сохраняется/читается как bool; value None <-> NULL;
  * get_entries форма {item_key: {...}}; get_entry; remove_entry;
  * assign_tenant + get_tenant_tariff; assign неизвестного тарифа -> ValueError;
  * add_addon + addon_units суммирует пакеты; addons_for.

Запуск: py -3.12 tests/test_tariff_store.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import tariff_store as ts
import sqlite3

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Фейковые часы — детерминизм updated_at/created_at.
class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-06-28T00:00:%02dZ' % self.t


def _store():
    return ts.TariffStore(':memory:', now=Clock())


def tariff_crud_checks():
    print('-- create / get / list тарифов')
    s = _store()
    s.create_tariff('pro', title='Профи', sort=2)
    s.create_tariff('base', title='Базовый', sort=1)
    check('get_tariff возвращает dict', s.get_tariff('pro')['title'] == 'Профи')
    check('get_tariff отсутствующего -> None', s.get_tariff('нет') is None)
    names = [t['name'] for t in s.list_tariffs()]
    check('list по sort, name', names == ['base', 'pro'])
    # одинаковый sort -> разрешает name.
    s.create_tariff('alpha', sort=1)
    names2 = [t['name'] for t in s.list_tariffs()]
    check('равный sort -> по name', names2 == ['alpha', 'base', 'pro'])


def duplicate_checks():
    print('-- дубликат name -> IntegrityError')
    s = _store()
    s.create_tariff('dup')
    try:
        s.create_tariff('dup')
        check('дубликат name -> IntegrityError', False)
    except sqlite3.IntegrityError:
        check('дубликат name -> IntegrityError', True)


def update_delete_checks():
    print('-- update_tariff (partial) + delete_tariff каскад')
    s = _store()
    s.create_tariff('t', title='Старый', sort=5)
    upd = s.update_tariff('t', title='Новый')
    check('update title', upd['title'] == 'Новый')
    check('update partial: sort не затёрт', upd['sort'] == 5)
    check('update_tariff отсутствующего -> None', s.update_tariff('нет') is None)
    # delete каскадит ячейки.
    s.set_entry('t', 'catalog')
    s.set_entry('t', 'circulation')
    check('ячейки заведены', len(s.get_entries('t')) == 2)
    check('delete_tariff -> True', s.delete_tariff('t') is True)
    check('delete_tariff снова -> False', s.delete_tariff('t') is False)
    check('после delete ячеек нет', s.get_entries('t') == {})


def entry_default_checks():
    print('-- set_entry создаёт с дефолтами')
    s = _store()
    s.create_tariff('p')
    e = s.set_entry('p', 'ocr')
    check('дефолт included True (bool)', e['included'] is True)
    check('дефолт value None', e['value'] is None)
    check("дефолт enforcement 'block'", e['enforcement'] == 'block')
    # неизвестный тариф -> ValueError.
    try:
        s.set_entry('нет', 'x')
        check('set_entry неизвестного тарифа -> ValueError', False)
    except ValueError:
        check('set_entry неизвестного тарифа -> ValueError', True)


def entry_partial_checks():
    print('-- set_entry PARTIAL: None не затирает поля')
    s = _store()
    s.create_tariff('p')
    # сначала ставим value.
    s.set_entry('p', 'ocr', value=1000)
    # потом ставим только enforcement -> value должен сохраниться.
    e = s.set_entry('p', 'ocr', enforcement='grace')
    check('partial: value сохранён', e['value'] == 1000)
    check('partial: enforcement обновлён', e['enforcement'] == 'grace')
    check('partial: included не затёрт (True)', e['included'] is True)
    # included False сохраняется и читается как bool.
    e2 = s.set_entry('p', 'ocr', included=False)
    check('included False (bool)', e2['included'] is False)
    check('included False: value цел', e2['value'] == 1000)
    check('included False: enforcement цел', e2['enforcement'] == 'grace')
    # повторный partial с included=None не воскрешает True.
    e3 = s.set_entry('p', 'ocr', value=2000)
    check('partial: included False остался', e3['included'] is False)
    check('partial: value обновлён', e3['value'] == 2000)


def entry_read_checks():
    print('-- get_entries / get_entry / remove_entry')
    s = _store()
    s.create_tariff('p')
    s.set_entry('p', 'catalog', value=50, enforcement='block')
    s.set_entry('p', 'ocr', included=False)
    entries = s.get_entries('p')
    check('get_entries форма {key: dict}',
          set(entries.keys()) == {'catalog', 'ocr'})
    check('get_entries ячейка catalog',
          entries['catalog'] == {'included': True, 'value': 50, 'enforcement': 'block'})
    check('get_entries included bool', entries['ocr']['included'] is False)
    check('get_entry одиночный', s.get_entry('p', 'catalog')['value'] == 50)
    check('get_entry отсутствующего -> None', s.get_entry('p', 'нет') is None)
    check('get_entry неизвестного тарифа -> None', s.get_entry('нет', 'x') is None)
    check('remove_entry -> True', s.remove_entry('p', 'ocr') is True)
    check('remove_entry снова -> False', s.remove_entry('p', 'ocr') is False)
    check('после remove get_entries', set(s.get_entries('p').keys()) == {'catalog'})


def assign_checks():
    print('-- assign_tenant / get_tenant_tariff')
    s = _store()
    s.create_tariff('base')
    s.create_tariff('pro')
    s.assign_tenant('spb-gtb', 'base')
    check('get_tenant_tariff', s.get_tenant_tariff('spb-gtb') == 'base')
    check('get_tenant_tariff чужой -> None', s.get_tenant_tariff('нет') is None)
    # переназначение (upsert).
    s.assign_tenant('spb-gtb', 'pro')
    check('переназначение тарифа', s.get_tenant_tariff('spb-gtb') == 'pro')
    # неизвестный тариф -> ValueError.
    try:
        s.assign_tenant('x', 'нетакого')
        check('assign неизвестного тарифа -> ValueError', False)
    except ValueError:
        check('assign неизвестного тарифа -> ValueError', True)
    # delete тарифа не трогает назначение (намеренно).
    s.delete_tariff('pro')
    check('delete тарифа не трогает tenant_tariff',
          s.get_tenant_tariff('spb-gtb') == 'pro')


def addon_checks():
    print('-- add_addon / addon_units / addons_for')
    s = _store()
    check('addon_units пусто -> 0', s.addon_units('t', 'ocr_pages') == 0)
    s.add_addon('t', 'ocr_pages', packs=1, pack_size=1000)
    s.add_addon('t', 'ocr_pages', packs=1, pack_size=1000)
    check('2 пакета по 1000 -> 2000', s.addon_units('t', 'ocr_pages') == 2000)
    check('addon_units другого ресурса -> 0', s.addon_units('t', 'sms') == 0)
    s.add_addon('t', 'sms', packs=3, pack_size=100)
    check('сумма по ресурсу sms', s.addon_units('t', 'sms') == 300)
    items = s.addons_for('t')
    check('addons_for вернул записи по ресурсам',
          {r['resource'] for r in items} == {'ocr_pages', 'sms'})
    check('addons_for чужого тенанта -> []', s.addons_for('нет') == [])


def main():
    tariff_crud_checks()
    duplicate_checks()
    update_delete_checks()
    entry_default_checks()
    entry_partial_checks()
    entry_read_checks()
    assign_checks()
    addon_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
