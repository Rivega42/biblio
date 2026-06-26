-- Vision domain — PostgreSQL DDL mirror of vision.py's inline sqlite schema
-- (ADR-004: sqlite dev / Postgres prod). Узел #272 (DEVICES_NATIVE_ARCHITECTURE.md,
-- BIBLIO_DEVICE_INTEGRATION_DESIGN.md §5.4 «Vision»).
--
-- Нативный домен КАМЕР / FaceID Biblio: журнал распознаваний + реестр привязок
-- «лицо↔билет читателя» для идентификации на станции самообслуживания и брони
-- SafeKeeper по лицу. НОВЫЙ файл — не трогает schema_postgres.sql / schema_devices.sql.
-- НЕ копия БД IDlogic: реконструированный контракт FaceDetect (DEVICE_CONTROL_MAP.md
-- §6) — лишь источник требований.
--
-- ПРИВАТНОСТЬ (жёсткое правило): хранится ТОЛЬКО непрозрачный токен лица
-- (id/хеш/ссылка на шаблон от SDK камеры). Сырые биометрические изображения и
-- шаблоны здесь НЕ хранятся НИКОГДА — для них нет ни одной колонки. Право на
-- забвение реализует vision.py::VisionService.forget (delete subject +
-- recognition_event.ticket -> NULL).

-- Реестр привязок «лицо↔билет читателя».
CREATE TABLE IF NOT EXISTS face_subject (
  id          BIGSERIAL PRIMARY KEY,
  ticket      TEXT NOT NULL,                       -- билет читателя (AbisCode/ЕКП)
  face_token  TEXT NOT NULL UNIQUE,                -- НЕПРОЗРАЧНЫЙ токен лица (id/хеш SDK); НЕ изображение
  label       TEXT,                                -- произвольная метка (камера/станция/комментарий)
  created     DOUBLE PRECISION NOT NULL,
  updated     DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS face_subject_ticket_idx ON face_subject(ticket);

-- Журнал распознаваний камеры (вход колбэка SDK `Fd_OnFaceRecognized`).
CREATE TABLE IF NOT EXISTS recognition_event (
  id          BIGSERIAL PRIMARY KEY,
  device_id   BIGINT,                              -- камера (device.id из домена devices), может быть NULL
  face_token  TEXT,                                -- НЕПРОЗРАЧНЫЙ токен лица из колбэка SDK
  ticket      TEXT,                                -- резолв в билет (NULL = не сопоставлено / обезличено)
  score       DOUBLE PRECISION,                    -- уверенность распознавания SDK (0..1), опц.
  matched     INTEGER NOT NULL DEFAULT 0,          -- 1 = токен есть в реестре face_subject
  ts          DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS recognition_event_dev_idx ON recognition_event(device_id, ts);
CREATE INDEX IF NOT EXISTS recognition_event_ticket_idx ON recognition_event(ticket, ts);
