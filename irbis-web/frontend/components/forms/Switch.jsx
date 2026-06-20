import React from "react";

const CSS = `
.irb-switch{display:inline-flex;align-items:center;gap:var(--space-3);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-switch--disabled{opacity:.5;cursor:not-allowed;}
.irb-switch__track{
  flex:none;position:relative;width:40px;height:24px;border-radius:var(--radius-pill);
  background:var(--surface-active);border:var(--border-width) solid var(--border-default);
  transition:background-color var(--dur) var(--ease-standard), border-color var(--dur) var(--ease-standard);
}
.irb-switch input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-switch__thumb{
  position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:var(--radius-round);
  background:#fff;box-shadow:var(--shadow-xs);
  transition:transform var(--dur) var(--ease-standard);
}
.irb-switch input:checked + .irb-switch__track{background:var(--accent);border-color:var(--accent);}
.irb-switch input:checked + .irb-switch__track .irb-switch__thumb{transform:translateX(16px);}
.irb-switch input:focus-visible + .irb-switch__track{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-switch-css")) {
  const s = document.createElement("style");
  s.id = "irb-switch-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Switch({ label, checked, disabled = false, className = "", ...rest }) {
  return (
    <label className={`irb-switch${disabled ? " irb-switch--disabled" : ""} ${className}`}>
      <input type="checkbox" role="switch" checked={checked} disabled={disabled} {...rest} />
      <span className="irb-switch__track" aria-hidden="true">
        <span className="irb-switch__thumb"></span>
      </span>
      {label != null && <span>{label}</span>}
    </label>
  );
}
