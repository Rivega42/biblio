# EASYBOOKABIS_SIP2_MAP — построчный разбор SIP2-клиента EasyBookAbis

> **Источник:** ПОЛНАЯ C#‑декомпиляция `EasyBookAbis.dll` — `_scratch_devices/dc_EasyBookAbis/EasyBookAbis.SIP2/*` + `RfidStation.SIP2/Renew.cs`. Ссылки — `<файл>.cs`.
> **Когда используется:** ветка `AbisConnectType.SIP2` (флаг `UseSIP2=True`). На текущем стенде `UseSIP2=False` → работает прямой ИРБИС ([EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md)). Здесь — что нужно, если развёртывание идёт через **SIP2-сервер АБИС** (наша Biblio должна будет его эмулировать).
> **Связанные:** [DEVICE_IRBIS_INTEGRATION.md](DEVICE_IRBIS_INTEGRATION.md) §4 · [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md)

## 0. Роль и модель

`EasyBookAbis.SIP2.SIP` (`SIP.cs`) — **SIP2-клиент self-check**, реализует тот же интерфейс `IDataBase`, что и `Irbis`. Надстройка выступает терминалом (SC), сервер АБИС — ACS. Фасад `AbisWorker` выбирает `SIP` вместо `Irbis` при `UseSIP2`.

**Что НЕ поддержано по SIP2** (возвращают `false`/no-op, `SIP.cs:255-314`): `GetReaders`, `AddEkp`, `AddReader`, `AddReaderByCard`, `AddExtraCard` → регистрация читателей и привязка ЕКП/карт работают **только в режиме прямого ИРБИС**. `SetBookState` → `true` (заглушка). `GetClientChargedDocsFullInfo` — собирается из `GetClientChargedDocs`+`GetDocInfo`.

Подключение (`SIP.cs:232-253`): `Disconnect` → `Client.Connect` (TCP) → если `IsNeedAuth` шлёт `Login`(93) → `IsDbOk` (`ScStatus` 99). Параметры из `SIP2settings.xml`: `DbIP/DbPort`, `Login/Password`, `InstitutionID`(→AO), `LocationCode`(→CP/AP), `IsNeedAuth`, `AllowedPlaces`.

## 1. Транспорт и кадр (Client.cs, CheckSum.cs, SequenceNumber.cs)

- **TCP-сокет** (`Client.cs`): `SendTimeout=4000`, `ReceiveTimeout=7000`, буфер приёма 2000 б, сборка до терминатора `\r`. Кодировка — `Sip2Config.Encoding` (**по умолчанию UTF-8**).
- **Формирование запроса** (`SendCommand`):
  ```
  wire = CheckSum.CheckSumAdd( command.CreateRequest() + <seq> ) + "\r"
  ```
  где `CreateRequest()` заканчивается на поле `AY`, `<seq>` — цифра 0..9 (циклично, `SequenceNumber`), затем `CheckSumAdd` дописывает `AZ` + 4‑hex контрольную сумму.
  Итоговый кадр: `<MSG><фикс.поля><|поля>AY<seq>AZ<CRC>\r`.
- **Контрольная сумма** (`CheckSum.CheckSumAdd`): к строке дописывается `"AZ"`, складываются байты, `CRC = ((65535 - sum + 1) & 0xFFFF)` в виде 4‑hex. Проверка ответа — `IsCheckSumCorrect` (можно отключить `Sip2Config.IgnoreCheckSum`).
- **Sequence** (`AY`): `SequenceNumber` 0→9 цикл; ответ принимается если его seq == последнего (или `IgnoreCheckSum`).
- **Ретраи** (`SendCommand`): ответ `96` (Request SC Resend) → повтор до 5 раз; запрос `17`+ответ `98` → повтор до 2.
- **Лог** `sip_log.txt` при `SaveLog` (`CONNECT_ERROR/Request/Response/ERROR`).
- **Разбор полей** (`StringParser.GetField`): поле `|XX` до следующего `|` (или фикс. длины); поля `AE/AF` ищутся даже без ведущего `|`.

## 2. Сообщения (точные кадры) — request → response

> `{now}`/`{due}` = `DateConverter.DateToSipFormat` = **`yyyyMMdd    HHmmss`** (4 пробела). `{inst}`=InstitutionID. Срок возврата = `DateConverter.GetReturnDate()` (см. [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) §5).

