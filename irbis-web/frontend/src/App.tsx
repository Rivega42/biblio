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
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { StaffArea, StaffLoginOverlay } from "./Staff";
import type { StaffSession } from "./Staff";
import { exportRecord, exportBasket, basketMailto } from "./export";
import { HomeScreen } from "./reader/HomeScreen";
import { GalleryGrid } from "./reader/GalleryGrid";
import { CalendarGrid } from "./reader/CalendarGrid";
import { ArchiveList } from "./reader/ArchiveList";
import { ResultsToolbar, sortItems } from "./reader/ResultsToolbar";
import type { ViewMode, SortKey } from "./reader/ResultsToolbar";
import { OrdersTab } from "./reader/OrdersTab";
import { NotificationInbox } from "./reader/NotificationInbox";
import { HoldsTab } from "./reader/HoldsTab";
import { ShelvesPanel, ShelfMenu } from "./reader/Shelves";
import { ReviewPanel } from "./reader/ReviewPanel";
import { SimilarRecommendations, ForYouRecommendations } from "./reader/Recommendations";
import { HistoryTab } from "./reader/HistoryTab";
import { SaveSearchButton, SavedSearchMenu, SavedSearchesPanel } from "./reader/SavedSearches";
import { ConsentBanner, ConsentToggle, EraseDataCard } from "./reader/Consent";
import { DocViewer } from "./reader/DocViewer";
import type { DocPage } from "./reader/DocViewer";
import type { SavedSearch } from "./api";
import { layoutProfile, defaultLayout, layoutAllows } from "./reader/dbLayout";
import type { LayoutKind } from "./reader/dbLayout";

const PREFIXES = [
  { code: "K", label: "Ключевые слова" }, { code: "A", label: "Автор" },
  { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
];
const esc = (s: string) => (s || "").replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]!));
// Доменные статус-бейджи Style A: цвет текста + мягкая подложка + точка-индикатор.
// Значения берутся из Biblio-токенов (--status-*), мост даёт постамат/Книгоприём.
const STATUS: Record<string, { label: string; fg: string; bg: string }> = {
  available: { label: "В наличии", fg: "var(--status-available,#2E7D52)", bg: "var(--status-available-bg,#E4F0E8)" },
  issued: { label: "На руках", fg: "var(--status-issued,#9A6A12)", bg: "var(--status-issued-bg,#F7ECD6)" },
  hold: { label: "В постамате", fg: "var(--status-hold,#2F6DB5)", bg: "var(--status-hold-bg,#E3ECF8)" },
  returned: { label: "Книгоприём", fg: "var(--status-return,#6B5CA5)", bg: "var(--status-return-bg,#ECE8F6)" },
  unknown: { label: "Нет данных", fg: "var(--text-subtle,#8A857A)", bg: "var(--surface-2,#F0EEE6)" },
};
const statusChip = (s: string): React.CSSProperties => {
  const c = STATUS[s] || STATUS.unknown;
  return { display: "inline-flex", alignItems: "center", gap: 6, background: c.bg, color: c.fg, borderRadius: "var(--radius-md,6px)", padding: "4px 10px", fontSize: "var(--text-xs)", fontWeight: 600, whiteSpace: "nowrap" };
};
const statusDot = (s: string): React.CSSProperties => ({ width: 6, height: 6, borderRadius: 999, background: (STATUS[s] || STATUS.unknown).fg, flex: "none" });
const sf = (f: FieldVal | undefined, c: string) =>
  !f ? "" : (f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "");

