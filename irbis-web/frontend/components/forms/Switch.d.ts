import * as React from "react";

/** Переключатель (вкл/выкл). Для бинарных настроек: усечение, фильтры, режимы. */
export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
}

export function Switch(props: SwitchProps): JSX.Element;
