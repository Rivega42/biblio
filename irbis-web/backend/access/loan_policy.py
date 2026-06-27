#!/usr/bin/env python3
"""LOAN POLICY — декларативные ПОЛИТИКИ ВЫДАЧИ АРМ «Книговыдача» (own-store).

Закрывает разрыв «лимиты выдачи»: правило вида
«категория читателя × вид издания → срок / лимит / продления / залог / пеня».
Это тот слой, который ИРБИС держит россыпью в ``.PAR``/меню (``.MNU``) и в логике
форматов, — здесь он сделан **декларативным** и единым. Чистый stdlib +
``sqlite3`` (dev-паритет, ADR-004), без сети и без новых pip-зависимостей —
в точности как ``pay.py``/``reader_registry.py``/``config_store.py``. Никаких
live-ИРБИС-записей.

Зачем отдельно от ``circulation.py``
------------------------------------
``circulation.py`` НЕ редактируется этим ребром. Там лимиты — захардкоженный
минимум на расчёт §5; здесь — самостоятельный конфигурируемый СЛОЙ ПОЛИТИК,
который книговыдача сможет опросить позже опциональным хендлом
``loan_policy=`` (как ``pay=``/``reader_registry=`` у ``CirculationEngine``),
вызывая ``resolve``/``check_loan``/``can_renew``/``fine_for``. Это не замена
движка выдачи, а его настраиваемые правила.

Модель
------
  * таблица ``loan_policy`` — правило уникально в паре
    ``(reader_category, doc_type)``;
  * ``reader_category`` — категория читателя (поле 50 RDR, напр. В01–В05),
    либо ``'*'`` — правило-джокер на любую категорию;
  * ``doc_type`` — вид издания (книга/журнал/диссертация/…), либо ``'*'``;
  * ``loan_days`` — срок выдачи в днях; ``max_items`` — лимит экземпляров
    на руках; ``renewals`` — число допустимых продлений;
  * ``deposit_kopecks`` — залог; ``fine_per_day_kopecks`` — пеня за день
    просрочки. Денежные величины — целые КОПЕЙКИ (как ``pay`` бережёт от
    плавающей арифметики).

Разрешение политики (зеркало ``authz.best_grant``)
--------------------------------------------------
``resolve(reader_category, doc_type)`` идёт по убыванию специфичности с
фолбэком, как best-grant в авторизации (точное правило бьёт ``'*'``):
точное ``(cat, type)`` → ``(cat, '*')`` → ``('*', type)`` → ``('*', '*')`` →
встроенный :data:`DEFAULT_POLICY`. В результат добавляется ключ ``matched`` —
на каком уровне сработало совпадение (``exact`` / ``category`` / ``type`` /
``global`` / ``default``).

``LoanPolicyStore`` — низкоуровневый стор (upsert/get/list/delete).
``LoanPolicyService`` — глубина: разрешение с фолбэком, проверка лимита
выдачи, проверка продления, расчёт пени.
"""
import sqlite3
import threading
from datetime import datetime, timezone

# Джокер: правило применимо к любой категории читателя / любому виду издания.
WILDCARD = '*'

# Встроенный дефолт — применяется, когда в сторе нет ни одного подходящего
# правила (последнее звено фолбэка ``resolve``). Срок 14 дней, лимит 5 на
# руках, одно продление, без залога, пеня 5 руб/день (500 копеек).
DEFAULT_POLICY = {
    'loan_days': 14,
    'max_items': 5,
    'renewals': 1,
    'deposit_kopecks': 0,
    'fine_per_day_kopecks': 500,
}


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS loan_policy (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  reader_category      TEXT,                  -- 50 категория RDR | '*'
  doc_type             TEXT,                  -- вид издания | '*'
  loan_days            INTEGER,               -- срок выдачи, дней
  max_items            INTEGER,               -- лимит экземпляров на руках
  renewals             INTEGER DEFAULT 1,     -- допустимых продлений
  deposit_kopecks      INTEGER DEFAULT 0,     -- залог, копейки
  fine_per_day_kopecks INTEGER DEFAULT 0,     -- пеня за день просрочки, копейки
  updated_at           TEXT,
  UNIQUE(reader_category, doc_type)
);
CREATE INDEX IF NOT EXISTS loan_policy_cat_idx
  ON loan_policy(reader_category, doc_type);
