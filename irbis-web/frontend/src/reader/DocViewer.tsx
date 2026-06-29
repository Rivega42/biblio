// Постраничный просмотрщик документов/изображений (#222) — заменяет одиночную
// картинку-заглушку. Модальное полноэкранное окно с навигацией по страницам
// (назад/вперёд, «стр. N из M»), зумом для изображений и фолбэком для не-картинок
// (PDF/внешние ссылки открываются в новой вкладке). Самодостаточный компонент:
// принимает массив страниц `pages` и стартовый индекс.
//
// Грациозная деградация: если у картинки не грузится src (onError) — показываем
// заглушку «страница недоступна», окно не падает. Клавиатура: ←/→ листают,
// +/− зумируют, Esc закрывает.
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";
import { PdfViewer } from "./PdfViewer";

export interface DocPage {
  // Подпись страницы/файла (имя из записи).
  name?: string;
  // URL ресурса. Для изображений — прямая ссылка на картинку; для PDF/прочего —
  // внешняя ссылка (откроется в новой вкладке кнопкой «Открыть»).
  url?: string;
  // Тип содержимого: image — рисуем во вьюере с зумом; file — внешний файл/ссылка.
  kind?: "image" | "file";
}

// Эвристика: похоже ли на изображение по расширению URL.
function looksLikeImage(url?: string): boolean {
  if (!url) return false;
  return /\.(png|jpe?g|gif|webp|bmp|tiff?|svg)(\?|#|$)/i.test(url);
}

// Эвристика: PDF по расширению URL (для встроенного постраничного pdf.js-вьюера).
function looksLikePdf(url?: string): boolean {
  if (!url) return false;
  return /\.pdf(\?|#|$)/i.test(url);
}

const CSS = `
.irb-doc{position:fixed;inset:0;z-index:80;background:rgba(15,12,10,.86);display:flex;flex-direction:column;
  backdrop-filter:blur(2px);}
.irb-doc__bar{display:flex;align-items:center;gap:12px;padding:12px 18px;color:#fff;
  background:rgba(0,0,0,.32);border-bottom:1px solid rgba(255,255,255,.12);flex-wrap:wrap;}
.irb-doc__title{font-family:var(--font-display,var(--font-serif));font-weight:600;font-size:var(--text-base,15.5px);
  min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:46vw;}
.irb-doc__count{font-size:var(--text-sm);color:rgba(255,255,255,.8);font-variant-numeric:tabular-nums;white-space:nowrap;}
.irb-doc__spacer{flex:1;}
.irb-doc__btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;background:rgba(255,255,255,.12);
  color:#fff;border:1px solid rgba(255,255,255,.28);border-radius:9px;padding:7px 11px;cursor:pointer;
  font-size:var(--text-sm);font-family:var(--font-ui,inherit);}
.irb-doc__btn:hover:not(:disabled){background:rgba(255,255,255,.22);}
.irb-doc__btn:disabled{opacity:.4;cursor:not-allowed;}
.irb-doc__btn--icon{padding:7px 9px;}
.irb-doc__stage{flex:1;min-height:0;overflow:auto;display:flex;align-items:center;justify-content:center;padding:20px;}
.irb-doc__img{display:block;border-radius:8px;box-shadow:0 14px 50px rgba(0,0,0,.5);background:#fff;
  transform-origin:center center;transition:transform var(--dur-fast,.12s) var(--ease-standard,ease);}
.irb-doc__file{display:flex;flex-direction:column;align-items:center;gap:14px;color:#fff;text-align:center;max-width:460px;}
.irb-doc__file-ic{width:84px;height:84px;border-radius:18px;background:rgba(255,255,255,.1);
  display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.92);}
.irb-doc__nav{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.4);color:#fff;
  border:1px solid rgba(255,255,255,.28);border-radius:999px;width:46px;height:46px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;}
.irb-doc__nav:hover:not(:disabled){background:rgba(0,0,0,.6);}
.irb-doc__nav:disabled{opacity:.35;cursor:not-allowed;}
.irb-doc__nav--prev{left:14px;}
.irb-doc__nav--next{right:14px;}
.irb-doc__thumbs{display:flex;gap:6px;overflow-x:auto;padding:8px 14px;background:rgba(0,0,0,.32);
  border-top:1px solid rgba(255,255,255,.12);scrollbar-width:thin;}
.irb-doc__thumb{flex:none;min-width:40px;height:30px;border-radius:6px;border:1px solid rgba(255,255,255,.28);
  background:rgba(255,255,255,.1);color:#fff;cursor:pointer;font-size:var(--text-xs);font-family:var(--font-ui,inherit);
  display:flex;align-items:center;justify-content:center;padding:0 8px;}
.irb-doc__thumb--on{background:var(--accent);border-color:var(--accent);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-doc-css")) {
  const s = document.createElement("style"); s.id = "irb-doc-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function DocViewer({ pages, startIndex = 0, title, onClose }: {
  pages: DocPage[];
  startIndex?: number;
  title?: string;
  onClose: () => void;
}) {
  const [idx, setIdx] = React.useState(Math.min(Math.max(0, startIndex), Math.max(0, pages.length - 1)));
  const [zoom, setZoom] = React.useState(1);
  const [imgError, setImgError] = React.useState(false);
  const [pdfOpen, setPdfOpen] = React.useState(false);

  const total = pages.length;
  const page = pages[idx] || { name: "" };
  const isImage = page.kind === "image" || (page.kind !== "file" && looksLikeImage(page.url));
  const isPdf = !isImage && looksLikePdf(page.url);

  const go = React.useCallback((next: number) => {
    setIdx((cur) => {
      const n = Math.min(Math.max(0, next), Math.max(0, total - 1));
      if (n !== cur) { setZoom(1); setImgError(false); }
      return n;
    });
  }, [total]);

  // Клавиатура: листание, зум, закрытие.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(idx + 1);
      else if (e.key === "ArrowLeft") go(idx - 1);
      else if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2)));
      else if (e.key === "-" || e.key === "_") setZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2)));
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [idx, go, onClose]);

  if (!total) return null;

  return (
    <div className="irb-doc" role="dialog" aria-modal="true" aria-label={"Просмотр: " + (title || page.name || "документ")}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      {/* Верхняя панель */}
      <div className="irb-doc__bar">
        <span className="irb-doc__title">{title || page.name || "Документ"}</span>
        <span className="irb-doc__count">стр. {idx + 1} из {total}</span>
        <span className="irb-doc__spacer" />
        {isImage && !imgError && (
          <>
            <button type="button" className="irb-doc__btn irb-doc__btn--icon" onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2)))} disabled={zoom <= 0.5} aria-label="Уменьшить" title="Уменьшить (−)">
              <Icon name="minus" size={16} />
            </button>
            <span className="irb-doc__count" style={{ minWidth: 44, textAlign: "center" }}>{Math.round(zoom * 100)}%</span>
            <button type="button" className="irb-doc__btn irb-doc__btn--icon" onClick={() => setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2)))} disabled={zoom >= 4} aria-label="Увеличить" title="Увеличить (+)">
              <Icon name="plus" size={16} />
            </button>
            <button type="button" className="irb-doc__btn irb-doc__btn--icon" onClick={() => setZoom(1)} disabled={zoom === 1} aria-label="Сбросить масштаб" title="Сбросить масштаб">
              <Icon name="maximize" size={16} />
            </button>
          </>
        )}
        {isPdf && page.url && (
          <button type="button" className="irb-doc__btn" onClick={() => setPdfOpen(true)} title="Листать PDF постранично">
            <Icon name="book-open" size={15} /> Постранично
          </button>
        )}
        {page.url && (
          <a className="irb-doc__btn" href={page.url} target="_blank" rel="noopener noreferrer" title="Открыть в новой вкладке">
            <Icon name="external-link" size={15} /> Открыть
          </a>
        )}
        <button type="button" className="irb-doc__btn irb-doc__btn--icon" onClick={onClose} aria-label="Закрыть просмотр" title="Закрыть (Esc)">
          <Icon name="x" size={18} />
        </button>
      </div>

      {/* Сцена с навигацией */}
      <div className="irb-doc__stage" style={{ position: "relative" }}>
        {total > 1 && (
          <button type="button" className="irb-doc__nav irb-doc__nav--prev" onClick={() => go(idx - 1)} disabled={idx === 0} aria-label="Предыдущая страница">
            <Icon name="chevron-left" size={22} />
          </button>
        )}

        {isImage && page.url && !imgError ? (
          <img className="irb-doc__img" src={page.url} alt={page.name || "Страница " + (idx + 1)}
            style={{ transform: "scale(" + zoom + ")", maxWidth: zoom <= 1 ? "100%" : "none", maxHeight: zoom <= 1 ? "100%" : "none" }}
            onError={() => setImgError(true)} />
        ) : (
          <div className="irb-doc__file">
            <span className="irb-doc__file-ic" aria-hidden="true">
              <Icon name={imgError ? "image" : "file-text"} size={40} />
            </span>
            <div style={{ fontFamily: "var(--font-display,var(--font-serif))", fontWeight: 600, fontSize: "var(--text-lg)" }}>
              {imgError ? "Страница недоступна" : (page.name || "Документ")}
            </div>
            <div style={{ fontSize: "var(--text-sm)", color: "rgba(255,255,255,.78)", lineHeight: 1.5 }}>
              {imgError
                ? "Не удалось загрузить изображение этой страницы."
                : isPdf
                  ? "PDF можно листать постранично прямо здесь."
                  : "Предпросмотр этого файла недоступен во встроенном просмотрщике."}
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
              {isPdf && page.url && (
                <button type="button" className="irb-doc__btn" onClick={() => setPdfOpen(true)}>
                  <Icon name="book-open" size={15} /> Открыть постранично
                </button>
              )}
              {page.url && (
                <a className="irb-doc__btn" href={page.url} target="_blank" rel="noopener noreferrer">
                  <Icon name="external-link" size={15} /> Открыть файл
                </a>
              )}
            </div>
          </div>
        )}

        {total > 1 && (
          <button type="button" className="irb-doc__nav irb-doc__nav--next" onClick={() => go(idx + 1)} disabled={idx === total - 1} aria-label="Следующая страница">
            <Icon name="chevron-right" size={22} />
          </button>
        )}
      </div>

      {/* Лента-нумератор страниц */}
      {total > 1 && (
        <div className="irb-doc__thumbs" role="tablist" aria-label="Страницы">
          {pages.map((p, i) => (
            <button key={i} type="button" role="tab" aria-selected={i === idx}
              className={"irb-doc__thumb" + (i === idx ? " irb-doc__thumb--on" : "")}
              onClick={() => go(i)} title={p.name || "Страница " + (i + 1)}>
              {i + 1}
            </button>
          ))}
        </div>
      )}

      {pdfOpen && page.url && (
        <PdfViewer url={page.url} title={page.name || title} onClose={() => setPdfOpen(false)} />
      )}
    </div>
  );
}
