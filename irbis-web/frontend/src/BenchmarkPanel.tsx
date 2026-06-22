// ============================================================================
// Сравнение ИРБИС ↔ Biblio — панель метрик скорости для демонстрации на пилоте.
//
// Единственная поверхность продукта в стиле «liquid glass» (стекломорфизм):
// полупрозрачные карточки с backdrop-filter, тонкая светлая граница, мягкая тень,
// градиент-подложка и блик. Остальной продукт остаётся плоским (Стиль A) — поэтому
// все классы изолированы в пространстве имён .irb-bench*, чтобы не задеть .stf__ /
// .adm__ / .cdesk__ и токены Biblio.
//
// Данные замера: POST /api/admin/benchmark/run (super-admin) либо GET /api/admin/
// benchmark (последний кэш). Контракт ответа:
//   { query:{irbis_ms, biblio_ms},
//     circulation:{irbis_ms?, biblio_ms},
//     migration:{records_per_sec, total?},
//     ts }
// Мягкая деградация: эндпойнт ещё не развёрнут (404/501) или недоступен → показываем
// демо-плейсхолдеры с явной плашкой «демо-значения», чтобы панель красиво выглядела
// на пилоте даже без бэкенда.
//
// Самодостаточный fetch (без правок api.ts — его держит сиблинг): запрос идёт на тот
// же origin /api, что и весь продукт; bearer-сессия передаётся cookie-/same-origin-
// транспортом бэкенда. Отдельный токен здесь не читаем (он приватный в api.ts).
// ============================================================================
import React from "react";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";

type ToastVariant = "success" | "info" | "warning" | "error";
type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// --- Контракт ответа замера -------------------------------------------------
interface BenchQuery { irbis_ms: number; biblio_ms: number; }
interface BenchCirculation { irbis_ms?: number; biblio_ms: number; }
interface BenchMigration { records_per_sec: number; total?: number; }
interface BenchResult {
  query: BenchQuery;
  circulation: BenchCirculation;
  migration: BenchMigration;
  ts?: number | string;
}

// Демо-значения для пилота (когда бэкенд-замер ещё не готов). Подобраны так, чтобы
// Biblio был ощутимо быстрее ИРБИС — типичная картина на современном стеке.
const DEMO: BenchResult = {
  query: { irbis_ms: 420, biblio_ms: 38 },
  circulation: { irbis_ms: 310, biblio_ms: 54 },
  migration: { records_per_sec: 1850, total: 248000 },
  ts: undefined,
};

