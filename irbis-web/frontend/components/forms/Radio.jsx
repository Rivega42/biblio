import React from "react";

const CSS = `
.irb-radio{display:inline-flex;align-items:flex-start;gap:var(--space-2);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);line-height:var(--leading-snug);}
.irb-radio--disabled{opacity:.5;cursor:not-allowed;}
.irb-radio__dot{
  flex:none;width:18px;height:18px;margin-top:1px;border-radius:var(--radius-round);
  border:var(--border-width-strong) solid var(--border-strong);background:var(--surface-card);
  display:inline-flex;align-items:center;justify-content:center;
  transition:border-color var(--dur-fast) var(--ease-standard);
}
.irb-radio input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-radio__dot::after{content:"";width:8px;height:8px;border-radius:var(--radius-round);
  background:var(--accent);transform:scale(0);transition:transform var(--dur-fast) var(--ease-standard);}
.irb-radio input:checked + .irb-radio__dot{border-color:var(--accent);}
.irb-radio input:checked + .irb-radio__dot::after{transform:scale(1);}
.irb-radio input:focus-visible + .irb-radio__dot{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-radio-css")) {
  const s = document.createElement("style");
  s.id = "irb-radio-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Radio({ label, disabled = false, className = "", ...rest }) {
  return (
    <label className={`irb-radio${disabled ? " irb-radio--disabled" : ""} ${className}`}>
      <input type="radio" disabled={disabled} {...rest} />
      <span className="irb-radio__dot" aria-hidden="true"></span>
      {label != null && <span>{label}</span>}
    </label>
  );
}
