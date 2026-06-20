import React from "react";
import { Icon } from "../icon/Icon.jsx";

const CSS = `
.irb-subject{
  display:inline-flex;align-items:center;gap:6px;
  font-family:var(--font-ui);font-size:var(--text-sm);
  height:28px;padding:0 var(--space-3);
  border-radius:var(--radius-sm);border:var(--border-width) solid var(--border-default);
  background:var(--surface-card);color:var(--text-body);
  cursor:pointer;text-decoration:none;white-space:nowrap;
  transition:border-color var(--dur) var(--ease-standard),
    background var(--dur) var(--ease-standard), color var(--dur) var(--ease-standard);
}
.irb-subject:hover{border-color:var(--accent);color:var(--accent-hover);background:var(--accent-weak);text-decoration:none;}
.irb-subject:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);outline-offset:1px;}
.irb-subject__icon{color:var(--text-subtle);}
.irb-subject:hover .irb-subject__icon{color:var(--accent);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-subject-css")) {
  const s = document.createElement("style");
  s.id = "irb-subject-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function SubjectTag({ children, as = "button", className = "", ...rest }) {
  const Comp = as;
  const extra = as === "button" ? { type: "button" } : {};
  return (
    <Comp className={`irb-subject ${className}`} {...extra} {...rest}>
      <Icon name="tag" size={13} className="irb-subject__icon" />
      {children}
    </Comp>
  );
}
