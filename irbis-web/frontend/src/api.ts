// Typed client for the IRBIS64 web backend (same-origin /api). Bearer token kept
// in memory only (no localStorage — secure contour). Mirrors backend core.py.

export interface Envelope<T> { ok: boolean; data?: T; error?: { code: string; message: string }; }
export interface Health { server: string; version: string; db: string; maxmfn: number; }
export interface ResultItem {
  mfn: number; title: string; author?: string; year?: string;
  docType?: string; availability?: "available" | "issued" | "unknown"; hasCover?: boolean;
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
  terms: (start: string, count = 8) => jget<{ db: string; terms: Term[] }>("/api/terms?" + qs({ start, count })),
  record: (db: string, mfn: number) => jget<RecordData>("/api/record/" + db + "/" + mfn),
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
  async loginReader(ticket: string) {
    const r = await jpost<{ token: string; name?: string }>("/api/auth/reader", { ticket });
    if (r.status === 200 && r.json?.ok && r.json.data) token = r.json.data.token;
    return r;
  },
  async loginStaff(login: string, password: string) {
    const r = await jpost<{ token: string; login: string; name?: string; grants: Grant[] }>("/api/auth/staff", { login, password });
    if (r.status === 200 && r.json?.ok && r.json.data) token = r.json.data.token;
    return r;
  },
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
};

export const LANG: Record<string, string> = {
  rus: "русский", eng: "английский", fre: "французский", ger: "немецкий",
  ita: "итальянский", spa: "испанский", lat: "латинский", ukr: "украинский",
};
