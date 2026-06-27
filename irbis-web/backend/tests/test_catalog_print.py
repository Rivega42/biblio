#!/usr/bin/env python3
"""Тесты печатных/выходных форм каталога (контур Каталогизатор — печать).

Покрыто:
  * `card`: несёт автора/заглавие (200^f/^a), выходные данные (210^a:^c,^d),
    ISBN (10^a), индекс УДК (675^a); ПУСТЫЕ элементы и зоны опускаются;
  * устойчивый парсинг полей: скаляр / {подполе:значение}-dict / список;
  * `brief_line`: однострочное краткое описание (нет переводов строк);
  * `catalog_list`: нумерованный список brief_line;
  * `index_form`: группировка по 700^a + сортировка рубрик; «[без значения]»;
  * `to_text`-диспетчер (card/list/index, одна запись-dict, неизвестная форма);
  * пустой ввод не роняет формы.

Запуск: py -3.12 tests/test_catalog_print.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.catalog_print import (
    card, brief_line, catalog_list, index_form, to_text,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Эталонная запись из ТЗ (Война и мир).
WAR = {
    '200': {'a': 'Война и мир', 'f': 'Л. Толстой'},
    '210': {'a': 'М.', 'c': 'Наука', 'd': '2020'},
    '10': {'a': '978-5-00000-000-1'},
    '675': {'a': '82'},
    '700': [{'a': 'Толстой'}],
}


def card_checks():
    print('-- card: зоны карточки + ГОСТ-разделители')
    c = card(WAR)
    check('card несёт автора (200^f)', 'Л. Толстой' in c)
    check('card несёт заглавие (200^a)', 'Война и мир' in c)
    check('card несёт выходные (210^a:^c,^d)',
          'М. : Наука, 2020' in c)
    check('card несёт ISBN (10^a)', '978-5-00000-000-1' in c)
    check('card несёт индекс УДК (675^a)', 'УДК 82' in c)
    check('card: заголовок «Автор. Заглавие»',
          c.startswith('Л. Толстой. Война и мир'))
    check('card: зоны разделены « . — »', ' . — ' in c)


def card_empty_elements_checks():
    print('-- card: пустые элементы и зоны опускаются')
    # Нет ISBN, нет УДК, нет издателя.
    rec = {
        '200': {'a': 'Заглавие без автора'},
        '210': {'a': 'СПб.', 'd': '1999'},
    }
    c = card(rec)
    check('нет автора -> заголовок = заглавие',
          c.startswith('Заглавие без автора'))
    check('нет ISBN -> нет зоны ISBN', '978' not in c and 'ISBN' not in c)
    check('нет УДК -> нет зоны УДК', 'УДК' not in c)
    check('нет издателя -> «Место, Год» без « : »',
          'СПб., 1999' in c and ' : ' not in c)

    # Совсем пустая запись не роняет форму.
    check('пустая запись -> пустая карточка', card({}) == '')
    check('None-запись -> пустая карточка', card(None) == '')

    # Запись только с УДК -> карточка ровно из зоны УДК (без ведущего « . — »).
    only_udc = card({'675': {'a': '004'}})
    check('одна зона УДК без ведущего разделителя', only_udc == 'УДК 004')


def robust_parsing_checks():
    print('-- устойчивый парсинг: скаляр / dict / список')
    # 200 как СПИСОК из одного dict; 700 как одиночный dict; 210 как dict.
    rec_list = {
        '200': [{'a': 'Список-форма', 'f': 'Автор С.'}],
        '210': {'a': 'М.', 'c': 'Изд', 'd': '2021'},
    }
    c = card(rec_list)
    check('поле-список читается как dict-экземпляр',
          'Автор С.' in c and 'Список-форма' in c)

    # Скаляр-поле (строка) на месте, где подполя нет -> не ломает парсинг,
    # подполе ^a у скаляра пустое.
    rec_scalar = {'200': 'Голая строка', '210': {'d': '2000'}}
    c2 = card(rec_scalar)
    check('скаляр-поле без подполей -> ^a пусто, не падает',
          isinstance(c2, str))
    check('скаляр-поле: год из 210^d виден', '2000' in c2)

    # Регистронезависимость ключа подполя.
    rec_upper = {'200': {'A': 'Верхний ключ'}}
    check('ключ подполя регистронезависим',
          'Верхний ключ' in card(rec_upper))


def brief_line_checks():
    print('-- brief_line: одна строка')
    b = brief_line(WAR)
    check('brief_line однострочный (нет \\n)', '\n' not in b)
    check('brief_line несёт заглавие и год', 'Война и мир' in b and '2020' in b)
    check('brief_line несёт ISBN', '978-5-00000-000-1' in b)
    check('brief_line пустой записи -> ""', brief_line({}) == '')


def catalog_list_checks():
    print('-- catalog_list: нумерация')
    recs = [
        WAR,
        {'200': {'a': 'Отцы и дети', 'f': 'И. Тургенев'},
         '210': {'a': 'М.', 'd': '2019'}},
    ]
    lst = catalog_list(recs)
    lines = lst.split('\n')
    check('две записи -> две строки', len(lines) == 2)
    check('первая строка нумерована «1. »', lines[0].startswith('1. '))
    check('вторая строка нумерована «2. »', lines[1].startswith('2. '))
    check('нумерация несёт описание', 'Отцы и дети' in lines[1])
    check('пустой список -> ""', catalog_list([]) == '')


def index_form_checks():
    print('-- index_form: группировка по 700^a + сортировка')
    recs = [
        {'200': {'a': 'Война и мир'}, '700': [{'a': 'Толстой'}]},
        {'200': {'a': 'Отцы и дети'}, '700': [{'a': 'Тургенев'}]},
        {'200': {'a': 'Анна Каренина'}, '700': [{'a': 'Толстой'}]},
        {'200': {'a': 'Аноним'}},  # без 700 -> рубрика «[без значения]»
    ]
    idx = index_form(recs, by='700')
    lines = idx.split('\n')
    # Рубрики верхнего уровня (без ведущих пробелов) в порядке появления.
    headers = [ln for ln in lines if not ln.startswith('  ')]
    check('рубрики отсортированы (Толстой < Тургенев)',
          headers.index('Толстой') < headers.index('Тургенев'))
    check('«[без значения]» в конце', headers[-1] == '[без значения]')
    check('Толстой сгруппировал 2 записи',
          'Война и мир' in idx and 'Анна Каренина' in idx)
    # Под рубрикой Толстой — две вложенные строки (с отступом).
    t_pos = lines.index('Толстой')
    nested = [ln for ln in lines[t_pos + 1:]
              if ln.startswith('  ')][:2]
    check('под рубрикой — описания с отступом', len(nested) == 2)
    check('index_form пустого ввода -> ""', index_form([]) == '')

    # Группировка по произвольному полю/подполю через by=/code=.
    idx_udc = index_form([WAR], by='675', code='a')
    check('index_form по 675^a группирует по УДК', idx_udc.startswith('82'))


def to_text_checks():
    print('-- to_text: диспетчер форм')
    recs = [WAR]
    check('form=card -> карточка', 'Война и мир' in to_text(recs, form='card'))
    check('form=list -> нумерация', to_text(recs, form='list').startswith('1. '))
    check('form=index -> рубрика автора',
          to_text(recs, form='index', by='700').startswith('Толстой'))

    # Одна запись-dict (не список) тоже принимается.
    check('to_text принимает одну запись-dict',
          'Война и мир' in to_text(WAR, form='card'))

    # Несколько карточек разделены пустой строкой.
    multi = to_text([WAR, WAR], form='card')
    check('card-диспетчер: карточки разделены \\n\\n', '\n\n' in multi)

    # Неизвестная форма -> ValueError.
    bad = False
    try:
        to_text(recs, form='nonsense')
    except ValueError:
        bad = True
    check('неизвестная форма -> ValueError', bad)

    # Пустой ввод по всем формам.
    check('to_text([], card) -> ""', to_text([], form='card') == '')
    check('to_text([], list) -> ""', to_text([], form='list') == '')
    check('to_text([], index) -> ""', to_text([], form='index') == '')


def main():
    card_checks()
    card_empty_elements_checks()
    robust_parsing_checks()
    brief_line_checks()
    catalog_list_checks()
    index_form_checks()
    to_text_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
