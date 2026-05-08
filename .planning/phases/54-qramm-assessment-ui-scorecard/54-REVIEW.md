---
phase: 54-qramm-assessment-ui-scorecard
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - quirk/dashboard/api/routes/qramm.py
  - quirk/db.py
  - quirk/models.py
  - src/dashboard/src/App.tsx
  - src/dashboard/src/components/qramm/PracticeAreaSection.tsx
  - src/dashboard/src/components/qramm/QuestionCard.tsx
  - src/dashboard/src/components/qramm/ScorecardTab.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/components/ui/collapsible.tsx
  - src/dashboard/src/components/ui/label.tsx
  - src/dashboard/src/components/ui/radio-group.tsx
  - src/dashboard/src/context/QRAMMContext.tsx
  - src/dashboard/src/context/QRAMMProvider.tsx
  - src/dashboard/src/hooks/useQRAMMSession.ts
  - src/dashboard/src/lib/qramm-benchmarks.ts
  - src/dashboard/src/lib/qramm-constants.ts
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/pages/qramm-profile.tsx
  - src/dashboard/src/types/api.ts
  - src/dashboard/tests/a11y/fixture-qramm.json
  - src/dashboard/tests/a11y/routes.json
  - src/dashboard/vite.config.ts
  - tests/test_qramm_answer.py
  - tests/test_qramm_router.py
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

This phase delivers the QRAMM assessment UI: org profile wizard, four dimension question tabs (CVI/SGRM/DPE/ITR), per-question radio/evidence card, and a scorecard with radar chart. The backend gains four new API endpoints (list sessions, create profile, draft answer upsert, read answers) plus the Phase 54 `evidence_note` migration on `qramm_answers`. The test suite covers the new endpoints well.

Four critical defects were found. The most severe is a data-loss bug in `QRAMMProvider`: the single shared debounce timer means that rapid edits across different questions silently drop all but the last save — a scenario that occurs under normal usage. The scorecard completion computation hard-codes question-number arithmetic that will silently mismatch if the question catalog layout changes. The `list_sessions` endpoint issues an unbounded N+1 query set with no pagination. The `handleNewAssessment` / `handleConfirmNew` flows in both page files reset client context even on server-side failures, causing the client and server to diverge.

---

## Critical Issues

### CR-01: Single shared debounce timer in `QRAMMProvider` causes silent data loss across multiple questions

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:18-36`

**Issue:** `debounceRef` is a single `useRef` holding one timer. Every call to `persistDraft` — regardless of which `qn` (question number) is being updated — clears that single timer and schedules a new one. When a user edits question 5 and then edits question 12 within 300 ms (normal when scrolling through a practice area section or using keyboard navigation), the question-5 timer is cancelled. Only the question-12 payload is sent to `/api/qramm/assessment/draft`. The question-5 answer is written to local React state but never persisted to the server. On a page reload `useQRAMMSession` re-seeds answers from the server, and question 5 reverts to its pre-edit value with no indication to the user.

This is a silent data loss bug under realistic usage. The comment on line 18 implies the debounce is per-question ("QRAMMProvider debounces 300ms") but the implementation is global last-writer-wins.

**Fix:** Maintain a per-question debounce map so each question has an independent timer:

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
    } catch { /* surface via page layer */ }
  }, 300)
  debounceRef.current.set(qn, timer)
}, [])
```

---

### CR-02: `handleNewAssessment` and `handleConfirmNew` reset client context in `finally` — server divergence on failure

**File:** `src/dashboard/src/pages/qramm-assessment.tsx:150-163` and `src/dashboard/src/pages/qramm-profile.tsx:49-65`

