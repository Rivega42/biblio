#!/usr/bin/env python3
"""JOB_QUEUE — собственная ОЧЕРЕДЬ ФОНОВЫХ ЗАДАЧ с приоритетами.

Фундамент pipeline ОЦИФРОВКИ (эпик #240): ставить в очередь долгие фоновые
задания и забирать их воркером по приоритету. Типичные ``kind``-ы — сборка
PDF/ZIP издания, OCR страниц, переиндексация полнотекста, генерация
IIIF-тайлов. Own-store: чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004),
без сети и без новых pip-зависимостей — в точности как
``debtors.py``/``pay.py``/``reader_registry.py``. В живой ИРБИС НИКОГДА не
пишем: очередь полностью изолирована в собственном sqlite-сторе.

Модель данных
-------------
Одна таблица ``job`` (job-keyed). ``payload`` и ``result`` хранятся как JSON-
строки (произвольная прикладная нагрузка/итог задания). Деньги/числа тут не
фигурируют — это инфраструктурный слой диспетчеризации.

Правило выборки (см. :meth:`JobStore.claim_next`)
-------------------------------------------------
Воркер забирает следующую ``pending``-задачу по правилу «БОЛЬШИЙ ``priority``
раньше; при равном приоритете — раньше созданная (FIFO)». FIFO детерминирован
по автоинкрементному ``id`` (НЕ по ``created_at``), поэтому порядок предсказуем
даже при совпадающих метках времени. Захват атомарен: ``pending -> running``
одним ``UPDATE ... WHERE status='pending'`` (выигрывает ровно один воркер).

Жизненный цикл статусов
-----------------------
``pending`` (поставлена) -> ``running`` (захвачена воркером, штамп
``started_at``) -> ``done`` (успех, штамп ``finished_at`` + ``result``) ИЛИ
``failed`` (ошибка, штамп ``finished_at`` + ``error``).

Время инжектируется (:func:`_utcnow` по умолчанию) для детерминизма в тестах.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Статусы задачи (жизненный цикл).
STATUS_PENDING = 'pending'   # поставлена в очередь, ждёт воркера
STATUS_RUNNING = 'running'   # захвачена воркером, выполняется
STATUS_DONE = 'done'         # успешно завершена
STATUS_FAILED = 'failed'     # завершена с ошибкой
JOB_STATUSES = (STATUS_PENDING, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED)


def _utcnow():
    """Текущий момент в ISO8601 (UTC, без микросекунд) — дефолтный ``now``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS job (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,                 -- тип задания (pdf|ocr|reindex|iiif|...)
  payload     TEXT NOT NULL DEFAULT '{}',    -- JSON прикладной нагрузки
  priority    INTEGER NOT NULL DEFAULT 0,    -- больше = раньше
  status      TEXT NOT NULL DEFAULT 'pending',
  result      TEXT,                          -- JSON итога (для done), null иначе
  error       TEXT,                          -- текст ошибки (для failed), null иначе
  created_at  TEXT NOT NULL,
  started_at  TEXT,                          -- штамп захвата воркером
  finished_at TEXT                           -- штамп завершения (done|failed)
);
CREATE INDEX IF NOT EXISTS job_status_idx ON job(status);
-- покрывающий индекс под правило выборки: priority DESC, id ASC по pending
CREATE INDEX IF NOT EXISTS job_claim_idx ON job(status, priority, id);
"""


class JobStore:
    """Собственный sqlite-стор очереди фоновых задач. ``:memory:`` или файл;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.

    ``now`` инжектируется (:func:`_utcnow` по умолчанию) для детерминизма."""

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

    # -- постановка / захват --------------------------------------------------

    def enqueue(self, kind, payload_json, priority=0):
        """Поставить задание в очередь (статус ``pending``); строка-dict.

        ``payload_json`` — уже сериализованная JSON-строка нагрузки."""
        c = self._conn()
        cur = c.execute(
            'INSERT INTO job(kind,payload,priority,status,created_at) '
            'VALUES(?,?,?,?,?)',
            (kind, payload_json if payload_json is not None else '{}',
             int(priority), STATUS_PENDING, self._now()))
        c.commit()
        return self.get(cur.lastrowid)

    def claim_next(self):
        """Атомарно захватить следующую ``pending``-задачу для воркера.

        Правило: БОЛЬШИЙ ``priority`` раньше; при равенстве — раньше созданная
        (FIFO по автоинкрементному ``id``). Переводит ``pending -> running`` и
        ставит ``started_at``. Возвращает строку-dict или ``None``, если
        очередь пуста."""
        c = self._conn()
        row = c.execute(
            'SELECT id FROM job WHERE status=? '
            'ORDER BY priority DESC, id ASC LIMIT 1',
            (STATUS_PENDING,)).fetchone()
        if row is None:
            return None
        job_id = row['id']
        # Атомарный захват: выигрывает ровно один воркер (WHERE status=pending).
        cur = c.execute(
            'UPDATE job SET status=?, started_at=? '
            'WHERE id=? AND status=?',
            (STATUS_RUNNING, self._now(), job_id, STATUS_PENDING))
        c.commit()
        if cur.rowcount == 0:
            # Гонка: кто-то опередил — задача уже не pending.
            return None
        return self.get(job_id)

    # -- завершение -----------------------------------------------------------

    def complete(self, job_id, result_json):
        """Завершить задачу успехом: ``done`` + ``finished_at`` + ``result``.

        ``result_json`` — уже сериализованная JSON-строка итога (или ``None``).
        Возвращает строку-dict или ``None``, если ``id`` неизвестен."""
        c = self._conn()
        cur = c.execute(
            'UPDATE job SET status=?, result=?, finished_at=? WHERE id=?',
            (STATUS_DONE, result_json, self._now(), job_id))
        c.commit()
        if cur.rowcount == 0:
            return None
        return self.get(job_id)

    def fail(self, job_id, error):
        """Завершить задачу ошибкой: ``failed`` + ``finished_at`` + ``error``.

        Возвращает строку-dict или ``None``, если ``id`` неизвестен."""
        c = self._conn()
        cur = c.execute(
            'UPDATE job SET status=?, error=?, finished_at=? WHERE id=?',
            (STATUS_FAILED, error, self._now(), job_id))
        c.commit()
        if cur.rowcount == 0:
            return None
        return self.get(job_id)

    # -- запросы --------------------------------------------------------------

    def get(self, job_id):
        r = self._conn().execute(
            'SELECT * FROM job WHERE id=?', (job_id,)).fetchone()
        return dict(r) if r else None

    def list(self, status=None, limit=100):
        """Список задач (опц. фильтр по статусу), новые сверху (по ``id`` DESC)."""
        sql = 'SELECT * FROM job'
        params = []
        if status is not None:
            sql += ' WHERE status=?'
            params.append(status)
        sql += ' ORDER BY id DESC LIMIT ?'
        params.append(int(limit))
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def counts_by_status(self):
        """Счётчики по ВСЕМ 4 статусам -> dict (0 для отсутствующих)."""
        counts = {s: 0 for s in JOB_STATUSES}
        rows = self._conn().execute(
            'SELECT status, COUNT(*) AS n FROM job GROUP BY status').fetchall()
        for r in rows:
            counts[r['status']] = int(r['n'])
        return counts


class JobQueue:
    """Прикладной сервис над :class:`JobStore` с JSON-удобством.

    Снаружи прикладной код оперирует обычными dict-нагрузками/итогами, а
    (де)сериализацию в JSON берёт на себя этот слой. ``store`` и ``now``
    инжектируются (``:memory:`` / :func:`_utcnow` по умолчанию).
    """

    def __init__(self, store=None, now=None):
        self.store = store or JobStore(':memory:', now=now)
        self._now = now or _utcnow

    @staticmethod
    def _hydrate(job):
        """Распарсить JSON-поля ``payload``/``result`` строки-задачи.

        Пустой/отсутствующий ``result`` отдаём как ``None``."""
        if job is None:
            return None
        job = dict(job)
        raw_payload = job.get('payload')
        job['payload'] = json.loads(raw_payload) if raw_payload else None
        raw_result = job.get('result')
        job['result'] = json.loads(raw_result) if raw_result else None
        return job

    # -- постановка / захват --------------------------------------------------

    def enqueue(self, kind, payload=None, priority=0):
        """Поставить задание (``payload`` dict -> JSON). Возвращает job с уже
        РАСПАРСЕННЫМ ``payload``."""
        payload_json = json.dumps(payload if payload is not None else {})
        return self._hydrate(self.store.enqueue(kind, payload_json, priority))

    def claim(self):
        """Захватить следующую задачу (по приоритету/FIFO) -> job|None."""
        return self._hydrate(self.store.claim_next())

    # -- завершение -----------------------------------------------------------

    def complete(self, job_id, result=None):
        """Завершить успехом (``result`` dict -> JSON). Неизвестный ``id`` ->
        ``None``. В ответе ``result`` распарсен."""
        result_json = json.dumps(result) if result is not None else None
        return self._hydrate(self.store.complete(job_id, result_json))

    def fail(self, job_id, error=''):
        """Завершить ошибкой. Неизвестный ``id`` -> ``None``."""
        return self._hydrate(self.store.fail(job_id, error))

    # -- запросы --------------------------------------------------------------

    def get(self, job_id):
        """Задача по ``id`` (``payload``/``result`` распарсены) или ``None``."""
        return self._hydrate(self.store.get(job_id))

    def list(self, status=None, limit=100):
        """Список задач (опц. фильтр по статусу), ``payload``/``result``
        распарсены."""
        return [self._hydrate(r)
                for r in self.store.list(status=status, limit=limit)]

    def stats(self):
        """Сводка очереди: ``{'total': N, 'by_status': {...4 статуса...}}``."""
        by_status = self.store.counts_by_status()
        return {'total': sum(by_status.values()), 'by_status': by_status}
