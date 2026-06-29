#!/usr/bin/env python3
"""Тесты авторитетного/нормативного контроля точек доступа (контур Каталогизатор,
issue #359).

Покрыто:
  * normalize_heading: схлопывание пробелов + нижний регистр (casefold), пусто;
  * heading: add дедуп по (kind, norm), невалидный kind / пустой heading ->
    ValueError, get, update_note, list с фильтром kind и подстрокой q, remove
    каскадит варианты и ссылки;
  * variant: add/дедуп/список/remove, add_variant к несуществующему -> None;
  * xref: add see/see_also, невалидный ref_type -> ValueError, self -> ValueError,
    несуществующий id -> ValueError, дедуп, xrefs/remove_xref;
  * service: search возвращает variants + see_also с названиями dst;
    find_or_create (created True потом False); merge переносит варианты, делает
    drop вариантом keep, перецепляет xref и удаляет drop.

Запуск: py -3.12 tests/test_authority_control.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.authority_control import (
    KINDS, REF_TYPES, normalize_heading, AuthorityStore, AuthorityService)

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
# normalize_heading
# ===========================================================================
def normalize_checks():
    print('-- normalize_heading: пробелы / регистр / пусто')
    check('константы KINDS', KINDS == ('person', 'org', 'subject', 'geo'))
    check('константы REF_TYPES', REF_TYPES == ('see', 'see_also'))
    check('схлопывает внутренние пробелы',
          normalize_heading('Толстой   Лев') == 'толстой лев')
    check('обрезает крайние пробелы',
          normalize_heading('  Пушкин  ') == 'пушкин')
    check('таб/перевод строки тоже схлопываются',
          normalize_heading('Лев\tНиколаевич\nТолстой') == 'лев николаевич толстой')
    check('нижний регистр (casefold)',
          normalize_heading('ПУШКИН А. С.') == 'пушкин а. с.')
    check('пустая строка -> ""', normalize_heading('') == '')
    check('None -> ""', normalize_heading(None) == '')


# ===========================================================================
# heading: add / дедуп / валидация / list
# ===========================================================================
def heading_add_checks():
    print('-- heading: add дедуп + валидация')
    st = AuthorityStore(':memory:')
    h = st.add('person', 'Толстой Л. Н.')
    check('add создал заголовок',
          h['kind'] == 'person' and h['heading'] == 'Толстой Л. Н.')
    check('norm посчитан', h['norm'] == 'толстой л. н.')
    check('note по умолчанию пуст', h['note'] == '')

    # Дедуп по (kind, norm): другой регистр/пробелы -> тот же id.
    again = st.add('person', '  толстой   л. н.  ')
    check('add дедуп по (kind, norm) -> тот же id', again['id'] == h['id'])
    check('дедуп не задвоил', len(st.list()) == 1)

    # Тот же norm, но другой kind -> отдельная запись.
    org = st.add('org', 'Толстой Л. Н.')
    check('тот же norm, другой kind -> отдельная запись', org['id'] != h['id'])
    check('теперь 2 заголовка', len(st.list()) == 2)

    bad_kind = False
    try:
        st.add('nope', 'X')
    except ValueError:
        bad_kind = True
    check('невалидный kind -> ValueError', bad_kind)

    bad_empty = False
    try:
        st.add('person', '   ')
    except ValueError:
        bad_empty = True
    check('пустой heading (после strip) -> ValueError', bad_empty)


def heading_list_checks():
    print('-- heading: list фильтр kind + подстрока q + update_note')
    st = AuthorityStore(':memory:')
    st.add('person', 'Пушкин А. С.')
    st.add('person', 'Лермонтов М. Ю.')
    st.add('org', 'Пушкинский дом')
    st.add('subject', 'Поэзия')

    check('list() возвращает все 4', len(st.list()) == 4)
    persons = st.list(kind='person')
    check('list(kind=person) -> только персоны (2)',
          len(persons) == 2 and all(x['kind'] == 'person' for x in persons))
    check('list сортировка по heading',
          [x['heading'] for x in persons] == ['Лермонтов М. Ю.', 'Пушкин А. С.'])

    by_q = st.list(q='ПУШКИН')
    check('list(q) подстрока по norm, регистронезависимо (2)', len(by_q) == 2)
    check('list(kind + q) комбинируется',
          len(st.list(kind='org', q='пушкин')) == 1)
    check('list(q) без совпадений -> []', st.list(q='нетакого') == [])

    target = st.list(kind='subject')[0]
    upd = st.update_note(target['id'], 'тематическая рубрика')
    check('update_note обновил note', upd['note'] == 'тематическая рубрика')
    check('update_note несуществующего -> None', st.update_note(99999, 'x') is None)


# ===========================================================================
# variant
# ===========================================================================
def variant_checks():
    print('-- variant: add / дедуп / список / remove')
    st = AuthorityStore(':memory:')
    h = st.add('person', 'Толстой Л. Н.')

    v = st.add_variant(h['id'], 'Tolstoy Leo')
    check('add_variant создал вариант', v['variant'] == 'Tolstoy Leo')
    check('вариант знает свой heading_id', v['heading_id'] == h['id'])

    again = st.add_variant(h['id'], '  tolstoy   leo  ')
    check('add_variant дедуп по (heading_id, norm) -> тот же id',
          again['id'] == v['id'])
    st.add_variant(h['id'], 'Лев Толстой')
    check('variants() вернул оба (2)', len(st.variants(h['id'])) == 2)

    check('add_variant к несуществующему heading -> None',
          st.add_variant(99999, 'X') is None)

    check('remove_variant удаляет', st.remove_variant(v['id']) is True)
    check('после remove_variant остался 1', len(st.variants(h['id'])) == 1)
    check('remove_variant несуществующего -> False',
          st.remove_variant(99999) is False)


# ===========================================================================
# xref
# ===========================================================================
def xref_checks():
    print('-- xref: add see/see_also + валидация + дедуп')
    st = AuthorityStore(':memory:')
    a = st.add('subject', 'ЭВМ')
    b = st.add('subject', 'Компьютеры')

    x = st.add_xref(a['id'], b['id'], 'see')
    check('add_xref see создан', x['ref_type'] == 'see')
    check('xref знает src/dst', x['src_id'] == a['id'] and x['dst_id'] == b['id'])
    x2 = st.add_xref(b['id'], a['id'])  # ref_type по умолчанию see_also
    check('add_xref по умолчанию see_also', x2['ref_type'] == 'see_also')

    again = st.add_xref(a['id'], b['id'], 'see')
    check('add_xref дедуп по (src, dst, ref_type) -> тот же id',
          again['id'] == x['id'])

    bad_ref = False
    try:
        st.add_xref(a['id'], b['id'], 'nope')
    except ValueError:
        bad_ref = True
    check('невалидный ref_type -> ValueError', bad_ref)

    self_ref = False
    try:
        st.add_xref(a['id'], a['id'])
    except ValueError as e:
        self_ref = 'self-reference' in str(e)
    check('self-reference -> ValueError', self_ref)

    no_id = False
    try:
        st.add_xref(a['id'], 99999)
    except ValueError:
        no_id = True
    check('несуществующий dst id -> ValueError', no_id)

    check('xrefs(a) -> исходящие a (1)', len(st.xrefs(a['id'])) == 1)
    check('remove_xref удаляет', st.remove_xref(x['id']) is True)
    check('после remove_xref у a пусто', st.xrefs(a['id']) == [])


# ===========================================================================
# heading remove каскад
# ===========================================================================
def remove_cascade_checks():
    print('-- heading remove: каскад вариантов и ссылок')
    st = AuthorityStore(':memory:')
    a = st.add('person', 'Иванов И. И.')
    b = st.add('person', 'Петров П. П.')
    st.add_variant(a['id'], 'Ivanov')
    st.add_xref(a['id'], b['id'], 'see_also')   # a как src
    st.add_xref(b['id'], a['id'], 'see_also')   # a как dst

    check('remove несуществующего -> False', st.remove(99999) is False)
    check('remove заголовка -> True', st.remove(a['id']) is True)
    check('после remove заголовка нет', st.get(a['id']) is None)
    check('каскад: варианты удалённого пусты', st.variants(a['id']) == [])
    check('каскад: исходящие ссылки (src=a) удалены', st.xrefs(a['id']) == [])
    check('каскад: входящие ссылки (dst=a) удалены у b', st.xrefs(b['id']) == [])
    check('remove не тронул другой заголовок', st.get(b['id']) is not None)


# ===========================================================================
# AuthorityService: search
# ===========================================================================
def service_search_checks():
    print('-- service: search подтягивает variants + see_also с названиями')
    svc = AuthorityService()
    a = svc.create('subject', 'ЭВМ')
    b = svc.create('subject', 'Компьютеры', note='предпочтительная форма')
    svc.add_variant(a['id'], 'Электронно-вычислительные машины')
    svc.link(a['id'], b['id'], 'see_also')

    res = svc.search(kind='subject', q='эвм')
    check('search вернул 1 заголовок', len(res) == 1)
    row = res[0]
    check('search дал variants', [v['variant'] for v in row['variants']]
          == ['Электронно-вычислительные машины'])
    check('search дал see_also (1)', len(row['see_also']) == 1)
    sa = row['see_also'][0]
    check('see_also подтянул id dst', sa['id'] == b['id'])
    check('see_also подтянул heading dst', sa['heading'] == 'Компьютеры')
    check('see_also несёт ref_type', sa['ref_type'] == 'see_also')

    # Заголовок без вариантов/ссылок -> пустые списки.
    plain = svc.search(kind='subject', q='компьютеры')[0]
    check('заголовок без вариантов -> variants пуст', plain['variants'] == [])
    check('заголовок без ссылок -> see_also пуст', plain['see_also'] == [])


# ===========================================================================
# AuthorityService: find_or_create
# ===========================================================================
def find_or_create_checks():
    print('-- service: find_or_create (created True потом False)')
    svc = AuthorityService()
    first = svc.find_or_create('person', 'Гоголь Н. В.')
    check('find_or_create создал: created=True', first['created'] is True)

    second = svc.find_or_create('person', '  гоголь   н. в.  ')
    check('find_or_create нашёл существующий: created=False',
          second['created'] is False)
    check('find_or_create вернул тот же id', second['id'] == first['id'])
    check('find_or_create не задвоил', len(svc.store.list()) == 1)

    bad = False
    try:
        svc.find_or_create('nope', 'X')
    except ValueError:
        bad = True
    check('find_or_create невалидный kind -> ValueError', bad)


# ===========================================================================
# AuthorityService: merge
# ===========================================================================
def merge_checks():
    print('-- service: merge переносит варианты + drop как вариант keep + xref')
    svc = AuthorityService()
    keep = svc.create('person', 'Чайковский П. И.')
    drop = svc.create('person', 'Tchaikovsky P. I.')
    other = svc.create('subject', 'Музыка')

    svc.add_variant(drop['id'], 'Pyotr Tchaikovsky')
    svc.link(drop['id'], other['id'], 'see_also')   # drop как src
    svc.link(other['id'], drop['id'], 'see')        # drop как dst

    out = svc.merge(keep['id'], drop['id'])
    check('merge: merged=True', out['merged'] is True)
    check('merge: kept = keep-заголовок', out['kept']['id'] == keep['id'])
    check('merge: moved_variants = 1', out['moved_variants'] == 1)

    keep_variants = [v['variant'] for v in svc.store.variants(keep['id'])]
    check('merge: вариант drop перенесён в keep',
          'Pyotr Tchaikovsky' in keep_variants)
    check('merge: сам заголовок drop стал вариантом keep',
          'Tchaikovsky P. I.' in keep_variants)

    check('merge: drop удалён', svc.store.get(drop['id']) is None)
    # xref drop->other перецеплен на keep->other.
    keep_xrefs = svc.store.xrefs(keep['id'])
    check('merge: исходящий xref drop перецеплен на keep',
          any(x['dst_id'] == other['id'] and x['ref_type'] == 'see_also'
              for x in keep_xrefs))
    # xref other->drop перецеплен на other->keep.
    other_xrefs = svc.store.xrefs(other['id'])
    check('merge: входящий xref drop перецеплен на keep',
          any(x['dst_id'] == keep['id'] and x['ref_type'] == 'see'
              for x in other_xrefs))

    bad_same = False
    try:
        svc.merge(keep['id'], keep['id'])
    except ValueError:
        bad_same = True
    check('merge keep == drop -> ValueError', bad_same)

    bad_missing = False
    try:
        svc.merge(keep['id'], 99999)
    except ValueError:
        bad_missing = True
    check('merge несуществующего -> ValueError', bad_missing)


def merge_self_xref_checks():
    print('-- service: merge пропускает ставшие self-ссылками xref')
    svc = AuthorityService()
    keep = svc.create('org', 'РАН')
    drop = svc.create('org', 'Российская академия наук')
    # Ссылка keep<->drop: после merge стала бы self -> должна быть пропущена.
    svc.link(keep['id'], drop['id'], 'see_also')

    svc.merge(keep['id'], drop['id'])
    check('merge: ставшая self-ссылка keep->keep пропущена',
          all(x['src_id'] != x['dst_id'] for x in svc.store.xrefs(keep['id'])))
    check('merge: у keep не осталось висячих self-xref',
          svc.store.xrefs(keep['id']) == [])


def main():
    normalize_checks()
    heading_add_checks()
    heading_list_checks()
    variant_checks()
    xref_checks()
    remove_cascade_checks()
    service_search_checks()
    find_or_create_checks()
    merge_checks()
    merge_self_xref_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
