---
name: library-catalog-design
description: Use this skill to generate well-branded interfaces and assets for the library web catalog (irbis-web) — a Russian-language public library catalog over IRBIS64 — for production or throwaway prototypes/mocks. Contains design guidelines, color/type/spacing tokens, local fonts, 8 themes (incl. per-library skins + dark + a11y), an icon set, reusable React components, and config-driven UI kits for reader and staff (search, results, record card, account, ordering, cataloging worksheet, circulation, inventory, dashboard).
user-invocable: true
---

Read the `readme.md` file within this skill, then explore the other files.

This is the design system for a **Russian-language public library web catalog** (`irbis-web`) over
IRBIS64 with a restrained "library-archival" character and a theatrical accent. Interface language
is **Russian**. The brand is the **library's own name** (configurable), not "ИРБИС".

Key things to know:
- **Tokens** live in `styles.css` → `tokens/*.css`. Themes switch via `data-theme` on the root
  container; only semantic aliases change. Themes: default `working` (бумага, light),
  `azure`/`pine` (light per-library skins), `theatrical` (reader skin), `dark`, seasonal
  `newyear`/`march8`, and `a11y` (high contrast, ГОСТ Р 52872-2019).
- **Per-library profiles:** `ui_kits/irbis-web/data.js → libraries` — each library has its own
  brand (name, monogram, tagline) and skin (theme). Header shows the library name. Adding a
  library = adding a config record.
- **Components** are React (`components/<group>/<Name>.jsx`) with `.d.ts` contracts and
  `.prompt.md` usage notes. Icons come only from `<Icon name="…">` (local set, no raw SVG/emoji).
  Key components: DatabaseSelector (hierarchical multi-select), SearchBar, SearchModes, TreeNav
  (ГРНТИ/УДК/ББК), ResultCard, StatusBadge, HoldingsTable, PftBlock, Pagination, FileViewer
  (view-only), DynamicField (cataloging field → control), plus forms/feedback/navigation primitives.
- **Config-driven screens:** databases are data (`data.js`); screens render from the config.
  Adding a database = adding config, not rewriting screens. Two contexts: **Reader** (search →
  record → order → account) and **Staff** (grant-based desktop → cataloging worksheet,
  circulation, inventory-with-TSD, BI dashboard).
- **Fonts** are local/system-safe stacks (PT Sans/Serif/Mono) — no external font hosting.
- **Constraints to respect (SECURITY / 152-ФЗ):** no real PII, minimal personal data in account
  screens, no service errors surfaced to users (friendly text only), no external CDNs/trackers,
  files served view-only via proxy (no direct links), statuses always conveyed by colour + icon +
  text, navigation built **by grants, not by АРМ**.

Target production stack (per project ТЗ §10): **React + TypeScript + Tailwind**. The JSX here uses
CSS custom properties (not Tailwind) — port tokens to `tailwind.config` (see
`design_handoff_irbis_web/README.md`) and recreate components with the codebase's patterns.

If creating visual artifacts (mocks, throwaway prototypes, slides), copy assets out and produce
static HTML files for the user to view. If working on production code, copy assets and follow the
rules here to design as an expert in this brand.

If the user invokes this skill without further guidance, ask what they want to build, ask a few
focused questions, then act as an expert designer who outputs HTML artifacts **or** production
React + TypeScript + Tailwind code, depending on the need.
