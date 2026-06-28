#!/usr/bin/env python3
"""Тесты матрицы доступов: каталог-SSOT + сид дефолт-тарифов + резолвер + вердикты.

Standalone (дом-стиль): py -3.12 tests/test_access_matrix.py
Вписан в раннер tests/test_access.py (module_checks).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import access_matrix as am
from access.tariff_store import TariffStore

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _seeded():
    st = TariffStore(':memory:')
    am.seed_defaults(st)
    return st


def catalog_checks():
    print('-- каталог-SSOT')
    check('разделов >= 12', len(am.SECTIONS) >= 12)
    check('ресурсы несут staff_seats и ocr_pages',
          {'staff_seats', 'ocr_pages'} <= {r['key'] for r in am.RESOURCES})
    rows = am.catalog_rows()
    check('catalog_rows: есть section/function/resource',
          {'section', 'function', 'resource'} == {r['kind'] for r in rows})
    check('ключи функций имеют префикс fn:',
          all(r['item_key'].startswith('fn:') for r in rows if r['kind'] == 'function'))


def seed_checks():
    print('-- сид дефолт-тарифов (идемпотентность)')
    st = TariffStore(':memory:')
    created = am.seed_defaults(st)
    check('создано 3 тарифа', sorted(created) == ['free', 'pro', 'standard'])
    again = am.seed_defaults(st)
    check('повторный сид ничего не создаёт (идемпотентно)', again == [])
    check('list_tariffs -> 3', len(st.list_tariffs()) == 3)


def resolve_checks():
    print('-- резолвер тарифа')
    st = _seeded()
    st.assign_tenant('t_free', 'free')
    st.assign_tenant('t_std', 'standard')
    st.assign_tenant('t_pro', 'pro')

    mf = am.resolve(st, 't_free')
    check('free: configured', mf['configured'] and mf['tariff'] == 'free')
    check('free: opac включён', mf['sections']['opac']['included'])
    check('free: каталогизация ВЫКЛ', not mf['sections']['cataloging']['included'])
    check('free: функция opac.search наследует включённость',
          mf['sections']['opac']['functions']['search']['included'])
    check('free: функция cataloging.marc выкл (раздел выкл)',
          not mf['sections']['cataloging']['functions']['marc']['included'])
    check('free: лимит записей 1000, режим grace',
          mf['caps']['records']['limit'] == 1000 and mf['caps']['records']['enforcement'] == am.ENFORCE_GRACE)

    ms = am.resolve(st, 't_std')
    check('standard: каталогизация ВКЛ', ms['sections']['cataloging']['included'])
    check('standard: оцифровка ВЫКЛ', not ms['sections']['digitization']['included'])
    check('standard: staff_seats=20 block',
          ms['caps']['staff_seats']['limit'] == 20 and ms['caps']['staff_seats']['enforcement'] == am.ENFORCE_BLOCK)

    mp = am.resolve(st, 't_pro')
    check('pro: оцифровка ВКЛ', mp['sections']['digitization']['included'])
    check('pro: записи UNLIMITED', mp['caps']['records']['limit'] is am.UNLIMITED)


def verdict_checks():
    print('-- вердикты доступа')
    st = _seeded()
    st.assign_tenant('t_std', 'standard')
    st.assign_tenant('t_free', 'free')
    ms = am.resolve(st, 't_std')
    check('section_verdict cataloging -> allow', am.section_verdict(ms, 'cataloging') == 'allow')
    check('section_verdict digitization (block) -> deny', am.section_verdict(ms, 'digitization') == 'deny')
    mf = am.resolve(st, 'free')  # неназначенный -> standard? нет: 'free' тенант не назначен -> default standard
    # явный free-тенант:
    mf = am.resolve(st, 't_free')
    check('free section digitization (grace) -> grace', am.section_verdict(mf, 'digitization') == 'grace')

    # cap-вердикты
    v, info = am.cap_verdict(ms, 'records', 99999)
    check('standard records 99999<100000 -> allow', v == 'allow' and info['remaining'] == 1)
    v, _ = am.cap_verdict(ms, 'records', 100000)
    check('standard records 100000 (block) -> deny', v == 'deny')
    v, _ = am.cap_verdict(mf, 'records', 5000)
    check('free records over (grace) -> grace', v == 'grace')
    v, _ = am.cap_verdict(am.resolve(st, 'unknown_tenant'), 'records', 0)
    check('неназначенный тенант -> default standard, records ok', v == 'allow')


def function_override_checks():
    print('-- переопределение функции в админ-ячейке')
    st = _seeded()
    st.assign_tenant('t_pro', 'pro')
    # админ выключает конкретную функцию z3950 в pro (раздел остаётся вкл)
    st.set_entry('pro', am.fn_key('cataloging', 'z3950'), included=False)
    mp = am.resolve(st, 't_pro')
    check('pro: раздел cataloging всё ещё ВКЛ', mp['sections']['cataloging']['included'])
    check('pro: функция z3950 ВЫКЛ (переопределена)',
          not mp['sections']['cataloging']['functions']['z3950']['included'])
    check('function_verdict z3950 (block) -> deny',
          am.function_verdict(mp, 'cataloging', 'z3950') == 'deny')
    check('function_verdict marc (вкл) -> allow',
          am.function_verdict(mp, 'cataloging', 'marc') == 'allow')


def alacarte_checks():
    print('-- à-la-carte пакеты (OCR-страницы)')
    st = _seeded()
    st.assign_tenant('t_pro', 'pro')
    base = am.resolve(st, 't_pro')['caps']['ocr_pages']['limit']
    check('pro ocr_pages база 0', base == 0)
    st.add_addon('t_pro', 'ocr_pages', packs=2, pack_size=1000)
    m = am.resolve(st, 't_pro')
    check('после покупки 2×1000 -> лимит 2000',
          m['caps']['ocr_pages']['limit'] == 2000 and m['caps']['ocr_pages']['addon_units'] == 2000)
    v, info = am.cap_verdict(m, 'ocr_pages', 1999)
    check('ocr_pages 1999<2000 -> allow', v == 'allow' and info['remaining'] == 1)
    v, _ = am.cap_verdict(m, 'ocr_pages', 2000)
    check('ocr_pages 2000 (block) -> deny', v == 'deny')


def failopen_checks():
    print('-- fail-open (тарифы не настроены)')
    st = TariffStore(':memory:')   # пусто
    m = am.resolve(st, 'anytenant')
    check('пустой стор -> permissive (не configured)', not m['configured'])
    check('permissive: всё включено', m['sections']['cataloging']['included'])
    check('permissive: лимиты UNLIMITED', m['caps']['records']['limit'] is am.UNLIMITED)
    check('permissive: section_verdict -> allow', am.section_verdict(m, 'digitization') == 'allow')


def editable_table_checks():
    print('-- данные редактируемой админ-таблицы')
    st = _seeded()
    tbl = am.editable_table(st)
    check('таблица: 3 тарифа-колонки', len(tbl['tariffs']) == 3)
    check('таблица: строки = каталог', len(tbl['rows']) == len(am.catalog_rows()))
    check('таблица: ячейки standard несут section:opac',
          am.section_key('opac') in tbl['cells']['standard'])


def main():
    catalog_checks()
    seed_checks()
    resolve_checks()
    verdict_checks()
    function_override_checks()
    alacarte_checks()
    failopen_checks()
    editable_table_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
