import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { Input } from "../forms/Input.jsx";
import { Select } from "../forms/Select.jsx";
import { IconButton } from "../forms/IconButton.jsx";

/* DynamicField (§6 ТЗ) — «главный» компонент каталогизации: ТИП ПОЛЯ
   определяет контрол. Управляется декларативным описанием поля из профиля
   базы (FIELD_CATALOG): тип ввода, метка, MARC-код, подполя, повторяемость,
   словарь/меню/дерево/авторитет, ФЛК. UI-only: значения наружу через onChange. */

const CSS = `
.irb-dyn{font-family:var(--font-ui);display:flex;flex-direction:column;gap:7px;}
.irb-dyn__head{display:flex;align-items:baseline;gap:8px;}
.irb-dyn__code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--accent);
  background:var(--accent-weak);border:1px solid var(--accent-weak-border);border-radius:var(--radius-xs);padding:1px 6px;flex:none;}
.irb-dyn__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-dyn__req{color:var(--danger-500);margin-left:2px;}
.irb-dyn__type{margin-left:auto;font-size:var(--text-2xs);color:var(--text-subtle);display:inline-flex;align-items:center;gap:4px;}
.irb-dyn__rep{display:flex;flex-direction:column;gap:8px;}
.irb-dyn__occ{display:flex;align-items:flex-start;gap:8px;}
.irb-dyn__occ-main{flex:1;min-width:0;}
.irb-dyn__sub{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;
  background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:10px;}
.irb-dyn__sublabel{display:block;font-size:var(--text-2xs);color:var(--text-muted);margin-bottom:4px;}
.irb-dyn__subcode{font-family:var(--font-mono);color:var(--text-subtle);}
.irb-dyn__add{align-self:flex-start;display:inline-flex;align-items:center;gap:5px;background:none;border:none;cursor:pointer;
  color:var(--text-link);font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);padding:2px 0;}
.irb-dyn__err{font-size:var(--text-xs);color:var(--danger-500);display:flex;align-items:center;gap:4px;}
.irb-dyn__hint{font-size:var(--text-xs);color:var(--text-muted);}

/* да-нет — сегмент */
.irb-dyn__seg{display:inline-flex;border:1px solid var(--border-default);border-radius:var(--radius-sm);overflow:hidden;}
.irb-dyn__seg button{border:none;background:var(--surface-card);color:var(--text-muted);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);padding:8px 16px;}
.irb-dyn__seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-fg);}
.irb-dyn__seg button + button{border-left:1px solid var(--border-default);}

/* combobox словаря/авторитета */
.irb-dyn__cb{position:relative;}
.irb-dyn__menu{position:absolute;z-index:var(--z-overlay);top:calc(100% + 4px);left:0;right:0;max-height:230px;overflow:auto;
  background:var(--surface-card);border:1px solid var(--border-default);border-radius:var(--radius-md);box-shadow:var(--shadow-lg);padding:4px;}
.irb-dyn__opt{display:flex;align-items:center;gap:8px;width:100%;text-align:left;border:none;background:transparent;cursor:pointer;
  border-radius:var(--radius-sm);padding:7px 9px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-dyn__opt:hover,.irb-dyn__opt--on{background:var(--surface-hover);}
.irb-dyn__opt small{margin-left:auto;color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-dyn__auth{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--accent);flex:none;}

/* дерево .tre */
.irb-dyn__tree{border:1px solid var(--border-default);border-radius:var(--radius-md);background:var(--surface-card);max-height:260px;overflow:auto;padding:4px;}
.irb-dyn__node{display:flex;align-items:center;gap:4px;border-radius:var(--radius-sm);}
.irb-dyn__node:hover{background:var(--surface-hover);}
.irb-dyn__twirl{flex:none;width:22px;height:22px;display:flex;align-items:center;justify-content:center;border:none;background:none;cursor:pointer;color:var(--text-subtle);}
.irb-dyn__twirl svg{transition:transform var(--dur) var(--ease-standard);}
.irb-dyn__twirl--open svg{transform:rotate(90deg);}
.irb-dyn__pick{flex:1;text-align:left;border:none;background:none;cursor:pointer;padding:6px 4px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);display:flex;gap:8px;}
.irb-dyn__pick--on{color:var(--accent-press);font-weight:var(--weight-semibold);}
.irb-dyn__pick code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--text-subtle);}
.irb-dyn__chosen{display:inline-flex;align-items:center;gap:6px;margin-top:6px;font-size:var(--text-xs);color:var(--accent-press);background:var(--accent-weak);border:1px solid var(--accent-weak-border);border-radius:var(--radius-pill);padding:3px 10px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-dyn-css")) {
  const s = document.createElement("style");
  s.id = "irb-dyn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const TYPE_META = {
  text: { label: "текст", icon: "type" },
  menu: { label: "меню (.mnu)", icon: "list" },
  dict: { label: "словарь", icon: "search" },
  tree: { label: "справочник (.tre)", icon: "list-tree" },
  bool: { label: "да / нет", icon: "check-circle" },
  authority: { label: "авторитет", icon: "shield" },
  date: { label: "дата", icon: "calendar" },
};

function Combobox({ value, onChange, options = [], placeholder, authority }) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  const text = q || value || "";
  const filtered = options.filter((o) => (o.term || o.label || o).toLowerCase().startsWith((q || "").toLowerCase()));
  return (
    <div className="irb-dyn__cb" ref={ref}>
      <Input size="sm" iconLeft={authority ? "shield" : "search"} value={text} placeholder={placeholder}
        onChange={(e) => { setQ(e.target.value); onChange(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)} onClear={text ? () => { setQ(""); onChange(""); } : undefined} />
      {open && filtered.length > 0 && (
        <div className="irb-dyn__menu" role="listbox">
          {filtered.map((o) => {
            const term = o.term || o.label || o;
            return (
              <button key={term} type="button" className={"irb-dyn__opt" + (term === value ? " irb-dyn__opt--on" : "")}
                onClick={() => { onChange(term); setQ(""); setOpen(false); }}>
                {authority && o.code && <span className="irb-dyn__auth">{o.code}</span>}
                {term}
                {o.count != null && <small>{o.count}</small>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TreeNode({ node, depth, value, onPick }) {
  const [open, setOpen] = React.useState(depth < 1);
  const has = node.children && node.children.length;
  return (
    <div>
      <div className="irb-dyn__node" style={{ paddingLeft: depth * 14 }}>
        {has ? (
          <button type="button" className={"irb-dyn__twirl" + (open ? " irb-dyn__twirl--open" : "")} onClick={() => setOpen((o) => !o)} aria-label={open ? "Свернуть" : "Развернуть"}>
            <Icon name="chevron-right" size={15} />
          </button>
        ) : <span style={{ width: 22, flex: "none" }} />}
        <button type="button" className={"irb-dyn__pick" + (value === node.code ? " irb-dyn__pick--on" : "")} onClick={() => onPick(node)}>
          {node.code && <code>{node.code}</code>} {node.label}
        </button>
      </div>
      {has && open && node.children.map((c) => <TreeNode key={c.code || c.label} node={c} depth={depth + 1} value={value} onPick={onPick} />)}
    </div>
  );
}

function Control({ field, value, onChange }) {
  switch (field.type) {
    case "menu":
      return <Select size="sm" value={value || ""} onChange={(e) => onChange(e.target.value)}
        options={[{ value: "", label: field.placeholder || "— выберите —" }].concat((field.options || []).map((o) => (typeof o === "string" ? { value: o, label: o } : o)))} />;
    case "bool":
      return (
        <div className="irb-dyn__seg" role="group" aria-label={field.label}>
          {(field.options || ["Да", "Нет"]).map((o) => {
            const v = typeof o === "string" ? o : o.value;
            return <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(value === v ? "" : v)}>{typeof o === "string" ? o : o.label}</button>;
          })}
        </div>
      );
    case "date":
      return <Input size="sm" iconLeft="calendar" value={value || ""} placeholder={field.placeholder || "ГГГГ или ГГГГ-ММ-ДД"} onChange={(e) => onChange(e.target.value)} />;
    case "dict":
      return <Combobox value={value} onChange={onChange} options={field.dictionary || field.options || []} placeholder={field.placeholder || "ввод по словарю (префикс)…"} />;
    case "authority":
      return <Combobox value={value} onChange={onChange} options={field.authority || field.options || []} placeholder={field.placeholder || "поиск в авторитетном файле…"} authority />;
    case "tree":
      return (
        <div>
          <div className="irb-dyn__tree" role="tree">
            {(field.tree || []).map((n) => <TreeNode key={n.code || n.label} node={n} depth={0} value={value} onPick={(node) => onChange(node.code)} />)}
          </div>
          {value && <span className="irb-dyn__chosen"><Icon name="check" size={13} /> выбрано: {value}</span>}
        </div>
      );
    default:
      return <Input size="sm" value={value || ""} placeholder={field.placeholder || "значение"} onChange={(e) => onChange(e.target.value)} />;
  }
}

export function DynamicField({ field, value, onChange, error, className = "" }) {
  const meta = TYPE_META[field.type] || TYPE_META.text;
  const repeatable = !!field.repeatable;
  const hasSub = field.subfields && field.subfields.length;

  // Значение: повторяемое → массив «вхождений»; вхождение с подполями → объект.
  const occurrences = repeatable ? (Array.isArray(value) ? value : [hasSub ? {} : ""]) : [value];
  const setOcc = (i, v) => {
    if (!repeatable) return onChange(v);
    const next = occurrences.slice();
    next[i] = v;
    onChange(next);
  };
  const addOcc = () => onChange(occurrences.concat([hasSub ? {} : ""]));
  const delOcc = (i) => onChange(occurrences.filter((_, j) => j !== i));

  const renderOcc = (occ, i) => (
    <div className="irb-dyn__occ" key={i}>
      <div className="irb-dyn__occ-main">
        {hasSub ? (
          <div className="irb-dyn__sub">
            {field.subfields.map((sf) => (
              <div key={sf.code}>
                <span className="irb-dyn__sublabel"><span className="irb-dyn__subcode">^{sf.code}</span> {sf.label}</span>
                <Control field={sf} value={(occ || {})[sf.code] || ""} onChange={(v) => setOcc(i, { ...(occ || {}), [sf.code]: v })} />
              </div>
            ))}
          </div>
        ) : (
          <Control field={field} value={occ} onChange={(v) => setOcc(i, v)} />
        )}
      </div>
      {repeatable && occurrences.length > 1 && (
        <IconButton icon="trash" label="Удалить повторение" size="sm" variant="ghost" onClick={() => delOcc(i)} />
      )}
    </div>
  );

  return (
    <div className={"irb-dyn " + className}>
      <div className="irb-dyn__head">
        {field.code && <span className="irb-dyn__code">{field.code}</span>}
        <span className="irb-dyn__label">{field.label}{field.required && <span className="irb-dyn__req" aria-hidden="true">*</span>}</span>
        <span className="irb-dyn__type"><Icon name={meta.icon} size={12} /> {meta.label}{repeatable ? " · повтор." : ""}</span>
      </div>
      <div className="irb-dyn__rep">
        {occurrences.map(renderOcc)}
      </div>
      {repeatable && (
        <button type="button" className="irb-dyn__add" onClick={addOcc}><Icon name="plus" size={13} /> Добавить повторение поля</button>
      )}
      {error ? <span className="irb-dyn__err"><Icon name="alert-triangle" size={13} /> {error}</span>
        : field.hint ? <span className="irb-dyn__hint">{field.hint}</span> : null}
    </div>
  );
}
