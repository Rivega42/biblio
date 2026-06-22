#!/usr/bin/env python3
"""Офлайн-адаптер прямого чтения мастер-файлов ИРБИС64 (`.mst` + `.xrf`).

Локальный источник для миграции (GitHub #225, эпик #223): читает базу данных
ИРБИС64 **прямо с диска**, без запущенного сервера, разбирая физический формат
мастер-файла (`<db>.mst`) и таблицы перекрёстных ссылок (`<db>.xrf`). Это
альтернатива сетевому пути (`irbis.SessionManager`): мигратор и интроспекция
получают записи через тот же утиный интерфейс ``max_mfn`` / ``read_record``,
поэтому источник «сеть» и источник «файл» взаимозаменяемы.

Зачем офлайн-путь. Чтобы перенести библиотеку с устаревшей САБ, не нужен живой
сервер ИРБИС64 — достаточно скопированной папки DataPath. Адаптер читает байты
сам и отдаёт каноническую запись в той же форме ``{поле: [{подполе: значение}]}``,
что и ``access.catalog.CatalogStore`` / ``tools.migrate_irbis.map_catalog_record``.

Формат (выверен по реальным `C:\\IRBIS64\\Datai\\IBIS\\ibis.MST/.XRF` и `RDR`,
подтверждён реверсом — см. docs/recon/deep/reference/protocol/DECOMPILATION_FINDINGS.md:
числовые поля ИРБИС64 — big-endian, явные ``htonl``/``ntohl`` в движке)

`.xrf` — таблица MFN → смещение в `.mst`
----------------------------------------
Массив 12-байтовых записей, по одной на MFN (1-based: запись с индексом ``i``
соответствует ``MFN = i + 1``). Поля big-endian. Запись хранит абсолютное
файловое смещение записи в `.mst`, упакованное парой 32-битных слов
``(XRF_LOW, XRF_HIGH)`` (старший бит ``XRF_LOW`` — флаг логического удаления,
как в классическом ISIS/ИРБИС). Полное смещение восстанавливается из младших и
старших разрядов; в наблюдаемых файлах оно умещается в первом слове, но мы
читаем 64-битно, чтобы поддержать `.mst` > 2 ГБ.

    смещение  размер  поле        значение
    +0x00     4       XRF_LOW     младшие разряды смещения; бит 0x80000000 = удалён
    +0x04     4       XRF_HIGH    старшие разряды смещения (обычно 0)
    +0x08     4       (резерв)    в наблюдаемых файлах = 0

`.mst` — мастер-файл записей
----------------------------
Первая запись файла (смещение 0) — **управляющая** (control record), 36 байт BE:

    +0x00     4       CTLMFN      (служебное, обычно 0)
    +0x04     4       NXTMFN      следующий свободный MFN  => max_mfn = NXTMFN - 1
    +0x08     4       NXTBLK_LOW  младшие разряды смещения хвоста (куда дописывать)
    +0x0c     4       NXTBLK_HIGH старшие разряды
    +0x10..   …       (резерв / флаги БД)

Каждая запись (по смещению из `.xrf`) — лидер 32 байта BE + директорий полей +
переменная часть:

    ЛИДЕР (32 байта, big-endian int32):
    +0x00     4       MFN         номер записи
    +0x04     4       MFRL        полная длина записи в байтах (лидер+дир.+данные)
    +0x08     4       PREV_LOW    backlink на пред. версию (младшие разряды)
    +0x0c     4       PREV_HIGH   backlink на пред. версию (старшие разряды)
    +0x10     4       BASE        смещение начала переменной части от начала записи
    +0x14     4       NVF         число полей (записей директория)
    +0x18     4       VERSION     версия записи
    +0x1c     4       STATUS      статус: бит 0x01 = ЛОГИЧЕСКИ УДАЛЕНА,
                                  бит 0x02 = длинная (несколько блоков),
                                  бит 0x20 = последняя/актуализированная версия

    ДИРЕКТОРИЙ (NVF × 12 байт, сразу за лидером, big-endian int32):
    +0x00     4       TAG         метка поля
    +0x04     4       POS         смещение значения от BASE
    +0x08     4       LEN         длина значения в байтах
    (инвариант: BASE == 32 + NVF*12)

    ПЕРЕМЕННАЯ ЧАСТЬ: для поля i значение лежит по
        запись_offset + BASE + POS[i], длиной LEN[i], кодировка CP1251.
    Разделитель подполей — '^': '^aЗначение^bДругое' => {'a': ..., 'b': ...}.
    Текст до первого '^' — «голова» поля (поля без подполей — голый текст).

Системная метка ``2147483647`` (MaxInt32) — GUID записи, не библиографическое
поле: в каноническую запись не попадает (как и в ``irbis.parser``).

Защита. Битый/короткий `.xrf`/`.mst`, метка/смещение/длина вне файла, исключение
декодирования — запись пропускается со счётчиком предупреждений, без падения.
"""
import os
import struct

