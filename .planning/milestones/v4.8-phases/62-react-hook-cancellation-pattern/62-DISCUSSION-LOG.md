# Phase 62: React Hook Cancellation Pattern - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 62-react-hook-cancellation-pattern
**Areas discussed:** useCancellableFetch abstraction, QRAMM debounce field-drop fix, confirmed_at flush strategy, Test validation approach

---

## useCancellableFetch Abstraction

| Option | Description | Selected |
|--------|-------------|----------|
| Shared hook abstraction | Create `useCancellableFetch` wrapper hook all hooks use | |
| In-place fixes + consistent application | Fix specific gaps in each hook's error branches; no new abstraction | ✓ |
| AbortController everywhere | Replace flag pattern with AbortController for true network cancellation | |

**User's choice:** Claude discretion — user asked Claude to proceed with recommended actions
**Notes:** Most hooks already have `let cancelled = false` patterns. The bugs are gaps in error-branch early-returns (401/403/429/404 calling `setError()` without `if (!cancelled)`), not structural absence of the pattern. A wrapper hook would require refactoring all hooks to fit a common signature — risky for `useQRAMMSession` with its multi-step fetch chain + seededRef. AbortController deferred as a future improvement.

---

## QRAMM Debounce Field-Drop Fix (BR-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Answers-map ref | Add `latestAnswersRef` in provider; update synchronously in `setAnswer`; `persistDraft` reads full answer from ref at fire time | ✓ |
| Full-state passthrough | Pass full merged answer to `persistDraft` instead of partial | ✓ (same approach) |
| Per-field accumulator | Track pending field writes in a separate ref Map, merge at fire time | |

**User's choice:** Claude discretion
**Notes:** The root cause is that `persistDraft` captures `Partial<AnswerState>` at debounce-schedule time. Rapid edits cancel+reschedule the timer, and each new closure only holds the most-recent partial. The fix: `setAnswer` computes the full merged answer and passes it to `persistDraft` (which accepts `AnswerState`, not `Partial<AnswerState>`). A `latestAnswersRef` enables this since React state updates are async and the ref provides the synchronously-accurate current answer.

---

## confirmed_at Flush Strategy (BR-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Bypass debounce for confirm | Add `confirmAnswer()` to context; cancel pending timer, fire direct `fetchApi()` immediately | ✓ |
| Flush debounce immediately | Call `clearTimeout` + invoke callback synchronously on confirm | |
| Send confirmed_at in draft payload | Pass `confirmed_at` field explicitly to backend | |

**User's choice:** Claude discretion
**Notes:** The backend already auto-sets `confirmed_at` when `answer_value` arrives for a row with `suggested_answer` (`qramm.py:565`). So the fix is purely about guaranteeing delivery — the confirm action must not go through the 300ms debounce queue. The `confirmAnswer()` method also cancels any pending debounce for the question to prevent a stale timer from overwriting the confirm with an older value.

---

## Test Validation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Install Playwright | Browser integration tests; requires bundle + live server | |
| Install Vitest + MSW | Hook unit/integration tests with request recording; `renderHook` + `vi.useFakeTimers()` | ✓ |
| No new test framework | Validate via existing a11y infra + Python pytest + manual UAT | |

**User's choice:** Claude discretion
**Notes:** The ROADMAP success criteria test hook behavior (stale scan ID on rapid switch, POST count during debounce window) — these are not visual rendering tests. Vitest + MSW is the right fit: `renderHook` for hooks, MSW as a network recorder, `vi.useFakeTimers()` for debounce simulation. Playwright would require a running app + built bundle; significant CI overhead for what are essentially unit tests.

---

## Claude's Discretion

All four areas were delegated to Claude. The user's instruction was "go forward with your recommended actions to address the questions." All decisions in CONTEXT.md reflect Claude's analysis of the codebase, audit findings, and implementation tradeoffs.

## Deferred Ideas

- **AbortController for true network cancellation** — more powerful than the flag pattern; deferred to future hardening phase
- **Custom ESLint plugin rule** — AST-aware cancelled-guard enforcement; deferred in favor of simpler CI grep check
- **Playwright integration tests** — if Vitest+MSW proves insufficient; deferred
- **`seededRef` reset on new assessment (IN-04)** — separate bug, distinct phase
- **`useScanList` WR-02 silent error swallowing** — low severity, opportunistic fix only
