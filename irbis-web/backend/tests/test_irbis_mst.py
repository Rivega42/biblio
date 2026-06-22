#!/usr/bin/env python3
"""Тесты офлайн-адаптера мастер-файлов ИРБИС64 (#225, эпик #223 — tools/irbis_mst.py).

Проверяют прямое чтение `.mst`+`.xrf` с диска (без сервера) на **синтетических**
фикстурах: пара `.mst`/`.xrf` строится в памяти/во временном каталоге функцией
``build_mst_xrf`` (точная инверсия парсера) — НИКАКИХ реальных данных/ПДн.

Покрытие:
  1. форма записи: ``read_record`` возвращает канон ``{поле: [{подполе: значение}]}``
     (как ``access.catalog`` / ``tools.migrate_irbis``); подполя -> {код: значение}
     с кодами в нижнем регистре; повторяющееся поле -> список экземпляров.
  2. голое поле без '^' -> голая строка (а не dict).
  3. CP1251: кириллица декодируется корректно.
  4. удаление: запись с битом STATUS 0x01 И запись с флагом удаления в `.xrf`
     обе пропускаются (``read_record`` -> None, ``read_records`` их не отдаёт).
  5. ``max_mfn`` = NXTMFN-1 из управляющей записи; ``read_records`` перебирает
     все живые записи; ``list_databases`` находит БД по ``<db>.mst``.
  6. защита: короткая/битая запись, MFN вне диапазона, директорий-вне-границ ->
     пропуск со счётчиком предупреждений, без исключения.

Запускается автономно (дом. стиль tests/test_migrate.py)::

    py -3 tests/test_irbis_mst.py   ->  'ok …' + 'N passed, M failed', exit!=0

Без зависимости от живого сервера и без реальных файлов БД (CI — Linux, без Datai).
"""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import irbis_mst
from tools.irbis_mst import (
    build_mst_xrf, read_record, read_records, max_mfn, list_databases,
    STATUS_DELETED, XRF_DELETED_FLAG, MST_LEADER_SIZE, SYSTEM_GUID_TAG,
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


# --------------------------------------------------------------------------- #
# Помощник: записать синтетическую пару .mst/.xrf во временный каталог БД.
# --------------------------------------------------------------------------- #
def _write_db(tmp, db, records, deleted_mfns=()):
    """Создать ``<tmp>/<db>/<db>.mst|.xrf`` из записей. Возвращает data_path=tmp."""
    db_dir = os.path.join(tmp, db)
    os.makedirs(db_dir, exist_ok=True)
    mst, xrf = build_mst_xrf(records, deleted_mfns=deleted_mfns)
    with open(os.path.join(db_dir, db + '.mst'), 'wb') as f:
        f.write(mst)
    with open(os.path.join(db_dir, db + '.xrf'), 'wb') as f:
        f.write(xrf)
    return tmp


# Набор записей с подполями, голым полем, кириллицей, повтором и удалённой.
def _sample_records():
    return [
        # MFN 1 — заглавие с подполями + голое поле языка + повтор автора +
        # обязательное 920 (вид документа), чтобы запись проходила ФЛК.
        {
            '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.'}],
            '101': ['rus'],
            '700': [{'a': 'Иванова И.И.'}, {'a': 'Петров П.П.'}],
            '910': [{'a': '0', 'b': '1024365'}],
            '920': ['PAZK'],
        },
        # MFN 2 — простая запись с кириллицей в значении.
        {
            '200': [{'a': 'Библиотечное дело'}],
            '610': ['каталогизация'],
        },
        # MFN 3 — будет помечена удалённой по STATUS.
        {
            '200': [{'a': 'Удалённая запись'}],
        },
        # MFN 4 — будет помечена удалённой по флагу .xrf.
        {
            '200': [{'a': 'Тоже удалена'}],
        },
    ]


# --------------------------------------------------------------------------- #
# 1+2+3. Форма записи, подполя, голые поля, CP1251.
# --------------------------------------------------------------------------- #
def shape_checks():
    with tempfile.TemporaryDirectory() as tmp:
        _write_db(tmp, 'TEST', _sample_records())
        rec = read_record(tmp, 'TEST', 1)
        check('read_record возвращает dict', isinstance(rec, dict))
        check('поле -> список экземпляров', isinstance(rec.get('200'), list))
        inst = rec['200'][0]
        check('подполя -> dict {код: значение}', isinstance(inst, dict))
        check('подполе ^a (нижний регистр кода)', inst.get('a') == 'Основы каталогизации')
        check('подполе ^f', inst.get('f') == 'Иванова И.И.')
        check('CP1251 кириллица декодирована', 'каталогизации' in inst['a'])

        # голое поле без '^' -> голая строка
        check('голое поле 101 -> строка', rec.get('101') == ['rus'])

        # повторяющееся поле -> список из 2 экземпляров
        authors = rec.get('700')
        check('повтор поля -> 2 экземпляра', isinstance(authors, list) and len(authors) == 2)
        check('повтор: первый автор', authors[0].get('a') == 'Иванова И.И.')
        check('повтор: второй автор', authors[1].get('a') == 'Петров П.П.')

        # 910 экземпляр (как у мигратора): ^a статус, ^b инв.№
        ex = rec['910'][0]
        check('910^a статус', ex.get('a') == '0')
        check('910^b инв.номер', ex.get('b') == '1024365')

        # форма совместима с CatalogStore.save (round-trip без падения)
        from access.catalog import CatalogStore
        cs = CatalogStore(':memory:')
        res = cs.save('TEST', rec)
        check('запись сохраняется в CatalogStore', res.get('saved'))


