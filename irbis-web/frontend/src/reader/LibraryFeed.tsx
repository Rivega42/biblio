// Новости / события (G1+) — два смежных блока главной, питающихся редактируемым
// per-tenant контентом (tenantContent):
//   LibraryNews   — «Новости библиотеки»: карточки заголовок/дата/краткий текст;
//   LibraryEvents — «События и выставки»: карточки с датой, местом и типом.
// Контент в пилоте задаётся библиотекой (сид-набор СПб ГТБ) и помечен пометкой
// «редактируется библиотекой». Сетевых вызовов нет → блоки устойчивы; при пустом
// наборе блок не рендерится (грациозная деградация).
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";
import { getTenantContent, fmtNewsDate } from "./tenantContent";
import type { EventItem } from "./tenantContent";
import type { IconName } from "../../components/icon/Icon";

const CSS = `
.irb-feed{margin:0;}
.irb-feed__head{display:flex;align-items:center;gap:10px;margin:0 0 12px;flex-wrap:wrap;}
.irb-feed__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-feed__sub{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-feed__edit{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:999px;
  background:var(--surface-sunken);color:var(--text-subtle);font-size:var(--text-2xs,11px);font-weight:600;letter-spacing:.02em;margin-left:auto;}
.irb-feed__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px;}

.irb-news__card{display:flex;flex-direction:column;gap:8px;background:var(--surface-card,#fff);
  border:1px solid var(--border-subtle);border-radius:var(--radius-xl,16px);padding:16px 18px;box-shadow:var(--shadow-sm);
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-news__card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);}
.irb-news__top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.irb-news__tag{display:inline-flex;align-items:center;gap:4px;background:var(--accent-weak,#eef2f7);color:var(--accent);
  border-radius:999px;padding:2px 9px;font-size:var(--text-2xs,11px);font-weight:600;}
.irb-news__date{font-size:var(--text-xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-news__name{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-base,1rem);line-height:1.25;color:var(--text-strong);margin:0;}
.irb-news__text{font-size:var(--text-sm);color:var(--text-muted,var(--text-secondary));line-height:1.45;margin:0;
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}

.irb-ev__card{display:flex;gap:14px;background:var(--surface-card,#fff);
  border:1px solid var(--border-subtle);border-radius:var(--radius-xl,16px);padding:14px 16px;box-shadow:var(--shadow-sm);
  transition:transform var(--dur,.18s) var(--ease-standard,ease),box-shadow var(--dur,.18s) var(--ease-standard,ease);}
.irb-ev__card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);}
.irb-ev__day{flex:none;width:54px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  border-radius:var(--radius-lg,12px);background:linear-gradient(155deg,var(--accent),var(--accent-hover));color:var(--accent-fg,#fff);
  padding:8px 4px;text-align:center;box-shadow:var(--shadow-sm);}
.irb-ev__d{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);font-size:1.35rem;line-height:1;font-variant-numeric:tabular-nums;}
.irb-ev__m{font-size:var(--text-2xs,11px);text-transform:uppercase;letter-spacing:.04em;opacity:.92;margin-top:2px;}
.irb-ev__body{min-width:0;flex:1;display:flex;flex-direction:column;gap:5px;}
.irb-ev__kind{display:inline-flex;align-items:center;gap:5px;align-self:flex-start;font-size:var(--text-2xs,11px);font-weight:600;
  color:var(--text-subtle);text-transform:uppercase;letter-spacing:.03em;}
.irb-ev__name{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-base,1rem);line-height:1.25;color:var(--text-strong);}
.irb-ev__meta{display:flex;align-items:center;gap:6px;font-size:var(--text-xs);color:var(--text-subtle);}
.irb-ev__when{font-size:var(--text-xs);color:var(--accent);font-weight:600;}
.irb-ev__text{font-size:var(--text-sm);color:var(--text-muted,var(--text-secondary));line-height:1.4;margin:0;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-feed-css")) {
  const s = document.createElement("style"); s.id = "irb-feed-css"; s.textContent = CSS; document.head.appendChild(s);
}

function EditableBadge() {
  // #247: служебный CMS-флаг скрыт от читателя — он выглядел как «сайт недоделан».
  // Вернётся только в режиме редактора (когда появится админ-CMS).
  return null;
}

// --- Новости библиотеки -----------------------------------------------------
export function LibraryNews() {
  const { news, editable } = getTenantContent();
  if (!news.length) return null;
  const items = [...news].sort((a, b) => (b.date || "").localeCompare(a.date || "")).slice(0, 4);

  return (
    <section className="irb-feed" aria-label="Новости библиотеки">
      <div className="irb-feed__head">
        <h2 className="irb-feed__title">Новости библиотеки</h2>
        <span className="irb-feed__sub">анонсы и объявления</span>
        {editable && <EditableBadge />}
      </div>
      <div className="irb-feed__grid">
        {items.map((n) => (
          <article key={n.id} className="irb-news__card">
            <div className="irb-news__top">
              {n.tag && <span className="irb-news__tag"><Icon name="tag" size={10} /> {n.tag}</span>}
              <span className="irb-news__date">{fmtNewsDate(n.date)}</span>
            </div>
            <h3 className="irb-news__name">{n.title}</h3>
            <p className="irb-news__text">{n.excerpt}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

// --- События и выставки -----------------------------------------------------
const EVENT_KIND: Record<EventItem["kind"], { label: string; icon: IconName }> = {
  exhibition: { label: "Выставка", icon: "image" },
  lecture: { label: "Лекция", icon: "book-open" },
  tour: { label: "Экскурсия", icon: "map-pin" },
  concert: { label: "Концерт", icon: "music" },
  meeting: { label: "Встреча", icon: "users" },
};
const RU_MONTH_SHORT = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
function dayMonth(iso: string): { d: string; m: string } {
  const mm = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!mm) return { d: "—", m: "" };
  const mo = +mm[2];
  return { d: String(+mm[3]), m: mo >= 1 && mo <= 12 ? RU_MONTH_SHORT[mo - 1] : "" };
}

export function LibraryEvents() {
  const { events, editable } = getTenantContent();
  if (!events.length) return null;
  const items = [...events].sort((a, b) => (a.date || "").localeCompare(b.date || "")).slice(0, 4);

  return (
    <section className="irb-feed" aria-label="События и выставки">
      <div className="irb-feed__head">
        <h2 className="irb-feed__title">События и выставки</h2>
        <span className="irb-feed__sub">афиша библиотеки</span>
        {editable && <EditableBadge />}
      </div>
      <div className="irb-feed__grid">
        {items.map((e) => {
          const k = EVENT_KIND[e.kind] || EVENT_KIND.meeting;
          const dm = dayMonth(e.date);
          return (
            <article key={e.id} className="irb-ev__card">
              <div className="irb-ev__day" aria-hidden="true">
                <span className="irb-ev__d">{dm.d}</span>
                <span className="irb-ev__m">{dm.m}</span>
              </div>
              <div className="irb-ev__body">
                <span className="irb-ev__kind"><Icon name={k.icon} size={12} /> {k.label}</span>
                <span className="irb-ev__name">{e.title}</span>
                {e.dateLabel && <span className="irb-ev__when">{e.dateLabel}</span>}
                <span className="irb-ev__meta"><Icon name="map-pin" size={13} /> {e.place}</span>
                {e.excerpt && <p className="irb-ev__text">{e.excerpt}</p>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
