import React from "react";

/**
 * ИРБИС-Веб — набор линейных иконок.
 * 24×24, обводка currentColor, скруглённые концы. Локально, без сети.
 * Стиль: Lucide/Feather. Заменяется на self-hosted Lucide при необходимости.
 */
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m16.5 16.5 4 4"/>',
  x: '<path d="M5 5 19 19"/><path d="M19 5 5 19"/>',
  "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
  "chevron-up": '<polyline points="6 15 12 9 18 15"/>',
  "chevron-left": '<polyline points="15 18 9 12 15 6"/>',
  "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
  "chevrons-left": '<polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/>',
  "chevrons-right": '<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>',
  "arrow-left": '<path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/>',
  "arrow-right": '<path d="M5 12h14"/><polyline points="12 5 19 12 12 19"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  filter: '<path d="M22 4H2l8 9.46V20l4-2v-4.54L22 4z"/>',
  "sliders": '<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  "book-open": '<path d="M12 7v14"/><path d="M3 5h5a3 3 0 0 1 3 3v12a2.5 2.5 0 0 0-2.5-2.5H3z"/><path d="M21 5h-5a3 3 0 0 0-3 3v12a2.5 2.5 0 0 1 2.5-2.5H21z"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  images: '<rect x="6" y="6" width="15" height="15" rx="2"/><circle cx="11" cy="11" r="1.4"/><path d="m21 17-3.5-3.5L11 20"/><path d="M3 16V5a2 2 0 0 1 2-2h11"/>',
  archive: '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><path d="M10 12h4"/>',
  calendar: '<rect x="3" y="4.5" width="18" height="17" rx="2"/><path d="M16 2.5v4"/><path d="M8 2.5v4"/><path d="M3 10h18"/>',
  "calendar-star": '<rect x="3" y="4.5" width="18" height="17" rx="2"/><path d="M16 2.5v4"/><path d="M8 2.5v4"/><path d="M3 10h18"/><path d="m12 12.5 1 2 2.2.2-1.6 1.5.5 2.1-2.1-1.1-2.1 1.1.5-2.1L8.8 14.7 11 14.5z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 20a8 8 0 0 1 16 0"/>',
  "log-in": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>',
  "log-out": '<path d="M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  bookmark: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  "bookmark-check": '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/><polyline points="9 10 11 12 15 8"/>',
  "check-circle": '<circle cx="12" cy="12" r="9"/><polyline points="8.5 12.5 11 15 15.5 9.5"/>',
  "alert-triangle": '<path d="M10.3 4.3 1.8 18a1.6 1.6 0 0 0 1.4 2.4h17.6a1.6 1.6 0 0 0 1.4-2.4L13.7 4.3a1.6 1.6 0 0 0-2.8 0z"/><line x1="12" y1="9.5" x2="12" y2="14"/><path d="M12 17.5h.01"/>',
  "alert-octagon": '<path d="M7.9 3h8.2L21 7.9v8.2L16.1 21H7.9L3 16.1V7.9z"/><line x1="12" y1="8" x2="12" y2="12.5"/><path d="M12 16h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
  "x-circle": '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6"/><path d="M9 9l6 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
  "map-pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.5"/>',
  "external-link": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/>',
  download: '<path d="M12 3v12"/><polyline points="7 10 12 15 17 10"/><path d="M5 19h14"/>',
  "share": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/>',
  "link": '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><path d="M3.5 6h.01"/><path d="M3.5 12h.01"/><path d="M3.5 18h.01"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  eye: '<path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7z"/><circle cx="12" cy="12" r="3"/>',
  "eye-off": '<path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.2 4.2"/><path d="M9.9 5.2A9.6 9.6 0 0 1 12 5c6 0 9.5 7 9.5 7a17 17 0 0 1-3.2 4"/><path d="M6.5 6.6A16.6 16.6 0 0 0 2.5 12S6 19 12 19a9.6 9.6 0 0 0 2.6-.4"/>',
  type: '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>',
  accessibility: '<circle cx="12" cy="12" r="9.5"/><circle cx="12" cy="6.2" r="1.2"/><path d="M5.5 9.5 12 11l6.5-1.5"/><path d="M12 11v4"/><path d="m9.5 20 2.5-5 2.5 5"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.3 17.7-1.4 1.4"/><path d="m19.1 4.9-1.4 1.4"/>',
  "file-text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/>',
  newspaper: '<path d="M4 22a2 2 0 0 1-2-2V6a1 1 0 0 1 1-1h13a1 1 0 0 1 1 1v14a2 2 0 0 1-2 2z"/><path d="M18 8h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2"/><line x1="6" y1="9" x2="13" y2="9"/><line x1="6" y1="13" x2="13" y2="13"/><line x1="6" y1="17" x2="11" y2="17"/>',
  tag: '<path d="M20.6 13.4 11 3.8a2 2 0 0 0-1.4-.6H4a1 1 0 0 0-1 1v5.6a2 2 0 0 0 .6 1.4l9.6 9.6a2 2 0 0 0 2.8 0l4.6-4.6a2 2 0 0 0 0-2.8z"/><circle cx="7.5" cy="7.5" r="1.2"/>',
  "rotate-ccw": '<path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><polyline points="3 3 3 8 8 8"/>',
  menu: '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.2-8.5" opacity="0.9"/>',
  "map": '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>',
  layers: '<path d="m12 2 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z"/>',
  "help-circle": '<circle cx="12" cy="12" r="9"/><path d="M9.2 9.2a2.8 2.8 0 0 1 5.5.8c0 1.8-2.7 2.7-2.7 2.7"/><path d="M12 17h.01"/>',
  "panel-left": '<rect x="3" y="4" width="18" height="16" rx="2"/><line x1="9.5" y1="4" x2="9.5" y2="20"/>',
  snowflake: '<line x1="12" y1="2" x2="12" y2="22"/><line x1="3.3" y1="7" x2="20.7" y2="17"/><line x1="3.3" y1="17" x2="20.7" y2="7"/><path d="M12 2.5 9.7 4.8M12 2.5l2.3 2.3M12 21.5l-2.3-2.3M12 21.5l2.3-2.3"/><path d="m3.3 7 1 3.1M3.3 7l3.1-1M20.7 17l-3.1 1M20.7 17l-1-3.1"/><path d="m3.3 17 3.1 1M3.3 17l1-3.1M20.7 7l-1 3.1M20.7 7l-3.1-1"/>',
  flower: '<circle cx="12" cy="12" r="2.6"/><path d="M12 9.4a2.6 2.6 0 0 1 0-5.2 2.6 2.6 0 0 1 0 5.2"/><path d="M12 14.6a2.6 2.6 0 0 0 0 5.2 2.6 2.6 0 0 0 0-5.2"/><path d="M14.6 12a2.6 2.6 0 0 1 5.2 0 2.6 2.6 0 0 1-5.2 0"/><path d="M9.4 12a2.6 2.6 0 0 0-5.2 0 2.6 2.6 0 0 0 5.2 0"/>',
  music: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
  drama: '<path d="M3 6.5C3 5 4 4.5 6.5 4.5S10 5 10 6.5v3C10 12.5 8.5 14 6.5 14S3 12.5 3 9.5z"/><path d="M5 9.2s.6.6 1.5.6 1.5-.6 1.5-.6"/><path d="M14 11.5c0-1.5 1-2 3.5-2s3.5.5 3.5 2v3c0 3-1.5 4.5-3.5 4.5S14 17.5 14 14.5z"/><path d="M16 17.2s.6.6 1.5.6 1.5-.6 1.5-.6"/>',
  stamp: '<path d="M5 21h14"/><path d="M8 17v-1a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v1H8z"/><path d="M10 12a3 3 0 0 1-2-2.8V7a4 4 0 0 1 8 0v2.2A3 3 0 0 1 14 12"/>',
  maximize: '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/><path d="M21 16v3a2 2 0 0 1-2 2h-3"/><path d="M8 21H5a2 2 0 0 1-2-2v-3"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M3 13h18"/>',
  "graduation-cap": '<path d="M22 9 12 5 2 9l10 4 10-4z"/><path d="M6 10.5V16c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5.5"/>',
  edit: '<path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4z"/>',
  "scan-line": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="6" y1="12" x2="18" y2="12"/>',
  package: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5"/><path d="M12 12v9"/>',
  "clipboard-check": '<rect x="8" y="3" width="8" height="4" rx="1"/><path d="M16 5h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
  "bar-chart": '<line x1="5" y1="21" x2="5" y2="10"/><line x1="12" y1="21" x2="12" y2="4"/><line x1="19" y1="21" x2="19" y2="14"/><line x1="3" y1="21" x2="21" y2="21"/>',
  "trending-up": '<polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  shield: '<path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6z"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 5.2a3.2 3.2 0 0 1 0 6"/><path d="M17.5 14.3A6 6 0 0 1 21 20"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9z"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  "credit-card": '<rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>',
  "refresh-cw": '<polyline points="21 4 21 9 16 9"/><path d="M20 13a8 8 0 1 1-2.3-5.7L21 9"/><polyline points="3 20 3 15 8 15"/>',
  star: '<path d="m12 3 2.7 5.5 6 .9-4.3 4.2 1 6L12 17l-5.4 2.6 1-6L3.3 9.4l6-.9z"/>',
  "folder-tree": '<path d="M3 4h4l2 2h3a1 1 0 0 1 1 1v2H3z"/><path d="M3 9h11v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M16 6h5"/><path d="M16 12h5"/><path d="M19 6v6"/>',
  "list-tree": '<path d="M21 6H8"/><path d="M21 12H8"/><path d="M21 18H8"/><path d="M3 4v14a2 2 0 0 0 2 2h1"/><path d="M3 11h3"/>',
  "chevrons-up-down": '<polyline points="7 15 12 20 17 15"/><polyline points="7 9 12 4 17 9"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>',
  "rotate-cw": '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><polyline points="21 3 21 8 16 8"/>',
  "trash": '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M5 6l1 14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-14"/>',
  wallet: '<path d="M3 7a2 2 0 0 1 2-2h13a1 1 0 0 1 1 1v2"/><path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="13" r="1.2"/>',
};

export function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
  className = "",
  style,
  label,
  ...rest
}) {
  const inner = ICONS[name] || "";
  const a11y = label
    ? { role: "img", "aria-label": label }
    : { "aria-hidden": "true", focusable: "false" };
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ flex: "none", display: "block", ...style }}
      {...a11y}
      {...rest}
      dangerouslySetInnerHTML={{ __html: inner }}
    />
  );
}

export const ICON_NAMES = Object.keys(ICONS);