# --------------------------------------------------------------------------- #
# 4. Удаление: и по STATUS-биту, и по флагу .xrf.
# --------------------------------------------------------------------------- #
def deleted_checks():
    with tempfile.TemporaryDirectory() as tmp:
        # MFN 3 удалена через STATUS; MFN 4 — через флаг в .xrf.
        _write_db(tmp, 'TEST', _sample_records(), deleted_mfns={3, 4})

        check('живая запись 1 читается', read_record(tmp, 'TEST', 1) is not None)
        check('живая запись 2 читается', read_record(tmp, 'TEST', 2) is not None)
        check('удалённая по STATUS (mfn 3) -> None', read_record(tmp, 'TEST', 3) is None)
        check('удалённая по .xrf-флагу (mfn 4) -> None', read_record(tmp, 'TEST', 4) is None)

        # read_records отдаёт только живые
        live = list(read_records(tmp, 'TEST'))
        mfns = [m for (m, _r) in live]
        check('read_records: только живые MFN [1,2]', mfns == [1, 2])
        check('read_records: записи — каноничные dict',
              all(isinstance(r, dict) and 'a' in r['200'][0] for (_m, r) in live))


# --------------------------------------------------------------------------- #
# Раздельная проверка флага удаления в .xrf (без STATUS-бита тоже срабатывает).
# --------------------------------------------------------------------------- #
def xrf_deleted_flag_checks():
    with tempfile.TemporaryDirectory() as tmp:
        # 1 живая запись; вручную выставим старший бит её XRF-слова.
        db_dir = os.path.join(tmp, 'X')
        os.makedirs(db_dir)
        mst, xrf = build_mst_xrf([{'200': [{'a': 'Запись'}]}])
        with open(os.path.join(db_dir, 'X.mst'), 'wb') as f:
            f.write(mst)
        # Перепишем XRF-слот 1: тот же offset, но с флагом удаления.
        low, _high = struct.unpack('>2i', xrf[:8])
        low_u = (low & 0xffffffff) | XRF_DELETED_FLAG
        signed = low_u - 0x100000000 if low_u & 0x80000000 else low_u
        patched = struct.pack('>2i', signed, 0) + xrf[8:12]
        with open(os.path.join(db_dir, 'X.xrf'), 'wb') as f:
            f.write(patched)
        check('флаг удаления в .xrf -> запись пропущена',
              read_record(tmp, 'X', 1) is None)


# --------------------------------------------------------------------------- #
# 5. max_mfn, read_records счёт, list_databases.
# --------------------------------------------------------------------------- #
def control_and_listing_checks():
    with tempfile.TemporaryDirectory() as tmp:
        _write_db(tmp, 'IBIS', _sample_records())
        _write_db(tmp, 'RDR', [{'30': ['111'], '10': [{'a': 'Тест'}]}])

        check('max_mfn = число записей (4)', max_mfn(tmp, 'IBIS') == 4)
        check('max_mfn RDR = 1', max_mfn(tmp, 'RDR') == 1)

        dbs = list_databases(tmp)
        check('list_databases находит IBIS и RDR', dbs == ['IBIS', 'RDR'])

        # пустая БД -> max_mfn 0, read_records пустой
        _write_db(tmp, 'EMPTY', [])
        check('пустая БД -> max_mfn 0', max_mfn(tmp, 'EMPTY') == 0)
        check('пустая БД -> read_records пуст', list(read_records(tmp, 'EMPTY')) == [])


