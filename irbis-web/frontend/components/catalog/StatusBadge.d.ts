import * as React from "react";

export type HoldingStatus = "available" | "issued" | "unknown";

/**
 * Бейдж статуса экземпляра. Никогда не передаёт смысл только цветом —
 * всегда цвет + иконка + текст (a11y, ГОСТ Р 52872-2019).
 * available → «Доступен», issued → «Выдан», unknown → «Нет данных».
 *
 * @startingPoint section="Каталог" subtitle="Статусы экземпляров: цвет + иконка + текст" viewport="700x150"
 */
export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: HoldingStatus;
  /** Переопределить текст (по умолчанию — по статусу). */
  label?: string;
  size?: "sm" | "md";
  /** Компактный вид: цветная точка + текст, без подложки. */
  dot?: boolean;
}

export function StatusBadge(props: StatusBadgeProps): JSX.Element;
