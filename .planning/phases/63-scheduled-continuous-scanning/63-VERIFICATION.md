---
phase: 63-scheduled-continuous-scanning
verified: 2026-05-10T21:00:00Z
status: passed
score: 6/6
overrides_applied: 0
re_verification: null
gaps: []
human_verification:
  - test: "Browser walkthrough of /schedules dashboard page"
    expected: "Table renders with Switch toggles that toggle enabled state, delete dialog fires correctly, and Add Schedule sheet shows CLI command"
    why_human: "React build tested by npm, route wired in App.tsx, but visual rendering and interactive toggle/delete flow require browser confirmation"
---

# Phase 63: Scheduled / Continuous Scanning — Verification Report

**Phase Goal:** Transform QUIRK from a one-shot CLI tool into a continuously-running posture monitor — CLI scheduling layer (SCHED-01), long-running dispatcher (SCHED-02), and dashboard /schedules route (SCHED-03).
**Verified:** 2026-05-10T21:00:00Z
**Status:** passed (1 human verification item — all automated checks green)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `quirk schedule add` persists a row to `scheduled_scans` | VERIFIED | `schedule_cmd.py` _cmd_add inserts ScheduledScan row; `test_schedule_add_persists` passes |
| 2 | `quirk/cli/scheduler_cmd.py` implements 60s loop, subprocess dispatch, SIGINT/SIGTERM, startup recovery | VERIFIED | File exists, 245 lines, all four behaviours confirmed in code and tests |
| 3 | `GET /api/schedules` returns `next_run_at` (computed) and `last_run_status` (joined) | VERIFIED | `_compute_next_run` + `_last_run_status` in schedules.py; `test_get_includes_next_run` + `test_get_includes_last_run_status` pass |
| 4 | `POST/PATCH/DELETE /api/schedules/*` require auth + CSRF (`X-Quirk-Request: 1`) | VERIFIED | `router = APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])`; `test_patch_requires_csrf`, `test_post_requires_auth`, `test_no_unprotected_mutating_routes` all pass |
| 5 | Dashboard `/schedules` React page exists with Switch toggles, status badges, delete dialog | VERIFIED | `src/dashboard/src/pages/schedules.tsx` (302 lines): Switch, StatusBadge, Dialog all present; route wired in App.tsx; sidebar Calendar nav item added |
| 6 | All 40 Phase 63 tests pass | VERIFIED | `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py tests/test_api_auth.py` — 40 collected, 40 passed, 0 failed |

