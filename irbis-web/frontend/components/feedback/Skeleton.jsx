import React from "react";

const CSS = `
.irb-skel{
  display:block;background:linear-gradient(90deg,
    var(--surface-sunken) 25%, var(--surface-hover) 37%, var(--surface-sunken) 63%);
  background-size:400% 100%;border-radius:var(--radius-sm);
  animation:irb-shimmer 1.4s ease infinite;
}
@keyframes irb-shimmer{from{background-position:100% 0;}to{background-position:0 0;}}
@media (prefers-reduced-motion:reduce){.irb-skel{animation:none;background:var(--surface-sunken);}}
.irb-skel--text{height:.72em;margin:.18em 0;border-radius:var(--radius-xs);}
.irb-skel--circle{border-radius:var(--radius-round);}

.irb-skelcard{display:flex;gap:var(--space-3);background:var(--surface-card);
  border:var(--border-width) solid var(--border-subtle);border-radius:var(--radius-lg);padding:var(--space-4);}
.irb-skelcard__b{flex:1;display:flex;flex-direction:column;gap:var(--space-2);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-skel-css")) {
  const s = document.createElement("style");
  s.id = "irb-skel-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function Skeleton({ width = "100%", height = "1em", variant = "text", radius, className = "", style }) {
  return (
    <span
      className={`irb-skel irb-skel--${variant} ${className}`}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}

/** Скелетон карточки результата — для состояния загрузки списка. */
export function SkeletonResult({ showThumb = false }) {
  return (
    <div className="irb-skelcard" aria-hidden="true">
      <Skeleton variant="circle" width={18} height={18} />
      {showThumb && <Skeleton width={56} height={74} radius="var(--radius-sm)" />}
      <div className="irb-skelcard__b">
        <Skeleton width="38%" height={10} />
        <Skeleton width="72%" height={18} />
        <Skeleton width="46%" height={12} />
      </div>
      <Skeleton width={84} height={22} radius="var(--radius-pill)" />
    </div>
  );
}
