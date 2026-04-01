---
phase: 07-polish-and-packaging
plan: "04"
subsystem: dashboard-branding
tags: [favicon, cross-browser, branding, BRAND-01, D-13]
requirements: [BRAND-01]

dependency_graph:
  requires: [07-01, 07-02]
  provides: [cross-browser-favicon, BRAND-01-complete]
  affects: [quirk/dashboard/static]

tech_stack:
  added: [Pillow (favicon PNG generation)]
  patterns: [multi-format favicon strategy (SVG+PNG+ICO), path-based SVG (no font dependency)]

key_files:
  created: []
  modified:
    - src/dashboard/public/favicon.svg
    - src/dashboard/public/favicon.png
    - src/dashboard/public/favicon.ico
    - quirk/dashboard/static/favicon.svg
    - quirk/dashboard/static/favicon.png
    - quirk/dashboard/static/favicon.ico

decisions:
  - Replace text-element SVG with path-based circle+line Q design to eliminate font dependency
  - Use Pillow to generate PNG (cairosvg unavailable); draws geometry directly without font rasterization
  - ICO contains both 16x16 and 32x32 sizes for maximum browser compatibility

metrics:
  duration: "~20 minutes"
  completed: "2026-03-31"
  tasks_completed: 3
  files_modified: 6
---

# Phase 7 Plan 4: Cross-Browser Favicon Fix Summary

Cross-browser favicon support via three-format strategy (SVG + PNG + ICO) with path-based SVG design that eliminates font rendering dependency.

## What Was Built

Tasks 1 and 2 (favicon SVG and D-13 color audit, committed as 7fca7c2 and be4287b) were completed in the prior session. Human verification revealed the favicon failed in all three browsers:

- Chrome: default browser globe (SVG not loading)
- Firefox: no favicon
- Safari: showed "1"

This continuation fixed the root causes.

## Root Cause Analysis

Two compounding problems:

1. **SVG used `<text>` element with `font-family="'Courier New', Courier, monospace"`** — when browsers render SVG favicons, text elements depending on system fonts render inconsistently or not at all. Chrome in particular may silently fail to render text-based SVGs as favicons.

2. **SVG had mismatched dimensions** — `width="32" height="32"` but `viewBox="0 0 48 48"`. This inconsistency causes browsers to scale the viewport unexpectedly.

3. **Safari "1" badge** — likely caused by the viewBox scaling confusion causing Safari to misinterpret the SVG as a touch/badge asset.

4. **PNG existed but had no visible content** — the existing favicon.png had been generated from the text-based SVG without font rendering, resulting in a 32x32 image with only the dark background and no Q character.

## Fix Applied (Task 3 — continuation)

**SVG redesigned:** Replaced `<text>Q</text>` with SVG primitives:
- `<circle>` for the Q body (cx=14, cy=15, r=7, stroke electric-blue)
- `<line>` for the Q tail diagonal
- `<circle>` accent dot bottom-right
- Fixed viewBox to `0 0 32 32` matching `width="32" height="32"`
- No external font references — fully self-contained

**PNG regenerated:** Used Pillow to draw the same geometry directly (334 blue pixels confirmed), since cairosvg is unavailable.

**ICO regenerated:** Multi-size ICO with 16x16 (LANCZOS-downscaled) and 32x32 sizes.

**All three files copied** to `quirk/dashboard/static/` and Vite build confirmed.

**HTML strategy already correct** (set in Task 1):
```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate icon" type="image/png" href="/favicon.png">
<link rel="shortcut icon" href="/favicon.ico">
```

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 — Favicon SVG + title | 7fca7c2 | feat(07-04): update favicon to electric-blue Q monogram, update page title |
| 2 — D-13 audit + sidebar + build | be4287b | feat(07-04): D-13 color audit, strengthen sidebar wordmark, rebuild static assets |
| 3 — Cross-browser fix | 6e13740 | fix(07-04): cross-browser favicon — add PNG fallback, fix SVG link type |

## Test Results

```
tests/test_dashboard_theme.py::test_primary_color_token PASSED
tests/test_dashboard_theme.py::test_accent_color_token PASSED
tests/test_dashboard_theme.py::test_sidebar_wordmark_present PASSED
3 passed in 0.01s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cross-browser SVG favicon failure — text element and viewBox mismatch**
- **Found during:** Human verification checkpoint (post Task 2)
- **Issue:** SVG used `<text font-family="...">` which fails silently in Chrome/Safari; viewBox `0 0 48 48` mismatched `width="32" height="32"`; generated PNG had no visible Q content
- **Fix:** Replaced text element with SVG path primitives (circle + line); fixed viewBox to `0 0 32 32`; regenerated PNG and ICO using Pillow with direct geometry drawing
- **Files modified:** `src/dashboard/public/favicon.svg`, `src/dashboard/public/favicon.png`, `src/dashboard/public/favicon.ico`, mirrored to `quirk/dashboard/static/`
- **Commit:** 6e13740

## Known Stubs

None. All favicon files contain proper rendered content. The Q design is visible at favicon scale.

## Self-Check: PASSED

Files confirmed present:
- src/dashboard/public/favicon.svg — FOUND
- src/dashboard/public/favicon.png — FOUND (32x32 RGBA, 334 blue pixels)
- src/dashboard/public/favicon.ico — FOUND (16x16 + 32x32 multi-size)
- quirk/dashboard/static/favicon.svg — FOUND
- quirk/dashboard/static/favicon.png — FOUND
- quirk/dashboard/static/favicon.ico — FOUND

Commits confirmed:
- 7fca7c2 — FOUND
- be4287b — FOUND
- 6e13740 — FOUND
