// Typed client for the IRBIS64 web backend (same-origin /api). Bearer token kept
// in memory only (no localStorage — secure contour). Mirrors backend core.py.

export interface Envelope<T> { ok: boolean; data?: T; error?: { code: string; message: string }; }
export interface Health { server: string; version: string; db: string; maxmfn: number; }
export interface ResultItem {
  mfn: number; title: string; author?: string; year?: string;
  docType?: string; availability?: "available" | "issued" | "unknown"; hasCover?: boolean;
  // База-источник записи. Заполняется клиентом при поиске «во всех базах»
  // (мульти-БД, #3), чтобы открыть/забронировать запись в её собственной БД.
  // При обычном одно-БД-поиске поле опущено — действует активная база.
  db?: string;
}
export interface SearchResult { db: string; expr: string; total: number; page: number; pageSize: number; items: ResultItem[]; }
export interface FieldVal { tag: string; value: string; text?: string; subfields: Record<string, string>; }
export interface Holding { inv_no: string; status: string; cell: string; rfid: string; location?: string; }
export interface RecordData { db: string; mfn: number; version?: string; brief?: string; hasCover?: boolean; fields: FieldVal[]; holdings?: Holding[]; }
export interface StorageNode {
  id: number; kind: string; code: string; name?: string; address?: string; size?: string;
  gx?: number; gy?: number; gw?: number; gh?: number;
  cellsTotal?: number; cellsOccupied?: number;
  occupied?: boolean; status?: string; title?: string; inv?: string; mfn?: number;
  children?: StorageNode[];
}
export interface Term { count: number; term: string; }
// Серверный рендер записи в формате ИРБИС (GET /api/render/{db}/{mfn}?fmt=).
// rendered — готовый текст библиографического описания (PFT сворачивается в
// текст; HTML-разметка — поздняя фаза движка). fmt — применённый формат (@full,
// @brief и т.п.). Пустой rendered → клиент откатывается на следующий формат.
export interface RecordRender { db: string; mfn: number; fmt: string; rendered: string; }
// «Вы имели в виду» (GET /api/suggest) — варианты исправления/расширения запроса
// при нулевой выдаче. Эндпойнт-сиблинг бэкенда может отсутствовать → 404 → блок
// скрывается. Сервер может вернуть массив строк или объектов {term,count}.
export interface Suggestion { term: string; count?: number; }
export interface SuggestResult { db?: string; q?: string; suggestions: Suggestion[]; }
export interface FacetValue { value: string; label: string; count: number; }
export interface Facet { field: string; prefix: string; label: string; values: FacetValue[]; }
export interface FacetsResult { db: string; expr: string; facets: Facet[]; }
export interface Grant { function: string; db: string; level: string; }
// Enriched /api/databases item: optional record count + icon/description for the
// rich DB selector (G17). Older backends may omit count/icon/description — degrade.
export interface DbItem { code: string; name: string; public: boolean; count?: number; icon?: string; description?: string; }
export interface Loan { value: string; subfields: Record<string, string>; }
export interface CabinetData { mfn: number; name: string; loans: Loan[]; loanCount: number; }
// Discovery façade (G2) — a showcase row of new arrivals from /api/showcase.
export interface ShowcaseItem { mfn: number; title: string; author?: string; year?: string; cover?: boolean; }
// Reader cabinet «Заказы» (G12) — an order with a cancel-before-issue affordance.
export interface OrderItem {
  id?: string | number; mfn: number; db?: string; title?: string; author?: string;
  status?: string; statusLabel?: string; created?: string; place?: string; cancelable?: boolean;
}
// Бронирование (#222) — заявка на удержание экземпляра с позицией в очереди.
//   status: 'ready' — готов к получению; 'queued' — в очереди (position — ваш номер).
export interface Hold {
  holdId: string; db: string; mfn: number; title?: string;
  status: "ready" | "queued"; position?: number; until?: string;
}
export interface HoldResult { holdId: string; status: "ready" | "queued"; position?: number; }
// Уведомления читателя (#222) — почтовый ящик портала. event — машинный тип
// события (hold_ready/due_soon/…); subject/body — человекочитаемый текст.
export interface Notification {
  id: string | number; ts?: string; event?: string; subject?: string; body?: string; read?: boolean;
}
// Полки / списки чтения (#222). system=true — встроенные («Хочу прочитать»,
// «Избранное»), их нельзя удалять; пользовательские списки — system=false.
export interface ShelfItem { db: string; mfn: number; title?: string; }
export interface Shelf { id: string; name: string; system?: boolean; items: ShelfItem[]; }
// Отзывы и оценки (#134). avg/count — агрегат по записи; mine — отзыв текущего
// читателя (если оставлял), для режима «редактировать/удалить свой».
export interface Review { id: string | number; readerName?: string; rating: number; text?: string; ts?: string; mine?: boolean; }
export interface ReviewsResult { avg: number; count: number; mine?: Review | null; items: Review[]; }
// Рекомендации (#133). reason — человекочитаемое обоснование («похоже по теме»,
// «читатели также брали», «новинка по вашим интересам»).
export interface Recommendation { db: string; mfn: number; title: string; author?: string; reason?: string; }
// История просмотров (#134). Недавно открытые записи с временной меткой.
export interface HistoryItem { db: string; mfn: number; title?: string; ts?: string; }
// Сохранённые запросы (#133). prefix/query задают простой поиск; query может
// нести готовое выражение, тогда prefix пуст. db — база, в которой искать.
export interface SavedSearch { id: string | number; name: string; db: string; prefix?: string; query: string; ts?: string; }

