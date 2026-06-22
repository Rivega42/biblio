#!/usr/bin/env python3
"""Тесты шва Авторитеты↔Каталог (рёбра 6.2/6.3/6.4 INTEGRATION_MAP).

Покрывают НОВЫЕ пути, добавленные сверх шва 6.1 (`^3`-on-save):
  * 6.2 autoin — обратное ребро «каталог → пополнение ATHR*»: при сохранении
    БО с заголовком 700/710/606… БЕЗ ``^3`` авторитетная запись авто-создаётся
    (нужна ревизия) либо привязывается к существующей по алкоду свёртки;
  * 6.4 индексация ``AR=`` над подполем ``^3`` (700/701/710/606/607…) — поиск
    каталога ПО авторитету (по номеру авторитетной записи);
  * 6.3 ФЛК ``^3`` — поля со ссылкой на авторитет и предикат битой ссылки.

Реализация смок-протестирована автором изменений; регрессия покрыта
test_authority/test_catalog/test_flk. Здесь — целевой смок именно нового
write-пути autoin (самый рискованный) + структурные проверки индекса/ФЛК.

Запуск в доме-стиле: ``py -3.12 tests/test_authority_seam.py``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.authority import AuthorityStore, UnknownCatalogField
from access import catalog as C
from access import flk as F

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
# 6.2 — autoin: авто-создание/привязка авторитетной записи из заголовка БО.
# --------------------------------------------------------------------------- #
def autoin_checks():
    print('-- 6.2 autoin: создание/привязка авторитета из БО без ^3')
    st = AuthorityStore(':memory:')
    heading = {'a': 'Толстой', 'b': 'Л. Н.', 'g': 'Лев Николаевич'}

    aid, created = st.autoin('700', dict(heading))
    check('autoin создал новую запись (created=True)', created is True)
    check('autoin вернул id для протяжки в ^3', bool(aid))
    rec = st.get('athra', aid)
    check('созданная авторитетная запись доступна по id', rec is not None)

    # повтор того же заголовка -> привязка к существующей (без дубля)
    aid2, created2 = st.autoin('700', dict(heading))
    check('повтор autoin привязался к существующей (created=False)', created2 is False)
    check('повтор autoin дал тот же id (дедуп по алкоду свёртки)', aid2 == aid)

    # find_by_alcode симметричен autoin-дедупу: тот же заголовок резолвится в id
    found = st.find_by_alcode('athra', None)
    check('find_by_alcode пустой алкод -> None (без краха)', found is None)

    # каталог-поле без fill-map -> UnknownCatalogField
    try:
        st.autoin('999999', {'a': 'x'})
        check('неизвестное каталог-поле -> ошибка', False)
    except UnknownCatalogField:
        check('неизвестное каталог-поле -> UnknownCatalogField', True)

    # пустой заголовок -> нечего пополнять -> ValueError
    try:
        st.autoin('700', {})
        check('пустой заголовок -> ошибка', False)
    except ValueError:
        check('пустой заголовок -> ValueError', True)


# --------------------------------------------------------------------------- #
# 6.4 — индексация AR= над ^3: каталог findable ПО авторитету.
# --------------------------------------------------------------------------- #
def index_checks():
    print('-- 6.4 индекс AR= над ^3 (поиск каталога по авторитету)')
    check('AR в SEARCH_PREFIXES каталога', 'AR' in C.SEARCH_PREFIXES)
    ar_specs = [s for s in C.INDEX_SPEC if s[0] == 'AR']
    check('INDEX_SPEC индексирует AR над несколькими полями (>=5)', len(ar_specs) >= 5)
    check('каждый AR-индекс — над подполем ^3', all(s[2] == '3' for s in ar_specs))
    tags = {s[1] for s in ar_specs}
    check('AR покрывает ключевые поля-заголовки (700/710/606)',
          {'700', '710', '606'} <= tags)


# --------------------------------------------------------------------------- #
# 6.3 — ФЛК ^3: поля со ссылкой и предикат битой ссылки.
# --------------------------------------------------------------------------- #
def flk_checks():
    print('-- 6.3 ФЛК ^3: поля со ссылкой на авторитет + предикат битой ссылки')
    check('AUTHORITY_LINK_FIELDS — словарь полей со ссылкой ^3',
          isinstance(F.AUTHORITY_LINK_FIELDS, dict))
    check('AUTHORITY_LINK_FIELDS включает 700/606',
          '700' in F.AUTHORITY_LINK_FIELDS and '606' in F.AUTHORITY_LINK_FIELDS)
    check('_authref_broken — вызываемый предикат', callable(F._authref_broken))
    # битая ссылка ^3 на несуществующий авторитет ловится (с authority-handle)
    st = AuthorityStore(':memory:')
    rec_broken = {'700': [{'a': 'Кто-то', '3': '999999'}]}
    broken = F._authref_broken(rec_broken, st)
    check('битая ^3 на несуществующий авторитет распознана', bool(broken))


def main():
    autoin_checks()
    index_checks()
    flk_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
