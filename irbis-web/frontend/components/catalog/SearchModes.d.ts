import * as React from "react";

export type SearchMode = "simple" | "advanced" | "complex" | "special";

/**
 * Модуль «Поисковые режимы» (§1.10, §7) — список режимов поиска; выбранный
 * выделяется цветом (акцентная подложка + цветная полоса). Состав режимов
 * приходит из конфига базы.
 *
 * @startingPoint section="Каталог" subtitle="Переключатель режимов поиска" viewport="320x220"
 */
export interface SearchModesProps {
  /** Доступные режимы (порядок сохраняется). */
  modes: SearchMode[];
  value?: SearchMode;
  onChange?: (mode: SearchMode) => void;
  heading?: string;
  /** Переопределение подписей: { special: "Поиск пьес" }. */
  labels?: Partial<Record<SearchMode, string>>;
  className?: string;
}

export function SearchModes(props: SearchModesProps): JSX.Element;
