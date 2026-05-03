---
phase: 43-dashboard-polish
plan: "04"
subsystem: dashboard-ci-closeout
tags: [ci, github-actions, a11y, baselines, allowlist, uat, obsidian, validation]
dependency_graph:
  requires: [43-01, 43-02, 43-03]
  provides: [a11y-baselines, dashboard-quality-workflow, uat-43-series, obsidian-phase-note]
  affects:
    - src/dashboard/tests/a11y/baseline-root.json
    - src/dashboard/tests/a11y/baseline-findings.json
    - src/dashboard/tests/a11y/baseline-identity.json
    - src/dashboard/tests/a11y/baseline-motion.json
    - src/dashboard/tests/a11y/baseline-data-at-rest.json
    - src/dashboard/tests/a11y/baseline-certificates.json
    - src/dashboard/tests/a11y/baseline-cbom.json
    - src/dashboard/tests/a11y/baseline-roadmap.json
    - src/dashboard/tests/a11y/baseline-trends.json
    - src/dashboard/tests/console-allowlist.json
    - .github/workflows/dashboard-quality.yml
    - docs/UAT-SERIES.md
    - .planning/phases/43-dashboard-polish/43-VALIDATION.md
tech_stack:
  added: []
  patterns: [axe-baseline-lock, gha-path-filtered-workflow, vault-filesystem-write]
key_files:
  created:
    - .github/workflows/dashboard-quality.yml
  modified:
    - src/dashboard/tests/a11y/baseline-root.json
    - src/dashboard/tests/a11y/baseline-findings.json
    - src/dashboard/tests/a11y/baseline-identity.json
    - src/dashboard/tests/a11y/baseline-motion.json
    - src/dashboard/tests/a11y/baseline-data-at-rest.json
    - src/dashboard/tests/a11y/baseline-certificates.json
    - src/dashboard/tests/a11y/baseline-cbom.json
    - src/dashboard/tests/a11y/baseline-roadmap.json
    - src/dashboard/tests/a11y/baseline-trends.json
    - src/dashboard/tests/console-allowlist.json
    - src/dashboard/vite.config.ts
    - docs/UAT-SERIES.md
    - .planning/phases/43-dashboard-polish/43-VALIDATION.md
decisions:
  - "Regenerated all 9 baselines after fixing Cytoscape HSL syntax error and roadmap/executive/dar empty-state crashes that were causing pre-Plan-04 violations"
  - "Orchestrator added two post-Task-2 bug fix commits: 3s delay on /api/trends for loading variant, and Cache-Control: no-store on all fixture API responses — both reflected in this SUMMARY as plan deliverables"
  - "GHA workflow uses PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable on ubuntu-latest (avoids channel:'chrome' resolution failure on some runner images)"
  - "UAT-SERIES.md Last Updated header updated to 2026-05-01 with Phase 43 wrap summary"
  - "43-VALIDATION.md flipped: status->complete, nyquist_compliant->true, wave_0_complete->true, all sign-off checkboxes ticked"
metrics:
  duration: "~30 min"
  completed: "2026-05-01"
  tasks: 5
  files_changed: 14
---

# Phase 43 Plan 04: Baselines + CI + Close-out — Summary

Captured 9 axe baseline JSONs locking the Phase 43 green state, wired GitHub Actions dashboard-quality CI workflow gating `src/dashboard/**` PRs, executed CLAUDE.md mandatory phase close-out (UAT-SERIES update, Obsidian vault sync, Obsidian phase note), and flipped the 43-VALIDATION.md to complete.

## What Was Built

### Task 1: Generate baselines, fix bugs, verify full sweep

Re-ran `npm run a11y:baseline` to capture all 9 per-route baseline JSONs after bug fixes in the same task surfaced three issues:

1. **Cytoscape HSL syntax error in roadmap.tsx** — canvas wrapper used malformed `aria-label` with an HSL color literal; fixed inline before re-running baselines.
2. **executive.tsx empty-state crash** — the page-level empty branch was missing a required return; fixed during baseline generation.
3. **data-at-rest.tsx import error** — a renamed import caused the DAR page to throw during axe navigation; corrected before final baseline run.

After fixes, `npm run a11y:check` and `npm run a11y:check:empty` both exit 0. The `console-allowlist.json` already contained all required fields (no new entries needed). Hygiene check confirmed `console-allowlist.json` is never imported by app code.

Commits: `ac35c2a` (baselines + bug fixes), `0fb4f4a` (refreshed build artifacts)

### Task 2: Create GitHub Actions workflow for dashboard quality gate

Created `.github/workflows/dashboard-quality.yml` — the first workflow in this repository:

- Triggers on PRs touching `src/dashboard/**` or `.github/workflows/dashboard-quality.yml`
- Runs on `ubuntu-latest` with Node 20 (npm cache keyed to `src/dashboard/package-lock.json`)
- Steps: `npm ci` → `npm run build` → `npm run lint` → `npm run a11y:check` → `npm run a11y:check:empty`
- Both a11y steps set `PUPPETEER_EXECUTABLE_PATH: /usr/bin/google-chrome-stable`

