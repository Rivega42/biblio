#!/usr/bin/env python3
"""Тесты connections — редактируемые внешние подключения per-tenant (own-store).

Покрыто (на :memory: + фейковые часы):
  * set irbis с паролем; get маскирует password ('***'), host виден открыто;
  * get_raw отдаёт РЕАЛЬНЫЙ password (внутренний слой);
  * обновление host с password='***' НЕ затирает реальный секрет (get_raw прежний);
  * обновление host с password='' тоже НЕ затирает (sentinel);
  * обновление новым НЕпустым password — реально меняет секрет;
  * невалидный kind -> ValueError; config не-dict -> ValueError;
  * remove -> True/False; list тенанта маскирован; for_tenant/изоляция тенантов;
  * field_hints('irbis'): password secret=True, host secret=False;
  * mask_config: пустой секрет -> '' (не звёздочки), несекретное поле цело.

Запуск: py -3.12 tests/test_connections.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import connections as cn

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


def _service():
    return cn.ConnectionService(store=cn.ConnectionStore(':memory:', now=Clock()))


def set_get_mask_checks():
    print('-- set irbis с паролем: get маскирует, host виден')
    svc = _service()
    pub = svc.set('t1', 'irbis', {
        'host': 'irbis.local', 'port': 6666, 'user': 'reader',
        'password': 's3cret', 'encoding': 'utf-8'})
    check('set вернул маскированный password', pub['config']['password'] == '***')
    check('set вернул host открыто', pub['config']['host'] == 'irbis.local')
    check('set kind в выдаче', pub['kind'] == 'irbis')
    check('set enabled по умолчанию True', pub['enabled'] is True)
    got = svc.get('t1', 'irbis')
    check('get маскирует password', got['config']['password'] == '***')
    check('get host виден', got['config']['host'] == 'irbis.local')
    check('get отсутствующего -> None', svc.get('t1', 'jirbis') is None)


def raw_checks():
    print('-- get_raw отдаёт реальный секрет (внутренний слой)')
    svc = _service()
    svc.set('t1', 'irbis', {'host': 'h', 'password': 's3cret'})
    raw = svc.get_raw('t1', 'irbis')
    check('get_raw реальный password', raw['config']['password'] == 's3cret')
    check('get_raw host', raw['config']['host'] == 'h')
    check('get_raw отсутствующего -> None', svc.get_raw('t1', 'inforost') is None)


def no_overwrite_secret_checks():
    print('-- обновление с ***/"" НЕ затирает секрет; новый пароль меняет')
    svc = _service()
    svc.set('t1', 'irbis', {'host': 'old', 'password': 's3cret'})
    # Обновляем host, пароль приходит как '***' (вернулся из UI) — не затирать.
    svc.set('t1', 'irbis', {'host': 'new', 'password': '***'})
    raw = svc.get_raw('t1', 'irbis')
    check('host обновлён', raw['config']['host'] == 'new')
    check('*** НЕ затёр реальный password', raw['config']['password'] == 's3cret')
    # Пустая строка тоже sentinel — не затирать.
    svc.set('t1', 'irbis', {'host': 'newer', 'password': ''})
    raw2 = svc.get_raw('t1', 'irbis')
    check('"" НЕ затёр реальный password', raw2['config']['password'] == 's3cret')
    check('host снова обновлён', raw2['config']['host'] == 'newer')
    # Новый НЕпустой пароль — реально меняет.
    svc.set('t1', 'irbis', {'host': 'newer', 'password': 'newpass'})
    raw3 = svc.get_raw('t1', 'irbis')
    check('новый непустой password применён', raw3['config']['password'] == 'newpass')
    check('get всё ещё маскирует обновлённый', svc.get('t1', 'irbis')['config']['password'] == '***')


def validation_checks():
    print('-- валидация kind / config')
    svc = _service()
    try:
        svc.set('t1', 'unknown', {'host': 'h'})
        check('невалидный kind -> ValueError', False)
    except ValueError:
        check('невалидный kind -> ValueError', True)
    try:
        svc.set('t1', 'irbis', ['not', 'a', 'dict'])
        check('config не-dict -> ValueError', False)
    except ValueError:
        check('config не-dict -> ValueError', True)
    # Валидный kind принимается.
    check('валидный kind inforost ок',
          svc.set('t1', 'inforost', {'base_url': 'u', 'api_key': 'k'})['kind'] == 'inforost')


def list_remove_checks():
    print('-- list (маскирован) / remove / изоляция тенантов')
    svc = _service()
    svc.set('t1', 'irbis', {'host': 'h1', 'password': 'p1'})
    svc.set('t1', 'jirbis', {'host': 'h2', 'password': 'p2'})
    svc.set('t2', 'irbis', {'host': 'other', 'password': 'pX'})
    lst = svc.list('t1')
    kinds = sorted(r['kind'] for r in lst)
    check('list тенанта вернул 2', len(lst) == 2 and kinds == ['irbis', 'jirbis'])
    check('list маскирован',
          all(r['config'].get('password') == '***' for r in lst))
    check('list изолирован по тенанту', [r['kind'] for r in svc.list('t2')] == ['irbis'])
    check('remove существующего -> True', svc.remove('t1', 'irbis') is True)
    check('remove снова -> False', svc.remove('t1', 'irbis') is False)
    check('после remove get -> None', svc.get('t1', 'irbis') is None)
    check('сосед по тенанту цел', svc.get('t1', 'jirbis') is not None)


def mask_config_checks():
    print('-- mask_config: пустой секрет -> "" (не звёздочки)')
    svc = _service()
    m = svc.mask_config({'host': 'h', 'password': '', 'api_key': 'live', 'port': 6666})
    check('пустой секрет -> ""', m['password'] == '')
    check('непустой секрет -> ***', m['api_key'] == '***')
    check('несекретное поле цело', m['host'] == 'h' and m['port'] == 6666)


def field_hints_checks():
    print('-- field_hints')
    svc = _service()
    hints = svc.field_hints('irbis')
    by_key = {h['key']: h for h in hints}
    check('field_hints irbis password secret=True', by_key['password']['secret'] is True)
    check('field_hints irbis host secret=False', by_key['host']['secret'] is False)
    check('field_hints неизвестного -> []', svc.field_hints('nope') == [])
    check('field_hints inforost api_key secret=True',
          {h['key']: h for h in svc.field_hints('inforost')}['api_key']['secret'] is True)


def constants_checks():
    print('-- константы модуля')
    check('KINDS', cn.KINDS == ('irbis', 'jirbis', 'inforost'))
    check('SECRET_FIELDS содержит password/api_key/token',
          {'password', 'api_key', 'token'} <= cn.SECRET_FIELDS)


def main():
    set_get_mask_checks()
    raw_checks()
    no_overwrite_secret_checks()
    validation_checks()
    list_remove_checks()
    mask_config_checks()
    field_hints_checks()
    constants_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
