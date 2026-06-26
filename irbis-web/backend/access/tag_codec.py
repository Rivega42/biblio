#!/usr/bin/env python3
"""Кодек данных RFID-метки библиотечного фонда (ISO 28560-2 / Danish).

Чистый stdlib-кодек байтовой раскладки метки, восстановленной реверсом
нативного ``EasyBook_RFid.dll`` (см. ``docs/devices/TAG_DATA_MODEL.md``).
Главный вывод реверса: IDlogic пишет на метку **стандартный ISO 28560-2** —
проприетарного формата нет, для совместимости с промаркированным фондом Biblio
достаточно стандартного кодека. Этот модуль — pure-Python реализация (без БД,
без I/O), на которую опирается Reader Agent при чтении/записи user-memory
ISO 15693 ICODE SLI/SLIX.

Раскладка «объекта данных» (§2 дока), precursor-байт:
  * бит 7      — флаг «offset present» (расширенный заголовок)
  * биты 6..4  — КОД КОМПАКЦИИ (1..7), способ кодирования содержимого
  * биты 3..0  — относительный OID (тип данных); для первичного идентификатора = 1
  если бит7=1:  байт1 = offset, байт2 = длина, данные с offset 3
  если бит7=0:  байт1 = длина,  данные с offset 2 (offset=0)

Коды компакции (§3 дока):
  1 integer        — октеты payload в обратном порядке (big↔little) → число
  2 hexadecimal    — каждый байт → 2 hex-символа "0123456789ABCDEF"
  3 5-бит текст    — упаковка по 5 бит, +0x40 → символы '@'..'_' (заглавные A-Z)
  4 6-бит текст    — по 6 бит, +0x40 → символы '@'..'\x7f'
  5 7-бит текст    — по 7 бит, без смещения → полный ISO 646 IRV
  6 octet-string   — октеты payload как есть (строка байт)
  7 integer-string — то же копирование октетов (по §3 — как 6)

EAS/AFI (§5 дока) — командный уровень NXP ICODE SLIX; значения AFI ON/OFF и
пароль EAS конфигурируемые (не зашиты в DLL). Здесь — только константы/хелпер
форматирования состояния защиты; сама запись AFI/EAS — задача транспортного слоя.
"""

# --- Коды компакции (ISO 28560-2, §3 доки) -------------------------------
COMPACTION_INTEGER = 1        # FUN_0043c478 — октеты в обратном порядке
COMPACTION_HEX = 2            # FUN_0043c350 — байт → 2 hex-символа
COMPACTION_5BIT = 3           # +0x40, подмножество ISO 646 (заглавные/цифры)
COMPACTION_6BIT = 4           # +0x40
COMPACTION_7BIT = 5           # без смещения, полный ISO 646 IRV
COMPACTION_OCTET = 6          # FUN_0043c294 — октеты как есть
COMPACTION_INTEGER_STRING = 7  # по §3 копирует октеты так же, как 6

# Алфавит hex-таблицы из DLL (DAT_004afe6c)
_HEX_DIGITS = '0123456789ABCDEF'

# --- Относительные OID (типы данных, §4 доки) ----------------------------
OID_PRIMARY_ITEM_ID = 1   # Primary Item Identifier — штрихкод/инв. номер
OID_OWNER_LIBRARY = 5     # Owner library (ISIL) — по §4 (инференс)
OID_SET_INFORMATION = 6   # Set information / тип использования (инференс)

# --- AFI / EAS (§5 доки) -------------------------------------------------
# Значения AFI ON/OFF конфигурируемые (поля edAFION/edAFIOFF, дефолт 00).
# Здесь — типовые значения профиля библиотечной метки ISO 28560 / NXP ICODE:
#   0xC2 — "secured" (в обороте, противокражка активна),
#   0x07 — "free"/выдана (противокражка снята).
# Транспортный слой может переопределить из конфигурации стенда.
AFI_SECURE = 0xC2   # метка в фонде, EAS активен
AFI_FREE = 0x07     # метка выдана, EAS снят
AFI_NONE = 0x00     # AFI не задан (дефолт DLL)

# EAS — это бит безопасности ICODE SLIX (не байт в user-memory); маркер состояния.
EAS_ON = True       # противокражка включена (метка «звенит»)
EAS_OFF = False     # противокражка снята


class TagCodecError(Exception):
    """Некорректные данные метки (битый precursor, длина, payload)."""


