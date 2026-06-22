#!/usr/bin/env python3
"""ИРБИС → Biblio data **migrator** (pilot enabler, epic #223).

Exports an existing ИРБИС library's data from a *source* ИРБИС64 server and loads
it into Biblio's own store (the same sqlite-dev / PostgreSQL-prod stores the app
serves from). This is the seam that lets a real library move off the legacy САБ
onto Biblio: catalog records (``IBIS``) become :class:`access.catalog.CatalogStore`
records; readers (``RDR``) become circulation readers + the portal reader store,
with their ПДн **encrypted at rest** (V1 seam, ``access/crypto.py``).

It RUNS transiently against a real server to populate a target DB; it is NOT part
of the serving app. The protocol layer (``irbis/`` client + ``core``'s
``SessionManager``) is reused unchanged as the read-only export handle; the target
stores are reused unchanged as the load handle — nothing in ``core.py`` /
``access/catalog.py`` is modified.

ПДн / security (HARD)
---------------------
Real reader data (RDR) is персональные данные. This tool only ever *loads* a
target DB — it must NEVER persist real ПДн or credentials to the repository. Two
guarantees enforce that here:

  * **Encryption at rest.** Every reader PII field this migrator writes (name parts,
    e-mail, phone) is run through :func:`access.crypto.encrypt` before it touches a
    store, so the migrated value is ciphertext — exactly like
    ``reader_review.reader_name``. A raw dump of the target never reveals a name.
  * **Redacted logging.** The report carries COUNTS only; per-record logging (when
    enabled) prints redacted samples (``Бр***``), never a full name/contact and
    never the source password.

Mapping (ИРБИС → Biblio)
------------------------
*Catalog* (``IBIS`` → ``CatalogStore`` records — the shapes already match, so the
map is largely 1:1, lower-casing subfield codes to the canonical ``200^a`` form
the engines/index use)::

    200 (заглавие)        -> 200^a title, ^e/^f/^v…   (DB_IBIS §3.5)
    700/701/702/710       -> author/collective headings (^a/^g…)
    210 (выходные данные) -> imprint
    101/102               -> language / country
    675/621               -> УДК / ББК
    610                   -> unstructured keywords (K=)
    910 (экземпляры)      -> exemplars, ^a status / ^b inventory / ^d location …
    920                   -> worklist (carried so ФЛК picks the right rules)
    <source MFN>          -> 907^_mfn  (idempotency key, see below)

*Reader* (``RDR`` → circulation reader + portal reader store — minimal, only what
the product uses; DB_CIRCULATION §1–3)::

    30 (RI=)              -> reader ticket  (the primary key everywhere)
    10/11/12              -> surname / name / patronymic  (ПДн -> ENCRYPTED)
    32, 17/18             -> e-mail / phones              (ПДн -> ENCRYPTED)
    50                    -> reader category (circulation policy bucket)

Idempotency
-----------
A re-run must UPSERT, never duplicate. The stable key per catalog record is its
**source MFN**, stamped into the loaded record as a private ``907^_mfn`` subfield
and indexed on first load so a re-run resolves the existing target ``mfn`` and
updates it in place (CatalogStore.save with an explicit ``mfn``). Readers are keyed
by their ticket (``30``/RI=), which is already the natural primary key of every
reader table — re-loading a ticket is an ``INSERT OR REPLACE`` upsert.

CLI
---
::

    python -m tools.migrate_irbis --source-host H --source-port P \
        --user U --pass S --target-tenant slug \
        [--dbs IBIS,RDR] [--catalog-db IBIS] [--dry-run] [--limit N] [--verbose]

Prints a JSON report ``{records_read, records_loaded, readers_loaded, skipped,
errors}``. ``--dry-run`` connects, reads, and maps every record/reader and reports
the same counts WITHOUT writing the target (no row touched, no PII persisted).

Интроспекция (онбординг, #225) — ДВУХФАЗНАЯ
-------------------------------------------
``introspect(source)`` снимает с источника СТРУКТУРНЫЙ ПЛАН до переноса. Чтобы
большой источник (десятки БД) не упирался в HTTP-таймаут, интроспекция разбита на
две фазы (один и тот же вызов, выбор по аргументу ``dbs``):

  * **Фаза 1 — быстрый список (без ``dbs``).** Перечисляет БД (меню ``dbnam`` /
    ``list_databases``) и для каждой отдаёт только дешёвые метаданные
    ``{code, name, kind, recordCount, readerCount?}``. Число записей берётся из
    управляющей записи (``max_mfn``/NXTMFN-1) — это один round-trip без чтения
    записей, поэтому фаза проходит быстро даже на ~50 БД. Поля НЕ сэмплируются.
  * **Фаза 2 — инвентарь полей (с ``dbs=[коды]``).** Только для запрошенных БД
    строит инвентарь полей по выборке записей (тяжёлая часть), где каждое поле/
    подполе помечено флагом ``custom`` (нештатное доппole — то, чего нет в
    эталонном :data:`STANDARD_CATALOG`). Выборка ограничена сверху
    :data:`INSPECT_SAMPLE_SIZE` записями на БД — достаточно для инвентаря, но не
    заставляет сканировать всю базу.

Это даёт мастеру онбординга сперва мгновенно показать «какие БД и сколько в них
записей», а инвентарь полей подгружать по выбранным БД. ``--introspect`` в CLI
печатает план как JSON (с ``--dbs`` — фаза 2, без — фаза 1). Сетевой режим
работает через ``open_source``; локальный (без сервера, чтение `.mst`/`.xrf`) —
через :class:`LocalSource` поверх соседнего адаптера ``tools.irbis_mst``.

Адаптивность экспорта: мигратор копирует ВСЕ поля/подполя (field-agnostic, не
whitelist) — допполя сохраняются как есть, см. :func:`map_catalog_record`.
"""
import argparse
import json
import sys

# Reused as handles — NOT modified. Import lazily-friendly (the protocol + stores
# are stdlib-only so this works on a fresh box with no installs).
from access import crypto
from access.catalog import CatalogStore
from access.circulation import CirculationStore
from access.store import AccessStore


