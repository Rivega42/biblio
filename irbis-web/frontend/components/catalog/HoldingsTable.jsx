import React from "react";
import { StatusBadge } from "./StatusBadge.jsx";
import { Button } from "../forms/Button.jsx";

const CSS = `
.irb-holdings{font-family:var(--font-ui);}
.irb-holdings__tbl{width:100%;border-collapse:collapse;font-size:var(--text-sm);}
.irb-holdings__tbl th{
  text-align:left;font-weight:var(--weight-semibold);color:var(--text-muted);
  font-size:var(--text-xs);text-transform:uppercase;letter-spacing:var(--tracking-wide);
  padding:0 var(--space-3) var(--space-2);border-bottom:var(--border-width) solid var(--border-default);
}
.irb-holdings__tbl td{padding:var(--space-3);border-bottom:var(--border-width) solid var(--border-subtle);color:var(--text-body);vertical-align:middle;}
.irb-holdings__tbl tr:last-child td{border-bottom:none;}
.irb-holdings__loc{font-weight:var(--weight-medium);color:var(--text-strong);}
.irb-holdings__inv{font-family:var(--font-mono);font-size:var(--text-xs);color:var(--text-muted);}
.irb-holdings__act{text-align:right;}

/* Карточки на узких экранах */
.irb-holdings__cards{display:none;flex-direction:column;gap:var(--space-2);}
.irb-holdings__card{border:var(--border-width) solid var(--border-subtle);border-radius:var(--radius-md);
  padding:var(--space-3);display:flex;flex-direction:column;gap:var(--space-2);background:var(--surface-card);}
.irb-holdings__crow{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);}
.irb-holdings__clbl{font-size:var(--text-xs);color:var(--text-subtle);}

@media (max-width:560px){
  .irb-holdings__tbl{display:none;}
  .irb-holdings__cards{display:flex;}
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-holdings-css")) {
  const s = document.createElement("style");
  s.id = "irb-holdings-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function HoldingsTable({ holdings = [], onOrder, className = "" }) {
  return (
    <div className={`irb-holdings ${className}`}>
      <table className="irb-holdings__tbl">
        <thead>
          <tr>
            <th>Место хранения</th>
            <th>Инвентарный №</th>
            <th>Статус</th>
            {onOrder && <th className="irb-holdings__act"></th>}
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => (
            <tr key={i}>
              <td className="irb-holdings__loc">{h.location}</td>
              <td><span className="irb-holdings__inv">{h.inventory}</span></td>
              <td><StatusBadge status={h.status} size="sm" /></td>
              {onOrder && (
                <td className="irb-holdings__act">
                  <Button
                    size="sm"
                    variant={h.status === "available" ? "secondary" : "ghost"}
                    disabled={h.status !== "available"}
                    onClick={() => onOrder(h, i)}
                  >
                    {h.status === "available" ? "Заказать" : "Недоступен"}
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="irb-holdings__cards">
        {holdings.map((h, i) => (
          <div className="irb-holdings__card" key={i}>
            <div className="irb-holdings__crow">
              <span className="irb-holdings__loc">{h.location}</span>
              <StatusBadge status={h.status} size="sm" />
            </div>
            <div className="irb-holdings__crow">
              <span className="irb-holdings__clbl">Инв. №</span>
              <span className="irb-holdings__inv">{h.inventory}</span>
            </div>
            {onOrder && (
              <Button
                size="sm" block
                variant={h.status === "available" ? "secondary" : "ghost"}
                disabled={h.status !== "available"}
                onClick={() => onOrder(h, i)}
              >
                {h.status === "available" ? "Заказать" : "Недоступен"}
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
