# Phase 65: Dashboard-Initiated Scan - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 65-dashboard-initiated-scan
**Areas discussed:** @file targets in form, Stale job recovery placement, Sidebar 'New Scan' placement

---

## @file Targets in Form

| Option | Description | Selected |
|--------|-------------|----------|
| @file is CLI-only | Strip @file support from the dashboard form. Validator rejects any target starting with '@'. Returns 422 immediately. | ✓ |
| @file supported with allowlist guard | Allow @file but clamp to an allowed directory, same pattern as Phase 58 PDF SSRF clamp. | |
| Pass through unchanged | Let target_expander.py handle it at scan time. No additional validation. | |

**User's choice:** @file is CLI-only  
**Follow-up:** Add `@field_validator('targets')` in `ScanSubmitRequest` that raises `ValueError` if value starts with `@`. Returns 422 with clear field-level message. Form placeholder omits `@file` entirely.

**Notes:** This is a defense-in-depth decision consistent with Phase 58's path-traversal guard on `quirk init`. The API layer must not trust that only the UI calls it — any direct POST to `/api/jobs` with an `@file` target would otherwise cause the spawned subprocess to read arbitrary server-side files.

---

## Stale Job Recovery Placement

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI lifespan | @asynccontextmanager lifespan in app.py; startup block runs stale-job sweep. Modern FastAPI pattern (on_event deprecated since 0.95). | ✓ |
| Inline in create_app() | Synchronous call to _recover_stale_jobs(db_path) inside the factory. Simpler. | |
| Skip stale recovery for now | Defer to Phase 68. Document as known edge case. | |

**Follow-up (db_path access):**

| Option | Description | Selected |
|--------|-------------|----------|
| Pass db_path via app.state | create_app(db_path) sets app.state.db_path; lifespan reads state.db_path. FastAPI-idiomatic. | ✓ |
| Read from env/config inside lifespan | lifespan calls get_config() or reads QUIRK_DB_PATH directly. | |

**User's choice:** FastAPI lifespan + app.state.db_path  
**Notes:** app.py currently has no startup hook at all — Phase 65 introduces the first lifespan. Pattern: `create_app(db_path)` sets `app.state.db_path`, passes `lifespan=lifespan` to `FastAPI(...)`. The lifespan startup block calls `_recover_stale_jobs(app.state.db_path)`.

---

## Sidebar 'New Scan' Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top of sidebar as primary button | Filled Button (shadcn Button variant='default') above view links. Primary CTA treatment. | ✓ |
| At the bottom of nav links | Plain nav link after Schedules. Consistent but less prominent. | |

**User's choice:** Top of sidebar as primary button  
**Notes:** "New Scan" is an action, not a view. Positioning it above the view links with a distinct Button variant signals this clearly. Matches common SaaS patterns (e.g., "New project", "Create workspace" as top-of-sidebar CTAs).

---

## Claude's Discretion

- Output directory: `output/jobs/{job_id}/` (mirrors Phase 63's `output/scheduled/`)
- Signal handling: optimistic SIGTERM + catch `ProcessLookupError` silently
- Stage progress bar: `stage_index` computed server-side in `JobStatusResponse`
- Loading state: `<PageSpinner />` until first poll resolves
- `/scan/job/:jobId` with unknown ID: show error state with link back to `/scan/new` (not silent redirect)

## Deferred Ideas

- Per-scanner granular toggles — future UX polish phase
- WebSocket real-time streaming — 3s polling sufficient for 30–120s scans
- Multi-user job ownership — out of scope for v4.8
- Operator completion notifications — notifications phase post-operating-model