**Issue:** Both "New Assessment" flows follow a `try/finally` pattern where the `finally` block unconditionally resets `sessionId`, `answers`, `profile`, `scoreResult` and (in the assessment page) navigates to `/qramm`. In `qramm-assessment.tsx` the `finally` always fires regardless of whether the `DELETE` returned a non-2xx status code — a non-ok response does not throw, so the `catch` does not intercept it. The client clears its state and navigates away while the server still has the old session. When `useQRAMMSession` runs after navigation it re-fetches the session list, finds the un-deleted session, and re-seeds context from it — the user ends up back on the resume screen having been led to believe they started fresh.

In `qramm-profile.tsx` (line 55) the `catch` block explicitly silences errors: `// Ignore errors — user wants a clean slate regardless`. This is the same divergence: on a network error the server still has the session, but the client shows a fresh profile form. On the next reload the session reappears.

**Fix:** Check `resp.ok` before resetting context and only navigate/reload on success:

```typescript
// qramm-assessment.tsx
async function handleNewAssessment() {
  if (!ctx.sessionId) return
  setArchiving(true)
  try {
    const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
    if (!resp.ok && resp.status !== 404) {
      // surface error state — do NOT reset context
      return
    }
    ctx.setSessionId(null)
    ctx.resetAnswers(new Map())
    ctx.setProfile(null)
    ctx.setScoreResult(null)
    navigate("/qramm")
  } catch {
    // surface error to user
  } finally {
    setArchiving(false)
  }
}
```

---

### CR-03: `list_sessions` issues N+1 queries with no upper bound on result set

**File:** `quirk/dashboard/api/routes/qramm.py:401-423`

**Issue:** The endpoint fetches all session rows then executes a separate `COUNT` SQL query for each session row inside a Python loop (lines 411-415). With N sessions this is N+1 database round-trips. There is no `LIMIT` clause on the initial session query, so both the response size and the query count grow unbounded as assessment history accumulates. For a consultant who has run dozens of client assessments, this endpoint blocks the sync thread pool for the duration of N+1 sequential SQLite queries and returns an arbitrarily large response.

Beyond the N+1 pattern, fetching all historical assessment sessions (org names, timestamps, status, answer counts) with no authentication or pagination gate exposes all prior client data to any browser on the same LAN as the API server.

**Fix:** Resolve with a correlated subquery to reduce to a single DB round-trip, and add a default `limit`:

```python
from sqlalchemy import func

@router.get("/qramm/sessions", response_model=List[SessionSummary])
def list_sessions(db: Session = Depends(get_db), limit: int = 50) -> List[SessionSummary]:
    answered_sq = (
        db.query(
            QRAMMAnswer.session_id,
            func.count(QRAMMAnswer.id).label("cnt"),
        )
        .filter(QRAMMAnswer.answer_value.isnot(None))
        .group_by(QRAMMAnswer.session_id)
        .subquery()
    )
    rows = (
        db.query(QRAMMSession, func.coalesce(answered_sq.c.cnt, 0).label("answers_count"))
        .outerjoin(answered_sq, QRAMMSession.id == answered_sq.c.session_id)
        .order_by(QRAMMSession.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        SessionSummary(
            session_id=s.id,
            org_name=s.org_name,
            created_at=_iso_str(s.created_at),
            status=s.status,
            answers_count=count,
        )
        for s, count in rows
    ]
```

---

### CR-04: `ScorecardTab` completion percentage hard-codes question-number arithmetic instead of using the catalog

**File:** `src/dashboard/src/components/qramm/ScorecardTab.tsx:36-42`

**Issue:** Completion per dimension is computed by deriving the dimension index from the question number:

```typescript
const dimIdx = Math.floor((qn - 1) / 30)
if (DIMENSIONS[dimIdx] === dim) answered += 1
```

This hard-codes the assumption that questions 1–30 = CVI, 31–60 = SGRM, 61–90 = DPE, 91–120 = ITR. This is a parallel source of truth that diverges from `QRAMM_QUESTIONS` (the authoritative catalog). If any question is added, removed, or renumbered, the per-dimension completion percentages shown in the scorecard table will be wrong — silently and with no type-system protection. The frontend already fetches the 120-question catalog from `/api/qramm/questions` into the `questions: QuestionItem[]` state in `AssessmentPage`; each `QuestionItem` carries a `dimension` field.

