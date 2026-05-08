# Phase 54: QRAMM Assessment UI & Scorecard - Research

**Researched:** 2026-05-07
**Domain:** React dashboard UI — multi-tab assessment form, RadarChart scorecard, context state management, debounced API persistence
**Confidence:** HIGH — all findings verified against live codebase and installed packages

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Session Lifecycle**
- D-01: Auto-resume in-progress session on /qramm navigate; "New Assessment" requires explicit action
- D-02: Single active session at a time; "New Assessment" archives/deletes current session via POST /api/qramm/sessions
- D-03: Session ID in QRAMMContext; GET /api/qramm/sessions list called on mount to find most recent session

**Auto-fill Confirmation UX (QRAMM-14)**
- D-04: Auto-filled questions show "Auto-filled from scan" badge + pre-highlighted radio — answer_value remains null until confirmation
- D-05: Per-question Confirm button (not bulk). Two-step: select radio then click Confirm to write answer_value and dismiss badge
- D-06: Modified auto-fill updates badge text to "Modified from scan suggestion" until Confirm clicked

**Question Layout (QRAMM-08)**
- D-07: 3 collapsible sections per dimension tab; section headers show [practice area name] — [X/10 answered]
- D-08: All 3 sections expanded by default on tab load
- D-09: Question card: number + text, 1–4 radio scale, optional evidence note, Confirm button + badge if auto-filled

**Scorecard Access (QRAMM-11)**
- D-10: Scorecard is the 5th tab; always accessible (not gated)
- D-11: "Calculate Score" calls POST /api/qramm/sessions/{id}/score; NOT real-time
- D-12: Industry benchmarks hardcoded per sector; shows dash if no Org Profile

**Routing and Context Architecture**
- D-13: Two new routes: /qramm and /qramm/assessment; both in App.tsx and sidebar NAV_ITEMS
- D-14: QRAMMContext holds: sessionId, answers Map, profile, scoreResult
- D-15: 300ms debounced POST /api/qramm/assessment/draft; answers seeded from GET /api/qramm/sessions/{id}

### Claude's Discretion

None recorded — all scope decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Multiple sessions per client/engagement (future v4.8+)
- QRAMM Compliance Mapping View (Phase 55)
- PDF export with QRAMM section (Phase 56)
- Evidence bridge for SGRM, DPE, ITR dimensions (QRAMM-F01 — v4.8)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QRAMM-08 | 120-question assessment across 4 dimension tabs with 1–4 radio scale, maturity labels, evidence note field, and per-dimension progress tracker | shadcn RadioGroup + Collapsible (new installs); Progress (existing); all pattern verified |
| QRAMM-09 | Org Profile wizard: collect 5 fields, compute multiplier, store in qramm_profiles; redirect to assessment | QRAMMProfile model exists in DB; profile CRUD API endpoint is missing — must be added to qramm.py |
| QRAMM-10 | Top-level React context for all 120 answers; debounced POST /api/qramm/assessment/draft for persistence | QRAMMContext/QRAMMProvider pattern mirrors ScanContext; draft endpoint is missing — must be added; debounce via useRef/setTimeout (no library) |
| QRAMM-11 | Scorecard: 4-axis RadarChart (static SVG), dimension summary table, maturity distribution; explicit Calculate Score action | recharts RadarChart, PolarGrid, PolarAngleAxis, Radar confirmed installed; POST /api/qramm/sessions/{id}/score exists with correct response shape |
</phase_requirements>

---

## Summary

Phase 54 is a pure React UI build on top of a fully implemented backend (Phases 51 + 53). No new Python scanner logic is required. The work decomposes into: (1) three new shadcn component installs (radio-group, label, collapsible), (2) new React context (QRAMMContext/QRAMMProvider), (3) two new page components (/qramm Org Profile wizard, /qramm/assessment 5-tab assessment), (4) three new backend API endpoints that the UI requires but Phase 51 did not build, and (5) a11y baseline additions for both new routes.

The charting library (recharts 2.15.4 with RadarChart, PolarGrid, PolarAngleAxis, Radar) is already installed and verified. All required CSS token utilities (severity-accent-chip, severity-medium-chip, .font-data, quantum-safe, quantum-at-risk, quantum-vulnerable, severity-low) exist in index.css and tailwind.config.ts. No new design tokens are needed.

Three API endpoints are missing and must be added to quirk/dashboard/api/routes/qramm.py in this phase: GET /api/qramm/sessions (session list for auto-resume), POST /api/qramm/profiles (org profile create), and POST /api/qramm/assessment/draft (debounced answer persistence). Additionally, GET /api/qramm/sessions/{id}/answers is needed to load full answer state on page mount. The existing GET /api/qramm/sessions/{id} returns only answers_count, not the full answer rows needed for badge state rendering.

