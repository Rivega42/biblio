#!/usr/bin/env python3
"""Browse-указатели A–Z — алфавитный перебор терминов указателя со счётчиками.

Контур **«Быстрые победы»** (эпик #240): раздел перебора каталога по алфавиту.
Сценарий пользователя — открыть указатель A–Z (авторы / темы / места), кликнуть
по букве, увидеть термины этой буквы со счётчиками и провалиться в отфильтрованную
выдачу. Здесь — набор ЧИСТЫХ функций, которые группируют термины по первой букве
и подсчитывают их частоты прямо из каталожных записей. Никакого состояния, I/O или
обращений к живому ИРБИС: на вход — готовые термины/записи, на выход —
json-сериализуемые dict/list, которые отдаёт контроллер указателя.

Форма записи (как везде в проекте)
----------------------------------
Tag-keyed dict: поля — теги (строки), подполя — ключи внутри инстанса
(зеркалит ``access/oai_pmh.py`` / ``access/marcxml.py``)::

    {'700': [{'a': 'Иванов И.И.'}, {'a': 'Петров П.П.'}],   # повторяющееся поле
     '606': [{'a': 'Библиотеки'}],
     '101': 'rus'}

Поле может быть списком инстансов-dict ``[{code: value}]`` ИЛИ голым скаляром.
Для повторяющегося поля (несколько авторов в 700) учитывается КАЖДЫЙ инстанс —
своё значение подполя. Все функции устойчивы к отсутствию полей/None (defensive).

Обработка буквы Ё
-----------------
В русском указателе Ё СВОРАЧИВАЕТСЯ к Е (Ё→Е), чтобы не плодить почти пустой
раздел «Ё» и держать указатель компактным: термины «Ёлка» и «Енисей» попадают
в одну букву «Е». Это сознательный выбор в пользу компактности перебора.

Чистый stdlib, без pip и без сети.
"""

__all__ = [
    'LETTERS_RU', 'LETTERS_LAT', 'OTHER',
    'first_letter', 'bucket', 'aggregate', 'browse',
]

# Русский алфавит заглавными (с Ё — для проверки принадлежности; в указателе Ё→Е).
LETTERS_RU = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
# Латиница заглавными.
LETTERS_LAT = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
# Корзина «прочее»: цифры, знаки, всё не-буквенное.
OTHER = '#'

# Символы, которые игнорируются в начале термина при поиске первой значимой буквы
# (ведущие пробелы, кавычки разных видов, открывающие скобки — артефакты
# заглавий/предметных рубрик ИРБИС).
_LEADING_IGNORE = ' \t\r\n"\'«»„“”‘’()[]{}<>'


def first_letter(term):
    """Заглавная первая ЗНАЧИМАЯ буква термина (для раздела указателя A–Z).

    Алгоритм:

    * пустой/``None`` -> :data:`OTHER` (``'#'``);
    * ведущие пробелы/кавычки/скобки (см. ``_LEADING_IGNORE``) пропускаются;
    * найденный первый значимый символ:
        - русская буква -> заглавная, причём **Ё сворачивается к Е** (компактность
          указателя, см. модуль-docstring);
        - латинская буква -> заглавная;
        - любой другой символ (цифра/знак) -> :data:`OTHER`.

    Возвращает одиночный символ-букву из :data:`LETTERS_RU`/:data:`LETTERS_LAT`
    (кроме Ё) либо ``'#'``. Устойчиво к не-строковому входу."""
    if term is None:
        return OTHER
    s = str(term)
    # Пропустить ведущие незначимые символы.
    i = 0
    n = len(s)
    while i < n and s[i] in _LEADING_IGNORE:
        i += 1
    if i >= n:
        return OTHER
    ch = s[i].upper()
    if ch == 'Ё':           # свернуть Ё -> Е (см. модуль-docstring).
        ch = 'Е'
    if ch in LETTERS_RU or ch in LETTERS_LAT:
        return ch
    return OTHER


def _iter_pairs(entries):
    """Привести ``entries`` к потоку пар ``(term, count)`` (устойчиво к форме).

    Принимает итерируемое из dict ``{'term','count'}`` ИЛИ кортежей/списков
    ``(term, count)``. Отсутствующий ``count`` -> 1; не-числовой ``count`` -> 0.
    Пустой/None ``term`` пропускается. Внутренний хелпер для :func:`bucket`."""
    for ent in (entries or []):
        if isinstance(ent, dict):
            term = ent.get('term')
            cnt = ent.get('count', 1)
        elif isinstance(ent, (tuple, list)) and len(ent) >= 2:
            term, cnt = ent[0], ent[1]
        elif isinstance(ent, (tuple, list)) and len(ent) == 1:
            term, cnt = ent[0], 1
        else:
            continue
        if term is None:
            continue
        term = str(term)
        if term == '':
            continue
        try:
            cnt = int(cnt)
        except (TypeError, ValueError):
            cnt = 0
        yield term, cnt


