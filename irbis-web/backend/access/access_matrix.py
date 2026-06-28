#!/usr/bin/env python3
"""ACCESS MATRIX — каталог разделов×функций (SSOT) + резолвер тарифа тенанта.

Матрица доступов (issue #331): по тарифу / купленному набору функций тенанта
определяет, какие **разделы** и какие **функции внутри разделов** доступны, какие
числовые **лимиты** действуют (в т.ч. число аккаунтов), и КАК реагировать на
превышение/недоступность — жёсткий блок (HTTP 402) или мягкий грейс.

Две части:
  * **Каталог-SSOT** (:data:`SECTIONS`, :data:`RESOURCES`) — продуктовая таксономия
    разделов и функций, к которой привязаны тарифы. Источник истины каталога —
    дизайн-доки (``docs/design/COMPETITIVE_MATRIX.md`` / ``COVERAGE_MATRIX.md`` /
    ``arm_inventory/*_FUNCTIONS.md``). **Правило:** при добавлении новой функции в
    продукт — дописываем её сюда (каталог не должен устаревать).
  * **Резолвер** (:func:`resolve`) — из РЕДАКТИРУЕМОГО ``access.tariff_store``
    (тарифы-данные, правятся в админ-таблице, не хардкод) собирает эффективную
    матрицу для тенанта: какие разделы/функции включены, лимиты (с учётом
    à-la-carte пакетов) и режим enforcement по каждому пункту.

Тарифы — ДАННЫЕ: значения сидируются из текущих ``billing.PLANS`` (:func:`seed_defaults`),
дальше правятся админом. Сам модуль — чистая трансформация над стором (без сети/
живого ИРБИС), тестируется на синтетике.
"""

# --------------------------------------------------------------------------- #
# Ключи пунктов матрицы (строки, по которым tariff_store хранит ячейки).
# --------------------------------------------------------------------------- #
SECTION_PREFIX = 'section:'
FN_PREFIX = 'fn:'
CAP_PREFIX = 'cap:'

# Режимы реакции на превышение лимита / недоступность пункта.
ENFORCE_BLOCK = 'block'   # жёсткий отказ (HTTP 402 на слое роута)
ENFORCE_GRACE = 'grace'   # мягко: пускаем, но помечаем warning (грейс)


def section_key(section):
    return SECTION_PREFIX + section


def fn_key(section, fn):
    return FN_PREFIX + section + '.' + fn


def cap_key(resource):
    return CAP_PREFIX + resource


