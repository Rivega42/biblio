// Соответствие 152-ФЗ в читательском портале (#199, MVP фаза 3, аудит V9/V5).
// Три экспорта:
//   ConsentBanner — нена­вязчивое уведомление о согласии на обработку ПДн при
//     первом сеансе: показывается, если GET /api/reader/consent.given === false;
//     «Принять» → POST /api/reader/consent {given:true}; ссылка на уведомление о
//     конфиденциальности. Для гостей не показывается (рендерится только для
//     вошедшего читателя — управляется флагом loggedIn в App.tsx).
//   ConsentToggle — переключатель «Согласие на обработку ПДн» в кабинете:
//     показать/отозвать согласие; persist через POST /api/reader/consent.
//   EraseDataCard — «Удалить мои данные» (право на забвение): диалог
//     подтверждения со списком удаляемого; POST /api/reader/erase {confirm:true};
//     на успехе — счётчики удалённого.
// Грациозная деградация: при 404/501 баннер не показываем; тумблер/карточка
// прячутся или тихо тостят «модуль ещё подключается». Namespaced CSS irb-consent*/
// irb-erase*, токены Biblio. Каталог библиотеки правом на забвение НЕ затрагивается.
import React from "react";
import { api } from "../api";
import type { ConsentState, ErasureResult } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";

type Toast = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Ссылка на уведомление о конфиденциальности (политику обработки ПДн). Жёстко не
// зашиваем URL — открываем якорь #privacy на странице (или печатную версию).
const PRIVACY_HREF = "#privacy";

