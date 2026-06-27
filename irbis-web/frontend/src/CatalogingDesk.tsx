// АРМ Каталогизатор · ИНСТРУМЕНТЫ (PR #319) — отдельный деск от рабочего листа
// CatalogingWorksheet (который правит конкретную запись). Здесь — служебные
// инструменты каталогизатора над ПРОИЗВОЛЬНЫМ массивом записей:
//   • Обмен MARC — экспорт записей в ISO2709 (base64) / MARCXML и импорт MARCXML;
//   • Дубли — поиск дублей (кластеры key/members + сводка stats);
//   • Печать ГОСТ — формирование печатной формы (card/list/index);
//   • Словари — просмотр и пополнение словарей значений;
//   • Версии — история версий записи (db+mfn).
//
// Записи задаются JSON-массивом в tag-keyed форме, напр.:
//   [{"920":"PAZK","200":[{"a":"Заглавие"}],"101":"rus"}]
// JSON парсится через try/catch: на ошибке — toast «Неверный JSON» и стоп.
//
// Мягкая деградация: контракт бэкенда (/api/cataloging/*) может быть ещё не
// развёрнут — на 404/501 показываем информер во вкладке, деск не падает.
import React from "react";
import { api } from "./api";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import type { IconName } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";
import type { ToastVariant } from "../components/feedback/Toast.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .cat__* — не пересекается с .adm__/.stf__/.utl__/.irb-*.
const CSS = `
.cat{font-family:var(--font-ui);}
.cat__tabs{display:flex;gap:4px;padding:4px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);margin-bottom:16px;width:fit-content;flex-wrap:wrap;}
.cat__tab{display:inline-flex;align-items:center;gap:7px;border:none;cursor:pointer;font-family:var(--font-ui);font-size:13px;font-weight:500;padding:7px 14px;border-radius:var(--radius-sm);background:transparent;color:var(--text-muted);}
.cat__tab:hover{color:var(--text-body);}
.cat__tab--on{background:var(--surface-card);color:var(--text-strong);font-weight:600;box-shadow:var(--shadow-sm);}
.cat__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);overflow:hidden;}
.cat__bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border-subtle);flex-wrap:wrap;}
.cat__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);}
.cat__body{padding:14px;display:flex;flex-direction:column;gap:12px;}
.cat__fld{display:flex;flex-direction:column;gap:5px;min-width:0;}
.cat__fld-lab{font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.cat__hint{font-size:11.5px;color:var(--text-subtle);line-height:1.5;}
.cat__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-ui);font-size:13px;}
.cat__in:focus{outline:none;border-color:var(--accent);}
.cat__ta{width:100%;box-sizing:border-box;min-height:148px;resize:vertical;padding:10px 12px;border-radius:var(--radius-md);border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);font-family:var(--font-mono);font-size:12.5px;line-height:1.55;}
.cat__ta:focus{outline:none;border-color:var(--accent);}
.cat__actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.cat__row{display:flex;gap:10px;flex-wrap:wrap;align-items:end;}
.cat__row .cat__fld{flex:1 1 160px;}
.cat__pre{margin:0;font-family:var(--font-mono);font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:12px 14px;max-height:420px;overflow:auto;color:var(--text-body);}
.cat__tbl{width:100%;border-collapse:collapse;font-size:13px;}
.cat__tbl th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);padding:9px 12px;border-bottom:1px solid var(--border-subtle);background:var(--surface-sunken);white-space:nowrap;}
.cat__tbl td{padding:9px 12px;border-bottom:1px solid var(--border-subtle);vertical-align:top;}
.cat__tbl tr:last-child td{border-bottom:none;}
.cat__mono{font-family:var(--font-mono);font-size:12px;}
.cat__chip{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:var(--radius-full);background:var(--surface-hover);color:var(--text-muted);margin:1px 3px 1px 0;font-family:var(--font-mono);}
.cat__stats{display:flex;gap:10px;flex-wrap:wrap;}
.cat__stat{flex:1 1 130px;background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:11px 14px;}
.cat__stat-val{font-family:var(--font-mono);font-weight:700;font-size:22px;line-height:1;color:var(--text-strong);}
.cat__stat-lab{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--text-subtle);margin-top:5px;}
.cat__scroll{max-height:420px;overflow:auto;}
@media (max-width:760px){.cat__row{flex-direction:column;align-items:stretch;}}
`;
if (typeof document !== "undefined" && !document.getElementById("cat-css")) {
  const s = document.createElement("style"); s.id = "cat-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Образец массива записей (tag-keyed) для подсказки и значения по умолчанию.
const SAMPLE_RECORDS = '[{"920":"PAZK","200":[{"a":"Заглавие"}],"101":"rus"}]';

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

// Информер «эндпойнт инструмента не развёрнут» (404/501).
function ToolDown({ icon, title }: { icon: IconName; title: string }) {
  return (
    <div className="cat__card" style={{ padding: 4 }}>
      <EmptyState icon={icon} title={title}
        description="Раздел свёрстан в дизайн-системе Biblio и работает поверх инструментов каталогизатора. На текущем сервере соответствующий эндпойнт /api/cataloging/* ещё не развёрнут — раздел активируется после его публикации. Остальные инструменты продолжают работать." />
    </div>
  );
}

type Tab = "marc" | "dedup" | "print" | "vocab" | "versions";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "marc", label: "Обмен MARC", icon: "download" },
  { id: "dedup", label: "Дубли", icon: "copy" },
  { id: "print", label: "Печать ГОСТ", icon: "file-text" },
  { id: "vocab", label: "Словари", icon: "list" },
  { id: "versions", label: "Версии", icon: "clock" },
];