**Score:** 6/6 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/cli/schedule_cmd.py` | CRUD CLI (add/list/enable/disable/remove) | VERIFIED | 195 lines; all 5 subcommands implemented with argparse; croniter validation; name allowlist regex; IntegrityError fixed message |
| `quirk/cli/scheduler_cmd.py` | 60s dispatch loop + signal handlers + startup recovery | VERIFIED | 245 lines; `_stop_flag` + SIGINT/SIGTERM handlers; `_recover_stale_runs`; `_check_and_dispatch_due`; 1-second sub-sleep loop |
| `quirk/models.py` — ScheduledScan/ScheduledRun | ORM models with correct columns | VERIFIED | ScheduledScan at line 158 (8 columns including unique name, cron_expr, enabled); ScheduledRun at line 177 (7 columns including schedule_id, status) |
| `quirk/db.py` — `_ensure_scheduled_tables` | Migration helper called from init_db() | VERIFIED | `_ensure_scheduled_tables(engine)` at line 228; called at line 264 from `init_db()` |
| `run_scan.py` — interception blocks | `schedule` and `scheduler` blocks with `return` | VERIFIED | Lines 267–277; both blocks with `return` after dispatch |
| `pyproject.toml` — croniter dep | `croniter>=1.4.0` in `[dashboard]` extra | VERIFIED | `croniter>=1.4.0` on line 39 under dashboard optional extras |
| `quirk/dashboard/api/routes/schedules.py` | GET/POST/PATCH/DELETE with auth+csrf at router level | VERIFIED | 192 lines; `APIRouter(dependencies=[Depends(require_auth), Depends(require_csrf)])`; all 4 verbs; `_compute_next_run` on-the-fly; explicit cascade delete |
| `quirk/dashboard/api/app.py` | schedules router mounted | VERIFIED | Import at line 22, `include_router(schedules.router, prefix="/api")` at line 67 |
| `src/dashboard/src/hooks/useSchedules.ts` | Cancellation-safe hook with patchEnabled + deleteSchedule | VERIFIED | 155 lines; `let cancelled = false` guard; optimistic patchEnabled with revert-on-failure; deleteSchedule |
| `src/dashboard/src/pages/schedules.tsx` | SchedulesPage with Switch, StatusBadge, delete Dialog | VERIFIED | 302 lines; Switch, StatusBadge, Dialog, EmptyStateCard, Table all present; cronToHuman helper |
| `src/dashboard/src/components/ui/switch.tsx` | shadcn Switch component | VERIFIED | File present |
| `src/dashboard/src/components/ui/dialog.tsx` | shadcn Dialog component | VERIFIED | File present |
| `src/dashboard/src/components/sidebar.tsx` | Schedules nav item | VERIFIED | `Calendar` icon imported; `{ path: "/schedules", label: "Schedules", Icon: Calendar }` at line 33 |
| `src/dashboard/src/App.tsx` | `/schedules` Route | VERIFIED | `SchedulesPage` import at line 19; `Route path="/schedules"` at line 46 |
| `tests/test_schedule_cmd.py` | 7 tests for SCHED-01 | VERIFIED | 7 tests collected, 7 pass |
| `tests/test_scheduler_cmd.py` | 6 tests for SCHED-02 | VERIFIED | 6 tests collected, 6 pass |
| `tests/test_schedules_api.py` | 11 tests for SCHED-03 | VERIFIED | 11 tests collected, 11 pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run_scan.py` | `quirk.cli.schedule_cmd.run_schedule` | interception block + `return` | WIRED | Lines 267–271 |
| `run_scan.py` | `quirk.cli.scheduler_cmd.run_scheduler` | interception block + `return` | WIRED | Lines 273–277 |
| `schedule_cmd.py` | `ScheduledScan` model | `from quirk.models import ScheduledScan` + `get_session` | WIRED | Insert at `_cmd_add`; query at `_cmd_list` |
| `scheduler_cmd.py` | `ScheduledScan` + `ScheduledRun` | `from quirk.models import ScheduledScan, ScheduledRun` + session | WIRED | `_check_and_dispatch_due` queries ScheduledScan; `_dispatch_schedule` writes ScheduledRun |
| `schedules.py` (API) | `ScheduledScan` + `ScheduledRun` | `from quirk.models import ScheduledRun, ScheduledScan` + `get_db` | WIRED | All 4 verbs read/write both models |
| `schedules.py` (API) | `require_auth` + `require_csrf` | `APIRouter(dependencies=[...])` | WIRED | Router-level — covers all 4 verbs automatically |
| `app.py` | `schedules.router` | `include_router(schedules.router, prefix="/api")` | WIRED | Line 67 |
| `useSchedules.ts` | `/api/schedules` | `fetchApi("/api/schedules")` + `fetchApi("/api/schedules/${id}", {method:"PATCH"/"DELETE"})` | WIRED | Fetch + response handling all present |
| `schedules.tsx` | `useSchedules` hook | `const { data, loading, error, patchEnabled, deleteSchedule } = useSchedules()` | WIRED | Data rendered in Table; patchEnabled called from Switch onCheckedChange |
| `App.tsx` | `SchedulesPage` | `Route path="/schedules" element={<SchedulesPage />}` | WIRED | Line 46 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `schedules.tsx` | `data.schedules` | `useSchedules` → `fetchApi("/api/schedules")` → `list_schedules()` → `db.query(ScheduledScan)` | Yes — SQLAlchemy query from `scheduled_scans` table | FLOWING |
| `schedules.py` GET | `rows` | `db.query(ScheduledScan).order_by(ScheduledScan.id.asc()).all()` | Yes — live DB read | FLOWING |
| `schedules.py` GET | `last_run_status` | `_last_run_status()` → `db.query(ScheduledRun).filter(...).order_by(dispatched_at.desc()).first()` | Yes — live DB join query | FLOWING |
| `schedules.py` GET | `next_run_at` | `_compute_next_run()` → `croniter(s.cron_expr, base).get_next(datetime)` | Yes — computed from real cron_expr per row | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 40 Phase 63 tests pass | `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py tests/test_api_auth.py` | 40 collected, 40 passed, 0 failed, 1.85s + 0.70s | PASS |
| schedule_cmd and scheduler_cmd compile clean | Python import check via test collection | No import errors in any of the 3 test modules | PASS |
| `test_all_mutating_routes_have_auth_dependency` meta-test | included in test_schedules_api.py and test_api_auth.py | Both pass — /api/schedules PATCH/POST/DELETE confirmed auth-gated | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SCHED-01 | 63-01 | Operator can register a scan schedule via `quirk schedule add` persisting to `scheduled_scans` | SATISFIED | `schedule_cmd.py` + `ScheduledScan` model + 7 passing tests; REQUIREMENTS.md marked `[x]` |
| SCHED-02 | 63-02 | `quirk scheduler run` long-running mode dispatches at cron times, writes results, surfaces dispatch status | SATISFIED | `scheduler_cmd.py` + subprocess Popen dispatch + `ScheduledRun` status tracking + 6 passing tests; REQUIREMENTS.md marked `[x]` |
| SCHED-03 | 63-03 | Dashboard `/schedules` route lists scheduled scans with next-run time, last-run status, enable/disable toggles | SATISFIED | `schedules.py` API + `schedules.tsx` page + `useSchedules.ts` hook + 11 passing API tests; REQUIREMENTS.md marked `[x]` |

