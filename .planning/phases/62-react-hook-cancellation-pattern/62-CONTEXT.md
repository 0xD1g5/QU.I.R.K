# Phase 62: React Hook Cancellation Pattern - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 62 closes 6 audit blockers + 3 warnings that together constitute
"Pattern C — Cancellation guard inconsistency in React hooks":

- **BR-01:** `QRAMMProvider.persistDraft` captures a partial snapshot at
  debounce-schedule time; rapid multi-field edits drop earlier fields. Closes
  HOOK-02 (debounce coalescing).
- **BR-02:** Confirm-auto-fill flow never guarantees `confirmed_at` reaches the
  server before a crash/reload — `persistDraft` is debounced 300ms; the confirm
  action must bypass the debounce queue. Closes HOOK-03 (badge contract).
- **BR-03:** `useScanData` error-status branches (401/403/429/404) call
  `setError()` without `if (!cancelled)` guard. Closes HOOK-01.
- **BR-04:** `useScanData` does not clear stale data when `selectedScanId`
  changes; old scan's data is displayed during the next fetch. Closes HOOK-01.
- **BR-05:** `/print` page's `data-ready` sentinel is never removed on
  component unmount — stale `data-ready` persists across navigation. Closes
  HOOK-04.
- **BR-06:** System theme (`prefers-color-scheme`) is read once on mount; no
  `MediaQueryList` change listener wired up, so dark/light OS toggle is
  ignored while the app is running. Closes HOOK-04.
- **WR-01:** `useQRAMMSession` setError/setSession calls in error branches
  (401/403/429) lack `if (!cancelled)` guards. Opportunistic close with HOOK-01.
- **WR-03:** QRAMMProvider `debounceRef` timers are never cleared on provider
  unmount — memory leak. Opportunistic close with HOOK-03.
- **WR-14:** `handleNewAssessment` does not abort pending debounce timers
  before resetting session state — a timer that fires after reset writes to
  the new session. Opportunistic close with HOOK-03.

**In scope:** `src/dashboard/src/hooks/` (all hooks), `src/dashboard/src/context/QRAMMProvider.tsx`,
`src/dashboard/src/pages/print.tsx`, theme provider, ESLint config, new Vitest
+ MSW test files, AUDIT-TASKS.md row closures.

**Out of scope:** New backend routes, SQLite schema changes, `useScanList` error
handling (non-critical; WR-02 deferred), chart component optimizations (IN-03
deferred), `seededRef` reset on new assessment (IN-04 deferred).

</domain>

<decisions>
## Implementation Decisions

### D-01: Abstraction Level — In-Place Fixes, No New Hook Abstraction

Do NOT create a `useCancellableFetch` wrapper hook. The existing `let cancelled = false` / `return () => { cancelled = true }` pattern in every hook is correct and already established — the bugs are gaps in specific error-branch early-returns, not structural absence of the pattern. A wrapper hook would require refactoring all hooks to fit a common signature, which is risky for hooks with multi-step fetch chains (e.g., `useQRAMMSession` with its list → answers chain + seededRef).

Fix each hook in-place:
- Apply `if (!cancelled)` to EVERY `setState` / `setError` call, including early returns inside error branches (status 401/403/429/404/general). The pattern must be: no state setter fires after an async boundary without first checking `cancelled`.
- Do NOT use `AbortController` — the flag pattern is already sufficient and established in this codebase.

### D-02: Stale Data Clearing (BR-04)

At the **top of the `useEffect` callback** in `useScanData`, before the async `fetchData()` call, reset state synchronously:
```typescript
setData(null)
setLoading(true)
setError(null)
```
This ensures the UI never shows stale scan data from a previous `selectedScanId` while the new fetch is in flight. All three setters run synchronously (before any `await`), so no cancellation check is needed for these lines.

### D-03: QRAMM Debounce Coalescing Fix (BR-01)

Add `latestAnswersRef = useRef<Map<number, AnswerState>>(new Map())` to `QRAMMProvider`. Update this ref **synchronously** inside `setAnswer` (before calling `persistDraft`) by computing the full merged answer and writing it into the ref:

