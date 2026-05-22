---
phase: 86-scoring-correctness-hotfix
plan: "02"
subsystem: dashboard/gauges
tags: [dashboard, gauge, frontend, tdd, vitest, bug-fix]
dependency_graph:
  requires: [normalized-readiness-aggregator]
  provides: [maxvalue-aware-gauge, executive-subscore-wiring, dar-tab-wiring, gauge-vitest-coverage]
  affects:
    - src/dashboard/src/components/gauges/ScoreGauge.tsx
    - src/dashboard/src/pages/executive.tsx
    - src/dashboard/src/pages/data-at-rest.tsx
    - src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx
    - quirk/dashboard/static/ (rebuilt bundle)
tech_stack:
  added: []
  patterns: [normalized-fraction gauge, vitest+RTL component testing]
key_files:
  created:
    - src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx
  modified:
    - src/dashboard/src/components/gauges/ScoreGauge.tsx
    - src/dashboard/src/pages/executive.tsx
    - src/dashboard/src/pages/data-at-rest.tsx
decisions:
  - "D-04: Add maxValue?: number prop (default 100) to ScoreGauge; internal fraction = score/maxValue"
  - "D-05: _gaugeColor operates on normalized fraction (0.0-1.0) with thresholds >= 0.8 (green) / >= 0.5 (amber) / else (red)"
  - "D-06: executive.tsx subscore gauges (lines 262-267) pass maxValue={25}; overall gauge (lines 245-250) keeps default"
  - "D-07: data-at-rest.tsx:301 standalone Data at Rest tab gauge passes maxValue={25}; print.tsx confirmed NOT a caller"
  - "D-10: Vitest coverage for green-at-max, red-at-low, amber/green boundary, and legacy-default-red cases"
metrics:
  duration: "< 10 minutes"
  completed: "2026-05-22"
  tasks_completed: 3
  files_changed: 4
  tests_added: 4
---

# Phase 86 Plan 02: Dashboard Gauge maxValue Wiring Summary

**One-liner:** Add `maxValue?: number` prop (default 100) to `ScoreGauge`, rewrite `_gaugeColor` to operate on a normalized fraction, wire all seven subscore gauge callers with `maxValue={25}`, add vitest+RTL coverage for the D-10 boundary cases, and rebuild the pre-built statics.

## What Was Built

### Task 1 — ScoreGauge maxValue prop + normalized color thresholds

**File:** `src/dashboard/src/components/gauges/ScoreGauge.tsx`

Changes made:
- Added `maxValue?: number` to `ScoreGaugeProps` (default 100 — existing callers unaffected).
- Added `const fraction = Math.max(0, Math.min(1, score / maxValue))` near the top of the function body.
- Rewrote `_gaugeColor(score: number)` to `_gaugeColor(fraction: number)` with thresholds `>= 0.8` (quantum-safe/green), `>= 0.5` (quantum-at-risk/amber), else (quantum-vulnerable/red).
- Replaced `score / 100` in the `fillEndAngle` calculation with `fraction`.
- Updated `_gaugeColor(score)` call on the color derivation line to pass `fraction`.
- Removed the unused `fillLength` constant (was `(score / 100) * circumference`) and its `void fillLength` suppressor.
- The `{score}` text node remains unchanged — the raw numeric label is preserved.
- `isOverall` accent-color path is unchanged.

Before / after for the key color logic:
```typescript
// BEFORE
function _gaugeColor(score: number): string {
  if (score >= 80) return "hsl(var(--quantum-safe))"
  if (score >= 50) return "hsl(var(--quantum-at-risk))"
  return "hsl(var(--quantum-vulnerable))"
}
// ...
const color = strokeColor ?? (isOverall ? "hsl(var(--accent))" : _gaugeColor(score))

// AFTER
function _gaugeColor(fraction: number): string {
  if (fraction >= 0.8) return "hsl(var(--quantum-safe))"
  if (fraction >= 0.5) return "hsl(var(--quantum-at-risk))"
  return "hsl(var(--quantum-vulnerable))"
}
// ...
const fraction = Math.max(0, Math.min(1, score / maxValue))
const color = strokeColor ?? (isOverall ? "hsl(var(--accent))" : _gaugeColor(fraction))
```

Commit: `fad2ced` — `feat(86-02): ScoreGauge supports maxValue prop + normalized color thresholds`

### Task 2 — Wire executive.tsx + data-at-rest.tsx subscore gauges with maxValue={25}

**Files:** `src/dashboard/src/pages/executive.tsx`, `src/dashboard/src/pages/data-at-rest.tsx`

**executive.tsx diff (six insertions at lines 262-267):**

