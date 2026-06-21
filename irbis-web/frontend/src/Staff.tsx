import React from "react";
import { api } from "./api";
import type { Grant } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { DynamicField } from "../components/cataloging/DynamicField.jsx";

export interface StaffSession { name?: string; login: string; grants: Grant[]; }
type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Функциональные модули продукта «Рабочее пространство сотрудника».
// Собираются ПО ГРАНТАМ учётки (а не «по АРМам»): видны только разрешённые.
type DomainTile = { id: string; label: string; icon: IconName; grant: string; desc: string; route: "cataloging" | "cells" | "stub" };
const DOMAINS: DomainTile[] = [
  { id: "cataloging", label: "Каталогизация", icon: "book", grant: "record.write", desc: "Создание и правка библиографических записей RUSMARC", route: "cataloging" as const },
  { id: "acq", label: "Комплектование", icon: "archive", grant: "acq.receipt", desc: "Заказ, поступление, КСУ, списание", route: "stub" as const },
  { id: "circ", label: "Книговыдача", icon: "package", grant: "circ.issue", desc: "Выдача, возврат, очередь, бронеполка, ячейки", route: "stub" as const },
  { id: "cells", label: "Ячеистое хранение", icon: "grid", grant: "record.read", desc: "Карта ячеек: занятость, адрес, RFID (наша фишка)", route: "cells" as const },
  { id: "provision", label: "Книгообеспеченность", icon: "bar-chart", grant: "record.read", desc: "Обеспеченность дисциплин учебной литературой", route: "stub" as const },
  { id: "inv", label: "Инвентаризация", icon: "scan-line", grant: "record.read", desc: "Сверка фонда с ТСД", route: "stub" as const },
  { id: "admin", label: "Администрирование", icon: "sliders", grant: "admin.users", desc: "Учётки, гранты, роли, аудит", route: "stub" as const },
];
const hasGrant = (grants: Grant[], fn: string) => (grants || []).some((g) => g.function === fn);

type WLField = { code: string; label: string; type: string; required?: boolean; repeatable?: boolean; subfields?: { code: string; label: string; type: string }[]; options?: string[] };

function emptyValues(wl: WLField[]) {
  const v: Record<string, any> = {};
  (wl || []).forEach((fd) => { v[fd.code] = fd.repeatable ? [] : (fd.subfields ? {} : ""); });
  return v;
}
function valuesToFields(wl: WLField[], values: Record<string, any>) {
  const out: { tag: string; value: string }[] = [];
  (wl || []).forEach((fd) => {
    const v = values[fd.code];
    const occs = fd.repeatable ? (Array.isArray(v) ? v : []) : [v];
    occs.forEach((occ: any) => {
      let str = "";
      if (fd.subfields) { if (occ && typeof occ === "object") str = fd.subfields.map((sf) => { const t = (occ[sf.code] || "").trim(); return t ? "^" + sf.code + t : ""; }).join(""); }
      else str = (occ || "").toString().trim();
      if (str) out.push({ tag: fd.code, value: str });
    });
  });
  return out;
}
function recordToValues(fields: any[], wl: WLField[]) {
  const values: Record<string, any> = {};
  const pick = (f: any, c: string) => f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "";
  (wl || []).forEach((fd) => {
    const matches = fields.filter((f) => f.tag === fd.code);
    if (fd.subfields) {
      const toObj = (f: any) => { const o: Record<string, string> = {}; fd.subfields!.forEach((sf) => { o[sf.code] = pick(f, sf.code); }); return o; };
      values[fd.code] = fd.repeatable ? matches.map(toObj) : (matches[0] ? toObj(matches[0]) : {});
    } else { const f = matches[0]; values[fd.code] = f ? (f.text || f.value || "") : ""; }
  });
  return values;
}

// ============================================================================
// Стиль A — плотная (dense) AppShell рабочего пространства сотрудника:
//   sidebar (модули по грантам) + topbar (хлебные крошки · плотность · онлайн).
// Плотность через --row-py / --cell-fs на корне shell (как в макете «03»).
// Рендерится внутри читательского <main> — не трогаем App.tsx разметку.
// ============================================================================

