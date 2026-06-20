import * as React from "react";

/** Плейсхолдер-блок состояния загрузки (шиммер). */
export interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  variant?: "text" | "block" | "circle";
  radius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton(props: SkeletonProps): JSX.Element;

/** Готовый скелетон карточки результата (для списка выдачи). */
export function SkeletonResult(props: { showThumb?: boolean }): JSX.Element;
