---
phase: 54-qramm-assessment-ui-scorecard
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - tests/test_qramm_answer.py
  - quirk/models.py
  - quirk/db.py
  - quirk/dashboard/api/routes/qramm.py
  - tests/test_qramm_router.py
  - src/dashboard/src/components/ui/radio-group.tsx
  - src/dashboard/src/components/ui/collapsible.tsx
  - src/dashboard/src/components/ui/label.tsx
  - src/dashboard/src/context/QRAMMContext.tsx
  - src/dashboard/src/context/QRAMMProvider.tsx
  - src/dashboard/src/hooks/useQRAMMSession.ts
  - src/dashboard/src/lib/qramm-benchmarks.ts
  - src/dashboard/src/lib/qramm-constants.ts
  - src/dashboard/src/types/api.ts
  - src/dashboard/src/pages/qramm-profile.tsx
  - src/dashboard/src/App.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/components/qramm/QuestionCard.tsx
  - src/dashboard/src/components/qramm/PracticeAreaSection.tsx
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/components/qramm/ScorecardTab.tsx
  - src/dashboard/vite.config.ts
  - src/dashboard/tests/a11y/routes.json
findings:
  critical: 4
  warning: 7
  info: 3
  total: 14
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-05-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

This phase delivers the QRAMM assessment UI: org profile wizard, 4-dimension question tabs, per-question radio/evidence card, and a scorecard with radar chart. The backend gains four new API endpoints (list sessions, create profile, draft answer upsert, read answers) plus a migration for `evidence_note` on `qramm_answers`.

The implementation is broadly sound in structure. However several correctness issues were found — two of which can cause silent data loss or incorrect scoring, and two of which allow the application to reach an unrecoverable state. The debounce logic in `QRAMMProvider` has a closure bug that silently drops in-flight answer saves. The scorecard completion-percentage computation hard-codes question-number ranges that will break the moment the question catalog layout deviates from 1–30/31–60/61–90/91–120. The `draft_answer` endpoint allows upserts to silently clobber `evidence_note` with `None` when only `answer_value` is being patched. And the `list_sessions` endpoint issues N+1 queries (one `COUNT` per session row) with no limit or pagination, which degrades to a full-table scan as history grows and also exposes all historical assessment data to any unauthenticated caller on the same network.

---

## Critical Issues

### CR-01: Debounce closure in `QRAMMProvider` captures a stale `qn` and `state` reference

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:15-36`

**Issue:** `persistDraft` is a `useCallback` with `[]` as its dependency array, so it is memoised once. Inside the `setTimeout` callback it closes over `qn` and `state`, which are parameters to the outer `persistDraft` call. This part is fine — parameters are captured correctly per call. **However**, the debounce implementation uses a single shared `debounceRef` across all question numbers. If the user edits question 5 (starts a 300 ms timer) and then immediately edits question 12, the question-5 timer is cancelled and only the question-12 payload is sent. The question-5 change is silently lost — no retry, no error surfaced, no queuing. This is data-loss under normal, realistic usage (tabbing through questions quickly).

The comment in the code describes debouncing as if it is per-question, but the single `debounceRef` implements a global last-writer-wins debounce. Only the most-recently-touched question is ever persisted.

**Fix:** Maintain a `Map<number, ReturnType<typeof setTimeout>>` keyed by `questionNumber` so each question has its own independent debounce timer:

```typescript
const debounceRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

