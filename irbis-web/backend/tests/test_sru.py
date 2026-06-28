#!/usr/bin/env python3
"""Тесты SRU копи-каталогизации (эпик #240 «Z39.50», access/sru.py).

Покрыто (на синтетическом SRU-XML с встроенным MARCXML — кириллица, 200^a/700^a/
010^a; проверяется namespace-вариативность префиксов srw:/zs:/без префикса):
  * `cql` — форма ``index="term"``, экранирование кавычек, пустой term -> '';
  * `search_query` — маппинг поля проекта через BY_INDEX, фолбэк cql.anywhere;
  * `sru_url` — operation=searchRetrieve, recordSchema=marcxml, закодированный
    query/version/maximumRecords/startRecord;
  * `parse_response` — total <- numberOfRecords, records tag-keyed (200^a/700^a/
    010^a верны); устойчивость к битому/пустому XML -> total 0; пропуск битого
    MARCXML; namespace-вариативность (zs: и без префикса);
  * `candidates` — отбор по isbn (010^a) и по title (вхождение в 200^a,
    регистронезависимо), пустой критерий -> [].

Запуск: PYTHONIOENCODING=utf-8 py -3.12 tests/test_sru.py ; в test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import sru
from access.marcxml import from_marcxml

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Сборка синтетического SRU-ответа.
#
# Встроенный MARCXML — РОВНО в формате, который умеет access/marcxml.from_marcxml
# (datafield tag/ind1/ind2 + subfield code), свёрено на круг ниже в
# marcxml_roundtrip_checks. Параметр prefix задаёт namespace-вариант:
#   ''   -> дефолтный namespace SRU (xmlns без префикса)
#   'zs' -> префикс zs:
# --------------------------------------------------------------------------- #
def _marc_record(title, author, isbn):
    """MARCXML <record> (MARC21slim) с 200^a=title, 700^a=author, 010^a=isbn."""
    return (
        '<record xmlns="%s">'
        '<leader>00000nam  2200000   4500</leader>'
        '<datafield tag="010" ind1=" " ind2=" ">'
        '<subfield code="a">%s</subfield></datafield>'
        '<datafield tag="200" ind1="1" ind2=" ">'
        '<subfield code="a">%s</subfield></datafield>'
        '<datafield tag="700" ind1=" " ind2=" ">'
        '<subfield code="a">%s</subfield></datafield>'
        '</record>'
    ) % (sru.MARC_NS, isbn, title, author)


def _sru_response(records_marc, total, prefix=''):
    """Собрать searchRetrieveResponse с заданным numberOfRecords и MARCXML внутри.

    ``prefix`` -> namespace-вариант SRU: '' (дефолтный xmlns), 'zs' (zs:),
    'srw' (srw:). MARCXML внутри recordData всегда в своём namespace MARC21slim."""
    if prefix:
        p = prefix + ':'
        xmlns = ' xmlns:%s="%s"' % (prefix, sru.SRW_NS)
    else:
        p = ''
        xmlns = ' xmlns="%s"' % sru.SRW_NS
    recs = ''.join(
        '<%srecord><%srecordSchema>marcxml</%srecordSchema>'
        '<%srecordData>%s</%srecordData></%srecord>'
        % (p, p, p, p, marc, p, p)
        for marc in records_marc
    )
    return (
        '<%ssearchRetrieveResponse%s>'
        '<%snumberOfRecords>%d</%snumberOfRecords>'
        '<%srecords>%s</%srecords>'
        '</%ssearchRetrieveResponse>'
    ) % (p, xmlns, p, total, p, p, recs, p, p)


def cql_checks():
    print('-- cql: index="term", экранирование, пустой term')
    check('базовая форма', sru.cql('dc.title', 'Чайка') == 'dc.title="Чайка"')
    check('экранирование кавычек',
          sru.cql('dc.title', 'Say "Hi"') == 'dc.title="Say \\"Hi\\""')
    check('пустой term -> пусто', sru.cql('dc.title', '') == '')
    check('None term -> пусто', sru.cql('dc.title', None) == '')
    check('isbn-индекс',
          sru.cql('bath.isbn', '978-5') == 'bath.isbn="978-5"')


def search_query_checks():
    print('-- search_query: поле проекта -> CQL через BY_INDEX')
    check('title -> dc.title',
          sru.search_query('title', 'Чайка') == 'dc.title="Чайка"')
    check('author -> dc.creator',
          sru.search_query('author', 'Чехов') == 'dc.creator="Чехов"')
    check('isbn -> bath.isbn',
          sru.search_query('isbn', '978-5') == 'bath.isbn="978-5"')
    check('неизвестное поле -> cql.anywhere',
          sru.search_query('xyz', 'кот') == 'cql.anywhere="кот"')
    check('BY_INDEX содержит any', sru.BY_INDEX['any'] == 'cql.anywhere')


def sru_url_checks():
    print('-- sru_url: операция searchRetrieve, schema marcxml, кодирование')
    url = sru.sru_url('http://z.example/sru',
                      sru.search_query('title', 'Чайка'),
                      max_records=5, start=1)
    check('базовый URL + ?', url.startswith('http://z.example/sru?'))
    check('operation=searchRetrieve', 'operation=searchRetrieve' in url)
    check('recordSchema=marcxml', 'recordSchema=marcxml' in url)
    check('version=1.1 (дефолт)', 'version=1.1' in url)
    check('maximumRecords=5', 'maximumRecords=5' in url)
    check('startRecord=1', 'startRecord=1' in url)
    # query закодирован (CQL содержит =, ", кириллицу -> percent-encoding)
    check('query закодирован (есть query=)', 'query=' in url)
    check('сырые кавычки не утекли в URL', '="Чайка"' not in url)
    check('пробел/кириллица percent-кодированы',
          'dc.title' in url and '%' in url.split('query=', 1)[1])
    # кастомная версия
    url2 = sru.sru_url('http://z/sru', 'dc.title="X"', version='2.0')
    check('кастомная version=2.0', 'version=2.0' in url2)


def marcxml_roundtrip_checks():
    print('-- свёрка: синтетический MARCXML -> from_marcxml -> tag-keyed')
    marc = _marc_record('Чайка', 'Чехов А.П.', '978-5-09-099157-0')
    rec = from_marcxml(marc)
    check('200^a заглавие', rec['200'][0]['a'] == 'Чайка')
    check('700^a автор', rec['700'][0]['a'] == 'Чехов А.П.')
    check('010^a ISBN', rec['010'][0]['a'] == '978-5-09-099157-0')


def parse_response_checks():
    print('-- parse_response: searchRetrieveResponse -> total + records')
    marc = [
        _marc_record('Чайка', 'Чехов А.П.', '978-5-09-099157-0'),
        _marc_record('Война и мир', 'Толстой Л.Н.', '978-5-17-000000-0'),
    ]
    xml = _sru_response(marc, total=2)
    res = sru.parse_response(xml)
    check('total == 2', res['total'] == 2)
    check('records: 2 записи', len(res['records']) == 2)
    check('records[0] tag-keyed 200^a',
          res['records'][0]['200'][0]['a'] == 'Чайка')
    check('records[0] 700^a автор',
          res['records'][0]['700'][0]['a'] == 'Чехов А.П.')
    check('records[0] 010^a ISBN',
          res['records'][0]['010'][0]['a'] == '978-5-09-099157-0')
    check('records[1] 200^a',
          res['records'][1]['200'][0]['a'] == 'Война и мир')


def parse_namespace_checks():
    print('-- parse_response: namespace-вариативность (zs: / без префикса)')
    marc = [_marc_record('Чайка', 'Чехов', '978-5-09-099157-0')]
    # с префиксом zs:
    xml_zs = _sru_response(marc, total=1, prefix='zs')
    res_zs = sru.parse_response(xml_zs)
    check('zs:-префикс total==1', res_zs['total'] == 1)
    check('zs:-префикс запись разобрана',
          res_zs['records'] and res_zs['records'][0]['200'][0]['a'] == 'Чайка')
    # без префикса (дефолтный xmlns)
    xml_def = _sru_response(marc, total=1, prefix='')
    res_def = sru.parse_response(xml_def)
    check('без префикса total==1', res_def['total'] == 1)
    check('без префикса запись разобрана',
          res_def['records'] and res_def['records'][0]['200'][0]['a'] == 'Чайка')
    # с префиксом srw:
    xml_srw = _sru_response(marc, total=1, prefix='srw')
    res_srw = sru.parse_response(xml_srw)
    check('srw:-префикс total==1 и запись', res_srw['total'] == 1 and
          res_srw['records'][0]['200'][0]['a'] == 'Чайка')


def parse_robustness_checks():
    print('-- parse_response: устойчивость к битому/пустому/неполному XML')
    check('битый XML -> total 0',
          sru.parse_response('<searchRetrieveResponse><records>') ==
          {'total': 0, 'records': []})
    check('пустая строка -> total 0',
          sru.parse_response('') == {'total': 0, 'records': []})
    check('None -> total 0',
          sru.parse_response(None) == {'total': 0, 'records': []})
    check('пробелы -> total 0',
          sru.parse_response('   ') == {'total': 0, 'records': []})
    # нет numberOfRecords, но есть запись -> total 0, запись разобрана
    marc = [_marc_record('Чайка', 'Чехов', '978-5')]
    no_total = (
        '<searchRetrieveResponse xmlns="%s"><records>'
        '<record><recordData>%s</recordData></record>'
        '</records></searchRetrieveResponse>' % (sru.SRW_NS, marc[0])
    )
    res = sru.parse_response(no_total)
    check('нет numberOfRecords -> total 0', res['total'] == 0)
    check('нет numberOfRecords -> запись всё равно разобрана',
          len(res['records']) == 1 and res['records'][0]['200'][0]['a'] == 'Чайка')
    # пустой набор записей (numberOfRecords=0, нет recordData)
    empty = _sru_response([], total=0)
    res_e = sru.parse_response(empty)
    check('пустой набор -> total 0, records []',
          res_e == {'total': 0, 'records': []})


def candidates_checks():
    print('-- candidates: отбор по isbn (010^a) и title (вхождение в 200^a)')
    marc = [
        _marc_record('Чайка', 'Чехов А.П.', '978-5-09-099157-0'),
        _marc_record('Вишнёвый сад', 'Чехов А.П.', '978-5-17-111111-1'),
        _marc_record('Война и мир', 'Толстой Л.Н.', '978-5-17-000000-0'),
    ]
    records = sru.parse_response(_sru_response(marc, total=3))['records']
    # по ISBN — точное совпадение 010^a
    by_isbn = sru.candidates(records, isbn='978-5-17-111111-1')
    check('isbn -> 1 кандидат', len(by_isbn) == 1)
    check('isbn -> верная запись',
          by_isbn[0]['200'][0]['a'] == 'Вишнёвый сад')
    check('isbn без совпадений -> []',
          sru.candidates(records, isbn='000') == [])
    # по title — вхождение, регистронезависимо, кириллица
    by_title = sru.candidates(records, title='война')
    check('title (регистронезависимо) -> 1 кандидат', len(by_title) == 1)
    check('title -> верная запись',
          by_title[0]['200'][0]['a'] == 'Война и мир')
    by_part = sru.candidates(records, title='Сад')
    check('title-подстрока -> 1 кандидат (Вишнёвый сад)',
          len(by_part) == 1 and by_part[0]['200'][0]['a'] == 'Вишнёвый сад')
    # оба критерия -> логическое ИЛИ (расширяем пул)
    by_both = sru.candidates(records, isbn='978-5-09-099157-0', title='война')
    check('isbn ИЛИ title -> 2 кандидата', len(by_both) == 2)
    # ни одного критерия -> []
    check('без критериев -> []', sru.candidates(records) == [])
    check('пустые критерии -> []',
          sru.candidates(records, isbn='', title='') == [])


def main():
    cql_checks()
    search_query_checks()
    sru_url_checks()
    marcxml_roundtrip_checks()
    parse_response_checks()
    parse_namespace_checks()
    parse_robustness_checks()
    candidates_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
