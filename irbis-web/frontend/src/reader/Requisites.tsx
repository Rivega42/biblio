// Страница «Реквизиты» (#335) — модал с юридическими данными и контактами
// учреждения: полное наименование, ИНН/ОГРН/КПП, юр. и почтовый адрес, телефон,
// e-mail, сайт, часы работы. Данные — из публичной конфигурации библиотеки
// (GET /api/library-config), которая правится в админке (заменяет захардкоженный
// tenantContent). Пустые поля не показываются. Самодостаточный компонент.
import React from "react";
import { api } from "../api";
import type { LibraryConfig } from "../api";
import { Icon } from "../../components/icon/Icon.jsx";

const CSS = `
.irb-req{position:fixed;inset:0;z-index:85;background:rgba(15,12,10,.55);display:flex;align-items:flex-start;
  justify-content:center;padding:40px 16px;overflow-y:auto;}
.irb-req__box{width:100%;max-width:620px;background:var(--surface-card,#fff);border-radius:var(--radius-xl,16px);
  box-shadow:var(--shadow-lg);border:1px solid var(--border-subtle);overflow:hidden;}
.irb-req__bar{display:flex;align-items:center;gap:10px;padding:15px 20px;border-bottom:1px solid var(--border-subtle);}
.irb-req__ttl{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-bold,700);font-size:var(--text-lg,1.1rem);
  color:var(--text-strong);margin:0;flex:1;min-width:0;}
.irb-req__x{border:none;background:none;cursor:pointer;color:var(--text-muted);padding:4px;border-radius:var(--radius-md,8px);}
.irb-req__x:hover{background:var(--surface-sunken);}
.irb-req__body{padding:18px 20px;display:flex;flex-direction:column;gap:16px;}
.irb-req__name{font-family:var(--font-display,var(--font-serif));font-weight:var(--weight-semibold,600);font-size:var(--text-base,1rem);
  color:var(--text-strong);line-height:1.35;}
.irb-req__grp-h{font-size:var(--text-2xs,11px);font-weight:var(--weight-bold,700);letter-spacing:.06em;text-transform:uppercase;
  color:var(--text-subtle);margin:0 0 7px;}
.irb-req__tbl{width:100%;font-size:var(--text-sm,.92rem);border-collapse:collapse;}
.irb-req__tbl td{padding:5px 0;vertical-align:top;line-height:1.4;}
.irb-req__tbl td:first-child{color:var(--text-subtle);width:42%;padding-right:12px;}
.irb-req__tbl td:last-child{color:var(--text-body);}
.irb-req__tbl a{color:var(--accent);text-decoration:none;}
.irb-req__tbl a:hover{text-decoration:underline;}
.irb-req__empty{font-size:var(--text-sm);color:var(--text-subtle);}
`;

if (typeof document !== "undefined" && !document.getElementById("irb-req-css")) {
  const s = document.createElement("style"); s.id = "irb-req-css"; s.textContent = CSS; document.head.appendChild(s);
}

function Row({ label, value, href }: { label: string; value?: string; href?: string }) {
  if (!value) return null;
  return (
    <tr>
      <td>{label}</td>
      <td>{href ? <a href={href}>{value}</a> : value}</td>
    </tr>
  );
}

export function Requisites({ onClose }: { onClose: () => void }) {
  const [cfg, setCfg] = React.useState<LibraryConfig | null>(null);
  const [loaded, setLoaded] = React.useState(false);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      const r = await api.libraryConfig();
      if (!alive) return;
      if (r.json?.ok && r.json.data?.config) setCfg(r.json.data.config);
      setLoaded(true);
    })();
    return () => { alive = false; };
  }, []);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const rq = cfg?.requisites;
  const hasLegal = rq && (rq.inn || rq.ogrn || rq.kpp || rq.legal_address);
  const hasContacts = rq && (rq.address || rq.phone || rq.email || rq.site);
  const empty = loaded && !cfg?.full_name && !cfg?.name && !hasLegal && !hasContacts && !cfg?.hours;

  return (
    <div className="irb-req" role="dialog" aria-modal="true" aria-label="Реквизиты учреждения"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="irb-req__box">
        <div className="irb-req__bar">
          <h2 className="irb-req__ttl">Реквизиты</h2>
          <button type="button" className="irb-req__x" onClick={onClose} aria-label="Закрыть (Esc)" title="Закрыть">
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="irb-req__body">
          {!loaded
            ? <p className="irb-req__empty">Загрузка…</p>
            : empty
              ? <p className="irb-req__empty">Реквизиты учреждения ещё не заполнены администратором.</p>
              : (
                <>
                  {(cfg?.full_name || cfg?.name) && (
                    <div className="irb-req__name">{cfg?.full_name || cfg?.name}</div>
                  )}
                  {hasLegal && (
                    <div>
                      <p className="irb-req__grp-h">Юридические данные</p>
                      <table className="irb-req__tbl"><tbody>
                        <Row label="ИНН" value={rq?.inn} />
                        <Row label="ОГРН" value={rq?.ogrn} />
                        <Row label="КПП" value={rq?.kpp} />
                        <Row label="Юридический адрес" value={rq?.legal_address} />
                      </tbody></table>
                    </div>
                  )}
                  {(hasContacts || cfg?.hours) && (
                    <div>
                      <p className="irb-req__grp-h">Контакты</p>
                      <table className="irb-req__tbl"><tbody>
                        <Row label="Адрес" value={rq?.address} />
                        <Row label="Телефон" value={rq?.phone} href={rq?.phone ? "tel:" + rq.phone.replace(/[^+\d]/g, "") : undefined} />
                        <Row label="E-mail" value={rq?.email} href={rq?.email ? "mailto:" + rq.email : undefined} />
                        <Row label="Сайт" value={rq?.site} href={rq?.site ? (/^https?:/.test(rq.site) ? rq.site : "https://" + rq.site) : undefined} />
                        <Row label="Часы работы" value={cfg?.hours} />
                      </tbody></table>
                    </div>
                  )}
                </>
              )}
        </div>
      </div>
    </div>
  );
}
