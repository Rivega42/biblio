// Лёгкий i18n-каркас портала (#C10). Словарь RU/EN + реактивный хук useLang()
// (подписка на смену языка → перерисовка потребителей) + persist в localStorage.
// По умолчанию — русский. Ключи добавляются постепенно; неизвестный ключ
// возвращается как есть (безопасная деградация). Без внешних зависимостей.
import React from "react";

export type Lang = "ru" | "en";
export const LANGS: Lang[] = ["ru", "en"];

type Entry = { ru: string; en: string };
export const DICT: Record<string, Entry> = {
  "nav.reader": { ru: "Читатель", en: "Reader" },
  "nav.staff": { ru: "Сотрудник", en: "Staff" },
  "nav.dark": { ru: "Тёмная", en: "Dark" },
  "nav.light": { ru: "Светлая", en: "Light" },
  "nav.cabinet": { ru: "Кабинет", en: "My account" },
  "nav.login": { ru: "Вход", en: "Sign in" },
  "nav.logout": { ru: "Выйти", en: "Sign out" },
  // Лендинг / поиск (#D4)
  "hero.eyebrow": { ru: "Электронный каталог", en: "Electronic catalog" },
  "hero.title": { ru: "Найдите нужное издание в библиотеке", en: "Find the edition you need" },
  "hero.lead": { ru: "Книги, статьи, электронные версии и архивные материалы — поиск по всему фонду в одном окне.", en: "Books, articles, e-versions and archival materials — search the whole collection in one place." },
  "search.find": { ru: "Найти", en: "Search" },
  "search.in": { ru: "Искать в:", en: "Search in:" },
  "search.allbases": { ru: "Во всех базах", en: "All databases" },
  "search.popular": { ru: "Популярные запросы", en: "Popular queries" },
  "search.placeholder": { ru: "Например: основы программирования", en: "e.g.: programming basics" },
  "prefix.all": { ru: "Везде", en: "Everywhere" },
  "prefix.author": { ru: "Автор", en: "Author" },
  "prefix.title": { ru: "Заглавие", en: "Title" },
  "prefix.doctype": { ru: "Вид документа", en: "Document type" },
  "home.collections": { ru: "Тематические подборки", en: "Topic collections" },
  // АРМ сотрудника / модули (#D10)
  "staff.workspace": { ru: "Рабочее пространство сотрудника", en: "Staff workspace" },
  "staff.cataloging": { ru: "Каталогизация", en: "Cataloging" },
  "staff.acq": { ru: "Комплектование", en: "Acquisitions" },
  "staff.circ": { ru: "Книговыдача", en: "Circulation" },
  "staff.cells": { ru: "Ячеистое хранение", en: "Cell storage" },
  "staff.provision": { ru: "Книгообеспеченность", en: "Curriculum provision" },
  "staff.inv": { ru: "Инвентаризация", en: "Inventory" },
  "staff.cattools": { ru: "Каталог · инструменты", en: "Catalog · tools" },
  "staff.utilities": { ru: "Утилиты", en: "Utilities" },
  "staff.admin": { ru: "Администрирование", en: "Administration" },
  "staff.platform": { ru: "Платформа", en: "Platform" },
  "staff.migration": { ru: "Миграция", en: "Migration" },
  "staff.benchmark": { ru: "Сравнение", en: "Benchmark" },
};

const KEY = "biblio.lang";
let current: Lang = "ru";
try {
  const saved = typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null;
  if (saved === "en" || saved === "ru") current = saved;
} catch { /* localStorage недоступен — остаёмся на ru */ }
if (typeof document !== "undefined") document.documentElement.lang = current;

const subs = new Set<() => void>();

export function getLang(): Lang { return current; }

export function setLang(l: Lang): void {
  if (l !== "ru" && l !== "en") return;
  current = l;
  try { localStorage.setItem(KEY, l); } catch { /* игнор */ }
  if (typeof document !== "undefined") document.documentElement.lang = l;
  subs.forEach((fn) => fn());
}

// Перевод по ключу; неизвестный ключ → сам ключ (деградация без падения).
export function t(key: string): string {
  const e = DICT[key];
  return e ? e[current] : key;
}

// Реактивный хук: перерисовывает потребителя при смене языка.
export function useLang(): { lang: Lang; setLang: (l: Lang) => void; t: (key: string) => string } {
  const [, force] = React.useState(0);
  React.useEffect(() => {
    const fn = () => force((x) => x + 1);
    subs.add(fn);
    return () => { subs.delete(fn); };
  }, []);
  return { lang: current, setLang, t };
}