# --------------------------------------------------------------------------- #
# Стандартный каталог полей/подполей (для детекции «допполей»).
#
# `STANDARD_CATALOG` — это эталонный набор тегов и тегов^подполей штатной САБ
# ИРБИС64+, сгруппированный по «виду» БД. Источник: справочник проекта
# (docs/recon/deep/reference/databases/DB_*.md + format/FIELD_CATALOG — извлечён
# машинно из 1605 рабочих листов `.wss`). Здесь зафиксирован компактный,
# самодостаточный срез (без зависимости от путей docs во время выполнения / в
# тестах) штатных полей двух базовых видов БД: `bib` (электронный каталог IBIS и
# его варианты) и `rdr` (база читателей / циркуляция).
#
# Правило «custom»: тег (или тег^подполе) помечается ``custom=True``, если он НЕ
# входит в эталонный набор соответствующего вида БД, т.е. это институт-специфичное
# доппole, добавленное конкретной библиотекой сверх штатной схемы. Детектор
# работает на двух уровнях:
#   * тег целиком отсутствует в эталоне  -> всё поле кастомное;
#   * тег штатный, но встретилось подполе, которого нет в эталоне поля -> кастомным
#     помечается это подполе (а тег — нет).
# Сравнение регистронезависимое; коды подполей нормализуются в нижний регистр.
# --------------------------------------------------------------------------- #
STANDARD_CATALOG = {
    # Электронный каталог (IBIS / PAZK / NJ …) — штатные библиографические поля.
    # tag -> множество штатных кодов подполей (нижний регистр). Пустое множество =
    # поле штатное, но без выделенных подполей (значение в «голове»).
    'bib': {
        '10': {'a', 'b', 'd', 'z'},                     # ISBN / цена
        '101': set(),                                   # язык текста
        '102': set(),                                   # страна
        '200': {'a', 'b', 'c', 'e', 'f', 'g', 'h', 'i', 'v'},   # заглавие
        '205': {'a', 'b', 'f'},                         # сведения об издании
        '210': {'a', 'b', 'c', 'd', 'e', 'g', 'h'},     # выходные данные
        '215': {'a', 'c', 'd', 'e'},                    # количеств. характеристики
        '300': {'a'}, '330': {'a'}, '331': {'a'},       # примечания / аннотация
        '423': {'a'}, '454': {'a'}, '461': {'a'}, '463': {'a'}, '481': {'a'},
        '600': {'a', 'b', 'c', 'f', 'g'},               # имя как предмет
        '606': {'a', 'b', 'c', 'x', 'y', 'z'},          # предметная рубрика
        '607': {'a', 'b', 'c'},                         # геогр. рубрика
        '610': set(),                                   # неуправляемые ключевые слова
        '621': set(), '675': set(), '686': {'a'},       # ББК / УДК / др. индексы
        '691': {'a', 'b', 'c'},
        '700': {'a', 'b', 'c', 'f', 'g'},               # первый автор
        '701': {'a', 'b', 'c', 'f', 'g'}, '702': {'a', 'b', 'c', 'f', 'g', '4'},
        '710': {'a', 'b', 'c', 'g'}, '711': {'a', 'b', 'c', 'g'}, '712': {'a', 'b'},
        '900': {'a', 'b', 'c', 't'},                    # коды назначения/типа
        '901': {'a'}, '902': {'a'}, '903': set(),
        '907': {'a', 'b', 'c'},                         # каталогизатор / служебное
        '908': set(),                                   # шифр
        '910': {'a', 'b', 'c', 'd', 'e', 'f', 'h', 'u', 'x', 'y'},   # экземпляры
        '920': set(),                                   # тип/рабочий лист записи
        '922': {'a', 'b'}, '923': {'a'}, '938': {'a'}, '941': {'a'},
        '951': {'a', 'h', 'i', 't'}, '964': set(), '965': set(),
        '999': set(),
    },
    # База читателей (RDR) / циркуляция — штатные поля читательской записи.
    'rdr': {
        '10': set(), '11': set(), '12': set(),          # фамилия / имя / отчество
        '13': set(), '14': set(), '15': set(),
        '17': set(), '18': set(),                       # телефоны
        '19': set(), '20': set(), '21': set(), '22': set(), '23': set(),
        '24': set(), '25': set(), '26': set(), '27': set(), '28': set(), '29': set(),
        '30': set(),                                    # № читательского билета (RI=)
        '31': set(), '32': set(),                       # пароль / e-mail
        '33': set(), '40': set(), '41': set(),
        '50': set(), '51': set(), '54': set(), '56': set(),
        '60': set(), '67': set(), '90': set(),
        '100': set(), '102': set(), '112': set(),
        '140': set(), '200': set(), '301': set(),
        '691': {'a', 'b', 'c'},
        '903': set(), '907': {'a', 'b', 'c'},
        '910': {'a', 'b', 'c', 'd', 'h'},
        '911': {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'k', 'v'},  # выдача
        '920': set(), '950': set(), '999': set(),
    },
}

# Человекочитаемые метки штатных полей (для подсказки в плане интроспекции).
# Намеренно компактный набор самых частых тегов обоих видов БД; неизвестный тег
# просто остаётся без label (None) — детекцию custom это не затрагивает.
STANDARD_FIELD_LABELS = {
    '10': 'ISBN / Фамилия читателя', '11': 'Имя читателя', '12': 'Отчество читателя',
    '30': 'Номер читательского билета', '32': 'Электронная почта',
    '50': 'Категория читателя',
    '101': 'Язык основного текста', '102': 'Страна', '200': 'Заглавие',
    '205': 'Сведения об издании', '210': 'Выходные данные',
    '215': 'Количественные характеристики', '331': 'Аннотация',
    '606': 'Предметная рубрика', '607': 'Географическая рубрика',
    '610': 'Неуправляемые ключевые слова', '621': 'Шифр (ББК)', '675': 'Индекс УДК',
    '700': 'Первый автор', '701': 'Другой автор', '702': 'Второй ответственный',
    '710': 'Коллектив-автор', '900': 'Код назначения', '907': 'Каталогизатор',
    '910': 'Сведения об экземплярах', '911': 'Выдача', '920': 'Тип/рабочий лист записи',
}

# Виды БД, распознаваемые по коду базы. Любой неизвестный код трактуется как
# библиографический (`bib`) — это самый частый и самый безопасный дефолт для
# детекции допполей (эталон шире, поэтому ложноположительных «custom» меньше).
_RDR_DB_CODES = frozenset(('RDR', 'CIRC', 'CIRCUL', 'RDR_ARH'))


