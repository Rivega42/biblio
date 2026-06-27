#!/usr/bin/env python3
"""Тесты migration-тулинга J-IRBIS (Joomla jirbis2) -> Biblio own-store (узел 4).

Покрыто (на синтетике — реальный дамп off-git, ПДн, #310):
  * `classify_table` — migrate / cms / ballast (jstats/session) / other;
  * `classify_password` — phpass(`$P$`)→upgrade, pbkdf2→native, md5:salt/md5→upgrade,
    пусто→other;
  * `map_user`/`map_rating`/`map_reservation`/`map_chat` — форма own-store;
  * `plan` — сводка (accounts/needs_upgrade/ratings/…), auth_breakdown, балласт
    пропущен, CMS учтён, пустой план.

Запуск: py -3.12 tests/test_jirbis_migrate.py ; в агрегаторе test_access.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import jirbis_migrate as jm

PASS = [0]
FAIL = [0]

# Реальный phpass `$P$` (golden-вектор из tests/test_phpass.py) — Joomla 2.5 дефолт.
PHPASS = '$P$B12345678Eg2z6eqcenWjcSosVt4mZ.'
MD5 = '5f4dcc3b5aa765d61d8327deb882cf99'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


def classify_password_checks():
    print('-- classify_password: формат хэша -> стратегия входа')
    check('phpass -> (phpass, upgrade)', jm.classify_password(PHPASS) == ('phpass', True))
    check('pbkdf2 -> (native, no upgrade)',
          jm.classify_password('pbkdf2$200000$a$b') == ('native', False))
    check('md5:salt -> (md5_salt, upgrade)',
          jm.classify_password(MD5 + ':abc') == ('md5_salt', True))
    check('md5 -> (md5, upgrade)', jm.classify_password(MD5) == ('md5', True))
    check('пусто -> (other, upgrade)', jm.classify_password('') == ('other', True))
    check('None-безопасно -> other', jm.classify_password(None) == ('other', True))


def classify_table_checks():
    print('-- classify_table: migrate / cms / ballast / other')
    check('jos_users -> migrate', jm.classify_table('jos_users') == 'migrate')
    check('jos_reservations -> migrate', jm.classify_table('jos_reservations') == 'migrate')
    check('jos_jstats_visits -> ballast', jm.classify_table('jos_jstats_visits') == 'ballast')
    check('jos_session -> ballast', jm.classify_table('jos_session') == 'ballast')
    check('jos_content -> cms', jm.classify_table('jos_content') == 'cms')
    check('неизвестная -> other', jm.classify_table('jos_whatever') == 'other')


def map_user_checks():
    print('-- map_user: jos_users -> учётка own-store')
    u = jm.map_user({'id': 1, 'name': 'Иван', 'username': 'ivan',
                     'email': 'IVAN@X.ru', 'password': PHPASS, 'block': '0'})
    check('login', u['login'] == 'ivan')
    check('email нормализован (lower)', u['email'] == 'ivan@x.ru')
    check('ФИО', u['name'] == 'Иван')
    check('legacy_hash перенесён', u['legacy_hash'] == PHPASS)
    check('auth phpass', u['auth'] == 'phpass')
    check('needs_upgrade True', u['needs_upgrade'] is True)
    check('не заблокирован', u['blocked'] is False)
    ub = jm.map_user({'id': 2, 'username': 'b', 'email': 'b@x',
                      'password': 'pbkdf2$1$a$b', 'block': '1'})
    check('native -> без апгрейда', ub['auth'] == 'native' and ub['needs_upgrade'] is False)
    check('blocked True', ub['blocked'] is True)


def map_rating_checks():
    print('-- map_rating: jos_content_rating -> avg=sum/count')
    r = jm.map_rating({'content_id': 5, 'rating_sum': '18', 'rating_count': '4'})
    check('avg 4.5 / count 4', r['avg'] == 4.5 and r['count'] == 4)
    r0 = jm.map_rating({'content_id': 6, 'rating_sum': 0, 'rating_count': 0})
    check('count 0 -> avg 0', r0['avg'] == 0.0)


def map_reservation_chat_checks():
    print('-- map_reservation / map_chat')
    rv = jm.map_reservation({'id': 1, 'user_id': '111', 'item': 'BK-1', 'status': 'new'})
    check('reservation reader', rv['reader'] == '111' and rv['item'] == 'BK-1')
    ch = jm.map_chat({'user_message': 'привет', 'rating': '5', 'deepthink': '1'})
    check('chat message', ch['user_message'] == 'привет')
    check('chat deepthink bool', ch['deepthink'] is True)


def plan_checks():
    print('-- plan: строки таблиц -> план + сводка')
    tables = {
        'jos_users': [
            {'id': 1, 'username': 'a', 'email': 'a@x', 'password': PHPASS},
            {'id': 2, 'username': 'b', 'email': 'b@x', 'password': 'pbkdf2$1$a$b'},
            {'id': 3, 'username': 'c', 'email': 'c@x', 'password': ''}],
        'jos_content_rating': [{'content_id': 1, 'rating_sum': '10', 'rating_count': '2'}],
        'jos_reservations': [{'id': 1, 'user_id': '111', 'item': 'BK-1'}],
        'jos_ai_chat_feedback': [],
        'jos_jstats_visits': [{'a': 1}, {'a': 2}],
        'jos_content': [{'id': 1}],
    }
    p = jm.plan(tables)
    check('3 учётки', p['summary']['accounts'] == 3)
    check('needs_upgrade 2 (phpass + empty)', p['summary']['needs_upgrade'] == 2)
    check('auth_breakdown phpass 1', p['auth_breakdown']['phpass'] == 1)
    check('auth_breakdown native 1', p['auth_breakdown']['native'] == 1)
    check('auth_breakdown other 1', p['auth_breakdown']['other'] == 1)
    check('1 рейтинг', p['summary']['ratings'] == 1)
    check('1 бронь', p['summary']['reservations'] == 1)
    check('chat 0 строк', p['summary']['chat'] == 0)
    check('балласт jstats пропущен (2)', p['ballast_skipped'].get('jos_jstats_visits') == 2)
    check('CMS content учтён (1)', p['cms'].get('jos_content') == 1)
    check('пустой план не падает', jm.plan({})['summary']['accounts'] == 0)


def main():
    classify_password_checks()
    classify_table_checks()
    map_user_checks()
    map_rating_checks()
    map_reservation_chat_checks()
    plan_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
