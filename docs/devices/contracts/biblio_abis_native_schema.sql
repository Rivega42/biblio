-- =====================================================================
-- АРХИТЕКТУРА (#272, DEVICES_NATIVE_ARCHITECTURE.md): таблицы reader/item/loan/
-- reader_order ниже = ПОЛЕ-МАППИНГ на СУЩЕСТВУЮЩИЕ домены Biblio
-- (own-store/RDR, CatalogStore, circulation, holds #222), а НЕ новая параллельная
-- схема. По-настоящему НОВОЕ — только домен `devices` (device/device_data/audit_log).
-- Используйте как справочник соответствия полей ИРБИС <-> сущности Biblio.
-- =====================================================================
-- Biblio — нативное ABIS-хранилище (РЕЖИМ 2: замена ИРБИС)
-- Поля = эквиваленты ИРБИС (исходный тег указан в комментарии).
-- Источник модели: docs/devices/EASYBOOKABIS_IRBIS_MAP.md, TZ_PHASE1 §3.
-- СУБД: PostgreSQL (типы uuid/timestamptz/text[]). Для SQLite — адаптировать.
-- Назначение: за интерфейсом IAbis (BiblioNativeBackend) — те же операции,
--             что IrbisBackend пишет в RDR/RQST/каталог.
-- =====================================================================

-- ---- Читатель (БД RDR) ----------------------------------------------
create table reader (
  id                   bigserial primary key,
  ticket               text not null,                 -- 30  билет/осн. карта
  last_name            text,                          -- 10
  first_name           text,                          -- 11
  patronymic           text,                          -- 12
  birth_date           date,                          -- 21/23 (год/дата)
  gender               char(1),                       -- 23
  category             text,                          -- 50
  email                text,                          -- 32
  phone                text,                          -- 17
  status               text default '1',              -- 100
  citizenship          text,                          -- 101 ("ЕКП РФ")
  pin                  text,                          -- 103 (логин по карте с PIN)
  abis_guid            text,                          -- 12000
  ekp_code             text,                          -- 28  (ЕКП)
  reg_date             date,                          -- 51
  reg_place            text,                          -- 51^C (writePlace = [PRIVATE]MZ)
  created_by           text,                          -- 31^B (оператор)
  created_at           timestamptz default now(),     -- 31^A
  search_hash_passport text,                          -- 12814  MD5(год+MD5(паспорт))
  search_hash_fio      text,                          -- 12815  конкатенация хэшей ФИО/ДР
  has_rights           boolean default true,          -- из ReaderRightsPft (политика прав)
  photo                bytea,
  constraint reader_ticket_uniq unique (ticket)
);
create index reader_ekp_idx       on reader (ekp_code);
create index reader_guid_idx      on reader (abis_guid);
create index reader_hash_fio_idx  on reader (search_hash_fio);
create index reader_hash_pasp_idx on reader (search_hash_passport);

-- ---- Карты читателя (поля 30/24/28) ---------------------------------
-- одна карта — один читатель (AddExtraCard: CardInUse/HasAnother/HasSame)
create table reader_card (
  id          bigserial primary key,
  reader_id   bigint not null references reader(id) on delete cascade,
  code        text not null,
  kind        text not null check (kind in ('main','extra','ekp')),  -- 30 / 24 / 28
  serial      text,
  created_at  timestamptz default now(),
  constraint reader_card_code_uniq unique (code)
);

-- ---- Каталожная запись (каталог) ------------------------------------
-- (или внешняя ссылка на каталожный модуль Biblio)
create table catalog_record (
  id          bigserial primary key,
  external_id text,                                   -- ключ в каталоге
  title       text,                                   -- @brief / 200^A(,E)
  authors     text[],                                 -- 700/701/961 ^A ^G ^B
  shelf_mark  text,                                   -- 903
  age_cenz    int default 18,                         -- @cenz / 900^Z
  genres      text[],                                 -- 60 (rzn.mnu) / 606
  cover_url   text                                    -- 954 ^p+^f
);

-- ---- Экземпляр (поле 910) -------------------------------------------
create table item (
  id                bigserial primary key,
  catalog_record_id bigint references catalog_record(id),
  inv_number        text,                             -- инв. номер
  barcode           text,                             -- 910^B / штрихкод (ключ выдачи)
  status            int not null default 0,           -- 910^A → BookState (0/1/4/6/8/9/12)
  -- групповые экземпляры (910^A = 'U'/'C'):
  is_group          boolean default false,
  group_total       int,                              -- 910^1 (всего)
  group_issued      int,                              -- 910^2 (выдано)
  location          text,                             -- 910^D (чз/место)
  shelf_mark        text,                             -- 903
  issue_count       int default 0                     -- 999 (счётчик выдач)
);
create index item_barcode_idx on item (barcode);
-- BookState (значения столбца status): -1 Unknown,0 Available,1 OnHands,4 Lost,
--   6 Discarded,8 Processing,9 OnShelf,10 AllAvailable(вирт),11 BookedForOrder(вирт),12 InTransit

-- ---- Выдача (поле 40) -----------------------------------------------
create table loan (
  id            bigserial primary key,
  reader_id     bigint not null references reader(id),
  item_id       bigint references item(id),
  item_barcode  text not null,                        -- 40^H (идентификатор экз.)
  shelf_mark    text,                                 -- 40^A (=903)
  barcode_b     text,                                 -- 40^B
  place_loc     text,                                 -- 40^K (=910^D)
  catalog_db    text,                                 -- 40^G (имя БД каталога)
  book_name     text,                                 -- 40^C (@brief; удаляется если READERHISTORY=0)
  operator      text,                                 -- 40^I (chargePerson)
  place_out     text,                                 -- 40^V (MaskMrg или '*')
  place_in      text,                                 -- 40^R (место возврата)
  issued_at     timestamptz not null,                 -- 40^D (дата) + 40^1 (время)
  due_at        date not null,                        -- 40^E (срок)
  returned_at   timestamptz,                          -- 40^F(дата)+40^2(время); NULL = на руках
  renew_count   int default 0,
  last_renew_at date,                                 -- 40^L (продление)
  is_open       boolean generated always as (returned_at is null) stored
);
create index loan_open_reader_idx on loan (reader_id) where returned_at is null;
create index loan_item_idx        on loan (item_barcode);
-- «на руках» (эквивалент 40^F начинается с '*') = returned_at IS NULL.
-- просрочка = is_open AND due_at < current_date.

-- ---- Заказ / бронь (RQST-эквивалент) --------------------------------
-- ВНИМАНИЕ: точная раскладка RQST/691 — инференс (OPEN_QUESTIONS §6);
-- до уточнения заказы/бронь ведутся здесь (Device Service), не в ИРБИС.
create table reader_order (
  id            bigserial primary key,
  reader_id     bigint references reader(id),
  number        text,                                 -- 903 / порядковый
  state         int not null default 1,               -- OrderStates: 1 Created,2 Prepared,3 Staffed,4 Issued,5 Cancelled
  cell_number   int,
  safekeeper_id uuid,
  created_at    timestamptz default now()
);
create table reader_order_item (
  id           bigserial primary key,
  order_id     bigint references reader_order(id) on delete cascade,
  item_barcode text,
  verified     boolean default false,
  processed    boolean default false
);

-- ---- Аудит (ExternalLog) --------------------------------------------
create table audit_log (
  id         bigserial primary key,
  ts         timestamptz default now(),
  login      text,
  action     int not null,                            -- ExternalLogTypes 1..32
  entity     text,
  entity_id  text,
  comment    text
);
-- ExternalLogTypes (action): 1 EASSystemAdded … 14 BookCheckOut,15 BookCheckIn,
--   16 ReaderFormRequest,17 BookInfoRequest,18 ReaderFDSearch … 31 ProgramSettingsChanged,
--   32 UserPasswordChanged. Полный список — docs/devices/LAS_FUNCTION_MAP.md §3.

-- =====================================================================
-- Примечания:
-- • Режим 1 (замена JIRBIS) использует IrbisBackend и пишет в реальный ИРБИС —
--   эти таблицы не задействуются; миграция режим1→режим2 = вычитка RDR/каталог
--   (поиск MFN>n…) в reader/item/catalog_record. RQST — после уточнения раскладки.
-- • Парк устройств (станции/SafeKeeper/ворота/полки/СКУД/камеры) — отдельная
--   БД Device Service; её сущности = DTO из device_service_openapi.json.
-- =====================================================================
