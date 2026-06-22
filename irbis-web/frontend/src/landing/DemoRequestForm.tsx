import React from "react";
import { CONSENT_TEXT } from "./content";

// Форма заявки на демодоступ (#226). POST /api/demo-request (публичный, тот же
// origin). Поля: ФИО, e-mail, телефон, учреждение, должность + ОБЯЗАТЕЛЬНОЕ
// согласие 152-ФЗ. Без согласия кнопка отправки заблокирована, а сервер всё равно
// вернёт 400 (двойная защита). Biblio-токены, плоский Style A.

interface FormState {
  fullName: string;
  email: string;
  phone: string;
  institution: string;
  position: string;
  consent: boolean;
}

const EMPTY: FormState = {
  fullName: "", email: "", phone: "", institution: "", position: "", consent: false,
};

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type Status = "idle" | "sending" | "ok" | "error";

const field: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  height: "var(--control-h-md, 40px)",
  padding: "0 var(--space-3, 12px)",
  borderRadius: "var(--radius-md, 8px)",
  border: "1px solid var(--border-default, #D6D1C4)",
  background: "var(--surface-card, #fff)",
  color: "var(--text-body, #36291F)",
  fontSize: "var(--text-base, 15px)",
  fontFamily: "var(--font-body, inherit)",
};

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: "var(--text-sm, 13px)",
  fontWeight: 600, color: "var(--text-strong, #241C16)",
  marginBottom: "var(--space-1, 4px)",
};

function Row(props: {
  id: string; label: string; required?: boolean; type?: string;
  value: string; onChange: (v: string) => void; placeholder?: string;
  autoComplete?: string;
}) {
  return (
    <div style={{ marginBottom: "var(--space-4, 16px)" }}>
      <label htmlFor={props.id} style={labelStyle}>
        {props.label}{props.required ? <span style={{ color: "var(--danger-500, #C0392B)" }}> *</span> : null}
      </label>
      <input
        id={props.id}
        type={props.type || "text"}
        required={props.required}
        value={props.value}
        placeholder={props.placeholder}
        autoComplete={props.autoComplete}
        onChange={(e) => props.onChange(e.target.value)}
        style={field}
      />
    </div>
  );
}

