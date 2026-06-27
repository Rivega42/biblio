#!/usr/bin/env python3
"""Circulation integration-edge tests — рёбра 12.6/12.7 (устройства) + 3.5 (срок).

Замыкает «Книговыдача-швы» из INTEGRATION_MAP:

  * **3.5 — RDR.40 (40^E срок) -> A6 уведомления.** :meth:`CirculationEngine.scan_due`
    по выдачам «на руках» эмитит ``overdue`` (просрочка, ``days_overdue``) и
    ``due_soon`` (близкий срок, ``days_left``) через ``_emit`` -> A6; идемпотентно в
    пределах суток (dedup-ключ с дневным бакетом), на следующий день — снова.
  * **12.6 / 12.7 — device_event.loan_ref -> loan / hold_ref -> hold.** Когда операция
    инициирована устройством (``device_id``) и подключён ``devices``-хэндл
    (:class:`access.devices.DeviceService`), checkout/return/renew/place_hold/
    cancel_hold пишут строку ``device_event`` со ссылкой на выдачу/бронь.

Гарантии, на которые опирается слой правил (как у ``catalog=``/``notifications=``):
  * back-compat — без ``devices``-хэндла / без ``device_id`` устройство-журнал не
    трогается, операция проходит как раньше;
  * failure-isolation — падение домена устройств НЕ роняет операцию книговыдачи;
  * scan_due без A6-хэндла — события только возвращаются интентами, ничего не шлёт.

Запуск в домашнем стиле (как test_circ_notify.py)::
  py -3.12 tests/test_circ_seams.py  ->  ok ... + "N passed, M failed" + код выхода
Также регистрируется в агрегаторе tests/test_access.py (module_checks).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import notifications as nt
from access import devices as dv
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy, ALLOW, SECONDS_PER_DAY,
)

PASS = [0]
FAIL = [0]

DAY = SECONDS_PER_DAY
T0 = 1_700_000_000


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _wired(policy=None, category='В01', reader='R1', tenant='public'):
    """Circulation engine + свежая A6-очередь + recording-каналы.

    Возвращает ``(store, eng, queue, channels)``."""
    store = CirculationStore(':memory:')
    queue = nt.NotificationQueue(':memory:')
    eng = CirculationEngine(store=store, policy=policy or default_policy(),
                            notifications=queue, tenant=tenant)
    store.add_reader(reader, category=category)
    channels = {'email': nt.MemoryChannel('email'), 'sms': nt.MemoryChannel('sms')}
    return store, eng, queue, channels


def _drain(queue, channels):
    queue.process_once(channels)
    delivered = []
    for ch in channels.values():
        delivered.extend(ch.sent)
    return delivered


# --------------------------------------------------------------------------- #
# 3.5 — scan_due: overdue + due_soon, окно, рендер, идемпотентность.
# --------------------------------------------------------------------------- #
def scan_due_emit_checks():
    print('-- scan_due: overdue + due_soon эмитятся, far — нет')
    store, eng, queue, channels = _wired(category='В01')
    # просрочена на 5 дней
    overdue = store.add_loan('R1', 'BK-OD', T0 - 5 * DAY, T0 - 25 * DAY)
    # срок через 2 дня (окно по умолчанию 3) — «скоро»
    soon = store.add_loan('R1', 'BK-SOON', T0 + 2 * DAY, T0 - 18 * DAY)
    # срок через 10 дней — вне окна
    far = store.add_loan('R1', 'BK-FAR', T0 + 10 * DAY, T0 - 10 * DAY)

    d = eng.scan_due(T0)
    check('scan_due ALLOW', d.decision == ALLOW)
    check('overdue id попал в computed', overdue['id'] in d.computed['overdue'])
    check('due_soon id попал в computed', soon['id'] in d.computed['due_soon'])
    check('far НЕ в overdue', far['id'] not in d.computed['overdue'])
    check('far НЕ в due_soon', far['id'] not in d.computed['due_soon'])
    check('overdue vs due_soon без пересечения',
          not (set(d.computed['overdue']) & set(d.computed['due_soon'])))

    rows = queue.all()
    od = [r for r in rows if r['event'] == 'overdue']
    ds = [r for r in rows if r['event'] == 'due_soon']
    check('ровно один overdue в очереди', len(od) == 1)
    check('overdue адресован читателю R1', od and od[0]['recipient'] == 'R1')
    check('ровно один due_soon в очереди', len(ds) == 1)
    check('due_soon адресован читателю R1', ds and ds[0]['recipient'] == 'R1')
    check('far ничего не поставил в очередь (только 2 события)', len(rows) == 2)


def scan_due_render_checks():
    print('-- scan_due: рендер несёт days_overdue / days_left, без {плейсхолдеров}')
    store, eng, queue, channels = _wired(category='В01')
    store.add_loan('R1', 'BK-OD', T0 - 5 * DAY, T0 - 25 * DAY)
    store.add_loan('R1', 'BK-SOON', T0 + 2 * DAY, T0 - 18 * DAY)
    eng.scan_due(T0)
    delivered = _drain(queue, channels)

    od = [m for m in delivered if 'просрочен' in m['subject'].lower()
          or 'Просрочен' in m['subject']]
    ds = [m for m in delivered if 'срок возврата' in m['subject'].lower()]
    check('overdue доставлен', len(od) == 1)
    check('due_soon доставлен', len(ds) == 1)
    od_body = od[0]['body'] if od else ''
    ds_body = ds[0]['body'] if ds else ''
    check('overdue: days_overdue=5 в теле', '5' in od_body)
    check('overdue: нет {days_overdue}', '{days_overdue}' not in od_body)
    check('overdue: title = шифр BK-OD', 'BK-OD' in od_body)
    check('due_soon: days_left=2 в теле', '2' in ds_body)
    check('due_soon: нет {days_left}', '{days_left}' not in ds_body)
    check('due_soon: нет {due_date}', '{due_date}' not in ds_body)


def scan_due_idempotent_checks():
    print('-- scan_due: дедуп в пределах суток, новое напоминание на след. день')
    store, eng, queue, channels = _wired(category='В01')
    store.add_loan('R1', 'BK-OD', T0 - 5 * DAY, T0 - 25 * DAY)

    eng.scan_due(T0)
    eng.scan_due(T0)                       # тот же день -> dedup, без задвоения
    od_same = [r for r in queue.all() if r['event'] == 'overdue']
    check('повтор в тот же день не задваивает (1 строка)', len(od_same) == 1)

    eng.scan_due(T0 + 1 * DAY)             # следующий день -> новый dedup-ключ
    od_next = [r for r in queue.all() if r['event'] == 'overdue']
    check('на следующий день — новое напоминание (2 строки)', len(od_next) == 2)


def scan_due_window_and_filter_checks():
    print('-- scan_due: настраиваемое окно + фильтр по читателю')
    store, eng, queue, channels = _wired(category='В01')
    store.add_reader('R2', category='В01')
    # срок через 5 дней — вне дефолтного окна 3, но в окне 7
    store.add_loan('R1', 'BK-5', T0 + 5 * DAY, T0 - 15 * DAY)
    d_default = eng.scan_due(T0)
    check('окно 3: срок +5дн не «скоро»', not d_default.computed['due_soon'])
    d_wide = eng.scan_due(T0, due_soon_days=7)
    check('окно 7: срок +5дн уже «скоро»', len(d_wide.computed['due_soon']) == 1)

    # фильтр по читателю: просрочка у обоих, но скан только R2
    store2, eng2, queue2, channels2 = _wired(category='В01', reader='RA')
    store2.add_reader('RB', category='В01')
    store2.add_loan('RA', 'BK-A', T0 - 5 * DAY, T0 - 25 * DAY)
    lb = store2.add_loan('RB', 'BK-B', T0 - 5 * DAY, T0 - 25 * DAY)
    d_one = eng2.scan_due(T0, reader_id='RB')
    check('фильтр reader_id: только выдача RB', d_one.computed['overdue'] == [lb['id']])
    recips = {r['recipient'] for r in queue2.all()}
    check('фильтр reader_id: в очереди только RB', recips == {'RB'})


def scan_due_standalone_checks():
    print('-- scan_due: без A6 — только интенты, ничего не отправляется')
    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy())  # notifier=None
    store.add_reader('R1', category='В01')
    store.add_loan('R1', 'BK-OD', T0 - 5 * DAY, T0 - 25 * DAY)
    store.add_loan('R1', 'BK-SOON', T0 + 2 * DAY, T0 - 18 * DAY)
    d = eng.scan_due(T0)
    check('standalone: 2 интента возвращены', len(d.events) == 2)
    evs = {e['event'] for e in d.events}
    check('standalone: интенты overdue+due_soon', evs == {'overdue', 'due_soon'})
    check('standalone: интент несёт days_overdue',
          any(e['event'] == 'overdue' and e['payload'].get('days_overdue') == 5
              for e in d.events))


# --------------------------------------------------------------------------- #
# 12.6 / 12.7 — device_event.loan_ref / hold_ref.
# --------------------------------------------------------------------------- #
def _wired_devices(category='В01', reader='R1'):
    """Circulation engine с подключённым доменом устройств + зарегистрированной
    станцией. Возвращает ``(store, eng, svc, device_id)``."""
    store = CirculationStore(':memory:')
    svc = dv.DeviceService(dv.DeviceStore(':memory:'))
    dev = svc.register('GUID-ST1', dv.KIND_STATION, name='Станция-1',
                       library='spb-gtb')
    eng = CirculationEngine(store=store, policy=default_policy(), devices=svc)
    store.add_reader(reader, category=category)
    return store, eng, svc, dev['id']


def device_loan_ref_checks():
    print('-- 12.6: checkout/return/renew -> device_event.loan_ref')
    store, eng, svc, did = _wired_devices()

    d = eng.checkout('R1', 'BK-1', T0, device_id=did)
    loan = d.computed['loan']
    check('checkout ALLOW', d.decision == ALLOW)
    check('checkout вернул device_event id', d.computed.get('device_event') is not None)
    evs = svc.events(device_id=did)
    co = [e for e in evs if e['event_name'] == 'loan_checkout']
    check('device_event loan_checkout записан', len(co) == 1)
    check('loan_ref ссылается на выдачу', co and co[0]['loan_ref'] == loan['id'])
    check('user_code = читатель', co and co[0]['user_code'] == 'R1')
    check('hold_ref пуст у выдачи', co and co[0]['hold_ref'] is None)

    eng.renew(loan['id'], T0 + 5 * DAY, device_id=did)
    rn = [e for e in svc.events(device_id=did) if e['event_name'] == 'loan_renew']
    check('renew -> device_event loan_renew', len(rn) == 1)
    check('renew loan_ref верный', rn and rn[0]['loan_ref'] == loan['id'])

    eng.return_item(loan['id'], T0 + 6 * DAY, device_id=did)
    rt = [e for e in svc.events(device_id=did) if e['event_name'] == 'loan_return']
    check('return -> device_event loan_return', len(rt) == 1)
    check('return loan_ref верный', rt and rt[0]['loan_ref'] == loan['id'])


def device_hold_ref_checks():
    print('-- 12.7: place_hold/cancel_hold -> device_event.hold_ref')
    store, eng, svc, did = _wired_devices()
    # книга на руках у другого читателя, чтобы бронь встала в очередь
    store.add_reader('R0', category='В01')
    eng.checkout('R0', 'BK-H', T0)

    d = eng.place_hold('R1', 'BK-H', T0 + 1 * DAY, device_id=did)
    hold = d.computed['hold']
    check('place_hold ALLOW', d.decision == ALLOW)
    ph = [e for e in svc.events(device_id=did) if e['event_name'] == 'hold_placed']
    check('place_hold -> device_event hold_placed', len(ph) == 1)
    check('hold_ref ссылается на бронь', ph and ph[0]['hold_ref'] == hold['id'])
    check('loan_ref пуст у брони', ph and ph[0]['loan_ref'] is None)
    check('user_code = читатель', ph and ph[0]['user_code'] == 'R1')

    eng.cancel_hold(hold['id'], T0 + 2 * DAY, device_id=did)
    ch = [e for e in svc.events(device_id=did) if e['event_name'] == 'hold_cancelled']
    check('cancel_hold -> device_event hold_cancelled', len(ch) == 1)
    check('cancel hold_ref верный', ch and ch[0]['hold_ref'] == hold['id'])


def device_backcompat_checks():
    print('-- back-compat: без device_id / без devices-хэндла — журнал не трогаем')
    # хэндл есть, но device_id не передан -> событие не пишется
    store, eng, svc, did = _wired_devices()
    d = eng.checkout('R1', 'BK-1', T0)            # без device_id
    check('checkout ALLOW без device_id', d.decision == ALLOW)
    check('device_event НЕ в computed без device_id',
          'device_event' not in d.computed)
    check('журнал устройства пуст', svc.events(device_id=did) == [])

    # хэндла нет вовсе -> device_id игнорируется (back-compat)
    store2 = CirculationStore(':memory:')
    eng2 = CirculationEngine(store=store2, policy=default_policy())  # devices=None
    store2.add_reader('R1', category='В01')
    d2 = eng2.checkout('R1', 'BK-2', T0, device_id=999)
    check('checkout ALLOW без devices-хэндла', d2.decision == ALLOW)
    check('device_event НЕ в computed без хэндла',
          'device_event' not in d2.computed)


def device_failure_isolation_checks():
    print('-- failure-isolation: падение domain устройств не роняет книговыдачу')

    class _Boom:
        def record_event(self, *a, **k):
            raise RuntimeError('device journal down')

    store = CirculationStore(':memory:')
    eng = CirculationEngine(store=store, policy=default_policy(), devices=_Boom())
    store.add_reader('R1', category='В01')
    d = eng.checkout('R1', 'BK-1', T0, device_id=7)
    check('checkout всё равно ALLOW при сбое устройства', d.decision == ALLOW)
    check('выдача создана несмотря на сбой', d.computed.get('loan') is not None)
    check('device_event не проставлен при сбое',
          'device_event' not in d.computed)

    # хэндл без метода record_event -> тихий no-op, не падение
    class _NoMethod:
        pass
    eng2 = CirculationEngine(store=CirculationStore(':memory:'),
                             policy=default_policy(), devices=_NoMethod())
    eng2.store.add_reader('R1', category='В01')
    d2 = eng2.checkout('R1', 'BK-1', T0, device_id=7)
    check('checkout ALLOW при хэндле без record_event', d2.decision == ALLOW)


def main():
    scan_due_emit_checks()
    scan_due_render_checks()
    scan_due_idempotent_checks()
    scan_due_window_and_filter_checks()
    scan_due_standalone_checks()
    device_loan_ref_checks()
    device_hold_ref_checks()
    device_backcompat_checks()
    device_failure_isolation_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
