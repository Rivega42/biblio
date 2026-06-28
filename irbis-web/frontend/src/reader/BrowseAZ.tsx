// Указатель A–Z (#240) — перебор авторов по первой букве со счётчиками. Данные
// из GET /api/browse (own-store каталог, 700^a). Клик по букве раскрывает её
// термины; клик по термину ведёт в поиск автора (onSearch("A", термин)). Если
// каталог пуст (404/нет терминов) — блок не рендерится (graceful degrade). Стиль
// на Biblio-токенах, как Rubricator.
import React from "react";
import { api } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const CSS = `
.irb-az{margin:0;}
.irb-az__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;flex-wrap:wrap;}
.irb-az__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-az__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-az__letters{display:flex;flex-wrap:wrap;gap:6px;}
.irb-az__l{min-width:32px;padding:6px 9px;border:1px solid var(--border-subtle);border-radius:var(--radius-md,8px);
  background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui,inherit);font-size:var(--text-sm);
  font-weight:var(--weight-semibold,600);cursor:pointer;transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-az__l:hover{background:var(--surface-sunken);}
.irb-az__l--on{background:var(--accent,#2f5d62);color:var(--accent-fg,#fff);border-color:var(--accent,#2f5d62);}
.irb-az__l:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
.irb-az__terms{margin-top:12px;display:flex;flex-direction:column;gap:2px;border:1px solid var(--border-subtle);
  border-radius:var(--radius-lg,12px);background:var(--surface-card);padding:8px;max-height:320px;overflow-y:auto;}
.irb-az__t{display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;background:none;border:none;
  padding:8px 10px;border-radius:var(--radius-md,8px);cursor:pointer;text-align:left;font-family:inherit;color:var(--text-body);
  transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-az__t:hover{background:var(--surface-sunken);}
.irb-az__t:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
.irb-az__term{font-size:var(--text-sm);line-height:1.3;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-az__count{flex:none;font-size:var(--text-xs);color:var(--text-subtle);background:var(--surface-sunken);
  border-radius:var(--radius-pill,999px);padding:1px 9px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-az-css")) {
  const s = document.createElement("style"); s.id = "irb-az-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function BrowseAZ({ db, onSearch }: { db: string; onSearch: (prefix: string, query: string) => void }) {
  const [data, setData] = React.useState<{ letters: string[]; buckets: Record<string, { term: string; count: number }[]> } | null>(null);
  const [active, setActive] = React.useState<string | null>(null);

  React.useEffect(() => {
    let alive = true;
    setData(null); setActive(null);
    (async () => {
      const r = await api.browseIndex(db, "700", "a");
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.letters)) setData(r.json.data);
      else setData({ letters: [], buckets: {} });
    })();
    return () => { alive = false; };
  }, [db]);

  if (data === null || !data.letters.length) return null; // загрузка / пусто — не показываем
  const terms = active ? (data.buckets[active] || []) : [];

  return (
    <section className="irb-az" aria-label="Указатель авторов A–Z">
      <div className="irb-az__head">
        <h2 className="irb-az__title">Указатель авторов</h2>
        <span className="irb-az__sub">выберите букву — перейдите к автору</span>
      </div>
      <div className="irb-az__letters" role="group" aria-label="Буквы">
        {data.letters.map((l) => (
          <button key={l} type="button"
            className={"irb-az__l" + (active === l ? " irb-az__l--on" : "")}
            aria-pressed={active === l}
            onClick={() => setActive((cur) => (cur === l ? null : l))}>{l}</button>
        ))}
      </div>
      {active && (
        <div className="irb-az__terms" role="list">
          {terms.length
            ? terms.map((t, i) => (
                <button key={t.term + i} type="button" role="listitem" className="irb-az__t"
                  onClick={() => onSearch("A", t.term)}
                  aria-label={"Автор «" + t.term + "» — " + t.count + " — перейти к поиску"}>
                  <span className="irb-az__term">{t.term}</span>
                  <span className="irb-az__count">{t.count}</span>
                </button>
              ))
            : <span style={{ padding: "8px 10px", fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>Нет терминов на «{active}».</span>}
        </div>
      )}
    </section>
  );
}
