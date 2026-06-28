// Администрирование (#187) — рабочий стол администратора. Read-heavy:
//   • Пользователи — таблица (логин / ФИО / активность / роли + гранты), создание
//     учётки, назначение ролей, включение/отключение.
//   • Роли — справочник (код роли / состав грантов function@db:level).
//   • Аудит — журнал операций (время / актор / функция / результат + detail).
//   • Базы — список баз контура (код / имя / публичность).
//
// ВАЖНО (контракт бэкенда core.py #187, проверено по строкам 2427–2539):
//   GET  /api/admin/users      -> ok({users:[{id,login,fullName,active,roles[],grants[{function,db,level}]}]})
//        ВНИМАНИЕ: ключ data.USERS (НЕ items), а в api.ts тип объявлен как {items},
//        поэтому читаем сырой data.users, минуя дженерик-тип клиента.
//   POST /api/admin/users      -> ok({id,login,roles})            (НЕ полный AdminUser)
//   POST /api/admin/users/roles  {userId,roles[]} -> ok({ok,userId,roles})
//   POST /api/admin/users/active {userId,active}   -> ok({ok,userId,active})
//   GET  /api/admin/roles      -> ok({roles:[{name,grants:[{function,db,level}]}]})
//        ВНИМАНИЕ: ключ data.ROLES (НЕ items); role.NAME (нет поля code);
//        grants — МАССИВ ОБЪЕКТОВ {function,db,level}, не строк.
//   GET  /api/admin/audit?limit= -> ok({items:[{ts(float epoch),actor,function,db,mfn,result,detail{}}]})
//   GET  /api/admin/databases    -> ok({items:[{code,name,public,count?}], default})
//
// Все surface — staff-only + грант admin.users / admin.db на уровне admin:
// у seed-учётки `librarian` этих грантов НЕТ (роли reader-service+cataloger), у
// seed-учётки `admin` (роль administrator) — ЕСТЬ. Тестировать под admin/admin.
//
// Так как ответы POST частичны (create -> только id/login/roles; roles/active ->
// {ok,userId,...}), после каждой мутации мы ПЕРЕЧИТЫВАЕМ список — это и проще, и
// гарантирует консистентность строки (login/fullName/active/roles/grants).
//
// Мягкая деградация: нет эндпойнта вкладки (404/501) — информер в этой вкладке,
// остальные продолжают работать; приложение не падает.
import React from "react";
import { api } from "./api";
import type { AuditEntry, AdminDatabase, PdnAccessEntry } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// --- Локальные типы, отражающие ФАКТИЧЕСКИЕ тела ответов core.py (#187). ------
// Они НАМЕРЕННО отличаются от дженериков api.ts (там users/roles ошибочно лежат
// под items, а grants роли — строки); читаем сырой data соответствующего ключа.
type AdmGrant = { function: string; db: string; level: string };
type AdmUser = {
  id: string | number; login: string; fullName?: string;
  active: boolean; roles: string[]; grants?: AdmGrant[];
};
type AdmRole = { name: string; grants: AdmGrant[] };

// Грант → компактная строка-чип «function@db:level» (db='*' опускаем).
const grantLabel = (g: AdmGrant): string =>
  g.function + (g.db && g.db !== "*" ? "@" + g.db : "") + ":" + g.level;

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
.adm__grants{display:flex;flex-wrap:wrap;gap:3px;max-width:340px;}
@media (max-width:760px){.adm__form{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("adm-css")) {
  const s = document.createElement("style"); s.id = "adm-css"; s.textContent = CSS; document.head.appendChild(s);
}

type Tab = "users" | "roles" | "audit" | "pdn" | "databases";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "users", label: "Пользователи", icon: "users" },
  { id: "roles", label: "Роли", icon: "shield" },
  { id: "audit", label: "Аудит", icon: "list" },
  { id: "pdn", label: "Доступ к ПДн", icon: "eye" },
  { id: "databases", label: "Базы", icon: "archive" },
];

