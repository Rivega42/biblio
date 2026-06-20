/* global React */
const NS = window.DesignSystem_d9a584;

function Brand({ onClick, library }) {
  const lib = library || { monogram: "ЭК", short: "Электронный каталог", tagline: "каталог" };
  return (
    <button type="button" onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 11, background: "none", border: "none",
      cursor: "pointer", padding: 0, color: "var(--accent)", textAlign: "left",
    }} aria-label={lib.short + " — на главную"}>
      <span style={{
        width: 40, height: 40, borderRadius: "var(--radius-md)", background: "var(--accent)",
        color: "var(--accent-fg)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none",
        fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 16, letterSpacing: ".02em",
      }}>{lib.monogram}</span>
      <span style={{ lineHeight: 1.12, maxWidth: 280 }}>
        <span style={{ display: "block", fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15.5, color: "var(--text-strong)",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lib.short}</span>
        <span style={{ display: "block", fontSize: 10.5, letterSpacing: ".14em", textTransform: "uppercase", color: "var(--text-subtle)", fontWeight: 600 }}>{lib.tagline}</span>
      </span>
    </button>
  );
}

function LibraryPicker({ libraries, current, onPick }) {
  const { Icon } = NS;
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  return (
    <div style={{ position: "relative" }} ref={ref}>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-label="Сменить библиотеку (демонстрация скинов)" title="Демонстрация: библиотека и её скин"
        style={{ display: "inline-flex", alignItems: "center", gap: 5, border: "1px solid var(--border-default)", background: "var(--surface-card)",
          color: "var(--text-muted)", borderRadius: "var(--radius-pill)", padding: "6px 10px", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-xs)", fontWeight: 600 }}>
        <Icon name="settings" size={14} /> Скин
      </button>
      {open && (
        <div role="menu" style={{ position: "absolute", top: "calc(100% + 8px)", left: 0, width: 320, zIndex: "var(--z-overlay)",
          background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", padding: "var(--space-3)" }}>
          <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, padding: "4px 8px 8px" }}>Библиотека и её скин</div>
          {libraries.map((lib) => {
            const on = lib.id === current;
            return (
              <button key={lib.id} type="button" onClick={() => { onPick(lib.id); setOpen(false); }} style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%", textAlign: "left", cursor: "pointer",
                border: "1px solid " + (on ? "var(--accent-weak-border)" : "transparent"), background: on ? "var(--accent-weak)" : "transparent",
                borderRadius: "var(--radius-sm)", padding: "9px 10px", fontFamily: "var(--font-ui)",
              }}>
                <span data-theme={lib.theme === "working" ? undefined : lib.theme} style={{ width: 30, height: 30, borderRadius: "var(--radius-sm)", background: "var(--accent)", color: "var(--accent-fg)",
                  display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 12 }}>{lib.monogram}</span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: "block", fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lib.short}</span>
                  <span style={{ display: "block", fontSize: "var(--text-2xs)", color: "var(--text-subtle)" }}>скин: {lib.theme}</span>
                </span>
                {on && <Icon name="check" size={16} style={{ color: "var(--accent)" }} />}
              </button>
            );
          })}
          <div style={{ fontSize: "var(--text-2xs)", color: "var(--text-subtle)", padding: "6px 8px 2px", lineHeight: 1.4 }}>
            Скин и название настраиваются под учреждение декларативно (§9). Пользователь может переопределить тему в меню «Доступность и тема».
          </div>
        </div>
      )}
    </div>
  );
}

function AccessibilityMenu({ theme, setTheme, a11y, setA11y, noImg, setNoImg }) {
  const { IconButton, Switch, Icon } = NS;
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const seg = (val, label, icon) => (
    <button type="button" onClick={() => setTheme(val)} aria-pressed={theme === val} style={{
      display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
      padding: "9px 8px", borderRadius: "var(--radius-sm)", cursor: "pointer",
      border: "1px solid " + (theme === val ? "var(--accent)" : "var(--border-default)"),
      background: theme === val ? "var(--accent-weak)" : "var(--surface-card)",
      color: theme === val ? "var(--accent-press)" : "var(--text-muted)",
      fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600,
    }}>
      <Icon name={icon} size={16} /> {label}
    </button>
  );

  return (
    <div style={{ position: "relative" }} ref={ref}>
      <IconButton icon="accessibility" label="Доступность и тема" variant={open ? "accent" : "outline"} onClick={() => setOpen((o) => !o)} />
      {open && (
        <div role="dialog" aria-label="Доступность и тема" style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0, width: 270, zIndex: "var(--z-overlay)",
          background: "var(--surface-card)", border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", padding: "var(--space-4)",
          display: "flex", flexDirection: "column", gap: "var(--space-4)", fontFamily: "var(--font-ui)",
        }}>
          <div>
            <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, marginBottom: 8 }}>Светлые темы</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {seg("working", "Бумага", "sun")}
              {seg("azure", "Лазурь", "globe")}
              {seg("pine", "Хвоя", "book")}
              {seg("theatrical", "Театр", "book-open")}
            </div>
            <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, margin: "12px 0 8px" }}>Тёмная и праздничные</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              {seg("dark", "Тёмная", "moon")}
              {seg("newyear", "Новый год", "snowflake")}
              {seg("march8", "8 марта", "flower")}
            </div>
            {(theme === "newyear" || theme === "march8") && (
              <div style={{ marginTop: 8, fontSize: "var(--text-2xs)", color: "var(--text-subtle)", lineHeight: 1.4 }}>
                Праздничный скин со сценическими эффектами. Движение отключается системной настройкой «уменьшить движение».
              </div>
            )}
          </div>
          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700 }}>Доступность (ГОСТ Р 52872-2019)</div>
            <Switch label="Высокий контраст и крупный текст" checked={a11y} onChange={(e) => setA11y(e.target.checked)} />
            <Switch label="Без изображений (только текст)" checked={noImg} onChange={(e) => setNoImg(e.target.checked)} />
          </div>
        </div>
      )}
    </div>
  );
}

