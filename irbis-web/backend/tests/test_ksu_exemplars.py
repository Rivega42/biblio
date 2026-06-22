#!/usr/bin/env python3
"""КСУ ↔ экземпляры — тесты рёбер 5.1 / 5.3 (INTEGRATION_MAP кластер 5).

Сценарные тесты учётной связи «партия поступления ↔ экземпляр» в
:mod:`access.acquisition`:

  * [5.1] №КСУ поступления (88^U) проставляется в экземпляры (910^U, индекс
    ``KSU=``): :meth:`AcquisitionEngine.link_ksu_to_exemplars` — через опц.
    catalog-handle (без правки ``catalog.py``); поиск экз. партии по №КСУ —
    :meth:`find_exemplars_by_ksu` (точки доступа ``KSU=``/``NKSUK=``);
  * [5.3] базовое авто-распределение партии (Мастер «Пополнение записи КСУ»):
    :meth:`distribute_ksu_batch` — сумматоры (наименования/экземпляры) +
    наблюдаемые грани (тип/язык 45, УДК 48, ББК 49, раздел 151, МХР 148);
    нераскрытые членения (#CMPL-05) — в ``todo``, не домысливаются;
  * back-compat: без catalog-handle модуль автономен (связь только в ledger'е);
  * PG-паритет: связь/поиск/распределение опираются на собственный sqlite-ledger
    (``acq_inventory``) + чистую логику над dict'ами — backend-независимы.

Запуск в стиле дома (как ``test_tocat.py``)::

    py -3.12 tests/test_ksu_exemplars.py  -> ok ... + "N passed, M failed" + код

FakeCatalog: самодостаточный каталог-handle (контракт 5.1 — find_exemplar / get /
save / iter_records). DB-сервер не нужен.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.acquisition import (  # noqa: E402
    AcquisitionStore, AcquisitionEngine, AcquisitionError,
    EXEMPLAR_FREE, EXEMPLAR_KSU_SUB, KSU_DISTRIBUTION_FIELDS,
)

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
# FakeCatalog — каталог-handle, реализующий контракт, который дёргают 5.1/5.3:
# find_exemplar / get / save / iter_records. Хранит записи в dict, выдаёт
# последовательный mfn. Это ровно поверхность handle (без зависимости от
# access/catalog.py — его держит сиблинг, INTEGRATION_MAP).
# --------------------------------------------------------------------------- #
class FakeCatalog:
    def __init__(self):
        self._db = {}        # db -> {mfn -> record}
        self._next = {}      # db -> next mfn

    def _store(self, db):
        return self._db.setdefault(db, {})

    def save(self, db, record, mfn=None):
        store = self._store(db)
        if mfn is None:
            mfn = self._next.get(db, 1)
            self._next[db] = mfn + 1
        if not record.get('920'):                 # 920 FLK-mandatory (как реальный)
            return {'saved': False, 'mfn': None, 'violations': ['no 920']}
        store[mfn] = copy.deepcopy(record)
        return {'saved': True, 'mfn': mfn, 'violations': []}

    def get(self, db, mfn):
        rec = self._store(db).get(mfn)
        return copy.deepcopy(rec) if rec is not None else None

    def search(self, db, expr, limit=20):
        # понимаем только T=<term>; matched по 200^a (для receive-driven ToCat
        # new-vs-existing резолва).
        term = expr.split('=', 1)[1].strip().casefold() if '=' in expr \
            else expr.strip().casefold()
        items = []
        for mfn, rec in sorted(self._store(db).items()):
            insts = rec.get('200')
            if not isinstance(insts, list):
                insts = [insts] if insts else []
            t = ''
            for inst in insts:
                if isinstance(inst, dict) and inst.get('a'):
                    t = str(inst['a']).strip().casefold()
                    break
            if t == term:
                items.append({'mfn': mfn})
        return {'items': items[:limit]}

    def find_exemplar(self, db, item):
        for mfn, rec in sorted(self._store(db).items()):
            insts = rec.get('910')
            if insts is None:
                continue
            if not isinstance(insts, list):
                insts = [insts]
            for i, inst in enumerate(insts):
                if isinstance(inst, dict) and \
                        str(inst.get('b') or inst.get('B') or '') == str(item):
                    return (mfn, i, inst)
        return None

    def iter_records(self, db):
        return [(mfn, copy.deepcopy(rec))
                for mfn, rec in sorted(self._store(db).items())]


class FakeCatalogNoIter(FakeCatalog):
    """Каталог-handle БЕЗ iter_records — проверяет фолбэк скана через find_exemplar."""
    iter_records = None
    all_records = None


# --------------------------------------------------------------------------- #
# Фабрики.
# --------------------------------------------------------------------------- #
def fresh_engine(catalog=None):
    return AcquisitionEngine(store=AcquisitionStore(':memory:'), catalog=catalog)


def seed_catalog_book(cat, db='IBIS', title='Базы данных', lang='rus',
                      udk='004.6', bbk='З973', invs=(('INV-1', 'ЧЗ'),
                                                     ('INV-2', 'АБ'))):
    """Засеять запись книги в каталог с экземплярами (910^b/^d), без 910^U."""
    rec = {'920': 'PAZK', '200': [{'a': title}], '101': lang,
           '675': [{'a': udk}], '621': [{'a': bbk}], '910': []}
    for inv, mhr in invs:
        rec['910'].append({'a': EXEMPLAR_FREE, 'b': inv, 'd': mhr})
    res = cat.save(db, rec)
    return res['mfn']


def _received_engine(eng, ksu='KSU-2026-1', copies=2,
                     invs=('INV-1', 'INV-2')):
    """Принять партию в ledger (receive) — даёт инв.№ в acq_inventory."""
    o = eng.create_order('Базы данных', author='Дейт К.', copies=copies, price=100)
    eng.receive(o['id'], ksu, copies, inv_numbers=list(invs))
    return o


# --------------------------------------------------------------------------- #
# 5.1 — №КСУ поступления (88^U) ↔ экземпляры (910^U). Ledger-сторона.
# --------------------------------------------------------------------------- #
def link_ledger_checks():
    """[5.1] Связь КСУ↔экз в собственном ledger'е (без каталога)."""
    eng = fresh_engine()
    _received_engine(eng, ksu='KSU-A', invs=('INV-1', 'INV-2'))
    # инв.№ уже в ledger'е с этим КСУ (receive проставил); re-link не задваивает.
    res = eng.link_ksu_to_exemplars('KSU-A', ['INV-1', 'INV-2'])
    check('5.1 ledger: оба инв.№ связаны', res['ledger'] == ['INV-1', 'INV-2'])
    check('5.1 ledger: ничего не зарегистрировано заново (уже в receive)',
          res['registered'] == [])
    check('5.1 ledger: без каталога catalog[] пуст', res['catalog'] == [])

    # новый инв.№ под другим КСУ — регистрируется в ledger'е «бесхозной» строкой.
    res2 = eng.link_ksu_to_exemplars('KSU-B', ['INV-9'])
    check('5.1 ledger: новый инв.№ зарегистрирован', res2['registered'] == ['INV-9'])
    check('5.1 ledger: новый инв.№ в ledger', res2['ledger'] == ['INV-9'])

    # перепривязка существующего инв.№ на ДРУГОЙ КСУ — обновляет ksu_no (re-link).
    res3 = eng.link_ksu_to_exemplars('KSU-C', ['INV-1'])
    check('5.1 ledger: re-link не регистрирует заново', res3['registered'] == [])
    found_c = eng.find_exemplars_by_ksu('KSU-C')
    found_a = eng.find_exemplars_by_ksu('KSU-A')
    check('5.1 ledger: re-link перенёс инв.№ на новый КСУ',
          found_c['inv_numbers'] == ['INV-1'] and 'INV-1' not in found_a['inv_numbers'])


