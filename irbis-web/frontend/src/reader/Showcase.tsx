// Витрина новых поступлений (G2) — горизонтальный ряд обложек-карточек на
// главной. Данные из GET /api/showcase?db&kind=new&limit. Если эндпойнт ещё не
// готов (404) или пуст — блок не рендерится (graceful degrade). Стиль строго на
// Biblio-токенах; обложки берём из /api/cover, плейсхолдер — тонированная подложка.
import React from "react";
import { api } from "../api";
import type { ShowcaseItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

const CSS = `
.irb-showcase{margin:0 0 6px;}
.irb-showcase__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;}
.irb-showcase__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-showcase__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-showcase__rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 12px;scroll-snap-type:x mandatory;
  scrollbar-width:thin;}
.irb-showcase__card{flex:none;width:140px;scroll-snap-align:start;display:flex;flex-direction:column;gap:8px;
  background:none;border:none;padding:0;cursor:pointer;text-align:left;font-family:inherit;}
.irb-showcase__cover{width:140px;height:196px;border-radius:var(--radius-lg,12px);overflow:hidden;
  box-shadow:var(--shadow-md);border:1px solid var(--border-subtle);position:relative;
  display:flex;align-items:flex-end;justify-content:center;
  transition:transform var(--dur,.18s) var(--ease-standard,ease), box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-showcase__card:hover .irb-showcase__cover,
.irb-showcase__card:focus-visible .irb-showcase__cover{transform:translateY(-3px);box-shadow:var(--shadow-lg);}
.irb-showcase__card:focus-visible{outline:none;}
.irb-showcase__card:focus-visible .irb-showcase__cover{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-showcase__cover img{width:100%;height:100%;object-fit:cover;display:block;}
.irb-showcase__ph{padding:10px;color:rgba(255,255,255,.9);font-family:var(--font-display,var(--font-serif));
  font-size:var(--text-sm);font-weight:var(--weight-semibold,600);line-height:1.2;width:100%;box-sizing:border-box;
  text-shadow:0 1px 4px rgba(0,0,0,.35);
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.irb-showcase__badge{position:absolute;top:8px;left:8px;display:inline-flex;align-items:center;gap:4px;
  background:var(--accent);color:var(--accent-fg,#fff);font-size:var(--text-2xs,11px);font-weight:var(--weight-bold,700);
  padding:2px 8px;border-radius:var(--radius-pill,999px);}
.irb-showcase__meta{display:block;width:140px;min-width:0;box-sizing:border-box;}
.irb-showcase__name{display:-webkit-box;width:100%;font-size:var(--text-sm);font-weight:var(--weight-semibold,600);
  color:var(--text-strong);line-height:1.25;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;overflow-wrap:break-word;word-break:break-word;}
.irb-showcase__by{display:block;width:100%;font-size:var(--text-xs);color:var(--text-subtle);margin-top:2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-showcase-css")) {
  const s = document.createElement("style"); s.id = "irb-showcase-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function Showcase({ db, onOpen }: { db: string; onOpen: (mfn: number, db: string) => void }) {
  const [items, setItems] = React.useState<ShowcaseItem[] | null>(null);

  React.useEffect(() => {
    let alive = true;
    setItems(null);
    (async () => {
      const r = await api.showcase(db, "new", 12);
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setItems(r.json.data.items);
      else setItems([]); // 404 / error → пустой массив, блок скрывается
    })();
    return () => { alive = false; };
  }, [db]);

  // Пока грузится — лёгкий скелет, чтобы не было прыжка раскладки.
  if (items === null) {
    return (
      <section className="irb-showcase" aria-label="Новые поступления">
        <div className="irb-showcase__head"><h2 className="irb-showcase__title">Новые поступления</h2></div>
        <div className="irb-showcase__rail" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="irb-showcase__card" style={{ pointerEvents: "none" }}>
              <div className="irb-showcase__cover" style={{ background: "var(--surface-sunken)", boxShadow: "none" }} />
            </div>
          ))}
        </div>
      </section>
    );
  }
  if (!items.length) return null; // эндпойнта нет / пусто — не показываем блок

  return (
    <section className="irb-showcase" aria-label="Новые поступления">
      <div className="irb-showcase__head">
        <h2 className="irb-showcase__title">Новые поступления</h2>
        <span className="irb-showcase__sub">недавно добавлены в каталог</span>
      </div>
      <div className="irb-showcase__rail" role="list">
        {items.map((it, i) => (
          <button
            key={it.mfn} type="button" role="listitem" className="irb-showcase__card"
            onClick={() => onOpen(it.mfn, db)}
            aria-label={"Открыть: " + (it.title || "издание") + (it.author ? ", " + it.author : "")}
          >
            <span
              className="irb-showcase__cover"
              style={it.cover ? undefined : { background: "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.42))" }}
            >
              <span className="irb-showcase__badge"><Icon name="star" size={11} /> Новинка</span>
              {it.cover
                ? <img src={api.coverUrl(db, it.mfn)} alt="" onError={(e) => { const img = e.currentTarget; img.style.display = "none"; const p = img.parentElement; if (p) { p.style.background = "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.42))"; } }} />
                : <span className="irb-showcase__ph">{it.title || "Без заглавия"}</span>}
            </span>
            <span className="irb-showcase__meta">
              <span className="irb-showcase__name">{it.title || "Без заглавия"}</span>
              {(it.author || it.year) && <span className="irb-showcase__by">{[it.author, it.year].filter(Boolean).join(" · ")}</span>}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