### 2.1 Login `93 → 94` (Login.cs)
```
запрос : 9300 CN{login} |CO{password} |CP{locationCode} |AY
ответ  : 94  → ok = response[2]=='1'
```
`93` + `00` (алгоритмы UID/PWD = 0). Поля: **CN**=логин, **CO**=пароль, **CP**=код локации.

### 2.2 SC Status `99 → 98` (ScStatus.cs)
```
запрос : 99 0 010 2.00 AY
ответ  : 98  → online = response[2]=='Y'
```
`99` + статус `0` + max print width `010` + версия протокола `2.00`. Из ответа доступны (поля парсятся в свойствах): `AllowCheckIn/Out`, `AllowPatronRenewal`, `AllowPatronStatusUpdate`, и т.п. (читается только `IsOnline`).

### 2.3 Patron Information `63 → 64` (UserInfo.cs)
```
запрос : 63 015 {now} <summary[10]> AO{inst} |AA{userId} |AC |AD{pin} |AY
ответ  : 64 (длина ≥ 61)
```
`<summary[10]>` — 10‑символьная маска «что вернуть», позиция `Y` зависит от типа (`UserBooksTypes`):
| Тип EasyBook | Маска (Y на позиции) | Метод SIP | Поле списка в ответе |
|---|---|---|---|
| `Holds` (= книги на руках, по умолч.) | `"  Y       "` (поз.3 = charged) | `GetClientChargedDocs` | **AU** (charged items) |
| `Orders` (= заказы) | `"Y         "` (поз.1 = hold) | `GetRequestedDocs` | **AS** (hold items) |
| `Recommends` | `"     Y    "` (поз.6) | `GetRecomendedDocs` | **CD** |

Поля запроса: **AO**=инст., **AA**=билет, **AC**=пароль терминала (пусто), **AD**=PIN читателя.
Разбор ответа `64`: `AE`=ФИО, `CQ`(1 симв.)=`Y`→PIN ок, `BF`=категория, `BE`=email, `AA`=билет; **просрочка** = число в `response.Substring(41,4) > 0` (фикс. позиция overdue count); списки кодов книг — повторяющиеся поля `AU`/`AS`/`CD`.

### 2.4 Item Information `17 → 18` (BookInfo.cs)
```
запрос : 17 {now} AO{inst} |AB{bookId} |AC |AY
ответ  : 18
```
Разбор `18`: `Substring(2,2)`=**статус циркуляции** (`CirculationStatus` 00..13), `Substring(4,2)=="01"`→**нужно снять EAS** (`NeedUnsetEas`), `AJ`=название, `BG`=владелец (Owner), `CH`=свойства (split по `":: "` → `Shifr` / `InvNumber` / `BookType`), `AQ`=место (BookPlace), `AH`=срок (`dd.MM.yyyy`/`yyyyMMdd`). Маппинг `CirculationStatus`→`BookState` — `SIP.cs:112-136` (Available→Available, Charged→OnHands, Lost/Missing→Lost, OnOrder/WaitingOnHoldShelf/WaitingToBeReshelved→BookedForOrder, InProcess→Processing, InTransit→InTransit). `AllowedPlaces`: если задан и место не в списке — статус принудительно `Unknown`.

### 2.5 Checkout `11 → 12` (CheckOut.cs)
```
запрос : 11 Y N {now} {due} AO{inst} |AA{client} |AB{book} |AC |BIN |AY
ответ  : 12 → ok = response[2]=='1' && AB==book && AA==client
```
`11` + renewal_ok `Y` + no_block `N` + дата + срок; **AA**=билет, **AB**=экземпляр, **AC**=пароль терминала, **BI**=`N` (no cancel). `DateReturn` берётся из `GetReturnDate()`.

### 2.6 Checkin `09 → 10` (CheckIn.cs)
```
запрос : 09 N {now} {now} AP |AO{inst} |AB{book} |AC |BIN |AY
ответ  : 10 → ok = response[2]=='1' && AB==book
```
`09` + no_block `N` + дата транзакции + дата возврата; **AP**=текущая локация (пусто), **AO**=инст., **AB**=экземпляр, **AC**, **BI**=`N`.

