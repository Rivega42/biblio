#!/usr/bin/env python3
"""MARC ISO 2709 import/export — the Каталогизатор/Утилиты обмена-данными контур.

Контур «обмен библиографическими записями» (Каталогизатор → Утилиты, сейчас
~10%): сериализация НАШИХ tag-keyed записей (тот же I1 field/subfield draft, что у
``access/pft.py`` / ``access/catalog.py``) в стандарт **ISO 2709** и обратно.
Записи ИРБИС — RUSMARC (семья UNIMARC), поэтому наш экспорт = ISO 2709 наших же
полей; контент-формат (UNIMARC/MARC21) на байтовую раскладку ISO 2709 не влияет —
это чистый транспортный конверт.

Структура ISO 2709 (один record)
--------------------------------
::

    [ leader(24) ][ directory ... ][ FT ][ field data ... ][ RT ]
                                     0x1e                     0x1d

  * **Leader** — 24 символа. Значимые для нас позиции (остальные — константы
    каталога):
      00-04  record length (5 цифр, вся запись в БАЙТАХ, дополнено нулями)
      05     record status ('n' new)
      06     type of record ('a' textual)
      07     bibliographic level ('m' monograph)
      08-09  два пробела (тип контроля / неопр.)
      10     indicator count ('2')
      11     subfield code count ('2' — ``\x1f`` + 1 символ кода)
      12-16  base address of data (5 цифр: 24 + длина directory + 1 FT)
      17     encoding level
      18     descriptive cataloguing form
      19     multipart resource record level
      20-23  entry map ('4500' — длины 4/5/0/0 + резерв)
  * **Directory** — по 12 символов на поле:
      tag(3) + field-length(4) + starting-offset(5).
    Длина и смещение поля — в БАЙТАХ (utf-8), смещение относительно base address.
    Directory завершается полевым терминатором ``\x1e`` (FT).
  * **Field data** — для каждого поля по порядку directory:
      * поле БЕЗ подполей (контрольное/скаляр, напр. 101/10-как-строка): сразу
        значение, затем ``\x1e``.
      * поле С подполями: два индикатора (2 символа) + для каждого подполя
        ``\x1f`` + код(1) + значение; в конце поля ``\x1e``.
    Тег поля 00X (< 010) трактуется как контрольное (без индикаторов/подполей) —
    как в MARC21/UNIMARC; у нас это типично 001/005 и т.п. Прочие скалярные поля
    (значение — голая строка) тоже пишутся без индикаторов/подполей.
  * Запись завершается терминатором записи ``\x1d`` (RT).

Кодировка — utf-8. ВНИМАНИЕ: длины/смещения в directory считаются в БАЙТАХ utf-8
(кириллица — 2 байта/символ), иначе round-trip многобайтовых полей сломается.

Round-trip
----------
``from_iso2709(to_iso2709(r))`` даёт НОРМАЛИЗОВАННУЮ форму ``r``:
  * каждое поле — список инстансов (повторяющиеся поля — список, одиночные тоже
    становятся списком из одного элемента);
  * инстанс с подполями — ``{code: value}``; скалярное/контрольное поле — голая
    строка (значение целиком).
:func:`normalize` строит эту же форму из исходной записи, поэтому сравнивать
надо ``from_iso2709(to_iso2709(r)) == normalize(r)``.

Робастность
-----------
Парсинг устойчив к пустому/битому входу:
  * пустой ``b''`` / только пробелы → :func:`from_iso2709` поднимает
    :class:`MarcError`; :func:`import_batch` для пустого входа возвращает ``[]``.
  * усечённый/повреждённый leader или directory → :class:`MarcError`.
  * :func:`import_batch` парсит поток жадно по терминаторам записи; неполный
    «хвост» без RT игнорируется (а не роняет весь батч).

Чистый stdlib, без pip, без сети.
"""

__all__ = [
    'MarcError', 'to_iso2709', 'from_iso2709', 'export_batch', 'import_batch',
    'normalize',
]

# --------------------------------------------------------------------------- #
# Разделители ISO 2709 (ASCII control chars).
# --------------------------------------------------------------------------- #
FT = b'\x1e'        # field terminator  (конец поля и конец directory)
RT = b'\x1d'        # record terminator (конец записи)
SF = b'\x1f'        # subfield delimiter (перед кодом подполя)

