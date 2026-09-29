---
phase: 216-a11y-harness-repair
plan: 04
subsystem: a11y-test-harness
tags: [a11y, puppeteer, theme, vitest, ci, HARNESS-01]
requirements: [HARNESS-01]
dependency-graph:
  requires: ["216-01", "216-03"]
  provides:
    - "run-a11y.mjs seeds the app's real theme-provider localStorage path via page.evaluateOnNewDocument before navigation (D-01)"
    - "THEME_STORAGE_KEY exported from theme-context.ts, consumed as theme-provider.tsx's storageKey default"
    - "D-03 refusal: light+empty/loading exits 1 loudly, no preview/browser started"
    - "axe incomplete counts logged per route/interaction and carried into the summary table (RESEARCH Pitfall 3)"
    - "a11y:check:dark/light + a11y:baseline:dark/light npm scripts; a11y:check/a11y:baseline are aliases to the :dark forms"
    - "both dashboard-quality.yml jobs (a11y gate, a11y-regenerate-baselines) enumerate both themes explicitly (D-16)"
    - "theme-sweep-contract.test.ts: mechanical, THEMES-derived guard across harness/scripts/CI/storage-key"
  affects:
    - "216-05 (theme-complete ACCEPTED-VIOLATIONS ledger)"
    - "216-08 (must land Linux-generated light baselines before the a11y gate job goes green)"
tech-stack:
  added: []
  patterns:
    - "page.evaluateOnNewDocument seed-before-navigate, registered once per page (RESEARCH Pattern 2)"
    - "loud refusal over silent skip for an excluded theme/variant combination (D-03), matching the harness's existing missing-baseline idiom"
    - "run-time-source-scan contract test deriving its occurrence set from THEMES rather than a hardcoded array literal"
key-files:
  created:
    - src/dashboard/tests/a11y/theme-sweep-contract.test.ts
  modified:
    - src/dashboard/src/components/theme-context.ts
    - src/dashboard/src/components/theme-provider.tsx
    - src/dashboard/tests/a11y/run-a11y.mjs
    - src/dashboard/package.json
    - .github/workflows/dashboard-quality.yml
    - .planning/STATE.md
    - quirk/dashboard/static/index.html
    - quirk/dashboard/static/assets/index-BQ5tku15.js (rebuild artifact; replaces index-BJw2kl8c.js)
decisions:
  - "216-CONTEXT.md D-01/D-02/D-03/D-16 implemented as locked; no deviations from the decision text itself"
  - "Made the a11y gate job's and a11y-regenerate-baselines job's dark-theme steps use the explicit a11y:check:dark/a11y:baseline:dark script names instead of the pre-existing unsuffixed alias -- not specified verbatim by the plan's action text, but required for theme-sweep-contract.test.ts's per-theme workflow assertion to be symmetric across THEMES rather than special-casing dark, and consistent with D-16's actual ask that no theme be left implicit in CI"
metrics:
  duration: "~50m"
  completed: "2026-09-29"
---

# Phase 216 Plan 04: Theme-seeded a11y sweep + CI wiring + drift contract Summary

**Gave `run-a11y.mjs` a theme dimension it has never had: seeds the app's real localStorage
theme key before navigation (not a forced class or a silent-no-op media emulation), refuses
the D-03-excluded theme/variant combinations loudly, threads the theme through every
operator-facing string, logs axe `incomplete` counts, adds explicit per-theme npm scripts and
CI steps, and locks all of it together with a mechanical, THEMES-derived contract test.**

## What Was Built

**Task 1 — `src/dashboard/src/components/theme-context.ts` / `theme-provider.tsx` /
`tests/a11y/run-a11y.mjs`:**
- `theme-context.ts` now exports `THEME_STORAGE_KEY = "quirk-ui-theme"`; `theme-provider.tsx`
  imports it and uses it as the `storageKey` default parameter (previously a bare string
  literal) — the single-source choke point D-01 calls for.
