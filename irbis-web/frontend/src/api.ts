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
  worklist: (db: string) => jget<{ db: string; fields: any[] }>("/api/worklist/" + db),
  saveRecord: (db: string, mfn: number, fields: { tag: string; value: string }[]) =>
    jpost<{ db: string; mfn: number; created: boolean; returnCode: number }>("/api/record/" + db + "/" + mfn, { fields }),
};

export const LANG: Record<string, string> = {
  rus: "русский", eng: "английский", fre: "французский", ger: "немецкий",
  ita: "итальянский", spa: "испанский", lat: "латинский", ukr: "украинский",
};