There is no toast library installed. The UI-SPEC requires a toast notification for save errors. The plan must either add sonner (lightweight, compatible with shadcn/Tailwind stack) or implement a minimal inline useState-based banner. [ASSUMED: sonner is the preferred approach given shadcn ecosystem alignment; requires planner decision.]

**Primary recommendation:** Build in 5 plans — (1) 3 missing API endpoints + backend tests, (2) QRAMMContext + session lifecycle hooks, (3) Org Profile wizard page, (4) Assessment 5-tab view with question cards, (5) Scorecard tab + a11y baseline additions.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session lifecycle (create, list, resume, delete) | API / Backend | — | State lives in SQLite; UI reads/writes via REST |
| Org profile CRUD | API / Backend | — | qramm_profiles table; multiplier computed server-side |
| Answer persistence (debounced draft) | API / Backend | Browser / Client | Server is source of truth; client debounces to reduce write frequency |
| QRAMMContext (in-memory answer state) | Browser / Client | — | Reduces round-trips; answers loaded once on mount, mutated locally |
| 5-tab assessment UI | Browser / Client | — | React component tree; no SSR |
| RadarChart rendering | Browser / Client | — | recharts SVG; rendered client-side; isAnimationActive={false} for PDF |
| Score computation | API / Backend | — | Weakest-link scoring in quirk/qramm/scoring.py; not client-side |
| Industry benchmark lookup | Browser / Client | — | Hardcoded static object per D-12; no API call needed |
| Auto-fill badge display | Browser / Client | — | Badge state derived from suggested_answer != null AND answer_value == null from API response |

---

## Standard Stack

### Core (already installed — verified against package.json)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| recharts | 2.15.4 | RadarChart, bar charts | [VERIFIED: package.json] |
| @radix-ui/react-tabs | 1.1.13 | 5-tab assessment layout | [VERIFIED: package.json] |
| @radix-ui/react-progress | 1.1.8 | Per-dimension progress bar | [VERIFIED: package.json] |
| @radix-ui/react-select | 2.2.6 | Org Profile wizard dropdowns | [VERIFIED: package.json] |
| @radix-ui/react-label | 2.1.8 | Form field labels | [VERIFIED: package.json] |
| lucide-react | 0.474.0 | Icons (ChevronDown, Loader2, ClipboardList) | [VERIFIED: package.json] |
| react-router-dom | 7.4.0 | useNavigate for post-wizard redirect | [VERIFIED: package.json] |

### New installs required

| Library | Current Version | Purpose | Source |
|---------|----------------|---------|--------|
| @radix-ui/react-radio-group | 1.3.8 | 1–4 maturity scale per question | [VERIFIED: npm view] |
| @radix-ui/react-collapsible | 1.1.12 | Practice area accordion sections | [VERIFIED: npm view] |

**shadcn add commands (generates component files in src/components/ui/):**
```bash
cd src/dashboard
npx shadcn add radio-group
npx shadcn add collapsible
```

Note: label is listed in UI-SPEC as new but @radix-ui/react-label 2.1.8 is already in package.json. Run `npx shadcn add label` to generate the shadcn wrapper if src/components/ui/label.tsx does not exist.

**Verify before running:**
```bash
ls src/dashboard/src/components/ui/radio-group.tsx  # should not exist
ls src/dashboard/src/components/ui/collapsible.tsx   # should not exist
ls src/dashboard/src/components/ui/label.tsx         # may not exist
```

### Toast notification (gap — decision needed)

There is no toast library installed. [ASSUMED: sonner is appropriate given shadcn ecosystem]

Option A — Install sonner (shadcn-recommended, minimal):
```bash
npm install sonner
# Add Toaster component to App.tsx root
```

Option B — Implement inline useState-based non-blocking banner (no new dependency). Simpler; matches project's minimal-dependency posture.

The UI-SPEC requires a "non-blocking toast notification (bottom-right)" for save errors and score errors. Both options satisfy this. The planner should pick one and lock it.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (/qramm)
  └─ OrgProfilePage
       └─ POST /api/qramm/profiles  ──> FastAPI ──> qramm_profiles (SQLite)
       └─ POST /api/qramm/sessions  ──> FastAPI ──> qramm_sessions + qramm_answers (30 CVI rows)
       └─ useNavigate("/qramm/assessment")

