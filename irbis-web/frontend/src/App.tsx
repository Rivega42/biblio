import React from "react";
import { api, LANG } from "./api";
import type { RecordData, ResultItem, FieldVal, DbItem, CabinetData, Facet } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { FilterChip } from "../components/forms/FilterChip.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { SearchBar } from "../components/catalog/SearchBar.jsx";
import { ResultCard } from "../components/catalog/ResultCard.jsx";
import { StatusBadge } from "../components/catalog/StatusBadge.jsx";
import { PftBlock } from "../components/catalog/PftBlock.jsx";
import { Pagination } from "../components/catalog/Pagination.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import { ToastViewport } from "../components/feedback/Toast.jsx";
import { StaffArea, StaffLoginOverlay } from "./Staff";
import type { StaffSession } from "./Staff";
import { exportRecord, exportBasket, basketMailto } from "./export";

const PREFIXES = [
  { code: "K", label: "Ключевые слова" }, { code: "A", label: "Автор" },
  { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
];
const esc = (s: string) => (s || "").replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]!));
const STATUS: Record<string, { label: string; bg: string }> = {
  available: { label: "В ячейке", bg: "var(--status-available-strong,#2f855a)" },
  issued: { label: "На руках", bg: "var(--status-issued-strong,#b7791f)" },
  hold: { label: "В постамате", bg: "#2c5e8a" },
  returned: { label: "Книгоприём", bg: "#7a6a55" },
  unknown: { label: "Нет данных", bg: "#888" },
};
const statusChip = (s: string): React.CSSProperties => ({ background: (STATUS[s] || STATUS.unknown).bg, color: "#fff", borderRadius: 999, padding: "2px 10px", fontSize: "var(--text-xs)", whiteSpace: "nowrap" });
const sf = (f: FieldVal | undefined, c: string) =>
  !f ? "" : (f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "");

interface Toast { id: number; variant: string; title: string; message?: string; }
interface ActiveFacet { field: string; prefix: string; groupLabel: string; value: string; valueLabel: string; }