def bucket(entries):
    """Сгруппировать термины-со-счётчиками в указатель A–Z.

    Вход ``entries`` — итерируемое из ``{'term','count'}`` ИЛИ кортежей
    ``(term, count)``. Возвращает dict::

        {'letters': [буквы в порядке присутствия],
         'buckets': {буква: [{'term','count'}, ...], ...}}

    Правила:

    * группировка — по :func:`first_letter` термина;
    * внутри буквы термины **сортируются по term** лексикографически
      без учёта регистра; счётчики совпадающих term (после ``str``) **суммируются**;
    * пустой ``term`` пропускается;
    * ``'letters'`` — только присутствующие буквы в порядке: сначала русские по
      :data:`LETTERS_RU`, затем латиница по :data:`LETTERS_LAT`, затем ``'#'``
      (:data:`OTHER`), если он есть.

    Возвращает json-сериализуемый dict."""
    # letter -> {term: count} (суммирование одинаковых term).
    acc = {}
    for term, cnt in _iter_pairs(entries):
        letter = first_letter(term)
        per = acc.setdefault(letter, {})
        per[term] = per.get(term, 0) + cnt

    buckets = {}
    for letter, terms in acc.items():
        # Сортировка по term без учёта регистра (стабильно по самому term).
        ordered = sorted(terms.items(), key=lambda kv: (kv[0].lower(), kv[0]))
        buckets[letter] = [{'term': t, 'count': c} for t, c in ordered]

    # Порядок букв: русские по LETTERS_RU (с учётом Ё→Е уже не появится),
    # затем латиница, затем '#'.
    letters = []
    for ch in LETTERS_RU:
        if ch == 'Ё':          # Ё в buckets не попадает (свёрнут в Е) — пропустить.
            continue
        if ch in buckets:
            letters.append(ch)
    for ch in LETTERS_LAT:
        if ch in buckets:
            letters.append(ch)
    if OTHER in buckets:
        letters.append(OTHER)

    return {'letters': letters, 'buckets': buckets}


def _instances(record, tag):
    """Список инстансов поля ``tag`` (устойчиво к отсутствию/скаляру/None).

    Зеркалит ``access/oai_pmh.py``: голый скаляр оборачивается в одноэлементный
    список (единообразная итерация), список инстансов остаётся как есть."""
    if not isinstance(record, dict):
        return []
    val = record.get(tag)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _values(record, tag, subfield):
    """Все значения подполя ``subfield`` поля ``tag`` по ВСЕМ инстансам.

    Для повторяющегося поля (несколько авторов в 700) возвращает значение из
    каждого инстанса. Если ``subfield`` пуст (``''``/``None``) — поле трактуется
    как СКАЛЯР: берётся голая строка инстанса. Пустые/None значения опускаются.
    Зеркалит подход ``access/oai_pmh.py`` к tag-keyed форме."""
    out = []
    for inst in _instances(record, tag):
        if subfield:
            if isinstance(inst, dict):
                v = inst.get(subfield)
                if v is not None and v != '':
                    out.append(str(v))
        else:
            # Поле-скаляр: значащая голая строка (или dict без подполя — пропуск).
            if isinstance(inst, str):
                if inst != '':
                    out.append(inst)
    return out


def aggregate(records, tag, subfield='a'):
    """Подсчитать частоты значений подполя по списку tag-keyed записей.

    Сканирует каждую запись из ``records``, по полю ``tag`` берёт значение
    подполя ``subfield`` КАЖДОГО инстанса (повторяющееся поле -> несколько
    значений), и считает частоты. Пустой ``subfield`` -> поле трактуется как
    голый скаляр. Термины с пустым значением пропускаются. Устойчиво к
    отсутствию полей/None в любой записи.

    Возвращает список ``[{'term','count'}, ...]``, отсортированный по term
    без учёта регистра (стабильный, удобен для прямой передачи в :func:`bucket`)."""
    counts = {}
    for rec in (records or []):
        for v in _values(rec, tag, subfield):
            counts[v] = counts.get(v, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (kv[0].lower(), kv[0]))
    return [{'term': t, 'count': c} for t, c in ordered]


def browse(records, tag, subfield='a'):
    """Сквозной конструктор «из записей сразу в указатель A–Z».

    Удобная композиция :func:`bucket` поверх :func:`aggregate`: по списку
    tag-keyed записей считает частоты значений подполя ``tag``/``subfield`` и
    раскладывает их по буквам. Возвращает тот же dict, что :func:`bucket`
    (``{'letters', 'buckets'}``)."""
    return bucket(aggregate(records, tag, subfield))
