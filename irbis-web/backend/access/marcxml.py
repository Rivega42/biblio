#!/usr/bin/env python3
"""MARCXML import/export — Каталогизатор interop (дополняет ISO 2709 в marc.py).

Контур «обмен библиографическими записями»: сериализация НАШИХ tag-keyed записей
(та же I1 field/subfield-модель, что у ``access/marc.py`` / ``access/pft.py``) в
формат **MARCXML** (Library of Congress, ``MARC21slim``) и обратно. MARCXML — это
XML-конверт для MARC: тот же контент, что несёт ISO 2709 (``access/marc.py``), но
в виде ``<record>``/``<controlfield>``/``<datafield>``/``<subfield>``. Контент-
формат (UNIMARC/RUSMARC у ИРБИС) на XML-раскладку не влияет — это транспортный
конверт, как и ISO 2709.

Структура MARCXML (один record)
-------------------------------
::

    <record>
      <leader>...........</leader>
      <controlfield tag="001">12345</controlfield>
      <datafield tag="200" ind1=" " ind2=" ">
        <subfield code="a">Заглавие</subfield>
        <subfield code="f">Автор</subfield>
      </datafield>
    </record>

  * **leader** — 24-символьная строка-заголовок (как в ISO 2709). Мы генерируем
    каталожный «скелет» (см. ``_LEADER``); на разборе leader игнорируется (контент
    лежит в полях, не в leader).
  * **controlfield** — контрольное поле 00X (tag < 010): голое значение, без
    индикаторов/подполей. У нас это типично 001/005/100 и т.п. в bare-string
    форме.
  * **datafield** — поле с подполями: атрибуты ``ind1``/``ind2`` (индикаторы, по
    умолчанию пробел) + дочерние ``<subfield code="x">value</subfield>``.

Namespace
---------
По умолчанию пишем БЕЗ namespace-префикса, но с дефолтным namespace LOC
``http://www.loc.gov/MARC21/slim`` на корне (``xmlns=...``) — это стандартный
``MARC21slim``. Разбор устойчив и к namespaced, и к голому XML: мы сопоставляем
теги по локальному имени (``record``/``leader``/``controlfield``/``datafield``/
``subfield``), отбрасывая ``{ns}`` Clark-нотацию ElementTree. Передайте
``namespace=None`` в ``to_marcxml``/``to_marcxml_collection``, чтобы писать без
``xmlns`` вовсе.

Модель записи / нормализация
----------------------------
Та же модель, что в ``access/marc.py``: поле — bare string (скаляр/контрольное),
``{subfield: value}`` dict или список любого из этого. ``normalize`` (импортируем
из ``marc``) приводит запись к ``{tag3: [inst, ...]}``; именно эту форму выдаёт
round-trip ``from_marcxml(to_marcxml(r)) == normalize(r)``.

Робастность
-----------
  * Битый XML (``xml.etree.ElementTree.ParseError``) -> :class:`MarcXmlError` в
    одиночном ``from_marcxml``; в ``from_marcxml_collection`` -> ``[]`` (битый
    поток не должен ронять весь импорт).
  * Внутри валидного ``<collection>`` каждый ``<record>`` парсится независимо;
    отдельный битый record пропускается, а не отменяет батч.

Кодировка — utf-8 (кириллица сериализуется как есть). Чистый stdlib
(``xml.etree.ElementTree``), без pip, без сети.
"""
import xml.etree.ElementTree as ET

from access.marc import normalize, _norm_tag

__all__ = [
    'MarcXmlError', 'MARC21_SLIM_NS',
    'to_marcxml', 'from_marcxml',
    'to_marcxml_collection', 'from_marcxml_collection',
]

# Дефолтный namespace MARC21slim (Library of Congress).
MARC21_SLIM_NS = 'http://www.loc.gov/MARC21/slim'

# Каталожный «скелет» leader (24 символа) — те же позиции-константы, что в
# ISO 2709 (marc._LDR_*): status 'n', type 'a', biblevel 'm', indcount '2',
# sfcount '2', entry-map '4500'. Позиции длины/base-address для MARCXML не
# значимы (длина не считается), поэтому ставим нули-заполнитель.
_LEADER = '00000nam  2200000   4500'

DEFAULT_INDICATOR = ' '


class MarcXmlError(Exception):
    """Ошибка сериализации/разбора MARCXML (битый XML / структура)."""


