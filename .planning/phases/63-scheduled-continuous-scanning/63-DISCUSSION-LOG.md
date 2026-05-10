# Phase 63: Scheduled / Continuous Scanning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 63-scheduled-continuous-scanning
**Mode:** --auto (all gray areas auto-resolved; no user interaction)
**Areas discussed:** Cron parsing, Dispatch mechanism, Run history storage, Dashboard mutability, Scheduler process model

---

## Preflight: Wave A Gate Fix

Phase 58 (`dashboard-api-hardening`) was marked `[ ]` in ROADMAP.md despite all 7 plans having
SUMMARY.md files with `Self-Check: PASSED` and all audit blockers closed (`[x]` in AUDIT-TASKS.md).
Auto-fix: updated ROADMAP.md to `[x]` with `(completed 2026-05-10)`. Wave A is now 100% complete.

---

## Cron Parsing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| `croniter` | Lightweight MIT library, de facto Python cron parser, no transitive extras | ✓ |
| `APScheduler` | Full scheduling framework; heavier dep tree | |
| Custom parser | Roll-our-own regex/split; error-prone | |

**Auto-selected:** `croniter>=1.4.0` added to `[dashboard]` optional extra in `pyproject.toml`
**Notes:** Scoped to optional extra since it's only needed for `quirk scheduler run`

---

## Dispatch Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Subprocess call | `subprocess.Popen(["quirk", ...])` — crash-isolated, full CLI code path | ✓ |
| Direct Python import | Import `run_scan.main()` equivalent — tighter coupling, state-sharing risk | |

**Auto-selected:** subprocess
**Notes:** A crashed scan subprocess does not crash the scheduler; reuses CLI arg chain unchanged

---

## Run History Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Status columns only | Add `last_run_at`, `last_run_status` to `scheduled_scans` | |
| Separate `scheduled_runs` table | Per-dispatch history rows with FK to `scheduled_scans` | ✓ |

**Auto-selected:** separate `scheduled_runs` table
**Notes:** Phase 64 (trend analysis) will want `scan_id` FK on each dispatch; separate table enables this without schema migration

---

## Dashboard Mutability

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only listing only | No enable/disable toggle | |
| PATCH `/api/schedules/{id}` | RESTful enable/disable toggle endpoint, bearer auth required | ✓ |
| Separate enable/disable endpoints | `/enable` and `/disable` action endpoints | |

**Auto-selected:** PATCH `/api/schedules/{id}` with `{"enabled": bool}`
**Notes:** First writable dashboard route; Phase 58 bearer + CSRF auth makes this safe. Full REST surface: GET list, POST create, PATCH update, DELETE remove.

---

## Scheduler Process Model

| Option | Description | Selected |
|--------|-------------|----------|
| 60-second sleep-loop | `while True: check(); time.sleep(60)` | ✓ |
| asyncio event loop | Async sleep; needed only if multiple concurrent I/O operations required | |
| Threading | ThreadPoolExecutor for concurrent checks; adds complexity | |

**Auto-selected:** 60-second sleep-loop
**Notes:** Scans are long-running (minutes), not frequent (minutes to hours); no sub-minute use case. Simple loop is easiest to reason about and maintain.

---

## Claude's Discretion

- Output directory for dispatched scans: `output/scheduled/{schedule_name}/{YYYYMMDD-HHMMSS}/`
- Signal handling: catch SIGINT/SIGTERM, set stop flag, wait up to 30s for in-flight subprocess
- `quirk schedule list`: Rich table via Logger, consistent with existing CLI output style
- `next_run_at`: computed on-the-fly from `croniter`, not stored (would go stale immediately)

## Deferred Ideas

- Failure notifications (email/webhook) — future notification phase
- Distributed scheduler (leadership election) — SaaS/multi-tenant phase
- Sub-minute scheduling — no use case identified
- Resumable scheduled scans — Phase 67 integration task
- Dashboard-initiated ad-hoc scheduling — Phase 65 scope