def link_requires_ksu_checks():
    """[5.1] Валидация аргументов link/find."""
    eng = fresh_engine()
    for bad in ('', '   ', None):
        try:
            eng.link_ksu_to_exemplars(bad, ['INV-1'])
            check('5.1 пустой №КСУ -> ошибка (%r)' % (bad,), False)
        except AcquisitionError:
            check('5.1 пустой №КСУ -> ошибка (%r)' % (bad,), True)
    try:
        eng.find_exemplars_by_ksu('')
        check('5.1 find: пустой №КСУ -> ошибка', False)
    except AcquisitionError:
        check('5.1 find: пустой №КСУ -> ошибка', True)
    # пустой список инв.№ — допустимо (no-op), не падает.
    res = eng.link_ksu_to_exemplars('KSU-Z', [])
    check('5.1 пустой список инв.№ -> no-op', res['ledger'] == [])


# --------------------------------------------------------------------------- #
# 5.1 — каталог-сторона: 910^U проставляется в записи ЭК + поиск по №КСУ.
# --------------------------------------------------------------------------- #
def link_catalog_checks():
    """[5.1] 910^U проставляется в запись каталога через handle; поиск по №КСУ."""
    cat = FakeCatalog()
    mfn = seed_catalog_book(cat)
    eng = fresh_engine(catalog=cat)

    res = eng.link_ksu_to_exemplars('KSU-2026-1',
                                    ['INV-1', 'INV-2', 'INV-NONE'])
    check('5.1 каталог: оба известных экз. размечены 910^U',
          res['catalog'] == ['INV-1', 'INV-2'])
    check('5.1 каталог: неизвестный каталогу инв.№ -> missing',
          res['missing'] == ['INV-NONE'])

    rec = cat.get('IBIS', mfn)
    ksu_vals = [str(i.get(EXEMPLAR_KSU_SUB) or '') for i in rec['910']]
    check('5.1 каталог: 910^U == №КСУ на обоих экз.',
          ksu_vals == ['KSU-2026-1', 'KSU-2026-1'])

    # поиск экз. партии по №КСУ: объединение ledger + каталог.
    found = eng.find_exemplars_by_ksu('KSU-2026-1')
    check('5.1 поиск по №КСУ: ledger содержит все 3 инв.№',
          set(found['inv_numbers']) == {'INV-1', 'INV-2', 'INV-NONE'})
    cat_invs = {h['inv_no'] for h in found['catalog']}
    check('5.1 поиск по №КСУ: каталог-хиты только реальные экз. ЭК',
          cat_invs == {'INV-1', 'INV-2'})
    check('5.1 поиск по №КСУ: каталог-хиты несут mfn',
          all(h.get('mfn') == mfn for h in found['catalog']))