# --------------------------------------------------------------------------- #
# КАТАЛОГ-SSOT: разделы (раздел -> функции). Курируется как продуктовая
# таксономия (фич-уровень), а не сырой дамп пунктов меню ИРБИС. module — связь с
# энтайтлмент-модулем (access/entitlements) там, где он есть; иначе раздел сам по
# себе единица гейтинга.
# --------------------------------------------------------------------------- #
SECTIONS = [
    {'key': 'opac', 'title': 'Читательский портал (поиск)', 'module': 'opac', 'functions': [
        {'key': 'search', 'title': 'Поиск каталога'},
        {'key': 'record', 'title': 'Просмотр записи'},
        {'key': 'facets', 'title': 'Фасеты'},
        {'key': 'rubricator', 'title': 'Рубрикатор'},
        {'key': 'showcase', 'title': 'Витрина новинок'},
        {'key': 'browse', 'title': 'Указатели A–Z'},
        {'key': 'suggest', 'title': 'Подсказки поиска'},
        {'key': 'covers', 'title': 'Обложки'},
    ]},
    {'key': 'reader', 'title': 'Читательский кабинет', 'module': 'reader', 'functions': [
        {'key': 'orders', 'title': 'Заказы'},
        {'key': 'holds', 'title': 'Брони'},
        {'key': 'shelves', 'title': 'Полки'},
        {'key': 'history', 'title': 'История чтения'},
        {'key': 'saved_searches', 'title': 'Сохранённые поиски'},
        {'key': 'inbox', 'title': 'Уведомления'},
        {'key': 'reviews', 'title': 'Отзывы/рейтинги'},
        {'key': 'recommendations', 'title': 'Рекомендации'},
        {'key': 'collections', 'title': 'Подписки на коллекции'},
    ]},
    {'key': 'cataloging', 'title': 'Каталогизация', 'module': 'cataloging', 'functions': [
        {'key': 'edit', 'title': 'Редактор записи'},
        {'key': 'marc', 'title': 'MARC/ISO2709 обмен'},
        {'key': 'marcxml', 'title': 'MARCXML обмен'},
        {'key': 'dedup', 'title': 'Дедупликация'},
        {'key': 'gost_print', 'title': 'Печать ГОСТ'},
        {'key': 'versions', 'title': 'Версии записи'},
        {'key': 'vocab', 'title': 'Редактор словарей'},
        {'key': 'templates', 'title': 'Шаблоны метаданных'},
        {'key': 'auto_facets', 'title': 'Авто-фасеты (конфиг)'},
        {'key': 'gbl', 'title': 'Глобальная корректировка'},
        {'key': 'authority', 'title': 'Авторитетные файлы'},
        {'key': 'z3950', 'title': 'Копикаталогизация Z39.50'},
    ]},
    {'key': 'circulation', 'title': 'Книговыдача', 'module': 'circulation', 'functions': [
        {'key': 'issue', 'title': 'Выдача/возврат'},
        {'key': 'renew', 'title': 'Продление'},
        {'key': 'fines', 'title': 'Штрафы/пени'},
        {'key': 'loan_policy', 'title': 'Политики выдачи'},
        {'key': 'debtors', 'title': 'Должники/санкции'},
        {'key': 'device_circ', 'title': 'Выдача через устройства'},
    ]},
    {'key': 'acquisition', 'title': 'Комплектование', 'module': 'acquisition', 'functions': [
        {'key': 'orders', 'title': 'Заказы'},
        {'key': 'receipt', 'title': 'Поступление/КСУ'},
        {'key': 'suppliers', 'title': 'Поставщики/счета'},
        {'key': 'subscriptions', 'title': 'Подписка/периодика'},
        {'key': 'serials', 'title': 'Сериалы'},
    ]},
    {'key': 'bookprovision', 'title': 'Книгообеспеченность', 'module': 'bookprovision', 'functions': [
        {'key': 'structure', 'title': 'Факультеты/специальности'},
        {'key': 'disciplines', 'title': 'Дисциплины/РПД'},
        {'key': 'norms', 'title': 'Нормативы'},
        {'key': 'kko', 'title': 'ККО-аналитика'},
    ]},
    {'key': 'admin', 'title': 'Администрирование', 'module': 'admin', 'functions': [
        {'key': 'users', 'title': 'Учётки/роли'},
        {'key': 'rbac', 'title': 'RBAC (редактируемые роли)'},
        {'key': 'audit', 'title': 'Аудит-трейл'},
        {'key': 'config', 'title': 'Конфиг-параметры'},
        {'key': 'tenants', 'title': 'Тенанты/провижининг'},
        {'key': 'billing', 'title': 'Тарифы/биллинг'},
        {'key': 'migration', 'title': 'Миграция из ИРБИС'},
        {'key': 'benchmark', 'title': 'Бенчмарк'},
        {'key': 'ip_ranges', 'title': 'IP-диапазоны'},
        {'key': 'jobs', 'title': 'Очередь фоновых задач'},
    ]},
    {'key': 'analytics', 'title': 'Аналитика', 'module': 'analytics', 'functions': [
        {'key': 'stats', 'title': 'Статистика'},
        {'key': 'exports', 'title': 'Экспорт данных'},
        {'key': 'duplicates', 'title': 'Поиск дублей'},
        {'key': 'validate', 'title': 'ФЛК-валидация (batch)'},
    ]},
    {'key': 'digitization', 'title': 'Оцифровка', 'module': 'digitization', 'functions': [
        {'key': 'dam', 'title': 'DAM/файлы'},
        {'key': 'iiif', 'title': 'IIIF-просмотрщик'},
        {'key': 'ocr_search', 'title': 'Поиск по OCR'},
        {'key': 'ocr_recognize', 'title': 'OCR-распознавание (à-la-carte)'},
        {'key': 'oai', 'title': 'OAI-PMH выгрузка'},
        {'key': 'exhibits', 'title': 'Виртуальные выставки'},
    ]},
    {'key': 'devices', 'title': 'Постаматы/устройства', 'module': 'devices', 'functions': [
        {'key': 'lockers', 'title': 'Постаматы/ячейки 24/7'},
        {'key': 'sip2', 'title': 'SIP2-киоски самообслуживания'},
        {'key': 'inventory', 'title': 'ТСД-инвентаризация'},
        {'key': 'vision', 'title': 'Камеры/FaceID'},
        {'key': 'compat', 'title': 'Совместимость IDlogic'},
    ]},
    {'key': 'social_ai', 'title': 'Соц-граф / AI', 'module': 'social_ai', 'functions': [
        {'key': 'recommendations', 'title': 'Рекомендации/соц-граф'},
        {'key': 'rag', 'title': 'RAG-ассистент с цитированием'},
    ]},
    {'key': 'auth_plugins', 'title': 'Авторизация-плагины', 'module': 'auth_plugins', 'functions': [
        {'key': 'oidc', 'title': 'OIDC (ЕСИА/Сбер/Яндекс)'},
        {'key': 'ip_login', 'title': 'IP-авто-вход организации'},
        {'key': 'ticket_link', 'title': 'Привязка билета'},
    ]},
    {'key': 'platform', 'title': 'Платформа/мультитенант', 'module': 'multitenant', 'functions': [
        {'key': 'modes', 'title': 'Режимы demo/portal/full'},
        {'key': 'marketplace', 'title': 'Маркетплейс модулей'},
        {'key': 'edge', 'title': 'Edge-узлы/офлайн-синхр'},
        {'key': 'i18n', 'title': 'Локализация (i18n)'},
        {'key': 'a11y', 'title': 'Доступность WCAG 2.2'},
    ]},
]

