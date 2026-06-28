// Кукипанель (#335, Фаза 1) — баннер согласия на использование cookie для ВСЕХ
// посетителей сайта (отдельно от согласия на обработку ПДн читателя `Consent.tsx`,
// которое про залогиненного читателя). Категории: необходимые (всегда вкл.),
// аналитика, предпочтения. Выбор запоминается в localStorage и баннер больше не
// показывается; «Настроить» раскрывает тумблеры. 152-ФЗ + типовая веб-практика.
//
// Прочий код читает решение через cookieConsent() (напр. гейтить аналитику до
// согласия). Самодостаточный компонент: scoped-CSS, без сетевых вызовов.
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";

export interface CookieConsent {
  necessary: true;        // необходимые — всегда включены (нельзя отключить)
  analytics: boolean;
  preferences: boolean;
  ts: string;             // ISO-метка момента выбора
}

const LS_KEY = "biblio_cookie_consent_v1";

// Текущее решение по cookie или null, если выбор ещё не сделан. Безопасно к
// отсутствию localStorage / повреждённому значению (-> null).
export function cookieConsent(): CookieConsent | null {
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw);
    if (v && typeof v === "object" && v.ts) return { necessary: true, analytics: !!v.analytics, preferences: !!v.preferences, ts: String(v.ts) };
  } catch { /* нет localStorage / битое значение */ }
  return null;
}

function persist(c: { analytics: boolean; preferences: boolean }) {
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify({ necessary: true, analytics: c.analytics, preferences: c.preferences, ts: new Date().toISOString() }));
  } catch { /* приватный режим / нет localStorage — баннер просто покажется снова */ }
}

