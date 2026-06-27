#!/usr/bin/env python3
"""IIIF — генератор манифестов IIIF Presentation API v3 для трека «Оцифровка».

Контур **Оцифровка** (электронная библиотека/полнотекстовые образы): набор ЧИСТЫХ
функций, которые из каталожной записи и её оцифрованных образов (страниц) строят
JSON-структуры IIIF Presentation API v3 — Canvas, Manifest, Collection, Range.
Никакого состояния, никакого I/O и никаких записей в живой ИРБИС: на вход —
готовые данные (URL образов, размеры, метаданные), на выход — json-сериализуемые
dict, которые отдаёт IIIF-сервер (viewer Mirador/UV их потребляет напрямую).

Модель данных
-------------
Страница оцифровки — dict проекта::

    {'page_no': '1',           # номер/идентификатор страницы (str/int)
     'image': 'https://.../1.jpg',  # URL образа (опц.; иначе base_image_url+page_no)
     'width': 1200,            # ширина образа в пикселях
     'height': 1600}           # высота образа в пикселях

Все размеры (``width``/``height``) — целые пиксели. Метки (``label``) и значения
метаданных хранятся в IIIF как языковые карты ``{'ru': [...]}`` (язык-агностично,
но проект ведёт русскоязычный каталог).

Чистый stdlib (``json`` — только для проверки сериализуемости вызывающим кодом),
без pip и без сети.
"""

__all__ = [
    'IIIF_CONTEXT',
    'canvas', 'manifest', 'manifest_from_pages', 'collection', 'range_toc',
]

# JSON-LD контекст IIIF Presentation API v3 (обязателен в корне Manifest/Collection).
IIIF_CONTEXT = 'http://iiif.io/api/presentation/3/context.json'


def _lang_ru(text):
    """Языковая карта IIIF под одну русскоязычную строку -> ``{'ru': [text]}``.

    IIIF v3 требует, чтобы ``label``/``value`` были картами «язык -> список строк».
    Значение приводится к ``str`` (устойчиво к числам/None)."""
    return {'ru': ['' if text is None else str(text)]}


def canvas(canvas_id, label, image_url, width, height):
    """Canvas v3 с одной painting-аннотацией на образ страницы.

    Canvas — «холст» одной страницы: его геометрия (``width``/``height``) и
    единственная аннотация с ``motivation='painting'``, которая «рисует» образ
    (``body`` типа ``Image``, ``image/jpeg``) на цель ``target=canvas_id``.
    Аннотация обёрнута в один ``AnnotationPage`` (требование структуры v3).
    Возвращает json-сериализуемый dict."""
    return {
        'id': canvas_id,
        'type': 'Canvas',
        'label': _lang_ru(label),
        'width': width,
        'height': height,
        'items': [{
            'id': canvas_id + '/page/1',
            'type': 'AnnotationPage',
            'items': [{
                'id': canvas_id + '/annotation/1',
                'type': 'Annotation',
                'motivation': 'painting',
                'body': {
                    'id': image_url,
                    'type': 'Image',
                    'format': 'image/jpeg',
                    'width': width,
                    'height': height,
                },
                'target': canvas_id,
            }],
        }],
    }


def manifest(manifest_id, label, canvases, metadata=None):
    """Manifest v3 — объект оцифровки (издание) как список канв.

    ``canvases`` — список dict-канв (обычно из :func:`canvas`). При заданном
    ``metadata`` (список пар ``(label, value)``) добавляется блок ``'metadata'``
    с языковыми картами на каждую пару (порядок сохраняется). Корень несёт
    обязательный ``@context`` (:data:`IIIF_CONTEXT`). Возвращает json-сериализуемый
    dict."""
    out = {
        '@context': IIIF_CONTEXT,
        'id': manifest_id,
        'type': 'Manifest',
        'label': _lang_ru(label),
        'items': list(canvases or []),
    }
    if metadata:
        out['metadata'] = [
            {'label': _lang_ru(k), 'value': _lang_ru(v)} for k, v in metadata
        ]
    return out


def manifest_from_pages(manifest_id, label, base_image_url, pages, metadata=None):
    """Собрать Manifest из списка страниц оцифровки (удобный конструктор).

    Для каждой страницы ``pages`` (форма ``{'page_no','image','width','height'}``)
    строится Canvas:

    * ``id`` канвы = ``manifest_id + '/canvas/' + str(page_no)``;
    * URL образа = ``page['image']`` если задан, иначе ``base_image_url + str(page_no)``
      (конкатенация — вызывающий код задаёт ``base_image_url`` с разделителем сам);
    * ``label`` канвы = номер страницы.

    Делегирует сборку корня :func:`manifest` (включая ``metadata``). Пустой
    ``pages`` -> Manifest без канв. Возвращает json-сериализуемый dict."""
    canvases = []
    for page in (pages or []):
        page_no = str(page.get('page_no'))
        canvas_id = manifest_id + '/canvas/' + page_no
        image_url = page.get('image')
        if not image_url:
            image_url = base_image_url + page_no
        canvases.append(canvas(
            canvas_id, page_no, image_url,
            page.get('width'), page.get('height')))
    return manifest(manifest_id, label, canvases, metadata)


def collection(collection_id, label, manifest_refs):
    """Collection v3 — список ссылок на манифесты (фонд/раздел оцифровки).

    ``manifest_refs`` — список пар ``(id, label)``: каждый элемент превращается в
    краткую ссылку ``{'id', 'type':'Manifest', 'label':{'ru':[label]}}``. Корень
    несёт ``@context``. Возвращает json-сериализуемый dict."""
    return {
        '@context': IIIF_CONTEXT,
        'id': collection_id,
        'type': 'Collection',
        'label': _lang_ru(label),
        'items': [
            {'id': ref_id, 'type': 'Manifest', 'label': _lang_ru(ref_label)}
            for ref_id, ref_label in (manifest_refs or [])
        ],
    }


def range_toc(manifest_id, label, entries):
    """Range v3 — оглавление (структура) манифеста по списку id канв.

    Строит верхнеуровневый Range ``manifest_id + '/range/top'`` со списком ссылок на
    канвы (``entries`` — список ``canvas_id``), каждая как ``{'id', 'type':'Canvas'}``.
    Используется viewer'ом для навигации «оглавление -> страница». Возвращает
    json-сериализуемый dict."""
    return {
        'id': manifest_id + '/range/top',
        'type': 'Range',
        'label': _lang_ru(label),
        'items': [
            {'id': canvas_id, 'type': 'Canvas'} for canvas_id in (entries or [])
        ],
    }