# Числовые ресурсы (лимиты). kind: 'cap' — потолок (число аккаунтов/записей/МБ);
# 'pack' — à-la-carte, докупается пакетами (база из тарифа + купленные пакеты).
RESOURCES = [
    {'key': 'staff_seats', 'title': 'Сотруднические аккаунты (сидов)', 'kind': 'cap', 'unit': 'аккаунт'},
    {'key': 'readers', 'title': 'Читательские аккаунты', 'kind': 'cap', 'unit': 'читатель'},
    {'key': 'records', 'title': 'Записи каталога', 'kind': 'cap', 'unit': 'запись'},
    {'key': 'storage_mb', 'title': 'Хранилище', 'kind': 'cap', 'unit': 'МБ'},
    {'key': 'ocr_pages', 'title': 'OCR-распознанные страницы', 'kind': 'pack', 'unit': 'страница'},
]

# Быстрые индексы по ключам.
_SECTION_BY_KEY = {s['key']: s for s in SECTIONS}
_RESOURCE_BY_KEY = {r['key']: r for r in RESOURCES}
UNLIMITED = None   # потолок «без ограничения»


# --------------------------------------------------------------------------- #
# Дефолтные тарифы (сид из текущих billing.PLANS). Дальше правятся в админ-таблице.
# Раздел включён целиком; функции наследуют включённость раздела, пока админ не
# переопределит отдельную ячейку. Лимиты + режим enforcement — на тариф.
# --------------------------------------------------------------------------- #
DEFAULT_TARIFFS = [
    {'name': 'free', 'title': 'Free', 'sort': 0, 'enforcement': ENFORCE_GRACE,
     'sections': ['opac', 'reader'],
     'caps': {'staff_seats': 2, 'readers': 200, 'records': 1000,
              'storage_mb': 100, 'ocr_pages': 0}},
    {'name': 'standard', 'title': 'Standard', 'sort': 1, 'enforcement': ENFORCE_BLOCK,
     'sections': ['opac', 'reader', 'cataloging', 'circulation', 'admin', 'analytics'],
     'caps': {'staff_seats': 20, 'readers': 20000, 'records': 100000,
              'storage_mb': 10240, 'ocr_pages': 0}},
    {'name': 'pro', 'title': 'Pro', 'sort': 2, 'enforcement': ENFORCE_BLOCK,
     'sections': [s['key'] for s in SECTIONS],   # всё
     'caps': {'staff_seats': UNLIMITED, 'readers': UNLIMITED, 'records': UNLIMITED,
              'storage_mb': UNLIMITED, 'ocr_pages': 0}},   # ocr_pages — докупается пакетами
]

