// «Вы недавно смотрели» (#133) — блок на discovery-лендинге портала из истории
// чтения читателя (GET /api/history). Только для читательской сессии; для гостя,
// при 404/501/403 или пустой истории — блок не рендерится (лендинг не ломается).
import React from "react";
import { api } from "../api";
import type { HistoryItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

export function RecentlyViewed({ onOpen }: { onOpen: (db: string, mfn: number) => void }) {
  const [items, setItems] = React.useState<HistoryItem[] | null>(null);
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.history();
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items) && r.json.data.items.length) {
        setItems(r.json.data.items.slice(0, 8));
      } else {
        setItems([]); // гость / 404 / пусто → скрыто
      }
    })();
    return () => { alive = false; };
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <section aria-label="Вы недавно смотрели" style={{ margin: "4px 0" }}>
      <h2 style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-xl,1.25rem)", letterSpacing: "-.02em", margin: "0 0 12px", display: "inline-flex", alignItems: "center", gap: 8 }}>
        <Icon name="clock" size={18} /> Вы недавно смотрели
      </h2>
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        {items.map((it, i) => (
          <button key={it.db + ":" + it.mfn + ":" + i} type="button" onClick={() => onOpen(it.db, it.mfn)}
            aria-label={"Открыть: " + (it.title || "запись " + it.mfn)}
            style={{ flex: "none", width: 200, textAlign: "left", cursor: "pointer", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg,13px)", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6, fontFamily: "inherit" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-2xs,11px)", color: "var(--text-subtle)" }}>
              <Icon name="book" size={12} /> {it.db}
            </span>
            <span style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              {it.title || "Запись № " + it.mfn}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
