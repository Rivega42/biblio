#!/usr/bin/env python3
"""Representative SYSTEM vocabulary seed set (gap A5, epic #188).

Transcribed verbatim from the recon reference
``docs/recon/deep/reference/format/CONTROL_VOCABULARIES.{md,csv}`` — the
vendor-standard (DB=Deposit/RQST) ИРБИС control dictionaries that every tenant
must have for ФЛК-by-dictionary and code→label rendering to work.

This is a *first slice*, not the full 940-value catalog: a representative system
set that proves the seeding design end-to-end.

  * ``jz.mnu``           — languages (10, representative subset of 108)
  * ``str.mnu``          — countries (10, representative subset of 149)
  * ``vd.mnu``           — document types (10, representative subset of 54)
  * ``ste.mnu``          — exemplar statuses (14, FULL — drives circulation ws3)
  * ``reservstatus.mnu`` — reservation statuses (5, FULL — drives the hold shelf)

Institution-specific dictionaries are listed with ``kind='institution'`` and NO
values: they are created EMPTY at provision time and populated by the library
(import from source ИРБИС, or manual entry in the ws5 editor). See SPEC §2.3.

``SEED_VERSION`` is the global seed epoch; it stamps ``vocabulary.seed_version``
on every seeded row so a future ``reseed`` (SPEC §3.3) can three-way-merge.
"""

SEED_VERSION = 1

# --------------------------------------------------------------------------- #
# SYSTEM dictionaries: kind='system', populated with vendor-standard values.
# Each entry: name -> {title, field_hint, values: [(code, label), ...]}.
# Order of `values` is the seeded sort_order (0-based).
# --------------------------------------------------------------------------- #
SYSTEM_VOCABS = {
    'jz.mnu': {
        'title': 'Языки',
        'field_hint': '101/J=',
        'values': [
            ('rus', 'Русский'),
            ('eng', 'Английский'),
            ('ger', 'Немецкий'),
            ('fre', 'Французский'),
            ('spa', 'Испанский'),
            ('ita', 'Итальянский'),
            ('ukr', 'Украинский'),
            ('bel', 'Белорусский'),
            ('lat', 'Латинский'),
            ('ara', 'Арабский'),
        ],
    },
    'str.mnu': {
        'title': 'Страны',
        'field_hint': '102/C=',
        'values': [
            ('RU', 'Россия'),
            ('AU', 'Австралия'),
            ('AT', 'Австрия'),
            ('AZ', 'Азербайджан'),
            ('AM', 'Армения'),
            ('BY', 'Беларусь'),
            ('BE', 'Бельгия'),
            ('BG', 'Болгария'),
            ('GB', 'Великобритания'),
            ('DE', 'Германия'),
        ],
    },
    'vd.mnu': {
        'title': 'Вид документа',
        'field_hint': '900/V=',
        'values': [
            ('KN', 'Книги в целом'),
            ('05', 'Однотомное издание'),
            ('03', 'Многотомное издание'),
            ('04', 'Продолжающееся издание (ПРИ)'),
            ('07', 'Монографическая серия (МС)'),
            ('01', 'Газета (общее описание)'),
            ('02', 'Журнал (общее описание)'),
            ('NJ', 'Отдельный номер газеты или журнала'),
            ('FT', 'Документы с полным текстом'),
            ('EXT', 'Документ с внешним объектом'),
        ],
    },
    # FULL (14) — drives circulation (ws3). Codes are case-sensitive ИРБИС codes.
    'ste.mnu': {
        'title': 'Статусы экземпляра',
        'field_hint': '910^A',
        'values': [
            ('0', 'Для ЭК - отдельный экземпляр, поступил по месту хранения'),
            ('R', 'Для ЭК - группа экз-ров. Размножение с вводом инвентарных номеров'),
            ('U', 'Для ЭК ВУЗа - группа экз-ров (Безинв.учет). Размножения не требуется'),
            ('C', 'Группа экземпляров для библиотеки сети. Размножения не требуется'),
            ('E', 'Сетевой локальный ресурс'),
            ('8', 'Номер журнала/газеты поступил, но еще не дошел до места хранения'),
            ('2', 'Отдельный экземпляр в библиотеку еще не поступал, ожидается'),
            ('3', 'В переплете'),
            ('4', 'Утерян'),
            ('5', 'Временно не выдается'),
            ('6', 'Списан'),
            ('p', 'Номер журнала/газеты переплетен (входит в "подшивку")'),
            ('1', 'Выдан читателю'),
            ('9', 'На бронеполке'),
        ],
    },
    # FULL (5) — drives the hold shelf (ws3 бронеполка).
    'reservstatus.mnu': {
        'title': 'Статусы брони',
        'field_hint': 'RQST 910^A',
        'values': [
            ('0', 'отправлен с места хранения на место выдачи'),
            ('1', 'получен с места хранения/находится по месту выдачи/предназначен для выдачи читателю'),
            ('2', 'получен от читателя/находится по месту выдачи/предназначен для выдачи читателю'),
            ('3', 'получен от читателя/находится по месту выдачи/предназначен для возврата по месту хранения'),
            ('4', 'отправлен с места выдачи на место хранения'),
        ],
    },
}

# --------------------------------------------------------------------------- #
# INSTITUTION dictionaries: kind='institution', seeded EMPTY (seed_version=NULL).
# Created so the tenant has the metadata row + a field hint; the library fills
# the values (import from source ИРБИС §2.3, or the ws5 editor). `kv.mnu` empty
# is the literal onboarding blocker this engine unblocks.
# --------------------------------------------------------------------------- #
INSTITUTION_VOCABS = {
    'kv.mnu': {'title': 'Места обслуживания / выдачи (МВ)', 'field_hint': 'RQST'},
    'mhr.mnu': {'title': 'Места хранения (МХ)', 'field_hint': '910^D'},
}

# Institution-specific TREE dictionaries: created EMPTY (kind='institution').
INSTITUTION_TREES = {
    'spec.tre': {'title': 'Специальности (дерево)', 'field_hint': '—'},
}


def system_catalog_rows():
    """Rows for ``control.seed_catalog`` for the SYSTEM dictionaries.

    Yields (name, code, label, kind, seed_version, title, field_hint, sort).
    The catalog holds both the per-vocab metadata (carried on every value row's
    title/field_hint) and the value pairs — a flat master copy that
    ``seed_vocabularies`` reads to populate a tenant.
    """
    for name, spec in SYSTEM_VOCABS.items():
        for sort, (code, label) in enumerate(spec['values']):
            yield (name, code, label, 'system', SEED_VERSION,
                   spec['title'], spec['field_hint'], sort)


def all_vocab_meta():
    """All vocab metadata rows: (name, title, kind, field_hint, seed_version).

    System vocabs carry ``seed_version``; institution vocabs carry NULL.
    """
    for name, spec in SYSTEM_VOCABS.items():
        yield (name, spec['title'], 'system', spec['field_hint'], SEED_VERSION)
    for name, spec in INSTITUTION_VOCABS.items():
        yield (name, spec['title'], 'institution', spec['field_hint'], None)
