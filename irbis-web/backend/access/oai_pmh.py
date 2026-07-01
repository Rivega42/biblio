#!/usr/bin/env python3
"""OAI-PMH — провайдер метаданных каталога (трек «Оцифровка»).

Контур **отдачи метаданных во внешние агрегаторы** (НЭБ, КиберЛенинка-подобные
харвестеры, сводные каталоги): набор ЧИСТЫХ функций, которые мапят наши tag-keyed
каталожные записи в **Dublin Core** (``oai_dc``) и собирают ответы протокола
**OAI-PMH 2.0** как Python-dict. Сериализацию dict -> XML делает вызывающий слой
(контроллер); здесь нет ни I/O, ни записей в живой ИРБИС — только маппинг.

OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting) — это набор
HTTP-«глаголов» (``Identify``, ``ListMetadataFormats``, ``GetRecord``,
``ListRecords``, ``ListIdentifiers``), которыми внешний харвестер забирает
метаданные репозитория. Минимально-обязательный формат метаданных — ``oai_dc``
(Dublin Core в XML-обёртке OAI). Мы готовим именно «тело» этих ответов в виде
dict, а транспортный слой оборачивает их в XML-конверт ``<OAI-PMH>``.

Форма записи (как везде в проекте)
----------------------------------
Tag-keyed dict: поля — теги (строки), подполя — ключи внутри инстанса::

    {'200': [{'a': 'Заглавие'}],
     '700': [{'a': 'Иванов И.'}],
     '210': [{'c': 'Наука', 'd': '2021'}],
     '101': 'rus',
     '900': [{'b': '05'}],
     'mfn': 1}

Поле может быть списком инстансов-dict ``[{code: value}]`` ИЛИ голым скаляром
(как ``'101'``). Все функции устойчивы к отсутствию любых полей (defensive),
ровно как мапперы ``access/marcxml.py`` / ``access/db_utils.py``.

Маппинг Dublin Core
-------------------
  * ``title``      <- 200^a (заглавие)
  * ``creator``    <- 700^a (первый автор)
  * ``date``       <- 210^d (год издания)
  * ``publisher``  <- 210^c (издательство)
  * ``language``   <- 101   (язык; голый скаляр или 101^a)
  * ``identifier`` <- ``oai:biblio:<mfn>`` (всегда присутствует)
  * ``type``       <- ``'text'`` (всегда присутствует)

Пустые элементы DC ОПУСКАЮТСЯ (нет ключа), кроме ``identifier`` и ``type`` —
они присутствуют всегда (DC-минимум для валидной OAI-записи).

Чистый stdlib, без pip и без сети.
"""

__all__ = [
    'dublin_core', 'oai_identifier', 'record_header', 'identify',
    'list_metadata_formats', 'get_record', 'list_records',
    'list_identifiers', 'record_set', 'paginate',
]

# Префикс OAI-идентификатора репозитория по умолчанию.
DEFAULT_ID_PREFIX = 'oai:biblio:'

# Дата-заглушка для штампов (granularity YYYY-MM-DD): у наших записей нет
# собственного штампа изменения, поэтому вызывающий слой задаёт его явно.
DEFAULT_DATESTAMP = '2026-01-01'


# --------------------------------------------------------------------------- #
# Локальный аксессор по форме записи проекта.
#
# Та же модель, что в access/marcxml.py (tag-keyed ``{tag: [inst]}``), но здесь
# нам нужно лишь ПЕРВОЕ значение подполя — пишем компактный хелпер под это.
# --------------------------------------------------------------------------- #
def _instances(record, tag):
    """Список инстансов поля ``tag`` (устойчиво к отсутствию/скаляру/None).

    Голый скаляр (например ``'101': 'rus'``) оборачивается в одноэлементный
    список — чтобы единообразно итерироваться; dict-инстанс остаётся как есть."""
    if not isinstance(record, dict):
        return []
    val = record.get(tag)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _sub(record, tag, code):
    """Первое значение подполя ``code`` поля ``tag`` или ``''`` (никогда не None).

    Зеркалит подход ``access/marcxml.py`` к tag-keyed форме: берём первый
    инстанс-dict с нужным кодом. Если инстанс — голый скаляр (поле без подполей),
    он не несёт подполей, поэтому возвращается ``''``."""
    for inst in _instances(record, tag):
        if isinstance(inst, dict):
            if code in inst and inst[code] not in (None, ''):
                return str(inst[code])
    return ''