# --------------------------------------------------------------------------- #
# Константы формата.
# --------------------------------------------------------------------------- #
XRF_ENTRY_SIZE = 12          # байт на запись таблицы перекрёстных ссылок
MST_LEADER_SIZE = 32         # байт лидера записи мастер-файла
MST_DIR_ENTRY_SIZE = 12      # байт на запись директория (tag/pos/len)
MST_CONTROL_SIZE = 36        # байт управляющей записи (первая в .mst)

STATUS_DELETED = 0x01        # бит «логически удалена»
STATUS_ABSENT = 0x80         # бит «отсутствует/заблокирована»
STATUS_DELETED_BITS = STATUS_DELETED | STATUS_ABSENT

XRF_DELETED_FLAG = 0x80000000  # старший бит XRF_LOW — признак удаления в .xrf

SUBFIELD_DELIM = '^'
SYSTEM_GUID_TAG = 2147483647   # MaxInt32 — системное поле GUID, не библиографическое

# Кодировка значений полей. Классический ИРБИС64 хранит записи в CP1251 (правило
# проекта, см. docs/recon/.../databases/*), НО встречаются UTF-8-сборки/базы
# (выверено на реальном C:\IRBIS64\Datai\IBIS: все поля — валидный UTF-8 с
# многобайтовой кириллицей). Поэтому декодирование адаптивное: если байты поля —
# валидный UTF-8 и содержат не-ASCII, читаем как UTF-8; иначе — как CP1251.
# Чисто-ASCII декодируется одинаково в обеих кодировках.
ENCODING = 'cp1251'            # документированная базовая кодировка формата

_MST_SUFFIX = '.mst'
_XRF_SUFFIX = '.xrf'


class IrbisMstError(Exception):
    """Ошибка структуры мастер-файла (отсутствует файл БД и т. п.)."""


# --------------------------------------------------------------------------- #
# Поиск файлов БД (на Windows расширения бывают .MST/.XRF в верхнем регистре).
# --------------------------------------------------------------------------- #
def _find_file(directory, db, suffix):
    """Путь к ``<db><suffix>`` в ``directory`` без учёта регистра, либо None."""
    target = (db + suffix).lower()
    try:
        names = os.listdir(directory)
    except OSError:
        return None
    for name in names:
        if name.lower() == target:
            return os.path.join(directory, name)
    return None


def _db_paths(data_path, db):
    """(mst_path, xrf_path) для БД. Подкаталог ``<data_path>/<db>/`` или сам
    ``data_path`` (некоторые DataPath держат файлы прямо в корне БД)."""
    candidates = [os.path.join(data_path, db), data_path]
    for directory in candidates:
        mst = _find_file(directory, db, _MST_SUFFIX)
        if mst:
            xrf = _find_file(directory, db, _XRF_SUFFIX)
            return mst, xrf
    return None, None


def list_databases(data_path):
    """Список кодов БД под DataPath ИРБИС64.

    БД — это подкаталог, содержащий ``<имя_подкаталога>.mst`` (без учёта
    регистра). Возвращает отсортированный список кодов в верхнем регистре."""
    found = []
    try:
        entries = os.listdir(data_path)
    except OSError as e:
        raise IrbisMstError('DataPath недоступен: %s (%s)' % (data_path, e))
    for entry in entries:
        sub = os.path.join(data_path, entry)
        if not os.path.isdir(sub):
            continue
        if _find_file(sub, entry, _MST_SUFFIX):
            found.append(entry.upper())
    return sorted(found)


