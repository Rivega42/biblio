import * as React from "react";

/**
 * Текстовое поле с подписью, подсказкой/ошибкой, опц. иконкой и кнопкой очистки.
 *
 * @startingPoint section="Формы" subtitle="Поле ввода: подпись, иконка, очистка, ошибка" viewport="700x150"
 */
export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  /** Подпись над полем. */
  label?: string;
  /** Вспомогательный текст под полем. */
  hint?: string;
  /** Текст ошибки — переводит поле в состояние ошибки и связывает через aria. */
  error?: string;
  required?: boolean;
  size?: "sm" | "md" | "lg";
  /** Имя иконки слева внутри поля. */
  iconLeft?: string;
  /** Если задан — показывает кнопку очистки при непустом значении. */
  onClear?: () => void;
}

export function Input(props: InputProps): JSX.Element;
