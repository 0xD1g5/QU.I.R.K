---
phase: 77-info-code-quality-audit-ledger
plan: 04
subsystem: react-frontend
tags: [info, code-quality, react, tdd, frontend, polish]
requires: []
provides: [INFO-04]
affects:
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/pages/cbom.tsx
  - src/dashboard/src/pages/roadmap.tsx
  - src/dashboard/src/pages/findings.tsx
  - src/dashboard/src/pages/identity.tsx
  - src/dashboard/src/pages/print.tsx
  - src/dashboard/src/hooks/useQRAMMSession.ts
  - src/dashboard/src/hooks/useScanData.ts
tech_stack:
  added: []
  patterns:
    - "HMR-safe message-regex re-throw for cytoscape registration (RESEARCH C-12 / Pattern 8)"
    - "useMemo<ColumnDef<T>[]>(() => [...], []) for TanStack-table column stability (Pattern 6)"
    - "useCallback-wrapped resetSession() for ref-clearing across flow transitions"
    - "URL hoisted out of try-block for catch-handler reuse (RESEARCH Pitfall 8)"
    - "JSX <style>{constant}</style> for static stylesheet injection (Pattern 7)"
key_files:
  created:
    - src/dashboard/src/pages/__tests__/qramm-assessment-tab-comment.test.tsx
    - src/dashboard/src/pages/__tests__/cbom-cytoscape-catch.test.tsx
    - src/dashboard/src/pages/__tests__/findings-columns-memo.test.tsx
    - src/dashboard/src/hooks/__tests__/useQRAMMSession-reset.test.ts
    - src/dashboard/src/pages/__tests__/cbom-compByAlg-statistic.test.tsx
    - src/dashboard/src/pages/__tests__/print-no-createElement.test.tsx
    - src/dashboard/src/hooks/__tests__/useScanData-error-url.test.ts
  modified:
    - src/dashboard/src/pages/qramm-assessment.tsx
    - src/dashboard/src/pages/cbom.tsx
    - src/dashboard/src/pages/roadmap.tsx
    - src/dashboard/src/pages/findings.tsx
    - src/dashboard/src/pages/identity.tsx
    - src/dashboard/src/pages/print.tsx
    - src/dashboard/src/hooks/useQRAMMSession.ts
    - src/dashboard/src/hooks/useScanData.ts
decisions:
  - "D-24 HMR-safe re-throw applied: console.error logs + /already/i message guard, not naive re-throw"
  - "D-25 empty useMemo deps confirmed: cells close only over row.original and module-level constants"
  - "D-27 firstNonZeroComp generic relaxed to <T> with runtime count probe — CbomComponent has no count field; falls through to comps[0], preserving pre-D-27 semantic exactly"
  - "D-28 createElement import removed entirely (was only used for the <style> tag)"
  - "D-29 URL hoisted out of try-block per RESEARCH Pitfall 8 — single source for both non-ok path and catch handler"
metrics:
  duration: "~15 min"
  completed: "2026-05-15"
  tasks_completed: 3
  files_created: 7
  files_modified: 8
---

# Phase 77 Plan 04: INFO-04 React Frontend INFOs Summary

Closed 7 React-frontend INFO-severity audit findings (react-frontend/IN-01..07) via RED→GREEN TDD with Vitest, satisfying the CONTEXT `npm run build` exit-0 gate and preserving every Phase 62 + Phase 76 invariant.

## What was built

### D-23 (IN-01) — qramm-assessment tab-count comment

`src/dashboard/src/pages/qramm-assessment.tsx:246` previously read `{/* 5-tab assessment layout */}` despite rendering 6 `<TabsTrigger>` elements at lines 248-254 (CVI, SGRM, DPE, ITR, Scorecard, Compliance Map). Rewrote to `{/* 6-tab assessment layout: CVI, SGRM, DPE, ITR, Scorecard, Compliance Map — closes react-frontend/IN-01 (D-23) */}`. Comment-only fix; zero behavior change.

### D-24 (IN-02) — Cytoscape registration is loud + HMR-safe

Both `cbom.tsx:19-23` (`coseBilkent`) and `roadmap.tsx:11-16` (`dagre`) previously swallowed all `cytoscape.use(...)` failures via bare `catch { /* already */ }`. Applied RESEARCH C-12 Pattern 8: log via `console.error` AND re-throw only when the error message does **not** match `/already/i`. This satisfies CONTEXT D-24 (log + re-throw) while preserving HMR safety — a naive unconditional re-throw would break vite hot-module-reload because the second registration legitimately throws "already registered."

### D-25 (IN-03) — Columns memoized for TanStack-table stability

`findings.tsx::columns` and `identity.tsx::columns` were declared as inline array literals inside the component body, generating a new reference on every render. Wrapped both in `useMemo<ColumnDef<FindingItem | IdentityFinding>[]>(() => [...], [])`. Empty deps are safe because all `cell` callbacks close only over `row.original` and module-level constants (`SEVERITY_STYLES`) — verified by grep + AST review. The `useMemo` import was already present in both files.

