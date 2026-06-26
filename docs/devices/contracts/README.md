# contracts — машиночитаемые контракты Biblio (Фаза 1)

> ⚠️ Архитектура — нативные домены Biblio, см. [DEVICES_NATIVE_ARCHITECTURE.md](../DEVICES_NATIVE_ARCHITECTURE.md) (#272). Поэтому: **OpenAPI = device-facing спецификация** (что обязан принять тонкий compat-шим, а не «сервис-клон»); **DDL** = поле-маппинг на существующие домены (own-store/catalog/circulation/holds) + по-настоящему новое — только таблицы домена `devices`.

Артефакты для постановки в разработку, выведенные из рекона.

| Файл | Что это | Источник |
|---|---|---|
| [biblio_abis_native_schema.sql](biblio_abis_native_schema.sql) | **DDL нативного ABIS-хранилища (режим 2)** — таблицы reader/reader_card/catalog_record/item/loan/reader_order/audit_log; поля = эквиваленты ИРБИС (тег в комментарии). PostgreSQL. | [EASYBOOKABIS_IRBIS_MAP.md](../EASYBOOKABIS_IRBIS_MAP.md), [TZ_PHASE1](../TZ_PHASE1_abis_device_core.md) §3 |
| [device_service_openapi.json](device_service_openapi.json) | **OpenAPI 3.0.3 сервиса устройств** — 151 операция `api.svc` + 7 device-facing `/easybookdll/*` + 106 DTO-схем. Сгенерировано из декомпиляции `WebService.cs`/DataContracts. | [CENTRAL_SERVICE_API.md](../CENTRAL_SERVICE_API.md), [CENTRAL_SERVICE.md](../CENTRAL_SERVICE.md) |
| [mock_station_spec.md](mock_station_spec.md) | **Спецификация мок-станции** (эмулятор SafeKeeper/постамата) — разработка и тест оркестрации ячеек без железа + контракт-тест Device Service | [CONTROL_CAPABILITY.md](../CONTROL_CAPABILITY.md) |

## Как использовать
- **DDL** — основа БД режима 2 (замена ИРБИС). За интерфейсом `IAbis`/`BiblioNativeBackend` операции (`Checkout/Checkin/Renew/AddReader/…`) пишут в эти таблицы по семантике [EASYBOOKABIS_IRBIS_MAP.md](../EASYBOOKABIS_IRBIS_MAP.md) §3. В режиме 1 (замена JIRBIS) таблицы не используются — `IrbisBackend` пишет в реальный ИРБИС.
- **OpenAPI** — контракт Device Service (замена `api.svc`). Открыть в Swagger UI / сгенерировать серверные стабы. Фаза 1 реализует поднабор ([TZ_PHASE1](../TZ_PHASE1_abis_device_core.md) §4) + device-facing `/easybookdll/*` для бесшовного подхвата агентов.

## Оговорки (из ревью)
- Контракт восстановлен **с клиентской стороны** — типы/имена точны; серверные коды ошибок и точные тела ответов отдельных операций требуют сетевого трейса ([OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) §4).
- Баги исходника НЕ воспроизводить: `EntranceModify` (без opID), `DesktopDeviceConfigGet` (пустое тело), `ManualGet` (поток ломается). Отмечено в OpenAPI `info.description` и [CENTRAL_SERVICE_API.md](../CENTRAL_SERVICE_API.md).
- В Biblio device-facing — TLS + токены; legacy-Basic `ServiceLogin` принимать только для бесшовного подхвата существующих агентов EasyBook.
- Заказы/бронь (`reader_order`): раскладка RQST/691 — инференс; до уточнения вести в Device Service, не в ИРБИС.
