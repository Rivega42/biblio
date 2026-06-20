# irbis-web — P0 (ядро + читательский поиск)

Минимальный боевой каркас веб-замены ИРБИС. **Backend читает реальные данные с живого сервера ИРБИС64** через адаптер, снятый в Проходе Б (см. [`../docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md`](../docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md)). Проектные контракты — [`../docs/build/P0_BUILDKIT_web-irbis.md`](../docs/build/P0_BUILDKIT_web-irbis.md).

## Статус P0 (проверено на живом `:6666`, БД IBIS)
- ✅ Соединение/сессия, `health` (версия сервера `2022+`, maxmfn 394).
- ✅ Поиск: `K=` (ключевые), `A=`/`T=` (автор/заглавие, авто-усечение `$`), `V=` и любой `expr`.
- ✅ Запись: структурированное чтение полей/подполей (разделитель `^`) → JSON.
- ✅ Рендер: серверный PFT (`@brief`) → готовое БО.
- ✅ Демо-страница читателя (`/`): поиск → список → карточка записи.

## Запуск (без установки зависимостей — stdlib Python 3)
```
cp irbis-web/.env.example irbis-web/backend/.env   # вписать IRBIS_USER/PASS
py irbis-web/backend/server.py                     # http://127.0.0.1:8080
py irbis-web/backend/smoke.py                       # самопроверка слоя IRBIS (без HTTP)
```

## API (конверт `{ok, data}` | `{ok:false, error:{code,message}}`)
| Метод | Назначение |
|---|---|
| `GET /api/health` | сервер, версия, maxmfn |
| `GET /api/search?db&prefix&q&page&pageSize` (или `&expr=`) | поиск: total + краткие БО (серверный PFT) |
| `GET /api/record/{db}/{mfn}` | запись: поля/подполя (структура) + `brief` |
| `GET /api/render/{db}/{mfn}?fmt=@brief` | серверный рендер PFT |
| `GET /` | демо-страница читателя |

## Структура
```
irbis-web/
├─ .env.example
├─ backend/
│  ├─ server.py            # HTTP API (stdlib) + демо-страница
│  ├─ smoke.py             # самопроверка слоя IRBIS на живом сервере
│  ├─ config.py            # конфиг из .env (секреты не в коде)
│  ├─ requirements.txt     # stdlib; prod-порт на aiohttp — опц.
│  └─ irbis/               # ⭐ переиспользуемый слой протокола (Проход Б)
│     ├─ client.py         #   синхронный IrbisClient (connection-per-request)
│     ├─ parser.py         #   запись -> поля/подполя
│     └─ session.py        #   потокобезопасная сессия (1 client_id, lock, reconnect)
└─ (frontend/ React+TS — следующий шаг, по TZ_ClaudeDesign_UI)
```

## Безопасность
- Креды только в `irbis-web/backend/.env` (**gitignored**), не в коде/репозитории.
- Ответы об ошибках без внутренних деталей; `-3338`(нет доступа) → HTTP 403.
- Слой read-only по умолчанию; запись (`update_record`) — отдельный метод под гранты записи.

## Дальше (по P0_BUILDKIT / issues)
- Порт HTTP-слоя на **aiohttp**; PostgreSQL для сотрудников/грантов/аудита (Access-набор, #34).
- **Frontend** React+TS+Tailwind по [`../docs/design/TZ_ClaudeDesign_UI.md`](../docs/design/TZ_ClaudeDesign_UI.md) (#33).
- Эндпоинты `terms` (автодополнение по словарю), `order`/ЛК, файлы/полный текст через прокси.
- Боевые базы пилота (СПб ГТБ): префиксы `[SEARCH]`, PFT, рабочие листы.