function ContextSwitch({ context, setContext }) {
  const { Icon } = NS;
  const opts = [
    { id: "reader", label: "Читатель", icon: "book-open" },
    { id: "staff", label: "Сотрудник", icon: "briefcase" },
  ];
  return (
    <div style={{ display: "inline-flex", border: "1px solid var(--border-default)", borderRadius: "var(--radius-pill)", overflow: "hidden", background: "var(--surface-card)" }} role="group" aria-label="Контекст входа">
      {opts.map((o) => {
        const on = context === o.id;
        return (
          <button key={o.id} type="button" onClick={() => setContext(o.id)} aria-pressed={on} style={{
            display: "inline-flex", alignItems: "center", gap: 6, border: "none", cursor: "pointer",
            padding: "7px 14px", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600,
            background: on ? "var(--accent)" : "transparent", color: on ? "var(--accent-fg)" : "var(--text-muted)",
          }}>
            <Icon name={o.icon} size={15} /> {o.label}
          </button>
        );
      })}
    </div>
  );
}

function TopBar(props) {
  const { Button, Badge, Icon } = NS;
  const { onHome, onAccount, account, theme, setTheme, a11y, setA11y, noImg, setNoImg, currentDb, multiBase, context, setContext, library, libraries, onPickLibrary } = props;
  return (
    <header style={{
      position: "sticky", top: 0, zIndex: "var(--z-sticky)", background: "var(--surface-card)",
      borderBottom: "1px solid var(--border-default)",
    }}>
      <div style={{
        maxWidth: "var(--container-max)", margin: "0 auto", padding: "10px var(--space-6)",
        display: "flex", alignItems: "center", gap: "var(--space-4)",
      }}>
        <Brand onClick={onHome} library={library} />
        <LibraryPicker libraries={libraries} current={library ? library.id : null} onPick={onPickLibrary} />
        {multiBase > 0 ? (
          <span style={{
            display: "flex", alignItems: "center", gap: 7, marginLeft: 4, padding: "6px 12px",
            border: "1px solid var(--accent-weak-border)", borderRadius: "var(--radius-pill)",
            background: "var(--accent-weak)", color: "var(--accent-press)",
            fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600,
          }}>
            <Icon name="layers" size={15} /> {multiBase} базы
          </span>
        ) : currentDb && (
          <span style={{
            display: "flex", alignItems: "center", gap: 7, marginLeft: 4, padding: "6px 12px",
            border: "1px solid var(--border-default)", borderRadius: "var(--radius-pill)",
            background: "var(--surface-sunken)", color: "var(--text-muted)",
            fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600,
          }}>
            <Icon name={currentDb.icon} size={15} /> {currentDb.short || currentDb.name}
          </span>
        )}
        <div style={{ flex: 1 }} />
        <ContextSwitch context={context} setContext={setContext} />
        <AccessibilityMenu theme={theme} setTheme={setTheme} a11y={a11y} setA11y={setA11y} noImg={noImg} setNoImg={setNoImg} />
        {context === "staff" ? (
          <Button variant="secondary" iconLeft="briefcase" onClick={onHome}>Рабочий стол</Button>
        ) : account.loggedIn ? (
          <Button variant="secondary" iconLeft="user" onClick={onAccount}>
            Билет {account.ticket} <Badge variant="accent" count style={{ marginLeft: 6 }}>{account.orders.length}</Badge>
          </Button>
        ) : (
          <Button iconLeft="log-in" onClick={onAccount}>Вход в ЛК</Button>
        )}
      </div>
    </header>
  );
}

Object.assign(window, { TopBar, Brand });
