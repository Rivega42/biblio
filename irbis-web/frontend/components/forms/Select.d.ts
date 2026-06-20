import * as React from "react";

export type SelectOption = string | { value: string; label: string };

/** Нативный select со стилизованной обёрткой и подписью. */
export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  label?: string;
  /** Список опций. Игнорируется, если переданы children (<option>). */
  options?: SelectOption[];
  size?: "sm" | "md" | "lg";
}

export function Select(props: SelectProps): JSX.Element;