# --------------------------------------------------------------------------- #
# Вспомогательное: локальное имя тега (отбрасываем namespace ElementTree).
# --------------------------------------------------------------------------- #
def _localname(tag):
    """Локальное имя XML-тега: ``{ns}record`` -> ``record`` (namespace-agnostic)."""
    if tag is None:
        return ''
    if '}' in tag:
        return tag.rsplit('}', 1)[1]
    return tag


# --------------------------------------------------------------------------- #
# Сериализация: record -> MARCXML.
# --------------------------------------------------------------------------- #
def _record_element(record, namespace):
    """Построить ``<record>`` Element из tag-keyed записи (нормализуя её).

    Контрольные поля (00X) и bare-string инстансы -> ``<controlfield>``; dict-
    инстансы с подполями -> ``<datafield>`` + ``<subfield>``. Поля упорядочены
    нормализацией по числовому тегу."""
    norm = normalize(record)
    rec_tag = '{%s}record' % namespace if namespace else 'record'
    rec = ET.Element(rec_tag)

    leader_tag = '{%s}leader' % namespace if namespace else 'leader'
    ET.SubElement(rec, leader_tag).text = _LEADER

    cf_tag = '{%s}controlfield' % namespace if namespace else 'controlfield'
    df_tag = '{%s}datafield' % namespace if namespace else 'datafield'
    sf_tag = '{%s}subfield' % namespace if namespace else 'subfield'

    for tag3 in sorted(norm.keys(), key=lambda t: int(t)):
        for inst in norm[tag3]:
            if isinstance(inst, dict):
                # поле с подполями -> datafield
                df = ET.SubElement(rec, df_tag)
                df.set('tag', tag3)
                df.set('ind1', DEFAULT_INDICATOR)
                df.set('ind2', DEFAULT_INDICATOR)
                for code, val in inst.items():
                    sf = ET.SubElement(df, sf_tag)
                    sf.set('code', str(code))
                    sf.text = str(val)
            else:
                # bare string -> controlfield (контрольные 00X и прочие скаляры)
                cf = ET.SubElement(rec, cf_tag)
                cf.set('tag', tag3)
                cf.text = str(inst)
    return rec


def _serialize(element, namespace):
    """Element -> строка XML (utf-8, с XML-декларацией).

    Если задан ``namespace``, регистрируем его как ДЕФОЛТНЫЙ (пустой префикс),
    чтобы ElementTree писал каноничный ``xmlns="..."`` (форма LOC MARC21slim), а
    не ``ns0:``-префикс. Декларацию добавляем вручную (``encoding='unicode'`` её
    не пишет), чтобы кириллица/кодировка не зависели от платформы."""
    if namespace:
        ET.register_namespace('', namespace)
    body = ET.tostring(element, encoding='unicode')
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


def to_marcxml(record, namespace=MARC21_SLIM_NS):
    """Сериализовать tag-keyed запись в MARCXML ``<record>`` (str, utf-8).

    Контрольные/скалярные поля -> ``<controlfield tag=...>value</controlfield>``;
    поля с подполями -> ``<datafield tag=... ind1=" " ind2=" ">`` с дочерними
    ``<subfield code=...>``. По умолчанию корень несёт дефолтный namespace
    LOC ``MARC21slim`` (``xmlns``); ``namespace=None`` пишет без него.

    Запись нормализуется (:func:`marc.normalize`), поэтому скаляры, одиночные и
    повторяющиеся поля раскладываются единообразно; round-trip:
    ``from_marcxml(to_marcxml(r)) == normalize(r)``."""
    return _serialize(_record_element(record, namespace), namespace)


def to_marcxml_collection(records, namespace=MARC21_SLIM_NS):
    """Сериализовать список записей в MARCXML ``<collection>`` (str, utf-8).

    Обёртка массового экспорта: ``<collection>`` с дочерними ``<record>`` по
    каждой записи. Пустой список -> валидный пустой ``<collection/>``."""
    coll_tag = '{%s}collection' % namespace if namespace else 'collection'
    coll = ET.Element(coll_tag)
    for rec in (records or []):
        coll.append(_record_element(rec, namespace))
    return _serialize(coll, namespace)


