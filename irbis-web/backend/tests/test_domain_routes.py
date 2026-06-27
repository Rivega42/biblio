#!/usr/bin/env python3
"""HTTP-route-тесты разводки own-store домен-модулей в core.Api.route().

Закрывает (через РЕАЛЬНЫЙ ``core.Api.route()``, тот же путь, что server.py):
  * **10.1 ИРИ/SDI** — /api/sdi/profile|profiles|run|new (reader-scoped): профиль
    постоянного запроса, переигрывание против каталога, НОВЫЕ попадания,
    идемпотентность, владение профилем (чужой -> 404), гость -> 401/403.
  * **8.1/8.2 Сводный каталог SK** — /api/union/ingest (staff) + /api/union/search:
    свод по сигле, дедуп по ISBN (две библиотеки -> 1 запись, 2 сиглы), поиск;
    запись только staff (reader/guest -> 403).
  * **11.3 Диспетч уведомлений** — /api/admin/notifications/dispatch (admin):
    прогон очереди в каналы (InApp), не-admin -> 403.
  * **3.1 Реестр читателя** — circulation.reader_record резолвит читателя как
    ЗАПИСЬ через подключённый reader_registry (а не строку-id).

Standalone (дом-стиль): py -3.12 tests/test_domain_routes.py
Вписан в раннер tests/test_access.py (module_checks).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.catalog import CatalogStore
from access import seed_vocab
from access import notifications as _nt
from access.sdi import SdiService, SdiStore
from access.union import UnionCatalog, UnionStore
from access.reader_registry import ReaderRegistry, ReaderStore
from access.notify_dispatch import DispatchWorker

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


READER_G = [{'function': 'cabinet', 'db': '*', 'level': 'read'},
            {'function': 'search', 'db': '*', 'level': 'read'}]
STAFF_G = [{'function': 'cataloging', 'db': '*', 'level': 'write'},
           {'function': 'search', 'db': '*', 'level': 'read'}]
ADMIN_G = [{'function': 'admin', 'db': '*', 'level': 'admin'}]


def _api():
    os.environ['JWT_SECRET'] = 'domain-routes-test'
    os.environ['ACCESS_DB'] = ':memory:'
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = None
    seed_vocab.seed_vocabularies(api.access, from_catalog=False)
    api.catalog = CatalogStore(':memory:', access_store=api.access)
    # Свежие in-memory домен-сторы; circ перецепляем на тестовый реестр.
    api.sdi = SdiService(SdiStore(':memory:'), catalog=api.catalog)
    api.union = UnionCatalog(UnionStore(':memory:'))
    api.reader_registry = ReaderRegistry(ReaderStore(':memory:'))
    if api.circulation is not None:
        api.circulation.reader_registry = api.reader_registry
    api.notifications = _nt.NotificationQueue(':memory:')
    api.dispatch_worker = DispatchWorker(api.notifications)
    return api


def _sess(api, kind, login, grants, rdr_mfn=None):
    tok, _ = api._new_session(kind, login, grants, tenant='public', rdr_mfn=rdr_mfn)
    return {'authorization': 'Bearer ' + tok}


def _reader(api, ticket='111', rdr_mfn=1):
    return _sess(api, 'reader', 'RI=%s' % ticket, READER_G, rdr_mfn=rdr_mfn)


def _rec(title, **extra):
    base = {'920': 'PAZK', '200': [{'a': title}], '700': [{'a': 'Автор'}],
            '610': [{'': 'тест'}], '101': 'rus'}
    base.update(extra)
    return base


# --------------------------------------------------------------------------- #
# 10.1 — ИРИ/SDI через route().
# --------------------------------------------------------------------------- #
def sdi_route_checks():
    print('-- 10.1 ИРИ/SDI: профиль/прогон/новые через route()')
    api = _api()
    R = _reader(api, ticket='111')
    # каталог с записью под запрос T=Театр
    api.catalog.save('IBIS', _rec('Театр и жизнь'))

    st, p = api.route('POST', '/api/sdi/profile',
                      {}, {'name': 'театр', 'db': 'IBIS', 'query': 'K=тест'}, R)
    check('POST /api/sdi/profile -> 200', st == 200)
    pid = p['data']['profile']['id']
    check('профиль создан с id', isinstance(pid, int))

    st, p = api.route('GET', '/api/sdi/profiles', {}, None, R)
    check('GET /api/sdi/profiles -> 1', st == 200 and len(p['data']['items']) == 1)

    st, p = api.route('POST', '/api/sdi/run', {}, {'id': pid}, R)
    check('run -> 200', st == 200)
    check('run нашёл НОВОЕ попадание', len(p['data']['new']) == 1)

    st, p = api.route('POST', '/api/sdi/run', {}, {'id': pid}, R)
    check('повторный run идемпотентен (new пуст)', p['data']['new'] == [])

    st, p = api.route('GET', '/api/sdi/new', {}, None, R)
    check('GET /api/sdi/new несёт попадание', st == 200 and len(p['data']['items']) == 1)

    # владение: чужой читатель не удалит профиль
    R2 = _reader(api, ticket='222', rdr_mfn=2)
    st, p = api.route('POST', '/api/sdi/profile/remove', {}, {'id': pid}, R2)
    check('чужой remove -> 404', st == 404)
    st, p = api.route('POST', '/api/sdi/profile/remove', {}, {'id': pid}, R)
    check('свой remove -> 200', st == 200 and p['data']['removed'] is True)

    # гость (без сессии) -> 401/403
    st, p = api.route('GET', '/api/sdi/profiles', {}, None, {})
    check('гость на SDI -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# 8.1/8.2 — Сводный каталог SK через route().
# --------------------------------------------------------------------------- #
def union_route_checks():
    print('-- 8.1/8.2 Сводный каталог: ingest (staff) + search')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    rec = {'10': {'a': '978-5-0001-1'}, '200': {'a': 'Чайка'}, '210': {'d': '2018'}}

    st, p = api.route('POST', '/api/union/ingest',
                      {}, {'record': rec, 'sigla': 'SPB-1', 'db': 'IBIS', 'mfn': 1}, S)
    check('ingest #1 -> 200', st == 200)
    check('ingest #1 merged=False (новая сводная)', p['data']['merged'] is False)

    st, p = api.route('POST', '/api/union/ingest',
                      {}, {'record': rec, 'sigla': 'SPB-2', 'db': 'IBIS', 'mfn': 7}, S)
    check('ingest #2 (тот же ISBN) merged=True', p['data']['merged'] is True)

    st, p = api.route('GET', '/api/union/search', {'q': ['Чайка']}, None, S)
    check('search -> 200, 1 сводная', st == 200 and p['data']['total'] == 1)
    item = p['data']['items'][0]
    check('сводная несёт 2 сиглы держателей',
          set(item['siglas']) == {'SPB-1', 'SPB-2'})

    # reader/guest не может ingest (staff write)
    R = _reader(api)
    st, p = api.route('POST', '/api/union/ingest',
                      {}, {'record': rec, 'sigla': 'X', 'mfn': 9}, R)
    check('reader ingest -> 403', st == 403)
    st, p = api.route('POST', '/api/union/ingest',
                      {}, {'record': rec, 'sigla': 'X', 'mfn': 9}, {})
    check('гость ingest -> 401/403', st in (401, 403))
    # reader МОЖЕТ искать по сводному
    st, p = api.route('GET', '/api/union/search', {'q': ['Чайка']}, None, R)
    check('reader search -> 200', st == 200 and p['data']['total'] == 1)


# --------------------------------------------------------------------------- #
# 11.3 — Диспетч уведомлений через route() (admin).
# --------------------------------------------------------------------------- #
def dispatch_route_checks():
    print('-- 11.3 Диспетч уведомлений: /api/admin/notifications/dispatch (admin)')
    api = _api()
    A = _sess(api, 'staff', 'root', ADMIN_G)
    # поставить уведомление в очередь с inapp-предпочтением (внешние каналы OFF,
    # доставка идёт во всегда-доступный inapp — что и проверяем у воркера).
    api.notifications.enqueue('hold_ready', 'R1',
                              {'ref': 1, 'item': 'BK-1', 'hold_until': 999},
                              prefs=_nt.Preferences(default_channels=['inapp']))

    st, p = api.route('POST', '/api/admin/notifications/dispatch', {}, {}, A)
    check('dispatch -> 200', st == 200)
    check('сводка несёт ключи', set(p['data'].keys())
          >= {'processed', 'sent', 'failed', 'retried'})
    check('доставлено >=1 (через inapp)', p['data']['sent'] >= 1)

    # идемпотентность: второй прогон осевшей очереди — 0 sent
    st, p = api.route('POST', '/api/admin/notifications/dispatch', {}, {}, A)
    check('второй dispatch: 0 sent', p['data']['sent'] == 0)

    # не-admin (reader) -> 403
    R = _reader(api)
    st, p = api.route('POST', '/api/admin/notifications/dispatch', {}, {}, R)
    check('reader dispatch -> 403', st == 403)


# --------------------------------------------------------------------------- #
# 3.1 — circulation.reader_record резолвит читателя как ЗАПИСЬ.
# --------------------------------------------------------------------------- #
def reader_record_checks():
    print('-- 3.1 circulation.reader_record: читатель как запись, не строка-id')
    api = _api()
    if api.circulation is None:
        check('circulation доступен', False)
        return
    api.reader_registry.register('111', category='В01', full_name='Иванов Иван',
                                 email='i@x.ru')
    rec = api.circulation.reader_record('111')
    check('reader_record вернул профиль-запись', isinstance(rec, dict))
    check('профиль несёт ФИО', rec.get('full_name') == 'Иванов Иван')
    check('профиль несёт категорию', rec.get('category') == 'В01')
    check('профиль несёт контакты', rec.get('email') == 'i@x.ru')
    # неизвестный в реестре -> деградация к базовой строке circ-стора
    api.circulation.store.add_reader('222', category='Д01')
    base = api.circulation.reader_record('222')
    check('fallback к базовой строке reader', base is not None and base.get('id') == '222')


def main():
    sdi_route_checks()
    union_route_checks()
    dispatch_route_checks()
    reader_record_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
