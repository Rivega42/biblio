import * as React from "react";

/**
 * Единый паттерн состояний: пусто / ошибка / нет прав. Иконка + заголовок +
 * текст + опц. подсказки + действие. Сообщения дружелюбные, без служебных деталей.
 *
 * @startingPoint section="Обратная связь" subtitle="Пусто / ошибка / нет прав" viewport="700x340"
 */
export interface EmptyStateProps {
  variant?: "neutral" | "error" | "locked";
  /** Имя иконки (по умолчанию зависит от variant). */
  icon?: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** Список подсказок «как изменить запрос». */
  hints?: React.ReactNode[];
  /** Кнопка(и) действия. */
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState(props: EmptyStateProps): JSX.Element;