const SHELL_CSS = `
.stf{display:grid;grid-template-columns:208px 1fr;gap:0;min-height:560px;
  background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;
  box-shadow:var(--shadow-sm);font-family:var(--font-ui);}
.stf--compact{--row-py:8px;--cell-fs:13px;}
.stf--comfortable{--row-py:13px;--cell-fs:14px;}
.stf__side{background:var(--surface-sunken);border-right:1px solid var(--border-subtle);display:flex;flex-direction:column;min-width:0;}
.stf__brand{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--border-subtle);}
.stf__brand-badge{width:30px;height:30px;border-radius:var(--radius-md);background:var(--accent);color:var(--accent-fg);
  display:flex;align-items:center;justify-content:center;flex:none;}
.stf__brand-name{font-family:var(--font-display);font-weight:600;font-size:15px;line-height:1.1;}
.stf__brand-sub{font-size:10.5px;color:var(--text-subtle);line-height:1.2;}
.stf__nav{padding:10px 10px;display:flex;flex-direction:column;gap:2px;flex:1;}
.stf__nav-cap{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--text-subtle);padding:8px 8px 4px;}
.stf__nav-item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:none;cursor:pointer;
  padding:8px 9px;border-radius:var(--radius-md);font-family:var(--font-ui);font-size:13px;font-weight:500;
  color:var(--text-muted);background:transparent;transition:background-color .12s,color .12s;}
.stf__nav-item:hover{background:var(--surface-hover);color:var(--text-body);}
.stf__nav-item--on{background:var(--accent-weak);color:var(--accent-press);font-weight:600;}
.stf__nav-item .stf__nav-ic{flex:none;display:flex;color:inherit;opacity:.9;}
.stf__nav-item--on .stf__nav-ic{color:var(--accent);opacity:1;}
.stf__user{display:flex;align-items:center;gap:10px;padding:11px 14px;border-top:1px solid var(--border-subtle);}
.stf__user-av{width:30px;height:30px;border-radius:var(--radius-full);background:var(--accent);color:var(--accent-fg);
  display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex:none;}
.stf__user-name{font-size:12px;font-weight:600;line-height:1.2;}
.stf__user-role{font-size:10.5px;color:var(--text-subtle);}
.stf__main{display:flex;flex-direction:column;min-width:0;}
.stf__top{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:14px;
  padding:9px 18px;background:var(--surface-card);border-bottom:1px solid var(--border-subtle);}
.stf__crumb{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--text-subtle);min-width:0;}
.stf__crumb b{color:var(--text-body);font-weight:600;}
.stf__density{margin-left:auto;display:flex;gap:3px;padding:3px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);}
.stf__density button{border:none;cursor:pointer;font-family:var(--font-ui);font-size:11.5px;font-weight:500;padding:4px 10px;border-radius:var(--radius-sm);background:transparent;color:var(--text-muted);}
.stf__density button[aria-pressed="true"]{background:var(--text-primary);color:var(--surface-1);}
.stf__online{display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:var(--radius-md);
  background:var(--status-available-bg);color:var(--status-available);font-size:11px;font-weight:600;white-space:nowrap;}
.stf__online .dot{width:6px;height:6px;border-radius:var(--radius-full);background:var(--status-available);}
.stf__body{flex:1;padding:18px 22px 28px;min-width:0;}
.stf__pagehead{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px;flex-wrap:wrap;}
.stf__h1{display:flex;align-items:center;gap:11px;}
.stf__h1 h2{font-family:var(--font-display);font-weight:600;font-size:21px;letter-spacing:-.02em;margin:0;}
.stf__pill{padding:3px 10px;border-radius:var(--radius-md);background:var(--surface-sunken);border:1px solid var(--border-subtle);
  font-size:11px;font-weight:600;color:var(--text-muted);}
.stf__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);}
.stf__card-cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}

/* worksheet — labelled field rows (макет «03 каталогизация») */
.stf__row{display:grid;grid-template-columns:184px 1fr;gap:16px;align-items:start;
  padding:var(--row-py) 0;border-bottom:1px solid var(--border-subtle);}
.stf__row:last-child{border-bottom:none;}
.stf__row-lab{display:flex;align-items:center;gap:8px;padding-top:6px;min-width:0;}
.stf__row-code{font-family:var(--font-mono);font-size:11px;font-weight:600;padding:2px 6px;border-radius:var(--radius-sm);
  background:var(--surface-hover);color:var(--text-muted);flex:none;}
.stf__row-name{font-size:13px;font-weight:600;color:var(--text-strong);}
.stf__row-req{color:var(--danger-500);margin-left:1px;}
/* Левая колонка строки уже даёт код+метку — прячем дублирующий заголовок DynamicField,
   оставляя контрол, подсказку и ФЛК-сообщение. */
.stf__row .irb-dyn__head{display:none;}
.stf__row .irb-dyn{gap:6px;}

@media (max-width:880px){
  .stf__cat-grid{grid-template-columns:1fr !important;}
}
@media (max-width:780px){
  .stf{grid-template-columns:1fr;}
  .stf__side{flex-direction:row;flex-wrap:wrap;border-right:none;border-bottom:1px solid var(--border-subtle);}
  .stf__nav{flex-direction:row;flex-wrap:wrap;flex:1 1 100%;}
  .stf__nav-cap,.stf__user{display:none;}
  .stf__row{grid-template-columns:1fr;gap:6px;}
}
`;
if (typeof document !== "undefined" && !document.getElementById("stf-shell-css")) {
  const s = document.createElement("style"); s.id = "stf-shell-css"; s.textContent = SHELL_CSS; document.head.appendChild(s);
}

