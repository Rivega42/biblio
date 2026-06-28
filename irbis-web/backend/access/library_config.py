#!/usr/bin/env python3
"""LIBRARY CONFIG — редактируемая конфигурация библиотеки per-tenant (own-store).

Закрывает разрыв «паспорт/реквизиты библиотеки»: тот набор полей, который во
фронтенде был **захардкожен** в ``tenantContent.ts`` (имя, логотип, реквизиты,
часы работы, текст «о библиотеке»), здесь сделан **редактируемыми ДАННЫМИ**,
разделёнными по тенантам (issue #335). Чистый stdlib + ``sqlite3`` (dev-паритет,
ADR-004), без сети и без новых pip-зависимостей — в точности как
``config_store.py``/``pay.py``. Никаких live-ИРБИС-записей.

Зачем
-----
Каждая библиотека-тенант должна сама править свой «паспорт»: название, полное
название, логотип, фирменный оттенок, юридические реквизиты, часы работы и
описание. Раньше эти значения жили константой в коде фронтенда — изменить их без
пересборки было нельзя. ``library_config`` — own-store такого слоя: одна строка
JSON на тенанта, форма всегда полная (недостающие ключи берутся из
:data:`DEFAULT_CONFIG`), правки — частичные и **глубокие** (вложенный
``requisites`` мёржится, а не затирается целиком).

Модель
------
  * таблица ``library_config`` — ключ — сам ``tenant`` (PRIMARY KEY);
  * ``data`` хранится текстом (JSON всей формы целиком);
  * сериализация — ``json.dumps(ensure_ascii=False, sort_keys=True)`` (кириллица
    хранится как есть), десериализация — ``json.loads``.

``LibraryConfigStore`` — низкоуровневый стор (upsert/get/список тенантов).
``LibraryConfigService`` — глубина: всегда полная форма, частичный глубокий
апдейт, публично-безопасный вид.
"""
import copy
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Дефолтная (полная) форма конфигурации библиотеки. Любой `get`/`update`
# возвращает форму, дополненную недостающими ключами отсюда. НЕ мутировать —
# наружу всегда отдаётся глубокая копия.
DEFAULT_CONFIG = {
    'name': '',
    'full_name': '',
    'logo_url': '',
    'tint': '',
    'requisites': {
        'inn': '',
        'ogrn': '',
        'kpp': '',
        'legal_address': '',
        'address': '',
        'phone': '',
        'email': '',
        'site': '',
    },
    'hours': '',
    'about': '',
}


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS library_config (
  tenant      TEXT PRIMARY KEY,
  data        TEXT NOT NULL,            -- JSON всей формы целиком
  updated_at  TEXT
);
"""


def _deep_merge(base, patch):
    """Глубоко слить ``patch`` в копию ``base`` (вложенные dict мёржатся).

    Возвращает НОВЫЙ dict: ``base`` и ``patch`` не мутируются. Для каждого ключа
    ``patch``: если в обоих лежит dict — рекурсивный merge; иначе значение из
    ``patch`` перезаписывает. Ключи, которых нет в ``patch``, берутся из ``base``.
    """
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if (key in out and isinstance(out[key], dict)
                and isinstance(value, dict)):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


class LibraryConfigStore:
    """Собственный sqlite-стор конфигурации библиотеки (одна JSON-строка/тенант).

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._now = now or _utcnow
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    def get(self, tenant):
        """Распарсенный JSON конфигурации тенанта (dict) или ``None``."""
        row = self._conn().execute(
            'SELECT data FROM library_config WHERE tenant=?',
            (tenant,)).fetchone()
        if row is None:
            return None
        return json.loads(row['data'])

    def set(self, tenant, data):
        """Записать (upsert по ``tenant``) форму ``data`` ЦЕЛИКОМ как JSON.

        ``data`` сериализуется в текст (``ensure_ascii=False``, кириллица как
        есть). Возвращает сохранённый dict (round-trip через стор).
        """
        text = json.dumps(data, ensure_ascii=False, sort_keys=True)
        now = self._now()
        c = self._conn()
        existing = self._conn().execute(
            'SELECT tenant FROM library_config WHERE tenant=?',
            (tenant,)).fetchone()
        if existing is None:
            c.execute(
                'INSERT INTO library_config(tenant,data,updated_at) '
                'VALUES(?,?,?)', (tenant, text, now))
        else:
            c.execute(
                'UPDATE library_config SET data=?,updated_at=? WHERE tenant=?',
                (text, now, tenant))
        c.commit()
        return self.get(tenant)

    def list_tenants(self):
        """Отсортированный список различных имён тенантов."""
        rows = self._conn().execute(
            'SELECT tenant FROM library_config ORDER BY tenant').fetchall()
        return [r['tenant'] for r in rows]


class LibraryConfigService:
    """Глубина над :class:`LibraryConfigStore`: всегда полная форма, частичный
    глубокий апдейт, публично-безопасный вид. Делегирует CRUD стору.
    """

    def __init__(self, store=None, now=None):
        self.store = store or LibraryConfigStore(':memory:', now=now)

    def get(self, tenant):
        """Полная форма конфигурации тенанта (всегда).

        Глубокий merge :data:`DEFAULT_CONFIG` с сохранённым: недостающие ключи
        берутся из дефолта (вложенный ``requisites`` тоже дополняется). Если для
        тенанта ничего не сохранено — глубокая копия :data:`DEFAULT_CONFIG`.
        """
        saved = self.store.get(tenant)
        if saved is None:
            return copy.deepcopy(DEFAULT_CONFIG)
        return _deep_merge(DEFAULT_CONFIG, saved)

    def update(self, tenant, patch):
        """Частичный ГЛУБОКИЙ апдейт конфигурации тенанта.

        ``patch`` мёржится в текущую полную форму: верхний уровень + вложенный
        dict ``requisites``. Переданные ключи перезаписывают, прочие сохраняются
        (в т.ч. остальные поля ``requisites`` — ``{'requisites':{'inn':...}}`` НЕ
        затирает ``requisites.email`` и т.п.). Возвращает полную форму.

        Валидация: ``patch`` должен быть dict, иначе ``ValueError``. Неизвестные
        верхнеуровневые ключи (которых нет в :data:`DEFAULT_CONFIG`) ИГНОРИРУЮТСЯ.
        """
        if not isinstance(patch, dict):
            raise ValueError('patch должен быть dict, получено: %r' % (patch,))
        # Отбрасываем неизвестные верхнеуровневые ключи.
        clean = {k: v for k, v in patch.items() if k in DEFAULT_CONFIG}
        current = self.get(tenant)
        merged = _deep_merge(current, clean)
        return self.store.set(tenant, merged)

    def public(self, tenant):
        """Публично-безопасный вид конфигурации (= :meth:`get`).

        Сейчас совпадает с полной формой; вынесено отдельной точкой на будущее —
        когда часть полей нужно будет скрывать из публичной выдачи.
        """
        return self.get(tenant)
