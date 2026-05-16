---
phase: 65
plan: 05
subsystem: dashboard-initiated-scan
tags: [react, typescript, shadcn, polling, forms, routing]
dependency_graph:
  requires:
    - src/dashboard/src/lib/api.ts (fetchApi)
    - src/dashboard/src/context/ScanContext.tsx (setSelectedScanId)
    - src/dashboard/src/hooks/useSelectedScan.ts
    - quirk/dashboard/api/routes/jobs.py (POST/GET/DELETE /api/jobs)
  provides:
    - src/dashboard/src/types/api.ts (ScanSubmitRequest, JobStatus interfaces)
    - src/dashboard/src/hooks/useJobStatus.ts (cancellation-safe polling hook)
    - src/dashboard/src/pages/scan-new.tsx (ScanNewPage form component)
    - src/dashboard/src/pages/scan-job.tsx (ScanJobPage status component)
    - App.tsx /scan/new and /scan/job/:jobId routes
    - sidebar.tsx New Scan CTA button
  affects:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/App.tsx
    - src/dashboard/src/components/sidebar.tsx
tech_stack:
  added: []
  patterns:
    - "Discriminated union return type (kind: loading | not_found | error | ok) for hook state"
    - "Phase 62 HOOK-01 cancellation-safe polling: let cancelled = false + cleanup clearTimeout"
    - "satisfies operator for type-narrowed POST body (ScanSubmitRequest)"
    - "Lucide CheckCircle2 + animate-pulse for stage indicator dot states"
    - "STATUS_BADGE_CLASS map using CSS variable tokens (--ds-ok, --ds-high, --ds-critical)"
key_files:
  created:
    - src/dashboard/src/hooks/useJobStatus.ts
    - src/dashboard/src/pages/scan-new.tsx
    - src/dashboard/src/pages/scan-job.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/App.tsx
    - src/dashboard/src/components/sidebar.tsx
decisions:
  - "useJobStatus returns discriminated union (not data/loading/error) — avoids ambiguous state combinations"
  - "404 maps to not_found variant, not error — gives clean UI path for expired/unknown job IDs"
  - "On-error polling continues (setTimeout reschedule) to handle transient API unavailability"
  - "satisfies ScanSubmitRequest on POST body — TypeScript verifies payload shape at compile time"
  - "New Scan button uses useNavigate (not Link) per UI-SPEC: action button, not nav link"
  - "Stage dot state: stage_index > stageNum (1-indexed) = completed; === stageNum = current; else upcoming"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-13"
  tasks_completed: 3
  files_changed: 6
---

# Phase 65 Plan 05: Dashboard-Initiated Scan — React Frontend Slice Summary

One-liner: Full React frontend for dashboard-initiated scanning — ScanSubmitRequest/JobStatus types, cancellation-safe useJobStatus polling hook, ScanNewPage 4-control form, ScanJobPage 7-step stage indicator, route registration, and sidebar New Scan CTA.

## What Was Built

### Task 1: TypeScript types + useJobStatus polling hook

**`src/dashboard/src/types/api.ts`** — appended two interfaces:

- `ScanSubmitRequest`: `targets` string, `profile` union ("quick" | "standard" | "deep"), `calibration` union ("strict" | "balanced" | "lenient"), `enable_nmap` boolean.
- `JobStatus`: `job_id`, `status` 5-variant union, `current_stage`, `started_at`, `completed_at`, `scan_run_id`, `error_message`, `stage_index`, `stage_total`.

**`src/dashboard/src/hooks/useJobStatus.ts`** — new file implementing:

- Returns `JobStatusResult` discriminated union: `loading | not_found | error | ok`.
- Polls `GET /api/jobs/{jobId}` every 3000ms (`POLL_INTERVAL_MS = 3000`).
- Cancellation-safe per Phase 62 HOOK-01: `let cancelled = false` + `return () => { cancelled = true; clearTimeout(timer) }`.
- Stops polling on terminal status (`completed | failed | cancelled`).
- On `completed` with `scan_run_id`: calls `setSelectedScanId(scan_run_id)` then `navigate("/")` — auto-navigates to executive summary.
- 404 response yields `{ kind: "not_found" }` (not retried).
- Transient API errors yield `{ kind: "error" }` + reschedule (handles flapping backends).

### Task 2: ScanNewPage and ScanJobPage components

**`src/dashboard/src/pages/scan-new.tsx`** — form page implementing UI-SPEC `/scan/new` layout:

- Card (`max-w-[640px] mx-auto mt-16`) with "New Scan" heading and helper text.
- Targets: 4-row `<textarea>` with font-mono styling, aria-describedby help text.
- Profile: `<RadioGroup defaultValue="standard">` with Quick / Standard (default) / Deep, each with description copy per UI-SPEC Copywriting Contract.
- Calibration: `<RadioGroup defaultValue="balanced">` with Strict / Balanced (default) / Lenient.
- Options: `<Checkbox id="enable_nmap">` with nmap help text.
- Submit handler: client-side empty validation then POST `/api/jobs` with typed body then navigate to `/scan/job/{job_id}` on 201.
- 422 handling: @file path rejection message, field-level detail extraction, generic fallback.
- Inline error zone: `<p className="text-sm text-destructive">` shown below button when error is set.
- All error messages rendered via React text interpolation — no HTML-string injection sink used.

