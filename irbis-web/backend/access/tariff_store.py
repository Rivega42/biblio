#!/usr/bin/env python3
"""TARIFF STORE — редактируемые тарифы для матрицы доступов (own-store, issue #331).

Закрывает разрыв «редактирование тарифов»: тот слой биллинговой матрицы, который
раньше был ЗАШИТ в коде (статичная access-матрица), здесь сделан **редактируемым**
и **разделённым по тенантам** (per-tenant assignment). Чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в точности как
``config_store.py``/``pay.py``. Никаких live-ИРБИС-записей.

Зачем
-----
Тариф — это КОЛОНКА в админ-таблице тарифов: набор «ячеек» по строкам каталога
(разделы/функции). Раньше эти ячейки были статичны; здесь администратор может
их редактировать. Стор НАМЕРЕННО не знает каталог разделов/функций — он хранит
ячейки по СТРОКОВЫМ ключам ``item_key``; связку ключей с каталогом делает
родитель (вызывающий код). Тариф назначается тенанту (``tenant_tariff``), а сверх
тарифа тенант может докупать пакеты ресурсов à-la-carte (``tenant_addon``).

Модель (4 таблицы)
------------------
  * ``tariff`` — тариф (колонка таблицы); ``name`` уникален;
  * ``tariff_entry`` — ячейка тарифа: ``included`` (вкл/выкл, хранится 0/1),
    ``value`` (число-лимит или ``NULL`` = без значения/безлимит),
    ``enforcement`` (``'block'`` | ``'grace'``); уникальна в паре
    ``(tariff_id, item_key)``;
  * ``tenant_tariff`` — назначение тарифа тенанту (1:1 по тенанту);
  * ``tenant_addon`` — à-la-carte покупки пакетов (напр. OCR-страницы):
    ``packs`` штук по ``pack_size`` единиц.

Контракты значений
------------------
  * ``included`` хранится как ``0/1``, наружу отдаётся как ``bool``;
  * ``value`` ``NULL`` <-> ``None``;
  * :meth:`TariffStore.set_entry` — UPSERT с PARTIAL-семантикой: параметры,
    переданные как ``None``, НЕ затирают уже сохранённые поля (при первом создании
    действуют дефолты ``included=1``, ``value=NULL``, ``enforcement='block'``).
"""
import sqlite3
import threading
from datetime import datetime, timezone

# Допустимые режимы принуждения для ячейки.
ENFORCE_BLOCK = 'block'
ENFORCE_GRACE = 'grace'


def _utcnow():
    """Текущее время в ISO8601 (UTC, без микросекунд). Инжектируется как ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS tariff (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE,     -- машинное имя тарифа (колонка матрицы)
  title       TEXT NOT NULL DEFAULT '', -- человекочитаемый заголовок
  sort        INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT,
  updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS tariff_entry (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tariff_id   INTEGER NOT NULL,
  item_key    TEXT NOT NULL,            -- строковый ключ строки каталога
  included    INTEGER NOT NULL DEFAULT 1,   -- bool 0/1: ячейка включена
  value       INTEGER,                 -- число-лимит или NULL (без значения)
  enforcement TEXT NOT NULL DEFAULT 'block', -- block | grace
  updated_at  TEXT,
  UNIQUE(tariff_id, item_key)
);
CREATE INDEX IF NOT EXISTS tariff_entry_tariff_idx
  ON tariff_entry(tariff_id, item_key);
CREATE TABLE IF NOT EXISTS tenant_tariff (
  tenant       TEXT PRIMARY KEY,
  tariff_name  TEXT NOT NULL,
  updated_at   TEXT
);
CREATE TABLE IF NOT EXISTS tenant_addon (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant      TEXT NOT NULL,
  resource    TEXT NOT NULL,           -- ресурс пакета (напр. 'ocr_pages')
  packs       INTEGER NOT NULL,        -- сколько пакетов куплено
  pack_size   INTEGER NOT NULL,        -- единиц в одном пакете
  created_at  TEXT,
  UNIQUE(tenant, resource, pack_size)
);
CREATE INDEX IF NOT EXISTS tenant_addon_tenant_idx
  ON tenant_addon(tenant, resource);
"""


