#!/usr/bin/env python3
"""Тесты METADATA TEMPLATES — шаблоны метаданных по типу издания (own-store).

Покрыто:
  * встроенные типы присутствуют (book/journal/map/dissertation/article);
  * skeleton('book') несёт тег 200 как required; неизвестный тип -> None;
  * стор: save_template upsert (новая/обновление-не-дубль), get_custom,
    list_custom, delete_custom; fields переживают JSON-раунд-трип;
  * service.save кастома ПЕРЕОПРЕДЕЛЯЕТ skeleton; types() помечает source;
  * валидация save: пустой/не-список fields и поле без 'tag' -> ValueError;
  * label по умолчанию из TYPE_LABELS.

Запуск: py -3.12 tests/test_metadata_templates.py ; в агрегаторе test_access.py.
ASCII `->` в принтах (cp1251-консоль падает на юникод-стрелках).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import metadata_templates

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Детерминированные часы для updated_at.
class _Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-01-01T00:00:%02dZ' % self.t


def _svc():
    """In-memory сервис с фейковыми часами."""
    return metadata_templates.TemplateService(
        store=metadata_templates.TemplateStore(':memory:', now=_Clock()))


def builtin_checks():
    print('-- builtin: типы и каркас')
    bt = metadata_templates.BUILTIN_TEMPLATES
    for t in ('book', 'journal', 'map', 'dissertation', 'article'):
        check('встроенный тип есть: ' + t, t in bt)
    check('TYPE_LABELS book -> Книга',
          metadata_templates.TYPE_LABELS['book'] == 'Книга')
    # У каждого встроенного типа 3–7 полей, у каждого поля непустой tag.
    ok_shape = True
    for t, fields in bt.items():
        if not (3 <= len(fields) <= 7):
            ok_shape = False
        for f in fields:
            if not f.get('tag') or not isinstance(f.get('label'), str):
                ok_shape = False
    check('каждый встроенный тип: 3-7 полей с tag/label', ok_shape)


def skeleton_checks():
    print('-- skeleton: каркас полей, required, неизвестный тип')
    svc = _svc()
    sk = svc.skeleton('book')
    check('skeleton book -> dict', isinstance(sk, dict))
    check('skeleton book label = Книга', sk['label'] == 'Книга')
    tag200 = [f for f in sk['fields'] if f['tag'] == '200']
    check('skeleton book содержит тег 200', len(tag200) == 1)
    check('тег 200 — required', tag200[0]['required'] is True)
    check('неизвестный тип -> None', svc.skeleton('zzz') is None)
    check('журнал несёт ISSN (011)',
          any(f['tag'] == '011' for f in svc.skeleton('journal')['fields']))
    # skeleton отдаёт КОПИИ — мутация не трогает встроенную константу.
    sk['fields'][0]['label'] = 'ИЗМЕНЕНО'
    check('skeleton возвращает копии (без мутации BUILTIN)',
          metadata_templates.BUILTIN_TEMPLATES['book'][0]['label'] == 'Заглавие')


def store_checks():
    print('-- store: save_template / get_custom / list / delete')
    s = metadata_templates.TemplateStore(':memory:', now=_Clock())
    fields = [{'tag': '200', 'label': 'Заглавие', 'required': True,
               'repeatable': False, 'hint': 'тест'}]
    saved = s.save_template('book', fields, label='Моя книга')
    check('save_template вернул dict', isinstance(saved, dict))
    check('label сохранён', saved['label'] == 'Моя книга')
    check('fields пережили JSON-раунд-трип', saved['fields'] == fields)
    check('get_custom точный тип', s.get_custom('book')['label'] == 'Моя книга')
    check('get_custom промах -> None', s.get_custom('journal') is None)
    # Обновление того же типа — не дубль, новые значения.
    s.save_template('book', fields, label='Книга v2')
    check('save_template update label', s.get_custom('book')['label'] == 'Книга v2')
    check('save_template update не плодит дубль', len(s.list_custom()) == 1)
    s.save_template('map', fields, label='Карта')
    check('list_custom 2 шаблона', len(s.list_custom()) == 2)
    check('list_custom несёт type/label',
          {'type', 'label'} <= set(s.list_custom()[0].keys()))
    check('delete_custom True', s.delete_custom('map') is True)
    check('delete снизил счёт', len(s.list_custom()) == 1)
    check('delete несуществующего -> False', s.delete_custom('zzz') is False)


def service_save_checks():
    print('-- service.save: переопределение, source, label по умолчанию')
    svc = _svc()
    custom_fields = [{'tag': '999', 'label': 'Спецполе', 'required': True,
                      'repeatable': False, 'hint': 'кастом'}]
    out = svc.save('book', custom_fields)
    check('save вернул сохранённый кастом', out['fields'] == custom_fields)
    check('save label по умолчанию из TYPE_LABELS', out['label'] == 'Книга')
    # Кастом переопределяет skeleton.
    sk = svc.skeleton('book')
    check('кастом переопределяет skeleton (тег 999)',
          [f['tag'] for f in sk['fields']] == ['999'])
    check('кастом убрал встроенный 200 из skeleton',
          not any(f['tag'] == '200' for f in sk['fields']))
    # types() помечает source.
    by_type = {t['type']: t for t in svc.types()}
    check('types() book помечен custom', by_type['book']['source'] == 'custom')
    check('types() journal остаётся builtin', by_type['journal']['source'] == 'builtin')
    check('types() покрывает все встроенные', len(by_type) >= 5)
    # Явный label уважается.
    out2 = svc.save('map', custom_fields, label='Особая карта')
    check('save уважает явный label', out2['label'] == 'Особая карта')
    # Кастомный тип вне встроенного набора попадает в types().
    svc.save('newspaper', custom_fields, label='Газета')
    check('кастомный тип вне builtin виден в types()',
          any(t['type'] == 'newspaper' and t['source'] == 'custom'
              for t in svc.types()))


def validation_checks():
    print('-- validation: пустой/битый fields -> ValueError')
    svc = _svc()

    def raises(fn):
        try:
            fn()
            return False
        except ValueError:
            return True

    check('пустой список fields -> ValueError',
          raises(lambda: svc.save('book', [])))
    check('fields не список -> ValueError',
          raises(lambda: svc.save('book', 'нет')))
    check('поле без tag -> ValueError',
          raises(lambda: svc.save('book', [{'label': 'без тега'}])))
    check('поле с пустым tag -> ValueError',
          raises(lambda: svc.save('book', [{'tag': '   ', 'label': 'пробелы'}])))
    check('валидный минимум не падает',
          isinstance(svc.save('book', [{'tag': '200'}]), dict))


def main():
    builtin_checks()
    skeleton_checks()
    store_checks()
    service_save_checks()
    validation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