Browser (/qramm/assessment)
  └─ QRAMMProvider  (wraps all routes)
       └─ sessionId, answers Map, profile, scoreResult
  └─ AssessmentPage
       ├─ GET /api/qramm/sessions  (list, on mount)  ──> find most recent
       ├─ GET /api/qramm/sessions/{id}/answers  ──> seed full answer + badge state
       │
       ├─ [CVI tab]  [SGRM tab]  [DPE tab]  [ITR tab]  [Scorecard tab]
       │    └─ Collapsible practice area (3 per tab, all expanded by default)
       │         └─ QuestionCard (x10 per practice area)
       │              ├─ RadioGroup (1–4)
       │              ├─ evidence note textarea
       │              └─ Confirm button (if auto-filled)
       │
       ├─ answer change ──> 300ms debounce ──> POST /api/qramm/assessment/draft
       │
       └─ [Scorecard tab]
            ├─ RadarChart (recharts, isAnimationActive=false)
            ├─ Dimension summary table (.font-data for numerics)
            ├─ Maturity distribution bars
            └─ "Calculate Score" ──> POST /api/qramm/sessions/{id}/score
                                 ──> scoreResult stored in QRAMMContext
```

### Recommended Project Structure

```
src/dashboard/src/
├── context/
│   ├── QRAMMContext.tsx         # createContext + typed interface
│   └── QRAMMProvider.tsx        # useState wrapper; debounce logic
├── hooks/
│   └── useQRAMMSession.ts       # { session, answers, loading, error } hook
├── pages/
│   ├── qramm-profile.tsx        # OrgProfilePage — /qramm
│   └── qramm-assessment.tsx     # AssessmentPage — /qramm/assessment
├── components/ui/
│   ├── radio-group.tsx          # NEW via npx shadcn add radio-group
│   ├── collapsible.tsx          # NEW via npx shadcn add collapsible
│   └── label.tsx                # NEW via npx shadcn add label (if missing)
└── types/
    └── api.ts                   # Extend with QRAMM API response types
```

Backend:
```
quirk/dashboard/api/routes/qramm.py   # Add 4 missing endpoints
tests/test_qramm_router.py            # Add tests for new endpoints
```

### Pattern 1: QRAMMContext (mirrors ScanContext/ScanProvider)

```typescript
// Source: src/dashboard/src/context/ScanContext.tsx (verified live)
// QRAMMContext.tsx
import { createContext } from "react"

export interface AnswerState {
  answer_value: 1 | 2 | 3 | 4 | null
  suggested_answer: 1 | 2 | 3 | 4 | null
  confirmed_at: string | null   // ISO8601
  evidence_note: string
}

export interface OrgProfile {
  industry: string
  org_size: string
  geographic_scope: string
  data_sensitivity: string
  regulatory_obligations: string[]
  multiplier: number
}

export interface ScoreResult {
  overall: number
  maturity: string
  dimensions: Record<string, { score: number; weighted: number }>
  profile_multiplier: number
}

interface QRAMMContextValue {
  sessionId: number | null
  setSessionId: (id: number | null) => void
  answers: Map<number, AnswerState>
  setAnswer: (questionNumber: number, state: Partial<AnswerState>) => void
  profile: OrgProfile | null
  setProfile: (p: OrgProfile | null) => void
  scoreResult: ScoreResult | null
  setScoreResult: (r: ScoreResult | null) => void
}

export const QRAMMContext = createContext<QRAMMContextValue>({ ... })
```

### Pattern 2: Debounced Draft Persistence (no library)

```typescript
// Source: [ASSUMED — standard React pattern with useRef]
import { useRef, useCallback } from "react"

function useDebouncedDraft(sessionId: number | null, delay = 300) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const persist = useCallback((questionNumber: number, answerValue: number | null, evidenceNote: string) => {
    if (!sessionId) return
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(async () => {
      try {
        await fetch("/api/qramm/assessment/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            question_number: questionNumber,
            answer_value: answerValue,
            evidence_note: evidenceNote,
          }),
        })
      } catch {
        // surface toast error
      }
    }, delay)
  }, [sessionId, delay])

  return { persist }
}
```

### Pattern 3: RadarChart (static SVG for PDF compatibility)

```typescript
// Source: recharts node_modules verified — RadarChart, PolarGrid, PolarAngleAxis, Radar confirmed
import { RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts"

// Key: isAnimationActive={false} required per QRAMM-11 (PDF embed downstream in Phase 56)
<RadarChart
  width={320}
  height={320}
  data={[
    { axis: "CVI", score: dims.CVI.score, benchmark: benchmarks.cvi },
    { axis: "SGRM", score: dims.SGRM.score, benchmark: benchmarks.sgrm },
    { axis: "DPE", score: dims.DPE.score, benchmark: benchmarks.dpe },
    { axis: "ITR", score: dims.ITR.score, benchmark: benchmarks.itr },
  ]}
  aria-label="QRAMM radar chart showing dimension scores"
  role="img"
>
  <PolarGrid stroke="var(--ds-border)" />
  <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--ds-text-muted)", fontSize: 12 }} />
  <Radar
    name="Assessment"
    dataKey="score"
    fill="rgba(75, 168, 168, 0.20)"
    stroke="hsl(var(--accent))"
    isAnimationActive={false}
  />
  <Radar
    name="Benchmark"
    dataKey="benchmark"
    fill="rgba(110, 122, 149, 0.15)"
    stroke="hsl(var(--muted-foreground))"
    strokeDasharray="4 2"
    isAnimationActive={false}
  />
