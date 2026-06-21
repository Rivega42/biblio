// Почтовый ящик уведомлений читателя (#222). Колокольчик с бейджем непрочитанных
// в шапке; по клику открывается панель с лентой уведомлений (тема/текст/относительное
// время, отметка прочитано/непрочитано), действиями «прочитать» и «прочитать все».
// Данные — GET /api/notifications; при 404/501/сети деградируем мягко (панель
// показывает «нет уведомлений», бейдж скрыт). Только для вошедшего читателя.
import React from "react";
import { api } from "../api";
import type { Notification } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const CSS = `
.irb-nbell{position:relative;display:inline-flex;}
.irb-nbell__btn{position:relative;display:inline-flex;align-items:center;justify-content:center;
  background:transparent;color:#fff;border:1px solid rgba(255,255,255,.45);border-radius:8px;
  padding:5px 9px;cursor:pointer;}
.irb-nbell__btn--on{background:rgba(255,255,255,.25);}
.irb-nbell__badge{position:absolute;top:-6px;right:-6px;min-width:17px;height:17px;padding:0 4px;box-sizing:border-box;
  border-radius:999px;background:var(--error,#c0392b);color:#fff;font-size:10px;font-weight:700;line-height:17px;
  text-align:center;font-variant-numeric:tabular-nums;border:1.5px solid var(--accent);}
.irb-npanel{position:absolute;top:calc(100% + 8px);right:0;z-index:70;width:min(380px,92vw);
  background:var(--surface-card,#fff);color:var(--text-body);border:1px solid var(--border-strong,#cdd3da);
  border-radius:14px;box-shadow:var(--shadow-lg,0 16px 40px rgba(0,0,0,.22));overflow:hidden;
  display:flex;flex-direction:column;max-height:min(70vh,520px);}
.irb-npanel__head{display:flex;align-items:center;gap:8px;padding:13px 15px;border-bottom:1px solid var(--border-subtle);}
.irb-npanel__title{font-weight:600;font-size:var(--text-base,15px);}
.irb-npanel__count{font-size:var(--text-xs);color:var(--text-subtle);}
.irb-npanel__readall{margin-left:auto;background:none;border:none;color:var(--accent);cursor:pointer;
  font-size:var(--text-xs);font-family:var(--font-ui,inherit);padding:4px 6px;border-radius:6px;}
.irb-npanel__readall:hover{background:var(--accent-weak,#eef2f7);}
.irb-npanel__readall:disabled{color:var(--text-subtle);cursor:default;background:none;}
.irb-npanel__list{flex:1;overflow-y:auto;}
.irb-nitem{display:flex;gap:10px;align-items:flex-start;padding:12px 15px;border-top:1px solid var(--border-subtle);
  cursor:default;}
.irb-nitem:first-child{border-top:none;}
.irb-nitem--unread{background:var(--accent-weak,#eef2f7);}
.irb-nitem__dot{flex:none;width:8px;height:8px;border-radius:999px;margin-top:6px;background:transparent;}
.irb-nitem--unread .irb-nitem__dot{background:var(--accent);}
.irb-nitem__body{flex:1;min-width:0;}
.irb-nitem__subj{font-size:var(--text-sm,14px);font-weight:600;color:var(--text-strong);line-height:1.3;}
.irb-nitem__text{font-size:var(--text-xs,12.5px);color:var(--text-muted,var(--text-secondary));margin-top:2px;line-height:1.4;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.irb-nitem__time{font-size:var(--text-2xs,11px);color:var(--text-subtle);margin-top:4px;}
.irb-nitem__mark{flex:none;background:none;border:none;color:var(--text-subtle);cursor:pointer;padding:2px;border-radius:6px;}
.irb-nitem__mark:hover{color:var(--accent);background:var(--accent-weak,#eef2f7);}
.irb-npanel__empty{padding:30px 18px;text-align:center;color:var(--text-subtle);font-size:var(--text-sm);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-ninbox-css")) {
  const s = document.createElement("style"); s.id = "irb-ninbox-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Относительное время «N мин/ч/дн назад» из ISO/epoch строки; пусто если не парсится.
function relTime(ts?: string): string {
  if (!ts) return "";
  let d = new Date(ts);
  if (isNaN(d.getTime())) { const n = Number(ts); if (!isNaN(n) && n > 0) d = new Date(n * (n < 1e12 ? 1000 : 1)); }
  if (isNaN(d.getTime())) return "";
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 0) return "только что";
  if (sec < 60) return "только что";
  const min = Math.floor(sec / 60);
  if (min < 60) return min + " " + plural(min, "минуту", "минуты", "минут") + " назад";
  const hr = Math.floor(min / 60);
  if (hr < 24) return hr + " " + plural(hr, "час", "часа", "часов") + " назад";
  const day = Math.floor(hr / 24);
  if (day < 30) return day + " " + plural(day, "день", "дня", "дней") + " назад";
  return d.toLocaleDateString("ru-RU");
}
function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

export function NotificationInbox() {
  const [open, setOpen] = React.useState(false);
  const [items, setItems] = React.useState<Notification[] | null>(null);
  const [unread, setUnread] = React.useState(0);
  const [unavailable, setUnavailable] = React.useState(false);
  const wrapRef = React.useRef<HTMLDivElement>(null);

  const fetchAll = React.useCallback(async () => {
    const r = await api.notifications(false);
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setItems(r.json.data.items);
      setUnread(typeof r.json.data.unread === "number" ? r.json.data.unread : r.json.data.items.filter((n) => !n.read).length);
      setUnavailable(false);
    } else {
      // 404/501/сеть — модуль уведомлений ещё не подключён: тихо деградируем.
      setItems([]); setUnread(0); setUnavailable(true);
    }
  }, []);

  // Лёгкий поллинг счётчика (раз в 60 с), плюс загрузка при открытии панели.
  React.useEffect(() => {
    let alive = true;
    const poll = async () => {
      const r = await api.notifications(true);
      if (!alive) return;
      if (r.json?.ok && r.json.data) { setUnread(r.json.data.unread || 0); setUnavailable(false); }
      else setUnavailable(true);
    };
    poll();
    const t = setInterval(poll, 60000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // Закрытие по клику вне панели / Escape.
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next) fetchAll();
  }

  async function markOne(n: Notification) {
    if (n.read) return;
    // Оптимистично гасим непрочитанность.
    setItems((list) => (list || []).map((x) => x.id === n.id ? { ...x, read: true } : x));
    setUnread((u) => Math.max(0, u - 1));
    const r = await api.markNotificationRead({ id: n.id });
    if (r.json?.ok && r.json.data && typeof r.json.data.unread === "number") setUnread(r.json.data.unread);
  }
  async function markAll() {
    setItems((list) => (list || []).map((x) => ({ ...x, read: true })));
    setUnread(0);
    await api.markNotificationRead({ all: true });
  }

  return (
    <div className="irb-nbell" ref={wrapRef}>
      <button
        type="button" className={"irb-nbell__btn" + (open ? " irb-nbell__btn--on" : "")}
        onClick={toggle} aria-expanded={open} aria-haspopup="dialog"
        title="Уведомления" aria-label={"Уведомления" + (unread ? ", непрочитанных: " + unread : "")}
      >
        <Icon name="bell" size={17} />
        {unread > 0 && <span className="irb-nbell__badge" aria-hidden="true">{unread > 99 ? "99+" : unread}</span>}
      </button>

      {open && (
        <div className="irb-npanel" role="dialog" aria-label="Уведомления">
          <div className="irb-npanel__head">
            <span className="irb-npanel__title">Уведомления</span>
            {unread > 0 && <span className="irb-npanel__count">· {unread} новых</span>}
            <button type="button" className="irb-npanel__readall" onClick={markAll} disabled={unread === 0}>
              Прочитать все
            </button>
          </div>
          <div className="irb-npanel__list">
            {items === null ? (
              <div className="irb-npanel__empty">Загрузка…</div>
            ) : items.length === 0 ? (
              <div className="irb-npanel__empty">
                {unavailable ? "Уведомления появятся после подключения модуля оповещений." : "Новых уведомлений нет."}
              </div>
            ) : (
              items.map((n) => (
                <div key={String(n.id)} className={"irb-nitem" + (n.read ? "" : " irb-nitem--unread")}>
                  <span className="irb-nitem__dot" aria-hidden="true" />
                  <div className="irb-nitem__body">
                    <div className="irb-nitem__subj">{n.subject || "Уведомление"}</div>
                    {n.body && <div className="irb-nitem__text">{n.body}</div>}
                    {relTime(n.ts) && <div className="irb-nitem__time">{relTime(n.ts)}</div>}
                  </div>
                  {!n.read && (
                    <button type="button" className="irb-nitem__mark" onClick={() => markOne(n)} title="Отметить прочитанным" aria-label="Отметить прочитанным">
                      <Icon name="check" size={16} />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
