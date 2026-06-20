import * as React from "react";

/**
 * Линейная иконка из набора ИРБИС-Веб (24×24, обводка currentColor).
 * Используйте для всех иконок интерфейса — не вставляйте сырые SVG.
 *
 * @startingPoint section="Иконки" subtitle="Локальный линейный набор" viewport="700x150"
 */
export interface IconProps extends React.SVGProps<SVGSVGElement> {
  /** Имя иконки из набора (см. ICON_NAMES). */
  name:
    | "search" | "x" | "chevron-down" | "chevron-up" | "chevron-left" | "chevron-right"
    | "chevrons-left" | "chevrons-right" | "arrow-left" | "arrow-right" | "check"
    | "plus" | "minus" | "filter" | "sliders" | "book" | "book-open" | "image" | "images"
    | "archive" | "calendar" | "calendar-star" | "user" | "log-in" | "log-out"
    | "bookmark" | "bookmark-check" | "check-circle" | "alert-triangle" | "alert-octagon"
    | "info" | "x-circle" | "clock" | "map-pin" | "external-link" | "download" | "share"
    | "link" | "copy" | "list" | "grid" | "eye" | "eye-off" | "type" | "accessibility"
    | "sun" | "file-text" | "newspaper" | "tag" | "rotate-ccw" | "menu" | "loader"
    | "map" | "layers" | "globe" | "help-circle" | "panel-left";
  /** Размер в px (ширина и высота). По умолчанию 20. */
  size?: number;
  /** Толщина обводки. По умолчанию 1.75. */
  strokeWidth?: number;
  /** Доступная подпись. Если задана — role="img"; иначе иконка скрыта от скринридера. */
  label?: string;
}

export function Icon(props: IconProps): JSX.Element;

/** Все доступные имена иконок. */
export const ICON_NAMES: string[];