</RadarChart>
```

### Pattern 4: App.tsx Provider + Route Registration

```typescript
// Source: src/dashboard/src/App.tsx (verified live)
// Wrap QRAMMProvider INSIDE ScanProvider:
<ScanProvider>
  <QRAMMProvider>       {/* NEW */}
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
          {/* existing routes... */}
          <Route path="/qramm" element={<OrgProfilePage />} />            {/* NEW */}
          <Route path="/qramm/assessment" element={<AssessmentPage />} /> {/* NEW */}
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QRAMMProvider>
</ScanProvider>
```

### Pattern 5: Sidebar NAV_ITEMS Addition

```typescript
// Source: src/dashboard/src/components/sidebar.tsx (verified live)
// Add to NAV_ITEMS array:
{ path: "/qramm", label: "QRAMM Assessment", Icon: ClipboardList }
// Import ClipboardList from "lucide-react" — available in 0.474.0
```

The current sidebar active-state check uses `location.pathname === path`. For `/qramm/assessment`, this will NOT highlight the QRAMM nav item. Fix: use `location.pathname.startsWith(path)` for the QRAMM entry only, or add a separate nav entry for the assessment route.

### Anti-Patterns to Avoid

- **Hardcoded hex/hsl color literals:** All colors use CSS variables. Never use `#4ba8a8` or `hsl(180, 37%, 47%)` directly in component JSX. Use `hsl(var(--accent))` or Tailwind token classes.
- **RadarChart with animation:** isAnimationActive must be false on both Radar elements — downstream PDF export (Phase 56) requires static SVG.
- **Real-time score recalculation:** Scores must only update on explicit "Calculate Score" button click (D-11). Do not call the score endpoint on answer change.
- **answer_value written before Confirm:** For auto-filled questions (suggested_answer != null), answer_value must remain null until the Confirm button is clicked. Writing it on radio selection alone violates D-04/D-05.
- **Bulk Accept All:** No "Accept All" button — per D-05, each auto-filled question requires individual Confirm.
- **datetime.utcnow() in new Python code:** Phase 51 (DEBT-01) established that all timestamps use datetime.now(timezone.utc). New endpoints in this phase must follow the same pattern.

---

## Missing API Endpoints (Must Be Added in This Phase)

The following endpoints are required by the UI context decisions but do not exist in quirk/dashboard/api/routes/qramm.py.

### Gap 1: GET /api/qramm/sessions — Session List

**Required by:** D-03 (auto-resume: find most recent session on mount)

**Response shape:**
```python
class SessionSummary(BaseModel):
    session_id: int
    org_name: Optional[str]
    created_at: Optional[str]
    status: Optional[str]
    answers_count: int

# Returns: List[SessionSummary], ordered by created_at DESC
```

**Implementation:** Query QRAMMSession ordered by created_at DESC. The UI only needs index 0 (most recent).

### Gap 2: POST /api/qramm/profiles — Org Profile Create

**Required by:** QRAMM-09 (Org Profile wizard stores a qramm_profiles row)

**Request shape:**
```python
class CreateProfileRequest(BaseModel):
    session_id: int
    industry: str
    org_size: str
    geographic_scope: str
    data_sensitivity: str
    regulatory_obligations: List[str]  # serialized to JSON in DB

# Returns: { profile_id, session_id, multiplier }
```

**Multiplier computation:** The QRAMMProfile.multiplier column exists but Phase 51 never implemented the computation logic. [ASSUMED: a simple lookup table per sector + data sensitivity is appropriate.] After creating the profile, the router must also update QRAMMSession.profile_id to link the profile to the session.

### Gap 3: POST /api/qramm/assessment/draft — Single-Answer Debounced Persistence

**Required by:** QRAMM-10, D-15

