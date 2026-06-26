// Книгообеспеченность (#186) — рабочий стол (standalone-деск ККО).
// Связка строится сверху вниз: факультет → специальность → дисциплина. К
// дисциплине привязывается литература (осн./доп.), задаётся контингент (число
// студентов). По дисциплине и по специальности считается коэффициент
// книгообеспеченности (Кко) с флагом дефицита и недостающими экземплярами;
// переключатель «нормализация» меняет режим расчёта (учёт многоразового
// использования — каждый Кко в среднем ограничивается единицей).
//
// КОНТРАКТ БЭКА (own BookProvisionStore, ИРБИС не нужен — core.py / bookprovision.py):
//   POST /api/bp/faculty     {code,name}                      → {id}            (bp.write)
//   POST /api/bp/specialty   {facultyId,napr,spec,vid,form,name} → {id}         (bp.write)
//   POST /api/bp/discipline  {specialtyId,discId,name,semester,students} → {id} (bp.write)
//                            — идемпотентен по (specialtyId,discId,semester):
//                              повторный POST обновляет name/students (так задаём контингент).
//   POST /api/bp/bind        {disciplineId,title,kind,copies} → {id}            (bp.write)
//   GET  /api/bp/provision?discipline=<id>  → отчёт ККО дисциплины               (bp.read)
//   GET  /api/bp/provision?specialty=<id>   → сводный отчёт ККО специальности    (bp.read)
//     Отчёт = BpProvisionReport: {coefficient(=average_kko), norm(=kko_norm),
//       status(ok|deficit), students, copies(=total_exemplars), shortfall,
//       bindings:[{title,kind,copies(=exemplars),author?,mfn?}], а также сырые поля
//       движка: under_provisioned, disciplines[...] (для специальности)}.
// ВАЖНО: POST-эндпойнты возвращают ТОЛЬКО {id} — реквизиты карточки (код/имя)
//   держим локально из форм. Расчёт ВСЕГДА читаем отчётом bp/provision по id.
// Гранты: всё под bp.write/bp.read. У демо-роли administrator они есть; у
//   librarian (reader-service+cataloger) их НЕТ → операции вернут 403 (см. отчёт).
// Мягкая деградация: нет /api/bp/* (404/501) — информер, приложение не падает.
import React from "react";
import { api } from "./api";
import type { BpFaculty, BpSpecialty, BpDiscipline, BpProvisionReport, BpProvisionBinding } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Локальные узлы связки: id с сервера + реквизиты из форм (POST отдаёт только {id}).
type FacNode = { id: string | number; code: string; name: string };
type SpecNode = { id: string | number; facultyId: string | number; spec: string; name: string };
type DiscNode = {
  id: string | number; specialtyId: string | number;
  discId: string; name: string; semester: string; students: number;
};

