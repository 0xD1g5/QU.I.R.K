---
phase: 63-scheduled-continuous-scanning
plan: 03
subsystem: api
tags: [fastapi, react, scheduling, dashboard, shadcn, sqlite, croniter]

requires:
  - phase: 63-scheduled-continuous-scanning
    plan: 01
    provides: ScheduledScan/ScheduledRun ORM models, get_db dep, croniter dep
  - phase: 58-dashboard-api-hardening
    provides: require_auth + require_csrf middleware, fetchApi wrapper with auto-headers

provides:
  - GET/POST/PATCH/DELETE /api/schedules FastAPI router with auth+csrf at router level
  - schedules.py router registered in app.py (first writable dashboard route — D-04)
  - useSchedules.ts hook: cancellation-safe, patchEnabled (optimistic), deleteSchedule
  - SchedulesPage React component: Table with all UI-SPEC columns, Switch toggles, delete Dialog
  - Sidebar Calendar nav item between Trends and QRAMM Assessment
  - App.tsx Route path="/schedules"
  - 11 pytest tests covering all verbs + auth/csrf negative paths

affects:
  - 63-04 (Plan 04: phase verification uses /api/schedules surface)
  - 64 (Phase 64 trend analysis: correlates by scheduled_runs.scan_id)

tech-stack:
  added: [shadcn switch component, shadcn dialog component]
  patterns:
    - "APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)]) — first writable dashboard route (D-04)"
    - "Optimistic UI toggle: flip local state before PATCH, revert on failure (Pitfall 6)"
    - "Cancellation-safe hook: let cancelled=false + if(!cancelled) guard + cleanup return (HOOK-01)"
    - "IntegrityError → fixed 409 message, never stringify exception (T-63-16/LEAK-02)"
    - "next_run_at computed on-the-fly via croniter, never stored (D-06)"
    - "tz-naive UTC datetimes: datetime.now(timezone.utc).replace(tzinfo=None) (Pitfall 1)"
    - "Explicit ScheduledRun cascade delete before ScheduledScan delete (SQLite no FK enforcement)"

key-files:
  created:
    - quirk/dashboard/api/routes/schedules.py
    - tests/test_schedules_api.py
    - src/dashboard/src/hooks/useSchedules.ts
    - src/dashboard/src/pages/schedules.tsx
    - src/dashboard/src/components/ui/switch.tsx
    - src/dashboard/src/components/ui/dialog.tsx
  modified:
    - quirk/dashboard/api/app.py
    - src/dashboard/src/components/sidebar.tsx
    - src/dashboard/src/App.tsx

key-decisions:
  - "Auth+CSRF applied at APIRouter level (not per-route) — single dependency declaration covers all 4 verbs (D-04)"
  - "shadcn switch/dialog installed via npx shadcn add; moved from @/ alias path to correct src/components/ui/"
  - "cronToHuman() implemented as lightweight local helper (5 patterns + raw fallback) — no third-party lib per UI-SPEC"
  - "EmptyStateCard body prop not available; combined heading+body into single message string"
  - "useSchedules fetchCount state triggers refetch without re-declaring the useEffect dependency"

patterns-established:
  - "First writable dashboard route: mutating verbs require APIRouter(dependencies=[auth, csrf]) — D-04 architecture milestone"
  - "Optimistic toggle UI: flip → PATCH → no-op on success; flip-back on failure"
  - "Delete confirmation dialog: Dialog with Keep/Delete buttons + inline error on failure"

requirements-completed: [SCHED-01, SCHED-03]

duration: 5min
completed: 2026-05-10
---

# Phase 63 Plan 03: Schedules API + React Dashboard Page Summary

**FastAPI GET/POST/PATCH/DELETE /api/schedules router (first writable dashboard route, D-04) + React /schedules page with Switch toggles, delete Dialog, and optimistic UI — 11 pytest tests, production build verified**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-10T20:36:50Z
- **Completed:** 2026-05-10T20:41:53Z
- **Tasks:** 2
- **Files modified:** 9 (2 modified, 7 created)

## Accomplishments

- Four-verb /api/schedules REST surface with auth+csrf enforced at router level (D-04 architecture milestone — first writable dashboard route)
- croniter.is_valid() validation → 400; IntegrityError → fixed 409 message (T-63-16/LEAK-02 pattern)
- Explicit ScheduledRun cascade delete; next_run_at computed on-the-fly (D-06)
- React /schedules page: Table with Name/Target/Cron(tooltip)/Next Run/Last Run/Switch/Delete columns per UI-SPEC; all colors via CSS variable tokens, zero hardcoded hex
- useSchedules hook with cancellation guard (HOOK-01), optimistic patchEnabled + revert-on-failure
- shadcn switch + dialog components installed and placed in src/components/ui/
- 11 pytest tests pass; existing test_all_mutating_routes_have_auth_dependency remains green; npm build succeeds

## API Surface Table

