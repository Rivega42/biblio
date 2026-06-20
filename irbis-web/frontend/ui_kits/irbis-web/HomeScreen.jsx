/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Checkbox, Button } = NS;

  function ExampleChips({ items, onPick }) {
    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>Например:</span>
        {items.map((t) => (
          <button key={t} type="button" onClick={() => onPick(t)} style={{
            border: "1px solid var(--border-default)", background: "var(--surface-card)",
            color: "var(--text-body)", borderRadius: "var(--radius-pill)", padding: "5px 13px",
            cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)",
          }}>{t}</button>
        ))}
      </div>
    );
  }

  function PremiereBlock({ premieres, onOpen }) {
    return (
      <section style={{
        maxWidth: 720, margin: "0 auto", marginTop: "var(--space-12)",
        background: "var(--surface-card)", border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)", overflow: "hidden",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 18px", borderBottom: "1px solid var(--border-subtle)", color: "var(--accent)" }}>
          <Icon name="calendar-star" size={18} />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, color: "var(--text-strong)", fontSize: "var(--text-md)" }}>Календарь событий</span>
          <span style={{ marginLeft: "auto", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>из базы «Премьеры»</span>
        </div>
        {premieres.map((p) => (
          <button key={p.mfn} type="button" onClick={() => onOpen(p)} style={{
            display: "flex", alignItems: "center", gap: 14, width: "100%", padding: "13px 18px",
            border: "none", borderBottom: "1px solid var(--border-subtle)", background: "transparent",
            cursor: "pointer", textAlign: "left", fontFamily: "var(--font-ui)",
          }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--accent)", width: 130, flex: "none" }}>{p.year}</span>
            <span style={{ flex: 1 }}>
              <span style={{ display: "block", fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{p.title}</span>
              <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{p.author} · {p.fields[0].value}</span>
            </span>
            <Icon name="chevron-right" size={16} style={{ color: "var(--text-subtle)" }} />
          </button>
        ))}
      </section>
    );
  }

  function HomeScreen(props) {
    const { databases, groups, dbIds, setDbIds, query, setQuery, onSearch, onlyDigital, setOnlyDigital, formDb, suggestions, premieres, onOpenRecord, account, onLogin, library } = props;
    const examples = formDb ? ({
      EK: ["Чайка", "Чехов А. П.", "русская драматургия"],
      SKETCH: ["эскиз декорации", "Симов В. А.", "костюм"],
      GUAR: ["цензура", "Фонд 1", "1898"],
      TUAR: ["Чайка", "опера", "балет"],
      PLAY: ["Чайка", "комедия", "Чехов"],
    }[formDb.id] || []) : ["Чайка", "Чехов А. П."];
    const showDigital = formDb && formDb.simpleExtra;

    return (
      <div style={{ maxWidth: 920, margin: "0 auto", padding: "var(--space-16) var(--space-6) var(--space-12)" }}>
        <div style={{ textAlign: "center", marginBottom: "var(--space-8)" }}>
          {library && <div style={{ fontSize: "var(--text-xs)", fontWeight: 600, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--accent)", marginBottom: "var(--space-3)" }}>{library.name}</div>}
          <h1 style={{ fontSize: "var(--text-3xl)", marginBottom: "var(--space-3)" }}>Электронный каталог и Базы данных</h1>
          <p style={{ fontSize: "var(--text-md)", color: "var(--text-muted)", maxWidth: 580, margin: "0 auto" }}>
            {library && library.id === "spbgtb"
              ? "Профильная театрально-художественная библиотека: книги, периодика, эскизный фонд, архивные документы, пьесы, либретто и календарь премьер."
              : "Поиск по книгам, периодике, статьям, архивным и изобразительным материалам. Выберите базы и начните поиск."}
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", maxWidth: 720, margin: "0 auto" }}>
          <NS.DatabaseSelector databases={databases} groups={groups} value={dbIds} onChange={setDbIds} />
          <div>
            <label style={{ display: "block", fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)", marginBottom: 6 }}>Я ищу:</label>
            <NS.SearchBar
              value={query} onChange={setQuery} onSearch={onSearch}
              suggestions={suggestions} onPickSuggestion={(sug) => { setQuery(sug.term || sug); onSearch(sug.term || sug); }}
              buttonLabel="Поиск" onReset={() => { setQuery(""); setDbIds([]); }}
              placeholder={formDb ? ("в базе «" + formDb.name + "»…") : (dbIds.length ? ("поиск по " + dbIds.length + " базам…") : "сначала выберите базу…")}
            />
            {showDigital && (
              <div style={{ marginTop: 10 }}>
                <Checkbox label="Только с электронными версиями" checked={onlyDigital} onChange={(e) => setOnlyDigital(e.target.checked)} />
              </div>
            )}
          </div>
        </div>

        {examples.length > 0 && (
          <div style={{ marginTop: "var(--space-5)" }}>
            <ExampleChips items={examples} onPick={(t) => { setQuery(t); onSearch(t); }} />
          </div>
        )}

        {!account.loggedIn && (
          <div style={{ textAlign: "center", marginTop: "var(--space-6)" }}>
            <button type="button" onClick={onLogin} style={{ background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="log-in" size={16} /> Вход в Личный кабинет
            </button>
          </div>
        )}

        {premieres && premieres.length > 0 && <PremiereBlock premieres={premieres} onOpen={onOpenRecord} />}
      </div>
    );
  }

  Object.assign(window, { HomeScreen });
})();
