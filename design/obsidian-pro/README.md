# Obsidian Pro Design System

> A professional dark-mode design system purpose-built for security and governance tooling.

Obsidian Pro is the visual language for **Connection's security practice** — it powers customer-facing deliverables, presales assets, CoE outputs, summit dashboards, and security tools across multiple products. It is opinionated, signal-first, and dark-by-default with a parity light theme for reports and print.

The system was designed to load directly into Claude Design as a team design system so every prototype, dashboard and deliverable inherits the right colors, type, spacing, and component patterns without manual respec.

---

## Brand context

**Tagline (working):** *Cybersecurity tools made for the community.*

The look-and-feel draws directly from leading security platforms — Wiz, CrowdStrike, Vanta — where the product spans dashboards, reports, and product pages. The brand promise is **clarity over decoration**: color is reserved for risk state, typography uses dramatic scale contrast (10px labels against 30px metrics) so dashboards are scannable in seconds, and information is structured in three progressive layers: *glanceable metrics → scannable tables → actionable detail*.

### Surfaces this system covers

| Surface | What it looks like |
|---|---|
| **Security tooling dashboards** | Detection consoles, asset inventories, vulnerability triage |
| **CoE deliverables / reports** | PDF-bound assessments, posture summaries, executive briefs |
| **Presales assets** | Slide decks, pitch one-pagers, scoring rubrics |
| **Product pages** | Marketing surfaces describing tools to security teams |

### Source materials given

- `uploads/ds-tokens.css` — full v1.1 token file (mirrored at `ds-tokens.css` in the project root)
- `uploads/ds-components.html` — single-page component library reference (mirrored at `ds-components.html`)

If you need the originals, they are preserved in `uploads/`.

---

## Content fundamentals

The voice is **calm, precise, technical** — written for security practitioners who already speak the vocabulary. Never marketing-y. Never breezy.

### Tone
- **Confident, not loud.** State the finding. Don't sell it.
- **Practitioner-to-practitioner.** Assume the reader knows what CVSS, MTTR, and lateral movement mean. No hand-holding.
- **Signal over commentary.** Lead with the number, the CVE, the host. Prose comes after.

### Casing
- **Lowercase severity labels** in chips and table cells: `critical`, `high`, `ok`, `medium`. These are status values, not titles.
- **Title Case for screen names**: Dashboard, Detections, Assets, Policies.
- **ALL CAPS + tracking** for eyebrow labels (10px, `letter-spacing: 0.08em`). Reserve for section dividers, stat labels, table headers.
- **Sentence case** for body and CTAs (`Investigate`, `Assign`, `Dismiss` — never `INVESTIGATE`).

### Voice
- **Use "you" sparingly.** Most copy is descriptive ("3 critical findings need action"), not addressed.
- **Imperative for actions.** Buttons read as commands: *Investigate*, *Patch*, *Assign*, *Dismiss*, *Quarantine*.
- **No emoji.** Ever. They break the signal. Use semantic badges + dot indicators instead.
- **No exclamation marks.** Severity is conveyed by color and scale, not punctuation.

### Examples

✓ *needs action* (badge text on a critical stat card)
✓ *Mimikatz on SRV-DC01* (detection title — proper noun + host)
✓ *↑ 8 points from last assessment* (delta caption)
✓ *Enable continuous monitoring* (settings checkbox)

✗ *Looks like you've got 3 critical alerts! 🚨* (too breezy, emoji, exclamation)
✗ *URGENT: TAKE ACTION NOW* (shouting; rely on color + position instead)

### Numbers and data
- Always **monospace** for numerics: counts, IDs, timestamps, CVSS scores, CVEs.
- **Tabular figures** are non-negotiable in tables (`font-feature-settings: 'tnum'`).
- Round only when it improves scannability — `4.2h` not `4.183h`. Never round CVSS or CVE IDs.

---

## Visual foundations

### Colors

A single opinionated palette. **Color is reserved for severity** — never decorative. The accent indigo is reserved for interactive elements (primary buttons, focused inputs, active nav).

| Role | Dark | Light | Use |
|---|---|---|---|
| Page | `#080a0f` | `#f6f7fb` | Outermost shell |
| Base | `#0d0f14` | `#ffffff` | App / card bg |
| Surface | `#161921` | `#f1f3f9` | Raised, hover row |
| Elevated | `#1e2129` | `#ffffff` | Modals, dropdowns |
| Border | `#252d3e` | `#d8dde8` | Default |
| Text | `#f0f2f8` | `#11141c` | Primary |
| Muted | `#6e7a95` | `#525e78` | Labels, secondary |
| Faint | `#4a5568` | `#8a93a8` | Placeholder, disabled |
| Accent | `#6675f7` | `#4f5fe6` | Primary action |
| Critical | `#e05555` | `#c83a3a` | Immediate action |
| High | `#d4893a` | `#b46b1b` | Elevated risk |
| OK | `#3fa876` | `#2c8a5d` | Healthy / resolved |
| Medium | `#8892a4` | `#6c7589` | Neutral / informational |

