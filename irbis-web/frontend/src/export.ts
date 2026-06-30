// Client-side export of bibliographic descriptions: RIS, BibTeX, ГОСТ Р 7.0.100.
// All generation is pure-string + Blob download — no network, no server calls.
// Field mapping (ИРБИС/UNIMARC-подобный формат записи):
//   200 a/e/f — заглавие; 700/701 — авторы; 210 a/c/d — место/издательство/год;
//   215 — объём; 10 a — ISBN; 101 a — язык; 675 a — УДК.
import type { RecordData, FieldVal, ResultItem } from "./api";
import { LANG } from "./api";

const sf = (f: FieldVal | undefined, c: string): string =>
  !f ? "" : (f.subfields[c] || f.subfields[c.toUpperCase()] || f.subfields[c.toLowerCase()] || "");

// Normalised, format-agnostic view of one record's citation fields.
export interface CiteFields {
  mfn: number;
  title: string;       // 200a + : 200e
  responsibility: string; // 200f
  authors: string[];   // 700/701 «Фамилия, И.О.»
  place: string;       // 210a
  publisher: string;   // 210c
  year: string;        // 210d
  extent: string;      // 215a (+ c/e)
  isbn: string;        // 10a
  lang: string;        // 101a (код)
  udc: string;         // 675a
}

function authorName(f: FieldVal): string {
  const a = sf(f, "A");
  const g = sf(f, "G") || sf(f, "B");
  if (!a) return "";
  return g ? a + ", " + g : a;
}

export function citeFields(d: RecordData): CiteFields {
  const F = (tag: string) => d.fields.filter((x) => x.tag === tag);
  const F1 = (tag: string) => F(tag)[0];
  const f200 = F1("200");
  const titleA = sf(f200, "A") || (d.brief || "");
  const titleE = sf(f200, "E");
  const f210 = F1("210");
  const f215 = F1("215");
  return {
    mfn: d.mfn,
    title: [titleA, titleE].filter(Boolean).join(" : "),
    responsibility: sf(f200, "F"),
    authors: ["700", "701"].flatMap(F).map(authorName).filter(Boolean),
    place: sf(f210, "A"),
    publisher: sf(f210, "C"),
    year: sf(f210, "D"),
    extent: [sf(f215, "A"), sf(f215, "C"), sf(f215, "E")].filter(Boolean).join(" : "),
    isbn: sf(F1("10"), "A"),
    lang: sf(F1("101"), "A") || (F1("101")?.value ?? ""),
    udc: sf(F1("675"), "A") || (F1("675")?.value ?? ""),
  };
}

// Split «Фамилия, И.О.» → BibTeX/RIS «Фамилия, И.О.» is already author order;
// RIS AU expects «Last, First».
const yearDigits = (y: string) => (y.match(/\d{4}/) || [""])[0] || y;

export function toRIS(c: CiteFields): string {
  const L: string[] = [];
  L.push("TY  - BOOK");
  for (const a of c.authors) L.push("AU  - " + a);
  if (c.title) L.push("TI  - " + c.title);
  if (c.publisher) L.push("PB  - " + c.publisher);
  if (c.place) L.push("CY  - " + c.place);
  if (yearDigits(c.year)) L.push("PY  - " + yearDigits(c.year));
  if (c.extent) L.push("SP  - " + c.extent);
  if (c.isbn) L.push("SN  - " + c.isbn);
  if (c.lang) L.push("LA  - " + c.lang);
  if (c.udc) L.push("N1  - УДК " + c.udc);
  L.push("ER  - ");
  return L.join("\r\n") + "\r\n";
}

function bibKey(c: CiteFields): string {
  const first = (c.authors[0] || c.title || "rec").split(/[\s,]+/)[0].replace(/[^A-Za-zА-Яа-я0-9]/g, "");
  return (first || "rec") + (yearDigits(c.year) || c.mfn);
}

export function toBibTeX(c: CiteFields): string {
  const fields: [string, string][] = [];
  if (c.authors.length) fields.push(["author", c.authors.join(" and ")]);
  if (c.title) fields.push(["title", c.title]);
  if (c.publisher) fields.push(["publisher", c.publisher]);
  if (c.place) fields.push(["address", c.place]);
  if (yearDigits(c.year)) fields.push(["year", yearDigits(c.year)]);
  if (c.isbn) fields.push(["isbn", c.isbn]);
  if (c.lang) fields.push(["language", LANG[c.lang] || c.lang]);
  if (c.extent) fields.push(["note", "Объём: " + c.extent + (c.udc ? "; УДК " + c.udc : "")]);
  else if (c.udc) fields.push(["note", "УДК " + c.udc]);
  const body = fields.map(([k, v]) => "  " + k + " = {" + v.replace(/[{}]/g, "") + "}").join(",\n");
  return "@book{" + bibKey(c) + ",\n" + body + "\n}\n";
}

