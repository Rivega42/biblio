#!/usr/bin/env python3
"""Тесты webhooks — исходящие вебхуки per-tenant (own-store, issue #356).

Покрыто (на :memory: + фейковые часы):
  * subscribe: валидный -> подписка; недопустимое событие -> ValueError;
    пустой url -> ValueError;
  * маскировка secret наружу (subscribe/list/set_active -> '***'/'');
  * sign: стабильный HMAC (одинаковый вход -> одинаковый хэш), пустой secret -> '';
  * build_payload: форма {event, ts, data};
  * prepare: 2 активные подписки -> 2 элемента с подписью; неактивная исключена;
    чужое событие -> []; подпись сделана РЕАЛЬНЫМ секретом (sign совпадает);
  * log_delivery + deliveries (журнал — отдельная таблица);
  * unsubscribe/set_active.

Запуск: py -3.12 tests/test_webhooks.py ; в агрегаторе test_access.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import webhooks as wh

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# Фейковые часы — детерминизм created_at / ts.
class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return '2026-06-27T00:00:%02dZ' % self.t


def _service():
    store = wh.WebhookStore(':memory:', now=Clock())
    return wh.WebhookService(store=store, now=Clock())


def subscribe_checks():
    print('-- subscribe: валидация события и url')
    svc = _service()
    sub = svc.subscribe('t1', 'record.created', 'https://ex.test/hook', 'sek')
    check('subscribe вернул id', isinstance(sub.get('id'), int))
    check('subscribe сохранил event', sub['event'] == 'record.created')
    check('subscribe сохранил url', sub['url'] == 'https://ex.test/hook')
    check('новая подписка active=1', sub['active'] == 1)
    try:
        svc.subscribe('t1', 'no.such.event', 'https://ex.test/x', 's')
        check('недопустимое событие -> ValueError', False)
    except ValueError:
        check('недопустимое событие -> ValueError', True)
    try:
        svc.subscribe('t1', 'record.created', '', 's')
        check('пустой url -> ValueError', False)
    except ValueError:
        check('пустой url -> ValueError', True)


def mask_checks():
    print('-- маскировка secret наружу')
    svc = _service()
    with_secret = svc.subscribe('t1', 'loan.issued', 'https://ex.test/a', 'topsecret')
    no_secret = svc.subscribe('t1', 'loan.issued', 'https://ex.test/b')
    check('subscribe маскирует заданный secret', with_secret['secret'] == '***')
    check('subscribe пустой secret -> ""', no_secret['secret'] == '')
    listed = svc.list('t1')
    check('list маскирует заданный secret',
          listed[0]['secret'] == '***')
    check('list пустой secret -> ""', listed[1]['secret'] == '')
    # реальный secret виден только на уровне стора, не наружу.
    raw = svc.store.get(with_secret['id'])
    check('реальный secret цел в сторе', raw['secret'] == 'topsecret')


def sign_checks():
    print('-- sign: стабильный HMAC, пустой secret -> ""')
    svc = _service()
    a = svc.sign('key', 'тело-вебхука')
    b = svc.sign('key', 'тело-вебхука')
    check('одинаковый вход -> одинаковый хэш', a == b)
    check('подпись непуста', len(a) == 64)  # sha256 hex
    check('другой ключ -> другая подпись', svc.sign('key2', 'тело-вебхука') != a)
    check('другое тело -> другая подпись', svc.sign('key', 'другое') != a)
    check('пустой secret -> ""', svc.sign('', 'тело-вебхука') == '')


def build_payload_checks():
    print('-- build_payload: форма {event, ts, data}')
    svc = _service()
    p = svc.build_payload('hold.placed', {'mfn': 42}, now_ts='2026-06-29T00:00:00Z')
    check('payload event', p['event'] == 'hold.placed')
    check('payload ts', p['ts'] == '2026-06-29T00:00:00Z')
    check('payload data', p['data'] == {'mfn': 42})
    check('payload только три ключа', set(p.keys()) == {'event', 'ts', 'data'})
    # без now_ts ts берётся из инжектированных часов (непуст).
    p2 = svc.build_payload('hold.placed', {})
    check('ts из часов при отсутствии now_ts', bool(p2['ts']))


def prepare_checks():
    print('-- prepare: план отправки по активным подпискам')
    svc = _service()
    s1 = svc.subscribe('t1', 'import.completed', 'https://ex.test/1', 'sec1')
    s2 = svc.subscribe('t1', 'import.completed', 'https://ex.test/2', 'sec2')
    # неактивная подписка на то же событие — должна быть исключена.
    s3 = svc.subscribe('t1', 'import.completed', 'https://ex.test/3', 'sec3')
    svc.set_active(s3['id'], False)
    # чужое событие у того же тенанта — не должно попасть.
    svc.subscribe('t1', 'loan.issued', 'https://ex.test/other', 'x')
    # чужой тенант на то же событие — не должно попасть.
    svc.subscribe('t2', 'import.completed', 'https://ex.test/foreign', 'y')

    plan = svc.prepare('t1', 'import.completed', {'count': 10})
    check('prepare вернул 2 элемента (активные)', len(plan) == 2)
    ids = sorted(item['subscription_id'] for item in plan)
    check('prepare включил обе активные', ids == sorted([s1['id'], s2['id']]))
    check('неактивная исключена',
          s3['id'] not in [item['subscription_id'] for item in plan])
    check('форма элемента plan',
          set(plan[0].keys()) ==
          {'subscription_id', 'url', 'event', 'payload', 'signature'})
    check('payload в элементе — форма {event,ts,data}',
          set(plan[0]['payload'].keys()) == {'event', 'ts', 'data'})

    # подпись сделана РЕАЛЬНЫМ секретом (не маскированным '***').
    item = next(i for i in plan if i['subscription_id'] == s1['id'])
    body = json.dumps(item['payload'], sort_keys=True)
    expected = svc.sign('sec1', body)
    check('prepare подписывает РЕАЛЬНЫМ секретом', item['signature'] == expected)
    check('подпись непуста и не маска',
          item['signature'] and item['signature'] != '***')

    # событие без подписок -> [].
    check('чужое событие -> []', svc.prepare('t1', 'record.created', {}) == [])
    check('чужой тенант изолирован',
          len(svc.prepare('t2', 'import.completed', {})) == 1)


def delivery_checks():
    print('-- log_delivery + deliveries (журнал — отдельная таблица)')
    svc = _service()
    sub = svc.subscribe('t1', 'loan.issued', 'https://ex.test/d', 'k')
    d1 = svc.store.log_delivery(sub['id'], 'loan.issued', 'ok')
    check('log_delivery вернул id', isinstance(d1.get('id'), int))
    check('log_delivery attempts по умолчанию 1', d1['attempts'] == 1)
    check('log_delivery status', d1['status'] == 'ok')
    svc.store.log_delivery(sub['id'], 'loan.issued', 'failed', attempts=3)
    rows = svc.store.deliveries(subscription_id=sub['id'])
    check('deliveries вернул 2 записи', len(rows) == 2)
    check('deliveries свежие сверху', rows[0]['status'] == 'failed')
    check('deliveries attempts сохранён', rows[0]['attempts'] == 3)
    # журнал по всем подпискам.
    check('deliveries без фильтра видит все', len(svc.store.deliveries()) == 2)


def lifecycle_checks():
    print('-- unsubscribe / set_active')
    svc = _service()
    sub = svc.subscribe('t1', 'record.created', 'https://ex.test/lc', 'k')
    off = svc.set_active(sub['id'], False)
    check('set_active выключил', off['active'] == 0)
    check('set_active маскирует secret', off['secret'] == '***')
    check('после выкл prepare пуст',
          svc.prepare('t1', 'record.created', {}) == [])
    on = svc.set_active(sub['id'], True)
    check('set_active включил обратно', on['active'] == 1)
    check('после вкл prepare снова есть',
          len(svc.prepare('t1', 'record.created', {})) == 1)
    check('set_active несуществующего -> None', svc.set_active(99999, True) is None)
    check('unsubscribe существующего -> True', svc.unsubscribe(sub['id']) is True)
    check('unsubscribe снова -> False', svc.unsubscribe(sub['id']) is False)
    check('после unsubscribe list пуст', svc.list('t1') == [])


def main():
    subscribe_checks()
    mask_checks()
    sign_checks()
    build_payload_checks()
    prepare_checks()
    delivery_checks()
    lifecycle_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