**Request shape:**
```python
class DraftAnswerRequest(BaseModel):
    session_id: int
    question_number: int = Field(ge=1, le=120)
    answer_value: Optional[int] = Field(default=None, ge=1, le=4)
    evidence_note: Optional[str] = Field(default=None, max_length=2000)

# Returns: { saved: True }
```

**Implementation note:** This is a thin wrapper over the existing save_answers upsert logic — upserts a single qramm_answers row. The evidence_note column does not currently exist in QRAMMAnswer (see Pitfall 1 below). The plan must add it.

### Gap 4: GET /api/qramm/sessions/{id}/answers — Full Answer Read

**Required by:** D-15 (answers seeded from session load on page mount including badge state)

The existing GET /api/qramm/sessions/{id} returns only answers_count. The UI needs full answer rows (including suggested_answer, confirmed_at, answer_value) to render badge state correctly.

**Response shape:**
```python
class AnswerRead(BaseModel):
    question_number: int
    answer_value: Optional[int]
    suggested_answer: Optional[int]
    confirmed_at: Optional[str]
    evidence_note: Optional[str]

# Returns: List[AnswerRead]
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accordion sections | Custom div toggle | shadcn Collapsible (Radix UI) | Keyboard nav (Enter/Space), aria-expanded, focus management |
| Radio buttons | input type=radio group | shadcn RadioGroup + RadioGroupItem | Arrow-key navigation, group semantics, consistent styling |
| Radar chart | SVG path math | recharts RadarChart | Already installed; handles coordinate math, axis labeling |
| Debounce | lodash.debounce import | useRef + setTimeout pattern | No new dependency needed for a single use case |
| Form field labels | html label only | shadcn Label (Radix) | Correct htmlFor wiring, accessibility |
| Progress bars | Custom div | shadcn Progress (Radix) | aria-valuenow / aria-valuemax provided automatically |

**Key insight:** Every interactive element in this phase has an exact shadcn/Radix counterpart. Custom implementations would miss keyboard navigation and ARIA semantics that Radix provides for free.

---

## Common Pitfalls

### Pitfall 1: evidence_note Column Does Not Exist in QRAMMAnswer

**What goes wrong:** The UI-SPEC includes an evidence note textarea per question, and D-15 specifies it is persisted via the draft endpoint. The QRAMMAnswer ORM model does NOT have an evidence_note column — Phase 51 pre-provisioned suggested_answer, confirmed_at, evidence_source but not a freeform evidence_note.

**Why it happens:** The evidence note field appears in the UI-SPEC but the backend schema from Phase 51 predates it.

**How to avoid:** Wave 0 plan must add `evidence_note = Column(Text, nullable=True)` to QRAMMAnswer in quirk/models.py and add a corresponding migration call in quirk/db.py following the `_ensure_phase46_columns()` pattern.

**Warning signs:** Draft endpoint accepts evidence_note in the request body but the ORM has no column to store it.

### Pitfall 2: score_session Ignores profile_multiplier Unless profile_id Is Linked

**What goes wrong:** POST /api/qramm/sessions/{id}/score accepts an optional profile_multiplier in its request body, but QRAMMSession.profile_id is always NULL if the profile create endpoint does not update it. The scorecard will always use multiplier 1.0.

**How to avoid:** POST /api/qramm/profiles must update QRAMMSession.profile_id. The frontend "Calculate Score" call should pass the multiplier from QRAMMContext.profile.multiplier in the ScoreRequest body.

**Warning signs:** Calculate Score returns profile_multiplier = 1.0 even when an org profile was submitted.

### Pitfall 3: Badge State Derived from Stale Context

**What goes wrong:** If QRAMMContext seeds answers from the API on mount but only stores answer_value, the badge will never appear because suggested_answer is unknown client-side.

**How to avoid:** The GET /api/qramm/sessions/{id}/answers response (Gap 4) must include suggested_answer and confirmed_at. The AnswerState in context must store all four fields (answer_value, suggested_answer, confirmed_at, evidence_note), not just answer_value.

**Warning signs:** Auto-fill badges never appear for CVI questions even though Phase 53 populated suggested_answer values.

### Pitfall 4: RadarChart Renders as Invisible Polygon When All Scores Are 0

**What goes wrong:** Before "Calculate Score" is clicked, all score values are 0. recharts RadarChart with all-zero data renders a degenerate point at the center, which is invisible. The UI-SPEC specifies the unscored state should show axis labels plus a callout text.

**How to avoid:** Render the Radar children conditionally — when scoreResult is null, omit the Radar fill elements and show only PolarGrid + PolarAngleAxis, plus the muted callout text below. Do not pass score: 0 to a Radar with a 1–4 domain.

**Warning signs:** Scorecard tab shows what looks like an empty chart with no axis labels visible.

### Pitfall 5: Collapsible Default-Expanded State

**What goes wrong:** Radix Collapsible is closed by default. D-08 requires all 3 sections expanded on tab load. If the developer uses `open` (controlled) instead of `defaultOpen` (uncontrolled), they need to manage state for all 12 sections (4 tabs x 3 each).

**How to avoid:** Use `<Collapsible defaultOpen={true}>` (uncontrolled). Only upgrade to controlled state if programmatic collapse is required (it is not).

**Warning signs:** Practice area sections load collapsed; user must click to expand before seeing questions.

### Pitfall 6: Sidebar Active State for Nested Routes

**What goes wrong:** The sidebar marks items active with `location.pathname === path`. For /qramm/assessment, the QRAMM sidebar item (path /qramm) will NOT be highlighted.

**How to avoid:** Change the active check to `location.pathname.startsWith(path)` for the QRAMM item. The existing pattern uses strict equality — the QRAMM item needs a special case.

**Warning signs:** QRAMM assessment page shows no active sidebar item highlighted.

### Pitfall 7: A11y Baseline for New Routes Not Added

**What goes wrong:** src/dashboard/tests/a11y/routes.json does not include /qramm or /qramm/assessment. The a11y harness will not scan these routes and the axe test will miss violations.

**How to avoid:** Add both routes to routes.json and add QRAMM API fixture responses to the Vite a11y middleware in vite.config.ts. Run `npm run a11y:baseline` after the UI is built to capture new baselines.

**Warning signs:** A11y check passes with no new routes; CI never tests the new pages.

---

## Code Examples

### Industry Benchmark Static Lookup

```typescript
// Source: [ASSUMED — representative community averages; verify or disclaim before use]
// Place in: src/dashboard/src/lib/qramm-benchmarks.ts
export const INDUSTRY_BENCHMARKS: Record<string, { cvi: number; sgrm: number; dpe: number; itr: number }> = {
  financial_services: { cvi: 3.1, sgrm: 2.8, dpe: 2.5, itr: 2.9 },
  healthcare:         { cvi: 2.6, sgrm: 2.4, dpe: 2.2, itr: 2.5 },
  government:         { cvi: 2.8, sgrm: 2.9, dpe: 2.4, itr: 2.7 },
  technology:         { cvi: 3.0, sgrm: 2.6, dpe: 2.7, itr: 3.1 },
  retail:             { cvi: 2.2, sgrm: 2.0, dpe: 2.3, itr: 2.1 },
  energy:             { cvi: 2.4, sgrm: 2.5, dpe: 2.1, itr: 2.3 },
  other:              { cvi: 2.0, sgrm: 2.0, dpe: 2.0, itr: 2.0 },
}
```

Note: [ASSUMED: values above are representative placeholders — exact values need sourcing from CSNP QRAMM community averages]

### Maturity Level Color Badge

```typescript
// Source: tailwind.config.ts verified — quantum-safe, quantum-at-risk, quantum-vulnerable, severity-low all exist
const MATURITY_BADGE_CLASS: Record<number, string> = {
  4: "bg-quantum-safe/20 text-quantum-safe border border-quantum-safe/30",           // Optimizing
  3: "bg-severity-low/20 text-severity-low border border-severity-low/30",           // Established
  2: "bg-quantum-at-risk/20 text-quantum-at-risk border border-quantum-at-risk/30",  // Developing
  1: "bg-quantum-vulnerable/20 text-quantum-vulnerable border border-quantum-vulnerable/30", // Basic
}
const MATURITY_LABEL: Record<number, string> = {
  4: "Optimizing", 3: "Established", 2: "Developing", 1: "Basic"
}
```

### Practice Area Name Map

```typescript
// Source: [VERIFIED: quirk/qramm/questions.py comments, read live]
export const PRACTICE_AREA_NAMES: Record<string, string> = {
  "1.1": "Cryptographic Discovery & Inventory Management",
  "1.2": "Vulnerability Assessment & Classification",
  "1.3": "Cryptographic Dependency Mapping",
  "2.1": "Executive Leadership & Policy Management",
  "2.2": "Risk & Compliance Management",
  "2.3": "Third-Party Risk Management",
  "3.1": "Data Classification",
  "3.2": "Storage Security",
  "3.3": "Transit Security",
  "4.1": "Infrastructure",
  "4.2": "Implementation",
  "4.3": "Testing & Validation",
}
```

### Existing API Fetch Pattern (from executive.tsx)

```typescript
// Source: src/dashboard/src/pages/executive.tsx (verified live)
const resp = await fetch("/api/qramm/sessions", { method: "GET" })
if (!resp.ok) {
  setError(`API error: ${resp.status} ${resp.statusText}`)
  return
}
const json = await resp.json()
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Hardcoded inline color values | CSS variables via hsl(var(--token)) | No hardcoded colors in new components |
| datetime.utcnow() | datetime.now(timezone.utc) | Python 3.12+ compliant — required per DEBT-01 |
| input type=radio | shadcn RadioGroup + RadioGroupItem | Full keyboard nav + ARIA |
| Manual accordion div | shadcn Collapsible | aria-expanded provided by Radix |
| react-router-dom v6 | react-router-dom v7 (7.4.0) | useNavigate API unchanged; no migration needed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sonner is appropriate toast library for save/score error notifications | Standard Stack | Could use simpler useState banner; no functional risk, just DX choice |
| A2 | Industry benchmark values (financial_services: CVI 3.1, etc.) are representative placeholders | Code Examples | Wrong benchmark values mislead consultants; must be sourced or disclaimed |
| A3 | evidence_note column must be added to QRAMMAnswer in this phase | Missing API Endpoints | If deferred, evidence note textarea UI cannot persist; field would be display-only |
| A4 | Profile multiplier uses a simple sector + sensitivity lookup table in the router | Missing API Endpoints | A different formula changes the router implementation; needs confirmation or spec |
| A5 | GET /api/qramm/sessions/{id}/answers (separate endpoint) is preferred over extending SessionRead | Architecture Patterns | Larger payload at mount if embedded; either approach works functionally |

