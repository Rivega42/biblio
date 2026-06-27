#!/usr/bin/env python3
"""DEDUP — детект дублей записей каталога (контур Каталогизатор).

Дополняет ``union.py`` (свод между библиотеками): там дедупликация —
ПОБОЧНЫЙ эффект свода по сигле в собственный стор; здесь — ЧИСТЫЙ анализ
набора записей БЕЗ стора. Задача — copy-cataloging: при вводе новой записи
понять, есть ли уже такая в каталоге (дубль), и кластеризовать массив
записей по ключу дедупликации для пакетной чистки.

Ключ дедупликации ``dedup_key`` — та же ИДЕЯ, что в ``union.UnionCatalog``:
приоритет **ISBN (10^a)** > **шифр (903)** > нормализованный
**``title(200^a)|year(210^d)``**. ISBN нормализуется (цифры/X), текст —
нижний регистр + схлопнутые пробелы (кириллица/регистр едины).

Запись ``record`` — НАША tag-keyed запись (как в ``catalog.py``/``union.py``):
dict полей, где поле — скаляр, ``{подполе: значение}`` или список такого.
Парсинг устойчив к любой из трёх форм (см. :func:`_field_value`).

Чистый stdlib, без стора и без новых pip-зависимостей — в духе ``pay.py``.
"""
import re

# Поля записи, из которых строится ключ дедупликации (приоритет сверху вниз).
FIELD_ISBN = '10'        # 10^a — ISBN
SUB_ISBN = 'a'
FIELD_SHIFR = '903'      # 903 — шифр документа
FIELD_TITLE = '200'      # 200^a — заглавие
SUB_TITLE = 'a'
FIELD_PUBL = '210'       # 210^d — год издания
SUB_YEAR = 'd'


# --------------------------------------------------------------------------- #
# Парсинг tag-keyed записи (скаляр / dict / список) — зеркало union._field_value.
# --------------------------------------------------------------------------- #
def _field_value(rec, field, subfield=None):
    """Первое непустое значение ``field`` (опц. подполя) из записи ``rec``.

    Поле может быть скаляром, ``{подполе: значение}`` или списком такого;
    регистр подполя нечувствителен.
    """
    raw = rec.get(field) if rec else None
    if raw is None:
        return ''
    insts = raw if isinstance(raw, list) else [raw]
    for inst in insts:
        if isinstance(inst, dict):
            if subfield is None or subfield == '':
                v = (inst.get('') or inst.get('value')
                     or ''.join(str(x) for x in inst.values()))
            else:
                v = (inst.get(subfield) or inst.get(subfield.lower())
                     or inst.get(subfield.upper()) or '')
        else:
            v = inst if (subfield is None or subfield == '') else ''
        if v:
            return str(v)
    return ''


def _norm_isbn(raw):
    """Нормализовать ISBN: оставить цифры и финальный X (контр. символ)."""
    if not raw:
        return ''
    return re.sub(r'[^0-9X]', '', str(raw).upper())


def _norm_text(raw):
    """Нормализовать текст для ключа: нижний регистр, схлопнуть пробелы."""
    return re.sub(r'\s+', ' ', str(raw or '').strip().lower())


# --------------------------------------------------------------------------- #
# Ключ дедупликации — та же идея, что union.UnionCatalog.dedup_key.
# --------------------------------------------------------------------------- #
def dedup_key(record):
    """Ключ дедупликации записи: ISBN (10^a) > шифр (903) > ``title|year``.

    ISBN нормализуется (цифры/X); шифр — как есть (trim); fallback —
    нормализованные заглавие+год. Возвращает строку с типовым префиксом
    (``isbn:`` / ``shifr:`` / ``ty:``) — идентично ``union.py``.
    """
    isbn = _norm_isbn(_field_value(record, FIELD_ISBN, SUB_ISBN))
    if isbn:
        return 'isbn:' + isbn
    shifr = _field_value(record, FIELD_SHIFR).strip()
    if shifr:
        return 'shifr:' + shifr
    title = _norm_text(_field_value(record, FIELD_TITLE, SUB_TITLE))
    year = _norm_text(_field_value(record, FIELD_PUBL, SUB_YEAR))
    return 'ty:' + title + '|' + year


# --------------------------------------------------------------------------- #
# Кластеризация набора записей по ключу дедупликации.
# --------------------------------------------------------------------------- #
def cluster_map(records):
    """Все кластеры набора: ``{key: [idx...]}`` (включая одиночные).

    ``idx`` — позиция записи в ``records`` (0-based), порядок сохраняется.
    """
    clusters = {}
    for idx, record in enumerate(records or []):
        clusters.setdefault(dedup_key(record), []).append(idx)
    return clusters


def find_duplicates(records):
    """Кластеры дублей: ``[{'key':…, 'members':[idx…]}]`` для ключей с >1 записью.

    Одиночные ключи (уникальные записи) опускаются. ``members`` — позиции в
    ``records``; кластеры отсортированы по ключу для детерминизма.
    """
    clusters = cluster_map(records)
    return [{'key': key, 'members': members}
            for key, members in sorted(clusters.items())
            if len(members) > 1]


def is_duplicate(record, existing_records):
    """Индекс дубля ``record`` в ``existing_records`` или ``None``.

    Решение copy-cataloging: совпал ключ дедупликации с уже существующей
    записью -> вернуть её индекс (дубль), иначе ``None`` (запись новая).
    При нескольких совпадениях — индекс ПЕРВОГО (как при «слиянии в первую»).
    """
    key = dedup_key(record)
    for idx, existing in enumerate(existing_records or []):
        if dedup_key(existing) == key:
            return idx
    return None


def dedup_stats(records):
    """Сводка по дублируемости набора.

    Возвращает ``{total, unique_keys, duplicate_clusters, duplicate_records}``:
      * ``total`` — всего записей в наборе;
      * ``unique_keys`` — различных ключей дедупликации;
      * ``duplicate_clusters`` — ключей, под которыми >1 записи;
      * ``duplicate_records`` — «лишних» записей (которые ушли бы в слияние),
        т.е. ``total - unique_keys``.
    """
    clusters = cluster_map(records)
    total = sum(len(members) for members in clusters.values())
    unique_keys = len(clusters)
    dup_clusters = sum(1 for members in clusters.values() if len(members) > 1)
    return {
        'total': total,
        'unique_keys': unique_keys,
        'duplicate_clusters': dup_clusters,
        'duplicate_records': total - unique_keys,
    }
