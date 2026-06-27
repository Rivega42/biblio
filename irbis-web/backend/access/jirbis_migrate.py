#!/usr/bin/env python3
"""J-IRBIS (Joomla `jirbis2`) -> Biblio own-store — migration-тулинг узла 4 cutover.

Преобразует строки Joomla-таблиц `jos_*` боевого J-IRBIS 2.5.28 в форму own-store
Biblio. **Чистая трансформация + план** (никаких сетевых/БД-записей здесь): на
вход — уже распарсенные строки (list[dict], как из `mysqldump`/CSV), на выход —
структурированный план миграции, который применяет вызывающий слой, когда дамп
`jirbis2` окажется на руках (он off-git, ПДн, 152-ФЗ — см.
`docs/cutover/JIRBIS_MYSQL_ACCESS_RESPONSE.md`, issue #310).

Почему так
----------
Сам дамп root-only off-git на pve (`/root/jirbis2-offgit/`) — недоступен из этого
окружения. Поэтому тулинг готовится и тестируется на синтетике, а реальный прогон
= «загрузить строки -> вызвать :func:`plan`/мапперы». Парсинг `mysqldump` -> строки
— отдельная граница (стандартный инструмент при наличии дампа); здесь работаем с
уже-строками.

Что переносим (из RESPONSE/#310)
--------------------------------
  * `jos_users` (~240) -> учётки own-store с **upgrade-on-login** (phpass `$P$` →
    при первом входе пере-хэш в нативный pbkdf2, #294; верификатор `access/phpass.py`);
  * `jos_content_rating` -> соц-рейтинги;
  * `jos_reservations` -> брони (own-store holds);
  * `jos_ai_chat_feedback` (InnoDB, ~0 строк на проде) -> `chat_message` (#293) —
    мапим схему, данных нет;
  * CMS (`jos_content`/`jos_menu`/`jos_modules`) -> отдельный CMS-перенос (тут только
    учитываем в сводке).

Балласт (НЕ переносим): `jos_jstats_*` (статистика, ~60МБ), `jos_session` (~13МБ).

Данные читателя (формуляр/выдачи/заказы) — в ИРБИС RDR/RQST, НЕ в Joomla: сверка
учётки `jos_users` ↔ читатель ИРБИС идёт по email/билету на слое применения.
"""
from access import phpass

# --------------------------------------------------------------------------- #
# Классификация таблиц дампа (что переносим / что балласт).
# --------------------------------------------------------------------------- #
MIGRATE_TABLES = {
    'jos_users': 'accounts',
    'jos_content_rating': 'ratings',
    'jos_reservations': 'reservations',
    'jos_ai_chat_feedback': 'chat',
}
CMS_TABLES = ('jos_content', 'jos_menu', 'jos_modules', 'jos_categories')
# Балласт: префиксы таблиц, которые НЕ переносим (статистика/сессии/кэш).
BALLAST_PREFIXES = ('jos_jstats', 'jos_session', 'jos_#__cache', 'jos_cache')


def classify_table(name):
    """Классифицировать таблицу дампа: ``migrate`` / ``cms`` / ``ballast`` / ``other``."""
    n = (name or '').lower()
    if n in MIGRATE_TABLES:
        return 'migrate'
    if n in CMS_TABLES:
        return 'cms'
    if any(n.startswith(p) for p in BALLAST_PREFIXES):
        return 'ballast'
    return 'other'


# --------------------------------------------------------------------------- #
# Классификация формата пароля -> стратегия переноса входа.
# --------------------------------------------------------------------------- #
def classify_password(stored):
    """Определить формат хэша пароля Joomla -> стратегия входа в Biblio.

    Возвращает ``(auth, needs_upgrade)``:
      * ``'phpass'``  — переносимый `$P$`/`$H$` (Joomla 2.5 дефолт) → upgrade-on-login
        (verify legacy → пере-хэш в нативный pbkdf2 при первом входе, #294);
      * ``'native'``  — уже наш pbkdf2 (мигрировать как есть, апгрейд не нужен);
      * ``'md5_salt'``/``'md5'`` — легаси Joomla < 1.6 (`md5:salt` / голый md5) →
        upgrade-on-login по тому же принципу, но через md5-ветку верификатора;
      * ``'other'``   — пусто/нераспознано → перенос без пароля, вход через сброс/ЕСИА.
    ``needs_upgrade`` True для всех легаси-форматов (всё, кроме native)."""
    s = stored if isinstance(stored, str) else ''
    if phpass.is_phpass(s):
        return 'phpass', True
    if s.startswith('pbkdf2'):
        return 'native', False
    body = s.split(':', 1)[0]
    if ':' in s and len(body) == 32 and _is_hex(body):
        return 'md5_salt', True
    if len(s) == 32 and _is_hex(s):
        return 'md5', True
    return 'other', True


