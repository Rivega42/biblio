# DEVICES_NATIVE_ARCHITECTURE — устройства как нативные домены Biblio (каноничное)

> **Статус:** КАНОНИЧНОЕ архитектурное решение (владелец продукта, [#272](https://github.com/Rivega42/biblio/issues/272)). Заменяет «overlay»-рамку («Device Service = клон `api.svc`») в [BIBLIO_DEVICE_INTEGRATION_DESIGN.md](BIBLIO_DEVICE_INTEGRATION_DESIGN.md) и [TZ_PHASE1_abis_device_core.md](TZ_PHASE1_abis_device_core.md). Технический разбор протоколов в остальных доках остаётся в силе — меняется только **куда** это ложится.

## 1. Принцип

Всё, что дал реверс IDlogic, реализуем как **нормальные сервисы и связи ВНУТРИ Biblio**, переиспользуя существующие домены. Реконструированный контракт IDlogic (151 операция, `/easybookdll/*`, SafeKeeper-заказы, мониторинг, RFID/EAS) — это **спецификация того, что ждут физические устройства**, а НЕ чертёж второго сервиса-надстройки.

**НЕ создаём:** второй «Device Service», зеркалящий `api.svc`; копию БД IDlogic; параллельный «ABIS-порт» как отдельную надстройку над ИРБИС.

## 2. Карта: возможность IDlogic → нативный домен Biblio

| Возможность IDlogic | Нативный домен Biblio (переиспользуем) | Семантика из рекона |
|---|---|---|
| Checkout / Checkin / Renew / SetBookState | существующий движок **circulation** | поля RDR 40 + каталог 910^A/903/999 — [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) §3 |
| Статус экземпляра / RFID-тег | нативный **CatalogStore** | `910^A`=статус (BookState), `910^H/B`=RFID/штрихкод; кодек метки ISO 28560‑2 — [TAG_DATA_MODEL.md](TAG_DATA_MODEL.md) |
| Поля читателя / карты ЕКП | нативный **own-store / RDR** | 30(билет)/24(доп.карта)/28(ЕКП)/103(PIN)/10‑12/21/23/40 |
| SafeKeeper-заказы / выдача из ячейки | существующие **holds / заказы ([#222](https://github.com/Rivega42/biblio/issues/222))** | заказ в локер = бронь с pickup-местом = ячейка; состояния `1→2→3→4/6` ↔ queued→ready→fulfilled/error; ячейка = битмаска занятости |
| Реестр устройств + health + мониторинг + ExternalLog (32 типа) + ворота/EAS-события + счётчик посетителей + умные полки/СКУД | **НОВЫЙ нативный домен `devices`** (движок+схема+гранты+аудит, как circulation/acquisition) | DTO `MON_*`/`SK_*`/`SS_*`/`ACS_*`, `DeviceDataAdd` health, EventTypeID, `ExternalLogTypes` |
| Камеры / FaceID | в домен **`devices`** (драйвер Dahua) + связь с own-store (фото/идентификация читателя) | Dahua NetSDK :37777 |

## 3. Единственная «совместимость» — device-facing compat-адаптер

Тонкий **протокольный шим**, который существующие физические устройства/агенты (TagService, станции) уже умеют вызывать, и который **переводит** их вызовы в нативные сервисы Biblio. Это адаптер, НЕ система-источник.

- **Принимает** (то, что устройства шлют): `/easybookdll/*` (`IsServerAlive`, `LibraryInfoGet`, `ReaderInfoGet`, `ReaderModify`, `DeviceIsLicenseValid`, `DeviceDataAdd`, `BooksCacheAddUpdate`) + station-facing вызовы (заказы/ячейки/мастер-ключи/health) — с унаследованным Basic `ServiceLogin` (для бесшовного подхвата).
- **Транслирует** в нативные домены:
  - `ReaderInfoGet/ReaderModify` → own-store/RDR;
  - `DeviceDataAdd`/health/события → домен `devices`;
  - заказы/ячейки SafeKeeper → holds (#222);
  - выдача/возврат с устройства → circulation.
- **Сокет :6001** настольного считывателя и **WebSocket** для портала — часть Reader Agent, тоже шим к нативным сервисам.
- Полный перечень эндпоинтов, которые шим обязан принять, — [contracts/device_service_openapi.json](contracts/device_service_openapi.json) (теперь читается как **device-facing спецификация**, а не «наш сервис-клон»).

## 4. Новый домен `devices` (что в нём)

Единственный по-настоящему новый домен (остальное — переиспользование). По образцу существующих движков (circulation/acquisition): схема + движок + гранты + аудит.
- **Сущности:** устройство (`device`, тип, библиотека, online, health), данные/метрики (`device_data` — soft/ok/error), события (`device_event`, тип/сообщение/время), ворота+EAS-события+счётчик, умные полки (инвентаризация), СКУД (проход/зона/направление), камеры/FaceID, баннеры станций.
- **Связи:** устройство ↔ библиотека/МХ; событие выдачи ↔ circulation; локер-заказ ↔ holds (#222); фото/идентификация ↔ own-store.
- **Аудит:** `ExternalLogTypes` (32 типа) → нативный аудит домена.
- **НЕ** копия БД IDlogic: моделируем по нашим правилам; контракт IDlogic — лишь источник требований.

## 5. Режимы (это backend существующего circulation, не отдельная штука)
- **Замена ИРБИС:** circulation/catalog/own-store — нативные (своя БД). Поля = семантика ИРБИС из рекона.
- **Замена JIRBIS:** тот же circulation-движок в backend-режиме «клиент ИРБИС» (пишет в реальный `irbis_server`). Переключение — конфиг backend домена circulation, а не отдельный сервис.

## 6. Место в ген-линии
Входит **узлом** после auth + режимов + cutover; строится поверх уже валидированных на staging **own-store/circulation**. Сначала переиспользование (circulation/catalog/holds/own-store), затем новый домен `devices`, затем compat-адаптер, затем станционная Фаза 3.

## 7. Фазы (переформулированы под нативную архитектуру)
1. **Фаза 1:** circulation (выдача/возврат/продление/регистрация — оба backend-режима) + CatalogStore (910^A/H/B + ISO 28560‑2) + own-store/RDR (30/24/28/103) + **Reader Agent** (настольный считыватель) + **device-facing шим** для бесшовного подхвата TagService.
2. **Фаза 2:** домен `devices` наполняется — ТСД (хранение фонда), ворота (EAS-события), камеры (FaceID/счётчик); связи с circulation/own-store.
3. **Фаза 3:** станции/постаматы/SafeKeeper через holds (#222) + домен `devices` + compat-адаптер; станционные эндпоинты по реконструированной модели, тест на [мок-станции](contracts/mock_station_spec.md); финальная сверка station-facing вызовов трейсом/станционным билдом — но результат ложится в домен `devices`, **не в отдельный силос**.

## 8. Что меняется в уже сделанных артефактах
- [contracts/device_service_openapi.json](contracts/device_service_openapi.json) — теперь **device-facing спецификация** (что обязан принять compat-шим), не «сервис-клон».
- [contracts/biblio_abis_native_schema.sql](contracts/biblio_abis_native_schema.sql) — таблицы reader/item/loan/order = **поле-маппинг на существующие домены** (own-store/catalog/circulation/holds), а НЕ новая параллельная схема; по-настоящему новое — только таблицы домена `devices` (`device/device_data/audit_log`).
- [mock_station_spec.md](contracts/mock_station_spec.md) — тестирует нативный поток через compat-шим (holds + devices), не «второй сервис».
- [TZ_PHASE1_abis_device_core.md](TZ_PHASE1_abis_device_core.md) / [BIBLIO_DEVICE_INTEGRATION_DESIGN.md](BIBLIO_DEVICE_INTEGRATION_DESIGN.md) — «Device Service» читать как «домен `devices` + compat-шим»; «ABIS-порт» — как backend-абстракция существующего circulation.

> Итог: один связный Biblio — нативные circulation/catalog/holds/own-store + новый домен `devices` + тонкий device-facing compat-адаптер. Никакого зеркала IDlogic надстройкой.
