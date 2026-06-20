import React from "react";
import { IconButton } from "../forms/IconButton.jsx";

const CSS = `
.irb-overlay{
  position:fixed;inset:0;z-index:var(--z-modal);
  background:rgba(28,27,25,.46);backdrop-filter:blur(1.5px);
  display:flex;align-items:flex-start;justify-content:center;
  padding:var(--space-8) var(--space-4);overflow:auto;
  animation:irb-fade var(--dur) var(--ease-standard);
}
@keyframes irb-fade{from{opacity:0;}to{opacity:1;}}
.irb-dialog{
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);width:100%;margin:auto;
  display:flex;flex-direction:column;max-height:calc(100vh - 2 * var(--space-8));
  animation:irb-pop var(--dur-slow) var(--ease-out);
}
@keyframes irb-pop{from{opacity:0;transform:translateY(10px) scale(.99);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){.irb-overlay,.irb-dialog{animation:none;}}
.irb-dialog--sm{max-width:420px;}
.irb-dialog--md{max-width:560px;}
.irb-dialog--lg{max-width:760px;}
.irb-dialog__head{
  display:flex;align-items:flex-start;gap:var(--space-3);
  padding:var(--space-5) var(--space-5) var(--space-3);
}
.irb-dialog__titles{flex:1;min-width:0;}
.irb-dialog__title{font-family:var(--font-display);font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--text-strong);line-height:var(--leading-snug);}
.irb-dialog__sub{font-size:var(--text-sm);color:var(--text-muted);margin-top:4px;}
.irb-dialog__body{padding:0 var(--space-5) var(--space-5);overflow:auto;font-family:var(--font-ui);color:var(--text-body);}
.irb-dialog__foot{
  display:flex;justify-content:flex-end;gap:var(--space-2);flex-wrap:wrap;
  padding:var(--space-4) var(--space-5);border-top:var(--border-width) solid var(--border-subtle);
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-dialog-css")) {
  const s = document.createElement("style");
  s.id = "irb-dialog-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _did = 0;

export function Dialog({ open, onClose, title, subtitle, children, footer, size = "md", className = "" }) {
  const id = React.useMemo(() => `irb-dlg-${++_did}`, []);
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="irb-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose && onClose()}>
      <div
        className={`irb-dialog irb-dialog--${size} ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? `${id}-t` : undefined}
      >
        <div className="irb-dialog__head">
          <div className="irb-dialog__titles">
            {title && <h2 className="irb-dialog__title" id={`${id}-t`}>{title}</h2>}
            {subtitle && <div className="irb-dialog__sub">{subtitle}</div>}
          </div>
          {onClose && <IconButton icon="x" label="Закрыть" onClick={onClose} />}
        </div>
        <div className="irb-dialog__body">{children}</div>
        {footer && <div className="irb-dialog__foot">{footer}</div>}
      </div>
    </div>
  );
}
