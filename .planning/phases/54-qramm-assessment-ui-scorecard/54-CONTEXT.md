---
phase: 54-qramm-assessment-ui-scorecard
type: context
status: active
source: /gsd-discuss-phase 54
updated: 2026-05-07
milestone: v4.7 Governance & Compliance Platform
requirements: [QRAMM-08, QRAMM-09, QRAMM-10, QRAMM-11]
---

# Phase 54: QRAMM Assessment UI & Scorecard - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 54 delivers a complete consultant-facing UI flow within the QUIRK dashboard:

1. **Org Profile wizard** — collects industry sector, org size, geographic scope, data sensitivity, and regulatory obligations; stores a `qramm_profiles` row; redirects to the assessment view
2. **120-question assessment** — 4 dimension tabs (CVI, SGRM, DPE, ITR), questions grouped by practice area (3 areas × 10 questions each), per-question 1–4 radio scale, evidence note field, auto-fill badge + explicit Confirm UX
3. **QRAMM Scorecard** — 5th tab within the assessment view; 4-axis RadarChart (static SVG), dimension summary table, maturity distribution; scores update only on explicit "Calculate Score" action

**In scope:**
- New React pages: Org Profile wizard (`/qramm`), Assessment view (`/qramm/assessment`)
- New `QRAMMContext` / `QRAMMProvider` above all route changes (mirrors `ScanContext`/`ScanProvider` pattern)
- Sidebar entry + App.tsx routes for `/qramm` and `/qramm/assessment`
- `POST /api/qramm/assessment/draft` debounced persistence (QRAMM-10)
- Auto-fill badge display + per-question Confirm button (QRAMM-14)
- RadarChart scorecard tab using existing `recharts` `RadarChart` component (QRAMM-11)
- Industry benchmark lookup (hardcoded per sector from Org Profile)

**Out of scope:**
- Multiple sessions per client (deferred — future phase)
- QRAMM Compliance Mapping View (Phase 55)
- PDF export with QRAMM section (Phase 56)
- Evidence bridge for SGRM, DPE, ITR dimensions (QRAMM-F01 — v4.8)

</domain>

<decisions>
## Implementation Decisions

### Session Lifecycle

- **D-01:** When a consultant navigates to `/qramm` and an in-progress session exists, auto-resume it — load all saved answers from `qramm_answers` and restore them into `QRAMMContext`. Starting fresh requires an explicit "New Assessment" action.
- **D-02:** Single active session at a time. "New Assessment" archives (or deletes) the current session and creates a fresh one via `POST /api/qramm/sessions`. There is no session picker UI in this phase.
- **D-03:** Session ID is persisted in `QRAMMContext` state; `GET /api/qramm/sessions` (list) is called on mount to find the most recent session.

### Auto-fill Confirmation UX (QRAMM-14)

- **D-04:** Auto-filled questions (those with `suggested_answer` from the evidence bridge) display an "Auto-filled from scan" badge and a pre-highlighted radio button (showing the suggested value) — but `answer_value` remains null until explicit confirmation.
- **D-05:** Each auto-filled question has a dedicated **Confirm** button. Two-step flow: consultant selects a radio (can accept the suggestion or override it), then clicks Confirm to write `answer_value` and dismiss the badge. There is no bulk "Accept all" action.
- **D-06:** When a consultant modifies an auto-filled question (selects a different radio value), the badge updates to "Modified from scan suggestion" until Confirm is clicked, at which point the badge is removed entirely.

### Question Layout Within Tabs (QRAMM-08)

- **D-07:** Each dimension tab renders questions grouped by practice area — 3 collapsible sections per tab, each containing 10 questions. Section headers show: `[practice area name] — [X/10 answered]`.
- **D-08:** All 3 practice area sections are **expanded by default** when a tab loads. No collapse-on-load logic.
- **D-09:** Each question card renders: question number + text, 1–4 radio scale (`Basic / Developing / Established / Optimizing`), optional evidence note text field, and (if auto-filled) the Confirm button + badge.

### Scorecard Access (QRAMM-11)

- **D-10:** Scorecard is the **5th tab** in the assessment view: `[ CVI ] [ SGRM ] [ DPE ] [ ITR ] [ Scorecard ]`. It is always accessible — a consultant can check the scorecard at any point, even with partial answers.
- **D-11:** "Calculate Score" is a button inside the Scorecard tab that calls `POST /api/qramm/sessions/{id}/score`. Scores are NOT recalculated in real time as questions are answered.
- **D-12:** The dimension summary table columns: Raw Score / Weighted Score / Industry Benchmark / Maturity Level / Completion %. Industry benchmarks are hardcoded per industry sector — a static lookup keyed by the sector selected in the Org Profile wizard (e.g., `financial_services → CVI: 3.1, SGRM: 2.8, DPE: 2.5, ITR: 2.9`). If no Org Profile exists yet, benchmark column shows "—".

### Routing & Context Architecture

