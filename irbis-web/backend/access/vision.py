#!/usr/bin/env python3
"""Vision domain — нативный домен КАМЕР / FaceID (нативный домен Biblio).

Узел #272 (DEVICES_NATIVE_ARCHITECTURE.md, BIBLIO_DEVICE_INTEGRATION_DESIGN.md
§5.4 «Vision»): то, что в стеке IDlogic делал Dahua NetSDK + центральный
`api.svc` (FaceDetect/камеры — `FaceDetectCameraModify`,
`FaceDetectCameraToStationAttach`, `KPI_Visitor`, FaceID-авторизация в
`BookCheckOutPage.btnFaceIDAuth_Click`, см. DEVICE_CONTROL_MAP.md §6), —
реализуем как НОРМАЛЬНЫЙ домен Biblio. Это НЕ копия БД IDlogic и НЕ второй
SDK-силос: реконструированный контракт — лишь источник требований; модель наша.

Что это
-------
Самодостаточный домен над собственным sqlite-стором (dev-паритет, ADR-004:
sqlite dev / Postgres prod — зеркало в ``schema_vision.sql``). Чистая доменная
логика, без сетевого I/O, без новых pip-зависимостей — в точности как
``devices.py``/``acquisition.py``. Дробит две задачи:

  * **журнал распознаваний** (``recognition_event``) — что и когда камера
    «увидела» (вход NetSDK-колбэка `Fd_OnFaceRecognized`);
  * **реестр привязок «лицо↔билет читателя»** (``face_subject``) — для
    идентификации на станции самообслуживания (FaceID-вход как альтернатива
    карте/ЕКП) и брони SafeKeeper по лицу.

Приватность (жёсткое правило)
-----------------------------
Домен хранит ТОЛЬКО непрозрачные **токены лица** — строковый id/хеш/ссылку на
шаблон, которые отдаёт SDK камеры. Сырые биометрические изображения и шаблоны
(вектора признаков, кадры лица) здесь НЕ хранятся НИКОГДА — для них в схеме нет
ни одной колонки. Камера/её SDK держит чувствительную биометрию у себя; Biblio
оперирует лишь обезличенной ссылкой. Дополнительно:

  * ``forget(ticket)`` — операция «права на забвение»: удаляет привязки читателя
    и обезличивает его события распознавания (``ticket -> NULL``).
  * В коде/тестах нет реальных ПДн — только синтетические токены.

Это сознательное усиление относительно IDlogic (там `ReaderPhotoAdd` грузил сам
снимок лица в БД); см. BIBLIO_DEVICE_INTEGRATION_DESIGN.md §8 (безопасность).

Гранты/аудит
------------
Домен — чистая логика над своим стором (как ``devices.py``): авторизацию
(`vision.read`/`vision.enroll`/`vision.admin`) и центральный audit-log
проставляет слой маршрутов (`server.py` + `access/authz.py`).
"""
import threading
import time


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS face_subject (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket      TEXT NOT NULL,                       -- билет читателя (AbisCode/ЕКП)
  face_token  TEXT NOT NULL UNIQUE,                -- НЕПРОЗРАЧНЫЙ токен лица (id/хеш SDK); НЕ изображение
  label       TEXT,                                -- произвольная метка (камера/станция/комментарий)
  created     REAL NOT NULL,
  updated     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS face_subject_ticket_idx ON face_subject(ticket);
CREATE TABLE IF NOT EXISTS recognition_event (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id   INTEGER,                             -- камера (device.id из домена devices), может быть NULL
  face_token  TEXT,                                -- НЕПРОЗРАЧНЫЙ токен лица из колбэка SDK
  ticket      TEXT,                                -- резолв в билет (NULL = не сопоставлено / обезличено)
  score       REAL,                                -- уверенность распознавания SDK (0..1), опц.
  matched     INTEGER NOT NULL DEFAULT 0,          -- 1 = токен есть в реестре face_subject
  ts          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS recognition_event_dev_idx ON recognition_event(device_id, ts);
CREATE INDEX IF NOT EXISTS recognition_event_ticket_idx ON recognition_event(ticket, ts);
"""


class VisionError(Exception):
    """Доменная ошибка vision (пустые аргументы enroll/identify и т.п.)."""


class VisionStore:
    """Собственный sqlite-стор домена vision (реестр привязок + журнал событий).

    ``db_path=':memory:'`` (по умолчанию) или временный файл в тестах;
    create-on-init. Соединение thread-local (домашний стиль); строки — dict.
    """

    def __init__(self, db_path=':memory:'):
        self.db_path = db_path
        self._local = threading.local()
        self.ensure_schema()

    def _conn(self):
        import sqlite3
        c = getattr(self._local, 'conn', None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            c.row_factory = sqlite3.Row
            c.execute('PRAGMA foreign_keys=ON')
            self._local.conn = c
        return c

    def ensure_schema(self):
        c = self._conn()
        c.executescript(SCHEMA_SQLITE)
        c.commit()

    # ---- face_subject (реестр привязок лицо↔билет) ------------------------ #
    def get_subject_by_token(self, face_token):
        r = self._conn().execute('SELECT * FROM face_subject WHERE face_token=?',
                                 (face_token,)).fetchone()
        return dict(r) if r else None

    def upsert_subject(self, ticket, face_token, label, now=None):
        """Идемпотентный upsert по ``face_token`` (UNIQUE): повторный enroll
        того же токена обновляет билет/метку, не создавая дубль. ``created``
        сохраняется, ``updated`` — обновляется."""
        now = time.time() if now is None else now
        c = self._conn()
        existing = self.get_subject_by_token(face_token)
        if existing:
            c.execute('UPDATE face_subject SET ticket=?, label=?, updated=? '
                      'WHERE face_token=?', (ticket, label, now, face_token))
            c.commit()
            return self.get_subject_by_token(face_token)
        c.execute('INSERT INTO face_subject(ticket,face_token,label,created,'
                  'updated) VALUES(?,?,?,?,?)', (ticket, face_token, label, now,
                                                 now))
        c.commit()
        return self.get_subject_by_token(face_token)

    def list_subjects(self, ticket=None):
        if ticket is None:
            rows = self._conn().execute(
                'SELECT * FROM face_subject ORDER BY id').fetchall()
        else:
            rows = self._conn().execute(
                'SELECT * FROM face_subject WHERE ticket=? ORDER BY id',
                (ticket,)).fetchall()
        return [dict(r) for r in rows]

    def delete_subjects(self, ticket):
        c = self._conn()
        cur = c.execute('DELETE FROM face_subject WHERE ticket=?', (ticket,))
        c.commit()
        return cur.rowcount

    # ---- recognition_event (журнал распознаваний) ------------------------- #
    def add_event(self, device_id, face_token, ticket, score, matched, ts=None):
        ts = time.time() if ts is None else ts
        c = self._conn()
        cur = c.execute(
            'INSERT INTO recognition_event(device_id,face_token,ticket,score,'
            'matched,ts) VALUES(?,?,?,?,?,?)',
            (device_id, face_token, ticket, score, 1 if matched else 0, ts))
        c.commit()
        return cur.lastrowid

    def list_events(self, device_id=None, ticket=None, limit=100):
        q = 'SELECT * FROM recognition_event WHERE 1=1'
        args = []
        if device_id is not None:
            q += ' AND device_id=?'; args.append(device_id)
        if ticket is not None:
            q += ' AND ticket=?'; args.append(ticket)
        q += ' ORDER BY ts DESC, id DESC'
        if limit is not None:
            q += ' LIMIT ?'; args.append(limit)
        return [dict(r) for r in self._conn().execute(q, args).fetchall()]

    def anonymize_events(self, ticket):
        """Обезличить события читателя (``ticket -> NULL``) — право на забвение.
        Сам факт распознавания (статистика камеры) сохраняется, но связь с
        читателем разрывается."""
        c = self._conn()
        cur = c.execute('UPDATE recognition_event SET ticket=NULL WHERE ticket=?',
                        (ticket,))
        c.commit()
        return cur.rowcount


class VisionService:
    """Операции домена камер/FaceID над :class:`VisionStore`.

    Авторизация/аудит — на слое маршрутов; здесь — чистая доменная логика.

    Параметры:
      * ``min_score`` — нижний порог уверенности для событий (точное совпадение
        токена в реестре от него НЕ зависит — токен либо есть, либо нет).
    """

    def __init__(self, store=None, now=None, min_score=0.0):
        self.store = store or VisionStore()
        self._now = now or time.time
        self.min_score = min_score

    # -- реестр привязок лицо↔билет ----------------------------------------- #
    def enroll(self, ticket, face_token, label=None):
        """Привязать токен лица к билету читателя (upsert, идемпотентно по
        ``face_token``). Хранится ТОЛЬКО токен — не изображение.

        Raises ``VisionError`` при пустых ``ticket``/``face_token``.
        """
        if not ticket:
            raise VisionError('enroll: empty ticket')
        if not face_token:
            raise VisionError('enroll: empty face_token')
        return self.store.upsert_subject(ticket, face_token, label,
                                         now=self._now())

    def identify(self, face_token, min_score=None):
        """Сопоставить токен лица с реестром.

        Возвращает ``{'ticket': <билет>, 'matched': True}`` если токен есть в
        реестре, иначе ``{'ticket': None, 'matched': False}``. Сопоставление —
        ТОЧНОЕ по токену; score-порог к точному токену НЕ применяется (он
        относится к событиям распознавания, не к реестровому совпадению), но
        принят в сигнатуре для симметрии вызова со станции.

        Raises ``VisionError`` при пустом ``face_token``.
        """
        if not face_token:
            raise VisionError('identify: empty face_token')
        subj = self.store.get_subject_by_token(face_token)
        if subj:
            return {'ticket': subj['ticket'], 'matched': True}
        return {'ticket': None, 'matched': False}

    def subjects(self, ticket=None):
        return self.store.list_subjects(ticket=ticket)

    # -- журнал распознаваний (вход колбэка SDK) ---------------------------- #
    def record_event(self, device_id, face_token, score=None, ticket=None):
        """Записать событие распознавания камеры.

        ``matched`` = есть ли в реестре subject для ``face_token``. Если
        ``ticket`` не передан и токен распознан — авто-резолв билета из реестра.
        Чувствительная биометрия (кадр/шаблон) сюда не попадает — только токен.
        """
        subj = self.store.get_subject_by_token(face_token) if face_token else None
        matched = subj is not None
        if matched and ticket is None:
            ticket = subj['ticket']
        return self.store.add_event(device_id, face_token, ticket, score,
                                    matched, ts=self._now())

    def events(self, device_id=None, ticket=None, limit=100):
        return self.store.list_events(device_id=device_id, ticket=ticket,
                                      limit=limit)

    # -- право на забвение -------------------------------------------------- #
    def forget(self, ticket):
        """Удалить привязки лица читателя (реестр) и обезличить его события
        распознавания (``ticket -> NULL``).

        Возвращает число затронутых строк (удалённые subject + обезличенные
        события).
        """
        if not ticket:
            raise VisionError('forget: empty ticket')
        deleted = self.store.delete_subjects(ticket)
        anonymized = self.store.anonymize_events(ticket)
        return deleted + anonymized
