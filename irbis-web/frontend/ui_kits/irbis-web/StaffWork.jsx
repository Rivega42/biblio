/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, Badge, Input, StatusBadge, Tabs, Alert, EmptyState } = NS;

  function Back({ onBack }) {
    return (
      <button type="button" onClick={onBack} style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", fontWeight: 600, padding: 0, marginBottom: "var(--space-4)" }}>
        <Icon name="arrow-left" size={17} /> К рабочему столу
      </button>
    );
  }
  function H1({ children, sub }) {
    return (
      <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)", marginBottom: "var(--space-5)", flexWrap: "wrap" }}>
        <h1 style={{ fontSize: "var(--text-2xl)" }}>{children}</h1>
        {sub && <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>{sub}</span>}
      </div>
    );
  }
  const Card = ({ children, style }) => <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)", ...style }}>{children}</div>;

  // ===== Книговыдача: выдача/возврат, очередь, бронеполка =====
  function Circulation({ data, onBack, onToast }) {
    const [tab, setTab] = React.useState("desk");
    const [scan, setScan] = React.useState("");
    const [reader, setReader] = React.useState(null);
    const r = data.reader;

    return (
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        <Back onBack={onBack} />
        <H1 sub="сканер / RFID · ячеистое хранение">Книговыдача</H1>
        <Tabs value={tab} onChange={setTab} tabs={[
          { id: "desk", label: "Выдача / возврат" },
          { id: "queue", label: "Очередь заказов", count: data.queue.length },
          { id: "shelf", label: "Бронеполка", count: data.shelf.length },
        ]} />

        <div style={{ marginTop: "var(--space-5)" }}>
          {tab === "desk" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-5)" }}>
              <Card>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-3)" }}>
                  <Icon name="scan-line" size={18} style={{ color: "var(--accent)" }} /><b style={{ color: "var(--text-strong)" }}>Билет читателя</b>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <div style={{ flex: 1 }}><Input size="sm" iconLeft="scan-line" placeholder="Сканируйте билет (00012345)" value={scan} onChange={(e) => setScan(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setReader(r)} /></div>
                  <Button size="sm" onClick={() => setReader(r)}>Найти</Button>
                </div>
                {reader && (
                  <div style={{ marginTop: "var(--space-4)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", paddingBottom: "var(--space-3)", borderBottom: "1px solid var(--border-subtle)" }}>
                      <span style={{ width: 40, height: 40, borderRadius: "var(--radius-round)", background: "var(--accent-weak)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><Icon name="user" size={20} /></span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, color: "var(--text-strong)" }}>{reader.display}</div>
                        <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{reader.category} · билет № {reader.ticket} · {reader.valid}</div>
                      </div>
                      {reader.overdue > 0 && <Badge variant="warning">просрочка: {reader.overdue}</Badge>}
                    </div>
                    <div style={{ marginTop: "var(--space-3)", display: "flex", flexDirection: "column", gap: 6 }}>
                      {reader.items.map((it) => (
                        <div key={it.inv} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "var(--text-sm)" }}>
                          <Icon name="book" size={15} style={{ color: "var(--text-subtle)", flex: "none" }} />
                          <span style={{ flex: 1, color: "var(--text-body)" }}>{it.title}</span>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>{it.inv}</span>
                          {it.status === "overdue" ? <Badge variant="danger">просрочено</Badge> : <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>до {it.due}</span>}
                          <Button size="sm" variant="ghost" onClick={() => onToast({ variant: "success", title: "Возврат принят", message: it.title })}>Возврат</Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
              <Card>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-3)" }}>
                  <Icon name="package" size={18} style={{ color: "var(--accent)" }} /><b style={{ color: "var(--text-strong)" }}>Выдать экземпляр</b>
                </div>
                <div style={{ display: "flex", gap: 8, marginBottom: "var(--space-3)" }}>
                  <div style={{ flex: 1 }}><Input size="sm" iconLeft="scan-line" placeholder="Сканируйте инв. номер / RFID" /></div>
                  <Button size="sm" iconLeft="check" disabled={!reader} onClick={() => onToast({ variant: "success", title: "Выдано", message: reader ? reader.display : "" })}>Выдать</Button>
                </div>
                {!reader ? (
                  <Alert variant="info" title="Сначала найдите читателя">Слева сканируйте билет, затем экземпляр.</Alert>
                ) : (
                  <div style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>Читатель: <b style={{ color: "var(--text-strong)" }}>{reader.display}</b>. На руках: {reader.onHand}. Лимит не превышен.</div>
                )}
              </Card>
            </div>
          )}

          {tab === "queue" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {data.queue.map((q) => (
                <Card key={q.inv} style={{ padding: "var(--space-3) var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                  <Icon name={q.status === "ready" ? "check-circle" : "clock"} size={18} style={{ color: q.status === "ready" ? "var(--status-available-strong)" : "var(--status-issued)", flex: "none" }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{q.title}</div>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{q.reader} · билет {q.ticket} · {q.location} · от {q.placed}</div>
                  </div>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>{q.inv}</span>
                  {q.status === "ready" ? <Badge variant="success">на бронеполке</Badge> : (
                    <Button size="sm" variant="secondary" iconLeft="bookmark" onClick={() => onToast({ variant: "success", title: "На бронеполку", message: q.title })}>На полку</Button>
                  )}
                </Card>
              ))}
            </div>
          )}

          {tab === "shelf" && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "var(--space-3)" }}>
              {data.shelf.map((s) => (
                <Card key={s.cell} style={{ padding: "var(--space-4)", display: "flex", gap: "var(--space-3)", alignItems: "flex-start" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent)", background: "var(--accent-weak)", borderRadius: "var(--radius-sm)", padding: "4px 9px", flex: "none" }}>{s.cell}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{s.title}</div>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{s.reader} · бронь {s.hold}</div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ===== Инвентаризация с ТСД =====
  function Inventory({ data, onBack, onToast }) {
    const inv = data.inventory;
    const [scanned, setScanned] = React.useState([]);
    const [online, setOnline] = React.useState(true);
    const remaining = inv.expected.filter((e) => !scanned.includes(e.inv));
    const scanNext = () => { const next = remaining[0]; if (next) { setScanned((s) => s.concat([next.inv])); onToast({ variant: "success", title: "Сверено", message: next.inv + " · " + next.title }); } };
    const scanUnknown = () => onToast({ variant: "warning", title: "Не из этого ряда", message: "К-99999 — отметить как «обнаружен в другом месте»." });

    return (
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        <Back onBack={onBack} />
        <H1 sub={inv.session + " · " + inv.location}>Инвентаризация (ТСД)</H1>

        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "var(--space-6)", alignItems: "start" }}>
          {/* ТСД-панель: крупные элементы, офлайн-индикатор */}
          <div style={{ position: "sticky", top: 76, background: "var(--surface-card)", border: "2px solid var(--border-strong)", borderRadius: "var(--radius-xl)", padding: "var(--space-4)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-3)" }}>
              <Icon name="scan-line" size={20} style={{ color: "var(--accent)" }} />
              <b style={{ color: "var(--text-strong)" }}>Терминал сбора данных</b>
              <span style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: 5, fontSize: "var(--text-2xs)", fontWeight: 600, color: online ? "var(--status-available-strong)" : "var(--status-issued-strong)" }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: online ? "var(--status-available)" : "var(--status-issued)" }} />{online ? "Онлайн" : "Офлайн"}
              </span>
            </div>
            <div style={{ textAlign: "center", padding: "var(--space-5) 0", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", marginBottom: "var(--space-3)" }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 44, fontWeight: 800, color: "var(--text-strong)", lineHeight: 1 }}>{scanned.length}<span style={{ fontSize: 22, color: "var(--text-subtle)" }}> / {inv.expected.length}</span></div>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 4 }}>сверено в ряду</div>
            </div>
            <Button block size="lg" iconLeft="scan-line" disabled={remaining.length === 0} onClick={scanNext}>Сканировать экземпляр</Button>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <Button size="sm" variant="secondary" onClick={scanUnknown} style={{ flex: 1 }}>Чужой</Button>
              <Button size="sm" variant="ghost" onClick={() => setOnline((o) => !o)} style={{ flex: 1 }}>{online ? "Офлайн" : "Синхр."}</Button>
            </div>
            {!online && <div style={{ marginTop: 8, fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Сканы копятся локально; синхронизируются при подключении.</div>}
          </div>

          {/* Прогресс и расхождения */}
          <div>
            <Card style={{ marginBottom: "var(--space-4)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: "var(--text-sm)" }}>
                <span style={{ color: "var(--text-muted)" }}>Прогресс сверки ряда</span>
                <b style={{ color: "var(--text-strong)" }}>{Math.round(scanned.length / inv.expected.length * 100)}%</b>
              </div>
              <div style={{ height: 10, borderRadius: 5, background: "var(--surface-sunken)", overflow: "hidden" }}>
                <div style={{ height: "100%", width: (scanned.length / inv.expected.length * 100) + "%", background: "var(--accent)", transition: "width var(--dur) var(--ease-standard)" }} />
              </div>
              {remaining.length === 0 && <div style={{ marginTop: "var(--space-3)" }}><Button size="sm" iconLeft="file-text" onClick={() => onToast({ variant: "success", title: "Отчёт сформирован", message: "Расхождений не выявлено." })}>Сформировать отчёт</Button></div>}
            </Card>

            <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, marginBottom: 10 }}>Ожидается в ряду · не сверено: {remaining.length}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {inv.expected.map((e) => {
                const ok = scanned.includes(e.inv);
                return (
                  <div key={e.inv} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", background: ok ? "var(--status-available-bg)" : "var(--surface-card)", opacity: ok ? 1 : 0.92 }}>
                    <Icon name={ok ? "check-circle" : "clock"} size={17} style={{ color: ok ? "var(--status-available-strong)" : "var(--text-subtle)", flex: "none" }} />
                    <span style={{ flex: 1, fontSize: "var(--text-sm)", color: "var(--text-body)" }}>{e.title}</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>{e.inv}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ===== BI-дашборд =====
  function Dashboard({ data, onBack }) {
    const d = data.dashboard;
    const TONE = { available: "var(--status-available-strong)", issued: "var(--status-issued-strong)" };
    const maxV = Math.max(...d.monthly.map((x) => x.v));
    return (
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        <Back onBack={onBack} />
        <H1 sub="книговыдача · фонд · читатели">Аналитика</H1>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
          {d.kpis.map((k) => (
            <Card key={k.label} style={{ padding: "var(--space-4)" }}>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginBottom: 6 }}>{k.label}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-2xl)", fontWeight: 700, color: "var(--text-strong)" }}>{k.value}</span>
                <span style={{ fontSize: "var(--text-xs)", fontWeight: 600, color: TONE[k.tone] }}>{k.delta}</span>
              </div>
            </Card>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "var(--space-5)" }}>
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-4)" }}><Icon name="bar-chart" size={18} style={{ color: "var(--accent)" }} /><b style={{ color: "var(--text-strong)" }}>Выдачи по месяцам</b></div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--space-3)", height: 180 }}>
              {d.monthly.map((m) => (
                <div key={m.m} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <div style={{ width: "100%", height: (m.v / maxV * 150) + "px", background: "var(--accent)", borderRadius: "var(--radius-sm) var(--radius-sm) 0 0", opacity: 0.55 + 0.45 * (m.v / maxV) }} />
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{m.m}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-4)" }}><Icon name="trending-up" size={18} style={{ color: "var(--accent)" }} /><b style={{ color: "var(--text-strong)" }}>Доля выдач по базам</b></div>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              {d.topDb.map((t) => (
                <div key={t.label}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)", marginBottom: 4 }}>
                    <span style={{ color: "var(--text-body)" }}>{t.label}</span><b style={{ color: "var(--text-strong)" }}>{t.pct}%</b>
                  </div>
                  <div style={{ height: 8, borderRadius: 4, background: "var(--surface-sunken)", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: t.pct + "%", background: "var(--accent)" }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  Object.assign(window, { Circulation, Inventory, Dashboard });
})();