function initials(name?: string, login?: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  if (parts.length === 1 && parts[0].length >= 2) return parts[0].slice(0, 2).toUpperCase();
  return (login || "СТ").slice(0, 2).toUpperCase();
}

// Текущий модуль по маршруту (для подсветки nav + хлебных крошек).
function routeId(route: any): string {
  if (route === "cataloging") return "cataloging";
  if (route === "cells") return "cells";
  if (route === "desktop" || !route) return "desktop";
  return "stub";
}

export function StaffArea({ staff, route, setRoute, toast }: { staff: StaffSession; route: any; setRoute: (r: any) => void; toast: ToastFn }) {
  const [density, setDensity] = React.useState<"compact" | "comfortable">("compact");
  const tiles = DOMAINS.filter((d) => hasGrant(staff.grants, d.grant));
  const current = routeId(route);
  const stubTitle = route && route.name === "stub" ? route.title : "";
  const open = (d: typeof DOMAINS[number]) => setRoute(d.route === "stub" ? { name: "stub", title: d.label } : d.route);

  const crumbLeaf =
    current === "cataloging" ? "Каталогизация" :
    current === "cells" ? "Ячеистое хранение" :
    current === "stub" ? stubTitle :
    "Рабочий стол";

  return (
    <div className={"stf stf--" + density} role="application" aria-label="Рабочее пространство сотрудника">
      {/* ===== Sidebar: модули по грантам ===== */}
      <nav className="stf__side" aria-label="Модули рабочего пространства">
        <div className="stf__brand">
          <span className="stf__brand-badge" aria-hidden="true"><Icon name="book" size={17} /></span>
          <div style={{ minWidth: 0 }}>
            <div className="stf__brand-name">Biblio</div>
            <div className="stf__brand-sub">Рабочее пространство</div>
          </div>
        </div>
        <div className="stf__nav">
          <span className="stf__nav-cap">Рабочее место</span>
          <button type="button" className={"stf__nav-item" + (current === "desktop" ? " stf__nav-item--on" : "")}
            aria-current={current === "desktop" ? "page" : undefined} onClick={() => setRoute("desktop")}>
            <span className="stf__nav-ic"><Icon name="panel-left" size={17} /></span>Рабочий стол
          </button>
          {tiles.map((d) => (
            <button key={d.id} type="button"
              className={"stf__nav-item" + (current !== "desktop" && crumbLeaf === d.label ? " stf__nav-item--on" : "")}
              aria-current={current !== "desktop" && crumbLeaf === d.label ? "page" : undefined}
              onClick={() => open(d)}>
              <span className="stf__nav-ic"><Icon name={d.icon} size={17} /></span>{d.label}
            </button>
          ))}
        </div>
        <div className="stf__user">
          <span className="stf__user-av" aria-hidden="true">{initials(staff.name, staff.login)}</span>
          <div style={{ minWidth: 0 }}>
            <div className="stf__user-name">{staff.name || staff.login}</div>
            <div className="stf__user-role">{staff.grants.length} грант(ов)</div>
          </div>
        </div>
      </nav>

      {/* ===== Main: topbar + routed content ===== */}
      <div className="stf__main">
        <header className="stf__top">
          <div className="stf__crumb">
            <span>Рабочее пространство</span>
            <Icon name="chevron-right" size={13} />
            <b>{crumbLeaf}</b>
          </div>
          <div className="stf__density" role="group" aria-label="Плотность интерфейса">
            <button type="button" aria-pressed={density === "comfortable"} onClick={() => setDensity("comfortable")}>Просторно</button>
            <button type="button" aria-pressed={density === "compact"} onClick={() => setDensity("compact")}>Плотно</button>
          </div>
          <span className="stf__online"><span className="dot" />Онлайн</span>
        </header>

        <div className="stf__body">
          {current === "cataloging" ? <CatalogingWorksheet staff={staff} toast={toast} />
            : current === "cells" ? <CellMap />
            : current === "stub" ? <StaffStub title={stubTitle} onOpen={() => setRoute("cataloging")} />
            : <StaffDesktop staff={staff} tiles={tiles} onOpen={open} />}
        </div>
      </div>
    </div>
  );
}

