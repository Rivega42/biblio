// Архивный вид выдачи (#222) — плотные строки для архивных фондов/дел. Минимум
// декора: монохромный значок «дело», заглавие в одну-две строки, метаданные
// (автор · год), компактный статус и чек «в корзину». Плотнее списка ResultCard,
// рассчитан на длинные перечни единиц хранения. Данные — те же ResultItem.
import React from "react";
import type { ResultItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import { StatusBadge } from "../../components/catalog/StatusBadge.jsx";

const CSS = `
.irb-arch{display:flex;flex-direction:column;border:1px solid var(--border-subtle);border-radius:var(--radius-lg,13px);
  overflow:hidden;background:var(--surface-card);}
.irb-arch__row{display:flex;align-items:center;gap:12px;padding:9px 14px;border-top:1px solid var(--border-subtle);
  cursor:pointer;transition:background-color var(--dur,.15s) var(--ease-standard,ease);}
.irb-arch__row:first-child{border-top:none;}
.irb-arch__row:hover{background:var(--surface-hover,var(--surface-sunken,#f5f4ef));}
.irb-arch__row:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:-2px;}
.irb-arch__no{flex:none;width:34px;text-align:right;font-family:var(--font-mono);font-size:var(--text-xs);
  color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-arch__icon{flex:none;display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;
  border-radius:var(--radius-sm,7px);background:var(--surface-sunken,#f0eee6);color:var(--text-subtle);}
.irb-arch__body{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px;}
.irb-arch__title{font-size:var(--text-sm,14px);font-weight:var(--weight-semibold,600);color:var(--text-strong);
  line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-arch__meta{font-size:var(--text-xs);color:var(--text-subtle);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-arch__aside{flex:none;display:flex;align-items:center;gap:10px;}
.irb-arch__check{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;flex:none;
  border-radius:var(--radius-sm,7px);border:1px solid var(--border-strong,#cdd3da);background:var(--surface-card,#fff);
  color:var(--text-body);cursor:pointer;}
.irb-arch__check--on{background:var(--accent);border-color:var(--accent);color:var(--accent-fg,#fff);}
.irb-arch__check:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
@media (max-width:560px){.irb-arch__no{display:none;}}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-arch-css")) {
  const s = document.createElement("style"); s.id = "irb-arch-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function ArchiveList({
  items, inBasket, onToggleBasket, onOpen, startIndex = 0,
}: {
  items: ResultItem[];
  inBasket: (mfn: number) => boolean;
  onToggleBasket: (it: ResultItem) => void;
  onOpen: (mfn: number) => void;
  startIndex?: number;
}) {
  return (
    <div className="irb-arch" role="list">
      {items.map((it, i) => {
        const on = inBasket(it.mfn);
        return (
          <div
            key={it.mfn} role="listitem" className="irb-arch__row" tabIndex={0}
            onClick={() => onOpen(it.mfn)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(it.mfn); } }}
            aria-label={"Открыть: " + (it.title || "единица хранения")}
          >
            <span className="irb-arch__no" aria-hidden="true">{startIndex + i + 1}</span>
            <span className="irb-arch__icon" aria-hidden="true"><Icon name="archive" size={16} /></span>
            <span className="irb-arch__body">
              <span className="irb-arch__title">{it.title || "Без заглавия"}</span>
              {(it.author || it.year || it.docType) && (
                <span className="irb-arch__meta">{[it.author, it.year, it.docType].filter(Boolean).join(" · ")}</span>
              )}
            </span>
            <span className="irb-arch__aside" onClick={(e) => e.stopPropagation()}>
              <StatusBadge status={it.availability || "unknown"} size="sm" />
              <button
                type="button" className={"irb-arch__check" + (on ? " irb-arch__check--on" : "")}
                aria-pressed={on} aria-label={on ? "Убрать из корзины" : "Добавить в корзину"}
                onClick={(e) => { e.stopPropagation(); onToggleBasket(it); }}
              >
                <Icon name={on ? "check" : "plus"} size={15} />
              </button>
            </span>
          </div>
        );
      })}
    </div>
  );
}
