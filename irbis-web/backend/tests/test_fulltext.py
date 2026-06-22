#!/usr/bin/env python3
"""FULLTEXT — реестр артефактов ПТ 951/953/955 (кластер 7, ребро 7.1) — тест.

Покрывает ``access/fulltext.py`` (хранение/резолв артефактов полных текстов /
образов на запись каталога — дополняет ПТ↔права-гейтинг rights.py/lich.py):

  * ``blob_ref`` — blob-референс для 953 (путь+хэш+размер), сырые байты НЕ хранятся;
  * ``FulltextStore`` — дуальный стор: attach/for_record/delete_record/count (sqlite);
  * ``FulltextRegistry.attach`` — завести 951 (ссылка) / 953 (blob-реф) / 955
    (метаданные: файл, страницы, шаблон прав 955^B);
  * ``artifacts_for`` — единый список (стор + каталог), нормализованная форма
    (kind/source/ref/pages/rights_template/data); несколько артефактов на запись;
  * ``page_count`` — число страниц 955^N (максимум среди 955-артефактов);
  * ``rights_template_for`` — 955^B наружу для связки с rights (гейтинг тут НЕ делается);
  * резолв 951/953/955 каталожной записи через опц. catalog-handle (get(db,mfn));
  * back-compat без handle И без стора → пустой список;
  * PG-ПАРИТЕТ — когда postgres доступен (иначе чисто пропускается).

Вписан в раннер tests/test_access.py (его module-list) через ``module_checks`` —
раннер вызывает каждую ``*_checks()`` и складывает PASS/FAIL.

Standalone:  py tests/test_fulltext.py
PG:          (set ACCESS_BACKEND=postgres) py -3.12 tests/test_fulltext.py
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.fulltext import (FulltextStore, FulltextRegistry, blob_ref,
                             KIND_LINK, KIND_BLOB, KIND_META, KINDS)

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
# 1. blob_ref — blob-референс 953 (путь+хэш), сырые байты НЕ хранятся.
# --------------------------------------------------------------------------- #
def blob_ref_checks():
    print('-- fulltext: blob_ref (953 blob-reference, no raw bytes)')
    data = b'PDF-bytes-here'
    ref = blob_ref(data=data, path='s3://bucket/scan.pdf', content_type='application/pdf')
    check('blob_ref несёт путь', ref['path'] == 's3://bucket/scan.pdf')
    check('blob_ref считает sha256 из data',
          ref['sha256'] == hashlib.sha256(data).hexdigest())
    check('blob_ref считает size из data', ref['size'] == len(data))
    check('blob_ref несёт content-type', ref['contentType'] == 'application/pdf')
    # Сырые байты НЕ попадают в референс (раздувание БД недопустимо).
    check('blob_ref не хранит сырые байты',
          'data' not in ref and data not in tuple(ref.values()))
    # Готовый sha256 имеет приоритет над data.
    ref2 = blob_ref(sha256='deadbeef', path='p')
    check('blob_ref берёт готовый sha256', ref2['sha256'] == 'deadbeef')
    # Пустой вход → пустой dict.
    check('blob_ref пустой → {}', blob_ref() == {})


# --------------------------------------------------------------------------- #
# 2. FulltextStore — дуальный стор (sqlite): attach/for_record/delete/count.
# --------------------------------------------------------------------------- #
def store_checks():
    print('-- fulltext: FulltextStore (sqlite)')
    st = FulltextStore(':memory:')
    check('empty store count == 0', st.count() == 0)

    a = st.attach('IBIS', 10, KIND_META, {'file': 'book.pdf', 'pages': 42,
                                          'rights_template': 'R1'})
    check('attach echoes kind', a['kind'] == KIND_META)
    check('attach echoes mfn (int)', a['mfn'] == 10 and isinstance(a['mfn'], int))
    check('attach round-trips data', a['data']['rights_template'] == 'R1')
    check('store count == 1', st.count() == 1)

    # Поле 955/951/953 повторяющееся — attach НЕ перезаписывает, добавляет строку.
    st.attach('IBIS', 10, KIND_LINK, {'url': 'https://x/y.pdf'})
    check('повторный attach добавляет строку (повтор. поле)', st.count() == 2)
    recs = st.for_record('IBIS', 10)
    check('for_record видит оба артефакта', len(recs) == 2)
    check('for_record в порядке добавления',
          recs[0]['kind'] == KIND_META and recs[1]['kind'] == KIND_LINK)

    # Изоляция по записи: другой mfn независим.
    st.attach('IBIS', 11, KIND_LINK, {'url': 'https://z'})
    check('другой mfn изолирован', len(st.for_record('IBIS', 11)) == 1
          and len(st.for_record('IBIS', 10)) == 2)
    # Изоляция по БД.
    st.attach('VKR', 10, KIND_META, {'file': 'thesis.pdf'})
    check('другая БД изолирована', len(st.for_record('VKR', 10)) == 1)

    # delete_record сносит все артефакты записи.
    n = st.delete_record('IBIS', 10)
    check('delete_record вернул число удалённых (2)', n == 2)
    check('после delete for_record пуст', st.for_record('IBIS', 10) == [])
    check('delete не задел другие записи', len(st.for_record('IBIS', 11)) == 1)

    # Невалидный kind → ValueError.
    bad = False
    try:
        st.attach('IBIS', 1, '999', {})
    except ValueError:
        bad = True
    check('attach kind=999 → ValueError', bad)


# --------------------------------------------------------------------------- #
# 3. FulltextRegistry.attach — конструктор по виду (951/953/955).
# --------------------------------------------------------------------------- #
def registry_attach_checks():
    print('-- fulltext: FulltextRegistry.attach (951 link / 953 blob / 955 meta)')
    reg = FulltextRegistry(store=FulltextStore(':memory:'))

    # 951 — внешняя ссылка: ref = URL (приоритет) либо имя файла.
    link = reg.attach('IBIS', 10, KIND_LINK, file='y.pdf', url='https://x/y.pdf',
                      text='Читать онлайн')
    check('951: kind/source', link['kind'] == KIND_LINK and link['source'] == 'store')
    check('951: ref = URL', link['ref'] == 'https://x/y.pdf')
    check('951: data несёт текст ссылки', link['data']['text'] == 'Читать онлайн')
    check('951: pages/rights пусты', link['pages'] is None and link['rights_template'] is None)
    # 951 только с именем файла → ref = имя файла.
    link2 = reg.attach('IBIS', 10, KIND_LINK, file='only.pdf')
    check('951 без URL: ref = имя файла', link2['ref'] == 'only.pdf')

    # 953 — встроенный двоичный: blob-референс из data-bytes (байты не в сторе).
    blob = reg.attach('IBIS', 10, KIND_BLOB, res_type='JPG', name='скан',
                      view_mode='0', data=b'\x89PNG-bytes', path='s3://b/scan.jpg')
    check('953: kind', blob['kind'] == KIND_BLOB)
    check('953: ref = путь blob-референса', blob['ref'] == 's3://b/scan.jpg')
    check('953: blob несёт sha256',
          blob['data']['blob']['sha256'] == hashlib.sha256(b'\x89PNG-bytes').hexdigest())
    check('953: embedded флаг', blob['embedded'] is True)
    # 953 не пишет сырые байты в data.
    check('953: сырые байты не в артефакте',
          b'\x89PNG-bytes' not in tuple(str(v).encode() for v in blob['data'].get('blob', {}).values()))
    # 953 с готовым blob-референсом (dict) — принимается как есть.
    blob2 = reg.attach('IBIS', 10, KIND_BLOB,
                       blob=blob_ref(path='s3://b/x', sha256='abc'))
    check('953: готовый blob-реф dict', blob2['data']['blob']['sha256'] == 'abc')

    # 955 — метаданные ПТ: файл, страницы (^N), шаблон прав (^B).
    meta = reg.attach('IBIS', 10, KIND_META, file='book.pdf', pages='42',
                      rights_template='R1')
    check('955: kind', meta['kind'] == KIND_META)
    check('955: ref = имя файла (^A)', meta['ref'] == 'book.pdf')
    check('955: pages (^N) приведён к int', meta['pages'] == 42)
    check('955: rights_template (^B)', meta['rights_template'] == 'R1')
    # pages-мусор → None.
    meta2 = reg.attach('IBIS', 10, KIND_META, file='x.pdf', pages='abc')
    check('955: нечисловой ^N → pages None', meta2['pages'] is None)

    # attach без стора → RuntimeError.
    boom = False
    try:
        FulltextRegistry(store=None).attach('IBIS', 1, KIND_LINK, url='u')
    except RuntimeError:
        boom = True
    check('attach без стора → RuntimeError', boom)


# --------------------------------------------------------------------------- #
# 4. artifacts_for / page_count / rights_template_for + несколько артефактов.
# --------------------------------------------------------------------------- #
def artifacts_for_checks():
    print('-- fulltext: artifacts_for / page_count / rights_template_for')
    reg = FulltextRegistry(store=FulltextStore(':memory:'))
    reg.attach('IBIS', 10, KIND_LINK, url='https://x/y.pdf')
    reg.attach('IBIS', 10, KIND_BLOB, res_type='JPG', path='s3://b/s.jpg')
    reg.attach('IBIS', 10, KIND_META, file='book.pdf', pages=42, rights_template='R1')

    arts = reg.artifacts_for('IBIS', 10)
    check('несколько артефактов на запись (3)', len(arts) == 3)
    kinds = {a['kind'] for a in arts}
    check('виды 951/953/955 присутствуют', kinds == {KIND_LINK, KIND_BLOB, KIND_META})
    check('все из стора', all(a['source'] == 'store' for a in arts))

    # page_count = 955^N.
    check('page_count = 42', reg.page_count('IBIS', 10) == 42)
    # rights_template_for = 955^B наружу (для связки с rights — гейтинг тут НЕ делается).
    check('rights_template_for = R1', reg.rights_template_for('IBIS', 10) == 'R1')

    # Несколько 955 на запись: page_count = максимум.
    reg.attach('IBIS', 10, KIND_META, file='vol2.pdf', pages=100)
    check('page_count = max(42,100) = 100', reg.page_count('IBIS', 10) == 100)

    # Запись без 955-метаданных → page_count None, rights_template_for None.
    reg.attach('IBIS', 12, KIND_LINK, url='https://only-link')
    check('нет 955 → page_count None', reg.page_count('IBIS', 12) is None)
    check('нет 955^B → rights_template_for None', reg.rights_template_for('IBIS', 12) is None)

    # Пустая запись → [].
    check('нет артефактов → []', reg.artifacts_for('IBIS', 999) == [])
    check('нет артефактов → page_count None', reg.page_count('IBIS', 999) is None)


# --------------------------------------------------------------------------- #
# 5. Резолв 951/953/955 каталожной записи через catalog-handle (ребро 7.1).
# --------------------------------------------------------------------------- #
class _FakeCatalog:
    """Минимальный catalog-handle: get(db, mfn) -> record (как CatalogStore.get)."""
    def __init__(self, records):
        self._records = records  # {(db, mfn): record-dict}

    def get(self, db, mfn):
        return self._records.get((db, mfn))


def catalog_resolve_checks():
    print('-- fulltext: resolve 951/953/955 from catalog record (handle)')
    cat = _FakeCatalog({
        # Запись со всеми тремя видами полей (подполя регистронезависимо: A/a, I, N, B).
        ('IBIS', 10): {
            '951': {'A': 'ext.pdf', 'I': 'https://ext/ext.pdf', 'T': 'Скачать'},
            '953': {'A': 'JPG', 'T': 'обложка', 'P': '0', 'B': 'BASE64DATA=='},
            '955': {'A': 'book.pdf', 'N': '120', 'B': 'R7'},
        },
        # Повторяющееся 955 (несколько ПТ на запись) + список инстансов.
        ('IBIS', 11): {
            '955': [{'a': 'v1.pdf', 'n': '30', 'b': 'R1'},
                    {'a': 'v2.pdf', 'n': '70'}],
        },
        # Целое поле строкой (без подполей) — игнорируется для 951/953/955.
        ('IBIS', 12): {'955': 'bare-string', '200': {'a': 'Заголовок'}},
        # Запись без полей ПТ вовсе.
        ('IBIS', 13): {'200': {'a': 'Только БО'}},
    })
    reg = FulltextRegistry(store=None, catalog=cat)

    arts = reg.artifacts_for('IBIS', 10)
    check('из каталога: 3 артефакта (951/953/955)', len(arts) == 3)
    by_kind = {a['kind']: a for a in arts}
    check('все из каталога (source=catalog)', all(a['source'] == 'catalog' for a in arts))
    # 951 → внешняя ссылка (URL приоритет).
    check('951 из записи: ref = URL', by_kind[KIND_LINK]['ref'] == 'https://ext/ext.pdf')
    check('951 из записи: data^T текст', by_kind[KIND_LINK]['data']['text'] == 'Скачать')
    # 953 → метаданные; сам base64-бинарь наружу НЕ отдаётся как ref (раздувание).
    check('953 из записи: тип ресурса', by_kind[KIND_BLOB]['data']['res_type'] == 'JPG')
    check('953 из записи: embedded=True', by_kind[KIND_BLOB]['embedded'] is True)
    check('953 из записи: ref не несёт сырой base64',
          by_kind[KIND_BLOB]['ref'] != 'BASE64DATA==')
    # 955 → метаданные ПТ: файл/страницы/шаблон прав.
    check('955 из записи: ref = имя файла (^A)', by_kind[KIND_META]['ref'] == 'book.pdf')
    check('955 из записи: pages (^N) = 120', by_kind[KIND_META]['pages'] == 120)
    check('955 из записи: rights_template (^B) = R7',
          by_kind[KIND_META]['rights_template'] == 'R7')
    # Аксессоры по записи.
    check('page_count из записи = 120', reg.page_count('IBIS', 10) == 120)
    check('rights_template_for из записи = R7', reg.rights_template_for('IBIS', 10) == 'R7')

    # Повторяющееся 955: оба инстанса; page_count = max(30,70).
    rep = reg.artifacts_for('IBIS', 11)
    check('повтор. 955: 2 артефакта', len([a for a in rep if a['kind'] == KIND_META]) == 2)
    check('повтор. 955: page_count = max(30,70) = 70', reg.page_count('IBIS', 11) == 70)
    check('повтор. 955: rights_template = R1 (первый непустой ^B)',
          reg.rights_template_for('IBIS', 11) == 'R1')

    # Целое поле строкой ^B/^N не несёт → артефакт без полезных подполей.
    bare = reg.artifacts_for('IBIS', 12)
    check('955 строкой: rights_template_for None', reg.rights_template_for('IBIS', 12) is None)
    check('955 строкой: page_count None', reg.page_count('IBIS', 12) is None)

    # Запись без полей ПТ → [].
    check('запись без ПТ-полей → []', reg.artifacts_for('IBIS', 13) == [])


# --------------------------------------------------------------------------- #
# 6. Стор + каталог вместе; back-compat без handle; seam не бросает.
# --------------------------------------------------------------------------- #
def store_plus_catalog_checks():
    print('-- fulltext: store+catalog merge / back-compat / seam resilience')
    cat = _FakeCatalog({('IBIS', 10): {'955': {'a': 'cat.pdf', 'n': '50', 'b': 'R9'}}})
    st = FulltextStore(':memory:')
    reg = FulltextRegistry(store=st, catalog=cat)

    # Завели свой артефакт в стор + есть 955 в каталоге → оба в выдаче.
    reg.attach('IBIS', 10, KIND_LINK, url='https://store-link')
    arts = reg.artifacts_for('IBIS', 10)
    check('стор+каталог: 2 артефакта', len(arts) == 2)
    check('порядок: стор раньше каталога',
          arts[0]['source'] == 'store' and arts[1]['source'] == 'catalog')
    # page_count из каталожного 955.
    check('стор+каталог: page_count из 955 каталога = 50', reg.page_count('IBIS', 10) == 50)
    check('стор+каталог: rights_template из 955 каталога = R9',
          reg.rights_template_for('IBIS', 10) == 'R9')

    # back-compat: без handle И без стора → []; без handle, со стором → только стор.
    reg_bare = FulltextRegistry()
    check('back-compat: без handle и стора → []', reg_bare.artifacts_for('IBIS', 10) == [])
    reg_store_only = FulltextRegistry(store=FulltextStore(':memory:'))
    reg_store_only.attach('IBIS', 10, KIND_META, file='s.pdf', pages=7, rights_template='RX')
    check('back-compat: без handle резолв только из стора',
          reg_store_only.page_count('IBIS', 10) == 7
          and reg_store_only.rights_template_for('IBIS', 10) == 'RX')

    # Seam не бросает: битый catalog-handle деградирует (артефакты каталога просто []).
    class _BoomCatalog:
        def get(self, db, mfn):
            raise RuntimeError('boom')
    reg_boom = FulltextRegistry(store=st, catalog=_BoomCatalog())
    arts_b = reg_boom.artifacts_for('IBIS', 10)
    check('битый handle не бросает; видны только сторовые артефакты',
          len(arts_b) == 1 and arts_b[0]['source'] == 'store')


# --------------------------------------------------------------------------- #
# 7. PG-ПАРИТЕТ — когда postgres доступен; иначе чисто пропускается.
# --------------------------------------------------------------------------- #
def _pg_reachable_dsn():
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return None
    try:
        from access import pgstore
        dsn = pgstore.default_pg_dsn()
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS fulltext_artifact')
        conn.close()
        return dsn
    except Exception as e:
        print('-- fulltext: postgres SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return None


def pg_parity_checks():
    dsn = _pg_reachable_dsn()
    if dsn is None:
        return
    print('-- fulltext: store (postgres parity)')
    st = FulltextStore(dsn, backend='postgres')
    reg = FulltextRegistry(store=st)
    check('[pg] empty count == 0', st.count() == 0)

    reg.attach('IBIS', 10, KIND_META, file='book.pdf', pages=42, rights_template='R1')
    reg.attach('IBIS', 10, KIND_LINK, url='https://x/y.pdf')
    blob = reg.attach('IBIS', 10, KIND_BLOB, res_type='JPG', data=b'bytes', path='s3://b/x')
    check('[pg] count == 3', st.count() == 3)
    check('[pg] blob-реф sha256 на PG',
          blob['data']['blob']['sha256'] == hashlib.sha256(b'bytes').hexdigest())

    arts = reg.artifacts_for('IBIS', 10)
    check('[pg] artifacts_for == 3', len(arts) == 3)
    check('[pg] page_count = 42', reg.page_count('IBIS', 10) == 42)
    check('[pg] rights_template_for = R1', reg.rights_template_for('IBIS', 10) == 'R1')
    check('[pg] mfn int round-trip', arts[0]['mfn'] == 10)

    check('[pg] delete_record == 3', st.delete_record('IBIS', 10) == 3)
    check('[pg] after delete count == 0', st.count() == 0)

    # cleanup
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS fulltext_artifact')
        conn.close()
    except Exception:
        pass


def main():
    blob_ref_checks()
    store_checks()
    registry_attach_checks()
    artifacts_for_checks()
    catalog_resolve_checks()
    store_plus_catalog_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
