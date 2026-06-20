import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-check{display:inline-flex;align-items:flex-start;gap:var(--space-2);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);line-height:var(--leading-snug);}
.irb-check--disabled{opacity:.5;cursor:not-allowed;}
.irb-check__box{
  flex:none;width:18px;height:18px;margin-top:1px;border-radius:var(--radius-xs);
  border:var(--border-width-strong) solid var(--border-strong);background:var(--surface-card);
  display:inline-flex;align-items:center;justify-content:center;color:#fff;
  transition:background-color var(--dur-fast) var(--ease-standard), border-color var(--dur-fast) var(--ease-standard);
}
.irb-check input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-check input:checked + .irb-check__box,
.irb-check input:indeterminate + .irb-check__box{background:var(--accent);border-color:var(--accent);}
.irb-check input:focus-visible + .irb-check__box{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-check__mark{opacity:0;}
.irb-check input:checked + .irb-check__box .irb-check__mark{opacity:1;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-check-css")) {
  const s = document.createElement("style");
  s.id = "irb-check-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Checkbox({
  label,
  checked,
  indeterminate = false,
  disabled = false,
  className = "",
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <label className={`irb-check${disabled ? " irb-check--disabled" : ""} ${className}`}>
      <input
        ref={ref}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        {...rest}
      />
      <span className="irb-check__box" aria-hidden="true">
        <Icon
          name={indeterminate ? "minus" : "check"}
          size={13}
          strokeWidth={2.6}
          className="irb-check__mark"
          style={indeterminate ? { opacity: 1 } : undefined}
        />
      </span>
      {label != null && <span>{label}</span>}
    </label>
  );
}
