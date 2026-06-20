import React from "react";

const CSS = `
.irb-badge{
  display:inline-flex;align-items:center;gap:5px;
  font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);
  line-height:1;padding:3px 8px;border-radius:var(--radius-pill);
  border:var(--border-width) solid transparent;white-space:nowrap;
}
.irb-badge--neutral{background:var(--surface-sunken);color:var(--text-muted);border-color:var(--border-subtle);}
.irb-badge--accent{background:var(--accent-weak);color:var(--accent-press);border-color:var(--accent-weak-border);}
.irb-badge--solid{background:var(--accent);color:var(--accent-fg);}
.irb-badge--success{background:var(--success-bg);color:var(--status-available-strong);border-color:var(--status-available-border);}
.irb-badge--warning{background:var(--warning-bg);color:var(--status-issued-strong);border-color:var(--status-issued-border);}
.irb-badge--danger{background:var(--danger-bg);color:var(--danger-600);border-color:var(--danger-border);}
.irb-badge--count{min-width:18px;height:18px;justify-content:center;padding:0 5px;font-variant-numeric:tabular-nums;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-badge-css")) {
  const s = document.createElement("style");
  s.id = "irb-badge-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Badge({ variant = "neutral", count = false, children, className = "", ...rest }) {
  return (
    <span className={`irb-badge irb-badge--${variant}${count ? " irb-badge--count" : ""} ${className}`} {...rest}>
      {children}
    </span>
  );
}