Additionally, the denominator is hard-coded as `30` (line 40: `(answered / 30) * 100`). If any dimension ever has a different question count, completion percentages exceed 100% or never reach 100%.

**Fix:** Pass a question-number-to-dimension lookup into `ScorecardTab` rather than performing arithmetic:

```typescript
// In qramm-assessment.tsx: build and pass to ScorecardTab
const qnToDim = useMemo(() => {
  const m = new Map<number, string>()
  for (const q of questions) m.set(q.question_number, q.dimension)
  return m
}, [questions])

// ScorecardTab receives: qnToDim: Map<number, string>
const completionByDim = useMemo(() => {
  const answered: Record<string, number> = {}
  const totals: Record<string, number> = {}
  for (const [qn, a] of ctx.answers) {
    const dim = qnToDim.get(qn)
    if (!dim) continue
    totals[dim] = (totals[dim] ?? 0) + 1
    if (a.answer_value != null) answered[dim] = (answered[dim] ?? 0) + 1
  }
  return Object.fromEntries(
    DIMENSIONS.map(d => [d, totals[d] ? Math.round(((answered[d] ?? 0) / totals[d]) * 100) : 0])
  )
}, [ctx.answers, qnToDim])
```

---

## Warnings

### WR-01: `persistDraft` always includes `evidence_note: null` when only `answer_value` changes — can overwrite a previously saved note

**File:** `src/dashboard/src/context/QRAMMProvider.tsx:26-29`

**Issue:** `persistDraft` is called with the `state` partial passed to `setAnswer`. When only `answer_value` is being changed (e.g., user clicks a radio button), `state` contains `{ answer_value: 3 }` and `state.evidence_note` is `undefined`. The body construction `state.evidence_note ?? null` converts `undefined` to `null` and sends `"evidence_note": null` to the backend. The backend `draft_answer` update branch correctly guards `if payload.evidence_note is not None` and skips the assignment (line 485 of `qramm.py`), so the note is not wiped in the update path.

However, for **non-pre-seeded questions** (SGRM/DPE/ITR) where no row exists yet, the `draft_answer` insert branch fires and sets `evidence_note=None` (from `payload.evidence_note` which is `None`) — wiping any note the user typed in a previous draft call that was superseded by a radio-button edit that arrived first via the debounce queue. This is a compound effect of CR-01 (global debounce drops the note-save, then radio-save creates the row with `evidence_note=None`).

Even without CR-01 in play, the body should not include `evidence_note` at all when the caller did not explicitly set it:

**Fix:** Only include `evidence_note` in the POST body when the `state` partial explicitly carries the key:

```typescript
body: JSON.stringify({
  session_id: sid,
  question_number: qn,
  ...("answer_value" in state && { answer_value: state.answer_value ?? null }),
  ...("evidence_note" in state && { evidence_note: state.evidence_note ?? null }),
}),
```

---

### WR-02: `create_profile` allows duplicate profiles per session — old rows orphaned

**File:** `quirk/dashboard/api/routes/qramm.py:426-453`

**Issue:** `POST /api/qramm/profiles` always inserts a new row and updates `session.profile_id`. Calling it twice for the same session creates two `QRAMMProfile` rows with the same `session_id`. The first profile row is orphaned — no foreign key constraint, no cascade, no cleanup. Any analytics or reporting that queries `qramm_profiles` on `session_id` will find multiple rows and return ambiguous results. The UI currently calls this endpoint only once, but the API is not guarded.

**Fix:** Upsert semantics — check for an existing profile row first:

