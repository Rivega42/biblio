// Книгообеспеченность (#186) — рабочий стол. Связка строится сверху вниз:
//   факультет → специальность → дисциплина. К дисциплине привязывается
//   литература (осн./доп.), задаётся контингент (число студентов). По дисциплине
//   и по специальности считается коэффициент книгообеспеченности (Кко) с флагом
//   недообеспеченности и дефицитом экземпляров; переключатель «нормализация»
//   меняет режим расчёта (учёт многоразового использования). Карточки тянутся с
//   /api/bp/discipline и /api/bp/specialty.
// Мягкая деградация: нет /api/bp/* (404/501) — информер, приложение не падает.
import React from "react";
import { api } from "./api";
import type { BpFaculty, BpSpecialty, BpDiscipline, BpDisciplineCard, BpSpecialtyCard, BpKko } from "./api";
import type { ToastVariant } from "../components/feedback/Toast.jsx";
import { Button } from "../components/forms/Button.jsx";
import { Icon } from "../components/icon/Icon.jsx";
import { EmptyState } from "../components/feedback/EmptyState.jsx";

type ToastFn = (t: { variant: ToastVariant; title: string; message?: string }) => void;

// Пространство имён .bp__* — не пересекается с .stf__ / .cdesk__ / .acq__ / .irb-*.
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

