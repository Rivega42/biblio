import React from "react";
import { api } from "./api";
import type { Grant } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import { DynamicField } from "../components/cataloging/DynamicField.jsx";

export interface StaffSession { name?: string; login: string; grants: Grant[]; }
type ToastFn = (t: { variant: string; title: string; message?: string }) => void;

const DOMAINS = [
  { id: "cataloging", label: "Каталогизация", icon: "book", grant: "record.write", desc: "Создание и правка библиографических записей", route: "cataloging" as const },
  { id: "cells", label: "Ячеистое хранение", icon: "archive", grant: "record.read", desc: "Карта ячеек: занятость, адрес, RFID (наша фишка)", route: "cells" as const },
  { id: "circ", label: "Книговыдача", icon: "package", grant: "circ.issue", desc: "Выдача, возврат, очередь, бронеполка, ячейки", route: "stub" as const },
  { id: "acq", label: "Комплектование", icon: "archive", grant: "acq.receipt", desc: "Заказ, поступление, КСУ, списание", route: "stub" as const },
  { id: "inv", label: "Инвентаризация", icon: "scan-line", grant: "record.read", desc: "Сверка фонда с ТСД", route: "stub" as const },
  { id: "analytics", label: "Аналитика", icon: "bar-chart", grant: "record.read", desc: "BI-дашборды: выдачи, фонд, читатели", route: "stub" as const },
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

export function StaffArea({ staff, route, setRoute, toast }: { staff: StaffSession; route: any; setRoute: (r: any) => void; toast: ToastFn }) {
  if (route === "cataloging") return <CatalogingWorksheet staff={staff} onBack={() => setRoute("desktop")} toast={toast} />;
  if (route === "cells") return <CellMap onBack={() => setRoute("desktop")} />;
  if (route && route.name === "stub") return <StaffStub title={route.title} onBack={() => setRoute("desktop")} />;
  return <StaffDesktop staff={staff} onOpen={(d) => setRoute(d.route === "stub" ? { name: "stub", title: d.label } : d.route)} />;
}

function StaffDesktop({ staff, onOpen }: { staff: StaffSession; onOpen: (d: typeof DOMAINS[number]) => void }) {
  const tiles = DOMAINS.filter((d) => hasGrant(staff.grants, d.grant));
  return (
    <div>
      <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: "4px 0 2px" }}>Рабочий стол сотрудника</h2>
      <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", marginTop: 0 }}>{staff.name} · доступно задач: {tiles.length} — собрано <b>по грантам</b>, не «по АРМам».</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px,1fr))", gap: 14, marginTop: 14 }}>
        {tiles.map((d) => (
          <div key={d.id} onClick={() => onOpen(d)} style={{ cursor: "pointer", background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
            <span style={{ background: "var(--accent-weak,#eef2f7)", color: "var(--accent)", borderRadius: 10, padding: 8, flex: "none" }}><Icon name={d.icon} size={22} /></span>
            <div><div style={{ fontWeight: 600 }}>{d.label}</div><div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>{d.desc}</div></div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 16, fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Показаны только разрешённые функции. Запись/удаление — под грантами уровня write/admin, действия пишутся в аудит.</div>
    </div>
  );
}

function StaffStub({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
      <EmptyState icon="clock" title={title} description="Экран спроектирован в дизайн-системе. На живые данные подключается следующим шагом — сейчас доступна каталогизация." />
    </div>
  );
}

const KIND_RU: Record<string, string> = { building: "🏛 Здание", floor: "Этаж", room: "Помещение", rack: "Стеллаж", shelf: "Полка", postamat: "📦 Постамат выдачи", return: "↩ Станция книгоприёма" };
const cellColor = (c: any) => !c.occupied ? "var(--surface-sunken,#e8e4da)"
  : ({ available: "#2f855a", hold: "#2c5e8a", returned: "#7a6a55", issued: "#b7791f" } as any)[c.status] || "#888";

function rackFill(r: any) {
  const t = r.cellsTotal || 0, o = r.cellsOccupied || 0, ratio = t ? o / t : 0;
  return !t ? "#cfc8ba" : ratio >= 0.85 ? "#b7791f" : ratio >= 0.5 ? "#caa53d" : ratio > 0 ? "#3f9d6d" : "#cfc8ba";
}

function CellGrid({ cells }: { cells: any[] }) {
  return <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
    {cells.map((c, j) => <span key={j} title={c.occupied ? ((c.title || "") + " · " + c.inv) : "свободно"} style={{ fontFamily: "var(--font-mono)", fontSize: 11, padding: "3px 6px", borderRadius: 5, color: c.occupied ? "#fff" : "var(--text-subtle)", background: cellColor(c), cursor: "default" }}>{c.code}</span>)}
  </div>;
}

function RoomPlan({ room, onPick, selId }: { room: any; onPick: (r: any) => void; selId: number | null }) {
  const racks = (room.children || []).filter((c: any) => c.kind === "rack");
  const W = room.gw || 300, H = room.gh || 160;
  return (
    <div style={{ overflowX: "auto", margin: "4px 0 8px" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={Math.min(W, 720)} style={{ maxWidth: "100%", border: "1px solid var(--border-subtle)", borderRadius: 8, background: "var(--surface-card,#fff)" }}>
        <rect x={0} y={H - 13} width={W} height={13} fill="var(--surface-sunken,#eee)" />
        <text x={6} y={H - 3.5} fontSize={8} fill="var(--text-subtle)">вход</text>
        {racks.map((r: any, i: number) => (
          <g key={i} onClick={() => onPick(r)} style={{ cursor: "pointer" }}>
            <rect x={r.gx} y={r.gy} width={r.gw} height={r.gh} rx={3} fill={rackFill(r)} stroke={selId === r.id ? "#1a1a1a" : "rgba(0,0,0,.18)"} strokeWidth={selId === r.id ? 2 : 1} />
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
      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", margin: "2px 0 4px" }}>План помещения · {(room.children || []).filter((c: any) => c.kind === "rack").length} стеллажей · цвет = заполненность</div>
      <RoomPlan room={room} onPick={setSel} selId={sel ? sel.id : null} />
      {sel ? (
        <div style={{ margin: "2px 0 8px" }}>
          <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", marginBottom: 4 }}>Стеллаж {sel.code} · занято {sel.cellsOccupied}/{sel.cellsTotal}</div>
          {(sel.children || []).map((sh: any, i: number) => (
            <div key={i} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginBottom: 2 }}>Полка {sh.code}</div>
              <CellGrid cells={sh.children || []} />
            </div>
          ))}
        </div>
      ) : <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginBottom: 8 }}>Кликните стеллаж на плане — покажутся его полки и ячейки.</div>}
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
      <div onClick={() => setOpen((o) => !o)} style={{ cursor: "pointer", fontWeight: depth < 3 ? 600 : 500, fontSize: depth < 2 ? "var(--text-base,15px)" : "var(--text-sm)", display: "flex", gap: 6, alignItems: "center", margin: "5px 0" }}>
        <span style={{ color: "var(--text-subtle)", width: 10 }}>{kids.length ? (open ? "▾" : "▸") : "·"}</span>
        <span>{head}</span>
        {occ && <span style={{ color: "var(--text-subtle)", fontSize: "var(--text-xs)", fontWeight: 400 }}>· занято {occ}</span>}
      </div>
      {open && (node.kind === "room" ? <RoomView room={node} /> : <>
        {leaves.length > 0 && <div style={{ margin: "2px 0 8px 16px" }}><CellGrid cells={leaves} /></div>}
        {conts.map((k, i) => <StorageNode key={i} node={k} depth={depth + 1} />)}
      </>)}
    </div>
  );
}

function CellMap({ onBack }: { onBack: () => void }) {
  const [data, setData] = React.useState<any>(null);
  const [err, setErr] = React.useState(false);
  React.useEffect(() => { (async () => { const r = await api.storage("IBIS"); if (r.json && r.json.ok && r.json.data) setData(r.json.data); else setErr(true); })(); }, []);
  if (err) return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
      <EmptyState icon="archive" title="Ячеистое хранение" description="Доступно на нашем сервере (server-own). На адаптере к ИРБИС иерархии хранения нет — это наша модель." />
    </div>
  );
  if (!data) return <div style={{ color: "var(--text-subtle)" }}>Загрузка карты хранения…</div>;
  const legend: [string, string][] = [["В ячейке", "#2f855a"], ["В постамате", "#2c5e8a"], ["Книгоприём", "#7a6a55"], ["Свободно", "var(--surface-sunken,#e8e4da)"]];
  return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
      <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: "8px 0 2px" }}>Ячеистое хранение</h2>
      <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", marginTop: 0 }}>Размещено экземпляров: {data.holdings} · здания → этажи → помещения → стеллажи → полки → ячейки (число ячеек на полке разное) + постамат/книгоприём. В ИРБИС такого нет.</p>
      <div style={{ display: "flex", gap: 14, margin: "8px 0 14px", flexWrap: "wrap", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
        {legend.map(([l, c], i) => <span key={i}><span style={{ display: "inline-block", width: 11, height: 11, borderRadius: 3, background: c, marginRight: 5, verticalAlign: "middle" }} />{l}</span>)}
      </div>
      {(data.tree || []).map((n: any, i: number) => <StorageNode key={i} node={n} depth={0} />)}
    </div>
  );
}

function CatalogingWorksheet({ staff, onBack, toast }: { staff: StaffSession; onBack: () => void; toast: ToastFn }) {
  const SANDBOX = "WORK";
  const [wl, setWl] = React.useState<WLField[] | null>(null);
  const [values, setValues] = React.useState<Record<string, any>>({});
  const [mfn, setMfn] = React.useState(0);
  const [openMfn, setOpenMfn] = React.useState("");
  const [saved, setSaved] = React.useState<any>(null);
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  React.useEffect(() => { (async () => { const r = await api.worklist(SANDBOX); if (r.json?.ok && r.json.data) { setWl(r.json.data.fields); setValues(emptyValues(r.json.data.fields)); } })(); }, []);

  const set = (code: string, val: any) => setValues((v) => ({ ...v, [code]: val }));
  const newRecord = () => { setValues(emptyValues(wl!)); setMfn(0); setSaved(null); setErrors({}); };
  async function loadFromIbis() {
    const id = parseInt(openMfn, 10); if (!id) return;
    const r = await api.record("IBIS", id);
    if (r.json?.ok && r.json.data) { setValues(recordToValues(r.json.data.fields, wl!)); setMfn(0); setSaved(null); toast({ variant: "info", title: "Запись загружена в форму", message: "IBIS MFN " + id + " → сохранится в песочницу " + SANDBOX }); }
    else toast({ variant: "warning", title: "Не найдено", message: "Нет записи MFN " + id + " в IBIS." });
  }
  async function save() {
    const errs: Record<string, string> = {};
    (wl || []).forEach((fd) => { if (fd.required) { const ok = fd.subfields ? (values[fd.code] && Object.values(values[fd.code]).some(Boolean)) : !!values[fd.code]; if (!ok) errs[fd.code] = "Обязательное поле (ФЛК)"; } });
    setErrors(errs);
    if (Object.keys(errs).length) { toast({ variant: "warning", title: "Заполните обязательные поля", message: "Тип записи и Заглавие." }); return; }
    const r = await api.saveRecord(SANDBOX, mfn, valuesToFields(wl!, values));
    if (r.status === 200 && r.json?.ok && r.json.data) { setSaved(r.json.data); setMfn(r.json.data.mfn); toast({ variant: "success", title: r.json.data.created ? "Запись создана" : "Запись обновлена", message: SANDBOX + " · MFN " + r.json.data.mfn }); }
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант record.write." });
    else toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку." });
  }

  const tbtn: React.CSSProperties = { padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)" };
  return (
    <div>
      <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
        <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: 0 }}>Каталогизация</h2>
        <span style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>учебная база {SANDBOX} (песочница) · рабочий лист «Книга»</span>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "14px 0", flexWrap: "wrap" }}>
        <Button iconLeft="plus" onClick={newRecord}>Новая запись</Button>
        <span style={{ color: "var(--text-subtle)" }}>·</span>
        <input value={openMfn} onChange={(e) => setOpenMfn(e.target.value)} placeholder="MFN из IBIS" style={{ ...tbtn, width: 130 }} onKeyDown={(e) => { if (e.key === "Enter") loadFromIbis(); }} />
        <button onClick={loadFromIbis} style={tbtn}>Загрузить из IBIS</button>
        <span style={{ marginLeft: "auto", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>{mfn ? "MFN " + mfn : "новая запись"}</span>
      </div>
      {!wl ? <div style={{ color: "var(--text-subtle)" }}>Загрузка рабочего листа…</div> : (
        <div style={{ background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
          {wl.map((fd) => <DynamicField key={fd.code} field={fd} value={values[fd.code]} onChange={(v: any) => set(fd.code, v)} error={errors[fd.code]} />)}
          <div style={{ display: "flex", gap: 10, alignItems: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
            <Button iconLeft="check-circle" onClick={save}>Сохранить запись</Button>
            {saved && <span style={{ color: "var(--accent)", fontSize: "var(--text-sm)" }}>✓ сохранено в {saved.db}, MFN {saved.mfn} (код {saved.returnCode})</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export function StaffLoginOverlay({ onClose, onSubmit }: { onClose: () => void; onSubmit: (l: string, p: string) => void }) {
  const [l, setL] = React.useState("");
  const [p, setP] = React.useState("");
  const inp: React.CSSProperties = { width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", marginBottom: 10 };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--surface-card, #fff)", color: "var(--text-body)", borderRadius: 16, padding: 22, width: 340, boxShadow: "var(--shadow-lg, 0 20px 50px rgba(0,0,0,.25))" }}>
        <div style={{ fontWeight: 600, fontSize: "var(--text-lg)", marginBottom: 8 }}>Вход сотрудника</div>
        <p style={{ margin: "0 0 12px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Доступ определяется грантами учётной записи.</p>
        <input value={l} onChange={(e) => setL(e.target.value)} placeholder="Логин" style={inp} />
        <input value={p} onChange={(e) => setP(e.target.value)} type="password" placeholder="Пароль" onKeyDown={(e) => { if (e.key === "Enter") onSubmit(l, p); }} style={inp} />
        <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginBottom: 12 }}>демо: <b>admin / admin</b> · <b>librarian / librarian</b></div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onClose}>Отмена</Button>
          <Button onClick={() => onSubmit(l, p)}>Войти</Button>
        </div>
      </div>
    </div>
  );
}