### 2.7 Hold `15 → 16` (Hold.cs)
```
запрос : 15 + {now} BS{pickup} |AO{inst} |AA{client} |AB{book} |AC |AY
ответ  : 16 → ok = response[2]=='1'
```
`15` + hold_mode `+` (добавить); **BS**=место получения (`LocationCode`), **AA**=билет, **AB**=экземпляр. (В фасаде ИРБИС `Hold` — заглушка; по SIP2 — реализован.)

### 2.8 Renew `29 → 30` (RfidStation.SIP2/Renew.cs)
```
запрос : 29 Y N {now} {due} AO{inst} |AA{user} |AD |AB{book} |AY
ответ  : 30 → ok = response.Substring(2,2)=="1Y" && AB==book && AA==user
```
`29` + renewal_ok `Y` + no_block `N` + дата + новый срок; **AA**=билет, **AD**=пароль читателя (пусто), **AB**=экземпляр. Из ответа: `AF`=сообщение (`Message`), `AH`=новый срок (`NewReturnDate`).

## 3. Сводная таблица номеров и полей

| Операция EasyBook | SIP req→resp | Ключевые поля запроса | Признак успеха |
|---|---|---|---|
| Login | 93→94 | CN, CO, CP | resp[2]=='1' |
| IsDbOk/Status | 99→98 | (фикс.) | resp[2]=='Y' |
| GetClientName / ChargedDocs | 63→64 | AO, AA, AC, AD; summary | список AU |
| GetRequestedDocs | 63→64 | summary поз.1 | список AS |
| GetRecomendedDocs | 63→64 | summary поз.6 | список CD |
| GetDocInfo / GetDocState | 17→18 | AO, AB, AC | статус[2..4], поля AJ/BG/CH/AQ/AH |
| Checkout | 11→12 | AA, AB, AC, BI | resp[2]=='1' & AA & AB |
| Checkin | 09→10 | AP, AO, AB, BI | resp[2]=='1' & AB |
| Hold | 15→16 | BS, AA, AB | resp[2]=='1' |
| Renew | 29→30 | AA, AD, AB | resp[2..4]=='1Y' & AA & AB |

Коды полей: **AO**=institution id, **AA**=patron id (билет), **AB**=item id (экземпляр), **AC**=terminal password, **AD**=patron password/PIN, **AE**=personal name, **AF**=screen message, **AH**=due date, **AJ**=title, **AQ**=permanent location, **AS**=hold items, **AU**=charged items, **AP**=current location, **AY**=sequence, **AZ**=checksum, **BE**=email, **BF**=category, **BG**=owner, **BS**=pickup location, **CD**=recommend, **CH**=item properties (`шифр :: инв :: тип`), **CN/CO/CP**=login id/pwd/location, **CQ**=valid patron password.

## 4. Что нужно реализовать в Biblio (если поддерживаем SIP2-развёртывания)

Реализовать **SIP2-сервер (ACS)** со следующим набором (поднабор SIP2 v2.00), чтобы существующая надстройка работала против нашей системы при `UseSIP2=True`:
- **93/94** Login, **99/98** SC/ACS Status (вернуть `online=Y` + флаги политики).
- **63/64** Patron Information с 10‑символьной summary‑маской и списками **AU**(charged)/**AS**(holds)/**CD**(recommend), полями `AE/BF/BE/CQ`, overdue count в `Substring(41,4)`.
- **17/18** Item Information: статус в позициях 2..4 (`CirculationStatus`), маркер EAS `Substring(4,2)=="01"`, поля `AJ/BG/CH(шифр::инв::тип)/AQ/AH`.
- **11/12** Checkout, **09/10** Checkin, **15/16** Hold, **29/30** Renew (с `AF`/`AH`).
- **Конверт:** контрольная сумма (sum→`(0x10000-sum)&0xFFFF` hex4, маркер `AZ`), последовательность `AY` 0..9, терминатор `\r`, кодировка UTF‑8, ответ `96` для запроса повтора.
- Учесть, что **регистрация/ЕКП/доп.карты по SIP2 не идут** — для них требуется прямой ИРБИС (или наш аналог).

> На текущем стенде это **не требуется** (`UseSIP2=False`) — достаточно ИРБИС-совместимости из [EASYBOOKABIS_IRBIS_MAP.md](EASYBOOKABIS_IRBIS_MAP.md) §6.