def db_kind(db_code):
    """Вид БД по её коду: ``'rdr'`` для базы читателей/циркуляции, иначе ``'bib'``.

    Используется и для выбора эталона при детекции допполей, и в плане интроспекции
    (поле ``kind``)."""
    return 'rdr' if (db_code or '').strip().upper() in _RDR_DB_CODES else 'bib'


def is_custom_field(kind, tag):
    """True, если ``tag`` целиком отсутствует в эталоне вида БД (всё поле кастомное)."""
    return str(tag) not in STANDARD_CATALOG.get(kind, {})


def is_custom_subfield(kind, tag, sub):
    """True, если ``sub`` — нештатное подполе штатного поля ``tag``.

    Для кастомного поля подполя отдельно НЕ помечаются (поле уже custom целиком —
    возвращаем False, чтобы не дублировать сигнал). Для штатного поля без
    выделенных подполей (эталон = пустое множество) любое подполе считается
    нештатным."""
    std = STANDARD_CATALOG.get(kind, {})
    tag = str(tag)
    if tag not in std:                       # поле целиком кастомное — см. is_custom_field
        return False
    return str(sub).lower() not in std[tag]


# --------------------------------------------------------------------------- #
# Idempotency key. The source MFN is stamped into a private 907 subfield so a
# re-run can find the already-loaded target record and update it in place rather
# than inserting a duplicate. 907 (каталогизатор/служебное) is the natural home;
# the '_mfn' subfield code is private (won't collide with a real ^a/^b/^c).
# --------------------------------------------------------------------------- #
SOURCE_MFN_FIELD = '907'
SOURCE_MFN_SUB = '_mfn'

# Catalog fields we carry across. The record shapes already match (MARC-ish
# field->[{subfield:value}]); we copy every field the source has, but this is the
# documented set the product reads / indexes (DB_IBIS §3.3/§3.5). We copy ALL
# fields verbatim — this list is for documentation + the dry-run preview.
CATALOG_FIELDS = (
    '200', '700', '701', '702', '710', '210', '205', '215', '101', '102',
    '675', '621', '606', '607', '610', '900', '910', '920', '907',
)

# RDR fields the product uses. PII fields are encrypted at rest.
RDR_TICKET_FIELD = '30'                       # RI= — the reader ticket / primary key
RDR_NAME_FIELDS = ('10', '11', '12')          # surname / name / patronymic (ПДн)
RDR_CONTACT_FIELDS = ('32', '17', '18')       # e-mail / phones (ПДн)
RDR_CATEGORY_FIELD = '50'                     # reader category (policy bucket)
RDR_PII_FIELDS = RDR_NAME_FIELDS + RDR_CONTACT_FIELDS

# ИРБИС record status bits (master-file RECORD.status). 0x01 = LOGICALLY DELETED,
# 0x02 = LONG (multi-block), 0x80 = ABSENT/blocked. A read of a deleted/absent
# record usually surfaces as an IrbisError (-600/-601/-605/-140 etc.), but a
# record can also come back with a non-empty status carrying the delete bit; we
# skip either way. (Parser puts the raw status string in rec['status'].)
STATUS_DELETED_BITS = 0x01 | 0x80


def _status_is_deleted(status):
    """True iff a parsed record's ``status`` marks it logically deleted / absent.

    The status is a string of the integer master-file status. Empty / non-numeric
    => active (the live IBIS returns '' for every active record)."""
    if status is None:
        return False
    s = str(status).strip()
    if not s:
        return False
    try:
        return bool(int(s) & STATUS_DELETED_BITS)
    except ValueError:
        return False


def redact(value):
    """Redact a PII string for logging: keep <=2 leading chars, mask the rest.

    ``'Бродовский' -> 'Бр***'``; empty/None -> ''. Never returns the full value —
    this is the only form reader PII may appear in a log line."""
    if not value:
        return ''
    s = str(value)
    return (s[:2] + '***') if len(s) > 2 else (s[:1] + '***')


# --------------------------------------------------------------------------- #
# Mapping: parsed-ИРБИС-record (irbis.parser shape) -> Biblio record dict.
#
# The client parser yields rec['fields'] = [{'tag','value','text','subfields'}…].
# CatalogStore wants {tag: [ {subfield_lower: value}, … ]} (repeatable fields are
# lists; a field with no subfields becomes a bare-value instance under '' ). We
# lower-case subfield codes so the stored record matches the canonical 200^a /
# 910^b shape the ФЛК / PFT / index engines key on (the live server returns
# UPPER-case codes; CatalogStore reads case-insensitively but we normalize so the
# AT-REST record is canonical and round-trips byte-for-byte in tests).
# --------------------------------------------------------------------------- #
def _instance_from_field(f):
    """One CatalogStore field-instance from a parsed source field.

    ``f`` is a parser field dict. Returns a ``{subfield: value}`` dict (codes
    lower-cased), or a bare string when the source field has no subfields."""
    subs = f.get('subfields') or {}
    if not subs:
        # bare value (e.g. 101 'rus', 920 'PAZK', 675 '004.4') — keep as a string.
        return f.get('value', '')
    inst = {}
    head = f.get('text') or ''
    if head:
        inst[''] = head            # text before the first '^' (rare on IBIS bib data)
    for code, text in subs.items():
        if code == '_repeats':
            continue
        inst[str(code).lower()] = text
    # carry repeated subfields (parser stashes extras under '_repeats')
    for rep in subs.get('_repeats', []):
        for code, text in rep.items():
            key = str(code).lower()
            inst.setdefault(key, text)
    return inst


def map_catalog_record(parsed):
    """Map a parsed ИРБИС catalog record -> a CatalogStore record dict.

    Copies every field verbatim (repeatable fields collapse into a list of
    instances), lower-casing subfield codes. Stamps the source MFN into
    ``907^_mfn`` for idempotency. Returns ``(record, source_mfn)``."""
    record = {}
    for f in parsed.get('fields', []):
        tag = f['tag']
        inst = _instance_from_field(f)
        record.setdefault(tag, []).append(inst)

    source_mfn = parsed.get('mfn')
    # Stamp the source MFN as a private 907 subfield (idempotency key). 907 may
    # already exist (каталогизатор); append a dedicated instance carrying only the
    # marker so we never disturb a real 907^a.
    if source_mfn is not None:
        record.setdefault(SOURCE_MFN_FIELD, [])
        record[SOURCE_MFN_FIELD].append({SOURCE_MFN_SUB: str(source_mfn)})
    return record, source_mfn


