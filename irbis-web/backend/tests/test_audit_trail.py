#!/usr/bin/env python3
"""Тесты AUDIT TRAIL (богатый журнал аудита АРМ «Администратор», own-store).

Покрыто (на :memory: + ФЕЙКОВЫЕ возрастающие метки времени — детерминизм):
  * `record` -> распарсенные dict-записи; кириллица сохранена (ensure_ascii=False);
  * фильтры `entries` (actor/action/object/status/since/until) сужают по AND;
  * `limit` ограничивает; `count` совпадает с числом; новые сверху;
  * `get(missing)` -> None;
  * `diff`: создание (всё added) / правка (changed) / удаление (всё removed) /
    смешанный (added+changed+removed);
  * `summary`: tally по by_action / by_actor / by_status, фильтр tenant/since;
  * `actor_history`: только актор, новые сверху.

Запуск: py -3.12 tests/test_audit_trail.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import audit_trail

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


class FakeClock:
    """Возрастающие ISO-подобные метки: каждый вызов -> следующая строка.
    Лексикографический порядок == хронологический (нужно для since/until и
    'новые сверху')."""

    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return '2026-01-01T00:00:%02d' % self.n


def new_service():
    """Свежий сервис на :memory: с фейковыми часами."""
    return audit_trail.AuditService(now=FakeClock())


def record_checks():
    print('-- record: вставка -> распарсенный dict, кириллица сохранена')
    svc = new_service()
    e = svc.record('Иванов', 'update', 'reader', 'R-1',
                   before={'имя': 'Аня', 'долг': 0},
                   after={'имя': 'Анна', 'долг': 0},
                   note='правка ФИО')
    check('record вернул dict', isinstance(e, dict))
    check('actor сохранён', e['actor'] == 'Иванов')
    check('action сохранён', e['action'] == 'update')
    check('object_type/id', e['object_type'] == 'reader' and e['object_id'] == 'R-1')
    check('status дефолт ok', e['status'] == 'ok')
    check('tenant дефолт default', e['tenant'] == 'default')
    check('db дефолт *', e['db'] == '*')
    check('before -> dict (распарсен)', e['before'] == {'имя': 'Аня', 'долг': 0})
    check('after -> dict (распарсен)', e['after'] == {'имя': 'Анна', 'долг': 0})
    check('кириллица в note сохранена', e['note'] == 'правка ФИО')
    check('кириллица в after сохранена', e['after']['имя'] == 'Анна')
    check('ts проставлен фейк-часами', e['ts'] == '2026-01-01T00:00:01')
    check('get(id) == запись', svc.get(e['id'])['actor'] == 'Иванов')
    check('get(missing) -> None', svc.get(999999) is None)
    nb = svc.record('a', 'login', 'session', None)
    check('before/after None допустимы', nb['before'] is None and nb['after'] is None)
    check('object_id None допустим', nb['object_id'] is None)


def query_checks():
    print('-- entries: фильтры (AND) / limit / count / порядок')
    svc = new_service()
    svc.record('alice', 'create', 'reader', 'R-1', status='ok', tenant='t1')
    svc.record('bob', 'update', 'reader', 'R-1', status='denied', tenant='t1')
    svc.record('alice', 'delete', 'record', 'B-9', status='ok', tenant='t2')
    svc.record('alice', 'update', 'reader', 'R-2', status='error', tenant='t1')

    check('все 4 записи', len(svc.entries()) == 4)
    check('новые сверху (ts DESC)',
          [r['object_id'] for r in svc.entries()] == ['R-2', 'B-9', 'R-1', 'R-1'])
    check('фильтр actor=alice -> 3', len(svc.entries(actor='alice')) == 3)
    check('фильтр action=update -> 2', len(svc.entries(action='update')) == 2)
    check('фильтр object_type=reader -> 3',
          len(svc.entries(object_type='reader')) == 3)
    check('фильтр object_id=R-1 -> 2', len(svc.entries(object_id='R-1')) == 2)
    check('фильтр status=denied -> 1', len(svc.entries(status='denied')) == 1)
    check('фильтр tenant=t1 -> 3', len(svc.entries(tenant='t1')) == 3)
    check('AND actor=alice & action=update -> 1',
          len(svc.entries(actor='alice', action='update')) == 1)
    check('AND object_type=reader & status=ok -> 1',
          len(svc.entries(object_type='reader', status='ok')) == 1)
    # since/until по ts (записи 1..4 -> :01..:04)
    check('since отсекает старые',
          [r['object_id'] for r in svc.entries(since='2026-01-01T00:00:03')]
          == ['R-2', 'B-9'])
    check('until отсекает новые',
          [r['object_id'] for r in svc.entries(until='2026-01-01T00:00:02')]
          == ['R-1', 'R-1'])
    check('since+until окно -> 1',
          len(svc.entries(since='2026-01-01T00:00:02',
                          until='2026-01-01T00:00:02')) == 1)
    check('limit ограничивает', len(svc.entries(limit=2)) == 2)
    check('limit сохраняет порядок (новые)',
          [r['object_id'] for r in svc.entries(limit=2)] == ['R-2', 'B-9'])
    check('count() == 4', svc.count() == 4)
    check('count(actor=alice) == 3', svc.count(actor='alice') == 3)
    check('count совпадает с len(entries) при фильтре',
          svc.count(status='ok') == len(svc.entries(status='ok')))


def diff_checks():
    print('-- diff: create(added) / update(changed) / delete(removed) / mixed')
    svc = new_service()
    # Создание: before=None -> всё added.
    e_create = svc.record('a', 'create', 'reader', 'R-1', before=None,
                          after={'имя': 'Аня', 'долг': 0})
    d = svc.diff(e_create['id'])
    check('create: added == after', d['added'] == {'имя': 'Аня', 'долг': 0})
    check('create: changed пуст', d['changed'] == {})
    check('create: removed пуст', d['removed'] == {})

    # Правка: before/after отличаются одним полем.
    e_upd = svc.record('a', 'update', 'reader', 'R-1',
                       before={'имя': 'Аня', 'долг': 0},
                       after={'имя': 'Анна', 'долг': 0})
    d = svc.diff(e_upd['id'])
    check('update: changed имя from/to',
          d['changed'] == {'имя': {'from': 'Аня', 'to': 'Анна'}})
    check('update: added пуст', d['added'] == {})
    check('update: removed пуст (равные поля не в removed)', d['removed'] == {})

    # Удаление: after=None -> всё removed.
    e_del = svc.record('a', 'delete', 'reader', 'R-1',
                       before={'имя': 'Анна', 'долг': 5}, after=None)
    d = svc.diff(e_del['id'])
    check('delete: removed == before',
          d['removed'] == {'имя': 'Анна', 'долг': 5})
    check('delete: added/changed пусты',
          d['added'] == {} and d['changed'] == {})

    # Смешанный: одно изменено, одно добавлено, одно убрано.
    e_mix = svc.record('a', 'update', 'reader', 'R-1',
                       before={'a': 1, 'b': 2},
                       after={'a': 9, 'c': 3})
    d = svc.diff(e_mix['id'])
    check('mixed: changed a 1->9',
          d['changed'] == {'a': {'from': 1, 'to': 9}})
    check('mixed: added c', d['added'] == {'c': 3})
    check('mixed: removed b', d['removed'] == {'b': 2})

    check('diff(missing) -> пустой',
          svc.diff(999999) == {'changed': {}, 'added': {}, 'removed': {}})


def summary_checks():
    print('-- summary: tally by_action / by_actor / by_status + фильтры')
    svc = new_service()
    svc.record('alice', 'create', 'reader', 'R-1', status='ok', tenant='t1')
    svc.record('alice', 'update', 'reader', 'R-1', status='denied', tenant='t1')
    svc.record('bob', 'update', 'record', 'B-1', status='ok', tenant='t1')
    svc.record('bob', 'delete', 'record', 'B-2', status='ok', tenant='t2')

    s = svc.summary()
    check('summary total 4', s['total'] == 4)
    check('by_action update 2', s['by_action']['update'] == 2)
    check('by_action create 1', s['by_action']['create'] == 1)
    check('by_actor alice 2', s['by_actor']['alice'] == 2)
    check('by_actor bob 2', s['by_actor']['bob'] == 2)
    check('by_status ok 3', s['by_status']['ok'] == 3)
    check('by_status denied 1', s['by_status']['denied'] == 1)

    s1 = svc.summary(tenant='t1')
    check('summary tenant=t1 total 3', s1['total'] == 3)
    check('summary tenant=t1 не видит t2', 'delete' not in s1['by_action'])

    # since: записи 1..4 -> :01..:04; since=:03 оставляет 2 последние.
    s_since = svc.summary(since='2026-01-01T00:00:03')
    check('summary since -> total 2', s_since['total'] == 2)


def actor_history_checks():
    print('-- actor_history: только актор, новые сверху, limit')
    svc = new_service()
    svc.record('alice', 'create', 'reader', 'R-1')
    svc.record('bob', 'create', 'reader', 'R-2')
    svc.record('alice', 'update', 'reader', 'R-1')
    svc.record('alice', 'delete', 'reader', 'R-1')

    h = svc.actor_history('alice')
    check('actor_history только alice (3)', len(h) == 3)
    check('actor_history все actor==alice',
          all(r['actor'] == 'alice' for r in h))
    check('actor_history новые сверху',
          [r['action'] for r in h] == ['delete', 'update', 'create'])
    check('actor_history limit ограничивает',
          len(svc.actor_history('alice', limit=2)) == 2)
    check('actor_history неизвестного -> []',
          svc.actor_history('nobody') == [])


def edgecase_checks():
    print('-- edgecase: status/error, store-level record, схема')
    store = audit_trail.AuditStore(':memory:')
    # Прямой record на сторе с явным ts.
    e = store.record('sys', 'error', 'job', 'J-1', status='error',
                     ts='2026-01-01T00:00:09', note='сбой')
    check('store.record вернул dict', e['actor'] == 'sys')
    check('store.record статус error', e['status'] == 'error')
    check('store.record явный ts', e['ts'] == '2026-01-01T00:00:09')
    check('store.get(missing) -> None', store.get(123456) is None)
    check('store.count() == 1', store.count() == 1)
    check('SCHEMA_SQLITE содержит audit_entry',
          'audit_entry' in audit_trail.SCHEMA_SQLITE)
    check('константы статусов', audit_trail.STATUSES ==
          ('ok', 'denied', 'error'))
    # JSON стабилен (sort_keys) — сериализация не падает на кириллице.
    e2 = store.record('опер', 'update', 'reader', 'R-1',
                      before={'я': 1, 'а': 2}, after={'а': 2, 'я': 1})
    check('равные before/after -> пустой дифф',
          audit_trail.AuditService(store=store).diff(e2['id'])
          == {'changed': {}, 'added': {}, 'removed': {}})


def main():
    record_checks()
    query_checks()
    diff_checks()
    summary_checks()
    actor_history_checks()
    edgecase_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
