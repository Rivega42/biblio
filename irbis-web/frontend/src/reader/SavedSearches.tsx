// Сохранённые запросы (#133). Три экспорта:
//   SaveSearchButton — кнопка «Сохранить запрос» на странице результатов: спрашивает
//     имя и сохраняет (db/prefix/query) через POST /api/savedsearch;
//   SavedSearchMenu — выпадающий список в шапке/тулбаре для повторного запуска/удаления;
//   SavedSearchesPanel — раздел кабинета с тем же списком (re-run / delete).
// Грациозная деградация: при 404/501 кнопка тихо тостит «модуль ещё подключается»,
// меню/панель показывают пустое состояние и не рушат страницу.
import React from "react";
import { api } from "../api";
import type { SavedSearch } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

type Toast = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Человекочитаемая метка области поиска по префиксу ИРБИС.
const PREFIX_LABEL: Record<string, string> = {
  K: "Ключевые слова", A: "Автор", T: "Заглавие", V: "Вид документа", "": "Выражение",
};
function prefixLabel(p?: string): string { return PREFIX_LABEL[p || ""] || (p ? p + "=" : "Выражение"); }

const CSS = `
.irb-ssmenu{position:relative;display:inline-flex;}
.irb-ssmenu__pop{position:absolute;top:calc(100% + 6px);right:0;z-index:40;width:min(320px,90vw);
  background:var(--surface-card,#fff);color:var(--text-body);border:1px solid var(--border-strong,#cdd3da);
  border-radius:12px;box-shadow:var(--shadow-lg,0 14px 36px rgba(0,0,0,.2));overflow:hidden;
  display:flex;flex-direction:column;max-height:360px;}
.irb-ssmenu__hd{padding:9px 13px;font-size:var(--text-2xs,11px);font-weight:700;letter-spacing:.04em;
  text-transform:uppercase;color:var(--text-subtle);border-bottom:1px solid var(--border-subtle);}
.irb-ssmenu__list{overflow-y:auto;}
.irb-ssrow{display:flex;align-items:center;gap:8px;padding:9px 13px;border-top:1px solid var(--border-subtle);}
.irb-ssrow:first-child{border-top:none;}
.irb-ssrow__main{flex:1;min-width:0;background:none;border:none;text-align:left;cursor:pointer;padding:0;
  font-family:var(--font-ui,inherit);color:var(--text-body);}
.irb-ssrow__name{display:block;font-size:var(--text-sm);font-weight:600;color:var(--text-strong);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-ssrow__meta{display:block;font-size:var(--text-xs);color:var(--text-subtle);margin-top:1px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-ssrow__del{background:none;border:none;cursor:pointer;color:var(--text-subtle);flex:none;padding:2px;}
.irb-ssrow__del:hover{color:var(--error,var(--danger-500));}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-ss-css")) {
  const s = document.createElement("style"); s.id = "irb-ss-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Кнопка «Сохранить запрос» на странице результатов.
export function SaveSearchButton({ db, prefix, query, defaultName, toast, onSaved, compact }: {
  db: string; prefix: string; query: string; defaultName?: string; toast: Toast;
  onSaved?: () => void; compact?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const wrapRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc); document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  function toggle() { const next = !open; setOpen(next); if (next) setName(defaultName || query); }

  async function save() {
    const nm = name.trim() || query.trim();
    if (!nm) return;
    setBusy(true);
    const r = await api.saveSearch(nm, db, prefix, query);
    setBusy(false);
    if (r.status === 200 && r.json?.ok) {
      setOpen(false);
      toast({ variant: "success", title: "Запрос сохранён", message: nm });
      onSaved?.();
    } else if (r.status === 401 || r.status === 403) {
      setOpen(false);
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету, чтобы сохранять запросы." });
    } else {
      setOpen(false);
      toast({ variant: "info", title: "Сохранение недоступно", message: "Модуль сохранённых запросов ещё подключается." });
    }
  }

  const btnSx: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", gap: 6, background: "transparent", color: "var(--text-body)",
    border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: compact ? "5px 10px" : "7px 11px",
    cursor: "pointer", fontSize: compact ? "var(--text-xs)" : "var(--text-sm)",
  };

  return (
    <div className="irb-ssmenu" ref={wrapRef}>
      <button type="button" style={btnSx} onClick={toggle} aria-expanded={open} title="Сохранить текущий запрос">
        <Icon name="save" size={compact ? 14 : 15} /> Сохранить запрос
      </button>
      {open && (
        <div className="irb-ssmenu__pop" role="dialog" aria-label="Сохранить запрос" onClick={(e) => e.stopPropagation()}>
          <div className="irb-ssmenu__hd">Название запроса</div>
          <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Например: книги по Python"
              onKeyDown={(e) => { if (e.key === "Enter") save(); }} aria-label="Название сохранённого запроса"
              style={{ width: "100%", boxSizing: "border-box", padding: "8px 11px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", fontSize: "var(--text-sm)", background: "var(--surface-card,#fff)", color: "var(--text-body)" }} />
            <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
              {prefixLabel(prefix)} · «{query}» · база {db}
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Отмена</Button>
              <Button size="sm" iconLeft="save" loading={busy} onClick={save}>Сохранить</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Общий хук загрузки/удаления списка сохранённых запросов.
function useSavedSearches(refreshKey?: number) {
  const [items, setItems] = React.useState<SavedSearch[] | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const load = React.useCallback(async () => {
    const r = await api.savedSearches();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setItems(r.json.data.items); setUnavailable(false);
    } else { setItems([]); setUnavailable(true); }
  }, []);
  React.useEffect(() => { load(); }, [load, refreshKey]);
  return { items, setItems, unavailable, load };
}

async function deleteSaved(id: string | number, setItems: React.Dispatch<React.SetStateAction<SavedSearch[] | null>>, toast: Toast) {
  let removed: SavedSearch | undefined;
  setItems((list) => { removed = (list || []).find((x) => x.id === id); return (list || []).filter((x) => x.id !== id); });
  const r = await api.deleteSavedSearch(id);
  if (r.status !== 200) {
    if (removed) setItems((list) => [...(list || []), removed!]);
    toast({ variant: "error", title: "Не удалось удалить запрос", message: "Повторите попытку позже." });
  }
}

// Выпадающее меню сохранённых запросов (шапка/тулбар).
export function SavedSearchMenu({ toast, onRun, refreshKey }: {
  toast: Toast; onRun: (s: SavedSearch) => void; refreshKey?: number;
}) {
  const [open, setOpen] = React.useState(false);
  const { items, setItems, unavailable } = useSavedSearches(refreshKey);
  const wrapRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc); document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  // Модуль недоступен или список пуст → не показываем контрол вовсе.
  if (unavailable || !items || items.length === 0) return null;

  const btnSx: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", gap: 6, background: "transparent", color: "var(--text-body)",
    border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, padding: "7px 11px", cursor: "pointer", fontSize: "var(--text-sm)",
  };

  return (
    <div className="irb-ssmenu" ref={wrapRef}>
      <button type="button" style={btnSx} onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="menu" title="Сохранённые запросы">
        <Icon name="bookmark" size={15} /> Мои запросы <Icon name="chevron-down" size={13} />
      </button>
      {open && (
        <div className="irb-ssmenu__pop" role="menu" onClick={(e) => e.stopPropagation()}>
          <div className="irb-ssmenu__hd">Сохранённые запросы</div>
          <div className="irb-ssmenu__list">
            {items.map((s) => (
              <div key={s.id} className="irb-ssrow" role="menuitem">
                <button type="button" className="irb-ssrow__main" onClick={() => { setOpen(false); onRun(s); }}>
                  <span className="irb-ssrow__name">{s.name}</span>
                  <span className="irb-ssrow__meta">{prefixLabel(s.prefix)} · «{s.query}» · {s.db}</span>
                </button>
                <button type="button" className="irb-ssrow__del" aria-label="Удалить запрос" title="Удалить запрос"
                  onClick={() => deleteSaved(s.id, setItems, toast)}>
                  <Icon name="trash" size={15} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Раздел кабинета «Сохранённые запросы».
export function SavedSearchesPanel({ cardSx, h2Sx, toast, onRun, onUnavailable, refreshKey, standalone }: {
  cardSx: React.CSSProperties; h2Sx: React.CSSProperties; toast: Toast;
  onRun: (s: SavedSearch) => void; onUnavailable?: () => void; refreshKey?: number;
  // standalone=true — отдельная вкладка кабинета: при недоступности показываем
  // информер, а не скрываем целиком (null).
  standalone?: boolean;
}) {
  const { items, setItems, unavailable } = useSavedSearches(refreshKey);
  React.useEffect(() => { if (unavailable) onUnavailable?.(); }, [unavailable, onUnavailable]);

  if (unavailable) {
    if (!standalone) return null;
    return (
      <section aria-labelledby="cab-saved">
        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
          <h2 id="cab-saved" style={h2Sx}>Сохранённые запросы</h2>
        </div>
        <div style={cardSx}>
          <EmptyState icon="search" title="Запросы пока недоступны" description="Модуль сохранённых запросов ещё подключается. Загляните позже." />
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="cab-saved">
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
        <h2 id="cab-saved" style={h2Sx}>Сохранённые запросы</h2>
        {items && items.length > 0 && (
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>· {items.length}</span>
        )}
      </div>

      {items === null ? (
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", padding: "4px 2px" }}>Загрузка запросов…</div>
      ) : items.length === 0 ? (
        <div style={cardSx}>
          <EmptyState icon="search" title="Сохранённых запросов нет" description="Сохраните поиск кнопкой «Сохранить запрос» на странице результатов — он появится здесь." />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((s) => (
            <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 14, ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: "12px 16px" }}>
              <span aria-hidden="true" style={{ width: 38, height: 38, flex: "none", borderRadius: 11, background: "var(--accent-weak,var(--accent-tint))", border: "1px solid var(--accent-weak-border,var(--accent-tint-border))", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)" }}>
                <Icon name="search" size={17} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: "var(--text-sm)", color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{prefixLabel(s.prefix)} · «{s.query}» · база {s.db}</div>
              </div>
              <div style={{ display: "flex", gap: 6, flex: "none" }}>
                <Button size="sm" variant="secondary" iconLeft="search" onClick={() => onRun(s)}>Повторить</Button>
                <button type="button" aria-label="Удалить запрос" title="Удалить запрос" onClick={() => deleteSaved(s.id, setItems, toast)}
                  style={{ background: "none", border: "1px solid var(--border-strong,#cdd3da)", borderRadius: 8, cursor: "pointer", color: "var(--text-subtle)", padding: "0 9px" }}>
                  <Icon name="trash" size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
