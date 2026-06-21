// Кабинет → «История просмотров» (#134). Недавно открытые записи из GET
// /api/history; клик переоткрывает запись. Грациозная деградация: при 404/501
// (модуль истории ещё не подключён) секция скрывается (onUnavailable), кабинет
// не падает.
import React from "react";
import { api } from "../api";
import type { HistoryItem } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const COVER_TINTS = [
  "var(--cover-tint-1, #2F5D62)", "var(--cover-tint-2, #C96442)", "var(--cover-tint-3, #6B5CA5)",
  "var(--cover-tint-4, #3E4C7E)", "var(--cover-tint-5, #1F8A5B)", "var(--cover-tint-6, #8A4F9E)",
];

// Метка времени: ISO/число → «дд.мм.гггг, чч:мм»; иначе как есть.
function fmtTs(ts?: string): string {
  if (!ts) return "";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function HistoryTab({ cardSx, h2Sx, onUnavailable, refreshKey, onOpenRecord, standalone }: {
  cardSx: React.CSSProperties;
  h2Sx: React.CSSProperties;
  onUnavailable?: () => void;
  refreshKey?: number;
  onOpenRecord?: (db: string, mfn: number) => void;
  // standalone=true — компонент используется как отдельная вкладка кабинета: при
  // недоступности эндпойнта показываем информер вместо полного скрытия (null),
  // чтобы кликнутая вкладка не была пустой.
  standalone?: boolean;
}) {
  const [items, setItems] = React.useState<HistoryItem[] | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);

  const load = React.useCallback(async () => {
    const r = await api.history();
    if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
      setItems(r.json.data.items); setUnavailable(false);
    } else {
      setItems([]); setUnavailable(true); onUnavailable?.();
    }
  }, [onUnavailable]);

  React.useEffect(() => { load(); }, [load, refreshKey]);

  // Эндпойнта истории ещё нет → как вложенная секция скрываемся; как вкладка
  // показываем мягкий информер (вкладка не должна быть пустой).
  if (unavailable) {
    if (!standalone) return null;
    return (
      <section aria-labelledby="cab-history">
        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
          <h2 id="cab-history" style={h2Sx}>История просмотров</h2>
        </div>
        <div style={cardSx}>
          <EmptyState icon="clock" title="История пока недоступна" description="Модуль истории просмотров ещё подключается. Загляните позже." />
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="cab-history">
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "0 0 14px" }}>
        <h2 id="cab-history" style={h2Sx}>История просмотров</h2>
        {items && items.length > 0 && (
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-subtle)" }}>· {items.length}</span>
        )}
      </div>

      {items === null ? (
        <div style={{ color: "var(--text-subtle)", fontSize: "var(--text-sm)", padding: "4px 2px" }}>Загрузка истории…</div>
      ) : items.length === 0 ? (
        <div style={cardSx}>
          <EmptyState icon="clock" title="История пуста" description="Открытые вами записи появятся здесь — чтобы быстро к ним вернуться." />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((it, i) => (
            <button key={it.db + ":" + it.mfn + ":" + i} type="button" onClick={() => onOpenRecord?.(it.db, it.mfn)} disabled={!onOpenRecord}
              style={{ display: "flex", alignItems: "center", gap: 16, ...cardSx, borderRadius: "var(--radius-lg,13px)", padding: "12px 16px", textAlign: "left", width: "100%", cursor: onOpenRecord ? "pointer" : "default", fontFamily: "var(--font-ui,inherit)" }}>
              <span aria-hidden="true" style={{ width: 38, height: 52, flex: "none", borderRadius: 6, background: "linear-gradient(150deg," + COVER_TINTS[i % COVER_TINTS.length] + ",rgba(0,0,0,.35))", boxShadow: "var(--shadow-md)", display: "flex", alignItems: "flex-end", justifyContent: "center", padding: 4 }}>
                <Icon name="book" size={12} style={{ color: "rgba(255,255,255,.85)" }} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-base,15.5px)", lineHeight: 1.25, color: "var(--text-strong)", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{it.title || "Издание · " + it.db + "/" + it.mfn}</div>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--text-subtle)", marginTop: 3, display: "flex", gap: 12, flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--font-mono)" }}>{it.db} · {it.mfn}</span>
                  {it.ts && <span>просмотрено {fmtTs(it.ts)}</span>}
                </div>
              </div>
              {onOpenRecord && <Icon name="chevron-right" size={18} style={{ color: "var(--text-subtle)", flex: "none" }} />}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