function StaffDesktop({ staff, tiles, onOpen }: { staff: StaffSession; tiles: typeof DOMAINS; onOpen: (d: typeof DOMAINS[number]) => void }) {
  return (
    <div>
      <div className="stf__pagehead">
        <div className="stf__h1">
          <h2>Рабочее пространство сотрудника</h2>
          <span className="stf__pill">{tiles.length} модул{tiles.length === 1 ? "ь" : "я/ей"}</span>
        </div>
      </div>
      <p style={{ color: "var(--text-subtle)", fontSize: 13, marginTop: 0, marginBottom: 16 }}>
        {staff.name || staff.login} · модули собраны <b>по грантам учётки</b>, а не «по АРМам». Видны только разрешённые функции.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(248px,1fr))", gap: 12 }}>
        {tiles.map((d) => (
          <button key={d.id} type="button" onClick={() => onOpen(d)}
            style={{ textAlign: "left", cursor: "pointer", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", padding: 15, display: "flex", gap: 12, alignItems: "flex-start", font: "inherit", color: "inherit", transition: "border-color .12s, background-color .12s" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--accent-weak-border)"; e.currentTarget.style.background = "var(--surface-sunken)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border-subtle)"; e.currentTarget.style.background = "var(--surface-card)"; }}>
            <span style={{ background: "var(--accent-weak)", color: "var(--accent)", borderRadius: "var(--radius-md)", padding: 8, flex: "none", display: "inline-flex" }}><Icon name={d.icon} size={20} /></span>
            <span style={{ minWidth: 0 }}>
              <span style={{ display: "block", fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{d.label}</span>
              <span style={{ display: "block", color: "var(--text-subtle)", fontSize: 12.5, lineHeight: 1.45 }}>{d.desc}</span>
            </span>
          </button>
        ))}
      </div>
      <div style={{ marginTop: 16, fontSize: 11.5, color: "var(--text-subtle)", lineHeight: 1.6 }}>
        Запись/удаление — под грантами уровня write/admin; действия пишутся в аудит.
      </div>
    </div>
  );
}

function StaffStub({ title, onOpen }: { title: string; onOpen: () => void }) {
  return (
    <div>
      <div className="stf__pagehead">
        <div className="stf__h1"><h2>{title}</h2><span className="stf__pill">в разработке</span></div>
      </div>
      <EmptyState icon="clock" title={title} description="Экран спроектирован в дизайн-системе Biblio (Стиль A). На живые данные подключается следующим шагом — сейчас доступна каталогизация." />
      <div style={{ marginTop: 14 }}><Button iconLeft="book" onClick={onOpen}>Перейти к каталогизации</Button></div>
    </div>
  );
}

// ============================================================================
// Ячеистое хранение — план помещения (RoomPlan SVG) + сетка ячеек/постамата.
// Данные приходят с собственного сервера; на адаптере ИРБИС (:8080) — 404 →
// аккуратный пустой плейсхолдер (наша модель хранения, в ИРБИС её нет).
// ============================================================================

const KIND_RU: Record<string, string> = { building: "Здание", floor: "Этаж", room: "Помещение", rack: "Стеллаж", shelf: "Полка", postamat: "Постамат выдачи", return: "Станция книгоприёма" };
// Цвет ячейки = домен-статус из токенов Стиля A.
const cellColor = (c: any) => !c.occupied ? "var(--surface-hover)"
  : ({ available: "var(--status-available)", hold: "var(--status-postamat)", returned: "var(--status-return)", issued: "var(--status-issued)" } as any)[c.status] || "var(--text-subtle)";

function rackFill(r: any) {
  const t = r.cellsTotal || 0, o = r.cellsOccupied || 0, ratio = t ? o / t : 0;
  return !t ? "var(--surface-hover)" : ratio >= 0.85 ? "var(--status-issued)" : ratio >= 0.5 ? "var(--warning)" : ratio > 0 ? "var(--status-available)" : "var(--surface-hover)";
}

function CellGrid({ cells }: { cells: any[] }) {
  return <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
    {cells.map((c, j) => <span key={j} title={c.occupied ? ((c.title || "") + " · " + c.inv) : "свободно"} style={{ fontFamily: "var(--font-mono)", fontSize: 11, padding: "3px 7px", borderRadius: "var(--radius-sm)", color: c.occupied ? "#fff" : "var(--text-subtle)", border: c.occupied ? "none" : "1px solid var(--border-subtle)", background: cellColor(c), cursor: "default" }}>{c.code}</span>)}
  </div>;
}

function RoomPlan({ room, onPick, selId }: { room: any; onPick: (r: any) => void; selId: number | null }) {
  const racks = (room.children || []).filter((c: any) => c.kind === "rack");
  const W = room.gw || 300, H = room.gh || 160;
  return (
    <div style={{ overflowX: "auto", margin: "4px 0 8px" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={Math.min(W, 720)} style={{ maxWidth: "100%", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", background: "var(--surface-sunken)" }}>
        <rect x={0} y={H - 13} width={W} height={13} fill="var(--surface-hover)" />
        <text x={6} y={H - 3.5} fontSize={8} fill="var(--text-subtle)">вход</text>
        {racks.map((r: any, i: number) => (
          <g key={i} onClick={() => onPick(r)} style={{ cursor: "pointer" }}>
            <rect x={r.gx} y={r.gy} width={r.gw} height={r.gh} rx={4} fill={rackFill(r)} stroke={selId === r.id ? "var(--text-primary)" : "var(--border-strong)"} strokeWidth={selId === r.id ? 2 : 1} />
            <text x={r.gx + r.gw / 2} y={r.gy + r.gh / 2 + 3.5} fontSize={11} fontWeight={700} fill="#fff" textAnchor="middle" pointerEvents="none">{r.code}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function RoomView({ room }: { room: any }) {
  const [sel, setSel] = React.useState<any>(null);
  return (
    <div style={{ marginLeft: 16 }}>
      <div style={{ fontSize: 11, color: "var(--text-subtle)", margin: "2px 0 4px" }}>План помещения · {(room.children || []).filter((c: any) => c.kind === "rack").length} стеллажей · цвет = заполненность</div>
      <RoomPlan room={room} onPick={setSel} selId={sel ? sel.id : null} />
      {sel ? (
        <div style={{ margin: "2px 0 8px" }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Стеллаж {sel.code} · занято {sel.cellsOccupied}/{sel.cellsTotal}</div>
          {(sel.children || []).map((sh: any, i: number) => (
            <div key={i} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 11, color: "var(--text-subtle)", marginBottom: 2 }}>Полка {sh.code}</div>
              <CellGrid cells={sh.children || []} />
            </div>
          ))}
        </div>
      ) : <div style={{ fontSize: 11, color: "var(--text-subtle)", marginBottom: 8 }}>Кликните стеллаж на плане — покажутся его полки и ячейки.</div>}
    </div>
  );
}

function StorageNode({ node, depth }: { node: any; depth: number }) {
  const [open, setOpen] = React.useState(depth < 2);
  const kids: any[] = node.children || [];
  const leaves = kids.filter((k) => k.kind === "cell" || k.kind === "slot");
  const conts = kids.filter((k) => k.kind !== "cell" && k.kind !== "slot");
  const head = (KIND_RU[node.kind] || node.kind) + " " + node.code + (node.name ? " · " + node.name : "") + (node.address ? " · " + node.address : "");
  const occ = node.cellsTotal ? node.cellsOccupied + "/" + node.cellsTotal : (leaves.length ? leaves.filter((c) => c.occupied).length + "/" + leaves.length : "");
  return (
    <div style={{ marginLeft: depth ? 14 : 0, borderLeft: depth ? "1px solid var(--border-subtle)" : "none", paddingLeft: depth ? 8 : 0 }}>
      <div onClick={() => setOpen((o) => !o)} style={{ cursor: "pointer", fontWeight: depth < 3 ? 600 : 500, fontSize: depth < 2 ? 14 : 13, display: "flex", gap: 6, alignItems: "center", margin: "5px 0" }}>
        <span style={{ color: "var(--text-subtle)", width: 10 }}>{kids.length ? (open ? "▾" : "▸") : "·"}</span>
        <span>{head}</span>
        {occ && <span style={{ color: "var(--text-subtle)", fontSize: 11, fontWeight: 400 }}>· занято {occ}</span>}
      </div>
      {open && (node.kind === "room" ? <RoomView room={node} /> : <>
        {leaves.length > 0 && <div style={{ margin: "2px 0 8px 16px" }}><CellGrid cells={leaves} /></div>}
        {conts.map((k, i) => <StorageNode key={i} node={k} depth={depth + 1} />)}
      </>)}
    </div>
  );
}

function CellMap() {
  const [data, setData] = React.useState<any>(null);
  const [err, setErr] = React.useState(false);
  React.useEffect(() => { (async () => { const r = await api.storage("IBIS"); if (r.json && r.json.ok && r.json.data) setData(r.json.data); else setErr(true); })(); }, []);

  const legend: [string, string][] = [
    ["В ячейке", "var(--status-available)"],
    ["В постамате", "var(--status-postamat)"],
    ["Книгоприём", "var(--status-return)"],
    ["Свободно", "var(--surface-hover)"],
  ];

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Ячеистое хранение</h2>
        <span className="stf__pill">наша модель · RFID</span>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 11.5, color: "var(--text-muted)" }}>
        {legend.map(([l, c], i) => <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><span style={{ display: "inline-block", width: 11, height: 11, borderRadius: 3, background: c, border: c === "var(--surface-hover)" ? "1px solid var(--border-strong)" : "none" }} />{l}</span>)}
      </div>
    </div>
  );

  // На адаптере ИРБИС (:8080) /api/storage → 404: аккуратный пустой плейсхолдер.
  if (err) return (
    <div>
      {head}
      <div className="stf__card" style={{ padding: 4 }}>
        <EmptyState icon="grid" title="Карта хранения подключается с собственного сервера"
          description="Иерархия здание → этаж → помещение → стеллаж → полка → ячейка (+ постамат и книгоприём) — наша модель ячеистого хранения. На адаптере к ИРБИС64 её нет, поэтому здесь данные пусты. Экран свёрстан в Стиле A и наполняется при работе через server-own." />
      </div>
    </div>
  );
  if (!data) return <div>{head}<div style={{ color: "var(--text-subtle)", fontSize: 13 }}>Загрузка карты хранения…</div></div>;
  return (
    <div>
      {head}
      <p style={{ color: "var(--text-subtle)", fontSize: 13, marginTop: 0 }}>Размещено экземпляров: {data.holdings} · здания → этажи → помещения → стеллажи → полки → ячейки + постамат/книгоприём.</p>
      <div className="stf__card" style={{ padding: 16 }}>
        {(data.tree || []).map((n: any, i: number) => <StorageNode key={i} node={n} depth={0} />)}
      </div>
    </div>
  );
}

// ============================================================================
// Каталогизация — рабочий лист RUSMARC: labelled field rows (DynamicField),
// control-by-type, ФЛК-валидация (ошибка поля + сообщение), панель сводки ФЛК.
// Live: загрузка из IBIS, сохранение в песочницу WORK.
// ============================================================================

function CatalogingWorksheet({ staff: _staff, toast }: { staff: StaffSession; toast: ToastFn }) {
  const SANDBOX = "WORK";
  const [wl, setWl] = React.useState<WLField[] | null>(null);
  const [values, setValues] = React.useState<Record<string, any>>({});
  const [mfn, setMfn] = React.useState(0);
  const [openMfn, setOpenMfn] = React.useState("");
  const [saved, setSaved] = React.useState<any>(null);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [checked, setChecked] = React.useState(false);

  React.useEffect(() => { (async () => { const r = await api.worklist(SANDBOX); if (r.json?.ok && r.json.data) { setWl(r.json.data.fields); setValues(emptyValues(r.json.data.fields)); } })(); }, []);

  const set = (code: string, val: any) => { setValues((v) => ({ ...v, [code]: val })); if (errors[code]) setErrors((e) => { const n = { ...e }; delete n[code]; return n; }); };
  const newRecord = () => { setValues(emptyValues(wl!)); setMfn(0); setSaved(null); setErrors({}); setChecked(false); };

  // ФЛК: обязательные поля. Возвращает map ошибок (для подсветки + сводки).
  function runFlk(): Record<string, string> {
    const errs: Record<string, string> = {};
    (wl || []).forEach((fd) => {
      if (fd.required) {
        const ok = fd.subfields ? (values[fd.code] && Object.values(values[fd.code]).some(Boolean)) : !!values[fd.code];
        if (!ok) errs[fd.code] = "ФЛК: обязательное поле не заполнено";
      }
    });
    return errs;
  }
  function checkFlk() {
    const errs = runFlk(); setErrors(errs); setChecked(true);
    if (Object.keys(errs).length) toast({ variant: "warning", title: "ФЛК: есть замечания", message: "Заполните обязательные поля." });
    else toast({ variant: "success", title: "ФЛК пройден", message: "Обязательные поля заполнены." });
  }

  async function loadFromIbis() {
    const id = parseInt(openMfn, 10); if (!id) return;
    const r = await api.record("IBIS", id);
    if (r.json?.ok && r.json.data) { setValues(recordToValues(r.json.data.fields, wl!)); setMfn(0); setSaved(null); setErrors({}); setChecked(false); toast({ variant: "info", title: "Запись загружена в форму", message: "IBIS MFN " + id + " → сохранится в песочницу " + SANDBOX }); }
    else toast({ variant: "warning", title: "Не найдено", message: "Нет записи MFN " + id + " в IBIS." });
  }
  async function save() {
    const errs = runFlk();
    setErrors(errs); setChecked(true);
    if (Object.keys(errs).length) { toast({ variant: "warning", title: "Заполните обязательные поля", message: "ФЛК не пройден." }); return; }
    const r = await api.saveRecord(SANDBOX, mfn, valuesToFields(wl!, values));
    if (r.status === 200 && r.json?.ok && r.json.data) { setSaved(r.json.data); setMfn(r.json.data.mfn); toast({ variant: "success", title: r.json.data.created ? "Запись создана" : "Запись обновлена", message: SANDBOX + " · MFN " + r.json.data.mfn }); }
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант record.write." });
    else toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку." });
  }

  // Сводка ФЛК для правой панели.
  const requiredFields = (wl || []).filter((f) => f.required);
  const errCount = Object.keys(errors).length;

  const inputSx: React.CSSProperties = { width: 132, padding: "7px 11px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-body)", fontFamily: "var(--font-ui)", fontSize: 13 };

  return (
    <div>
      <div className="stf__pagehead">
        <div className="stf__h1">
          <h2>Каталогизация</h2>
          <span className="stf__pill">Книга · RUSMARC</span>
          <span className="stf__pill" style={{ background: "var(--status-issued-bg)", color: "var(--status-issued)", borderColor: "transparent" }}>{mfn ? "MFN " + mfn : "Черновик"}</span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Button variant="secondary" size="sm" iconLeft="check-circle" onClick={checkFlk} disabled={!wl}>Проверить ФЛК</Button>
          <Button size="sm" iconLeft="check-circle" onClick={save} disabled={!wl}>Сохранить</Button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "0 0 14px", flexWrap: "wrap" }}>
        <Button variant="secondary" size="sm" iconLeft="plus" onClick={newRecord} disabled={!wl}>Новая запись</Button>
        <span style={{ color: "var(--text-subtle)" }}>·</span>
        <input value={openMfn} onChange={(e) => setOpenMfn(e.target.value)} placeholder="MFN из IBIS" aria-label="MFN записи в базе IBIS" style={inputSx} onKeyDown={(e) => { if (e.key === "Enter") loadFromIbis(); }} />
        <Button variant="secondary" size="sm" onClick={loadFromIbis} disabled={!wl}>Загрузить из IBIS</Button>
        <span style={{ marginLeft: "auto", color: "var(--text-subtle)", fontSize: 12.5 }}>песочница {SANDBOX} · рабочий лист «Книга»</span>
      </div>

      {!wl ? <div style={{ color: "var(--text-subtle)", fontSize: 13 }}>Загрузка рабочего листа…</div> : (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 280px", gap: 18, alignItems: "start" }} className="stf__cat-grid">
          {/* worksheet — labelled field rows */}
          <div className="stf__card" style={{ padding: "4px 20px" }}>
            {wl.map((fd) => (
              <div className="stf__row" key={fd.code}>
                <div className="stf__row-lab">
                  <span className="stf__row-code">{fd.code}</span>
                  <span className="stf__row-name">{fd.label}{fd.required && <span className="stf__row-req" aria-hidden="true">*</span>}</span>
                </div>
                <DynamicField field={{ ...fd, code: undefined } as any} value={values[fd.code]} onChange={(v: any) => set(fd.code, v)} error={errors[fd.code]} />
              </div>
            ))}
            <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "14px 0" }}>
              <Button iconLeft="check-circle" onClick={save}>Сохранить запись</Button>
              {saved && <span style={{ color: "var(--success)", fontSize: 13 }}><Icon name="check" size={13} /> сохранено в {saved.db}, MFN {saved.mfn} (код {saved.returnCode})</span>}
            </div>
          </div>

          {/* ФЛК сводка */}
          <aside className="stf__card" style={{ padding: 16, position: "sticky", top: 64 }} aria-label="Сводка проверки ФЛК">
            <span className="stf__card-cap">Проверка ФЛК</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 12 }}>
              {requiredFields.map((fd) => {
                const bad = !!errors[fd.code];
                return (
                  <div key={fd.code} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: bad ? "var(--danger-500)" : "var(--text-body)" }}>
                    <Icon name={bad ? "alert-octagon" : "check-circle"} size={15} style={{ color: bad ? "var(--danger-500)" : "var(--success)", flex: "none" }} />
                    <span>{fd.label} {bad ? "— не заполнено" : "— заполнено"}</span>
                  </div>
                );
              })}
              {!requiredFields.length && <div style={{ fontSize: 12.5, color: "var(--text-subtle)" }}>Обязательных полей нет.</div>}
            </div>
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border-subtle)", fontSize: 12, color: checked ? (errCount ? "var(--danger-500)" : "var(--success)") : "var(--text-subtle)" }}>
              {!checked ? "Нажмите «Проверить ФЛК» перед сохранением." : errCount ? errCount + " замечани(е/я) ФЛК" : "ФЛК пройден — можно сохранять."}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

export function StaffLoginOverlay({ onClose, onSubmit }: { onClose: () => void; onSubmit: (l: string, p: string) => void }) {
  const [l, setL] = React.useState("");
  const [p, setP] = React.useState("");
  const inp: React.CSSProperties = { width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)", marginBottom: 10, background: "var(--surface-card)", color: "var(--text-body)", fontFamily: "var(--font-ui)" };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} role="dialog" aria-modal="true" aria-label="Вход сотрудника">
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--surface-card)", color: "var(--text-body)", borderRadius: "var(--radius-xl)", padding: 22, width: 340, boxShadow: "var(--shadow-lg)" }}>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 18, marginBottom: 8 }}>Вход сотрудника</div>
        <p style={{ margin: "0 0 12px", color: "var(--text-subtle)", fontSize: 13 }}>Доступ определяется грантами учётной записи.</p>
        <input value={l} onChange={(e) => setL(e.target.value)} placeholder="Логин" aria-label="Логин" style={inp} />
        <input value={p} onChange={(e) => setP(e.target.value)} type="password" placeholder="Пароль" aria-label="Пароль" onKeyDown={(e) => { if (e.key === "Enter") onSubmit(l, p); }} style={inp} />
        <div style={{ fontSize: 11.5, color: "var(--text-subtle)", marginBottom: 12 }}>демо: <b>admin / admin</b> · <b>librarian / librarian</b></div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={() => onSubmit(l, p)}>Войти</Button>
        </div>
      </div>
    </div>
  );
}