| Verb | Path | Auth | CSRF | Request Schema | Response Schema |
|------|------|------|------|----------------|-----------------|
| GET | /api/schedules | required* | passthrough | — | ScheduleListResponse |
| POST | /api/schedules | required* | required | ScheduleCreateRequest | ScheduleResponse (201) |
| PATCH | /api/schedules/{id} | required* | required | ScheduleTogglePayload | ScheduleResponse |
| DELETE | /api/schedules/{id} | required* | required | — | 204 No Content |

*Auth: required when QUIRK_API_TOKEN is set (Phase 58 D-02 passthrough when disabled)

## Task Commits

1. **Task 1: FastAPI schedules router + app.py + 11 pytest tests** - `9c6ed6b` (feat)
2. **Task 2: React /schedules page + useSchedules hook + sidebar + App route** - `862363e` (feat)

## Files Created/Modified

- `quirk/dashboard/api/routes/schedules.py` - New: GET/POST/PATCH/DELETE router with auth+csrf
- `quirk/dashboard/api/app.py` - Modified: import schedules, include_router(schedules.router, prefix="/api")
- `tests/test_schedules_api.py` - New: 11 tests for all verbs + auth/csrf negative paths
- `src/dashboard/src/hooks/useSchedules.ts` - New: cancellation-safe hook with optimistic patchEnabled
- `src/dashboard/src/pages/schedules.tsx` - New: SchedulesPage with Table, Switch, Dialog
- `src/dashboard/src/components/ui/switch.tsx` - New: shadcn switch component
- `src/dashboard/src/components/ui/dialog.tsx` - New: shadcn dialog component
- `src/dashboard/src/components/sidebar.tsx` - Modified: Calendar nav item added
- `src/dashboard/src/App.tsx` - Modified: SchedulesPage import + Route

## Decisions Made

- Auth+CSRF applied at APIRouter level (not per-route) — single dependency declaration per D-04 design
- shadcn add installed to @/ alias path (not src/components/ui/); moved manually to correct location
- cronToHuman() as local helper covering 5 patterns (daily, weekly, every-N-hours + fallback) per UI-SPEC
- EmptyStateCard only accepts `message`; combined empty-state copy into single string without body prop
- Fetch-count state for refetch trigger avoids re-declaring useEffect deps

## D-04 Architecture Note

This plan closes the first writable dashboard route milestone. The APIRouter pattern:
```python
router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])
```
is now the canonical pattern for all future mutating dashboard routes. The D-06 gate
(`test_all_mutating_routes_have_auth_dependency`) automatically validates new routes.

## Phase 64 Dependency Note

Phase 64 trend analysis can correlate scheduled scans to scan results via
`scheduled_runs.scan_id` (populated by Plan 02 dispatcher once scans complete).
The /api/schedules GET surface provides `last_run_status` which Phase 64 can
extend with trend data using the same ScheduledRun table.

## Deviations from Plan

None - plan executed exactly as written. All patterns (HOOK-01 cancellation, Pitfall 1 tz-naive UTC, T-63-16 IntegrityError, D-04 router-level auth) applied as specified.

## Issues Encountered

- shadcn CLI installed components to `@/components/ui/` (treated `@` as a literal directory) instead of `src/components/ui/`. Moved files manually to correct location. No impact on functionality.

## Known Stubs

None — all routes return real DB data. The "Add Schedule" Sheet shows the CLI command as documented (Phase 63 scope for the form-based create UI is explicitly deferred to Phase 65 per UI-SPEC).

## Threat Flags

No new threat surface beyond what was declared in the PLAN.md threat model:
- T-63-12 (CSRF): mitigated via Depends(require_csrf) at router level
- T-63-13 (unauth DELETE): mitigated via Depends(require_auth) at router level
- T-63-14 (cron injection): mitigated via croniter.is_valid() before INSERT
- T-63-15 (name path traversal): mitigated via Pydantic Field(pattern=r"^[A-Za-z0-9_\-\.]+$")
- T-63-16 (IntegrityError leak): mitigated via fixed 409 message

## Next Phase Readiness

- Plan 04 (`63-04`): phase verification — all API surfaces and React routes ready for verification
- Phase 64: trend analysis can use scheduled_runs.scan_id correlation
- Phase 65: dashboard-initiated ad-hoc scans (the "Add Schedule" form currently shows CLI-only)
- No blockers

## Self-Check: PASSED

- `quirk/dashboard/api/routes/schedules.py`: exists, compiles clean
- `quirk/dashboard/api/app.py`: schedules imported + include_router registered
- `tests/test_schedules_api.py`: exists, 11 tests, all pass
- `src/dashboard/src/hooks/useSchedules.ts`: exists, cancellation pattern verified
- `src/dashboard/src/pages/schedules.tsx`: exists, no hardcoded hex, build succeeds
- `src/dashboard/src/components/ui/switch.tsx`: exists
- `src/dashboard/src/components/ui/dialog.tsx`: exists
- Task 1 commit: `9c6ed6b` — verified in git log
- Task 2 commit: `862363e` — verified in git log
- 27 tests pass (11 new + 16 existing auth tests)
- npm run build: exit 0

---
*Phase: 63-scheduled-continuous-scanning*
*Completed: 2026-05-10*
