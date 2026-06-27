#!/usr/bin/env python3
"""DEBTORS — собственный реестр ЗАДОЛЖЕННОСТЕЙ и САНКЦИЙ АРМ Книговыдача.

Аналог санкционного слоя ИРБИС64 (просроченные/утерянные экземпляры, расчёт
пеней, блокировка читателя-должника), но own-store: чистый stdlib + ``sqlite3``
(dev-паритет, ADR-004), без сети и без новых pip-зависимостей — в точности как
``pay.py``/``reader_registry.py``/``circulation.py``.

Зачем отдельно от ``circulation.py``
------------------------------------
``circulation.py`` ведёт ВЫДАЧИ (loan-keyed): кто что взял, сроки, лимиты,
штраф НА ВЫДАЧЕ. **DEBTORS** — это самостоятельный санкционный РЕЕСТР
(reader-keyed): записи задолженностей (просрочка/утеря) с расчётом пеней по
календарю и блокировки читателей с эскалацией ``warn`` -> ``block``. Этот слой
НЕ трогает ``circulation.py``; книговыдача сможет опрашивать его позже
опциональным хендлом (как ``pay=``/``reader_registry=`` у ``CirculationEngine``),
например ``debtors.is_blocked(reader)`` перед выдачей.

Деньги — в КОПЕЙКАХ (целые ``int``), чтобы расчёт пеней был точным и без
плавающей запятой. Даты — ISO8601 (``YYYY-MM-DD``); даты-math через
``datetime.date`` (в модуле это допустимо).

Виды задолженности
------------------
  * ``overdue`` — просрочка возврата: ``amount = дни_просрочки * тариф_за_день``;
  * ``lost``    — утеря экземпляра: ``amount = стоимость замены``.

Эскалация блокировки (см. :meth:`DebtorsService.evaluate_block`)
---------------------------------------------------------------
Незакрытые (``unsettled``) долги читателя агрегируются; если сумма превышает
порог ИЛИ число долгов достигло порога — ставится ``block`` (полная блокировка
выдачи), иначе при наличии хоть одного долга — ``warn`` (предупреждение), а при
отсутствии долгов блокировка снимается.
"""
import sqlite3
import threading
from datetime import date, datetime, timezone

# Виды задолженности.
KIND_OVERDUE = 'overdue'
KIND_LOST = 'lost'
DEBT_KINDS = (KIND_OVERDUE, KIND_LOST)

# Уровни санкции читателя (эскалация).
LEVEL_WARN = 'warn'    # предупреждение (есть долг, но ниже порогов)
LEVEL_BLOCK = 'block'  # блокировка выдачи (порог превышен)
BLOCK_LEVELS = (LEVEL_WARN, LEVEL_BLOCK)


def _utcnow():
    """Текущий момент в ISO8601 (UTC) — дефолтный инжектируемый ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS debt (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  reader         TEXT NOT NULL,            -- RI= билет читателя-должника
  item           TEXT NOT NULL,            -- экземпляр (инв. номер / штрих-код)
  db             TEXT NOT NULL DEFAULT '*',-- БД каталога экземпляра
  due_date       TEXT,                     -- ISO срок возврата (для overdue)
  kind           TEXT NOT NULL,            -- overdue | lost
  amount_kopecks INTEGER NOT NULL DEFAULT 0,
  settled        INTEGER NOT NULL DEFAULT 0,-- 0 открыт / 1 погашен
  created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS debt_reader_idx ON debt(reader);
CREATE INDEX IF NOT EXISTS debt_settled_idx ON debt(settled);

CREATE TABLE IF NOT EXISTS reader_block (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  reader     TEXT NOT NULL UNIQUE,         -- один актуальный статус на читателя
  reason     TEXT,
  level      TEXT NOT NULL,                -- warn | block
  created_at TEXT NOT NULL
);
"""


