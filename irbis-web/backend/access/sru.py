#!/usr/bin/env python3
"""SRU — COPY-каталогизация через Search/Retrieve via URL (эпик #240 «Z39.50»).

Контур **заимствования библиографических записей из внешних каталогов** (копи-
каталогизация): набор ЧИСТЫХ функций, которые СТРОЯТ SRU-запросы (URL c CQL) и
РАЗБИРАЮТ SRU-ответы (которые несут MARCXML записи) в нашу tag-keyed форму. SRU
(Search/Retrieve via URL) — это веб-вариант Z39.50: тот же поиск по сводным
каталогам, но поверх обычного HTTP GET с параметром-запросом на языке CQL, а в
ответе — ``searchRetrieveResponse`` со встроенными MARCXML-записями.

Реального сетевого вызова здесь НЕТ: транспорт (HTTP GET к ``base_url``) —
граница вызывающего слоя (контроллера), ровно как ``mysqldump`` в
``access/jirbis_migrate.py``. Этот модуль умеет ровно две вещи: собрать URL
SRU-запроса и распарсить XML-ответ в записи проекта. Ни I/O, ни состояния, ни
sqlite — чистый stdlib.

CQL (Contextual Query Language)
-------------------------------
SRU ищет на CQL — простом языке запросов вида ``index relation term``::

    dc.title="Чайка"
    bath.isbn="978-5-09-099157-0"

Мы строим только базовую форму ``index="term"`` (отношение «равно»); кавычки
внутри term экранируются (``"`` -> ``\\"``). Удобные индексы проекта (поле ->
CQL-индекс) лежат в :data:`BY_INDEX`.

SRU-ответ (searchRetrieveResponse)
----------------------------------
Namespace SRU — ``http://www.loc.gov/zing/srw/`` (исторически ZeeRex/SRW);
структура::

    <searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
      <numberOfRecords>2</numberOfRecords>
      <records>
        <record>
          <recordSchema>marcxml</recordSchema>
          <recordData>
            <record xmlns="http://www.loc.gov/MARC21/slim"> ...MARCXML... </record>
          </recordData>
        </record>
        ...
      </records>
    </searchRetrieveResponse>

ВАЖНО про namespace: разные серверы отдают эти элементы то с префиксом ``srw:``,
то с ``zs:``, то с ДЕФОЛТНЫМ namespace (без префикса). Поэтому мы парсим строго по
ЛОКАЛЬНОМУ имени тега (``tag.split('}')[-1]``), игнорируя префикс/namespace —
ровно как ``access/marcxml.py``.

Разбор MARCXML внутри ``recordData`` делегируется в :func:`marcxml.from_marcxml`:
извлекаем элемент ``record`` (MARC21slim) из каждого ``recordData``, сериализуем
его обратно в строку (``ET.tostring``) и прогоняем через штатный MARCXML-парсер —
на выходе наша tag-keyed запись (та же форма, что у ``access/marc.py`` /
``access/oai_pmh.py``: ``{tag3: [inst, ...]}``).

Робастность
-----------
Разбор устойчив (НЕ исключение): битый/пустой XML, отсутствие ``numberOfRecords``
или записей -> ``{'total': 0, 'records': []}``. Отдельный битый MARCXML внутри
``recordData`` пропускается, а не роняет весь ответ.

Чистый stdlib (``xml.etree.ElementTree``, ``urllib.parse``), без pip и без сети.
"""
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from access.marcxml import from_marcxml

__all__ = [
    'SRW_NS', 'MARC_NS', 'BY_INDEX',
    'cql', 'sru_url', 'search_query', 'parse_response', 'candidates',
]

# Namespace SRU/SRW (Search/Retrieve via URL — ZING/SRW, Library of Congress).
# Реально префикс бывает srw:/zs:/без префикса — парсим по localname (см. ниже).
SRW_NS = 'http://www.loc.gov/zing/srw/'

# Namespace MARCXML (MARC21slim) — конверт встроенных в recordData записей.
MARC_NS = 'http://www.loc.gov/MARC21/slim'

