import React from "react";
import {
  PRODUCT, FUNCTIONAL, TECH, GUIDE, INSTALL, INSTALL_STEPS, PROVISION_STEP,
  REQUIREMENTS, SECURITY, DOC_LINKS,
} from "./content";
import type { DocSection } from "./content";
import { DemoRequestForm } from "./DemoRequestForm";

// Публичная страница продукта Biblio (/product, issue #226). Без логина: описание
// продукта, функциональные характеристики, руководство, установка (выжимки из
// templates/04, 05, deploy/README + ссылки на полное) и форма-заявка на демодоступ
// (152-ФЗ). Biblio-токены, плоский Style A. Самодостаточна — не зависит от App.tsx.

const maxw = 1040;

const page: React.CSSProperties = {
  background: "var(--bg-page, #F3ECDD)",
  color: "var(--text-body, #36291F)",
  fontFamily: "var(--font-body, system-ui, sans-serif)",
  minHeight: "100vh",
};

const wrap: React.CSSProperties = {
  maxWidth: maxw, margin: "0 auto", padding: "0 var(--space-5, 20px)",
};

const card: React.CSSProperties = {
  background: "var(--surface-card, #FBF6EC)",
  border: "1px solid var(--border-default, #D6D1C4)",
  borderRadius: "var(--radius-lg, 10px)",
  padding: "var(--space-6, 24px)",
};

const h2: React.CSSProperties = {
  fontFamily: "var(--font-display, var(--font-serif, Georgia, serif))",
  fontSize: "var(--text-2xl, 26px)", fontWeight: 700,
  color: "var(--text-strong, #241C16)", margin: "0 0 var(--space-3, 12px)",
};

const h3: React.CSSProperties = {
  fontSize: "var(--text-md, 16px)", fontWeight: 700,
  color: "var(--text-strong, #241C16)", margin: "var(--space-4, 16px) 0 var(--space-2, 8px)",
};

const lead: React.CSSProperties = {
  fontSize: "var(--text-lg, 17px)", lineHeight: 1.6,
  color: "var(--text-body, #36291F)", margin: 0,
};

const pre: React.CSSProperties = {
  background: "var(--surface-sunken, #ECE0CB)",
  border: "1px solid var(--border-subtle, #E4E0D6)",
  borderRadius: "var(--radius-md, 8px)",
  padding: "var(--space-4, 16px)", overflowX: "auto",
  fontFamily: "var(--font-mono, ui-monospace, Menlo, Consolas, monospace)",
  fontSize: "var(--text-sm, 13px)", lineHeight: 1.6,
  color: "var(--text-strong, #241C16)", margin: 0, whiteSpace: "pre",
};

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} style={{ marginBottom: "var(--space-8, 32px)", scrollMarginTop: 80 }}>
      <h2 style={h2}>{title}</h2>
      {children}
    </section>
  );
}

function BulletDoc({ doc }: { doc: DocSection }) {
  return (
    <>
      {doc.intro && <p style={{ ...lead, fontSize: "var(--text-base, 15px)", marginBottom: "var(--space-4, 16px)" }}>{doc.intro}</p>}
      {doc.bullets?.map((grp, i) => (
        <div key={i}>
          {grp.heading && <h3 style={h3}>{grp.heading}</h3>}
          <ul style={{ margin: "0 0 var(--space-3, 12px)", paddingLeft: "var(--space-5, 20px)", lineHeight: 1.6 }}>
            {grp.items.map((it, j) => <li key={j} style={{ marginBottom: 4 }}>{it}</li>)}
          </ul>
        </div>
      ))}
    </>
  );
}

const NAV = [
  { id: "functional", label: "Функции" },
  { id: "guide", label: "Руководство" },
  { id: "install", label: "Установка" },
  { id: "security", label: "Безопасность" },
  { id: "demo", label: "Демодоступ" },
];