// --- Стекломорфизм: namespaced CSS, светлая/тёмная тема -----------------------
// Поддержка темы: токены Biblio + ручной фолбэк через prefers-color-scheme на
// случай, если корневые токены темы не заданы. Класс .irb-bench--dark/--light не
// навязываем — берём системную тему и токены продукта.
const CSS = `
.irb-bench{position:relative;font-family:var(--font-ui,system-ui,sans-serif);
  --irb-glass-bg:rgba(255,255,255,.55);
  --irb-glass-brd:rgba(255,255,255,.65);
  --irb-glass-hi:rgba(255,255,255,.9);
  --irb-glass-sh:0 8px 30px rgba(20,16,14,.10),0 1px 2px rgba(20,16,14,.06);
  --irb-ink:var(--text-strong,#1a1714);
  --irb-ink-soft:var(--text-subtle,#7a726a);
  --irb-irbis:#5b6b8c;
  --irb-biblio:var(--accent,#c2410c);
}
@media (prefers-color-scheme:dark){
  .irb-bench{
    --irb-glass-bg:rgba(38,34,30,.46);
    --irb-glass-brd:rgba(255,255,255,.14);
    --irb-glass-hi:rgba(255,255,255,.22);
    --irb-glass-sh:0 10px 34px rgba(0,0,0,.42),0 1px 2px rgba(0,0,0,.3);
    --irb-irbis:#8ea0c4;
  }
}
/* Подложка-градиент с блёром — даёт стеклу «что преломлять». Изолирована внутри панели. */
.irb-bench__bg{position:absolute;inset:-40px;z-index:0;pointer-events:none;overflow:hidden;border-radius:24px;}
.irb-bench__bg::before,.irb-bench__bg::after{content:"";position:absolute;border-radius:50%;filter:blur(56px);opacity:.5;}
.irb-bench__bg::before{width:340px;height:340px;left:-40px;top:-60px;
  background:radial-gradient(circle,var(--irb-biblio),transparent 70%);}
.irb-bench__bg::after{width:300px;height:300px;right:-30px;bottom:-70px;
  background:radial-gradient(circle,var(--irb-irbis),transparent 70%);opacity:.42;}
.irb-bench__inner{position:relative;z-index:1;}

.irb-bench__head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:20px;}
.irb-bench__title{display:flex;align-items:center;gap:11px;}
.irb-bench__title h2{font-family:var(--font-display,inherit);font-weight:600;font-size:22px;letter-spacing:-.02em;margin:0;color:var(--irb-ink);}
.irb-bench__sub{margin:4px 0 0;font-size:13px;color:var(--irb-ink-soft);max-width:56ch;line-height:1.5;}

/* Стеклянный сегмент-тоггл «ИРБИС / Biblio / Сравнение» */
.irb-bench__seg{display:inline-flex;gap:3px;padding:4px;border-radius:14px;
  background:var(--irb-glass-bg);border:1px solid var(--irb-glass-brd);
  backdrop-filter:blur(14px) saturate(1.3);-webkit-backdrop-filter:blur(14px) saturate(1.3);
  box-shadow:inset 0 1px 0 var(--irb-glass-hi);}
.irb-bench__seg button{border:none;cursor:pointer;font-family:inherit;font-size:12.5px;font-weight:600;
  padding:7px 15px;border-radius:10px;background:transparent;color:var(--irb-ink-soft);
  display:inline-flex;align-items:center;gap:6px;transition:color .14s,background-color .14s,box-shadow .14s;white-space:nowrap;}
.irb-bench__seg button:hover{color:var(--irb-ink);}
.irb-bench__seg button[aria-pressed="true"]{color:#fff;box-shadow:0 2px 8px rgba(20,16,14,.22);}
.irb-bench__seg button[data-side="irbis"][aria-pressed="true"]{background:var(--irb-irbis);}
.irb-bench__seg button[data-side="biblio"][aria-pressed="true"]{background:var(--irb-biblio);}
.irb-bench__seg button[data-side="both"][aria-pressed="true"]{background:var(--irb-ink);}

.irb-bench__actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.irb-bench__run{border:none;cursor:pointer;font-family:inherit;font-size:13.5px;font-weight:600;
  padding:10px 18px;border-radius:13px;color:#fff;background:var(--irb-biblio);
  display:inline-flex;align-items:center;gap:8px;
  box-shadow:0 6px 18px color-mix(in srgb,var(--irb-biblio) 38%,transparent),inset 0 1px 0 rgba(255,255,255,.25);
  transition:transform .12s,box-shadow .12s,opacity .12s;}
.irb-bench__run:hover{transform:translateY(-1px);}
.irb-bench__run:active{transform:translateY(0);}
.irb-bench__run:disabled{opacity:.6;cursor:default;transform:none;}
.irb-bench__run .irb-bench__spin{animation:irb-bench-spin 1s linear infinite;display:inline-flex;}
@keyframes irb-bench-spin{to{transform:rotate(360deg);}}

/* Плашка демо-режима */
.irb-bench__demo{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:600;
  padding:6px 12px;border-radius:11px;color:var(--irb-ink);
  background:var(--irb-glass-bg);border:1px dashed var(--irb-glass-brd);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);}
.irb-bench__demo i{width:7px;height:7px;border-radius:50%;background:var(--irb-biblio);flex:none;
  box-shadow:0 0 0 3px color-mix(in srgb,var(--irb-biblio) 22%,transparent);}
.irb-bench__ts{font-size:12px;color:var(--irb-ink-soft);}

/* Сетка стеклянных метрик-карточек */
.irb-bench__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;}
.irb-bench__card{position:relative;border-radius:20px;padding:20px 20px 18px;overflow:hidden;
  background:var(--irb-glass-bg);border:1px solid var(--irb-glass-brd);
  backdrop-filter:blur(20px) saturate(1.35);-webkit-backdrop-filter:blur(20px) saturate(1.35);
  box-shadow:var(--irb-glass-sh),inset 0 1px 0 var(--irb-glass-hi);
  transition:transform .16s,box-shadow .16s;}
.irb-bench__card:hover{transform:translateY(-2px);}
/* Тонкий диагональный блик по верхней кромке стекла */
.irb-bench__card::before{content:"";position:absolute;left:0;right:0;top:0;height:42%;pointer-events:none;
  background:linear-gradient(160deg,var(--irb-glass-hi),transparent 80%);opacity:.7;}
.irb-bench__card-top{position:relative;display:flex;align-items:center;gap:9px;margin-bottom:14px;}
.irb-bench__card-ic{display:inline-flex;padding:7px;border-radius:11px;color:var(--irb-biblio);flex:none;
  background:color-mix(in srgb,var(--irb-biblio) 14%,transparent);}
.irb-bench__card-cap{font-size:12px;font-weight:600;color:var(--irb-ink);line-height:1.3;}
.irb-bench__card-unit{font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--irb-ink-soft);}

/* Крупное число (главная метрика стороны) */
.irb-bench__big{position:relative;display:flex;align-items:baseline;gap:8px;margin:2px 0 4px;}
.irb-bench__big-num{font-family:var(--font-display,inherit);font-weight:700;font-size:40px;line-height:1;
  letter-spacing:-.03em;font-variant-numeric:tabular-nums;color:var(--irb-ink);}
.irb-bench__big-u{font-size:13px;font-weight:600;color:var(--irb-ink-soft);}

/* Сравнительные строки сторон (ИРБИС / Biblio) */
.irb-bench__sides{position:relative;display:flex;flex-direction:column;gap:9px;margin-top:14px;}
.irb-bench__side{display:grid;grid-template-columns:64px 1fr auto;align-items:center;gap:10px;}
.irb-bench__side-lab{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:var(--irb-ink-soft);}
.irb-bench__side-lab i{width:8px;height:8px;border-radius:3px;flex:none;}
.irb-bench__side[data-side="irbis"] .irb-bench__side-lab i{background:var(--irb-irbis);}
.irb-bench__side[data-side="biblio"] .irb-bench__side-lab i{background:var(--irb-biblio);}
.irb-bench__track{height:7px;border-radius:99px;background:color-mix(in srgb,var(--irb-ink) 9%,transparent);overflow:hidden;}
.irb-bench__fill{height:100%;border-radius:99px;transition:width .5s cubic-bezier(.22,1,.36,1);}
.irb-bench__side[data-side="irbis"] .irb-bench__fill{background:var(--irb-irbis);}
.irb-bench__side[data-side="biblio"] .irb-bench__fill{background:var(--irb-biblio);}
.irb-bench__side-val{font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--irb-ink);min-width:54px;text-align:right;}

/* Бейдж ускорения «×N» */
.irb-bench__speedup{position:relative;display:inline-flex;align-items:center;gap:6px;margin-top:14px;
  padding:6px 12px;border-radius:11px;font-size:12.5px;font-weight:700;
  color:var(--irb-biblio);background:color-mix(in srgb,var(--irb-biblio) 13%,transparent);
  border:1px solid color-mix(in srgb,var(--irb-biblio) 26%,transparent);}
.irb-bench__speedup--flat{color:var(--irb-ink-soft);background:color-mix(in srgb,var(--irb-ink) 7%,transparent);border-color:transparent;}

/* Приглушение «проигравшей» стороны при выборе фокуса в тоггле */
.irb-bench--focus-irbis .irb-bench__side[data-side="biblio"],
.irb-bench--focus-biblio .irb-bench__side[data-side="irbis"]{opacity:.42;}

.irb-bench__foot{margin-top:18px;font-size:11.5px;color:var(--irb-ink-soft);line-height:1.6;max-width:70ch;}

@media (max-width:560px){
  .irb-bench__head{flex-direction:column;}
  .irb-bench__big-num{font-size:34px;}
}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-bench-css")) {
  const s = document.createElement("style"); s.id = "irb-bench-css"; s.textContent = CSS; document.head.appendChild(s);
}

// --- Утилиты округления / ускорения -----------------------------------------
function round(n: number): number {
  if (!isFinite(n)) return 0;
  return Math.round(n);
}
// Ускорение «×N» = медленнее / быстрее. Защита от 0/NaN: при нулевом знаменателе
// или нечисловых данных возвращаем null (показываем «—», без деления на ноль).
function speedup(slow: number, fast: number): number | null {
  if (!isFinite(slow) || !isFinite(fast) || fast <= 0 || slow <= 0) return null;
  return slow / fast;
}
function fmtSpeedup(x: number | null): string {
  if (x == null) return "—";
  if (x >= 10) return "×" + round(x);
  return "×" + (Math.round(x * 10) / 10).toString().replace(".", ",");
}
function fmtInt(n: number): string {
  return round(n).toLocaleString("ru-RU");
}
function fmtTs(ts: number | string | undefined): string {
  if (ts == null) return "";
  const d = typeof ts === "number" ? new Date(ts < 1e12 ? ts * 1000 : ts) : new Date(ts);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

type Focus = "both" | "irbis" | "biblio";
type LoadState = "demo" | "live" | "loading";

// Нормализация ответа сервера к BenchResult (терпимо к недостающим полям).
function normalize(d: any): BenchResult | null {
  if (!d || typeof d !== "object") return null;
  const q = d.query || {}; const c = d.circulation || {}; const m = d.migration || {};
  const num = (v: any): number => (typeof v === "number" && isFinite(v) ? v : NaN);
  const res: BenchResult = {
    query: { irbis_ms: num(q.irbis_ms), biblio_ms: num(q.biblio_ms) },
    circulation: { irbis_ms: num(c.irbis_ms), biblio_ms: num(c.biblio_ms) },
    migration: { records_per_sec: num(m.records_per_sec), total: typeof m.total === "number" ? m.total : undefined },
    ts: d.ts,
  };
  // Минимально валидный ответ: есть числовая выдача поиска у обеих сторон.
  if (!isFinite(res.query.irbis_ms) || !isFinite(res.query.biblio_ms)) return null;
  return res;
}

export function BenchmarkPanel({ toast }: { toast: ToastFn }) {
  const [focus, setFocus] = React.useState<Focus>("both");
  const [data, setData] = React.useState<BenchResult>(DEMO);
  const [state, setState] = React.useState<LoadState>("demo");
  const [running, setRunning] = React.useState(false);

  // При открытии — пробуем подтянуть последний кэш замера (GET). Если эндпойнта
  // ещё нет (404/501) или сеть недоступна — тихо остаёмся в демо-режиме.
  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch("/api/admin/benchmark", { headers: { Accept: "application/json" } });
        if (!alive) return;
        if (r.status === 404 || r.status === 501 || !r.ok) return;
        const j = await r.json().catch(() => null);
        const norm = normalize(j && j.data ? j.data : j);
        if (norm && alive) { setData(norm); setState("live"); }
      } catch {
        /* демо-режим — без шума */
      }
    })();
    return () => { alive = false; };
  }, []);

  async function runBenchmark() {
    setRunning(true); setState((s) => (s === "live" ? "loading" : s));
    try {
      const r = await fetch("/api/admin/benchmark/run", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
      });
      if (r.status === 404 || r.status === 501) {
        toast({ variant: "info", title: "Замер пока в демо-режиме", message: "Бэкенд-эндпойнт /api/admin/benchmark/run ещё не развёрнут — показаны демо-значения." });
        setState("demo");
        return;
      }
      if (r.status === 403) {
        toast({ variant: "warning", title: "Недостаточно прав", message: "Запуск замера доступен супер-администратору." });
        return;
      }
      if (!r.ok) { toast({ variant: "error", title: "Замер не выполнен", message: "Код ответа " + r.status + ". Повторите позже." }); return; }
      const j = await r.json().catch(() => null);
      const norm = normalize(j && j.data ? j.data : j);
      if (norm) {
        setData(norm); setState("live");
        toast({ variant: "success", title: "Замер выполнен", message: "Метрики обновлены по живому замеру." });
      } else {
        toast({ variant: "warning", title: "Неожиданный ответ", message: "Сервер вернул данные в неизвестном формате — оставлены демо-значения." });
        setState("demo");
      }
    } catch {
      toast({ variant: "info", title: "Замер пока в демо-режиме", message: "Бэкенд-замер недоступен — показаны демо-значения. Нажмите «Запустить замер», когда он будет готов." });
      setState("demo");
    } finally {
      setRunning(false);
    }
  }

  const demo = state === "demo";
  const focusClass = focus === "irbis" ? " irb-bench--focus-irbis" : focus === "biblio" ? " irb-bench--focus-biblio" : "";

  return (
    <div className={"irb-bench" + focusClass}>
      <div className="irb-bench__bg" aria-hidden="true" />
      <div className="irb-bench__inner">
        {/* ===== Шапка: заголовок + тоггл + запуск ===== */}
        <div className="irb-bench__head">
          <div>
            <div className="irb-bench__title">
              <h2>Сравнение ИРБИС ↔ Biblio</h2>
            </div>
            <p className="irb-bench__sub">
              Скорость обработки запросов, выдачи и наполнения базы. По умолчанию — сравнение бок-о-бок;
              переключатель выделяет одну из сторон.
            </p>
          </div>
          <div className="irb-bench__actions">
            <div className="irb-bench__seg" role="group" aria-label="Что выделить в сравнении">
              <button type="button" data-side="both" aria-pressed={focus === "both"} onClick={() => setFocus("both")}>
                <Icon name="bar-chart" size={14} />Сравнение
              </button>
              <button type="button" data-side="irbis" aria-pressed={focus === "irbis"} onClick={() => setFocus("irbis")}>ИРБИС</button>
              <button type="button" data-side="biblio" aria-pressed={focus === "biblio"} onClick={() => setFocus("biblio")}>Biblio</button>
            </div>
            <button type="button" className="irb-bench__run" onClick={runBenchmark} disabled={running} aria-busy={running}>
              <span className={running ? "irb-bench__spin" : ""}><Icon name="refresh-cw" size={15} /></span>
              {running ? "Замер…" : "Запустить замер"}
            </button>
          </div>
        </div>

        {/* ===== Плашка режима ===== */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
          {demo ? (
            <span className="irb-bench__demo"><i aria-hidden="true" />демо-значения</span>
          ) : (
            <span className="irb-bench__ts">Живой замер{data.ts ? " · " + fmtTs(data.ts) : ""}</span>
          )}
          {demo && (
            <span className="irb-bench__ts">нажмите «Запустить замер», когда бэкенд-замер будет готов</span>
          )}
        </div>

        {/* ===== Метрик-карточки ===== */}
        <div className="irb-bench__grid">
          <DurationCard
            icon="trending-up"
            cap="Скорость обработки запроса"
            hint="поиск"
            irbis={data.query.irbis_ms}
            biblio={data.query.biblio_ms}
            focus={focus}
          />
          <DurationCard
            icon="package"
            cap="Скорость выдачи"
            hint="выдача / возврат"
            irbis={data.circulation.irbis_ms}
            biblio={data.circulation.biblio_ms}
            focus={focus}
          />
          <MigrationCard migration={data.migration} />
        </div>

        <p className="irb-bench__foot">
          Метрики времени — миллисекунды на операцию (меньше — лучше); ускорение «×N» — во сколько раз Biblio
          быстрее ИРБИС. Наполнение базы — скорость переноса записей из ИРБИС64 при миграции.
          {demo && " Значения на карточках — иллюстративные (демо); после развёртывания бэкенд-замера панель показывает живые числа."}
        </p>
      </div>
    </div>
  );
}

// Карточка длительности операции (мс): крупное число «быстрой» стороны (Biblio),
// две сравнительные дорожки, бейдж ускорения. Дорожки нормируются по медленной
// стороне, чтобы визуально читалась разница.
function DurationCard({ icon, cap, hint, irbis, biblio, focus }: {
  icon: IconName; cap: string; hint: string; irbis: number; biblio: number; focus: Focus;
}) {
  const hasIrbis = isFinite(irbis) && irbis > 0;
  const hasBiblio = isFinite(biblio) && biblio > 0;
  const su = hasIrbis && hasBiblio ? speedup(irbis, biblio) : null;
  // Главное число карточки — сторона в фокусе (или Biblio в режиме сравнения).
  const heroVal = focus === "irbis" ? irbis : biblio;
  const heroOk = focus === "irbis" ? hasIrbis : hasBiblio;
  const max = Math.max(hasIrbis ? irbis : 0, hasBiblio ? biblio : 0) || 1;
  const pct = (v: number, ok: boolean) => (ok ? Math.max(4, Math.round((v / max) * 100)) : 0);
  return (
    <div className="irb-bench__card">
      <div className="irb-bench__card-top">
        <span className="irb-bench__card-ic"><Icon name={icon} size={17} /></span>
        <span>
          <span className="irb-bench__card-cap" style={{ display: "block" }}>{cap}</span>
          <span className="irb-bench__card-unit">{hint} · мс</span>
        </span>
      </div>
      <div className="irb-bench__big">
        <span className="irb-bench__big-num">{heroOk ? fmtInt(heroVal) : "—"}</span>
        <span className="irb-bench__big-u">мс · {focus === "irbis" ? "ИРБИС" : "Biblio"}</span>
      </div>
      <div className="irb-bench__sides">
        <div className="irb-bench__side" data-side="irbis">
          <span className="irb-bench__side-lab"><i aria-hidden="true" />ИРБИС</span>
          <span className="irb-bench__track"><span className="irb-bench__fill" style={{ width: pct(irbis, hasIrbis) + "%" }} /></span>
          <span className="irb-bench__side-val">{hasIrbis ? fmtInt(irbis) : "—"}</span>
        </div>
        <div className="irb-bench__side" data-side="biblio">
          <span className="irb-bench__side-lab"><i aria-hidden="true" />Biblio</span>
          <span className="irb-bench__track"><span className="irb-bench__fill" style={{ width: pct(biblio, hasBiblio) + "%" }} /></span>
          <span className="irb-bench__side-val">{hasBiblio ? fmtInt(biblio) : "—"}</span>
        </div>
      </div>
      <span className={"irb-bench__speedup" + (su == null ? " irb-bench__speedup--flat" : "")}>
        <Icon name="trending-up" size={14} />
        {su == null ? "сравнение недоступно" : "быстрее в " + fmtSpeedup(su) + " раз"}
      </span>
    </div>
  );
}

// Карточка миграции: скорость наполнения базы из ИРБИС (записей/сек) + всего записей.
// Односторонняя метрика (это наша операция переноса), поэтому без дорожек ИРБИС/Biblio.
function MigrationCard({ migration }: { migration: BenchMigration }) {
  const rps = migration.records_per_sec;
  const hasRps = isFinite(rps) && rps > 0;
  const total = migration.total;
  return (
    <div className="irb-bench__card">
      <div className="irb-bench__card-top">
        <span className="irb-bench__card-ic"><Icon name="download" size={17} /></span>
        <span>
          <span className="irb-bench__card-cap" style={{ display: "block" }}>Наполнение базы из ИРБИС</span>
          <span className="irb-bench__card-unit">миграция · записей/сек</span>
        </span>
      </div>
      <div className="irb-bench__big">
        <span className="irb-bench__big-num">{hasRps ? fmtInt(rps) : "—"}</span>
        <span className="irb-bench__big-u">зап./сек</span>
      </div>
      <div className="irb-bench__sides">
        <div className="irb-bench__side" data-side="biblio" style={{ gridTemplateColumns: "1fr auto" }}>
          <span className="irb-bench__side-lab" style={{ gridColumn: "1" }}>Перенесено всего</span>
          <span className="irb-bench__side-val">{typeof total === "number" ? fmtInt(total) : "—"}</span>
        </div>
      </div>
      <span className="irb-bench__speedup">
        <Icon name="refresh-cw" size={14} />
        {hasRps && typeof total === "number"
          ? "≈ " + fmtInt(total / rps / 60) + " мин на весь объём"
          : "потоковый перенос записей"}
      </span>
    </div>
  );
}
