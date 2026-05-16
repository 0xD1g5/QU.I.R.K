---
phase: 76-react-frontend-warnings
plan: 02
subsystem: react-frontend
tags: [react, theme, pdf, useeffect, audit-flip, qramm, compliance, vitest]
requires:
  - 76-01 (RED→GREEN cadence + audit-flip pattern; test-setup unchanged at that point)
provides:
  - VALID_THEMES allowlist + exported getStoredTheme helper (src/dashboard/src/components/theme-provider.tsx)
  - useRef-tracked PDF revoke timer + blob URL with unmount cleanup (src/dashboard/src/pages/executive.tsx)
  - Narrowed ComplianceMapTab useEffect dep ([ctx.sessionId] only) (src/dashboard/src/components/qramm/ComplianceMapTab.tsx)
  - In-memory localStorage shim for jsdom 25 (src/dashboard/src/test-setup.ts)
affects:
  - AUDIT-TASKS.md (WR-04, WR-05, WR-13 closed)
  - Dashboard built statics rebuilt (quirk/dashboard/static/)
tech-stack:
  added: []
  patterns:
    - "as const tuple + includes-narrowed cast (D-05)"
    - "useRef + useEffect cleanup for async resource lifetime (D-06, mirrors Phase 62 HOOK pattern)"
    - "useEffect dependency narrowing to stable id (D-07, sessionId not whole scoreResult)"
key-files:
  created:
    - .planning/phases/76-react-frontend-warnings/76-02-SUMMARY.md
    - src/dashboard/src/components/__tests__/theme-provider.test.tsx
    - src/dashboard/src/pages/__tests__/executive-pdf-cleanup.test.tsx
    - src/dashboard/src/components/qramm/__tests__/compliance-map-tab.test.tsx
  modified:
    - src/dashboard/src/components/theme-provider.tsx
    - src/dashboard/src/pages/executive.tsx
    - src/dashboard/src/components/qramm/ComplianceMapTab.tsx
    - src/dashboard/src/test-setup.ts
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
    - quirk/dashboard/static/index.html
    - quirk/dashboard/static/assets/index-IKFPYqJz.js (was index-qt7x_qm6.js)
decisions:
  - D-05 implemented as exported helper getStoredTheme (preferred unit-testable shape over inline closure)
  - D-06 cleanup useEffect placed at top of ExecutivePage body adjacent to ref decls; setTimeout cast to window.setTimeout for numeric id
  - D-07 dependency narrowed to [ctx.sessionId]; RESEARCH C-4 confirmed ctx.sessionId is the stable field (ctx.scoreResult.session_id does not exist on the ScoreResult type — only overall/maturity/dimensions/profile_multiplier)
  - Rule 3 deviation — added in-memory localStorage shim to src/test-setup.ts: jsdom 25 does not expose globalThis.localStorage by default ("ExperimentalWarning: localStorage is not available because --localstorage-file was not provided")
metrics:
  duration_minutes: 6
  completed_date: 2026-05-15
  tasks: 3
  files_changed: 7
  test_count: 14
---

# Phase 76 Plan 02: REACT-02 — localStorage allowlist, PDF cleanup, ComplianceMapTab dep narrowing Summary

REACT-02 (WR-04, WR-05, WR-13) closed: theme-provider now validates `localStorage` against a `VALID_THEMES` allowlist with silent fallback, executive PDF download tracks the revoke timer + blob URL via `useRef` with a `useEffect` cleanup, and `ComplianceMapTab` no longer re-fetches on every `scoreResult` mutation.

## Tasks Completed

| Task | Description                                                    | Commit  |
| ---- | -------------------------------------------------------------- | ------- |
| 1    | RED — 3 failing test modules (theme, pdf cleanup, compliance)  | 0da702d |
| 2    | GREEN — D-05 / D-06 / D-07 implementations + localStorage shim | eb8e494 |
| 3    | Build gate (npm run build exit 0) + audit flips WR-04/05/13    | 01e77e2 |

## What Was Built

### D-05 (WR-04): theme-provider allowlist