```python
existing = (
    db.query(QRAMMProfile)
    .filter(QRAMMProfile.session_id == payload.session_id)
    .one_or_none()
)
if existing:
    # update in place
    existing.industry = payload.industry
    existing.org_size = payload.org_size
    existing.geographic_scope = payload.geographic_scope
    existing.data_sensitivity = payload.data_sensitivity
    existing.regulatory_obligations = json.dumps(payload.regulatory_obligations)
    existing.multiplier = multiplier
    db.commit()
    db.refresh(existing)
    return CreateProfileResponse(profile_id=existing.id, session_id=payload.session_id, multiplier=multiplier)
```

---

### WR-03: `test_list_sessions_orders_desc` is non-deterministic on fast hardware

**File:** `tests/test_qramm_router.py:278-290`

**Issue:** The test creates two sessions back-to-back in the same function with no delay:

```python
sid1 = client.post("/api/qramm/sessions", json={"org_name": "First"}).json()["session_id"]
sid2 = client.post("/api/qramm/sessions", json={"org_name": "Second"}).json()["session_id"]
```

The ORDER BY clause in `list_sessions` is `QRAMMSession.created_at.desc()`. On a fast machine with an in-memory SQLite database, both rows may receive identical `created_at` timestamps (same microsecond). When timestamps tie, SQLite's ordering is undefined — the assertion `body[0]["session_id"] == sid2` can fail non-deterministically.

**Fix:** Assert ordering by ID as a tiebreaker in the endpoint, or add a minimal sleep in the test, or assert membership rather than position when timestamps may collide:

```python
# In list_sessions endpoint, add tiebreaker:
.order_by(QRAMMSession.created_at.desc(), QRAMMSession.id.desc())
```

---

### WR-04: `getBenchmarks` silently falls back to `other` benchmarks for unrecognised industry strings

**File:** `src/dashboard/src/lib/qramm-benchmarks.ts:23-26`

**Issue:**

```typescript
return INDUSTRY_BENCHMARKS[industry] ?? INDUSTRY_BENCHMARKS.other
```

Any unknown `industry` string (future option, typo, API mismatch) silently returns the generic `other` benchmark (all 2.0). The scorecard then renders a benchmark comparison column that appears to contain real industry data but is actually the placeholder floor value. Consultants using the scorecard cannot distinguish a genuine `other` benchmark from a fallback caused by a missing entry.

**Fix:** Return `null` for unknown industries and let the scorecard render "—" in the benchmark column:

```typescript
export function getBenchmarks(industry: string | null | undefined): DimensionBenchmarks | null {
  if (!industry) return null
  return INDUSTRY_BENCHMARKS[industry] ?? null
}
```

---

### WR-05: `vite.config.ts` reads fixture files at plugin initialisation time — crashes dev server when files are absent

**File:** `src/dashboard/vite.config.ts:10-12`

**Issue:** Lines 10–12 call `readFileSync` synchronously at plugin init time, before any env-var check:

```typescript
const scanFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8')
const trendsFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8')
const qrammFixtureRaw = JSON.parse(readFileSync(...))
```

Any developer who runs `vite dev` or `vite build` without the fixture files present — or on a fresh clone before the test fixture files are committed — gets an `ENOENT` crash at startup even if they never intend to use the a11y fixture mode. The files are only needed when `VITE_A11Y_FIXTURE` is set.

**Fix:** Move the `readFileSync` calls inside `configureServer` after the env-var guard:

```typescript
configureServer(server) {
  if (!process.env.VITE_A11Y_FIXTURE) return
  const scanFixture = readFileSync(...)
  // ...
  server.middlewares.use(handler)
},
```

---

### WR-06: `ScoreRequest.profile_multiplier` accepts values outside the model-specified range

**File:** `quirk/dashboard/api/routes/qramm.py:83`

**Issue:** `ScoreRequest.profile_multiplier` is validated as `ge=0.5, le=2.0`. The RESEARCH document and `_compute_multiplier` both specify the valid multiplier range as 0.8–1.5. An API caller who sends `{"profile_multiplier": 0.5}` gets a `200` response with weighted scores computed at 0.5x — outside the model's defined range and without any clamping in `score_session`. This produces out-of-spec scores that are persisted to `score_json`.

