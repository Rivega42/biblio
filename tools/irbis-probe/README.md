# irbis-probe — эмпирический клиент протокола ИРБИС64 (:6666)

Инструменты Прохода Б: сняли реальный проводной протокол с живого сервера и собрали минимальный боевой адаптер. Находки → [`../../docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md`](../../docs/recon/deep/reference/protocol/WIRE_PROTOCOL.md).

| Файл | Назначение |
|---|---|
| `irbis_client.py` | **Минимальный адаптер `IrbisClient`**: connect/disconnect, `max_mfn`, `search`, `read_record`, `format_record` (рендер серверным PFT). Запись (`_execute('D', …)`) — см. demo_write. |
| `probe.py` | Сырой зонд: REGISTER/NOP/MAXMFN/SEARCH/UNREGISTER, дамп байт. |
| `demo_read.py` | Демо: connect → search → read полей → render `@brief`/`@`. |
| `demo_write.py` | Демо записи (БЕЗОПАСНО, в служебную БД `WORK`): create → read-back → logical delete. |
| `cleanup.py` | Логически удаляет тестовые записи `PROHOD_B_TEST` из `WORK`. |

## Запуск
```
py tools\irbis-probe\demo_read.py     # чтение + рендер (read-only)
py tools\irbis-probe\demo_write.py    # запись в WORK (с откатом)
```
Результаты пишутся в `*_results.txt` (UTF-8; **gitignored** — содержат ANSI-артефакты профиля).

## Безопасность
- Логин/пароль сервера передаются как аргументы скрипта/в коде демо — **боевые креды держать в `.env`, не коммитить**.
- Демо записи работает только в служебной `WORK`, публичный каталог не трогает.
- Подключение read-only по умолчанию; запись — только в demo_write/cleanup.

## Подтверждено на живом сервере
Соединение (одно TCP на запрос, сессия по `client_id`) · поиск · чтение полей/подполей (`^`) · серверный рендер PFT · запись/правка/удаление полей · числовые коды (`0`/`-140`/`-603`/`-3337`/`-3338`).
