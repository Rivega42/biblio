#!/usr/bin/env python3
"""Тесты deployment — режимы развёртывания Biblio (own-store, issue #335).

Покрыто (на :memory: + фейковые часы):
  * set -> get -> resolve: назначенный тенант возвращает свой режим/топологию;
  * валидация: невалидный mode/topology -> ValueError; запись не происходит;
  * required_connections: overlay_jirbis -> ['irbis','jirbis']; full -> [];
    replace_irbis -> ['irbis']; неизвестный -> [];
  * default_modules: full -> 8 модулей; overlay_jirbis короче; копия (не алиас);
  * resolve неназначенного -> дефолты + configured=False;
  * resolve назначенного -> configured=True + корректные производные;
  * mode_meta по ключу/None; catalog() форма; upsert и list стора.

Запуск: py -3.12 tests/test_deployment.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import deployment as dep

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
        return '2026-06-28T00:00:%02dZ' % self.t


def _store():
    return dep.DeploymentStore(':memory:', now=Clock())


def _service():
    return dep.DeploymentService(store=_store())


def constants_checks():
    print('-- константы: режимы и топологии')
    keys = [m['key'] for m in dep.REPLACEMENT_MODES]
    check('режимы в нужном порядке',
          keys == ['overlay_jirbis', 'replace_irbis', 'replace_both', 'full'])
    check('каждый режим имеет нужные поля',
          all({'key', 'title', 'needs_irbis', 'needs_jirbis', 'description'}
              <= set(m) for m in dep.REPLACEMENT_MODES))
    topo = [t['key'] for t in dep.TOPOLOGIES]
    check('топологии в нужном порядке', topo == ['cloud', 'onprem'])
    check('дефолты', dep.DEFAULT_MODE == 'overlay_jirbis'
          and dep.DEFAULT_TOPOLOGY == 'cloud')


def mode_meta_checks():
    print('-- mode_meta')
    m = dep.mode_meta('replace_irbis')
    check('mode_meta находит режим', m is not None and m['key'] == 'replace_irbis')
    check('mode_meta needs флаги', m['needs_irbis'] is True
          and m['needs_jirbis'] is False)
    check('mode_meta неизвестного -> None', dep.mode_meta('нет') is None)


def required_connections_checks():
    print('-- required_connections')
    check("overlay_jirbis -> ['irbis','jirbis']",
          dep.required_connections('overlay_jirbis') == ['irbis', 'jirbis'])
    check("replace_irbis -> ['irbis']",
          dep.required_connections('replace_irbis') == ['irbis'])
    check("replace_both -> ['irbis','jirbis']",
          dep.required_connections('replace_both') == ['irbis', 'jirbis'])
    check('full -> []', dep.required_connections('full') == [])
    check('inforost не появляется автоматически',
          'inforost' not in dep.required_connections('overlay_jirbis'))
    check('неизвестный режим -> []', dep.required_connections('нет') == [])


def default_modules_checks():
    print('-- default_modules')
    check('full -> 8 модулей', len(dep.default_modules('full')) == 8)
    check('overlay_jirbis короче full',
          len(dep.default_modules('overlay_jirbis'))
          < len(dep.default_modules('full')))
    check('overlay_jirbis набор',
          dep.default_modules('overlay_jirbis') == ['opac', 'reader', 'admin'])
    check('replace_both = replace_irbis + 2',
          len(dep.default_modules('replace_both'))
          == len(dep.default_modules('replace_irbis')) + 2)
    # Возвращается копия — мутация результата не влияет на следующий вызов.
    lst = dep.default_modules('full')
    lst.append('xxx')
    check('default_modules отдаёт копию', len(dep.default_modules('full')) == 8)
    check('неизвестный режим -> []', dep.default_modules('нет') == [])


def store_checks():
    print('-- DeploymentStore: set/get/list/upsert')
    s = _store()
    check('get неназначенного -> None', s.get('lib1') is None)
    row = s.set('lib1', 'full', 'onprem')
    check('set вернул строку', row['mode'] == 'full' and row['topology'] == 'onprem')
    check('get после set', s.get('lib1')['mode'] == 'full')
    # upsert: повторный set обновляет ту же строку.
    s.set('lib1', 'replace_irbis', 'cloud')
    check('upsert обновил mode', s.get('lib1')['mode'] == 'replace_irbis')
    check('upsert обновил topology', s.get('lib1')['topology'] == 'cloud')
    s.set('lib2', 'overlay_jirbis', 'cloud')
    check('list две записи', len(s.list()) == 2)
    check('list отсортирован по tenant',
          [r['tenant'] for r in s.list()] == ['lib1', 'lib2'])
    check('updated_at проставлен', s.get('lib2')['updated_at'] is not None)


def service_set_validation_checks():
    print('-- DeploymentService.set: валидация')
    svc = _service()
    row = svc.set('t1', 'replace_both', 'onprem')
    check('валидный set ок', row['mode'] == 'replace_both')
    try:
        svc.set('t2', 'нет-такого', 'cloud')
        check('невалидный mode -> ValueError', False)
    except ValueError:
        check('невалидный mode -> ValueError', True)
    try:
        svc.set('t3', 'full', 'марс')
        check('невалидная topology -> ValueError', False)
    except ValueError:
        check('невалидная topology -> ValueError', True)
    # После провалов записи не появилось.
    check('сбойные set не записались',
          svc.store.get('t2') is None and svc.store.get('t3') is None)


def service_resolve_checks():
    print('-- DeploymentService.resolve')
    svc = _service()
    # Неназначенный -> дефолты + configured False.
    r = svc.resolve('newbie')
    check('resolve неназначенного: configured False', r['configured'] is False)
    check('resolve неназначенного: mode = дефолт',
          r['mode'] == dep.DEFAULT_MODE)
    check('resolve неназначенного: topology = дефолт',
          r['topology'] == dep.DEFAULT_TOPOLOGY)
    check('resolve неназначенного: подключения дефолта',
          r['required_connections'] == ['irbis', 'jirbis'])
    check('resolve неназначенного: tenant в ответе', r['tenant'] == 'newbie')
    # Назначенный -> configured True + производные по режиму.
    svc.set('lib', 'full', 'onprem')
    r2 = svc.resolve('lib')
    check('resolve назначенного: configured True', r2['configured'] is True)
    check('resolve назначенного: mode', r2['mode'] == 'full')
    check('resolve назначенного: topology', r2['topology'] == 'onprem')
    check('resolve назначенного: подключения []',
          r2['required_connections'] == [])
    check('resolve назначенного: 8 модулей',
          len(r2['default_modules']) == 8)
    check('resolve назначенного: mode_meta',
          r2['mode_meta'] is not None and r2['mode_meta']['key'] == 'full')


def catalog_checks():
    print('-- catalog')
    svc = _service()
    cat = svc.catalog()
    check('catalog содержит modes и topologies',
          set(cat) == {'modes', 'topologies'})
    check('catalog.modes == REPLACEMENT_MODES',
          cat['modes'] == dep.REPLACEMENT_MODES)
    check('catalog.topologies == TOPOLOGIES',
          cat['topologies'] == dep.TOPOLOGIES)


def main():
    constants_checks()
    mode_meta_checks()
    required_connections_checks()
    default_modules_checks()
    store_checks()
    service_set_validation_checks()
    service_resolve_checks()
    catalog_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