DEFAULT_TARIFF_NAME = 'standard'


def seed_defaults(store):
    """Идемпотентно засеять дефолтные тарифы в ``tariff_store`` (если их там нет).

    Существующие тарифы НЕ перезаписываются (админ-правки сохраняются). Возвращает
    список имён реально созданных тарифов."""
    existing = {t['name'] for t in store.list_tariffs()}
    created = []
    for t in DEFAULT_TARIFFS:
        if t['name'] in existing:
            continue
        store.create_tariff(t['name'], title=t['title'], sort=t['sort'])
        enf = t['enforcement']
        incl = set(t['sections'])
        # Включённость разделов (функции наследуют, пока не переопределены).
        for s in SECTIONS:
            store.set_entry(t['name'], section_key(s['key']),
                            included=s['key'] in incl, enforcement=enf)
        # Лимиты-ресурсы.
        for res, val in t['caps'].items():
            store.set_entry(t['name'], cap_key(res), included=True,
                            value=val, enforcement=enf)
        created.append(t['name'])
    return created


# --------------------------------------------------------------------------- #
# Резолвер: тенант -> эффективная матрица.
# --------------------------------------------------------------------------- #
def _permissive():
    """Fail-open матрица (dev / тарифы не настроены): всё включено, без лимитов,
    грейс. Сохраняет совместимость, пока админ не сконфигурировал тарифы."""
    sections = {}
    for s in SECTIONS:
        sections[s['key']] = {
            'title': s['title'], 'module': s['module'],
            'included': True, 'enforcement': ENFORCE_GRACE,
            'functions': {f['key']: {'title': f['title'], 'included': True,
                                     'enforcement': ENFORCE_GRACE}
                          for f in s['functions']},
        }
    caps = {r['key']: {'title': r['title'], 'kind': r['kind'], 'unit': r['unit'],
                       'limit': UNLIMITED, 'enforcement': ENFORCE_GRACE,
                       'addon_units': 0}
            for r in RESOURCES}
    return {'tariff': None, 'configured': False, 'sections': sections, 'caps': caps}


def resolve(store, tenant):
    """Эффективная матрица доступов тенанта из ``tariff_store``.

    Тенант -> назначенный тариф (или :data:`DEFAULT_TARIFF_NAME`) -> ячейки. Если
    тарифы вовсе не засеяны ИЛИ назначенный тариф не найден — fail-open
    (:func:`_permissive`), чтобы dev/непровиженные тенанты работали. À-la-carte
    пакеты прибавляются к лимиту pack-ресурсов (``limit += addon_units``).

    Форма::

        {'tariff': name|None, 'configured': bool,
         'sections': {sk: {'included','enforcement','title','module',
                           'functions': {fk: {'included','enforcement','title'}}}},
         'caps': {res: {'limit': int|None, 'enforcement', 'addon_units', ...}}}
    """
    tariffs = store.list_tariffs()
    if not tariffs:
        return _permissive()
    tname = store.get_tenant_tariff(tenant) or DEFAULT_TARIFF_NAME
    if store.get_tariff(tname) is None:
        return _permissive()
    entries = store.get_entries(tname)

    sections = {}
    for s in SECTIONS:
        se = entries.get(section_key(s['key']))
        s_incl = se['included'] if se else False
        s_enf = se['enforcement'] if se else ENFORCE_BLOCK
        funcs = {}
        for f in s['functions']:
            fe = entries.get(fn_key(s['key'], f['key']))
            # функция наследует включённость раздела, пока не переопределена ячейкой
            f_incl = (fe['included'] if fe else s_incl) and s_incl
            f_enf = fe['enforcement'] if fe else s_enf
            funcs[f['key']] = {'title': f['title'], 'included': bool(f_incl),
                               'enforcement': f_enf}
        sections[s['key']] = {'title': s['title'], 'module': s['module'],
                              'included': bool(s_incl), 'enforcement': s_enf,
                              'functions': funcs}

    caps = {}
    for r in RESOURCES:
        ce = entries.get(cap_key(r['key']))
        limit = ce['value'] if ce else UNLIMITED
        enf = ce['enforcement'] if ce else ENFORCE_BLOCK
        addon = store.addon_units(tenant, r['key']) if r['kind'] == 'pack' else 0
        if r['kind'] == 'pack' and limit is not None:
            limit = limit + addon
        caps[r['key']] = {'title': r['title'], 'kind': r['kind'], 'unit': r['unit'],
                          'limit': limit, 'enforcement': enf, 'addon_units': addon}
    return {'tariff': tname, 'configured': True, 'sections': sections, 'caps': caps}