# --------------------------------------------------------------------------- #
# Управляющая запись / число записей.
# --------------------------------------------------------------------------- #
def _read_control(mst_path):
    """Управляющая запись `.mst`: (CTLMFN, NXTMFN, NXTBLK)."""
    with open(mst_path, 'rb') as f:
        raw = f.read(MST_CONTROL_SIZE)
    if len(raw) < 16:
        raise IrbisMstError('повреждённая управляющая запись: %s' % mst_path)
    ctlmfn, nxtmfn, nxtlow, nxthigh = struct.unpack('>4i', raw[:16])
    nxtblk = (nxthigh << 32) | (nxtlow & 0xffffffff)
    return ctlmfn, nxtmfn, nxtblk


def max_mfn(data_path, db):
    """Число записей БД = (NXTMFN - 1) из управляющей записи `.mst`.

    NXTMFN — следующий свободный MFN, значит наибольший существующий MFN равен
    ``NXTMFN - 1`` (записи нумеруются с 1). Возвращает 0 для пустой БД."""
    mst_path, _ = _db_paths(data_path, db)
    if not mst_path:
        raise IrbisMstError('не найден %s.mst в %s' % (db, data_path))
    _, nxtmfn, _ = _read_control(mst_path)
    return max(0, nxtmfn - 1)


# --------------------------------------------------------------------------- #
# Таблица перекрёстных ссылок `.xrf` — MFN → (смещение, удалён?).
# --------------------------------------------------------------------------- #
def _xrf_entry(xrf_path, mfn):
    """(offset, deleted) для ``mfn`` из `.xrf`, либо None если вне файла/пусто.

    Смещение собирается из пары BE-слов (XRF_LOW, XRF_HIGH); старший бит
    XRF_LOW — флаг удаления и в адрес не входит. offset == 0 => слот не занят."""
    if mfn < 1:
        return None
    pos = (mfn - 1) * XRF_ENTRY_SIZE
    try:
        with open(xrf_path, 'rb') as f:
            f.seek(pos)
            raw = f.read(XRF_ENTRY_SIZE)
    except OSError:
        return None
    if len(raw) < 8:
        return None
    low, high = struct.unpack('>2i', raw[:8])
    low_u = low & 0xffffffff
    deleted = bool(low_u & XRF_DELETED_FLAG)
    offset = (high << 32) | (low_u & ~XRF_DELETED_FLAG & 0xffffffff)
    if offset <= 0:
        return None
    return offset, deleted


# --------------------------------------------------------------------------- #
# Разбор одной записи мастер-файла.
# --------------------------------------------------------------------------- #
def _decode_field(raw_bytes):
    """Байты значения поля -> str. Адаптивно UTF-8 / CP1251 (см. ``ENCODING``).

    Многобайтовые UTF-8-последовательности кириллицы практически никогда не
    образуют «случайно валидный» CP1251-текст, поэтому валидный не-ASCII UTF-8
    декодируется как UTF-8; всё прочее (в т. ч. однобайтовый CP1251) — как
    CP1251 с заменой неотображаемых байтов (CP1251 покрывает все 256 значений,
    кроме 5 неопределённых позиций — их и заменяем, чтобы не падать)."""
    if any(b >= 0x80 for b in raw_bytes):
        try:
            return raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
    return raw_bytes.decode(ENCODING, 'replace')


def _parse_subfields(value):
    """'^aЗнач^bДр' -> (голова, {'a': 'Знач', 'b': 'Др'}).

    Голова — текст до первого '^'. Коды подполей приводятся к нижнему регистру
    (канон ``200^a``). Повторные коды: сохраняется первое вхождение (как в
    ``access.catalog`` / мигратор), порядок не важен для целевого хранилища."""
    if SUBFIELD_DELIM not in value:
        return value, {}
    parts = value.split(SUBFIELD_DELIM)
    head = parts[0]
    subs = {}
    for p in parts[1:]:
        if not p:
            continue
        code = p[0].lower()
        text = p[1:]
        subs.setdefault(code, text)
    return head, subs


