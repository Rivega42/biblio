/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, Badge, SubjectTag, HoldingsTable, PftBlock, Alert, Tabs } = NS;

  const KIND_NOTE = { pdf: "документ pdf-формата", image: "изображение", djvu: "документ djvu-формата" };

  function SectionLabel({ children }) {
    return <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, marginBottom: "var(--space-3)" }}>{children}</div>;
  }

  // Сворачиваемый блок записи (§4, §10) — профили отображения.
  function Collapsible({ title, icon, defaultOpen = true, count, children }) {
    const [open, setOpen] = React.useState(defaultOpen);
    return (
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-3)", overflow: "hidden" }}>
        <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} style={{
          display: "flex", alignItems: "center", gap: "var(--space-3)", width: "100%", textAlign: "left",
          border: "none", background: "transparent", cursor: "pointer", padding: "var(--space-3) var(--space-4)", fontFamily: "var(--font-ui)",
        }}>
          {icon && <Icon name={icon} size={17} style={{ color: "var(--accent)", flex: "none" }} />}
          <span style={{ fontWeight: 700, color: "var(--text-strong)", fontSize: "var(--text-md)" }}>{title}</span>
          {count != null && <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>· {count}</span>}
          <Icon name="chevron-down" size={18} style={{ marginLeft: "auto", color: "var(--text-subtle)", transform: open ? "rotate(180deg)" : "none", transition: "transform var(--dur) var(--ease-standard)" }} />
        </button>
        {open && <div style={{ padding: "0 var(--space-4) var(--space-4)" }}>{children}</div>}
      </div>
    );
  }

  // Закладки записи: Экземпляры / Электронные версии / Сиглы (§4)
  function RecordTabs({ record, files, account, onOpenFile, onOrder }) {
    const tabsDef = [
      { id: "holdings", label: "Экземпляры", icon: "archive", count: record.holdings.length },
      { id: "files", label: "Электронные версии", icon: "file-text", count: files.length },
      { id: "sigla", label: "Сиглы хранения", icon: "map-pin", count: (record.sigla || []).length },
    ].filter((t) => t.count > 0 || t.id === "holdings");
    const [tab, setTab] = React.useState(tabsDef[0].id);
    return (
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
        <div style={{ padding: "var(--space-3) var(--space-4) 0" }}>
          <Tabs value={tab} onChange={setTab} tabs={tabsDef.map((t) => ({ id: t.id, label: t.label, count: t.count }))} />
        </div>
        <div style={{ padding: "var(--space-4)" }}>
          {tab === "holdings" && (record.holdings.length > 0
            ? <HoldingsTable holdings={record.holdings} onOrder={onOrder} />
            : <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", margin: 0 }}>Сведения об экземплярах отсутствуют.</p>)}
          {tab === "files" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {files.length > 0 ? files.map((f, i) => <FileRow key={i} file={f} account={account} onOpen={onOpenFile} />)
                : <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", margin: 0 }}>Электронных версий нет.</p>}
              {files.some((f) => f.requiresAuth && !account.loggedIn) && (
                <Alert variant="info" title="Часть материалов — по входу">Доступно в читальном зале или после входа по читательскому билету.</Alert>
              )}
            </div>
          )}
          {tab === "sigla" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {(record.sigla || []).map((s) => (
                <div key={s.code} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "10px 12px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", background: s.here ? "var(--accent-weak)" : "transparent" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "var(--text-sm)", color: s.here ? "var(--accent-press)" : "var(--text-strong)", minWidth: 64 }}>{s.code}</span>
                  <span style={{ flex: 1, fontSize: "var(--text-sm)", color: "var(--text-body)" }}>{s.name}</span>
                  {s.here && <Badge variant="accent">здесь</Badge>}
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>экз.: {s.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  function Cover({ tint, noImg, onOpen }) {
    return (
      <button type="button" onClick={onOpen} style={{
        width: "100%", aspectRatio: "3 / 4", borderRadius: "var(--radius-md)", overflow: "hidden",
        border: "1px solid var(--border-subtle)", cursor: onOpen ? "pointer" : "default", padding: 0,
        background: noImg ? "var(--surface-sunken)" : "hsl(" + (tint || 30) + " 32% 86%)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }} aria-label="Открыть изображение">
        <Icon name={noImg ? "file-text" : "image"} size={40} style={{ color: noImg ? "var(--text-subtle)" : "hsl(" + (tint || 30) + " 38% 42%)" }} />
      </button>
    );
  }

  // Кнопка просмотра файла (view-only). 955 раньше 951 — задаёт порядок в files.
  function FileRow({ file, account, onOpen }) {
    const locked = file.requiresAuth && !account.loggedIn;
    return (
      <button type="button" onClick={() => onOpen(file)} style={{
        display: "flex", alignItems: "center", gap: "var(--space-3)", width: "100%", textAlign: "left",
        background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-4)", cursor: "pointer", fontFamily: "var(--font-ui)",
      }}>
        <span style={{ width: 34, height: 34, borderRadius: "var(--radius-sm)", background: "var(--accent-weak)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
          <Icon name={file.kind === "image" ? "image" : "file-text"} size={18} />
        </span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <span style={{ display: "block", fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{file.label}</span>
          <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
            {KIND_NOTE[file.kind] || file.kind}{file.pages ? " · " + file.pages + " с." : ""} · поле {file.field} · только просмотр
          </span>
        </span>
        {locked ? <Badge variant="neutral">нужен вход</Badge> : <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--accent)", fontSize: "var(--text-sm)", fontWeight: 600 }}><Icon name="eye" size={16} /> Открыть</span>}
      </button>
    );
  }

  function RecordScreen(props) {
    const { record, db, onBack, onSubject, onOrder, onToggleMark, marked, account, noImg, onToast, onOpenFile, onFollowLink, pickFile } = props;
    const isImage = db.layout === "gallery";
    const links = record.links || {};
    const files = (record.files || []).slice().sort((a, b) => (a.priority || 9) - (b.priority || 9));
    const cover = pickFile(files.filter((f) => f.kind === "image"));

    return (
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
          <button type="button" onClick={onBack} style={{
            display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none",
            color: "var(--text-link)", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, padding: 0,
          }}>
            <Icon name="arrow-left" size={17} /> Назад к результатам
          </button>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginLeft: "auto" }}>
            <Icon name={db.icon} size={14} /> База: <b style={{ color: "var(--text-muted)", fontWeight: 600 }}>{db.name}</b>
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: isImage ? "240px 1fr" : "1fr", gap: "var(--space-8)", alignItems: "start" }}>
          {isImage && (
            <div style={{ position: "sticky", top: 76 }}>
              <Cover tint={record.tint} noImg={noImg} onOpen={cover ? () => onOpenFile(cover) : undefined} />
              <div style={{ marginTop: 8, fontSize: "var(--text-xs)", color: "var(--text-subtle)", textAlign: "center" }}>
                {noImg ? "Изображение скрыто (режим без изображений)" : (cover ? "Нажмите для просмотра" : "Превью")}
              </div>
            </div>
          )}

          <div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "var(--space-3)" }}>
              {(record.badges || []).map((b, i) => <Badge key={i} variant={b.variant}>{b.text}</Badge>)}
            </div>
            <h1 style={{ fontFamily: "var(--font-record-title)", fontSize: "var(--text-2xl)", marginBottom: "var(--space-2)" }}>{record.title}</h1>
            <div style={{ fontSize: "var(--text-md)", color: "var(--text-muted)", marginBottom: "var(--space-5)" }}>
              {record.author && record.author !== "—" ? record.author + " · " : ""}{record.imprint.publisher !== "—" ? record.imprint.publisher + ", " : ""}{record.imprint.year}
            </div>

            {/* Действия */}
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginBottom: "var(--space-6)" }}>
              {record.holdings && record.holdings.length > 0 && (
                <Button iconLeft="bookmark" onClick={onOrder}>Заказать / забронировать</Button>
              )}
              <Button variant="secondary" iconLeft={marked ? "bookmark-check" : "bookmark"} onClick={onToggleMark}>{marked ? "Отмечено" : "Отметить"}</Button>
              <Button variant="secondary" iconLeft="link" onClick={() => onToast({ variant: "info", title: "Ссылка скопирована", message: "Доступна внутри сети библиотеки." })}>Поделиться ссылкой</Button>
              {links.f481 && links.f481.length > 0 && (
                <Button variant="ghost" iconLeft="search" onClick={() => onSubject(record.title.split(":")[0])}>Поиск по связи (481)</Button>
              )}
            </div>

            {/* Связи 488 (Фонд↔Опись GUAR) и 390 (цветная ссылка на ЭК) */}
            {(links.f488 || links.f390) && (
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", marginBottom: "var(--space-6)" }}>
                {links.f488 && (
                  <button type="button" onClick={() => onFollowLink(links.f488)} style={{
                    display: "inline-flex", alignItems: "center", gap: 8, alignSelf: "flex-start",
                    background: "var(--surface-sunken)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)",
                    padding: "9px 14px", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-strong)",
                  }}>
                    <Icon name="archive" size={16} style={{ color: "var(--accent)" }} /> {links.f488.label} <Icon name="arrow-right" size={15} style={{ color: "var(--text-subtle)" }} />
                  </button>
                )}
                {links.f390 && (
                  <button type="button" onClick={() => onFollowLink(links.f390)} style={{
                    display: "inline-flex", alignItems: "center", gap: 7, alignSelf: "flex-start",
                    background: "none", border: "none", padding: 0, cursor: "pointer",
                    fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-link)",
                  }}>
                    <Icon name="external-link" size={15} /> {links.f390.label}
                  </button>
                )}
              </div>
            )}

            {/* PFT-блок — сворачиваемый */}
            <Collapsible title="Описание и аннотация" icon="file-text" defaultOpen>
              <PftBlock html={record.pftHtml} />
            </Collapsible>

            {/* Рубрики — сворачиваемые */}
            {record.subjects && record.subjects.length > 0 && (
              <Collapsible title="Предметные рубрики" icon="tag" count={record.subjects.length} defaultOpen>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {record.subjects.map((s) => <SubjectTag key={s} onClick={() => onSubject(s)}>{s}</SubjectTag>)}
                </div>
              </Collapsible>
            )}

            {/* Закладки: Экземпляры / Эл. версии / Сиглы */}
            <div style={{ marginTop: "var(--space-2)" }}>
              <RecordTabs record={record} files={files} account={account} onOpenFile={onOpenFile} onOrder={onOrder} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  Object.assign(window, { RecordScreen });
})();
