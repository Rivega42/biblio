// Администрирование (#187) — рабочий стол администратора. Read-heavy:
//   • Пользователи — таблица (логин / ФИО / активность / роли), создание учётки,
//     назначение ролей, включение/отключение.
//   • Роли — справочник (код / наименование / состав грантов).
//   • Аудит — журнал операций (время / актор / функция / результат).
//   • Базы — список баз контура (код / имя / публичность).
// Админ-маршруты публикуются отдельно (#187), поэтому КАЖДАЯ вкладка
// деградирует независимо: нет своего эндпойнта (404/501) — информер в этой
// вкладке, остальные продолжают работать; приложение не падает.
import React from "react";
import { api } from "./api";
import type { AdminUser, AdminRole, AuditEntry, AdminDatabase } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .adm__* — не пересекается с .stf__ / .cdesk__ / .acq__ / .bp__ / .irb-*.
const CSS = `
.adm{font-family:var(--font-ui);}
.adm__tabs{display:flex;gap:4px;padding:4px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-bottom:16px;width:fit-content;flex-wrap:wrap;}
.adm__tab{display:inline-flex;align-items:center;gap:7px;border:none;cursor:pointer;font-family:var(--font-ui);font-size:13px;font-weight:500;padding:7px 14px;border-radius:var(--radius-sm);background:transparent;color:var(--text-muted);}
.adm__tab:hover{color:var(--text-body);}
.adm__tab--on{background:var(--surface-card);color:var(--text-strong);font-weight:600;box-shadow:var(--shadow-sm);}
.adm__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;}
.adm__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.adm__tbl{width:100%;border-collapse:collapse;font-size:13px;}
.adm__tbl th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);padding:10px 14px;border-bottom:1px solid var(--border-subtle);background:var(--surface-sunken);white-space:nowrap;}
.adm__tbl td{padding:10px 14px;border-bottom:1px solid var(--border-subtle);vertical-align:middle;}
.adm__tbl tr:last-child td{border-bottom:none;}
.adm__tbl tr:hover td{background:var(--surface-hover);}
.adm__mono{font-family:var(--font-mono);font-size:12px;}
.adm__chip{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);background:var(--accent-weak);color:var(--accent-press);margin:1px 3px 1px 0;}
.adm__chip--gr{background:var(--surface-hover);color:var(--text-muted);font-family:var(--font-mono);}
.adm__dot{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;white-space:nowrap;}
.adm__dot i{width:7px;height:7px;border-radius:var(--radius-full);flex:none;}
.adm__dot--on i{background:var(--status-available,#3C7D3F);} .adm__dot--on{color:var(--status-available,#3C7D3F);}
.adm__dot--off i{background:var(--text-subtle);} .adm__dot--off{color:var(--text-subtle);}
.adm__res{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);}
.adm__res--ok{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);}
.adm__res--err{background:var(--danger-50,#FBE9E7);color:var(--danger-500);}
.adm__bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border-subtle);flex-wrap:wrap;}
.adm__form{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr)) auto;gap:10px;align-items:end;padding:14px;background:var(--surface-sunken);border-bottom:1px solid var(--border-subtle);}
.adm__fld{display:flex;flex-direction:column;gap:5px;}
.adm__fld-lab{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.adm__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.adm__in:focus{outline:none;border-color:var(--accent);}
.adm__rolepick{display:flex;flex-wrap:wrap;gap:6px;}
.adm__rolebtn{font-size:11.5px;font-weight:600;padding:4px 10px;border-radius:var(--radius-full);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-muted);cursor:pointer;}
.adm__rolebtn--on{background:var(--accent-weak);color:var(--accent-press);border-color:transparent;}
.adm__scroll{max-height:460px;overflow-y:auto;}
@media (max-width:760px){.adm__form{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("adm-css")) {
  const s = document.createElement("style"); s.id = "adm-css"; s.textContent = CSS; document.head.appendChild(s);
}

type Tab = "users" | "roles" | "audit" | "databases";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "users", label: "Пользователи", icon: "users" },
  { id: "roles", label: "Роли", icon: "shield" },
  { id: "audit", label: "Аудит", icon: "list" },
  { id: "databases", label: "Базы", icon: "archive" },
];

// Информер «эндпойнт вкладки не развёрнут».
function SectionDown({ icon, title }: { icon: IconName; title: string }) {
  return (
    <div className="adm__card" style={{ padding: 4 }}>
      <EmptyState icon={icon} title={title}
        description="Раздел свёрстан в Стиле A и работает поверх движка администрирования (#187). На текущем сервере соответствующий эндпойнт /api/admin/* ещё не развёрнут — данные появятся после его публикации. Остальные разделы продолжают работать." />
    </div>
  );
}

export function AdminDesk({ toast }: { toast: ToastFn }) {
  const [tab, setTab] = React.useState<Tab>("users");
  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Администрирование</h2>
        <span className="stf__pill">Учётки · роли · аудит · базы</span>
      </div>
    </div>
  );
  return (
    <div className="adm">
      {head}
      <div className="adm__tabs" role="tablist" aria-label="Разделы администрирования">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
            className={"adm__tab" + (tab === t.id ? " adm__tab--on" : "")} onClick={() => setTab(t.id)}>
            <Icon name={t.icon} size={15} />{t.label}
          </button>
        ))}
      </div>
      {tab === "users" ? <UsersTab toast={toast} />
        : tab === "roles" ? <RolesTab />
        : tab === "audit" ? <AuditTab />
        : <DatabasesTab />}
    </div>
  );
}

// ===== Пользователи ========================================================
function UsersTab({ toast }: { toast: ToastFn }) {
  const [users, setUsers] = React.useState<AdminUser[] | null>(null);
  const [roles, setRoles] = React.useState<AdminRole[]>([]);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState<string | number | null>(null);
  const [editRolesFor, setEditRolesFor] = React.useState<string | number | null>(null);
  const [draftRoles, setDraftRoles] = React.useState<string[]>([]);

  // форма создания
  const [showCreate, setShowCreate] = React.useState(false);
  const [login, setLogin] = React.useState(""); const [fullName, setFullName] = React.useState("");
  const [password, setPassword] = React.useState(""); const [newRoles, setNewRoles] = React.useState<string[]>([]);
  const [creating, setCreating] = React.useState(false);

  async function load() {
    const [u, r] = await Promise.all([api.adminUsers(), api.adminRoles()]);
    if (u.status === 404 || u.status === 501) { setDown(true); return; }
    if (u.json?.ok && u.json.data) setUsers(u.json.data.items || []);
    else setUsers([]);
    if (r.json?.ok && r.json.data) setRoles(r.json.data.items || []);
  }
  React.useEffect(() => { void load(); }, []);

  const roleCodes = roles.map((r) => r.code);
  const toggle = (arr: string[], code: string) => arr.includes(code) ? arr.filter((c) => c !== code) : arr.concat([code]);

  async function createUser() {
    const l = login.trim();
    if (!l || !password.trim()) { toast({ variant: "info", title: "Заполните учётку", message: "Логин и пароль обязательны." }); return; }
    setCreating(true);
    const r = await api.adminCreateUser({ login: l, fullName: fullName.trim(), password: password.trim(), roles: newRoles.length ? newRoles : undefined });
    setCreating(false);
    if (r.status === 200 && r.json?.ok && r.json.data) {
      setUsers((us) => [r.json!.data!].concat(us || []));
      toast({ variant: "success", title: "Учётка создана", message: l });
      setLogin(""); setFullName(""); setPassword(""); setNewRoles([]); setShowCreate(false);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Создание недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users." });
    else toast({ variant: "error", title: "Не создано", message: "Возможно, логин занят." });
  }

  async function toggleActive(u: AdminUser) {
    setBusy(u.id);
    const r = await api.adminSetActive(u.id, !u.active);
    setBusy(null);
    if (r.status === 200 && r.json?.ok) {
      setUsers((us) => (us || []).map((x) => x.id === u.id ? (r.json!.data || { ...x, active: !x.active }) : x));
      toast({ variant: "success", title: !u.active ? "Учётка включена" : "Учётка отключена", message: u.login });
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  function startEditRoles(u: AdminUser) { setEditRolesFor(u.id); setDraftRoles(u.roles || []); }
  async function saveRoles(u: AdminUser) {
    setBusy(u.id);
    const r = await api.adminSetRoles(u.id, draftRoles);
    setBusy(null);
    if (r.status === 200 && r.json?.ok) {
      setUsers((us) => (us || []).map((x) => x.id === u.id ? (r.json!.data || { ...x, roles: draftRoles }) : x));
      toast({ variant: "success", title: "Роли назначены", message: u.login + " · " + (draftRoles.join(", ") || "без ролей") });
      setEditRolesFor(null);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users." });
    else toast({ variant: "error", title: "Не назначено", message: "Повторите попытку." });
  }

  if (down) return <SectionDown icon="users" title="Управление пользователями подключается отдельно" />;

  return (
    <div className="adm__card">
      <div className="adm__bar">
        <span className="adm__cap">Учётные записи сотрудников {users ? "· " + users.length : ""}</span>
        <Button size="sm" iconLeft={showCreate ? "x" : "plus"} variant={showCreate ? "ghost" : "primary"} onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Свернуть" : "Новая учётка"}</Button>
      </div>

      {showCreate && (
        <div className="adm__form">
          <div className="adm__fld"><label className="adm__fld-lab">Логин</label><input className="adm__in" value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="off" /></div>
          <div className="adm__fld"><label className="adm__fld-lab">ФИО</label><input className="adm__in" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="off" /></div>
          <div className="adm__fld"><label className="adm__fld-lab">Пароль</label><input className="adm__in" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" /></div>
          <div className="adm__fld" style={{ gridColumn: "1 / -2" }}>
            <label className="adm__fld-lab">Роли</label>
            {roleCodes.length ? (
              <div className="adm__rolepick">
                {roleCodes.map((c) => <button key={c} type="button" className={"adm__rolebtn" + (newRoles.includes(c) ? " adm__rolebtn--on" : "")} onClick={() => setNewRoles((a) => toggle(a, c))}>{c}</button>)}
              </div>
            ) : <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>Справочник ролей недоступен — назначьте позже.</span>}
          </div>
          <Button iconLeft="check" loading={creating} onClick={createUser}>Создать</Button>
        </div>
      )}

      {users === null ? (
        <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка пользователей…</div>
      ) : users.length === 0 ? (
        <div style={{ padding: 4 }}><EmptyState icon="users" title="Учётных записей нет" description="Создайте первую учётную запись сотрудника — доступ к функциям определяется её ролями и грантами." /></div>
      ) : (
        <div className="adm__scroll">
          <table className="adm__tbl">
            <thead><tr><th>Логин</th><th>ФИО</th><th>Статус</th><th>Роли</th><th style={{ textAlign: "right" }}>Действия</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="adm__mono">{u.login}</td>
                  <td>{u.fullName || "—"}</td>
                  <td><span className={"adm__dot adm__dot--" + (u.active ? "on" : "off")}><i />{u.active ? "Активна" : "Отключена"}</span></td>
                  <td>
                    {editRolesFor === u.id ? (
                      <div className="adm__rolepick">
                        {(roleCodes.length ? roleCodes : u.roles).map((c) => <button key={c} type="button" className={"adm__rolebtn" + (draftRoles.includes(c) ? " adm__rolebtn--on" : "")} onClick={() => setDraftRoles((a) => toggle(a, c))}>{c}</button>)}
                      </div>
                    ) : (u.roles && u.roles.length ? u.roles.map((r) => <span key={r} className="adm__chip">{r}</span>) : <span style={{ color: "var(--text-subtle)" }}>—</span>)}
                  </td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {editRolesFor === u.id ? (
                      <>
                        <Button size="sm" iconLeft="save" loading={busy === u.id} onClick={() => saveRoles(u)}>Сохранить</Button>{" "}
                        <Button size="sm" variant="ghost" onClick={() => setEditRolesFor(null)}>Отмена</Button>
                      </>
                    ) : (
                      <>
                        <Button size="sm" variant="ghost" iconLeft="shield" onClick={() => startEditRoles(u)}>Роли</Button>{" "}
                        <Button size="sm" variant={u.active ? "ghost" : "secondary"} iconLeft={u.active ? "eye-off" : "check-circle"} loading={busy === u.id} onClick={() => toggleActive(u)}>{u.active ? "Отключить" : "Включить"}</Button>
                      </>
                    )}
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

// ===== Роли (справочник) ====================================================
function RolesTab() {
  const [roles, setRoles] = React.useState<AdminRole[] | null>(null);
  const [down, setDown] = React.useState(false);
  React.useEffect(() => { (async () => {
    const r = await api.adminRoles();
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) setRoles(r.json.data.items || []); else setRoles([]);
  })(); }, []);

  if (down) return <SectionDown icon="shield" title="Справочник ролей подключается отдельно" />;
  if (roles === null) return <div className="adm__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка ролей…</div>;
  if (roles.length === 0) return <div className="adm__card" style={{ padding: 4 }}><EmptyState icon="shield" title="Ролей нет" description="Справочник ролей пуст. Роли группируют гранты и назначаются учётным записям." /></div>;

  return (
    <div className="adm__card adm__scroll">
      <table className="adm__tbl">
        <thead><tr><th>Код</th><th>Наименование</th><th>Гранты</th></tr></thead>
        <tbody>
          {roles.map((r) => (
            <tr key={r.code}>
              <td className="adm__mono">{r.code}</td>
              <td>{r.name || "—"}{r.description ? <div style={{ fontSize: 11.5, color: "var(--text-subtle)", marginTop: 2 }}>{r.description}</div> : null}</td>
              <td>{r.grants && r.grants.length ? r.grants.map((g) => <span key={g} className="adm__chip adm__chip--gr">{g}</span>) : <span style={{ color: "var(--text-subtle)" }}>—</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ===== Аудит ================================================================
function AuditTab() {
  const [rows, setRows] = React.useState<AuditEntry[] | null>(null);
  const [down, setDown] = React.useState(false);
  const [limit, setLimit] = React.useState(50);
  const [loading, setLoading] = React.useState(false);

  async function load(lim: number) {
    setLoading(true);
    const r = await api.adminAudit(lim);
    setLoading(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) setRows(r.json.data.items || []); else setRows([]);
  }
  React.useEffect(() => { void load(limit); }, [limit]);

  if (down) return <SectionDown icon="list" title="Журнал аудита подключается отдельно" />;

  return (
    <div className="adm__card">
      <div className="adm__bar">
        <span className="adm__cap">Журнал операций {rows ? "· " + rows.length : ""}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>Показывать</span>
          <select className="adm__in" style={{ width: "auto", padding: "5px 9px" }} value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10))}>
            {[25, 50, 100, 200].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <Button size="sm" variant="ghost" iconLeft="refresh-cw" loading={loading} onClick={() => load(limit)}>Обновить</Button>
        </div>
      </div>
      {rows === null ? (
        <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка журнала…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: 4 }}><EmptyState icon="list" title="Журнал пуст" description="Операции сотрудников (вход, правка записей, выдача, администрирование) фиксируются здесь с меткой времени, актором и результатом." /></div>
      ) : (
        <div className="adm__scroll">
          <table className="adm__tbl">
            <thead><tr><th>Время</th><th>Актор</th><th>Функция</th><th>Результат</th></tr></thead>
            <tbody>
              {rows.map((e, i) => {
                const ok = e.ok != null ? e.ok : (e.result ? /ok|success|успе|200/i.test(e.result) : true);
                return (
                  <tr key={i}>
                    <td className="adm__mono" style={{ whiteSpace: "nowrap" }}>{e.ts || "—"}</td>
                    <td className="adm__mono">{e.actor || "—"}</td>
                    <td>{e.function || e.fn || "—"}{e.detail ? <div style={{ fontSize: 11.5, color: "var(--text-subtle)", marginTop: 2 }}>{e.detail}</div> : null}</td>
                    <td><span className={"adm__res adm__res--" + (ok ? "ok" : "err")}><Icon name={ok ? "check" : "x"} size={12} />{e.result || (ok ? "OK" : "ошибка")}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ===== Базы данных ==========================================================
function DatabasesTab() {
  const [dbs, setDbs] = React.useState<AdminDatabase[] | null>(null);
  const [down, setDown] = React.useState(false);
  React.useEffect(() => { (async () => {
    // основной эндпойнт админа; при его отсутствии — общий /api/databases.
    let r = await api.adminDatabases();
    if (r.status === 404 || r.status === 501) {
      const g = await api.databases();
      if (g.json?.ok && g.json.data) { setDbs((g.json.data.items || []).map((d) => ({ code: d.code, name: d.name, public: d.public, count: d.count }))); return; }
      setDown(true); return;
    }
    if (r.json?.ok && r.json.data) setDbs(r.json.data.items || []); else setDbs([]);
  })(); }, []);

  if (down) return <SectionDown icon="archive" title="Список баз подключается отдельно" />;
  if (dbs === null) return <div className="adm__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка баз…</div>;
  if (dbs.length === 0) return <div className="adm__card" style={{ padding: 4 }}><EmptyState icon="archive" title="Баз нет" description="Список баз данных контура пуст." /></div>;

  return (
    <div className="adm__card adm__scroll">
      <table className="adm__tbl">
        <thead><tr><th>Код</th><th>Наименование</th><th>Доступ</th><th style={{ textAlign: "right" }}>Записей</th></tr></thead>
        <tbody>
          {dbs.map((d) => (
            <tr key={d.code}>
              <td className="adm__mono">{d.code}</td>
              <td>{d.name}</td>
              <td><span className={"adm__dot adm__dot--" + (d.public ? "on" : "off")}><i />{d.public ? "Публичная" : "Служебная"}</span></td>
              <td className="adm__mono" style={{ textAlign: "right" }}>{d.count != null ? d.count.toLocaleString("ru-RU") : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