---

## Open Questions

1. **Evidence note column**
   - What we know: QRAMMAnswer has no evidence_note column; the UI renders one per question
   - What's unclear: Is it in scope for Phase 54 or deferred (display-only textarea, no persistence)?
   - Recommendation: Add the column in this phase — omitting it means the draft endpoint cannot honor it and the field would silently discard user input

2. **Profile multiplier formula**
   - What we know: multiplier range is 0.8–1.5; QRAMMProfile has industry, org_size, data_sensitivity fields
   - What's unclear: The exact computation formula was not implemented in Phase 51 (column exists but is always NULL)
   - Recommendation: Use a static lookup table; document it as an approximation in comments

3. **Benchmark values**
   - What we know: D-12 specifies hardcoded values keyed by sector; example given is financial_services CVI 3.1
   - What's unclear: Whether the full 7-sector x 4-dimension table has been sourced
   - Recommendation: Define a representative table in src/lib/qramm-benchmarks.ts with source comment attributing to CSNP QRAMM community averages

4. **Toast vs. inline banner**
   - What we know: UI-SPEC calls for non-blocking toast notification (bottom-right) for save and score errors
   - What's unclear: Whether adding sonner is acceptable or the project prefers zero new npm dependencies
   - Recommendation: Add sonner — it is the shadcn-standard toast and adds approximately 8KB gzipped

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | shadcn add, build | Yes | (project running) | — |
| recharts | RadarChart rendering | Yes | 2.15.4 | — |
| @radix-ui/react-radio-group | RadioGroup component | Not yet in node_modules | 1.3.8 (registry) | — |
| @radix-ui/react-collapsible | Collapsible component | Not yet in node_modules | 1.1.12 (registry) | — |
| Python pytest | Backend endpoint tests | Yes | (existing test suite) | — |