### D-26 (IN-04) — QRAMM `seededRef` resets on New Assessment

`useQRAMMSession.ts` exposed no way to clear `seededRef`, so after `handleNewAssessment` archived the current session and called `ctx.setSessionId(null)`, the next session load would short-circuit the seed-once gate (`if (seededRef.current !== latest.session_id)`) when the new session's id collided with the archived one (or in edge cases where the seed effect re-ran). Added `resetSession = useCallback(() => { seededRef.current = null }, [])`, exposed via the hook's return object and the `UseQRAMMSessionResult` interface. `qramm-assessment.tsx::handleNewAssessment` now destructures `resetSession` from `useQRAMMSession()` and invokes it after the archive succeeds (between `ctx.setScoreResult(null)` and `navigate("/qramm")`).

### D-27 (IN-05) — `firstNonZeroComp` representative selector

Added an exported `firstNonZeroComp<T>(comps: T[] | undefined): T | undefined` helper at the top of `cbom.tsx` that returns the first component whose `count` field is greater than 0, falling back to `comps[0]` when no element satisfies the predicate. Replaced both `compByAlg[d.label]?.[0]` (line 285) and `compByAlg[alg]?.[0]` (line 390) call sites with `firstNonZeroComp(...)`. Per Discretion D-27 (Researcher recommendation), the helper preserves the existing "any representative" semantic — and because `CbomComponent` has no `count` field today, every call falls through to `comps[0]`, matching pre-D-27 behavior bit-for-bit. The helper is future-proof for any caller passing a richer shape.

### D-28 (IN-06) — JSX `<style>` replaces `createElement`

`print.tsx` previously imported `createElement` from React solely to inject the print stylesheet via `{createElement("style", null, PRINT_CSS)}`. Replaced with standard JSX `<style>{PRINT_CSS}</style>` (RESEARCH Pattern 7) and removed `createElement` from the import (it had no other call sites). `PRINT_CSS` is a module-level concatenated string of static rules — no user content interpolation, so this is a pure idiomatic-style improvement with no security implication.

Phase 62 BR-05 cleanup at `print.tsx:333-336` (`document.body.removeAttribute('data-ready')` mount + cleanup) and Phase 76 D-03 sentinel guard at lines 347-353 were **NOT** touched — both still grep-verifiable in HEAD.

### D-29 (IN-07) — Fetch URL surfaced in error message

`useScanData.ts` previously constructed the fetch URL inside the `try` block, leaving the non-ok error path emitting only `API error: 500 Internal Server Error` with no indication of which endpoint failed. Per RESEARCH Pitfall 8, hoisted `const url = selectedScanId ? ... : "/api/scan/latest"` to the effect-callback scope so it is in lexical scope for both the non-ok branch (now `Failed to fetch ${url}: ${resp.status} ${resp.statusText}`) and the catch handler (now `Failed to fetch ${url}: ${err.message}`). Operators triaging a scan-load failure now see the literal endpoint that failed, including the `scan_id` query parameter when applicable.

The 401/403/404/429 typed-error paths were preserved unchanged — only the generic "API error" fallback was upgraded to include the URL.

## Tests

7 new Vitest modules; 20 new test cases.

| File | Cases | Strategy |
| ---- | ----- | -------- |
| `qramm-assessment-tab-comment.test.tsx` | 2 | Source-string assert (no `5-tab`; matches `/6[-\s]tab/i`) |
| `cbom-cytoscape-catch.test.tsx` | 4 | Source-string asserts for `console.error`, `/already/i`, `throw e` in both cbom.tsx and roadmap.tsx |
| `findings-columns-memo.test.tsx` | 2 | Source-string regex for `useMemo<ColumnDef<...>[]>` |
| `useQRAMMSession-reset.test.ts` | 3 | Source-string asserts on hook (resetSession defined, returned, sets ref to null) AND caller (qramm-assessment wires it in) |
| `cbom-compByAlg-statistic.test.tsx` | 5 | Direct unit tests on imported `firstNonZeroComp` (first-non-zero, fallback to [0], undefined, empty, single) |
| `print-no-createElement.test.tsx` | 3 | Source-string: no `createElement("style"`, has `<style>{PRINT_CSS}</style>`, BR-05 cleanup still grep-visible |
| `useScanData-error-url.test.ts` | 1 | MSW 500 response → assert `error` matches `/Failed to fetch/`, `/scan-xyz-123/`, `/\/api\/scan\/latest/` |

**Test gates:**

- `cd src/dashboard && npm test -- --run` — 18 files, 70 tests, all green
- `cd src/dashboard && npm run build` — exits 0 (CONTEXT test_strategy gate satisfied)
- Phase 76 carry-over (`useScanList`, `executive-error-coercion`, `print-pdf-cleanup`, `qramm-profile-submit-error`) — all still green

