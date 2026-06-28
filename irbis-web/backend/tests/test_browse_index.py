#!/usr/bin/env python3
"""Тесты Browse-указателей A–Z (эпик #240, access/browse_index.py).

Покрыто (на синтетике — кириллица/латиница/цифры; повторяющиеся 700):
  * `first_letter` — русская/латинская буква к заглавной; цифра/знак -> '#';
    пустая/None -> '#'; ведущие кавычки/скобки/пробелы пропускаются; Ё -> Е;
  * `bucket` — группировка по первой букве; сортировка по term без учёта
    регистра; суммирование count одинаковых term; пустой term пропущен;
    'letters' в порядке рус -> лат -> '#';
  * `aggregate` — частоты по подполю из нескольких записей, вкл. повторяющиеся
    700; пустой subfield -> поле-скаляр; устойчивость к записи без поля/None;
  * `browse` — сквозной из записей в указатель A–Z.

Запуск: py -3.12 tests/test_browse_index.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import browse_index as bi

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def first_letter_checks():
    print('-- first_letter: первая значимая буква термина')
    check('русская строчная -> заглавная', bi.first_letter('иванов') == 'И')
    check('русская заглавная остаётся', bi.first_letter('Петров') == 'П')
    check('латиница строчная -> заглавная', bi.first_letter('smith') == 'S')
    check('латиница заглавная остаётся', bi.first_letter('Black') == 'B')
    check('цифра -> #', bi.first_letter('2021 год') == bi.OTHER)
    check('знак -> #', bi.first_letter('—тире') == bi.OTHER)
    check('пустая строка -> #', bi.first_letter('') == bi.OTHER)
    check('None -> #', bi.first_letter(None) == bi.OTHER)
    check('ведущая кавычка пропущена',
          bi.first_letter('"Анна Каренина"') == 'А')
    check('ведущие пробелы пропущены', bi.first_letter('   Толстой') == 'Т')
    check('ведущая скобка пропущена', bi.first_letter('[Сборник]') == 'С')
    check('Ё сворачивается к Е', bi.first_letter('Ёлка') == 'Е')
    check('ё строчная сворачивается к Е', bi.first_letter('ёж') == 'Е')


def bucket_checks():
    print('-- bucket: группировка/сортировка/суммирование')
    entries = [
        {'term': 'Яблоко', 'count': 2},
        {'term': 'Арбуз', 'count': 3},
        {'term': 'апельсин', 'count': 1},   # тоже буква А, регистр иной
        {'term': 'Apple', 'count': 5},      # латиница A
        {'term': '2021', 'count': 4},       # цифра -> '#'
        {'term': 'Арбуз', 'count': 1},      # дубль term -> суммировать с 3
        {'term': '', 'count': 9},           # пустой -> пропустить
    ]
    res = bi.bucket(entries)
    check('есть ключи letters/buckets',
          'letters' in res and 'buckets' in res)
    check("буква 'А' присутствует", 'А' in res['buckets'])
    # внутри 'А': апельсин(а), Арбуз — сортировка без учёта регистра.
    a_terms = [e['term'] for e in res['buckets']['А']]
    check('сортировка по term без регистра (апельсин < Арбуз)',
          a_terms == ['апельсин', 'Арбуз'])
    # суммирование Арбуз: 3 + 1 = 4.
    arbuz = [e['count'] for e in res['buckets']['А'] if e['term'] == 'Арбуз'][0]
    check('count одинаковых term суммируется (3+1=4)', arbuz == 4)
    check('каждый бакет — {term,count}',
          all(set(e.keys()) == {'term', 'count'} for e in res['buckets']['А']))
    check('пустой term не попал', all(
        e['term'] != '' for b in res['buckets'].values() for e in b))
    check("цифра -> бакет '#'", '2021' == res['buckets'][bi.OTHER][0]['term'])
    # порядок letters: рус (А, Я) -> лат (A) -> '#'.
    check("'letters' в порядке рус->лат->#",
          res['letters'] == ['А', 'Я', 'A', bi.OTHER])
    check('пустой вход -> пустой указатель',
          bi.bucket([]) == {'letters': [], 'buckets': {}})
    # кортежная форма входа.
    res_t = bi.bucket([('Книга', 2), ('Книга', 3)])
    check('кортежи (term,count) принимаются',
          res_t['buckets']['К'][0] == {'term': 'Книга', 'count': 5})


# --- Фикстура для aggregate/browse: записи с повторяющимися полями ----------- #
REC1 = {
    '700': [{'a': 'Иванов И.И.'}, {'a': 'Петров П.П.'}],  # два автора
    '606': [{'a': 'Библиотеки'}],
    '101': 'rus',
}
REC2 = {
    '700': [{'a': 'Иванов И.И.'}],   # повтор того же автора (частота 2)
    '606': [{'a': 'Архивы'}],
}
REC3 = {'606': [{'a': 'Библиотеки'}]}   # нет 700 -> устойчивость
REC4 = None                              # None-запись -> устойчивость
RECORDS = [REC1, REC2, REC3, REC4]


def aggregate_checks():
    print('-- aggregate: частоты по подполю из нескольких записей')
    agg = bi.aggregate(RECORDS, '700', 'a')
    counts = {e['term']: e['count'] for e in agg}
    check('Иванов И.И. встречается дважды', counts.get('Иванов И.И.') == 2)
    check('Петров П.П. встречается однажды', counts.get('Петров П.П.') == 1)
    check('aggregate отдаёт {term,count}',
          all(set(e.keys()) == {'term', 'count'} for e in agg))
    # темы 606: Библиотеки x2, Архивы x1.
    agg_subj = bi.aggregate(RECORDS, '606', 'a')
    sc = {e['term']: e['count'] for e in agg_subj}
    check('тема Библиотеки x2', sc.get('Библиотеки') == 2)
    check('тема Архивы x1', sc.get('Архивы') == 1)
    check('устойчивость к None/без поля (нет краша)', isinstance(agg, list))
    # поле-скаляр: пустой subfield берёт голую строку 101.
    agg_lang = bi.aggregate(RECORDS, '101', '')
    lc = {e['term']: e['count'] for e in agg_lang}
    check('поле-скаляр 101 через пустой subfield', lc.get('rus') == 1)
    # отсутствующий тег -> пусто.
    check('отсутствующий тег -> []', bi.aggregate(RECORDS, '999', 'a') == [])


def browse_checks():
    print('-- browse: сквозной из записей в указатель A–Z')
    res = bi.browse(RECORDS, '700', 'a')
    check('browse даёт {letters,buckets}',
          'letters' in res and 'buckets' in res)
    check("автор на 'И' присутствует", 'И' in res['buckets'])
    iv = [e for e in res['buckets']['И'] if e['term'] == 'Иванов И.И.']
    check('browse: Иванов И.И. count 2', iv and iv[0]['count'] == 2)
    check("автор на 'П' присутствует", 'П' in res['buckets'])
    # темы через browse.
    res_subj = bi.browse(RECORDS, '606', 'a')
    check('browse тем: Архивы(А) и Библиотеки(Б)',
          'А' in res_subj['buckets'] and 'Б' in res_subj['buckets'])


def main():
    first_letter_checks()
    bucket_checks()
    aggregate_checks()
    browse_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