export function Landing() {
  return (
    <div style={page}>
      {/* Шапка с навигацией */}
      <header style={{
        position: "sticky", top: 0, zIndex: 10,
        background: "var(--surface-card, #FBF6EC)",
        borderBottom: "1px solid var(--border-default, #D6D1C4)",
      }}>
        <div style={{ ...wrap, display: "flex", alignItems: "center", gap: "var(--space-4, 16px)", height: 60 }}>
          <a href="/" style={{ textDecoration: "none", display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{
              fontFamily: "var(--font-display, var(--font-serif, Georgia, serif))",
              fontSize: "var(--text-xl, 20px)", fontWeight: 800, color: "var(--accent, #C96442)",
            }}>Biblio</span>
            <span style={{ fontSize: "var(--text-xs, 12px)", color: "var(--text-muted, #8A857A)" }}>
              продукт
            </span>
          </a>
          <nav style={{ marginLeft: "auto", display: "flex", gap: "var(--space-4, 16px)", flexWrap: "wrap" }}>
            {NAV.map((n) => (
              <a key={n.id} href={"#" + n.id} style={{
                textDecoration: "none", color: "var(--text-body, #36291F)",
                fontSize: "var(--text-sm, 13px)", fontWeight: 600,
              }}>{n.label}</a>
            ))}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <div style={{ background: "var(--surface-card, #FBF6EC)", borderBottom: "1px solid var(--border-default, #D6D1C4)" }}>
        <div style={{ ...wrap, padding: "var(--space-10, 56px) var(--space-5, 20px)" }}>
          <h1 style={{
            fontFamily: "var(--font-display, var(--font-serif, Georgia, serif))",
            fontSize: "var(--text-4xl, 40px)", lineHeight: 1.15, fontWeight: 800,
            color: "var(--text-strong, #241C16)", margin: "0 0 var(--space-3, 12px)",
          }}>
            {PRODUCT.name} — {PRODUCT.tagline}
          </h1>
          <p style={{ ...lead, maxWidth: 760 }}>{PRODUCT.lead}</p>
          <div style={{ display: "flex", gap: "var(--space-2, 8px)", flexWrap: "wrap", marginTop: "var(--space-5, 20px)" }}>
            {PRODUCT.facts.map((fct) => (
              <span key={fct} style={{
                display: "inline-flex", alignItems: "center",
                background: "var(--accent-weak, #F6E7DF)",
                border: "1px solid var(--accent-weak-border, #ECC9B9)",
                color: "var(--accent, #C96442)", borderRadius: "var(--radius-pill, 999px)",
                padding: "5px 12px", fontSize: "var(--text-xs, 12px)", fontWeight: 600,
              }}>{fct}</span>
            ))}
          </div>
          <div style={{ marginTop: "var(--space-6, 24px)", display: "flex", gap: "var(--space-3, 12px)", flexWrap: "wrap" }}>
            <a href="#demo" style={{
              textDecoration: "none", display: "inline-flex", alignItems: "center",
              height: "var(--control-h-lg, 46px)", padding: "0 var(--space-6, 24px)",
              borderRadius: "var(--radius-md, 8px)", background: "var(--accent, #C96442)",
              color: "var(--accent-fg, #fff)", fontWeight: 700, fontSize: "var(--text-base, 15px)",
            }}>Получить демодоступ</a>
            <a href="#functional" style={{
              textDecoration: "none", display: "inline-flex", alignItems: "center",
              height: "var(--control-h-lg, 46px)", padding: "0 var(--space-6, 24px)",
              borderRadius: "var(--radius-md, 8px)", background: "var(--surface-card, #fff)",
              color: "var(--text-strong, #241C16)", border: "1px solid var(--border-strong, #D6D1C4)",
              fontWeight: 700, fontSize: "var(--text-base, 15px)",
            }}>Документация</a>
          </div>
        </div>
      </div>

      {/* Контент */}
      <main style={{ ...wrap, padding: "var(--space-8, 32px) var(--space-5, 20px) var(--space-12, 64px)" }}>
        {/* Функциональные характеристики */}
        <Section id={FUNCTIONAL.id} title={FUNCTIONAL.title}>
          <div style={card}><BulletDoc doc={FUNCTIONAL} /></div>

          <h3 style={{ ...h3, marginTop: "var(--space-6, 24px)" }}>Технические характеристики</h3>
          <div style={{ ...card, padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm, 13px)" }}>
              <tbody>
                {TECH.map((t, i) => (
                  <tr key={i} style={{ borderTop: i ? "1px solid var(--border-subtle, #E4E0D6)" : "none" }}>
                    <th scope="row" style={{
                      textAlign: "left", verticalAlign: "top", width: "34%",
                      padding: "var(--space-3, 12px) var(--space-4, 16px)",
                      fontWeight: 600, color: "var(--text-strong, #241C16)",
                      background: "var(--surface-sunken, #ECE0CB)",
                    }}>{t.param}</th>
                    <td style={{ padding: "var(--space-3, 12px) var(--space-4, 16px)", color: "var(--text-body, #36291F)" }}>
                      {t.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Руководство */}
        <Section id={GUIDE.id} title={GUIDE.title}>
          <div style={card}><BulletDoc doc={GUIDE} /></div>
        </Section>

        {/* Установка */}
        <Section id={INSTALL.id} title={INSTALL.title}>
          <div style={card}>
            <p style={{ ...lead, fontSize: "var(--text-base, 15px)", marginBottom: "var(--space-4, 16px)" }}>{INSTALL.intro}</p>
            <h3 style={h3}>Установка одной командой (docker-compose)</h3>
            <pre style={pre}>{INSTALL_STEPS.join("\n")}</pre>
            <p style={{ margin: "var(--space-3, 12px) 0", color: "var(--text-body, #36291F)" }}>
              Открыть <b>https://localhost</b> (в dev принять предупреждение о самоподписанном сертификате).
            </p>
            <h3 style={h3}>Провижининг первого арендатора</h3>
            <pre style={pre}>{PROVISION_STEP}</pre>
            <h3 style={h3}>Системные требования (минимальные)</h3>
            <ul style={{ margin: 0, paddingLeft: "var(--space-5, 20px)", lineHeight: 1.6 }}>
              {REQUIREMENTS.map((r, i) => <li key={i} style={{ marginBottom: 4 }}>{r}</li>)}
            </ul>
          </div>
        </Section>

        {/* Безопасность и соответствие */}
        <Section id="security" title="Информационная безопасность и соответствие">
          <div style={card}>
            <ul style={{ margin: 0, paddingLeft: "var(--space-5, 20px)", lineHeight: 1.6 }}>
              {SECURITY.map((s, i) => <li key={i} style={{ marginBottom: 4 }}>{s}</li>)}
            </ul>
          </div>
        </Section>

        {/* Форма заявки на демодоступ */}
        <Section id="demo" title="Заявка на демодоступ">
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr)", gap: "var(--space-6, 24px)" }}>
            <div style={card}>
              <p style={{ ...lead, fontSize: "var(--text-base, 15px)", margin: "0 0 var(--space-5, 20px)" }}>
                Оставьте заявку — мы выдадим доступ к работающему демо-стенду Biblio
                (сервер в РФ). Заполните контактные данные и подтвердите согласие на
                обработку персональных данных (152-ФЗ).
              </p>
              <DemoRequestForm />
            </div>
          </div>
        </Section>

        {/* Ссылки на полные документы */}
        <Section id="docs" title="Полная документация">
          <div style={card}>
            <ul style={{ margin: 0, paddingLeft: "var(--space-5, 20px)", lineHeight: 1.8 }}>
              {DOC_LINKS.map((d) => (
                <li key={d.href}>
                  <a href={d.href} target="_blank" rel="noopener noreferrer"
                    style={{ color: "var(--text-link, var(--accent, #C96442))", fontWeight: 600 }}>
                    {d.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      </main>

      <footer style={{ borderTop: "1px solid var(--border-default, #D6D1C4)", background: "var(--surface-card, #FBF6EC)" }}>
        <div style={{ ...wrap, padding: "var(--space-6, 24px) var(--space-5, 20px)", color: "var(--text-muted, #8A857A)", fontSize: "var(--text-sm, 13px)" }}>
          <b style={{ color: "var(--accent, #C96442)" }}>Biblio</b> — система автоматизации библиотек.
          Интерфейс на русском языке; сервер и данные — в РФ.{" "}
          <a href="/" style={{ color: "var(--text-link, var(--accent, #C96442))" }}>Перейти к каталогу</a>
        </div>
      </footer>
    </div>
  );
}
