// Декларативные формы расширенного поиска под каждую базу — реплика боевого
// jirbis СПб ГТБ (#255 п.4). Источник полей: docs/design/JIRBIS_PER_BASE_SEARCH_FIELDS.md
// (снято с http://85.235.221.54:8087/jirbis2/ — label + ИРБИС-префикс + тип).
//
// Тип поля:
//   "text"   — обычное текстовое поле → "PREFIX=значение$"
//   "year"   — диапазон «с–по» (два поля year1/year2) → перечисление "G=YYYY" по диапазону
//   "select" — выпадающий список (combobox); опции тянутся из словаря /api/terms по префиксу
//   "bool"   — чекбокс «наличие эл.копии / полного текста» (ed_filter), спец-фильтр
//
// База, для которой здесь НЕТ записи, использует общую (генерик) расширенную форму
// App.tsx (поле «префикс + значение»). Это graceful-фолбэк для не подтверждённых баз.

export type FieldType = "text" | "year" | "select" | "bool";

export interface SearchFieldDef {
  label: string;
  prefix: string;        // ИРБИС-префикс ("A","T","G",…); для чекбокса — спец-ключ "ed_filter"/"IZ900"/"IZ606"
  type: FieldType;
  group?: string;        // визуальная группа (напр. «Роли», «Дата события»)
}

export interface BaseFormDef {
  base: string;          // человекочитаемое название базы (для подзаголовка формы)
  fields: SearchFieldDef[];
  note?: string;         // пометка для не до конца подтверждённых баз
}

// Полная форма «Электронного каталога» (как на скриншоте jirbis — 9 полей).
const EK_FIELDS: SearchFieldDef[] = [
  { label: "Автор/Персоналия", prefix: "A", type: "text" },
  { label: "Заглавие", prefix: "T", type: "text" },
  { label: "Предметная рубрика", prefix: "S", type: "text" },
  { label: "Место издания", prefix: "MI", type: "text" },
  { label: "Год издания", prefix: "G", type: "year" },
  { label: "Вид/тип документа", prefix: "V", type: "select" },
  { label: "Язык документа", prefix: "J", type: "select" },
  { label: "Инв. номер", prefix: "IN", type: "text" },
  { label: 'Наличие «Электронная копия / полный текст»', prefix: "ed_filter", type: "bool" },
];

