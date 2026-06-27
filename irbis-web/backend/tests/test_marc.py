#!/usr/bin/env python3
"""Тесты MARC ISO 2709 — импорт/экспорт (Каталогизатор/Утилиты обмена данными).

Покрыто:
  * round-trip ОДНОЙ записи: подполя (200^a/^f), повторяющиеся поля (700 x2),
    контрольное/скалярное поле (101/10-как-строка), кириллица (utf-8 multibyte);
  * структура ISO 2709: leader длиной ровно 24, корректные позиции length/base,
    directory кратен 12 и его tag/length/offset согласованы с данными,
    разделители \x1f (подполя) / \x1e (FT) / \x1d (RT) на местах;
  * export_batch + import_batch round-trip списка записей (включая кириллицу);
  * пустой/битый вход: пустая запись, b'', None, мусор -> MarcError / [].

Запуск: py -3.12 tests/test_marc.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import marc
from access.marc import (
    to_iso2709, from_iso2709, export_batch, import_batch, normalize,
    MarcError, FT, RT, SF, LEADER_LEN,
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


# Эталонная запись: подполя, повтор, контрольное, скаляр, кириллица.
SAMPLE = {
    '200': {'a': 'Война и мир', 'f': 'Толстой Л.Н.'},
    '700': [{'a': 'Толстой'}, {'a': 'Иванов'}],
    '101': 'rus',
    '10': {'a': '5-7654-0001-X'},
    '001': '12345',                      # контрольное поле (00X) — скаляр
}


def roundtrip_single_checks():
    print('-- round-trip одной записи (подполя/повтор/контроль/кириллица)')
    blob = to_iso2709(SAMPLE)
    check('to_iso2709 -> bytes', isinstance(blob, bytes) and len(blob) > 24)
    got = from_iso2709(blob)
    check('round-trip == normalize(record)', got == normalize(SAMPLE))

    check('подполя 200^a/^f сохранены',
          got['200'] == [{'a': 'Война и мир', 'f': 'Толстой Л.Н.'}])
    check('повторяющееся 700 -> список из 2',
          got['700'] == [{'a': 'Толстой'}, {'a': 'Иванов'}])
    check('контрольное 001 -> голая строка', got['001'] == ['12345'])
    check('скалярное 101 -> голая строка', got['101'] == ['rus'])
    # тег '10' нормализуется в 3-символьный '010' (как в directory ISO 2709)
    check('подполе 10^a (ISBN) сохранено под тегом 010',
          got['010'] == [{'a': '5-7654-0001-X'}])
    check('кириллица не побилась (utf-8)',
          got['200'][0]['a'] == 'Война и мир')


def leader_directory_checks():
    print('-- leader(24) + directory корректны (байтовые длины/смещения)')
    blob = to_iso2709(SAMPLE)
    leader = blob[0:LEADER_LEN]
    check('leader длиной ровно 24', len(leader) == 24)

    rec_len = int(leader[0:5])
    check('leader[0:5] = полная длина записи в байтах', rec_len == len(blob))

    base = int(leader[12:17])
    check('base address указывает за directory (на FT данных)',
          blob[base - 1:base] == FT)
    check('leader[10:12] indicator/subfield count = 22', leader[10:12] == b'22')
    check('запись завершается RT (\\x1d)', blob.endswith(RT))

    # directory: между leader и base, минус хвостовой FT, кратен 12.
    dir_region = blob[LEADER_LEN:base]
    check('directory завершается FT', dir_region.endswith(FT))
    dir_bytes = dir_region[:-1]
    check('directory кратен 12', len(dir_bytes) % 12 == 0)

    # проверим, что каждая запись directory реально адресует поле, кончающееся FT
    data_region = blob[base:]
    ok = True
    n_entries = len(dir_bytes) // 12
    for k in range(n_entries):
        e = dir_bytes[k * 12:(k + 1) * 12]
        length = int(e[3:7])
        offset = int(e[7:12])
        seg = data_region[offset:offset + length]
        if len(seg) != length or not seg.endswith(FT):
            ok = False
            break
    check('каждая запись directory адресует поле, кончающееся FT', ok)
    check('число записей directory = числу инстансов полей',
          n_entries == sum(len(v) for v in normalize(SAMPLE).values()))

    # разделитель подполя присутствует у поля 200
    check('разделитель подполя \\x1f присутствует', SF in blob)


def normalize_checks():
    print('-- normalize: scalar|dict|list единообразно, пустые отброшены')
    n = normalize({'101': 'rus', '200': {'a': 'X'}, '700': [{'a': 'A'}]})
    check('скаляр -> список из строки', n['101'] == ['rus'])
    check('dict -> список из dict', n['200'] == [{'a': 'X'}])
    check('list сохранён', n['700'] == [{'a': 'A'}])
    n2 = normalize({'200': {'a': '', 'f': None}, '300': '', '101': 'rus'})
    check('пустые подполя/скаляры отброшены', '200' not in n2 and '300' not in n2)
    check('непустое поле остаётся', n2['101'] == ['rus'])
    check('пустая запись -> {}', normalize({}) == {} and normalize(None) == {})


def batch_checks():
    print('-- export_batch + import_batch round-trip списка')
    recs = [
        SAMPLE,
        {'200': {'a': 'Идиот', 'f': 'Достоевский Ф.М.'}, '101': 'rus'},
        {'200': {'a': 'Hello'}, '700': [{'a': 'Smith'}]},
    ]
    stream = export_batch(recs)
    check('export_batch -> bytes', isinstance(stream, bytes))
    check('export_batch = конкатенация to_iso2709',
          stream == b''.join(to_iso2709(r) for r in recs))
    check('в потоке столько RT, сколько записей', stream.count(RT) == len(recs))

    back = import_batch(stream)
    check('import_batch вернул столько же записей', len(back) == len(recs))
    check('батч round-trip == [normalize(r)]',
          back == [normalize(r) for r in recs])
    check('вторая запись (кириллица) цела',
          back[1]['200'][0]['a'] == 'Идиот')

    check('export_batch([]) -> b""', export_batch([]) == b'')
    check('export_batch(None) -> b""', export_batch(None) == b'')


def empty_and_broken_checks():
    print('-- пустой/битый вход: MarcError / []')
    # пустая запись сериализуется в валидный скелет, парсится в {}
    skeleton = to_iso2709({})
    check('to_iso2709({}) -> валидный скелет (>=26 байт)', len(skeleton) >= 26)
    check('leader скелета длиной 24', len(skeleton) >= 24 and int(skeleton[0:5]) == len(skeleton))
    check('from_iso2709(скелет) -> {}', from_iso2709(skeleton) == {})

    # import_batch устойчив к пустому
    check('import_batch(b"") -> []', import_batch(b'') == [])
    check('import_batch(None) -> []', import_batch(None) == [])
    check('import_batch(пробелы) -> []', import_batch(b'   \r\n') == [])

    # from_iso2709 на пустом/битом -> MarcError
    def raises(fn):
        try:
            fn()
        except MarcError:
            return True
        return False

    check('from_iso2709(b"") -> MarcError', raises(lambda: from_iso2709(b'')))
    check('from_iso2709(None) -> MarcError', raises(lambda: from_iso2709(None)))
    check('from_iso2709(короткий мусор) -> MarcError',
          raises(lambda: from_iso2709(b'abc')))
    check('from_iso2709(битый base address) -> MarcError',
          raises(lambda: from_iso2709(b'00100xxxxxxxZZZZZ4500' + b'rest!!!')))

    # битая запись внутри батча пропускается, валидная — проходит
    good = to_iso2709(SAMPLE)
    mixed = b'GARBAGE-NO-RT-VALID-ONLY-AFTER' + RT + good
    back = import_batch(mixed)
    check('import_batch пропускает битую запись, берёт валидную',
          len(back) == 1 and back[0] == normalize(SAMPLE))


def control_field_checks():
    print('-- контрольные поля 00X пишутся без индикаторов/подполей')
    blob = to_iso2709({'001': '42', '005': '20260627', '200': {'a': 'T'}})
    got = from_iso2709(blob)
    check('001/005 -> голые строки', got['001'] == ['42'] and got['005'] == ['20260627'])
    # у контрольных полей в данных НЕ должно быть \x1f-сегментов; проверим, что
    # round-trip это даёт (нет ложного подполя)
    check('контрольное поле не получило подполей',
          all(not isinstance(i, dict) for i in got['001']))
    check('обычное поле 200 осталось dict-инстансом',
          isinstance(got['200'][0], dict))


def main():
    roundtrip_single_checks()
    leader_directory_checks()
    normalize_checks()
    batch_checks()
    empty_and_broken_checks()
    control_field_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