```typescript
const setAnswer = useCallback((questionNumber: number, state: Partial<AnswerState>) => {
  const existing = latestAnswersRef.current.get(questionNumber) ?? DEFAULT_ANSWER
  const merged: AnswerState = { ...existing, ...state }
  // Update ref synchronously — captures merged state before React batches the setState
  const nextMap = new Map(latestAnswersRef.current)
  nextMap.set(questionNumber, merged)
  latestAnswersRef.current = nextMap
  setAnswers(latestAnswersRef.current)
  persistDraft(questionNumber, merged)  // pass FULL merged answer, not just partial
}, [persistDraft])
```

Change `persistDraft` signature from `(qn: number, state: Partial<AnswerState>)` to `(qn: number, fullAnswer: AnswerState)`. The closure captures `fullAnswer` at schedule time — when the timer fires it sends `answer_value` + `evidence_note` from the full accumulated state, not from the last-changed partial.

### D-04: confirmed_at Flush Strategy (BR-02)

Add `confirmAnswer(qn: number, value: 1 | 2 | 3 | 4)` to `QRAMMContext` interface and `QRAMMProvider` implementation. This method:
1. Cancels any pending debounce timer for `qn` (calls `clearTimeout(debounceRef.current.get(qn))` + deletes the entry)
2. Updates `latestAnswersRef` and calls `setAnswers` with the merged `{ answer_value: value, confirmed_at: new Date().toISOString() }`
3. Fires a **direct** `fetchApi("/api/qramm/assessment/draft", { method: "POST", ... })` immediately (no debounce), sending `answer_value: value`

The backend `/api/qramm/assessment/draft` already auto-sets `confirmed_at` when `answer_value` is received for a row that has `suggested_answer != null` (see `qramm.py:565`). So no backend changes are needed — the direct fetch is sufficient to guarantee persistence.

`handleConfirm` in `qramm-assessment.tsx` changes from calling `ctx.setAnswer(qn, { answer_value: ..., confirmed_at: ... })` to calling `ctx.confirmAnswer(qn, pendingValue)`.

### D-05: Provider Unmount Cleanup (WR-03) and New Assessment Abort (WR-14)

Add a cleanup `useEffect` to `QRAMMProvider` that clears all pending timers on unmount:
```typescript
useEffect(() => {
  return () => { debounceRef.current.forEach(t => clearTimeout(t)) }
}, [])
```

For WR-14: before `handleNewAssessment` resets context state, call a `clearPendingDebounces()` helper (or expose `debounceRef.current.forEach(clearTimeout)` via context) to abort any in-flight debounce timers that would write to the about-to-be-deleted session.

### D-06: Print Sentinel (BR-05)

Add a mount/unmount effect in `print.tsx` that removes `data-ready` on mount (to clear any stale sentinel from a previous render cycle) and on unmount:
```typescript
useEffect(() => {
  document.body.removeAttribute('data-ready')
  return () => { document.body.removeAttribute('data-ready') }
}, [])
```
This runs once on mount/unmount (empty dep array). The existing data-set effect (with `[data, loading, qrammLoading]` deps) is unchanged — it still sets the attribute when data is ready. The combined behavior: stale sentinel cleared on mount, set when both hooks resolve, removed on unmount.

### D-07: Reactive System Theme (BR-06)

In the theme provider (wherever `prefers-color-scheme` is read), wire a `MediaQueryList` change listener:
```typescript
const mql = window.matchMedia('(prefers-color-scheme: dark)')
const handler = (e: MediaQueryListEvent) => { /* update theme state */ }
mql.addEventListener('change', handler)
return () => mql.removeEventListener('change', handler)
```
This must be inside a `useEffect` so it registers once on mount and cleans up on unmount.

### D-08: Test Tooling — Vitest + MSW

Install Vitest + `@testing-library/react` + MSW into `src/dashboard/` as dev deps. Do NOT install Playwright — the success criteria test hook state transitions (stale data, POST count), not visual rendering. Playwright adds a full browser + bundle requirement; Vitest + MSW tests hooks directly with `renderHook`.

Test file locations: `src/dashboard/src/hooks/__tests__/` for hook tests, `src/dashboard/src/context/__tests__/` for provider tests.

