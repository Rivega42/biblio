#!/usr/bin/env python3
"""HTTP-route-тесты движков СВЯЗНОСТИ, выведенных в core.Api.route() (эпик #188).

Три «готовых» движка landed-ранее (их сами НЕ правим) теперь достижимы по HTTP —
каждое утверждение идёт через настоящий ``core.Api.route()`` (тот же путь, что у
server.py / app_aiohttp.py), с СКОНСТРУИРОВАННЫМ ``Api`` (конструктор НЕ
подключается к ИРБИС).

Покрыто (контракт задачи):
  * GET /api/linked/{db}/{mfn}?kind=children|host — обход связи иерархии
    (catalog.linked_records). ПУБЛИЧНЫЙ: форма ответа {db,mfn,kind,total,items},
    public-db guard (гость на непубличную БД → 403), мягкая деградация
    (несуществующий mfn / нет каталог-движка → {total:0,items:[]}, не 500).
  * GET /api/fulltext/{db}/{mfn} — артефакты ПТ (fulltext.artifacts_for) + уровень
    доступа (rights.access_level/page_limit, lich.download_budget). ПУБЛИЧНЫЙ:
    форма {db,mfn,artifacts:[{kind,ref,pages,rightsTemplate}],access:{level,
    pageLimit,downloadBudget}}, public-db guard, гейтинг по категории читателя
    (deny/view/download), квота скачивания только для читателя (по билету; чужой
    LICH-счётчик не светим), мягкая деградация (нет артефактов → []; пустой
    шаблон → download без 500).
  * GET /api/bp/provision?discipline=|specialty=|faculty= — быстрый отчёт ККО
    (bookprovision.*_provision). STAFF-grant: не-staff (гость/читатель) → 403;
    форма BpProvisionReport (coefficient/status/shortfall/bindings); неизвестный
    id → 404 (не 500).

PG-ПАРИТЕТ: эндпойнты-движки построены на ОБЩЕМ ``access.catalog.CatalogStore`` и
сторах fulltext/rights/lich, которые сами несут sqlite+postgres-паритет (он покрыт
их юнит-сьютами test_record_links/test_fulltext/test_rights_lich). Здесь — поведение
ЭНДПОЙНТА (гейтинг/форма/деградация), бэкенд-инвариантное; sqlite-leg всегда зелёный,
а ``route()`` одинаков на обоих бэкендах. Поэтому отдельный PG-leg тут не дублируется.

Вписан в раннер tests/test_access.py (его module-list) через ``module_checks`` —
раннер вызывает каждую ``*_checks()`` и складывает PASS/FAIL.

Standalone (дом-стиль):
  py tests/test_engine_routes.py  -> 'ok …' + 'N passed, M failed' + код возврата.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS
from access.catalog import CatalogStore
from access import fulltext as _ft
from access import rights as _rights
from access import lich as _lich
from access import bookprovision as _bp
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


# Staff-грант для КО-функции /api/bp/provision (bp.read читает bookprovision).
STAFF_GRANTS = [
    {'function': 'bp.read', 'db': '*', 'level': 'read'},
    {'function': 'bp.write', 'db': '*', 'level': 'write'},
]


class FakeRdrIrbis:
    """Заглушка SessionManager: отдаёт RDR-запись по mfn с полем 50 (категория).

    ``categories``: {rdr_mfn: '<код категории 50.mnu>'}. Любой другой mfn → запись
    без поля 50 (категория None). Нужна, чтобы _reader_category() прочитал живую
    запись RDR читательской сессии — в реальном Api это делает self.irbis."""

    def __init__(self, categories=None, raise_on=()):
        self._categories = categories or {}
        self.raise_on = set(raise_on)

    def read_record(self, db, mfn):
        if 'read_record' in self.raise_on:
            from irbis.client import IrbisError
            raise IrbisError(-1, 'stub raise read_record')
        cat = self._categories.get(mfn)
        flds = []
        if cat is not None:
            flds.append({'tag': '50', 'value': str(cat), 'subfields': {}})
        return {'mfn': mfn, 'status': '0', 'version': '1', 'guid': None,
                'fields': flds}

    def format_record(self, db, mfn, pft='@brief'):
        return ''


def _api(categories=None, raise_on=()):
    """Сконструированный Api без живого ИРБИС, со свежими in-memory сторами движков.

    Каталог — общий seam: linked_records, fulltext (955/955^B) и rights (резолв
    955^B) ходят в ОДИН CatalogStore. Заглушка irbis отдаёт RDR (категория)."""
    os.environ['JWT_SECRET'] = 'engine-routes-test-secret'
    os.environ['ACCESS_DB'] = ':memory:'
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = FakeRdrIrbis(categories=categories, raise_on=raise_on)
    # Свежие in-memory сторы — каждая группа стартует изолированно и пусто.
    seed_vocab.seed_vocabularies(api.access, from_catalog=False)
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    api.fulltext = _ft.FulltextRegistry(store=_ft.FulltextStore(':memory:'),
                                        catalog=api.catalog)
    api.rights = _rights.RightService(store=_rights.RightStore(':memory:'),
                                      catalog=api.catalog)
    api.lich = _lich.LichService(_lich.LichStore(':memory:'), rights=api.rights)
    api.bookprovision = _bp.BookProvisionEngine(':memory:', catalog=api.catalog)
    return api, _core


def _staff(api, login='ko'):
    tok, _ = api._new_session('staff', login, STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111', rdr_mfn=1):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=rdr_mfn)
    return {'authorization': 'Bearer ' + tok}


_INV = [0]


def _rec(title, **extra):
    """Валидная книжная запись каталога (проходит ФЛК) с уникальным экз.№."""
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


def _mfns(items):
    return {it['mfn'] for it in items}


# --------------------------------------------------------------------------- #
# 1. /api/linked — обход связи иерархии (публичный, форма + деградация).
# --------------------------------------------------------------------------- #
def linked_route_checks():
    print('-- linked: связь иерархии через route() (публичный)')
    api, _core = _api()
    H = _guest(api)
    # Журнал-хозяин + две статьи (463^c → 200^a), как 9.1.
    jm = api.catalog.save('IBIS', _rec('Театр и жизнь'))['mfn']
    a1 = api.catalog.save('IBIS', _rec('Сцена', **{'463': [{'c': 'Театр и жизнь'}]}))['mfn']
    a2 = api.catalog.save('IBIS', _rec('Кулисы', **{'463': [{'c': 'Театр и жизнь'}]}))['mfn']

    # children: хозяин → его статьи.
    st, p = api.route('GET', '/api/linked/IBIS/%d' % jm, {'kind': ['children']}, None, H)
    check('GET /api/linked children -> 200', st == 200)
    d = p['data']
    check('форма: db/mfn/kind/total/items присутствуют',
          set(d.keys()) >= {'db', 'mfn', 'kind', 'total', 'items'})
    check('children kind эхо', d['kind'] == 'children')
    check('children total == 2', d['total'] == 2)
    check('children items == обе статьи', _mfns(d['items']) == {a1, a2})
    check('item несёт {mfn, brief}',
          all(set(it.keys()) == {'mfn', 'brief'} for it in d['items']))
    check('служебное keys движка наружу НЕ отдаётся', 'keys' not in d)

    # host: статья → её журнал.
    st, p = api.route('GET', '/api/linked/IBIS/%d' % a1, {'kind': ['host']}, None, H)
    check('GET /api/linked host -> 200', st == 200)
    check('host items == журнал', _mfns(p['data']['items']) == {jm})

    # kind по умолчанию children (без ?kind=).
    st, p = api.route('GET', '/api/linked/IBIS/%d' % jm, {}, None, H)
    check('kind по умолчанию children', p['data']['kind'] == 'children' and st == 200)

    # Мягкая деградация: несуществующий mfn → total:0, items:[], не 500.
    st, p = api.route('GET', '/api/linked/IBIS/999999', {'kind': ['children']}, None, H)
    check('несуществующий mfn -> 200 total:0', st == 200 and p['data']['total'] == 0)
    check('несуществующий mfn -> items []', p['data']['items'] == [])

    # Мягкая деградация: нет каталог-движка → пусто, не 500.
    api.catalog = None
    st, p = api.route('GET', '/api/linked/IBIS/%d' % jm, {'kind': ['children']}, None, H)
    check('нет каталог-движка -> 200 пусто (не 500)',
          st == 200 and p['data']['total'] == 0 and p['data']['items'] == [])


def linked_public_guard_checks():
    print('-- linked: public-db guard (гость на непубличную БД → 403)')
    api, _core = _api()
    # Непубличная БД (RDR — служебная/ПДн): гость должен получить 403 ДО чтения.
    for headers, who in ((_guest(api), 'guest'), (_reader(api), 'reader')):
        st, _ = api.route('GET', '/api/linked/RDR/1', {'kind': ['children']}, None, headers)
        check('%s на непубличную RDR -> 403' % who, st == 403)
    # Тот же гость на ПУБЛИЧНУЮ IBIS — допущен (200), guard не глухой.
    st, _ = api.route('GET', '/api/linked/IBIS/1', {'kind': ['children']}, None, _guest(api))
    check('гость на публичную IBIS -> 200', st == 200)
    # Нет сессии вовсе → 401/403, не 200.
    st, _ = api.route('GET', '/api/linked/IBIS/1', {'kind': ['children']}, None, {})
    check('нет сессии -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# 2. /api/fulltext — артефакты ПТ + уровень доступа (публичный).
# --------------------------------------------------------------------------- #
# Шаблон прав: студент(1)→view, преподаватель(2)→download(лимит 50 стр.), гость(9)→deny.
KAT_STUDENT, KAT_TEACHER, KAT_GUEST = '1', '2', '9'


def _rule(cat, value, level, limit=''):
    return {'category': cat, 'value': value, 'level': level,
            'limit': limit, 'unit': '', 'start': '', 'end': ''}


def _seed_fulltext(api, db='IBIS', template_id='R1'):
    """Завести запись каталога с 955 (артефакт + 955^B→шаблон) и сам шаблон прав.

    Артефакт ПТ резолвится и из стора (attach), и из каталога (955). Шаблон прав
    R1 описывает категорийный гейтинг; 955^B записи ссылается на R1."""
    mfn = api.catalog.save(db, _rec('Полнотекстовый труд',
                                    **{'955': [{'a': 'book.pdf', 'n': '120', 'b': template_id}]}))['mfn']
    # Доп. артефакт прямо через стор (поверх каталожного) — проверим, что оба видны.
    api.fulltext.attach(db, mfn, '955', file='extra.pdf', pages=10, rights_template=template_id)
    cat = _rights.CAT_READER_KAT   # '02' — измерение «категория читателя» (50.mnu)
    api.rights.store.upsert(template_id,
                            period={'start': '20200101', 'end': '20301231'},
                            rules=[_rule(cat, KAT_STUDENT, '1'),
                                   _rule(cat, KAT_TEACHER, '2', limit='50'),
                                   _rule(cat, KAT_GUEST, '0')])
    return mfn


def fulltext_route_checks():
    print('-- fulltext: артефакты + уровень доступа через route() (публичный)')
    # Преподаватель (категория 2): download + лимит 50.
    api, _core = _api(categories={7: KAT_TEACHER})
    mfn = _seed_fulltext(api)
    H = _reader(api, ticket='111', rdr_mfn=7)
    st, p = api.route('GET', '/api/fulltext/IBIS/%d' % mfn, {}, None, H)
    check('GET /api/fulltext -> 200', st == 200)
    d = p['data']
    check('форма: db/mfn/artifacts/access',
          set(d.keys()) >= {'db', 'mfn', 'artifacts', 'access'})
    check('артефакты непусты (стор+каталог)', len(d['artifacts']) >= 2)
    check('артефакт несёт {kind,ref,pages,rightsTemplate}',
          all(set(a.keys()) == {'kind', 'ref', 'pages', 'rightsTemplate'}
              for a in d['artifacts']))
    check('955^B виден как rightsTemplate',
          any(a['rightsTemplate'] == 'R1' for a in d['artifacts']))
    check('преподаватель → level download', d['access']['level'] == 'download')
    check('преподаватель → pageLimit 50', d['access'].get('pageLimit') == 50)
    check('читатель → downloadBudget присутствует (квота 50 − 0 = 50)',
          d['access'].get('downloadBudget') == 50)

    # Студент (категория 1): только view, без download-квоты по правилу (view≠deny,
    # но ^F не задан → pageLimit None → downloadBudget None).
    api2, _ = _api(categories={8: KAT_STUDENT})
    mfn2 = _seed_fulltext(api2)
    Hs = _reader(api2, ticket='222', rdr_mfn=8)
    st, p = api2.route('GET', '/api/fulltext/IBIS/%d' % mfn2, {}, None, Hs)
    check('студент → level view', p['data']['access']['level'] == 'view')

    # «Гость-категория» (9) по правилу шаблона → deny.
    api3, _ = _api(categories={9: KAT_GUEST})
    mfn3 = _seed_fulltext(api3)
    Hg = _reader(api3, ticket='333', rdr_mfn=9)
    st, p = api3.route('GET', '/api/fulltext/IBIS/%d' % mfn3, {}, None, Hg)
    check('категория-гость по шаблону → level deny', p['data']['access']['level'] == 'deny')


def fulltext_guest_no_budget_checks():
    print('-- fulltext: гость — уровень по rights без LICH-квоты (ПДн)')
    api, _core = _api()
    # Запись БЕЗ 955^B → пустой шаблон → полный доступ (download), без квоты.
    mfn = api.catalog.save('IBIS', _rec('Открытый труд',
                                        **{'955': [{'a': 'open.pdf', 'n': '5'}]}))['mfn']
    H = _guest(api)
    st, p = api.route('GET', '/api/fulltext/IBIS/%d' % mfn, {}, None, H)
    check('гость на запись без шаблона -> 200', st == 200)
    check('пустой шаблон → level download (полный доступ)',
          p['data']['access']['level'] == 'download')
    check('гость → downloadBudget НЕ отдаётся (квота персональна, ПДн)',
          'downloadBudget' not in p['data']['access'])
    check('гость → артефакт виден', len(p['data']['artifacts']) == 1)


def fulltext_public_guard_and_degrade_checks():
    print('-- fulltext: public-db guard + мягкая деградация')
    api, _core = _api()
    # public-db guard: гость/читатель на непубличную БД → 403.
    for headers, who in ((_guest(api), 'guest'), (_reader(api), 'reader')):
        st, _ = api.route('GET', '/api/fulltext/RDR/1', {}, None, headers)
        check('%s на непубличную RDR -> 403' % who, st == 403)
    # Нет сессии → 401/403.
    st, _ = api.route('GET', '/api/fulltext/IBIS/1', {}, None, {})
    check('нет сессии -> 401/403', st in (401, 403))
    # Деградация: запись без артефактов ПТ → artifacts [], access безопасный (не 500).
    plain = api.catalog.save('IBIS', _rec('Без ПТ'))['mfn']
    st, p = api.route('GET', '/api/fulltext/IBIS/%d' % plain, {}, None, _guest(api))
    check('нет артефактов -> 200 artifacts []', st == 200 and p['data']['artifacts'] == [])
    check('нет шаблона → level download (безопасно, не 500)',
          p['data']['access']['level'] == 'download')
    # Деградация: irbis (чтение RDR категории) бросает — читатель всё равно не 500.
    api2, _ = _api(categories={7: KAT_TEACHER}, raise_on=('read_record',))
    mfn = _seed_fulltext(api2)
    st, p = api2.route('GET', '/api/fulltext/IBIS/%d' % mfn, {}, None,
                       _reader(api2, ticket='111', rdr_mfn=7))
    check('сбой чтения RDR-категории → не 500 (200)', st == 200)
    # Категория None → правило не совпало → deny по непустому шаблону.
    check('категория None при сбое → level deny (правила есть, совпадений нет)',
          p['data']['access']['level'] == 'deny')


# --------------------------------------------------------------------------- #
# 3. /api/bp/provision — быстрый отчёт ККО (staff-gate, форма, 404).
# --------------------------------------------------------------------------- #
def _seed_bp(api, students=100, copies=40):
    """Связка факультет→специальность→дисциплина + привязка литературы.

    Кко = copies/students. По умолчанию 40/100 = 0.4 (< норма 0.5 → дефицит)."""
    fid = api.bookprovision.add_faculty('ФВТ', name='Факультет ВТ')
    sid = api.bookprovision.add_specialty(fid, napr='09.03.01', spec='ИВТ')
    did = api.bookprovision.add_discipline(sid, 'D-1', name='Программирование',
                                           students=students)
    api.bookprovision.bind_literature(did, 'Учебник', kind=_bp.KIND_MAIN, copies=copies)
    return fid, sid, did


def bp_provision_route_checks():
    print('-- bp/provision: отчёт ККО через route() (staff)')
    api, _core = _api()
    fid, sid, did = _seed_bp(api, students=100, copies=40)
    H = _staff(api)

    # discipline scope → дефицит (Кко 0.4 < 0.5).
    st, p = api.route('GET', '/api/bp/provision', {'discipline': [str(did)]}, None, H)
    check('GET /api/bp/provision?discipline= -> 200', st == 200)
    d = p['data']
    check('scope=discipline эхо', d.get('scope') == 'discipline')
    check('coefficient = average_kko = 0.4', abs(d.get('coefficient') - 0.4) < 1e-9)
    check('status=deficit при Кко<норма', d.get('status') == 'deficit')
    check('shortfall = ceil(100*0.5)-40 = 10', d.get('shortfall') == 10)
    check('bindings проброшены (1 привязка)', len(d.get('bindings') or []) == 1)
    check('сырой отчёт-суперсет сохранён (average_kko присутствует)',
          'average_kko' in d)

    # specialty scope → status ok когда нет недообеспеченных (поднимем контингент).
    api.bookprovision.set_contingent(did, 50)   # 40/50 = 0.8 ≥ 0.5
    st, p = api.route('GET', '/api/bp/provision', {'specialty': [str(sid)]}, None, H)
    check('GET /api/bp/provision?specialty= -> 200', st == 200)
    check('scope=specialty эхо', p['data'].get('scope') == 'specialty')
    check('specialty status=ok когда нет дефицита', p['data'].get('status') == 'ok')

    # faculty scope → агрегат (provision_aggregate).
    st, p = api.route('GET', '/api/bp/provision', {'faculty': [str(fid)]}, None, H)
    check('GET /api/bp/provision?faculty= -> 200', st == 200)
    check('scope=faculty эхо', p['data'].get('scope') == 'faculty')
    check('faculty агрегат несёт coefficient', 'coefficient' in p['data'])

    # Неизвестный id → 404 (не 500).
    st, _ = api.route('GET', '/api/bp/provision', {'discipline': ['999999']}, None, H)
    check('неизвестная дисциплина -> 404', st == 404)
    st, _ = api.route('GET', '/api/bp/provision', {'specialty': ['999999']}, None, H)
    check('неизвестная специальность -> 404', st == 404)

    # Нет параметра scope → 400.
    st, _ = api.route('GET', '/api/bp/provision', {}, None, H)
    check('без discipline/specialty/faculty -> 400', st == 400)


def bp_provision_staff_gate_checks():
    print('-- bp/provision: staff-gate (не-staff → 403)')
    api, _core = _api()
    _f, _s, did = _seed_bp(api)
    # Гость и читатель — не staff: 403 на КО-функцию.
    for headers, who in ((_guest(api), 'guest'), (_reader(api), 'reader')):
        st, _ = api.route('GET', '/api/bp/provision', {'discipline': [str(did)]}, None, headers)
        check('%s на /api/bp/provision -> 403' % who, st == 403)
    # Нет сессии → 401/403.
    st, _ = api.route('GET', '/api/bp/provision', {'discipline': [str(did)]}, None, {})
    check('нет сессии на /api/bp/provision -> 401/403', st in (401, 403))
    # Staff допущен (gate не глухой).
    st, _ = api.route('GET', '/api/bp/provision', {'discipline': [str(did)]}, None, _staff(api))
    check('staff допущен к /api/bp/provision -> 200', st == 200)


def main():
    linked_route_checks()
    linked_public_guard_checks()
    fulltext_route_checks()
    fulltext_guest_no_budget_checks()
    fulltext_public_guard_and_degrade_checks()
    bp_provision_route_checks()
    bp_provision_staff_gate_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
