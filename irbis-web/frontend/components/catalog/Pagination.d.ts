import * as React from "react";

/**
 * Постраничная навигация: номера страниц + вперёд/назад + размер страницы.
 * Контролируемый компонент — позиция хранится снаружи (сохраняется при возврате из карточки).
 */
export interface PaginationProps {
  page?: number;
  pageCount?: number;
  onPage?: (page: number) => void;
  /** Текущий размер страницы; если задан вместе с onPageSize — показывает селект. */
  pageSize?: number;
  onPageSize?: (size: number) => void;
  pageSizeOptions?: number[];
  /** Всего найдено — показывается в счётчике рядом с номером страницы. */
  total?: number;
  /** Компактный режим для дублирующей строки навигации сверху (§1.6). */
  compact?: boolean;
  className?: string;
}

export function Pagination(props: PaginationProps): JSX.Element;
