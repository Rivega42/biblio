#!/usr/bin/env python3
"""RIGHT — типовые права доступа к полным текстам (кластер 7, рёбра 7.2/7.3).

Серверная БД ИРБИС64 ``RIGHT`` хранит **типовые шаблоны правил** доступа к полным
текстам (ПТ). Каждая запись = один шаблон, опознаваемый по ``v1`` (идентификатор).
Запись-ресурс в БД-источнике (IBIS/SK/VKR) ссылается на шаблон полем **955^B**
(``I=`` template id). Уровень доступа выводится алгоритмом ``right_ft.pft`` из
депозитария — здесь он воспроизведён как чистая доменная логика.

Источники (только факты из конфигов):
  * ``docs/recon/deep/reference/databases/DB_SERVICE.md`` §1 (структура поля 3,
    меню 3A/3C/3G, алгоритм ``Deposit\\right_ft.pft``);
  * ``docs/design/INTEGRATION_MAP.md`` кластер 7 (рёбра 7.2/7.3/7.4/7.5);
  * ``docs/recon/deep/FINDINGS_09_web_reader.md`` (web-читатель, гейтинг ПТ).

Модель данных (зеркало серверной структуры RIGHT):
  * шаблон = ``{'id', 'period', 'rules', 'description'}``;
  * ``period`` = общий период действия (``{'start','end'}``, ГГГГММДД), поле v2 (^D/^E);
  * ``rules`` = повторения поля v3, каждое: ``{'category','value','level',
    'limit','unit','start','end'}`` —
      - ``category`` = ^A: ``01`` идентификатор читателя · ``02`` категория ·
        ``03`` IP · ``04`` домен · ``05`` факультет · ``06`` семестр · ``07`` спец.;
      - ``value``    = ^B: значение элемента доступа (для ^A=02 — код категории по 50.mnu);
      - ``level``    = ^C: ``0`` запрет · ``1`` постраничный просмотр · ``2`` скачивание;
      - ``limit``    = ^F: количественное ограничение (число; для ^G='' — страницы);
      - ``unit``     = ^G: '' страницы · ``1`` проценты;
      - ``start``/``end`` = ^D/^E: период правила (по умолчанию — даты общего периода).

Алгоритм ``access_level`` (по ``Deposit\\right_ft.pft``, DB_SERVICE §1):
  1. Пустой/отсутствующий шаблон (955^B пусто) → ``download`` («полный доступ»).
  2. Загружается шаблон. Общий период: start=v2^D|``00000101``, end=v2^E|``99990101``.
  3. Нет правил → ``download``, если текущая дата в [start..end], иначе ``deny``.
  4. Есть правила → по каждому повторению, чьё ^A совпадает с проверяемым измерением
     (здесь — категория читателя ^A=02) и чьё значение ^B = категории читателя,
     с действующим периодом правила, копится разрешённый уровень ^C.
  5. Итог = **максимальный** разрешённый уровень среди совпавших правил
     (``g10``: 0→deny, 1→view, 2→download). Нет совпадений → ``deny``.

Метод ``access_level(reader_category, right_template)`` — чистая функция (без I/O).
Резолв 955^B → id шаблона делает ``RightService`` через опциональный catalog-handle
(``get(db, mfn)``); без handle — back-compat: шаблон передаётся напрямую/по id из стора.

Бэкенд-портируемость (ADR-004: sqlite dev / PostgreSQL prod) — ``RightStore``
работает на ДВУХ бэкендах с одинаковой поверхностью (как ``demo_requests.py``):
sqlite по умолчанию (свой файл/``:memory:``), postgres по DSN; DDL зеркалит схему,
psycopg импортируется лениво.
"""
import json
import threading
import time

# --- Уровни доступа (контракт наружу) --------------------------------------- #
# Совпадают по смыслу с 3C.mnu: 0 Запрет / 1 Постраничный просмотр / 2 Скачивание.
DENY = 'deny'
VIEW = 'view'
DOWNLOAD = 'download'

# Код права доступа ^C (3C.mnu) → уровень. Любое иное/пустое значение → DENY
# (консервативно: неизвестное правило не открывает доступ).
_LEVEL_BY_CODE = {'0': DENY, '1': VIEW, '2': DOWNLOAD}
# Уровень → код ^C и числовой ранг (для выбора максимума, как ``g10`` в right_ft.pft).
_RANK = {DENY: 0, VIEW: 1, DOWNLOAD: 2}
_LEVEL_BY_RANK = {0: DENY, 1: VIEW, 2: DOWNLOAD}

