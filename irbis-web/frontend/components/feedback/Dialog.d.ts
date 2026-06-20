import * as React from "react";

/**
 * Модальное окно. ESC и клик по подложке закрывают. Используется для потока заказа.
 */
export interface DialogProps {
  open: boolean;
  onClose?: () => void;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Контент подвала (кнопки). */
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  children?: React.ReactNode;
  className?: string;
}

export function Dialog(props: DialogProps): JSX.Element | null;
