import * as React from "react";

/** Универсальный бейдж/счётчик. Для статусов экземпляров используйте StatusBadge. */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "accent" | "solid" | "success" | "warning" | "danger";
  /** Компактный круглый вид счётчика. */
  count?: boolean;
}

export function Badge(props: BadgeProps): JSX.Element;