Before:
```tsx
<ScoreGauge score={score.subscores.hygiene} label="Hygiene" size={120} />
<ScoreGauge score={score.subscores.modern_tls} label="Modern TLS" size={120} />
<ScoreGauge score={score.subscores.identity_trust} label="Identity" size={120} />
<ScoreGauge score={score.subscores.agility_signals} label="Agility" size={120} />
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} />
<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} />
```

After:
```tsx
<ScoreGauge score={score.subscores.hygiene} label="Hygiene" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.modern_tls} label="Modern TLS" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.identity_trust} label="Identity" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.agility_signals} label="Agility" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.data_at_rest} label="Data at Rest" size={120} maxValue={25} />
<ScoreGauge score={score.subscores.data_in_motion} label="Data in Motion" size={120} maxValue={25} />
```

Overall-readiness gauge (lines 245-250) is unchanged — inherits default `maxValue=100`.

**data-at-rest.tsx diff (one insertion at line 301):**

Before:
```tsx
<ScoreGauge score={darScore} label="Data at Rest" size={120} />
```

After:
```tsx
<ScoreGauge score={darScore} label="Data at Rest" size={120} maxValue={25} />
```

Where `darScore = data?.score?.subscores?.data_at_rest ?? 0` (confirmed 0-25 subscore per D-07).

**Callers not touched (per D-07 verified audit):**
- `print.tsx` — does NOT import or render `ScoreGauge` (verified 2026-05-22). Not a caller. Not touched.
- `sidebar.tsx:2` — code comment referencing `ScoreGauge.tsx` token migration history; not a caller. Not touched.

**npm run build** rebuilt the pre-built statics at `quirk/dashboard/static/` — `dist/` updated; `quirk serve` will serve the corrected bundle.

Commit: `620e5db` — `feat(86-02): executive.tsx + data-at-rest.tsx subscore gauges use maxValue={25}`

### Task 3 — ScoreGauge vitest+RTL coverage (D-10 cases)

**File:** `src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx` (new)

Four `it(...)` cases covering all D-10 assertions:

| Test | Input | Expected stroke |
|------|-------|----------------|
| green when subscore equals category max | score=25, maxValue=25 (fraction=1.0 >= 0.8) | `hsl(var(--quantum-safe))` |
| red when subscore is low | score=3, maxValue=25 (fraction=0.12 < 0.5) | `hsl(var(--quantum-vulnerable))` |
| amber at overall=79, green at 80 boundary | score=79 / score=80, default maxValue | at-risk / safe |
| legacy-default red (no maxValue) | score=25, no maxValue (25/100=0.25 < 0.5) | `hsl(var(--quantum-vulnerable))` |

Query pattern: `container.querySelector('path[stroke^="hsl(var(--quantum"]')` — selects the colored fill path (not the background track which uses `--border`).

Results: `4 passed` in 18ms. Full suite after Task 3: `19 test files / 74 tests — all passed`. No regressions.

Commit: `b9bab9e` — `test(86-02): ScoreGauge color + scale coverage (D-10)`

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing lint errors in `executive.tsx` (react-refresh/only-export-components), `trends.tsx` (no-explicit-any), and `print.tsx` (unused-disable-directive) are out-of-scope pre-existing issues; logged here as deferral breadcrumb per deviation scope rules.

## TDD Gate Compliance

This plan is labeled `tdd="true"` per-task. All three tasks were AUTO tasks (implementation changes); the D-10 test task (Task 3) is the explicit test gate.

- Task 1: Component change — lint verified; `score/100` removal verified via grep returning no output.
- Task 2: Caller wiring — `grep -c` confirmed exactly 6 + 1 occurrences; `npm run build` exited 0.
- Task 3 (test): `npm test ScoreGauge.test.tsx` — 4 tests PASS; full suite — 74 tests PASS.

## Threat Flags

None. This change only modifies frontend rendering math. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `src/dashboard/src/components/gauges/ScoreGauge.tsx` contains `maxValue`: FOUND
- `grep -n "score / 100" ScoreGauge.tsx` returns empty (no live-code matches): CONFIRMED
- `grep -c "maxValue={25}" executive.tsx` = 6: CONFIRMED
- `grep -c "maxValue={25}" data-at-rest.tsx` = 1: CONFIRMED
- `src/dashboard/src/components/gauges/__tests__/ScoreGauge.test.tsx` exists: FOUND
- `npm test` — 74/74 tests pass: CONFIRMED
- `npm run build` exits 0 — statics regenerated: CONFIRMED
- Commit `fad2ced` exists: FOUND
- Commit `620e5db` exists: FOUND
- Commit `b9bab9e` exists: FOUND
