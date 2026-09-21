---
phase: 206-dashboard-ui-coverage-drain
plan: 10
subsystem: dashboard-tests
tags: [uat, vitest, coverage, shell, routing, theme, branding]
requires: ["206-01 (AppShell export, D-A4)"]
provides: ["UAT-7-20 coverage", "UAT-7-22 coverage", "UAT-7-31 coverage", "UAT-7-23 reclassification evidence"]
affects: ["206-12 (red-proof assembly)", "206-13 (UAT-SERIES.md dispositions)", "Phase 207 (browser-only set)"]
tech-stack:
  added: []
  patterns: ["named AppShell import under MemoryRouter", "context-hook vi.mock (ConnectorsPanel pattern)", "static-document assertion tier for index.html facts"]
key-files:
  created:
    - src/dashboard/src/__tests__/shell-spa-routing.test.tsx
    - src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx
    - src/dashboard/src/components/__tests__/dashboard-branding.test.tsx
    - .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-shell.md
  modified: []
decisions:
  - "UAT-7-31's tab-title/favicon half asserted against index.html as a static-document tier, with the D-A1-shaped per-claim reasoning stated in the test file and the fragment"
  - "UAT-7-23 reclassified out of the jsdom-tractable set on reproducible grep evidence; SC#3's denominator moves 28 -> 27, recorded explicitly not silently"
metrics:
  duration: ~25 min
  completed: 2026-09-21
---

# Phase 206 Plan 10: Shell / Cross-Cutting Coverage Summary

Covered the three convertible shell cases (SPA routing, theme persistence, branding) with newly
written, red-proved vitest nodes, and produced reproducible evidence that UAT-7-23's sidebar
collapse is a pure CSS breakpoint and therefore leaves the jsdom-tractable set.

## Tasks Completed

| Task | Name | Commit |
|------|------|--------|
| 1 | UAT-7-20 SPA routing test against the real route table | `c0e55c15` |
| 2 | UAT-7-22 theme persistence + UAT-7-31 branding tests | `c0e55c15` |
| 3 | UAT-7-23 reclassification evidence, red-proof, fragment | `705e9c39` / `472878a8` / `3efee963` |

## What Was Built

**`src/dashboard/src/__tests__/shell-spa-routing.test.tsx` (UAT-7-20)** — mounts the real
`AppShell` (named import from `@/App`, exported by 206-01 under D-A4) inside
`<MemoryRouter initialEntries={["/findings"]}>`, with `useAuth` mocked authenticated, `useVertical`,
`useScanData`, `useScanList`, `useSelectedScan`, `useMergeLatest`, and `useFindingStoryline` mocked.
No `<Route` element appears in the test — the app's own `<Routes>` table is what resolves the path.
Asserts the Findings page's own heading and a fixture row ARE present and the Executive page's
distinguishing heading (`QU.I.R.K. — Scan Results`) is NOT, which is what proves the route was
selected rather than that something merely mounted. `TooltipProvider` wraps the render because
`Sidebar` (rendered by `AppShell`) uses Radix tooltips, exactly as `App.tsx` does in production.

**`src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx` (UAT-7-22)** — renders
the real `ModeToggle` inside `ThemeProvider` with the app's real `storageKey` (`quirk-ui-theme`,
`App.tsx:130`), clicks Light, and asserts BOTH halves: `documentElement` gains `light` / loses
`dark`, AND `localStorage.getItem("quirk-ui-theme") === "light"`. Reload equivalence is asserted
through the app's own rehydration function `getStoredTheme()`; the return trip to dark (UAT step 8)
is asserted too. Confirmed first that the pre-existing `theme-provider.test.tsx` covers only the
`getStoredTheme()` / `VALID_THEMES` utility surface — it renders no provider and clicks nothing — so
this is genuinely new coverage.

**`src/dashboard/src/components/__tests__/dashboard-branding.test.tsx` (UAT-7-31)** — renders the
real `Sidebar` and asserts the `QU.I.R.K.` wordmark element plus its `font-black` / `font-mono` /
`text-accent` classes ("bold monospace electric-blue", asserted as the design token rather than a
hex literal, since hardcoded hex is what UAT-7-21 forbids), and the collapsed-state `Q` monogram.
The tab-title and favicon halves are asserted against `src/dashboard/index.html`.

