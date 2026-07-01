// Морфо-полнотекстовый поиск (#368) — читательская панель портала. Ищет по
// полным текстам/каталогу с морфологией (русский стеммер: «книга»/«книги» →
// одна основа) и ранжированием BM25. Источник рефа: cat:<db>:<mfn> (каталожная
// запись) | ocr:<asset> (распознанный текст оцифровки). Кнопка «похожие» по
// каждому хиту (more_like). При недоступном эндпойнте (404/501) — мягкий информер.
import React from "react";
import { api } from "../api";
import type { FtsHit } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

function refKind(ref: string): { label: string; icon: "scan-line" | "book" } {
  if (ref.startsWith("ocr:")) return { label: "Оцифровка / OCR", icon: "scan-line" };
  return { label: "Каталог", icon: "book" };
}

export function FulltextSearchPanel({ cardSx, h2Sx }: { cardSx: React.CSSProperties; h2Sx: React.CSSProperties }) {
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<FtsHit[] | null>(null);
  const [state, setState] = React.useState<"idle" | "live" | "down">("idle");
  const [busy, setBusy] = React.useState(false);
  const [more, setMore] = React.useState<Record<string, FtsHit[] | null>>({});

  const run = React.useCallback(async (term: string) => {
    const t = term.trim();
    if (!t) { setHits(null); setState("idle"); return; }
    setBusy(true);
    const r = await api.fulltextSearch(t, 25);
    setBusy(false);
    if (r.status === 404 || r.status === 501) { setState("down"); return; }
    setState("live");
    setMore({});
    setHits(r.json?.ok && r.json.data ? r.json.data.hits : []);
  }, []);

  const showMore = async (ref: string) => {
    if (more[ref] !== undefined) { setMore((m) => ({ ...m, [ref]: m[ref] === null ? null : null })); }
    const r = await api.fulltextMoreLike(ref);
    setMore((m) => ({ ...m, [ref]: r.json?.ok && r.json.data ? r.json.data.hits : [] }));
  };

  return (
    <section aria-labelledby="fts-h" style={{ ...cardSx, padding: 18 }}>
      <h2 id="fts-h" style={{ ...h2Sx, margin: "0 0 4px" }}>Поиск по полным текстам</h2>
      <p style={{ margin: "0 0 14px", fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>
        С учётом морфологии (любая словоформа) и ранжированием по релевантности. Ищет в каталоге и распознанных текстах оцифровки.
      </p>
      <form onSubmit={(e) => { e.preventDefault(); run(q); }} style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <div style={{ position: "relative", flex: 1 }}>
          <span style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-subtle)", display: "inline-flex" }}><Icon name="search" size={16} /></span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="например: театральные рукописи"
            aria-label="Запрос полнотекстового поиска"
            style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px 10px 34px", borderRadius: "var(--radius-md,8px)", border: "1px solid var(--border-subtle)", background: "var(--surface-base)", color: "var(--text-strong)", fontFamily: "inherit", fontSize: "var(--text-sm)" }} />
        </div>
        <button type="submit" disabled={busy || !q.trim()}
          style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "0 16px", borderRadius: "var(--radius-md,8px)", border: "none", background: "var(--accent,#2d7d6e)", color: "#fff", cursor: busy || !q.trim() ? "default" : "pointer", opacity: busy || !q.trim() ? 0.6 : 1, fontFamily: "inherit", fontSize: "var(--text-sm)", fontWeight: 600 }}>
          {busy ? "Ищу…" : "Найти"}
        </button>
      </form>

      {state === "down" && <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Полнотекстовый поиск подключается отдельно.</div>}
      {state === "live" && hits && hits.length === 0 && <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Ничего не найдено. Попробуйте другие слова.</div>}
      {state === "live" && hits && hits.length > 0 && (
        <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          {hits.map((h, i) => {
            const k = refKind(h.ref);
            const ml = more[h.ref];
            return (
              <li key={h.ref} style={{ border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md,10px)", padding: "11px 14px" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                  <span style={{ flex: "none", fontSize: "var(--text-xs)", color: "var(--text-subtle)", fontVariantNumeric: "tabular-nums", minWidth: 18 }}>{i + 1}.</span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap" }}>
                      <b style={{ fontSize: "var(--text-base,15px)", color: "var(--text-strong)" }}>{h.title || h.ref}</b>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "var(--text-2xs,11px)", color: "var(--text-subtle)", background: "var(--surface-sunken)", borderRadius: "var(--radius-pill,999px)", padding: "2px 8px" }}>
                        <Icon name={k.icon} size={11} /> {k.label}
                      </span>
                    </span>
                    {h.snippet && (
                      <span style={{ display: "block", marginTop: 4, fontSize: "var(--text-sm)", color: "var(--text-muted)", lineHeight: 1.4 }}>{h.snippet}</span>
                    )}
                    {h.matched && h.matched.length > 0 && (
                      <span style={{ display: "block", marginTop: 3, fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>совпало: {h.matched.join(", ")}</span>
                    )}
                  </span>
                  <span style={{ flex: "none", fontSize: "var(--text-xs)", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }} title="оценка релевантности BM25">{h.score.toFixed(2)}</span>
                  <button type="button" onClick={() => showMore(h.ref)}
                    style={{ flex: "none", display: "inline-flex", alignItems: "center", gap: 5, background: "none", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md,8px)", padding: "5px 10px", cursor: "pointer", color: "var(--text-muted)", fontSize: "var(--text-xs)", fontFamily: "inherit" }}>
                    <Icon name="share" size={12} /> Похожие
                  </button>
                </div>
                {ml && ml.length > 0 && (
                  <ul style={{ listStyle: "none", margin: "10px 0 0 28px", padding: "8px 0 0", borderTop: "1px dashed var(--border-subtle)", display: "flex", flexDirection: "column", gap: 5 }}>
                    {ml.map((m) => (
                      <li key={m.ref} style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", display: "flex", gap: 7 }}>
                        <Icon name={refKind(m.ref).icon} size={12} /> <span style={{ flex: 1, minWidth: 0 }}>{m.title || m.ref}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {ml && ml.length === 0 && (
                  <div style={{ margin: "8px 0 0 28px", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Похожих не найдено.</div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