# --------------------------------------------------------------------------- #
# Разбор: MARCXML -> record.
# --------------------------------------------------------------------------- #
def _parse_record_element(rec_el):
    """Разобрать ``<record>`` Element в нормализованную tag-keyed запись.

    ``<controlfield>`` -> bare string; ``<datafield>`` -> ``{code: value}`` по
    дочерним ``<subfield>``; повторяющиеся поля -> список инстансов. Возвращает
    ту же форму, что :func:`marc.normalize` (``{tag3: [inst, ...]}``)."""
    record = {}
    for child in rec_el:
        name = _localname(child.tag)
        if name == 'controlfield':
            tag = child.get('tag')
            if tag is None:
                continue
            tag3 = _norm_tag(tag)
            val = child.text if child.text is not None else ''
            if val == '':
                continue
            record.setdefault(tag3, []).append(val)
        elif name == 'datafield':
            tag = child.get('tag')
            if tag is None:
                continue
            tag3 = _norm_tag(tag)
            sub = {}
            for sf in child:
                if _localname(sf.tag) != 'subfield':
                    continue
                code = sf.get('code')
                if code is None:
                    continue
                value = sf.text if sf.text is not None else ''
                if value == '':
                    continue
                sub[str(code)] = value
            if sub:
                record.setdefault(tag3, []).append(sub)
        # leader и прочие элементы игнорируем (контент лежит в полях)
    return record


def from_marcxml(xml_str):
    """Разобрать ОДИН MARCXML ``<record>`` (str/bytes) в tag-keyed запись.

    Возвращает ``{tag3: [inst, ...]}`` (как :func:`marc.normalize`):
    ``<controlfield>`` -> bare string, ``<datafield>`` -> ``{code: value}``,
    повторяющиеся поля -> список. Round-trip:
    ``from_marcxml(to_marcxml(r)) == normalize(r)``.

    Принимает корень ``<record>`` напрямую ИЛИ ``<collection>`` с ровно одним (или
    первым) ``<record>``. Поднимает :class:`MarcXmlError` на битом/пустом XML
    (:class:`xml.etree.ElementTree.ParseError`)."""
    if xml_str is None:
        raise MarcXmlError('пустой вход (None)')
    if isinstance(xml_str, bytes):
        try:
            xml_str = xml_str.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise MarcXmlError('вход не декодируется как utf-8') from exc
    if not xml_str.strip():
        raise MarcXmlError('пустой вход')
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as exc:
        raise MarcXmlError('битый MARCXML: %s' % (exc,)) from exc

    name = _localname(root.tag)
    if name == 'record':
        return _parse_record_element(root)
    if name == 'collection':
        for child in root:
            if _localname(child.tag) == 'record':
                return _parse_record_element(child)
        return {}
    # неожиданный корень — но, может, record вложен глубже; ищем первый record
    rec = root.find('.//' + _record_path(root))
    if rec is not None:
        return _parse_record_element(rec)
    raise MarcXmlError('корень не <record>/<collection>: %r' % (name,))


def _record_path(root):
    """Path-фрагмент для поиска ``record`` с учётом namespace корня."""
    if '}' in (root.tag or ''):
        ns = root.tag.rsplit('}', 1)[0][1:]
        return '{%s}record' % ns
    return 'record'


def from_marcxml_collection(xml_str):
    """Разобрать MARCXML ``<collection>`` (str/bytes) в список tag-keyed записей.

    Каждый дочерний ``<record>`` парсится :func:`_parse_record_element`. Устойчиво
    к битому/пустому входу:
      * пустой/пробельный вход или :class:`ParseError` -> ``[]`` (битый поток не
        роняет импорт);
      * одиночный ``<record>`` как корень тоже принимается (-> список из одного);
      * отдельный record без полей даёт пустой dict (сохраняется в списке)."""
    if not xml_str:
        return []
    if isinstance(xml_str, bytes):
        try:
            xml_str = xml_str.decode('utf-8')
        except UnicodeDecodeError:
            return []
    if not xml_str.strip():
        return []
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    name = _localname(root.tag)
    if name == 'record':
        return [_parse_record_element(root)]
    if name == 'collection':
        out = []
        for child in root:
            if _localname(child.tag) == 'record':
                out.append(_parse_record_element(child))
        return out
    # иной корень — соберём все record-потомки
    out = []
    for child in root.iter():
        if _localname(child.tag) == 'record':
            out.append(_parse_record_element(child))
    return out
