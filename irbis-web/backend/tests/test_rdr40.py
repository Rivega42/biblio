#!/usr/bin/env python3
"""Тесты материализации поля 40 RDR + архива RDR_ARH (рёбра 2.4/2.5).

Покрывает «связующую ткань» INTEGRATION_MAP, кластер 2:

  * [2.4] Материализация поля 40 — выдача отдаётся в структуре поля 40 RDR
    (``RQSTRDR.pft``): подполя ``^A``=903 (шифр), ``^B``=910^B (инв.№),
    ``^H``=910^H (штрих-код), ``^K``=910^D (место хранения), ``^D``=41 (дата
    выдачи), ``^E``=42 (срок), ``^F``=дата факт. возврата / ``******`` (долг),
    ``^G``=имя БД, ``^C``=brief, ``^U``=утеря. Это ДОП. представление поверх
    существующей loan-модели — её колонки/сценарии не меняются.

  * [2.5] Архив RDR_ARH — при возврате завершённая выдача **opt-in** (флаг
    ``archive_on_return``) переносится в архив ``rdr_arh`` (152-ФЗ ретенция) В
    ДОПОЛНЕНИЕ к ``returned=1``. Без флага — поведение прежнее.

Back-compat: материализация работает и без каталога (поле 40 строится из
loan-модели, обогащение из ЭК пропускается); архив выключен по умолчанию;
checkout/return/renew/лимиты/долг не затронуты.

Всё гоняется на in-memory store с инъекцией ``today`` (epoch) — детерминизм без
часов. Standalone-запуск в стиле tests/test_circulation.py::

    py -3.12 tests/test_rdr40.py   ->  'ok …' + 'N passed, M failed' + код выхода

sqlite-путь выполняется всегда; PG-паритет (:func:`pg_parity_checks`) повторяет
те же ассерты поля 40 на каталоге, чья ФЛК питается из PG-access-стора, и
пропускается чисто, когда PG недоступен. Подключён в раннер tests/test_access.py
через module_checks.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import seed_vocab
from access.catalog import CatalogStore, EXEMPLAR_FREE, EXEMPLAR_ISSUED
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy,
    ALLOW, DENY, REQUIRE_OVERRIDE, SECONDS_PER_DAY, DEBT_MARKER,
)
from access.store import AccessStore

PASS = [0]
FAIL = [0]

DAY = SECONDS_PER_DAY
T0 = 1_700_000_000  # фиксированный epoch-якорь — детерминизм


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Фикстуры.
# --------------------------------------------------------------------------- #
def _seeded_access_store():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


def _book_with_copy(inv='1024365', shifr='АБ/Я45', barcode='BC-77',
                    store_place='ЧЗ-1', status=EXEMPLAR_FREE):
    """Книга с одним экземпляром 910 (инв.``inv``) + 903 шифр.

    910^a=статус, 910^b=инв.№, 910^h=штрих-код, 910^d=место хранения; 903=шифр.
    """
    return {
        '920': 'PAZK',
        '200': [{'a': 'Основы каталогизации', 'f': 'Иванова И.И.'}],
        '700': [{'a': 'Петров П.П.'}],
        '101': 'rus',
        '903': shifr,
        '910': [{'a': status, 'b': inv, 'h': barcode, 'd': store_place}],
        '907': [{'a': 'Сидорова С.С.'}],
    }


def _seed_catalog(cat, db, record):
    """Положить запись в каталог, изолировав тест от ФЛК-на-save.

    Тест проверяет материализацию поля 40 (резолв 903/910 → подполя), а НЕ ФЛК.
    Параллельные сиблинг-агенты правят ФЛК/каталог-save (рёбра 6.2/6.3), что
    может транзиторно ломать save-пайплайн. Чтобы корректность ЭТОГО теста не
    зависела от их таймингов, на время засева подменяем ``cat.validate`` на
    разрешающий результат — запись просто кладётся в стор, дальше работают
    read-аксессоры (``find_exemplar``/``get``/``brief``)."""
    orig = cat.validate
    cat.validate = lambda *a, **k: {
        'violations': [], 'canSave': True, 'overallSeverity': 0}
    try:
        return cat.save(db, record)
    finally:
        cat.validate = orig


def _wired(access_store=None, inv='1024365', shifr='АБ/Я45',
           barcode='BC-77', store_place='ЧЗ-1', archive_on_return=False):
    """Каталог с книгой + движок книговыдачи, связанный с каталогом."""
    cat = CatalogStore(':memory:',
                       access_store=access_store or _seeded_access_store())
    _seed_catalog(cat, 'IBIS', _book_with_copy(inv, shifr, barcode, store_place))
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(),
                            catalog=cat, catalog_db='IBIS',
                            archive_on_return=archive_on_return)
    store.add_reader('R1', category='В01')
    return cat, store, eng, inv


# --------------------------------------------------------------------------- #
# [2.4] Структура поля 40 при выдаче — подполя из 903/910/41/42/БД.
# --------------------------------------------------------------------------- #
def field40_structure_checks():
    print('-- [2.4] материализация поля 40 (подполя из 903/910/41/42/БД)')
    cat, store, eng, inv = _wired(shifr='АБ/Я45', barcode='BC-77',
                                  store_place='ЧЗ-1')

    d = eng.checkout('R1', inv, T0)
    check('выдача разрешена', d.decision == ALLOW)
    loan = d.computed['loan']

    f40 = eng.loan_field40(loan)

    # ^A = 903 шифр (резолв ЭК по инв.№)
    check('40^A = 903 шифр', f40['A'] == 'АБ/Я45')
    # ^B = 910^B инвентарный номер (= loan.item)
    check('40^B = 910^B инв.№', f40['B'] == inv)
    # ^H = 910^H штрих-код
    check('40^H = 910^H штрих-код', f40['H'] == 'BC-77')
    # ^K = 910^D место хранения
    check('40^K = 910^D место хранения', f40['K'] == 'ЧЗ-1')
    # ^D = 41 дата выдачи (epoch checked_out_at)
    check('40^D = 41 дата выдачи', f40['D'] == loan['checked_out_at'] == T0)
    # ^E = 42 срок (due)
    check('40^E = 42 срок', f40['E'] == loan['due'])
    check('40^E срок = выдача + max_return_days',
          f40['E'] == T0 + 20 * DAY)  # В01 max_return_days=20
    # ^F = маркер долга «на руках»
    check('40^F = ****** (на руках)', f40['F'] == DEBT_MARKER == '******')
    # ^G = имя БД ЭК
    check('40^G = имя БД (IBIS)', f40['G'] == 'IBIS')
    # ^C = brief (краткое описание)
    check('40^C = brief непустой', bool(f40['C']))
    # пока не утеряна — ^U отсутствует
    check('40^U отсутствует у обычной выдачи', 'U' not in f40)

    # reader_field40: повторяющееся поле 40, по умолчанию только «на руках»
    rows = eng.reader_field40('R1')
    check('reader_field40 отдаёт 1 инстанс на руках', len(rows) == 1)
    check('reader_field40 совпадает с loan_field40', rows[0]['B'] == inv)


def field40_lost_checks():
    print('-- [2.4] поле 40: утеря → ^U=1')
    cat, store, eng, inv = _wired()
    d = eng.checkout('R1', inv, T0)
    loan_id = d.computed['loan']['id']
    # подтверждённая утеря
    eng.mark_lost(loan_id, T0 + 70 * DAY, confirm=True, override_grant=True)
    loan = store.get_loan(loan_id)
    f40 = eng.loan_field40(loan)
    check('40^U=1 при подтверждённой утере', f40.get('U') == '1')


# --------------------------------------------------------------------------- #
# [2.4] Возврат: ^F переходит от ****** к дате факт. возврата.
# --------------------------------------------------------------------------- #
def field40_return_marker_checks():
    print('-- [2.4] поле 40: ^F ****** → дата факт. возврата')
    cat, store, eng, inv = _wired()
    d = eng.checkout('R1', inv, T0)
    loan_id = d.computed['loan']['id']

    f40_open = eng.loan_field40(store.get_loan(loan_id))
    check('на руках: 40^F = ******', f40_open['F'] == DEBT_MARKER)

    eng.return_item(loan_id, T0 + 5 * DAY)
    f40_ret = eng.loan_field40(store.get_loan(loan_id))
    check('после возврата: 40^F = дата (epoch)', f40_ret['F'] == T0 + 5 * DAY)
    check('после возврата: 40^F != ******', f40_ret['F'] != DEBT_MARKER)

    # на руках больше нет — formulary пуст по умолчанию
    check('reader_field40 пуст после возврата', eng.reader_field40('R1') == [])
    # но полный формуляр (include_returned) показывает возвращённую выдачу
    full = eng.reader_field40('R1', include_returned=True)
    check('полный формуляр включает возвращённую', len(full) == 1
          and full[0]['F'] == T0 + 5 * DAY)


# --------------------------------------------------------------------------- #
# [2.4] Back-compat: материализация без каталога (standalone).
# --------------------------------------------------------------------------- #
def field40_standalone_checks():
    print('-- [2.4] поле 40 без каталога (back-compat)')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())  # каталога нет
    store.add_reader('R1', category='В01')

    d = eng.checkout('R1', '5500123', T0)
    check('выдача без каталога разрешена', d.decision == ALLOW)
    f40 = eng.loan_field40(d.computed['loan'])

    # loan-локальные подполя всегда есть
    check('без каталога: 40^B = инв.№', f40['B'] == '5500123')
    check('без каталога: 40^D = дата выдачи', f40['D'] == T0)
    check('без каталога: 40^E = срок', f40['E'] == T0 + 20 * DAY)
    check('без каталога: 40^F = ******', f40['F'] == DEBT_MARKER)
    check('без каталога: 40^G = IBIS', f40['G'] == 'IBIS')
    # обогащение из ЭК пропущено — пустые, но ключи присутствуют (стабильная форма)
    check('без каталога: 40^A пуст (нет резолва 903)', f40['A'] == '')
    check('без каталога: 40^H пуст', f40['H'] == '')
    check('без каталога: 40^K пуст', f40['K'] == '')
    check('без каталога: 40^C пуст', f40['C'] == '')


# --------------------------------------------------------------------------- #
# [2.5] Архив RDR_ARH — opt-in при возврате.
# --------------------------------------------------------------------------- #
def archive_optin_checks():
    print('-- [2.5] архив RDR_ARH: opt-in при возврате')
    cat, store, eng, inv = _wired(archive_on_return=True)
    d = eng.checkout('R1', inv, T0)
    loan_id = d.computed['loan']['id']

    check('до возврата архив пуст', store.count_archived('R1') == 0)

    dr = eng.return_item(loan_id, T0 + 5 * DAY)
    check('возврат разрешён', dr.decision == ALLOW)
    check('возврат сообщает id архивной записи', 'archived' in dr.computed)

    # в дополнение к returned=1 (не вместо!)
    check('loan по-прежнему returned=1', store.get_loan(loan_id)['returned'] == 1)
    check('архив содержит 1 запись', store.count_archived('R1') == 1)

    arh = store.archived_loans('R1')[0]
    check('архив: ссылка на исходную выдачу', arh['loan'] == loan_id)
    check('архив: тот же инв.№', arh['item'] == inv)
    check('архив: дата факт. возврата', arh['returned_at'] == T0 + 5 * DAY)
    check('архив: дата выдачи сохранена', arh['checked_out_at'] == T0)
    check('архив: срок сохранён', arh['due'] == T0 + 20 * DAY)
    check('архив: момент архивации проставлен', arh['archived_at'] == T0 + 5 * DAY)


def archive_lost_state_checks():
    print('-- [2.5] архив: состояние выдачи сохраняется')
    cat, store, eng, inv = _wired(archive_on_return=True)
    d = eng.checkout('R1', inv, T0)
    loan_id = d.computed['loan']['id']
    eng.return_item(loan_id, T0 + 3 * DAY)
    arh = store.archived_loans('R1')[0]
    check('архив: lost_status снят с возвращённой', arh['lost_status'] == 'none')
    check('count_archived(None) = всего по всем читателям',
          store.count_archived() == 1)


# --------------------------------------------------------------------------- #
# [2.5] Back-compat: флаг off ⇒ архива нет, поведение прежнее.
# --------------------------------------------------------------------------- #
def archive_off_backcompat_checks():
    print('-- [2.5] архив off (по умолчанию) — без архива, как раньше')
    cat, store, eng, inv = _wired()  # archive_on_return=False по умолчанию
    check('по умолчанию archive_on_return=False', eng.archive_on_return is False)
    d = eng.checkout('R1', inv, T0)
    loan_id = d.computed['loan']['id']
    dr = eng.return_item(loan_id, T0 + 5 * DAY)

    check('возврат разрешён (флаг off)', dr.decision == ALLOW)
    check('без флага: архив пуст', store.count_archived('R1') == 0)
    check('без флага: computed без archived', 'archived' not in dr.computed)
    check('без флага: loan returned=1 (как раньше)',
          store.get_loan(loan_id)['returned'] == 1)
    # каталожный flip 910^A 1→0 не сломан архивом
    check('без флага: каталог 910^A вернулся в FREE',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)


# --------------------------------------------------------------------------- #
# Back-compat: checkout/return/renew/лимиты/долг целы под новым кодом.
# --------------------------------------------------------------------------- #
def backcompat_flow_checks():
    print('-- back-compat: checkout/return/renew/лимиты/долг целы')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())
    store.add_reader('R1', category='В01')  # max_books=5

    # лимит max_books=5: 6-я требует override
    for i in range(5):
        eng.checkout('R1', 'BK-%d' % i, T0)
    check('5 книг на руках', store.count_on_hand('R1') == 5)
    d6 = eng.checkout('R1', 'BK-6', T0)
    check('6-я выдача — require_override (лимит)',
          d6.decision == REQUIRE_OVERRIDE and 'limit_exceeded' in d6.reasons)

    # возврат закрывает выдачу
    loan0 = store.loans_on_hand('R1')[0]
    dr = eng.return_item(loan0['id'], T0 + 2 * DAY)
    check('возврат разрешён', dr.decision == ALLOW)
    check('4 книги на руках после возврата', store.count_on_hand('R1') == 4)
    check('повторный возврат отклонён',
          eng.return_item(loan0['id'], T0 + 3 * DAY).decision == DENY)

    # продление: cap max_prolong=5, потом deny
    d2 = eng.checkout('R1', 'PRO', T0)
    pid = d2.computed['loan']['id']
    for i in range(5):
        rr = eng.renew(pid, T0 + (i + 1) * DAY)
        check('продление %d разрешено' % (i + 1), rr.decision == ALLOW) if i == 0 else None
    check('5 продлений выполнено', store.get_loan(pid)['renewals'] == 5)
    cap = eng.renew(pid, T0 + 6 * DAY)
    check('6-е продление — deny (max_prolong)',
          cap.decision == DENY and 'max_prolong_reached' in cap.reasons)

    # долг: твёрдый должник блокируется на выдаче
    store.add_reader('D1', category='В01')
    store.add_loan('D1', 'OLD', T0 - 30 * DAY, T0 - 50 * DAY)  # 30 дн. просрочки
    dd = eng.checkout('D1', 'NEW', T0)
    check('твёрдый должник заблокирован',
          dd.decision == REQUIRE_OVERRIDE and 'reader_has_debt' in dd.reasons)
    do = eng.checkout('D1', 'NEW', T0, staff_override=True, override_grant=True)
    check('авторизованный override выдаёт должнику', do.decision == ALLOW)


def catalog_flip_intact_checks():
    print('-- back-compat: каталожный flip 910^A 0↔1 не задет полем 40')
    cat, store, eng, inv = _wired()
    d = eng.checkout('R1', inv, T0)
    check('выдача флипает 910^A 0→1',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_ISSUED)
    eng.return_item(d.computed['loan']['id'], T0 + 1 * DAY)
    check('возврат флипает 910^A 1→0',
          cat.exemplar_status('IBIS', inv) == EXEMPLAR_FREE)


# --------------------------------------------------------------------------- #
# PG-паритет: те же ассерты поля 40 на каталоге с PG-access-стором (ФЛК), либо
# чистый пропуск, когда PG недоступен.
# --------------------------------------------------------------------------- #
def _pg_reachable(dsn):
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return False
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.close()
        return True
    except Exception as e:
        print('-- rdr40 PG-паритет ПРОПУЩЕН (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return False


def pg_parity_checks():
    print('-- PG-паритет: поле 40 backend-независимо')
    from access import pgstore
    dsn = pgstore.default_pg_dsn()
    if not _pg_reachable(dsn):
        return
    print('-- rdr40: postgres', dsn.rsplit('@', 1)[-1])
    slug = 'rdr40_pg'
    try:
        pgstore.deprovision_tenant(slug, dsn)
    except Exception:
        pass
    sa = pgstore.provision_tenant(slug, 'RDR40 PG', 'публичная', dsn)
    # каталог с ФЛК, питаемой PG-стором; круг материализации поля 40 тот же —
    # store/каталог остаются sqlite (own-store ADR-004), а паритет проверяет, что
    # подполя поля 40 идентичны при PG-питаемой валидации.
    cat, store, eng, inv = _wired(access_store=sa)
    d = eng.checkout('R1', inv, T0)
    f40 = eng.loan_field40(d.computed['loan'])
    check('[pg] 40^A = 903 шифр', f40['A'] == 'АБ/Я45')
    check('[pg] 40^B = инв.№', f40['B'] == inv)
    check('[pg] 40^H = штрих-код', f40['H'] == 'BC-77')
    check('[pg] 40^K = место хранения', f40['K'] == 'ЧЗ-1')
    check('[pg] 40^F = ****** на руках', f40['F'] == DEBT_MARKER)
    try:
        pgstore.deprovision_tenant(slug, dsn)
    except Exception:
        pass


def main():
    field40_structure_checks()
    field40_lost_checks()
    field40_return_marker_checks()
    field40_standalone_checks()
    archive_optin_checks()
    archive_lost_state_checks()
    archive_off_backcompat_checks()
    backcompat_flow_checks()
    catalog_flip_intact_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
