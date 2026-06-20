/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const D = window.IRBIS_DATA;
  const { ToastViewport, EmptyState, Button, Icon } = NS;
  const FileViewer = NS.FileViewer;

  const DBS = D.databases;
  const GROUPS = D.groups;
  const getDb = (id) => DBS.find((d) => d.id === id) || DBS[0];

  // Выбор файла для просмотра: приоритет поля 955 над 951 (§1.7).
  function pickFile(files) {
    if (!files || !files.length) return null;
    return files.slice().sort((a, b) => (a.priority || 9) - (b.priority || 9))[0];
  }

  function recordFor(item) {
    const dbId = item.sourceDb || item.db;
    if (D.records[item.mfn]) return D.records[item.mfn];
    return {
      mfn: item.mfn, db: dbId, title: item.title, author: item.author,
      imprint: { publisher: "—", year: item.year },
      badges: [{ variant: "neutral", text: item.docType }],
      tint: item.tint, recLevel: item.recLevel,
      pftHtml: "<p><b>" + item.title + "</b></p><p>" +
        (item.author && item.author !== "—" ? item.author + ". " : "") + item.year + ".</p>" +
        ((item.fields || []).length ? "<dl>" + item.fields.map((f) => "<dt>" + f.label + "</dt><dd>" + f.value + "</dd>").join("") + "</dl>" : ""),
      subjects: [], files: [], links: {},
      holdings: item.availability ? [{ location: "Основной фонд", inventory: "инв. " + item.mfn, status: item.availability }] : [],
    };
  }

  // Мультибазовый поиск (§1.4): агрегируем по всем выбранным базам,
  // каждую запись помечаем источником (sourceDb / dbShort).
  function runQuery(dbIds, query, filters, opts = {}) {
    let out = [];
    const q = (query || "").trim().toLowerCase();
    dbIds.forEach((id) => {
      const db = getDb(id);
      let list = (D.results[id] || []).slice();
      if (q) list = list.filter((r) => (r.title + " " + (r.author || "")).toLowerCase().includes(q));
      if (opts.onlyDigital && id === "EK") list = list.filter((r) => r.hasDigital);
      // Словарные чипы и групповые фильтры применяются только при одной базе.
      if (dbIds.length === 1) {
        const dictTerms = Object.keys(filters).filter((k) => k.startsWith("dict:") && filters[k]).map((k) => k.slice(5).toLowerCase());
        if (dictTerms.length) list = list.filter((r) => dictTerms.some((t) => (r.title + " " + (r.author || "")).toLowerCase().includes(t.split(" ")[0])));
        // nav: (классификатор) — на моке пропускаем как индексный фильтр (чип показывается).
        (db.filters || []).forEach((g) => {
          const sel = g.options.filter((o) => filters[g.id + ":" + o]);
          if (sel.length) list = list.filter((r) => sel.some((v) => r.docType === v || (r.fields || []).some((f) => f.value === v || v.indexOf(f.value) === 0)));
        });
      }
      list = list.map((r) => ({ ...r, sourceDb: id, db: id, dbTitle: db.name, dbShort: db.short || db.name }));
      out = out.concat(list);
    });
    return out;
  }

  function availableModes(dbIds) {
    if (dbIds.length === 1) return getDb(dbIds[0]).modes || ["simple"];
    return ["simple"];
  }

  const blankSpecial = (db) => {
    const v = {};
    (db && db.specialForm || []).forEach((f) => {
      if (f.kind === "roles") f.fields.forEach((r, i) => (v[f.id + ":" + i] = ""));
      else if (f.kind === "sourceArea") f.fields.forEach((sf) => (v[sf.id] = ""));
      else if (f.kind === "range") { v[f.id + ":from"] = ""; v[f.id + ":to"] = ""; }
      else if (f.kind === "dateEvent") { v[f.id + ":y"] = ""; v[f.id + ":m"] = ""; v[f.id + ":d"] = ""; }
      else v[f.id] = "";
    });
    return v;
  };

  const initialSearch = () => ({
    dbIds: [], query: "", mode: "simple", page: 1, pageSize: 20,
    sort: "По релевантности", view: "gallery", filters: {},
    advRows: [{ op: "and", field: "TI", qual: "contains", value: "" }],
    trunc: true, dateFrom: "", dateTo: "", onlyDigital: false,
    special: {}, marked: new Set(), all: [],
  });

  function App() {
    const [theme, setTheme] = React.useState("theatrical");
    const [a11y, setA11y] = React.useState(false);
    const [noImg, setNoImg] = React.useState(false);
    const [libraryId, setLibraryId] = React.useState((D.libraries[0] || {}).id);
    const library = (D.libraries || []).find((l) => l.id === libraryId) || D.libraries[0];
    const [context, setContext] = React.useState("reader");   // reader | staff
    const [staffRoute, setStaffRoute] = React.useState({ name: "desktop" });
    const [route, setRoute] = React.useState({ name: "home" });
    const [s, setS] = React.useState(initialSearch);
    const [loading, setLoading] = React.useState(false);
    const [account, setAccount] = React.useState({ loggedIn: false, ticket: D.account.ticket, lastName: D.account.lastName, displayName: D.account.displayName, loans: D.account.loans, orders: [], bookmarks: D.account.bookmarks || [], savedQueries: D.account.savedQueries || [], notifications: D.account.notifications || [], fines: D.account.fines || [] });
    const [toasts, setToasts] = React.useState([]);
    const [order, setOrder] = React.useState({ open: false, record: null });
    const [pendingOrder, setPendingOrder] = React.useState(null);
    const [viewer, setViewer] = React.useState({ open: false, file: null, canView: true });
    const timer = React.useRef(null);

    const dbIds = s.dbIds;
    const formDb = dbIds.length === 1 ? getDb(dbIds[0]) : null;     // конфиг формы — при одной базе
    const headDb = formDb || (dbIds.length ? getDb(dbIds[0]) : null);
    const patch = (p) => setS((prev) => ({ ...prev, ...p }));
    const toast = (t) => { const id = Date.now() + Math.random(); setToasts((x) => [...x, { ...t, id }]); setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), 4200); };

    function freezeTransitions() {
      const el = document.documentElement;
      el.classList.add("irb-theme-switching");
      requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove("irb-theme-switching")));
    }
    const changeTheme = (v) => { freezeTransitions(); setTheme(v); };
    const changeA11y = (v) => { freezeTransitions(); setA11y(v); };
    // Смена библиотеки — меняет бренд и применяет её скин (§9).
    const pickLibrary = (id) => {
      const lib = (D.libraries || []).find((l) => l.id === id);
      if (!lib) return;
      freezeTransitions();
      setLibraryId(id);
      if (!a11y) setTheme(lib.theme);
    };

    // ---- Сотруднический контекст ----
    function staffTask(domainId, taskId) {
      if (domainId === "cataloging" && (taskId === "cat-new" || taskId === "cat-list")) {
        setStaffRoute({ name: "cataloging", profile: D.catalogingProfiles.EK });
      } else if (taskId === "circ-issue" || taskId === "circ-queue" || taskId === "circ-shelf") {
        setStaffRoute({ name: "circulation", tab: taskId });
      } else if (taskId === "inv-session") {
        setStaffRoute({ name: "inventory" });
      } else if (taskId === "an-dash") {
        setStaffRoute({ name: "dashboard" });
      } else {
        setStaffRoute({ name: "stub", title: ({
          "cat-global": "Глобальная корректировка", "cat-import": "Импорт записи (copy-cataloging)",
          "circ-issue": "Книговыдача: выдача / возврат", "circ-queue": "Очередь заказов",
          "circ-shelf": "Бронеполка", "circ-debt": "Должники",
          "acq-order": "Заказы поставщикам", "acq-ksu": "КСУ",
          "inv-session": "Сессия инвентаризации (ТСД)", "inv-report": "Отчёт расхождений",
          "an-dash": "BI-дашборд",
        })[taskId] || "Экран сотрудника" });
      }
    }
    function switchContext(c) {
      setContext(c);
      if (c === "staff") setStaffRoute({ name: "desktop" });
      else setRoute({ name: "home" });
    }

    // ---- Поиск (старт ТОЛЬКО по кнопке для расширенного/спец; простой — кнопка/Enter) ----
    function doSearch(query, opts = {}) {
      const q = query != null ? query : s.query;
      if (!dbIds.length) { toast({ variant: "warning", title: "Не выбрана база", message: "Отметьте хотя бы одну базу в селекторе баз." }); return; }
      if (q.trim().toLowerCase() === "ошибка") { setRoute({ name: "catalog-error" }); return; }
      const nextFilters = opts.filters || s.filters;
      setLoading(true);
      setRoute({ name: "results" });
      patch({ query: q, page: opts.resetPage ? 1 : s.page, filters: nextFilters });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        const all = runQuery(dbIds, q, nextFilters, { onlyDigital: s.onlyDigital });
        setS((prev) => ({ ...prev, all, query: q, page: opts.resetPage ? 1 : prev.page }));
        setLoading(false);
      }, 600);
    }

    function setDbIds(ids) {
      setS((prev) => {
        const modes = availableModes(ids);
        const mode = modes.includes(prev.mode) ? prev.mode : "simple";
        const next = { ...prev, dbIds: ids, mode, special: ids.length === 1 ? (Object.keys(prev.special).length ? prev.special : blankSpecial(getDb(ids[0]))) : {}, filters: {}, page: 1 };
        return next;
      });
      if (route.name === "results" && ids.length) {
        setLoading(true);
        clearTimeout(timer.current);
        timer.current = setTimeout(() => { setS((prev) => ({ ...prev, all: runQuery(ids, prev.query, {}, { onlyDigital: prev.onlyDigital }) })); setLoading(false); }, 500);
      }
    }

    function setMode(m) {
      setS((prev) => ({ ...prev, mode: m, special: m === "special" && formDb ? (Object.keys(prev.special).length ? prev.special : blankSpecial(formDb)) : prev.special }));
    }

    function setFilter(key, val) {
      const filters = { ...s.filters, [key]: val };
      if (!val) delete filters[key];
      setLoading(true);
      patch({ filters, page: 1 });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => { setS((prev) => ({ ...prev, all: runQuery(dbIds, s.query, filters, { onlyDigital: prev.onlyDigital }), filters, page: 1 })); setLoading(false); }, 350);
    }
    function clearAll() {
      setLoading(true);
      patch({ filters: {}, page: 1 });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => { setS((prev) => ({ ...prev, all: runQuery(dbIds, s.query, {}, { onlyDigital: prev.onlyDigital }), filters: {}, page: 1 })); setLoading(false); }, 300);
    }

    function runAdvanced() {
      const q = s.advRows.map((r) => r.value).filter(Boolean).join(" ") || s.query;
      doSearch(q, { resetPage: true });
    }
    function runSpecial() {
      const q = Object.keys(s.special).map((k) => s.special[k]).filter((v) => v && typeof v === "string" && v.trim() && v.indexOf("—") !== 0).join(" ") || s.query;
      doSearch(q, { resetPage: true });
    }

    const activeChips = Object.keys(s.filters).filter((k) => s.filters[k]).map((k) => {
      if (k.startsWith("dict:")) return { key: k, group: "Словарь", label: k.slice(5) };
      if (k.startsWith("nav:")) return { key: k, group: "Классификатор", label: typeof s.filters[k] === "string" ? s.filters[k] : k.slice(4) };
      const [gid, ...rest] = k.split(":");
      const g = (formDb ? formDb.filters : []).find((x) => x.id === gid);
      return { key: k, group: g ? g.label : gid, label: rest.join(":") };
    });

    // ---- Навигация по записи ----
    function openRecord(item) {
      const targetDb = getDb(item.sourceDb || item.db);
      setRoute({ name: "record", item, db: targetDb });
      window.scrollTo(0, 0);
    }
    function backToResults() { setRoute({ name: "results" }); }   // состояние s сохраняется (§1.3)

    // Переход по связи 390/488 в другую базу — показываем имя целевой БД (§1.4)
    function followLink(link) {
      const targetDbId = link.target || (link.level ? "GUAR" : null) || "EK";
      const mfn = link.mfn;
      const rec = D.records[mfn];
      const targetDb = getDb(rec ? rec.db : targetDbId);
      const item = rec || { mfn, db: targetDb.id };
      toast({ variant: "info", title: "Переход в базу", message: targetDb.name });
      setRoute({ name: "record", item, db: targetDb });
      window.scrollTo(0, 0);
    }

    function toggleMark(mfn) {
      setS((prev) => { const m = new Set(prev.marked); m.has(mfn) ? m.delete(mfn) : m.add(mfn); return { ...prev, marked: m }; });
    }

    // ---- Просмотр файла (view-only) ----
    function openFile(file) {
      const canView = !file.requiresAuth || account.loggedIn;
      const terms = (s.query || "").split(/\s+/).filter((w) => w.length > 1).slice(0, 4);
      const relevantPages = file.kind === "pdf" && terms.length ? [3, 12, 45].filter((p) => p <= (file.pages || 99)) : null;
      setViewer({ open: true, file, canView, terms, relevantPages });
    }

    // ---- Заказ (гость не может — §1.2) ----
    function startOrder(record) {
      if (!account.loggedIn) { setPendingOrder(record); setRoute({ name: "login" }); toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету, чтобы оформить заказ." }); return; }
      setOrder({ open: true, record });
    }
    function confirmOrder(holding) {
      setAccount((a) => ({ ...a, orders: [...a.orders, { title: order.record.title, status: "queued", location: holding.location }] }));
      toast({ variant: "success", title: "Заказ принят", message: "Экземпляр в очереди выдачи." });
    }
    function orderMarked() {
      if (!account.loggedIn) { setRoute({ name: "login" }); toast({ variant: "info", title: "Требуется вход", message: "Войдите, чтобы заказать отмеченные." }); return; }
      const titles = s.all.filter((r) => s.marked.has(r.mfn));
      setAccount((a) => ({ ...a, orders: [...a.orders, ...titles.map((t) => ({ title: t.title, status: "queued", location: "Основной фонд" }))] }));
      toast({ variant: "success", title: "Заказано: " + titles.length, message: "Добавлено в Корзину заказов." });
      setS((prev) => ({ ...prev, marked: new Set() }));
    }

    function login(ticket, lastName) {
      setAccount((a) => ({ ...a, loggedIn: true, ticket }));
      if (pendingOrder) { const r = pendingOrder; setPendingOrder(null); setOrder({ open: true, record: r }); setRoute({ name: "record", item: r, db: getDb(r.db) }); }
      else setRoute({ name: "account" });
      toast({ variant: "success", title: "Вы вошли", message: "Билет № " + ticket });
    }
    function logout() { setAccount((a) => ({ ...a, loggedIn: false, orders: [] })); setRoute({ name: "home" }); }

    function searchSubject(subject) {
      if (!dbIds.length) setS((prev) => ({ ...prev, dbIds: [route.db ? route.db.id : "EK"] }));
      const ids = dbIds.length ? dbIds : [route.db ? route.db.id : "EK"];
      patch({ query: subject, filters: {}, mode: "simple" });
      setLoading(true);
      setRoute({ name: "results" });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => { setS((prev) => ({ ...prev, all: runQuery(ids, subject, {}, {}), query: subject, page: 1, filters: {} })); setLoading(false); }, 500);
    }

    // ---- Производные для выдачи ----
    const total = s.all.length;
    const start = (s.page - 1) * s.pageSize;
    const pageItems = s.all.slice(start, start + s.pageSize);
    const dictionary = formDb ? (D.dictionaries[formDb.id] || []) : [];
    const premieres = D.results.TUAR;
    const multiBase = dbIds.length > 1;

    const rootTheme = a11y ? "a11y" : (theme === "working" ? undefined : theme);
    const fxTheme = a11y ? null : theme;

    return (
      <div data-theme={rootTheme} style={{ minHeight: "100vh", background: "var(--bg-page)", color: "var(--text-body)", display: "flex", flexDirection: "column" }}>
        <window.TopBar
          onHome={() => { if (context === "staff") setStaffRoute({ name: "desktop" }); else setRoute({ name: "home" }); }}
          onAccount={() => setRoute({ name: account.loggedIn ? "account" : "login" })}
          account={account} theme={theme} setTheme={changeTheme} a11y={a11y} setA11y={changeA11y} noImg={noImg} setNoImg={setNoImg}
          context={context} setContext={switchContext}
          library={library} libraries={D.libraries} onPickLibrary={pickLibrary}
          currentDb={context === "reader" && ((route.name === "results" && headDb) ? headDb : (route.name === "record" ? route.db : null))}
          multiBase={context === "reader" && route.name === "results" && multiBase ? dbIds.length : 0}
        />

        <main style={{ flex: 1 }}>
          {context === "staff" ? (
            <>
              {staffRoute.name === "desktop" && <window.StaffDesktop staff={D.staff} onTask={staffTask} />}
              {staffRoute.name === "cataloging" && <window.CatalogingWorksheet profile={staffRoute.profile} onBack={() => setStaffRoute({ name: "desktop" })} onToast={toast} />}
              {staffRoute.name === "circulation" && <window.Circulation data={D.staffData} onBack={() => setStaffRoute({ name: "desktop" })} onToast={toast} />}
              {staffRoute.name === "inventory" && <window.Inventory data={D.staffData} onBack={() => setStaffRoute({ name: "desktop" })} onToast={toast} />}
              {staffRoute.name === "dashboard" && <window.Dashboard data={D.staffData} onBack={() => setStaffRoute({ name: "desktop" })} />}
              {staffRoute.name === "stub" && <window.StaffStub title={staffRoute.title} onBack={() => setStaffRoute({ name: "desktop" })} />}
            </>
          ) : (
          <React.Fragment>
          {route.name === "home" && (
            <window.HomeScreen databases={DBS} groups={GROUPS} dbIds={dbIds} setDbIds={setDbIds}
              query={s.query} setQuery={(q) => patch({ query: q })}
              onSearch={(q) => doSearch(q, { resetPage: true })}
              onlyDigital={s.onlyDigital} setOnlyDigital={(v) => patch({ onlyDigital: v })}
              formDb={formDb} suggestions={dictionary} premieres={premieres} onOpenRecord={openRecord} account={account} onLogin={() => setRoute({ name: "login" })} library={library} />
          )}

          {route.name === "results" && (
            <window.ResultsScreen
              databases={DBS} groups={GROUPS} dbIds={dbIds} setDbIds={setDbIds} formDb={formDb} headDb={headDb} multiBase={multiBase}
              query={s.query} setQuery={(q) => patch({ query: q })} onSearch={(q) => doSearch(q, { resetPage: true })}
              mode={s.mode} setMode={setMode} availableModes={availableModes(dbIds)}
              loading={loading} items={pageItems} total={total}
              page={s.page} setPage={(p) => patch({ page: p })} pageSize={s.pageSize} setPageSize={(n) => patch({ pageSize: n, page: 1 })}
              sort={s.sort} setSort={(v) => patch({ sort: v })} view={s.view} setView={(v) => patch({ view: v })}
              marked={s.marked} toggleMark={toggleMark} clearMarked={() => patch({ marked: new Set() })} onOrderMarked={orderMarked}
              filters={s.filters} setFilter={setFilter} activeChips={activeChips} removeChip={(k) => setFilter(k, false)} clearAll={clearAll}
              advRows={s.advRows} setAdvRows={(r) => patch({ advRows: r })} trunc={s.trunc} setTrunc={(v) => patch({ trunc: v })} runAdvanced={runAdvanced}
              special={s.special} setSpecial={(sp) => patch({ special: sp })} runSpecial={runSpecial} resetSpecial={() => patch({ special: blankSpecial(formDb) })}
              onlyDigital={s.onlyDigital} setOnlyDigital={(v) => patch({ onlyDigital: v })}
              dictionary={dictionary} dateFrom={s.dateFrom} dateTo={s.dateTo} setDate={(k, v) => patch(k === "from" ? { dateFrom: v } : { dateTo: v })}
              onOpenRecord={openRecord} noImg={noImg} suggestions={dictionary} account={account} allItems={s.all} />
          )}

          {route.name === "record" && (
            <window.RecordScreen record={recordFor(route.item)} db={route.db} onBack={backToResults} fromResults={s.all.length > 0}
              onSubject={searchSubject} onOrder={() => startOrder(recordFor(route.item))}
              onToggleMark={() => toggleMark(route.item.mfn)} marked={s.marked.has(route.item.mfn)}
              account={account} noImg={noImg} onToast={toast} onOpenFile={openFile} onFollowLink={followLink} pickFile={pickFile} />
          )}

          {route.name === "login" && <window.LoginScreen onLogin={login} pending={!!pendingOrder} />}
          {route.name === "account" && <window.FormularScreen account={account}
            onCancelOrder={(i) => setAccount((a) => ({ ...a, orders: a.orders.filter((_, j) => j !== i) }))}
            onLogout={logout} onSearch={() => setRoute({ name: "home" })}
            onRenew={(i) => { setAccount((a) => ({ ...a, loans: a.loans.map((l, j) => j === i ? { ...l, due: "31.07.2026", renewable: false } : l) })); toast({ variant: "success", title: "Срок продлён", message: "Новая дата возврата: 31.07.2026." }); }}
            onRemoveBookmark={(mfn) => setAccount((a) => ({ ...a, bookmarks: a.bookmarks.filter((b) => b.mfn !== mfn) }))}
            onOpenBookmark={(b) => openRecord(b)}
            onRunQuery={(q) => searchSubject(q.label)}
            onRemoveQuery={(id) => setAccount((a) => ({ ...a, savedQueries: a.savedQueries.filter((q) => q.id !== id) }))}
            onReadNotifications={() => setAccount((a) => ({ ...a, notifications: a.notifications.map((n) => ({ ...n, unread: false })) }))}
            onPayFines={() => { setAccount((a) => ({ ...a, fines: [] })); toast({ variant: "success", title: "Оплата прошла", message: "Задолженность погашена." }); }}
          />}

          {route.name === "catalog-error" && (
            <div style={{ padding: "var(--space-16) var(--space-6)" }}>
              <EmptyState variant="error" icon="alert-octagon" title="Каталог временно недоступен"
                description="Не удалось связаться с каталогом. Повторите попытку позже — мы уже знаем о проблеме."
                action={<Button iconLeft="rotate-ccw" onClick={() => setRoute({ name: "home" })}>На главную</Button>} />
            </div>
          )}
          </React.Fragment>
          )}
        </main>

        <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "var(--space-5) var(--space-6)", marginTop: "var(--space-12)" }}>
          <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", display: "flex", gap: "var(--space-4)", alignItems: "center", flexWrap: "wrap", fontSize: "var(--text-xs)", color: "var(--text-subtle)" }}>
            <Icon name="globe" size={14} />
            <span>Каталог работает в защищённом контуре. Демонстрационные данные обезличены.</span>
            <span style={{ marginLeft: "auto" }}>Подсказка: запрос «ошибка» покажет состояние недоступности каталога.</span>
          </div>
        </footer>

        <ToastViewport toasts={toasts} onDismiss={(id) => setToasts((x) => x.filter((y) => y.id !== id))} />
        <window.OrderModal open={order.open} record={order.record} onClose={() => setOrder({ open: false, record: null })} onConfirm={confirmOrder} />
        {FileViewer && <FileViewer open={viewer.open} file={viewer.file} canView={viewer.canView} terms={viewer.terms} relevantPages={viewer.relevantPages} onClose={() => setViewer({ open: false, file: null, canView: true })} />}
        {window.SeasonalFX && <window.SeasonalFX theme={fxTheme} />}
      </div>
    );
  }

  Object.assign(window, { IrbisApp: App });
})();
