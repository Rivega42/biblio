import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-field{display:flex;flex-direction:column;gap:var(--space-2);}
.irb-field__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-field__req{color:var(--danger-500);margin-inline-start:2px;}
.irb-field__hint{font-size:var(--text-xs);color:var(--text-muted);}
.irb-field__err{font-size:var(--text-xs);color:var(--danger-500);display:flex;align-items:center;gap:var(--space-1);}

.irb-input{
  display:flex;align-items:center;gap:var(--space-2);
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);color:var(--text-body);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-input--sm{height:var(--control-h-sm);padding:0 var(--space-3);}
.irb-input--md{height:var(--control-h-md);padding:0 var(--space-3);}
.irb-input--lg{height:var(--control-h-lg);padding:0 var(--space-4);}
.irb-input:hover{border-color:var(--border-strong);}
.irb-input:focus-within{border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-input--error{border-color:var(--danger-500);}
.irb-input--error:focus-within{box-shadow:0 0 0 var(--focus-ring-width) rgba(178,59,59,.3);}
.irb-input--disabled{background:var(--surface-sunken);opacity:.7;cursor:not-allowed;}
.irb-input__icon{color:var(--text-subtle);flex:none;}
.irb-input__el{
  flex:1;min-width:0;border:none;background:transparent;outline:none;
  font-family:var(--font-ui);font-size:var(--text-base);color:inherit;
}
.irb-input__el::placeholder{color:var(--text-subtle);}
.irb-input__clear{
  display:inline-flex;border:none;background:transparent;cursor:pointer;
  color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);flex:none;
}
.irb-input__clear:hover{color:var(--text-strong);background:var(--surface-hover);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-input-css")) {
  const s = document.createElement("style");
  s.id = "irb-input-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

let _uid = 0;

export function Input({
  label,
  hint,
  error,
  required = false,
  size = "md",
  iconLeft,
  onClear,
  value,
  disabled = false,
  id,
  className = "",
  ...rest
}) {
  const autoId = React.useMemo(() => id || `irb-in-${++_uid}`, [id]);
  const showClear = onClear && value != null && String(value).length > 0;
  return (
    <div className={`irb-field ${className}`}>
      {label && (
        <label className="irb-field__label" htmlFor={autoId}>
          {label}
          {required && <span className="irb-field__req" aria-hidden="true">*</span>}
        </label>
      )}
      <div
        className={`irb-input irb-input--${size}${error ? " irb-input--error" : ""}${disabled ? " irb-input--disabled" : ""}`}
      >
        {iconLeft && <Icon name={iconLeft} size={18} className="irb-input__icon" />}
        <input
          id={autoId}
          className="irb-input__el"
          value={value}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${autoId}-err` : hint ? `${autoId}-hint` : undefined}
          {...rest}
        />
        {showClear && (
          <button
            type="button"
            className="irb-input__clear"
            aria-label="Очистить"
            onClick={onClear}
          >
            <Icon name="x" size={16} />
          </button>
        )}
      </div>
      {error ? (
        <span className="irb-field__err" id={`${autoId}-err`}>
          <Icon name="alert-triangle" size={13} /> {error}
        </span>
      ) : hint ? (
        <span className="irb-field__hint" id={`${autoId}-hint`}>{hint}</span>
      ) : null}
    </div>
  );
}
