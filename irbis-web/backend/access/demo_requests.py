#!/usr/bin/env python3
"""Заявки на демодоступ (issue #226) — СТОР.

Публичная страница продукта Biblio (`/product`) несёт форму-заявку на демодоступ.
Эта форма собирает ПДн заявителя (ФИО, e-mail, телефон, учреждение, должность) и
**обязательное согласие на обработку ПДн** (152-ФЗ, ст. 6/9). Заявки складываются
в собственный стор ``demo_request`` — отдельный от Access-стора и от живого ИРБИС
(тот же посыл изоляции, что и у circulation/notifications/holds, #222): на демо-
стенде реальных ПДн нет, а заявки правообладатель обрабатывает на публичной
странице с согласием и минимизацией (см. ``docs/deploy/DEMO_STAND.md`` §6/§7).

Соответствие 152-ФЗ:
  * **согласие обязательно** — ``add`` без ``consent=True`` поднимает
    ``ConsentRequired``; роут превращает это в 400 (заявка НЕ сохраняется);
  * **минимизация** — храним ровно пять заявленных полей формы + отметку согласия
    и время; ничего лишнего (ни IP, ни user-agent, ни cookie);
  * **листинг только под super-admin** — выдачу заявок (с ПДн) роут гейтит
    ``admin.db@admin`` (как соседние кросс-тенантные admin-поверхности).

Бэкенд-портируемость (ADR-004: sqlite dev / PostgreSQL prod). Как и Access-стор,
этот стор работает на ДВУХ бэкендах с одинаковой публичной поверхностью:
  * **sqlite** — дефолт (свой файл/`:memory:`), запускается без СУБД;
  * **postgres** — когда передан DSN (``postgresql://…``) или ``backend='postgres'``;
    DDL зеркалит sqlite-схему. psycopg импортируется лениво, поэтому модуль
    импортируется и на Python без драйвера (sqlite-путь).

Один публичный класс ``DemoRequestStore`` с ``add`` / ``list`` / ``count`` / ``get``.
"""
import json
import re
import threading
import time

