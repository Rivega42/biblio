/* @ds-bundle: {"format":3,"namespace":"DesignSystem_d9a584","components":[{"name":"DatabaseSelector","sourcePath":"components/catalog/DatabaseSelector.jsx"},{"name":"HoldingsTable","sourcePath":"components/catalog/HoldingsTable.jsx"},{"name":"Pagination","sourcePath":"components/catalog/Pagination.jsx"},{"name":"PftBlock","sourcePath":"components/catalog/PftBlock.jsx"},{"name":"ResultCard","sourcePath":"components/catalog/ResultCard.jsx"},{"name":"SearchBar","sourcePath":"components/catalog/SearchBar.jsx"},{"name":"SearchModes","sourcePath":"components/catalog/SearchModes.jsx"},{"name":"StatusBadge","sourcePath":"components/catalog/StatusBadge.jsx"},{"name":"SubjectTag","sourcePath":"components/catalog/SubjectTag.jsx"},{"name":"TreeNav","sourcePath":"components/catalog/TreeNav.jsx"},{"name":"DynamicField","sourcePath":"components/cataloging/DynamicField.jsx"},{"name":"Alert","sourcePath":"components/feedback/Alert.jsx"},{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"EmptyState","sourcePath":"components/feedback/EmptyState.jsx"},{"name":"Skeleton","sourcePath":"components/feedback/Skeleton.jsx"},{"name":"SkeletonResult","sourcePath":"components/feedback/Skeleton.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"ToastViewport","sourcePath":"components/feedback/Toast.jsx"},{"name":"Button","sourcePath":"components/forms/Button.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"FilterChip","sourcePath":"components/forms/FilterChip.jsx"},{"name":"IconButton","sourcePath":"components/forms/IconButton.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Icon","sourcePath":"components/icon/Icon.jsx"},{"name":"ICON_NAMES","sourcePath":"components/icon/Icon.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"},{"name":"FileViewer","sourcePath":"components/viewer/FileViewer.jsx"}],"sourceHashes":{"components/catalog/DatabaseSelector.jsx":"44a5bee92c3e","components/catalog/HoldingsTable.jsx":"7801ac0581c5","components/catalog/Pagination.jsx":"bdd171b9844f","components/catalog/PftBlock.jsx":"91dd8ee35d7d","components/catalog/ResultCard.jsx":"b20687aba629","components/catalog/SearchBar.jsx":"c7a05ee448db","components/catalog/SearchModes.jsx":"2c714bf77809","components/catalog/StatusBadge.jsx":"2ce31e0e1b69","components/catalog/SubjectTag.jsx":"cd71e06b62a6","components/catalog/TreeNav.jsx":"3146e2f22f62","components/cataloging/DynamicField.jsx":"d6bbe7e5da81","components/feedback/Alert.jsx":"6c6570702ef0","components/feedback/Badge.jsx":"59a87c939201","components/feedback/Dialog.jsx":"349b33bc85bc","components/feedback/EmptyState.jsx":"ee1cc4bd3799","components/feedback/Skeleton.jsx":"f374a4559d7b","components/feedback/Toast.jsx":"d9b3691c3e5d","components/forms/Button.jsx":"9e125bc3ef4b","components/forms/Checkbox.jsx":"e96f1810b8ac","components/forms/FilterChip.jsx":"d8062759cb30","components/forms/IconButton.jsx":"6e8b79a925b2","components/forms/Input.jsx":"36e3abb1ab8b","components/forms/Radio.jsx":"aaaba84b3ff1","components/forms/Select.jsx":"f2254d01c323","components/forms/Switch.jsx":"6c74949a6c2b","components/icon/Icon.jsx":"cd71f6cfc35d","components/navigation/Tabs.jsx":"21a292ee8605","components/viewer/FileViewer.jsx":"ebc9849e151d","ui_kits/irbis-web/AccountScreens.jsx":"eeacea6dff82","ui_kits/irbis-web/App.jsx":"de47852aabf1","ui_kits/irbis-web/HomeScreen.jsx":"41954e3319ce","ui_kits/irbis-web/OrderModal.jsx":"a0ee2ffd7bd9","ui_kits/irbis-web/RecordScreen.jsx":"71d32c4a3595","ui_kits/irbis-web/ResultsScreen.jsx":"2e5691bcd73f","ui_kits/irbis-web/SeasonalFX.jsx":"f9d1f914332b","ui_kits/irbis-web/Shell.jsx":"3f8feecaa4fb","ui_kits/irbis-web/SpecialForm.jsx":"28a72dd1f0cd","ui_kits/irbis-web/StaffScreens.jsx":"9daaa73e5ff1","ui_kits/irbis-web/StaffWork.jsx":"d05dfd36af2a","ui_kits/irbis-web/data.js":"d41ccf51f475"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DesignSystem_d9a584 = window.DesignSystem_d9a584 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/catalog/PftBlock.jsx
try { (() => {
const CSS = `
.irb-pft{
  font-family:var(--font-body);font-size:var(--text-base);line-height:var(--leading-relaxed);
  color:var(--text-body);max-width:var(--content-max);
}
.irb-pft p{margin:0 0 var(--space-3);}
.irb-pft p:last-child{margin-bottom:0;}
.irb-pft b,.irb-pft strong{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-pft a{color:var(--text-link);text-decoration:underline;text-underline-offset:2px;}
.irb-pft h1,.irb-pft h2,.irb-pft h3,.irb-pft h4{font-family:var(--font-record-title);margin:var(--space-4) 0 var(--space-2);line-height:var(--leading-snug);}
.irb-pft h3{font-size:var(--text-lg);}
.irb-pft h4{font-size:var(--text-md);}
.irb-pft ul,.irb-pft ol{margin:0 0 var(--space-3);padding-inline-start:var(--space-5);}
.irb-pft li{margin-bottom:4px;}
.irb-pft dl{display:grid;grid-template-columns:max-content 1fr;gap:var(--space-2) var(--space-4);margin:0;}
.irb-pft dt{color:var(--text-muted);font-size:var(--text-sm);font-weight:var(--weight-semibold);}
.irb-pft dd{margin:0;color:var(--text-body);}
.irb-pft table{border-collapse:collapse;width:100%;margin:0 0 var(--space-3);font-size:var(--text-sm);}
.irb-pft td,.irb-pft th{border:var(--border-width) solid var(--border-subtle);padding:var(--space-2) var(--space-3);text-align:left;}
.irb-pft__label{display:flex;align-items:center;gap:var(--space-2);font-size:var(--text-2xs);
  text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);
  font-weight:var(--weight-semibold);font-family:var(--font-ui);margin-bottom:var(--space-3);}
.irb-pft__label::after{content:"";flex:1;height:1px;background:var(--border-subtle);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-pft-css")) {
  const s = document.createElement("style");
  s.id = "irb-pft-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function PftBlock({
  html = "",
  sanitize,
  showLabel = true,
  label = "Библиографическое описание",
  className = "",
  children
}) {
  // Безопасный рендер: серверный HTML должен быть очищен ДО вставки.
  // Если передан sanitize() — применяем его; иначе доверяем уже очищенному входу.
  const safe = typeof sanitize === "function" ? sanitize(html) : html;
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-pft ${className}`
  }, showLabel && /*#__PURE__*/React.createElement("div", {
    className: "irb-pft__label"
  }, label), children != null ? children : /*#__PURE__*/React.createElement("div", {
    dangerouslySetInnerHTML: {
      __html: safe
    }
  }));
}
Object.assign(__ds_scope, { PftBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/PftBlock.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-badge{
  display:inline-flex;align-items:center;gap:5px;
  font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);
  line-height:1;padding:3px 8px;border-radius:var(--radius-pill);
  border:var(--border-width) solid transparent;white-space:nowrap;
}
.irb-badge--neutral{background:var(--surface-sunken);color:var(--text-muted);border-color:var(--border-subtle);}
.irb-badge--accent{background:var(--accent-weak);color:var(--accent-press);border-color:var(--accent-weak-border);}
.irb-badge--solid{background:var(--accent);color:var(--accent-fg);}
.irb-badge--success{background:var(--success-bg);color:var(--status-available-strong);border-color:var(--status-available-border);}
.irb-badge--warning{background:var(--warning-bg);color:var(--status-issued-strong);border-color:var(--status-issued-border);}
.irb-badge--danger{background:var(--danger-bg);color:var(--danger-600);border-color:var(--danger-border);}
.irb-badge--count{min-width:18px;height:18px;justify-content:center;padding:0 5px;font-variant-numeric:tabular-nums;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-badge-css")) {
  const s = document.createElement("style");
  s.id = "irb-badge-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Badge({
  variant = "neutral",
  count = false,
  children,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("span", _extends({
    className: `irb-badge irb-badge--${variant}${count ? " irb-badge--count" : ""} ${className}`
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Skeleton.jsx
try { (() => {
const CSS = `
.irb-skel{
  display:block;background:linear-gradient(90deg,
    var(--surface-sunken) 25%, var(--surface-hover) 37%, var(--surface-sunken) 63%);
  background-size:400% 100%;border-radius:var(--radius-sm);
  animation:irb-shimmer 1.4s ease infinite;
}
@keyframes irb-shimmer{from{background-position:100% 0;}to{background-position:0 0;}}
@media (prefers-reduced-motion:reduce){.irb-skel{animation:none;background:var(--surface-sunken);}}
.irb-skel--text{height:.72em;margin:.18em 0;border-radius:var(--radius-xs);}
.irb-skel--circle{border-radius:var(--radius-round);}

.irb-skelcard{display:flex;gap:var(--space-3);background:var(--surface-card);
  border:var(--border-width) solid var(--border-subtle);border-radius:var(--radius-lg);padding:var(--space-4);}
.irb-skelcard__b{flex:1;display:flex;flex-direction:column;gap:var(--space-2);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-skel-css")) {
  const s = document.createElement("style");
  s.id = "irb-skel-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Skeleton({
  width = "100%",
  height = "1em",
  variant = "text",
  radius,
  className = "",
  style
}) {
  return /*#__PURE__*/React.createElement("span", {
    className: `irb-skel irb-skel--${variant} ${className}`,
    style: {
      width,
      height,
      borderRadius: radius,
      ...style
    },
    "aria-hidden": "true"
  });
}

/** Скелетон карточки результата — для состояния загрузки списка. */
function SkeletonResult({
  showThumb = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-skelcard",
    "aria-hidden": "true"
  }, /*#__PURE__*/React.createElement(Skeleton, {
    variant: "circle",
    width: 18,
    height: 18
  }), showThumb && /*#__PURE__*/React.createElement(Skeleton, {
    width: 56,
    height: 74,
    radius: "var(--radius-sm)"
  }), /*#__PURE__*/React.createElement("div", {
    className: "irb-skelcard__b"
  }, /*#__PURE__*/React.createElement(Skeleton, {
    width: "38%",
    height: 10
  }), /*#__PURE__*/React.createElement(Skeleton, {
    width: "72%",
    height: 18
  }), /*#__PURE__*/React.createElement(Skeleton, {
    width: "46%",
    height: 12
  })), /*#__PURE__*/React.createElement(Skeleton, {
    width: 84,
    height: 22,
    radius: "var(--radius-pill)"
  }));
}
Object.assign(__ds_scope, { Skeleton, SkeletonResult });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Skeleton.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-radio{display:inline-flex;align-items:flex-start;gap:var(--space-2);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);line-height:var(--leading-snug);}
.irb-radio--disabled{opacity:.5;cursor:not-allowed;}
.irb-radio__dot{
  flex:none;width:18px;height:18px;margin-top:1px;border-radius:var(--radius-round);
  border:var(--border-width-strong) solid var(--border-strong);background:var(--surface-card);
  display:inline-flex;align-items:center;justify-content:center;
  transition:border-color var(--dur-fast) var(--ease-standard);
}
.irb-radio input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-radio__dot::after{content:"";width:8px;height:8px;border-radius:var(--radius-round);
  background:var(--accent);transform:scale(0);transition:transform var(--dur-fast) var(--ease-standard);}
.irb-radio input:checked + .irb-radio__dot{border-color:var(--accent);}
.irb-radio input:checked + .irb-radio__dot::after{transform:scale(1);}
.irb-radio input:focus-visible + .irb-radio__dot{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-radio-css")) {
  const s = document.createElement("style");
  s.id = "irb-radio-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Radio({
  label,
  disabled = false,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: `irb-radio${disabled ? " irb-radio--disabled" : ""} ${className}`
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "radio",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "irb-radio__dot",
    "aria-hidden": "true"
  }), label != null && /*#__PURE__*/React.createElement("span", null, label));
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-switch{display:inline-flex;align-items:center;gap:var(--space-3);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-switch--disabled{opacity:.5;cursor:not-allowed;}
.irb-switch__track{
  flex:none;position:relative;width:40px;height:24px;border-radius:var(--radius-pill);
  background:var(--surface-active);border:var(--border-width) solid var(--border-default);
  transition:background-color var(--dur) var(--ease-standard), border-color var(--dur) var(--ease-standard);
}
.irb-switch input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-switch__thumb{
  position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:var(--radius-round);
  background:#fff;box-shadow:var(--shadow-xs);
  transition:transform var(--dur) var(--ease-standard);
}
.irb-switch input:checked + .irb-switch__track{background:var(--accent);border-color:var(--accent);}
.irb-switch input:checked + .irb-switch__track .irb-switch__thumb{transform:translateX(16px);}
.irb-switch input:focus-visible + .irb-switch__track{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-switch-css")) {
  const s = document.createElement("style");
  s.id = "irb-switch-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Switch({
  label,
  checked,
  disabled = false,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("label", {
    className: `irb-switch${disabled ? " irb-switch--disabled" : ""} ${className}`
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    role: "switch",
    checked: checked,
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "irb-switch__track",
    "aria-hidden": "true"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-switch__thumb"
  })), label != null && /*#__PURE__*/React.createElement("span", null, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/icon/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
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
  wallet: '<path d="M3 7a2 2 0 0 1 2-2h13a1 1 0 0 1 1 1v2"/><path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="13" r="1.2"/>'
};
function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
  className = "",
  style,
  label,
  ...rest
}) {
  const inner = ICONS[name] || "";
  const a11y = label ? {
    role: "img",
    "aria-label": label
  } : {
    "aria-hidden": "true",
    focusable: "false"
  };
  return /*#__PURE__*/React.createElement("svg", _extends({
    xmlns: "http://www.w3.org/2000/svg",
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: strokeWidth,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    className: className,
    style: {
      flex: "none",
      display: "block",
      ...style
    }
  }, a11y, rest, {
    dangerouslySetInnerHTML: {
      __html: inner
    }
  }));
}
const ICON_NAMES = Object.keys(ICONS);
Object.assign(__ds_scope, { Icon, ICON_NAMES });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/icon/Icon.jsx", error: String((e && e.message) || e) }); }

// components/catalog/SearchModes.jsx
try { (() => {
/* Модуль «Поисковые режимы» (§1.10, §7): список режимов поиска;
   выбранный ВЫДЕЛЯЕТСЯ ЦВЕТОМ. Состав режимов зависит от базы (конфиг). */

const CSS = `
.irb-modes{font-family:var(--font-ui);}
.irb-modes__hd{font-size:var(--text-2xs);text-transform:uppercase;letter-spacing:var(--tracking-caps);
  color:var(--text-subtle);font-weight:var(--weight-bold);margin-bottom:10px;}
.irb-modes__list{display:flex;flex-direction:column;gap:4px;}
.irb-modes__item{
  display:flex;align-items:center;gap:var(--space-2);width:100%;text-align:left;cursor:pointer;
  padding:9px var(--space-3);border-radius:var(--radius-sm);font-family:var(--font-ui);
  font-size:var(--text-sm);font-weight:var(--weight-medium);
  border:var(--border-width) solid transparent;background:transparent;color:var(--text-body);
  transition:background-color var(--dur) var(--ease-standard),color var(--dur) var(--ease-standard);
}
.irb-modes__item:hover{background:var(--surface-hover);}
.irb-modes__item--on{
  background:var(--accent-weak);border-color:var(--accent-weak-border);
  color:var(--accent-press);font-weight:var(--weight-semibold);
}
.irb-modes__item--on .irb-modes__ic{color:var(--accent);}
.irb-modes__ic{flex:none;color:var(--text-subtle);}
.irb-modes__bar{flex:none;width:3px;align-self:stretch;border-radius:2px;background:transparent;margin-right:2px;}
.irb-modes__item--on .irb-modes__bar{background:var(--accent);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-modes-css")) {
  const s = document.createElement("style");
  s.id = "irb-modes-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const META = {
  simple: {
    label: "Простой",
    icon: "search"
  },
  advanced: {
    label: "Расширенный",
    icon: "sliders"
  },
  complex: {
    label: "Комплексный",
    icon: "layers"
  },
  special: {
    label: "Спецформа базы",
    icon: "filter"
  }
};
function SearchModes({
  modes = ["simple"],
  value,
  onChange,
  heading = "Поисковые режимы",
  labels = {},
  className = ""
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-modes ${className}`
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-modes__hd"
  }, heading), /*#__PURE__*/React.createElement("div", {
    className: "irb-modes__list",
    role: "tablist",
    "aria-label": heading
  }, modes.map(m => {
    const meta = META[m] || {
      label: m,
      icon: "search"
    };
    const on = m === value;
    return /*#__PURE__*/React.createElement("button", {
      key: m,
      type: "button",
      role: "tab",
      "aria-selected": on,
      className: `irb-modes__item${on ? " irb-modes__item--on" : ""}`,
      onClick: () => onChange && onChange(m)
    }, /*#__PURE__*/React.createElement("span", {
      className: "irb-modes__bar",
      "aria-hidden": "true"
    }), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: meta.icon,
      size: 16,
      className: "irb-modes__ic"
    }), labels[m] || meta.label);
  })));
}
Object.assign(__ds_scope, { SearchModes });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/SearchModes.jsx", error: String((e && e.message) || e) }); }

// components/catalog/StatusBadge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-status{
  display:inline-flex;align-items:center;gap:var(--space-2);
  font-family:var(--font-ui);font-weight:var(--weight-semibold);
  border-radius:var(--radius-pill);border:var(--border-width) solid transparent;
  white-space:nowrap;line-height:1;
}
.irb-status--md{font-size:var(--text-sm);height:26px;padding:0 var(--space-3);}
.irb-status--sm{font-size:var(--text-xs);height:22px;padding:0 var(--space-2);}
.irb-status--dot{display:inline-flex;align-items:center;gap:var(--space-2);
  background:transparent;border:none;padding:0;font-weight:var(--weight-medium);font-size:var(--text-sm);}
.irb-status__dot{width:9px;height:9px;border-radius:var(--radius-round);flex:none;}

.irb-status--available{background:var(--status-available-bg);border-color:var(--status-available-border);color:var(--status-available-strong);}
.irb-status--issued{background:var(--status-issued-bg);border-color:var(--status-issued-border);color:var(--status-issued-strong);}
.irb-status--unknown{background:var(--status-unknown-bg);border-color:var(--status-unknown-border);color:var(--status-unknown-strong);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-status-css")) {
  const s = document.createElement("style");
  s.id = "irb-status-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const MAP = {
  available: {
    icon: "check-circle",
    text: "Доступен",
    dot: "var(--status-available)"
  },
  issued: {
    icon: "clock",
    text: "Выдан",
    dot: "var(--status-issued)"
  },
  unknown: {
    icon: "x-circle",
    text: "Нет данных",
    dot: "var(--status-unknown)"
  }
};
function StatusBadge({
  status = "unknown",
  label,
  size = "md",
  dot = false,
  className = "",
  ...rest
}) {
  const cfg = MAP[status] || MAP.unknown;
  const text = label || cfg.text;
  if (dot) {
    return /*#__PURE__*/React.createElement("span", _extends({
      className: `irb-status irb-status--dot ${className}`
    }, rest), /*#__PURE__*/React.createElement("span", {
      className: "irb-status__dot",
      style: {
        background: cfg.dot
      },
      "aria-hidden": "true"
    }), text);
  }
  return /*#__PURE__*/React.createElement("span", _extends({
    className: `irb-status irb-status--${status} irb-status--${size} ${className}`
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: cfg.icon,
    size: size === "sm" ? 13 : 15
  }), text);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/catalog/SubjectTag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-subject{
  display:inline-flex;align-items:center;gap:6px;
  font-family:var(--font-ui);font-size:var(--text-sm);
  height:28px;padding:0 var(--space-3);
  border-radius:var(--radius-sm);border:var(--border-width) solid var(--border-default);
  background:var(--surface-card);color:var(--text-body);
  cursor:pointer;text-decoration:none;white-space:nowrap;
  transition:border-color var(--dur) var(--ease-standard),
    background var(--dur) var(--ease-standard), color var(--dur) var(--ease-standard);
}
.irb-subject:hover{border-color:var(--accent);color:var(--accent-hover);background:var(--accent-weak);text-decoration:none;}
.irb-subject:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);outline-offset:1px;}
.irb-subject__icon{color:var(--text-subtle);}
.irb-subject:hover .irb-subject__icon{color:var(--accent);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-subject-css")) {
  const s = document.createElement("style");
  s.id = "irb-subject-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function SubjectTag({
  children,
  as = "button",
  className = "",
  ...rest
}) {
  const Comp = as;
  const extra = as === "button" ? {
    type: "button"
  } : {};
  return /*#__PURE__*/React.createElement(Comp, _extends({
    className: `irb-subject ${className}`
  }, extra, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "tag",
    size: 13,
    className: "irb-subject__icon"
  }), children);
}
Object.assign(__ds_scope, { SubjectTag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/SubjectTag.jsx", error: String((e && e.message) || e) }); }

// components/catalog/TreeNav.jsx
try { (() => {
/* TreeNav (§4, §10) — навигатор-классификатор (ГРНТИ/УДК/ББК): раскрываемое
   дерево рубрик с количеством записей; выбор узла фильтрует выдачу. Ленивая
   подача: показываем счётчик у каждого узла. */

const CSS = `
.irb-tnav{font-family:var(--font-ui);border:1px solid var(--border-subtle);border-radius:var(--radius-md);
  background:var(--surface-card);overflow:hidden;}
.irb-tnav__tabs{display:flex;border-bottom:1px solid var(--border-subtle);}
.irb-tnav__tab{flex:1;border:none;background:var(--surface-sunken);cursor:pointer;padding:7px 4px;
  font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);color:var(--text-muted);}
.irb-tnav__tab--on{background:var(--surface-card);color:var(--accent-press);box-shadow:inset 0 -2px 0 var(--accent);}
.irb-tnav__body{max-height:280px;overflow:auto;padding:4px;}
.irb-tnav__row{display:flex;align-items:center;gap:2px;border-radius:var(--radius-sm);}
.irb-tnav__row:hover{background:var(--surface-hover);}
.irb-tnav__tw{flex:none;width:20px;height:26px;display:flex;align-items:center;justify-content:center;border:none;background:none;cursor:pointer;color:var(--text-subtle);}
.irb-tnav__tw svg{transition:transform var(--dur) var(--ease-standard);}
.irb-tnav__tw--open svg{transform:rotate(90deg);}
.irb-tnav__pick{flex:1;min-width:0;display:flex;align-items:center;gap:8px;text-align:left;border:none;background:none;cursor:pointer;
  padding:5px 4px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-tnav__pick--on{color:var(--accent-press);font-weight:var(--weight-semibold);}
.irb-tnav__pick code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--text-subtle);flex:none;}
.irb-tnav__pick span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.irb-tnav__cnt{margin-left:auto;flex:none;font-size:var(--text-2xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;
  background:var(--surface-sunken);border-radius:var(--radius-pill);padding:1px 7px;}
.irb-tnav__pick--on + .irb-tnav__cnt,.irb-tnav__row:hover .irb-tnav__cnt{color:var(--text-muted);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-tnav-css")) {
  const s = document.createElement("style");
  s.id = "irb-tnav-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Node({
  node,
  depth,
  value,
  onPick
}) {
  const [open, setOpen] = React.useState(depth < 1);
  const has = node.children && node.children.length;
  const on = value === node.code;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "irb-tnav__row",
    style: {
      paddingLeft: depth * 12
    }
  }, has ? /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-tnav__tw" + (open ? " irb-tnav__tw--open" : ""),
    onClick: () => setOpen(o => !o),
    "aria-label": open ? "Свернуть" : "Развернуть"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 14
  })) : /*#__PURE__*/React.createElement("span", {
    style: {
      width: 20,
      flex: "none"
    }
  }), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-tnav__pick" + (on ? " irb-tnav__pick--on" : ""),
    onClick: () => onPick(on ? null : node),
    "aria-pressed": on
  }, node.code && /*#__PURE__*/React.createElement("code", null, node.code), /*#__PURE__*/React.createElement("span", null, node.label)), node.count != null && /*#__PURE__*/React.createElement("span", {
    className: "irb-tnav__cnt"
  }, node.count)), has && open && node.children.map(c => /*#__PURE__*/React.createElement(Node, {
    key: c.code || c.label,
    node: c,
    depth: depth + 1,
    value: value,
    onPick: onPick
  })));
}
function TreeNav({
  navigators = [],
  value,
  onPick,
  className = ""
}) {
  const [active, setActive] = React.useState(navigators[0] ? navigators[0].id : null);
  const cur = navigators.find(n => n.id === active) || navigators[0];
  if (!cur) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-tnav " + className
  }, navigators.length > 1 && /*#__PURE__*/React.createElement("div", {
    className: "irb-tnav__tabs",
    role: "tablist"
  }, navigators.map(n => /*#__PURE__*/React.createElement("button", {
    key: n.id,
    type: "button",
    role: "tab",
    "aria-selected": n.id === active,
    className: "irb-tnav__tab" + (n.id === active ? " irb-tnav__tab--on" : ""),
    onClick: () => setActive(n.id)
  }, n.label))), /*#__PURE__*/React.createElement("div", {
    className: "irb-tnav__body",
    role: "tree"
  }, cur.tree.map(n => /*#__PURE__*/React.createElement(Node, {
    key: n.code || n.label,
    node: n,
    depth: 0,
    value: value,
    onPick: onPick
  }))));
}
Object.assign(__ds_scope, { TreeNav });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/TreeNav.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Alert.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-alert{
  display:flex;gap:var(--space-3);align-items:flex-start;
  border:var(--border-width) solid;border-radius:var(--radius-md);
  padding:var(--space-3) var(--space-4);font-family:var(--font-ui);font-size:var(--text-sm);
  line-height:var(--leading-snug);color:var(--text-body);
}
.irb-alert__icon{flex:none;margin-top:1px;}
.irb-alert__body{flex:1;min-width:0;}
.irb-alert__title{font-weight:var(--weight-semibold);color:var(--text-strong);margin-bottom:2px;}
.irb-alert__close{flex:none;border:none;background:transparent;cursor:pointer;color:var(--text-muted);padding:2px;border-radius:var(--radius-sm);margin:-2px -2px 0 0;}
.irb-alert__close:hover{color:var(--text-strong);background:rgba(0,0,0,.06);}

.irb-alert--info{background:var(--info-bg);border-color:var(--accent-weak-border);}
.irb-alert--info .irb-alert__icon{color:var(--accent);}
.irb-alert--success{background:var(--success-bg);border-color:var(--status-available-border);}
.irb-alert--success .irb-alert__icon{color:var(--status-available);}
.irb-alert--warning{background:var(--warning-bg);border-color:var(--status-issued-border);}
.irb-alert--warning .irb-alert__icon{color:var(--status-issued);}
.irb-alert--error{background:var(--danger-bg);border-color:var(--danger-border);}
.irb-alert--error .irb-alert__icon{color:var(--danger-500);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-alert-css")) {
  const s = document.createElement("style");
  s.id = "irb-alert-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const ICONS = {
  info: "info",
  success: "check-circle",
  warning: "alert-triangle",
  error: "alert-octagon"
};
function Alert({
  variant = "info",
  title,
  children,
  onClose,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    className: `irb-alert irb-alert--${variant} ${className}`,
    role: variant === "error" ? "alert" : "status"
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: ICONS[variant],
    size: 18,
    className: "irb-alert__icon"
  }), /*#__PURE__*/React.createElement("div", {
    className: "irb-alert__body"
  }, title && /*#__PURE__*/React.createElement("div", {
    className: "irb-alert__title"
  }, title), children), onClose && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-alert__close",
    "aria-label": "\u0417\u0430\u043A\u0440\u044B\u0442\u044C",
    onClick: onClose
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 16
  })));
}
Object.assign(__ds_scope, { Alert });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Alert.jsx", error: String((e && e.message) || e) }); }

// components/feedback/EmptyState.jsx
try { (() => {
const CSS = `
.irb-empty{
  display:flex;flex-direction:column;align-items:center;text-align:center;
  padding:var(--space-12) var(--space-6);font-family:var(--font-ui);max-width:440px;margin:0 auto;gap:var(--space-2);
}
.irb-empty__icon{
  width:64px;height:64px;border-radius:var(--radius-round);
  display:flex;align-items:center;justify-content:center;margin-bottom:var(--space-2);
  background:var(--surface-sunken);color:var(--text-muted);
  border:var(--border-width) solid var(--border-subtle);
}
.irb-empty--error .irb-empty__icon{background:var(--danger-bg);color:var(--danger-500);border-color:var(--danger-border);}
.irb-empty--locked .irb-empty__icon{background:var(--info-bg);color:var(--accent);border-color:var(--accent-weak-border);}
.irb-empty__title{font-family:var(--font-display);font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--text-strong);line-height:var(--leading-snug);}
.irb-empty__desc{font-size:var(--text-sm);color:var(--text-muted);line-height:var(--leading-normal);}
.irb-empty__hint{display:flex;flex-direction:column;gap:6px;margin-top:var(--space-2);font-size:var(--text-sm);color:var(--text-muted);text-align:left;}
.irb-empty__hint li{margin:0;}
.irb-empty__action{margin-top:var(--space-4);display:flex;gap:var(--space-2);flex-wrap:wrap;justify-content:center;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-empty-css")) {
  const s = document.createElement("style");
  s.id = "irb-empty-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const DEFAULT_ICON = {
  neutral: "search",
  error: "alert-triangle",
  locked: "log-in"
};
function EmptyState({
  variant = "neutral",
  icon,
  title,
  description,
  hints,
  action,
  className = ""
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-empty irb-empty--${variant} ${className}`,
    role: variant === "error" ? "alert" : undefined
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-empty__icon"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon || DEFAULT_ICON[variant],
    size: 30
  })), title && /*#__PURE__*/React.createElement("div", {
    className: "irb-empty__title"
  }, title), description && /*#__PURE__*/React.createElement("p", {
    className: "irb-empty__desc"
  }, description), hints && hints.length > 0 && /*#__PURE__*/React.createElement("ul", {
    className: "irb-empty__hint"
  }, hints.map((h, i) => /*#__PURE__*/React.createElement("li", {
    key: i
  }, "\u2022 ", h))), action && /*#__PURE__*/React.createElement("div", {
    className: "irb-empty__action"
  }, action));
}
Object.assign(__ds_scope, { EmptyState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/EmptyState.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
const CSS = `
.irb-toastwrap{
  position:fixed;z-index:var(--z-toast);bottom:var(--space-6);right:var(--space-6);
  display:flex;flex-direction:column;gap:var(--space-2);max-width:380px;width:calc(100vw - 2 * var(--space-6));
  pointer-events:none;
}
.irb-toast{
  pointer-events:auto;display:flex;gap:var(--space-3);align-items:flex-start;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-left-width:3px;border-radius:var(--radius-md);box-shadow:var(--shadow-lg);
  padding:var(--space-3) var(--space-4);font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);
  animation:irb-toast-in var(--dur-slow) var(--ease-out);
}
@keyframes irb-toast-in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){.irb-toast{animation:none;}}
.irb-toast__icon{flex:none;margin-top:1px;}
.irb-toast__body{flex:1;min-width:0;}
.irb-toast__title{font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-toast__close{flex:none;border:none;background:transparent;cursor:pointer;color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);}
.irb-toast__close:hover{color:var(--text-strong);background:var(--surface-hover);}
.irb-toast--success{border-left-color:var(--status-available);}
.irb-toast--success .irb-toast__icon{color:var(--status-available);}
.irb-toast--warning{border-left-color:var(--status-issued);}
.irb-toast--warning .irb-toast__icon{color:var(--status-issued);}
.irb-toast--error{border-left-color:var(--danger-500);}
.irb-toast--error .irb-toast__icon{color:var(--danger-500);}
.irb-toast--info{border-left-color:var(--accent);}
.irb-toast--info .irb-toast__icon{color:var(--accent);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-toast-css")) {
  const s = document.createElement("style");
  s.id = "irb-toast-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const ICONS = {
  info: "info",
  success: "check-circle",
  warning: "alert-triangle",
  error: "alert-octagon"
};
function Toast({
  variant = "info",
  title,
  children,
  onClose,
  className = ""
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-toast irb-toast--${variant} ${className}`,
    role: "status"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: ICONS[variant],
    size: 18,
    className: "irb-toast__icon"
  }), /*#__PURE__*/React.createElement("div", {
    className: "irb-toast__body"
  }, title && /*#__PURE__*/React.createElement("div", {
    className: "irb-toast__title"
  }, title), children && /*#__PURE__*/React.createElement("div", null, children)), onClose && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-toast__close",
    "aria-label": "\u0417\u0430\u043A\u0440\u044B\u0442\u044C",
    onClick: onClose
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 16
  })));
}

/** Контейнер для стопки тостов (фиксированный, правый нижний угол). */
function ToastViewport({
  toasts = [],
  onDismiss
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-toastwrap",
    "aria-live": "polite",
    "aria-atomic": "false"
  }, toasts.map(t => /*#__PURE__*/React.createElement(Toast, {
    key: t.id,
    variant: t.variant,
    title: t.title,
    onClose: () => onDismiss && onDismiss(t.id)
  }, t.message)));
}
Object.assign(__ds_scope, { Toast, ToastViewport });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/forms/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:var(--space-2);
  font-family:var(--font-ui);font-weight:var(--weight-semibold);
  border:var(--border-width) solid transparent;border-radius:var(--radius-md);
  cursor:pointer;white-space:nowrap;text-decoration:none;
  transition:background-color var(--dur) var(--ease-standard),
    border-color var(--dur) var(--ease-standard),
    color var(--dur) var(--ease-standard), transform var(--dur-fast) var(--ease-standard);
  -webkit-tap-highlight-color:transparent;
}
.irb-btn:disabled,.irb-btn[aria-disabled="true"]{opacity:.5;cursor:not-allowed;}
.irb-btn:active:not(:disabled){transform:translateY(.5px);}

.irb-btn--sm{height:var(--control-h-sm);padding:0 var(--space-3);font-size:var(--text-sm);}
.irb-btn--md{height:var(--control-h-md);padding:0 var(--space-4);font-size:var(--text-base);}
.irb-btn--lg{height:var(--control-h-lg);padding:0 var(--space-6);font-size:var(--text-md);}
.irb-btn--block{width:100%;}

.irb-btn--primary{background:var(--accent);color:var(--accent-fg);}
.irb-btn--primary:hover:not(:disabled){background:var(--accent-hover);}
.irb-btn--primary:active:not(:disabled){background:var(--accent-press);}

.irb-btn--secondary{background:var(--surface-card);color:var(--text-strong);border-color:var(--border-default);}
.irb-btn--secondary:hover:not(:disabled){background:var(--surface-hover);border-color:var(--border-strong);}
.irb-btn--secondary:active:not(:disabled){background:var(--surface-active);}

.irb-btn--ghost{background:transparent;color:var(--accent);}
.irb-btn--ghost:hover:not(:disabled){background:var(--accent-weak);}
.irb-btn--ghost:active:not(:disabled){background:var(--accent-weak-hover);}

.irb-btn--danger{background:var(--danger-500);color:#fff;}
.irb-btn--danger:hover:not(:disabled){background:var(--danger-600);}

.irb-btn__spin{animation:irb-spin .7s linear infinite;}
@keyframes irb-spin{to{transform:rotate(360deg);}}
@media (prefers-reduced-motion:reduce){.irb-btn__spin{animation:none;}}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-btn-css")) {
  const s = document.createElement("style");
  s.id = "irb-btn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Button({
  children,
  variant = "primary",
  size = "md",
  iconLeft,
  iconRight,
  loading = false,
  block = false,
  disabled = false,
  type = "button",
  className = "",
  ...rest
}) {
  const isDisabled = disabled || loading;
  const iconSize = size === "sm" ? 16 : size === "lg" ? 20 : 18;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    className: `irb-btn irb-btn--${variant} irb-btn--${size}${block ? " irb-btn--block" : ""} ${className}`,
    disabled: isDisabled,
    "aria-busy": loading || undefined
  }, rest), loading ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "loader",
    size: iconSize,
    className: "irb-btn__spin"
  }) : iconLeft ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconLeft,
    size: iconSize
  }) : null, children != null && /*#__PURE__*/React.createElement("span", null, children), !loading && iconRight ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconRight,
    size: iconSize
  }) : null);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Button.jsx", error: String((e && e.message) || e) }); }

