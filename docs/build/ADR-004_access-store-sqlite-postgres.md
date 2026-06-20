# ADR-004: хранилище доступа — sqlite (dev) / PostgreSQL (prod)

**Статус:** принято, P0. **Контекст:** Access-набор (учётки сотрудников, гранты функция×база×уровень, роли, аудит) нужен боевой и тестируемый сразу, без поднятия БД-сервера на машине разработки.

**Решение.**
- **Модель и SQL — единые.** Каноничная DDL — PostgreSQL (`irbis-web/backend/access/schema_postgres.sql`); dev-зеркало на **sqlite3** (stdlib) в `access/store.py` (та же модель: `staff_account`, `grant_entry`, `role`/`role_grant`/`account_role`, `audit_log`).
- **DAO абстрагирован.** Прикладной код ходит через `AccessStore` (методы `authenticate`, `add_grant`, `effective_grants`, `audit`…). Перенос на Postgres = реализация того же интерфейса на asyncpg + `PG_DSN` из env; логика авторизации (`access/authz.py`) и сидов (`access/seed.py`) не меняется.
- **Читатели НЕ в этом хранилище** — они в `RDR` (вход по билету через протокол). Здесь только сотрудники, их гранты и аудит.

**Почему так.** sqlite даёт работающий authz+audit в один `py server.py` (ноль инфраструктуры), при этом prod-путь (Postgres/asyncpg) уже описан DDL и DSN — переключение конфигурацией, без переписывания. Соответствует `P0_BUILDKIT §3-4`.

**Последствия.**
- Dev-БД `access.db` — **gitignored** (как и `.env`); сиды содержат только демо-пароли.
- Конкурентность sqlite ограничена (для P0 достаточно; нагрузка — на Postgres).
- `TODO(prod):` asyncpg-реализация `AccessStore`; миграции; перенос демо-сидов в провижининг.

См. также: `irbis-web/README.md`, `docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md`.
