import * as React from "react";

export interface ToastProps {
  variant?: "info" | "success" | "warning" | "error";
  title?: React.ReactNode;
  children?: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

export interface ToastItem {
  id: string | number;
  variant?: "info" | "success" | "warning" | "error";
  title?: React.ReactNode;
  message?: React.ReactNode;
}

/** Одиночный тост. */
export function Toast(props: ToastProps): JSX.Element;

/** Фиксированный контейнер для стопки тостов (правый нижний угол). */
export function ToastViewport(props: {
  toasts: ToastItem[];
  onDismiss?: (id: string | number) => void;
}): JSX.Element;
