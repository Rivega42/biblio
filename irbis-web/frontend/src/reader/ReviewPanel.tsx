// Отзывы и оценки на карточке записи (#134). Показываем средний балл (звёзды) +
// число отзывов и ленту отзывов. Вошедший читатель может оставить / изменить /
// удалить СВОЙ отзыв (1–5 звёзд + текст). Гость видит отзывы только для чтения и
// мягкую подсказку «войдите, чтобы оценить».
//
// Грациозная деградация: при 404/501 эндпойнтов отзывов (модуль ещё не подключён)
// весь блок скрывается (unavailable) — карточка записи не падает и не пустует
// заглушками. Запись/обновление/удаление при ошибке откатываются с мягким тостом.
import React from "react";
import { api } from "../api";
import type { Review, ReviewsResult } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";

type Toast = (t: { variant: ToastVariant; title: string; message?: string }) => void;

const CSS = `
.irb-rev{margin-top:26px;border-top:1px solid var(--border-subtle);padding-top:18px;}
.irb-rev__head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 14px;}
.irb-rev__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-xl,1.25rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);}
.irb-rev__avg{display:inline-flex;align-items:center;gap:8px;}
.irb-rev__avgnum{font-family:var(--font-display,var(--font-serif));font-weight:600;font-size:var(--text-lg);
  font-variant-numeric:tabular-nums;color:var(--text-strong);}
.irb-rev__count{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-stars{display:inline-flex;gap:2px;line-height:0;}
.irb-stars--btns button{background:none;border:none;padding:1px;cursor:pointer;line-height:0;color:inherit;}
.irb-stars--btns button:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:1px;border-radius:3px;}
.irb-rev__star-on{color:var(--accent);}
.irb-rev__star-off{color:var(--border-strong,#cdd3da);}
.irb-rev__list{display:flex;flex-direction:column;gap:14px;}
.irb-rev__item{display:flex;gap:12px;}
.irb-rev__ava{width:36px;height:36px;flex:none;border-radius:999px;background:var(--accent-weak,var(--accent-tint));
  color:var(--accent);display:flex;align-items:center;justify-content:center;font:600 14px var(--font-ui,inherit);}
.irb-rev__body{flex:1;min-width:0;}
.irb-rev__by{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.irb-rev__name{font-weight:600;font-size:var(--text-sm);color:var(--text-strong);}
.irb-rev__ts{font-size:var(--text-xs);color:var(--text-subtle);}
.irb-rev__text{font-size:var(--text-sm);color:var(--text-body);line-height:1.5;margin:5px 0 0;white-space:pre-wrap;overflow-wrap:break-word;}
.irb-rev__form{background:var(--surface-sunken,#f5f5f5);border:1px solid var(--border-subtle);border-radius:var(--radius-lg,13px);padding:14px 16px;margin:0 0 18px;}
.irb-rev__formhd{font-weight:600;font-size:var(--text-sm);margin:0 0 10px;color:var(--text-strong);}
.irb-rev__ta{width:100%;box-sizing:border-box;margin-top:10px;padding:9px 11px;border-radius:8px;
  border:1px solid var(--border-strong,#cdd3da);font-family:var(--font-ui,inherit);font-size:var(--text-sm);
  background:var(--surface-card,#fff);color:var(--text-body);resize:vertical;min-height:64px;}
.irb-rev__guest{display:flex;align-items:center;gap:8px;background:var(--surface-sunken,#f5f5f5);
  border:1px solid var(--border-subtle);border-radius:var(--radius-lg,13px);padding:11px 14px;margin:0 0 18px;
  font-size:var(--text-sm);color:var(--text-subtle);}
.irb-rev__mineactions{display:flex;gap:10px;margin-top:6px;}
.irb-rev__minebtn{background:none;border:none;cursor:pointer;color:var(--accent);font-size:var(--text-xs);
  font-family:var(--font-ui,inherit);padding:0;display:inline-flex;align-items:center;gap:4px;}
.irb-rev__minebtn--danger{color:var(--error,var(--danger-500));}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-rev-css")) {
  const s = document.createElement("style"); s.id = "irb-rev-css"; s.textContent = CSS; document.head.appendChild(s);
}

function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}
function initials(name?: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "ЧТ";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}
// Метка времени: ISO/число → «дд.мм.гггг»; иначе показываем как есть.
function fmtTs(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// Звёзды только для чтения (агрегат / чужой отзыв).
function Stars({ value, size = 16 }: { value: number; size?: number }) {
  return (
    <span className="irb-stars" aria-label={"Оценка: " + (Math.round(value * 10) / 10) + " из 5"}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Icon key={n} name="star" size={size}
          className={n <= Math.round(value) ? "irb-rev__star-on" : "irb-rev__star-off"}
          style={n <= Math.round(value) ? { fill: "currentColor" } : undefined} />
      ))}
    </span>
  );
}

// Интерактивный выбор звёзд (форма отзыва).
function StarInput({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const [hover, setHover] = React.useState(0);
  const shown = hover || value;
  return (
    <span className="irb-stars irb-stars--btns" role="radiogroup" aria-label="Ваша оценка" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={n + " из 5"}
          onMouseEnter={() => setHover(n)} onClick={() => onChange(n)}>
          <Icon name="star" size={26}
            className={n <= shown ? "irb-rev__star-on" : "irb-rev__star-off"}
            style={n <= shown ? { fill: "currentColor" } : undefined} />
        </button>
      ))}
    </span>
  );
}

export function ReviewPanel({ db, mfn, loggedIn, readerName, toast }: {
  db: string; mfn: number; loggedIn: boolean; readerName?: string; toast: Toast;
}) {
  const [data, setData] = React.useState<ReviewsResult | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [rating, setRating] = React.useState(0);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    const r = await api.reviews(db, mfn);
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setData(r.json.data); setUnavailable(false);
    } else {
      setData(null); setUnavailable(true);
    }
  }, [db, mfn]);

  React.useEffect(() => { setData(null); setUnavailable(false); setEditing(false); load(); }, [load]);

  // Найти отзыв текущего читателя: явный mine, либо флаг mine в списке.
  const mine: Review | null = data ? (data.mine || data.items.find((x) => x.mine) || null) : null;

  function openForm() {
    setRating(mine?.rating || 0);
    setText(mine?.text || "");
    setEditing(true);
  }

  async function submit() {
    if (rating < 1) { toast({ variant: "warning", title: "Поставьте оценку", message: "Выберите от 1 до 5 звёзд." }); return; }
    setBusy(true);
    const r = await api.postReview(db, mfn, rating, text.trim() || undefined);
    setBusy(false);
    if (r.status === 200 && r.json?.ok) {
      setEditing(false);
      toast({ variant: "success", title: mine ? "Отзыв обновлён" : "Спасибо за отзыв" });
      load();
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." });
    } else {
      toast({ variant: "error", title: "Не удалось сохранить отзыв", message: "Повторите попытку позже." });
    }
  }

  async function remove() {
    if (!mine) return;
    setBusy(true);
    const r = await api.deleteReview(mine.id);
    setBusy(false);
    if (r.status === 200) {
      toast({ variant: "success", title: "Отзыв удалён" });
      setEditing(false);
      load();
    } else {
      toast({ variant: "error", title: "Не удалось удалить отзыв", message: "Повторите попытку позже." });
    }
  }

  // Модуль отзывов ещё не подключён → блок скрываем (мягкая деградация).
  if (unavailable) return null;
  if (data === null) {
    return (
      <div className="irb-rev">
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Загрузка отзывов…</div>
      </div>
    );
  }

  const { avg, count, items } = data;
  // Прочие отзывы (без своего, если он выводится отдельной формой выше).
  const others = mine ? items.filter((x) => x.id !== mine.id) : items;

  return (
    <div className="irb-rev">
      <div className="irb-rev__head">
        <h3 className="irb-rev__title">Отзывы и оценки</h3>
        {count > 0 ? (
          <span className="irb-rev__avg">
            <Stars value={avg} />
            <span className="irb-rev__avgnum">{(Math.round(avg * 10) / 10).toString().replace(".", ",")}</span>
            <span className="irb-rev__count">· {count} {plural(count, "отзыв", "отзыва", "отзывов")}</span>
          </span>
        ) : (
          <span className="irb-rev__count">Пока нет отзывов</span>
        )}
        {loggedIn && !editing && (
          <Button size="sm" variant="secondary" iconLeft={mine ? "edit" : "star"} onClick={openForm} style={{ marginLeft: "auto" }}>
            {mine ? "Изменить отзыв" : "Оценить"}
          </Button>
        )}
      </div>

      {/* Форма отзыва — вошедшему, по запросу. */}
      {loggedIn && editing && (
        <div className="irb-rev__form">
          <div className="irb-rev__formhd">{mine ? "Ваш отзыв" : "Оставьте отзыв"}</div>
          <StarInput value={rating} onChange={setRating} />
          <textarea className="irb-rev__ta" value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Поделитесь впечатлением об издании (необязательно)…" aria-label="Текст отзыва" maxLength={2000} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
            {mine && <Button size="sm" variant="ghost" iconLeft="trash" loading={busy} onClick={remove} style={{ marginRight: "auto", color: "var(--error,var(--danger-500))" }}>Удалить</Button>}
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Отмена</Button>
            <Button size="sm" iconLeft="check" loading={busy} onClick={submit}>{mine ? "Сохранить" : "Опубликовать"}</Button>
          </div>
        </div>
      )}

      {/* Гость — read-only + мягкое приглашение войти. */}
      {!loggedIn && (
        <div className="irb-rev__guest">
          <Icon name="info" size={16} /> Войдите по читательскому билету, чтобы оценить издание.
        </div>
      )}

      {/* Свой отзыв сверху (если есть и форма закрыта). */}
      {mine && !editing && (
        <div className="irb-rev__list" style={{ marginBottom: others.length ? 18 : 0 }}>
          <div className="irb-rev__item">
            <span className="irb-rev__ava" aria-hidden="true">{initials(readerName || mine.readerName || "Вы")}</span>
            <div className="irb-rev__body">
              <div className="irb-rev__by">
                <span className="irb-rev__name">{mine.readerName || readerName || "Ваш отзыв"}</span>
                <span style={{ fontSize: "var(--text-2xs,11px)", fontWeight: 600, color: "var(--accent)", background: "var(--accent-weak,#eef2f7)", borderRadius: 999, padding: "1px 8px" }}>ваш отзыв</span>
                <Stars value={mine.rating} size={14} />
                {mine.ts && <span className="irb-rev__ts">{fmtTs(mine.ts)}</span>}
              </div>
              {mine.text && <p className="irb-rev__text">{mine.text}</p>}
              <div className="irb-rev__mineactions">
                <button type="button" className="irb-rev__minebtn" onClick={openForm}><Icon name="edit" size={13} /> Изменить</button>
                <button type="button" className="irb-rev__minebtn irb-rev__minebtn--danger" onClick={remove}><Icon name="trash" size={13} /> Удалить</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Лента остальных отзывов. */}
      {others.length > 0 ? (
        <div className="irb-rev__list">
          {others.map((rv) => (
            <div key={rv.id} className="irb-rev__item">
              <span className="irb-rev__ava" aria-hidden="true">{initials(rv.readerName)}</span>
              <div className="irb-rev__body">
                <div className="irb-rev__by">
                  <span className="irb-rev__name">{rv.readerName || "Читатель"}</span>
                  <Stars value={rv.rating} size={14} />
                  {rv.ts && <span className="irb-rev__ts">{fmtTs(rv.ts)}</span>}
                </div>
                {rv.text && <p className="irb-rev__text">{rv.text}</p>}
              </div>
            </div>
          ))}
        </div>
      ) : (!mine && count === 0 ? (
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>
          {loggedIn ? "Будьте первым, кто оценит это издание." : "Отзывов пока нет."}
        </div>
      ) : null)}
    </div>
  );
}
