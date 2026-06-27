#!/usr/bin/env python3
"""Тесты config_store — типизированные параметры АРМ «Администратор» (own-store).

Покрыто (на :memory: + фейковые часы):
  * вывод типа из Python-значения (bool/int/float/json/str, порядок bool>int);
  * round-trip set->get для int/float/bool/json/str (кириллица в json/str цела);
  * ValueError при несоответствии значения заявленному типу;
  * изоляция тенантов (один ключ, два тенанта, независимы);
  * get -> default при отсутствии; delete -> True/False; list с фильтром prefix;
  * typed_get -> TypeError при неверном expected_type; set_many all-or-nothing;
  * export/import при overwrite True/False; tenants() сортированы.

Запуск: py -3.12 tests/test_config_store.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import config_store as cs

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Фейковые часы — детерминизм updated_at.
class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-06-27T00:00:%02dZ' % self.t


def _store():
    return cs.ConfigStore(':memory:', now=Clock())


def _service():
    return cs.ConfigService(store=_store())


def type_inference_checks():
    print('-- вывод типа из Python-значения')
    s = _store()
    check('bool -> bool', s.set('b', True)['type'] == 'bool')
    check('int -> int', s.set('i', 7)['type'] == 'int')
    check('float -> float', s.set('f', 1.5)['type'] == 'float')
    check('dict -> json', s.set('d', {'k': 1})['type'] == 'json')
    check('list -> json', s.set('l', [1, 2])['type'] == 'json')
    check('str -> str', s.set('s', 'hi')['type'] == 'str')
    # bool раньше int (bool — подкласс int).
    check('True не уходит в int', s.set('bb', False)['type'] == 'bool')


def roundtrip_checks():
    print('-- round-trip set -> get для каждого типа')
    s = _store()
    s.set('i', 42)
    check('int round-trip', s.get('i') == 42 and isinstance(s.get('i'), int))
    s.set('f', 3.14)
    check('float round-trip', s.get('f') == 3.14 and isinstance(s.get('f'), float))
    s.set('bt', True)
    s.set('bf', False)
    check('bool True round-trip', s.get('bt') is True)
    check('bool False round-trip', s.get('bf') is False)
    s.set('j', {'имя': 'Иван', 'roles': [1, 2]})
    j = s.get('j')
    check('json round-trip (dict)', j == {'имя': 'Иван', 'roles': [1, 2]})
    check('json кириллица цела', j['имя'] == 'Иван')
    s.set('str', 'Привет, мир')
    check('str кириллица цела', s.get('str') == 'Привет, мир')
    # get_raw отдаёт десериализованное значение + тип + описание.
    s.set('withdesc', 100, description='лимит')
    raw = s.get_raw('withdesc')
    check('get_raw value десериализован', raw['value'] == 100)
    check('get_raw type', raw['type'] == 'int')
    check('get_raw description', raw['description'] == 'лимит')
    check('get_raw отсутствующего -> None', s.get_raw('нет') is None)


def validation_checks():
    print('-- валидация: ValueError при несоответствии типу')
    s = _store()
    try:
        s.set('x', 'abc', type='int')
        check('int+abc -> ValueError', False)
    except ValueError:
        check('int+abc -> ValueError', True)
    try:
        s.set('y', 'нет', type='float')
        check('float+нет -> ValueError', False)
    except ValueError:
        check('float+нет -> ValueError', True)
    try:
        s.set('z', 'maybe', type='bool')
        check('bool+maybe -> ValueError', False)
    except ValueError:
        check('bool+maybe -> ValueError', True)
    # Явный валидный тип принимается, строковое число под int ок.
    check('int из строки "5" ок', s.set('n', '5', type='int')['value'] == 5)
    check('bool из "1" ок', s.set('q', '1', type='bool')['value'] is True)


def tenant_checks():
    print('-- изоляция тенантов')
    s = _store()
    s.set('color', 'red', tenant='t1')
    s.set('color', 'blue', tenant='t2')
    check('t1 независим', s.get('color', tenant='t1') == 'red')
    check('t2 независим', s.get('color', tenant='t2') == 'blue')
    check('default не задет', s.get('color', default='none') == 'none')
    s.set('only', 1, tenant='t1')
    check('tenants() сортированы', s.tenants() == ['t1', 't2'])
    check('list тенанта изолирован',
          [r['key'] for r in s.list(tenant='t2')] == ['color'])


def list_delete_checks():
    print('-- list/prefix + delete + get default')
    s = _store()
    s.set('ui.theme', 'dark')
    s.set('ui.lang', 'ru')
    s.set('net.port', 6666)
    keys = [r['key'] for r in s.list()]
    check('list по ключу отсортирован', keys == ['net.port', 'ui.lang', 'ui.theme'])
    ui = [r['key'] for r in s.list(prefix='ui.')]
    check('prefix фильтр ui.', ui == ['ui.lang', 'ui.theme'])
    check('prefix без совпадений -> []', s.list(prefix='zzz') == [])
    check('get default при отсутствии', s.get('нет', default=99) == 99)
    check('delete существующего -> True', s.delete('ui.lang') is True)
    check('delete снова -> False', s.delete('ui.lang') is False)
    check('после delete get -> None', s.get('ui.lang') is None)


def upsert_checks():
    print('-- upsert: повторный set обновляет одну запись')
    s = _store()
    s.set('k', 1)
    s.set('k', 2)
    check('значение обновлено', s.get('k') == 2)
    check('запись одна (не дубль)', len(s.list()) == 1)
    # description сохраняется при обновлении значения без description.
    s.set('k2', 1, description='описание')
    s.set('k2', 5)
    check('description сохранён при upsert', s.get_raw('k2')['description'] == 'описание')
    # смена типа при upsert.
    s.set('k', 'строка', type='str')
    check('тип сменился на str', s.get_raw('k')['type'] == 'str' and s.get('k') == 'строка')


def service_checks():
    print('-- ConfigService: typed_get / set_many / export / import')
    svc = _service()
    svc.store.set('port', 8080)
    check('typed_get верный тип', svc.typed_get('port', 'int') == 8080)
    try:
        svc.typed_get('port', 'str')
        check('typed_get неверный тип -> TypeError', False)
    except TypeError:
        check('typed_get неверный тип -> TypeError', True)
    check('typed_get отсутствующего -> default',
          svc.typed_get('нет', 'int', default=-1) == -1)
    # set_many: тип выводится.
    rows = svc.set_many({'a': 1, 'b': True, 'c': 'текст'})
    check('set_many вернул 3 строки', len(rows) == 3)
    check('set_many вывел типы', svc.store.get_raw('b')['type'] == 'bool')


def setmany_atomic_checks():
    print('-- set_many: all-or-nothing на валидации')
    svc = _service()
    svc.store.set('existing', 1)
    # Чтобы получить сбой на ФАЗЕ валидации set_many, нужен объект, чей
    # json.dumps падает: значение-dict (выводится как json) с несериализуемым
    # множеством внутри. 'good' валиден -> проверяем, что он НЕ записан.
    bad = {'good': 5, 'bad': {'nested': {1, 2}}}  # dict -> json, внутри set -> сбой
    try:
        svc.set_many(bad)
        check('set_many сбой -> ValueError', False)
    except ValueError:
        check('set_many сбой -> ValueError', True)
    check('ни один ключ из сбойного батча не записан',
          svc.store.get_raw('good') is None)
    check('существующее не тронуто', svc.store.get('existing') == 1)


def export_import_checks():
    print('-- export / import (overwrite True/False)')
    svc = _service()
    svc.set_many({'a': 1, 'b': 'два', 'c': True})
    dump = svc.export()
    check('export round-trip', dump == {'a': 1, 'b': 'два', 'c': True})
    # import в новый тенант.
    n = svc.import_(dump, tenant='copy')
    check('import вернул count 3', n == 3)
    check('import перенёс значения', svc.store.get('b', tenant='copy') == 'два')
    # overwrite=False: существующие ключи пропускаются.
    svc.store.set('a', 999, tenant='copy')
    n2 = svc.import_({'a': 1, 'new': 7}, tenant='copy', overwrite=False)
    check('overwrite=False пропустил a, записал new', n2 == 1)
    check('overwrite=False не перезаписал a', svc.store.get('a', tenant='copy') == 999)
    check('overwrite=False записал new', svc.store.get('new', tenant='copy') == 7)
    # overwrite=True перезаписывает.
    n3 = svc.import_({'a': 5}, tenant='copy', overwrite=True)
    check('overwrite=True перезаписал a', n3 == 1 and svc.store.get('a', tenant='copy') == 5)


def main():
    type_inference_checks()
    roundtrip_checks()
    validation_checks()
    tenant_checks()
    list_delete_checks()
    upsert_checks()
    service_checks()
    setmany_atomic_checks()
    export_import_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