// Информер «эндпойнт вкладки не развёрнут» (404/501) или «нет прав» (403).
function SectionDown({ icon, title, description }: { icon: IconName; title: string; description?: string }) {
  return (
    <div className="adm__card" style={{ padding: 4 }}>
      <EmptyState icon={icon} title={title}
        description={description ||
          "Раздел свёрстан в Стиле A и работает поверх движка администрирования (#187). На текущем сервере соответствующий эндпойнт /api/admin/* ещё не развёрнут — данные появятся после его публикации. Остальные разделы продолжают работать."} />
    </div>
  );
}

// Текст информера для 403 (нет грантов admin.users/admin.db).
const FORBIDDEN_DESC =
  "Текущая учётная запись не имеет грантов администрирования (admin.users / admin.db на уровне admin). " +
  "Войдите учётной записью с ролью «administrator» (в демо-контуре — admin / admin).";

export function AdminDesk({ toast }: { toast: ToastFn }) {
  const [tab, setTab] = React.useState<Tab>("users");
  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Администрирование</h2>
        <span className="stf__pill">Учётки · роли · аудит · ПДн · базы</span>
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
        : tab === "pdn" ? <PdnAccessTab />
        : <DatabasesTab />}
    </div>
  );
}

// ===== Пользователи ========================================================
function UsersTab({ toast }: { toast: ToastFn }) {
  const [users, setUsers] = React.useState<AdmUser[] | null>(null);
  const [roles, setRoles] = React.useState<AdmRole[]>([]);
  // 'live' — данные есть; 'down' — 404/501; 'forbidden' — 403 (нет грантов).
  const [state, setState] = React.useState<"live" | "down" | "forbidden">("live");
  const [busy, setBusy] = React.useState<string | number | null>(null);
  const [editRolesFor, setEditRolesFor] = React.useState<string | number | null>(null);
  const [draftRoles, setDraftRoles] = React.useState<string[]>([]);

  // форма создания
  const [showCreate, setShowCreate] = React.useState(false);
  const [login, setLogin] = React.useState(""); const [fullName, setFullName] = React.useState("");
  const [password, setPassword] = React.useState(""); const [newRoles, setNewRoles] = React.useState<string[]>([]);
  const [creating, setCreating] = React.useState(false);

  // Перечитать список учёток + справочник ролей с ЖИВЫХ эндпойнтов.
  // ВАЖНО: backend кладёт массивы под data.users / data.roles (НЕ items) —
  // читаем сырой data, минуя (неверный) дженерик-тип api.ts.
  async function load() {
    const [u, r] = await Promise.all([api.adminUsers(), api.adminRoles()]);
    if (u.status === 404 || u.status === 501) { setState("down"); return; }
    if (u.status === 403) { setState("forbidden"); return; }
    const ud: any = u.json?.data;
    if (u.json?.ok && ud) setUsers((ud.users || ud.items || []) as AdmUser[]);
    else setUsers([]);
    const rd: any = r.json?.data;
    if (r.json?.ok && rd) setRoles((rd.roles || rd.items || []) as AdmRole[]);
    setState("live");
  }
  React.useEffect(() => { void load(); }, []);

  const roleNames = roles.map((r) => r.name);
  const toggle = (arr: string[], code: string) => arr.includes(code) ? arr.filter((c) => c !== code) : arr.concat([code]);

  async function createUser() {
    const l = login.trim();
    if (!l || !password.trim()) { toast({ variant: "info", title: "Заполните учётку", message: "Логин и пароль обязательны." }); return; }
    setCreating(true);
    const r = await api.adminCreateUser({ login: l, fullName: fullName.trim(), password: password.trim(), roles: newRoles.length ? newRoles : undefined });
    setCreating(false);
    if (r.status === 200 && r.json?.ok) {
      // Ответ создания частичный ({id,login,roles}) — перечитываем список,
      // чтобы строка несла полный набор (fullName/active/grants).
      toast({ variant: "success", title: "Учётка создана", message: l });
      setLogin(""); setFullName(""); setPassword(""); setNewRoles([]); setShowCreate(false);
      void load();
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Создание недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users (роль administrator)." });
    else if (r.status === 409) toast({ variant: "error", title: "Логин занят", message: "Учётная запись с таким логином уже есть." });
    else if (r.status === 400) toast({ variant: "error", title: "Не создано", message: "Логин обязателен." });
    else toast({ variant: "error", title: "Не создано", message: "Повторите попытку." });
  }

  async function toggleActive(u: AdmUser) {
    setBusy(u.id);
    const r = await api.adminSetActive(u.id, !u.active);
    setBusy(null);
    if (r.status === 200 && r.json?.ok) {
      // Ответ {ok,userId,active} — обновляем флаг в существующей строке.
      const active = (r.json.data as any)?.active ?? !u.active;
      setUsers((us) => (us || []).map((x) => x.id === u.id ? { ...x, active } : x));
      toast({ variant: "success", title: active ? "Учётка включена" : "Учётка отключена", message: u.login });
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users." });
    else if (r.status === 404) toast({ variant: "error", title: "Не найдено", message: "Учётная запись не найдена." });
    else toast({ variant: "error", title: "Не изменено", message: "Повторите попытку." });
  }

  function startEditRoles(u: AdmUser) { setEditRolesFor(u.id); setDraftRoles(u.roles || []); }
  async function saveRoles(u: AdmUser) {
    setBusy(u.id);
    const r = await api.adminSetRoles(u.id, draftRoles);
    setBusy(null);
    if (r.status === 200 && r.json?.ok) {
      // Ответ {ok,userId,roles} — применяем НОРМАЛИЗОВАННЫЙ роль-набор сервера в строку.
      const applied = ((r.json.data as any)?.roles as string[]) || draftRoles;
      setUsers((us) => (us || []).map((x) => x.id === u.id ? { ...x, roles: applied } : x));
      toast({ variant: "success", title: "Роли назначены", message: u.login + " · " + (applied.join(", ") || "без ролей") });
      setEditRolesFor(null);
    } else if (r.status === 404 || r.status === 501) toast({ variant: "info", title: "Недоступно", message: "Эндпойнт администрирования не развёрнут." });
    else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.users." });
    else toast({ variant: "error", title: "Не назначено", message: "Повторите попытку." });
  }

  if (state === "down") return <SectionDown icon="users" title="Управление пользователями подключается отдельно" />;
  if (state === "forbidden") return <SectionDown icon="shield" title="Недостаточно прав для администрирования" description={FORBIDDEN_DESC} />;

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
            {roleNames.length ? (
              <div className="adm__rolepick">
                {roleNames.map((c) => <button key={c} type="button" className={"adm__rolebtn" + (newRoles.includes(c) ? " adm__rolebtn--on" : "")} onClick={() => setNewRoles((a) => toggle(a, c))}>{c}</button>)}
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
            <thead><tr><th>Логин</th><th>ФИО</th><th>Статус</th><th>Роли</th><th>Гранты</th><th style={{ textAlign: "right" }}>Действия</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="adm__mono">{u.login}</td>
                  <td>{u.fullName || "—"}</td>
                  <td><span className={"adm__dot adm__dot--" + (u.active ? "on" : "off")}><i />{u.active ? "Активна" : "Отключена"}</span></td>
                  <td>
                    {editRolesFor === u.id ? (
                      <div className="adm__rolepick">
                        {(roleNames.length ? roleNames : u.roles).map((c) => <button key={c} type="button" className={"adm__rolebtn" + (draftRoles.includes(c) ? " adm__rolebtn--on" : "")} onClick={() => setDraftRoles((a) => toggle(a, c))}>{c}</button>)}
                      </div>
                    ) : (u.roles && u.roles.length ? u.roles.map((r) => <span key={r} className="adm__chip">{r}</span>) : <span style={{ color: "var(--text-subtle)" }}>—</span>)}
                  </td>
                  <td>
                    {u.grants && u.grants.length ? (
                      <div className="adm__grants">
                        {u.grants.map((g, i) => <span key={i} className="adm__chip adm__chip--gr">{grantLabel(g)}</span>)}
                      </div>
                    ) : <span style={{ color: "var(--text-subtle)" }}>—</span>}
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
  const [roles, setRoles] = React.useState<AdmRole[] | null>(null);
  const [state, setState] = React.useState<"live" | "down" | "forbidden">("live");
  React.useEffect(() => { (async () => {
    const r = await api.adminRoles();
    if (r.status === 404 || r.status === 501) { setState("down"); return; }
    if (r.status === 403) { setState("forbidden"); return; }
    const rd: any = r.json?.data;
    if (r.json?.ok && rd) setRoles((rd.roles || rd.items || []) as AdmRole[]); else setRoles([]);
    setState("live");
  })(); }, []);

  if (state === "down") return <SectionDown icon="shield" title="Справочник ролей подключается отдельно" />;
  if (state === "forbidden") return <SectionDown icon="shield" title="Недостаточно прав для администрирования" description={FORBIDDEN_DESC} />;
  if (roles === null) return <div className="adm__card" style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка ролей…</div>;
  if (roles.length === 0) return <div className="adm__card" style={{ padding: 4 }}><EmptyState icon="shield" title="Ролей нет" description="Справочник ролей пуст. Роли группируют гранты и назначаются учётным записям." /></div>;

  return (
    <div className="adm__card adm__scroll">
      <table className="adm__tbl">
        <thead><tr><th>Роль</th><th>Грантов</th><th>Состав грантов</th></tr></thead>
        <tbody>
          {roles.map((r) => (
            <tr key={r.name}>
              <td className="adm__mono">{r.name}</td>
              <td className="adm__mono" style={{ color: "var(--text-subtle)" }}>{(r.grants || []).length}</td>
              <td>
                <div className="adm__grants" style={{ maxWidth: 560 }}>
                  {r.grants && r.grants.length
                    ? r.grants.map((g, i) => <span key={i} className="adm__chip adm__chip--gr">{grantLabel(g)}</span>)
                    : <span style={{ color: "var(--text-subtle)" }}>—</span>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ===== Аудит ================================================================
// Backend отдаёт ts как float epoch (сек) и detail как ОБЪЕКТ — форматируем оба.
function fmtAuditTs(ts: any): string {
  if (ts == null) return "—";
  const n = typeof ts === "number" ? ts : parseFloat(String(ts));
  if (!isFinite(n)) return String(ts);
  // epoch в секундах → мс. (значения вида 1.7e9 — секунды)
  const ms = n < 1e12 ? n * 1000 : n;
  const d = new Date(ms);
  return isNaN(d.getTime()) ? String(ts) : d.toLocaleString("ru-RU");
}
function fmtAuditDetail(detail: any): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (typeof detail === "object") {
    const parts = Object.keys(detail).map((k) => {
      const v = detail[k];
      return k + "=" + (v != null && typeof v === "object" ? JSON.stringify(v) : String(v));
    });
    return parts.join(" · ");
  }
  return String(detail);
}
const auditOk = (r: string | undefined): boolean =>
  r ? /^ok$|success|успе|^2\d\d$/i.test(r) : true;

function AuditTab() {
  const [rows, setRows] = React.useState<AuditEntry[] | null>(null);
  const [state, setState] = React.useState<"live" | "down" | "forbidden">("live");
  const [limit, setLimit] = React.useState(50);
  const [loading, setLoading] = React.useState(false);

  async function load(lim: number) {
    setLoading(true);
    const r = await api.adminAudit(lim);
    setLoading(false);
    if (r.status === 404 || r.status === 501) { setState("down"); return; }
    if (r.status === 403) { setState("forbidden"); return; }
    if (r.json?.ok && r.json.data) setRows(r.json.data.items || []); else setRows([]);
    setState("live");
  }
  React.useEffect(() => { void load(limit); }, [limit]);

  if (state === "down") return <SectionDown icon="list" title="Журнал аудита подключается отдельно" />;
  if (state === "forbidden") return <SectionDown icon="shield" title="Недостаточно прав для администрирования" description={FORBIDDEN_DESC} />;

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
                const ok = e.ok != null ? e.ok : auditOk(e.result);
                const detailStr = fmtAuditDetail((e as any).detail);
                const fn = e.function || (e as any).fn || "—";
                const db = (e as any).db;
                return (
                  <tr key={i}>
                    <td className="adm__mono" style={{ whiteSpace: "nowrap" }}>{fmtAuditTs(e.ts)}</td>
                    <td className="adm__mono">{e.actor || "—"}</td>
                    <td>
                      {fn}{db ? <span className="adm__mono" style={{ color: "var(--text-subtle)" }}> · {db}</span> : null}
                      {detailStr ? <div style={{ fontSize: 11.5, color: "var(--text-subtle)", marginTop: 2 }}>{detailStr}</div> : null}
                    </td>
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

// ===== Доступ к ПДн (152-ФЗ, #199) ==========================================
// Журнал обращений к персональным данным субъектов: когда / кто (актор) /
// субъект (билет читателя) / действие. Лимит + обновление, как у журнала аудита.
// 404/501 → информер (эндпойнт /api/admin/pdn-access ещё не развёрнут); 403 → нет прав.
function PdnAccessTab() {
  const [rows, setRows] = React.useState<PdnAccessEntry[] | null>(null);
  const [state, setState] = React.useState<"live" | "down" | "forbidden">("live");
  const [limit, setLimit] = React.useState(50);
  const [loading, setLoading] = React.useState(false);

  async function load(lim: number) {
    setLoading(true);
    const r = await api.pdnAccess(lim);
    setLoading(false);
    if (r.status === 404 || r.status === 501) { setState("down"); return; }
    if (r.status === 403) { setState("forbidden"); return; }
    if (r.json?.ok && r.json.data) setRows(r.json.data.items || []); else setRows([]);
    setState("live");
  }
  React.useEffect(() => { void load(limit); }, [limit]);

  if (state === "down") return <SectionDown icon="eye" title="Журнал доступа к ПДн подключается отдельно" />;
  if (state === "forbidden") return <SectionDown icon="shield" title="Недостаточно прав для администрирования" description={FORBIDDEN_DESC} />;

  return (
    <div className="adm__card">
      <div className="adm__bar">
        <span className="adm__cap">Доступ к персональным данным · 152-ФЗ {rows ? "· " + rows.length : ""}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>Показывать</span>
          <select className="adm__in" style={{ width: "auto", padding: "5px 9px" }} value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10))}>
            {[25, 50, 100, 200].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <Button size="sm" variant="ghost" iconLeft="refresh-cw" loading={loading} onClick={() => load(limit)}>Обновить</Button>
        </div>
      </div>
      {rows === null ? (
        <div style={{ padding: 16, color: "var(--text-subtle)", fontSize: 13 }}>Загрузка журнала ПДн…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: 4 }}><EmptyState icon="eye" title="Обращений к ПДн нет" description="Здесь фиксируется каждое обращение сотрудника или системы к персональным данным читателя — с меткой времени, актором, субъектом (билетом) и характером действия. Журнал — основа отчётности по 152-ФЗ." /></div>
      ) : (
        <div className="adm__scroll">
          <table className="adm__tbl">
            <thead><tr><th>Время</th><th>Актор</th><th>Субъект (билет)</th><th>Действие</th></tr></thead>
            <tbody>
              {rows.map((e, i) => (
                <tr key={i}>
                  <td className="adm__mono" style={{ whiteSpace: "nowrap" }}>{e.ts || "—"}</td>
                  <td className="adm__mono">{e.actor || "—"}</td>
                  <td className="adm__mono">{e.subject || "—"}</td>
                  <td>{e.action || "—"}</td>
                </tr>
              ))}
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
  const [state, setState] = React.useState<"live" | "down" | "forbidden">("live");
  React.useEffect(() => { (async () => {
    // основной эндпойнт админа; при его отсутствии — общий /api/databases.
    const r = await api.adminDatabases();
    if (r.status === 403) { setState("forbidden"); return; }
    if (r.status === 404 || r.status === 501) {
      const g = await api.databases();
      if (g.json?.ok && g.json.data) { setDbs((g.json.data.items || []).map((d) => ({ code: d.code, name: d.name, public: d.public, count: d.count }))); setState("live"); return; }
      setState("down"); return;
    }
    if (r.json?.ok && r.json.data) setDbs(r.json.data.items || []); else setDbs([]);
    setState("live");
  })(); }, []);

  if (state === "down") return <SectionDown icon="archive" title="Список баз подключается отдельно" />;
  if (state === "forbidden") return <SectionDown icon="shield" title="Недостаточно прав для администрирования" description={FORBIDDEN_DESC} />;
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
