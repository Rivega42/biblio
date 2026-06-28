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
from access.vkr import VkrService, VkrStore
from access.ksu_auto import KsuAutoService, KsuAutoStore
from access.serials import SerialsService, SerialsStore
from access.dam import DamRegistry, DamStore
from access.suppliers import SupplierService, SupplierStore
from access.subscription import SubscriptionService, SubscriptionStore
from access.catalog_versions import VersionService, VersionStore
from access.vocab_editor import VocabEditor, VocabStore
from access.roles import RoleService, RoleStore
from access.audit_trail import AuditService, AuditStore
from access.config_store import ConfigService, ConfigStore
from access.loan_policy import LoanPolicyService, LoanPolicyStore
from access.debtors import DebtorsService, DebtStore
from access.discipline_norms import DisciplineNormService, DisciplineStore
from access.kko_reports import KkoSnapshotStore
from access.ocr import OcrService, OcrStore
from access.exhibits import ExhibitService, ExhibitStore
from access.metadata_templates import TemplateService, TemplateStore
from access.job_queue import JobQueue, JobStore
from access.collection_subs import CollectionSubscriptionService, CollectionSubStore
from access.facet_config import FacetService, FacetConfigStore
from access.ip_auth import IpAuthService, IpRangeStore
from access.tariff_store import TariffStore
from access import access_matrix as _am
from access import circulation as _circ

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
# Расширенный staff-набор для разводки бэклога (#316/#317/#318): каталогизация +
# поступление/чтение комплектования (поставщики/подписка гвардятся acq-токенами).
STAFF_BL_G = [{'function': 'cataloging', 'db': '*', 'level': 'write'},
              {'function': 'acq.read', 'db': '*', 'level': 'read'},
              {'function': 'acq.receipt', 'db': '*', 'level': 'write'},
              {'function': 'search', 'db': '*', 'level': 'read'}]
# Книговыдача (circ.issue) + Книгообеспеченность (bp.read/bp.write) для PR #320-разводки.
STAFF_CIRC_G = [{'function': 'circ.issue', 'db': '*', 'level': 'write'},
                {'function': 'bp.read', 'db': '*', 'level': 'read'},
                {'function': 'bp.write', 'db': '*', 'level': 'write'},
                {'function': 'search', 'db': '*', 'level': 'read'}]


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
    api.vkr = VkrService(VkrStore(':memory:'))
    api.ksu_auto = KsuAutoService(KsuAutoStore(':memory:'))
    api.serials = SerialsService(SerialsStore(':memory:'))
    api.dam = DamRegistry(DamStore(':memory:'))
    # Разводка бэклога (#316/#317/#318) — свежие in-memory сторы.
    api.suppliers = SupplierService(SupplierStore(':memory:'))
    api.subscription = SubscriptionService(SubscriptionStore(':memory:'))
    api.catalog_versions = VersionService(VersionStore(':memory:'))
    api.vocab_editor = VocabEditor(VocabStore(':memory:'))
    api.roles = RoleService(RoleStore(':memory:'))
    api.audit_trail = AuditService(AuditStore(':memory:'))
    api.config = ConfigService(ConfigStore(':memory:'))
    # PR #320-разводка: Книговыдача (политики/должники) + Книгообеспеченность.
    api.loan_policy = LoanPolicyService(LoanPolicyStore(':memory:'))
    api.debtors = DebtorsService(DebtStore(':memory:'))
    api.discipline_norms = DisciplineNormService(DisciplineStore(':memory:'))
    api.kko_snapshots = KkoSnapshotStore(':memory:')
    # Трек «Оцифровка» (PR #325) — свежие in-memory сторы.
    api.ocr = OcrService(OcrStore(':memory:'))
    api.exhibits = ExhibitService(ExhibitStore(':memory:'))
    # Батч #240 — свежие in-memory сторы. job_queue/collection_subs с фикс. now
    # для детерминизма (FIFO по id; подписки активны на фиксированную «сегодня»).
    api.metadata_templates = TemplateService(TemplateStore(':memory:'))
    api.job_queue = JobQueue(JobStore(':memory:'))
    api.collection_subs = CollectionSubscriptionService(
        CollectionSubStore(':memory:', now=lambda: '2026-06-28T00:00:00+00:00'),
        now=lambda: '2026-06-28T00:00:00+00:00')
    # Батч #240 (2-я волна) — свежие in-memory сторы.
    api.facets_cfg = FacetService(FacetConfigStore(':memory:'))
    api.ip_auth = IpAuthService(IpRangeStore(':memory:'))
    # Матрица доступов (#331) — свежий in-memory стор тарифов + сид дефолтов.
    api.tariffs = TariffStore(':memory:')
    _am.seed_defaults(api.tariffs)
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


