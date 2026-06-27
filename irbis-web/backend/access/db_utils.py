#!/usr/bin/env python3
"""DB_UTILS — инструментарий АРМ «Администратор/Утилиты» над списком записей.

Контур **Утилиты-АРМ** (статистика БД, выгрузки, пакетное обслуживание): набор
ЧИСТЫХ функций над списком уже загруженных каталожных записей — ровно как мапперы
``access/jirbis_migrate.py`` (никакого собственного стора, никакого I/O кроме
возврата строк). Вызывающий код достаёт записи из БД (catalog/marc) и передаёт их
сюда; модуль считает статистику, готовит выгрузки JSON/CSV и предпросмотры
обслуживания (дубли по ISBN/УДК, ФЛК-lite проверки на обязательные поля).

Форма записи
------------
Запись — MARC-подобный dict проекта::

    {'mfn': 123,
     'fields': [
         {'tag': '920', 'value': 'PAZK'},                       # поле данных (value)
         {'tag': '700', 'subfields': [{'code': 'a', 'value': 'Иванов'}]},
         {'tag': '210', 'subfields': [{'code': 'd', 'value': '2021'}]},
     ]}

Поле может нести ``value`` (скаляр) ИЛИ ``subfields`` (список ``{code, value}``).
Записи могут не иметь части тегов — все функции к этому устойчивы (defensive).

Спецификация тега (``tag_spec``)
--------------------------------
Строка вида ``'920'`` (всё поле -> его ``value``) или ``'200^a'`` (подполе ``a``
поля ``200``). При извлечении берётся ПЕРВОЕ совпадающее поле/подполе; если его
нет — пустая строка.

Чистый stdlib (json, csv, io, collections), без pip и без сети.
"""
import csv
import io
import json
from collections import Counter

__all__ = [
    'stats', 'fund_summary', 'export_json', 'export_csv',
    'field_histogram', 'field_histogram_sorted', 'duplicate_keys',
    'validate_batch',
]


# --------------------------------------------------------------------------- #
# Локальные аксессоры по форме записи проекта.
#
# marc.py оперирует ДРУГОЙ моделью (tag-keyed ``{tag: [inst]}``), а здесь запись —
# ``{'mfn', 'fields': [{'tag', 'value'|'subfields'}]}`` (как описано в ТЗ модуля),
# поэтому пишем небольшие свои хелперы под эту форму.
# --------------------------------------------------------------------------- #
def _fields(rec):
    """Список полей записи (устойчиво к отсутствию ключа/None)."""
    if not rec:
        return []
    flds = rec.get('fields')
    return flds if isinstance(flds, list) else []


def _field(rec, tag):
    """Первое поле записи с данным тегом или ``None`` (теги сравниваем как str)."""
    tag = str(tag)
    for f in _fields(rec):
        if isinstance(f, dict) and str(f.get('tag')) == tag:
            return f
    return None


def _fields_all(rec, tag):
    """Все поля записи с данным тегом (список; пустой, если нет)."""
    tag = str(tag)
    return [f for f in _fields(rec)
            if isinstance(f, dict) and str(f.get('tag')) == tag]


def _subfield(field, code):
    """Значение первого подполя с кодом ``code`` в поле или ``None``.

    Устойчиво к полю без ``subfields`` (скалярное поле данных)."""
    if not isinstance(field, dict):
        return None
    code = str(code)
    for sf in field.get('subfields') or []:
        if isinstance(sf, dict) and str(sf.get('code')) == code:
            return sf.get('value')
    return None


def _parse_spec(tag_spec):
    """Разобрать ``tag_spec`` -> ``(tag, code|None)``.

    ``'200^a'`` -> ``('200', 'a')``; ``'920'`` -> ``('920', None)``."""
    spec = str(tag_spec)
    if '^' in spec:
        tag, code = spec.split('^', 1)
        return tag.strip(), code.strip()
    return spec.strip(), None


def _extract(rec, tag_spec):
    """Извлечь ПЕРВОЕ значение по спецификации тега или ``''`` (никогда не None).

    Для ``tag^code`` — значение подполя; для голого тега — ``value`` поля."""
    tag, code = _parse_spec(tag_spec)
    fld = _field(rec, tag)
    if fld is None:
        return ''
    if code is None:
        val = fld.get('value')
        return '' if val is None else str(val)
    val = _subfield(fld, code)
    return '' if val is None else str(val)


# --------------------------------------------------------------------------- #
# Статистика БД (АРМ «Статистика»).
# --------------------------------------------------------------------------- #
def _year4(raw):
    """Выделить 4-значный год из значения 210^d ('2021' / '[2021]' / 'c2021').

    Возвращает строку года или ``None``, если 4 цифры подряд не нашлись."""
    if raw is None:
        return None
    s = str(raw)
    run = ''
    for ch in s:
        if ch.isdigit():
            run += ch
            if len(run) == 4:
                return run
        else:
            run = ''
    return None


def stats(records):
    """Сводная статистика по списку записей.

    Возвращает dict::

        {'count': N,
         'by_type': {920-value: count},          # вид документа (поле 920)
         'by_year': {год: count},                # 4 цифры из 210^d
         'by_language': {101^a: count},          # язык
         'with_exemplars': N,                    # записей с хотя бы одним 910
         'avg_fields': float}                    # среднее число полей на запись

    Устойчиво к отсутствию любых тегов: запись без 920/210/101/910 просто не
    попадает в соответствующий счётчик. Пустой список -> нули и ``avg_fields`` 0.0.
    """
    records = records or []
    by_type = Counter()
    by_year = Counter()
    by_language = Counter()
    with_exemplars = 0
    total_fields = 0

    for rec in records:
        flds = _fields(rec)
        total_fields += len(flds)

        t = _extract(rec, '920')
        if t:
            by_type[t] += 1

        y = _year4(_extract(rec, '210^d'))
        if y:
            by_year[y] += 1

        lang = _extract(rec, '101^a')
        if lang:
            by_language[lang] += 1

        if _fields_all(rec, '910'):
            with_exemplars += 1

    count = len(records)
    avg_fields = (total_fields / count) if count else 0.0
    return {
        'count': count,
        'by_type': dict(by_type),
        'by_year': dict(by_year),
        'by_language': dict(by_language),
        'with_exemplars': with_exemplars,
        'avg_fields': avg_fields,
    }


