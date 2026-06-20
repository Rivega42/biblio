import * as React from "react";

export type FieldType = "text" | "menu" | "dict" | "tree" | "bool" | "authority" | "date";

export interface DictEntry { term: string; count?: number; code?: string; }
export interface TreeNodeDef { code?: string; label: string; children?: TreeNodeDef[]; }

export interface FieldDef {
  /** MARC-код поля/подполя, напр. "200", "^a". */
  code?: string;
  label: string;
  /** Тип ввода → контрол: text | menu(.mnu) | dict | tree(.tre) | bool | authority | date. */
  type: FieldType;
  required?: boolean;
  /** Повторяемое поле — добавление/удаление вхождений. */
  repeatable?: boolean;
  /** Вложенные подполя (для составных полей). Каждое — свой FieldDef. */
  subfields?: FieldDef[];
  /** Значения для menu/bool. */
  options?: (string | { value: string; label: string })[];
  /** Словарь автодополнения (префикс) для type="dict". */
  dictionary?: DictEntry[];
  /** Авторитетный файл для type="authority". */
  authority?: DictEntry[];
  /** Иерархический справочник для type="tree". */
  tree?: TreeNodeDef[];
  placeholder?: string;
  hint?: string;
}

/**
 * DynamicField (§6) — «главный» компонент каталогизации: ТИП ПОЛЯ определяет
 * контрол. Управляется декларативным описанием поля из профиля базы
 * (FIELD_CATALOG): свободный текст / меню .mnu / словарь с автодополнением /
 * иерархический справочник .tre / да-нет / авторитетный файл / дата. Подполя —
 * вложенные группы; повторяемые поля — добавление/удаление вхождений; ФЛК
 * через проп error. Значение: одиночное, либо массив вхождений (repeatable),
 * вхождение с подполями — объект { [code]: value }.
 *
 * @startingPoint section="Каталогизация" subtitle="Динамическое поле ввода по типу" viewport="560x200"
 */
export interface DynamicFieldProps {
  field: FieldDef;
  value?: any;
  onChange: (value: any) => void;
  /** Сообщение ФЛК (валидации). */
  error?: string;
  className?: string;
}

export function DynamicField(props: DynamicFieldProps): JSX.Element;