Added `VALID_THEMES = ['light', 'dark', 'system'] as const` plus an exported `getStoredTheme(storageKey, defaultTheme)` helper. The `ThemeProvider` `useState` initializer now calls the helper instead of the raw cast at line 17. Tampered or stale localStorage values silently fall back to `defaultTheme` — no `console.warn` (theme is QoL, not security). SSR-safe via `typeof window === 'undefined'` guard.

### D-06 (WR-05): executive PDF cleanup

Added `revokeTimerRef = useRef<number | null>(null)` and `blobUrlRef = useRef<string | null>(null)` at the top of `ExecutivePage`, plus a component-scope `useEffect(() => () => { ... }, [])` that calls `clearTimeout` and `URL.revokeObjectURL` on unmount. The setTimeout in `handleExportPdf` now writes its id to `revokeTimerRef.current` and clears both refs when the timer fires. Mirrors Phase 62 HOOK cleanup pattern.

`coerceErrorDetail` (76-01) and the WR-06 body.detail block at line 118 left untouched.

### D-07 (WR-13): ComplianceMapTab dep narrow

Dependency array on the compliance-map fetch effect narrowed from `[ctx.sessionId, ctx.scoreResult]` to `[ctx.sessionId]`. RESEARCH C-4 verified during this plan: `ctx.scoreResult` typed as `{ overall, maturity, dimensions, profile_multiplier }` — there is no `session_id` field on it, so the original assumption of "track scoreResult identity" was always wrong. Compliance rows are framework-question mapping data, independent of scored values; re-fetching on every score recompute was spurious.

Phase 55 Calculate Score button preserved untouched. Recharts not touched (D-12).

## Tests

14 new Vitest assertions across 3 files; all green. Full dashboard suite: 30 passed / 30.

- `theme-provider.test.tsx` — 9 tests (parametrized over 5 stored values + key-absent + console.warn + default-theme respect + tuple shape)
- `executive-pdf-cleanup.test.tsx` — 2 tests (unmount-before-timer + timer-then-unmount-idempotent)
- `compliance-map-tab.test.tsx` — 3 tests (initial fetch + scoreResult-mutation-stable + sessionId-change-refetches)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] jsdom 25 missing localStorage global**

- **Found during:** Task 1 RED run
- **Issue:** jsdom 25 (used by Vitest 2.1.9) does not expose `globalThis.localStorage` by default. Node 22 emits `ExperimentalWarning: localStorage is not available because --localstorage-file was not provided.` Tests calling `localStorage.clear()` failed with `TypeError: Cannot read properties of undefined (reading 'clear')`.
- **Fix:** Added an in-memory localStorage shim in `src/dashboard/src/test-setup.ts` (Map-backed Storage implementation). Only installed when `globalThis.localStorage === undefined`, so real browser-like envs are untouched.
- **Files modified:** `src/dashboard/src/test-setup.ts`
- **Commit:** eb8e494 (bundled with GREEN — shim is part of getting the GREEN tests to even run)

## Verification

- `cd src/dashboard && npm test -- theme-provider executive-pdf-cleanup compliance-map-tab --run` → 14 passed
- `cd src/dashboard && npm test -- --run` → 30 passed / 9 files (no regressions)
- `cd src/dashboard && npm run build` → exit 0, statics emitted to `quirk/dashboard/static/`
- `grep -cE "react-frontend/WR-(04|05|13).*Phase 76.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → 3
- D-12 do-not-touch list honored: no Phase 55 Calculate Score button changes, no Recharts touches, no Phase 62 hook touches

## Self-Check: PASSED

- FOUND: src/dashboard/src/components/__tests__/theme-provider.test.tsx
- FOUND: src/dashboard/src/pages/__tests__/executive-pdf-cleanup.test.tsx
- FOUND: src/dashboard/src/components/qramm/__tests__/compliance-map-tab.test.tsx
- FOUND: commit 0da702d (RED)
- FOUND: commit eb8e494 (GREEN)
- FOUND: commit 01e77e2 (audit + statics)
- AUDIT-TASKS.md WR-04, WR-05, WR-13 rows show `Phase 76 | [x] closed`
- npm run build exit 0 confirmed
