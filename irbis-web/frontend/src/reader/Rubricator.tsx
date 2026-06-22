// Рубрикатор / навигация по фонду (G1+) — блок «Просмотр по разделам». Плитки
// разделов с количеством записей берутся из живого словаря GET /api/rubricator
// (термины с частотой). Клик по разделу → поиск каталога по этой рубрике
// (onSearch("K", термин)). Грациозная деградация: при 404/пустом ответе или
// нехватке разделов блок не рендерится — главная не зависит от наличия словаря.
import React from "react";
import { api } from "../api";
import type { Term } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const CSS = `
.irb-rubr{margin:0;}
.irb-rubr__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;flex-wrap:wrap;}
.irb-rubr__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-rubr__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-rubr__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;}
.irb-rubr__tile{display:flex;align-items:center;gap:11px;text-align:left;
  background:var(--surface-card,#fff);border:1px solid var(--border-subtle);border-radius:var(--radius-lg,12px);
  padding:12px 14px;cursor:pointer;font-family:inherit;box-shadow:var(--shadow-sm);width:100%;
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease),border-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-rubr__tile:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);border-color:var(--border-strong,#cdd3da);}
.irb-rubr__tile:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-rubr__ic{width:34px;height:34px;flex:none;border-radius:9px;background:var(--accent-weak,#eef2f7);color:var(--accent);
  display:inline-flex;align-items:center;justify-content:center;}
.irb-rubr__body{min-width:0;flex:1;display:flex;flex-direction:column;gap:1px;}
.irb-rubr__name{font-size:var(--text-sm);font-weight:var(--weight-semibold,600);color:var(--text-strong);line-height:1.2;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:break-word;}
.irb-rubr__count{font-size:var(--text-xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-rubr-css")) {
  const s = document.createElement("style"); s.id = "irb-rubr-css"; s.textContent = CSS; document.head.appendChild(s);
}

interface Section { term: string; count: number; }

function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

export function Rubricator({ db, onSearch }: { db: string; onSearch: (prefix: string, query: string) => void }) {
  const [sections, setSections] = React.useState<Section[] | null>(null);

  React.useEffect(() => {
    let alive = true;
    setSections(null);
    (async () => {
      // Тематический рубрикатор — по ключевым словам (K). Берём с запасом и
      // отсеиваем служебные/короткие термины.
      const r = await api.rubricator(db, "K", 18);
      if (!alive) return;
      const terms: Term[] = r.json?.ok && r.json.data ? (r.json.data.terms || []) : [];
      const live: Section[] = terms
        .map((t) => ({ term: (t.term || "").replace(/^[A-ZА-Я]=/, "").trim(), count: t.count || 0 }))
        .filter((s) => s.term.length >= 3 && s.term.length <= 40)
        .slice(0, 12);
      setSections(live);
    })();
    return () => { alive = false; };
  }, [db]);

  // Лёгкий скелет, чтобы не было прыжка раскладки при загрузке словаря.
  if (sections === null) {
    return (
      <section className="irb-rubr" aria-label="Просмотр по разделам">
        <div className="irb-rubr__head"><h2 className="irb-rubr__title">Просмотр по разделам</h2></div>
        <div className="irb-rubr__grid" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="irb-rubr__tile" style={{ pointerEvents: "none", boxShadow: "none", background: "var(--surface-sunken)", borderColor: "transparent", minHeight: 58 }} />
          ))}
        </div>
      </section>
    );
  }
  if (sections.length < 3) return null; // словаря нет / мало разделов → блок скрыт

  return (
    <section className="irb-rubr" aria-label="Просмотр по разделам">
      <div className="irb-rubr__head">
        <h2 className="irb-rubr__title">Просмотр по разделам</h2>
        <span className="irb-rubr__sub">навигация по фонду — выберите раздел</span>
      </div>
      <div className="irb-rubr__grid" role="list">
        {sections.map((s) => (
          <button
            key={s.term} type="button" role="listitem" className="irb-rubr__tile"
            onClick={() => onSearch("K", s.term)}
            aria-label={"Раздел «" + s.term + "»" + (s.count ? ", " + s.count + " " + plural(s.count, "запись", "записи", "записей") : "")}
          >
            <span className="irb-rubr__ic" aria-hidden="true"><Icon name="folder-tree" size={18} /></span>
            <span className="irb-rubr__body">
              <span className="irb-rubr__name">{s.term}</span>
              {s.count > 0 && <span className="irb-rubr__count">{s.count.toLocaleString("ru-RU")} {plural(s.count, "запись", "записи", "записей")}</span>}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
