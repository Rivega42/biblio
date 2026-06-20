import React from "react";
import { api, LANG } from "./api";
import type { RecordData, ResultItem, FieldVal, DbItem, CabinetData } from "./api";
import { Button } from "../components/forms/Button.jsx";
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

const PREFIXES = [
  { code: "K", label: "Ключевые слова" }, { code: "A", label: "Автор" },
  { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
];
const esc = (s: string) => (s || "").replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]!));
const sf = (f: FieldVal | undefined, c: string) =>
  !f ? "" : (f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "");

interface Toast { id: number; variant: string; title: string; message?: string; }

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
    ? d.holdings.map((h) => ({ loc: "Основной фонд", inv: h.inv_no, st: h.status, cell: h.cell, rfid: h.rfid }))
    : F("910").map((h) => ({ loc: sf(h, "D") || "Фонд", inv: sf(h, "B"),
        st: (sf(h, "A") === "0" || sf(h, "A") === "") ? "available" : "issued", cell: "", rfid: "" }));
  const files = ["951", "955"].flatMap(F).map((f) => sf(f, "A") || sf(f, "T")).filter(Boolean);
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
  const [mode, setMode] = React.useState<"simple" | "advanced">("simple");
  const [advRows, setAdvRows] = React.useState([{ field: "A", value: "" }, { field: "T", value: "" }]);
  const [advCombine, setAdvCombine] = React.useState<"and" | "or">("and");
  const [sug, setSug] = React.useState<any[]>([]);
  const [items, setItems] = React.useState<ResultItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(false);
  const [rec, setRec] = React.useState<RecordData | null>(null);
  const [showRaw, setShowRaw] = React.useState(false);
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
      runSearch(startDb, "K", "Android", 1);
    })();
  }, []);

  async function runSearch(database: string, px: string, query: string, pg: number) {
    if (!query.trim()) return;
    setLoading(true); setRec(null); setSug([]); setPage(pg);
    const r = await api.search(database, px, query, pg, pageSize);
    if (r.json?.ok && r.json.data) { setItems(r.json.data.items); setTotal(r.json.data.total); }
    else { toast({ variant: "error", title: "Каталог недоступен", message: "Повторите попытку позже." }); setItems([]); setTotal(0); }
    setLoading(false);
  }
  function onQuery(v: string) {
    setQ(v); clearTimeout(tRef.current);
    if (v.trim().length < 2) { setSug([]); return; }
    tRef.current = setTimeout(async () => {
      const r = await api.terms(prefix + "=" + v.toUpperCase(), 8);
      if (r.json?.ok && r.json.data) setSug(r.json.data.terms.filter((t) => t.term.indexOf(prefix + "=") === 0).map((t) => ({ term: t.term.slice(prefix.length + 1), count: t.count })));
    }, 200);
  }
  async function runExpr(database: string, expr: string, pg: number) {
    setLoading(true); setRec(null); setPage(pg);
    const r = await api.searchExpr(database, expr, pg, pageSize);
    if (r.json?.ok && r.json.data) { setItems(r.json.data.items); setTotal(r.json.data.total); }
    else { toast({ variant: "error", title: "Каталог недоступен", message: "Повторите попытку позже." }); setItems([]); setTotal(0); }
    setLoading(false);
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
    runExpr(db, expr, 1);
  }

  async function openRecord(mfn: number) { setLoading(true); const r = await api.record(db, mfn); setLoading(false); if (r.json?.ok && r.json.data) { setRec(r.json.data); window.scrollTo(0, 0); } }
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
              <div style={{ display: "flex", gap: 4, padding: 2, background: "var(--surface-sunken,#eee)", borderRadius: 10 }}>
                <button onClick={() => setMode("simple")} style={modeBtn(mode === "simple")}>Простой</button>
                <button onClick={() => setMode("advanced")} style={modeBtn(mode === "advanced")}>Расширенный</button>
              </div>
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
            {loading ? <div style={{ color: "var(--text-subtle)" }}>Поиск…</div> :
              total === 0 ? <EmptyState icon="search" title="Ничего не найдено" description="Измените запрос или область поиска." /> :
                <>
                  <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", margin: "4px 0 10px" }}>Найдено: {total} · страница {page} из {pageCount}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {items.map((it) => <ResultCard key={it.mfn} item={it} dbTag="Книги" typeIcon="book" showCheck={false} onOpen={() => openRecord(it.mfn)} />)}
                  </div>
                  <div style={{ marginTop: 14 }}><Pagination page={page} pageCount={pageCount} total={total} onPage={(p: number) => { const ex = mode === "advanced" ? buildAdvExpr() : null; ex ? runExpr(db, ex, p) : runSearch(db, prefix, q, p); }} /></div>
                </>}
          </>
        )}

        {rec && (() => {
          const v = recView(rec);
          const lbl: React.CSSProperties = { fontWeight: 600, fontSize: "var(--text-sm)", margin: "18px 0 8px" };
          return (
            <div>
              <Button iconLeft="arrow-left" onClick={() => { setRec(null); setShowRaw(false); }}>К результатам</Button>
              <div style={{ display: "flex", gap: 24, marginTop: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
                {rec.hasCover && <img alt="обложка" src={api.coverUrl(DB, rec.mfn)} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} style={{ width: 180, borderRadius: 10, border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)" }} />}
                <div style={{ flex: 1, minWidth: 300 }}>
                  <h2 style={{ fontFamily: "var(--font-record-title, inherit)", fontSize: "var(--text-2xl, 1.5rem)", lineHeight: 1.3, margin: "2px 0 4px" }}>{v.brief}</h2>
                  {v.meta.length > 0 && (
                    <dl style={{ display: "grid", gridTemplateColumns: "minmax(120px,160px) 1fr", gap: "6px 14px", margin: "14px 0 0", fontSize: "var(--text-sm)" }}>
                      {v.meta.map((m, i) => <React.Fragment key={i}><dt style={{ color: "var(--text-subtle)" }}>{m.label}</dt><dd style={{ margin: 0 }}>{m.value}</dd></React.Fragment>)}
                    </dl>
                  )}
                  {v.subjects.length > 0 && <><div style={lbl}>Темы и рубрики</div><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {v.subjects.map((s, i) => <span key={i} onClick={() => { setMode("simple"); setPrefix("K"); setQ(s.split(" — ")[0]); runSearch(db, "K", s.split(" — ")[0], 1); }} style={{ cursor: "pointer", background: "var(--accent-weak, #eef2f7)", color: "var(--accent)", padding: "3px 11px", borderRadius: 999, fontSize: "var(--text-xs)" }}>{s}</span>)}
                  </div></>}
                  {v.files.length > 0 && <><div style={lbl}>Электронная версия</div>{v.files.map((f, i) => <div key={i} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}><Icon name="file-text" size={15} />{f}<span style={{ fontSize: "var(--text-xs)" }}>· документ pdf-формата</span></div>)}</>}
                  <div style={lbl}>Экземпляры</div>
                  {v.holds.length ?
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}><tbody>
                      {v.holds.map((h, i) => <tr key={i}>
                        <td style={{ padding: "4px 0" }}>{h.loc}</td>
                        <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-subtle)" }}>{h.inv}</td>
                        <td>{(h as any).cell ? <span title={"RFID " + (h as any).rfid} style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--accent)", background: "var(--accent-weak,#eef2f7)", borderRadius: 6, padding: "1px 8px" }}>⬚ {(h as any).cell}</span> : null}</td>
                        <td style={{ textAlign: "right" }}><StatusBadge status={(h.st === "available" || h.st === "issued" || h.st === "unknown") ? h.st as any : (h.st === "0" || h.st === "" ? "available" : "issued")} dot /></td>
                      </tr>)}
                    </tbody></table> :
                    <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Сведения об экземплярах в записи отсутствуют.</div>}
                  <div style={{ marginTop: 20, display: "flex", gap: 10, alignItems: "center" }}>
                    <Button iconLeft="bookmark" onClick={() => order(rec.mfn)}>Заказать</Button>
                    <button onClick={() => setShowRaw((x) => !x)} style={{ background: "none", border: "none", color: "var(--text-subtle)", cursor: "pointer", fontSize: "var(--text-xs)" }}>{showRaw ? "Скрыть" : "Показать"} все поля (MARC)</button>
                  </div>
                  {showRaw && <div style={{ marginTop: 12, borderTop: "1px solid var(--border-subtle)", paddingTop: 8 }} dangerouslySetInnerHTML={{ __html: `<table style="border-collapse:collapse;width:100%">${v.rawRows}</table>` }} />}
                </div>
              </div>
            </div>
          );
        })()}
        </>
        )}
      </main>

      <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 20px", fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "flex", gap: 10, alignItems: "center" }}>
        <Icon name="globe" size={14} />
        <span>Производственный клиент поверх ИРБИС64 (база {DB}). Работает в защищённом контуре.</span>
      </footer>

      {loginOpen && <LoginOverlay onClose={() => setLoginOpen(false)} onSubmit={doLogin} />}
      {staffLoginOpen && <StaffLoginOverlay onClose={() => setStaffLoginOpen(false)} onSubmit={doStaffLogin} />}
      <ToastViewport toasts={toasts} onDismiss={(id: number) => setToasts((x) => x.filter((y) => y.id !== id))} />
    </div>
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