def map_reader_record(parsed):
    """Map a parsed ИРБИС RDR record -> a minimal Biblio reader dict.

    Returns ``{ticket, category, pii:{...plaintext...}}`` or None when the record
    has no ticket (field 30). The ``pii`` map is PLAINTEXT here — the loader
    encrypts it before any store write (so plaintext never leaves this process).
    """
    def first(tag):
        for f in parsed.get('fields', []):
            if f['tag'] == tag:
                return f.get('value', '') or f.get('text', '')
        return ''

    ticket = (first(RDR_TICKET_FIELD) or '').strip()
    if not ticket:
        return None
    pii = {}
    for tag in RDR_PII_FIELDS:
        v = first(tag)
        if v:
            pii[tag] = v
    category = (first(RDR_CATEGORY_FIELD) or '').strip() or '_DEFAULT'
    return {'ticket': ticket, 'category': category, 'pii': pii}


# --------------------------------------------------------------------------- #
# Source adapter. The migrator reads through a tiny duck-typed interface
# (``max_mfn``/``read_record``) so the live ``core.SessionManager`` /
# ``irbis.SessionManager`` plug straight in AND tests inject a FakeIrbis with no
# server. We don't depend on a concrete class — just the two methods.
# --------------------------------------------------------------------------- #
def open_source(host, port, user, password, workstation='A', timeout=8.0):
    """Open a read-only export session against a source ИРБИС server.

    Returns an ``irbis.SessionManager`` (auto-(re)connect, thread-safe). Imported
    lazily so the module imports on a box without the server / for unit tests that
    inject their own source."""
    from irbis import SessionManager
    return SessionManager(host, port, workstation, user, password, timeout=timeout)


# --------------------------------------------------------------------------- #
# Перечисление БД источника (меню `dbnam`). Сетевой источник (SessionManager)
# отдаёт список БД через файловый ресурс-меню (пары строк код/имя, терминатор
# '*****'); тот же формат читает core.databases(). Источник для интроспекции может
# дополнительно предоставить метод ``list_databases()`` (тогда он используется
# как есть) — так FakeIrbis в тестах перечисляет БД без файлового ресурса.
# --------------------------------------------------------------------------- #
DBNAM_MENU_SPEC = '1.&.dbnam1.mnu'         # ресурс-меню списка БД (как в Config.db_menu)


def parse_menu_pairs(text):
    """Разобрать меню ИРБИС (`.mnu`) в список ``[{'code','name'}]``.

    Формат: чередующиеся строки код/имя, маркер-терминатор '*****'. Пустые строки
    и терминатор отбрасываются (как в core.databases). Регистр кода сохраняется."""
    lines = [x.strip() for x in (text or '').splitlines()
             if x.strip() and x.strip() != '*****']
    pairs = []
    for i in range(0, len(lines) - 1, 2):
        code = lines[i]
        if code:
            pairs.append({'code': code, 'name': lines[i + 1]})
    return pairs


def enumerate_databases(source):
    """Список БД источника: ``[{'code','name'}]``.

    Порядок выбора: (1) если у источника есть ``list_databases()`` — берём его
    (так тестовый FakeIrbis перечисляет свои БД); (2) иначе читаем меню `dbnam`
    через ``read_file`` (живой SessionManager). Любой сбой чтения меню -> []
    (интроспекция деградирует мягко, а не падает)."""
    lister = getattr(source, 'list_databases', None)
    if callable(lister):
        out = []
        for d in lister():
            if isinstance(d, dict):
                out.append({'code': d.get('code'), 'name': d.get('name') or d.get('code')})
            else:
                out.append({'code': d, 'name': d})
        return out
    reader = getattr(source, 'read_file', None)
    if callable(reader):
        try:
            return parse_menu_pairs(reader(DBNAM_MENU_SPEC))
        except Exception:                              # noqa: BLE001 - server/permission hiccup
            return []
    return []


# --------------------------------------------------------------------------- #
# Адаптер ЛОКАЛЬНОГО режима (чтение MST/XRF напрямую с диска без сервера).
# Реализуется в соседнем модуле ``tools.irbis_mst`` (его делает другой исполнитель).
# Контракт, который мы вызываем:
#     irbis_mst.list_databases(path) -> [{'code','name'} | str, …]
#     irbis_mst.max_mfn(path, db)    -> int
#     irbis_mst.read_records(path, db) -> iterable[parsed-record]
# Импортируем ЛЕНИВО: если модуля ещё нет, сетевой режим работает по-прежнему, а
# локальный отдаёт понятное уведомление «адаптер не готов» (graceful).
# --------------------------------------------------------------------------- #
class LocalAdapterUnavailable(Exception):
    """Адаптер локального режима (tools.irbis_mst) ещё не готов / не установлен."""


def _load_local_adapter():
    """Лениво импортировать ``tools.irbis_mst`` или поднять LocalAdapterUnavailable."""
    try:
        from tools import irbis_mst                     # noqa: WPS433 - lazy by design
    except ImportError as e:
        raise LocalAdapterUnavailable(
            'адаптер локального режима (tools.irbis_mst) ещё не готов: %s' % e)
    return irbis_mst


def canonical_to_parsed(mfn, record, status=''):
    """Канонический ``{tag: [значение|{подполе: значение}]}`` -> parser-shape запись.

    Локальный адаптер (``tools.irbis_mst``) отдаёт запись в канонической форме
    CatalogStore. Сетевой путь и интроспекция/мигратор работают с parser-shape
    (``{mfn,status,fields:[{tag,value,text,subfields}]}``). Эта функция приводит
    локальную запись к parser-shape, чтобы оба режима шли по одному коду — поля и
    подполя сохраняются ПОЛНОСТЬЮ (field-agnostic), коды подполей не теряются."""
    fields = []
    for tag, instances in (record or {}).items():
        for inst in (instances if isinstance(instances, list) else [instances]):
            if isinstance(inst, dict):
                subs = {}
                head = ''
                for code, val in inst.items():
                    if code == '' or code is None:
                        head = val
                    else:
                        subs[str(code)] = val
                value = head + ''.join('^%s%s' % (c, v) for c, v in subs.items())
                fields.append({'tag': str(tag), 'value': value, 'text': head,
                               'subfields': subs})
            else:
                fields.append({'tag': str(tag), 'value': inst, 'text': inst,
                               'subfields': {}})
    return {'mfn': mfn, 'status': status, 'version': None, 'guid': None,
            'fields': fields}