# --- Утилиты упаковки N-бит текста ---------------------------------------

def _pack_nbit(text, bits, bias):
    """Упаковать строку в поток по ``bits`` бит на символ со смещением ``bias``.

    Каждый символ кодируется как ``(ord(ch) - bias)`` в ``bits`` бит, биты
    укладываются MSB-first в непрерывный поток, добитый нулями до целого байта.
    """
    acc = 0
    nbits = 0
    out = bytearray()
    for ch in text:
        code = ord(ch) - bias
        if code < 0 or code >= (1 << bits):
            raise TagCodecError(
                'символ %r вне диапазона %d-бит компакции (bias=%d)'
                % (ch, bits, bias))
        acc = (acc << bits) | code
        nbits += bits
        while nbits >= 8:
            nbits -= 8
            out.append((acc >> nbits) & 0xFF)
    if nbits:
        out.append((acc << (8 - nbits)) & 0xFF)
    return bytes(out)


def _unpack_nbit(data, bits, bias):
    """Распаковать поток по ``bits`` бит на символ со смещением ``bias``.

    Обратное к :func:`_pack_nbit`. Хвостовые биты-набивка (значение 0 → ord==bias,
    для 5/6-бит это символ '@') не отбрасываются — длина задаётся payload; вызывающий
    при необходимости обрезает по бизнес-логике. Полностью нулевой хвостовой байт
    набивки (нет полного символа) пропускается.
    """
    acc = 0
    nbits = 0
    out = []
    for byte in data:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= bits:
            nbits -= bits
            code = (acc >> nbits) & ((1 << bits) - 1)
            out.append(chr(code + bias))
    return ''.join(out)


# --- Кодирование/декодирование содержимого по компакции ------------------