# Удобные индексы проекта: простое поле запроса -> CQL-индекс сводного каталога.
# 'any' — поиск по любому полю (cql.anywhere); по умолчанию (неизвестное поле)
# тоже падаем в cql.anywhere (см. search_query).
BY_INDEX = {
    'title': 'dc.title',
    'author': 'dc.creator',
    'isbn': 'bath.isbn',
    'any': 'cql.anywhere',
}


# --------------------------------------------------------------------------- #
# Вспомогательное: локальное имя тега (отбрасываем namespace ElementTree).
#
# Та же идея, что в access/marcxml.py: SRU-ответы приходят с РАЗНЫМИ префиксами
# (srw:/zs:/без префикса), поэтому сопоставляем элементы строго по localname.
# --------------------------------------------------------------------------- #
def _localname(tag):
    """Локальное имя XML-тега: ``{ns}record`` -> ``record`` (namespace-agnostic)."""
    if not tag:
        return ''
    return tag.split('}')[-1]


# --------------------------------------------------------------------------- #
# Локальный аксессор по форме записи проекта (зеркалит oai_pmh._sub).
# --------------------------------------------------------------------------- #
def _instances(record, tag):
    """Список инстансов поля ``tag`` (устойчиво к отсутствию/скаляру/None)."""
    if not isinstance(record, dict):
        return []
    val = record.get(tag)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _subvalues(record, tag, code):
    """ВСЕ непустые значения подполя ``code`` поля ``tag`` (список строк).

    В отличие от ``oai_pmh._sub`` (берёт первое), для дедупа нам нужны ВСЕ
    инстансы поля (у записи может быть несколько ISBN/заглавий). Голый скаляр
    подполей не несёт и пропускается."""
    out = []
    for inst in _instances(record, tag):
        if isinstance(inst, dict):
            v = inst.get(code)
            if v not in (None, ''):
                out.append(str(v))
    return out


# --------------------------------------------------------------------------- #
# Построение CQL-запроса.
# --------------------------------------------------------------------------- #
def cql(index, term):
    """Построить базовое CQL-выражение ``index="term"`` (отношение «равно»).

    Например ``cql('dc.title', 'Чайка')`` -> ``'dc.title="Чайка"'``. Кавычки в
    ``term`` экранируются (``"`` -> ``\\"``), чтобы не сломать CQL-синтаксис.
    Пустой/``None`` ``term`` -> ``''`` (нечего искать — пустой запрос)."""
    if term is None:
        return ''
    term = str(term)
    if term == '':
        return ''
    escaped = term.replace('"', '\\"')
    return '%s="%s"' % (index, escaped)


def search_query(field, term):
    """Удобная обёртка «поле проекта -> CQL»: маппит ``field`` через :data:`BY_INDEX`.

    Неизвестное поле падает в ``cql.anywhere`` (поиск по любому полю). Например
    ``search_query('title', 'Чайка')`` -> ``'dc.title="Чайка"'``,
    ``search_query('isbn', '978...')`` -> ``'bath.isbn="978..."'``."""
    return cql(BY_INDEX.get(field, 'cql.anywhere'), term)


# --------------------------------------------------------------------------- #
# Построение URL SRU-запроса (searchRetrieve).
# --------------------------------------------------------------------------- #
def sru_url(base_url, query, max_records=10, start=1, version='1.1'):
    """Собрать URL SRU-операции ``searchRetrieve``.

    Возвращает ``base_url + '?' + urlencode(params)`` со стандартным набором
    SRU-параметров: ``operation=searchRetrieve``, ``version``, ``query`` (CQL),
    ``maximumRecords``, ``startRecord``, ``recordSchema=marcxml``. Кодирование —
    штатный :func:`urllib.parse.urlencode` (кавычки/кириллица/пробелы в CQL
    экранируются как нужно для URL)."""
    params = {
        'operation': 'searchRetrieve',
        'version': version,
        'query': query,
        'maximumRecords': max_records,
        'startRecord': start,
        'recordSchema': 'marcxml',
    }
    return base_url + '?' + urlencode(params)