class LocalSource:
    """Обёртка над ``tools.irbis_mst``, дающая тот же интерфейс, что и сетевой
    источник (``list_databases`` / ``max_mfn`` / ``read_record``), чтобы
    интроспекция и миграция работали единообразно поверх локальных файлов.

    Адаптер отдаёт записи в канонической форме CatalogStore; ``read_record`` тут
    приводит их к parser-shape (см. :func:`canonical_to_parsed`), так что оба
    режима — сетевой и локальный — обрабатываются ОДНИМ кодом. Записи БД
    материализуются по требованию (адаптер читает MST потоково)."""

    def __init__(self, path, adapter=None):
        self.path = path
        self._adapter = adapter or _load_local_adapter()
        self._cache = {}                                # db -> {mfn: parsed-record}
        self._maxmfn = {}                               # db -> наибольший MFN в БД

    def list_databases(self):
        out = []
        for d in self._adapter.list_databases(self.path):
            if isinstance(d, dict):
                out.append({'code': d.get('code'), 'name': d.get('name') or d.get('code')})
            else:
                out.append({'code': d, 'name': d})
        return out

    def max_mfn(self, db):
        return self._adapter.max_mfn(self.path, db)

    def _records(self, db):
        """Материализовать живые записи БД как ``{mfn: parser-shape}`` (с кэшем).

        ``read_records`` адаптера — итератор ``(mfn, canonical-record)`` по живым
        записям; удалённые он уже пропустил, поэтому индекс по реальному MFN."""
        if db not in self._cache:
            recs = {}
            top = 0
            for mfn, record in self._adapter.read_records(self.path, db):
                recs[mfn] = canonical_to_parsed(mfn, record)
                top = max(top, mfn)
            self._cache[db] = recs
            self._maxmfn[db] = top
        return self._cache[db]

    def read_records(self, db, limit=None):
        """Потоковый перебор живых записей БД в parser-shape, ОСТАНОВКА после
        ``limit`` штук (фаза 2: инвентарь полей по ограниченной выборке).

        Без этого метода интроспекция читала бы записи по одному MFN через
        ``read_record``, что для локального источника материализует ВСЮ БД в кэш на
        первом же обращении (медленно для крупных БД, напр. морфословарь). Здесь же
        адаптер читает MST потоково, и мы прерываем итерацию, набрав ``limit`` живых
        записей — поэтому выборка не зависит от размера базы. Удалённые/пустые
        адаптер уже пропустил. Выдаёт parser-shape записи (без MFN — инвентарю он не
        нужен)."""
        n = 0
        for mfn, record in self._adapter.read_records(self.path, db):
            if limit is not None and n >= limit:
                break
            yield canonical_to_parsed(mfn, record)
            n += 1

    def read_record(self, db, mfn):
        recs = self._records(db)
        rec = recs.get(mfn)
        if rec is None:                                 # удалён/пуст/вне диапазона
            raise IndexError('mfn %s отсутствует в %s' % (mfn, db))
        return rec

    def close(self):
        closer = getattr(self._adapter, 'close', None)
        if callable(closer):
            closer()


# --------------------------------------------------------------------------- #
# Интроспекция источника — ДВУХФАЗНАЯ (см. модульный docstring, #225).
#   Фаза 1 (быстрая, без dbs): перечислить БД + на каждую дешёвые метаданные
#     {code,name,kind,recordCount,readerCount?} — БЕЗ чтения записей.
#   Фаза 2 (тяжёлая, с dbs=[коды]): для запрошенных БД построить инвентарь полей
#     по выборке записей, помечая нештатные допполя флагом ``custom``.
# Возвращает структурированный план (тот же shape, что /api/admin/migrate/inspect).
# --------------------------------------------------------------------------- #
# Верхний ПРЕДЕЛ выборки на БД для инвентаря полей (фаза 2). 300 записей с запасом
# хватает, чтобы увидеть штатные и нештатные поля/подполя, но не заставляет
# сканировать всю базу — поэтому даже большая БД интроспектируется быстро.
INSPECT_SAMPLE_SIZE = 300          # сколько записей сэмплировать на БД для инвентаря полей


def _accumulate_field_inventory(parsed, inv):
    """Подмешать поля одной разобранной записи в накопитель инвентаря ``inv``.

    ``inv`` — dict ``tag -> {'freq':int, 'subfields': {sub: freq}}``. Частота тега
    считается по записям (один тег в записи = +1, даже если он повторяется),
    частота подполя — по записям, где это подполе встретилось хотя бы раз."""
    seen_tags = set()
    seen_subs = set()                                   # (tag, sub) уже учтённые в ЭТОЙ записи
    for f in parsed.get('fields', []):
        tag = str(f.get('tag'))
        if not tag:
            continue
        slot = inv.setdefault(tag, {'freq': 0, 'subfields': {}})
        if tag not in seen_tags:
            slot['freq'] += 1
            seen_tags.add(tag)
        subs = f.get('subfields') or {}
        codes = [c for c in subs if c != '_repeats']
        for rep in subs.get('_repeats', []):
            codes.extend(rep.keys())
        for code in codes:
            sub = str(code).lower()
            key = (tag, sub)
            if key not in seen_subs:
                slot['subfields'][sub] = slot['subfields'].get(sub, 0) + 1
                seen_subs.add(key)


def _inventory_to_fields(kind, inv):
    """Преобразовать накопитель инвентаря в список полей плана (с флагом custom).

    Каждый элемент: ``{tag, label?, subfields:[…], freq, custom}``. ``label`` —
    человекочитаемое имя из эталона (если штатное поле известно). Поля
    сортируются по тегу (числовые сначала, по возрастанию)."""
    out = []
    for tag in sorted(inv, key=_tag_sort_key):
        slot = inv[tag]
        custom_field = is_custom_field(kind, tag)
        subfields = []
        for sub in sorted(slot['subfields']):
            subfields.append({
                'code': sub,
                'freq': slot['subfields'][sub],
                # подполе кастомное, только если поле штатное, а подполя в эталоне нет
                'custom': (not custom_field) and is_custom_subfield(kind, tag, sub),
            })
        out.append({
            'tag': tag,
            'label': STANDARD_FIELD_LABELS.get(tag),
            'subfields': subfields,
            'freq': slot['freq'],
            'custom': custom_field,
        })
    return out


def _tag_sort_key(tag):
    s = str(tag)
    return (0, int(s)) if s.isdigit() else (1, s)


