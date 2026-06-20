import * as React from "react";

/**
 * Контейнер под серверно-отрендеренный контент (PFT) с базовой типографикой.
 * ВАЖНО: серверный HTML должен быть очищен (санитайзинг) ДО вставки — передайте
 * функцию `sanitize` (например, обёртку DOMPurify) либо уже очищенный html.
 */
export interface PftBlockProps {
  /** Серверно-отрендеренный HTML (очищенный). */
  html?: string;
  /** Функция очистки; применяется к html перед вставкой. */
  sanitize?: (raw: string) => string;
  /** Показывать заголовок-метку над блоком. */
  showLabel?: boolean;
  label?: string;
  /** Вместо html можно передать готовый React-контент. */
  children?: React.ReactNode;
  className?: string;
}

export function PftBlock(props: PftBlockProps): JSX.Element;
