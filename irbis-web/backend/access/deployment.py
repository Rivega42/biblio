#!/usr/bin/env python3
"""DEPLOYMENT — режимы развёртывания Biblio (own-store, issue #335).

Две независимые оси конфигурации, которые задают, ЧЕМ Biblio выступает в
конкретной инсталляции и ГДЕ он работает:

  * **ось замены** (``mode``) — что именно Biblio замещает: остаётся надстройкой
    над живым ИРБИС (заменяя только jirbis-портал), заменяет сервер ИРБИС,
    заменяет и ИРБИС, и jirbis, либо разворачивается полностью самостоятельно;
  * **ось топологии** (``topology``) — где крутится инсталляция: облако/SaaS или
    on-prem в самой библиотеке.

Выбор режима ДРАЙВИТ остальное: какие внешние подключения обязательны
(``required_connections``) и какой стартовый набор функциональных модулей
включён (``default_modules``). Это ось онбординг-визарда: оператор выбирает
режим+топологию, а Biblio детерминированно выводит из них требования и
дефолты.

Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей — в точности как ``config_store.py``/``pay.py``. Состояние
изолировано по ``tenant`` (одна инсталляция — один режим).

Модель
------
  * таблица ``deployment`` — одна строка на ``tenant`` (PRIMARY KEY);
  * ``mode`` — ключ из :data:`REPLACEMENT_MODES`;
  * ``topology`` — ключ из :data:`TOPOLOGIES`;
  * неназначенный тенант разрешается в дефолты (:data:`DEFAULT_MODE` /
    :data:`DEFAULT_TOPOLOGY`) с флагом ``configured=False``.

``DeploymentStore`` — низкоуровневый стор (upsert + чтение + список).
``DeploymentService`` — глубина: валидация режима/топологии, разрешение
тенанта в полный профиль (мета режима + обязательные подключения + дефолтные
модули), каталог для визарда.
"""
import sqlite3
import threading
from datetime import datetime, timezone

# Оси режимов: ключи функциональных модулей Biblio (паритет с access-каталогом).
# Полный набор из 8 модулей — то, что включает «Полная» инсталляция.
_ALL_MODULES = ['opac', 'reader', 'cataloging', 'circulation',
                'acquisition', 'bookprovision', 'admin', 'analytics']

# Ось «что заменяет»: упорядоченный список метаданных режимов замены.
# Порядок важен — это порядок предъявления в онбординг-визарде (по нарастанию
# самостоятельности Biblio относительно ИРБИС).
REPLACEMENT_MODES = [
    {
        'key': 'overlay_jirbis',
        'title': 'Надстройка над ИРБИС (замена только jirbis)',
        'needs_irbis': True,
        'needs_jirbis': True,
        'description': 'Biblio работает поверх живого ИРБИС, заменяя только '
                       'веб-портал jirbis.',
    },
    {
        'key': 'replace_irbis',
        'title': 'Замена ИРБИС',
        'needs_irbis': True,
        'needs_jirbis': False,
        'description': 'Biblio замещает сервер ИРБИС, сохраняя совместимость по '
                       'данным.',
    },
    {
        'key': 'replace_both',
        'title': 'Замена ИРБИС и jirbis',
        'needs_irbis': True,
        'needs_jirbis': True,
        'description': 'Biblio замещает и сервер ИРБИС, и портал jirbis.',
    },
    {
        'key': 'full',
        'title': 'Полная',
        'needs_irbis': False,
        'needs_jirbis': False,
        'description': 'Полностью самостоятельная инсталляция Biblio без ИРБИС.',
    },
]

# Ось «где работает»: упорядоченный список топологий развёртывания.
TOPOLOGIES = [
    {'key': 'cloud', 'title': 'Облако / SaaS'},
    {'key': 'onprem', 'title': 'On-prem в библиотеке'},
]

# Дефолты неназначенного тенанта (см. DeploymentService.resolve).
DEFAULT_MODE = 'overlay_jirbis'
DEFAULT_TOPOLOGY = 'cloud'

# Индекс ключ->мета режима (внутренний, для быстрого поиска).
_MODE_BY_KEY = {m['key']: m for m in REPLACEMENT_MODES}
# Множество допустимых ключей топологий.
_TOPOLOGY_KEYS = {t['key'] for t in TOPOLOGIES}

# Стартовый набор функциональных модулей по режиму замены.
# overlay_jirbis — минимум читательского фасада (каталог/кабинет/админ),
# тяжёлый бэк-офис остаётся в живом ИРБИС;
# replace_irbis — добавляются каталогизация/обслуживание/аналитика;
# replace_both — то же + комплектование и книгообеспеченность;
# full — все 8 модулей.
_DEFAULT_MODULES = {
    'overlay_jirbis': ['opac', 'reader', 'admin'],
    'replace_irbis': ['opac', 'reader', 'cataloging', 'circulation',
                      'admin', 'analytics'],
    'replace_both': ['opac', 'reader', 'cataloging', 'circulation',
                     'admin', 'analytics', 'acquisition', 'bookprovision'],
    'full': list(_ALL_MODULES),
}


