#!/usr/bin/env python3
"""Тесты EXHIBITS — виртуальные выставки (трек «Оцифровка»).

Покрыто (in-memory own-store, инжектируемые часы — детерминизм):
  * create + get; дубликат slug -> ValueError;
  * add_record (инкремент sort); неизвестный slug -> ValueError;
  * items по возрастанию sort; reorder меняет порядок;
  * publish/unpublish переключает флаг; public_exhibits только опубликованные;
  * view -> {exhibit, items}; view неизвестного -> None; remove позиции.

Запуск: py -3.12 tests/test_exhibits.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import exhibits

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


class FakeClock:
    """Детерминированные ISO8601-часы: каждый вызов сдвигается на минуту."""

    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-06-27T00:%02d:00+00:00' % (self.t % 60)


def service():
    return exhibits.ExhibitService(
        store=exhibits.ExhibitStore(':memory:', now=FakeClock()))


def create_checks():
    print('-- create + get: создание выставки и чтение по slug')
    svc = service()
    ex = svc.create('rare-maps', 'Редкие карты', 'Подборка оцифрованных карт')
    check('создана с id', isinstance(ex['id'], int) and ex['id'] >= 1)
    check('slug', ex['slug'] == 'rare-maps')
    check('кириллица в title', ex['title'] == 'Редкие карты')
    check('description', ex['description'] == 'Подборка оцифрованных карт')
    check('по умолчанию черновик', ex['published'] == 0)
    check('есть метки времени', bool(ex['created_at']) and bool(ex['updated_at']))
    got = svc.get('rare-maps')
    check('get возвращает ту же запись', got is not None and got['id'] == ex['id'])
    check('description по умолчанию пуст',
          svc.create('empty', 'Пусто')['description'] == '')


def duplicate_slug_checks():
    print('-- дубликат slug -> ValueError')
    svc = service()
    svc.create('dup', 'Первая')
    raised = False
    try:
        svc.create('dup', 'Вторая')
    except ValueError:
        raised = True
    check('повторный slug бросает ValueError', raised)
    check('исходная выставка не перезаписана', svc.get('dup')['title'] == 'Первая')


def add_record_checks():
    print('-- add_record: добавление записей, инкремент sort')
    svc = service()
    svc.create('digi', 'Оцифровка')
    a = svc.add_record('digi', 'IBIS', 101, caption='Первый лист',
                       asset_ref='iiif://img/1')
    b = svc.add_record('digi', 'IBIS', 102, caption='Второй лист')
    c = svc.add_record('digi', 'IBIS', 103)
    check('sort первой позиции = 1', a['sort'] == 1)
    check('sort второй позиции = 2', b['sort'] == 2)
    check('sort третьей позиции = 3', c['sort'] == 3)
    check('db/mfn сохранены', a['db'] == 'IBIS' and a['mfn'] == 101)
    check('кириллица в caption', a['caption'] == 'Первый лист')
    check('asset_ref сохранён', a['asset_ref'] == 'iiif://img/1')
    check('asset_ref по умолчанию пуст', c['asset_ref'] == '')


def add_record_unknown_checks():
    print('-- add_record на неизвестный slug -> ValueError')
    svc = service()
    raised = False
    try:
        svc.add_record('nope', 'IBIS', 1)
    except ValueError:
        raised = True
    check('неизвестный slug бросает ValueError', raised)


def items_order_checks():
    print('-- items: позиции по возрастанию sort')
    svc = service()
    svc.create('ord', 'Порядок')
    svc.add_record('ord', 'IBIS', 1)
    svc.add_record('ord', 'IBIS', 2)
    svc.add_record('ord', 'IBIS', 3)
    its = svc.store.items(svc.get('ord')['id'])
    check('три позиции', len(its) == 3)
    check('отсортированы по sort',
          [i['sort'] for i in its] == [1, 2, 3])
    check('mfn в порядке добавления',
          [i['mfn'] for i in its] == [1, 2, 3])


def reorder_checks():
    print('-- reorder: переустановка порядка по item_ids')
    svc = service()
    svc.create('re', 'Перестановка')
    a = svc.add_record('re', 'IBIS', 1)
    b = svc.add_record('re', 'IBIS', 2)
    c = svc.add_record('re', 'IBIS', 3)
    res = svc.reorder('re', [c['id'], a['id'], b['id']])
    check('reorder вернул mfn в новом порядке',
          [i['mfn'] for i in res] == [3, 1, 2])
    check('sort пронумерован с 1',
          [i['sort'] for i in res] == [1, 2, 3])
    again = svc.store.items(svc.get('re')['id'])
    check('порядок сохранён в сторе',
          [i['mfn'] for i in again] == [3, 1, 2])


def publish_checks():
    print('-- publish / unpublish: переключение флага')
    svc = service()
    svc.create('pub', 'Витрина')
    check('создана как черновик', svc.get('pub')['published'] == 0)
    p = svc.publish('pub')
    check('после publish опубликована', p['published'] == 1)
    u = svc.unpublish('pub')
    check('после unpublish снова черновик', u['published'] == 0)


def public_exhibits_checks():
    print('-- public_exhibits: только опубликованные')
    svc = service()
    svc.create('p1', 'Открытая 1')
    svc.create('p2', 'Открытая 2')
    svc.create('draft', 'Черновик')
    svc.publish('p1')
    svc.publish('p2')
    pub = svc.public_exhibits()
    slugs = {e['slug'] for e in pub}
    check('две опубликованные', len(pub) == 2)
    check('черновик не в витрине', 'draft' not in slugs)
    check('опубликованные присутствуют', slugs == {'p1', 'p2'})
    check('list(all) видит все три', len(svc.list()) == 3)


def view_checks():
    print('-- view: структура {exhibit, items}')
    svc = service()
    svc.create('v', 'Просмотр', 'Описание')
    svc.add_record('v', 'IBIS', 10, caption='A')
    svc.add_record('v', 'IBIS', 20, caption='B')
    v = svc.view('v')
    check('view не None', v is not None)
    check('есть ключ exhibit', v['exhibit']['slug'] == 'v')
    check('есть ключ items', isinstance(v['items'], list) and len(v['items']) == 2)
    check('items по порядку', [i['mfn'] for i in v['items']] == [10, 20])
    check('view неизвестного -> None', svc.view('missing') is None)


def remove_checks():
    print('-- remove: удаление позиции')
    svc = service()
    svc.create('rm', 'Удаление')
    a = svc.add_record('rm', 'IBIS', 1)
    b = svc.add_record('rm', 'IBIS', 2)
    ok = svc.remove('rm', a['id'])
    check('remove вернул True', ok is True)
    left = svc.view('rm')['items']
    check('осталась одна позиция', len(left) == 1 and left[0]['id'] == b['id'])
    check('повторное удаление -> False', svc.remove('rm', a['id']) is False)
    check('remove из неизвестной выставки -> False',
          svc.remove('nope', b['id']) is False)


def main():
    create_checks()
    duplicate_slug_checks()
    add_record_checks()
    add_record_unknown_checks()
    items_order_checks()
    reorder_checks()
    publish_checks()
    public_exhibits_checks()
    view_checks()
    remove_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
