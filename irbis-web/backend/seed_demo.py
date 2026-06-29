#!/usr/bin/env python3
"""seed_demo.py — наполнение own-store ДЕМО-данными (#374), чтобы все экраны были
видны на пред-наполненной базе БЕЗ живого ИРБИС.

Пишет в те же sqlite-файлы, что читает сервер (дефолтные пути в backend/). Поднимать
демо так:

    OWN_SEARCH_DBS=IBIS py -3.12 seed_demo.py        # наполнить
    OWN_SEARCH_DBS=IBIS py -3.12 server.py           # сервер на :8080 (own-store каталог)
    (в frontend/)  npm run dev                       # vite, проксирует /api -> :8080

Идемпотентно: повторный прогон не плодит дубли (каталог сверяется по заглавию,
выставки — по slug, FTS/OCR — по ref). Тематика — Театральная библиотека (контекст
пилота), но это просто демо-контент.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('OWN_SEARCH_DBS', 'IBIS')      # чтобы _api-инстанс был согласован

from core import Api                                  # noqa: E402

DB = 'IBIS'

# --- Каталог: разнообразные записи (автор/тема/год/аннотация/обложка/ПТ) -------- #
# (title, author, year, subject, annotation, cover?, pdf_pages|0)
BOOKS = [
    ('Чайка', 'Чехов А. П.', '1896', 'Русская драматургия', 'Комедия в четырёх действиях.', True, 96),
    ('Вишнёвый сад', 'Чехов А. П.', '1904', 'Русская драматургия', 'Последняя пьеса драматурга.', True, 88),
    ('Гроза', 'Островский А. Н.', '1859', 'Русская драматургия', 'Драма в пяти действиях.', True, 0),
    ('Ревизор', 'Гоголь Н. В.', '1836', 'Русская драматургия', 'Комедия в пяти действиях.', True, 120),
    ('Горе от ума', 'Грибоедов А. С.', '1825', 'Русская драматургия', 'Комедия в стихах.', False, 0),
    ('Гамлет', 'Шекспир У.', '1601', 'Зарубежная драматургия', 'Трагедия принца Датского.', True, 210),
    ('Король Лир', 'Шекспир У.', '1606', 'Зарубежная драматургия', 'Трагедия.', False, 0),
    ('Тартюф', 'Мольер Ж.-Б.', '1664', 'Зарубежная драматургия', 'Комедия о лицемерии.', False, 0),
    ('Сцена и время', 'Мейерхольд В. Э.', '1920', 'Театроведение', 'Статьи о режиссуре и биомеханике.', True, 64),
    ('Работа актёра над собой', 'Станиславский К. С.', '1938', 'Театроведение', 'Основы системы Станиславского.', True, 340),
    ('Моя жизнь в искусстве', 'Станиславский К. С.', '1926', 'Театроведение', 'Мемуары реформатора сцены.', True, 0),
    ('Театральный костюм XVIII века', 'Иванова М. С.', '1998', 'История театра', 'Каталог сценических костюмов.', True, 0),
    ('Декорации русского балета', 'Бенуа А. Н.', '1910', 'Сценография', 'Эскизы и описания постановок.', True, 48),
    ('Афиши императорских театров', 'Сидоров П. К.', '1903', 'История театра', 'Альбом театральных афиш.', True, 0),
    ('Опера и драма', 'Вагнер Р.', '1851', 'Музыкальный театр', 'Трактат о синтезе искусств.', False, 0),
    ('Балетные либретто', 'Петипа М.', '1890', 'Музыкальный театр', 'Сборник либретто классических балетов.', False, 0),
    ('Записки режиссёра', 'Таиров А. Я.', '1921', 'Театроведение', 'О Камерном театре.', True, 0),
    ('Условный театр', 'Евреинов Н. Н.', '1912', 'Театроведение', 'Теория театральности.', False, 0),
    ('Сценическая речь', 'Кнебель М. О.', '1970', 'Сценическая педагогика', 'Учебное пособие.', False, 0),
    ('История русского театра', 'Варнеке Б. В.', '1913', 'История театра', 'От истоков до XX века.', True, 0),
    ('Драматургия Серебряного века', 'Блок А. А.', '1907', 'Русская драматургия', 'Лирические драмы.', False, 0),
    ('Принцесса Турандот', 'Гоцци К.', '1762', 'Зарубежная драматургия', 'Трагикомическая сказка.', True, 72),
    ('Маскарад', 'Лермонтов М. Ю.', '1835', 'Русская драматургия', 'Драма в стихах.', False, 0),
    ('Бесприданница', 'Островский А. Н.', '1878', 'Русская драматургия', 'Драма в четырёх действиях.', False, 0),
    ('Сирано де Бержерак', 'Ростан Э.', '1897', 'Зарубежная драматургия', 'Героическая комедия.', True, 0),
    ('Пер Гюнт', 'Ибсен Г.', '1867', 'Зарубежная драматургия', 'Драматическая поэма.', False, 0),
    ('Кукольный дом', 'Ибсен Г.', '1879', 'Зарубежная драматургия', 'Драма в трёх действиях.', False, 0),
    ('Театр абсурда', 'Эсслин М.', '1961', 'Театроведение', 'Исследование жанра.', False, 0),
    ('Сценография XX века', 'Берман Е. Г.', '1985', 'Сценография', 'Очерки и альбом.', True, 0),
    ('Антреприза и репертуар', 'Кугель А. Р.', '1908', 'История театра', 'Очерки театрального дела.', False, 0),
]


def _book_record(title, author, year, subject, annotation, cover, pages):
    rec = {'920': 'PAZK', '101': 'rus',
           '200': [{'a': title, 'f': author}],
           '700': [{'a': author}],
           '606': [{'a': subject}],
           '330': [{'a': annotation}],
           '210': [{'d': year}]}
    if cover:
        rec['953'] = [{'a': 'IMAGE', 't': title}]
    if pages:
        rec['955'] = [{'a': title + '.pdf', 'n': str(pages)}]
    return rec


# Демо-выставки (инфорост-формат) — для витрины/Оцифровки.
EXHIBITS_EXPORT = {'collections': [
    {'id': 'serebro-veka', 'title': 'Театр Серебряного века',
     'description': 'Афиши, эскизы и программы постановок 1900–1917 гг.',
     'items': [
         {'id': 'sv-1', 'title': 'Афиша «Балаганчик»', 'author': 'Блок А. А.', 'year': '1906',
          'pages': [{'no': 1, 'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Theatre_poster_placeholder.png/480px-Theatre_poster_placeholder.png'}]},
         {'id': 'sv-2', 'title': 'Эскиз декорации к «Маскараду»', 'author': 'Головин А. Я.', 'year': '1917',
          'pages': [{'no': 1, 'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Theatre_poster_placeholder.png/480px-Theatre_poster_placeholder.png'}]},
     ]},
    {'id': 'stanislavsky', 'title': 'Наследие Станиславского',
     'description': 'Рукописи, фотографии и издания основателя МХТ.',
     'items': [
         {'id': 'st-1', 'title': 'Рукопись «Работа актёра над собой»', 'author': 'Станиславский К. С.', 'year': '1935',
          'pages': [{'no': 1, 'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Theatre_poster_placeholder.png/480px-Theatre_poster_placeholder.png'}]},
     ]},
]}

# OCR-документы (распознанный текст) — для полнотекста по оцифровке.
OCR_DOCS = [
    ('dam://demo/chaika-ms', [
        {'page_no': 1, 'text': 'Чайка. Комедия в четырёх действиях. Действие первое. Часть парка в усадьбе Сорина.'},
        {'page_no': 2, 'text': 'Треплев и Сорин. Нина Заречная читает монолог о мировой душе.'},
    ]),
    ('dam://demo/hamlet-folio', [
        {'page_no': 1, 'text': 'Гамлет, принц Датский. Трагедия. Быть или не быть — вот в чём вопрос.'},
    ]),
]


def main():
    api = Api()
    if api.catalog is None:
        print('CatalogStore недоступен — сид невозможен'); return 1

    # 1) Каталог (идемпотентно: пропускаем, если запись с таким заглавием уже есть).
    try:
        existing = {((r.get('200') or [{}])[0].get('a') or '')
                    for r in (api.catalog.get(DB, m) or {} for m in api.catalog.list_mfns(DB, limit=5000))}
    except Exception:
        existing = set()
    created_mfns, created = [], 0
    for (title, author, year, subject, ann, cover, pages) in BOOKS:
        if title in existing:
            continue
        res = api.catalog.save(DB, _book_record(title, author, year, subject, ann, cover, pages))
        if res and res.get('saved') and res.get('mfn'):
            created_mfns.append(res['mfn']); created += 1
    print('Каталог: создано %d записей (всего в базе теперь %d)'
          % (created, api.catalog.count(DB)))

    # 2) FTS-индекс по всему каталогу (морфо-поиск, #368) + 955-ПТ артефакты.
    fts = 0
    if api.search_index is not None:
        for mfn in api.catalog.list_mfns(DB, limit=5000):
            rec = api.catalog.get(DB, mfn)
            if rec is None:
                continue
            title, text = api._record_search_text(rec)
            try:
                api.search_index.index('cat:%s:%d' % (DB, mfn), text, db=DB, mfn=mfn, title=title)
                fts += 1
            except Exception:
                pass
            # 955-ПТ артефакт (для блока «Полный текст» + PDF-вьюера)
            if api.fulltext is not None and rec.get('955'):
                try:
                    n = (rec['955'][0] or {}).get('n')
                    api.fulltext.attach(DB, mfn, '955', file=(rec['955'][0] or {}).get('a') or '',
                                        pages=int(n) if n else None)
                except Exception:
                    pass
    print('FTS: проиндексировано %d записей каталога' % fts)

    # 3) Выставки (витрина/Оцифровка) — через инфорост-импорт с публикацией.
    SUP = _staff(api, [{'function': 'admin.db', 'db': '*', 'level': 'admin'}])
    try:
        st, p = api.route('POST', '/api/admin/inforost/import-exhibits', {},
                          {'export': EXHIBITS_EXPORT, 'publish': True}, SUP)
        print('Выставки: created=%s skipped=%s (publish)'
              % (p.get('data', {}).get('created'), p.get('data', {}).get('skipped')))
    except Exception as e:
        print('Выставки: пропущено (%s)' % e)

    # 4) OCR-документы + мост в FTS (через recognize+process).
    STAFF = _staff(api, [{'function': 'cataloging', 'db': '*', 'level': 'write'}])
    ocr_done = 0
    for asset_ref, pages in OCR_DOCS:
        try:
            api.route('POST', '/api/ocr/recognize', {}, {'assetRef': asset_ref, 'pages': pages}, STAFF)
            st, p = api.route('POST', '/api/ocr/process', {}, {}, SUP)
            if p.get('data', {}).get('job'):
                ocr_done += 1
        except Exception:
            pass
    print('OCR: обработано %d документов' % ocr_done)

    # 5) Тарифы платформы (матрица доступов/usage) — дефолты.
    if api.tariffs is not None:
        try:
            from access import access_matrix as _am
            _am.seed_defaults(api.tariffs)
            print('Тарифы: дефолты засеяны')
        except Exception as e:
            print('Тарифы: пропущено (%s)' % e)

    # 6) Конфиг библиотеки (реквизиты на сайте) — через tenant-admin.
    TA = _staff(api, [{'function': 'admin.users', 'db': '*', 'level': 'admin'}])
    try:
        api.route('POST', '/api/admin/library-config', {},
                  {'name': 'Театральная библиотека (демо)',
                   'requisites': {'inn': '7800000000', 'email': 'demo@sptl.spb.ru',
                                  'address': 'Санкт-Петербург, пл. Островского, 6'}}, TA)
        print('Конфиг библиотеки: записан')
    except Exception as e:
        print('Конфиг: пропущено (%s)' % e)

    print('\nГотово. Поднимай: OWN_SEARCH_DBS=IBIS py -3.12 server.py  (+ vite npm run dev)')
    return 0


def _staff(api, grants):
    tok, _ = api._new_session('staff', 'demo', grants, tenant='public')
    return {'authorization': 'Bearer ' + tok}


if __name__ == '__main__':
    sys.exit(main())
