---
phase: 43-dashboard-polish
plan: "01"
subsystem: dashboard-test-infra
tags: [react, vite, axe-core, puppeteer, a11y, test-harness]
dependency_graph:
  requires: []
  provides: [a11y-harness, fixture-middleware, baseline-json]
  affects: [src/dashboard/tests/a11y/, src/dashboard/vite.config.ts, src/dashboard/package.json]
tech_stack:
  added: ["@axe-core/puppeteer@^4.11.3", "puppeteer-core@^24.42.0"]
  patterns: [vite-middleware-fixture, node-esm-test-harness, axe-core-baseline-diff]
key_files:
  created:
    - src/dashboard/tests/a11y/run-a11y.mjs
    - src/dashboard/tests/a11y/routes.json
    - src/dashboard/tests/a11y/fixture-scan.json
    - src/dashboard/tests/a11y/fixture-trends.json
    - src/dashboard/tests/console-allowlist.json
    - src/dashboard/tests/a11y/baseline-root.json
    - src/dashboard/tests/a11y/baseline-findings.json
    - src/dashboard/tests/a11y/baseline-identity.json
    - src/dashboard/tests/a11y/baseline-motion.json
    - src/dashboard/tests/a11y/baseline-data-at-rest.json
    - src/dashboard/tests/a11y/baseline-certificates.json
    - src/dashboard/tests/a11y/baseline-cbom.json
    - src/dashboard/tests/a11y/baseline-roadmap.json
    - src/dashboard/tests/a11y/baseline-trends.json
  modified:
    - src/dashboard/package.json
    - src/dashboard/vite.config.ts
decisions:
  - "Used @axe-core/puppeteer (D-01 revised) to collapse axe + console capture into one harness rather than @axe-core/cli + separate puppeteer script"
  - "Trends API path is /api/trends (not /api/scan/trends as referenced in plan) — corrected fixture middleware to match actual FastAPI route"
  - "Added /api/scans fixture handler (returns []) to prevent ScanContext from surfacing 404 errors during harness runs"
  - "VITE_A11Y_FIXTURE_VARIANT=empty serves {} for scan/latest and {} for trends; loading variant adds 3s delay to scan/latest"
  - "Generated 9 initial baselines via a11y:baseline — baselines capture current violations (Plans 02/03 will reduce them)"
metrics:
  duration: "~25 min"
  completed: "2026-05-01"
  tasks: 3
  files_changed: 17
---

# Phase 43 Plan 01: A11y + Console-Capture Test Harness — Summary

Stand up the a11y + console-capture test harness with @axe-core/puppeteer driving 9 dashboard routes via Vite preview with a seeded fixture middleware.

## What Was Built

### Task 1: Install devDeps + fixtures + config files

- Added `@axe-core/puppeteer@^4.11.3` and `puppeteer-core@^24.42.0` to `devDependencies`
- Added four npm scripts: `a11y:check`, `a11y:check:empty`, `a11y:check:loading`, `a11y:baseline`
- Created `tests/a11y/routes.json` — 9 routes mirroring `App.tsx` (excludes `/print` per scope)
- Created `tests/a11y/fixture-scan.json` — hand-authored schema-conformant payload with populated `findings` (3), `motion_findings` (2), `dar_findings` (2), `cbom_components` (4), `identity_findings` (2), `certificates` (2), `roadmap` (4 nodes / 3 edges); sanitized hostnames use `chaos-lab.local`
- Created `tests/a11y/fixture-trends.json` — trend report with current/previous session comparison, new/resolved findings
- Created `tests/console-allowlist.json` — recharts `defaultProps` entry with all 5 required fields (pattern, library, upstream, owner, added)

### Task 2: a11yFixture Vite plugin

Extended `vite.config.ts` with:
- `readFileSync` + `Plugin` imports
- `a11yFixture()` plugin function with shared `handler` that intercepts `/api/scan/latest`, `/api/scans`, and `/api/trends`
- Registered in both `configureServer` and `configurePreviewServer`
- Gated on `VITE_A11Y_FIXTURE` env var (T-43-01: no-op in production)
- Supports `VITE_A11Y_FIXTURE_VARIANT=empty|loading` variants
- Plugin added to plugins array: `[react(), a11yFixture()]`
- Build exits 0; zero src/ imports of tests/a11y/ confirmed

### Task 3: run-a11y.mjs harness

Created 214-line Node ESM script at `tests/a11y/run-a11y.mjs`:
- Boots `vite preview` as a subprocess with `VITE_A11Y_FIXTURE=1`
- Waits for port 4173 with 30s TCP poll (250ms backoff)
- Launches headless Chrome via `puppeteer.launch({ channel: 'chrome' })` with `executablePath` fallback
- For each route: attaches console capture, navigates with `networkidle0`, runs `AxePuppeteer.withTags(['wcag2a','wcag2aa']).analyze()`
- `--update-baselines` mode: writes `baseline-{slug}.json` per route
- Diff mode: computes `(id, sortedTargets)` delta against saved baseline; exits 1 on new violations
- Console: filters against ALLOWLIST_REGEXES; exits 1 on unallowlisted messages
- Kills preview subprocess on normal exit and SIGINT/SIGTERM

Generated 9 initial baselines via `npm run a11y:baseline` — harness runs end-to-end (exit 1 expected because existing violations are now captured as baselines).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected trends API path in fixture middleware**
- **Found during:** Task 2 implementation
- **Issue:** Plan referenced `/api/scan/trends` but `useTrendsData.ts` fetches `/api/trends` (confirmed in `quirk/dashboard/api/routes/trends.py:52` `@router.get("/trends", ...)`). The plan's middleware would have silently never intercepted trends requests.
- **Fix:** Changed `/api/scan/trends` to `/api/trends` in the `a11yFixture` handler
- **Files modified:** `src/dashboard/vite.config.ts`
- **Commit:** faa6118

**2. [Rule 2 - Missing Critical Functionality] Added /api/scans fixture handler**
- **Found during:** Task 2 implementation
- **Issue:** `useScanList.ts` fetches `/api/scans` to populate the scan selector dropdown. Without a fixture handler, the ScanContext would receive a 404 and may surface an error state that obscures the actual page content during axe runs.
- **Fix:** Added `/api/scans` handler returning `[]` to the `a11yFixture` plugin
- **Files modified:** `src/dashboard/vite.config.ts`
- **Commit:** faa6118

**3. [Rule 3 - Blocking] Static build artifacts replaced by build run**
- **Found during:** Task 3 (after running `a11y:baseline` which triggers `npm run build`)
- **Issue:** Build run produced new asset files with updated content hashes (`index-CyXKCw3A.css`, `index-uXEUUTLg.js`), replacing tracked files (`index-BPsGddYv.css`, `index-IsPyIPTZ.js`). Git showed tracked file deletions.
- **Fix:** Staged both the new and deleted static assets in the Task 3 commit
- **Files modified:** `quirk/dashboard/static/assets/*`
- **Commit:** b428bfd

## Known Stubs

None — all fixture data is schema-conformant and populates non-empty arrays for all 7 required fields.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. The `a11yFixture` plugin is a no-op in production (T-43-01 satisfied: `! grep -r "tests/a11y" src/dashboard/src/`).

## Self-Check: PASSED

All 7 artifact files confirmed on disk. All 4 task commits confirmed in git log (14925a7, fa444a3, faa6118, b428bfd).