// Compose a base query expr with the active facet refinements using the IRBIS
// AND operator '*': (<base>) * "V=05" * "J=RUS". Mirrors the backend refinement.
function composeExpr(base: string, active: ActiveFacet[]): string {
  let expr = base;
  for (const a of active) {
    expr = "(" + expr + ') * "' + a.prefix + "=" + a.value.replace(/"/g, "") + '"';
  }
  return expr;
}

function recView(d: RecordData) {
  const F = (tag: string) => d.fields.filter((x) => x.tag === tag);
  const F1 = (tag: string) => F(tag)[0];
  const authors = ["700", "701", "702"].flatMap(F).map((f) => (sf(f, "A") + (sf(f, "G") ? ", " + sf(f, "G") : "")).trim()).filter(Boolean);
  const orgs = ["710", "711"].flatMap(F).map((f) => sf(f, "A")).filter(Boolean);
  const imprint = (() => { const f = F1("210"); if (!f) return ""; const a = sf(f, "A"), c = sf(f, "C"), y = sf(f, "D"); return [a, c].filter(Boolean).join(" : ") + (y ? (a || c ? ", " : "") + y : ""); })();
  const volume = (() => { const f = F1("215"); if (!f) return ""; return [sf(f, "A"), sf(f, "C"), sf(f, "E")].filter(Boolean).join(" ; "); })();
  const langCode = (() => { const f = F1("101"); return f ? (sf(f, "A") || f.value) : ""; })();
  const meta = [
    { label: "Авторы", value: authors.concat(orgs).join("; ") },
    { label: "Выходные данные", value: imprint },
    { label: "Объём", value: volume },
    { label: "ISBN", value: F1("10") ? sf(F1("10"), "A") : "" },
    { label: "Язык", value: LANG[langCode] || langCode },
    { label: "УДК", value: (F1("675") && sf(F1("675"), "A")) || (F1("675")?.value ?? "") },
    { label: "Примечание", value: (F1("331") && sf(F1("331"), "A")) || (F1("330") && sf(F1("330"), "A")) || (F1("300")?.value ?? "") },
  ].filter((r) => r.value);
  const subjects = F("606").map((f) => [sf(f, "A"), sf(f, "B"), sf(f, "C"), sf(f, "D")].filter(Boolean).join(" — ")).filter(Boolean);
  const holds = (d.holdings && d.holdings.length)
    ? d.holdings.map((h) => ({ loc: h.location || "", inv: h.inv_no, st: h.status }))
    : F("910").map((h) => ({ loc: sf(h, "D") || "Основной фонд", inv: sf(h, "B"),
        st: (sf(h, "A") === "0" || sf(h, "A") === "") ? "available" : "issued" }));
  const files = ["951", "955"].flatMap(F).map((f) => {
    const name = sf(f, "T") || sf(f, "A") || sf(f, "H") || f.value || "";
    const link = sf(f, "I") || sf(f, "U") || sf(f, "A") || "";
    const isUrl = /^(https?:\/\/|ftp:\/\/|www\.)/i.test(link.trim());
    return { name: name.trim(), url: isUrl ? (link.trim().startsWith("www.") ? "http://" + link.trim() : link.trim()) : "" };
  }).filter((x) => x.name || x.url);
  const rawRows = d.fields.map((x) => `<tr><td style="color:var(--text-subtle);font-family:var(--font-mono);padding-right:12px;vertical-align:top">${x.tag}</td><td style="font-family:var(--font-mono);font-size:12px">${esc(x.value)}</td></tr>`).join("");
  return { brief: d.brief || "", meta, subjects, holds, files, rawRows };
}

export function App() {
  const [ready, setReady] = React.useState(false);
  const [server, setServer] = React.useState<any>(null);
  const [theme, setTheme] = React.useState("theatrical");
  const [a11y, setA11y] = React.useState(false);
  const [databases, setDatabases] = React.useState<DbItem[]>([]);
  const [db, setDb] = React.useState("IBIS");
  const [prefix, setPrefix] = React.useState("K");
  const [q, setQ] = React.useState("Android");
  const [mode, setMode] = React.useState<"simple" | "advanced" | "expert">("simple");
  const [advRows, setAdvRows] = React.useState([{ field: "A", value: "" }, { field: "T", value: "" }]);
  const [advCombine, setAdvCombine] = React.useState<"and" | "or">("and");
  const [expertExpr, setExpertExpr] = React.useState('"K=Android" + "K=PHP"');
  const [sug, setSug] = React.useState<any[]>([]);
  const [items, setItems] = React.useState<ResultItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [facets, setFacets] = React.useState<Facet[]>([]);
  const [baseExpr, setBaseExpr] = React.useState<string | null>(null);
  const [activeFacets, setActiveFacets] = React.useState<ActiveFacet[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [rec, setRec] = React.useState<RecordData | null>(null);
  const [recTab, setRecTab] = React.useState(0);
  const [shareOpen, setShareOpen] = React.useState(false);
  // Корзина (отбор) — только в памяти, без localStorage (защищённый контур).
  const [basket, setBasket] = React.useState<ResultItem[]>([]);
  const [basketOpen, setBasketOpen] = React.useState(false);
  const [toasts, setToasts] = React.useState<Toast[]>([]);
  const [account, setAccount] = React.useState<{ loggedIn: boolean; ticket?: string }>({ loggedIn: false });
  const [loginOpen, setLoginOpen] = React.useState(false);
  const [view, setView] = React.useState<"search" | "cabinet">("search");
  const [cab, setCab] = React.useState<CabinetData | null>(null);
  const [context, setContext] = React.useState<"reader" | "staff">("reader");
  const [staff, setStaff] = React.useState<StaffSession | null>(null);
  const [staffRoute, setStaffRoute] = React.useState<any>("desktop");
  const [staffLoginOpen, setStaffLoginOpen] = React.useState(false);
  const pageSize = 10;
  const tRef = React.useRef<any>(null);
  const toast = (t: Omit<Toast, "id">) => { const id = Math.random(); setToasts((x) => [...x, { ...t, id }]); setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), 4000); };

  React.useEffect(() => {
    (async () => {
      await api.initGuest();
      const h = await api.health(); setServer(h.json?.data);
      const startDb = h.json?.data?.db || "IBIS"; setDb(startDb);
      const d = await api.databases(); if (d.json?.ok && d.json.data) setDatabases(d.json.data.items);
      setReady(true);
      // Постоянная ссылка: если в URL есть ?db=&mfn=, автоматически открыть запись.
      let opened = false;
      try {
        const p = new URLSearchParams(window.location.search);
        const linkDb = p.get("db"); const linkMfn = p.get("mfn");
        if (linkMfn && /^\d+$/.test(linkMfn)) {
          const useDb = linkDb || startDb; setDb(useDb);
          opened = true;
          await openRecord(parseInt(linkMfn, 10), useDb);
        }
      } catch { /* ignore */ }
      if (!opened) runSearch(startDb, "K", "Android", 1);
    })();
  }, []);

  async function runSearch(database: string, px: string, query: string, pg: number) {
    if (!query.trim()) return;
    setLoading(true); setRec(null); setSug([]); setPage(pg);
    const r = await api.search(database, px, query, pg, pageSize);
    if (r.json?.ok && r.json.data) {
      setItems(r.json.data.items); setTotal(r.json.data.total);
      // a fresh simple search becomes the new base query: reset facets
      if (pg === 1) { setBaseExpr(r.json.data.expr); setActiveFacets([]); loadFacets(database, r.json.data.expr); }
    } else { toast({ variant: "error", title: "Каталог недоступен", message: "Повторите попытку позже." }); setItems([]); setTotal(0); }
    setLoading(false);
  }
  async function loadFacets(database: string, expr: string) {
    setFacets([]);
    const r = await api.facetsExpr(database, expr);
    if (r.json?.ok && r.json.data) setFacets(r.json.data.facets);
  }
  function onQuery(v: string) {
    setQ(v); clearTimeout(tRef.current);
    if (v.trim().length < 2) { setSug([]); return; }
    tRef.current = setTimeout(async () => {
      const r = await api.terms(prefix + "=" + v.toUpperCase(), 8);
      if (r.json?.ok && r.json.data) setSug(r.json.data.terms.filter((t) => t.term.indexOf(prefix + "=") === 0).map((t) => ({ term: t.term.slice(prefix.length + 1), count: t.count })));
    }, 200);
  }
  async function runExpr(database: string, expr: string, pg: number, asBase = false) {
    setLoading(true); setRec(null); setPage(pg);
    const r = await api.searchExpr(database, expr, pg, pageSize);
    if (r.json?.ok && r.json.data) {
      setItems(r.json.data.items); setTotal(r.json.data.total);
      // a fresh expr search (advanced) becomes the new base query: reset facets
      if (asBase && pg === 1) { setBaseExpr(expr); setActiveFacets([]); loadFacets(database, expr); }
    } else { toast({ variant: "error", title: "Каталог недоступен", message: "Повторите попытку позже." }); setItems([]); setTotal(0); }
    setLoading(false);
  }
  // Re-run the search with the current base intersected by the given active facets.
  function applyFacets(next: ActiveFacet[]) {
    if (baseExpr == null) return;
    setActiveFacets(next);
    runExpr(db, composeExpr(baseExpr, next), 1);
  }
  function toggleFacet(f: Facet, v: { value: string; label: string }) {
    const exists = activeFacets.find((a) => a.field === f.field && a.value === v.value);
    if (exists) applyFacets(activeFacets.filter((a) => !(a.field === f.field && a.value === v.value)));
    else applyFacets([...activeFacets, { field: f.field, prefix: f.prefix, groupLabel: f.label, value: v.value, valueLabel: v.label }]);
  }
  function removeFacet(a: ActiveFacet) {
    applyFacets(activeFacets.filter((x) => !(x.field === a.field && x.value === a.value)));
  }
  function buildAdvExpr() {
    const parts = advRows.map((r) => {
      let v = r.value.trim().replace(/"/g, "");
      if (!v) return "";
      if ((r.field === "A" || r.field === "T") && !v.endsWith("$")) v += "$";
      return `"${r.field}=${v}"`;
    }).filter(Boolean);
    if (!parts.length) return null;
    if (parts.length === 1) return parts[0];
    return "(" + parts.join(advCombine === "or" ? " + " : " * ") + ")";
  }
  function runAdvanced() {
    const expr = buildAdvExpr();
    if (!expr) { toast({ variant: "warning", title: "Заполните условия", message: "Введите хотя бы одно значение." }); return; }
    runExpr(db, expr, 1, true);
  }
  function runExpert() {
    const expr = expertExpr.trim();
    if (!expr) { toast({ variant: "warning", title: "Введите выражение", message: "Запрос поиска не должен быть пустым." }); return; }
    runExpr(db, expr, 1, true);
  }
  // --- Корзина (отбор) -----------------------------------------------------
  function inBasket(mfn: number) { return basket.some((b) => b.mfn === mfn); }
  function toggleBasket(it: ResultItem) {
    setBasket((b) => b.some((x) => x.mfn === it.mfn) ? b.filter((x) => x.mfn !== it.mfn) : [...b, it]);
  }
  function removeFromBasket(mfn: number) { setBasket((b) => b.filter((x) => x.mfn !== mfn)); }
  // Pagination that preserves the active base query + facet refinements.
  function gotoPage(p: number) {
    if (baseExpr != null) runExpr(db, composeExpr(baseExpr, activeFacets), p);
    else if (mode === "advanced") { const ex = buildAdvExpr(); if (ex) runExpr(db, ex, p); }
    else runSearch(db, prefix, q, p);
  }

  async function openRecord(mfn: number, database: string = db) {
    setLoading(true); const r = await api.record(database, mfn); setLoading(false);
    if (r.json?.ok && r.json.data) {
      setRec(r.json.data); setRecTab(0); setShareOpen(false);
      // Постоянная ссылка: ?db=<db>&mfn=<mfn> в адресной строке без перезагрузки.
      try { const u = new URL(window.location.href); u.searchParams.set("db", database); u.searchParams.set("mfn", String(mfn)); window.history.replaceState(null, "", u.toString()); } catch { /* ignore */ }
      window.scrollTo(0, 0);
    }
  }
  function closeRecord() {
    setRec(null); setShareOpen(false);
    try { const u = new URL(window.location.href); u.searchParams.delete("db"); u.searchParams.delete("mfn"); window.history.replaceState(null, "", u.pathname + (u.search ? u.search : "")); } catch { /* ignore */ }
  }
  function permalink(): string {
    try { const u = new URL(window.location.href); u.search = ""; u.searchParams.set("db", rec ? rec.db : db); if (rec) u.searchParams.set("mfn", String(rec.mfn)); return u.toString(); } catch { return ""; }
  }
  async function copyPermalink() {
    const link = permalink();
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(link);
      else { const ta = document.createElement("textarea"); ta.value = link; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta); }
      toast({ variant: "success", title: "Ссылка скопирована", message: "Постоянная ссылка на запись в буфере обмена." });
    } catch { toast({ variant: "info", title: "Скопируйте ссылку", message: link }); }
  }
  async function order(mfn: number) {
    const r = await api.order(db, mfn);
    if (r.status === 200) toast({ variant: "success", title: "Заказ принят", message: "Экземпляр поставлен в очередь выдачи." });
    else if (r.status === 401 || r.status === 403) { toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." }); setLoginOpen(true); }
    else toast({ variant: "error", title: "Не удалось заказать", message: "Повторите попытку." });
  }
  async function loadCabinet() {
    const r = await api.cabinet();
    if (r.json?.ok && r.json.data) { setCab(r.json.data); setView("cabinet"); setRec(null); }
    else toast({ variant: "info", title: "Кабинет недоступен", message: "Войдите по читательскому билету." });
  }
  async function doLogin(ticket: string) {
    const r = await api.loginReader(ticket);
    if (r.status === 200) { setAccount({ loggedIn: true, ticket }); setLoginOpen(false); toast({ variant: "success", title: "Вы вошли", message: "Билет № " + ticket }); loadCabinet(); }
    else toast({ variant: "warning", title: "Билет не найден", message: "Проверьте номер читательского билета." });
  }
  function switchContext(c: "reader" | "staff") { if (c === "staff" && !staff) { setStaffLoginOpen(true); return; } setContext(c); setRec(null); }
  async function doStaffLogin(login: string, password: string) {
    const r = await api.loginStaff(login, password);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      setStaff({ name: r.json.data.name, login: r.json.data.login, grants: r.json.data.grants || [] });
      setContext("staff"); setStaffRoute("desktop"); setStaffLoginOpen(false);
      toast({ variant: "success", title: "Вход выполнен", message: r.json.data.name || login });
    } else toast({ variant: "warning", title: "Неверный логин или пароль", message: "Проверьте учётные данные." });
  }

  const rootTheme = a11y ? "a11y" : (theme === "working" ? undefined : theme);
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const DB = db;
  const hbtn = (active: boolean): React.CSSProperties => ({ background: active ? "rgba(255,255,255,.25)" : "transparent", color: "#fff", border: "1px solid rgba(255,255,255,.45)", borderRadius: 8, padding: "5px 10px", cursor: "pointer", fontSize: "var(--text-xs)" });
  const selStyle: React.CSSProperties = { padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)", maxWidth: 240 };
  const modeBtn = (active: boolean): React.CSSProperties => ({ background: active ? "var(--accent)" : "transparent", color: active ? "#fff" : "var(--text-body)", border: "none", borderRadius: 8, padding: "5px 12px", cursor: "pointer", fontSize: "var(--text-sm)" });
  const iconBtn: React.CSSProperties = { padding: "7px 11px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)", cursor: "pointer" };

  if (!ready) return <div style={{ padding: 40, color: "var(--text-subtle)" }}>Загрузка каталога…</div>;

  return (
    <div data-theme={rootTheme} style={{ minHeight: "100vh", background: "var(--bg-page)", color: "var(--text-body)", display: "flex", flexDirection: "column" }}>
      <header style={{ background: "var(--accent)", color: "#fff", padding: "12px 20px", display: "flex", alignItems: "center", gap: 12 }}>
        <Icon name="book" size={22} />
        <b>ИРБИС-Веб · электронный каталог</b>
        <span style={{ opacity: .85, fontSize: "var(--text-xs)" }}>ИРБИС {server?.version} · база {DB}</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, marginRight: 6, padding: 2, background: "rgba(255,255,255,.12)", borderRadius: 10 }}>
            <button onClick={() => switchContext("reader")} style={hbtn(context === "reader")}>Читатель</button>
            <button onClick={() => switchContext("staff")} style={hbtn(context === "staff")}>Сотрудник</button>
          </div>
          <button onClick={() => { setA11y(false); setTheme("working"); }} style={hbtn(theme === "working" && !a11y)}>Рабочая</button>
          <button onClick={() => { setA11y(false); setTheme("theatrical"); }} style={hbtn(theme === "theatrical" && !a11y)}>Театр</button>
          <button onClick={() => setA11y((v) => !v)} style={hbtn(a11y)}>A11y</button>
          {context === "reader" && account.loggedIn && <button onClick={loadCabinet} style={hbtn(view === "cabinet")}>Кабинет</button>}
          {context === "reader" && <button onClick={() => account.loggedIn ? (setAccount({ loggedIn: false }), setView("search"), setCab(null)) : setLoginOpen(true)} style={hbtn(false)}>{account.loggedIn ? "Выйти" : "Вход"}</button>}
          {context === "staff" && staff && <button onClick={() => { setStaff(null); setContext("reader"); }} style={hbtn(false)}>Выйти ({staff.login})</button>}
        </div>
      </header>

      <main style={{ flex: 1, maxWidth: 1100, width: "100%", margin: "0 auto", padding: 20, boxSizing: "border-box" }}>
        {context === "staff" ? (
          <StaffArea staff={staff!} route={staffRoute} setRoute={setStaffRoute} toast={toast} />
        ) : view === "cabinet" ? (
          <CabinetScreen cab={cab} ticket={account.ticket} onBack={() => setView("search")} onLogout={() => { setAccount({ loggedIn: false }); setView("search"); setCab(null); }} />
        ) : (
        <>
        {!rec && (
          <>
            <div style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "center", flexWrap: "wrap" }}>
              {databases.filter((d) => d.public).length > 1 && (
                <select value={db} onChange={(e) => { setDb(e.target.value); if (mode === "simple") runSearch(e.target.value, prefix, q, 1); }} title="База поиска" style={selStyle}>
                  {databases.filter((d) => d.public).map((d) => <option key={d.code} value={d.code}>{d.name || d.code}</option>)}
                </select>
              )}
              <div role="tablist" aria-label="Режим поиска" style={{ display: "flex", gap: 4, padding: 2, background: "var(--surface-sunken,#eee)", borderRadius: 10 }}>
                <button role="tab" aria-selected={mode === "simple"} onClick={() => setMode("simple")} style={modeBtn(mode === "simple")}>Простой</button>
                <button role="tab" aria-selected={mode === "advanced"} onClick={() => setMode("advanced")} style={modeBtn(mode === "advanced")}>Расширенный</button>
                <button role="tab" aria-selected={mode === "expert"} onClick={() => setMode("expert")} style={modeBtn(mode === "expert")}>Экспертный</button>
              </div>
              <button onClick={() => setBasketOpen(true)} title="Корзина отбора"
                style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: 6, background: basket.length ? "var(--accent)" : "transparent", color: basket.length ? "#fff" : "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)" }}>
                <Icon name="bookmark" size={16} /> Корзина{basket.length ? " · " + basket.length : ""}
              </button>
            </div>
            {mode === "simple" ? (
              <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                <select value={prefix} onChange={(e) => setPrefix(e.target.value)} style={selStyle}>
                  {PREFIXES.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
                </select>
                <div style={{ flex: 1, minWidth: 240 }}>
                  <SearchBar value={q} onChange={onQuery} onSearch={(v: string) => runSearch(db, prefix, v, 1)} suggestions={sug}
                    onPickSuggestion={(s: any) => { const term = typeof s === "string" ? s : s.term; setQ(term); runSearch(db, prefix, term, 1); }}
                    placeholder="Поиск по каталогу" buttonLabel="Найти" />
                </div>
              </div>
            ) : mode === "expert" ? (
              <div style={{ marginBottom: 14, background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
                <label htmlFor="expert-expr" style={{ display: "block", fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 6 }}>Поисковое выражение ИРБИС</label>
                <textarea id="expert-expr" value={expertExpr} onChange={(e) => setExpertExpr(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) runExpert(); }}
                  rows={3} spellCheck={false} placeholder={'Например: "K=Android" + "K=PHP"'}
                  style={{ width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", background: "var(--surface-card,#fff)", color: "var(--text-body)", resize: "vertical" }} />
                <div style={{ marginTop: 8, fontSize: "var(--text-xs)", color: "var(--text-subtle)", lineHeight: 1.6 }}>
                  Операторы: <b>*</b> И · <b>+</b> ИЛИ · <b>^</b> НЕ · <b>$</b> усечение · префиксы <code style={{ fontFamily: "var(--font-mono)" }}>K=</code>/<code style={{ fontFamily: "var(--font-mono)" }}>A=</code>/<code style={{ fontFamily: "var(--font-mono)" }}>T=</code>/<code style={{ fontFamily: "var(--font-mono)" }}>V=</code>. Термин в кавычках, напр. <code style={{ fontFamily: "var(--font-mono)" }}>"K=Android"</code>.
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 10, justifyContent: "flex-end" }}>
                  <Button variant="ghost" onClick={() => setExpertExpr("")}>Очистить</Button>
                  <Button iconLeft="search" onClick={runExpert}>Найти</Button>
                </div>
              </div>
            ) : (
              <div style={{ marginBottom: 14, background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 14 }}>
                {advRows.map((r, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                    {i > 0
                      ? <select value={advCombine} onChange={(e) => setAdvCombine(e.target.value as any)} style={{ ...selStyle, width: 86 }}><option value="and">И</option><option value="or">ИЛИ</option></select>
                      : <span style={{ width: 86, fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>где</span>}
                    <select value={r.field} onChange={(e) => setAdvRows((rows) => rows.map((x, j) => j === i ? { ...x, field: e.target.value } : x))} style={selStyle}>
                      {PREFIXES.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
                    </select>
                    <input value={r.value} onChange={(e) => setAdvRows((rows) => rows.map((x, j) => j === i ? { ...x, value: e.target.value } : x))}
                      onKeyDown={(e) => { if (e.key === "Enter") runAdvanced(); }} placeholder="значение" style={{ flex: 1, minWidth: 160, padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)" }} />
                    {advRows.length > 1 && <button onClick={() => setAdvRows((rows) => rows.filter((_, j) => j !== i))} style={iconBtn} title="Убрать условие">×</button>}
                  </div>
                ))}
                <div style={{ display: "flex", gap: 8, marginTop: 6, alignItems: "center" }}>
                  <button onClick={() => setAdvRows((rows) => [...rows, { field: "K", value: "" }])} style={iconBtn}>+ условие</button>
                  <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                    <Button variant="ghost" onClick={() => setAdvRows([{ field: "A", value: "" }, { field: "T", value: "" }])}>Сброс</Button>
                    <Button iconLeft="search" onClick={runAdvanced}>Найти</Button>
                  </div>
                </div>
              </div>
            )}
            {loading && !items.length ? <div style={{ color: "var(--text-subtle)" }}>Поиск…</div> :
              total === 0 && !activeFacets.length ? <EmptyState icon="search" title="Ничего не найдено" description="Измените запрос или область поиска." /> :
                <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
                  <div style={{ flex: "1 1 200px", minWidth: 180, maxWidth: 260, order: 1 }} className="irb-facet-rail">
                    <FacetRail facets={facets} active={activeFacets} onToggle={toggleFacet} />
                  </div>
                  <div style={{ flex: "100 1 380px", minWidth: 280, order: 2 }}>
                    {activeFacets.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", margin: "0 0 12px" }}>
                        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Фильтры:</span>
                        {activeFacets.map((a) => (
                          <FilterChip key={a.field + a.value} label={a.valueLabel} group={a.groupLabel} onRemove={() => removeFacet(a)} />
                        ))}
                        <button onClick={() => applyFacets([])} style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontSize: "var(--text-xs)" }}>Сбросить все</button>
                      </div>
                    )}
                    <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", margin: "4px 0 10px" }}>Найдено: {total} · страница {page} из {pageCount}</div>
                    {total === 0 ? <EmptyState icon="search" title="Ничего не найдено" description="Снимите часть фильтров и повторите поиск." /> : <>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {items.map((it) => <ResultCard key={it.mfn} item={it} dbTag="Книги" typeIcon="book" showCheck={true} checked={inBasket(it.mfn)} onToggleCheck={() => toggleBasket(it)} onOpen={() => openRecord(it.mfn)} />)}
                      </div>
                      <div style={{ marginTop: 14 }}><Pagination page={page} pageCount={pageCount} total={total} onPage={gotoPage} /></div>
                    </>}
                  </div>
                </div>}
          </>
        )}

        {rec && (
          <RecordCard
            rec={rec} db={DB} tab={recTab} setTab={setRecTab}
            shareOpen={shareOpen} setShareOpen={setShareOpen}
            permalink={permalink()} onCopyPermalink={copyPermalink}
            onBack={closeRecord} onOrder={() => order(rec.mfn)}
            onSubject={(t: string) => { setMode("simple"); setPrefix("K"); setQ(t); closeRecord(); runSearch(db, "K", t, 1); }}
            inBasket={inBasket(rec.mfn)}
            onToggleBasket={() => toggleBasket({ mfn: rec.mfn, title: rec.brief || "", author: recView(rec).meta.find((m) => m.label === "Авторы")?.value, year: recView(rec).meta.find((m) => m.label === "Выходные данные")?.value })}
          />
        )}
        </>
        )}
      </main>

      <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 20px", fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "flex", gap: 10, alignItems: "center" }}>
        <Icon name="globe" size={14} />
        <span>Производственный клиент поверх ИРБИС64 (база {DB}). Работает в защищённом контуре.</span>
      </footer>

      {loginOpen && <LoginOverlay onClose={() => setLoginOpen(false)} onSubmit={doLogin} />}
      {staffLoginOpen && <StaffLoginOverlay onClose={() => setStaffLoginOpen(false)} onSubmit={doStaffLogin} />}
      {basketOpen && <BasketPanel items={basket} onClose={() => setBasketOpen(false)} onRemove={removeFromBasket} onClear={() => setBasket([])} toast={toast} />}
      <ToastViewport toasts={toasts} onDismiss={(id: number) => setToasts((x) => x.filter((y) => y.id !== id))} />
    </div>
  );
}

