// IIIF deep-zoom просмотрщик (#240) — OpenSeadragon поверх образов IIIF-манифеста.
// Глубокий зум/панорамирование + постраничная навигация (sequenceMode). Тайловых
// источников у нас нет (DAM хранит URL образов), поэтому каждый образ подаётся как
// simple-image tile source — OSD всё равно даёт плавный зум/пан. Кнопки —
// собственный тулбар (не дефолтные OSD-кнопки), чтобы не тянуть их CDN-ассеты.
import React from "react";
import OpenSeadragon from "openseadragon";
import { Icon } from "../../components/icon/Icon.jsx";

export interface ViewerPage { url?: string; name?: string }

export function IiifViewer({ pages, title, onClose }: { pages: ViewerPage[]; title?: string; onClose: () => void }) {
  const hostRef = React.useRef<HTMLDivElement | null>(null);
  const osdRef = React.useRef<any>(null);
  const [page, setPage] = React.useState(0);
  const urls = React.useMemo(() => pages.map((p) => p.url).filter((u): u is string => !!u), [pages]);
  const multi = urls.length > 1;

  React.useEffect(() => {
    if (!hostRef.current || !urls.length) return;
    const viewer = OpenSeadragon({
      element: hostRef.current,
      tileSources: urls.map((u) => ({ type: "image", url: u })) as any,
      sequenceMode: multi,
      showNavigationControl: false,   // свой тулбар (без OSD-ассетов кнопок)
      showSequenceControl: false,
      showNavigator: true,
      navigatorPosition: "BOTTOM_RIGHT",
      gestureSettingsMouse: { clickToZoom: false },
      crossOriginPolicy: "Anonymous",
      animationTime: 0.4,
    });
    osdRef.current = viewer;
    viewer.addHandler("page", (e: any) => setPage(e.page));
    return () => { viewer.destroy(); osdRef.current = null; };
  }, [urls, multi]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight" && multi) osdRef.current?.goToPage(Math.min(urls.length - 1, page + 1));
      else if (e.key === "ArrowLeft" && multi) osdRef.current?.goToPage(Math.max(0, page - 1));
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [page, multi, urls.length, onClose]);

  const zoom = (f: number) => { const v = osdRef.current; if (v) { v.viewport.zoomBy(f); v.viewport.applyConstraints(); } };
  const home = () => osdRef.current?.viewport.goHome();
  const go = (d: number) => osdRef.current?.goToPage(Math.max(0, Math.min(urls.length - 1, page + d)));

  const btn: React.CSSProperties = { display: "inline-flex", alignItems: "center", justifyContent: "center", width: 34, height: 34, borderRadius: 8, border: "1px solid rgba(255,255,255,.25)", background: "rgba(0,0,0,.35)", color: "#fff", cursor: "pointer" };
  return (
    <div role="dialog" aria-modal="true" aria-label={"Просмотр: " + (title || "оцифровка")}
      style={{ position: "fixed", inset: 0, zIndex: 95, background: "rgba(12,10,9,.92)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", color: "#fff", flexWrap: "wrap" }}>
        <b style={{ fontSize: 15, fontWeight: 500, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title || "Оцифрованный документ"}</b>
        {multi && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <button type="button" style={btn} onClick={() => go(-1)} disabled={page === 0} aria-label="Предыдущая страница"><Icon name="chevron-left" size={18} /></button>
            <span style={{ fontSize: 13, minWidth: 78, textAlign: "center" }}>стр. {page + 1} из {urls.length}</span>
            <button type="button" style={btn} onClick={() => go(1)} disabled={page === urls.length - 1} aria-label="Следующая страница"><Icon name="chevron-right" size={18} /></button>
          </span>
        )}
        <span style={{ display: "inline-flex", gap: 6 }}>
          <button type="button" style={btn} onClick={() => zoom(1.4)} aria-label="Приблизить"><Icon name="plus" size={18} /></button>
          <button type="button" style={btn} onClick={() => zoom(0.7)} aria-label="Отдалить"><Icon name="minus" size={18} /></button>
          <button type="button" style={btn} onClick={home} aria-label="По размеру окна"><Icon name="maximize" size={16} /></button>
        </span>
        <button type="button" style={{ ...btn, marginLeft: 4 }} onClick={onClose} aria-label="Закрыть (Esc)"><Icon name="x" size={18} /></button>
      </div>
      <div ref={hostRef} style={{ flex: 1, minHeight: 0, background: "#0c0a09" }} />
    </div>
  );
}
