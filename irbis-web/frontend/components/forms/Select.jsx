import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-select{position:relative;display:flex;flex-direction:column;gap:var(--space-2);}
.irb-select__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-select__wrap{position:relative;display:flex;align-items:center;}
.irb-select__el{
  appearance:none;-webkit-appearance:none;width:100%;
  font-family:var(--font-ui);font-size:var(--text-base);color:var(--text-body);
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);cursor:pointer;
  padding:0 var(--space-8) 0 var(--space-3);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-select__el--sm{height:var(--control-h-sm);}
.irb-select__el--md{height:var(--control-h-md);}
.irb-select__el--lg{height:var(--control-h-lg);}
.irb-select__el:hover{border-color:var(--border-strong);}
.irb-select__el:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-select__el:disabled{background:var(--surface-sunken);opacity:.7;cursor:not-allowed;}
.irb-select__chev{position:absolute;right:var(--space-3);color:var(--text-subtle);pointer-events:none;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-select-css")) {
  const s = document.createElement("style");
  s.id = "irb-select-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _sid = 0;

export function Select({
  label,
  options = [],
  size = "md",
  id,
  disabled = false,
  className = "",
  children,
  ...rest
}) {
  const autoId = React.useMemo(() => id || `irb-sel-${++_sid}`, [id]);
  return (
    <div className={`irb-select ${className}`}>
      {label && (
        <label className="irb-select__label" htmlFor={autoId}>{label}</label>
      )}
      <div className="irb-select__wrap">
        <select
          id={autoId}
          className={`irb-select__el irb-select__el--${size}`}
          disabled={disabled}
          {...rest}
        >
          {children
            ? children
            : options.map((o) => {
                const value = typeof o === "string" ? o : o.value;
                const text = typeof o === "string" ? o : o.label;
                return (
                  <option key={value} value={value}>{text}</option>
                );
              })}
        </select>
        <Icon name="chevron-down" size={18} className="irb-select__chev" />
      </div>
    </div>
  );
}
