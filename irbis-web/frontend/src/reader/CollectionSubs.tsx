// Подписки на коллекции (#240) — раздел читательского кабинета. Time-boxed
// подписки на выставки/коллекции/записи (GET /api/me/collections): что отслеживаю
// и в каком окне дат. Фильтр «только активные»; отмена подписки. Данные
// reader-scoped; при недоступном эндпойнте (404/501) — мягкий информер.
import React from "react";
import { api } from "../api";
import type { CollectionSub } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

type ToastFn = (t: { variant: string; title: string; message?: string }) => void;

const KIND_RU: Record<string, string> = { exhibit: "Выставка", collection: "Коллекция", record: "Запись" };

function fmtWindow(s: CollectionSub): string {
  const f = s.date_from, t = s.date_to;
  if (!f && !t) return "бессрочно";
  if (f && t) return f + " — " + t;
  if (f) return "с " + f;
  return "по " + t;
}

export function CollectionSubsPanel({ cardSx, h2Sx, toast }: { cardSx: React.CSSProperties; h2Sx: React.CSSProperties; toast: ToastFn }) {
  const [items, setItems] = React.useState<CollectionSub[] | null>(null);
  const [state, setState] = React.useState<"live" | "down">("live");
  const [activeOnly, setActiveOnly] = React.useState(false);
  const [busy, setBusy] = React.useState<number | null>(null);

  const load = React.useCallback(async () => {
    const r = await api.collectionSubs(activeOnly);
    if (r.status === 404 || r.status === 501) { setState("down"); return; }
    setState("live");
    if (r.json?.ok && r.json.data) setItems(r.json.data.items); else setItems([]);
  }, [activeOnly]);
  React.useEffect(() => { load(); }, [load]);

  const cancel = async (id: number) => {
    setBusy(id);
    const r = await api.collectionSubCancel(id);
    setBusy(null);
    if (r.json?.ok && (r.json.data as any)?.cancelled) { setItems((x) => (x || []).filter((s) => s.id !== id)); toast({ variant: "success", title: "Подписка отменена" }); }
    else toast({ variant: "error", title: "Не отменено", message: "Повторите попытку." });
  };

  return (
    <section aria-labelledby="cab-subs">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, margin: "0 0 14px", flexWrap: "wrap" }}>
        <h1 id="cab-subs" style={{ ...h2Sx, fontSize: "var(--text-2xl,22px)" }}>Подписки на коллекции</h1>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: "var(--text-sm)", color: "var(--text-subtle)", cursor: "pointer" }}>
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} /> только активные
        </label>
      </div>
      {state === "down"
        ? <div style={{ ...cardSx, padding: 18, color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Раздел подписок подключается отдельно.</div>
        : items === null
          ? <div style={{ ...cardSx, padding: 18, color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Загрузка…</div>
          : items.length === 0
            ? <div style={{ ...cardSx, padding: 18, color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Вы пока не подписаны на коллекции. Подпишитесь со страницы выставки на портале.</div>
            : (
              <div style={{ ...cardSx, padding: 0, overflow: "hidden" }}>
                {items.map((s, i) => (
                  <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderTop: i ? "1px solid var(--border-subtle)" : "none" }}>
                    <span style={{ flex: "none", fontSize: "var(--text-2xs,11px)", fontWeight: 600, padding: "2px 9px", borderRadius: "var(--radius-pill,999px)", background: "var(--surface-sunken)", color: "var(--text-subtle)" }}>{KIND_RU[s.target_kind] || s.target_kind}</span>
                    <span style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 2 }}>
                      <b style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.target_ref}</b>
                      <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>окно: {fmtWindow(s)}</span>
                    </span>
                    <button type="button" onClick={() => cancel(s.id)} disabled={busy === s.id}
                      aria-label={"Отменить подписку на " + s.target_ref}
                      style={{ flex: "none", display: "inline-flex", alignItems: "center", gap: 5, background: "none", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md,8px)", padding: "6px 11px", cursor: "pointer", color: "var(--text-muted)", fontSize: "var(--text-xs)", fontFamily: "inherit" }}>
                      <Icon name="x" size={13} /> Отписаться
                    </button>
                  </div>
                ))}
              </div>
            )}
    </section>
  );
}