Two critical tests (matching HOOK-01 + HOOK-02 success criteria):
1. **Scan-switch stale-data test (HOOK-01):** Use `renderHook` with a mock `ScanContext`. Rapidly switch `selectedScanId` twice; assert that after both fetches resolve, the displayed `data.scan_id` matches the last-selected ID, not the first. MSW returns distinct payloads per scan ID.
2. **Debounce coalescing test (HOOK-02):** Render `QRAMMProvider`. Call `setAnswer(qn, {answer_value: 1})` 20 times in rapid succession (within a single fake-timer window). Use MSW request recorder. After advancing fake timers by 300ms, assert exactly 1 POST to `/api/qramm/assessment/draft`. Use `vi.useFakeTimers()`.

### D-09: ESLint Guard Rule (HOOK-04)

Add a CI shell-script check (not a custom ESLint plugin rule — authoring an ESLint AST rule that reliably detects async-without-cancelled-guard is complex and error-prone). The CI check:
```bash
# Fail if any hook file contains `setError(` or `setState(` after an `await`
# outside of an `if (!cancelled)` block — heuristic check, grep-based
```
Implementation: a small `scripts/check-cancelled-guards.sh` that greps `src/dashboard/src/hooks/` for the pattern. Wire it into `package.json` `lint` script and into CI alongside the existing ESLint run.

Alternatively: add `// eslint-disable-line` comments as explicit in-code acknowledgment that a state setter is intentionally unguarded (for any legitimate cases). This documents intent and makes the grep check's false-positives explicit.

### D-10: Audit Ledger Updates

After phase completion, flip these rows to `[x] closed` in `.planning/audit-2026-05-08/AUDIT-TASKS.md`:
- `react-frontend/BR-01` through `react-frontend/BR-06`
- `react-frontend/WR-01`, `WR-03`, `WR-14`
Also update REQUIREMENTS.md: HOOK-01 through HOOK-04 → `[x]`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### React Hooks (primary targets)
- `src/dashboard/src/hooks/useScanData.ts` — BR-03, BR-04 target; cancellation gaps in error branches + stale data on scan switch
- `src/dashboard/src/hooks/useQRAMMSession.ts` — WR-01 target; error branches unguarded; complex multi-step fetch chain (list → answers) + seededRef
- `src/dashboard/src/hooks/useTrendsData.ts` — already largely correct; review for consistency
- `src/dashboard/src/hooks/useScanList.ts` — WR-02 (non-OK responses silently swallowed); low-priority warning, opportunistic fix
- `src/dashboard/src/hooks/useQRAMMPrintData.ts` — review cancellation consistency in parallel `Promise.all` branch

### QRAMM Provider + Context
- `src/dashboard/src/context/QRAMMProvider.tsx` — BR-01, WR-03, WR-14 target; `persistDraft`, `debounceRef`, `setAnswer`
- `src/dashboard/src/context/QRAMMContext.tsx` — interface definitions; must add `confirmAnswer` method signature

### QRAMM Assessment Page
- `src/dashboard/src/pages/qramm-assessment.tsx` — `handleConfirm` (line 152), `handleNewAssessment`; both change in this phase

### Print Page
- `src/dashboard/src/pages/print.tsx` — BR-05 target; `data-ready` sentinel (lines 334–340)

### Theme Provider
- Find and read the theme provider file (`grep -r "prefers-color-scheme" src/dashboard/src/`) — BR-06 target; location TBD before planning

### Backend (read-only — no changes needed)
- `quirk/dashboard/api/routes/qramm.py` §`draft_answer` (line 532) — confirms that backend auto-sets `confirmed_at` when `answer_value` arrives for a row with `suggested_answer`; `DraftAnswerRequest` model (line 136) — shows `confirmed_at: Optional[str]` is already in the schema (available if needed)

### ESLint Config
- `src/dashboard/eslint.config.js` — flat config, ESLint 9; extend with the CI guard script path reference

### Audit + Requirements
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — react-frontend section, BR-01..BR-06, WR-01, WR-03, WR-14, Pattern C description
- `.planning/REQUIREMENTS.md` — HOOK-01, HOOK-02, HOOK-03, HOOK-04 definitions
- `.planning/ROADMAP.md` §Phase 62 — success criteria 1 and 2 are the acceptance gates

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `let cancelled = false; ... return () => { cancelled = true }` — already the established cancellation pattern in every hook; extend it, do not replace it
- `fetchApi()` in `src/dashboard/src/lib/api.ts` — Phase 58 CSRF/auth wrapper; all hook fetches must use this, not `fetch()` directly
- `debounceRef = useRef<Map<number, ReturnType<typeof setTimeout>>>` — per-question debounce map in QRAMMProvider; already set up correctly, just needs the field-drop fix and unmount cleanup
- `sessionIdRef = useRef<number | null>(null)` — already in `useQRAMMSession` as a stable session ID ref; same pattern for `latestAnswersRef` in QRAMMProvider

### Established Patterns
- Every hook's `useEffect` has the `cancelled` flag + cleanup return — this is the invariant to enforce, not replace
- `QRAMMContext` is typed with an explicit interface in `QRAMMContext.tsx`; add `confirmAnswer` there, not just in the provider
- `DEFAULT_ANSWER` constant exists in `PracticeAreaSection.tsx`; the same shape should be used when initializing the `latestAnswersRef` map entries in `QRAMMProvider`
- `fetchApi()` returns a `Response` — check `resp.ok` before reading body; never call `resp.json()` on error responses (consistent pattern across all existing hooks)

### Integration Points
- `ScanContext` (provides `selectedScanId`) — the dep array of `useScanData`'s `useEffect` already depends on `selectedScanId`; the stale-data fix (`setData(null)` on effect entry) plugs into this naturally
- `QRAMMContext.Provider` wraps the assessment page; adding `confirmAnswer` to the context value is the only interface change propagated to consumers
- `print.tsx` imports both `useScanData` and `useQRAMMPrintData` — the mount-cleanup effect for `data-ready` is independent of both; add it as a third `useEffect` in `PrintPage`
- ESLint `package.json` `"lint"` script — the CI guard script should be a separate `"lint:hooks"` script, both called from the CI pipeline

</code_context>

<specifics>
## Specific Ideas

- The `confirmAnswer` method in the provider should cancel the pending debounce for that `qn` BEFORE firing the direct fetch, to prevent a race where a queued debounce fires after `confirmAnswer` and overwrites the server state with an older `answer_value` (if the debounce was scheduled before the user clicked Confirm).
- For the debounce coalescing test, use `vi.useFakeTimers()` — Vitest's fake timer API — rather than real timeouts. The test advances time by 300ms after firing all 20 `setAnswer` calls, then counts MSW-recorded requests.
- `useQRAMMSession`'s `seededRef` is a `useRef<number | null>(null)` that tracks the session_id that has been seeded — this is intentionally NOT reset on re-renders, only on new session loads. Do NOT change its behavior; only add cancellation guards to error branches.
- The `latestAnswersRef` in QRAMMProvider must be initialized to `new Map()` (matching the initial `answers` state). The ref update in `setAnswer` must happen before `setAnswers` to avoid a render where the ref is stale relative to React state.
- For the grep-based CI guard: scope it to `src/dashboard/src/hooks/` only (the context provider uses debounce, not the standard `cancelled` pattern, so a different check applies there).

</specifics>

<deferred>
## Deferred Ideas

- **`AbortController` for actual network cancellation:** Would abort in-flight requests rather than just ignoring their results. Bigger change — requires passing an `AbortSignal` through `fetchApi()`. Deferred to a future hardening phase; the flag pattern is sufficient for the current bugs.
- **`useScanList` error handling (WR-02):** Silently swallows non-OK responses — low-severity warning. Opportunistic fix acceptable but not required for HOOK-01..04 closure.
- **`seededRef` reset on new assessment flow (IN-04):** After `handleNewAssessment` resets `ctx.resetAnswers`, the `seededRef` in `useQRAMMSession` still holds the old session_id, meaning a new session's answers won't be seeded on next load. Separate bug; deferred — the fix requires coordinating seededRef reset with the new session load.
- **Custom ESLint plugin rule:** A full AST-aware rule that flags async-setState-without-cancelled-guard would be more precise than the grep check. Deferred — the grep check covers the immediate regression risk; a proper rule can be added as a developer-experience improvement.
- **Playwright integration tests:** If Vitest + MSW proves insufficient for E2E confidence on hook behavior, Playwright can be added in a future phase targeting dashboard E2E coverage.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 62-react-hook-cancellation-pattern*
*Context gathered: 2026-05-10*