# Категории элемента доступа ^A (3A.mnu).
CAT_READER_ID = '01'   # идентификатор читателя (RDR v30)
CAT_READER_KAT = '02'  # категория читателя (50.mnu) ← основное измерение гейтинга
CAT_IP = '03'          # IP-адрес клиента
CAT_DOMAIN = '04'      # доменное имя клиента
CAT_FACULTY = '05'     # факультет (fak.mnu)
CAT_SEMESTER = '06'    # семестр
CAT_SPECIALITY = '07'  # специальность (spec.mnu)

# Границы общего периода по умолчанию (как в right_ft.pft: g4/g5).
_PERIOD_MIN = '00000101'
_PERIOD_MAX = '99990101'


def _norm_date(v, default):
    """Нормализовать дату ГГГГММДД к строке для лексикографического сравнения.
    Пусто/None → ``default``. Сравнение дат-строк ГГГГММДД корректно лексикографически."""
    s = ('' if v is None else str(v)).strip()
    return s if s else default


def _level_from_code(code):
    """Код ^C → уровень доступа. Неизвестный/пустой код → DENY (консервативно)."""
    return _LEVEL_BY_CODE.get(('' if code is None else str(code)).strip(), DENY)


def _today():
    """Текущая дата ГГГГММДД (как ``&uf('3')`` в right_ft.pft)."""
    return time.strftime('%Y%m%d')


def access_level(reader_category, right_template, *, today=None):
    """Вычислить уровень доступа читателя к ПТ по шаблону прав RIGHT.

    Чистая функция (ребро 7.2/7.3): воспроизводит ``Deposit\\right_ft.pft``.

    Parameters
    ----------
    reader_category : str | int | None
        Категория читателя (поле RDR 50; код по ``50.mnu``). Сверяется с ^B правил
        категории (^A=02). None/'' → правила категории не совпадают.
    right_template : dict | None
        Шаблон прав ``{'period','rules',...}`` (как из ``RightStore.get`` /
        ``RightService.template_for``). **None / пустой** ⇒ 955^B пусто ⇒ ``download``
        (полный доступ — п.1 алгоритма).
    today : str | None
        Дата ГГГГММДД для проверки периода (по умолчанию — системная). Инъекция
        ради детерминизма тестов.

    Returns
    -------
    str
        ``deny`` | ``view`` | ``download`` — максимальный разрешённый уровень.
    """
    # п.1: нет шаблона (955^B пусто) → полный доступ.
    if not right_template:
        return DOWNLOAD

    today = _today() if today is None else str(today)
    period = right_template.get('period') or {}
    g_start = _norm_date(period.get('start'), _PERIOD_MIN)
    g_end = _norm_date(period.get('end'), _PERIOD_MAX)
    rules = right_template.get('rules') or []

    # п.3: правил нет → download, если дата в общем периоде, иначе deny.
    if not rules:
        return DOWNLOAD if (g_start <= today <= g_end) else DENY

    cat = ('' if reader_category is None else str(reader_category)).strip()
    best = -1  # ранг лучшего совпавшего уровня; -1 = совпадений ещё нет
    for rule in rules:
        if (rule.get('category') or '').strip() != CAT_READER_KAT:
            continue  # здесь оцениваем измерение «категория читателя» (^A=02)
        # Значение элемента доступа ^B = код категории, к которой применимо правило.
        rule_val = ('' if rule.get('value') is None else str(rule.get('value'))).strip()
        if rule_val != cat:
            continue
        # Период правила (^D/^E); по умолчанию — границы общего периода (как в pft).
        r_start = _norm_date(rule.get('start'), g_start)
        r_end = _norm_date(rule.get('end'), g_end)
        if not (r_start <= today <= r_end):
            continue
        rank = _RANK[_level_from_code(rule.get('level'))]
        if rank > best:
            best = rank

    # п.5: нет совпавших правил → deny; иначе — максимальный разрешённый уровень.
    return _LEVEL_BY_RANK[best] if best >= 0 else DENY


