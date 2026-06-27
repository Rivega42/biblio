#!/usr/bin/env python3
"""Тесты IIIF-генератора (трек «Оцифровка»): Canvas/Manifest/Collection/Range v3.

Покрыто (чистые функции, без I/O):
  * `canvas` — type=Canvas, размеры, painting-аннотация, body=Image, target;
  * `manifest` — @context/type/label/items count, маппинг metadata (пары -> карты);
  * `manifest_from_pages` — N канв с правильными id, выбор image vs base_image_url;
  * `collection` — items=ссылки на манифесты;
  * `range_toc` — оглавление по id канв;
  * json.dumps-абельность всех результатов (кириллица в label/metadata).

Запуск: py -3.12 tests/test_iiif.py ; в агрегаторе test_access.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import iiif

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def canvas_checks():
    print('-- canvas: Canvas v3 + painting-аннотация на образ')
    c = iiif.canvas('http://x/m1/canvas/1', 'Страница 1',
                    'http://x/img/1.jpg', 1200, 1600)
    check('type=Canvas', c['type'] == 'Canvas')
    check('id канвы', c['id'] == 'http://x/m1/canvas/1')
    check('label языковая карта ru', c['label'] == {'ru': ['Страница 1']})
    check('width/height канвы', c['width'] == 1200 and c['height'] == 1600)
    check('один AnnotationPage', len(c['items']) == 1)
    ap = c['items'][0]
    check('AnnotationPage type', ap['type'] == 'AnnotationPage')
    check('одна Annotation', len(ap['items']) == 1)
    ann = ap['items'][0]
    check('Annotation type', ann['type'] == 'Annotation')
    check('motivation=painting', ann['motivation'] == 'painting')
    check('target=canvas_id', ann['target'] == 'http://x/m1/canvas/1')
    body = ann['body']
    check('body id=image_url', body['id'] == 'http://x/img/1.jpg')
    check('body type=Image', body['type'] == 'Image')
    check('body format=image/jpeg', body['format'] == 'image/jpeg')
    check('body width/height', body['width'] == 1200 and body['height'] == 1600)
    check('canvas json-сериализуем', json.dumps(c) is not None)


def manifest_checks():
    print('-- manifest: корень Manifest v3 + metadata')
    c = iiif.canvas('http://x/m1/canvas/1', '1', 'http://x/1.jpg', 800, 1000)
    m = iiif.manifest('http://x/m1', 'Издание', [c])
    check('@context IIIF v3', m['@context'] == iiif.IIIF_CONTEXT)
    check('type=Manifest', m['type'] == 'Manifest')
    check('id манифеста', m['id'] == 'http://x/m1')
    check('label ru', m['label'] == {'ru': ['Издание']})
    check('items = 1 канва', len(m['items']) == 1 and m['items'][0] is c)
    check('без metadata по умолчанию', 'metadata' not in m)
    m2 = iiif.manifest('http://x/m2', 'Книга', [],
                       metadata=[('Автор', 'Иванов'), ('Год', '2021')])
    check('metadata из 2 пар', len(m2['metadata']) == 2)
    md0 = m2['metadata'][0]
    check('metadata label-карта', md0['label'] == {'ru': ['Автор']})
    check('metadata value-карта', md0['value'] == {'ru': ['Иванов']})
    check('manifest json-сериализуем', json.dumps(m2) is not None)


def manifest_from_pages_checks():
    print('-- manifest_from_pages: страницы -> канвы')
    pages = [
        {'page_no': 1, 'image': 'http://x/a.jpg', 'width': 800, 'height': 600},
        {'page_no': 2, 'width': 800, 'height': 600},
    ]
    m = iiif.manifest_from_pages('http://x/m1', 'Альбом',
                                 'http://x/base/', pages)
    check('type=Manifest', m['type'] == 'Manifest')
    check('2 канвы из 2 страниц', len(m['items']) == 2)
    check('id канвы 1', m['items'][0]['id'] == 'http://x/m1/canvas/1')
    check('id канвы 2', m['items'][1]['id'] == 'http://x/m1/canvas/2')
    body1 = m['items'][0]['items'][0]['items'][0]['body']
    check('image из page', body1['id'] == 'http://x/a.jpg')
    body2 = m['items'][1]['items'][0]['items'][0]['body']
    check('image из base+page_no', body2['id'] == 'http://x/base/2')
    check('label канвы = номер', m['items'][0]['label'] == {'ru': ['1']})
    mm = iiif.manifest_from_pages('http://x/m3', 'С метой', 'http://x/b/',
                                  [{'page_no': 1, 'image': 'http://x/p.jpg',
                                    'width': 10, 'height': 20}],
                                  metadata=[('Шифр', 'Ф1-123')])
    check('metadata прокинут', mm['metadata'][0]['value'] == {'ru': ['Ф1-123']})
    check('пустые pages -> 0 канв',
          iiif.manifest_from_pages('http://x/e', 'Пусто', 'http://x/',
                                   [])['items'] == [])
    check('from_pages json-сериализуем', json.dumps(m) is not None)


def collection_checks():
    print('-- collection: Collection v3 ссылок на манифесты')
    col = iiif.collection('http://x/col', 'Фонд оцифровки',
                          [('http://x/m1', 'Книга 1'),
                           ('http://x/m2', 'Книга 2')])
    check('@context', col['@context'] == iiif.IIIF_CONTEXT)
    check('type=Collection', col['type'] == 'Collection')
    check('label ru', col['label'] == {'ru': ['Фонд оцифровки']})
    check('2 items', len(col['items']) == 2)
    it0 = col['items'][0]
    check('item type=Manifest', it0['type'] == 'Manifest')
    check('item id', it0['id'] == 'http://x/m1')
    check('item label-карта', it0['label'] == {'ru': ['Книга 1']})
    check('пустой список ссылок',
          iiif.collection('http://x/c', 'Пусто', [])['items'] == [])
    check('collection json-сериализуем', json.dumps(col) is not None)


def range_toc_checks():
    print('-- range_toc: оглавление (Range) по id канв')
    r = iiif.range_toc('http://x/m1', 'Оглавление',
                       ['http://x/m1/canvas/1', 'http://x/m1/canvas/2'])
    check('id = manifest_id/range/top', r['id'] == 'http://x/m1/range/top')
    check('type=Range', r['type'] == 'Range')
    check('label ru', r['label'] == {'ru': ['Оглавление']})
    check('2 ссылки на канвы', len(r['items']) == 2)
    check('item type=Canvas', r['items'][0]['type'] == 'Canvas')
    check('item id=canvas_id', r['items'][0]['id'] == 'http://x/m1/canvas/1')
    check('range json-сериализуем', json.dumps(r) is not None)


def main():
    canvas_checks()
    manifest_checks()
    manifest_from_pages_checks()
    collection_checks()
    range_toc_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
