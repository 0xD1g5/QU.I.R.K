---
phase: 62-react-hook-cancellation-pattern
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - scripts/check-cancelled-guards.sh
  - src/dashboard/package.json
  - src/dashboard/src/components/theme-provider.tsx
  - src/dashboard/src/context/__tests__/QRAMMProvider.test.tsx
  - src/dashboard/src/context/QRAMMContext.tsx
  - src/dashboard/src/context/QRAMMProvider.tsx
  - src/dashboard/src/hooks/__tests__/useScanData.test.tsx
  - src/dashboard/src/hooks/useQRAMMSession.ts
  - src/dashboard/src/hooks/useScanData.ts
  - src/dashboard/src/hooks/useScanList.ts
  - src/dashboard/src/lib/api.ts
  - src/dashboard/src/pages/print.tsx
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/test-setup.ts
  - src/dashboard/vitest.config.ts
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 62: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

The React hook cancellation pattern is largely implemented correctly. Every `useEffect` that performs async work (`useScanData`, `useScanList`, `useQRAMMSession`, `useQRAMMPrintData`) correctly declares `let cancelled = false`, sets it in the cleanup return, and guards all post-`await` state setters behind `if (!cancelled)`. The pre-`await` setters (`setLoading(true)`, `setError(null)`) are called synchronously before the first `await` in each hook, which is safe.

The debounce coalescing logic in `QRAMMProvider` is correct: each question gets an independent timer, `setAnswer` cancels-and-reschedules on every call for the same question, `confirmAnswer` performs a direct flush, and the unmount `useEffect` clears all pending timers.

`fetchApi` correctly injects CSRF and auth headers on every call and centralises token resolution. The auth token is never logged or reflected into error messages.

Four warnings and three info items require attention, detailed below.

## Warnings

