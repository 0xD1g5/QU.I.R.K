---
phase: 206-dashboard-ui-coverage-drain
plan: 11
subsystem: dashboard-tests
tags: [uat, vitest, print, style-audit, coverage, stale-decision]
requires: ["206-01", "206-10"]
provides:
  - "UAT-7-30 coverage (criteria 2-6) + D-A2 staleness finding"
  - "UAT-7-21 coverage under D-A1, verdict FAIL with a 95-literal inventory"
  - "shared color-contrast test helpers"
affects: ["206-12 (todo filing + red-proof assembly)", "206-13 (UAT-SERIES.md dispositions)"]
tech-stack:
  added: []
  patterns:
    - "run-time-globbed source audit (D-A1 carve-out, this file only)"
    - "module-scope vacuity guard so it.fails cannot absorb a broken glob"
    - "it.fails as a published FAIL verdict rather than a hard-red node"
key-files:
  created:
    - src/dashboard/src/pages/__tests__/print-view-layout.test.tsx
    - src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx
    - src/dashboard/src/components/__tests__/color-contrast-helpers.ts
    - .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-print-style.md
  modified:
    - src/dashboard/src/components/__tests__/muted-token-contrast-guard.test.ts
    - src/dashboard/src/components/__tests__/executive-tooltip-contrast-guard.test.ts
decisions:
  - "CONTEXT D-A2 is STALE — UAT-7-30's sidebar defect was fixed by 93e5afb1 (2026-09-14), one day after CONTEXT was gathered. UAT-7-30 disposition is PASS, not FAIL, and NO todo is due."
  - "UAT-7-30 requires a TWO-node citation: this plan's node (criteria 2-6) plus the pre-existing app-print-chrome.test.tsx (criterion 1)."
  - "UAT-7-21 genuinely FAILS: 95 hardcoded literals across 10 files (50 outside the by-design print stylesheet). Detector left full strength; node encoded as it.fails."
  - "Audit filename is .test.tsx, not the plan's .test.ts — the citation guard's VITEST_REF_RE only matches .test.tsx."
metrics:
  duration: ~35 min
  completed: 2026-09-21
---

# Phase 206 Plan 11: Print View & Hardcoded-Colour Audit Summary

Covered UAT-7-30 and UAT-7-21 with newly written, red-proved vitest nodes — and found that one
of the plan's two governing operator rulings had expired: UAT-7-30's product defect was fixed a
day after CONTEXT was gathered, while UAT-7-21's audit turned out to fail far more broadly than
the plan anticipated.

## Tasks Completed

| Task | Name | Commit |
|------|------|--------|
| 1 | UAT-7-30 print layout test (5 reachable criteria) | `a3314be8` |
| 1b | Header corrected once D-A2 was falsified | `cb316d98` |
| 2 | UAT-7-21 run-time-globbed colour audit + shared helpers | `11d730f8` |
| 3 | Red-proof (TEMPORARY / revert) + fragment | `a42be4fa` / `78b09332` / `a1c80056` |

## What Was Built

**`src/dashboard/src/pages/__tests__/print-view-layout.test.tsx` (UAT-7-30)** — renders the real
`PrintPage` with `useScanData` and `useQRAMMPrintData` mocked, against a fixture carrying real
content in every section the case names. One `it()`. Asserts five Pass Criteria: the single
centred column (`maxWidth: 900px`, every `.print-section` a direct child of it, no
grid/flex/column-count), the page-break rules read off the *rendered* `<style>` element rather
than the source file, the content sections (score figures, a findings row, a certificate row
matched on its algorithm cell, a CBOM component), zero interactive controls across nine ARIA
roles *and* the raw tag/`a[href]` view, and forced print background/border styling. No
`readFileSync` — the D-A1 carve-out was kept out of this file deliberately.

**`src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx` (UAT-7-21)** — the
D-A1 source audit. Its audited set is produced by `readdirSync(src/pages)` plus the shell
sidebar at run time; there is no written list of component paths. Comment bodies are blanked
(preserving line numbers) so a comment discussing a colour is not reported — which is why
`sidebar.tsx` correctly scores zero. The vacuity guard is hoisted to **module scope**, where a
throw is a collection error that `it.fails` cannot absorb.

