#!/usr/bin/env python3
"""Замыкание двух хвостов книговыдачи — рёбра 2.3 и 2.6 INTEGRATION_MAP.

Грунтовано на DB_CIRCULATION §3/§5/§6/§8 и INTEGRATION_MAP кластер 2.

Покрывает:
  * **2.3 RQST 903 (шифр заказа) → запись каталога.**
    ``CirculationEngine.resolve_order_record(item_or_shifr, catalog_db=None)``
    резолвит mfn записи ЭК по шифру ``903`` = ``I=`` (основной путь заказа,
    ``DBNPREFSHIFR=I=``) И по инв.№ ``910^b`` как fallback (существующий путь не
    ломаем). Без каталога-хендла — ``None`` (back-compat). Найдено / не найдено /
    приоритет шифра / автономность.
  * **2.6 reservstatus (RQST 910^A 0–4) ↔ hold.status.** Двусторонний словарь
    кодов ``reservstatus.mnu`` (0–4) ↔ наш enum брони
    (queued|ready|fulfilled|cancelled|expired) — «одно подполе, разные кодировки»
    (recon #CIRC-06). Обе стороны, round-trip, краевые коды.
  * **back-compat:** существующий checkout/return_item/place_hold цел; резолв по
    инв.№ (910^b, ребро 2.1) не сломан.

Запуск автономно (стиль tests/test_circulation.py)::

    py -3.12 tests/test_circ_resolve.py  ->  'ok …' + 'N passed, M failed' + код

Подключён в раннер tests/test_access.py рядом с test_circulation (module_checks
гоняет каждый *_checks()). sqlite зелёный; PG-паритет — резолв читает каталог
через тот же опц. handle, бэкенд-агностичен (in-memory sqlite-каталог в тестах).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import seed_vocab
from access.catalog import CatalogStore, EXEMPLAR_FREE, EXEMPLAR_ISSUED
from access.store import AccessStore
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy,
    RESERVSTATUS_TO_HOLD, HOLD_TO_RESERVSTATUS,
    ALLOW, SECONDS_PER_DAY,
)

PASS = [0]
FAIL = [0]

DAY = SECONDS_PER_DAY
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Fixtures — реальный каталог (in-memory) с записью, несущей 903 шифр + 910 экз.
# --------------------------------------------------------------------------- #
def _seeded_access_store():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


def _book(shifr='AB/Ч-15', inv='INV-777', status=EXEMPLAR_FREE):
    """Валидная книга: поле 903 (шифр документа) + один экз. 910 по инв.№ ``inv``."""
    return {
        '920': 'PAZK',
        '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.'}],
        '700': [{'a': 'Петров П.П.'}],
        '101': 'rus',
        '903': shifr,
        '910': [{'a': status, 'b': inv}],
        '907': [{'a': 'Сидорова С.С.'}],
    }


def _engine_with_catalog(shifr='AB/Ч-15', inv='INV-777', status=EXEMPLAR_FREE):
    """Движок книговыдачи с подключённым каталогом и одной записью в ЭК."""
    cat = CatalogStore(':memory:', access_store=_seeded_access_store())
    cat.save('IBIS', _book(shifr, inv, status))
    eng = CirculationEngine(store=CirculationStore(':memory:'),
                            policy=default_policy(), catalog=cat, catalog_db='IBIS')
    return cat, eng


# --------------------------------------------------------------------------- #
# 2.3 — RQST 903 (шифр заказа) → запись каталога (резолв по I= и 910^b).
# --------------------------------------------------------------------------- #
def resolve_order_record_checks():
    print('-- ребро 2.3: resolve_order_record (903 ↔ I=) + fallback 910^b')
    cat, eng = _engine_with_catalog(shifr='AB/Ч-15', inv='INV-777')

    # mfn записи в каталоге (для сверки, что резолв нашёл именно её).
    found = cat.find_exemplar('IBIS', 'INV-777')
    check('фикстура: экз. по 910^b есть в каталоге', found is not None)
    rec_mfn = found[0]

    # (а) основной путь — по шифру 903 = I= (DBNPREFSHIFR=I=).
    check('903→запись каталога: найдено по шифру (I=)',
          eng.resolve_order_record('AB/Ч-15') == rec_mfn)
    # пробел/регистр шифра нормализуется поиском (casefold+trim, как I=).
    check('903 резолв терпим к пробелам',
          eng.resolve_order_record('  AB/Ч-15 ') == rec_mfn)

    # (б) fallback — по инв.№ 910^b (существующий путь резолва не ломаем).
    check('910^b→запись каталога: найдено по инв.№ (fallback)',
          eng.resolve_order_record('INV-777') == rec_mfn)

    # (в) не найдено — ни шифр, ни инв.№ не совпали → None.
    check('903→запись: не найдено → None', eng.resolve_order_record('НЕТ-ТАКОГО') is None)
    check('пустой/None ключ → None',
          eng.resolve_order_record('') is None and eng.resolve_order_record(None) is None)

    # (г) приоритет: при наличии шифра берётся запись по 903, даже если такая же
    # строка не является инв.№ (резолв шифра идёт первым).
    cat2 = CatalogStore(':memory:', access_store=_seeded_access_store())
    cat2.save('IBIS', _book(shifr='SH-1', inv='INV-A'))
    cat2.save('IBIS', _book(shifr='SH-2', inv='INV-B'))
    eng2 = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), catalog=cat2, catalog_db='IBIS')
    mfn_sh1 = cat2.search('IBIS', 'I=SH-1')['items'][0]['mfn']
    mfn_invb = cat2.find_exemplar('IBIS', 'INV-B')[0]
    check('шифр-резолв выбирает запись по 903', eng2.resolve_order_record('SH-1') == mfn_sh1)
    check('инв.№-резолв выбирает запись по 910^b', eng2.resolve_order_record('INV-B') == mfn_invb)

    # (д) явный catalog_db: пустая/иная БД → None (нет записей под этим именем).
    check('иная catalog_db без записей → None',
          eng.resolve_order_record('AB/Ч-15', catalog_db='RQST') is None)

    # (е) back-compat: без каталога-хендла движок автономен — резолв даёт None.
    eng_solo = CirculationEngine(store=CirculationStore(':memory:'),
                                 policy=default_policy())  # catalog=None
    check('без каталога resolve_order_record → None (standalone)',
          eng_solo.resolve_order_record('AB/Ч-15') is None)


# --------------------------------------------------------------------------- #
# 2.6 — reservstatus (RQST 910^A 0–4) ↔ hold.status (в обе стороны).
# --------------------------------------------------------------------------- #
def reservstatus_mapping_checks():
    print('-- ребро 2.6: reservstatus.mnu (0–4) ↔ hold.status enum')
    eng = CirculationEngine(store=CirculationStore(':memory:'), policy=default_policy())

    # прямое: код брони → наш enum (DB_CIRCULATION §5 «БРОНИРОВАНИЕ»).
    expected_in = {'0': 'queued', '1': 'ready', '2': 'fulfilled',
                   '3': 'expired', '4': 'expired'}
    for code, st in expected_in.items():
        check('reservstatus %s → %s' % (code, st),
              eng.resolve_hold_status_in(code) == st)
    # принимает и число, не только строку.
    check('reservstatus 1 (int) → ready', eng.resolve_hold_status_in(1) == 'ready')
    check('таблица RESERVSTATUS_TO_HOLD совпадает', RESERVSTATUS_TO_HOLD == expected_in)

    # неизвестный/пустой код → None (нечего отображать).
    check('неизвестный код брони → None', eng.resolve_hold_status_in('9') is None)
    check('None код → None', eng.resolve_hold_status_in(None) is None)

    # обратное: наш enum → код брони.
    expected_out = {'queued': '0', 'ready': '1', 'fulfilled': '2',
                    'expired': '3', 'cancelled': None}
    for st, code in expected_out.items():
        check('hold.status %s → reservstatus %r' % (st, code),
              eng.hold_status_to_reservstatus(st) == code)
    check('таблица HOLD_TO_RESERVSTATUS совпадает', HOLD_TO_RESERVSTATUS == expected_out)
    check('неизвестный enum → None', eng.hold_status_to_reservstatus('frobnicate') is None)

    # round-trip enum→код→enum для кодируемых статусов (cancelled не имеет кода).
    for st in ('queued', 'ready', 'fulfilled'):
        code = eng.hold_status_to_reservstatus(st)
        check('round-trip %s' % st, eng.resolve_hold_status_in(code) == st)
    # expired кодируется в '3'; обратно '3'→expired (3 и 4 оба → expired).
    check('expired→3→expired (3/4 схлопнуты в expired)',
          eng.resolve_hold_status_in(eng.hold_status_to_reservstatus('expired')) == 'expired')
    # cancelled — чисто наш статус, кода брони нет → None (бронь исчезает из RQST).
    check('cancelled→reservstatus None (нет кода в reservstatus.mnu)',
          eng.hold_status_to_reservstatus('cancelled') is None)

    # «развести одно подполя — разные кодировки»: код брони '1' (получен на МВ)
    # — это НЕ статус экземпляра ЭК ste.mnu '1' (выдан читателю). Наш резолв
    # брони даёт 'ready', а не экземплярный EXEMPLAR_ISSUED.
    check('reservstatus 1 ≠ ste.mnu 1 (разные кодировки)',
          eng.resolve_hold_status_in('1') == 'ready' and EXEMPLAR_ISSUED == '1')


# --------------------------------------------------------------------------- #
# back-compat: существующий checkout/return/hold цел; резолв по 910^b (2.1) жив.
# --------------------------------------------------------------------------- #
def back_compat_checks():
    print('-- back-compat: checkout/return/hold + 910^b flip целы')
    cat, eng = _engine_with_catalog(shifr='BC/1', inv='BC-INV-1', status=EXEMPLAR_FREE)
    eng.store.add_reader('R1', category='В01')

    # checkout по-прежнему флипает 910^A 0→1 по инв.№ (ребро 2.1 — не сломали).
    d = eng.checkout('R1', 'BC-INV-1', T0)
    check('checkout всё ещё ALLOW', d.decision == ALLOW)
    check('910^A 0→1 при выдаче (резолв по 910^b цел)',
          cat.exemplar_status('IBIS', 'BC-INV-1') == EXEMPLAR_ISSUED)
    loan = d.computed['loan']
    check('выдача записана в loan-стор', eng.store.count_on_hand('R1') == 1)

    # резолв заказа этой выдачи к записи каталога — по инв.№ И по шифру дают ту же.
    rec_mfn = cat.find_exemplar('IBIS', 'BC-INV-1')[0]
    check('resolve_order_record(инв.№ выдачи) → запись', eng.resolve_order_record('BC-INV-1') == rec_mfn)
    check('resolve_order_record(шифр 903) → та же запись', eng.resolve_order_record('BC/1') == rec_mfn)

    # return по-прежнему флипает 910^A 1→0.
    dr = eng.return_item(loan['id'], T0 + 5 * DAY)
    check('return всё ещё ALLOW', dr.decision == ALLOW)
    check('910^A 1→0 при возврате', cat.exemplar_status('IBIS', 'BC-INV-1') == EXEMPLAR_FREE)

    # place_hold всё ещё считает FIFO-позицию (hold.status enum не тронут).
    eng.store.add_reader('R2', category='В01')
    eng.checkout('R1', 'BC-INV-1', T0 + 6 * DAY)            # снова на руках
    dh = eng.place_hold('R2', 'BC-INV-1', T0 + 7 * DAY)
    check('place_hold всё ещё ALLOW', dh.decision == ALLOW)
    check('hold.status остаётся нашим enum (queued)',
          eng.store.get_hold(dh.computed['hold']['id'])['status'] == 'queued')

    # автономность: без каталога checkout/return работают (резолв-методы — opt-in).
    solo = CirculationEngine(store=CirculationStore(':memory:'), policy=default_policy())
    solo.store.add_reader('S1', category='В01')
    ds = solo.checkout('S1', 'NO-CAT', T0)
    check('checkout без каталога ALLOW (standalone)', ds.decision == ALLOW)
    check('resolve без каталога → None (standalone)',
          solo.resolve_order_record('NO-CAT') is None)


def main():
    resolve_order_record_checks()
    reservstatus_mapping_checks()
    back_compat_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