def _scalar(record, tag, code='a'):
    """Значение поля как СКАЛЯР: голый скаляр напрямую, иначе подполе ``code``.

    Поле 101 (язык) в проекте бывает и голой строкой (``'101': 'rus'``), и
    инстансом с подполем (``'101': [{'a': 'rus'}]``) — обрабатываем оба вида."""
    val = record.get(tag) if isinstance(record, dict) else None
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    # список/иное -> пробуем как подполе
    return _sub(record, tag, code)


# --------------------------------------------------------------------------- #
# Маппинг записи в Dublin Core (oai_dc).
# --------------------------------------------------------------------------- #
def oai_identifier(record, prefix=DEFAULT_ID_PREFIX):
    """OAI-идентификатор записи: ``<prefix><mfn>`` (например ``oai:biblio:1``).

    ``mfn`` отсутствует -> хвост пустой (``oai:biblio:``); идентификатор всё равно
    строится, чтобы запись была адресуема в ответах протокола."""
    mfn = ''
    if isinstance(record, dict):
        mfn = record.get('mfn', '')
        if mfn is None:
            mfn = ''
    return str(prefix) + str(mfn)


def dublin_core(record):
    """Смаппить tag-keyed запись в Dublin Core (``oai_dc``) -> dict.

    Возвращает dict DC-элементов::

        {'title': 200^a, 'creator': 700^a, 'date': 210^d,
         'publisher': 210^c, 'language': 101,
         'identifier': 'oai:biblio:<mfn>', 'type': 'text'}

    Пустые элементы ОПУСКАЮТСЯ (ключа нет), КРОМЕ ``identifier`` и ``type`` —
    они присутствуют всегда (DC-минимум валидной OAI-записи). Устойчиво к
    отсутствию любых полей."""
    dc = {}
    title = _sub(record, '200', 'a')
    if title:
        dc['title'] = title
    creator = _sub(record, '700', 'a')
    if creator:
        dc['creator'] = creator
    date = _sub(record, '210', 'd')
    if date:
        dc['date'] = date
    publisher = _sub(record, '210', 'c')
    if publisher:
        dc['publisher'] = publisher
    language = _scalar(record, '101', 'a')
    if language:
        dc['language'] = language
    # identifier/type — всегда присутствуют.
    dc['identifier'] = oai_identifier(record)
    dc['type'] = 'text'
    return dc


# --------------------------------------------------------------------------- #
# Сеты (setSpec) по виду издания.
# --------------------------------------------------------------------------- #
def record_set(record):
    """Сет записи (``setSpec``) по виду издания 900^b.

    Простая мапа: ``'05'`` (сериальное/продолжающееся) -> ``'serials'``, иначе
    ``'books'``. Если 900^b вовсе нет — ``'other'``. Используется для фильтрации
    в ``list_records`` и как ``setSpec`` в заголовке записи."""
    kind = _sub(record, '900', 'b')
    if not kind:
        return 'other'
    if kind == '05':
        return 'serials'
    return 'books'


# --------------------------------------------------------------------------- #
# Заголовок записи (record header) — общий для всех list-глаголов.
# --------------------------------------------------------------------------- #
def record_header(record, datestamp, set_spec=None):
    """Заголовок OAI-записи (``<header>``) -> dict.

    Возвращает ``{'identifier': oai_identifier, 'datestamp': datestamp}``; если
    задан ``set_spec`` — добавляет ключ ``'setSpec'``. ``datestamp`` задаёт
    вызывающий слой (granularity ``YYYY-MM-DD``)."""
    header = {
        'identifier': oai_identifier(record),
        'datestamp': datestamp,
    }
    if set_spec is not None:
        header['setSpec'] = set_spec
    return header


