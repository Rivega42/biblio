#!/usr/bin/env python3
"""Тесты поиска-по-связи иерархии записей каталога (рёбра 9.1/9.2/9.3).

Связь иерархии хранится зеркальной парой ``HOST=``/``LINK=`` в ``record_index``:
издание-хозяин несёт ключ-идентичность под ``HOST=`` (200^a заглавие / 11^a ISSN /
903 шифр), зависимая запись — тот же ключ как отсылку под ``LINK=`` (463/461/481/
963). ``CatalogStore.linked_records(db, mfn, kind)`` обходит ребро в обе стороны:
``kind='children'`` от хозяина → зависимые; ``kind='host'`` от зависимой → хозяин.

Что проверяется:
  1. 9.1 статья↔журнал (463): хозяин 'children' → статьи; статья 'host' → журнал;
     посторонний журнал не примешивает чужую статью.
  2. 9.2 номер↔журнал (461) — обе стороны.
  3. 9.3 том↔многотомник (481) — обе стороны.
  4. краевые: матч по нормализованному ключу (регистр/пробелы); self не считается
     своим родственником; запись без ключей нужной стороны → пусто; несуществующий
     mfn → пусто без краха.

Дом-стиль (как test_catalog.py)::
  py -3.12 tests/test_record_links.py  -> 'ok …' + 'N passed, M failed', exit!=0
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import seed_vocab
from access.catalog import CatalogStore
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


_INV = [0]


def _rec(title, **extra):
    """Валидная книжная запись (проходит ФЛК на сохранении) с уникальным экз.№."""
    _INV[0] += 1
    base = {
        '920': 'PAZK',
        '200': [{'a': title}],
        '700': [{'a': 'Автор'}],
        '610': [{'': 'тест'}],
        '101': 'rus',
        '910': [{'a': '0', 'b': 'INV%05d' % _INV[0]}],
    }
    base.update(extra)
    return base


def _mfn(store, db, rec):
    return store.save(db, rec)['mfn']


def _mfns(result):
    return {it['mfn'] for it in result['items']}


# --------------------------------------------------------------------------- #
# 9.1 статья ↔ журнал/сборник (463).
# --------------------------------------------------------------------------- #
def article_journal_checks():
    print('-- 9.1 статья ↔ журнал (463^c/^j ↔ 200^a/11^a)')
    st = _store()
    jm = _mfn(st, 'IBIS', _rec('Театр и жизнь', **{'11': [{'a': '1111-2222'}]}))
    am = _mfn(st, 'IBIS', _rec('Сцена сегодня',
                               **{'463': [{'c': 'Театр и жизнь', 'j': '1111-2222'}]}))
    am2 = _mfn(st, 'IBIS', _rec('Свет и тень',
                                **{'463': [{'c': 'Театр и жизнь'}]}))
    # посторонний журнал + его статья — не должны примешаться к выдаче jm
    om = _mfn(st, 'IBIS', _rec('Другой журнал', **{'11': [{'a': '9999-0000'}]}))
    _mfn(st, 'IBIS', _rec('Чужая статья', **{'463': [{'c': 'Другой журнал'}]}))

    kids = st.linked_records('IBIS', jm, 'children')
    check('журнал children → обе свои статьи', {am, am2} <= _mfns(kids))
    check('журнал children → ровно 2 (чужая статья не примешалась)', kids['total'] == 2)

    host = st.linked_records('IBIS', am, 'host')
    check('статья host → её журнал', _mfns(host) == {jm})
    check('статья host → ровно 1', host['total'] == 1)

    check('посторонний журнал не считает чужую статью jm своим хозяином',
          jm not in _mfns(st.linked_records('IBIS', om, 'children')))


# --------------------------------------------------------------------------- #
# 9.2 номер ↔ журнал (461).
# --------------------------------------------------------------------------- #
def issue_journal_checks():
    print('-- 9.2 номер ↔ журнал (461^c)')
    st = _store()
    jm = _mfn(st, 'IBIS', _rec('Вестник сцены'))
    n1 = _mfn(st, 'IBIS', _rec('Вестник сцены, 2026 N1',
                               **{'461': [{'c': 'Вестник сцены'}]}))
    check('журнал children → номер', n1 in _mfns(st.linked_records('IBIS', jm, 'children')))
    check('номер host → журнал', jm in _mfns(st.linked_records('IBIS', n1, 'host')))


# --------------------------------------------------------------------------- #
# 9.3 том ↔ многотомник (481).
# --------------------------------------------------------------------------- #
def volume_multivolume_checks():
    print('-- 9.3 том ↔ многотомник (481^c)')
    st = _store()
    mv = _mfn(st, 'IBIS', _rec('Собрание сочинений'))
    v1 = _mfn(st, 'IBIS', _rec('Собрание сочинений. Т.1',
                               **{'481': [{'c': 'Собрание сочинений'}]}))
    v2 = _mfn(st, 'IBIS', _rec('Собрание сочинений. Т.2',
                               **{'481': [{'c': 'Собрание сочинений'}]}))
    kids = st.linked_records('IBIS', mv, 'children')
    check('многотомник children → оба тома', _mfns(kids) == {v1, v2})
    check('том host → сводная', mv in _mfns(st.linked_records('IBIS', v1, 'host')))


# --------------------------------------------------------------------------- #
# 4. Краевые: нормализация / self / пусто.
# --------------------------------------------------------------------------- #
def edge_checks():
    print('-- краевые: нормализация / self / пусто')
    st = _store()
    jm = _mfn(st, 'IBIS', _rec('Театр и жизнь'))
    am = _mfn(st, 'IBIS', _rec('Статья X', **{'463': [{'c': '  ТЕАТР И ЖИЗНЬ '}]}))
    check('матч по нормализованному ключу (регистр/пробелы)',
          am in _mfns(st.linked_records('IBIS', jm, 'children')))

    plain = _mfn(st, 'IBIS', _rec('Одиночная книга'))
    check('запись без LINK= → host пусто', st.linked_records('IBIS', plain, 'host')['total'] == 0)

    # self не родственник: запись, чьё 463^c == своему же 200^a, не находит себя
    self_mfn = _mfn(st, 'IBIS', _rec('Зеркало', **{'463': [{'c': 'Зеркало'}]}))
    check('self исключён (запись не свой родственник)',
          self_mfn not in _mfns(st.linked_records('IBIS', self_mfn, 'children')))

    check('несуществующий mfn → пусто без краха',
          st.linked_records('IBIS', 999999, 'children')['total'] == 0)


def main():
    article_journal_checks()
    issue_journal_checks()
    volume_multivolume_checks()
    edge_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
