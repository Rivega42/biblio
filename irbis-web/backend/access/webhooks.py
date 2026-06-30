#!/usr/bin/env python3
"""WEBHOOKS — исходящие вебхуки per-tenant (own-store, issue #356, эпик #240).

Закрывает разрыв «интеграция по событиям»: внешние системы (СУФД, СМЭВ,
учётные/уведомительные сервисы тенанта) должны узнавать о фактах в Biblio —
заведена запись, выдан экземпляр, поставлен холд, завершён импорт. Реестр
подписок на события + формирование ПОДПИСАННОГО payload + журнал доставки.
Чистый stdlib + ``sqlite3`` (dev-паритет, ADR-004), без сети и без новых
pip-зависимостей — в точности как ``config_store.py``/``pay.py``. HMAC —
stdlib ``hmac`` + ``hashlib``, JSON — stdlib ``json``.

Важно про границы слоя
----------------------
Здесь НЕТ реального сетевого вызова. Транспорт (HTTP POST по ``url`` с
заголовком подписи и собственно ``log_delivery``) — на слое applier. Этот
модуль отвечает за «ЧТО отправить»: какие подписки активны на событие, какой
payload сформировать и какой подписью его заверить. Реальную отправку и запись
факта доставки делает applier.

Модель
------
  * таблица ``subscription`` — реестр подписок ``(tenant, event, url, secret)``;
    ``secret`` хранится В ОТКРЫТОМ виде в сторе (нужен для подписи), но наружу
    (``list``/``subscribe``/``set_active``) ВСЕГДА маскируется (``'***'`` если
    задан, иначе ``''``). Реальный secret виден только внутри ``sign``/``prepare``;
  * таблица ``delivery`` — журнал доставки (отдельная таблица): кто/что/статус/
    сколько попыток. Заполняется applier'ом через :meth:`WebhookStore.log_delivery`.

``WebhookStore`` — низкоуровневый стор (CRUD подписок + журнал доставки).
``WebhookService`` — глубина: валидация события/URL, маскировка secret наружу,
подпись HMAC-SHA256, сборка payload и план отправки :meth:`prepare`.
"""
import hashlib
import hmac
import json
import sqlite3
import threading
from datetime import datetime, timezone

# Допустимые события вебхука.
EVENTS = ('record.created', 'record.updated', 'loan.issued',
          'hold.placed', 'hold.cancelled', 'import.completed')

# Чем маскируется secret наружу, если он задан.
_MASK = '***'


def _utcnow():
    """Текущее время в ISO8601 (UTC). Инжектируется в стор как ``now``."""
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS subscription (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant     TEXT NOT NULL DEFAULT 'default',
  event      TEXT NOT NULL,            -- одно из EVENTS
  url        TEXT NOT NULL,            -- куда слать (транспорт — на applier)
  secret     TEXT NOT NULL DEFAULT '', -- ключ HMAC; наружу маскируется
  active     INTEGER NOT NULL DEFAULT 1,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS subscription_tenant_idx
  ON subscription(tenant, event, active);

CREATE TABLE IF NOT EXISTS delivery (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  subscription_id INTEGER NOT NULL,
  event           TEXT NOT NULL,
  status          TEXT NOT NULL,       -- ok | failed | ... (на усмотрение applier)
  attempts        INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT
);
CREATE INDEX IF NOT EXISTS delivery_sub_idx
  ON delivery(subscription_id);
"""


class WebhookStore:
    """Собственный sqlite-стор подписок на события и журнала доставки.

    ``:memory:`` или файл; create-on-init. Соединение thread-local (домашний
    стиль); строки — plain ``dict``. ``now`` инжектируется (по умолчанию
    :func:`_utcnow`, ISO8601) для детерминизма в тестах. Secret в этом слое
    хранится КАК ЕСТЬ (открытым) — маскировка живёт в :class:`WebhookService`.
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

    # ---- подписки -------------------------------------------------------

    def add(self, tenant, event, url, secret):
        """Завести подписку. Возвращает сохранённую строку-dict (с РЕАЛЬНЫМ secret)."""
        now = self._now()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO subscription(tenant,event,url,secret,active,created_at) '
            'VALUES(?,?,?,?,1,?)',
            (tenant, event, url, secret, now))
        c.commit()
        return self.get(cur.lastrowid)

    def list(self, tenant, event=None, active_only=False):
        """Подписки тенанта (с РЕАЛЬНЫМ secret), по ``id``.

        ``event`` — фильтр по событию; ``active_only`` — только активные.
        """
        sql = 'SELECT * FROM subscription WHERE tenant=?'
        params = [tenant]
        if event is not None:
            sql += ' AND event=?'
            params.append(event)
        if active_only:
            sql += ' AND active=1'
        sql += ' ORDER BY id'
        rows = self._conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get(self, id):
        """Строка-dict подписки (с РЕАЛЬНЫМ secret) по ``id`` или ``None``."""
        row = self._conn().execute(
            'SELECT * FROM subscription WHERE id=?', (id,)).fetchone()
        return dict(row) if row else None

    def set_active(self, id, active):
        """Включить/выключить подписку. Возвращает обновлённую строку или ``None``."""
        c = self._conn()
        c.execute('UPDATE subscription SET active=? WHERE id=?',
                  (1 if active else 0, id))
        c.commit()
        return self.get(id)

    def set_secret(self, id, secret):
        """Сменить секрет подписи подписки. Возвращает обновлённую строку или ``None``."""
        c = self._conn()
        c.execute('UPDATE subscription SET secret=? WHERE id=?', (secret or '', id))
        c.commit()
        return self.get(id)

    def remove(self, id):
        """Удалить подписку. ``True`` — если строка была удалена, иначе ``False``."""
        c = self._conn()
        cur = c.execute('DELETE FROM subscription WHERE id=?', (id,))
        c.commit()
        return cur.rowcount > 0

    # ---- журнал доставки ------------------------------------------------

    def log_delivery(self, subscription_id, event, status, attempts=1):
        """Записать факт доставки в журнал. Возвращает сохранённую строку-dict.

        Вызывается applier'ом после реальной отправки (этот модуль сеть не трогает).
        """
        now = self._now()
        c = self._conn()
        cur = c.execute(
            'INSERT INTO delivery(subscription_id,event,status,attempts,created_at) '
            'VALUES(?,?,?,?,?)',
            (subscription_id, event, status, attempts, now))
        c.commit()
        row = c.execute('SELECT * FROM delivery WHERE id=?',
                        (cur.lastrowid,)).fetchone()
        return dict(row)

    def deliveries(self, subscription_id=None, limit=100):
        """Журнал доставки (свежие сверху), опционально по одной подписке."""
        if subscription_id is None:
            rows = self._conn().execute(
                'SELECT * FROM delivery ORDER BY id DESC LIMIT ?',
                (limit,)).fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM delivery WHERE subscription_id=? '
                'ORDER BY id DESC LIMIT ?',
                (subscription_id, limit)).fetchall()
        return [dict(r) for r in rows]