- `run-a11y.mjs` carries a deliberately duplicated literal copy (`.mjs` cannot import from the
  app's `.ts` module), seeded via `page.evaluateOnNewDocument((key, value) => {
  localStorage.setItem(key, value) }, THEME_STORAGE_KEY, THEME)` immediately after
  `browser.newPage()` and before `page.goto` — registered once per page, since the loop
  already opens a fresh page per route.
- D-03 refusal: immediately after `THEME` is resolved, `THEME !== 'dark' && VARIANT !==
  'default'` prints a `REFUSED ... D-03` message and calls `process.exit(1)` before the
  preview server or browser are even started.
- Theme threaded through the `Scanning <slug>` line, a new per-route/interaction
  `<slug> [<theme>]: violations=<n> incomplete=<m>` log line, and both missing-baseline
  remediation commands (`npm run a11y:baseline:light` when `THEME === 'light'`).
- axe's `results.incomplete.length` is logged and carried into every `summary.push` object
  (including the previously-untouched `NAV_ERR`/content-marker-FAIL/missing-baseline-FAIL
  paths, all defaulted to `incomplete: 0`) and the final printed summary table.
- `npm run build` was re-run because `theme-provider.tsx` changed; the regenerated dashboard
  bundle (`index-BQ5tku15.js` replacing `index-BJw2kl8c.js`) is committed alongside.

**Task 2 — `src/dashboard/package.json` / `.github/workflows/dashboard-quality.yml`:**
- Added `a11y:check:dark`, `a11y:check:light`, `a11y:baseline:dark`, `a11y:baseline:light`.
  `a11y:check`/`a11y:baseline` are now aliases (`npm run a11y:check:dark` /
  `npm run a11y:baseline:dark`) so `docs/operators-guide.md`, `docs/UAT-SERIES.md`, and the
  harness's own remediation messages, which all name the unsuffixed commands, keep working.
  `:empty`/`:loading` untouched (dark-only per D-03).
- `a11y` gate job: renamed the happy-fixture step to `Run axe + console sweep (happy fixture,
  dark theme)` and pointed its `run:` at the now-explicit `npm run a11y:check:dark`; added a
  sibling step `Run axe + console sweep (happy fixture, light theme)` running
  `npm run a11y:check:light`, commented `216 D-16`.
- `a11y-regenerate-baselines` job: same rename/explicit-command pattern for
  `a11y:baseline:dark`, plus a sibling `Regenerate baselines (default fixture, light theme)`
  step running `npm run a11y:baseline:light`, positioned before `Upload regenerated
  baselines` (confirmed via a PyYAML parse of the job's step-name list).
- No fourth `setup-chrome`/job added — `pinned-deps.test.ts`'s exactly-3
  `chrome-version:` assertion stays green (`grep -c "chrome-version:"` == 3, unchanged).
- `.planning/STATE.md`'s `**Current focus:**` line got one hand-appended sentence: *"a11y
  light-theme CI step is intentionally RED on this branch until plan 216-08 lands the
  Linux-generated light baselines — not a regression."* Edited under the mandated
  pre-image + full-diff protocol (see Deviations/Verification below) — `.planning/STATE.md`
  is gitignored-but-tracked (grandfathered), so it was staged with `git add -f`.

**Task 3 — `src/dashboard/tests/a11y/theme-sweep-contract.test.ts` (new, 8 nodes):**
- Derives its theme set from `THEMES` (imported from `./baseline-diff.mjs`) at run time —
  no hardcoded `'light'`/`'dark'` array literal anywhere in the file.
- Vacuity guard: `THEMES.length >= 2`.
- `it.each(THEMES)`: every theme has both `a11y:check:<theme>`/`a11y:baseline:<theme>` npm
  scripts containing `A11Y_THEME=<theme>`.
- `it.each(THEMES)`: `dashboard-quality.yml`'s raw text contains
  `npm run a11y:check:<theme>` and `npm run a11y:baseline:<theme>` for every theme (D-16's
  actual requirement, mechanically enforced).
- `THEME_STORAGE_KEY` equality between `run-a11y.mjs`'s literal and `theme-context.ts`'s
  exported constant, both extracted from source text via regex (not hand-copied).
- Mechanism guard: source contains `page.evaluateOnNewDocument(` and does NOT contain an
  actual `classList.add(THEME...)` call or a real `.setEmulatedMedia(...)` invocation —
  checked as regex-matched calls, not bare substrings, because the harness's own header
  comment names `Emulation.setEmulatedMedia` in prose as the rejected alternative (a naive
  `not.toContain("setEmulatedMedia")` would have failed against that documentation, not a
  real regression — caught live while writing this test, see Deviations below).
- D-03 refusal guard: `D-03`, `process.exit(1)`, and `THEME !== 'dark'` all present, and all
  three found to live inside the same ~400-character window starting at the `REFUSED` message
  (not merely present anywhere in the file).

## Falsification Evidence (Task 3 acceptance criterion, demonstrated not asserted)

Temporarily deleted the light-theme step block from `.github/workflows/dashboard-quality.yml`
(the `a11y` gate job's `Run axe + console sweep (happy fixture, light theme)` step) and reran
the contract test:

```
 ❯ tests/a11y/theme-sweep-contract.test.ts:62:9
     60|         WORKFLOW_TEXT,
     61|         `dashboard-quality.yml has no "npm run a11y:check:${theme}" st…
     62|       ).toContain(`npm run a11y:check:${theme}`)
       |         ^
     63|       expect(
     64|         WORKFLOW_TEXT,

 FAIL  tests/a11y/theme-sweep-contract.test.ts > theme-sweep contract — harness, scripts and CI cannot drift apart (216 D-16) > dashboard-quality.yml names both npm run a11y:check:light and npm run a11y:baseline:%s
AssertionError: dashboard-quality.yml has no "npm run a11y:check:light" step: expected 'name: Dashboard Quality\n\non:\n  pul…' to contain 'npm run a11y:check:light'

 Test Files  1 failed (1)
      Tests  1 failed | 7 passed (8)
```

The failure names `light` explicitly, as required. Restored the workflow file from a
pre-deletion copy, confirmed `diff` reported no differences (byte-identical), and reran:

```
 ✓ tests/a11y/theme-sweep-contract.test.ts (8 tests) 2ms

 Test Files  1 passed (1)
      Tests  8 passed (8)
```

`git diff --stat .github/workflows/dashboard-quality.yml` after the round-trip showed only
the two legitimate Task 3 changes (the `a11y:check`→`a11y:check:dark` and
`a11y:baseline`→`a11y:baseline:dark` explicit-command edits) — the falsification left no
residue.

## Verbatim `a11y:check:light` Missing-Baseline Output (falsifier 1 evidence)

`npm run a11y:check:light` (exit code 1), confirming the loud-failure requirement — no
silent fallback to the dark baseline, every route names the exact remediation command:

```
> dashboard@0.0.0 a11y:check:light
> VITE_A11Y_FIXTURE=1 A11Y_THEME=light node tests/a11y/run-a11y.mjs

[a11y] Fixture variant: default
[a11y] Theme: light
[a11y] Starting vite preview with VITE_A11Y_FIXTURE=1...
[a11y] Preview ready at http://localhost:4173
[a11y] Scanning root [light] (http://localhost:4173/)...
[a11y] root [light]: violations=1 incomplete=1
[a11y] FAIL [root]: missing baseline file .../baseline-root-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning findings [light] (http://localhost:4173/findings)...
[a11y] FAIL [findings]: missing baseline file .../baseline-findings-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning identity [light] (http://localhost:4173/identity)...
[a11y] FAIL [identity]: missing baseline file .../baseline-identity-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning motion [light] (http://localhost:4173/motion)...
[a11y] FAIL [motion]: missing baseline file .../baseline-motion-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning data-at-rest [light] (http://localhost:4173/data-at-rest)...
[a11y] FAIL [data-at-rest]: missing baseline file .../baseline-data-at-rest-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning certificates [light] (http://localhost:4173/certificates)...
[a11y] FAIL [certificates]: missing baseline file .../baseline-certificates-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning cbom [light] (http://localhost:4173/cbom)...
[a11y] FAIL [cbom]: missing baseline file .../baseline-cbom-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning roadmap [light] (http://localhost:4173/roadmap)...
[a11y] FAIL [roadmap]: missing baseline file .../baseline-roadmap-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning trends [light] (http://localhost:4173/trends)...
[a11y] FAIL [trends]: missing baseline file .../baseline-trends-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning qramm [light] (http://localhost:4173/qramm)...
[a11y] FAIL [qramm]: missing baseline file .../baseline-qramm-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning qramm-assessment [light] (http://localhost:4173/qramm/assessment)...
[a11y] FAIL [qramm-assessment]: missing baseline file .../baseline-qramm-assessment-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning hardware [light] (http://localhost:4173/hardware)...
[a11y] FAIL [hardware]: missing baseline file .../baseline-hardware-default-light.json — run `npm run a11y:baseline:light` to generate it
[a11y] Scanning compare [light] (http://localhost:4173/compare?a=1&b=2)...
[a11y] FAIL [compare]: missing baseline file .../baseline-compare-default-light.json — run `npm run a11y:baseline:light` to generate it

[a11y] Summary:
  FAIL    root — violations: 0, console: 0, incomplete: 0
  FAIL    findings — violations: 0, console: 0, incomplete: 0
  FAIL    identity — violations: 0, console: 0, incomplete: 0
  FAIL    motion — violations: 0, console: 0, incomplete: 0
  FAIL    data-at-rest — violations: 0, console: 0, incomplete: 0
  FAIL    certificates — violations: 0, console: 0, incomplete: 0
  FAIL    cbom — violations: 0, console: 0, incomplete: 0
  FAIL    roadmap — violations: 0, console: 0, incomplete: 0
  FAIL    trends — violations: 0, console: 0, incomplete: 0
  FAIL    qramm — violations: 0, console: 0, incomplete: 0
  FAIL    qramm-assessment — violations: 0, console: 0, incomplete: 0
  FAIL    hardware — violations: 0, console: 0, incomplete: 0
  FAIL    compare — violations: 0, console: 0, incomplete: 0
```

`findings-storyline` (the interaction slug) never appears: the primary `findings` route's
missing-baseline branch does `await page.close(); continue`, which — as pre-existing harness
control flow untouched by this plan — skips the interaction block entirely. This is expected:
the interaction sweep only ever runs after its parent route's baseline check passes.

**This is exactly the CI state this plan's Task 2 predicted and is required to stay in.**
216-08 must generate and commit `-light.json` baselines from the Linux CI job (D-15 — never
from this macOS run) before the `a11y` gate job's light step goes green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `theme-sweep-contract.test.ts`'s mechanism-guard assertion was a
tautology against the harness's own documentation, not a real regression check**
- **Found during:** Task 3, first test run.
- **Issue:** The plan's action text specified `not.toContain('classList.add')` /
  `not.toContain('setEmulatedMedia')`-shaped assertions. `run-a11y.mjs`'s own D-01 comment
  block *names* `Emulation.setEmulatedMedia` as the rejected alternative (as Task 1 explicitly
  requires it to), so a bare substring check failed immediately against prose, not code.
- **Fix:** Tightened both assertions to regex-match an actual call shape
  (`/\.setEmulatedMedia\(/`, `/classList\.add\(\s*THEME\b/`) rather than a bare substring, so
  the guard fires on a real mechanism swap and not on the very documentation D-01 requires.
- **Files modified:** `src/dashboard/tests/a11y/theme-sweep-contract.test.ts`
- **Commit:** `cbf694a5`

**2. [Rule 3 - Blocking] Two workflow steps had to use the explicit `a11y:check:dark` /
`a11y:baseline:dark` script names instead of the pre-existing unsuffixed alias, or Task 3's
own contract test could not be written symmetrically**
- **Found during:** Task 3, writing the per-theme workflow-text assertion.
- **Issue:** Task 2's action text said only to *rename* the existing dark-theme steps, not
  change their `run:` command — leaving them at `npm run a11y:check` / `npm run
  a11y:baseline` (now aliases to the `:dark` forms). A THEMES-derived
  `it.each(THEMES)` assertion checking for `npm run a11y:check:<theme>` in the workflow text
  would then need to special-case `dark` to accept the unsuffixed alias, defeating the
  "derived from source, not a written list" guard the whole plan exists to install.
- **Fix:** Changed those two `run:` lines to the explicit `a11y:check:dark`/
  `a11y:baseline:dark` forms. Behaviourally identical (both are the same underlying script
  via the alias), and consistent with D-16's own stated rationale ("an unnamed dimension is
  exactly the defect class being drained").
- **Files modified:** `.github/workflows/dashboard-quality.yml`
- **Commit:** `cbf694a5`

### Findings (not defects, recorded per CLAUDE.md's "a count that disagrees is a finding")

**`npm run a11y:check` (dark) is RED on this machine at 3 routes, not the 2 the plan
predicted.** `/certificates` and `/hardware` fail on `color-contrast` — expected, this is
216-02's enriched fixture doing its job. `/data-at-rest` ALSO fails
(`scrollable-region-focusable count 1 is BELOW baseline 2 — Baseline is stale`) — this is the
ALREADY-DOCUMENTED macOS-vs-Linux render mismatch named in `run-a11y.mjs`'s own D-13 comment
(baseline `2` is the CI-observed value from Phase 177-07; this machine renders `1`), entirely
unrelated to this plan's changes, and intentionally left unresolved pending 216-08's
CI-derived `countRange` for that entry. The other 10 routes/interactions (`root`, `findings`,
`findings-storyline`, `identity`, `motion`, `cbom`, `roadmap`, `trends`, `qramm`,
`qramm-assessment`, `compare`) are unchanged `PASS`. Not fixed here — HARNESS-03/D-13/D-14
scope it to 216-08's Linux-derived bounds, and this plan's job is instrument repair, not
baseline regeneration.

## Requirements Coverage

HARNESS-01 — theme dimension added to the harness, both themes swept for the default variant
via the real localStorage path, D-03 combinations refused loudly, both npm scripts and both
CI jobs enumerate both themes, and a mechanical contract test fails if any of the three ever
drift apart. **Complete for this plan's scope** — the `a11y` gate job's light step staying RED
until 216-08 lands Linux-generated baselines is the plan's own stated, intentional end state,
not a gap in this plan.

## Verification

- `npx vitest run tests/a11y/` — 91/91 passed across 6 files (pinned-deps 7, theme-sweep-contract 8, fixture-coverage 7, accepted-violations-freshness 7, badge-variant-coverage 6, baseline-diff 56).
- `npm run lint` — 0 errors (1 pre-existing, unrelated warning in `ConnectorsPanel.test.tsx`).
- `npm run build` — succeeds; dashboard bundle rebuilt and committed with Task 1.
- `npm run test` — 538 passed, 2 skipped (unrelated), 88 files.
- `A11Y_THEME=light VITE_A11Y_FIXTURE_VARIANT=empty node tests/a11y/run-a11y.mjs` — exit 1, `REFUSED ... D-03`, no preview/browser started.
- `grep -c "evaluateOnNewDocument" run-a11y.mjs` == 1; `grep -c "incomplete" run-a11y.mjs` == 14 (>= 3 required).
- `grep -c "chrome-version:" dashboard-quality.yml` == 3 (unchanged); `grep -c "a11y:check:light\|a11y:baseline:light"` == 2.
- `.planning/STATE.md` full diff: 1 line changed, 0 frontmatter keys touched, no multi-line value orphaned (pre-image at `/tmp/state.pre-216-04.md`).
- Task 3 falsification: light-theme step deleted -> test RED naming `light` verbatim above; restored -> byte-identical `diff`, test GREEN 8/8.

## Known Stubs

None.

## Threat Flags

None — this plan's only new surface (the injected `localStorage.setItem` page script) was
already dispositioned `accept` as T-216-08 in 216-04-PLAN.md's own threat model (runs against
localhost `vite preview` in a headless, `--no-sandbox` CI browser already trusted with the
same content; the injected value is drawn from the `THEMES` allowlist).

## Self-Check: PASSED

- `src/dashboard/tests/a11y/theme-sweep-contract.test.ts` — FOUND
- `src/dashboard/src/components/theme-context.ts` (THEME_STORAGE_KEY export) — FOUND
- Commit `ef5ad3a3` (Task 1) — FOUND in `git log --oneline --all`
- Commit `8601eff0` (Task 2) — FOUND in `git log --oneline --all`
- Commit `cbf694a5` (Task 3) — FOUND in `git log --oneline --all`
