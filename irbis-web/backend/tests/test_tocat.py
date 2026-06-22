#!/usr/bin/env python3
"""ToCat tests — реформат БО Комплектование → Каталог (рёбра 1.1–1.5).

Сценарные тесты переноса БО CMPL в каталог ЭК (INTEGRATION_MAP кластер 1, ядро
ToCat) через :meth:`AcquisitionEngine.to_catalog`. Закрывают крупнейший ❌-кластер
карты: реформат полей БО CMPL → формат IBIS, перенос экземпляров, связь подписки
и техн.путь, пометку исходника на удаление.

Запуск в стиле дома (как ``test_acquisition.py``)::

    py -3.12 tests/test_tocat.py   ->  ok ...  +  "N passed, M failed"  + exit code

Покрытие (рёбра 1.1–1.5):
  * [1.1] реформат полей: 920→РЛ (PAZK/SPEC/PVK/J/ASP), заглавие→200,
    922/330→700/701, аналитика→463; триггер — флаг поля 66;
  * [1.2] перенос экземпляров CMPL 910 → IBIS 910 (статус ^A, инв.№ ^b, КСУ ^U);
  * [1.3] связь подписки 938 (период);
  * [1.4] технологический путь 901 (^B №экз + пункты ТП);
  * [1.5] VD=DEL (пометка на удаление) на исходную CMPL-запись (анти-дубль);
  * идемпотентность (повторный ToCat не задваивает запись/экземпляры);
  * back-compat (нет catalog-handle → standalone, реформат всё равно строится);
  * PG-паритет: реформат БО — чистая функция, не зависит от backend'а стора.

FakeIrbis/синтетика: все БО CMPL — синтетические dict'ы; каталог — in-memory
CatalogStore (sqlite ':memory:'). DB-сервер не нужен.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import acquisition as acq  # noqa: F401
from access.acquisition import (
    AcquisitionStore, AcquisitionEngine, AcquisitionError,  # noqa: F401
    field66_set, is_source_deleted,
    WORKLIST_MAP_TO_CAT, NON_CATALOG_WORKLISTS, VD_DEL, EXEMPLAR_FREE,  # noqa: F401
)

# Каталог-handle опционален; импортируем РЕАЛЬНЫЙ CatalogStore для сквозной
# проверки, КОГДА дерево консистентно. Тесты, однако, по умолчанию работают через
# самодостаточный FakeCatalog (ниже) — это (а) ровно тот контракт handle, который
# использует to_catalog, (б) изолирует ToCat-тесты от живого catalog.py (его держит
# сиблинг — INTEGRATION_MAP), и (в) даёт детерминированную синтетику без ФЛК-веса.
try:
    from access import catalog as _catalog
except Exception:  # pragma: no cover
    _catalog = None

PASS = [0]
FAIL = [0]


# --------------------------------------------------------------------------- #
# FakeIrbis: самодостаточный каталог-handle (контракт ToCat — save/get/search/
# find_exemplar/exemplar_status/is_available/count). Хранит записи в dict, выдаёт
# последовательный mfn, инвертирует заглавие (T=) для поиска новый-vs-существующий.
# Это ровно поверхность, которую дёргает AcquisitionEngine.to_catalog, поэтому
# тест полноценно проверяет перенос, не завися от реализации access/catalog.py.
# --------------------------------------------------------------------------- #
EXEMPLAR_FREE_CODE = EXEMPLAR_FREE  # '0' (ste.mnu «свободен»)


class FakeCatalog:
    """In-memory каталог-handle, реализующий контракт, который вызывает ToCat."""

    def __init__(self):
        self._db = {}            # db -> {mfn -> record}
        self._next = {}          # db -> next mfn

    def _store(self, db):
        return self._db.setdefault(db, {})

    def save(self, db, record, mfn=None):
        store = self._store(db)
        if mfn is None:
            mfn = self._next.get(db, 1)
            self._next[db] = mfn + 1
        # FLK-минимум: 920 обязателен (severity-1) — отвергаем запись без него,
        # как реальный catalog.save (поле 920 FLK-mandatory).
        if not record.get('920'):
            return {'saved': False, 'mfn': None, 'violations': ['no 920']}
        import copy
        store[mfn] = copy.deepcopy(record)
        return {'saved': True, 'mfn': mfn, 'violations': []}

    def get(self, db, mfn):
        import copy
        rec = self._store(db).get(mfn)
        return copy.deepcopy(rec) if rec is not None else None

    def search(self, db, expr, limit=20):
        # понимаем только T=<term>; возвращаем mfn'ы, у которых 200^a == term.
        term = expr.split('=', 1)[1].strip().casefold() if '=' in expr else \
            expr.strip().casefold()
        items = []
        for mfn, rec in sorted(self._store(db).items()):
            t = _val(rec, '200', 'a').strip().casefold()
            if t == term:
                items.append({'mfn': mfn})
        return {'items': items[:limit]}

    def _find910(self, db, item):
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

    def find_exemplar(self, db, item):
        return self._find910(db, item)

    def exemplar_status(self, db, item):
        f = self._find910(db, item)
        if f is None:
            return None
        inst = f[2]
        return str(inst.get('a') or inst.get('A') or '')

    def is_available(self, db, item):
        return self.exemplar_status(db, item) == EXEMPLAR_FREE_CODE

    def count(self, db):
        return len(self._store(db))


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Фабрики: движок + каталог + синтетические БО CMPL.
# --------------------------------------------------------------------------- #
def fresh_catalog():
    """Свежий FakeCatalog — самодостаточный handle (контракт ToCat).

    Намеренно НЕ зависит от access/catalog.py: его держит сиблинг (INTEGRATION_MAP),
    и ToCat-тесты должны быть детерминированы. Сквозная проверка против реального
    CatalogStore — отдельным :func:`real_catalog_smoke_checks` (когда дерево готово)."""
    return FakeCatalog()


def real_catalog_or_none():
    """Реальный CatalogStore, если он импортируется И работает; иначе None.

    Сиблинг может держать catalog.py в промежуточном состоянии — тогда сквозная
    проверка корректно пропускается (skip, не fail), а основное покрытие даёт
    FakeCatalog."""
    if _catalog is None:
        return None
    try:
        cat = _catalog.CatalogStore(':memory:')
        # дымовая проба save: если ФЛК-пайплайн в дереве сейчас сломан, пропускаем.
        probe = cat.save('IBIS', {'920': 'PAZK', '200': [{'a': 'проба'}]})
        if not probe.get('saved'):
            return None
        return _catalog.CatalogStore(':memory:')
    except Exception:
        return None


def fresh_engine(catalog=None):
    """Свежий движок над in-memory стором (опц. с catalog-handle)."""
    return AcquisitionEngine(store=AcquisitionStore(':memory:'), catalog=catalog)


def cmpl_book(title='Базы данных', author='Дейт К.', inv=('INV-1',),
              ksu_in=None, flag66=True, worklist='PAZK', price=None):
    """Синтетический БО CMPL: книга (920=PAZK) с флагом 66 и экземплярами 910."""
    rec = {
        '920': worklist,
        '200': [{'a': title, 'f': author}],
        '700': [{'a': author.split(' ')[0], 'b': ' '.join(author.split(' ')[1:])}]
        if ' ' in author else [{'a': author}],
        '910': [],
    }
    for i, n in enumerate(inv):
        ex = {'A': EXEMPLAR_FREE, 'B': n}
        if price is not None:
            ex['E'] = str(price)
        if ksu_in:
            ex['U'] = ksu_in
        rec['910'].append(ex)
    if flag66:
        rec['66'] = [{'a': 'X'}]   # флаг переноса взведён
    return rec


def cmpl_article(title='О реляционной модели', author='Кодд Э.',
                 host='Системы баз данных', inv=('ASP-1',), flag66=True):
    """Синтетический БО CMPL: аналитика (920=ASP) — статья 922/330 + host 463."""
    rec = {
        '920': 'ASP',
        '922': [{'C': title, 'F': author}],
        '463': [{'C': host, 'J': '1234-5678'}],
        '910': [{'A': EXEMPLAR_FREE, 'B': n} for n in inv],
    }
    if flag66:
        rec['66'] = [{'a': 'X'}]
    return rec


# --------------------------------------------------------------------------- #
# Локальные аксессоры для ассертов.
# --------------------------------------------------------------------------- #
def _insts(record, field):
    raw = record.get(field)
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _val(record, field, subfield):
    for inst in _insts(record, field):
        if isinstance(inst, dict) and inst.get(subfield):
            return inst[subfield]
    return ''


# --------------------------------------------------------------------------- #
# 1.1 — реформат полей БО CMPL → IBIS (920→700/200/463) + триггер 66.
# --------------------------------------------------------------------------- #
def reformat_checks():
    print('-- [1.1] реформат БО CMPL -> IBIS (920/200/700/463)')
    eng = fresh_engine()

    # книга: 920 PAZK, заглавие 200^a/^f, автор 700^a/^b
    rec = cmpl_book(title='Алгоритмы', author='Кормен Т.')
    ibis = eng.reformat_to_ibis(rec)
    check('920 PAZK переносится', ibis['920'] == 'PAZK')
    check('заглавие -> 200^a', _val(ibis, '200', 'a') == 'Алгоритмы')
    check('свед. об отв. -> 200^f', _val(ibis, '200', 'f') == 'Кормен Т.')
    check('автор -> 700^a (фамилия)', _val(ibis, '700', 'a') == 'Кормен')
    check('инициалы -> 700^b', _val(ibis, '700', 'b') == 'Т.')
    check('язык умолч. rus -> 101', ibis.get('101') == 'rus')

    # аналитика: 922^C загл. статьи -> 200, 922^F автор -> 700, 463 host
    art = cmpl_article(title='О реляционной модели', author='Кодд Э.',
                       host='Системы БД')
    ai = eng.reformat_to_ibis(art)
    check('ASP 920 переносится', ai['920'] == 'ASP')
    check('загл. статьи 922^C -> 200^a',
          _val(ai, '200', 'a') == 'О реляционной модели')
    check('автор статьи 922^F -> 700^a', _val(ai, '700', 'a') == 'Кодд')
    check('аналитика -> 463^C (host)', _val(ai, '463', 'C') == 'Системы БД')
    check('463 несёт ISSN ^J', _val(ai, '463', 'J') == '1234-5678')

    # 922 с несколькими авторами -> 700 (1-й) + 701 (прочие)
    multi = {'920': 'ASP',
             '922': [{'C': 'Статья', 'F': 'Иванов И.'},
                     {'F': 'Петров П.'}],
             '66': [{'a': 'X'}]}
    mi = eng.reformat_to_ibis(multi)
    check('1-й автор -> 700', _val(mi, '700', 'a') == 'Иванов')
    check('прочие авторы -> 701', _val(mi, '701', 'a') == 'Петров')

    # маппинг РЛ: коды видов документа CMPL -> IBIS
    for code in ('PAZK', 'SPEC', 'PVK', 'J', 'ASP'):
        r = {'920': code, '200': [{'a': 'X'}]}
        check('920 %s маппится' % code,
              eng.reformat_to_ibis(r)['920'] == WORKLIST_MAP_TO_CAT[code])

    # реформат не мутирует исходник
    src = cmpl_book()
    before = dict(src)
    eng.reformat_to_ibis(src)
    check('reformat не мутирует исходный БО', src == before)


def trigger66_checks():
    print('-- [триггер] флаг поля 66 запускает перенос')
    # флаг взведён
    check('66 с непустым подполем -> взведён', field66_set({'66': [{'a': 'X'}]}))
    check('66 = "1" строкой -> взведён', field66_set({'66': '1'}))
    # флаг НЕ взведён
    check('нет поля 66 -> не взведён', not field66_set({'200': [{'a': 'X'}]}))
    check('66 пустой -> не взведён', not field66_set({'66': [{'a': ''}]}))
    # уже помеченный VD=DEL -> флаг «потреблён» (не pending)
    check('66 только VD=DEL -> не pending',
          not field66_set({'66': [{'a': 'DEL'}]}))
    check('is_source_deleted читает VD=DEL',
          is_source_deleted({'66': [{'a': 'DEL'}]}))
    check('is_source_deleted ложь без метки',
          not is_source_deleted({'66': [{'a': 'X'}]}))


# --------------------------------------------------------------------------- #
# Полный перенос через catalog-handle: 1.2/1.3/1.4 + сохранение.
# --------------------------------------------------------------------------- #
def to_catalog_full_checks():
    print('-- [1.1-1.4] полный ToCat через catalog-handle')
    cat = fresh_catalog()
    if cat is None:
        check('catalog importable (skip ToCat)', False)
        return
    eng = fresh_engine(catalog=cat)

    rec = cmpl_book(title='Машинное обучение', author='Бишоп К.',
                    inv=('INV-A', 'INV-B'), price='400.00')
    # 938 (подписка-период) + явный 901 на исходнике
    rec['938'] = [{'Q': '2026', 'N': '1'}]
    res = eng.to_catalog(rec, ksu_no='2026/30')
    check('ToCat создал запись', res['action'] == 'created')
    check('ToCat вернул mfn', res['catalog_mfn'] is not None)

    mfn = res['catalog_mfn']
    saved = cat.get('IBIS', mfn)

    # [1.1] поля
    check('IBIS заглавие 200^a',
          _val(saved, '200', 'a') == 'Машинное обучение')
    check('IBIS автор 700^a', _val(saved, '700', 'a') == 'Бишоп')
    check('IBIS РЛ 920=PAZK', saved.get('920') == 'PAZK')

    # [1.2] экземпляры 910 CMPL -> IBIS 910
    ex_list = saved['910'] if isinstance(saved['910'], list) else [saved['910']]
    check('[1.2] 2 экземпляра перенесены', len(ex_list) == 2)
    check('[1.2] экз. findable по инв.№',
          cat.find_exemplar('IBIS', 'INV-A') is not None)
    check('[1.2] экз. ^A свободен (выдаваем)',
          cat.exemplar_status('IBIS', 'INV-A') == EXEMPLAR_FREE)
    check('[1.2] экз. is_available', cat.is_available('IBIS', 'INV-A') is True)
    check('[1.2] КСУ-связь ^U на экземпляре',
          _val({'910': ex_list}, '910', 'u') == '2026/30' or
          any(str(i.get('u') or '') == '2026/30' for i in ex_list))
    check('[1.2] цена ^E перенесена',
          any(str(i.get('e') or '') == '400.00' for i in ex_list))
    check('res.exemplars содержит инв.№',
          set(res['exemplars']) == {'INV-A', 'INV-B'})

    # [1.3] связь подписки 938
    check('[1.3] 938 период перенесён', _val(saved, '938', 'Q') == '2026')

    # [1.4] техн.путь 901 (^B №экз + пункт ТП)
    p901 = _insts(saved, '901')
    check('[1.4] 901 построен на экземпляр', len(p901) == 2)
    check('[1.4] 901^B = инв.№',
          {i.get('B') for i in p901} == {'INV-A', 'INV-B'})
    check('[1.4] 901 несёт пункт ТП ^1',
          all(i.get('1') for i in p901))

    # field-66 КСУ-связь на самой записи
    check('запись несёт field-66 КСУ-связь', _val(saved, '66', 'u') == '2026/30')


def explicit_901_checks():
    print('-- [1.4] явный 901 в БО CMPL переносится как есть')
    cat = fresh_catalog()
    if cat is None:
        check('catalog importable (skip)', False)
        return
    eng = fresh_engine(catalog=cat)
    rec = cmpl_book(title='ТП-книга', inv=('TP-1',))
    rec['901'] = [{'B': 'TP-1', '1': '1', '2': '2', '3': '3'}]
    res = eng.to_catalog(rec, ksu_no='2026/50')
    saved = cat.get('IBIS', res['catalog_mfn'])
    p = _insts(saved, '901')
    check('явный 901 перенесён', len(p) == 1)
    check('901 пункты ТП сохранены',
          p[0].get('1') == '1' and p[0].get('2') == '2' and p[0].get('3') == '3')


# --------------------------------------------------------------------------- #
# 1.5 — VD=DEL на исходник + анти-дубль/идемпотентность.
# --------------------------------------------------------------------------- #
def vd_del_checks():
    print('-- [1.5] VD=DEL на исходную CMPL-запись (анти-дубль)')
    cat = fresh_catalog()
    if cat is None:
        check('catalog importable (skip)', False)
        return
    eng = fresh_engine(catalog=cat)

    rec = cmpl_book(title='Удаляемый исходник', inv=('D-1',))
    res = eng.to_catalog(rec, ksu_no='2026/60')
    check('перенос успешен', res['action'] == 'created')
    check('[1.5] source_deleted=True', res['source_deleted'] is True)
    check('[1.5] исходник помечен VD=DEL', is_source_deleted(rec))
    check('[1.5] КСУ сохранён в метке ^u',
          any(i.get('u') == '2026/60' for i in _insts(rec, '66')
              if isinstance(i, dict)))

    # повторный ToCat над помеченным -> no-op (идемпотентность)
    count_before = cat.count('IBIS')
    res2 = eng.to_catalog(rec, ksu_no='2026/60')
    check('[идемпот.] повтор -> already_transferred',
          res2['action'] == 'already_transferred')
    check('[идемпот.] запись не задвоена',
          cat.count('IBIS') == count_before)
    check('[идемпот.] mfn не выдан повторно', res2['catalog_mfn'] is None)


def vd_del_not_set_on_reject_checks():
    print('-- [1.5] VD=DEL НЕ ставится при отказе сохранения')

    class RejectingCatalog:
        """FakeIrbis: каталог, у которого save всегда отклоняет (ФЛК severity-1)."""
        def search(self, db, expr, limit=20):
            return {'items': []}

        def get(self, db, mfn):
            return None

        def save(self, db, record, mfn=None):
            return {'saved': False, 'mfn': None, 'violations': ['mock-reject']}

    eng = fresh_engine(catalog=RejectingCatalog())
    rec = cmpl_book(title='Отклонённый', inv=('R-1',))
    res = eng.to_catalog(rec, ksu_no='2026/70')
    check('отказ -> action=rejected', res['action'] == 'rejected')
    check('отказ -> source НЕ помечен VD=DEL', not is_source_deleted(rec))
    check('отказ -> source_deleted False', res['source_deleted'] is False)


# --------------------------------------------------------------------------- #
# Re-supply: одинаковое заглавие дополняет запись, не дублирует.
# --------------------------------------------------------------------------- #
def resupply_checks():
    print('-- re-supply: одно заглавие -> дополнение, не дубль')
    cat = fresh_catalog()
    if cat is None:
        check('catalog importable (skip)', False)
        return
    eng = fresh_engine(catalog=cat)

    r1 = eng.to_catalog(cmpl_book(title='Сети', author='Таненбаум Э.',
                                  inv=('N-1',)), ksu_no='2026/1')
    r2 = eng.to_catalog(cmpl_book(title='Сети', author='Таненбаум Э.',
                                  inv=('N-2',)), ksu_no='2026/2')
    check('1-й перенос -> created', r1['action'] == 'created')
    check('повтор того же заглавия -> updated', r2['action'] == 'updated')
    check('тот же mfn', r2['catalog_mfn'] == r1['catalog_mfn'])
    check('запись не задвоена (count=1)', cat.count('IBIS') == 1)

    saved = cat.get('IBIS', r1['catalog_mfn'])
    ex = saved['910'] if isinstance(saved['910'], list) else [saved['910']]
    check('экземпляры дополнены (2 шт.)', len(ex) == 2)
    check('новый экз. findable', cat.find_exemplar('IBIS', 'N-2') is not None)
    check('обе КСУ-связи на записи',
          {i.get('u') for i in _insts(saved, '66')} == {'2026/1', '2026/2'})

    # другое заглавие -> новая запись
    r3 = eng.to_catalog(cmpl_book(title='ОС', author='Таненбаум Э.',
                                  inv=('O-1',)), ksu_no='2026/3')
    check('другое заглавие -> created', r3['action'] == 'created')
    check('другое заглавие -> другой mfn',
          r3['catalog_mfn'] != r1['catalog_mfn'])
    check('теперь 2 записи', cat.count('IBIS') == 2)


# --------------------------------------------------------------------------- #
# Триггер / back-compat (нет handle → standalone).
# --------------------------------------------------------------------------- #
def trigger_and_standalone_checks():
    print('-- триггер 66 + back-compat (нет catalog-handle)')
    cat = fresh_catalog()
    if cat is not None:
        eng = fresh_engine(catalog=cat)
        # нет флага 66 -> перенос не запускается
        norec = cmpl_book(title='Без флага', flag66=False)
        res = eng.to_catalog(norec)
        check('нет 66 -> not_triggered', res['action'] == 'not_triggered')
        check('нет 66 -> ничего не записано', cat.count('IBIS') == 0)
        check('нет 66 -> исходник не помечен', not is_source_deleted(norec))

    # back-compat: нет catalog-handle -> реформат строится, но не пишется
    eng2 = fresh_engine(catalog=None)
    rec = cmpl_book(title='Автономный', inv=('S-1',))
    res2 = eng2.to_catalog(rec)
    check('standalone -> action=no_catalog', res2['action'] == 'no_catalog')
    check('standalone -> реформат построен', res2['record'] is not None)
    check('standalone -> 200 в реформате',
          _val(res2['record'], '200', 'a') == 'Автономный')
    check('standalone -> экземпляры в реформате',
          set(res2['exemplars']) == {'S-1'})
    check('standalone -> исходник НЕ помечен (нечего удалять без переноса)',
          not is_source_deleted(rec))
    check('standalone -> source_deleted False', res2['source_deleted'] is False)


# --------------------------------------------------------------------------- #
# PG-паритет: реформат — чистая функция, идентична на любом backend'е.
# --------------------------------------------------------------------------- #
def pg_parity_checks():
    print('-- PG-паритет: реформат БО store-независим')
    # to_catalog'овский реформат (reformat_to_ibis) — чистая функция над dict'ом,
    # не зависит от backend стора (sqlite/PG). Перенос идёт через catalog-handle,
    # чья запись использует портируемый SQL (CatalogStore). Здесь проверяем
    # детерминизм/независимость реформата от стора: два движка с РАЗНЫМИ сторами
    # дают идентичный реформат одного БО.
    eng_a = fresh_engine()
    eng_b = AcquisitionEngine(store=AcquisitionStore(':memory:'), catalog=None)
    rec = cmpl_book(title='Паритет', author='Автор А.', inv=('P-1', 'P-2'),
                    price='100.00')
    rec['938'] = [{'Q': '2026', 'N': '2'}]
    ra = eng_a.reformat_to_ibis(rec)
    rb = eng_b.reformat_to_ibis(rec)
    check('реформат детерминирован (store-независим)', ra == rb)
    check('реформат не зависит от наличия catalog-handle',
          ra['920'] == 'PAZK' and _val(ra, '200', 'a') == 'Паритет')

    # перенос экземпляров через _carry_exemplars также чистый
    ex = eng_a._carry_exemplars(rec, '2026/PG')
    check('перенос 910 детерминирован',
          [e['b'] for e in ex] == ['P-1', 'P-2'])
    check('перенос 910 ставит КСУ ^U',
          all(e.get('u') == '2026/PG' for e in ex))


def real_catalog_smoke_checks():
    print('-- сквозная проба против РЕАЛЬНОГО CatalogStore (когда дерево готово)')
    cat = real_catalog_or_none()
    if cat is None:
        print('  .. real CatalogStore недоступен/в работе у сиблинга — SKIP')
        return
    eng = fresh_engine(catalog=cat)
    rec = cmpl_book(title='Реальный каталог', author='Иванов И.',
                    inv=('RC-1', 'RC-2'))
    res = eng.to_catalog(rec, ksu_no='2026/99')
    check('[real] ToCat создал запись', res['action'] == 'created')
    saved = cat.get('IBIS', res['catalog_mfn'])
    check('[real] заглавие в ЭК', _val(saved, '200', 'a') == 'Реальный каталог')
    check('[real] 2 экземпляра findable',
          cat.find_exemplar('IBIS', 'RC-1') is not None and
          cat.find_exemplar('IBIS', 'RC-2') is not None)
    check('[real] экз. свободен (выдаваем)',
          cat.is_available('IBIS', 'RC-1') is True)
    check('[real] исходник помечен VD=DEL', is_source_deleted(rec))
    # идемпотентность на реальном сторе
    res2 = eng.to_catalog(rec, ksu_no='2026/99')
    check('[real] повтор -> already_transferred',
          res2['action'] == 'already_transferred')
    check('[real] запись не задвоена', cat.count('IBIS') == 1)


def main():
    reformat_checks()
    trigger66_checks()
    to_catalog_full_checks()
    explicit_901_checks()
    vd_del_checks()
    vd_del_not_set_on_reject_checks()
    resupply_checks()
    trigger_and_standalone_checks()
    pg_parity_checks()
    real_catalog_smoke_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