---

## Anti-Patterns Found

No anti-patterns found. Scan of `schedule_cmd.py`, `scheduler_cmd.py`, `schedules.py` (API), `schedules.tsx`, and `useSchedules.ts` found:
- No TODO/FIXME/PLACEHOLDER comments
- No stub returns (`return null`, `return {}`, `return []`) in rendering paths
- No hardcoded empty data structures passed to rendering components
- No console.log-only handlers
- All form handlers perform real API calls (patchEnabled, deleteSchedule call fetchApi)

---

## Human Verification Required

### 1. /schedules Dashboard Page — Interactive Visual Walkthrough

**Test:** Navigate to the QUIRK dashboard `/schedules` route in a browser. Add a schedule via CLI (`quirk schedule add --name "weekly-prod" --cron "0 2 * * 1" --target prod.example.com --profile balanced`), then reload the page.
**Expected:**
- Table renders with Name, Target, Cron, Next Run, Last Run, Enabled (Switch), and Actions columns
- The new schedule appears with a "Never run" status badge
- Cron cell shows `0 2 * * 1` with a tooltip displaying "Every Monday at 02:00 UTC"
- Switch toggle is in enabled state; clicking it sends PATCH to `/api/schedules/{id}`
- Trash icon opens delete confirmation dialog; "Delete Schedule" button removes the row
- "Add Schedule" button opens a Sheet showing the CLI command
**Why human:** React build verified by npm, route wired in App.tsx, all API paths tested via pytest — but Switch interactivity, optimistic toggle, delete dialog flow, and tooltip rendering require a browser to confirm visual correctness.

---

## Gaps Summary

No gaps. All 6 observable truths are VERIFIED, all 17 required artifacts pass all 4 verification levels (exists, substantive, wired, data-flowing), all 3 SCHED requirements are satisfied, and all 40 Phase 63 tests pass.

The single human verification item is the standard browser walkthrough for an interactive React page — this does not block phase completion; it is flagged per verification methodology for completeness.

---

## Commit History (Phase 63)

| Commit | Description | Verified |
|--------|-------------|---------|
| `d1a2e98` | feat(63-01): add ScheduledScan/ScheduledRun ORM models, croniter dep, migration helper, test stubs | YES |
| `8356724` | feat(63-01): implement schedule_cmd.py CRUD subcommands and wire run_scan.py interception blocks | YES |
| `2602b16` | feat(63-02): implement quirk scheduler run dispatcher loop (SCHED-02) | YES |
| `9c6ed6b` | feat(63-03): add FastAPI schedules router + 11 pytest tests | YES |
| `862363e` | feat(63-03): add React /schedules page, useSchedules hook, sidebar nav | YES |

---

_Verified: 2026-05-10T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