def _mask_secret(secret):
    """Маскировать secret для выдачи наружу: ``'***'`` если задан, иначе ``''``."""
    return _MASK if secret else ''


def _masked(row):
    """Копия строки-dict подписки с замаскированным ``secret`` (для выдачи наружу)."""
    d = dict(row)
    d['secret'] = _mask_secret(d.get('secret', ''))
    return d


class WebhookService:
    """Глубина над :class:`WebhookStore`: валидация, маскировка secret наружу,
    подпись HMAC-SHA256, сборка payload и план отправки.

    КОНТРАКТ маскировки: всё, что уходит наружу (``subscribe``/``list``/
    ``set_active``), несёт ЗАМАСКИРОВАННЫЙ secret (``'***'``/``''``). Реальный
    secret читается из стора только внутри :meth:`sign` (через :meth:`prepare`)
    и нигде не отдаётся вызывающему.
    """

    def __init__(self, store=None, now=None):
        self.store = store or WebhookStore(':memory:', now=now)
        self._now = now or _utcnow

    # ---- реестр подписок (secret наружу маскирован) ---------------------

    def subscribe(self, tenant, event, url, secret=''):
        """Подписать тенант на событие. Возвращает подписку с МАСКИРОВАННЫМ secret.

        Валидация: ``event`` обязан быть из :data:`EVENTS` (иначе ``ValueError``),
        ``url`` непуст (иначе ``ValueError``). Реальный secret уходит в стор;
        наружу — ``'***'`` если задан, иначе ``''``.
        """
        if event not in EVENTS:
            raise ValueError('недопустимое событие вебхука: %r' % (event,))
        if not url:
            raise ValueError('url подписки не может быть пустым')
        row = self.store.add(tenant, event, url, secret or '')
        return _masked(row)

    def list(self, tenant, event=None):
        """Подписки тенанта с МАСКИРОВАННЫМ secret (фильтр по ``event``)."""
        return [_masked(r) for r in self.store.list(tenant, event=event)]

    def unsubscribe(self, id):
        """Удалить подписку. ``True``/``False`` (делегирует стору)."""
        return self.store.remove(id)

    def set_active(self, id, active):
        """Вкл/выкл подписку. Возвращает обновлённую строку (МАСКИР.) или ``None``."""
        row = self.store.set_active(id, active)
        return _masked(row) if row else None

    def rotate_secret(self, id, secret):
        """Сменить секрет подписи подписки. Возвращает строку (secret МАСКИР.) или ``None``."""
        row = self.store.set_secret(id, secret or '')
        return _masked(row) if row else None

    # ---- подпись и payload ----------------------------------------------

    def sign(self, secret, body_str):
        """Подписать тело вебхука: HMAC-SHA256 hex от ``body_str`` ключом ``secret``.

        Ключ и тело кодируются в ``utf-8``. Пустой ``secret`` -> ``''`` (без
        подписи): анонимные/нечувствительные вебхуки допустимы.
        """
        if not secret:
            return ''
        mac = hmac.new(secret.encode('utf-8'), body_str.encode('utf-8'),
                       hashlib.sha256)
        return mac.hexdigest()

    def build_payload(self, event, data, now_ts=None):
        """Сформировать тело вебхука: ``{'event', 'ts', 'data'}``.

        ``ts`` — отметка времени (``now_ts`` если задана, иначе текущее ``now``).
        ``data`` — произвольный dict полезной нагрузки события.
        """
        return {'event': event, 'ts': now_ts or self._now(), 'data': data}

    def prepare(self, tenant, event, data):
        """План отправки: что нужно разослать по АКТИВНЫМ подпискам на событие.

        Для каждой активной подписки тенанта на ``event`` формирует элемент
        ``{'subscription_id', 'url', 'event', 'payload', 'signature'}``, где
        ``payload`` = :meth:`build_payload`, а ``signature`` = :meth:`sign` от
        ``json.dumps(payload, sort_keys=True)`` РЕАЛЬНЫМ secret из стора (не
        маскированным). Реальную отправку и :meth:`WebhookStore.log_delivery`
        делает applier. Событие без активных подписок -> ``[]``.
        """
        subs = self.store.list(tenant, event=event, active_only=True)
        plan = []
        for sub in subs:
            payload = self.build_payload(event, data)
            body = json.dumps(payload, sort_keys=True)
            plan.append({
                'subscription_id': sub['id'],
                'url': sub['url'],
                'event': event,
                'payload': payload,
                'signature': self.sign(sub['secret'], body),
            })
        return plan
