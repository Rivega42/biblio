import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { Button } from "../forms/Button.jsx";

const CSS = `
.irb-searchbar{position:relative;font-family:var(--font-ui);}
.irb-searchbar__row{display:flex;gap:var(--space-2);align-items:stretch;}
.irb-searchbar__field{
  flex:1;display:flex;align-items:center;gap:var(--space-2);min-width:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);padding:0 var(--space-3);height:var(--control-h-lg);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-searchbar__field:focus-within{border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-searchbar__field .irb-sb-ico{color:var(--text-subtle);flex:none;}
.irb-searchbar__input{
  flex:1;min-width:0;border:none;outline:none;background:transparent;
  font-family:var(--font-ui);font-size:var(--text-md);color:var(--text-body);
}
.irb-searchbar__input::placeholder{color:var(--text-subtle);}
.irb-searchbar__clear{display:inline-flex;border:none;background:transparent;cursor:pointer;color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);}
.irb-searchbar__clear:hover{color:var(--text-strong);background:var(--surface-hover);}

.irb-searchbar__sugg{
  position:absolute;z-index:var(--z-overlay);top:calc(var(--control-h-lg) + 6px);left:0;right:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);box-shadow:var(--shadow-lg);overflow:hidden;padding:var(--space-1);
}
.irb-searchbar__si{display:flex;align-items:center;gap:var(--space-2);width:100%;padding:var(--space-2) var(--space-3);
  border:none;background:transparent;cursor:pointer;text-align:left;color:var(--text-body);font-size:var(--text-sm);border-radius:var(--radius-sm);}
.irb-searchbar__si:hover,.irb-searchbar__si[data-active="true"]{background:var(--surface-hover);}
.irb-searchbar__si .irb-sb-sico{color:var(--text-subtle);flex:none;}
.irb-searchbar__si b{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-searchbar__sc{margin-left:auto;color:var(--text-subtle);font-size:var(--text-xs);font-variant-numeric:tabular-nums;}
.irb-searchbar__foot{display:flex;justify-content:flex-end;margin-top:var(--space-2);}
.irb-searchbar__adv{display:inline-flex;align-items:center;gap:6px;background:none;border:none;cursor:pointer;
  color:var(--text-link);font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);}
.irb-searchbar__adv:hover{text-decoration:underline;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-searchbar-css")) {
  const s = document.createElement("style");
  s.id = "irb-searchbar-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function SearchBar({
  value = "",
  onChange,
  onSearch,
  suggestions = [],
  onPickSuggestion,
  placeholder = "Введите запрос…",
  onAdvanced,
  onReset,
  buttonLabel = "Найти",
  className = "",
}) {
  const [focused, setFocused] = React.useState(false);
  const [active, setActive] = React.useState(-1);
  const wrapRef = React.useRef(null);
  const showSugg = focused && value.trim().length > 0 && suggestions.length > 0;

  React.useEffect(() => {
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setFocused(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const pick = (s) => {
    onPickSuggestion ? onPickSuggestion(s) : onChange && onChange(s.term || s);
    setFocused(false);
  };

  const onKeyDown = (e) => {
    if (!showSugg) {
      if (e.key === "Enter") onSearch && onSearch(value);
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, suggestions.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, -1)); }
    else if (e.key === "Enter") {
      if (active >= 0) { e.preventDefault(); pick(suggestions[active]); }
      else onSearch && onSearch(value);
    }
  };

  return (
    <div className={`irb-searchbar ${className}`} ref={wrapRef}>
      <div className="irb-searchbar__row">
        <div className="irb-searchbar__field" role="search">
          <Icon name="search" size={20} className="irb-sb-ico" />
          <input
            className="irb-searchbar__input"
            value={value}
            placeholder={placeholder}
            aria-label="Поисковый запрос"
            autoComplete="off"
            onChange={(e) => { onChange && onChange(e.target.value); setActive(-1); }}
            onFocus={() => setFocused(true)}
            onKeyDown={onKeyDown}
          />
          {value.length > 0 && (
            <button type="button" className="irb-searchbar__clear" aria-label="Очистить" onClick={() => onChange && onChange("")}>
              <Icon name="x" size={18} />
            </button>
          )}
        </div>
        <Button size="lg" iconLeft="search" onClick={() => onSearch && onSearch(value)}>{buttonLabel}</Button>
        {onReset && <Button size="lg" variant="secondary" iconLeft="rotate-ccw" onClick={onReset}>Сброс</Button>}
      </div>

      {onAdvanced && (
        <div className="irb-searchbar__foot">
          <button type="button" className="irb-searchbar__adv" onClick={onAdvanced}>
            <Icon name="sliders" size={15} /> Расширенный поиск
          </button>
        </div>
      )}

      {showSugg && (
        <div className="irb-searchbar__sugg" role="listbox" aria-label="Подсказки словаря">
          {suggestions.map((s, i) => {
            const term = s.term || s;
            return (
              <button
                key={term + i}
                type="button"
                role="option"
                aria-selected={i === active}
                data-active={i === active}
                className="irb-searchbar__si"
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(s)}
              >
                <Icon name="search" size={15} className="irb-sb-sico" />
                <span>{term}</span>
                {s.count != null && <span className="irb-searchbar__sc">{s.count.toLocaleString("ru-RU")}</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
