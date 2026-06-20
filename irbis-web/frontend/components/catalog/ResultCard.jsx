import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { Checkbox } from "../forms/Checkbox.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

const CSS = `
.irb-result{
  display:flex;gap:var(--space-3);align-items:flex-start;
  background:var(--surface-card);border:var(--border-width) solid var(--border-subtle);
  border-radius:var(--radius-lg);padding:var(--space-4);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-result:hover{border-color:var(--border-strong);box-shadow:var(--shadow-sm);}
.irb-result--marked{border-color:var(--accent-weak-border);background:var(--accent-weak);}
.irb-result__check{padding-top:2px;}
.irb-result__thumb{
  flex:none;width:56px;height:74px;border-radius:var(--radius-sm);overflow:hidden;
  background:var(--surface-sunken);border:var(--border-width) solid var(--border-subtle);
  display:flex;align-items:center;justify-content:center;color:var(--text-subtle);
}
.irb-result__thumb img{width:100%;height:100%;object-fit:cover;display:block;}
.irb-result__body{flex:1;min-width:0;}
.irb-result__type{display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs);
  text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);font-weight:var(--weight-semibold);}
.irb-result__dbtag{display:inline-flex;align-items:center;gap:4px;font-size:var(--text-2xs);font-weight:var(--weight-semibold);
  color:var(--accent);background:var(--accent-weak);border:1px solid var(--accent-weak-border);
  border-radius:var(--radius-pill);padding:1px 8px;text-transform:none;letter-spacing:0;}
.irb-result__toprow{display:flex;align-items:center;gap:var(--space-2);flex-wrap:wrap;}
.irb-result__title{
  font-family:var(--font-record-title);font-size:var(--text-lg);font-weight:var(--weight-semibold);
  color:var(--text-strong);line-height:var(--leading-snug);margin:3px 0;cursor:pointer;
  background:none;border:none;padding:0;text-align:left;display:block;
}
.irb-result__title:hover{color:var(--accent-hover);text-decoration:underline;text-underline-offset:3px;}
.irb-result__meta{display:flex;flex-wrap:wrap;gap:var(--space-1) var(--space-3);
  font-size:var(--text-sm);color:var(--text-muted);align-items:center;}
.irb-result__author{color:var(--text-body);font-weight:var(--weight-medium);}
.irb-result__sep{color:var(--border-strong);}
.irb-result__extra{margin-top:var(--space-2);display:flex;flex-wrap:wrap;gap:var(--space-1) var(--space-4);
  font-size:var(--text-sm);color:var(--text-muted);}
.irb-result__extra b{color:var(--text-body);font-weight:var(--weight-medium);}
.irb-result__aside{display:flex;flex-direction:column;align-items:flex-end;gap:var(--space-2);flex:none;}
@media (max-width:560px){
  .irb-result__aside{align-items:flex-start;}
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-result-css")) {
  const s = document.createElement("style");
  s.id = "irb-result-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function ResultCard({
  item = {},
  checked = false,
  onToggleCheck,
  onOpen,
  showCheck = true,
  showThumb = false,
  typeIcon = "book",
  dbTag,
  className = "",
}) {
  const { title, author, year, docType, availability = "unknown", fields = [], thumb } = item;
  return (
    <article className={`irb-result${checked ? " irb-result--marked" : ""} ${className}`}>
      {showCheck && (
        <span className="irb-result__check">
          <Checkbox checked={checked} onChange={onToggleCheck} aria-label={`Отметить: ${title}`} />
        </span>
      )}
      {showThumb && (
        <span className="irb-result__thumb">
          {thumb ? <img src={thumb} alt="" /> : <Icon name="image" size={22} />}
        </span>
      )}
      <div className="irb-result__body">
        {(docType || dbTag) && (
          <div className="irb-result__toprow">
            {docType && <span className="irb-result__type"><Icon name={typeIcon} size={12} /> {docType}</span>}
            {dbTag && <span className="irb-result__dbtag" title={"Из базы: " + dbTag}><Icon name="layers" size={11} /> {dbTag}</span>}
          </div>
        )}
        <button type="button" className="irb-result__title" onClick={onOpen}>{title}</button>
        <div className="irb-result__meta">
          {author && <span className="irb-result__author">{author}</span>}
          {author && year && <span className="irb-result__sep" aria-hidden="true">·</span>}
          {year && <span>{year}</span>}
        </div>
        {fields.length > 0 && (
          <div className="irb-result__extra">
            {fields.map((f, i) => (
              <span key={i}>{f.label}: <b>{f.value}</b></span>
            ))}
          </div>
        )}
      </div>
      <div className="irb-result__aside">
        <StatusBadge status={availability} size="sm" />
        <Icon name="chevron-right" size={18} style={{ color: "var(--text-subtle)" }} />
      </div>
    </article>
  );
}