interface Toast { id: number; variant: ToastVariant; title: string; message?: string; }
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
  // Biblio Style A is the default skin. MODE light/dark via data-mode, a11y via data-theme.
  const [darkMode, setDarkMode] = React.useState(false);
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
  // Постраничный просмотрщик (#222): открытый документ/набор страниц или null.
  const [docView, setDocView] = React.useState<{ pages: DocPage[]; idx: number; title?: string } | null>(null);
  // Корзина (отбор) — только в памяти, без localStorage (защищённый контур).
  const [basket, setBasket] = React.useState<ResultItem[]>([]);
  const [basketOpen, setBasketOpen] = React.useState(false);
  const [toasts, setToasts] = React.useState<Toast[]>([]);
  const [account, setAccount] = React.useState<{ loggedIn: boolean; ticket?: string }>({ loggedIn: false });
  const [loginOpen, setLoginOpen] = React.useState(false);
  const [view, setView] = React.useState<"search" | "cabinet">("search");
  const [cab, setCab] = React.useState<CabinetData | null>(null);
  const [cabinetSeen, setCabinetSeen] = React.useState(false);
  const [context, setContext] = React.useState<"reader" | "staff">("reader");
  const [staff, setStaff] = React.useState<StaffSession | null>(null);
  const [staffRoute, setStaffRoute] = React.useState<any>("desktop");
  const [staffLoginOpen, setStaffLoginOpen] = React.useState(false);
  // Discovery façade (G1): главная-лендинг показывается до первого поиска.
  const [home, setHome] = React.useState(true);
  // Представление выдачи (G4) и сортировка (G6) и размер страницы (G19).
  const [viewMode, setViewMode] = React.useState<ViewMode>("list");
  const [sort, setSort] = React.useState<SortKey>("relevance");
  const [pageSize, setPageSize] = React.useState(10);
  // Мульти-лейаут по типу базы (#222): активный вид выдачи (list/gallery/calendar/archive).
  // По умолчанию берётся из профиля базы; пользователь может переключать там, где доступно.
  const [layout, setLayout] = React.useState<LayoutKind>("list");
  // Тик для перезагрузки списка броней в кабинете после новой брони (#222).
  const [holdsRefresh, setHoldsRefresh] = React.useState(0);
  // Тик для перезагрузки полок «Для вас» (#133) — обновляем после просмотра записей,
  // т.к. подборка зависит от истории. Сохранённые запросы (#133) — после сохранения.
  const [forYouRefresh, setForYouRefresh] = React.useState(0);
  const [savedRefresh, setSavedRefresh] = React.useState(0);
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
      try {
        const p = new URLSearchParams(window.location.search);
        const linkDb = p.get("db"); const linkMfn = p.get("mfn");
        if (linkMfn && /^\d+$/.test(linkMfn)) {
          const useDb = linkDb || startDb; setDb(useDb);
          setHome(false); // permalink ведёт сразу к записи, минуя лендинг
          await openRecord(parseInt(linkMfn, 10), useDb);
        }
      } catch { /* ignore */ }
      // Иначе остаёмся на главной-лендинге (фасад discovery, G1) — без авто-поиска.
    })();
  }, []);

  // Мульти-лейаут (#222): при смене активной базы сбрасываем вид выдачи на дефолт
  // её профиля (book→list, image→gallery, perio→calendar, arch→archive). Внутри
  // одной базы пользовательский тумблер list/gallery сохраняется (db не меняется).
  React.useEffect(() => {
    const def = defaultLayout(db);
    setLayout(def);
    // Синхронизируем тумблер list/gallery, чтобы он отражал актуальный вид.
    if (def === "list" || def === "gallery") setViewMode(def);
  }, [db]);

  async function runSearch(database: string, px: string, query: string, pg: number) {
    if (!query.trim()) return;
    setHome(false); setLoading(true); setRec(null); setSug([]); setPage(pg);
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
  // С главной-лендинга: задаём поле/запрос, уходим в результаты и ищем (G1).
  function goSearch(px: string, query: string) {
    setHome(false); setMode("simple"); setPrefix(px); setQ(query); setRec(null);
    runSearch(db, px, query, 1);
  }
  // Сохранённые запросы (#133): повторно запустить сохранённый поиск. Если задан
  // префикс — простой поиск; иначе query трактуется как поисковое выражение.
  function runSavedSearch(s: SavedSearch) {
    const useDb = s.db || db;
    setDb(useDb); setView("search"); setRec(null); setHome(false);
    if (s.prefix) { setMode("simple"); setPrefix(s.prefix); setQ(s.query); runSearch(useDb, s.prefix, s.query, 1); }
    else { setMode("expert"); setExpertExpr(s.query); runExpr(useDb, s.query, 1, true); }
  }
  // Логотип / «Главная» — вернуться на лендинг (G1).
  function goHome() {
    setHome(true); setRec(null); setView("search");
    setItems([]); setTotal(0); setBaseExpr(null); setActiveFacets([]); setFacets([]);
    try { const u = new URL(window.location.href); u.searchParams.delete("db"); u.searchParams.delete("mfn"); window.history.replaceState(null, "", u.pathname); } catch { /* ignore */ }
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
    setHome(false); setLoading(true); setRec(null); setPage(pg);
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
  // Размер страницы (G19): меняем и перезапускаем текущий запрос с 1-й страницы.
  function changePageSize(size: number) {
    setPageSize(size);
    if (baseExpr != null) { setLoading(true); setRec(null); setPage(1); api.searchExpr(db, composeExpr(baseExpr, activeFacets), 1, size).then((r) => { if (r.json?.ok && r.json.data) { setItems(r.json.data.items); setTotal(r.json.data.total); } setLoading(false); }); }
    else if (mode === "advanced") { const ex = buildAdvExpr(); if (ex) { setLoading(true); setPage(1); api.searchExpr(db, ex, 1, size).then((r) => { if (r.json?.ok && r.json.data) { setItems(r.json.data.items); setTotal(r.json.data.total); } setLoading(false); }); } }
    else { setLoading(true); setPage(1); api.search(db, prefix, q, 1, size).then((r) => { if (r.json?.ok && r.json.data) { setItems(r.json.data.items); setTotal(r.json.data.total); } setLoading(false); }); }
  }

  async function openRecord(mfn: number, database: string = db) {
    setLoading(true); const r = await api.record(database, mfn); setLoading(false);
    if (r.json?.ok && r.json.data) {
      setRec(r.json.data); setRecTab(0); setShareOpen(false);
      // Постоянная ссылка: ?db=<db>&mfn=<mfn> в адресной строке без перезагрузки.
      try { const u = new URL(window.location.href); u.searchParams.set("db", database); u.searchParams.set("mfn", String(mfn)); window.history.replaceState(null, "", u.toString()); } catch { /* ignore */ }
      window.scrollTo(0, 0);
      // Просмотр записи влияет на историю и подборку «Для вас» (#133/#134) — обновим тик.
      setForYouRefresh((n) => n + 1);
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
  // Бронирование (#222): POST /api/hold → показываем итог (готов / позиция в очереди).
  // 404/501 — модуль брони ещё не подключён → мягкий тост, страница не падает.
  async function hold(mfn: number, database: string = db) {
    const r = await api.hold(database, mfn);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      const d = r.json.data;
      if (d.status === "ready") toast({ variant: "success", title: "Забронировано", message: "Издание готово к получению." });
      else toast({ variant: "success", title: "Вы в очереди", message: d.position ? "Ваша позиция: " + d.position + "-я." : "Бронь поставлена в очередь." });
      setHoldsRefresh((n) => n + 1);
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." }); setLoginOpen(true);
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Бронирование недоступно", message: "Модуль бронирования ещё подключается." });
    } else {
      toast({ variant: "error", title: "Не удалось забронировать", message: "Повторите попытку позже." });
    }
  }
  async function loadCabinet() {
    const r = await api.cabinet();
    if (r.json?.ok && r.json.data) {
      setCab(r.json.data); setView("cabinet"); setRec(null);
      // «06» — тёмная витрина: показываем кабинет в тёмной теме (если не a11y и
      // пользователь сам ещё не выбрал светлую в этой сессии). Тумблер остаётся рабочим.
      if (!a11y && !cabinetSeen) { setDarkMode(true); setCabinetSeen(true); }
    } else toast({ variant: "info", title: "Кабинет недоступен", message: "Войдите по читательскому билету." });
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

  // Skin: a11y high-contrast wins; otherwise Biblio Style A ("working" alias the
  // bridge maps to Style A). data-mode carries light/dark for the Biblio palette.
  const rootTheme = a11y ? "a11y" : "working";
  const rootMode = !a11y && darkMode ? "dark" : undefined;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const DB = db;
  // Человекочитаемое имя текущей базы для пилюли в шапке (G18).
  const dbName = (databases.find((d) => d.code === db)?.name) || db;
  const hbtn = (active: boolean): React.CSSProperties => ({ background: active ? "rgba(255,255,255,.25)" : "transparent", color: "#fff", border: "1px solid rgba(255,255,255,.45)", borderRadius: 8, padding: "5px 10px", cursor: "pointer", fontSize: "var(--text-xs)" });
  const selStyle: React.CSSProperties = { padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)", maxWidth: 240 };
  const modeBtn = (active: boolean): React.CSSProperties => ({ background: active ? "var(--accent)" : "transparent", color: active ? "var(--text-on-accent, #fff)" : "var(--text-body)", border: "none", borderRadius: 8, padding: "5px 12px", cursor: "pointer", fontSize: "var(--text-sm)" });
  const iconBtn: React.CSSProperties = { padding: "7px 11px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)", cursor: "pointer" };

  if (!ready) return <div style={{ padding: 40, color: "var(--text-subtle)" }}>Загрузка каталога…</div>;

  return (
    <div data-theme={rootTheme} data-mode={rootMode} style={{ minHeight: "100vh", background: "var(--bg-page)", color: "var(--text-body)", display: "flex", flexDirection: "column" }}>
      <header style={{ background: "var(--accent)", color: "var(--text-on-accent, #fff)", padding: "12px 20px", display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={goHome} title="На главную" aria-label="На главную"
          style={{ display: "inline-flex", alignItems: "center", gap: 12, background: "none", border: "none", padding: 0, cursor: "pointer", color: "inherit", font: "inherit" }}>
          <span style={{ width: 32, height: 32, borderRadius: 9, background: "rgba(255,255,255,.18)", display: "inline-flex", alignItems: "center", justifyContent: "center", flex: "none" }}><Icon name="book" size={19} /></span>
          <b style={{ fontFamily: "var(--font-record-title, inherit)", fontSize: "var(--text-lg)", letterSpacing: "-.01em" }}>Читательский портал</b>
        </button>
        {/* Пилюля текущей базы (G18) — контекст «где я ищу». */}
        {context === "reader" && !home && (
          <span title={"Текущая база поиска: " + dbName} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,.16)", border: "1px solid rgba(255,255,255,.34)", borderRadius: 999, padding: "3px 11px", fontSize: "var(--text-xs)", fontWeight: 600 }}>
            <Icon name="layers" size={13} /> {dbName}
          </span>
        )}
        <span style={{ opacity: .85, fontSize: "var(--text-xs)" }}>ИРБИС {server?.version}{home ? " · база " + DB : ""}</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 4, marginRight: 6, padding: 2, background: "rgba(255,255,255,.12)", borderRadius: 10 }}>
            <button onClick={() => switchContext("reader")} style={hbtn(context === "reader")}>Читатель</button>
            <button onClick={() => switchContext("staff")} style={hbtn(context === "staff")}>Сотрудник</button>
          </div>
          <button onClick={() => setDarkMode((v) => !v)} title="Светлая / тёмная тема" style={hbtn(darkMode && !a11y)}>{darkMode ? "Светлая" : "Тёмная"}</button>
          <button onClick={() => setA11y((v) => !v)} style={hbtn(a11y)}>A11y</button>
          {/* Почтовый ящик уведомлений (#222) — только для вошедшего читателя. */}
          {context === "reader" && account.loggedIn && <NotificationInbox />}
          {context === "reader" && account.loggedIn && <button onClick={loadCabinet} style={hbtn(view === "cabinet")}>Кабинет</button>}
          {context === "reader" && <button onClick={() => account.loggedIn ? (setAccount({ loggedIn: false }), setView("search"), setCab(null)) : setLoginOpen(true)} style={hbtn(false)}>{account.loggedIn ? "Выйти" : "Вход"}</button>}
          {context === "staff" && staff && <button onClick={() => { setStaff(null); setContext("reader"); }} style={hbtn(false)}>Выйти ({staff.login})</button>}
        </div>
      </header>

      <main style={{ flex: 1, maxWidth: 1100, width: "100%", margin: "0 auto", padding: 20, boxSizing: "border-box" }}>
        {context === "staff" ? (
          <StaffArea staff={staff!} route={staffRoute} setRoute={setStaffRoute} toast={toast} />
        ) : view === "cabinet" ? (
          <CabinetScreen cab={cab} ticket={account.ticket} toast={toast} holdsRefresh={holdsRefresh}
            onOpenRecord={(database, mfn) => { setView("search"); setHome(false); openRecord(mfn, database); }}
            onRunSearch={(s) => runSavedSearch(s)} onErased={() => { setHoldsRefresh((n) => n + 1); loadCabinet(); }}
            onBack={() => setView("search")} onLogout={() => { setAccount({ loggedIn: false }); setView("search"); setCab(null); }} />
        ) : home && !rec ? (
          /* Discovery façade (G1-G3, G17) — лендинг до первого поиска. */
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <HomeScreen
              databases={databases} db={db}
              onPickDb={(code) => setDb(code)}
              onSearch={(px, query) => goSearch(px, query)}
              onOpen={(mfn, database) => { setHome(false); openRecord(mfn, database); }}
            />
            {/* «Для вас» (#133) — персональная подборка; скрыта, если эндпойнт пуст/404. */}
            <ForYouRecommendations refreshKey={forYouRefresh}
              onOpen={(mfn, database) => { setHome(false); openRecord(mfn, database); }} />
          </div>
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
              <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                {/* Сохранённые запросы (#133): меню повтора + сохранение текущего поиска. */}
                <SavedSearchMenu toast={toast} onRun={runSavedSearch} refreshKey={savedRefresh} />
                {(total > 0 || baseExpr != null) && (
                  <SaveSearchButton
                    db={db}
                    prefix={mode === "simple" ? prefix : ""}
                    query={mode === "simple" ? q : (baseExpr || expertExpr)}
                    defaultName={mode === "simple" ? q : undefined}
                    toast={toast} onSaved={() => setSavedRefresh((n) => n + 1)} />
                )}
                <button onClick={() => setBasketOpen(true)} title="Корзина отбора"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, background: basket.length ? "var(--accent)" : "transparent", color: basket.length ? "#fff" : "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)" }}>
                  <Icon name="bookmark" size={16} /> Корзина{basket.length ? " · " + basket.length : ""}
                </button>
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
                    {/* Мульти-лейаут (#222): профиль базы задаёт вид. Для list/gallery-баз
                        вид следует тумблеру (viewMode); для calendar/archive — профилю. */}
                    {(() => {
                      const prof = layoutProfile(db);
                      const togglable = layoutAllows(db, "list") && layoutAllows(db, "gallery");
                      const effLayout: LayoutKind = togglable ? viewMode : prof.views[0];
                      const sorted = sortItems(items, sort);
                      return (
                        <>
                          <ResultsToolbar total={total} page={page} pageCount={pageCount}
                            view={viewMode} onView={setViewMode} sort={sort} onSort={setSort} showToggle={togglable} />
                          {total === 0 ? <EmptyState icon="search" title="Ничего не найдено" description="Снимите часть фильтров и повторите поиск." /> : <>
                            {effLayout === "gallery" ? (
                              <GalleryGrid items={sorted} db={db}
                                inBasket={inBasket} onToggleBasket={toggleBasket} onOpen={(mfn) => openRecord(mfn)}
                                onHold={(it) => hold(it.mfn, db)}
                                renderShelf={account.loggedIn ? (it) => <ShelfMenu db={db} mfn={it.mfn} title={it.title} toast={toast} compact /> : undefined} />
                            ) : effLayout === "calendar" ? (
                              <CalendarGrid items={sorted}
                                inBasket={inBasket} onToggleBasket={toggleBasket} onOpen={(mfn) => openRecord(mfn)} />
                            ) : effLayout === "archive" ? (
                              <ArchiveList items={sorted} startIndex={(page - 1) * pageSize}
                                inBasket={inBasket} onToggleBasket={toggleBasket} onOpen={(mfn) => openRecord(mfn)} />
                            ) : (
                              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                {sorted.map((it) => (
                                  <div key={it.mfn} style={{ position: "relative" }}>
                                    <ResultCard item={it} dbTag={dbName} typeIcon="book" showCheck={true} checked={inBasket(it.mfn)} onToggleCheck={() => toggleBasket(it)} onOpen={() => openRecord(it.mfn)} />
                                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "6px 0 2px 0", paddingLeft: 4 }}>
                                      <button type="button" onClick={() => hold(it.mfn, db)} title="Забронировать"
                                        style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "transparent", color: "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "5px 10px", cursor: "pointer", fontSize: "var(--text-xs)" }}>
                                        <Icon name="clock" size={14} /> Забронировать
                                      </button>
                                      {account.loggedIn && <ShelfMenu db={db} mfn={it.mfn} title={it.title} toast={toast} />}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                            <div style={{ marginTop: 14 }}><Pagination page={page} pageCount={pageCount} total={total} onPage={gotoPage} pageSize={pageSize} onPageSize={changePageSize} /></div>
                          </>}
                        </>
                      );
                    })()}
                  </div>
                </div>}
          </>
        )}

        {rec && (
          <RecordCard
            rec={rec} db={DB} tab={recTab} setTab={setRecTab}
            shareOpen={shareOpen} setShareOpen={setShareOpen}
            permalink={permalink()} onCopyPermalink={copyPermalink}
            onBack={closeRecord} onOrder={() => order(rec.mfn)} onHold={() => hold(rec.mfn, rec.db)}
            onSubject={(t: string) => { setMode("simple"); setPrefix("K"); setQ(t); closeRecord(); runSearch(db, "K", t, 1); }}
            loggedIn={account.loggedIn} readerName={cab?.name} toast={toast}
            onOpenRecord={(database, mfn) => openRecord(mfn, database)}
            onViewDoc={(pages, idx, title) => setDocView({ pages, idx, title })}
            inBasket={inBasket(rec.mfn)}
            onToggleBasket={() => toggleBasket({ mfn: rec.mfn, title: rec.brief || "", author: recView(rec).meta.find((m) => m.label === "Авторы")?.value, year: recView(rec).meta.find((m) => m.label === "Выходные данные")?.value })}
          />
        )}
        </>
        )}
      </main>

      <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 20px", fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "flex", gap: 10, alignItems: "center" }}>
        <Icon name="globe" size={14} />
        <span>Читательский портал поверх ИРБИС64 (база {DB}). Работает в защищённом контуре.</span>
      </footer>

      {loginOpen && <LoginOverlay onClose={() => setLoginOpen(false)} onSubmit={doLogin} />}
      {staffLoginOpen && <StaffLoginOverlay onClose={() => setStaffLoginOpen(false)} onSubmit={doStaffLogin} />}
      {basketOpen && <BasketPanel items={basket} onClose={() => setBasketOpen(false)} onRemove={removeFromBasket} onClear={() => setBasket([])} toast={toast} />}
      {docView && <DocViewer pages={docView.pages} startIndex={docView.idx} title={docView.title} onClose={() => setDocView(null)} />}
      {/* Согласие на обработку ПДн (#199) — баннер первого сеанса. Только для вошедшего
          читателя (не гость, не контекст сотрудника). Сам прячется при given/404. */}
      {context === "reader" && account.loggedIn && <ConsentBanner toast={toast} />}
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

// --- Личный кабинет (экран «06 Reader Cabinet») ----------------------------
// Формуляр читателя из живого ИРБИС: поле 40 с подполями
//   ^A шифр · ^B инв · ^C краткое описание · ^D дата выдачи · ^E план. возврата
//   ^F факт. возврата (****** = на руках) · ^L продление.
// Очередь брони / полки / челлендж — backend пока не отдаёт: показываем как
// демонстрационный UI (помечено «демо»), без обращения к несуществующим эндпойнтам.
const RU_MONTH = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
// Разбор даты ИРБИС YYYYMMDD → Date (локальная полночь) либо null.
function parseIrbisDate(s: string): Date | null {
  if (!s || !/^\d{8}$/.test(s)) return null;
  const y = +s.slice(0, 4), m = +s.slice(4, 6), d = +s.slice(6, 8);
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  const dt = new Date(y, m - 1, d);
  return isNaN(dt.getTime()) ? null : dt;
}
function fmtDate(dt: Date | null): string {
  return dt ? dt.getDate() + " " + RU_MONTH[dt.getMonth()] : "";
}
// Декоративная палитра подложек обложек-плейсхолдеров — токены Biblio
// (--cover-tint-*); hex оставлен как фолбэк на случай отсутствия токен-слоя.
const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

// Адаптив кабинета: на узких экранах профиль уезжает наверх, сетки в одну колонку.
const CAB_CSS = `
@media (max-width: 860px){
  .irb-cab-grid{grid-template-columns:1fr !important;}
  .irb-cab-2col,.irb-cab-3col{grid-template-columns:1fr !important;}
}`;
if (typeof document !== "undefined" && !document.getElementById("irb-cab-css")) {
  const s = document.createElement("style"); s.id = "irb-cab-css"; s.textContent = CAB_CSS; document.head.appendChild(s);
}

interface LoanView {
  title: string;
  meta: string;          // шифр · инв
  issued: Date | null;   // ^D
  due: Date | null;      // ^E
  returned: boolean;     // ^F != ******
  onHand: boolean;       // выдано и не возвращено
  renewals: number;      // ^L (число продлений), если есть
  tone: "ok" | "soon" | "over" | "done";
  dueLabel: string;
  daysWord: string;
}
// Краткое описание ^C обычно содержит «Автор. Заглавие [Текст] : … / …, ГОД. - … с.»
// Берём заглавную часть до первого « [» или « : » как заголовок; остальное служит подписью.
function loanTitle(desc: string, code: string): { title: string; sub: string } {
  const raw = (desc || "").trim();
  if (!raw) return { title: code || "Издание", sub: "" };
  let head = raw.split(/\s\[|\s:\s|\s\/\s/)[0].trim();
  if (head.length > 90) head = head.slice(0, 88).trim() + "…";
  // Подпись: остаток после заголовка (год / автор), ограниченный по длине.
  let sub = raw.slice(head.length).replace(/^[\s\[\]:/.,–-]+/, "").trim();
  if (sub.length > 70) sub = sub.slice(0, 68).trim() + "…";
  return { title: head || code || "Издание", sub };
}
function buildLoan(l: { value: string; subfields: Record<string, string> }, today: Date): LoanView {
  const sub = l.subfields || {};
  const get = (c: string) => sub[c] || sub[c.toUpperCase()] || sub[c.toLowerCase()] || "";
  const code = get("A"), inv = get("B"), desc = get("C");
  const issued = parseIrbisDate(get("D"));
  const due = parseIrbisDate(get("E"));
  const fact = get("F");
  const returned = !!fact && fact.indexOf("*") < 0; // реальная дата возврата
  const onHand = !returned;                          // ****** или пусто → на руках
  const renewals = (() => { const v = get("L"); const n = parseInt(v, 10); return isNaN(n) ? 0 : n; })();
  const t = loanTitle(desc, code);
  let tone: LoanView["tone"] = "ok";
  let dueLabel = due ? "до " + fmtDate(due) : "";
  let daysWord = "";
  if (returned) {
    tone = "done"; dueLabel = "возвращено";
  } else if (due) {
    const ms = due.getTime() - today.getTime();
    const days = Math.round(ms / 86400000);
    if (days < 0) {
      tone = "over"; daysWord = Math.abs(days) + " " + plural(Math.abs(days), "день", "дня", "дней"); dueLabel = "просрочено · " + daysWord;
    } else if (days <= 3) {
      tone = "soon"; daysWord = days === 0 ? "сегодня" : days + " " + plural(days, "день", "дня", "дней"); dueLabel = "до " + fmtDate(due) + " · скоро";
    } else {
      tone = "ok"; dueLabel = "до " + fmtDate(due);
    }
  }
  return {
    title: t.title, meta: [code, inv ? "инв. " + inv : ""].filter(Boolean).join(" · "),
    issued, due, returned, onHand, renewals, tone, dueLabel, daysWord,
  };
}
function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}
function initials(name: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "ЧТ";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}
const TONE_STATUS: Record<LoanView["tone"], string> = { ok: "available", soon: "issued", over: "unknown", done: "returned" };
function toneChip(tone: LoanView["tone"]): React.CSSProperties {
  if (tone === "over") return { display: "inline-flex", alignItems: "center", gap: 6, background: "color-mix(in srgb, var(--error) 18%, transparent)", color: "var(--error)", borderRadius: "var(--radius-md,6px)", padding: "4px 10px", fontSize: "var(--text-xs)", fontWeight: 600, whiteSpace: "nowrap" };
  return statusChip(TONE_STATUS[tone]);
}
function toneDot(tone: LoanView["tone"]): React.CSSProperties {
  const c = tone === "over" ? "var(--error)" : (STATUS[TONE_STATUS[tone]] || STATUS.unknown).fg;
  return { width: 6, height: 6, borderRadius: 999, background: c, flex: "none" };
}

function CabinetScreen({ cab, ticket, toast, holdsRefresh, onOpenRecord, onRunSearch, onErased, onBack, onLogout }: { cab: CabinetData | null; ticket?: string; toast: (t: { variant: ToastVariant; title: string; message?: string }) => void; holdsRefresh?: number; onOpenRecord?: (db: string, mfn: number) => void; onRunSearch?: (s: SavedSearch) => void; onErased?: () => void; onBack: () => void; onLogout: () => void }) {
  const [cabTab, setCabTab] = React.useState<"formular" | "orders" | "history" | "saved">("formular");
  const today = React.useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }, []);
  const loans = React.useMemo(() => (cab?.loans || []).map((l) => buildLoan(l, today)), [cab, today]);
  const onHand = loans.filter((l) => l.onHand);
  const returnedCount = loans.length - onHand.length;
  const overdue = onHand.filter((l) => l.tone === "over").length;
  const name = cab?.name || "Читатель";
  const cardSx: React.CSSProperties = { background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-xl,16px)", boxShadow: "var(--shadow-sm)" };
  const h2Sx: React.CSSProperties = { fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-xl,1.25rem)", letterSpacing: "-.02em", margin: 0 };
  const demoHint: React.CSSProperties = { display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px", borderRadius: 999, background: "var(--surface-sunken)", color: "var(--text-subtle)", fontSize: "var(--text-2xs,11px)", fontWeight: 600, letterSpacing: ".02em" };

  // Челлендж остаётся демонстрационным (вне объёма #222) — помечен «демо».
  const challengeGoal = 50, challengeDone = Math.min(returnedCount + 35, 49);
  const pct = Math.round((challengeDone / challengeGoal) * 100);
  // Реальное число активных броней (#222) для статистики профиля; 0 пока не загружено
  // или модуль брони недоступен.
  const [holdsCount, setHoldsCount] = React.useState(0);
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.holds();
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setHoldsCount(r.json.data.items.length);
      else setHoldsCount(0);
    })();
    return () => { alive = false; };
  }, [holdsRefresh]);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
        <Button variant="secondary" size="sm" iconLeft="arrow-left" onClick={onBack}>К каталогу</Button>
        <span style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Мой кабинет</span>
      </div>
      <div className="irb-cab-grid" style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 24, alignItems: "start" }}>

        {/* ===== Профиль + челлендж ===== */}
        <aside aria-label="Профиль читателя" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ ...cardSx, padding: 22, textAlign: "center" }}>
            <span aria-hidden="true" style={{ width: 64, height: 64, borderRadius: 999, background: "linear-gradient(150deg, var(--accent), var(--accent-hover))", color: "var(--accent-fg,#fff)", display: "inline-flex", alignItems: "center", justifyContent: "center", font: "600 24px var(--font-ui)", margin: "0 auto" }}>{initials(name)}</span>
            <h2 style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-lg,19px)", margin: "14px 0 2px" }}>{name}</h2>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>{ticket ? "Билет № " + ticket : "Читательский билет"}</span>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 12, padding: "4px 11px", borderRadius: 999, ...statusChip("available") }}>
              <span style={statusDot("available")} aria-hidden="true" />Активен
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, marginTop: 20, paddingTop: 18, borderTop: "1px solid var(--border-subtle)" }}>
              {[{ n: onHand.length, l: "на руках" }, { n: holdsCount, l: "в брони" }, { n: challengeDone, l: "прочитано", demo: true }].map((s, i) => (
                <div key={i} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: 21, fontVariantNumeric: "tabular-nums" }}>{s.n}</span>
                  <span style={{ fontSize: "var(--text-2xs,11px)", color: "var(--text-subtle)" }}>{s.l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Reading challenge (демо) */}
          <div style={{ ...cardSx, padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Icon name="star" size={16} style={{ color: "var(--accent)" }} />
              <span style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>Челлендж 2026</span>
              <span style={{ ...demoHint, marginLeft: "auto" }} title="Раздел в разработке">демо</span>
            </div>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted,var(--text-secondary))", margin: "10px 0 14px" }}>Прочитать {challengeGoal} книг за год</p>
            <div style={{ height: 9, borderRadius: 999, background: "var(--surface-hover,var(--surface-3))", overflow: "hidden" }} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Прогресс челленджа">
              <div style={{ height: "100%", width: pct + "%", borderRadius: 999, background: "linear-gradient(90deg, var(--accent), var(--accent-hover))" }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 9 }}>
              <span style={{ fontSize: "var(--text-xs)", fontWeight: 600, color: "var(--accent)" }}>{challengeDone} из {challengeGoal}</span>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", fontVariantNumeric: "tabular-nums" }}>{pct}%</span>
            </div>
          </div>
        </aside>

        {/* ===== Основная колонка ===== */}
        <main style={{ display: "flex", flexDirection: "column", gap: 24, minWidth: 0 }}>

          {/* Вкладки кабинета: Формуляр / Заказы (G12) / История (#134) / Запросы (#133) */}
          <div role="tablist" aria-label="Разделы кабинета" style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--border-subtle)", flexWrap: "wrap" }}>
            {([["formular", "Формуляр"], ["orders", "Заказы"], ["history", "История"], ["saved", "Запросы"]] as const).map(([key, label]) => {
              const on = cabTab === key;
              return (
                <button key={key} role="tab" aria-selected={on} onClick={() => setCabTab(key)}
                  style={{ background: "none", border: "none", borderBottom: on ? "2px solid var(--accent)" : "2px solid transparent", color: on ? "var(--accent)" : "var(--text-subtle)", fontWeight: on ? 600 : 500, padding: "9px 14px", cursor: "pointer", fontSize: "var(--text-sm)", fontFamily: "var(--font-ui,inherit)" }}>
                  {label}
                </button>
              );
            })}
          </div>

          {cabTab === "orders" ? (
            <section aria-labelledby="cab-orders">
              <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
                <h1 id="cab-orders" style={{ ...h2Sx, fontSize: "var(--text-2xl,22px)" }}>Мои заказы</h1>
              </div>
              <OrdersTab toast={toast} cardSx={cardSx} />
            </section>
          ) : cabTab === "history" ? (
            /* История просмотров (#134) — реальные данные GET /api/history. */
            <HistoryTab cardSx={cardSx} standalone
              h2Sx={{ ...h2Sx, fontSize: "var(--text-2xl,22px)" }}
              onOpenRecord={onOpenRecord} />
          ) : cabTab === "saved" ? (
            /* Сохранённые запросы (#133) — повтор/удаление, реальные данные GET /api/savedsearch. */
            <SavedSearchesPanel cardSx={cardSx} standalone
              h2Sx={{ ...h2Sx, fontSize: "var(--text-2xl,22px)" }}
              toast={toast} onRun={(s) => onRunSearch?.(s)} />
          ) : (
          <>
          {/* На руках сейчас — LIVE формуляр */}
          <section aria-labelledby="cab-onhand">
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
              <h1 id="cab-onhand" style={{ ...h2Sx, fontSize: "var(--text-2xl,22px)" }}>На руках сейчас</h1>
              <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>
                Формуляр · {onHand.length} {plural(onHand.length, "издание", "издания", "изданий")}
                {overdue ? " · " : ""}{overdue ? <span style={{ color: "var(--error)", fontWeight: 600 }}>{overdue} {plural(overdue, "просрочено", "просрочены", "просрочено")}</span> : null}
              </span>
            </div>
            {onHand.length ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {onHand.map((l, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: "14px 16px" }}>
                    <div aria-hidden="true" style={{ width: 40, height: 56, flex: "none", borderRadius: 6, background: "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.35))", boxShadow: "var(--shadow-md)", display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 4 }}>
                      <Icon name="book" size={13} style={{ color: "rgba(255,255,255,.85)" }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-base,15.5px)", lineHeight: 1.25, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{l.title}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 3, display: "flex", gap: 12, flexWrap: "wrap" }}>
                        <span style={{ fontFamily: "var(--font-mono)" }}>{l.meta || "—"}</span>
                        {l.issued && <span>выдано {fmtDate(l.issued)}</span>}
                        {l.renewals > 0 && <span>продлений: {l.renewals}</span>}
                      </div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 7, flex: "none" }}>
                      <span style={toneChip(l.tone)}><span style={toneDot(l.tone)} aria-hidden="true" />{l.dueLabel || "срок не указан"}</span>
                      <RenewButton />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={cardSx}><EmptyState icon="check-circle" title="На руках книг нет" description={returnedCount ? "Все издания возвращены." : "Формуляр пуст — закажите издание в каталоге."} /></div>
            )}
          </section>

          {/* Очередь брони — реальные данные GET /api/holds (#222). При 404/501 секция прячется. */}
          <HoldsTab cardSx={cardSx} h2Sx={h2Sx} demoHint={demoHint} toast={toast} refreshKey={holdsRefresh} />

          {/* Мои полки — реальные списки GET /api/shelves (#222). При 404/501 секция прячется. */}
          <ShelvesPanel cardSx={cardSx} h2Sx={h2Sx} toast={toast} onOpenRecord={onOpenRecord} />

          {/* Конфиденциальность (#199, 152-ФЗ): согласие на обработку ПДн + право на
              забвение. Тумблер прячется при отсутствии эндпойнта; карточка удаления
              деградирует тостом. Каталог библиотеки правом на забвение не затрагивается. */}
          <section aria-labelledby="cab-privacy">
            <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
              <h2 id="cab-privacy" style={h2Sx}>Конфиденциальность</h2>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <ConsentToggle cardSx={cardSx} toast={toast} />
              <EraseDataCard cardSx={cardSx} toast={toast} onErased={onErased} />
            </div>
          </section>
          </>
          )}

          <div style={{ marginTop: 4 }}><Button variant="ghost" iconLeft="log-out" onClick={onLogout}>Выйти из кабинета</Button></div>
        </main>
      </div>
    </div>
  );
}