export function CatalogingDesk({ toast }: { toast: ToastFn }) {
  const [tab, setTab] = React.useState<Tab>("marc");
  return (
    <div className="cat">
      <div className="stf__pagehead">
        <div className="stf__h1">
          <h2>Каталогизатор · инструменты</h2>
          <span className="stf__pill">MARC · дубли · печать · словари · версии</span>
        </div>
      </div>
      <div className="cat__tabs" role="tablist" aria-label="Инструменты каталогизатора">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
            className={"cat__tab" + (tab === t.id ? " cat__tab--on" : "")} onClick={() => setTab(t.id)}>
            <Icon name={t.icon} size={15} />{t.label}
          </button>
        ))}
      </div>
      {tab === "marc" ? <MarcTab toast={toast} />
        : tab === "dedup" ? <DedupTab toast={toast} />
        : tab === "print" ? <PrintTab toast={toast} />
        : tab === "vocab" ? <VocabTab toast={toast} />
        : <VersionsTab />}
    </div>
  );
}

// ===== Обмен MARC ===========================================================
function MarcTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [marcxmlIn, setMarcxmlIn] = React.useState("");
  const [iso, setIso] = React.useState<{ b64: string; count: number } | null>(null);
  const [xmlOut, setXmlOut] = React.useState<string | null>(null);
  const [imported, setImported] = React.useState<{ records: unknown[]; count: number } | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState<"iso" | "xml" | "imp" | null>(null);

  async function exportIso() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    setBusy("iso"); const r = await api.marcExport(recs); setBusy(null);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setIso({ b64: r.json.data.iso2709_b64, count: r.json.data.count }); }
    else toast({ variant: "error", title: "Экспорт не выполнен", message: "Повторите попытку." });
  }
  async function exportXml() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    setBusy("xml"); const r = await api.marcxmlExport(recs); setBusy(null);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setXmlOut(r.json.data.marcxml); }
    else toast({ variant: "error", title: "Экспорт не выполнен", message: "Повторите попытку." });
  }
  async function importXml() {
    if (!marcxmlIn.trim()) { toast({ variant: "info", title: "Пустой MARCXML", message: "Вставьте XML для импорта." }); return; }
    setBusy("imp"); const r = await api.marcxmlImport(marcxmlIn); setBusy(null);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setImported({ records: r.json.data.records, count: r.json.data.count }); toast({ variant: "success", title: "Импорт выполнен", message: r.json.data.count + " запис(ей)" }); }
    else toast({ variant: "error", title: "Импорт не выполнен", message: "Проверьте корректность MARCXML." });
  }

  if (down) return <ToolDown icon="download" title="Обмен MARC подключается отдельно" />;

  return (
    <div className="cat__card">
      <div className="cat__bar"><span className="cat__cap">Экспорт записей в форматы обмена</span></div>
      <div className="cat__body">
        <div className="cat__fld">
          <label className="cat__fld-lab">Записи (JSON-массив, tag-keyed)</label>
          <textarea className="cat__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
          <span className="cat__hint">Например: <code>{SAMPLE_RECORDS}</code> — ключи это теги полей; значение поля — строка либо массив объектов «подполе→значение».</span>
        </div>
        <div className="cat__actions">
          <Button iconLeft="download" loading={busy === "iso"} onClick={exportIso}>Экспорт ISO2709</Button>
          <Button iconLeft="download" variant="secondary" loading={busy === "xml"} onClick={exportXml}>Экспорт MARCXML</Button>
        </div>
        {iso && (
          <div className="cat__fld">
            <label className="cat__fld-lab">ISO2709 · base64 · записей: {iso.count}</label>
            <pre className="cat__pre">{iso.b64}</pre>
          </div>
        )}
        {xmlOut != null && (
          <div className="cat__fld">
            <label className="cat__fld-lab">MARCXML</label>
            <pre className="cat__pre">{xmlOut}</pre>
          </div>
        )}
        <div className="cat__fld" style={{ marginTop: 6, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
          <label className="cat__fld-lab">Импорт MARCXML → записи</label>
          <textarea className="cat__ta" value={marcxmlIn} onChange={(e) => setMarcxmlIn(e.target.value)} spellCheck={false}
            placeholder="<record>…</record> или <collection>…</collection>" />
        </div>
        <div className="cat__actions">
          <Button iconLeft="check" loading={busy === "imp"} onClick={importXml}>Импорт MARCXML</Button>
        </div>
        {imported && (
          <div className="cat__fld">
            <label className="cat__fld-lab">Импортировано записей: {imported.count}</label>
            <pre className="cat__pre">{JSON.stringify(imported.records, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

// ===== Дубли ================================================================
function DedupTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [clusters, setClusters] = React.useState<{ key: string; members: number[] }[] | null>(null);
  const [stats, setStats] = React.useState<Record<string, unknown> | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    setBusy(true); const r = await api.dedupScan(recs); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setClusters(r.json.data.clusters || []); setStats(r.json.data.stats || {}); }
    else toast({ variant: "error", title: "Поиск дублей не выполнен", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="copy" title="Поиск дублей подключается отдельно" />;

  return (
    <div className="cat__card">
      <div className="cat__bar"><span className="cat__cap">Поиск дублей в наборе записей</span></div>
      <div className="cat__body">
        <div className="cat__fld">
          <label className="cat__fld-lab">Записи (JSON-массив)</label>
          <textarea className="cat__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
        </div>
        <div className="cat__actions"><Button iconLeft="copy" loading={busy} onClick={run}>Найти дубли</Button></div>
        {stats && (
          <div className="cat__stats">
            {Object.keys(stats).map((k) => (
              <div className="cat__stat" key={k}><div className="cat__stat-val">{String((stats as any)[k])}</div><div className="cat__stat-lab">{k}</div></div>
            ))}
          </div>
        )}
        {clusters && (clusters.length ? (
          <div className="cat__scroll">
            <table className="cat__tbl">
              <thead><tr><th>Ключ кластера</th><th>Записи (members)</th></tr></thead>
              <tbody>
                {clusters.map((c, i) => (
                  <tr key={i}>
                    <td className="cat__mono">{c.key}</td>
                    <td>{(c.members || []).map((m, j) => <span key={j} className="cat__chip">{m}</span>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="cat__hint">Дубли не обнаружены.</div>)}
      </div>
    </div>
  );
}

// ===== Печать ГОСТ ==========================================================
const PRINT_FORMS: { id: string; label: string }[] = [
  { id: "card", label: "Каталожная карточка" },
  { id: "list", label: "Список" },
  { id: "index", label: "Указатель" },
];

function PrintTab({ toast }: { toast: ToastFn }) {
  const [recordsJson, setRecordsJson] = React.useState(SAMPLE_RECORDS);
  const [form, setForm] = React.useState("card");
  const [text, setText] = React.useState<string | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const recs = parseRecords(recordsJson, toast); if (!recs) return;
    setBusy(true); const r = await api.catalogPrint(recs, form); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setText(r.json.data.text); }
    else toast({ variant: "error", title: "Печать не сформирована", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="file-text" title="Печать по ГОСТ подключается отдельно" />;

  return (
    <div className="cat__card">
      <div className="cat__bar"><span className="cat__cap">Печатная форма по ГОСТ</span></div>
      <div className="cat__body">
        <div className="cat__fld">
          <label className="cat__fld-lab">Записи (JSON-массив)</label>
          <textarea className="cat__ta" value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} spellCheck={false} />
        </div>
        <div className="cat__row">
          <div className="cat__fld" style={{ flex: "0 0 220px" }}>
            <label className="cat__fld-lab">Форма</label>
            <select className="cat__in" value={form} onChange={(e) => setForm(e.target.value)}>
              {PRINT_FORMS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
            </select>
          </div>
          <Button iconLeft="file-text" loading={busy} onClick={run}>Сформировать</Button>
        </div>
        {text != null && <pre className="cat__pre">{text}</pre>}
      </div>
    </div>
  );
}

// ===== Словари ==============================================================
function VocabTab({ toast }: { toast: ToastFn }) {
  const [vocab, setVocab] = React.useState("");
  const [items, setItems] = React.useState<Array<Record<string, unknown>> | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [adding, setAdding] = React.useState(false);
  const [code, setCode] = React.useState("");
  const [label, setLabel] = React.useState("");

  async function load() {
    const v = vocab.trim();
    if (!v) { toast({ variant: "info", title: "Укажите словарь", message: "Введите идентификатор словаря." }); return; }
    setBusy(true); const r = await api.vocabValues(v); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setItems(r.json.data.items || []); }
    else setItems([]);
  }
  async function add() {
    const v = vocab.trim();
    if (!v || !code.trim() || !label.trim()) { toast({ variant: "info", title: "Заполните значение", message: "Словарь, код и подпись обязательны." }); return; }
    setAdding(true); const r = await api.vocabAddValue(v, code.trim(), label.trim()); setAdding(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok) { toast({ variant: "success", title: "Значение добавлено", message: code.trim() + " · " + label.trim() }); setCode(""); setLabel(""); void load(); }
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }

  if (down) return <ToolDown icon="list" title="Словари подключаются отдельно" />;

  const cols = items && items.length ? Object.keys(items[0]) : [];
  return (
    <div className="cat__card">
      <div className="cat__bar"><span className="cat__cap">Словари значений {items ? "· " + items.length : ""}</span></div>
      <div className="cat__body">
        <div className="cat__row">
          <div className="cat__fld"><label className="cat__fld-lab">Словарь (vocab)</label>
            <input className="cat__in" value={vocab} onChange={(e) => setVocab(e.target.value)} placeholder="напр. T-status" autoComplete="off" /></div>
          <Button iconLeft="refresh-cw" loading={busy} onClick={load}>Загрузить</Button>
        </div>
        {items && (items.length ? (
          <div className="cat__scroll">
            <table className="cat__tbl">
              <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {items.map((row, i) => (
                  <tr key={i}>{cols.map((c) => <td key={c} className="cat__mono">{String(row[c] ?? "—")}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="cat__hint">Значения словаря отсутствуют.</div>)}

        <div className="cat__fld" style={{ paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
          <span className="cat__fld-lab">Добавить значение</span>
          <div className="cat__row" style={{ marginTop: 6 }}>
            <div className="cat__fld"><label className="cat__fld-lab">Код</label>
              <input className="cat__in" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" /></div>
            <div className="cat__fld"><label className="cat__fld-lab">Подпись</label>
              <input className="cat__in" value={label} onChange={(e) => setLabel(e.target.value)} autoComplete="off" /></div>
            <Button iconLeft="plus" loading={adding} onClick={add}>Добавить</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ===== Версии ===============================================================
function VersionsTab() {
  const [db, setDb] = React.useState("IBIS");
  const [mfn, setMfn] = React.useState("");
  const [rows, setRows] = React.useState<Array<{ version: number; actor?: string; created_at?: string }> | null>(null);
  const [down, setDown] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    const n = parseInt(mfn, 10);
    if (!db.trim() || !isFinite(n)) return;
    setBusy(true); const r = await api.recVersions(db.trim(), n); setBusy(false);
    if (r.status === 404 || r.status === 501) { setDown(true); return; }
    if (r.json?.ok && r.json.data) { setRows(r.json.data.items || []); }
    else setRows([]);
  }

  if (down) return <ToolDown icon="clock" title="История версий подключается отдельно" />;

  return (
    <div className="cat__card">
      <div className="cat__bar"><span className="cat__cap">История версий записи {rows ? "· " + rows.length : ""}</span></div>
      <div className="cat__body">
        <div className="cat__row">
          <div className="cat__fld" style={{ flex: "0 0 180px" }}><label className="cat__fld-lab">База</label>
            <input className="cat__in" value={db} onChange={(e) => setDb(e.target.value)} autoComplete="off" /></div>
          <div className="cat__fld" style={{ flex: "0 0 160px" }}><label className="cat__fld-lab">MFN</label>
            <input className="cat__in" value={mfn} onChange={(e) => setMfn(e.target.value)} inputMode="numeric" autoComplete="off" /></div>
          <Button iconLeft="clock" loading={busy} onClick={run}>История</Button>
        </div>
        {rows && (rows.length ? (
          <div className="cat__scroll">
            <table className="cat__tbl">
              <thead><tr><th>Версия</th><th>Актор</th><th>Создана</th></tr></thead>
              <tbody>
                {rows.map((v, i) => (
                  <tr key={i}>
                    <td className="cat__mono">{v.version}</td>
                    <td className="cat__mono">{v.actor || "—"}</td>
                    <td className="cat__mono">{v.created_at || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="cat__hint">Версии не найдены.</div>)}
      </div>
    </div>
  );
}