// --- Каталогизация: рабочий лист + ФЛК (#183, #188) ------------------------
// Описание поля рабочего листа (.ws/.wss → FIELD_CATALOG). type определяет
// контрол в DynamicField: text/menu/dict/tree/bool/authority/date. subfields —
// вложенные подполя; repeatable — повторяемое поле (массив вхождений).
export interface WorklistSubfield { code: string; label: string; type: string; options?: string[]; }
export interface WorklistField {
  code: string; label: string; type: string;
  required?: boolean; repeatable?: boolean;
  options?: string[]; subfields?: WorklistSubfield[];
  placeholder?: string; hint?: string;
}
// Нарушение ФЛК (SPEC §0): severity 0 пройдено · 1 непреодолимая (блокирует
// сохранение) · 2 преодолимая (сохранение после подтверждения). field/subfield —
// MARC-адрес для подсветки строки рабочего листа; message — текст оператору.
export interface FlkViolation {
  ruleId: string; severity: 0 | 1 | 2; message: string;
  path?: string; field?: string | null; subfield?: string | null; stub?: boolean;
}
export interface FlkResult {
  db: string; phase: string;
  overallSeverity: 0 | 1 | 2; canSave: boolean;
  violations: FlkViolation[];
}
// Запись для ФЛК — карта поле→значение: скаляр, {подполе:значение} или массив
// (повторяемое). Совпадает с record-draft движка flk.py.
export type FlkRecord = Record<string, string | Record<string, string> | Array<string | Record<string, string>>>;

// --- Книговыдача (#185) ----------------------------------------------------
// Формуляр читателя: карточка + активные выдачи. blocks/messages — служебные
// сообщения (должник, превышен лимит, бронеблок), debtor/fine — флаги/сумма.
export interface CircReader {
  ticket: string; name?: string; category?: string; status?: string;
  debtor?: boolean; finesTotal?: number; blocks?: string[];
}
export interface CircLoan {
  db?: string; item: string; title?: string; author?: string;
  issued?: string; due?: string; overdue?: boolean; renewable?: boolean;
}
export interface CircFormular { reader: CircReader; loans: CircLoan[]; messages?: string[]; }
// Штрафы читателя: список начислений + итог. paid/reason — статус и причина.
export interface CircFine { id?: string | number; amount: number; reason?: string; date?: string; paid?: boolean; }
export interface CircFines { ticket: string; total: number; items: CircFine[]; }
// Результат операции выдачи/возврата/продления: обновлённый займ + сообщение.
export interface CircActionResult { ok?: boolean; message?: string; loan?: CircLoan; block?: string; }

// --- Комплектование (#184) -------------------------------------------------
// Заказ на комплектование: издание, поставщик, число экземпляров, цена,
// источник финансирования. status — стадия (создан / отправлен / частично
// получен / получен / отменён); statusLabel — человекочитаемая метка.
export interface AcqOrder {
  id: string | number; title: string; author?: string; supplier?: string;
  copies: number; price?: number; funding_source?: string;
  status?: string; statusLabel?: string; created?: string;
  received?: number; ksuNo?: string; canceled?: boolean;
}
// Строка КСУ (книга суммарного учёта) — итог поступления партии: номер записи
// КСУ, дата, число и сумма поступивших экземпляров, ссылка на акт/счёт.
export interface KsuEntry {
  no: string; date?: string; copies?: number; sum?: number;
  actRef?: string; orderId?: string | number; supplier?: string;
}
// Результат поступления (POST /api/acq/receive): запись КСУ + результат ToCat
// (создание/правка каталожной записи) с MFN созданной/обновлённой записи.
export interface AcqReceiveResult {
  ksu?: KsuEntry; ksuNo?: string;
  mfn?: number; db?: string; created?: boolean; toCat?: boolean;
  copies?: number; message?: string;
}

// --- Книгообеспеченность (#186) --------------------------------------------
// Структура связки: факультет → специальность → дисциплина. Идентификаторы
// возвращает сервер при создании; код/наименование — реквизиты карточки.
export interface BpFaculty { id: string | number; code: string; name: string; }
export interface BpSpecialty {
  id: string | number; facultyId?: string | number;
  napr?: string; spec?: string; vid?: string; form?: string; name: string;
}
export interface BpDiscipline {
  id: string | number; specialtyId?: string | number;
  discId?: string; name: string; semester?: number; students?: number;
}
// Привязанная к дисциплине литература: вид (осн./доп.), число экземпляров.
//   kind: 'main' — основная, 'extra' — дополнительная.
export interface BpBinding {
  id?: string | number; title: string; kind: "main" | "extra";
  copies: number; mfn?: number; author?: string;
}
// Коэффициент книгообеспеченности (Кко). value — сам коэффициент (экз/чел);
// underProvided — флаг недообеспеченности (value < норматива); shortfall —
// дефицит экземпляров до норматива; norm — применённый норматив.
export interface BpKko {
  value: number; norm?: number; underProvided: boolean; shortfall?: number;
  students?: number; copies?: number; normalized?: boolean;
}
// Карточка дисциплины с расчётом Кко: реквизиты + привязки + коэффициент.
export interface BpDisciplineCard {
  discipline: BpDiscipline; bindings: BpBinding[]; kko?: BpKko;
}
// Карточка специальности: дисциплины с их Кко + сводный Кко по специальности.
export interface BpSpecialtyCard {
  specialty: BpSpecialty; disciplines: BpDisciplineCard[]; kko?: BpKko;
}