LEADER_LEN = 24
DIR_ENTRY_LEN = 12          # tag(3) + length(4) + offset(5)
DEFAULT_INDICATORS = '  '   # два пробела, когда индикаторы не заданы

# Позиции leader, которые мы не вычисляем, — каталожные константы (UNIMARC-подобно).
# 00-04 длина / 12-16 base address заполняются вычислением; остальное — отсюда.
_LDR_STATUS = 'n'       # 05  new
_LDR_TYPE = 'a'         # 06  textual material
_LDR_BIBLEVEL = 'm'     # 07  monograph
_LDR_09 = '  '          # 08-09
_LDR_INDCOUNT = '2'     # 10  indicator count
_LDR_SFCOUNT = '2'      # 11  subfield code count (delimiter + 1 char)
_LDR_17 = ' '           # 17  encoding level
_LDR_18 = ' '           # 18  descriptive cataloguing form
_LDR_19 = ' '           # 19  multipart resource record level
_LDR_2023 = '4500'      # 20-23 entry map (4/5/0/0)


class MarcError(Exception):
    """Ошибка сериализации/разбора ISO 2709 (битый leader/directory/поток)."""


# --------------------------------------------------------------------------- #
# Нормализация записи (та же модель, что pft/catalog: scalar | dict | list).
# --------------------------------------------------------------------------- #
def _instances(raw):
    """Список инстансов поля: list как есть, иначе одноэлементный список."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _is_control_tag(tag):
    """Контрольное поле (00X, < 010) — пишется БЕЗ индикаторов/подполей.

    В MARC21/UNIMARC поля 001-009 — контрольные. У наших записей значение такого
    поля — голая строка. ``10`` (ISBN) уже двузначное (>=10) — НЕ контрольное,
    хотя как скаляр всё равно пишется без подполей (см. _inst_is_scalar)."""
    t = str(tag)
    return t.isdigit() and int(t) < 10


def _norm_tag(tag):
    """Тег → 3-символьная цифровая строка ('10' -> '010', '7' -> '007')."""
    t = str(tag).strip()
    if not t.isdigit():
        raise MarcError('некорректный тег поля: %r' % (tag,))
    if len(t) > 3:
        raise MarcError('тег длиннее 3 цифр: %r' % (tag,))
    return t.zfill(3)


def normalize(record):
    """Нормализованная форма записи — то, что выдаёт round-trip ``from_iso2709``.

    Каждое поле -> список инстансов; инстанс — голая строка (скаляр/контрольное)
    ИЛИ ``{code: value}`` (подполя, значения приведены к str, пустые подполя
    отброшены). Поля упорядочены по числовому тегу (как в directory ISO 2709 на
    round-trip); повторяющиеся поля сохраняют исходный порядок инстансов.

    Скаляр-инстанс с пустым значением и dict-инстанс без подполей опускаются
    (в ISO 2709 им нечего нести)."""
    if not record:
        return {}
    out = {}
    for tag in sorted(record.keys(), key=lambda k: (int(_norm_tag(k)), str(k))):
        tag3 = _norm_tag(tag)
        insts_out = []
        for inst in _instances(record[tag]):
            if isinstance(inst, dict):
                sub = {}
                for code, val in inst.items():
                    code = str(code)
                    if val is None or val == '':
                        continue
                    sub[code] = str(val)
                if sub:
                    insts_out.append(sub)
            else:
                val = '' if inst is None else str(inst)
                if val != '':
                    insts_out.append(val)
        if insts_out:
            out[tag3] = insts_out
    return out


# --------------------------------------------------------------------------- #
# Сериализация: record -> ISO 2709 bytes.
# --------------------------------------------------------------------------- #
def _encode_field(tag3, inst):
    """Закодировать ОДИН инстанс поля в байты ПОЛЯ (без терминатора FT).

    * dict с подполями -> индикаторы '  ' + ``\x1f<code><value>`` по каждому
      подполю (в порядке вставки).
    * голая строка (скаляр/контрольное) -> само значение, без индикаторов/подполей.
    """
    if isinstance(inst, dict):
        parts = [DEFAULT_INDICATORS.encode('utf-8')]
        for code, val in inst.items():
            parts.append(SF + str(code).encode('utf-8') + str(val).encode('utf-8'))
        return b''.join(parts)
    # скаляр/контрольное поле — голое значение
    return str(inst).encode('utf-8')


def to_iso2709(record):
    """Сериализовать tag-keyed запись в ISO 2709 (bytes, utf-8).

    Формат: leader(24) + directory(12/поле) + FT + поля(подполя через ``\x1f``,
    каждое поле завершено FT) + RT. Длины/смещения directory — в БАЙТАХ utf-8.
    Запись нормализуется (:func:`normalize`) перед записью, поэтому скаляры,
    одиночные и повторяющиеся поля раскладываются единообразно. Пустая запись
    даёт валидный «скелет» (leader + FT + RT) без полей."""
    norm = normalize(record)

    field_blobs = []      # (tag3, field_bytes_with_FT)
    for tag3 in sorted(norm.keys(), key=lambda t: int(t)):
        for inst in norm[tag3]:
            body = _encode_field(tag3, inst) + FT
            field_blobs.append((tag3, body))

    # directory + смещения (в байтах, относительно base address)
    directory = []
    offset = 0
    for tag3, body in field_blobs:
        length = len(body)
        if length > 9999:
            raise MarcError('поле %s длиннее 9999 байт (ISO 2709 limit)' % tag3)
        if offset > 99999:
            raise MarcError('смещение поля %s превышает 99999 байт' % tag3)
        directory.append('%3s%04d%05d' % (tag3, length, offset))
        offset += length
    directory_bytes = ''.join(directory).encode('utf-8') + FT

    data_bytes = b''.join(body for _tag, body in field_blobs) + RT

    base_address = LEADER_LEN + len(directory_bytes)
    record_length = base_address + len(data_bytes)
    if record_length > 99999:
        raise MarcError('длина записи %d превышает 99999 байт' % record_length)

    leader = (
        '%05d' % record_length          # 00-04
        + _LDR_STATUS                   # 05
        + _LDR_TYPE                     # 06
        + _LDR_BIBLEVEL                 # 07
        + _LDR_09                       # 08-09
        + _LDR_INDCOUNT                 # 10
        + _LDR_SFCOUNT                  # 11
        + '%05d' % base_address         # 12-16
        + _LDR_17                       # 17
        + _LDR_18                       # 18
        + _LDR_19                       # 19
        + _LDR_2023                     # 20-23
    )
    assert len(leader) == LEADER_LEN, 'leader != 24: %d' % len(leader)

    return leader.encode('utf-8') + directory_bytes + data_bytes


# --------------------------------------------------------------------------- #
# Разбор: ISO 2709 bytes -> record.
# --------------------------------------------------------------------------- #
def _parse_directory(dir_bytes):
    """Разобрать байты directory (без хвостового FT) в список записей каталога.

    Каждая запись — (tag3, length, offset). Длина directory должна быть кратна
    12; иначе — :class:`MarcError`."""
    if len(dir_bytes) % DIR_ENTRY_LEN != 0:
        raise MarcError('directory не кратен %d байтам (%d)'
                        % (DIR_ENTRY_LEN, len(dir_bytes)))
    entries = []
    for k in range(0, len(dir_bytes), DIR_ENTRY_LEN):
        chunk = dir_bytes[k:k + DIR_ENTRY_LEN]
        try:
            tag3 = chunk[0:3].decode('ascii')
            length = int(chunk[3:7])
            offset = int(chunk[7:12])
        except (ValueError, UnicodeDecodeError) as exc:
            raise MarcError('битая запись directory: %r' % (chunk,)) from exc
        entries.append((tag3, length, offset))
    return entries


def _decode_field(tag3, field_bytes):
    """Разобрать байты ОДНОГО поля (без хвостового FT) в инстанс.

    * есть ``\x1f`` -> поле с подполями: первые 2 байта — индикаторы (отбрасываем),
      далее сегменты ``\x1f<code><value>`` -> ``{code: value}``.
    * нет ``\x1f`` -> контрольное/скалярное поле -> голая строка."""
    if SF in field_bytes:
        # отрезаем индикаторы (2 символа) до первого разделителя подполя
        idx = field_bytes.find(SF)
        body = field_bytes[idx:]            # начинается с \x1f
        sub = {}
        for seg in body.split(SF):
            if not seg:
                continue
            code = seg[0:1].decode('utf-8')
            value = seg[1:].decode('utf-8')
            sub[code] = value
        return sub
    return field_bytes.decode('utf-8')


def from_iso2709(data):
    """Разобрать ОДНУ ISO 2709-запись (bytes) в нормализованную tag-keyed запись.

    Возвращает ``{tag3: [inst, ...]}`` (как :func:`normalize`): повторяющиеся
    поля -> список инстансов, подполя -> ``{code: value}``, контрольные/скаляры ->
    голая строка. Round-trip: ``from_iso2709(to_iso2709(r)) == normalize(r)``.

    Поднимает :class:`MarcError` на пустом/усечённом/битом входе (нет leader,
    нет base address, обрезан directory/data)."""
    if data is None:
        raise MarcError('пустой вход (None)')
    if isinstance(data, str):
        data = data.encode('utf-8')
    # хвостовой RT может присутствовать или нет — обрежем для удобства
    if not data or data.strip(b' \r\n') == b'':
        raise MarcError('пустой вход')
    if len(data) < LEADER_LEN:
        raise MarcError('вход короче leader (24 байта): %d' % len(data))

    leader = data[0:LEADER_LEN]
    try:
        base_address = int(leader[12:17])
    except ValueError as exc:
        raise MarcError('битый base address в leader: %r' % (leader[12:17],)) from exc
    if base_address < LEADER_LEN or base_address > len(data):
        raise MarcError('base address вне диапазона: %d (len=%d)'
                        % (base_address, len(data)))

    # directory — между leader и base address, минус хвостовой FT
    dir_region = data[LEADER_LEN:base_address]
    if not dir_region.endswith(FT):
        raise MarcError('directory не завершён FT (\\x1e)')
    dir_bytes = dir_region[:-1]
    entries = _parse_directory(dir_bytes)

    data_region = data[base_address:]
    # сбросим хвостовой RT, если он есть
    if data_region.endswith(RT):
        data_region = data_region[:-1]

    record = {}
    for tag3, length, offset in entries:
        seg = data_region[offset:offset + length]
        if len(seg) != length:
            raise MarcError('поле %s обрезано (нужно %d байт, есть %d)'
                            % (tag3, length, len(seg)))
        if not seg.endswith(FT):
            raise MarcError('поле %s не завершено FT (\\x1e)' % tag3)
        field_bytes = seg[:-1]              # без хвостового FT
        inst = _decode_field(tag3, field_bytes)
        # пропускаем пустые скаляры (нечего нести), как и normalize
        if not isinstance(inst, dict) and inst == '':
            continue
        record.setdefault(tag3, []).append(inst)
    return record


# --------------------------------------------------------------------------- #
# Батч (mass-export / mass-import утилиты).
# --------------------------------------------------------------------------- #
def export_batch(records):
    """Сконкатенировать ISO 2709 для списка записей (поток обмена).

    Утилита массового экспорта: каждая запись сериализуется :func:`to_iso2709`
    и склеивается встык (каждая уже завершена RT). Пустой список -> ``b''``."""
    return b''.join(to_iso2709(r) for r in (records or []))


def import_batch(data):
    """Разобрать поток ISO 2709 в список нормализованных записей.

    Жадно режет поток по терминатору записи ``\x1d`` (RT) и парсит каждый кусок
    :func:`from_iso2709`. Устойчиво к битому/пустому входу:
      * пустой/пробельный вход -> ``[]``;
      * неполный «хвост» без завершающего RT игнорируется (а не роняет батч);
      * кусок, который не разобрался (:class:`MarcError`), пропускается, чтобы
        одна битая запись не отменяла весь импорт.
    """
    if not data:
        return []
    if isinstance(data, str):
        data = data.encode('utf-8')
    if data.strip(b' \r\n') == b'':
        return []

    records = []
    start = 0
    n = len(data)
    while start < n:
        end = data.find(RT, start)
        if end == -1:
            break                           # хвост без RT — игнорируем
        chunk = data[start:end + 1]         # включая RT
        start = end + 1
        if chunk.strip(b' \r\n') in (b'', RT):
            continue
        try:
            records.append(from_iso2709(chunk))
        except MarcError:
            continue                        # битую запись пропускаем
    return records
