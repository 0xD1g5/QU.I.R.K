# Phase 62: React Hook Cancellation Pattern — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 11 new/modified files
**Analogs found:** 9 / 11 (2 new files with no codebase analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/dashboard/src/hooks/useScanData.ts` | hook | request-response | `src/dashboard/src/hooks/useTrendsData.ts` | exact — same shape, correct guard pattern |
| `src/dashboard/src/hooks/useQRAMMSession.ts` | hook | request-response (chained) | `src/dashboard/src/hooks/useScanData.ts` | role-match — same structure, same gaps |
| `src/dashboard/src/hooks/useTrendsData.ts` | hook | request-response | self (reference / correct model) | reference — already correct |
| `src/dashboard/src/hooks/useScanList.ts` | hook | request-response | `src/dashboard/src/hooks/useTrendsData.ts` | role-match |
| `src/dashboard/src/hooks/useQRAMMPrintData.ts` | hook | request-response (parallel) | `src/dashboard/src/hooks/useTrendsData.ts` | role-match — already largely correct |
| `src/dashboard/src/context/QRAMMProvider.tsx` | context-provider | event-driven (debounce) | self (modify in place) | — |
| `src/dashboard/src/context/QRAMMContext.tsx` | context-interface | — | self (modify in place) | — |
| `src/dashboard/src/pages/qramm-assessment.tsx` | page-component | request-response | self (modify in place) | — |
| `src/dashboard/src/pages/print.tsx` | page-component | request-response | self (modify in place) | — |
| `src/dashboard/src/components/theme-provider.tsx` | component/provider | event-driven (MQL) | no analog — first MQL listener in codebase | no analog |
| `src/dashboard/eslint.config.js` | config | — | self (extend) | — |
| `scripts/check-cancelled-guards.sh` | script (new) | — | no analog — new file | no analog |
| `src/dashboard/src/hooks/__tests__/useScanData.test.ts` | test | — | no codebase hook tests yet | no analog |
| `src/dashboard/src/context/__tests__/QRAMMProvider.test.tsx` | test | — | no codebase context tests yet | no analog |

---

## Pattern Assignments

### `src/dashboard/src/hooks/useScanData.ts` (hook, request-response)

**Bugs:** BR-03 (unguarded error-branch setters) + BR-04 (stale data on scan switch)

**Analog:** `src/dashboard/src/hooks/useTrendsData.ts` — this file has the CORRECT cancellation pattern;
`useScanData` must be brought into conformance with it.

**The correct cancellation pattern** (`useTrendsData.ts` lines 17–62):
```typescript
useEffect(() => {
  let cancelled = false

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const resp = await fetchApi("/api/trends")
      if (!resp.ok) {
        if (!cancelled) {          // <-- guard wraps ALL error branches
          if (resp.status === 401) {
            setError("Authentication required")
            return
          }
          if (resp.status === 403) {
            setError("Request blocked")
            return
          }
          if (resp.status === 429) {
            const retryAfter = resp.headers.get("Retry-After") ?? "60"
            setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
            return
          }
          setError(`API error: ${resp.status} ${resp.statusText}`)
        }
        return
      }
      const json: TrendReport = await resp.json()
      if (!cancelled) {
        setData(json)
      }
    } catch (err) {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : "Failed to load trend data")
      }
    } finally {
      if (!cancelled) {
        setLoading(false)
      }
    }
  }

  fetchData()
  return () => {
    cancelled = true
  }
}, [])
```

**Current bug in `useScanData.ts`** (lines 30–48) — error branches fire setters without checking `cancelled`:
```typescript
// BUGGY — no !cancelled check on any of these early-return branches:
if (resp.status === 401) {
  setError("Authentication required")   // BR-03: unguarded
  return
}
if (resp.status === 403) {
  setError("Request blocked")           // BR-03: unguarded
  return
}
if (resp.status === 429) {
  const retryAfter = resp.headers.get("Retry-After") ?? "60"
  setError(`Too many requests. ...`)    // BR-03: unguarded
  return
}
if (resp.status === 404) {
  setError("No scan data available...")  // BR-03: unguarded
} else {
  setError(`API error: ...`)             // BR-03: unguarded
}
return
```

**Fix pattern — stale data clear (D-02, BR-04):** Add synchronously at the top of the `useEffect`
callback, BEFORE the `fetchData()` call (no `!cancelled` guard needed — these run before any await):
```typescript
useEffect(() => {
  let cancelled = false
  // BR-04: clear stale data synchronously before initiating the new fetch
  setData(null)
  setLoading(true)
  setError(null)

  async function fetchData() {
    // ... (setLoading/setError at top of fetchData can be removed or kept idempotent)
  }
  fetchData()
  return () => { cancelled = true }
}, [selectedScanId])
```

**Fix pattern — error branch guards (D-01, BR-03):** Wrap the entire `!resp.ok` block in `if (!cancelled)`,
matching `useTrendsData.ts` lines 25–42 exactly.

---

### `src/dashboard/src/hooks/useQRAMMSession.ts` (hook, request-response chained)

**Bug:** WR-01 — error branches in BOTH the list fetch (lines 31–45) and the answers fetch (lines 64–78)
fire `setError` / `setSession` / `ctx.setSessionId` without `if (!cancelled)`.

**Analog:** `src/dashboard/src/hooks/useTrendsData.ts` (single-fetch, correct guard model).
Also compare `useScanData.ts` which has the same structure of bugs.

**Current bug — list fetch error branches** (`useQRAMMSession.ts` lines 31–45):
```typescript
if (!listResp.ok) {
  if (listResp.status === 401) {
    setError("Authentication required")   // WR-01: unguarded
    return
  }
  if (listResp.status === 403) {
    setError("Request blocked")           // WR-01: unguarded
    return
  }
  if (listResp.status === 429) {
    const retryAfter = listResp.headers.get("Retry-After") ?? "60"
    setError(`Too many requests. ...`)    // WR-01: unguarded
    return
  }
  setError(`API error: ${listResp.status} ${listResp.statusText}`)  // WR-01: unguarded
  return
}
```

**Current bug — zero-sessions branch** (lines 50–54): also unguarded:
```typescript
if (list.length === 0) {
  setSession(null)          // unguarded
  ctx.setSessionId(null)    // unguarded
  return
}
const latest = list[0]
setSession(latest)          // unguarded (line 57)
ctx.setSessionId(...)       // unguarded (line 58)
```

**Current bug — answers fetch error branches** (lines 63–78): same pattern, all unguarded.

**Fix pattern:** Wrap the entire `!listResp.ok` block in `if (!cancelled)`. For the positive branches
after `await listResp.json()`, check `if (cancelled) return` (already done on line 48 — maintain this).
For the zero-session branch and `setSession`/`ctx.setSessionId` calls, wrap in `if (!cancelled)`.
Same treatment for the answers fetch error branches.

**Important:** Do NOT change `seededRef` behavior — it is intentionally not reset on re-renders
(lines 61–93). Only add `!cancelled` guards to state/context setter calls in error branches.

**fetchApi return type** (`src/dashboard/src/lib/api.ts` lines 44–73):
```typescript
export async function fetchApi(
  path: string,
  options: RequestInit = {}
): Promise<Response>
// Returns native Response — check resp.ok before resp.json()
// Never call resp.json() on error responses
```

---

### `src/dashboard/src/hooks/useTrendsData.ts` (hook, request-response) — REFERENCE MODEL

**Status:** Already correct. This file IS the canonical pattern. No changes needed unless a
consistency audit reveals a gap.

**Why it is correct:** The `if (!cancelled)` block at line 25 wraps all error-status branches AND
the success path. The `catch` block checks `!cancelled`. The `finally` block checks `!cancelled`.
The cleanup return sets `cancelled = true`. This is the complete invariant.

---

### `src/dashboard/src/hooks/useScanList.ts` (hook, request-response)

**Bug (WR-02, low priority):** Non-OK responses are silently swallowed — the `if (resp.ok)` guard
means 401/403/429/404 responses are ignored and `loading` is never set to `false` in the error path
(actually `finally` does clear it — but no error state is surfaced to the UI).

**Current pattern** (`useScanList.ts` lines 14–31):
```typescript
useEffect(() => {
  let cancelled = false
  async function fetchSessions() {
    try {
      const resp = await fetchApi("/api/scans")
      if (resp.ok) {
        const data: ScanSession[] = await resp.json()
        if (!cancelled) setSessions(data)
      }
      // WR-02: non-ok responses reach here silently — no error state set
    } finally {
      if (!cancelled) setLoading(false)
    }
  }
  fetchSessions()
  return () => { cancelled = true }
}, [])
```

**Note:** The `cancelled` guard on `setSessions` and `setLoading` is already correct. The fix
(if opportunistic) is to add an `error` state and surface it for non-ok responses, following
`useTrendsData.ts` structure. However, `UseScanListResult` interface has no `error` field —
adding it is a public API change. The interface must be updated in tandem.

---

### `src/dashboard/src/hooks/useQRAMMPrintData.ts` (hook, request-response parallel)

**Status:** Already largely correct. Review findings:
- Lines 32–49: `!listResp.ok` block is wrapped in `if (!cancelled)` — correct.
- Line 51: `if (cancelled) return` after `await listResp.json()` — correct.
- Lines 57–60: `setScoreResult(null) / setComplianceRows(null)` inside `if (!cancelled)` — correct.
- Lines 70–87, 90–104: both `!scoreResp.ok` and `!mapResp.ok` blocks wrapped in `if (!cancelled)` — correct.
- Lines 110–113: success setters inside `if (!cancelled)` — correct.
- Lines 115–116, 119–121: catch and finally blocks guarded — correct.

**No changes required.** This file already conforms to the `useTrendsData.ts` model.

---

### `src/dashboard/src/context/QRAMMProvider.tsx` (context-provider, event-driven/debounce)

**Bugs:** BR-01 (debounce coalescing drops fields), WR-03 (timers not cleared on unmount),
WR-14 (new assessment doesn't abort pending timers).

**Current `persistDraft` implementation** (lines 17–41) — two problems:
```typescript
const persistDraft = useCallback((qn: number, state: Partial<AnswerState>) => {
  const sid = sessionIdRef.current
  if (sid == null) return
  const existing = debounceRef.current.get(qn)
  if (existing) clearTimeout(existing)
  const timer = setTimeout(async () => {
    debounceRef.current.delete(qn)
    try {
      await fetch("/api/qramm/assessment/draft", {   // BUG: uses fetch() not fetchApi()
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          question_number: qn,
          ...("answer_value" in state && { answer_value: state.answer_value ?? null }),
          ...("evidence_note" in state && { evidence_note: state.evidence_note ?? null }),
          // BR-01: `state` is the partial from the LAST setAnswer call —
          // if two fields were set in separate calls before the timer fires,
          // only the second call's fields are sent (earlier fields are lost).
        }),
      })
    } catch { /* silent */ }
  }, 300)
  debounceRef.current.set(qn, timer)
}, [])
```

**Current `setAnswer` implementation** (lines 43–57):
```typescript
const setAnswer = useCallback((questionNumber: number, state: Partial<AnswerState>) => {
  setAnswers(prev => {
    const next = new Map(prev)
    const existing = next.get(questionNumber) ?? {
      answer_value: null, suggested_answer: null, confirmed_at: null, evidence_note: "",
    }
    const merged: AnswerState = { ...existing, ...state }
    next.set(questionNumber, merged)
    return next
  })
  persistDraft(questionNumber, state)  // BR-01: passes `state` (partial), not `merged`
}, [persistDraft])
```

**Fix pattern — `latestAnswersRef` and debounce coalescing (D-03, BR-01):**

Add ref declaration (after existing `sessionIdRef`):
```typescript
const latestAnswersRef = useRef<Map<number, AnswerState>>(new Map())
```

Change `setAnswer` to compute merged answer synchronously and pass the FULL answer to `persistDraft`:
```typescript
const setAnswer = useCallback((questionNumber: number, state: Partial<AnswerState>) => {
  const existing = latestAnswersRef.current.get(questionNumber) ?? DEFAULT_ANSWER
  const merged: AnswerState = { ...existing, ...state }
  // Update ref synchronously — before React batches the setState
  const nextMap = new Map(latestAnswersRef.current)
  nextMap.set(questionNumber, merged)
  latestAnswersRef.current = nextMap
  setAnswers(latestAnswersRef.current)
  persistDraft(questionNumber, merged)   // pass FULL merged answer, not partial
}, [persistDraft])
```

Change `persistDraft` signature to accept `fullAnswer: AnswerState` (not `Partial<AnswerState>`).
Change the closure body to serialize `fullAnswer.answer_value` and `fullAnswer.evidence_note` directly.
Also change `fetch(` to `fetchApi(` (CSRF requirement).

**Fix pattern — `confirmAnswer` new method (D-04, BR-02):**
```typescript
const confirmAnswer = useCallback((qn: number, value: 1 | 2 | 3 | 4) => {
  // 1. Cancel any pending debounce timer for this question
  const pending = debounceRef.current.get(qn)
  if (pending) {
    clearTimeout(pending)
    debounceRef.current.delete(qn)
  }
  // 2. Merge confirmed state into ref and React state
  const existing = latestAnswersRef.current.get(qn) ?? DEFAULT_ANSWER
  const merged: AnswerState = { ...existing, answer_value: value, confirmed_at: new Date().toISOString() }
  const nextMap = new Map(latestAnswersRef.current)
  nextMap.set(qn, merged)
  latestAnswersRef.current = nextMap
  setAnswers(latestAnswersRef.current)
  // 3. Direct flush — no debounce
  const sid = sessionIdRef.current
  if (sid == null) return
  fetchApi("/api/qramm/assessment/draft", {
    method: "POST",
    body: JSON.stringify({ session_id: sid, question_number: qn, answer_value: value }),
  }).catch(() => {})
}, [])
```

**Fix pattern — unmount cleanup (D-05, WR-03):**
```typescript
useEffect(() => {
  return () => { debounceRef.current.forEach(t => clearTimeout(t)) }
}, [])
```

**`DEFAULT_ANSWER` constant source** (`src/dashboard/src/components/qramm/PracticeAreaSection.tsx` lines 25–30):
```typescript
const DEFAULT_ANSWER: AnswerState = {
  answer_value: null,
  suggested_answer: null,
  confirmed_at: null,
  evidence_note: "",
}
```
This constant must be imported or duplicated into `QRAMMProvider.tsx` for use in `setAnswer` and `confirmAnswer`.

**Context value spread** (line 64–69) must include `confirmAnswer` in the Provider value object.

---

### `src/dashboard/src/context/QRAMMContext.tsx` (context-interface)

**Bug:** `confirmAnswer` method missing from `QRAMMContextValue` interface and default context.

**Current interface** (lines 26–36):
```typescript
interface QRAMMContextValue {
  sessionId: number | null
  setSessionId: (id: number | null) => void
  answers: Map<number, AnswerState>
  setAnswer: (questionNumber: number, state: Partial<AnswerState>) => void
  resetAnswers: (next: Map<number, AnswerState>) => void
  profile: OrgProfile | null
  setProfile: (p: OrgProfile | null) => void
  scoreResult: ScoreResult | null
  setScoreResult: (r: ScoreResult | null) => void
}
```

**Fix:** Add `confirmAnswer` to the interface AND to the `createContext` default value:
```typescript
interface QRAMMContextValue {
  // ... existing fields ...
  confirmAnswer: (questionNumber: number, value: 1 | 2 | 3 | 4) => void
}

export const QRAMMContext = createContext<QRAMMContextValue>({
  // ... existing defaults ...
  confirmAnswer: () => {},
})
```

---

### `src/dashboard/src/pages/qramm-assessment.tsx` (page-component)

**Bug:** `handleConfirm` (line 152–157) calls `ctx.setAnswer` with a partial that includes
`confirmed_at` set optimistically on the client — this bypasses the direct-flush contract of BR-02
and continues through the debounce queue.

**Current `handleConfirm`** (lines 152–157):
```typescript
function handleConfirm(qn: number, pendingValue: number) {
  ctx.setAnswer(qn, {
    answer_value: pendingValue as 1 | 2 | 3 | 4,
    confirmed_at: new Date().toISOString(),
  })
}
```

**Fix pattern (D-04):**
```typescript
function handleConfirm(qn: number, pendingValue: number) {
  ctx.confirmAnswer(qn, pendingValue as 1 | 2 | 3 | 4)
}
```

**`handleNewAssessment`** (lines 163–182) — current implementation does NOT clear debounce timers
before resetting context. The `ctx.resetAnswers(new Map())` call on line 173 can be followed by a
pending debounce timer writing to the new (empty) session.

**Fix pattern (D-05, WR-14):** Before resetting context state, call debounce clear. Since
`debounceRef` lives in `QRAMMProvider`, expose clearing via context or call `ctx.confirmAnswer`
is not the right hook here — the simplest approach is to expose a `clearPendingDebounces()` via
context, or document that `confirmAnswer` is a per-question clear. The phase plan should choose
to add `clearPendingDebounces: () => void` to `QRAMMContextValue` (same interface-change
pattern as `confirmAnswer`), called at the top of `handleNewAssessment`:
```typescript
async function handleNewAssessment() {
  if (!ctx.sessionId) return
  ctx.clearPendingDebounces()    // WR-14: abort timers before resetting state
  setArchiving(true)
  // ... rest unchanged ...
}
```

---

### `src/dashboard/src/pages/print.tsx` (page-component)

**Bug (BR-05):** The `data-ready` attribute is set on mount (lines 337–341) but never removed on
unmount. A stale `data-ready` on `document.body` persists across client-side navigation.

**Current sentinel effect** (lines 337–341):
```typescript
useEffect(() => {
  if (data && !loading && !qrammLoading) {
    document.body.setAttribute('data-ready', 'true')
  }
}, [data, loading, qrammLoading])
```

**Fix pattern (D-06):** Add a second `useEffect` with empty dep array — mount/unmount lifecycle only.
This runs BEFORE the data-ready effect on mount (effects run in order), clearing any stale sentinel:
```typescript
useEffect(() => {
  document.body.removeAttribute('data-ready')
  return () => { document.body.removeAttribute('data-ready') }
}, [])
```
The existing data-set effect is unchanged. Combined behavior: stale sentinel cleared on mount,
`data-ready` set when both hooks resolve, removed on unmount.

---

### `src/dashboard/src/components/theme-provider.tsx` (component/provider)

**Bug (BR-06):** `prefers-color-scheme` is read once per render inside a `useEffect` (lines 24–26).
There is no `MediaQueryList` change listener — OS dark/light toggle while app is running is ignored.

**Current implementation** (lines 21–32):
```typescript
useEffect(() => {
  const root = window.document.documentElement
  root.classList.remove("light", "dark")
  if (theme === "system") {
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light"
    root.classList.add(systemTheme)   // read once, no listener
  } else {
    root.classList.add(theme)
  }
}, [theme])
```

**Fix pattern (D-07):** Add a separate `useEffect` that wires the MQL listener only when
`theme === "system"`, with cleanup on unmount or when theme changes away from "system":
```typescript
useEffect(() => {
  if (theme !== "system") return
  const mql = window.matchMedia("(prefers-color-scheme: dark)")
  const handler = (e: MediaQueryListEvent) => {
    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    root.classList.add(e.matches ? "dark" : "light")
  }
  mql.addEventListener("change", handler)
  return () => mql.removeEventListener("change", handler)
}, [theme])
```

---

### `src/dashboard/eslint.config.js` (config)

**Current file** (lines 1–23): flat ESLint 9 config. No custom scripts referenced.

**Fix (D-09):** No changes to `eslint.config.js` itself. Instead, add a separate `"lint:hooks"` script
to `package.json` that calls `scripts/check-cancelled-guards.sh`. The CI pipeline calls both
`npm run lint` (ESLint) and `npm run lint:hooks` (shell guard check) independently.

**`package.json` scripts addition pattern** (existing `"lint"` script at `src/dashboard/package.json`):
```json
"lint": "eslint .",
"lint:hooks": "bash ../../scripts/check-cancelled-guards.sh"
```

---

### `scripts/check-cancelled-guards.sh` (new shell script — no codebase analog)

**Purpose (D-09):** Grep-based heuristic CI guard. Fails if any hook file contains `setError(` or
a state setter call after an `await` that is NOT inside an `if (!cancelled)` block.

**No analog exists** in the codebase. Pattern from RESEARCH.md / D-09 decision:
```bash
#!/usr/bin/env bash
# check-cancelled-guards.sh — Heuristic check: every setError/setState after an await
# in src/dashboard/src/hooks/ must be inside an !cancelled guard.
# Scope: hooks only (context provider uses debounce, different pattern).
set -euo pipefail
HOOKS_DIR="src/dashboard/src/hooks"
# ... grep logic ...
```

Implementation detail: the script should grep for `setError(` lines in hook files that are NOT
preceded by `if (!cancelled)` within the same error block. A pragmatic approach is to flag any
hook file where `setError(` appears WITHOUT a corresponding `if (!cancelled)` block present in
the file at all (file-level heuristic), then require `// eslint-disable-line` comments for any
legitimate unguarded cases as explicit in-code acknowledgment.

---

### Test Files (no codebase analog — new)

**`src/dashboard/src/hooks/__tests__/useScanData.test.ts`**
**`src/dashboard/src/context/__tests__/QRAMMProvider.test.tsx`**

No existing test files for hooks or context providers. Must be written from scratch.

**Required test tooling (D-08):** Vitest + `@testing-library/react` + MSW installed as devDeps in
`src/dashboard/`. Use `vi.useFakeTimers()` for debounce tests.

**Test 1 — Scan-switch stale-data (HOOK-01):**
```typescript
// useScanData.test.ts structure (D-08)
import { renderHook, waitFor } from "@testing-library/react"
import { useScanData } from "../useScanData"
// MSW: register handlers that return distinct payloads for scan_id=1 vs scan_id=2
// Act: render with scan_id=1, then switch to scan_id=2 before first fetch resolves
// Assert: final data.scan_id === 2, not 1
```

**Test 2 — Debounce coalescing (HOOK-02):**
```typescript
// QRAMMProvider.test.tsx structure (D-08)
import { renderHook, act } from "@testing-library/react"
import { QRAMMProvider } from "../QRAMMProvider"
// vi.useFakeTimers()
// Act: call ctx.setAnswer(1, {...}) 20 times in rapid succession
// vi.advanceTimersByTime(300)
// Assert: MSW recorded exactly 1 POST to /api/qramm/assessment/draft
```

---

## Shared Patterns

### Cancellation Guard (apply to ALL hooks)
**Source:** `src/dashboard/src/hooks/useTrendsData.ts` (complete correct implementation)
**Apply to:** `useScanData.ts` (error branches), `useQRAMMSession.ts` (both list and answers fetch error branches + zero-session branch)
**Pattern invariant:** Every `setState`/`setError`/`ctx.*` call that appears after any `await` must be guarded by `if (!cancelled)`. No exceptions. The `finally` block must also check `if (!cancelled)` before `setLoading(false)`.

### fetchApi Wrapper (apply to ALL network calls)
**Source:** `src/dashboard/src/lib/api.ts` lines 44–73
**Apply to:** `QRAMMProvider.persistDraft` (currently uses bare `fetch()`) and `QRAMMProvider.confirmAnswer` (new direct flush)
**Signature:** `fetchApi(path: string, options?: RequestInit): Promise<Response>`
**Rule:** Never call `fetch()` directly. All API calls must go through `fetchApi()` for CSRF + auth header injection.

### Error Response Handling (all hooks)
**Source:** `src/dashboard/src/hooks/useTrendsData.ts` lines 25–42
**Pattern:** Check `resp.ok` first. If not ok, wrap the entire error-status dispatch in `if (!cancelled)`. Never call `resp.json()` on error responses.

### Debounce Timer Pattern
**Source:** `src/dashboard/src/context/QRAMMProvider.tsx` lines 13, 17–41
**The ref:** `debounceRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())`
**Per-question keys** allow independent timers — do not use a single shared timeout.
**Clear on new timer:** `clearTimeout(existing)` before `setTimeout(...)` — already correct.
**Missing:** cleanup on unmount (`WR-03`) and abort before session reset (`WR-14`).

### Context Interface Extension Pattern
**Source:** `src/dashboard/src/context/QRAMMContext.tsx` lines 26–48
**Pattern:** Add new methods to both the `interface QRAMMContextValue` definition AND the `createContext(...)` default value object (with no-op implementations). This keeps TypeScript happy and prevents runtime errors when a consumer renders outside the provider.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/dashboard/src/components/theme-provider.tsx` (BR-06 addition) | component | event-driven (MQL) | No `MediaQueryList` change listener exists anywhere in the codebase |
| `scripts/check-cancelled-guards.sh` | script | — | No CI guard scripts exist in `scripts/`; directory is empty |
| `src/dashboard/src/hooks/__tests__/` | test | — | No hook test files exist in the codebase |
| `src/dashboard/src/context/__tests__/` | test | — | No context test files exist in the codebase |

---

## Metadata

**Analog search scope:** `src/dashboard/src/hooks/`, `src/dashboard/src/context/`, `src/dashboard/src/pages/`, `src/dashboard/src/components/`, `src/dashboard/src/lib/`, `scripts/`
**Files read:** 11 source files
**Pattern extraction date:** 2026-05-10