**Fix:** Tighten the Pydantic bounds to match the spec and mirror `_compute_multiplier`:

```python
class ScoreRequest(BaseModel):
    profile_multiplier: Optional[float] = Field(default=None, ge=0.8, le=1.5)
```

---

### WR-07: `score_session` returns `200` with `overall=0.0` when no questions are answered

**File:** `quirk/dashboard/api/routes/qramm.py:308-370`

**Issue:** If called on a session with zero answered questions (or only CVI pre-seeded rows with `answer_value=NULL`), `rows` is empty, `practice_buckets` is empty, all `dimension_scores` are `0.0`, and the endpoint returns `{ "overall": 0.0, "maturity": "...", status: "scored" }`. This is then persisted to `score_json` and `status` is set to `"scored"`. A session with no answered questions now shows as scored, which is semantically incorrect and will confuse any downstream consumer that treats `status="scored"` as meaningful.

**Fix:** Guard against scoring an empty session:

```python
if not rows:
    raise HTTPException(
        status_code=422,
        detail="Cannot score a session with no answered questions",
    )
```

---

## Info

### IN-01: `_compute_multiplier` silently falls back to defaults for unknown `industry` or `data_sensitivity` values

**File:** `quirk/dashboard/api/routes/qramm.py:146-152`

**Issue:** `CreateProfileRequest.industry` and `data_sensitivity` are plain `str` fields with no enumeration constraint. Unknown values fall back silently: `_INDUSTRY_BASE.get(industry, 1.00)` and `_SENSITIVITY_DELTA.get(data_sensitivity, 0.0)`. A typo or future UI option that is not yet in the backend dictionaries returns `201` with a silently incorrect multiplier.

**Fix:** Apply Pydantic `Literal` validation so the API rejects unrecognised values with `422`:

```python
from typing import Literal
IndustryLiteral = Literal["financial_services","healthcare","government","technology","retail","energy","other"]
SensitivityLiteral = Literal["public","internal","confidential","restricted_secret","restricted"]

class CreateProfileRequest(BaseModel):
    industry: IndustryLiteral
    data_sensitivity: SensitivityLiteral
    ...
```

---

### IN-02: `test_read_session_round_trip` asserts `answers_count == 0` without explaining the pre-seeding invariant

**File:** `tests/test_qramm_router.py:97`

**Issue:** `create_session` pre-seeds 30 blank CVI `QRAMMAnswer` rows with `answer_value=None` (Phase 53 QRAMM-12). `answers_count` only counts rows where `answer_value IS NOT NULL`, so the assertion passes. But there is no comment explaining this — a future reader may assume no rows are created at all, and a change that accidentally fills pre-seeded rows with a default `answer_value` will break the assertion silently.

**Fix:** Add a comment anchoring the assertion to the filter:

```python
# Pre-seeded CVI rows have answer_value=None and are excluded from answers_count.
assert body["answers_count"] == 0
```

---

### IN-03: `_ensure_qramm_tables` is redundant — QRAMM tables are already created by the top-level `Base.metadata.create_all` in `init_db`

**File:** `quirk/db.py:214-225` and `252`

**Issue:** `init_db` calls `Base.metadata.create_all(engine)` on line 244, which creates all ORM-registered tables including `QRAMMSession`, `QRAMMAnswer`, and `QRAMMProfile` (registered via `quirk.models`). Then on line 252 it calls `_ensure_qramm_tables(engine)`, which calls `Base.metadata.create_all(engine, checkfirst=True)` again. The second call is a complete no-op — all tables already exist. The function adds confusion (the docstring says "create QRAMM tables if absent" but they are already created) and maintenance surface (two code paths that both create the same tables).

**Fix:** Remove `_ensure_qramm_tables` and its call from `init_db`. The top-level `create_all` on line 244 already covers all Base-registered tables. If isolated QRAMM table creation is needed for tests, document that tests should call `Base.metadata.create_all(engine)` directly.

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
