/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, Input, Select, Checkbox } = NS;

  const MONTHS = ["— месяц —", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"];
  const DAYS = ["— день —"].concat(Array.from({ length: 31 }, (_, i) => String(i + 1)));

  function FieldLabel({ children }) {
    return <label style={{ display: "block", fontSize: "var(--text-xs)", fontWeight: 600, color: "var(--text-muted)", marginBottom: 5 }}>{children}</label>;
  }

  function AreaHead({ icon, children }) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: "var(--space-3)" }}>
        <Icon name={icon} size={15} style={{ color: "var(--accent)" }} />
        <span style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700 }}>{children}</span>
      </div>
    );
  }

  // Конфиг-управляемая спецформа (§4–§7): рендерит виджеты из db.specialForm.
  function SpecialForm({ db, values, setValues, onSearch, onReset }) {
    const v = values || {};
    const set = (k, val) => setValues({ ...v, [k]: val });
    const fields = db.specialForm || [];

    const renderField = (f) => {
      switch (f.kind) {
        case "text":
          return (
            <div key={f.id}>
              <FieldLabel>{f.label}</FieldLabel>
              <Input size="sm" value={v[f.id] || ""} placeholder="значение" onChange={(e) => set(f.id, e.target.value)} />
            </div>
          );
        case "select":
          return (
            <div key={f.id}>
              <FieldLabel>{f.label}</FieldLabel>
              <Select size="sm" value={v[f.id] || f.options[0]} onChange={(e) => set(f.id, e.target.value)} options={f.options} />
            </div>
          );
        case "range":
          return (
            <div key={f.id}>
              <FieldLabel>{f.label}</FieldLabel>
              <div style={{ display: "flex", gap: 8 }}>
                <Input size="sm" placeholder={f.from || "с…"} value={v[f.id + ":from"] || ""} onChange={(e) => set(f.id + ":from", e.target.value)} />
                <Input size="sm" placeholder={f.to || "по…"} value={v[f.id + ":to"] || ""} onChange={(e) => set(f.id + ":to", e.target.value)} />
              </div>
            </div>
          );
        case "checkbox":
          return (
            <div key={f.id} style={{ display: "flex", alignItems: "center", paddingTop: 22 }}>
              <Checkbox label={f.label} checked={!!v[f.id]} onChange={(e) => set(f.id, e.target.checked)} />
            </div>
          );
        case "dateEvent":
          return (
            <div key={f.id} style={{ gridColumn: "1 / -1", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
              <AreaHead icon="calendar">{f.label} · логика «И»</AreaHead>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr", gap: "var(--space-3)" }}>
                <div><FieldLabel>Год</FieldLabel><Input size="sm" placeholder="напр. 1898" value={v[f.id + ":y"] || ""} onChange={(e) => set(f.id + ":y", e.target.value)} /></div>
                <div><FieldLabel>Месяц</FieldLabel><Select size="sm" value={v[f.id + ":m"] || MONTHS[0]} onChange={(e) => set(f.id + ":m", e.target.value)} options={MONTHS} /></div>
                <div><FieldLabel>День</FieldLabel><Select size="sm" value={v[f.id + ":d"] || DAYS[0]} onChange={(e) => set(f.id + ":d", e.target.value)} options={DAYS} /></div>
              </div>
            </div>
          );
        case "sourceArea":
          return (
            <div key={f.id} style={{ gridColumn: "1 / -1", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
              <AreaHead icon="book">{f.label}</AreaHead>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
                {f.fields.map((sf) => (
                  <div key={sf.id}><FieldLabel>{sf.label}</FieldLabel><Input size="sm" value={v[sf.id] || ""} onChange={(e) => set(sf.id, e.target.value)} /></div>
                ))}
              </div>
            </div>
          );
        case "roles":
          return (
            <div key={f.id} style={{ gridColumn: "1 / -1", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
              <AreaHead icon="drama">{f.label} · {f.fields.length} полей, комбинируются</AreaHead>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-3)" }}>
                {f.fields.map((r, i) => (
                  <div key={i}><FieldLabel>{r}</FieldLabel><Input size="sm" placeholder="—" value={v[f.id + ":" + i] || ""} onChange={(e) => set(f.id + ":" + i, e.target.value)} /></div>
                ))}
              </div>
            </div>
          );
        default:
          return null;
      }
    };

    return (
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)", marginBottom: "var(--space-4)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-4)" }}>
          <Icon name={db.icon} size={18} style={{ color: "var(--accent)" }} />
          <h2 style={{ fontSize: "var(--text-lg)" }}>{db.specialTitle || ("Поиск · " + db.name)}</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-3) var(--space-4)" }}>
          {fields.map(renderField)}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginTop: "var(--space-5)" }}>
          <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Поиск стартует по кнопке.</span>
          <div style={{ flex: 1 }} />
          <Button variant="secondary" size="lg" iconLeft="rotate-ccw" onClick={onReset}>Сброс</Button>
          <Button size="lg" iconLeft="search" onClick={onSearch}>Поиск</Button>
        </div>
      </div>
    );
  }

  Object.assign(window, { SpecialForm });
})();
