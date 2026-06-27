#!/usr/bin/env python3
"""Тесты MARCXML interop (контур Каталогизатор) — access/marcxml.py.

Покрыто:
  * round-trip ``from_marcxml(to_marcxml(r)) == normalize(r)``: подполя,
    повторяющиеся поля, контрольные поля, кириллица (utf-8);
  * controlfield vs datafield: 00X / bare-string -> <controlfield>, поля с
    подполями -> <datafield ind1 ind2>/<subfield code>;
  * namespace: дефолтный MARC21slim (xmlns) И namespace=None; разбор устойчив к
    обоим, а также к namespaced входу;
  * коллекция: <collection> round-trip (mass), пустая коллекция, одиночный
    <record> как вход коллекции;
  * робастность: битый XML -> MarcXmlError (одиночный) / [] (коллекция); пустой
    вход; битый record внутри коллекции пропускается.

Запуск: py -3.12 tests/test_marcxml.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.marc import normalize
from access import marcxml
from access.marcxml import (
    to_marcxml, from_marcxml,
    to_marcxml_collection, from_marcxml_collection,
    MarcXmlError, MARC21_SLIM_NS,
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


def roundtrip_checks():
    print('-- round-trip: from_marcxml(to_marcxml(r)) == normalize(r)')
    rec = {
        '001': '12345',
        '101': 'rus',
        '200': {'a': 'Title', 'f': 'Author'},
        '700': [{'a': 'Tolstoy'}, {'a': 'Pushkin'}],
    }
    rt = from_marcxml(to_marcxml(rec))
    check('подполя + повтор + контрольные -> normalize', rt == normalize(rec))

    rt_no_ns = from_marcxml(to_marcxml(rec, namespace=None))
    check('round-trip без namespace тоже == normalize', rt_no_ns == normalize(rec))

    # одиночный dict-инстанс нормализуется в список из одного
    one = {'200': {'a': 'X'}}
    check('одиночное поле -> [inst]', from_marcxml(to_marcxml(one)) == normalize(one))


def cyrillic_checks():
    print('-- кириллица (utf-8) сохраняется в round-trip')
    rec = {
        '001': '00000077',
        '101': 'rus',
        '200': {'a': 'Война и мир', 'f': 'Лев Толстой'},
        '700': [{'a': 'Толстой', 'b': 'Л. Н.'}],
    }
    rt = from_marcxml(to_marcxml(rec))
    check('кириллица в подполях == normalize', rt == normalize(rec))
    check('кириллица значение точное',
          rt['200'][0]['a'] == 'Война и мир' and rt['700'][0]['a'] == 'Толстой')


def controlfield_vs_datafield_checks():
    print('-- controlfield (00X/bare) vs datafield (подполя)')
    rec = {'001': '42', '210': {'a': 'Москва', 'c': 'Наука'}}
    xml = to_marcxml(rec)
    check('контрольное поле -> <controlfield', '<controlfield' in xml or
          ':controlfield' in xml)
    check('controlfield tag=001 присутствует', 'tag="001"' in xml)
    check('поле с подполями -> <datafield', '<datafield' in xml or
          ':datafield' in xml)
    check('datafield имеет ind1/ind2', 'ind1=" "' in xml and 'ind2=" "' in xml)
    check('subfield code присутствует', 'code="a"' in xml)

    # bare-string поле >= 010 тоже идёт как controlfield (см. normalize -> bare)
    bare = {'005': '20240101120000'}
    xb = to_marcxml(bare)
    check('bare scalar 005 -> controlfield', '<controlfield' in xb or
          ':controlfield' in xb)
    rt = from_marcxml(xb)
    check('controlfield -> bare string на разборе', rt == {'005': ['20240101120000']})


def namespace_checks():
    print('-- namespace: дефолтный MARC21slim и namespace=None')
    rec = {'200': {'a': 'T'}}
    xml_ns = to_marcxml(rec)
    check('дефолт несёт xmlns MARC21slim', MARC21_SLIM_NS in xml_ns)
    xml_no = to_marcxml(rec, namespace=None)
    check('namespace=None -> без xmlns', MARC21_SLIM_NS not in xml_no)
    # разбор устойчив к обоим
    check('разбор namespaced == normalize', from_marcxml(xml_ns) == normalize(rec))
    check('разбор без ns == normalize', from_marcxml(xml_no) == normalize(rec))


def collection_checks():
    print('-- коллекция <collection> round-trip (mass)')
    recs = [
        {'001': '1', '200': {'a': 'Первая'}},
        {'001': '2', '200': {'a': 'Вторая'}, '700': [{'a': 'A'}, {'a': 'B'}]},
    ]
    xml = to_marcxml_collection(recs)
    back = from_marcxml_collection(xml)
    check('коллекция: число записей', len(back) == 2)
    check('коллекция: запись[0] == normalize', back[0] == normalize(recs[0]))
    check('коллекция: запись[1] == normalize', back[1] == normalize(recs[1]))

    # без namespace
    back_no = from_marcxml_collection(to_marcxml_collection(recs, namespace=None))
    check('коллекция без ns == normalize', back_no == [normalize(r) for r in recs])

    # пустая коллекция
    empty = to_marcxml_collection([])
    check('пустая коллекция -> []', from_marcxml_collection(empty) == [])

    # одиночный <record> как вход коллекции -> список из одного
    single = to_marcxml(recs[0])
    check('одиночный record в from_collection -> [r]',
          from_marcxml_collection(single) == [normalize(recs[0])])


def robustness_checks():
    print('-- робастность: битый XML -> MarcXmlError / []')
    broken = False
    try:
        from_marcxml('<record><datafield tag="200"></record>')  # незакрытый
    except MarcXmlError:
        broken = True
    check('битый XML (одиночный) -> MarcXmlError', broken)

    empty = False
    try:
        from_marcxml('')
    except MarcXmlError:
        empty = True
    check('пустой вход -> MarcXmlError', empty)

    none = False
    try:
        from_marcxml(None)
    except MarcXmlError:
        none = True
    check('None -> MarcXmlError', none)

    check('битый XML (коллекция) -> []',
          from_marcxml_collection('<collection><record</collection>') == [])
    check('пустой вход (коллекция) -> []', from_marcxml_collection('') == [])
    check('None (коллекция) -> []', from_marcxml_collection(None) == [])

    # валидная коллекция с пустым record -> пустой dict в списке
    only_leader = (
        '<collection xmlns="%s"><record><leader>x</leader></record>'
        '<record><controlfield tag="001">9</controlfield></record></collection>'
        % MARC21_SLIM_NS
    )
    out = from_marcxml_collection(only_leader)
    check('record без полей -> {} в списке', out == [{}, {'001': ['9']}])


def main():
    roundtrip_checks()
    cyrillic_checks()
    controlfield_vs_datafield_checks()
    namespace_checks()
    collection_checks()
    robustness_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
