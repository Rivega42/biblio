#!/usr/bin/env python3
"""SEARCH_INDEX — морфологический полнотекстовый индекс + BM25 (issue #368) — тест.

Покрывает ``access/search_index.py``:

  * ``russian_stem`` — русский стеммер Snowball: словоформы → одна основа
    (книга/книги/книгу; красивый/красивая/красивые; бежать/бежал;
    программирование/программировании); латиница 'Python' → 'python';
  * ``tokenize`` / ``normalize_query`` — выкидывают стоп-слова и стеммят;
  * ``SearchIndexStore`` — дуальный стор (sqlite): upsert/delete/get/postings/
    doc_freq/totals/doc_view/count;
  * ``SearchIndex.index`` + ``search`` — поиск по СЛОВОФОРМЕ (доказывает морфологию);
  * BM25 — ранжирование (частота / редкость термина / multi-term AND-ish);
  * ``remove`` — убирает из выдачи;
  * ``more_like`` — близкий по терминам документ;
  * пустой запрос → []; backend по умолчанию sqlite ':memory:'.

Standalone:  py -3.12 tests/test_search_index.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.search_index import (russian_stem, tokenize, normalize_query,
                                  STOPWORDS, SearchIndexStore, SearchIndex)

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
# 1. russian_stem — словоформы сводятся к ОДНОЙ основе (морфология).
# --------------------------------------------------------------------------- #
def stem_checks():
    print('-- search_index: russian_stem (Snowball Russian)')
    # книга/книги/книгу/книгой/книге → одна основа.
    books = [russian_stem(w) for w in ('книга', 'книги', 'книгу', 'книгой', 'книге')]
    check('книга/книги/книгу/… → одна основа', len(set(books)) == 1)
    check('основа «книг…» начинается с «книг»', books[0].startswith('книг'))

    # красивый/красивая/красивые/красивое → одна основа.
    pretty = [russian_stem(w) for w in ('красивый', 'красивая', 'красивые', 'красивое')]
    check('красивый/красивая/красивые/… → одна основа', len(set(pretty)) == 1)

    # бежать/бежал/бежала/бежали → одна основа.
    run = [russian_stem(w) for w in ('бежать', 'бежал', 'бежала', 'бежали')]
    check('бежать/бежал/бежала/бежали → одна основа', len(set(run)) == 1)

    # программирование/программировании/программированию → одна основа.
    prog = [russian_stem(w) for w in ('программирование', 'программировании',
                                      'программированию')]
    check('программирование/…ии/…ию → одна основа', len(set(prog)) == 1)

    # читатель/читатели/читателя → одна основа.
    rdr = [russian_stem(w) for w in ('читатель', 'читатели', 'читателя', 'читателю')]
    check('читатель/читатели/читателя → одна основа', len(set(rdr)) == 1)

    # библиотека/библиотеки/библиотеку → одна основа.
    lib = [russian_stem(w) for w in ('библиотека', 'библиотеки', 'библиотеку')]
    check('библиотека/библиотеки/библиотеку → одна основа', len(set(lib)) == 1)

    # Латиница НЕ стеммится — только нижний регистр.
    check("'Python' → 'python' (латиница не стеммится)", russian_stem('Python') == 'python')
    check("'2024' → '2024' (цифры как есть)", russian_stem('2024') == '2024')

    # Пустое → ''.
    check("пустая строка → ''", russian_stem('') == '')
    check('None → \'\'', russian_stem(None) == '')

    # Разные основы не должны схлопываться (стеммер не overstem).
    check('книга vs библиотека — РАЗНЫЕ основы',
          russian_stem('книга') != russian_stem('библиотека'))


# --------------------------------------------------------------------------- #
# 2. tokenize / normalize_query — стоп-слова + стемминг.
# --------------------------------------------------------------------------- #
def tokenize_checks():
    print('-- search_index: tokenize / normalize_query')
    toks = tokenize('Красивые книги в большой библиотеке')
    check('tokenize стеммит словоформы', 'книг' in toks and 'библиотек' in toks)
    check('tokenize выкинул стоп-слово «в»', 'в' not in toks)

    # «и», «на», «с» — стоп-слова, исчезают.
    toks2 = tokenize('кот и пёс на диване с миской')
    check('tokenize выкинул стоп-слова и/на/с',
          'и' not in toks2 and 'на' not in toks2 and 'с' not in toks2)
    check('STOPWORDS содержит служебные слова',
          'и' in STOPWORDS and 'в' in STOPWORDS and 'на' in STOPWORDS)

    # tokenize сохраняет повторы (частота важна для tf).
    rep = tokenize('книга книга книга')
    check('tokenize сохраняет повторы (tf)', rep == ['книг', 'книг', 'книг'])

    # normalize_query — та же обработка.
    check('normalize_query == tokenize (та же морфология)',
          normalize_query('Красивые книги') == tokenize('Красивые книги'))

    # Пустой/мусорный вход → [].
    check('tokenize(\'\') → []', tokenize('') == [])
    check('tokenize(None) → []', tokenize(None) == [])
    check('tokenize из одних стоп-слов → []', tokenize('и в на с') == [])


# --------------------------------------------------------------------------- #
# 3. SearchIndexStore — дуальный стор (sqlite): upsert/get/postings/df/totals.
# --------------------------------------------------------------------------- #
def store_checks():
    print('-- search_index: SearchIndexStore (sqlite)')
    st = SearchIndexStore(':memory:')
    check('backend по умолчанию sqlite', st.backend == 'sqlite')
    check('empty store count == 0', st.count() == 0)

    d = st.upsert_doc('IBIS:1', 'IBIS', 1, 'Книга', ['книг', 'книг', 'библиотек'])
    check('upsert echoes ref', d['ref'] == 'IBIS:1')
    check('upsert length = число токенов (3)', d['length'] == 3)
    check('store count == 1', st.count() == 1)

    got = st.get_doc('IBIS:1')
    check('get_doc возвращает документ', got is not None and got['title'] == 'Книга')
    check('get_doc несуществующего → None', st.get_doc('NOPE') is None)

    # постинги: term→tf агрегированы (книг встречается 2 раза).
    post = st.postings_for_terms(['книг', 'библиотек'])
    by_term = {p['term']: p['tf'] for p in post}
    check('postings_for_terms: tf «книг» = 2', by_term.get('книг') == 2)
    check('postings_for_terms: tf «библиотек» = 1', by_term.get('библиотек') == 1)
    check('postings_for_terms([]) → []', st.postings_for_terms([]) == [])

    # второй документ для df/totals.
    st.upsert_doc('IBIS:2', 'IBIS', 2, 'Журнал', ['журнал', 'библиотек'])
    df = st.doc_freq(['книг', 'библиотек', 'журнал'])
    check('doc_freq: «библиотек» в 2 док.', df['библиотек'] == 2)
    check('doc_freq: «книг» в 1 док.', df['книг'] == 1)
    check('doc_freq: отсутствующий термин → 0', st.doc_freq(['ничего'])['ничего'] == 0)

    tot = st.totals()
    check('totals N == 2', tot['N'] == 2)
    check('totals avgdl == (3+2)/2 == 2.5', abs(tot['avgdl'] - 2.5) < 1e-9)

    # upsert по тому же ref ПЕРЕСОЗДАёт (не плодит дубли).
    st.upsert_doc('IBIS:1', 'IBIS', 1, 'Книга v2', ['книг'])
    check('upsert того же ref не плодит документ', st.count() == 2)
    check('upsert того же ref пересоздал постинги (tf «книг» = 1)',
          {p['term']: p['tf'] for p in st.postings_for_terms(['книг'])}.get('книг') == 1)

    # doc_view по внутреннему id (берём свежий id — upsert выше пересоздал документ).
    fresh = st.get_doc('IBIS:1')
    dv = st.doc_view(fresh['id'])
    check('doc_view по id возвращает ref', dv is not None and dv['ref'] == 'IBIS:1')

    # delete.
    check('delete существующего → True', st.delete('IBIS:1') is True)
    check('delete несуществующего → False', st.delete('IBIS:1') is False)
    check('после delete count == 1', st.count() == 1)


# --------------------------------------------------------------------------- #
# 4. index + search — поиск по СЛОВОФОРМЕ (доказательство морфологии).
# --------------------------------------------------------------------------- #
def search_morphology_checks():
    print('-- search_index: index + search (морфология: словоформа → находим)')
    idx = SearchIndex()  # дефолт: sqlite :memory:
    r = idx.index('IBIS:1', 'Интересные книги о библиотеках', db='IBIS', mfn=1,
                  title='Каталог')
    check('index возвращает ref', r['ref'] == 'IBIS:1')
    check('index возвращает terms (число уникальных)', r['terms'] >= 1)
    check('index возвращает length', r['length'] >= 1)

    # Индексировали «книги» — ищем «книга» → найдено (доказывает морфологию).
    hits = idx.search('книга')
    check('поиск «книга» находит док с «книги» (морфология)',
          len(hits) == 1 and hits[0]['ref'] == 'IBIS:1')
    check('хит несёт matched (реально найденные основы)',
          hits[0]['matched'] == ['книг'])
    check('хит несёт score', isinstance(hits[0]['score'], float))
    check('хит несёт title/db/mfn', hits[0]['title'] == 'Каталог' and hits[0]['db'] == 'IBIS')

    # Ищем «библиотека» (ед.ч.) — находим док с «библиотеках» (мн.ч., предл.).
    hits2 = idx.search('библиотека')
    check('поиск «библиотека» находит «библиотеках» (морфология)',
          len(hits2) == 1 and hits2[0]['ref'] == 'IBIS:1')

    # Слово, которого нет → пусто.
    check('поиск отсутствующего слова → []', idx.search('самолёт') == [])
    # Пустой запрос → [].
    check('пустой запрос → []', idx.search('') == [])
    check('запрос из стоп-слов → []', idx.search('и в на') == [])


# --------------------------------------------------------------------------- #
# 5. BM25 — ранжирование (частота / редкость / multi-term).
# --------------------------------------------------------------------------- #
def bm25_ranking_checks():
    print('-- search_index: BM25 ranking')
    idx = SearchIndex()
    # doc A: «книга» встречается часто; doc B — один раз. При равной длине A выше.
    idx.index('A', 'книга книга книга книга про библиотеку')
    idx.index('B', 'книга про музей и архив искусство')
    hits = idx.search('книга')
    check('BM25: оба документа найдены', len(hits) == 2)
    check('BM25: чаще встречающийся термин — выше', hits[0]['ref'] == 'A')
    check('BM25: score(A) > score(B)', hits[0]['score'] > hits[1]['score'])

    # Редкость термина: idf. Термин в 1 док важнее термина в каждом.
    idx2 = SearchIndex()
    # «библиотека» — в каждом (частый, малый idf); «палеография» — только в D (редкий).
    idx2.index('C', 'библиотека каталог фонд хранение')
    idx2.index('D', 'библиотека палеография рукопись')
    idx2.index('E', 'библиотека читатель абонемент')
    # Запрос с обоими: D несёт редкую «палеографию» → должен быть первым.
    hits2 = idx2.search('библиотека палеография')
    check('BM25: редкий термин поднимает документ выше',
          hits2[0]['ref'] == 'D')
    check('BM25: документ с двумя совпадениями matched=2',
          hits2[0]['matched'] == ['библиотек', 'палеограф'])

    # multi-term AND-ish: документ с ОБОИМИ терминами выше, чем с одним.
    idx3 = SearchIndex()
    idx3.index('F', 'научная статья про квантовую физику и физику плазмы')
    idx3.index('G', 'научная статья про историю')
    hits3 = idx3.search('научная физика')
    check('multi-term: оба документа найдены', len(hits3) == 2)
    check('multi-term: документ с двумя терминами выше', hits3[0]['ref'] == 'F')
    check('multi-term: F несёт обе совпавшие основы', len(hits3[0]['matched']) == 2)
    check('multi-term: G несёт одну совпавшую основу', len(hits3[1]['matched']) == 1)

    # limit обрезает выдачу.
    idx4 = SearchIndex()
    for i in range(5):
        idx4.index('doc%d' % i, 'общий термин общий')
    check('search limit обрезает выдачу', len(idx4.search('общий', limit=3)) == 3)


# --------------------------------------------------------------------------- #
# 6. remove + more_like.
# --------------------------------------------------------------------------- #
def remove_more_like_checks():
    print('-- search_index: remove / more_like')
    idx = SearchIndex()
    idx.index('IBIS:1', 'книга про библиотеку')
    idx.index('IBIS:2', 'журнал про музей')
    check('перед remove «книга» находится', len(idx.search('книга')) == 1)
    check('remove существующего → True', idx.remove('IBIS:1') is True)
    check('после remove «книга» НЕ находится', idx.search('книга') == [])
    check('remove несуществующего → False', idx.remove('IBIS:1') is False)
    check('другой документ не задет', len(idx.search('журнал')) == 1)

    # more_like: близкий по терминам документ.
    idx2 = SearchIndex()
    idx2.index('X', 'квантовая физика теория поля элементарные частицы')
    idx2.index('Y', 'квантовая физика частицы стандартная модель')  # близок к X
    idx2.index('Z', 'кулинария рецепты выпечка хлеб')                # далёк
    like = idx2.more_like('X')
    check('more_like находит близкий док (Y)', any(h['ref'] == 'Y' for h in like))
    check('more_like исключает сам документ (X)', all(h['ref'] != 'X' for h in like))
    check('more_like не тянет далёкий док (Z) выше близкого (Y)',
          (not like) or like[0]['ref'] == 'Y')
    check('more_like несуществующего → []', idx2.more_like('NOPE') == [])


def main():
    stem_checks()
    tokenize_checks()
    store_checks()
    search_morphology_checks()
    bm25_ranking_checks()
    remove_more_like_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
