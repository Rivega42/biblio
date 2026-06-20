import * as React from "react";

/** Флажок. Поддерживает промежуточное состояние (indeterminate). */
export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Подпись справа от флажка. */
  label?: React.ReactNode;
  /** Промежуточное состояние («часть выбрана»). */
  indeterminate?: boolean;
}

export function Checkbox(props: CheckboxProps): JSX.Element;
