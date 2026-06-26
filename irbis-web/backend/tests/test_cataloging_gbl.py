#!/usr/bin/env python3
"""HTTP-route тесты исполнения глобальной корректировки (.gbl) по выборке каталога.

Ребро 11.2 INTEGRATION_MAP: интерпретатор ``access/gbl.py`` сам по себе покрыт
``test_gbl.py`` (парсер/апплай/preview/кросс-БД, чистый stdlib), а ЭТОТ сьют
доказывает, что задание .gbl реально ПРОГОНЯЕТСЯ по выборке записей каталога
через боевой диспетчер ``core.Api.route()`` (тот же путь, что у server.py /
app_aiohttp.py), с собственным стором ``CatalogStore`` (':memory:').

Покрыто (контракт задачи):
  1. preview НЕ меняет стор (сухой прогон — чистая проекция);
  2. apply реально меняет поле записи (REP/ADD), и она перечитывается изменённой;
  3. CORREC правит ДРУГУЮ запись (кросс-запись по терму);
  4. NEWMFN создаёт НОВУЮ запись (emit → catalog.save → новый MFN);
  5. guard: сессия без права ``cat.gbl`` (guest/reader) → 403.

ФОРМАТ-вычислитель НЕ инжектится — ``gbl`` делегирует его реальному PFT-движку
``access.pft.eval`` (он импортируем); литералы ``'X'`` / ссылки ``v910`` этого
достаточно для типовых ADD/REP, что и проверяется ниже.

Запуск (в стиле дома, как tests/test_acq_bp_routes.py)::
  py -3.12 tests/test_cataloging_gbl.py  -> 'ok ...' + 'N passed, M failed' + код выхода
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS
from access.catalog import CatalogStore
from access.store import AccessStore
from access import seed_vocab

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Грант каталогизатора для функции cat.gbl (в core.py FUNCTION_MODULE → cataloging).
# Боевой аккаунт нёс бы его через сидированную роль; здесь чеканим прямо на токен.
STAFF_GRANTS = [
    {'function': 'cat.gbl', 'db': '*', 'level': 'write'},
    {'function': 'record.write', 'db': '*', 'level': 'write'},
]

DB = 'IBIS'


def _seeded_access():
    st = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(st, from_catalog=False)
    return st


def _api():
    """Сконструированный Api БЕЗ живого ИРБИС, с собственным CatalogStore поверх
    ':memory:'. Конструктор Api к ИРБИС не подключается (как в test_acq_bp_routes)."""
    os.environ['JWT_SECRET'] = 'gbl-routes-test-secret'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.catalog = CatalogStore(':memory:', access_store=_seeded_access())
    return api, _core


def _staff(api, login='cataloger'):
    tok, _ = api._new_session('staff', login, STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


def _good_book(title='Основы каталогизации', author='Петров П.П.'):
    """Чистая валидная книга (проходит полный прогон ФЛК на save)."""
    return {
        '920': 'PAZK',
        '200': [{'a': title, 'f': author}],
        '700': [{'a': author}],
        '101': 'rus',
    }


def _post(api, headers, body):
    return api.route('POST', '/api/cataloging/gbl', {}, body, headers)


# --------------------------------------------------------------------------- #
# 1. preview не меняет стор.
# --------------------------------------------------------------------------- #
def preview_checks():
    print('-- preview (сухой прогон, без мутации стора)')
    api, _ = _api()
    headers = _staff(api)
    saved = api.catalog.save(DB, _good_book())
    mfn = saved['mfn']

    # REP заменит рабочий лист 920 PAZK -> SPEC; в preview стор не трогаем.
    job = "0\nREP\n920\n*\n'SPEC'\n\n"
    status, payload = _post(api, headers, {
        'db': DB, 'mfns': [mfn], 'gbl': job, 'mode': 'preview'})
    check('preview 200 ok', status == 200 and payload['ok'] is True)
    data = payload['data']
    check('preview mode echoed', data['mode'] == 'preview' and data['processed'] == 1)
    check('preview reports 1 changed record', data['changed'] == 1)
    rec0 = data['records'][0]
    check('preview record keyed by mfn', rec0['mfn'] == mfn)
    mod = [c for c in rec0['changes']
           if c['tag'] == '920' and c['op'] == 'modify']
    check('preview diff: 920 PAZK->SPEC',
          len(mod) == 1 and mod[0]['before'] == 'PAZK' and mod[0]['after'] == 'SPEC')
    # стор НЕ изменён — запись всё ещё PAZK.
    after = api.catalog.get(DB, mfn)
    check('preview did NOT persist (920 still PAZK)',
          _whole(after, '920') == ['PAZK'])


# --------------------------------------------------------------------------- #
# 2. apply реально меняет поле и запись перечитывается изменённой.
# --------------------------------------------------------------------------- #
def apply_rep_checks():
    print('-- apply (REP/ADD меняют запись в сторе)')
    api, _ = _api()
    headers = _staff(api)
    mfn = api.catalog.save(DB, _good_book())['mfn']

    # REP 920 PAZK->SPEC + ADD нового экземпляра 910^b.
    job = ("0\n"
           "REP\n920\n*\n'SPEC'\n\n"
           "ADD\n910^b\n\n'INV-777'\n\n")
    status, payload = _post(api, headers, {
        'db': DB, 'mfns': [mfn], 'gbl': job, 'mode': 'apply'})
    check('apply 200 ok', status == 200 and payload['ok'] is True)
    data = payload['data']
    check('apply reports 1 changed', data['changed'] == 1 and data['processed'] == 1)
    check('apply per-record status changed',
          data['records'][0]['status'] == 'changed')

    after = api.catalog.get(DB, mfn)
    check('apply persisted REP 920->SPEC', _whole(after, '920') == ['SPEC'])
    check('apply persisted ADD 910^b', _sub(after, '910', 'b') == ['INV-777'])
    # Перечитка по поиску тоже видит новый рабочий лист (переиндексация на save).
    res = api.catalog.search_records(DB, 'IN=INV-777', limit=5)
    check('apply reindexed: IN=INV-777 findable',
          any(it['mfn'] == mfn for it in res['items']))


# --------------------------------------------------------------------------- #
# 2b. apply: DEL и REP-empty удаляют поле.
# --------------------------------------------------------------------------- #
def apply_del_checks():
    print('-- apply (DEL удаляет поле)')
    api, _ = _api()
    headers = _staff(api)
    book = _good_book()
    book['910'] = [{'b': 'A'}, {'b': 'B'}]
    mfn = api.catalog.save(DB, book)['mfn']

    job = "0\nDEL\n910\n*\n\n\n"           # удалить все повторения 910
    status, payload = _post(api, headers, {
        'db': DB, 'mfns': [mfn], 'gbl': job, 'mode': 'apply'})
    check('apply DEL 200 ok', status == 200)
    after = api.catalog.get(DB, mfn)
    check('apply DEL removed all 910', not after.get('910'))
    check('apply DEL kept 200^a',
          _sub(after, '200', 'a') == ['Основы каталогизации'])


# --------------------------------------------------------------------------- #
# 3. CORREC правит ДРУГУЮ запись (кросс-запись по терму).
# --------------------------------------------------------------------------- #
def correc_checks():
    print('-- apply CORREC (кросс-правка чужой записи по терму)')
    api, _ = _api()
    headers = _staff(api)
    # источник, по чьему 910 копируем; и цель CORREC (резолвим по инв.№ цели).
    src_mfn = api.catalog.save(DB, dict(_good_book('Источник'),
                                        **{'910': [{'b': 'SRC-INV'}]}))['mfn']
    tgt_mfn = api.catalog.save(DB, dict(_good_book('Цель'),
                                        **{'910': [{'b': 'TGT-INV'}]}))['mfn']

    # CORREC: db=IBIS, ключ -> 1001, термин 'TGT-INV' (резолвится find_exemplar →
    # запись-владелец tgt_mfn); тело добавляет литеральный 909 в найденную запись.
    job = ("0\nCORREC\n'IBIS'\n'KEY'\n'TGT-INV'\n"
           "ADD\n909\n\n'touched-by-correc'\n\n"
           "END\n")
    status, payload = _post(api, headers, {
        'db': DB, 'mfns': [src_mfn], 'gbl': job, 'mode': 'apply'})
    check('CORREC 200 ok', status == 200 and payload['ok'] is True)
    data = payload['data']
    check('CORREC emitted >=1 cross record', data['createdCount'] >= 1)

    # Цель перечитывается изменённой; 1001 (модельное поле) стёрто после тела.
    tgt = api.catalog.get(DB, tgt_mfn)
    check('CORREC wrote 909 into the OTHER record',
          _whole(tgt, '909') == ['touched-by-correc'])
    check('CORREC stripped model field 1001', '1001' not in tgt)
    # Источник CORREC сам по себе не получил 909.
    src = api.catalog.get(DB, src_mfn)
    check('CORREC did not touch source 909', not src.get('909'))


# --------------------------------------------------------------------------- #
# 4. NEWMFN создаёт новую запись (emit → catalog.save → новый MFN).
# --------------------------------------------------------------------------- #
def newmfn_checks():
    print('-- apply NEWMFN (создание новой записи через emit)')
    api, _ = _api()
    headers = _staff(api)
    src_mfn = api.catalog.save(DB, _good_book('Книга-источник'))['mfn']
    count_before = api.catalog.count(DB)

    # NEWMFN в ту же БД ('*'): новая запись с валидным 920/200^a (пройдёт ФЛК),
    # заглавие реформатируется из источника (v200^a читается на SOURCE-записи).
    job = ("0\nNEWMFN\n'*'\n"
           "ADD\n920\n\n'PAZK'\n\n"
           "ADD\n101\n\n'rus'\n\n"
           "ADD\n200^a\n1\nv200^a\n\n"
           "END\n")
    status, payload = _post(api, headers, {
        'db': DB, 'mfns': [src_mfn], 'gbl': job, 'mode': 'apply'})
    check('NEWMFN 200 ok', status == 200 and payload['ok'] is True)
    data = payload['data']
    check('NEWMFN emitted exactly 1 new record',
          data['createdCount'] == 1 and len(data['emitted']) == 1)
    new_mfn = data['emitted'][0]['mfn']
    check('NEWMFN store count grew by 1', api.catalog.count(DB) == count_before + 1)
    made = api.catalog.get(DB, new_mfn)
    check('NEWMFN persisted record is readable', made is not None)
    check('NEWMFN reformatted 200^a from SOURCE',
          _sub(made, '200', 'a') == ['Книга-источник'])
    check('NEWMFN 920 literal', _whole(made, '920') == ['PAZK'])

    # preview той же работы НЕ создаёт записи (хост-emit подавлен).
    count_now = api.catalog.count(DB)
    st2, pl2 = _post(api, headers, {
        'db': DB, 'mfns': [src_mfn], 'gbl': job, 'mode': 'preview'})
    check('NEWMFN preview reports would-create',
          st2 == 200 and pl2['data']['createdCount'] == 1)
    check('NEWMFN preview did NOT persist',
          api.catalog.count(DB) == count_now)


# --------------------------------------------------------------------------- #
# 5. Guard: гость/читатель без cat.gbl → 403; нет сессии → 401.
# --------------------------------------------------------------------------- #
def guard_checks():
    print('-- guard (cat.gbl обязателен)')
    api, _ = _api()
    mfn = api.catalog.save(DB, _good_book())['mfn']
    job = "0\nREP\n920\n*\n'SPEC'\n\n"
    body = {'db': DB, 'mfns': [mfn], 'gbl': job, 'mode': 'apply'}

    st_g, pl_g = _post(api, _guest(api), body)
    check('guest -> 403', st_g == 403 and pl_g['ok'] is False)
    st_r, pl_r = _post(api, _reader(api), body)
    check('reader -> 403', st_r == 403 and pl_r['ok'] is False)
    st_n, pl_n = _post(api, {}, body)
    check('no session -> 401', st_n == 401 and pl_n['ok'] is False)
    # запись осталась нетронутой после всех отказов.
    check('denied calls did not change the record',
          _whole(api.catalog.get(DB, mfn), '920') == ['PAZK'])

    # сотрудник С грантом проходит (sanity на тех же данных).
    st_ok, pl_ok = _post(api, _staff(api), body)
    check('staff with cat.gbl -> 200', st_ok == 200 and pl_ok['ok'] is True)


# --------------------------------------------------------------------------- #
# 5b. Ошибки разбора/выборки изолируются (пачка не падает).
# --------------------------------------------------------------------------- #
def robustness_checks():
    print('-- robustness (ParseError 400, missing MFN не валит пачку)')
    api, _ = _api()
    headers = _staff(api)
    mfn = api.catalog.save(DB, _good_book())['mfn']

    # битое задание -> 400, стор не тронут.
    st_b, pl_b = _post(api, headers, {
        'db': DB, 'mfns': [mfn], 'gbl': "0\nFOO\n", 'mode': 'apply'})
    check('bad gbl -> 400', st_b == 400 and pl_b['ok'] is False)

    # отсутствующий MFN помечается missing, валидный обрабатывается.
    job = "0\nREP\n920\n*\n'SPEC'\n\n"
    st_m, pl_m = _post(api, headers, {
        'db': DB, 'mfns': [mfn, 999999], 'gbl': job, 'mode': 'apply'})
    check('missing MFN isolated, batch survives',
          st_m == 200 and pl_m['data']['processed'] == 2
          and any(r['status'] == 'missing' for r in pl_m['data']['records'])
          and any(r['status'] == 'changed' for r in pl_m['data']['records']))


# --------------------------------------------------------------------------- #
# Хелперы чтения значений из tag-keyed записи (форма gbl/catalog).
# --------------------------------------------------------------------------- #
def _instances(rec, tag):
    raw = rec.get(tag) if rec else None
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _whole(rec, tag):
    out = []
    for inst in _instances(rec, tag):
        if isinstance(inst, dict):
            v = inst.get('')
            if v:
                out.append(v)
        elif inst:
            out.append(str(inst))
    return out


def _sub(rec, tag, sub):
    out = []
    for inst in _instances(rec, tag):
        if isinstance(inst, dict):
            v = inst.get(sub) or inst.get(sub.upper()) or inst.get(sub.lower())
            if v:
                out.append(v)
    return out


def main():
    preview_checks()
    apply_rep_checks()
    apply_del_checks()
    correc_checks()
    newmfn_checks()
    guard_checks()
    robustness_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