**`src/dashboard/src/pages/scan-job.tsx`** — status page implementing UI-SPEC `/scan/job/:jobId` layout:

- `STAGE_DISPLAY_NAMES` map: discovery, tls, ssh, api, identity, data_at_rest, reports.
- `STAGE_ORDER` array (7 stages) + `STATUS_BADGE_CLASS` / `STATUS_LABEL` maps using CSS variable tokens.
- Loading: `<PageSpinner ariaLabel="Loading scan status" />`.
- Not found: "Scan not found" card with link to `/scan/new`.
- Error: inline destructive text at top of card.
- OK state: heading + status badge, job ID (mono), Separator, 7-step horizontal stage indicator with `role="list"` / `role="listitem"` aria labels, Progress bar, stage label, metadata row.
- Stage indicator dot states: completed = `--ds-ok` teal + CheckCircle2 icon; current = `bg-primary animate-pulse`; upcoming = `bg-[var(--ds-border)]`.
- Cancel button: `variant="destructive"` fires `DELETE /api/jobs/{jobId}`; navigates to `/scan/new` on 204.
- Failed block: `<pre className="whitespace-pre-wrap text-sm">` renders `error_message` via React text interpolation only.
- Cancelled block: inline notice with link to `/scan/new`.

### Task 3: Route registration + sidebar CTA

**`src/dashboard/src/App.tsx`** — added two route registrations after `<Route path="/schedules" ...>`:
- `<Route path="/scan/new" element={<ScanNewPage />} />`
- `<Route path="/scan/job/:jobId" element={<ScanJobPage />} />`

**`src/dashboard/src/components/sidebar.tsx`** — added New Scan CTA:
- Imports: `Scan` from lucide-react, `Button` from `@/components/ui/button`, `useNavigate` from react-router-dom.
- `const navigate = useNavigate()` added to component body.
- New `<div className="px-2 py-3 border-b border-border">` block inserted after wordmark, before `<nav>`.
- Button: `variant="default"` (accent-filled per UI-SPEC), `w-full justify-start gap-3 min-h-[44px]`, `aria-label="New Scan"`.
- Icon-only below `lg` breakpoint (`<span className="hidden lg:inline">New Scan</span>`).
- Wrapped in `<Tooltip>` + `<TooltipContent side="right" className="lg:hidden">` per existing sidebar pattern.
- Not added to NAV_ITEMS (action button, not nav link — no active-link highlight treatment).

## Deviations from Plan

### Merge from main required

**Found during:** Pre-execution setup
**Issue:** Worktree was created from Phase 57 commit (65e0463) and was missing all Phase 65 Plans 01-04 changes (ScanJob model, /api/jobs router, app.py lifespan, shadcn Checkbox install, schedules.tsx, etc.).
**Fix:** `git merge main --no-edit` — fast-forward merge brought in all required files cleanly.
**Impact:** None — standard worktree initialization, same approach used by Plans 03 and 04.

## Known Stubs

None. All components render real data from the API. No hardcoded empty values that flow to UI rendering.

## Threat Surface Scan

No new network endpoints. New browser-side surfaces interacting with existing endpoints:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: form_input_to_api | src/dashboard/src/pages/scan-new.tsx | targets textarea value flows to POST /api/jobs body — validated server-side by Pydantic (Plan 03 mitigations apply) |
| threat_flag: polling_timer | src/dashboard/src/hooks/useJobStatus.ts | 3s polling timer bounded by tab lifecycle; stopped on terminal status plus unmount cleanup |

T-65-05-01 (targets XSS): React controlled input — value never flows to an HTML-string sink.
T-65-05-02 (error_message rendering): pre tag with React text interpolation only — no unsafe injection pattern.
T-65-05-03 (polling never stops): cleanup clears timer on unmount; TERMINAL set stops on completed/failed/cancelled.
T-65-05-05 (cancel without auth): fetchApi injects bearer + CSRF headers automatically.

## Self-Check: PASSED

- `src/dashboard/src/types/api.ts`: ScanSubmitRequest interface present, JobStatus interface present
- `src/dashboard/src/hooks/useJobStatus.ts`: file exists, `let cancelled = false` present, `POLL_INTERVAL_MS = 3000` present, `setSelectedScanId` present, `navigate("/")` present
- `src/dashboard/src/pages/scan-new.tsx`: ScanNewPage export, RadioGroup, Checkbox, POST to /api/jobs all present
- `src/dashboard/src/pages/scan-job.tsx`: ScanJobPage export, useJobStatus, STAGE_DISPLAY_NAMES, Cancel scan DELETE, PageSpinner, Scan not found all present
- `src/dashboard/src/App.tsx`: ScanNewPage import, ScanJobPage import, /scan/new route, /scan/job/:jobId route all present
- `src/dashboard/src/components/sidebar.tsx`: New Scan, variant="default", navigate("/scan/new"), Scan icon all present
- Grep for innerHTML/unsafe injection patterns in new pages: 0 matches
- TypeScript: `tsc --noEmit` exit 0
- Build: `npm run build` exit 0 (built in 368ms)
- Commits: fbe9eac (Task 1), ca736bb (Task 2), 0cfde47 (Task 3) all present in git log
