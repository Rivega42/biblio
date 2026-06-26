#!/usr/bin/env python3
"""Пословный keyword-индекс K= (#270).

Раньше own-индекс клал значение поля 610 ЦЕЛЫМ термином под ``K=`` — точное
``K=театр`` находило 0, хотя усечение ``K=театр$`` срабатывало. Теперь 610
индексируется ПОСЛОВНО (как у ИРБИС): значение токенизируется на слова, каждое
слово — отдельный термин ``K=``. Здесь проверяется, что:

  * точное слово ``K=театр`` находит запись с 610="театральное искусство; театр"
    и запись с многословным ключевым словом "сценический театр";
  * многозначные/составные ключевые слова (несколько слов в одном повторе 610)
    разбиваются на слова;
  * усечение ``K=театр$`` (prefix-match) НЕ сломано;
  * составные выражения (``+``/``*``/``^``) с K= работают;
  * цело-полевое поведение прочих префиксов (T=/A=/S=) НЕ изменилось.

Standalone (Windows): set PYTHONUTF8=1 && py -3.12 tests/test_own_search_keyword.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import seed_vocab
from access.catalog import CatalogStore, _field_values, _keyword_words
from access.store import AccessStore

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _store():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return CatalogStore(':memory:', access_store=st)


def _book(title, author, kw, inv):
    """kw — список повторов поля 610; каждый повтор может быть многословным."""
    return {
        '920': 'PAZK',
        '200': [{'a': title}],
        '700': [{'a': author}],
        '610': [{'': k} for k in kw],
        '101': 'rus',
        '910': [{'a': '0', 'b': inv}],
        '907': [{'a': 'Tester'}],
    }


def _title(rec):
    vals = _field_values(rec, '200', 'a')
    return vals[0] if vals else ''


def _titles(res):
    return sorted(_title(it['record']) for it in res['items'])


def main():
    # --- юнит: токенизатор слов ключевого поля ---
    check('words: разбивка по ; и пробелам',
          _keyword_words('театральное искусство; театр')
          == ['театральное', 'искусство', 'театр'])
    check('words: дефисное слово не дробится',
          _keyword_words('научно-популярный') == ['научно-популярный'])
    check('words: пунктуация-разделитель',
          _keyword_words('театр, кино.') == ['театр', 'кино'])
    check('words: пусто -> []', _keyword_words('') == [] and _keyword_words(None) == [])

    cat = _store()
    # mfn1: ключевое слово как ОДИН многословный повтор — должен разбиться на слова.
    cat.save('EK', _book('Театральная энциклопедия', 'Иванов И.И.',
                         ['театральное искусство; театр'], '2001'))
    # mfn2: несколько повторов 610, один многословный.
    cat.save('EK', _book('Сцена и зал', 'Петров П.П.',
                         ['сценический театр', 'драматургия'], '2002'))
    # mfn3: «театр» отсутствует в ключевых словах вовсе.
    cat.save('EK', _book('Основы кино', 'Сидоров С.С.',
                         ['кинематограф', 'монтаж'], '2003'))

    # 1. ТОЧНОЕ слово K=театр — главный кейс #270 (раньше давал 0).
    r = cat.search_records('EK', 'K=театр')
    check('K= точное слово находит ОБЕ записи с «театр»',
          r['total'] == 2 and _titles(r) == ['Сцена и зал', 'Театральная энциклопедия'])

    # 2. Точное слово из многословного повтора 610.
    r = cat.search_records('EK', 'K=искусство')
    check('K= точное «искусство» (из «театральное искусство»)',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная энциклопедия')
    r = cat.search_records('EK', 'K=сценический')
    check('K= точное «сценический» (из «сценический театр»)',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Сцена и зал')

    # 3. Одиночное (несоставное) ключевое слово по-прежнему точно находится.
    r = cat.search_records('EK', 'K=драматургия')
    check('K= одиночное точное слово',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Сцена и зал')

    # 4. Усечение K=театр$ (prefix-match) НЕ сломано.
    r = cat.search_records('EK', 'K=теат$')
    check('K= усечение по префиксу слова', r['total'] == 2)
    r = cat.search_records('EK', 'K=кино$')
    check('K= усечение «кино$» (кинематограф нет — отдельное слово «кинематограф»)',
          r['total'] == 0)
    r = cat.search_records('EK', 'K=кинемат$')
    check('K= усечение «кинемат$» -> кинематограф', r['total'] == 1)

    # 5. Нет такого слова.
    r = cat.search_records('EK', 'K=балет')
    check('K= нет совпадений', r['total'] == 0 and r['items'] == [])

    # 6. Составные выражения с пословным K=.
    r = cat.search_records('EK', '("K=театр" * "K=искусство")')
    check('compound AND: театр И искусство -> одна',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная энциклопедия')
    r = cat.search_records('EK', '("K=театр" + "K=кинематограф")')
    check('compound OR: театр ИЛИ кинематограф -> все три', r['total'] == 3)
    r = cat.search_records('EK', '"K=театр" ^ "K=искусство"')
    check('compound NOT: театр без искусства -> «Сцена и зал»',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Сцена и зал')

    # 7. Цело-полевые префиксы НЕ затронуты: T= ищет ВСЁ заглавие, а не пословно.
    r = cat.search_records('EK', 'T=Сцена')
    check('T= НЕ пословно: «Сцена» (часть заглавия) не находит', r['total'] == 0)
    r = cat.search_records('EK', 'T=Сцена и зал')
    check('T= целое заглавие находит',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Сцена и зал')
    r = cat.search_records('EK', 'A=Иванов И.И.')
    check('A= целое значение автора находит',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная энциклопедия')

    print('%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
