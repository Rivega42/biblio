import * as React from "react";

export interface TabDef {
  id: string;
  label: React.ReactNode;
  icon?: string;
  count?: number;
}

/** Вкладки. Контролируемые: value + onChange. */
export interface TabsProps {
  tabs: (TabDef | string)[];
  value?: string;
  onChange?: (id: string) => void;
  variant?: "underline" | "pill";
  className?: string;
}

export function Tabs(props: TabsProps): JSX.Element;