# --------------------------------------------------------------------------- #
# Проверки доступа над разрешённой матрицей (verdict: allow|grace|deny).
# --------------------------------------------------------------------------- #
def _verdict(ok, enforcement):
    """ok=True -> 'allow'. ok=False -> 'deny' при block, 'grace' при мягком режиме."""
    if ok:
        return 'allow'
    return 'deny' if enforcement == ENFORCE_BLOCK else 'grace'


def section_verdict(matrix, section):
    """Вердикт по разделу: allow|grace|deny (deny -> 402 на роуте)."""
    s = matrix['sections'].get(section)
    if s is None:
        return 'allow'   # раздела нет в каталоге — не гейтим (forward-compat)
    return _verdict(s['included'], s['enforcement'])


def function_verdict(matrix, section, fn):
    """Вердикт по функции внутри раздела: allow|grace|deny."""
    s = matrix['sections'].get(section)
    if s is None:
        return 'allow'
    f = s['functions'].get(fn)
    if f is None:
        return _verdict(s['included'], s['enforcement'])
    return _verdict(f['included'], f['enforcement'])


def cap_verdict(matrix, resource, current):
    """Вердикт по числовому лимиту при ТЕКУЩЕМ потреблении ``current``.

    Возвращает ``(verdict, info)``: verdict allow|grace|deny; info несёт
    limit/remaining/addon_units. ``current`` — потребление ДО запрашиваемой
    единицы (превышение = current >= limit). UNLIMITED -> всегда allow."""
    c = matrix['caps'].get(resource)
    if c is None:
        return 'allow', {'limit': UNLIMITED, 'remaining': None}
    limit = c['limit']
    if limit is None:
        return 'allow', {'limit': UNLIMITED, 'remaining': None,
                         'addon_units': c.get('addon_units', 0)}
    within = current < limit
    info = {'limit': limit, 'remaining': max(0, limit - current),
            'addon_units': c.get('addon_units', 0)}
    return _verdict(within, c['enforcement']), info


# --------------------------------------------------------------------------- #
# Данные для редактируемой админ-таблицы (строки каталога × колонки тарифов).
# --------------------------------------------------------------------------- #
def catalog_rows():
    """Плоский список строк каталога для админ-таблицы (разделы, функции, ресурсы)
    с типом и ключом. Порядок: раздел, затем его функции; в конце — ресурсы."""
    rows = []
    for s in SECTIONS:
        rows.append({'kind': 'section', 'item_key': section_key(s['key']),
                     'section': s['key'], 'title': s['title'], 'module': s['module']})
        for f in s['functions']:
            rows.append({'kind': 'function', 'item_key': fn_key(s['key'], f['key']),
                         'section': s['key'], 'fn': f['key'], 'title': f['title']})
    for r in RESOURCES:
        rows.append({'kind': 'resource', 'item_key': cap_key(r['key']),
                     'resource': r['key'], 'title': r['title'],
                     'res_kind': r['kind'], 'unit': r['unit']})
    return rows


def editable_table(store):
    """Полные данные редактируемой матрицы для админ-UI.

    ``{'rows': [...каталог...], 'tariffs': [{name,title,sort}], 'cells':
    {tariff_name: {item_key: {included,value,enforcement}}}}``. Строки —
    из :func:`catalog_rows` (SSOT), колонки — тарифы из стора, ячейки — их entries."""
    tariffs = store.list_tariffs()
    cells = {t['name']: store.get_entries(t['name']) for t in tariffs}
    return {'rows': catalog_rows(),
            'tariffs': [{'name': t['name'], 'title': t['title'], 'sort': t['sort']}
                        for t in tariffs],
            'cells': cells}
