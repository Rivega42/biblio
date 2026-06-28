#!/usr/bin/env python3
"""Тесты IP_AUTH — реестр IP-диапазонов и авто-вход организации по IP.

Покрыто (in-memory + fake-clock для детерминизма):
  * `add_range` нормализует сеть (хост-биты схлопываются к адресу сети);
  * невалидный CIDR -> ValueError; пустой org -> ValueError;
  * `resolve` ip внутри диапазона -> та организация; ip вне всех -> None;
  * ПЕРЕСЕКАЮЩИЕСЯ диапазоны -> резолв отдаёт самый специфичный (большая /);
  * `enabled=False` диапазон не матчится в resolve;
  * некорректный ip-литерал -> None (резолв не падает);
  * IPv6-диапазон резолвит свой ip и НЕ матчит IPv4 (изоляция семейств);
  * `set_enabled` / `remove` / `list` — стор-операции.

Запуск: py -3.12 tests/test_ip_auth.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import ip_auth

PASS = [0]
FAIL = [0]

# Детерминированные «часы» для created_at (момент регистрации диапазона).
CLOCK = '2026-06-15T00:00:00+00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def svc():
    """Свежий сервис на чистом in-memory сторе с фиксированными часами."""
    return ip_auth.IpAuthService(
        store=ip_auth.IpRangeStore(':memory:', now=lambda: CLOCK),
        now=lambda: CLOCK)


def add_range_checks():
    print('-- add_range: нормализация сети, created_at от часов')
    s = svc()
    row = s.add_range('10.1.2.0/24', 'ВУЗ-А', role='reader', label='корпус-1')
    check('сохранён нормализованный cidr', row['cidr'] == '10.1.2.0/24')
    check('org сохранён', row['org'] == 'ВУЗ-А')
    check('role сохранён', row['role'] == 'reader')
    check('label сохранён', row['label'] == 'корпус-1')
    check('enabled по умолчанию 1', row['enabled'] == 1)
    check('created_at от часов', row['created_at'] == CLOCK)
    # хост-биты схлопываются к адресу сети (strict=False).
    row2 = s.add_range('10.1.2.5/24', 'ВУЗ-Б')
    check('хост-биты схлопнуты к адресу сети', row2['cidr'] == '10.1.2.0/24')
    # одиночный хост нормализуется в /32.
    row3 = s.add_range('192.168.0.7', 'ВУЗ-В')
    check('одиночный хост -> /32', row3['cidr'] == '192.168.0.7/32')


def validation_checks():
    print('-- add_range: валидация CIDR и org')
    s = svc()
    bad_cidr = False
    try:
        s.add_range('не-сеть', 'ВУЗ')
    except ValueError:
        bad_cidr = True
    check('невалидный CIDR -> ValueError', bad_cidr is True)
    bad_cidr2 = False
    try:
        s.add_range('10.0.0.0/99', 'ВУЗ')
    except ValueError:
        bad_cidr2 = True
    check('невалидный префикс -> ValueError', bad_cidr2 is True)
    empty_org = False
    try:
        s.add_range('10.0.0.0/8', '')
    except ValueError:
        empty_org = True
    check('пустой org -> ValueError', empty_org is True)


def resolve_basic_checks():
    print('-- resolve: внутри диапазона -> организация; вне -> None')
    s = svc()
    s.add_range('10.1.2.0/24', 'ВУЗ-А', role='reader')
    hit = s.resolve('10.1.2.5')
    check('ip внутри -> найден', hit is not None)
    check('ip внутри -> та организация', hit['org'] == 'ВУЗ-А')
    check('ip внутри -> отдана роль', hit['role'] == 'reader')
    check('ip вне всех -> None', s.resolve('8.8.8.8') is None)
    # граничные адреса сети 10.1.2.0/24.
    check('сетевой адрес матчит', s.resolve('10.1.2.0')['org'] == 'ВУЗ-А')
    check('broadcast матчит', s.resolve('10.1.2.255')['org'] == 'ВУЗ-А')
    check('сосед вне сети -> None', s.resolve('10.1.3.0') is None)


def overlap_specificity_checks():
    print('-- resolve: пересечение -> самый специфичный (большая prefixlen)')
    s = svc()
    s.add_range('10.0.0.0/8', 'ВУЗ-A-широкий')      # /8
    s.add_range('10.1.2.0/24', 'ВУЗ-B-узкий')       # /24 внутри /8
    hit = s.resolve('10.1.2.5')
    check('пересечение -> узкий /24 выигрывает', hit['org'] == 'ВУЗ-B-узкий')
    check('узкий cidr именно /24', hit['cidr'] == '10.1.2.0/24')
    # ip вне узкого, но внутри широкого -> широкий.
    hit2 = s.resolve('10.9.9.9')
    check('вне узкого, внутри широкого -> широкий',
          hit2['org'] == 'ВУЗ-A-широкий')
    # порядок добавления не влияет: добавим ещё более узкий /32.
    s.add_range('10.1.2.5/32', 'ВУЗ-C-точечный')
    hit3 = s.resolve('10.1.2.5')
    check('самый узкий /32 выигрывает', hit3['org'] == 'ВУЗ-C-точечный')


def enabled_checks():
    print('-- resolve: выключенный диапазон не матчится; set_enabled')
    s = svc()
    row = s.add_range('172.16.0.0/12', 'ВУЗ-OFF')
    check('пока включён -> матчится', s.resolve('172.16.5.5') is not None)
    upd = s.set_enabled(row['id'], False)
    check('set_enabled вернул запись', upd is not None)
    check('enabled стал 0', upd['enabled'] == 0)
    check('выключенный -> resolve None', s.resolve('172.16.5.5') is None)
    s.set_enabled(row['id'], True)
    check('снова включён -> матчится', s.resolve('172.16.5.5') is not None)


def bad_ip_checks():
    print('-- resolve: некорректный ip-литерал -> None (без падения)')
    s = svc()
    s.add_range('10.0.0.0/8', 'ВУЗ')
    check('мусор -> None', s.resolve('не-айпи') is None)
    check('октет вне диапазона -> None', s.resolve('10.0.0.999') is None)
    check('пустая строка -> None', s.resolve('') is None)
    check('None -> None', s.resolve(None) is None)


def ipv6_checks():
    print('-- resolve: IPv6-диапазон резолвит свой ip и НЕ матчит IPv4')
    s = svc()
    s.add_range('2001:db8::/32', 'ВУЗ-IPv6')
    hit = s.resolve('2001:db8::1')
    check('IPv6 ip внутри -> найден', hit is not None)
    check('IPv6 -> та организация', hit['org'] == 'ВУЗ-IPv6')
    check('IPv4 не матчит IPv6-сеть', s.resolve('10.0.0.1') is None)
    # обратная изоляция: IPv4-сеть не матчит IPv6-адрес.
    s2 = svc()
    s2.add_range('10.0.0.0/8', 'ВУЗ-IPv4')
    check('IPv6-адрес не матчит IPv4-сеть',
          s2.resolve('2001:db8::1') is None)


def store_ops_checks():
    print('-- list / remove / get: стор-операции')
    s = svc()
    a = s.add_range('10.0.0.0/8', 'A')
    b = s.add_range('172.16.0.0/12', 'B')
    c = s.add_range('192.168.0.0/16', 'C')
    check('list все -> 3', len(s.list()) == 3)
    check('list по id (первый — A)', s.list()[0]['org'] == 'A')
    s.set_enabled(b['id'], False)
    check('list enabled_only -> 2', len(s.list(enabled_only=True)) == 2)
    check('remove существующего -> True', s.remove(c['id']) is True)
    check('после remove list -> 2', len(s.list()) == 2)
    check('remove несуществующего -> False', s.remove(99999) is False)
    check('set_enabled несуществующего -> None',
          s.set_enabled(99999, True) is None)
    check('store.get несуществующего -> None', s.store.get(99999) is None)
    # резолв после удаления C не находит его сеть.
    check('удалённый диапазон не резолвится',
          s.resolve('192.168.1.1') is None)
    # A остался активным.
    check('оставшийся A резолвится', s.resolve('10.5.5.5')['org'] == 'A')


def main():
    add_range_checks()
    validation_checks()
    resolve_basic_checks()
    overlap_specificity_checks()
    enabled_checks()
    bad_ip_checks()
    ipv6_checks()
    store_ops_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
