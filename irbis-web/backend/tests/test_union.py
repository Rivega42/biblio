#!/usr/bin/env python3
"""Тесты рёбер 8.1-8.3 — Сводный каталог SK: свод по сигле + дедуп + федер. поиск.

Покрыто:
  * `dedup_key`: приоритет ISBN(10^a) > шифр(903) > нормализованный title|year;
    устойчивый парсинг (скаляр/dict/список), нормализация ISBN (дефисы/пробелы);
  * 8.1/8.2: две библиотеки с одним ISBN -> ОДНА сводная, 2 holdings, merged=True
    у второй, разные сиглы; разные книги -> разные сводные (merged=False);
  * идемпотентность: повтор ingest того же (sigla, source_mfn) не задваивает holding;
  * 8.3: search по подстроке заглавия / году -> сводные со списком сигл держателей;
  * stats: records / holdings / dedup_rate.

Запуск: py -3.12 tests/test_union.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.union import UnionCatalog, UnionStore, _field_value, _norm_isbn

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


def _rec(isbn=None, shifr=None, title=None, year=None):
    """Собрать НАШУ tag-keyed запись из удобных полей."""
    rec = {}
    if isbn is not None:
        rec['10'] = {'a': isbn}
    if shifr is not None:
        rec['903'] = shifr
    if title is not None:
        rec['200'] = {'a': title}
    if year is not None:
        rec['210'] = {'d': year}
    return rec


def _cat():
    return UnionCatalog(UnionStore(':memory:'), now=lambda: T0)


def dedup_key_checks():
    print('-- dedup_key: приоритет ISBN > шифр > title|year + парсинг')
    cat = _cat()
    check('ключ по ISBN (10^a)',
          cat.dedup_key(_rec(isbn='978-5-7038-1234-5', shifr='X1',
                             title='T', year='2020')) == 'isbn:9785703812345')
    check('ISBN нормализуется (дефисы/пробелы)',
          cat.dedup_key(_rec(isbn='5-94157-X')) == 'isbn:594157X')
    check('нет ISBN -> ключ по шифру (903)',
          cat.dedup_key(_rec(shifr='Ш-77', title='T', year='2020'))
          == 'shifr:Ш-77')
    check('нет ISBN/шифра -> ключ по title|year',
          cat.dedup_key(_rec(title='Война и Мир', year='2020'))
          == 'ty:война и мир|2020')
    # устойчивый парсинг разных форм поля
    check('поле-скаляр читается', _field_value({'903': 'S1'}, '903') == 'S1')
    check('поле-список читается',
          _field_value({'10': [{'a': 'A1'}, {'a': 'A2'}]}, '10', 'a') == 'A1')
    check('подполе регистронезависимо',
          _field_value({'200': {'A': 'Hi'}}, '200', 'a') == 'Hi')
    check('_norm_isbn чистит до цифр/X', _norm_isbn('978 5 7038-1234x') == '978570381234X')


def merge_by_isbn_checks():
    print('-- 8.1/8.2: две библиотеки, один ISBN -> 1 сводная, 2 holdings')
    cat = _cat()
    rec = _rec(isbn='978-5-00000-001-1', title='Алгоритмы', year='2019')
    r1 = cat.ingest(rec, sigla='SPB-01', source_db='LIB_A', source_mfn=10)
    check('первая библиотека: merged=False', r1['merged'] is False)
    r2 = cat.ingest(rec, sigla='MSK-02', source_db='LIB_B', source_mfn=55)
    check('вторая библиотека: merged=True (свод)', r2['merged'] is True)
    check('одна и та же сводная запись', r1['union_id'] == r2['union_id'])
    holds = cat.holdings(r1['union_id'])
    check('2 holdings под сводной', len(holds) == 2)
    siglas = sorted(h['sigla'] for h in holds)
    check('разные сиглы держателей', siglas == ['MSK-02', 'SPB-01'])
    st = cat.stats()
    check('1 сводная запись в каталоге', st['records'] == 1)
    check('2 держания всего', st['holdings'] == 2)


def distinct_books_checks():
    print('-- 8.2: разные книги -> разные сводные записи')
    cat = _cat()
    a = cat.ingest(_rec(isbn='111-1'), sigla='S1', source_mfn=1)
    b = cat.ingest(_rec(isbn='222-2'), sigla='S1', source_mfn=2)
    check('разные ISBN -> разные сводные', a['union_id'] != b['union_id'])
    check('обе как новые (merged=False)',
          a['merged'] is False and b['merged'] is False)
    check('две сводные записи', cat.stats()['records'] == 2)


def idempotent_checks():
    print('-- идемпотентность: повтор ingest не задваивает holding')
    cat = _cat()
    rec = _rec(isbn='978-5-12345-000-0', title='Сети', year='2021')
    cat.ingest(rec, sigla='S1', source_db='LIB_A', source_mfn=7)
    r2 = cat.ingest(rec, sigla='S1', source_db='LIB_A', source_mfn=7)
    check('повтор присоединился к существующей (merged=True)',
          r2['merged'] is True)
    check('holding не задвоился (1)', len(cat.holdings(r2['union_id'])) == 1)
    check('stats: 1 запись / 1 держание',
          cat.stats()['records'] == 1 and cat.stats()['holdings'] == 1)
    # другая сигла под той же сводной -> новое holding
    cat.ingest(rec, sigla='S2', source_db='LIB_B', source_mfn=7)
    check('иная сигла -> +1 holding (2)',
          len(cat.holdings(r2['union_id'])) == 2)


def search_checks():
    print('-- 8.3: федеративный поиск по заглавию/году со списком сигл')
    cat = _cat()
    rec = _rec(isbn='978-5-99999-000-0', title='Базы данных', year='2018')
    cat.ingest(rec, sigla='SPB-01', source_mfn=1)
    cat.ingest(rec, sigla='MSK-02', source_mfn=2)
    cat.ingest(_rec(isbn='000-0', title='Компиляторы', year='2018'),
               sigla='KZN-03', source_mfn=3)

    res = cat.search('базы')
    check('поиск по подстроке заглавия нашёл 1', len(res) == 1)
    check('результат со списком сигл всех держателей',
          sorted(res[0]['siglas']) == ['MSK-02', 'SPB-01'])
    check('holdings_count в результате', res[0]['holdings_count'] == 2)

    res_year = cat.search(year='2018')
    check('поиск по году вернул обе книги 2018', len(res_year) == 2)
    check('поиск без совпадений -> пусто', cat.search('нетакого') == [])

    rid = res[0]['id']
    rec_full = cat.record(rid)
    check('record() отдаёт сиглы + holdings',
          len(rec_full['siglas']) == 2 and len(rec_full['holdings']) == 2)
    check('record() для несуществующей -> None', cat.record(99999) is None)


def stats_checks():
    print('-- stats: records / holdings / dedup_rate')
    cat = _cat()
    check('пустой каталог: dedup_rate 0', cat.stats()['dedup_rate'] == 0.0)
    rec = _rec(isbn='978-5-77777-000-0', title='ОС', year='2017')
    cat.ingest(rec, sigla='S1', source_mfn=1)
    cat.ingest(rec, sigla='S2', source_mfn=2)
    cat.ingest(rec, sigla='S3', source_mfn=3)   # 1 запись, 3 держания
    st = cat.stats()
    check('records=1 / holdings=3', st['records'] == 1 and st['holdings'] == 3)
    check('dedup_rate = 1 - 1/3', st['dedup_rate'] == round(1 - 1 / 3, 4))


def main():
    dedup_key_checks()
    merge_by_isbn_checks()
    distinct_books_checks()
    idempotent_checks()
    search_checks()
    stats_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
