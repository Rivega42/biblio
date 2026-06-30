// Платформа (#207/#209; epic #223) — административный стол управления контуром
// SaaS. Read-heavy, две вкладки:
//   • Арендаторы — таблица (слаг / наименование / тариф / создан) + форма
//     провизионирования нового арендатора (слаг, наименование, логин админа,
//     тариф) → POST /api/admin/tenant → обновление списка.
//   • Тариф и лимиты — для выбранного арендатора: текущий тариф + переключатель,
//     лимиты vs потребление (записи / читатели / хранилище — прогресс-бары) и
//     тумблеры включённости функциональных модулей.
// Бэкенд платформы публикуется отдельно, поэтому КАЖДАЯ вкладка деградирует
// независимо: нет эндпойнта (404/501) — информер в этой вкладке, остальное
// продолжает работать; приложение не падает.
import React from "react";
import { api } from "./api";
import type { Tenant, BillingInfo, PlanLimits } from "./api";
import type { TariffTable, TariffRow, TariffCell, MatrixCap, ResourceUsage } from "./api";
import type { DeploymentMode, DeploymentTopology, DeploymentResolved, ConnectionItem, ConnectionHint, WebhookSub, WebhookTarget, WebhookDelivery, JobItem, JobStats } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .irb-plat* — не пересекается с .stf__ / .adm__ / .cdesk__ /
// .acq__ / .bp__ / прочими .irb-*.
const CSS = `
.irb-plat{font-family:var(--font-ui);}
.irb-plat__tabs{display:flex;gap:4px;padding:4px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-bottom:16px;width:fit-content;flex-wrap:wrap;}
.irb-plat__tab{display:inline-flex;align-items:center;gap:7px;border:none;cursor:pointer;font-family:var(--font-ui);font-size:13px;font-weight:500;padding:7px 14px;border-radius:var(--radius-sm);background:transparent;color:var(--text-muted);}
.irb-plat__tab:hover{color:var(--text-body);}
.irb-plat__tab--on{background:var(--surface-card);color:var(--text-strong);font-weight:600;box-shadow:var(--shadow-sm);}
.irb-plat__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;}
.irb-plat__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.irb-plat__bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border-subtle);flex-wrap:wrap;}
.irb-plat__tbl{width:100%;border-collapse:collapse;font-size:13px;}
.irb-plat__tbl th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);padding:10px 14px;border-bottom:1px solid var(--border-subtle);background:var(--surface-sunken);white-space:nowrap;}
.irb-plat__tbl td{padding:10px 14px;border-bottom:1px solid var(--border-subtle);vertical-align:middle;}
.irb-plat__tbl tr:last-child td{border-bottom:none;}
.irb-plat__tbl tr:hover td{background:var(--surface-hover);}
.irb-plat__tbl tr[aria-selected="true"] td{background:var(--accent-weak);}
.irb-plat__mono{font-family:var(--font-mono);font-size:12px;}
.irb-plat__plan{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:var(--radius-full);background:var(--accent-weak);color:var(--accent-press);text-transform:capitalize;}
.irb-plat__form{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr)) auto;gap:10px;align-items:end;padding:14px;background:var(--surface-sunken);border-bottom:1px solid var(--border-subtle);}
.irb-plat__fld{display:flex;flex-direction:column;gap:5px;}
.irb-plat__fld-lab{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.irb-plat__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.irb-plat__in:focus{outline:none;border-color:var(--accent);}
.irb-plat__scroll{max-height:460px;overflow-y:auto;}
.irb-plat__pick{display:flex;flex-wrap:wrap;gap:6px;}
.irb-plat__pickbtn{font-size:11.5px;font-weight:600;padding:5px 13px;border-radius:var(--radius-full);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-muted);cursor:pointer;text-transform:capitalize;}
.irb-plat__pickbtn--on{background:var(--accent-weak);color:var(--accent-press);border-color:transparent;}
.irb-plat__pickbtn:disabled{opacity:.55;cursor:default;}
.irb-plat__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
.irb-plat__meter{display:flex;flex-direction:column;gap:7px;padding:14px;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface-card);}
.irb-plat__meter-top{display:flex;align-items:center;justify-content:space-between;gap:8px;}
.irb-plat__meter-name{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:600;color:var(--text-strong);}
.irb-plat__meter-val{font-family:var(--font-mono);font-size:12px;color:var(--text-muted);}
.irb-plat__track{height:8px;border-radius:var(--radius-full);background:var(--surface-hover);overflow:hidden;}
.irb-plat__fill{height:100%;border-radius:var(--radius-full);transition:width .3s ease;}
.irb-plat__meter-pct{font-size:11px;color:var(--text-subtle);}
.irb-plat__mods{display:flex;flex-direction:column;gap:2px;}
.irb-plat__mod{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 14px;border-bottom:1px solid var(--border-subtle);}
.irb-plat__mod:last-child{border-bottom:none;}
.irb-plat__mod-name{font-size:13px;font-weight:500;color:var(--text-body);}
.irb-plat__mod-code{font-family:var(--font-mono);font-size:11px;color:var(--text-subtle);}
.irb-plat__sw{position:relative;width:40px;height:22px;border-radius:var(--radius-full);border:none;cursor:pointer;background:var(--border-strong);transition:background-color .15s;flex:none;padding:0;}
.irb-plat__sw[aria-checked="true"]{background:var(--accent);}
.irb-plat__sw:disabled{opacity:.55;cursor:default;}
.irb-plat__sw i{position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:var(--radius-full);background:#fff;transition:left .15s;box-shadow:var(--shadow-sm);}
.irb-plat__sw[aria-checked="true"] i{left:21px;}
@media (max-width:760px){.irb-plat__form{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-plat-css")) {
  const s = document.createElement("style"); s.id = "irb-plat-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Тарифные планы контура (MVP). Совпадают с backend billing.PLANS
// (access/billing.py). Реальный список тарифов берём из каталога `plans` на
// ответе биллинга; эти значения — запасной справочник для формы создания.
const PLANS = ["free", "standard", "pro"] as const;
// Человекочитаемые подписи функциональных модулей. Коды — backend
// entitlements.DEFAULT_MODULES; неизвестный код показываем как есть.
const MODULE_RU: Record<string, string> = {
  opac: "Читательский портал / поиск",
  cataloging: "Каталогизация",
  circulation: "Книговыдача",
  acquisition: "Комплектование",
  bookprovision: "Книгообеспеченность",
  reader: "Читательский кабинет",
  admin: "Администрирование",
  analytics: "Аналитика и отчёты",
};
const moduleLabel = (code: string) => MODULE_RU[code] || code;
// Режимы продукта (узел 3): именованные пресеты модулей. Совпадают с backend
// entitlements.MODE_PRESETS. webportal — portal-only (first-class). 'custom' —
// нестандартный набор, собранный вручную через тумблеры модулей.
const MODE_LIST = ["demo", "webportal", "full"] as const;
const MODE_RU: Record<string, string> = {
  demo: "Демо", webportal: "Веб-портал", full: "Полная", custom: "Свой набор",
};
const modeLabel = (code?: string) => (code ? MODE_RU[code] || code : "—");
// Человекочитаемые подписи лимит-ресурсов (backend snake_case ключи).
const LIMIT_META: { key: keyof PlanLimits; name: string; icon: IconName; unit?: string }[] = [
  { key: "max_records", name: "Записи", icon: "file-text" },
  { key: "max_readers", name: "Читатели", icon: "users" },
  { key: "max_storage_mb", name: "Хранилище", icon: "archive", unit: " МБ" },
];

type Tab = "tenants" | "billing" | "matrix" | "deployment" | "connections" | "webhooks" | "jobs" | "onboard";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "tenants", label: "Арендаторы", icon: "layers" },
  { id: "billing", label: "Тариф и лимиты", icon: "credit-card" },
  { id: "matrix", label: "Матрица доступов", icon: "sliders" },
  { id: "deployment", label: "Развёртывание", icon: "settings" },
  { id: "connections", label: "Подключения", icon: "link" },
  { id: "webhooks", label: "Вебхуки", icon: "share" },
  { id: "jobs", label: "Задачи", icon: "clock" },
  { id: "onboard", label: "Онбординг", icon: "check" },
];

// Информер «эндпойнт вкладки не развёрнут».
function SectionDown({ icon, title }: { icon: IconName; title: string }) {
  return (
    <div className="irb-plat__card" style={{ padding: 4 }}>
      <EmptyState icon={icon} title={title}
        description="Раздел свёрстан в Стиле A и работает поверх движка платформы (#207/#209). На текущем сервере соответствующий эндпойнт /api/admin/* ещё не развёрнут — данные появятся после его публикации. Остальные разделы продолжают работать." />
    </div>
  );
}

export function PlatformDesk({ toast }: { toast: ToastFn }) {
  const [tab, setTab] = React.useState<Tab>("tenants");
  // Выбранный для вкладки «Тариф и лимиты» арендатор (слаг). Поднят сюда, чтобы
  // выбор строки в «Арендаторах» переносился во вкладку биллинга.
  const [selected, setSelected] = React.useState<string | null>(null);

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Платформа</h2>
        <span className="stf__pill">Арендаторы · тариф · лимиты · модули</span>
      </div>
    </div>
  );
  function openBilling(slug: string) { setSelected(slug); setTab("billing"); }

  return (
    <div className="irb-plat">
      {head}
      <div className="irb-plat__tabs" role="tablist" aria-label="Разделы платформы">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
            className={"irb-plat__tab" + (tab === t.id ? " irb-plat__tab--on" : "")} onClick={() => setTab(t.id)}>
            <Icon name={t.icon} size={15} />{t.label}
          </button>
        ))}
      </div>
      {tab === "tenants"
        ? <TenantsTab toast={toast} selected={selected} onSelect={setSelected} onManage={openBilling} />
        : tab === "billing"
          ? <BillingTab toast={toast} selected={selected} onSelect={setSelected} />
          : tab === "matrix"
            ? <MatrixTab toast={toast} />
            : tab === "deployment"
              ? <DeploymentTab toast={toast} selected={selected} />
              : tab === "connections"
                ? <ConnectionsTab toast={toast} selected={selected} />
                : tab === "webhooks"
                  ? <WebhooksTab toast={toast} selected={selected} />
                  : tab === "jobs"
                    ? <JobsTab toast={toast} />
                    : <OnboardWizard toast={toast} onGoConnections={() => setTab("connections")} onSelect={setSelected} />}
    </div>
  );
}

// ===== Арендаторы ===========================================================
function TenantsTab({ toast, selected, onSelect, onManage }: {
  toast: ToastFn; selected: string | null; onSelect: (slug: string) => void; onManage: (slug: string) => void;
}) {
  const [tenants, setTenants] = React.useState<Tenant[] | null>(null);
  const [down, setDown] = React.useState(false);

  // форма провизионирования
  const [showCreate, setShowCreate] = React.useState(false);
  const [slug, setSlug] = React.useState("");
  const [name, setName] = React.useState("");
  const [adminLogin, setAdminLogin] = React.useState("");
  const [plan, setPlan] = React.useState<string>("standard");
  const [creating, setCreating] = React.useState(false);

  async function load() {
    const r = await api.adminTenants();
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) setTenants(r.json.data.tenants || []);
    else setTenants([]);
  }
  React.useEffect(() => { void load(); }, []);

  async function createTenant() {
    const s = slug.trim(), n = name.trim(), al = adminLogin.trim();
    if (!s || !n || !al) { toast({ variant: "info", title: "Заполните арендатора", message: "Слаг, наименование и логин администратора обязательны." }); return; }
    setCreating(true);
    const r = await api.adminCreateTenant({ slug: s, name: n, adminLogin: al, plan });
    setCreating(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      const created: Tenant = { slug: r.json.data.slug || s, name: n, plan };
      setTenants((ts) => [created].concat((ts || []).filter((t) => t.slug !== created.slug)));
      onSelect(created.slug);
      toast({ variant: "success", title: "Арендатор создан", message: created.slug + " · тариф " + plan });
      setSlug(""); setName(""); setAdminLogin(""); setPlan("standard"); setShowCreate(false);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Создание недоступно", message: "Эндпойнт платформы не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db / admin.users." });
    else if (r.status === 409) toast({ variant: "error", title: "Слаг занят", message: "Арендатор с таким слагом уже существует." });
    else toast({ variant: "error", title: "Не создано", message: "Повторите попытку." });
  }

  if (down) return <SectionDown icon="layers" title="Управление арендаторами подключается отдельно" />;

  return (
    <div className="irb-plat__card">
      <div className="irb-plat__bar">
        <span className="irb-plat__cap">Арендаторы контура {tenants ? "· " + tenants.length : ""}</span>
        <Button size="sm" iconLeft={showCreate ? "x" : "plus"} variant={showCreate ? "ghost" : "primary"} onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Свернуть" : "Новый арендатор"}</Button>
      </div>

      {showCreate && (
        <div className="irb-plat__form">
          <div className="irb-plat__fld"><label className="irb-plat__fld-lab">Слаг</label><input className="irb-plat__in" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="napr. spbtl" autoComplete="off" /></div>
          <div className="irb-plat__fld"><label className="irb-plat__fld-lab">Наименование</label><input className="irb-plat__in" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" /></div>
          <div className="irb-plat__fld"><label className="irb-plat__fld-lab">Логин администратора</label><input className="irb-plat__in" value={adminLogin} onChange={(e) => setAdminLogin(e.target.value)} autoComplete="off" /></div>
          <div className="irb-plat__fld" style={{ gridColumn: "1 / -2" }}>
            <label className="irb-plat__fld-lab">Тариф</label>
            <div className="irb-plat__pick">
              {PLANS.map((p) => <button key={p} type="button" className={"irb-plat__pickbtn" + (plan === p ? " irb-plat__pickbtn--on" : "")} onClick={() => setPlan(p)}>{p}</button>)}
            </div>
          </div>
          <Button iconLeft="check" loading={creating} onClick={createTenant}>Создать</Button>
        </div>
      )}

      {tenants === null ? (
        <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка арендаторов…</div>
      ) : tenants.length === 0 ? (
        <div style={{ padding: 4 }}><EmptyState icon="layers" title="Арендаторов нет" description="Создайте первого арендатора контура — отдельное пространство с собственными базами, учётками и тарифом." /></div>
      ) : (
        <div className="irb-plat__scroll">
          <table className="irb-plat__tbl">
            <thead><tr><th>Слаг</th><th>Наименование</th><th>Тариф</th><th>Тип</th><th style={{ textAlign: "right" }}>Действия</th></tr></thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.slug} aria-selected={selected === t.slug}>
                  <td className="irb-plat__mono">{t.slug}</td>
                  <td>{t.name || "—"}</td>
                  <td><span className="irb-plat__plan">{t.plan || "—"}</span></td>
                  <td className="irb-plat__mono" style={{ whiteSpace: "nowrap" }}>{t.kind || "—"}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <Button size="sm" variant="ghost" iconLeft="credit-card" onClick={() => onManage(t.slug)}>Тариф и лимиты</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ===== Тариф и лимиты =======================================================
function BillingTab({ toast, selected, onSelect }: {
  toast: ToastFn; selected: string | null; onSelect: (slug: string) => void;
}) {
  const [tenants, setTenants] = React.useState<Tenant[] | null>(null);
  const [tenantsDown, setTenantsDown] = React.useState(false);
  const [billing, setBilling] = React.useState<BillingInfo | null>(null);
  const [billingDown, setBillingDown] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [busyPlan, setBusyPlan] = React.useState<string | null>(null);
  const [busyModule, setBusyModule] = React.useState<string | null>(null);
  const [busyMode, setBusyMode] = React.useState<string | null>(null);

  // справочник арендаторов для выпадающего выбора
  React.useEffect(() => { (async () => {
    const r = await api.adminTenants();
    if (r.status === 404 || r.status === 501) { setTenantsDown(true); return; }
    if (r.json?.ok && r.json.data) {
      const list = r.json.data.tenants || [];
      setTenants(list);
      if (!selected && list.length) onSelect(list[0].slug);
    } else setTenants([]);
  })(); }, []);

  async function loadBilling(slug: string) {
    setLoading(true); setBillingDown(false);
    const r = await api.adminBilling(slug);
    setLoading(false);
    if (r.status === 404 || r.status === 501) { setBillingDown(true); setBilling(null); return; }
    if (r.json?.ok && r.json.data) setBilling(r.json.data);
    else { setBilling(null); toast({ variant: "info", title: "Тариф недоступен", message: "Не удалось получить тариф арендатора " + slug + "." }); }
  }
  React.useEffect(() => { if (selected) void loadBilling(selected); else setBilling(null); }, [selected]);

  async function changePlan(plan: string) {
    if (!selected || !billing || plan === billing.plan) return;
    setBusyPlan(plan);
    const r = await api.adminSetPlan(selected, plan);
    setBusyPlan(null);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      // Ответ /plan несёт {plan,modules,limits,applied}, но НЕ usage/plans.
      // Оптимистично обновляем то, что пришло, и перечитываем биллинг целиком,
      // чтобы освежить потребление и каталог тарифов.
      const d = r.json.data;
      setBilling({ ...billing, plan: d.plan, modules: d.modules, limits: d.limits });
      setTenants((ts) => (ts || []).map((t) => t.slug === selected ? { ...t, plan: d.plan } : t));
      toast({ variant: "success", title: "Тариф изменён", message: selected + " → " + d.plan });
      void loadBilling(selected);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт платформы не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  async function changeMode(mode: string) {
    if (!selected || !billing || mode === billing.mode) return;
    setBusyMode(mode);
    const r = await api.adminSetMode(selected, mode);
    setBusyMode(null);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      // Ответ /mode несёт {mode,modules,applied}; обновляем оптимистично и
      // перечитываем биллинг (модули/потребление могли смениться).
      setBilling({ ...billing, mode: r.json.data.mode, modules: r.json.data.modules });
      toast({ variant: "success", title: "Режим переключён", message: selected + " → " + modeLabel(mode) });
      void loadBilling(selected);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт платформы не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  async function toggleModule(module: string, enabled: boolean) {
    if (!selected || !billing) return;
    setBusyModule(module);
    const r = await api.adminSetModule(selected, module, enabled);
    setBusyModule(null);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      // Ответ /module несёт обновлённый СПИСОК включённых модулей — берём его.
      setBilling({ ...billing, modules: r.json.data.modules });
      toast({ variant: "success", title: enabled ? "Модуль включён" : "Модуль отключён", message: moduleLabel(module) });
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт платформы не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  if (tenantsDown) return <SectionDown icon="credit-card" title="Тарифы и лимиты подключаются отдельно" />;

  const tenantPicker = (
    <div className="irb-plat__bar">
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span className="irb-plat__cap">Арендатор</span>
        <select className="irb-plat__in" style={{ width: "auto", minWidth: 200 }} value={selected || ""}
          onChange={(e) => onSelect(e.target.value)} aria-label="Выбор арендатора">
          {!selected && <option value="">— выберите —</option>}
          {(tenants || []).map((t) => <option key={t.slug} value={t.slug}>{t.name ? t.name + " (" + t.slug + ")" : t.slug}</option>)}
        </select>
      </div>
      <Button size="sm" variant="ghost" iconLeft="refresh-cw" loading={loading} disabled={!selected} onClick={() => selected && loadBilling(selected)}>Обновить</Button>
    </div>
  );

  let content: React.ReactNode;
  if (!selected) {
    content = <div style={{ padding: 4 }}><EmptyState icon="layers" title="Выберите арендатора" description="Выберите арендатора, чтобы увидеть его тариф, лимиты, потребление и состав функциональных модулей." /></div>;
  } else if (billingDown) {
    content = <div style={{ padding: 4 }}><EmptyState icon="credit-card" title="Тариф арендатора подключается отдельно" description="Раздел свёрстан в Стиле A и работает поверх движка платформы (#209). На текущем сервере /api/admin/billing ещё не развёрнут — данные появятся после публикации." /></div>;
  } else if (loading && !billing) {
    content = <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка тарифа…</div>;
  } else if (!billing) {
    content = <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Нет данных по тарифу.</div>;
  } else {
    // Выбор тарифа: имена из каталога `plans` (backend billing.PLANS), плюс
    // текущий план и запасной список, на случай если каталог не пришёл.
    const catalogPlans = (billing.plans || []).map((p) => p.plan);
    const planChoices = Array.from(new Set([...catalogPlans, ...PLANS, billing.plan])).filter(Boolean);
    // Полный набор модулей = объединение модулей всех тарифов каталога. Если
    // каталога нет — деградируем к текущему списку включённых модулей.
    const enabledSet = new Set(billing.modules || []);
    const allModules = Array.from(new Set([
      ...(billing.plans || []).flatMap((p) => p.modules),
      ...(billing.modules || []),
    ])).sort();
    const moduleCodes = allModules.length ? allModules : Array.from(enabledSet).sort();
    content = (
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 18 }}>
        {/* Режим продукта (узел 3): именованный пресет модулей. webportal =
            portal-only (first-class). Переключение применяет пресет на бэке. */}
        <div>
          <span className="irb-plat__cap">Режим</span>
          <div className="irb-plat__pick" style={{ marginTop: 9 }}>
            {MODE_LIST.map((mo) => (
              <button key={mo} type="button"
                className={"irb-plat__pickbtn" + (billing.mode === mo ? " irb-plat__pickbtn--on" : "")}
                disabled={busyMode !== null} onClick={() => changeMode(mo)}>{MODE_RU[mo]}</button>
            ))}
            {billing.mode === "custom" && (
              <span className="irb-plat__pickbtn irb-plat__pickbtn--on" style={{ pointerEvents: "none" }} title="Нестандартный набор модулей">Свой набор</span>
            )}
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-subtle)", marginTop: 6 }}>
            Демо / Веб-портал / Полная — пресет функциональных модулей ниже. «Веб-портал» = только читательский контур (без staff-АРМов).
          </div>
        </div>

        {/* Тариф + переключатель */}
        <div>
          <span className="irb-plat__cap">Тариф</span>
          <div className="irb-plat__pick" style={{ marginTop: 9 }}>
            {planChoices.map((p) => (
              <button key={p} type="button"
                className={"irb-plat__pickbtn" + (billing.plan === p ? " irb-plat__pickbtn--on" : "")}
                disabled={busyPlan !== null} onClick={() => changePlan(p)}>{p}</button>
            ))}
          </div>
        </div>

        {/* Лимиты vs потребление — лимит из snake_case карты limits, потребление
            из частичной карты usage (ресурс без значения → «—»). */}
        <div>
          <span className="irb-plat__cap">Лимиты и потребление</span>
          <div className="irb-plat__grid" style={{ marginTop: 9 }}>
            {LIMIT_META.map((m) => (
              <Meter key={m.key} icon={m.icon} name={m.name} unit={m.unit}
                limit={billing.limits ? billing.limits[m.key] : null}
                used={billing.usage ? billing.usage[m.key] : undefined} />
            ))}
          </div>
        </div>

        {/* Модули — переключатель ON ⇔ код в списке billing.modules. */}
        <div>
          <span className="irb-plat__cap">Функциональные модули</span>
          {moduleCodes.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--text-subtle)", marginTop: 9 }}>Тариф не задаёт модулей — состав определяется грантами учёток.</div>
          ) : (
            <div className="irb-plat__card irb-plat__mods" style={{ marginTop: 9 }}>
              {moduleCodes.map((code) => {
                const on = enabledSet.has(code);
                return (
                  <div className="irb-plat__mod" key={code}>
                    <div style={{ minWidth: 0 }}>
                      <div className="irb-plat__mod-name">{moduleLabel(code)}</div>
                      <div className="irb-plat__mod-code">{code}</div>
                    </div>
                    <button type="button" role="switch" aria-checked={on}
                      aria-label={(on ? "Отключить" : "Включить") + " модуль " + moduleLabel(code)}
                      className="irb-plat__sw" disabled={busyModule === code}
                      onClick={() => toggleModule(code, !on)}><i /></button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="irb-plat__card">
      {tenantPicker}
      {content}
    </div>
  );
}

// Прогресс-бар «использовано / лимит». Цвет: зелёный < 75% < жёлтый < 90% < красный.
//   limit: number — ceiling; null/UNLIMITED — без лимита («∞»);
//   used:  number — потребление; undefined — сервер не посчитал («—»).
function Meter({ icon, name, used, limit, unit = "" }: {
  icon: IconName; name: string; used?: number; limit: number | null; unit?: string;
}) {
  const hasUsed = typeof used === "number" && Number.isFinite(used);
  const u = hasUsed ? (used as number) : 0;
  // null или ≤0 → лимита нет (∞). Иначе — конечный потолок.
  const lim = typeof limit === "number" && Number.isFinite(limit) && limit > 0 ? limit : null;
  const ratio = lim && hasUsed ? u / lim : 0;
  const pct = Math.max(0, Math.min(100, Math.round(ratio * 100)));
  const color = ratio >= 0.9 ? "var(--danger-500)" : ratio >= 0.75 ? "var(--warning)" : "var(--status-available)";
  const fmt = (n: number) => Number.isFinite(n) ? n.toLocaleString("ru-RU") : "—";
  const usedLabel = hasUsed ? fmt(u) + unit : "—";
  const limitLabel = lim ? fmt(lim) + unit : "∞";
  // Подпись: без лимита → «без лимита»; нет данных потребления → «нет данных»;
  // иначе — процент использования.
  const note = !lim ? "без лимита" : !hasUsed ? "потребление неизвестно" : pct + "% использовано";
  return (
    <div className="irb-plat__meter">
      <div className="irb-plat__meter-top">
        <span className="irb-plat__meter-name"><Icon name={icon} size={15} />{name}</span>
        <span className="irb-plat__meter-val">{usedLabel} / {limitLabel}</span>
      </div>
      <div className="irb-plat__track"><div className="irb-plat__fill" style={{ width: (lim && hasUsed ? pct : 0) + "%", background: color }} /></div>
      <span className="irb-plat__meter-pct">{note}</span>
    </div>
  );
}

// ===== Матрица доступов (#331) ==============================================
// Главная тарифная control-поверхность ОПЕРАТОРА ПЛАТФОРМЫ (не per-tenant
// админки библиотеки): редактируемая таблица «разделы/функции × тарифы».
// Галочка — раздел/функция входит в тариф (функция наследует раздел, пока не
// переопределена явной ячейкой); число — лимит ресурса (пусто = безлимит);
// select — режим при превышении/недоступности (блок 402 / грейс). Изменение
// сразу пишется POST /api/admin/tariffs/cell. Гейт — super-admin (admin.db).
function matrixIncluded(cells: TariffTable["cells"], row: TariffRow, tname: string): boolean {
  const c = cells[tname]?.[row.item_key];
  if (c) return c.included;
  if (row.kind === "function" && row.section) {
    const sc = cells[tname]?.["section:" + row.section];
    return sc ? sc.included : false;
  }
  return row.kind === "resource";
}
function matrixEnf(cells: TariffTable["cells"], row: TariffRow, tname: string): "block" | "grace" {
  const c = cells[tname]?.[row.item_key];
  if (c) return c.enforcement;
  if (row.kind === "function" && row.section) {
    const sc = cells[tname]?.["section:" + row.section];
    if (sc) return sc.enforcement;
  }
  return "block";
}

// Полоса «Потребление vs лимит» для выбранного тенанта (#331). Показывает
// фактическое использование ресурсов против лимита тарифа; красная при превышении.
function UsageBars({ tenant }: { tenant: string }) {
  const [caps, setCaps] = React.useState<Record<string, MatrixCap> | null>(null);
  const [usage, setUsage] = React.useState<ResourceUsage>({});
  const [tariff, setTariff] = React.useState<string | null>(null);
  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.adminAccessMatrix(tenant);
      if (!alive) return;
      if (r.json?.ok && r.json.data?.matrix) { setCaps(r.json.data.matrix.caps); setUsage(r.json.data.usage || {}); setTariff(r.json.data.matrix.tariff); }
      else setCaps({});
    })();
    return () => { alive = false; };
  }, [tenant]);
  if (caps === null) return null;
  const keys = Object.keys(caps);
  return (
    <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)", display: "flex", flexWrap: "wrap", gap: 14 }}>
      <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-strong)", width: "100%" }}>
        Потребление · тенант «{tenant}»{tariff ? " · тариф " + tariff : " · тариф не назначен"}
      </span>
      {keys.map((k) => {
        const cap = caps[k]; const used = usage[k] ?? 0; const lim = cap.limit;
        const pct = lim && lim > 0 ? Math.min(100, Math.round((used / lim) * 100)) : 0;
        const over = lim != null && used > lim;
        const near = lim != null && !over && pct >= 80;
        const color = over ? "var(--danger,#c0392b)" : near ? "var(--warning,#b8860b)" : "var(--accent,#2d7d6e)";
        return (
          <div key={k} style={{ minWidth: 150, flex: "1 1 150px", maxWidth: 230 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, color: "var(--text-subtle)", marginBottom: 4 }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cap.title}</span>
              <span style={{ color: over ? color : "var(--text-muted)", fontWeight: over ? 700 : 500 }}>{used}{lim == null ? " / ∞" : " / " + lim}</span>
            </div>
            <div style={{ height: 6, borderRadius: 999, background: "var(--surface-sunken,#eceae3)", overflow: "hidden" }}>
              <div style={{ width: (lim == null ? 0 : pct) + "%", height: "100%", background: color, transition: "width .3s" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MatrixTab({ toast }: { toast: ToastFn }) {
  const [data, setData] = React.useState<TariffTable | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [newTitle, setNewTitle] = React.useState("");
  const [usageTenant, setUsageTenant] = React.useState("public");

  const load = React.useCallback(async () => {
    const r = await api.adminTariffs();
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    setDown(false);
    if (r.json?.ok && r.json.data) setData(r.json.data); else setData({ rows: [], tariffs: [], cells: {} });
  }, []);
  React.useEffect(() => { load(); }, [load]);

  const patch = async (tname: string, itemKey: string,
                       p: { included?: boolean; value?: number | null; enforcement?: "block" | "grace" }) => {
    setBusy(true);
    const r = await api.adminTariffCell(tname, itemKey, p);
    setBusy(false);
    const cell: TariffCell | undefined = r.json?.ok ? (r.json.data as any)?.cell : undefined;
    if (cell) setData((d) => d && ({ ...d, cells: { ...d.cells, [tname]: { ...(d.cells[tname] || {}), [itemKey]: cell } } }));
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db (оператор платформы)." });
    else toast({ variant: "error", title: "Не сохранено", message: "Ячейка тарифа не обновлена." });
  };
  const addTariff = async () => {
    const n = newName.trim(); if (!n) return;
    const r = await api.adminTariffCreate(n, newTitle.trim() || n, data ? data.tariffs.length : 0);
    if (r.json?.ok) { setNewName(""); setNewTitle(""); load(); toast({ variant: "success", title: "Тариф добавлен", message: n }); }
    else toast({ variant: "error", title: "Не добавлен", message: "Тариф с таким кодом уже есть." });
  };
  const delTariff = async (n: string) => {
    const r = await api.adminTariffDelete(n);
    if (r.json?.ok) { load(); toast({ variant: "success", title: "Тариф удалён", message: n }); }
  };

  if (down) return <SectionDown icon="sliders" title="Матрица доступов подключается отдельно" />;
  if (data === null) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка матрицы…</div>;

  return (
    <div className="irb-plat__card">
      <UsageBars key={usageTenant} tenant={usageTenant} />
      <div className="irb-plat__bar">
        <span style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 420 }}>
          Тарифная сетка платформы: разделы/функции × тарифы. Галочка — входит в тариф; число — лимит (вкл. число аккаунтов); режим — блок (402) / грейс при превышении.
        </span>
        <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
          <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Тенант (потребление)</span>
            <input className="irb-plat__in" placeholder="public" value={usageTenant} onChange={(e) => setUsageTenant(e.target.value || "public")} style={{ width: 110 }} aria-label="Тенант для счётчиков потребления" /></div>
          <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Код</span>
            <input className="irb-plat__in" placeholder="vuz" value={newName} onChange={(e) => setNewName(e.target.value)} style={{ width: 100 }} aria-label="Код нового тарифа" /></div>
          <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Название</span>
            <input className="irb-plat__in" placeholder="ВУЗ" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} style={{ width: 130 }} aria-label="Название нового тарифа" /></div>
          <Button variant="secondary" size="sm" onClick={addTariff} disabled={busy || !newName.trim()}>
            <Icon name="plus" size={14} /> Тариф
          </Button>
        </div>
      </div>
      <div className="irb-plat__scroll">
        <table className="irb-plat__tbl">
          <thead>
            <tr>
              <th>Раздел / функция / ресурс</th>
              {data.tariffs.map((t) => (
                <th key={t.name} style={{ textAlign: "center" }}>
                  {t.title}{" "}
                  <button type="button" onClick={() => delTariff(t.name)} title={"Удалить тариф " + t.name}
                    aria-label={"Удалить тариф " + t.name}
                    style={{ border: "none", background: "none", cursor: "pointer", color: "var(--text-subtle)", padding: 2 }}>
                    <Icon name="trash" size={12} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.item_key}>
                <td style={{ paddingLeft: row.kind === "function" ? 28 : 14 }} className={row.kind === "resource" ? "irb-plat__mono" : ""}>
                  {row.kind === "section" ? <b>{row.title}</b> : row.title}
                  {row.kind === "resource" && row.unit ? <span style={{ color: "var(--text-subtle)" }}> ({row.unit})</span> : null}
                </td>
                {data.tariffs.map((t) => (
                  <td key={t.name} style={{ textAlign: "center", whiteSpace: "nowrap" }}>
                    {row.kind === "resource"
                      ? <input type="number" min={0} placeholder="∞" className="irb-plat__in"
                          value={data.cells[t.name]?.[row.item_key]?.value ?? ""}
                          onChange={(e) => patch(t.name, row.item_key, { value: e.target.value === "" ? null : parseInt(e.target.value, 10) })}
                          style={{ width: 66, padding: "5px 7px" }} aria-label={row.title + " — лимит в тарифе " + t.name} />
                      : <input type="checkbox" checked={matrixIncluded(data.cells, row, t.name)}
                          onChange={(e) => patch(t.name, row.item_key, { included: e.target.checked })}
                          aria-label={row.title + " в тарифе " + t.name} />}
                    {" "}
                    <select value={matrixEnf(data.cells, row, t.name)}
                      onChange={(e) => patch(t.name, row.item_key, { enforcement: e.target.value as "block" | "grace" })}
                      style={{ fontSize: 11 }} title="Поведение при превышении/недоступности"
                      aria-label={"Режим: " + row.title + " / " + t.name}>
                      <option value="block">блок</option>
                      <option value="grace">грейс</option>
                    </select>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ===== Развёртывание (#335) =================================================
// Оператор платформы выбирает режим (что Biblio заменяет) и топологию (cloud/
// onprem) для выбранного арендатора. Гейт — super-admin (admin.db).
function DeploymentTab({ toast, selected }: { toast: ToastFn; selected: string | null }) {
  const [catalog, setCatalog] = React.useState<{ modes: DeploymentMode[]; topologies: DeploymentTopology[] } | null>(null);
  const [dep, setDep] = React.useState<DeploymentResolved | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => { (async () => {
    const r = await api.adminDeploymentCatalog();
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    if (r.json?.ok && r.json.data) setCatalog(r.json.data);
  })(); }, []);
  React.useEffect(() => { (async () => {
    if (!selected) { setDep(null); return; }
    const r = await api.adminDeployment(selected);
    if (r.json?.ok && r.json.data?.deployment) setDep(r.json.data.deployment);
  })(); }, [selected]);

  const apply = async (mode: string, topology: string) => {
    if (!selected) return;
    setBusy(true);
    const r = await api.adminDeploymentSet({ tenant: selected, mode, topology });
    setBusy(false);
    if (r.json?.ok && r.json.data?.resolved) { setDep(r.json.data.resolved); toast({ variant: "success", title: "Режим сохранён", message: r.json.data.resolved.mode }); }
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db (оператор платформы)." });
    else toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку." });
  };

  if (down) return <SectionDown icon="settings" title="Развёртывание подключается отдельно" />;
  if (!selected) return <SectionDown icon="settings" title="Выберите арендатора на вкладке «Арендаторы»" />;
  if (!catalog || !dep) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка…</div>;

  return (
    <div className="irb-plat__card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <p className="irb-plat__cap" style={{ marginBottom: 8 }}>Режим — что Biblio заменяет</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {catalog.modes.map((m) => (
            <button key={m.key} type="button" onClick={() => apply(m.key, dep.topology)} disabled={busy}
              style={{ textAlign: "left", padding: "11px 13px", borderRadius: "var(--radius-md)", cursor: "pointer",
                border: "1px solid " + (dep.mode === m.key ? "var(--accent)" : "var(--border-subtle)"),
                background: dep.mode === m.key ? "var(--accent-weak)" : "var(--surface-card)" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{m.title}</div>
              <div style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 2 }}>{m.description}</div>
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="irb-plat__cap" style={{ marginBottom: 8 }}>Где работает</p>
        <div className="irb-plat__pick">
          {catalog.topologies.map((t) => (
            <button key={t.key} type="button" disabled={busy}
              className={"irb-plat__pickbtn" + (dep.topology === t.key ? " irb-plat__pickbtn--on" : "")}
              onClick={() => apply(dep.mode, t.key)}>{t.title}</button>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", fontSize: 12, color: "var(--text-muted)", borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
        <span>Нужные подключения: <b style={{ color: "var(--text-body)" }}>{dep.required_connections.join(", ") || "—"}</b></span>
        <span>Модулей по режиму: <b style={{ color: "var(--text-body)" }}>{dep.default_modules.length}</b></span>
      </div>
    </div>
  );
}

// ===== Подключения (#335) ===================================================
// Внешние подключения арендатора (ИРБИС/jirbis/инфорост). Секреты маскированы;
// пустой/маска-секрет при сохранении не затирает прежний. Гейт super-admin.
function ConnectionsTab({ toast, selected }: { toast: ToastFn; selected: string | null }) {
  const [data, setData] = React.useState<{ items: ConnectionItem[]; kinds: string[]; hints: Record<string, ConnectionHint[]> } | null>(null);
  const [down, setDown] = React.useState(false);
  const [draft, setDraft] = React.useState<Record<string, Record<string, string>>>({});
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    if (!selected) { setData(null); return; }
    const r = await api.adminConnections(selected);
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    setDown(false);
    if (r.json?.ok && r.json.data) {
      setData(r.json.data);
      const d: Record<string, Record<string, string>> = {};
      for (const it of r.json.data.items) d[it.kind] = Object.fromEntries(Object.entries(it.config).map(([k, v]) => [k, String(v ?? "")]));
      setDraft(d);
    }
  }, [selected]);
  React.useEffect(() => { load(); }, [load]);

  const setVal = (kind: string, key: string, v: string) =>
    setDraft((d) => ({ ...d, [kind]: { ...(d[kind] || {}), [key]: v } }));

  const save = async (kind: string) => {
    if (!selected) return;
    setBusy(true);
    const r = await api.adminConnectionSet({ tenant: selected, kind, config: draft[kind] || {} });
    setBusy(false);
    if (r.json?.ok) { toast({ variant: "success", title: "Подключение сохранено", message: kind }); load(); }
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не сохранено", message: "Проверьте поля." });
  };
  const remove = async (kind: string) => {
    if (!selected) return;
    const r = await api.adminConnectionRemove({ tenant: selected, kind });
    if (r.json?.ok) { toast({ variant: "success", title: "Удалено", message: kind }); load(); }
  };

  if (down) return <SectionDown icon="link" title="Подключения подключаются отдельно" />;
  if (!selected) return <SectionDown icon="link" title="Выберите арендатора на вкладке «Арендаторы»" />;
  if (!data) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка…</div>;

  const KIND_RU: Record<string, string> = { irbis: "ИРБИС (каталог/выдача)", jirbis: "jirbis (Joomla — cutover)", inforost: "Инфорост (оцифровка)" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {data.kinds.map((kind) => {
        const hints = data.hints[kind] || [];
        const exists = data.items.some((i) => i.kind === kind);
        return (
          <div key={kind} className="irb-plat__card" style={{ padding: 14 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10, gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{KIND_RU[kind] || kind}</span>
              <div style={{ display: "flex", gap: 8 }}>
                {exists && <Button size="sm" variant="ghost" iconLeft="trash" onClick={() => remove(kind)}>Удалить</Button>}
                <Button size="sm" iconLeft="check" loading={busy} onClick={() => save(kind)}>Сохранить</Button>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 10 }}>
              {hints.map((h) => (
                <label key={h.key} className="irb-plat__fld">
                  <span className="irb-plat__fld-lab">{h.label}{h.secret ? " (секрет)" : ""}</span>
                  <input className="irb-plat__in" type={h.secret ? "password" : "text"}
                    value={(draft[kind]?.[h.key]) ?? ""} onChange={(e) => setVal(kind, h.key, e.target.value)}
                    placeholder={h.secret ? "не меняется" : ""} aria-label={h.label} />
                </label>
              ))}
            </div>
          </div>
        );
      })}
      <p style={{ fontSize: 12, color: "var(--text-subtle)", margin: 0 }}>Секреты хранятся off-git; наружу — маскированными. Пустой/маска секрет при сохранении не затирает прежний.</p>
    </div>
  );
}

// ===== Исходящие вебхуки (#356) =============================================
// Оператор платформы (admin.db) управляет подписками тенанта на события:
// добавить (событие/url/секрет), вкл/выкл, удалить, превью отправляемого payload
// с HMAC-подписью. Секрет наружу маскируется (***).
const WH_EVENT_RU: Record<string, string> = {
  "record.created": "Создана запись", "loan.issued": "Выдача",
  "hold.placed": "Бронь", "import.completed": "Импорт завершён",
};
function WebhooksTab({ toast, selected }: { toast: ToastFn; selected: string | null }) {
  const [data, setData] = React.useState<{ items: WebhookSub[]; events: string[] } | null>(null);
  const [down, setDown] = React.useState(false);
  const [event, setEvent] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [secret, setSecret] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [preview, setPreview] = React.useState<Record<number, WebhookTarget | "empty">>({});
  const [deliveries, setDeliveries] = React.useState<Record<number, WebhookDelivery[]>>({});

  const load = React.useCallback(async () => {
    if (!selected) { setData(null); return; }
    const r = await api.adminWebhooks(selected);
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    setDown(false);
    if (r.json?.ok && r.json.data) { setData(r.json.data); if (!event && r.json.data.events[0]) setEvent(r.json.data.events[0]); }
  }, [selected, event]);
  React.useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!selected) return;
    const u = url.trim();
    if (!event || !u) { toast({ variant: "info", title: "Заполните поля", message: "Событие и URL обязательны." }); return; }
    setBusy(true);
    const r = await api.adminWebhookSubscribe({ tenant: selected, event, url: u, secret: secret.trim() });
    setBusy(false);
    if (r.json?.ok) { setUrl(""); setSecret(""); toast({ variant: "success", title: "Подписка добавлена", message: WH_EVENT_RU[event] || event }); load(); }
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else if (r.status === 400) toast({ variant: "error", title: "Не добавлено", message: "Проверьте событие и URL." });
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  };
  const toggle = async (s: WebhookSub) => {
    const r = await api.adminWebhookSetActive({ id: s.id, active: !(s.active === true || s.active === 1) });
    if (r.json?.ok) load();
  };
  const remove = async (id: number) => {
    const r = await api.adminWebhookRemove({ id });
    if (r.json?.ok) { toast({ variant: "success", title: "Подписка удалена" }); load(); }
  };
  const doPreview = async (s: WebhookSub) => {
    if (!selected) return;
    const r = await api.adminWebhookPreview({ tenant: selected, event: s.event, data: { example: true } });
    const t = r.json?.ok && r.json.data ? r.json.data.targets.find((x) => x.subscription_id === s.id) : undefined;
    setPreview((p) => ({ ...p, [s.id]: t || "empty" }));
  };
  const doDeliveries = async (s: WebhookSub) => {
    if (deliveries[s.id]) { setDeliveries((d) => { const n = { ...d }; delete n[s.id]; return n; }); return; }
    const r = await api.adminWebhookDeliveries(s.id);
    setDeliveries((d) => ({ ...d, [s.id]: (r.json?.ok && r.json.data ? r.json.data.items : []) }));
  };

  if (down) return <SectionDown icon="share" title="Вебхуки подключаются отдельно" />;
  if (!selected) return <SectionDown icon="share" title="Выберите арендатора на вкладке «Арендаторы»" />;
  if (!data) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="irb-plat__card" style={{ padding: 14 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)", marginBottom: 10 }}>Новая подписка</div>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(150px,1fr) minmax(200px,2fr) minmax(120px,1fr) auto", gap: 10, alignItems: "end" }}>
          <label className="irb-plat__fld">
            <span className="irb-plat__fld-lab">Событие</span>
            <select className="irb-plat__in" value={event} onChange={(e) => setEvent(e.target.value)} aria-label="Событие">
              {data.events.map((ev) => <option key={ev} value={ev}>{WH_EVENT_RU[ev] || ev}</option>)}
            </select>
          </label>
          <label className="irb-plat__fld">
            <span className="irb-plat__fld-lab">URL приёмника</span>
            <input className="irb-plat__in" type="text" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" aria-label="URL приёмника" />
          </label>
          <label className="irb-plat__fld">
            <span className="irb-plat__fld-lab">Секрет (HMAC)</span>
            <input className="irb-plat__in" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="опц." aria-label="Секрет HMAC" />
          </label>
          <Button size="sm" iconLeft="plus" loading={busy} onClick={add}>Добавить</Button>
        </div>
      </div>

      {data.items.length === 0
        ? <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Подписок пока нет. Добавьте первую выше.</div>
        : data.items.map((s) => {
          const on = s.active === true || s.active === 1;
          const pv = preview[s.id];
          return (
            <div key={s.id} className="irb-plat__card" style={{ padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, fontWeight: 600, padding: "3px 9px", borderRadius: 999, background: "var(--surface-sunken,#f1efe9)", color: "var(--text-subtle)" }}>{WH_EVENT_RU[s.event] || s.event}</span>
                <span style={{ flex: 1, minWidth: 0, fontSize: 13, color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.url}</span>
                <span style={{ fontSize: 12, color: on ? "var(--text-strong)" : "var(--text-subtle)" }}>{on ? "активна" : "выключена"}</span>
                <Button size="sm" variant="ghost" iconLeft="eye" onClick={() => doPreview(s)}>Превью</Button>
                <Button size="sm" variant="ghost" iconLeft="clock" onClick={() => doDeliveries(s)}>Журнал</Button>
                <Button size="sm" variant="ghost" iconLeft={on ? "x-circle" : "check-circle"} onClick={() => toggle(s)}>{on ? "Выключить" : "Включить"}</Button>
                <Button size="sm" variant="ghost" iconLeft="trash" onClick={() => remove(s.id)}>Удалить</Button>
              </div>
              {pv && (pv === "empty"
                ? <p style={{ fontSize: 12, color: "var(--text-subtle)", margin: "10px 0 0" }}>Превью пусто (подписка неактивна или событие не совпало).</p>
                : <pre style={{ margin: "10px 0 0", padding: 10, background: "var(--surface-sunken,#f5f3ee)", borderRadius: 8, fontSize: 11.5, overflow: "auto", maxHeight: 160 }}>{"подпись HMAC: " + pv.signature.slice(0, 24) + "…\n" + JSON.stringify(pv.payload, null, 2)}</pre>)}
              {deliveries[s.id] && (deliveries[s.id].length === 0
                ? <p style={{ fontSize: 12, color: "var(--text-subtle)", margin: "10px 0 0" }}>Журнал доставки пуст — событий по этой подписке ещё не было.</p>
                : <div style={{ margin: "10px 0 0", overflow: "hidden", border: "1px solid var(--border-subtle)", borderRadius: 8 }}>
                    {deliveries[s.id].map((d, i) => (
                      <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 11px", fontSize: 12, borderTop: i ? "1px solid var(--border-subtle)" : "none" }}>
                        <span style={{ fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 999, background: d.status === "prepared" ? "var(--status-issued-bg,#FBEFD8)" : d.status === "ok" ? "var(--status-available-bg,#E3F0E4)" : "var(--surface-sunken)", color: "var(--text-muted)" }}>{d.status}</span>
                        <span style={{ flex: 1, minWidth: 0, color: "var(--text-strong)" }}>{WH_EVENT_RU[d.event] || d.event}</span>
                        <span style={{ color: "var(--text-subtle)" }}>попыток: {d.attempts}</span>
                      </div>
                    ))}
                  </div>)}
            </div>
          );
        })}
      <p style={{ fontSize: 12, color: "var(--text-subtle)", margin: 0 }}>Секрет хранится off-git, наружу маскируется (***). Тело подписывается HMAC-SHA256; реальная отправка — на стороне коннектора.</p>
    </div>
  );
}

// ===== Фоновые задачи (#240) ================================================
// Оператор платформы (admin.db) видит очередь фоновых задач (OCR, тайлы, реиндекс):
// сводка по статусам + последние задачи + ручной прогон OCR-конвейера.
const JOB_STATUS_RU: Record<string, string> = { pending: "в очереди", running: "выполняется", done: "готово", failed: "ошибка" };
function JobsTab({ toast }: { toast: ToastFn }) {
  const [data, setData] = React.useState<{ items: JobItem[]; stats: JobStats } | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    const r = await api.adminJobs();
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    setDown(false);
    if (r.json?.ok && r.json.data) setData(r.json.data); else setData({ items: [], stats: { total: 0, by_status: {} } });
  }, []);
  React.useEffect(() => { load(); }, [load]);

  const processOcr = async () => {
    setBusy(true);
    const r = await api.adminOcrProcess();
    setBusy(false);
    if (r.json?.ok) {
      const job = r.json.data?.job;
      if (job) toast({ variant: "success", title: "OCR-задача обработана", message: "проиндексировано: " + (r.json.data?.indexed ?? 0) });
      else toast({ variant: "info", title: "Очередь OCR пуста" });
      load();
    } else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не обработано", message: "Повторите попытку." });
  };

  if (down) return <SectionDown icon="clock" title="Очередь задач подключается отдельно" />;
  if (!data) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка очереди…</div>;

  const STATUS_COLOR: Record<string, string> = { pending: "var(--text-subtle)", running: "var(--accent,#2d7d6e)", done: "var(--text-muted)", failed: "var(--danger,#c0392b)" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="irb-plat__card" style={{ padding: 14, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>Всего задач: {data.stats.total}</span>
        {(["pending", "running", "done", "failed"] as const).map((s) => (
          <span key={s} style={{ fontSize: 12.5, color: STATUS_COLOR[s] }}>
            {JOB_STATUS_RU[s]}: <b>{data.stats.by_status[s] ?? 0}</b>
          </span>
        ))}
        <span style={{ flex: 1 }} />
        <Button size="sm" iconLeft="refresh-cw" variant="ghost" onClick={load}>Обновить</Button>
        <Button size="sm" iconLeft="scan-line" loading={busy} onClick={processOcr}>Обработать OCR</Button>
      </div>
      {data.items.length === 0
        ? <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Очередь пуста.</div>
        : <div className="irb-plat__card" style={{ padding: 0, overflow: "hidden" }}>
            {data.items.map((j, i) => (
              <div key={j.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 16px", borderTop: i ? "1px solid var(--border-subtle)" : "none" }}>
                <span className="irb-plat__mono" style={{ fontSize: 12, color: "var(--text-subtle)", minWidth: 36 }}>#{j.id}</span>
                <span style={{ flex: 1, minWidth: 0, fontSize: 13, color: "var(--text-strong)" }}>{j.kind}</span>
                {j.error ? <span style={{ fontSize: 11.5, color: "var(--danger,#c0392b)", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{j.error}</span> : null}
                <span style={{ fontSize: 12, fontWeight: 600, padding: "2px 9px", borderRadius: 999, background: "var(--surface-sunken,#f1efe9)", color: STATUS_COLOR[j.status] || "var(--text-subtle)" }}>{JOB_STATUS_RU[j.status] || j.status}</span>
              </div>
            ))}
          </div>}
      <p style={{ fontSize: 12, color: "var(--text-subtle)", margin: 0 }}>Воркеры забирают задачи по приоритету (больше — раньше). «Обработать OCR» прогоняет одну задачу распознавания синхронно.</p>
    </div>
  );
}

// ===== Онбординг-визард (#335) ==============================================
// Гайдед-флоу оператора платформы: учреждение + режим развёртывания -> применить
// (POST /api/admin/onboard) -> подсказка по нужным подключениям. Гейт super-admin.
function OnboardWizard({ toast, onGoConnections, onSelect }: { toast: ToastFn; onGoConnections: () => void; onSelect: (slug: string) => void }) {
  const [catalog, setCatalog] = React.useState<{ modes: DeploymentMode[]; topologies: DeploymentTopology[] } | null>(null);
  const [down, setDown] = React.useState(false);
  const [slug, setSlug] = React.useState("");
  const [name, setName] = React.useState("");
  const [fullName, setFullName] = React.useState("");
  const [mode, setMode] = React.useState("");
  const [topology, setTopology] = React.useState("cloud");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<DeploymentResolved | null>(null);

  React.useEffect(() => { (async () => {
    const r = await api.adminDeploymentCatalog();
    if (r.status === 404 || r.status === 501 || r.status === 403) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setCatalog(r.json.data); if (r.json.data.modes[0]) setMode(r.json.data.modes[0].key); }
  })(); }, []);

  const apply = async () => {
    const s = slug.trim();
    if (!s || !mode) { toast({ variant: "info", title: "Заполните поля", message: "Код арендатора и режим обязательны." }); return; }
    setBusy(true);
    const r = await api.adminOnboard({ tenant: s, mode, topology, name: name.trim(), fullName: fullName.trim() });
    setBusy(false);
    if (r.json?.ok && r.json.data?.deployment) {
      setResult(r.json.data.deployment); onSelect(s);
      toast({ variant: "success", title: "Онбординг применён", message: s });
    } else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db (оператор платформы)." });
    else if (r.status === 400) toast({ variant: "error", title: "Не применено", message: "Проверьте режим/топологию." });
    else toast({ variant: "error", title: "Не применено", message: "Повторите попытку." });
  };
  const reset = () => { setResult(null); setSlug(""); setName(""); setFullName(""); };

  if (down) return <SectionDown icon="check" title="Онбординг подключается отдельно" />;
  if (!catalog) return <div className="irb-plat__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка…</div>;

  if (result) {
    const KIND_RU: Record<string, string> = { irbis: "ИРБИС", jirbis: "jirbis", inforost: "Инфорост" };
    return (
      <div className="irb-plat__card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <Icon name="check" size={18} /><span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-strong)" }}>Шаг 1 готов — режим применён</span>
        </div>
        <div style={{ fontSize: 13, color: "var(--text-body)" }}>
          Арендатор <b>{result.tenant}</b> · режим <b>{result.mode_meta ? result.mode_meta.title : result.mode}</b> · {result.topology === "onprem" ? "on-prem" : "облако"}.
        </div>
        <div>
          <p className="irb-plat__cap" style={{ marginBottom: 6 }}>Шаг 2 — настройте подключения</p>
          {result.required_connections.length
            ? <div className="irb-plat__pick">{result.required_connections.map((c) => <span key={c} className="irb-plat__pickbtn irb-plat__pickbtn--on">{KIND_RU[c] || c}</span>)}</div>
            : <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>Внешние подключения для этого режима не требуются.</span>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {result.required_connections.length > 0 && <Button iconLeft="link" onClick={onGoConnections}>Настроить подключения</Button>}
          <Button variant="ghost" iconLeft="plus" onClick={reset}>Ещё арендатор</Button>
        </div>
      </div>
    );
  }

  const inStyle: React.CSSProperties = { width: "100%", boxSizing: "border-box" };
  return (
    <div className="irb-plat__card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
      <p style={{ fontSize: 13, color: "var(--text-subtle)", margin: 0 }}>Шаг 1 — учреждение и режим. Что Biblio заменяет и где работает определяет нужные подключения на шаге 2.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12 }}>
        <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Код арендатора</span><input className="irb-plat__in" style={inStyle} value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="vuz-spb" /></div>
        <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Краткое наименование</span><input className="irb-plat__in" style={inStyle} value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div className="irb-plat__fld"><span className="irb-plat__fld-lab">Полное наименование</span><input className="irb-plat__in" style={inStyle} value={fullName} onChange={(e) => setFullName(e.target.value)} /></div>
      </div>
      <div>
        <p className="irb-plat__cap" style={{ marginBottom: 8 }}>Режим — что Biblio заменяет</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {catalog.modes.map((m) => (
            <button key={m.key} type="button" onClick={() => setMode(m.key)}
              style={{ textAlign: "left", padding: "10px 12px", borderRadius: "var(--radius-md)", cursor: "pointer",
                border: "1px solid " + (mode === m.key ? "var(--accent)" : "var(--border-subtle)"), background: mode === m.key ? "var(--accent-weak)" : "var(--surface-card)" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{m.title}</div>
              <div style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 2 }}>{m.description}</div>
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="irb-plat__cap" style={{ marginBottom: 8 }}>Где работает</p>
        <div className="irb-plat__pick">
          {catalog.topologies.map((t) => (
            <button key={t.key} type="button" className={"irb-plat__pickbtn" + (topology === t.key ? " irb-plat__pickbtn--on" : "")} onClick={() => setTopology(t.key)}>{t.title}</button>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Button iconLeft="check" loading={busy} disabled={!slug.trim() || !mode} onClick={apply}>Применить и продолжить</Button>
      </div>
    </div>
  );
}