def link_catalog_idempotent_checks():
    """[5.1] Повторная разметка тем же №КСУ — идемпотентна (910^U не задваивается)."""
    cat = FakeCatalog()
    mfn = seed_catalog_book(cat)
    eng = fresh_engine(catalog=cat)
    eng.link_ksu_to_exemplars('KSU-1', ['INV-1', 'INV-2'])
    rec1 = cat.get('IBIS', mfn)
    eng.link_ksu_to_exemplars('KSU-1', ['INV-1', 'INV-2'])   # повтор
    rec2 = cat.get('IBIS', mfn)
    check('5.1 идемпотентность: запись не изменилась при повторе', rec1 == rec2)
    check('5.1 идемпотентность: ровно по одному 910^U на экз.',
          all(isinstance(i.get(EXEMPLAR_KSU_SUB), str) for i in rec2['910']))


def link_catalog_no_iter_checks():
    """[5.1] Поиск по №КСУ работает и без iter_records (фолбэк через find_exemplar)."""
    cat = FakeCatalogNoIter()
    seed_catalog_book(cat)
    eng = fresh_engine(catalog=cat)
    eng.link_ksu_to_exemplars('KSU-NI', ['INV-1', 'INV-2'])
    found = eng.find_exemplars_by_ksu('KSU-NI')
    # ledger несёт оба; каталог-хиты собираются фолбэком (сверкой ledger↔ЭК).
    check('5.1 без iter: ledger полон', set(found['ledger']) == {'INV-1', 'INV-2'})
    check('5.1 без iter: каталог-хиты собраны фолбэком',
          {h['inv_no'] for h in found['catalog']} == {'INV-1', 'INV-2'})