# --------------------------------------------------------------------------- #
# Глагол Identify — описание репозитория.
# --------------------------------------------------------------------------- #
def identify(repo_name, base_url, admin_email, earliest_datestamp):
    """Ответ глагола ``Identify`` (описание репозитория) -> dict.

    Жёстко фиксирует протокольные константы: ``protocolVersion`` ``'2.0'``,
    ``deletedRecord`` ``'no'`` (мы не отдаём tombstone-записи об удалении),
    ``granularity`` ``'YYYY-MM-DD'``. Параметры — переменная часть, которую
    задаёт вызывающий слой (имя репозитория, базовый URL, e-mail админа,
    самый ранний штамп)."""
    return {
        'repositoryName': repo_name,
        'baseURL': base_url,
        'protocolVersion': '2.0',
        'adminEmail': admin_email,
        'earliestDatestamp': earliest_datestamp,
        'deletedRecord': 'no',
        'granularity': 'YYYY-MM-DD',
    }


# --------------------------------------------------------------------------- #
# Глагол ListMetadataFormats — поддерживаемые форматы метаданных.
# --------------------------------------------------------------------------- #
def list_metadata_formats():
    """Ответ глагола ``ListMetadataFormats`` -> список форматов.

    Мы отдаём единственный обязательный формат ``oai_dc`` (Dublin Core) с его
    каноничными schema/namespace OAI 2.0."""
    return [{
        'metadataPrefix': 'oai_dc',
        'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
        'metadataNamespace': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    }]


# --------------------------------------------------------------------------- #
# Глаголы выборки записей: GetRecord / ListRecords / ListIdentifiers.
# --------------------------------------------------------------------------- #
def get_record(records, identifier, datestamp=DEFAULT_DATESTAMP):
    """Ответ глагола ``GetRecord`` — найти запись по OAI-идентификатору.

    Сканирует ``records`` и возвращает ``{'header': record_header,
    'metadata': dublin_core}`` для записи, чей ``oai_identifier`` равен
    ``identifier``; если такой нет — ``None``. ``setSpec`` в заголовок кладётся
    по ``record_set`` найденной записи."""
    for rec in (records or []):
        if oai_identifier(rec) == identifier:
            return {
                'header': record_header(rec, datestamp, record_set(rec)),
                'metadata': dublin_core(rec),
            }
    return None


def list_records(records, datestamp=DEFAULT_DATESTAMP, set_spec=None):
    """Ответ глагола ``ListRecords`` — заголовок+метаданные по каждой записи.

    Возвращает список ``[{'header': ..., 'metadata': ...}, ...]``. Если задан
    ``set_spec`` — отдаём ТОЛЬКО записи, чей вычисленный ``record_set`` совпадает
    (фильтрация по сету, как в OAI-выборке ``&set=``). Заголовок каждой записи
    несёт свой ``setSpec``."""
    out = []
    for rec in (records or []):
        rset = record_set(rec)
        if set_spec is not None and rset != set_spec:
            continue
        out.append({
            'header': record_header(rec, datestamp, rset),
            'metadata': dublin_core(rec),
        })
    return out


def list_identifiers(records, datestamp=DEFAULT_DATESTAMP):
    """Ответ глагола ``ListIdentifiers`` — ТОЛЬКО заголовки записей.

    Возвращает список ``record_header`` (без блока ``metadata``) по каждой
    записи — облегчённый обход репозитория для харвестера. ``setSpec`` в каждом
    заголовке — по ``record_set``."""
    return [record_header(rec, datestamp, record_set(rec))
            for rec in (records or [])]


