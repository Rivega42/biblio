#!/usr/bin/env python3
"""Тесты ВОРКЕРА-ДИСПЕТЧА внешней доставки (ребро 11.3, движок A6, эпик #188).

Покрывают оркестратор ``access.notify_dispatch`` поверх
``NotificationQueue.dispatch``: сборку набора каналов из конфига тенанта, прогон
осевшей очереди в каналы, идемпотентность и статус каналов. РЕАЛЬНОЙ отправки нет
— внешние каналы конфигурируемы, по умолчанию OFF, InApp терминальный/всегда.

Что проверяется:
  1. Набор каналов из конфига: InApp всегда; email/sms ТОЛЬКО при enabled
     (булев и вложенная форма); по умолчанию внешние OFF.
  2. run_once доставляет: enqueue нескольких событий -> прогон -> всё sent;
     при внешних OFF доставка садится в inapp (fallback).
  3. Включённый email доставляет через email (заглушка, без реального SMTP).
  4. Идемпотентность: второй run_once по осевшей очереди -> 0 sent.
  5. channel_status корректен (inapp всегда True; внешние по конфигу).
  6. Best-effort: воркер не бросает на битом конфиге/сбое.

Запуск (дом-стиль, как test_notifications_dispatch.py):
  py -3.12 tests/test_notify_dispatch.py  -> строки 'ok ...' + 'N passed, M failed'
  и код выхода 1 при любом провале.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import notifications as nt
from access import notify_dispatch as nd

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def _q(catalog=None):
    """Свежая in-memory очередь (каждый тест изолирован)."""
    return nt.NotificationQueue(':memory:', catalog=catalog)


def _enqueue_some(q, recipient='reader-1', prefs=None):
    """Поставить несколько разнотипных событий в очередь. Возвращает список id."""
    ids = []
    ids.append(q.enqueue('hold_ready', recipient,
                         {'reader_name': 'Иван', 'title': 'Идиот',
                          'hold_until': '2026-06-30', 'pickup': 'Абонемент',
                          'ref': 'hold-1'}, prefs=prefs)['id'])
    ids.append(q.enqueue('due_soon', recipient,
                         {'title': 'Мёртвые души', 'due_date': '2026-07-01',
                          'days_left': 3, 'ref': 'loan-1'}, prefs=prefs)['id'])
    ids.append(q.enqueue('overdue', recipient,
                         {'title': 'Война и мир', 'days_overdue': 5,
                          'ref': 'loan-2'}, prefs=prefs)['id'])
    return ids


# --------------------------------------------------------------------------- #
# 1. build_channels — InApp всегда; внешние только при enabled; OFF по умолчанию.
# --------------------------------------------------------------------------- #
def build_channels_checks():
    print('-- build_channels: inapp всегда, внешние только при enabled')

    # пустой/None конфиг -> только inapp (внешние OFF по умолчанию)
    ch = nd.build_channels(None)
    check('None-конфиг: inapp присутствует', 'inapp' in ch)
    check('None-конфиг: email отсутствует (OFF)', 'email' not in ch)
    check('None-конфиг: sms отсутствует (OFF)', 'sms' not in ch)
    check('inapp — это InAppChannel', isinstance(ch['inapp'], nt.InAppChannel))

    ch2 = nd.build_channels({})
    check('пустой dict: только inapp', set(ch2) == {'inapp'})

    # вложенная форма enabled
    ch3 = nd.build_channels({'email': {'enabled': True}, 'sms': {'enabled': False}})
    check('email enabled -> в наборе', 'email' in ch3)
    check('sms disabled -> нет в наборе', 'sms' not in ch3)
    check('включённый email — это EmailChannel', isinstance(ch3['email'], nt.EmailChannel))
    check('включённый email доступен (available)', ch3['email'].available is True)

    # короткая булева форма
    ch4 = nd.build_channels({'email': True, 'sms': True})
    check('булев email=True -> в наборе', 'email' in ch4)
    check('булев sms=True -> в наборе', 'sms' in ch4)
    check('булев email=False -> нет', 'email' not in nd.build_channels({'email': False}))

    # форма под ключом channels
    ch5 = nd.build_channels({'channels': {'sms': {'enabled': True}}})
    check('channels.sms enabled -> в наборе', 'sms' in ch5)
    check('channels: email без записи остаётся OFF', 'email' not in ch5)

    # inapp нельзя выключить
    ch6 = nd.build_channels({'inapp': False})
    check('inapp нельзя выключить конфигом', 'inapp' in ch6)


# --------------------------------------------------------------------------- #
# 2. run_once доставляет; внешние OFF -> садится в inapp (fallback).
# --------------------------------------------------------------------------- #
def run_once_delivers_checks():
    print('-- run_once: доставляет; внешние OFF -> fallback на inapp')
    q = _q()
    # читатель предпочитает email, затем inapp — внешний OFF по умолчанию, поэтому
    # email отсутствует в наборе -> цепочка доезжает на inapp.
    prefs = nt.Preferences(default_channels=['email', 'inapp'])
    ids = _enqueue_some(q, 'reader-1', prefs=prefs)
    check('поставлено в очередь 3 события', q.pending_count() == 3)

    worker = nd.DispatchWorker(q)  # без конфига -> только inapp
    summary = worker.run_once()
    check('run_once: сводка несёт ключи',
          set(summary) == {'processed', 'sent', 'failed', 'retried'})
    check('run_once: доставлено ровно 3', summary['sent'] == 3)
    check('run_once: ни одного failed', summary['failed'] == 0)
    check('после прогона нет pending', q.pending_count() == 0)

    # всё село в inapp (внешний email отсутствовал в наборе)
    for nid in ids:
        row = q.get(nid)
        check('строка %d sent через inapp' % nid,
              row['status'] == 'sent' and row['channel'] == 'inapp')

    # inbox читателя показывает доставленные карточки
    inbox = q.inbox('reader-1')
    check('inbox читателя несёт 3 уведомления', len(inbox) == 3)
    check('unread_count == 3', q.unread_count('reader-1') == 3)


# --------------------------------------------------------------------------- #
# 3. Включённый email -> доставка через email (заглушка, без SMTP).
# --------------------------------------------------------------------------- #
def email_enabled_checks():
    print('-- включённый email: доставка через email-канал (заглушка)')
    q = _q()
    prefs = nt.Preferences(default_channels=['email', 'inapp'])
    ids = _enqueue_some(q, 'reader-2', prefs=prefs)

    # конфиг тенанта включает email
    worker = nd.DispatchWorker(q, channels={'email': {'enabled': True}})
    summary = worker.run_once()
    check('email enabled: доставлено 3', summary['sent'] == 3)

    # все строки доставлены через email (первый предпочтительный, теперь активен)
    via_email = sum(1 for nid in ids if q.get(nid)['channel'] == 'email')
    check('все 3 доставлены через email', via_email == 3)

    # email-заглушка записала отправки в outbox (без реального SMTP)
    email_ch = worker.channels['email']
    check('email-заглушка несёт 3 записи в outbox', len(email_ch.outbox) == 3)
    check('outbox несёт отрендеренную тему',
          any('Идиот' in m['subject'] for m in email_ch.outbox))

    # ничего не ушло в inapp (email принял первым)
    inapp_ch = worker.channels['inapp']
    check('inapp не задействован (email принял)', len(inapp_ch.delivered) == 0)


# --------------------------------------------------------------------------- #
# 4. Идемпотентность: второй run_once по осевшей очереди -> 0 sent.
# --------------------------------------------------------------------------- #
def idempotency_checks():
    print('-- идемпотентность: второй run_once -> 0 sent')
    q = _q()
    prefs = nt.Preferences(default_channels=['email', 'inapp'])
    _enqueue_some(q, 'reader-3', prefs=prefs)

    worker = nd.DispatchWorker(q, channels={'email': True})
    a1 = worker.run_once()
    check('первый run_once доставил 3', a1['sent'] == 3)

    email_ch = worker.channels['email']
    check('email outbox == 3 после первого', len(email_ch.outbox) == 3)

    # второй прогон по осевшей очереди: нет pending -> ничего нового
    a2 = worker.run_once()
    check('второй run_once: 0 processed', a2['processed'] == 0)
    check('второй run_once: 0 sent', a2['sent'] == 0)
    check('канал не задвоил доставку (outbox всё ещё 3)', len(email_ch.outbox) == 3)

    # третий — тоже no-op
    a3 = worker.run_once()
    check('третий run_once: 0 sent', a3['sent'] == 0)


# --------------------------------------------------------------------------- #
# 5. channel_status корректен.
# --------------------------------------------------------------------------- #
def channel_status_checks():
    print('-- channel_status: inapp всегда True; внешние по конфигу')
    q = _q()

    # только inapp (внешние OFF)
    w0 = nd.DispatchWorker(q)
    st0 = w0.channel_status()
    check('status: inapp True', st0['inapp'] is True)
    check('status: email False (OFF)', st0['email'] is False)
    check('status: sms False (OFF)', st0['sms'] is False)

    # email включён
    w1 = nd.DispatchWorker(q, channels={'email': {'enabled': True}})
    st1 = w1.channel_status()
    check('status: email True при enabled', st1['email'] is True)
    check('status: sms по-прежнему False', st1['sms'] is False)
    check('status: inapp True', st1['inapp'] is True)

    # оба внешних включены
    w2 = nd.DispatchWorker(q, channels={'email': True, 'sms': True})
    st2 = w2.channel_status()
    check('status: оба внешних True', st2['email'] is True and st2['sms'] is True)
    check('active_channels несёт все три',
          set(w2.active_channels()) == {'inapp', 'email', 'sms'})

    # готовый набор каналов принимается напрямую; inapp досоздаётся, если забыли
    w3 = nd.DispatchWorker(q, channels={'email': nt.MemoryChannel('email')})
    st3 = w3.channel_status()
    check('готовый набор: email активен', st3['email'] is True)
    check('готовый набор: inapp досоздан', st3['inapp'] is True)


# --------------------------------------------------------------------------- #
# 6. Best-effort: воркер не бросает на битом конфиге/сбое.
# --------------------------------------------------------------------------- #
def best_effort_checks():
    print('-- best-effort: воркер не бросает')

    # битый конфиг (не dict) -> остаётся хотя бы inapp, без исключения
    ch = nd.build_channels(['not', 'a', 'dict'])
    check('битый конфиг -> хотя бы inapp', 'inapp' in ch)

    ch2 = nd.build_channels(42)
    check('число вместо конфига -> inapp', 'inapp' in ch2)

    # run_once на пустой очереди -> чистый no-op
    q = _q()
    w = nd.DispatchWorker(q)
    s = w.run_once()
    check('пустая очередь: 0 processed', s['processed'] == 0)
    check('пустая очередь: 0 sent', s['sent'] == 0)

    # запоротая очередь (dispatch бросает) -> сводка из нулей, без краха
    class BrokenQueue:
        def dispatch(self, channels, now=None, limit=100):
            raise RuntimeError('boom')
    wb = nd.DispatchWorker(BrokenQueue())
    sb = wb.run_once()
    check('сбойный dispatch -> нулевая сводка без краха',
          sb == {'processed': 0, 'sent': 0, 'failed': 0, 'retried': 0})

    # фиксированные часы (now как число) принимаются
    q2 = _q()
    nt_prefs = nt.Preferences(default_channels=['inapp'])
    q2.enqueue('hold_ready', 'r', {'title': 'T', 'ref': 'h1'}, prefs=nt_prefs)
    wc = nd.DispatchWorker(q2, now=1000.0)
    sc = wc.run_once()
    check('фиксированные часы (число): доставлено', sc['sent'] == 1)

    # часы как callable
    q3 = _q()
    q3.enqueue('hold_ready', 'r', {'title': 'T', 'ref': 'h2'}, prefs=nt_prefs)
    wd = nd.DispatchWorker(q3, now=lambda: 2000.0)
    sd = wd.run_once()
    check('часы как callable: доставлено', sd['sent'] == 1)


def main():
    build_channels_checks()
    run_once_delivers_checks()
    email_enabled_checks()
    idempotency_checks()
    channel_status_checks()
    best_effort_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
