import * as React from "react";

/** Радиокнопка. Сгруппируйте по общему `name`. */
export interface RadioProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
}

export function Radio(props: RadioProps): JSX.Element;
