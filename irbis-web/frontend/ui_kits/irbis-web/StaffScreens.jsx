/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, Badge, Input, Alert } = NS;

  const LEVELS = { none: 0, read: 1, write: 2, delete: 3, admin: 4 };
  const hasGrant = (grants, domainId, need) => LEVELS[grants[domainId] || "none"] >= LEVELS[need || "read"];

  const TONE = {
    available: { fg: "var(--status-available-strong)", bg: "var(--status-available-bg)" },
    issued: { fg: "var(--status-issued-strong)", bg: "var(--status-issued-bg)" },
    danger: { fg: "var(--danger-500)", bg: "var(--status-unknown-bg)" },
    neutral: { fg: "var(--text-muted)", bg: "var(--surface-sunken)" },
  };

  // ===== Рабочий стол сотрудника — меню задач ПО ГРАНТАМ (не по АРМам) =====
  function StaffDesktop({ staff, onTask }) {
    const visible = staff.domains.filter((d) => hasGrant(staff.grants, d.id, d.need));
    return (
      <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-6) var(--space-6) var(--space-12)" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)", marginBottom: "var(--space-5)", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "var(--text-2xl)" }}>Рабочий стол</h1>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>{staff.role} · доступно задач по грантам: {visible.length}</span>
        </div>

        {/* Сводка */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
          {staff.summary.map((s) => {
            const t = TONE[s.tone] || TONE.neutral;
            return (
              <div key={s.label} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
                <span style={{ width: 40, height: 40, borderRadius: "var(--radius-md)", background: t.bg, color: t.fg, display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                  <Icon name={s.icon} size={20} />
                </span>
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-2xl)", fontWeight: 700, color: "var(--text-strong)", lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 3 }}>{s.label}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Домены-задачи */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "var(--space-4)" }}>
          {visible.map((d) => (
            <section key={d.id} style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-4)", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ width: 38, height: 38, borderRadius: "var(--radius-md)", background: "var(--accent-weak)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                  <Icon name={d.icon} size={20} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, color: "var(--text-strong)", fontSize: "var(--text-md)" }}>{d.label}</div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{d.desc}</div>
                </div>
                <Badge variant="neutral">{staff.grants[d.id]}</Badge>
              </div>
              <div style={{ padding: "var(--space-2)" }}>
                {d.tasks.length === 0 ? (
                  <div style={{ padding: "var(--space-3)", fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>Нет доступных операций.</div>
                ) : d.tasks.map((t) => (
                  <button key={t.id} type="button" onClick={() => onTask(d.id, t.id)} style={{
                    display: "flex", alignItems: "center", gap: "var(--space-3)", width: "100%", textAlign: "left",
                    border: "none", background: "transparent", borderRadius: "var(--radius-sm)", padding: "10px 12px", cursor: "pointer", fontFamily: "var(--font-ui)",
                  }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <Icon name={t.icon} size={17} style={{ color: "var(--text-subtle)", flex: "none" }} />
                    <span style={{ flex: 1, fontSize: "var(--text-sm)", color: "var(--text-body)", fontWeight: 500 }}>{t.label}</span>
                    {t.badge != null && <Badge variant="accent" count>{t.badge}</Badge>}
                    <Icon name="chevron-right" size={16} style={{ color: "var(--text-subtle)" }} />
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>

        {/* Скрытые по грантам — прозрачность модели доступа */}
        {staff.domains.length > visible.length && (
          <div style={{ marginTop: "var(--space-6)" }}>
            <Alert variant="info" title="Часть функций скрыта">
              Недоступно по грантам учётки: {staff.domains.filter((d) => !hasGrant(staff.grants, d.id, d.need)).map((d) => d.label).join(", ")}. Интерфейс показывает только разрешённое.
            </Alert>
          </div>
        )}
      </div>
    );
  }

  // ===== Рабочий лист каталогизации — динамическая форма из профиля базы =====
  function CatalogingWorksheet({ profile, onBack, onToast }) {
    const { DynamicField } = NS;
    const [page, setPage] = React.useState(profile.pages[0].id);
    const [values, setValues] = React.useState({});
    const [errors, setErrors] = React.useState({});
    const cur = profile.pages.find((p) => p.id === page);

    const setField = (code, v) => setValues((s) => ({ ...s, [code]: v }));

    function validate() {
      const errs = {};
      profile.pages.forEach((pg) => pg.fields.forEach((f) => {
        const v = values[f.code];
        if (f.required && (v == null || (typeof v === "string" && !v.trim()) || (Array.isArray(v) && v.length === 0))) {
          errs[f.code] = "Поле обязательно (ФЛК)";
        }
        if (f.type === "date" && typeof v === "string" && v && !/^\d{4}/.test(v)) {
          errs[f.code] = "Год должен начинаться с 4 цифр";
        }
      }));
      setErrors(errs);
      const ok = Object.keys(errs).length === 0;
      if (!ok) {
        const firstPage = profile.pages.find((pg) => pg.fields.some((f) => errs[f.code]));
        if (firstPage) setPage(firstPage.id);
      }
      return ok;
    }

    const filled = profile.pages.reduce((n, pg) => n + pg.fields.filter((f) => {
      const v = values[f.code];
      return v != null && (Array.isArray(v) ? v.length : String(v).trim());
    }).length, 0);

    return (
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
          <button type="button" onClick={onBack} style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, padding: 0 }}>
            <Icon name="arrow-left" size={17} /> К рабочему столу
          </button>
          <span style={{ marginLeft: "auto", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>заполнено полей: {filled}</span>
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)", marginBottom: "var(--space-5)", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "var(--text-2xl)" }}>Рабочий лист записи</h1>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>профиль: {profile.dbName}</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "210px 1fr", gap: "var(--space-6)", alignItems: "start" }}>
          {/* Страницы рабочего листа */}
          <aside style={{ position: "sticky", top: 76, display: "flex", flexDirection: "column", gap: 4 }}>
            {profile.pages.map((pg) => {
              const on = pg.id === page;
              const pgErr = pg.fields.some((f) => errors[f.code]);
              return (
                <button key={pg.id} type="button" onClick={() => setPage(pg.id)} style={{
                  display: "flex", alignItems: "center", gap: 9, textAlign: "left", cursor: "pointer",
                  padding: "10px 12px", borderRadius: "var(--radius-sm)", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: on ? 600 : 500,
                  border: "1px solid " + (on ? "var(--accent-weak-border)" : "transparent"),
                  background: on ? "var(--accent-weak)" : "transparent", color: on ? "var(--accent-press)" : "var(--text-body)",
                }}>
                  <span style={{ width: 3, alignSelf: "stretch", borderRadius: 2, background: on ? "var(--accent)" : "transparent" }} />
                  {pg.label}
                  {pgErr && <Icon name="alert-triangle" size={14} style={{ color: "var(--danger-500)", marginLeft: "auto" }} />}
                </button>
              );
            })}
          </aside>

          {/* Поля текущей страницы */}
          <div>
            <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)", display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
              {cur.fields.map((f) => (
                <DynamicField key={f.code} field={f} value={values[f.code]} onChange={(v) => setField(f.code, v)} error={errors[f.code]} />
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginTop: "var(--space-4)", flexWrap: "wrap" }}>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "inline-flex", alignItems: "center", gap: 6 }}>
                <Icon name="shield" size={14} /> ФЛК проверит обязательные поля и форматы перед сохранением.
              </span>
              <div style={{ flex: 1 }} />
              <Button variant="secondary" iconLeft="rotate-ccw" onClick={() => { setValues({}); setErrors({}); }}>Очистить</Button>
              <Button iconLeft="save" onClick={() => { if (validate()) onToast({ variant: "success", title: "Запись сохранена", message: "Прошла ФЛК. Внесена в черновики." }); else onToast({ variant: "error", title: "Не прошло ФЛК", message: "Заполните обязательные поля." }); }}>Сохранить запись</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Заглушка для операций, которые ещё не спроектированы детально
  function StaffStub({ title, onBack }) {
    return (
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "var(--space-16) var(--space-6)" }}>
        <button type="button" onClick={onBack} style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, padding: 0, marginBottom: "var(--space-5)" }}>
          <Icon name="arrow-left" size={17} /> К рабочему столу
        </button>
        <NS.EmptyState icon="clipboard-check" title={title}
          description="Экран запланирован в следующей итерации (книговыдача / инвентаризация с ТСД / дашборды). Структура — по SCREENMAP_web-staff." />
      </div>
    );
  }

  Object.assign(window, { StaffDesktop, CatalogingWorksheet, StaffStub });
})();