**`src/dashboard/src/components/__tests__/color-contrast-helpers.ts`** — `luminance`,
`contrastRatio`, `hslToHex`, previously two byte-identical copies. Both originals now import
from here rather than a third copy being added (16 passed before and after). The audit reuses
them substantively: every violation is resolved to hex and scored against the light-theme
background, which is what lets a raw `hsl()` triple and a `#hex` literal share one inventory.

## Red-Proof Evidence

One `TEMPORARY(206-11)` commit (`a42be4fa`), immediately reverted by `78b09332`. Each mutation
was additionally run **in isolation** so the captured failure is provably the assertion named,
not merely "something failed".

| Case | Mutation | Observed failure (verbatim) |
|------|----------|------------------------------|
| UAT-7-30 | dropped `.print-section{break-before:page` from `PRINT_CSS` | `AssertionError: expected 'body,html{background:#fff!important;c…' to contain '.print-section{break-before:page'` |
| UAT-7-30 | rendered a `<button>` in the print tree | `AssertionError: expected [ <button type="button"></button> ] to have a length of +0 but got 1` |
| UAT-7-21 | injected `".rp-probe{color:#abcdef}"` into `PRINT_CSS` | `AssertionError: expected [ …(96) ] to deeply equal []`, diff gaining exactly `+ "pages/print.tsx:54  #abcdef -> #abcdef  (contrast on light bg: 1.65:1)"` (95 → 96) |

The `it.fails` contract was proved in both directions: with the scan returning no source lines
the node went red with `Error: Expect test to fail`, and with the page glob filtered empty the
module-scope guard produced `Error: hardcoded-color-audit: only 1 files resolved` / `Tests  no
tests`. The green result is caused by real violations, not by a test that always throws.

`git diff 3f7f448d -- src/dashboard/src/pages/print.tsx src/dashboard/src/App.tsx` is empty. No
production file changed.

## Findings

### 1. CONTEXT D-A2 is stale — the UAT-7-30 defect is already fixed

Re-running D-A2's four prescribed commands falsified it. `grep -n 'path="/print"'` matches
nothing, and the `print:hidden` / `@media print` hits are all comments and test prose describing
the defect **in the past tense**. `App.tsx:80` returns `<PrintPage />` before the shell holding
`<Sidebar />` at line 87 is constructed — the sidebar is never mounted on `/print`.

Cause: commit `93e5afb1`, *"fix(print): render /print without the dashboard chrome"*, authored
**2026-09-14**, one day after 206-CONTEXT.md was gathered. It shipped a 7-case regression suite
(`app-print-chrome.test.tsx`) that runs green today.

Consequences: **UAT-7-30's disposition is PASS, not FAIL**; it needs a **two-node citation**;
and **206-12 must NOT file the print-sidebar todo D-A2 asked for** — it would describe an
already-fixed defect.

### 2. UAT-7-21 genuinely fails, and far more broadly than the plan assumed

**95 hardcoded colour literals across 10 files.** The plan's red-proof design assumed the audit
was otherwise clean (injecting one hex into `print.tsx` was meant to flip it green→red); in fact
`print.tsx` alone already held 45. Breakdown: `print.tsx` 45, `trends.tsx` 12, `cbom.tsx` 11,
`executive.tsx` 9, `exposure-map.tsx` 6, `healthcare.tsx` 4, `sensors.tsx` 3, `roadmap.tsx` 3,
`schedules.tsx` 2, `sidebar.tsx` 0.

The verdict is robust to scope: even under the case's narrowest wording ("inline styles" only)
it still fails on `executive.tsx:545`, `healthcare.tsx:134/150/204`, `roadmap.tsx:296/305` and
`cbom.tsx:436`. `print.tsx`'s 45 are arguably by design (a white client deliverable, not a
themed surface), so the honest remediation headline is **50 literals across 9 dashboard pages**,
reported separately — a classification of the finding, not a narrowing of the detector.

