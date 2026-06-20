import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-empty{
  display:flex;flex-direction:column;align-items:center;text-align:center;
  padding:var(--space-12) var(--space-6);font-family:var(--font-ui);max-width:440px;margin:0 auto;gap:var(--space-2);
}
.irb-empty__icon{
  width:64px;height:64px;border-radius:var(--radius-round);
  display:flex;align-items:center;justify-content:center;margin-bottom:var(--space-2);
  background:var(--surface-sunken);color:var(--text-muted);
  border:var(--border-width) solid var(--border-subtle);
}
.irb-empty--error .irb-empty__icon{background:var(--danger-bg);color:var(--danger-500);border-color:var(--danger-border);}
.irb-empty--locked .irb-empty__icon{background:var(--info-bg);color:var(--accent);border-color:var(--accent-weak-border);}
.irb-empty__title{font-family:var(--font-display);font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--text-strong);line-height:var(--leading-snug);}
.irb-empty__desc{font-size:var(--text-sm);color:var(--text-muted);line-height:var(--leading-normal);}
.irb-empty__hint{display:flex;flex-direction:column;gap:6px;margin-top:var(--space-2);font-size:var(--text-sm);color:var(--text-muted);text-align:left;}
.irb-empty__hint li{margin:0;}
.irb-empty__action{margin-top:var(--space-4);display:flex;gap:var(--space-2);flex-wrap:wrap;justify-content:center;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-empty-css")) {
  const s = document.createElement("style");
  s.id = "irb-empty-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const DEFAULT_ICON = { neutral: "search", error: "alert-triangle", locked: "log-in" };

export function EmptyState({ variant = "neutral", icon, title, description, hints, action, className = "" }) {
  return (
    <div className={`irb-empty irb-empty--${variant} ${className}`} role={variant === "error" ? "alert" : undefined}>
      <span className="irb-empty__icon"><Icon name={icon || DEFAULT_ICON[variant]} size={30} /></span>
      {title && <div className="irb-empty__title">{title}</div>}
      {description && <p className="irb-empty__desc">{description}</p>}
      {hints && hints.length > 0 && (
        <ul className="irb-empty__hint">
          {hints.map((h, i) => <li key={i}>• {h}</li>)}
        </ul>
      )}
      {action && <div className="irb-empty__action">{action}</div>}
    </div>
  );
}