def _instance_from_value(value):
    """Один экземпляр поля в каноне CatalogStore из сырого значения.

    Поле с подполями -> dict {код: значение} (коды в нижнем регистре). Поле без
    подполей -> голая строка (так его читает ``access.catalog._inst_value``).
    Это ровно форма ``tools.migrate_irbis._instance_from_field``."""
    head, subs = _parse_subfields(value)
    if not subs:
        return value
    inst = {}
    if head:
        inst[''] = head
    inst.update(subs)
    return inst


def _decode_record(raw, mfn_expected, warn):
    """Разобрать сырые байты записи -> (status, {поле: [{подполе}]}).

    Возвращает None при структурной порче (с предупреждением через ``warn``).
    ``status`` — целое из лидера (бит 0x01 = удалена)."""
    if len(raw) < MST_LEADER_SIZE:
        warn('запись короче лидера (mfn=%s)' % mfn_expected)
        return None
    (mfn, mfrl, _prev_low, _prev_high,
     base, nvf, _version, status) = struct.unpack('>8i', raw[:MST_LEADER_SIZE])

    if nvf < 0 or base < MST_LEADER_SIZE or base > len(raw):
        warn('лидер вне диапазона (mfn=%s base=%s nvf=%s)' % (mfn_expected, base, nvf))
        return None
    # Инвариант формата: переменная часть начинается строго за директорием.
    dir_end = MST_LEADER_SIZE + nvf * MST_DIR_ENTRY_SIZE
    if dir_end > len(raw) or base < dir_end:
        warn('директорий не сходится (mfn=%s nvf=%s base=%s)'
             % (mfn_expected, nvf, base))
        return None

    record = {}
    for i in range(nvf):
        d = MST_LEADER_SIZE + i * MST_DIR_ENTRY_SIZE
        tag, pos, ln = struct.unpack('>3i', raw[d:d + MST_DIR_ENTRY_SIZE])
        if tag == SYSTEM_GUID_TAG:
            continue                      # системный GUID — не библиографическое поле
        if tag <= 0 or pos < 0 or ln < 0:
            warn('битая запись директория (mfn=%s tag=%s)' % (mfn_expected, tag))
            continue
        start = base + pos
        end = start + ln
        if end > len(raw):
            warn('значение поля вне записи (mfn=%s tag=%s)' % (mfn_expected, tag))
            continue
        try:
            value = _decode_field(raw[start:end])
        except (UnicodeDecodeError, ValueError):
            warn('не декодируется (mfn=%s tag=%s)' % (mfn_expected, tag))
            continue
        record.setdefault(str(tag), []).append(_instance_from_value(value))
    return status, record


def _read_raw_record(mst_path, offset, length_hint=None):
    """Сырые байты записи из `.mst`. Длина берётся из MFRL лидера."""
    with open(mst_path, 'rb') as f:
        f.seek(offset)
        head = f.read(MST_LEADER_SIZE)
        if len(head) < MST_LEADER_SIZE:
            return head
        mfrl = struct.unpack('>i', head[4:8])[0]
        if mfrl < MST_LEADER_SIZE or mfrl > (1 << 28):
            # MFRL невменяемый — читаем щедрый блок, разбор всё равно проверит границы.
            return head + f.read(1 << 16)
        return head + f.read(mfrl - MST_LEADER_SIZE)


# --------------------------------------------------------------------------- #
# Публичный интерфейс чтения (зеркало сетевого пути irbis.SessionManager).
# --------------------------------------------------------------------------- #
def read_record(data_path, db, mfn, _warn=None):
    """Одна запись БД как канонический dict ``{поле: [{подполе: значение}]}``.

    Находит запись через смещение в `.xrf`, читает её из `.mst`, разбирает лидер,
    директорий и переменные поля, декодирует CP1251. Логически удалённые записи
    (флаг в `.xrf` или бит STATUS 0x01) -> возвращается None. Битая/короткая
    запись -> None (с предупреждением). MFN вне диапазона -> None."""
    warn = _warn or (lambda _m: None)
    mst_path, xrf_path = _db_paths(data_path, db)
    if not mst_path or not xrf_path:
        raise IrbisMstError('не найдены файлы БД %s в %s' % (db, data_path))

    entry = _xrf_entry(xrf_path, mfn)
    if entry is None:
        return None
    offset, deleted = entry
    if deleted:
        return None

    try:
        raw = _read_raw_record(mst_path, offset)
    except OSError as e:
        warn('ошибка чтения .mst (mfn=%s): %s' % (mfn, e))
        return None

    parsed = _decode_record(raw, mfn, warn)
    if parsed is None:
        return None
    status, record = parsed
    if status & STATUS_DELETED_BITS:
        return None
    return record


