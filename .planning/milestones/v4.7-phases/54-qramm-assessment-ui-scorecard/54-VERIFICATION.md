---
phase: 54-qramm-assessment-ui-scorecard
verified: 2026-05-07T18:00:00Z
status: human_needed
score: 18/18 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /qramm in the browser, fill the Org Profile form with all 5 fields, and click Start Assessment"
    expected: "Session created, profile created, redirected to /qramm/assessment, sidebar QRAMM entry is highlighted"
    why_human: "End-to-end form submission + navigation + sidebar highlight require a running browser"
  - test: "On /qramm/assessment, click each of the 5 tabs (CVI, SGRM, DPE, ITR, Scorecard)"
    expected: "Each dimension tab shows 3 default-open collapsible sections with 10 question cards each (30 per tab); Scorecard tab shows Calculate Score button, empty radar chart with callout text"
    why_human: "120-question rendering correctness and collapsible open state require visual inspection"
  - test: "Select a radio for a non-auto-filled question, wait ~1 second, then refresh the page"
    expected: "The same radio is still selected (debounced draft persisted and restore-on-reload working)"
    why_human: "Requires running browser + backend to verify end-to-end persistence and reload"
  - test: "If any session has an auto-filled question (suggested_answer != null), verify the Auto-filled from scan badge appears; change the radio; verify Modified from scan suggestion badge; click Confirm Answer; verify badge disappears"
    expected: "Badge state transitions correctly per D-04/D-05/D-06"
    why_human: "Requires live CVI scan data or pre-seeded suggested_answer rows; badge state is dynamic"
  - test: "Click Calculate Score on the Scorecard tab after answering some questions"
    expected: "Radar chart renders with 4-axis polygon, dimension summary table shows numeric values, maturity distribution fills"
    why_human: "Visual chart rendering and score response integration require running app"
---

# Phase 54: QRAMM Assessment UI + Scorecard Verification Report

