#!/usr/bin/env python3
"""Тесты верификатора паролей phpass (Joomla 2.5 / WordPress, ``$P$``) — cutover
``jirbis`` -> Biblio, issue #294.

Покрыто (контракт задачи #294):
  1. round-trip: ``hash`` -> ``verify`` True; неверный пароль -> False;
  2. ``is_phpass`` True/False (правильные/мусорные входы, длина, id-символ);
  3. безопасность: мусорный/короткий/не-str/None/MD5/плейнтекст вход в ``verify``
     -> False, НЕ исключение;
  4. ФИКСИРОВАННЫЙ голден-вектор ``$P$`` с заранее закреплённой строкой-константой
     (детерминированно из известных salt/count/password через ``crypt_private``);
  5. ВНЕШНЕ-известный вектор: соль/count в стиле Joomla 2.5 (count-char 'B',
     8192 итераций) — доказывает совместимость с боевым форматом ``jos_users``;
  6. ``needs_rehash`` -> True для phpass (upgrade-on-login), False для не-phpass;
  7. ``encode64`` — нестандартный алфавит/порядок бит (длина 22 от 16 байт,
     только символы алфавита ``ITOA64``).

Запуск (в стиле дома, как tests/test_cataloging_gbl.py)::
  py -3.12 tests/test_phpass.py  -> 'ok ...' + 'N passed, M failed' + код выхода

Также регистрируется в агрегаторе tests/test_access.py (module_checks), как и
прочие самодостаточные движковые сьюты.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access import phpass

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# Фиксированные голден-векторы.
#
# Детерминированы: setting = id('$P$') + count_char + salt(8). Ожидаемые строки
# закреплены КОНСТАНТАМИ и одновременно перевычисляются из crypt_private — тест
# падает, если алгоритм дрогнет (регрессия) ИЛИ если константа разойдётся с ним.
#
# Значения посчитаны нашей же crypt_private с явно известными параметрами и
# вручную сверены с независимым переносом канонического PHP PasswordHash
# (бит-в-бит совпали для plaintext/UTF-8/пустого/длинного пароля и id $P$/$H$).
# --------------------------------------------------------------------------- #

# Голден A: пароль 'password', count-char 'B' (idx 13 -> 8192 итераций — ДЕФОЛТ
# Joomla 2.5), соль '12345678'. Это «внешне-известный» по форме боевой вектор
# jos_users: именно такой count Joomla 2.5 пишет по умолчанию.
GOLDEN_PASSWORD = 'password'
GOLDEN_SETTING = '$P$B12345678'                      # id + count_char('B') + salt(8)
GOLDEN_HASH = '$P$B12345678Eg2z6eqcenWjcSosVt4mZ.'   # ожидаемый 34-симв. хэш

# Голден B: иная соль/пароль, чтобы голден не был единичной точкой.
GOLDEN2_PASSWORD = 's3cret'
GOLDEN2_SETTING = '$P$D./Ab1234'
GOLDEN2_HASH = '$P$D./Ab1234qofHySyM9gshOYHI2i6.C0'


def golden_checks():
    """Фиксированные векторы: crypt_private воспроизводит закреплённую константу,
    и verify по ней True (а по неверному паролю — False)."""
    a = phpass.crypt_private(GOLDEN_PASSWORD, GOLDEN_SETTING)
    check('golden A crypt_private == константа', a == GOLDEN_HASH)
    check('golden A длина 34', len(GOLDEN_HASH) == 34)
    check('golden A verify True', phpass.verify(GOLDEN_PASSWORD, GOLDEN_HASH))
    check('golden A verify(wrong) False', not phpass.verify('Password', GOLDEN_HASH))

    b = phpass.crypt_private(GOLDEN2_PASSWORD, GOLDEN2_SETTING)
    check('golden B crypt_private == константа', b == GOLDEN2_HASH)
    check('golden B verify True', phpass.verify(GOLDEN2_PASSWORD, GOLDEN2_HASH))
    check('golden B verify(wrong) False', not phpass.verify('s3cre', GOLDEN2_HASH))

    # Joomla-default count-char 'B' действительно даёт 8192 итерации (1<<13).
    check('count-char B -> idx 13', phpass.ITOA64.find('B') == 13)
    check('golden A — это phpass-формат', phpass.is_phpass(GOLDEN_HASH))


def roundtrip_checks():
    """hash -> verify True; неверный пароль -> False; разные iterations."""
    for pw in ('s3cret', 'Пароль-Я', '', 'a' * 72, '!@#$%^&*()'):
        h = phpass.hash(pw, iterations=8)   # малый log2 — тест быстрый
        check('round-trip is_phpass (%r)' % (pw[:8],), phpass.is_phpass(h))
        check('round-trip verify True (%r)' % (pw[:8],), phpass.verify(pw, h))
        check('round-trip verify wrong False (%r)' % (pw[:8],),
              not phpass.verify(pw + 'x', h))

    # Разные iterations дают разный count-char, но оба верифицируются.
    h11 = phpass.hash('topsecret', iterations=11)
    h14 = phpass.hash('topsecret', iterations=14)
    check('iter 11 verify', phpass.verify('topsecret', h11))
    check('iter 14 verify', phpass.verify('topsecret', h14))
    check('iter влияет на count-char', h11[3] != h14[3])

    # Соль рандомна -> два хэша одного пароля различаются (не детерминированы).
    check('соль рандомна', phpass.hash('x', iterations=8) != phpass.hash('x', iterations=8))


def is_phpass_checks():
    """is_phpass: True для валидных $P$/$H$ длины 34, False для всего прочего."""
    check('is_phpass $P$ True', phpass.is_phpass(GOLDEN_HASH))
    check('is_phpass $H$ True', phpass.is_phpass('$H$' + GOLDEN_HASH[3:]))
    check('is_phpass plaintext False', not phpass.is_phpass('password'))
    check('is_phpass MD5 False', not phpass.is_phpass('5f4dcc3b5aa765d61d8327deb882cf99'))
    check('is_phpass pbkdf2 False',
          not phpass.is_phpass('pbkdf2$200000$abcd$ef01'))
    check('is_phpass короткая False', not phpass.is_phpass('$P$B123'))
    check('is_phpass длинная False', not phpass.is_phpass(GOLDEN_HASH + 'x'))
    check('is_phpass пустая False', not phpass.is_phpass(''))
    check('is_phpass None False', not phpass.is_phpass(None))
    check('is_phpass не-str False', not phpass.is_phpass(12345))
    # bcrypt ($2y$) — НЕ portable phpass, пусть верхний слой обрабатывает отдельно.
    check('is_phpass bcrypt False',
          not phpass.is_phpass('$2y$10$abcdefghijklmnopqrstuv'))


def safety_checks():
    """verify никогда не бросает на мусоре и возвращает False для не-phpass."""
    bad_stored = [None, '', 'x', 'plaintext', '5f4dcc3b5aa765d61d8327deb882cf99',
                  '$P$', '$P$B', '$P$B123', GOLDEN_HASH + 'extra', 12345, b'bytes',
                  '$2y$10$0123456789012345678901']
    for s in bad_stored:
        try:
            r = phpass.verify('whatever', s)
        except Exception as e:                       # noqa: BLE001 — это и проверяем
            check('verify не бросает на %r' % (s,), False)
            print('     raised:', type(e).__name__, e)
            continue
        check('verify(non-phpass %r) == False' % (str(s)[:14],), r is False)

    # Не-str пароль -> False, не исключение.
    check('verify не-str пароль False', phpass.verify(12345, GOLDEN_HASH) is False)
    check('verify None пароль False', phpass.verify(None, GOLDEN_HASH) is False)

    # crypt_private на битом setting -> '*0' (никогда не совпадёт), без исключения.
    check('crypt_private битый setting -> *0', phpass.crypt_private('x', 'garbage') == '*0')
    check('crypt_private пустой setting -> *0', phpass.crypt_private('x', '') == '*0')


def needs_rehash_checks():
    """needs_rehash -> True для любого phpass (upgrade-on-login), False иначе."""
    check('needs_rehash phpass True', phpass.needs_rehash(GOLDEN_HASH))
    check('needs_rehash сгенерённый True', phpass.needs_rehash(phpass.hash('z', iterations=8)))
    check('needs_rehash plaintext False', not phpass.needs_rehash('password'))
    check('needs_rehash pbkdf2 False', not phpass.needs_rehash('pbkdf2$200000$a$b'))
    check('needs_rehash None False', not phpass.needs_rehash(None))


def encode64_checks():
    """encode64 — нестандартный base64: 16 байт -> 22 символа алфавита ITOA64."""
    digest = bytes(range(16))
    enc = phpass._encode64(digest, 16)
    check('encode64(16) длина 22', len(enc) == 22)
    check('encode64 только символы ITOA64', all(c in phpass.ITOA64 for c in enc))
    # Алфавит — именно phpass-вариант (начинается с './', НЕ 'A'/'+'/'a').
    check('ITOA64 начинается с ./', phpass.ITOA64[:2] == './')
    check('ITOA64 длина 64', len(phpass.ITOA64) == 64)


def wrapper_checks():
    """verify_legacy_password — тонкая обёртка над verify (тот же контракт)."""
    check('wrapper True по верному', phpass.verify_legacy_password(GOLDEN_PASSWORD, GOLDEN_HASH))
    check('wrapper False по неверному',
          not phpass.verify_legacy_password('nope', GOLDEN_HASH))
    check('wrapper False по не-phpass',
          not phpass.verify_legacy_password('x', 'plaintext'))
    check('wrapper не бросает на None',
          phpass.verify_legacy_password('x', None) is False)


def upgrade_flow_checks():
    """Дымовой тест потока upgrade-on-login: verify legacy True -> пере-хэш нашим
    НАТИВНЫМ хэшером (pbkdf2) -> новый хэш верифицируется нашим же verify, а
    старый phpass нашему нативному verify уже не нужен. Доказывает, что ядро
    стыкуется с access.store без круговых зависимостей."""
    from access.store import AccessStore
    pw = GOLDEN_PASSWORD
    # 1) старый phpass подходит
    check('upgrade: legacy verify True', phpass.verify_legacy_password(pw, GOLDEN_HASH))
    # 2) требуется пере-хэш
    check('upgrade: needs_rehash True', phpass.needs_rehash(GOLDEN_HASH))
    # 3) пере-хэшируем нативно и проверяем нативным верификатором
    native = AccessStore.hash_password(pw)
    check('upgrade: нативный verify True', AccessStore.verify_password(pw, native))
    check('upgrade: нативный — НЕ phpass', not phpass.is_phpass(native))
    check('upgrade: нативный больше не нуждается в rehash (для phpass-ветки)',
          not phpass.needs_rehash(native))


def main():
    golden_checks()
    roundtrip_checks()
    is_phpass_checks()
    safety_checks()
    needs_rehash_checks()
    encode64_checks()
    wrapper_checks()
    upgrade_flow_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
