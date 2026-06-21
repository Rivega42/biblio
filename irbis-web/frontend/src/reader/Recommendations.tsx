// Рекомендации (#133). Два экспорта одной горизонтальной «полки»-карточек:
//   SimilarRecommendations — «Похожие издания» на карточке записи (GET
//     /api/recommendations?db&mfn);
//   ForYouRecommendations — «Для вас» на главной (GET /api/recommendations/foryou).
// Каждая карточка показывает заглавие/автора + причину (reason); клик открывает
// запись. Грациозная деградация: при 404/пустом ответе блок не рендерится.
import React from "react";
import { api } from "../api";
import type { Recommendation } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

const CSS = `
.irb-recs{margin:0;}
.irb-recs--rec{margin-top:26px;border-top:1px solid var(--border-subtle);padding-top:18px;}
.irb-recs__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;}
.irb-recs__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-recs__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-recs__rail{display:flex;gap:12px;overflow-x:auto;padding:2px 2px 10px;scroll-snap-type:x mandatory;scrollbar-width:thin;}
.irb-recs__card{flex:none;width:184px;scroll-snap-align:start;display:flex;gap:10px;text-align:left;
  background:var(--surface-card,#fff);border:1px solid var(--border-subtle);border-radius:var(--radius-lg,12px);
  padding:12px;cursor:pointer;font-family:inherit;box-shadow:var(--shadow-sm);
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease),border-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-recs__card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);border-color:var(--border-strong,#cdd3da);}
.irb-recs__card:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-recs__cover{width:40px;height:56px;flex:none;border-radius:6px;box-shadow:var(--shadow-md);
  display:flex;align-items:flex-end;justify-content:center;padding:4px;box-sizing:border-box;}
.irb-recs__meta{min-width:0;flex:1;display:flex;flex-direction:column;gap:3px;}
.irb-recs__name{font-size:var(--text-sm);font-weight:var(--weight-semibold,600);color:var(--text-strong);line-height:1.25;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:break-word;}
.irb-recs__by{font-size:var(--text-xs);color:var(--text-subtle);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-recs__reason{margin-top:2px;font-size:var(--text-2xs,11px);color:var(--accent);background:var(--accent-weak,#eef2f7);
  border-radius:999px;padding:2px 8px;align-self:flex-start;display:inline-flex;align-items:center;gap:4px;max-width:100%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-recs-css")) {
  const s = document.createElement("style"); s.id = "irb-recs-css"; s.textContent = CSS; document.head.appendChild(s);
}

function RecsRail({ title, sub, items, onOpen, variant }: {
  title: string; sub?: string; items: Recommendation[];
  onOpen: (mfn: number, db: string) => void; variant?: "rec";
}) {
  return (
    <section className={"irb-recs" + (variant === "rec" ? " irb-recs--rec" : "")} aria-label={title}>
      <div className="irb-recs__head">
        <h2 className="irb-recs__title">{title}</h2>
        {sub && <span className="irb-recs__sub">{sub}</span>}
      </div>
      <div className="irb-recs__rail" role="list">
        {items.map((it, i) => (
          <button key={it.db + ":" + it.mfn} type="button" role="listitem" className="irb-recs__card"
            onClick={() => onOpen(it.mfn, it.db)}
            aria-label={"Открыть: " + (it.title || "издание") + (it.author ? ", " + it.author : "")}>
            <span className="irb-recs__cover" aria-hidden="true"
              style={{ background: "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.4))" }}>
              <Icon name="book" size={13} style={{ color: "rgba(255,255,255,.85)" }} />
            </span>
            <span className="irb-recs__meta">
              <span className="irb-recs__name">{it.title || "Без заглавия"}</span>
              {it.author && <span className="irb-recs__by">{it.author}</span>}
              {it.reason && <span className="irb-recs__reason" title={it.reason}><Icon name="sliders" size={10} /> {it.reason}</span>}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

// «Похожие издания» — на карточке записи.
export function SimilarRecommendations({ db, mfn, onOpen }: {
  db: string; mfn: number; onOpen: (mfn: number, db: string) => void;
}) {
  const [items, setItems] = React.useState<Recommendation[] | null>(null);
  React.useEffect(() => {
    let alive = true; setItems(null);
    (async () => {
      const r = await api.recommendations(db, mfn);
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setItems(r.json.data.items);
      else setItems([]);
    })();
    return () => { alive = false; };
  }, [db, mfn]);

  if (!items || !items.length) return null; // 404 / пусто → блок скрыт
  return <RecsRail title="Похожие издания" sub="вам также может быть интересно" items={items} onOpen={onOpen} variant="rec" />;
}

// «Для вас» — на главной (персональная подборка). Скрыт, если пусто.
export function ForYouRecommendations({ onOpen, refreshKey }: {
  onOpen: (mfn: number, db: string) => void; refreshKey?: number;
}) {
  const [items, setItems] = React.useState<Recommendation[] | null>(null);
  React.useEffect(() => {
    let alive = true; setItems(null);
    (async () => {
      const r = await api.recommendationsForYou();
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setItems(r.json.data.items);
      else setItems([]);
    })();
    return () => { alive = false; };
  }, [refreshKey]);

  if (!items || !items.length) return null; // нет персональных рекомендаций → блок скрыт
  return <RecsRail title="Для вас" sub="подобрано по вашим интересам" items={items} onOpen={onOpen} />;
}
