import * as React from "react";

export interface DatabaseOption {
  id: string;
  name: string;
  /** id группы для иерархии (напр. "ek", "libretto"). Базы без group — верхнего уровня. */
  group?: string;
  /** Имя иконки (book, images, archive, calendar-star, music, drama, …). */
  icon?: string;
  /** Краткое пояснение под названием. */
  description?: string;
  /** Число записей (отображается справа). */
  count?: number;
  /** Демо-заглушка (помечается бейджем). */
  stub?: boolean;
}

export interface DatabaseGroup {
  id: string;
  label: string;
  icon?: string;
}

/**
 * Иерархический мультиселектор баз (§1.1) — одно окно «Электронный каталог и
 * Базы данных»: раскрываемые группы (ЭК, Базы Либретто) с чекбоксами,
 * «Выбрать все» / «Снять всё», БЕЗ галочек по умолчанию. Выбор баз меняет
 * доступные поля поиска и формат вывода (конфиг базы); используется
 * мультибазовым поиском.
 *
 * @startingPoint section="Каталог" subtitle="Иерархический выбор баз данных" viewport="700x150"
 */
export interface DatabaseSelectorProps {
  databases: DatabaseOption[];
  /** Метаданные групп: { ek: {label, icon}, … }. */
  groups?: Record<string, DatabaseGroup>;
  /** Массив id выбранных баз (без выбора по умолчанию — пустой). */
  value?: string[];
  onChange?: (ids: string[]) => void;
  /** Заголовок окна. По умолчанию «Электронный каталог и Базы данных». */
  title?: string;
  className?: string;
}

export function DatabaseSelector(props: DatabaseSelectorProps): JSX.Element;