## Decisions Made

1. **D-25 useMemo deps were empty** — every cell callback in findings.tsx and identity.tsx closes only over `row.original` (function parameter) and module-level constants (`SEVERITY_STYLES`). No external state is referenced, so `[]` is correct.
2. **D-27 generic signature relaxed** — the plan's draft `<T extends { count: number }>` failed tsc against `CbomComponent[]` (no count field). Relaxed to `<T>` with a runtime `(c as { count?: number }).count` probe inside the find predicate. Falls through to `comps[0]` for shapes without `count`, preserving the existing semantic.
3. **D-24 HMR-safety preference over loud failure** — CONTEXT D-24 says "log + re-throw," but RESEARCH C-12 / Pitfall warns that naive re-throw breaks vite HMR (cytoscape.use legitimately throws `"already registered"` on every hot reload). Applied Pattern 8 (`/already/i` message guard) to honor BOTH: loud on genuine failures, silent on HMR re-registration.
4. **D-28 createElement import removed** — `createElement` had only the one use site, so the import was deleted entirely rather than left dangling.

## Deviations from Plan

### Rule 1 — Bug: `firstNonZeroComp` generic signature

**Found during:** Task 3 (`npm run build` gate)
**Issue:** Plan-specified signature `<T extends { count: number }>` raised TS2345 because `CbomComponent` has no `count` field — all 6 use sites in cbom.tsx (the helper's call sites + downstream property reads on its result) failed type-checking.
**Fix:** Relaxed to `<T>(comps: T[] | undefined): T | undefined` with a runtime probe `(c as { count?: number }).count` inside the find predicate. Behavior on `CbomComponent[]`: falls through to `comps[0]` (no element has a count), matching pre-D-27 semantic exactly.
**Files modified:** src/dashboard/src/pages/cbom.tsx
**Commit:** consolidated into b76e164 / 874a4e4 (see "Parallel-agent commit attribution" below)

### Parallel-agent commit attribution

Plans 77-01, 77-02, 77-03, 77-04 ran in parallel against the same working tree. When I attempted to commit the D-27 generic-signature fix in a separate Task 3 commit, parallel-agent `git add`/`git reset` interleavings caused the cbom.tsx delta to be staged by a sibling agent first. The cbom.tsx D-27 fix landed in commit **874a4e4 `feat(77-02)`** instead of a dedicated 77-04 fix commit. The fix content is functionally correct and present in HEAD; only the commit attribution is non-ideal. No work was lost.

The plan acceptance criterion `grep -c "firstNonZeroComp" cbom.tsx >= 5` expected 1 def + 4 call sites; the actual code has 1 def + 2 call sites (only 2 `compByAlg[X]?.[0]` instances existed at HEAD cf2417a — lines 148 and 317 cited in the plan are the useMemo definition and its deps array, not call sites). Final count: 3 occurrences. This is a plan inventory error; the substantive fix is complete.

### Audit rows NOT flipped

Per plan, **no** audit-row flips were made in AUDIT-TASKS.md for IN-01..07. PLAN 77-05 consolidates all INFO-01..04 audit-row flips.

## Phase 62 + Phase 76 invariants preserved

- `print.tsx:333-336` BR-05 cleanup effect (Phase 62) — untouched; grep-verifiable
- `print.tsx:347-353` D-03 (WR-07) sentinel guard (Phase 76) — untouched; grep-verifiable
- Phase 76 test modules (`print-pdf-cleanup`, `executive-error-coercion`, `qramm-profile-submit-error`, `useScanData`) — all still pass

## D-32 do-not-touch honored

- No new npm dependencies (`git diff src/dashboard/package.json` shows zero dependency changes)
- No QRAMM-120-question taxonomy edits
- No Recharts component swaps
- No CLI flag changes
- No schema migrations

## Commits

- `5c6f204` test(77-04): add failing Vitest modules for INFO-04 (D-23..D-29) — per RESEARCH C-12 HMR-safe re-throw
- `b76e164` feat(77-04): close INFO-04 (D-23..D-29) — React frontend INFOs; RESEARCH C-12 HMR-safe re-throw applied
- `874a4e4` feat(77-02) — picked up the D-27 generic-relaxation patch due to parallel-agent staging interleave (functionally a 77-04 fix; see Deviations)

## Self-Check: PASSED

- All 7 test files exist (verified via Read)
- All 8 production source files edited (verified via grep for closes-citations and signature changes)
- `cd src/dashboard && npm run build` exits 0
- `cd src/dashboard && npm test -- --run` — 70/70 pass
- Commits `5c6f204` and `b76e164` exist in `git log`
- Phase 62 + Phase 76 invariants intact
- Zero audit-row flips made (deferred to PLAN 77-05 per plan)