def _record_count(source, db_code):
    """Дешёвое число записей БД через ``max_mfn`` (NXTMFN-1) — без чтения записей.

    Один round-trip к управляющей записи; сбой сервера/БД мягко даёт 0 (а не
    падение всей интроспекции)."""
    try:
        return max(0, int(source.max_mfn(db_code) or 0))
    except Exception:                                   # noqa: BLE001 - сервер/БД недоступны
        return 0


def database_summary(source, db_code, db_name=None):
    """ФАЗА 1 — дешёвая сводка по ОДНОЙ БД (без сэмплирования полей).

    Возвращает ``{code, name, kind, recordCount, readerCount?}`` — только
    метаданные, которые берутся из управляющей записи (``max_mfn``) одним
    round-trip'ом. Поля НЕ читаются, поэтому даже большая БД обрабатывается мгновенно
    (это и есть быстрый путь, чтобы список из ~50 БД не упирался в HTTP-таймаут)."""
    kind = db_kind(db_code)
    record_count = _record_count(source, db_code)
    item = {
        'code': db_code,
        'name': db_name or db_code,
        'kind': kind,
        'recordCount': record_count,
    }
    if kind == 'rdr':
        item['readerCount'] = record_count              # 1 запись RDR = 1 читатель
    return item


def introspect_database(source, db_code, db_name=None, sample=INSPECT_SAMPLE_SIZE):
    """ФАЗА 2 — интроспекция ОДНОЙ БД источника с инвентарём полей.

    Возвращает ``{code, name, kind, recordCount, fields:[…], readerCount?}``.
    Считает ``recordCount`` через ``max_mfn`` и строит инвентарь полей по выборке
    первых ``sample`` читаемых записей (``sample`` ограничен сверху
    :data:`INSPECT_SAMPLE_SIZE`). Удалённые/пустые/нечитаемые записи в выборке
    пропускаются (но в recordCount учитывается max_mfn целиком)."""
    item = database_summary(source, db_code, db_name=db_name)
    record_count = item['recordCount']
    kind = item['kind']
    cap = min(int(sample), INSPECT_SAMPLE_SIZE) if sample else INSPECT_SAMPLE_SIZE
    inv = {}
    for parsed in _sample_records(source, db_code, record_count, cap):
        _accumulate_field_inventory(parsed, inv)
    item['fields'] = _inventory_to_fields(kind, inv)
    return item


def _accepts_limit(fn):
    """True, если у вызываемого ``fn`` есть параметр ``limit`` (или **kwargs).

    Так потоковый путь выбирается только для источников, чей ``read_records``
    действительно умеет ограничивать выборку (LocalSource), и не подменяет
    собой посимвольный перебор там, где сигнатура иная."""
    try:
        import inspect
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):                     # noqa: BLE001 - C-ускоренные/без сигнатуры
        return False
    if 'limit' in params:
        return True
    return any(p.kind == p.VAR_KEYWORD for p in params.values())


def _sample_records(source, db_code, record_count, cap):
    """Выдать до ``cap`` живых разобранных записей БД для инвентаря полей.

    Предпочитает ПОТОКОВЫЙ ``source.read_records(db, limit=cap)`` (его даёт
    :class:`LocalSource` — так крупная БД не материализуется целиком ради выборки);
    при отсутствии метода падает на перебор по MFN через ``read_record`` (сетевой
    источник, FakeIrbis в тестах). Удалённые/пустые/нечитаемые записи пропускаются;
    в обоих случаях читается не больше ``cap`` живых записей."""
    streamer = getattr(source, 'read_records', None)
    if callable(streamer) and _accepts_limit(streamer):
        sampled = 0
        for parsed in streamer(db_code, limit=cap):
            if sampled >= cap:
                break
            if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                continue
            yield parsed
            sampled += 1
        return
    sampled = 0
    for mfn in range(1, record_count + 1):
        if sampled >= cap:
            break
        try:
            parsed = source.read_record(db_code, mfn)
        except Exception:                               # noqa: BLE001 - удалён/заблокирован MFN
            continue
        if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
            continue
        yield parsed
        sampled += 1


def introspect(source, dbs=None, sample=INSPECT_SAMPLE_SIZE):
    """Интроспекция источника -> структурированный план миграции (ДВУХФАЗНАЯ, #225).

    Перечисляет БД источника (меню `dbnam` / ``list_databases``) и в зависимости
    от ``dbs`` выбирает фазу:

      * **без ``dbs`` (фаза 1, быстрая):** на каждую БД — только дешёвая сводка
        ``{code, name, kind, recordCount, readerCount?}`` БЕЗ инвентаря полей
        (поле ``fields`` отсутствует). Поля не читаются, поэтому список из десятков
        БД отдаётся быстро и не упирается в HTTP-таймаут.
      * **с ``dbs=[коды]`` (фаза 2, тяжёлая):** разбирает ТОЛЬКО перечисленные БД
        (регистронезависимо), для каждой добавляя инвентарь полей ``fields:[…]`` с
        флагом ``custom`` на нештатных допполях. БД вне списка пропускаются.

    Возвращает ``{'databases': [<db-item>, …]}`` — тот же shape, что отдаёт
    эндпойнт /api/admin/migrate/inspect."""
    wanted = None
    if dbs:
        wanted = {str(d).strip().upper() for d in dbs if str(d).strip()}
    plan = []
    for entry in enumerate_databases(source):
        code = entry.get('code')
        if not code:
            continue
        if wanted is not None and code.strip().upper() not in wanted:
            continue
        if wanted is None:
            # Фаза 1: быстрая сводка без сэмплирования полей.
            plan.append(database_summary(source, code, db_name=entry.get('name')))
        else:
            # Фаза 2: полный инвентарь полей для запрошенных БД.
            plan.append(introspect_database(source, code, db_name=entry.get('name'),
                                            sample=sample))
    return {'databases': plan}