function FacetRail({ facets, active, onToggle }: {
  facets: Facet[];
  active: ActiveFacet[];
  onToggle: (f: Facet, v: { value: string; label: string }) => void;
}) {
  const groups = facets.filter((f) => f.values.length > 0);
  if (!groups.length) return null;
  return (
    <aside aria-label="Уточнение поиска" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", color: "var(--text-body)" }}>Уточнить</div>
      {groups.map((f) => (
        <div key={f.field}>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 8 }}>{f.label}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {f.values.map((v) => {
              const on = active.some((a) => a.field === f.field && a.value === v.value);
              return (
                <FilterChip key={v.value} label={v.label} count={v.count} pressed={on}
                  onToggle={() => onToggle(f, { value: v.value, label: v.label })} />
              );
            })}
          </div>
        </div>
      ))}
    </aside>
  );
}

function CabinetScreen({ cab, ticket, onBack, onLogout }: { cab: CabinetData | null; ticket?: string; onBack: () => void; onLogout: () => void }) {
  const loanLine = (l: any) => Object.values(l.subfields).filter(Boolean).join(" · ") || l.value;
  return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К поиску</Button>
      <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: "8px 0 2px" }}>Личный кабинет</h2>
      <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", marginTop: 0 }}>{cab?.name || "Читатель"}{ticket ? " · билет № " + ticket : ""}</p>
      <div style={{ fontWeight: 600, margin: "16px 0 8px" }}>Формуляр · книги на руках: {cab?.loanCount ?? 0}</div>
      {cab && cab.loans.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {cab.loans.map((l, i) => (
            <div key={i} style={{ background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 10, padding: "10px 14px", fontSize: "var(--text-sm)", display: "flex", gap: 10, alignItems: "center" }}>
              <Icon name="book" size={15} style={{ color: "var(--text-subtle)", flexShrink: 0 }} />
              <span style={{ flex: 1 }}>{loanLine(l)}</span>
            </div>
          ))}
        </div>
      ) : <EmptyState icon="check-circle" title="На руках книг нет" description="Все издания возвращены, либо формуляр пуст." />}
      <div style={{ marginTop: 20 }}><Button variant="ghost" onClick={onLogout}>Выйти из кабинета</Button></div>
    </div>
  );
}

