import * as React from "react";

/**
 * Встроенное сообщение (в потоке страницы). Для всплывающих уведомлений — Toast.
 * Дружелюбный текст без служебных деталей (без стека, кодов протокола).
 *
 * @startingPoint section="Обратная связь" subtitle="Алерты: info/success/warning/error" viewport="700x150"
 */
export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "error";
  title?: React.ReactNode;
  /** Если задан — показывает кнопку закрытия. */
  onClose?: () => void;
}

export function Alert(props: AlertProps): JSX.Element;
