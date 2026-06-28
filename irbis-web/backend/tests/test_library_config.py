#!/usr/bin/env python3
"""Тесты library_config — редактируемая конфигурация библиотеки per-tenant.

Покрыто (на :memory: + фейковые часы):
  * get неустановленного тенанта == DEFAULT_CONFIG (копия, не сам объект);
  * update name сохраняется и возвращается полная форма;
  * update requisites.inn НЕ затирает остальные поля requisites (deep-merge);
  * повторный update мёржит (накапливает изменения);
  * неизвестный верхнеуровневый ключ игнорируется;
  * patch не-dict -> ValueError;
  * public == get;
  * стор: set/get round-trip (кириллица цела), list_tenants сортированы.

Запуск: py -3.12 tests/test_library_config.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import library_config as lc

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
    return lc.LibraryConfigStore(':memory:', now=Clock())


def _service():
    return lc.LibraryConfigService(store=_store())


def default_checks():
    print('-- get неустановленного тенанта -> DEFAULT_CONFIG')
    svc = _service()
    got = svc.get('t1')
    check('равен DEFAULT_CONFIG', got == lc.DEFAULT_CONFIG)
    check('это копия, а не сам объект', got is not lc.DEFAULT_CONFIG)
    check('requisites — копия', got['requisites'] is not lc.DEFAULT_CONFIG['requisites'])
    # Мутация выдачи не портит дефолт.
    got['name'] = 'мутация'
    check('мутация выдачи не трогает DEFAULT_CONFIG', lc.DEFAULT_CONFIG['name'] == '')
    check('форма полная — есть все верхние ключи',
          set(got.keys()) == set(lc.DEFAULT_CONFIG.keys()))


def update_name_checks():
    print('-- update name сохраняется')
    svc = _service()
    out = svc.update('t1', {'name': 'СПб ГТБ'})
    check('update вернул name', out['name'] == 'СПб ГТБ')
    check('форма полная после update', out['requisites']['inn'] == '')
    check('повторный get отдаёт сохранённое', svc.get('t1')['name'] == 'СПб ГТБ')


def deep_merge_requisites_checks():
    print('-- deep-merge requisites: inn НЕ затирает email')
    svc = _service()
    svc.update('t1', {'requisites': {'email': 'mail@gtb.spb.ru'}})
    svc.update('t1', {'requisites': {'inn': '7700000000'}})
    cfg = svc.get('t1')
    check('inn записан', cfg['requisites']['inn'] == '7700000000')
    check('email НЕ затёрт', cfg['requisites']['email'] == 'mail@gtb.spb.ru')
    # Прочие requisites-поля остались дефолтными.
    check('kpp остался дефолтным', cfg['requisites']['kpp'] == '')


def repeated_update_checks():
    print('-- повторный update мёржит (накапливает)')
    svc = _service()
    svc.update('t1', {'name': 'Имя'})
    svc.update('t1', {'about': 'О библиотеке'})
    cfg = svc.get('t1')
    check('name сохранён после второго update', cfg['name'] == 'Имя')
    check('about добавлен', cfg['about'] == 'О библиотеке')
    # Третий update перезаписывает только своё поле.
    svc.update('t1', {'name': 'Новое имя'})
    cfg2 = svc.get('t1')
    check('name перезаписан', cfg2['name'] == 'Новое имя')
    check('about цел при перезаписи name', cfg2['about'] == 'О библиотеке')


def unknown_key_checks():
    print('-- неизвестный верхнеуровневый ключ игнорируется')
    svc = _service()
    out = svc.update('t1', {'name': 'X', 'hacker': 'drop', 'admin': True})
    check('известный ключ записан', out['name'] == 'X')
    check('неизвестный ключ не в форме', 'hacker' not in out)
    check('неизвестный ключ не в форме (admin)', 'admin' not in out)
    check('форма по-прежнему ровно из ключей DEFAULT_CONFIG',
          set(out.keys()) == set(lc.DEFAULT_CONFIG.keys()))


def validation_checks():
    print('-- patch не-dict -> ValueError')
    svc = _service()
    for bad in ('строка', 123, ['list'], None):
        try:
            svc.update('t1', bad)
            check('patch %r -> ValueError' % (bad,), False)
        except ValueError:
            check('patch %r -> ValueError' % (bad,), True)


def public_checks():
    print('-- public == get')
    svc = _service()
    svc.update('t1', {'name': 'Имя', 'requisites': {'inn': '7700'}})
    check('public совпадает с get', svc.public('t1') == svc.get('t1'))
    check('public неустановленного == DEFAULT_CONFIG',
          svc.public('пусто') == lc.DEFAULT_CONFIG)


def store_checks():
    print('-- LibraryConfigStore: set/get round-trip + list_tenants')
    s = _store()
    check('get отсутствующего -> None', s.get('нет') is None)
    s.set('t1', {'name': 'Театральная', 'requisites': {'inn': '7800'}})
    got = s.get('t1')
    check('set/get round-trip', got == {'name': 'Театральная', 'requisites': {'inn': '7800'}})
    check('кириллица цела', s.get('t1')['name'] == 'Театральная')
    # upsert: повторный set обновляет ту же строку.
    s.set('t1', {'name': 'Обновлено'})
    check('upsert обновил', s.get('t1') == {'name': 'Обновлено'})
    s.set('t2', {'name': 'Вторая'})
    check('list_tenants сортированы', s.list_tenants() == ['t1', 't2'])


def tenant_isolation_checks():
    print('-- изоляция тенантов в сервисе')
    svc = _service()
    svc.update('t1', {'name': 'Первая'})
    svc.update('t2', {'name': 'Вторая'})
    check('t1 независим', svc.get('t1')['name'] == 'Первая')
    check('t2 независим', svc.get('t2')['name'] == 'Вторая')
    check('третий тенант — дефолт', svc.get('t3') == lc.DEFAULT_CONFIG)


def main():
    default_checks()
    update_name_checks()
    deep_merge_requisites_checks()
    repeated_update_checks()
    unknown_key_checks()
    validation_checks()
    public_checks()
    store_checks()
    tenant_isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
