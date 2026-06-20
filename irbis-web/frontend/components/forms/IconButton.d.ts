import * as React from "react";

/** Кнопка-иконка без текста. Всегда требует `label` для доступности. */
export interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  /** Имя иконки. */
  icon: string;
  /** Доступная подпись (aria-label + title). Обязательна. */
  label: string;
  variant?: "ghost" | "outline" | "accent" | "solid";
  size?: "sm" | "md" | "lg";
}

export function IconButton(props: IconButtonProps): JSX.Element;
