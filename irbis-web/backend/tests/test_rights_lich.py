#!/usr/bin/env python3
"""RIGHT/LICH — права и личный кабинет ПТ (кластер 7, рёбра 7.2/7.3/7.4/7.5) — тест.

Покрывает:

  * RIGHT (``access/rights.py``):
      - ``access_level`` — гейтинг по категории читателя: deny/view/download,
        выбор МАКСИМАЛЬНОГО разрешённого уровня среди правил, период
        общий/правила, пустой шаблон → полный доступ (955^B пусто), нет правил →
        download в периоде / deny вне периода (ребро 7.3);
      - ``RightStore`` — upsert/get/list/delete шаблонов;
      - ``RightService`` — резолв 955^B каталожной записи через опц. catalog-handle
        → id шаблона → уровень доступа (ребро 7.2); back-compat без handle
        (template_id/template напрямую);
      - ``page_limit`` — лимит страниц ^F по категории.
  * LICH (``access/lich.py``):
      - закладки (поле 3): add/remove идемпотентно, отсортированы (ребро 7.4);
      - рейтинг (поле 7): 0..5, выход за диапазон → ValueError (ребро 7.4);
      - счётчик скачанных (поле 4): инкремент (ребро 7.4);
      - ``download_budget = RIGHT.^F − LICH.v4`` и ``can_download`` (ребро 7.5).
  * PG-ПАРИТЕТ — когда postgres доступен (иначе чисто пропускается): тот же
    upsert/get RIGHT и закладки/скачано/рейтинг LICH на PG-DSN.

Вписан в раннер tests/test_access.py (его module-list) через ``module_checks`` —
раннер вызывает каждую ``*_checks()`` и складывает PASS/FAIL.

Standalone:  py tests/test_rights_lich.py
PG:          (set ACCESS_BACKEND=postgres) py -3.12 tests/test_rights_lich.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import rights as rights_mod
from access.rights import (RightStore, RightService, access_level, page_limit,
                           DENY, VIEW, DOWNLOAD)
from access.lich import LichStore, LichService

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Категории читателя (коды по 50.mnu — синтетика теста).
KAT_STUDENT = '1'    # студент: только постраничный просмотр
KAT_TEACHER = '2'    # преподаватель: скачивание с лимитом
KAT_GUEST = '9'      # гость: явный запрет

# Фиксированная «сегодняшняя» дата для детерминизма проверок периода.
TODAY = '20260622'


def _rule(cat, value, level, limit='', unit='', start='', end=''):
    return {'category': cat, 'value': value, 'level': level,
            'limit': limit, 'unit': unit, 'start': start, 'end': end}


# Шаблон: студент→view, преподаватель→download(лимит 50 стр.), гость→deny.
TEMPLATE = {
    'id': 'R1',
    'period': {'start': '20200101', 'end': '20301231'},
    'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '1'),
        _rule(rights_mod.CAT_READER_KAT, KAT_TEACHER, '2', limit='50'),
        _rule(rights_mod.CAT_READER_KAT, KAT_GUEST, '0'),
    ],
}


# --------------------------------------------------------------------------- #
# 1. access_level — чистый гейтинг по категориям (ребро 7.3).
# --------------------------------------------------------------------------- #
def access_level_checks():
    print('-- rights: access_level (gating by reader category)')

    # Категорийный гейтинг: deny / view / download.
    check('гость → deny',
          access_level(KAT_GUEST, TEMPLATE, today=TODAY) == DENY)
    check('студент → view',
          access_level(KAT_STUDENT, TEMPLATE, today=TODAY) == VIEW)
    check('преподаватель → download',
          access_level(KAT_TEACHER, TEMPLATE, today=TODAY) == DOWNLOAD)

    # Категория без правила → deny (нет совпадений, п.5 алгоритма).
    check('неизвестная категория → deny',
          access_level('777', TEMPLATE, today=TODAY) == DENY)
    check('пустая категория → deny',
          access_level('', TEMPLATE, today=TODAY) == DENY)
    check('None категория → deny',
          access_level(None, TEMPLATE, today=TODAY) == DENY)

    # Пустой шаблон (955^B пусто) → полный доступ download (п.1).
    check('пустой шаблон (None) → download',
          access_level(KAT_GUEST, None, today=TODAY) == DOWNLOAD)
    check('пустой dict → download',
          access_level(KAT_GUEST, {}, today=TODAY) == DOWNLOAD)

    # Нет правил → download в периоде / deny вне (п.3/4).
    no_rules_in = {'id': 'R', 'period': {'start': '20200101', 'end': '20301231'},
                   'rules': []}
    no_rules_out = {'id': 'R', 'period': {'start': '20200101', 'end': '20201231'},
                    'rules': []}
    check('нет правил, дата в периоде → download',
          access_level(KAT_GUEST, no_rules_in, today=TODAY) == DOWNLOAD)
    check('нет правил, дата вне периода → deny',
          access_level(KAT_GUEST, no_rules_out, today=TODAY) == DENY)

    # МАКСИМУМ среди совпавших правил (g10): для одной категории несколько правил.
    multi = {'id': 'M', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '1'),   # view
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '2'),   # download — победит
    ]}
    check('несколько правил категории → максимум (download)',
          access_level(KAT_STUDENT, multi, today=TODAY) == DOWNLOAD)
    multi2 = {'id': 'M2', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '0'),   # deny
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '1'),   # view — победит над deny
    ]}
    check('deny+view для одной категории → view (максимум)',
          access_level(KAT_STUDENT, multi2, today=TODAY) == VIEW)

    # Период ПРАВИЛА сужает доступ (^D/^E), даже если общий период открыт.
    rule_window = {'id': 'W', 'period': {'start': '20000101', 'end': '20991231'},
                   'rules': [_rule(rights_mod.CAT_READER_KAT, KAT_TEACHER, '2',
                                   start='20200101', end='20201231')]}
    check('правило вне своего периода → deny',
          access_level(KAT_TEACHER, rule_window, today=TODAY) == DENY)
    check('правило в своём периоде → download',
          access_level(KAT_TEACHER, rule_window, today='20200601') == DOWNLOAD)

    # Неизвестный код ^C → deny (консервативно).
    weird = {'id': 'X', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '9')]}
    check('неизвестный код права → deny',
          access_level(KAT_STUDENT, weird, today=TODAY) == DENY)

    # Правила только для других измерений (IP/факультет) не дают доступ по категории.
    other_dim = {'id': 'O', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_FACULTY, '01', '2'),
        _rule(rights_mod.CAT_IP, '192.168.0.0', '2')]}
    check('правила другого измерения → deny по категории',
          access_level(KAT_STUDENT, other_dim, today=TODAY) == DENY)


# --------------------------------------------------------------------------- #
# 2. page_limit — лимит страниц ^F по категории (ребро 7.3/7.5).
# --------------------------------------------------------------------------- #
def page_limit_checks():
    print('-- rights: page_limit (^F)')
    check('преподаватель: лимит 50 страниц',
          page_limit(KAT_TEACHER, TEMPLATE, today=TODAY) == 50)
    check('студент: лимит не задан (^F пусто) → None',
          page_limit(KAT_STUDENT, TEMPLATE, today=TODAY) is None)
    check('пустой шаблон → None',
          page_limit(KAT_TEACHER, None, today=TODAY) is None)
    check('гость (deny) → None (запрет лимита не несёт)',
          page_limit(KAT_GUEST, TEMPLATE, today=TODAY) is None)
    # Несколько правил с лимитом → максимум.
    multi = {'id': 'L', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_TEACHER, '2', limit='20'),
        _rule(rights_mod.CAT_READER_KAT, KAT_TEACHER, '2', limit='80')]}
    check('несколько лимитов → максимум (80)',
          page_limit(KAT_TEACHER, multi, today=TODAY) == 80)
    # Проценты (^G='1') не дают постраничного лимита.
    pct = {'id': 'P', 'period': {}, 'rules': [
        _rule(rights_mod.CAT_READER_KAT, KAT_TEACHER, '2', limit='30', unit='1')]}
    check('лимит в процентах (^G=1) → None по страницам',
          page_limit(KAT_TEACHER, pct, today=TODAY) is None)


# --------------------------------------------------------------------------- #
# 3. RightStore — хранилище шаблонов (sqlite).
# --------------------------------------------------------------------------- #
def right_store_checks():
    print('-- rights: RightStore (sqlite)')
    st = RightStore(':memory:')
    check('empty store count == 0', st.count() == 0)
    saved = st.upsert('R1', period=TEMPLATE['period'], rules=TEMPLATE['rules'],
                      description='Учебники')
    check('upsert echoes id', saved['id'] == 'R1')
    check('upsert normalises rules', len(saved['rules']) == 3)
    check('store count == 1', st.count() == 1)

    got = st.get('R1')
    check('get round-trips period', got['period']['start'] == '20200101')
    check('get round-trips rules', got['rules'][1]['value'] == KAT_TEACHER)
    check('get round-trips description', got['description'] == 'Учебники')
    check('get missing → None', st.get('NOPE') is None)

    # upsert идемпотентен/обновляет (тот же id → одна строка, новые данные).
    st.upsert('R1', period={'start': '20210101', 'end': '20211231'},
              rules=[_rule(rights_mod.CAT_READER_KAT, KAT_STUDENT, '2')])
    check('upsert same id does not duplicate', st.count() == 1)
    check('upsert updates data', st.get('R1')['period']['start'] == '20210101')

    # подполевые алиасы (A/B/C/F) принимаются и канонизируются.
    st.upsert('R2', rules=[{'A': rights_mod.CAT_READER_KAT, 'B': KAT_TEACHER,
                            'C': '2', 'F': '10'}])
    r2 = st.get('R2')
    check('subfield aliases canonicalised',
          r2['rules'][0]['category'] == rights_mod.CAT_READER_KAT
          and r2['rules'][0]['value'] == KAT_TEACHER
          and r2['rules'][0]['level'] == '2'
          and r2['rules'][0]['limit'] == '10')

    items = st.list()
    check('list returns both templates', len(items) == 2)
    check('delete removes a template', st.delete('R2') is True and st.count() == 1)
    check('delete missing → False', st.delete('NOPE') is False)


# --------------------------------------------------------------------------- #
# 4. RightService — резолв 955^B через catalog-handle (ребро 7.2) + back-compat.
# --------------------------------------------------------------------------- #
class _FakeCatalog:
    """Минимальный catalog-handle: get(db, mfn) -> record (как CatalogStore.get)."""
    def __init__(self, records):
        self._records = records  # {(db, mfn): record-dict}

    def get(self, db, mfn):
        return self._records.get((db, mfn))


def right_service_checks():
    print('-- rights: RightService (955^B resolve via catalog handle / back-compat)')
    st = RightStore(':memory:')
    st.upsert('R1', period=TEMPLATE['period'], rules=TEMPLATE['rules'])

    # Каталожные записи: ресурс с 955^B=R1; ресурс без 955^B; повторяющееся 955.
    cat = _FakeCatalog({
        ('IBIS', 10): {'955': {'a': 'book.pdf', 'b': 'R1'}},        # 955^B → R1
        ('IBIS', 11): {'955': {'a': 'free.pdf'}},                   # 955 без ^B
        ('IBIS', 12): {'200': {'a': 'Нет 955 вовсе'}},              # нет 955
        ('IBIS', 13): {'955': [{'a': 'x.pdf'}, {'b': 'R1'}]},       # ^B во 2-м повторении
    })
    svc = RightService(store=st, catalog=cat, now=lambda: _ts(TODAY))

    # 7.2: резолв 955^B → id шаблона.
    check('955^B → template id (R1)', svc.template_id_for_record('IBIS', 10) == 'R1')
    check('955 без ^B → None', svc.template_id_for_record('IBIS', 11) is None)
    check('нет 955 → None', svc.template_id_for_record('IBIS', 12) is None)
    check('^B в повторении 955 → R1', svc.template_id_for_record('IBIS', 13) == 'R1')

    # 7.2+7.3: уровень доступа по записи (handle + стор + категория).
    check('по записи: преподаватель → download',
          svc.access_level(KAT_TEACHER, db='IBIS', mfn=10) == DOWNLOAD)
    check('по записи: студент → view',
          svc.access_level(KAT_STUDENT, db='IBIS', mfn=10) == VIEW)
    check('по записи: гость → deny',
          svc.access_level(KAT_GUEST, db='IBIS', mfn=10) == DENY)
    # Ресурс без 955^B → полный доступ всем (download).
    check('запись без 955^B → download (полный доступ)',
          svc.access_level(KAT_GUEST, db='IBIS', mfn=11) == DOWNLOAD)
    # page_limit по записи.
    check('по записи: лимит преподавателя 50',
          svc.page_limit(KAT_TEACHER, db='IBIS', mfn=10) == 50)

    # back-compat без handle: template_id напрямую из стора.
    svc_nohandle = RightService(store=st, catalog=None, now=lambda: _ts(TODAY))
    check('back-compat: template_id → download',
          svc_nohandle.access_level(KAT_TEACHER, template_id='R1') == DOWNLOAD)
    check('back-compat без handle: db/mfn не резолвится → полный доступ',
          svc_nohandle.access_level(KAT_GUEST, db='IBIS', mfn=10) == DOWNLOAD)
    # back-compat: готовый template-dict (без стора вовсе).
    svc_bare = RightService(store=None, catalog=None, now=lambda: _ts(TODAY))
    check('back-compat: template dict напрямую',
          svc_bare.access_level(KAT_STUDENT, template=TEMPLATE) == VIEW)

    # Seam не бросает: битый handle деградирует к полному доступу.
    class _BoomCatalog:
        def get(self, db, mfn):
            raise RuntimeError('boom')
    svc_boom = RightService(store=st, catalog=_BoomCatalog(), now=lambda: _ts(TODAY))
    check('битый catalog-handle → None (деградация), доступ download',
          svc_boom.template_id_for_record('IBIS', 10) is None
          and svc_boom.access_level(KAT_GUEST, db='IBIS', mfn=10) == DOWNLOAD)


# --------------------------------------------------------------------------- #
# 5. LICH — закладки/рейтинг/счётчик (ребро 7.4).
# --------------------------------------------------------------------------- #
def lich_basics_checks():
    print('-- lich: bookmarks / rating / downloaded (field 3/7/4)')
    st = LichStore(':memory:')
    svc = LichService(st)
    R, T = 'RI=111', 'IBIS/АБ123'

    check('empty store count == 0', st.count() == 0)
    check('нет записи: закладок []', svc.bookmarks(R, T) == [])
    check('нет записи: рейтинг None', svc.rating(R, T) is None)
    check('нет записи: скачано 0', svc.downloaded(R, T) == 0)

    # Закладки (поле 3): add идемпотентно и отсортировано.
    check('add закладку 5 → [5]', svc.add_bookmark(R, T, 5) == [5])
    check('add закладку 2 → [2,5]', svc.add_bookmark(R, T, 2) == [2, 5])
    check('add дубль 5 → [2,5] (идемпотентно)', svc.add_bookmark(R, T, 5) == [2, 5])
    check('bookmarks читает [2,5]', svc.bookmarks(R, T) == [2, 5])
    check('remove 2 → [5]', svc.remove_bookmark(R, T, 2) == [5])
    check('remove отсутствующей → no-op [5]', svc.remove_bookmark(R, T, 99) == [5])
    # Невалидный номер страницы → ValueError.
    bad = False
    try:
        svc.add_bookmark(R, T, 0)
    except ValueError:
        bad = True
    check('add закладку 0 → ValueError', bad)

    # Рейтинг (поле 7): 0..5; вне диапазона → ValueError.
    check('rate 4 → 4', svc.rate(R, T, 4) == 4)
    check('rating читает 4', svc.rating(R, T) == 4)
    check('rate 0 допустим', svc.rate(R, T, 0) == 0)
    for badv in (6, -1, 'x', None):
        raised = False
        try:
            svc.rate(R, T, badv)
        except ValueError:
            raised = True
        check('rate %r → ValueError' % (badv,), raised)

    # Счётчик скачанных (поле 4): инкремент.
    check('record_download 3 → 3', svc.record_download(R, T, 3) == 3)
    check('record_download +2 → 5', svc.record_download(R, T, 2) == 5)
    check('downloaded читает 5', svc.downloaded(R, T) == 5)
    neg = False
    try:
        svc.record_download(R, T, -1)
    except ValueError:
        neg = True
    check('record_download -1 → ValueError', neg)

    # Одна строка на (reader, text); закладки/рейтинг/скачано в одной записи.
    check('одна строка на reader+text', st.count() == 1)
    # Изоляция по тексту: другой текст того же читателя независим.
    svc.add_bookmark(R, 'IBIS/ДРУГОЙ', 7)
    check('другой текст изолирован', svc.bookmarks(R, 'IBIS/ДРУГОЙ') == [7]
          and svc.bookmarks(R, T) == [5])
    # for_reader видит оба текста читателя.
    texts = {e['text'] for e in svc.for_reader(R)}
    check('for_reader видит оба текста', texts == {T, 'IBIS/ДРУГОЙ'})


# --------------------------------------------------------------------------- #
# 6. download_budget = RIGHT.^F − LICH.v4 (ребро 7.5).
# --------------------------------------------------------------------------- #
def download_budget_checks():
    print('-- lich: download_budget = RIGHT.^F − LICH.v4 (quota)')
    rstore = RightStore(':memory:')
    rstore.upsert('R1', period=TEMPLATE['period'], rules=TEMPLATE['rules'])
    rsvc = RightService(store=rstore, now=lambda: _ts(TODAY))

    lst = LichStore(':memory:')
    lsvc = LichService(lst, rights=rsvc)
    R, T = 'RI=111', 'IBIS/АБ123'

    # Лимит преподавателя = 50, скачано 0 → остаток 50.
    check('остаток = лимит при 0 скачанных',
          lsvc.download_budget(R, T, reader_category=KAT_TEACHER, template_id='R1') == 50)
    # Скачали 20 → остаток 30.
    lsvc.record_download(R, T, 20)
    check('остаток 50−20 = 30',
          lsvc.download_budget(R, T, reader_category=KAT_TEACHER, template_id='R1') == 30)
    # Скачали ещё 40 (всего 60 > 50) → остаток 0 (не отрицательный).
    lsvc.record_download(R, T, 40)
    check('остаток не отрицательный (max(0, 50−60)=0)',
          lsvc.download_budget(R, T, reader_category=KAT_TEACHER, template_id='R1') == 0)

    # Студент: лимит не задан (^F пусто) → бюджет None (без ограничения).
    check('студент без ^F → бюджет None',
          lsvc.download_budget(R, T, reader_category=KAT_STUDENT, template_id='R1') is None)

    # Явный page_limit имеет приоритет над seam.
    check('явный page_limit=100, скачано 60 → остаток 40',
          lsvc.download_budget(R, T, page_limit=100) == 40)

    # can_download: гейтинг по остатку.
    R2, T2 = 'RI=222', 'IBIS/КН9'
    check('can_download когда хватает',
          lsvc.can_download(R2, T2, pages=10, reader_category=KAT_TEACHER, template_id='R1'))
    lsvc.record_download(R2, T2, 45)  # остаток 5
    check('can_download False когда не хватает (нужно 10, остаток 5)',
          not lsvc.can_download(R2, T2, pages=10, reader_category=KAT_TEACHER, template_id='R1'))
    check('can_download True когда ровно хватает (нужно 5, остаток 5)',
          lsvc.can_download(R2, T2, pages=5, reader_category=KAT_TEACHER, template_id='R1'))
    # Без лимита (студент) можно скачивать сколько угодно.
    check('can_download True при отсутствии лимита',
          lsvc.can_download(R2, T2, pages=9999, reader_category=KAT_STUDENT, template_id='R1'))

    # Без rights-seam бюджет не ограничен.
    lsvc_norights = LichService(LichStore(':memory:'), rights=None)
    check('без rights-seam → бюджет None',
          lsvc_norights.download_budget(R, T, reader_category=KAT_TEACHER) is None)
    check('без rights-seam → can_download True',
          lsvc_norights.can_download(R, T, pages=1000, reader_category=KAT_TEACHER))


# --------------------------------------------------------------------------- #
# 7. PG-ПАРИТЕТ — когда postgres доступен; иначе чисто пропускается.
# --------------------------------------------------------------------------- #
def _pg_reachable_dsn():
    want = os.environ.get('ACCESS_BACKEND', '').lower() in ('postgres', 'pg') \
        or os.environ.get('ACCESS_TEST_PG') == '1'
    if not want:
        return None
    try:
        from access import pgstore
        dsn = pgstore.default_pg_dsn()
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS right_template')
        conn.execute('DROP TABLE IF EXISTS lich_entry')
        conn.close()
        return dsn
    except Exception as e:
        print('-- rights/lich: postgres SKIPPED (%s: %s)'
              % (type(e).__name__, str(e).splitlines()[0]))
        return None


def pg_parity_checks():
    dsn = _pg_reachable_dsn()
    if dsn is None:
        return
    print('-- rights/lich: store (postgres parity)')

    # RIGHT на PG.
    rst = RightStore(dsn, backend='postgres')
    check('[pg] right empty count == 0', rst.count() == 0)
    rst.upsert('R1', period=TEMPLATE['period'], rules=TEMPLATE['rules'], description='X')
    check('[pg] right count == 1', rst.count() == 1)
    got = rst.get('R1')
    check('[pg] right round-trips rules', got and len(got['rules']) == 3)
    check('[pg] access_level over pg template: preподаватель download',
          access_level(KAT_TEACHER, got, today=TODAY) == DOWNLOAD)
    rst.upsert('R1', period={'start': '20210101', 'end': '20211231'}, rules=[])
    check('[pg] upsert no-duplicate', rst.count() == 1)
    check('[pg] right delete', rst.delete('R1') is True and rst.count() == 0)

    # LICH на PG.
    lst = LichStore(dsn, backend='postgres')
    lsvc = LichService(lst)
    R, T = 'RI=PG', 'IBIS/PG1'
    check('[pg] lich empty count == 0', lst.count() == 0)
    check('[pg] add bookmark', lsvc.add_bookmark(R, T, 3) == [3])
    check('[pg] add bookmark sorted', lsvc.add_bookmark(R, T, 1) == [1, 3])
    check('[pg] rate', lsvc.rate(R, T, 5) == 5 and lsvc.rating(R, T) == 5)
    check('[pg] downloaded increment', lsvc.record_download(R, T, 7) == 7)
    check('[pg] one row per reader+text', lst.count() == 1)
    # budget on PG (явный лимит).
    check('[pg] budget 50−7=43', lsvc.download_budget(R, T, page_limit=50) == 43)

    # cleanup
    try:
        from access import pgstore
        conn = pgstore._admin_conn(dsn)
        conn.execute('DROP TABLE IF EXISTS right_template')
        conn.execute('DROP TABLE IF EXISTS lich_entry')
        conn.close()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Хелперы.
# --------------------------------------------------------------------------- #
def _ts(yyyymmdd):
    """ГГГГММДД → epoch-секунды локального полудня (для инъекции now в RightService)."""
    import time as _t
    tm = _t.strptime(yyyymmdd + ' 12:00:00', '%Y%m%d %H:%M:%S')
    return _t.mktime(tm)


def main():
    access_level_checks()
    page_limit_checks()
    right_store_checks()
    right_service_checks()
    lich_basics_checks()
    download_budget_checks()
    pg_parity_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
