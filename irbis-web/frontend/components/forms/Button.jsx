import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:var(--space-2);
  font-family:var(--font-ui);font-weight:var(--weight-semibold);
  border:var(--border-width) solid transparent;border-radius:var(--radius-md);
  cursor:pointer;white-space:nowrap;text-decoration:none;
  transition:background-color var(--dur) var(--ease-standard),
    border-color var(--dur) var(--ease-standard),
    color var(--dur) var(--ease-standard), transform var(--dur-fast) var(--ease-standard);
  -webkit-tap-highlight-color:transparent;
}
.irb-btn:disabled,.irb-btn[aria-disabled="true"]{opacity:.5;cursor:not-allowed;}
.irb-btn:active:not(:disabled){transform:translateY(.5px);}

.irb-btn--sm{height:var(--control-h-sm);padding:0 var(--space-3);font-size:var(--text-sm);}
.irb-btn--md{height:var(--control-h-md);padding:0 var(--space-4);font-size:var(--text-base);}
.irb-btn--lg{height:var(--control-h-lg);padding:0 var(--space-6);font-size:var(--text-md);}
.irb-btn--block{width:100%;}

.irb-btn--primary{background:var(--accent);color:var(--accent-fg);}
.irb-btn--primary:hover:not(:disabled){background:var(--accent-hover);}
.irb-btn--primary:active:not(:disabled){background:var(--accent-press);}

.irb-btn--secondary{background:var(--surface-card);color:var(--text-strong);border-color:var(--border-default);}
.irb-btn--secondary:hover:not(:disabled){background:var(--surface-hover);border-color:var(--border-strong);}
.irb-btn--secondary:active:not(:disabled){background:var(--surface-active);}

.irb-btn--ghost{background:transparent;color:var(--accent);}
.irb-btn--ghost:hover:not(:disabled){background:var(--accent-weak);}
.irb-btn--ghost:active:not(:disabled){background:var(--accent-weak-hover);}

.irb-btn--danger{background:var(--danger-500);color:#fff;}
.irb-btn--danger:hover:not(:disabled){background:var(--danger-600);}

.irb-btn__spin{animation:irb-spin .7s linear infinite;}
@keyframes irb-spin{to{transform:rotate(360deg);}}
@media (prefers-reduced-motion:reduce){.irb-btn__spin{animation:none;}}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-btn-css")) {
  const s = document.createElement("style");
  s.id = "irb-btn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  iconLeft,
  iconRight,
  loading = false,
  block = false,
  disabled = false,
  type = "button",
  className = "",
  ...rest
}) {
  const isDisabled = disabled || loading;
  const iconSize = size === "sm" ? 16 : size === "lg" ? 20 : 18;
  return (
    <button
      type={type}
      className={`irb-btn irb-btn--${variant} irb-btn--${size}${block ? " irb-btn--block" : ""} ${className}`}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <Icon name="loader" size={iconSize} className="irb-btn__spin" />
      ) : iconLeft ? (
        <Icon name={iconLeft} size={iconSize} />
      ) : null}
      {children != null && <span>{children}</span>}
      {!loading && iconRight ? <Icon name={iconRight} size={iconSize} /> : null}
    </button>
  );
}
