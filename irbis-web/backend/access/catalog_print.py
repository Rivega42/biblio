#!/usr/bin/env python3
"""Печатные/выходные формы каталога — контур Каталогизатор (печать).

Рендер библиографических записей в человекочитаемые печатные формы аналога
ИРБИС64 (печать каталожных карточек / списков / индексов из АРМ Каталогизатор).
Чистый stdlib, без сети и pip — как ``access/pay.py`` / ``access/pft.py``.

Зачем отдельный модуль (а не ``pft.eval``)
------------------------------------------
``pft.py`` — это интерпретатор PFT-выражений (форматный язык ИРБИС): он умеет
произвольный шаблон, но требует написания ``.pft``-формата для каждой формы.
Здесь — НАБОР ГОТОВЫХ печатных форм каталога (карточка/список/индекс) с
ГОСТ-подобной типографикой «из коробки»: вызвал ``card(record)`` — получил
карточку. Это «верхний» слой над той же моделью записи, что у ``pft.py``.

Модель записи (та же I1-черновик, что у ``pft.py`` / ``access/flk.py``)::

    {
      "200": {"a": "Война и мир", "f": "Л. Толстой"},   # один экземпляр (dict)
      "210": {"a": "М.", "c": "Наука", "d": "2020"},
      "10":  {"a": "978-5-..."},
      "675": {"a": "82"},
      "700": [{"a": "Толстой"}],                          # повторяющееся = список
      "101": "rus",                                       # скаляр-поле
    }

Поле может быть скаляром (строка), ``{подполе: значение}``-словарём или списком
из того и другого. Парсинг устойчив ко всем трём формам (см. ``_subfield`` /
``_field_value`` — зеркало ``access/pft.py`` ``_instances`` / ``_inst_value``).
"""

# Метки полей UNIMARC/RUSMARC, которые рендерят формы (для читаемости кода).
TAG_TITLE = '200'        # заглавие и сведения об ответственности (^a загол., ^f отв.)
TAG_IMPRINT = '210'      # выходные данные (^a место, ^c издатель, ^d год)
TAG_ISBN = '10'          # ISBN (^a)
TAG_UDC = '675'          # индекс УДК (^a)
TAG_AUTHOR = '700'       # первый автор — индивидуальное имя (^a)


# --------------------------------------------------------------------------- #
# Устойчивые аксессоры записи (скаляр / {подполе:значение} / список) —
# зеркало access/pft.py, чтобы формы и PFT-движок «видели» запись одинаково.
# --------------------------------------------------------------------------- #
def _instances(record, tag):
    """Список экземпляров поля ``tag``. Скаляр/dict оборачиваются в [x]."""
    raw = record.get(tag) if record else None
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _subfield(inst, code):
    """Значение подполя ``code`` одного экземпляра (скаляр или dict).

    Для скалярного экземпляра подполя нет — возвращаем сам скаляр только когда
    подполе не запрошено (``code is None``). Регистронезависимо по ключу."""
    if isinstance(inst, dict):
        if code is None or code == '':
            return ''.join(str(v) for v in inst.values() if v)
        return (inst.get(code) or inst.get(code.lower())
                or inst.get(code.upper()) or '')
    # скаляр-поле: «целое значение» есть, отдельных подполей нет
    return '' if code else (str(inst) if inst else '')


def _field_value(record, tag, code=None):
    """Значение подполя ``code`` ПЕРВОГО непустого экземпляра поля (или '')."""
    for inst in _instances(record, tag):
        v = _subfield(inst, code)
        if v:
            return str(v)
    return ''


def _field_values(record, tag, code=None):
    """Значения подполя ``code`` по ВСЕМ экземплярам (пустые пропускаются)."""
    out = []
    for inst in _instances(record, tag):
        v = _subfield(inst, code)
        if v:
            out.append(str(v))
    return out


def _join(parts, sep):
    """Соединить непустые элементы разделителем (пустые опускаются)."""
    return sep.join(p for p in parts if p)