**`red-proof/206-RED-PROOF-shell.md`** — 3 body rows (no row for 7-23, which converted nothing), a
`## Citations` section with the three citation strings and their named partial-coverage carve-outs,
and the `## UAT-7-23 reclassification evidence` section.

## Red-Proof Evidence

One `TEMPORARY(206-10)` commit (`705e9c39`) applied all three mutations, immediately reverted by
`472878a8`. All three nodes went red; failure text captured verbatim into the fragment.

| Case | Mutation | Observed failure |
|------|----------|------------------|
| UAT-7-20 | `App.tsx`'s `/findings` route re-pointed at `<ExecutivePage />` | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Findings"` |
| UAT-7-22 | `localStorage.setItem(storageKey, t)` removed from `ThemeProvider.setTheme` | `AssertionError: expected null to be 'light' // Object.is equality` |
| UAT-7-31 | Sidebar wordmark text node blanked | `TestingLibraryElementError: Unable to find an element with the text: QU.I.R.K.. …` |

Post-revert: `git diff 68c048d0 -- src/dashboard/src/App.tsx src/dashboard/src/components/sidebar.tsx
src/dashboard/src/components/theme-provider.tsx` returns **no output**, and
`grep -c "^export function AppShell()" src/dashboard/src/App.tsx` returns **1** (T-206-10-01
mitigated).

## UAT-7-23 Reclassification

`grep -n "matchMedia\|useMediaQuery" src/dashboard/src/components/sidebar.tsx` → no output (exit 1).
`grep -n "lg:w-\|w-12" …` → `78:        "w-12 lg:w-60",` (exit 0). The collapse is a pure Tailwind
breakpoint with no JS listener; jsdom evaluates no media queries, so the DOM is identical above and
below 1024px. **UAT-7-23 leaves the jsdom-tractable set**, joins the browser-only group routed to
Phase 207, and moves SC#3's denominator from 28 to 27. Recorded with reproducible commands and
literal output in the fragment (T-206-10-02 mitigated), not enacted silently. No test was written
for it.

## Verification

- Three cited nodes: **3 passed | 0 failed** (`vitest run` on the three files).
- Whole dashboard suite after the change: **70 test files passed, 445 passed | 2 skipped (447)**.
- `npm run lint` — 0 errors (1 pre-existing warning in `ConnectorsPanel.test.tsx`, another plan's
  file, untouched here). `npm run build` — exit 0, no static-output diff.
- `git diff --name-only 68c048d0..HEAD -- docs/` — empty. No `docs/UAT-SERIES.md`,
  `uat-disposition-ledger.jsonl`, or `uat-coverage-gaps.md` edit; those are fenced into 206-13.

## Deviations from Plan

**1. [Rule 3 - Blocking] `fileURLToPath(import.meta.url)` is not usable in this vitest setup**
- **Found during:** Task 2
- **Issue:** `TypeError: The URL must be of scheme file` — vitest's transform does not give
  `import.meta.url` a `file:` scheme here.
- **Fix:** switched to `path.resolve(__dirname, "../../../index.html")`, the idiom already used by
  `pages/__tests__/cbom-cytoscape-catch.test.tsx`.
- **Files modified:** `src/dashboard/src/components/__tests__/dashboard-branding.test.tsx`
- **Commit:** `c0e55c15`

**2. [Rule 1 - Accuracy] Plan cited `App.tsx:100` for the `storageKey`; the real line is 130**
- Corrected in both the test file comment and the fragment. `App.tsx` has grown since the plan was
  written (the `/print` chrome-free branch now sits above the route table).

No product behaviour was changed. No product defect was discovered by these three cases, so no todo
was filed.

## Self-Check: PASSED

- `src/dashboard/src/__tests__/shell-spa-routing.test.tsx` — FOUND
- `src/dashboard/src/components/__tests__/theme-toggle-persistence.test.tsx` — FOUND
- `src/dashboard/src/components/__tests__/dashboard-branding.test.tsx` — FOUND
- `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-shell.md` — FOUND
- Commits `c0e55c15`, `705e9c39`, `472878a8`, `3efee963` — all FOUND in `git log`
