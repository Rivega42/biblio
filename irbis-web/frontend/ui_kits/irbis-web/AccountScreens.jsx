/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Icon, Button, Input, Tabs, StatusBadge, Badge, EmptyState, Alert } = NS;

  const TONE = {
    available: "var(--status-available-strong)", issued: "var(--status-issued-strong)",
    danger: "var(--danger-500)", neutral: "var(--text-muted)",
  };

  function LoginScreen({ onLogin, pending }) {
    const [lastName, setLastName] = React.useState("");
    const [ticket, setTicket] = React.useState("");
    const [err, setErr] = React.useState("");
    const submit = () => {
      const v = ticket.trim();
      if (!/^\d{4,}$/.test(v)) { setErr("Введите номер билета (только цифры)."); return; }
      setErr("");
      onLogin(v, lastName.trim());
    };
    return (
      <div style={{ maxWidth: 420, margin: "0 auto", padding: "var(--space-16) var(--space-6)" }}>
        <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
          <span style={{ display: "inline-flex", width: 56, height: 56, borderRadius: "var(--radius-round)", background: "var(--accent-weak)", color: "var(--accent)", alignItems: "center", justifyContent: "center", marginBottom: "var(--space-3)" }}>
            <Icon name="log-in" size={28} />
          </span>
          <h1 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-2)" }}>Вход в Личный кабинет</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>Вход по номеру читательского билета.</p>
        </div>
        {pending && <div style={{ marginBottom: "var(--space-4)" }}><Alert variant="info" title="Для заказа нужен вход">Уважаемый Гость! Для заказа книг и входа в Личный кабинет авторизуйтесь.</Alert></div>}
        <div style={{ background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)", padding: "var(--space-6)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Input label="Фамилия" iconLeft="user" placeholder="Необязательно" value={lastName} onChange={(e) => setLastName(e.target.value)} onClear={() => setLastName("")} />
          <Input label="Номер читательского билета" iconLeft="log-in" placeholder="00012345" inputMode="numeric"
            value={ticket} error={err} onChange={(e) => setTicket(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} onClear={() => setTicket("")} />
          <Button block size="lg" iconLeft="log-in" onClick={submit}>Войти</Button>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", textAlign: "center", margin: 0 }}>
            Для демонстрации используйте билет <b>00012345</b>. Мы не собираем лишних данных (152-ФЗ).
          </p>
        </div>
      </div>
    );
  }

  function FormularScreen({ account, onCancelOrder, onLogout, onSearch, onRenew, onRemoveBookmark, onOpenBookmark, onRunQuery, onRemoveQuery, onReadNotifications, onPayFines }) {
    const [tab, setTab] = React.useState("loans");
    const unread = (account.notifications || []).filter((n) => n.unread).length;
    const finesTotal = (account.fines || []).reduce((s, f) => s + f.amount, 0);
    React.useEffect(() => { if (tab === "notify" && unread && onReadNotifications) onReadNotifications(); }, [tab]);

    const Row = ({ children, accentTone }) => (
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", background: "var(--surface-card)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "var(--space-3) var(--space-4)" }}>{children}</div>
    );

    return (
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "var(--space-6)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
          <span style={{ width: 52, height: 52, borderRadius: "var(--radius-round)", background: "var(--accent-weak)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
            <Icon name="user" size={26} />
          </span>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: "var(--text-xl)" }}>Читатель</h1>
            <div style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>Вы, {account.displayName} · <span style={{ fontFamily: "var(--font-mono)" }}>билет № {account.ticket}</span></div>
          </div>
          {finesTotal > 0 && <Badge variant="danger">К оплате: {finesTotal} ₽</Badge>}
          <Button variant="ghost" iconLeft="log-out" onClick={onLogout}>Выйти</Button>
        </div>

        <Tabs value={tab} onChange={setTab} tabs={[
          { id: "loans", label: "Формуляр", count: account.loans.length },
          { id: "orders", label: "Корзина заказов", count: account.orders.length },
          { id: "bookmarks", label: "Закладки", count: (account.bookmarks || []).length },
          { id: "queries", label: "Пост. запросы", count: (account.savedQueries || []).length },
          { id: "notify", label: "Уведомления", count: unread || undefined },
          { id: "fines", label: "Оплата" },
        ]} />

        <div style={{ marginTop: "var(--space-5)" }}>
          {tab === "loans" && (
            account.loans.length === 0
              ? <EmptyState title="Нет текущих выдач" description="Здесь появятся издания на руках." />
              : <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {account.loans.map((l, i) => (
                  <Row key={i}>
                    <Icon name="book" size={18} style={{ color: "var(--text-muted)", flex: "none" }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{l.title}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{l.location}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "var(--text-2xs)", color: "var(--text-subtle)", textTransform: "uppercase", letterSpacing: ".05em" }}>Вернуть до</div>
                      <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: l.overdueSoon ? "var(--status-issued-strong)" : "var(--text-strong)", fontFamily: "var(--font-mono)" }}>{l.due}</div>
                    </div>
                    <Button size="sm" variant="secondary" iconLeft="refresh-cw" disabled={!l.renewable} onClick={() => onRenew(i)}>Продлить</Button>
                  </Row>
                ))}
              </div>
          )}

          {tab === "orders" && (
            account.orders.length === 0
              ? <EmptyState title="Корзина заказов пуста" description="Найдите издание и нажмите «Заказать» — заказ появится здесь."
                action={<Button iconLeft="search" onClick={onSearch}>К поиску</Button>} />
              : <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {account.orders.map((o, i) => (
                  <Row key={i}>
                    <Icon name="clock" size={18} style={{ color: "var(--status-issued)", flex: "none" }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{o.title}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{o.location}</div>
                    </div>
                    <Badge variant="warning">В очереди</Badge>
                    <Button size="sm" variant="ghost" onClick={() => onCancelOrder(i)}>Отменить</Button>
                  </Row>
                ))}
              </div>
          )}

          {tab === "bookmarks" && (
            (account.bookmarks || []).length === 0
              ? <EmptyState title="Закладок нет" description="Отмечайте записи кнопкой «Отметить» — они сохранятся здесь." />
              : <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {account.bookmarks.map((b) => (
                  <Row key={b.mfn}>
                    <Icon name="bookmark" size={18} style={{ color: "var(--accent)", flex: "none" }} />
                    <button type="button" onClick={() => onOpenBookmark(b)} style={{ flex: 1, minWidth: 0, textAlign: "left", border: "none", background: "none", cursor: "pointer", padding: 0 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{b.title}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{b.author}</div>
                    </button>
                    <Button size="sm" variant="ghost" iconLeft="trash" onClick={() => onRemoveBookmark(b.mfn)}>Убрать</Button>
                  </Row>
                ))}
              </div>
          )}

          {tab === "queries" && (
            (account.savedQueries || []).length === 0
              ? <EmptyState title="Нет постоянных запросов" description="Сохраняйте поисковые запросы — при новых записях придёт уведомление." />
              : <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {account.savedQueries.map((q) => (
                  <Row key={q.id}>
                    <Icon name="search" size={18} style={{ color: "var(--text-muted)", flex: "none" }} />
                    <button type="button" onClick={() => onRunQuery(q)} style={{ flex: 1, minWidth: 0, textAlign: "left", border: "none", background: "none", cursor: "pointer", padding: 0 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{q.label}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{q.db}</div>
                    </button>
                    {q.fresh > 0 && <Badge variant="accent">+{q.fresh} новых</Badge>}
                    <Button size="sm" variant="ghost" iconLeft="trash" onClick={() => onRemoveQuery(q.id)}>Удалить</Button>
                  </Row>
                ))}
              </div>
          )}

          {tab === "notify" && (
            (account.notifications || []).length === 0
              ? <EmptyState title="Уведомлений нет" description="Сроки возврата, готовность заказов и новое по запросам — здесь." />
              : <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {account.notifications.map((n) => (
                  <div key={n.id} style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)", background: n.unread ? "var(--accent-weak)" : "var(--surface-card)", border: "1px solid " + (n.unread ? "var(--accent-weak-border)" : "var(--border-subtle)"), borderRadius: "var(--radius-md)", padding: "var(--space-3) var(--space-4)" }}>
                    <Icon name={n.icon} size={18} style={{ color: TONE[n.tone] || TONE.neutral, flex: "none", marginTop: 2 }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{n.title}</div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{n.text}</div>
                    </div>
                    {n.unread && <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", flex: "none", marginTop: 5 }} />}
                  </div>
                ))}
              </div>
          )}

          {tab === "fines" && (
            finesTotal === 0
              ? <EmptyState icon="check-circle" title="Задолженностей нет" description="Штрафы отсутствуют. Спасибо, что возвращаете вовремя." />
              : <div>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
                  {account.fines.map((f) => (
                    <Row key={f.id}>
                      <Icon name="alert-triangle" size={18} style={{ color: "var(--danger-500)", flex: "none" }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{f.reason}</div>
                        <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>начислено {f.date}</div>
                      </div>
                      <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--text-strong)" }}>{f.amount} ₽</div>
                    </Row>
                  ))}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-4)", background: "var(--surface-card)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)" }}>
                  <span style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>Итого к оплате</span>
                  <span style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--text-strong)" }}>{finesTotal} ₽</span>
                  <div style={{ flex: 1 }} />
                  <Button iconLeft="credit-card" onClick={onPayFines}>Оплатить онлайн</Button>
                </div>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: "var(--space-3)" }}>Оплата проводится через защищённый шлюз; данные карты не хранятся в каталоге.</p>
              </div>
          )}
        </div>
      </div>
    );
  }

  Object.assign(window, { LoginScreen, FormularScreen });
})();