// components/catalog/HoldingsTable.jsx
try { (() => {
const CSS = `
.irb-holdings{font-family:var(--font-ui);}
.irb-holdings__tbl{width:100%;border-collapse:collapse;font-size:var(--text-sm);}
.irb-holdings__tbl th{
  text-align:left;font-weight:var(--weight-semibold);color:var(--text-muted);
  font-size:var(--text-xs);text-transform:uppercase;letter-spacing:var(--tracking-wide);
  padding:0 var(--space-3) var(--space-2);border-bottom:var(--border-width) solid var(--border-default);
}
.irb-holdings__tbl td{padding:var(--space-3);border-bottom:var(--border-width) solid var(--border-subtle);color:var(--text-body);vertical-align:middle;}
.irb-holdings__tbl tr:last-child td{border-bottom:none;}
.irb-holdings__loc{font-weight:var(--weight-medium);color:var(--text-strong);}
.irb-holdings__inv{font-family:var(--font-mono);font-size:var(--text-xs);color:var(--text-muted);}
.irb-holdings__act{text-align:right;}

/* Карточки на узких экранах */
.irb-holdings__cards{display:none;flex-direction:column;gap:var(--space-2);}
.irb-holdings__card{border:var(--border-width) solid var(--border-subtle);border-radius:var(--radius-md);
  padding:var(--space-3);display:flex;flex-direction:column;gap:var(--space-2);background:var(--surface-card);}
.irb-holdings__crow{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);}
.irb-holdings__clbl{font-size:var(--text-xs);color:var(--text-subtle);}

@media (max-width:560px){
  .irb-holdings__tbl{display:none;}
  .irb-holdings__cards{display:flex;}
}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-holdings-css")) {
  const s = document.createElement("style");
  s.id = "irb-holdings-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function HoldingsTable({
  holdings = [],
  onOrder,
  className = ""
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-holdings ${className}`
  }, /*#__PURE__*/React.createElement("table", {
    className: "irb-holdings__tbl"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null, "\u041C\u0435\u0441\u0442\u043E \u0445\u0440\u0430\u043D\u0435\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("th", null, "\u0418\u043D\u0432\u0435\u043D\u0442\u0430\u0440\u043D\u044B\u0439 \u2116"), /*#__PURE__*/React.createElement("th", null, "\u0421\u0442\u0430\u0442\u0443\u0441"), onOrder && /*#__PURE__*/React.createElement("th", {
    className: "irb-holdings__act"
  }))), /*#__PURE__*/React.createElement("tbody", null, holdings.map((h, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: "irb-holdings__loc"
  }, h.location), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("span", {
    className: "irb-holdings__inv"
  }, h.inventory)), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: h.status,
    size: "sm"
  })), onOrder && /*#__PURE__*/React.createElement("td", {
    className: "irb-holdings__act"
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "sm",
    variant: h.status === "available" ? "secondary" : "ghost",
    disabled: h.status !== "available",
    onClick: () => onOrder(h, i)
  }, h.status === "available" ? "Заказать" : "Недоступен")))))), /*#__PURE__*/React.createElement("div", {
    className: "irb-holdings__cards"
  }, holdings.map((h, i) => /*#__PURE__*/React.createElement("div", {
    className: "irb-holdings__card",
    key: i
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-holdings__crow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-holdings__loc"
  }, h.location), /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: h.status,
    size: "sm"
  })), /*#__PURE__*/React.createElement("div", {
    className: "irb-holdings__crow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-holdings__clbl"
  }, "\u0418\u043D\u0432. \u2116"), /*#__PURE__*/React.createElement("span", {
    className: "irb-holdings__inv"
  }, h.inventory)), onOrder && /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "sm",
    block: true,
    variant: h.status === "available" ? "secondary" : "ghost",
    disabled: h.status !== "available",
    onClick: () => onOrder(h, i)
  }, h.status === "available" ? "Заказать" : "Недоступен")))));
}
Object.assign(__ds_scope, { HoldingsTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/HoldingsTable.jsx", error: String((e && e.message) || e) }); }

// components/catalog/SearchBar.jsx
try { (() => {
const CSS = `
.irb-searchbar{position:relative;font-family:var(--font-ui);}
.irb-searchbar__row{display:flex;gap:var(--space-2);align-items:stretch;}
.irb-searchbar__field{
  flex:1;display:flex;align-items:center;gap:var(--space-2);min-width:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);padding:0 var(--space-3);height:var(--control-h-lg);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-searchbar__field:focus-within{border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-searchbar__field .irb-sb-ico{color:var(--text-subtle);flex:none;}
.irb-searchbar__input{
  flex:1;min-width:0;border:none;outline:none;background:transparent;
  font-family:var(--font-ui);font-size:var(--text-md);color:var(--text-body);
}
.irb-searchbar__input::placeholder{color:var(--text-subtle);}
.irb-searchbar__clear{display:inline-flex;border:none;background:transparent;cursor:pointer;color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);}
.irb-searchbar__clear:hover{color:var(--text-strong);background:var(--surface-hover);}

.irb-searchbar__sugg{
  position:absolute;z-index:var(--z-overlay);top:calc(var(--control-h-lg) + 6px);left:0;right:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);box-shadow:var(--shadow-lg);overflow:hidden;padding:var(--space-1);
}
.irb-searchbar__si{display:flex;align-items:center;gap:var(--space-2);width:100%;padding:var(--space-2) var(--space-3);
  border:none;background:transparent;cursor:pointer;text-align:left;color:var(--text-body);font-size:var(--text-sm);border-radius:var(--radius-sm);}
.irb-searchbar__si:hover,.irb-searchbar__si[data-active="true"]{background:var(--surface-hover);}
.irb-searchbar__si .irb-sb-sico{color:var(--text-subtle);flex:none;}
.irb-searchbar__si b{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-searchbar__sc{margin-left:auto;color:var(--text-subtle);font-size:var(--text-xs);font-variant-numeric:tabular-nums;}
.irb-searchbar__foot{display:flex;justify-content:flex-end;margin-top:var(--space-2);}
.irb-searchbar__adv{display:inline-flex;align-items:center;gap:6px;background:none;border:none;cursor:pointer;
  color:var(--text-link);font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);}
.irb-searchbar__adv:hover{text-decoration:underline;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-searchbar-css")) {
  const s = document.createElement("style");
  s.id = "irb-searchbar-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function SearchBar({
  value = "",
  onChange,
  onSearch,
  suggestions = [],
  onPickSuggestion,
  placeholder = "Введите запрос…",
  onAdvanced,
  onReset,
  buttonLabel = "Найти",
  className = ""
}) {
  const [focused, setFocused] = React.useState(false);
  const [active, setActive] = React.useState(-1);
  const wrapRef = React.useRef(null);
  const showSugg = focused && value.trim().length > 0 && suggestions.length > 0;
  React.useEffect(() => {
    const onDoc = e => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setFocused(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  const pick = s => {
    onPickSuggestion ? onPickSuggestion(s) : onChange && onChange(s.term || s);
    setFocused(false);
  };
  const onKeyDown = e => {
    if (!showSugg) {
      if (e.key === "Enter") onSearch && onSearch(value);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive(a => Math.min(a + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(a => Math.max(a - 1, -1));
    } else if (e.key === "Enter") {
      if (active >= 0) {
        e.preventDefault();
        pick(suggestions[active]);
      } else onSearch && onSearch(value);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-searchbar ${className}`,
    ref: wrapRef
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-searchbar__row"
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-searchbar__field",
    role: "search"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "search",
    size: 20,
    className: "irb-sb-ico"
  }), /*#__PURE__*/React.createElement("input", {
    className: "irb-searchbar__input",
    value: value,
    placeholder: placeholder,
    "aria-label": "\u041F\u043E\u0438\u0441\u043A\u043E\u0432\u044B\u0439 \u0437\u0430\u043F\u0440\u043E\u0441",
    autoComplete: "off",
    onChange: e => {
      onChange && onChange(e.target.value);
      setActive(-1);
    },
    onFocus: () => setFocused(true),
    onKeyDown: onKeyDown
  }), value.length > 0 && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-searchbar__clear",
    "aria-label": "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C",
    onClick: () => onChange && onChange("")
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 18
  }))), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "lg",
    iconLeft: "search",
    onClick: () => onSearch && onSearch(value)
  }, buttonLabel), onReset && /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "lg",
    variant: "secondary",
    iconLeft: "rotate-ccw",
    onClick: onReset
  }, "\u0421\u0431\u0440\u043E\u0441")), onAdvanced && /*#__PURE__*/React.createElement("div", {
    className: "irb-searchbar__foot"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-searchbar__adv",
    onClick: onAdvanced
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "sliders",
    size: 15
  }), " \u0420\u0430\u0441\u0448\u0438\u0440\u0435\u043D\u043D\u044B\u0439 \u043F\u043E\u0438\u0441\u043A")), showSugg && /*#__PURE__*/React.createElement("div", {
    className: "irb-searchbar__sugg",
    role: "listbox",
    "aria-label": "\u041F\u043E\u0434\u0441\u043A\u0430\u0437\u043A\u0438 \u0441\u043B\u043E\u0432\u0430\u0440\u044F"
  }, suggestions.map((s, i) => {
    const term = s.term || s;
    return /*#__PURE__*/React.createElement("button", {
      key: term + i,
      type: "button",
      role: "option",
      "aria-selected": i === active,
      "data-active": i === active,
      className: "irb-searchbar__si",
      onMouseEnter: () => setActive(i),
      onClick: () => pick(s)
    }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: "search",
      size: 15,
      className: "irb-sb-sico"
    }), /*#__PURE__*/React.createElement("span", null, term), s.count != null && /*#__PURE__*/React.createElement("span", {
      className: "irb-searchbar__sc"
    }, s.count.toLocaleString("ru-RU")));
  })));
}
Object.assign(__ds_scope, { SearchBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/SearchBar.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-check{display:inline-flex;align-items:flex-start;gap:var(--space-2);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);line-height:var(--leading-snug);}
.irb-check--disabled{opacity:.5;cursor:not-allowed;}
.irb-check__box{
  flex:none;width:18px;height:18px;margin-top:1px;border-radius:var(--radius-xs);
  border:var(--border-width-strong) solid var(--border-strong);background:var(--surface-card);
  display:inline-flex;align-items:center;justify-content:center;color:#fff;
  transition:background-color var(--dur-fast) var(--ease-standard), border-color var(--dur-fast) var(--ease-standard);
}
.irb-check input{position:absolute;opacity:0;width:1px;height:1px;}
.irb-check input:checked + .irb-check__box,
.irb-check input:indeterminate + .irb-check__box{background:var(--accent);border-color:var(--accent);}
.irb-check input:focus-visible + .irb-check__box{box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-check__mark{opacity:0;}
.irb-check input:checked + .irb-check__box .irb-check__mark{opacity:1;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-check-css")) {
  const s = document.createElement("style");
  s.id = "irb-check-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Checkbox({
  label,
  checked,
  indeterminate = false,
  disabled = false,
  className = "",
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return /*#__PURE__*/React.createElement("label", {
    className: `irb-check${disabled ? " irb-check--disabled" : ""} ${className}`
  }, /*#__PURE__*/React.createElement("input", _extends({
    ref: ref,
    type: "checkbox",
    checked: checked,
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "irb-check__box",
    "aria-hidden": "true"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: indeterminate ? "minus" : "check",
    size: 13,
    strokeWidth: 2.6,
    className: "irb-check__mark",
    style: indeterminate ? {
      opacity: 1
    } : undefined
  })), label != null && /*#__PURE__*/React.createElement("span", null, label));
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/catalog/DatabaseSelector.jsx
try { (() => {
/* Иерархический мультиселектор баз (§1.1 ТЗ): одно окно «Электронный
   каталог и Базы данных», раскрываемые группы (ЭК, Базы Либретто),
   чекбоксы, «Выбрать все» / «Снять всё», БЕЗ галочек по умолчанию. */

const CSS = `
.irb-dbsel{position:relative;font-family:var(--font-ui);}
.irb-dbsel__btn{
  display:flex;align-items:center;gap:var(--space-3);width:100%;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);padding:var(--space-2) var(--space-3);cursor:pointer;text-align:left;
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-dbsel__btn:hover{border-color:var(--border-strong);}
.irb-dbsel__btn:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-dbsel__mark{
  flex:none;width:38px;height:38px;border-radius:var(--radius-sm);
  display:flex;align-items:center;justify-content:center;
  background:var(--accent-weak);color:var(--accent);border:var(--border-width) solid var(--accent-weak-border);
}
.irb-dbsel__txt{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px;}
.irb-dbsel__eyebrow{display:block;font-size:var(--text-2xs);text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);font-weight:var(--weight-semibold);}
.irb-dbsel__name{font-size:var(--text-md);font-weight:var(--weight-semibold);color:var(--text-strong);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-dbsel__name--empty{color:var(--text-muted);font-weight:var(--weight-medium);}
.irb-dbsel__chev{color:var(--text-muted);flex:none;transition:transform var(--dur) var(--ease-standard);}
.irb-dbsel--open .irb-dbsel__chev{transform:rotate(180deg);}
.irb-dbsel__count{flex:none;display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 6px;
  border-radius:var(--radius-pill);background:var(--accent);color:var(--accent-fg);font-size:var(--text-2xs);font-weight:var(--weight-bold);}

.irb-dbsel__menu{
  position:absolute;z-index:var(--z-overlay);top:calc(100% + 6px);left:0;right:0;
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-lg);
  max-height:440px;display:flex;flex-direction:column;overflow:hidden;min-width:340px;
}
.irb-dbsel__head{padding:var(--space-3) var(--space-4);border-bottom:var(--border-width) solid var(--border-subtle);}
.irb-dbsel__title{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);}
.irb-dbsel__tools{display:flex;align-items:center;gap:var(--space-3);margin-top:6px;}
.irb-dbsel__link{background:none;border:none;padding:0;cursor:pointer;color:var(--text-link);
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);}
.irb-dbsel__link:hover{text-decoration:underline;}
.irb-dbsel__link:disabled{color:var(--text-subtle);cursor:default;text-decoration:none;}
.irb-dbsel__sel{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);}
.irb-dbsel__list{overflow:auto;padding:var(--space-2);}

.irb-dbsel__grp{margin:2px 0;}
.irb-dbsel__grphead{display:flex;align-items:center;gap:var(--space-2);width:100%;
  padding:var(--space-2) var(--space-2);border:none;background:var(--surface-sunken);border-radius:var(--radius-sm);cursor:default;}
.irb-dbsel__exp{flex:none;display:flex;align-items:center;justify-content:center;width:24px;height:24px;border:none;background:none;
  cursor:pointer;color:var(--text-muted);border-radius:var(--radius-xs);}
.irb-dbsel__exp:hover{background:var(--surface-hover);}
.irb-dbsel__exp svg{transition:transform var(--dur) var(--ease-standard);}
.irb-dbsel__exp--open svg{transform:rotate(90deg);}
.irb-dbsel__grpname{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);}
.irb-dbsel__grpcount{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);}
.irb-dbsel__children{padding:2px 0 4px 28px;}

.irb-dbsel__row{
  display:flex;align-items:center;gap:var(--space-3);width:100%;
  padding:var(--space-2) var(--space-2);border:none;background:transparent;border-radius:var(--radius-sm);
  cursor:pointer;text-align:left;color:var(--text-body);
}
.irb-dbsel__row:hover{background:var(--surface-hover);}
.irb-dbsel__row .irb-check{pointer-events:none;}
.irb-dbsel__oicon{flex:none;width:30px;height:30px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;
  background:var(--surface-sunken);color:var(--text-muted);}
.irb-dbsel__row--on .irb-dbsel__oicon{background:var(--accent-weak);color:var(--accent);}
.irb-dbsel__oname{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-dbsel__odesc{font-size:var(--text-xs);color:var(--text-muted);}
.irb-dbsel__ocount{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-dbsel__stub{margin-left:6px;font-size:var(--text-2xs);color:var(--text-subtle);border:1px solid var(--border-subtle);border-radius:var(--radius-pill);padding:0 6px;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-dbsel-css")) {
  const s = document.createElement("style");
  s.id = "irb-dbsel-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const fmt = n => typeof n === "number" ? n.toLocaleString("ru-RU") : n;
function DatabaseSelector({
  databases = [],
  groups = {},
  value = [],
  onChange,
  title = "Электронный каталог и Базы данных",
  className = ""
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  const selected = new Set(value);

  // Порядок отображения: группы и одиночные базы в порядке появления.
  const order = [];
  const seen = new Set();
  databases.forEach(d => {
    if (d.group) {
      if (!seen.has(d.group)) {
        seen.add(d.group);
        order.push({
          type: "group",
          id: d.group
        });
      }
    } else {
      order.push({
        type: "db",
        db: d
      });
    }
  });
  const childrenOf = gid => databases.filter(d => d.group === gid);
  const [expanded, setExpanded] = React.useState(() => {
    const m = {};
    Object.keys(groups).forEach(g => m[g] = true);
    return m;
  });
  React.useEffect(() => {
    if (!open) return;
    const onDoc = e => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = e => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  const emit = ids => onChange && onChange(ids);
  const toggle = id => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    emit(databases.filter(d => next.has(d.id)).map(d => d.id));
  };
  const allIds = databases.map(d => d.id);
  const selectAll = () => emit(allIds.slice());
  const clearAll = () => emit([]);
  const toggleGroup = gid => {
    const kids = childrenOf(gid).map(d => d.id);
    const allOn = kids.every(id => selected.has(id));
    const next = new Set(selected);
    kids.forEach(id => allOn ? next.delete(id) : next.add(id));
    emit(databases.filter(d => next.has(d.id)).map(d => d.id));
  };
  const count = selected.size;
  const summary = count === 0 ? "Базы не выбраны" : count === 1 ? (databases.find(d => selected.has(d.id)) || {}).name : `Выбрано баз: ${count}`;
  const Row = d => {
    const on = selected.has(d.id);
    return /*#__PURE__*/React.createElement("button", {
      key: d.id,
      type: "button",
      role: "option",
      "aria-selected": on,
      className: `irb-dbsel__row${on ? " irb-dbsel__row--on" : ""}`,
      onClick: () => toggle(d.id)
    }, /*#__PURE__*/React.createElement(__ds_scope.Checkbox, {
      checked: on,
      readOnly: true,
      tabIndex: -1
    }), /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__oicon"
    }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: d.icon || "layers",
      size: 17
    })), /*#__PURE__*/React.createElement("span", {
      style: {
        minWidth: 0,
        display: "flex",
        flexDirection: "column"
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__oname"
    }, d.name, d.stub && /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__stub"
    }, "\u0434\u0435\u043C\u043E-\u0437\u0430\u0433\u043B\u0443\u0448\u043A\u0430")), d.description && /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__odesc"
    }, d.description)), d.count != null && /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__ocount"
    }, fmt(d.count)));
  };
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-dbsel${open ? " irb-dbsel--open" : ""} ${className}`,
    ref: ref
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dbsel__btn",
    "aria-haspopup": "dialog",
    "aria-expanded": open,
    onClick: () => setOpen(o => !o)
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-dbsel__mark"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "layers",
    size: 22
  })), /*#__PURE__*/React.createElement("span", {
    className: "irb-dbsel__txt"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-dbsel__eyebrow"
  }, "\u0411\u0430\u0437\u044B \u043F\u043E\u0438\u0441\u043A\u0430"), /*#__PURE__*/React.createElement("span", {
    className: `irb-dbsel__name${count === 0 ? " irb-dbsel__name--empty" : ""}`
  }, summary)), count > 1 && /*#__PURE__*/React.createElement("span", {
    className: "irb-dbsel__count"
  }, count), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 20,
    className: "irb-dbsel__chev"
  })), open && /*#__PURE__*/React.createElement("div", {
    className: "irb-dbsel__menu",
    role: "dialog",
    "aria-label": title
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dbsel__head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dbsel__title"
  }, title), /*#__PURE__*/React.createElement("div", {
    className: "irb-dbsel__tools"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dbsel__link",
    onClick: selectAll,
    disabled: count === allIds.length
  }, "\u0412\u044B\u0431\u0440\u0430\u0442\u044C \u0432\u0441\u0435"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dbsel__link",
    onClick: clearAll,
    disabled: count === 0
  }, "\u0421\u043D\u044F\u0442\u044C \u0432\u0441\u0451"), /*#__PURE__*/React.createElement("span", {
    className: "irb-dbsel__sel"
  }, count > 0 ? `выбрано: ${count}` : "ничего не выбрано"))), /*#__PURE__*/React.createElement("div", {
    className: "irb-dbsel__list"
  }, order.map(node => {
    if (node.type === "db") return Row(node.db);
    const g = groups[node.id] || {
      label: node.id
    };
    const kids = childrenOf(node.id);
    const on = kids.filter(d => selected.has(d.id)).length;
    const isOpen = expanded[node.id];
    return /*#__PURE__*/React.createElement("div", {
      className: "irb-dbsel__grp",
      key: node.id
    }, /*#__PURE__*/React.createElement("div", {
      className: "irb-dbsel__grphead"
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      className: `irb-dbsel__exp${isOpen ? " irb-dbsel__exp--open" : ""}`,
      "aria-label": isOpen ? "Свернуть группу" : "Раскрыть группу",
      "aria-expanded": isOpen,
      onClick: () => setExpanded(m => ({
        ...m,
        [node.id]: !m[node.id]
      }))
    }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: "chevron-right",
      size: 16
    })), /*#__PURE__*/React.createElement("span", {
      onClick: () => toggleGroup(node.id),
      style: {
        cursor: "pointer",
        display: "inline-flex"
      }
    }, /*#__PURE__*/React.createElement(__ds_scope.Checkbox, {
      checked: on === kids.length && kids.length > 0,
      indeterminate: on > 0 && on < kids.length,
      readOnly: true,
      tabIndex: -1
    })), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: g.icon || "layers",
      size: 16,
      style: {
        color: "var(--text-muted)"
      }
    }), /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__grpname",
      onClick: () => toggleGroup(node.id),
      style: {
        cursor: "pointer"
      }
    }, g.label), /*#__PURE__*/React.createElement("span", {
      className: "irb-dbsel__grpcount"
    }, on > 0 ? `${on} из ${kids.length}` : `${kids.length}`)), isOpen && /*#__PURE__*/React.createElement("div", {
      className: "irb-dbsel__children"
    }, kids.map(Row)));
  }))));
}
Object.assign(__ds_scope, { DatabaseSelector });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/DatabaseSelector.jsx", error: String((e && e.message) || e) }); }

// components/catalog/ResultCard.jsx
try { (() => {
const CSS = `
.irb-result{
  display:flex;gap:var(--space-3);align-items:flex-start;
  background:var(--surface-card);border:var(--border-width) solid var(--border-subtle);
  border-radius:var(--radius-lg);padding:var(--space-4);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-result:hover{border-color:var(--border-strong);box-shadow:var(--shadow-sm);}
.irb-result--marked{border-color:var(--accent-weak-border);background:var(--accent-weak);}
.irb-result__check{padding-top:2px;}
.irb-result__thumb{
  flex:none;width:56px;height:74px;border-radius:var(--radius-sm);overflow:hidden;
  background:var(--surface-sunken);border:var(--border-width) solid var(--border-subtle);
  display:flex;align-items:center;justify-content:center;color:var(--text-subtle);
}
.irb-result__thumb img{width:100%;height:100%;object-fit:cover;display:block;}
.irb-result__body{flex:1;min-width:0;}
.irb-result__type{display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs);
  text-transform:uppercase;letter-spacing:var(--tracking-caps);color:var(--text-subtle);font-weight:var(--weight-semibold);}
.irb-result__dbtag{display:inline-flex;align-items:center;gap:4px;font-size:var(--text-2xs);font-weight:var(--weight-semibold);
  color:var(--accent);background:var(--accent-weak);border:1px solid var(--accent-weak-border);
  border-radius:var(--radius-pill);padding:1px 8px;text-transform:none;letter-spacing:0;}
.irb-result__toprow{display:flex;align-items:center;gap:var(--space-2);flex-wrap:wrap;}
.irb-result__title{
  font-family:var(--font-record-title);font-size:var(--text-lg);font-weight:var(--weight-semibold);
  color:var(--text-strong);line-height:var(--leading-snug);margin:3px 0;cursor:pointer;
  background:none;border:none;padding:0;text-align:left;display:block;
}
.irb-result__title:hover{color:var(--accent-hover);text-decoration:underline;text-underline-offset:3px;}
.irb-result__meta{display:flex;flex-wrap:wrap;gap:var(--space-1) var(--space-3);
  font-size:var(--text-sm);color:var(--text-muted);align-items:center;}
.irb-result__author{color:var(--text-body);font-weight:var(--weight-medium);}
.irb-result__sep{color:var(--border-strong);}
.irb-result__extra{margin-top:var(--space-2);display:flex;flex-wrap:wrap;gap:var(--space-1) var(--space-4);
  font-size:var(--text-sm);color:var(--text-muted);}
.irb-result__extra b{color:var(--text-body);font-weight:var(--weight-medium);}
.irb-result__aside{display:flex;flex-direction:column;align-items:flex-end;gap:var(--space-2);flex:none;}
@media (max-width:560px){
  .irb-result__aside{align-items:flex-start;}
}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-result-css")) {
  const s = document.createElement("style");
  s.id = "irb-result-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function ResultCard({
  item = {},
  checked = false,
  onToggleCheck,
  onOpen,
  showCheck = true,
  showThumb = false,
  typeIcon = "book",
  dbTag,
  className = ""
}) {
  const {
    title,
    author,
    year,
    docType,
    availability = "unknown",
    fields = [],
    thumb
  } = item;
  return /*#__PURE__*/React.createElement("article", {
    className: `irb-result${checked ? " irb-result--marked" : ""} ${className}`
  }, showCheck && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__check"
  }, /*#__PURE__*/React.createElement(__ds_scope.Checkbox, {
    checked: checked,
    onChange: onToggleCheck,
    "aria-label": `Отметить: ${title}`
  })), showThumb && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__thumb"
  }, thumb ? /*#__PURE__*/React.createElement("img", {
    src: thumb,
    alt: ""
  }) : /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "image",
    size: 22
  })), /*#__PURE__*/React.createElement("div", {
    className: "irb-result__body"
  }, (docType || dbTag) && /*#__PURE__*/React.createElement("div", {
    className: "irb-result__toprow"
  }, docType && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__type"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: typeIcon,
    size: 12
  }), " ", docType), dbTag && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__dbtag",
    title: "Из базы: " + dbTag
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "layers",
    size: 11
  }), " ", dbTag)), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-result__title",
    onClick: onOpen
  }, title), /*#__PURE__*/React.createElement("div", {
    className: "irb-result__meta"
  }, author && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__author"
  }, author), author && year && /*#__PURE__*/React.createElement("span", {
    className: "irb-result__sep",
    "aria-hidden": "true"
  }, "\xB7"), year && /*#__PURE__*/React.createElement("span", null, year)), fields.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "irb-result__extra"
  }, fields.map((f, i) => /*#__PURE__*/React.createElement("span", {
    key: i
  }, f.label, ": ", /*#__PURE__*/React.createElement("b", null, f.value))))), /*#__PURE__*/React.createElement("div", {
    className: "irb-result__aside"
  }, /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: availability,
    size: "sm"
  }), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 18,
    style: {
      color: "var(--text-subtle)"
    }
  })));
}
Object.assign(__ds_scope, { ResultCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/ResultCard.jsx", error: String((e && e.message) || e) }); }

// components/forms/FilterChip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-chip{
  display:inline-flex;align-items:center;gap:var(--space-2);
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);
  height:var(--control-h-sm);padding:0 var(--space-1) 0 var(--space-3);
  border-radius:var(--radius-pill);border:var(--border-width) solid var(--accent-weak-border);
  background:var(--accent-weak);color:var(--accent-press);white-space:nowrap;
  transition:background-color var(--dur) var(--ease-standard);
}
.irb-chip--plain{background:var(--surface-sunken);border-color:var(--border-default);color:var(--text-body);}
.irb-chip__group{font-weight:var(--weight-regular);color:var(--text-muted);}
.irb-chip__remove{
  display:inline-flex;align-items:center;justify-content:center;
  width:22px;height:22px;border:none;border-radius:var(--radius-round);
  background:transparent;color:inherit;cursor:pointer;opacity:.75;
}
.irb-chip__remove:hover{opacity:1;background:rgba(0,0,0,.07);}
.irb-chip__remove:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);}

.irb-chip--toggle{cursor:pointer;padding:0 var(--space-3);background:var(--surface-card);
  border-color:var(--border-default);color:var(--text-body);}
.irb-chip--toggle:hover{border-color:var(--border-strong);background:var(--surface-hover);}
.irb-chip--toggle[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-fg);}
.irb-chip__count{font-weight:var(--weight-regular);opacity:.7;font-size:var(--text-xs);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-chip-css")) {
  const s = document.createElement("style");
  s.id = "irb-chip-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function FilterChip({
  label,
  group,
  count,
  onRemove,
  onToggle,
  pressed,
  plain = false,
  className = "",
  ...rest
}) {
  // Режим переключателя (выбор фильтра)
  if (onToggle) {
    return /*#__PURE__*/React.createElement("button", _extends({
      type: "button",
      className: `irb-chip irb-chip--toggle ${className}`,
      "aria-pressed": !!pressed,
      onClick: onToggle
    }, rest), /*#__PURE__*/React.createElement("span", null, label), count != null && /*#__PURE__*/React.createElement("span", {
      className: "irb-chip__count"
    }, count));
  }
  // Режим снимаемого чипа (активный фильтр)
  return /*#__PURE__*/React.createElement("span", _extends({
    className: `irb-chip${plain ? " irb-chip--plain" : ""} ${className}`
  }, rest), group && /*#__PURE__*/React.createElement("span", {
    className: "irb-chip__group"
  }, group, ":"), /*#__PURE__*/React.createElement("span", null, label), onRemove && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-chip__remove",
    "aria-label": `Снять фильтр: ${group ? group + " " : ""}${label}`,
    onClick: onRemove
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 14
  })));
}
Object.assign(__ds_scope, { FilterChip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/FilterChip.jsx", error: String((e && e.message) || e) }); }

// components/forms/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-iconbtn{
  display:inline-flex;align-items:center;justify-content:center;
  border:var(--border-width) solid transparent;border-radius:var(--radius-md);
  background:transparent;color:var(--text-muted);cursor:pointer;
  transition:background-color var(--dur) var(--ease-standard),
    color var(--dur) var(--ease-standard), border-color var(--dur) var(--ease-standard);
  -webkit-tap-highlight-color:transparent;
}
.irb-iconbtn:hover:not(:disabled){background:var(--surface-hover);color:var(--text-strong);}
.irb-iconbtn:active:not(:disabled){background:var(--surface-active);}
.irb-iconbtn:disabled{opacity:.45;cursor:not-allowed;}
.irb-iconbtn--sm{width:var(--control-h-sm);height:var(--control-h-sm);}
.irb-iconbtn--md{width:var(--control-h-md);height:var(--control-h-md);}
.irb-iconbtn--lg{width:var(--control-h-lg);height:var(--control-h-lg);}
.irb-iconbtn--outline{border-color:var(--border-default);background:var(--surface-card);}
.irb-iconbtn--outline:hover:not(:disabled){border-color:var(--border-strong);}
.irb-iconbtn--accent{color:var(--accent);}
.irb-iconbtn--accent:hover:not(:disabled){background:var(--accent-weak);color:var(--accent-hover);}
.irb-iconbtn--solid{background:var(--accent);color:var(--accent-fg);}
.irb-iconbtn--solid:hover:not(:disabled){background:var(--accent-hover);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-iconbtn-css")) {
  const s = document.createElement("style");
  s.id = "irb-iconbtn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function IconButton({
  icon,
  label,
  variant = "ghost",
  size = "md",
  disabled = false,
  className = "",
  ...rest
}) {
  const iconSize = size === "sm" ? 18 : size === "lg" ? 24 : 20;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: `irb-iconbtn irb-iconbtn--${variant} irb-iconbtn--${size} ${className}`,
    "aria-label": label,
    title: label,
    disabled: disabled
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: iconSize
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
const CSS = `
.irb-overlay{
  position:fixed;inset:0;z-index:var(--z-modal);
  background:rgba(28,27,25,.46);backdrop-filter:blur(1.5px);
  display:flex;align-items:flex-start;justify-content:center;
  padding:var(--space-8) var(--space-4);overflow:auto;
  animation:irb-fade var(--dur) var(--ease-standard);
}
@keyframes irb-fade{from{opacity:0;}to{opacity:1;}}
.irb-dialog{
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);width:100%;margin:auto;
  display:flex;flex-direction:column;max-height:calc(100vh - 2 * var(--space-8));
  animation:irb-pop var(--dur-slow) var(--ease-out);
}
@keyframes irb-pop{from{opacity:0;transform:translateY(10px) scale(.99);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){.irb-overlay,.irb-dialog{animation:none;}}
.irb-dialog--sm{max-width:420px;}
.irb-dialog--md{max-width:560px;}
.irb-dialog--lg{max-width:760px;}
.irb-dialog__head{
  display:flex;align-items:flex-start;gap:var(--space-3);
  padding:var(--space-5) var(--space-5) var(--space-3);
}
.irb-dialog__titles{flex:1;min-width:0;}
.irb-dialog__title{font-family:var(--font-display);font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--text-strong);line-height:var(--leading-snug);}
.irb-dialog__sub{font-size:var(--text-sm);color:var(--text-muted);margin-top:4px;}
.irb-dialog__body{padding:0 var(--space-5) var(--space-5);overflow:auto;font-family:var(--font-ui);color:var(--text-body);}
.irb-dialog__foot{
  display:flex;justify-content:flex-end;gap:var(--space-2);flex-wrap:wrap;
  padding:var(--space-4) var(--space-5);border-top:var(--border-width) solid var(--border-subtle);
}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-dialog-css")) {
  const s = document.createElement("style");
  s.id = "irb-dialog-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _did = 0;
function Dialog({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  size = "md",
  className = ""
}) {
  const id = React.useMemo(() => `irb-dlg-${++_did}`, []);
  React.useEffect(() => {
    if (!open) return;
    const onKey = e => e.key === "Escape" && onClose && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-overlay",
    onMouseDown: e => e.target === e.currentTarget && onClose && onClose()
  }, /*#__PURE__*/React.createElement("div", {
    className: `irb-dialog irb-dialog--${size} ${className}`,
    role: "dialog",
    "aria-modal": "true",
    "aria-labelledby": title ? `${id}-t` : undefined
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dialog__head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dialog__titles"
  }, title && /*#__PURE__*/React.createElement("h2", {
    className: "irb-dialog__title",
    id: `${id}-t`
  }, title), subtitle && /*#__PURE__*/React.createElement("div", {
    className: "irb-dialog__sub"
  }, subtitle)), onClose && /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "\u0417\u0430\u043A\u0440\u044B\u0442\u044C",
    onClick: onClose
  })), /*#__PURE__*/React.createElement("div", {
    className: "irb-dialog__body"
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    className: "irb-dialog__foot"
  }, footer)));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-field{display:flex;flex-direction:column;gap:var(--space-2);}
.irb-field__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-field__req{color:var(--danger-500);margin-inline-start:2px;}
.irb-field__hint{font-size:var(--text-xs);color:var(--text-muted);}
.irb-field__err{font-size:var(--text-xs);color:var(--danger-500);display:flex;align-items:center;gap:var(--space-1);}

