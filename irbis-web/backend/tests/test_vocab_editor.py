#!/usr/bin/env python3
"""Тесты редактора словарей .mnu и деревьев .tre (контур Каталогизатор).

Покрыто:
  * словарь (.mnu): add_value (авто-sort в конец), rename, deactivate/activate,
    remove, values(active_only), идемпотентность add_value, изоляция по vocab;
  * дерево (.tre): add_node вычисляет depth + материализованный точечный path,
    children (корни и потомки), move_node пересчитывает depth/path узла И всех
    потомков, subtree по префиксу path, идемпотентность add_node, изоляция по
    tree; защита от переноса в собственное поддерево.

Запуск: py -3.12 tests/test_vocab_editor.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.vocab_editor import VocabEditor, VocabStore

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# ===========================================================================
# СЛОВАРЬ (.mnu)
# ===========================================================================
def value_crud_checks():
    print('-- .mnu: add/rename/deactivate/remove значения')
    ed = VocabEditor(VocabStore(':memory:'))
    v = ed.add_value('langs', 'rus', 'Русский')
    check('add_value создал значение',
          v['code'] == 'rus' and v['label'] == 'Русский' and v['active'] == 1)
    check('первый sort = 0', v['sort'] == 0)
    check('origin по умолчанию custom', v['origin'] == 'custom')

    ed.add_value('langs', 'eng', 'Английскй')           # с опечаткой -> rename ниже
    check('второй авто-sort = 1 (в конец)',
          ed.store.value_get('langs', 'eng')['sort'] == 1)
    ed.add_value('langs', 'ger', 'Немецкий', sort=5)
    check('явный sort уважается',
          ed.store.value_get('langs', 'ger')['sort'] == 5)

    r = ed.rename('langs', 'eng', 'Английский')
    check('rename поменял label', r['label'] == 'Английский')
    check('rename не трогает code/sort', r['code'] == 'eng' and r['sort'] == 1)

    bad = False
    try:
        ed.rename('langs', 'nope', 'X')
    except KeyError:
        bad = True
    check('rename несуществующего -> KeyError', bad)


def value_active_checks():
    print('-- .mnu: deactivate/activate + values(active_only)')
    ed = VocabEditor(VocabStore(':memory:'))
    ed.add_value('doctype', 'a', 'Книга')
    ed.add_value('doctype', 'b', 'Статья')
    ed.add_value('doctype', 'c', 'Диск')

    d = ed.deactivate('doctype', 'b')
    check('deactivate -> active=0', d['active'] == 0)
    all_vals = ed.values('doctype')
    check('values() показывает все 3', len(all_vals) == 3)
    act = ed.values('doctype', active_only=True)
    check('values(active_only) скрывает выключенное (2)', len(act) == 2)
    check('active_only не содержит b',
          all(x['code'] != 'b' for x in act))
    check('values упорядочены по sort',
          [x['code'] for x in all_vals] == ['a', 'b', 'c'])

    a = ed.activate('doctype', 'b')
    check('activate -> active=1', a['active'] == 1)
    check('после activate снова 3 активных',
          len(ed.values('doctype', active_only=True)) == 3)


def value_remove_isolation_checks():
    print('-- .mnu: remove + идемпотентность + изоляция по vocab')
    ed = VocabEditor(VocabStore(':memory:'))
    ed.add_value('langs', 'rus', 'Русский')
    ed.add_value('countries', 'rus', 'Россия')          # тот же code, другой vocab
    check('изоляция по vocab: одинаковый code в разных словарях',
          ed.store.value_get('langs', 'rus')['label'] == 'Русский'
          and ed.store.value_get('countries', 'rus')['label'] == 'Россия')

    again = ed.add_value('langs', 'rus', 'Русский язык')  # идемпотентно по (vocab,code)
    check('add_value идемпотентен: обновил label, не задвоил',
          again['label'] == 'Русский язык'
          and len(ed.values('langs')) == 1)

    check('remove удаляет значение', ed.remove('langs', 'rus') is True)
    check('после remove словарь langs пуст', ed.values('langs') == [])
    check('remove несуществующего -> False', ed.remove('langs', 'rus') is False)
    check('remove не затронул другой vocab',
          len(ed.values('countries')) == 1)


# ===========================================================================
# ДЕРЕВО (.tre)
# ===========================================================================
def _grnti_fixture(ed):
    """Маленькое ГРНТИ-подобное дерево:
        00 -> 00.10 -> 00.10.30
              00.20
    """
    ed.add_node('GRNTI', '00', 'Общие вопросы')
    ed.add_node('GRNTI', '10', 'Раздел 10', parent_code='00')
    ed.add_node('GRNTI', '20', 'Раздел 20', parent_code='00')
    ed.add_node('GRNTI', '30', 'Подраздел 30', parent_code='10')


def node_build_checks():
    print('-- .tre: add_node строит depth + материализованный path')
    ed = VocabEditor(VocabStore(':memory:'))
    _grnti_fixture(ed)

    root = ed.store.node_get('GRNTI', '00')
    check('корень: depth=0', root['depth'] == 0)
    check('корень: path = code', root['path'] == '00')
    check('корень: parent_code = NULL', root['parent_code'] is None)

    n10 = ed.store.node_get('GRNTI', '10')
    check('узел 10: depth=1', n10['depth'] == 1)
    check('узел 10: path точечный из кодов (00.10)', n10['path'] == '00.10')
    check('узел 10: parent_code=00', n10['parent_code'] == '00')

    n30 = ed.store.node_get('GRNTI', '30')
    check('узел 30: depth=2', n30['depth'] == 2)
    check('узел 30: path = 00.10.30', n30['path'] == '00.10.30')

    bad = False
    try:
        ed.add_node('GRNTI', 'x', 'X', parent_code='nope')
    except KeyError:
        bad = True
    check('add_node с несуществующим родителем -> KeyError', bad)


def children_checks():
    print('-- .tre: children (корни и прямые потомки)')
    ed = VocabEditor(VocabStore(':memory:'))
    _grnti_fixture(ed)

    roots = ed.children('GRNTI')
    check('children(None) -> корни (только 00)',
          [n['code'] for n in roots] == ['00'])
    kids = ed.children('GRNTI', '00')
    check('children(00) -> [10, 20]',
          sorted(n['code'] for n in kids) == ['10', '20'])
    check('children(30) пуст (лист)', ed.children('GRNTI', '30') == [])


def subtree_checks():
    print('-- .tre: subtree по префиксу path')
    ed = VocabEditor(VocabStore(':memory:'))
    _grnti_fixture(ed)

    sub = ed.subtree('GRNTI', '10')
    codes = sorted(n['code'] for n in sub)
    check('subtree(10) = сам узел + потомок (10, 30)', codes == ['10', '30'])
    check('subtree(10) НЕ включает соседа 20',
          all(n['code'] != '20' for n in sub))

    whole = ed.subtree('GRNTI', '00')
    check('subtree(00) = всё дерево (4 узла)', len(whole) == 4)

    bad = False
    try:
        ed.subtree('GRNTI', 'nope')
    except KeyError:
        bad = True
    check('subtree несуществующего -> KeyError', bad)


def move_node_checks():
    print('-- .tre: move_node пересчитывает depth/path узла И потомков')
    ed = VocabEditor(VocabStore(':memory:'))
    _grnti_fixture(ed)
    # Дополним: 30 получает свой потомок 40, чтобы проверить каскад.
    ed.add_node('GRNTI', '40', 'Лист 40', parent_code='30')
    check('исходно 40: path=00.10.30.40',
          ed.store.node_get('GRNTI', '40')['path'] == '00.10.30.40')

    # Переносим узел 10 (с поддеревом 30->40) под 20.
    ed.move_node('GRNTI', '10', '20')

    n10 = ed.store.node_get('GRNTI', '10')
    check('move: 10 теперь под 20 (parent_code=20)', n10['parent_code'] == '20')
    check('move: 10 path=00.20.10', n10['path'] == '00.20.10')
    check('move: 10 depth=2', n10['depth'] == 2)

    n30 = ed.store.node_get('GRNTI', '30')
    check('move: потомок 30 path пересчитан (00.20.10.30)',
          n30['path'] == '00.20.10.30')
    check('move: потомок 30 depth=3', n30['depth'] == 3)
    n40 = ed.store.node_get('GRNTI', '40')
    check('move: глубокий потомок 40 path=00.20.10.30.40',
          n40['path'] == '00.20.10.30.40')
    check('move: глубокий потомок 40 depth=4', n40['depth'] == 4)

    # Перенос в корень.
    ed.move_node('GRNTI', '10', None)
    r10 = ed.store.node_get('GRNTI', '10')
    check('move в корень: 10 depth=0, path=10',
          r10['depth'] == 0 and r10['path'] == '10' and r10['parent_code'] is None)
    check('move в корень: потомок 30 path=10.30',
          ed.store.node_get('GRNTI', '30')['path'] == '10.30')

    # Защита от цикла: перенос узла в собственное поддерево.
    cyc = False
    try:
        ed.move_node('GRNTI', '10', '30')
    except ValueError:
        cyc = True
    check('move в собственное поддерево -> ValueError', cyc)


def node_idempotent_isolation_checks():
    print('-- .tre: идемпотентность add_node + изоляция по tree + remove_node')
    ed = VocabEditor(VocabStore(':memory:'))
    _grnti_fixture(ed)

    # Идемпотентность: повторный add_node не двоит и не переносит, обновляет label.
    before = ed.store.node_get('GRNTI', '10')
    again = ed.add_node('GRNTI', '10', 'Раздел 10 (испр.)', parent_code='00')
    check('add_node идемпотентен: label обновлён', again['label'] == 'Раздел 10 (испр.)')
    check('add_node идемпотентен: path не изменился', again['path'] == before['path'])
    check('add_node идемпотентен: не задвоил детей 00',
          len(ed.children('GRNTI', '00')) == 2)

    # Изоляция по tree: тот же code в другом дереве независим.
    ed.add_node('UDK', '00', 'УДК корень')
    check('изоляция по tree: 00 в GRNTI и UDK независимы',
          ed.store.node_get('GRNTI', '00')['label'] == 'Общие вопросы'
          and ed.store.node_get('UDK', '00')['label'] == 'УДК корень')

    # remove_node с потомками.
    removed = ed.remove_node('GRNTI', '10')
    check('remove_node вернул число узлов поддерева (10,30)', removed == 2)
    check('remove_node удалил поддерево',
          ed.store.node_get('GRNTI', '10') is None
          and ed.store.node_get('GRNTI', '30') is None)
    check('remove_node не тронул соседа 20',
          ed.store.node_get('GRNTI', '20') is not None)
    check('remove_node не тронул другое дерево UDK',
          ed.store.node_get('UDK', '00') is not None)
    check('remove_node несуществующего -> 0', ed.remove_node('GRNTI', 'nope') == 0)


def main():
    value_crud_checks()
    value_active_checks()
    value_remove_isolation_checks()
    node_build_checks()
    children_checks()
    subtree_checks()
    move_node_checks()
    node_idempotent_isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