const persistDraft = useCallback((qn: number, state: Partial<AnswerState>) => {
  const sid = sessionIdRef.current
  if (sid == null) return
  const existing = debounceRef.current.get(qn)
  if (existing) clearTimeout(existing)
  const timer = setTimeout(async () => {
    debounceRef.current.delete(qn)
    try {
      await fetch("/api/qramm/assessment/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          question_number: qn,
          answer_value: state.answer_value ?? null,
          evidence_note: state.evidence_note ?? null,
        }),
      })
    } catch {
      // surface via page layer
    }
  }, 300)
  debounceRef.current.set(qn, timer)
}, [])
```

---

### CR-02: `draft_answer` endpoint silently wipes `evidence_note` when only `answer_value` is sent

**File:** `quirk/dashboard/api/routes/qramm.py:472-491`

**Issue:** `DraftAnswerRequest.evidence_note` defaults to `None`. When the frontend calls `POST /api/qramm/assessment/draft` with only `answer_value` (e.g., the batch `save_answers` path, or any caller that omits the field), the update branch checks `if payload.evidence_note is not None` and correctly skips the assignment. **But the insert branch (no existing row)** always writes `evidence_note=payload.evidence_note`, which is `None` — overwriting any prior value if the ORM somehow merges, but more critically: if a row is deleted and re-created via the upsert path, the note is lost.

A more immediate issue: `persistDraft` in `QRAMMProvider` always passes `state.evidence_note ?? null`. When `setAnswer` is called with only `{ answer_value: 3 }` (no `evidence_note` key), `state.evidence_note` is `undefined`, so `undefined ?? null` yields `null`, and the POST body contains `"evidence_note": null`. The backend receives a non-None `None` equivalent that passes the `if payload.evidence_note is not None` guard as False — correct. But the update branch for the *new-row* path (line 473–480) unconditionally sets `evidence_note=payload.evidence_note` to `None`. If the question was pre-seeded by the CVI bridge with a note, this wipes it.

More concretely: when the user changes a radio button on a pre-seeded CVI question (which triggers `handleAnswerChange` → `setAnswer({answer_value: n})` → `persistDraft(qn, {answer_value: n})`), `evidence_note` is absent from `state` in `persistDraft`, so `state.evidence_note ?? null` is `null`. The backend receives `evidence_note: null` and — because this is an **existing** row — correctly skips the assignment (line 485). That path is safe. However, **non-pre-seeded SGRM/DPE/ITR questions** that have no existing row will have a new row created with `evidence_note=None` even when the user previously entered a note that was persisted by a separate `evidence_note`-only draft call. The scenario: user types a note (draft fires, note saved), user changes radio within the debounce window (note draft is cancelled by CR-01), radio draft fires without note → new row created, note erased.

This is a compounding bug with CR-01 and produces silent evidence-note data loss.

**Fix:** In the insert branch, only set `evidence_note` when the payload value is non-None:

```python
row = QRAMMAnswer(
    session_id=payload.session_id,
    question_number=payload.question_number,
    dimension=meta["dimension"],
    practice_area=meta["practice_area"],
    answer_value=payload.answer_value,
    evidence_note=payload.evidence_note,  # None is fine for new rows
)
```

The insert path is actually fine as-is for brand-new rows (None is the correct default). The real fix needed is in `persistDraft` (CR-01): never send `evidence_note` in the body unless it was explicitly changed. Pass it only when the `state` object contains the key:

```typescript
body: JSON.stringify({
  session_id: sid,
  question_number: qn,
  ...(state.answer_value !== undefined && { answer_value: state.answer_value ?? null }),
  ...("evidence_note" in state && { evidence_note: state.evidence_note ?? null }),
}),
```

---

### CR-03: `list_sessions` endpoint has no authentication guard and no pagination — unbounded data exposure

**File:** `quirk/dashboard/api/routes/qramm.py:401-423`

**Issue:** `GET /api/qramm/sessions` returns **all** assessment sessions in the database with no limit, no pagination, and — consistent with the rest of the API — no authentication. For a single-user local tool this is low-risk, but the QRAMM assessment is specifically described as a consulting-grade engagement tool that may be run against client organisations. If the backend is exposed on a LAN (standard dev/consulting setup), all prior client assessment sessions (org names, answer counts, status, creation timestamps) are readable by any device on that network.

Additionally the endpoint issues a separate `COUNT` query for every session row returned (lines 411–415). For a consultant who has run assessments for N clients, this is N+1 queries. There is no `LIMIT` clause, so the response also grows without bound.

**Fix (minimum viable):** Add a `limit` query parameter and default it to a reasonable cap (e.g. 50):

```python
@router.get("/qramm/sessions", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_db), limit: int = 50) -> List[SessionSummary]:
    sessions = (
        db.query(QRAMMSession)
        .order_by(QRAMMSession.created_at.desc())
        .limit(limit)
        .all()
    )
    ...