export const BASE_SEARCH_FORMS: Record<string, BaseFormDef> = {
  // ── Электронный каталог + стандартный книжный каталог ──────────────────────
  EK: { base: "Электронный каталог", fields: EK_FIELDS },
  IBIS: { base: "Электронный каталог", fields: EK_FIELDS },

  // ── Периодические издания ─────────────────────────────────────────────────
  PERIO: { base: "Периодические издания", fields: [
    { label: "Заглавие (журналы, газеты)", prefix: "TJ", type: "text" },
    { label: "Редактор / издатель", prefix: "AJ", type: "text" },
    { label: "Место издания", prefix: "MI", type: "text" },
    { label: "Год издания", prefix: "G", type: "year" },
    { label: "ISSN", prefix: "B", type: "text" },
    { label: "Язык документа", prefix: "J", type: "select" },
    { label: "Происхождение экземпляра", prefix: "PROIS", type: "text" },
    { label: "Коллекция", prefix: "COLLT", type: "text" },
    { label: 'Наличие «Электронная копия / полный текст»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Статьи из книг и периодических изданий (код SBO) ──────────────────────
  SBO: { base: "Статьи из книг и периодических изданий", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Автор/Персоналия", prefix: "A", type: "text" },
    { label: "Заглавие статьи", prefix: "T", type: "text" },
    { label: "Предмет / тема", prefix: "S", type: "text" },
    { label: "Наименование произведения", prefix: "NPS", type: "text" },
    { label: "Коллектив / мероприятие", prefix: "M", type: "text" },
    { label: "Год источника статьи", prefix: "GI", type: "text" },
    { label: "Заглавие источника статьи", prefix: "TI", type: "text" },
    { label: "Наличие «изоматериал»", prefix: "IZ606", type: "bool" },
    { label: 'Наличие «Электронная копия изображения»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Аннотированный указатель пьес (с блоком «Роли») ───────────────────────
  PLAY: { base: "Аннотированный указатель пьес", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Персоны", prefix: "A", type: "text" },
    { label: "Заглавия", prefix: "TP", type: "text" },
    { label: "Жанры и темы", prefix: "DES", type: "select" },
    { label: "Время написания пьесы", prefix: "G", type: "text" },
    { label: "Место написания пьесы", prefix: "MN", type: "text" },
    { label: "Язык написания", prefix: "JZI", type: "text" },
    { label: "Женские", prefix: "NJ", type: "text", group: "Роли" },
    { label: "Мужские", prefix: "NM", type: "text", group: "Роли" },
    { label: "Детские", prefix: "ND", type: "text", group: "Роли" },
    { label: "Куклы", prefix: "NK", type: "text", group: "Роли" },
    { label: "Животные", prefix: "NG", type: "text", group: "Роли" },
    { label: "Сказочные персонажи", prefix: "NS", type: "text", group: "Роли" },
    { label: "Без определения", prefix: "NO", type: "text", group: "Роли" },
    { label: "Эпизодические", prefix: "NE", type: "text", group: "Роли" },
    { label: "Количество действий", prefix: "KDP", type: "text" },
    { label: "Время действия", prefix: "HS", type: "text" },
    { label: "Место действия", prefix: "GEO", type: "text" },
  ]},

  // ── Эскизный фонд ─────────────────────────────────────────────────────────
  ESKIZ: { base: "Эскизный фонд", fields: [
    { label: "Автор эскиза, художник", prefix: "AU", type: "text" },
    { label: "Персоналия", prefix: "P", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
    { label: "Коллектив / мероприятие", prefix: "M", type: "text" },
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Год издания", prefix: "G", type: "year" },
    { label: "Эскизы художников (комплекты)", prefix: "TS", type: "text" },
    { label: "Характер документа", prefix: "HD", type: "select" },
    { label: "Инвентарь", prefix: "IN", type: "text" },
    { label: 'Наличие «Электронная копия / полный текст»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Иллюстративные и историко-бытовые материалы ───────────────────────────
  HPO: { base: "Иллюстративные и историко-бытовые материалы", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Автор/Персоналия", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "NSI", type: "text" },
    { label: "Предмет / тема", prefix: "S", type: "text" },
    { label: "Коллектив", prefix: "M", type: "text" },
    { label: "Географическое наименование", prefix: "GST", type: "text" },
    { label: "Народы", prefix: "GPN", type: "text" },
    { label: "Хронология", prefix: "HS", type: "text" },
    { label: "Наличие «изоматериал»", prefix: "IZ900", type: "bool" },
    { label: 'Наличие «Электронная копия изображения»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Собрание архивных документов (Фонд↔Опись, поле 488) ───────────────────
  GUAR: { base: "Собрание архивных документов", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Все фонды", prefix: "IFT", type: "text" },
    { label: "Название фонда", prefix: "T", type: "text" },
    { label: "Номер фонда", prefix: "IF", type: "select" },
    { label: "Персоналия", prefix: "A", type: "text" },
    { label: "Организация", prefix: "M", type: "text" },
    { label: "Год создания документов", prefix: "DN", type: "year" },
    { label: 'Наличие «Электронные копии»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Указатель литературы о СПбГТБ (лёгкий пресет) ─────────────────────────
  UKAZ: { base: "Указатель литературы о СПбГТБ", fields: [
    { label: "Ключевые слова", prefix: "KT=FT!", type: "text" },
    { label: "Автор и др. ответственные лица", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
  ]},

  // ── Календарь премьер Петербургских театров (подтверждено по имени БД на проде) ──
  TUAR: { base: "Календарь премьер Петербургских театров", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Персоны", prefix: "A", type: "text" },
    { label: "Спектакли / события", prefix: "TP", type: "text" },
    { label: "Год события", prefix: "SG", type: "text", group: "Дата события" },
    { label: "Месяц", prefix: "SM", type: "select", group: "Дата события" },
    { label: "День", prefix: "SD", type: "select", group: "Дата события" },
    { label: "Коллектив", prefix: "M", type: "text" },
    { label: "Вид и тип события", prefix: "VTS", type: "select" },
    { label: "Роли и представления", prefix: "RS", type: "text" },
    { label: "Автор источника", prefix: "BA1", type: "text", group: "Библиографический источник" },
    { label: "Заглавие источника", prefix: "BZ", type: "text", group: "Библиографический источник" },
  ]},

  // ── Картотека Всеволодского-Гернгросса (общий имидж-каталог) ───────────────
  IMAGE: { base: "Картотека Всеволодского-Гернгросса", fields: [
    { label: "Ключевые слова", prefix: "K", type: "text" },
    { label: "Автор/Персоналия", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
    { label: "Предмет / тема", prefix: "S", type: "text" },
    { label: 'Наличие «Электронная копия изображения»', prefix: "ed_filter", type: "bool" },
  ]},

  // ── Цензура пьес на языках народов Российской империи (имидж-каталог) ──────
  IMGZENZ: { base: "Цензура пьес на языках народов Российской империи", fields: [
    { label: "Ключевые слова", prefix: "KT=FT!", type: "text" },
    { label: "Автор и др. ответственные лица", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
    { label: "Язык", prefix: "J", type: "select" },
  ]},

  // ── Либретто балетов / опер (имидж-каталог, лёгкий пресет) ─────────────────
  IMGBALET: { base: "Либретто балетов", fields: [
    { label: "Ключевые слова", prefix: "KT=FT!", type: "text" },
    { label: "Автор и др. ответственные лица", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
  ]},
  IMGOPERA: { base: "Либретто опер, оперетт", fields: [
    { label: "Ключевые слова", prefix: "KT=FT!", type: "text" },
    { label: "Автор и др. ответственные лица", prefix: "A", type: "text" },
    { label: "Заглавие", prefix: "T", type: "text" },
  ]},
};
// Все 14 публичных баз СПб ГТБ покрыты per-base формами (SBO=Статьи добавлена).

export function baseFormFor(code: string): BaseFormDef | undefined {
  return BASE_SEARCH_FORMS[code];
}