// ГОСТ Р 7.0.100-2018 — упрощённое библиографическое описание (одна ссылка).
// Заголовок (1 автор) . Заглавие : сведения / ответственность. — Место : Издательство, Год. — Объём. — ISBN.
export function toGOST(c: CiteFields): string {
  const parts: string[] = [];
  let head = "";
  if (c.authors.length === 1) head = c.authors[0] + ". ";
  let area = c.title || "[Без заглавия]";
  // сведения об ответственности
  const resp = c.responsibility || (c.authors.length ? c.authors.join(", ") : "");
  if (resp) area += " / " + resp;
  parts.push(head + area);
  const imprint = [c.place, c.publisher].filter(Boolean).join(" : ") +
    (c.year ? (c.place || c.publisher ? ", " : "") + c.year : "");
  if (imprint) parts.push("— " + imprint + ".");
  if (c.extent) parts.push("— " + c.extent + ".");
  if (c.isbn) parts.push("— ISBN " + c.isbn + ".");
  if (c.udc) parts.push("— УДК " + c.udc + ".");
  // join: «Заголовок Заглавие. — Место…»
  return parts.join(" ").replace(/\.\s*—/g, ". —").trim() + "\n";
}

// Краткая строка для корзины / письма.
export function toPlainLine(c: CiteFields): string {
  const a = c.authors.length ? c.authors.join(", ") + " " : "";
  const im = [c.place, c.publisher].filter(Boolean).join(" : ") + (c.year ? ", " + c.year : "");
  return (a + (c.title || "[Без заглавия]") + (im ? ". — " + im : "")).trim();
}

const MIME: Record<string, string> = {
  ris: "application/x-research-info-systems",
  bib: "application/x-bibtex",
  txt: "text/plain;charset=utf-8",
  csv: "text/csv;charset=utf-8",
};

// Browser download via Blob + object URL. UTF-8, BOM for txt/csv so Windows-кириллица
// открывается корректно в блокноте и Excel.
export function downloadText(filename: string, text: string, ext: string): void {
  const isBom = ext === "txt" || ext === "csv";
  const data = isBom ? "﻿" + text : text;
  const blob = new Blob([data], { type: MIME[ext] || "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Convenience: build + download one record in a given format.
export function exportRecord(d: RecordData, fmt: "ris" | "bib" | "gost"): void {
  const c = citeFields(d);
  if (fmt === "ris") downloadText("record_" + c.mfn + ".ris", toRIS(c), "ris");
  else if (fmt === "bib") downloadText("record_" + c.mfn + ".bib", toBibTeX(c), "bib");
  else downloadText("record_" + c.mfn + ".txt", toGOST(c), "txt");
}

// --- Корзина (отбор) -------------------------------------------------------
// Basket items carry only brief search-result data (нет полной записи), поэтому
// CiteFields строится из заглавия/автора/года.
export function citeFromItem(it: ResultItem): CiteFields {
  return {
    mfn: it.mfn,
    title: it.title || "",
    responsibility: "",
    authors: it.author ? [it.author] : [],
    place: "", publisher: "",
    year: it.year || "",
    extent: "", isbn: "", lang: "", udc: "",
  };
}

// CSV выборки (Excel-дружественный): №, заглавие, автор, год, MFN, база.
function csvCell(v: string | number | undefined): string {
  const s = (v ?? "").toString();
  return /[",\r\n;]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
export function toCSV(items: ResultItem[]): string {
  const head = ["№", "Заглавие", "Автор", "Год", "MFN", "База"];
  const rows = items.map((it, i) =>
    [i + 1, it.title || "", it.author || "", it.year || "", it.mfn, it.db || ""].map(csvCell).join(","));
  return [head.map(csvCell).join(","), ...rows].join("\r\n") + "\r\n";
}

export function exportBasket(items: ResultItem[], fmt: "ris" | "bib" | "txt" | "csv"): void {
  const cites = items.map(citeFromItem);
  if (fmt === "ris") {
    downloadText("basket.ris", cites.map(toRIS).join("\r\n"), "ris");
  } else if (fmt === "bib") {
    downloadText("basket.bib", cites.map(toBibTeX).join("\n"), "bib");
  } else if (fmt === "csv") {
    downloadText("basket.csv", toCSV(items), "csv");
  } else {
    const body = cites.map((c, i) => (i + 1) + ". " + toPlainLine(c)).join("\n");
    downloadText("basket.txt", body + "\n", "txt");
  }
}

// «Отправить на почту» — mailto: со списком в теле письма.
export function basketMailto(items: ResultItem[]): string {
  const lines = items.map((it, i) => (i + 1) + ". " + toPlainLine(citeFromItem(it)));
  const subject = "Список изданий из каталога (" + items.length + ")";
  const body = "Отобранные издания:\n\n" + lines.join("\n") + "\n";
  return "mailto:?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
}