# Заявка минимизирована до пяти полей формы (#226) + согласие/время. Ограничения
# длины — защита от мусора/переполнения, не бизнес-валидация.
MAX_LEN = 200
# Простая проверка e-mail: есть ровно один @, по бокам непустые части без пробелов.
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Схема стора. На sqlite — это DDL целиком; на PG — то же, с типами PG (см.
# ``_SCHEMA_PG``). Имена/семантика колонок одинаковы, чтобы accessors не ветвились.
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS demo_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name   TEXT NOT NULL,
  email       TEXT NOT NULL,
  phone       TEXT,
  institution TEXT,
  position    TEXT,
  consent     INTEGER NOT NULL DEFAULT 0,   -- 1 = согласие на обработку ПДн дано (152-ФЗ)
  created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS demo_request_created_idx ON demo_request(created_at DESC);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS demo_request (
  id BIGSERIAL PRIMARY KEY,
  full_name   TEXT NOT NULL,
  email       TEXT NOT NULL,
  phone       TEXT,
  institution TEXT,
  position    TEXT,
  consent     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS demo_request_created_idx ON demo_request(created_at DESC);
"""

# Поля формы, возвращаемые/принимаемые в стабильном порядке (минимизация —
# ничего сверх этого набора в стор не пишется).
FORM_FIELDS = ('full_name', 'email', 'phone', 'institution', 'position')


class ConsentRequired(Exception):
    """Заявка без согласия на обработку ПДн (152-ФЗ). Роут → 400, не сохраняем."""


class ValidationError(Exception):
    """Невалидная заявка (нет ФИО / нет или кривой e-mail). Роут → 400."""


def _clean(v):
    """Привести значение к обрезанной строке (None → '') и подрезать по MAX_LEN."""
    if v is None:
        return ''
    return str(v).strip()[:MAX_LEN]


def _is_pg(handle):
    """True, если ``handle`` — это PG DSN-строка (а не путь к sqlite-файлу)."""
    return isinstance(handle, str) and handle.startswith(('postgres://', 'postgresql://'))


class DemoRequestStore:
    """Стор заявок на демодоступ (#226). sqlite (дефолт) или PostgreSQL.

    Parameters
    ----------
    db_path : str
        ``':memory:'`` (дефолт) / путь к sqlite-файлу, ЛИБО PG DSN
        (``postgresql://…``). PG-путь выбирается автоматически по виду строки или
        явным ``backend='postgres'``.
    backend : str | None
        ``'sqlite'`` | ``'postgres'``. Если не задан — определяется по ``db_path``
        (DSN → postgres, иначе sqlite).
    """

    def __init__(self, db_path=':memory:', backend=None):
        self.db_path = db_path
        if backend is None:
            backend = 'postgres' if _is_pg(db_path) else 'sqlite'
        self.backend = backend
        self._local = threading.local()
        self.ensure_schema()

    # ---- connection (thread-local; autocommit/per-op commit, house style) ---- #
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
        """Плейсхолдер параметра для текущего бэкенда (sqlite '?' / PG '%s')."""
        return '%s' if self.backend == 'postgres' else '?'

    def ensure_schema(self):
        c = self._conn()
        if self.backend == 'postgres':
            c.execute(_SCHEMA_PG)
        else:
            c.executescript(SCHEMA_SQLITE)
            c.commit()

    # ---- validation ------------------------------------------------------- #
    @staticmethod
    def _validate(full_name, email):
        """ФИО обязательно; e-mail обязателен и должен быть похож на e-mail."""
        if not full_name:
            raise ValidationError('ФИО обязательно')
        if not email:
            raise ValidationError('E-mail обязателен')
        if not _EMAIL_RE.match(email):
            raise ValidationError('Некорректный e-mail')

    # ---- write ------------------------------------------------------------ #
    def add(self, full_name, email, phone='', institution='', position='',
            consent=False, now=None):
        """Сохранить заявку на демодоступ. Возвращает ``{'id', ...}``.

        Согласие на обработку ПДн ОБЯЗАТЕЛЬНО (152-ФЗ): ``consent`` ложно →
        ``ConsentRequired`` и НИЧЕГО не пишем. ФИО и e-mail валидируются
        (``ValidationError``). Хранится ровно набор ``FORM_FIELDS`` + согласие +
        время — минимизация.
        """
        full_name = _clean(full_name)
        email = _clean(email)
        phone = _clean(phone)
        institution = _clean(institution)
        position = _clean(position)
        self._validate(full_name, email)
        if not consent:
            # Согласие — предусловие обработки: проверяем ПОСЛЕ формальной
            # валидации, но строго ДО записи, чтобы без согласия в сторе пусто.
            raise ConsentRequired('требуется согласие на обработку персональных данных')
        ts = float(now if now is not None else time.time())
        c = self._conn()
        ph = self._ph
        sql = ('INSERT INTO demo_request'
               '(full_name,email,phone,institution,position,consent,created_at) '
               'VALUES(%s,%s,%s,%s,%s,%s,%s)'
               % (ph, ph, ph, ph, ph, ph, ph))
        consent_val = True if self.backend == 'postgres' else 1
        if self.backend == 'postgres':
            row = c.execute(sql + ' RETURNING id',
                            (full_name, email, phone, institution, position,
                             consent_val, ts)).fetchone()
            new_id = row['id']
        else:
            cur = c.execute(sql, (full_name, email, phone, institution,
                                  position, consent_val, ts))
            c.commit()
            new_id = cur.lastrowid
        return {'id': new_id, 'full_name': full_name, 'email': email,
                'phone': phone, 'institution': institution, 'position': position,
                'consent': True, 'created_at': ts}

    # ---- read (super-admin only at the route layer) ----------------------- #
    @staticmethod
    def _view(r):
        """Нормализовать строку к бэкенд-независимому виду заявки."""
        return {
            'id': r['id'],
            'fullName': r['full_name'],
            'email': r['email'],
            'phone': r['phone'] or '',
            'institution': r['institution'] or '',
            'position': r['position'] or '',
            'consent': bool(r['consent']),
            'createdAt': float(r['created_at']),
        }

    def list(self, limit=100):
        """Заявки, новейшие первыми, не больше ``limit`` (для super-admin листинга)."""
        limit = max(1, min(1000, int(limit)))
        ph = self._ph
        rows = self._conn().execute(
            'SELECT * FROM demo_request ORDER BY created_at DESC, id DESC '
            'LIMIT %s' % ph, (limit,)).fetchall()
        return [self._view(dict(r)) for r in rows]

    def get(self, request_id):
        """Одна заявка по id, или None."""
        ph = self._ph
        r = self._conn().execute(
            'SELECT * FROM demo_request WHERE id=%s' % ph,
            (int(request_id),)).fetchone()
        return self._view(dict(r)) if r else None

    def count(self):
        """Сколько заявок в сторе (для метрик/тестов)."""
        r = self._conn().execute(
            'SELECT COUNT(*) AS n FROM demo_request').fetchone()
        return int(dict(r)['n'])
