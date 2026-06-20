import React from "react";
import { Icon } from "../icon/Icon.jsx";

/* Модуль «Поисковые режимы» (§1.10, §7): список режимов поиска;
   выбранный ВЫДЕЛЯЕТСЯ ЦВЕТОМ. Состав режимов зависит от базы (конфиг). */

const CSS = `
.irb-modes{font-family:var(--font-ui);}
.irb-modes__hd{font-size:var(--text-2xs);text-transform:uppercase;letter-spacing:var(--tracking-caps);
  color:var(--text-subtle);font-weight:var(--weight-bold);margin-bottom:10px;}
.irb-modes__list{display:flex;flex-direction:column;gap:4px;}
.irb-modes__item{
  display:flex;align-items:center;gap:var(--space-2);width:100%;text-align:left;cursor:pointer;
  padding:9px var(--space-3);border-radius:var(--radius-sm);font-family:var(--font-ui);
  font-size:var(--text-sm);font-weight:var(--weight-medium);
  border:var(--border-width) solid transparent;background:transparent;color:var(--text-body);
  transition:background-color var(--dur) var(--ease-standard),color var(--dur) var(--ease-standard);
}
.irb-modes__item:hover{background:var(--surface-hover);}
.irb-modes__item--on{
  background:var(--accent-weak);border-color:var(--accent-weak-border);
  color:var(--accent-press);font-weight:var(--weight-semibold);
}
.irb-modes__item--on .irb-modes__ic{color:var(--accent);}
.irb-modes__ic{flex:none;color:var(--text-subtle);}
.irb-modes__bar{flex:none;width:3px;align-self:stretch;border-radius:2px;background:transparent;margin-right:2px;}
.irb-modes__item--on .irb-modes__bar{background:var(--accent);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-modes-css")) {
  const s = document.createElement("style");
  s.id = "irb-modes-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const META = {
  simple: { label: "Простой", icon: "search" },
  advanced: { label: "Расширенный", icon: "sliders" },
  complex: { label: "Комплексный", icon: "layers" },
  special: { label: "Спецформа базы", icon: "filter" },
};

export function SearchModes({ modes = ["simple"], value, onChange, heading = "Поисковые режимы", labels = {}, className = "" }) {
  return (
    <div className={`irb-modes ${className}`}>
      <div className="irb-modes__hd">{heading}</div>
      <div className="irb-modes__list" role="tablist" aria-label={heading}>
        {modes.map((m) => {
          const meta = META[m] || { label: m, icon: "search" };
          const on = m === value;
          return (
            <button
              key={m} type="button" role="tab" aria-selected={on}
              className={`irb-modes__item${on ? " irb-modes__item--on" : ""}`}
              onClick={() => onChange && onChange(m)}
            >
              <span className="irb-modes__bar" aria-hidden="true" />
              <Icon name={meta.icon} size={16} className="irb-modes__ic" />
              {labels[m] || meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