.irb-input{
  display:flex;align-items:center;gap:var(--space-2);
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);color:var(--text-body);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-input--sm{height:var(--control-h-sm);padding:0 var(--space-3);}
.irb-input--md{height:var(--control-h-md);padding:0 var(--space-3);}
.irb-input--lg{height:var(--control-h-lg);padding:0 var(--space-4);}
.irb-input:hover{border-color:var(--border-strong);}
.irb-input:focus-within{border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-input--error{border-color:var(--danger-500);}
.irb-input--error:focus-within{box-shadow:0 0 0 var(--focus-ring-width) rgba(178,59,59,.3);}
.irb-input--disabled{background:var(--surface-sunken);opacity:.7;cursor:not-allowed;}
.irb-input__icon{color:var(--text-subtle);flex:none;}
.irb-input__el{
  flex:1;min-width:0;border:none;background:transparent;outline:none;
  font-family:var(--font-ui);font-size:var(--text-base);color:inherit;
}
.irb-input__el::placeholder{color:var(--text-subtle);}
.irb-input__clear{
  display:inline-flex;border:none;background:transparent;cursor:pointer;
  color:var(--text-subtle);padding:2px;border-radius:var(--radius-sm);flex:none;
}
.irb-input__clear:hover{color:var(--text-strong);background:var(--surface-hover);}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-input-css")) {
  const s = document.createElement("style");
  s.id = "irb-input-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _uid = 0;
function Input({
  label,
  hint,
  error,
  required = false,
  size = "md",
  iconLeft,
  onClear,
  value,
  disabled = false,
  id,
  className = "",
  ...rest
}) {
  const autoId = React.useMemo(() => id || `irb-in-${++_uid}`, [id]);
  const showClear = onClear && value != null && String(value).length > 0;
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-field ${className}`
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "irb-field__label",
    htmlFor: autoId
  }, label, required && /*#__PURE__*/React.createElement("span", {
    className: "irb-field__req",
    "aria-hidden": "true"
  }, "*")), /*#__PURE__*/React.createElement("div", {
    className: `irb-input irb-input--${size}${error ? " irb-input--error" : ""}${disabled ? " irb-input--disabled" : ""}`
  }, iconLeft && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconLeft,
    size: 18,
    className: "irb-input__icon"
  }), /*#__PURE__*/React.createElement("input", _extends({
    id: autoId,
    className: "irb-input__el",
    value: value,
    disabled: disabled,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? `${autoId}-err` : hint ? `${autoId}-hint` : undefined
  }, rest)), showClear && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-input__clear",
    "aria-label": "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C",
    onClick: onClear
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 16
  }))), error ? /*#__PURE__*/React.createElement("span", {
    className: "irb-field__err",
    id: `${autoId}-err`
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "alert-triangle",
    size: 13
  }), " ", error) : hint ? /*#__PURE__*/React.createElement("span", {
    className: "irb-field__hint",
    id: `${autoId}-hint`
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CSS = `
.irb-select{position:relative;display:flex;flex-direction:column;gap:var(--space-2);}
.irb-select__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-select__wrap{position:relative;display:flex;align-items:center;}
.irb-select__el{
  appearance:none;-webkit-appearance:none;width:100%;
  font-family:var(--font-ui);font-size:var(--text-base);color:var(--text-body);
  background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-md);cursor:pointer;
  padding:0 var(--space-8) 0 var(--space-3);
  transition:border-color var(--dur) var(--ease-standard), box-shadow var(--dur) var(--ease-standard);
}
.irb-select__el--sm{height:var(--control-h-sm);}
.irb-select__el--md{height:var(--control-h-md);}
.irb-select__el--lg{height:var(--control-h-lg);}
.irb-select__el:hover{border-color:var(--border-strong);}
.irb-select__el:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 var(--focus-ring-width) var(--focus-ring-color);}
.irb-select__el:disabled{background:var(--surface-sunken);opacity:.7;cursor:not-allowed;}
.irb-select__chev{position:absolute;right:var(--space-3);color:var(--text-subtle);pointer-events:none;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-select-css")) {
  const s = document.createElement("style");
  s.id = "irb-select-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
let _sid = 0;
function Select({
  label,
  options = [],
  size = "md",
  id,
  disabled = false,
  className = "",
  children,
  ...rest
}) {
  const autoId = React.useMemo(() => id || `irb-sel-${++_sid}`, [id]);
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-select ${className}`
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "irb-select__label",
    htmlFor: autoId
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "irb-select__wrap"
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: autoId,
    className: `irb-select__el irb-select__el--${size}`,
    disabled: disabled
  }, rest), children ? children : options.map(o => {
    const value = typeof o === "string" ? o : o.value;
    const text = typeof o === "string" ? o : o.label;
    return /*#__PURE__*/React.createElement("option", {
      key: value,
      value: value
    }, text);
  })), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 18,
    className: "irb-select__chev"
  })));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/catalog/Pagination.jsx
try { (() => {
const CSS = `
.irb-pg{display:flex;align-items:center;gap:var(--space-4);flex-wrap:wrap;font-family:var(--font-ui);}
.irb-pg__nums{display:flex;align-items:center;gap:4px;}
.irb-pg__b{
  min-width:var(--control-h-sm);height:var(--control-h-sm);padding:0 var(--space-2);
  display:inline-flex;align-items:center;justify-content:center;
  border:var(--border-width) solid transparent;border-radius:var(--radius-sm);
  background:transparent;color:var(--text-body);cursor:pointer;font-size:var(--text-sm);
  font-variant-numeric:tabular-nums;font-weight:var(--weight-medium);
  transition:background-color var(--dur) var(--ease-standard);
}
.irb-pg__b:hover:not(:disabled){background:var(--surface-hover);}
.irb-pg__b:disabled{opacity:.4;cursor:not-allowed;}
.irb-pg__b--cur{background:var(--accent);color:var(--accent-fg);}
.irb-pg__b--cur:hover{background:var(--accent);}
.irb-pg__b:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);}
.irb-pg__ell{padding:0 4px;color:var(--text-subtle);}
.irb-pg__stat{font-size:var(--text-sm);color:var(--text-muted);font-variant-numeric:tabular-nums;}
.irb-pg__stat b{color:var(--text-strong);font-weight:var(--weight-semibold);}
.irb-pg__size{display:flex;align-items:center;gap:var(--space-2);margin-left:auto;font-size:var(--text-sm);color:var(--text-muted);}
.irb-pg__size .irb-select{min-width:84px;}
.irb-pg--compact{justify-content:flex-end;}
.irb-pg--compact .irb-pg__stat{margin-right:auto;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-pg-css")) {
  const s = document.createElement("style");
  s.id = "irb-pg-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function pageList(cur, count) {
  if (count <= 7) return Array.from({
    length: count
  }, (_, i) => i + 1);
  const set = new Set([1, count, cur, cur - 1, cur + 1]);
  if (cur <= 3) [2, 3, 4].forEach(n => set.add(n));
  if (cur >= count - 2) [count - 1, count - 2, count - 3].forEach(n => set.add(n));
  const nums = [...set].filter(n => n >= 1 && n <= count).sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < nums.length; i++) {
    out.push(nums[i]);
    if (i < nums.length - 1 && nums[i + 1] - nums[i] > 1) out.push("…");
  }
  return out;
}
function Pagination({
  page = 1,
  pageCount = 1,
  onPage,
  pageSize,
  onPageSize,
  pageSizeOptions = [10, 20, 50],
  total,
  compact = false,
  className = ""
}) {
  const go = p => p >= 1 && p <= pageCount && p !== page && onPage && onPage(p);
  return /*#__PURE__*/React.createElement("nav", {
    className: `irb-pg${compact ? " irb-pg--compact" : ""} ${className}`,
    "aria-label": "\u041F\u043E\u0441\u0442\u0440\u0430\u043D\u0438\u0447\u043D\u0430\u044F \u043D\u0430\u0432\u0438\u0433\u0430\u0446\u0438\u044F"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-pg__stat"
  }, "\u0421\u0442\u0440\u0430\u043D\u0438\u0446\u0430 ", /*#__PURE__*/React.createElement("b", null, page), " \u0438\u0437 ", /*#__PURE__*/React.createElement("b", null, pageCount), total != null && /*#__PURE__*/React.createElement(React.Fragment, null, " \xB7 \u043D\u0430\u0439\u0434\u0435\u043D\u043E ", /*#__PURE__*/React.createElement("b", null, total.toLocaleString("ru-RU")))), /*#__PURE__*/React.createElement("div", {
    className: "irb-pg__nums"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-pg__b",
    onClick: () => go(1),
    disabled: page <= 1,
    "aria-label": "\u041F\u0435\u0440\u0432\u0430\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevrons-left",
    size: 18
  })), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-pg__b",
    onClick: () => go(page - 1),
    disabled: page <= 1,
    "aria-label": "\u041F\u0440\u0435\u0434\u044B\u0434\u0443\u0449\u0430\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-left",
    size: 18
  })), pageList(page, pageCount).map((p, i) => p === "…" ? /*#__PURE__*/React.createElement("span", {
    key: `e${i}`,
    className: "irb-pg__ell",
    "aria-hidden": "true"
  }, "\u2026") : /*#__PURE__*/React.createElement("button", {
    key: p,
    type: "button",
    className: `irb-pg__b${p === page ? " irb-pg__b--cur" : ""}`,
    "aria-current": p === page ? "page" : undefined,
    onClick: () => go(p)
  }, p)), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-pg__b",
    onClick: () => go(page + 1),
    disabled: page >= pageCount,
    "aria-label": "\u0421\u043B\u0435\u0434\u0443\u044E\u0449\u0430\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 18
  })), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-pg__b",
    onClick: () => go(pageCount),
    disabled: page >= pageCount,
    "aria-label": "\u041F\u043E\u0441\u043B\u0435\u0434\u043D\u044F\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevrons-right",
    size: 18
  }))), pageSize != null && onPageSize && /*#__PURE__*/React.createElement("div", {
    className: "irb-pg__size"
  }, /*#__PURE__*/React.createElement("span", null, "\u041F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0442\u044C \u043F\u043E"), /*#__PURE__*/React.createElement(__ds_scope.Select, {
    size: "sm",
    value: String(pageSize),
    onChange: e => onPageSize(Number(e.target.value)),
    options: pageSizeOptions.map(n => String(n)),
    "aria-label": "\u0420\u0430\u0437\u043C\u0435\u0440 \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u044B"
  })));
}
Object.assign(__ds_scope, { Pagination });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/catalog/Pagination.jsx", error: String((e && e.message) || e) }); }

