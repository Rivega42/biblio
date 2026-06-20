import * as React from "react";

/** Кликабельная предметная рубрика (поля 600/601) — ведёт в поиск по рубрике. */
export interface SubjectTagProps extends React.HTMLAttributes<HTMLElement> {
  /** Рендерить как button (по умолчанию) или ссылку "a". */
  as?: "button" | "a";
  href?: string;
}

export function SubjectTag(props: SubjectTagProps): JSX.Element;
