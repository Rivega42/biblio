#!/usr/bin/env python3
"""Тесты OAI-PMH провайдера (трек «Оцифровка», access/oai_pmh.py).

Покрыто (на синтетике — 4 записи, кириллица, разные виды/годы; одна 900^b='05'
-> serials):
  * `dublin_core` — маппинг title/creator/date/publisher/language/identifier/type;
    отсутствующее поле опущено; identifier/type присутствуют всегда;
  * `oai_identifier` — формат `oai:biblio:<mfn>`, кастомный префикс, без mfn;
  * `record_set` — 900^b '05'->serials, иначе books, без 900^b->other;
  * `record_header` — identifier/datestamp/setSpec (с сетом и без);
  * `identify` — протокольные ключи/константы (2.0/no/YYYY-MM-DD);
  * `list_metadata_formats` — единственный oai_dc;
  * `get_record` — найдена / None;
  * `list_records` — кол-во + структура header/metadata; фильтр по set;
  * `list_identifiers` — только header (без metadata);
  * `paginate` — страница + resumption token; последняя страница -> None.

Запуск: py -3.12 tests/test_oai_pmh.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import oai_pmh as oai

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --- Фикстура: 4 каталожные записи (кириллица, разные виды/годы) ------------- #
# rec1 — книга (без 900^b -> сет 'other'), полный набор DC-полей.
REC1 = {
    '200': [{'a': 'История библиотек'}],
    '700': [{'a': 'Иванов И.И.'}],
    '210': [{'c': 'Наука', 'd': '2021'}],
    '101': 'rus',
    'mfn': 1,
}
# rec2 — книга (900^b отличен от '05' -> 'books'), без автора (creator опущен).
REC2 = {
    '200': [{'a': 'Каталогизация'}],
    '210': [{'c': 'Профессия', 'd': '2019'}],
    '101': [{'a': 'rus'}],          # язык как подполе 101^a
    '900': [{'b': '01'}],
    'mfn': 2,
}
# rec3 — сериальное издание (900^b='05' -> 'serials').
REC3 = {
    '200': [{'a': 'Вестник библиотеки'}],
    '700': [{'a': 'Петров П.П.'}],
    '210': [{'c': 'Вестник', 'd': '2022'}],
    '101': 'rus',
    '900': [{'b': '05'}],
    'mfn': 3,
}
# rec4 — минимальная запись (только mfn): нет title/creator/date/publisher/lang.
REC4 = {'mfn': 4}

RECORDS = [REC1, REC2, REC3, REC4]


def dublin_core_checks():
    print('-- dublin_core: запись -> Dublin Core (oai_dc)')
    dc = oai.dublin_core(REC1)
    check('title <- 200^a', dc['title'] == 'История библиотек')
    check('creator <- 700^a', dc['creator'] == 'Иванов И.И.')
    check('date <- 210^d', dc['date'] == '2021')
    check('publisher <- 210^c', dc['publisher'] == 'Наука')
    check('language <- 101 (скаляр)', dc['language'] == 'rus')
    check('identifier oai:biblio:1', dc['identifier'] == 'oai:biblio:1')
    check('type == text', dc['type'] == 'text')
    # rec2: язык как подполе 101^a, нет автора.
    dc2 = oai.dublin_core(REC2)
    check('language <- 101^a (подполе)', dc2['language'] == 'rus')
    check('creator опущен (нет 700)', 'creator' not in dc2)
    # rec4: пустая запись — все опциональные DC опущены, кроме id/type.
    dc4 = oai.dublin_core(REC4)
    check('пустая: title опущен', 'title' not in dc4)
    check('пустая: language опущен', 'language' not in dc4)
    check('пустая: identifier есть всегда', dc4['identifier'] == 'oai:biblio:4')
    check('пустая: type есть всегда', dc4['type'] == 'text')


def oai_identifier_checks():
    print('-- oai_identifier: формат идентификатора')
    check('дефолтный префикс', oai.oai_identifier(REC1) == 'oai:biblio:1')
    check('кастомный префикс',
          oai.oai_identifier(REC3, prefix='oai:sptl:') == 'oai:sptl:3')
    check('без mfn -> пустой хвост',
          oai.oai_identifier({'200': [{'a': 'X'}]}) == 'oai:biblio:')


def record_set_checks():
    print('-- record_set: вид издания 900^b -> setSpec')
    check("'05' -> serials", oai.record_set(REC3) == 'serials')
    check("'01' -> books", oai.record_set(REC2) == 'books')
    check('нет 900^b -> other', oai.record_set(REC1) == 'other')


def record_header_checks():
    print('-- record_header: заголовок записи')
    h = oai.record_header(REC1, '2026-01-01')
    check('header identifier', h['identifier'] == 'oai:biblio:1')
    check('header datestamp', h['datestamp'] == '2026-01-01')
    check('header без setSpec', 'setSpec' not in h)
    hs = oai.record_header(REC3, '2026-01-01', set_spec='serials')
    check('header setSpec задан', hs['setSpec'] == 'serials')


def identify_checks():
    print('-- identify: описание репозитория')
    idn = oai.identify('Biblio', 'http://x/oai', 'a@x', '2020-01-01')
    check('repositoryName', idn['repositoryName'] == 'Biblio')
    check('baseURL', idn['baseURL'] == 'http://x/oai')
    check('protocolVersion 2.0', idn['protocolVersion'] == '2.0')
    check('adminEmail', idn['adminEmail'] == 'a@x')
    check('earliestDatestamp', idn['earliestDatestamp'] == '2020-01-01')
    check('deletedRecord no', idn['deletedRecord'] == 'no')
    check('granularity YYYY-MM-DD', idn['granularity'] == 'YYYY-MM-DD')


def list_metadata_formats_checks():
    print('-- list_metadata_formats: oai_dc')
    fmts = oai.list_metadata_formats()
    check('один формат', len(fmts) == 1)
    check('metadataPrefix oai_dc', fmts[0]['metadataPrefix'] == 'oai_dc')
    check('schema oai_dc.xsd', fmts[0]['schema'].endswith('oai_dc.xsd'))


def get_record_checks():
    print('-- get_record: найти по идентификатору')
    g = oai.get_record(RECORDS, 'oai:biblio:3')
    check('get_record найдена', g is not None)
    check('get_record header id', g['header']['identifier'] == 'oai:biblio:3')
    check('get_record header setSpec serials',
          g['header']['setSpec'] == 'serials')
    check('get_record metadata title',
          g['metadata']['title'] == 'Вестник библиотеки')
    check('get_record не найдена -> None',
          oai.get_record(RECORDS, 'oai:biblio:999') is None)


def list_records_checks():
    print('-- list_records: заголовок + метаданные, фильтр по set')
    lr = oai.list_records(RECORDS)
    check('list_records 4 записи', len(lr) == 4)
    check('list_records структура header',
          'identifier' in lr[0]['header'] and 'datestamp' in lr[0]['header'])
    check('list_records структура metadata',
          lr[0]['metadata']['identifier'] == 'oai:biblio:1')
    # фильтр по set: только serials (rec3).
    lr_ser = oai.list_records(RECORDS, set_spec='serials')
    check('фильтр serials -> 1 запись', len(lr_ser) == 1)
    check('фильтр serials -> mfn 3',
          lr_ser[0]['header']['identifier'] == 'oai:biblio:3')
    # фильтр по books (только rec2).
    lr_bk = oai.list_records(RECORDS, set_spec='books')
    check('фильтр books -> 1 запись (rec2)',
          len(lr_bk) == 1 and lr_bk[0]['header']['identifier'] == 'oai:biblio:2')


def list_identifiers_checks():
    print('-- list_identifiers: только заголовки')
    li = oai.list_identifiers(RECORDS)
    check('list_identifiers 4 заголовка', len(li) == 4)
    check('list_identifiers без metadata', 'metadata' not in li[0])
    check('list_identifiers header id', li[0]['identifier'] == 'oai:biblio:1')
    check('list_identifiers setSpec', li[2]['setSpec'] == 'serials')


def paginate_checks():
    print('-- paginate: страница + resumption token')
    items = [1, 2, 3, 4, 5]
    page, token = oai.paginate(items, 0, 2)
    check('страница 1 -> [1,2]', page == [1, 2])
    check('страница 1 -> token "2"', token == '2')
    page2, token2 = oai.paginate(items, 2, 2)
    check('страница 2 -> [3,4]', page2 == [3, 4])
    check('страница 2 -> token "4"', token2 == '4')
    page3, token3 = oai.paginate(items, 4, 2)
    check('последняя страница -> [5]', page3 == [5])
    check('последняя страница -> token None', token3 is None)
    pe, te = oai.paginate([], 0, 10)
    check('пустой вход -> ([], None)', pe == [] and te is None)


def main():
    dublin_core_checks()
    oai_identifier_checks()
    record_set_checks()
    record_header_checks()
    identify_checks()
    list_metadata_formats_checks()
    get_record_checks()
    list_records_checks()
    list_identifiers_checks()
    paginate_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