// Цвет/класс блока Кко по флагу недообеспеченности.
function kkoClass(k?: BpKko): string { return k && k.underProvided ? "bad" : "ok"; }
function fmtKko(v?: number): string { return v == null ? "—" : v.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function KkoFlag({ k }: { k?: BpKko }) {
  if (!k) return null;
  return k.underProvided
    ? <span className="bp__flag bp__flag--bad"><Icon name="alert-triangle" size={13} />Недообеспечена{k.shortfall ? " · −" + k.shortfall + " экз." : ""}</span>
    : <span className="bp__flag bp__flag--ok"><Icon name="check-circle" size={13} />Норматив выполнен</span>;
}

const SPEC_FORMS = ["очная", "очно-заочная", "заочная"];

export function BookProvisionDesk({ toast }: { toast: ToastFn }) {
  const [unavailable, setUnavailable] = React.useState(false);
  const [normalize, setNormalize] = React.useState(false);

  // связка (локальная — связка строится формами; карточки тянутся с сервера)
  const [faculties, setFaculties] = React.useState<BpFaculty[]>([]);
  const [specialties, setSpecialties] = React.useState<BpSpecialty[]>([]);
  const [disciplines, setDisciplines] = React.useState<BpDiscipline[]>([]);
  const [facId, setFacId] = React.useState<string | number | null>(null);
  const [specId, setSpecId] = React.useState<string | number | null>(null);
  const [discId, setDiscId] = React.useState<string | number | null>(null);

  // карточки расчёта
  const [discCard, setDiscCard] = React.useState<BpDisciplineCard | null>(null);
  const [specCard, setSpecCard] = React.useState<BpSpecialtyCard | null>(null);

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

  function down404(r: { status: number }): boolean {
    if (r.status === 404 || r.status === 501) { setUnavailable(true); return true; }
    return false;
  }

  // --- расчётные карточки (после изменения связки/нормализации) -------------
  async function refreshDiscCard(id: string | number) {
    const r = await api.bpDisciplineCard(id, normalize);
    if (r.json?.ok && r.json.data) setDiscCard(r.json.data);
    else if (down404(r)) return;
    else setDiscCard(null);
  }
  async function refreshSpecCard(id: string | number) {
    const r = await api.bpSpecialtyCard(id, normalize);
    if (r.json?.ok && r.json.data) setSpecCard(r.json.data);
    else if (down404(r)) return;
    else setSpecCard(null);
  }
  // пересчёт при смене нормализации
  React.useEffect(() => {
    if (discId != null) void refreshDiscCard(discId);
    if (specId != null) void refreshSpecCard(specId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [normalize]);

  // --- создание узлов связки -----------------------------------------------
  async function addFaculty() {
    const code = fCode.trim(); const name = fName.trim();
    if (!code || !name) { toast({ variant: "info", title: "Заполните факультет", message: "Нужны код и наименование." }); return; }
    const r = await api.bpFaculty({ code, name });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const f = r.json.data;
      setFaculties((xs) => xs.concat([f])); setFacId(f.id); setSpecId(null); setDiscId(null); setSpecCard(null); setDiscCard(null);
      setFCode(""); setFName("");
      toast({ variant: "success", title: "Факультет добавлен", message: code + " · " + name });
    } else if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант на правку справочников." });
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }
  async function addSpecialty() {
    if (facId == null) { toast({ variant: "info", title: "Выберите факультет", message: "Специальность создаётся под факультетом." }); return; }
    const name = sName.trim();
    if (!name) { toast({ variant: "info", title: "Укажите наименование", message: "Наименование специальности обязательно." }); return; }
    const r = await api.bpSpecialty({ facultyId: facId, napr: sNapr.trim() || undefined, spec: sSpec.trim() || undefined, vid: sVid.trim() || undefined, form: sForm, name });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const s = { ...r.json.data, facultyId: r.json.data.facultyId ?? facId };
      setSpecialties((xs) => xs.concat([s])); setSpecId(s.id); setDiscId(null); setDiscCard(null);
      void refreshSpecCard(s.id);
      setSNapr(""); setSSpec(""); setSVid(""); setSName("");
      toast({ variant: "success", title: "Специальность добавлена", message: name });
    } else if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант на правку справочников." });
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }
  async function addDiscipline() {
    if (specId == null) { toast({ variant: "info", title: "Выберите специальность", message: "Дисциплина создаётся под специальностью." }); return; }
    const name = dName.trim();
    if (!name) { toast({ variant: "info", title: "Укажите наименование", message: "Наименование дисциплины обязательно." }); return; }
    const r = await api.bpDiscipline({ specialtyId: specId, discId: dDiscId.trim() || undefined, name, semester: dSem.trim() ? parseInt(dSem, 10) : undefined, students: dStud.trim() ? parseInt(dStud, 10) : undefined });
    if (down404(r)) return;
    if (r.json?.ok && r.json.data) {
      const d = { ...r.json.data, specialtyId: r.json.data.specialtyId ?? specId };
      setDisciplines((xs) => xs.concat([d])); setDiscId(d.id);
      void refreshDiscCard(d.id); if (specId != null) void refreshSpecCard(specId);
      setDDiscId(""); setDName(""); setDSem(""); setDStud("");
      toast({ variant: "success", title: "Дисциплина добавлена", message: name });
    } else if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант на правку справочников." });
    else toast({ variant: "error", title: "Не добавлено", message: "Повторите попытку." });
  }

  // --- контингент + привязка литературы ------------------------------------
  async function setContingent() {
    if (discId == null) return;
    const n = parseInt(contStud, 10);
    if (!n || n < 0) { toast({ variant: "info", title: "Проверьте контингент", message: "Число студентов должно быть ≥ 0." }); return; }
    const r = await api.bpContingent({ discId, students: n });
    if (down404(r)) return;
    if (r.json?.ok) {
      toast({ variant: "success", title: "Контингент обновлён", message: n + " студент(ов) — Кко пересчитан." });
      setContStud("");
      void refreshDiscCard(discId); if (specId != null) void refreshSpecCard(specId);
    } else if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант на правку." });
    else toast({ variant: "error", title: "Не обновлено", message: "Повторите попытку." });
  }
  async function bindLit() {
    if (discId == null) return;
    const t = litTitle.trim(); const c = parseInt(litCopies, 10);
    if (!t) { toast({ variant: "info", title: "Укажите издание", message: "Заглавие литературы обязательно." }); return; }
    if (!c || c < 1) { toast({ variant: "info", title: "Проверьте экземпляры", message: "Число экземпляров должно быть ≥ 1." }); return; }
    const r = await api.bpBind({ disciplineId: discId, title: t, kind: litKind, copies: c });
    if (down404(r)) return;
    if (r.json?.ok) {
      toast({ variant: "success", title: "Литература привязана", message: (litKind === "main" ? "Осн." : "Доп.") + " · " + t + " · " + c + " экз." });
      setLitTitle(""); setLitCopies("");
      void refreshDiscCard(discId); if (specId != null) void refreshSpecCard(specId);
    } else if (r.status === 401 || r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант на правку." });
    else toast({ variant: "error", title: "Не привязано", message: "Повторите попытку." });
  }

  function pickFac(id: string | number) { setFacId(id); setSpecId(null); setDiscId(null); setSpecCard(null); setDiscCard(null); }
  function pickSpec(id: string | number) { setSpecId(id); setDiscId(null); setDiscCard(null); void refreshSpecCard(id); }
  function pickDisc(id: string | number) { setDiscId(id); void refreshDiscCard(id); }

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

  const dk = discCard?.kko;
  const sk = specCard?.kko;
  const curDisc = disciplines.find((d) => d.id === discId);

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
                <span className="bp__cap">Кко дисциплины · {curDisc?.name || discCard?.discipline.name || "—"}</span>
                <div className={"bp__kko bp__kko--" + kkoClass(dk)}>
                  <div>
                    <div className="bp__kko-val">{fmtKko(dk?.value)}</div>
                    <div className="bp__kko-lab">экз. / студента</div>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <KkoFlag k={dk} />
                    <div className="bp__kko-sub">
                      {dk?.copies != null ? dk.copies + " экз. фонда" : "фонд не привязан"}
                      {dk?.students != null ? " · " + dk.students + " студ." : ""}
                      {dk?.norm != null ? " · норматив " + fmtKko(dk.norm) : ""}
                      {dk?.normalized ? " · нормализовано" : ""}
                    </div>
                  </div>
                </div>

                {/* контингент */}
                <div className="bp__row2" style={{ alignItems: "end", marginBottom: 12 }}>
                  <div className="bp__fld" style={{ marginBottom: 0 }}>
                    <label className="bp__fld-lab">Изменить контингент</label>
                    <input className="bp__in" type="number" min={0} value={contStud} onChange={(e) => setContStud(e.target.value)} placeholder={dk?.students != null ? String(dk.students) : "студентов"} />
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

                {/* привязанная литература */}
                {discCard?.bindings && discCard.bindings.length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    {discCard.bindings.map((b, i) => (
                      <div className="bp__lit" key={(b.id ?? i) + ":" + b.title}>
                        <span className={"bp__lit-kind bp__lit-kind--" + b.kind}>{b.kind === "main" ? "ОСН" : "ДОП"}</span>
                        <span className="bp__lit-title" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{b.title}{b.author ? <span style={{ fontWeight: 400, color: "var(--text-subtle)" }}> · {b.author}</span> : null}</span>
                        <span className="bp__lit-copies">{b.copies} экз.</span>
                        {b.mfn != null ? <span className="bp__pick-code">MFN {b.mfn}</span> : <span />}
                      </div>
                    ))}
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
          {specId != null && specCard && (
            <div className="bp__card">
              <div className="bp__pad" style={{ paddingBottom: 8 }}>
                <span className="bp__cap" style={{ marginBottom: 8 }}>Кко специальности · {specCard.specialty.name}</span>
                <div className={"bp__kko bp__kko--" + kkoClass(sk)} style={{ marginBottom: 0 }}>
                  <div>
                    <div className="bp__kko-val">{fmtKko(sk?.value)}</div>
                    <div className="bp__kko-lab">сводный Кко</div>
                  </div>
                  <KkoFlag k={sk} />
                </div>
              </div>
              {specCard.disciplines && specCard.disciplines.length > 0 && (
                <div>
                  {specCard.disciplines.map((dc, i) => (
                    <div className="bp__disc" key={(dc.discipline.id ?? i) + ":" + dc.discipline.name}>
                      <span style={{ fontWeight: 600, fontSize: 13, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>{dc.discipline.name}</span>
                      <KkoFlag k={dc.kko} />
                      <span className="bp__disc-kko" style={{ color: dc.kko?.underProvided ? "var(--status-issued,#B0791C)" : "var(--status-available,#3C7D3F)" }}>{fmtKko(dc.kko?.value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