# --------------------------------------------------------------------------- #
# Батч-2 разводка: ВКР / КСУ-авто / периодика / DAM через route().
# --------------------------------------------------------------------------- #
def vkr_route_checks():
    print('-- 7.6/8.3 ВКР: submit (reader) + review (staff)')
    api = _api()
    R = _reader(api)
    st, p = api.route('POST', '/api/vkr', {},
                      {'title': 'Театр XX века', 'author': 'Студент', 'faculty': 'ФКН'}, R)
    check('POST /api/vkr -> 200', st == 200)
    vid = p['data']['vkr']['id']
    check('ВКР создан (submitted)', p['data']['vkr']['status'] == 'submitted')
    S = _sess(api, 'staff', 'cat', STAFF_G)
    api.vkr.set_antiplagiat(vid, 85)
    st, p = api.route('POST', '/api/vkr/review', {}, {'id': vid, 'approve': True}, S)
    check('review approve -> approved',
          st == 200 and p['data']['ok'] is True
          and p['data']['vkr']['status'] == 'approved')
    st, p = api.route('GET', '/api/vkr', {'status': ['approved']}, None, S)
    check('GET /api/vkr (staff) -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('POST', '/api/vkr/review', {}, {'id': vid}, R)
    check('reader review -> 403', st == 403)


def ksu_route_checks():
    print('-- 5.3 КСУ авто-распределение (staff)')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    items = [{'section': 'A', 'doc_type': 'book', 'language': 'rus', 'printed': True, 'copies': 3},
             {'section': 'B', 'doc_type': 'book', 'language': 'eng', 'printed': True, 'copies': 2}]
    st, p = api.route('POST', '/api/ksu/distribute', {}, {'items': items}, S)
    check('distribute -> 200', st == 200)
    check('titles == 2', p['data']['titles'] == 2)
    check('copies == 5', p['data']['copies'] == 5)
    st, p = api.route('POST', '/api/ksu/distribute', {}, {'ksuNo': 'K-1', 'items': items}, S)
    check('compute_and_store сохранил', st == 200 and api.ksu_auto.get('K-1') is not None)
    R = _reader(api)
    st, p = api.route('POST', '/api/ksu/distribute', {}, {'items': items}, R)
    check('reader distribute -> 403', st == 403)


def serials_route_checks():
    print('-- 9.2/9.3 Периодика (register/issue/search)')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    st, p = api.route('POST', '/api/serials', {},
                      {'kind': 'journal', 'title': 'Театральный журнал', 'issn': '1234-5678'}, S)
    check('register journal -> 200', st == 200)
    sid = p['data']['serial']['id']
    st, p = api.route('POST', '/api/serials/issue', {},
                      {'serialId': sid, 'number': 1, 'year': 2023}, S)
    check('add_issue -> 200', st == 200)
    st, p = api.route('GET', '/api/serials/search', {'q': ['Театральный']}, None, S)
    check('search -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('POST', '/api/serials', {}, {'kind': 'bogus', 'title': 'X'}, S)
    check('неизвестный kind -> 400', st == 400)
    R = _reader(api)
    st, p = api.route('POST', '/api/serials', {}, {'kind': 'journal', 'title': 'Y'}, R)
    check('reader register -> 403', st == 403)
    st, p = api.route('GET', '/api/serials/search', {'q': ['Театральный']}, None, R)
    check('reader search -> 200', st == 200)


def dam_route_checks():
    print('-- 7.1 DAM/файлы (attach/assets)')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    st, p = api.route('POST', '/api/dam/attach', {},
                      {'db': 'IBIS', 'mfn': 10, 'kind': '951', 'ref': 'http://x/f.pdf'}, S)
    check('attach 951 -> 200', st == 200)
    st, p = api.route('POST', '/api/dam/attach', {},
                      {'db': 'IBIS', 'mfn': 10, 'kind': '955', 'ref': 'f.pdf',
                       'pages': 120, 'rightsTemplate': 'R1'}, S)
    check('attach 955 -> 200', st == 200)
    R = _reader(api)
    st, p = api.route('GET', '/api/dam', {'db': ['IBIS'], 'mfn': ['10']}, None, R)
    check('GET /api/dam -> 2 ассета', st == 200 and len(p['data']['items']) == 2)
    st, p = api.route('POST', '/api/dam/attach', {},
                      {'db': 'IBIS', 'mfn': 10, 'kind': '951', 'ref': 'x'}, R)
    check('reader attach -> 403', st == 403)


# --------------------------------------------------------------------------- #
# Разводка бэклога #316 — Комплектование: поставщики/счета + подписка.
# --------------------------------------------------------------------------- #
def backlog_acq_route_checks():
    print('-- #316 Комплектование: поставщики/счета + подписка через route()')
    api = _api()
    S = _sess(api, 'staff', 'lib', STAFF_BL_G)

    st, p = api.route('POST', '/api/acq/supplier', {},
                      {'name': 'Лань', 'inn': '7700'}, S)
    check('POST /api/acq/supplier -> 200', st == 200)
    sid = p['data']['supplier']['id']
    check('поставщик с id', isinstance(sid, int))

    st, p = api.route('GET', '/api/acq/suppliers', {}, None, S)
    check('GET /api/acq/suppliers -> 1 + stats', st == 200
          and len(p['data']['items']) == 1 and 'stats' in p['data'])

    st, p = api.route('POST', '/api/acq/supplier/invoice', {},
                      {'supplierId': sid, 'number': 'INV-1', 'amount': 100,
                       'ksuNo': 'КСУ-7'}, S)
    check('POST supplier/invoice -> 200', st == 200 and p['data']['invoice'])

    st, p = api.route('POST', '/api/acq/supplier/invoice', {},
                      {'supplierId': 999999, 'number': 'X', 'amount': 1}, S)
    check('счёт неизвестному поставщику -> 400', st == 400)

    st, p = api.route('POST', '/api/acq/subscription', {},
                      {'title': 'Вестник', 'issn': '1234-5678', 'copies': 2}, S)
    check('POST /api/acq/subscription -> 200', st == 200)
    subid = p['data']['subscription']['id']
    check('подписка с id', isinstance(subid, int))

    st, p = api.route('GET', '/api/acq/subscriptions', {}, None, S)
    check('GET /api/acq/subscriptions -> 1', st == 200
          and len(p['data']['items']) == 1)

    # write только staff: гость -> 401/403
    st, p = api.route('POST', '/api/acq/supplier', {}, {'name': 'X'}, {})
    check('гость на supplier -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# Разводка бэклога #316/#317 — Каталогизатор: MARC/MARCXML/дедуп/печать/версии/
# редактор словарей.
# --------------------------------------------------------------------------- #
def backlog_cataloging_route_checks():
    print('-- #316/#317 Каталогизатор: обмен/дедуп/печать/версии/словари')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_BL_G)
    rec = _rec('Театр и время', **{'10': [{'a': '978-5-0001'}]})
    # ISO2709-чистая запись (только именованные подполя) — _rec кладёт 610 с
    # ПУСТЫМ кодом подполя {'': …}, что валидно для MARCXML, но ISO2709 так не
    # кодирует (пустой код ломает round-trip; через роут это вернуло бы 400).
    mrec = {'920': 'PAZK', '200': [{'a': 'Театр и время'}],
            '700': [{'a': 'Автор'}], '101': 'rus', '10': [{'a': '978-5-0001'}]}

    # MARC ISO2709 round-trip (base64)
    st, p = api.route('POST', '/api/cataloging/marc/export', {},
                      {'records': [mrec]}, S)
    check('marc/export -> base64', st == 200 and p['data']['iso2709_b64'])
    b64 = p['data']['iso2709_b64']
    st, p = api.route('POST', '/api/cataloging/marc/import', {},
                      {'iso2709_b64': b64}, S)
    check('marc/import round-trip 1 запись', st == 200 and p['data']['count'] == 1)

    # MARCXML round-trip
    st, p = api.route('POST', '/api/cataloging/marcxml/export', {},
                      {'records': [rec]}, S)
    check('marcxml/export -> XML', st == 200 and '<' in p['data']['marcxml'])
    xml = p['data']['marcxml']
    st, p = api.route('POST', '/api/cataloging/marcxml/import', {},
                      {'marcxml': xml}, S)
    check('marcxml/import round-trip', st == 200 and p['data']['count'] == 1)

    # дедуп
    st, p = api.route('POST', '/api/cataloging/dedup', {},
                      {'records': [rec, rec]}, S)
    check('dedup -> кластер дублей', st == 200 and len(p['data']['clusters']) >= 1)
    st, p = api.route('POST', '/api/cataloging/dedup/check', {},
                      {'record': rec, 'existing': [rec]}, S)
    check('dedup/check -> дубль', st == 200 and p['data']['duplicate'] is True)

    # печать ГОСТ
    st, p = api.route('POST', '/api/cataloging/print', {},
                      {'records': [rec], 'form': 'card'}, S)
    check('print card -> текст', st == 200 and len(p['data']['text']) > 0)

    # версии записи
    st, p = api.route('POST', '/api/cataloging/versions/snapshot', {},
                      {'db': 'IBIS', 'mfn': 5, 'record': rec}, S)
    check('versions/snapshot -> v1', st == 200 and p['data']['version'] == 1)
    st, p = api.route('POST', '/api/cataloging/versions/snapshot', {},
                      {'db': 'IBIS', 'mfn': 5, 'record': rec}, S)
    check('versions/snapshot -> v2', st == 200 and p['data']['version'] == 2)
    st, p = api.route('GET', '/api/cataloging/versions',
                      {'db': ['IBIS'], 'mfn': ['5']}, None, S)
    check('versions history -> 2', st == 200 and len(p['data']['items']) == 2)
    st, p = api.route('POST', '/api/cataloging/versions/revert', {},
                      {'db': 'IBIS', 'mfn': 5, 'version': 1}, S)
    check('versions/revert -> record', st == 200 and p['data']['record'])
    st, p = api.route('POST', '/api/cataloging/versions/revert', {},
                      {'db': 'IBIS', 'mfn': 5, 'version': 99}, S)
    check('revert несуществующей -> 404', st == 404)

    # редактор словарей .mnu / деревьев .tre
    st, p = api.route('POST', '/api/cataloging/vocab/value', {},
                      {'vocab': 'v900', 'code': 'a', 'label': 'Книга'}, S)
    check('vocab/value add -> 200', st == 200 and p['data']['value'])
    st, p = api.route('GET', '/api/cataloging/vocab', {'vocab': ['v900']}, None, S)
    check('vocab values -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('POST', '/api/cataloging/tree/node', {},
                      {'tree': 'rubr', 'code': 'r', 'label': 'Корень'}, S)
    check('tree/node add корень -> 200', st == 200 and p['data']['node'])
    st, p = api.route('POST', '/api/cataloging/tree/node', {},
                      {'tree': 'rubr', 'code': 'c1', 'label': 'Раздел',
                       'parentCode': 'r'}, S)
    check('tree/node add потомок -> 200', st == 200)
    st, p = api.route('GET', '/api/cataloging/tree',
                      {'tree': ['rubr'], 'parent': ['r']}, None, S)
    check('tree children(r) -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('POST', '/api/cataloging/tree/node', {},
                      {'tree': 'rubr', 'code': 'x', 'label': 'Y',
                       'parentCode': 'НЕТ'}, S)
    check('tree/node с несуществ. родителем -> 400', st == 400)


# --------------------------------------------------------------------------- #
# Разводка бэклога #318 — Администратор: роли RBAC + аудит-трейл + конфиг.
# --------------------------------------------------------------------------- #
def backlog_admin_route_checks():
    print('-- #318 Администратор: RBAC + аудит-трейл + конфиг через route()')
    api = _api()
    A = _sess(api, 'staff', 'adm', ADMIN_G)
    S = _sess(api, 'staff', 'lib', STAFF_BL_G)

    st, p = api.route('POST', '/api/admin/rbac/role', {},
                      {'name': 'editor', 'description': 'каталогизатор'}, A)
    check('rbac/role create -> 200', st == 200)
    rid = p['data']['role']['id']
    st, p = api.route('POST', '/api/admin/rbac/grant', {},
                      {'role': rid, 'function': 'record.write', 'level': 'write'}, A)
    check('rbac/grant -> 200', st == 200 and p['data']['grant'])
    st, p = api.route('POST', '/api/admin/rbac/assign', {},
                      {'account': 'u1', 'role': rid}, A)
    check('rbac/assign -> 200', st == 200 and p['data']['assigned'])
    st, p = api.route('GET', '/api/admin/rbac/effective',
                      {'account': ['u1']}, None, A)
    check('rbac/effective -> 1 грант', st == 200 and len(p['data']['grants']) == 1)
    st, p = api.route('GET', '/api/admin/rbac/roles', {}, None, A)
    check('rbac/roles -> 1', st == 200 and len(p['data']['items']) == 1)

    # аудит-трейл (наполняем через сервис, читаем через роут)
    api.audit_trail.record('adm', 'config.set', 'config', 'opac.title',
                           status='ok')
    api.audit_trail.record('lib', 'record.write', 'record', '42', status='denied')
    st, p = api.route('GET', '/api/admin/audit-trail', {}, None, A)
    check('audit-trail entries -> 2 + summary', st == 200
          and len(p['data']['items']) == 2 and 'summary' in p['data'])
    st, p = api.route('GET', '/api/admin/audit-trail',
                      {'status': ['denied']}, None, A)
    check('audit-trail фильтр status=denied -> 1', st == 200
          and len(p['data']['items']) == 1)

    # конфиг-параметры
    st, p = api.route('POST', '/api/admin/config', {},
                      {'key': 'opac.title', 'value': 'СПб ГТБ'}, A)
    check('config set -> 200', st == 200 and p['data']['param']['value'] == 'СПб ГТБ')
    st, p = api.route('POST', '/api/admin/config', {},
                      {'key': 'opac.perPage', 'value': 20, 'type': 'int'}, A)
    check('config set typed int -> 200', st == 200
          and p['data']['param']['value'] == 20)
    st, p = api.route('GET', '/api/admin/config', {}, None, A)
    check('config list -> 2', st == 200 and len(p['data']['items']) == 2)
    st, p = api.route('POST', '/api/admin/config', {},
                      {'key': 'x', 'value': 'нечисло', 'type': 'int'}, A)
    check('config неверный тип -> 400', st == 400)

    # admin-гейт: staff без admin-гранта -> 401/403
    st, p = api.route('GET', '/api/admin/rbac/roles', {}, None, S)
    check('staff на rbac/roles -> 401/403', st in (401, 403))
    st, p = api.route('POST', '/api/admin/config', {}, {'key': 'k', 'value': 'v'}, S)
    check('staff на config set -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# Разводка бэклога #318 — Утилиты: стат/экспорт/дубли/ФЛК-lite над выборкой.
# db_utils работает над моделью записи {'mfn','fields':[{'tag','value'|'subfields'}]}.
# --------------------------------------------------------------------------- #
def backlog_utils_route_checks():
    print('-- #318 Утилиты: стат/экспорт/дубли/валидация через route()')
    api = _api()
    S = _sess(api, 'staff', 'util', STAFF_BL_G)

    def urec(mfn, isbn):
        return {'mfn': mfn, 'fields': [
            {'tag': '920', 'value': 'PAZK'},
            {'tag': '101', 'subfields': [{'code': 'a', 'value': 'rus'}]},
            {'tag': '210', 'subfields': [{'code': 'd', 'value': '2021'}]},
            {'tag': '10', 'subfields': [{'code': 'a', 'value': isbn}]},
            {'tag': '910', 'subfields': [{'code': 'a', 'value': '0'},
                                         {'code': 'd', 'value': 'ХР'}]}]}
    recs = [urec(1, '978-5-1'), urec(2, '978-5-1'), urec(3, '978-5-2')]

    st, p = api.route('POST', '/api/utils/stats', {}, {'records': recs}, S)
    check('utils/stats -> count 3', st == 200 and p['data']['stats']['count'] == 3)
    check('utils/stats fund экземпляры', 'total_exemplars' in p['data']['fund'])

    st, p = api.route('POST', '/api/utils/export', {},
                      {'records': recs, 'format': 'json'}, S)
    check('utils/export json', st == 200 and p['data']['format'] == 'json')
    st, p = api.route('POST', '/api/utils/export', {},
                      {'records': recs, 'format': 'csv', 'fields': ['10^a', '920']}, S)
    check('utils/export csv c заголовком', st == 200
          and p['data']['format'] == 'csv' and '10^a' in p['data']['data'])

    st, p = api.route('POST', '/api/utils/duplicates', {},
                      {'records': recs, 'tag': '10^a'}, S)
    check('utils/duplicates по ISBN -> 1 дубль-ключ', st == 200
          and len(p['data']['duplicates']) == 1)

    st, p = api.route('POST', '/api/utils/validate', {},
                      {'records': recs, 'required': ['200']}, S)
    check('utils/validate флагует отсутствие 200', st == 200
          and p['data']['ok'] is False and len(p['data']['invalid']) == 3)
    st, p = api.route('POST', '/api/utils/validate', {},
                      {'records': recs, 'required': ['920']}, S)
    check('utils/validate проходит при 920', st == 200 and p['data']['ok'] is True)


# --------------------------------------------------------------------------- #
# Разводка #320 — Книговыдача: политики выдачи + должники/санкции.
# --------------------------------------------------------------------------- #
def backlog_circ_route_checks():
    print('-- #320 Книговыдача: политики выдачи + должники через route()')
    api = _api()
    S = _sess(api, 'staff', 'circ', STAFF_CIRC_G)

    st, p = api.route('POST', '/api/circ/policy', {},
                      {'readerCategory': 'STD', 'docType': '*',
                       'loanDays': 10, 'maxItems': 1, 'finePerDay': 500}, S)
    check('POST /api/circ/policy -> 200', st == 200 and p['data']['policy'])
    st, p = api.route('GET', '/api/circ/policies', {}, None, S)
    check('GET /api/circ/policies -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('GET', '/api/circ/policy/resolve',
                      {'category': ['STD'], 'docType': ['BK']}, None, S)
    check('resolve -> max_items 1 (matched category)', st == 200
          and p['data']['policy']['max_items'] == 1)

    st, p = api.route('POST', '/api/circ/debt', {},
                      {'reader': 'RDR1', 'item': 'BK-1', 'kind': 'overdue',
                       'dueDate': '2026-06-01', 'asOf': '2026-06-15',
                       'finePerDay': 500}, S)
    check('debt overdue -> amount 7000 (14дн*500)', st == 200
          and p['data']['debt']['amount_kopecks'] == 7000)
    st, p = api.route('POST', '/api/circ/debt', {},
                      {'reader': 'RDR1', 'item': 'BK-2', 'kind': 'lost',
                       'amount': 30000}, S)
    check('debt lost -> 200', st == 200 and p['data']['debt']['kind'] == 'lost')
    st, p = api.route('GET', '/api/circ/debts', {'reader': ['RDR1']}, None, S)
    check('reader debts total 37000', st == 200
          and p['data']['debts']['total'] == 37000)
    st, p = api.route('POST', '/api/circ/block/evaluate', {},
                      {'reader': 'RDR1', 'thresholdKopecks': 10000}, S)
    check('block/evaluate -> block', st == 200
          and p['data']['state']['level'] == 'block')
    st, p = api.route('GET', '/api/circ/blocks', {}, None, S)
    check('blocks -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('GET', '/api/circ/debts', {}, None, S)
    check('debtors report readers_with_debt 1', st == 200
          and p['data']['report']['readers_with_debt'] == 1)
    did = api.debtors.reader_debts('RDR1')['items'][0]['id']
    st, p = api.route('POST', '/api/circ/debt/settle', {}, {'debtId': did}, S)
    check('debt settle -> True', st == 200 and p['data']['settled'] is True)

    # write только staff: гость -> 401/403
    st, p = api.route('POST', '/api/circ/policy', {},
                      {'readerCategory': 'X', 'docType': '*',
                       'loanDays': 1, 'maxItems': 1}, {})
    check('гость на policy set -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# Разводка #320 — Книгообеспеченность: нормы РПД + ККО-аналитика.
# --------------------------------------------------------------------------- #
def backlog_bp_route_checks():
    print('-- #320 Книгообеспеченность: нормы РПД + ККО через route()')
    api = _api()
    S = _sess(api, 'staff', 'bp', STAFF_CIRC_G)

    st, p = api.route('POST', '/api/bp/rpd/discipline', {},
                      {'code': 'D1', 'name': 'Матанализ',
                       'department': 'Кафедра ВМ', 'contingent': 50}, S)
    check('POST /api/bp/rpd/discipline -> 200', st == 200
          and p['data']['discipline']['code'] == 'D1')
    st, p = api.route('POST', '/api/bp/rpd/norm', {},
                      {'disciplineCode': 'D1', 'editionRef': 'BK-100',
                       'normPerStudent': 0.5}, S)
    check('POST /api/bp/rpd/norm -> 200', st == 200 and p['data']['norm'])
    st, p = api.route('GET', '/api/bp/rpd/required', {'code': ['D1']}, None, S)
    check('required = ceil(50*0.5)=25', st == 200
          and p['data']['items'][0]['required'] == 25 and p['data']['total'] == 25)
    st, p = api.route('GET', '/api/bp/rpd/disciplines', {}, None, S)
    check('disciplines -> 1', st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('POST', '/api/bp/rpd/norm', {},
                      {'disciplineCode': 'НЕТ', 'editionRef': 'X',
                       'normPerStudent': 1.0}, S)
    check('норматив неизвестной дисциплине -> 400', st == 400)

    disc = [{'discipline': 'Матанализ', 'department': 'ВМ', 'students': 50,
             'exemplars': 10, 'norm_per_student': 0.5},
            {'discipline': 'Физика', 'department': 'Физ', 'students': 40,
             'exemplars': 0, 'norm_per_student': 0.5}]
    st, p = api.route('POST', '/api/bp/kko/report', {}, {'disciplines': disc}, S)
    check('kko report summary 2 + by_department + worst', st == 200
          and p['data']['summary']['disciplines'] == 2
          and 'by_department' in p['data'] and 'worst' in p['data'])
    st, p = api.route('POST', '/api/bp/kko/snapshot', {},
                      {'period': '2026-H1', 'disciplines': disc}, S)
    check('kko snapshot save -> 200', st == 200 and p['data']['snapshot'])

    # bp.write только staff: гость -> 401/403
    st, p = api.route('POST', '/api/bp/rpd/discipline', {},
                      {'code': 'Z', 'name': 'Z'}, {})
    check('гость на bp/rpd/discipline -> 401/403', st in (401, 403))


# --------------------------------------------------------------------------- #
# Ребро 11.4 — внешняя loan_policy + debtors ПЕРЕОПРЕДЕЛЯЮТ лимиты circulation.
# --------------------------------------------------------------------------- #
def edge_11_4_checks():
    print('-- 11.4: loan_policy/debtors -> CirculationEngine.checkout')
    lp = LoanPolicyService(LoanPolicyStore(':memory:'))
    lp.set_policy('STD', '*', loan_days=10, max_items=1)   # понижает STD 15 -> 1
    dbt = DebtorsService(DebtStore(':memory:'))
    eng = _circ.CirculationEngine(store=_circ.CirculationStore(':memory:'),
                                  loan_policy=lp, debtors=dbt)
    eng.store.add_reader('R9', category='STD')
    T = 1000000
    check('1-я выдача ALLOW', eng.checkout('R9', 'A', T).decision == _circ.ALLOW)
    d2 = eng.checkout('R9', 'B', T)
    check('2-я выдача упёрлась в ВНЕШНИЙ лимит max_items=1 (не встроенные 15)',
          d2.decision in (_circ.REQUIRE_OVERRIDE, _circ.DENY)
          and 'limit_exceeded' in d2.reasons)

    # back-compat: без loan_policy STD=15 -> 2-я выдача проходит
    eng2 = _circ.CirculationEngine(store=_circ.CirculationStore(':memory:'))
    eng2.store.add_reader('R8', category='STD')
    eng2.checkout('R8', 'X1', T)
    check('back-compat: без политики 2-я выдача ALLOW (встроенный STD=15)',
          eng2.checkout('R8', 'X2', T).decision == _circ.ALLOW)

    # должник-блок -> жёсткий DENY (не override-абельный)
    dbt.register_lost('R9', 'L', 50000)
    dbt.evaluate_block('R9', threshold_kopecks=10000)
    d3 = eng.checkout('R9', 'C', T)
    check('должник-блок -> DENY reader_blocked_debt',
          d3.decision == _circ.DENY and 'reader_blocked_debt' in d3.reasons)


def digitization_route_checks():
    print('-- Оцифровка: выставки / IIIF / OCR / OAI-PMH через route()')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    R = _reader(api)

    # --- Виртуальные выставки: черновик -> позиция -> публикация -> витрина ---
    st, p = api.route('POST', '/api/exhibits', {},
                      {'slug': 'teatr-1920', 'title': 'Театр 1920-х',
                       'description': 'Афиши и программы'}, S)
    check('создать выставку -> 200',
          st == 200 and p['data']['exhibit']['slug'] == 'teatr-1920')
    st, p = api.route('GET', '/api/exhibits', {}, None, R)
    check('витрина пуста (черновик не виден) -> 0',
          st == 200 and len(p['data']['items']) == 0)
    st, p = api.route('GET', '/api/exhibits/teatr-1920', {}, None, R)
    check('view черновика (reader) -> 404', st == 404)
    st, p = api.route('POST', '/api/exhibits/item', {},
                      {'slug': 'teatr-1920', 'db': 'IBIS', 'mfn': 5,
                       'caption': 'Афиша «Чайки»', 'assetRef': 'dam://a1'}, S)
    check('добавить позицию -> 200',
          st == 200 and p['data']['item']['mfn'] == 5)
    st, p = api.route('POST', '/api/exhibits/publish', {},
                      {'slug': 'teatr-1920', 'published': True}, S)
    check('публикация -> 200',
          st == 200 and p['data']['exhibit']['published'] == 1)
    st, p = api.route('GET', '/api/exhibits', {}, None, R)
    check('витрина: 1 опубликованная (public-read)',
          st == 200 and len(p['data']['items']) == 1)
    st, p = api.route('GET', '/api/exhibits/teatr-1920', {}, None, R)
    check('view опубликованной -> 200 + 1 позиция',
          st == 200 and len(p['data']['items']) == 1
          and p['data']['exhibit']['slug'] == 'teatr-1920')
    # Гварды + валидация выставок.
    st, p = api.route('POST', '/api/exhibits', {}, {'slug': 'x', 'title': 'X'}, R)
    check('reader создаёт выставку -> 403', st == 403)
    st, p = api.route('POST', '/api/exhibits', {}, {'title': 'без-слага'}, S)
    check('создание без slug -> 400', st == 400)
    st, p = api.route('POST', '/api/exhibits', {},
                      {'slug': 'teatr-1920', 'title': 'dup'}, S)
    check('дубликат slug -> 400', st == 400)
    st, p = api.route('POST', '/api/exhibits/publish', {}, {'slug': 'нет'}, S)
    check('публикация неизвестной -> 404', st == 404)
    st, p = api.route('POST', '/api/exhibits/item', {},
                      {'slug': 'нет', 'mfn': 1}, S)
    check('позиция в неизвестную выставку -> 400', st == 400)

    # --- OCR: индексация (staff) + поиск (public-read) ---
    st, p = api.route('POST', '/api/ocr/index', {},
                      {'assetRef': 'dam://doc1',
                       'pages': [{'page_no': 1, 'text': 'Чайка Антона Чехова'},
                                 {'page_no': 2, 'text': 'Вишнёвый сад пьеса'}]}, S)
    check('OCR index -> 2 страницы',
          st == 200 and p['data']['indexed'] == 2 and p['data']['pageCount'] == 2)
    st, p = api.route('GET', '/api/ocr/search', {'q': ['чехов']}, None, R)
    check('OCR search по всем (public, кириллица/регистр) -> 1 хит',
          st == 200 and len(p['data']['hits']) == 1
          and p['data']['hits'][0]['asset_ref'] == 'dam://doc1')
    st, p = api.route('GET', '/api/ocr/search',
                      {'q': ['сад'], 'assetRef': ['dam://doc1']}, None, R)
    check('OCR search в документе -> 1 (page 2)',
          st == 200 and len(p['data']['hits']) == 1
          and p['data']['hits'][0]['page_no'] == 2)
    st, p = api.route('GET', '/api/ocr/search', {'q': ['']}, None, R)
    check('OCR search пустой q -> []',
          st == 200 and p['data']['hits'] == [])
    st, p = api.route('POST', '/api/ocr/index', {}, {'pages': []}, S)
    check('OCR index без assetRef -> 400', st == 400)
    st, p = api.route('POST', '/api/ocr/index', {},
                      {'assetRef': 'd', 'pages': []}, R)
    check('reader OCR index -> 403', st == 403)

    # --- IIIF: манифест Presentation v3 из DAM-ассетов записи ---
    api.dam.attach('IBIS', 5, '955', 'http://img/doc5', pages=3,
                   rights_template='R1')
    st, p = api.route('GET', '/api/iiif/manifest',
                      {'db': ['IBIS'], 'mfn': ['5']}, None, R)
    man = p['data']['manifest']
    check('IIIF manifest -> v3 + 3 канвы',
          st == 200 and man['type'] == 'Manifest' and '@context' in man
          and len(man['items']) == 3 and p['data']['pages'] == 3)
    check('IIIF canvas -> painting-аннотация на образ страницы',
          man['items'][0]['items'][0]['items'][0]['body']['id']
          == 'http://img/doc5/1')
    st, p = api.route('GET', '/api/iiif/manifest',
                      {'db': ['IBIS'], 'mfn': ['99']}, None, R)
    check('IIIF без ассетов -> манифест без канв',
          st == 200 and len(p['data']['manifest']['items']) == 0)
    st, p = api.route('GET', '/api/iiif/manifest',
                      {'db': ['IBIS'], 'mfn': ['0']}, None, R)
    check('IIIF без mfn -> 400', st == 400)

    # --- OAI-PMH: провайдер метаданных (анонимный харвестер) ---
    api.catalog.save('IBIS', _rec('Чайка', **{'700': [{'a': 'Чехов А.П.'}],
                                              '210': [{'c': 'Искусство', 'd': '1980'}]}))
    st, p = api.route('GET', '/api/oai', {'verb': ['Identify']}, None, {})
    check('OAI Identify (anon) -> 200 v2.0',
          st == 200 and p['data']['Identify']['protocolVersion'] == '2.0')
    st, p = api.route('GET', '/api/oai', {'verb': ['ListMetadataFormats']},
                      None, {})
    check('OAI ListMetadataFormats -> oai_dc',
          st == 200
          and p['data']['ListMetadataFormats'][0]['metadataPrefix'] == 'oai_dc')
    st, p = api.route('GET', '/api/oai', {'verb': ['ListRecords']}, None, {})
    check('OAI ListRecords -> >=1 + DC-маппинг',
          st == 200 and len(p['data']['ListRecords']) >= 1
          and p['data']['ListRecords'][0]['metadata']['title'] == 'Чайка'
          and p['data']['ListRecords'][0]['metadata']['creator'] == 'Чехов А.П.')
    st, p = api.route('GET', '/api/oai', {'verb': ['ListIdentifiers']}, None, {})
    check('OAI ListIdentifiers -> >=1', st == 200
          and len(p['data']['ListIdentifiers']) >= 1)
    ident = p['data']['ListIdentifiers'][0]['identifier']
    st, p = api.route('GET', '/api/oai',
                      {'verb': ['GetRecord'], 'identifier': [ident]}, None, {})
    check('OAI GetRecord по identifier -> запись',
          st == 200
          and p['data']['GetRecord']['header']['identifier'] == ident)
    st, p = api.route('GET', '/api/oai',
                      {'verb': ['GetRecord'], 'identifier': ['oai:biblio:99999']},
                      None, {})
    check('OAI GetRecord неизвестный id -> 404', st == 404)
    st, p = api.route('GET', '/api/oai',
                      {'verb': ['ListRecords'], 'metadataPrefix': ['marc21']},
                      None, {})
    check('OAI неподдерживаемый формат -> 400', st == 400)
    st, p = api.route('GET', '/api/oai', {'verb': ['Bogus']}, None, {})
    check('OAI неизвестный verb -> 400', st == 400)


def batch240_route_checks():
    print('-- Батч #240: шаблоны метаданных / очередь задач / подписки через route()')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    A = _sess(api, 'staff', 'adm', ADMIN_G)
    R = _reader(api)

    # --- Шаблоны метаданных (Каталогизатор) ---
    st, p = api.route('GET', '/api/cataloging/templates', {}, None, S)
    check('типы шаблонов -> >=5 встроенных', st == 200 and len(p['data']['items']) >= 5)
    st, p = api.route('GET', '/api/cataloging/template', {'type': ['book']}, None, S)
    check('skeleton book -> 200 + 200 required',
          st == 200 and p['data']['type'] == 'book'
          and any(f['tag'] == '200' and f['required'] for f in p['data']['fields']))
    st, p = api.route('GET', '/api/cataloging/template', {'type': ['bogus']}, None, S)
    check('skeleton неизвестного типа -> 404', st == 404)
    st, p = api.route('GET', '/api/cataloging/template', {}, None, S)
    check('skeleton без type -> 400', st == 400)
    st, p = api.route('POST', '/api/cataloging/template', {},
                      {'type': 'book', 'fields': [{'tag': '200', 'label': 'Загл.'}],
                       'label': 'Книга (наш)'}, S)
    check('сохранить кастом -> 200', st == 200 and p['data']['template']['label'] == 'Книга (наш)')
    st, p = api.route('GET', '/api/cataloging/template', {'type': ['book']}, None, S)
    check('кастом бьёт встроенный (1 поле)', st == 200 and len(p['data']['fields']) == 1)
    st, p = api.route('POST', '/api/cataloging/template', {},
                      {'type': 'book', 'fields': [{'label': 'без тега'}]}, S)
    check('кастом без tag -> 400', st == 400)
    st, p = api.route('POST', '/api/cataloging/template', {},
                      {'type': 'book', 'fields': [{'tag': '200'}]}, R)
    check('reader сохраняет шаблон -> 403', st == 403)

    # --- Очередь фоновых задач (admin) ---
    st, p = api.route('POST', '/api/jobs', {},
                      {'kind': 'ocr', 'payload': {'asset': 'a1'}, 'priority': 1}, A)
    check('enqueue ocr (prio 1) -> 200 pending',
          st == 200 and p['data']['job']['status'] == 'pending')
    st, p = api.route('POST', '/api/jobs', {},
                      {'kind': 'tiles', 'payload': {'asset': 'a2'}, 'priority': 5}, A)
    check('enqueue tiles (prio 5) -> 200', st == 200)
    jid5 = p['data']['job']['id']
    st, p = api.route('POST', '/api/jobs/claim', {}, {}, A)
    check('claim -> сначала бОльший приоритет (tiles)',
          st == 200 and p['data']['job']['id'] == jid5
          and p['data']['job']['status'] == 'running')
    st, p = api.route('POST', '/api/jobs/complete', {},
                      {'id': jid5, 'result': {'pages': 3}}, A)
    check('complete -> done + result', st == 200
          and p['data']['job']['status'] == 'done'
          and p['data']['job']['result']['pages'] == 3)
    st, p = api.route('GET', '/api/jobs', {}, None, A)
    check('list + stats (total 2, done 1)', st == 200
          and p['data']['stats']['total'] == 2
          and p['data']['stats']['by_status']['done'] == 1)
    st, p = api.route('POST', '/api/jobs/complete', {}, {'id': 999999}, A)
    check('complete неизвестного id -> 404', st == 404)
    st, p = api.route('POST', '/api/jobs', {}, {'kind': 'x'}, R)
    check('reader enqueue -> 403', st == 403)
    st, p = api.route('POST', '/api/jobs', {}, {'kind': 'x'}, S)
    check('staff-без-admin enqueue -> 403', st == 403)

    # --- Time-boxed подписки читателя на коллекции ---
    st, p = api.route('POST', '/api/me/collections', {},
                      {'kind': 'exhibit', 'ref': 'teatr-1920',
                       'from': '2026-06-01', 'to': '2026-12-31'}, R)
    check('подписка на выставку -> 200', st == 200 and p['data']['subscription'])
    st, p = api.route('POST', '/api/me/collections', {},
                      {'kind': 'collection', 'ref': 'expired',
                       'from': '2025-01-01', 'to': '2025-12-31'}, R)
    check('подписка с прошедшим окном -> 200', st == 200)
    st, p = api.route('GET', '/api/me/collections', {}, None, R)
    check('все подписки -> 2', st == 200 and len(p['data']['items']) == 2)
    st, p = api.route('GET', '/api/me/collections', {'active': ['1']}, None, R)
    check('активные на сегодня -> 1 (прошедшее окно отфильтровано)',
          st == 200 and len(p['data']['items']) == 1
          and p['data']['items'][0]['target_ref'] == 'teatr-1920')
    st, p = api.route('POST', '/api/me/collections', {},
                      {'kind': 'bogus', 'ref': 'x'}, R)
    check('подписка с невалидным kind -> 400', st == 400)
    st, p = api.route('POST', '/api/me/collections', {}, {'kind': 'exhibit', 'ref': 'x'}, S)
    check('staff (не reader) подписка -> 403', st == 403)
    st, p = api.route('GET', '/api/me/collections', {}, None, R)
    first_id = p['data']['items'][0]['id']
    st, p = api.route('POST', '/api/me/collections/cancel', {}, {'id': first_id}, R)
    check('отмена своей подписки -> cancelled true', st == 200 and p['data']['cancelled'] is True)
    other = _reader(api, ticket='222', rdr_mfn=2)
    st, p = api.route('POST', '/api/me/collections/cancel', {}, {'id': 99999}, other)
    check('отмена чужой/несуществующей -> cancelled false',
          st == 200 and p['data']['cancelled'] is False)


def batch240b_route_checks():
    print('-- Батч #240 (2-я волна): авто-фасеты / реестр IP-диапазонов через route()')
    api = _api()
    S = _sess(api, 'staff', 'cat', STAFF_G)
    A = _sess(api, 'staff', 'adm', ADMIN_G)
    R = _reader(api)

    # --- Авто-фасеты «поле→фасет» ---
    st, p = api.route('GET', '/api/facet-config', {}, None, S)
    check('конфиг фасетов: дефолт >=5', st == 200 and len(p['data']['items']) >= 5
          and any(f['key'] == '900^b' for f in p['data']['items']))
    recs = [_rec('Книга A', **{'101': 'rus', '900': [{'b': '01'}]}),
            _rec('Книга B', **{'101': 'rus', '900': [{'b': '05'}]}),
            _rec('Book C', **{'101': 'eng', '900': [{'b': '01'}]})]
    st, p = api.route('POST', '/api/facets/compute', {}, {'records': recs}, S)
    lang = {x['value']: x['count'] for x in p['data']['facets'].get('101', [])}
    check('compute язык rus=2/eng=1', st == 200 and lang.get('rus') == 2 and lang.get('eng') == 1)
    check('compute язык сортирован по убыванию', p['data']['facets']['101'][0]['value'] == 'rus')
    st, p = api.route('POST', '/api/facet-config', {},
                      {'tag': '999', 'subfield': 'x', 'label': 'Мой фасет'}, S)
    check('upsert кастом-фасета -> 200', st == 200 and p['data']['facet']['tag'] == '999')
    fid = p['data']['facet']['id']
    st, p = api.route('GET', '/api/facet-config', {}, None, S)
    check('кастом замещает дефолт (1 фасет 999^x)',
          st == 200 and len(p['data']['items']) == 1 and p['data']['items'][0]['key'] == '999^x')
    st, p = api.route('POST', '/api/facet-config/remove', {}, {'id': fid}, S)
    check('remove кастом-фасета -> 200 removed', st == 200 and p['data']['removed'] is True)
    st, p = api.route('POST', '/api/facet-config', {}, {'subfield': 'x'}, S)
    check('upsert без tag -> 400', st == 400)
    st, p = api.route('POST', '/api/facet-config', {}, {'tag': '999'}, R)
    check('reader правит конфиг фасетов -> 403', st == 403)

    # --- Реестр IP-диапазонов организаций (admin) ---
    st, p = api.route('POST', '/api/admin/ip-ranges', {},
                      {'cidr': '10.0.0.0/8', 'org': 'ВУЗ-A', 'role': 'org'}, A)
    check('добавить /8 ВУЗ-A -> 200', st == 200 and p['data']['range']['org'] == 'ВУЗ-A')
    st, p = api.route('POST', '/api/admin/ip-ranges', {},
                      {'cidr': '10.1.2.0/24', 'org': 'Библ-B'}, A)
    check('добавить более специфичный /24 Библ-B -> 200', st == 200)
    st, p = api.route('GET', '/api/admin/ip-ranges/resolve', {'ip': ['10.1.2.5']}, None, A)
    check('resolve 10.1.2.5 -> Библ-B (специфичнее)',
          st == 200 and p['data']['match'] and p['data']['match']['org'] == 'Библ-B')
    st, p = api.route('GET', '/api/admin/ip-ranges/resolve', {'ip': ['10.9.9.9']}, None, A)
    check('resolve 10.9.9.9 -> ВУЗ-A (/8)',
          st == 200 and p['data']['match']['org'] == 'ВУЗ-A')
    st, p = api.route('GET', '/api/admin/ip-ranges/resolve', {'ip': ['8.8.8.8']}, None, A)
    check('resolve вне всех -> null', st == 200 and p['data']['match'] is None)
    st, p = api.route('POST', '/api/admin/ip-ranges', {}, {'cidr': 'не-cidr', 'org': 'X'}, A)
    check('кривой CIDR -> 400', st == 400)
    st, p = api.route('POST', '/api/admin/ip-ranges', {}, {'cidr': '10.0.0.0/8'}, A)
    check('пустой org -> 400', st == 400)
    st, p = api.route('GET', '/api/admin/ip-ranges', {}, None, R)
    check('reader смотрит ip-ranges -> 403', st == 403)
    st, p = api.route('GET', '/api/admin/ip-ranges', {}, None, S)
    check('staff-без-admin ip-ranges -> 403', st == 403)


def browse_route_checks():
    print('-- #240 Browse-указатели A–Z через route()')
    api = _api()
    G = _sess(api, 'guest', 'g', READER_G)
    R = _reader(api)
    # каталог с авторами под указатель 700^a
    api.catalog.save('IBIS', _rec('Кн1', **{'700': [{'a': 'Антонов'}]}))
    api.catalog.save('IBIS', _rec('Кн2', **{'700': [{'a': 'Борисов'}]}))
    api.catalog.save('IBIS', _rec('Кн3', **{'700': [{'a': 'Антипов'}]}))

    st, p = api.route('GET', '/api/browse', {'tag': ['700'], 'subfield': ['a']}, None, G)
    check('browse 700^a -> 200', st == 200)
    d = p['data']
    check('буквы указателя [А, Б]', d['letters'] == ['А', 'Б'])
    check('буква А: Антипов перед Антоновым',
          [x['term'] for x in d['buckets']['А']] == ['Антипов', 'Антонов'])
    check('буква Б: Борисов (count 1)',
          d['buckets']['Б'][0]['term'] == 'Борисов' and d['buckets']['Б'][0]['count'] == 1)
    # public-db guard: читатель не может перебирать служебную базу
    st, p = api.route('GET', '/api/browse', {'db': ['RDR'], 'tag': ['700']}, None, R)
    check('browse служебной базы (reader) -> 403', st == 403)
    # пустое поле -> пустой указатель
    st, p = api.route('GET', '/api/browse', {'tag': ['999'], 'subfield': ['z']}, None, G)
    check('browse по пустому полю -> letters []', st == 200 and p['data']['letters'] == [])


def access_matrix_route_checks():
    print('-- Матрица доступов / тарифы через route() (#331)')
    api = _api()
    A = _sess(api, 'staff', 'adm', ADMIN_G)
    R = _reader(api)

    # Редактируемая таблица: строки каталога × тарифы-колонки.
    st, p = api.route('GET', '/api/admin/tariffs', {}, None, A)
    check('таблица тарифов -> 3 колонки + строки каталога',
          st == 200 and len(p['data']['tariffs']) == 3 and len(p['data']['rows']) > 20)
    check('ячейки standard несут section:opac',
          _am.section_key('opac') in p['data']['cells']['standard'])

    # Эффективная матрица тенанта (по умолчанию public -> default standard).
    st, p = api.route('GET', '/api/admin/access-matrix', {}, None, A)
    m = p['data']['matrix']
    check('матрица: каталогизация включена (standard)',
          st == 200 and m['sections']['cataloging']['included'])
    check('матрица: оцифровка выключена (standard)',
          not m['sections']['digitization']['included'])

    # Создать тариф-колонку + назначить тенанту + проверить резолв.
    st, p = api.route('POST', '/api/admin/tariffs', {},
                      {'name': 'vuz', 'title': 'ВУЗ', 'sort': 5}, A)
    check('создать тариф vuz -> 200', st == 200 and p['data']['tariff']['name'] == 'vuz')
    # включить раздел оцифровки в новом тарифе
    st, p = api.route('POST', '/api/admin/tariffs/cell', {},
                      {'tariff': 'vuz', 'itemKey': _am.section_key('digitization'),
                       'included': True, 'enforcement': 'block'}, A)
    check('ячейка vuz/section:digitization included -> 200',
          st == 200 and p['data']['cell']['included'] is True)
    st, p = api.route('POST', '/api/admin/tariffs/assign', {},
                      {'tenant': 't_vuz', 'tariff': 'vuz'}, A)
    check('назначить vuz тенанту t_vuz -> 200', st == 200)
    st, p = api.route('GET', '/api/admin/access-matrix', {'tenant': ['t_vuz']}, None, A)
    check('t_vuz: оцифровка теперь включена',
          st == 200 and p['data']['matrix']['sections']['digitization']['included'])

    # À-la-carte: задать базу ocr_pages=0 ячейкой (иначе ресурс безлимитен), потом докупить.
    st, p = api.route('POST', '/api/admin/tariffs/cell', {},
                      {'tariff': 'vuz', 'itemKey': _am.cap_key('ocr_pages'),
                       'value': 0, 'enforcement': 'block'}, A)
    check('ячейка vuz/cap:ocr_pages value=0 -> 200',
          st == 200 and p['data']['cell']['value'] == 0)
    st, p = api.route('POST', '/api/admin/tariffs/addon', {},
                      {'tenant': 't_vuz', 'resource': 'ocr_pages',
                       'packs': 3, 'packSize': 1000}, A)
    check('à-la-carte addon -> 200', st == 200)
    st, p = api.route('GET', '/api/admin/access-matrix', {'tenant': ['t_vuz']}, None, A)
    check('t_vuz: ocr_pages лимит = 3000 (3×1000)',
          p['data']['matrix']['caps']['ocr_pages']['limit'] == 3000)

    # Валидация + гварды.
    st, p = api.route('POST', '/api/admin/tariffs/cell', {},
                      {'tariff': 'нет', 'itemKey': 'x'}, A)
    check('ячейка неизвестного тарифа -> 400', st == 400)
    st, p = api.route('POST', '/api/admin/tariffs/assign', {},
                      {'tenant': 't', 'tariff': 'неттакого'}, A)
    check('назначить несуществующий тариф -> 400', st == 400)
    st, p = api.route('POST', '/api/admin/tariffs', {}, {'title': 'без имени'}, A)
    check('создать тариф без name -> 400', st == 400)
    st, p = api.route('GET', '/api/admin/tariffs', {}, None, R)
    check('reader смотрит тарифы -> 403', st == 403)
    st, p = api.route('POST', '/api/admin/tariffs', {}, {'name': 'x'}, R)
    check('reader создаёт тариф -> 403', st == 403)
    st, p = api.route('POST', '/api/admin/tariffs/delete', {}, {'name': 'vuz'}, A)
    check('удалить тариф vuz -> removed true', st == 200 and p['data']['removed'] is True)


def main():
    sdi_route_checks()
    union_route_checks()
    dispatch_route_checks()
    reader_record_checks()
    vkr_route_checks()
    ksu_route_checks()
    serials_route_checks()
    dam_route_checks()
    backlog_acq_route_checks()
    backlog_cataloging_route_checks()
    backlog_admin_route_checks()
    backlog_utils_route_checks()
    backlog_circ_route_checks()
    backlog_bp_route_checks()
    edge_11_4_checks()
    digitization_route_checks()
    batch240_route_checks()
    batch240b_route_checks()
    browse_route_checks()
    access_matrix_route_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
