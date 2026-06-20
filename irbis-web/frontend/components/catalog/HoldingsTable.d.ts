import * as React from "react";

export interface Holding {
  /** Место хранения (910^D). */
  location: string;
  /** Инвентарный номер (910^B). */
  inventory: string;
  /** Статус (910^A): available | issued | unknown. */
  status: "available" | "issued" | "unknown";
}

/**
 * Таблица экземпляров: место хранения / инвентарь / статус.
 * На узких экранах превращается в карточки. RFID и служебные id не показываем.
 */
export interface HoldingsTableProps {
  holdings: Holding[];
  /** Если задан — добавляет столбец действия «Заказать» (только для доступных). */
  onOrder?: (holding: Holding, index: number) => void;
  className?: string;
}

export function HoldingsTable(props: HoldingsTableProps): JSX.Element;
