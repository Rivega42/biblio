#!/usr/bin/env python3
"""Own-index search slice (#229): CatalogStore.search_records + OWN_SEARCH_DBS.

Собственный индекс позволит /api/search обслуживать базу из НАШЕГО FTS в обход
сломанного индекса K= ИРБИС. Здесь покрыт механизм поиска на уровне store
(одиночный ``PREFIX=term`` + усечение ``$``); сам маршрут /api/search + адаптер
карточки (tag-keyed запись → поля карточки) приземляются в фокус-блоке #262.

Standalone: py -3.12 tests/test_own_search.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import seed_vocab
from access.catalog import CatalogStore, _field_values
from access.store import AccessStore

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _store():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return CatalogStore(':memory:', access_store=st)


def _book(title, author, kw, inv):
    return {
        '920': 'PAZK',
        '200': [{'a': title}],
        '700': [{'a': author}],
        '610': [{'': k} for k in kw],
        '101': 'rus',
        '910': [{'a': '0', 'b': inv}],
        '907': [{'a': 'Тест Т.Т.'}],
    }


def _title(rec):
    vals = _field_values(rec, '200', 'a')
    return vals[0] if vals else ''


def _route_check():
    """Активация маршрута /api/search за флагом OWN_SEARCH_DBS через Api: одиночный
    префиксный запрос по EK обслуживается из нашего индекса (source='own')."""
    os.environ['ACCESS_DB'] = ':memory:'
    os.environ.setdefault('APP_SECRET', 'own-search-test')
    import core as _core
    from access.authz import GUEST_GRANTS
    api = _core.Api()
    seed_vocab.seed_vocabularies(api.access, from_catalog=False)
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    api.cfg.public_dbs = frozenset(set(api.cfg.public_dbs) | {'EK'})
    api.cfg.own_search_dbs = frozenset({'EK'})
    api.catalog.save('EK', _book('Чайка', 'Чехов А.П.', ['пьеса', 'театр'], '5001'))
    _tok, sess = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    code, body = api.search(sess, 'EK', 'K=театр', 1, 20)
    data = body.get('data', {}) if isinstance(body, dict) else {}
    check('route: 200', code == 200)
    check('route: source=own (обошли ИРБИС)', data.get('source') == 'own')
    check('route: нашёл запись по K=', any(i.get('title') == 'Чайка' for i in data.get('items', [])))
    code2, body2 = api.search(sess, 'EK', '("T=Чайка$" + "K=пьеса")', 1, 20)
    data2 = body2.get('data', {}) if isinstance(body2, dict) else {}
    check('route: составное → source=own', data2.get('source') == 'own')
    check('route: составное нашло запись', any(i.get('title') == 'Чайка' for i in data2.get('items', [])))


def main():
    cat = _store()
    cat.save('EK', _book('Основы каталогизации', 'Петров П.П.', ['каталогизация', 'библиография'], '1001'))
    cat.save('EK', _book('Театральная история', 'Чехов А.П.', ['театр', 'история'], '1002'))

    # 1. Точное ключевое слово (K=) — именно тот случай, что не отдаёт сломанный ИРБИС-K=.
    r = cat.search_records('EK', 'K=каталогизация')
    check('K= exact: total=1', r['total'] == 1)
    check('K= exact: верная запись',
          len(r['items']) == 1 and _title(r['items'][0]['record']) == 'Основы каталогизации')
    check('K= exact: есть mfn', bool(r['items']) and isinstance(r['items'][0]['mfn'], int))

    # 2. Точный автор (A=).
    r = cat.search_records('EK', 'A=Чехов А.П.')
    check('A= exact находит book2',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная история')

    # 3. Усечение (T=...$) — префиксное совпадение.
    r = cat.search_records('EK', 'T=Основы$')
    check('T= усечение по префиксу',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Основы каталогизации')

    # 4. Усечение нечувствительно к регистру (нормализация casefold).
    r = cat.search_records('EK', 'T=основы$')
    check('T= усечение без учёта регистра', r['total'] == 1)

    # 5. Нет совпадений.
    r = cat.search_records('EK', 'K=отсутствуеттакого')
    check('нет совпадений: total=0, пусто', r['total'] == 0 and r['items'] == [])

    # 6. Изоляция по базе — тот же термин в другой БД.
    r = cat.search_records('PERIO', 'K=каталогизация')
    check('db-scoped: другая БД пуста', r['total'] == 0)

    # 6b. search_items — структурная карточка (та же форма, что /api/search).
    si = cat.search_items('EK', 'A=Петров П.П.')
    check('search_items: верная карточка',
          bool(si['items']) and si['items'][0]['title'] == 'Основы каталогизации')
    check('search_items: availability из 910^a',
          bool(si['items']) and si['items'][0]['availability'] == 'available')
    check('search_items: contract-поля',
          bool(si['items']) and set(si['items'][0]) >= {'mfn', 'title', 'author', 'year',
                                                        'docType', 'availability', 'hasCover'})

    # 6c. Составные выражения (#262) — для дефолтного мультиполевого поиска портала.
    r = cat.search_records('EK', '("A=Петров$" + "A=Чехов$")')
    check('compound OR: оба', r['total'] == 2)
    r = cat.search_records('EK', '("T=Основы$" * "A=Петров$")')
    check('compound AND: пересечение',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Основы каталогизации')
    r = cat.search_records('EK', '("T=Основы$" * "A=Чехов$")')
    check('compound AND: пусто', r['total'] == 0)
    r = cat.search_records('EK', '"A=Чехов$" ^ "K=каталогизация"')
    check('compound NOT: разность',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная история')
    r = cat.search_records('EK', '("A=Петров$" + "A=Чехов$") * "K=театр"')
    check('compound скобки+приоритет',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная история')
    r = cat.search_records('EK', '("T=Театр$" + "A=Театр$" + "K=Театр$")')
    check('multi-field union (как build_expr портала)',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театральная история')

    # 6d. Пословный K= (#270): многословное ключевое слово 610 разбивается на слова —
    # точное слово находит запись (раньше «театральное искусство; театр» целым
    # термином давало 0 на точное K=театр).
    cat.save('EK', _book('Театр и зритель', 'Островский А.Н.',
                         ['театральное искусство; театр'], '1003'))
    r = cat.search_records('EK', 'K=театр')
    check('K= пословно: точное слово из многословного 610',
          any(_title(it['record']) == 'Театр и зритель' for it in r['items']))
    r = cat.search_records('EK', 'K=искусство')
    check('K= пословно: слово «искусство» из «театральное искусство»',
          r['total'] == 1 and _title(r['items'][0]['record']) == 'Театр и зритель')

    # 7. Конфиг-флаг OWN_SEARCH_DBS парсится (csv, upper).
    os.environ['OWN_SEARCH_DBS'] = 'ek, perio'
    from config import Config
    cfg = Config()
    check('OWN_SEARCH_DBS -> upper frozenset', cfg.own_search_dbs == frozenset({'EK', 'PERIO'}))
    os.environ.pop('OWN_SEARCH_DBS', None)

    # 8. Маршрут /api/search за флагом (через Api) — активация + source='own'.
    _route_check()

    print('%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
