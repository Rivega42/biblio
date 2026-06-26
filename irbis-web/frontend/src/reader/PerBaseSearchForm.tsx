// Расширенный поиск под конкретную базу (#255 п.4) — реплика форм боевого jirbis.
// Рендерит набор полей из baseSearchForms по выбранной базе, собирает выражение
// ИРБИС и отдаёт его наверх (onSearch). Поля: текст / диапазон года / список с
// автоподсказками из словаря / чекбокс эл.копии (пока помечен «скоро»).
import React from "react";
import { api } from "../api";
import { Button } from "../../components/forms/Button.jsx";
import type { BaseFormDef, SearchFieldDef } from "./baseSearchForms";

const CSS = `
.irb-pbf{background:var(--surface-card,#fff);border:1px solid var(--border-subtle);border-radius:var(--radius-xl,14px);
  padding:16px 18px;margin-bottom:14px;box-shadow:var(--shadow-sm);}
.irb-pbf__head{display:flex;align-items:baseline;gap:8px;margin:0 0 14px;flex-wrap:wrap;}
.irb-pbf__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-base,1rem);color:var(--text-strong);margin:0;}
.irb-pbf__sub{font-size:var(--text-xs);color:var(--text-subtle);}
.irb-pbf__grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px 16px;}
.irb-pbf__field{display:flex;flex-direction:column;gap:5px;min-width:0;}
.irb-pbf__label{font-size:var(--text-xs);font-weight:var(--weight-semibold,600);color:var(--text-body);}
.irb-pbf__in{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md,8px);
  border:1px solid var(--border-strong,#cdd3da);background:var(--surface-card,#fff);color:var(--text-body);
  font-family:var(--font-ui,inherit);font-size:var(--text-sm);}
.irb-pbf__in:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent);}
.irb-pbf__year{display:flex;align-items:center;gap:8px;}
.irb-pbf__year span{font-size:var(--text-xs);color:var(--text-subtle);}
.irb-pbf__year input{width:100%;}
.irb-pbf__group{grid-column:1/-1;border:1px solid var(--border-subtle);border-radius:var(--radius-lg,12px);
  padding:10px 14px 14px;margin:2px 0;}
.irb-pbf__legend{font-size:var(--text-xs);font-weight:var(--weight-semibold,600);color:var(--accent);padding:0 6px;}
.irb-pbf__groupgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px 12px;}
.irb-pbf__bool{grid-column:1/-1;display:flex;align-items:center;gap:9px;padding:4px 2px;}
.irb-pbf__bool input{width:17px;height:17px;accent-color:var(--accent);}
.irb-pbf__bool label{font-size:var(--text-sm);color:var(--text-body);}
.irb-pbf__soon{display:inline-flex;align-items:center;font-size:var(--text-2xs,11px);font-weight:600;color:var(--text-subtle);
  background:var(--surface-sunken);border-radius:999px;padding:1px 8px;}
.irb-pbf__actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;}
/* Адаптив (#238): на узком экране — гарантированно один столбец, уже паддинги. */
@media (max-width:560px){
  .irb-pbf{padding:14px 13px;}
  .irb-pbf__grid{grid-template-columns:1fr;}
  .irb-pbf__groupgrid{grid-template-columns:1fr;}
  .irb-pbf__actions{justify-content:stretch;}
  .irb-pbf__actions > *{flex:1;}
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-pbf-css")) {
  const s = document.createElement("style"); s.id = "irb-pbf-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Конструктор одного терма ИРБИС. Префикс может уже содержать «=» (напр. "KT=FT!"),
// тогда значение клеится без второго «=». Текстовые поля усекаем «$».
function term(f: SearchFieldDef, raw: string): string {
  const v = raw.trim().replace(/"/g, "");
  if (!v) return "";
  const body = f.prefix.includes("=") ? f.prefix + v : f.prefix + "=" + v + (f.type === "text" ? "$" : "");
  return '"' + body + '"';
}

// Диапазон года → перечисление "(G=2000 + G=2001 + …)"; ограничиваем 80 годами.
function yearTerm(prefix: string, from: string, to: string): string {
  const a0 = parseInt(from, 10), b0 = parseInt(to, 10);
  const hasA = !Number.isNaN(a0), hasB = !Number.isNaN(b0);
  if (hasA && hasB) {
    let a = Math.min(a0, b0), b = Math.max(a0, b0);
    if (b - a > 80) b = a + 80;
    const ys: string[] = [];
    for (let y = a; y <= b; y++) ys.push('"' + prefix + "=" + y + '"');
    return "(" + ys.join(" + ") + ")";
  }
  if (hasA || hasB) return '"' + prefix + "=" + (hasA ? a0 : b0) + '"';
  return "";
}

export function PerBaseSearchForm({ form, db, onSearch, onWarn }: {
  form: BaseFormDef;
  db: string;
  onSearch: (expr: string) => void;
  onWarn?: (msg: string) => void;
}) {
  // Значения по индексу поля; для года — отдельные ключи "<i>_from"/"<i>_to".
  const [vals, setVals] = React.useState<Record<string, string>>({});
  // Опции для списков (combobox) из словаря: индекс поля → массив значений.
  const [opts, setOpts] = React.useState<Record<number, string[]>>({});

  // Сбрасываем значения при смене базы.
  React.useEffect(() => { setVals({}); }, [form]);

  // Подтягиваем подсказки для полей-списков из /api/terms по префиксу.
  React.useEffect(() => {
    let alive = true;
    form.fields.forEach((f, i) => {
      if (f.type !== "select" || f.prefix.includes("=")) return;
      api.terms(f.prefix + "=", 40, db).then((r) => {
        if (!alive || !r.json?.ok || !r.json.data) return;
        const list = r.json.data.terms
          .map((t) => t.term.indexOf(f.prefix + "=") === 0 ? t.term.slice(f.prefix.length + 1) : t.term)
          .filter((s) => s && s.length <= 60);
        if (list.length) setOpts((o) => ({ ...o, [i]: Array.from(new Set(list)).slice(0, 40) }));
      });
    });
    return () => { alive = false; };
  }, [form, db]);

  const set = (k: string, v: string) => setVals((s) => ({ ...s, [k]: v }));

  function submit() {
    const parts: string[] = [];
    form.fields.forEach((f, i) => {
      if (f.type === "bool") return;                       // фильтр эл.копии пока не подключён
      if (f.type === "year") {
        const t = yearTerm(f.prefix, vals[i + "_from"] || "", vals[i + "_to"] || "");
        if (t) parts.push(t);
      } else {
        const t = term(f, vals[i] || "");
        if (t) parts.push(t);
      }
    });
    if (!parts.length) { onWarn?.("Заполните хотя бы одно поле."); return; }
    onSearch(parts.length === 1 ? parts[0] : "(" + parts.join(" * ") + ")");
  }

  function reset() { setVals({}); }

  // Рендер одного поля (без обёртки группы).
  const renderField = (f: SearchFieldDef, i: number) => {
    if (f.type === "year") {
      return (
        <div className="irb-pbf__field" key={i}>
          <span className="irb-pbf__label">{f.label}</span>
          <div className="irb-pbf__year">
            <span>с</span>
            <input className="irb-pbf__in" inputMode="numeric" maxLength={4} placeholder="гггг"
              value={vals[i + "_from"] || ""} onChange={(e) => set(i + "_from", e.target.value)} />
            <span>по</span>
            <input className="irb-pbf__in" inputMode="numeric" maxLength={4} placeholder="гггг"
              value={vals[i + "_to"] || ""} onChange={(e) => set(i + "_to", e.target.value)} />
          </div>
        </div>
      );
    }
    if (f.type === "bool") {
      return (
        <div className="irb-pbf__bool" key={i}>
          <input type="checkbox" id={"pbf-bool-" + i} disabled />
          <label htmlFor={"pbf-bool-" + i}>{f.label}</label>
          <span className="irb-pbf__soon">скоро</span>
        </div>
      );
    }
    const listId = "pbf-dl-" + i;
    const hasOpts = f.type === "select" && (opts[i]?.length ?? 0) > 0;
    return (
      <div className="irb-pbf__field" key={i}>
        <label className="irb-pbf__label" htmlFor={"pbf-f-" + i}>{f.label}</label>
        <input id={"pbf-f-" + i} className="irb-pbf__in" value={vals[i] || ""}
          list={hasOpts ? listId : undefined}
          onChange={(e) => set(i, e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          placeholder={f.type === "select" ? "значение или выбор из словаря" : ""} />
        {hasOpts && <datalist id={listId}>{opts[i].map((o) => <option key={o} value={o} />)}</datalist>}
      </div>
    );
  };

  // Группируем подряд идущие поля с одинаковым group в один fieldset.
  const blocks: React.ReactNode[] = [];
  let i = 0;
  while (i < form.fields.length) {
    const g = form.fields[i].group;
    if (g) {
      const groupFields: Array<[SearchFieldDef, number]> = [];
      while (i < form.fields.length && form.fields[i].group === g) { groupFields.push([form.fields[i], i]); i++; }
      blocks.push(
        <fieldset className="irb-pbf__group" key={"g-" + g}>
          <legend className="irb-pbf__legend">{g}</legend>
          <div className="irb-pbf__groupgrid">{groupFields.map(([f, idx]) => renderField(f, idx))}</div>
        </fieldset>
      );
    } else {
      blocks.push(renderField(form.fields[i], i)); i++;
    }
  }

  return (
    <div className="irb-pbf">
      <div className="irb-pbf__head">
        <h3 className="irb-pbf__title">Расширенный поиск</h3>
        <span className="irb-pbf__sub">· {form.base}</span>
      </div>
      <div className="irb-pbf__grid">{blocks}</div>
      <div className="irb-pbf__actions">
        <Button variant="ghost" onClick={reset}>Сброс</Button>
        <Button iconLeft="search" onClick={submit}>Найти</Button>
      </div>
    </div>
  );
}
