# DLL_API_EXTRACTED — экспортируемый API ИРБИС64 (реверс DLL)

> Снято из бинарей `C:\IRBIS64\irbis64_client.dll` (439 КБ) и `IRBIS64.dll` (975 КБ) через `pefile` (см. `irbis-web/backend/re_dll.py`). Обе — **32-битные Delphi** (секции CODE/DATA/BSS, импорт RTL). Это **таблицы экспортов = канонический API** (имена функций); тела функций (алгоритмы) бинарны — для псевдокода нужен Ghidra/IDA (не установлены). Заполняет «DLL-внутреннюю логику», которой нет в INI. Дополняет [PROTOCOL_REFERENCE](./).

## 1. `irbis64_client.dll` — КЛИЕНТСКИЙ протокольный API (75 функций `IC_*`)
Это то, что клиент шлёт серверу по TCP (импорт `wsock32.dll`). Протокол-маркеры в строках: **`IRBIS_START_REQUEST` / `IRBIS_END_REQUEST` / `IRBIS_BINARY_DATA`**, `User-Agent: GPNTB/Irbis64`, веб-шлюз `/cgi-bin/wwwirbis.exe`.

**Сессия/регистрация:** `IC_reg · IC_unreg · IC_set_blocksocket · IC_set_client_time_live · IC_set_show_waiting · IC_set_webserver · IC_set_webcgi · IC_update_ini · IC_clearresourse · IC_nooperation`
**Запись (read/write):** `IC_read · IC_readformat · IC_record_sformat · IC_update · IC_updategroup · IC_updategroup_sinhronize · IC_ifupdate · IC_recdel · IC_recundel · IC_recunlock · IC_recdummy · IC_changemfn · IC_getmfn · IC_maxmfn · IC_nfields · IC_field · IC_fieldn · IC_fldadd · IC_fldrep · IC_fldempty · IC_fldtag · IC_isActualized · IC_isDeleted · IC_isLocked · IC_isbusy`
**Поиск/словарь:** `IC_search · IC_searchscan · IC_getposting · IC_posting · IC_postingformat · IC_postinggroup · IC_nexttrm · IC_prevtrm · IC_nexttrmgroup · IC_prevtrmgroup · IC_nocc · IC_stat`
**Форматирование:** `IC_sformat · IC_sformatgroup · IC_print`
**Глобальная корректировка:** `IC_gbl · IC_gbl_ex`
**Ресурсы (файлы/.pft/.mnu с сервера):** `IC_getresourse · IC_getresoursegroup · IC_getbinaryresourse · IC_getbinaryresourse_standart · IC_putresourse · IC_reg`
**Администрирование сервера** (закрывает 🟡 из ADMIN_FUNCTIONS): `IC_adm_newdb · IC_adm_dbdelete · IC_adm_dbempty · IC_adm_DBStartCreateDictionry · IC_adm_DBStartReorgDictionry · IC_adm_DBStartReorgMaster · IC_adm_DBunlock · IC_adm_DBunlockMFN · IC_adm_getClientlist · IC_adm_getClientslist · IC_adm_SetClientslist · IC_adm_getProcessList · IC_adm_getDeletedList · IC_adm_getallDeletedLists · IC_adm_restartserver`

> Наш бэкенд `core.py`/`SessionManager` уже реализует подмножество (search/read/update/terms/gbl/file) — этот список **полный контрольный** для паритета протокола.

## 2. `IRBIS64.dll` — ДВИЖКОВЫЙ API сервера (72 функции `Irbis*`)
Низкоуровневые примитивы БД/индекса/формата (импорт `wininet.dll` — веб-функции).

**Мастер-файл/запись:** `Irbisinit · IrbisinitNewDB · Irbisinitmst · Irbisclose · Irbisclosemst · IrbisRecord · IrbisRecordBack · IrbisRecUpdate0 · IrbisRecUpdateTime · Irbisnewrec · Irbisrecdel · Irbisrecundelete · Irbischangemfn · Irbismaxmfn · Irbismfn · Irbisnfields · Irbisfield · Irbisfieldn · Irbisfldadd · Irbisfldrep · Irbisfldempty · Irbisfldtag`
**Инвертированный файл (поиск):** `IrbisInitInvContext · Irbisinitterm · Irbisinitpost · Irbiscloseterm · InsertTerm · IrbisFindPosting · Irbisfind · IrbisSearch_Range · IrbisFreeIrbisSearch · Irbisposting · Irbisnxtterm · Irbisprevterm · Irbisnxtpost · Irbisnocc · Irbisnposts · IrbisSetUseCashTerms · TSearchRecX`
**Форматирование (ядро A1):** `Irbis_Format · Irbis_InitPFT · UNIFOR · UMARCI` (UNIMARC import)
**Блокировки:** `IrbisIsDBLocked · IrbisIsLocked · IrbisIsRealyLocked · IrbisLockDBTime · IrbisUnLockDBTime · IrbisRecLock0 · IrbisRecLockTime · IrbisRecUnLock0 · IrbisRecUnLockTime`
**Актуализация + ПОЛНЫЕ ТЕКСТЫ (закрывает G1):** `IrbisIsActualized · IrbisIsActualizedFT · IrbisRecIfUpdate0 · IrbisRecIfUpdateTime · IrbisRecIfUpdateFullText · IrbisRecIfUpdateFullTextTime · IrbisIsRealyNotActualizedFT · IrbisSetFullTextActualizedBitTime · IrbisNotActList · IrbisEmptyTime`
**Версия/GUID/инициализация:** `IrbisDLLVersion · IrbisReadVersion · IrbisGetGuid · IrbisSetGuid · IrbisReadGuid · irbis_MainIni_Init · irbis_init_DepositPath · irbis_set_options · IrbisInitUACTAB · irbis_uatab_init`

## Ключевые выводы (что это даёт)
- **`UNIFOR` и `Irbis_Format/InitPFT` — экспортируемые примитивы** → подтверждают, что PFT+UNIFOR это ядро (наш движок A1 моделирует именно их).
- **Полнотекстовая актуализация** — отдельный набор функций (`*FullText*`) → подтверждает ПБД как первоклассную подсистему (G1, DAM).
- **`irbis_init_DepositPath`** → форматы реально лежат в `Deposit\` (снимает recon-вопрос #MOD-01).
- **`IrbisInitUACTAB`/`uatab_init`** → таблица приведения регистра/морфология (БД MORPH) — отдельный примитив.
- **Админ-функции `IC_adm_*`** → точные серверные операции (реорг/актуализация/unlock/процессы/клиенты), которые мы помечали 🟡 — теперь это явный контракт.

## Что НЕ извлекается без Ghidra/IDA
Тела функций = алгоритмы: точная семантика ранжирования поиска, пошаговое вычисление ФЛК внутри, парсинг `.gbl`, логика `Irbis_Format`. Имена и контракт есть; для байт-точной логики нужен декомпилятор (Ghidra бесплатен) — отдельный шаг по конкретным функциям при необходимости.
