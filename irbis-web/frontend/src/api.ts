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
export interface RecordData { db: string; mfn: number; version?: string; brief?: string; hasCover?: boolean; fields: FieldVal[]; }
export interface Term { count: number; term: string; }
export interface Grant { function: string; db: string; level: string; }
export interface DbItem { code: string; name: string; public: boolean; }

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
  searchExpr: (expr: string, page: number, pageSize: number) =>
    jget<SearchResult>("/api/search?" + qs({ expr, page, pageSize })),
  terms: (start: string, count = 8) => jget<{ db: string; terms: Term[] }>("/api/terms?" + qs({ start, count })),
  record: (db: string, mfn: number) => jget<RecordData>("/api/record/" + db + "/" + mfn),
  coverUrl: (db: string, mfn: number) => "/api/cover/" + db + "/" + mfn + (token ? "?t=" + encodeURIComponent(token) : ""),
  order: (db: string, mfn: number) => jpost("/api/order", { db, mfn }),
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
