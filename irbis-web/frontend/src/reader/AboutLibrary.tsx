// «О библиотеке» (G1+) — компактный блок-подвал главной: краткое «о фонде», часы
// работы и контакты (адрес/телефон/почта/сайт). Реквизиты конфигурируются
// per-tenant (tenantContent); для пилота — фактические данные СПб ГТБ. Сетевых
// вызовов нет → блок устойчив; при отсутствии about-данных не рендерится.
import React from "react";
import { Icon } from "../../components/icon/Icon.jsx";
import { getTenantContent } from "./tenantContent";

const CSS = `
.irb-about{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:0;overflow:hidden;
  background:var(--surface-card,#fff);border:1px solid var(--border-subtle);border-radius:var(--radius-2xl,20px);box-shadow:var(--shadow-sm);}
.irb-about__col{padding:18px 20px;}
.irb-about__col + .irb-about__col{border-left:1px solid var(--border-subtle);}
.irb-about__title{display:flex;align-items:center;gap:8px;font-family:var(--font-display,var(--font-serif));
  font-weight:var(--weight-semibold,600);font-size:var(--text-base,1rem);color:var(--text-strong);margin:0 0 8px;}
.irb-about__name{font-size:var(--text-sm);font-weight:600;color:var(--text-strong);margin:0 0 6px;line-height:1.3;}
.irb-about__blurb{font-size:var(--text-sm);color:var(--text-muted,var(--text-secondary));line-height:1.5;margin:0;}
.irb-about__rows{display:flex;flex-direction:column;gap:6px;margin:0;}
.irb-about__row{display:flex;justify-content:space-between;gap:10px;font-size:var(--text-sm);}
.irb-about__row dt{color:var(--text-subtle);margin:0;}
.irb-about__row dd{margin:0;color:var(--text-body);font-weight:500;text-align:right;}
.irb-about__contacts{display:flex;flex-direction:column;gap:9px;}
.irb-about__c{display:flex;align-items:flex-start;gap:9px;font-size:var(--text-sm);color:var(--text-body);}
.irb-about__c .irb-about__ic{color:var(--accent);flex:none;margin-top:1px;}
.irb-about__c a{color:var(--accent);text-decoration:none;overflow-wrap:break-word;word-break:break-word;}
.irb-about__c a:hover{text-decoration:underline;}
@media (max-width:760px){
  .irb-about{grid-template-columns:1fr;}
  .irb-about__col + .irb-about__col{border-left:none;border-top:1px solid var(--border-subtle);}
}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-about-css")) {
  const s = document.createElement("style"); s.id = "irb-about-css"; s.textContent = CSS; document.head.appendChild(s);
}

export function AboutLibrary() {
  const { about } = getTenantContent();
  if (!about) return null;
  const telHref = "tel:" + about.phone.replace(/[^\d+]/g, "");

  return (
    <section className="irb-about" aria-label="О библиотеке">
      {/* О фонде */}
      <div className="irb-about__col">
        <h2 className="irb-about__title"><Icon name="info" size={16} /> О библиотеке</h2>
        <p className="irb-about__name">{about.name}</p>
        <p className="irb-about__blurb">{about.blurb}</p>
      </div>

      {/* Часы работы */}
      <div className="irb-about__col">
        <div className="irb-about__title"><Icon name="clock" size={16} /> Часы работы</div>
        <dl className="irb-about__rows">
          {about.hours.map((h, i) => (
            <div key={i} className="irb-about__row"><dt>{h.label}</dt><dd>{h.value}</dd></div>
          ))}
        </dl>
      </div>

      {/* Контакты */}
      <div className="irb-about__col">
        <div className="irb-about__title"><Icon name="map-pin" size={16} /> Контакты</div>
        <div className="irb-about__contacts">
          <div className="irb-about__c"><Icon name="map-pin" size={15} className="irb-about__ic" /><span>{about.address}</span></div>
          <div className="irb-about__c"><Icon name="bell" size={15} className="irb-about__ic" /><a href={telHref}>{about.phone}</a></div>
          <div className="irb-about__c"><Icon name="share" size={15} className="irb-about__ic" /><a href={"mailto:" + about.email}>{about.email}</a></div>
          {about.site && <div className="irb-about__c"><Icon name="globe" size={15} className="irb-about__ic" /><a href={"https://" + about.site} target="_blank" rel="noopener noreferrer">{about.site}</a></div>}
        </div>
      </div>
    </section>
  );
}
