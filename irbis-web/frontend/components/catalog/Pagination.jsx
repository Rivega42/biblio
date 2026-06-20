import React from "react";
import { Icon } from "../icon/Icon.jsx";
import { Select } from "../forms/Select.jsx";

const CSS = `
.irb-pg{display:flex;align-items:center;gap:var(--space-4);flex-wrap:wrap;font-family:var(--font-ui);}
.irb-pg__nums{display:flex;align-items:center;gap:4px;}
.irb-pg__b{
  min-width:var(--control-h-sm);height:var(--control-h-sm);padding:0 var(--space-2);
  display:inline-flex;align-items:center;justify-content:center;
  border:var(--border-width) solid transparent;border-radius:var(--radius-sm);
  background:transparent;color:var(--text-body);cursor:pointer;font-size:var(--text-sm);
  font-variant-numeric:tabular-nums;font-weight:var(--weight-medium);
  transition:background-color var(--dur) var(--ease-standard);
}
.irb-pg__b:hover:not(:disabled){background:var(--surface-hover);}
.irb-pg__b:disabled{opacity:.4;cursor:not-allowed;}
.irb-pg__b--cur{background:var(--accent);color:var(--accent-fg);}
.irb-pg__b--cur:hover{background:var(--accent);}
.irb-pg__b:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);}
.irb-pg__ell{padding:0 4px;color:var(--text-subtle);}
.irb-pg__stat{font-size:var(--text-sm);color:var(--text-muted);font-variant-numeric:tabular-nums;}
.irb-pg__stat b{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-pg__size{display:flex;align-items:center;gap:var(--space-2);margin-left:auto;font-size:var(--text-sm);color:var(--text-muted);}
.irb-pg__size .irb-select{min-width:84px;}
.irb-pg--compact{justify-content:flex-end;}
.irb-pg--compact .irb-pg__stat{margin-right:auto;}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-pg-css")) {
  const s = document.createElement("style");
  s.id = "irb-pg-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

function pageList(cur, count) {
  if (count <= 7) return Array.from({ length: count }, (_, i) => i + 1);
  const set = new Set([1, count, cur, cur - 1, cur + 1]);
  if (cur <= 3) [2, 3, 4].forEach((n) => set.add(n));
  if (cur >= count - 2) [count - 1, count - 2, count - 3].forEach((n) => set.add(n));
  const nums = [...set].filter((n) => n >= 1 && n <= count).sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < nums.length; i++) {
    out.push(nums[i]);
    if (i < nums.length - 1 && nums[i + 1] - nums[i] > 1) out.push("…");
  }
  return out;
}

export function Pagination({
  page = 1,
  pageCount = 1,
  onPage,
  pageSize,
  onPageSize,
  pageSizeOptions = [10, 20, 50],
  total,
  compact = false,
  className = "",
}) {
  const go = (p) => p >= 1 && p <= pageCount && p !== page && onPage && onPage(p);
  return (
    <nav className={`irb-pg${compact ? " irb-pg--compact" : ""} ${className}`} aria-label="Постраничная навигация">
      <span className="irb-pg__stat">
        Страница <b>{page}</b> из <b>{pageCount}</b>
        {total != null && <> · найдено <b>{total.toLocaleString("ru-RU")}</b></>}
      </span>
      <div className="irb-pg__nums">
        <button type="button" className="irb-pg__b" onClick={() => go(1)} disabled={page <= 1} aria-label="Первая страница">
          <Icon name="chevrons-left" size={18} />
        </button>
        <button type="button" className="irb-pg__b" onClick={() => go(page - 1)} disabled={page <= 1} aria-label="Предыдущая страница">
          <Icon name="chevron-left" size={18} />
        </button>
        {pageList(page, pageCount).map((p, i) =>
          p === "…" ? (
            <span key={`e${i}`} className="irb-pg__ell" aria-hidden="true">…</span>
          ) : (
            <button
              key={p}
              type="button"
              className={`irb-pg__b${p === page ? " irb-pg__b--cur" : ""}`}
              aria-current={p === page ? "page" : undefined}
              onClick={() => go(p)}
            >
              {p}
            </button>
          )
        )}
        <button type="button" className="irb-pg__b" onClick={() => go(page + 1)} disabled={page >= pageCount} aria-label="Следующая страница">
          <Icon name="chevron-right" size={18} />
        </button>
        <button type="button" className="irb-pg__b" onClick={() => go(pageCount)} disabled={page >= pageCount} aria-label="Последняя страница">
          <Icon name="chevrons-right" size={18} />
        </button>
      </div>
      {pageSize != null && onPageSize && (
        <div className="irb-pg__size">
          <span>Показывать по</span>
          <Select
            size="sm"
            value={String(pageSize)}
            onChange={(e) => onPageSize(Number(e.target.value))}
            options={pageSizeOptions.map((n) => String(n))}
            aria-label="Размер страницы"
          />
        </div>
      )}
    </nav>
  );
}
