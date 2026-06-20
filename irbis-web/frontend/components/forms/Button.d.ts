import * as React from "react";

/**
 * Основная кнопка действия. Главное действие на экране — `primary`,
 * вторичное — `secondary`, малозаметное — `ghost`, опасное — `danger`.
 *
 * @startingPoint section="Формы" subtitle="Кнопка: варианты, размеры, иконки, загрузка" viewport="700x150"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  /** Имя иконки слева (см. IconProps["name"]). */
  iconLeft?: string;
  /** Имя иконки справа. */
  iconRight?: string;
  /** Состояние загрузки — показывает спиннер, блокирует кнопку. */
  loading?: boolean;
  /** Растянуть на всю ширину. */
  block?: boolean;
}

export function Button(props: ButtonProps): JSX.Element;