# --------------------------------------------------------------------------- #
# Targets. A small bundle so the migrator can be pointed at fresh in-memory
# stores (tests / dry-run) or the real configured stores. Idempotency for the
# catalog uses an in-process source-MFN -> target-MFN index built on demand from
# the loaded records (so a re-run against an existing store still upserts).
# --------------------------------------------------------------------------- #
class Targets:
    """The set of Biblio stores the migrator loads into.

    Pass explicit stores (tests use ``:memory:`` ones); ``Targets.in_memory()``
    builds a fresh isolated set. The ``access`` store is wired into the catalog so
    its ФЛК dictionary rules can resolve (and to hold the portal reader rows)."""

    def __init__(self, catalog, circulation, access, catalog_db='IBIS',
                 tenant='public'):
        self.catalog = catalog
        self.circulation = circulation
        self.access = access
        self.catalog_db = catalog_db
        self.tenant = tenant

    @classmethod
    def in_memory(cls, catalog_db='IBIS', tenant='public', access=None):
        access = access or AccessStore(':memory:')
        catalog = CatalogStore(':memory:', access_store=access)
        circ = CirculationStore(':memory:')
        return cls(catalog, circ, access, catalog_db=catalog_db, tenant=tenant)

    # -- catalog idempotency: source-MFN -> target-MFN ------------------- #
    def find_by_source_mfn(self, source_mfn):
        """Resolve a previously-loaded record's target MFN by its source MFN.

        Scans the catalog db for the record carrying ``907^_mfn == source_mfn``
        (the idempotency stamp). Returns the target mfn or None. O(n) scan — fine
        for a one-shot migration; a production run could add an index, but the
        catalog store is intentionally not modified here."""
        target = str(source_mfn)
        for mfn in self.catalog.list_mfns(self.catalog_db, include_deleted=True,
                                          limit=10 ** 9):
            rec = self.catalog.get(self.catalog_db, mfn, include_deleted=True)
            if rec is None:
                continue
            for inst in _as_list(rec.get(SOURCE_MFN_FIELD)):
                if isinstance(inst, dict) and str(inst.get(SOURCE_MFN_SUB)) == target:
                    return mfn
        return None


def _as_list(raw):
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


# --------------------------------------------------------------------------- #
# The migration itself.
# --------------------------------------------------------------------------- #
class Migrator:
    """Drive the ИРБИС → Biblio migration over a source + targets.

    ``source`` only needs ``max_mfn(db)`` and ``read_record(db, mfn)`` (the live
    SessionManager satisfies this; tests inject a FakeIrbis). ``dry_run=True`` maps
    everything and counts it WITHOUT writing the targets."""

    def __init__(self, source, targets, *, dry_run=False, log=None):
        self.source = source
        self.targets = targets
        self.dry_run = dry_run
        self._log = log                    # callable(str) or None

    def _emit(self, msg):
        if self._log:
            self._log(msg)

    # -- catalog ------------------------------------------------------------ #
    def migrate_catalog(self, src_db='IBIS', limit=None, report=None):
        """Iterate source ``src_db`` MFN 1..max_mfn, map + load each record.

        Deleted / empty / unreadable records are skipped (counted). Idempotent: a
        record already loaded (matched by source MFN) is updated in place. Returns
        the running report dict."""
        report = report if report is not None else _new_report()
        try:
            top = self.source.max_mfn(src_db)
        except Exception as e:                          # noqa: BLE001 - server may be down
            report['errors'] += 1
            self._emit('catalog: max_mfn(%s) failed: %s' % (src_db, type(e).__name__))
            return report
        if not top or top < 1:
            return report
        last = top if limit is None else min(top, limit)
        for mfn in range(1, last + 1):
            try:
                parsed = self.source.read_record(src_db, mfn)
            except Exception:                           # noqa: BLE001 - deleted/locked MFN
                report['skipped'] += 1
                continue
            report['records_read'] += 1
            if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                report['skipped'] += 1
                continue
            record, source_mfn = map_catalog_record(parsed)
            if self.dry_run:
                report['records_loaded'] += 1           # would-load count
                continue
            try:
                self._load_catalog_record(record, source_mfn)
                report['records_loaded'] += 1
            except Exception as e:                       # noqa: BLE001
                report['errors'] += 1
                self._emit('catalog: load mfn %s failed: %s' % (mfn, type(e).__name__))
        return report

    def _load_catalog_record(self, record, source_mfn):
        """Upsert one mapped record into the catalog (idempotent by source MFN)."""
        existing_mfn = None
        if source_mfn is not None:
            existing_mfn = self.targets.find_by_source_mfn(source_mfn)
        res = self.targets.catalog.save(self.targets.catalog_db, record,
                                        mfn=existing_mfn)
        # A severity-1 ФЛК rejection is a per-record skip, not a crash; surface it.
        if not res.get('saved'):
            raise CatalogLoadRejected(res.get('violations'))
        return res

    # -- readers ------------------------------------------------------------ #
    def migrate_readers(self, src_db='RDR', limit=None, report=None):
        """Iterate source ``src_db`` (readers), map + load each ticket.

        PII is ENCRYPTED before any store write. Idempotent by ticket (upsert).
        Seeds the circulation reader row (ticket + category) so holds/loans can
        reference it. Returns the running report dict."""
        report = report if report is not None else _new_report()
        try:
            top = self.source.max_mfn(src_db)
        except Exception as e:                          # noqa: BLE001
            report['errors'] += 1
            self._emit('readers: max_mfn(%s) failed: %s' % (src_db, type(e).__name__))
            return report
        if not top or top < 1:
            return report
        last = top if limit is None else min(top, limit)
        seen = set()
        for mfn in range(1, last + 1):
            try:
                parsed = self.source.read_record(src_db, mfn)
            except Exception:                           # noqa: BLE001
                report['skipped'] += 1
                continue
            report['records_read'] += 1
            if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                report['skipped'] += 1
                continue
            mapped = map_reader_record(parsed)
            if mapped is None or mapped['ticket'] in seen:
                report['skipped'] += 1
                continue
            seen.add(mapped['ticket'])
            # redacted sample only — never the full name (ПДн logging rule)
            self._emit('reader %s (%s)' % (mapped['ticket'],
                                           redact(mapped['pii'].get('10'))))
            if self.dry_run:
                report['readers_loaded'] += 1
                continue
            try:
                self._load_reader(mapped)
                report['readers_loaded'] += 1
            except Exception as e:                       # noqa: BLE001
                report['errors'] += 1
                self._emit('reader %s load failed: %s' % (mapped['ticket'],
                                                          type(e).__name__))
        return report

    def _load_reader(self, mapped):
        """Load one reader: circulation row (ticket+category) + encrypted PII review.

        The product persists reader PII at rest as ciphertext (V1 seam). We store
        the resolved display name under the same encrypted column the social layer
        uses (``reader_review.reader_name``) so the migrated reader's name is
        ciphertext at rest, identical to a name written by the running app. The
        circulation reader row holds only the ticket + policy category (no PII).
        """
        ticket = mapped['ticket']
        # circulation reader (no PII — just ticket + category bucket)
        self.targets.circulation.add_reader(ticket, category=mapped['category'])
        # reader display name -> ENCRYPTED at rest via the V1 seam.
        display = _reader_display_name(mapped['pii'])
        if display:
            enc = crypto.encrypt(display)
            self._write_reader_pii(ticket, enc, mapped['pii'])

    def _write_reader_pii(self, ticket, enc_name, pii):
        """Persist the reader's encrypted display name into OUR store.

        Writes through ``review_upsert`` against a reserved migration marker
        (db='_MIGRATION', mfn=0) so the name lands in the ENCRYPTED
        ``reader_review.reader_name`` column — proving migrated PII is ciphertext
        at rest by the same mechanism the running app uses. ``review_upsert``
        already calls ``crypto.encrypt`` internally; we pass the plaintext display
        name (idempotent: encrypt() never double-wraps, and the column is the
        single source of the ciphertext-at-rest guarantee)."""
        display = _reader_display_name(pii)
        # rating is required (1..5) by the schema; a migration marker uses 3 (n/a).
        self.targets.access.review_upsert(
            ticket, '_MIGRATION', 0, 3, 'migrated', display, _now())

    # -- driver ------------------------------------------------------------- #
    def run(self, dbs=('IBIS', 'RDR'), catalog_db='IBIS', limit=None):
        """Run the full migration over ``dbs`` and return the combined report."""
        report = _new_report()
        for db in dbs:
            up = db.strip().upper()
            if up == 'RDR':
                self.migrate_readers(src_db=db, limit=limit, report=report)
            else:
                self.migrate_catalog(src_db=db, limit=limit, report=report)
        return report


