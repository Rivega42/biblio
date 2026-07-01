// Книговыдача (#185) — рабочий стол выдачи/возврата. Сценарий оператора:
//   1) ввести читательский билет (Enter) → формуляр (карточка, активные выдачи,
//      штрафы, служебные блоки: должник / превышен лимит / бронеблок);
//   2) поле экземпляра (инв./RFID, фокус автоматически) → Выдать (Enter) →
//      POST /api/circ/issue → формуляр обновляется; Возврат / Продление по строке.
// Клавиатура: билет → экземпляр → Enter выдаёт, поле очищается под следующий скан.
// Мягкая деградация: если /api/circ/* нет (404/501) — информер, приложение не падает.
import React from "react";
import { api } from "./api";
import type { CircFormular, CircLoan, CircFine, DebtorsReport } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .cdesk__* — НЕ пересекается с .stf__ / .irb-* (см. инцидент .irb-chip).
const CSS = `
.cdesk{font-family:var(--font-ui);}
.cdesk__scan{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;align-items:end;
  background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);padding:14px 16px;margin-bottom:16px;}
.cdesk__fld{display:flex;flex-direction:column;gap:5px;min-width:0;}
.cdesk__fld-lab{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);}
.cdesk__in{width:100%;box-sizing:border-box;padding:9px 12px;border-radius:var(--radius-md);
  border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);
  font-family:var(--font-ui);font-size:14px;}
.cdesk__in:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width,3px) var(--focus-ring-color,rgba(47,93,98,.25));}
.cdesk__in--mono{font-family:var(--font-mono);}
.cdesk__grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:18px;align-items:start;}
.cdesk__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);}
.cdesk__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.cdesk__rdr{display:flex;align-items:center;gap:13px;padding:14px 16px;border-bottom:1px solid var(--border-subtle);}
.cdesk__av{width:42px;height:42px;border-radius:var(--radius-full);background:var(--accent);color:var(--accent-fg);
  display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;flex:none;}
.cdesk__rdr-name{font-family:var(--font-display);font-weight:600;font-size:16px;line-height:1.2;}
.cdesk__rdr-sub{font-size:12px;color:var(--text-subtle);}
.cdesk__blocks{display:flex;flex-direction:column;gap:7px;padding:12px 16px;border-bottom:1px solid var(--border-subtle);}
.cdesk__block{display:flex;align-items:flex-start;gap:8px;font-size:12.5px;border-radius:var(--radius-md);padding:8px 10px;}
.cdesk__block--warn{background:var(--status-issued-bg,#FBEFD8);color:var(--status-issued,#B0791C);}
.cdesk__block--info{background:var(--accent-weak);color:var(--accent-press);}
.cdesk__loans{padding:4px 0;}
.cdesk__loan{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:11px 16px;border-bottom:1px solid var(--border-subtle);}
.cdesk__loan:last-child{border-bottom:none;}
.cdesk__loan-title{font-weight:600;font-size:13.5px;line-height:1.3;}
.cdesk__loan-meta{font-size:12px;color:var(--text-subtle);display:flex;gap:10px;flex-wrap:wrap;margin-top:3px;}
.cdesk__inv{font-family:var(--font-mono);font-size:11.5px;color:var(--text-muted);}
.cdesk__due{display:inline-flex;align-items:center;gap:4px;}
.cdesk__due--over{color:var(--danger-500);font-weight:600;}
.cdesk__loan-act{display:flex;gap:6px;flex:none;}
.cdesk__fines{padding:14px 16px;}
.cdesk__fine{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--border-subtle);}
.cdesk__fine:last-child{border-bottom:none;}
.cdesk__fine-amt{font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap;}
.cdesk__fines-total{display:flex;justify-content:space-between;margin-top:10px;padding-top:10px;border-top:2px solid var(--border-strong);font-weight:700;font-size:14px;}

/* типизированные баннеры блокировок (должник / штрафы / бронь / просрочка) */
.cdesk__block--danger{background:var(--status-issued-bg,#FBEFD8);color:var(--danger-500);border:1px solid var(--danger-500);}
.cdesk__block--hold{background:var(--accent-weak);color:var(--accent-press);}
.cdesk__block-strong{font-weight:600;}

/* клавиатурные подсказки */
.cdesk__hints{display:flex;gap:16px;flex-wrap:wrap;align-items:center;padding:8px 14px;margin-bottom:14px;
  background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);font-size:11.5px;color:var(--text-subtle);}
.cdesk__kbd{display:inline-flex;align-items:center;gap:5px;}
.cdesk__kbd kbd{font-family:var(--font-mono);font-size:10.5px;line-height:1;padding:3px 6px;border-radius:var(--radius-sm);
  background:var(--surface-card);border:1px solid var(--border-subtle);border-bottom-width:2px;color:var(--text-muted);}

/* панель массовых действий над выдачами */
.cdesk__bulk{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 16px;border-bottom:1px solid var(--border-subtle);
  background:var(--surface-sunken);font-size:12.5px;}
.cdesk__bulk-info{color:var(--text-muted);}
.cdesk__loan--sel{background:var(--accent-weak);}
.cdesk__chk{width:16px;height:16px;flex:none;cursor:pointer;accent-color:var(--accent);}
.cdesk__loanhead{display:flex;align-items:center;gap:10px;padding:9px 16px;border-bottom:1px solid var(--border-subtle);}
.cdesk__loanhead-cap{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);}
@media (max-width:920px){.cdesk__grid{grid-template-columns:1fr;}.cdesk__scan{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("cdesk-css")) {
  const s = document.createElement("style"); s.id = "cdesk-css"; s.textContent = CSS; document.head.appendChild(s);
}

function rdrInitials(name?: string, ticket?: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  if (parts.length === 1 && parts[0].length >= 2) return parts[0].slice(0, 2).toUpperCase();
  return (ticket || "ЧТ").slice(0, 2).toUpperCase();
}
function money(n?: number): string {
  if (n == null) return "—";
  return n.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ₽";
}

const CIRC_DB = "IBIS";

export function CirculationDesk({ toast }: { toast: ToastFn }) {
  const [ticket, setTicket] = React.useState("");
  const [item, setItem] = React.useState("");
  const [form, setForm] = React.useState<CircFormular | null>(null);
  const [fines, setFines] = React.useState<CircFine[] | null>(null);
  const [finesTotal, setFinesTotal] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [unavailable, setUnavailable] = React.useState(false);
  const [busyItem, setBusyItem] = React.useState<string | null>(null);
  const [issuing, setIssuing] = React.useState(false);
  // массовый возврат: набор выбранных инв./RFID + флаг идущей операции.
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = React.useState(false);
  const itemRef = React.useRef<HTMLInputElement>(null);

  const activeTicket = form?.reader.ticket || "";

  async function loadFormular(tk: string) {
    const t = tk.trim();
    if (!t) return;
    setLoading(true);
    const r = await api.circReader(t);
    setLoading(false);
    if (r.status === 404 || r.status === 501) { setUnavailable(true); return; }
    if (r.json?.ok && r.json.data && r.json.data.reader) {
      setForm(r.json.data);
      setUnavailable(false);
      setSelected(new Set()); // сброс выбора массового возврата под нового читателя
      // штрафы — отдельным запросом (мягко, без блокировки формуляра)
      void loadFines(r.json.data.reader.ticket || t);
      // фокус сразу в поле экземпляра — оператор сканирует книгу
      setTimeout(() => itemRef.current?.focus(), 0);
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите учётной записью с грантом circ.issue." });
    } else {
      setForm(null);
      toast({ variant: "warning", title: "Читатель не найден", message: "Билет " + t + " не зарегистрирован." });
    }
  }

  async function loadFines(tk: string) {
    const r = await api.circFines(tk);
    if (r.json?.ok && r.json.data) {
      setFines(r.json.data.items || []);
      setFinesTotal(r.json.data.total ?? 0);
    } else {
      setFines(null); setFinesTotal(null); // штрафов-эндпойнта нет — секцию прячем
    }
  }

  async function refresh() {
    if (activeTicket) await loadFormular(activeTicket);
  }

  async function issue() {
    const it = item.trim();
    if (!it || !activeTicket) return;
    setIssuing(true);
    const r = await api.circIssue(activeTicket, CIRC_DB, it);
    setIssuing(false);
    const d = r.json?.data;
    if (r.status === 200 && r.json?.ok && !(d && d.block)) {
      toast({ variant: "success", title: "Экземпляр выдан", message: (d?.loan?.title || it) + (d?.loan?.due ? " · до " + d.loan.due : "") });
      setItem("");
      await refresh();
      setTimeout(() => itemRef.current?.focus(), 0);
    } else if (d && d.block) {
      toast({ variant: "warning", title: "Выдача отклонена", message: d.block });
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Выдача недоступна", message: "Модуль книговыдачи ещё не подключён на этом сервере." });
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант circ.issue." });
    } else {
      toast({ variant: "error", title: "Не выдано", message: (d && d.message) || "Проверьте инвентарный номер экземпляра." });
    }
  }

  async function doReturn(loan: CircLoan) {
    setBusyItem(loan.item);
    const r = await api.circReturn(activeTicket, loan.db || CIRC_DB, loan.item);
    setBusyItem(null);
    if (r.status === 200 && r.json?.ok) {
      toast({ variant: "success", title: "Экземпляр принят", message: loan.title || loan.item });
      await refresh();
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Возврат недоступен", message: "Модуль книговыдачи ещё не подключён." });
    } else {
      toast({ variant: "error", title: "Не принято", message: r.json?.data?.message || "Повторите попытку." });
    }
  }

  async function doRenew(loan: CircLoan) {
    setBusyItem(loan.item);
    const r = await api.circRenew(activeTicket, loan.db || CIRC_DB, loan.item);
    setBusyItem(null);
    const d = r.json?.data;
    if (r.status === 200 && r.json?.ok && !(d && d.block)) {
      toast({ variant: "success", title: "Срок продлён", message: (loan.title || loan.item) + (d?.loan?.due ? " · до " + d.loan.due : "") });
      await refresh();
    } else if (d && d.block) {
      toast({ variant: "warning", title: "Продление отклонено", message: d.block });
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Продление недоступно", message: "Модуль книговыдачи ещё не подключён." });
    } else {
      toast({ variant: "error", title: "Не продлено", message: (d && d.message) || "Повторите попытку." });
    }
  }

  // --- массовый возврат ----------------------------------------------------
  const loanList = form?.loans || [];
  const toggleSel = (item: string) =>
    setSelected((s) => { const n = new Set(s); n.has(item) ? n.delete(item) : n.add(item); return n; });
  const allSelected = loanList.length > 0 && selected.size === loanList.length;
  const toggleAll = () =>
    setSelected(() => allSelected ? new Set() : new Set(loanList.map((l) => l.item)));

  // Принять возврат всех выбранных экземпляров последовательно (по одному вызову
  // circReturn на экземпляр — массового эндпойнта нет). Сводный тост по итогу.
  async function bulkReturn() {
    const picks = loanList.filter((l) => selected.has(l.item));
    if (!picks.length || !activeTicket) return;
    setBulkBusy(true);
    let ok = 0, fail = 0, unavailable = false;
    for (const ln of picks) {
      const r = await api.circReturn(activeTicket, ln.db || CIRC_DB, ln.item);
      if (r.status === 200 && r.json?.ok) ok++;
      else if (r.status === 404 || r.status === 501) { unavailable = true; break; }
      else fail++;
    }
    setBulkBusy(false);
    setSelected(new Set());
    if (unavailable) toast({ variant: "info", title: "Возврат недоступен", message: "Модуль книговыдачи ещё не подключён." });
    else if (fail === 0) toast({ variant: "success", title: "Массовый возврат", message: "Принято экземпляров: " + ok + "." });
    else toast({ variant: "warning", title: "Массовый возврат — частично", message: "Принято " + ok + ", не принято " + fail + ". Проверьте оставшиеся." });
    await refresh();
  }

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Книговыдача</h2>
        <span className="stf__pill">Выдача · возврат · продление</span>
        {form && <span className="stf__pill" style={{ background: "var(--status-issued-bg)", color: "var(--status-issued)", borderColor: "transparent" }}>{form.loans.length} на руках</span>}
        {form && form.loans.some((l) => l.overdue) && <span className="stf__pill" style={{ background: "var(--danger-500)", color: "#fff", borderColor: "transparent" }}>{form.loans.filter((l) => l.overdue).length} просрочено</span>}
      </div>
    </div>
  );

  // /api/circ/* отсутствует на сервере → информер, экран не падает.
  if (unavailable) return (
    <div className="cdesk">
      {head}
      <div className="cdesk__card" style={{ padding: 4 }}>
        <EmptyState icon="package" title="Книговыдача подключается отдельным модулем"
          description="Рабочий стол выдачи/возврата свёрстан в Стиле A и работает поверх движка книговыдачи (#185). На текущем сервере эндпойнты /api/circ/* ещё не развёрнуты — данные появятся после их публикации." />
      </div>
    </div>
  );

  const reader = form?.reader;
  const overdueCount = (form?.loans || []).filter((l) => l.overdue).length;
  // Типизированные баннеры: должник (danger), штрафы (danger), просрочка (warn),
  // бронь/удержание (hold), служебные блоки (warn), сообщения сервера (info).
  // Распознаём бронь по ключевым словам в тексте служебного блока.
  type BannerKind = "danger" | "warn" | "hold" | "info";
  const blocks: { kind: BannerKind; icon: "alert-octagon" | "alert-triangle" | "bookmark-check" | "info"; text: string; strong?: boolean }[] = [];
  if (reader?.debtor) blocks.push({ kind: "danger", icon: "alert-octagon", strong: true, text: "Читатель — должник. Выдача ограничена до погашения задолженности." });
  if (reader?.finesTotal) blocks.push({ kind: "danger", icon: "alert-octagon", text: "Непогашенные штрафы: " + money(reader.finesTotal) + "." });
  if (overdueCount > 0) blocks.push({ kind: "warn", icon: "alert-triangle", text: "Просрочено экземпляров: " + overdueCount + " — примите возврат или продлите." });
  (reader?.blocks || []).forEach((b) => {
    const isHold = /бронь|брон|удержан|hold|заказ/i.test(b);
    blocks.push({ kind: isHold ? "hold" : "warn", icon: isHold ? "bookmark-check" : "alert-triangle", text: b });
  });
  (form?.messages || []).forEach((m) => blocks.push({ kind: "info", icon: "info", text: m }));

  return (
    <div className="cdesk">
      {head}

      <DebtorsSummary />

      {/* ===== Сканер: билет → экземпляр ===== */}
      <div className="cdesk__scan">
        <div className="cdesk__fld">
          <label className="cdesk__fld-lab" htmlFor="cdesk-ticket">Читательский билет</label>
          <input id="cdesk-ticket" className="cdesk__in cdesk__in--mono" value={ticket} placeholder="скан / номер билета"
            autoComplete="off" autoFocus
            onChange={(e) => setTicket(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") loadFormular(ticket); else if (e.key === "Escape") setTicket(""); }} />
        </div>
        <div className="cdesk__fld">
          <label className="cdesk__fld-lab" htmlFor="cdesk-item">Экземпляр (инв. / RFID)</label>
          <input id="cdesk-item" ref={itemRef} className="cdesk__in cdesk__in--mono" value={item} placeholder={form ? "скан экземпляра → Enter" : "сначала загрузите формуляр"}
            autoComplete="off" disabled={!form}
            onChange={(e) => setItem(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") issue(); else if (e.key === "Escape") setItem(""); }} />
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!form
            ? <Button iconLeft="user" loading={loading} onClick={() => loadFormular(ticket)}>Формуляр</Button>
            : <Button iconLeft="log-out" loading={issuing} disabled={!item.trim()} onClick={issue}>Выдать</Button>}
        </div>
      </div>

      {/* ===== Клавиатурные подсказки оператора ===== */}
      <div className="cdesk__hints" aria-hidden="true">
        <span className="cdesk__kbd"><kbd>Enter</kbd> в поле билета — открыть формуляр</span>
        <span className="cdesk__kbd"><kbd>Enter</kbd> в поле экземпляра — выдать и очистить под след. скан</span>
        <span className="cdesk__kbd"><kbd>Esc</kbd> — очистить текущее поле</span>
      </div>

      {!form ? (
        <div className="cdesk__card" style={{ padding: 4 }}>
          <EmptyState icon="credit-card" title="Введите читательский билет"
            description="Отсканируйте или наберите номер билета и нажмите Enter — откроется формуляр читателя: активные выдачи, сроки и штрафы. Затем сканируйте экземпляры для выдачи." />
        </div>
      ) : (
        <div className="cdesk__grid">
          {/* ===== Формуляр: карточка + блоки + выдачи ===== */}
          <div className="cdesk__card">
            <div className="cdesk__rdr">
              <span className="cdesk__av" aria-hidden="true">{rdrInitials(reader?.name, reader?.ticket)}</span>
              <div style={{ minWidth: 0 }}>
                <div className="cdesk__rdr-name">{reader?.name || "Читатель"}</div>
                <div className="cdesk__rdr-sub">
                  билет {reader?.ticket}
                  {reader?.category ? " · " + reader.category : ""}
                  {reader?.status ? " · " + reader.status : ""}
                </div>
              </div>
              <div style={{ marginLeft: "auto" }}>
                <Button variant="ghost" size="sm" iconLeft="refresh-cw" onClick={() => { setForm(null); setFines(null); setFinesTotal(null); setTicket(""); setItem(""); setSelected(new Set()); }}>Другой читатель</Button>
              </div>
            </div>

            {blocks.length > 0 && (
              <div className="cdesk__blocks">
                {blocks.map((b, i) => (
                  <div key={i} className={"cdesk__block cdesk__block--" + b.kind}>
                    <Icon name={b.icon} size={15} style={{ flex: "none", marginTop: 1 }} />
                    <span className={b.strong ? "cdesk__block-strong" : undefined}>{b.text}</span>
                  </div>
                ))}
              </div>
            )}

            {/* шапка раздела выдач + панель массового возврата */}
            {form.loans.length > 0 && (
              <div className="cdesk__loanhead">
                <input type="checkbox" className="cdesk__chk" checked={allSelected} onChange={toggleAll}
                  aria-label="Выбрать все выдачи" title="Выбрать все" />
                <span className="cdesk__loanhead-cap">На руках · {form.loans.length}</span>
                {selected.size > 0 && (
                  <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="cdesk__bulk-info">Выбрано: {selected.size}</span>
                    <Button variant="secondary" size="sm" iconLeft="arrow-left" loading={bulkBusy} onClick={bulkReturn}>Принять выбранные</Button>
                    <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>Снять выбор</Button>
                  </div>
                )}
              </div>
            )}

            <div className="cdesk__loans">
              {form.loans.length === 0 ? (
                <div style={{ padding: "18px 16px" }}>
                  <EmptyState icon="check-circle" title="На руках ничего нет" description="У читателя нет активных выдач. Отсканируйте экземпляр выше, чтобы выдать." />
                </div>
              ) : form.loans.map((ln, i) => {
                const sel = selected.has(ln.item);
                return (
                <div className={"cdesk__loan" + (sel ? " cdesk__loan--sel" : "")} key={ln.item + ":" + i}>
                  <input type="checkbox" className="cdesk__chk" checked={sel} onChange={() => toggleSel(ln.item)}
                    aria-label={"Выбрать для возврата: " + (ln.title || ln.item)} />
                  <div style={{ minWidth: 0 }}>
                    <div className="cdesk__loan-title">{ln.title || "Издание"}</div>
                    <div className="cdesk__loan-meta">
                      <span className="cdesk__inv">{ln.item}</span>
                      {ln.author && <span>{ln.author}</span>}
                      {ln.issued && <span>выдано {ln.issued}</span>}
                      {ln.due && <span className={"cdesk__due" + (ln.overdue ? " cdesk__due--over" : "")}>
                        <Icon name={ln.overdue ? "alert-triangle" : "clock"} size={12} /> до {ln.due}{ln.overdue ? " · просрочено" : ""}
                      </span>}
                    </div>
                  </div>
                  <div className="cdesk__loan-act">
                    {ln.renewable !== false && (
                      <Button variant="secondary" size="sm" iconLeft="rotate-cw" loading={busyItem === ln.item} onClick={() => doRenew(ln)}>Продлить</Button>
                    )}
                    <Button variant="secondary" size="sm" iconLeft="arrow-left" loading={busyItem === ln.item} onClick={() => doReturn(ln)}>Возврат</Button>
                  </div>
                </div>
              ); })}
            </div>
          </div>

          {/* ===== Штрафы ===== */}
          <aside className="cdesk__card cdesk__fines" aria-label="Штрафы читателя">
            <span className="cdesk__cap">Штрафы и задолженность</span>
            {fines === null ? (
              <div style={{ marginTop: 12, fontSize: 12.5, color: "var(--text-subtle)" }}>
                Сведения о штрафах подгружаются модулем книговыдачи.
              </div>
            ) : fines.length === 0 ? (
              <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "var(--success)" }}>
                <Icon name="check-circle" size={15} /> Задолженности нет.
              </div>
            ) : (
              <div style={{ marginTop: 12 }}>
                {fines.map((f, i) => (
                  <div className="cdesk__fine" key={f.id ?? i}>
                    <span style={{ minWidth: 0 }}>
                      {f.reason || "Начисление"}
                      {f.date ? <span style={{ color: "var(--text-subtle)" }}> · {f.date}</span> : null}
                      {f.paid ? <span style={{ color: "var(--success)" }}> · погашено</span> : null}
                    </span>
                    <span className="cdesk__fine-amt" style={{ color: f.paid ? "var(--text-subtle)" : "var(--danger-500)" }}>{money(f.amount)}</span>
                  </div>
                ))}
                <div className="cdesk__fines-total">
                  <span>Итого к оплате</span>
                  <span style={{ color: (finesTotal || 0) > 0 ? "var(--danger-500)" : "var(--success)" }}>{money(finesTotal || 0)}</span>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

// ===== Сводка по должникам (#C6) ============================================
// Компактная карточка над рабочим столом: читателей с долгом, сумма к взысканию
// (просрочка/утеря). Данные — GET /api/circ/debts (сводный отчёт, staff). При
// 404/403 или отсутствии долгов блок не рендерится.
function rub(kopecks: number | undefined): string {
  return ((kopecks || 0) / 100).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ₽";
}
function DebtorsSummary() {
  const [rep, setRep] = React.useState<DebtorsReport | null>(null);
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.circDebtsReport();
      if (!alive) return;
      if (r.json?.ok && r.json.data?.report) setRep(r.json.data.report);
    })();
    return () => { alive = false; };
  }, []);
  if (!rep || !rep.readers_with_debt) return null;
  const cells: { label: string; val: string; danger?: boolean }[] = [
    { label: "Читателей с долгом", val: String(rep.readers_with_debt), danger: true },
    { label: "К взысканию", val: rub(rep.total_owed), danger: true },
    { label: "Просрочка", val: rub(rep.by_kind?.overdue) },
    { label: "Утеря", val: rub(rep.by_kind?.lost) },
  ];
  return (
    <div className="cdesk__card" style={{ padding: 14, marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <Icon name="alert-triangle" size={16} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>Должники</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 10 }}>
        {cells.map((c) => (
          <div key={c.label} style={{ background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", padding: "10px 12px" }}>
            <div style={{ fontWeight: 700, fontSize: 18, lineHeight: 1.1, color: c.danger ? "var(--danger-500,#c0392b)" : "var(--text-strong)" }}>{c.val}</div>
            <div style={{ fontSize: 11, color: "var(--text-subtle)", marginTop: 3 }}>{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
