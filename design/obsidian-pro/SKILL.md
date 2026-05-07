---
name: obsidian-pro-design
description: Use this skill to generate well-branded interfaces and assets for Obsidian Pro — the design system for Connection's security practice — either for production code or throwaway prototypes, dashboards, reports, decks, and product pages. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping security tooling and governance deliverables.
user-invocable: true
---

# Obsidian Pro Design Skill

Read the `README.md` file within this skill, and explore the other available files. Key entry points:

- `README.md` — brand context, voice, visual foundations, iconography
- `colors_and_type.css` — drop-in token + semantic-class CSS (dark + light)
- `ds-tokens.css` — original v1.1 single-palette token file
- `ds-components.html` — full component library reference
- `ui_kits/command/` — interactive UI kit (dashboard, detections, detail drawer)
- `preview/` — small swatch + specimen cards used to populate the Design System tab
- `assets/` — wordmark, icon mapping, Lucide loading instructions

## How to use this skill

If creating **visual artifacts** (slides, mocks, throwaway prototypes, dashboards, reports):
1. Copy `colors_and_type.css` (or `ds-tokens.css` for v1.1 dark-only) into your output folder.
2. Copy any logos / icons you need from `assets/`.
3. Lift component patterns directly from `ui_kits/command/` — buttons, badges, stat cards, tables, form inputs, nav patterns are all there.
4. Output static HTML files for the user to view.

If working on **production code**:
- Reference tokens by their `--ds-*` custom properties; do not inline hex values.
- Follow the visual + content rules in `README.md` strictly. Color is for severity. Typography uses dramatic scale contrast. No emoji, no gradients on UI chrome.

If the user invokes this skill **without other guidance**, ask them what they want to build or design (security dashboard? incident report PDF? presales deck? product page?), ask 3–5 clarifying questions about audience, density, and tone, and act as an expert designer who outputs HTML artifacts or production code depending on the need.

## Hard rules — do not break

1. **Color is for severity, never decoration.** Critical/high/ok/medium each have one job.
2. **No emoji, ever.** Use Lucide icons or semantic badges with status dots.
3. **No gradients on UI surfaces.** Solid fills only.
4. **Numerics are always monospace.** JetBrains Mono with `tnum` enabled.
5. **8px grid, no exceptions.** Padding, gap, and margin are multiples of 4/8.
6. **Eyebrow labels are 10px ALL CAPS with 0.08em tracking.** That is the rhythm of the whole system.
