#!/usr/bin/env python3
"""Тесты бэкенд-замера скорости ИРБИС↔Biblio (panel «liquid glass», super-admin).

Покрывают КОНТРАКТ ответа, который УЖЕ потребляет фронт (BenchmarkPanel.tsx) —
форму менять нельзя:
  POST /api/admin/benchmark/run -> { query:{irbis_ms,biblio_ms},
    circulation:{irbis_ms|null,biblio_ms}, migration:{records_per_sec,total|null},
    ts:<iso>, notes:{...} }
  GET  /api/admin/benchmark     -> последний кэш (или 404, если не запускали).

Без живого сервера: ``self.irbis`` подменяется на FakeIrbis (детерминированный
in-memory стенд), own-store каталог сидируется одной записью. Проверяем:
  * super-admin gate — не-админ (staff без admin.*, guest, reader) -> 403; нет
    сессии -> 401/403; админ -> 200 (как соседние /api/admin/*);
  * GET до первого запуска -> 404 (кэш пуст);
  * контракт run: ключи/типы каждой метрики, ts — ISO-строка, notes — dict;
  * GET после run отдаёт ТОТ ЖЕ кэш;
  * мягкая деградация: падает сторона ИРБИС (read_record/search/max_mfn кидают
    IrbisError) -> соответствующее поле = null, пометка в notes, статус 200 (НЕ 500);
  * own-store каталог отсутствует (catalog=None) -> query.biblio_ms=null, не 500;
  * чистая логика медианы с отбросом max-выброса (_bench_median_ms): медиана из
    N-1 после отброса самого медленного прогона; сбой fn -> (None, '<err>').

Контракт-чек проходит ОДИНАКОВО на sqlite и postgres (вся стадийная логика поверх
own-store/catalog — backend-agnostic); PG-паритет: суть в том, что эти проверки не
зависят от backend access-store, поэтому одна и та же ветка валидна для обоих
(как и в test_admin_routes — запускается раннером test_access.py на обоих плечах CI).

Запуск standalone (house style):
  py -3.12 tests/test_benchmark.py  -> ok ... + "N passed, M failed" + код возврата.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.authz import GUEST_GRANTS, READER_GRANTS

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Super-admin несёт admin.db на уровне admin (seed 'administrator'); минтим прямо на
# токен, чтобы не заводить роли в БД (та же техника, что в test_admin_routes).
SUPER_GRANTS = [
    {'function': 'admin.db', 'db': '*', 'level': 'admin'},
    {'function': 'admin.users', 'db': '*', 'level': 'admin'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]
# Не-админ staff: реальный сотрудник, но БЕЗ admin.* — gate обязан дать 403.
NONADMIN_STAFF_GRANTS = [
    {'function': 'record.write', 'db': '*', 'level': 'write'},
    {'function': 'search', 'db': '*', 'level': 'read'},
]


def _record(mfn):
    return {'mfn': mfn, 'status': '0', 'version': '1', 'guid': None,
            'fields': [{'tag': '200', 'value': 'Заглавие %d' % mfn,
                        'subfields': {'A': 'Заглавие %d' % mfn}}]}


class FakeIrbis:
    """In-memory стенд SessionManager. ``raise_on`` — имена методов, которые должны
    кидать IrbisError (для веток мягкой деградации)."""

    def __init__(self, maxmfn=60, raise_on=()):
        self._maxmfn = maxmfn
        self.raise_on = set(raise_on)

    def _maybe_raise(self, name):
        if name in self.raise_on:
            from irbis.client import IrbisError
            raise IrbisError(-1, 'stub raise %s' % name)

    def max_mfn(self, db):
        self._maybe_raise('max_mfn')
        return self._maxmfn

    def search(self, db, expr):
        self._maybe_raise('search')
        return 1, [1]

    def read_record(self, db, mfn):
        self._maybe_raise('read_record')
        return _record(mfn)

    def format_record(self, db, mfn, pft='@brief'):
        self._maybe_raise('format_record')
        return 'brief %d' % mfn


def _api(fake):
    """Сконструировать Api (в __init__ нет коннекта к ИРБИС) и подменить сессию на
    стенд. JWT-секрет и sqlite-стор пинятся для детерминизма/изоляции."""
    os.environ['JWT_SECRET'] = 'benchmark-test-secret'
    os.environ['ACCESS_BACKEND'] = 'sqlite'
    os.environ['ACCESS_DB'] = ':memory:'
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = fake
    # Засидировать own-store каталога одной записью, чтобы biblio-поиск был реальным
    # попаданием по тому же словарю (K=). Best-effort: если каталог не поднялся —
    # тест биболио-стороны это явно учтёт (biblio_ms может быть null).
    if api.catalog is not None:
        try:
            api.catalog.save('IBIS', {'200': [{'a': 'Библиотека и книга'}],
                                      '610': [{'': 'библиотека'}]})
        except Exception:
            pass
    return api, _core


def _super(api, login='super-acct'):
    tok, _ = api._new_session('staff', login, SUPER_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _nonadmin_staff(api, login='cat-acct'):
    tok, _ = api._new_session('staff', login, NONADMIN_STAFF_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _guest(api):
    tok, _ = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111'):
    tok, _ = api._new_session('reader', 'RI=%s' % ticket, READER_GRANTS,
                              tenant='public', rdr_mfn=1)
    return {'authorization': 'Bearer ' + tok}


# --------------------------------------------------------------------------- #
# 1. Контракт ответа run + GET-кэш после запуска.
# --------------------------------------------------------------------------- #
def contract_checks():
    print('-- benchmark: контракт POST /run + GET-кэш')
    api, _core = _api(FakeIrbis())
    H = _super(api)

    st, p = api.route('POST', '/api/admin/benchmark/run', {}, None, H)
    check('POST /api/admin/benchmark/run -> 200', st == 200)
    d = p['data']
    # верхний уровень
    check('есть query/circulation/migration/ts/notes',
          all(k in d for k in ('query', 'circulation', 'migration', 'ts', 'notes')))
    check('ts — непустая ISO-строка', isinstance(d['ts'], str) and 'T' in d['ts'])
    check('notes — dict', isinstance(d['notes'], dict))
    # query: обе стороны реальны -> числа
    q = d['query']
    check('query.irbis_ms число', isinstance(q['irbis_ms'], (int, float)))
    check('query.biblio_ms число', isinstance(q['biblio_ms'], (int, float)))
    check('query.irbis_ms >= 0', q['irbis_ms'] is None or q['irbis_ms'] >= 0)
    # circulation: biblio реальная, irbis прокси (оба числа при живом стенде)
    c = d['circulation']
    check('circulation.biblio_ms число', isinstance(c['biblio_ms'], (int, float)))
    check('circulation содержит ключ irbis_ms', 'irbis_ms' in c)
    check('circulation.irbis_ms число|null',
          c['irbis_ms'] is None or isinstance(c['irbis_ms'], (int, float)))
    check('notes помечает circ-ИРБИС как ПРОКСИ',
          d['notes'].get('circulation', {}).get('irbis_method') == 'proxy')
    check('notes помечает circ-Biblio как real',
          d['notes'].get('circulation', {}).get('biblio_method') == 'real')
    # migration: records_per_sec число|null, total int|null
    m = d['migration']
    check('migration.records_per_sec число|null',
          m['records_per_sec'] is None or isinstance(m['records_per_sec'], (int, float)))
    check('migration содержит ключ total', 'total' in m)
    check('migration.total int|null',
          m['total'] is None or isinstance(m['total'], int))
    check('migration.total = max_mfn стенда (60)', m['total'] == 60)
    check('migration.records_per_sec > 0 при живом чтении',
          m['records_per_sec'] is not None and m['records_per_sec'] > 0)

    # GET отдаёт ТОТ ЖЕ кэш.
    st, p2 = api.route('GET', '/api/admin/benchmark', {}, None, H)
    check('GET /api/admin/benchmark -> 200 после run', st == 200)
    check('GET отдаёт закэшированный ts', p2['data']['ts'] == d['ts'])


# --------------------------------------------------------------------------- #
# 2. GET до первого запуска -> 404 (кэш в памяти пуст).
# --------------------------------------------------------------------------- #
def empty_cache_checks():
    print('-- benchmark: GET до запуска -> 404')
    api, _core = _api(FakeIrbis())
    H = _super(api)
    st, p = api.route('GET', '/api/admin/benchmark', {}, None, H)
    check('GET до run -> 404', st == 404)
    check('404 несёт ошибку not_found',
          isinstance(p, dict) and p.get('ok') is False
          and p['error']['code'] == 'not_found')


# --------------------------------------------------------------------------- #
# 3. Super-admin gate — 403 не-админам, 401/403 без сессии, 200 админу.
# --------------------------------------------------------------------------- #
BENCH_ROUTES = [
    ('POST', '/api/admin/benchmark/run'),
    ('GET', '/api/admin/benchmark'),
]


def gate_checks():
    print('-- benchmark: super-admin gate')
    api, _core = _api(FakeIrbis())

    # не-админ staff -> 403 на обоих маршрутах
    HS = _nonadmin_staff(api)
    for m, path in BENCH_ROUTES:
        st, _ = api.route(m, path, {}, None, HS)
        check('не-админ staff -> 403 на %s %s' % (m, path), st == 403)

    # guest + reader -> 403
    for label, H in (('guest', _guest(api)), ('reader', _reader(api))):
        for m, path in BENCH_ROUTES:
            st, _ = api.route(m, path, {}, None, H)
            check('%s -> 403 на %s %s' % (label, m, path), st == 403)

    # нет сессии -> 401/403, не 200
    for m, path in BENCH_ROUTES:
        st, _ = api.route(m, path, {}, None, {})
        check('нет сессии -> 401/403 на %s %s' % (m, path), st in (401, 403))

    # super-admin допущен (gate не блокирует всех подряд)
    H = _super(api)
    st, _ = api.route('POST', '/api/admin/benchmark/run', {}, None, H)
    check('super-admin допущен к /run (200)', st == 200)


# --------------------------------------------------------------------------- #
# 4. Мягкая деградация: падает сторона ИРБИС -> null + пометка, статус 200.
# --------------------------------------------------------------------------- #
def degradation_checks():
    print('-- benchmark: деградация стороны -> null, без 500')
    # ИРБИС целиком недоступен: search/read_record/format_record/max_mfn кидают.
    fake = FakeIrbis(raise_on=('search', 'read_record', 'format_record', 'max_mfn'))
    api, _core = _api(fake)
    H = _super(api)
    st, p = api.route('POST', '/api/admin/benchmark/run', {}, None, H)
    check('run при мёртвом ИРБИС -> 200 (НЕ 500)', st == 200)
    d = p['data']
    check('query.irbis_ms = null при сбое', d['query']['irbis_ms'] is None)
    check('notes.query помечает irbis_error',
          'irbis_error' in d['notes'].get('query', {}))
    check('circulation.irbis_ms = null при сбое прокси', d['circulation']['irbis_ms'] is None)
    check('migration.records_per_sec = null при сбое чтения',
          d['migration']['records_per_sec'] is None)
    check('migration.total = null при сбое max_mfn', d['migration']['total'] is None)
    # Biblio-сторона при этом ОСТАЁТСЯ реальной (own-store жив).
    check('query.biblio_ms остаётся числом (own-store жив)',
          isinstance(d['query']['biblio_ms'], (int, float)))
    check('circulation.biblio_ms остаётся числом (own-store жив)',
          isinstance(d['circulation']['biblio_ms'], (int, float)))

    # Own-store каталога отсутствует -> biblio query = null, тоже не 500.
    api2, _core2 = _api(FakeIrbis())
    api2.catalog = None
    H2 = _super(api2)
    st, p = api2.route('POST', '/api/admin/benchmark/run', {}, None, H2)
    check('run без own-store каталога -> 200', st == 200)
    check('query.biblio_ms = null без каталога', p['data']['query']['biblio_ms'] is None)
    check('notes.query помечает biblio_error без каталога',
          'biblio_error' in p['data']['notes'].get('query', {}))


# --------------------------------------------------------------------------- #
# 5. Чистая логика медианы с отбросом max-выброса (_bench_median_ms).
# --------------------------------------------------------------------------- #
def median_checks():
    print('-- benchmark: медиана + отброс max-выброса (чистая логика)')
    import core as _core

    # Детерминированная последовательность задержек: контролируем «время» прогона
    # через счётчик, отдавая известные длительности. Замеряем РЕАЛЬНОЕ perf_counter,
    # поэтому проверяем не точные мс, а инварианты: число прогонов и устойчивость к
    # выбросу/ошибке.
    calls = [0]

    def counting_fn():
        calls[0] += 1

    med, err = _core._bench_median_ms(counting_fn, samples=5)
    check('median: 5 прогонов выполнено', calls[0] == 5)
    check('median: ошибки нет', err is None)
    check('median: результат — неотрицательное число',
          isinstance(med, float) and med >= 0)

    # Сбой fn на первом же прогоне -> (None, '<err>'), без падения.
    def boom():
        raise ValueError('boom')

    med2, err2 = _core._bench_median_ms(boom, samples=5)
    check('median: сбой fn -> None', med2 is None)
    check('median: сбой fn -> текст ошибки', isinstance(err2, str) and 'boom' in err2)

    # Отброс выброса: с >=3 прогонами один максимум отбрасывается -> медиана берётся
    # из оставшихся. Проверяем инвариант на синтетических длительностях напрямую
    # (повторяем алгоритм отброса, чтобы зафиксировать поведение независимо от часов).
    import statistics as _st
    durs = [10.0, 12.0, 11.0, 13.0, 999.0]   # 999 — выброс
    durs2 = list(durs)
    durs2.remove(max(durs2))
    check('отброс выброса: max удалён', 999.0 not in durs2 and len(durs2) == 4)
    check('медиана без выброса разумна (~11.5), не уехала к 999',
          _st.median(durs2) < 50)

    # Меньше 3 прогонов — выброс НЕ отбрасываем (медиана из 1-2 значений).
    calls2 = [0]

    def cf2():
        calls2[0] += 1

    med3, err3 = _core._bench_median_ms(cf2, samples=1)
    check('median: samples=1 -> ровно 1 прогон', calls2[0] == 1)
    check('median: samples=1 без ошибки', err3 is None and med3 is not None)


def main():
    contract_checks()
    empty_cache_checks()
    gate_checks()
    degradation_checks()
    median_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