class DebtStore:
    """Собственный sqlite-стор задолженностей и блокировок. ``:memory:`` или
    файл; create-on-init. Соединение thread-local (домашний стиль); строки — dict."""

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
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

    # -- задолженности --------------------------------------------------------

    def add_debt(self, reader, item, db, due_date, kind, amount_kopecks,
                 created_at):
        """Завести запись задолженности; возвращает строку-dict."""
        c = self._conn()
        cur = c.execute(
            'INSERT INTO debt(reader,item,db,due_date,kind,amount_kopecks,'
            'settled,created_at) VALUES(?,?,?,?,?,?,0,?)',
            (reader, item, db or '*', due_date, kind, int(amount_kopecks),
             created_at))
        c.commit()
        return self.get_debt(cur.lastrowid)

    def get_debt(self, debt_id):
        r = self._conn().execute(
            'SELECT * FROM debt WHERE id=?', (debt_id,)).fetchone()
        return dict(r) if r else None

    def settle_debt(self, debt_id):
        """Пометить долг погашенным; ``True`` если строка реально изменилась."""
        c = self._conn()
        cur = c.execute(
            'UPDATE debt SET settled=1 WHERE id=? AND settled=0', (debt_id,))
        c.commit()
        return cur.rowcount > 0

    def debts(self, reader=None, unsettled_only=False):
        """Список долгов (по читателю / только открытые), хронологически."""
        sql = 'SELECT * FROM debt'
        conds = []
        params = []
        if reader is not None:
            conds.append('reader=?')
            params.append(reader)
        if unsettled_only:
            conds.append('settled=0')
        if conds:
            sql += ' WHERE ' + ' AND '.join(conds)
        sql += ' ORDER BY id'
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def outstanding_total(self, reader):
        """Сумма (копеек) НЕпогашенных долгов читателя -> ``int``."""
        r = self._conn().execute(
            'SELECT COALESCE(SUM(amount_kopecks),0) AS s FROM debt '
            'WHERE reader=? AND settled=0', (reader,)).fetchone()
        return int(r['s'])

    # -- блокировки -----------------------------------------------------------

    def block_reader(self, reader, reason, level, created_at):
        """Идемпотентно поставить/обновить статус блокировки читателя (upsert
        по уникальному ``reader``). Возвращает строку-dict."""
        c = self._conn()
        c.execute(
            'INSERT INTO reader_block(reader,reason,level,created_at) '
            'VALUES(?,?,?,?) ON CONFLICT(reader) DO UPDATE SET '
            'reason=excluded.reason, level=excluded.level, '
            'created_at=excluded.created_at',
            (reader, reason, level, created_at))
        c.commit()
        return self.get_block(reader)

    def unblock_reader(self, reader):
        """Снять блокировку; ``True`` если запись была и удалена."""
        c = self._conn()
        cur = c.execute('DELETE FROM reader_block WHERE reader=?', (reader,))
        c.commit()
        return cur.rowcount > 0

    def get_block(self, reader):
        r = self._conn().execute(
            'SELECT * FROM reader_block WHERE reader=?', (reader,)).fetchone()
        return dict(r) if r else None

    def blocked_readers(self):
        """Все актуальные статусы блокировки -> list (по читателю)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM reader_block ORDER BY reader').fetchall()]


class DebtorsService:
    """Прикладной слой санкций над :class:`DebtStore` — расчёт пеней по
    календарю, регистрация просрочек/утерь, эскалация блокировок, отчётность.

    ``now`` инжектируется (:func:`_utcnow` по умолчанию) для детерминизма в
    тестах. ``store`` тоже инжектируется (``:memory:`` по умолчанию).
    """

    def __init__(self, store=None, now=None):
        self.store = store or DebtStore(':memory:')
        self._now = now or _utcnow

    # -- расчёт по календарю --------------------------------------------------

    @staticmethod
    def days_overdue(due_date, as_of):
        """Число ЦЕЛЫХ дней просрочки (``>= 0``).

        Разница ``as_of - due_date`` по календарю (``date.fromisoformat``).
        Если ``as_of`` ещё не наступил после срока (в срок или раньше) — ``0``.
        """
        if not due_date or not as_of:
            return 0
        due = date.fromisoformat(due_date)
        cur = date.fromisoformat(as_of)
        delta = (cur - due).days
        return delta if delta > 0 else 0

    # -- регистрация задолженностей ------------------------------------------

    def register_overdue(self, reader, item, due_date, as_of,
                         fine_per_day_kopecks, db='*'):
        """Зарегистрировать ПРОСРОЧКУ: ``amount = дни_просрочки * тариф/день``.

        При ``days_overdue == 0`` сумма ``0`` (долг всё равно фиксируется как
        факт просрочки нулевой длины — на момент ``as_of`` она ещё нулевая)."""
        days = self.days_overdue(due_date, as_of)
        amount = days * int(fine_per_day_kopecks)
        return self.store.add_debt(reader, item, db, due_date, KIND_OVERDUE,
                                   amount, self._now())

    def register_lost(self, reader, item, replacement_kopecks, db='*'):
        """Зарегистрировать УТЕРЮ: ``amount = стоимость замены`` (копеек)."""
        return self.store.add_debt(reader, item, db, None, KIND_LOST,
                                   int(replacement_kopecks), self._now())

    # -- запросы по читателю --------------------------------------------------

    def reader_debts(self, reader):
        """Открытые (``unsettled``) долги читателя -> сводка.

        ``{'items': [...], 'total': копеек, 'count': N}``."""
        items = self.store.debts(reader=reader, unsettled_only=True)
        total = self.store.outstanding_total(reader)
        return {'items': items, 'total': total, 'count': len(items)}

    def settle(self, debt_id):
        """Погасить долг по id -> ``bool`` (изменилась ли строка)."""
        return self.store.settle_debt(debt_id)

    # -- эскалация блокировки -------------------------------------------------

    def evaluate_block(self, reader, threshold_kopecks=0, threshold_count=3):
        """Пересчитать санкцию читателя по его ОТКРЫТЫМ долгам.

        Правило эскалации:
          * ``total > threshold_kopecks`` ИЛИ ``count >= threshold_count``
            -> ``block`` (полная блокировка);
          * иначе если есть хотя бы один долг -> ``warn``;
          * если долгов нет -> снять блокировку (``unblock``).

        Возвращает текущее состояние:
        ``{'reader', 'level': 'warn'|'block'|None, 'total', 'count'}``.
        """
        summary = self.reader_debts(reader)
        total = summary['total']
        count = summary['count']
        if count == 0:
            self.store.unblock_reader(reader)
            return {'reader': reader, 'level': None, 'total': 0, 'count': 0}
        if total > threshold_kopecks or count >= threshold_count:
            level = LEVEL_BLOCK
        else:
            level = LEVEL_WARN
        reason = 'unsettled=%d total=%dk' % (count, total)
        self.store.block_reader(reader, reason, level, self._now())
        return {'reader': reader, 'level': level, 'total': total,
                'count': count}

    def is_blocked(self, reader):
        """Полностью ли заблокирован читатель (``level == 'block'``)."""
        blk = self.store.get_block(reader)
        return bool(blk) and blk['level'] == LEVEL_BLOCK

    # -- отчётность -----------------------------------------------------------

    def debtors_report(self, as_of=None):
        """Сводный отчёт по ВСЕМ открытым долгам.

        ``{'readers_with_debt': N, 'total_owed': копеек,
           'by_kind': {'overdue': копеек, 'lost': копеек}}``.

        ``as_of`` принимается для совместимости сигнатуры (отчёт строится по
        уже зафиксированным суммам долгов и от него не зависит).
        """
        rows = self.store.debts(unsettled_only=True)
        readers = set()
        total = 0
        by_kind = {KIND_OVERDUE: 0, KIND_LOST: 0}
        for r in rows:
            readers.add(r['reader'])
            amt = int(r['amount_kopecks'])
            total += amt
            by_kind[r['kind']] = by_kind.get(r['kind'], 0) + amt
        return {'readers_with_debt': len(readers), 'total_owed': total,
                'by_kind': by_kind}
