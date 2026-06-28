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
import { Exhibits } from "./Exhibits";
import { Collections } from "./Collections";
import { Rubricator } from "./Rubricator";
import { BrowseAZ } from "./BrowseAZ";
import { LibraryNews, LibraryEvents } from "./LibraryFeed";
import { AboutLibrary } from "./AboutLibrary";

// Базовые примеры запросов (онбординг поиска). Дополняются «живыми» рубриками
// из /api/rubricator, если эндпойнт доступен.
const SEED_EXAMPLES = ["Программирование", "История России", "Психология", "Математика", "Менеджмент", "Право"];

const CSS = `
.irb-home{display:flex;flex-direction:column;gap:20px;}
.irb-hero{position:relative;overflow:hidden;border-radius:var(--radius-2xl,22px);
  background:linear-gradient(155deg,var(--accent),var(--accent-hover));
  color:var(--accent-fg,#fff);padding:24px 28px 22px;text-align:center;box-shadow:var(--shadow-md);}
.irb-hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 80% at 50% -10%,rgba(255,255,255,.18),transparent 60%);}
.irb-hero__inner{position:relative;max-width:640px;margin:0 auto;}
.irb-hero__eyebrow{display:inline-flex;align-items:center;gap:7px;font-size:var(--text-xs);font-weight:var(--weight-semibold,600);
  text-transform:uppercase;letter-spacing:.06em;background:rgba(255,255,255,.16);padding:5px 12px;border-radius:var(--radius-pill,999px);}
.irb-hero__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);
  font-size:clamp(1.3rem,2.6vw,1.9rem);line-height:1.1;letter-spacing:-.02em;margin:8px 0 5px;}
.irb-hero__lead{font-size:var(--text-sm,.95rem);opacity:.92;margin:0 0 14px;line-height:1.4;}
.irb-hero__search{background:var(--surface-card);border-radius:var(--radius-xl,16px);padding:10px;
  box-shadow:var(--shadow-lg);display:flex;gap:8px;align-items:stretch;text-align:left;}
.irb-hero__field{flex:none;min-width:140px;}
.irb-hero__bar{flex:1;min-width:0;}
.irb-home__examples{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px;}
.irb-home__exlabel{width:100%;text-align:center;font-size:var(--text-xs);opacity:.85;margin-bottom:2px;}
.irb-hero-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.16);
  color:var(--accent-fg,#fff);border:1px solid rgba(255,255,255,.34);border-radius:var(--radius-pill,999px);
  padding:6px 14px;font-size:var(--text-sm);cursor:pointer;font-family:var(--font-ui,inherit);
  transition:background-color var(--dur,.18s) var(--ease-standard,ease);}
.irb-hero-chip:hover{background:rgba(255,255,255,.28);}
.irb-hero-chip:focus-visible{outline:2px solid #fff;outline-offset:2px;}
.irb-hero__scope{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:12px;flex-wrap:wrap;}
.irb-hero__scopelabel{font-size:var(--text-sm);opacity:.92;}
.irb-hero__scopesel{background:rgba(255,255,255,.16);color:var(--accent-fg,#fff);
  border:1px solid rgba(255,255,255,.38);border-radius:var(--radius-pill,999px);
  padding:6px 30px 6px 14px;font-family:var(--font-ui,inherit);font-size:var(--text-sm);cursor:pointer;
  appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 11px center;}
.irb-hero__scopesel:focus-visible{outline:2px solid #fff;outline-offset:2px;}
.irb-hero__scopesel option{color:var(--text-body);background:var(--surface-card);}
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
  { code: "ALL", label: "Везде" }, { code: "A", label: "Автор" },
  { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
];
// «Во всех базах» — то же значение, что ALL_DBS в App.tsx (#255 п.2).
const ALL_BASES = "__ALL__";

const DB_ICONS: Record<string, string> = { IBIS: "book", IMAGE: "images", PERIO: "newspaper", ARCH: "archive" };

export function HomeScreen({
  databases, db, onPickDb, onSearch, onOpen,
}: {
  databases: DbItem[];
  db: string;
  onPickDb: (code: string) => void;
  onSearch: (prefix: string, query: string, base?: string) => void;
  onOpen: (mfn: number, db: string) => void;
}) {
  const [prefix, setPrefix] = React.useState("ALL");
  const [q, setQ] = React.useState("");
  const [base, setBase] = React.useState(ALL_BASES);   // #255 п.2: дефолт — во всех базах
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

  const submit = (query: string) => { const v = query.trim(); if (v) onSearch(prefix, v, base); };

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

          {/* #255 п.2: выбор базы под поиском; по умолчанию — во всех базах сразу. */}
          {publicDbs.length > 1 && (
            <div className="irb-hero__scope" role="group" aria-label="База поиска">
              <span className="irb-hero__scopelabel">Искать в:</span>
              <select className="irb-hero__scopesel" aria-label="Выбор базы поиска"
                value={base} onChange={(e) => setBase(e.target.value)}>
                <option value={ALL_BASES}>Во всех базах</option>
                {publicDbs.map((d) => <option key={d.code} value={d.code}>{d.name || d.code}</option>)}
              </select>
            </div>
          )}

          <div className="irb-home__examples" role="group" aria-label="Примеры запросов">
            <span className="irb-home__exlabel">Популярные запросы</span>
            {examples.map((ex) => (
              <button key={ex} type="button" className="irb-hero-chip"
                onClick={() => { setQ(ex); onSearch(prefix, ex, base); }}>
                <Icon name="search" size={13} /> {ex}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Тематические подборки (театральная специфика, конфиг арендатора) ===== */}
      <Collections onSearch={onSearch} />

      {/* ===== Витрина новых поступлений (G2) — живые данные /api/showcase ===== */}
      <Showcase db={db} onOpen={onOpen} />

      {/* ===== Виртуальные выставки (трек «Оцифровка») — /api/exhibits ===== */}
      <Exhibits db={db} onOpen={onOpen} />

      {/* ===== Рубрикатор «Просмотр по разделам» — живой словарь /api/rubricator ===== */}
      <Rubricator db={db} onSearch={onSearch} />

      {/* ===== Указатель авторов A–Z (#240) — own-store /api/browse ===== */}
      <BrowseAZ db={db} onSearch={onSearch} />

      {/* Селектор баз перенесён под строку поиска (hero, #255 п.2) — здесь больше
          не дублируем «Где искать», чтобы не было двух конкурирующих выборов базы. */}

      {/* ===== Новости + события (редактируемый per-tenant контент) ===== */}
      <LibraryNews />
      <LibraryEvents />

      {/* ===== О библиотеке (часы / контакты / о фонде) ===== */}
      <AboutLibrary />
    </div>
  );
}
