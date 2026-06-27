#!/usr/bin/env python3
"""Verifier for Joomla 2.5 / phpass «Portable PHP password hashes» (prefix ``$P$``)
— cutover ``jirbis`` → Biblio, issue #294.

Контекст (узел cutover)
-----------------------
Боевой ``jirbis`` (Joomla 2.5) хранит пароли сотрудников/читателей портала в
``jos_users.password`` хэшем **phpass** («Portable PHP password Hashing
framework» Соломона Камворта, тот же алгоритм, что в WordPress) с идентификатором
``$P$``. Старый WordPress-импорт мог дать вариант ``$H$`` (тот же алгоритм, иной
id-символ). Чтобы перенесённые учётки вошли СО СВОИМ существующим паролем без
сброса, наш вход должен уметь СВЕРИТЬ введённый пароль с таким хэшем, а при
успехе — ПЕРЕ-ХЭШИРОВАТЬ его нашим нативным форматом (``access.store`` pbkdf2-
sha256) и сохранить (upgrade-on-login), чтобы legacy-формат вымывался по мере
входов и боевой phpass переставал быть источником истины.

Это переиспользуемое КРИПТО-ЯДРО: чистый stdlib (``hashlib``/``hmac``/``secrets``),
без внешних зависимостей и без обращения к боевым данным. Реальные 240 хэшей здесь
не нужны — алгоритм самодостаточен и проверяется голден-векторами в
``tests/test_phpass.py`` (в т.ч. внешне-известным вектором WordPress).

Канонический алгоритм phpass (``crypt_private``)
------------------------------------------------
Хэш — строка из 34 символов::

    $P$ B 12345678 9abcdef0123456789abcdef0
    └┬┘ │ └───┬──┘ └──────────┬───────────┘
     id │   соль (8)      encode64(md5-digest, 16) = 22 символа
        └ символ счётчика итераций: count = 1 << ITOA64.index(символ)

Проверка пароля:
  1. ``hash = md5(salt + password)`` (raw 16 байт);
  2. ``count`` раз: ``hash = md5(hash + password)``;
  3. результат = первые 12 символов ``setting`` (``$P$`` + count-char + соль)
     + ``encode64(hash, 16)`` (нестандартный base64, алфавит ниже);
  4. сравнить с сохранённым значением (постоянное время).

ВАЖНО: используется НЕ стандартный base64. Алфавит phpass::

    ./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz

и собственная функция ``encode64`` (порядок бит как в исходном PHP phpass), а НЕ
``base64.b64encode``.

Публичный API
-------------
* ``is_phpass(stored) -> bool``     — это phpass-хэш (``$P$``/``$H$``, длина 34)?
* ``verify(password, stored) -> bool`` — пароль подходит? (не-phpass вход → False,
  не исключение; сравнение через ``hmac.compare_digest``).
* ``hash(password, iterations=13) -> str`` — сгенерировать phpass-хэш (соль через
  ``secrets``); нужен для round-trip тестов и теоретического обратного экспорта.
* ``needs_rehash(stored) -> bool``  — любой legacy/phpass-хэш → True (вызывающий
  обязан пере-хэшировать в наш нативный формат при успешном входе).
* ``verify_legacy_password(password, stored) -> bool`` — тонкая документированная
  обёртка над ``verify`` с описанием потока upgrade-on-login (см. её docstring).
"""
import hashlib
import hmac
import secrets

# Нестандартный base64-алфавит phpass («itoa64»). НЕ совпадает со стандартным
# base64 и НЕ с bcrypt-алфавитом — порядок символов важен для совместимости.
ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

# Идентификаторы portable-хэша. ``$P$`` — phpass/Joomla/WordPress; ``$H$`` —
# исторический вариант phpBB3 (тот же алгоритм). Оба сверяем одинаково.
_IDS = ('$P$', '$H$')

# Длина portable-хэша: 3 (id) + 1 (count-char) + 8 (salt) + 22 (encode64 от 16
# байт) = 34. Любая иная длина — это не phpass.
PHPASS_LEN = 34

# Диапазон допустимого log2(count). Канонический phpass: 7..30 (count = 1<<N).
# Joomla 2.5 по умолчанию пишет count-char 'B' (index 13 → 8192 итераций).
_MIN_LOG2 = 7
_MAX_LOG2 = 30
_DEFAULT_LOG2 = 13   # Joomla 2.5 default (count-char 'B')


def _encode64(data, count):
    """phpass ``encode64`` — упаковка ``count`` байт ``data`` в строку алфавита
    ``ITOA64``, бит-в-бит как оригинальный PHP ``PasswordHash::encode64``.

    Берёт по 3 байта (24 бита) и раскладывает в 4 символа по 6 бит, добивая
    хвост. Для 16-байтового md5-дайджеста даёт 22 символа. Это НЕ стандартный
    base64 (иной алфавит И иной порядок добивания хвоста), поэтому реализуем
    вручную, а не через ``base64``."""
    out = []
    i = 0
    while i < count:
        value = data[i]
        i += 1
        out.append(ITOA64[value & 0x3f])
        if i < count:
            value |= data[i] << 8
        out.append(ITOA64[(value >> 6) & 0x3f])
        if i >= count:
            break
        i += 1
        if i < count:
            value |= data[i] << 16
        out.append(ITOA64[(value >> 12) & 0x3f])
        if i >= count:
            break
        i += 1
        out.append(ITOA64[(value >> 18) & 0x3f])
    return ''.join(out)


