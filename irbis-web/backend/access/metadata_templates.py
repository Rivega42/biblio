#!/usr/bin/env python3
"""METADATA TEMPLATES — шаблоны метаданных по типу издания АРМ «Каталогизатор» (own-store).

Продвигает эпик #240. Назначение: при каталогизации ПОДСКАЗЫВАТЬ каркас полей
под вид издания — какие RUSMARC/ИРБИС-теги стоит заполнить, что обязательно,
что повторяется. Это каркас-подсказка для UI каталогизации, а **не** ФЛК
(формально-логический контроль) и не запись в живой ИРБИС.

Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей — в точности как ``loan_policy.py``/``config_store.py``.
Никаких live-ИРБИС-записей.

Модель
------
  * :data:`BUILTIN_TEMPLATES` — встроенные каркасы по типам издания
    (``book``/``journal``/``map``/``dissertation``/``article``). Значение —
    список field-def: ``{'tag','label','required','repeatable','hint'}``.
  * :data:`TYPE_LABELS` — русские имена типов для UI.
  * таблица ``metadata_template`` — КАСТОМНЫЕ шаблоны библиотеки, которые
    ПЕРЕОПРЕДЕЛЯЮТ встроенные. Шаблон уникален по ``type``; список полей
    хранится как JSON-текст (``fields_json``).

Слои
----
``TemplateStore`` — низкоуровневый стор кастомных шаблонов
(upsert/get/list/delete). ``TemplateService`` — глубина: сведение встроенных
и кастомных типов, выдача каркаса (кастом бьёт встроенный), валидируемое
сохранение кастома.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Встроенные каркасы по виду издания. Каждое поле — подсказка каталогизатору:
# RUSMARC/ИРБИС-тег, русская подпись, обязательность, повторяемость, hint.
# Это НЕ ФЛК — теги подобраны разумно как скелет ввода (3–7 полей на тип).
BUILTIN_TEMPLATES = {
    'book': [
        {'tag': '200', 'label': 'Заглавие', 'required': True,
         'repeatable': False, 'hint': 'Основное заглавие (^a), сведения (^e), ответственность (^f)'},
        {'tag': '700', 'label': 'Первый автор', 'required': False,
         'repeatable': False, 'hint': 'Имя лица — первичная ответственность (^a фамилия, ^b инициалы)'},
        {'tag': '210', 'label': 'Выходные данные', 'required': False,
         'repeatable': False, 'hint': 'Место (^a), издатель (^c), год (^d)'},
        {'tag': '215', 'label': 'Объём', 'required': False,
         'repeatable': False, 'hint': 'Количество страниц (^a), иллюстрации (^c), размер (^d)'},
        {'tag': '010', 'label': 'ISBN', 'required': False,
         'repeatable': True, 'hint': 'Международный стандартный номер книги (^a)'},
        {'tag': '675', 'label': 'Индекс УДК', 'required': False,
         'repeatable': True, 'hint': 'Универсальная десятичная классификация (^a)'},
        {'tag': '606', 'label': 'Предметная рубрика', 'required': False,
         'repeatable': True, 'hint': 'Тематический предметный заголовок (^a)'},
    ],
    'journal': [
        {'tag': '200', 'label': 'Заглавие', 'required': True,
         'repeatable': False, 'hint': 'Основное заглавие сериального издания (^a)'},
        {'tag': '210', 'label': 'Выходные данные', 'required': False,
         'repeatable': False, 'hint': 'Место (^a), издатель (^c), год основания (^d)'},
        {'tag': '011', 'label': 'ISSN', 'required': False,
         'repeatable': True, 'hint': 'Международный стандартный номер сериального издания (^a)'},
        {'tag': '900', 'label': 'Вид документа', 'required': False,
         'repeatable': False, 'hint': 'Код вида — для сериального издания обычно 05'},
        {'tag': '934', 'label': 'Шифр сериального', 'required': False,
         'repeatable': False, 'hint': 'Служебный шифр/связка комплекта сериального издания'},
    ],
    'map': [
        {'tag': '200', 'label': 'Заглавие', 'required': True,
         'repeatable': False, 'hint': 'Основное заглавие картографического издания (^a)'},
        {'tag': '206', 'label': 'Математическая основа', 'required': False,
         'repeatable': False, 'hint': 'Масштаб, проекция, координаты (^a масштаб)'},
        {'tag': '210', 'label': 'Выходные данные', 'required': False,
         'repeatable': False, 'hint': 'Место (^a), издатель (^c), год (^d)'},
        {'tag': '215', 'label': 'Объём', 'required': False,
         'repeatable': False, 'hint': 'Число листов/карт (^a), цвет (^c), размер (^d)'},
    ],
    'dissertation': [
        {'tag': '200', 'label': 'Заглавие', 'required': True,
         'repeatable': False, 'hint': 'Тема диссертации (^a), сведения (^e)'},
        {'tag': '700', 'label': 'Автор', 'required': False,
         'repeatable': False, 'hint': 'Соискатель — первичная ответственность (^a фамилия, ^b инициалы)'},
        {'tag': '210', 'label': 'Выходные данные', 'required': False,
         'repeatable': False, 'hint': 'Место защиты (^a), год (^d)'},
        {'tag': '328', 'label': 'Сведения о диссертации', 'required': False,
         'repeatable': False, 'hint': 'Учёная степень, специальность, место/год защиты (^a)'},
        {'tag': '675', 'label': 'Индекс УДК', 'required': False,
         'repeatable': True, 'hint': 'Универсальная десятичная классификация (^a)'},
    ],
    'article': [
        {'tag': '200', 'label': 'Заглавие', 'required': True,
         'repeatable': False, 'hint': 'Заглавие статьи (^a)'},
        {'tag': '700', 'label': 'Первый автор', 'required': False,
         'repeatable': False, 'hint': 'Имя лица — первичная ответственность (^a фамилия, ^b инициалы)'},
        {'tag': '463', 'label': 'Источник (host)', 'required': False,
         'repeatable': False, 'hint': 'Связь с документом-источником: заглавие (^t), том/номер, страницы'},
        {'tag': 'premissia', 'label': 'Постраничная ссылка', 'required': False,
         'repeatable': False, 'hint': 'Диапазон страниц статьи в источнике'},
    ],
}

# Русские имена типов издания — для выпадающих списков/заголовков UI.
TYPE_LABELS = {
    'book': 'Книга',
    'journal': 'Журнал/сериальное',
    'map': 'Карта',
    'dissertation': 'Диссертация',
    'article': 'Статья',
}


def _utcnow():
    """Текущее время в ISO8601 (UTC, без микросекунд). Инжектируется как ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS metadata_template (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  type        TEXT UNIQUE,    -- тип издания (book/journal/map/...) — кастом бьёт встроенный
  label       TEXT,           -- русское имя шаблона для UI
  fields_json TEXT,           -- список field-def, сериализованный в JSON
  updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS metadata_template_type_idx
  ON metadata_template(type);
"""


class TemplateStore:
    """Собственный sqlite-стор КАСТОМНЫХ шаблонов метаданных. ``:memory:`` или
    файл; create-on-init. Соединение thread-local (домашний стиль); строки —
    dict. Список полей хранится как JSON-текст (``fields_json``).

    ``now`` инжектируется (по умолчанию :func:`_utcnow`, ISO8601) — чтобы
    тесты могли подставить детерминированные часы.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._local = threading.local()
        self._now = now or _utcnow
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    def save_template(self, type, fields, label=None):
        """Идемпотентно завести/обновить кастомный шаблон по ``type`` (upsert).

        ``fields`` — список field-def (dict); хранится как JSON-текст. Повторный
        вызов того же ``type`` обновляет поля/подпись/``updated_at`` (одна
        запись, не дубль). Возвращает шаблон (dict с распарсенным ``fields``)."""
        now = self._now()
        fields_json = json.dumps(fields, ensure_ascii=False)
        c = self._conn()
        c.execute(
            'INSERT INTO metadata_template(type,label,fields_json,updated_at) '
            'VALUES(?,?,?,?) '
            'ON CONFLICT(type) DO UPDATE SET '
            'label=excluded.label,fields_json=excluded.fields_json,'
            'updated_at=excluded.updated_at',
            (type, label, fields_json, now))
        c.commit()
        return self.get_custom(type)

    def get_custom(self, type):
        """Кастомный шаблон по ``type`` или ``None``.

        Возвращает ``{'type','label','fields'}`` с распарсенным из JSON списком
        полей."""
        r = self._conn().execute(
            'SELECT * FROM metadata_template WHERE type=?', (type,)).fetchone()
        if r is None:
            return None
        return {
            'type': r['type'],
            'label': r['label'],
            'fields': json.loads(r['fields_json']),
        }

    def list_custom(self):
        """Все кастомные шаблоны как ``[{'type','label'}, ...]`` (по id)."""
        return [{'type': r['type'], 'label': r['label']}
                for r in self._conn().execute(
                    'SELECT type,label FROM metadata_template ORDER BY id').fetchall()]

    def delete_custom(self, type):
        """Удалить кастомный шаблон по ``type``. Возвращает ``True``, если был."""
        c = self._conn()
        cur = c.execute('DELETE FROM metadata_template WHERE type=?', (type,))
        c.commit()
        return cur.rowcount > 0


class TemplateService:
    """Операции над :class:`TemplateStore` — сведение встроенных и кастомных
    типов, выдача каркаса полей (кастом бьёт встроенный), валидируемое
    сохранение кастома.

    Контракт для разводки в роуты «Каталогизатора»: ``types`` для списка видов
    издания, ``skeleton`` — каркас под выбранный вид, ``save`` — переопределение
    встроенного шаблона библиотечным.
    """

    def __init__(self, store=None, now=None):
        self.store = store or TemplateStore(':memory:', now=now)

    def types(self):
        """Все типы издания: встроенные + кастомные, помеченные источником.

        Возвращает ``[{'type','label','source'}, ...]``, где ``source`` —
        ``'custom'`` для типов с кастомным шаблоном (он переопределяет
        встроенный), иначе ``'builtin'``. Кастомные типы вне встроенного набора
        тоже попадают в список."""
        custom = {c['type']: c['label'] for c in self.store.list_custom()}
        result = []
        seen = set()
        # Встроенные типы — в стабильном порядке BUILTIN_TEMPLATES.
        for type in BUILTIN_TEMPLATES:
            seen.add(type)
            if type in custom:
                label = custom[type] or TYPE_LABELS.get(type, type)
                result.append({'type': type, 'label': label, 'source': 'custom'})
            else:
                result.append({'type': type, 'label': TYPE_LABELS.get(type, type),
                               'source': 'builtin'})
        # Кастомные типы, которых нет среди встроенных.
        for type, label in custom.items():
            if type not in seen:
                result.append({'type': type, 'label': label or TYPE_LABELS.get(type, type),
                               'source': 'custom'})
        return result

    def skeleton(self, type):
        """Каркас полей под вид издания ``type``.

        Если есть кастомный шаблон — отдаёт его поля; иначе встроенный.
        НЕИЗВЕСТНЫЙ тип (нет ни кастома, ни встроенного) -> ``None``.
        Возвращает ``{'type','label','fields':[...]}``."""
        custom = self.store.get_custom(type)
        if custom is not None:
            return {
                'type': type,
                'label': custom['label'] or TYPE_LABELS.get(type, type),
                'fields': custom['fields'],
            }
        builtin = BUILTIN_TEMPLATES.get(type)
        if builtin is not None:
            # Копии field-def, чтобы вызывающий не мутировал встроенную константу.
            return {
                'type': type,
                'label': TYPE_LABELS.get(type, type),
                'fields': [dict(f) for f in builtin],
            }
        return None

    def save(self, type, fields, label=None):
        """Сохранить кастомный шаблон, переопределяющий встроенный.

        Валидация: ``fields`` — непустой список dict, в каждом обязателен
        непустой строковый ``'tag'`` (иначе :class:`ValueError`). ``label`` по
        умолчанию = ``TYPE_LABELS.get(type, type)``. Возвращает сохранённый
        кастом ``{'type','label','fields'}``."""
        if not isinstance(fields, list) or not fields:
            raise ValueError('fields должен быть непустым списком')
        for f in fields:
            if not isinstance(f, dict):
                raise ValueError('каждое поле должно быть dict')
            tag = f.get('tag')
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError("каждое поле обязано нести непустой 'tag'")
        if label is None:
            label = TYPE_LABELS.get(type, type)
        return self.store.save_template(type, fields, label=label)
