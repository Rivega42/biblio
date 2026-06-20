/* global React */
/* Live reader app — design-system components wired to the P0 backend (real IBIS data).
   Flow: guest auth -> search (terms autocomplete) -> results -> record (cover/holdings) ->
   reader login -> order. EK(UI) maps to IBIS(server). */
(function () {
  const NS = window.DesignSystem_d9a584;
  const API = window.IrbisAPI;
  const { Button, Icon, SearchBar, ResultCard, StatusBadge, PftBlock, Pagination,
          EmptyState, ToastViewport } = NS;
  const DB = "IBIS";
  const PREFIXES = [
    { code: "K", label: "Ключевые слова" }, { code: "A", label: "Автор" },
    { code: "T", label: "Заглавие" }, { code: "V", label: "Вид документа" },
  ];
  const esc = (s) => (s || "").replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
  const LANG = { rus: "русский", eng: "английский", fre: "французский", ger: "немецкий", ita: "итальянский", spa: "испанский", lat: "латинский", chi: "китайский", jpn: "японский", ukr: "украинский" };

  function App() {
    const [ready, setReady] = React.useState(false);
    const [server, setServer] = React.useState(null);
    const [theme, setTheme] = React.useState("theatrical");
    const [a11y, setA11y] = React.useState(false);
    const [prefix, setPrefix] = React.useState("K");
    const [q, setQ] = React.useState("Android");
    const [sug, setSug] = React.useState([]);
    const [items, setItems] = React.useState([]);
    const [total, setTotal] = React.useState(0);
    const [page, setPage] = React.useState(1);
    const [loading, setLoading] = React.useState(false);
    const [rec, setRec] = React.useState(null);
    const [toasts, setToasts] = React.useState([]);
    const [account, setAccount] = React.useState({ loggedIn: false });
    const [loginOpen, setLoginOpen] = React.useState(false);
    const [showRaw, setShowRaw] = React.useState(false);
    const pageSize = 10;
    const tRef = React.useRef(null);

    const toast = (t) => {
      const id = Math.random();
      setToasts((x) => [...x, { ...t, id }]);
      setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), 4000);
    };

    React.useEffect(() => {
      (async () => {
        await API.initGuest();
        const h = await API.health();
        setServer(h.json && h.json.data);
        setReady(true);
        runSearch("K", "Android", 1);
      })();
    }, []);

    async function runSearch(px, query, pg) {
      px = px || prefix; query = query != null ? query : q; pg = pg || 1;
      if (!query.trim()) return;
      setLoading(true); setRec(null); setSug([]); setPage(pg);
      const r = await API.search(px, query, pg, pageSize);
      if (r.json && r.json.ok) { setItems(r.json.data.items); setTotal(r.json.data.total); }
      else { toast({ variant: "error", title: "Каталог недоступен", message: "Повторите попытку позже." }); setItems([]); setTotal(0); }
      setLoading(false);
    }

    function onQuery(v) {
      setQ(v);
      clearTimeout(tRef.current);
      if (v.trim().length < 2) { setSug([]); return; }
      tRef.current = setTimeout(async () => {
        const r = await API.terms(prefix + "=" + v.toUpperCase(), 8);
        if (r.json && r.json.ok) {
          setSug(r.json.data.terms
            .filter((t) => t.term.indexOf(prefix + "=") === 0)
            .map((t) => ({ term: t.term.slice(prefix.length + 1), count: t.count })));
        }
      }, 200);
    }

    async function openRecord(mfn) {
      setLoading(true);
      const r = await API.record(DB, mfn);
      setLoading(false);
      if (r.json && r.json.ok) { setRec(r.json.data); window.scrollTo(0, 0); }
    }

    async function order(mfn) {
      const r = await API.order(DB, mfn);
      if (r.status === 200) toast({ variant: "success", title: "Заказ принят", message: "Экземпляр поставлен в очередь выдачи." });
      else if (r.status === 401 || r.status === 403) { toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету, чтобы заказать." }); setLoginOpen(true); }
      else toast({ variant: "error", title: "Не удалось заказать", message: "Повторите попытку позже." });
    }

    async function doLogin(ticket) {
      const r = await API.loginReader(ticket);
      if (r.status === 200) { setAccount({ loggedIn: true, ticket }); setLoginOpen(false); toast({ variant: "success", title: "Вы вошли", message: "Билет № " + ticket }); }
      else toast({ variant: "warning", title: "Билет не найден", message: "Проверьте номер читательского билета." });
    }

    function recView(d) {
      const sub = (f, c) => (f.subfields[c] || f.subfields[c.toLowerCase()] || f.subfields[c.toUpperCase()] || "");
      const F = (tag) => d.fields.filter((x) => x.tag === tag);
      const F1 = (tag) => F(tag)[0];

      // авторы 700/701/702 -> "Фамилия, Имя"
      const authors = ["700", "701", "702"].flatMap(F).map((f) => {
        const s = sub(f, "A"), g = sub(f, "G") || sub(f, "B");
        return (s + (g ? ", " + g : "")).trim();
      }).filter(Boolean);
      // организации-авторы 710/711
      const orgs = ["710", "711"].flatMap(F).map((f) => sub(f, "A")).filter(Boolean);

      const imprint = (() => { const f = F1("210"); if (!f) return ""; const a = sub(f, "A"), c = sub(f, "C"), y = sub(f, "D"); return [a, c].filter(Boolean).join(" : ") + (y ? (a || c ? ", " : "") + y : ""); })();
      const volume = (() => { const f = F1("215"); if (!f) return ""; return [sub(f, "A"), sub(f, "C"), sub(f, "E")].filter(Boolean).join(" ; "); })();
      const isbn = (() => { const f = F1("10"); return f ? sub(f, "A") : ""; })();
      const langCode = (() => { const f = F1("101"); return f ? (sub(f, "A") || f.value) : ""; })();
      const lang = LANG[langCode] || langCode;
      const udk = (F1("675") && sub(F1("675"), "A")) || (F1("675") || {}).value || "";
      const note = (F1("331") && sub(F1("331"), "A")) || (F1("330") && sub(F1("330"), "A")) || (F1("300") || {}).value || "";

      const meta = [
        { label: "Авторы", value: authors.concat(orgs).join("; ") },
        { label: "Выходные данные", value: imprint },
        { label: "Объём", value: volume },
        { label: "ISBN", value: isbn },
        { label: "Язык", value: lang },
        { label: "УДК", value: udk },
        { label: "Примечание", value: note },
      ].filter((r) => r.value);

      const subjects = F("606").map((f) => [sub(f, "A"), sub(f, "B"), sub(f, "C"), sub(f, "D")].filter(Boolean).join(" — ")).filter(Boolean);
      const holds = F("910").map((h) => ({ loc: sub(h, "D") || "Фонд", inv: sub(h, "B"), st: sub(h, "A") }));
      const files = ["951", "955"].flatMap(F).map((f) => sub(f, "A") || sub(f, "T")).filter(Boolean);
      const rawRows = d.fields.map((x) =>
        `<tr><td style="color:var(--text-subtle);font-family:var(--font-mono);padding-right:12px;vertical-align:top">${x.tag}</td><td style="font-family:var(--font-mono);font-size:12px">${esc(x.value)}</td></tr>`).join("");
      return { brief: d.brief || "", meta, subjects, holds, files, rawRows };
    }

    const rootTheme = a11y ? "a11y" : (theme === "working" ? undefined : theme);
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const hbtn = (active) => ({ background: active ? "rgba(255,255,255,.25)" : "transparent", color: "#fff", border: "1px solid rgba(255,255,255,.45)", borderRadius: 8, padding: "5px 10px", cursor: "pointer", fontSize: "var(--text-xs)" });

    if (!ready) return <div style={{ padding: 40, color: "var(--text-subtle)" }}>Загрузка каталога…</div>;

    return (
      <div data-theme={rootTheme} style={{ minHeight: "100vh", background: "var(--bg-page)", color: "var(--text-body)", display: "flex", flexDirection: "column" }}>
        <header style={{ background: "var(--accent)", color: "#fff", padding: "12px 20px", display: "flex", alignItems: "center", gap: 12 }}>
          <Icon name="book" size={22} />
          <b>ИРБИС-Веб · каталог</b>
          <span style={{ opacity: .85, fontSize: "var(--text-xs)" }}>живые данные · ИРБИС {server && server.version} · база {DB}</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button onClick={() => { setA11y(false); setTheme("working"); }} style={hbtn(theme === "working" && !a11y)}>Рабочая</button>
            <button onClick={() => { setA11y(false); setTheme("theatrical"); }} style={hbtn(theme === "theatrical" && !a11y)}>Театр</button>
            <button onClick={() => setA11y((v) => !v)} style={hbtn(a11y)}>A11y</button>
            <button onClick={() => account.loggedIn ? setAccount({ loggedIn: false }) : setLoginOpen(true)} style={hbtn(false)}>{account.loggedIn ? "Выйти" : "Вход"}</button>
          </div>
        </header>

        <main style={{ flex: 1, maxWidth: "var(--container-max, 1100px)", width: "100%", margin: "0 auto", padding: "20px", boxSizing: "border-box" }}>
          {!rec && (
            <React.Fragment>
              <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                <select value={prefix} onChange={(e) => setPrefix(e.target.value)} style={{ padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)" }}>
                  {PREFIXES.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
                </select>
                <div style={{ flex: 1 }}>
                  <SearchBar value={q} onChange={onQuery} onSearch={(v) => runSearch(prefix, v, 1)}
                    suggestions={sug} onPickSuggestion={(s) => { const term = typeof s === "string" ? s : s.term; setQ(term); runSearch(prefix, term, 1); }}
                    placeholder="Поиск по каталогу" buttonLabel="Найти" />
                </div>
              </div>

              {loading ? <div style={{ color: "var(--text-subtle)" }}>Поиск…</div> :
                total === 0 ? <EmptyState icon="search" title="Ничего не найдено" description="Измените запрос или область поиска." /> :
                  <React.Fragment>
                    <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", margin: "4px 0 10px" }}>Найдено: {total} · страница {page} из {pageCount}</div>
                    {items.map((it) => <ResultCard key={it.mfn} item={it} dbTag="Книги" typeIcon="book" onOpen={() => openRecord(it.mfn)} />)}
                    <div style={{ marginTop: 14 }}><Pagination page={page} pageCount={pageCount} total={total} onPage={(p) => runSearch(prefix, q, p)} /></div>
                  </React.Fragment>}
            </React.Fragment>
          )}

          {rec && (() => {
            const v = recView(rec);
            const lbl = { fontWeight: 600, fontSize: "var(--text-sm)", margin: "18px 0 8px" };
            return (
              <div>
                <Button iconLeft="arrow-left" onClick={() => { setRec(null); setShowRaw(false); }}>К результатам</Button>
                <div style={{ display: "flex", gap: 24, marginTop: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
                  {rec.hasCover && <img alt="обложка" src={API.coverUrl(DB, rec.mfn)} onError={(e) => { e.target.style.display = "none"; }} style={{ width: 180, borderRadius: 10, border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)" }} />}
                  <div style={{ flex: 1, minWidth: 300 }}>
                    {/* заголовок — серверное БО (PFT) */}
                    <h2 style={{ fontFamily: "var(--font-serif, inherit)", fontSize: "var(--text-2xl, 1.5rem)", lineHeight: 1.3, margin: "2px 0 4px" }}>{v.brief}</h2>

                    {/* поля с подписями (не сырой MARC) */}
                    {v.meta.length > 0 && (
                      <dl style={{ display: "grid", gridTemplateColumns: "minmax(120px,160px) 1fr", gap: "6px 14px", margin: "14px 0 0", fontSize: "var(--text-sm)" }}>
                        {v.meta.map((m, i) => (
                          <React.Fragment key={i}>
                            <dt style={{ color: "var(--text-subtle)" }}>{m.label}</dt>
                            <dd style={{ margin: 0 }}>{m.value}</dd>
                          </React.Fragment>
                        ))}
                      </dl>
                    )}

                    {v.subjects.length > 0 && <>
                      <div style={lbl}>Темы и рубрики</div>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {v.subjects.map((s, i) => <span key={i} title="Искать по рубрике" onClick={() => { setPrefix("K"); setQ(s.split(" — ")[0]); runSearch("K", s.split(" — ")[0], 1); }} style={{ cursor: "pointer", background: "var(--accent-weak, #eef2f7)", color: "var(--accent)", padding: "3px 11px", borderRadius: 999, fontSize: "var(--text-xs)" }}>{s}</span>)}
                      </div>
                    </>}

                    {v.files.length > 0 && <>
                      <div style={lbl}>Электронная версия</div>
                      {v.files.map((f, i) => <div key={i} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}><Icon name="file-text" size={15} />{f}<span style={{ fontSize: "var(--text-xs)" }}>· документ pdf-формата</span></div>)}
                    </>}

                    <div style={lbl}>Экземпляры</div>
                    {v.holds.length ?
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}><tbody>
                        {v.holds.map((h, i) => <tr key={i}><td style={{ padding: "4px 0" }}>{h.loc}</td><td style={{ fontFamily: "var(--font-mono)" }}>{h.inv}</td><td style={{ textAlign: "right" }}><StatusBadge status={h.st === "0" || h.st === "" ? "available" : "issued"} dot /></td></tr>)}
                      </tbody></table> :
                      <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Сведения об экземплярах в записи отсутствуют.</div>}

                    <div style={{ marginTop: 20, display: "flex", gap: 10, alignItems: "center" }}>
                      <Button iconLeft="bookmark" onClick={() => order(rec.mfn)}>Заказать</Button>
                      <button onClick={() => setShowRaw((x) => !x)} style={{ background: "none", border: "none", color: "var(--text-subtle)", cursor: "pointer", fontSize: "var(--text-xs)" }}>
                        {showRaw ? "Скрыть" : "Показать"} все поля (MARC)
                      </button>
                    </div>

                    {showRaw && <div style={{ marginTop: 12, borderTop: "1px solid var(--border-subtle)", paddingTop: 8 }} dangerouslySetInnerHTML={{ __html: `<table style="border-collapse:collapse;width:100%">${v.rawRows}</table>` }} />}
                  </div>
                </div>
              </div>
            );
          })()}
        </main>

        <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 20px", fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "flex", gap: 10, alignItems: "center" }}>
          <Icon name="globe" size={14} />
          <span>Данные читаются с живого сервера ИРБИС64 (база {DB}). Демонстрационные данные обезличены.</span>
        </footer>

        {loginOpen && <LoginOverlay onClose={() => setLoginOpen(false)} onSubmit={doLogin} />}
        <ToastViewport toasts={toasts} onDismiss={(id) => setToasts((x) => x.filter((y) => y.id !== id))} />
      </div>
    );
  }

  function LoginOverlay({ onClose, onSubmit }) {
    const [t, setT] = React.useState("");
    return (
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
        <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--surface-card, #fff)", color: "var(--text-body)", borderRadius: 16, padding: 22, width: 320, boxShadow: "var(--shadow-lg, 0 20px 50px rgba(0,0,0,.25))" }}>
          <div style={{ fontWeight: 600, fontSize: "var(--text-lg)", marginBottom: 8 }}>Вход в личный кабинет</div>
          <p style={{ margin: "0 0 12px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Войдите по номеру читательского билета.</p>
          <input value={t} onChange={(e) => setT(e.target.value)} placeholder="Номер билета"
            onKeyDown={(e) => { if (e.key === "Enter") onSubmit(t); }}
            style={{ width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", marginBottom: 12 }} />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <NS.Button variant="ghost" onClick={onClose}>Отмена</NS.Button>
            <NS.Button onClick={() => onSubmit(t)}>Войти</NS.Button>
          </div>
        </div>
      </div>
    );
  }

  window.IrbisLiveApp = App;
})();
