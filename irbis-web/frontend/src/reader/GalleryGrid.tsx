// Галерея-сетка результатов (G4) — обложки-карточки вместо строк. Для каждой
// записи: обложка (api.coverUrl при hasCover, иначе тонированный плейсхолдер с
// заглавием), заглавие/автор/год, статус-бейдж, чек «в корзину» в углу. Тот же
// набор данных, что у списка (ResultItem) — переключается тумблером в тулбаре.
import React from "react";
import type { ResultItem } from "../api";
import { api } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import { StatusBadge } from "../../components/catalog/StatusBadge.jsx";

const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

const CSS = `
.irb-gal{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));}
.irb-gcard{position:relative;display:flex;flex-direction:column;gap:9px;background:none;border:none;padding:0;text-align:left;font-family:inherit;}
.irb-gcard__cover{position:relative;width:100%;aspect-ratio:5/7;border-radius:var(--radius-lg,12px);overflow:hidden;
  box-shadow:var(--shadow-md);border:1px solid var(--border-subtle);cursor:pointer;
  display:flex;align-items:flex-end;justify-content:center;
  transition:transform var(--dur,.18s) var(--ease-standard,ease), box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-gcard__cover:hover,.irb-gcard__cover:focus-visible{transform:translateY(-3px);box-shadow:var(--shadow-lg);outline:none;}
.irb-gcard__cover:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-gcard__cover img{width:100%;height:100%;object-fit:cover;display:block;}
.irb-gcard__ph{padding:12px;color:rgba(255,255,255,.92);font-family:var(--font-display,var(--font-serif));
  font-size:var(--text-sm);font-weight:var(--weight-semibold,600);line-height:1.22;width:100%;box-sizing:border-box;
  text-shadow:0 1px 4px rgba(0,0,0,.35);
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;}
.irb-gcard__check{position:absolute;top:8px;left:8px;width:26px;height:26px;border-radius:var(--radius-sm,7px);
  border:1px solid rgba(255,255,255,.7);background:rgba(20,16,14,.4);color:#fff;cursor:pointer;
  display:flex;align-items:center;justify-content:center;backdrop-filter:blur(2px);}
.irb-gcard__check--on{background:var(--accent);border-color:var(--accent);}
.irb-gcard__check:focus-visible{outline:2px solid #fff;outline-offset:1px;}
.irb-gcard__status{position:absolute;bottom:8px;right:8px;}
.irb-gcard__meta{display:flex;flex-direction:column;min-width:0;}
.irb-gcard__title{font-family:var(--font-record-title,var(--font-display,inherit));font-size:var(--text-base,15.5px);
  font-weight:var(--weight-semibold,600);color:var(--text-strong);line-height:1.25;cursor:pointer;
  background:none;border:none;padding:0;text-align:left;max-width:100%;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.irb-gcard__title:hover{color:var(--accent-hover);text-decoration:underline;text-underline-offset:3px;}
.irb-gcard__by{display:block;max-width:100%;font-size:var(--text-xs);color:var(--text-subtle);margin-top:3px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-gcard__acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px;}
.irb-gcard__act{display:inline-flex;align-items:center;gap:5px;background:transparent;color:var(--text-body);
  border:1px solid var(--border-strong,#cdd3da);border-radius:var(--radius-sm,7px);padding:4px 8px;cursor:pointer;
  font-family:var(--font-ui,inherit);font-size:var(--text-2xs,11px);}
.irb-gcard__act:hover{border-color:var(--accent);color:var(--accent);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-gal-css")) {
  const s = document.createElement("style"); s.id = "irb-gal-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function GalleryGrid({
  items, db, inBasket, onToggleBasket, onOpen, onHold, renderShelf,
}: {
  items: ResultItem[];
  db: string;
  inBasket: (mfn: number) => boolean;
  onToggleBasket: (it: ResultItem) => void;
  onOpen: (mfn: number) => void;
  // Действия #222 (необязательны): бронь и меню «В список» на карточке-обложке.
  onHold?: (it: ResultItem) => void;
  renderShelf?: (it: ResultItem) => React.ReactNode;
}) {
  return (
    <div className="irb-gal" role="list">
      {items.map((it, i) => {
        const on = inBasket(it.mfn);
        const tint = "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.42))";
        return (
          <article key={it.mfn} role="listitem" className="irb-gcard">
            <span
              className="irb-gcard__cover" role="button" tabIndex={0}
              onClick={() => onOpen(it.mfn)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(it.mfn); } }}
              aria-label={"Открыть: " + (it.title || "издание")}
              style={it.hasCover ? undefined : { background: tint }}
            >
              {it.hasCover
                ? <img src={api.coverUrl(db, it.mfn)} alt="" onError={(e) => { const img = e.currentTarget; img.style.display = "none"; const p = img.parentElement; if (p) p.style.background = tint; }} />
                : <span className="irb-gcard__ph">{it.title || "Без заглавия"}</span>}
              <button
                type="button" className={"irb-gcard__check" + (on ? " irb-gcard__check--on" : "")}
                aria-pressed={on} aria-label={on ? "Убрать из корзины" : "Добавить в корзину"}
                onClick={(e) => { e.stopPropagation(); onToggleBasket(it); }}
              >
                <Icon name={on ? "check" : "plus"} size={15} />
              </button>
              <span className="irb-gcard__status" onClick={(e) => e.stopPropagation()}>
                <StatusBadge status={it.availability || "unknown"} size="sm" />
              </span>
            </span>
            <span className="irb-gcard__meta">
              <button type="button" className="irb-gcard__title" onClick={() => onOpen(it.mfn)}>{it.title || "Без заглавия"}</button>
              {(it.author || it.year) && <span className="irb-gcard__by">{[it.author, it.year].filter(Boolean).join(" · ")}</span>}
              {(onHold || renderShelf) && (
                <span className="irb-gcard__acts">
                  {onHold && (
                    <button type="button" className="irb-gcard__act" onClick={(e) => { e.stopPropagation(); onHold(it); }} title="Забронировать">
                      <Icon name="clock" size={13} /> Бронь
                    </button>
                  )}
                  {renderShelf && renderShelf(it)}
                </span>
              )}
            </span>
          </article>
        );
      })}
    </div>
  );
}