**Phase Goal:** Build the QRAMM Assessment UI — an interactive web-based assessment tool that walks users through the 120-question QRAMM framework, captures and persists answers, and renders a scored quantum-readiness profile with industry benchmark comparison.
**Verified:** 2026-05-07T18:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | evidence_note column exists on qramm_answers table after init_db() | ✓ VERIFIED | `quirk/models.py` line 134: `evidence_note = Column(Text, nullable=True)` confirmed; `quirk/db.py` has `_ensure_phase54_qramm_columns` called from `init_db()`; 33 pytest tests pass including migration behavior tests |
| 2 | GET /api/qramm/sessions returns list of sessions ordered by created_at DESC | ✓ VERIFIED | Router at line 401: `order_by(QRAMMSession.created_at.desc())`; test_list_sessions_orders_desc in test suite (33 pass) |
| 3 | POST /api/qramm/profiles creates a qramm_profiles row, computes a 0.8–1.5 multiplier, and links it to QRAMMSession.profile_id | ✓ VERIFIED | `_compute_multiplier` function + `session.profile_id = profile.id` at line 446; test_create_profile and test_create_profile_multiplier_varies pass |
| 4 | POST /api/qramm/assessment/draft upserts a single answer (answer_value and/or evidence_note) | ✓ VERIFIED | `draft_answer` endpoint (line 456): upserts by (session_id, question_number); test_draft_answer_creates_row and test_draft_answer_updates_row pass |
| 5 | GET /api/qramm/sessions/{id}/answers returns full answer rows including suggested_answer + confirmed_at | ✓ VERIFIED | `read_answers` endpoint (line 494): returns AnswerRead with all fields including suggested_answer, confirmed_at, evidence_note |
| 6 | Auto-filled answer only sets confirmed_at when answer_value is supplied | ✓ VERIFIED | `draft_answer` line 488: `if existing.suggested_answer is not None and payload.answer_value is not None: existing.confirmed_at = _now_iso()`; test_draft_answer_confirms_when_suggested passes |
| 7 | Three shadcn primitives (radio-group, collapsible, label) exist in src/dashboard/src/components/ui/ | ✓ VERIFIED | All three files exist on disk; radio-group.tsx contains RadioGroupPrimitive (indirectly via @radix-ui/react-radio-group imports) |
| 8 | QRAMMContext exposes sessionId, answers Map, profile, scoreResult plus setters | ✓ VERIFIED | QRAMMContext.tsx lines 26-48: full 9-field context interface confirmed |
| 9 | QRAMMProvider wraps children and stores all state with 300ms debounced draft persistence | ✓ VERIFIED | QRAMMProvider.tsx: useState for all 4 state fields; `setTimeout(..., 300)` in persistDraft; QRAMMContext.Provider value prop present |
| 10 | useQRAMMSession hook fetches sessions list and seeds answers from /api/qramm/sessions/{id}/answers | ✓ VERIFIED | useQRAMMSession.ts: fetch to /api/qramm/sessions + fetch to /api/qramm/sessions/{id}/answers; cancellation guard `let cancelled = false`; resetAnswers called |
| 11 | /qramm route renders OrgProfilePage with 5 form fields and auto-resume behavior | ✓ VERIFIED | qramm-profile.tsx (310 lines): 3 visual states (loading/resume/form); INDUSTRY_OPTIONS, ORG_SIZE_OPTIONS, GEOGRAPHIC_SCOPE_OPTIONS, DATA_SENSITIVITY_OPTIONS, REGULATORY_OPTIONS all consumed; Resume Your Assessment heading; POST /api/qramm/sessions → POST /api/qramm/profiles → navigate('/qramm/assessment') chain |
| 12 | QRAMMProvider wraps Routes inside ScanProvider and sidebar has QRAMM Assessment nav entry | ✓ VERIFIED | App.tsx: `<ScanProvider><QRAMMProvider>` nesting confirmed; sidebar.tsx: ClipboardList import + `{ path: "/qramm", label: "QRAMM Assessment", Icon: ClipboardList }` + `startsWith("/qramm")` active state |
| 13 | /qramm/assessment renders 5 tabs (CVI, SGRM, DPE, ITR, Scorecard) with 120 questions across 12 collapsible sections | ✓ VERIFIED | qramm-assessment.tsx: 5 TabsTrigger values (cvi/sgrm/dpe/itr/scorecard); DimensionTab renders PracticeAreaSection for each of 3 practice areas; catalog fetched from /api/qramm/questions; per-dimension Progress bar with "X of N answered" label |
| 14 | QuestionCard shows auto-fill badge, modified badge, Confirm Answer button, and two-step D-04/D-05 UX | ✓ VERIFIED | QuestionCard.tsx: Auto-filled from scan badge (severity-accent-chip), Modified from scan suggestion badge (severity-medium-chip); Confirm Answer button visible only when isAutoFilled; local pendingValue state gates answer_value write |
| 15 | PracticeAreaSection renders default-open Collapsible with per-section answered counter | ✓ VERIFIED | PracticeAreaSection.tsx: `<Collapsible defaultOpen={true}>`; answered/questions.length counter; ChevronDown with data-[state=open]:rotate-180 |
| 16 | GET /api/qramm/questions returns the 120-question catalog | ✓ VERIFIED | list_questions endpoint at line 393; QRAMM_QUESTIONS imported; test_list_questions_returns_120 passes (33 total tests pass) |
| 17 | ScorecardTab renders RadarChart with 4 axes, dimension table, maturity distribution; Calculate Score is the only score trigger | ✓ VERIFIED | ScorecardTab.tsx (266 lines): RadarChart from recharts; PolarGrid + PolarAngleAxis + 2 conditional Radar elements; both have isAnimationActive={false}; Calculate Score button calls POST /api/qramm/sessions/${sessionId}/score; scoreResult stored via ctx.setScoreResult |
| 18 | /qramm and /qramm/assessment registered in a11y routes.json; fixture-qramm.json has required mock keys | ✓ VERIFIED | routes.json has 11 entries including both qramm routes; fixture-qramm.json has GET /api/qramm/sessions, GET /api/qramm/questions (120 entries), sessions/1, sessions/1/answers |

