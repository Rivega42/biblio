#!/usr/bin/env python3
"""Тесты ребра 7.1 — связь записи каталога с бинарём (ПТ/образ) -> own-store DAM-реестр.

Покрыто (``access.dam``):
  * `attach` 951/953/955 к записи (db, mfn): внешний URL/файл, идентификатор блоба,
    метаданные ПТ (^A файл, ^N страниц);
  * `assets_for(db, mfn)` -> все бинари записи (это и есть закрытие 7.1: запись↔бинарь);
  * `by_kind(db, mfn, kind)` фильтрует по виду;
  * идемпотентность повторного `attach` по (db, mfn, kind, ref);
  * `get` / `remove` (отвязать ассет);
  * `rights_template` сохраняется (955^B) — вход для ребра 7.2 (rights), но rights НЕ
    импортируется (храним лишь id шаблона);
  * `stats()` по видам {951,953,955};
  * изоляция по (db, mfn): разные записи / разные БД не пересекаются.

Запуск: py -3.12 tests/test_dam.py  ; регистрируется в tests/test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.dam import (
    DamRegistry, DamStore, KIND_EXTERNAL, KIND_EMBEDDED, KIND_META, KINDS,
)

PASS = [0]
FAIL = [0]
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _reg():
    """Реестр на свежем :memory:-сторе с детерминированными часами."""
    return DamRegistry(DamStore(':memory:'), now=lambda: float(T0))


def attach_kinds_checks():
    print('-- 7.1: attach 951/953/955 к записи + assets_for')
    reg = _reg()
    a951 = reg.attach('IBIS', 42, '951', 'https://lib/ft/42.pdf', mime='application/pdf')
    a953 = reg.attach('IBIS', 42, '953', 'blob:abc123', mime='image/jpeg')
    a955 = reg.attach('IBIS', 42, '955', 'scan42.pdf', pages=120,
                      rights_template='RIGHT_VKR')
    check('951 -> внешний URL/файл', a951['kind'] == '951'
          and a951['ref'] == 'https://lib/ft/42.pdf' and a951['mime'] == 'application/pdf')
    check('953 -> идентификатор блоба', a953['kind'] == '953' and a953['ref'] == 'blob:abc123')
    check('955 -> метаданные ПТ (^A файл, ^N страниц)',
          a955['kind'] == '955' and a955['ref'] == 'scan42.pdf' and a955['pages'] == 120)
    check('created_at проставлен (детерминированно)', a951['created_at'] == float(T0))

    got = reg.assets_for('IBIS', 42)
    check('assets_for -> все 3 бинаря записи (закрытие 7.1)', len(got) == 3)
    check('assets_for несёт все виды', {r['kind'] for r in got} == set(KINDS))


def by_kind_checks():
    print('-- 7.1: by_kind фильтрует по виду')
    reg = _reg()
    reg.attach('IBIS', 7, '951', 'http://a/1')
    reg.attach('IBIS', 7, '951', 'http://a/2')
    reg.attach('IBIS', 7, '955', 'scan.pdf', pages=10)
    check('by_kind 951 -> 2 ассета', len(reg.by_kind('IBIS', 7, KIND_EXTERNAL)) == 2)
    check('by_kind 955 -> 1 ассет', len(reg.by_kind('IBIS', 7, KIND_META)) == 1)
    check('by_kind 953 -> пусто', reg.by_kind('IBIS', 7, KIND_EMBEDDED) == [])
    bad = False
    try:
        reg.by_kind('IBIS', 7, '999')
    except ValueError:
        bad = True
    check('by_kind неизвестного вида -> ValueError', bad)


def idempotent_checks():
    print('-- 7.1: идемпотентность повторного attach по (db, mfn, kind, ref)')
    reg = _reg()
    first = reg.attach('IBIS', 5, '951', 'http://x/ft.pdf')
    again = reg.attach('IBIS', 5, '951', 'http://x/ft.pdf')
    check('повторный attach -> тот же id', first['id'] == again['id'])
    check('дубль не плодит строк', len(reg.assets_for('IBIS', 5)) == 1)
    # Иной ref того же вида — отдельная связь (поля повторяющиеся).
    reg.attach('IBIS', 5, '951', 'http://x/other.pdf')
    check('иной ref -> отдельный ассет', len(reg.assets_for('IBIS', 5)) == 2)


def get_remove_checks():
    print('-- 7.1: get / remove (отвязать ассет)')
    reg = _reg()
    a = reg.attach('IBIS', 9, '953', 'blob:zzz')
    check('get -> тот же ассет', reg.get(a['id'])['ref'] == 'blob:zzz')
    check('get несуществующего -> None', reg.get(999999) is None)
    check('remove -> True', reg.remove(a['id']) is True)
    check('после remove ассета нет', reg.get(a['id']) is None)
    check('после remove запись пуста', reg.assets_for('IBIS', 9) == [])
    check('remove несуществующего -> False', reg.remove(a['id']) is False)


def rights_template_checks():
    print('-- 7.1/7.2: rights_template сохраняется (955^B), rights НЕ импортируется')
    reg = _reg()
    a = reg.attach('VKR', 100, '955', 'thesis.pdf', pages=88,
                   rights_template='RIGHT_THESIS')
    check('955^B -> rights_template сохранён', a['rights_template'] == 'RIGHT_THESIS')
    fetched = reg.get(a['id'])
    check('rights_template читается обратно', fetched['rights_template'] == 'RIGHT_THESIS')
    # 951/953 без шаблона прав -> NULL.
    b = reg.attach('VKR', 100, '951', 'http://vkr/100')
    check('951 без rights_template -> None', b['rights_template'] is None)


def stats_checks():
    print('-- 7.1: stats() по видам {951,953,955}')
    reg = _reg()
    check('пустой реестр -> assets 0, все виды 0',
          reg.stats() == {'assets': 0, 'by_kind': {'951': 0, '953': 0, '955': 0}})
    reg.attach('IBIS', 1, '951', 'u1')
    reg.attach('IBIS', 1, '951', 'u2')
    reg.attach('IBIS', 2, '953', 'b1')
    reg.attach('IBIS', 3, '955', 'f1', pages=3, rights_template='R1')
    st = reg.stats()
    check('stats assets = 4', st['assets'] == 4)
    check('stats by_kind 951=2 / 953=1 / 955=1',
          st['by_kind'] == {'951': 2, '953': 1, '955': 1})


def isolation_checks():
    print('-- 7.1: изоляция по (db, mfn)')
    reg = _reg()
    reg.attach('IBIS', 1, '951', 'http://r1')
    reg.attach('IBIS', 2, '951', 'http://r2')
    reg.attach('SK', 1, '951', 'http://sk1')           # та же mfn, иная БД
    check('запись (IBIS,1) видит только свой ассет',
          [r['ref'] for r in reg.assets_for('IBIS', 1)] == ['http://r1'])
    check('запись (IBIS,2) изолирована', [r['ref'] for r in reg.assets_for('IBIS', 2)]
          == ['http://r2'])
    check('иная БД с той же mfn изолирована',
          [r['ref'] for r in reg.assets_for('SK', 1)] == ['http://sk1'])
    check('пустая запись -> []', reg.assets_for('IBIS', 777) == [])
    # Та же (db,mfn,kind,ref) в РАЗНЫХ БД допустима (UNIQUE учитывает db).
    check('stats видит все 3 ассета', reg.stats()['assets'] == 3)


def main():
    attach_kinds_checks()
    by_kind_checks()
    idempotent_checks()
    get_remove_checks()
    rights_template_checks()
    stats_checks()
    isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
