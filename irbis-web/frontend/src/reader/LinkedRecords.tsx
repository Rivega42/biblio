// Карточка записи — новые блоки иерархии издания и полного текста:
//   InThisEdition («В этом издании») — что входит В издание: статьи журнала,
//     номера, тома (GET /api/linked/{db}/{mfn}?kind=children). Кликабельно —
//     открывает связанную запись.
//   RecordHost («Источник») — издание-хозяин для аналитической росписи
//     (GET /api/linked/{db}/{mfn}?kind=host). Клик открывает запись-хозяина.
//   FulltextBlock («Полный текст») — артефакты ПТ + бейдж доступа категории
//     читателя (deny/view/download) + остаток квоты страниц
//     (GET /api/fulltext/{db}/{mfn}). Кнопка просмотра активна по уровню;
//     при deny — подпись «недоступно для вашей категории».
//
// Все три блока — самодостаточные, с грациозной деградацией: при 404/501 или
// пустом ответе блок просто не рендерится (карточка не ломается).
import React from "react";
import { api } from "../api";
import type { LinkedItem, LinkedKind, FulltextArtifact, FulltextLevel } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";
import type { DocPage } from "./DocViewer";

const CSS = `
.irb-link{margin-top:24px;border-top:1px solid var(--border-subtle);padding-top:16px;}
.irb-link__head{display:flex;align-items:baseline;gap:9px;margin:0 0 11px;}
.irb-link__title{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);
  font-size:var(--text-lg,1.125rem);letter-spacing:-.01em;margin:0;color:var(--text-strong);
  display:inline-flex;align-items:center;gap:7px;}
.irb-link__count{font-size:var(--text-sm);color:var(--text-subtle);}
.irb-link__list{display:flex;flex-direction:column;}
.irb-link__item{display:flex;align-items:center;gap:9px;width:100%;text-align:left;
  background:transparent;border:none;border-top:1px solid var(--border-subtle);
  padding:10px 4px;cursor:pointer;font:inherit;color:var(--text-body);
  transition:background var(--dur,.15s) var(--ease-standard,ease);border-radius:6px;}
.irb-link__item:first-child{border-top:none;}
.irb-link__item:hover{background:var(--surface-hover,#f5f5f5);}
.irb-link__item:focus-visible{outline:2px solid var(--focus-ring-color,var(--accent));outline-offset:-2px;}
.irb-link__ic{flex:none;color:var(--text-subtle);}
.irb-link__brief{flex:1;min-width:0;font-size:var(--text-sm);line-height:1.35;overflow-wrap:break-word;}
.irb-link__go{flex:none;color:var(--text-subtle);}
.irb-link__more{font-size:var(--text-xs);color:var(--text-subtle);padding:9px 4px 0;}

.irb-ft__access{display:inline-flex;align-items:center;gap:6px;font-size:var(--text-xs);font-weight:600;
  padding:3px 10px;border-radius:999px;}
.irb-ft__access--deny{background:var(--danger-50,#FBE9E7);color:var(--danger-500,#C0392B);}
.irb-ft__access--view{background:var(--status-issued-bg,#FBEFD8);color:var(--status-issued,#B0791C);}
.irb-ft__access--download{background:var(--status-available-bg,#E3F0E4);color:var(--status-available,#3C7D3F);}
.irb-ft__quota{font-size:var(--text-xs);color:var(--text-subtle);margin-left:8px;}
.irb-ft__art{display:flex;align-items:center;gap:11px;padding:11px 4px;border-top:1px solid var(--border-subtle);}
.irb-ft__art:first-of-type{border-top:none;}
.irb-ft__art-ic{flex:none;color:var(--text-subtle);}
.irb-ft__art-main{flex:1;min-width:0;}
.irb-ft__art-name{font-size:var(--text-sm);font-weight:600;color:var(--text-strong);overflow-wrap:break-word;}
.irb-ft__art-meta{font-size:var(--text-xs);color:var(--text-subtle);margin-top:2px;}
.irb-ft__art-rights{font-size:var(--text-2xs,11px);color:var(--text-subtle);margin-top:3px;font-style:italic;}
.irb-ft__btn{flex:none;display:inline-flex;align-items:center;gap:6px;font:inherit;font-size:var(--text-sm);
  border-radius:8px;padding:7px 13px;cursor:pointer;border:1px solid var(--border-strong,#cdd3da);
  background:var(--surface-card,#fff);color:var(--text-body);}
.irb-ft__btn:hover{background:var(--surface-hover,#f5f5f5);}
.irb-ft__btn--primary{background:var(--accent,#2F5D62);color:#fff;border-color:var(--accent,#2F5D62);}
.irb-ft__btn--primary:hover{filter:brightness(1.06);background:var(--accent,#2F5D62);}
.irb-ft__btn:disabled{cursor:not-allowed;opacity:.5;}
.irb-ft__deny{flex:none;font-size:var(--text-xs);color:var(--text-subtle);max-width:170px;text-align:right;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-link-css")) {
  const s = document.createElement("style"); s.id = "irb-link-css"; s.textContent = CSS; document.head.appendChild(s);
}

// Загрузка связанных записей по направлению kind. Возвращает null, пока грузим;
// [] — если 404/501/пусто (блок скрывается); массив — есть данные.
function useLinked(db: string, mfn: number, kind: LinkedKind): { items: LinkedItem[] | null; total: number } {
  const [state, setState] = React.useState<{ items: LinkedItem[] | null; total: number }>({ items: null, total: 0 });
  React.useEffect(() => {
    let alive = true; setState({ items: null, total: 0 });
    (async () => {
      const r = await api.linked(db, mfn, kind);
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.items)) {
        setState({ items: r.json.data.items, total: r.json.data.total ?? r.json.data.items.length });
      } else {
        setState({ items: [], total: 0 }); // 404/501/пусто → блок скрыт
      }
    })();
    return () => { alive = false; };
  }, [db, mfn, kind]);
  return state;
}

const MAX_ROWS = 30; // защита от гигантских журналов: показываем первые N

function LinkedList({ title, icon, items, total, onOpen }: {
  title: string; icon: "list-tree" | "book-open"; items: LinkedItem[]; total: number;
  onOpen: (mfn: number) => void;
}) {
  const shown = items.slice(0, MAX_ROWS);
  return (
    <section className="irb-link" aria-label={title}>
      <div className="irb-link__head">
        <h3 className="irb-link__title"><Icon name={icon} size={16} /> {title}</h3>
        {total > 0 && <span className="irb-link__count">{total}</span>}
      </div>
      <div className="irb-link__list" role="list">
        {shown.map((it) => (
          <button key={it.mfn} type="button" role="listitem" className="irb-link__item"
            onClick={() => onOpen(it.mfn)} aria-label={"Открыть: " + (it.brief || "запись " + it.mfn)}>
            <Icon name="file-text" size={15} className="irb-link__ic" />
            <span className="irb-link__brief">{it.brief || "Запись № " + it.mfn}</span>
            <Icon name="chevron-right" size={15} className="irb-link__go" />
          </button>
        ))}
      </div>
      {total > shown.length && (
        <div className="irb-link__more">Показаны первые {shown.length} из {total}.</div>
      )}
    </section>
  );
}

// «В этом издании» — что входит В издание (статьи/номера/тома). kind=children.
export function InThisEdition({ db, mfn, onOpen }: { db: string; mfn: number; onOpen: (db: string, mfn: number) => void }) {
  const { items, total } = useLinked(db, mfn, "children");
  if (!items || !items.length) return null; // 404/501/пусто → скрыт
  return <LinkedList title="В этом издании" icon="list-tree" items={items} total={total} onOpen={(m) => onOpen(db, m)} />;
}

// «Источник» — издание-хозяин аналитической росписи. kind=host.
export function RecordHost({ db, mfn, onOpen }: { db: string; mfn: number; onOpen: (db: string, mfn: number) => void }) {
  const { items, total } = useLinked(db, mfn, "host");
  if (!items || !items.length) return null; // 404/501/пусто → скрыт
  return <LinkedList title="Источник" icon="book-open" items={items} total={total} onOpen={(m) => onOpen(db, m)} />;
}

// Бейдж уровня доступа к полному тексту.
const ACCESS_META: Record<FulltextLevel, { label: string; cls: string }> = {
  deny: { label: "Нет доступа", cls: "irb-ft__access--deny" },
  view: { label: "Только просмотр", cls: "irb-ft__access--view" },
  download: { label: "Просмотр и скачивание", cls: "irb-ft__access--download" },
};

function looksLikeImage(url?: string): boolean {
  return !!url && /\.(png|jpe?g|gif|webp|bmp|tiff?|svg)(\?|#|$)/i.test(url);
}

// «Полный текст» — артефакты + бейдж доступа + остаток квоты страниц.
// При уровне view/download кнопка просмотра активна (открывает просмотрщик
// для page-ресурсов либо ссылку); при deny — кнопка неактивна и подпись
// «недоступно для вашей категории».
export function FulltextBlock({ db, mfn, onViewDoc }: {
  db: string; mfn: number;
  onViewDoc: (pages: DocPage[], idx: number, title?: string) => void;
}) {
  const [state, setState] = React.useState<{
    artifacts: FulltextArtifact[]; level: FulltextLevel; pageLimit?: number; downloadBudget?: number;
  } | null | "empty">(null);
  React.useEffect(() => {
    let alive = true; setState(null);
    (async () => {
      const r = await api.fulltext(db, mfn);
      if (!alive) return;
      if (r.json?.ok && r.json.data && Array.isArray(r.json.data.artifacts) && r.json.data.artifacts.length) {
        const d = r.json.data;
        setState({
          artifacts: d.artifacts, level: d.access?.level ?? "deny",
          pageLimit: d.access?.pageLimit, downloadBudget: d.access?.downloadBudget,
        });
      } else {
        setState("empty"); // 404/501/нет артефактов → блок скрыт
      }
    })();
    return () => { alive = false; };
  }, [db, mfn]);

  if (state === null || state === "empty") return null;
  const { artifacts, level, pageLimit, downloadBudget } = state;
  const acc = ACCESS_META[level];
  const canView = level === "view" || level === "download";

  // Открыть артефакт в просмотрщике: page-ресурсы рисуем как страницы, прочее —
  // как файл (откроется в новой вкладке кнопкой просмотрщика).
  const open = (a: FulltextArtifact) => {
    const page: DocPage = { name: a.ref, url: a.ref, kind: looksLikeImage(a.ref) ? "image" : "file" };
    onViewDoc([page], 0, a.kind ? a.kind.toUpperCase() : "Полный текст");
  };

  return (
    <section className="irb-link" aria-label="Полный текст">
      <div className="irb-link__head">
        <h3 className="irb-link__title"><Icon name="file-text" size={16} /> Полный текст</h3>
        <span className={"irb-ft__access " + acc.cls}>
          <Icon name={level === "deny" ? "eye-off" : level === "download" ? "download" : "eye"} size={12} /> {acc.label}
        </span>
        {canView && typeof pageLimit === "number" && pageLimit >= 0 && (
          <span className="irb-ft__quota">остаток страниц: {pageLimit}</span>
        )}
        {level === "download" && typeof downloadBudget === "number" && downloadBudget >= 0 && (
          <span className="irb-ft__quota">квота скачиваний: {downloadBudget}</span>
        )}
      </div>
      <div role="list">
        {artifacts.map((a, i) => (
          <div className="irb-ft__art" role="listitem" key={i}>
            <Icon name="file-text" size={18} className="irb-ft__art-ic" />
            <div className="irb-ft__art-main">
              <div className="irb-ft__art-name">{(a.kind ? a.kind.toUpperCase() : "Файл") + (a.ref && !looksLikeImage(a.ref) ? " · " + a.ref.split("/").pop() : "")}</div>
              {typeof a.pages === "number" && a.pages > 0 && <div className="irb-ft__art-meta">{a.pages} стр.</div>}
              {a.rightsTemplate && <div className="irb-ft__art-rights">{a.rightsTemplate}</div>}
            </div>
            {canView ? (
              <button type="button" className="irb-ft__btn irb-ft__btn--primary" onClick={() => open(a)}>
                <Icon name="eye" size={14} /> Просмотр
              </button>
            ) : (
              <span className="irb-ft__deny">недоступно для вашей категории</span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
