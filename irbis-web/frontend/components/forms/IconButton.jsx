import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-iconbtn{
  display:inline-flex;align-items:center;justify-content:center;
  border:var(--border-width) solid transparent;border-radius:var(--radius-md);
  background:transparent;color:var(--text-muted);cursor:pointer;
  transition:background-color var(--dur) var(--ease-standard),
    color var(--dur) var(--ease-standard), border-color var(--dur) var(--ease-standard);
  -webkit-tap-highlight-color:transparent;
}
.irb-iconbtn:hover:not(:disabled){background:var(--surface-hover);color:var(--text-strong);}
.irb-iconbtn:active:not(:disabled){background:var(--surface-active);}
.irb-iconbtn:disabled{opacity:.45;cursor:not-allowed;}
.irb-iconbtn--sm{width:var(--control-h-sm);height:var(--control-h-sm);}
.irb-iconbtn--md{width:var(--control-h-md);height:var(--control-h-md);}
.irb-iconbtn--lg{width:var(--control-h-lg);height:var(--control-h-lg);}
.irb-iconbtn--outline{border-color:var(--border-default);background:var(--surface-card);}
.irb-iconbtn--outline:hover:not(:disabled){border-color:var(--border-strong);}
.irb-iconbtn--accent{color:var(--accent);}
.irb-iconbtn--accent:hover:not(:disabled){background:var(--accent-weak);color:var(--accent-hover);}
.irb-iconbtn--solid{background:var(--accent);color:var(--accent-fg);}
.irb-iconbtn--solid:hover:not(:disabled){background:var(--accent-hover);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-iconbtn-css")) {
  const s = document.createElement("style");
  s.id = "irb-iconbtn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function IconButton({
  icon,
  label,
  variant = "ghost",
  size = "md",
  disabled = false,
  className = "",
  ...rest
}) {
  const iconSize = size === "sm" ? 18 : size === "lg" ? 24 : 20;
  return (
    <button
      type="button"
      className={`irb-iconbtn irb-iconbtn--${variant} irb-iconbtn--${size} ${className}`}
      aria-label={label}
      title={label}
      disabled={disabled}
      {...rest}
    >
      <Icon name={icon} size={iconSize} />
    </button>
  );
}
