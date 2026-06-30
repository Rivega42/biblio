// «Популярное» — блок на discovery-лендинге: самые открываемые записи по истории
// чтения (GET /api/popular, own-store, public). Виден всем (включая гостя); при
// пустой истории / 404 / 501 — не рендерится. Клик открывает карточку.
import React from "react";
import { api } from "../api";
import type { PopularItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

export function PopularPanel({ onOpen }: { onOpen: (db: string, mfn: number) => void }) {
  const [items, setItems] = React.useState<PopularItem[] | null>(null);
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.popular(undefined, 8);
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items) && r.json.data.items.length) {
        setItems(r.json.data.items);
      } else {
        setItems([]); // 404 / пусто → скрыто
      }
    })();
    return () => { alive = false; };
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <section aria-label="Популярное" style={{ margin: "4px 0" }}>
      <h2 style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-xl,1.25rem)", letterSpacing: "-.02em", margin: "0 0 12px", display: "inline-flex", alignItems: "center", gap: 8 }}>
        <Icon name="trending-up" size={18} /> Популярное
      </h2>
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        {items.map((it) => (
          <button key={it.db + ":" + it.mfn} type="button" onClick={() => onOpen(it.db, it.mfn)}
            aria-label={"Открыть: " + (it.title || "запись " + it.mfn)}
            style={{ flex: "none", width: 210, textAlign: "left", cursor: "pointer", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg,13px)", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6, fontFamily: "inherit" }}>
            <span style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "var(--text-2xs,11px)", color: "var(--text-subtle)" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="book" size={12} /> {it.db}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 3 }} title="число обращений"><Icon name="eye" size={11} /> {it.count}</span>
            </span>
            <span style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              {it.title || "Запись № " + it.mfn}
            </span>
            {it.author && <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.author}</span>}
          </button>
        ))}
      </div>
    </section>
  );
}
