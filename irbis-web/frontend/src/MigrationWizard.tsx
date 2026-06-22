// Онбординг-мастер миграции (#225; epic #223) — перенос данных из существующей
// установки ИРБИС64 в арендатора Biblio, по шагам:
//   1. Источник   — режим «Сеть» (хост/порт/логин/пароль/рабочая станция) ИЛИ
//                   «Локальный путь» (каталог данных ИРБИС, напр. C:\IRBIS64\Datai).
//                   Креды живут только в форме: не сохраняются и не логируются.
//   2. Изучение   — «Изучить источник» → /inspect → таблица обнаруженных БД
//                   (код / название / число записей) + раскрываемый по каждой
//                   список полей с пометкой «допполе» для кастомных и частотами.
//   3. Выбор      — чекбоксы каких БД мигрировать, целевой арендатор, тумблер
//                   «Пробный прогон (dry-run)».
//   4. Запуск     — «Мигрировать» → /run → отчёт {прочитано, загружено,
//                   читателей, пропущено, ошибок}; для dry-run явно «ничего не
//                   записано».
// Бэкенд миграции публикуется отдельно (#225), поэтому мастер деградирует мягко:
// нет эндпойнта (404/501) — информер на текущем шаге, приложение не падает.
import React from "react";
import { api } from "./api";
import type { MigrateMode, MigrateSource, MigrateDatabase, MigrateField, MigrateReport } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .irb-mig* — не пересекается с .stf__ / .adm__ / .irb-plat* /
// .cdesk__ / .acq__ / .bp__ / прочими .irb-*.
const CSS = `
.irb-mig{font-family:var(--font-ui);}
.irb-mig__steps{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:18px;}
.irb-mig__step{display:inline-flex;align-items:center;gap:8px;border:none;background:transparent;cursor:default;font-family:var(--font-ui);padding:6px 4px;color:var(--text-subtle);}
.irb-mig__step--clickable{cursor:pointer;}
.irb-mig__step-no{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:var(--radius-full);background:var(--surface-hover);color:var(--text-muted);font-size:12px;font-weight:700;flex:none;border:1px solid var(--border-subtle);}
.irb-mig__step--on .irb-mig__step-no{background:var(--accent);color:var(--accent-fg);border-color:transparent;}
.irb-mig__step--done .irb-mig__step-no{background:var(--accent-weak);color:var(--accent-press);border-color:transparent;}
.irb-mig__step-lab{font-size:12.5px;font-weight:600;color:var(--text-muted);}
.irb-mig__step--on .irb-mig__step-lab{color:var(--text-strong);}
.irb-mig__step-sep{color:var(--text-subtle);flex:none;}
.irb-mig__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;}
.irb-mig__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.irb-mig__bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border-subtle);flex-wrap:wrap;}
.irb-mig__pad{padding:16px;}
.irb-mig__modes{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;}
.irb-mig__mode{flex:1 1 220px;display:flex;gap:11px;align-items:flex-start;text-align:left;cursor:pointer;background:var(--surface-card);border:1px solid var(--border-default);border-radius:var(--radius-md);padding:13px 14px;font:inherit;color:inherit;transition:border-color .12s,background-color .12s;}
.irb-mig__mode:hover{background:var(--surface-hover);}
.irb-mig__mode--on{border-color:var(--accent);background:var(--accent-weak);}
.irb-mig__mode-ic{flex:none;display:inline-flex;color:var(--accent);}
.irb-mig__mode-name{font-size:13.5px;font-weight:600;color:var(--text-strong);margin-bottom:2px;}
.irb-mig__mode-desc{font-size:11.5px;color:var(--text-subtle);line-height:1.45;}
.irb-mig__form{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;}
.irb-mig__fld{display:flex;flex-direction:column;gap:5px;}
.irb-mig__fld-lab{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.irb-mig__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.irb-mig__in:focus{outline:none;border-color:var(--accent);}
.irb-mig__note{font-size:11.5px;color:var(--text-subtle);line-height:1.5;margin-top:12px;display:flex;gap:7px;align-items:flex-start;}
.irb-mig__actions{display:flex;gap:10px;align-items:center;justify-content:flex-end;flex-wrap:wrap;padding:14px 16px;border-top:1px solid var(--border-subtle);}
.irb-mig__tbl{width:100%;border-collapse:collapse;font-size:13px;}
.irb-mig__tbl th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);padding:10px 14px;border-bottom:1px solid var(--border-subtle);background:var(--surface-sunken);white-space:nowrap;}
.irb-mig__tbl td{padding:9px 14px;border-bottom:1px solid var(--border-subtle);vertical-align:middle;}
.irb-mig__tbl tr:last-child td{border-bottom:none;}
.irb-mig__mono{font-family:var(--font-mono);font-size:12px;}
.irb-mig__db{cursor:pointer;}
.irb-mig__db:hover td{background:var(--surface-hover);}
.irb-mig__caret{display:inline-flex;color:var(--text-subtle);transition:transform .12s;flex:none;}
.irb-mig__caret--open{transform:rotate(90deg);}
.irb-mig__kind{display:inline-block;font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);background:var(--surface-hover);color:var(--text-muted);}
.irb-mig__fields{background:var(--surface-sunken);}
.irb-mig__ftbl{width:100%;border-collapse:collapse;font-size:12px;}
.irb-mig__ftbl th{text-align:left;font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);padding:6px 12px;}
.irb-mig__ftbl td{padding:5px 12px;border-top:1px solid var(--border-subtle);vertical-align:top;}
.irb-mig__ftag{font-family:var(--font-mono);font-size:11.5px;font-weight:600;color:var(--text-muted);}
.irb-mig__sub{font-family:var(--font-mono);font-size:11px;color:var(--text-subtle);}
.irb-mig__custom{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:1px 7px;border-radius:var(--radius-full);background:var(--status-issued-bg,#FBEFD8);color:var(--status-issued,#B5710E);text-transform:uppercase;letter-spacing:.04em;}
.irb-mig__chk{display:flex;align-items:center;gap:10px;padding:11px 14px;border-bottom:1px solid var(--border-subtle);cursor:pointer;}
.irb-mig__chk:last-child{border-bottom:none;}
.irb-mig__chk:hover{background:var(--surface-hover);}
.irb-mig__chk input{width:16px;height:16px;accent-color:var(--accent);flex:none;cursor:pointer;}
.irb-mig__chk-main{min-width:0;flex:1;}
.irb-mig__chk-name{font-size:13px;font-weight:600;color:var(--text-strong);}
.irb-mig__chk-sub{font-size:11.5px;color:var(--text-subtle);}
.irb-mig__sw{position:relative;width:40px;height:22px;border-radius:var(--radius-full);border:none;cursor:pointer;background:var(--border-strong);transition:background-color .15s;flex:none;padding:0;}
.irb-mig__sw[aria-checked="true"]{background:var(--accent);}
.irb-mig__sw i{position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:var(--radius-full);background:#fff;transition:left .15s;box-shadow:var(--shadow-sm);}
.irb-mig__sw[aria-checked="true"] i{left:21px;}
.irb-mig__dry{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 14px;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface-sunken);margin-top:14px;}
.irb-mig__report{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;}
.irb-mig__metric{display:flex;flex-direction:column;gap:4px;padding:14px;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface-card);}
.irb-mig__metric-val{font-family:var(--font-display);font-size:24px;font-weight:700;letter-spacing:-.02em;color:var(--text-strong);}
.irb-mig__metric-val--bad{color:var(--danger-500);}
.irb-mig__metric-lab{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--text-muted);}
.irb-mig__banner{display:flex;gap:9px;align-items:flex-start;padding:12px 14px;border-radius:var(--radius-md);font-size:12.5px;line-height:1.5;margin-bottom:14px;}
.irb-mig__banner--dry{background:var(--info-bg,var(--accent-weak));color:var(--accent-press);}
.irb-mig__banner--done{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);}
@media (max-width:760px){.irb-mig__form{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-mig-css")) {
  const s = document.createElement("style"); s.id = "irb-mig-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Человекочитаемые подписи типов баз (kind). Неизвестный код показываем как есть.
const KIND_RU: Record<string, string> = {
  bibliographic: "Библиографическая",
  biblio: "Библиографическая",
  reader: "Читатели (RDR)",
  readers: "Читатели (RDR)",
  authority: "Авторитетная",
  thesaurus: "Тезаурус / рубрикатор",
};
const kindLabel = (k?: string) => (k ? KIND_RU[k] || k : "—");
const fmtNum = (n?: number) => (typeof n === "number" && Number.isFinite(n) ? n.toLocaleString("ru-RU") : "—");

type Step = 1 | 2 | 3 | 4;
const STEPS: { no: Step; label: string }[] = [
  { no: 1, label: "Источник" },
  { no: 2, label: "Изучение" },
  { no: 3, label: "Выбор" },
  { no: 4, label: "Запуск" },
];

// Информер «эндпойнт миграции не развёрнут» (мягкая деградация на 404/501).
function MigDown({ title }: { title: string }) {
  return (
    <div className="irb-mig__card" style={{ padding: 4 }}>
      <EmptyState icon="download" title={title}
        description="Мастер свёрстан в Стиле A и работает поверх движка миграции ИРБИС64 → Biblio (#225). На текущем сервере эндпойнт /api/admin/migrate/* ещё не развёрнут — перенос данных станет доступен после его публикации." />
    </div>
  );
}

export function MigrationWizard({ toast }: { toast: ToastFn }) {
  const [step, setStep] = React.useState<Step>(1);
  // Источник.
  const [mode, setMode] = React.useState<MigrateMode>("network");
  const [host, setHost] = React.useState("");
  const [port, setPort] = React.useState("6666");
  const [user, setUser] = React.useState("");
  const [pass, setPass] = React.useState("");
  const [workstation, setWorkstation] = React.useState("");
  const [path, setPath] = React.useState("");
  // Изучение.
  const [databases, setDatabases] = React.useState<MigrateDatabase[] | null>(null);
  const [inspecting, setInspecting] = React.useState(false);
  const [down, setDown] = React.useState(false);
  // Выбор.
  const [selected, setSelected] = React.useState<Record<string, boolean>>({});
  const [tenant, setTenant] = React.useState("");
  const [dryRun, setDryRun] = React.useState(true);
  // Запуск.
  const [running, setRunning] = React.useState(false);
  const [report, setReport] = React.useState<MigrateReport | null>(null);
  const [ranDry, setRanDry] = React.useState(false);

  // Собрать источник из формы (креды — транзитом, не сохраняем).
  function buildSource(): MigrateSource {
    return mode === "network"
      ? { host: host.trim(), port: Number(port) || 0, user: user.trim(), pass, workstation: workstation.trim() || undefined }
      : { path: path.trim() };
  }
  function sourceReady(): boolean {
    return mode === "network" ? !!host.trim() : !!path.trim();
  }

  const selectedCodes = (databases || []).filter((d) => selected[d.code]).map((d) => d.code);

  // --- Шаг 2: изучить источник --------------------------------------------
  async function inspect() {
    if (!sourceReady()) {
      toast({ variant: "info", title: "Укажите источник", message: mode === "network" ? "Заполните хост сервера ИРБИС64." : "Укажите путь к каталогу данных ИРБИС." });
      return;
    }
    setInspecting(true); setDown(false);
    const r = await api.migrateInspect(mode, buildSource());
    setInspecting(false);
    if (r.status === 404 || r.status === 501) { setDown(true); setStep(2); return; }
    if (r.status === 403) { toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." }); return; }
    if (r.json?.ok && r.json.data) {
      const dbs = r.json.data.databases || [];
      setDatabases(dbs);
      // По умолчанию отмечаем к миграции все обнаруженные базы.
      const sel: Record<string, boolean> = {};
      dbs.forEach((d) => { sel[d.code] = true; });
      setSelected(sel);
      setStep(2);
      toast({ variant: "success", title: "Источник изучен", message: "Обнаружено баз: " + dbs.length });
    } else {
      setDatabases([]); setStep(2);
      toast({ variant: "error", title: "Не удалось изучить источник", message: "Проверьте реквизиты подключения и повторите." });
    }
  }

  // --- Шаг 4: запустить миграцию ------------------------------------------
  async function run() {
    if (!selectedCodes.length) { toast({ variant: "info", title: "Выберите базы", message: "Отметьте хотя бы одну базу для миграции." }); return; }
    if (!tenant.trim()) { toast({ variant: "info", title: "Укажите арендатора", message: "Целевой арендатор обязателен." }); return; }
    setRunning(true); setReport(null);
    const isDry = dryRun;
    const r = await api.migrateRun({ mode, source: buildSource(), tenant: tenant.trim(), dbs: selectedCodes, dryRun: isDry });
    setRunning(false);
    if (r.status === 404 || r.status === 501) { setDown(true); setStep(4); return; }
    if (r.status === 403) { toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант admin.db." }); return; }
    if (r.json?.ok && r.json.data && r.json.data.report) {
      setReport(r.json.data.report); setRanDry(isDry); setStep(4);
      toast({ variant: "success", title: isDry ? "Пробный прогон завершён" : "Миграция завершена",
        message: isDry ? "Ничего не записано — это анализ." : "Записей загружено: " + fmtNum(r.json.data.report.records_loaded) });
    } else {
      toast({ variant: "error", title: "Миграция не выполнена", message: "Сервер не вернул отчёт. Повторите попытку." });
    }
  }

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Миграция</h2>
        <span className="stf__pill">ИРБИС64 → Biblio · мастер</span>
      </div>
    </div>
  );

  // Индикатор шагов (1 → 2 → 3 → 4). Вернуться к пройденному шагу можно кликом.
  const canGo = (n: Step): boolean =>
    n === 1 || (n === 2 && (databases !== null || down)) ||
    (n === 3 && databases !== null && databases.length > 0) ||
    (n === 4 && report !== null);
  const stepper = (
    <div className="irb-mig__steps" role="list" aria-label="Шаги мастера миграции">
      {STEPS.map((s, i) => {
        const state = s.no === step ? "on" : s.no < step ? "done" : "";
        const clickable = s.no !== step && canGo(s.no);
        return (
          <React.Fragment key={s.no}>
            {i > 0 && <span className="irb-mig__step-sep"><Icon name="chevron-right" size={14} /></span>}
            <button type="button" role="listitem"
              className={"irb-mig__step" + (state ? " irb-mig__step--" + state : "") + (clickable ? " irb-mig__step--clickable" : "")}
              aria-current={s.no === step ? "step" : undefined}
              disabled={!clickable && s.no !== step}
              onClick={() => clickable && setStep(s.no)}>
              <span className="irb-mig__step-no">{s.no < step ? <Icon name="check" size={13} /> : s.no}</span>
              <span className="irb-mig__step-lab">{s.label}</span>
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );

  return (
    <div className="irb-mig">
      {head}
      {stepper}
      {step === 1 && <SourceStep
        mode={mode} setMode={setMode}
        host={host} setHost={setHost} port={port} setPort={setPort}
        user={user} setUser={setUser} pass={pass} setPass={setPass}
        workstation={workstation} setWorkstation={setWorkstation}
        path={path} setPath={setPath}
        ready={sourceReady()} inspecting={inspecting} onInspect={inspect} />}
      {step === 2 && (down
        ? <MigDown title="Изучение источника подключается отдельно" />
        : <InspectStep databases={databases} inspecting={inspecting}
            onReinspect={inspect} onNext={() => setStep(3)} />)}
      {step === 3 && <SelectStep
        databases={databases || []} selected={selected} setSelected={setSelected}
        tenant={tenant} setTenant={setTenant} dryRun={dryRun} setDryRun={setDryRun}
        selectedCount={selectedCodes.length} running={running} onRun={run} onBack={() => setStep(2)} />}
      {step === 4 && (down
        ? <MigDown title="Запуск миграции подключается отдельно" />
        : <RunStep report={report} dry={ranDry} running={running}
            onRestart={() => { setReport(null); setStep(1); }} onBackToSelect={() => setStep(3)} />)}
    </div>
  );
}

// ===== Шаг 1: Источник =====================================================
function SourceStep(props: {
  mode: MigrateMode; setMode: (m: MigrateMode) => void;
  host: string; setHost: (v: string) => void; port: string; setPort: (v: string) => void;
  user: string; setUser: (v: string) => void; pass: string; setPass: (v: string) => void;
  workstation: string; setWorkstation: (v: string) => void;
  path: string; setPath: (v: string) => void;
  ready: boolean; inspecting: boolean; onInspect: () => void;
}) {
  const { mode, setMode } = props;
  const modes: { id: MigrateMode; name: string; desc: string; icon: IconName }[] = [
    { id: "network", name: "Сеть", desc: "Сервер ИРБИС64 по TCP: хост, порт, учётка, рабочая станция.", icon: "globe" },
    { id: "local", name: "Локальный путь", desc: "Каталог данных ИРБИС на этой машине, напр. C:\\IRBIS64\\Datai.", icon: "folder-tree" },
  ];
  return (
    <div className="irb-mig__card">
      <div className="irb-mig__bar"><span className="irb-mig__cap">Шаг 1 · Источник миграции</span></div>
      <div className="irb-mig__pad">
        <div className="irb-mig__modes" role="radiogroup" aria-label="Режим источника">
          {modes.map((m) => (
            <button key={m.id} type="button" role="radio" aria-checked={mode === m.id}
              className={"irb-mig__mode" + (mode === m.id ? " irb-mig__mode--on" : "")} onClick={() => setMode(m.id)}>
              <span className="irb-mig__mode-ic"><Icon name={m.icon} size={20} /></span>
              <span style={{ minWidth: 0 }}>
                <span className="irb-mig__mode-name" style={{ display: "block" }}>{m.name}</span>
                <span className="irb-mig__mode-desc" style={{ display: "block" }}>{m.desc}</span>
              </span>
            </button>
          ))}
        </div>

        {mode === "network" ? (
          <div className="irb-mig__form">
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Хост сервера ИРБИС64</label>
              <input className="irb-mig__in" value={props.host} onChange={(e) => props.setHost(e.target.value)} placeholder="127.0.0.1" autoComplete="off" /></div>
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Порт</label>
              <input className="irb-mig__in" value={props.port} onChange={(e) => props.setPort(e.target.value)} placeholder="6666" inputMode="numeric" autoComplete="off" /></div>
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Логин</label>
              <input className="irb-mig__in" value={props.user} onChange={(e) => props.setUser(e.target.value)} autoComplete="off" /></div>
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Пароль</label>
              <input className="irb-mig__in" type="password" value={props.pass} onChange={(e) => props.setPass(e.target.value)} autoComplete="new-password" /></div>
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Рабочая станция</label>
              <input className="irb-mig__in" value={props.workstation} onChange={(e) => props.setWorkstation(e.target.value)} placeholder="напр. C (каталогизатор)" autoComplete="off" /></div>
          </div>
        ) : (
          <div className="irb-mig__form" style={{ gridTemplateColumns: "1fr" }}>
            <div className="irb-mig__fld"><label className="irb-mig__fld-lab">Путь к каталогу данных ИРБИС</label>
              <input className="irb-mig__in" value={props.path} onChange={(e) => props.setPath(e.target.value)} placeholder="C:\\IRBIS64\\Datai" autoComplete="off" /></div>
          </div>
        )}

        <div className="irb-mig__note">
          <Icon name="shield" size={14} style={{ flex: "none", marginTop: 1, color: "var(--text-subtle)" }} />
          <span>Реквизиты подключения используются только для этого переноса: они не сохраняются в браузере и не записываются в журналы.</span>
        </div>
      </div>
      <div className="irb-mig__actions">
        <Button iconLeft="search" loading={props.inspecting} disabled={!props.ready} onClick={props.onInspect}>Изучить источник</Button>
      </div>
    </div>
  );
}

// ===== Шаг 2: Изучение =====================================================
function InspectStep({ databases, inspecting, onReinspect, onNext }: {
  databases: MigrateDatabase[] | null; inspecting: boolean; onReinspect: () => void; onNext: () => void;
}) {
  if (databases === null) {
    return (
      <div className="irb-mig__card" style={{ padding: 4 }}>
        <EmptyState icon="search" title={inspecting ? "Изучаем источник…" : "Источник ещё не изучен"}
          description="Нажмите «Изучить источник» на шаге 1 — мастер обнаружит базы данных, посчитает записи и разберёт состав полей." />
      </div>
    );
  }
  if (databases.length === 0) {
    return (
      <div className="irb-mig__card">
        <div className="irb-mig__bar">
          <span className="irb-mig__cap">Шаг 2 · Обнаруженные базы</span>
          <Button size="sm" variant="ghost" iconLeft="refresh-cw" loading={inspecting} onClick={onReinspect}>Изучить снова</Button>
        </div>
        <div style={{ padding: 4 }}>
          <EmptyState icon="archive" title="Базы не обнаружены" description="В указанном источнике не найдено баз данных ИРБИС. Проверьте путь / реквизиты подключения и повторите изучение." />
        </div>
      </div>
    );
  }
  const totalRecords = databases.reduce((s, d) => s + (d.recordCount || 0), 0);
  return (
    <div className="irb-mig__card">
      <div className="irb-mig__bar">
        <span className="irb-mig__cap">Шаг 2 · Обнаружено баз: {databases.length} · записей: {fmtNum(totalRecords)}</span>
        <Button size="sm" variant="ghost" iconLeft="refresh-cw" loading={inspecting} onClick={onReinspect}>Изучить снова</Button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="irb-mig__tbl">
          <thead><tr><th style={{ width: 28 }} aria-label="Раскрыть" /><th>Код</th><th>Название</th><th>Тип</th><th style={{ textAlign: "right" }}>Записей</th><th style={{ textAlign: "right" }}>Читателей</th><th style={{ textAlign: "right" }}>Полей</th></tr></thead>
          <tbody>
            {databases.map((db) => <DbRow key={db.code} db={db} />)}
          </tbody>
        </table>
      </div>
      <div className="irb-mig__actions">
        <Button iconLeft="chevron-right" onClick={onNext}>К выбору баз</Button>
      </div>
    </div>
  );
}

// Строка БД с раскрываемым списком полей (тег / метка / подполя / частота /
// пометка «допполе» для кастомных полей вне штатной схемы).
function DbRow({ db }: { db: MigrateDatabase }) {
  const [open, setOpen] = React.useState(false);
  const fields: MigrateField[] = db.fields || [];
  return (
    <>
      <tr className="irb-mig__db" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <td><span className={"irb-mig__caret" + (open ? " irb-mig__caret--open" : "")}><Icon name="chevron-right" size={15} /></span></td>
        <td className="irb-mig__mono">{db.code}</td>
        <td>{db.name || "—"}</td>
        <td><span className="irb-mig__kind">{kindLabel(db.kind)}</span></td>
        <td className="irb-mig__mono" style={{ textAlign: "right" }}>{fmtNum(db.recordCount)}</td>
        <td className="irb-mig__mono" style={{ textAlign: "right" }}>{fmtNum(db.readerCount)}</td>
        <td className="irb-mig__mono" style={{ textAlign: "right" }}>{fields.length}</td>
      </tr>
      {open && (
        <tr className="irb-mig__fields">
          <td colSpan={7} style={{ padding: "8px 14px 12px 40px" }}>
            {fields.length === 0 ? (
              <span style={{ fontSize: 12, color: "var(--text-subtle)" }}>Состав полей не определён.</span>
            ) : (
              <table className="irb-mig__ftbl">
                <thead><tr><th>Тег</th><th>Метка</th><th>Подполя</th><th style={{ textAlign: "right" }}>Частота</th></tr></thead>
                <tbody>
                  {fields.map((f) => (
                    <tr key={f.tag}>
                      <td className="irb-mig__ftag">
                        {f.tag}
                        {f.custom && <span className="irb-mig__custom" style={{ marginLeft: 7 }} title="Поле вне штатной схемы РУСМАРК"><Icon name="tag" size={10} />допполе</span>}
                      </td>
                      <td>{f.label || "—"}</td>
                      <td className="irb-mig__sub">{(f.subfields || []).length ? (f.subfields || []).map((s) => "^" + s).join(" ") : "—"}</td>
                      <td className="irb-mig__mono" style={{ textAlign: "right" }}>{fmtNum(f.freq)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

// ===== Шаг 3: Выбор ========================================================
function SelectStep({ databases, selected, setSelected, tenant, setTenant, dryRun, setDryRun, selectedCount, running, onRun, onBack }: {
  databases: MigrateDatabase[]; selected: Record<string, boolean>; setSelected: (s: Record<string, boolean>) => void;
  tenant: string; setTenant: (v: string) => void; dryRun: boolean; setDryRun: (v: boolean) => void;
  selectedCount: number; running: boolean; onRun: () => void; onBack: () => void;
}) {
  const toggle = (code: string) => setSelected({ ...selected, [code]: !selected[code] });
  return (
    <div className="irb-mig__card">
      <div className="irb-mig__bar">
        <span className="irb-mig__cap">Шаг 3 · Какие базы мигрировать · выбрано: {selectedCount} из {databases.length}</span>
      </div>
      <div>
        {databases.map((db) => (
          <label key={db.code} className="irb-mig__chk">
            <input type="checkbox" checked={!!selected[db.code]} onChange={() => toggle(db.code)} aria-label={"Мигрировать базу " + db.code} />
            <span className="irb-mig__chk-main">
              <span className="irb-mig__chk-name" style={{ display: "block" }}>{db.name || db.code} <span className="irb-mig__mono" style={{ color: "var(--text-subtle)", fontWeight: 400 }}>({db.code})</span></span>
              <span className="irb-mig__chk-sub" style={{ display: "block" }}>{kindLabel(db.kind)} · записей {fmtNum(db.recordCount)}{typeof db.readerCount === "number" ? " · читателей " + fmtNum(db.readerCount) : ""} · полей {(db.fields || []).length}</span>
            </span>
          </label>
        ))}
      </div>
      <div className="irb-mig__pad" style={{ paddingTop: 16, paddingBottom: 4 }}>
        <div className="irb-mig__fld" style={{ maxWidth: 360 }}>
          <label className="irb-mig__fld-lab">Целевой арендатор</label>
          <input className="irb-mig__in" value={tenant} onChange={(e) => setTenant(e.target.value)} placeholder="слаг арендатора, напр. spbtl" autoComplete="off" />
        </div>
        <div className="irb-mig__dry">
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>Пробный прогон (dry-run)</div>
            <div style={{ fontSize: 11.5, color: "var(--text-subtle)", lineHeight: 1.45 }}>Только анализ: записи читаются и проверяются, но ничего не записывается в арендатора.</div>
          </div>
          <button type="button" role="switch" aria-checked={dryRun} aria-label="Пробный прогон" className="irb-mig__sw" onClick={() => setDryRun(!dryRun)}><i /></button>
        </div>
      </div>
      <div className="irb-mig__actions">
        <Button variant="ghost" iconLeft="chevron-left" onClick={onBack}>Назад</Button>
        <Button iconLeft="download" loading={running} disabled={!selectedCount || !tenant.trim()} onClick={onRun}>
          {dryRun ? "Пробный прогон" : "Мигрировать"}
        </Button>
      </div>
    </div>
  );
}

// ===== Шаг 4: Запуск / Отчёт ===============================================
function RunStep({ report, dry, running, onRestart, onBackToSelect }: {
  report: MigrateReport | null; dry: boolean; running: boolean; onRestart: () => void; onBackToSelect: () => void;
}) {
  if (running && !report) {
    return (
      <div className="irb-mig__card" style={{ padding: 4 }}>
        <EmptyState icon="download" title="Миграция выполняется…" description="Идёт перенос выбранных баз. Это может занять время в зависимости от объёма данных." />
      </div>
    );
  }
  if (!report) {
    return (
      <div className="irb-mig__card" style={{ padding: 4 }}>
        <EmptyState icon="download" title="Отчёт появится после запуска" description="Вернитесь к шагу 3, выберите базы и запустите миграцию (или пробный прогон) — здесь покажется отчёт." />
        <div className="irb-mig__actions"><Button variant="ghost" iconLeft="chevron-left" onClick={onBackToSelect}>К выбору баз</Button></div>
      </div>
    );
  }
  const metrics: { lab: string; icon: IconName; val: number; bad?: boolean }[] = [
    { lab: "Прочитано записей", icon: "file-text", val: report.records_read },
    { lab: "Загружено записей", icon: "check-circle", val: report.records_loaded },
    { lab: "Загружено читателей", icon: "users", val: report.readers_loaded },
    { lab: "Пропущено", icon: "minus", val: report.skipped },
    { lab: "Ошибок", icon: "alert-triangle", val: report.errors, bad: report.errors > 0 },
  ];
  return (
    <div className="irb-mig__card">
      <div className="irb-mig__bar">
        <span className="irb-mig__cap">Шаг 4 · Отчёт о миграции</span>
      </div>
      <div className="irb-mig__pad">
        <div className={"irb-mig__banner " + (dry ? "irb-mig__banner--dry" : "irb-mig__banner--done")}>
          <Icon name={dry ? "info" : "check-circle"} size={16} style={{ flex: "none", marginTop: 1 }} />
          <span>{dry
            ? "Это пробный прогон (dry-run): данные проанализированы, но в арендатора ничего не записано. Снимите тумблер на шаге 3, чтобы выполнить реальную миграцию."
            : "Миграция завершена. Данные загружены в арендатора."}</span>
        </div>
        <div className="irb-mig__report">
          {metrics.map((m) => (
            <div className="irb-mig__metric" key={m.lab}>
              <span className={"irb-mig__metric-val" + (m.bad ? " irb-mig__metric-val--bad" : "")}>{fmtNum(m.val)}</span>
              <span className="irb-mig__metric-lab"><Icon name={m.icon} size={14} />{m.lab}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="irb-mig__actions">
        <Button variant="ghost" iconLeft="chevron-left" onClick={onBackToSelect}>К выбору баз</Button>
        <Button variant="secondary" iconLeft="rotate-ccw" onClick={onRestart}>Новая миграция</Button>
      </div>
    </div>
  );
}
