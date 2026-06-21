// Календарный вид выдачи (#222) — для периодики/статей: записи группируются по
// году (извлекается из поля year, напр. «М. : Изд, 2019» → 2019; иначе «Без даты»).
// Внутри года — компактные карточки выпусков с заглавием/автором и статусом.
// Те же данные ResultItem, что у списка/галереи; переключается мульти-лейаутом.
import React from "react";
import type { ResultItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import { StatusBadge } from "../../components/catalog/StatusBadge.jsx";

const CSS = `
.irb-cal{display:flex;flex-direction:column;gap:22px;}
.irb-cal__group{display:flex;flex-direction:column;gap:10px;}
.irb-cal__year{display:flex;align-items:center;gap:9px;font-family:var(--font-display,var(--font-serif));
  font-weight:var(--weight-semibold,600);font-size:var(--text-lg,19px);color:var(--text-strong);
  letter-spacing:-.01em;padding-bottom:6px;border-bottom:1px solid var(--border-subtle);}
.irb-cal__year-badge{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:20px;
  padding:0 7px;border-radius:var(--radius-pill,999px);background:var(--accent-weak,#eef2f7);color:var(--accent);
  font-size:var(--text-2xs,11px);font-weight:var(--weight-semibold,600);font-variant-numeric:tabular-nums;}
.irb-cal__items{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));}
.irb-cal__card{display:flex;flex-direction:column;gap:7px;background:var(--surface-card);
  border:1px solid var(--border-subtle);border-radius:var(--radius-lg,13px);padding:13px 14px;text-align:left;
  cursor:pointer;font-family:inherit;transition:border-color var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-cal__card:hover{border-color:var(--border-strong,#cdd3da);box-shadow:var(--shadow-sm);}
.irb-cal__card:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-cal__title{font-family:var(--font-record-title,var(--font-display,inherit));font-size:var(--text-base,15.5px);
  font-weight:var(--weight-semibold,600);color:var(--text-strong);line-height:1.25;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.irb-cal__by{font-size:var(--text-xs);color:var(--text-subtle);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-cal__foot{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:2px;}
.irb-cal__check{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;flex:none;
  border-radius:var(--radius-sm,7px);border:1px solid var(--border-strong,#cdd3da);background:var(--surface-card,#fff);
  color:var(--text-body);cursor:pointer;}
.irb-cal__check--on{background:var(--accent);border-color:var(--accent);color:var(--accent-fg,#fff);}
.irb-cal__check:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-cal-css")) {
  const s = document.createElement("style"); s.id = "irb-cal-css"; s.textContent = CSS; document.head.appendChild(s);
}

// 4-значный год из строки year; null если не найден.
function yearOf(y?: string): string | null {
  const m = (y || "").match(/\b(1[5-9]\d{2}|20\d{2})\b/);
  return m ? m[1] : null;
}

export function CalendarGrid({
  items, inBasket, onToggleBasket, onOpen,
}: {
  items: ResultItem[];
  inBasket: (mfn: number) => boolean;
  onToggleBasket: (it: ResultItem) => void;
  onOpen: (mfn: number) => void;
}) {
  // Группируем по году, сохраняя порядок появления групп (новые/известные сначала).
  const groups = React.useMemo(() => {
    const map = new Map<string, ResultItem[]>();
    for (const it of items) {
      const key = yearOf(it.year) || "Без даты";
      const bucket = map.get(key);
      if (bucket) bucket.push(it); else map.set(key, [it]);
    }
    const entries = Array.from(map.entries());
    // Годы по убыванию; «Без даты» — в конец.
    entries.sort((a, b) => {
      if (a[0] === "Без даты") return 1;
      if (b[0] === "Без даты") return -1;
      return parseInt(b[0], 10) - parseInt(a[0], 10);
    });
    return entries;
  }, [items]);

  return (
    <div className="irb-cal" role="list">
      {groups.map(([year, list]) => (
        <section key={year} className="irb-cal__group" aria-label={"Год: " + year}>
          <div className="irb-cal__year">
            <Icon name="calendar" size={17} style={{ color: "var(--accent)" }} />
            {year}
            <span className="irb-cal__year-badge">{list.length}</span>
          </div>
          <div className="irb-cal__items">
            {list.map((it) => {
              const on = inBasket(it.mfn);
              return (
                <article
                  key={it.mfn} role="listitem" className="irb-cal__card" tabIndex={0}
                  onClick={() => onOpen(it.mfn)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(it.mfn); } }}
                  aria-label={"Открыть: " + (it.title || "выпуск")}
                >
                  <div className="irb-cal__title">{it.title || "Без заглавия"}</div>
                  {(it.author || it.year) && <div className="irb-cal__by">{[it.author, it.year].filter(Boolean).join(" · ")}</div>}
                  <div className="irb-cal__foot">
                    <StatusBadge status={it.availability || "unknown"} size="sm" />
                    <button
                      type="button" className={"irb-cal__check" + (on ? " irb-cal__check--on" : "")}
                      aria-pressed={on} aria-label={on ? "Убрать из корзины" : "Добавить в корзину"}
                      onClick={(e) => { e.stopPropagation(); onToggleBasket(it); }}
                    >
                      <Icon name={on ? "check" : "plus"} size={15} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
