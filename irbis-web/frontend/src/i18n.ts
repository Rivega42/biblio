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
