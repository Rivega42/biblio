#!/usr/bin/env python3
"""Тесты OCR-слоя (трек «Оцифровка»): постраничное хранение + полнотекстовый поиск.

Покрыто (in-memory стор, фиксированные часы, кириллический текст страниц):
  * `OcrStore.add_page` — upsert по (asset_ref, page_no): повтор обновляет text;
  * `pages` — порядок по возрастанию page_no;
  * `OcrService.index_document` — кол-во обработанных страниц;
  * `search_in_document` — регистронезависимый поиск по кириллице, сниппет с '...';
  * нет вхождения -> страница не в результатах; пустой query -> [];
  * `search_all` — по нескольким документам (asset_ref в результате);
  * `page_count` / `word_count`; `delete_document` — число удалённых.

Запуск: py -3.12 tests/test_ocr.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import ocr

PASS = [0]
FAIL = [0]

# Фиксированные часы (детерминизм created_at).
CLOCK = lambda: '2026-06-27T00:00:00+00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _svc():
    """Свежий сервис на in-memory сторе с фиксированными часами."""
    return ocr.OcrService(ocr.OcrStore(':memory:'), now=CLOCK)


def add_page_checks():
    print('-- add_page: upsert по (asset_ref, page_no)')
    s = ocr.OcrStore(':memory:')
    row = s.add_page('DOC-1', 1, 'Первая страница документа', created_at=CLOCK())
    check('add_page -> dict', isinstance(row, dict))
    check('page_no сохранён', row['page_no'] == 1)
    check('text сохранён', row['text'] == 'Первая страница документа')
    check('lang по умолчанию rus', row['lang'] == 'rus')
    check('created_at проставлен', row['created_at'] == CLOCK())
    # Повторный add той же страницы -> обновление text, без дубля.
    s.add_page('DOC-1', 1, 'Исправленный текст страницы', created_at=CLOCK())
    check('upsert обновил text', s.get_page('DOC-1', 1)['text'] == 'Исправленный текст страницы')
    check('upsert не плодит дубль', len(s.pages('DOC-1')) == 1)
    check('get_page для отсутствующей -> None', s.get_page('DOC-1', 9) is None)


def pages_order_checks():
    print('-- pages: порядок по возрастанию page_no')
    s = ocr.OcrStore(':memory:')
    s.add_page('DOC-2', 3, 'третья', created_at=CLOCK())
    s.add_page('DOC-2', 1, 'первая', created_at=CLOCK())
    s.add_page('DOC-2', 2, 'вторая', created_at=CLOCK())
    nums = [p['page_no'] for p in s.pages('DOC-2')]
    check('страницы по возрастанию', nums == [1, 2, 3])
    check('пустой документ -> []', s.pages('NOPE') == [])


def index_document_checks():
    print('-- index_document: кол-во обработанных страниц')
    svc = _svc()
    pages = [{'page_no': 1, 'text': 'Глава первая. Введение в каталогизацию.'},
             {'page_no': 2, 'text': 'Глава вторая. Описание изданий.'},
             {'page_no': 3, 'text': 'Глава третья. Поиск по фонду.'}]
    n = svc.index_document('DOC-3', pages, lang='rus')
    check('index_document вернул 3', n == 3)
    check('page_count == 3', svc.page_count('DOC-3') == 3)
    check('lang проброшен в строку', svc.store.get_page('DOC-3', 1)['lang'] == 'rus')


def search_in_document_checks():
    print('-- search_in_document: регистронезависимо, кириллица, сниппет')
    svc = _svc()
    svc.index_document('DOC-4', [
        {'page_no': 1, 'text': 'Москва — столица, здесь находится главная библиотека страны.'},
        {'page_no': 2, 'text': 'В читальном зале хранятся редкие издания и рукописи.'},
        {'page_no': 3, 'text': 'Каталог фонда доступен в электронном виде.'},
    ])
    res = svc.search_in_document('DOC-4', 'библиотека')
    check('найдена 1 страница', len(res) == 1)
    check('найдена именно стр.1', res[0]['page_no'] == 1)
    check('сниппет содержит запрос', 'библиотека' in res[0]['snippet'])
    check("сниппет с '...'", '...' in res[0]['snippet'])
    # Регистронезависимость (кириллица): запрос капсом находит строчное.
    res_up = svc.search_in_document('DOC-4', 'БИБЛИОТЕКА')
    check('регистронезависимо (капс находит)', len(res_up) == 1 and res_up[0]['page_no'] == 1)
    # Нет вхождения -> страница не в результатах.
    res_none = svc.search_in_document('DOC-4', 'диссертация')
    check('нет вхождения -> []', res_none == [])
    # Пустой query -> [].
    check('пустой query -> []', svc.search_in_document('DOC-4', '') == [])
    # Запрос на нескольких страницах.
    svc.index_document('DOC-5', [
        {'page_no': 1, 'text': 'Издание первое.'},
        {'page_no': 2, 'text': 'Издание второе.'},
    ])
    res_multi = svc.search_in_document('DOC-5', 'издание')
    check('запрос на 2 страницах -> 2', len(res_multi) == 2)


def search_all_checks():
    print('-- search_all: по нескольким документам')
    svc = _svc()
    svc.index_document('DOC-A', [{'page_no': 1, 'text': 'Реставрация старинных переплётов.'}])
    svc.index_document('DOC-B', [{'page_no': 1, 'text': 'Оцифровка и реставрация фондов.'},
                                 {'page_no': 2, 'text': 'Хранение микрофильмов.'}])
    res = svc.search_all('реставрация')
    refs = sorted({r['asset_ref'] for r in res})
    check('найдено по 2 документам', refs == ['DOC-A', 'DOC-B'])
    check('всего 2 совпадения', len(res) == 2)
    check('в результате есть asset_ref', all('asset_ref' in r for r in res))
    check('в результате есть snippet', all('snippet' in r for r in res))
    check('search_all пустой query -> []', svc.search_all('') == [])
    check('search_all без совпадений -> []', svc.search_all('самолёт') == [])


def counts_and_delete_checks():
    print('-- page_count / word_count / delete_document')
    svc = _svc()
    svc.index_document('DOC-W', [
        {'page_no': 1, 'text': 'один два три'},
        {'page_no': 2, 'text': 'четыре пять'},
    ])
    check('page_count 2', svc.page_count('DOC-W') == 2)
    check('word_count 5', svc.word_count('DOC-W') == 5)
    check('page_count отсутствующего 0', svc.page_count('NOPE') == 0)
    check('word_count отсутствующего 0', svc.word_count('NOPE') == 0)
    deleted = svc.store.delete_document('DOC-W')
    check('delete_document вернул 2', deleted == 2)
    check('после удаления page_count 0', svc.page_count('DOC-W') == 0)
    check('delete несуществующего -> 0', svc.store.delete_document('NOPE') == 0)


def snippet_checks():
    print('-- _snippet: фрагмент вокруг первого вхождения')
    svc = _svc()
    long = 'А' * 60 + 'якорь' + 'Б' * 60
    snip = svc._snippet(long, 'якорь', width=10)
    check('сниппет содержит якорь', 'якорь' in snip)
    check('сниппет с многоточием по краям', snip.startswith('...') and snip.endswith('...'))
    check('нет вхождения -> пустая строка', svc._snippet('текст', 'нет') == '')
    check('пустой query -> пустая строка', svc._snippet('текст', '') == '')


def main():
    add_page_checks()
    pages_order_checks()
    index_document_checks()
    search_in_document_checks()
    search_all_checks()
    counts_and_delete_checks()
    snippet_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
