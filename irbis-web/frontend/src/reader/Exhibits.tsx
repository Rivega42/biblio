// Виртуальные выставки (трек «Оцифровка», G2+) — горизонтальная полка
// опубликованных кураторских подборок. Данные из GET /api/exhibits (только
// published-витрина); клик по выставке раскрывает её позиции из
// GET /api/exhibits/{slug} (записи каталога + опц. оцифрованный образ), клик по
// позиции открывает запись через onOpen(mfn, db). Если эндпойнта нет (404) или
// опубликованных выставок нет — блок не рендерится (graceful degrade). Стиль
// строго на Biblio-токенах; обложек у выставок нет — тонированные подложки.
import React from "react";
import { api } from "../api";
import type { ExhibitSummary, ExhibitItem, IiifManifest } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import type { DocPage } from "./DocViewer";
import { IiifViewer } from "./IiifViewer";

// IIIF-манифест -> страницы для DocViewer. Из каждой канвы берём URL образа
// (painting-аннотация: items[0].items[0].body.id) и подпись (label.<lang>[0]).
// Канвы без URL пропускаем.
function manifestToPages(manifest: IiifManifest | undefined): DocPage[] {
  const canvases = manifest && Array.isArray(manifest.items) ? manifest.items : [];
  const pages: DocPage[] = [];
  canvases.forEach((c, i) => {
    const anyc = c as any;
    let url: string | undefined;
    try { url = anyc?.items?.[0]?.items?.[0]?.body?.id; } catch { url = undefined; }
    let name: string | undefined;
    const lbl = anyc?.label;
    if (lbl && typeof lbl === "object") {
      const first = Object.values(lbl)[0];
      if (Array.isArray(first) && first.length) name = String(first[0]);
    }
    if (url) pages.push({ name: name ? "Стр. " + name : "Стр. " + (i + 1), url, kind: "image" });
  });
  return pages;
}

const TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

