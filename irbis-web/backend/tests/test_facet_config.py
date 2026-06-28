#!/usr/bin/env python3
"""Тесты FACET CONFIG — авто-фасеты из любого поля каталога (own-store, #240).

Покрыто (in-memory + фиксированные часы для детерминизма):
  * `configured` без кастома = DEFAULT_FACETS с ключами ('900^b', '101', ...);
  * `facet_key` — '^'-склейка / голый тег при пустом подполе;
  * `compute` по тестовым записям: язык rus×2/eng×1, вид документа, несколько
    авторов из ПОВТОРЯЮЩИХСЯ полей 700;
  * сортировка значений по убыванию count, затем по значению;
  * кастом-конфиг через upsert ПЕРЕОПРЕДЕЛЯЕТ дефолт (configured отдаёт кастом);
  * enabled=False исключается из активного набора;
  * upsert идемпотентен; get/remove работают;
  * устойчивость к записи без нужных полей (фасет с пустым списком).

Запуск: py -3.12 tests/test_facet_config.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import facet_config

PASS = [0]
FAIL = [0]

# Детерминированные «часы» для updated_at.
CLOCK = '2026-06-15T00:00:00+00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def svc():
    """Свежий сервис на чистом in-memory сторе с фиксированными часами."""
    return facet_config.FacetService(
        store=facet_config.FacetConfigStore(':memory:', now=lambda: CLOCK))


# Тестовый набор каталожных записей (tag-keyed; смесь list-инстансов и скаляра).
RECORDS = [
    {  # rus, книга, два автора (повторяющееся 700), 2021, история
        '900': [{'b': '05'}],
        '101': 'rus',
        '700': [{'a': 'Иванов И.'}, {'a': 'Петров П.'}],
        '210': [{'d': '2021'}],
        '606': [{'a': 'История'}],
    },
    {  # rus, иной вид, один автор, 2021, история
        '900': [{'b': '01'}],
        '101': 'rus',
        '700': [{'a': 'Иванов И.'}],
        '210': [{'d': '2021'}],
        '606': [{'a': 'История'}],
    },
    {  # eng, тот же вид что у первой, другой автор, 2019, право
        '900': [{'b': '05'}],
        '101': 'eng',
        '700': [{'a': 'Smith J.'}],
        '210': [{'d': '2019'}],
        '606': [{'a': 'Право'}],
    },
    {  # запись без нужных полей (defensive): только mfn
        'mfn': 99,
    },
]


def facet_key_checks():
    print('-- facet_key: склейка tag^subfield / голый тег')
    check("('900','b') -> '900^b'",
          facet_config.facet_key('900', 'b') == '900^b')
    check("('101','') -> '101'",
          facet_config.facet_key('101', '') == '101')
    check("('101',None) -> '101'",
          facet_config.facet_key('101', None) == '101')


def configured_default_checks():
    print('-- configured без кастома = DEFAULT_FACETS с ключами')
    s = svc()
    cfg = s.configured()
    check('кол-во = len(DEFAULT_FACETS)',
          len(cfg) == len(facet_config.DEFAULT_FACETS))
    keys = [c['key'] for c in cfg]
    check("ключ '900^b' присутствует", '900^b' in keys)
    check("ключ '101' (пустое подполе) присутствует", '101' in keys)
    check("ключ '700^a' присутствует", '700^a' in keys)
    first = cfg[0]
    check('facet-def несёт tag/subfield/label/key',
          set(first.keys()) == {'tag', 'subfield', 'label', 'key'})
    check('label по-русски (Вид документа)',
          cfg[0]['label'] == 'Вид документа')


def compute_counts_checks():
    print('-- compute: частоты значений по дефолтным фасетам')
    s = svc()
    res = s.compute(RECORDS)
    # язык: rus x2, eng x1
    lang = res['101']
    check('язык rus первым (count 2)',
          lang[0] == {'value': 'rus', 'count': 2})
    check('язык eng вторым (count 1)',
          lang[1] == {'value': 'eng', 'count': 1})
    check('язык — ровно 2 значения', len(lang) == 2)
    # вид документа 900^b: '05' x2, '01' x1
    kind = res['900^b']
    check("вид '05' первым (count 2)",
          kind[0] == {'value': '05', 'count': 2})
    check("вид '01' (count 1) присутствует",
          {'value': '01', 'count': 1} in kind)
    # авторы 700^a из повторяющихся полей: Иванов x2, Петров x1, Smith x1
    authors = {b['value']: b['count'] for b in res['700^a']}
    check('Иванов И. count 2 (повторяющиеся 700)',
          authors.get('Иванов И.') == 2)
    check('Петров П. count 1', authors.get('Петров П.') == 1)
    check('Smith J. count 1', authors.get('Smith J.') == 1)
    # год 210^d: 2021 x2, 2019 x1
    years = {b['value']: b['count'] for b in res['210^d']}
    check('год 2021 count 2', years.get('2021') == 2)
    check('год 2019 count 1', years.get('2019') == 1)


def sort_order_checks():
    print('-- сортировка: убывание count, затем значение')
    s = svc()
    res = s.compute(RECORDS)
    authors = res['700^a']
    counts = [b['count'] for b in authors]
    check('счётчики не возрастают (по убыванию)',
          all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)))
    check('лидер по count — Иванов И.', authors[0]['value'] == 'Иванов И.')
    # тематика: История x2, Право x1
    subj = res['606^a']
    check('тематика История первой (count 2)',
          subj[0] == {'value': 'История', 'count': 2})


def defensive_checks():
    print('-- устойчивость к записям без полей / пустым наборам')
    s = svc()
    # запись без нужных полей не ломает и не добавляет значений
    res = s.compute([{'mfn': 1}])
    check("у фасета '101' пустой список при отсутствии поля",
          res['101'] == [])
    check('все дефолтные ключи присутствуют в выводе',
          all(k in res for k in ('900^b', '101', '700^a', '210^d', '606^a')))
    # пустой список записей -> все фасеты пустые
    res2 = s.compute([])
    check('пустой ввод -> каждый фасет пустой',
          all(v == [] for v in res2.values()))
    # None среди записей не ломает (defensive)
    res3 = s.compute([None, {'101': 'rus'}])
    check('None в списке записей не ломает', res3['101'] == [
        {'value': 'rus', 'count': 1}])


def custom_override_checks():
    print('-- кастом-конфиг через upsert переопределяет дефолт')
    s = svc()
    s.upsert('public', '900', 'b', 'Тип', enabled=True, sort=1)
    s.upsert('public', '101', '', 'Язык документа', enabled=True, sort=0)
    cfg = s.configured('public')
    check('кастом замещает дефолт целиком (2 фасета)', len(cfg) == 2)
    # порядок по sort: сначала язык (sort=0), затем тип (sort=1)
    check('порядок по sort: язык первым', cfg[0]['key'] == '101')
    check('кастом-метка применилась', cfg[0]['label'] == 'Язык документа')
    check("ключ кастом-вида '900^b'", cfg[1]['key'] == '900^b')
    # compute использует активный (кастомный) набор
    res = s.compute(RECORDS)
    check('compute по кастому: только кастом-ключи',
          set(res.keys()) == {'101', '900^b'})


def custom_then_default_compute_checks():
    print('-- compute с явным defs игнорирует стор')
    s = svc()
    s.upsert('public', '101', '', 'Язык', enabled=True)
    defs = [{'tag': '606', 'subfield': 'a', 'label': 'Тематика'}]
    res = s.compute(RECORDS, defs=defs)
    check('явный defs задаёт ключи', set(res.keys()) == {'606^a'})
    check('явный defs считает верно',
          res['606^a'][0] == {'value': 'История', 'count': 2})


def enabled_flag_checks():
    print('-- enabled=False исключается из активного набора')
    s = svc()
    s.upsert('public', '900', 'b', 'Вид', enabled=True, sort=0)
    s.upsert('public', '101', '', 'Язык', enabled=False, sort=1)
    cfg = s.configured('public')
    keys = [c['key'] for c in cfg]
    check('включённый фасет в наборе', '900^b' in keys)
    check('выключенный фасет НЕ в наборе', '101' not in keys)
    # list без фильтра видит обе записи, с enabled_only — только одну
    check('list(enabled_only=False) видит обе',
          len(s.list('public', enabled_only=False)) == 2)
    check('list(enabled_only=True) видит одну',
          len(s.list('public', enabled_only=True)) == 1)


def upsert_idempotent_checks():
    print('-- upsert идемпотентен по (tenant,tag,subfield)')
    s = svc()
    r1 = s.upsert('public', '700', 'a', 'Автор', enabled=True, sort=0)
    r2 = s.upsert('public', '700', 'a', 'Авторы', enabled=True, sort=2)
    check('один и тот же id (не дубль)', r1['id'] == r2['id'])
    check('обновлён label', r2['label'] == 'Авторы')
    check('обновлён sort', r2['sort'] == 2)
    check('всего одна запись', len(s.list('public')) == 1)
    check('updated_at от часов', r2['updated_at'] == CLOCK)


def get_remove_checks():
    print('-- get/remove работают')
    s = svc()
    row = s.upsert('public', '606', 'a', 'Тематика')
    got = s.store.get(row['id'])
    check('get возвращает строку', got is not None and got['tag'] == '606')
    check('get несуществующего -> None', s.store.get(99999) is None)
    check('remove существующего -> True', s.remove(row['id']) is True)
    check('после remove get -> None', s.store.get(row['id']) is None)
    check('повторный remove -> False', s.remove(row['id']) is False)


def tenant_isolation_checks():
    print('-- изоляция по tenant')
    s = svc()
    s.upsert('t1', '900', 'b', 'Вид', enabled=True)
    # у t2 кастома нет -> дефолт
    cfg2 = s.configured('t2')
    check('другой tenant без кастома -> дефолт',
          len(cfg2) == len(facet_config.DEFAULT_FACETS))
    cfg1 = s.configured('t1')
    check('tenant с кастомом -> кастом (1 фасет)', len(cfg1) == 1)


def main():
    facet_key_checks()
    configured_default_checks()
    compute_counts_checks()
    sort_order_checks()
    defensive_checks()
    custom_override_checks()
    custom_then_default_compute_checks()
    enabled_flag_checks()
    upsert_idempotent_checks()
    get_remove_checks()
    tenant_isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
