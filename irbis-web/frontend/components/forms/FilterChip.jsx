import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-chip{
  display:inline-flex;align-items:center;gap:var(--space-2);
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);
  height:var(--control-h-sm);padding:0 var(--space-1) 0 var(--space-3);
  border-radius:var(--radius-pill);border:var(--border-width) solid var(--accent-weak-border);
  background:var(--accent-weak);color:var(--accent-press);white-space:nowrap;
  transition:background-color var(--dur) var(--ease-standard);
}
.irb-chip--plain{background:var(--surface-sunken);border-color:var(--border-default);color:var(--text-body);}
.irb-chip__group{font-weight:var(--weight-regular);color:var(--text-muted);}
.irb-chip__remove{
  display:inline-flex;align-items:center;justify-content:center;
  width:22px;height:22px;border:none;border-radius:var(--radius-round);
  background:transparent;color:inherit;cursor:pointer;opacity:.75;
}
.irb-chip__remove:hover{opacity:1;background:rgba(0,0,0,.07);}
.irb-chip__remove:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);}

.irb-chip--toggle{cursor:pointer;padding:0 var(--space-3);background:var(--surface-card);
  border-color:var(--border-default);color:var(--text-body);}
.irb-chip--toggle:hover{border-color:var(--border-strong);background:var(--surface-hover);}
.irb-chip--toggle[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-fg);}
.irb-chip__count{font-weight:var(--weight-regular);opacity:.7;font-size:var(--text-xs);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-chip-css")) {
  const s = document.createElement("style");
  s.id = "irb-chip-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function FilterChip({
  label,
  group,
  count,
  onRemove,
  onToggle,
  pressed,
  plain = false,
  className = "",
  ...rest
}) {
  // Режим переключателя (выбор фильтра)
  if (onToggle) {
    return (
      <button
        type="button"
        className={`irb-chip irb-chip--toggle ${className}`}
        aria-pressed={!!pressed}
        onClick={onToggle}
        {...rest}
      >
        <span>{label}</span>
        {count != null && <span className="irb-chip__count">{count}</span>}
      </button>
    );
  }
  // Режим снимаемого чипа (активный фильтр)
  return (
    <span className={`irb-chip${plain ? " irb-chip--plain" : ""} ${className}`} {...rest}>
      {group && <span className="irb-chip__group">{group}:</span>}
      <span>{label}</span>
      {onRemove && (
        <button
          type="button"
          className="irb-chip__remove"
          aria-label={`Снять фильтр: ${group ? group + " " : ""}${label}`}
          onClick={onRemove}
        >
          <Icon name="x" size={14} />
        </button>
      )}
    </span>
  );
}