// «Продлить» — реальное продление это запись в backend, которой ещё нет.
// Кнопка задизейблена с подсказкой «скоро»; write-эндпойнты не вызываются.
function RenewButton() {
  return (
    <span title="Онлайн-продление появится скоро" style={{ display: "inline-block" }}>
      <button type="button" disabled aria-disabled="true" aria-label="Продлить (скоро)"
        style={{ border: "1px solid var(--border-default,var(--border-strong))", background: "transparent", color: "var(--text-muted,var(--text-secondary))", borderRadius: 8, padding: "6px 13px", fontFamily: "var(--font-ui)", fontWeight: 500, fontSize: "var(--text-xs,12px)", cursor: "not-allowed", opacity: .7, display: "inline-flex", alignItems: "center", gap: 5 }}>
        <Icon name="refresh-cw" size={13} /> Продлить
      </button>
    </span>
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

function RecordCard({ rec, db, tab, setTab, shareOpen, setShareOpen, permalink, onCopyPermalink, onBack, onOrder, onHold, onSubject, loggedIn, readerName, toast, onOpenRecord, onViewDoc, inBasket, onToggleBasket }: {
  rec: RecordData; db: string; tab: number; setTab: (n: number) => void;
  shareOpen: boolean; setShareOpen: (b: boolean) => void;
  permalink: string; onCopyPermalink: () => void;
  onBack: () => void; onOrder: () => void; onHold: () => void; onSubject: (t: string) => void;
  loggedIn: boolean; readerName?: string; toast: (t: { variant: ToastVariant; title: string; message?: string }) => void;
  onOpenRecord: (db: string, mfn: number) => void;
  onViewDoc: (pages: DocPage[], idx: number, title?: string) => void;
  inBasket: boolean; onToggleBasket: () => void;
}) {
  const v = recView(rec);
  // Страницы для постраничного просмотрщика (#222): из электронных версий записи.
  // Картинки (по расширению) — листаются и зумируются во вьюере; прочие файлы —
  // открываются по ссылке. Только записи со страницами получают кнопку «Открыть просмотр».
  const docPages: DocPage[] = v.files
    .filter((f) => f.url)
    .map((f) => ({ name: f.name || f.url, url: f.url, kind: /\.(png|jpe?g|gif|webp|bmp|tiff?|svg)(\?|#|$)/i.test(f.url) ? ("image" as const) : ("file" as const) }));
  const hasImagePages = docPages.some((p) => p.kind === "image");
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

          {/* Действия: заказ, бронь, список, корзина, поделиться, экспорт */}
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 14, position: "relative" }}>
            <Button iconLeft="bookmark" onClick={onOrder}>Заказать</Button>
            {/* Бронирование (#222) — ставит экземпляр в очередь удержания. */}
            <Button variant="secondary" iconLeft="clock" onClick={onHold}>Забронировать</Button>
            {/* «В список ▾» (#222) — доступно вошедшему читателю. */}
            {loggedIn && <ShelfMenu db={rec.db} mfn={rec.mfn} title={rec.brief || ""} toast={toast} />}
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
                    <span style={statusChip(h.st)}><span style={statusDot(h.st)} aria-hidden="true" />{(STATUS[h.st] || STATUS.unknown).label}</span>
                  </div>)}
                </div> :
                <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Сведения об экземплярах в записи отсутствуют.</div>
            )}
            {tab === 2 && (
              v.files.length ?
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {/* Постраничный просмотрщик (#222): доступен, если есть страницы-файлы. */}
                  {docPages.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <Button size="sm" iconLeft={hasImagePages ? "images" : "book-open"}
                        onClick={() => onViewDoc(docPages, 0, rec.brief || "")}>
                        Открыть просмотр{docPages.length > 1 ? " · " + docPages.length + " стр." : ""}
                      </Button>
                    </div>
                  )}
                  {v.files.map((f, i) => {
                    const pageIdx = docPages.findIndex((p) => p.url === f.url);
                    return (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "var(--text-sm)" }}>
                        <Icon name="file-text" size={16} style={{ color: "var(--text-subtle)", flexShrink: 0 }} />
                        {f.url && pageIdx >= 0
                          ? <button type="button" onClick={() => onViewDoc(docPages, pageIdx, rec.brief || "")}
                              style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--accent)", font: "inherit", display: "inline-flex", alignItems: "center", gap: 5 }}>
                              {f.name || f.url} <Icon name="eye" size={13} />
                            </button>
                          : f.url
                            ? <a href={f.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: 5 }}>{f.name || f.url} <Icon name="external-link" size={13} /></a>
                            : <span>{f.name}</span>}
                      </div>
                    );
                  })}
                </div> :
                <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Электронные версии к записи не прикреплены.</div>
            )}
            {tab === 3 && (
              <div dangerouslySetInnerHTML={{ __html: `<table style="border-collapse:collapse;width:100%">${v.rawRows}</table>` }} />
            )}
          </div>

          {/* Отзывы и оценки (#134) — скрыто при отсутствии эндпойнта. */}
          <ReviewPanel db={rec.db} mfn={rec.mfn} loggedIn={loggedIn} readerName={readerName} toast={toast} />

          {/* «Похожие издания» (#133) — скрыто, если рекомендаций нет/404. */}
          <SimilarRecommendations db={rec.db} mfn={rec.mfn} onOpen={(mfn, database) => onOpenRecord(database, mfn)} />
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
  toast: (t: { variant: ToastVariant; title: string; message?: string }) => void;
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