```

The N+1 query pattern should also be resolved with a subquery or joined count rather than a Python-level loop.

---

### CR-04: `ScorecardTab` completion percentage hard-codes question-number ranges

**File:** `src/dashboard/src/components/qramm/ScorecardTab.tsx:36-42`

**Issue:** Completion per dimension is computed by deriving the dimension from the question number:

```typescript
const dimIdx = Math.floor((qn - 1) / 30)
if (DIMENSIONS[dimIdx] === dim) answered += 1
```

This hard-codes the assumption that questions 1–30 = CVI, 31–60 = SGRM, 61–90 = DPE, 91–120 = ITR and that each dimension has exactly 30 questions. This assumption is not validated anywhere in the frontend. If the QRAMM question catalog ever gains, loses, or reorders questions (even by one), this arithmetic breaks silently — dimensions are mis-attributed and percentages are wrong. The backend `QRAMM_QUESTIONS` list is the authoritative source of `question_number → dimension` mapping; the frontend already fetches it into `QuestionItem[]` via the assessment page.

The context `answers` map keys are `question_number` values (integers), but the `AnswerState` type does not carry `dimension`. The correct fix is to look up the dimension from the fetched question catalog, not from arithmetic on the question number.

**Fix:** Pass `questionsByArea` (or a `qnToDim` map) as a prop from `AssessmentPage` to `ScorecardTab`, or store it in context:

```typescript
// In ScorecardTab, receive qnToDim: Map<number, string> as prop
const completionByDim = useMemo(() => {
  const out: Record<string, number> = {}
  const totals: Record<string, number> = {}
  for (const dim of DIMENSIONS) { out[dim] = 0; totals[dim] = 0 }
  for (const [qn, a] of ctx.answers) {
    const dim = qnToDim.get(qn)
    if (!dim) continue
    totals[dim] = (totals[dim] ?? 0) + 1
    if (a.answer_value != null) out[dim] = (out[dim] ?? 0) + 1
  }
  return Object.fromEntries(
    DIMENSIONS.map(d => [d, totals[d] ? Math.round((out[d] / totals[d]) * 100) : 0])
  )
}, [ctx.answers, qnToDim])
```

---

## Warnings

### WR-01: `useQRAMMSession` omits `ctx` from `useEffect` dependency array

**File:** `src/dashboard/src/hooks/useQRAMMSession.ts:78`

**Issue:** The `useEffect` dependency array is `[tick]` with an `eslint-disable-line react-hooks/exhaustive-deps` suppression. Inside the effect, `ctx.setSessionId`, `ctx.resetAnswers` are called. These are stable callback references (from `useCallback` in `QRAMMProvider`), so in practice they will not change. However suppressing the exhaustive-deps rule entirely rather than listing the stable refs hides the risk: if `QRAMMProvider` is ever refactored to return unstable refs (e.g. by removing `useCallback`), the stale closure will silently stop updating the context.

**Fix:** List the specific stable context functions as deps, or document why suppression is acceptable:

```typescript
}, [tick, ctx.setSessionId, ctx.resetAnswers]) // stable refs from QRAMMProvider useCallback
```

---

### WR-02: `handleConfirmNew` defined inside a conditional render branch — hoisting/stale closure risk

**File:** `src/dashboard/src/pages/qramm-profile.tsx:49-65`

**Issue:** `handleConfirmNew` is declared as an `async function` inside the `if (session !== null)` branch — i.e., inside the function body of `OrgProfilePage` but conditionally only executed when the branch is rendered. This is not strictly a hooks violation (it is not a hook), but the function captures `ctx`, `reload`, and `setShowNewConfirm` from the outer render scope. If React ever renders the component tree in a way that the branch condition flips between the function declaration and invocation (unusual but possible under concurrent mode with transitions), the captured values may be stale.

Additionally, the `finally` block always calls `reload()` even when the `DELETE` request fails (the `catch` swallows the error). This means after a failed delete the UI calls `reload()`, which re-fetches the session list, sees the old session still exists, and re-renders the resume screen — correct. But the user has no indication the delete failed. This is a UX gap that creates confusion ("I clicked New Assessment but my old one is still there").

**Fix:** Move `handleConfirmNew` to a stable `useCallback` at the top of the component, and surface a failure message rather than silently ignoring the delete error:

```typescript
const handleConfirmNew = useCallback(async () => {
  setArchiving(true)
  try {
    if (ctx.sessionId != null) {
      const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
      if (!resp.ok) {
        setSubmitError("Could not archive session — try again")
        return
      }
    }
  } catch {
    setSubmitError("Could not archive session — check your connection")
    return
  } finally {
    setArchiving(false)
  }
  ctx.setSessionId(null)
  ctx.setProfile(null)
  ctx.setScoreResult(null)
  ctx.resetAnswers(new Map())
  setShowNewConfirm(false)
  reload()
}, [ctx, reload])
```

---

### WR-03: `handleNewAssessment` in `AssessmentPage` does not surface DELETE errors to the user

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:150-163`

**Issue:** The `try/finally` pattern resets context and navigates to `/qramm` even when the `DELETE` request fails (network error or 5xx). The user is silently redirected and sees a "no session" state, but the server still has the old session. On next load, `useQRAMMSession` will re-fetch it and resume from the old data — contradicting the user's intent to start fresh.