"""


class LoanPolicyStore:
    """Собственный sqlite-стор политик выдачи. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.

    ``now`` инжектируется (по умолчанию :func:`_utcnow`, ISO8601) — чтобы
    тесты могли подставить детерминированные часы.
    """

    def __init__(self, db_path=':memory:', now=None):
        self.db_path = db_path
        self._local = threading.local()
        self._now = now or _utcnow
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

    def upsert_policy(self, reader_category, doc_type, loan_days, max_items,
                      renewals=1, deposit_kopecks=0, fine_per_day_kopecks=0):
        """Идемпотентно завести/обновить правило по паре
        ``(reader_category, doc_type)``.

        Повторный upsert той же пары обновляет поля и ``updated_at`` (одна
        запись, не дубль). Возвращает строку правила (dict)."""
        now = self._now()
        c = self._conn()
        c.execute(
            'INSERT INTO loan_policy(reader_category,doc_type,loan_days,'
            'max_items,renewals,deposit_kopecks,fine_per_day_kopecks,updated_at) '
            'VALUES(?,?,?,?,?,?,?,?) '
            'ON CONFLICT(reader_category,doc_type) DO UPDATE SET '
            'loan_days=excluded.loan_days,max_items=excluded.max_items,'
            'renewals=excluded.renewals,deposit_kopecks=excluded.deposit_kopecks,'
            'fine_per_day_kopecks=excluded.fine_per_day_kopecks,'
            'updated_at=excluded.updated_at',
            (reader_category, doc_type, loan_days, max_items, renewals,
             deposit_kopecks, fine_per_day_kopecks, now))
        c.commit()
        return self.get_policy(reader_category, doc_type)

    def get_policy(self, reader_category, doc_type):
        """Правило по точной паре ``(reader_category, doc_type)`` или ``None``."""
        r = self._conn().execute(
            'SELECT * FROM loan_policy WHERE reader_category=? AND doc_type=?',
            (reader_category, doc_type)).fetchone()
        return dict(r) if r else None

    def list_policies(self):
        """Все правила (по id)."""
        return [dict(r) for r in self._conn().execute(
            'SELECT * FROM loan_policy ORDER BY id').fetchall()]

    def delete_policy(self, policy_id):
        """Удалить правило по ``id``. Возвращает ``True``, если строка была."""
        c = self._conn()
        cur = c.execute('DELETE FROM loan_policy WHERE id=?', (policy_id,))
        c.commit()
        return cur.rowcount > 0


class LoanPolicyService:
    """Операции над :class:`LoanPolicyStore` — разрешение политик с фолбэком,
    проверка лимита выдачи, проверка продления, расчёт пени.

    Duck-typed контракт для опционального хендла ``loan_policy=`` в
    ``CirculationEngine`` (``circulation.py`` не редактируется): движок сможет
    вызвать ``resolve``/``check_loan``/``can_renew``/``fine_for``.
    """

    def __init__(self, store=None, now=None):
        self.store = store or LoanPolicyStore(':memory:', now=now)

    def set_policy(self, reader_category, doc_type, loan_days, max_items,
                   renewals=1, deposit=0, fine_per_day=0):
        """Завести/обновить правило (идемпотентно по паре). Возвращает dict."""
        return self.store.upsert_policy(
            reader_category, doc_type, loan_days, max_items,
            renewals=renewals, deposit_kopecks=deposit,
            fine_per_day_kopecks=fine_per_day)

    def resolve(self, reader_category, doc_type):
        """Применимая политика по убыванию специфичности с ФОЛБЭКОМ.

        Зеркало ``authz.best_grant`` (точное бьёт ``'*'``):
        точное ``(cat, type)`` -> ``(cat, '*')`` -> ``('*', type)`` ->
        ``('*', '*')`` -> :data:`DEFAULT_POLICY`. Возвращает dict политики
        с дополнительным ключом ``matched`` — уровень совпадения
        (``exact`` / ``category`` / ``type`` / ``global`` / ``default``).
        """
        ladder = (
            ('exact', reader_category, doc_type),
            ('category', reader_category, WILDCARD),
            ('type', WILDCARD, doc_type),
            ('global', WILDCARD, WILDCARD),
        )
        for matched, cat, typ in ladder:
            row = self.store.get_policy(cat, typ)
            if row is not None:
                row['matched'] = matched
                return row
        # Последнее звено — встроенный дефолт (стор пуст / ничего не подошло).
        policy = dict(DEFAULT_POLICY)
        policy['matched'] = 'default'
        return policy

    def check_loan(self, reader_category, doc_type, current_count):
        """Можно ли выдать ещё один экземпляр при ``current_count`` на руках.

        Запрещает выдачу, если ``current_count >= max_items``
        (``reason='limit_reached'``), иначе ``allowed=True``. В ответе — срок
        и лимит из разрешённой политики (для UI/движка)."""
        policy = self.resolve(reader_category, doc_type)
        max_items = policy['max_items']
        if current_count >= max_items:
            allowed, reason = False, 'limit_reached'
        else:
            allowed, reason = True, 'ok'
        return {
            'allowed': allowed,
            'reason': reason,
            'loan_days': policy['loan_days'],
            'max_items': max_items,
        }

    def can_renew(self, reader_category, doc_type, renewals_used):
        """Допустимо ли ещё одно продление: ``renewals_used < renewals``."""
        policy = self.resolve(reader_category, doc_type)
        return renewals_used < policy['renewals']

    def fine_for(self, reader_category, doc_type, days_overdue):
        """Пеня в копейках за просрочку:
        ``max(0, days_overdue) * fine_per_day_kopecks`` (отрицательные дни -> 0)."""
        policy = self.resolve(reader_category, doc_type)
        return max(0, days_overdue) * policy['fine_per_day_kopecks']