# --------------------------------------------------------------------------- #
# Готовые печатные формы.
# --------------------------------------------------------------------------- #
def card(record):
    """Каталожная карточка (ГОСТ-подобно) одной записи -> ``str``.

    Структура (зоны разделяются ``. — `` как в карточном описании):

        Автор. Заглавие
            . — Место : Издатель, Год
            . — ISBN
            . — УДК <индекс>

    Где:
      * автор/заглавие — ``200^f`` (сведения об ответственности) и ``200^a``;
      * выходные данные — ``210^a`` (место) ``: `` ``210^c`` (издатель)
        ``, `` ``210^d`` (год);
      * ISBN — ``10^a``; индекс УДК — ``675^a``.

    Пустые элементы и пустые зоны ОПУСКАЮТСЯ (нет ISBN -> зоны нет вовсе).
    """
    record = record or {}
    title = _field_value(record, TAG_TITLE, 'a')
    resp = _field_value(record, TAG_TITLE, 'f')

    # Заголовок описания: «Автор. Заглавие» (любая часть может отсутствовать).
    heading = _join([resp, title], '. ')

    # Зона выходных данных: «Место : Издатель, Год».
    place = _field_value(record, TAG_IMPRINT, 'a')
    publisher = _field_value(record, TAG_IMPRINT, 'c')
    year = _field_value(record, TAG_IMPRINT, 'd')
    imprint = _join([_join([place, publisher], ' : '), year], ', ')

    isbn = _field_value(record, TAG_ISBN, 'a')
    udc = _field_value(record, TAG_UDC, 'a')
    udc_zone = ('УДК ' + udc) if udc else ''

    # Каждая последующая зона предваряется « . — » (область описания ГОСТ 7.1).
    zones = [z for z in (imprint, isbn, udc_zone) if z]
    out = heading
    for z in zones:
        out = (out + ' . — ' + z) if out else z
    return out


def brief_line(record):
    """Однострочное краткое библио-описание для списка -> ``str``.

    «Автор. Заглавие. — Место : Издатель, Год. — ISBN» в одну строку; пустые
    элементы опускаются. По сути компактная одностроковая форма ``card``."""
    record = record or {}
    title = _field_value(record, TAG_TITLE, 'a')
    resp = _field_value(record, TAG_TITLE, 'f')
    heading = _join([resp, title], '. ')

    place = _field_value(record, TAG_IMPRINT, 'a')
    publisher = _field_value(record, TAG_IMPRINT, 'c')
    year = _field_value(record, TAG_IMPRINT, 'd')
    imprint = _join([_join([place, publisher], ' : '), year], ', ')

    isbn = _field_value(record, TAG_ISBN, 'a')

    line = _join([heading, imprint, isbn], '. — ')
    # На всякий случай схлопываем переводы строк — описание ОДНОСТРОЧНОЕ.
    return ' '.join(line.split())


def catalog_list(records):
    """Нумерованный список кратких описаний -> ``str`` (по строке на запись).

    Записи без распознаваемых полей дают пустую ``brief_line`` и нумеруются как
    есть (форма не «теряет» запись). Пустой ввод -> ``''``."""
    records = records or []
    lines = []
    for i, rec in enumerate(records, start=1):
        lines.append('%d. %s' % (i, brief_line(rec)))
    return '\n'.join(lines)


def index_form(records, by=TAG_AUTHOR, code='a'):
    """Индекс (например авторский по ``700^a``) -> ``str``.

    Группирует записи по значению подполя ``by^code``, сортирует рубрики по
    алфавиту (кириллица — естественный порядок ``str``), под каждой рубрикой —
    краткие описания. Запись без значения попадает в рубрику «[без значения]».

        Толстой
          Война и мир. — М. : Наука, 2020
        Тургенев
          ...

    Возвращает ``''`` на пустом вводе.
    """
    records = records or []
    groups = {}
    NO_VALUE = '[без значения]'
    for rec in records:
        key = _field_value(rec or {}, by, code) or NO_VALUE
        groups.setdefault(key, []).append(rec)

    # Сортируем рубрики: «[без значения]» всегда в конце, остальное по алфавиту.
    def _sort_key(k):
        return (1, '') if k == NO_VALUE else (0, k.lower())

    out = []
    for key in sorted(groups, key=_sort_key):
        out.append(key)
        for rec in groups[key]:
            out.append('  ' + brief_line(rec))
    return '\n'.join(out)


def to_text(records, form='card', **kw):
    """Диспетчер форм. ``records`` — список записей (для ``card`` берётся первая,
    либо ``records`` может быть одной записью-словарём).

      * ``form='card'``  -> каталожные карточки (по записи, разделены пустой
        строкой);
      * ``form='list'``  -> нумерованный ``catalog_list``;
      * ``form='index'`` -> ``index_form`` (``by=`` / ``code=`` через ``**kw``).

    Неизвестная форма -> ``ValueError``. Пустой ввод -> ``''``.
    """
    # Допускаем как список записей, так и одну запись-словарь.
    if isinstance(records, dict):
        records = [records]
    records = records or []

    if form == 'card':
        return '\n\n'.join(card(rec) for rec in records)
    if form == 'list':
        return catalog_list(records)
    if form == 'index':
        by = kw.get('by', TAG_AUTHOR)
        code = kw.get('code', 'a')
        return index_form(records, by=by, code=code)
    raise ValueError('unknown print form: %r' % (form,))
