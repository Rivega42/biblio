import React from "react";
import { Icon } from "../icon/Icon.jsx";

/* Доменные статус-бейджи Biblio Style A: цветной текст на мягкой подложке,
   точка-индикатор, мягкое скругление. Цвета — из токенов --status-*. */
const CSS = `
.irb-status{
  display:inline-flex;align-items:center;gap:var(--space-2);
  font-family:var(--font-ui);font-weight:var(--weight-semibold);
  border-radius:var(--radius-md);border:var(--border-width) solid transparent;
  white-space:nowrap;line-height:1;
}
.irb-status--md{font-size:var(--text-sm);height:26px;padding:0 var(--space-3);}
.irb-status--sm{font-size:var(--text-xs);height:22px;padding:0 var(--space-2);}
.irb-status__bdot{width:6px;height:6px;border-radius:var(--radius-round);flex:none;background:currentColor;}
.irb-status--dot{display:inline-flex;align-items:center;gap:var(--space-2);
  background:transparent;border:none;padding:0;font-weight:var(--weight-medium);font-size:var(--text-sm);}
.irb-status__dot{width:9px;height:9px;border-radius:var(--radius-round);flex:none;}

.irb-status--available{background:var(--status-available-bg);color:var(--status-available-strong);}
.irb-status--issued{background:var(--status-issued-bg);color:var(--status-issued-strong);}
.irb-status--hold{background:var(--status-hold-bg);color:var(--status-hold);}
.irb-status--returned{background:var(--status-return-bg);color:var(--status-return);}
.irb-status--unknown{background:var(--status-unknown-bg);color:var(--status-unknown-strong);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-status-css")) {
  const s = document.createElement("style");
  s.id = "irb-status-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const MAP = {
  available: { text: "В наличии", dot: "var(--status-available)" },
  issued: { text: "На руках", dot: "var(--status-issued)" },
  hold: { text: "В постамате", dot: "var(--status-hold)" },
  returned: { text: "Книгоприём", dot: "var(--status-return)" },
  unknown: { text: "Нет данных", dot: "var(--status-unknown)" },
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
      <span className="irb-status__bdot" aria-hidden="true"></span>
      {text}
    </span>
  );
}