# --------------------------------------------------------------------------- #
# Разбор SRU-ответа (searchRetrieveResponse) -> {'total', 'records'}.
# --------------------------------------------------------------------------- #
def _find_marc_record(record_data_el):
    """Найти MARCXML-элемент ``<record>`` внутри ``<recordData>`` (по localname).

    Запись MARC21slim лежит дочерним элементом ``recordData``; иногда сам
    ``recordData`` namespaced иначе, поэтому ищем потомка с localname == 'record'.
    Если такого нет — ``None``."""
    for child in record_data_el.iter():
        if _localname(child.tag) == 'record':
            return child
    return None


def parse_response(xml_text):
    """Разобрать SRU ``searchRetrieveResponse`` -> ``{'total': int, 'records': [...]}``.

    ``total`` — значение ``numberOfRecords`` (int). ``records`` — список tag-keyed
    записей проekta: каждый встроенный в ``recordData`` MARCXML ``<record>``
    извлекается и прогоняется через :func:`marcxml.from_marcxml`.

    Namespace-агностично: элементы (searchRetrieveResponse / numberOfRecords /
    records / record / recordData) ищутся по ЛОКАЛЬНОМУ имени, поэтому работает с
    префиксами ``srw:``/``zs:`` и с дефолтным namespace.

    Устойчиво (НЕ исключение): битый/пустой XML, отсутствие ``numberOfRecords``
    или записей -> ``{'total': 0, 'records': []}``. Отдельный битый MARCXML внутри
    ``recordData`` пропускается."""
    empty = {'total': 0, 'records': []}
    if not xml_text:
        return dict(empty)
    if isinstance(xml_text, bytes):
        try:
            xml_text = xml_text.decode('utf-8')
        except UnicodeDecodeError:
            return dict(empty)
    if not xml_text.strip():
        return dict(empty)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return dict(empty)

    # total <- numberOfRecords (первое совпадение по localname; иначе 0).
    total = 0
    for el in root.iter():
        if _localname(el.tag) == 'numberOfRecords':
            try:
                total = int((el.text or '').strip())
            except (TypeError, ValueError):
                total = 0
            break

    # records <- каждый recordData -> встроенный MARCXML record -> from_marcxml.
    records = []
    for rd in root.iter():
        if _localname(rd.tag) != 'recordData':
            continue
        marc_el = _find_marc_record(rd)
        if marc_el is None:
            continue
        try:
            xml_str = ET.tostring(marc_el, encoding='unicode')
            rec = from_marcxml(xml_str)
        except Exception:
            # битый/непарсящийся MARCXML внутри recordData — пропускаем
            continue
        records.append(rec)

    return {'total': total, 'records': records}


# --------------------------------------------------------------------------- #
# Отбор кандидатов для дедупа при импорте.
# --------------------------------------------------------------------------- #
def candidates(records, isbn=None, title=None):
    """Отфильтровать записи-кандидаты для дедупа при импорте.

    Из ``records`` (как их вернул :func:`parse_response`) оставляет записи,
    подходящие под заданный критерий:

      * ``isbn`` задан — записи, у которых ЛЮБОЕ ISBN-подполе 010^a совпадает с
        ``isbn`` (точное равенство строки);
      * ``title`` задан — записи, где заглавие 200^a СОДЕРЖИТ ``title``
        (регистронезависимо, кириллица ОК).

    Если заданы оба — запись проходит, если удовлетворяет ЛЮБОМУ (логическое
    «или» — расширяем пул кандидатов на дедуп). Если ни один не задан —
    возвращается пустой список (нет критерия отбора)."""
    if isbn in (None, ''):
        isbn = None
    if title in (None, ''):
        title = None
    if isbn is None and title is None:
        return []
    title_lower = title.lower() if title is not None else None

    out = []
    for rec in (records or []):
        matched = False
        if isbn is not None:
            if isbn in _subvalues(rec, '010', 'a'):
                matched = True
        if not matched and title_lower is not None:
            for t in _subvalues(rec, '200', 'a'):
                if title_lower in t.lower():
                    matched = True
                    break
        if matched:
            out.append(rec)
    return out
