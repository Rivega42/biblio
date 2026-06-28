#!/usr/bin/env python3
"""Тесты JOB_QUEUE — очередь фоновых задач с приоритетами (фундамент #240).

Покрыто (in-memory + фиксированные часы для штампов; FIFO детерминирован по id):
  * enqueue/claim по приоритету — priority 5 раньше priority 1; при равном
    приоритете — FIFO (раньше созданная по автоинкрементному id);
  * claim пустой очереди -> None;
  * жизненный цикл pending -> running (claim, started_at) -> done (complete,
    finished_at + result); fail -> failed + error + finished_at;
  * stats / counts_by_status корректны по всем 4 статусам;
  * round-trip dict payload/result через JSON; пустой result -> None;
  * complete/fail неизвестного id -> None (не падает);
  * list с фильтром по статусу.

Запуск: py -3.12 tests/test_job_queue.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import job_queue

PASS = [0]
FAIL = [0]

# Детерминированные «часы» для штампов created_at/started_at/finished_at.
CLOCK = '2026-06-15T00:00:00+00:00'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def queue():
    """Свежая очередь на чистом in-memory сторе с фиксированными часами."""
    return job_queue.JobQueue(
        store=job_queue.JobStore(':memory:', now=lambda: CLOCK),
        now=lambda: CLOCK)


def enqueue_basic_checks():
    print('-- enqueue: постановка задачи в pending с payload round-trip')
    q = queue()
    job = q.enqueue('pdf', payload={'edition': 42, 'pages': [1, 2, 3]},
                    priority=0)
    check('новый статус pending', job['status'] == 'pending')
    check('kind сохранён', job['kind'] == 'pdf')
    check('payload распарсен в dict', job['payload'] == {'edition': 42,
                                                          'pages': [1, 2, 3]})
    check('created_at от часов', job['created_at'] == CLOCK)
    check('started_at пуст', job['started_at'] is None)
    check('result пуст -> None', job['result'] is None)


def priority_order_checks():
    print('-- claim: больший priority раньше')
    q = queue()
    q.enqueue('low', priority=1)
    q.enqueue('high', priority=5)
    q.enqueue('mid', priority=3)
    check('priority 5 забран первым', q.claim()['kind'] == 'high')
    check('затем priority 3', q.claim()['kind'] == 'mid')
    check('затем priority 1', q.claim()['kind'] == 'low')


def fifo_order_checks():
    print('-- claim: при равном priority — FIFO (раньше созданная)')
    q = queue()
    a = q.enqueue('first', priority=2)
    b = q.enqueue('second', priority=2)
    c = q.enqueue('third', priority=2)
    c1 = q.claim()
    c2 = q.claim()
    c3 = q.claim()
    check('FIFO: first раньше', c1['id'] == a['id'])
    check('FIFO: second вторым', c2['id'] == b['id'])
    check('FIFO: third третьим', c3['id'] == c['id'])


def empty_claim_checks():
    print('-- claim: пустая очередь -> None')
    q = queue()
    check('claim пустой -> None', q.claim() is None)
    q.enqueue('only', priority=0)
    q.claim()
    check('claim после опустошения -> None', q.claim() is None)


def lifecycle_done_checks():
    print('-- жизненный цикл: pending -> running -> done')
    q = queue()
    job = q.enqueue('ocr', payload={'doc': 'D-1'}, priority=0)
    claimed = q.claim()
    check('claim -> running', claimed['status'] == 'running')
    check('claim ставит started_at', claimed['started_at'] == CLOCK)
    check('claim не ставит finished_at', claimed['finished_at'] is None)
    done = q.complete(job['id'], result={'pages': 12, 'ok': True})
    check('complete -> done', done['status'] == 'done')
    check('complete ставит finished_at', done['finished_at'] == CLOCK)
    check('result распарсен round-trip',
          done['result'] == {'pages': 12, 'ok': True})


def lifecycle_fail_checks():
    print('-- жизненный цикл: fail -> failed + error')
    q = queue()
    job = q.enqueue('iiif', priority=0)
    q.claim()
    failed = q.fail(job['id'], error='tiler crashed')
    check('fail -> failed', failed['status'] == 'failed')
    check('fail сохраняет error', failed['error'] == 'tiler crashed')
    check('fail ставит finished_at', failed['finished_at'] == CLOCK)


def unknown_id_checks():
    print('-- устойчивость: неизвестный id не падает')
    q = queue()
    check('get неизвестного id -> None', q.get(99999) is None)
    check('complete неизвестного id -> None',
          q.complete(99999, result={'x': 1}) is None)
    check('fail неизвестного id -> None', q.fail(99999, error='nope') is None)


def stats_checks():
    print('-- stats / counts_by_status по всем 4 статусам')
    q = queue()
    j1 = q.enqueue('a', priority=0)   # останется pending
    j2 = q.enqueue('b', priority=0)   # станет done
    j3 = q.enqueue('c', priority=0)   # станет failed
    q.enqueue('d', priority=0)        # станет running
    # j2 -> done
    q.claim()  # заберёт что-то; порядок управляем явными переходами ниже
    # Явно проведём конкретные задачи по статусам (claim уже что-то взял —
    # переопределим состояния прямой адресацией по id).
    q.complete(j2['id'], result={'done': True})
    q.fail(j3['id'], error='boom')
    cbs = q.store.counts_by_status()
    check('counts включает все 4 ключа',
          set(cbs.keys()) == {'pending', 'running', 'done', 'failed'})
    check('done == 1', cbs['done'] == 1)
    check('failed == 1', cbs['failed'] == 1)
    st = q.stats()
    check('stats total == 4', st['total'] == 4)
    check('stats by_status совпадает', st['by_status'] == cbs)
    # j1 ни разу не трогали как done/failed — он либо pending, либо running.
    check('j1 не done и не failed',
          q.get(j1['id'])['status'] in ('pending', 'running'))


def list_filter_checks():
    print('-- list: фильтр по статусу, новые сверху')
    q = queue()
    q.enqueue('x1', priority=0)
    j2 = q.enqueue('x2', priority=0)
    q.claim()           # заберёт x1 (FIFO) -> running
    q.complete(j2['id'], result={'k': 'v'})
    pend = q.list(status='pending')
    check('pending список пуст', pend == [])
    done = q.list(status='done')
    check('done список длиной 1', len(done) == 1)
    check('done элемент с распарсенным result',
          done[0]['result'] == {'k': 'v'})
    allj = q.list()
    check('list без фильтра новые сверху (id DESC)',
          allj[0]['id'] > allj[-1]['id'])


def main():
    enqueue_basic_checks()
    priority_order_checks()
    fifo_order_checks()
    empty_claim_checks()
    lifecycle_done_checks()
    lifecycle_fail_checks()
    unknown_id_checks()
    stats_checks()
    list_filter_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
