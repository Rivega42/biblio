// Кабинет → вкладка «Заказы» (G12). Список заказов читателя со статусом и
// возможностью отмены до выдачи (cancelable). Данные из GET /api/me/orders; если
// эндпойнта ещё нет (404) — показываем демонстрационную заглушку (помечено «демо»),
// чтобы экран не был пустым. Отмена зовёт POST /api/me/orders/cancel и убирает
// строку оптимистично; при ошибке — тост и откат.
import React from "react";
import { api } from "../api";
import type { OrderItem } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

// Семантика статуса заказа → пресет статус-бейджа (цвет/подложка из токенов).
const ORDER_STATUS: Record<string, { label: string; fg: string; bg: string; dot: string }> = {
  queued: { label: "В очереди", fg: "var(--status-hold,#2F6DB5)", bg: "var(--status-hold-bg,#E3ECF8)", dot: "var(--status-hold,#2F6DB5)" },
  ready: { label: "Готов к выдаче", fg: "var(--status-available-strong,#2E7D52)", bg: "var(--status-available-bg,#E4F0E8)", dot: "var(--status-available,#2E7D52)" },
  issued: { label: "Выдан", fg: "var(--status-issued-strong,#9A6A12)", bg: "var(--status-issued-bg,#F7ECD6)", dot: "var(--status-issued,#9A6A12)" },
  cancelled: { label: "Отменён", fg: "var(--text-subtle,#8A857A)", bg: "var(--surface-sunken,#F0EEE6)", dot: "var(--text-subtle,#8A857A)" },
};

function chip(st: string): React.CSSProperties {
  const c = ORDER_STATUS[st] || ORDER_STATUS.queued;
  return { display: "inline-flex", alignItems: "center", gap: 6, background: c.bg, color: c.fg, borderRadius: "var(--radius-md,6px)", padding: "4px 10px", fontSize: "var(--text-xs)", fontWeight: 600, whiteSpace: "nowrap" };
}

export function OrdersTab({ toast, cardSx }: {
  toast: (t: { variant: ToastVariant; title: string; message?: string }) => void;
  cardSx: React.CSSProperties;
}) {
  const [orders, setOrders] = React.useState<OrderItem[] | null>(null);
  const [stub, setStub] = React.useState(false);
  const [busy, setBusy] = React.useState<string | number | null>(null);

  const load = React.useCallback(async () => {
    const r = await api.orders();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setOrders(r.json.data.items); setStub(false);
    } else {
      // Эндпойнта нет / не готов → честный пустой список (без выдуманных заказов).
      setOrders([]); setStub(false);
    }
  }, []);

  React.useEffect(() => { load(); }, [load]);

  async function cancel(o: OrderItem) {
    const key = o.id ?? o.mfn;
    if (stub) {
      // Демо-режим: отменяем локально, backend ещё нет.
      setOrders((list) => (list || []).map((x) => (x.id ?? x.mfn) === key ? { ...x, status: "cancelled", statusLabel: "Отменён", cancelable: false } : x));
      toast({ variant: "info", title: "Демо-режим", message: "Отмена заказов появится после подключения модуля бронирования." });
      return;
    }
    setBusy(key);
    const r = await api.cancelOrder(o.id ?? "", o.db, o.mfn);
    setBusy(null);
    if (r.status === 200) {
      setOrders((list) => (list || []).map((x) => (x.id ?? x.mfn) === key ? { ...x, status: "cancelled", statusLabel: "Отменён", cancelable: false } : x));
      toast({ variant: "success", title: "Заказ отменён", message: o.title || "" });
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." });
    } else {
      toast({ variant: "error", title: "Не удалось отменить", message: "Повторите попытку позже." });
    }
  }

  if (orders === null) {
    return <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", padding: "8px 2px" }}>Загрузка заказов…</div>;
  }

  const active = orders.filter((o) => o.status !== "cancelled");
  if (!active.length && !orders.length) {
    return (
      <div style={cardSx}>
        <EmptyState icon="clipboard-check" title="Заказов нет" description="Закажите издание в каталоге — заказ появится здесь со статусом выдачи." />
      </div>
    );
  }

  return (
    <div>
      {stub && (
        <p style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-2xs,11px)", color: "var(--text-subtle)", background: "var(--surface-sunken)", borderRadius: 999, padding: "3px 10px", margin: "0 0 12px", fontWeight: 600 }}>
          <Icon name="info" size={12} /> демонстрационные данные — модуль заказов ещё подключается
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {orders.map((o) => {
          const st = o.status || "queued";
          const cfg = ORDER_STATUS[st] || ORDER_STATUS.queued;
          const key = o.id ?? o.mfn;
          return (
            <div key={String(key)} style={{ display: "flex", alignItems: "center", gap: 16, ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: "14px 16px", opacity: st === "cancelled" ? .6 : 1 }}>
              <span aria-hidden="true" style={{ width: 40, height: 56, flex: "none", borderRadius: 6, background: "linear-gradient(150deg,var(--cover-tint-1,#2F5D62),rgba(0,0,0,.35))", boxShadow: "var(--shadow-md)", display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 4 }}>
                <Icon name="book" size={13} style={{ color: "rgba(255,255,255,.85)" }} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-base,15.5px)", lineHeight: 1.25, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{o.title || "Издание"}</div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 3, display: "flex", gap: 12, flexWrap: "wrap" }}>
                  {o.author && <span>{o.author}</span>}
                  {o.place && <span><Icon name="map-pin" size={11} style={{ verticalAlign: "-1px" }} /> {o.place}</span>}
                  {o.created && <span>заказан {o.created}</span>}
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flex: "none" }}>
                <span style={chip(st)}><span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 999, background: cfg.dot, flex: "none" }} />{o.statusLabel || cfg.label}</span>
                {o.cancelable && st !== "cancelled" && (
                  <Button variant="ghost" size="sm" iconLeft="x" loading={busy === key} onClick={() => cancel(o)}>Отменить</Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
