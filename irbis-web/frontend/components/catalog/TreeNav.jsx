import React from "react";
import { Icon } from "../icon/Icon.jsx";

/* TreeNav (§4, §10) — навигатор-классификатор (ГРНТИ/УДК/ББК): раскрываемое
   дерево рубрик с количеством записей; выбор узла фильтрует выдачу. Ленивая
   подача: показываем счётчик у каждого узла. */

const CSS = `
.irb-tnav{font-family:var(--font-ui);border:1px solid var(--border-subtle);border-radius:var(--radius-md);
  background:var(--surface-card);overflow:hidden;}
.irb-tnav__tabs{display:flex;border-bottom:1px solid var(--border-subtle);}
.irb-tnav__tab{flex:1;border:none;background:var(--surface-sunken);cursor:pointer;padding:7px 4px;
  font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);color:var(--text-muted);}
.irb-tnav__tab--on{background:var(--surface-card);color:var(--accent-press);box-shadow:inset 0 -2px 0 var(--accent);}
.irb-tnav__body{max-height:280px;overflow:auto;padding:4px;}
.irb-tnav__row{display:flex;align-items:center;gap:2px;border-radius:var(--radius-sm);}
.irb-tnav__row:hover{background:var(--surface-hover);}
.irb-tnav__tw{flex:none;width:20px;height:26px;display:flex;align-items:center;justify-content:center;border:none;background:none;cursor:pointer;color:var(--text-subtle);}
.irb-tnav__tw svg{transition:transform var(--dur) var(--ease-standard);}
.irb-tnav__tw--open svg{transform:rotate(90deg);}
.irb-tnav__pick{flex:1;min-width:0;display:flex;align-items:center;gap:8px;text-align:left;border:none;background:none;cursor:pointer;
  padding:5px 4px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-tnav__pick--on{color:var(--accent-press);font-weight:var(--weight-semibold);}
.irb-tnav__pick code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--text-subtle);flex:none;}
.irb-tnav__pick span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-tnav__cnt{margin-left:auto;flex:none;font-size:var(--text-2xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;
  background:var(--surface-sunken);border-radius:var(--radius-pill);padding:1px 7px;}
.irb-tnav__pick--on + .irb-tnav__cnt,.irb-tnav__row:hover .irb-tnav__cnt{color:var(--text-muted);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-tnav-css")) {
  const s = document.createElement("style");
  s.id = "irb-tnav-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

function Node({ node, depth, value, onPick }) {
  const [open, setOpen] = React.useState(depth < 1);
  const has = node.children && node.children.length;
  const on = value === node.code;
  return (
    <div>
      <div className="irb-tnav__row" style={{ paddingLeft: depth * 12 }}>
        {has ? (
          <button type="button" className={"irb-tnav__tw" + (open ? " irb-tnav__tw--open" : "")} onClick={() => setOpen((o) => !o)} aria-label={open ? "Свернуть" : "Развернуть"}>
            <Icon name="chevron-right" size={14} />
          </button>
        ) : <span style={{ width: 20, flex: "none" }} />}
        <button type="button" className={"irb-tnav__pick" + (on ? " irb-tnav__pick--on" : "")} onClick={() => onPick(on ? null : node)} aria-pressed={on}>
          {node.code && <code>{node.code}</code>}
          <span>{node.label}</span>
        </button>
        {node.count != null && <span className="irb-tnav__cnt">{node.count}</span>}
      </div>
      {has && open && node.children.map((c) => <Node key={c.code || c.label} node={c} depth={depth + 1} value={value} onPick={onPick} />)}
    </div>
  );
}

export function TreeNav({ navigators = [], value, onPick, className = "" }) {
  const [active, setActive] = React.useState(navigators[0] ? navigators[0].id : null);
  const cur = navigators.find((n) => n.id === active) || navigators[0];
  if (!cur) return null;
  return (
    <div className={"irb-tnav " + className}>
      {navigators.length > 1 && (
        <div className="irb-tnav__tabs" role="tablist">
          {navigators.map((n) => (
            <button key={n.id} type="button" role="tab" aria-selected={n.id === active}
              className={"irb-tnav__tab" + (n.id === active ? " irb-tnav__tab--on" : "")} onClick={() => setActive(n.id)}>{n.label}</button>
          ))}
        </div>
      )}
      <div className="irb-tnav__body" role="tree">
        {cur.tree.map((n) => <Node key={n.code || n.label} node={n} depth={0} value={value} onPick={onPick} />)}
      </div>
    </div>
  );
}
