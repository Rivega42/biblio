// Главная-лендинг читательского портала (G1) — «фасад» discovery перед любым
// поиском: hero со слоганом и крупным полем поиска по центру, ряд примеров-чипов
// запросов (G3), витрина новых поступлений (G2, компонент Showcase) и богатый
// селектор баз с названием/счётчиком (G17, компонент DatabaseSelector).
//
// Экран НЕ дублирует поисковую логику App.tsx: он лишь собирает запрос и зовёт
// onSearch(prefix, query) / onPickDb(code) / onOpen(mfn, db). Стиль — Biblio-токены.
import React from "react";
import type { DbItem } from "../api";
import { api } from "../api";
import type { Term } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import { SearchBar } from "../../components/catalog/SearchBar.jsx";
import { DatabaseSelector } from "../../components/catalog/DatabaseSelector.jsx";
import { Showcase } from "./Showcase";

// Базовые примеры запросов (онбординг поиска). Дополняются «живыми» рубриками
// из /api/rubricator, если эндпойнт доступен.
const SEED_EXAMPLES = ["Программирование", "История России", "Психология", "Математика", "Менеджмент", "Право"];

const CSS = `
.irb-home{display:flex;flex-direction:column;gap:34px;}
.irb-hero{position:relative;overflow:hidden;border-radius:var(--radius-2xl,22px);
  background:linear-gradient(155deg,var(--accent),var(--accent-hover));
  color:var(--accent-fg,#fff);padding:46px 32px 40px;text-align:center;box-shadow:var(--shadow-md);}
.irb-hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 80% at 50% -10%,rgba(255,255,255,.18),transparent 60%);}
.irb-hero__inner{position:relative;max-width:640px;margin:0 auto;}
.irb-hero__eyebrow{display:inline-flex;align-items:center;gap:7px;font-size:var(--text-xs);font-weight:var(--weight-semibold,600);
  text-transform:uppercase;letter-spacing:.06em;background:rgba(255,255,255,.16);padding:5px 12px;border-radius:var(--radius-pill,999px);}
.irb-hero__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);
  font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.12;letter-spacing:-.02em;margin:16px 0 8px;}
.irb-hero__lead{font-size:var(--text-md,1rem);opacity:.92;margin:0 0 22px;line-height:1.5;}
.irb-hero__search{background:var(--surface-card);border-radius:var(--radius-xl,16px);padding:10px;
  box-shadow:var(--shadow-lg);display:flex;gap:8px;align-items:stretch;text-align:left;}
.irb-hero__field{flex:none;min-width:140px;}
.irb-hero__bar{flex:1;min-width:0;}
.irb-home__examples{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:18px;}
.irb-home__exlabel{width:100%;text-align:center;font-size:var(--text-xs);opacity:.85;margin-bottom:2px;}
.irb-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.16);
  color:var(--accent-fg,#fff);border:1px solid rgba(255,255,255,.34);border-radius:var(--radius-pill,999px);
  padding:6px 14px;font-size:var(--text-sm);cursor:pointer;font-family:var(--font-ui,inherit);
  transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-chip:hover{background:rgba(255,255,255,.28);}
.irb-chip:focus-visible{outline:2px solid #fff;outline-offset:2px;}
.irb-home__pick{max-width:520px;margin:0 auto;width:100%;display:flex;flex-direction:column;gap:8px;}
.irb-home__picklabel{font-size:var(--text-sm);font-weight:var(--weight-semibold,600);color:var(--text-strong);text-align:center;}
@media (max-width:560px){
  .irb-hero__search{flex-direction:column;}
  .irb-hero__field{min-width:0;}
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-home-css")) {
  const s = document.createElement("style"); s.id = "irb-home-css"; s.textContent = CSS; document.head.appendChild(s);
}

const PREFIX_OPTS = [
  { code: "K", label: "Везде" }, { code: "A", label: "Автор" },
  { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
];

const DB_ICONS: Record<string, string> = { IBIS: "book", IMAGE: "images", PERIO: "newspaper", ARCH: "archive" };

export function HomeScreen({
  databases, db, onPickDb, onSearch, onOpen,
}: {
  databases: DbItem[];
  db: string;
  onPickDb: (code: string) => void;
  onSearch: (prefix: string, query: string) => void;
  onOpen: (mfn: number, db: string) => void;
}) {
  const [prefix, setPrefix] = React.useState("K");
  const [q, setQ] = React.useState("");
  const [examples, setExamples] = React.useState<string[]>(SEED_EXAMPLES);

  // Подмешиваем «живые» рубрики из словаря (если backend отдаёт). Не критично:
  // при 404 остаются SEED_EXAMPLES.
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.rubricator(db, "K", 8);
      if (!alive) return;
      const terms: Term[] = r.json?.ok && r.json.data ? (r.json.data.terms || []) : [];
      const live = terms
        .map((t) => (t.term || "").replace(/^[A-ZА-Я]=/, "").trim())
        .filter((s) => s.length >= 3 && s.length <= 28);
      if (live.length >= 3) setExamples(Array.from(new Set(live)).slice(0, 6));
      else setExamples(SEED_EXAMPLES);
    })();
    return () => { alive = false; };
  }, [db]);

  const publicDbs = databases.filter((d) => d.public);
  const selectorDbs = publicDbs.map((d) => ({
    id: d.code,
    name: d.name || d.code,
    icon: d.icon || DB_ICONS[d.code] || "book",
    description: d.description,
    count: d.count,
  }));

  const submit = (query: string) => { const v = query.trim(); if (v) onSearch(prefix, v); };

  return (
    <div className="irb-home">
      {/* ===== Hero + поиск ===== */}
      <section className="irb-hero" aria-label="Поиск по каталогу">
        <div className="irb-hero__inner">
          <span className="irb-hero__eyebrow"><Icon name="book-open" size={14} /> Электронный каталог</span>
          <h1 className="irb-hero__title">Найдите нужное издание в библиотеке</h1>
          <p className="irb-hero__lead">Книги, статьи, электронные версии и архивные материалы — поиск по всему фонду в одном окне.</p>

          <div className="irb-hero__search">
            <div className="irb-hero__field">
              <select
                aria-label="Область поиска" value={prefix} onChange={(e) => setPrefix(e.target.value)}
                style={{ width: "100%", height: "100%", boxSizing: "border-box", padding: "0 12px", borderRadius: "var(--radius-md,8px)", border: "1px solid var(--border-strong,#cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)", fontFamily: "var(--font-ui,inherit)", fontSize: "var(--text-sm)" }}
              >
                {PREFIX_OPTS.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
              </select>
            </div>
            <div className="irb-hero__bar">
              <SearchBar value={q} onChange={setQ} onSearch={submit}
                placeholder="Например: основы программирования" buttonLabel="Найти" />
            </div>
          </div>

          <div className="irb-home__examples" role="group" aria-label="Примеры запросов">
            <span className="irb-home__exlabel">Популярные запросы</span>
            {examples.map((ex) => (
              <button key={ex} type="button" className="irb-chip"
                onClick={() => { setQ(ex); onSearch(prefix, ex); }}>
                <Icon name="search" size={13} /> {ex}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Богатый селектор баз (G17) ===== */}
      {selectorDbs.length > 1 && (
        <div className="irb-home__pick">
          <div className="irb-home__picklabel">Где искать</div>
          <DatabaseSelector
            databases={selectorDbs}
            value={[db]}
            title="Электронный каталог и базы данных"
            onChange={(ids: string[]) => {
              // Селектор многозначный по типу; портал ищет в одной базе → берём
              // последнюю изменённую (отличную от текущей) или первую выбранную.
              const next = ids.find((id) => id !== db) || ids[0];
              if (next && next !== db) onPickDb(next);
            }}
          />
        </div>
      )}

      {/* ===== Витрина новых поступлений (G2) ===== */}
      <Showcase db={db} onOpen={onOpen} />
    </div>
  );
}