def crypt_private(password, setting):
    """Каноническая phpass ``crypt_private``: посчитать хэш ``password`` под
    параметрами из ``setting`` (id + count-char + 8-символьная соль).

    ``setting`` — это либо полный сохранённый хэш (берутся только первые 12
    символов как «настройка»), либо самостоятельно собранная строка
    ``id + count_char + salt``. Возврат — строка длиной 34 (``setting[:12]`` +
    encode64 от 16-байтового md5). При нераспознанном ``setting`` возвращает
    ``'*0'`` (как оригинал) — это никогда не совпадёт с валидным хэшем.

    Алгоритм: ``h = md5(salt+password)``; затем ``count = 1<<idx`` раз
    ``h = md5(h+password)``; ``encode64(h, 16)``."""
    output = '*0'
    if len(setting) < 12 or setting[:3] not in _IDS:
        return output

    count_char = setting[3]
    count_log2 = ITOA64.find(count_char)
    if count_log2 < _MIN_LOG2 or count_log2 > _MAX_LOG2:
        return output
    count = 1 << count_log2

    salt = setting[4:12]
    if len(salt) != 8:
        return output

    pw_bytes = password.encode('utf-8') if isinstance(password, str) else password

    # Базовый раунд: md5(salt + password); далее `count` повторных md5(hash+pw).
    digest = hashlib.md5(salt.encode('ascii') + pw_bytes).digest()
    for _ in range(count):
        digest = hashlib.md5(digest + pw_bytes).digest()

    return setting[:12] + _encode64(digest, 16)


def is_phpass(stored):
    """True, если ``stored`` похоже на phpass portable-хэш: начинается с ``$P$``
    или ``$H$`` И имеет длину 34. Защищён от не-str/пустого входа (→ False)."""
    if not isinstance(stored, str) or len(stored) != PHPASS_LEN:
        return False
    return stored[:3] in _IDS


def verify(password, stored):
    """True, если ``password`` соответствует phpass-хэшу ``stored``.

    Безопасно к мусорному входу: не-phpass ``stored`` (плейнтекст, MD5, None,
    короткая строка, не-str) → ``False`` (НЕ исключение). Сравнение через
    ``hmac.compare_digest`` (постоянное время). Пустой пароль допустим как
    значение, но почти наверняка не совпадёт с реальным хэшем."""
    if not is_phpass(stored):
        return False
    if not isinstance(password, str):
        return False
    computed = crypt_private(password, stored)
    # Длина 34 у валидного результата; '*0' (ошибка разбора) сюда не пройдёт по
    # длине, но compare_digest всё равно безопасен.
    if len(computed) != PHPASS_LEN:
        return False
    return hmac.compare_digest(computed, stored)


def hash(password, iterations=_DEFAULT_LOG2):
    """Сгенерировать новый phpass-хэш для ``password``.

    ``iterations`` — это log2 числа раундов (count = 1<<iterations); диапазон
    зажимается в [7, 30]. Соль (8 символов алфавита ``ITOA64``) берётся из
    криптостойкого ``secrets``. Нужен для round-trip тестов и теоретического
    обратного экспорта в Joomla-совместимый формат; НАШ нативный вход хранит
    пароли pbkdf2-sha256 (``access.store``), а не этим."""
    if not isinstance(password, str):
        raise TypeError('password must be str')
    log2 = max(_MIN_LOG2, min(_MAX_LOG2, int(iterations)))
    salt = ''.join(secrets.choice(ITOA64) for _ in range(8))
    setting = '$P$' + ITOA64[log2] + salt
    return crypt_private(password, setting)


def needs_rehash(stored):
    """True для ЛЮБОГО legacy-хэша, который наш вход должен заменить на нативный
    формat при успешном входе (upgrade-on-login).

    Сейчас это любой phpass portable-хэш (``$P$``/``$H$``): он по определению
    «чужой» для нашего pbkdf2-хранилища, поэтому каждый успешный вход по phpass —
    повод пере-хэшировать. Вызывающий (живой auth-роут) обязан при ``verify`` ==
    True И ``needs_rehash`` == True заменить сохранённое значение результатом
    нашего нативного хэшера и сохранить (см. ``verify_legacy_password``)."""
    return is_phpass(stored)


def verify_legacy_password(password, stored):
    """Тонкая обёртка: проверить ``password`` против legacy-phpass ``stored``.

    Поток **upgrade-on-login** (как вызывающий должен это применять)::

        if phpass.verify_legacy_password(supplied, stored):
            # 1) пароль верный по СТАРОМУ (phpass) формату — пускаем
            if phpass.needs_rehash(stored):
                # 2) пере-хэшируем нашим НАТИВНЫМ хэшером и persist'им, чтобы
                #    legacy-формат вымывался и больше не зависел от phpass:
                new_hash = AccessStore.hash_password(supplied)  # pbkdf2-sha256
                store.set_password_hash(account_id, new_hash)    # persist
            grant_session(...)

    Сам пере-хэш/persist НАМЕРЕННО НЕ здесь: это чистая (без побочных эффектов)
    проверка, чтобы её можно было звать из любого слоя (staff-login и reader-
    login имеют разные хранилища пароля — staff_account.pass_hash против поля RDR
    130/100). Точку подключения см. в ``core.py`` (маркер ``# INTEGRATION POINT``
    в ``verify_reader_password`` и в ``AccessStore.authenticate``/``auth_staff``).

    Возврат: True/False. К не-phpass ``stored`` возвращает False (пусть legacy-
    цепочка вызывающего попробует другие форматы — плейнтекст/MD5/pbkdf2)."""
    return verify(password, stored)