// Пространство имён .bp__* — не пересекается с .stf__ / .cdesk__ / .acq__ / .irb-* / .kko__.
const CSS = `
.bp{font-family:var(--font-ui);}
.bp__grid{display:grid;grid-template-columns:300px minmax(0,1fr);gap:18px;align-items:start;}
.bp__card{background:var(--surface-card);border:1px solid var(--border-subtle);border-radius:var(--radius-lg);}
.bp__pad{padding:14px 16px;}
.bp__cap{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--text-subtle);display:flex;align-items:center;gap:7px;margin-bottom:12px;}
.bp__step-n{width:18px;height:18px;border-radius:var(--radius-full);background:var(--accent-weak);color:var(--accent-press);font-size:10.5px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none;}
.bp__fld{display:flex;flex-direction:column;gap:5px;margin-bottom:10px;}
.bp__fld-lab{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-subtle);}
.bp__in,.bp__sel{width:100%;box-sizing:border-box;padding:8px 11px;border-radius:var(--radius-md);
  border:1px solid var(--border-default);background:var(--surface-card);color:var(--text-body);
  font-family:var(--font-ui);font-size:13.5px;}
.bp__in:focus,.bp__sel:focus{outline:none;border-color:var(--accent);}
.bp__row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.bp__pick{display:flex;flex-direction:column;gap:2px;margin-bottom:12px;}
.bp__pick-item{display:flex;align-items:center;gap:8px;width:100%;text-align:left;border:none;cursor:pointer;background:transparent;
  padding:7px 9px;border-radius:var(--radius-md);font:inherit;color:var(--text-muted);}
.bp__pick-item:hover{background:var(--surface-hover);color:var(--text-body);}
.bp__pick-item--on{background:var(--accent-weak);color:var(--accent-press);font-weight:600;}
.bp__pick-code{font-family:var(--font-mono);font-size:11px;color:var(--text-subtle);flex:none;}
.bp__kko{display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:var(--radius-lg);margin-bottom:14px;}
.bp__kko--ok{background:var(--status-available-bg,#E3F0E4);}
.bp__kko--bad{background:var(--status-issued-bg,#FBEFD8);}
.bp__kko-val{font-family:var(--font-mono);font-weight:700;font-size:30px;line-height:1;}
.bp__kko--ok .bp__kko-val{color:var(--status-available,#3C7D3F);}
.bp__kko--bad .bp__kko-val{color:var(--status-issued,#B0791C);}
.bp__kko-lab{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-subtle);}
.bp__kko-sub{font-size:12.5px;color:var(--text-body);margin-top:3px;}
.bp__flag{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:var(--radius-full);}
.bp__flag--bad{background:var(--danger-50,#FBE9E7);color:var(--danger-500);}
.bp__flag--ok{background:transparent;color:var(--status-available,#3C7D3F);}
.bp__toggle{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--text-body);cursor:pointer;user-select:none;}
.bp__lit{display:grid;grid-template-columns:auto 1fr auto auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border-subtle);}
.bp__lit:last-child{border-bottom:none;}
.bp__lit-kind{font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:var(--radius-full);white-space:nowrap;}
.bp__lit-kind--main{background:var(--accent-weak);color:var(--accent-press);}
.bp__lit-kind--extra{background:var(--surface-hover);color:var(--text-muted);}
.bp__lit-title{font-weight:600;font-size:13px;min-width:0;}
.bp__lit-copies{font-family:var(--font-mono);font-size:12.5px;color:var(--text-muted);white-space:nowrap;}
.bp__disc{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;padding:11px 16px;border-bottom:1px solid var(--border-subtle);}
.bp__disc:last-child{border-bottom:none;}
.bp__disc-kko{font-family:var(--font-mono);font-weight:700;font-size:15px;text-align:right;}
@media (max-width:920px){.bp__grid{grid-template-columns:1fr;}}
`;
if (typeof document !== "undefined" && !document.getElementById("bp-css")) {
  const s = document.createElement("style"); s.id = "bp-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Дефицит по отчёту: status==='deficit' (или, как запас, under_provisioned флаг движка).
function isDeficit(r?: BpProvisionReport | null): boolean {
  if (!r) return false;
  if (r.status) return r.status === "deficit";
  const under = (r as any).under_provisioned;
  if (typeof under === "boolean") return under;
  if (Array.isArray(under)) return under.length > 0;
  if (r.coefficient != null && r.norm != null) return r.coefficient < r.norm;
  return false;
}
function kkoClass(r?: BpProvisionReport | null): string { return isDeficit(r) ? "bad" : "ok"; }
function fmtKko(v?: number | null): string {
  return v == null ? "—" : v.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function KkoFlag({ r }: { r?: BpProvisionReport | null }) {
  if (!r) return null;
  const bad = isDeficit(r);
  const sf = r.shortfall;
  return bad
    ? <span className="bp__flag bp__flag--bad"><Icon name="alert-triangle" size={13} />Дефицит{sf ? " · −" + sf + " экз." : ""}</span>
    : <span className="bp__flag bp__flag--ok"><Icon name="check-circle" size={13} />Норматив выполнен</span>;
}

// Сводка специальности перечисляет дисциплины с их Кко: используем сырые
// disciplines[...] из specialty_provision (поля движка), деградируем к [].
type SpecDiscRow = { id?: string | number; name?: string; average_kko?: number | null; under_provisioned?: boolean };
function specDisciplines(r?: BpProvisionReport | null): SpecDiscRow[] {
  const raw = r && (r as any).disciplines;
  if (!Array.isArray(raw)) return [];
  return raw.map((d: any) => ({
    id: d.discipline_id, name: d.name, average_kko: d.average_kko, under_provisioned: d.under_provisioned,
  }));
}

const SPEC_FORMS = ["очная", "очно-заочная", "заочная"];

export function BookProvisionDesk({ toast }: { toast: ToastFn }) {
  const [unavailable, setUnavailable] = React.useState(false);
  const [normalize, setNormalize] = React.useState(false);

  // связка (id+реквизиты держим локально; расчёт читаем отчётом по id)
  const [faculties, setFaculties] = React.useState<FacNode[]>([]);
  const [specialties, setSpecialties] = React.useState<SpecNode[]>([]);
  const [disciplines, setDisciplines] = React.useState<DiscNode[]>([]);
  const [facId, setFacId] = React.useState<string | number | null>(null);
  const [specId, setSpecId] = React.useState<string | number | null>(null);
  const [discId, setDiscId] = React.useState<string | number | null>(null);

  // отчёты ККО (от GET /api/bp/provision)
  const [discReport, setDiscReport] = React.useState<BpProvisionReport | null>(null);
  const [specReport, setSpecReport] = React.useState<BpProvisionReport | null>(null);

  // формы
  const [fCode, setFCode] = React.useState(""); const [fName, setFName] = React.useState("");
  const [sNapr, setSNapr] = React.useState(""); const [sSpec, setSSpec] = React.useState("");
  const [sVid, setSVid] = React.useState(""); const [sForm, setSForm] = React.useState(SPEC_FORMS[0]); const [sName, setSName] = React.useState("");
  const [dDiscId, setDDiscId] = React.useState(""); const [dName, setDName] = React.useState("");
  const [dSem, setDSem] = React.useState(""); const [dStud, setDStud] = React.useState("");
  const [contStud, setContStud] = React.useState("");
  const [litTitle, setLitTitle] = React.useState(""); const [litKind, setLitKind] = React.useState<"main" | "extra">("main"); const [litCopies, setLitCopies] = React.useState("");

  const facList = faculties;
  const specList = specialties.filter((s) => s.facultyId === facId);
  const discList = disciplines.filter((d) => d.specialtyId === specId);
  const curDisc = disciplines.find((d) => d.id === discId) || null;
  const curSpec = specialties.find((s) => s.id === specId) || null;

  function down404(r: { status: number }): boolean {
    if (r.status === 404 || r.status === 501) { setUnavailable(true); return true; }
    return false;
  }

  // --- отчёты ККО (после изменения связки/контингента/привязки/нормализации) ----
  async function refreshDiscReport(id: string | number) {
    const r = await api.bpProvision({ discipline: String(id) });
    if (r.json?.ok && r.json.data) setDiscReport(r.json.data);
    else if (down404(r)) return;
    else setDiscReport(null);
  }
  async function refreshSpecReport(id: string | number) {
    const r = await api.bpProvision({ specialty: String(id) });
    if (r.json?.ok && r.json.data) setSpecReport(r.json.data);
    else if (down404(r)) return;
    else setSpecReport(null);
  }
  // пересчёт при смене нормализации
  React.useEffect(() => {
    if (discId != null) void refreshDiscReport(discId);
    if (specId != null) void refreshSpecReport(specId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [normalize]);

  function permToast(r: { status: number }): boolean {
    if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант bp.write (роль «Администратор»)." });
      return true;
    }
    return false;
  }

  // --- создание узлов связки -----------------------------------------------
  async function addFaculty() {
    const code = fCode.trim(); const name = fName.trim();
    if (!code || !name) { toast({ variant: "info", title: "Заполните факультет", message: "Нужны код и наименование." }); return; }
    const r = await api.bpFaculty({ code, name });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const f: FacNode = { id: (r.json.data as BpFaculty).id, code, name };
      setFaculties((xs) => xs.concat([f])); setFacId(f.id);
      setSpecId(null); setDiscId(null); setSpecReport(null); setDiscReport(null);
      setFCode(""); setFName("");
      toast({ variant: "success", title: "Факультет добавлен", message: code + " · " + name });
    } else if (permToast(r)) return;
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }
  async function addSpecialty() {
    if (facId == null) { toast({ variant: "info", title: "Выберите факультет", message: "Специальность создаётся под факультетом." }); return; }
    const name = sName.trim();
    if (!name) { toast({ variant: "info", title: "Укажите наименование", message: "Наименование специальности обязательно." }); return; }
    const spec = sSpec.trim();
    const r = await api.bpSpecialty({ facultyId: facId, napr: sNapr.trim() || undefined, spec: spec || undefined, vid: sVid.trim() || undefined, form: sForm, name });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const s: SpecNode = { id: (r.json.data as BpSpecialty).id, facultyId: facId, spec, name };
      setSpecialties((xs) => xs.concat([s])); setSpecId(s.id); setDiscId(null); setDiscReport(null);
      void refreshSpecReport(s.id);
      setSNapr(""); setSSpec(""); setSVid(""); setSName("");
      toast({ variant: "success", title: "Специальность добавлена", message: name });
    } else if (permToast(r)) return;
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }
  async function addDiscipline() {
    if (specId == null) { toast({ variant: "info", title: "Выберите специальность", message: "Дисциплина создаётся под специальностью." }); return; }
    const name = dName.trim();
    if (!name) { toast({ variant: "info", title: "Укажите наименование", message: "Наименование дисциплины обязательно." }); return; }
    // Шифр дисциплины (3^0) обязателен на бэке — подставляем устойчивый локальный, если оператор не задал.
    const discIdVal = dDiscId.trim() || ("D-" + (disciplines.length + 1));
    const semester = dSem.trim();
    const students = dStud.trim() ? parseInt(dStud, 10) : 0;
    const r = await api.bpDiscipline({ specialtyId: specId, discId: discIdVal, name, semester: semester ? parseInt(semester, 10) : undefined, students });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const d: DiscNode = { id: (r.json.data as BpDiscipline).id, specialtyId: specId, discId: discIdVal, name, semester, students };
      setDisciplines((xs) => xs.concat([d])); setDiscId(d.id);
      void refreshDiscReport(d.id); if (specId != null) void refreshSpecReport(specId);
      setDDiscId(""); setDName(""); setDSem(""); setDStud("");
      toast({ variant: "success", title: "Дисциплина добавлена", message: name });
    } else if (permToast(r)) return;
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }

  // --- контингент: повторный POST /api/bp/discipline (идемпотентен по
  //     specialtyId+discId+semester) обновляет students. Так задаём контингент
  //     БЕЗ /api/bp/contingent (его клиентский метод шлёт несовместимое тело). ----
  async function setContingent() {
    if (discId == null || curDisc == null) return;
    const n = parseInt(contStud, 10);
    if (isNaN(n) || n < 0) { toast({ variant: "info", title: "Проверьте контингент", message: "Число студентов должно быть ≥ 0." }); return; }
    const r = await api.bpDiscipline({
      specialtyId: curDisc.specialtyId, discId: curDisc.discId, name: curDisc.name,
      semester: curDisc.semester ? parseInt(curDisc.semester, 10) : undefined, students: n,
    });
    if (down404(r)) return;
    if (r.json?.ok) {
      setDisciplines((xs) => xs.map((d) => (d.id === discId ? { ...d, students: n } : d)));
      toast({ variant: "success", title: "Контингент обновлён", message: n + " студент(ов) — Кко пересчитан." });
      setContStud("");
      void refreshDiscReport(discId); if (specId != null) void refreshSpecReport(specId);
    } else if (permToast(r)) return;
    else toast({ variant: "error", title: "Не обновлено", message: "Повторите попытку." });
  }
  async function bindLit() {
    if (discId == null) return;
    const t = litTitle.trim(); const c = parseInt(litCopies, 10);
    if (!t) { toast({ variant: "info", title: "Укажите издание", message: "Заглавие литературы обязательно." }); return; }
    if (isNaN(c) || c < 1) { toast({ variant: "info", title: "Проверьте экземпляры", message: "Число экземпляров должно быть ≥ 1." }); return; }
    const r = await api.bpBind({ disciplineId: discId, title: t, kind: litKind, copies: c });
    if (down404(r)) return;
    if (r.json?.ok) {
      toast({ variant: "success", title: "Литература привязана", message: (litKind === "main" ? "Осн." : "Доп.") + " · " + t + " · " + c + " экз." });
      setLitTitle(""); setLitCopies("");
      void refreshDiscReport(discId); if (specId != null) void refreshSpecReport(specId);
    } else if (permToast(r)) return;
    else toast({ variant: "error", title: "Не привязано", message: "Повторите попытку." });
  }

  function pickFac(id: string | number) { setFacId(id); setSpecId(null); setDiscId(null); setSpecReport(null); setDiscReport(null); }
  function pickSpec(id: string | number) { setSpecId(id); setDiscId(null); setDiscReport(null); void refreshSpecReport(id); }
  function pickDisc(id: string | number) { setDiscId(id); void refreshDiscReport(id); }

  const head = (
    <div className="stf__pagehead">
      <div className="stf__h1">
        <h2>Книгообеспеченность</h2>
        <span className="stf__pill">Связка · Кко</span>
      </div>
      <label className="bp__toggle">
        <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} />
        Нормализация расчёта
      </label>
    </div>
  );

  if (unavailable) return (
    <div className="bp">
      {head}
      <div className="bp__card" style={{ padding: 4 }}>
        <EmptyState icon="bar-chart" title="Книгообеспеченность подключается отдельным модулем"
          description="Рабочий стол книгообеспеченности (факультет → специальность → дисциплина, привязка литературы, расчёт Кко) свёрстан в Стиле A и работает поверх движка (#186). На текущем сервере эндпойнты /api/bp/* ещё не развёрнуты — данные появятся после их публикации." />
      </div>
    </div>
  );

  const dr = discReport;
  const sr = specReport;
  const bindings: BpProvisionBinding[] = (dr?.bindings as BpProvisionBinding[]) || [];

  return (
    <div className="bp">
      {head}
      <div className="bp__grid">
        {/* ===== Левая колонка: построение связки ===== */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {/* факультет */}
          <div className="bp__card bp__pad">
            <span className="bp__cap"><span className="bp__step-n">1</span>Факультет</span>
            {facList.length > 0 && (
              <div className="bp__pick">
                {facList.map((f) => (
                  <button key={f.id} type="button" className={"bp__pick-item" + (f.id === facId ? " bp__pick-item--on" : "")} onClick={() => pickFac(f.id)}>
                    <span className="bp__pick-code">{f.code}</span><span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{f.name}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="bp__row2">
              <div className="bp__fld"><label className="bp__fld-lab">Код</label><input className="bp__in" value={fCode} onChange={(e) => setFCode(e.target.value)} placeholder="ФТ" /></div>
              <div className="bp__fld"><label className="bp__fld-lab">Наименование</label><input className="bp__in" value={fName} onChange={(e) => setFName(e.target.value)} placeholder="Факультет…" /></div>
            </div>
            <Button block variant="secondary" size="sm" iconLeft="plus" onClick={addFaculty}>Добавить факультет</Button>
          </div>

          {/* специальность */}
          <div className="bp__card bp__pad" style={{ opacity: facId == null ? 0.55 : 1 }}>
            <span className="bp__cap"><span className="bp__step-n">2</span>Специальность</span>
            {specList.length > 0 && (
              <div className="bp__pick">
                {specList.map((s) => (
                  <button key={s.id} type="button" className={"bp__pick-item" + (s.id === specId ? " bp__pick-item--on" : "")} onClick={() => pickSpec(s.id)}>
                    {s.spec && <span className="bp__pick-code">{s.spec}</span>}<span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="bp__row2">
              <div className="bp__fld"><label className="bp__fld-lab">Направление</label><input className="bp__in" value={sNapr} onChange={(e) => setSNapr(e.target.value)} placeholder="напр." disabled={facId == null} /></div>
              <div className="bp__fld"><label className="bp__fld-lab">Специальность</label><input className="bp__in" value={sSpec} onChange={(e) => setSSpec(e.target.value)} placeholder="код" disabled={facId == null} /></div>
            </div>
            <div className="bp__row2">
              <div className="bp__fld"><label className="bp__fld-lab">Вид</label><input className="bp__in" value={sVid} onChange={(e) => setSVid(e.target.value)} placeholder="бакалавриат…" disabled={facId == null} /></div>
              <div className="bp__fld"><label className="bp__fld-lab">Форма</label>
                <select className="bp__sel" value={sForm} onChange={(e) => setSForm(e.target.value)} disabled={facId == null}>
                  {SPEC_FORMS.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
            </div>
            <div className="bp__fld"><label className="bp__fld-lab">Наименование</label><input className="bp__in" value={sName} onChange={(e) => setSName(e.target.value)} placeholder="Наименование специальности" disabled={facId == null} /></div>
            <Button block variant="secondary" size="sm" iconLeft="plus" onClick={addSpecialty} disabled={facId == null}>Добавить специальность</Button>
          </div>

          {/* дисциплина */}
          <div className="bp__card bp__pad" style={{ opacity: specId == null ? 0.55 : 1 }}>
            <span className="bp__cap"><span className="bp__step-n">3</span>Дисциплина</span>
            {discList.length > 0 && (
              <div className="bp__pick">
                {discList.map((d) => (
                  <button key={d.id} type="button" className={"bp__pick-item" + (d.id === discId ? " bp__pick-item--on" : "")} onClick={() => pickDisc(d.id)}>
                    {d.discId && <span className="bp__pick-code">{d.discId}</span>}<span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{d.name}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="bp__fld"><label className="bp__fld-lab">Наименование</label><input className="bp__in" value={dName} onChange={(e) => setDName(e.target.value)} placeholder="Дисциплина" disabled={specId == null} /></div>
            <div className="bp__row2">
              <div className="bp__fld"><label className="bp__fld-lab">Шифр</label><input className="bp__in" value={dDiscId} onChange={(e) => setDDiscId(e.target.value)} placeholder="код" disabled={specId == null} /></div>
              <div className="bp__fld"><label className="bp__fld-lab">Семестр</label><input className="bp__in" type="number" min={1} value={dSem} onChange={(e) => setDSem(e.target.value)} disabled={specId == null} /></div>
            </div>
            <div className="bp__fld"><label className="bp__fld-lab">Студентов (контингент)</label><input className="bp__in" type="number" min={0} value={dStud} onChange={(e) => setDStud(e.target.value)} disabled={specId == null} /></div>
            <Button block variant="secondary" size="sm" iconLeft="plus" onClick={addDiscipline} disabled={specId == null}>Добавить дисциплину</Button>
          </div>
        </div>

        {/* ===== Правая колонка: Кко по дисциплине / по специальности ===== */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {discId != null ? (
            <>
              {/* Кко по дисциплине */}
              <div className="bp__card bp__pad">
                <span className="bp__cap">Кко дисциплины · {curDisc?.name || "—"}</span>
                <div className={"bp__kko bp__kko--" + kkoClass(dr)}>
                  <div>
                    <div className="bp__kko-val">{fmtKko(dr?.coefficient)}</div>
                    <div className="bp__kko-lab">экз. / студента</div>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <KkoFlag r={dr} />
                    <div className="bp__kko-sub">
                      {dr?.copies != null ? dr.copies + " экз. фонда" : "фонд не привязан"}
                      {dr?.students != null ? " · " + dr.students + " студ." : ""}
                      {dr?.norm != null ? " · норматив " + fmtKko(dr.norm) : ""}
                      {normalize ? " · нормализовано" : ""}
                    </div>
                  </div>
                </div>

                {/* контингент */}
                <div className="bp__row2" style={{ alignItems: "end", marginBottom: 12 }}>
                  <div className="bp__fld" style={{ marginBottom: 0 }}>
                    <label className="bp__fld-lab">Изменить контингент</label>
                    <input className="bp__in" type="number" min={0} value={contStud} onChange={(e) => setContStud(e.target.value)} placeholder={dr?.students != null ? String(dr.students) : "студентов"} />
                  </div>
                  <Button variant="secondary" iconLeft="users" onClick={setContingent}>Задать</Button>
                </div>

                {/* привязка литературы */}
                <span className="bp__cap" style={{ marginTop: 4 }}>Привязать литературу</span>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 120px 90px auto", gap: 8, alignItems: "end" }}>
                  <div className="bp__fld" style={{ marginBottom: 0 }}><label className="bp__fld-lab">Издание</label><input className="bp__in" value={litTitle} onChange={(e) => setLitTitle(e.target.value)} placeholder="заглавие / MFN" /></div>
                  <div className="bp__fld" style={{ marginBottom: 0 }}><label className="bp__fld-lab">Вид</label>
                    <select className="bp__sel" value={litKind} onChange={(e) => setLitKind(e.target.value as "main" | "extra")}>
                      <option value="main">Основная</option><option value="extra">Дополнительная</option>
                    </select>
                  </div>
                  <div className="bp__fld" style={{ marginBottom: 0 }}><label className="bp__fld-lab">Экз.</label><input className="bp__in" type="number" min={1} value={litCopies} onChange={(e) => setLitCopies(e.target.value)} /></div>
                  <Button iconLeft="plus" onClick={bindLit}>Привязать</Button>
                </div>

                {/* привязанная литература (из отчёта дисциплины) */}
                {bindings.length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    {bindings.map((b, i) => {
                      // Отчёт движка кладёт число экземпляров в `exemplars`; легковесный
                      // контракт информера — в `copies`. Берём что есть (exemplars ⊃ copies).
                      const ex = b.copies != null ? b.copies : (b as any).exemplars;
                      return (
                        <div className="bp__lit" key={i + ":" + b.title}>
                          <span className={"bp__lit-kind bp__lit-kind--" + (b.kind === "extra" ? "extra" : "main")}>{b.kind === "extra" ? "ДОП" : "ОСН"}</span>
                          <span className="bp__lit-title" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{b.title}{b.author ? <span style={{ fontWeight: 400, color: "var(--text-subtle)" }}> · {b.author}</span> : null}</span>
                          <span className="bp__lit-copies">{ex != null ? ex + " экз." : "—"}</span>
                          {b.mfn != null ? <span className="bp__pick-code">MFN {b.mfn}</span> : <span />}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bp__card" style={{ padding: 4 }}>
              <EmptyState icon="list-tree" title="Выберите дисциплину" description="Постройте связку слева (факультет → специальность → дисциплина) и выберите дисциплину — здесь покажется её коэффициент книгообеспеченности (Кко), привязка литературы и контингент." />
            </div>
          )}

          {/* сводный Кко по специальности */}
          {specId != null && sr && (
            <div className="bp__card">
              <div className="bp__pad" style={{ paddingBottom: 8 }}>
                <span className="bp__cap" style={{ marginBottom: 8 }}>Кко специальности · {curSpec?.name || "—"}</span>
                <div className={"bp__kko bp__kko--" + kkoClass(sr)} style={{ marginBottom: 0 }}>
                  <div>
                    <div className="bp__kko-val">{fmtKko(sr?.coefficient)}</div>
                    <div className="bp__kko-lab">сводный Кко</div>
                  </div>
                  <KkoFlag r={sr} />
                </div>
              </div>
              {specDisciplines(sr).length > 0 && (
                <div>
                  {specDisciplines(sr).map((dc, i) => {
                    const bad = !!dc.under_provisioned;
                    return (
                      <div className="bp__disc" key={(dc.id ?? i) + ":" + (dc.name || "")}>
                        <span style={{ fontWeight: 600, fontSize: 13, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{dc.name}</span>
                        {bad
                          ? <span className="bp__flag bp__flag--bad"><Icon name="alert-triangle" size={13} />Дефицит</span>
                          : <span className="bp__flag bp__flag--ok"><Icon name="check-circle" size={13} />Норматив выполнен</span>}
                        <span className="bp__disc-kko" style={{ color: bad ? "var(--status-issued,#B0791C)" : "var(--status-available,#3C7D3F)" }}>{fmtKko(dc.average_kko)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