def link_catalog_backcompat_checks():
    """[5.1] back-compat: тот же вызов без handle проставляет связь только в ledger."""
    eng = fresh_engine(catalog=None)
    res = eng.link_ksu_to_exemplars('KSU-BC', ['INV-1', 'INV-2'])
    check('5.1 back-compat: ledger размечен', res['ledger'] == ['INV-1', 'INV-2'])
    check('5.1 back-compat: catalog[] пуст без handle', res['catalog'] == [])
    check('5.1 back-compat: missing[] пуст без handle', res['missing'] == [])
    found = eng.find_exemplars_by_ksu('KSU-BC')
    check('5.1 back-compat: поиск по №КСУ из ledger',
          found['inv_numbers'] == ['INV-1', 'INV-2'] and found['catalog'] == [])


# --------------------------------------------------------------------------- #
# 5.3 — базовое авто-распределение партии (Мастер «Пополнение записи КСУ»).
# --------------------------------------------------------------------------- #
def distribute_catalog_checks():
    """[5.3] Авто-распределение по граням с записей/экз. каталога."""
    cat = FakeCatalog()
    # две записи: книга (rus, 004.6/З973) на 2 экз. + книга (eng, 51/В1) на 1 экз.
    seed_catalog_book(cat, title='Базы данных', lang='rus', udk='004.6',
                      bbk='З973', invs=(('INV-1', 'ЧЗ'), ('INV-2', 'АБ')))
    seed_catalog_book(cat, title='Algorithms', lang='eng', udk='51',
                      bbk='В1', invs=(('INV-3', 'ЧЗ'),))
    eng = fresh_engine(catalog=cat)
    eng.link_ksu_to_exemplars('KSU-D', ['INV-1', 'INV-2', 'INV-3'])

    dist = eng.distribute_ksu_batch('KSU-D')
    check('5.3 сумматор: число экземпляров (88^F)', dist['copies'] == 3)
    check('5.3 сумматор: число наименований 17 = разные записи ЭК',
          dist['17'] == 2)
    check('5.3 грань 45 (тип/язык): rus×2, eng×1',
          dist['by_type'] == {'rus': 2, 'eng': 1})
    check('5.3 грань 48 (УДК): 004.6×2, 51×1',
          dist['by_udk'] == {'004.6': 2, '51': 1})
    check('5.3 грань 49 (ББК): З973×2, В1×1',
          dist['by_bbk'] == {'З973': 2, 'В1': 1})
    check('5.3 грань 148 (МХР/фонды): ЧЗ×2, АБ×1',
          dist['by_mhr'] == {'ЧЗ': 2, 'АБ': 1})
    check('5.3 раздел 151 ≈ ББК (наблюдаемая грань)',
          dist['by_section'] == {'З973': 2, 'В1': 1})
    # под-№-полей зеркалят грани.
    check('5.3 fields[45] == by_type', dist['fields']['45'] == dist['by_type'])
    check('5.3 fields[48] == by_udk', dist['fields']['48'] == dist['by_udk'])


def distribute_explicit_exemplars_checks():
    """[5.3] Распределение по ЯВНО переданным экземплярам (чистая логика)."""
    eng = fresh_engine()
    rows = [
        {'b': 'I-1', '45': 'rus', '48': '004', '49': 'З9', '151': 'ИТ', 'd': 'ЧЗ'},
        {'b': 'I-2', 'lang': 'rus', 'udk': '004', 'bbk': 'З9', 'mhr': 'АБ'},
        {'b': 'I-3', 'type': 'eng', 'udk': '51', 'bbk': 'В1', 'section': 'МАТ'},
        {'b': 'I-4'},                                   # без граней — только счёт
    ]
    dist = eng.distribute_ksu_batch('KSU-X', exemplars=rows)
    check('5.3 явн.: copies = 4', dist['copies'] == 4)
    check('5.3 явн.: by_type rus×2/eng×1 (alias lang/type)',
          dist['by_type'] == {'rus': 2, 'eng': 1})
    check('5.3 явн.: by_udk алиасы 48/udk', dist['by_udk'] == {'004': 2, '51': 1})
    check('5.3 явн.: by_section алиасы 151/section',
          dist['by_section'] == {'ИТ': 1, 'МАТ': 1})
    check('5.3 явн.: by_mhr алиасы d/mhr', dist['by_mhr'] == {'ЧЗ': 1, 'АБ': 1})
    check('5.3 явн.: экз. без граней не попадает в bucket\'ы',
          sum(dist['by_type'].values()) == 3)


