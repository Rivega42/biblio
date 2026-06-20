import React from "react";

const CSS = `
.irb-pft{
  font-family:var(--font-body);font-size:var(--text-base);line-height:var(--leading-relaxed);
  color:var(--text-body);max-width:var(--content-max);
}
.irb-pft p{margin:0 0 var(--space-3);}
.irb-pft p:last-child{margin-bottom:0;}
.irb-pft b,.irb-pft strong{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-pft a{color:var(--text-link);text-decoration:underline;text-underline-offset:2px;}
.irb-pft h1,.irb-pft h2,.irb-pft h3,.irb-pft h4{font-family:var(--font-record-title);margin:var(--space-4) 0 var(--space-2);line-height:var(--leading-snug);}
.irb-pft h3{font-size:var(--text-lg);}
.irb-pft h4{font-size:var(--text-md);}
.irb-pft ul,.irb-pft ol{margin:0 0 var(--space-3);padding-inline-start:var(--space-5);}
.irb-pft li{margin-bottom:4px;}
.irb-pft dl{display:grid;grid-template-columns:max-content 1fr;gap:var(--space-2) var(--space-4);margin:0;}
.irb-pft dt{color:var(--text-muted);font-size:var(--text-sm);font-weight:var(--weight-semibold);}
.irb-pft dd{margin:0;color:var(--text-body);}
.irb-pft table{border-collapse:collapse;width:100%;margin:0 0 var(--space-3);font-size:var(--text-sm);}
.irb-pft td,.irb-pft th{border:var(--border-width) solid var(--border-subtle);padding:var(--space-2) var(--space-3);text-align:left;}
.irb-pft__label{display:flex;align-items:center;gap:var(--space-2);font-size:var(--text-2xs);
  text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);
  font-weight:var(--weight-semibold);font-family:var(--font-ui);margin-bottom:var(--space-3);}
.irb-pft__label::after{content:"";flex:1;height:1px;background:var(--border-subtle);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-pft-css")) {
  const s = document.createElement("style");
  s.id = "irb-pft-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function PftBlock({ html = "", sanitize, showLabel = true, label = "Библиографическое описание", className = "", children }) {
  // Безопасный рендер: серверный HTML должен быть очищен ДО вставки.
  // Если передан sanitize() — применяем его; иначе доверяем уже очищенному входу.
  const safe = typeof sanitize === "function" ? sanitize(html) : html;
  return (
    <div className={`irb-pft ${className}`}>
      {showLabel && <div className="irb-pft__label">{label}</div>}
      {children != null ? children : <div dangerouslySetInnerHTML={{ __html: safe }} />}
    </div>
  );
}