def page_limit(reader_category, right_template, *, today=None):
    """Лимит страниц ^F для читателя по шаблону (ребро 7.3/7.5).

    Возвращает максимальный ``^F`` среди совпавших правил категории, разрешающих
    хотя бы просмотр (уровень ≠ deny). ``None`` ⇒ ограничение не задано (без лимита):
      * пустой шаблон / нет правил (полный доступ);
      * совпавшие правила без числового ^F.
    Правила в процентах (^G='1') здесь НЕ дают постраничного лимита (возвращают None
    по своей ветке) — кол-вая семантика квоты считается в страницах (LICH v4).
    """
    if not right_template:
        return None
    rules = right_template.get('rules') or []
    if not rules:
        return None

    today = _today() if today is None else str(today)
    period = right_template.get('period') or {}
    g_start = _norm_date(period.get('start'), _PERIOD_MIN)
    g_end = _norm_date(period.get('end'), _PERIOD_MAX)
    cat = ('' if reader_category is None else str(reader_category)).strip()

    limit = None
    for rule in rules:
        if (rule.get('category') or '').strip() != CAT_READER_KAT:
            continue
        rule_val = ('' if rule.get('value') is None else str(rule.get('value'))).strip()
        if rule_val != cat:
            continue
        r_start = _norm_date(rule.get('start'), g_start)
        r_end = _norm_date(rule.get('end'), g_end)
        if not (r_start <= today <= r_end):
            continue
        if _level_from_code(rule.get('level')) == DENY:
            continue  # запрет лимит страниц не несёт
        # ^G='1' → проценты, не страницы: постраничный лимит не задаём.
        if ('' if rule.get('unit') is None else str(rule.get('unit'))).strip() == '1':
            continue
        raw = rule.get('limit')
        if raw is None or str(raw).strip() == '':
            continue
        try:
            n = int(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if n < 0:
            continue
        limit = n if limit is None else max(limit, n)
    return limit


# --------------------------------------------------------------------------- #
# Хранилище шаблонов RIGHT (sqlite dev / PostgreSQL prod), своя схема.
# --------------------------------------------------------------------------- #
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS right_template (
  id          TEXT PRIMARY KEY,          -- v1: идентификатор шаблона (955^B ссылается сюда)
  period_json TEXT NOT NULL DEFAULT '{}',-- v2: общий период {start,end} (ГГГГММДД)
  rules_json  TEXT NOT NULL DEFAULT '[]',-- v3 (повторения): правила доступа
  description TEXT NOT NULL DEFAULT '',   -- v4: описание/название шаблона
  updated_at  REAL NOT NULL
);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS right_template (
  id          TEXT PRIMARY KEY,
  period_json TEXT NOT NULL DEFAULT '{}',
  rules_json  TEXT NOT NULL DEFAULT '[]',
  description TEXT NOT NULL DEFAULT '',
  updated_at  DOUBLE PRECISION NOT NULL
);
"""

# Подполя правила в их каноническом порядке (зеркало 3.wss).
RULE_SUBFIELDS = ('category', 'value', 'level', 'limit', 'unit', 'start', 'end')


def _is_pg(handle):
    """True, если ``handle`` — PG DSN-строка (а не путь к sqlite-файлу)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


def _clean_rule(rule):
    """Нормализовать одно правило к стабильному dict с ключами RULE_SUBFIELDS.

    Принимает либо «плоский» dict (``{'category':..., 'level':...}``), либо запись
    в стиле подполей (``{'A':..., 'C':...}``). Значения приводятся к строкам
    (числа/None терпимо). Возвращает dict ровно с ключами RULE_SUBFIELDS."""
    # Алиасы подполей серверной записи поля 3 → канонические ключи.
    aliases = {'a': 'category', 'b': 'value', 'c': 'level',
               'f': 'limit', 'g': 'unit', 'd': 'start', 'e': 'end'}
    out = {k: '' for k in RULE_SUBFIELDS}
    for key, val in (rule or {}).items():
        k = str(key).strip()
        canon = aliases.get(k.lower(), k if k in RULE_SUBFIELDS else None)
        if canon is None:
            continue
        out[canon] = '' if val is None else str(val).strip()
    return out


class RightStore:
    """Стор шаблонов прав RIGHT (sqlite по умолчанию / PostgreSQL по DSN).

    Поверхность: ``upsert`` / ``get`` / ``list`` / ``delete`` / ``count``.
    Записи опознаются по строковому ``id`` (на него ссылается каталожное 955^B).

    Parameters
    ----------
    db_path : str
        ``':memory:'`` (дефолт) / путь к sqlite-файлу, ЛИБО PG DSN (``postgresql://…``).
    backend : str | None
        ``'sqlite'`` | ``'postgres'``; если не задан — по виду ``db_path``.
    """

    def __init__(self, db_path=':memory:', backend=None):
        self.db_path = db_path
        if backend is None:
            backend = 'postgres' if _is_pg(db_path) else 'sqlite'
        self.backend = backend
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is not None and not getattr(c, 'closed', False):
            return c
        if self.backend == 'postgres':
            import psycopg
            from psycopg.rows import dict_row
            c = psycopg.connect(self.db_path, row_factory=dict_row, autocommit=True)
        else:
            import sqlite3
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
        self._local.conn = c
        return c

    @property
    def _ph(self):
        return '%s' if self.backend == 'postgres' else '?'

    def ensure_schema(self):
        c = self._conn()
        if self.backend == 'postgres':
            c.execute(_SCHEMA_PG)
        else:
            c.executescript(SCHEMA_SQLITE)
            c.commit()

    # ---- запись ----------------------------------------------------------- #
    def upsert(self, template_id, period=None, rules=None, description='', now=None):
        """Создать/обновить шаблон прав по строковому ``template_id``.

        ``period`` = ``{'start','end'}`` (ГГГГММДД, любое отсутствующее → '');
        ``rules`` = список правил (каждое нормализуется ``_clean_rule``). Возвращает
        нормализованный шаблон (как ``get``)."""
        tid = str(template_id).strip()
        if not tid:
            raise ValueError('template_id обязателен')
        period = period or {}
        period_norm = {'start': _norm_date(period.get('start'), ''),
                       'end': _norm_date(period.get('end'), '')}
        rules_norm = [_clean_rule(r) for r in (rules or [])]
        ts = float(now if now is not None else time.time())
        c = self._conn()
        ph = self._ph
        pj = json.dumps(period_norm, ensure_ascii=False)
        rj = json.dumps(rules_norm, ensure_ascii=False)
        if self.backend == 'postgres':
            c.execute(
                'INSERT INTO right_template(id,period_json,rules_json,description,updated_at) '
                'VALUES(%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET '
                'period_json=EXCLUDED.period_json, rules_json=EXCLUDED.rules_json, '
                'description=EXCLUDED.description, updated_at=EXCLUDED.updated_at',
                (tid, pj, rj, description or '', ts))
        else:
            c.execute(
                'INSERT INTO right_template(id,period_json,rules_json,description,updated_at) '
                'VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                'period_json=excluded.period_json, rules_json=excluded.rules_json, '
                'description=excluded.description, updated_at=excluded.updated_at',
                (tid, pj, rj, description or '', ts))
            c.commit()
        return {'id': tid, 'period': period_norm, 'rules': rules_norm,
                'description': description or ''}

    # ---- чтение ----------------------------------------------------------- #
    @staticmethod
    def _view(r):
        return {
            'id': r['id'],
            'period': json.loads(r['period_json'] or '{}'),
            'rules': json.loads(r['rules_json'] or '[]'),
            'description': r['description'] or '',
        }

    def get(self, template_id):
        """Шаблон по id (нормализованный dict), либо None."""
        tid = str(template_id).strip()
        if not tid:
            return None
        ph = self._ph
        r = self._conn().execute(
            'SELECT * FROM right_template WHERE id=%s' % ph, (tid,)).fetchone()
        return self._view(dict(r)) if r else None

    def list(self, limit=200):
        limit = max(1, min(2000, int(limit)))
        ph = self._ph
        rows = self._conn().execute(
            'SELECT * FROM right_template ORDER BY id LIMIT %s' % ph, (limit,)).fetchall()
        return [self._view(dict(r)) for r in rows]

    def delete(self, template_id):
        """Удалить шаблон. True, если строка была удалена."""
        tid = str(template_id).strip()
        if not tid:
            return False
        ph = self._ph
        c = self._conn()
        cur = c.execute('DELETE FROM right_template WHERE id=%s' % ph, (tid,))
        if self.backend != 'postgres':
            c.commit()
            return cur.rowcount > 0
        return getattr(cur, 'rowcount', 0) > 0

    def count(self):
        r = self._conn().execute(
            'SELECT COUNT(*) AS n FROM right_template').fetchone()
        return int(dict(r)['n'])


class RightService:
    """Гейтинг доступа к ПТ по правам читателя (рёбра 7.2/7.3).

    Связывает каталожную запись-ресурс (через поле **955^B**) с шаблоном RIGHT и
    выдаёт уровень доступа по категории читателя. Чистая доменная логика над
    стором + одним опциональным catalog-handle (как holds/social):

    Parameters
    ----------
    store : RightStore | None
        Стор шаблонов прав. ``None`` допустимо, если шаблоны передаются вызовами
        напрямую (``access_for(..., template=...)``) — тогда стор не нужен.
    catalog : object | None
        Каталог-handle с ``get(db, mfn) -> record`` (``access.catalog.CatalogStore``).
        По нему резолвится 955^B → id шаблона. ``None`` ⇒ back-compat без handle:
        955^B не читается из каталога (id шаблона передаётся явно).
    now : callable
        Часы (``time.time`` по умолчанию) — здесь используется только дата ГГГГММДД.
    """

    def __init__(self, store=None, catalog=None, now=None):
        self.store = store
        self.catalog = catalog
        if now is None:
            now = time.time
        self._now = now

    def _today(self):
        try:
            return time.strftime('%Y%m%d', time.localtime(self._now()))
        except Exception:
            return _today()

    # ---- резолв 955^B → id шаблона (ребро 7.2) ---------------------------- #
    def template_id_for_record(self, db, mfn):
        """Прочитать 955^B каталожной записи через handle → id шаблона прав.

        Возвращает строку-id или ``None`` (нет handle / нет записи / 955^B пусто).
        Никогда не бросает наружу seam-ошибку (деградирует к None — полный доступ)."""
        if self.catalog is None:
            return None
        try:
            rec = self.catalog.get(db, mfn)
        except Exception:
            return None
        return self._extract_955b(rec)

    @staticmethod
    def _extract_955b(record):
        """Достать первое непустое 955^B из записи (поле 955 — повторяющееся).

        Запись — dict {тег: инстанс|список}, инстанс — str|{подполе:значение}.
        Подполя читаются регистронезависимо (b/B). Целое поле (str) ^B не несёт."""
        if not record:
            return None
        raw = record.get('955')
        if raw is None:
            return None
        insts = raw if isinstance(raw, list) else [raw]
        for inst in insts:
            if isinstance(inst, dict):
                val = inst.get('b') or inst.get('B')
                if val is not None and str(val).strip():
                    return str(val).strip()
        return None

    # ---- разрешение шаблона ----------------------------------------------- #
    def template_for(self, *, db=None, mfn=None, template_id=None, template=None):
        """Разрешить шаблон прав из доступных входов (в порядке приоритета).

        1. ``template`` (готовый dict) — отдаётся как есть;
        2. ``template_id`` — берётся из стора;
        3. ``db``+``mfn`` — резолв 955^B через handle, затем стор.
        Возвращает шаблон-dict или ``None`` (955^B пусто / шаблон не найден →
        вызывающий трактует как полный доступ)."""
        if template is not None:
            return template
        tid = template_id
        if tid is None and db is not None and mfn is not None:
            tid = self.template_id_for_record(db, mfn)
        if tid is None:
            return None
        if self.store is None:
            return None
        return self.store.get(tid)

    # ---- основной контракт (ребро 7.3) ------------------------------------ #
    def access_level(self, reader_category, *, db=None, mfn=None,
                     template_id=None, template=None):
        """Уровень доступа читателя к ПТ: ``deny`` | ``view`` | ``download``.

        Шаблон разрешается ``template_for`` (по записи/id/готовому dict). Пустой
        шаблон (955^B пусто или не найден) ⇒ ``download`` (полный доступ, п.1)."""
        tmpl = self.template_for(db=db, mfn=mfn, template_id=template_id,
                                 template=template)
        return access_level(reader_category, tmpl, today=self._today())

    def page_limit(self, reader_category, *, db=None, mfn=None,
                   template_id=None, template=None):
        """Лимит страниц ^F для читателя (None ⇒ без ограничения). Ребро 7.3/7.5."""
        tmpl = self.template_for(db=db, mfn=mfn, template_id=template_id,
                                 template=template)
        return page_limit(reader_category, tmpl, today=self._today())