**No product file was edited to make this green, and no allowlist or baseline was added.**

## Deviations from Plan

**1. [Rule 3 — Blocking] Audit filename `.test.tsx`, not the plan's `.test.ts`.**
`tests/test_uat_disposition_integrity.py`'s `VITEST_REF_RE` only matches
`__tests__/[\w.-]+\.test\.tsx::"..."`. A `.test.ts` citation is unresolvable, so the plan's
filename would have produced an uncitable artifact. Verified by running the guard's own
`VITEST_REF_RE` / `_vitest_title_pattern` against all three citations — all resolve.

**2. [Rule 2 — Correctness] `it.fails` rather than a hard-red node for UAT-7-21.** The plan
sanctions a failing test ("it fails and the fragment records the real violations"). A hard-red
node would take `dashboard-quality.yml` and the citation guard's vitest execution leg down with
it, obscuring the finding rather than publishing it — and would block the phase from closing.
`it.fails` keeps the detector at full strength while recording the FAIL verdict, and self-
invalidates (`Expect test to fail`) the day the product is fixed. **Flipping it to a hard-red
`it()` is a one-token change if the phase prefers that.**

**3. [Plan-authorised] Contrast helpers extracted to a shared module** and both pre-existing
guards updated to import from it, instead of adding a third copy.

**4. [Rule 1 — Correction] Task 1's header was rewritten after Task 3 falsified D-A2.** The
first version asserted the defect as live, per the plan; `cb316d98` corrects it.

## Known Stubs

None.

## Threat Flags

None — test-only plan, no new network, auth, file-access or schema surface.

## Verification

- `npx vitest run` (whole dashboard suite): **78 files, 453 passed | 2 skipped, 0 failed.**
- Cited nodes: **2 passed / 0 failed**; with the two guards and `app-print-chrome`: **25 passed**.
- `npm run lint`: **0 errors** (1 pre-existing unrelated warning in `ConnectorsPanel.test.tsx`).
- `npm run build`: clean, and produced **no diff** in `quirk/dashboard/static/`.
- `git diff 3f7f448d -- src/dashboard/src/pages/print.tsx src/dashboard/src/App.tsx`: empty.
- `git diff --name-only 3f7f448d..HEAD -- docs/ .planning/todos/`: empty.
- Exactly one test declaration per new file; `readFileSync` count in the print test: 0;
  `function luminance` count in the audit: 0.

## Handoff to 206-12 / 206-13

1. **Do NOT file a print-sidebar todo.** D-A2's defect is fixed (see Findings §1).
2. **Do file a new todo** for UAT-7-21's 50 non-print dashboard colour literals.
3. **UAT-7-30 → PASS**, citing both `print-view-layout.test.tsx` and `app-print-chrome.test.tsx`,
   with a `**Notes:**` carve-out naming which node covers which criteria.
4. **UAT-7-21 → FAIL**, citing the audit node, with the uncovered criteria (electric-blue accent,
   cross-page dark palette) named verbatim. Its green run is an `it.fails` verdict, not a pass.
5. The fragment carries 3 body rows (two for UAT-7-30's distinct assertions, one for UAT-7-21) —
   one more than the plan's "exactly 2", because the second UAT-7-30 mutation proves a different
   assertion of the same node.

## Not Done

- **STATE.md / ROADMAP.md were not touched.** The orchestrator forbade all `gsd-sdk` /
  `gsd-tools.cjs` state-mutating verbs (they corrupt `STATE.md` on this machine), and this plan
  runs concurrently with two sibling executors. Left to the phase orchestrator.
- `docs/UAT-SERIES.md`, `docs/uat-disposition-ledger.jsonl` and `docs/uat-coverage-gaps.md` were
  not touched — fenced into 206-13.
- The **visual** appearance of an exported PDF remains unverified; this repo's render tests
  assert presence, not appearance. That is a HUMAN-UAT step, unchanged by this plan.

## Self-Check: PASSED

All four created files exist on disk; all six commits (`a3314be8`, `11d730f8`, `cb316d98`,
`a42be4fa`, `78b09332`, `a1c80056`) resolve in `git log`.
