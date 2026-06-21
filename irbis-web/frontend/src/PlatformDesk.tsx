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
import type { Tenant, BillingInfo } from "./api";
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

// Тарифные планы контура (MVP). Бэкенд может вернуть и иные коды — список
// дополняется фактическими значениями арендаторов.
const PLANS = ["free", "basic", "pro", "enterprise"] as const;
// Человекочитаемые подписи известных функциональных модулей; неизвестный код
// показываем как есть.
const MODULE_RU: Record<string, string> = {
  cataloging: "Каталогизация",
  circulation: "Книговыдача",
  acquisition: "Комплектование",
  provision: "Книгообеспеченность",
  cells: "Ячеистое хранение",
  inventory: "Инвентаризация",
  reader: "Читательский портал",
  ill: "МБА / ЭДД",
  analytics: "Аналитика и отчёты",
  authority: "Авторитетные файлы",
};
const moduleLabel = (code: string) => MODULE_RU[code] || code;

type Tab = "tenants" | "billing";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "tenants", label: "Арендаторы", icon: "layers" },
  { id: "billing", label: "Тариф и лимиты", icon: "credit-card" },
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
        : <BillingTab toast={toast} selected={selected} onSelect={setSelected} />}
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
  const [plan, setPlan] = React.useState<string>("basic");
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
      setSlug(""); setName(""); setAdminLogin(""); setPlan("basic"); setShowCreate(false);
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
            <thead><tr><th>Слаг</th><th>Наименование</th><th>Тариф</th><th>Создан</th><th style={{ textAlign: "right" }}>Действия</th></tr></thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.slug} aria-selected={selected === t.slug}>
                  <td className="irb-plat__mono">{t.slug}</td>
                  <td>{t.name || "—"}</td>
                  <td><span className="irb-plat__plan">{t.plan || "—"}</span></td>
                  <td className="irb-plat__mono" style={{ whiteSpace: "nowrap" }}>{t.createdAt || "—"}</td>
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
    if (r.status === 200 && r.json?.ok) {
      if (r.json.data) setBilling(r.json.data); else setBilling({ ...billing, plan });
      setTenants((ts) => (ts || []).map((t) => t.slug === selected ? { ...t, plan } : t));
      toast({ variant: "success", title: "Тариф изменён", message: selected + " → " + plan });
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт платформы не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  async function toggleModule(module: string, enabled: boolean) {
    if (!selected || !billing) return;
    setBusyModule(module);
    const r = await api.adminSetModule(selected, module, enabled);
    setBusyModule(null);
    if (r.status === 200 && r.json?.ok) {
      if (r.json.data) setBilling(r.json.data);
      else setBilling({ ...billing, modules: { ...billing.modules, [module]: enabled } });
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
    const planChoices = Array.from(new Set([...PLANS, billing.plan])).filter(Boolean);
    const moduleCodes = Object.keys(billing.modules || {});
    content = (
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 18 }}>
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

        {/* Лимиты vs потребление */}
        <div>
          <span className="irb-plat__cap">Лимиты и потребление</span>
          <div className="irb-plat__grid" style={{ marginTop: 9 }}>
            <Meter icon="file-text" name="Записи" used={billing.usage.records} limit={billing.limits.maxRecords} />
            <Meter icon="users" name="Читатели" used={billing.usage.readers} limit={billing.limits.maxReaders} />
            <Meter icon="archive" name="Хранилище" used={billing.usage.storageMb} limit={billing.limits.maxStorageMb} unit=" МБ" />
          </div>
        </div>

        {/* Модули */}
        <div>
          <span className="irb-plat__cap">Функциональные модули</span>
          {moduleCodes.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--text-subtle)", marginTop: 9 }}>Тариф не задаёт модулей — состав определяется грантами учёток.</div>
          ) : (
            <div className="irb-plat__card irb-plat__mods" style={{ marginTop: 9 }}>
              {moduleCodes.map((code) => {
                const on = !!billing.modules[code];
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
function Meter({ icon, name, used, limit, unit = "" }: { icon: IconName; name: string; used: number; limit: number; unit?: string }) {
  const u = Number.isFinite(used) ? used : 0;
  const lim = Number.isFinite(limit) && limit > 0 ? limit : 0;
  const ratio = lim ? u / lim : 0;
  const pct = Math.max(0, Math.min(100, Math.round(ratio * 100)));
  const color = ratio >= 0.9 ? "var(--danger-500)" : ratio >= 0.75 ? "var(--warning)" : "var(--status-available)";
  const fmt = (n: number) => Number.isFinite(n) ? n.toLocaleString("ru-RU") : "—";
  return (
    <div className="irb-plat__meter">
      <div className="irb-plat__meter-top">
        <span className="irb-plat__meter-name"><Icon name={icon} size={15} />{name}</span>
        <span className="irb-plat__meter-val">{fmt(u) + unit} / {lim ? fmt(lim) + unit : "∞"}</span>
      </div>
      <div className="irb-plat__track"><div className="irb-plat__fill" style={{ width: pct + "%", background: color }} /></div>
      <span className="irb-plat__meter-pct">{lim ? pct + "% использовано" : "лимит не задан"}</span>
    </div>
  );
}
