# Реконструкция надстройки управления устройствами (IDlogic Admin Server / EasyBook)

Картография ПО управления внешними оконечными устройствами библиотеки поверх САБ ИРБИС64 — **IDlogic Library Admin Server (LAS)** + агент **EasyBook TagService**, распакованного в `C:\IRBIS64\Library Admin Server\`. Метод: статический анализ + полная C#‑декомпиляция (бинарники не запускались).

## С чего начать
1. [DEVICE_INVENTORY.md](DEVICE_INVENTORY.md) — что за поставка, реестр всех файлов.
2. [DEVICE_CONNECTION_MAP.md](DEVICE_CONNECTION_MAP.md) — кто к кому подключается ([схема](assets/connection_map.svg)).
3. [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) — как драйвится каждый класс устройств.

## Все документы
| Документ | О чём |
|---|---|
| [DEVICE_INVENTORY.md](DEVICE_INVENTORY.md) | Реестр файлов: модули, SDK устройств, драйверы, конфиги, логи |
| [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) | Управление по классам: RFID‑считыватели (вендоры/протоколы/команды), модель метки ISO 28560/Danish + EAS/AFI, ворота, Dahua/FaceID, REST‑контракт api.svc |
| [DEVICE_CONNECTION_MAP.md](DEVICE_CONNECTION_MAP.md) | Топология подключений + потоки запросов (кто кому что шлёт), `[✓]` подтверждено / `[~]` инференс |
| [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) | Обзор связок с ИРБИС/SIP2 + чек‑лист репликации для Biblio |
| [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) | Как устроен центральный сервис `api.svc` (REST/JSON+Basic) и как он общается с устройствами |
| [CENTRAL_SERVICE_API.md](CENTRAL_SERVICE_API.md) | Приложение: 151 операция (route→тело→ответ) + полные схемы всех 106 DTO |
| [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md) | Карта функций панели администратора: модули/страницы/методы, enum'ы, FaceID |
| [TAGSERVICE_FUNCTION_MAP.md](TAGSERVICE_FUNCTION_MAP.md) | Карта функций агента считывателя: P/Invoke, сокет‑протокол :6001, ИРБИС, ЕКП |
| [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) | Построчно: точные поля ИРБИС (RDR 40, каталог 910/903/999) для Checkout/Checkin/Renew/AddReader/AddEkp |
| [EASYBOOKABIS_SIP2_MAP.md](EASYBOOKABIS_SIP2_MAP.md) | Построчно: SIP2‑клиент — кадры 93/99/63/17/11/09/15/29, коды полей, чек‑сумма |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | Пробелы и нужный стенд/доступы |
| [BIBLIO_DEVICE_INTEGRATION_DESIGN.md](BIBLIO_DEVICE_INTEGRATION_DESIGN.md) | **Проект:** как Biblio (два режима: замена JIRBIS / замена ИРБИС) полноформатно работает со всеми устройствами + Android ТСД через ABIS‑порт; замена стека IDlogic |
| [TZ_PHASE1_abis_device_core.md](TZ_PHASE1_abis_device_core.md) | **ТЗ Фаза 1:** контракт IAbis, нативная БД (режим 2), эндпоинты Device Service, протокол Reader Agent; разделы «бесшовный подхват устройств» и «покрытие интерфейсов сотрудников» |
| [contracts/](contracts/) | **Контракты для разработки:** [DDL режима 2](contracts/biblio_abis_native_schema.sql) + [OpenAPI Device Service](contracts/device_service_openapi.json) (151 операция + 106 DTO) |
| [REVIEW_NOTES.md](REVIEW_NOTES.md) | Протокол ревью документации против декомпиляции + список исправлений |

## Ключевые выводы
- **Архитектура:** три центра — ИРБИС64 (`:6666`, читатели/выдача), центральный сервис IDlogic (`api.svc :8005`, парк устройств), локальные шины (COM/USB/PCSC/Dahua).
- **Реплицируемо «по проводу» уже сейчас:** настольный считыватель, противокражные ворота (COM/EAS), камеры Dahua, интеграция с ИРБИС/SIP2, модель данных метки.
- **🔴 Блокер:** физический привод ячеек постаматов/SafeKeeper в этих бинарниках отсутствует — он в прошивке станций (см. OPEN_QUESTIONS §1).
- **Интеграция с ИРБИС:** прямой TCP (`arm=B/C`) или SIP2. Бронирование через ИРБИС — заглушка (`Hold()→false`); заказы идут через центральный сервис.

## Безопасность
Найденные креды/ключи **в репозиторий не вынесены** — помечены `секрет → .env`; реестр секретов лежит локально вне гита (`SECRETS_INVENTORY.local.md`, gitignored). ПДн читателей не обнаружены. Декомпилированный код и дампы строк — в `_scratch_devices/` (gitignored).