### WR-01: `handleNewAssessment` calls `setArchiving(false)` on a potentially unmounted component

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:161-180`

**Issue:** `handleNewAssessment` is an async event handler. On the success path it calls `navigate("/qramm")` (line 175), which unmounts `AssessmentPage`. The `finally` block (line 179) then calls `setArchiving(false)` on the already-unmounted component. In React 19 this is a silent no-op, but it is the exact pattern the phase was introduced to eliminate. A future React version or strict-mode behaviour change could surface this as a warning or error.

```
167: const resp = await fetchApi(...)
...
173: navigate("/qramm")    // <-- unmounts this component
...
179: setArchiving(false)   // <-- setState after unmount
```

**Fix:** Introduce a `mountedRef` or move the `setArchiving(false)` call before `navigate()`. The simplest correct fix:

```tsx
async function handleNewAssessment() {
  if (!ctx.sessionId) return
  ctx.clearPendingDebounces()
  setArchiving(true)
  try {
    const resp = await fetchApi(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
    if (!resp.ok && resp.status !== 404) {
      setArchiving(false)   // reset before returning (component still mounted)
      return
    }
    ctx.setSessionId(null)
    ctx.resetAnswers(new Map())
    ctx.setProfile(null)
    ctx.setScoreResult(null)
    setArchiving(false)     // reset before navigate (component still mounted)
    navigate("/qramm")
  } catch {
    setArchiving(false)     // reset on error (component still mounted)
  }
  // no finally block needed
}
```

---

### WR-02: CI guard script setter allowlist misses project-specific state setters

**File:** `scripts/check-cancelled-guards.sh:44`

**Issue:** The CI guard's setter regex is:

```
\b(setError|setData|setLoading|setSession|setSessions)\(
```

This list does not include `setScoreResult`, `setComplianceRows`, `setQuestions`, or any other hook-specific setter that a future hook might introduce. A new hook that uses only unlisted setters (e.g. `setItems`, `setReportData`) and performs async work without cancellation guards would pass the CI check silently, defeating the entire purpose of the guard.

`useQRAMMPrintData` (already in the codebase) uses `setScoreResult` and `setComplianceRows` — these are not in the allowlist. The file currently also contains `setLoading` and `setError` (which ARE listed), so the guard accidentally catches it for the right reasons. Remove that lucky dependency.

**Fix:** Broaden the setter detection to any `set` + uppercase pattern, which matches all React `useState` destructured setters by convention:

```bash
# Replace line 44 with:
has_setter="$(printf '%s\n' "$stripped" | grep -cE '\bset[A-Z][a-zA-Z]+\(' || true)"
```

This matches the full project naming convention (`setScoreResult`, `setComplianceRows`, `setQuestions`, etc.) without requiring a manually maintained allowlist.

---

### WR-03: `fetchApi` silently drops caller headers when `HeadersInit` is `string[][]`

**File:** `src/dashboard/src/lib/api.ts:51-54`

**Issue:** `RequestInit.headers` is typed as `HeadersInit`, which is `Headers | string[][] | Record<string, string>`. `fetchApi` handles `Headers` (via `instanceof`) and `Record<string, string>` (via cast). If a caller passes `string[][]`, the cast on line 54 treats it as a plain object with numeric indices `{ "0": [...], "1": [...] }`, silently discarding all caller-supplied headers. The CSRF and auth headers are still injected, but the caller's intended headers are lost with no error.

No current call site uses `string[][]`, so this is not a live defect — but it is a correctness gap in the type contract the function advertises.

**Fix:** Add an explicit branch for the `string[][]` case before the cast:

```typescript
const existingHeaders: Record<string, string> =
  options.headers instanceof Headers
    ? Object.fromEntries(options.headers.entries())
    : Array.isArray(options.headers)
      ? Object.fromEntries(options.headers as string[][])
      : (options.headers as Record<string, string>) ?? {}
```

---

### WR-04: Vitest tests are not run in CI — cancellation regression is not enforced

**File:** `.github/workflows/dashboard-quality.yml` (no test step)

**Issue:** The `dashboard-quality.yml` CI workflow runs `build`, `lint` (which includes the shell guard script), and `a11y` checks — but it never runs `npm test`. The two regression tests added by this phase (`HOOK-01` in `useScanData.test.tsx` and `HOOK-02` in `QRAMMProvider.test.tsx`) are the primary evidence that the cancellation pattern works correctly. If those tests are never executed in CI, any regression that breaks the actual guard behavior (while preserving the text `if (!cancelled)` in the file) will ship undetected.

**Fix:** Add a test step to `dashboard-quality.yml` after the install step:

```yaml
- name: Run unit tests
  run: npm test
```

## Info

### IN-01: Misleading comment on cleanup `useEffect` in `QRAMMProvider`

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:117-118`

**Issue:** The comment reads: "Capture the ref value inside the effect so the cleanup function holds a stable reference to the Map at mount time". The phrase "at mount time" is misleading — `useRef` always returns the same object reference, so `timers === debounceRef.current` at all times. The comment implies the ref value could differ between mount and cleanup, which is not true. The behaviour is correct; the comment description is not.

**Fix:** Update the comment:

```tsx
// Hold a local alias for the Map so the linter doesn't warn about
// reading debounceRef.current inside the cleanup closure. The Map
// identity is stable for the lifetime of the provider.
const timers = debounceRef.current
```

---

### IN-02: CI guard script strips `eslint-disable-line` but not `eslint-disable-next-line`

**File:** `scripts/check-cancelled-guards.sh:34-35`

**Issue:** The script strips lines containing `eslint-disable-line` before scanning for setters. This allows an explicit in-code acknowledgment of intentional unguarded setters. However, if a developer uses `// eslint-disable-next-line` on the line above a setter (a common ESLint suppress pattern), the setter line itself is NOT stripped and would still be counted, causing a false positive. Conversely, if a developer uses `eslint-disable-line` on the line of a GUARD (`if (!cancelled)`) rather than the setter, the guard would be stripped, potentially causing a false negative.

The grep used to detect the guard (`grep -cE 'if \(!cancelled\)'`) operates on the stripped content, so stripping the guard line would cause a file to fail when it should pass.

**Fix:** Also strip lines whose immediately preceding line contains `eslint-disable-next-line`, or document the precise intended use of the `eslint-disable-line` escape hatch in the script header.

---

### IN-03: Debounce test uses `vi.useRealTimers()` inside `act()` without structured teardown risk

**File:** `src/dashboard/src/context/__tests__/QRAMMProvider.test.tsx:69-71`

**Issue:** The second `act()` block switches to real timers inside the Promise constructor:

```ts
await act(async () => {
  await new Promise((r) => { vi.useRealTimers(); setTimeout(r, 100) })
})
```

The `afterEach` hook also calls `vi.useRealTimers()`. Because the switch happens inside the test body rather than in `afterEach`, if `advanceTimersByTimeAsync(350)` throws or the act fails, `vi.useRealTimers()` inside the Promise would never be reached. Subsequent tests in the suite would then run with fake timers unexpectedly, causing spurious hangs or failures.

The `afterEach` guard does protect against this — it calls `vi.useRealTimers()` unconditionally — so the failure mode is limited to tests running in the same file after this one in a single failing run. There is only one test in this suite currently, so the practical risk is zero. However, as the suite grows the fragility increases.

**Fix:** Move the `vi.useRealTimers()` call to a dedicated `afterEach` position (which already exists) and restructure the wait:

```ts
// In afterEach (already present) — no change needed; vi.useRealTimers() is there.

// Replace the inner act block with:
await act(async () => {
  await vi.advanceTimersByTimeAsync(350)
})
// Switch to real timers for the MSW flush
vi.useRealTimers()
await new Promise((r) => setTimeout(r, 100))
```

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