# --------------------------------------------------------------------------- #
# Сводка по фонду (экземпляры — поля 910).
# --------------------------------------------------------------------------- #
def fund_summary(records):
    """Сводка по экземплярам (поля 910) — для АРМ «Книгообеспеченность/Фонд».

    Проходит ВСЕ поля 910 во всех записях и считает::

        {'total_exemplars': N,
         'by_status': {910^a: count},      # статус экземпляра
         'by_location': {910^d: count}}    # место хранения / сигла

    Экземпляр без ^a / ^d просто не учитывается в соответствующем разрезе, но в
    ``total_exemplars`` входит (это физический 910). Пустой список -> нули."""
    total = 0
    by_status = Counter()
    by_location = Counter()
    for rec in (records or []):
        for f in _fields_all(rec, '910'):
            total += 1
            status = _subfield(f, 'a')
            if status not in (None, ''):
                by_status[str(status)] += 1
            loc = _subfield(f, 'd')
            if loc not in (None, ''):
                by_location[str(loc)] += 1
    return {
        'total_exemplars': total,
        'by_status': dict(by_status),
        'by_location': dict(by_location),
    }


# --------------------------------------------------------------------------- #
# Выгрузки (АРМ «Экспорт»).
# --------------------------------------------------------------------------- #
def export_json(records):
    """Сериализовать список записей в JSON (utf-8, кириллица как есть, отступ 2).

    ``ensure_ascii=False`` — кириллица сохраняется читаемой, не ``\\uXXXX``."""
    return json.dumps(records or [], ensure_ascii=False, indent=2)


def export_csv(records, fields):
    """Выгрузить записи в CSV: одна строка на запись, один столбец на спецификацию.

    ``fields`` — список спецификаций тегов (``'200^a'`` / ``'920'``). Первая строка
    CSV — заголовок (сами спецификации). В ячейку идёт ПЕРВОЕ совпавшее значение
    поля/подполя (или пустая строка, если в записи нет такого тега/подполя).
    Используется модуль :mod:`csv` поверх :class:`io.StringIO`; перевод строк
    нормализован (``\\n``)."""
    fields = list(fields or [])
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(fields)
    for rec in (records or []):
        writer.writerow([_extract(rec, spec) for spec in fields])
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Гистограмма заполненности полей (отчёт «какие поля заполнены»).
# --------------------------------------------------------------------------- #
def field_histogram(records):
    """Сколько раз каждый тег встречается во ВСЕХ записях -> ``{tag: count}``.

    Считаются вхождения полей (повторяющееся поле учитывается несколько раз), а
    не число записей с тегом. Пустой список -> ``{}``."""
    hist = Counter()
    for rec in (records or []):
        for f in _fields(rec):
            if isinstance(f, dict) and f.get('tag') is not None:
                hist[str(f['tag'])] += 1
    return dict(hist)


def field_histogram_sorted(records):
    """:func:`field_histogram` как список ``(tag, count)``, сорт. по убыванию.

    При равном счётчике — стабильно по тегу (возрастанию), чтобы вывод был
    детерминированным."""
    hist = field_histogram(records)
    return sorted(hist.items(), key=lambda kv: (-kv[1], kv[0]))


# --------------------------------------------------------------------------- #
# Предпросмотр дублей (обслуживание: «потенциальные дубли по ISBN/УДК»).
# --------------------------------------------------------------------------- #
def duplicate_keys(records, tag_spec):
    """Значения ``tag_spec``, встречающиеся БОЛЕЕ чем в одной записи.

    Возвращает ``{value: [mfn, ...]}`` только для тех значений, что встретились в
    >1 записи (предпросмотр дублей по ISBN ``'10^a'`` / УДК ``'675^a'`` и т.п.).
    Пустые значения игнорируются. Запись без ``mfn`` даёт ``None`` в списке (чтобы
    дубль всё равно был виден). Уникальные значения в результат НЕ попадают."""
    buckets = {}
    for rec in (records or []):
        val = _extract(rec, tag_spec)
        if not val:
            continue
        mfn = rec.get('mfn') if isinstance(rec, dict) else None
        buckets.setdefault(val, []).append(mfn)
    return {val: mfns for val, mfns in buckets.items() if len(mfns) > 1}


# --------------------------------------------------------------------------- #
# Пакетная проверка обязательных полей (ФЛК-lite перед импортом).
# --------------------------------------------------------------------------- #
def validate_batch(records, required_tags):
    """Найти записи без обязательных тегов (предимпортная ФЛК-lite проверка).

    Возвращает список ``{'mfn': mfn, 'missing': [tags]}`` ТОЛЬКО для записей, где
    отсутствует хотя бы один тег из ``required_tags`` (порядок ``missing`` повторяет
    ``required_tags``). Полные записи в результат не попадают. ``required_tags``
    сравниваются как строки тегов (без ``^code``)."""
    required = [str(t) for t in (required_tags or [])]
    out = []
    for rec in (records or []):
        missing = [t for t in required if _field(rec, t) is None]
        if missing:
            out.append({'mfn': rec.get('mfn') if isinstance(rec, dict) else None,
                        'missing': missing})
    return out