# --------------------------------------------------------------------------- #
# Пагинация (resumption token) — для list-глаголов с большим выводом.
# --------------------------------------------------------------------------- #
def paginate(items, offset, limit):
    """Нарезать ``items`` на страницу ``[offset : offset+limit]`` + токен.

    Возвращает кортеж ``(page_items, resumption_token)``: ``page_items`` — срез
    страницы; ``resumption_token`` — строка следующего смещения ``str(offset+limit)``,
    если за страницей ещё есть элементы, иначе ``None`` (последняя страница).
    OAI-харвестер передаёт этот токен обратно как ``&resumptionToken=`` для
    дочитки. Устойчиво к отрицательному/запредельному ``offset`` (срез Python)."""
    items = list(items or [])
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 0
    if offset < 0:
        offset = 0
    page = items[offset:offset + limit] if limit > 0 else []
    next_offset = offset + limit
    token = str(next_offset) if next_offset < len(items) else None
    return page, token


# --------------------------------------------------------------------------- #
# XML-сериализация OAI-PMH (#C9): те же структуры глаголов -> валидный
# OAI-PMH 2.0 XML для харвестеров (JSON-путь остаётся для внутренних потребителей).
# --------------------------------------------------------------------------- #
import xml.sax.saxutils as _sax   # noqa: E402

_DC_KEYS = ('title', 'creator', 'subject', 'description', 'publisher',
            'date', 'type', 'language', 'identifier')


def _x(s):
    return _sax.escape('' if s is None else str(s))


def _header_xml(h):
    parts = ['<identifier>%s</identifier>' % _x(h.get('identifier')),
             '<datestamp>%s</datestamp>' % _x(h.get('datestamp'))]
    if h.get('setSpec'):
        parts.append('<setSpec>%s</setSpec>' % _x(h['setSpec']))
    return '<header>%s</header>' % ''.join(parts)


def _metadata_xml(dc):
    body = ''.join('<dc:%s>%s</dc:%s>' % (k, _x(dc[k]), k) for k in _DC_KEYS if k in dc)
    return ('<metadata><oai_dc:dc '
            'xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">%s</oai_dc:dc></metadata>' % body)


def _envelope(base_url, args, inner, datestamp=DEFAULT_DATESTAMP):
    req_attrs = ''.join(' %s="%s"' % (k, _x(v)) for k, v in (args or {}).items())
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
            '<responseDate>%s</responseDate><request%s>%s</request>%s</OAI-PMH>'
            % (_x(datestamp), req_attrs, _x(base_url), inner))


def to_xml(verb, payload, base_url, args=None, datestamp=DEFAULT_DATESTAMP):
    """OAI-PMH XML-ответ по глаголу + структурам (identify/list_*/get_record)."""
    if verb == 'Identify':
        inner = '<Identify>%s</Identify>' % ''.join(
            '<%s>%s</%s>' % (k, _x(v), k) for k, v in payload.items())
    elif verb == 'ListMetadataFormats':
        fmts = ''.join('<metadataFormat><metadataPrefix>%s</metadataPrefix>'
                       '<schema>%s</schema><metadataNamespace>%s</metadataNamespace>'
                       '</metadataFormat>'
                       % (_x(f['metadataPrefix']), _x(f['schema']), _x(f['metadataNamespace']))
                       for f in payload)
        inner = '<ListMetadataFormats>%s</ListMetadataFormats>' % fmts
    elif verb == 'GetRecord':
        inner = ('<GetRecord><record>%s%s</record></GetRecord>'
                 % (_header_xml(payload['header']), _metadata_xml(payload['metadata'])))
    elif verb == 'ListRecords':
        recs = ''.join('<record>%s%s</record>'
                       % (_header_xml(r['header']), _metadata_xml(r['metadata'])) for r in payload)
        inner = '<ListRecords>%s</ListRecords>' % recs
    elif verb == 'ListIdentifiers':
        inner = '<ListIdentifiers>%s</ListIdentifiers>' % ''.join(_header_xml(h) for h in payload)
    else:
        inner = ''
    return _envelope(base_url, args, inner, datestamp)


def error_xml(code, message, base_url, args=None):
    """OAI-PMH XML с ошибкой (badVerb / cannotDisseminateFormat / idDoesNotExist …)."""
    return _envelope(base_url, args, '<error code="%s">%s</error>' % (_x(code), _x(message)))