const CSS = `
.irb-consent-banner{position:fixed;left:0;right:0;bottom:0;z-index:55;display:flex;justify-content:center;
  padding:0 16px 16px;pointer-events:none;}
.irb-consent-banner__inner{pointer-events:auto;max-width:760px;width:100%;display:flex;align-items:flex-start;gap:14px;
  background:var(--surface-card,#fff);color:var(--text-body);border:1px solid var(--border-strong,#cdd3da);
  border-radius:14px;box-shadow:var(--shadow-lg,0 16px 44px rgba(0,0,0,.22));padding:16px 18px;}
.irb-consent-banner__ic{flex:none;display:flex;align-items:center;justify-content:center;width:36px;height:36px;
  border-radius:10px;background:var(--accent-weak,#eef2f7);color:var(--accent);}
.irb-consent-banner__txt{flex:1;min-width:0;font-size:var(--text-sm);line-height:1.5;}
.irb-consent-banner__title{font-weight:600;color:var(--text-strong);margin-bottom:3px;}
.irb-consent-banner__link{color:var(--accent);text-decoration:underline;cursor:pointer;}
.irb-consent-banner__actions{display:flex;gap:8px;align-items:center;flex:none;align-self:center;}
.irb-consent-toggle{display:flex;align-items:flex-start;gap:13px;}
.irb-consent-toggle__main{flex:1;min-width:0;}
.irb-consent-toggle__name{font-weight:600;font-size:var(--text-sm);color:var(--text-strong);}
.irb-consent-toggle__meta{font-size:var(--text-xs);color:var(--text-subtle);margin-top:3px;line-height:1.5;}
.irb-consent-state{display:inline-flex;align-items:center;gap:6px;font-size:var(--text-xs);font-weight:600;
  padding:3px 10px;border-radius:999px;white-space:nowrap;}
.irb-consent-state--on{background:var(--status-available-bg,#E4F0E8);color:var(--status-available,#2E7D52);}
.irb-consent-state--off{background:var(--surface-sunken,#f0eee6);color:var(--text-subtle);}
.irb-erase__list{margin:10px 0 4px;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px;}
.irb-erase__li{display:flex;align-items:center;gap:9px;font-size:var(--text-sm);color:var(--text-body);}
.irb-erase__li i{flex:none;display:flex;color:var(--error,var(--danger-500));}
.irb-erase__note{font-size:var(--text-xs);color:var(--text-subtle);line-height:1.55;
  background:var(--surface-sunken,#f5f4ee);border-radius:10px;padding:10px 12px;margin-top:12px;
  display:flex;gap:8px;align-items:flex-start;}
.irb-erase__counts{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;}
.irb-erase__count{display:inline-flex;align-items:center;gap:6px;font-size:var(--text-xs);font-weight:600;
  padding:4px 11px;border-radius:999px;background:var(--accent-weak,#eef2f7);color:var(--accent-press,var(--accent));}
.irb-modal__back{position:fixed;inset:0;background:rgba(20,16,14,.45);display:flex;align-items:center;
  justify-content:center;z-index:70;padding:16px;}
.irb-modal__card{background:var(--surface-card,#fff);color:var(--text-body);border-radius:16px;padding:22px;
  width:min(440px,96vw);box-shadow:var(--shadow-lg,0 20px 50px rgba(0,0,0,.25));}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-consent-css")) {
  const s = document.createElement("style"); s.id = "irb-consent-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Категории читательских данных, удаляемые правом на забвение (порядок = порядок
// счётчиков в ErasureResult). Каталог библиотеки сюда не входит — он неприкосновенен.
const ERASE_CATEGORIES: { key: keyof ErasureResult; label: string }[] = [
  { key: "reviews", label: "Отзывы и оценки" },
  { key: "holds", label: "Брони" },
  { key: "shelves", label: "Полки и списки чтения" },
  { key: "history", label: "История просмотров" },
  { key: "savedSearches", label: "Сохранённые запросы" },
];

// Общий хук состояния согласия. unavailable=true → эндпойнт согласия не развёрнут.
function useConsent() {
  const [state, setState] = React.useState<ConsentState | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const load = React.useCallback(async () => {
    const r = await api.readerConsent();
    if (r.status === 404 || r.status === 501) { setUnavailable(true); setState(null); return; }
    if (r.json?.ok && r.json.data) { setState(r.json.data); setUnavailable(false); }
    else { setState(null); setUnavailable(true); }
  }, []);
  React.useEffect(() => { void load(); }, [load]);
  return { state, setState, unavailable, load };
}

// ── Баннер согласия (первый сеанс) ─────────────────────────────────────────
// Рендерится App.tsx только для вошедшего читателя (не для гостей). Показывается,
// пока согласие не дано и эндпойнт доступен. «Принять» сохраняет согласие.
export function ConsentBanner({ toast }: { toast: Toast }) {
  const { state, setState, unavailable } = useConsent();
  const [dismissed, setDismissed] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function accept() {
    setBusy(true);
    const r = await api.setReaderConsent(true);
    setBusy(false);
    if (r.status === 200 && r.json?.ok) {
      setState((s) => ({ given: true, ts: new Date().toISOString(), version: s?.version }));
      toast({ variant: "success", title: "Согласие сохранено", message: "Спасибо! Изменить решение можно в кабинете." });
    } else if (r.status === 404 || r.status === 501) {
      setDismissed(true);
      toast({ variant: "info", title: "Согласие недоступно", message: "Модуль обработки согласий ещё подключается." });
    } else {
      toast({ variant: "error", title: "Не удалось сохранить", message: "Повторите попытку позже." });
    }
  }

  // Не показываем: эндпойнта нет, ещё грузим, согласие уже дано, либо закрыли.
  if (unavailable || dismissed || state === null || state.given) return null;

  return (
    <div className="irb-consent-banner" role="region" aria-label="Согласие на обработку персональных данных">
      <div className="irb-consent-banner__inner">
        <span className="irb-consent-banner__ic" aria-hidden="true"><Icon name="shield" size={20} /></span>
        <div className="irb-consent-banner__txt">
          <div className="irb-consent-banner__title">Обработка персональных данных</div>
          Портал обрабатывает ваши персональные данные (формуляр, история, заказы) для библиотечного
          обслуживания согласно 152-ФЗ.{" "}
          <a className="irb-consent-banner__link" href={PRIVACY_HREF} target="_blank" rel="noopener noreferrer">
            Уведомление о конфиденциальности
          </a>. Согласие можно отозвать в кабинете в любой момент.
        </div>
        <div className="irb-consent-banner__actions">
          <Button variant="ghost" size="sm" onClick={() => setDismissed(true)}>Позже</Button>
          <Button size="sm" iconLeft="check" loading={busy} onClick={accept}>Принять</Button>
        </div>
      </div>
    </div>
  );
}

// ── Переключатель согласия (кабинет) ───────────────────────────────────────
// Показать текущее состояние согласия + дать/отозвать. При недоступности эндпойнта
// карточку не показываем (секция управляется родителем; здесь — null).
export function ConsentToggle({ cardSx, toast }: { cardSx: React.CSSProperties; toast: Toast }) {
  const { state, setState, unavailable } = useConsent();
  const [busy, setBusy] = React.useState(false);

  async function set(given: boolean) {
    setBusy(true);
    const r = await api.setReaderConsent(given);
    setBusy(false);
    if (r.status === 200 && r.json?.ok) {
      setState((s) => ({ given, ts: new Date().toISOString(), version: s?.version }));
      toast({ variant: given ? "success" : "info", title: given ? "Согласие дано" : "Согласие отозвано",
        message: given ? "Спасибо." : "Часть сервисов портала может стать недоступной." });
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Недоступно", message: "Модуль обработки согласий ещё подключается." });
    } else {
      toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку позже." });
    }
  }

  if (unavailable) return null;
  const given = !!state?.given;

  return (
    <div style={{ ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: 18 }}>
      <div className="irb-consent-toggle">
        <span className="irb-consent-banner__ic" aria-hidden="true"><Icon name="shield" size={18} /></span>
        <div className="irb-consent-toggle__main">
          <div className="irb-consent-toggle__name">Согласие на обработку персональных данных</div>
          <div className="irb-consent-toggle__meta">
            {state === null ? "Загрузка состояния согласия…"
              : given
                ? <>Согласие дано{state.ts ? " · " + fmtTs(state.ts) : ""}. Вы можете отозвать его в любой момент.</>
                : "Согласие не дано. Часть персональных сервисов портала недоступна."}
          </div>
        </div>
        <span className={"irb-consent-state irb-consent-state--" + (given ? "on" : "off")}>
          <Icon name={given ? "check-circle" : "info"} size={13} />{given ? "Дано" : "Не дано"}
        </span>
      </div>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 14 }}>
        {given
          ? <Button variant="ghost" size="sm" iconLeft="x" loading={busy} onClick={() => set(false)}>Отозвать согласие</Button>
          : <Button size="sm" iconLeft="check" loading={busy} onClick={() => set(true)} disabled={state === null}>Дать согласие</Button>}
      </div>
    </div>
  );
}

// ── Право на забвение (кабинет) ────────────────────────────────────────────
// «Удалить мои данные» с диалогом подтверждения. На успехе — счётчики удалённого
// + onErased() для обновления кабинета. Каталог библиотеки не затрагивается.
export function EraseDataCard({ cardSx, toast, onErased }: {
  cardSx: React.CSSProperties; toast: Toast; onErased?: () => void;
}) {
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<ErasureResult | null>(null);

  async function erase() {
    setBusy(true);
    const r = await api.eraseReaderData();
    setBusy(false);
    setConfirmOpen(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      setResult(r.json.data.erased || {});
      const total = ERASE_CATEGORIES.reduce((n, c) => n + (Number(r.json!.data!.erased?.[c.key]) || 0), 0);
      toast({ variant: "success", title: "Данные удалены", message: "Удалено записей: " + total + ". Каталог библиотеки не затронут." });
      onErased?.();
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." });
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Удаление недоступно", message: "Модуль права на забвение ещё подключается." });
    } else {
      toast({ variant: "error", title: "Не удалось удалить", message: "Повторите попытку позже." });
    }
  }

  return (
    <div style={{ ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: 18, borderColor: "var(--danger-200,var(--border-subtle))" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 13 }}>
        <span className="irb-consent-banner__ic" aria-hidden="true"
          style={{ background: "var(--danger-50,#FBE9E7)", color: "var(--error,var(--danger-500))" }}>
          <Icon name="trash" size={18} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="irb-consent-toggle__name">Удалить мои данные</div>
          <div className="irb-consent-toggle__meta">
            Право на забвение (152-ФЗ): удаление ваших читательских данных с портала. Действие необратимо.
          </div>
        </div>
      </div>

      {result ? (
        <div className="irb-erase__counts" aria-live="polite">
          {ERASE_CATEGORIES.map((c) => (
            <span key={c.key} className="irb-erase__count">
              <Icon name="check" size={12} />{c.label}: {Number(result[c.key]) || 0}
            </span>
          ))}
        </div>
      ) : (
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
          <Button variant="ghost" size="sm" iconLeft="download"
            onClick={async () => {
              const okexp = await api.meExport();
              toast(okexp ? { variant: "success", title: "Данные выгружены", message: "Файл my-data.json скачан." }
                          : { variant: "error", title: "Не выгружено", message: "Повторите попытку." });
            }}>Скачать мои данные</Button>
          <Button variant="ghost" size="sm" iconLeft="trash" onClick={() => setConfirmOpen(true)}>Удалить мои данные</Button>
        </div>
      )}

      {confirmOpen && (
        <div className="irb-modal__back" onClick={() => setConfirmOpen(false)}>
          <div className="irb-modal__card" role="dialog" aria-modal="true" aria-label="Подтверждение удаления данных"
            onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <Icon name="alert-triangle" size={20} style={{ color: "var(--error,var(--danger-500))" }} />
              <b style={{ fontSize: "var(--text-lg)" }}>Удалить мои данные?</b>
            </div>
            <p style={{ margin: "0 0 4px", color: "var(--text-subtle)", fontSize: "var(--text-sm)", lineHeight: 1.5 }}>
              Будут безвозвратно удалены ваши персональные данные на портале:
            </p>
            <ul className="irb-erase__list">
              {ERASE_CATEGORIES.map((c) => (
                <li key={c.key} className="irb-erase__li"><i aria-hidden="true"><Icon name="x" size={14} /></i>{c.label}</li>
              ))}
            </ul>
            <div className="irb-erase__note">
              <Icon name="info" size={15} style={{ flex: "none", color: "var(--text-subtle)", marginTop: 1 }} />
              <span>Каталог библиотеки и сведения о выданных экземплярах (формуляр) <b>не затрагиваются</b> —
                это учётные данные библиотеки. Удаляются только данные, созданные вами на портале.</span>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 18 }}>
              <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Отмена</Button>
              <Button variant="danger" iconLeft="trash" loading={busy} onClick={erase}>Удалить безвозвратно</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Отметка времени ISO → человекочитаемая дата (локально). На ошибке — как есть.
function fmtTs(ts: string): string {
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  } catch { return ts; }
}