def _utcnow():
    """Текущее время в ISO8601 (UTC, без микросекунд). Инжектируется как ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS deployment (
  tenant     TEXT PRIMARY KEY,
  mode       TEXT NOT NULL,
  topology   TEXT NOT NULL,
  updated_at TEXT
);
"""


def mode_meta(key):
    """Метаданные режима замены по ключу или ``None``, если ключ неизвестен."""
    return _MODE_BY_KEY.get(key)


def required_connections(mode):
    """Список обязательных внешних подключений для режима замены.

    ``'irbis'`` — если режим требует живой сервер ИРБИС (``needs_irbis``);
    ``'jirbis'`` — если режим требует портал jirbis (``needs_jirbis``).
    ``inforost`` сюда НЕ добавляется автоматически. Неизвестный режим -> ``[]``.
    """
    meta = _MODE_BY_KEY.get(mode)
    if meta is None:
        return []
    out = []
    if meta['needs_irbis']:
        out.append('irbis')
    if meta['needs_jirbis']:
        out.append('jirbis')
    return out


def default_modules(mode):
    """Стартовый набор функциональных модулей для режима замены (копия списка).

    Неизвестный режим -> ``[]``.
    """
    return list(_DEFAULT_MODULES.get(mode, []))


class DeploymentStore:
    """Собственный sqlite-стор режима развёртывания (одна строка на ``tenant``).

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

    def set(self, tenant, mode, topology):
        """Завести/обновить (upsert по ``tenant``) режим+топологию развёртывания.

        Возвращает сохранённую строку-dict. Валидации значений здесь НЕТ — она
        живёт в :class:`DeploymentService`; стор пишет, что дали.
        """
        now = self._now()
        c = self._conn()
        existing = self.get(tenant)
        if existing is None:
            c.execute(
                'INSERT INTO deployment(tenant,mode,topology,updated_at) '
                'VALUES(?,?,?,?)',
                (tenant, mode, topology, now))
        else:
            c.execute(
                'UPDATE deployment SET mode=?,topology=?,updated_at=? '
                'WHERE tenant=?',
                (mode, topology, now, tenant))
        c.commit()
        return self.get(tenant)

    def get(self, tenant):
        """Строка-dict режима тенанта или ``None``, если не назначен."""
        row = self._conn().execute(
            'SELECT * FROM deployment WHERE tenant=?', (tenant,)).fetchone()
        return dict(row) if row else None

    def list(self):
        """Список строк-dict всех назначенных тенантов (по имени тенанта)."""
        rows = self._conn().execute(
            'SELECT * FROM deployment ORDER BY tenant').fetchall()
        return [dict(r) for r in rows]


class DeploymentService:
    """Глубина над :class:`DeploymentStore`: валидация и разрешение профиля.

    Делегирует запись/чтение стору; добавляет проверку ключей и вывод
    производных требований (подключения, дефолтные модули) для онбординга.
    """

    def __init__(self, store=None, now=None):
        self.store = store or DeploymentStore(':memory:', now=now)

    def set(self, tenant, mode, topology):
        """Назначить тенанту режим+топологию с ВАЛИДАЦИЕЙ ключей.

        ``mode`` должен быть ключом из :data:`REPLACEMENT_MODES`, ``topology`` —
        из :data:`TOPOLOGIES`, иначе ``ValueError``. Возвращает сохранённую
        строку-dict.
        """
        if mode not in _MODE_BY_KEY:
            raise ValueError('неизвестный режим развёртывания: %r' % (mode,))
        if topology not in _TOPOLOGY_KEYS:
            raise ValueError('неизвестная топология: %r' % (topology,))
        return self.store.set(tenant, mode, topology)

    def resolve(self, tenant):
        """Полный профиль развёртывания тенанта (с дефолтами при отсутствии).

        Если тенант не назначен — режим/топология берутся из :data:`DEFAULT_MODE`
        / :data:`DEFAULT_TOPOLOGY`, а ``configured=False``. Возвращает dict:
        ``tenant``, ``mode``, ``topology``, ``mode_meta``,
        ``required_connections``, ``default_modules``, ``configured``.
        """
        row = self.store.get(tenant)
        if row is None:
            mode = DEFAULT_MODE
            topology = DEFAULT_TOPOLOGY
            configured = False
        else:
            mode = row['mode']
            topology = row['topology']
            configured = True
        return {
            'tenant': tenant,
            'mode': mode,
            'topology': topology,
            'mode_meta': mode_meta(mode),
            'required_connections': required_connections(mode),
            'default_modules': default_modules(mode),
            'configured': configured,
        }

    def catalog(self):
        """Каталог для онбординг-визарда: доступные режимы и топологии."""
        return {'modes': REPLACEMENT_MODES, 'topologies': TOPOLOGIES}
