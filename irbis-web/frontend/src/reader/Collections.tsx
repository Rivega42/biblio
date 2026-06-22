// Тематические подборки (G1+) — горизонтальная полка крупных плиток-витрин по
// театральным темам (Театр, Драматургия, Сценография, История театра, …). Каждая
// плитка ведёт в поиск каталога: onSearch(prefix, query). Определения подборок —
// из tenantContent (конфиг арендатора, для пилота — театральная специфика СПб ГТБ).
// Каталожных вызовов нет → блок устойчив и всегда рендерится при наличии подборок.
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";
import { getTenantContent, COVER_TINTS } from "./tenantContent";

const CSS = `
.irb-coll{margin:0;}
.irb-coll__head{display:flex;align-items:baseline;gap:10px;margin:0 0 12px;flex-wrap:wrap;}
.irb-coll__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-coll__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-coll__rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 12px;scroll-snap-type:x mandatory;scrollbar-width:thin;}
.irb-coll__card{flex:none;width:208px;min-height:128px;scroll-snap-align:start;display:flex;flex-direction:column;
  justify-content:flex-end;gap:6px;position:relative;overflow:hidden;
  border:none;border-radius:var(--radius-xl,16px);padding:16px;cursor:pointer;text-align:left;
  color:#fff;font-family:inherit;box-shadow:var(--shadow-md);
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-coll__card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);}
.irb-coll__card:focus-visible{outline:var(--focus-ring-width,2px) solid var(--focus-ring-color,var(--accent));outline-offset:2px;}
.irb-coll__card::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 90% at 85% 0%,rgba(255,255,255,.20),transparent 60%);}
.irb-coll__ic{position:relative;width:38px;height:38px;border-radius:11px;background:rgba(255,255,255,.20);
  display:inline-flex;align-items:center;justify-content:center;margin-bottom:auto;}
.irb-coll__name{position:relative;font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);
  font-size:var(--text-lg,1.05rem);line-height:1.15;text-shadow:0 1px 4px rgba(0,0,0,.28);}
.irb-coll__desc{position:relative;font-size:var(--text-xs);opacity:.94;line-height:1.3;text-shadow:0 1px 3px rgba(0,0,0,.3);}
.irb-coll__go{position:relative;display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs,11px);
  font-weight:var(--weight-semibold,600);opacity:.92;margin-top:2px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-coll-css")) {
  const s = document.createElement("style"); s.id = "irb-coll-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function Collections({ onSearch }: { onSearch: (prefix: string, query: string) => void }) {
  const { collections } = getTenantContent();
  if (!collections.length) return null;

  return (
    <section className="irb-coll" aria-label="Тематические подборки">
      <div className="irb-coll__head">
        <h2 className="irb-coll__title">Тематические подборки</h2>
        <span className="irb-coll__sub">подборки фонда по темам — нажмите, чтобы перейти к поиску</span>
      </div>
      <div className="irb-coll__rail" role="list">
        {collections.map((c) => (
          <button
            key={c.id} type="button" role="listitem" className="irb-coll__card"
            onClick={() => onSearch(c.prefix, c.query)}
            aria-label={"Подборка «" + c.title + "» — перейти к поиску"}
            style={{ background: "linear-gradient(150deg," + COVER_TINTS[c.tint % COVER_TINTS.length] + ",rgba(0,0,0,.5))" }}
          >
            <span className="irb-coll__ic"><Icon name={c.icon} size={20} /></span>
            <span className="irb-coll__name">{c.title}</span>
            <span className="irb-coll__desc">{c.subtitle}</span>
            <span className="irb-coll__go">Смотреть подборку <Icon name="arrow-right" size={12} /></span>
          </button>
        ))}
      </div>
    </section>
  );
}