def read_records(data_path, db, _warn=None):
    """Итератор по всем живым записям БД: yield (mfn, ``{поле: [{подполе}]}``).

    Перебирает MFN 1..max_mfn; пропускает логически удалённые, пустые и битые
    записи (с подсчётом предупреждений). Потребляется мигратором/интроспекцией
    точно так же, как сетевой путь."""
    warn = _warn or (lambda _m: None)
    top = max_mfn(data_path, db)
    for mfn in range(1, top + 1):
        record = read_record(data_path, db, mfn, _warn=warn)
        if record is None:
            continue
        yield mfn, record


# --------------------------------------------------------------------------- #
# Сборка `.mst`+`.xrf` пары из записей — для тестов и как обратимая спецификация
# формата (синтетические фикстуры строятся ровно по разобранному выше layout'у).
# --------------------------------------------------------------------------- #
def build_mst_xrf(records, deleted_mfns=()):
    """Собрать (mst_bytes, xrf_bytes) из списка записей.

    ``records`` — список ``{tag(str|int): [значение|{подполе: значение}]}`` (по
    одному элементу на MFN, начиная с MFN=1). Каждое значение поля сериализуется
    обратно в форму ``^aЗнач^bДр`` (CP1251). ``deleted_mfns`` — множество MFN,
    помечаемых удалёнными (бит STATUS 0x01). Это точная инверсия парсера —
    используется тестами для построения временной пары без реальных данных."""
    deleted = set(deleted_mfns)
    mst = bytearray()
    # Управляющая запись: NXTMFN = число записей + 1.
    nxtmfn = len(records) + 1
    mst += struct.pack('>4i', 0, nxtmfn, 0, 0)
    mst += b'\x00' * (MST_CONTROL_SIZE - 16)

    xrf = bytearray()
    for idx, fields in enumerate(records):
        mfn = idx + 1
        offset = len(mst)

        # Переменная часть + директорий.
        var = bytearray()
        directory = []
        for tag, instances in fields.items():
            for inst in instances:
                value = _serialize_value(inst)
                encoded = value.encode(ENCODING)
                directory.append((int(tag), len(var), len(encoded)))
                var += encoded

        nvf = len(directory)
        base = MST_LEADER_SIZE + nvf * MST_DIR_ENTRY_SIZE
        mfrl = base + len(var)
        status = STATUS_DELETED if mfn in deleted else 0x20  # 0x20 = последняя версия

        leader = struct.pack('>8i', mfn, mfrl, 0, 0, base, nvf, 1, status)
        dir_bytes = b''.join(struct.pack('>3i', t, p, l) for (t, p, l) in directory)
        mst += leader + dir_bytes + bytes(var)

        # XRF: смещение в первом слове; старший бит при логическом удалении.
        low = offset
        if mfn in deleted:
            low |= XRF_DELETED_FLAG
        xrf += struct.pack('>2i', _as_int32(low), 0) + b'\x00' * 4

    return bytes(mst), bytes(xrf)


def _serialize_value(inst):
    """Канонический экземпляр поля -> сырая строка ``^aЗнач``.

    Голая строка -> как есть. dict -> голова (ключ '') + '^код'+значение."""
    if isinstance(inst, str):
        return inst
    if isinstance(inst, dict):
        out = inst.get('', '')
        for code, text in inst.items():
            if code == '':
                continue
            out += SUBFIELD_DELIM + str(code) + str(text)
        return out
    return str(inst)


def _as_int32(value):
    """Упаковать беззнаковое 32-битное значение в знаковый int для struct '>i'."""
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value
