#!/usr/bin/env python3
"""Vision domain tests (узел #272, нативный домен КАМЕР / FaceID).

Сценарные тесты нативного домена `vision` над in-memory стором (детерминизм, без
DB-сервера). Дом. стиль ``test_devices.py``::

    py -3.12 tests/test_vision.py   ->  ok ... + "N passed, M failed" + exit code

Покрыто:
  * enroll -> identify: hit (токен в реестре) / miss (нет);
  * enroll идемпотентен: повторный enroll того же токена обновляет, 1 строка;
  * record_event: matched vs unmatched, авто-резолв ticket из реестра;
  * events: фильтр по device_id / ticket;
  * forget: удаляет subject + обезличивает события (ticket -> NULL);
  * пустые аргументы -> VisionError;
  * приватность: в схеме НЕТ колонок изображений/шаблонов — только токен.

Реальных ПДн нет — только синтетические токены/билеты.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access.vision import (
    VisionStore, VisionService, VisionError, SCHEMA_SQLITE,
)

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def expect_raises(name, fn, exc=VisionError):
    try:
        fn()
        check(name, False)
    except exc:
        check(name, True)
    except Exception:
        check(name, False)


def make_service(now_ref):
    return VisionService(VisionStore(':memory:'), now=lambda: now_ref[0])


def test_enroll_identify():
    now = [1000.0]
    svc = make_service(now)
    s = svc.enroll('R-001', 'tok-aaa', label='cam-1')
    check('enroll returns subject', s and s['ticket'] == 'R-001'
          and s['face_token'] == 'tok-aaa')
    check('enroll stores label', s['label'] == 'cam-1')
    hit = svc.identify('tok-aaa')
    check('identify hit ticket', hit['ticket'] == 'R-001')
    check('identify hit matched', hit['matched'] is True)
    miss = svc.identify('tok-unknown')
    check('identify miss ticket None', miss['ticket'] is None)
    check('identify miss matched False', miss['matched'] is False)
    # score-порог не влияет на точное совпадение токена
    check('identify hit ignores min_score',
          svc.identify('tok-aaa', min_score=0.99)['matched'] is True)


def test_enroll_idempotent():
    now = [10.0]
    svc = make_service(now)
    svc.enroll('R-001', 'tok-aaa', label='cam-1')
    now[0] = 20.0
    s2 = svc.enroll('R-002', 'tok-aaa', label='cam-2')  # тот же токен -> другой билет
    check('re-enroll updates ticket', s2['ticket'] == 'R-002')
    check('re-enroll updates label', s2['label'] == 'cam-2')
    check('re-enroll touches updated', s2['updated'] == 20.0)
    check('re-enroll keeps created', s2['created'] == 10.0)
    check('re-enroll no dup row (1 subject)', len(svc.subjects()) == 1)
    # теперь identify резолвит в новый билет
    check('identify after re-enroll -> new ticket',
          svc.identify('tok-aaa')['ticket'] == 'R-002')


def test_record_event():
    now = [100.0]
    svc = make_service(now)
    svc.enroll('R-100', 'tok-known')
    # matched + авто-резолв ticket из реестра (ticket не передан)
    svc.record_event(device_id=7, face_token='tok-known', score=0.93)
    ev = svc.events(device_id=7)
    check('event recorded', len(ev) == 1)
    check('event matched=1', ev[0]['matched'] == 1)
    check('event auto-resolved ticket', ev[0]['ticket'] == 'R-100')
    check('event keeps score', ev[0]['score'] == 0.93)
    check('event stores only token (no image col)', 'face_token' in ev[0]
          and ev[0]['face_token'] == 'tok-known')
    # unmatched: токен не в реестре
    svc.record_event(device_id=7, face_token='tok-stranger', score=0.40)
    ev2 = svc.events(device_id=7)
    unmatched = [e for e in ev2 if e['face_token'] == 'tok-stranger'][0]
    check('unmatched event matched=0', unmatched['matched'] == 0)
    check('unmatched event ticket None', unmatched['ticket'] is None)


def test_events_filter():
    now = [5.0]
    svc = make_service(now)
    svc.enroll('R-A', 'tok-a')
    svc.enroll('R-B', 'tok-b')
    svc.record_event(device_id=1, face_token='tok-a')
    svc.record_event(device_id=2, face_token='tok-b')
    svc.record_event(device_id=1, face_token='tok-b')
    check('filter by device_id=1', len(svc.events(device_id=1)) == 2)
    check('filter by device_id=2', len(svc.events(device_id=2)) == 1)
    check('filter by ticket R-B', len(svc.events(ticket='R-B')) == 2)
    check('no filter -> all', len(svc.events()) == 3)
    check('limit honored', len(svc.events(limit=1)) == 1)


def test_forget():
    now = [50.0]
    svc = make_service(now)
    svc.enroll('R-X', 'tok-x1', label='a')
    svc.enroll('R-X', 'tok-x2', label='b')  # 2 токена одного читателя
    svc.enroll('R-Y', 'tok-y1')
    svc.record_event(device_id=3, face_token='tok-x1')
    svc.record_event(device_id=3, face_token='tok-y1')
    affected = svc.forget('R-X')
    # 2 subject удалены + 1 событие обезличено = 3
    check('forget returns affected count', affected == 3)
    check('forget removes subjects', len(svc.subjects(ticket='R-X')) == 0)
    check('forget keeps other reader', len(svc.subjects(ticket='R-Y')) == 1)
    check('forget identify now miss', svc.identify('tok-x1')['matched'] is False)
    # событие осталось (статистика камеры), но обезличено
    check('forget anonymizes events (ticket None)',
          len(svc.events(ticket='R-X')) == 0)
    x_ev = [e for e in svc.events(device_id=3) if e['face_token'] == 'tok-x1']
    check('forgotten event still exists, ticket NULL',
          len(x_ev) == 1 and x_ev[0]['ticket'] is None)
    check('forget unknown ticket -> 0', svc.forget('R-NONE') == 0)


def test_validation_errors():
    now = [1.0]
    svc = make_service(now)
    expect_raises('enroll empty ticket raises', lambda: svc.enroll('', 'tok'))
    expect_raises('enroll empty token raises', lambda: svc.enroll('R-1', ''))
    expect_raises('enroll None ticket raises', lambda: svc.enroll(None, 'tok'))
    expect_raises('identify empty token raises', lambda: svc.identify(''))
    expect_raises('forget empty ticket raises', lambda: svc.forget(''))


def test_privacy_posture():
    # Жёсткое правило: только токен, никаких изображений/шаблонов в схеме.
    schema = SCHEMA_SQLITE.lower()
    forbidden = ('image', 'photo', 'template', 'embedding', 'descriptor',
                 'blob', 'bytea', 'frame', 'snapshot', 'biometric')
    for word in forbidden:
        check('schema has no %r column' % word, word not in schema)
    check('schema stores face_token', 'face_token' in schema)
    # столбцы реестра — ровно реестровая модель, без сырой биометрии
    svc = VisionService(VisionStore(':memory:'))
    svc.enroll('R-1', 'tok-1')
    cols = set(svc.subjects()[0].keys())
    check('subject cols are token-only',
          cols == {'id', 'ticket', 'face_token', 'label', 'created', 'updated'})


def main():
    for t in (test_enroll_identify, test_enroll_idempotent, test_record_event,
              test_events_filter, test_forget, test_validation_errors,
              test_privacy_posture):
        print('==', t.__name__)
        t()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