export function DemoRequestForm() {
  const [f, setF] = React.useState<FormState>(EMPTY);
  const [status, setStatus] = React.useState<Status>("idle");
  const [errorMsg, setErrorMsg] = React.useState("");
  const set = (k: keyof FormState) => (v: string) => setF((s) => ({ ...s, [k]: v }));

  const fullNameOk = f.fullName.trim().length > 0;
  const emailOk = EMAIL_RE.test(f.email.trim());
  const canSubmit = fullNameOk && emailOk && f.consent && status !== "sending";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setStatus("sending");
    setErrorMsg("");
    try {
      const res = await fetch("/api/demo-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName: f.fullName.trim(),
          email: f.email.trim(),
          phone: f.phone.trim(),
          institution: f.institution.trim(),
          position: f.position.trim(),
          consent: f.consent,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data && data.ok) {
        setStatus("ok");
        setF(EMPTY);
      } else {
        setStatus("error");
        setErrorMsg((data && data.error && data.error.message) || "Не удалось отправить заявку. Попробуйте позже.");
      }
    } catch {
      setStatus("error");
      setErrorMsg("Сеть недоступна. Проверьте подключение и попробуйте снова.");
    }
  }

  if (status === "ok") {
    return (
      <div
        role="status"
        style={{
          padding: "var(--space-6, 24px)",
          borderRadius: "var(--radius-lg, 10px)",
          background: "var(--success-bg, #E4F0E8)",
          border: "1px solid var(--success-500, #2E7D52)",
          color: "var(--text-strong, #241C16)",
        }}
      >
        <div style={{ fontWeight: 700, fontSize: "var(--text-lg, 17px)", marginBottom: 6 }}>
          Заявка отправлена
        </div>
        <p style={{ margin: 0, color: "var(--text-body, #36291F)", lineHeight: 1.5 }}>
          Спасибо! Мы свяжемся с вами по указанному e-mail и выдадим демодоступ к
          стенду Biblio (сервер в РФ).
        </p>
        <button
          type="button"
          onClick={() => setStatus("idle")}
          style={{
            marginTop: "var(--space-4, 16px)",
            height: "var(--control-h-md, 40px)", padding: "0 var(--space-4, 16px)",
            borderRadius: "var(--radius-md, 8px)", cursor: "pointer",
            background: "var(--surface-card, #fff)", color: "var(--text-strong, #241C16)",
            border: "1px solid var(--border-default, #D6D1C4)", fontWeight: 600,
          }}
        >
          Отправить ещё одну заявку
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate aria-label="Заявка на демодоступ">
      <Row id="dr-fullName" label="ФИО" required value={f.fullName}
        onChange={set("fullName")} autoComplete="name" placeholder="Иванова Мария Петровна" />
      <Row id="dr-email" label="E-mail" required type="email" value={f.email}
        onChange={set("email")} autoComplete="email" placeholder="name@example.org" />
      <Row id="dr-phone" label="Телефон" value={f.phone}
        onChange={set("phone")} autoComplete="tel" placeholder="+7 ___ ___-__-__" />
      <Row id="dr-institution" label="Учреждение (библиотека/организация)" value={f.institution}
        onChange={set("institution")} autoComplete="organization" placeholder="ЦГБ им. Пушкина" />
      <Row id="dr-position" label="Должность" value={f.position}
        onChange={set("position")} autoComplete="organization-title" placeholder="Заведующая отделом" />

      <label
        htmlFor="dr-consent"
        style={{
          display: "flex", gap: "var(--space-2, 8px)", alignItems: "flex-start",
          margin: "var(--space-2, 8px) 0 var(--space-5, 20px)",
          fontSize: "var(--text-sm, 13px)", color: "var(--text-body, #36291F)",
          lineHeight: 1.5, cursor: "pointer",
        }}
      >
        <input
          id="dr-consent"
          type="checkbox"
          checked={f.consent}
          onChange={(e) => setF((s) => ({ ...s, consent: e.target.checked }))}
          style={{ marginTop: 3, width: 16, height: 16, flex: "none", accentColor: "var(--accent, #C96442)" }}
        />
        <span>
          {CONSENT_TEXT}
          <span style={{ color: "var(--danger-500, #C0392B)" }}> *</span>
        </span>
      </label>

      {status === "error" && (
        <div
          role="alert"
          style={{
            marginBottom: "var(--space-4, 16px)", padding: "var(--space-3, 12px)",
            borderRadius: "var(--radius-md, 8px)",
            background: "var(--danger-bg, #F7E4E1)",
            border: "1px solid var(--danger-500, #C0392B)",
            color: "var(--text-strong, #241C16)", fontSize: "var(--text-sm, 13px)",
          }}
        >
          {errorMsg}
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        style={{
          width: "100%", height: "var(--control-h-lg, 46px)",
          borderRadius: "var(--radius-md, 8px)", cursor: canSubmit ? "pointer" : "not-allowed",
          background: "var(--accent, #C96442)", color: "var(--accent-fg, #fff)",
          border: "none", fontWeight: 700, fontSize: "var(--text-base, 15px)",
          opacity: canSubmit ? 1 : 0.55,
          transition: "opacity .15s, background .15s",
        }}
      >
        {status === "sending" ? "Отправка…" : "Отправить заявку на демодоступ"}
      </button>
      <p style={{ margin: "var(--space-3, 12px) 0 0", fontSize: "var(--text-xs, 12px)", color: "var(--text-muted, #8A857A)", lineHeight: 1.5 }}>
        Поля, отмеченные <span style={{ color: "var(--danger-500, #C0392B)" }}>*</span>, обязательны.
        Без согласия на обработку персональных данных заявка не принимается (152-ФЗ).
      </p>
    </form>
  );
}
