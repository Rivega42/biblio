import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { IconButton } from "../forms/IconButton.jsx";
import { EmptyState } from "../feedback/EmptyState.jsx";

/* Просмотрщик файла/изображения — VIEW-ONLY (§1.7, §10):
   - НЕТ кнопки скачивания и путей к файлу;
   - контекстное меню по правой кнопке ЗАБЛОКИРОВАНО;
   - перетаскивание изображения отключено;
   - при requiresAuth и отсутствии входа — состояние «нет прав»;
   - для PDF — подпись «документ pdf-формата».
   Приоритет поля 955 над 951 решает вызывающая сторона (выбор файла). */

const CSS = `
.irb-fv__back{position:fixed;inset:0;z-index:var(--z-modal);background:rgba(28,27,25,.46);
  backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:var(--space-5);}
.irb-fv{background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);width:min(880px,100%);max-height:92vh;
  display:flex;flex-direction:column;overflow:hidden;font-family:var(--font-ui);}
.irb-fv__head{display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) var(--space-4);
  border-bottom:var(--border-width) solid var(--border-subtle);}
.irb-fv__ic{flex:none;width:34px;height:34px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;
  background:var(--accent-weak);color:var(--accent);}
.irb-fv__t{min-width:0;flex:1;}
.irb-fv__title{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-fv__sub{font-size:var(--text-xs);color:var(--text-muted);}
.irb-fv__viewonly{display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs);font-weight:var(--weight-semibold);
  color:var(--text-muted);background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-pill);padding:2px 9px;}
.irb-fv__stage{flex:1;overflow:auto;background:var(--surface-sunken);display:flex;align-items:center;justify-content:center;
  padding:var(--space-6);min-height:280px;}
.irb-fv__page{background:#fff;border:var(--border-width) solid var(--border-subtle);box-shadow:var(--shadow-md);
  width:min(460px,100%);aspect-ratio:1 / 1.414;border-radius:var(--radius-xs);
  display:flex;flex-direction:column;padding:42px 40px;color:#2b2926;}
.irb-fv__page h4{font-family:var(--font-record-title);font-size:18px;margin:0 0 14px;}
.irb-fv__lines{display:flex;flex-direction:column;gap:9px;}
.irb-fv__lines i{display:block;height:8px;border-radius:3px;background:#e7e2d8;}
.irb-fv__img{width:100%;height:100%;display:flex;align-items:center;justify-content:center;border-radius:var(--radius-sm);}
.irb-fv__foot{display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) var(--space-4);
  border-top:var(--border-width) solid var(--border-subtle);}
.irb-fv__pg{font-size:var(--text-sm);color:var(--text-muted);font-variant-numeric:tabular-nums;}
.irb-fv__note{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);display:inline-flex;align-items:center;gap:6px;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-fv-css")) {
  const s = document.createElement("style");
  s.id = "irb-fv-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

const KIND_LABEL = { pdf: "документ pdf-формата", image: "изображение", djvu: "документ djvu-формата" };

// Демо-абзацы «страницы» с подсветкой искомых терминов (§4, §10).
const PAGE_TEXT = [
  "Пьеса написана в форме комедии в четырёх действиях. Действие происходит в усадьбе на берегу озера.",
  "Чайка как образ проходит через всю драму, становясь символом несбывшихся надежд героев.",
  "Премьера на сцене Александринского театра не имела успеха, однако постановка Художественного театра принесла признание.",
  "Композиция строится на контрасте бытовых сцен и внутренних монологов действующих лиц.",
];

function highlightText(text, terms) {
  if (!terms || !terms.length) return text;
  const safe = terms.filter(Boolean).map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).filter((t) => t.length > 1);
  if (!safe.length) return text;
  const re = new RegExp("(" + safe.join("|") + ")", "gi");
  const parts = String(text).split(re);
  return parts.map((p, i) => (re.test(p) ? <mark key={i} style={{ background: "var(--status-issued-bg)", color: "inherit", borderRadius: 2, padding: "0 1px" }}>{p}</mark> : p));
}

export function FileViewer({ open, file, title, canView = true, terms, relevantPages, onClose }) {
  const [page, setPage] = React.useState(1);
  React.useEffect(() => { if (open) setPage(relevantPages && relevantPages.length ? relevantPages[0] : 1); }, [open, file]);
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !file) return null;
  const kind = file.kind || "pdf";
  const pages = file.pages || 1;
  const denyContext = (e) => { e.preventDefault(); return false; };

  return (
    <div className="irb-fv__back" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose && onClose()}>
      <div className="irb-fv" role="dialog" aria-modal="true" aria-label={title || file.label} onContextMenu={denyContext}>
        <div className="irb-fv__head">
          <span className="irb-fv__ic"><Icon name={kind === "image" ? "image" : "file-text"} size={19} /></span>
          <div className="irb-fv__t">
            <div className="irb-fv__title">{file.label || title}</div>
            <div className="irb-fv__sub">{KIND_LABEL[kind] || kind}</div>
          </div>
          <span className="irb-fv__viewonly"><Icon name="eye" size={13} /> только просмотр</span>
          <IconButton icon="x" label="Закрыть" variant="ghost" onClick={onClose} />
        </div>

        {!canView ? (
          <div className="irb-fv__stage">
            <EmptyState variant="locked" icon="log-in" title="Нужен вход по билету"
              description="Полный текст доступен в читальном зале или после входа по читательскому билету." />
          </div>
        ) : (
          <>
            <div className="irb-fv__stage" onContextMenu={denyContext}>
              {kind === "image" ? (
                <div className="irb-fv__img" onContextMenu={denyContext} onDragStart={denyContext}
                  style={{ background: "hsl(" + (file.tint || 30) + " 32% 86%)", aspectRatio: "4 / 3", width: "min(560px,100%)", userSelect: "none" }}>
                  <Icon name="image" size={52} style={{ color: "hsl(" + (file.tint || 30) + " 38% 42%)" }} />
                </div>
              ) : (
                <div className="irb-fv__page" onContextMenu={denyContext} style={{ userSelect: "none" }}>
                  <h4>{file.label}{pages > 1 ? " · с. " + page : ""}</h4>
                  {terms && terms.length ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 11, fontSize: 14, lineHeight: 1.65, color: "#2b2926" }}>
                      {PAGE_TEXT.map((t, i) => <p key={i} style={{ margin: 0 }}>{highlightText(t, terms)}</p>)}
                    </div>
                  ) : (
                    <div className="irb-fv__lines">
                      {Array.from({ length: 11 }).map((_, i) => (
                        <i key={i} style={{ width: [92, 100, 86, 96, 70, 100, 90, 60, 98, 82, 44][i] + "%" }} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="irb-fv__foot">
              {relevantPages && relevantPages.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: 7, marginRight: 8 }}>
                  <span style={{ fontSize: "var(--text-2xs)", color: "var(--text-subtle)" }}>Релевантные с.:</span>
                  {relevantPages.map((p) => (
                    <button key={p} type="button" onClick={() => setPage(p)} style={{
                      border: "1px solid " + (p === page ? "var(--accent)" : "var(--border-default)"), cursor: "pointer",
                      background: p === page ? "var(--accent-weak)" : "var(--surface-card)", color: p === page ? "var(--accent-press)" : "var(--text-muted)",
                      borderRadius: "var(--radius-pill)", padding: "1px 9px", fontFamily: "var(--font-mono)", fontSize: "var(--text-2xs)", fontWeight: 600,
                    }}>{p}</button>
                  ))}
                </div>
              )}
              {kind !== "image" && pages > 1 && (
                <>
                  <IconButton icon="chevron-left" label="Предыдущая страница" size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} />
                  <span className="irb-fv__pg">Стр. {page} из {pages}</span>
                  <IconButton icon="chevron-right" label="Следующая страница" size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage((p) => Math.min(pages, p + 1))} />
                </>
              )}
              <span className="irb-fv__note"><Icon name="eye-off" size={13} /> Скачивание и копирование отключены</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