class TariffStore:
    """Собственный sqlite-стор редактируемых тарифов матрицы доступов.

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain dict. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601 без микросекунд) для детерминизма в тестах.

    Стор НЕ знает каталог разделов/функций: ячейки адресуются строковым
    ``item_key`` (связку с каталогом делает вызывающий код).
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

    # -- тарифы -------------------------------------------------------------

    def _tariff_row(self, name):
        """Сырая строка таблицы ``tariff`` (sqlite3.Row) по имени или ``None``."""
        return self._conn().execute(
            'SELECT * FROM tariff WHERE name=?', (name,)).fetchone()

    def create_tariff(self, name, title='', sort=0):
        """Завести тариф. Возвращает сохранённую строку-dict.

        Дубликат ``name`` приводит к ``sqlite3.IntegrityError`` (UNIQUE) —
        ловит вызывающий код, здесь НЕ оборачивается.
        """
        now = self._now()
        c = self._conn()
        c.execute(
            'INSERT INTO tariff(name,title,sort,created_at,updated_at) '
            'VALUES(?,?,?,?,?)',
            (name, title, sort, now, now))
        c.commit()
        return dict(self._tariff_row(name))

    def get_tariff(self, name):
        """Строка-dict тарифа по имени или ``None``."""
        row = self._tariff_row(name)
        return dict(row) if row else None

    def list_tariffs(self):
        """Список строк-dict всех тарифов (по ``sort``, затем ``name``)."""
        rows = self._conn().execute(
            'SELECT * FROM tariff ORDER BY sort, name').fetchall()
        return [dict(r) for r in rows]

    def update_tariff(self, name, title=None, sort=None):
        """Обновить заголовок/порядок тарифа (partial). ``None`` поля не меняет.

        Возвращает обновлённую строку-dict или ``None``, если тарифа нет.
        """
        row = self._tariff_row(name)
        if row is None:
            return None
        new_title = row['title'] if title is None else title
        new_sort = row['sort'] if sort is None else sort
        c = self._conn()
        c.execute(
            'UPDATE tariff SET title=?,sort=?,updated_at=? WHERE name=?',
            (new_title, new_sort, self._now(), name))
        c.commit()
        return dict(self._tariff_row(name))

    def delete_tariff(self, name):
        """Удалить тариф и каскадно его ячейки. ``True`` — если был удалён.

        Назначения тенантам (``tenant_tariff``) НЕ трогаются намеренно.
        """
        row = self._tariff_row(name)
        if row is None:
            return False
        c = self._conn()
        c.execute('DELETE FROM tariff_entry WHERE tariff_id=?', (row['id'],))
        c.execute('DELETE FROM tariff WHERE id=?', (row['id'],))
        c.commit()
        return True

    # -- ячейки тарифа ------------------------------------------------------

    def _entry_row(self, tariff_id, item_key):
        """Сырая строка ``tariff_entry`` (sqlite3.Row) или ``None``."""
        return self._conn().execute(
            'SELECT * FROM tariff_entry WHERE tariff_id=? AND item_key=?',
            (tariff_id, item_key)).fetchone()

    @staticmethod
    def _entry_to_dict(row):
        """Преобразовать строку ячейки в dict: ``included`` -> bool, value <-> None."""
        return {
            'included': bool(row['included']),
            'value': row['value'],
            'enforcement': row['enforcement'],
        }

    def set_entry(self, tariff_name, item_key, included=None, value=None,
                  enforcement=None):
        """UPSERT ячейки тарифа по ``(tariff, item_key)`` с PARTIAL-семантикой.

        Параметры, переданные как ``None``, НЕ затирают уже сохранённые поля.
        При ПЕРВОМ создании действуют дефолты ``included=1``, ``value=NULL``,
        ``enforcement='block'``. Неизвестный ``tariff_name`` -> ``ValueError``.

        Возвращает dict ячейки: ``{'included': bool, 'value': int|None,
        'enforcement': str}``.
        """
        tariff = self._tariff_row(tariff_name)
        if tariff is None:
            raise ValueError('неизвестный тариф: %r' % (tariff_name,))
        tid = tariff['id']
        now = self._now()
        c = self._conn()
        existing = self._entry_row(tid, item_key)
        if existing is None:
            # Дефолты при создании; None-параметры заменяются дефолтом.
            inc = 1 if included is None else (1 if included else 0)
            val = value  # None допустим (без значения / безлимит)
            enf = ENFORCE_BLOCK if enforcement is None else enforcement
            c.execute(
                'INSERT INTO tariff_entry(tariff_id,item_key,included,value,'
                'enforcement,updated_at) VALUES(?,?,?,?,?,?)',
                (tid, item_key, inc, val, enf, now))
        else:
            # PARTIAL: None-параметры сохраняют существующее значение.
            inc = existing['included'] if included is None else (1 if included else 0)
            val = existing['value'] if value is None else value
            enf = existing['enforcement'] if enforcement is None else enforcement
            c.execute(
                'UPDATE tariff_entry SET included=?,value=?,enforcement=?,'
                'updated_at=? WHERE tariff_id=? AND item_key=?',
                (inc, val, enf, now, tid, item_key))
        c.commit()
        return self._entry_to_dict(self._entry_row(tid, item_key))

    def get_entries(self, tariff_name):
        """Все ячейки тарифа -> ``{item_key: {'included','value','enforcement'}}``.

        Неизвестный тариф (или тариф без ячеек) -> пустой dict.
        """
        tariff = self._tariff_row(tariff_name)
        if tariff is None:
            return {}
        rows = self._conn().execute(
            'SELECT * FROM tariff_entry WHERE tariff_id=? ORDER BY item_key',
            (tariff['id'],)).fetchall()
        return {r['item_key']: self._entry_to_dict(r) for r in rows}

    def get_entry(self, tariff_name, item_key):
        """Одна ячейка-dict ``{'included','value','enforcement'}`` или ``None``."""
        tariff = self._tariff_row(tariff_name)
        if tariff is None:
            return None
        row = self._entry_row(tariff['id'], item_key)
        return self._entry_to_dict(row) if row else None

    def remove_entry(self, tariff_name, item_key):
        """Удалить ячейку тарифа. ``True`` — если строка была удалена, иначе ``False``."""
        tariff = self._tariff_row(tariff_name)
        if tariff is None:
            return False
        c = self._conn()
        cur = c.execute(
            'DELETE FROM tariff_entry WHERE tariff_id=? AND item_key=?',
            (tariff['id'], item_key))
        c.commit()
        return cur.rowcount > 0

    # -- назначение тарифа тенанту ------------------------------------------

    def assign_tenant(self, tenant, tariff_name):
        """Назначить тенанту тариф (upsert по ``tenant``). Возвращает строку-dict.

        Неизвестный ``tariff_name`` -> ``ValueError``.
        """
        if self._tariff_row(tariff_name) is None:
            raise ValueError('неизвестный тариф: %r' % (tariff_name,))
        now = self._now()
        c = self._conn()
        c.execute(
            'INSERT INTO tenant_tariff(tenant,tariff_name,updated_at) '
            'VALUES(?,?,?) ON CONFLICT(tenant) DO UPDATE SET '
            'tariff_name=excluded.tariff_name, updated_at=excluded.updated_at',
            (tenant, tariff_name, now))
        c.commit()
        row = self._conn().execute(
            'SELECT * FROM tenant_tariff WHERE tenant=?', (tenant,)).fetchone()
        return dict(row)

    def get_tenant_tariff(self, tenant):
        """Имя тарифа, назначенного тенанту, или ``None``."""
        row = self._conn().execute(
            'SELECT tariff_name FROM tenant_tariff WHERE tenant=?',
            (tenant,)).fetchone()
        return row['tariff_name'] if row else None

    # -- à-la-carte пакеты --------------------------------------------------

    def add_addon(self, tenant, resource, packs, pack_size):
        """Записать покупку пакетов ресурса à-la-carte. Возвращает строку-dict.

        Повторная покупка того же ``(tenant, resource, pack_size)`` суммирует
        число пакетов (upsert по уникальному ключу).
        """
        now = self._now()
        c = self._conn()
        c.execute(
            'INSERT INTO tenant_addon(tenant,resource,packs,pack_size,created_at) '
            'VALUES(?,?,?,?,?) ON CONFLICT(tenant,resource,pack_size) DO UPDATE '
            'SET packs=tenant_addon.packs+excluded.packs',
            (tenant, resource, packs, pack_size, now))
        c.commit()
        row = self._conn().execute(
            'SELECT * FROM tenant_addon WHERE tenant=? AND resource=? AND '
            'pack_size=?', (tenant, resource, pack_size)).fetchone()
        return dict(row)

    def addons_for(self, tenant):
        """Список строк-dict всех пакетов тенанта (по ресурсу, размеру пакета)."""
        rows = self._conn().execute(
            'SELECT * FROM tenant_addon WHERE tenant=? '
            'ORDER BY resource, pack_size', (tenant,)).fetchall()
        return [dict(r) for r in rows]

    def addon_units(self, tenant, resource):
        """Суммарное число единиц ресурса из пакетов (``packs*pack_size``), 0 если нет."""
        row = self._conn().execute(
            'SELECT COALESCE(SUM(packs*pack_size), 0) AS units FROM tenant_addon '
            'WHERE tenant=? AND resource=?', (tenant, resource)).fetchone()
        return int(row['units'])
