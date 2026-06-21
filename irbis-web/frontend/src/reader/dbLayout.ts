// Профили отображения выдачи по типу базы (#222, мульти-лейаут). Каждый код базы
// сопоставляется со списком доступных видов и видом по умолчанию:
//   list     — компактные строки (каталог книг);
//   gallery  — сетка обложек (используем существующий GalleryGrid);
//   calendar — группировка по дате/году/выпуску (периодика);
//   archive  — плотные архивные строки (фонды, дела).
// Профиль выбирается по коду активной базы; неизвестные базы → дефолт (list+gallery).
// Пользовательский тумблер «Список/Галерея» по-прежнему работает там, где оба вида
// доступны — поэтому в `views` для list/gallery-баз держим обе опции.

export type LayoutKind = "list" | "gallery" | "calendar" | "archive";

export interface DbLayoutProfile {
  // Доступные виды в порядке предпочтения; первый — вид по умолчанию.
  views: LayoutKind[];
  // Подпись профиля для подсказок (необязательно).
  hint?: string;
}

// Карта код-базы → профиль. Коды соответствуют распространённым базам ИРБИС64.
const PROFILES: Record<string, DbLayoutProfile> = {
  // Электронный каталог книг — список с возможностью галереи обложек.
  IBIS: { views: ["list", "gallery"], hint: "Книги: список или галерея обложек" },
  // База изображений / медиатека — галерея по умолчанию.
  IMAGE: { views: ["gallery", "list"], hint: "Изображения: галерея" },
  // Периодика / статьи — календарная группировка по году/выпуску.
  PERIO: { views: ["calendar", "list"], hint: "Периодика: по годам и выпускам" },
  // Архивные фонды и дела — плотные архивные строки.
  ARCH: { views: ["archive", "list"], hint: "Архив: дела и единицы хранения" },
};

// Дефолт для неизвестных баз: список + галерея (как у книжного каталога).
const DEFAULT_PROFILE: DbLayoutProfile = { views: ["list", "gallery"] };

export function layoutProfile(db: string): DbLayoutProfile {
  return PROFILES[(db || "").toUpperCase()] || DEFAULT_PROFILE;
}

// Вид по умолчанию для базы.
export function defaultLayout(db: string): LayoutKind {
  return layoutProfile(db).views[0];
}

// Доступен ли вид в профиле базы.
export function layoutAllows(db: string, kind: LayoutKind): boolean {
  return layoutProfile(db).views.includes(kind);
}
