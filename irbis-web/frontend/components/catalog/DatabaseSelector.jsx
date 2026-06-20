import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { Checkbox } from "../forms/Checkbox.jsx";

/* Иерархический мультиселектор баз (§1.1 ТЗ): одно окно «Электронный
   каталог и Базы данных», раскрываемые группы (ЭК, Базы Либретто),
   чекбоксы, «Выбрать все» / «Снять всё», БЕЗ галочек по умолчанию. */

const CSS = `
.irb-dbsel{position:relative;font-family:var(--font-ui);}
.irb-dbsel__btn{
  display:flex;align-items:center;gap:var(--space-3);width:100%;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);padding:var(--space-2) var(--space-3);cursor:pointer;text-align:left;
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-dbsel__btn:hover{border-color:var(--border-strong);}
.irb-dbsel__btn:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-dbsel__mark{
  flex:none;width:38px;height:38px;border-radius:var(--radius-sm);
  display:flex;align-items:center;justify-content:center;
  background:var(--accent-weak);color:var(--accent);border:var(--border-width) solid var(--accent-weak-border);
}
.irb-dbsel__txt{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px;}
.irb-dbsel__eyebrow{display:block;font-size:var(--text-2xs);text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);font-weight:var(--weight-semibold);}
.irb-dbsel__name{font-size:var(--text-md);font-weight:var(--weight-semibold);color:var(--text-strong);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-dbsel__name--empty{color:var(--text-muted);font-weight:var(--weight-medium);}
.irb-dbsel__chev{color:var(--text-muted);flex:none;transition:transform var(--dur) var(--ease-standard);}
.irb-dbsel--open .irb-dbsel__chev{transform:rotate(180deg);}
.irb-dbsel__count{flex:none;display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 6px;
  border-radius:var(--radius-pill);background:var(--accent);color:var(--accent-fg);font-size:var(--text-2xs);font-weight:var(--weight-bold);}

.irb-dbsel__menu{
  position:absolute;z-index:var(--z-overlay);top:calc(100% + 6px);left:0;right:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-lg);
  max-height:440px;display:flex;flex-direction:column;overflow:hidden;min-width:340px;
}
.irb-dbsel__head{padding:var(--space-3) var(--space-4);border-bottom:var(--border-width) solid var(--border-subtle);}
.irb-dbsel__title{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);}
.irb-dbsel__tools{display:flex;align-items:center;gap:var(--space-3);margin-top:6px;}
.irb-dbsel__link{background:none;border:none;padding:0;cursor:pointer;color:var(--text-link);
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);}
.irb-dbsel__link:hover{text-decoration:underline;}
.irb-dbsel__link:disabled{color:var(--text-subtle);cursor:default;text-decoration:none;}
.irb-dbsel__sel{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);}
.irb-dbsel__list{overflow:auto;padding:var(--space-2);}

.irb-dbsel__grp{margin:2px 0;}
.irb-dbsel__grphead{display:flex;align-items:center;gap:var(--space-2);width:100%;
  padding:var(--space-2) var(--space-2);border:none;background:var(--surface-sunken);border-radius:var(--radius-sm);cursor:default;}
.irb-dbsel__exp{flex:none;display:flex;align-items:center;justify-content:center;width:24px;height:24px;border:none;background:none;
  cursor:pointer;color:var(--text-muted);border-radius:var(--radius-xs);}
.irb-dbsel__exp:hover{background:var(--surface-hover);}
.irb-dbsel__exp svg{transition:transform var(--dur) var(--ease-standard);}
.irb-dbsel__exp--open svg{transform:rotate(90deg);}
.irb-dbsel__grpname{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);}
.irb-dbsel__grpcount{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);}
.irb-dbsel__children{padding:2px 0 4px 28px;}

.irb-dbsel__row{
  display:flex;align-items:center;gap:var(--space-3);width:100%;
  padding:var(--space-2) var(--space-2);border:none;background:transparent;border-radius:var(--radius-sm);
  cursor:pointer;text-align:left;color:var(--text-body);
}
.irb-dbsel__row:hover{background:var(--surface-hover);}
.irb-dbsel__row .irb-check{pointer-events:none;}
.irb-dbsel__oicon{flex:none;width:30px;height:30px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;
  background:var(--surface-sunken);color:var(--text-muted);}
.irb-dbsel__row--on .irb-dbsel__oicon{background:var(--accent-weak);color:var(--accent);}
.irb-dbsel__oname{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-dbsel__odesc{font-size:var(--text-xs);color:var(--text-muted);}
.irb-dbsel__ocount{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-dbsel__stub{margin-left:6px;font-size:var(--text-2xs);color:var(--text-subtle);border:1px solid var(--border-subtle);border-radius:var(--radius-pill);padding:0 6px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-dbsel-css")) {
  const s = document.createElement("style");
  s.id = "irb-dbsel-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const fmt = (n) => (typeof n === "number" ? n.toLocaleString("ru-RU") : n);

export function DatabaseSelector({
  databases = [],
  groups = {},
  value = [],
  onChange,
  title = "Электронный каталог и Базы данных",
  className = "",
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  const selected = new Set(value);

  // Порядок отображения: группы и одиночные базы в порядке появления.
  const order = [];
  const seen = new Set();
  databases.forEach((d) => {
    if (d.group) {
      if (!seen.has(d.group)) { seen.add(d.group); order.push({ type: "group", id: d.group }); }
    } else {
      order.push({ type: "db", db: d });
    }
  });
  const childrenOf = (gid) => databases.filter((d) => d.group === gid);

  const [expanded, setExpanded] = React.useState(() => {
    const m = {}; Object.keys(groups).forEach((g) => (m[g] = true)); return m;
  });

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const emit = (ids) => onChange && onChange(ids);
  const toggle = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    emit(databases.filter((d) => next.has(d.id)).map((d) => d.id));
  };
  const allIds = databases.map((d) => d.id);
  const selectAll = () => emit(allIds.slice());
  const clearAll = () => emit([]);
  const toggleGroup = (gid) => {
    const kids = childrenOf(gid).map((d) => d.id);
    const allOn = kids.every((id) => selected.has(id));
    const next = new Set(selected);
    kids.forEach((id) => (allOn ? next.delete(id) : next.add(id)));
    emit(databases.filter((d) => next.has(d.id)).map((d) => d.id));
  };

  const count = selected.size;
  const summary =
    count === 0 ? "Базы не выбраны"
      : count === 1 ? (databases.find((d) => selected.has(d.id)) || {}).name
        : `Выбрано баз: ${count}`;

  const Row = (d) => {
    const on = selected.has(d.id);
    return (
      <button
        key={d.id} type="button" role="option" aria-selected={on}
        className={`irb-dbsel__row${on ? " irb-dbsel__row--on" : ""}`}
        onClick={() => toggle(d.id)}
      >
        <Checkbox checked={on} readOnly tabIndex={-1} />
        <span className="irb-dbsel__oicon"><Icon name={d.icon || "layers"} size={17} /></span>
        <span style={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
          <span className="irb-dbsel__oname">{d.name}{d.stub && <span className="irb-dbsel__stub">демо-заглушка</span>}</span>
          {d.description && <span className="irb-dbsel__odesc">{d.description}</span>}
        </span>
        {d.count != null && <span className="irb-dbsel__ocount">{fmt(d.count)}</span>}
      </button>
    );
  };

  return (
    <div className={`irb-dbsel${open ? " irb-dbsel--open" : ""} ${className}`} ref={ref}>
      <button type="button" className="irb-dbsel__btn" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <span className="irb-dbsel__mark"><Icon name="layers" size={22} /></span>
        <span className="irb-dbsel__txt">
          <span className="irb-dbsel__eyebrow">Базы поиска</span>
          <span className={`irb-dbsel__name${count === 0 ? " irb-dbsel__name--empty" : ""}`}>{summary}</span>
        </span>
        {count > 1 && <span className="irb-dbsel__count">{count}</span>}
        <Icon name="chevron-down" size={20} className="irb-dbsel__chev" />
      </button>

      {open && (
        <div className="irb-dbsel__menu" role="dialog" aria-label={title}>
          <div className="irb-dbsel__head">
            <div className="irb-dbsel__title">{title}</div>
            <div className="irb-dbsel__tools">
              <button type="button" className="irb-dbsel__link" onClick={selectAll} disabled={count === allIds.length}>Выбрать все</button>
              <button type="button" className="irb-dbsel__link" onClick={clearAll} disabled={count === 0}>Снять всё</button>
              <span className="irb-dbsel__sel">{count > 0 ? `выбрано: ${count}` : "ничего не выбрано"}</span>
            </div>
          </div>
          <div className="irb-dbsel__list">
            {order.map((node) => {
              if (node.type === "db") return Row(node.db);
              const g = groups[node.id] || { label: node.id };
              const kids = childrenOf(node.id);
              const on = kids.filter((d) => selected.has(d.id)).length;
              const isOpen = expanded[node.id];
              return (
                <div className="irb-dbsel__grp" key={node.id}>
                  <div className="irb-dbsel__grphead">
                    <button type="button" className={`irb-dbsel__exp${isOpen ? " irb-dbsel__exp--open" : ""}`}
                      aria-label={isOpen ? "Свернуть группу" : "Раскрыть группу"} aria-expanded={isOpen}
                      onClick={() => setExpanded((m) => ({ ...m, [node.id]: !m[node.id] }))}>
                      <Icon name="chevron-right" size={16} />
                    </button>
                    <span onClick={() => toggleGroup(node.id)} style={{ cursor: "pointer", display: "inline-flex" }}>
                      <Checkbox checked={on === kids.length && kids.length > 0} indeterminate={on > 0 && on < kids.length} readOnly tabIndex={-1} />
                    </span>
                    <Icon name={g.icon || "layers"} size={16} style={{ color: "var(--text-muted)" }} />
                    <span className="irb-dbsel__grpname" onClick={() => toggleGroup(node.id)} style={{ cursor: "pointer" }}>{g.label}</span>
                    <span className="irb-dbsel__grpcount">{on > 0 ? `${on} из ${kids.length}` : `${kids.length}`}</span>
                  </div>
                  {isOpen && <div className="irb-dbsel__children">{kids.map(Row)}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
