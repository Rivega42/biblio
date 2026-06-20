import * as React from "react";

export interface ViewerFile {
  /** MARC-поле источника: "955" (приоритетное) или "951". */
  field?: "955" | "951";
  label?: string;
  /** Тип содержимого. */
  kind?: "pdf" | "image" | "djvu";
  /** Кол-во страниц (для PDF — постраничная навигация). */
  pages?: number;
  /** Оттенок плейсхолдера изображения (hue 0–360). */
  tint?: number;
  viewOnly?: boolean;
  requiresAuth?: boolean;
  /** Приоритет (955 над 951): меньше = выше. */
  priority?: number;
}

/**
 * Просмотрщик файла/изображения — строго VIEW-ONLY (§1.7, §10):
 * нет кнопки скачивания и путей к файлу, контекстное меню по правой кнопке
 * заблокировано, перетаскивание изображения отключено. Для PDF — подпись
 * «документ pdf-формата» и постраничная навигация. При `canView=false`
 * показывает состояние «нужен вход». Приоритет 955 над 951 решает вызывающая
 * сторона при выборе файла.
 *
 * @startingPoint section="Каталог" subtitle="Просмотрщик файла (view-only)" viewport="900x620"
 */
export interface FileViewerProps {
  open: boolean;
  file: ViewerFile | null;
  title?: string;
  /** Есть ли право на просмотр (учитывает requiresAuth + вход). */
  canView?: boolean;
  /** Искомые термины — подсвечиваются в тексте PDF (§4, §10). */
  terms?: string[];
  /** Номера релевантных страниц — кнопки быстрого перехода. */
  relevantPages?: number[];
  onClose?: () => void;
}

export function FileViewer(props: FileViewerProps): JSX.Element | null;