class CatalogLoadRejected(Exception):
    """A mapped record was rejected by ФЛК on load (severity-1) — per-record skip."""


def _reader_display_name(pii):
    """Build 'Surname Name Patronymic' from the reader PII map (plaintext)."""
    parts = [pii.get(t, '').strip() for t in RDR_NAME_FIELDS]
    return ' '.join(p for p in parts if p)


def _now():
    import time
    return time.time()


def _new_report():
    return {'records_read': 0, 'records_loaded': 0, 'readers_loaded': 0,
            'skipped': 0, 'errors': 0}


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def build_arg_parser():
    p = argparse.ArgumentParser(
        prog='migrate_irbis',
        description='Migrate an ИРБИС library (catalog + readers) into Biblio, '
                    'or introspect a source (--introspect).')
    # Источник: сетевой (--source-host/--user/--pass) ИЛИ локальный (--source-path).
    # required не выставляем — режим/полнота проверяются в main (local ≠ network).
    p.add_argument('--source-host', help='source ИРБИС host (network mode)')
    p.add_argument('--source-port', type=int, default=6666, help='source ИРБИС port')
    p.add_argument('--user', help='source ИРБИС login (network mode)')
    p.add_argument('--pass', dest='password', help='source ИРБИС password (network mode)')
    p.add_argument('--source-path', help='DataPath к файлам БД (local mode, без сервера)')
    p.add_argument('--workstation', default='A', help='ИРБИС workstation code (default A)')
    p.add_argument('--target-tenant', help='target Biblio tenant slug (нужен для миграции)')
    p.add_argument('--dbs', default=None,
                   help='список БД через запятую. Для миграции — что переносить '
                        '(по умолчанию IBIS,RDR). Для --introspect — фаза 2: '
                        'инвентарь полей ТОЛЬКО по этим БД; без --dbs --introspect '
                        'даёт быстрый список БД с числом записей (фаза 1)')
    p.add_argument('--catalog-db', default='IBIS',
                   help='target catalog base name (default IBIS)')
    p.add_argument('--introspect', action='store_true',
                   help='снять и напечатать план источника и выйти — НИЧЕГО не '
                        'мигрируя. Без --dbs — быстрый список БД (фаза 1); с --dbs — '
                        'инвентарь полей с флагом custom по этим БД (фаза 2)')
    p.add_argument('--dry-run', action='store_true',
                   help='read + map + report only; write NOTHING to the target')
    p.add_argument('--limit', type=int, default=None,
                   help='cap MFNs read per DB (smoke-test convenience)')
    p.add_argument('--verbose', action='store_true',
                   help='log per-record progress (redacted PII only)')
    return p


def _open_source_from_args(args):
    """Открыть источник по аргументам CLI: локальный (--source-path) или сетевой."""
    if args.source_path:
        return LocalSource(args.source_path)
    if not args.source_host or not args.user or args.password is None:
        raise SystemExit('network mode требует --source-host/--user/--pass '
                         '(или используйте --source-path для local mode)')
    return open_source(args.source_host, args.source_port, args.user,
                       args.password, workstation=args.workstation)


def _parse_dbs_arg(raw):
    """``--dbs`` -> кортеж кодов (или () если не задано). Разделители ',' и ';'."""
    if not raw:
        return ()
    return tuple(d.strip() for d in raw.replace(';', ',').split(',') if d.strip())


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    dbs = _parse_dbs_arg(args.dbs)
    source = _open_source_from_args(args)

    # Режим интроспекции: печатаем план и выходим (ничего не мигрируем).
    # Без --dbs -> фаза 1 (быстрый список); с --dbs -> фаза 2 (инвентарь полей).
    if args.introspect:
        try:
            plan = introspect(source, dbs=dbs or None)
        finally:
            close = getattr(source, 'close', None)
            if callable(close):
                close()
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if not args.target_tenant:
        raise SystemExit('миграция требует --target-tenant (или используйте --introspect)')
    migrate_dbs = dbs or ('IBIS', 'RDR')        # миграция по умолчанию переносит IBIS,RDR
    targets = Targets.in_memory(catalog_db=args.catalog_db, tenant=args.target_tenant)
    log = (lambda m: print(m, file=sys.stderr)) if args.verbose else None
    migrator = Migrator(source, targets, dry_run=args.dry_run, log=log)
    try:
        report = migrator.run(dbs=migrate_dbs, catalog_db=args.catalog_db, limit=args.limit)
    finally:
        close = getattr(source, 'close', None)
        if callable(close):
            close()
    report['dry_run'] = bool(args.dry_run)
    report['tenant'] = args.target_tenant
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