### Typography

- **UI / body:** `system-ui, -apple-system, 'Segoe UI', sans-serif` — chosen for 0-config performance and platform native feel.
- **Data / mono:** `JetBrains Mono` — **brand TTFs shipped in `fonts/`** (full axis: Thin → ExtraBold, regular + italic, plus the No-Ligatures variant `JetBrains Mono NL`). Wired via `@font-face` in `colors_and_type.css`. Falls back to `Fira Code` → `SF Mono` → system monospace if local fonts fail. All numerics use mono.
- **No display / serif face.** Dramatic scale contrast (10px labels against 30px metrics) does the work a display face would.

Font scale: `10 / 12 / 13 / 15 / 18 / 22 / 28 / 30 / 40 / 56`. Stat metrics are always mono and `font-weight: 700`.

### Spacing

Strict **8px grid**. Tokens: `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40px`. No half-grid, no in-between values.

### Backgrounds + imagery
- **Solid backgrounds.** No gradients on UI surfaces — gradients are the #1 ai-slop tell. The single allowed gradient is a 1-stop subtle radial behind hero KPIs in marketing surfaces, and only with `mix-blend-mode: screen`.
- **No photographs in product chrome.** Marketing surfaces may use abstract graphics (network diagrams, code rasters), always **monochrome or duotone in the indigo accent**.
- **No textures, no grain, no hand-drawn illustrations.** Geometry only.
- **No full-bleed photo headers.** Reports + decks open with a wordmark + eyebrow on solid `--ds-bg-page`.

### Animation
- `--ds-ease: 0.18s ease` is the workhorse. Used on hover, focus, and small state changes.
- `--ds-ease-md: 0.25s ease` for panel + drawer transitions.
- **No bounces, no springs, no parallax.** Linear or ease, fast.
- **Motion is for affordance, not delight.** A button that doesn't transition is acceptable; a button that bounces is wrong.

### Hover + press states
- **Buttons:** primary uses `opacity: 0.85` on hover. Secondary darkens via `background: var(--ds-bg-surface)` and brightens border. Ghost gets a surface fill.
- **Rows + nav items:** `background: var(--ds-bg-surface)` on hover. Active nav adds `color: var(--ds-accent)` and a left border accent on expanded sidebars.
- **Press / active:** no shrink animation. The system trusts color change to communicate.
- **Focus:** `border-color: var(--ds-accent)` on inputs. No outline-offset shadows; the accent border is the focus ring.

### Borders
- **1px hairlines, always.** `var(--ds-border)` for default; `var(--ds-border-subtle)` for sub-dividers within a card.
- Severity-tinted borders only on chips, badges, and the `--critical` stat card variant.

### Shadows + elevation
- **Almost none.** This system is flat. Elevation is communicated by *background step* (page → base → surface → elevated), not drop shadow.
- Modals and floating menus may use `0 8px 32px rgba(0,0,0,0.4)` (dark) / `0 8px 32px rgba(11,17,32,0.10)` (light). That is the entire shadow vocabulary.

### Corner radii
`4 / 6 / 10 / 14 / 100` (px). Default for cards is **10px**. Buttons + inputs are **6px**. Badges are **pill (100px)**. No mixing.

### Cards
- Solid `--ds-bg-base` fill, 1px `--ds-border`, 10px radius. No drop shadow.
- Padding: `--ds-s4` (16px) default; `--ds-s5` (20px) for content-rich previews.
- Stat cards step up to `--ds-bg-surface` to read as "raised" within an already-dark page.

### Transparency + blur
- Used **only** for severity-dim chip backgrounds (`rgba(R,G,B,0.10)`) and accent-dim surfaces.
- **No `backdrop-filter: blur`.** It is a marketing tell and degrades on print exports.

### Layout rules
- App chrome is **always fixed-position**: a 52px top header, a 54px (collapsed) or 200px (expanded) left sidebar.
- Main content is `max-width: 860px` for reading-focused views, full-width for tables and dashboards.
- **Three-layer information hierarchy** is structural, not just visual: stat row at top, table in the middle, detail drawer/page on click.

### Color vibe of imagery
Cool, technical, monochromatic. If a hero illustration is needed, render it in `--ds-accent` over `--ds-bg-page` — never warm, never grainy, never photographic.

---

## Iconography

This system uses **Lucide** (lucide.dev) as its primary icon set. Lucide is the open-source successor to Feather Icons — same minimal stroke style, MIT-licensed, ~1500 icons, identical stroke weight (1.5px) at the sizes Obsidian Pro renders (14–18px).

