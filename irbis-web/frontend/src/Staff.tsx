import React from "react";
import { api } from "./api";
import type { Grant, ResultItem, WorklistField, FlkViolation, FlkRecord } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { DynamicField } from "../components/cataloging/DynamicField.jsx";
import { CirculationDesk } from "./CirculationDesk";
import { AcquisitionDesk } from "./AcquisitionDesk";
import { BookProvisionDesk } from "./BookProvisionDesk";
import { AdminDesk } from "./AdminDesk";

export interface StaffSession { name?: string; login: string; grants: Grant[]; }
type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Функциональные модули продукта «Рабочее пространство сотрудника».
// Собираются ПО ГРАНТАМ учётки (а не «по АРМам»): видны только разрешённые.
type StaffRoute = "cataloging" | "circulation" | "cells" | "acquisition" | "provision" | "admin" | "stub";
type DomainTile = { id: string; label: string; icon: IconName; grant: string; desc: string; route: StaffRoute };
const DOMAINS: DomainTile[] = [
  { id: "cataloging", label: "Каталогизация", icon: "book", grant: "record.write", desc: "Создание и правка библиографических записей RUSMARC", route: "cataloging" as const },
  { id: "acq", label: "Комплектование", icon: "archive", grant: "acq.receipt", desc: "Заказ, поступление, КСУ, списание", route: "acquisition" as const },
  { id: "circ", label: "Книговыдача", icon: "package", grant: "circ.issue", desc: "Выдача, возврат, продление, штрафы, формуляр читателя", route: "circulation" as const },
  { id: "cells", label: "Ячеистое хранение", icon: "grid", grant: "record.read", desc: "Карта ячеек: занятость, адрес, RFID (наша фишка)", route: "cells" as const },
  { id: "provision", label: "Книгообеспеченность", icon: "bar-chart", grant: "record.read", desc: "Обеспеченность дисциплин учебной литературой", route: "provision" as const },
  { id: "inv", label: "Инвентаризация", icon: "scan-line", grant: "record.read", desc: "Сверка фонда с ТСД", route: "stub" as const },
  { id: "admin", label: "Администрирование", icon: "sliders", grant: "admin.users", desc: "Учётки, гранты, роли, аудит", route: "admin" as const },
];
const hasGrant = (grants: Grant[], fn: string) => (grants || []).some((g) => g.function === fn);

