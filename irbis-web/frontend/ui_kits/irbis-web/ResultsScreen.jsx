/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, IconButton, Select, Checkbox, Switch, Input,
    FilterChip, ResultCard, StatusBadge, Tabs, Pagination, SkeletonResult, EmptyState } = NS;
  const SearchModes = NS.SearchModes;
  const TreeNav = NS.TreeNav;

  const SORTS = ["По релевантности", "По году ↓", "По году ↑", "По месту хранения", "По рубрикам"];

  // ---- Конструктор расширенного / комплексного поиска ----
  function QueryBuilder({ db, rows, setRows, trunc, setTrunc, onSearch, onReset, complex }) {
    const setRow = (i, patch) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
    const addRow = () => setRows([...rows, { op: "and", field: db.searchFields[0].code, qual: "contains", value: "" }]);
    const delRow = (i) => setRows(rows.filter((_, j) => j !== i));
    return (
      <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-5)", marginBottom: "var(--space-4)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "var(--space-4)" }}>
          <Icon name={complex ? "layers" : "sliders"} size={18} style={{ color: "var(--accent)" }} />
          <h2 style={{ fontSize: "var(--text-lg)" }}>{complex ? "Комплексный поиск" : "Расширенный поиск"} · {db.name}</h2>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {rows.map((r, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "84px 1fr 150px 1fr 40px", gap: "var(--space-2)", alignItems: "center" }}>
              {i === 0
                ? <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)", paddingLeft: 4 }}>Где</span>
                : <Select size="sm" value={r.op} onChange={(e) => setRow(i, { op: e.target.value })}
                    options={[{ value: "and", label: "И" }, { value: "or", label: "ИЛИ" }, { value: "not", label: "НЕ" }]} />}
              <Select size="sm" value={r.field} onChange={(e) => setRow(i, { field: e.target.value })}
                options={db.searchFields.map((f) => ({ value: f.code, label: f.label }))} />
              <Select size="sm" value={r.qual} onChange={(e) => setRow(i, { qual: e.target.value })}
                options={[{ value: "contains", label: "содержит" }, { value: "starts", label: "начинается с" }, { value: "exact", label: "совпадает" }]} />
              <Input size="sm" value={r.value} placeholder="значение" onChange={(e) => setRow(i, { value: e.target.value })} />
              <IconButton icon="x" label="Удалить строку" size="sm" onClick={() => delRow(i)} disabled={rows.length === 1} />
            </div>
          ))}
        </div>
        {complex && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
            <div><label style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Год издания</label>
              <div style={{ display: "flex", gap: 8, marginTop: 5 }}><Input size="sm" placeholder="с" /><Input size="sm" placeholder="по" /></div></div>
            <div><label style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Язык публикации</label>
              <Select size="sm" options={["— любой —", "русский", "английский", "французский"]} /></div>
            <div><label style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>Вид документа</label>
              <Select size="sm" options={["— любой —", "Книга", "Сборник", "Многотомник"]} /></div>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", marginTop: "var(--space-4)", flexWrap: "wrap" }}>
          <Button variant="ghost" size="sm" iconLeft="plus" onClick={addRow}>Добавить условие</Button>
          <Switch label="Усечение (*)" checked={trunc} onChange={(e) => setTrunc(e.target.checked)} />
          <div style={{ flex: 1 }} />
          <Button variant="secondary" size="lg" iconLeft="rotate-ccw" onClick={onReset}>Сброс</Button>
          <Button size="lg" iconLeft="search" onClick={onSearch}>Поиск</Button>
        </div>
      </div>
    );
  }

  // ---- Левая колонка: режимы + словарь + фильтры ----
  function LeftRail({ formDb, multiBase, mode, setMode, availableModes, dictionary, filters, setFilter, dateFrom, dateTo, setDate, facetSource, navCode, setNav }) {
    const Hd = ({ children }) => <div style={{ fontSize: "var(--text-2xs)", textTransform: "uppercase", letterSpacing: "var(--tracking-caps)", color: "var(--text-subtle)", fontWeight: 700, marginBottom: 10 }}>{children}</div>;
    const facetCount = (opt) => (facetSource || []).filter((r) => r.docType === opt || (r.fields || []).some((f) => f.value === opt)).length;
    return (
      <aside style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
        {SearchModes && <SearchModes modes={availableModes} value={mode} onChange={setMode}
          labels={formDb && formDb.modes && formDb.modes.includes("special") ? { special: "Спецформа базы" } : {}} />}

        {multiBase ? (
          <div style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "var(--space-3)" }}>
            <Icon name="info" size={15} style={{ verticalAlign: "-2px", marginRight: 6, color: "var(--text-subtle)" }} />
            Словарь и фильтры доступны при поиске в одной базе. Сейчас выбрано несколько баз.
          </div>
        ) : (
          <>
            {formDb && formDb.navigators && TreeNav && (
              <div>
                <Hd>Навигатор · классификаторы</Hd>
                <TreeNav navigators={formDb.navigators} value={navCode} onPick={(node) => setNav(node || null)} />
              </div>
            )}
            {dictionary.length > 0 && (
              <div>
                <Hd>Словарь · уточните</Hd>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {dictionary.map((t) => (
                    <FilterChip key={t.term} label={t.term} count={t.count}
                      pressed={!!filters["dict:" + t.term]} onToggle={() => setFilter("dict:" + t.term, !filters["dict:" + t.term])} />
                  ))}
                </div>
              </div>
            )}
            {formDb && formDb.dateRange && (
              <div>
                <Hd>Диапазон дат · поле 122</Hd>
                <div style={{ display: "flex", gap: 8 }}>
                  <Input size="sm" placeholder="с (год)" value={dateFrom} onChange={(e) => setDate("from", e.target.value)} />
                  <Input size="sm" placeholder="по (год)" value={dateTo} onChange={(e) => setDate("to", e.target.value)} />
                </div>
              </div>
            )}
            {(formDb ? formDb.filters : []).map((g) => (
              <div key={g.id}>
                <Hd>{g.label}</Hd>
                <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                  {g.options.map((opt) => {
                    const key = g.id + ":" + opt;
                    const c = facetCount(opt);
                    return (
                      <div key={opt} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Checkbox label={opt} checked={!!filters[key]} onChange={() => setFilter(key, !filters[key])} />
                        {c > 0 && <span style={{ marginLeft: "auto", fontSize: "var(--text-2xs)", color: "var(--text-subtle)", fontVariantNumeric: "tabular-nums", background: "var(--surface-sunken)", borderRadius: "var(--radius-pill)", padding: "1px 7px" }}>{c}</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </>
        )}
      </aside>
    );
  }

  // ---- Галерея (изобразительные базы) ----
  function GalleryGrid({ items, marked, toggleMark, onOpen, noImg, multiBase }) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: "var(--space-3)" }}>
        {items.map((it) => (
          <article key={it.sourceDb + it.mfn} style={{
            background: "var(--surface-card)", border: "1px solid " + (marked.has(it.mfn) ? "var(--accent-weak-border)" : "var(--border-subtle)"),
            borderRadius: "var(--radius-lg)", overflow: "hidden", display: "flex", flexDirection: "column",
          }}>
            <button type="button" onClick={() => onOpen(it)} style={{
              border: "none", padding: 0, cursor: "pointer", height: 130, position: "relative",
              background: noImg ? "var(--surface-sunken)" : "hsl(" + (it.tint || 30) + " 32% 86%)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }} aria-label={"Открыть: " + it.title}>
              <Icon name={noImg ? "file-text" : "image"} size={30} style={{ color: noImg ? "var(--text-subtle)" : "hsl(" + (it.tint || 30) + " 38% 42%)" }} />
              <span style={{ position: "absolute", top: 8, left: 8 }}>
                <span onClick={(e) => { e.stopPropagation(); toggleMark(it.mfn); }} style={{
                  display: "flex", width: 24, height: 24, borderRadius: "var(--radius-sm)", alignItems: "center", justifyContent: "center",
                  background: marked.has(it.mfn) ? "var(--accent)" : "rgba(255,255,255,.85)", color: marked.has(it.mfn) ? "#fff" : "var(--text-muted)",
                }}>{marked.has(it.mfn) ? <Icon name="check" size={15} /> : <Icon name="plus" size={15} />}</span>
              </span>
            </button>
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
              {multiBase && <span style={{ fontSize: "var(--text-2xs)", fontWeight: 600, color: "var(--accent)" }}>{it.dbShort}</span>}
              <button type="button" onClick={() => onOpen(it)} style={{ border: "none", background: "none", padding: 0, textAlign: "left", cursor: "pointer",
                fontFamily: "var(--font-record-title)", fontWeight: 600, fontSize: "var(--text-sm)", color: "var(--text-strong)", lineHeight: 1.3 }}>{it.title}</button>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{it.author} · {it.year}</span>
              <div style={{ marginTop: "auto", paddingTop: 4 }}><StatusBadge status={it.availability} size="sm" /></div>
            </div>
          </article>
        ))}
      </div>
    );
  }

  function ResultsScreen(props) {
    const {
      databases, groups, dbIds, setDbIds, formDb, headDb, multiBase,
      query, setQuery, onSearch, mode, setMode, availableModes,
      loading, items, total, page, setPage, pageSize, setPageSize, sort, setSort, view, setView,
      marked, toggleMark, clearMarked, onOrderMarked, filters, setFilter, activeChips, removeChip, clearAll,
      advRows, setAdvRows, trunc, setTrunc, runAdvanced,
      special, setSpecial, runSpecial, resetSpecial, onlyDigital, setOnlyDigital,
      dictionary, dateFrom, dateTo, setDate, onOpenRecord, noImg, suggestions, allItems,
    } = props;

    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const galleryLayout = headDb && headDb.layout === "gallery" && !multiBase;
    const resetAdv = () => setAdvRows([{ op: "and", field: (formDb || databases[0]).searchFields[0].code, qual: "contains", value: "" }]);

    return (
      <div style={{ maxWidth: "var(--container-max)", margin: "0 auto", padding: "var(--space-5) var(--space-6) var(--space-12)" }}>
        {/* Строка поиска + базы */}
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: "var(--space-3)", alignItems: "start", marginBottom: "var(--space-4)" }}>
          <NS.DatabaseSelector databases={databases} groups={groups} value={dbIds} onChange={setDbIds} />
          <div>
            <label style={{ display: "block", fontSize: "var(--text-xs)", fontWeight: 600, color: "var(--text-muted)", marginBottom: 5 }}>Я ищу:</label>
            <NS.SearchBar value={query} onChange={setQuery} onSearch={onSearch} suggestions={suggestions}
              buttonLabel="Поиск" onReset={() => { setQuery(""); onSearch(""); }}
              onPickSuggestion={(sug) => { setQuery(sug.term || sug); onSearch(sug.term || sug); }} />
            {formDb && formDb.simpleExtra && mode === "simple" && (
              <div style={{ marginTop: 9 }}>
                <Checkbox label={formDb.simpleExtra.label} checked={onlyDigital} onChange={(e) => { setOnlyDigital(e.target.checked); }} />
              </div>
            )}
          </div>
        </div>

        {/* Панели режимов (старт по кнопке) */}
        {mode === "advanced" && formDb && (
          <QueryBuilder db={formDb} rows={advRows} setRows={setAdvRows} trunc={trunc} setTrunc={setTrunc} onSearch={runAdvanced} onReset={resetAdv} />
        )}
        {mode === "complex" && formDb && (
          <QueryBuilder db={formDb} rows={advRows} setRows={setAdvRows} trunc={trunc} setTrunc={setTrunc} onSearch={runAdvanced} onReset={resetAdv} complex />
        )}
        {mode === "special" && formDb && window.SpecialForm && (
          <window.SpecialForm db={formDb} values={special} setValues={setSpecial} onSearch={runSpecial} onReset={resetSpecial} />
        )}

        <div style={{ display: "grid", gridTemplateColumns: "var(--rail-filters) 1fr", gap: "var(--space-6)", alignItems: "start" }}>
          <div style={{ position: "sticky", top: 76 }} className="irbis-rail">
            <LeftRail formDb={formDb} multiBase={multiBase} mode={mode} setMode={setMode} availableModes={availableModes}
              dictionary={dictionary} filters={filters} setFilter={setFilter} dateFrom={dateFrom} dateTo={dateTo} setDate={setDate}
              facetSource={allItems} navCode={(Object.keys(filters).find((k) => k.indexOf("nav:") === 0) || "").slice(4) || null}
              setNav={(node) => {
                Object.keys(filters).forEach((k) => { if (k.indexOf("nav:") === 0) setFilter(k, false); });
                if (node) setFilter("nav:" + node.code, node.label + (node.code ? " (" + node.code + ")" : ""));
              }} />
          </div>

          <div>
            {/* Тулбар: счётчик + дубль навигации сверху + сортировка */}
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap", marginBottom: "var(--space-3)" }}>
              {multiBase && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-xs)", fontWeight: 600, color: "var(--accent)", background: "var(--accent-weak)", border: "1px solid var(--accent-weak-border)", borderRadius: "var(--radius-pill)", padding: "3px 10px" }}>
                  <Icon name="layers" size={13} /> Поиск по {dbIds.length} базам
                </span>
              )}
              {!loading && total > 0 && <Pagination compact page={page} pageCount={pageCount} total={total} onPage={setPage} />}
              <div style={{ flex: 1 }} />
              {galleryLayout && (
                <Tabs variant="pill" value={view} onChange={setView}
                  tabs={[{ id: "gallery", label: "Галерея", icon: "grid" }, { id: "list", label: "Список", icon: "list" }]} />
              )}
              <Select size="sm" value={sort} onChange={(e) => setSort(e.target.value)} options={SORTS} aria-label="Сортировка" />
            </div>

            {/* Чипы активных фильтров */}
            {activeChips.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: "var(--space-4)" }}>
                {activeChips.map((c) => <FilterChip key={c.key} group={c.group} label={c.label} onRemove={() => removeChip(c.key)} />)}
                <button type="button" onClick={clearAll} style={{ background: "none", border: "none", color: "var(--text-link)", cursor: "pointer", fontSize: "var(--text-sm)", fontFamily: "var(--font-ui)", fontWeight: 500 }}>Очистить все</button>
              </div>
            )}

            {/* Панель отмеченных */}
            {marked.size > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "10px 14px", background: "var(--accent-weak)", border: "1px solid var(--accent-weak-border)", borderRadius: "var(--radius-md)", marginBottom: "var(--space-4)" }}>
                <Icon name="check-circle" size={18} style={{ color: "var(--accent)" }} />
                <span style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--accent-press)" }}>Отмечено: {marked.size}</span>
                <div style={{ flex: 1 }} />
                <Button size="sm" variant="secondary" iconLeft="bookmark" onClick={onOrderMarked}>Заказать отмеченные</Button>
                <Button size="sm" variant="ghost" onClick={clearMarked}>Снять все отметки</Button>
              </div>
            )}

            {/* Контент */}
            {loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {Array.from({ length: 5 }).map((_, i) => <SkeletonResult key={i} showThumb={galleryLayout} />)}
              </div>
            ) : items.length === 0 ? (
              <EmptyState title="Ничего не найдено" description={"По запросу «" + query + "» записей нет."}
                hints={["Уберите часть условий или фильтров", "Включите усечение в расширенном поиске", "Проверьте раскладку клавиатуры", "Добавьте базы в селекторе"]}
                action={<Button variant="secondary" iconLeft="rotate-ccw" onClick={clearAll}>Сбросить фильтры</Button>} />
            ) : galleryLayout && view === "gallery" ? (
              <GalleryGrid items={items} marked={marked} toggleMark={toggleMark} onOpen={onOpenRecord} noImg={noImg} multiBase={multiBase} />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {items.map((it) => (
                  <ResultCard key={it.sourceDb + it.mfn} item={it} checked={marked.has(it.mfn)}
                    onToggleCheck={() => toggleMark(it.mfn)} onOpen={() => onOpenRecord(it)}
                    showThumb={headDb && headDb.layout === "gallery"} typeIcon={(it.sourceDb && databases.find((d) => d.id === it.sourceDb) || {}).typeIcon || "book"}
                    dbTag={multiBase ? it.dbShort : null} />
                ))}
              </div>
            )}

            {/* Пагинация снизу */}
            {!loading && items.length > 0 && (
              <div style={{ marginTop: "var(--space-6)" }}>
                <Pagination page={page} pageCount={pageCount} total={total} onPage={setPage} pageSize={pageSize} onPageSize={setPageSize} />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  Object.assign(window, { ResultsScreen });
})();
