import * as React from "react";

/**
 * Чип-фильтр. Два режима:
 *  • снимаемый (активный фильтр) — задайте `onRemove`, опц. `group`;
 *  • переключатель (выбор фильтра) — задайте `onToggle` + `pressed`, опц. `count`.
 *
 * @startingPoint section="Формы" subtitle="Чипы: активные фильтры и переключатели" viewport="700x150"
 */
export interface FilterChipProps extends React.HTMLAttributes<HTMLElement> {
  label: React.ReactNode;
  /** Группа фильтра (показывается префиксом «Группа:») — для снимаемого чипа. */
  group?: string;
  /** Счётчик (частота термина) — для режима переключателя. */
  count?: number;
  /** Обработчик снятия — включает режим снимаемого чипа с крестиком. */
  onRemove?: () => void;
  /** Обработчик переключения — включает режим кнопки-переключателя. */
  onToggle?: () => void;
  /** Нажат ли переключатель. */
  pressed?: boolean;
  /** Нейтральный вид (серый) вместо акцентного. */
  plain?: boolean;
}

export function FilterChip(props: FilterChipProps): JSX.Element;
