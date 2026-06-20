import * as React from "react";

export interface Suggestion {
  term: string;
  /** Частота термина в словаре. */
  count?: number;
}

/**
 * Поисковая строка: одно поле с автокомплитом из словаря, кнопка «Найти»,
 * опц. ссылка на расширенный поиск. Клавиатура: ↑/↓ по подсказкам, Enter — поиск/выбор.
 *
 * @startingPoint section="Каталог" subtitle="Поле поиска с автокомплитом словаря" viewport="760x150"
 */
export interface SearchBarProps {
  value?: string;
  onChange?: (value: string) => void;
  /** Запуск поиска (Enter в пустом списке подсказок или кнопка). */
  onSearch?: (value: string) => void;
  /** Подсказки словаря (строки или {term,count}). */
  suggestions?: (Suggestion | string)[];
  onPickSuggestion?: (s: Suggestion | string) => void;
  placeholder?: string;
  /** Если задан — показывает ссылку «Расширенный поиск». */
  onAdvanced?: () => void;
  /** Если задан — показывает крупную кнопку «Сброс» рядом с «Поиск» (§1.5). */
  onReset?: () => void;
  buttonLabel?: string;
  className?: string;
}

export function SearchBar(props: SearchBarProps): JSX.Element;