// --- Администрирование (#187) ----------------------------------------------
// Учётная запись сотрудника: логин, ФИО, активность, набор ролей.
export interface AdminUser {
  id: string | number; login: string; fullName?: string;
  active: boolean; roles: string[]; created?: string; lastLogin?: string;
}
// Роль (справочник): код, наименование, состав грантов (для подсказки оператору).
export interface AdminRole { code: string; name?: string; grants?: string[]; description?: string; }
// Запись аудита: метка времени, актор (логин), функция (операция), результат.
export interface AuditEntry {
  ts?: string; actor?: string; function?: string; fn?: string;
  result?: string; ok?: boolean; detail?: string; ip?: string;
}
// База данных контура (для справочника администратора): код, имя, публичность.
export interface AdminDatabase { code: string; name: string; public: boolean; count?: number; }

// --- Платформа: арендаторы + тариф/биллинг (#207, #209; epic #223) ----------
// Арендатор (tenant) контура SaaS. Бэкенд (#207/#209) возвращает
// {slug,name,kind,plan} из контрольного каталога (provision.list_tenants);
// kind — тип учреждения (опц., может быть null). Клиент деградирует на 404/501.
export interface Tenant {
  slug: string; name: string; plan: string;
  kind?: string | null;
}
// Лимиты тарифа (backend snake_case, billing.plan_limits): верхние границы по
// записям, читателям и хранилищу (МБ). Значение null/UNLIMITED — без лимита (∞).
// Ключи покрывают весь набор LIMIT_RESOURCES.
export interface PlanLimits {
  max_records: number | null;
  max_readers: number | null;
  max_storage_mb: number | null;
}
// Потребление — ЧАСТИЧНАЯ карта тех же ресурсов (billing.tenant_usage). Ресурс,
// который сервер не смог посчитать, просто отсутствует (трактуем как «—»/0).
export interface PlanUsage {
  max_records?: number;
  max_readers?: number;
  max_storage_mb?: number;
}
// Элемент каталога тарифов (billing.plans_catalog): код плана, человекочитаемый
// заголовок, набор лицензируемых модулей и его лимиты.
export interface PlanCatalogItem {
  plan: string; title: string; modules: string[]; limits: PlanLimits;
}
// Тариф/биллинг выбранного арендатора (GET /api/admin/billing):
//   plan    — текущий тариф (один из каталога);
//   limits  — лимиты тарифа (snake_case, null = без лимита);
//   usage   — частичная карта потребления (snake_case);
//   modules — СПИСОК включённых модулей (имена); модуль ON ⇔ он в этом списке;
//   plans   — каталог всех тарифов (полный набор модулей = объединение их modules).
export interface BillingInfo {
  tenant?: string;
  plan: string;
  limits: PlanLimits;
  usage: PlanUsage;
  modules: string[];
  // Режим продукта (узел 3): demo/webportal/full или 'custom' (нестандартный
  // набор модулей вручную). Производное от modules — сервер считает derive_mode.
  mode?: string;
  plans?: PlanCatalogItem[];
}

// --- Соответствие 152-ФЗ: согласие · право на забвение · журнал ПДн ----------
// (MVP фаза 3, аудит V9/V5; #199, epic #223). Бэкенд приземляется отдельно —
// клиент деградирует на 404/501 (информер/тихий тост), портал не падает.
// Согласие читателя на обработку ПДн: given — дано ли; ts — отметка времени
// последнего изменения; version — версия политики/уведомления, на которую
// дано согласие (для повторного запроса при обновлении уведомления).
export interface ConsentState { given: boolean; ts?: string; version?: string; }
// Результат права на забвение (POST /api/reader/erase): счётчики удалённого по
// категориям читательских данных. Каталожные записи библиотеки НЕ затрагиваются.
export interface ErasureResult {
  reviews?: number; holds?: number; shelves?: number; history?: number; savedSearches?: number;
}
// Запись журнала доступа к ПДн (GET /api/admin/pdn-access): ts — когда; actor —
// кто обращался (логин сотрудника/система); subject — субъект ПДн (билет
// читателя); action — что сделано (просмотр формуляра, выгрузка, правка, …).
export interface PdnAccessEntry { ts?: string; actor?: string; subject?: string; action?: string; }