const CSS = `
.irb-exh{margin:0;}
.irb-exh__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;flex-wrap:wrap;}
.irb-exh__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-exh__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-exh__rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 12px;scroll-snap-type:x mandatory;scrollbar-width:thin;}
.irb-exh__card{flex:none;width:236px;min-height:138px;scroll-snap-align:start;display:flex;flex-direction:column;
  justify-content:flex-end;gap:6px;position:relative;overflow:hidden;
  border:2px solid transparent;border-radius:var(--radius-xl,16px);padding:16px;cursor:pointer;text-align:left;
  color:#fff;font-family:inherit;box-shadow:var(--shadow-md);
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-exh__card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);}
.irb-exh__card:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-exh__card[aria-expanded="true"]{border-color:#fff;}
.irb-exh__card::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 90% at 85% 0%,rgba(255,255,255,.20),transparent 60%);}
.irb-exh__ic{position:relative;width:38px;height:38px;border-radius:11px;background:rgba(255,255,255,.20);
  display:inline-flex;align-items:center;justify-content:center;margin-bottom:auto;}
.irb-exh__name{position:relative;font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);
  font-size:var(--text-lg,1.05rem);line-height:1.15;text-shadow:0 1px 4px rgba(0,0,0,.28);}
.irb-exh__desc{position:relative;font-size:var(--text-xs);opacity:.94;line-height:1.3;text-shadow:0 1px 3px rgba(0,0,0,.3);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.irb-exh__go{position:relative;display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs,11px);
  font-weight:var(--weight-semibold,600);opacity:.92;margin-top:2px;}
.irb-exh__panel{margin-top:4px;border:1px solid var(--border-subtle);border-radius:var(--radius-lg,12px);
  background:var(--surface-card);box-shadow:var(--shadow-sm);padding:14px 16px;}
.irb-exh__panelhead{display:flex;align-items:baseline;gap:8px;margin:0 0 10px;flex-wrap:wrap;}
.irb-exh__panelttl{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-lg,1.05rem);margin:0;color:var(--text-strong);}
.irb-exh__paneldesc{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-exh__items{display:flex;flex-direction:column;gap:6px;margin:0;padding:0;list-style:none;}
.irb-exh__itemrow{display:flex;align-items:stretch;gap:6px;}
.irb-exh__digi{flex:none;display:inline-flex;align-items:center;gap:5px;background:none;
  border:1px solid var(--border-subtle);border-radius:var(--radius-md,8px);padding:0 11px;cursor:pointer;
  font-family:inherit;font-size:var(--text-xs);color:var(--accent);white-space:nowrap;
  transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-exh__digi:hover:not(:disabled){background:var(--surface-sunken);}
.irb-exh__digi:disabled{opacity:.55;cursor:default;color:var(--text-subtle);}
.irb-exh__digi:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
.irb-exh__item{flex:1;min-width:0;display:flex;align-items:flex-start;gap:10px;width:100%;background:none;border:none;
  padding:8px 10px;border-radius:var(--radius-md,8px);cursor:pointer;text-align:left;font-family:inherit;
  color:var(--text-body);transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-exh__item:hover{background:var(--surface-sunken);}
.irb-exh__item:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:1px;}
.irb-exh__num{flex:none;width:22px;height:22px;border-radius:6px;background:var(--surface-sunken);color:var(--text-subtle);
  font-size:var(--text-2xs,11px);font-weight:var(--weight-bold,700);display:inline-flex;align-items:center;justify-content:center;}
.irb-exh__cap{flex:1;min-width:0;font-size:var(--text-sm);line-height:1.3;}
.irb-exh__asset{display:inline-flex;align-items:center;gap:4px;font-size:var(--text-2xs,11px);color:var(--accent);margin-top:2px;}
.irb-exh__empty{font-size:var(--text-sm);color:var(--text-subtle);margin:0;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-exh-css")) {
  const s = document.createElement("style"); s.id = "irb-exh-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function Exhibits({ db, onOpen }: { db: string; onOpen: (mfn: number, db: string) => void }) {
  const [list, setList] = React.useState<ExhibitSummary[] | null>(null);
  const [open, setOpen] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<ExhibitItem[] | null>(null);
  // Встроенный IIIF-просмотрщик: страницы открытой записи + статусы по позициям
  // ('loading' пока тянем манифест, 'empty' если оцифрованных образов нет).
  const [viewer, setViewer] = React.useState<{ pages: DocPage[]; title: string } | null>(null);
  const [digi, setDigi] = React.useState<Record<number, "loading" | "empty">>({});
  // Подписка читателя на выставку (#240): 'busy'|'ok'|'err'(не читатель) по slug.
  const [subState, setSubState] = React.useState<Record<string, "busy" | "ok" | "err">>({});

  const subscribe = async (slug: string) => {
    setSubState((s) => ({ ...s, [slug]: "busy" }));
    const r = await api.collectionSubscribe({ kind: "exhibit", ref: slug });
    setSubState((s) => ({ ...s, [slug]: (r.json?.ok && (r.json.data as any)?.subscription) ? "ok" : "err" }));
  };

  const openDigitized = async (it: ExhibitItem) => {
    if (digi[it.id] === "loading") return;
    setDigi((d) => ({ ...d, [it.id]: "loading" }));
    const r = await api.iiifManifest(it.db || db, it.mfn);
    const pages = r.json?.ok && r.json.data ? manifestToPages(r.json.data.manifest) : [];
    if (pages.length) {
      setDigi((d) => { const n = { ...d }; delete n[it.id]; return n; });
      setViewer({ pages, title: it.caption || ("Запись · MFN " + it.mfn) });
    } else {
      setDigi((d) => ({ ...d, [it.id]: "empty" })); // нет оцифрованных образов
    }
  };

  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.exhibits();
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setList(r.json.data.items);
      else setList([]); // 404 / error → пусто, блок скрывается
    })();
    return () => { alive = false; };
  }, []);

  const toggle = async (slug: string) => {
    if (open === slug) { setOpen(null); setItems(null); return; }
    setOpen(slug); setItems(null);
    const r = await api.exhibit(slug);
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) setItems(r.json.data.items);
    else setItems([]);
  };

  if (list === null || !list.length) return null; // загрузка / нет опубликованных — не показываем

  const active = list.find((e) => e.slug === open) || null;

  return (
    <section className="irb-exh" aria-label="Виртуальные выставки">
      <div className="irb-exh__head">
        <h2 className="irb-exh__title">Виртуальные выставки</h2>
        <span className="irb-exh__sub">кураторские подборки из фонда — нажмите, чтобы открыть</span>
      </div>
      <div className="irb-exh__rail" role="list">
        {list.map((e, i) => (
          <button
            key={e.slug} type="button" role="listitem" className="irb-exh__card"
            aria-expanded={open === e.slug} onClick={() => toggle(e.slug)}
            aria-label={"Выставка «" + e.title + "» — открыть подборку"}
            style={{ background: "linear-gradient(150deg," + TINTS[i % TINTS.length] + ",rgba(0,0,0,.5))" }}
          >
            <span className="irb-exh__ic"><Icon name="image" size={20} /></span>
            <span className="irb-exh__name">{e.title}</span>
            {e.description && <span className="irb-exh__desc">{e.description}</span>}
            <span className="irb-exh__go">
              {open === e.slug ? "Свернуть" : "Открыть выставку"} <Icon name={open === e.slug ? "chevron-up" : "arrow-right"} size={12} />
            </span>
          </button>
        ))}
      </div>

      {active && (
        <div className="irb-exh__panel">
          <div className="irb-exh__panelhead">
            <h3 className="irb-exh__panelttl">{active.title}</h3>
            {active.description && <span className="irb-exh__paneldesc">{active.description}</span>}
            <span style={{ flex: 1 }} />
            <button type="button" className="irb-exh__digi"
              onClick={() => subscribe(active.slug)}
              disabled={subState[active.slug] === "busy" || subState[active.slug] === "ok"}
              title="Подписаться на обновления выставки"
              aria-label={"Подписаться на выставку " + active.title}>
              <Icon name={subState[active.slug] === "ok" ? "check" : "bell"} size={14} />
              {subState[active.slug] === "ok" ? "Вы подписаны"
                : subState[active.slug] === "err" ? "Войдите как читатель"
                : "Подписаться"}
            </button>
          </div>
          {items === null
            ? <p className="irb-exh__empty">Загрузка подборки…</p>
            : !items.length
              ? <p className="irb-exh__empty">В этой выставке пока нет позиций.</p>
              : (
                <ul className="irb-exh__items">
                  {items.map((it, i) => (
                    <li key={it.id} className="irb-exh__itemrow">
                      <button type="button" className="irb-exh__item"
                        onClick={() => onOpen(it.mfn, it.db || db)}
                        aria-label={"Открыть запись" + (it.caption ? ": " + it.caption : "")}>
                        <span className="irb-exh__num">{i + 1}</span>
                        <span className="irb-exh__cap">
                          {it.caption || ("Запись " + (it.db || db) + " · MFN " + it.mfn)}
                          {it.asset_ref && <span className="irb-exh__asset"><Icon name="image" size={11} /> оцифрованный образ</span>}
                        </span>
                      </button>
                      <button type="button" className="irb-exh__digi"
                        onClick={() => openDigitized(it)}
                        disabled={digi[it.id] === "loading" || digi[it.id] === "empty"}
                        aria-label={"Смотреть оцифровку записи MFN " + it.mfn}
                        title="Постраничный просмотр оцифрованных образов">
                        <Icon name={digi[it.id] === "loading" ? "clock" : "images"} size={14} />
                        {digi[it.id] === "empty" ? "нет страниц" : "Оцифровка"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
        </div>
      )}

      {viewer && (
        <IiifViewer pages={viewer.pages} title={viewer.title} onClose={() => setViewer(null)} />
      )}
    </section>
  );
}