def distribute_todo_checks():
    """[5.3] Нераскрытые в recon членения (#CMPL-05) — в todo, НЕ заполнены."""
    eng = fresh_engine()
    dist = eng.distribute_ksu_batch('KSU-T', exemplars=[{'b': 'I-1'}])
    # #CMPL-05: членение наименований 17->18/19, направления 44/744, печатные
    # 145-150, периодика 155, ВУЗ 158/248/249 — во внешнем Мастере, не домысливаем.
    for tag in ('18', '19', '44', '744', '145', '155', '158', '248', '249'):
        check('5.3 TODO #CMPL-05: поле %s в todo (не выдумано)' % tag,
              tag in dist['todo'])
    # результат не содержит самовыдуманных значений для todo-полей.
    check('5.3 TODO: todo-поля отсутствуют среди заполненных fields',
          not (set(dist['todo']) & set(dist['fields'].keys())))
    # карта полей распределения (для документации/UI) согласована с DB_ACQUISITION.
    check('5.3 карта KSU_DISTRIBUTION_FIELDS несёт 17/45/48/49/151',
          all(t in KSU_DISTRIBUTION_FIELDS for t in ('17', '45', '48', '49', '151')))


def distribute_backcompat_checks():
    """[5.3] back-compat: без каталога — сумматоры по ledger'у, грани пусты."""
    eng = fresh_engine(catalog=None)
    _received_engine(eng, ksu='KSU-LB', copies=2, invs=('INV-1', 'INV-2'))
    dist = eng.distribute_ksu_batch('KSU-LB')
    check('5.3 back-compat: copies из ledger', dist['copies'] == 2)
    check('5.3 back-compat: наименований базово 1 на партию', dist['17'] == 1)
    check('5.3 back-compat: грани пусты (ledger граней не несёт)',
          dist['by_type'] == {} and dist['by_udk'] == {} and dist['by_bbk'] == {})
    # пустая партия -> нулевые сумматоры.
    empty = eng.distribute_ksu_batch('KSU-EMPTY')
    check('5.3 back-compat: пустая партия -> copies 0 / наименований 0',
          empty['copies'] == 0 and empty['17'] == 0)


def distribute_requires_ksu_checks():
    """[5.3] Валидация: пустой №КСУ -> ошибка."""
    eng = fresh_engine()
    try:
        eng.distribute_ksu_batch('   ')
        check('5.3 пустой №КСУ -> ошибка', False)
    except AcquisitionError:
        check('5.3 пустой №КСУ -> ошибка', True)


# --------------------------------------------------------------------------- #
# Интеграция: receive -> link -> find -> distribute (полный поток партии).
# --------------------------------------------------------------------------- #
def end_to_end_checks():
    """receive (ledger) + ToCat в каталог + link 910^U + поиск + распределение."""
    cat = FakeCatalog()
    eng = fresh_engine(catalog=cat)
    # приём 2 экз. с ToCat (receive создаёт запись ЭК с 910^U из receive-driven ToCat).
    o = eng.create_order('Сети', author='Таненбаум Э.', copies=2, price=200)
    r = eng.receive(o['id'], 'KSU-E2E', 2, inv_numbers=['E-1', 'E-2'])
    check('e2e: ToCat создал запись каталога', r['catalog_mfn'] is not None)
    # независимый link (повторно проставляет 910^U — идемпотентно).
    link = eng.link_ksu_to_exemplars('KSU-E2E', ['E-1', 'E-2'])
    check('e2e: оба экз. размечены в каталоге', link['catalog'] == ['E-1', 'E-2'])
    # поиск экз. партии.
    found = eng.find_exemplars_by_ksu('KSU-E2E')
    check('e2e: поиск по №КСУ нашёл оба экз.',
          set(found['inv_numbers']) == {'E-1', 'E-2'})
    # распределение (наименований 1, экз. 2).
    dist = eng.distribute_ksu_batch('KSU-E2E')
    check('e2e: распределение copies=2, наименований=1',
          dist['copies'] == 2 and dist['17'] == 1)


def main():
    for fn in sorted(name for name in globals() if name.endswith('_checks')):
        globals()[fn]()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