// --- Миграция данных: онбординг-мастер переноса из ИРБИС64 (#225; epic #223) -
// Источник миграции:
//   • 'network' — сетевой сервер ИРБИС64 (хост/порт + учётка + рабочая станция);
//   • 'local'   — локальный каталог данных ИРБИС (напр. C:\IRBIS64\Datai).
// Креды живут только в форме мастера: не сохраняются в клиенте и не логируются.
export type MigrateMode = "network" | "local";
// Сетевые реквизиты подключения к серверу ИРБИС64 (логин/пароль — транзитом).
export interface MigrateNetworkSource { host: string; port: number; user: string; pass: string; workstation?: string; }
// Локальный источник — путь к каталогу данных ИРБИС.
export interface MigrateLocalSource { path: string; }
export type MigrateSource = MigrateNetworkSource | MigrateLocalSource;
// Поле обнаруженной БД: MARC-тег, метка, состав подполей, частота встречаемости
// и флаг «допполе» (custom:true) — поле вне штатной схемы РУСМАРК (локальное
// расширение библиотеки), которое мастер помечает оператору при изучении.
export interface MigrateField {
  tag: string; label?: string; subfields: string[];
  freq?: number; custom?: boolean;
}
// Обнаруженная при изучении источника база: код, наименование, тип (kind —
// напр. bibliographic/reader/authority), число записей и (для читательских БД)
// число читателей. Инвентарь полей (fields) грузится ЛЕНИВО — отдельным
// вызовом migrateInspect(mode, source, [code]) при раскрытии конкретной БД,
// поэтому в быстром списке баз он отсутствует (поле опциональное).
export interface MigrateDatabase {
  code: string; name: string; kind?: string;
  recordCount?: number; readerCount?: number;
  fields?: MigrateField[];
}
// Результат изучения источника (POST /api/admin/migrate/inspect).
export interface MigrateInspect { databases: MigrateDatabase[]; }
// Отчёт о миграции (POST /api/admin/migrate/run): прочитано/загружено записей,
// загружено читателей, пропущено, ошибок. Для dry-run загрузка = 0 (ничего не
// записано), но счётчики чтения/пропусков отражают пробный анализ.
export interface MigrateReport {
  records_read: number; records_loaded: number;
  readers_loaded: number; skipped: number; errors: number;
}
// Ответ запуска миграции: отчёт (синхронно) и/или идентификатор фоновой задачи
// (jobId) — тогда статус добирается через GET /api/admin/migrate/status.
export interface MigrateRunResult { report: MigrateReport; jobId?: string; }
// Статус фоновой задачи миграции (GET /api/admin/migrate/status?jobId=):
//   state: queued|running|done|error; report появляется по завершении.
export interface MigrateStatus { jobId?: string; state: string; report?: MigrateReport; error?: string; }

// --- Связанные записи: иерархия издания (#analytics) -----------------------
// Аналитическая роспись и многоуровневые издания. kind задаёт направление:
//   'children' — что входит В издание (статьи журнала, номера, тома);
//   'host'     — издание-хозяин для аналитики (журнал/сборник статьи).
// items[].brief — готовое краткое описание для строки списка; mfn — для перехода.
// Сиблинг-бэкенд отдаёт {db,mfn,kind,total,items}. 404/501 → блок скрывается.
export type LinkedKind = "children" | "host";
export interface LinkedItem { mfn: number; brief: string; }
export interface LinkedResult {
  db: string; mfn: number; kind: LinkedKind; total: number; items: LinkedItem[];
}
// --- Полный текст: артефакты + права доступа -------------------------------
// Артефакт полного текста записи: kind — тип (pdf/djvu/scan/epub/…); ref —
// ссылка/идентификатор; pages — число страниц (если известно); rightsTemplate —
// человекочитаемый шаблон условий использования (копирайт/лицензия).
export interface FulltextArtifact {
  kind: string; ref: string; pages?: number; rightsTemplate?: string;
}
// Уровень доступа к полному тексту для категории текущего пользователя:
//   'deny'     — недоступно (показываем подпись, кнопка просмотра неактивна);
//   'view'     — только просмотр (без скачивания);
//   'download' — просмотр и скачивание.
// pageLimit — лимит страниц к просмотру; downloadBudget — остаток квоты скачиваний.
export type FulltextLevel = "deny" | "view" | "download";
export interface FulltextAccess { level: FulltextLevel; pageLimit?: number; downloadBudget?: number; }
export interface FulltextResult {
  db: string; mfn: number; artifacts: FulltextArtifact[]; access: FulltextAccess;
}
// --- Книгообеспеченность: отчёт ККО (быстрая справка) ----------------------
// Отчёт по обеспеченности (GET /api/bp/provision) для деска ККО: запрашивается
// по дисциплине / специальности / факультету. coefficient — коэффициент Кко
// (экз/чел); status: 'ok' — обеспечено, 'deficit' — дефицит; shortfall — дефицит
// экземпляров до норматива; bindings — привязанная литература (осн./доп.).
export type BpProvisionStatus = "ok" | "deficit";
export interface BpProvisionBinding {
  title: string; kind?: "main" | "extra"; copies?: number; author?: string; mfn?: number;
}
export interface BpProvisionReport {
  scope?: string; subject?: string;
  coefficient?: number; norm?: number;
  status?: BpProvisionStatus;
  students?: number; copies?: number; shortfall?: number;
  bindings?: BpProvisionBinding[];
}

