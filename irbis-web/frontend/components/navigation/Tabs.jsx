import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-tabs{display:flex;gap:var(--space-1);border-bottom:var(--border-width) solid var(--border-subtle);font-family:var(--font-ui);}
.irb-tabs--pill{border-bottom:none;background:var(--surface-sunken);padding:4px;border-radius:var(--radius-md);gap:2px;width:max-content;}
.irb-tab{
  display:inline-flex;align-items:center;gap:var(--space-2);
  background:none;border:none;cursor:pointer;color:var(--text-muted);
  font-size:var(--text-sm);font-weight:var(--weight-semibold);
  padding:var(--space-3) var(--space-3);position:relative;
  transition:color var(--dur) var(--ease-standard);
}
.irb-tab:hover{color:var(--text-strong);}
.irb-tab[aria-selected="true"]{color:var(--accent);}
.irb-tab[aria-selected="true"]::after{
  content:"";position:absolute;left:var(--space-3);right:var(--space-3);bottom:-1px;height:2px;
  background:var(--accent);border-radius:2px;
}
.irb-tab:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);border-radius:var(--radius-sm);}
.irb-tab__count{font-size:var(--text-xs);font-weight:var(--weight-medium);color:var(--text-subtle);
  background:var(--surface-sunken);border-radius:var(--radius-pill);padding:1px 7px;font-variant-numeric:tabular-nums;}
.irb-tab[aria-selected="true"] .irb-tab__count{background:var(--accent-weak);color:var(--accent);}

.irb-tabs--pill .irb-tab{border-radius:var(--radius-sm);padding:var(--space-2) var(--space-4);}
.irb-tabs--pill .irb-tab[aria-selected="true"]{background:var(--surface-card);color:var(--text-strong);box-shadow:var(--shadow-xs);}
.irb-tabs--pill .irb-tab[aria-selected="true"]::after{display:none;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-tabs-css")) {
  const s = document.createElement("style");
  s.id = "irb-tabs-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Tabs({ tabs = [], value, onChange, variant = "underline", className = "" }) {
  return (
    <div className={`irb-tabs irb-tabs--${variant} ${className}`} role="tablist">
      {tabs.map((t) => {
        const id = typeof t === "string" ? t : t.id;
        const label = typeof t === "string" ? t : t.label;
        const selected = id === value;
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={selected}
            className="irb-tab"
            onClick={() => onChange && onChange(id)}
          >
            {t.icon && <Icon name={t.icon} size={16} />}
            {label}
            {t.count != null && <span className="irb-tab__count">{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
