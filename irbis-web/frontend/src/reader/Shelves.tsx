// Полки / списки чтения читателя (#222). Два экспорта:
//   ShelvesPanel — раздел кабинета: реальные списки из GET /api/shelves, создание
//     нового списка, разворачивание со списком изданий и удалением позиции;
//   ShelfMenu — выпадающий контрол «В список ▾» на карточке записи/результата:
//     добавляет издание в «Хочу прочитать»/«Избранное»/пользовательский список.
// Оптимистичный UI с reconcile (на ошибке откатываем и показываем тост). При 404/501
// эндпойнтов полок ещё нет → ShelvesPanel прячется (onUnavailable), ShelfMenu тихо тостит.
import React from "react";
import { api } from "../api";
import type { Shelf } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";
import type { IconName } from "../../components/icon/Icon.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

type Toast = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Иконка для встроенных списков по имени; пользовательские → «star».
function shelfIcon(name: string, system?: boolean): IconName {
  const n = (name || "").toLowerCase();
  if (n.includes("прочит")) return "book";
  if (n.includes("избран")) return "star";
  if (n.includes("работ")) return "briefcase";
  return system ? "bookmark" : "list";
}
function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

const MENU_CSS = `
.irb-shmenu{position:relative;display:inline-flex;}
.irb-shmenu__pop{position:absolute;top:calc(100% + 6px);left:0;z-index:40;width:min(260px,86vw);
  background:var(--surface-card,#fff);color:var(--text-body);border:1px solid var(--border-strong,#cdd3da);
  border-radius:12px;box-shadow:var(--shadow-lg,0 14px 36px rgba(0,0,0,.2));overflow:hidden;
  display:flex;flex-direction:column;max-height:330px;}
.irb-shmenu__hd{padding:9px 13px;font-size:var(--text-2xs,11px);font-weight:700;letter-spacing:.04em;
  text-transform:uppercase;color:var(--text-subtle);border-bottom:1px solid var(--border-subtle);}
.irb-shmenu__list{overflow-y:auto;}
.irb-shmenu__opt{display:flex;align-items:center;gap:9px;width:100%;background:none;border:none;text-align:left;
  padding:9px 13px;cursor:pointer;font-family:var(--font-ui,inherit);font-size:var(--text-sm);color:var(--text-body);}
.irb-shmenu__opt:hover{background:var(--accent-weak,#eef2f7);}
.irb-shmenu__opt--on{color:var(--accent);}
.irb-shmenu__opt-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-shmenu__create{display:flex;gap:6px;padding:9px 11px;border-top:1px solid var(--border-subtle);}
.irb-shmenu__create input{flex:1;min-width:0;padding:6px 9px;border-radius:7px;border:1px solid var(--border-strong,#cdd3da);
  font-size:var(--text-sm);background:var(--surface-card,#fff);color:var(--text-body);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-shmenu-css")) {
  const s = document.createElement("style"); s.id = "irb-shmenu-css"; s.textContent = MENU_CSS; document.head.appendChild(s);
}

// «В список ▾» — выпадающий список полок с добавлением издания (#222).
export function ShelfMenu({
  db, mfn, title, toast, compact = false,
}: {
  db: string; mfn: number; title?: string; toast: Toast; compact?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [lists, setLists] = React.useState<Shelf[] | null>(null);
  const [newName, setNewName] = React.useState("");
  const wrapRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc); document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  async function loadLists() {
    const r = await api.shelves();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.lists)) setLists(r.json.data.lists);
    else setLists([]);
  }
  function toggle() { const next = !open; setOpen(next); if (next && lists === null) loadLists(); }

  function has(list: Shelf): boolean { return list.items.some((it) => it.db === db && it.mfn === mfn); }

  async function add(list: Shelf) {
    if (has(list)) { setOpen(false); return; }
    // Оптимистично помечаем как добавленное.
    setLists((ls) => (ls || []).map((l) => l.id === list.id ? { ...l, items: [...l.items, { db, mfn, title }] } : l));
    const r = await api.addToShelf(list.id, db, mfn);
    if (r.status === 200) {
      toast({ variant: "success", title: "Добавлено в список", message: list.name });
      setOpen(false);
    } else {
      // Откат.
      setLists((ls) => (ls || []).map((l) => l.id === list.id ? { ...l, items: l.items.filter((it) => !(it.db === db && it.mfn === mfn)) } : l));
      if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." });
      else toast({ variant: "info", title: "Списки недоступны", message: "Модуль списков чтения ещё подключается." });
      setOpen(false);
    }
  }

  async function createAndAdd() {
    const name = newName.trim();
    if (!name) return;
    const r = await api.createShelf(name);
    if (r.json?.ok && r.json.data) {
      const created: Shelf = { id: r.json.data.id, name: r.json.data.name || name, system: false, items: [] };
      setLists((ls) => [...(ls || []), created]);
      setNewName("");
      await add(created);
    } else {
      toast({ variant: "info", title: "Списки недоступны", message: "Не удалось создать список — повторите позже." });
    }
  }

  const btnSx: React.CSSProperties = compact
    ? { display: "inline-flex", alignItems: "center", gap: 5, background: "rgba(20,16,14,.4)", color: "#fff", border: "1px solid rgba(255,255,255,.7)", borderRadius: "var(--radius-sm,7px)", padding: "4px 8px", cursor: "pointer", fontSize: "var(--text-2xs,11px)", backdropFilter: "blur(2px)" }
    : { display: "inline-flex", alignItems: "center", gap: 6, background: "transparent", color: "var(--text-body)", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)" };

  return (
    <div className="irb-shmenu" ref={wrapRef}>
      <button type="button" style={btnSx} onClick={(e) => { e.stopPropagation(); toggle(); }} aria-expanded={open} aria-haspopup="menu" title="Добавить в список чтения">
        <Icon name="bookmark" size={compact ? 13 : 15} /> В список <Icon name="chevron-down" size={compact ? 11 : 13} />
      </button>
      {open && (
        <div className="irb-shmenu__pop" role="menu" onClick={(e) => e.stopPropagation()}>
          <div className="irb-shmenu__hd">Добавить в список</div>
          <div className="irb-shmenu__list">
            {lists === null ? (
              <div style={{ padding: "12px 13px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Загрузка…</div>
            ) : lists.length === 0 ? (
              <div style={{ padding: "12px 13px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Создайте первый список ниже.</div>
            ) : (
              lists.map((l) => {
                const on = has(l);
                return (
                  <button key={l.id} type="button" role="menuitem" className={"irb-shmenu__opt" + (on ? " irb-shmenu__opt--on" : "")} onClick={() => add(l)}>
                    <Icon name={shelfIcon(l.name, l.system)} size={16} />
                    <span className="irb-shmenu__opt-name">{l.name}</span>
                    {on && <Icon name="check" size={15} />}
                  </button>
                );
              })
            )}
          </div>
          <div className="irb-shmenu__create">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Новый список…"
              onKeyDown={(e) => { if (e.key === "Enter") createAndAdd(); }} aria-label="Название нового списка" />
            <Button size="sm" iconLeft="plus" onClick={createAndAdd}>Создать</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Раздел кабинета «Мои полки» (#222) — реальные списки с разворачиванием/удалением.
export function ShelvesPanel({
  cardSx, h2Sx, toast, onUnavailable, refreshKey, onOpenRecord,
}: {
  cardSx: React.CSSProperties;
  h2Sx: React.CSSProperties;
  toast: Toast;
  onUnavailable?: () => void;
  refreshKey?: number;
  onOpenRecord?: (db: string, mfn: number) => void;
}) {
  const [lists, setLists] = React.useState<Shelf[] | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const [openId, setOpenId] = React.useState<string | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [newName, setNewName] = React.useState("");

  const load = React.useCallback(async () => {
    const r = await api.shelves();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.lists)) {
      setLists(r.json.data.lists); setUnavailable(false);
    } else { setLists([]); setUnavailable(true); onUnavailable?.(); }
  }, [onUnavailable]);

  React.useEffect(() => { load(); }, [load, refreshKey]);

  async function createList() {
    const name = newName.trim();
    if (!name) return;
    const r = await api.createShelf(name);
    if (r.json?.ok && r.json.data) {
      setLists((ls) => [...(ls || []), { id: r.json!.data!.id, name: r.json!.data!.name || name, system: false, items: [] }]);
      setNewName(""); setCreating(false);
      toast({ variant: "success", title: "Список создан", message: name });
    } else {
      toast({ variant: "error", title: "Не удалось создать список", message: "Повторите попытку позже." });
    }
  }

  async function removeItem(list: Shelf, db: string, mfn: number) {
    const prev = list.items;
    setLists((ls) => (ls || []).map((l) => l.id === list.id ? { ...l, items: l.items.filter((it) => !(it.db === db && it.mfn === mfn)) } : l));
    const r = await api.removeFromShelf(list.id, db, mfn);
    if (r.status !== 200) {
      setLists((ls) => (ls || []).map((l) => l.id === list.id ? { ...l, items: prev } : l));
      toast({ variant: "error", title: "Не удалось убрать из списка", message: "Повторите попытку позже." });
    }
  }

  if (unavailable) return null;

  return (
    <section aria-labelledby="cab-shelves">
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
        <h2 id="cab-shelves" style={h2Sx}>Мои полки</h2>
        <div style={{ marginLeft: "auto" }}>
          {creating ? (
            <span style={{ display: "inline-flex", gap: 6 }}>
              <input autoFocus value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Название списка"
                onKeyDown={(e) => { if (e.key === "Enter") createList(); if (e.key === "Escape") { setCreating(false); setNewName(""); } }}
                aria-label="Название нового списка"
                style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", fontSize: "var(--text-sm)" }} />
              <Button size="sm" onClick={createList}>Создать</Button>
              <Button size="sm" variant="ghost" onClick={() => { setCreating(false); setNewName(""); }}>Отмена</Button>
            </span>
          ) : (
            <Button size="sm" variant="secondary" iconLeft="plus" onClick={() => setCreating(true)}>Новый список</Button>
          )}
        </div>
      </div>

      {lists === null ? (
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", padding: "4px 2px" }}>Загрузка полок…</div>
      ) : lists.length === 0 ? (
        <div style={cardSx}>
          <EmptyState icon="bookmark" title="Списков пока нет" description="Создайте список и добавляйте в него издания из каталога кнопкой «В список»." />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {lists.map((l) => {
            const expanded = openId === l.id;
            return (
              <div key={l.id} style={{ ...cardSx, borderRadius: "var(--radius-lg,13px)", overflow: "hidden" }}>
                <button type="button" onClick={() => setOpenId(expanded ? null : l.id)} aria-expanded={expanded}
                  style={{ display: "flex", alignItems: "center", gap: 12, width: "100%", background: "none", border: "none", textAlign: "left", padding: 16, cursor: "pointer", fontFamily: "var(--font-ui,inherit)" }}>
                  <span aria-hidden="true" style={{ width: 38, height: 38, flex: "none", borderRadius: 11, background: "var(--accent-weak,var(--accent-tint))", border: "1px solid var(--accent-weak-border,var(--accent-tint-border))", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)" }}>
                    <Icon name={shelfIcon(l.name, l.system)} size={18} />
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "block", fontWeight: 600, fontSize: "var(--text-sm)", color: "var(--text-strong)" }}>{l.name}</span>
                    <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 2 }}>{l.items.length} {plural(l.items.length, "издание", "издания", "изданий")}</span>
                  </span>
                  <Icon name={expanded ? "chevron-up" : "chevron-down"} size={18} style={{ color: "var(--text-subtle)", flex: "none" }} />
                </button>
                {expanded && (
                  <div style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    {l.items.length === 0 ? (
                      <div style={{ padding: "14px 16px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Список пуст — добавьте издания из каталога.</div>
                    ) : (
                      l.items.map((it) => (
                        <div key={it.db + ":" + it.mfn} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderTop: "1px solid var(--border-subtle)" }}>
                          <Icon name="book" size={15} style={{ color: "var(--text-subtle)", flex: "none" }} />
                          <button type="button" onClick={() => onOpenRecord?.(it.db, it.mfn)} disabled={!onOpenRecord}
                            style={{ flex: 1, minWidth: 0, textAlign: "left", background: "none", border: "none", padding: 0, cursor: onOpenRecord ? "pointer" : "default", color: onOpenRecord ? "var(--accent)" : "var(--text-body)", fontSize: "var(--text-sm)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "var(--font-ui,inherit)" }}>
                            {it.title || "Издание · " + it.db + "/" + it.mfn}
                          </button>
                          <button type="button" onClick={() => removeItem(l, it.db, it.mfn)} aria-label="Убрать из списка" title="Убрать из списка"
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-subtle)", flex: "none", padding: 2 }}>
                            <Icon name="trash" size={16} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