**Fix:** Check response status and show an error rather than silently proceeding:

```typescript
async function handleNewAssessment() {
  if (!ctx.sessionId) return
  setArchiving(true)
  try {
    const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
    if (!resp.ok) {
      // surface error; do not reset context
      setArchiving(false)
      return
    }
    ctx.setSessionId(null)
    ctx.resetAnswers(new Map())
    ctx.setProfile(null)
    ctx.setScoreResult(null)
    navigate("/qramm")
  } catch {
    // surface error
  } finally {
    setArchiving(false)
  }
}
```

---

### WR-04: `getBenchmarks` falls back to `INDUSTRY_BENCHMARKS.other` for unknown industries instead of returning null

**File:** `src/dashboard/src/lib/qramm-benchmarks.ts:23-26`

**Issue:**

```typescript
return INDUSTRY_BENCHMARKS[industry] ?? INDUSTRY_BENCHMARKS.other
```

When a future profile wizard adds a new `industry` value that is not yet in `INDUSTRY_BENCHMARKS`, this silently returns the `other` benchmark (all 2.0s) rather than `null`. The scorecard then shows a benchmark column that appears to have real data but is actually the generic `other` floor. This is a silent accuracy failure: consultants see a benchmark comparison that is fabricated.

**Fix:** Return `null` for unknown industries so the scorecard correctly renders "—":

```typescript
export function getBenchmarks(industry: string | null | undefined): DimensionBenchmarks | null {
  if (!industry) return null
  return INDUSTRY_BENCHMARKS[industry] ?? null
}
```

---

### WR-05: `vite.config.ts` reads fixture files at plugin-init time with synchronous `readFileSync` — crashes the dev server when fixture files are absent

**File:** `src/dashboard/vite.config.ts:10-12`

**Issue:** `readFileSync` at module evaluation time (plugin init) will throw `ENOENT` if `fixture-scan.json`, `fixture-trends.json`, or `fixture-qramm.json` are missing. This crashes the Vite dev server for any developer who does not have the fixture files in place — even when `VITE_A11Y_FIXTURE` is not set. The files are only needed when the env var is active.

**Fix:** Guard the reads inside `configureServer` / `configurePreviewServer` (where the env var is checked), or lazy-read inside the handler:

```typescript
function a11yFixture(): Plugin {
  let scanFixture: string, trendsFixture: string, qrammFixtureRaw: Record<string, unknown>

  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      scanFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8')
      trendsFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8')
      qrammFixtureRaw = JSON.parse(readFileSync(path.resolve(__dirname, './tests/a11y/fixture-qramm.json'), 'utf8'))
      server.middlewares.use(handler)
    },
    ...
  }
}
```

---

### WR-06: `create_profile` endpoint does not validate that the session already has a profile — calling it twice creates two QRAMMProfile rows

**File:** `quirk/dashboard/api/routes/qramm.py:426-453`

**Issue:** `POST /api/qramm/profiles` inserts a new `QRAMMProfile` row and updates `session.profile_id` unconditionally. Calling it twice for the same session creates two orphaned `QRAMMProfile` rows. The second call updates `session.profile_id` to the new row, leaving the first row unreferenced but present in the database. Over time this accumulates dead rows and may confuse any query that joins on `qramm_profiles.session_id`.

There is no uniqueness constraint on `(session_id)` in `QRAMMProfile` and no guard in the endpoint.

**Fix:** Check whether a profile already exists and update it rather than inserting a duplicate:

```python
existing_profile = (
    db.query(QRAMMProfile)
    .filter(QRAMMProfile.session_id == payload.session_id)
    .one_or_none()
)
if existing_profile:
    existing_profile.industry = payload.industry
    # ... update remaining fields
    db.commit()
    db.refresh(existing_profile)
    return CreateProfileResponse(...)
```

---

### WR-07: `QuestionCard` renders a `Confirm Answer` button for all auto-filled questions including those that have already been confirmed

**File:** `src/dashboard/src/components/qramm/QuestionCard.tsx:131-143`

**Issue:** The `isAutoFilled` flag is `suggested_answer != null && confirmed_at == null`. Once the user clicks Confirm, `confirmed_at` is set optimistically (in `handleConfirm` → `onConfirm` → `AssessmentPage.handleConfirm`), so `isAutoFilled` becomes `false` and the button disappears — correct. However, on the **next page load** (when answers are re-seeded from the server via `useQRAMMSession`), `confirmed_at` comes back from `QRAMMAnswerRead.confirmed_at`, which is a `string | null`. If the server returns a `confirmed_at` value, the button correctly stays hidden. But if the server's `confirmed_at` column is `NULL` for a question that was confirmed via the backend's `draft_answer` endpoint — which only sets `confirmed_at` when `suggested_answer IS NOT NULL AND answer_value IS NOT NULL` (line 488) — then after a reload the user is shown the Confirm button again for a question they already confirmed.

