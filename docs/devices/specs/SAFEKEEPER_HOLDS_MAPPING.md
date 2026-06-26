# Маппинг SafeKeeper-заказов на holds (#222) (3/3)

> Locker‑заказ (постамат/SafeKeeper) = **бронь читателя (#222)** с pickup‑местом = ячейка. Переиспользуем `access/holds.py` (`HoldService`, `reader_hold`), а не заводим отдельную сущность заказов. Рамка — [DEVICES_NATIVE_ARCHITECTURE.md](../DEVICES_NATIVE_ARCHITECTURE.md) (#272).
> Связанные: [DOMAIN_DEVICES_SPEC.md](DOMAIN_DEVICES_SPEC.md) (1/3), [COMPAT_ADAPTER_CONTRACT.md](COMPAT_ADAPTER_CONTRACT.md) (2/3). Семантика заказа из рекона — [DEVICE_CONTROL_MAP.md](../DEVICE_CONTROL_MAP.md) §7.3, [LAS_FUNCTION_MAP.md](../LAS_FUNCTION_MAP.md) §2.2.

## 1. Концепция
`holds.py` уже моделирует бронь читателя на экземпляр (`reader_hold`, статусы `ready/queued/cancelled`, FIFO‑очередь, pickup‑shelf TTL). **Locker‑заказ = такая бронь + место выдачи = ячейка камеры**. Это расширение holds, а не новый домен.
> `holds.py` хранит брони в нашем access‑сторе (не пишет в живой ИРБИС; боевая RQST/910 — отдельный TODO `core.order`). Значит в **режиме замены ИРБИС** locker‑заказ полностью нативен; в **режиме замены JIRBIS** списание при выдаче идёт в ИРБИС через backend circulation.

## 2. Расширение схемы (рядом с reader_hold)
Таблица‑компаньон 1:1 к брони (или доп. колонки в `reader_hold` — на усмотрение владельца holds):
```sql
CREATE TABLE locker_order (
  hold_id      BIGINT PRIMARY KEY REFERENCES reader_hold(id) ON DELETE CASCADE,
  safekeeper   BIGINT NOT NULL REFERENCES device(id),   -- камера (домен devices)
  cell_no      INT,                                      -- номер ячейки (физический)
  cell_shift   INT DEFAULT 0,                            -- CellNumberShifted = cell_no - cell_shift
  state        INT NOT NULL DEFAULT 1,                   -- см. §3 (1..4/6)
  staffed_by   BIGINT,                                   -- кто укомплектовал (own-store/staff)
  master_rfid  TEXT,                                     -- мастер-ключ при сервисном открытии
  abis_error   TEXT                                      -- причина state=6
);
CREATE TABLE locker_order_item (
  id BIGSERIAL PRIMARY KEY,
  hold_id    BIGINT REFERENCES reader_hold(id) ON DELETE CASCADE,
  book_code  TEXT, book_rfid TEXT,
  verified   INT DEFAULT 0, processed INT DEFAULT 0
);
```

## 3. Машина состояний (IDlogic ↔ holds)

| IDlogic OrderStateId | Смысл | Наше состояние (holds + locker_order.state) | Действие |
|---|---|---|---|
| `1` Создан | заказ создан, тело пустое | `reader_hold` `queued`/draft; `locker_order.state=1` | `HoldService.place(...)` + создать locker_order |
| `2` Подготовлен | тело наполнено книгами | `state=2`; позиции в `locker_order_item` | наполнение тела |
| `3` Укомплектован | книги в ячейке, готов к выдаче | `reader_hold` `ready`; `state=3`; ячейка занята | staffed: занять ячейку, `ready_at` |
| `4` Выдан | читатель забрал | `reader_hold` fulfilled; `state=4`; ячейка свободна | pickup → `CirculationEngine.checkout` |
| `6` Выдан‑с‑ошибками | забрал, но запись в АБИС не прошла | `state=6` (fulfilled + `abis_error`) | повтор списания из портала |
| opID `0` (отмена/удаление) | отменён | `reader_hold` `cancelled` | освободить ячейку |

> «Подготовлен/Укомплектован» (1→2→3) — наполнение и размещение в ячейку (staff/мастер‑ключ на камере). «Выдан» (3→4) — читатель приложил карту → выдача через **circulation** (loan + 910^A). Ошибка АБИС → `6`.

## 4. Ячейки и занятость
- **Источник истины — holds:** ячейка занята ⇔ существует активный `locker_order` (state 3) в ней на данной `safekeeper`. Отдельную «битмаску» внутри не храним.
- **Совместимость:** compat‑шим **отдаёт** legacy‑клиентам `CellsState` (long битмаска) — вычисляет как `OR(1<<cell_no)` по занятым ячейкам камеры (формат `BindingCells`, [CONTROL_CAPABILITY.md](../CONTROL_CAPABILITY.md)). Свободные для нового заказа — `StationTypeID∈{3,4} && !busy`.
- `cell_no`/`cell_shift`: наружу — `CellNumberShifted = cell_no - cell_shift` (как в LAS).

## 5. Мастер‑ключ и сервисные открытия
- Мастер‑ключ = `device_master_rfid` (домен `devices`), привязан к камере. Валидация при сервисном открытии; событие — `device_event` (+ аудит, тип из `ExternalLogTypes`: MasterRFIDAdded/…).
- Сервисное открытие ячейки/укомплектование — событие истории (вкладка «Администратор» в LAS), пишем в `device_event` с `hold_ref`.

## 6. Выдача при получении (pickup → circulation)
1. Читатель/карта на камере → шим вызывает `HoldService` (найти ready‑hold читателя на этой камере) → `CirculationEngine.checkout(reader, item)`.
2. Успех → `locker_order.state=4`, `reader_hold` fulfilled, ячейка освобождается, `device_event(loan_ref)`.
3. Ошибка списания (режим JIRBIS, ИРБИС вернул ошибку) → `state=6`, ячейка освобождена, портал предлагает повтор.

## 7. Связи и переиспользование (итог)
- **holds (#222)** — жизненный цикл заказа/брони, очередь, pickup‑TTL.
- **circulation** — выдача при получении (loan, 910^A, правила/долги).
- **devices** — камера (`device`), мастер‑ключи, события/health, и `CellsState` наружу через шим.
- **own‑store/RDR** — читатель/карта/ФИО заказа.
- **catalog** — экземпляр/RFID‑тег (910^A/H/B).

Никакой отдельной «таблицы заказов IDlogic»: заказ = бронь (#222) + `locker_order` поверх неё.