def _encode_payload(value, compaction):
    if compaction == COMPACTION_INTEGER:
        if not isinstance(value, int):
            value = int(value)
        if value < 0:
            raise TagCodecError('integer-компакция не поддерживает отрицательные значения')
        n = value.to_bytes(max(1, (value.bit_length() + 7) // 8), 'big')
        return bytes(reversed(n))  # октеты в обратном порядке (big↔little)
    if compaction == COMPACTION_HEX:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        s = str(value).upper()
        if len(s) % 2:
            raise TagCodecError('hex-строка нечётной длины: %r' % value)
        try:
            return bytes(int(s[i:i + 2], 16) for i in range(0, len(s), 2))
        except ValueError:
            raise TagCodecError('недопустимый hex: %r' % value)
    if compaction in (COMPACTION_OCTET, COMPACTION_INTEGER_STRING):
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        return str(value).encode('ascii', 'strict')
    if compaction == COMPACTION_5BIT:
        return _pack_nbit(str(value).upper(), 5, 0x40)
    if compaction == COMPACTION_6BIT:
        return _pack_nbit(str(value).upper(), 6, 0x40)
    if compaction == COMPACTION_7BIT:
        return _pack_nbit(str(value), 7, 0x00)
    raise TagCodecError('неизвестный код компакции: %r' % compaction)


def _decode_payload(data, compaction):
    if compaction == COMPACTION_INTEGER:
        return int.from_bytes(bytes(reversed(data)), 'big')
    if compaction == COMPACTION_HEX:
        return ''.join(_HEX_DIGITS[b >> 4] + _HEX_DIGITS[b & 0x0F] for b in data)
    if compaction in (COMPACTION_OCTET, COMPACTION_INTEGER_STRING):
        return data.decode('ascii', 'strict')
    if compaction == COMPACTION_5BIT:
        return _unpack_nbit(data, 5, 0x40)
    if compaction == COMPACTION_6BIT:
        return _unpack_nbit(data, 6, 0x40)
    if compaction == COMPACTION_7BIT:
        return _unpack_nbit(data, 7, 0x00)
    raise TagCodecError('неизвестный код компакции: %r' % compaction)


# --- Элемент (объект данных) ---------------------------------------------

def encode_element(oid, value, compaction):
    """Закодировать один объект данных ISO 28560-2 → bytes.

    :param oid: относительный OID (тип данных), 0..15.
    :param value: значение (int для integer; str/bytes для прочих компакций).
    :param compaction: код компакции (1..7), см. ``COMPACTION_*``.
    :returns: precursor-байт + длина + payload (короткая форма, бит7=0).
    """
    if not (0 <= oid <= 0x0F):
        raise TagCodecError('OID вне диапазона 0..15: %r' % oid)
    if not (1 <= compaction <= 7):
        raise TagCodecError('код компакции вне диапазона 1..7: %r' % compaction)
    payload = _encode_payload(value, compaction)
    if len(payload) > 0xFF:
        raise TagCodecError('payload слишком длинный для однобайтовой длины: %d' % len(payload))
    precursor = ((compaction & 0x07) << 4) | (oid & 0x0F)  # бит7=0 (короткая форма)
    return bytes([precursor, len(payload)]) + payload


def decode_element(data, offset=0):
    """Декодировать один объект данных из ``data`` начиная с ``offset``.

    :returns: кортеж ``(oid, value, next_offset)`` — тип, значение и индекс
        начала следующего объекта в потоке.
    :raises TagCodecError: при битом precursor/длине/payload.
    """
    if offset >= len(data):
        raise TagCodecError('пустой ввод или offset за концом данных')
    precursor = data[offset]
    ext = precursor & 0x80
    compaction = (precursor >> 4) & 0x07
    oid = precursor & 0x0F
    if compaction == 0:
        raise TagCodecError('Input data is corrupt: код компакции = 0')
    if ext:
        # расширенный заголовок: байт1=offset, байт2=длина, данные с +3
        if offset + 3 > len(data):
            raise TagCodecError('Input data is missing or corrupt: усечённый расширенный заголовок')
        skip = data[offset + 1]
        length = data[offset + 2]
        start = offset + 3
    else:
        if offset + 2 > len(data):
            raise TagCodecError('Input data is missing or corrupt: усечённый заголовок')
        skip = 0
        length = data[offset + 1]
        start = offset + 2
    end = start + length
    if end > len(data):
        raise TagCodecError('Input data is corrupt: payload выходит за пределы (%d > %d)'
                            % (end, len(data)))
    payload = data[start:end]
    value = _decode_payload(payload, compaction)
    # skip (offset present) — позиционное смещение элемента в логической записи;
    # на разбор потока не влияет, но валидируем как присутствующее.
    _ = skip
    return oid, value, end


# --- Блок (поток объектов) ------------------------------------------------

def encode_block(elements, compaction=None):
    """Закодировать набор объектов ``{oid: value}`` → непрерывный поток байт.

    :param elements: dict ``{oid: value}`` либо ``{oid: (value, compaction)}``.
    :param compaction: код компакции по умолчанию, если значение задано без него.
        Если не указан — выбирается эвристикой: int→integer(1), иначе octet(6).
    :returns: поток объектов (как пишется в user-memory ISO 15693).

    OID сортируются по возрастанию для детерминированной раскладки.
    """
    out = bytearray()
    for oid in sorted(elements):
        item = elements[oid]
        if isinstance(item, tuple):
            value, comp = item
        else:
            value, comp = item, compaction
        if comp is None:
            comp = COMPACTION_INTEGER if isinstance(value, int) else COMPACTION_OCTET
        out += encode_element(oid, value, comp)
    return bytes(out)


def decode_block(data):
    """Декодировать поток объектов → dict ``{oid: value}``.

    Читает объекты подряд до конца буфера. При повторе OID последний выигрывает.

    :raises TagCodecError: при битом потоке.
    """
    result = {}
    offset = 0
    n = len(data)
    while offset < n:
        # хвостовая набивка нулями (precursor=0 → compaction=0) — конец потока
        if data[offset] == 0x00:
            break
        oid, value, offset = decode_element(data, offset)
        result[oid] = value
    return result


# --- AFI / EAS хелпер -----------------------------------------------------

def security_state(afi):
    """Форматировать состояние защиты по байту AFI (§5 доки).

    :param afi: байт AFI (0..255).
    :returns: dict ``{'afi', 'secure', 'eas', 'label'}`` — где ``secure``/``eas``
        отражают, активна ли противокражка (AFI == AFI_SECURE).
    """
    if not (0 <= afi <= 0xFF):
        raise TagCodecError('AFI вне диапазона 0..255: %r' % afi)
    secure = afi == AFI_SECURE
    return {
        'afi': afi,
        'secure': secure,
        'eas': EAS_ON if secure else EAS_OFF,
        'label': 'secured' if secure else ('free' if afi == AFI_FREE else 'unknown'),
    }