- **D-13:** Two new routes: `/qramm` (Org Profile wizard page) and `/qramm/assessment` (120-question + scorecard tab page). Both added to `App.tsx` and `sidebar.tsx` NAV_ITEMS.
- **D-14:** `QRAMMContext` holds: `sessionId`, `answers` (map of questionNumber → `{answer_value, suggested_answer, confirmed_at, evidence_note}`), `profile` (org profile data), `scoreResult` (null until calculated). `QRAMMProvider` wraps inside `ScanProvider` in App.tsx.
- **D-15:** Answer persistence uses a debounced `POST /api/qramm/assessment/draft` (300ms debounce) triggered on every answer change. On page load, answers are seeded from `GET /api/qramm/sessions/{id}`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 54 Requirements
- `.planning/REQUIREMENTS.md` §QRAMM-08, QRAMM-09, QRAMM-10, QRAMM-11 — locked requirements for this phase
- `.planning/ROADMAP.md` §Phase 54 — goal, success criteria, dependency chain

### Backend API Surface (Phase 51 + 53)
- `.planning/phases/51-qramm-core-infrastructure/51-CONTEXT.md` — ORM models, router design, SESSION_BRACKET, scoring engine decisions
- `.planning/phases/53-qramm-evidence-bridge/53-CONTEXT.md` — evidence bridge decisions, auto-fill badge behavior spec (D-04 through D-09 in that file)
- `quirk/qramm/` — live implementation: `questions.py` (120-entry catalog), `scoring.py`, `evidence_bridge.py`
- `quirk/dashboard/api/routes/qramm.py` — FastAPI router: all `/api/qramm/*` endpoints this phase consumes

### Frontend Patterns
- `src/dashboard/src/App.tsx` — routing pattern; add new routes here
- `src/dashboard/src/components/sidebar.tsx` — NAV_ITEMS pattern; add QRAMM sidebar entry here
- `src/dashboard/src/context/ScanContext.tsx` + `ScanProvider.tsx` — mirror this pattern for `QRAMMContext`/`QRAMMProvider`
- `src/dashboard/src/components/ui/tabs.tsx` — shadcn Tabs component; reuse for 5-tab assessment view
- `src/dashboard/src/components/ui/chart.tsx` — recharts wrapper; `RadarChart` from `recharts` is already installed

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/src/components/ui/tabs.tsx` — shadcn Radix Tabs; use for the 5-tab assessment view (CVI / SGRM / DPE / ITR / Scorecard)
- `src/dashboard/src/components/ui/card.tsx` — Card component with shadow/rounded variants; use for question cards and scorecard panels
- `src/dashboard/src/components/ui/progress.tsx` — Progress bar; use for per-dimension completion counters
- `src/dashboard/src/components/ui/badge.tsx` — Badge component; use for the "Auto-filled from scan" badge (already exists)
- `src/dashboard/src/components/ui/select.tsx` — Dropdown; use for Org Profile wizard fields (industry sector, org size, etc.)
- `src/dashboard/src/components/ui/input.tsx` — Input; use for evidence note fields
- `recharts` (`RadarChart`, `PolarGrid`, `PolarAngleAxis`, `Radar`) — already in `package.json`; used by chart.tsx wrapper

### Established Patterns
- **Context shape**: `ScanContext` is a `createContext` with a typed interface + `ScanProvider` that wraps with `useState`. `QRAMMContext` follows the same pattern. Both are declared in `src/dashboard/src/context/`.
- **Page component shape**: Pages export a named function (e.g., `export function AssessmentPage()`). Import in `App.tsx`, add `<Route path="..." element={<AssessmentPage />} />`.
- **API data fetching**: Pages use hooks like `useScanData()` that call `/api/...` endpoints. New `useQRAMMSession()` hook should follow the same `{ data, loading, error }` return shape.
- **CSS variables**: All color tokens use CSS variables (e.g., `hsl(var(--accent))`). Never use hardcoded hex/hsl values in new components.

### Integration Points
- `App.tsx`: Add `QRAMMProvider` around `<Routes>` (inside `ScanProvider`); add two new `<Route>` entries
- `sidebar.tsx`: Add a new entry to `NAV_ITEMS` array for `/qramm` with a suitable lucide-react icon (e.g., `ClipboardList` or `BarChart3`)
- `quirk/dashboard/api/routes/qramm.py`: The `POST /api/qramm/assessment/draft` endpoint needed for QRAMM-10 may not exist yet — planner should verify and add if missing
- `quirk/dashboard/api/app.py`: QRAMM router is already registered (Phase 51)

</code_context>

<specifics>
## Specific Ideas

- **5-tab layout** with the Scorecard always accessible (not gated behind completion) — confirmed in discussion.
- **Industry benchmark hardcoded lookup**: a static JS/TS object mapping sector → `{cvi, sgrm, dpe, itr}` benchmark scores. The data is representative community averages — not derived from any live API.
- **Confirm button placement**: appears below the radio group for auto-filled questions, visually adjacent to the badge. One button per question (not per practice area).
- **"New Assessment"** button — placed in the assessment page header or as a secondary action in the Scorecard tab. Archives or deletes the current session before creating a new one.

</specifics>

<deferred>
## Deferred Ideas

- **Multiple sessions per client/engagement** — user requested this as a future feature. In Phase 54, only a single active session exists. A future phase would add a session picker, session naming (e.g., by client or date), and a session history list. Noted for v4.8 or later backlog.

</deferred>

---

*Phase: 54-qramm-assessment-ui-scorecard*
*Context gathered: 2026-05-07*