# --------------------------------------------------------------------------- #
# 6. Защита: битые/короткие записи и MFN вне диапазона не роняют адаптер.
# --------------------------------------------------------------------------- #
def robustness_checks():
    with tempfile.TemporaryDirectory() as tmp:
        _write_db(tmp, 'TEST', _sample_records())

        # MFN вне диапазона -> None, без исключения.
        check('MFN 0 -> None', read_record(tmp, 'TEST', 0) is None)
        check('MFN 999 (вне .xrf) -> None', read_record(tmp, 'TEST', 999) is None)

        # Битая запись: испортим лидер MFN 2 (укажем гигантский NVF) — должна
        # пропуститься со счётчиком предупреждений, остальные читаются.
        warnings = []
        db_dir = os.path.join(tmp, 'BAD')
        os.makedirs(db_dir)
        mst, xrf = build_mst_xrf([
            {'200': [{'a': 'Хорошая'}]},
            {'200': [{'a': 'Плохая'}]},
        ])
        # Найдём offset записи 2 из .xrf и испортим её NVF (лидер +0x14).
        off2 = struct.unpack('>i', xrf[12:16])[0]
        mst_b = bytearray(mst)
        struct.pack_into('>i', mst_b, off2 + 0x14, 0x7fffffff)  # NVF дикий
        with open(os.path.join(db_dir, 'BAD.mst'), 'wb') as f:
            f.write(bytes(mst_b))
        with open(os.path.join(db_dir, 'BAD.xrf'), 'wb') as f:
            f.write(xrf)

        good = read_record(tmp, 'BAD', 1, _warn=warnings.append)
        bad = read_record(tmp, 'BAD', 2, _warn=warnings.append)
        check('битый лидер -> None (без падения)', bad is None)
        check('соседняя живая запись читается', good is not None and good['200'][0]['a'] == 'Хорошая')
        check('порча зафиксирована предупреждением', len(warnings) >= 1)

        # read_records по битой БД не падает и отдаёт только хорошую.
        live = list(read_records(tmp, 'BAD'))
        check('read_records переживает порчу', [m for (m, _r) in live] == [1])

        # Усечённый .mst (запись короче лидера) -> None, без исключения.
        db_dir2 = os.path.join(tmp, 'TRUNC')
        os.makedirs(db_dir2)
        mst2, xrf2 = build_mst_xrf([{'200': [{'a': 'X'}]}])
        with open(os.path.join(db_dir2, 'TRUNC.mst'), 'wb') as f:
            f.write(mst2[:MST_LEADER_SIZE // 2])     # обрезали посреди лидера
        with open(os.path.join(db_dir2, 'TRUNC.xrf'), 'wb') as f:
            f.write(xrf2)
        warns2 = []
        check('усечённая запись -> None',
              read_record(tmp, 'TRUNC', 1, _warn=warns2.append) is None)


# --------------------------------------------------------------------------- #
# 7. Системное поле GUID (MaxInt32) в каноническую запись не попадает.
# --------------------------------------------------------------------------- #
def guid_field_checks():
    with tempfile.TemporaryDirectory() as tmp:
        db_dir = os.path.join(tmp, 'G')
        os.makedirs(db_dir)
        # Запись с GUID-полем (метка 2147483647) + обычным 200.
        rec_fields = {
            str(SYSTEM_GUID_TAG): ['{ACEF1ACE-A93D-4F22-910B-02D35C1547BF}'],
            '200': [{'a': 'С GUID'}],
        }
        mst, xrf = build_mst_xrf([rec_fields])
        with open(os.path.join(db_dir, 'G.mst'), 'wb') as f:
            f.write(mst)
        with open(os.path.join(db_dir, 'G.xrf'), 'wb') as f:
            f.write(xrf)
        rec = read_record(tmp, 'G', 1)
        check('GUID-поле (MaxInt32) исключено из записи',
              str(SYSTEM_GUID_TAG) not in rec)
        check('обычное поле 200 сохранено', rec['200'][0]['a'] == 'С GUID')


# --------------------------------------------------------------------------- #
# 8. Кодировка: CP1251-фикстуры читаются корректно (базовый формат), а UTF-8-
#    поля (встречаются на реальных установках ИРБИС64) — тоже декодируются.
# --------------------------------------------------------------------------- #
def encoding_checks():
    with tempfile.TemporaryDirectory() as tmp:
        # build_mst_xrf пишет в CP1251 — проверяем round-trip кириллицы.
        _write_db(tmp, 'C', [{'200': [{'a': 'Каталогизация и поиск'}]}])
        rec = read_record(tmp, 'C', 1)
        check('CP1251 round-trip кириллицы', rec['200'][0]['a'] == 'Каталогизация и поиск')

        # Соберём запись с UTF-8-полем вручную (как в реальной БД на этой машине).
        db_dir = os.path.join(tmp, 'U')
        os.makedirs(db_dir)
        title = 'Компьютерное моделирование'
        val = ('^a' + title).encode('utf-8')        # UTF-8, не CP1251
        nvf = 1
        base = MST_LEADER_SIZE + nvf * 12
        directory = struct.pack('>3i', 200, 0, len(val))
        mfrl = base + len(val)
        leader = struct.pack('>8i', 1, mfrl, 0, 0, base, nvf, 1, 0x20)
        ctl = struct.pack('>4i', 0, 2, 0, 0) + b'\x00' * (36 - 16)
        rec_bytes = leader + directory + val
        with open(os.path.join(db_dir, 'U.mst'), 'wb') as f:
            f.write(ctl + rec_bytes)
        with open(os.path.join(db_dir, 'U.xrf'), 'wb') as f:
            f.write(struct.pack('>2i', len(ctl), 0) + b'\x00' * 4)
        urec = read_record(tmp, 'U', 1)
        check('UTF-8 поле декодировано корректно', urec['200'][0]['a'] == title)


def main():
    shape_checks()
    deleted_checks()
    xrf_deleted_flag_checks()
    control_and_listing_checks()
    robustness_checks()
    guid_field_checks()
    encoding_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
