import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-status{
  display:inline-flex;align-items:center;gap:var(--space-2);
  font-family:var(--font-ui);font-weight:var(--weight-semibold);
  border-radius:var(--radius-pill);border:var(--border-width) solid transparent;
  white-space:nowrap;line-height:1;
}
.irb-status--md{font-size:var(--text-sm);height:26px;padding:0 var(--space-3);}
.irb-status--sm{font-size:var(--text-xs);height:22px;padding:0 var(--space-2);}
.irb-status--dot{display:inline-flex;align-items:center;gap:var(--space-2);
  background:transparent;border:none;padding:0;font-weight:var(--weight-medium);font-size:var(--text-sm);}
.irb-status__dot{width:9px;height:9px;border-radius:var(--radius-round);flex:none;}

.irb-status--available{background:var(--status-available-bg);border-color:var(--status-available-border);color:var(--status-available-strong);}
.irb-status--issued{background:var(--status-issued-bg);border-color:var(--status-issued-border);color:var(--status-issued-strong);}
.irb-status--unknown{background:var(--status-unknown-bg);border-color:var(--status-unknown-border);color:var(--status-unknown-strong);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-status-css")) {
  const s = document.createElement("style");
  s.id = "irb-status-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const MAP = {
  available: { icon: "check-circle", text: "Доступен", dot: "var(--status-available)" },
  issued: { icon: "clock", text: "Выдан", dot: "var(--status-issued)" },
  unknown: { icon: "x-circle", text: "Нет данных", dot: "var(--status-unknown)" },
};

export function StatusBadge({ status = "unknown", label, size = "md", dot = false, className = "", ...rest }) {
  const cfg = MAP[status] || MAP.unknown;
  const text = label || cfg.text;
  if (dot) {
    return (
      <span className={`irb-status irb-status--dot ${className}`} {...rest}>
        <span className="irb-status__dot" style={{ background: cfg.dot }} aria-hidden="true"></span>
        {text}
      </span>
    );
  }
  return (
    <span className={`irb-status irb-status--${status} irb-status--${size} ${className}`} {...rest}>
      <Icon name={cfg.icon} size={size === "sm" ? 13 : 15} />
      {text}
    </span>
  );
}