type WLField = WorklistField;

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
// values → запись для ФЛК (flk.py): карта поле→значение. Скалярное поле — строка;
// поле с подполями — {подполе:значение}; повторяемое — массив таких. Пустые
// вхождения/подполя отбрасываем, чтобы mandatory-правила не путались.
function valuesToFlkRecord(wl: WLField[], values: Record<string, any>): FlkRecord {
  const rec: FlkRecord = {};
  (wl || []).forEach((fd) => {
    const v = values[fd.code];
    const occToVal = (occ: any): string | Record<string, string> | null => {
      if (fd.subfields) {
        const o: Record<string, string> = {};
        fd.subfields.forEach((sf) => { const t = ((occ || {})[sf.code] || "").toString().trim(); if (t) o[sf.code] = t; });
        return Object.keys(o).length ? o : null;
      }
      const t = (occ ?? "").toString().trim();
      return t ? t : null;
    };
    if (fd.repeatable) {
      const arr = (Array.isArray(v) ? v : []).map(occToVal).filter(Boolean) as Array<string | Record<string, string>>;
      if (arr.length) rec[fd.code] = arr.length === 1 ? arr[0] : arr;
    } else {
      const one = occToVal(v);
      if (one != null) rec[fd.code] = one;
    }
  });
  return rec;
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
.stf__row--bad .stf__row-name{color:var(--danger-500);}

/* search-to-edit — поиск записи в базе и список результатов */
.stf__search{display:grid;grid-template-columns:150px 1fr auto;gap:8px;align-items:center;
  background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:10px 12px;margin-bottom:12px;}
.stf__results{border:1px solid var(--border-subtle);border-radius:var(--radius-md);overflow:hidden;margin-bottom:14px;max-height:260px;overflow-y:auto;}
.stf__res{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:none;cursor:pointer;background:var(--surface-card);
  padding:9px 12px;border-bottom:1px solid var(--border-subtle);font-family:var(--font-ui);color:var(--text-body);}
.stf__res:last-child{border-bottom:none;}
.stf__res:hover{background:var(--surface-hover);}
.stf__res-mfn{font-family:var(--font-mono);font-size:11px;color:var(--text-subtle);flex:none;min-width:46px;}
.stf__res-main{min-width:0;flex:1;}
.stf__res-title{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.stf__res-sub{font-size:11.5px;color:var(--text-subtle);}

/* экземпляры (910) */
.stf__exh{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:18px 0 8px;}
.stf__ex{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-subtle);}
.stf__ex:last-of-type{border-bottom:none;}
.stf__ex input{box-sizing:border-box;width:100%;padding:7px 10px;border-radius:var(--radius-md);border:1px solid var(--border-default);
  background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.stf__ex input:focus{outline:none;border-color:var(--accent);}
@media (max-width:880px){.stf__search{grid-template-columns:1fr;}.stf__ex{grid-template-columns:1fr 1fr;}}

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
  if (route === "circulation") return "circulation";
  if (route === "cells") return "cells";
  if (route === "acquisition") return "acquisition";
  if (route === "provision") return "provision";
  if (route === "admin") return "admin";
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
    current === "circulation" ? "Книговыдача" :
    current === "cells" ? "Ячеистое хранение" :
    current === "acquisition" ? "Комплектование" :
    current === "provision" ? "Книгообеспеченность" :
    current === "admin" ? "Администрирование" :
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
            : current === "circulation" ? <CirculationDesk toast={toast} />
            : current === "acquisition" ? <AcquisitionDesk toast={toast} />
            : current === "provision" ? <BookProvisionDesk toast={toast} />
            : current === "admin" ? <AdminDesk toast={toast} />
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
// Каталогизация — рабочий лист RUSMARC: поиск записи в базе → правка в редакторе
// полей/подполей (control-by-type через DynamicField), экземпляры (910), и
// сохранение с ЖИВЫМ ФЛК (POST /api/validate): severity-1 непреодолимая блокирует
// сохранение, severity-2 преодолимая — сохранение с подтверждением. Нарушения
// раскладываются по строкам рабочего листа (field/subfield → подсветка строки).
// Деградация: нет /api/validate → клиентская проверка обязательных полей; нет
// /api/worklist → информер. Сохранение — в песочницу WORK (правка не на боевой).
// ============================================================================

// Строка экземпляра (поле 910): инвентарный номер (^b), штрих-код/RFID (^h),
// место хранения (^d). Базовый ввод — MVP, расширяется статусом/КСУ позже.
type Exemplar = { b: string; h: string; d: string };
const emptyExemplar = (): Exemplar => ({ b: "", h: "", d: "" });

// Ключ строки рабочего листа для нарушения ФЛК: совпадает с кодом поля; саб-поле
// здесь не разводим по отдельным контролам (DynamicField рисует подполя внутри),
// поэтому подсвечиваем всю строку поля.
const flkKey = (v: FlkViolation): string => (v.field || v.path || "").toString();

function CatalogingWorksheet({ staff: _staff, toast }: { staff: StaffSession; toast: ToastFn }) {
  const SANDBOX = "WORK";
  const SEARCH_DB = "IBIS";
  const [wl, setWl] = React.useState<WLField[] | null>(null);
  const [wlMissing, setWlMissing] = React.useState(false);
  const [values, setValues] = React.useState<Record<string, any>>({});
  const [exemplars, setExemplars] = React.useState<Exemplar[]>([]);
  const [mfn, setMfn] = React.useState(0);
  const [saved, setSaved] = React.useState<any>(null);
  // errors: код поля → текст (для подсветки строки + DynamicField error).
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [violations, setViolations] = React.useState<FlkViolation[]>([]);
  const [checked, setChecked] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  // search-to-edit
  const [query, setQuery] = React.useState("");
  const [prefix, setPrefix] = React.useState("T=");
  const [results, setResults] = React.useState<ResultItem[] | null>(null);
  const [searching, setSearching] = React.useState(false);

  React.useEffect(() => { (async () => {
    const r = await api.worklist(SANDBOX);
    if (r.json?.ok && r.json.data && r.json.data.fields) { setWl(r.json.data.fields); setValues(emptyValues(r.json.data.fields)); }
    else setWlMissing(true);
  })(); }, []);

  const set = (code: string, val: any) => {
    setValues((v) => ({ ...v, [code]: val }));
    if (errors[code]) setErrors((e) => { const n = { ...e }; delete n[code]; return n; });
  };
  function resetEditor(keepResults = true) {
    setValues(emptyValues(wl!)); setExemplars([]); setMfn(0); setSaved(null);
    setErrors({}); setViolations([]); setChecked(false);
    if (!keepResults) setResults(null);
  }
  const newRecord = () => resetEditor();

  // --- поиск записи в базе → список результатов → выбор для правки ---------
  async function runSearch() {
    const q = query.trim(); if (!q) return;
    setSearching(true);
    const r = await api.search(SEARCH_DB, prefix, q, 1, 25);
    setSearching(false);
    if (r.json?.ok && r.json.data) setResults(r.json.data.items);
    else { setResults([]); toast({ variant: "info", title: "Поиск недоступен", message: "Не удалось выполнить поиск в базе " + SEARCH_DB + "." }); }
  }
  async function pickRecord(item: ResultItem) {
    const r = await api.record(SEARCH_DB, item.mfn);
    if (r.json?.ok && r.json.data) {
      setValues(recordToValues(r.json.data.fields, wl!));
      // экземпляры из поля 910 загруженной записи (b/h/d) — для правки.
      const ex = (r.json.data.fields || []).filter((f: any) => f.tag === "910").map((f: any) => ({
        b: f.subfields?.b || f.subfields?.B || "", h: f.subfields?.h || f.subfields?.H || "", d: f.subfields?.d || f.subfields?.D || "",
      }));
      setExemplars(ex);
      setMfn(0); setSaved(null); setErrors({}); setViolations([]); setChecked(false);
      toast({ variant: "info", title: "Запись загружена в форму", message: SEARCH_DB + " MFN " + item.mfn + " → сохранится в песочницу " + SANDBOX });
    } else toast({ variant: "warning", title: "Не удалось открыть", message: "MFN " + item.mfn });
  }

  // --- экземпляры (910) ----------------------------------------------------
  const addExemplar = () => setExemplars((xs) => xs.concat([emptyExemplar()]));
  const setExemplar = (i: number, patch: Partial<Exemplar>) => setExemplars((xs) => xs.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  const delExemplar = (i: number) => setExemplars((xs) => xs.filter((_, j) => j !== i));
  function exemplarFields(): { tag: string; value: string }[] {
    return exemplars
      .map((x) => [["b", x.b], ["h", x.h], ["d", x.d]].filter(([, v]) => (v || "").trim()).map(([c, v]) => "^" + c + (v as string).trim()).join(""))
      .filter((s) => s).map((value) => ({ tag: "910", value }));
  }

  // --- клиентский ФЛК (деградация): обязательные поля -----------------------
  function clientRequired(): Record<string, string> {
    const errs: Record<string, string> = {};
    (wl || []).forEach((fd) => {
      if (fd.required) {
        const v = values[fd.code];
        const ok = fd.subfields ? (v && typeof v === "object" && Object.values(v).some(Boolean)) : !!(v && v.toString().trim());
        if (!ok) errs[fd.code] = "ФЛК: обязательное поле не заполнено";
      }
    });
    return errs;
  }

  // Разложить нарушения сервера по строкам рабочего листа + текст в DynamicField.
  function applyViolations(vs: FlkViolation[]) {
    const errs: Record<string, string> = {};
    vs.forEach((v) => { if (v.severity >= 1) { const k = flkKey(v); if (k) errs[k] = (errs[k] ? errs[k] + " · " : "") + v.message; } });
    setErrors(errs); setViolations(vs);
  }

  // Прогон ФЛК: пробуем сервер (/api/validate), при 404/501 — клиентская проверка.
  // Возвращает {hardBlocked, ok} для решения «сохранять / блокировать».
  async function runFlk(): Promise<{ hardBlocked: boolean; soft: boolean; serverUp: boolean }> {
    const rec = valuesToFlkRecord(wl!, values);
    const r = await api.validate(SANDBOX, rec, "save", undefined, mfn || undefined);
    if (r.status === 404 || r.status === 501 || !r.json?.ok || !r.json.data) {
      // движок ФЛК не развёрнут → клиентская обязательность
      const errs = clientRequired(); setErrors(errs); setViolations([]);
      return { hardBlocked: Object.keys(errs).length > 0, soft: false, serverUp: false };
    }
    const data = r.json.data;
    applyViolations(data.violations || []);
    return { hardBlocked: !data.canSave, soft: data.overallSeverity === 2, serverUp: true };
  }

  async function checkFlk() {
    setChecked(true);
    const res = await runFlk();
    if (res.hardBlocked) toast({ variant: "warning", title: "ФЛК: непреодолимые замечания", message: "Сохранение заблокировано — исправьте отмеченные поля." });
    else if (res.soft) toast({ variant: "info", title: "ФЛК: преодолимые замечания", message: "Можно сохранить с подтверждением." });
    else toast({ variant: "success", title: "ФЛК пройден", message: res.serverUp ? "Нарушений нет." : "Обязательные поля заполнены." });
  }

  async function persist() {
    setSaving(true);
    const r = await api.saveRecord(SANDBOX, mfn, valuesToFields(wl!, values).concat(exemplarFields()));
    setSaving(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      // сервер может вернуть нарушения и при сохранении — покажем их.
      if (r.json.data.violations && r.json.data.violations.length) applyViolations(r.json.data.violations);
      setSaved(r.json.data); setMfn(r.json.data.mfn);
      toast({ variant: "success", title: r.json.data.created ? "Запись создана" : "Запись обновлена", message: SANDBOX + " · MFN " + r.json.data.mfn });
    } else if (r.status === 422 && r.json?.data?.violations) {
      applyViolations(r.json.data.violations); setChecked(true);
      toast({ variant: "warning", title: "ФЛК не пройден на сервере", message: "Запись не сохранена — см. отмеченные поля." });
    } else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант record.write." });
    else toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку." });
  }

  async function save() {
    setChecked(true);
    const res = await runFlk();
    if (res.hardBlocked) {
      toast({ variant: "warning", title: "Сохранение заблокировано (ФЛК)", message: res.serverUp ? "Есть непреодолимые нарушения — исправьте отмеченные поля." : "Заполните обязательные поля." });
      return; // severity-1 блокирует
    }
    if (res.soft) {
      const okSoft = typeof window === "undefined" ? true : window.confirm("ФЛК: есть преодолимые замечания. Сохранить запись всё равно?");
      if (!okSoft) return;
    }
    await persist();
  }

  // Сводка ФЛК для правой панели.
  const requiredFields = (wl || []).filter((f) => f.required);
  const hardCount = violations.filter((v) => v.severity === 1).length;
  const softCount = violations.filter((v) => v.severity === 2).length;
  const errCount = Object.keys(errors).length;

  const exInputs = (i: number, x: Exemplar) => (
    <div className="stf__ex" key={i}>
      <input value={x.b} onChange={(e) => setExemplar(i, { b: e.target.value })} placeholder="Инв. номер (^b)" aria-label={"Инвентарный номер экземпляра " + (i + 1)} />
      <input value={x.h} onChange={(e) => setExemplar(i, { h: e.target.value })} placeholder="Штрих-код / RFID (^h)" aria-label={"Штрих-код экземпляра " + (i + 1)} />
      <input value={x.d} onChange={(e) => setExemplar(i, { d: e.target.value })} placeholder="Место хранения (^d)" aria-label={"Место хранения экземпляра " + (i + 1)} />
      <Button variant="ghost" size="sm" iconLeft="trash" aria-label="Удалить экземпляр" onClick={() => delExemplar(i)} />
    </div>
  );

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Каталогизация</h2>
        <span className="stf__pill">Книга · RUSMARC</span>
        <span className="stf__pill" style={{ background: "var(--status-issued-bg)", color: "var(--status-issued)", borderColor: "transparent" }}>{mfn ? "MFN " + mfn : "Черновик"}</span>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button variant="secondary" size="sm" iconLeft="check-circle" onClick={checkFlk} disabled={!wl}>Проверить ФЛК</Button>
        <Button size="sm" iconLeft="check-circle" loading={saving} onClick={save} disabled={!wl}>Сохранить</Button>
      </div>
    </div>
  );

  // нет рабочего листа → информер (движок каталогизации не развёрнут).
  if (wlMissing) return (
    <div>
      {head}
      <div className="stf__card" style={{ padding: 4 }}>
        <EmptyState icon="file-text" title="Рабочий лист каталогизации подключается отдельно"
          description="Редактор библиографической записи свёрстан в Стиле A и работает поверх движка каталогизации (#183/#188). На текущем сервере /api/worklist ещё не опубликован — поле/подполе появятся после его развёртывания." />
      </div>
    </div>
  );

  return (
    <div>
      {head}

      {/* ===== Поиск записи в базе → выбор для правки ===== */}
      <div className="stf__search">
        <select value={prefix} onChange={(e) => setPrefix(e.target.value)} aria-label="Точка доступа поиска"
          style={{ padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-body)", fontFamily: "var(--font-ui)", fontSize: 13 }}>
          <option value="T=">Заглавие</option>
          <option value="A=">Автор</option>
          <option value="K=">Ключевые слова</option>
          <option value="I=">Инв./шифр</option>
          <option value="">Свободно (выражение)</option>
        </select>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={"Поиск записи в базе " + SEARCH_DB + " для правки…"}
          aria-label="Поисковый запрос" autoComplete="off"
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
          style={{ padding: "8px 11px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)", background: "var(--surface-card)", color: "var(--text-body)", fontFamily: "var(--font-ui)", fontSize: 13 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant="secondary" size="sm" iconLeft="search" loading={searching} onClick={runSearch} disabled={!wl}>Найти</Button>
          <Button variant="secondary" size="sm" iconLeft="plus" onClick={newRecord} disabled={!wl}>Новая</Button>
        </div>
      </div>

      {results !== null && (
        results.length === 0
          ? <div style={{ color: "var(--text-subtle)", fontSize: 13, marginBottom: 14 }}>Ничего не найдено — уточните запрос или создайте новую запись.</div>
          : <div className="stf__results" role="listbox" aria-label="Результаты поиска">
              {results.map((it) => (
                <button key={it.mfn} type="button" className="stf__res" onClick={() => pickRecord(it)}>
                  <span className="stf__res-mfn">MFN {it.mfn}</span>
                  <span className="stf__res-main">
                    <span className="stf__res-title">{it.title || "Без заглавия"}</span>
                    <span className="stf__res-sub">{[it.author, it.year, it.docType].filter(Boolean).join(" · ")}</span>
                  </span>
                  <Icon name="edit" size={15} style={{ color: "var(--text-subtle)", flex: "none" }} />
                </button>
              ))}
            </div>
      )}

      {!wl ? <div style={{ color: "var(--text-subtle)", fontSize: 13 }}>Загрузка рабочего листа…</div> : (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 280px", gap: 18, alignItems: "start" }} className="stf__cat-grid">
          {/* worksheet — labelled field rows + экземпляры */}
          <div className="stf__card" style={{ padding: "4px 20px" }}>
            {wl.map((fd) => (
              <div className={"stf__row" + (errors[fd.code] ? " stf__row--bad" : "")} key={fd.code}>
                <div className="stf__row-lab">
                  <span className="stf__row-code">{fd.code}</span>
                  <span className="stf__row-name">{fd.label}{fd.required && <span className="stf__row-req" aria-hidden="true">*</span>}</span>
                </div>
                <DynamicField field={{ ...fd, code: undefined } as any} value={values[fd.code]} onChange={(v: any) => set(fd.code, v)} error={errors[fd.code]} />
              </div>
            ))}

            {/* экземпляры (910) */}
            <div className="stf__exh">
              <div className="stf__row-lab">
                <span className="stf__row-code">910</span>
                <span className="stf__row-name">Экземпляры</span>
                <span style={{ fontSize: 11.5, color: "var(--text-subtle)" }}>· {exemplars.length}</span>
              </div>
              <Button variant="secondary" size="sm" iconLeft="plus" onClick={addExemplar}>Добавить экземпляр</Button>
            </div>
            {exemplars.length === 0
              ? <div style={{ fontSize: 12.5, color: "var(--text-subtle)", paddingBottom: 8 }}>Экземпляров нет. Добавьте инвентарные единицы (инв. номер, штрих-код/RFID, место хранения).</div>
              : exemplars.map((x, i) => exInputs(i, x))}

            <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "14px 0" }}>
              <Button iconLeft="check-circle" loading={saving} onClick={save}>Сохранить запись</Button>
              {saved && <span style={{ color: "var(--success)", fontSize: 13 }}><Icon name="check" size={13} /> сохранено в {saved.db}, MFN {saved.mfn} (код {saved.returnCode})</span>}
            </div>
          </div>

          {/* ФЛК сводка */}
          <aside className="stf__card" style={{ padding: 16, position: "sticky", top: 64 }} aria-label="Сводка проверки ФЛК">
            <span className="stf__card-cap">Проверка ФЛК</span>
            {violations.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 12 }}>
                {violations.map((v, i) => (
                  <div key={v.ruleId + ":" + i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12.5, color: v.severity === 1 ? "var(--danger-500)" : "var(--text-body)" }}>
                    <Icon name={v.severity === 1 ? "alert-octagon" : "alert-triangle"} size={15} style={{ color: v.severity === 1 ? "var(--danger-500)" : "var(--status-issued)", flex: "none", marginTop: 1 }} />
                    <span>{v.path ? <b style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{v.path}</b> : null} {v.message}</span>
                  </div>
                ))}
              </div>
            ) : (
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
            )}
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border-subtle)", fontSize: 12, color: checked ? ((hardCount || errCount) ? "var(--danger-500)" : softCount ? "var(--status-issued)" : "var(--success)") : "var(--text-subtle)" }}>
              {!checked ? "Нажмите «Проверить ФЛК» перед сохранением."
                : hardCount ? hardCount + " непреодолим(ое/ых) — сохранение блокируется" + (softCount ? ", + " + softCount + " преодолим(ое/ых)" : "")
                : softCount ? softCount + " преодолим(ое/ых) — можно сохранить с подтверждением"
                : errCount ? errCount + " замечани(е/я) ФЛК"
                : "ФЛК пройден — можно сохранять."}
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
