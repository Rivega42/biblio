import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-toastwrap{
  position:fixed;z-index:var(--z-toast);bottom:var(--space-6);right:var(--space-6);
  display:flex;flex-direction:column;gap:var(--space-2);max-width:380px;width:calc(100vw - 2 * var(--space-6));
  pointer-events:none;
}
.irb-toast{
  pointer-events:auto;display:flex;gap:var(--space-3);align-items:flex-start;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-left-width:3px;border-radius:var(--radius-md);box-shadow:var(--shadow-lg);
  padding:var(--space-3) var(--space-4);font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);
  animation:irb-toast-in var(--dur-slow) var(--ease-out);
}
@keyframes irb-toast-in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){.irb-toast{animation:none;}}
.irb-toast__icon{flex:none;margin-top:1px;}
.irb-toast__body{flex:1;min-width:0;}
.irb-toast__title{font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-toast__close{flex:none;border:none;background:transparent;cursor:pointer;color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);}
.irb-toast__close:hover{color:var(--text-strong);background:var(--surface-hover);}
.irb-toast--success{border-left-color:var(--status-available);}
.irb-toast--success .irb-toast__icon{color:var(--status-available);}
.irb-toast--warning{border-left-color:var(--status-issued);}
.irb-toast--warning .irb-toast__icon{color:var(--status-issued);}
.irb-toast--error{border-left-color:var(--danger-500);}
.irb-toast--error .irb-toast__icon{color:var(--danger-500);}
.irb-toast--info{border-left-color:var(--accent);}
.irb-toast--info .irb-toast__icon{color:var(--accent);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-toast-css")) {
  const s = document.createElement("style");
  s.id = "irb-toast-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const ICONS = { info: "info", success: "check-circle", warning: "alert-triangle", error: "alert-octagon" };

export function Toast({ variant = "info", title, children, onClose, className = "" }) {
  return (
    <div className={`irb-toast irb-toast--${variant} ${className}`} role="status">
      <Icon name={ICONS[variant]} size={18} className="irb-toast__icon" />
      <div className="irb-toast__body">
        {title && <div className="irb-toast__title">{title}</div>}
        {children && <div>{children}</div>}
      </div>
      {onClose && (
        <button type="button" className="irb-toast__close" aria-label="Закрыть" onClick={onClose}>
          <Icon name="x" size={16} />
        </button>
      )}
    </div>
  );
}

/** Контейнер для стопки тостов (фиксированный, правый нижний угол). */
export function ToastViewport({ toasts = [], onDismiss }) {
  return (
    <div className="irb-toastwrap" aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <Toast key={t.id} variant={t.variant} title={t.title} onClose={() => onDismiss && onDismiss(t.id)}>
          {t.message}
        </Toast>
      ))}
    </div>
  );
}
