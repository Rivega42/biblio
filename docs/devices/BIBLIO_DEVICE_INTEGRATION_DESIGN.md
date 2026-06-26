# BIBLIO_DEVICE_INTEGRATION_DESIGN — архитектура работы Biblio со всеми устройствами

> **Контекст:** Biblio заменяет **JIRBIS** и выступает **интерфейсом ИРБИС** (сам `irbis_server` остаётся бэкендом, мы — его клиент). При этом **заменяем стек IDlogic целиком**: Biblio = и читательский/служебный портал, и **сервис устройств** (вместо центрального `api.svc` + локальных агентов EasyBook). Добавляем **Android ТСД** (ручной UHF-терминал) для хранения фонда.
> **Опора:** весь рекон в этой папке — см. [README.md](README.md). Это мост «рекон → реализация», не эмуляция сервера ИРБИС.
> **Статус:** проектный черновик. Решения по железо-зависимым классам — в [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## 1. Позиционирование и общая схема

Biblio играет **две роли одновременно**:
- **A. Интерфейс ИРБИС** (замена JIRBIS): читательский портал + рабочие места персонала. Внутри — **ABIS-адаптер** = клиент `irbis_server` (как ManagedClient), реализующий полевую модель выдачи/регистрации.
- **B. Сервис устройств** (замена IDlogic `api.svc` + агентов): держит БД парка, принимает отчёты устройств, оркеструет сценарии, а саму выдачу пишет в ИРБИС через роль A.

```
 Читатели / персонал                         Устройства / агенты Biblio
        │                                              │
        ▼                                              ▼
 ┌─────────────────────────── BIBLIO ───────────────────────────┐
 │  A. Портал/АРМ (замена JIRBIS)   B. Сервис устройств (api)    │
 │        └─────────── ABIS-адаптер (клиент ИРБИС) ──────────────┼──TCP:6666──▶ irbis_server
 │                                                               │   (RDR/RQST/каталог) [ОСТАЁТСЯ]
 └───────────────────────────────────────────────────────────────┘
        ▲ локальные мосты (COM/USB/PCSC/SDK)        ▲ REST/JSON (устройства рапортуют)
 ┌──────┴──────┬──────────┬───────────┐    ┌────────┴─────────┬───────────┬──────────┐
 │ Reader Agent│ Gate Agent│ Vision    │    │ Станции/постаматы│ Умные полки│ СКУД      │
 │ (настольный)│ (ворота)  │ (Dahua)   │    │ (прошивка)       │ (прошивка) │           │
 │ ТСД (Android)│          │           │    └──────────────────┴───────────┴──────────┘
 └─────────────┴──────────┴───────────┘
```

## 2. Компоненты Biblio

| Компонент | Роль | Заменяет | Опора в реконе |
|---|---|---|---|
| **ABIS-адаптер** | клиент `irbis_server`: выдача/возврат/продление/регистрация/поиск | `EasyBookAbis` (IRBIS-ветка) | [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) |
| **SIP2-адаптер** (опц.) | если развёртывание требует SIP2 вместо прямого ИРБИС | `EasyBookAbis.SIP2` | [EASYBOOKABIS_SIP2_MAP.md](EASYBOOKABIS_SIP2_MAP.md) |
| **Device Service (API)** | REST/JSON сервис парка + БД устройств + приём отчётов | центральный `api.svc` | [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md), [CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md) |
| **Reader Agent** (Windows) | локальный мост к настольному считывателю (COM/USB/PCSC), EAS, Danish/EPC, ЕКП | `EasyBook TagService` | [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md), [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §2,§4 |
| **Biblio Mobile (ТСД, Android)** | UHF-терминал: инвентаризация/привязка/перемещение фонда | мобильный модуль IDlogic | [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §2 (Chainway R3/UHFAPI), §7.6 |
| **Gate Agent** | ворота: COM, EAS_Set/Reset/Alarm, события | `RFID_ANTIVOR_ActiveX` | [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §5 |
| **Vision** | камеры Dahua: FaceID, счётчик посетителей | Dahua-интеграция LAS | [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §6 |
| **Адаптеры станций/локеров/полок** | мост к прошивке постаматов/SafeKeeper/полок | прошивка станций | 🔴 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1–3 |

## 3. Роль A — ABIS-адаптер (мы интерфейс ИРБИС)

Реализуем поднабор клиента ИРБИС, который надстройка использовала (мы это уже разобрали построчно). Минимум операций:
- **Сессия:** регистрация `arm=B` (книговыдача) и `arm=C` (каталог), keep-alive, реконнект.
- **Поиск:** `RI=`, `GUID=`, `MDPASP=`, `H=` (RDR); `IN=`/`I=` (каталог); `V30:'…' and V910^H<>''`, `V691^…`; `MFN>n AND MFN<=m`.
- **Чтение/запись** RDR и каталога с подполями ([EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) §2).
- **Операции:** Checkout (RDR 40 + каталог 910^A=1 + 999++), Checkin (40^F/^2/^R + 910^A=0), Renew (40^L/^E), SetBookState (910^A=enum), регистрация (полный набор RDR + ЕКП поле 28 / карта поле 30 / доп.карта поле 24), GetDocInfo/GetDocState/GetClientChargedDocs/GetUserDebts/GetBookCenz.
- **PFT/INI:** `@brief`, `@cenz`, `ReturnRightsPft`/`ReaderRightsPft`, `MaskMrg`, `BIBSIGLA`, `READERHISTORY`, `PRIVATE/MZ`, `rzn.mnu`.

> Это «портал как интерфейс ИРБИС»: читатель в Biblio видит формуляр/заказы/штрафы, оформляет бронь — а записи идут в реальный `irbis_server`.

## 4. Роль B — Device Service (замена api.svc)

REST/JSON сервис (взять контракт из [CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md)):
- **Админ/чтение/CRUD** парка: операции `*Get/*Modify/*Set` по классам (Stations/SafeKeeper/SmartShelf/Gates/ACS/Devices/Readers/KPI/Banners/Update) и DTO (`MON_*`, `SK_*`, `SS_*`, `ACS_*`, …).
- **Приём отчётов от устройств** (обратный канал): устройства/агенты POST'ят своё состояние/события в формате DTO (`MON_DeviceData` health, `MON_Station` узлы, `MON_GateEASEvent`, `SK_SafeKeeper.CellsState`, `SS_BookOnShelf`, `ACS_Event`).
- **Устройство-facing совместимость** (чтобы существующие агенты/устройства можно было перенаправить на Biblio без переустановки): эндпоинты-эквиваленты `/easybookdll/{IsServerAlive, LibraryInfoGet, ReaderInfoGet, ReaderModify, DeviceIsLicenseValid, DeviceDataAdd, BooksCacheAddUpdate}`.
- **Связка с ИРБИС:** все circulation-эффекты (выдача из станции/постамата) сервис выполняет через роль A (ABIS-адаптер), не дублируя БД ИРБИС.
- **Безопасность (улучшаем относительно IDlogic):** TLS, токены/ключ-на-устройство вместо общего Basic, без захардкоженных кред (см. [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) §7).

## 5. Поустройственная спецификация

### 5.1 Настольный RFID-считыватель (персонал/портал-киоск) — ✅ воспроизводимо
- **Мост:** `Biblio Reader Agent` (Windows-служба) драйвит считыватель по COM/USB/TCP/PCSC; абстракция «открыть/прочитать метки/EAS get-set/мощность/звук» — как нативное ядро (`IsReaderOnline/RfidReadDataByCfg/RfidEASGet/Set/RfidDM15*/ReaderPower*`). Можно временно переиспользовать `EasyBook_RFid.dll`, цель — свой драйвер.
- **Канал в портал:** локальный **WebSocket/сокет** (протокол как :6001: команды чтения UID/запись EAS — [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) §4) **или** режим SendChar (ввод кода в активное поле). Для веб-портала предпочтителен WebSocket-агент на localhost.
- **Метка:** ISO 15693 + Danish (ISO 28560) для HF, EPC для UHF; EAS/AFI — [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §4.
- **ЕКП:** контактный считыватель через `EkpMed.dll` (или аналог) — авторизация → `GetPersID/GetPersData/GetPhoto`.

### 5.2 Android ТСД (ручной UHF-терминал) — ✅ воспроизводимо (нужен SDK терминала)
- **Приложение:** нативное Android-приложение Biblio. UHF-чтение через SDK терминала (Chainway/Urovo; в стеке уже Chainway R3 → `UHFAPI`/`IDlogicR3API`). Инвентаризационный режим — массовое чтение EPC.
- **Сценарии (Хранение фонда):** привязка книг к ячейке/полке, инвентаризация (найдено/не найдено/перемещено/новая), перемещение. Логика и статусы — `BookInvStates` (New/Found/NotFound/NotOnPlace/Unknown), [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md) §2.6.
- **API:** Device Service REST — `BookKeepingBookInfoGet`, `BookKeepingBookToCellBind`, `BookKeepingHistoryAdd`, `BooksOnCellGet`, иерархия `BookCase/Section/Shelf/Cell` ([CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md)). Неизвестная книга → дотянуть из каталога ИРБИС (`GetDocInfo`) → `BookToLibBooksAdd`.
- **Идентификатор:** EPC-код экземпляра ↔ инв.номер/штрихкод (поле каталога), мэппинг в Device Service.

### 5.3 Противокражные ворота — ✅ воспроизводимо
- `Gate Agent`: COM (Andea R-Pan/FEIG), цикл инвентаризации + `RfidEASGet`; тревога → событие в Device Service (`MON_GateEASEvent{UID,BookCode,...}`); счётчик вход/выход (`CounterIP:Port`) → `MON_GateCounter`. Реле сирены — `SetOutput` ([DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) §5).

### 5.4 Камеры / FaceID / СКУД — ✅ если Dahua
- `Vision`: Dahua NetSDK (TCP :37777) — логин к камере/NVR, `DetectFace` → распознавание → резолв читателя (`ReaderInfoGet` по UserID) → формуляр/выдача через роль A; счётчик посетителей (`VisitorsGet`). СКУД: стационарные считыватели/антенны → события прохода (`ACS_Event`).

### 5.5 Станции самообслуживания (киоски книговыдачи) — ⚠️ частично
- Сценарий книговыдачи на станции: идентификация читателя (карта/ЕКП/лицо) → набор книг по RFID → `Checkout` через роль A → `UnsetEas`. Эту **логику** Biblio реализует.
- **Блокер:** механика станции (чековый принтер, конвейер/выдача) — прошивка станции; нужен её SDK/протокол (узлы `IsPrinterOk/IsConveyorOk/IsControllerOk` — [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) §5).

### 5.6 SafeKeeper / постаматы (бронирование с выдачей в ячейку) — 🔴 блокер на «железе»
- Сценарий брони Biblio реализует целиком (заказ, состояния Создан→Подготовлен→Укомплектован→Выдан, мастер-ключ, связка с RQST/выдачей через роль A).
- **Блокер:** физическое **открытие ячейки** — в контроллере камеры/постамата; нужен его протокол (реле/RS485/соленоид). Без этого — учёт без привода ([OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1).

### 5.7 Умные полки — ⚠️ блокер на контроллере
- Полка рапортует RFID-инвентаризацию в Device Service (`BooksOnShelfGet` DTO). Нужен wire-протокол контроллера полки (прошивка).

## 6. Что реплицируемо сейчас vs что требует доступа к железу

| Готовность | Классы | Что нужно |
|---|---|---|
| ✅ Сейчас | ABIS-адаптер (вся выдача/регистрация), Device Service API+DTO, настольный считыватель, ворота, Android ТСД, FaceID/Dahua | — (всё разобрано в реконе) |
| ⚠️ Логика да, механика нет | станции самообслуживания | SDK/протокол станции (принтер/конвейер) |
| 🔴 Блокер | привод ячеек SafeKeeper/постаматов, wire-протокол умных полок | контроллер/прошивка станции + доступ к стенду |

## 7. Фазы внедрения (предложение)

1. **Фаза 1 (ядро, без зависимости от чужого железа):** ABIS-адаптер (роль A) + Device Service (роль B, схема БД и API) + Reader Agent (настольный считыватель) + портал-замена JIRBIS. → полноценная книговыдача/возврат/формуляр/регистрация + настольный RFID.
2. **Фаза 2 (мобильность и периметр):** Android ТСД (Хранение фонда) + Gate Agent (ворота) + Vision (FaceID/счётчик). → инвентаризация фонда, противокражка, идентификация по лицу.
3. **Фаза 3 (станционное железо):** интеграция станций самообслуживания и SafeKeeper/постаматов и умных полок — после получения протоколов/SDK станций (см. OPEN_QUESTIONS). До этого — режим учёта/мониторинга.

## 8. Безопасность (заложить сразу, не повторять ошибки IDlogic)
- TLS на Device Service и устройство-facing API; токен/ключ на устройство вместо общего Basic.
- Никаких захардкоженных паролей/AES-ключей в клиентах (у IDlogic это есть — [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) §7); секреты — в защищённом хранилище/`.env`.
- Креды ИРБИС/камер — из конфигурации, ротация (реестр секретов стенда — локально, вне гита).

## 9. Открытые вопросы для этого плана
- Протоколы станций/локеров/полок (прошивки) — [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §1–3.
- Конкретная модель Android-ТСД и её UHF-SDK (Chainway/Urovo?) — определить целевое устройство.
- Точная раскладка байт ISO 28560/Danish внутри блоков метки (для побайтовой совместимости с уже промаркированным фондом) — [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §8 (можно закрыть декомпиляцией Delphi-ядра `EasyBook_RFid.dll`).
