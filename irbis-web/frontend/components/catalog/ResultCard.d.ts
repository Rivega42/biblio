import * as React from "react";

export interface ResultItem {
  mfn?: number;
  title: string;
  author?: string;
  year?: string;
  docType?: string;
  availability?: "available" | "issued" | "unknown";
  /** Доп. поля из конфига базы (фонд/опись, язык, техника и т. п.). */
  fields?: { label: string; value: string }[];
  /** URL превью (для изобразительных баз). */
  thumb?: string;
}

/**
 * Карточка результата поиска — плотная, сканируемая. Заглавие/автор/год/тип
 * + бейдж статуса; чекбокс «отметить». Поддерживает превью и доп. поля из конфига базы.
 *
 * @startingPoint section="Каталог" subtitle="Карточка результата (плотная)" viewport="760x150"
 */
export interface ResultCardProps {
  item: ResultItem;
  checked?: boolean;
  onToggleCheck?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpen?: () => void;
  /** Показывать чекбокс «отметить». */
  showCheck?: boolean;
  /** Показывать превью слева (изобразительные базы). */
  showThumb?: boolean;
  /** Иконка типа документа. */
  typeIcon?: string;
  /** Метка базы-источника (мультибазовый поиск, §1.4) — напр. «Книги», «Эскизы». */
  dbTag?: string;
  className?: string;
}

export function ResultCard(props: ResultCardProps): JSX.Element;
