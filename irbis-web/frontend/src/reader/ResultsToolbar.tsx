// Фурнитура выдачи (G4 + G6): переключатель «Галерея / Список» и контрол
// сортировки (релевантность / год / заглавие). Контролируемый компонент —
// состояние живёт в App.tsx. Сортировка применяется на клиенте к текущей
// странице результатов (backend сортировки нет → сортируем имеющиеся items).
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";

export type ViewMode = "list" | "gallery";
export type SortKey = "relevance" | "year-desc" | "year-asc" | "title";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "relevance", label: "По релевантности" },
  { key: "year-desc", label: "Год: новые сначала" },
  { key: "year-asc", label: "Год: старые сначала" },
  { key: "title", label: "По заглавию" },
];

const CSS = `
.irb-rtoolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 12px;font-family:var(--font-ui);}
.irb-rtoolbar__count{font-size:var(--text-sm);color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-rtoolbar__spacer{margin-left:auto;}
.irb-rtoolbar__group{display:flex;align-items:center;gap:8px;}
.irb-rtoolbar__lbl{font-size:var(--text-xs);color:var(--text-subtle);}
.irb-rtoolbar__sort{padding:7px 10px;border-radius:var(--radius-md,8px);border:1px solid var(--border-strong,#cdd3da);
  background:var(--surface-card,#fff);color:var(--text-body);font-family:var(--font-ui,inherit);font-size:var(--text-sm);cursor:pointer;}
.irb-seg{display:inline-flex;gap:2px;padding:2px;background:var(--surface-sunken,#eee);border-radius:var(--radius-md,10px);}
.irb-seg__b{display:inline-flex;align-items:center;gap:6px;border:none;background:transparent;color:var(--text-body);
  border-radius:var(--radius-sm,7px);padding:6px 12px;cursor:pointer;font-family:var(--font-ui,inherit);font-size:var(--text-sm);
  transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-seg__b--on{background:var(--accent);color:var(--accent-fg,#fff);font-weight:var(--weight-semibold,600);}
.irb-seg__b:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-rtoolbar-css")) {
  const s = document.createElement("style"); s.id = "irb-rtoolbar-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Извлекает 4-значный год из строки year ("М. : Изд, 2019" → 2019); 0 если нет.
function yearOf(y?: string): number {
  const m = (y || "").match(/\d{4}/);
  return m ? parseInt(m[0], 10) : 0;
}

// Стабильная сортировка items по выбранному ключу. relevance = исходный порядок.
export function sortItems<T extends { title?: string; year?: string }>(items: T[], sort: SortKey): T[] {
  if (sort === "relevance") return items;
  const arr = items.map((it, i) => ({ it, i }));
  arr.sort((a, b) => {
    if (sort === "title") {
      const c = (a.it.title || "").localeCompare(b.it.title || "", "ru");
      return c !== 0 ? c : a.i - b.i;
    }
    const ya = yearOf(a.it.year), yb = yearOf(b.it.year);
    const c = sort === "year-asc" ? ya - yb : yb - ya;
    return c !== 0 ? c : a.i - b.i;
  });
  return arr.map((x) => x.it);
}

export function ResultsToolbar({
  total, page, pageCount, view, onView, sort, onSort, showToggle = true,
}: {
  total: number; page: number; pageCount: number;
  view: ViewMode; onView: (v: ViewMode) => void;
  sort: SortKey; onSort: (s: SortKey) => void;
  // Показывать ли тумблер «Список/Галерея». Для баз с календарным/архивным
  // профилем (#222) тумблер скрыт — вид задаётся профилем базы.
  showToggle?: boolean;
}) {
  return (
    <div className="irb-rtoolbar">
      <span className="irb-rtoolbar__count">Найдено: <b>{total.toLocaleString("ru-RU")}</b> · страница {page} из {pageCount}</span>

      <div className="irb-rtoolbar__spacer" />

      <div className="irb-rtoolbar__group">
        <label className="irb-rtoolbar__lbl" htmlFor="irb-sort">Сортировка</label>
        <select id="irb-sort" className="irb-rtoolbar__sort" value={sort} onChange={(e) => onSort(e.target.value as SortKey)} aria-label="Сортировка результатов">
          {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>

      {showToggle && (
        <div className="irb-seg" role="group" aria-label="Вид выдачи">
          <button type="button" className={"irb-seg__b" + (view === "list" ? " irb-seg__b--on" : "")}
            aria-pressed={view === "list"} onClick={() => onView("list")} title="Список">
            <Icon name="list" size={16} /> Список
          </button>
          <button type="button" className={"irb-seg__b" + (view === "gallery" ? " irb-seg__b--on" : "")}
            aria-pressed={view === "gallery"} onClick={() => onView("gallery")} title="Галерея">
            <Icon name="grid" size={16} /> Галерея
          </button>
        </div>
      )}
    </div>
  );
}