**Missing dependencies with no fallback:**
- @radix-ui/react-radio-group and @radix-ui/react-collapsible — installed via `npx shadcn add radio-group collapsible` (Wave 0)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest (existing) |
| Python quick run | `python -m pytest tests/test_qramm_router.py -x` |
| Python full suite | `python -m pytest tests/ -x` |
| Frontend framework | Puppeteer + axe-core a11y harness |
| Frontend quick run | `npm run a11y:check` (from src/dashboard/) |
| Frontend full suite | `npm run build && npm run a11y:check` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QRAMM-08 | 120 questions rendered across 4 tabs | a11y + manual | `npm run a11y:check` (after baseline) | No — Wave 0 |
| QRAMM-09 | Org Profile form submits and stores qramm_profiles row | unit | `pytest tests/test_qramm_router.py::test_create_profile -x` | No — Wave 0 |
| QRAMM-10 | Draft endpoint persists single answer; round-trip via session load | unit | `pytest tests/test_qramm_router.py::test_draft_answer -x` | No — Wave 0 |
| QRAMM-11 | Score endpoint returns dimensions + overall + maturity | unit | `pytest tests/test_qramm_router.py::test_score_session_full_120_answers -x` | Yes (extends existing) |
| QRAMM-14 | Auto-fill badge visible when suggested_answer != null | a11y + manual | `npm run a11y:check` with QRAMM fixture | No — Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_qramm_router.py` — add tests for: GET /api/qramm/sessions (list), POST /api/qramm/profiles, POST /api/qramm/assessment/draft, GET /api/qramm/sessions/{id}/answers
- [ ] `src/dashboard/tests/a11y/routes.json` — add qramm (path /qramm) and qramm-assessment (path /qramm/assessment)
- [ ] `src/dashboard/tests/a11y/fixture-qramm.json` — mock responses for QRAMM API endpoints used by Vite a11y middleware
- [ ] `src/dashboard/tests/a11y/baseline-qramm.json` and `baseline-qramm-assessment.json` — captured via `npm run a11y:baseline` after Wave 3+ implementation

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic Field(ge=1, le=4) on answer_value; max_length on text fields |
| V4 Access Control | no | No authentication in current QUIRK architecture — single-user tool |
| V2 Authentication | no | Same — no auth layer in scope |
| V6 Cryptography | no | No new cryptographic operations |

**Threat pattern:** The draft endpoint accepts user-supplied evidence_note text (free text up to 2000 chars). React JSX auto-escapes string values, so rendering evidence_note as JSX text is safe. Do not use innerHTML or unsafe rendering APIs to display evidence note values. [ASSUMED: safe — no unsafe rendering patterns found in existing pages]

---

## Sources

### Primary (HIGH confidence)
- `quirk/dashboard/api/routes/qramm.py` — live endpoint inventory, Pydantic models, session lifecycle [VERIFIED: codebase read]
- `quirk/models.py` — QRAMMSession, QRAMMAnswer, QRAMMProfile ORM schemas (all columns verified) [VERIFIED: codebase read]
- `quirk/qramm/questions.py` — full 120-question catalog, practice area structure (1.1–4.3), dimension distribution [VERIFIED: codebase read]
- `quirk/qramm/evidence_bridge.py` — suggested_answer population, which fields it writes [VERIFIED: codebase read]
- `src/dashboard/src/context/ScanContext.tsx` + ScanProvider.tsx — exact pattern QRAMMContext must mirror [VERIFIED: codebase read]
- `src/dashboard/src/App.tsx` — routing structure, provider nesting [VERIFIED: codebase read]
- `src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS shape and active state logic [VERIFIED: codebase read]
- `src/dashboard/package.json` — all installed npm packages and versions [VERIFIED: codebase read]
- `src/dashboard/src/index.css` — .severity-accent-chip, .severity-medium-chip, .font-data confirmed present [VERIFIED: codebase read]
- `src/dashboard/tailwind.config.ts` — quantum-safe, quantum-at-risk, quantum-vulnerable, severity-low tokens confirmed [VERIFIED: codebase read]
- `src/dashboard/tests/a11y/routes.json` — confirmed /qramm and /qramm/assessment are absent [VERIFIED: codebase read]
- recharts node_modules — RadarChart, PolarGrid, PolarAngleAxis, Radar confirmed exported [VERIFIED: node -e require()]
- npm registry — @radix-ui/react-radio-group 1.3.8, @radix-ui/react-collapsible 1.1.12 [VERIFIED: npm view]