Commit: `ff89ce8`

### Task 3 (Checkpoint): Human verification

Human-verify checkpoint approved. Verified items:
- All 9 routes render populated data (happy fixture)
- All 9 routes render explicit empty states (empty fixture)
- Loading variant shows skeleton/PageSpinner ~3s before content
- Tab key navigation shows visible focus rings on sidebar links and interactive elements
- `npm run a11y:check` and `npm run a11y:check:empty` exit 0

### Orchestrator bug fixes (post-Task-2)

Two commits added by orchestrator after Task 2:
- `fix(43-04): add loading delay to /api/trends fixture variant` — adds 3s delay to the `/api/trends` response in the loading variant (previously only `/api/scan/latest` was delayed)
- `fix(43-04): add Cache-Control: no-store to fixture API responses` — prevents browser from caching fixture responses between fixture variant switches during manual testing

### Task 4: Update docs/UAT-SERIES.md, sync to Obsidian vault, write Obsidian phase note, flip validation frontmatter

- **UAT-SERIES.md** — Added UAT-43-01 through UAT-43-05 covering: happy axe sweep, empty axe sweep, keyboard focus visibility, loading-state first paint, and GitHub Actions workflow verification. Bumped Last Updated to 2026-05-01.
- **Vault sync** — `docs/UAT-SERIES.md` synced to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` with project frontmatter prepended.
- **Obsidian phase note** — Written to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-43-Dashboard-Polish.md` with `status: complete` frontmatter, Goal, Requirements Covered, Success Criteria, four What-Was-Built subsections (one per plan), Verification outcome, and Links.
- **43-VALIDATION.md** — Flipped `status: draft` → `status: complete`, `nyquist_compliant: false` → `nyquist_compliant: true`, `wave_0_complete: false` → `wave_0_complete: true`; all 6 sign-off checkboxes ticked; Per-Task Verification Map rows set to `green`; Approval set to `approved 2026-05-01`.

Commit: `ac28ab3`

### Task 5: Final verification

Working tree clean (no staged modified files outside SUMMARY/STATE). All phase-43 commits present:
- `ac35c2a` — baselines + Cytoscape/roadmap/executive/dar bug fixes
- `0fb4f4a` — refreshed build artifacts
- `ff89ce8` — GitHub Actions dashboard-quality workflow
- `979fc59` — fix: /api/trends loading delay
- `4a77549` — fix: Cache-Control no-store on fixture responses
- `ac28ab3` — docs: UAT-SERIES + VALIDATION flip

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Cytoscape HSL syntax error in roadmap.tsx**
- **Found during:** Task 1 (baseline generation — axe reported violation on /roadmap)
- **Issue:** `aria-label` on the canvas wrapper contained a malformed HSL color literal causing the axe `image-alt` rule to flag the element
- **Fix:** Corrected the `aria-label` string to plain text
- **Files modified:** `src/dashboard/src/pages/roadmap.tsx`
- **Commit:** ac35c2a

**2. [Rule 1 - Bug] Fixed executive.tsx empty-state crash**
- **Found during:** Task 1 (baseline generation — /root crashed during axe run)
- **Issue:** Empty-state branch in executive.tsx was missing a proper return statement, causing the component to throw during axe navigation with empty fixture
- **Fix:** Added correct return to the empty-state branch
- **Files modified:** `src/dashboard/src/pages/executive.tsx`
- **Commit:** ac35c2a

**3. [Rule 1 - Bug] Fixed data-at-rest.tsx import error**
- **Found during:** Task 1 (baseline generation — /data-at-rest page threw import error)
- **Issue:** A renamed import in data-at-rest.tsx caused a runtime error during axe navigation
- **Fix:** Corrected the import reference
- **Files modified:** `src/dashboard/src/pages/data-at-rest.tsx`
- **Commit:** ac35c2a

**4. Orchestrator bug fixes (post-Task-2 checkpoint)**
- `/api/trends` loading delay (3s) added to loading fixture variant — ensures trends page shows PageSpinner during loading variant testing
- `Cache-Control: no-store` added to all fixture API responses — prevents stale fixture responses across variant switches
- Both committed to plan 43-04 branch by orchestrator; reflected in this SUMMARY as plan deliverables

## Known Stubs

None — all baselines reflect real axe-core output from the post-Plan-02/03 clean state. All UAT-SERIES entries reference real command-line invocations. No placeholder data.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes introduced in this plan. The GitHub Actions workflow has no elevated permissions beyond default read and runs no privileged steps.

## Self-Check: PASSED

All artifact files confirmed on disk:
- 9 baseline JSONs: FOUND
- `.github/workflows/dashboard-quality.yml`: FOUND
- `docs/UAT-SERIES.md` contains UAT-43-01..05 (grep count: 12): FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`: FOUND (source frontmatter present)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-43-Dashboard-Polish.md`: FOUND (status: complete)
- `43-VALIDATION.md` nyquist_compliant: true, wave_0_complete: true, status: complete, Approval: approved: CONFIRMED

All commits confirmed in git log: ac35c2a, 0fb4f4a, ff89ce8, 979fc59, 4a77549, ac28ab3
