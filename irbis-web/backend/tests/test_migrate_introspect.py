#!/usr/bin/env python3
"""Тесты интроспекции источника + HTTP-эндпойнтов миграции (epic #223, #225).

Дополняют tests/test_migrate.py (тот покрывает сам перенос). Здесь проверяется:

  1. ИНТРОСПЕКЦИЯ (tools.migrate_irbis.introspect) на FakeIrbis с синтетическими
     записями, ВКЛЮЧАЯ нештатное доппole: перечисляет БД, для каждой отдаёт число
     записей и инвентарь полей; флаг ``custom`` стоит на нештатном поле (и на
     нештатном подполе штатного поля) и НЕ стоит на штатных.
  2. АДАПТИВНЫЙ экспорт: миграция переносит запись с доппolem БЕЗ потери —
     кастомное поле/подполе сохраняется в целевом каталоге (field-agnostic, не
     whitelist).
  3. ЛОКАЛЬНЫЙ адаптер: LocalSource поверх инжектированного адаптера приводит
     каноническую запись к parser-shape и работает с интроспекцией; при
     отсутствии tools.irbis_mst поднимается LocalAdapterUnavailable (graceful).
  4. ЭНДПОЙНТЫ через core.Api.route(): POST /api/admin/migrate/inspect и
     /api/admin/migrate/run работают для super-admin (200), отказывают
     reader/guest/не-админ-staff (403), а креды источника НЕ эхо-отражаются в
     ответе и НЕ попадают в аудит (только redacted host:port/user, без пароля).

Подключён в раннер test_access.py (модуль в списке). Standalone в стиле дома:
  py tests/test_migrate_introspect.py  -> ok ... + "N passed, M failed" + exit code.

НЕТ зависимости от живого сервера — всё на FakeIrbis / инжектированных стора́х.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS
from access.circulation import CirculationStore
from access.store import AccessStore
from access.catalog import CatalogStore

from tools.migrate_irbis import (
    Migrator, Targets, introspect, introspect_database, enumerate_databases,
    db_kind, is_custom_field, is_custom_subfield, parse_menu_pairs,
    canonical_to_parsed, LocalSource, LocalAdapterUnavailable,
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
# FakeIrbis с перечислением БД (list_databases) — синтетический источник для
# интроспекции. Запись — в parser-shape; коды подполей UPPER-case (как у живого).
# --------------------------------------------------------------------------- #
def _fld(tag, value=None, text='', subs=None):
    subs = subs or {}
    if value is None:
        value = ('^' + '^'.join('%s%s' % (k, v) for k, v in subs.items())) if subs else text
    return {'tag': tag, 'value': value, 'text': text, 'subfields': dict(subs)}


def _bib_with_custom(mfn, title):
    """Библиозапись со штатными полями (200/700/210/910) И нештатными:
    поле 996 (доппole целиком) + подполе 200^z (нештатное подполе штатного поля)."""
    return {'mfn': mfn, 'status': '', 'fields': [
        _fld('920', text='PAZK'),
        _fld('200', subs={'A': title, 'F': 'отв.', 'Z': 'локальное подполе'}),  # ^z custom
        _fld('700', subs={'A': 'Автор А.'}),
        _fld('210', subs={'A': 'СПб', 'D': '2020'}),
        _fld('910', subs={'A': '0', 'B': '777', 'D': 'ХР'}),
        _fld('996', subs={'Q': 'институтские данные'}),                         # доппole
        _fld('610', text='ключевое'),
    ]}


def _reader(mfn, ticket, surname):
    return {'mfn': mfn, 'status': '', 'fields': [
        _fld('30', text=ticket), _fld('920', text='RDR'),
        _fld('50', text='В01'), _fld('10', text=surname),
        _fld('555', text='нештатное читательское поле'),                        # доппole RDR
    ]}


class FakeIrbisError(Exception):
    pass


class FakeIrbis:
    """Источник с перечислением БД (list_databases) + чтением записей."""

    def __init__(self, dbs, names=None):
        # dbs: {code: [parser-record, …]}; names: {code: human-name}
        self._dbs = dbs
        self._names = names or {}

    def list_databases(self):
        return [{'code': code, 'name': self._names.get(code, code)} for code in self._dbs]

    def max_mfn(self, db):
        return len(self._dbs.get(db, []))

    def read_record(self, db, mfn):
        recs = self._dbs.get(db, [])
        if mfn < 1 or mfn > len(recs):
            raise FakeIrbisError('out of range')
        return recs[mfn - 1]

    def close(self):
        pass


def _fresh_targets():
    access = AccessStore(':memory:')
    catalog = CatalogStore(':memory:', access_store=access)
    circ = CirculationStore(':memory:')
    return Targets(catalog, circ, access, catalog_db='IBIS', tenant='public')


# --------------------------------------------------------------------------- #
# 1. Интроспекция: перечисление БД + инвентарь полей + флаг custom.
# --------------------------------------------------------------------------- #
def introspect_plan_checks():
    print('-- интроспекция: перечисление БД + инвентарь полей + флаг custom')
    src = FakeIrbis(
        {'IBIS': [_bib_with_custom(1, 'Первая'), _bib_with_custom(2, 'Вторая')],
         'RDR': [_reader(1, '111', 'Иванов'), _reader(2, '222', 'Петров')]},
        names={'IBIS': 'Электронный каталог', 'RDR': 'Читатели'})

    plan = introspect(src)
    check('план содержит databases', isinstance(plan.get('databases'), list))
    codes = {d['code'] for d in plan['databases']}
    check('перечислены обе БД (IBIS, RDR)', codes == {'IBIS', 'RDR'})

    ibis = next(d for d in plan['databases'] if d['code'] == 'IBIS')
    check('IBIS: имя из меню', ibis['name'] == 'Электронный каталог')
    check('IBIS: вид bib', ibis['kind'] == 'bib')
    check('IBIS: recordCount == 2', ibis['recordCount'] == 2)
    check('IBIS: нет readerCount', 'readerCount' not in ibis)

    by_tag = {f['tag']: f for f in ibis['fields']}
    check('инвентарь нашёл поле 200', '200' in by_tag)
    check('200 не помечено custom (штатное)', by_tag['200']['custom'] is False)
    check('200: частота по записям == 2', by_tag['200']['freq'] == 2)
    check('200: есть метка (label)', bool(by_tag['200'].get('label')))
    sub200 = {s['code']: s for s in by_tag['200']['subfields']}
    check('200^a не custom', sub200['a']['custom'] is False)
    check('200^z помечено custom (нештатное подполе штатного поля)',
          sub200['z']['custom'] is True)

    check('поле 996 присутствует в инвентаре', '996' in by_tag)
    check('996 помечено custom (доппole)', by_tag['996']['custom'] is True)
    check('996: частота == 2', by_tag['996']['freq'] == 2)
    # подполя кастомного поля отдельно НЕ помечаются (поле уже custom целиком)
    sub996 = {s['code']: s for s in by_tag['996']['subfields']}
    check('996^q НЕ помечено custom (поле уже custom целиком)',
          sub996['q']['custom'] is False)

    # RDR: вид rdr, readerCount, нештатное читательское поле помечено custom.
    rdr = next(d for d in plan['databases'] if d['code'] == 'RDR')
    check('RDR: вид rdr', rdr['kind'] == 'rdr')
    check('RDR: readerCount == 2', rdr.get('readerCount') == 2)
    rdr_by_tag = {f['tag']: f for f in rdr['fields']}
    check('RDR: поле 30 штатное (билет)', rdr_by_tag['30']['custom'] is False)
    check('RDR: поле 555 помечено custom (доппole)', rdr_by_tag['555']['custom'] is True)


def introspect_filter_checks():
    print('-- интроспекция: фильтр dbs ограничивает разбор подмножеством')
    src = FakeIrbis({'IBIS': [_bib_with_custom(1, 'X')],
                     'RDR': [_reader(1, '111', 'И')]})
    plan = introspect(src, dbs=['IBIS'])
    check('dbs=[IBIS] -> только IBIS в плане',
          [d['code'] for d in plan['databases']] == ['IBIS'])
    plan2 = introspect(src, dbs=['rdr'])    # регистронезависимо
    check('dbs=[rdr] (нижний регистр) -> только RDR',
          [d['code'] for d in plan2['databases']] == ['RDR'])


def introspect_unit_checks():
    print('-- интроспекция: юниты детектора custom + парсер меню')
    check('db_kind(RDR) == rdr', db_kind('RDR') == 'rdr')
    check('db_kind(IBIS) == bib', db_kind('IBIS') == 'bib')
    check('db_kind(неизвестная) == bib (дефолт)', db_kind('FOO') == 'bib')
    check('is_custom_field bib 200 -> False', is_custom_field('bib', '200') is False)
    check('is_custom_field bib 996 -> True', is_custom_field('bib', '996') is True)
    check('is_custom_subfield bib 200 a -> False',
          is_custom_subfield('bib', '200', 'a') is False)
    check('is_custom_subfield bib 200 z -> True',
          is_custom_subfield('bib', '200', 'z') is True)
    check('is_custom_subfield для кастомного поля -> False (не дублируем сигнал)',
          is_custom_subfield('bib', '996', 'q') is False)
    # парсер меню dbnam: пары код/имя, '*****' терминатор.
    pairs = parse_menu_pairs('IBIS\nКаталог\nRDR\nЧитатели\n*****\n')
    check('parse_menu_pairs -> 2 пары', len(pairs) == 2)
    check('parse_menu_pairs код/имя', pairs[0] == {'code': 'IBIS', 'name': 'Каталог'})


# --------------------------------------------------------------------------- #
# 2. Адаптивный экспорт: доппole переносится без потери.
# --------------------------------------------------------------------------- #
def adaptive_export_checks():
    print('-- адаптивный экспорт: доппole сохраняется при миграции')
    src = FakeIrbis({'IBIS': [_bib_with_custom(1, 'С доппolem')]})
    t = _fresh_targets()
    rep = Migrator(src, t).migrate_catalog(src_db='IBIS')
    check('запись загружена', rep['records_loaded'] == 1 and t.catalog.count('IBIS') == 1)
    # достать загруженную запись
    rec = None
    for mfn in t.catalog.list_mfns('IBIS'):
        rec = t.catalog.get('IBIS', mfn)
        break
    check('кастомное поле 996 сохранено в каталоге', rec is not None and '996' in rec)
    check('кастомное подполе 996^q сохранено',
          rec and rec['996'][0].get('q') == 'институтские данные')
    check('нештатное подполе 200^z сохранено',
          rec and any(inst.get('z') == 'локальное подполе' for inst in rec['200']))
    check('штатные поля тоже на месте (700^a)',
          rec and rec['700'][0].get('a') == 'Автор А.')


# --------------------------------------------------------------------------- #
# 3. Локальный адаптер: bridge каноническая -> parser-shape + graceful absence.
# --------------------------------------------------------------------------- #
class FakeMstAdapter:
    """Инжектируемый адаптер вида tools.irbis_mst (канонические записи)."""

    def __init__(self, dbs):
        # dbs: {code: [ {tag: [значение|{подполе: значение}]}, … ]}
        self._dbs = dbs

    def list_databases(self, path):
        return sorted(self._dbs)              # список кодов-строк, как реальный адаптер

    def max_mfn(self, path, db):
        return len(self._dbs.get(db, []))

    def read_records(self, path, db):
        for i, rec in enumerate(self._dbs.get(db, []), start=1):
            yield i, rec                       # (mfn, каноническая запись)


def local_source_checks():
    print('-- локальный адаптер: bridge + интроспекция через LocalSource')
    adapter = FakeMstAdapter({
        'IBIS': [
            {'200': [{'a': 'Локальная книга', 'z': 'нештатное'}],
             '700': [{'a': 'Локальный автор'}],
             '996': [{'q': 'доппole'}],
             '920': ['PAZK']},
        ],
    })
    src = LocalSource('/любой/путь', adapter=adapter)
    check('LocalSource.list_databases -> [{code,name}]',
          src.list_databases() == [{'code': 'IBIS', 'name': 'IBIS'}])
    check('LocalSource.max_mfn', src.max_mfn('IBIS') == 1)
    parsed = src.read_record('IBIS', 1)
    check('read_record отдаёт parser-shape (есть fields)',
          isinstance(parsed.get('fields'), list))
    tags = {f['tag'] for f in parsed['fields']}
    check('bridge сохранил все теги (вкл. доппole 996)', {'200', '700', '996', '920'} <= tags)

    # интроспекция поверх LocalSource распознаёт доппole.
    plan = introspect(src, dbs=['IBIS'])
    ibis = plan['databases'][0]
    by_tag = {f['tag']: f for f in ibis['fields']}
    check('LOCAL: 996 помечено custom', by_tag['996']['custom'] is True)
    sub200 = {s['code']: s for s in by_tag['200']['subfields']}
    check('LOCAL: 200^z помечено custom', sub200['z']['custom'] is True)


def canonical_bridge_checks():
    print('-- bridge: canonical_to_parsed сохраняет поля и подполя')
    rec = {'101': ['rus'], '200': [{'a': 'Заглавие', 'f': 'отв.'}],
           '910': [{'a': '0', 'b': '123'}, {'a': '1', 'b': '456'}]}
    parsed = canonical_to_parsed(5, rec, status='')
    check('mfn проброшен', parsed['mfn'] == 5)
    f200 = [f for f in parsed['fields'] if f['tag'] == '200'][0]
    check('200 подполя восстановлены', f200['subfields'].get('a') == 'Заглавие')
    f101 = [f for f in parsed['fields'] if f['tag'] == '101'][0]
    check('голое значение 101 как text', f101['text'] == 'rus')
    f910 = [f for f in parsed['fields'] if f['tag'] == '910']
    check('повторяющееся 910 -> 2 поля', len(f910) == 2)


def local_adapter_absent_checks():
    print('-- локальный адаптер: при отсутствии модуля — graceful (Unavailable)')
    import tools.migrate_irbis as _mig
    orig = _mig._load_local_adapter
    try:
        def _boom():
            raise LocalAdapterUnavailable('адаптер локального режима не готов')
        _mig._load_local_adapter = _boom
        raised = False
        try:
            LocalSource('/x')                  # без adapter -> вызовет _load_local_adapter
        except LocalAdapterUnavailable:
            raised = True
        check('LocalSource без готового адаптера -> LocalAdapterUnavailable', raised)
    finally:
        _mig._load_local_adapter = orig


# --------------------------------------------------------------------------- #
# 4. HTTP-эндпойнты через core.Api.route(): super-admin OK, прочие 403, креды
#    не эхо-отражаются и не попадают в аудит.
# --------------------------------------------------------------------------- #
SUPER_ADMIN_GRANTS = [
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]


def _api():
    os.environ['JWT_SECRET'] = 'migrate-introspect-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    os.environ['CATALOG_DB'] = ':memory:'
    os.environ['CIRC_DB'] = ':memory:'
    import importlib
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    return api, _core


def _super(api, login='super'):
    tok, _ = api._new_session('staff', login, SUPER_ADMIN_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _nonadmin(api, login='cat'):
    tok, _ = api._new_session('staff', login, NONADMIN_STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader_headers(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


def _patch_source(api):
    """Подменить tools.migrate_irbis.open_source синтетическим FakeIrbis, чтобы
    эндпойнты работали без живого сервера. Возвращает «холдер» с захваченными
    кредами, чтобы проверить, что пароль реально дошёл до открытия сессии (т.е.
    эндпойнт его использует), но при этом НЕ утёк в ответ/аудит."""
    import tools.migrate_irbis as _mig
    captured = {}
    fake = FakeIrbis(
        {'IBIS': [_bib_with_custom(1, 'Книга'), _bib_with_custom(2, 'Книга 2')],
         'RDR': [_reader(1, '111', 'Иванов')]},
        names={'IBIS': 'Каталог', 'RDR': 'Читатели'})
    orig = _mig.open_source

    def _fake_open(host, port, user, password, workstation='A', timeout=8.0):
        captured.update(host=host, port=port, user=user, password=password)
        return fake
    _mig.open_source = _fake_open
    return _mig, orig, captured


def inspect_endpoint_checks():
    print('-- эндпойнт POST /api/admin/migrate/inspect (super-admin)')
    api, _core = _api()
    _mig, orig, captured = _patch_source(api)
    try:
        H = _super(api)
        body = {'mode': 'network',
                'source': {'host': 'src.example', 'port': 6666,
                           'user': 'MIGRATE', 'pass': 'СЕКРЕТ-ПАРОЛЬ'}}
        st, p = api.route('POST', '/api/admin/migrate/inspect', {}, body, H)
        check('inspect -> 200', st == 200)
        dbs = p['data']['databases']
        check('inspect: перечислены БД', {d['code'] for d in dbs} == {'IBIS', 'RDR'})
        ibis = next(d for d in dbs if d['code'] == 'IBIS')
        check('inspect: IBIS recordCount == 2', ibis['recordCount'] == 2)
        check('inspect: 996 помечено custom',
              any(f['tag'] == '996' and f['custom'] for f in ibis['fields']))
        # КРЕДЫ: дошли до открытия сессии, но НЕ эхо-отражены в ответе.
        check('inspect: пароль реально использован (дошёл до open_source)',
              captured.get('password') == 'СЕКРЕТ-ПАРОЛЬ')
        import json as _json
        blob = _json.dumps(p, ensure_ascii=False)
        check('inspect: пароль НЕ в ответе', 'СЕКРЕТ-ПАРОЛЬ' not in blob)

        # КРЕДЫ: не попали в аудит (только redacted host/port/user, без пароля).
        audit = api.access.recent_audit(20)
        rec = next((a for a in audit
                    if (a.get('detail') or '{}') and 'migrate.inspect'
                    in (a['detail'] if isinstance(a['detail'], str) else _json.dumps(a['detail']))),
                   None)
        check('inspect: записан аудит migrate.inspect', rec is not None)
        detail_blob = rec['detail'] if isinstance(rec['detail'], str) else _json.dumps(rec['detail'], ensure_ascii=False)
        check('inspect: пароль НЕ в аудите', 'СЕКРЕТ-ПАРОЛЬ' not in detail_blob)
        check('inspect: в аудите есть host (redacted-описание)', 'src.example' in detail_blob)

        # bad_request: network без host.
        st, _ = api.route('POST', '/api/admin/migrate/inspect', {},
                          {'mode': 'network', 'source': {}}, H)
        check('inspect: network без host -> 400', st == 400)
        # неизвестный режим -> 400.
        st, _ = api.route('POST', '/api/admin/migrate/inspect', {},
                          {'mode': 'нечто', 'source': {}}, H)
        check('inspect: неизвестный mode -> 400', st == 400)
    finally:
        _mig.open_source = orig


def run_endpoint_checks():
    print('-- эндпойнт POST /api/admin/migrate/run (super-admin)')
    api, _core = _api()
    _mig, orig, captured = _patch_source(api)
    try:
        H = _super(api)
        # dry-run: читает + считает, НИЧЕГО не пишет.
        body = {'mode': 'network', 'tenant': 'public', 'dbs': ['IBIS', 'RDR'],
                'dryRun': True,
                'source': {'host': 'src.example', 'user': 'M', 'pass': 'P@ss'}}
        st, p = api.route('POST', '/api/admin/migrate/run', {}, body, H)
        check('run dry-run -> 200', st == 200)
        report = p['data']['report']
        check('run: report имеет 5 ключей',
              set(report) >= {'records_read', 'records_loaded', 'readers_loaded',
                              'skipped', 'errors'})
        check('run dry-run: would-load каталог (2)', report['records_loaded'] == 2)
        check('run dry-run: would-load читатель (1)', report['readers_loaded'] == 1)
        check('run dry-run: каталог пуст (ничего не записано)',
              api.catalog.count('IBIS') == 0)
        import json as _json
        check('run: пароль НЕ в ответе', 'P@ss' not in _json.dumps(p, ensure_ascii=False))

        # реальный прогон: записывает каталог + читателя, доппole сохранён.
        body['dryRun'] = False
        st, p = api.route('POST', '/api/admin/migrate/run', {}, body, H)
        check('run real -> 200', st == 200)
        check('run real: каталог загружен', api.catalog.count('IBIS') == 2)
        rec = api.catalog.get('IBIS', api.catalog.list_mfns('IBIS')[0])
        check('run real: доппole 996 сохранено в целевом каталоге',
              rec is not None and '996' in rec)
        # пароль не в аудите run.
        audit = api.access.recent_audit(30)
        runrec = next((a for a in audit if 'migrate.run'
                       in (a['detail'] if isinstance(a['detail'], str) else _json.dumps(a['detail']))),
                      None)
        check('run: записан аудит migrate.run', runrec is not None)
        db = runrec['detail'] if isinstance(runrec['detail'], str) else _json.dumps(runrec['detail'], ensure_ascii=False)
        check('run: пароль НЕ в аудите', 'P@ss' not in db)
    finally:
        _mig.open_source = orig


def migrate_local_notready_checks():
    print('-- эндпойнт: local при неготовом адаптере -> 503 not_ready')
    api, _core = _api()
    import tools.migrate_irbis as _mig
    orig = _mig._load_local_adapter

    def _boom():
        raise _mig.LocalAdapterUnavailable('адаптер локального режима ещё не готов')
    _mig._load_local_adapter = _boom
    try:
        H = _super(api)
        st, p = api.route('POST', '/api/admin/migrate/inspect', {},
                          {'mode': 'local', 'source': {'path': 'C:/IRBIS64/Datai'}}, H)
        check('inspect local (адаптер не готов) -> 503', st == 503)
        check('inspect local: код ошибки not_ready',
              p.get('error', {}).get('code') == 'not_ready')
        check('inspect local: сообщение по-русски «не готов»',
              'не готов' in p.get('error', {}).get('message', ''))
    finally:
        _mig._load_local_adapter = orig


def migrate_auth_checks():
    print('-- авторизация: reader/guest/не-админ-staff -> 403 на эндпойнтах миграции')
    api, _core = _api()
    _mig, orig, _cap = _patch_source(api)
    routes = [
        ('POST', '/api/admin/migrate/inspect',
         {'mode': 'network', 'source': {'host': 'h'}}),
        ('POST', '/api/admin/migrate/run',
         {'mode': 'network', 'tenant': 'public', 'source': {'host': 'h'}, 'dryRun': True}),
    ]
    try:
        for label, headers in (('reader', _reader_headers(api)), ('guest', _guest(api)),
                               ('не-админ-staff', _nonadmin(api))):
            for m, path, b in routes:
                st, _ = api.route(m, path, {}, b, headers)
                check('%s -> 403 на %s' % (label, path), st == 403)
        # без сессии -> 401/403, не 200.
        for m, path, b in routes:
            st, _ = api.route(m, path, {}, b, {})
            check('без сессии -> 401/403 на %s' % path, st in (401, 403))
        # super-admin допущен (контроль, что гард не блокирует всех).
        st, _ = api.route('POST', '/api/admin/migrate/inspect', {},
                          {'mode': 'network', 'source': {'host': 'h'}}, _super(api))
        check('super-admin допущен к inspect (200)', st == 200)
    finally:
        _mig.open_source = orig


def main():
    introspect_plan_checks()
    introspect_filter_checks()
    introspect_unit_checks()
    adaptive_export_checks()
    local_source_checks()
    canonical_bridge_checks()
    local_adapter_absent_checks()
    inspect_endpoint_checks()
    run_endpoint_checks()
    migrate_local_notready_checks()
    migrate_auth_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
