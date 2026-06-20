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
    const [context, setContext] = React.useState("reader");
    const [staff, setStaff] = React.useState(null);          // {name, login, grants}
    const [staffRoute, setStaffRoute] = React.useState("desktop");
    const [staffLoginOpen, setStaffLoginOpen] = React.useState(false);
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

    function switchContext(c) {
      if (c === "staff" && !staff) { setStaffLoginOpen(true); return; }
      setContext(c); setRec(null);
    }
    async function doStaffLogin(login, password) {
      const r = await API.loginStaff(login, password);
      if (r.status === 200 && r.json && r.json.ok) {
        setStaff({ name: r.json.data.name, login: r.json.data.login, grants: r.json.data.grants || [] });
        setContext("staff"); setStaffRoute("desktop"); setStaffLoginOpen(false);
        toast({ variant: "success", title: "Вход выполнен", message: r.json.data.name || login });
      } else toast({ variant: "warning", title: "Неверный логин или пароль", message: "Проверьте учётные данные." });
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
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
            <div style={{ display: "flex", gap: 4, marginRight: 6, padding: 2, background: "rgba(255,255,255,.12)", borderRadius: 10 }}>
              <button onClick={() => switchContext("reader")} style={hbtn(context === "reader")}>Читатель</button>
              <button onClick={() => switchContext("staff")} style={hbtn(context === "staff")}>Сотрудник</button>
            </div>
            <button onClick={() => { setA11y(false); setTheme("working"); }} style={hbtn(theme === "working" && !a11y)}>Рабочая</button>
            <button onClick={() => { setA11y(false); setTheme("theatrical"); }} style={hbtn(theme === "theatrical" && !a11y)}>Театр</button>
            <button onClick={() => setA11y((v) => !v)} style={hbtn(a11y)}>A11y</button>
            {context === "reader" && <button onClick={() => account.loggedIn ? setAccount({ loggedIn: false }) : setLoginOpen(true)} style={hbtn(false)}>{account.loggedIn ? "Выйти" : "Вход"}</button>}
            {context === "staff" && staff && <button onClick={() => { setStaff(null); setContext("reader"); }} style={hbtn(false)}>Выйти ({staff.login})</button>}
          </div>
        </header>

        <main style={{ flex: 1, maxWidth: "var(--container-max, 1100px)", width: "100%", margin: "0 auto", padding: "20px", boxSizing: "border-box" }}>
          {context === "staff" ? (
            <StaffArea staff={staff} route={staffRoute} setRoute={setStaffRoute} toast={toast} />
          ) : (
          <React.Fragment>
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
          </React.Fragment>
          )}
        </main>

        <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "14px 20px", fontSize: "var(--text-xs)", color: "var(--text-subtle)", display: "flex", gap: 10, alignItems: "center" }}>
          <Icon name="globe" size={14} />
          <span>Данные читаются с живого сервера ИРБИС64 (база {DB}). Демонстрационные данные обезличены.</span>
        </footer>

        {loginOpen && <LoginOverlay onClose={() => setLoginOpen(false)} onSubmit={doLogin} />}
        {staffLoginOpen && <StaffLoginOverlay onClose={() => setStaffLoginOpen(false)} onSubmit={doStaffLogin} />}
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

  // ===================== Staff side (live) =====================
  const DOMAINS = [
    { id: "cataloging", label: "Каталогизация", icon: "book", grant: "record.write", desc: "Создание и правка библиографических записей", route: "cataloging" },
    { id: "circ", label: "Книговыдача", icon: "package", grant: "circ.issue", desc: "Выдача, возврат, очередь, бронеполка, ячейки", route: "stub" },
    { id: "acq", label: "Комплектование", icon: "archive", grant: "acq.receipt", desc: "Заказ, поступление, КСУ, списание", route: "stub" },
    { id: "inv", label: "Инвентаризация", icon: "scan-line", grant: "record.read", desc: "Сверка фонда с ТСД", route: "stub" },
    { id: "analytics", label: "Аналитика", icon: "bar-chart", grant: "record.read", desc: "BI-дашборды: выдачи, фонд, читатели", route: "stub" },
    { id: "admin", label: "Администрирование", icon: "sliders", grant: "admin.users", desc: "Учётки, гранты, роли, аудит", route: "stub" },
  ];
  const hasGrant = (grants, fn) => (grants || []).some((g) => g.function === fn);

  function emptyValues(wl) {
    const v = {};
    (wl || []).forEach((fd) => { v[fd.code] = fd.repeatable ? [] : (fd.subfields ? {} : ""); });
    return v;
  }
  function valuesToFields(wl, values) {
    const out = [];
    (wl || []).forEach((fd) => {
      const v = values[fd.code];
      const occs = fd.repeatable ? (Array.isArray(v) ? v : []) : [v];
      occs.forEach((occ) => {
        let str = "";
        if (fd.subfields) { if (occ && typeof occ === "object") str = fd.subfields.map((sf) => { const t = (occ[sf.code] || "").trim(); return t ? "^" + sf.code + t : ""; }).join(""); }
        else str = (occ || "").toString().trim();
        if (str) out.push({ tag: fd.code, value: str });
      });
    });
    return out;
  }
  function recordToValues(fields, wl) {
    const values = {};
    const pick = (f, c) => f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "";
    (wl || []).forEach((fd) => {
      const matches = fields.filter((f) => f.tag === fd.code);
      if (fd.subfields) {
        const toObj = (f) => { const o = {}; fd.subfields.forEach((sf) => { o[sf.code] = pick(f, sf.code); }); return o; };
        values[fd.code] = fd.repeatable ? matches.map(toObj) : (matches[0] ? toObj(matches[0]) : {});
      } else {
        const f = matches[0];
        values[fd.code] = f ? (f.text || f.value || "") : "";
      }
    });
    return values;
  }

  function StaffLoginOverlay({ onClose, onSubmit }) {
    const [l, setL] = React.useState("");
    const [p, setP] = React.useState("");
    const inp = { width: "100%", boxSizing: "border-box", padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border-strong, #cdd3da)", marginBottom: 10 };
    return (
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,16,14,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
        <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--surface-card, #fff)", color: "var(--text-body)", borderRadius: 16, padding: 22, width: 340, boxShadow: "var(--shadow-lg, 0 20px 50px rgba(0,0,0,.25))" }}>
          <div style={{ fontWeight: 600, fontSize: "var(--text-lg)", marginBottom: 8 }}>Вход сотрудника</div>
          <p style={{ margin: "0 0 12px", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>Доступ определяется грантами учётной записи.</p>
          <input value={l} onChange={(e) => setL(e.target.value)} placeholder="Логин" style={inp} />
          <input value={p} onChange={(e) => setP(e.target.value)} type="password" placeholder="Пароль"
            onKeyDown={(e) => { if (e.key === "Enter") onSubmit(l, p); }} style={inp} />
          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginBottom: 12 }}>демо: <b>admin / admin</b> · <b>librarian / librarian</b></div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <NS.Button variant="ghost" onClick={onClose}>Отмена</NS.Button>
            <NS.Button onClick={() => onSubmit(l, p)}>Войти</NS.Button>
          </div>
        </div>
      </div>
    );
  }

  function StaffArea({ staff, route, setRoute, toast }) {
    if (route === "cataloging") return <CatalogingWorksheet staff={staff} onBack={() => setRoute("desktop")} toast={toast} />;
    if (route && route.name === "stub") return <StaffStub title={route.title} onBack={() => setRoute("desktop")} />;
    return <StaffDesktop staff={staff} onOpen={(d) => setRoute(d.route === "cataloging" ? "cataloging" : { name: "stub", title: d.label })} />;
  }

  function StaffDesktop({ staff, onOpen }) {
    const tiles = DOMAINS.filter((d) => hasGrant(staff.grants, d.grant));
    return (
      <div>
        <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: "4px 0 2px" }}>Рабочий стол сотрудника</h2>
        <p style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", marginTop: 0 }}>{staff.name} · доступно задач: {tiles.length} — собрано <b>по грантам</b>, не «по АРМам».</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px,1fr))", gap: 14, marginTop: 14 }}>
          {tiles.map((d) => (
            <div key={d.id} onClick={() => onOpen(d)} style={{ cursor: "pointer", background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 16, display: "flex", gap: 12, alignItems: "flex-start" }}>
              <span style={{ background: "var(--accent-weak,#eef2f7)", color: "var(--accent)", borderRadius: 10, padding: 8, flex: "none" }}><Icon name={d.icon} size={22} /></span>
              <div>
                <div style={{ fontWeight: 600 }}>{d.label}</div>
                <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>{d.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>Показаны только разрешённые функции. Запись/удаление — под грантами уровня write/admin, действия пишутся в аудит.</div>
      </div>
    );
  }

  function StaffStub({ title, onBack }) {
    return (
      <div>
        <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
        <EmptyState icon="clock" title={title} description="Экран спроектирован в дизайн-системе (прототип). На живые данные подключается следующим шагом — здесь доступна каталогизация." />
      </div>
    );
  }

  function CatalogingWorksheet({ staff, onBack, toast }) {
    const SANDBOX = "WORK";
    const DF = NS.DynamicField;
    const [wl, setWl] = React.useState(null);
    const [values, setValues] = React.useState({});
    const [mfn, setMfn] = React.useState(0);
    const [openMfn, setOpenMfn] = React.useState("");
    const [saved, setSaved] = React.useState(null);
    const [errors, setErrors] = React.useState({});

    React.useEffect(() => { (async () => { const r = await API.worklist(SANDBOX); if (r.json && r.json.ok) { setWl(r.json.data.fields); setValues(emptyValues(r.json.data.fields)); } })(); }, []);

    const set = (code, val) => setValues((v) => ({ ...v, [code]: val }));
    const newRecord = () => { setValues(emptyValues(wl)); setMfn(0); setSaved(null); setErrors({}); };
    async function loadFromIbis() {
      const id = parseInt(openMfn, 10); if (!id) return;
      const r = await API.record("IBIS", id);
      if (r.json && r.json.ok) { setValues(recordToValues(r.json.data.fields, wl)); setMfn(0); setSaved(null); toast({ variant: "info", title: "Запись загружена в форму", message: "IBIS MFN " + id + " → сохранится в песочницу " + SANDBOX }); }
      else toast({ variant: "warning", title: "Не найдено", message: "Нет записи MFN " + id + " в IBIS." });
    }
    async function save() {
      const errs = {};
      (wl || []).forEach((fd) => { if (fd.required) { const ok = fd.subfields ? (values[fd.code] && Object.values(values[fd.code]).some(Boolean)) : !!values[fd.code]; if (!ok) errs[fd.code] = "Обязательное поле (ФЛК)"; } });
      setErrors(errs);
      if (Object.keys(errs).length) { toast({ variant: "warning", title: "Заполните обязательные поля", message: "Тип записи и Заглавие." }); return; }
      const fields = valuesToFields(wl, values);
      const r = await API.saveRecord(SANDBOX, mfn, fields);
      if (r.status === 200 && r.json && r.json.ok) { setSaved(r.json.data); setMfn(r.json.data.mfn); toast({ variant: "success", title: r.json.data.created ? "Запись создана" : "Запись обновлена", message: SANDBOX + " · MFN " + r.json.data.mfn }); }
      else if (r.status === 403) toast({ variant: "info", title: "Недостаточно прав", message: "Нужен грант record.write." });
      else toast({ variant: "error", title: "Не сохранено", message: "Повторите попытку." });
    }

    const tbtn = { padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-strong,#cdd3da)", background: "var(--surface-card,#fff)", color: "var(--text-body)" };
    return (
      <div>
        <Button iconLeft="arrow-left" onClick={onBack}>К рабочему столу</Button>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
          <h2 style={{ fontSize: "var(--text-2xl,1.5rem)", margin: 0 }}>Каталогизация</h2>
          <span style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>учебная база {SANDBOX} (песочница) · рабочий лист «Книга»</span>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "14px 0", flexWrap: "wrap" }}>
          <Button iconLeft="plus" onClick={newRecord}>Новая запись</Button>
          <span style={{ color: "var(--text-subtle)" }}>·</span>
          <input value={openMfn} onChange={(e) => setOpenMfn(e.target.value)} placeholder="MFN из IBIS" style={{ ...tbtn, width: 130 }} onKeyDown={(e) => { if (e.key === "Enter") loadFromIbis(); }} />
          <button onClick={loadFromIbis} style={tbtn}>Загрузить из IBIS</button>
          <span style={{ marginLeft: "auto", color: "var(--text-subtle)", fontSize: "var(--text-sm)" }}>{mfn ? "MFN " + mfn : "новая запись"}</span>
        </div>

        {!wl ? <div style={{ color: "var(--text-subtle)" }}>Загрузка рабочего листа…</div> : (
          <div style={{ background: "var(--surface-card,#fff)", border: "1px solid var(--border-subtle)", borderRadius: 12, padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
            {wl.map((fd) => (
              <div key={fd.code}>
                {DF ? <DF field={fd} value={values[fd.code]} onChange={(v) => set(fd.code, v)} error={errors[fd.code]} />
                  : <BasicField fd={fd} value={values[fd.code]} onChange={(v) => set(fd.code, v)} error={errors[fd.code]} />}
              </div>
            ))}
            <div style={{ display: "flex", gap: 10, alignItems: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
              <Button iconLeft="check-circle" onClick={save}>Сохранить запись</Button>
              {saved && <span style={{ color: "var(--accent)", fontSize: "var(--text-sm)" }}>✓ сохранено в {saved.db}, MFN {saved.mfn} (код {saved.returnCode})</span>}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Fallback editor if the bundled DynamicField is unavailable.
  function BasicField({ fd, value, onChange, error }) {
    const lab = { fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 4 };
    const inp = { width: "100%", boxSizing: "border-box", padding: "8px 11px", borderRadius: 8, border: "1px solid " + (error ? "var(--status-issued,#c66)" : "var(--border-strong,#cdd3da)") };
    if (fd.subfields && !fd.repeatable) {
      const occ = value || {};
      return <div><div style={lab}>{fd.label}{fd.required ? " *" : ""}</div>
        <div style={{ display: "grid", gap: 6 }}>{fd.subfields.map((sf) => <input key={sf.code} placeholder={sf.label + " (^" + sf.code + ")"} value={occ[sf.code] || ""} onChange={(e) => onChange({ ...occ, [sf.code]: e.target.value })} style={inp} />)}</div>
        {error && <div style={{ color: "var(--status-issued,#c66)", fontSize: "var(--text-xs)" }}>{error}</div>}</div>;
    }
    if (fd.type === "menu") {
      return <div><div style={lab}>{fd.label}{fd.required ? " *" : ""}</div>
        <select value={value || ""} onChange={(e) => onChange(e.target.value)} style={inp}><option value="">—</option>{(fd.options || []).map((o) => <option key={o} value={o}>{o}</option>)}</select></div>;
    }
    return <div><div style={lab}>{fd.label}</div><input value={value || ""} onChange={(e) => onChange(e.target.value)} style={inp} /></div>;
  }

  window.IrbisLiveApp = App;
})();