The backend `draft_answer` does set `confirmed_at` for the update branch. The risk is specifically when a question is created via the insert branch of `draft_answer` with both `suggested_answer` and `answer_value` set: line 473 creates the row but never sets `confirmed_at`. After a reload, the user sees the Confirm button on an already-answered question.

**Fix:** In the `draft_answer` insert branch, set `confirmed_at` when both `suggested_answer` and `answer_value` are present:

```python
row = QRAMMAnswer(
    ...
    answer_value=payload.answer_value,
    evidence_note=payload.evidence_note,
    confirmed_at=_now_iso() if (
        payload.answer_value is not None and payload.suggested_answer is not None
    ) else None,
)
```

Note: `DraftAnswerRequest` does not accept `suggested_answer` as a field, so the insert branch cannot set it. The real fix is: when creating a new row via `draft_answer`, look up whether a pre-seeded row with a `suggested_answer` already exists before branching to insert (which the code already does via `one_or_none()`). If a row with `suggested_answer` exists, the update branch is taken; the insert branch only fires when no row exists at all, so `suggested_answer` will always be `None` on insert — meaning `confirmed_at` should never need to be set in the insert branch. Document this invariant with a comment to prevent future confusion.

---

## Info

### IN-01: `_compute_multiplier` does not validate that `industry` or `data_sensitivity` are from the allowed set

**File:** `quirk/dashboard/api/routes/qramm.py:146-152`

**Issue:** `CreateProfileRequest.industry` and `data_sensitivity` are typed as `str` with no `Literal` / `Enum` constraint. Any string is accepted; unknown values silently fall back to `1.00` / `0.0`. A typo in an API call (e.g. `"finacial_services"`) returns `201` with a silently wrong multiplier. The frontend constrains choices via `SELECT` widgets, but the API itself has no guard.

**Fix:** Use Pydantic `Literal` or `Enum` types:

```python
from typing import Literal
IndustryType = Literal["financial_services", "healthcare", "government", "technology", "retail", "energy", "other"]

class CreateProfileRequest(BaseModel):
    industry: IndustryType
    data_sensitivity: Literal["public", "internal", "confidential", "restricted_secret", "restricted"]
    ...
```

---

### IN-02: `test_qramm_router.py` `test_read_session_round_trip` asserts `answers_count == 0` but Phase 53 pre-seeds 30 CVI rows

**File:** `tests/test_qramm_router.py:97`

**Issue:**

```python
assert body["answers_count"] == 0
```

`create_session` pre-seeds 30 blank CVI `QRAMMAnswer` rows (Phase 53 QRAMM-12). `answers_count` is computed as rows where `answer_value IS NOT NULL`, so blank pre-seeded rows (where `answer_value=None`) do not count. The assertion passes today. But the assertion comment says nothing about this, and any change that pre-fills answers with a non-null `answer_value` would silently break this test's assumption without the test explaining why. The assertion should include a comment anchoring it to the `answer_value IS NOT NULL` filter.

**Fix:** Add a clarifying comment:

```python
# Pre-seeded CVI rows have answer_value=None, so count must be 0 here.
assert body["answers_count"] == 0
```

---

### IN-03: `ScoreRequest.profile_multiplier` has bounds `ge=0.5, le=2.0` but `_compute_multiplier` clamps to `0.8–1.5`

**File:** `quirk/dashboard/api/routes/qramm.py:83`

**Issue:** The API accepts `profile_multiplier` values from 0.5 to 2.0, but the RESEARCH/spec document states the valid range is 0.8–1.5 and `_compute_multiplier` enforces that via `max(0.8, min(1.5, ...))`. The `score_session` endpoint does not clamp the manually-supplied multiplier — a caller who sends `{"profile_multiplier": 0.5}` gets weighted scores computed at 0.5x, which is outside the specified model range. The inconsistency between the validation bounds and the spec range is confusing and can produce out-of-spec score results.

**Fix:** Tighten the Pydantic bounds to match the spec:

```python
class ScoreRequest(BaseModel):
    profile_multiplier: Optional[float] = Field(default=None, ge=0.8, le=1.5)
```

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
