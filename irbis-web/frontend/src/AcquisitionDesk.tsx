// Комплектование (#184) — рабочий стол комплектатора. Сквозной поток:
//   заказ → поступление → каталог. Оператор оформляет заказ (издание, поставщик,
//   экземпляры, цена, источник финансирования) → POST /api/acq/order; заказ
//   попадает в список. По заказу оформляется поступление (число экземпляров,
//   акт/счёт, инв. номера) → POST /api/acq/receive → создаётся запись КСУ и
//   запускается ToCat (создание/правка каталожной записи). Результат показывает
//   номер КСУ и MFN созданной/обновлённой записи — заказ→поступление→каталог
//   виден из конца в конец. Отдельно — поиск записи КСУ по номеру.
// Мягкая деградация: нет /api/acq/* (404/501) — информер, приложение не падает.
import React from "react";
import { api } from "./api";
import type { AcqOrder, KsuEntry, AcqReceiveResult } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .acq__* — не пересекается с .stf__ / .cdesk__ / .irb-*.
const CSS = `
.acq{font-family:var(--font-ui);}
.acq__grid{display:grid;grid-template-columns:340px minmax(0,1fr);gap:18px;align-items:start;}
.acq__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);}
.acq__card-pad{padding:14px 16px;}
.acq__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);display:block;margin-bottom:12px;}
.acq__fld{display:flex;flex-direction:column;gap:5px;margin-bottom:11px;}
.acq__fld-lab{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.acq__in,.acq__sel{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);
  border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);
  font-family:var(--font-ui);font-size:13.5px;}
.acq__in:focus,.acq__sel:focus{outline:none;border-color:var(--accent);}
.acq__in--mono{font-family:var(--font-mono);}
.acq__row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.acq__orders{padding:0;}
.acq__order{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:start;padding:12px 16px;border-bottom:1px solid var(--border-subtle);cursor:pointer;background:var(--surface-card);text-align:left;width:100%;border-left:none;border-right:none;border-top:none;font:inherit;color:inherit;}
.acq__order:last-child{border-bottom:none;}
.acq__order:hover{background:var(--surface-hover);}
.acq__order--on{background:var(--accent-weak);}
.acq__order--on:hover{background:var(--accent-weak);}
.acq__order-title{font-weight:600;font-size:13.5px;line-height:1.3;}
.acq__order-meta{font-size:12px;color:var(--text-subtle);display:flex;gap:10px;flex-wrap:wrap;margin-top:3px;}
.acq__order-r{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none;}
.acq__st{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);white-space:nowrap;}
.acq__st--new{background:var(--accent-weak);color:var(--accent-press);}
.acq__st--recv{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);}
.acq__st--part{background:var(--status-issued-bg,#FBEFD8);color:var(--status-issued,#B0791C);}
.acq__st--cancel{background:var(--surface-hover);color:var(--text-subtle);}
.acq__flow{display:flex;align-items:center;gap:8px;margin:10px 0;flex-wrap:wrap;}
.acq__flow-step{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:var(--radius-full);font-size:12px;font-weight:600;background:var(--surface-sunken);color:var(--text-subtle);border:1px solid var(--border-subtle);}
.acq__flow-step--done{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);border-color:transparent;}
.acq__flow-step--active{background:var(--accent-weak);color:var(--accent-press);border-color:transparent;}
.acq__cat{margin-top:12px;padding:13px 15px;border-radius:var(--radius-md);background:var(--status-available-bg,#E3F0E4);border:1px solid transparent;display:flex;align-items:flex-start;gap:10px;}
.acq__cat-mfn{font-family:var(--font-mono);font-weight:700;font-size:15px;color:var(--status-available,#3C7D3F);}
.acq__ksu{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-top:10px;font-size:12.5px;}
.acq__ksu-k{color:var(--text-subtle);}
.acq__ksu-v{font-weight:600;font-variant-numeric:tabular-nums;}
.acq__lookup{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end;}
@media (max-width:920px){.acq__grid{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("acq-css")) {
  const s = document.createElement("style"); s.id = "acq-css"; s.textContent = CSS; document.head.appendChild(s);
}

function money(n?: number): string {
  if (n == null) return "—";
  return n.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ₽";
}

// Бэкенд (access/acquisition.py) отдаёт «сырую» строку acq_order с именами полей
// sqlite-схемы: copies_ordered / copies_received / status='cancelled'. Фронт-тип
// AcqOrder ждёт copies / received / canceled. Нормализуем при каждом приёме строки
// от сервера, чтобы рендер и statusOf работали единообразно (и для созданного
// заказа, и для обновлённого после поступления). Терпимо к обоим вариантам имён.
function normOrder(raw: any): AcqOrder {
  if (!raw || typeof raw !== "object") return raw;
  const copies = raw.copies != null ? raw.copies : (raw.copies_ordered != null ? raw.copies_ordered : 0);
  const received = raw.received != null ? raw.received : (raw.copies_received != null ? raw.copies_received : 0);
  const status = raw.status === "cancelled" ? "canceled" : raw.status;
  return {
    id: raw.id,
    title: raw.title,
    author: raw.author || undefined,
    supplier: raw.supplier || undefined,
    copies,
    received,
    price: raw.price != null ? raw.price : undefined,
    funding_source: raw.funding_source || raw.fundingSource || undefined,
    status,
    statusLabel: raw.statusLabel,
    created: raw.created,
    ksuNo: raw.ksuNo,
    canceled: status === "canceled" || raw.canceled === true,
  };
}

// Результат POST /api/acq/receive у бэкенда: {receipt, ksu, order, inventory,
// sum, catalog_mfn, catalog_action, lendable}. Раскладываем в плоскую форму,
// которую рендерит карточка результата (КСУ-номер, MFN, создана/обновлена).
function normReceive(d: any): AcqReceiveResult & { inventory?: string[]; lendable?: string[]; order?: AcqOrder } {
  const ksuRow = d?.ksu || null;
  const ksuNo = ksuRow?.ksu_no || ksuRow?.no || d?.ksuNo;
  const mfn = d?.catalog_mfn != null ? d.catalog_mfn : (d?.mfn != null ? d.mfn : undefined);
  const action = d?.catalog_action || (d?.created ? "created" : undefined);
  return {
    ksu: ksuRow ? {
      no: ksuNo,
      copies: ksuRow.copies,
      sum: ksuRow.total_sum != null ? ksuRow.total_sum : ksuRow.sum,
      actRef: ksuRow.act_ref || ksuRow.actRef,
    } : undefined,
    ksuNo,
    mfn,
    db: d?.db || "IBIS",
    created: action === "created",
    copies: Array.isArray(d?.inventory) ? d.inventory.length : (d?.copies != null ? d.copies : ksuRow?.copies),
    inventory: Array.isArray(d?.inventory) ? d.inventory : undefined,
    lendable: Array.isArray(d?.lendable) ? d.lendable : undefined,
    order: d?.order ? normOrder(d.order) : undefined,
    message: d?.message,
  };
}

// Строка КСУ от GET /api/acq/ksu (access/acquisition.py get_ksu): ksu_no / titles
// / copies / total_sum / act_ref. Раскладываем в KsuEntry.
function normKsu(raw: any): KsuEntry | null {
  if (!raw || typeof raw !== "object") return null;
  return {
    no: raw.ksu_no || raw.no,
    copies: raw.copies,
    sum: raw.total_sum != null ? raw.total_sum : raw.sum,
    actRef: raw.act_ref || raw.actRef,
    supplier: raw.supplier,
  };
}

// Метка статуса заказа: машинный код → русская подпись + класс «таблетки».
function statusOf(o: AcqOrder): { label: string; cls: string } {
  if (o.canceled || o.status === "canceled") return { label: o.statusLabel || "Отменён", cls: "cancel" };
  const recv = o.received || 0;
  if (o.status === "received" || (recv >= o.copies && o.copies > 0)) return { label: o.statusLabel || "Получен", cls: "recv" };
  if (recv > 0) return { label: o.statusLabel || ("Получено " + recv + "/" + o.copies), cls: "part" };
  return { label: o.statusLabel || "Создан", cls: "new" };
}

const FUNDING = ["Бюджет", "Внебюджет", "Грант", "Дар", "Обмен", "Замена утерянных"];

// Список заказов «за эту сессию». У бэкенда НЕТ endpoint'а ленты заказов
// (GET /api/acq/order требует id; список не отдаётся), поэтому деск держит
// заказы, созданные/принятые в этой сессии, на клиенте — и доуточняет каждый
// по GET /api/acq/order?id= после операций. Это не зависит от ИРБИС: вся
// учётная история — в own-store (AcquisitionStore).
export function AcquisitionDesk({ toast }: { toast: ToastFn }) {
  const [orders, setOrders] = React.useState<AcqOrder[]>([]);
  const [unavailable, setUnavailable] = React.useState(false);
  const [selId, setSelId] = React.useState<string | number | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [receiving, setReceiving] = React.useState(false);
  const [busyId, setBusyId] = React.useState<string | number | null>(null);
  const [lastReceive, setLastReceive] = React.useState<(AcqReceiveResult & { inventory?: string[]; lendable?: string[] }) | null>(null);

  // форма заказа
  const [title, setTitle] = React.useState("");
  const [author, setAuthor] = React.useState("");
  const [supplier, setSupplier] = React.useState("");
  const [copies, setCopies] = React.useState("1");
  const [price, setPrice] = React.useState("");
  const [funding, setFunding] = React.useState(FUNDING[0]);

  // форма поступления (по выбранному заказу)
  const [rcvKsuNo, setRcvKsuNo] = React.useState("");
  const [rcvCopies, setRcvCopies] = React.useState("");
  const [rcvUnit, setRcvUnit] = React.useState("");
  const [rcvInv, setRcvInv] = React.useState("");
  const [rcvAct, setRcvAct] = React.useState("");

  // поиск КСУ
  const [ksuQuery, setKsuQuery] = React.useState("");
  const [ksuResult, setKsuResult] = React.useState<KsuEntry | null | "none">(null);

  const selected = orders.find((o) => o.id === selId) || null;
  // Подсказка № КСУ по умолчанию: «<год>-1» (88^A год+№). Оператор может заменить.
  const ksuSuggest = String(new Date().getFullYear()) + "-1";

  // Вмержить/обновить заказ в клиентский список (по id). Новый — в начало.
  function upsertOrder(o: AcqOrder) {
    setOrders((os) => {
      const i = os.findIndex((x) => x.id === o.id);
      if (i < 0) return [o].concat(os);
      const next = os.slice(); next[i] = o; return next;
    });
  }

  // Доуточнить один заказ с сервера (GET /api/acq/order?id=) после операции —
  // чтобы статус/received соответствовали own-store, а не оптимистичной правке.
  async function refreshOrder(id: string | number) {
    const r = await api.acqGetOrder(id);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      const raw = (r.json.data as any).order || r.json.data;
      if (raw && raw.id != null) upsertOrder(normOrder(raw));
    }
  }

  async function createOrder() {
    const t = title.trim(); const c = parseInt(copies, 10);
    if (!t) { toast({ variant: "info", title: "Укажите заглавие", message: "Заглавие издания обязательно для заказа." }); return; }
    if (!c || c < 1) { toast({ variant: "info", title: "Проверьте число экземпляров", message: "Число экземпляров должно быть ≥ 1." }); return; }
    setCreating(true);
    const r = await api.acqOrder({
      title: t, author: author.trim() || undefined, supplier: supplier.trim() || undefined,
      copies: c, price: price.trim() ? parseFloat(price.replace(",", ".")) : undefined,
      funding_source: funding,
    });
    setCreating(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      const created = normOrder(r.json.data);
      toast({ variant: "success", title: "Заказ создан", message: t + " · " + c + " экз." });
      upsertOrder(created);
      setSelId(created.id);
      setUnavailable(false);
      setTitle(""); setAuthor(""); setSupplier(""); setCopies("1"); setPrice("");
    } else if (r.status === 404 || r.status === 501) {
      setUnavailable(true);
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант acq.receipt (роль администратора)." });
    } else {
      toast({ variant: "error", title: "Заказ не создан", message: r.json?.error?.message || "Повторите попытку." });
    }
  }

  async function cancelOrder(o: AcqOrder) {
    setBusyId(o.id);
    const r = await api.acqCancelOrder(o.id);
    setBusyId(null);
    if (r.status === 200 && r.json?.ok) {
      toast({ variant: "success", title: "Заказ отменён", message: o.title });
      const updated = r.json.data ? normOrder(r.json.data) : { ...o, canceled: true, status: "canceled" };
      upsertOrder(updated);
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Отмена недоступна", message: "Модуль комплектования ещё не подключён." });
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант acq.receipt (роль администратора)." });
    } else {
      toast({ variant: "error", title: "Не отменено", message: r.json?.error?.message || "Повторите попытку." });
    }
  }

  async function receive() {
    if (!selected) return;
    const c = parseInt(rcvCopies || String(selected.copies), 10);
    if (!c || c < 1) { toast({ variant: "info", title: "Укажите число экземпляров", message: "Сколько экземпляров поступило?" }); return; }
    // Бэкенд требует №КСУ (acq_receive → 400 'ksuNo required', если пусто). В UI
    // подставляем подсказку (год+«-1») как дефолт, но даём оператору исправить.
    const ksuNo = rcvKsuNo.trim() || ksuSuggest;
    if (!ksuNo) { toast({ variant: "info", title: "Укажите № КСУ", message: "Номер записи КСУ обязателен для поступления." }); return; }
    const invNumbers = rcvInv.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean);
    if (invNumbers.length && invNumbers.length !== c) {
      toast({ variant: "info", title: "Проверьте инв. номера", message: "Инв. номеров (" + invNumbers.length + ") должно быть ровно " + c + " — или оставьте поле пустым (авто-нумерация)." });
      return;
    }
    setReceiving(true);
    const r = await api.acqReceive({
      orderId: selected.id, ksuNo, copies: c,
      unitPrice: rcvUnit.trim() ? parseFloat(rcvUnit.replace(",", ".")) : undefined,
      invNumbers: invNumbers.length ? invNumbers : undefined,
      actRef: rcvAct.trim() || undefined,
    });
    setReceiving(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      const d = normReceive(r.json.data);
      setLastReceive(d);
      const ksuNo = d.ksu?.no || d.ksuNo;
      toast({ variant: "success", title: "Поступление оформлено", message: (ksuNo ? "КСУ " + ksuNo : "") + (d.mfn != null ? " · каталог MFN " + d.mfn : "") });
      setRcvKsuNo(""); setRcvCopies(""); setRcvUnit(""); setRcvInv(""); setRcvAct("");
      // обновляем строку заказа: предпочитаем order из ответа, иначе доуточняем GET'ом
      if (d.order && d.order.id != null) upsertOrder(d.order);
      else await refreshOrder(selected.id);
    } else if (r.status === 404 || r.status === 501) {
      toast({ variant: "info", title: "Поступление недоступно", message: "Модуль комплектования ещё не подключён." });
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант acq.receipt (роль администратора)." });
    } else {
      toast({ variant: "error", title: "Не оформлено", message: r.json?.error?.message || "Проверьте данные поступления." });
    }
  }

  async function lookupKsu() {
    const no = ksuQuery.trim();
    if (!no) return;
    const r = await api.acqKsu(no);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      // бэкенд отдаёт строку КСУ прямо в data (get_ksu); терпим и {entry}/{items}.
      const raw = (r.json.data as any).entry || ((r.json.data as any).items && (r.json.data as any).items[0]) || r.json.data;
      const e = normKsu(raw);
      setKsuResult(e || "none");
    } else if (r.status === 404) {
      // 404 здесь — «запись КСУ не найдена» (own-store), это НЕ отсутствие модуля.
      setKsuResult("none");
    } else if (r.status === 501) {
      toast({ variant: "info", title: "КСУ недоступна", message: "Книга суммарного учёта подключается модулем комплектования." });
      setKsuResult("none");
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант acq.read (роль администратора)." });
      setKsuResult("none");
    } else { setKsuResult("none"); }
  }

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Комплектование</h2>
        <span className="stf__pill">Заказ → поступление → каталог</span>
        {orders.length > 0 && <span className="stf__pill" style={{ background: "var(--status-issued-bg)", color: "var(--status-issued)", borderColor: "transparent" }}>{orders.filter((o) => !o.canceled && o.status !== "canceled").length} заказ(ов)</span>}
      </div>
    </div>
  );

  // /api/acq/* отсутствует → информер, экран не падает.
  if (unavailable) return (
    <div className="acq">
      {head}
      <div className="acq__card" style={{ padding: 4 }}>
        <EmptyState icon="archive" title="Комплектование подключается отдельным модулем"
          description="Рабочий стол комплектатора (заказ → поступление → КСУ → каталог) свёрстан в Стиле A и работает поверх движка комплектования (#184). На текущем сервере эндпойнты /api/acq/* ещё не развёрнуты — данные появятся после их публикации." />
      </div>
    </div>
  );

  return (
    <div className="acq">
      {head}
      <div className="acq__grid">
        {/* ===== Левая колонка: создание заказа + поиск КСУ ===== */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="acq__card acq__card-pad">
            <span className="acq__cap">Новый заказ</span>
            <div className="acq__fld">
              <label className="acq__fld-lab" htmlFor="acq-title">Заглавие</label>
              <input id="acq-title" className="acq__in" value={title} onChange={(e) => setTitle(e.target.value)}
                placeholder="Издание для заказа" autoComplete="off"
                onKeyDown={(e) => { if (e.key === "Enter") createOrder(); }} />
            </div>
            <div className="acq__fld">
              <label className="acq__fld-lab" htmlFor="acq-author">Автор</label>
              <input id="acq-author" className="acq__in" value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="необязательно" autoComplete="off" />
            </div>
            <div className="acq__fld">
              <label className="acq__fld-lab" htmlFor="acq-supplier">Поставщик</label>
              <input id="acq-supplier" className="acq__in" value={supplier} onChange={(e) => setSupplier(e.target.value)} placeholder="издательство / поставщик" autoComplete="off" />
            </div>
            <div className="acq__row2">
              <div className="acq__fld">
                <label className="acq__fld-lab" htmlFor="acq-copies">Экземпляров</label>
                <input id="acq-copies" className="acq__in acq__in--mono" type="number" min={1} value={copies} onChange={(e) => setCopies(e.target.value)} />
              </div>
              <div className="acq__fld">
                <label className="acq__fld-lab" htmlFor="acq-price">Цена за экз.</label>
                <input id="acq-price" className="acq__in acq__in--mono" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="₽" autoComplete="off" inputMode="decimal" />
              </div>
            </div>
            <div className="acq__fld">
              <label className="acq__fld-lab" htmlFor="acq-funding">Источник финансирования</label>
              <select id="acq-funding" className="acq__sel" value={funding} onChange={(e) => setFunding(e.target.value)}>
                {FUNDING.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <Button block iconLeft="plus" loading={creating} onClick={createOrder}>Создать заказ</Button>
          </div>

          {/* поиск КСУ */}
          <div className="acq__card acq__card-pad">
            <span className="acq__cap">Поиск в КСУ</span>
            <div className="acq__lookup">
              <input className="acq__in acq__in--mono" value={ksuQuery} onChange={(e) => setKsuQuery(e.target.value)}
                placeholder="№ записи КСУ" aria-label="Номер записи КСУ" autoComplete="off"
                onKeyDown={(e) => { if (e.key === "Enter") lookupKsu(); }} />
              <Button variant="secondary" iconLeft="search" onClick={lookupKsu}>Найти</Button>
            </div>
            {ksuResult === "none" ? (
              <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--text-subtle)" }}>Запись КСУ не найдена.</div>
            ) : ksuResult ? (
              <div className="acq__ksu">
                <span className="acq__ksu-k">№ КСУ</span><span className="acq__ksu-v">{ksuResult.no}</span>
                {ksuResult.date && (<><span className="acq__ksu-k">Дата</span><span className="acq__ksu-v">{ksuResult.date}</span></>)}
                {ksuResult.copies != null && (<><span className="acq__ksu-k">Экземпляров</span><span className="acq__ksu-v">{ksuResult.copies}</span></>)}
                {ksuResult.sum != null && (<><span className="acq__ksu-k">Сумма</span><span className="acq__ksu-v">{money(ksuResult.sum)}</span></>)}
                {ksuResult.actRef && (<><span className="acq__ksu-k">Акт/счёт</span><span className="acq__ksu-v">{ksuResult.actRef}</span></>)}
                {ksuResult.supplier && (<><span className="acq__ksu-k">Поставщик</span><span className="acq__ksu-v">{ksuResult.supplier}</span></>)}
              </div>
            ) : null}
          </div>
        </div>

        {/* ===== Правая колонка: список заказов + поступление ===== */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="acq__card">
            <div className="acq__card-pad" style={{ paddingBottom: 0 }}>
              <span className="acq__cap" style={{ marginBottom: 0 }}>Заказы</span>
            </div>
            {orders.length === 0 ? (
              <div style={{ padding: "8px 4px" }}>
                <EmptyState icon="archive" title="Заказов пока нет" description="Оформите заказ слева — он появится здесь. По заказу можно оформить поступление: создастся запись КСУ и каталожная запись." />
              </div>
            ) : (
              <div className="acq__orders">
                {orders.map((o) => {
                  const st = statusOf(o);
                  return (
                    <button key={o.id} type="button" className={"acq__order" + (o.id === selId ? " acq__order--on" : "")} onClick={() => { setSelId(o.id); setLastReceive(null); }}>
                      <div style={{ minWidth: 0 }}>
                        <div className="acq__order-title">{o.title}{o.author ? <span style={{ fontWeight: 400, color: "var(--text-subtle)" }}> · {o.author}</span> : null}</div>
                        <div className="acq__order-meta">
                          {o.supplier && <span>{o.supplier}</span>}
                          <span>{o.copies} экз.</span>
                          {o.price != null && <span>{money(o.price)}/экз.</span>}
                          {o.funding_source && <span>{o.funding_source}</span>}
                        </div>
                      </div>
                      <div className="acq__order-r">
                        <span className={"acq__st acq__st--" + st.cls}>{st.label}</span>
                        {!o.canceled && o.status !== "canceled" && (o.received || 0) < o.copies && (
                          <Button variant="ghost" size="sm" iconLeft="x" loading={busyId === o.id} onClick={(e) => { e.stopPropagation(); cancelOrder(o); }}>Отменить</Button>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* поступление по выбранному заказу */}
          {selected && !selected.canceled && selected.status !== "canceled" && (
            <div className="acq__card acq__card-pad">
              <span className="acq__cap">Поступление по заказу · {selected.title}</span>

              <div className="acq__flow" aria-label="Стадии комплектования">
                <span className="acq__flow-step acq__flow-step--done"><Icon name="check" size={13} />Заказ</span>
                <Icon name="chevron-right" size={13} style={{ color: "var(--text-subtle)" }} />
                <span className={"acq__flow-step" + ((selected.received || 0) > 0 ? " acq__flow-step--done" : " acq__flow-step--active")}>
                  {(selected.received || 0) > 0 ? <Icon name="check" size={13} /> : null}Поступление · КСУ
                </span>
                <Icon name="chevron-right" size={13} style={{ color: "var(--text-subtle)" }} />
                <span className={"acq__flow-step" + (lastReceive?.mfn ? " acq__flow-step--done" : "")}>
                  {lastReceive?.mfn ? <Icon name="check" size={13} /> : null}Каталог
                </span>
              </div>

              <div className="acq__row2">
                <div className="acq__fld">
                  <label className="acq__fld-lab" htmlFor="acq-rcv-copies">Поступило экз.</label>
                  <input id="acq-rcv-copies" className="acq__in acq__in--mono" type="number" min={1} value={rcvCopies}
                    onChange={(e) => setRcvCopies(e.target.value)} placeholder={String(selected.copies)} />
                </div>
                <div className="acq__fld">
                  <label className="acq__fld-lab" htmlFor="acq-rcv-ksu">№ КСУ (обязательно)</label>
                  <input id="acq-rcv-ksu" className="acq__in acq__in--mono" value={rcvKsuNo} onChange={(e) => setRcvKsuNo(e.target.value)} placeholder={ksuSuggest} autoComplete="off"
                    onKeyDown={(e) => { if (e.key === "Enter") receive(); }} />
                </div>
              </div>
              <div className="acq__row2">
                <div className="acq__fld">
                  <label className="acq__fld-lab" htmlFor="acq-rcv-unit">Цена за экз.</label>
                  <input id="acq-rcv-unit" className="acq__in acq__in--mono" value={rcvUnit} onChange={(e) => setRcvUnit(e.target.value)} placeholder={selected.price != null ? String(selected.price) : "₽"} autoComplete="off" inputMode="decimal" />
                </div>
                <div className="acq__fld">
                  <label className="acq__fld-lab" htmlFor="acq-rcv-act">Акт / счёт</label>
                  <input id="acq-rcv-act" className="acq__in" value={rcvAct} onChange={(e) => setRcvAct(e.target.value)} placeholder="№ акта / счёта" autoComplete="off" />
                </div>
              </div>
              <div className="acq__fld">
                <label className="acq__fld-lab" htmlFor="acq-rcv-inv">Инв. номера (через пробел/запятую)</label>
                <input id="acq-rcv-inv" className="acq__in acq__in--mono" value={rcvInv} onChange={(e) => setRcvInv(e.target.value)} placeholder="1024 1025 1026…" autoComplete="off" />
              </div>
              <Button iconLeft="clipboard-check" loading={receiving} onClick={receive}>Оформить поступление</Button>

              {/* результат: КСУ + ToCat (MFN созданной/обновлённой записи) */}
              {lastReceive && (
                <div className="acq__cat">
                  <Icon name="check-circle" size={18} style={{ color: "var(--status-available,#3C7D3F)", flex: "none", marginTop: 1 }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>
                      Партия принята{(lastReceive.copies != null) ? " · " + lastReceive.copies + " экз." : ""}
                      {(lastReceive.ksu?.no || lastReceive.ksuNo) ? " · КСУ " + (lastReceive.ksu?.no || lastReceive.ksuNo) : ""}
                    </div>
                    {lastReceive.mfn != null ? (
                      <div style={{ marginTop: 4, fontSize: 12.5, color: "var(--text-body)" }}>
                        {lastReceive.created ? "Создана" : "Обновлена"} каталожная запись:{" "}
                        <span className="acq__cat-mfn">MFN {lastReceive.mfn}</span>
                        {lastReceive.db ? " · " + lastReceive.db : ""}
                      </div>
                    ) : (
                      <div style={{ marginTop: 4, fontSize: 12.5, color: "var(--text-subtle)" }}>ToCat: каталог не подключён на этом стенде — КСУ и инв. учёт записаны (ИРБИС не требуется).</div>
                    )}
                    {lastReceive.inventory && lastReceive.inventory.length > 0 && (
                      <div style={{ marginTop: 4, fontSize: 12, color: "var(--text-subtle)" }}>
                        Инв. №: <span style={{ fontFamily: "var(--font-mono)" }}>{lastReceive.inventory.join(", ")}</span>
                      </div>
                    )}
                    {lastReceive.lendable && lastReceive.lendable.length > 0 && (
                      <div style={{ marginTop: 4, fontSize: 12, color: "var(--status-available,#3C7D3F)" }}>
                        Доступно к выдаче сразу: {lastReceive.lendable.length} экз.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
