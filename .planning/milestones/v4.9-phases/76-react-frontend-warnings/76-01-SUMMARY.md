---
phase: 76-react-frontend-warnings
plan: 01
subsystem: react-frontend
tags: [react, error-handling, pdf-export, qramm, audit-2026-05-08, REACT-01]
dependency_graph:
  requires: []
  provides:
    - "coerceErrorDetail(body: unknown): string helper exported from src/dashboard/src/pages/executive.tsx"
    - "QRAMM-error-aware data-ready sentinel guard on print.tsx"
    - "API-detail-bearing submitError in qramm-profile.tsx handleSubmit"
  affects:
    - "src/dashboard/src/pages/executive.tsx"
    - "src/dashboard/src/pages/print.tsx"
    - "src/dashboard/src/pages/qramm-profile.tsx"
tech-stack:
  added: []
  patterns:
    - "Defensive unknown→string body coercion (typeof guard + String fallback)"
key-files:
  created:
    - "src/dashboard/src/hooks/__tests__/useScanList.test.tsx"
    - "src/dashboard/src/pages/__tests__/executive-error-coercion.test.tsx"
    - "src/dashboard/src/pages/__tests__/print-pdf-cleanup.test.tsx"
    - "src/dashboard/src/pages/__tests__/qramm-profile-submit-error.test.tsx"
  modified:
    - "src/dashboard/src/pages/executive.tsx"
    - "src/dashboard/src/pages/print.tsx"
    - "src/dashboard/src/pages/qramm-profile.tsx"
    - ".planning/audit-2026-05-08/AUDIT-TASKS.md"
    - "quirk/dashboard/static/index.html"
    - "quirk/dashboard/static/assets/index-*.js (bundle hash refresh)"
decisions:
  - "D-01 (WR-02) audit-flip-only — useScanList hook AND scan-history consumer already emit 401/403/429/non-OK errors and render destructive-text Card. Verified by useScanList.test.tsx Part A (hook) + Part B (consumer banner)."
  - "D-02 coerceErrorDetail helper exported from executive.tsx (so tests can unit-test it); applied to handleExportPdf with operator-friendly Playwright-hint fallback when body has no actionable detail field."
  - "D-03 second useEffect at print.tsx now gates on !qrammError; visible role=alert div renders QRAMM-unavailable copy. BR-05 cleanup at lines 332-335 untouched per RESEARCH Pitfall 3."
  - "D-04 inlined the D-02 coercion as a local readApiError(resp, fallback) helper in qramm-profile.tsx so the page file stays independent of executive.tsx. Refactored the throw-based control flow to setSubmitError + early-return so the API body is preserved across the catch boundary."
metrics:
  duration_seconds: 377
  tasks_completed: 3
  files_changed: 8
  tests_added: 14
  completed: 2026-05-15
---

# Phase 76 Plan 01: REACT-01 — API error surfacing (WR-02, WR-06, WR-07, WR-08) Summary

API error surfacing landed across executive PDF, print sentinel, and QRAMM submit; useScanList hook + scan-history consumer audit-flipped with regression-guard test evidence.

## What Was Built

### D-01 (WR-02) — audit-flip-only
Confirmed via Wave 0 audit AND new `useScanList.test.tsx` (4 `it()` blocks) that:
- `useScanList()` already returns `{sessions, loading, error}` with 401/403/429/non-OK branches.
- `pages/scan-history.tsx` already renders a destructive-text Card on `error`.

No production code change required. Tests committed as regression guards.

### D-02 (WR-06) — `coerceErrorDetail`
Added an exported helper to `executive.tsx`:

```ts
export function coerceErrorDetail(body: unknown): string {
  if (body && typeof body === 'object' && typeof (body as {detail?: unknown}).detail === 'string') {
    return (body as { detail: string }).detail
  }
  return String(body ?? 'Unknown error')
}
```

Consumed by `handleExportPdf`. When the API returns no actionable `detail` field, the existing operator-friendly Playwright hint is preserved.

### D-03 (WR-07) — print sentinel guard
`print.tsx` second `useEffect` (around line 346) now gates `data-ready` on `!qrammError` in addition to `!loading && !qrammLoading`. A visible `role="alert"` div renders the copy *"QRAMM data unavailable — Q section omitted"* when `qrammError` is truthy.

**BR-05 cleanup effect at lines 332-335 was NOT touched** per RESEARCH Pitfall 3 (Phase 62 contract). Verified by grep — two `document.body.removeAttribute('data-ready')` matches still present.

### D-04 (WR-08) — submitError API surfacing
`qramm-profile.tsx::handleSubmit` previously threw on every non-OK response and the catch then displayed a generic connectivity string. Refactored to:
- Local helper `readApiError(resp, fallback)` parses the response body as JSON (or raw text) and applies D-02-style coercion.
- Non-OK branches now `setSubmitError(detail); return` instead of `throw`, preserving the body across the control-flow boundary.
- Operators now see `"Organization Name required"` (400 JSON) or `"server exploded"` (500 raw string) instead of the generic hint.