**Score:** 18/18 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/models.py` | QRAMMAnswer.evidence_note column | ✓ VERIFIED | Line 134: `evidence_note = Column(Text, nullable=True)` |
| `quirk/db.py` | _ensure_phase54_qramm_columns migration | ✓ VERIFIED | Lines 193-211: DDL dict + function; called from init_db() line 253 |
| `quirk/dashboard/api/routes/qramm.py` | 5 new endpoints (list_sessions, create_profile, draft_answer, read_answers, list_questions) | ✓ VERIFIED | All 5 endpoint decorators confirmed; 496+ lines |
| `tests/test_qramm_answer.py` | Migration behavior tests | ✓ VERIFIED | Exists (82 lines); part of 33-test passing suite |
| `tests/test_qramm_router.py` | Tests for all new endpoints | ✓ VERIFIED | 13 new tests added; all 33 QRAMM router tests pass |
| `src/dashboard/src/components/ui/radio-group.tsx` | shadcn RadioGroup primitive | ✓ VERIFIED | File exists |
| `src/dashboard/src/components/ui/collapsible.tsx` | shadcn Collapsible primitive | ✓ VERIFIED | File exists |
| `src/dashboard/src/components/ui/label.tsx` | shadcn Label primitive | ✓ VERIFIED | File exists |
| `src/dashboard/src/context/QRAMMContext.tsx` | QRAMMContext + AnswerState/OrgProfile/ScoreResult types | ✓ VERIFIED | All 3 interfaces + createContext with 9-field default |
| `src/dashboard/src/context/QRAMMProvider.tsx` | QRAMMProvider with debounced persist | ✓ VERIFIED | 300ms setTimeout; QRAMMContext.Provider value |
| `src/dashboard/src/hooks/useQRAMMSession.ts` | Session loader hook | ✓ VERIFIED | Cancellation guard; seeds from /answers endpoint |
| `src/dashboard/src/lib/qramm-benchmarks.ts` | INDUSTRY_BENCHMARKS lookup | ✓ VERIFIED | Exists; financial_services + 6 other sectors |
| `src/dashboard/src/lib/qramm-constants.ts` | PRACTICE_AREA_NAMES, MATURITY_LABEL, MATURITY_BADGE_CLASS, DIMENSIONS | ✓ VERIFIED | All 5 constants confirmed (count returns 5) |
| `src/dashboard/src/pages/qramm-profile.tsx` | OrgProfilePage component | ✓ VERIFIED | 310 lines; exports OrgProfilePage; 3 visual states |
| `src/dashboard/src/App.tsx` | QRAMMProvider wrapping; /qramm + /qramm/assessment routes | ✓ VERIFIED | ScanProvider > QRAMMProvider nesting; 2 routes registered; no _AssessmentPagePlaceholder remaining |
| `src/dashboard/src/components/sidebar.tsx` | QRAMM nav item with ClipboardList + startsWith active state | ✓ VERIFIED | ClipboardList imported; NAV_ITEMS entry; startsWith('/qramm') check |
| `src/dashboard/src/pages/qramm-assessment.tsx` | AssessmentPage with 5-tab layout | ✓ VERIFIED | 256 lines; 5 TabsTriggers; DimensionTab renders PracticeAreaSection; useQRAMMSession seeding; ScorecardPlaceholder removed (0 occurrences) |
| `src/dashboard/src/components/qramm/QuestionCard.tsx` | QuestionCard with auto-fill UX | ✓ VERIFIED | 165 lines; two-step pendingValue pattern; all badges + Confirm Answer |
| `src/dashboard/src/components/qramm/PracticeAreaSection.tsx` | Collapsible section with answered counter | ✓ VERIFIED | 70 lines; defaultOpen={true}; answered counter |
| `src/dashboard/src/components/qramm/ScorecardTab.tsx` | ScorecardTab with recharts | ✓ VERIFIED | 266 lines (meets 150 min); 2x isAnimationActive={false}; Calculate Score button; score endpoint wired |
| `src/dashboard/tests/a11y/routes.json` | /qramm and /qramm/assessment route entries | ✓ VERIFIED | Both slugs + paths confirmed; valid JSON; 11 total routes |
| `src/dashboard/tests/a11y/fixture-qramm.json` | Mock API responses | ✓ VERIFIED | 1477 lines; 4 keys including 120-question catalog |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| init_db() | _ensure_phase54_qramm_columns(engine) | called after _ensure_qramm_tables | ✓ WIRED | db.py line 253 confirms |
| POST /api/qramm/profiles | QRAMMSession.profile_id | session.profile_id = profile.id | ✓ WIRED | qramm.py line 446 |
| POST /api/qramm/assessment/draft | qramm_answers row | upsert by (session_id, question_number) | ✓ WIRED | filter(QRAMMAnswer.session_id == ...) confirmed |
| QRAMMProvider | QRAMMContext.Provider | value prop with all 8 fields | ✓ WIRED | QRAMMProvider.tsx: QRAMMContext.Provider value confirmed |
| useQRAMMSession | /api/qramm/sessions + /api/qramm/sessions/{id}/answers | fetch in useEffect with cancellation guard | ✓ WIRED | Both fetch calls confirmed in useQRAMMSession.ts |
| App.tsx | QRAMMProvider | import + JSX wrap inside ScanProvider | ✓ WIRED | App.tsx: ScanProvider > QRAMMProvider nesting confirmed |
| OrgProfilePage submit | /api/qramm/profiles | fetch POST | ✓ WIRED | qramm-profile.tsx: `fetch("/api/qramm/profiles", ...)` confirmed |
| OrgProfilePage post-submit | /qramm/assessment | useNavigate | ✓ WIRED | `navigate("/qramm/assessment")` confirmed |
| sidebar.tsx | /qramm route | NAV_ITEMS + startsWith active check | ✓ WIRED | ClipboardList + startsWith('/qramm') confirmed |
| AssessmentPage | QRAMMContext.answers | useContext(QRAMMContext) | ✓ WIRED | qramm-assessment.tsx: ctx.answers passed to DimensionTab |
| QuestionCard radio change | POST /api/qramm/assessment/draft | setAnswer triggers QRAMMProvider's debounced persistDraft | ✓ WIRED | onAnswerChange → ctx.setAnswer → persistDraft(300ms debounce) |
| ScorecardTab Calculate Score | POST /api/qramm/sessions/{id}/score | fetch with profile_multiplier | ✓ WIRED | `/api/qramm/sessions/${ctx.sessionId}/score` confirmed in ScorecardTab.tsx |
| ScorecardTab | QRAMMContext.scoreResult | ctx.setScoreResult after calculate | ✓ WIRED | `ctx.setScoreResult(json)` on success |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| qramm-assessment.tsx | questions (QuestionItem[]) | GET /api/qramm/questions → QRAMM_QUESTIONS (static catalog) | ✓ Yes — 120 questions from Python constant | ✓ FLOWING |
| qramm-assessment.tsx | session | useQRAMMSession → GET /api/qramm/sessions → DB query | ✓ Yes — real DB rows ordered by created_at | ✓ FLOWING |
| ScorecardTab.tsx | scoreResult | ctx.setScoreResult after POST /score → compute_overall_score + DB | ✓ Yes — scoring engine + DB query | ✓ FLOWING |
| QRAMMProvider.tsx | answers Map | useQRAMMSession seeds from GET /api/qramm/sessions/{id}/answers → QRAMMAnswer rows | ✓ Yes — real DB rows with suggested_answer/confirmed_at | ✓ FLOWING |
| qramm-profile.tsx | session (resume state) | useQRAMMSession → GET /api/qramm/sessions | ✓ Yes — real DB data | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| pytest migration + router tests | `python -m pytest tests/test_qramm_answer.py tests/test_qramm_router.py -x -q` | 33 passed in 0.52s | ✓ PASS |
| evidence_note column in models.py | `grep -c 'evidence_note = Column(Text'` | 1 | ✓ PASS |
| No datetime.utcnow() in router | `grep -c 'datetime.utcnow'` | 0 | ✓ PASS |
| Both Radar elements isAnimationActive={false} | `grep -c 'isAnimationActive={false}'` | 2 | ✓ PASS |
| ScorecardPlaceholder removed from assessment page | `grep -c 'ScorecardPlaceholder'` | 0 | ✓ PASS |
| No hex literals in QRAMM UI files | `grep -E '#[0-9a-fA-F]{3,8}'` on qramm-assessment.tsx, QuestionCard.tsx, ScorecardTab.tsx | No matches | ✓ PASS |
| fixture-qramm.json has 120 questions | Python json.load + len check | 120 | ✓ PASS |
| Both /qramm routes in a11y routes.json | Python json.load + slug/path check | Both present; 11 total routes | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QRAMM-08 | Plans 01, 04 | React QRAMM Assessment page presents 120 questions across 4 dimension tabs; 1-4 radio scale with maturity labels; evidence note field; progress tracker per dimension | ✓ SATISFIED | AssessmentPage + QuestionCard + PracticeAreaSection confirmed; Progress bar renders X of 30 answered; RadioGroup with maturity labels; evidence textarea in QuestionCard |
| QRAMM-09 | Plans 01, 03 | Org Profile wizard collects 5 fields; computes multiplier 0.8–1.5; stores in qramm_profiles | ✓ SATISFIED | OrgProfilePage with 5 fields confirmed; _compute_multiplier lookup table (0.8-1.5 clamped); QRAMMProfile ORM populated via POST /api/qramm/profiles |
| QRAMM-10 | Plans 01, 02, 04 | All 120 answers in top-level React context; debounced POST /draft on answer change; browser refresh restores answers | ✓ SATISFIED | QRAMMContext (Map state at app root); QRAMMProvider 300ms debounce; useQRAMMSession seeds Map from /sessions/{id}/answers on mount |
| QRAMM-11 | Plan 05 | Scorecard: recharts RadarChart (static SVG); dimension summary table; maturity distribution; scores only on explicit Calculate Score | ✓ SATISFIED | ScorecardTab.tsx: RadarChart from recharts; isAnimationActive={false} on both Radars; full dimension table with font-data cells; MATURITY_BADGE_CLASS badges; Calculate Score is sole trigger for POST /score |

All 4 requirements satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| qramm-assessment.tsx | 87 | `useState<QuestionItem[]>([])` — initial empty array | ℹ Info | Initial state only; populated by fetch within useEffect; loading state prevents render on empty; not a data stub |
| ScorecardTab.tsx | 47 | `const dist: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 }` | ℹ Info | Initial value guarded by `if (!ctx.scoreResult) return dist` — displays "—" in UI when no score; not a rendering stub |

No blockers or warnings found.

### Human Verification Required

#### 1. End-to-End Org Profile Form Submission

**Test:** Navigate to /qramm (via sidebar). Select options for all 5 fields (industry, org size, geographic scope, data sensitivity, at least one regulatory obligation). Click "Start Assessment".
**Expected:** Network tab shows POST /api/qramm/sessions (201), then POST /api/qramm/profiles (201). Browser navigates to /qramm/assessment. Sidebar QRAMM Assessment entry remains highlighted on the assessment URL.
**Why human:** Full form submission + routing + sidebar active-state require a running browser with both the FastAPI backend and Vite dev server.

#### 2. 120-Question Rendering Correctness

**Test:** On /qramm/assessment (after creating a session), click through CVI, SGRM, DPE, ITR tabs.
**Expected:** Each tab shows 3 default-open collapsible sections. Each section has exactly 10 question cards. Each card shows question text, a 4-option RadioGroup with maturity labels (Basic/Developing/Established/Optimizing), and an evidence textarea. Per-section header shows "0/10 answered". Per-dimension Progress bar shows "0 of 30 answered".
**Why human:** Visual rendering of 120 questions and collapsible open state cannot be verified without a browser.

#### 3. Debounced Persistence and Restore-on-Reload

**Test:** Select a radio on any non-auto-filled question. Wait 2 seconds. Refresh the page (hard reload).
**Expected:** The same radio is still selected after reload. Network tab on reload shows GET /api/qramm/sessions, then GET /api/qramm/sessions/{id}/answers. During the initial radio click, a single POST /api/qramm/assessment/draft fires within ~300ms (not on every keydown/change event).
**Why human:** Requires running backend + frontend; timing of debounce is observable only via browser network inspector.

#### 4. Auto-fill Badge State Transitions

**Test:** Requires a session with at least one QRAMMAnswer row where suggested_answer is non-null and confirmed_at is null (populated by the Phase 53 evidence bridge for CVI questions). On /qramm/assessment → CVI tab, locate such a question.
**Expected:** "Auto-filled from scan" badge (teal) is visible. Change the radio to a different value: badge changes to "Modified from scan suggestion" (amber). Click "Confirm Answer": badge disappears. Selecting the same value as the suggestion should still trigger the confirm flow.
**Why human:** Requires live CVI scan data or pre-seeded DB rows; badge state transitions involve the pendingValue local state which is only observable in a running browser.

#### 5. Scorecard Calculate Score and Chart Rendering

**Test:** From /qramm/assessment → Scorecard tab. Before clicking Calculate Score, verify axis labels (CVI, SGRM, DPE, ITR) are visible with muted callout text (no polygon). Click "Calculate Score". Wait for response.
**Expected:** Radar chart renders a filled polygon covering the 4 axes. Dimension Summary table shows numeric scores in Raw Score, Weighted Score, Completion % columns. Maturity Level column shows Badge labels. If an Org Profile industry was selected, a dashed benchmark polygon should also appear. Clicking Calculate Score again fires a second POST (button re-enables after first completes).
**Why human:** Visual chart rendering and recharts SVG output require browser; benchmark overlay depends on profile.industry from prior form submission.

### Gaps Summary

No automated gaps found. All 18 must-have truths are verified against actual codebase evidence. The 5 human verification items require a running browser + backend for full end-to-end confirmation of behaviors that are correct at the code level but cannot be asserted programmatically (visual rendering, timing, network inspector observations).

---

_Verified: 2026-05-07T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