function LoginOverlay({ onClose, onSubmit }: { onClose: () => void; onSubmit: (t: string) => void }) {
  const [t, setT] = React.useState("");
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--surface-card, #fff)", color: "var(--text-body)", borderRadius: 16, padding: 22, width: 320, boxShadow: "var(--shadow-lg, 0 20px 50px rgba(0,0,0,.25))" }}>
        <div style={{ fontWeight: 600, fontSize: "var(--text-lg)", marginBottom: 8 }}>Вход в личный кабинет</div>
        <p style={{ margin: "0 0 12px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Войдите по номеру читательского билета.</p>
        <input value={t} onChange={(e) => setT(e.target.value)} placeholder="Номер билета" onKeyDown={(e) => { if (e.key === "Enter") onSubmit(t); }}
          style={{ width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", marginBottom: 12 }} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={() => onSubmit(t)}>Войти</Button>
        </div>
      </div>
    </div>
  );
}

// --- Карточка записи с вкладками ------------------------------------------
const REC_TABS = ["Описание", "Экземпляры", "Электронные версии", "Метки MARC"];

function RecordCard({ rec, db, tab, setTab, shareOpen, setShareOpen, permalink, onCopyPermalink, onBack, onOrder, onSubject, inBasket, onToggleBasket }: {
  rec: RecordData; db: string; tab: number; setTab: (n: number) => void;
  shareOpen: boolean; setShareOpen: (b: boolean) => void;
  permalink: string; onCopyPermalink: () => void;
  onBack: () => void; onOrder: () => void; onSubject: (t: string) => void;
  inBasket: boolean; onToggleBasket: () => void;
}) {
  const v = recView(rec);
  const tabRefs = React.useRef<(HTMLButtonElement | null)[]>([]);
  const lbl: React.CSSProperties = { fontWeight: 600, fontSize: "var(--text-sm)", margin: "0 0 8px" };
  const onTabKey = (e: React.KeyboardEvent, i: number) => {
    let next = i;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (i + 1) % REC_TABS.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (i - 1 + REC_TABS.length) % REC_TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = REC_TABS.length - 1;
    else return;
    e.preventDefault(); setTab(next); tabRefs.current[next]?.focus();
  };
  const tabBtn = (active: boolean): React.CSSProperties => ({
    background: "none", border: "none", borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
    color: active ? "var(--accent)" : "var(--text-subtle)", fontWeight: active ? 600 : 500,
    padding: "8px 12px", cursor: "pointer", fontSize: "var(--text-sm)", fontFamily: "var(--font-ui, inherit)", whiteSpace: "nowrap",
  });
  return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К результатам</Button>
      <div style={{ display: "flex", gap: 24, marginTop: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        {rec.hasCover && <img alt="обложка" src={api.coverUrl(db, rec.mfn)} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} style={{ width: 180, borderRadius: 10, border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)" }} />}
        <div style={{ flex: 1, minWidth: 300 }}>
          <h2 style={{ fontFamily: "var(--font-record-title, inherit)", fontSize: "var(--text-2xl, 1.5rem)", lineHeight: 1.3, margin: "2px 0 12px" }}>{v.brief}</h2>

          {/* Действия: заказ, корзина, поделиться, экспорт */}
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 14, position: "relative" }}>
            <Button iconLeft="bookmark" onClick={onOrder}>Заказать</Button>
            <button onClick={onToggleBasket} title={inBasket ? "Убрать из корзины" : "Добавить в корзину"}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, background: inBasket ? "var(--accent-weak,#eef2f7)" : "transparent", color: inBasket ? "var(--accent)" : "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)" }}>
              <Icon name={inBasket ? "check" : "plus"} size={15} /> {inBasket ? "В корзине" : "В корзину"}
            </button>
            <button onClick={() => setShareOpen(!shareOpen)} aria-expanded={shareOpen} title="Поделиться"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "transparent", color: "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)" }}>
              <Icon name="share" size={15} /> Поделиться
            </button>
            <span style={{ width: 1, height: 22, background: "var(--border-subtle)" }} aria-hidden="true" />
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Экспорт:</span>
            <button onClick={() => exportRecord(rec, "ris")} style={exportBtn} title="Экспорт в формате RIS"><Icon name="download" size={14} /> RIS</button>
            <button onClick={() => exportRecord(rec, "bib")} style={exportBtn} title="Экспорт в формате BibTeX"><Icon name="download" size={14} /> BibTeX</button>
            <button onClick={() => exportRecord(rec, "gost")} style={exportBtn} title="Экспорт по ГОСТ Р 7.0.100"><Icon name="download" size={14} /> ГОСТ</button>
            {shareOpen && (
              <div role="dialog" aria-label="Постоянная ссылка" style={{ position: "absolute", top: "100%", left: 0, marginTop: 8, zIndex: 20, background: "var(--surface-card,#fff)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 10, padding: 12, boxShadow: "var(--shadow-lg, 0 12px 30px rgba(0,0,0,.18))", width: "min(460px, 92vw)" }}>
                <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}><Icon name="link" size={15} /> Постоянная ссылка</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <input readOnly value={permalink} aria-label="Постоянная ссылка на запись" onFocus={(e) => e.currentTarget.select()}
                    style={{ flex: 1, minWidth: 0, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", background: "var(--surface-sunken,#f5f5f5)", color: "var(--text-body)" }} />
                  <Button size="sm" iconLeft="copy" onClick={onCopyPermalink}>Копировать</Button>
                </div>
              </div>
            )}
          </div>

          {/* Вкладки */}
          <div role="tablist" aria-label="Разделы записи" style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--border-subtle)", overflowX: "auto" }}>
            {REC_TABS.map((t, i) => (
              <button key={t} role="tab" id={"rectab-" + i} aria-selected={tab === i} aria-controls={"recpanel-" + i}
                tabIndex={tab === i ? 0 : -1} ref={(el) => { tabRefs.current[i] = el; }}
                onClick={() => setTab(i)} onKeyDown={(e) => onTabKey(e, i)} style={tabBtn(tab === i)}>
                {t}{i === 1 && v.holds.length ? " (" + v.holds.length + ")" : ""}{i === 2 && v.files.length ? " (" + v.files.length + ")" : ""}
              </button>
            ))}
          </div>

          <div role="tabpanel" id={"recpanel-" + tab} aria-labelledby={"rectab-" + tab} tabIndex={0} style={{ paddingTop: 16, outline: "none" }}>
            {tab === 0 && (
              <div>
                {v.meta.length > 0 ? (
                  <dl style={{ display: "grid", gridTemplateColumns: "minmax(120px,160px) 1fr", gap: "6px 14px", margin: "0 0 4px", fontSize: "var(--text-sm)" }}>
                    {v.meta.map((m, i) => <React.Fragment key={i}><dt style={{ color: "var(--text-subtle)" }}>{m.label}</dt><dd style={{ margin: 0 }}>{m.value}</dd></React.Fragment>)}
                  </dl>
                ) : <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Описание отсутствует.</div>}
                {v.subjects.length > 0 && <div style={{ marginTop: 18 }}><div style={lbl}>Темы и рубрики</div><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {v.subjects.map((s, i) => <span key={i} role="button" tabIndex={0}
                    onClick={() => onSubject(s.split(" — ")[0])}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSubject(s.split(" — ")[0]); } }}
                    style={{ cursor: "pointer", background: "var(--accent-weak, #eef2f7)", color: "var(--accent)", padding: "3px 11px", borderRadius: 999, fontSize: "var(--text-xs)" }}>{s}</span>)}
                </div></div>}
              </div>
            )}
            {tab === 1 && (
              v.holds.length ?
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {v.holds.map((h, i) => <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", padding: "9px 0", borderTop: i ? "1px solid var(--border-subtle)" : "none", fontSize: "var(--text-sm)" }}>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-subtle)", flex: "none", minWidth: 90 }}>{h.inv || "—"}</span>
                    <span style={{ flex: 1, minWidth: 0 }}>{h.loc || "на руках у читателя"}</span>
                    <span style={statusChip(h.st)}>{(STATUS[h.st] || STATUS.unknown).label}</span>
                  </div>)}
                </div> :
                <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Сведения об экземплярах в записи отсутствуют.</div>
            )}
            {tab === 2 && (
              v.files.length ?
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {v.files.map((f, i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "var(--text-sm)" }}>
                    <Icon name="file-text" size={16} style={{ color: "var(--text-subtle)", flexShrink: 0 }} />
                    {f.url
                      ? <a href={f.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: 5 }}>{f.name || f.url} <Icon name="external-link" size={13} /></a>
                      : <span>{f.name}</span>}
                  </div>)}
                </div> :
                <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Электронные версии к записи не прикреплены.</div>
            )}
            {tab === 3 && (
              <div dangerouslySetInnerHTML={{ __html: `<table style="border-collapse:collapse;width:100%">${v.rawRows}</table>` }} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const exportBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 5, background: "var(--surface-card,#fff)",
  color: "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8,
  padding: "6px 10px", cursor: "pointer", fontSize: "var(--text-xs)",
};

// --- Корзина (отбор) — модальная панель -----------------------------------
function BasketPanel({ items, onClose, onRemove, onClear, toast }: {
  items: ResultItem[]; onClose: () => void; onRemove: (mfn: number) => void; onClear: () => void;
  toast: (t: { variant: string; title: string; message?: string }) => void;
}) {
  const empty = items.length === 0;
  const exp = (fmt: "ris" | "bib" | "txt") => { if (empty) return; exportBasket(items, fmt); };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", justifyContent: "flex-end", zIndex: 60 }}>
      <div onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Корзина отбора"
        style={{ background: "var(--surface-card, #fff)", color: "var(--text-body)", width: "min(440px, 96vw)", height: "100%", boxShadow: "var(--shadow-lg, -10px 0 40px rgba(0,0,0,.25))", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 18px", borderBottom: "1px solid var(--border-subtle)" }}>
          <Icon name="bookmark" size={18} />
          <b style={{ fontSize: "var(--text-lg)" }}>Корзина отбора</b>
          <span style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>· {items.length}</span>
          <button onClick={onClose} aria-label="Закрыть корзину" style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-subtle)" }}><Icon name="x" size={20} /></button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 18px" }}>
          {empty ? (
            <EmptyState icon="bookmark" title="Корзина пуста" description="Отметьте издания в результатах поиска флажком, чтобы добавить их сюда." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {items.map((it) => (
                <div key={it.mfn} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)" }}>{it.title || "[Без заглавия]"}</div>
                    {(it.author || it.year) && <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 2 }}>{[it.author, it.year].filter(Boolean).join(" · ")}</div>}
                  </div>
                  <button onClick={() => onRemove(it.mfn)} aria-label={"Убрать из корзины: " + (it.title || "")} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-subtle)", flexShrink: 0 }}><Icon name="trash" size={16} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Экспорт отобранного списка</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={() => exp("ris")} disabled={empty} style={{ ...exportBtn, opacity: empty ? .5 : 1, cursor: empty ? "not-allowed" : "pointer" }}><Icon name="download" size={14} /> RIS</button>
            <button onClick={() => exp("bib")} disabled={empty} style={{ ...exportBtn, opacity: empty ? .5 : 1, cursor: empty ? "not-allowed" : "pointer" }}><Icon name="download" size={14} /> BibTeX</button>
            <button onClick={() => exp("txt")} disabled={empty} style={{ ...exportBtn, opacity: empty ? .5 : 1, cursor: empty ? "not-allowed" : "pointer" }}><Icon name="download" size={14} /> Текст</button>
            <a href={empty ? undefined : basketMailto(items)} onClick={(e) => { if (empty) e.preventDefault(); }}
              style={{ ...exportBtn, textDecoration: "none", opacity: empty ? .5 : 1, cursor: empty ? "not-allowed" : "pointer", marginLeft: "auto" }}><Icon name="share" size={14} /> Отправить на почту</a>
          </div>
          {!empty && <Button variant="ghost" onClick={() => { onClear(); toast({ variant: "info", title: "Корзина очищена" }); }}>Очистить корзину</Button>}
        </div>
      </div>
    </div>
  );
}
