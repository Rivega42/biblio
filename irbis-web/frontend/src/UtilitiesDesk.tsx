// АРМ Утилиты (PR #319) — пакетные операции над массивом записей:
//   • Статистика — сводка по набору (количество, среднее число полей, доля с
//     экземплярами; разрезы по типу/году/языку; фонд: экземпляры/статусы/места);
//   • Экспорт — выгрузка в json/csv (для csv — список полей-спецификаций);
//   • Дубли по полю — группировка по значению тег-спеки (напр. 10^a);
//   • Валидация — проверка наличия обязательных тегов в каждой записи.
//
// Записи задаются JSON-массивом в форме:
//   {"mfn":1,"fields":[{"tag":"920","value":"PAZK"},
//                      {"tag":"101","subfields":[{"code":"a","value":"rus"}]}]}
// — то есть каждое поле это либо {tag,value} (скалярное), либо {tag,subfields}
// (с подполями code/value). JSON парсится через try/catch: на ошибке — toast
// «Неверный JSON» и стоп.
//
// Мягкая деградация: контракт бэкенда (/api/utils/*) может быть ещё не развёрнут —
// на 404/501 показываем информер во вкладке, деск не падает.
import React from "react";
import { api } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import type { ToastVariant } from "../components/feedback/Toast.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .utl__* — не пересекается с .adm__/.stf__/.cat__/.irb-*.
const CSS = `
.utl{font-family:var(--font-ui);}
.utl__tabs{display:flex;gap:4px;padding:4px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-bottom:16px;width:fit-content;flex-wrap:wrap;}
.utl__tab{display:inline-flex;align-items:center;gap:7px;border:none;cursor:pointer;font-family:var(--font-ui);font-size:13px;font-weight:500;padding:7px 14px;border-radius:var(--radius-sm);background:transparent;color:var(--text-muted);}
.utl__tab:hover{color:var(--text-body);}
.utl__tab--on{background:var(--surface-card);color:var(--text-strong);font-weight:600;box-shadow:var(--shadow-sm);}
.utl__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;}
.utl__bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border-subtle);flex-wrap:wrap;}
.utl__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.utl__body{padding:14px;display:flex;flex-direction:column;gap:12px;}
.utl__fld{display:flex;flex-direction:column;gap:5px;min-width:0;}
.utl__fld-lab{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.utl__hint{font-size:11.5px;color:var(--text-subtle);line-height:1.5;}
.utl__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.utl__in:focus{outline:none;border-color:var(--accent);}
.utl__ta{width:100%;box-sizing:border-box;min-height:148px;resize:vertical;padding:10px 12px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-mono);font-size:12.5px;line-height:1.55;}
.utl__ta:focus{outline:none;border-color:var(--accent);}
.utl__actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.utl__row{display:flex;gap:10px;flex-wrap:wrap;align-items:end;}
.utl__row .utl__fld{flex:1 1 160px;}
.utl__pre{margin:0;font-family:var(--font-mono);font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:12px 14px;max-height:420px;overflow:auto;color:var(--text-body);}
.utl__tbl{width:100%;border-collapse:collapse;font-size:13px;}
.utl__tbl th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);padding:9px 12px;border-bottom:1px solid var(--border-subtle);background:var(--surface-sunken);white-space:nowrap;}
.utl__tbl td{padding:9px 12px;border-bottom:1px solid var(--border-subtle);vertical-align:top;}
.utl__tbl tr:last-child td{border-bottom:none;}
.utl__mono{font-family:var(--font-mono);font-size:12px;}
.utl__chip{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);background:var(--surface-hover);color:var(--text-muted);margin:1px 3px 1px 0;font-family:var(--font-mono);}
.utl__stats{display:flex;gap:10px;flex-wrap:wrap;}
.utl__stat{flex:1 1 130px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:11px 14px;}
.utl__stat-val{font-family:var(--font-mono);font-weight:700;font-size:22px;line-height:1;color:var(--text-strong);}
.utl__stat-lab{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--text-subtle);margin-top:5px;}
.utl__sub{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);margin:6px 0 2px;}
.utl__grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
.utl__scroll{max-height:380px;overflow:auto;border:1px solid var(--border-subtle);border-radius:var(--radius-md);}
.utl__badge{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;padding:5px 12px;border-radius:var(--radius-full);}
.utl__badge--ok{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);}
.utl__badge--bad{background:var(--danger-50,#FBE9E7);color:var(--danger-500,#C0392B);}
@media (max-width:760px){.utl__row{flex-direction:column;align-items:stretch;}}
`;
if (typeof document !== "undefined" && !document.getElementById("utl-css")) {
  const s = document.createElement("style"); s.id = "utl-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Образец массива записей (shape с fields[]/subfields[]) — подсказка и значение
// по умолчанию.
const SAMPLE_RECORDS =
  '[{"mfn":1,"fields":[{"tag":"920","value":"PAZK"},{"tag":"101","subfields":[{"code":"a","value":"rus"}]}]}]';

// Разбор JSON-массива записей с мягкой обработкой ошибки (toast + стоп).
function parseRecords(text: string, toast: ToastFn): unknown[] | null {
  try {
    const v = JSON.parse(text);
    if (!Array.isArray(v)) {
      toast({ variant: "error", title: "Неверный JSON", message: "Ожидается массив записей." });
      return null;
    }
    return v as unknown[];
  } catch (e: any) {
    toast({ variant: "error", title: "Неверный JSON", message: e?.message || "Не удалось разобрать JSON." });
    return null;
  }
}

// Подсказка под textarea про формат записей.
function RecordsHint() {
  return (
    <span className="utl__hint">
      Каждая запись — <code>{'{"mfn":N,"fields":[…]}'}</code>; поле это либо
      <code> {'{"tag":"920","value":"PAZK"}'}</code> (скалярное), либо
      <code> {'{"tag":"101","subfields":[{"code":"a","value":"rus"}]}'}</code> (с подполями).
    </span>
  );
}

// Информер «эндпойнт утилиты не развёрнут» (404/501).
function ToolDown({ icon, title }: { icon: IconName; title: string }) {
  return (
    <div className="utl__card" style={{ padding: 4 }}>
      <EmptyState icon={icon} title={title}
        description="Раздел свёрстан в дизайн-системе Biblio и работает поверх служебных утилит. На текущем сервере соответствующий эндпойнт /api/utils/* ещё не развёрнут — раздел активируется после его публикации. Остальные утилиты продолжают работать." />
    </div>
  );
}

// Таблица «ключ → значение» для разрезов статистики (by_type/by_year/…).
function KvTable({ title, map }: { title: string; map: Record<string, unknown> }) {
  const keys = Object.keys(map || {});
  if (!keys.length) return null;
  return (
    <div>
      <div className="utl__sub">{title}</div>
      <div className="utl__scroll">
        <table className="utl__tbl">
          <tbody>
            {keys.map((k) => (
              <tr key={k}><td className="utl__mono">{k}</td><td className="utl__mono" style={{ textAlign: "right" }}>{String((map as any)[k])}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

type Tab = "stats" | "export" | "duplicates" | "validate";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "stats", label: "Статистика", icon: "bar-chart" },
  { id: "export", label: "Экспорт", icon: "download" },
  { id: "duplicates", label: "Дубли по полю", icon: "copy" },
  { id: "validate", label: "Валидация", icon: "clipboard-check" },
];

export function UtilitiesDesk({ toast }: { toast: ToastFn }) {
  const [tab, setTab] = React.useState<Tab>("stats");
  return (
    <div className="utl">
      <div className="stf__pagehead">
        <div className="stf__h1">
          <h2>Утилиты</h2>
          <span className="stf__pill">статистика · экспорт · дубли · валидация</span>
        </div>
      </div>
      <div className="utl__tabs" role="tablist" aria-label="Служебные утилиты">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
            className={"utl__tab" + (tab === t.id ? " utl__tab--on" : "")} onClick={() => setTab(t.id)}>
            <Icon name={t.icon} size={15} />{t.label}
          </button>
        ))}
      </div>
      {tab === "stats" ? <StatsTab toast={toast} />
        : tab === "export" ? <ExportTab toast={toast} />
        : tab === "duplicates" ? <DuplicatesTab toast={toast} />
        : <ValidateTab toast={toast} />}
    </div>
  );
}

// ===== Статистика ===========================================================
function StatsTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [stats, setStats] = React.useState<Record<string, unknown> | null>(null);
  const [fund, setFund] = React.useState<Record<string, unknown> | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    setBusy(true); const r = await api.utilsStats(recs); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setStats(r.json.data.stats || {}); setFund(r.json.data.fund || {}); }
    else toast({ variant: "error", title: "Статистика не рассчитана", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="bar-chart" title="Статистика подключается отдельно" />;

  const num = (v: unknown) => (v == null ? "—" : String(v));
  return (
    <div className="utl__card">
      <div className="utl__bar"><span className="utl__cap">Статистика по набору записей</span></div>
      <div className="utl__body">
        <div className="utl__fld">
          <label className="utl__fld-lab">Записи (JSON-массив)</label>
          <textarea className="utl__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
          <RecordsHint />
        </div>
        <div className="utl__actions"><Button iconLeft="bar-chart" loading={busy} onClick={run}>Посчитать</Button></div>
        {stats && (
          <>
            <div className="utl__stats">
              <div className="utl__stat"><div className="utl__stat-val">{num((stats as any).count)}</div><div className="utl__stat-lab">Записей</div></div>
              <div className="utl__stat"><div className="utl__stat-val">{num((stats as any).avg_fields)}</div><div className="utl__stat-lab">Полей в среднем</div></div>
              <div className="utl__stat"><div className="utl__stat-val">{num((stats as any).with_exemplars)}</div><div className="utl__stat-lab">С экземплярами</div></div>
            </div>
            <div className="utl__grid2">
              <KvTable title="По типу" map={((stats as any).by_type as Record<string, unknown>) || {}} />
              <KvTable title="По году" map={((stats as any).by_year as Record<string, unknown>) || {}} />
              <KvTable title="По языку" map={((stats as any).by_language as Record<string, unknown>) || {}} />
            </div>
          </>
        )}
        {fund && (
          <>
            <div className="utl__sub">Фонд</div>
            <div className="utl__stats">
              <div className="utl__stat"><div className="utl__stat-val">{num((fund as any).total_exemplars)}</div><div className="utl__stat-lab">Экземпляров всего</div></div>
            </div>
            <div className="utl__grid2">
              <KvTable title="По статусу" map={((fund as any).by_status as Record<string, unknown>) || {}} />
              <KvTable title="По месту хранения" map={((fund as any).by_location as Record<string, unknown>) || {}} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ===== Экспорт ==============================================================
const EXPORT_FORMATS: { id: string; label: string }[] = [
  { id: "json", label: "JSON" },
  { id: "csv", label: "CSV" },
];

function ExportTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [format, setFormat] = React.useState("json");
  const [fieldsSpec, setFieldsSpec] = React.useState("200^a,920");
  const [data, setData] = React.useState<string | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    const fields = format === "csv"
      ? fieldsSpec.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    setBusy(true); const r = await api.utilsExport(recs, format, fields); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setData(r.json.data.data); }
    else toast({ variant: "error", title: "Экспорт не выполнен", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="download" title="Экспорт подключается отдельно" />;

  return (
    <div className="utl__card">
      <div className="utl__bar"><span className="utl__cap">Экспорт набора записей</span></div>
      <div className="utl__body">
        <div className="utl__fld">
          <label className="utl__fld-lab">Записи (JSON-массив)</label>
          <textarea className="utl__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
          <RecordsHint />
        </div>
        <div className="utl__row">
          <div className="utl__fld" style={{ flex: "0 0 160px" }}>
            <label className="utl__fld-lab">Формат</label>
            <select className="utl__in" value={format} onChange={(e) => setFormat(e.target.value)}>
              {EXPORT_FORMATS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
            </select>
          </div>
          {format === "csv" && (
            <div className="utl__fld">
              <label className="utl__fld-lab">Поля через запятую</label>
              <input className="utl__in" value={fieldsSpec} onChange={(e) => setFieldsSpec(e.target.value)} placeholder="напр. 200^a,920" autoComplete="off" />
            </div>
          )}
          <Button iconLeft="download" loading={busy} onClick={run}>Экспортировать</Button>
        </div>
        {data != null && <pre className="utl__pre">{data}</pre>}
      </div>
    </div>
  );
}

// ===== Дубли по полю ========================================================
function DuplicatesTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [tag, setTag] = React.useState("10^a");
  const [duplicates, setDuplicates] = React.useState<Record<string, number[]> | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    if (!tag.trim()) { toast({ variant: "info", title: "Укажите тег-спеку", message: "Например 10^a." }); return; }
    setBusy(true); const r = await api.utilsDuplicates(recs, tag.trim()); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setDuplicates(r.json.data.duplicates || {}); }
    else toast({ variant: "error", title: "Поиск не выполнен", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="copy" title="Поиск дублей по полю подключается отдельно" />;

  const keys = duplicates ? Object.keys(duplicates) : [];
  return (
    <div className="utl__card">
      <div className="utl__bar"><span className="utl__cap">Дубли по значению поля {duplicates ? "· групп " + keys.length : ""}</span></div>
      <div className="utl__body">
        <div className="utl__fld">
          <label className="utl__fld-lab">Записи (JSON-массив)</label>
          <textarea className="utl__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
          <RecordsHint />
        </div>
        <div className="utl__row">
          <div className="utl__fld" style={{ flex: "0 0 200px" }}>
            <label className="utl__fld-lab">Тег-спека</label>
            <input className="utl__in" value={tag} onChange={(e) => setTag(e.target.value)} placeholder="напр. 10^a" autoComplete="off" />
          </div>
          <Button iconLeft="copy" loading={busy} onClick={run}>Найти</Button>
        </div>
        {duplicates && (keys.length ? (
          <div className="utl__scroll">
            <table className="utl__tbl">
              <thead><tr><th>Значение</th><th>MFN записей</th></tr></thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k}>
                    <td className="utl__mono">{k}</td>
                    <td>{(duplicates[k] || []).map((m, j) => <span key={j} className="utl__chip">{m}</span>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="utl__hint">Дубли по заданному полю не обнаружены.</div>)}
      </div>
    </div>
  );
}

// ===== Валидация ============================================================
function ValidateTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [requiredSpec, setRequiredSpec] = React.useState("200,920");
  const [result, setResult] = React.useState<{ invalid: Array<{ mfn: number; missing: string[] }>; ok: boolean } | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    const required = requiredSpec.split(",").map((s) => s.trim()).filter(Boolean);
    if (!required.length) { toast({ variant: "info", title: "Укажите обязательные теги", message: "Например 200,920." }); return; }
    setBusy(true); const r = await api.utilsValidate(recs, required); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setResult({ invalid: r.json.data.invalid || [], ok: !!r.json.data.ok }); }
    else toast({ variant: "error", title: "Проверка не выполнена", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="clipboard-check" title="Валидация подключается отдельно" />;

  return (
    <div className="utl__card">
      <div className="utl__bar"><span className="utl__cap">Пакетная валидация записей</span></div>
      <div className="utl__body">
        <div className="utl__fld">
          <label className="utl__fld-lab">Записи (JSON-массив)</label>
          <textarea className="utl__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
          <RecordsHint />
        </div>
        <div className="utl__row">
          <div className="utl__fld">
            <label className="utl__fld-lab">Обязательные теги через запятую</label>
            <input className="utl__in" value={requiredSpec} onChange={(e) => setRequiredSpec(e.target.value)} placeholder="напр. 200,920" autoComplete="off" />
          </div>
          <Button iconLeft="clipboard-check" loading={busy} onClick={run}>Проверить</Button>
        </div>
        {result && (
          <>
            <div>
              <span className={"utl__badge " + (result.ok ? "utl__badge--ok" : "utl__badge--bad")}>
                <Icon name={result.ok ? "check-circle" : "alert-triangle"} size={14} />
                {result.ok ? "Все записи валидны" : "Есть невалидные записи · " + result.invalid.length}
              </span>
            </div>
            {!result.ok && result.invalid.length > 0 && (
              <div className="utl__scroll">
                <table className="utl__tbl">
                  <thead><tr><th>MFN</th><th>Отсутствующие теги</th></tr></thead>
                  <tbody>
                    {result.invalid.map((row, i) => (
                      <tr key={i}>
                        <td className="utl__mono">{row.mfn}</td>
                        <td>{(row.missing || []).map((m, j) => <span key={j} className="utl__chip">{m}</span>)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