// components/cataloging/DynamicField.jsx
try { (() => {
/* DynamicField (§6 ТЗ) — «главный» компонент каталогизации: ТИП ПОЛЯ
   определяет контрол. Управляется декларативным описанием поля из профиля
   базы (FIELD_CATALOG): тип ввода, метка, MARC-код, подполя, повторяемость,
   словарь/меню/дерево/авторитет, ФЛК. UI-only: значения наружу через onChange. */

const CSS = `
.irb-dyn{font-family:var(--font-ui);display:flex;flex-direction:column;gap:7px;}
.irb-dyn__head{display:flex;align-items:baseline;gap:8px;}
.irb-dyn__code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--accent);
  background:var(--accent-weak);border:1px solid var(--accent-weak-border);border-radius:var(--radius-xs);padding:1px 6px;flex:none;}
.irb-dyn__label{font-size:var(--text-sm);font-weight:var(--weight-semibold);color:var(--text-strong);}
.irb-dyn__req{color:var(--danger-500);margin-left:2px;}
.irb-dyn__type{margin-left:auto;font-size:var(--text-2xs);color:var(--text-subtle);display:inline-flex;align-items:center;gap:4px;}
.irb-dyn__rep{display:flex;flex-direction:column;gap:8px;}
.irb-dyn__occ{display:flex;align-items:flex-start;gap:8px;}
.irb-dyn__occ-main{flex:1;min-width:0;}
.irb-dyn__sub{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;
  background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:10px;}
.irb-dyn__sublabel{display:block;font-size:var(--text-2xs);color:var(--text-muted);margin-bottom:4px;}
.irb-dyn__subcode{font-family:var(--font-mono);color:var(--text-subtle);}
.irb-dyn__add{align-self:flex-start;display:inline-flex;align-items:center;gap:5px;background:none;border:none;cursor:pointer;
  color:var(--text-link);font-family:var(--font-ui);font-size:var(--text-xs);font-weight:var(--weight-semibold);padding:2px 0;}
.irb-dyn__err{font-size:var(--text-xs);color:var(--danger-500);display:flex;align-items:center;gap:4px;}
.irb-dyn__hint{font-size:var(--text-xs);color:var(--text-muted);}

/* да-нет — сегмент */
.irb-dyn__seg{display:inline-flex;border:1px solid var(--border-default);border-radius:var(--radius-sm);overflow:hidden;}
.irb-dyn__seg button{border:none;background:var(--surface-card);color:var(--text-muted);cursor:pointer;
  font-family:var(--font-ui);font-size:var(--text-sm);font-weight:var(--weight-medium);padding:8px 16px;}
.irb-dyn__seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-fg);}
.irb-dyn__seg button + button{border-left:1px solid var(--border-default);}

/* combobox словаря/авторитета */
.irb-dyn__cb{position:relative;}
.irb-dyn__menu{position:absolute;z-index:var(--z-overlay);top:calc(100% + 4px);left:0;right:0;max-height:230px;overflow:auto;
  background:var(--surface-card);border:1px solid var(--border-default);border-radius:var(--radius-md);box-shadow:var(--shadow-lg);padding:4px;}
.irb-dyn__opt{display:flex;align-items:center;gap:8px;width:100%;text-align:left;border:none;background:transparent;cursor:pointer;
  border-radius:var(--radius-sm);padding:7px 9px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);}
.irb-dyn__opt:hover,.irb-dyn__opt--on{background:var(--surface-hover);}
.irb-dyn__opt small{margin-left:auto;color:var(--text-subtle);font-variant-numeric:tabular-nums;}
.irb-dyn__auth{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--accent);flex:none;}

/* дерево .tre */
.irb-dyn__tree{border:1px solid var(--border-default);border-radius:var(--radius-md);background:var(--surface-card);max-height:260px;overflow:auto;padding:4px;}
.irb-dyn__node{display:flex;align-items:center;gap:4px;border-radius:var(--radius-sm);}
.irb-dyn__node:hover{background:var(--surface-hover);}
.irb-dyn__twirl{flex:none;width:22px;height:22px;display:flex;align-items:center;justify-content:center;border:none;background:none;cursor:pointer;color:var(--text-subtle);}
.irb-dyn__twirl svg{transition:transform var(--dur) var(--ease-standard);}
.irb-dyn__twirl--open svg{transform:rotate(90deg);}
.irb-dyn__pick{flex:1;text-align:left;border:none;background:none;cursor:pointer;padding:6px 4px;font-family:var(--font-ui);font-size:var(--text-sm);color:var(--text-body);display:flex;gap:8px;}
.irb-dyn__pick--on{color:var(--accent-press);font-weight:var(--weight-semibold);}
.irb-dyn__pick code{font-family:var(--font-mono);font-size:var(--text-2xs);color:var(--text-subtle);}
.irb-dyn__chosen{display:inline-flex;align-items:center;gap:6px;margin-top:6px;font-size:var(--text-xs);color:var(--accent-press);background:var(--accent-weak);border:1px solid var(--accent-weak-border);border-radius:var(--radius-pill);padding:3px 10px;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-dyn-css")) {
  const s = document.createElement("style");
  s.id = "irb-dyn-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const TYPE_META = {
  text: {
    label: "текст",
    icon: "type"
  },
  menu: {
    label: "меню (.mnu)",
    icon: "list"
  },
  dict: {
    label: "словарь",
    icon: "search"
  },
  tree: {
    label: "справочник (.tre)",
    icon: "list-tree"
  },
  bool: {
    label: "да / нет",
    icon: "check-circle"
  },
  authority: {
    label: "авторитет",
    icon: "shield"
  },
  date: {
    label: "дата",
    icon: "calendar"
  }
};
function Combobox({
  value,
  onChange,
  options = [],
  placeholder,
  authority
}) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = e => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  const text = q || value || "";
  const filtered = options.filter(o => (o.term || o.label || o).toLowerCase().startsWith((q || "").toLowerCase()));
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__cb",
    ref: ref
  }, /*#__PURE__*/React.createElement(__ds_scope.Input, {
    size: "sm",
    iconLeft: authority ? "shield" : "search",
    value: text,
    placeholder: placeholder,
    onChange: e => {
      setQ(e.target.value);
      onChange(e.target.value);
      setOpen(true);
    },
    onFocus: () => setOpen(true),
    onClear: text ? () => {
      setQ("");
      onChange("");
    } : undefined
  }), open && filtered.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__menu",
    role: "listbox"
  }, filtered.map(o => {
    const term = o.term || o.label || o;
    return /*#__PURE__*/React.createElement("button", {
      key: term,
      type: "button",
      className: "irb-dyn__opt" + (term === value ? " irb-dyn__opt--on" : ""),
      onClick: () => {
        onChange(term);
        setQ("");
        setOpen(false);
      }
    }, authority && o.code && /*#__PURE__*/React.createElement("span", {
      className: "irb-dyn__auth"
    }, o.code), term, o.count != null && /*#__PURE__*/React.createElement("small", null, o.count));
  })));
}
function TreeNode({
  node,
  depth,
  value,
  onPick
}) {
  const [open, setOpen] = React.useState(depth < 1);
  const has = node.children && node.children.length;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__node",
    style: {
      paddingLeft: depth * 14
    }
  }, has ? /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dyn__twirl" + (open ? " irb-dyn__twirl--open" : ""),
    onClick: () => setOpen(o => !o),
    "aria-label": open ? "Свернуть" : "Развернуть"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 15
  })) : /*#__PURE__*/React.createElement("span", {
    style: {
      width: 22,
      flex: "none"
    }
  }), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dyn__pick" + (value === node.code ? " irb-dyn__pick--on" : ""),
    onClick: () => onPick(node)
  }, node.code && /*#__PURE__*/React.createElement("code", null, node.code), " ", node.label)), has && open && node.children.map(c => /*#__PURE__*/React.createElement(TreeNode, {
    key: c.code || c.label,
    node: c,
    depth: depth + 1,
    value: value,
    onPick: onPick
  })));
}
function Control({
  field,
  value,
  onChange
}) {
  switch (field.type) {
    case "menu":
      return /*#__PURE__*/React.createElement(__ds_scope.Select, {
        size: "sm",
        value: value || "",
        onChange: e => onChange(e.target.value),
        options: [{
          value: "",
          label: field.placeholder || "— выберите —"
        }].concat((field.options || []).map(o => typeof o === "string" ? {
          value: o,
          label: o
        } : o))
      });
    case "bool":
      return /*#__PURE__*/React.createElement("div", {
        className: "irb-dyn__seg",
        role: "group",
        "aria-label": field.label
      }, (field.options || ["Да", "Нет"]).map(o => {
        const v = typeof o === "string" ? o : o.value;
        return /*#__PURE__*/React.createElement("button", {
          key: v,
          type: "button",
          "aria-pressed": value === v,
          onClick: () => onChange(value === v ? "" : v)
        }, typeof o === "string" ? o : o.label);
      }));
    case "date":
      return /*#__PURE__*/React.createElement(__ds_scope.Input, {
        size: "sm",
        iconLeft: "calendar",
        value: value || "",
        placeholder: field.placeholder || "ГГГГ или ГГГГ-ММ-ДД",
        onChange: e => onChange(e.target.value)
      });
    case "dict":
      return /*#__PURE__*/React.createElement(Combobox, {
        value: value,
        onChange: onChange,
        options: field.dictionary || field.options || [],
        placeholder: field.placeholder || "ввод по словарю (префикс)…"
      });
    case "authority":
      return /*#__PURE__*/React.createElement(Combobox, {
        value: value,
        onChange: onChange,
        options: field.authority || field.options || [],
        placeholder: field.placeholder || "поиск в авторитетном файле…",
        authority: true
      });
    case "tree":
      return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
        className: "irb-dyn__tree",
        role: "tree"
      }, (field.tree || []).map(n => /*#__PURE__*/React.createElement(TreeNode, {
        key: n.code || n.label,
        node: n,
        depth: 0,
        value: value,
        onPick: node => onChange(node.code)
      }))), value && /*#__PURE__*/React.createElement("span", {
        className: "irb-dyn__chosen"
      }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
        name: "check",
        size: 13
      }), " \u0432\u044B\u0431\u0440\u0430\u043D\u043E: ", value));
    default:
      return /*#__PURE__*/React.createElement(__ds_scope.Input, {
        size: "sm",
        value: value || "",
        placeholder: field.placeholder || "значение",
        onChange: e => onChange(e.target.value)
      });
  }
}
function DynamicField({
  field,
  value,
  onChange,
  error,
  className = ""
}) {
  const meta = TYPE_META[field.type] || TYPE_META.text;
  const repeatable = !!field.repeatable;
  const hasSub = field.subfields && field.subfields.length;

  // Значение: повторяемое → массив «вхождений»; вхождение с подполями → объект.
  const occurrences = repeatable ? Array.isArray(value) ? value : [hasSub ? {} : ""] : [value];
  const setOcc = (i, v) => {
    if (!repeatable) return onChange(v);
    const next = occurrences.slice();
    next[i] = v;
    onChange(next);
  };
  const addOcc = () => onChange(occurrences.concat([hasSub ? {} : ""]));
  const delOcc = i => onChange(occurrences.filter((_, j) => j !== i));
  const renderOcc = (occ, i) => /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__occ",
    key: i
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__occ-main"
  }, hasSub ? /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__sub"
  }, field.subfields.map(sf => /*#__PURE__*/React.createElement("div", {
    key: sf.code
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__sublabel"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__subcode"
  }, "^", sf.code), " ", sf.label), /*#__PURE__*/React.createElement(Control, {
    field: sf,
    value: (occ || {})[sf.code] || "",
    onChange: v => setOcc(i, {
      ...(occ || {}),
      [sf.code]: v
    })
  })))) : /*#__PURE__*/React.createElement(Control, {
    field: field,
    value: occ,
    onChange: v => setOcc(i, v)
  })), repeatable && occurrences.length > 1 && /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "trash",
    label: "\u0423\u0434\u0430\u043B\u0438\u0442\u044C \u043F\u043E\u0432\u0442\u043E\u0440\u0435\u043D\u0438\u0435",
    size: "sm",
    variant: "ghost",
    onClick: () => delOcc(i)
  }));
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn " + className
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__head"
  }, field.code && /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__code"
  }, field.code), /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__label"
  }, field.label, field.required && /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__req",
    "aria-hidden": "true"
  }, "*")), /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__type"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: meta.icon,
    size: 12
  }), " ", meta.label, repeatable ? " · повтор." : "")), /*#__PURE__*/React.createElement("div", {
    className: "irb-dyn__rep"
  }, occurrences.map(renderOcc)), repeatable && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "irb-dyn__add",
    onClick: addOcc
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "plus",
    size: 13
  }), " \u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C \u043F\u043E\u0432\u0442\u043E\u0440\u0435\u043D\u0438\u0435 \u043F\u043E\u043B\u044F"), error ? /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__err"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "alert-triangle",
    size: 13
  }), " ", error) : field.hint ? /*#__PURE__*/React.createElement("span", {
    className: "irb-dyn__hint"
  }, field.hint) : null);
}
Object.assign(__ds_scope, { DynamicField });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cataloging/DynamicField.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
const CSS = `
.irb-tabs{display:flex;gap:var(--space-1);border-bottom:var(--border-width) solid var(--border-subtle);font-family:var(--font-ui);}
.irb-tabs--pill{border-bottom:none;background:var(--surface-sunken);padding:4px;border-radius:var(--radius-md);gap:2px;width:max-content;}
.irb-tab{
  display:inline-flex;align-items:center;gap:var(--space-2);
  background:none;border:none;cursor:pointer;color:var(--text-muted);
  font-size:var(--text-sm);font-weight:var(--weight-semibold);
  padding:var(--space-3) var(--space-3);position:relative;
  transition:color var(--dur) var(--ease-standard);
}
.irb-tab:hover{color:var(--text-strong);}
.irb-tab[aria-selected="true"]{color:var(--accent);}
.irb-tab[aria-selected="true"]::after{
  content:"";position:absolute;left:var(--space-3);right:var(--space-3);bottom:-1px;height:2px;
  background:var(--accent);border-radius:2px;
}
.irb-tab:focus-visible{outline:var(--focus-ring-width) solid var(--focus-ring-color);border-radius:var(--radius-sm);}
.irb-tab__count{font-size:var(--text-xs);font-weight:var(--weight-medium);color:var(--text-subtle);
  background:var(--surface-sunken);border-radius:var(--radius-pill);padding:1px 7px;font-variant-numeric:tabular-nums;}
.irb-tab[aria-selected="true"] .irb-tab__count{background:var(--accent-weak);color:var(--accent);}

.irb-tabs--pill .irb-tab{border-radius:var(--radius-sm);padding:var(--space-2) var(--space-4);}
.irb-tabs--pill .irb-tab[aria-selected="true"]{background:var(--surface-card);color:var(--text-strong);box-shadow:var(--shadow-xs);}
.irb-tabs--pill .irb-tab[aria-selected="true"]::after{display:none;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-tabs-css")) {
  const s = document.createElement("style");
  s.id = "irb-tabs-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
function Tabs({
  tabs = [],
  value,
  onChange,
  variant = "underline",
  className = ""
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: `irb-tabs irb-tabs--${variant} ${className}`,
    role: "tablist"
  }, tabs.map(t => {
    const id = typeof t === "string" ? t : t.id;
    const label = typeof t === "string" ? t : t.label;
    const selected = id === value;
    return /*#__PURE__*/React.createElement("button", {
      key: id,
      type: "button",
      role: "tab",
      "aria-selected": selected,
      className: "irb-tab",
      onClick: () => onChange && onChange(id)
    }, t.icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: t.icon,
      size: 16
    }), label, t.count != null && /*#__PURE__*/React.createElement("span", {
      className: "irb-tab__count"
    }, t.count));
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/viewer/FileViewer.jsx
try { (() => {
/* Просмотрщик файла/изображения — VIEW-ONLY (§1.7, §10):
   - НЕТ кнопки скачивания и путей к файлу;
   - контекстное меню по правой кнопке ЗАБЛОКИРОВАНО;
   - перетаскивание изображения отключено;
   - при requiresAuth и отсутствии входа — состояние «нет прав»;
   - для PDF — подпись «документ pdf-формата».
   Приоритет поля 955 над 951 решает вызывающая сторона (выбор файла). */

const CSS = `
.irb-fv__back{position:fixed;inset:0;z-index:var(--z-modal);background:rgba(28,27,25,.46);
  backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:var(--space-5);}
.irb-fv{background:var(--surface-card);border:var(--border-width) solid var(--border-default);
  border-radius:var(--radius-xl);box-shadow:var(--shadow-lg);width:min(880px,100%);max-height:92vh;
  display:flex;flex-direction:column;overflow:hidden;font-family:var(--font-ui);}
.irb-fv__head{display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) var(--space-4);
  border-bottom:var(--border-width) solid var(--border-subtle);}
.irb-fv__ic{flex:none;width:34px;height:34px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;
  background:var(--accent-weak);color:var(--accent);}
.irb-fv__t{min-width:0;flex:1;}
.irb-fv__title{font-size:var(--text-sm);font-weight:var(--weight-bold);color:var(--text-strong);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.irb-fv__sub{font-size:var(--text-xs);color:var(--text-muted);}
.irb-fv__viewonly{display:inline-flex;align-items:center;gap:5px;font-size:var(--text-2xs);font-weight:var(--weight-semibold);
  color:var(--text-muted);background:var(--surface-sunken);border:1px solid var(--border-subtle);border-radius:var(--radius-pill);padding:2px 9px;}
.irb-fv__stage{flex:1;overflow:auto;background:var(--surface-sunken);display:flex;align-items:center;justify-content:center;
  padding:var(--space-6);min-height:280px;}
.irb-fv__page{background:#fff;border:var(--border-width) solid var(--border-subtle);box-shadow:var(--shadow-md);
  width:min(460px,100%);aspect-ratio:1 / 1.414;border-radius:var(--radius-xs);
  display:flex;flex-direction:column;padding:42px 40px;color:#2b2926;}
.irb-fv__page h4{font-family:var(--font-record-title);font-size:18px;margin:0 0 14px;}
.irb-fv__lines{display:flex;flex-direction:column;gap:9px;}
.irb-fv__lines i{display:block;height:8px;border-radius:3px;background:#e7e2d8;}
.irb-fv__img{width:100%;height:100%;display:flex;align-items:center;justify-content:center;border-radius:var(--radius-sm);}
.irb-fv__foot{display:flex;align-items:center;gap:var(--space-3);padding:var(--space-3) var(--space-4);
  border-top:var(--border-width) solid var(--border-subtle);}
.irb-fv__pg{font-size:var(--text-sm);color:var(--text-muted);font-variant-numeric:tabular-nums;}
.irb-fv__note{margin-left:auto;font-size:var(--text-xs);color:var(--text-subtle);display:inline-flex;align-items:center;gap:6px;}
`;
if (typeof document !== "undefined" && !document.getElementById("irb-fv-css")) {
  const s = document.createElement("style");
  s.id = "irb-fv-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}
const KIND_LABEL = {
  pdf: "документ pdf-формата",
  image: "изображение",
  djvu: "документ djvu-формата"
};

// Демо-абзацы «страницы» с подсветкой искомых терминов (§4, §10).
const PAGE_TEXT = ["Пьеса написана в форме комедии в четырёх действиях. Действие происходит в усадьбе на берегу озера.", "Чайка как образ проходит через всю драму, становясь символом несбывшихся надежд героев.", "Премьера на сцене Александринского театра не имела успеха, однако постановка Художественного театра принесла признание.", "Композиция строится на контрасте бытовых сцен и внутренних монологов действующих лиц."];
function highlightText(text, terms) {
  if (!terms || !terms.length) return text;
  const safe = terms.filter(Boolean).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).filter(t => t.length > 1);
  if (!safe.length) return text;
  const re = new RegExp("(" + safe.join("|") + ")", "gi");
  const parts = String(text).split(re);
  return parts.map((p, i) => re.test(p) ? /*#__PURE__*/React.createElement("mark", {
    key: i,
    style: {
      background: "var(--status-issued-bg)",
      color: "inherit",
      borderRadius: 2,
      padding: "0 1px"
    }
  }, p) : p);
}
function FileViewer({
  open,
  file,
  title,
  canView = true,
  terms,
  relevantPages,
  onClose
}) {
  const [page, setPage] = React.useState(1);
  React.useEffect(() => {
    if (open) setPage(relevantPages && relevantPages.length ? relevantPages[0] : 1);
  }, [open, file]);
  React.useEffect(() => {
    if (!open) return;
    const onKey = e => e.key === "Escape" && onClose && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open || !file) return null;
  const kind = file.kind || "pdf";
  const pages = file.pages || 1;
  const denyContext = e => {
    e.preventDefault();
    return false;
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__back",
    role: "presentation",
    onMouseDown: e => e.target === e.currentTarget && onClose && onClose()
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-fv",
    role: "dialog",
    "aria-modal": "true",
    "aria-label": title || file.label,
    onContextMenu: denyContext
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "irb-fv__ic"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: kind === "image" ? "image" : "file-text",
    size: 19
  })), /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__t"
  }, /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__title"
  }, file.label || title), /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__sub"
  }, KIND_LABEL[kind] || kind)), /*#__PURE__*/React.createElement("span", {
    className: "irb-fv__viewonly"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "eye",
    size: 13
  }), " \u0442\u043E\u043B\u044C\u043A\u043E \u043F\u0440\u043E\u0441\u043C\u043E\u0442\u0440"), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "\u0417\u0430\u043A\u0440\u044B\u0442\u044C",
    variant: "ghost",
    onClick: onClose
  })), !canView ? /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__stage"
  }, /*#__PURE__*/React.createElement(__ds_scope.EmptyState, {
    variant: "locked",
    icon: "log-in",
    title: "\u041D\u0443\u0436\u0435\u043D \u0432\u0445\u043E\u0434 \u043F\u043E \u0431\u0438\u043B\u0435\u0442\u0443",
    description: "\u041F\u043E\u043B\u043D\u044B\u0439 \u0442\u0435\u043A\u0441\u0442 \u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D \u0432 \u0447\u0438\u0442\u0430\u043B\u044C\u043D\u043E\u043C \u0437\u0430\u043B\u0435 \u0438\u043B\u0438 \u043F\u043E\u0441\u043B\u0435 \u0432\u0445\u043E\u0434\u0430 \u043F\u043E \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044C\u0441\u043A\u043E\u043C\u0443 \u0431\u0438\u043B\u0435\u0442\u0443."
  })) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__stage",
    onContextMenu: denyContext
  }, kind === "image" ? /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__img",
    onContextMenu: denyContext,
    onDragStart: denyContext,
    style: {
      background: "hsl(" + (file.tint || 30) + " 32% 86%)",
      aspectRatio: "4 / 3",
      width: "min(560px,100%)",
      userSelect: "none"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "image",
    size: 52,
    style: {
      color: "hsl(" + (file.tint || 30) + " 38% 42%)"
    }
  })) : /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__page",
    onContextMenu: denyContext,
    style: {
      userSelect: "none"
    }
  }, /*#__PURE__*/React.createElement("h4", null, file.label, pages > 1 ? " · с. " + page : ""), terms && terms.length ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 11,
      fontSize: 14,
      lineHeight: 1.65,
      color: "#2b2926"
    }
  }, PAGE_TEXT.map((t, i) => /*#__PURE__*/React.createElement("p", {
    key: i,
    style: {
      margin: 0
    }
  }, highlightText(t, terms)))) : /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__lines"
  }, Array.from({
    length: 11
  }).map((_, i) => /*#__PURE__*/React.createElement("i", {
    key: i,
    style: {
      width: [92, 100, 86, 96, 70, 100, 90, 60, 98, 82, 44][i] + "%"
    }
  }))))), /*#__PURE__*/React.createElement("div", {
    className: "irb-fv__foot"
  }, relevantPages && relevantPages.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      marginRight: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "var(--text-2xs)",
      color: "var(--text-subtle)"
    }
  }, "\u0420\u0435\u043B\u0435\u0432\u0430\u043D\u0442\u043D\u044B\u0435 \u0441.:"), relevantPages.map(p => /*#__PURE__*/React.createElement("button", {
    key: p,
    type: "button",
    onClick: () => setPage(p),
    style: {
      border: "1px solid " + (p === page ? "var(--accent)" : "var(--border-default)"),
      cursor: "pointer",
      background: p === page ? "var(--accent-weak)" : "var(--surface-card)",
      color: p === page ? "var(--accent-press)" : "var(--text-muted)",
      borderRadius: "var(--radius-pill)",
      padding: "1px 9px",
      fontFamily: "var(--font-mono)",
      fontSize: "var(--text-2xs)",
      fontWeight: 600
    }
  }, p))), kind !== "image" && pages > 1 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "chevron-left",
    label: "\u041F\u0440\u0435\u0434\u044B\u0434\u0443\u0449\u0430\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430",
    size: "sm",
    variant: "outline",
    disabled: page <= 1,
    onClick: () => setPage(p => Math.max(1, p - 1))
  }), /*#__PURE__*/React.createElement("span", {
    className: "irb-fv__pg"
  }, "\u0421\u0442\u0440. ", page, " \u0438\u0437 ", pages), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "chevron-right",
    label: "\u0421\u043B\u0435\u0434\u0443\u044E\u0449\u0430\u044F \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0430",
    size: "sm",
    variant: "outline",
    disabled: page >= pages,
    onClick: () => setPage(p => Math.min(pages, p + 1))
  })), /*#__PURE__*/React.createElement("span", {
    className: "irb-fv__note"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "eye-off",
    size: 13
  }), " \u0421\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435 \u0438 \u043A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435 \u043E\u0442\u043A\u043B\u044E\u0447\u0435\u043D\u044B")))));
}
Object.assign(__ds_scope, { FileViewer });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/viewer/FileViewer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/AccountScreens.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    Input,
    Tabs,
    StatusBadge,
    Badge,
    EmptyState,
    Alert
  } = NS;
  const TONE = {
    available: "var(--status-available-strong)",
    issued: "var(--status-issued-strong)",
    danger: "var(--danger-500)",
    neutral: "var(--text-muted)"
  };
  function LoginScreen({
    onLogin,
    pending
  }) {
    const [lastName, setLastName] = React.useState("");
    const [ticket, setTicket] = React.useState("");
    const [err, setErr] = React.useState("");
    const submit = () => {
      const v = ticket.trim();
      if (!/^\d{4,}$/.test(v)) {
        setErr("Введите номер билета (только цифры).");
        return;
      }
      setErr("");
      onLogin(v, lastName.trim());
    };
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 420,
        margin: "0 auto",
        padding: "var(--space-16) var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "center",
        marginBottom: "var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: "inline-flex",
        width: 56,
        height: 56,
        borderRadius: "var(--radius-round)",
        background: "var(--accent-weak)",
        color: "var(--accent)",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "log-in",
      size: 28
    })), /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-2xl)",
        marginBottom: "var(--space-2)"
      }
    }, "\u0412\u0445\u043E\u0434 \u0432 \u041B\u0438\u0447\u043D\u044B\u0439 \u043A\u0430\u0431\u0438\u043D\u0435\u0442"), /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u0412\u0445\u043E\u0434 \u043F\u043E \u043D\u043E\u043C\u0435\u0440\u0443 \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044C\u0441\u043A\u043E\u0433\u043E \u0431\u0438\u043B\u0435\u0442\u0430.")), pending && /*#__PURE__*/React.createElement("div", {
      style: {
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Alert, {
      variant: "info",
      title: "\u0414\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 \u043D\u0443\u0436\u0435\u043D \u0432\u0445\u043E\u0434"
    }, "\u0423\u0432\u0430\u0436\u0430\u0435\u043C\u044B\u0439 \u0413\u043E\u0441\u0442\u044C! \u0414\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 \u043A\u043D\u0438\u0433 \u0438 \u0432\u0445\u043E\u0434\u0430 \u0432 \u041B\u0438\u0447\u043D\u044B\u0439 \u043A\u0430\u0431\u0438\u043D\u0435\u0442 \u0430\u0432\u0442\u043E\u0440\u0438\u0437\u0443\u0439\u0442\u0435\u0441\u044C.")), /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-6)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Input, {
      label: "\u0424\u0430\u043C\u0438\u043B\u0438\u044F",
      iconLeft: "user",
      placeholder: "\u041D\u0435\u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u043E",
      value: lastName,
      onChange: e => setLastName(e.target.value),
      onClear: () => setLastName("")
    }), /*#__PURE__*/React.createElement(Input, {
      label: "\u041D\u043E\u043C\u0435\u0440 \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044C\u0441\u043A\u043E\u0433\u043E \u0431\u0438\u043B\u0435\u0442\u0430",
      iconLeft: "log-in",
      placeholder: "00012345",
      inputMode: "numeric",
      value: ticket,
      error: err,
      onChange: e => setTicket(e.target.value),
      onKeyDown: e => e.key === "Enter" && submit(),
      onClear: () => setTicket("")
    }), /*#__PURE__*/React.createElement(Button, {
      block: true,
      size: "lg",
      iconLeft: "log-in",
      onClick: submit
    }, "\u0412\u043E\u0439\u0442\u0438"), /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)",
        textAlign: "center",
        margin: 0
      }
    }, "\u0414\u043B\u044F \u0434\u0435\u043C\u043E\u043D\u0441\u0442\u0440\u0430\u0446\u0438\u0438 \u0438\u0441\u043F\u043E\u043B\u044C\u0437\u0443\u0439\u0442\u0435 \u0431\u0438\u043B\u0435\u0442 ", /*#__PURE__*/React.createElement("b", null, "00012345"), ". \u041C\u044B \u043D\u0435 \u0441\u043E\u0431\u0438\u0440\u0430\u0435\u043C \u043B\u0438\u0448\u043D\u0438\u0445 \u0434\u0430\u043D\u043D\u044B\u0445 (152-\u0424\u0417).")));
  }
  function FormularScreen({
    account,
    onCancelOrder,
    onLogout,
    onSearch,
    onRenew,
    onRemoveBookmark,
    onOpenBookmark,
    onRunQuery,
    onRemoveQuery,
    onReadNotifications,
    onPayFines
  }) {
    const [tab, setTab] = React.useState("loans");
    const unread = (account.notifications || []).filter(n => n.unread).length;
    const finesTotal = (account.fines || []).reduce((s, f) => s + f.amount, 0);
    React.useEffect(() => {
      if (tab === "notify" && unread && onReadNotifications) onReadNotifications();
    }, [tab]);
    const Row = ({
      children,
      accentTone
    }) => /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-4)"
      }
    }, children);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 780,
        margin: "0 auto",
        padding: "var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        marginBottom: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 52,
        height: 52,
        borderRadius: "var(--radius-round)",
        background: "var(--accent-weak)",
        color: "var(--accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "user",
      size: 26
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-xl)"
      }
    }, "\u0427\u0438\u0442\u0430\u0442\u0435\u043B\u044C"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u0412\u044B, ", account.displayName, " \xB7 ", /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)"
      }
    }, "\u0431\u0438\u043B\u0435\u0442 \u2116 ", account.ticket))), finesTotal > 0 && /*#__PURE__*/React.createElement(Badge, {
      variant: "danger"
    }, "\u041A \u043E\u043F\u043B\u0430\u0442\u0435: ", finesTotal, " \u20BD"), /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      iconLeft: "log-out",
      onClick: onLogout
    }, "\u0412\u044B\u0439\u0442\u0438")), /*#__PURE__*/React.createElement(Tabs, {
      value: tab,
      onChange: setTab,
      tabs: [{
        id: "loans",
        label: "Формуляр",
        count: account.loans.length
      }, {
        id: "orders",
        label: "Корзина заказов",
        count: account.orders.length
      }, {
        id: "bookmarks",
        label: "Закладки",
        count: (account.bookmarks || []).length
      }, {
        id: "queries",
        label: "Пост. запросы",
        count: (account.savedQueries || []).length
      }, {
        id: "notify",
        label: "Уведомления",
        count: unread || undefined
      }, {
        id: "fines",
        label: "Оплата"
      }]
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-5)"
      }
    }, tab === "loans" && (account.loans.length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u041D\u0435\u0442 \u0442\u0435\u043A\u0443\u0449\u0438\u0445 \u0432\u044B\u0434\u0430\u0447",
      description: "\u0417\u0434\u0435\u0441\u044C \u043F\u043E\u044F\u0432\u044F\u0442\u0441\u044F \u0438\u0437\u0434\u0430\u043D\u0438\u044F \u043D\u0430 \u0440\u0443\u043A\u0430\u0445."
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, account.loans.map((l, i) => /*#__PURE__*/React.createElement(Row, {
      key: i
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "book",
      size: 18,
      style: {
        color: "var(--text-muted)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, l.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, l.location)), /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "right"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-2xs)",
        color: "var(--text-subtle)",
        textTransform: "uppercase",
        letterSpacing: ".05em"
      }
    }, "\u0412\u0435\u0440\u043D\u0443\u0442\u044C \u0434\u043E"), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: l.overdueSoon ? "var(--status-issued-strong)" : "var(--text-strong)",
        fontFamily: "var(--font-mono)"
      }
    }, l.due)), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "secondary",
      iconLeft: "refresh-cw",
      disabled: !l.renewable,
      onClick: () => onRenew(i)
    }, "\u041F\u0440\u043E\u0434\u043B\u0438\u0442\u044C"))))), tab === "orders" && (account.orders.length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u041A\u043E\u0440\u0437\u0438\u043D\u0430 \u0437\u0430\u043A\u0430\u0437\u043E\u0432 \u043F\u0443\u0441\u0442\u0430",
      description: "\u041D\u0430\u0439\u0434\u0438\u0442\u0435 \u0438\u0437\u0434\u0430\u043D\u0438\u0435 \u0438 \u043D\u0430\u0436\u043C\u0438\u0442\u0435 \xAB\u0417\u0430\u043A\u0430\u0437\u0430\u0442\u044C\xBB \u2014 \u0437\u0430\u043A\u0430\u0437 \u043F\u043E\u044F\u0432\u0438\u0442\u0441\u044F \u0437\u0434\u0435\u0441\u044C.",
      action: /*#__PURE__*/React.createElement(Button, {
        iconLeft: "search",
        onClick: onSearch
      }, "\u041A \u043F\u043E\u0438\u0441\u043A\u0443")
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, account.orders.map((o, i) => /*#__PURE__*/React.createElement(Row, {
      key: i
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "clock",
      size: 18,
      style: {
        color: "var(--status-issued)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, o.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, o.location)), /*#__PURE__*/React.createElement(Badge, {
      variant: "warning"
    }, "\u0412 \u043E\u0447\u0435\u0440\u0435\u0434\u0438"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: () => onCancelOrder(i)
    }, "\u041E\u0442\u043C\u0435\u043D\u0438\u0442\u044C"))))), tab === "bookmarks" && ((account.bookmarks || []).length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u0417\u0430\u043A\u043B\u0430\u0434\u043E\u043A \u043D\u0435\u0442",
      description: "\u041E\u0442\u043C\u0435\u0447\u0430\u0439\u0442\u0435 \u0437\u0430\u043F\u0438\u0441\u0438 \u043A\u043D\u043E\u043F\u043A\u043E\u0439 \xAB\u041E\u0442\u043C\u0435\u0442\u0438\u0442\u044C\xBB \u2014 \u043E\u043D\u0438 \u0441\u043E\u0445\u0440\u0430\u043D\u044F\u0442\u0441\u044F \u0437\u0434\u0435\u0441\u044C."
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, account.bookmarks.map(b => /*#__PURE__*/React.createElement(Row, {
      key: b.mfn
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "bookmark",
      size: 18,
      style: {
        color: "var(--accent)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onOpenBookmark(b),
      style: {
        flex: 1,
        minWidth: 0,
        textAlign: "left",
        border: "none",
        background: "none",
        cursor: "pointer",
        padding: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, b.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, b.author)), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      iconLeft: "trash",
      onClick: () => onRemoveBookmark(b.mfn)
    }, "\u0423\u0431\u0440\u0430\u0442\u044C"))))), tab === "queries" && ((account.savedQueries || []).length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u041D\u0435\u0442 \u043F\u043E\u0441\u0442\u043E\u044F\u043D\u043D\u044B\u0445 \u0437\u0430\u043F\u0440\u043E\u0441\u043E\u0432",
      description: "\u0421\u043E\u0445\u0440\u0430\u043D\u044F\u0439\u0442\u0435 \u043F\u043E\u0438\u0441\u043A\u043E\u0432\u044B\u0435 \u0437\u0430\u043F\u0440\u043E\u0441\u044B \u2014 \u043F\u0440\u0438 \u043D\u043E\u0432\u044B\u0445 \u0437\u0430\u043F\u0438\u0441\u044F\u0445 \u043F\u0440\u0438\u0434\u0451\u0442 \u0443\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u0435."
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, account.savedQueries.map(q => /*#__PURE__*/React.createElement(Row, {
      key: q.id
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "search",
      size: 18,
      style: {
        color: "var(--text-muted)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onRunQuery(q),
      style: {
        flex: 1,
        minWidth: 0,
        textAlign: "left",
        border: "none",
        background: "none",
        cursor: "pointer",
        padding: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, q.label), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, q.db)), q.fresh > 0 && /*#__PURE__*/React.createElement(Badge, {
      variant: "accent"
    }, "+", q.fresh, " \u043D\u043E\u0432\u044B\u0445"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      iconLeft: "trash",
      onClick: () => onRemoveQuery(q.id)
    }, "\u0423\u0434\u0430\u043B\u0438\u0442\u044C"))))), tab === "notify" && ((account.notifications || []).length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u0423\u0432\u0435\u0434\u043E\u043C\u043B\u0435\u043D\u0438\u0439 \u043D\u0435\u0442",
      description: "\u0421\u0440\u043E\u043A\u0438 \u0432\u043E\u0437\u0432\u0440\u0430\u0442\u0430, \u0433\u043E\u0442\u043E\u0432\u043D\u043E\u0441\u0442\u044C \u0437\u0430\u043A\u0430\u0437\u043E\u0432 \u0438 \u043D\u043E\u0432\u043E\u0435 \u043F\u043E \u0437\u0430\u043F\u0440\u043E\u0441\u0430\u043C \u2014 \u0437\u0434\u0435\u0441\u044C."
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, account.notifications.map(n => /*#__PURE__*/React.createElement("div", {
      key: n.id,
      style: {
        display: "flex",
        alignItems: "flex-start",
        gap: "var(--space-3)",
        background: n.unread ? "var(--accent-weak)" : "var(--surface-card)",
        border: "1px solid " + (n.unread ? "var(--accent-weak-border)" : "var(--border-subtle)"),
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: n.icon,
      size: 18,
      style: {
        color: TONE[n.tone] || TONE.neutral,
        flex: "none",
        marginTop: 2
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, n.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, n.text)), n.unread && /*#__PURE__*/React.createElement("span", {
      style: {
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: "var(--accent)",
        flex: "none",
        marginTop: 5
      }
    }))))), tab === "fines" && (finesTotal === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      icon: "check-circle",
      title: "\u0417\u0430\u0434\u043E\u043B\u0436\u0435\u043D\u043D\u043E\u0441\u0442\u0435\u0439 \u043D\u0435\u0442",
      description: "\u0428\u0442\u0440\u0430\u0444\u044B \u043E\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044E\u0442. \u0421\u043F\u0430\u0441\u0438\u0431\u043E, \u0447\u0442\u043E \u0432\u043E\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442\u0435 \u0432\u043E\u0432\u0440\u0435\u043C\u044F."
    }) : /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)",
        marginBottom: "var(--space-4)"
      }
    }, account.fines.map(f => /*#__PURE__*/React.createElement(Row, {
      key: f.id
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "alert-triangle",
      size: 18,
      style: {
        color: "var(--danger-500)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, f.reason), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u043D\u0430\u0447\u0438\u0441\u043B\u0435\u043D\u043E ", f.date)), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: "var(--font-mono)",
        fontWeight: 700,
        color: "var(--text-strong)"
      }
    }, f.amount, " \u20BD")))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-4)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u0418\u0442\u043E\u0433\u043E \u043A \u043E\u043F\u043B\u0430\u0442\u0435"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-display)",
        fontSize: "var(--text-xl)",
        fontWeight: 700,
        color: "var(--text-strong)"
      }
    }, finesTotal, " \u20BD"), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      iconLeft: "credit-card",
      onClick: onPayFines
    }, "\u041E\u043F\u043B\u0430\u0442\u0438\u0442\u044C \u043E\u043D\u043B\u0430\u0439\u043D")), /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)",
        marginTop: "var(--space-3)"
      }
    }, "\u041E\u043F\u043B\u0430\u0442\u0430 \u043F\u0440\u043E\u0432\u043E\u0434\u0438\u0442\u0441\u044F \u0447\u0435\u0440\u0435\u0437 \u0437\u0430\u0449\u0438\u0449\u0451\u043D\u043D\u044B\u0439 \u0448\u043B\u044E\u0437; \u0434\u0430\u043D\u043D\u044B\u0435 \u043A\u0430\u0440\u0442\u044B \u043D\u0435 \u0445\u0440\u0430\u043D\u044F\u0442\u0441\u044F \u0432 \u043A\u0430\u0442\u0430\u043B\u043E\u0433\u0435.")))));
  }
  Object.assign(window, {
    LoginScreen,
    FormularScreen
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/AccountScreens.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/App.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const D = window.IRBIS_DATA;
  const {
    ToastViewport,
    EmptyState,
    Button,
    Icon
  } = NS;
  const FileViewer = NS.FileViewer;
  const DBS = D.databases;
  const GROUPS = D.groups;
  const getDb = id => DBS.find(d => d.id === id) || DBS[0];

  // Выбор файла для просмотра: приоритет поля 955 над 951 (§1.7).
  function pickFile(files) {
    if (!files || !files.length) return null;
    return files.slice().sort((a, b) => (a.priority || 9) - (b.priority || 9))[0];
  }
  function recordFor(item) {
    const dbId = item.sourceDb || item.db;
    if (D.records[item.mfn]) return D.records[item.mfn];
    return {
      mfn: item.mfn,
      db: dbId,
      title: item.title,
      author: item.author,
      imprint: {
        publisher: "—",
        year: item.year
      },
      badges: [{
        variant: "neutral",
        text: item.docType
      }],
      tint: item.tint,
      recLevel: item.recLevel,
      pftHtml: "<p><b>" + item.title + "</b></p><p>" + (item.author && item.author !== "—" ? item.author + ". " : "") + item.year + ".</p>" + ((item.fields || []).length ? "<dl>" + item.fields.map(f => "<dt>" + f.label + "</dt><dd>" + f.value + "</dd>").join("") + "</dl>" : ""),
      subjects: [],
      files: [],
      links: {},
      holdings: item.availability ? [{
        location: "Основной фонд",
        inventory: "инв. " + item.mfn,
        status: item.availability
      }] : []
    };
  }

  // Мультибазовый поиск (§1.4): агрегируем по всем выбранным базам,
  // каждую запись помечаем источником (sourceDb / dbShort).
  function runQuery(dbIds, query, filters, opts = {}) {
    let out = [];
    const q = (query || "").trim().toLowerCase();
    dbIds.forEach(id => {
      const db = getDb(id);
      let list = (D.results[id] || []).slice();
      if (q) list = list.filter(r => (r.title + " " + (r.author || "")).toLowerCase().includes(q));
      if (opts.onlyDigital && id === "EK") list = list.filter(r => r.hasDigital);
      // Словарные чипы и групповые фильтры применяются только при одной базе.
      if (dbIds.length === 1) {
        const dictTerms = Object.keys(filters).filter(k => k.startsWith("dict:") && filters[k]).map(k => k.slice(5).toLowerCase());
        if (dictTerms.length) list = list.filter(r => dictTerms.some(t => (r.title + " " + (r.author || "")).toLowerCase().includes(t.split(" ")[0])));
        // nav: (классификатор) — на моке пропускаем как индексный фильтр (чип показывается).
        (db.filters || []).forEach(g => {
          const sel = g.options.filter(o => filters[g.id + ":" + o]);
          if (sel.length) list = list.filter(r => sel.some(v => r.docType === v || (r.fields || []).some(f => f.value === v || v.indexOf(f.value) === 0)));
        });
      }
      list = list.map(r => ({
        ...r,
        sourceDb: id,
        db: id,
        dbTitle: db.name,
        dbShort: db.short || db.name
      }));
      out = out.concat(list);
    });
    return out;
  }
  function availableModes(dbIds) {
    if (dbIds.length === 1) return getDb(dbIds[0]).modes || ["simple"];
    return ["simple"];
  }
  const blankSpecial = db => {
    const v = {};
    (db && db.specialForm || []).forEach(f => {
      if (f.kind === "roles") f.fields.forEach((r, i) => v[f.id + ":" + i] = "");else if (f.kind === "sourceArea") f.fields.forEach(sf => v[sf.id] = "");else if (f.kind === "range") {
        v[f.id + ":from"] = "";
        v[f.id + ":to"] = "";
      } else if (f.kind === "dateEvent") {
        v[f.id + ":y"] = "";
        v[f.id + ":m"] = "";
        v[f.id + ":d"] = "";
      } else v[f.id] = "";
    });
    return v;
  };
  const initialSearch = () => ({
    dbIds: [],
    query: "",
    mode: "simple",
    page: 1,
    pageSize: 20,
    sort: "По релевантности",
    view: "gallery",
    filters: {},
    advRows: [{
      op: "and",
      field: "TI",
      qual: "contains",
      value: ""
    }],
    trunc: true,
    dateFrom: "",
    dateTo: "",
    onlyDigital: false,
    special: {},
    marked: new Set(),
    all: []
  });
  function App() {
    const [theme, setTheme] = React.useState("theatrical");
    const [a11y, setA11y] = React.useState(false);
    const [noImg, setNoImg] = React.useState(false);
    const [libraryId, setLibraryId] = React.useState((D.libraries[0] || {}).id);
    const library = (D.libraries || []).find(l => l.id === libraryId) || D.libraries[0];
    const [context, setContext] = React.useState("reader"); // reader | staff
    const [staffRoute, setStaffRoute] = React.useState({
      name: "desktop"
    });
    const [route, setRoute] = React.useState({
      name: "home"
    });
    const [s, setS] = React.useState(initialSearch);
    const [loading, setLoading] = React.useState(false);
    const [account, setAccount] = React.useState({
      loggedIn: false,
      ticket: D.account.ticket,
      lastName: D.account.lastName,
      displayName: D.account.displayName,
      loans: D.account.loans,
      orders: [],
      bookmarks: D.account.bookmarks || [],
      savedQueries: D.account.savedQueries || [],
      notifications: D.account.notifications || [],
      fines: D.account.fines || []
    });
    const [toasts, setToasts] = React.useState([]);
    const [order, setOrder] = React.useState({
      open: false,
      record: null
    });
    const [pendingOrder, setPendingOrder] = React.useState(null);
    const [viewer, setViewer] = React.useState({
      open: false,
      file: null,
      canView: true
    });
    const timer = React.useRef(null);
    const dbIds = s.dbIds;
    const formDb = dbIds.length === 1 ? getDb(dbIds[0]) : null; // конфиг формы — при одной базе
    const headDb = formDb || (dbIds.length ? getDb(dbIds[0]) : null);
    const patch = p => setS(prev => ({
      ...prev,
      ...p
    }));
    const toast = t => {
      const id = Date.now() + Math.random();
      setToasts(x => [...x, {
        ...t,
        id
      }]);
      setTimeout(() => setToasts(x => x.filter(y => y.id !== id)), 4200);
    };
    function freezeTransitions() {
      const el = document.documentElement;
      el.classList.add("irb-theme-switching");
      requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove("irb-theme-switching")));
    }
    const changeTheme = v => {
      freezeTransitions();
      setTheme(v);
    };
    const changeA11y = v => {
      freezeTransitions();
      setA11y(v);
    };
    // Смена библиотеки — меняет бренд и применяет её скин (§9).
    const pickLibrary = id => {
      const lib = (D.libraries || []).find(l => l.id === id);
      if (!lib) return;
      freezeTransitions();
      setLibraryId(id);
      if (!a11y) setTheme(lib.theme);
    };

    // ---- Сотруднический контекст ----
    function staffTask(domainId, taskId) {
      if (domainId === "cataloging" && (taskId === "cat-new" || taskId === "cat-list")) {
        setStaffRoute({
          name: "cataloging",
          profile: D.catalogingProfiles.EK
        });
      } else if (taskId === "circ-issue" || taskId === "circ-queue" || taskId === "circ-shelf") {
        setStaffRoute({
          name: "circulation",
          tab: taskId
        });
      } else if (taskId === "inv-session") {
        setStaffRoute({
          name: "inventory"
        });
      } else if (taskId === "an-dash") {
        setStaffRoute({
          name: "dashboard"
        });
      } else {
        setStaffRoute({
          name: "stub",
          title: {
            "cat-global": "Глобальная корректировка",
            "cat-import": "Импорт записи (copy-cataloging)",
            "circ-issue": "Книговыдача: выдача / возврат",
            "circ-queue": "Очередь заказов",
            "circ-shelf": "Бронеполка",
            "circ-debt": "Должники",
            "acq-order": "Заказы поставщикам",
            "acq-ksu": "КСУ",
            "inv-session": "Сессия инвентаризации (ТСД)",
            "inv-report": "Отчёт расхождений",
            "an-dash": "BI-дашборд"
          }[taskId] || "Экран сотрудника"
        });
      }
    }
    function switchContext(c) {
      setContext(c);
      if (c === "staff") setStaffRoute({
        name: "desktop"
      });else setRoute({
        name: "home"
      });
    }

    // ---- Поиск (старт ТОЛЬКО по кнопке для расширенного/спец; простой — кнопка/Enter) ----
    function doSearch(query, opts = {}) {
      const q = query != null ? query : s.query;
      if (!dbIds.length) {
        toast({
          variant: "warning",
          title: "Не выбрана база",
          message: "Отметьте хотя бы одну базу в селекторе баз."
        });
        return;
      }
      if (q.trim().toLowerCase() === "ошибка") {
        setRoute({
          name: "catalog-error"
        });
        return;
      }
      const nextFilters = opts.filters || s.filters;
      setLoading(true);
      setRoute({
        name: "results"
      });
      patch({
        query: q,
        page: opts.resetPage ? 1 : s.page,
        filters: nextFilters
      });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        const all = runQuery(dbIds, q, nextFilters, {
          onlyDigital: s.onlyDigital
        });
        setS(prev => ({
          ...prev,
          all,
          query: q,
          page: opts.resetPage ? 1 : prev.page
        }));
        setLoading(false);
      }, 600);
    }
    function setDbIds(ids) {
      setS(prev => {
        const modes = availableModes(ids);
        const mode = modes.includes(prev.mode) ? prev.mode : "simple";
        const next = {
          ...prev,
          dbIds: ids,
          mode,
          special: ids.length === 1 ? Object.keys(prev.special).length ? prev.special : blankSpecial(getDb(ids[0])) : {},
          filters: {},
          page: 1
        };
        return next;
      });
      if (route.name === "results" && ids.length) {
        setLoading(true);
        clearTimeout(timer.current);
        timer.current = setTimeout(() => {
          setS(prev => ({
            ...prev,
            all: runQuery(ids, prev.query, {}, {
              onlyDigital: prev.onlyDigital
            })
          }));
          setLoading(false);
        }, 500);
      }
    }
    function setMode(m) {
      setS(prev => ({
        ...prev,
        mode: m,
        special: m === "special" && formDb ? Object.keys(prev.special).length ? prev.special : blankSpecial(formDb) : prev.special
      }));
    }
    function setFilter(key, val) {
      const filters = {
        ...s.filters,
        [key]: val
      };
      if (!val) delete filters[key];
      setLoading(true);
      patch({
        filters,
        page: 1
      });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        setS(prev => ({
          ...prev,
          all: runQuery(dbIds, s.query, filters, {
            onlyDigital: prev.onlyDigital
          }),
          filters,
          page: 1
        }));
        setLoading(false);
      }, 350);
    }
    function clearAll() {
      setLoading(true);
      patch({
        filters: {},
        page: 1
      });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        setS(prev => ({
          ...prev,
          all: runQuery(dbIds, s.query, {}, {
            onlyDigital: prev.onlyDigital
          }),
          filters: {},
          page: 1
        }));
        setLoading(false);
      }, 300);
    }
    function runAdvanced() {
      const q = s.advRows.map(r => r.value).filter(Boolean).join(" ") || s.query;
      doSearch(q, {
        resetPage: true
      });
    }
    function runSpecial() {
      const q = Object.keys(s.special).map(k => s.special[k]).filter(v => v && typeof v === "string" && v.trim() && v.indexOf("—") !== 0).join(" ") || s.query;
      doSearch(q, {
        resetPage: true
      });
    }
    const activeChips = Object.keys(s.filters).filter(k => s.filters[k]).map(k => {
      if (k.startsWith("dict:")) return {
        key: k,
        group: "Словарь",
        label: k.slice(5)
      };
      if (k.startsWith("nav:")) return {
        key: k,
        group: "Классификатор",
        label: typeof s.filters[k] === "string" ? s.filters[k] : k.slice(4)
      };
      const [gid, ...rest] = k.split(":");
      const g = (formDb ? formDb.filters : []).find(x => x.id === gid);
      return {
        key: k,
        group: g ? g.label : gid,
        label: rest.join(":")
      };
    });

    // ---- Навигация по записи ----
    function openRecord(item) {
      const targetDb = getDb(item.sourceDb || item.db);
      setRoute({
        name: "record",
        item,
        db: targetDb
      });
      window.scrollTo(0, 0);
    }
    function backToResults() {
      setRoute({
        name: "results"
      });
    } // состояние s сохраняется (§1.3)

    // Переход по связи 390/488 в другую базу — показываем имя целевой БД (§1.4)
    function followLink(link) {
      const targetDbId = link.target || (link.level ? "GUAR" : null) || "EK";
      const mfn = link.mfn;
      const rec = D.records[mfn];
      const targetDb = getDb(rec ? rec.db : targetDbId);
      const item = rec || {
        mfn,
        db: targetDb.id
      };
      toast({
        variant: "info",
        title: "Переход в базу",
        message: targetDb.name
      });
      setRoute({
        name: "record",
        item,
        db: targetDb
      });
      window.scrollTo(0, 0);
    }
    function toggleMark(mfn) {
      setS(prev => {
        const m = new Set(prev.marked);
        m.has(mfn) ? m.delete(mfn) : m.add(mfn);
        return {
          ...prev,
          marked: m
        };
      });
    }

    // ---- Просмотр файла (view-only) ----
    function openFile(file) {
      const canView = !file.requiresAuth || account.loggedIn;
      const terms = (s.query || "").split(/\s+/).filter(w => w.length > 1).slice(0, 4);
      const relevantPages = file.kind === "pdf" && terms.length ? [3, 12, 45].filter(p => p <= (file.pages || 99)) : null;
      setViewer({
        open: true,
        file,
        canView,
        terms,
        relevantPages
      });
    }

    // ---- Заказ (гость не может — §1.2) ----
    function startOrder(record) {
      if (!account.loggedIn) {
        setPendingOrder(record);
        setRoute({
          name: "login"
        });
        toast({
          variant: "info",
          title: "Требуется вход",
          message: "Войдите по читательскому билету, чтобы оформить заказ."
        });
        return;
      }
      setOrder({
        open: true,
        record
      });
    }
    function confirmOrder(holding) {
      setAccount(a => ({
        ...a,
        orders: [...a.orders, {
          title: order.record.title,
          status: "queued",
          location: holding.location
        }]
      }));
      toast({
        variant: "success",
        title: "Заказ принят",
        message: "Экземпляр в очереди выдачи."
      });
    }
    function orderMarked() {
      if (!account.loggedIn) {
        setRoute({
          name: "login"
        });
        toast({
          variant: "info",
          title: "Требуется вход",
          message: "Войдите, чтобы заказать отмеченные."
        });
        return;
      }
      const titles = s.all.filter(r => s.marked.has(r.mfn));
      setAccount(a => ({
        ...a,
        orders: [...a.orders, ...titles.map(t => ({
          title: t.title,
          status: "queued",
          location: "Основной фонд"
        }))]
      }));
      toast({
        variant: "success",
        title: "Заказано: " + titles.length,
        message: "Добавлено в Корзину заказов."
      });
      setS(prev => ({
        ...prev,
        marked: new Set()
      }));
    }
    function login(ticket, lastName) {
      setAccount(a => ({
        ...a,
        loggedIn: true,
        ticket
      }));
      if (pendingOrder) {
        const r = pendingOrder;
        setPendingOrder(null);
        setOrder({
          open: true,
          record: r
        });
        setRoute({
          name: "record",
          item: r,
          db: getDb(r.db)
        });
      } else setRoute({
        name: "account"
      });
      toast({
        variant: "success",
        title: "Вы вошли",
        message: "Билет № " + ticket
      });
    }
    function logout() {
      setAccount(a => ({
        ...a,
        loggedIn: false,
        orders: []
      }));
      setRoute({
        name: "home"
      });
    }
    function searchSubject(subject) {
      if (!dbIds.length) setS(prev => ({
        ...prev,
        dbIds: [route.db ? route.db.id : "EK"]
      }));
      const ids = dbIds.length ? dbIds : [route.db ? route.db.id : "EK"];
      patch({
        query: subject,
        filters: {},
        mode: "simple"
      });
      setLoading(true);
      setRoute({
        name: "results"
      });
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        setS(prev => ({
          ...prev,
          all: runQuery(ids, subject, {}, {}),
          query: subject,
          page: 1,
          filters: {}
        }));
        setLoading(false);
      }, 500);
    }

    // ---- Производные для выдачи ----
    const total = s.all.length;
    const start = (s.page - 1) * s.pageSize;
    const pageItems = s.all.slice(start, start + s.pageSize);
    const dictionary = formDb ? D.dictionaries[formDb.id] || [] : [];
    const premieres = D.results.TUAR;
    const multiBase = dbIds.length > 1;
    const rootTheme = a11y ? "a11y" : theme === "working" ? undefined : theme;
    const fxTheme = a11y ? null : theme;
    return /*#__PURE__*/React.createElement("div", {
      "data-theme": rootTheme,
      style: {
        minHeight: "100vh",
        background: "var(--bg-page)",
        color: "var(--text-body)",
        display: "flex",
        flexDirection: "column"
      }
    }, /*#__PURE__*/React.createElement(window.TopBar, {
      onHome: () => {
        if (context === "staff") setStaffRoute({
          name: "desktop"
        });else setRoute({
          name: "home"
        });
      },
      onAccount: () => setRoute({
        name: account.loggedIn ? "account" : "login"
      }),
      account: account,
      theme: theme,
      setTheme: changeTheme,
      a11y: a11y,
      setA11y: changeA11y,
      noImg: noImg,
      setNoImg: setNoImg,
      context: context,
      setContext: switchContext,
      library: library,
      libraries: D.libraries,
      onPickLibrary: pickLibrary,
      currentDb: context === "reader" && (route.name === "results" && headDb ? headDb : route.name === "record" ? route.db : null),
      multiBase: context === "reader" && route.name === "results" && multiBase ? dbIds.length : 0
    }), /*#__PURE__*/React.createElement("main", {
      style: {
        flex: 1
      }
    }, context === "staff" ? /*#__PURE__*/React.createElement(React.Fragment, null, staffRoute.name === "desktop" && /*#__PURE__*/React.createElement(window.StaffDesktop, {
      staff: D.staff,
      onTask: staffTask
    }), staffRoute.name === "cataloging" && /*#__PURE__*/React.createElement(window.CatalogingWorksheet, {
      profile: staffRoute.profile,
      onBack: () => setStaffRoute({
        name: "desktop"
      }),
      onToast: toast
    }), staffRoute.name === "circulation" && /*#__PURE__*/React.createElement(window.Circulation, {
      data: D.staffData,
      onBack: () => setStaffRoute({
        name: "desktop"
      }),
      onToast: toast
    }), staffRoute.name === "inventory" && /*#__PURE__*/React.createElement(window.Inventory, {
      data: D.staffData,
      onBack: () => setStaffRoute({
        name: "desktop"
      }),
      onToast: toast
    }), staffRoute.name === "dashboard" && /*#__PURE__*/React.createElement(window.Dashboard, {
      data: D.staffData,
      onBack: () => setStaffRoute({
        name: "desktop"
      })
    }), staffRoute.name === "stub" && /*#__PURE__*/React.createElement(window.StaffStub, {
      title: staffRoute.title,
      onBack: () => setStaffRoute({
        name: "desktop"
      })
    })) : /*#__PURE__*/React.createElement(React.Fragment, null, route.name === "home" && /*#__PURE__*/React.createElement(window.HomeScreen, {
      databases: DBS,
      groups: GROUPS,
      dbIds: dbIds,
      setDbIds: setDbIds,
      query: s.query,
      setQuery: q => patch({
        query: q
      }),
      onSearch: q => doSearch(q, {
        resetPage: true
      }),
      onlyDigital: s.onlyDigital,
      setOnlyDigital: v => patch({
        onlyDigital: v
      }),
      formDb: formDb,
      suggestions: dictionary,
      premieres: premieres,
      onOpenRecord: openRecord,
      account: account,
      onLogin: () => setRoute({
        name: "login"
      }),
      library: library
    }), route.name === "results" && /*#__PURE__*/React.createElement(window.ResultsScreen, {
      databases: DBS,
      groups: GROUPS,
      dbIds: dbIds,
      setDbIds: setDbIds,
      formDb: formDb,
      headDb: headDb,
      multiBase: multiBase,
      query: s.query,
      setQuery: q => patch({
        query: q
      }),
      onSearch: q => doSearch(q, {
        resetPage: true
      }),
      mode: s.mode,
      setMode: setMode,
      availableModes: availableModes(dbIds),
      loading: loading,
      items: pageItems,
      total: total,
      page: s.page,
      setPage: p => patch({
        page: p
      }),
      pageSize: s.pageSize,
      setPageSize: n => patch({
        pageSize: n,
        page: 1
      }),
      sort: s.sort,
      setSort: v => patch({
        sort: v
      }),
      view: s.view,
      setView: v => patch({
        view: v
      }),
      marked: s.marked,
      toggleMark: toggleMark,
      clearMarked: () => patch({
        marked: new Set()
      }),
      onOrderMarked: orderMarked,
      filters: s.filters,
      setFilter: setFilter,
      activeChips: activeChips,
      removeChip: k => setFilter(k, false),
      clearAll: clearAll,
      advRows: s.advRows,
      setAdvRows: r => patch({
        advRows: r
      }),
      trunc: s.trunc,
      setTrunc: v => patch({
        trunc: v
      }),
      runAdvanced: runAdvanced,
      special: s.special,
      setSpecial: sp => patch({
        special: sp
      }),
      runSpecial: runSpecial,
      resetSpecial: () => patch({
        special: blankSpecial(formDb)
      }),
      onlyDigital: s.onlyDigital,
      setOnlyDigital: v => patch({
        onlyDigital: v
      }),
      dictionary: dictionary,
      dateFrom: s.dateFrom,
      dateTo: s.dateTo,
      setDate: (k, v) => patch(k === "from" ? {
        dateFrom: v
      } : {
        dateTo: v
      }),
      onOpenRecord: openRecord,
      noImg: noImg,
      suggestions: dictionary,
      account: account,
      allItems: s.all
    }), route.name === "record" && /*#__PURE__*/React.createElement(window.RecordScreen, {
      record: recordFor(route.item),
      db: route.db,
      onBack: backToResults,
      fromResults: s.all.length > 0,
      onSubject: searchSubject,
      onOrder: () => startOrder(recordFor(route.item)),
      onToggleMark: () => toggleMark(route.item.mfn),
      marked: s.marked.has(route.item.mfn),
      account: account,
      noImg: noImg,
      onToast: toast,
      onOpenFile: openFile,
      onFollowLink: followLink,
      pickFile: pickFile
    }), route.name === "login" && /*#__PURE__*/React.createElement(window.LoginScreen, {
      onLogin: login,
      pending: !!pendingOrder
    }), route.name === "account" && /*#__PURE__*/React.createElement(window.FormularScreen, {
      account: account,
      onCancelOrder: i => setAccount(a => ({
        ...a,
        orders: a.orders.filter((_, j) => j !== i)
      })),
      onLogout: logout,
      onSearch: () => setRoute({
        name: "home"
      }),
      onRenew: i => {
        setAccount(a => ({
          ...a,
          loans: a.loans.map((l, j) => j === i ? {
            ...l,
            due: "31.07.2026",
            renewable: false
          } : l)
        }));
        toast({
          variant: "success",
          title: "Срок продлён",
          message: "Новая дата возврата: 31.07.2026."
        });
      },
      onRemoveBookmark: mfn => setAccount(a => ({
        ...a,
        bookmarks: a.bookmarks.filter(b => b.mfn !== mfn)
      })),
      onOpenBookmark: b => openRecord(b),
      onRunQuery: q => searchSubject(q.label),
      onRemoveQuery: id => setAccount(a => ({
        ...a,
        savedQueries: a.savedQueries.filter(q => q.id !== id)
      })),
      onReadNotifications: () => setAccount(a => ({
        ...a,
        notifications: a.notifications.map(n => ({
          ...n,
          unread: false
        }))
      })),
      onPayFines: () => {
        setAccount(a => ({
          ...a,
          fines: []
        }));
        toast({
          variant: "success",
          title: "Оплата прошла",
          message: "Задолженность погашена."
        });
      }
    }), route.name === "catalog-error" && /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "var(--space-16) var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement(EmptyState, {
      variant: "error",
      icon: "alert-octagon",
      title: "\u041A\u0430\u0442\u0430\u043B\u043E\u0433 \u0432\u0440\u0435\u043C\u0435\u043D\u043D\u043E \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D",
      description: "\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0441\u0432\u044F\u0437\u0430\u0442\u044C\u0441\u044F \u0441 \u043A\u0430\u0442\u0430\u043B\u043E\u0433\u043E\u043C. \u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u0435 \u043F\u043E\u043F\u044B\u0442\u043A\u0443 \u043F\u043E\u0437\u0436\u0435 \u2014 \u043C\u044B \u0443\u0436\u0435 \u0437\u043D\u0430\u0435\u043C \u043E \u043F\u0440\u043E\u0431\u043B\u0435\u043C\u0435.",
      action: /*#__PURE__*/React.createElement(Button, {
        iconLeft: "rotate-ccw",
        onClick: () => setRoute({
          name: "home"
        })
      }, "\u041D\u0430 \u0433\u043B\u0430\u0432\u043D\u0443\u044E")
    })))), /*#__PURE__*/React.createElement("footer", {
      style: {
        borderTop: "1px solid var(--border-subtle)",
        padding: "var(--space-5) var(--space-6)",
        marginTop: "var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: "var(--container-max)",
        margin: "0 auto",
        display: "flex",
        gap: "var(--space-4)",
        alignItems: "center",
        flexWrap: "wrap",
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "globe",
      size: 14
    }), /*#__PURE__*/React.createElement("span", null, "\u041A\u0430\u0442\u0430\u043B\u043E\u0433 \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442 \u0432 \u0437\u0430\u0449\u0438\u0449\u0451\u043D\u043D\u043E\u043C \u043A\u043E\u043D\u0442\u0443\u0440\u0435. \u0414\u0435\u043C\u043E\u043D\u0441\u0442\u0440\u0430\u0446\u0438\u043E\u043D\u043D\u044B\u0435 \u0434\u0430\u043D\u043D\u044B\u0435 \u043E\u0431\u0435\u0437\u043B\u0438\u0447\u0435\u043D\u044B."), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: "auto"
      }
    }, "\u041F\u043E\u0434\u0441\u043A\u0430\u0437\u043A\u0430: \u0437\u0430\u043F\u0440\u043E\u0441 \xAB\u043E\u0448\u0438\u0431\u043A\u0430\xBB \u043F\u043E\u043A\u0430\u0436\u0435\u0442 \u0441\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u0435 \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u043D\u043E\u0441\u0442\u0438 \u043A\u0430\u0442\u0430\u043B\u043E\u0433\u0430."))), /*#__PURE__*/React.createElement(ToastViewport, {
      toasts: toasts,
      onDismiss: id => setToasts(x => x.filter(y => y.id !== id))
    }), /*#__PURE__*/React.createElement(window.OrderModal, {
      open: order.open,
      record: order.record,
      onClose: () => setOrder({
        open: false,
        record: null
      }),
      onConfirm: confirmOrder
    }), FileViewer && /*#__PURE__*/React.createElement(FileViewer, {
      open: viewer.open,
      file: viewer.file,
      canView: viewer.canView,
      terms: viewer.terms,
      relevantPages: viewer.relevantPages,
      onClose: () => setViewer({
        open: false,
        file: null,
        canView: true
      })
    }), window.SeasonalFX && /*#__PURE__*/React.createElement(window.SeasonalFX, {
      theme: fxTheme
    }));
  }
  Object.assign(window, {
    IrbisApp: App
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/HomeScreen.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Checkbox,
    Button
  } = NS;
  function ExampleChips({
    items,
    onPick
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        alignItems: "center",
        justifyContent: "center"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-subtle)"
      }
    }, "\u041D\u0430\u043F\u0440\u0438\u043C\u0435\u0440:"), items.map(t => /*#__PURE__*/React.createElement("button", {
      key: t,
      type: "button",
      onClick: () => onPick(t),
      style: {
        border: "1px solid var(--border-default)",
        background: "var(--surface-card)",
        color: "var(--text-body)",
        borderRadius: "var(--radius-pill)",
        padding: "5px 13px",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)"
      }
    }, t)));
  }
  function PremiereBlock({
    premieres,
    onOpen
  }) {
    return /*#__PURE__*/React.createElement("section", {
      style: {
        maxWidth: 720,
        margin: "0 auto",
        marginTop: "var(--space-12)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "12px 18px",
        borderBottom: "1px solid var(--border-subtle)",
        color: "var(--accent)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "calendar-star",
      size: 18
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-display)",
        fontWeight: 700,
        color: "var(--text-strong)",
        fontSize: "var(--text-md)"
      }
    }, "\u041A\u0430\u043B\u0435\u043D\u0434\u0430\u0440\u044C \u0441\u043E\u0431\u044B\u0442\u0438\u0439"), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: "auto",
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, "\u0438\u0437 \u0431\u0430\u0437\u044B \xAB\u041F\u0440\u0435\u043C\u044C\u0435\u0440\u044B\xBB")), premieres.map(p => /*#__PURE__*/React.createElement("button", {
      key: p.mfn,
      type: "button",
      onClick: () => onOpen(p),
      style: {
        display: "flex",
        alignItems: "center",
        gap: 14,
        width: "100%",
        padding: "13px 18px",
        border: "none",
        borderBottom: "1px solid var(--border-subtle)",
        background: "transparent",
        cursor: "pointer",
        textAlign: "left",
        fontFamily: "var(--font-ui)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--accent)",
        width: 130,
        flex: "none"
      }
    }, p.year), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, p.title), /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, p.author, " \xB7 ", p.fields[0].value)), /*#__PURE__*/React.createElement(Icon, {
      name: "chevron-right",
      size: 16,
      style: {
        color: "var(--text-subtle)"
      }
    }))));
  }
  function HomeScreen(props) {
    const {
      databases,
      groups,
      dbIds,
      setDbIds,
      query,
      setQuery,
      onSearch,
      onlyDigital,
      setOnlyDigital,
      formDb,
      suggestions,
      premieres,
      onOpenRecord,
      account,
      onLogin,
      library
    } = props;
    const examples = formDb ? {
      EK: ["Чайка", "Чехов А. П.", "русская драматургия"],
      SKETCH: ["эскиз декорации", "Симов В. А.", "костюм"],
      GUAR: ["цензура", "Фонд 1", "1898"],
      TUAR: ["Чайка", "опера", "балет"],
      PLAY: ["Чайка", "комедия", "Чехов"]
    }[formDb.id] || [] : ["Чайка", "Чехов А. П."];
    const showDigital = formDb && formDb.simpleExtra;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 920,
        margin: "0 auto",
        padding: "var(--space-16) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "center",
        marginBottom: "var(--space-8)"
      }
    }, library && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        letterSpacing: ".1em",
        textTransform: "uppercase",
        color: "var(--accent)",
        marginBottom: "var(--space-3)"
      }
    }, library.name), /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-3xl)",
        marginBottom: "var(--space-3)"
      }
    }, "\u042D\u043B\u0435\u043A\u0442\u0440\u043E\u043D\u043D\u044B\u0439 \u043A\u0430\u0442\u0430\u043B\u043E\u0433 \u0438 \u0411\u0430\u0437\u044B \u0434\u0430\u043D\u043D\u044B\u0445"), /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-md)",
        color: "var(--text-muted)",
        maxWidth: 580,
        margin: "0 auto"
      }
    }, library && library.id === "spbgtb" ? "Профильная театрально-художественная библиотека: книги, периодика, эскизный фонд, архивные документы, пьесы, либретто и календарь премьер." : "Поиск по книгам, периодике, статьям, архивным и изобразительным материалам. Выберите базы и начните поиск.")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
        maxWidth: 720,
        margin: "0 auto"
      }
    }, /*#__PURE__*/React.createElement(NS.DatabaseSelector, {
      databases: databases,
      groups: groups,
      value: dbIds,
      onChange: setDbIds
    }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      style: {
        display: "block",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: "var(--text-strong)",
        marginBottom: 6
      }
    }, "\u042F \u0438\u0449\u0443:"), /*#__PURE__*/React.createElement(NS.SearchBar, {
      value: query,
      onChange: setQuery,
      onSearch: onSearch,
      suggestions: suggestions,
      onPickSuggestion: sug => {
        setQuery(sug.term || sug);
        onSearch(sug.term || sug);
      },
      buttonLabel: "\u041F\u043E\u0438\u0441\u043A",
      onReset: () => {
        setQuery("");
        setDbIds([]);
      },
      placeholder: formDb ? "в базе «" + formDb.name + "»…" : dbIds.length ? "поиск по " + dbIds.length + " базам…" : "сначала выберите базу…"
    }), showDigital && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: 10
      }
    }, /*#__PURE__*/React.createElement(Checkbox, {
      label: "\u0422\u043E\u043B\u044C\u043A\u043E \u0441 \u044D\u043B\u0435\u043A\u0442\u0440\u043E\u043D\u043D\u044B\u043C\u0438 \u0432\u0435\u0440\u0441\u0438\u044F\u043C\u0438",
      checked: onlyDigital,
      onChange: e => setOnlyDigital(e.target.checked)
    })))), examples.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement(ExampleChips, {
      items: examples,
      onPick: t => {
        setQuery(t);
        onSearch(t);
      }
    })), !account.loggedIn && /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "center",
        marginTop: "var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onLogin,
      style: {
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        display: "inline-flex",
        alignItems: "center",
        gap: 6
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "log-in",
      size: 16
    }), " \u0412\u0445\u043E\u0434 \u0432 \u041B\u0438\u0447\u043D\u044B\u0439 \u043A\u0430\u0431\u0438\u043D\u0435\u0442")), premieres && premieres.length > 0 && /*#__PURE__*/React.createElement(PremiereBlock, {
      premieres: premieres,
      onOpen: onOpenRecord
    }));
  }
  Object.assign(window, {
    HomeScreen
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/HomeScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/OrderModal.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Dialog,
    Button,
    Radio,
    StatusBadge,
    Icon,
    Alert
  } = NS;
  function OrderModal({
    open,
    record,
    onClose,
    onConfirm
  }) {
    const [step, setStep] = React.useState("select");
    const [sel, setSel] = React.useState(null);
    React.useEffect(() => {
      if (open) {
        setStep("select");
        const firstAvail = (record && record.holdings || []).findIndex(h => h.status === "available");
        setSel(firstAvail >= 0 ? firstAvail : null);
      }
    }, [open, record]);
    if (!record) return null;
    const holdings = record.holdings || [];
    const anyAvail = holdings.some(h => h.status === "available");
    const footer = step === "select" ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      onClick: onClose
    }, "\u041E\u0442\u043C\u0435\u043D\u0430"), /*#__PURE__*/React.createElement(Button, {
      disabled: sel === null,
      iconLeft: "chevron-right",
      onClick: () => setStep("confirm")
    }, "\u0414\u0430\u043B\u0435\u0435")) : step === "confirm" ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      onClick: () => setStep("select")
    }, "\u041D\u0430\u0437\u0430\u0434"), /*#__PURE__*/React.createElement(Button, {
      iconLeft: "check",
      onClick: () => {
        onConfirm(holdings[sel]);
        setStep("result");
      }
    }, "\u041F\u043E\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044C \u0437\u0430\u043A\u0430\u0437")) : /*#__PURE__*/React.createElement(Button, {
      onClick: onClose
    }, "\u0413\u043E\u0442\u043E\u0432\u043E");
    return /*#__PURE__*/React.createElement(Dialog, {
      open: open,
      onClose: onClose,
      size: "md",
      title: step === "result" ? "Заказ принят" : "Заказ издания",
      subtitle: step === "result" ? undefined : record.title,
      footer: footer
    }, step === "select" && (!anyAvail ? /*#__PURE__*/React.createElement(Alert, {
      variant: "warning",
      title: "\u041D\u0435\u0442 \u0434\u043E\u0441\u0442\u0443\u043F\u043D\u044B\u0445 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u043E\u0432"
    }, "\u0412\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B \u0441\u0435\u0439\u0447\u0430\u0441 \u0432\u044B\u0434\u0430\u043D\u044B. \u041F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u043F\u043E\u0437\u0436\u0435 \u0438\u043B\u0438 \u043E\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044C \u043A \u0431\u0438\u0431\u043B\u0438\u043E\u0442\u0435\u043A\u0430\u0440\u044E.") : /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)",
        marginBottom: "var(--space-3)"
      }
    }, "\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440 \u0438 \u043C\u0435\u0441\u0442\u043E \u0432\u044B\u0434\u0430\u0447\u0438:"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: 0
      }
    }, holdings.map((h, i) => {
      const ok = h.status === "available";
      return /*#__PURE__*/React.createElement("label", {
        key: i,
        style: {
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          padding: "var(--space-3)",
          borderBottom: "1px solid var(--border-subtle)",
          cursor: ok ? "pointer" : "not-allowed",
          opacity: ok ? 1 : 0.55
        }
      }, /*#__PURE__*/React.createElement(Radio, {
        name: "hold",
        checked: sel === i,
        disabled: !ok,
        onChange: () => setSel(i)
      }), /*#__PURE__*/React.createElement("div", {
        style: {
          flex: 1
        }
      }, /*#__PURE__*/React.createElement("div", {
        style: {
          fontWeight: 600,
          color: "var(--text-strong)",
          fontSize: "var(--text-sm)"
        }
      }, h.location), /*#__PURE__*/React.createElement("div", {
        style: {
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--text-muted)"
        }
      }, h.inventory)), /*#__PURE__*/React.createElement(StatusBadge, {
        status: h.status,
        size: "sm"
      }));
    })))), step === "confirm" && sel !== null && /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-body)",
        lineHeight: 1.6
      }
    }, /*#__PURE__*/React.createElement("p", {
      style: {
        marginBottom: "var(--space-3)"
      }
    }, "\u0411\u0443\u0434\u0435\u0442 \u043E\u0444\u043E\u0440\u043C\u043B\u0435\u043D \u0437\u0430\u043A\u0430\u0437:"), /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-sunken)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-4)",
        display: "grid",
        gridTemplateColumns: "max-content 1fr",
        gap: "8px 16px"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-muted)"
      }
    }, "\u0418\u0437\u0434\u0430\u043D\u0438\u0435"), /*#__PURE__*/React.createElement("b", null, record.title), /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-muted)"
      }
    }, "\u042D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)"
      }
    }, holdings[sel].inventory), /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-muted)"
      }
    }, "\u041C\u0435\u0441\u0442\u043E \u0432\u044B\u0434\u0430\u0447\u0438"), /*#__PURE__*/React.createElement("span", null, holdings[sel].location)), /*#__PURE__*/React.createElement("p", {
      style: {
        marginTop: "var(--space-3)",
        color: "var(--text-muted)"
      }
    }, "\u042D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440 \u0431\u0443\u0434\u0435\u0442 \u043F\u043E\u0441\u0442\u0430\u0432\u043B\u0435\u043D \u0432 \u043E\u0447\u0435\u0440\u0435\u0434\u044C \u0432\u044B\u0434\u0430\u0447\u0438. \u0417\u0430\u043A\u0430\u0437 \u043F\u043E\u044F\u0432\u0438\u0442\u0441\u044F \u0432 \u043B\u0438\u0447\u043D\u043E\u043C \u043A\u0430\u0431\u0438\u043D\u0435\u0442\u0435.")), step === "result" && /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "center",
        padding: "var(--space-4) 0"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: "inline-flex",
        width: 56,
        height: 56,
        borderRadius: "var(--radius-round)",
        background: "var(--success-bg)",
        color: "var(--status-available)",
        alignItems: "center",
        justifyContent: "center",
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "check-circle",
      size: 30
    })), /*#__PURE__*/React.createElement("h3", {
      style: {
        fontSize: "var(--text-lg)",
        marginBottom: "var(--space-2)"
      }
    }, "\u0417\u0430\u043A\u0430\u0437 \u043F\u0440\u0438\u043D\u044F\u0442 \u0438 \u043F\u043E\u0441\u0442\u0430\u0432\u043B\u0435\u043D \u0432 \u043E\u0447\u0435\u0440\u0435\u0434\u044C"), /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u042D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440 ", /*#__PURE__*/React.createElement("b", {
      style: {
        fontFamily: "var(--font-mono)"
      }
    }, sel !== null ? holdings[sel].inventory : ""), " \u043E\u0436\u0438\u0434\u0430\u0435\u0442 \u0432 \xAB", sel !== null ? holdings[sel].location : "", "\xBB. \u0421\u0442\u0430\u0442\u0443\u0441 \u0437\u0430\u043A\u0430\u0437\u0430 \u0432\u0438\u0434\u0435\u043D \u0432 \u043B\u0438\u0447\u043D\u043E\u043C \u043A\u0430\u0431\u0438\u043D\u0435\u0442\u0435.")));
  }
  Object.assign(window, {
    OrderModal
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/OrderModal.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/RecordScreen.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    Badge,
    SubjectTag,
    HoldingsTable,
    PftBlock,
    Alert,
    Tabs
  } = NS;
  const KIND_NOTE = {
    pdf: "документ pdf-формата",
    image: "изображение",
    djvu: "документ djvu-формата"
  };
  function SectionLabel({
    children
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-2xs)",
        textTransform: "uppercase",
        letterSpacing: "var(--tracking-caps)",
        color: "var(--text-subtle)",
        fontWeight: 700,
        marginBottom: "var(--space-3)"
      }
    }, children);
  }

  // Сворачиваемый блок записи (§4, §10) — профили отображения.
  function Collapsible({
    title,
    icon,
    defaultOpen = true,
    count,
    children
  }) {
    const [open, setOpen] = React.useState(defaultOpen);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        marginBottom: "var(--space-3)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => setOpen(o => !o),
      "aria-expanded": open,
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        width: "100%",
        textAlign: "left",
        border: "none",
        background: "transparent",
        cursor: "pointer",
        padding: "var(--space-3) var(--space-4)",
        fontFamily: "var(--font-ui)"
      }
    }, icon && /*#__PURE__*/React.createElement(Icon, {
      name: icon,
      size: 17,
      style: {
        color: "var(--accent)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 700,
        color: "var(--text-strong)",
        fontSize: "var(--text-md)"
      }
    }, title), count != null && /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, "\xB7 ", count), /*#__PURE__*/React.createElement(Icon, {
      name: "chevron-down",
      size: 18,
      style: {
        marginLeft: "auto",
        color: "var(--text-subtle)",
        transform: open ? "rotate(180deg)" : "none",
        transition: "transform var(--dur) var(--ease-standard)"
      }
    })), open && /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "0 var(--space-4) var(--space-4)"
      }
    }, children));
  }

  // Закладки записи: Экземпляры / Электронные версии / Сиглы (§4)
  function RecordTabs({
    record,
    files,
    account,
    onOpenFile,
    onOrder
  }) {
    const tabsDef = [{
      id: "holdings",
      label: "Экземпляры",
      icon: "archive",
      count: record.holdings.length
    }, {
      id: "files",
      label: "Электронные версии",
      icon: "file-text",
      count: files.length
    }, {
      id: "sigla",
      label: "Сиглы хранения",
      icon: "map-pin",
      count: (record.sigla || []).length
    }].filter(t => t.count > 0 || t.id === "holdings");
    const [tab, setTab] = React.useState(tabsDef[0].id);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "var(--space-3) var(--space-4) 0"
      }
    }, /*#__PURE__*/React.createElement(Tabs, {
      value: tab,
      onChange: setTab,
      tabs: tabsDef.map(t => ({
        id: t.id,
        label: t.label,
        count: t.count
      }))
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "var(--space-4)"
      }
    }, tab === "holdings" && (record.holdings.length > 0 ? /*#__PURE__*/React.createElement(HoldingsTable, {
      holdings: record.holdings,
      onOrder: onOrder
    }) : /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)",
        margin: 0
      }
    }, "\u0421\u0432\u0435\u0434\u0435\u043D\u0438\u044F \u043E\u0431 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u0430\u0445 \u043E\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044E\u0442.")), tab === "files" && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, files.length > 0 ? files.map((f, i) => /*#__PURE__*/React.createElement(FileRow, {
      key: i,
      file: f,
      account: account,
      onOpen: onOpenFile
    })) : /*#__PURE__*/React.createElement("p", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)",
        margin: 0
      }
    }, "\u042D\u043B\u0435\u043A\u0442\u0440\u043E\u043D\u043D\u044B\u0445 \u0432\u0435\u0440\u0441\u0438\u0439 \u043D\u0435\u0442."), files.some(f => f.requiresAuth && !account.loggedIn) && /*#__PURE__*/React.createElement(Alert, {
      variant: "info",
      title: "\u0427\u0430\u0441\u0442\u044C \u043C\u0430\u0442\u0435\u0440\u0438\u0430\u043B\u043E\u0432 \u2014 \u043F\u043E \u0432\u0445\u043E\u0434\u0443"
    }, "\u0414\u043E\u0441\u0442\u0443\u043F\u043D\u043E \u0432 \u0447\u0438\u0442\u0430\u043B\u044C\u043D\u043E\u043C \u0437\u0430\u043B\u0435 \u0438\u043B\u0438 \u043F\u043E\u0441\u043B\u0435 \u0432\u0445\u043E\u0434\u0430 \u043F\u043E \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044C\u0441\u043A\u043E\u043C\u0443 \u0431\u0438\u043B\u0435\u0442\u0443.")), tab === "sigla" && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, (record.sigla || []).map(s => /*#__PURE__*/React.createElement("div", {
      key: s.code,
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "10px 12px",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        background: s.here ? "var(--accent-weak)" : "transparent"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)",
        fontWeight: 700,
        fontSize: "var(--text-sm)",
        color: s.here ? "var(--accent-press)" : "var(--text-strong)",
        minWidth: 64
      }
    }, s.code), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        fontSize: "var(--text-sm)",
        color: "var(--text-body)"
      }
    }, s.name), s.here && /*#__PURE__*/React.createElement(Badge, {
      variant: "accent"
    }, "\u0437\u0434\u0435\u0441\u044C"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, "\u044D\u043A\u0437.: ", s.count))))));
  }
  function Cover({
    tint,
    noImg,
    onOpen
  }) {
    return /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onOpen,
      style: {
        width: "100%",
        aspectRatio: "3 / 4",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        border: "1px solid var(--border-subtle)",
        cursor: onOpen ? "pointer" : "default",
        padding: 0,
        background: noImg ? "var(--surface-sunken)" : "hsl(" + (tint || 30) + " 32% 86%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      },
      "aria-label": "\u041E\u0442\u043A\u0440\u044B\u0442\u044C \u0438\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0435"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: noImg ? "file-text" : "image",
      size: 40,
      style: {
        color: noImg ? "var(--text-subtle)" : "hsl(" + (tint || 30) + " 38% 42%)"
      }
    }));
  }

  // Кнопка просмотра файла (view-only). 955 раньше 951 — задаёт порядок в files.
  function FileRow({
    file,
    account,
    onOpen
  }) {
    const locked = file.requiresAuth && !account.loggedIn;
    return /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onOpen(file),
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        width: "100%",
        textAlign: "left",
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-4)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 34,
        height: 34,
        borderRadius: "var(--radius-sm)",
        background: "var(--accent-weak)",
        color: "var(--accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: file.kind === "image" ? "image" : "file-text",
      size: 18
    })), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, file.label), /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, KIND_NOTE[file.kind] || file.kind, file.pages ? " · " + file.pages + " с." : "", " \xB7 \u043F\u043E\u043B\u0435 ", file.field, " \xB7 \u0442\u043E\u043B\u044C\u043A\u043E \u043F\u0440\u043E\u0441\u043C\u043E\u0442\u0440")), locked ? /*#__PURE__*/React.createElement(Badge, {
      variant: "neutral"
    }, "\u043D\u0443\u0436\u0435\u043D \u0432\u0445\u043E\u0434") : /*#__PURE__*/React.createElement("span", {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        color: "var(--accent)",
        fontSize: "var(--text-sm)",
        fontWeight: 600
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "eye",
      size: 16
    }), " \u041E\u0442\u043A\u0440\u044B\u0442\u044C"));
  }
  function RecordScreen(props) {
    const {
      record,
      db,
      onBack,
      onSubject,
      onOrder,
      onToggleMark,
      marked,
      account,
      noImg,
      onToast,
      onOpenFile,
      onFollowLink,
      pickFile
    } = props;
    const isImage = db.layout === "gallery";
    const links = record.links || {};
    const files = (record.files || []).slice().sort((a, b) => (a.priority || 9) - (b.priority || 9));
    const cover = pickFile(files.filter(f => f.kind === "image"));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1000,
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        marginBottom: "var(--space-4)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onBack,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        padding: 0
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left",
      size: 17
    }), " \u041D\u0430\u0437\u0430\u0434 \u043A \u0440\u0435\u0437\u0443\u043B\u044C\u0442\u0430\u0442\u0430\u043C"), /*#__PURE__*/React.createElement("span", {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)",
        marginLeft: "auto"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: db.icon,
      size: 14
    }), " \u0411\u0430\u0437\u0430: ", /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-muted)",
        fontWeight: 600
      }
    }, db.name))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: isImage ? "240px 1fr" : "1fr",
        gap: "var(--space-8)",
        alignItems: "start"
      }
    }, isImage && /*#__PURE__*/React.createElement("div", {
      style: {
        position: "sticky",
        top: 76
      }
    }, /*#__PURE__*/React.createElement(Cover, {
      tint: record.tint,
      noImg: noImg,
      onOpen: cover ? () => onOpenFile(cover) : undefined
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: 8,
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)",
        textAlign: "center"
      }
    }, noImg ? "Изображение скрыто (режим без изображений)" : cover ? "Нажмите для просмотра" : "Превью")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        marginBottom: "var(--space-3)"
      }
    }, (record.badges || []).map((b, i) => /*#__PURE__*/React.createElement(Badge, {
      key: i,
      variant: b.variant
    }, b.text))), /*#__PURE__*/React.createElement("h1", {
      style: {
        fontFamily: "var(--font-record-title)",
        fontSize: "var(--text-2xl)",
        marginBottom: "var(--space-2)"
      }
    }, record.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-md)",
        color: "var(--text-muted)",
        marginBottom: "var(--space-5)"
      }
    }, record.author && record.author !== "—" ? record.author + " · " : "", record.imprint.publisher !== "—" ? record.imprint.publisher + ", " : "", record.imprint.year), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: "var(--space-2)",
        flexWrap: "wrap",
        marginBottom: "var(--space-6)"
      }
    }, record.holdings && record.holdings.length > 0 && /*#__PURE__*/React.createElement(Button, {
      iconLeft: "bookmark",
      onClick: onOrder
    }, "\u0417\u0430\u043A\u0430\u0437\u0430\u0442\u044C / \u0437\u0430\u0431\u0440\u043E\u043D\u0438\u0440\u043E\u0432\u0430\u0442\u044C"), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      iconLeft: marked ? "bookmark-check" : "bookmark",
      onClick: onToggleMark
    }, marked ? "Отмечено" : "Отметить"), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      iconLeft: "link",
      onClick: () => onToast({
        variant: "info",
        title: "Ссылка скопирована",
        message: "Доступна внутри сети библиотеки."
      })
    }, "\u041F\u043E\u0434\u0435\u043B\u0438\u0442\u044C\u0441\u044F \u0441\u0441\u044B\u043B\u043A\u043E\u0439"), links.f481 && links.f481.length > 0 && /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      iconLeft: "search",
      onClick: () => onSubject(record.title.split(":")[0])
    }, "\u041F\u043E\u0438\u0441\u043A \u043F\u043E \u0441\u0432\u044F\u0437\u0438 (481)")), (links.f488 || links.f390) && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)",
        marginBottom: "var(--space-6)"
      }
    }, links.f488 && /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onFollowLink(links.f488),
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        alignSelf: "flex-start",
        background: "var(--surface-sunken)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
        padding: "9px 14px",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: "var(--text-strong)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "archive",
      size: 16,
      style: {
        color: "var(--accent)"
      }
    }), " ", links.f488.label, " ", /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-right",
      size: 15,
      style: {
        color: "var(--text-subtle)"
      }
    })), links.f390 && /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onFollowLink(links.f390),
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        alignSelf: "flex-start",
        background: "none",
        border: "none",
        padding: 0,
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: "var(--text-link)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "external-link",
      size: 15
    }), " ", links.f390.label)), /*#__PURE__*/React.createElement(Collapsible, {
      title: "\u041E\u043F\u0438\u0441\u0430\u043D\u0438\u0435 \u0438 \u0430\u043D\u043D\u043E\u0442\u0430\u0446\u0438\u044F",
      icon: "file-text",
      defaultOpen: true
    }, /*#__PURE__*/React.createElement(PftBlock, {
      html: record.pftHtml
    })), record.subjects && record.subjects.length > 0 && /*#__PURE__*/React.createElement(Collapsible, {
      title: "\u041F\u0440\u0435\u0434\u043C\u0435\u0442\u043D\u044B\u0435 \u0440\u0443\u0431\u0440\u0438\u043A\u0438",
      icon: "tag",
      count: record.subjects.length,
      defaultOpen: true
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: 8
      }
    }, record.subjects.map(s => /*#__PURE__*/React.createElement(SubjectTag, {
      key: s,
      onClick: () => onSubject(s)
    }, s)))), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-2)"
      }
    }, /*#__PURE__*/React.createElement(RecordTabs, {
      record: record,
      files: files,
      account: account,
      onOpenFile: onOpenFile,
      onOrder: onOrder
    })))));
  }
  Object.assign(window, {
    RecordScreen
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/RecordScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/ResultsScreen.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    IconButton,
    Select,
    Checkbox,
    Switch,
    Input,
    FilterChip,
    ResultCard,
    StatusBadge,
    Tabs,
    Pagination,
    SkeletonResult,
    EmptyState
  } = NS;
  const SearchModes = NS.SearchModes;
  const TreeNav = NS.TreeNav;
  const SORTS = ["По релевантности", "По году ↓", "По году ↑", "По месту хранения", "По рубрикам"];

  // ---- Конструктор расширенного / комплексного поиска ----
  function QueryBuilder({
    db,
    rows,
    setRows,
    trunc,
    setTrunc,
    onSearch,
    onReset,
    complex
  }) {
    const setRow = (i, patch) => setRows(rows.map((r, j) => j === i ? {
      ...r,
      ...patch
    } : r));
    const addRow = () => setRows([...rows, {
      op: "and",
      field: db.searchFields[0].code,
      qual: "contains",
      value: ""
    }]);
    const delRow = i => setRows(rows.filter((_, j) => j !== i));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: complex ? "layers" : "sliders",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("h2", {
      style: {
        fontSize: "var(--text-lg)"
      }
    }, complex ? "Комплексный поиск" : "Расширенный поиск", " \xB7 ", db.name)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)"
      }
    }, rows.map((r, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        display: "grid",
        gridTemplateColumns: "84px 1fr 150px 1fr 40px",
        gap: "var(--space-2)",
        alignItems: "center"
      }
    }, i === 0 ? /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-subtle)",
        paddingLeft: 4
      }
    }, "\u0413\u0434\u0435") : /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      value: r.op,
      onChange: e => setRow(i, {
        op: e.target.value
      }),
      options: [{
        value: "and",
        label: "И"
      }, {
        value: "or",
        label: "ИЛИ"
      }, {
        value: "not",
        label: "НЕ"
      }]
    }), /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      value: r.field,
      onChange: e => setRow(i, {
        field: e.target.value
      }),
      options: db.searchFields.map(f => ({
        value: f.code,
        label: f.label
      }))
    }), /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      value: r.qual,
      onChange: e => setRow(i, {
        qual: e.target.value
      }),
      options: [{
        value: "contains",
        label: "содержит"
      }, {
        value: "starts",
        label: "начинается с"
      }, {
        value: "exact",
        label: "совпадает"
      }]
    }), /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      value: r.value,
      placeholder: "\u0437\u043D\u0430\u0447\u0435\u043D\u0438\u0435",
      onChange: e => setRow(i, {
        value: e.target.value
      })
    }), /*#__PURE__*/React.createElement(IconButton, {
      icon: "x",
      label: "\u0423\u0434\u0430\u043B\u0438\u0442\u044C \u0441\u0442\u0440\u043E\u043A\u0443",
      size: "sm",
      onClick: () => delRow(i),
      disabled: rows.length === 1
    })))), complex && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: "var(--space-3)",
        marginTop: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u0413\u043E\u0434 \u0438\u0437\u0434\u0430\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8,
        marginTop: 5
      }
    }, /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      placeholder: "\u0441"
    }), /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      placeholder: "\u043F\u043E"
    }))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u042F\u0437\u044B\u043A \u043F\u0443\u0431\u043B\u0438\u043A\u0430\u0446\u0438\u0438"), /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      options: ["— любой —", "русский", "английский", "французский"]
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u0412\u0438\u0434 \u0434\u043E\u043A\u0443\u043C\u0435\u043D\u0442\u0430"), /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      options: ["— любой —", "Книга", "Сборник", "Многотомник"]
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-4)",
        marginTop: "var(--space-4)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      size: "sm",
      iconLeft: "plus",
      onClick: addRow
    }, "\u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C \u0443\u0441\u043B\u043E\u0432\u0438\u0435"), /*#__PURE__*/React.createElement(Switch, {
      label: "\u0423\u0441\u0435\u0447\u0435\u043D\u0438\u0435 (*)",
      checked: trunc,
      onChange: e => setTrunc(e.target.checked)
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "lg",
      iconLeft: "rotate-ccw",
      onClick: onReset
    }, "\u0421\u0431\u0440\u043E\u0441"), /*#__PURE__*/React.createElement(Button, {
      size: "lg",
      iconLeft: "search",
      onClick: onSearch
    }, "\u041F\u043E\u0438\u0441\u043A")));
  }

  // ---- Левая колонка: режимы + словарь + фильтры ----
  function LeftRail({
    formDb,
    multiBase,
    mode,
    setMode,
    availableModes,
    dictionary,
    filters,
    setFilter,
    dateFrom,
    dateTo,
    setDate,
    facetSource,
    navCode,
    setNav
  }) {
    const Hd = ({
      children
    }) => /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-2xs)",
        textTransform: "uppercase",
        letterSpacing: "var(--tracking-caps)",
        color: "var(--text-subtle)",
        fontWeight: 700,
        marginBottom: 10
      }
    }, children);
    const facetCount = opt => (facetSource || []).filter(r => r.docType === opt || (r.fields || []).some(f => f.value === opt)).length;
    return /*#__PURE__*/React.createElement("aside", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-6)"
      }
    }, SearchModes && /*#__PURE__*/React.createElement(SearchModes, {
      modes: availableModes,
      value: mode,
      onChange: setMode,
      labels: formDb && formDb.modes && formDb.modes.includes("special") ? {
        special: "Спецформа базы"
      } : {}
    }), multiBase ? /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)",
        background: "var(--surface-sunken)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "info",
      size: 15,
      style: {
        verticalAlign: "-2px",
        marginRight: 6,
        color: "var(--text-subtle)"
      }
    }), "\u0421\u043B\u043E\u0432\u0430\u0440\u044C \u0438 \u0444\u0438\u043B\u044C\u0442\u0440\u044B \u0434\u043E\u0441\u0442\u0443\u043F\u043D\u044B \u043F\u0440\u0438 \u043F\u043E\u0438\u0441\u043A\u0435 \u0432 \u043E\u0434\u043D\u043E\u0439 \u0431\u0430\u0437\u0435. \u0421\u0435\u0439\u0447\u0430\u0441 \u0432\u044B\u0431\u0440\u0430\u043D\u043E \u043D\u0435\u0441\u043A\u043E\u043B\u044C\u043A\u043E \u0431\u0430\u0437.") : /*#__PURE__*/React.createElement(React.Fragment, null, formDb && formDb.navigators && TreeNav && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Hd, null, "\u041D\u0430\u0432\u0438\u0433\u0430\u0442\u043E\u0440 \xB7 \u043A\u043B\u0430\u0441\u0441\u0438\u0444\u0438\u043A\u0430\u0442\u043E\u0440\u044B"), /*#__PURE__*/React.createElement(TreeNav, {
      navigators: formDb.navigators,
      value: navCode,
      onPick: node => setNav(node || null)
    })), dictionary.length > 0 && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Hd, null, "\u0421\u043B\u043E\u0432\u0430\u0440\u044C \xB7 \u0443\u0442\u043E\u0447\u043D\u0438\u0442\u0435"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: 6
      }
    }, dictionary.map(t => /*#__PURE__*/React.createElement(FilterChip, {
      key: t.term,
      label: t.term,
      count: t.count,
      pressed: !!filters["dict:" + t.term],
      onToggle: () => setFilter("dict:" + t.term, !filters["dict:" + t.term])
    })))), formDb && formDb.dateRange && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Hd, null, "\u0414\u0438\u0430\u043F\u0430\u0437\u043E\u043D \u0434\u0430\u0442 \xB7 \u043F\u043E\u043B\u0435 122"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8
      }
    }, /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      placeholder: "\u0441 (\u0433\u043E\u0434)",
      value: dateFrom,
      onChange: e => setDate("from", e.target.value)
    }), /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      placeholder: "\u043F\u043E (\u0433\u043E\u0434)",
      value: dateTo,
      onChange: e => setDate("to", e.target.value)
    }))), (formDb ? formDb.filters : []).map(g => /*#__PURE__*/React.createElement("div", {
      key: g.id
    }, /*#__PURE__*/React.createElement(Hd, null, g.label), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: 9
      }
    }, g.options.map(opt => {
      const key = g.id + ":" + opt;
      const c = facetCount(opt);
      return /*#__PURE__*/React.createElement("div", {
        key: opt,
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8
        }
      }, /*#__PURE__*/React.createElement(Checkbox, {
        label: opt,
        checked: !!filters[key],
        onChange: () => setFilter(key, !filters[key])
      }), c > 0 && /*#__PURE__*/React.createElement("span", {
        style: {
          marginLeft: "auto",
          fontSize: "var(--text-2xs)",
          color: "var(--text-subtle)",
          fontVariantNumeric: "tabular-nums",
          background: "var(--surface-sunken)",
          borderRadius: "var(--radius-pill)",
          padding: "1px 7px"
        }
      }, c));
    }))))));
  }

  // ---- Галерея (изобразительные базы) ----
  function GalleryGrid({
    items,
    marked,
    toggleMark,
    onOpen,
    noImg,
    multiBase
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
        gap: "var(--space-3)"
      }
    }, items.map(it => /*#__PURE__*/React.createElement("article", {
      key: it.sourceDb + it.mfn,
      style: {
        background: "var(--surface-card)",
        border: "1px solid " + (marked.has(it.mfn) ? "var(--accent-weak-border)" : "var(--border-subtle)"),
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onOpen(it),
      style: {
        border: "none",
        padding: 0,
        cursor: "pointer",
        height: 130,
        position: "relative",
        background: noImg ? "var(--surface-sunken)" : "hsl(" + (it.tint || 30) + " 32% 86%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      },
      "aria-label": "Открыть: " + it.title
    }, /*#__PURE__*/React.createElement(Icon, {
      name: noImg ? "file-text" : "image",
      size: 30,
      style: {
        color: noImg ? "var(--text-subtle)" : "hsl(" + (it.tint || 30) + " 38% 42%)"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        position: "absolute",
        top: 8,
        left: 8
      }
    }, /*#__PURE__*/React.createElement("span", {
      onClick: e => {
        e.stopPropagation();
        toggleMark(it.mfn);
      },
      style: {
        display: "flex",
        width: 24,
        height: 24,
        borderRadius: "var(--radius-sm)",
        alignItems: "center",
        justifyContent: "center",
        background: marked.has(it.mfn) ? "var(--accent)" : "rgba(255,255,255,.85)",
        color: marked.has(it.mfn) ? "#fff" : "var(--text-muted)"
      }
    }, marked.has(it.mfn) ? /*#__PURE__*/React.createElement(Icon, {
      name: "check",
      size: 15
    }) : /*#__PURE__*/React.createElement(Icon, {
      name: "plus",
      size: 15
    })))), /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        flex: 1
      }
    }, multiBase && /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-2xs)",
        fontWeight: 600,
        color: "var(--accent)"
      }
    }, it.dbShort), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: () => onOpen(it),
      style: {
        border: "none",
        background: "none",
        padding: 0,
        textAlign: "left",
        cursor: "pointer",
        fontFamily: "var(--font-record-title)",
        fontWeight: 600,
        fontSize: "var(--text-sm)",
        color: "var(--text-strong)",
        lineHeight: 1.3
      }
    }, it.title), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, it.author, " \xB7 ", it.year), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "auto",
        paddingTop: 4
      }
    }, /*#__PURE__*/React.createElement(StatusBadge, {
      status: it.availability,
      size: "sm"
    }))))));
  }
  function ResultsScreen(props) {
    const {
      databases,
      groups,
      dbIds,
      setDbIds,
      formDb,
      headDb,
      multiBase,
      query,
      setQuery,
      onSearch,
      mode,
      setMode,
      availableModes,
      loading,
      items,
      total,
      page,
      setPage,
      pageSize,
      setPageSize,
      sort,
      setSort,
      view,
      setView,
      marked,
      toggleMark,
      clearMarked,
      onOrderMarked,
      filters,
      setFilter,
      activeChips,
      removeChip,
      clearAll,
      advRows,
      setAdvRows,
      trunc,
      setTrunc,
      runAdvanced,
      special,
      setSpecial,
      runSpecial,
      resetSpecial,
      onlyDigital,
      setOnlyDigital,
      dictionary,
      dateFrom,
      dateTo,
      setDate,
      onOpenRecord,
      noImg,
      suggestions,
      allItems
    } = props;
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const galleryLayout = headDb && headDb.layout === "gallery" && !multiBase;
    const resetAdv = () => setAdvRows([{
      op: "and",
      field: (formDb || databases[0]).searchFields[0].code,
      qual: "contains",
      value: ""
    }]);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: "var(--container-max)",
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "260px 1fr",
        gap: "var(--space-3)",
        alignItems: "start",
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(NS.DatabaseSelector, {
      databases: databases,
      groups: groups,
      value: dbIds,
      onChange: setDbIds
    }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("label", {
      style: {
        display: "block",
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        color: "var(--text-muted)",
        marginBottom: 5
      }
    }, "\u042F \u0438\u0449\u0443:"), /*#__PURE__*/React.createElement(NS.SearchBar, {
      value: query,
      onChange: setQuery,
      onSearch: onSearch,
      suggestions: suggestions,
      buttonLabel: "\u041F\u043E\u0438\u0441\u043A",
      onReset: () => {
        setQuery("");
        onSearch("");
      },
      onPickSuggestion: sug => {
        setQuery(sug.term || sug);
        onSearch(sug.term || sug);
      }
    }), formDb && formDb.simpleExtra && mode === "simple" && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: 9
      }
    }, /*#__PURE__*/React.createElement(Checkbox, {
      label: formDb.simpleExtra.label,
      checked: onlyDigital,
      onChange: e => {
        setOnlyDigital(e.target.checked);
      }
    })))), mode === "advanced" && formDb && /*#__PURE__*/React.createElement(QueryBuilder, {
      db: formDb,
      rows: advRows,
      setRows: setAdvRows,
      trunc: trunc,
      setTrunc: setTrunc,
      onSearch: runAdvanced,
      onReset: resetAdv
    }), mode === "complex" && formDb && /*#__PURE__*/React.createElement(QueryBuilder, {
      db: formDb,
      rows: advRows,
      setRows: setAdvRows,
      trunc: trunc,
      setTrunc: setTrunc,
      onSearch: runAdvanced,
      onReset: resetAdv,
      complex: true
    }), mode === "special" && formDb && window.SpecialForm && /*#__PURE__*/React.createElement(window.SpecialForm, {
      db: formDb,
      values: special,
      setValues: setSpecial,
      onSearch: runSpecial,
      onReset: resetSpecial
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "var(--rail-filters) 1fr",
        gap: "var(--space-6)",
        alignItems: "start"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        position: "sticky",
        top: 76
      },
      className: "irbis-rail"
    }, /*#__PURE__*/React.createElement(LeftRail, {
      formDb: formDb,
      multiBase: multiBase,
      mode: mode,
      setMode: setMode,
      availableModes: availableModes,
      dictionary: dictionary,
      filters: filters,
      setFilter: setFilter,
      dateFrom: dateFrom,
      dateTo: dateTo,
      setDate: setDate,
      facetSource: allItems,
      navCode: (Object.keys(filters).find(k => k.indexOf("nav:") === 0) || "").slice(4) || null,
      setNav: node => {
        Object.keys(filters).forEach(k => {
          if (k.indexOf("nav:") === 0) setFilter(k, false);
        });
        if (node) setFilter("nav:" + node.code, node.label + (node.code ? " (" + node.code + ")" : ""));
      }
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        flexWrap: "wrap",
        marginBottom: "var(--space-3)"
      }
    }, multiBase && /*#__PURE__*/React.createElement("span", {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        color: "var(--accent)",
        background: "var(--accent-weak)",
        border: "1px solid var(--accent-weak-border)",
        borderRadius: "var(--radius-pill)",
        padding: "3px 10px"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "layers",
      size: 13
    }), " \u041F\u043E\u0438\u0441\u043A \u043F\u043E ", dbIds.length, " \u0431\u0430\u0437\u0430\u043C"), !loading && total > 0 && /*#__PURE__*/React.createElement(Pagination, {
      compact: true,
      page: page,
      pageCount: pageCount,
      total: total,
      onPage: setPage
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), galleryLayout && /*#__PURE__*/React.createElement(Tabs, {
      variant: "pill",
      value: view,
      onChange: setView,
      tabs: [{
        id: "gallery",
        label: "Галерея",
        icon: "grid"
      }, {
        id: "list",
        label: "Список",
        icon: "list"
      }]
    }), /*#__PURE__*/React.createElement(Select, {
      size: "sm",
      value: sort,
      onChange: e => setSort(e.target.value),
      options: SORTS,
      "aria-label": "\u0421\u043E\u0440\u0442\u0438\u0440\u043E\u0432\u043A\u0430"
    })), activeChips.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        alignItems: "center",
        marginBottom: "var(--space-4)"
      }
    }, activeChips.map(c => /*#__PURE__*/React.createElement(FilterChip, {
      key: c.key,
      group: c.group,
      label: c.label,
      onRemove: () => removeChip(c.key)
    })), /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: clearAll,
      style: {
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontSize: "var(--text-sm)",
        fontFamily: "var(--font-ui)",
        fontWeight: 500
      }
    }, "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C \u0432\u0441\u0435")), marked.size > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "10px 14px",
        background: "var(--accent-weak)",
        border: "1px solid var(--accent-weak-border)",
        borderRadius: "var(--radius-md)",
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "check-circle",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: "var(--accent-press)"
      }
    }, "\u041E\u0442\u043C\u0435\u0447\u0435\u043D\u043E: ", marked.size), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "secondary",
      iconLeft: "bookmark",
      onClick: onOrderMarked
    }, "\u0417\u0430\u043A\u0430\u0437\u0430\u0442\u044C \u043E\u0442\u043C\u0435\u0447\u0435\u043D\u043D\u044B\u0435"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: clearMarked
    }, "\u0421\u043D\u044F\u0442\u044C \u0432\u0441\u0435 \u043E\u0442\u043C\u0435\u0442\u043A\u0438")), loading ? /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, Array.from({
      length: 5
    }).map((_, i) => /*#__PURE__*/React.createElement(SkeletonResult, {
      key: i,
      showThumb: galleryLayout
    }))) : items.length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
      title: "\u041D\u0438\u0447\u0435\u0433\u043E \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E",
      description: "По запросу «" + query + "» записей нет.",
      hints: ["Уберите часть условий или фильтров", "Включите усечение в расширенном поиске", "Проверьте раскладку клавиатуры", "Добавьте базы в селекторе"],
      action: /*#__PURE__*/React.createElement(Button, {
        variant: "secondary",
        iconLeft: "rotate-ccw",
        onClick: clearAll
      }, "\u0421\u0431\u0440\u043E\u0441\u0438\u0442\u044C \u0444\u0438\u043B\u044C\u0442\u0440\u044B")
    }) : galleryLayout && view === "gallery" ? /*#__PURE__*/React.createElement(GalleryGrid, {
      items: items,
      marked: marked,
      toggleMark: toggleMark,
      onOpen: onOpenRecord,
      noImg: noImg,
      multiBase: multiBase
    }) : /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, items.map(it => /*#__PURE__*/React.createElement(ResultCard, {
      key: it.sourceDb + it.mfn,
      item: it,
      checked: marked.has(it.mfn),
      onToggleCheck: () => toggleMark(it.mfn),
      onOpen: () => onOpenRecord(it),
      showThumb: headDb && headDb.layout === "gallery",
      typeIcon: (it.sourceDb && databases.find(d => d.id === it.sourceDb) || {}).typeIcon || "book",
      dbTag: multiBase ? it.dbShort : null
    }))), !loading && items.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement(Pagination, {
      page: page,
      pageCount: pageCount,
      total: total,
      onPage: setPage,
      pageSize: pageSize,
      onPageSize: setPageSize
    })))));
  }
  Object.assign(window, {
    ResultsScreen
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/ResultsScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/SeasonalFX.jsx
try { (() => {
/* global React */
/* ============================================================
   SeasonalFX — декоративный оверлей для сезонных тем.
   «Новый год»  → стеатральная золотая гирлянда (мерцает) + снег + лёгкая дымка софита.
   «8 марта»    → тёплый сценический софит + падающие лепестки роз и мимозы.
   Оверлей всегда pointer-events:none, лежит НИЖЕ модалок/тостов (z=150),
   уважает prefers-reduced-motion (падение отключается, статичная сцена остаётся).
   Чистая декорация — на смысл/доступность контента не влияет (aria-hidden).
   ============================================================ */
(function () {
  // детерминированный «рандом», чтобы частицы не прыгали при ре-рендере
  function rng(seed) {
    let s = seed % 2147483647;
    if (s <= 0) s += 2147483646;
    return () => (s = s * 16807 % 2147483647) / 2147483647;
  }
  const FX_CSS = `
  @keyframes irbisFall {
    0%   { transform: translate3d(0,-12vh,0) rotate(0deg); }
    100% { transform: translate3d(var(--drift,0px),112vh,0) rotate(var(--spin,360deg)); }
  }
  @keyframes irbisSway {
    0%,100% { margin-left: -14px; }
    50%     { margin-left: 14px; }
  }
  @keyframes irbisTwinkle {
    0%,100% { opacity: .35; filter: brightness(.8); }
    50%     { opacity: 1;   filter: brightness(1.35); }
  }
  @keyframes irbisGlow {
    0%,100% { opacity: .55; transform: scale(1); }
    50%     { opacity: .85; transform: scale(1.06); }
  }
  .irbis-fx-fall { position:absolute; top:0; will-change: transform; animation: irbisFall linear infinite; }
  .irbis-fx-fall > i { display:block; animation: irbisSway ease-in-out infinite; }
  .irbis-fx-bulb { animation: irbisTwinkle ease-in-out infinite; transform-origin:center; }
  .irbis-fx-glow { animation: irbisGlow ease-in-out infinite; }
  @media (prefers-reduced-motion: reduce) {
    .irbis-fx-fall { display:none !important; }
    .irbis-fx-bulb, .irbis-fx-glow { animation: none !important; opacity:.8 !important; }
  }`;

  // ---- Снег (Новый год) ----
  function makeSnow() {
    const r = rng(7);
    return Array.from({
      length: 44
    }, (_, i) => {
      const size = 3 + r() * 9;
      const depth = r();
      return {
        id: i,
        left: r() * 100,
        size,
        dur: 9 + r() * 12,
        delay: -r() * 16,
        drift: (r() * 2 - 1) * 90,
        spin: (r() * 2 - 1) * 200,
        sway: 5 + r() * 6,
        opacity: 0.45 + depth * 0.5,
        blur: depth < 0.3 ? 1.2 : 0,
        star: r() > 0.78
      };
    });
  }

  // ---- Лепестки (8 марта) ----
  function makePetals() {
    const r = rng(23);
    const palette = ["#E27FA0", "#D85F86", "#EEAEC4", "#C44C70"];
    return Array.from({
      length: 30
    }, (_, i) => {
      const mimosa = r() > 0.74;
      const size = mimosa ? 7 + r() * 5 : 11 + r() * 12;
      const depth = r();
      return {
        id: i,
        left: r() * 100,
        size,
        dur: 8 + r() * 9,
        delay: -r() * 14,
        drift: (r() * 2 - 1) * 130,
        spin: (r() * 2 - 1) * 420,
        sway: 7 + r() * 8,
        opacity: 0.6 + depth * 0.4,
        mimosa,
        color: mimosa ? "#E3B100" : palette[i % palette.length],
        blur: depth < 0.28 ? 1 : 0
      };
    });
  }

  // Гирлянда: провисающая SVG-нить с мерцающими лампочками (театральная маркиза)
  function Garland() {
    const segs = 16;
    const W = 1200;
    const sag = 30;
    const step = W / segs;
    const pts = [];
    let d = "M 0 6";
    for (let i = 0; i < segs; i++) {
      const x0 = i * step;
      const x1 = (i + 1) * step;
      const cx = (x0 + x1) / 2;
      d += ` Q ${cx} ${6 + sag} ${x1} 6`;
      pts.push({
        x: cx,
        y: 6 + sag * 0.92
      });
    }
    const warm = ["#E6CB86", "#C8A24A", "#FBEFC9", "#D8A93F"];
    return /*#__PURE__*/React.createElement("svg", {
      viewBox: `0 0 ${W} 44`,
      preserveAspectRatio: "none",
      width: "100%",
      height: "44",
      style: {
        position: "absolute",
        top: 0,
        left: 0,
        display: "block"
      },
      "aria-hidden": "true"
    }, /*#__PURE__*/React.createElement("path", {
      d: d,
      fill: "none",
      stroke: "#6E5A2E",
      strokeWidth: "1.4",
      opacity: "0.55"
    }), pts.map((p, i) => /*#__PURE__*/React.createElement("g", {
      key: i,
      className: "irbis-fx-bulb",
      style: {
        animationDuration: `${1.6 + i % 5 * 0.35}s`,
        animationDelay: `${i % 7 * 0.22}s`
      }
    }, /*#__PURE__*/React.createElement("line", {
      x1: p.x,
      y1: p.y - 7,
      x2: p.x,
      y2: p.y - 1,
      stroke: "#6E5A2E",
      strokeWidth: "1.2",
      opacity: "0.6"
    }), /*#__PURE__*/React.createElement("circle", {
      cx: p.x,
      cy: p.y + 3,
      r: "5.4",
      fill: warm[i % warm.length]
    }), /*#__PURE__*/React.createElement("circle", {
      cx: p.x,
      cy: p.y + 3,
      r: "9.5",
      fill: warm[i % warm.length],
      opacity: "0.28"
    }))));
  }
  function SeasonalFX({
    theme
  }) {
    const isNY = theme === "newyear";
    const isM8 = theme === "march8";
    const snow = React.useMemo(makeSnow, []);
    const petals = React.useMemo(makePetals, []);
    if (!isNY && !isM8) return null;
    return /*#__PURE__*/React.createElement("div", {
      "aria-hidden": "true",
      style: {
        position: "fixed",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 150
      }
    }, /*#__PURE__*/React.createElement("style", null, FX_CSS), isNY && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "irbis-fx-glow",
      style: {
        position: "absolute",
        top: "-30vh",
        left: "50%",
        width: "120vw",
        height: "70vh",
        transform: "translateX(-50%)",
        animationDuration: "7s",
        background: "radial-gradient(ellipse at center top, rgba(200,162,74,.20), rgba(200,162,74,0) 62%)"
      }
    }), /*#__PURE__*/React.createElement(Garland, null), snow.map(p => /*#__PURE__*/React.createElement("div", {
      key: p.id,
      className: "irbis-fx-fall",
      style: {
        left: p.left + "vw",
        width: p.size,
        height: p.size,
        animationDuration: p.dur + "s",
        animationDelay: p.delay + "s",
        "--drift": p.drift + "px",
        "--spin": p.spin + "deg"
      }
    }, /*#__PURE__*/React.createElement("i", {
      style: {
        width: p.size,
        height: p.size,
        animationDuration: p.sway + "s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#FFFFFF",
        fontSize: p.size + 4,
        lineHeight: 1,
        opacity: p.opacity,
        filter: p.blur ? `blur(${p.blur}px)` : "none",
        textShadow: "0 0 4px rgba(120,150,190,.5)"
      }
    }, p.star ? "❄" : /*#__PURE__*/React.createElement("span", {
      style: {
        width: p.size,
        height: p.size,
        borderRadius: "50%",
        background: "#FFFFFF",
        display: "block",
        boxShadow: "0 0 5px rgba(150,180,220,.6)"
      }
    }))))), isM8 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "irbis-fx-glow",
      style: {
        position: "absolute",
        top: "-28vh",
        left: "50%",
        width: "110vw",
        height: "66vh",
        transform: "translateX(-50%)",
        animationDuration: "8s",
        background: "radial-gradient(ellipse at center top, rgba(227,177,0,.16), rgba(168,50,79,.05) 50%, rgba(0,0,0,0) 68%)"
      }
    }), petals.map(p => /*#__PURE__*/React.createElement("div", {
      key: p.id,
      className: "irbis-fx-fall",
      style: {
        left: p.left + "vw",
        width: p.size,
        height: p.size,
        animationDuration: p.dur + "s",
        animationDelay: p.delay + "s",
        "--drift": p.drift + "px",
        "--spin": p.spin + "deg"
      }
    }, /*#__PURE__*/React.createElement("i", {
      style: {
        width: p.size,
        height: p.size,
        animationDuration: p.sway + "s",
        opacity: p.opacity,
        filter: p.blur ? `blur(${p.blur}px)` : "none",
        background: p.mimosa ? `radial-gradient(circle at 38% 35%, #F6D656, ${p.color})` : `radial-gradient(circle at 32% 28%, rgba(255,255,255,.7), ${p.color} 70%)`,
        borderRadius: p.mimosa ? "50%" : "100% 0 100% 0",
        boxShadow: p.mimosa ? "0 0 4px rgba(227,177,0,.4)" : "0 1px 3px rgba(120,30,60,.18)"
      }
    })))));
  }
  Object.assign(window, {
    SeasonalFX
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/SeasonalFX.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/Shell.jsx
try { (() => {
/* global React */
const NS = window.DesignSystem_d9a584;
function Brand({
  onClick,
  library
}) {
  const lib = library || {
    monogram: "ЭК",
    short: "Электронный каталог",
    tagline: "каталог"
  };
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: onClick,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11,
      background: "none",
      border: "none",
      cursor: "pointer",
      padding: 0,
      color: "var(--accent)",
      textAlign: "left"
    },
    "aria-label": lib.short + " — на главную"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 40,
      height: 40,
      borderRadius: "var(--radius-md)",
      background: "var(--accent)",
      color: "var(--accent-fg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none",
      fontFamily: "var(--font-display)",
      fontWeight: 800,
      fontSize: 16,
      letterSpacing: ".02em"
    }
  }, lib.monogram), /*#__PURE__*/React.createElement("span", {
    style: {
      lineHeight: 1.12,
      maxWidth: 280
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: 15.5,
      color: "var(--text-strong)",
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap"
    }
  }, lib.short), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontSize: 10.5,
      letterSpacing: ".14em",
      textTransform: "uppercase",
      color: "var(--text-subtle)",
      fontWeight: 600
    }
  }, lib.tagline)));
}
function LibraryPicker({
  libraries,
  current,
  onPick
}) {
  const {
    Icon
  } = NS;
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = e => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    },
    ref: ref
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setOpen(o => !o),
    "aria-label": "\u0421\u043C\u0435\u043D\u0438\u0442\u044C \u0431\u0438\u0431\u043B\u0438\u043E\u0442\u0435\u043A\u0443 (\u0434\u0435\u043C\u043E\u043D\u0441\u0442\u0440\u0430\u0446\u0438\u044F \u0441\u043A\u0438\u043D\u043E\u0432)",
    title: "\u0414\u0435\u043C\u043E\u043D\u0441\u0442\u0440\u0430\u0446\u0438\u044F: \u0431\u0438\u0431\u043B\u0438\u043E\u0442\u0435\u043A\u0430 \u0438 \u0435\u0451 \u0441\u043A\u0438\u043D",
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      border: "1px solid var(--border-default)",
      background: "var(--surface-card)",
      color: "var(--text-muted)",
      borderRadius: "var(--radius-pill)",
      padding: "6px 10px",
      cursor: "pointer",
      fontFamily: "var(--font-ui)",
      fontSize: "var(--text-xs)",
      fontWeight: 600
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "settings",
    size: 14
  }), " \u0421\u043A\u0438\u043D"), open && /*#__PURE__*/React.createElement("div", {
    role: "menu",
    style: {
      position: "absolute",
      top: "calc(100% + 8px)",
      left: 0,
      width: 320,
      zIndex: "var(--z-overlay)",
      background: "var(--surface-card)",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-lg)",
      boxShadow: "var(--shadow-lg)",
      padding: "var(--space-3)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--text-2xs)",
      textTransform: "uppercase",
      letterSpacing: "var(--tracking-caps)",
      color: "var(--text-subtle)",
      fontWeight: 700,
      padding: "4px 8px 8px"
    }
  }, "\u0411\u0438\u0431\u043B\u0438\u043E\u0442\u0435\u043A\u0430 \u0438 \u0435\u0451 \u0441\u043A\u0438\u043D"), libraries.map(lib => {
    const on = lib.id === current;
    return /*#__PURE__*/React.createElement("button", {
      key: lib.id,
      type: "button",
      onClick: () => {
        onPick(lib.id);
        setOpen(false);
      },
      style: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        textAlign: "left",
        cursor: "pointer",
        border: "1px solid " + (on ? "var(--accent-weak-border)" : "transparent"),
        background: on ? "var(--accent-weak)" : "transparent",
        borderRadius: "var(--radius-sm)",
        padding: "9px 10px",
        fontFamily: "var(--font-ui)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      "data-theme": lib.theme === "working" ? undefined : lib.theme,
      style: {
        width: 30,
        height: 30,
        borderRadius: "var(--radius-sm)",
        background: "var(--accent)",
        color: "var(--accent-fg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
        fontFamily: "var(--font-display)",
        fontWeight: 800,
        fontSize: 12
      }
    }, lib.monogram), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        color: "var(--text-strong)",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap"
      }
    }, lib.short), /*#__PURE__*/React.createElement("span", {
      style: {
        display: "block",
        fontSize: "var(--text-2xs)",
        color: "var(--text-subtle)"
      }
    }, "\u0441\u043A\u0438\u043D: ", lib.theme)), on && /*#__PURE__*/React.createElement(Icon, {
      name: "check",
      size: 16,
      style: {
        color: "var(--accent)"
      }
    }));
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--text-2xs)",
      color: "var(--text-subtle)",
      padding: "6px 8px 2px",
      lineHeight: 1.4
    }
  }, "\u0421\u043A\u0438\u043D \u0438 \u043D\u0430\u0437\u0432\u0430\u043D\u0438\u0435 \u043D\u0430\u0441\u0442\u0440\u0430\u0438\u0432\u0430\u044E\u0442\u0441\u044F \u043F\u043E\u0434 \u0443\u0447\u0440\u0435\u0436\u0434\u0435\u043D\u0438\u0435 \u0434\u0435\u043A\u043B\u0430\u0440\u0430\u0442\u0438\u0432\u043D\u043E (\xA79). \u041F\u043E\u043B\u044C\u0437\u043E\u0432\u0430\u0442\u0435\u043B\u044C \u043C\u043E\u0436\u0435\u0442 \u043F\u0435\u0440\u0435\u043E\u043F\u0440\u0435\u0434\u0435\u043B\u0438\u0442\u044C \u0442\u0435\u043C\u0443 \u0432 \u043C\u0435\u043D\u044E \xAB\u0414\u043E\u0441\u0442\u0443\u043F\u043D\u043E\u0441\u0442\u044C \u0438 \u0442\u0435\u043C\u0430\xBB.")));
}
function AccessibilityMenu({
  theme,
  setTheme,
  a11y,
  setA11y,
  noImg,
  setNoImg
}) {
  const {
    IconButton,
    Switch,
    Icon
  } = NS;
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = e => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  const seg = (val, label, icon) => /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => setTheme(val),
    "aria-pressed": theme === val,
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 6,
      padding: "9px 8px",
      borderRadius: "var(--radius-sm)",
      cursor: "pointer",
      border: "1px solid " + (theme === val ? "var(--accent)" : "var(--border-default)"),
      background: theme === val ? "var(--accent-weak)" : "var(--surface-card)",
      color: theme === val ? "var(--accent-press)" : "var(--text-muted)",
      fontFamily: "var(--font-ui)",
      fontSize: "var(--text-sm)",
      fontWeight: 600
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: icon,
    size: 16
  }), " ", label);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    },
    ref: ref
  }, /*#__PURE__*/React.createElement(IconButton, {
    icon: "accessibility",
    label: "\u0414\u043E\u0441\u0442\u0443\u043F\u043D\u043E\u0441\u0442\u044C \u0438 \u0442\u0435\u043C\u0430",
    variant: open ? "accent" : "outline",
    onClick: () => setOpen(o => !o)
  }), open && /*#__PURE__*/React.createElement("div", {
    role: "dialog",
    "aria-label": "\u0414\u043E\u0441\u0442\u0443\u043F\u043D\u043E\u0441\u0442\u044C \u0438 \u0442\u0435\u043C\u0430",
    style: {
      position: "absolute",
      top: "calc(100% + 8px)",
      right: 0,
      width: 270,
      zIndex: "var(--z-overlay)",
      background: "var(--surface-card)",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-lg)",
      boxShadow: "var(--shadow-lg)",
      padding: "var(--space-4)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-4)",
      fontFamily: "var(--font-ui)"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--text-2xs)",
      textTransform: "uppercase",
      letterSpacing: "var(--tracking-caps)",
      color: "var(--text-subtle)",
      fontWeight: 700,
      marginBottom: 8
    }
  }, "\u0421\u0432\u0435\u0442\u043B\u044B\u0435 \u0442\u0435\u043C\u044B"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 6
    }
  }, seg("working", "Бумага", "sun"), seg("azure", "Лазурь", "globe"), seg("pine", "Хвоя", "book"), seg("theatrical", "Театр", "book-open")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--text-2xs)",
      textTransform: "uppercase",
      letterSpacing: "var(--tracking-caps)",
      color: "var(--text-subtle)",
      fontWeight: 700,
      margin: "12px 0 8px"
    }
  }, "\u0422\u0451\u043C\u043D\u0430\u044F \u0438 \u043F\u0440\u0430\u0437\u0434\u043D\u0438\u0447\u043D\u044B\u0435"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 6
    }
  }, seg("dark", "Тёмная", "moon"), seg("newyear", "Новый год", "snowflake"), seg("march8", "8 марта", "flower")), (theme === "newyear" || theme === "march8") && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontSize: "var(--text-2xs)",
      color: "var(--text-subtle)",
      lineHeight: 1.4
    }
  }, "\u041F\u0440\u0430\u0437\u0434\u043D\u0438\u0447\u043D\u044B\u0439 \u0441\u043A\u0438\u043D \u0441\u043E \u0441\u0446\u0435\u043D\u0438\u0447\u0435\u0441\u043A\u0438\u043C\u0438 \u044D\u0444\u0444\u0435\u043A\u0442\u0430\u043C\u0438. \u0414\u0432\u0438\u0436\u0435\u043D\u0438\u0435 \u043E\u0442\u043A\u043B\u044E\u0447\u0430\u0435\u0442\u0441\u044F \u0441\u0438\u0441\u0442\u0435\u043C\u043D\u043E\u0439 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u043E\u0439 \xAB\u0443\u043C\u0435\u043D\u044C\u0448\u0438\u0442\u044C \u0434\u0432\u0438\u0436\u0435\u043D\u0438\u0435\xBB.")), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: "1px solid var(--border-subtle)",
      paddingTop: "var(--space-4)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-3)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: "var(--text-2xs)",
      textTransform: "uppercase",
      letterSpacing: "var(--tracking-caps)",
      color: "var(--text-subtle)",
      fontWeight: 700
    }
  }, "\u0414\u043E\u0441\u0442\u0443\u043F\u043D\u043E\u0441\u0442\u044C (\u0413\u041E\u0421\u0422 \u0420 52872-2019)"), /*#__PURE__*/React.createElement(Switch, {
    label: "\u0412\u044B\u0441\u043E\u043A\u0438\u0439 \u043A\u043E\u043D\u0442\u0440\u0430\u0441\u0442 \u0438 \u043A\u0440\u0443\u043F\u043D\u044B\u0439 \u0442\u0435\u043A\u0441\u0442",
    checked: a11y,
    onChange: e => setA11y(e.target.checked)
  }), /*#__PURE__*/React.createElement(Switch, {
    label: "\u0411\u0435\u0437 \u0438\u0437\u043E\u0431\u0440\u0430\u0436\u0435\u043D\u0438\u0439 (\u0442\u043E\u043B\u044C\u043A\u043E \u0442\u0435\u043A\u0441\u0442)",
    checked: noImg,
    onChange: e => setNoImg(e.target.checked)
  }))));
}
function ContextSwitch({
  context,
  setContext
}) {
  const {
    Icon
  } = NS;
  const opts = [{
    id: "reader",
    label: "Читатель",
    icon: "book-open"
  }, {
    id: "staff",
    label: "Сотрудник",
    icon: "briefcase"
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "inline-flex",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-pill)",
      overflow: "hidden",
      background: "var(--surface-card)"
    },
    role: "group",
    "aria-label": "\u041A\u043E\u043D\u0442\u0435\u043A\u0441\u0442 \u0432\u0445\u043E\u0434\u0430"
  }, opts.map(o => {
    const on = context === o.id;
    return /*#__PURE__*/React.createElement("button", {
      key: o.id,
      type: "button",
      onClick: () => setContext(o.id),
      "aria-pressed": on,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        border: "none",
        cursor: "pointer",
        padding: "7px 14px",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        background: on ? "var(--accent)" : "transparent",
        color: on ? "var(--accent-fg)" : "var(--text-muted)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: o.icon,
      size: 15
    }), " ", o.label);
  }));
}
function TopBar(props) {
  const {
    Button,
    Badge,
    Icon
  } = NS;
  const {
    onHome,
    onAccount,
    account,
    theme,
    setTheme,
    a11y,
    setA11y,
    noImg,
    setNoImg,
    currentDb,
    multiBase,
    context,
    setContext,
    library,
    libraries,
    onPickLibrary
  } = props;
  return /*#__PURE__*/React.createElement("header", {
    style: {
      position: "sticky",
      top: 0,
      zIndex: "var(--z-sticky)",
      background: "var(--surface-card)",
      borderBottom: "1px solid var(--border-default)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "var(--container-max)",
      margin: "0 auto",
      padding: "10px var(--space-6)",
      display: "flex",
      alignItems: "center",
      gap: "var(--space-4)"
    }
  }, /*#__PURE__*/React.createElement(Brand, {
    onClick: onHome,
    library: library
  }), /*#__PURE__*/React.createElement(LibraryPicker, {
    libraries: libraries,
    current: library ? library.id : null,
    onPick: onPickLibrary
  }), multiBase > 0 ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      marginLeft: 4,
      padding: "6px 12px",
      border: "1px solid var(--accent-weak-border)",
      borderRadius: "var(--radius-pill)",
      background: "var(--accent-weak)",
      color: "var(--accent-press)",
      fontFamily: "var(--font-ui)",
      fontSize: "var(--text-sm)",
      fontWeight: 600
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "layers",
    size: 15
  }), " ", multiBase, " \u0431\u0430\u0437\u044B") : currentDb && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 7,
      marginLeft: 4,
      padding: "6px 12px",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-pill)",
      background: "var(--surface-sunken)",
      color: "var(--text-muted)",
      fontFamily: "var(--font-ui)",
      fontSize: "var(--text-sm)",
      fontWeight: 600
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: currentDb.icon,
    size: 15
  }), " ", currentDb.short || currentDb.name), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement(ContextSwitch, {
    context: context,
    setContext: setContext
  }), /*#__PURE__*/React.createElement(AccessibilityMenu, {
    theme: theme,
    setTheme: setTheme,
    a11y: a11y,
    setA11y: setA11y,
    noImg: noImg,
    setNoImg: setNoImg
  }), context === "staff" ? /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "briefcase",
    onClick: onHome
  }, "\u0420\u0430\u0431\u043E\u0447\u0438\u0439 \u0441\u0442\u043E\u043B") : account.loggedIn ? /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "user",
    onClick: onAccount
  }, "\u0411\u0438\u043B\u0435\u0442 ", account.ticket, " ", /*#__PURE__*/React.createElement(Badge, {
    variant: "accent",
    count: true,
    style: {
      marginLeft: 6
    }
  }, account.orders.length)) : /*#__PURE__*/React.createElement(Button, {
    iconLeft: "log-in",
    onClick: onAccount
  }, "\u0412\u0445\u043E\u0434 \u0432 \u041B\u041A")));
}
Object.assign(window, {
  TopBar,
  Brand
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/Shell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/SpecialForm.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    Input,
    Select,
    Checkbox
  } = NS;
  const MONTHS = ["— месяц —", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"];
  const DAYS = ["— день —"].concat(Array.from({
    length: 31
  }, (_, i) => String(i + 1)));
  function FieldLabel({
    children
  }) {
    return /*#__PURE__*/React.createElement("label", {
      style: {
        display: "block",
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        color: "var(--text-muted)",
        marginBottom: 5
      }
    }, children);
  }
  function AreaHead({
    icon,
    children
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 7,
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: icon,
      size: 15,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-2xs)",
        textTransform: "uppercase",
        letterSpacing: "var(--tracking-caps)",
        color: "var(--text-subtle)",
        fontWeight: 700
      }
    }, children));
  }

  // Конфиг-управляемая спецформа (§4–§7): рендерит виджеты из db.specialForm.
  function SpecialForm({
    db,
    values,
    setValues,
    onSearch,
    onReset
  }) {
    const v = values || {};
    const set = (k, val) => setValues({
      ...v,
      [k]: val
    });
    const fields = db.specialForm || [];
    const renderField = f => {
      switch (f.kind) {
        case "text":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id
          }, /*#__PURE__*/React.createElement(FieldLabel, null, f.label), /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            value: v[f.id] || "",
            placeholder: "\u0437\u043D\u0430\u0447\u0435\u043D\u0438\u0435",
            onChange: e => set(f.id, e.target.value)
          }));
        case "select":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id
          }, /*#__PURE__*/React.createElement(FieldLabel, null, f.label), /*#__PURE__*/React.createElement(Select, {
            size: "sm",
            value: v[f.id] || f.options[0],
            onChange: e => set(f.id, e.target.value),
            options: f.options
          }));
        case "range":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id
          }, /*#__PURE__*/React.createElement(FieldLabel, null, f.label), /*#__PURE__*/React.createElement("div", {
            style: {
              display: "flex",
              gap: 8
            }
          }, /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            placeholder: f.from || "с…",
            value: v[f.id + ":from"] || "",
            onChange: e => set(f.id + ":from", e.target.value)
          }), /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            placeholder: f.to || "по…",
            value: v[f.id + ":to"] || "",
            onChange: e => set(f.id + ":to", e.target.value)
          })));
        case "checkbox":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id,
            style: {
              display: "flex",
              alignItems: "center",
              paddingTop: 22
            }
          }, /*#__PURE__*/React.createElement(Checkbox, {
            label: f.label,
            checked: !!v[f.id],
            onChange: e => set(f.id, e.target.checked)
          }));
        case "dateEvent":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id,
            style: {
              gridColumn: "1 / -1",
              background: "var(--surface-sunken)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-4)"
            }
          }, /*#__PURE__*/React.createElement(AreaHead, {
            icon: "calendar"
          }, f.label, " \xB7 \u043B\u043E\u0433\u0438\u043A\u0430 \xAB\u0418\xBB"), /*#__PURE__*/React.createElement("div", {
            style: {
              display: "grid",
              gridTemplateColumns: "1fr 1.4fr 1fr",
              gap: "var(--space-3)"
            }
          }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(FieldLabel, null, "\u0413\u043E\u0434"), /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            placeholder: "\u043D\u0430\u043F\u0440. 1898",
            value: v[f.id + ":y"] || "",
            onChange: e => set(f.id + ":y", e.target.value)
          })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(FieldLabel, null, "\u041C\u0435\u0441\u044F\u0446"), /*#__PURE__*/React.createElement(Select, {
            size: "sm",
            value: v[f.id + ":m"] || MONTHS[0],
            onChange: e => set(f.id + ":m", e.target.value),
            options: MONTHS
          })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(FieldLabel, null, "\u0414\u0435\u043D\u044C"), /*#__PURE__*/React.createElement(Select, {
            size: "sm",
            value: v[f.id + ":d"] || DAYS[0],
            onChange: e => set(f.id + ":d", e.target.value),
            options: DAYS
          }))));
        case "sourceArea":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id,
            style: {
              gridColumn: "1 / -1",
              background: "var(--surface-sunken)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-4)"
            }
          }, /*#__PURE__*/React.createElement(AreaHead, {
            icon: "book"
          }, f.label), /*#__PURE__*/React.createElement("div", {
            style: {
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "var(--space-3)"
            }
          }, f.fields.map(sf => /*#__PURE__*/React.createElement("div", {
            key: sf.id
          }, /*#__PURE__*/React.createElement(FieldLabel, null, sf.label), /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            value: v[sf.id] || "",
            onChange: e => set(sf.id, e.target.value)
          })))));
        case "roles":
          return /*#__PURE__*/React.createElement("div", {
            key: f.id,
            style: {
              gridColumn: "1 / -1",
              background: "var(--surface-sunken)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-4)"
            }
          }, /*#__PURE__*/React.createElement(AreaHead, {
            icon: "drama"
          }, f.label, " \xB7 ", f.fields.length, " \u043F\u043E\u043B\u0435\u0439, \u043A\u043E\u043C\u0431\u0438\u043D\u0438\u0440\u0443\u044E\u0442\u0441\u044F"), /*#__PURE__*/React.createElement("div", {
            style: {
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "var(--space-3)"
            }
          }, f.fields.map((r, i) => /*#__PURE__*/React.createElement("div", {
            key: i
          }, /*#__PURE__*/React.createElement(FieldLabel, null, r), /*#__PURE__*/React.createElement(Input, {
            size: "sm",
            placeholder: "\u2014",
            value: v[f.id + ":" + i] || "",
            onChange: e => set(f.id + ":" + i, e.target.value)
          })))));
        default:
          return null;
      }
    };
    return /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: db.icon,
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("h2", {
      style: {
        fontSize: "var(--text-lg)"
      }
    }, db.specialTitle || "Поиск · " + db.name)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "var(--space-3) var(--space-4)"
      }
    }, fields.map(renderField)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        marginTop: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, "\u041F\u043E\u0438\u0441\u043A \u0441\u0442\u0430\u0440\u0442\u0443\u0435\u0442 \u043F\u043E \u043A\u043D\u043E\u043F\u043A\u0435."), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      size: "lg",
      iconLeft: "rotate-ccw",
      onClick: onReset
    }, "\u0421\u0431\u0440\u043E\u0441"), /*#__PURE__*/React.createElement(Button, {
      size: "lg",
      iconLeft: "search",
      onClick: onSearch
    }, "\u041F\u043E\u0438\u0441\u043A")));
  }
  Object.assign(window, {
    SpecialForm
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/SpecialForm.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/StaffScreens.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    Badge,
    Input,
    Alert
  } = NS;
  const LEVELS = {
    none: 0,
    read: 1,
    write: 2,
    delete: 3,
    admin: 4
  };
  const hasGrant = (grants, domainId, need) => LEVELS[grants[domainId] || "none"] >= LEVELS[need || "read"];
  const TONE = {
    available: {
      fg: "var(--status-available-strong)",
      bg: "var(--status-available-bg)"
    },
    issued: {
      fg: "var(--status-issued-strong)",
      bg: "var(--status-issued-bg)"
    },
    danger: {
      fg: "var(--danger-500)",
      bg: "var(--status-unknown-bg)"
    },
    neutral: {
      fg: "var(--text-muted)",
      bg: "var(--surface-sunken)"
    }
  };

  // ===== Рабочий стол сотрудника — меню задач ПО ГРАНТАМ (не по АРМам) =====
  function StaffDesktop({
    staff,
    onTask
  }) {
    const visible = staff.domains.filter(d => hasGrant(staff.grants, d.id, d.need));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: "var(--container-max)",
        margin: "0 auto",
        padding: "var(--space-6) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "baseline",
        gap: "var(--space-3)",
        marginBottom: "var(--space-5)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-2xl)"
      }
    }, "\u0420\u0430\u0431\u043E\u0447\u0438\u0439 \u0441\u0442\u043E\u043B"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, staff.role, " \xB7 \u0434\u043E\u0441\u0442\u0443\u043F\u043D\u043E \u0437\u0430\u0434\u0430\u0447 \u043F\u043E \u0433\u0440\u0430\u043D\u0442\u0430\u043C: ", visible.length)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
        gap: "var(--space-3)",
        marginBottom: "var(--space-6)"
      }
    }, staff.summary.map(s => {
      const t = TONE[s.tone] || TONE.neutral;
      return /*#__PURE__*/React.createElement("div", {
        key: s.label,
        style: {
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          background: "var(--surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "var(--space-4)"
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          width: 40,
          height: 40,
          borderRadius: "var(--radius-md)",
          background: t.bg,
          color: t.fg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none"
        }
      }, /*#__PURE__*/React.createElement(Icon, {
        name: s.icon,
        size: 20
      })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
        style: {
          fontFamily: "var(--font-display)",
          fontSize: "var(--text-2xl)",
          fontWeight: 700,
          color: "var(--text-strong)",
          lineHeight: 1
        }
      }, s.value), /*#__PURE__*/React.createElement("div", {
        style: {
          fontSize: "var(--text-xs)",
          color: "var(--text-muted)",
          marginTop: 3
        }
      }, s.label)));
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
        gap: "var(--space-4)"
      }
    }, visible.map(d => /*#__PURE__*/React.createElement("section", {
      key: d.id,
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-4)",
        borderBottom: "1px solid var(--border-subtle)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 38,
        height: 38,
        borderRadius: "var(--radius-md)",
        background: "var(--accent-weak)",
        color: "var(--accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: d.icon,
      size: 20
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 700,
        color: "var(--text-strong)",
        fontSize: "var(--text-md)"
      }
    }, d.label), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, d.desc)), /*#__PURE__*/React.createElement(Badge, {
      variant: "neutral"
    }, staff.grants[d.id])), /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "var(--space-2)"
      }
    }, d.tasks.length === 0 ? /*#__PURE__*/React.createElement("div", {
      style: {
        padding: "var(--space-3)",
        fontSize: "var(--text-sm)",
        color: "var(--text-subtle)"
      }
    }, "\u041D\u0435\u0442 \u0434\u043E\u0441\u0442\u0443\u043F\u043D\u044B\u0445 \u043E\u043F\u0435\u0440\u0430\u0446\u0438\u0439.") : d.tasks.map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      type: "button",
      onClick: () => onTask(d.id, t.id),
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        width: "100%",
        textAlign: "left",
        border: "none",
        background: "transparent",
        borderRadius: "var(--radius-sm)",
        padding: "10px 12px",
        cursor: "pointer",
        fontFamily: "var(--font-ui)"
      },
      onMouseEnter: e => e.currentTarget.style.background = "var(--surface-hover)",
      onMouseLeave: e => e.currentTarget.style.background = "transparent"
    }, /*#__PURE__*/React.createElement(Icon, {
      name: t.icon,
      size: 17,
      style: {
        color: "var(--text-subtle)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        fontSize: "var(--text-sm)",
        color: "var(--text-body)",
        fontWeight: 500
      }
    }, t.label), t.badge != null && /*#__PURE__*/React.createElement(Badge, {
      variant: "accent",
      count: true
    }, t.badge), /*#__PURE__*/React.createElement(Icon, {
      name: "chevron-right",
      size: 16,
      style: {
        color: "var(--text-subtle)"
      }
    }))))))), staff.domains.length > visible.length && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement(Alert, {
      variant: "info",
      title: "\u0427\u0430\u0441\u0442\u044C \u0444\u0443\u043D\u043A\u0446\u0438\u0439 \u0441\u043A\u0440\u044B\u0442\u0430"
    }, "\u041D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u043D\u043E \u043F\u043E \u0433\u0440\u0430\u043D\u0442\u0430\u043C \u0443\u0447\u0451\u0442\u043A\u0438: ", staff.domains.filter(d => !hasGrant(staff.grants, d.id, d.need)).map(d => d.label).join(", "), ". \u0418\u043D\u0442\u0435\u0440\u0444\u0435\u0439\u0441 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0435\u0442 \u0442\u043E\u043B\u044C\u043A\u043E \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043D\u043D\u043E\u0435.")));
  }

  // ===== Рабочий лист каталогизации — динамическая форма из профиля базы =====
  function CatalogingWorksheet({
    profile,
    onBack,
    onToast
  }) {
    const {
      DynamicField
    } = NS;
    const [page, setPage] = React.useState(profile.pages[0].id);
    const [values, setValues] = React.useState({});
    const [errors, setErrors] = React.useState({});
    const cur = profile.pages.find(p => p.id === page);
    const setField = (code, v) => setValues(s => ({
      ...s,
      [code]: v
    }));
    function validate() {
      const errs = {};
      profile.pages.forEach(pg => pg.fields.forEach(f => {
        const v = values[f.code];
        if (f.required && (v == null || typeof v === "string" && !v.trim() || Array.isArray(v) && v.length === 0)) {
          errs[f.code] = "Поле обязательно (ФЛК)";
        }
        if (f.type === "date" && typeof v === "string" && v && !/^\d{4}/.test(v)) {
          errs[f.code] = "Год должен начинаться с 4 цифр";
        }
      }));
      setErrors(errs);
      const ok = Object.keys(errs).length === 0;
      if (!ok) {
        const firstPage = profile.pages.find(pg => pg.fields.some(f => errs[f.code]));
        if (firstPage) setPage(firstPage.id);
      }
      return ok;
    }
    const filled = profile.pages.reduce((n, pg) => n + pg.fields.filter(f => {
      const v = values[f.code];
      return v != null && (Array.isArray(v) ? v.length : String(v).trim());
    }).length, 0);
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1000,
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        marginBottom: "var(--space-4)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onBack,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        padding: 0
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left",
      size: 17
    }), " \u041A \u0440\u0430\u0431\u043E\u0447\u0435\u043C\u0443 \u0441\u0442\u043E\u043B\u0443"), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: "auto",
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, "\u0437\u0430\u043F\u043E\u043B\u043D\u0435\u043D\u043E \u043F\u043E\u043B\u0435\u0439: ", filled)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "baseline",
        gap: "var(--space-3)",
        marginBottom: "var(--space-5)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-2xl)"
      }
    }, "\u0420\u0430\u0431\u043E\u0447\u0438\u0439 \u043B\u0438\u0441\u0442 \u0437\u0430\u043F\u0438\u0441\u0438"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u043F\u0440\u043E\u0444\u0438\u043B\u044C: ", profile.dbName)), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "210px 1fr",
        gap: "var(--space-6)",
        alignItems: "start"
      }
    }, /*#__PURE__*/React.createElement("aside", {
      style: {
        position: "sticky",
        top: 76,
        display: "flex",
        flexDirection: "column",
        gap: 4
      }
    }, profile.pages.map(pg => {
      const on = pg.id === page;
      const pgErr = pg.fields.some(f => errors[f.code]);
      return /*#__PURE__*/React.createElement("button", {
        key: pg.id,
        type: "button",
        onClick: () => setPage(pg.id),
        style: {
          display: "flex",
          alignItems: "center",
          gap: 9,
          textAlign: "left",
          cursor: "pointer",
          padding: "10px 12px",
          borderRadius: "var(--radius-sm)",
          fontFamily: "var(--font-ui)",
          fontSize: "var(--text-sm)",
          fontWeight: on ? 600 : 500,
          border: "1px solid " + (on ? "var(--accent-weak-border)" : "transparent"),
          background: on ? "var(--accent-weak)" : "transparent",
          color: on ? "var(--accent-press)" : "var(--text-body)"
        }
      }, /*#__PURE__*/React.createElement("span", {
        style: {
          width: 3,
          alignSelf: "stretch",
          borderRadius: 2,
          background: on ? "var(--accent)" : "transparent"
        }
      }), pg.label, pgErr && /*#__PURE__*/React.createElement(Icon, {
        name: "alert-triangle",
        size: 14,
        style: {
          color: "var(--danger-500)",
          marginLeft: "auto"
        }
      }));
    })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
      style: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-5)"
      }
    }, cur.fields.map(f => /*#__PURE__*/React.createElement(DynamicField, {
      key: f.code,
      field: f,
      value: values[f.code],
      onChange: v => setField(f.code, v),
      error: errors[f.code]
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        marginTop: "var(--space-4)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)",
        display: "inline-flex",
        alignItems: "center",
        gap: 6
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "shield",
      size: 14
    }), " \u0424\u041B\u041A \u043F\u0440\u043E\u0432\u0435\u0440\u0438\u0442 \u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u044B\u0435 \u043F\u043E\u043B\u044F \u0438 \u0444\u043E\u0440\u043C\u0430\u0442\u044B \u043F\u0435\u0440\u0435\u0434 \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u0438\u0435\u043C."), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }), /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      iconLeft: "rotate-ccw",
      onClick: () => {
        setValues({});
        setErrors({});
      }
    }, "\u041E\u0447\u0438\u0441\u0442\u0438\u0442\u044C"), /*#__PURE__*/React.createElement(Button, {
      iconLeft: "save",
      onClick: () => {
        if (validate()) onToast({
          variant: "success",
          title: "Запись сохранена",
          message: "Прошла ФЛК. Внесена в черновики."
        });else onToast({
          variant: "error",
          title: "Не прошло ФЛК",
          message: "Заполните обязательные поля."
        });
      }
    }, "\u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C \u0437\u0430\u043F\u0438\u0441\u044C")))));
  }

  // Заглушка для операций, которые ещё не спроектированы детально
  function StaffStub({
    title,
    onBack
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 720,
        margin: "0 auto",
        padding: "var(--space-16) var(--space-6)"
      }
    }, /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onBack,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        padding: 0,
        marginBottom: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left",
      size: 17
    }), " \u041A \u0440\u0430\u0431\u043E\u0447\u0435\u043C\u0443 \u0441\u0442\u043E\u043B\u0443"), /*#__PURE__*/React.createElement(NS.EmptyState, {
      icon: "clipboard-check",
      title: title,
      description: "\u042D\u043A\u0440\u0430\u043D \u0437\u0430\u043F\u043B\u0430\u043D\u0438\u0440\u043E\u0432\u0430\u043D \u0432 \u0441\u043B\u0435\u0434\u0443\u044E\u0449\u0435\u0439 \u0438\u0442\u0435\u0440\u0430\u0446\u0438\u0438 (\u043A\u043D\u0438\u0433\u043E\u0432\u044B\u0434\u0430\u0447\u0430 / \u0438\u043D\u0432\u0435\u043D\u0442\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u044F \u0441 \u0422\u0421\u0414 / \u0434\u0430\u0448\u0431\u043E\u0440\u0434\u044B). \u0421\u0442\u0440\u0443\u043A\u0442\u0443\u0440\u0430 \u2014 \u043F\u043E SCREENMAP_web-staff."
    }));
  }
  Object.assign(window, {
    StaffDesktop,
    CatalogingWorksheet,
    StaffStub
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/StaffScreens.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/StaffWork.jsx
try { (() => {
/* global React */
(function () {
  const NS = window.DesignSystem_d9a584;
  const {
    Icon,
    Button,
    Badge,
    Input,
    StatusBadge,
    Tabs,
    Alert,
    EmptyState
  } = NS;
  function Back({
    onBack
  }) {
    return /*#__PURE__*/React.createElement("button", {
      type: "button",
      onClick: onBack,
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        background: "none",
        border: "none",
        color: "var(--text-link)",
        cursor: "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "var(--text-sm)",
        fontWeight: 600,
        padding: 0,
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "arrow-left",
      size: 17
    }), " \u041A \u0440\u0430\u0431\u043E\u0447\u0435\u043C\u0443 \u0441\u0442\u043E\u043B\u0443");
  }
  function H1({
    children,
    sub
  }) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "baseline",
        gap: "var(--space-3)",
        marginBottom: "var(--space-5)",
        flexWrap: "wrap"
      }
    }, /*#__PURE__*/React.createElement("h1", {
      style: {
        fontSize: "var(--text-2xl)"
      }
    }, children), sub && /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, sub));
  }
  const Card = ({
    children,
    style
  }) => /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--border-default)",
      borderRadius: "var(--radius-lg)",
      padding: "var(--space-5)",
      ...style
    }
  }, children);

  // ===== Книговыдача: выдача/возврат, очередь, бронеполка =====
  function Circulation({
    data,
    onBack,
    onToast
  }) {
    const [tab, setTab] = React.useState("desk");
    const [scan, setScan] = React.useState("");
    const [reader, setReader] = React.useState(null);
    const r = data.reader;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 980,
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement(Back, {
      onBack: onBack
    }), /*#__PURE__*/React.createElement(H1, {
      sub: "\u0441\u043A\u0430\u043D\u0435\u0440 / RFID \xB7 \u044F\u0447\u0435\u0438\u0441\u0442\u043E\u0435 \u0445\u0440\u0430\u043D\u0435\u043D\u0438\u0435"
    }, "\u041A\u043D\u0438\u0433\u043E\u0432\u044B\u0434\u0430\u0447\u0430"), /*#__PURE__*/React.createElement(Tabs, {
      value: tab,
      onChange: setTab,
      tabs: [{
        id: "desk",
        label: "Выдача / возврат"
      }, {
        id: "queue",
        label: "Очередь заказов",
        count: data.queue.length
      }, {
        id: "shelf",
        label: "Бронеполка",
        count: data.shelf.length
      }]
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-5)"
      }
    }, tab === "desk" && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "scan-line",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, "\u0411\u0438\u043B\u0435\u0442 \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044F")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      iconLeft: "scan-line",
      placeholder: "\u0421\u043A\u0430\u043D\u0438\u0440\u0443\u0439\u0442\u0435 \u0431\u0438\u043B\u0435\u0442 (00012345)",
      value: scan,
      onChange: e => setScan(e.target.value),
      onKeyDown: e => e.key === "Enter" && setReader(r)
    })), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      onClick: () => setReader(r)
    }, "\u041D\u0430\u0439\u0442\u0438")), reader && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        paddingBottom: "var(--space-3)",
        borderBottom: "1px solid var(--border-subtle)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 40,
        height: 40,
        borderRadius: "var(--radius-round)",
        background: "var(--accent-weak)",
        color: "var(--accent)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "user",
      size: 20
    })), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 700,
        color: "var(--text-strong)"
      }
    }, reader.display), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, reader.category, " \xB7 \u0431\u0438\u043B\u0435\u0442 \u2116 ", reader.ticket, " \xB7 ", reader.valid)), reader.overdue > 0 && /*#__PURE__*/React.createElement(Badge, {
      variant: "warning"
    }, "\u043F\u0440\u043E\u0441\u0440\u043E\u0447\u043A\u0430: ", reader.overdue)), /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-3)",
        display: "flex",
        flexDirection: "column",
        gap: 6
      }
    }, reader.items.map(it => /*#__PURE__*/React.createElement("div", {
      key: it.inv,
      style: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: "var(--text-sm)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "book",
      size: 15,
      style: {
        color: "var(--text-subtle)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        color: "var(--text-body)"
      }
    }, it.title), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, it.inv), it.status === "overdue" ? /*#__PURE__*/React.createElement(Badge, {
      variant: "danger"
    }, "\u043F\u0440\u043E\u0441\u0440\u043E\u0447\u0435\u043D\u043E") : /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u0434\u043E ", it.due), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: () => onToast({
        variant: "success",
        title: "Возврат принят",
        message: it.title
      })
    }, "\u0412\u043E\u0437\u0432\u0440\u0430\u0442")))))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "package",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, "\u0412\u044B\u0434\u0430\u0442\u044C \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8,
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1
      }
    }, /*#__PURE__*/React.createElement(Input, {
      size: "sm",
      iconLeft: "scan-line",
      placeholder: "\u0421\u043A\u0430\u043D\u0438\u0440\u0443\u0439\u0442\u0435 \u0438\u043D\u0432. \u043D\u043E\u043C\u0435\u0440 / RFID"
    })), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      iconLeft: "check",
      disabled: !reader,
      onClick: () => onToast({
        variant: "success",
        title: "Выдано",
        message: reader ? reader.display : ""
      })
    }, "\u0412\u044B\u0434\u0430\u0442\u044C")), !reader ? /*#__PURE__*/React.createElement(Alert, {
      variant: "info",
      title: "\u0421\u043D\u0430\u0447\u0430\u043B\u0430 \u043D\u0430\u0439\u0434\u0438\u0442\u0435 \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u044F"
    }, "\u0421\u043B\u0435\u0432\u0430 \u0441\u043A\u0430\u043D\u0438\u0440\u0443\u0439\u0442\u0435 \u0431\u0438\u043B\u0435\u0442, \u0437\u0430\u0442\u0435\u043C \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440.") : /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)"
      }
    }, "\u0427\u0438\u0442\u0430\u0442\u0435\u043B\u044C: ", /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, reader.display), ". \u041D\u0430 \u0440\u0443\u043A\u0430\u0445: ", reader.onHand, ". \u041B\u0438\u043C\u0438\u0442 \u043D\u0435 \u043F\u0440\u0435\u0432\u044B\u0448\u0435\u043D."))), tab === "queue" && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)"
      }
    }, data.queue.map(q => /*#__PURE__*/React.createElement(Card, {
      key: q.inv,
      style: {
        padding: "var(--space-3) var(--space-4)",
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: q.status === "ready" ? "check-circle" : "clock",
      size: 18,
      style: {
        color: q.status === "ready" ? "var(--status-available-strong)" : "var(--status-issued)",
        flex: "none"
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, q.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, q.reader, " \xB7 \u0431\u0438\u043B\u0435\u0442 ", q.ticket, " \xB7 ", q.location, " \xB7 \u043E\u0442 ", q.placed)), /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--text-subtle)"
      }
    }, q.inv), q.status === "ready" ? /*#__PURE__*/React.createElement(Badge, {
      variant: "success"
    }, "\u043D\u0430 \u0431\u0440\u043E\u043D\u0435\u043F\u043E\u043B\u043A\u0435") : /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "secondary",
      iconLeft: "bookmark",
      onClick: () => onToast({
        variant: "success",
        title: "На бронеполку",
        message: q.title
      })
    }, "\u041D\u0430 \u043F\u043E\u043B\u043A\u0443")))), tab === "shelf" && /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        gap: "var(--space-3)"
      }
    }, data.shelf.map(s => /*#__PURE__*/React.createElement(Card, {
      key: s.cell,
      style: {
        padding: "var(--space-4)",
        display: "flex",
        gap: "var(--space-3)",
        alignItems: "flex-start"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-mono)",
        fontWeight: 700,
        color: "var(--accent)",
        background: "var(--accent-weak)",
        borderRadius: "var(--radius-sm)",
        padding: "4px 9px",
        flex: "none"
      }
    }, s.cell), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        minWidth: 0
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 600,
        color: "var(--text-strong)",
        fontSize: "var(--text-sm)"
      }
    }, s.title), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, s.reader, " \xB7 \u0431\u0440\u043E\u043D\u044C ", s.hold)))))));
  }

  // ===== Инвентаризация с ТСД =====
  function Inventory({
    data,
    onBack,
    onToast
  }) {
    const inv = data.inventory;
    const [scanned, setScanned] = React.useState([]);
    const [online, setOnline] = React.useState(true);
    const remaining = inv.expected.filter(e => !scanned.includes(e.inv));
    const scanNext = () => {
      const next = remaining[0];
      if (next) {
        setScanned(s => s.concat([next.inv]));
        onToast({
          variant: "success",
          title: "Сверено",
          message: next.inv + " · " + next.title
        });
      }
    };
    const scanUnknown = () => onToast({
      variant: "warning",
      title: "Не из этого ряда",
      message: "К-99999 — отметить как «обнаружен в другом месте»."
    });
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 900,
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement(Back, {
      onBack: onBack
    }), /*#__PURE__*/React.createElement(H1, {
      sub: inv.session + " · " + inv.location
    }, "\u0418\u043D\u0432\u0435\u043D\u0442\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u044F (\u0422\u0421\u0414)"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "300px 1fr",
        gap: "var(--space-6)",
        alignItems: "start"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        position: "sticky",
        top: 76,
        background: "var(--surface-card)",
        border: "2px solid var(--border-strong)",
        borderRadius: "var(--radius-xl)",
        padding: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "scan-line",
      size: 20,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, "\u0422\u0435\u0440\u043C\u0438\u043D\u0430\u043B \u0441\u0431\u043E\u0440\u0430 \u0434\u0430\u043D\u043D\u044B\u0445"), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: "auto",
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: "var(--text-2xs)",
        fontWeight: 600,
        color: online ? "var(--status-available-strong)" : "var(--status-issued-strong)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: online ? "var(--status-available)" : "var(--status-issued)"
      }
    }), online ? "Онлайн" : "Офлайн")), /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: "center",
        padding: "var(--space-5) 0",
        background: "var(--surface-sunken)",
        borderRadius: "var(--radius-md)",
        marginBottom: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: "var(--font-display)",
        fontSize: 44,
        fontWeight: 800,
        color: "var(--text-strong)",
        lineHeight: 1
      }
    }, scanned.length, /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 22,
        color: "var(--text-subtle)"
      }
    }, " / ", inv.expected.length)), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)",
        marginTop: 4
      }
    }, "\u0441\u0432\u0435\u0440\u0435\u043D\u043E \u0432 \u0440\u044F\u0434\u0443")), /*#__PURE__*/React.createElement(Button, {
      block: true,
      size: "lg",
      iconLeft: "scan-line",
      disabled: remaining.length === 0,
      onClick: scanNext
    }, "\u0421\u043A\u0430\u043D\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: 8,
        marginTop: 8
      }
    }, /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "secondary",
      onClick: scanUnknown,
      style: {
        flex: 1
      }
    }, "\u0427\u0443\u0436\u043E\u0439"), /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      variant: "ghost",
      onClick: () => setOnline(o => !o),
      style: {
        flex: 1
      }
    }, online ? "Офлайн" : "Синхр.")), !online && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: 8,
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, "\u0421\u043A\u0430\u043D\u044B \u043A\u043E\u043F\u044F\u0442\u0441\u044F \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u043E; \u0441\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u0443\u044E\u0442\u0441\u044F \u043F\u0440\u0438 \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0438.")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Card, {
      style: {
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        justifyContent: "space-between",
        marginBottom: 8,
        fontSize: "var(--text-sm)"
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-muted)"
      }
    }, "\u041F\u0440\u043E\u0433\u0440\u0435\u0441\u0441 \u0441\u0432\u0435\u0440\u043A\u0438 \u0440\u044F\u0434\u0430"), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, Math.round(scanned.length / inv.expected.length * 100), "%")), /*#__PURE__*/React.createElement("div", {
      style: {
        height: 10,
        borderRadius: 5,
        background: "var(--surface-sunken)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        height: "100%",
        width: scanned.length / inv.expected.length * 100 + "%",
        background: "var(--accent)",
        transition: "width var(--dur) var(--ease-standard)"
      }
    })), remaining.length === 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "var(--space-3)"
      }
    }, /*#__PURE__*/React.createElement(Button, {
      size: "sm",
      iconLeft: "file-text",
      onClick: () => onToast({
        variant: "success",
        title: "Отчёт сформирован",
        message: "Расхождений не выявлено."
      })
    }, "\u0421\u0444\u043E\u0440\u043C\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u043E\u0442\u0447\u0451\u0442"))), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-2xs)",
        textTransform: "uppercase",
        letterSpacing: "var(--tracking-caps)",
        color: "var(--text-subtle)",
        fontWeight: 700,
        marginBottom: 10
      }
    }, "\u041E\u0436\u0438\u0434\u0430\u0435\u0442\u0441\u044F \u0432 \u0440\u044F\u0434\u0443 \xB7 \u043D\u0435 \u0441\u0432\u0435\u0440\u0435\u043D\u043E: ", remaining.length), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: 6
      }
    }, inv.expected.map(e => {
      const ok = scanned.includes(e.inv);
      return /*#__PURE__*/React.createElement("div", {
        key: e.inv,
        style: {
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "9px 12px",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
          background: ok ? "var(--status-available-bg)" : "var(--surface-card)",
          opacity: ok ? 1 : 0.92
        }
      }, /*#__PURE__*/React.createElement(Icon, {
        name: ok ? "check-circle" : "clock",
        size: 17,
        style: {
          color: ok ? "var(--status-available-strong)" : "var(--text-subtle)",
          flex: "none"
        }
      }), /*#__PURE__*/React.createElement("span", {
        style: {
          flex: 1,
          fontSize: "var(--text-sm)",
          color: "var(--text-body)"
        }
      }, e.title), /*#__PURE__*/React.createElement("span", {
        style: {
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--text-subtle)"
        }
      }, e.inv));
    })))));
  }

  // ===== BI-дашборд =====
  function Dashboard({
    data,
    onBack
  }) {
    const d = data.dashboard;
    const TONE = {
      available: "var(--status-available-strong)",
      issued: "var(--status-issued-strong)"
    };
    const maxV = Math.max(...d.monthly.map(x => x.v));
    return /*#__PURE__*/React.createElement("div", {
      style: {
        maxWidth: 1000,
        margin: "0 auto",
        padding: "var(--space-5) var(--space-6) var(--space-12)"
      }
    }, /*#__PURE__*/React.createElement(Back, {
      onBack: onBack
    }), /*#__PURE__*/React.createElement(H1, {
      sub: "\u043A\u043D\u0438\u0433\u043E\u0432\u044B\u0434\u0430\u0447\u0430 \xB7 \u0444\u043E\u043D\u0434 \xB7 \u0447\u0438\u0442\u0430\u0442\u0435\u043B\u0438"
    }, "\u0410\u043D\u0430\u043B\u0438\u0442\u0438\u043A\u0430"), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
        gap: "var(--space-3)",
        marginBottom: "var(--space-5)"
      }
    }, d.kpis.map(k => /*#__PURE__*/React.createElement(Card, {
      key: k.label,
      style: {
        padding: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)",
        marginBottom: 6
      }
    }, k.label), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "baseline",
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        fontFamily: "var(--font-display)",
        fontSize: "var(--text-2xl)",
        fontWeight: 700,
        color: "var(--text-strong)"
      }
    }, k.value), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        color: TONE[k.tone]
      }
    }, k.delta))))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "grid",
        gridTemplateColumns: "1.4fr 1fr",
        gap: "var(--space-5)"
      }
    }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "bar-chart",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, "\u0412\u044B\u0434\u0430\u0447\u0438 \u043F\u043E \u043C\u0435\u0441\u044F\u0446\u0430\u043C")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "flex-end",
        gap: "var(--space-3)",
        height: 180
      }
    }, d.monthly.map(m => /*#__PURE__*/React.createElement("div", {
      key: m.m,
      style: {
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: "100%",
        height: m.v / maxV * 150 + "px",
        background: "var(--accent)",
        borderRadius: "var(--radius-sm) var(--radius-sm) 0 0",
        opacity: 0.55 + 0.45 * (m.v / maxV)
      }
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)"
      }
    }, m.m))))), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: "var(--space-4)"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: "trending-up",
      size: 18,
      style: {
        color: "var(--accent)"
      }
    }), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, "\u0414\u043E\u043B\u044F \u0432\u044B\u0434\u0430\u0447 \u043F\u043E \u0431\u0430\u0437\u0430\u043C")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)"
      }
    }, d.topDb.map(t => /*#__PURE__*/React.createElement("div", {
      key: t.label
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        justifyContent: "space-between",
        fontSize: "var(--text-sm)",
        marginBottom: 4
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-body)"
      }
    }, t.label), /*#__PURE__*/React.createElement("b", {
      style: {
        color: "var(--text-strong)"
      }
    }, t.pct, "%")), /*#__PURE__*/React.createElement("div", {
      style: {
        height: 8,
        borderRadius: 4,
        background: "var(--surface-sunken)",
        overflow: "hidden"
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        height: "100%",
        width: t.pct + "%",
        background: "var(--accent)"
      }
    }))))))));
  }
  Object.assign(window, {
    Circulation,
    Inventory,
    Dashboard
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/StaffWork.jsx", error: String((e && e.message) || e) }); }

// ui_kits/irbis-web/data.js
try { (() => {
/* ============================================================
   ИРБИС-Веб — мок-данные и КОНФИГ БАЗ (контракт §9 ТЗ v2).
   Экраны рендерятся ИЗ ЭТОЙ КОНФИГУРАЦИИ, а не из хардкода:
   добавление базы = добавление конфига, не переписывание экранов.
   Спецформы поиска (PLAY «Роли», TUAR «Дата события», GUAR Фонд/Опись)
   тоже описаны декларативно — поле `specialForm`.
   Все данные обезличены (152-ФЗ). Загружается как обычный <script>.
   ============================================================ */
(function () {
  // ---- Группы для иерархического селектора баз (§1.1) ----
  // Группа раскрывается тем же приёмом; у группы свой «выбрать все».
  const groups = {
    ek: {
      id: "ek",
      label: "Электронный каталог",
      icon: "book"
    },
    libretto: {
      id: "libretto",
      label: "Базы Либретто",
      icon: "music"
    }
  };

  // ---- Реестр баз (§3). group → принадлежность к раскрываемой группе ----
  const databases = [{
    id: "EK",
    group: "ek",
    name: "Электронный каталог",
    short: "Книги",
    icon: "book",
    description: "Книги — эталонная база",
    count: 214530,
    layout: "list",
    typeIcon: "book",
    simpleLabel: "Я ищу:",
    modes: ["simple", "advanced", "complex"],
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }, {
      code: "SUB",
      label: "Предметная рубрика"
    }, {
      code: "KW",
      label: "Ключевые слова"
    }, {
      code: "PY",
      label: "Год издания"
    }],
    // Чекбокс «Только с электронными версиями» — простой режим ЭК (§4)
    simpleExtra: {
      id: "onlyDigital",
      label: "Только с электронными версиями"
    },
    filters: [{
      id: "doctype",
      label: "Вид документа",
      options: ["Книга", "Сборник", "Многотомник"]
    }, {
      id: "lang",
      label: "Язык публикации",
      options: ["русский", "английский", "французский"]
    }],
    // Навигаторы-классификаторы (§4) — ленивое дерево с количеством.
    navigators: [{
      id: "grnti",
      label: "ГРНТИ",
      tree: [{
        code: "18",
        label: "Искусство",
        count: 412,
        children: [{
          code: "18.45",
          label: "Театр. Театроведение",
          count: 230,
          children: [{
            code: "18.45.09",
            label: "Драматический театр",
            count: 142
          }, {
            code: "18.45.21",
            label: "Опера. Балет",
            count: 64
          }]
        }, {
          code: "18.41",
          label: "Музыка",
          count: 96
        }]
      }, {
        code: "17",
        label: "Литературоведение",
        count: 318,
        children: [{
          code: "17.82",
          label: "Художественная литература",
          count: 210,
          children: [{
            code: "17.82.31",
            label: "Драматургия",
            count: 88
          }]
        }]
      }]
    }, {
      id: "udk",
      label: "УДК",
      tree: [{
        code: "792",
        label: "Театр",
        count: 256,
        children: [{
          code: "792.2",
          label: "Драматический театр",
          count: 130
        }, {
          code: "792.5",
          label: "Музыкальный театр",
          count: 58
        }]
      }, {
        code: "82",
        label: "Литература",
        count: 402,
        children: [{
          code: "82-2",
          label: "Драматургия",
          count: 91
        }]
      }]
    }, {
      id: "bbk",
      label: "ББК",
      tree: [{
        code: "85.33",
        label: "Театр",
        count: 240,
        children: [{
          code: "85.334",
          label: "Драматический театр",
          count: 128
        }]
      }, {
        code: "83.3",
        label: "История литературы",
        count: 176
      }]
    }]
  }, {
    id: "PERIO",
    group: "ek",
    name: "Периодические издания",
    short: "Периодика",
    icon: "newspaper",
    description: "Газеты и журналы",
    count: 18740,
    layout: "list",
    typeIcon: "newspaper",
    simpleLabel: "Я ищу:",
    modes: ["simple", "advanced"],
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "KW",
      label: "Ключевые слова"
    }, {
      code: "PY",
      label: "Год"
    }],
    filters: [{
      id: "kind",
      label: "Вид",
      options: ["Журнал", "Газета", "Альманах"]
    }]
  }, {
    id: "ARTICLES",
    group: "ek",
    name: "Статьи из книг и периодики",
    short: "Статьи",
    icon: "file-text",
    description: "Аналитическая роспись",
    count: 96210,
    layout: "list",
    typeIcon: "file-text",
    simpleLabel: "Я ищу:",
    modes: ["simple", "advanced"],
    searchFields: [{
      code: "TI",
      label: "Заглавие статьи"
    }, {
      code: "AU",
      label: "Автор"
    }, {
      code: "SRC",
      label: "Источник"
    }],
    filters: []
  }, {
    id: "SKETCH",
    name: "Эскизный фонд",
    short: "Эскизы",
    icon: "images",
    description: "Изобразительные материалы · превью",
    count: 8412,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple"],
    searchFields: [{
      code: "TI",
      label: "Название"
    }, {
      code: "AU",
      label: "Художник"
    }, {
      code: "TECH",
      label: "Техника"
    }, {
      code: "PROD",
      label: "Постановка"
    }],
    filters: [{
      id: "tech",
      label: "Техника",
      options: ["Акварель", "Карандаш", "Гуашь", "Тушь"]
    }, {
      id: "type",
      label: "Тип",
      options: ["Эскиз декорации", "Эскиз костюма", "Афиша"]
    }]
  }, {
    id: "HPO",
    name: "Иллюстративные и историко-бытовые материалы",
    short: "Иллюстрации",
    icon: "images",
    description: "Фотографии, открытки, предметы",
    count: 12305,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple"],
    searchFields: [{
      code: "TI",
      label: "Название"
    }, {
      code: "KW",
      label: "Ключевые слова"
    }],
    filters: [],
    stub: true
  }, {
    id: "ABOUT",
    name: "Указатель литературы о СПб ГТБ",
    short: "О библиотеке",
    icon: "bookmark",
    description: "Публикации об учреждении",
    count: 642,
    layout: "list",
    typeIcon: "book",
    simpleLabel: "Я ищу:",
    modes: ["simple"],
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }],
    filters: [],
    stub: true
  }, {
    id: "GUAR",
    name: "Собрание архивных документов",
    short: "Архив (GUAR)",
    icon: "archive",
    description: "Фонд / опись / даты",
    count: 31980,
    layout: "list",
    typeIcon: "file-text",
    simpleLabel: "Я ищу:",
    dateRange: true,
    modes: ["simple", "special"],
    specialTitle: "Поиск по архивным документам",
    searchFields: [{
      code: "TI",
      label: "Заголовок дела"
    }, {
      code: "FOND",
      label: "Фонд"
    }, {
      code: "OP",
      label: "Опись"
    }],
    filters: [{
      id: "fond",
      label: "Фонд",
      options: ["Ф. 1 — Дирекция", "Ф. 2 — Цензура", "Ф. 7 — Труппа"]
    }],
    // §4 GUAR — спецформа
    specialForm: [{
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "select",
      id: "allFonds",
      label: "Все фонды",
      options: ["— любой —", "Ф. 1 — Дирекция Императорских театров", "Ф. 2 — Драматическая цензура", "Ф. 7 — Труппа"]
    }, {
      kind: "text",
      id: "fondName",
      label: "Название фонда"
    }, {
      kind: "text",
      id: "fondNo",
      label: "Номер фонда"
    }, {
      kind: "text",
      id: "opisNo",
      label: "Номер описи"
    }, {
      kind: "text",
      id: "person",
      label: "Персоналия"
    }, {
      kind: "text",
      id: "org",
      label: "Организация"
    }, {
      kind: "range",
      id: "year",
      label: "Год создания",
      from: "с…",
      to: "по…"
    }, {
      kind: "checkbox",
      id: "ecopy",
      label: "Электронная копия / полный текст"
    }]
  }, {
    id: "PLAY",
    name: "Аннотированный указатель пьес",
    short: "Пьесы",
    icon: "drama",
    description: "Пьесы, роли, жанры",
    count: 9874,
    layout: "list",
    typeIcon: "drama",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск пьес",
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }, {
      code: "GEN",
      label: "Жанр"
    }],
    filters: [{
      id: "genre",
      label: "Жанр",
      options: ["Комедия", "Драма", "Трагедия", "Водевиль"]
    }],
    // §4/§7.1 PLAY — спецформа с областью «Роли» (8 вертикальных полей)
    specialForm: [{
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "text",
      id: "persons",
      label: "Персоны"
    }, {
      kind: "text",
      id: "titles",
      label: "Заглавия"
    }, {
      kind: "text",
      id: "genres",
      label: "Жанры и темы (Тезаурус)"
    }, {
      kind: "text",
      id: "timeW",
      label: "Время написания"
    }, {
      kind: "text",
      id: "placeC",
      label: "Место создания"
    }, {
      kind: "text",
      id: "lang",
      label: "Язык написания"
    }, {
      kind: "roles",
      id: "roles",
      label: "Роли",
      fields: ["Женские", "Мужские", "Детские", "Куклы", "Животные", "Сказочные персонажи", "Без определения", "Эпизодические"]
    }, {
      kind: "text",
      id: "acts",
      label: "Количество действий"
    }, {
      kind: "text",
      id: "timeA",
      label: "Время действия"
    }, {
      kind: "text",
      id: "placeA",
      label: "Место действия"
    }]
  }, {
    id: "TUAR",
    name: "Календарь премьер Петербургских театров",
    short: "Премьеры",
    icon: "calendar-star",
    description: "Театральные премьеры и события",
    count: 5621,
    layout: "list",
    typeIcon: "calendar",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск премьер и событий",
    searchFields: [{
      code: "TI",
      label: "Спектакль"
    }, {
      code: "AU",
      label: "Автор пьесы"
    }, {
      code: "THE",
      label: "Театр"
    }],
    filters: [{
      id: "genre",
      label: "Жанр",
      options: ["Драма", "Опера", "Балет", "Комедия"]
    }],
    // §4/§7.2 TUAR — спецформа с областью «Дата события» и «Библ. источник»
    specialForm: [{
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "text",
      id: "persons",
      label: "Персоны"
    }, {
      kind: "text",
      id: "events",
      label: "Спектакли / события"
    }, {
      kind: "dateEvent",
      id: "date",
      label: "Дата события"
    }, {
      kind: "text",
      id: "troupe",
      label: "Коллектив"
    }, {
      kind: "select",
      id: "etype",
      label: "Вид и тип события",
      options: ["— любой —", "Премьера", "Гастроль", "Бенефис", "Юбилей"]
    }, {
      kind: "text",
      id: "roleP",
      label: "Роли в представлениях"
    }, {
      kind: "sourceArea",
      id: "src",
      label: "Библиографический источник",
      fields: [{
        id: "srcAuthor",
        label: "Автор источника"
      }, {
        id: "srcTitle",
        label: "Заглавие источника"
      }]
    }, {
      kind: "checkbox",
      id: "ecopy",
      label: "Электронная копия программки"
    }]
  }, {
    id: "IMAGE",
    name: "Хронология театральной жизни 1800–1850",
    short: "Хронология",
    icon: "calendar",
    description: "Образы карточек · события",
    count: 4120,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск по хронологии",
    searchFields: [{
      code: "TI",
      label: "Событие / объект"
    }, {
      code: "KW",
      label: "Ключевые слова"
    }],
    filters: [],
    // §7.4 IMAGE — область «Дата события»
    specialForm: [{
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "dateEvent",
      id: "date",
      label: "Дата события"
    }, {
      kind: "text",
      id: "obj",
      label: "Название события / объекта"
    }, {
      kind: "text",
      id: "city",
      label: "Город"
    }, {
      kind: "text",
      id: "country",
      label: "Страна"
    }, {
      kind: "text",
      id: "persons",
      label: "Персоны"
    }, {
      kind: "text",
      id: "troupe",
      label: "Коллектив"
    }, {
      kind: "sourceArea",
      id: "src",
      label: "Библиографический источник",
      fields: [{
        id: "srcAuthor",
        label: "Автор источника"
      }, {
        id: "srcTitle",
        label: "Заглавие источника"
      }]
    }]
  }, {
    id: "IMGZENZ",
    name: "Драматическая цензура",
    short: "Цензура",
    icon: "stamp",
    description: "Образы карточек · цензурные дела",
    count: 3380,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск по драматической цензуре",
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }],
    filters: [],
    specialForm: [{
      kind: "select",
      id: "sep",
      label: "Выбор разделителей",
      options: ["— все —", "По дате", "По цензору", "По театру"]
    }, {
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "text",
      id: "author",
      label: "Автор"
    }, {
      kind: "text",
      id: "title",
      label: "Заглавие"
    }, {
      kind: "select",
      id: "lang",
      label: "Язык",
      options: ["— любой —", "русский", "французский", "немецкий"]
    }]
  }, {
    id: "IMGOPERA",
    group: "libretto",
    name: "Либретто опер, оперетт",
    short: "Либретто опер",
    icon: "music",
    description: "Образы карточек",
    count: 2140,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск либретто опер",
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }],
    filters: [],
    stub: true,
    specialForm: [{
      kind: "select",
      id: "sep",
      label: "Выбор разделителей",
      options: ["— все —", "По композитору", "По театру"]
    }, {
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "text",
      id: "author",
      label: "Автор"
    }, {
      kind: "text",
      id: "title",
      label: "Заглавие"
    }]
  }, {
    id: "IMGBALET",
    group: "libretto",
    name: "Либретто балетов",
    short: "Либретто балетов",
    icon: "music",
    description: "Образы карточек",
    count: 1560,
    layout: "gallery",
    typeIcon: "image",
    simpleLabel: "Я ищу:",
    modes: ["simple", "special"],
    specialTitle: "Поиск либретто балетов",
    searchFields: [{
      code: "TI",
      label: "Заглавие"
    }, {
      code: "AU",
      label: "Автор"
    }],
    filters: [],
    stub: true,
    specialForm: [{
      kind: "text",
      id: "kw",
      label: "Ключевые слова"
    }, {
      kind: "text",
      id: "author",
      label: "Автор"
    }, {
      kind: "text",
      id: "title",
      label: "Заглавие"
    }]
  }];

  // ---- Подсказки словаря (автокомплит), по базам ----
  const dictionaries = {
    EK: [{
      term: "Чайка",
      count: 42
    }, {
      term: "Чехов А. П.",
      count: 318
    }, {
      term: "Чайковский П. И.",
      count: 156
    }, {
      term: "Чацкий",
      count: 11
    }],
    SKETCH: [{
      term: "Чайка — декорация",
      count: 7
    }, {
      term: "Чистяков П. П.",
      count: 23
    }, {
      term: "Чёрное на белом",
      count: 4
    }],
    GUAR: [{
      term: "Чрезвычайная комиссия",
      count: 9
    }, {
      term: "Часть репертуарная",
      count: 14
    }],
    TUAR: [{
      term: "Чайка (1896)",
      count: 3
    }, {
      term: "Чародейка",
      count: 2
    }],
    PLAY: [{
      term: "Чайка",
      count: 5
    }, {
      term: "Чехов А. П.",
      count: 28
    }]
  };

  // ---- Результаты поиска, по базам (обезличенные примеры) ----
  // У каждой записи sourceDb — для мультибазового поиска (§1.4).
  const results = {
    EK: [{
      mfn: 10567,
      title: "Чайка: комедия в четырёх действиях",
      author: "Чехов А. П.",
      year: "1896",
      docType: "Книга",
      availability: "available",
      hasDigital: true
    }, {
      mfn: 10571,
      title: "Чайка и другие пьесы",
      author: "Чехов А. П.",
      year: "1980",
      docType: "Сборник",
      availability: "issued"
    }, {
      mfn: 10588,
      title: "«Чайка» на сцене: режиссёрские прочтения",
      author: "Громова М. И.",
      year: "2014",
      docType: "Книга",
      availability: "available",
      hasDigital: true
    }, {
      mfn: 10592,
      title: "Поэтика драмы Чехова",
      author: "Скафтымов А. П.",
      year: "1972",
      docType: "Книга",
      availability: "available"
    }, {
      mfn: 10601,
      title: "Театр Чехова: комментарии",
      author: "Бердников Г. П.",
      year: "1981",
      docType: "Книга",
      availability: "unknown"
    }, {
      mfn: 10610,
      title: "Чайка. Дядя Ваня. Три сестры. Вишнёвый сад",
      author: "Чехов А. П.",
      year: "2008",
      docType: "Сборник",
      availability: "available",
      hasDigital: true
    }],
    SKETCH: [{
      mfn: 50012,
      title: "Эскиз декорации к спектаклю «Чайка», III акт",
      author: "Симов В. А.",
      year: "1898",
      docType: "Эскиз декорации",
      availability: "available",
      fields: [{
        label: "Техника",
        value: "Акварель"
      }],
      tint: 18
    }, {
      mfn: 50018,
      title: "Эскиз костюма Нины Заречной",
      author: "Симов В. А.",
      year: "1898",
      docType: "Эскиз костюма",
      availability: "available",
      fields: [{
        label: "Техника",
        value: "Гуашь"
      }],
      tint: 168
    }, {
      mfn: 50031,
      title: "Афиша премьеры «Чайки»",
      author: "—",
      year: "1898",
      docType: "Афиша",
      availability: "issued",
      fields: [{
        label: "Техника",
        value: "Литография"
      }],
      tint: 38
    }, {
      mfn: 50044,
      title: "Эскиз декорации: усадебный сад",
      author: "Симов В. А.",
      year: "1898",
      docType: "Эскиз декорации",
      availability: "available",
      fields: [{
        label: "Техника",
        value: "Акварель"
      }],
      tint: 128
    }, {
      mfn: 50051,
      title: "Эскиз грима для роли Тригорина",
      author: "Неизв.",
      year: "1898",
      docType: "Эскиз костюма",
      availability: "unknown",
      fields: [{
        label: "Техника",
        value: "Карандаш"
      }],
      tint: 268
    }, {
      mfn: 50060,
      title: "Эскиз занавеса",
      author: "Симов В. А.",
      year: "1902",
      docType: "Эскиз декорации",
      availability: "available",
      fields: [{
        label: "Техника",
        value: "Гуашь"
      }],
      tint: 318
    }],
    GUAR: [{
      mfn: 70003,
      title: "Дело о постановке пьесы «Чайка» в сезон 1898/99",
      author: "—",
      year: "1898–1899",
      docType: "Архивное дело",
      availability: "available",
      recLevel: "opis",
      fields: [{
        label: "Фонд",
        value: "Ф. 1, оп. 2"
      }, {
        label: "Листов",
        value: "47"
      }]
    }, {
      mfn: 70011,
      title: "Переписка дирекции о репертуаре",
      author: "—",
      year: "1897–1900",
      docType: "Архивное дело",
      availability: "available",
      recLevel: "opis",
      fields: [{
        label: "Фонд",
        value: "Ф. 1, оп. 2"
      }, {
        label: "Листов",
        value: "112"
      }]
    }, {
      mfn: 70025,
      title: "Цензурные разрешения на драматические сочинения",
      author: "—",
      year: "1895–1898",
      docType: "Архивное дело",
      availability: "issued",
      recLevel: "opis",
      fields: [{
        label: "Фонд",
        value: "Ф. 2, оп. 1"
      }, {
        label: "Листов",
        value: "203"
      }]
    }, {
      mfn: 70100,
      title: "Ф. 1 — Дирекция Императорских театров",
      author: "—",
      year: "1842–1917",
      docType: "Фонд",
      availability: "available",
      recLevel: "fond",
      fields: [{
        label: "Описей",
        value: "6"
      }, {
        label: "Дел",
        value: "1 240"
      }]
    }],
    TUAR: [{
      mfn: 90002,
      title: "«Чайка» — премьера",
      author: "Чехов А. П.",
      year: "17 декабря 1898",
      docType: "Премьера",
      availability: "available",
      fields: [{
        label: "Театр",
        value: "Художественный театр"
      }, {
        label: "Жанр",
        value: "Драма"
      }]
    }, {
      mfn: 90007,
      title: "«Чародейка» — премьера оперы",
      author: "Чайковский П. И.",
      year: "20 октября 1887",
      docType: "Премьера",
      availability: "available",
      fields: [{
        label: "Театр",
        value: "Мариинский театр"
      }, {
        label: "Жанр",
        value: "Опера"
      }]
    }],
    PLAY: [{
      mfn: 60001,
      title: "Чайка: комедия в четырёх действиях",
      author: "Чехов А. П.",
      year: "1896",
      docType: "Пьеса",
      availability: "available",
      fields: [{
        label: "Жанр",
        value: "Комедия"
      }, {
        label: "Действий",
        value: "4"
      }]
    }, {
      mfn: 60004,
      title: "Вишнёвый сад: комедия в четырёх действиях",
      author: "Чехов А. П.",
      year: "1904",
      docType: "Пьеса",
      availability: "available",
      fields: [{
        label: "Жанр",
        value: "Комедия"
      }, {
        label: "Действий",
        value: "4"
      }]
    }]
  };

  // ---- Полные карточки записей (по mfn) ----
  // files: §9 контракт (951/955, priority, viewOnly, requiresAuth, kind).
  // links: f488 (Фонд↔Опись GUAR), f390 (цветная ссылка на ЭК), f481 (связь).
  const records = {
    10567: {
      mfn: 10567,
      db: "EK",
      title: "Чайка: комедия в четырёх действиях",
      author: "Чехов А. П.",
      imprint: {
        publisher: "Типография А. С. Суворина",
        year: "1896"
      },
      badges: [{
        variant: "accent",
        text: "Пьеса"
      }, {
        variant: "success",
        text: "Полный текст"
      }],
      pftHtml: '<p><b>Чехов, Антон Павлович</b> (1860–1904).</p>' + '<p>Чайка : комедия в четырёх действиях / А. П. Чехов. — Санкт-Петербург : Типография А. С. Суворина, 1896. — 84 с. ; 21 см.</p>' + '<dl><dt>Жанр</dt><dd>Драматургия. Комедия.</dd>' + '<dt>Язык</dt><dd>Русский</dd>' + '<dt>Первая постановка</dt><dd>Александринский театр, 17 октября 1896 г.</dd></dl>' + '<p>Премьера в Художественном театре (1898) принесла пьесе признание; чайка стала эмблемой театра.</p>',
      subjects: ["Русская драматургия", "Пьесы", "Чехов А. П.", "Театр"],
      links: {
        f390: {
          target: "PLAY",
          mfn: 60001,
          label: "Текст пьесы в указателе пьес"
        },
        f481: [10610]
      },
      files: [{
        field: "955",
        label: "Электронная версия",
        kind: "pdf",
        viewOnly: true,
        requiresAuth: true,
        priority: 1,
        pages: 84
      }, {
        field: "951",
        label: "Полный текст",
        kind: "pdf",
        viewOnly: true,
        requiresAuth: false,
        priority: 2,
        pages: 84
      }],
      holdings: [{
        location: "Основной фонд",
        inventory: "К-12345",
        status: "available"
      }, {
        location: "Отдел редкой книги",
        inventory: "РК-0087",
        status: "available"
      }, {
        location: "Филиал №2",
        inventory: "К-12346",
        status: "issued"
      }],
      sigla: [{
        code: "СПбГТБ",
        name: "СПб гос. театральная библиотека",
        count: 3,
        here: true
      }, {
        code: "РНБ",
        name: "Российская национальная библиотека",
        count: 2
      }, {
        code: "БАН",
        name: "Библиотека Академии наук",
        count: 1
      }]
    },
    50012: {
      mfn: 50012,
      db: "SKETCH",
      title: "Эскиз декорации к спектаклю «Чайка», III акт",
      author: "Симов В. А.",
      imprint: {
        publisher: "—",
        year: "1898"
      },
      tint: 18,
      badges: [{
        variant: "accent",
        text: "Эскиз декорации"
      }],
      pftHtml: '<p><b>Симов, Виктор Андреевич</b> (1858–1935).</p>' + '<p>Эскиз декорации к спектаклю «Чайка», действие III. — 1898. — Бумага, акварель ; 32 × 47 см.</p>' + '<dl><dt>Техника</dt><dd>Бумага, акварель</dd>' + '<dt>Постановка</dt><dd>Московский Художественный театр, 1898</dd>' + '<dt>Размер</dt><dd>32 × 47 см</dd></dl>',
      subjects: ["Сценография", "Симов В. А.", "Чайка (постановка)"],
      files: [{
        field: "955",
        label: "Изображение эскиза",
        kind: "image",
        viewOnly: true,
        requiresAuth: false,
        priority: 1,
        tint: 18
      }],
      holdings: [{
        location: "Эскизный фонд, папка 12",
        inventory: "Э-0451",
        status: "available"
      }]
    },
    70003: {
      mfn: 70003,
      db: "GUAR",
      title: "Дело о постановке пьесы «Чайка» в сезон 1898/99",
      author: "—",
      imprint: {
        publisher: "—",
        year: "1898–1899"
      },
      recLevel: "opis",
      badges: [{
        variant: "neutral",
        text: "Архивное дело"
      }],
      pftHtml: '<dl><dt>Фонд</dt><dd>Ф. 1 — Дирекция Императорских театров</dd>' + '<dt>Опись</dt><dd>оп. 2</dd><dt>Дело</dt><dd>№ 314</dd>' + '<dt>Крайние даты</dt><dd>1898 — 1899</dd><dt>Объём</dt><dd>47 листов</dd></dl>' + '<p>Переписка, сметы и распоряжения по постановке. Машинопись и рукопись.</p>',
      subjects: ["Дирекция театров", "Репертуар", "1898"],
      links: {
        f488: {
          label: "Перейти к фонду",
          mfn: 70100,
          level: "fond"
        }
      },
      files: [{
        field: "951",
        label: "Опись дела",
        kind: "pdf",
        viewOnly: true,
        requiresAuth: false,
        priority: 1,
        pages: 12
      }],
      holdings: [{
        location: "Архивохранилище, ряд 4",
        inventory: "Ф1-оп2-314",
        status: "available"
      }]
    },
    70100: {
      mfn: 70100,
      db: "GUAR",
      title: "Ф. 1 — Дирекция Императорских театров",
      author: "—",
      imprint: {
        publisher: "—",
        year: "1842–1917"
      },
      recLevel: "fond",
      badges: [{
        variant: "neutral",
        text: "Фонд"
      }],
      pftHtml: '<dl><dt>Номер фонда</dt><dd>Ф. 1</dd><dt>Название</dt><dd>Дирекция Императорских театров</dd>' + '<dt>Крайние даты</dt><dd>1842 — 1917</dd><dt>Описей</dt><dd>6</dd><dt>Дел</dt><dd>1 240</dd></dl>' + '<p>Фонд объединяет делопроизводство дирекции: репертуар, труппа, постановки, цензурная переписка.</p>',
      subjects: ["Дирекция театров", "Архивный фонд"],
      links: {
        f488: {
          label: "К описи дел сезона 1898/99",
          mfn: 70003,
          level: "opis"
        }
      },
      files: [],
      holdings: []
    },
    90002: {
      mfn: 90002,
      db: "TUAR",
      title: "«Чайка» — премьера",
      author: "Чехов А. П.",
      imprint: {
        publisher: "Художественный театр",
        year: "1898"
      },
      badges: [{
        variant: "accent",
        text: "Драма"
      }],
      pftHtml: '<dl><dt>Спектакль</dt><dd>Чайка</dd><dt>Автор</dt><dd>А. П. Чехов</dd>' + '<dt>Театр</dt><dd>Московский Художественный театр</dd>' + '<dt>Дата премьеры</dt><dd>17 декабря 1898</dd>' + '<dt>Режиссёр</dt><dd>К. С. Станиславский, Вл. И. Немирович-Данченко</dd></dl>',
      subjects: ["Премьеры", "МХТ", "Чехов А. П."],
      links: {
        f390: {
          target: "PLAY",
          mfn: 60001,
          label: "Пьеса в указателе пьес"
        }
      },
      files: [{
        field: "955",
        label: "Программка премьеры",
        kind: "image",
        viewOnly: true,
        requiresAuth: false,
        priority: 1,
        tint: 38
      }],
      holdings: []
    },
    60001: {
      mfn: 60001,
      db: "PLAY",
      title: "Чайка: комедия в четырёх действиях",
      author: "Чехов А. П.",
      imprint: {
        publisher: "—",
        year: "1896"
      },
      badges: [{
        variant: "accent",
        text: "Комедия"
      }],
      pftHtml: '<dl><dt>Заглавие</dt><dd>Чайка</dd><dt>Автор</dt><dd>А. П. Чехов</dd>' + '<dt>Жанр</dt><dd>Комедия</dd><dt>Количество действий</dt><dd>4</dd>' + '<dt>Роли</dt><dd>женские — 3, мужские — 6, эпизодические — 4</dd>' + '<dt>Время действия</dt><dd>конец XIX века</dd></dl>',
      subjects: ["Русская драматургия", "Комедия", "Чехов А. П."],
      links: {
        f390: {
          target: "EK",
          mfn: 10567,
          label: "Издание в электронном каталоге"
        }
      },
      files: [{
        field: "951",
        label: "Текст пьесы",
        kind: "pdf",
        viewOnly: true,
        requiresAuth: false,
        priority: 1,
        pages: 84
      }],
      holdings: [{
        location: "Читальный зал",
        inventory: "П-2210",
        status: "available"
      }]
    }
  };

  // ---- Личный кабинет (минимум ПДн, 152-ФЗ) ----
  const account = {
    ticket: "00012345",
    lastName: "Читатель",
    displayName: "И. О.",
    loans: [{
      title: "Чайка и другие пьесы",
      due: "01.07.2026",
      location: "Филиал №2",
      renewable: true
    }, {
      title: "Поэтика драмы Чехова",
      due: "10.07.2026",
      location: "Основной фонд",
      renewable: true
    }, {
      title: "Театр Чехова: комментарии",
      due: "24.06.2026",
      location: "Основной фонд",
      renewable: false,
      overdueSoon: true
    }],
    orders: [],
    bookmarks: [{
      mfn: 10567,
      db: "EK",
      title: "Чайка: комедия в четырёх действиях",
      author: "Чехов А. П."
    }, {
      mfn: 50012,
      db: "SKETCH",
      title: "Эскиз декорации к спектаклю «Чайка», III акт",
      author: "Симов В. А."
    }],
    savedQueries: [{
      id: "q1",
      label: "Чехов А. П.",
      db: "Электронный каталог",
      fresh: 3
    }, {
      id: "q2",
      label: "эскиз костюма",
      db: "Эскизный фонд",
      fresh: 0
    }],
    notifications: [{
      id: "n1",
      icon: "clock",
      tone: "issued",
      title: "Скоро срок возврата",
      text: "«Театр Чехова: комментарии» — вернуть до 24.06.2026.",
      unread: true
    }, {
      id: "n2",
      icon: "check-circle",
      tone: "available",
      title: "Заказ готов к выдаче",
      text: "«Чайка и другие пьесы» ждёт на бронеполке, Филиал №2.",
      unread: true
    }, {
      id: "n3",
      icon: "bell",
      tone: "neutral",
      title: "Новое в постоянном запросе",
      text: "По запросу «Чехов А. П.» — 3 новые записи.",
      unread: false
    }],
    fines: [{
      id: "f1",
      reason: "Просрочка возврата (5 дн.)",
      amount: 50,
      date: "18.06.2026"
    }, {
      id: "f2",
      reason: "Просрочка возврата (2 дн.)",
      amount: 20,
      date: "11.06.2026"
    }]
  };

  // ---- Сотрудник: гранты по доменам (ACCESS_MODEL §3) ----
  // Навигация собирается ПО ГРАНТАМ, а не по АРМам. Уровни: read/write/delete/admin.
  const staff = {
    displayName: "Сотрудник",
    role: "Каталогизатор-библиотекарь",
    // Гранты текущей учётки (демо: совмещает несколько доменов).
    grants: {
      catalog: "read",
      cataloging: "write",
      circulation: "write",
      acquisition: "read",
      inventory: "write",
      analytics: "read",
      admin: "none"
    },
    // Каталог задач по доменам — показываем только разрешённое.
    domains: [{
      id: "cataloging",
      label: "Каталогизация",
      icon: "edit",
      desc: "Рабочие листы, ФЛК, импорт",
      need: "write",
      tasks: [{
        id: "cat-new",
        label: "Новая запись",
        icon: "plus"
      }, {
        id: "cat-list",
        label: "Поиск и правка",
        icon: "search"
      }, {
        id: "cat-global",
        label: "Глобальная корректировка",
        icon: "sliders"
      }, {
        id: "cat-import",
        label: "Импорт (copy-cataloging)",
        icon: "download"
      }]
    }, {
      id: "circulation",
      label: "Книговыдача",
      icon: "scan-line",
      desc: "Выдача, возврат, очередь, бронеполка",
      need: "write",
      tasks: [{
        id: "circ-issue",
        label: "Выдача / возврат",
        icon: "scan-line"
      }, {
        id: "circ-queue",
        label: "Очередь заказов",
        icon: "clock",
        badge: 7
      }, {
        id: "circ-shelf",
        label: "Бронеполка",
        icon: "bookmark"
      }, {
        id: "circ-debt",
        label: "Должники",
        icon: "alert-triangle",
        badge: 3
      }]
    }, {
      id: "acquisition",
      label: "Комплектование",
      icon: "package",
      desc: "Заказ → поступление → КСУ → списание",
      need: "read",
      tasks: [{
        id: "acq-order",
        label: "Заказы поставщикам",
        icon: "package"
      }, {
        id: "acq-ksu",
        label: "КСУ",
        icon: "file-text"
      }]
    }, {
      id: "inventory",
      label: "Инвентаризация",
      icon: "clipboard-check",
      desc: "Онлайн-сверка с ТСД/сканера",
      need: "write",
      tasks: [{
        id: "inv-session",
        label: "Сессия сверки (ТСД)",
        icon: "scan-line"
      }, {
        id: "inv-report",
        label: "Отчёт расхождений",
        icon: "file-text"
      }]
    }, {
      id: "analytics",
      label: "Аналитика",
      icon: "bar-chart",
      desc: "BI-дашборды фонда и выдачи",
      need: "read",
      tasks: [{
        id: "an-dash",
        label: "Дашборд",
        icon: "bar-chart"
      }]
    }, {
      id: "admin",
      label: "Администрирование",
      icon: "shield",
      desc: "Учётки, гранты, аудит",
      need: "admin",
      tasks: []
    }],
    // Сводка рабочего стола
    summary: [{
      label: "Заказов в очереди",
      value: 7,
      icon: "clock",
      tone: "issued"
    }, {
      label: "На бронеполке",
      value: 12,
      icon: "bookmark",
      tone: "available"
    }, {
      label: "Должников",
      value: 3,
      icon: "alert-triangle",
      tone: "danger"
    }, {
      label: "Черновиков записей",
      value: 4,
      icon: "edit",
      tone: "neutral"
    }]
  };

  // ---- Профиль каталогизации (рабочий лист) для базы «Книги» ----
  // Источник по типам ввода — FIELD_CATALOG (демо-срез). Поля рендерит DynamicField.
  const catalogingProfiles = {
    EK: {
      db: "EK",
      dbName: "Электронный каталог (книги)",
      pages: [{
        id: "main",
        label: "Основное описание",
        fields: [{
          code: "200^a",
          label: "Заглавие",
          type: "text",
          required: true,
          placeholder: "Основное заглавие"
        }, {
          code: "200^e",
          label: "Сведения, относящиеся к заглавию",
          type: "text",
          placeholder: "подзаголовочные данные"
        }, {
          code: "700",
          label: "Первый автор",
          type: "text",
          repeatable: false,
          subfields: [{
            code: "a",
            label: "Фамилия",
            type: "dict",
            dictionary: [{
              term: "Чехов А. П.",
              count: 318
            }, {
              term: "Чайковский П. И.",
              count: 156
            }]
          }, {
            code: "b",
            label: "Инициалы",
            type: "text"
          }, {
            code: "4",
            label: "Роль",
            type: "menu",
            options: ["Автор", "Редактор", "Переводчик", "Составитель"]
          }]
        }, {
          code: "701",
          label: "Прочие авторы",
          type: "text",
          repeatable: true,
          subfields: [{
            code: "a",
            label: "Фамилия",
            type: "dict",
            dictionary: [{
              term: "Громова М. И."
            }, {
              term: "Скафтымов А. П."
            }]
          }, {
            code: "b",
            label: "Инициалы",
            type: "text"
          }]
        }, {
          code: "900",
          label: "Вид документа",
          type: "menu",
          required: true,
          options: ["Книга", "Сборник", "Многотомник", "Продолжающееся издание"]
        }, {
          code: "101^a",
          label: "Язык текста",
          type: "menu",
          options: ["rus — русский", "eng — английский", "fre — французский", "ger — немецкий"]
        }]
      }, {
        id: "imprint",
        label: "Выходные данные",
        fields: [{
          code: "210^a",
          label: "Место издания",
          type: "text",
          placeholder: "Санкт-Петербург"
        }, {
          code: "210^c",
          label: "Издательство",
          type: "authority",
          authority: [{
            term: "Типография А. С. Суворина",
            code: "PUB-014"
          }, {
            term: "Academia",
            code: "PUB-220"
          }]
        }, {
          code: "210^d",
          label: "Год издания",
          type: "date",
          required: true,
          placeholder: "ГГГГ",
          hint: "Формат: 4 цифры года"
        }, {
          code: "215^a",
          label: "Объём (с.)",
          type: "text",
          placeholder: "84 с."
        }]
      }, {
        id: "subjects",
        label: "Содержание и рубрики",
        fields: [{
          code: "606",
          label: "Рубрика ГРНТИ",
          type: "tree",
          tree: [{
            code: "18",
            label: "Искусство. Искусствоведение",
            children: [{
              code: "18.45",
              label: "Театр. Театроведение",
              children: [{
                code: "18.45.09",
                label: "Драматический театр"
              }, {
                code: "18.45.21",
                label: "Музыкальный театр. Опера. Балет"
              }]
            }, {
              code: "18.41",
              label: "Музыка"
            }]
          }, {
            code: "17",
            label: "Литература. Литературоведение",
            children: [{
              code: "17.07",
              label: "Теория литературы"
            }, {
              code: "17.82",
              label: "Художественная литература",
              children: [{
                code: "17.82.31",
                label: "Драматургия"
              }]
            }]
          }]
        }, {
          code: "601",
          label: "Предметная рубрика",
          type: "authority",
          repeatable: true,
          authority: [{
            term: "Русская драматургия",
            code: "AU-1042"
          }, {
            term: "Театр — История",
            code: "AU-2087"
          }, {
            term: "Пьесы",
            code: "AU-3310"
          }]
        }, {
          code: "610",
          label: "Ключевые слова",
          type: "text",
          repeatable: true,
          placeholder: "термин"
        }, {
          code: "330^a",
          label: "Аннотация",
          type: "text",
          placeholder: "краткое содержание"
        }]
      }, {
        id: "holdings",
        label: "Экземпляры",
        fields: [{
          code: "910",
          label: "Экземпляр",
          type: "text",
          repeatable: true,
          subfields: [{
            code: "a",
            label: "Статус",
            type: "menu",
            options: ["0 — доступен", "1 — выдан", "5 — в обработке"]
          }, {
            code: "b",
            label: "Инв. номер",
            type: "text"
          }, {
            code: "d",
            label: "Место хранения",
            type: "menu",
            options: ["Основной фонд", "Отдел редкой книги", "Филиал №2", "Читальный зал"]
          }, {
            code: "e",
            label: "Полка / ячейка",
            type: "text"
          }]
        }, {
          code: "905",
          label: "Есть электронная версия",
          type: "bool",
          options: ["Да", "Нет"]
        }]
      }]
    }
  };

  // ---- Книговыдача / Инвентаризация / Аналитика (демо) ----
  const staffData = {
    // Карточка читателя при сканировании билета
    reader: {
      ticket: "00012345",
      display: "Читатель И. О.",
      category: "Студент",
      valid: "до 31.12.2026",
      onHand: 3,
      debt: 0,
      overdue: 1,
      items: [{
        title: "Чайка и другие пьесы",
        inv: "К-12346",
        due: "01.07.2026",
        status: "ok"
      }, {
        title: "Поэтика драмы Чехова",
        inv: "К-19022",
        due: "10.07.2026",
        status: "ok"
      }, {
        title: "Театр Чехова: комментарии",
        inv: "К-10711",
        due: "24.06.2026",
        status: "overdue"
      }]
    },
    queue: [{
      ticket: "00012345",
      reader: "Читатель И. О.",
      title: "Чайка: комедия в четырёх действиях",
      inv: "К-12345",
      placed: "18.06",
      status: "ready",
      location: "Основной фонд"
    }, {
      ticket: "00033120",
      reader: "Читатель А. С.",
      title: "Вишнёвый сад",
      inv: "К-22019",
      placed: "19.06",
      status: "queued",
      location: "Филиал №2"
    }, {
      ticket: "00041255",
      reader: "Читатель М. П.",
      title: "Эскиз декорации к «Чайке»",
      inv: "Э-0451",
      placed: "19.06",
      status: "queued",
      location: "Эскизный фонд"
    }],
    shelf: [{
      cell: "Б-01",
      title: "Чайка: комедия в четырёх действиях",
      reader: "Читатель И. О.",
      hold: "до 23.06"
    }, {
      cell: "Б-02",
      title: "Три сестры",
      reader: "Читатель Н. К.",
      hold: "до 22.06"
    }, {
      cell: "Б-05",
      title: "Дядя Ваня",
      reader: "Читатель Д. Е.",
      hold: "до 24.06"
    }],
    // Инвентаризация — сессия сверки с ТСД
    inventory: {
      session: "ИНВ-2026-07",
      location: "Основной фонд, ряд 4",
      total: 1240,
      scanned: 0,
      expected: [{
        inv: "К-12345",
        title: "Чайка: комедия в четырёх действиях"
      }, {
        inv: "К-12346",
        title: "Чайка и другие пьесы"
      }, {
        inv: "К-10711",
        title: "Театр Чехова: комментарии"
      }, {
        inv: "К-19022",
        title: "Поэтика драмы Чехова"
      }, {
        inv: "К-22019",
        title: "Вишнёвый сад"
      }, {
        inv: "К-30015",
        title: "Драматургия Серебряного века"
      }]
    },
    // BI-дашборд
    dashboard: {
      kpis: [{
        label: "Выдач за месяц",
        value: "4 218",
        delta: "+8%",
        tone: "available"
      }, {
        label: "Возвратов",
        value: "3 960",
        delta: "+5%",
        tone: "available"
      }, {
        label: "Новых читателей",
        value: "112",
        delta: "+14%",
        tone: "available"
      }, {
        label: "Просрочки",
        value: "37",
        delta: "−6%",
        tone: "issued"
      }],
      monthly: [{
        m: "Янв",
        v: 60
      }, {
        m: "Фев",
        v: 72
      }, {
        m: "Мар",
        v: 95
      }, {
        m: "Апр",
        v: 88
      }, {
        m: "Май",
        v: 76
      }, {
        m: "Июн",
        v: 100
      }],
      topDb: [{
        label: "Электронный каталог",
        pct: 64
      }, {
        label: "Эскизный фонд",
        pct: 16
      }, {
        label: "Указатель пьес",
        pct: 11
      }, {
        label: "Архив (GUAR)",
        pct: 9
      }]
    }
  };

  // ---- Профили библиотек: у КАЖДОЙ свой скин (тема) + бренд (§9) ----
  // Конфигурируется декларативно: добавить библиотеку = добавить запись,
  // без правки кода. Текущая библиотека задаёт название в шапке и скин по умолчанию.
  const libraries = [{
    id: "spbgtb",
    theme: "theatrical",
    name: "Санкт-Петербургская государственная театральная библиотека",
    short: "Театральная библиотека",
    monogram: "ТБ",
    tagline: "электронный каталог",
    city: "Санкт-Петербург"
  }, {
    id: "nauchka",
    theme: "azure",
    name: "Научная библиотека университета",
    short: "Научная библиотека",
    monogram: "НБ",
    tagline: "электронный каталог и базы данных",
    city: "—"
  }, {
    id: "publichka",
    theme: "pine",
    name: "Центральная городская публичная библиотека",
    short: "Городская библиотека",
    monogram: "ГБ",
    tagline: "каталог и читательские сервисы",
    city: "—"
  }, {
    id: "neutral",
    theme: "working",
    name: "Библиотечный электронный каталог",
    short: "Электронный каталог",
    monogram: "ЭК",
    tagline: "поиск по базам данных",
    city: "—"
  }];
  window.IRBIS_DATA = {
    groups,
    databases,
    dictionaries,
    results,
    records,
    account,
    staff,
    catalogingProfiles,
    staffData,
    libraries
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/irbis-web/data.js", error: String((e && e.message) || e) }); }

__ds_ns.DatabaseSelector = __ds_scope.DatabaseSelector;

__ds_ns.HoldingsTable = __ds_scope.HoldingsTable;

__ds_ns.Pagination = __ds_scope.Pagination;

__ds_ns.PftBlock = __ds_scope.PftBlock;

__ds_ns.ResultCard = __ds_scope.ResultCard;

__ds_ns.SearchBar = __ds_scope.SearchBar;

__ds_ns.SearchModes = __ds_scope.SearchModes;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.SubjectTag = __ds_scope.SubjectTag;

__ds_ns.TreeNav = __ds_scope.TreeNav;

__ds_ns.DynamicField = __ds_scope.DynamicField;

__ds_ns.Alert = __ds_scope.Alert;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.EmptyState = __ds_scope.EmptyState;

__ds_ns.Skeleton = __ds_scope.Skeleton;

__ds_ns.SkeletonResult = __ds_scope.SkeletonResult;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.ToastViewport = __ds_scope.ToastViewport;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.FilterChip = __ds_scope.FilterChip;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.ICON_NAMES = __ds_scope.ICON_NAMES;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.FileViewer = __ds_scope.FileViewer;

})();