def _is_hex(s):
    try:
        int(s, 16)
        return True
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------- #
# Мапперы строк Joomla -> own-store-форма.
# --------------------------------------------------------------------------- #
def map_user(row):
    """`jos_users` -> запись миграции учётки own-store.

    Поля Joomla: ``id``/``name``/``username``/``email``/``password``/``block``/
    ``registerDate``/``lastvisitDate``. Возвращает dict с легаси-хэшем (для
    upgrade-on-login) и стратегией входа; пароль НЕ расшифровывается."""
    pw = row.get('password') or ''
    auth, needs_upgrade = classify_password(pw)
    return {
        'source_id': row.get('id'),
        'login': (row.get('username') or '').strip(),
        'email': (row.get('email') or '').strip().lower(),
        'name': (row.get('name') or '').strip(),
        'legacy_hash': pw,            # ПДн: применяется off-git, в git не кладём
        'auth': auth,
        'needs_upgrade': needs_upgrade,
        'blocked': str(row.get('block', '0')) in ('1', 'true', 'True'),
        'registered_at': row.get('registerDate'),
    }


def map_rating(row):
    """`jos_content_rating` -> соц-рейтинг own-store (avg = sum/count)."""
    try:
        rsum = float(row.get('rating_sum') or 0)
        rcount = int(row.get('rating_count') or 0)
    except (TypeError, ValueError):
        rsum, rcount = 0.0, 0
    avg = round(rsum / rcount, 3) if rcount else 0.0
    return {'content_id': row.get('content_id'), 'sum': rsum,
            'count': rcount, 'avg': avg}


def map_reservation(row):
    """`jos_reservations` -> бронь own-store (поля Joomla варьируются — берём гибко)."""
    return {
        'source_id': row.get('id'),
        'reader': (row.get('user_id') or row.get('reader') or row.get('uid') or ''),
        'item': (row.get('item') or row.get('record') or row.get('mfn') or ''),
        'status': row.get('status') or row.get('state'),
        'created_at': row.get('created') or row.get('date'),
    }


def map_chat(row):
    """`jos_ai_chat_feedback` -> `chat_message` (#293). На проде 0 строк — мапим схему."""
    return {
        'user_message': row.get('user_message'),
        'assistant_content': row.get('assistant_content'),
        'tool_calls_json': row.get('tool_calls_json'),
        'rating': row.get('rating'),
        'deepthink': str(row.get('deepthink', '0')) in ('1', 'true', 'True'),
        'has_file': str(row.get('has_file', '0')) in ('1', 'true', 'True'),
    }


_MAPPERS = {
    'accounts': ('jos_users', map_user),
    'ratings': ('jos_content_rating', map_rating),
    'reservations': ('jos_reservations', map_reservation),
    'chat': ('jos_ai_chat_feedback', map_chat),
}


# --------------------------------------------------------------------------- #
# План миграции (dry-run): строки таблиц -> структурированный план + сводка.
# --------------------------------------------------------------------------- #
def plan(tables):
    """Построить план миграции из ``tables`` = ``{table_name: [row, …]}``.

    Возвращает план без побочных эффектов:

        {'accounts': [...], 'ratings': [...], 'reservations': [...], 'chat': [...],
         'auth_breakdown': {'phpass': N, 'native': N, 'md5_salt': N, 'md5': N, 'other': N},
         'cms': {table: rowcount}, 'ballast_skipped': {table: rowcount},
         'summary': {'accounts': N, 'needs_upgrade': N, 'ratings': N,
                     'reservations': N, 'chat': N, 'tables_seen': N}}

    Применение (создание учёток с легаси-хэшем для upgrade-on-login, перенос соц/
    броней/чата) — на слое, у которого есть дамп и доступ к own-store; здесь —
    только трансформация (testable без дампа). PII (legacy_hash/email) остаётся в
    плане в памяти, в git/лог не выносится."""
    out = {'accounts': [], 'ratings': [], 'reservations': [], 'chat': [],
           'auth_breakdown': {'phpass': 0, 'native': 0, 'md5_salt': 0,
                              'md5': 0, 'other': 0},
           'cms': {}, 'ballast_skipped': {}, 'summary': {}}
    for name, rows in (tables or {}).items():
        rows = rows or []
        kind = classify_table(name)
        if kind == 'ballast':
            out['ballast_skipped'][name] = len(rows)
            continue
        if kind == 'cms':
            out['cms'][name] = len(rows)
            continue
        if kind == 'migrate':
            bucket, mapper = _bucket_for(name)
            for r in rows:
                rec = mapper(r)
                out[bucket].append(rec)
                if bucket == 'accounts':
                    out['auth_breakdown'][rec['auth']] = \
                        out['auth_breakdown'].get(rec['auth'], 0) + 1
        # 'other' — неизвестная таблица: в сводку только числом
    out['summary'] = {
        'accounts': len(out['accounts']),
        'needs_upgrade': sum(1 for a in out['accounts'] if a['needs_upgrade']),
        'ratings': len(out['ratings']),
        'reservations': len(out['reservations']),
        'chat': len(out['chat']),
        'cms_tables': len(out['cms']),
        'ballast_tables': len(out['ballast_skipped']),
        'tables_seen': len(tables or {}),
    }
    return out


def _bucket_for(table):
    """Имя бакета плана + маппер для таблицы из :data:`MIGRATE_TABLES`."""
    bucket = MIGRATE_TABLES[table]
    _t, mapper = _MAPPERS[bucket]
    return bucket, mapper
