---
phase: 54-qramm-assessment-ui-scorecard
plan: "03"
subsystem: qramm-frontend
tags: [qramm, react, routing, wizard, context, sidebar, shadcn]

dependency_graph:
  requires:
    - phase: 54-plan-01
      provides: POST /api/qramm/sessions, POST /api/qramm/profiles, GET /api/qramm/sessions
    - phase: 54-plan-02
      provides: QRAMMProvider, QRAMMContext, useQRAMMSession, qramm-constants.ts
  provides:
    - OrgProfilePage component at /qramm route
    - QRAMMProvider wiring in App.tsx (inside ScanProvider, outside TooltipProvider)
    - /qramm and /qramm/assessment routes registered in BrowserRouter
    - QRAMM Assessment sidebar nav entry with ClipboardList icon
    - startsWith('/qramm') active-state fix for nested route highlighting
    - _AssessmentPagePlaceholder stub in App.tsx (replaced in plan 04)
  affects:
    - plan 04 (qramm-assessment.tsx — can now be reached via real routing + sidebar)

tech-stack:
  added: []
  patterns:
    - "executive.tsx try/catch/finally + loading-state mutation pattern (handleExportPdf shape)"
    - "Inline confirmation pattern: no modal, rendered as conditional JSX below action buttons"
    - "Badge multi-select for regulatory obligations using aria-pressed toggleable buttons"
    - "startsWith active-state for parent/child route sidebar items"

key-files:
  created:
    - src/dashboard/src/pages/qramm-profile.tsx (311 lines)
  modified:
    - src/dashboard/src/App.tsx (49 -> 58 lines; +9 lines for QRAMMProvider wrap + 2 routes + placeholder component + imports)
    - src/dashboard/src/components/sidebar.tsx (97 -> 101 lines; +4 lines for ClipboardList + NAV_ITEMS entry + startsWith isActive patch)

key-decisions:
  - "Inline New Assessment confirmation (no modal) per UI-SPEC — avoids extra modal state management and matches plan direction"
  - "_AssessmentPagePlaceholder is intentionally a stub inline in App.tsx; plan 04 imports qramm-assessment.tsx which replaces it"
  - "Regulatory obligations rendered as badge toggle buttons with aria-pressed (not shadcn Select) per UI-SPEC multi-select requirement"
  - "Submit button disabled while submitting AND when required Select fields are empty — double-gate prevents accidental double-submit (T-54-14)"

patterns-established:
  - "Inline error banner (text-sm text-destructive paragraph) instead of sonner toast — per plan decision: no new toast library in phase 54"
  - "useQRAMMSession provides session + reload; page resets context state via ctx.setSessionId/setProfile/setScoreResult/resetAnswers then calls reload()"

requirements-completed: [QRAMM-09]

duration: 18min
completed: 2026-05-07
---

# Phase 54 Plan 03: QRAMM Org Profile Wizard Summary

**OrgProfilePage at /qramm: 5-field wizard with auto-resume (D-01), inline New Assessment archive flow (D-02), and POST /sessions -> POST /profiles -> navigate('/qramm/assessment') submit chain; sidebar and routing fully wired.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-07T00:00:00Z
- **Completed:** 2026-05-07
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- QRAMMProvider now wraps all routes inside ScanProvider; both /qramm and /qramm/assessment routes are registered in App.tsx
- Sidebar shows QRAMM Assessment entry with ClipboardList icon; active state correctly highlights on /qramm/assessment (startsWith fix)
- OrgProfilePage has 3 visual states: loading spinner, Resume card (session exists), 5-field org profile form (no session)
- New Assessment inline confirmation archives the previous session via DELETE and resets all QRAMM context state
- TypeScript strict-mode check and Vite production build both pass with zero errors

## Task Commits

1. **Task 1: Wire QRAMMProvider + routes in App.tsx and sidebar entry** - `283bf78` (feat)
2. **Task 2: Build OrgProfilePage with form, auto-resume, and New Assessment confirm flow** - `80bcd27` (feat)

## Files Created/Modified

- `src/dashboard/src/pages/qramm-profile.tsx` (311 lines) — OrgProfilePage: loading / resume / form states; submit + archive flows
- `src/dashboard/src/App.tsx` (+9 lines) — QRAMMProvider wrap, OrgProfilePage import, /qramm + /qramm/assessment routes, _AssessmentPagePlaceholder
- `src/dashboard/src/components/sidebar.tsx` (+4 lines) — ClipboardList import, QRAMM Assessment NAV_ITEMS entry, startsWith isActive patch

## File Line Counts

| File | Lines |
|------|-------|
| qramm-profile.tsx | 311 |
| App.tsx | 58 |
| sidebar.tsx | 101 |

## Placeholder Status

`_AssessmentPagePlaceholder` is still inline in App.tsx — intentional. Plan 04 will import `AssessmentPage` from `@/pages/qramm-assessment` and replace this function.

## Build Output

Production Vite build (run from main repo with node_modules):

```
2371 modules transformed
index-CYRZ_yTa.js   213.69 kB gzip: 60.93 kB
vendor-react-CvXjEM6e.js  217.60 kB gzip: 69.70 kB
built in 549ms
```

No size delta attributable to this plan (qramm-profile.tsx rolled into index bundle).

## UI-SPEC Copy Deviations

None. All copy strings match UI-SPEC verbatim:
- "Resume Your Assessment"
- "You have an in-progress assessment. Pick up where you left off."
- "Continue Assessment"
- "New Assessment"
- "Start a New Assessment?"
- "Starting a new assessment will archive your current progress. This cannot be undone."
- "Confirm New Assessment"
- "Keep Current Assessment"
- "QRAMM Org Profile"
- "Start Assessment"

## Deviations from Plan

None — plan executed exactly as written. The stub `qramm-profile.tsx` created during Task 1 (to allow TSC to pass on the App.tsx import) was immediately replaced by the full OrgProfilePage in Task 2 before the stub was committed as a final state.

## Known Stubs

- `_AssessmentPagePlaceholder` in App.tsx — intentional, documented above. Renders placeholder copy only when user navigates to /qramm/assessment before plan 04 is deployed. Not a data stub; no UI-breaking empty value.

## Threat Coverage

All 5 STRIDE threats from the plan's threat model were addressed:

| Threat | Mitigation |
|--------|-----------|
| T-54-12 Tampering (form payload) | Values come from constrained option list constants; no freeform text input |
| T-54-13 Info Disclosure (error rendering) | JSX text children; React auto-escapes string values; no unsafe HTML rendering APIs used |
| T-54-14 DoS (double-submit) | `submitting` state disables submit button while in-flight; required-field guard also prevents early submission |
| T-54-15 Repudiation (DELETE session) | User explicitly confirms via "Confirm New Assessment" inline UI before archive |
| T-54-16 EoP (direct nav to /qramm/assessment) | Accepted; plan 04 will show empty-state copy |

## Threat Flags

No new trust boundary surface beyond the plan's threat model.

## Self-Check

Files exist:
- src/dashboard/src/pages/qramm-profile.tsx: FOUND (311 lines)
- src/dashboard/src/App.tsx: FOUND (58 lines)
- src/dashboard/src/components/sidebar.tsx: FOUND (101 lines)

Commits:
- 283bf78 (Task 1: App.tsx + sidebar.tsx + stub): in git log
- 80bcd27 (Task 2: full OrgProfilePage): in git log

## Self-Check: PASSED
