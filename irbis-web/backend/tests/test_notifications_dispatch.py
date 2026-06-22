#!/usr/bin/env python3
"""Тесты ДИСПЕТЧА очереди уведомлений (ребро 11.3, движок A6, эпик #188).

Покрывают слой *доставки*: то, что превращает поставленные в очередь (`enqueue`)
уведомления в фактическую доставку по каналам, с журналом, состояниями и
идемпотентностью. Поведение `enqueue`/шаблонов/`_emit` тестируется отдельно в
test_notifications.py / test_circ_notify.py — здесь именно ДИСПЕТЧ
(`NotificationQueue.dispatch` поверх `process_once`).

Что проверяется:
  1. enqueue → dispatch → sent: поставленное в очередь уведомление доставляется,
     строка помечается `sent`, доставивший канал зафиксирован, журнал доставки
     (`delivery_attempt`) содержит запись `sent` по этому каналу.
  2. In-app inbox + журнал доставки: in-app — терминальный канал; доставленное
     уведомление видно в inbox читателя/сотрудника, журнал несёт попытки по каналам.
  3. Падение канала → failed + retry с лимитом: транзиентный сбой ретраится
     с backoff и доезжает; вечно падающий канал без fallback доходит до `failed`
     ровно за MAX_ATTEMPTS попыток (лимит ретраев соблюдён).
  4. Идемпотентность диспетча: повторный dispatch по доставленной очереди не
     задваивает доставку (ни в каналах, ни в журнале); канал-уровневая
     идемпотентность не шлёт второй раз по уже принявшему каналу.
  5. Контракт канала: Channel.deliver(notification) -> DeliveryResult; падение
     возвращает fail-результат (а не исключение); базовый адаптер прозрачно
     поднимает legacy send()-каналы в новый контракт.
  6. Пустая очередь → no-op: dispatch по пустой/уже осевшей очереди ничего не шлёт.

Запуск в доме-стиле (как test_notifications.py):
  py -3.12 tests/test_notifications_dispatch.py  -> строки 'ok ...' + 'N passed, M failed'
  и код выхода 1 при любом провале (CI падает громко).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import notifications as nt

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


# --------------------------------------------------------------------------- #
# 1. enqueue → dispatch → sent (+ журнал доставки).
# --------------------------------------------------------------------------- #
def dispatch_happy_checks():
    print('-- диспетч: enqueue -> dispatch -> sent')
    q = _q()
    email = nt.MemoryChannel('email')
    sms = nt.MemoryChannel('sms')

    res = q.enqueue('hold_ready', 'reader-42',
                    {'reader_name': 'Иван', 'title': 'Идиот',
                     'hold_until': '2026-06-30', 'pickup': 'Абонемент',
                     'ref': 'hold-100'})
    check('поставлено в очередь как pending', res['status'] == 'pending')

    agg = q.dispatch({'email': email, 'sms': sms})
    check('dispatch вернул агрегат с passes', 'passes' in agg and agg['passes'] >= 1)
    check('dispatch доставил ровно одно', agg['sent'] == 1)
    check('доставлено по email (первый предпочтительный)', len(email.sent) == 1)
    check('sms не задействован (email принял)', len(sms.sent) == 0)

    row = q.get(res['id'])
    check('строка помечена sent', row['status'] == 'sent')
    check('доставивший канал зафиксирован', row['channel'] == 'email')

    # журнал доставки несёт одну запись 'sent' по email
    log = q.delivery_log(res['id'])
    check('журнал доставки: одна запись', len(log) == 1)
    check('журнал: канал email, статус sent',
          log[0]['channel'] == 'email' and log[0]['status'] == 'sent')
    check('журнал: provider_id зафиксирован', bool(log[0]['provider_id']))

    # рендер дошёл до канала (тело/тема несут подставленные слоты)
    check('тело отрендерено для канала', 'Идиот' in email.sent[0]['body'])


# --------------------------------------------------------------------------- #
# 2. In-app inbox — терминальный канал + журнал доставки попыток.
# --------------------------------------------------------------------------- #
def inapp_inbox_checks():
    print('-- in-app inbox (терминальный канал) + журнал попыток')
    q = _q()
    # email недоступен -> fallback на in-app (терминальный, всегда принимает)
    email = nt.EmailChannel(available=False)
    inapp = nt.InAppChannel()

    # читатель предпочитает email -> in-app как fallback
    prefs = nt.Preferences(channels={'hold_ready': ['email', 'inapp']})
    res = q.enqueue('hold_ready', 'reader-7',
                    {'reader_name': 'Пётр', 'title': 'Мёртвые души',
                     'hold_until': '2026-07-01', 'pickup': 'Зал', 'ref': 'h-7'},
                    prefs=prefs)

    agg = q.dispatch({'email': email, 'inapp': inapp})
    check('доставлено через in-app fallback', agg['sent'] == 1)
    check('in-app принял уведомление', len(inapp.delivered) == 1)
    check('email-заглушка ничего не отправила', len(email.outbox) == 0)

    row = q.get(res['id'])
    check('строка sent через inapp', row['status'] == 'sent' and row['channel'] == 'inapp')

    # журнал несёт ОБЕ попытки: email failed, затем inapp sent
    log = q.delivery_log(res['id'])
    by_ch = {a['channel']: a for a in log}
    check('журнал содержит попытку email=failed',
          'email' in by_ch and by_ch['email']['status'] == 'failed')
    check('журнал содержит попытку inapp=sent',
          'inapp' in by_ch and by_ch['inapp']['status'] == 'sent')
    check('email failed несёт текст ошибки', bool(by_ch['email']['error']))

    # доставленное in-app уведомление видно в inbox читателя
    inbox = q.inbox('reader-7')
    check('inbox читателя показывает доставленное уведомление', len(inbox) == 1)
    check('карточка inbox несёт отрендеренную тему',
          'Мёртвые души' in inbox[0]['subject'])
    check('уведомление непрочитано в inbox', inbox[0]['read'] is False)
    check('unread_count == 1', q.unread_count('reader-7') == 1)

    # сотруднический inbox (staff_alert -> staff recipient), in-app терминальный
    q2 = _q()
    inapp2 = nt.InAppChannel()
    sprefs = nt.Preferences(channels={'staff_alert': ['inapp']})
    q2.enqueue('staff_alert', 'staff-desk',
               {'reader_name': 'Сидоров', 'title': 'Том 3', 'ref': 's-1'},
               prefs=sprefs)
    q2.dispatch({'inapp': inapp2})
    sinbox = q2.inbox('staff-desk')
    check('сотруднический inbox показывает служебное уведомление', len(sinbox) == 1)
    check('служебная карточка читается как staff',
          'Служебное' in sinbox[0]['subject'])


# --------------------------------------------------------------------------- #
# 3. Падение канала -> failed + retry (с лимитом).
# --------------------------------------------------------------------------- #
def retry_limit_checks():
    print('-- падение канала: retry с лимитом, затем failed')
    # транзиентный сбой: падает дважды, нет fallback -> ретраи в рамках dispatch,
    # затем доезжает (диспетч сам прокручивает часы по backoff).
    q = _q()
    flaky = nt.MemoryChannel('email', fail_times=2)
    res = q.enqueue('hold_ready', 'reader-1', {'title': 'R', 'ref': 'h1'})

    agg = q.dispatch({'email': flaky})
    row = q.get(res['id'])
    check('транзиентный канал в итоге доставил', row['status'] == 'sent')
    check('диспетч отчитался об одной доставке', agg['sent'] == 1)
    check('были ретраи перед доставкой', agg['retried'] >= 1)
    check('всего попыток канала == 3 (2 промаха + 1 успех)', flaky.attempts == 3)
    # журнал: одна строка на канал, tries отражает счёт попыток
    log = q.delivery_log(res['id'])
    check('журнал: одна строка email (без задвоения канала)', len(log) == 1)
    check('журнал: tries отражает повторные попытки', log[0]['tries'] >= 2)
    check('журнал: финальный статус sent', log[0]['status'] == 'sent')

    # вечно падающий канал без fallback -> failed РОВНО за MAX_ATTEMPTS попыток
    q2 = _q()
    dead = nt.MemoryChannel('email', fail=True)
    r2 = q2.enqueue('hold_ready', 'reader-2', {'title': 'D', 'ref': 'h2'})
    agg2 = q2.dispatch({'email': dead})
    final = q2.get(r2['id'])
    check('исчерпанный канал помечен failed', final['status'] == 'failed')
    check('лимит ретраев соблюдён: attempts == MAX_ATTEMPTS',
          final['attempts'] == nt.MAX_ATTEMPTS)
    check('канал бит ровно MAX_ATTEMPTS раз', dead.attempts == nt.MAX_ATTEMPTS)
    check('диспетч отчитался об одном failed', agg2['failed'] == 1)
    flog = q2.delivery_log(r2['id'])
    check('журнал failed: одна строка email со статусом failed',
          len(flog) == 1 and flog[0]['status'] == 'failed')
    check('журнал failed: tries == MAX_ATTEMPTS',
          flog[0]['tries'] == nt.MAX_ATTEMPTS)


# --------------------------------------------------------------------------- #
# 4. Идемпотентность диспетча — двойной dispatch не задваивает.
# --------------------------------------------------------------------------- #
def idempotency_checks():
    print('-- идемпотентность диспетча (двойной dispatch не задваивает)')
    q = _q()
    email = nt.MemoryChannel('email')
    res = q.enqueue('hold_ready', 'reader-3', {'title': 'X', 'ref': 'h3'})

    a1 = q.dispatch({'email': email})
    check('первый dispatch доставил', a1['sent'] == 1 and len(email.sent) == 1)

    # второй dispatch по уже осевшей очереди: нет pending -> ничего не шлёт
    a2 = q.dispatch({'email': email})
    check('второй dispatch: 0 processed (нет pending)', a2['processed'] == 0)
    check('второй dispatch: 0 sent', a2['sent'] == 0)
    check('канал не задваивает доставку', len(email.sent) == 1)
    log = q.delivery_log(res['id'])
    check('журнал не задвоился (одна строка)', len(log) == 1)

    # канал-уровневая идемпотентность: даже если бы строку снова сделали pending,
    # уже принявший канал не шлёт второй раз. Симулируем: вручную вернём pending
    # и прогоним dispatch — канал-журнал 'sent' блокирует повторную отправку.
    c = q._conn()
    c.execute("UPDATE notification SET status='pending', next_attempt_at=0 WHERE id=?",
              (res['id'],))
    c.commit()
    a3 = q.dispatch({'email': email})
    check('повторный pending: канал-журнал блокирует второй send',
          len(email.sent) == 1)
    row = q.get(res['id'])
    check('строка снова sent (за счёт журнала, без новой отправки)',
          row['status'] == 'sent')
    check('журнал по-прежнему одна строка', len(q.delivery_log(res['id'])) == 1)

    # дедуп на уровне события + идемпотентность диспетча вместе: повторный enqueue
    # + dispatch не порождает второй доставки
    b = q.enqueue('hold_ready', 'reader-3', {'title': 'X', 'ref': 'h3'})
    check('повторный enqueue дедуплицирован', b['deduped'] is True)
    q.dispatch({'email': email})
    check('дедуп+идемпотентность: всё ещё одна доставка', len(email.sent) == 1)


# --------------------------------------------------------------------------- #
# 5. Контракт канала: deliver(notification) -> DeliveryResult.
# --------------------------------------------------------------------------- #
def channel_contract_checks():
    print('-- контракт канала: deliver(notification) -> DeliveryResult')
    notice = nt.Notification(id=1, event='hold_ready', recipient='r1',
                             subject='Тема', body='Тело', payload={'ref': 'x'})

    # успешная доставка -> ok-результат с provider_id
    ok = nt.MemoryChannel('email')
    res_ok = ok.deliver(notice)
    check('deliver возвращает DeliveryResult', isinstance(res_ok, nt.DeliveryResult))
    check('успех -> ok=True', res_ok.ok is True)
    check('успех несёт provider_id', bool(res_ok.provider_id))
    check('legacy send() вызван адаптером', len(ok.sent) == 1)

    # падение канала -> fail-РЕЗУЛЬТАТ, а не исключение (диспетч-контракт)
    bad = nt.MemoryChannel('email', fail=True)
    res_bad = bad.deliver(notice)
    check('падение -> ok=False (без исключения)', res_bad.ok is False)
    check('fail несёт текст ошибки', bool(res_bad.error))

    # любое неожиданное исключение в канале тоже превращается в fail-результат
    class Broken(nt.Channel):
        name = 'broken'

        def send(self, recipient, subject, body, payload):
            raise RuntimeError('boom')
    res_broken = Broken().deliver(notice)
    check('баг канала (RuntimeError) -> fail-результат, не крах',
          res_broken.ok is False and 'boom' in (res_broken.error or ''))

    # фабрики результата
    check('DeliveryResult.sent() -> ok', nt.DeliveryResult.sent('p1').ok is True)
    check('DeliveryResult.fail() -> not ok', nt.DeliveryResult.fail('e').ok is False)

    # in-app переопределяет deliver напрямую (получает весь notification)
    inapp = nt.InAppChannel()
    r = inapp.deliver(notice)
    check('in-app deliver -> ok', r.ok is True)
    check('in-app получил весь notification (event/recipient)',
          inapp.delivered[0]['event'] == 'hold_ready'
          and inapp.delivered[0]['recipient'] == 'r1')


# --------------------------------------------------------------------------- #
# 6. Пустая очередь -> no-op.
# --------------------------------------------------------------------------- #
def empty_queue_checks():
    print('-- пустая очередь -> no-op')
    q = _q()
    email = nt.MemoryChannel('email')
    agg = q.dispatch({'email': email})
    check('пустая очередь: 0 passes-итераций с работой (processed==0)',
          agg['processed'] == 0)
    check('пустая очередь: ничего не отправлено', agg['sent'] == 0 and len(email.sent) == 0)
    check('пустая очередь: ни одного failed', agg['failed'] == 0)

    # очередь только из suppressed (opt-out) -> диспетч их не доставляет
    q2 = _q()
    prefs = nt.Preferences(opted_out={'*'})
    q2.enqueue('hold_ready', 'r', {'title': 'T', 'ref': 'h1'}, prefs=prefs)
    agg2 = q2.dispatch({'email': email})
    check('suppressed не доставляется диспетчем', agg2['sent'] == 0)
    check('suppressed: канал не задействован', len(email.sent) == 0)


def main():
    dispatch_happy_checks()
    inapp_inbox_checks()
    retry_limit_checks()
    idempotency_checks()
    channel_contract_checks()
    empty_queue_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
