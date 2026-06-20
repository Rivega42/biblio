import * as React from "react";

export interface NavNode {
  code?: string;
  label: string;
  count?: number;
  children?: NavNode[];
}

export interface Navigator {
  id: string;
  label: string;
  tree: NavNode[];
}

/**
 * TreeNav (§4, §10) — навигатор-классификатор (ГРНТИ/УДК/ББК): раскрываемое
 * дерево рубрик с количеством записей у каждого узла; выбор узла фильтрует
 * выдачу. Несколько навигаторов переключаются вкладками.
 *
 * @startingPoint section="Каталог" subtitle="Навигатор-классификатор (дерево)" viewport="320x320"
 */
export interface TreeNavProps {
  navigators: Navigator[];
  /** Код выбранного узла. */
  value?: string | null;
  /** Клик по узлу (null при снятии выбора). */
  onPick?: (node: NavNode | null) => void;
  className?: string;
}

export function TreeNav(props: TreeNavProps): JSX.Element | null;
