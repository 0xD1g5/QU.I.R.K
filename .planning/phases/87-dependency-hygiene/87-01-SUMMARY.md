---
phase: 87-dependency-hygiene
plan: 01
requirements: [DEP-01]
status: complete
completed: 2026-05-22
---

# 87-01 Summary — Node 20 → 24 CI bump (DEP-01)

## Objective

Raise the GitHub Actions Node runtime for the `dashboard-quality` workflow from
Node 20 to Node 24, clearing GitHub's runner default-switch deadline
(2026-06-16) before it lands.

## What was built

- **Node 24 pin** (`989be0c`, on `main`): one-line change to
  `.github/workflows/dashboard-quality.yml` — `node-version: '20'` → `'24'`,
  keeping `actions/setup-node@v4` unchanged. No remaining `node-version: '20'`
  reference in any workflow file.

- **Real-CI verification (D-02):** the `dashboard-quality` workflow is
  `pull_request`-only (paths `src/dashboard/**`, the workflow file), so a push
  to `main` cannot trigger it. Opened **PR #4**
  (`gsd/phase-87-node24-ci` → `main`) carrying the workflow change to trigger a
  real run. Run `26297453788` proved the **Node 24 toolchain works end-to-end**:
  `Setup Node` (24.x) ✅, `Install dependencies` (`npm ci`) ✅,
  `Build dashboard` (`tsc -b && vite build`) ✅, **`Lint` ✅**.

- **Lint-gate fix** (`326b247`, on `main`; mirrored to PR #4 as `a70e6f3`):
  the workflow had been red at `Lint` on 7 pre-existing, node-independent eslint
  errors that blocked the green-CI criterion. Fixed (no suppressions):
  - `react-refresh/only-export-components`: relocated test-only helpers
    `VALID_THEMES`/`getStoredTheme` → `theme-context.ts`, `coerceErrorDetail`
    → `executive-utils.ts`, `firstNonZeroComp` → `cbom-utils.ts`; test imports
    repointed; behavior unchanged.
  - `react-hooks/set-state-in-effect`: `useJobStatus` resets to loading via the
    React render-phase "adjust state when a prop changes" pattern.
  - `@typescript-eslint/no-explicit-any`: typed the `trends.tsx` Recharts tooltip
    callback with `TooltipProps` + a `TimelineRow` payload cast.
  - removed an unused `no-console` eslint-disable directive in `print.tsx`.
  - Verified locally: eslint clean, `tsc + vite` build green, 74/74 dashboard
    vitest pass. Static bundle rebuilt so the served assets match source.

## Verification

- `grep -rn "node-version: '20'" .github/workflows/` → empty.
- `.github/workflows/dashboard-quality.yml` contains `node-version: '24'`,
  `actions/setup-node@v4` unchanged.
- PR #4 run `26297453788`: Setup Node + Install + Build + **Lint** all green on
  Node 24 — the deadline-clearing intent of DEP-01 is satisfied on a real run.

## Deviations / deferrals

- **a11y sweep deferred (logged as tech debt).** With lint green, the pipeline
  reached the `Run axe + console sweep` step for the **first time ever** (lint
  had always failed first, skipping it). It is red on stale per-page a11y
  baselines + genuine `color-contrast`/`button-name` violations across all 11
  dashboard pages. This is orthogonal to the Node runtime and is a separate
  UI/a11y workstream — deferred to a dedicated phase (see ROADMAP backlog
  `BACK-A11Y-01`). The PR #4 run remains partially red on this gate only.
- **Scope note:** the lint fix (above) was an approved expansion beyond the
  one-line bump, required to exercise the CI gate past `Lint`.

## Commits

- `989be0c` ci(87-01): bump dashboard-quality Node runtime 20 → 24 (DEP-01)
- `326b247` fix(87-01): clear dashboard eslint errors blocking the Node 24 CI gate
- PR #4 branch: `a70e6f3` (source-only mirror for CI verification)
