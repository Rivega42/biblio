// Встроенный постраничный PDF-просмотрщик (#369) на pdf.js. Рендерит страницы в
// canvas по одной (ленивая отрисовка текущей), зум, навигация, клавиши ←/→/Esc.
// Закрывает пробел против web-reader ИРБИС: PDF больше не открывается внешней
// ссылкой, а листается в приложении. Гейтинг прав (Ф2) выражен через maxPages —
// сколько страниц разрешено показать (лимит ^F из rights); сверх лимита — баннер.
import React from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Icon } from "../../components/icon/Icon.jsx";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

export function PdfViewer({ url, title, maxPages, onClose }: { url: string; title?: string; maxPages?: number; onClose: () => void }) {
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const docRef = React.useRef<any>(null);
  const renderTaskRef = React.useRef<any>(null);
  const [numPages, setNumPages] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [scale, setScale] = React.useState(1.2);
  const [state, setState] = React.useState<"loading" | "ready" | "error">("loading");

  // Сколько страниц разрешено показать (гейтинг прав). 0/нет лимита → все.
  const allowed = maxPages && maxPages > 0 ? Math.min(numPages, maxPages) : numPages;
  const capped = !!(maxPages && maxPages > 0 && numPages > maxPages);

  // Загрузка документа один раз на url.
  React.useEffect(() => {
    let alive = true;
    setState("loading"); setPage(1); setNumPages(0);
    const task = pdfjsLib.getDocument({ url });
    task.promise.then((pdf: any) => {
      if (!alive) { try { pdf.destroy(); } catch { /* noop */ } return; }
      docRef.current = pdf;
      setNumPages(pdf.numPages);
      setState("ready");
    }).catch(() => { if (alive) setState("error"); });
    return () => {
      alive = false;
      try { renderTaskRef.current?.cancel(); } catch { /* noop */ }
      try { docRef.current?.destroy(); } catch { /* noop */ }
      docRef.current = null;
    };
  }, [url]);

  // Отрисовка текущей страницы при смене page/scale/готовности.
  React.useEffect(() => {
    const pdf = docRef.current;
    if (state !== "ready" || !pdf || !canvasRef.current) return;
    let alive = true;
    (async () => {
      try {
        const pg = await pdf.getPage(Math.min(page, allowed || 1));
        if (!alive) return;
        const viewport = pg.getViewport({ scale });
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        try { renderTaskRef.current?.cancel(); } catch { /* noop */ }
        const rt = pg.render({ canvasContext: ctx, viewport });
        renderTaskRef.current = rt;
        await rt.promise;
      } catch { /* отмена рендера/гонка — игнор */ }
    })();
    return () => { alive = false; };
  }, [page, scale, state, allowed]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") setPage((p) => Math.min(allowed || 1, p + 1));
      else if (e.key === "ArrowLeft") setPage((p) => Math.max(1, p - 1));
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [allowed, onClose]);

  const go = (d: number) => setPage((p) => Math.max(1, Math.min(allowed || 1, p + d)));
  const zoom = (f: number) => setScale((s) => Math.max(0.4, Math.min(4, +(s * f).toFixed(2))));

  const btn: React.CSSProperties = { display: "inline-flex", alignItems: "center", justifyContent: "center", width: 34, height: 34, borderRadius: 8, border: "1px solid rgba(255,255,255,.25)", background: "rgba(0,0,0,.35)", color: "#fff", cursor: "pointer" };
  return (
    <div role="dialog" aria-modal="true" aria-label={"Просмотр PDF: " + (title || "документ")}
      style={{ position: "fixed", inset: 0, zIndex: 95, background: "rgba(12,10,9,.93)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", color: "#fff", flexWrap: "wrap" }}>
        <b style={{ fontSize: 15, fontWeight: 500, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title || "PDF-документ"}</b>
        {state === "ready" && allowed > 1 && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <button type="button" style={btn} onClick={() => go(-1)} disabled={page <= 1} aria-label="Предыдущая страница"><Icon name="chevron-left" size={18} /></button>
            <span style={{ fontSize: 13, minWidth: 96, textAlign: "center" }}>стр. {page} из {allowed}{capped ? " · из " + numPages : ""}</span>
            <button type="button" style={btn} onClick={() => go(1)} disabled={page >= allowed} aria-label="Следующая страница"><Icon name="chevron-right" size={18} /></button>
          </span>
        )}
        <span style={{ display: "inline-flex", gap: 6 }}>
          <button type="button" style={btn} onClick={() => zoom(1.25)} aria-label="Приблизить"><Icon name="plus" size={18} /></button>
          <button type="button" style={btn} onClick={() => zoom(0.8)} aria-label="Отдалить"><Icon name="minus" size={18} /></button>
        </span>
        <button type="button" style={{ ...btn, marginLeft: 4 }} onClick={onClose} aria-label="Закрыть (Esc)"><Icon name="x" size={18} /></button>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: "auto", display: "flex", flexDirection: "column", alignItems: "center", padding: 16 }}>
        {state === "loading" && <div style={{ color: "rgba(255,255,255,.7)", fontSize: 14, margin: "auto" }}>Загрузка PDF…</div>}
        {state === "error" && <div style={{ color: "rgba(255,255,255,.7)", fontSize: 14, margin: "auto" }}>Не удалось открыть PDF.</div>}
        {state === "ready" && <canvas ref={canvasRef} style={{ maxWidth: "100%", boxShadow: "0 2px 18px rgba(0,0,0,.5)", background: "#fff" }} />}
        {capped && state === "ready" && page >= allowed && (
          <div style={{ margin: "14px auto 0", maxWidth: 420, textAlign: "center", color: "#fff", background: "rgba(186,117,23,.25)", border: "1px solid rgba(186,117,23,.5)", borderRadius: 10, padding: "12px 16px", fontSize: 13 }}>
            Доступно {allowed} из {numPages} страниц по вашему уровню доступа. Полный текст — в читальном зале или по расширенному праву.
          </div>
        )}
      </div>
    </div>
  );
}