### Secondary (MEDIUM confidence)
- `src/dashboard/src/pages/executive.tsx` — POST pattern for API calls [VERIFIED: codebase read]
- `src/dashboard/src/hooks/useScanData.ts` — { data, loading, error } hook pattern to mirror [VERIFIED: codebase read]
- `.planning/phases/54-qramm-assessment-ui-scorecard/54-CONTEXT.md` — locked decisions D-01 through D-15 [CITED: planning artifact]
- `.planning/phases/54-qramm-assessment-ui-scorecard/54-UI-SPEC.md` — component contracts, spacing, typography, color, copywriting [CITED: planning artifact]

### Tertiary (LOW confidence — needs validation)
- Industry benchmark values (A2) — representative placeholders, not sourced from CSNP
- Profile multiplier formula (A4) — assumed lookup table, formula not specified in any Phase 51 artifact

---

## Metadata

**Confidence breakdown:**
- Missing API endpoints: HIGH — gap confirmed by direct router inspection
- Standard stack (recharts, radix): HIGH — verified against installed node_modules
- Architecture patterns: HIGH — derived from live ScanContext/ScanProvider code
- Industry benchmark values: LOW — placeholder values, no official CSNP source verified
- Profile multiplier formula: LOW — column exists, computation not implemented in Phase 51

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable stack; recharts, shadcn versions unlikely to change in 30 days)