### Audit ledger
Flipped 4 react-frontend rows from `| — | [ ] open |` to `| Phase 76 | [x] closed |`:
- WR-02 (line 222), WR-06 (line 226), WR-07 (line 227), WR-08 (line 228).

7 remaining react-frontend WR rows (04, 05, 09, 10, 11, 12, 13) still `[ ] open` for 76-02 / 76-03 to close.

## Commits

| Task | Type | Hash    | Message                                                                                                |
|------|------|---------|--------------------------------------------------------------------------------------------------------|
| 1    | RED  | d863681 | test(76-01): add failing tests for REACT-01 (D-01 evidence, D-02 coercion, D-03 sentinel, D-04 submitError) |
| 2    | GREEN| 0ec493b | feat(76-01): implement REACT-01 fixes (D-02 coercion, D-03 sentinel guard, D-04 submitError)            |
| 3    | DOCS | 1aec991 | docs(76-01): close react-frontend WR-02/WR-06/WR-07/WR-08 in audit ledger                              |

## Verification Evidence

- `cd src/dashboard && npm test -- useScanList executive-error-coercion print-pdf-cleanup qramm-profile-submit-error` → **14/14 passed** (4 test files).
- `cd src/dashboard && npm run build` → **exit 0**, bundle emitted to `quirk/dashboard/static/`.
- `grep -cE "react-frontend/WR-(02|06|07|08).*Phase 76.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → **4**.
- `grep -cE "react-frontend/WR-(04|05|09|10|11|12|13).*\[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md` → **7**.
- BR-05 regression guard: 3rd `it()` in `print-pdf-cleanup.test.tsx` confirms `data-ready` removed on unmount.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `useScanList.test.ts` renamed to `.tsx`**
- **Found during:** Task 1 first test run.
- **Issue:** Part B of the test renders JSX (`<ScanHistoryPage />`), and Vite's esbuild transform rejects JSX in `.ts` files (`Expected ">" but found "/"`).
- **Fix:** Renamed `useScanList.test.ts` → `useScanList.test.tsx`. Content unchanged; the vitest `include` glob `src/**/__tests__/**/*.{test,spec}.{ts,tsx}` picks it up identically.
- **Files modified:** `src/dashboard/src/hooks/__tests__/useScanList.test.tsx`
- **Commit:** d863681

**2. [Rule 2 — Critical correctness] `handleSubmit` refactor from throw-to-catch into early-return**
- **Found during:** Task 2 (D-04 implementation).
- **Issue:** The existing `if (!resp.ok) throw new Error(...)` pattern dropped the response body before reaching the catch block, so no D-02-style coercion was possible without restructuring. A naive D-02 patch in the existing catch could not surface the API message.
- **Fix:** Replaced `throw` with `setSubmitError(detail); return` after consuming the response body via a local `readApiError` helper. Network-failure catch path retained the original generic fallback.
- **Files modified:** `src/dashboard/src/pages/qramm-profile.tsx`
- **Commit:** 0ec493b

**3. [Rule 2 — Critical correctness] Preserve Playwright-install hint when API returns empty body**
- **Found during:** Task 2.
- **Issue:** Pure D-02 coercion of `{}` (the prior `.catch(() => ({}))` fallback) yields `"[object Object]"`, which would replace the existing operator-friendly Playwright-install hint with a noise string.
- **Fix:** In `executive.tsx::handleExportPdf`, only show the coerced detail when `body.detail` is actually a string; otherwise keep the Playwright hint. Also changed `.json().catch(() => ({}))` to `.json().catch(() => null)` so coercion correctly treats parse failures as no-detail.
- **Files modified:** `src/dashboard/src/pages/executive.tsx`
- **Commit:** 0ec493b

### Auth Gates
None.

## Threat Mitigations Applied

| Threat ID | Mitigation                                                                                              |
|-----------|---------------------------------------------------------------------------------------------------------|
| T-76-01   | print.tsx second useEffect now gates `data-ready` on `!qrammError`; visible alert renders on QRAMM error |
| T-76-02   | executive.tsx `coerceErrorDetail` defends against non-string `body.detail` and raw-string bodies         |
| T-76-03   | qramm-profile.tsx surfaces API `detail` field via `readApiError`; operators see real validation reason  |
| T-76-04   | (accepted) — no new sanitization layer added                                                            |

## Known Stubs
None.

## Self-Check: PASSED

- `src/dashboard/src/hooks/__tests__/useScanList.test.tsx` — FOUND
- `src/dashboard/src/pages/__tests__/executive-error-coercion.test.tsx` — FOUND
- `src/dashboard/src/pages/__tests__/print-pdf-cleanup.test.tsx` — FOUND
- `src/dashboard/src/pages/__tests__/qramm-profile-submit-error.test.tsx` — FOUND
- Commit d863681 (RED) — FOUND in git log
- Commit 0ec493b (GREEN) — FOUND in git log
- Commit 1aec991 (DOCS) — FOUND in git log
- TDD gate compliance: `test(...)` (d863681) → `feat(...)` (0ec493b) sequence present
