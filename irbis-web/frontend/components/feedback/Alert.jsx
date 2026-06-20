import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-alert{
  display:flex;gap:var(--space-3);align-items:flex-start;
  border:var(--border-width) solid;border-radius:var(--radius-md);
  padding:var(--space-3) var(--space-4);font-family:var(--font-ui);font-size:var(--text-sm);
  line-height:var(--leading-snug);color:var(--text-body);
}
.irb-alert__icon{flex:none;margin-top:1px;}
.irb-alert__body{flex:1;min-width:0;}
.irb-alert__title{font-weight:var(--weight-semibold);color:var(--text-strong);margin-bottom:2px;}
.irb-alert__close{flex:none;border:none;background:transparent;cursor:pointer;color:var(--text-muted);padding:2px;border-radius:var(--radius-sm);margin:-2px -2px 0 0;}
.irb-alert__close:hover{color:var(--text-strong);background:rgba(0,0,0,.06);}

.irb-alert--info{background:var(--info-bg);border-color:var(--accent-weak-border);}
.irb-alert--info .irb-alert__icon{color:var(--accent);}
.irb-alert--success{background:var(--success-bg);border-color:var(--status-available-border);}
.irb-alert--success .irb-alert__icon{color:var(--status-available);}
.irb-alert--warning{background:var(--warning-bg);border-color:var(--status-issued-border);}
.irb-alert--warning .irb-alert__icon{color:var(--status-issued);}
.irb-alert--error{background:var(--danger-bg);border-color:var(--danger-border);}
.irb-alert--error .irb-alert__icon{color:var(--danger-500);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-alert-css")) {
  const s = document.createElement("style");
  s.id = "irb-alert-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const ICONS = { info: "info", success: "check-circle", warning: "alert-triangle", error: "alert-octagon" };

export function Alert({ variant = "info", title, children, onClose, className = "", ...rest }) {
  return (
    <div className={`irb-alert irb-alert--${variant} ${className}`} role={variant === "error" ? "alert" : "status"} {...rest}>
      <Icon name={ICONS[variant]} size={18} className="irb-alert__icon" />
      <div className="irb-alert__body">
        {title && <div className="irb-alert__title">{title}</div>}
        {children}
      </div>
      {onClose && (
        <button type="button" className="irb-alert__close" aria-label="Закрыть" onClick={onClose}>
          <Icon name="x" size={16} />
        </button>
      )}
    </div>
  );
}
