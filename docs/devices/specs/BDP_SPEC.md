# BDP — Biblio Device Protocol (спецификация, черновик v0.1)

> Нативный протокол Biblio ↔ device-agent робо-шкафа (#418, волна E2 эпика #410).
> НЕ SIP2 и НЕ протокол IDlogic — чистый контракт «намерение ↔ событие».
> Опора: [BOOKCABINET_INTEGRATION_DESIGN.md](../BOOKCABINET_INTEGRATION_DESIGN.md) §4.
> Статус: доменный слой реализован и покрыт сквозным e2e-тестом
> (`irbis-web/backend/tests/test_bdp_e2e.py`, мок-агент, без железа). HTTP-врезка
> роутов (REST+WS поверх этих доменных операций) — следующий шаг.

## Принципы
- **Намерение, не RPC железа.** Biblio выражает бизнес-намерение (выдать/принять);
  агент сам решает, как исполнить механически, и рапортует событиями.
- **Идемпотентность по `op_id`** (UUID агента) на каждой операции с побочным эффектом
  — replay после офлайна не задваивает выдачу (реализовано: `loan.op_id UNIQUE`, #412).
- **Двухфазная сага** выдачи: `reserve → execute → op.result → commit | rollback` (#415).
- **Аутентификация — device-token** (`Authorization: Bearer`), tenant-scoped, с
  ротацией/отзывом (#413). НЕ legacy Basic ServiceLogin (тот только для IDlogic).
- **Версионирование** `bdp_version` + capability-дескриптор (что за устройство, что умеет).
- **Транспорт:** REST (команды/запросы) + WebSocket (события/прогресс/телеметрия), TLS.
- Термины наши: билет, экземпляр, ячейка, выдача, приём.

## Аутентификация
`Authorization: Bearer <device-token>` → контекст `{device_id, tenant, kind}`
(`DeviceService.authenticate_token`). Токен получают при регистрации устройства
(`issue_token`), хранится только sha256-хэш. Отозванный/просроченный/чужой → 401.

## Capability-дескриптор (регистрация)
```json
{ "bdp_version": "0.1", "kind": "self_service_cabinet",
  "vendor": "bookcabinet", "model": "rpi3-corexy-126",
  "capabilities": ["issue","return","librarian_load","librarian_extract",
                   "inventory","cell_map","progress_stream"],
  "cells": {"count": 126, "rows": ["FRONT","BACK"], "cols": 3, "shelves": 21,
            "serviceable": 63},
  "readers": [ {"role":"patron_card","tech":"nfc"},
               {"role":"patron_ekp","tech":"uhf"},
               {"role":"item_tag","tech":"uhf"} ] }
```
`cells.serviceable` — реально обслуживаемые ячейки (кросс-ряд — атрибут, не блокер;
пока FRONT=63/126, см. C6).

## Операции агент → Biblio
| Операция | Тело | Доменный резолв |
|---|---|---|
| `card.presented` | `{reader_role, uid}` | `ReaderService.resolve_patron(role,uid)` → `ok`/`unknown`(гость)/`ambiguous` (#417) |
| `item.detected` | `{epc}` | `catalog.find_exemplar_by_tag(db,epc)` → инв.№ (910^b) (#411) |
| `op.progress` | `{op_id, step, total, phase, msg}` | стрим фаз (WS); best-effort, истина — `op.result` |
| `op.result` | `{op_id, status: ok\|failed, step?}` | → `commit(op_id)` при ok / `rollback(op_id)` при failed |
| `device.health` | `{soft_online, ok, errors, cells_busy?, sync_queue_len?}` | `DeviceService.heartbeat` (метрики шкафа — #421) |
| `sync.replay` | `{ops:[{op,op_id,...}]}` | пакетная досдача офлайн-операций; идемпотентно по `op_id` |

## Операции Biblio → агент
| Операция | Тело | Смысл |
|---|---|---|
| `session.begin` | `{reader, entitlements, screen}` | кого обслуживаем, что показать |
| `issue.execute` | `{op_id, item, cell?}` | достать полку с книгой к окну |
| `return.accept` | `{op_id}` | принять книгу в свободную ячейку |
| `librarian.load` | `{op_id, item, cell?}` | загрузка экземпляра в ячейку |
| `librarian.extract` | `{op_id, cell}` | изъятие из ячейки |
| `inventory.run` | `{op_id, scope}` | обход ячеек + опрос меток (сверка `cabinet_cell`) |
| `cell.map.get` | — | текущее зеркало ячеек (`DeviceService.cell_map`) |

## Сага выдачи (последовательность)
1. `card.presented` → `resolve_patron` → `session.begin`.
2. Читатель выбирает экземпляр → `circ.reserve(patron, item, op_id)` → PENDING-loan (+910^A).
3. `issue.execute{op_id}` агенту → `op.progress` (фазы на экран).
4. `op.result{ok}` → `circ.commit(op_id)` (loan ACTIVE); `{failed}`/таймаут → `circ.rollback(op_id)`.
5. TTL: `circ.expire_pending(now, ttl)` авто-откатывает зависшие резервы.

## Возврат
`item.detected{epc}` → `find_exemplar_by_tag` → инв.№ → найти on-hand loan →
`return_item(loan_id)` → ячейка `awaiting_extraction` → позже `librarian.extract`.
Приём валидируется: EPC ∈ множестве меток фонда (иначе отказ — не муляж/чужое).

## Офлайн
Локальный кэш (читатели + формуляр + bloom EPC) на edge/агенте; выдача по кэшу
(известный не-должник), возврат по метке фонда; бронь — единственная только-онлайн.
При связи — `sync.replay` (идемпотентно по `op_id`).

## Реализованные доменные примитивы (что уже есть в Biblio)
- `catalog.find_exemplar_by_tag` (#411) · `circulation.checkout/reserve/commit/rollback/expire_pending` op_id (#412/#415) · `devices` tenant + `cabinet_cell` + `kind=self_service_cabinet` (#414) · `device_token` (#413) · `readers.resolve_patron` (#417).
- Сквозной прогон всего этого мок-агентом — `tests/test_bdp_e2e.py` (#418).
