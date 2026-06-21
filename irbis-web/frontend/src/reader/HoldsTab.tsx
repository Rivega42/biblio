// Кабинет → «Очередь брони» (#222). Реальные брони из GET /api/holds:
//   status 'ready'  → «Готов к получению» (+ срок until, если есть);
//   status 'queued' → «В очереди: вы N-й» с индикатором позиции.
// Отмена брони — POST /api/hold/cancel (оптимистично убираем строку). При 404/501
// эндпойнта брони ещё нет → деградируем: блок прячется (onUnavailable), кабинет не падает.
import React from "react";
import { api } from "../api";
import type { Hold } from "../api";
import type { ToastVariant } from "../../components/feedback/Toast.jsx";
import { Button } from "../../components/forms/Button.jsx";
import { Icon } from "../../components/icon/Icon.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

function readyChip(): React.CSSProperties {
  return { display: "inline-flex", alignItems: "center", gap: 6, background: "var(--status-available-bg,#E4F0E8)", color: "var(--status-available-strong,#2E7D52)", borderRadius: "var(--radius-md,6px)", padding: "4px 10px", fontSize: "var(--text-xs)", fontWeight: 600, whiteSpace: "nowrap" };
}
function queueChip(): React.CSSProperties {
  return { display: "inline-flex", alignItems: "center", gap: 6, background: "var(--status-hold-bg,#E3ECF8)", color: "var(--status-hold,#2F6DB5)", borderRadius: "var(--radius-md,6px)", padding: "4px 10px", fontSize: "var(--text-xs)", fontWeight: 600, whiteSpace: "nowrap" };
}

// Russian ordinal-ish: «вы 1-й», «вы 2-й» — всегда «-й» (разговорная форма очереди).
function posLabel(pos?: number): string {
  if (!pos || pos < 1) return "в очереди";
  return "вы " + pos + "-й в очереди";
}

export function HoldsTab({
  cardSx, h2Sx, demoHint, toast, onUnavailable, refreshKey,
}: {
  cardSx: React.CSSProperties;
  h2Sx: React.CSSProperties;
  demoHint: React.CSSProperties;
  toast: (t: { variant: ToastVariant; title: string; message?: string }) => void;
  onUnavailable?: () => void;
  refreshKey?: number;
}) {
  const [holds, setHolds] = React.useState<Hold[] | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const [busy, setBusy] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    const r = await api.holds();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setHolds(r.json.data.items); setUnavailable(false);
    } else {
      setHolds([]); setUnavailable(true); onUnavailable?.();
    }
  }, [onUnavailable]);

  React.useEffect(() => { load(); }, [load, refreshKey]);

  async function cancel(h: Hold) {
    setBusy(h.holdId);
    const r = await api.cancelHold(h.holdId);
    setBusy(null);
    if (r.status === 200) {
      setHolds((list) => (list || []).filter((x) => x.holdId !== h.holdId));
      toast({ variant: "success", title: "Бронь снята", message: h.title || "" });
    } else if (r.status === 401 || r.status === 403) {
      toast({ variant: "info", title: "Требуется вход", message: "Войдите по читательскому билету." });
    } else {
      toast({ variant: "error", title: "Не удалось снять бронь", message: "Повторите попытку позже." });
    }
  }

  // Эндпойнта брони ещё нет → секцию не показываем (мягкая деградация).
  if (unavailable) return null;

  return (
    <section aria-labelledby="cab-holds">
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
        <h2 id="cab-holds" style={h2Sx}>Очередь брони</h2>
        {holds && holds.length > 0 && (
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>· {holds.length}</span>
        )}
      </div>

      {holds === null ? (
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", padding: "4px 2px" }}>Загрузка броней…</div>
      ) : holds.length === 0 ? (
        <div style={cardSx}>
          <EmptyState icon="clock" title="Активных броней нет" description="Забронируйте издание в каталоге — оно появится здесь с позицией в очереди." />
        </div>
      ) : (
        <div className="irb-cab-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {holds.map((h, i) => {
            const ready = h.status === "ready";
            const pos = h.position;
            return (
              <div key={h.holdId} style={{ ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: 16 }}>
                <div style={{ display: "flex", gap: 13, alignItems: "flex-start" }}>
                  <span aria-hidden="true" style={{ width: 38, height: 52, flex: "none", borderRadius: 6, background: "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.35))", boxShadow: "var(--shadow-md)", display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 4 }}>
                    <Icon name="book" size={12} style={{ color: "rgba(255,255,255,.85)" }} />
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-sm,15px)", lineHeight: 1.25, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{h.title || "Издание"}</div>
                    <div style={{ marginTop: 8 }}>
                      {ready ? (
                        <span style={readyChip()}><span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 999, background: "var(--status-available,#2E7D52)" }} />Готов к получению{h.until ? " · до " + h.until : ""}</span>
                      ) : (
                        <span style={queueChip()}><span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 999, background: "var(--status-hold,#2F6DB5)" }} />{posLabel(pos)}</span>
                      )}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
                  <Button variant="ghost" size="sm" iconLeft="x" loading={busy === h.holdId} onClick={() => cancel(h)}>Снять бронь</Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
