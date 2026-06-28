#!/usr/bin/env python3
"""Тесты inforost — коннектор импорта оцифровки инфороста (трек «Оцифровка», #240).

Покрыто (чистые мапперы + own-store-журнал на :memory: + фейковые часы):
  * map_item: 200^a = title, source 'inforost:<id>', вид 900^b = '08';
  * map_item: пустой author/year НЕ создают 700/210; 200 и source всегда есть;
  * item_assets: собирает URL из pages[].image; устойчив к отсутствию pages/None;
  * map_collection: slug из id (lower), items с source_id/caption/assets;
  * parse_export: сводка collections_total/items_total/assets_total верна;
  * устойчивость parse_export к пустому/None экспорту (defensive);
  * журнал record идемпотентен (повторный source_id -> не дубль, seen True);
  * import_log: new/skipped счёт корректен на первом и повторном прогоне.

Запуск: py -3.12 tests/test_inforost.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import inforost as ir

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Фейковые часы — детерминизм created_at.
class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-06-28T00:00:%02dZ' % self.t


def _store():
    return ir.InforostImportStore(':memory:', now=Clock())


def _service():
    return ir.InforostService(store=_store())


# Документированная форма инфорост-экспорта: 2 коллекции с разным числом страниц.
def _export():
    return {
        'collections': [
            {
                'id': 'c1', 'title': 'Афиши 1920-х', 'description': 'Театр',
                'items': [
                    {'id': 'i1', 'title': 'Афиша Чайки', 'author': 'Театр',
                     'year': '1925',
                     'pages': [
                         {'no': 1, 'image': 'https://inforost/i1/1.jpg'},
                         {'no': 2, 'image': 'https://inforost/i1/2.jpg'},
                     ]},
                    {'id': 'i2', 'title': 'Афиша Чайки II',
                     'pages': [
                         {'no': 1, 'image': 'https://inforost/i2/1.jpg'},
                     ]},
                ],
            },
            {
                'id': 'C2', 'title': 'Рукописи', 'description': '',
                'items': [
                    {'id': 'i3', 'title': 'Письмо', 'author': 'Автор',
                     'year': '1910',
                     'pages': [
                         {'no': 1, 'image': 'https://inforost/i3/1.jpg'},
                         {'no': 2, 'image': 'https://inforost/i3/2.jpg'},
                         {'no': 3, 'image': 'https://inforost/i3/3.jpg'},
                     ]},
                ],
            },
        ]
    }
    # c1: 2 позиции (3 образа), C2: 1 позиция (3 образа) -> items 3, assets 6.


def map_item_checks():
    print('-- map_item: tag-keyed запись Biblio')
    rec = ir.map_item({'id': 'i1', 'title': 'Афиша Чайки', 'author': 'Театр',
                       'year': '1925'})
    check('200^a = title', rec['200'] == [{'a': 'Афиша Чайки'}])
    check('source = inforost:i1', rec['source'] == 'inforost:i1')
    check("вид 900^b = '08'", rec['900'] == [{'b': '08'}])
    check('700^a = author', rec['700'] == [{'a': 'Театр'}])
    check('210^d = year', rec['210'] == [{'d': '1925'}])
    # Кириллица в заглавии цела.
    check('кириллица в 200^a цела', rec['200'][0]['a'] == 'Афиша Чайки')


def map_item_empty_checks():
    print('-- map_item: пустые поля опускаются (кроме 200/source)')
    rec = ir.map_item({'id': 'i9', 'title': 'Только заглавие'})
    check('пустой author -> нет 700', '700' not in rec)
    check('пустой year -> нет 210', '210' not in rec)
    check('200 присутствует всегда', rec['200'] == [{'a': 'Только заглавие'}])
    check('source присутствует всегда', rec['source'] == 'inforost:i9')
    check("900^b = '08' даже у голой позиции", rec['900'] == [{'b': '08'}])
    # Совсем пустая позиция: 200 пустой, source с пустым хвостом, 900 фикс.
    bare = ir.map_item({})
    check('пустая позиция: 200 пустой', bare['200'] == [{'a': ''}])
    check('пустая позиция: source хвост пуст', bare['source'] == 'inforost:')
    check('пустая позиция: нет 700/210', '700' not in bare and '210' not in bare)


def item_assets_checks():
    print('-- item_assets: URL образов страниц')
    assets = ir.item_assets({'id': 'i1', 'pages': [
        {'no': 1, 'image': 'https://inforost/i1/1.jpg'},
        {'no': 2, 'image': 'https://inforost/i1/2.jpg'},
    ]})
    check('собрал 2 URL по порядку',
          assets == ['https://inforost/i1/1.jpg', 'https://inforost/i1/2.jpg'])
    check('без pages -> []', ir.item_assets({'id': 'x'}) == [])
    check('pages=None -> []', ir.item_assets({'pages': None}) == [])
    check('страница без image пропущена',
          ir.item_assets({'pages': [{'no': 1}, {'image': 'u'}]}) == ['u'])
    check('item=None устойчиво -> []', ir.item_assets(None) == [])


def map_collection_checks():
    print('-- map_collection: выставка-форма')
    coll = ir.map_collection({
        'id': 'C1', 'title': 'Афиши', 'description': 'Театр',
        'items': [
            {'id': 'i1', 'title': 'Афиша', 'pages': [{'image': 'u1'}]},
            {'id': 'i2', 'title': 'Афиша 2', 'pages': []},
        ],
    })
    check('slug из id (lower)', coll['slug'] == 'c1')
    check('title перенесён', coll['title'] == 'Афиши')
    check('description перенесён', coll['description'] == 'Театр')
    check('2 позиции', len(coll['items']) == 2)
    check('item source_id', coll['items'][0]['source_id'] == 'i1')
    check('item caption = title', coll['items'][0]['caption'] == 'Афиша')
    check('item assets', coll['items'][0]['assets'] == ['u1'])
    # slug непуст даже при пустом id.
    check('slug непуст при пустом id',
          ir.map_collection({'id': ''})['slug'] == 'collection')
    # Без items устойчиво -> [].
    check('без items -> []', ir.map_collection({'id': 'c'})['items'] == [])


def parse_export_checks():
    print('-- parse_export: сводный план импорта (dry-run)')
    plan = ir.parse_export(_export())
    check('collections_total = 2', plan['collections_total'] == 2)
    check('items_total = 3', plan['items_total'] == 3)
    check('assets_total = 6', plan['assets_total'] == 6)
    check('records = items_total (3)', len(plan['records']) == 3)
    check('collections — выставка-формы', len(plan['collections']) == 2)
    # records — это map_item каждой позиции (вид оцифровки фиксирован).
    check('каждая record: вид 08',
          all(r['900'] == [{'b': '08'}] for r in plan['records']))
    check('slug второй коллекции lower', plan['collections'][1]['slug'] == 'c2')
    check('record source первой позиции', plan['records'][0]['source'] == 'inforost:i1')


def parse_export_defensive_checks():
    print('-- parse_export: устойчивость к пустому/None')
    empty = ir.parse_export({})
    check('пустой dict: collections_total 0', empty['collections_total'] == 0)
    check('пустой dict: items_total 0', empty['items_total'] == 0)
    check('пустой dict: assets_total 0', empty['assets_total'] == 0)
    check('пустой dict: records []', empty['records'] == [])
    none = ir.parse_export(None)
    check('None: collections_total 0', none['collections_total'] == 0)
    check('collections=None устойчиво',
          ir.parse_export({'collections': None})['collections_total'] == 0)
    # Коллекция без items не валит сводку.
    one = ir.parse_export({'collections': [{'id': 'c', 'title': 't'}]})
    check('коллекция без items: items_total 0', one['items_total'] == 0)
    check('коллекция без items: collections_total 1', one['collections_total'] == 1)


def store_record_checks():
    print('-- InforostImportStore: record идемпотентен')
    s = _store()
    r1 = s.record('t1', 'i1', 'item', 'Афиша')
    check('record вернул строку', r1['source_id'] == 'i1' and r1['kind'] == 'item')
    check('seen True после record', s.seen('t1', 'i1') is True)
    check('seen False для другого', s.seen('t1', 'i2') is False)
    # Повторный source_id не плодит дубль (INSERT OR IGNORE).
    s.record('t1', 'i1', 'item', 'Афиша (повтор)')
    check('повтор не плодит дубль', len(s.for_tenant('t1')) == 1)
    check('created_at от первой записи сохранён',
          s.record('t1', 'i1', 'item', 'x')['created_at'] == r1['created_at'])
    # Изоляция тенантов: тот же source_id в другом тенанте независим.
    s.record('t2', 'i1', 'item', 'Афиша')
    check('тенанты изолированы', s.seen('t2', 'i1') and len(s.for_tenant('t2')) == 1)
    check('for_tenant t1 не задет', len(s.for_tenant('t1')) == 1)


def service_import_log_checks():
    print('-- InforostService: import_log new/skipped')
    svc = _service()
    data = _export()
    # plan — тонкая обёртка над parse_export.
    check('plan == parse_export', svc.plan(data) == ir.parse_export(data))
    # Первый прогон: 2 коллекции + 3 позиции = 5 объектов, все новые.
    res1 = svc.import_log('t1', data)
    check('первый прогон new = 5', res1['new'] == 5)
    check('первый прогон skipped = 0', res1['skipped'] == 0)
    check('plan в ответе присутствует', res1['plan']['items_total'] == 3)
    check('is_imported после прогона (коллекция)', svc.is_imported('t1', 'c1') is True)
    check('is_imported после прогона (позиция)', svc.is_imported('t1', 'i1') is True)
    # Повторный прогон: всё уже было -> new 0, skipped 5 (идемпотентность).
    res2 = svc.import_log('t1', data)
    check('повторный прогон new = 0', res2['new'] == 0)
    check('повторный прогон skipped = 5', res2['skipped'] == 5)
    check('журнал не разросся (5 записей)', len(svc.store.for_tenant('t1')) == 5)
    # Другой тенант — снова всё новое.
    res3 = svc.import_log('t2', data)
    check('другой тенант: new = 5 снова', res3['new'] == 5)


def main():
    map_item_checks()
    map_item_empty_checks()
    item_assets_checks()
    map_collection_checks()
    parse_export_checks()
    parse_export_defensive_checks()
    store_record_checks()
    service_import_log_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