**Why Lucide:**
- Stroke-only icons match the flat, hairline-border aesthetic of the rest of the system.
- The set covers the full vocabulary needed for security tooling: shield, alert-triangle, eye, lock, server, network, file-warning, user-check, etc.
- 1.5px stroke at 16px reads cleanly against `--ds-bg-base` without bolding.

### Substitutions flagged

The original `ds-components.html` reference uses **unicode glyphs** as quick stand-ins for icons (`⊞`, `⚠`, `◈`, `⊟`, `≡`, `⚙`, `⌕`, `↕`, `↑`, `↓`). These render acceptably in dense UIs but are not a real icon system. **The UI kits in this project replace them with Lucide equivalents** and document the mapping in `assets/icons-mapping.md`.

### Usage rules

- **Sizes:** 14px (inline with body text), 16px (default UI), 18px (nav rail), 20px (hero / empty states).
- **Color:** inherits `currentColor`. Default to `--fg2`; switch to `--ds-accent` only on active/hovered nav items, primary CTAs, or severity-tinted chips.
- **Stroke weight:** 1.5px (Lucide default). Never bold, never fill.
- **No emoji.** Ever. Do not substitute 🚨 for an `alert-triangle`.
- **No unicode arrows in tables** for sort/delta indicators — use `lucide-arrow-up`, `lucide-arrow-down`, `lucide-arrows-up-down`.

### Logo / wordmark

The "DS" / "C" tile in the source files is a placeholder. The brand wordmark for **Connection's security practice** has not been provided. Until a real mark is supplied, the design system uses a **typographic wordmark**: the letter pair set in `--ds-font-body` at 11px / 700 weight, on an indigo `--ds-r-md` square (26–28px). See `assets/wordmark-placeholder.svg`.

**Brand mark provided:** `assets/0xD1g5_128.svg` — a 256×256 SVG using monospace `D1g5` over a `0x` eyebrow, on a near-black `#060810` field with a faint cyan grid and pink/cyan corner brackets. Treat this as the placeholder identity for now; if Connection's security practice has a separate house wordmark, drop it in `assets/` and update this section.

> ⚠ Note: the 0xD1g5 mark uses an off-palette pink (`#ff3366`) and cyan (`#00e5cc`) — these are **brand-only** and must not bleed into the UI palette, which stays on indigo + severity. Treat the logo as a brand asset, not a color source.

---

## Files in this project (index)

```
.
├── README.md                       ← this file
├── SKILL.md                        ← Agent-Skills compatible entry point
├── ds-tokens.css                   ← v1.1 token reference (verbatim from source)
├── ds-components.html              ← v1.1 component library reference (verbatim)
├── colors_and_type.css             ← v1.2 — primitives + semantic aliases + light theme
├── assets/
│   ├── wordmark-placeholder.svg
│   ├── icons-mapping.md            ← unicode → Lucide swap table
│   └── lucide.md                   ← how to load Lucide
├── preview/                        ← cards rendered in the Design System tab
│   ├── colors-bg.html
│   ├── colors-semantic.html
│   ├── colors-text.html
│   ├── colors-light-bg.html
│   ├── type-scale.html
│   ├── type-metrics.html
│   ├── type-mono.html
│   ├── spacing-scale.html
│   ├── radii.html
│   ├── elevation.html
│   ├── buttons.html
│   ├── badges.html
│   ├── stat-cards.html
│   ├── form-inputs.html
│   ├── data-table.html
│   └── nav-rail.html
├── ui_kits/
│   └── command/                    ← security console UI kit
│       ├── README.md
│       ├── index.html              ← interactive click-thru prototype
│       ├── components.jsx          ← shared atoms (Button, Badge, Stat…)
│       ├── DashboardScreen.jsx
│       ├── DetectionsScreen.jsx
│       └── DetailDrawer.jsx
└── uploads/                        ← original source files (preserved)
    ├── ds-tokens.css
    └── ds-components.html
```

---

## Caveats

- **No real logo / wordmark provided.** Placeholder typographic mark used; please supply SVG.
- **No marketing site / product page reference provided.** The "product pages" surface mentioned in the brief is currently a single UI kit (`ui_kits/command`) for the dashboard / tooling surface. If you want a marketing-page kit too, say the word.
- **No icon set in source.** Lucide chosen as a sensible default; loaded from CDN. If Connection has a house icon set, drop it in `assets/icons/` and update `icons-mapping.md`.
- **Light theme is new in v1.2.** Tokens are defined in `colors_and_type.css` but the components in `ds-components.html` (v1.1) only address dark. The UI kit in `ui_kits/command` supports both via a toolbar toggle.
