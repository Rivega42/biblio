/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const { Dialog, Button, Radio, StatusBadge, Icon, Alert } = NS;

  function OrderModal({ open, record, onClose, onConfirm }) {
    const [step, setStep] = React.useState("select");
    const [sel, setSel] = React.useState(null);

    React.useEffect(() => {
      if (open) {
        setStep("select");
        const firstAvail = (record && record.holdings || []).findIndex((h) => h.status === "available");
        setSel(firstAvail >= 0 ? firstAvail : null);
      }
    }, [open, record]);

    if (!record) return null;
    const holdings = record.holdings || [];
    const anyAvail = holdings.some((h) => h.status === "available");

    const footer = step === "select" ? (
      <>
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button disabled={sel === null} iconLeft="chevron-right" onClick={() => setStep("confirm")}>Далее</Button>
      </>
    ) : step === "confirm" ? (
      <>
        <Button variant="secondary" onClick={() => setStep("select")}>Назад</Button>
        <Button iconLeft="check" onClick={() => { onConfirm(holdings[sel]); setStep("result"); }}>Подтвердить заказ</Button>
      </>
    ) : (
      <Button onClick={onClose}>Готово</Button>
    );

    return (
      <Dialog open={open} onClose={onClose} size="md"
        title={step === "result" ? "Заказ принят" : "Заказ издания"}
        subtitle={step === "result" ? undefined : record.title}
        footer={footer}>
        {step === "select" && (
          !anyAvail ? (
            <Alert variant="warning" title="Нет доступных экземпляров">
              Все экземпляры сейчас выданы. Попробуйте позже или обратитесь к библиотекарю.
            </Alert>
          ) : (
            <div>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", marginBottom: "var(--space-3)" }}>
                Выберите экземпляр и место выдачи:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {holdings.map((h, i) => {
                  const ok = h.status === "available";
                  return (
                    <label key={i} style={{
                      display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-3)",
                      borderBottom: "1px solid var(--border-subtle)", cursor: ok ? "pointer" : "not-allowed", opacity: ok ? 1 : 0.55,
                    }}>
                      <Radio name="hold" checked={sel === i} disabled={!ok} onChange={() => setSel(i)} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: "var(--text-strong)", fontSize: "var(--text-sm)" }}>{h.location}</div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{h.inventory}</div>
                      </div>
                      <StatusBadge status={h.status} size="sm" />
                    </label>
                  );
                })}
              </div>
            </div>
          )
        )}

        {step === "confirm" && sel !== null && (
          <div style={{ fontSize: "var(--text-sm)", color: "var(--text-body)", lineHeight: 1.6 }}>
            <p style={{ marginBottom: "var(--space-3)" }}>Будет оформлен заказ:</p>
            <div style={{ background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", padding: "var(--space-4)", display: "grid", gridTemplateColumns: "max-content 1fr", gap: "8px 16px" }}>
              <span style={{ color: "var(--text-muted)" }}>Издание</span><b>{record.title}</b>
              <span style={{ color: "var(--text-muted)" }}>Экземпляр</span><span style={{ fontFamily: "var(--font-mono)" }}>{holdings[sel].inventory}</span>
              <span style={{ color: "var(--text-muted)" }}>Место выдачи</span><span>{holdings[sel].location}</span>
            </div>
            <p style={{ marginTop: "var(--space-3)", color: "var(--text-muted)" }}>Экземпляр будет поставлен в очередь выдачи. Заказ появится в личном кабинете.</p>
          </div>
        )}

        {step === "result" && (
          <div style={{ textAlign: "center", padding: "var(--space-4) 0" }}>
            <span style={{ display: "inline-flex", width: 56, height: 56, borderRadius: "var(--radius-round)", background: "var(--success-bg)", color: "var(--status-available)", alignItems: "center", justifyContent: "center", marginBottom: "var(--space-3)" }}>
              <Icon name="check-circle" size={30} />
            </span>
            <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>Заказ принят и поставлен в очередь</h3>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
              Экземпляр <b style={{ fontFamily: "var(--font-mono)" }}>{sel !== null ? holdings[sel].inventory : ""}</b> ожидает в «{sel !== null ? holdings[sel].location : ""}».
              Статус заказа виден в личном кабинете.
            </p>
          </div>
        )}
      </Dialog>
    );
  }

  Object.assign(window, { OrderModal });
})();