const CSS = `
.irb-cookie{position:fixed;left:0;right:0;bottom:0;z-index:90;display:flex;justify-content:center;padding:14px;pointer-events:none;}
.irb-cookie__box{pointer-events:auto;width:100%;max-width:780px;background:var(--surface-card,#fff);
  border:1px solid var(--border-strong,#cdd3da);border-radius:var(--radius-xl,16px);box-shadow:var(--shadow-lg);
  padding:16px 18px;display:flex;flex-direction:column;gap:12px;}
.irb-cookie__head{display:flex;align-items:flex-start;gap:11px;}
.irb-cookie__ic{flex:none;width:38px;height:38px;border-radius:11px;background:var(--accent-weak,#eef2f7);color:var(--accent,#2f5d62);
  display:inline-flex;align-items:center;justify-content:center;}
.irb-cookie__ttl{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);font-size:var(--text-lg,1.05rem);
  color:var(--text-strong);margin:0 0 3px;}
.irb-cookie__txt{font-size:var(--text-sm,.92rem);color:var(--text-body);line-height:1.45;margin:0;}
.irb-cookie__txt a{color:var(--accent,#2f5d62);text-decoration:underline;}
.irb-cookie__cats{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--border-subtle);padding-top:11px;}
.irb-cookie__cat{display:flex;align-items:flex-start;gap:10px;justify-content:space-between;}
.irb-cookie__cat-info{min-width:0;}
.irb-cookie__cat-name{font-size:var(--text-sm);font-weight:var(--weight-semibold,600);color:var(--text-strong);}
.irb-cookie__cat-desc{font-size:var(--text-xs);color:var(--text-subtle);line-height:1.35;}
.irb-cookie__sw{position:relative;flex:none;width:42px;height:24px;border-radius:999px;border:none;cursor:pointer;
  background:var(--border-strong,#cdd3da);transition:background-color .15s;padding:0;}
.irb-cookie__sw[aria-checked="true"]{background:var(--accent,#2f5d62);}
.irb-cookie__sw[aria-disabled="true"]{opacity:.55;cursor:not-allowed;}
.irb-cookie__sw span{position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:left .15s;box-shadow:var(--shadow-sm);}
.irb-cookie__sw[aria-checked="true"] span{left:21px;}
.irb-cookie__acts{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;}
.irb-cookie__btn{display:inline-flex;align-items:center;gap:6px;border-radius:var(--radius-md,8px);padding:8px 15px;cursor:pointer;
  font-family:var(--font-ui,inherit);font-size:var(--text-sm);font-weight:var(--weight-semibold,600);border:1px solid var(--border-strong,#cdd3da);
  background:var(--surface-card);color:var(--text-body);}
.irb-cookie__btn:hover{background:var(--surface-sunken);}
.irb-cookie__btn--primary{background:var(--accent,#2f5d62);border-color:var(--accent,#2f5d62);color:var(--accent-fg,#fff);}
.irb-cookie__btn--primary:hover{background:var(--accent-hover,#264c50);}
.irb-cookie__btn--ghost{border-color:transparent;color:var(--text-muted);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-cookie-css")) {
  const s = document.createElement("style"); s.id = "irb-cookie-css"; s.textContent = CSS; document.head.appendChild(s);
}

function Switch({ on, disabled, onToggle, label }: { on: boolean; disabled?: boolean; onToggle?: () => void; label: string }) {
  return (
    <button type="button" className="irb-cookie__sw" role="switch" aria-checked={on} aria-disabled={disabled || undefined}
      aria-label={label} onClick={() => { if (!disabled && onToggle) onToggle(); }}>
      <span />
    </button>
  );
}

// policyHref — ссылка на политику cookie/конфиденциальности (по умолчанию якорь
// страницы «Реквизиты»/политики; уточняется при появлении страницы, #335 Фаза 2).
export function CookiePanel({ policyHref = "/privacy" }: { policyHref?: string }) {
  const [decided, setDecided] = React.useState<boolean>(() => cookieConsent() !== null);
  const [open, setOpen] = React.useState(false);     // раскрыты ли настройки категорий
  const [analytics, setAnalytics] = React.useState(false);
  const [preferences, setPreferences] = React.useState(false);

  if (decided) return null; // выбор уже сделан — баннер не показываем

  const save = (a: boolean, p: boolean) => { persist({ analytics: a, preferences: p }); setDecided(true); };

  return (
    <div className="irb-cookie" role="region" aria-label="Согласие на использование cookie">
      <div className="irb-cookie__box">
        <div className="irb-cookie__head">
          <span className="irb-cookie__ic" aria-hidden="true"><Icon name="info" size={20} /></span>
          <div>
            <h2 className="irb-cookie__ttl">Мы используем cookie</h2>
            <p className="irb-cookie__txt">
              Сайт использует файлы cookie: необходимые — для работы портала, и опциональные — для аналитики
              и сохранения предпочтений. Необходимые включены всегда. Подробнее — в{" "}
              <a href={policyHref}>политике использования cookie</a>. Вы можете принять все или выбрать категории.
            </p>
          </div>
        </div>

        {open && (
          <div className="irb-cookie__cats">
            <div className="irb-cookie__cat">
              <div className="irb-cookie__cat-info">
                <div className="irb-cookie__cat-name">Необходимые</div>
                <div className="irb-cookie__cat-desc">Сессия, безопасность, базовая работа портала. Нельзя отключить.</div>
              </div>
              <Switch on disabled label="Необходимые cookie (всегда включены)" />
            </div>
            <div className="irb-cookie__cat">
              <div className="irb-cookie__cat-info">
                <div className="irb-cookie__cat-name">Аналитика</div>
                <div className="irb-cookie__cat-desc">Обезличенная статистика посещений — помогает улучшать сервис.</div>
              </div>
              <Switch on={analytics} onToggle={() => setAnalytics((v) => !v)} label="Cookie аналитики" />
            </div>
            <div className="irb-cookie__cat">
              <div className="irb-cookie__cat-info">
                <div className="irb-cookie__cat-name">Предпочтения</div>
                <div className="irb-cookie__cat-desc">Запоминание настроек интерфейса (тема, язык, вид выдачи).</div>
              </div>
              <Switch on={preferences} onToggle={() => setPreferences((v) => !v)} label="Cookie предпочтений" />
            </div>
          </div>
        )}

        <div className="irb-cookie__acts">
          {!open
            ? <button type="button" className="irb-cookie__btn irb-cookie__btn--ghost" onClick={() => setOpen(true)}>
                <Icon name="sliders" size={14} /> Настроить
              </button>
            : <button type="button" className="irb-cookie__btn" onClick={() => save(analytics, preferences)}>
                Сохранить выбор
              </button>}
          <button type="button" className="irb-cookie__btn" onClick={() => save(false, false)}>Только необходимые</button>
          <button type="button" className="irb-cookie__btn irb-cookie__btn--primary" onClick={() => save(true, true)}>
            <Icon name="check" size={14} /> Принять все
          </button>
        </div>
      </div>
    </div>
  );
}