let token: string | null = null;
const authHeaders = (): Record<string, string> => (token ? { Authorization: "Bearer " + token } : {});

async function jget<T>(path: string): Promise<{ status: number; json: Envelope<T> | null }> {
  const r = await fetch(path, { headers: authHeaders() });
  return { status: r.status, json: await r.json().catch(() => null) };
}
async function jpost<T>(path: string, body?: unknown): Promise<{ status: number; json: Envelope<T> | null }> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return { status: r.status, json: await r.json().catch(() => null) };
}
const qs = (o: Record<string, string | number>) =>
  Object.keys(o).map((k) => k + "=" + encodeURIComponent(String(o[k]))).join("&");

export const api = {
  hasToken: () => !!token,
  async initGuest() {
    const r = await fetch("/api/auth/guest", { method: "POST" });
    const j = await r.json();
    token = j.data.token;
    return j.data as { token: string; kind: string };
  },
  health: () => jget<Health>("/api/health"),
  databases: () => jget<{ items: DbItem[]; default: string }>("/api/databases"),
  search: (db: string, prefix: string, q: string, page: number, pageSize: number) =>
    jget<SearchResult>("/api/search?" + qs({ db, prefix, q, page, pageSize })),
  searchExpr: (db: string, expr: string, page: number, pageSize: number) =>
    jget<SearchResult>("/api/search?" + qs({ db, expr, page, pageSize })),
  facets: (db: string, prefix: string, q: string) =>
    jget<FacetsResult>("/api/facets?" + qs({ db, prefix, q })),
  facetsExpr: (db: string, expr: string) =>
    jget<FacetsResult>("/api/facets?" + qs({ db, expr })),
  terms: (start: string, count = 8, db?: string) => jget<{ db: string; terms: Term[] }>("/api/terms?" + qs({ db, start, count })),
  record: (db: string, mfn: number) => jget<RecordData>("/api/record/" + db + "/" + mfn),
  // Серверный рендер записи в формате ИРБИС: путь /api/render/{db}/{mfn}, формат
  // в query (?fmt=@full). По умолчанию @brief (как на бэкенде). 404/501 → fallback
  // делает вызывающий код (на @brief, затем на показ полей).
  render: (db: string, mfn: number, fmt = "@full") =>
    jget<RecordRender>("/api/render/" + db + "/" + mfn + "?" + qs({ fmt })),
  // «Вы имели в виду» (GET /api/suggest) при нулевой выдаче. db/prefix/q —
  // контекст исходного поиска. 404/501 → блок подсказок скрыт.
  suggest: (db: string, prefix: string, q: string) =>
    jget<SuggestResult>("/api/suggest?" + qs({ db, prefix, q })),
  coverUrl: (db: string, mfn: number) => "/api/cover/" + db + "/" + mfn + (token ? "?t=" + encodeURIComponent(token) : ""),
  order: (db: string, mfn: number) => jpost("/api/order", { db, mfn }),
  // Discovery showcase (G2): new arrivals etc. `kind` defaults to "new" on the backend.
  showcase: (db: string, kind = "new", limit = 12) =>
    jget<{ items: ShowcaseItem[] }>("/api/showcase?" + qs({ db, kind, limit })),
  // Rubricator terms with counts (browse navigators) — used for example-query seeds.
  rubricator: (db: string, prefix: string, limit = 12) =>
    jget<{ terms: Term[] }>("/api/rubricator?" + qs({ db, prefix, limit })),
  cabinet: () => jget<CabinetData>("/api/me/cabinet"),
  // Reader orders (G12). Endpoint may not exist yet → caller stubs the list on 404.
  orders: () => jget<{ items: OrderItem[] }>("/api/me/orders"),
  cancelOrder: (id: string | number, db?: string, mfn?: number) =>
    jpost("/api/me/orders/cancel", { id, db, mfn }),
  storage: (db: string) => jget<{ db: string; tree: StorageNode[]; holdings: number }>("/api/storage?" + qs({ db })),
  // Вход читателя по билету и паролю. Пароль передаётся в теле {ticket,password};
  // если пуст — поле просто опускается (совместимо со старым бэкендом, который
  // читает только ticket). Пароль — «как в читательском билете».
  async loginReader(ticket: string, password?: string) {
    const body: { ticket: string; password?: string } = { ticket };
    if (password) body.password = password;
    const r = await jpost<{ token: string; name?: string }>("/api/auth/reader", body);
    if (r.status === 200 && r.json?.ok && r.json.data) token = r.json.data.token;
    return r;
  },
  async loginStaff(login: string, password: string) {
    const r = await jpost<{ token: string; login: string; name?: string; grants: Grant[] }>("/api/auth/staff", { login, password });
    if (r.status === 200 && r.json?.ok && r.json.data) token = r.json.data.token;
    return r;
  },
  // --- Связанные записи: иерархия издания -----------------------------------
  // Связанные записи по направлению kind. children — что входит в издание
  // (статьи/номера/тома); host — издание-хозяин аналитики. 404/501 → блок скрыт.
  linked: (db: string, mfn: number, kind: LinkedKind) =>
    jget<LinkedResult>("/api/linked/" + db + "/" + mfn + "?" + qs({ kind })),
  // --- Полный текст: артефакты + права доступа ------------------------------
  // Артефакты полного текста записи и уровень доступа категории читателя.
  // 404/501 → блок «Полный текст» скрывается.
  fulltext: (db: string, mfn: number) =>
    jget<FulltextResult>("/api/fulltext/" + db + "/" + mfn),

  // --- Бронирование (#222) -------------------------------------------------
  // Поставить экземпляр в бронь. → {holdId,status,position}. 404/501 → degrade.
  hold: (db: string, mfn: number) => jpost<HoldResult>("/api/hold", { db, mfn }),
  // Список активных броней читателя с позицией в очереди.
  holds: () => jget<{ items: Hold[] }>("/api/holds"),
  // Снять бронь по её идентификатору.
  cancelHold: (holdId: string) => jpost("/api/hold/cancel", { holdId }),
  // --- Уведомления читателя (#222) -----------------------------------------
  // Лента уведомлений; unread=1 — только непрочитанные. Возвращает счётчик unread.
  notifications: (unreadOnly = false) =>
    jget<{ items: Notification[]; unread: number }>("/api/notifications?" + qs({ unread: unreadOnly ? 1 : 0 })),
  // Отметить прочитанным: одно (по id) либо все (all:true).
  markNotificationRead: (idOrAll: { id: string | number } | { all: true }) =>
    jpost<{ unread: number }>("/api/notifications/read", idOrAll),
  // --- Полки / списки чтения (#222) ----------------------------------------
  shelves: () => jget<{ lists: Shelf[] }>("/api/shelves"),
  createShelf: (name: string) => jpost<{ id: string; name: string; system?: boolean }>("/api/shelves", { name }),
  addToShelf: (listId: string, db: string, mfn: number) => jpost("/api/shelves/item", { listId, db, mfn }),
  removeFromShelf: (listId: string, db: string, mfn: number) => jpost("/api/shelves/item/remove", { listId, db, mfn }),
  worklist: (db: string) => jget<{ db: string; fields: WorklistField[] }>("/api/worklist/" + db),
  saveRecord: (db: string, mfn: number, fields: { tag: string; value: string }[]) =>
    jpost<{ db: string; mfn: number; created: boolean; returnCode: number; violations?: FlkViolation[] }>("/api/record/" + db + "/" + mfn, { fields }),
  // --- ФЛК «на лету» (#188) ------------------------------------------------
  // Прогнать декларативный ФЛК по черновику записи. record — карта поле→значение
  // (см. FlkRecord). phase: 'save' (полная проверка) | 'field' (точечная по
  // одному полю). 404/501 → деградируем к клиентской проверке обязательных полей.
  validate: (db: string, record: FlkRecord, phase: "save" | "field" = "save", field?: string, currentMfn?: number) =>
    jpost<FlkResult>("/api/validate", { db, record, phase, field, currentMfn }),
  // --- Книговыдача (#185) --------------------------------------------------
  // Формуляр читателя по билету: карточка + активные выдачи + служебные блоки.
  circReader: (ticket: string) => jget<CircFormular>("/api/circ/reader?" + qs({ ticket })),
  // Выдать экземпляр (инв./RFID) читателю. Сервер запускает контроль (должник,
  // лимит, бронеблок) и возвращает block при отказе.
  circIssue: (ticket: string, db: string, item: string) =>
    jpost<CircActionResult>("/api/circ/issue", { ticket, db, item }),
  // Принять возврат экземпляра.
  circReturn: (ticket: string, db: string, item: string) =>
    jpost<CircActionResult>("/api/circ/return", { ticket, db, item }),
  // Продлить выдачу (новый срок — в loan.due).
  circRenew: (ticket: string, db: string, item: string) =>
    jpost<CircActionResult>("/api/circ/renew", { ticket, db, item }),
  // Штрафы читателя: список начислений + итог.
  circFines: (ticket: string) => jget<CircFines>("/api/circ/fines?" + qs({ ticket })),
  // --- Отзывы и оценки (#134) ----------------------------------------------
  // Отзывы по записи: средняя оценка, число, список и (если вошёл) свой отзыв.
  reviews: (db: string, mfn: number) =>
    jget<ReviewsResult>("/api/reviews?" + qs({ db, mfn })),
  // Оставить / обновить свой отзыв (1–5 звёзд + опц. текст). 404/501 → degrade.
  postReview: (db: string, mfn: number, rating: number, text?: string) =>
    jpost<Review>("/api/review", { db, mfn, rating, text }),
  // Удалить свой отзыв по идентификатору.
  deleteReview: (id: string | number) => jpost("/api/review/delete", { id }),
  // --- Рекомендации (#133) -------------------------------------------------
  // «Похожие издания» к конкретной записи.
  recommendations: (db: string, mfn: number) =>
    jget<{ items: Recommendation[] }>("/api/recommendations?" + qs({ db, mfn })),
  // «Для вас» — персональная подборка на главной (по истории/интересам).
  recommendationsForYou: () =>
    jget<{ items: Recommendation[] }>("/api/recommendations/foryou"),
  // --- История просмотров (#134) -------------------------------------------
  history: () => jget<{ items: HistoryItem[] }>("/api/history"),
  // --- Сохранённые запросы (#133) ------------------------------------------
  savedSearches: () => jget<{ items: SavedSearch[] }>("/api/savedsearch"),
  saveSearch: (name: string, db: string, prefix: string, query: string) =>
    jpost<SavedSearch>("/api/savedsearch", { name, db, prefix, query }),
  deleteSavedSearch: (id: string | number) => jpost("/api/savedsearch/delete", { id }),

  // --- Комплектование (#184) ----------------------------------------------
  // Создать заказ на комплектование. → AcqOrder. 404/501 → degrade (информер).
  acqOrder: (o: { title: string; author?: string; supplier?: string; copies: number; price?: number; funding_source?: string }) =>
    jpost<AcqOrder>("/api/acq/order", o),
  // Отменить заказ (до поступления).
  acqCancelOrder: (id: string | number) => jpost<AcqOrder>("/api/acq/order/cancel", { id }),
  // Оформить поступление по заказу → запись КСУ + ToCat (создание/правка
  // каталожной записи). Возвращает номер КСУ и MFN созданной/обновлённой записи.
  acqReceive: (r: { orderId: string | number; ksuNo?: string; copies: number; unitPrice?: number; invNumbers?: string[]; actRef?: string }) =>
    jpost<AcqReceiveResult>("/api/acq/receive", r),
  // Получить заказ по идентификатору (для обновления карточки / списка).
  acqGetOrder: (id: string | number) => jget<{ items?: AcqOrder[]; order?: AcqOrder }>("/api/acq/order?" + qs({ id })),
  // Лента/список заказов (без id). 404 → degrade.
  acqOrders: () => jget<{ items: AcqOrder[] }>("/api/acq/order"),
  // Найти запись КСУ по номеру.
  acqKsu: (no: string) => jget<{ entry?: KsuEntry; items?: KsuEntry[] }>("/api/acq/ksu?" + qs({ no })),

  // --- Книгообеспеченность (#186) -----------------------------------------
  // Создать факультет связки.
  bpFaculty: (f: { code: string; name: string }) => jpost<BpFaculty>("/api/bp/faculty", f),
  // Создать специальность под факультетом.
  bpSpecialty: (s: { facultyId: string | number; napr?: string; spec?: string; vid?: string; form?: string; name: string }) =>
    jpost<BpSpecialty>("/api/bp/specialty", s),
  // Создать дисциплину под специальностью (семестр, число студентов).
  bpDiscipline: (d: { specialtyId: string | number; discId?: string; name: string; semester?: number; students?: number }) =>
    jpost<BpDiscipline>("/api/bp/discipline", d),
  // Задать контингент (число студентов) дисциплины — пересчитывает Кко.
  bpContingent: (c: { discId: string | number; students: number }) =>
    jpost<BpDiscipline>("/api/bp/contingent", c),
  // Привязать литературу (осн./доп.) к дисциплине.
  bpBind: (b: { disciplineId: string | number; title: string; kind: "main" | "extra"; copies: number }) =>
    jpost<BpBinding>("/api/bp/bind", b),
  // Карточка дисциплины с расчётом Кко. normalize — применить нормализацию
  // (учёт многоразового использования/семестровой нагрузки) при расчёте.
  bpDisciplineCard: (id: string | number, normalize = false) =>
    jget<BpDisciplineCard>("/api/bp/discipline?" + qs({ id, normalize: normalize ? 1 : 0 })),
  // Карточка специальности: дисциплины с Кко + сводный Кко.
  bpSpecialtyCard: (id: string | number, normalize = false) =>
    jget<BpSpecialtyCard>("/api/bp/specialty?" + qs({ id, normalize: normalize ? 1 : 0 })),
  // Быстрый отчёт ККО для деска: коэффициент, статус (обеспечено/дефицит),
  // дефицит экз. и список привязок. Параметр — один из discipline/specialty/
  // faculty (наименование или код). 404/501 → дек скрывает результат (информер).
  bpProvision: (scope: { discipline?: string; specialty?: string; faculty?: string }) => {
    const o: Record<string, string> = {};
    if (scope.discipline) o.discipline = scope.discipline;
    if (scope.specialty) o.specialty = scope.specialty;
    if (scope.faculty) o.faculty = scope.faculty;
    return jget<BpProvisionReport>("/api/bp/provision?" + qs(o));
  },

  // --- Администрирование (#187) -------------------------------------------
  // Список учётных записей сотрудников.
  adminUsers: () => jget<{ items: AdminUser[] }>("/api/admin/users"),
  // Создать учётную запись (логин, ФИО, пароль, опц. роли).
  adminCreateUser: (u: { login: string; fullName: string; password: string; roles?: string[] }) =>
    jpost<AdminUser>("/api/admin/users", u),
  // Назначить набор ролей пользователю.
  adminSetRoles: (userId: string | number, roles: string[]) =>
    jpost<AdminUser>("/api/admin/users/roles", { userId, roles }),
  // Включить / отключить учётную запись.
  adminSetActive: (userId: string | number, active: boolean) =>
    jpost<AdminUser>("/api/admin/users/active", { userId, active }),
  // Справочник ролей.
  adminRoles: () => jget<{ items: AdminRole[] }>("/api/admin/roles"),
  // Журнал аудита (последние limit записей).
  adminAudit: (limit = 50) => jget<{ items: AuditEntry[] }>("/api/admin/audit?" + qs({ limit })),
  // Список баз данных контура (код / имя / публичность).
  adminDatabases: () => jget<{ items: AdminDatabase[] }>("/api/admin/databases"),

  // --- Платформа: арендаторы + тариф/биллинг (#207, #209; epic #223) -------
  // Список арендаторов контура. 404/501 → degrade (информер).
  adminTenants: () => jget<{ tenants: Tenant[] }>("/api/admin/tenants"),
  // Создать (провизионировать) арендатора: слаг, наименование, логин админа,
  // тариф. → отчёт о провизионировании {slug,name,plan,modules,admin,postgres}.
  // 404/501/403 → degrade.
  adminCreateTenant: (t: { slug: string; name: string; adminLogin: string; plan: string }) =>
    jpost<{ slug: string; name: string; plan: string; modules: string[];
            admin: { id: number | string; login: string }; postgres: boolean }>(
      "/api/admin/tenant", t),
  // Тариф, лимиты, потребление, модули и каталог тарифов выбранного арендатора.
  adminBilling: (tenant: string) => jget<BillingInfo>("/api/admin/billing?" + qs({ tenant })),
  // Сменить тариф арендатора → {tenant,plan,modules,limits,applied}. После смены
  // плана клиент перечитывает биллинг, чтобы обновить usage/plans.
  adminSetPlan: (tenant: string, plan: string) =>
    jpost<{ tenant: string; plan: string; modules: string[]; limits: PlanLimits; applied: boolean }>(
      "/api/admin/billing/plan", { tenant, plan }),
  // Включить / отключить функциональный модуль арендатора →
  // {tenant,module,enabled,applied,modules} (modules — обновлённый список включённых).
  adminSetModule: (tenant: string, module: string, enabled: boolean) =>
    jpost<{ tenant: string; module: string; enabled: boolean; applied: boolean; modules: string[] }>(
      "/api/admin/billing/module", { tenant, module, enabled }),
  // Переключить РЕЖИМ арендатора (demo/webportal/full) — именованный пресет над
  // модулями (узел 3). Сервер применяет пресет и возвращает обновлённый список.
  adminSetMode: (tenant: string, mode: string) =>
    jpost<{ tenant: string; mode: string; applied: boolean; modules: string[] }>(
      "/api/admin/billing/mode", { tenant, mode }),

  // --- Соответствие 152-ФЗ (#199; MVP фаза 3) ------------------------------
  // Текущее согласие читателя на обработку ПДн. 404/501 → согласие не запрашиваем.
  readerConsent: () => jget<ConsentState>("/api/reader/consent"),
  // Дать / отозвать согласие на обработку ПДн. → {ok}. 404/501/401 → degrade.
  setReaderConsent: (given: boolean) => jpost<{ ok: boolean }>("/api/reader/consent", { given }),
  // Право на забвение: удалить читательские данные (отзывы/брони/полки/история/
  // запросы). confirm:true — обязательное подтверждение. Каталог библиотеки не
  // трогается. → {erased:{…счётчики}}. 404/501/401 → degrade.
  eraseReaderData: () => jpost<{ erased: ErasureResult }>("/api/reader/erase", { confirm: true }),
  // Журнал доступа к ПДн (последние limit записей) — для админ-деска. 404/501 → информер.
  pdnAccess: (limit = 50) => jget<{ items: PdnAccessEntry[] }>("/api/admin/pdn-access?" + qs({ limit })),

  // --- Миграция данных из ИРБИС64 (#225; epic #223) ------------------------
  // Изучить источник (сетевой сервер ИРБИС64 / локальный каталог данных):
  // обнаружить базы, число записей и состав полей (с пометкой «допполе» для
  // кастомных). dbs — опц. сужение перечня изучаемых баз. 404/501 → degrade.
  migrateInspect: (mode: MigrateMode, source: MigrateSource, dbs?: string[]) =>
    jpost<MigrateInspect>("/api/admin/migrate/inspect", { mode, source, dbs }),
  // Запустить миграцию выбранных баз в арендатора. dryRun:true — пробный прогон
  // (ничего не записывается). → отчёт {records_read, records_loaded,
  // readers_loaded, skipped, errors} (+ опц. jobId фоновой задачи). 404/501 → degrade.
  migrateRun: (params: { mode: MigrateMode; source: MigrateSource; tenant: string; dbs: string[]; dryRun: boolean }) =>
    jpost<MigrateRunResult>("/api/admin/migrate/run", params),
  // Статус фоновой задачи миграции по её jobId (если run вернул jobId).
  migrateStatus: (jobId: string) =>
    jget<MigrateStatus>("/api/admin/migrate/status?" + qs({ jobId })),
};

export const LANG: Record<string, string> = {
  rus: "русский", eng: "английский", fre: "французский", ger: "немецкий",
  ita: "итальянский", spa: "испанский", lat: "латинский", ukr: "украинский",
};
